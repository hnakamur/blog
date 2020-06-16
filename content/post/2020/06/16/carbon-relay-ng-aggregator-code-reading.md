---
title: "carbon-relay-ngのAggregationについてのコードリーディング"
date: 2020-06-16T21:49:01+09:00
---

## はじめに

[grafana/carbon-relay-ng: Fast carbon relay+aggregator with admin interfaces for making changes online - production ready](https://github.com/grafana/carbon-relay-ng/) の [aggregator/aggregator.go](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go) と [aggregator/processor.go](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/processor.go) あたりのコードを読んだメモです。

今回の焦点は `Sum` の実装とその使われ方です。

## Sum 構造体の定義

[aggregator/processor.go#L282-L301](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/processor.go#L282-L301)

```go
// Sum aggregates to sum
type Sum struct {
  sum float64
}

func NewSum(val float64, ts uint32) Processor {
  return &Sum{
    sum: val,
  }
}

func (s *Sum) Add(val float64, ts uint32) {
  s.sum += val
}

func (s *Sum) Flush() ([]processorResult, bool) {
  return []processorResult{
    {fcnName: "sum", val: s.sum},
  }, true
}
```

## Processor インターフェース

[aggregator/processor.go#L303-L310](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/processor.go#L303-L310)

```go
type Processor interface {
  // Add adds a point to aggregate
  Add(val float64, ts uint32)
  // Flush returns the aggregated value(s) and true if it is valid
  // the only reason why it would be non-valid is for aggregators that need
  // more than 1 value but they didn't have enough to produce a useful result.
  Flush() ([]processorResult, bool)
}
```

## Processor インターフェースの Add メソッドの呼び出し箇所

[aggregator/aggregator.go#L126-L166](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go#L126-L166)

```go
func (a *Aggregator) AddOrCreate(key string, ts uint32, quantized uint, value float64) {
  rangeTracker.Sample(ts)
  agg, ok := a.aggregations[quantized]
  var proc Processor
  if ok {
    proc, ok = agg.state[key]
    if ok {
      // if both levels already exist, we only need to add the value
      agg.count++
      proc.Add(value, ts)
      return
    }
  } else {
    // first level doesn't exist. create it and add the ts to the list
    // (second level will be created below)
    a.tsList = append(a.tsList, quantized)
    if len(a.tsList) > 1 && a.tsList[len(a.tsList)-2] > quantized {
      sort.Sort(TsSlice(a.tsList))
    }
    agg = &aggregation{
      state: make(map[string]Processor),
    }
    a.aggregations[quantized] = agg
  }

  // first level exists but we need to create the 2nd level.

  // note, we only flush where for a given value of now, quantized < now-wait
  // this means that as long as the clock doesn't go back in time
  // we never recreate a previously created bucket (and reflush with same key and ts)
  // a consequence of this is, that if your data stream runs consistently significantly behind
  // real time, it may never be included in aggregates, but it's up to you to configure your wait
  // parameter properly. You can use the rangeTracker and numTooOld metrics to help with this
  if quantized > uint(a.now().Unix())-a.Wait {
    agg.count++
    proc = a.procConstr(value, ts)
    agg.state[key] = proc
    return
  }
  numTooOld.Inc(1)
}
```

`Aggregator` の `AddOrCreate` は `run` メソッドから呼ばれています。

[aggregator/aggregator.go#L281-L351](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go#L281-L351)

```go
func (a *Aggregator) run() {
  for {
    select {
    case msg := <-a.in:
      // note, we rely here on the fact that the packet has already been validated
      outKey, ok := a.matchWithCache(msg.buf[0])
      if !ok {
        continue
      }
      a.numIn.Inc(1)
      ts := uint(msg.ts)
      quantized := ts - (ts % a.Interval)
      a.AddOrCreate(outKey, msg.ts, quantized, msg.val)
    case now := <-a.tick:
      thresh := now.Add(-time.Duration(a.Wait) * time.Second)
      a.Flush(uint(thresh.Unix()))

      // if cache is enabled, clean it out of stale entries
      // it's not ideal to block our channel while flushing AND cleaning up the cache
      // ideally, these operations are interleaved in time, but we can optimize that later
      // this is a simple heuristic but should make the cache always converge on only active data (without memory leaks)
      // even though some cruft may temporarily linger a bit longer.
      // WARNING: this relies on Go's map implementation detail which randomizes iteration order, in order for us to reach
      // the entire keyspace. This may stop working properly with future go releases.  Will need to come up with smth better.
      if a.reCache != nil {
        cutoff := uint32(now.Add(-100 * time.Duration(a.Wait) * time.Second).Unix())
        a.reCacheMutex.Lock()
        for k, v := range a.reCache {
          if v.seen < cutoff {
            delete(a.reCache, k)
          } else {
            break // stop looking when we don't see old entries. we'll look again soon enough.
          }
        }
        a.reCacheMutex.Unlock()
      }
    case <-a.snapReq:
      aggsCopy := make(map[uint]*aggregation)
      for quant, aggReal := range a.aggregations {
        stateCopy := make(map[string]Processor)
        for key := range aggReal.state {
          stateCopy[key] = nil
        }
        aggsCopy[quant] = &aggregation{
          state: stateCopy,
          count: aggReal.count,
        }
      }
      s := &Aggregator{
        Fun:          a.Fun,
        procConstr:   a.procConstr,
        Matcher:      a.Matcher,
        OutFmt:       a.OutFmt,
        Cache:        a.Cache,
        Interval:     a.Interval,
        Wait:         a.Wait,
        DropRaw:      a.DropRaw,
        aggregations: aggsCopy,
        now:          time.Now,
        Key:          a.Key,
      }
      a.snapResp <- s
    case <-a.shutdown:
      thresh := a.now().Add(-time.Duration(a.Wait) * time.Second)
      a.Flush(uint(thresh.Unix()))
      a.wg.Done()
      return

    }
  }
}
```

## Processor インターフェースの Flush メソッドの呼び出し箇所

[aggregator/aggregator.go#L168-L218](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go#L168-L218)

```go
// Flush finalizes and removes aggregations that are due
func (a *Aggregator) Flush(cutoff uint) {
  flushWaiting.Inc(1)
  flushes.Add()
  flushWaiting.Dec(1)
  defer flushes.Done()

  pos := -1 // will track the pos of the last ts position that was successfully processed
  for i, ts := range a.tsList {
    if ts > cutoff {
      break
    }
    agg := a.aggregations[ts]
    for key, proc := range agg.state {
      results, ok := proc.Flush()
      if ok {
        if len(results) == 1 {
          a.out <- []byte(fmt.Sprintf("%s %f %d", key, results[0].val, ts))
          a.numFlushed.Inc(1)
        } else {
          for _, result := range results {
            a.out <- []byte(fmt.Sprintf("%s.%s %f %d", key, result.fcnName, result.val, ts))
            a.numFlushed.Inc(1)
          }
        }
      }
    }
    if aggregatorReporter != nil {
      aggregatorReporter.add(a.Key, uint32(ts), agg.count)
    }
    delete(a.aggregations, ts)
    pos = i
  }
  // now we must delete all the timestamps from the ordered list
  if pos == -1 {
    // we didn't process anything, so no action needed
    return
  }
  if pos == len(a.tsList)-1 {
    // we went through all of them. can just reset the slice
    a.tsList = a.tsList[:0]
    return
  }

  // adjust the slice to only contain the timestamps that still need processing,
  // reusing the backing array
  copy(a.tsList[0:], a.tsList[pos+1:])
  a.tsList = a.tsList[:len(a.tsList)-pos-1]

  //fmt.Println("flush done for ", a.now().Unix(), ". agg size now", len(a.aggregations), a.now())
}
```

`Aggregator` の `Flush` メソッドは `run` メソッド内の 2 箇所から呼ばれています。

## Aggregator 構造体

[aggregator/aggregator.go#L16-L53](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go#L16-L53)

```go
type Aggregator struct {
  Fun          string `json:"fun"`
  procConstr   func(val float64, ts uint32) Processor
  in           chan msg    `json:"-"` // incoming metrics, already split in 3 fields
  out          chan []byte // outgoing metrics
  Matcher      matcher.Matcher
  OutFmt       string
  outFmt       []byte
  Cache        bool
  reCache      map[string]CacheEntry
  reCacheMutex sync.Mutex
  Interval     uint                  // expected interval between values in seconds, we will quantize to make sure alginment to interval-spaced timestamps
  Wait         uint                  // seconds to wait after quantized time value before flushing final outcome and ignoring future values that are sent too late.
  DropRaw      bool                  // drop raw values "consumed" by this aggregator
  tsList       []uint                // ordered list of quantized timestamps, so we can flush in correct order
  aggregations map[uint]*aggregation // aggregations in process: one for each quantized timestamp and output key, i.e. for each output metric.
  snapReq      chan bool             // chan to issue snapshot requests on
  snapResp     chan *Aggregator      // chan on which snapshot response gets sent
  shutdown     chan struct{}         // chan used internally to shut down
  wg           sync.WaitGroup        // tracks worker running state
  now          func() time.Time      // returns current time. wraps time.Now except in some unit tests
  tick         <-chan time.Time      // controls when to flush

  Key        string
  numIn      metrics.Counter
  numFlushed metrics.Counter
}

type aggregation struct {
  count uint32
  state map[string]Processor
}

type msg struct {
  buf [][]byte
  val float64
  ts  uint32
}
```

## 横道: Aggregator の matchWithCache メソッド

`Aggregator` の `run` メソッドで呼ばれている `matchWithCache` メソッドも見てみます。

[aggregator/aggregator.go#L252-L279](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go#L252-L279)

```go
// matchWithCache returns whether there was a match, and under which key, if so.
func (a *Aggregator) matchWithCache(key []byte) (string, bool) {
  if a.reCache == nil {
    return a.Matcher.MatchRegexAndExpand(key, a.outFmt)
  }

  a.reCacheMutex.Lock()

  var outKey string
  var ok bool
  entry, ok := a.reCache[string(key)]
  if ok {
    entry.seen = uint32(a.now().Unix())
    a.reCache[string(key)] = entry
    a.reCacheMutex.Unlock()
    return entry.key, entry.match
  }

  outKey, ok = a.Matcher.MatchRegexAndExpand(key, a.outFmt)
  a.reCache[string(key)] = CacheEntry{
    ok,
    outKey,
    uint32(a.now().Unix()),
  }
  a.reCacheMutex.Unlock()

  return outKey, ok
}
```

ここでは `reCache` フィールドへのアクセスを `reCacheMutex` で排他制御しています。
`reCache` は正規表現 (Regular Expression) のキャッシュです。

## Aggregator の AddOrCreate メソッドを見返す

一方、 `AddOrCreate` メソッドを見返すと `aggregations` フィールドへのアクセスは排他制御していません。これは data race にならないのでしょうか、気になるところです。

Aggregator の 1 インスタンスの run メソッドが 1 つの goroutine からのみ呼ばれるのであれば大丈夫そうな気もします。
でもそれなら `reCacheMutex` も不要なのではないかという話もあります。

## Aggregator の run の呼び出し箇所

`Aggregator` の `NewMocked` メソッドから呼ばれています。
`NewMocked` は `New` メソッドと `aggregator_test.go` 内のテストコードから呼ばれています。
現在時刻を `time.Now()` で取得するのではなく、チャンネルで受け渡すことによってテストの際に実時間と異なる時間を指定して動かすためにこのようになっています。

[aggregator/aggregator.go#L55-L95](https://github.com/grafana/carbon-relay-ng/blob/2dc70e909221a0408ca0505759f9e8f290c1d6f9/aggregator/aggregator.go#L55-L95)

```go
// New creates an aggregator
func New(fun string, matcher matcher.Matcher, outFmt string, cache bool, interval, wait uint, dropRaw bool, out chan []byte) (*Aggregator, error) {
  ticker := clock.AlignedTick(time.Duration(interval)*time.Second, time.Duration(wait)*time.Second, 2)
  return NewMocked(fun, matcher, outFmt, cache, interval, wait, dropRaw, out, 2000, time.Now, ticker)
}

func NewMocked(fun string, matcher matcher.Matcher, outFmt string, cache bool, interval, wait uint, dropRaw bool, out chan []byte, inBuf int, now func() time.Time, tick <-chan time.Time) (*Aggregator, error) {
  procConstr, err := GetProcessorConstructor(fun)
  if err != nil {
    return nil, err
  }

  a := &Aggregator{
    Fun:          fun,
    procConstr:   procConstr,
    in:           make(chan msg, inBuf),
    out:          out,
    Matcher:      matcher,
    OutFmt:       outFmt,
    outFmt:       []byte(outFmt),
    Cache:        cache,
    Interval:     interval,
    Wait:         wait,
    DropRaw:      dropRaw,
    aggregations: make(map[uint]*aggregation),
    snapReq:      make(chan bool),
    snapResp:     make(chan *Aggregator),
    shutdown:     make(chan struct{}),
    now:          now,
    tick:         tick,
  }
  if cache {
    a.reCache = make(map[string]CacheEntry)
  }
  a.setKey()
  a.numIn = stats.Counter("unit=Metric.direction=in.aggregator=" + a.Key)
  a.numFlushed = stats.Counter("unit=Metric.direction=out.aggregator=" + a.Key)
  a.wg.Add(1)
  go a.run()
  return a, nil
}
```

でこれを見ると `Aggregator` のインスタンスごとに 1 つの goroutine で `run` メソッドを実行しています。

一方で正規表現のキャッシュですが、キャッシュを使う設定の時は `cache` が `true` になっていて `reCache` フィールドには上記で `make` で Aggregator の 1 インスタンスごとに個別の `map` を作っています。
`reCache` を参照しているのは `matchWithCache` と `run` メソッドだけですので `reCacheMutex` は不要そうな気がします。

`git log --follow -p aggregator/aggregator.go` でログを見てみると
[fix race condition in aggregator match cache · grafana/carbon-relay-ng@3939706](https://github.com/grafana/carbon-relay-ng/commit/3939706acdd577ad905b4f04cbf226ca16e417ff) で `reCacheMutex` が追加されています。
このときは `*sync.Mutex` とポインターでしたが
[cleanup & simplify · grafana/carbon-relay-ng@51a241e](https://github.com/grafana/carbon-relay-ng/commit/51a241e466aeffbef86172eaa95b6c91fd8b001e)
で `sync.Mutex` とポインターなしの型に変更されています。

この 2 つのコミットは [Cache mutex2 by Dieterbe · Pull Request #273 · grafana/carbon-relay-ng](https://github.com/grafana/carbon-relay-ng/pull/273) のプルリクエストに含まれています。
これともとになった [fix race condition in aggregator match cache by DanCech · Pull Request #271 · grafana/carbon-relay-ng](https://github.com/grafana/carbon-relay-ng/pull/271) も見てみましたが、全く説明がなく、関連するイシューも無いので背景は不明でした。

うーん、なぜ `reCache` フィールドは排他制御が必要で `aggregations` フィールドは不要なのか、謎です。
