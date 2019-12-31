---
title: "VictoriaMetricsのマージに関してコードリーディング"
date: 2020-01-01T22:07:52+09:00
draft: true
---

## はじめに
READMEの [Troubleshooting](https://github.com/VictoriaMetrics/VictoriaMetrics#troubleshooting) からリンクされている [How VictoriaMetrics makes instant snapshots for multi-terabyte time series data](https://medium.com/@valyala/how-victoriametrics-makes-instant-snapshots-for-multi-terabyte-time-series-data-e1f3fb0e0282) の記事によると VictoriaMetrics は ClickHouse の [MergeTree](https://clickhouse.yandex/docs/en/development/architecture/#merge-tree) と似たデータ構造を採用しているそうです。

VictoriaMetrics では時系列データを MergeTree のような構造のテーブルに格納しています。
また [時系列セレクタ](https://prometheus.io/docs/prometheus/latest/querying/basics/#time-series-selectors) から高速にルックアップするための逆索引を mergeset に格納していてこれも MergeTree を参考にした構造になっているとのことです。

MergeTree に含まれる `part` は部分的に作成されることは無く、一旦作成したら変更はされない immutable なものになっています。これにより atomicity を実現しているそうです。

Rows are split into moderately sized blocks とその次の Blocks are merged into "parts" のセクションによると、 VictoriaMetrics のデータ行は block に分割され複数の block が parts にマージされるとのことです。

今回はこのマージについてコードリーディングします。

## lib/mergeset パッケージ

`OpenTable` 関数内で `Table` 型の `startPartMergers` メソッド呼び出し
[lib/mergeset/table.go#L176-L186](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L176-L186)
```go
  tb := &Table{
    path:          path,
    flushCallback: flushCallback,
    prepareBlock:  prepareBlock,
    parts:         pws,
    mergeIdx:      uint64(time.Now().UnixNano()),
    flockF:        flockF,
    stopCh:        make(chan struct{}),
  }
  tb.startPartMergers()
  tb.startRawItemsFlusher()
```

`Table` 型の `startPartMergers` メソッド
[lib/mergeset/table.go#L635-L645](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L635-L645)
```go
func (tb *Table) startPartMergers() {
  for i := 0; i < mergeWorkersCount; i++ {
    tb.partMergersWG.Add(1)
    go func() {
      if err := tb.partMerger(); err != nil {
        logger.Panicf("FATAL: unrecoverable error when merging parts in %q: %s", tb.path, err)
      }
      tb.partMergersWG.Done()
    }()
  }
}
```

`Table` 型の `partMerger` メソッドとそこから参照している定数とエラー変数
[lib/mergeset/table.go#L660-L706](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L660-L706)
```go
const (
  minMergeSleepTime = time.Millisecond
  maxMergeSleepTime = time.Second
)

func (tb *Table) partMerger() error {
  sleepTime := minMergeSleepTime
  var lastMergeTime time.Time
  isFinal := false
  t := time.NewTimer(sleepTime)
  for {
    err := tb.mergeExistingParts(isFinal)
    if err == nil {
      // Try merging additional parts.
      sleepTime = minMergeSleepTime
      lastMergeTime = time.Now()
      isFinal = false
      continue
    }
    if err == errForciblyStopped {
      // The merger has been stopped.
      return nil
    }
    if err != errNothingToMerge {
      return err
    }
    if time.Since(lastMergeTime) > 30*time.Second {
      // We have free time for merging into bigger parts.
      // This should improve select performance.
      lastMergeTime = time.Now()
      isFinal = true
      continue
    }

    // Nothing to merge. Sleep for a while and try again.
    sleepTime *= 2
    if sleepTime > maxMergeSleepTime {
      sleepTime = maxMergeSleepTime
    }
    select {
    case <-tb.stopCh:
      return nil
    case <-t.C:
      t.Reset(sleepTime)
    }
  }
}

var errNothingToMerge = fmt.Errorf("nothing to merge")
```
* まず `mergeExistingParts` メソッドを呼ぶ。
* 戻り値の `err` が `nil` なら再度呼ぶ。
* 戻り値の `err` が `errForciblyStopped` なら終了。
* 戻り値の `err` が `errNothingToMerge` 以外なら異常終了。
* 戻り値の `err` が `errNothingToMerge` のときは待ち時間を倍にしてsleepしたのち `mergeExistingParts` メソッドを呼ぶ。待ち時間は初回は 2ms で最大 1s。前回のマージから30sを超えた場合は `isFinal` を `true` にして `mergeExistingParts` メソッドを呼ぶ。

`Table` 型の `mergeExistingParts` メソッド
[lib/mergeset/table.go#L647-L658](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L647-L658)
```go
func (tb *Table) mergeExistingParts(isFinal bool) error {
  maxItems := tb.maxOutPartItems()
  if maxItems > maxItemsPerPart {
    maxItems = maxItemsPerPart
  }

  tb.partsLock.Lock()
  pws := getPartsToMerge(tb.parts, maxItems, isFinal)
  tb.partsLock.Unlock()

  return tb.mergeParts(pws, tb.stopCh, false)
}
```

`Table` 型の `maxOutPartItems` メソッドと関連する変数とメソッド
[lib/mergeset/table.go#L882-L907](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L882-L907)
```go
var (
  maxOutPartItemsLock     sync.Mutex
  maxOutPartItemsDeadline time.Time
  lastMaxOutPartItems     uint64
)

func (tb *Table) maxOutPartItems() uint64 {
  maxOutPartItemsLock.Lock()
  if time.Until(maxOutPartItemsDeadline) < 0 {
    lastMaxOutPartItems = tb.maxOutPartItemsSlow()
    maxOutPartItemsDeadline = time.Now().Add(time.Second)
  }
  n := lastMaxOutPartItems
  maxOutPartItemsLock.Unlock()
  return n
}

func (tb *Table) maxOutPartItemsSlow() uint64 {
  freeSpace := fs.MustGetFreeSpace(tb.path)

  // Calculate the maximum number of items in the output merge part
  // by dividing the freeSpace by 4 and by the number of concurrent
  // mergeWorkersCount.
  // This assumes each item is compressed into 4 bytes.
  return freeSpace / uint64(mergeWorkersCount) / 4
}
```
* `maxOutPartItems` メソッドが初回呼ばれたときは `maxOutPartItemsDeadline` がゼロ値なので `if time.Until(maxOutPartItemsDeadline) < 0` のブロックに入り `maxOutPartItemsSlow` メソッドが呼ばれる。`maxOutPartItemsDeadline` が現在時刻の1秒後に設定されるので、2回目以降の `maxOutPartItems` 呼び出しで前回から1秒以上経っていれば `if` ブロックが実行される。

`lib/fs` パッケージの `MustGetFreeSpace` 関数
[lib/fs/fs.go#L357-L372](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/fs/fs.go#L357-L372)
```go
// MustGetFreeSpace returns free space for the given directory path.
func MustGetFreeSpace(path string) uint64 {
  d, err := os.Open(path)
  if err != nil {
    logger.Panicf("FATAL: cannot determine free disk space on %q: %s", path, err)
  }
  defer MustClose(d)

  fd := d.Fd()
  var stat unix.Statfs_t
  if err := unix.Fstatfs(int(fd), &stat); err != nil {
    logger.Panicf("FATAL: cannot determine free disk space on %q: %s", path, err)
  }
  freeSpace := uint64(stat.Bavail) * uint64(stat.Bsize)
  return freeSpace
}
```
* `path` 引数のパスを含むパーティションの空き容量をバイト単位で返す。
* 参考: [fstatfs (2)](https://manpages.ubuntu.com/manpages/bionic/en/man2/fstatfs.2.html)

`getPartsToMerge` 関数。 `Table` 型の `mergeExistingParts` メソッドから呼ばれる。
[lib/mergeset/table.go#L1200-L1229](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/table.go#L1200-L1229)
```go
// getPartsToMerge returns optimal parts to merge from pws.
//
// if isFinal is set, then merge harder.
//
// The returned parts will contain less than maxItems items.
func getPartsToMerge(pws []*partWrapper, maxItems uint64, isFinal bool) []*partWrapper {
  pwsRemaining := make([]*partWrapper, 0, len(pws))
  for _, pw := range pws {
    if !pw.isInMerge {
      pwsRemaining = append(pwsRemaining, pw)
    }
  }
  maxPartsToMerge := defaultPartsToMerge
  var dst []*partWrapper
  if isFinal {
    for len(dst) == 0 && maxPartsToMerge >= finalPartsToMerge {
      dst = appendPartsToMerge(dst[:0], pwsRemaining, maxPartsToMerge, maxItems)
      maxPartsToMerge--
    }
  } else {
    dst = appendPartsToMerge(dst[:0], pwsRemaining, maxPartsToMerge, maxItems)
  }
  for _, pw := range dst {
    if pw.isInMerge {
      logger.Panicf("BUG: partWrapper.isInMerge is already set")
    }
    pw.isInMerge = true
  }
  return dst
}
```

## 旧コードリーディング

`merge.go` という名前のファイルが以下の2つあったのでこれらを見ていきます。

* [lib/mergeset/merge.go](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go)
* [lib/storage/merge.go](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/storage/merge.go)

### lib/mergeset パッケージ

`lib/mergeset` パッケージの `mergeBlockStreams` 関数
[lib/mergeset/merge.go#L21-L46](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L21-L46)
```go
// mergeBlockStreams merges bsrs and writes result to bsw.
//
// It also fills ph.
//
// prepareBlock is optional.
//
// The function immediately returns when stopCh is closed.
//
// It also atomically adds the number of items merged to itemsMerged.
func mergeBlockStreams(ph *partHeader, bsw *blockStreamWriter, bsrs []*blockStreamReader, prepareBlock PrepareBlockCallback, stopCh <-chan struct{}, itemsMerged *uint64) error {
```
`sync.Pool` から `blockStreamMerger` を取得して `Merge` メソッドを呼んでいます。

`blockStreamMerger` 構造体
[lib/mergeset/merge.go#L54-L68](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L54-L68)
```go
type blockStreamMerger struct {
  prepareBlock PrepareBlockCallback

  bsrHeap bsrHeap

  // ib is a scratch block with pending items.
  ib inmemoryBlock

  phFirstItemCaught bool

  // This are auxiliary buffers used in flushIB
  // for consistency checks after prepareBlock call.
  firstItem []byte
  lastItem  []byte
}
```

`lib/mergeset` パッケージの `bsrHeap` 型の定義
[lib/mergeset/merge.go#L198](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L198)
```go
type bsrHeap []*blockStreamReader
```

`bsrHeap` 型のメソッド群
[lib/mergeset/merge.go#L200-L224](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L200-L224)
ソートに使う `Len`, `Swap`, `Less` メソッドと、最後の要素を取り出す `Pop` メソッド、最後に要素を追加する `Push` メソッドが定義されている。
これらは Go 標準ライブラリの [container/heap.Interface](https://golang.org/pkg/container/heap/#Interface) インタフェースの実装になっていて `blockStreamMerger` の `Merge` メソッド内で [heap.Pop](https://golang.org/pkg/container/heap/#Pop) や [heap.Push](https://golang.org/pkg/container/heap/#Push) 関数が呼ばれている。

`lib/mergeset` パッケージの `blockStreamReader` 型
[lib/mergeset/block_stream_reader.go#L16-L65](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/block_stream_reader.go#L16-L65)
```go
type blockStreamReader struct {
  // Block contains the current block if Next returned true.
  Block inmemoryBlock

  blockItemIdx int

  path string

  // ph contains partHeader for the read part.
  ph partHeader

  // All the metaindexRows.
  // The blockStreamReader doesn't own mrs - it must be alive
  // during the read.
  mrs []metaindexRow

  // The index for the currently processed metaindexRow from mrs.
  mrIdx int

  // Currently processed blockHeaders.
  bhs []blockHeader

  // The index of the currently processed blockHeader.
  bhIdx int

  indexReader filestream.ReadCloser
  itemsReader filestream.ReadCloser
  lensReader  filestream.ReadCloser

  // Contains the current blockHeader.
  bh *blockHeader

  // Contains the current storageBlock.
  sb storageBlock

  // The number of items read so far.
  itemsRead uint64

  // The number of blocks read so far.
  blocksRead uint64

  // Whether the first item in the reader checked with ph.firstItem.
  firstItemChecked bool

  packedBuf   []byte
  unpackedBuf []byte

  // The last error.
  err error
}
```
`bsrHeap` 型の `Less` メソッドでは `blockStreamReader` 型の `bh` フィールドの `firstItem` の昇順の比較になっていたので `heap.Pop` が呼ばれると `bsrHeap` 内で `bh` の `firstItem` が一番小さいものが返されることになる。

`blockStreamMerger` の `Merge` メソッド
[lib/mergeset/merge.go#L105-L156](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L105-L156)
```go
func (bsm *blockStreamMerger) Merge(bsw *blockStreamWriter, ph *partHeader, stopCh <-chan struct{}, itemsMerged *uint64) error {
again:
  if len(bsm.bsrHeap) == 0 {
    // Write the last (maybe incomplete) inmemoryBlock to bsw.
    bsm.flushIB(bsw, ph, itemsMerged)
    return nil
  }

  select {
  case <-stopCh:
    return errForciblyStopped
  default:
  }

  bsr := heap.Pop(&bsm.bsrHeap).(*blockStreamReader)

  var nextItem []byte
  hasNextItem := false
  if len(bsm.bsrHeap) > 0 {
    nextItem = bsm.bsrHeap[0].bh.firstItem
    hasNextItem = true
  }
  for bsr.blockItemIdx < len(bsr.Block.items) {
    item := bsr.Block.items[bsr.blockItemIdx]
    if hasNextItem && string(item) > string(nextItem) {
      break
    }
    if !bsm.ib.Add(item) {
      // The bsm.ib is full. Flush it to bsw and continue.
      bsm.flushIB(bsw, ph, itemsMerged)
      continue
    }
    bsr.blockItemIdx++
  }
  if bsr.blockItemIdx == len(bsr.Block.items) {
    // bsr.Block is fully read. Proceed to the next block.
    if bsr.Next() {
      heap.Push(&bsm.bsrHeap, bsr)
      goto again
    }
    if err := bsr.Error(); err != nil {
      return fmt.Errorf("cannot read storageBlock: %s", err)
    }
    goto again
  }

  // The next item in the bsr.Block exceeds nextItem.
  // Adjust bsr.bh.firstItem and return bsr to heap.
  bsr.bh.firstItem = append(bsr.bh.firstItem[:0], bsr.Block.items[bsr.blockItemIdx]...)
  heap.Push(&bsm.bsrHeap, bsr)
  goto again
}
```

* 最初の `if len(bsm.bsrHeap) == 0` のブロックは `bsm.bsrHeap` が空になったらマージ対象のリーダが無くなったということで `bsm.flushIB` を呼んで抜ける。ここは `Merge` メソッドが呼ばれた時に加えて下から `goto again` で戻ってきた時にも通る。
* `heap.Pop` で `bsm.bsrHeap` から `bh.firstItem` が最小の `blockStreamReader` を取得する。あった場合は `nextItem` と `hasNextItem` もセット。
* `for` ループでは以下の処理を行う。
    * `bsr` の `Block.items` 内の `blockItemIdx` 番目のアイテムを `item` にセット。
    * `item` が `nextItem` より大きいなら `for` ループを抜ける。
    * `bsm.ib` の `Add` メソッドを呼んで戻り値が `false` なら `bsm.flushIB` を呼んで同じ `blockItemIdx` で `for` ループ内の処理を再度実行。
    * `Add` の戻り値が `false` の場合は `blockItemIdx` をインクリメントして次のアイテムに進む。
* `for` ループの下の `if` 文は `bsr.Block.items` を全て処理した場合。
    * `bsr.Next()` が `true` の場合は `bsr` を再度 `bsm.bsrHeap` に追加して `Merge` の先頭から再実行。
    * `bsr.Next()` が `false` の場合は `bsm.bsrHeap` の次の `blockStreamReader` を対象に `Merge` の先頭から再実行。
* `if` の下は `bsr.Block.items` の全てを処理していない場合。 `bsr.blockItemIdx` が指す item を `bsr.bh.firstItem` にコピーし `bsr` を `bsm.bsrHeap` に追加して `Merge` の先頭から再実行。

`blockStreamMerger` 型
[lib/mergeset/merge.go#L54-L68](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L54-L68)
```go
type blockStreamMerger struct {
  prepareBlock PrepareBlockCallback

  bsrHeap bsrHeap

  // ib is a scratch block with pending items.
  ib inmemoryBlock

  phFirstItemCaught bool

  // This are auxiliary buffers used in flushIB
  // for consistency checks after prepareBlock call.
  firstItem []byte
  lastItem  []byte
}
```

`blockStreamMerger` の `flushIB` メソッド
[lib/mergeset/merge.go#L158-L196](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/merge.go#L158-L196)
```go
func (bsm *blockStreamMerger) flushIB(bsw *blockStreamWriter, ph *partHeader, itemsMerged *uint64) {
  if len(bsm.ib.items) == 0 {
    // Nothing to flush.
    return
  }
  atomic.AddUint64(itemsMerged, uint64(len(bsm.ib.items)))
  if bsm.prepareBlock != nil {
    bsm.firstItem = append(bsm.firstItem[:0], bsm.ib.items[0]...)
    bsm.lastItem = append(bsm.lastItem[:0], bsm.ib.items[len(bsm.ib.items)-1]...)
    bsm.ib.data, bsm.ib.items = bsm.prepareBlock(bsm.ib.data, bsm.ib.items)
    if len(bsm.ib.items) == 0 {
      // Nothing to flush
      return
    }
    // Consistency checks after prepareBlock call.
    firstItem := bsm.ib.items[0]
    if string(firstItem) != string(bsm.firstItem) {
      logger.Panicf("BUG: prepareBlock must return first item equal to the original first item;\ngot\n%X\nwant\n%X", firstItem, bsm.firstItem)
    }
    lastItem := bsm.ib.items[len(bsm.ib.items)-1]
    if string(lastItem) != string(bsm.lastItem) {
      logger.Panicf("BUG: prepareBlock must return last item equal to the original last item;\ngot\n%X\nwant\n%X", lastItem, bsm.lastItem)
    }
    // Verify whether the bsm.ib.items are sorted only in tests, since this
    // can be expensive check in prod for items with long common prefix.
    if isInTest && !bsm.ib.isSorted() {
      logger.Panicf("BUG: prepareBlock must return sorted items;\ngot\n%s", bsm.ib.debugItemsString())
    }
  }
  ph.itemsCount += uint64(len(bsm.ib.items))
  if !bsm.phFirstItemCaught {
    ph.firstItem = append(ph.firstItem[:0], bsm.ib.items[0]...)
    bsm.phFirstItemCaught = true
  }
  ph.lastItem = append(ph.lastItem[:0], bsm.ib.items[len(bsm.ib.items)-1]...)
  bsw.WriteBlock(&bsm.ib)
  bsm.ib.Reset()
  ph.blocksCount++
}
```
一文で要約すると `bsm` の `ib` フィールド (`inmemoryBlock` 型 ) を調整後 `bsw` の `WriteBlock` で書き出す。

`inmemoryBlock` 型
[lib/mergeset/encoding.go#L25-L29](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/encoding.go#L25-L29)
```go
type inmemoryBlock struct {
  commonPrefix []byte
  data         []byte
  items        byteSliceSorter
}
```

`blockStreamMerger` の `Merge` メソッドから呼ばれる `inmemoryBlock` 型の `Add` メソッド
[lib/mergeset/encoding.go#L70-L84](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/encoding.go#L70-L84)
```go
// Add adds x to the end of ib.
//
// false is returned if x isn't added to ib due to block size contraints.
func (ib *inmemoryBlock) Add(x []byte) bool {
  if len(x)+len(ib.data) > maxInmemoryBlockSize {
    return false
  }
  if cap(ib.data) < maxInmemoryBlockSize {
    dataLen := len(ib.data)
    ib.data = bytesutil.Resize(ib.data, maxInmemoryBlockSize)[:dataLen]
  }
  ib.data = append(ib.data, x...)
  ib.items = append(ib.items, ib.data[len(ib.data)-len(x):])
  return true
}
```
* `ib.data` に `x` を追加すると 64KiB を超える場合は `false` を返す。
* 超えない場合、 `cap(ib.data)` が 64KiB 未満なら 64KiB に拡張する。
* `ib.data` に `x` を追加。
* `ib.items` に `ib.data` 内にコピーした `x` の部分を指す要素を追加。

`blockStreamMerger` の `flushIB` メソッドから呼ばれる `blockStreamWriter` 型の `WriteBlock` メソッド
[lib/mergeset/block_stream_writer.go#L163-L193](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/block_stream_writer.go#L163-L193)
```go
// WriteBlock writes ib to bsw.
//
// ib must be sorted.
func (bsw *blockStreamWriter) WriteBlock(ib *inmemoryBlock) {
  bsw.bh.firstItem, bsw.bh.commonPrefix, bsw.bh.itemsCount, bsw.bh.marshalType = ib.MarshalSortedData(&bsw.sb, bsw.bh.firstItem[:0], bsw.bh.commonPrefix[:0], bsw.compressLevel)

  if !bsw.mrFirstItemCaught {
    bsw.mr.firstItem = append(bsw.mr.firstItem[:0], bsw.bh.firstItem...)
    bsw.mrFirstItemCaught = true
  }

  // Write itemsData
  fs.MustWriteData(bsw.itemsWriter, bsw.sb.itemsData)
  bsw.bh.itemsBlockSize = uint32(len(bsw.sb.itemsData))
  bsw.bh.itemsBlockOffset = bsw.itemsBlockOffset
  bsw.itemsBlockOffset += uint64(bsw.bh.itemsBlockSize)

  // Write lensData
  fs.MustWriteData(bsw.lensWriter, bsw.sb.lensData)
  bsw.bh.lensBlockSize = uint32(len(bsw.sb.lensData))
  bsw.bh.lensBlockOffset = bsw.lensBlockOffset
  bsw.lensBlockOffset += uint64(bsw.bh.lensBlockSize)

  // Write blockHeader
  bsw.unpackedIndexBlockBuf = bsw.bh.Marshal(bsw.unpackedIndexBlockBuf)
  bsw.bh.Reset()
  bsw.mr.blockHeadersCount++
  if len(bsw.unpackedIndexBlockBuf) >= maxIndexBlockSize {
    bsw.flushIndexData()
  }
}
```

`blockStreamWriter` 型
[lib/mergeset/block_stream_writer.go#L13-L38](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/61c9d320ed924b8cc0202b4c5feee547010f8416/lib/mergeset/block_stream_writer.go#L13-L38)
```go
type blockStreamWriter struct {
  compressLevel int
  path          string

  metaindexWriter filestream.WriteCloser
  indexWriter     filestream.WriteCloser
  itemsWriter     filestream.WriteCloser
  lensWriter      filestream.WriteCloser

  sb storageBlock
  bh blockHeader
  mr metaindexRow

  unpackedIndexBlockBuf []byte
  packedIndexBlockBuf   []byte

  unpackedMetaindexBuf []byte
  packedMetaindexBuf   []byte

  itemsBlockOffset uint64
  lensBlockOffset  uint64
  indexBlockOffset uint64

  // whether the first item for mr has been caught.
  mrFirstItemCaught bool
}
```
