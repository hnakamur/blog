+++
title="VictoriaMetricsにgraphite形式でデータ投入のコードリーディング"
date = "2019-12-23T22:55:00+09:00"
tags = ["victoriametrics"]
categories = ["blog"]
+++

[VictoriaMetrics/VictoriaMetrics: VictoriaMetrics - fast, cost-effective and scalable time series database, long-term remote storage for Prometheus](https://github.com/VictoriaMetrics/VictoriaMetrics) の v1.31.2 のコードリーディングのメモ。

graphite 形式で投入したデータがどう格納されるかを調べたい。


`app/vminsert/graphite` パッケージの `serveTCP` 関数から `insertHandler` 関数を呼び出している。
[app/vminsert/graphite/server.go#L101](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vminsert/graphite/server.go#L101)

その先を辿ると `pushCtx` 構造体の `InsertRows` メソッド内で `app/vminsert/common/InsertCtx` 構造体の `WriteDataPoint` メソッドを呼び出している。
[app/vminsert/graphite/request_handler.go#L54](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vminsert/graphite/request_handler.go#L54)

```go
func (ctx *pushCtx) InsertRows() error {
  rows := ctx.Rows.Rows
  ic := &ctx.Common
  ic.Reset(len(rows))
  for i := range rows {
    r := &rows[i]
    ic.Labels = ic.Labels[:0]
    ic.AddLabel("", r.Metric)
    for j := range r.Tags {
      tag := &r.Tags[j]
      ic.AddLabel(tag.Key, tag.Value)
    }
    ic.WriteDataPoint(nil, ic.Labels, r.Timestamp, r.Value)
  }
  rowsInserted.Add(len(rows))
  rowsPerInsert.Update(float64(len(rows)))
  return ic.FlushBufs()
}
```

`WriteDataPoint` メソッドの実装。

[app/vminsert/common/insert_ctx.go#L50-L65](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vminsert/common/insert_ctx.go#L50-L65)

```go
// WriteDataPoint writes (timestamp, value) with the given prefix and labels into ctx buffer.
func (ctx *InsertCtx) WriteDataPoint(prefix []byte, labels []prompb.Label, timestamp int64, value float64) {
  metricNameRaw := ctx.marshalMetricNameRaw(prefix, labels)
  ctx.addRow(metricNameRaw, timestamp, value)
}

// WriteDataPointExt writes (timestamp, value) with the given metricNameRaw and labels into ctx buffer.
//
// It returns metricNameRaw for the given labels if len(metricNameRaw) == 0.
func (ctx *InsertCtx) WriteDataPointExt(metricNameRaw []byte, labels []prompb.Label, timestamp int64, value float64) []byte {
  if len(metricNameRaw) == 0 {
    metricNameRaw = ctx.marshalMetricNameRaw(nil, labels)
  }
  ctx.addRow(metricNameRaw, timestamp, value)
  return metricNameRaw
}
```

ちなみに prometheus からデータ投入したときは `WriteDataPointExt` のほうが呼ばれる。
[app/vminsert/prometheus/request_handler.go#L46](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vminsert/prometheus/request_handler.go#L46)

`WriteDataPoint` メソッドから呼ばれる `addRow` メソッドの実装。 `ctx.mrs` に `storage.MetricRow` を追加している。
[app/vminsert/common/insert_ctx.go#L67-L79](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vminsert/common/insert_ctx.go#L67-L79)
```go
func (ctx *InsertCtx) addRow(metricNameRaw []byte, timestamp int64, value float64) {
  mrs := ctx.mrs
  if cap(mrs) > len(mrs) {
    mrs = mrs[:len(mrs)+1]
  } else {
    mrs = append(mrs, storage.MetricRow{})
  }
  mr := &mrs[len(mrs)-1]
  ctx.mrs = mrs
  mr.MetricNameRaw = metricNameRaw
  mr.Timestamp = timestamp
  mr.Value = value
}
```

`ctx.mrs` は `FlushBufs` メソッド内で `vmstorage.AddRows` メソッドを呼ぶ際の引数として渡されている。
[app/vminsert/common/insert_ctx.go#L121-L130](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vminsert/common/insert_ctx.go#L121-L130)

```go
// FlushBufs flushes buffered rows to the underlying storage.
func (ctx *InsertCtx) FlushBufs() error {
  if err := vmstorage.AddRows(ctx.mrs); err != nil {
    return &httpserver.ErrorWithStatusCode{
      Err:        fmt.Errorf("cannot store metrics: %s", err),
      StatusCode: http.StatusServiceUnavailable,
    }
  }
  return nil
}
```

`app/vmstorage` パッケージの `AddRows` 関数。
[app/vmstorage/main.go#L80-L86](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmstorage/main.go#L80-L86)
```go
// AddRows adds mrs to the storage.
func AddRows(mrs []storage.MetricRow) error {
  WG.Add(1)
  err := Storage.AddRows(mrs, uint8(*precisionBits))
  WG.Done()
  return err
}
```

`Storage` はこの少し上に定義されているグローバル変数。
[app/vmstorage/main.go#L69-L73](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/app/vmstorage/main.go#L69-L73)
```go
// Storage is a storage.
//
// Every storage call must be wrapped into WG.Add(1) ... WG.Done()
// for proper graceful shutdown when Stop is called.
var Storage *storage.Storage
```

`lib/storage` パッケージの `Storage` の `AddRows` メソッドでは `add` メソッドを呼んでいる。
[lib/storage/storage.go#L782](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/storage.go#L782)

`add` メソッドのシグネチャ。
[lib/storage/storage.go#L793](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/storage.go#L793)
```go
func (s *Storage) add(rows []rawRow, mrs []MetricRow, precisionBits uint8) ([]rawRow, error) {
```
ざっと眺めた感じ `mrs` の内容を変換して `rows` に追加した後 `s.ts.Add` メソッドを呼び出しているのがメイン。
[lib/storage/storage.go#L890](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/storage.go#L890)
```go
  if err := s.tb.AddRows(rows); err != nil {
```

`lib/storage` パッケージの `table` の `AddRows` メソッド。
[lib/storage/table.go#L244-L353](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/table.go#L244-L353)

`lib/storage` パッケージの `partition` の `AddRows` メソッド。
[lib/storage/partition.go#L380-L401](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L380-L401)

`lib/storage` パッケージの `rawRowsShards` の `addRows` メソッド。
[lib/storage/partition.go#L415-L425](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L415-L425)

`lib/storage` パッケージの `rawRowsShard` の `addRows` メソッド。
[lib/storage/partition.go#L448-L479](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L448-L479)
引数の `rows` を `rrs.rows` に追加したりしながらローカル変数の `rrss` を構築して `pt.addRowsPart` と `putRawRows` を呼ぶのがメイン。
```go
func (rrs *rawRowsShard) addRows(pt *partition, rows []rawRow) {
  var rrss []*rawRows

  rrs.lock.Lock()
  if cap(rrs.rows) == 0 {
    rrs.rows = getRawRowsMaxSize().rows
  }
  maxRowsCount := getMaxRawRowsPerPartition()
  for {
    capacity := maxRowsCount - len(rrs.rows)
    if capacity >= len(rows) {
      // Fast path - rows fit capacity.
      rrs.rows = append(rrs.rows, rows...)
      break
    }

    // Slow path - rows don't fit capacity.
    // Fill rawRows to capacity and convert it to a part.
    rrs.rows = append(rrs.rows, rows[:capacity]...)
    rows = rows[capacity:]
    rr := getRawRowsMaxSize()
    rrs.rows, rr.rows = rr.rows, rrs.rows
    rrss = append(rrss, rr)
    rrs.lastFlushTime = time.Now()
  }
  rrs.lock.Unlock()

  for _, rr := range rrss {
    pt.addRowsPart(rr.rows)
    putRawRows(rr)
  }
}
```

`lib/storage` パッケージの `partition` の `addRowsPart` メソッド。
[lib/storage/partition.go#L524-L575](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L524-L575)
```go
func (pt *partition) addRowsPart(rows []rawRow) {
```
引数の `rows` を加工・ラップして `pt.smallParts` に追加。長さの limit を超えたら `pt.mergeSmallParts` を呼び出し。

`lib/storage` パッケージの `partition` の `mergeSmallParts` メソッド。
[lib/storage/partition.go#L980-L1010](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L980-L1010)
```go
func (pt *partition) mergeSmallParts(isFinal bool) error {
```
`pt.mergeParts` の呼び出しがメイン。

`lib/storage` パッケージの `partition` の `mergeParts` メソッド。
[lib/storage/partition.go#L1014-L1174](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/partition.go#L1014-L1174)
```go
func (pt *partition) mergeParts(pws []*partWrapper, stopCh <-chan struct{}) error {
```
`mergeBlockStreams` 関数を呼び出している。

`lib/storage` パッケージの `mergeBlockStreams` 関数。
[lib/storage/merge.go#L12-L34](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/merge.go#L12-L34)
```go
func mergeBlockStreams(ph *partHeader, bsw *blockStreamWriter, bsrs []*blockStreamReader, stopCh <-chan struct{}, rowsMerged *uint64,
  deletedMetricIDs *uint64set.Set, rowsDeleted *uint64) error {
```

`mergeBlockStreamsInternal` 関数
[lib/storage/merge.go#L44-L137](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/merge.go#L44-L137)
気になるのは `pendingBlock.CopyFrom` と `mergeBlocks` と `bsw.WriteExternalBlock`。

`CopyFrom` メソッド
[lib/storage/block.go#L50-L60](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/block.go#L50-L60)
```go
// CopyFrom copies src to b.
func (b *Block) CopyFrom(src *Block) {
```

`mergeBlocks` 関数
[lib/storage/merge.go#L139-L180](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/merge.go#L139-L180)
```go
// mergeBlocks merges ib1 and ib2 to ob.
func mergeBlocks(ob, ib1, ib2 *Block) {
```

`WriteExternalBlock` メソッド
[lib/storage/block_stream_writer.go#L172-L190](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/block_stream_writer.go#L172-L190)
```go
// WriteExternalBlock writes b to bsw and updates ph and rowsMerged.
func (bsw *blockStreamWriter) WriteExternalBlock(b *Block, ph *partHeader, rowsMerged *uint64) {
```

`Block` 構造体
[lib/storage/block.go#L18-L36](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/block.go#L18-L36)
```go
// Block represents a block of time series values for a single TSID.
type Block struct {
  bh blockHeader

  // nextIdx is the next row index for timestamps and values.
  nextIdx int

  timestamps []int64
  values     []int64

  // Marshaled representation of block header.
  headerData []byte

  // Marshaled representation of timestamps.
  timestampsData []byte

  // Marshaled representation of values.
  valuesData []byte
}
```

`BlockHeader` 構造体
[lib/storage/block_header.go#L11-L80](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/block_header.go#L11-L80)
```go
// blockHeader is a header for a time series block.
//
// Each block contains rows for a single time series. Rows are sorted
// by timestamp.
//
// A single time series may span multiple blocks.
type blockHeader struct {
  // TSID is the TSID for the block.
  // Multiple blocks may have the same TSID.
  TSID TSID

  // MinTimestamp is the minimum timestamp in the block.
  //
  // This is the first timestamp, since rows are sorted by timestamps.
  MinTimestamp int64

  // MaxTimestamp is the maximum timestamp in the block.
  //
  // This is the last timestamp, since rows are sorted by timestamps.
  MaxTimestamp int64

  // FirstValue is the first value in the block.
  //
  // It is stored here for better compression level, since usually
  // the first value significantly differs from subsequent values
  // which may be delta-encoded.
  FirstValue int64

  // TimestampsBlockOffset is the offset in bytes for a block
  // with timestamps in timestamps file.
  TimestampsBlockOffset uint64

  // ValuesBlockOffset is the offset in bytes for a block with values
  // in values file.
  ValuesBlockOffset uint64

  // TimestampsBlocksSize is the size in bytes for a block with timestamps.
  TimestampsBlockSize uint32

  // ValuesBlockSize is the size in bytes for a block with values.
  ValuesBlockSize uint32

  // RowsCount is the number of rows in the block.
  //
  // The block must contain at least one row.
  RowsCount uint32

  // Scale is the 10^Scale multiplier for values in the block.
  Scale int16

  // TimestampsMarshalType is the marshal type used for marshaling
  // a block with timestamps.
  TimestampsMarshalType encoding.MarshalType

  // ValuesMarshalType is the marshal type used for marshaling
  // a block with values.
  ValuesMarshalType encoding.MarshalType

  // PrecisionBits is the number of significant bits when using
  // MarshalTypeNearestDelta2 encoding.
  //
  // Possible values are in the range [1...64], where
  //     1 means max 50% error,
  //     2 means max 25% error,
  //     n means max 100/(2^n)% error,
  //    64 means exact values.
  //
  // Lower PrecisionBits give better block compression and speed.
  PrecisionBits uint8
}
```

今回はここまで。
