---
title: "VictoriaMetricsのデータディレクトリ構造"
date: 2019-12-30T16:19:41+09:00
---

## VictoriaMatricsのデータディレクトリの例

`sudo tree -F /var/lib/viectoriametrics` で調べたVictoriaMetricsのデータディレクトリ構造の例を以下に示します。

```text
/var/lib/victoriametrics/
├── cache/
│   ├── curr_hour_metric_ids
│   ├── metricID_metricName/
│   │   ├── data.0.bin
│   │   ├── data.1.bin
│   │   ├── data.2.bin
│   │   ├── data.3.bin
│   │   └── metadata.bin
│   ├── metricID_tsid/
│   │   ├── data.0.bin
│   │   ├── data.1.bin
│   │   ├── data.2.bin
│   │   ├── data.3.bin
│   │   └── metadata.bin
│   ├── metricName_tsid/
│   │   ├── data.0.bin
│   │   ├── data.1.bin
│   │   ├── data.2.bin
│   │   ├── data.3.bin
│   │   └── metadata.bin
│   ├── prev_hour_metric_ids
│   └── rollupResult/
│       ├── data.0.bin
│       ├── data.1.bin
│       ├── data.2.bin
│       ├── data.3.bin
│       └── metadata.bin
├── data/
│   ├── big/
│   │   ├── 2019_12/
│   │   │   ├── tmp/
│   │   │   └── txn/
│   │   └── snapshots/
│   ├── flock.lock
│   └── small/
│       ├── 2019_12/
│       │   ├── 72_36_20191223001228.000_20191225142526.000_15E3A2BA1AE90E27/
│       │   │   ├── index.bin
│       │   │   ├── metaindex.bin
│       │   │   ├── timestamps.bin
│       │   │   └── values.bin
│       │   ├── tmp/
│       │   └── txn/
│       └── snapshots/
├── flock.lock
├── indexdb/
│   ├── 15E2BB7FA24B99C4/
│   │   ├── converted-to-v1.28.0
│   │   ├── flock.lock
│   │   ├── tmp/
│   │   └── txn/
│   ├── 15E2BB7FA24B99C5/
│   │   ├── 10_1_15E2D7634FA6BCEF/
│   │   │   ├── index.bin
│   │   │   ├── items.bin
│   │   │   ├── lens.bin
│   │   │   ├── metadata.json
│   │   │   └── metaindex.bin
│   │   ├── 210_1_15E3A2BA19A1617C/
│   │   │   ├── index.bin
│   │   │   ├── items.bin
│   │   │   ├── lens.bin
│   │   │   ├── metadata.json
│   │   │   └── metaindex.bin
│   │   ├── converted-to-v1.28.0
│   │   ├── flock.lock
│   │   ├── tmp/
│   │   └── txn/
│   └── snapshots/
├── snapshots/
└── tmp/
    └── searchResults/

30 directories, 42 files
```

### cache ディレクトリ

`cache` ディレクトリ以下のデータの読み込みは以下のコードで行ってます。

