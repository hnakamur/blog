+++
title="go-carbonのTCPレシーバについてコードリーディングしてみた"
date = "2017-04-29T11:15:00+09:00"
tags = ["go", "go-carbon"]
categories = ["blog"]
+++


## はじめに

[lomik/go-carbon: Golang implementation of Graphite/Carbon server with classic architecture: Agent -> Cache -> Persister](https://github.com/lomik/go-carbon)
のTCPレシーバについてコードを読んでみたのでメモです。

対象のコミットは
https://github.com/lomik/go-carbon/tree/42b9832d13240ff044c86768e8d0dc1f356d9458
です。

## TCPレシーバの生成

`(app *App) Start()` というメソッドの中で `receiver.New` を呼んでTCPレシーバを生成しています。

[carbon/app.go#L271-L281](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/carbon/app.go#L271-L281)

```go {linenos=table,linenostart=271}
if conf.Tcp.Enabled {
    app.TCP, err = receiver.New(
        "tcp://"+conf.Tcp.Listen,
        receiver.OutFunc(core.Add),
        receiver.BufferSize(conf.Tcp.BufferSize),
    )

    if err != nil {
        return
    }
}
```

`receiver.New` 内では `TCP` というstructのインスタンスを生成して `Listen` メソッドを呼び出しています。

[receiver/receiver.go#L110-L127](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/receiver/receiver.go#L110-L127)

```go {linenos=table,linenostart=110}
r := &TCP{
    out:    blackhole,
    name:   u.Scheme,
    logger: zapwriter.Logger(u.Scheme),
}

if u.Scheme == "pickle" {
    r.isPickle = true
    r.maxPickleMessageSize = 67108864 // 64Mb
}

for _, optApply := range opts {
    optApply(r)
}

if err = r.Listen(addr); err != nil {
    return nil, err
}
```

`TCP` の `Listen` メソッド内では `Accept` したらgoroutineを作って code:`HandleConnection` フィールドに設定されたハンドラで処理しています。

また、197行目あたりを見ると `rcv.buffer` が設定されているときは `rcv.out` に書き込まれたポイントデータをバッファリングしてから元の出力先のチャンネルに送るように変更しています。

[receiver/tcp.go#L192-L237](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/receiver/tcp.go#L192-L237)

```go {linenos=table,linenostart=192}
handler := rcv.HandleConnection
if rcv.isPickle {
    handler = rcv.handlePickle
}

if rcv.buffer != nil {
    originalOut := rcv.out

    rcv.Go(func(exit chan bool) {
        for {
            select {
            case <-exit:
                return
            case p := <-rcv.buffer:
                originalOut(p)
            }
        }
    })

    rcv.out = func(p *points.Points) {
        rcv.buffer <- p
    }
}

rcv.Go(func(exit chan bool) {
    defer tcpListener.Close()

    for {

        conn, err := tcpListener.Accept()
        if err != nil {
            if strings.Contains(err.Error(), "use of closed network connection") {
                break
            }
            rcv.logger.Warn("failed to accept connection",
                zap.Error(err),
            )
            continue
        }

        rcv.Go(func(exit chan bool) {
            handler(conn)
        })
    }

})
```

## リクエスト処理

`TCP` の `HandleConnection` の実装は以下のようになっています。
リクエストの内容を1行ずつ `points.ParseText` 関数によりパーズして、その結果を `rcv.out` に書き出しています。

[receiver/tcp.go#L49-L99](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/receiver/tcp.go#L49-L99)

```go {linenos=table,linenostart=49}
func (rcv *TCP) HandleConnection(conn net.Conn) {
    atomic.AddInt32(&rcv.active, 1)
    defer atomic.AddInt32(&rcv.active, -1)

    defer conn.Close()
    reader := bufio.NewReader(conn)

    finished := make(chan bool)
    defer close(finished)

    rcv.Go(func(exit chan bool) {
        select {
        case <-finished:
            return
        case <-exit:
            conn.Close()
            return
        }
    })

    for {
        conn.SetReadDeadline(time.Now().Add(2 * time.Minute))

        line, err := reader.ReadBytes('\n')

        if err != nil {
            if err == io.EOF {
                if len(line) > 0 {
                    rcv.logger.Warn("unfinished line", zap.String("line", string(line)))
                }
            } else {
                atomic.AddUint32(&rcv.errors, 1)
                rcv.logger.Error("read error", zap.Error(err))
            }
            break
        }
        if len(line) > 0 { // skip empty lines
            if msg, err := points.ParseText(string(line)); err != nil {
                atomic.AddUint32(&rcv.errors, 1)
                zapwriter.Logger("parser").Info("parse failed",
                    zap.Error(err),
                    zap.String("protocol", rcv.name),
                    zap.String("peer", conn.RemoteAddr().String()),
                )
            } else {
                atomic.AddUint32(&rcv.metricsReceived, 1)
                rcv.out(msg)
            }
        }
    }
}
```

`points.ParseText` 関数の定義です。 `*Points` を返しています。

[points/points.go#L125-L161](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/points/points.go#L125-L161)

```go {linenos=table,linenostart=125}
func ParseText(line string) (*Points, error) {

    row := strings.Split(strings.Trim(line, "\n \t\r"), " ")
    if len(row) != 3 {
        return nil, fmt.Errorf("bad message: %#v", line)
    }

    // 0x2e == ".". Or use split? @TODO: benchmark
    // if strings.Contains(row[0], "..") || row[0][0] == 0x2e || row[0][len(row)-1] == 0x2e {
    // 	return nil, fmt.Errorf("bad message: %#v", line)
    // }

    value, err := strconv.ParseFloat(row[1], 64)

    if err != nil || math.IsNaN(value) {
        return nil, fmt.Errorf("bad message: %#v", line)
    }

    tsf, err := strconv.ParseFloat(row[2], 64)

    if err != nil || math.IsNaN(tsf) {
        return nil, fmt.Errorf("bad message: %#v", line)
    }

    // 315522000 == "1980-01-01 00:00:00"
    // if tsf < 315532800 {
    // 	return nil, fmt.Errorf("bad message: %#v", line)
    // }

    // 4102444800 = "2100-01-01 00:00:00"
    // Hello people from the future
    // if tsf > 4102444800 {
    // 	return nil, fmt.Errorf("bad message: %#v", line)
    // }

    return OnePoint(row[0], value, int64(tsf)), nil
}
```

`Points` の定義です。

[points/points.go#L15-L25](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/points/points.go#L15-L25)

```go {linenos=table,linenostart=15}
// Point value/time pair
type Point struct {
    Value     float64
    Timestamp int64
}

// Points from carbon clients
type Points struct {
    Metric string
    Data   []Point
}
```

## rcv.outに出力した後の処理

次は `rcv.out` に出力されたデータがどう処理されるかを見ていきます。

冒頭に書いた `(app *App) Start()` というメソッドの中で `receiver.New` を呼んでTCPレシーバを生成している際に274行目で `receiver.OutFunc` に `core.Add` を指定して呼んでいます。

[carbon/app.go#L271-L281](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/carbon/app.go#L271-L281)

```go {linenos=table,linenostart=271}
if conf.Tcp.Enabled {
    app.TCP, err = receiver.New(
        "tcp://"+conf.Tcp.Listen,
        receiver.OutFunc(core.Add),
        receiver.BufferSize(conf.Tcp.BufferSize),
    )

    if err != nil {
        return
    }
}
```

`receiver.OutFunc` の定義は以下の通りで、Functional Option Patternで実装されています。
Functional Option Patternについては [Go言語のFunctional Option Pattern - Qiita](http://qiita.com/weloan/items/56f1c7792088b5ede136) やその記事の最後の原典を参照してください。

[receiver/receiver.go#L48-L59](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/receiver/receiver.go#L48-L59)

```go {linenos=table,linenostart=48}
// OutFunc creates option for New contructor
func OutFunc(out func(*points.Points)) Option {
    return func(r Receiver) error {
        if t, ok := r.(*TCP); ok {
            t.out = out
        }
        if t, ok := r.(*UDP); ok {
            t.out = out
        }
        return nil
    }
}
```

ということで `rcv.out` には `core.Add` が設定されることがわかりました。
`core` は `(app *App) Start()` というメソッド内で以下のコードで生成されるローカル変数です。

[carbon/app.go#L245-L247](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/carbon/app.go#L245-L247)

```go {linenos=table,linenostart=245}
core := cache.New()
core.SetMaxSize(conf.Cache.MaxSize)
core.SetWriteStrategy(conf.Cache.WriteStrategy)
```

`cache.New` の実装は以下のようになっています。

[cache/cache.go#L62-L79](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/cache.go#L62-L79)

```go {linenos=table,linenostart=62}
// Creates a new cache instance
func New() *Cache {
    c := &Cache{
        data:          make([]*Shard, shardCount),
        writeStrategy: Noop,
        maxSize:       1000000,
    }

    for i := 0; i < shardCount; i++ {
        c.data[i] = &Shard{
            items:        make(map[string]*points.Points),
            notConfirmed: make([]*points.Points, 4),
        }
    }

    c.writeoutQueue = NewWriteoutQueue(c)
    return c
}
```

`Cache` の構造体とそれに関連する定義は以下の通りです。
1024個の `Shard` に分けてポイントデータを保持しています。
`Shard` では `items` というmapと `notConfirmed` というsliceでポイントデータを保持しています。

[cache/cache.go#L18-L60](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/cache.go#L18-L60)

```go {linenos=table,linenostart=18}
type WriteStrategy int

const (
    MaximumLength WriteStrategy = iota
    TimestampOrder
    Noop
)

const shardCount = 1024

// A "thread" safe map of type string:Anything.
// To avoid lock bottlenecks this map is dived to several (shardCount) map shards.
type Cache struct {
    sync.Mutex

    queueLastBuild time.Time

    data []*Shard

    maxSize       int32
    writeStrategy WriteStrategy

    writeoutQueue *WriteoutQueue

    xlog atomic.Value // io.Writer

    stat struct {
        size              int32  // changing via atomic
        queueBuildCnt     uint32 // number of times writeout queue was built
        queueBuildTimeMs  uint32 // time spent building writeout queue in milliseconds
        queueWriteoutTime uint32 // in milliseconds
        overflowCnt       uint32 // drop packages if cache full
        queryCnt          uint32 // number of queries
    }
}

// A "thread" safe string to anything map.
type Shard struct {
    sync.RWMutex     // Read Write mutex, guards access to internal map.
    items            map[string]*points.Points
    notConfirmed     []*points.Points // linear search for value/slot
    notConfirmedUsed int              // search value in notConfirmed[:notConfirmedUsed]
}
```

## CacheのAddメソッド

`Cache` の `Add` メソッドは以下のようになっています。

`maxSize` フィールドに値が設定されている場合 `Cache` の `Size` メソッドの結果がそれを超える場合は `stat.OverflowCnt` の統計情報にデータ数を加えて異常終了しています。

サイズ上限を超えない場合は、入力データのメトリクス名に対応するシャードを取得し、シャード内の `items` のmapにメトリクス名のキーがある場合はmapの値のsliceにポイントデータを追加します。キーがない場合はそのキーに新たにポイントデータを設定します。

[cache/cache.go#L232-L259](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/cache.go#L232-L259)

```go {linenos=table,linenostart=232}
// Sets the given value under the specified key.
func (c *Cache) Add(p *points.Points) {
    xlog := c.xlog.Load()

    if xlog != nil {
        p.WriteTo(xlog.(io.Writer))
    }

    // Get map shard.
    count := len(p.Data)

    if c.maxSize > 0 && c.Size() > c.maxSize {
        atomic.AddUint32(&c.stat.overflowCnt, uint32(count))
        return
    }

    shard := c.GetShard(p.Metric)

    shard.Lock()
    if values, exists := shard.items[p.Metric]; exists {
        values.Data = append(values.Data, p.Data...)
    } else {
        shard.items[p.Metric] = p
    }
    shard.Unlock()

    atomic.AddInt32(&c.stat.size, int32(count))
}
```

## Cacheの内容をディスクに書き出すpersister

次は上で `Cache` に格納したポイントデータをディスクに書き出す処理を見ていきます。

`(app *App) Start()` というメソッドの中で `app.startPersister()` を呼んでpersisterを開始しています。

[carbon/app.go#L245-L253](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/carbon/app.go#L245-L253)

```go {linenos=table,linenostart=245}
core := cache.New()
core.SetMaxSize(conf.Cache.MaxSize)
core.SetWriteStrategy(conf.Cache.WriteStrategy)

app.Cache = core

/* WHISPER start */
app.startPersister()
/* WHISPER end */
```

`App` の `startPersister` メソッドの定義です。

[carbon/app.go#L211-L228](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/carbon/app.go#L211-L228)

```go {linenos=table,linenostart=211}
func (app *App) startPersister() {
    if app.Config.Whisper.Enabled {
        p := persister.NewWhisper(
            app.Config.Whisper.DataDir,
            app.Config.Whisper.Schemas,
            app.Config.Whisper.Aggregation,
            app.Cache.WriteoutQueue().GetNotConfirmed,
            app.Cache.Confirm,
        )
        p.SetMaxUpdatesPerSecond(app.Config.Whisper.MaxUpdatesPerSecond)
        p.SetSparse(app.Config.Whisper.Sparse)
        p.SetWorkers(app.Config.Whisper.Workers)

        p.Start()

        app.Persister = p
    }
}
```

`persister.NewWhisper` の関数定義です。

[persister/whisper.go#L48-L67](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/persister/whisper.go#L48-L67)

```go {linenos=table,linenostart=48}
// NewWhisper create instance of Whisper
func NewWhisper(
    rootPath string,
    schemas WhisperSchemas,
    aggregation *WhisperAggregation,
    recv func(chan bool) *points.Points,
    confirm func(*points.Points)) *Whisper {

    return &Whisper{
        recv:                recv,
        confirm:             confirm,
        schemas:             schemas,
        aggregation:         aggregation,
        workersCount:        1,
        rootPath:            rootPath,
        maxUpdatesPerSecond: 0,
        logger:              zapwriter.Logger("persister"),
        createLogger:        zapwriter.Logger("whisper:new"),
    }
}
```

`Whisper` 構造体の定義です。

[persister/whisper.go#L19-L46](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/persister/whisper.go#L19-L46)

```go {linenos=table,linenostart=19}
const storeMutexCount = 32768

type StoreFunc func(p *Whisper, values *points.Points)

// Whisper write data to *.wsp files
type Whisper struct {
    helper.Stoppable
    updateOperations    uint32
    committedPoints     uint32
    recv                func(chan bool) *points.Points
    confirm             func(*points.Points)
    schemas             WhisperSchemas
    aggregation         *WhisperAggregation
    workersCount        int
    rootPath            string
    created             uint32 // counter
    sparse              bool
    maxUpdatesPerSecond int
    throttleTicker      *ThrottleTicker
    storeMutex          [storeMutexCount]sync.Mutex
    mockStore           func() (StoreFunc, func())
    logger              *zap.Logger
    createLogger        *zap.Logger
    // blockThrottleNs        uint64 // sum ns counter
    // blockQueueGetNs        uint64 // sum ns counter
    // blockAvoidConcurrentNs uint64 // sum ns counter
    // blockUpdateManyNs      uint64 // sum ns counter
}
```

次は `NewWhisper` の呼び出しで `recv` パラメータに渡していた
`app.Cache.WriteoutQueue().GetNotConfirmed` を見て行きます。

まず `Cache` の `WriteOutQueue` メソッドは単に `writeoutQueue` フィールドの値を返すだけです。
このフィールドには上に引用した `cache/cache.go` の77行目で `NewWriteoutQueue` 関数の戻り値を設定しています。

[cache/cache.go#L301-L303](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/cache.go#L301-L303)

```go {linenos=table,linenostart=301}
func (c *Cache) WriteoutQueue() *WriteoutQueue {
    return c.writeoutQueue
}
```

`NewWriteoutQueue` 関数の定義です。

[cache/writeout_queue.go#L24-L31](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/writeout_queue.go#L24-L31)

```go {linenos=table,linenostart=24}
func NewWriteoutQueue(cache *Cache) *WriteoutQueue {
    q := &WriteoutQueue{
        cache: cache,
        queue: nil,
    }
    q.rebuild = q.makeRebuildCallback(time.Time{})
    return q
}
```

`WriteoutQueue` 構造体の定義です。

[cache/writeout_queue.go#L13-L22](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/writeout_queue.go#L13-L22)

```go {linenos=table,linenostart=13}
type WriteoutQueue struct {
    sync.RWMutex
    cache *Cache

    // Writeout queue. Usage:
    // q := <- queue
    // p := cache.Pop(q.Metric)
    queue   chan *points.Points
    rebuild func(abort chan bool) chan bool // return chan waiting for complete
}
```

`WriteoutQueue` の `makeRebuildCallback` メソッドの実装です。

[cache/writeout_queue.go#L33-L68](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/writeout_queue.go#L33-L68)

```go {linenos=table,linenostart=33}
func (q *WriteoutQueue) makeRebuildCallback(nextRebuildTime time.Time) func(chan bool) chan bool {
    var nextRebuildOnce sync.Once
    nextRebuildComplete := make(chan bool)

    nextRebuild := func(abort chan bool) chan bool {
        // next rebuild
        nextRebuildOnce.Do(func() {
            now := time.Now()
            logger := zapwriter.Logger("cache")

            logger.Debug("WriteoutQueue.nextRebuildOnce.Do",
                zap.String("now", now.String()),
                zap.String("next", nextRebuildTime.String()),
            )
            if now.Before(nextRebuildTime) {
                sleepTime := nextRebuildTime.Sub(now)
                logger.Debug("WriteoutQueue sleep before rebuild",
                    zap.String("sleepTime", sleepTime.String()),
                )

                select {
                case <-time.After(sleepTime):
                    // pass
                case <-abort:
                    // pass
                }
            }
            q.update()
            close(nextRebuildComplete)
        })

        return nextRebuildComplete
    }

    return nextRebuild
}
```

`WriteoutQueue` の `GetNotConfirmed` とそこから呼ばれる `get` の実装です。

[cache/writeout_queue.go#L79-L118](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/writeout_queue.go#L79-L118)

```go {linenos=table,linenostart=79}
func (q *WriteoutQueue) get(abort chan bool, pop func(key string) (p *points.Points, exists bool)) *points.Points {
QueueLoop:
    for {
        q.RLock()
        queue := q.queue
        rebuild := q.rebuild
        q.RUnlock()

    FetchLoop:
        for {
            select {
            case qp := <-queue:
                // pop from cache
                if p, exists := pop(qp.Metric); exists {
                    return p
                }
                continue FetchLoop
            case <-abort:
                return nil
            default:
                // queue is empty, create new
                select {
                case <-rebuild(abort):
                    // wait for rebuild
                    continue QueueLoop
                case <-abort:
                    return nil
                }
            }
        }
    }
}

func (q *WriteoutQueue) Get(abort chan bool) *points.Points {
    return q.get(abort, q.cache.Pop)
}

func (q *WriteoutQueue) GetNotConfirmed(abort chan bool) *points.Points {
    return q.get(abort, q.cache.PopNotConfirmed)
}
```

`Cache` の `Pop` メソッドと `PopNotConfirmed` メソッドの実装です。
`PopNotConfirmed` メソッドはシャードの `items` からポイントデータを取り出し、削除して `notConfirmedUsed` に追加しています。

[cache/writeout_queue.go#L261-L299](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/cache/cache.go#L261-L299)

```go {linenos=table,linenostart=261}
// Removes an element from the map and returns it
func (c *Cache) Pop(key string) (p *points.Points, exists bool) {
    // Try to get shard.
    shard := c.GetShard(key)
    shard.Lock()
    p, exists = shard.items[key]
    delete(shard.items, key)
    shard.Unlock()

    if exists {
        atomic.AddInt32(&c.stat.size, -int32(len(p.Data)))
    }

    return p, exists
}

func (c *Cache) PopNotConfirmed(key string) (p *points.Points, exists bool) {
    // Try to get shard.
    shard := c.GetShard(key)
    shard.Lock()
    p, exists = shard.items[key]
    delete(shard.items, key)

    if exists {
        if shard.notConfirmedUsed < len(shard.notConfirmed) {
            shard.notConfirmed[shard.notConfirmedUsed] = p
        } else {
            shard.notConfirmed = append(shard.notConfirmed, p)
        }
        shard.notConfirmedUsed++
    }
    shard.Unlock()

    if exists {
        atomic.AddInt32(&c.stat.size, -int32(len(p.Data)))
    }

    return p, exists
}
```

## WhisperのStartメソッド

次は上の `carbon/app.go` の224行目で呼び出している `Whisper` の `Start` メソッドを見て行きます。

[persister/whisper.go#L265-L278](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/persister/whisper.go#L265-L278)

```go {linenos=table,linenostart=265}
func (p *Whisper) Start() error {
    return p.StartFunc(func() error {

        p.throttleTicker = NewThrottleTicker(p.maxUpdatesPerSecond)

        for i := 0; i < p.workersCount; i++ {
            p.Go(func(exit chan bool) {
                p.worker(p.recv, p.confirm, exit)
            })
        }

        return nil
    })
}
```

`Whisper` の `worker` メソッドの実装です。

[persister/whisper.go#L199-L232](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/persister/whisper.go#L199-L232)

```go {linenos=table,linenostart=199}
func (p *Whisper) worker(recv func(chan bool) *points.Points, confirm func(*points.Points), exit chan bool) {
    storeFunc := store
    var doneCb func()
    if p.mockStore != nil {
        storeFunc, doneCb = p.mockStore()
    }

LOOP:
    for {
        // start := time.Now()
        select {
        case <-p.throttleTicker.C:
            // atomic.AddUint64(&p.blockThrottleNs, uint64(time.Since(start).Nanoseconds()))
            // pass
        case <-exit:
            return
        }

        // start = time.Now()
        points := recv(exit)
        // atomic.AddUint64(&p.blockQueueGetNs, uint64(time.Since(start).Nanoseconds()))
        if points == nil {
            // exit closed
            break LOOP
        }
        storeFunc(p, points)
        if doneCb != nil {
            doneCb()
        }
        if confirm != nil {
            confirm(points)
        }
    }
}
```

上記の `persister/whisper.go` の200行目で参照している `store` 関数の実装です。

[persister/whisper.go#L107-L197](https://github.com/lomik/go-carbon/blob/42b9832d13240ff044c86768e8d0dc1f356d9458/persister/whisper.go#L107-L197)

```go {linenos=table,linenostart=107}
func store(p *Whisper, values *points.Points) {
    // avoid concurrent store same metric
    // @TODO: may be flock?
    // start := time.Now()
    mutexIndex := fnv32(values.Metric) % storeMutexCount
    p.storeMutex[mutexIndex].Lock()
    // atomic.AddUint64(&p.blockAvoidConcurrentNs, uint64(time.Since(start).Nanoseconds()))
    defer p.storeMutex[mutexIndex].Unlock()

    path := filepath.Join(p.rootPath, strings.Replace(values.Metric, ".", "/", -1)+".wsp")

    w, err := whisper.Open(path)
    if err != nil {
        // create new whisper if file not exists
        if !os.IsNotExist(err) {
            p.logger.Error("failed to open whisper file", zap.String("path", path), zap.Error(err))
            return
        }

        schema, ok := p.schemas.Match(values.Metric)
        if !ok {
            p.logger.Error("no storage schema defined for metric", zap.String("metric", values.Metric))
            return
        }

        aggr := p.aggregation.match(values.Metric)
        if aggr == nil {
            p.logger.Error("no storage aggregation defined for metric", zap.String("metric", values.Metric))
            return
        }

        if err = os.MkdirAll(filepath.Dir(path), os.ModeDir|os.ModePerm); err != nil {
            p.logger.Error("mkdir failed",
                zap.String("dir", filepath.Dir(path)),
                zap.Error(err),
                zap.String("path", path),
            )
            return
        }

        w, err = whisper.CreateWithOptions(path, schema.Retentions, aggr.aggregationMethod, float32(aggr.xFilesFactor), &whisper.Options{
            Sparse: p.sparse,
        })
        if err != nil {
            p.logger.Error("create new whisper file failed",
                zap.String("path", path),
                zap.Error(err),
                zap.String("retention", schema.RetentionStr),
                zap.String("schema", schema.Name),
                zap.String("aggregation", aggr.name),
                zap.Float64("xFilesFactor", aggr.xFilesFactor),
                zap.String("method", aggr.aggregationMethodStr),
            )
            return
        }

        p.createLogger.Debug("created",
            zap.String("path", path),
            zap.String("retention", schema.RetentionStr),
            zap.String("schema", schema.Name),
            zap.String("aggregation", aggr.name),
            zap.Float64("xFilesFactor", aggr.xFilesFactor),
            zap.String("method", aggr.aggregationMethodStr),
        )

        atomic.AddUint32(&p.created, 1)
    }

    points := make([]*whisper.TimeSeriesPoint, len(values.Data))
    for i, r := range values.Data {
        points[i] = &whisper.TimeSeriesPoint{Time: int(r.Timestamp), Value: r.Value}
    }

    atomic.AddUint32(&p.committedPoints, uint32(len(values.Data)))
    atomic.AddUint32(&p.updateOperations, 1)

    defer w.Close()

    defer func() {
        if r := recover(); r != nil {
            p.logger.Error("UpdateMany panic recovered",
                zap.String("path", path),
                zap.String("traceback", fmt.Sprint(r)),
            )
        }
    }()

    // start = time.Now()
    w.UpdateMany(points)
    // atomic.AddUint64(&p.blockUpdateManyNs, uint64(time.Since(start).Nanoseconds()))
}
```

ここからは `whisper.Open` や `whisper.CreateWithOptions` や `Whisper` の `UpdateMany` メソッドを見ていくことになります。
これは
[lomik/go-whisper: A Go port of Graphite's Whisper timeseries database](https://github.com/lomik/go-whisper)
と別レポジトリになるのと、記事が長くなってきたので別記事にすることにします。

[go-whisperをコードリーディングしてみた](/blog/2017/04/29/go-whisper-code-reading/) に続きます。
