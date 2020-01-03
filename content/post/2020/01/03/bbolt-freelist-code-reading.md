---
title: "bboltのフリーリストのコードリーディング"
date: 2020-01-03T20:21:58+09:00
---

## `freelist` 型と関連する型
[freelist.go#L9-L36](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L9-L36)
```go
// txPending holds a list of pgids and corresponding allocation txns
// that are pending to be freed.
type txPending struct {
  ids              []pgid
  alloctx          []txid // txids allocating the ids
  lastReleaseBegin txid   // beginning txid of last matching releaseRange
}

// pidSet holds the set of starting pgids which have the same span size
type pidSet map[pgid]struct{}

// freelist represents a list of all pages that are available for allocation.
// It also tracks pages that have been freed but are still in use by open transactions.
type freelist struct {
  freelistType   FreelistType                // freelist type
  ids            []pgid                      // all free and available free page ids.
  allocs         map[pgid]txid               // mapping of txid that allocated a pgid.
  pending        map[txid]*txPending         // mapping of soon-to-be free page ids by tx.
  cache          map[pgid]bool               // fast lookup of all free and pending page ids.
  freemaps       map[uint64]pidSet           // key is the size of continuous pages(span), value is a set which contains the starting pgids of same size
  forwardMap     map[pgid]uint64             // key is start pgid, value is its span size
  backwardMap    map[pgid]uint64             // key is end pgid, value is its span size
  allocate       func(txid txid, n int) pgid // the freelist allocate func
  free_count     func() int                  // the function which gives you free page number
  mergeSpans     func(ids pgids)             // the mergeSpan func
  getFreePageIDs func() []pgid               // get free pgids func
  readIDs        func(pgids []pgid)          // readIDs func reads list of pages and init the freelist
}
```

`FreelistType` 型
[db.go#L46-L54](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L46-L54)
```go
// FreelistType is the type of the freelist backend
type FreelistType string

const (
  // FreelistArrayType indicates backend freelist type is array
  FreelistArrayType = FreelistType("array")
  // FreelistMapType indicates backend freelist type is hashmap
  FreelistMapType = FreelistType("hashmap")
)
```

`newFreelist` 関数
[freelist.go#L38-L65](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L38-L65)
```go
// newFreelist returns an empty, initialized freelist.
func newFreelist(freelistType FreelistType) *freelist {
  f := &freelist{
    freelistType: freelistType,
    allocs:       make(map[pgid]txid),
    pending:      make(map[txid]*txPending),
    cache:        make(map[pgid]bool),
    freemaps:     make(map[uint64]pidSet),
    forwardMap:   make(map[pgid]uint64),
    backwardMap:  make(map[pgid]uint64),
  }

  if freelistType == FreelistMapType {
    f.allocate = f.hashmapAllocate
    f.free_count = f.hashmapFreeCount
    f.mergeSpans = f.hashmapMergeSpans
    f.getFreePageIDs = f.hashmapGetFreePageIDs
    f.readIDs = f.hashmapReadIDs
  } else {
    f.allocate = f.arrayAllocate
    f.free_count = f.arrayFreeCount
    f.mergeSpans = f.arrayMergeSpans
    f.getFreePageIDs = f.arrayGetFreePageIDs
    f.readIDs = f.arrayReadIDs
  }

  return f
}
```
`freelist` のバックエンド実装は `hashmap` と `array` の2種類があり、 `allocate`, `free_count`, `mergeSpans`, `getFreePageIDs`, `readIDs` メソッドがバックエンド毎に実装されている。

## array ベースのバックエンド実装

### `arrayAllocate` メソッド

[freelist.go#L107-L149](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L107-L149)
```go
// arrayAllocate returns the starting page id of a contiguous list of pages of a given size.
// If a contiguous block cannot be found then 0 is returned.
func (f *freelist) arrayAllocate(txid txid, n int) pgid {
  if len(f.ids) == 0 {
    return 0
  }

  var initial, previd pgid
  for i, id := range f.ids {
    if id <= 1 {
      panic(fmt.Sprintf("invalid page allocation: %d", id))
    }

    // Reset initial page if this is not contiguous.
    if previd == 0 || id-previd != 1 {
      initial = id
    }

    // If we found a contiguous block then remove it and return it.
    if (id-initial)+1 == pgid(n) {
      // If we're allocating off the beginning then take the fast path
      // and just adjust the existing slice. This will use extra memory
      // temporarily but the append() in free() will realloc the slice
      // as is necessary.
      if (i + 1) == n {
        f.ids = f.ids[i+1:]
      } else {
        copy(f.ids[i-n+1:], f.ids[i+1:])
        f.ids = f.ids[:len(f.ids)-n]
      }

      // Remove from the free cache.
      for i := pgid(0); i < pgid(n); i++ {
        delete(f.cache, initial+i)
      }
      f.allocs[initial] = txid
      return initial
    }

    previd = id
  }
  return 0
}
```
* `f.ids` にはfreeなページIDが昇順で格納されている。
* `f.ids` 内でページIDが `n` 個連続で並んでいる個所（つまり連続で `n` ページ空いている個所）を探す。
* 見つかったら、先頭のページIDを `initial` にセットして変える。
* また見つかった領域は `f.ids` からは削除し、 `f.cache` からも見つかった領域のすべてのページIDを削除。 `f.allocs` には先頭ページIDから引数のトランザクションID `txid` をセットする。

### `arrayFreeCount` メソッド
[freelist.go#L82-L85](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L82-L85)
```go
// arrayFreeCount returns count of free pages(array version)
func (f *freelist) arrayFreeCount() int {
  return len(f.ids)
}
```
`f.ids` の長さがそのまま free なページ数になる。

### `arrayMergeSpans` メソッド
[freelist.go#L388-L392](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L388-L392)
```go
// arrayMergeSpans try to merge list of pages(represented by pgids) with existing spans but using array
func (f *freelist) arrayMergeSpans(ids pgids) {
  sort.Sort(ids)
  f.ids = pgids(f.ids).merge(ids)
}
```
* 引数の `pgids` はソートされていないかもしれないのでまずソート。
* `pgids` 型の `merge` メソッドを呼んで `f.ids` とソートした `ids` をマージする。


### `arrayGetFreePageIDs` メソッド
[freelist.go#L298-L300](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L298-L300)
```go
func (f *freelist) arrayGetFreePageIDs() []pgid {
  return f.ids
}
```
`f.ids` をそのまま返すだけ。

### `arrayReadIDs` メソッド
[freelist.go#L292-L296](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L292-L296)
```go
// arrayReadIDs initializes the freelist from a given list of ids.
func (f *freelist) arrayReadIDs(ids []pgid) {
  f.ids = ids
  f.reindex()
}
```
引数の `ids` を `f.ids` にそのままセットして、 `reindex` メソッドを呼ぶだけ。

## hashmap ベースのバックエンド実装
### `hashmapAllocate` メソッド
[freelist_hmap.go#L15-L61](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L15-L61)
```go
// hashmapAllocate serves the same purpose as arrayAllocate, but use hashmap as backend
func (f *freelist) hashmapAllocate(txid txid, n int) pgid {
  if n == 0 {
    return 0
  }

  // if we have a exact size match just return short path
  if bm, ok := f.freemaps[uint64(n)]; ok {
    for pid := range bm {
      // remove the span
      f.delSpan(pid, uint64(n))

      f.allocs[pid] = txid

      for i := pgid(0); i < pgid(n); i++ {
        delete(f.cache, pid+pgid(i))
      }
      return pid
    }
  }

  // lookup the map to find larger span
  for size, bm := range f.freemaps {
    if size < uint64(n) {
      continue
    }

    for pid := range bm {
      // remove the initial
      f.delSpan(pid, uint64(size))

      f.allocs[pid] = txid

      remain := size - uint64(n)

      // add remain span
      f.addSpan(pid+pgid(n), remain)

      for i := pgid(0); i < pgid(n); i++ {
        delete(f.cache, pid+pgid(i))
      }
      return pid
    }
  }

  return 0
}
```
* `f.freemaps` は連続空きページ数をキー、 `pidSet` を値とする map になっている。
* `f.freemaps` に引数で指定された連続空きページ数 `n` のエントリがあれば、 `pidSet` から1つページIDを取得して返す。 `f.allocs` にトランザクションIDをセットし、 `f.cache` から連続領域のページIDを削除。
* `f.freemaps` に引数で指定された連続空きページ数 `n` のエントリがない場合は、 `f.freemaps` の全エントリを順番に見て、希望の連続空きページ数より多いエントリの最初のものから希望の連続ページ数だけ切り出して返す。差分の連続空きページ数は新たに `f.freemaps` に追加しておく。

`addSpan` と `delSpan` メソッド
[freelist_hmap.go#L125-L142](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L125-L142)
```go
func (f *freelist) addSpan(start pgid, size uint64) {
  f.backwardMap[start-1+pgid(size)] = size
  f.forwardMap[start] = size
  if _, ok := f.freemaps[size]; !ok {
    f.freemaps[size] = make(map[pgid]struct{})
  }

  f.freemaps[size][start] = struct{}{}
}

func (f *freelist) delSpan(start pgid, size uint64) {
  delete(f.forwardMap, start)
  delete(f.backwardMap, start+pgid(size-1))
  delete(f.freemaps[size], start)
  if len(f.freemaps[size]) == 0 {
    delete(f.freemaps, size)
  }
}
```

 `hashmapFreeCount` メソッド
[freelist_hmap.go#L5-L13](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L5-L13)
```go
// hashmapFreeCount returns count of free pages(hashmap version)
func (f *freelist) hashmapFreeCount() int {
  // use the forwardmap to get the total count
  count := 0
  for _, size := range f.forwardMap {
    count += int(size)
  }
  return count
}
```
`f.forwardMap` の値の合計を返す。

### `hashmapMergeSpans` メソッド
[freelist_hmap.go#L89-L95](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L89-L95)
```go
// hashmapMergeSpans try to merge list of pages(represented by pgids) with existing spans
func (f *freelist) hashmapMergeSpans(ids pgids) {
  for _, id := range ids {
    // try to see if we can merge and update
    f.mergeWithExistingSpan(id)
  }
}
```

`mergeWithExistingSpan` メソッド
[freelist_hmap.go#L97-L123](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L97-L123)
```go
// mergeWithExistingSpan merges pid to the existing free spans, try to merge it backward and forward
func (f *freelist) mergeWithExistingSpan(pid pgid) {
  prev := pid - 1
  next := pid + 1

  preSize, mergeWithPrev := f.backwardMap[prev]
  nextSize, mergeWithNext := f.forwardMap[next]
  newStart := pid
  newSize := uint64(1)

  if mergeWithPrev {
    //merge with previous span
    start := prev + 1 - pgid(preSize)
    f.delSpan(start, preSize)

    newStart -= pgid(preSize)
    newSize += preSize
  }

  if mergeWithNext {
    // merge with next span
    f.delSpan(next, nextSize)
    newSize += nextSize
  }

  f.addSpan(newStart, newSize)
}
```

### `hashmapGetFreePageIDs` メソッド
[freelist_hmap.go#L71-L87](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L71-L87)
```go
// hashmapGetFreePageIDs returns the sorted free page ids
func (f *freelist) hashmapGetFreePageIDs() []pgid {
  count := f.free_count()
  if count == 0 {
    return nil
  }

  m := make([]pgid, 0, count)
  for start, size := range f.forwardMap {
    for i := 0; i < int(size); i++ {
      m = append(m, start+pgid(i))
    }
  }
  sort.Sort(pgids(m))

  return m
}
```

### `hashmapReadIDs` メソッド
[freelist_hmap.go#L63-L69](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist_hmap.go#L63-L69)
```go
// hashmapReadIDs reads pgids as input an initial the freelist(hashmap version)
func (f *freelist) hashmapReadIDs(pgids []pgid) {
  f.init(pgids)

  // Rebuild the page cache.
  f.reindex()
}
```

## `free` メソッド
[freelist.go#L151-L182](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L151-L182)
```go
// free releases a page and its overflow for a given transaction id.
// If the page is already free then a panic will occur.
func (f *freelist) free(txid txid, p *page) {
  if p.id <= 1 {
    panic(fmt.Sprintf("cannot free page 0 or 1: %d", p.id))
  }

  // Free page and all its overflow pages.
  txp := f.pending[txid]
  if txp == nil {
    txp = &txPending{}
    f.pending[txid] = txp
  }
  allocTxid, ok := f.allocs[p.id]
  if ok {
    delete(f.allocs, p.id)
  } else if (p.flags & freelistPageFlag) != 0 {
    // Freelist is always allocated by prior tx.
    allocTxid = txid - 1
  }

  for id := p.id; id <= p.id+pgid(p.overflow); id++ {
    // Verify that page is not already free.
    if f.cache[id] {
      panic(fmt.Sprintf("page %d already freed", id))
    }
    // Add to the freelist and cache.
    txp.ids = append(txp.ids, id)
    txp.alloctx = append(txp.alloctx, allocTxid)
    f.cache[id] = true
  }
}
```

## `release` メソッド
[freelist.go#L184-L196](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L184-L196)
```go
// release moves all page ids for a transaction id (or older) to the freelist.
func (f *freelist) release(txid txid) {
  m := make(pgids, 0)
  for tid, txp := range f.pending {
    if tid <= txid {
      // Move transaction's pending pages to the available freelist.
      // Don't remove from the cache since the page is still free.
      m = append(m, txp.ids...)
      delete(f.pending, tid)
    }
  }
  f.mergeSpans(m)
}
```

## `releaseRange` メソッド
[freelist.go#L198-L229](https://github.com/etcd-io/bbolt/blob/v1.3.3/freelist.go#L198-L229)
```go
// releaseRange moves pending pages allocated within an extent [begin,end] to the free list.
func (f *freelist) releaseRange(begin, end txid) {
  if begin > end {
    return
  }
  var m pgids
  for tid, txp := range f.pending {
    if tid < begin || tid > end {
      continue
    }
    // Don't recompute freed pages if ranges haven't updated.
    if txp.lastReleaseBegin == begin {
      continue
    }
    for i := 0; i < len(txp.ids); i++ {
      if atx := txp.alloctx[i]; atx < begin || atx > end {
        continue
      }
      m = append(m, txp.ids[i])
      txp.ids[i] = txp.ids[len(txp.ids)-1]
      txp.ids = txp.ids[:len(txp.ids)-1]
      txp.alloctx[i] = txp.alloctx[len(txp.alloctx)-1]
      txp.alloctx = txp.alloctx[:len(txp.alloctx)-1]
      i--
    }
    txp.lastReleaseBegin = begin
    if len(txp.ids) == 0 {
      delete(f.pending, tid)
    }
  }
  f.mergeSpans(m)
}
```