[lib/storage/storage.go#L116-L121](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L116-L121)

```go
  // Load caches.
  mem := memory.Allowed()
  s.tsidCache = s.mustLoadCache("MetricName->TSID", "metricName_tsid", mem/3)
  s.metricIDCache = s.mustLoadCache("MetricID->TSID", "metricID_tsid", mem/16)
  s.metricNameCache = s.mustLoadCache("MetricID->MetricName", "metricID_metricName", mem/8)
  s.dateMetricIDCache = newDateMetricIDCache()

  hour := uint64(timestampFromTime(time.Now())) / msecPerHour
  hmCurr := s.mustLoadHourMetricIDs(hour, "curr_hour_metric_ids")
  hmPrev := s.mustLoadHourMetricIDs(hour-1, "prev_hour_metric_ids")
  s.currHourMetricIDs.Store(hmCurr)
  s.prevHourMetricIDs.Store(hmPrev)
  s.pendingHourEntries = &uint64set.Set{}
```

[app/vmselect/main.go#L33](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/app/vmselect/main.go#L33)

```go
  promql.InitRollupResultCache(*vmstorage.DataPath + "/cache/rollupResult")
```

`metricName_tsid`, `metricID_tsid`, `metricID_metricName` の3つは `s.mustLoadCache` の先を見ていくと `lib/workingsetcache` パッケージの `Load` メソッド内で [VictoriaMetrics/fastcache](https://github.com/VictoriaMetrics/fastcache) の `LoadFromFileOrNew` 関数を呼んでデータを読み込んでいることが分かります。
[lib/workingsetcache/cache.go#L53](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/workingsetcache/cache.go#L53)

`rollupResult` も `lib/workingsetcache` パッケージの `Load` メソッドまたは `New` メソッドを呼んでいるので fastcache を使っています。
[app/vmselect/promql/rollup_result_cache.go#L49-L55](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/app/vmselect/promql/rollup_result_cache.go#L49-L55)

`prev_hour_metric_ids` と `curr_hour_metric_ids` の2つは `Storage` の `mustLoadHourMetricIDs` メソッドでファイルの内容を読んでいます。
[lib/storage/storage.go#L482-L538](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L482-L538)
* 先頭の `uint64` が `isFull` 。
* 次の `uint64` が `hourLoaded` 。
* 次の `uint64` が `hmLen` で `uint64set.Set` 型のエントリ数に対応。
* その後 `hmLen` 個の `uint64` を読み取って `uint64set.Set` 型の変数 `m` に追加。

読み取ったデータから `hourMetricIDs` 構造体のインスタンスを作ってそのポインタを返しています。
[lib/storage/storage.go#L1143-L1147](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L1143-L1147)

### indexdb ディレクトリ

`indexdb` ディレクトリ以下のデータの読み込みは以下のコードで行ってます。

[lib/storage/storage.go#L130-L141](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L130-L141)

```go
  // Load indexdb
  idbPath := path + "/indexdb"
  idbSnapshotsPath := idbPath + "/snapshots"
  if err := fs.MkdirAllIfNotExist(idbSnapshotsPath); err != nil {
    return nil, fmt.Errorf("cannot create %q: %s", idbSnapshotsPath, err)
  }
  idbCurr, idbPrev, err := openIndexDBTables(idbPath, s.metricIDCache, s.metricNameCache, &s.currHourMetricIDs, &s.prevHourMetricIDs)
  if err != nil {
    return nil, fmt.Errorf("cannot open indexdb tables at %q: %s", idbPath, err)
  }
  idbCurr.SetExtDB(idbPrev)
  s.idbCurr.Store(idbCurr)
```

`openIndexDBTables` 関数
[lib/storage/storage.go#L1160-L1236](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L1160-L1236)
```go
func openIndexDBTables(path string, metricIDCache, metricNameCache *workingsetcache.Cache, currHourMetricIDs, prevHourMetricIDs *atomic.Value) (curr, prev *indexDB, err error) {
```
下記の `indexDBTableNameRegexp` にマッチするディレクトリ名でフィルタしたものをソートし、最後の1つ前を `idbPrev` （前世代）, 最後のを `idbCurr` （現世代）に読み込みます。

[lib/storage/storage.go#L1238](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L1238)
```go
var indexDBTableNameRegexp = regexp.MustCompile("^[0-9A-F]{16}$")
```

読み込みは `openIndexDB` 関数で行います。
[lib/storage/index_db.go#L151-L207](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/index_db.go#L151-L207)
```go
// openIndexDB opens index db from the given path with the given caches.
func openIndexDB(path string, metricIDCache, metricNameCache *workingsetcache.Cache, currHourMetricIDs, prevHourMetricIDs *atomic.Value) (*indexDB, error) {
```
戻り値は `lib/storage` パッケージの `indexDB` 型。
[lib/storage/index_db.go#L72-L149](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/index_db.go#L72-L149)
```go
// indexDB represents an index db.
type indexDB struct {
// …(略)…
  name string
  tb   *mergeset.Table

  extDB     *indexDB
// …(略)…
}
```

そこから `lib/mergeset` の `OpenTable` 関数が呼ばれます。
[lib/mergeset/table.go#L145-L200](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L145-L200)
```go
// OpenTable opens a table on the given path.
//
// Optional flushCallback is called every time new data batch is flushed
// to the underlying storage and becomes visible to search.
//
// Optional prepareBlock is called during merge before flushing the prepared block
// to persistent storage.
//
// The table is created if it doesn't exist yet.
func OpenTable(path string, flushCallback func(), prepareBlock PrepareBlockCallback) (*Table, error) {
```
戻り値は `lib/mergeset` パッケージの `Table` 型。
[lib/mergeset/table.go#L71-L112](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L71-L112)
```go
// Table represents mergeset table.
type Table struct {
// …(略)…
  parts     []*partWrapper
// …(略)…
}
```
`lib/mergeset` パッケージの `partWrapper` 型。
[lib/mergeset/table.go#L114-L122](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L114-L122)
```go
type partWrapper struct {
  p *part
// …(略)…
}
```
`lib/mergeset` パッケージの `part` 型。
[lib/mergeset/part.go#L61-L69](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/part.go#L61-L69)
```go
type part struct {
  partInternals
// …(略)…
}
```
`lib/mergeset` パッケージの `partInternals` 型。
[lib/mergeset/part.go#L47-L59](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/part.go#L47-L59)
```go
type partInternals struct {
  ph partHeader

  path string

  size uint64

  mrs []metaindexRow

  indexFile fs.ReadAtCloser
  itemsFile fs.ReadAtCloser
  lensFile  fs.ReadAtCloser
}
```
最後の3つのフィールドが上記のディレクトリ構成内の `index.bin`, `items.bin`, `lens`.bin` の3つのファイルに対応している。

`openFilePart` 関数で `metaindex.bin`, `index.bin`, `items.bin`, `lens.bin` の4つのファイルを開いている。
[lib/mergeset/part.go#L71-L115](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/part.go#L71-L115)

`metadata.json` ファイルは `partHeader` 構造体の `ParseFromPath` メソッド内で読み込んでいる。
[lib/mergeset/part_header.go#L82-L148](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/part_header.go#L82-L148)

### data ディレクトリ

`data` ディレクトリ以下のデータの読み込みは以下のコードで行ってます。

[lib/storage/storage.go#L143-L150](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/storage.go#L143-L150)

```go
  // Load data
  tablePath := path + "/data"
  tb, err := openTable(tablePath, retentionMonths, s.getDeletedMetricIDs)
  if err != nil {
    s.idb().MustClose()
    return nil, fmt.Errorf("cannot open table at %q: %s", tablePath, err)
  }
  s.tb = tb
```

`lib/storage` パッケージの `openTable` 関数
[lib/storage/table.go#L78-L141](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/table.go#L78-L141)
```go
// openTable opens a table on the given path with the given retentionMonths.
//
// The table is created if it doesn't exist.
//
// Data older than the retentionMonths may be dropped at any time.
func openTable(path string, retentionMonths int, getDeletedMetricIDs func() *uint64set.Set) (*table, error) {
```
ここで `small`, `small/snapshots`, `big`, `big/snapshots` の4つのディレクトリを作成後、 `openPartitions` 関数を呼んでいます。
`openTable` 関数の戻り値の `table` 型。
[lib/storage/table.go#L16-L33](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/table.go#L16-L33)
```go
// table represents a single table with time series data.
type table struct {
// …(略)…
  ptws     []*partitionWrapper
// …(略)…
}
```
`partitionWrapper` 型。
[lib/storage/table.go#L35-L46](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/table.go#L35-L46)
```go
// partitionWrapper provides refcounting mechanism for the partition.
type partitionWrapper struct {
// …(略)…
  refCount uint64
// …(略)…
  pt *partition
}
```

`openPartitions` 関数。
[lib/storage/table.go#L438-L460](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/table.go#L438-L460)
```go
func openPartitions(smallPartitionsPath, bigPartitionsPath string, getDeletedMetricIDs func() *uint64set.Set) ([]*partition, error) {
```

`openPartitions` から呼ばれる `populatePartitionNames` 関数
[lib/storage/table.go#L462-L486](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/table.go#L462-L486)
```
func populatePartitionNames(partitionsPath string, ptNames map[string]bool) error {
```
* `partitionsPath` は `small` と `big` のディレクトリでそれぞれ呼ばれる。
* `partitionsPath` 配下のディレクトリかシンボリックリンクで `snapshots` という名前は除外した一覧を `ptNames` に追加する。

`openPartitions` から呼ばれる `openPartition` 関数
[lib/storage/partition.go#L227-L263](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/partition.go#L227-L263)
```go
// openPartition opens the existing partition from the given paths.
func openPartition(smallPartsPath, bigPartsPath string, getDeletedMetricIDs func() *uint64set.Set) (*partition, error) {
```
`lib/storage` パッケージの `partition` 型。
[lib/storage/partition.go#L97-L150](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/partition.go#L97-L150)
```go
// partition represents a partition.
type partition struct {
// …(略)…
  // Name is the name of the partition in the form YYYY_MM.
  name string

  // The time range for the partition. Usually this is a whole month.
  tr TimeRange
// …(略)…
  // Contains all the inmemoryPart plus file-based parts
  // with small number of items (up to maxRowsCountPerSmallPart).
  smallParts []*partWrapper

  // Contains file-based parts with big number of items.
  bigParts []*partWrapper
// …(略)…
}
```

`openPartition` から呼ばれる `openParts` 関数
[lib/storage/partition.go#L1312-L1373](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/partition.go#L1312-L1373)
```go
func openParts(pathPrefix1, pathPrefix2, path string) ([]*partWrapper, error) {
```
戻り値の `lib/storage` パッケージの `partWrapper` 型。
[lib/storage/partition.go#L152-L168](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/partition.go#L152-L168)
```go
// partWrapper is a wrapper for the part.
type partWrapper struct {
// …(略)…
  // The number of references to the part.
  refCount uint64

  // The part itself.
  p *part
// …(略)…
}
```

`lib/storage` パッケージの `part` 型。
[lib/storage/part.go#L49-L57](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/part.go#L49-L57)
```go
// part represents a searchable part containing time series data.
type part struct {
  partInternals
// …(略)…
}
```

`lib/storage` パッケージの `partInternals` 型。
[lib/storage/part.go#L31-L47](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/part.go#L31-L47)
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
```
`timestampsFile`, `valuesFile`, `indexFile` の3つのフィールドが上記のディレクトリ構成の `timestamps.bin`,  `values.bin`, `index.bin` ファイルにそれぞれ対応。

`lib/storage` パッケージの `openFilePart` 関数で `timestamps.bin`,  `values.bin`, `index.bin`, `metaindex.bin` の4つのファイルを開いている。
[lib/storage/part.go#L59-L104](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/part.go#L59-L104)
```go
// openFilePart opens file-based part from the given path.
func openFilePart(path string) (*part, error) {
```

ファイルと読み込み箇所の対応までは追えたということで今回はここまで。
