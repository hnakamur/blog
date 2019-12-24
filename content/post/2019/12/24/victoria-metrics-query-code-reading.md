+++
title="VictoriaMetricsのクエリのコードリーディング"
date = "2019-12-24T08:25:00+09:00"
tags = ["victoriametrics"]
categories = ["blog"]
+++

[VictoriaMetrics/VictoriaMetrics: VictoriaMetrics - fast, cost-effective and scalable time series database, long-term remote storage for Prometheus](https://github.com/VictoriaMetrics/VictoriaMetrics) の v1.31.2 のコードリーディングのメモ。

今回は Prometheus QL 互換のクエリ回りを見る。

## メイン

メインのリクエストハンドラ。
[app/victoria-metrics/main.go#L52-L63](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/victoria-metrics/main.go#L52-L63)
```go
func requestHandler(w http.ResponseWriter, r *http.Request) bool {
  if vminsert.RequestHandler(w, r) {
    return true
  }
  if vmselect.RequestHandler(w, r) {
    return true
  }
  if vmstorage.RequestHandler(w, r) {
    return true
  }
  return false
}
```

`vmselect.RequestHandler`
[app/vmselect/main.go#L57-L199](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/main.go#L57-L199)

## ラベルバリューのクエリ

Prometheus のドキュメント: [Querying label values](https://prometheus.io/docs/prometheus/latest/querying/api/#querying-label-values)

grafana で VictoriaMetrics を Prometheus のデータソースとして登録してグラフを見た時は `/api/v1/label/__name__/values` というパスで呼ばれて
```json
{"status":"success","data":["foo.bar.baz"]}
```
といったレスポンスが返っていました。

VictoriaMetrics の実装: [app/vmselect/main.go#L83-L97](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/main.go#L83-L97)

`app/vmselect/prometheus` パッケージの `LabelValuesHandler` 関数
[app/vmselect/prometheus/prometheus.go#L234-L279](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/prometheus/prometheus.go#L234-L279)

```go
// LabelValuesHandler processes /api/v1/label/<labelName>/values request.
//
// See https://prometheus.io/docs/prometheus/latest/querying/api/#querying-label-values
func LabelValuesHandler(labelName string, w http.ResponseWriter, r *http.Request) error {
```

`app/vmselect/netstorage` パッケージの `GetLabelValues` 関数
[app/vmselect/netstorage/netstorage.go#L398-L415](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/netstorage/netstorage.go#L398-L415)
```go
// GetLabelValues returns label values for the given labelName
// until the given deadline.
func GetLabelValues(labelName string, deadline Deadline) ([]string, error) {
```

`app/vmstorage` パッケージの `SearchTagValues` 関数
[app/vmstorage/main.go#L106-L112](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmstorage/main.go#L106-L112)
```go
// SearchTagValues searches for tag values for the given tagKey
func SearchTagValues(tagKey []byte, maxTagValues int) ([]string, error) 
```

`lib/storage` パッケージの `Storage` の `SearchTagValues` メソッド
[lib/storage/storage.go#L644-L647](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/storage.go#L644-L647)
```go
// SearchTagValues searches for tag values for the given tagKey
func (s *Storage) SearchTagValues(tagKey []byte, maxTagValues int) ([]string, error) {
```
`Storage` 構造体
[lib/storage/storage.go#L30-L78](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/storage.go#L30-L78)
```go
// Storage represents TSDB storage.
type Storage struct {
…(略)…
  path            string
  cachePath       string
  retentionMonths int

  // lock file for exclusive access to the storage on the given path.
  flockF *os.File

  idbCurr atomic.Value

  tb *table
…(略)…
}
```
`table` 構造体
[lib/storage/table.go#L16-L33](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/table.go#L16-L33)
```go
// table represents a single table with time series data.
type table struct {
  path                string
  smallPartitionsPath string
  bigPartitionsPath   string

  getDeletedMetricIDs func() *uint64set.Set

  ptws     []*partitionWrapper
  ptwsLock sync.Mutex

  flockF *os.File

  stop chan struct{}

  retentionMilliseconds int64
  retentionWatcherWG    sync.WaitGroup
}
```
`partitionWrapper` 構造体
[lib/storage/table.go#L35-L46](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/table.go#L35-L46)
```go
// partitionWrapper provides refcounting mechanism for the partition.
type partitionWrapper struct {
  // Atomic counters must be at the top of struct for proper 8-byte alignment on 32-bit archs.
  // See https://github.com/VictoriaMetrics/VictoriaMetrics/issues/212

  refCount uint64

  // The partition must be dropped if mustDrop > 0
  mustDrop uint64

  pt *partition
}
```
`partition` 構造体
[lib/storage/partition.go#L97-L150](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L97-L150)
```go
// partition represents a partition.
type partition struct {
…(略)…
  mergeIdx uint64

  smallPartsPath string
  bigPartsPath   string

  // The callack that returns deleted metric ids which must be skipped during merge.
  getDeletedMetricIDs func() *uint64set.Set

  // Name is the name of the partition in the form YYYY_MM.
  name string

  // The time range for the partition. Usually this is a whole month.
  tr TimeRange
…(略)…
  // Contains all the inmemoryPart plus file-based parts
  // with small number of items (up to maxRowsCountPerSmallPart).
  smallParts []*partWrapper

  // Contains file-based parts with big number of items.
  bigParts []*partWrapper

  // rawRows contains recently added rows that haven't been converted into parts yet.
  //
  // rawRows aren't used in search for performance reasons.
  rawRows rawRowsShards
…(略)…
}
```
`partWrapper` 構造体
[lib/storage/partition.go#L152-L168](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L152-L168)
```go
// partWrapper is a wrapper for the part.
type partWrapper struct {
  // Put atomic counters to the top of struct, so they are aligned to 8 bytes on 32-bit arch.
  // See https://github.com/VictoriaMetrics/VictoriaMetrics/issues/212

  // The number of references to the part.
  refCount uint64

  // The part itself.
  p *part

  // non-nil if the part is inmemoryPart.
  mp *inmemoryPart

  // Whether the part is in merge now.
  isInMerge bool
}
```
`part` と `partInternals` 構造体
[lib/storage/part.go#L31-L57](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/part.go#L31-L57)
```go

type partInternals struct {
  ph partHeader

  // Filesystem path to the part.
  //
  // Empty for in-memory part.
  path string

  // Total size in bytes of part data.
  size uint64

  timestampsFile fs.ReadAtCloser
  valuesFile     fs.ReadAtCloser
  indexFile      fs.ReadAtCloser

  metaindex []metaindexRow
}

// part represents a searchable part containing time series data.
type part struct {
  partInternals

  // Align ibCache to 8 bytes in order to align internal counters on 32-bit architectures.
  // See https://github.com/VictoriaMetrics/VictoriaMetrics/issues/212
  _       [(8 - (unsafe.Sizeof(partInternals{}) % 8)) % 8]byte
  ibCache indexBlockCache
}
```
`partHeader` 構造体
[lib/storage/part_header.go#L11-L24](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/part_header.go#L11-L24)
```go
// partHeader represents part header.
type partHeader struct {
  // RowsCount is the total number of rows in the part.
  RowsCount uint64

  // BlocksCount is the total number of blocks in the part.
  BlocksCount uint64

  // MinTimestamp is the minimum timestamp in the part.
  MinTimestamp int64

  // MaxTimestamp is the maximum timestamp in the part.
  MaxTimestamp int64
}
```

`lib/storage` パッケージの `indexDB` の `SearchTagValues` メソッド
[lib/storage/index_db.go#L784-L811](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/index_db.go#L784-L811)
```go
// SearchTagValues returns all the tag values for the given tagKey
func (db *indexDB) SearchTagValues(tagKey []byte, maxTagValues int) ([]string, error) {
```

`lib/storage` パッケージの `indexSearch` の `searchTagValues` メソッド
[lib/storage/index_db.go#L813-L857](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/index_db.go#L813-L857)
```go
func (is *indexSearch) searchTagValues(tvs map[string]struct{}, tagKey []byte, maxTagValues int) error {
```
`tagKey` の箇所にシークしてタグを最大 `maxTagValues` 個まで `tvs` のキーに入れる。


`lib/mergeset` パッケージの `TableSearch` の `Seek` メソッド
[lib/mergeset/table_search.go#L83-L117](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/table_search.go#L83-L117)
```go
// Seek seeks for the first item greater or equal to k in the ts.
func (ts *TableSearch) Seek(k []byte) {
```

`lib/mergeset` パッケージの `partSearch` の `Seek` メソッド
[lib/mergeset/part_search.go#L89-L182](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/part_search.go#L89-L182)
```go
// Seek seeks for the first item greater or equal to k in ps.
func (ps *partSearch) Seek(k []byte) {
```

### 関連する型

`lib/mergeset` パッケージの `partSearch` 構造体
[lib/mergeset/part_search.go#L13-L49](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/part_search.go#L13-L49)

`lib/mergeset` パッケージの `partInternals` と `part` 構造体
[lib/mergeset/part.go#L47-L69](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/part.go#L47-L69)

`lib/mergeset` パッケージの `metaindexRow` 構造体
[lib/mergeset/metaindex_row.go#L12-L26](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/metaindex_row.go#L12-L26)

`lib/storage` パッケージの `indexBlock` 構造体
[lib/storage/part.go#L158-L160](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/part.go#L158-L160)
```go
type indexBlock struct {
  bhs []blockHeader
}
```

`lib/mergeset` パッケージの `blockHeader` 構造体
[lib/mergeset/block_header.go#L11-L35](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/block_header.go#L11-L35)


`lib/mergeset` パッケージの `inmemoryBlock` 構造体と `byteSliceSorter` 型
[lib/mergeset/encoding.go#L15-L29](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/mergeset/encoding.go#L15-L29)

## レンジクエリ

Prometheus のドキュメント: [Range queries](https://prometheus.io/docs/prometheus/latest/querying/api/#range-queries)

grafana で VictoriaMetrics を Prometheus のデータソースとして登録してグラフを見た時は `/api/v1/query_range?query=foo.bar.baz&start=1577150160&end=1577153760&step=15` というパスで呼ばれて
```json
{"JSON":{"status":"success","data":{"resultType":"matrix","result":[{"metric":{"__name__":"foo.bar.baz","tag1":"value1","tag2":"value2"},"values":[[1577059950,"123"],[1577059965,"123"],…(略)…,[1577060700,"130"],[1577060715,"130"],…(略)…,[1577061540,"130"]]}]}}
```
といったレスポンスが返っていました。

VictoriaMetrics の実装: [app/vmselect/main.go#L109-L117](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/main.go#L109-L117)

`app/vmselect/prometheus` パッケージの `QueryRangeHandler` 関数
[app/vmselect/prometheus/prometheus.go#L647-L675](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/prometheus/prometheus.go#L647-L675)

`app/vmselect/prometheus` パッケージの `queryRangeHandler` 関数
[app/vmselect/prometheus/prometheus.go#L677-L723](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/prometheus/prometheus.go#L677-L723)

`app/vmselect/promql` パッケージの `Exec` 関数
[app/vmselect/promql/exec.go#L32-L86](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/exec.go#L32-L86)
```go
// Exec executes q for the given ec.
func Exec(ec *EvalConfig, q string, isFirstPointOnly bool) ([]netstorage.Result, error) {
```

`app/vmselect/promql` パッケージの `evalExpr` 関数
[app/vmselect/promql/eval.go#L147-L271](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/eval.go#L147-L271)
```go
func evalExpr(ec *EvalConfig, e expr) ([]*timeseries, error) {
```

`app/vmselect/promql` パッケージの `evalRollupFunc` 関数
[app/vmselect/promql/eval.go#L397-L436](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/eval.go#L397-L436)
```go
func evalRollupFunc(ec *EvalConfig, name string, rf rollupFunc, re *rollupExpr, iafc *incrementalAggrFuncContext) ([]*timeseries, error) {
```

`app/vmselect/promql` パッケージの `evalRollupFuncWithMetricExpr` 関数
[app/vmselect/promql/eval.go#L547-L636](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/eval.go#L547-L636)
```go
func evalRollupFuncWithMetricExpr(ec *EvalConfig, name string, rf rollupFunc, me *metricExpr, iafc *incrementalAggrFuncContext, windowStr string) ([]*timeseries, error) {
```

`app/vmselect/netstorage` パッケージの `ProcessSearchQuery` 関数
[app/vmselect/netstorage/netstorage.go#L468-L539](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/netstorage/netstorage.go#L468-L539)
```go
// ProcessSearchQuery performs sq on storage nodes until the given deadline.
func ProcessSearchQuery(sq *storage.SearchQuery, fetchData bool, deadline Deadline) (*Results, error) {
```
`app/vmselect/netstorage` パッケージの `Result` 構造体
[app/vmselect/netstorage/netstorage.go#L50-L59](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/netstorage/netstorage.go#L50-L59)
```go
// Results holds results returned from ProcessSearchQuery.
type Results struct {
  tr        storage.TimeRange
  fetchData bool
  deadline  Deadline

  tbf *tmpBlocksFile

  packedTimeseries []packedTimeseries
}
```
`packedTimeseries` 構造体
[app/vmselect/netstorage/netstorage.go#L157-L160](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/netstorage/netstorage.go#L157-L160)
```go
type packedTimeseries struct {
  metricName string
  addrs      []tmpBlockAddr
}
```
`tmpBlockAddr` 構造体
[app/vmselect/netstorage/tmp_blocks_file.go#L74-L77](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/netstorage/tmp_blocks_file.go#L74-L77)
```go
type tmpBlockAddr struct {
  offset uint64
  size   int
}
```

`lib/storage` パッケージの `Search` の `Init` メソッド
[lib/storage/search.go#L103-L127](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/search.go#L103-L127)
```go
// Init initializes s from the given storage, tfss and tr.
//
// MustClose must be called when the search is done.
func (s *Search) Init(storage *Storage, tfss []*TagFilters, tr TimeRange, fetchData bool, maxMetrics int) {
```
`Search` 構造体
[lib/storage/search.go#L79-L91](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/search.go#L79-L91)
```go
// Search is a search for time series.
type Search struct {
  // MetricBlock is updated with each Search.NextMetricBlock call.
  MetricBlock MetricBlock

  storage *Storage

  ts tableSearch

  err error

  needClosing bool
}
```

`evalRollupWithIncrementalAggregate` 関数
[app/vmselect/promql/eval.go#L650-L671](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/eval.go#L650-L671)
```go
func evalRollupWithIncrementalAggregate(iafc *incrementalAggrFuncContext, rss *netstorage.Results, rcs []*rollupConfig,
  preFunc func(values []float64, timestamps []int64), sharedTimestamps []int64, removeMetricGroup bool) ([]*timeseries, error) {
  err := rss.RunParallel(func(rs *netstorage.Result, workerID uint) {
    preFunc(rs.Values, rs.Timestamps)
    ts := getTimeseries()
    defer putTimeseries(ts)
    for _, rc := range rcs {
      ts.Reset()
      doRollupForTimeseries(rc, ts, &rs.MetricName, rs.Values, rs.Timestamps, sharedTimestamps, removeMetricGroup)
      iafc.updateTimeseries(ts, workerID)

      // ts.Timestamps points to sharedTimestamps. Zero it, so it can be re-used.
      ts.Timestamps = nil
      ts.denyReuse = false
    }
  })
  if err != nil {
    return nil, err
  }
  tss := iafc.finalizeTimeseries()
  return tss, nil
}
```
`doRollupForTimeseries` 関数
[app/vmselect/promql/eval.go#L693-L705](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/eval.go#L693-L705)
```go
func doRollupForTimeseries(rc *rollupConfig, tsDst *timeseries, mnSrc *storage.MetricName, valuesSrc []float64, timestampsSrc []int64,
  sharedTimestamps []int64, removeMetricGroup bool) {
  tsDst.MetricName.CopyFrom(mnSrc)
  if len(rc.TagValue) > 0 {
    tsDst.MetricName.AddTag("rollup", rc.TagValue)
  }
  if removeMetricGroup {
    tsDst.MetricName.ResetMetricGroup()
  }
  tsDst.Values = rc.Do(tsDst.Values[:0], valuesSrc, timestampsSrc)
  tsDst.Timestamps = sharedTimestamps
  tsDst.denyReuse = true
}
```
`rollupConfig` 構造体と `rollupFunc` 型
[app/vmselect/promql/rollup.go#L133-L159](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmselect/promql/rollup.go#L133-L159)
```go
// rollupFunc must return rollup value for the given rfa.
//
// prevValue may be nan, values and timestamps may be empty.
type rollupFunc func(rfa *rollupFuncArg) float64

type rollupConfig struct {
  // This tag value must be added to "rollup" tag if non-empty.
  TagValue string

  Func   rollupFunc
  Start  int64
  End    int64
  Step   int64
  Window int64

  // Whether window may be adjusted to 2 x interval between data points.
  // This is needed for functions which have dt in the denominator
  // such as rate, deriv, etc.
  // Without the adjustement their value would jump in unexpected directions
  // when using window smaller than 2 x scrape_interval.
  MayAdjustWindow bool

  Timestamps []int64

  // LoookbackDelta is the analog to `-query.lookback-delta` from Prometheus world.
  LookbackDelta int64
}
```

`lib/storage` パッケージの `tableSearch` の `Init` メソッド
[lib/storage/table_search.go#L55-L120](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/table_search.go#L55-L120)
```go
// Init initializes the ts.
//
// tsids must be sorted.
// tsids cannot be modified after the Init call, since it is owned by ts.
//
// MustClose must be called then the tableSearch is done.
func (ts *tableSearch) Init(tb *table, tsids []TSID, tr TimeRange, fetchData bool) {
```

今回はこのへんで。
