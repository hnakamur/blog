---
title: "VictoriaMetrics/fastcacheのコードリーディングその2"
date: 2019-12-30T05:11:55+09:00
lastmod: 2020-01-01T07:30:00+09:00
tag: go, victoria-metrics
---

## はじめに

[VictoriMetrics/fastcacheのコードリーディングその1](/blog/2019/12/30/victoriametrics-fastcache-code-reading-part1/) の後、新しいコミットが入っていたので今回の対象は [2dd9480](https://github.com/VictoriaMetrics/fastcache/commit/2dd94801554bb525434adca19ae035c391934f18) です。

今回はファイルへの書き出しとファイルからの読み込みが対象です。ファイルは [file.go](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go) です。

## コードリーディング

### SaveToFile 関数

[file.go#L16-L26](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L16-L26)

```go
// SaveToFile atomically saves cache data to the given filePath using a single
// CPU core.
//
// SaveToFile may be called concurrently with other operations on the cache.
//
// The saved data may be loaded with LoadFromFile*.
//
// See also SaveToFileConcurrent for faster saving to file.
func (c *Cache) SaveToFile(filePath string) error {
  return c.SaveToFileConcurrent(filePath, 1)
}
```

`SaveToFileConcurrent` メソッドを並列度1で呼ぶラッパメソッドです。

### SaveToFileConcurrent 関数

[file.go#L28-L77](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L28-L77)

```go
// SaveToFileConcurrent saves cache data to the given filePath using concurrency
// CPU cores.
//
// SaveToFileConcurrent may be called concurrently with other operations
// on the cache.
//
// The saved data may be loaded with LoadFromFile*.
//
// See also SaveToFile.
func (c *Cache) SaveToFileConcurrent(filePath string, concurrency int) error {
  // Create dir if it doesn't exist.
  dir := filepath.Dir(filePath)
  if _, err := os.Stat(dir); err != nil {
    if !os.IsNotExist(err) {
      return fmt.Errorf("cannot stat %q: %s", dir, err)
    }
    if err := os.MkdirAll(dir, 0755); err != nil {
      return fmt.Errorf("cannot create dir %q: %s", dir, err)
    }
  }

  // Save cache data into a temporary directory.
  tmpDir, err := ioutil.TempDir(dir, "fastcache.tmp.")
  if err != nil {
    return fmt.Errorf("cannot create temporary dir inside %q: %s", dir, err)
  }
  defer func() {
    if tmpDir != "" {
      _ = os.RemoveAll(tmpDir)
    }
  }()
  gomaxprocs := runtime.GOMAXPROCS(-1)
  if concurrency <= 0 || concurrency > gomaxprocs {
    concurrency = gomaxprocs
  }
  if err := c.save(tmpDir, concurrency); err != nil {
    return fmt.Errorf("cannot save cache data to temporary dir %q: %s", tmpDir, err)
  }

  // Remove old filePath contents, since os.Rename may return
  // error if filePath dir exists.
  if err := os.RemoveAll(filePath); err != nil {
    return fmt.Errorf("cannot remove old contents at %q: %s", filePath, err)
  }
  if err := os.Rename(tmpDir, filePath); err != nil {
    return fmt.Errorf("cannot move temporary dir %q to %q: %s", tmpDir, filePath, err)
  }
  tmpDir = ""
  return nil
}
```

* 引数の `concurrency` で指定した数のCPUコアで並列実行して `Cache` をファイルに書き出します。
* 指定の `filePath` のパスのディレクトリ部分に対応するディレクトリが無い場合は作ります。
* 上記のディレクトリの下に中間ディレクトリ `tmpDir` を作ります。
* [runtime.GOMAXPROCS](https://golang.org/pkg/runtime/#GOMAXPROCS) を引数 -1 で呼ぶことで同時実行可能な CPU の最大数の現在の設定値を取得して `gomaxprocs` 変数に設定します。
* `concurency` が 0 以下かこの値より大きい場合は `gomaxprocs` の値にします。
* `Cache` の `save` メソッドを上記で調整した `concurrency` で呼び出します。
* `filePath` で指定したパスに古いコンテンツがある場合はまず削除します。
* `tmpDir` を `filePath` にリネームします。

### LoadFromFile 関数

[file.go#L79-L84](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L79-L84)

```go
// LoadFromFile loads cache data from the given filePath.
//
// See SaveToFile* for saving cache data to file.
func LoadFromFile(filePath string) (*Cache, error) {
  return load(filePath, 0)
}
```

`load` 関数を `maxBytes` を 0 で呼び出します。

### LoadFromFileOrNew 関数

[file.go#L86-L96](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L86-L96)

```go
// LoadFromFileOrNew tries loading cache data from the given filePath.
//
// The function falls back to creating new cache with the given maxBytes
// capacity if error occurs during loading the cache from file.
func LoadFromFileOrNew(filePath string, maxBytes int) *Cache {
  c, err := load(filePath, maxBytes)
  if err == nil {
    return c
  }
  return New(maxBytes)
}
```

`load` でファイルから読み込んで成功したらそれを返し、失敗したら `New` を呼んで新規作成します。

### Cache の save メソッド

[file.go#L98-L126](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L98-L126)

```go
func (c *Cache) save(dir string, workersCount int) error {
  if err := saveMetadata(c, dir); err != nil {
    return err
  }

  // Save buckets by workersCount concurrent workers.
  workCh := make(chan int, workersCount)
  results := make(chan error)
  for i := 0; i < workersCount; i++ {
    go func(workerNum int) {
      results <- saveBuckets(c.buckets[:], workCh, dir, workerNum)
    }(i)
  }
  // Feed workers with work
  for i := range c.buckets[:] {
    workCh <- i
  }
  close(workCh)

  // Read results.
  var err error
  for i := 0; i < workersCount; i++ {
    result := <-results
    if result != nil && err != nil {
      err = result
    }
  }
  return err
}
```

* まず `saveMetadata` 関数を呼んでメタデータを `dir` 引数で指定されたディレクトリに保存します。
* `workersCount` 引数の数だけ goroutine を作ります。 `workersCount` のバッファを持つ `chan int` 型の `workCh` と `chan error` 型の `results` も作ります。
* [Go Concurrency Patterns: Pipelines and cancellation - The Go Blog](https://blog.golang.org/pipelines) の [Fan-out, fan-in](https://blog.golang.org/pipelines#TOC_4.) と似たようなパターンですがここでは [sync.WaitGroup](https://golang.org/pkg/sync/#WaitGroup) を使わず `results` で `workersCount` 個の結果を待つようにしています。
* 各 goroutine は `saveBuckets` 関数を呼び出します。
* `workCh` には `c.buckets` の要素数分のインデクスを送って、これを各 goroutine が受け取って処理を実行します。
* `result != nil && err != nil` は `result != nil && err == nil` の間違いだと思います。 `results` から `nil` 以外の値が返ってきたときは最初のエラーを保管しておくという意図のはずです。 `result != nil && err != nil` だと `err` が初期値の `nil` のままで `result` は `nil` 以外でも捨てられることになってしまいます。
    * 2020-01-01追記: これを修正するプルリクエスト [Fix taking the first error from workers in save by hnakamur · Pull Request #28 · VictoriaMetrics/fastcache](https://github.com/VictoriaMetrics/fastcache/pull/28) を送っていたのが無事マージされました。

### load 関数

[file.go#L128-L177](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L128-L177)

```go
func load(filePath string, maxBytes int) (*Cache, error) {
  maxBucketChunks, err := loadMetadata(filePath)
  if err != nil {
    return nil, err
  }
  if maxBytes > 0 {
    maxBucketBytes := uint64((maxBytes + bucketsCount - 1) / bucketsCount)
    expectedBucketChunks := (maxBucketBytes + chunkSize - 1) / chunkSize
    if maxBucketChunks != expectedBucketChunks {
      return nil, fmt.Errorf("cache file %s contains maxBytes=%d; want %d", filePath, maxBytes, expectedBucketChunks*chunkSize*bucketsCount)
    }
  }

  // Read bucket files from filePath dir.
  d, err := os.Open(filePath)
  if err != nil {
    return nil, fmt.Errorf("cannot open %q: %s", filePath, err)
  }
  defer func() {
    _ = d.Close()
  }()
  fis, err := d.Readdir(-1)
  if err != nil {
    return nil, fmt.Errorf("cannot read files from %q: %s", filePath, err)
  }
  results := make(chan error)
  workersCount := 0
  var c Cache
  for _, fi := range fis {
    fn := fi.Name()
    if fi.IsDir() || !dataFileRegexp.MatchString(fn) {
      continue
    }
    workersCount++
    go func(dataPath string) {
      results <- loadBuckets(c.buckets[:], dataPath, maxBucketChunks)
    }(filePath + "/" + fn)
  }
  err = nil
  for i := 0; i < workersCount; i++ {
    result := <-results
    if result != nil && err == nil {
      err = result
    }
  }
  if err != nil {
    return nil, err
  }
  return &c, nil
}
```

* まず `loadMetadata` 関数でメタデータを読み込みます。戻り値としてバケットのチャンク数を受け取り `maxBucketChunks` 変数にセットします。
* `maxBytes` 引数に0より大きな指定された場合は、その値から期待されるバケットのチャンク数 `expectedBucketChunks` を計算します。まず `maxBytes` を `bucketsCount` (=512) で割って切り上げた数を `maxBucketBytes` （1バケットあたりの最大バイト数）に設定します。次に `maxBucketBytes` を `chunkSize` (=64KiB) で割って切り上げた数を `expectedBucketChunks` にセットし `maxBucketChunks` と比較し一致しない場合はエラーを返します。
* `filePath` のディレクトリを開いて `Readdir` メソッドでディレクトリエントリ一覧を読み取ります。
* この後 goroutine からの結果を受け取る `chan error` 型のチャンネル `results` を作成します。
* `dataFileRegexp` の正規表現にマッチする名前のディレクトリを処理対象とし、それぞれに goroutine を作成します。goroutine 内では `loadBuckets` 関数を呼んで結果を `results` に返します。 `workersCount` は 0 から goroutine 作成毎にインクリメントし、最終的に作成した goroutine の数になります。 各 goroutine は読み込んだ結果を `Cache` の各バケットにセットします。
* goroutine の呼び出し側では作成した goroutine の数を `workersCount` としその数だけ `results` から結果を受け取ります。 `results` からは受け取った `nil` でない最初のエラーを保管しておき、エラーがあった場合はエラーを返し、エラーが無かった場合は `Cache` のポインタを返します。

`dataFileRegexp` 変数は [file.go#L214](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L214) で定義されています。

```go
var dataFileRegexp = regexp.MustCompile(`^data\.\d+\.bin$`)
```

### saveMetadata 関数
[file.go#L179-L193](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L179-L193)

```go
func saveMetadata(c *Cache, dir string) error {
  metadataPath := dir + "/metadata.bin"
  metadataFile, err := os.Create(metadataPath)
  if err != nil {
    return fmt.Errorf("cannot create %q: %s", metadataPath, err)
  }
  defer func() {
    _ = metadataFile.Close()
  }()
  maxBucketChunks := uint64(cap(c.buckets[0].chunks))
  if err := writeUint64(metadataFile, maxBucketChunks); err != nil {
    return fmt.Errorf("cannot write maxBucketChunks=%d to %q: %s", maxBucketChunks, metadataPath, err)
  }
  return nil
}
```

* 引数 `dir` の下に `metadata.bin` というファイルを作成しバケットのチャンク数を `uint64` 型で書き出します。バケットのチャンク数はどのバケットも同じなので最初のバケットのチャンク数を使っています。

### loadMetadata 関数

[file.go#L195-L212](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L195-L212)

```go
func loadMetadata(dir string) (uint64, error) {
  metadataPath := dir + "/metadata.bin"
  metadataFile, err := os.Open(metadataPath)
  if err != nil {
    return 0, fmt.Errorf("cannot open %q: %s", metadataPath, err)
  }
  defer func() {
    _ = metadataFile.Close()
  }()
  maxBucketChunks, err := readUint64(metadataFile)
  if err != nil {
    return 0, fmt.Errorf("cannot read maxBucketChunks from %q: %s", metadataPath, err)
  }
  if maxBucketChunks == 0 {
    return 0, fmt.Errorf("invalid maxBucketChunks=0 read from %q", metadataPath)
  }
  return maxBucketChunks, nil
}
```

* 引数 `dir` の下に `metadata.bin` というファイル `uint64` 型の値を読み取ります。読み取り時にエラーが起きた時と読み取った結果が0の場合はエラーとします。


### saveBuckets 関数
[file.go#L216-L238](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L216-L238)

```go
func saveBuckets(buckets []bucket, workCh <-chan int, dir string, workerNum int) error {
  dataPath := fmt.Sprintf("%s/data.%d.bin", dir, workerNum)
  dataFile, err := os.Create(dataPath)
  if err != nil {
    return fmt.Errorf("cannot create %q: %s", dataPath, err)
  }
  defer func() {
    _ = dataFile.Close()
  }()
  zw := snappy.NewBufferedWriter(dataFile)
  for bucketNum := range workCh {
    if err := writeUint64(zw, uint64(bucketNum)); err != nil {
      return fmt.Errorf("cannot write bucketNum=%d to %q: %s", bucketNum, dataPath, err)
    }
    if err := buckets[bucketNum].Save(zw); err != nil {
      return fmt.Errorf("cannot save bucket[%d] to %q: %s", bucketNum, dataPath, err)
    }
  }
  if err := zw.Close(); err != nil {
    return fmt.Errorf("cannot close snappy.Writer for %q: %s", dataPath, err)
  }
  return nil
}
```

* `dir` 配下に `data.%d.bin` (`%d` にはワーカーの連番IDを設定 )というファイルを作成します。ファイルには snappy 形式で圧縮した内容を書き込むようにしています。
* `workCh` からバケットのインデクスを受け取ったら、それを `uint64` 形式で書き出し、その後バケットの `Save` メソッドを呼び出して書き込みます。


### loadBuckets 関数

[file.go#L240-L262](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L240-L262)

```go
func loadBuckets(buckets []bucket, dataPath string, maxChunks uint64) error {
  dataFile, err := os.Open(dataPath)
  if err != nil {
    return fmt.Errorf("cannot open %q: %s", dataPath, err)
  }
  defer func() {
    _ = dataFile.Close()
  }()
  zr := snappy.NewReader(dataFile)
  for {
    bucketNum, err := readUint64(zr)
    if err == io.EOF {
      // Reached the end of file.
      return nil
    }
    if bucketNum >= uint64(len(buckets)) {
      return fmt.Errorf("unexpected bucketNum read from %q: %d; must be smaller than %d", dataPath, bucketNum, len(buckets))
    }
    if err := buckets[bucketNum].Load(zr, maxChunks); err != nil {
      return fmt.Errorf("cannot load bucket[%d] from %q: %s", bucketNum, dataPath, err)
    }
  }
}
```

* `dataPath` 引数のパスを開いて snappy 形式で読み出します。
* 最初に `uint64` 形式でバケットのインデクスを読み取ります。
* バケットのインデクスがバケットの数以上の場合はエラーを返します。
* 上記のインデクスのバケットにファイルから読み込んだバケットの内容を設定します。


### bucket の Save メソッド

[file.go#L264-L315](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L264-L315)

```go
func (b *bucket) Save(w io.Writer) error {
  b.Clean()

  b.mu.RLock()
  defer b.mu.RUnlock()

  // Store b.idx, b.gen and b.m to w.

  bIdx := b.idx
  bGen := b.gen
  chunksLen := 0
  for _, chunk := range b.chunks {
    if chunk == nil {
      break
    }
    chunksLen++
  }
  kvs := make([]byte, 0, 2*8*len(b.m))
  var u64Buf [8]byte
  for k, v := range b.m {
    binary.LittleEndian.PutUint64(u64Buf[:], k)
    kvs = append(kvs, u64Buf[:]...)
    binary.LittleEndian.PutUint64(u64Buf[:], v)
    kvs = append(kvs, u64Buf[:]...)
  }

  if err := writeUint64(w, bIdx); err != nil {
    return fmt.Errorf("cannot write b.idx: %s", err)
  }
  if err := writeUint64(w, bGen); err != nil {
    return fmt.Errorf("cannot write b.gen: %s", err)
  }
  if err := writeUint64(w, uint64(len(kvs))/2/8); err != nil {
    return fmt.Errorf("cannot write len(b.m): %s", err)
  }
  if _, err := w.Write(kvs); err != nil {
    return fmt.Errorf("cannot write b.m: %s", err)
  }

  // Store b.chunks to w.
  if err := writeUint64(w, uint64(chunksLen)); err != nil {
    return fmt.Errorf("cannot write len(b.chunks): %s", err)
  }
  for chunkIdx := 0; chunkIdx < chunksLen; chunkIdx++ {
    chunk := b.chunks[chunkIdx][:chunkSize]
    if _, err := w.Write(chunk); err != nil {
      return fmt.Errorf("cannot write b.chunks[%d]: %s", chunkIdx, err)
    }
  }

  return nil
}
```

* `b.idx`, `b.gen` と `b.m` を書き出します。 `b.idx`, `b.gen` は `uint64` 形式で書きます。 `b.m` は各エントリのキーとバリューを `uint64` 形式でバイト列にしたものを `kvs` 変数に設定します。まずエントリ数を `uint64` 形式で書いてその後に `kvs` のバイト列を書き出します。
* その後 `b.chunks` の内容を書き出します。コードの手前の方で `b.chunks` のうち最初の `nil` でない部分の個数を `chunksLen` に設定しています。まず `chunksLen` を `uint64` 形式で書き出し、その後 `b.chunks` の各チャンクのバイト列の 64KiB 分のデータを書き出します。


### bucket の Load メソッド
[file.go#L317-L393](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L317-L393)

```go
func (b *bucket) Load(r io.Reader, maxChunks uint64) error {
  if maxChunks == 0 {
    return fmt.Errorf("the number of chunks per bucket cannot be zero")
  }
  bIdx, err := readUint64(r)
  if err != nil {
    return fmt.Errorf("cannot read b.idx: %s", err)
  }
  bGen, err := readUint64(r)
  if err != nil {
    return fmt.Errorf("cannot read b.gen: %s", err)
  }
  kvsLen, err := readUint64(r)
  if err != nil {
    return fmt.Errorf("cannot read len(b.m): %s", err)
  }
  kvsLen *= 2 * 8
  kvs := make([]byte, kvsLen)
  if _, err := io.ReadFull(r, kvs); err != nil {
    return fmt.Errorf("cannot read b.m: %s", err)
  }
  m := make(map[uint64]uint64, kvsLen/2/8)
  for len(kvs) > 0 {
    k := binary.LittleEndian.Uint64(kvs)
    kvs = kvs[8:]
    v := binary.LittleEndian.Uint64(kvs)
    kvs = kvs[8:]
    m[k] = v
  }

  maxBytes := maxChunks * chunkSize
  if maxBytes >= maxBucketSize {
    return fmt.Errorf("too big maxBytes=%d; should be smaller than %d", maxBytes, maxBucketSize)
  }
  chunks := make([][]byte, maxChunks)
  chunksLen, err := readUint64(r)
  if err != nil {
    return fmt.Errorf("cannot read len(b.chunks): %s", err)
  }
  if chunksLen > uint64(maxChunks) {
    return fmt.Errorf("chunksLen=%d cannot exceed maxChunks=%d", chunksLen, maxChunks)
  }
  currChunkIdx := bIdx / chunkSize
  if currChunkIdx > 0 && currChunkIdx >= chunksLen {
    return fmt.Errorf("too big bIdx=%d; should be smaller than %d", bIdx, chunksLen*chunkSize)
  }
  for chunkIdx := uint64(0); chunkIdx < chunksLen; chunkIdx++ {
    chunk := getChunk()
    chunks[chunkIdx] = chunk
    if _, err := io.ReadFull(r, chunk); err != nil {
      // Free up allocated chunks before returning the error.
      for _, chunk := range chunks {
        if chunk != nil {
          putChunk(chunk)
        }
      }
      return fmt.Errorf("cannot read b.chunks[%d]: %s", chunkIdx, err)
    }
  }
  // Adjust len for the chunk pointed by currChunkIdx.
  if chunksLen > 0 {
    chunkLen := bIdx % chunkSize
    chunks[currChunkIdx] = chunks[currChunkIdx][:chunkLen]
  }

  b.mu.Lock()
  for _, chunk := range b.chunks {
    putChunk(chunk)
  }
  b.chunks = chunks
  b.m = m
  b.idx = bIdx
  b.gen = bGen
  b.mu.Unlock()

  return nil
}
```

* `Save` メソッドで書いた形式に沿って読み込んでいきます。読み取る際に `maxChunks` 引数の値から算出した値とファイルから読みこんで得られた値を比較して（詳細は上記のコードを参照）おかしい場合はエラーを返します。
* 現在の書き込み対象のチャンクのインデクスを `bIdx / chunkSize` で算出し `currChunkIdx` 変数にセットしています。そのチャンク内の書き込み位置を `bIdx % chunkSize` で算出して、チャンクの `cap` はそのままにして `len` をその値に調節しています。
* `b.chunks` でループして `putChunk` 関数を呼んでいる箇所は初回は `b.chunks` が `nil` なので何もしません。一旦構築後に `Load` を呼んだ場合は古いチャンクを解放する必要があるのでループで回して `putChunk` を呼んでいます。

### writeUint64 関数

[file.go#L395-L400](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L395-L400)

```go
func writeUint64(w io.Writer, u uint64) error {
  var u64Buf [8]byte
  binary.LittleEndian.PutUint64(u64Buf[:], u)
  _, err := w.Write(u64Buf[:])
  return err
}
```

* LittleEndian の uint64 形式で値を書き出します。

### readUint64

[file.go#L402-L409](https://github.com/VictoriaMetrics/fastcache/blob/2dd94801554bb525434adca19ae035c391934f18/file.go#L402-L409)

```go
func readUint64(r io.Reader) (uint64, error) {
  var u64Buf [8]byte
  if _, err := io.ReadFull(r, u64Buf[:]); err != nil {
    return 0, err
  }
  u := binary.LittleEndian.Uint64(u64Buf[:])
  return u, nil
}
```

* LittleEndian の uint64 形式で値を読み取ります。


## まとめ

[VictoriMetrics/fastcacheのコードリーディングその1](/blog/2019/12/30/victoriametrics-fastcache-code-reading-part1/) と合わせて主な処理は読み終わりました。

* fastcache は作成時に指定した最大バイト数の領域をリングバッファ形式で書いていくという仕組みになっています。運用中にメモリ使用量が増えるという心配がない一方、指定のバイト数を超えると古いエントリが上書きされていきます。
* Google App Engine と Windows 以外では mmap を使ってGoのGCの管理外でメモリ割り当てをすることでGCのオーバーヘッドを回避しています。
* キーの最大長は 64KiB です。
* 値のサイズが 64KiB を超える場合は 64KiB より少し小さい単位で分割して同じハッシュ空間に別のキー (subkey) で保管します。
* キーも subkey も衝突したら古いエントリを黙って上書きします。

ハッシュ衝突の際に黙って上書きという割り切り仕様が高速化に寄与しているんだろうなと思いますが、実際に自分が使うことを考えると不安が残ります。

全般としては mmap で割り当てたメモリ領域を使ってデータ構造を構築する見本として非常に勉強になりました。
