+++
title="VictoriMetrics/fastcacheのコードリーディングその1"
date = "2019-12-30T01:20:00+09:00"
tags = ["go", "key-value-store", "victoria-metrics"]
categories = ["blog"]
+++

## はじめに

[VictoriaMetrics/fastcache](https://github.com/VictoriaMetrics/fastcache) のコードリーディングのメモです。対象バージョンはこの記事を書いた時点の最新コミット [c9a5939](https://github.com/VictoriaMetrics/fastcache/commit/c9a5939fd508ba790b708b23929feea13623d735) です。

## 仕様

[VictoriaMetrics/fastcache](https://github.com/VictoriaMetrics/fastcache) は [VictoriaMetrics/VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) のメトリクス名の管理に使っているキーバリューストアを切り出したものなので、 VictoriaMetrics での要件に沿った仕様となっています。

* ストア作成時に使用可能な最大メモリ容量を指定
* キー・バリューを追加するときにメモリ容量を超える場合は古いエントリが自動的に削除される

大量のエントリを GC のオーバーヘッドなしに登録可能なデザインとありますが、 VictoriaMetrics という時系列DBのメトリクス名からIDへのマッピングなどを保管する用途なのでキーと値の集合は一旦一通り登録したら、それ以降は基本的には増えないような使い方を想定していると推測します。

動的にコンテナが増えまくって、その際違うメトリクス名を使うような使い方をするなら別ですが。

## コードリーディング

[Architecture details](https://github.com/VictoriaMetrics/fastcache#architecture-details) にある通り、多数のバケットから構成されるハッシュテーブルになっています。バケット毎にロックが分かれているのでマルチコアの CPU で別のバケットにアクセスする場合は並列に実行可能です。

### 主な定数

[fastcache.go#L14-L24](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L14-L24)

```go
const bucketsCount = 512

const chunkSize = 64 * 1024

const bucketSizeBits = 40

const genSizeBits = 64 - bucketSizeBits

const maxGen = 1<<genSizeBits - 1

const maxBucketSize uint64 = 1 << bucketSizeBits
```

バケット数は 512 固定。チャンクサイズは 64 KiB。
`uint64` の 8 バイトの領域のうち 40bit をバケットサイズに使い、残りの 24bit を世代に使うようになっています。
`maxBucketSize` は `1<<40` つまり 1 TiB です。

### メインのCache 構造体

[fastcache.go#L108-L112](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L108-L112)

```go
type Cache struct {
  buckets [bucketsCount]bucket

  bigStats BigStats
}
```

512 個のバケットと統計情報のフィールドを持ちます。


### New 関数

[fastcache.go#L114-L130](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L114-L130)

```go
// New returns new cache with the given maxBytes capacity in bytes.
//
// maxBytes must be smaller than the available RAM size for the app,
// since the cache holds data in memory.
//
// If maxBytes is less than 32MB, then the minimum cache capacity is 32MB.
func New(maxBytes int) *Cache {
  if maxBytes <= 0 {
    panic(fmt.Errorf("maxBytes must be greater than 0; got %d", maxBytes))
  }
  var c Cache
  maxBucketBytes := uint64((maxBytes + bucketsCount - 1) / bucketsCount)
  for i := range c.buckets[:] {
    c.buckets[i].Init(maxBucketBytes)
  }
  return &c
}
```

引数の `maxBytes` をバケットの数 512 で割って切り上げたものを、1 つのバケット当たりの最大バイト数とし各バケットを初期化します。

### bucket 構造体と Init メソッド

[fastcache.go#L214-L248](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L214-L248)

```go
type bucket struct {
  mu sync.RWMutex

  // chunks is a ring buffer with encoded (k, v) pairs.
  // It consists of 64KB chunks.
  chunks [][]byte

  // m maps hash(k) to idx of (k, v) pair in chunks.
  m map[uint64]uint64

  // idx points to chunks for writing the next (k, v) pair.
  idx uint64

  // gen is the generation of chunks.
  gen uint64

  getCalls    uint64
  setCalls    uint64
  misses      uint64
  collisions  uint64
  corruptions uint64
}

func (b *bucket) Init(maxBytes uint64) {
  if maxBytes == 0 {
    panic(fmt.Errorf("maxBytes cannot be zero"))
  }
  if maxBytes >= maxBucketSize {
    panic(fmt.Errorf("too big maxBytes=%d; should be smaller than %d", maxBytes, maxBucketSize))
  }
  maxChunks := (maxBytes + chunkSize - 1) / chunkSize
  b.chunks = make([][]byte, maxChunks)
  b.m = make(map[uint64]uint64)
  b.Reset()
}
```

* `chunks` フィールドはキーバリューペアをエンコードした値を格納するリングバッファ。 `[]byte` は 64KiB のチャンクでそれを複数持つので `[][]byte` 型。
* `m` フィールドはキーのハッシュ値からキーバリューペアのエントリの `chunks` 内でのインデクスへのマッピング。
* `idx` フィールドは次のキーバリューペアを書き込むインデクス（具体的にどういう値かは `bucket` の `Set` メソッド参照）。
* `gen` は `chunks` の世代。
* `chunks` の長さ（要素数）は引数の `maxBytes` （1つのバケットの最大バイト数）を 1つの `chunk` のサイズ 64 KiB で割って切り上げた数としている。

### Cache の Set メソッド

[fastcache.go#L132-L149](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L132-L149)

```go
// Set stores (k, v) in the cache.
//
// Get must be used for reading the stored entry.
//
// The stored entry may be evicted at any time either due to cache
// overflow or due to unlikely hash collision.
// Pass higher maxBytes value to New if the added items disappear
// frequently.
//
// (k, v) entries with summary size exceeding 64KB aren't stored in the cache.
// SetBig can be used for storing entries exceeding 64KB.
//
// k and v contents may be modified after returning from Set.
func (c *Cache) Set(k, v []byte) {
  h := xxhash.Sum64(k)
  idx := h % bucketsCount
  c.buckets[idx].Set(k, v, h)
}
```

`xxhash.Sum64` でキーのハッシュ値を計算し、バケット数で割った余りをインデクスとして対応するバケットを決定しその `Set` メソッドに移譲。

ハッシュ値が衝突する場合は同じハッシュ値の古いキーが上書きされる。衝突が頻繁に起こるようなら `maxBytes` ともっと大きい値にして `New` を呼んで `Cache` を作るようにしておく。

`Get` など他のメソッドもほぼ同じパターン。

### bucket の Set メソッド

[fastcache.go#L302-L358](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L302-L358)

```go
func (b *bucket) Set(k, v []byte, h uint64) {
  setCalls := atomic.AddUint64(&b.setCalls, 1)
  if setCalls%(1<<14) == 0 {
    b.Clean()
  }

  if len(k) >= (1<<16) || len(v) >= (1<<16) {
    // Too big key or value - its length cannot be encoded
    // with 2 bytes (see below). Skip the entry.
    return
  }
  var kvLenBuf [4]byte
  kvLenBuf[0] = byte(uint16(len(k)) >> 8)
  kvLenBuf[1] = byte(len(k))
  kvLenBuf[2] = byte(uint16(len(v)) >> 8)
  kvLenBuf[3] = byte(len(v))
  kvLen := uint64(len(kvLenBuf) + len(k) + len(v))
  if kvLen >= chunkSize {
    // Do not store too big keys and values, since they do not
    // fit a chunk.
    return
  }

  b.mu.Lock()
  idx := b.idx
  idxNew := idx + kvLen
  chunkIdx := idx / chunkSize
  chunkIdxNew := idxNew / chunkSize
  if chunkIdxNew > chunkIdx {
    if chunkIdxNew >= uint64(len(b.chunks)) {
      idx = 0
      idxNew = kvLen
      chunkIdx = 0
      b.gen++
      if b.gen&((1<<genSizeBits)-1) == 0 {
        b.gen++
      }
    } else {
      idx = chunkIdxNew * chunkSize
      idxNew = idx + kvLen
      chunkIdx = chunkIdxNew
    }
    b.chunks[chunkIdx] = b.chunks[chunkIdx][:0]
  }
  chunk := b.chunks[chunkIdx]
  if chunk == nil {
    chunk = getChunk()
    chunk = chunk[:0]
  }
  chunk = append(chunk, kvLenBuf[:]...)
  chunk = append(chunk, k...)
  chunk = append(chunk, v...)
  b.chunks[chunkIdx] = chunk
  b.m[h] = idx | (b.gen << bucketSizeBits)
  b.idx = idxNew
  b.mu.Unlock()
}
```

* キーと値のバイト数でのサイズは共に最大 64 KiB。
* キーと値の長さをそれぞれ 2 バイトの整数でエンコードし、その後にキーと値のバイト列を追加したものが `chunk` になる。
* `chunk` の長さが 64 KiB 以上の場合は、なんと何もせずに抜ける。適切なサイズのキーと値を渡すのは呼び出し側の責任ということか。
* `idx` は 64 KiB のチャンクが複数並ぶ空間内での次に書き込む開始位置を表している。
* それに今回書き込むべき `chunk` の長さ `kvLen` を足したものが終端位置 `idxNew` 。
* `idx` と `idxNew` を `chunkSize` で割った値が `chunks` 内の対応するインデクスになる。
* `chunkIdxNew` > `chunkIdx` は今回の `chunk` が 64 KiB の境界をまたぐという場合。
* さらに `chunkIdxNew >= uint64(len(b.chunks))` は `chunks` の最後のチャンクの終端を超える場合。この場合は世代 `b.gen` を増やして `chunks` の最初の要素に書き込む。
* `b.gen` を増やしたとき `b.gen&((1<<genSizeBits)-1) == 0` になる場合というのは下位 24bit が 0 になる場合。1週目は `1<<24` で 2週目だと `2<<24` 。この値は下位24bitを取ると初期値の 0 と区別がつかなくなるのでさらに1足すようにしている。

### Cache の Get メソッド

[fastcache.go#L151-L163](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L151-L163)

```go
// Get appends value by the key k to dst and returns the result.
//
// Get allocates new byte slice for the returned value if dst is nil.
//
// Get returns only values stored in c via Set.
//
// k contents may be modified after returning from Get.
func (c *Cache) Get(dst, k []byte) []byte {
  h := xxhash.Sum64(k)
  idx := h % bucketsCount
  dst, _ = c.buckets[idx].Get(dst, k, h, true)
  return dst
}
```

まずシグネチャが `Get(k []byte) []byte` でなく、値の書き込み先 `dst` を引数で渡すことに注意。 Go のビルトイン関数 `append` と同じパターン。これにより `dst` の `cap` に余裕があればメモリ割り当てをしなくて済む。

### bucket の Get メソッド

[fastcache.go#L360-L409](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L360-L409)

```go
func (b *bucket) Get(dst, k []byte, h uint64, returnDst bool) ([]byte, bool) {
  atomic.AddUint64(&b.getCalls, 1)
  found := false
  b.mu.RLock()
  v := b.m[h]
  bGen := b.gen & ((1 << genSizeBits) - 1)
  if v > 0 {
    gen := v >> bucketSizeBits
    idx := v & ((1 << bucketSizeBits) - 1)
    if gen == bGen && idx < b.idx || gen+1 == bGen && idx >= b.idx || gen == maxGen && bGen == 1 && idx >= b.idx {
      chunkIdx := idx / chunkSize
      if chunkIdx >= uint64(len(b.chunks)) {
        // Corrupted data during the load from file. Just skip it.
        atomic.AddUint64(&b.corruptions, 1)
        goto end
      }
      chunk := b.chunks[chunkIdx]
      idx %= chunkSize
      if idx+4 >= chunkSize {
        // Corrupted data during the load from file. Just skip it.
        atomic.AddUint64(&b.corruptions, 1)
        goto end
      }
      kvLenBuf := chunk[idx : idx+4]
      keyLen := (uint64(kvLenBuf[0]) << 8) | uint64(kvLenBuf[1])
      valLen := (uint64(kvLenBuf[2]) << 8) | uint64(kvLenBuf[3])
      idx += 4
      if idx+keyLen+valLen >= chunkSize {
        // Corrupted data during the load from file. Just skip it.
        atomic.AddUint64(&b.corruptions, 1)
        goto end
      }
      if string(k) == string(chunk[idx:idx+keyLen]) {
        idx += keyLen
        if returnDst {
          dst = append(dst, chunk[idx:idx+valLen]...)
        }
        found = true
      } else {
        atomic.AddUint64(&b.collisions, 1)
      }
    }
  }
end:
  b.mu.RUnlock()
  if !found {
    atomic.AddUint64(&b.misses, 1)
  }
  return dst, found
}
```

* `b.gen` はバケットの世代でその下位24bitの値を `bGen` としている。
* `gen` は探索するキーバリューの世代。
* `gen == bGen && idx < b.idx` はキーバリューの世代がバケットの世代と同じで、キーバリューの `idx` がバケットの書き込みカーソル `b.idx` より手前の場合。
*  `gen+1 == bGen && idx >= b.idx` はバケットは次の世代に移っているが、キーバリューはまだ上書きされていない場合
* `gen == maxGen && bGen == 1 && idx >= b.idx` はキーバリューの世代は24bitの最大値 `1<<24-1` でバケットの世代の下位24bitは一周回って1になっているが、キーバリューはまだ上書きされていない場合。
* 上記3つのいずれかの場合はキーバリューの値を `chunks` から探す。
* 読む取る際に不整合が起きた場合は統計情報の `corruptions` をインクリメントしつつ、キーが見つからなかった扱いで返す。
* キーバリューを読み取って見てキーが一致しない場合はハッシュ値が衝突して上書きされていたということで統計情報の `collisions` をインクリメントしつつ、キーが見つからなかった扱いで返す。
* `returnDst` が `true` の場合は値を `dst` に `append` しつつ結果を戻り値でも返す。
* `Cache` にキーが存在するかしないかだけチェックする `Has` メソッドでは `returnDst` が `false` で呼び出される。


### Cache の Del メソッド

[fastcache.go#L182-L189](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L182-L189)

```go

// Del deletes value for the given k from the cache.
//
// k contents may be modified after returning from Del.
func (c *Cache) Del(k []byte) {
  h := xxhash.Sum64(k)
  idx := h % bucketsCount
  c.buckets[idx].Del(h)
}
```

### bucket の Del メソッド

[fastcache.go#L411-L415](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/fastcache.go#L411-L415)

```go
func (b *bucket) Del(h uint64) {
  b.mu.Lock()
  delete(b.m, h)
  b.mu.Unlock()
}
```

* 単に `b.m` から対象のキーのハッシュ値のエントリを削除するだけ。
* `b.chunks` 内のキーバリューは単なるバイト列なので放置で良い。

### malloc_mmap.go

[malloc_mmap.go](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/malloc_mmap.go)

```go
// +build !appengine,!windows

package fastcache

import (
  "fmt"
  "sync"
  "syscall"
  "unsafe"
)

const chunksPerAlloc = 1024

var (
  freeChunks     []*[chunkSize]byte
  freeChunksLock sync.Mutex
)

func getChunk() []byte {
  freeChunksLock.Lock()
  if len(freeChunks) == 0 {
    // Allocate offheap memory, so GOGC won't take into account cache size.
    // This should reduce free memory waste.
    data, err := syscall.Mmap(-1, 0, chunkSize*chunksPerAlloc, syscall.PROT_READ|syscall.PROT_WRITE, syscall.MAP_ANON|syscall.MAP_PRIVATE)
    if err != nil {
      panic(fmt.Errorf("cannot allocate %d bytes via mmap: %s", chunkSize*chunksPerAlloc, err))
    }
    for len(data) > 0 {
      p := (*[chunkSize]byte)(unsafe.Pointer(&data[0]))
      freeChunks = append(freeChunks, p)
      data = data[chunkSize:]
    }
  }
  n := len(freeChunks) - 1
  p := freeChunks[n]
  freeChunks[n] = nil
  freeChunks = freeChunks[:n]
  freeChunksLock.Unlock()
  return p[:]
}

func putChunk(chunk []byte) {
  if chunk == nil {
    return
  }
  chunk = chunk[:chunkSize]
  p := (*[chunkSize]byte)(unsafe.Pointer(&chunk[0]))

  freeChunksLock.Lock()
  freeChunks = append(freeChunks, p)
  freeChunksLock.Unlock()
}
```

* Google App Engine と Windows 以外ではこのファイルの `getChunk` と `putChunk` が利用される。
* `freeChunks` 変数は 64KiB のチャンクへのポインタのスライス。
* `freeChunks` が空の場合は `syscall.Mmap` を呼んで Go の GC の管理外でメモリを割り当てる。
* 割り当てサイズが `chunkSize` `=64KiB` ではなく `chunkSize*chunksPerAlloc` `=64MiB` にしている理由は私には不明。
* 割り当てたメモリ領域は `freeChunks` に `append` する。
* `data` 変数の指す先を `chunkSize` バイト進めた点にしているのも理由が理解できていない。 GoのGCが Mmap で割り当てったメモリ領域を解放しないようにするためか。
* `freechunks` は最後の要素から使用し、使い終わったら `putChunk` で `freeChunks` の最後に追加する。


### malloc_heap.go

[malloc_heap.go](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/malloc_heap.go)

```go
// +build appengine windows

package fastcache

func getChunk() []byte {
  return make([]byte, chunkSize)
}

func putChunk(chunk []byte) {
  // No-op.
}
```

* Google App Engine と Windows ではこのファイルの `getChunk` と `putChunk` が利用される。
* ごく素直に Go の `make` で `chunkSize` バイト数のメモリ領域を割り当てる。
* 使い終わった後の `putChunk` では解放は GC に任せればよいので何もしない。

### SetBig と GetBig に関連する定数

[bigcache.go#L10-L22](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/bigcache.go#L10-L22)

```go
// maxSubvalueLen is the maximum size of subvalue chunk.
//
// - 16 bytes are for subkey encoding
// - 4 bytes are for len(key)+len(value) encoding inside fastcache
// - 1 byte is implementation detail of fastcache
const maxSubvalueLen = chunkSize - 16 - 4 - 1

// maxKeyLen is the maximum size of key.
//
// - 16 bytes are for (hash + valueLen)
// - 4 bytes are for len(key)+len(subkey)
// - 1 byte is implementation detail of fastcache
const maxKeyLen = chunkSize - 16 - 4 - 1
```

* `SetBig` に指定可能なキーの最大長が `maxKeyLen` 。
*  64KiB 以上の値を分割して (subvalue) 保管する際の最大長が `maxSubvalueLen` 。
* 分割する際に subkey というものを作るがそれのエンコーディングに 16bit を使用する。
* key, subvalue, subkey の長さは全て 64KiB 以下なのでそれぞれ2バイトでエンコードする（が、この分を引く理由は `SetBig` と `GetBig` メソッドのコードを見ても良く分からなかった）。
* fastcache の実装詳細で1バイト使う（とコメントには書いてあるが `SetBig` と `GetBig` メソッドのコードを見ても良く分からなかった）。


### Cache の SetBig メソッド

[bigcache.go#L24-L66](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/bigcache.go#L24-L66)

```go
// SetBig sets (k, v) to c where len(v) may exceed 64KB.
//
// GetBig must be used for reading stored values.
//
// The stored entry may be evicted at any time either due to cache
// overflow or due to unlikely hash collision.
// Pass higher maxBytes value to New if the added items disappear
// frequently.
//
// It is safe to store entries smaller than 64KB with SetBig.
//
// k and v contents may be modified after returning from SetBig.
func (c *Cache) SetBig(k, v []byte) {
  atomic.AddUint64(&c.bigStats.SetBigCalls, 1)
  if len(k) > maxKeyLen {
    atomic.AddUint64(&c.bigStats.TooBigKeyErrors, 1)
    return
  }
  valueLen := len(v)
  valueHash := xxhash.Sum64(v)

  // Split v into chunks with up to 64Kb each.
  subkey := getSubkeyBuf()
  var i uint64
  for len(v) > 0 {
    subkey.B = marshalUint64(subkey.B[:0], valueHash)
    subkey.B = marshalUint64(subkey.B, uint64(i))
    i++
    subvalueLen := maxSubvalueLen
    if len(v) < subvalueLen {
      subvalueLen = len(v)
    }
    subvalue := v[:subvalueLen]
    v = v[subvalueLen:]
    c.Set(subkey.B, subvalue)
  }

  // Write metavalue, which consists of valueHash and valueLen.
  subkey.B = marshalUint64(subkey.B[:0], valueHash)
  subkey.B = marshalUint64(subkey.B, uint64(valueLen))
  c.Set(k, subkey.B)
  putSubkeyBuf(subkey)
}
```

* 値は約64KiB（正確には `maxSubvalueLen`）単位の subvalue に分割する。
* 引数の `k` には、 `v` のハッシュ値とバイト長をエンコードした値を設定する。 `uint64` (8バイト)が2つで計 16 バイト。これが `maxKeyLen` の定義で 16 引いてる分に対応。
* subvalue は `v` のハッシュ値と分割の連番をエンコードした値を subkey としてハッシュに設定する。 subkey も `uint64` 2つで `maxSubvalueLen` の16引いてる分。
* 例えば 128KiB の値だと subvalue は3つになり、 `k` と合わせて合計4エントリが追加されることになる。


### Cache の GetBig メソッド

[bigcache.go#L68-L124](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/bigcache.go#L68-L124)

```go
// GetBig searches for the value for the given k, appends it to dst
// and returns the result.
//
// GetBig returns only values stored via SetBig. It doesn't work
// with values stored via other methods.
//
// k contents may be modified after returning from GetBig.
func (c *Cache) GetBig(dst, k []byte) []byte {
  atomic.AddUint64(&c.bigStats.GetBigCalls, 1)
  subkey := getSubkeyBuf()
  defer putSubkeyBuf(subkey)

  // Read and parse metavalue
  subkey.B = c.Get(subkey.B[:0], k)
  if len(subkey.B) == 0 {
    // Nothing found.
    return dst
  }
  if len(subkey.B) != 16 {
    atomic.AddUint64(&c.bigStats.InvalidMetavalueErrors, 1)
    return dst
  }
  valueHash := unmarshalUint64(subkey.B)
  valueLen := unmarshalUint64(subkey.B[8:])

  // Collect result from chunks.
  dstLen := len(dst)
  if n := dstLen + int(valueLen) - cap(dst); n > 0 {
    dst = append(dst[:cap(dst)], make([]byte, n)...)
  }
  dst = dst[:dstLen]
  var i uint64
  for uint64(len(dst)-dstLen) < valueLen {
    subkey.B = marshalUint64(subkey.B[:0], valueHash)
    subkey.B = marshalUint64(subkey.B, uint64(i))
    i++
    dstNew := c.Get(dst, subkey.B)
    if len(dstNew) == len(dst) {
      // Cannot find subvalue
      return dst[:dstLen]
    }
    dst = dstNew
  }

  // Verify the obtained value.
  v := dst[dstLen:]
  if uint64(len(v)) != valueLen {
    atomic.AddUint64(&c.bigStats.InvalidValueLenErrors, 1)
    return dst[:dstLen]
  }
  h := xxhash.Sum64(v)
  if h != valueHash {
    atomic.AddUint64(&c.bigStats.InvalidValueHashErrors, 1)
    return dst[:dstLen]
  }
  return dst
}
```

* まず `k` に対する値を取得し、 `SetBig` で設定した値のハッシュ値と長さをデコードする。
* `GetBig` が呼ばれた時点の `dst` の長さを `dstLen` にとっておく。
* `dst` の `cap` が十分でなければ増やしておく。
* `dst` に追加した長さ `len(dst)-dstLen` が `valueLen` より小さい間は subvalue を取得して `dst` に `append` で追加していく。 subvalue 取得後に `len(dst)` が変わらなかった場合は subvalue が無かったと判断して `dst` と当初の長さに切り取って返す。subvalue を取得しつつ無かったか判定するのは今なら `HasGet` メソッドがあるのでそちらを使うべき。
* `GetBig` の呼び出し側では `len(dst)` が呼び出し前後で変わってなければ取得失敗というエラー処理を行う必要あり。最初に `dst` の `cap` を確保するところでアドレスが変わる場合があるので、アドレスが変わってなければというチェックではだめなことに注意。
* subvalue が全て取得できた場合は合計の長さのチェックと値全体のハッシュ値の突き合せチェックを行う。
