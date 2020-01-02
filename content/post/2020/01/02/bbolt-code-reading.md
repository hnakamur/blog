---
title: "bboltのコードリーディング"
date: 2020-01-02T11:00:00+09:00
---

## はじめに
[etcd-io/bbolt: An embedded key/value database for Go.](https://github.com/etcd-io/bbolt) は B+Tree を使った Go で書かれたキーバリューストアです。

[Project Status](https://github.com/etcd-io/bbolt#project-status) を見ると開発のフェーズとしては安定期に入っていて、 API、ファイルフォーマットともに stable になっています。高負荷なプロダクション環境でも使用されていて 1TB といった大きなサイズでも使われているそうです。

[bbolt importers - GoDoc](https://godoc.org/go.etcd.io/bbolt?importers) を見ると
[etcd-io/etcd: Distributed reliable key-value store for the most critical data of a distributed system](https://github.com/etcd-io/etcd) など様々なプロジェクトで使用されています。

## bbolt での B+Tree のリバランス

### 分割の際のノードの充填率

`Bucket` 型
[bucket.go#L28-L43](https://github.com/etcd-io/bbolt/blob/v1.3.3/bucket.go#L28-L43)
```go

// Bucket represents a collection of key/value pairs inside the database.
type Bucket struct {
  *bucket
  tx       *Tx                // the associated transaction
  buckets  map[string]*Bucket // subbucket cache
  page     *page              // inline page reference
  rootNode *node              // materialized node for the root page.
  nodes    map[pgid]*node     // node cache

  // Sets the threshold for filling nodes when they split. By default,
  // the bucket will fill to 50% but it can be useful to increase this
  // amount if you know that your write workloads are mostly append-only.
  //
  // This is non-persisted across transactions so it must be set in every Tx.
  FillPercent float64
}
```
`Bucket` の `FillPercent` でノード分割時の充填率を0.1～1.0の間で制御可能（下記参照）。
キーが単調増加するような追加パターンの場合は 1.0 に近い値にすると、無駄な分割が少なくノードのページの利用効率も上がる。
トランザクション毎に指定する必要がある。

`FillPercent` の利用箇所は `node` 型の `splitTwo` メソッド1か所のみ。
[node.go#L271-L310](https://github.com/etcd-io/bbolt/blob/v1.3.3/node.go#L271-L310)
```go
// splitTwo breaks up a node into two smaller nodes, if appropriate.
// This should only be called from the split() function.
func (n *node) splitTwo(pageSize int) (*node, *node) {
  // Ignore the split if the page doesn't have at least enough nodes for
  // two pages or if the nodes can fit in a single page.
  if len(n.inodes) <= (minKeysPerPage*2) || n.sizeLessThan(pageSize) {
    return n, nil
  }

  // Determine the threshold before starting a new node.
  var fillPercent = n.bucket.FillPercent
  if fillPercent < minFillPercent {
    fillPercent = minFillPercent
  } else if fillPercent > maxFillPercent {
    fillPercent = maxFillPercent
  }
  threshold := int(float64(pageSize) * fillPercent)
//…(略)…
```

充填率の定数定義
[bucket.go#L19-L22](https://github.com/etcd-io/bbolt/blob/v1.3.3/bucket.go#L19-L22)
```go
const (
  minFillPercent = 0.1
  maxFillPercent = 1.0
)
```

### ノードのマージの条件

`node` 型の `rebalance` メソッド。
[node.go#L407-L508](https://github.com/etcd-io/bbolt/blob/v1.3.3/node.go#L407-L508)
```go
// rebalance attempts to combine the node with sibling nodes if the node fill
// size is below a threshold or if there are not enough keys.
func (n *node) rebalance() {
  if !n.unbalanced {
    return
  }
  n.unbalanced = false

  // Update statistics.
  n.bucket.tx.stats.Rebalance++

  // Ignore if node is above threshold (25%) and has enough keys.
  var threshold = n.bucket.tx.db.pageSize / 4
  if n.size() > threshold && len(n.inodes) > n.minKeys() {
    return
  }

  // Root node has special handling.
  if n.parent == nil {
    // If root node is a branch and only has one node then collapse it.
    if !n.isLeaf && len(n.inodes) == 1 {
      // Move root's child up.
      child := n.bucket.node(n.inodes[0].pgid, n)
      n.isLeaf = child.isLeaf
      n.inodes = child.inodes[:]
      n.children = child.children

      // Reparent all child nodes being moved.
      for _, inode := range n.inodes {
        if child, ok := n.bucket.nodes[inode.pgid]; ok {
          child.parent = n
        }
      }

      // Remove old child.
      child.parent = nil
      delete(n.bucket.nodes, child.pgid)
      child.free()
    }

    return
  }

  // If node has no keys then just remove it.
  if n.numChildren() == 0 {
    n.parent.del(n.key)
    n.parent.removeChild(n)
    delete(n.bucket.nodes, n.pgid)
    n.free()
    n.parent.rebalance()
    return
  }

  _assert(n.parent.numChildren() > 1, "parent must have at least 2 children")

  // Destination node is right sibling if idx == 0, otherwise left sibling.
  var target *node
  var useNextSibling = (n.parent.childIndex(n) == 0)
  if useNextSibling {
    target = n.nextSibling()
  } else {
    target = n.prevSibling()
  }

  // If both this node and the target node are too small then merge them.
  if useNextSibling {
    // Reparent all child nodes being moved.
    for _, inode := range target.inodes {
      if child, ok := n.bucket.nodes[inode.pgid]; ok {
        child.parent.removeChild(child)
        child.parent = n
        child.parent.children = append(child.parent.children, child)
      }
    }

    // Copy over inodes from target and remove target.
    n.inodes = append(n.inodes, target.inodes...)
    n.parent.del(target.key)
    n.parent.removeChild(target)
    delete(n.bucket.nodes, target.pgid)
    target.free()
  } else {
    // Reparent all child nodes being moved.
    for _, inode := range n.inodes {
      if child, ok := n.bucket.nodes[inode.pgid]; ok {
        child.parent.removeChild(child)
        child.parent = target
        child.parent.children = append(child.parent.children, child)
      }
    }

    // Copy over inodes to target and remove node.
    target.inodes = append(target.inodes, n.inodes...)
    n.parent.del(n.key)
    n.parent.removeChild(n)
    delete(n.bucket.nodes, n.pgid)
    n.free()
  }

  // Either this node or the target node was deleted from the parent so rebalance it.
  n.parent.rebalance()
}
```
ノードの充填率が25%より大きくかつノード内のキー数が `minKeys` メソッドの戻り値より大きい場合はノードのリバランスは行わない。

`node` 型の `minKeys` メソッド。
[node.go#L31-L37](https://github.com/etcd-io/bbolt/blob/v1.3.3/node.go#L31-L37)
```go
// minKeys returns the minimum number of inodes this node should have.
func (n *node) minKeys() int {
  if n.isLeaf {
    return 1
  }
  return 2
}
```
最小のキー数はリーフノードは1、リーフでないノードは2。


ついでに `node` の `rebalance` メソッドの呼び出し元も調べる。
`Bucket` の `rebalance` メソッド。
[bucket.go#L630-L638](https://github.com/etcd-io/bbolt/blob/v1.3.3/bucket.go#L630-L638)
```go

// rebalance attempts to balance all nodes.
func (b *Bucket) rebalance() {
  for _, n := range b.nodes {
    n.rebalance()
  }
  for _, child := range b.buckets {
    child.rebalance()
  }
}
```

`Tx` の `Commit` メソッド。
[tx.go#L138-L223](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L138-L223)
```go
// Commit writes all changes to disk and updates the meta page.
// Returns an error if a disk write error occurs, or if Commit is
// called on a read-only transaction.
func (tx *Tx) Commit() error {
  _assert(!tx.managed, "managed tx commit not allowed")
  if tx.db == nil {
    return ErrTxClosed
  } else if !tx.writable {
    return ErrTxNotWritable
  }

  // TODO(benbjohnson): Use vectorized I/O to write out dirty pages.

  // Rebalance nodes which have had deletions.
  var startTime = time.Now()
  tx.root.rebalance()
  if tx.stats.Rebalance > 0 {
    tx.stats.RebalanceTime += time.Since(startTime)
  }

  // spill data onto dirty pages.
  startTime = time.Now()
  if err := tx.root.spill(); err != nil {
    tx.rollback()
    return err
  }
  tx.stats.SpillTime += time.Since(startTime)

  // Free the old root bucket.
  tx.meta.root.root = tx.root.root

  // Free the old freelist because commit writes out a fresh freelist.
  if tx.meta.freelist != pgidNoFreelist {
    tx.db.freelist.free(tx.meta.txid, tx.db.page(tx.meta.freelist))
  }

  if !tx.db.NoFreelistSync {
    err := tx.commitFreelist()
    if err != nil {
      return err
    }
  } else {
    tx.meta.freelist = pgidNoFreelist
  }

  // Write dirty pages to disk.
  startTime = time.Now()
  if err := tx.write(); err != nil {
    tx.rollback()
    return err
  }

  // If strict mode is enabled then perform a consistency check.
  // Only the first consistency error is reported in the panic.
  if tx.db.StrictMode {
    ch := tx.Check()
    var errs []string
    for {
      err, ok := <-ch
      if !ok {
        break
      }
      errs = append(errs, err.Error())
    }
    if len(errs) > 0 {
      panic("check fail: " + strings.Join(errs, "\n"))
    }
  }

  // Write meta to disk.
  if err := tx.writeMeta(); err != nil {
    tx.rollback()
    return err
  }
  tx.stats.WriteTime += time.Since(startTime)

  // Finalize the transaction.
  tx.close()

  // Execute commit handlers now that the locks have been removed.
  for _, fn := range tx.commitHandlers {
    fn()
  }

  return nil
}
```

## ページバッファ

`Open` 関数
[db.go#L175-L303](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L175-L303)
```go
// Open creates and opens a database at the given path.
// If the file does not exist then it will be created automatically.
// Passing in nil options will cause Bolt to open the database with the default options.
func Open(path string, mode os.FileMode, options *Options) (*DB, error) {
  db := &DB{
    opened: true,
  }
  // Set default options if no options are provided.
  if options == nil {
    options = DefaultOptions
  }
  db.NoSync = options.NoSync
  db.NoGrowSync = options.NoGrowSync
  db.MmapFlags = options.MmapFlags
  db.NoFreelistSync = options.NoFreelistSync
  db.FreelistType = options.FreelistType

  // Set default values for later DB operations.
  db.MaxBatchSize = DefaultMaxBatchSize
  db.MaxBatchDelay = DefaultMaxBatchDelay
  db.AllocSize = DefaultAllocSize

  flag := os.O_RDWR
  if options.ReadOnly {
    flag = os.O_RDONLY
    db.readOnly = true
  }

  db.openFile = options.OpenFile
  if db.openFile == nil {
    db.openFile = os.OpenFile
  }

  // Open data file and separate sync handler for metadata writes.
  db.path = path
  var err error
  if db.file, err = db.openFile(db.path, flag|os.O_CREATE, mode); err != nil {
    _ = db.close()
    return nil, err
  }

  // Lock file so that other processes using Bolt in read-write mode cannot
  // use the database  at the same time. This would cause corruption since
  // the two processes would write meta pages and free pages separately.
  // The database file is locked exclusively (only one process can grab the lock)
  // if !options.ReadOnly.
  // The database file is locked using the shared lock (more than one process may
  // hold a lock at the same time) otherwise (options.ReadOnly is set).
  if err := flock(db, !db.readOnly, options.Timeout); err != nil {
    _ = db.close()
    return nil, err
  }

  // Default values for test hooks
  db.ops.writeAt = db.file.WriteAt

  if db.pageSize = options.PageSize; db.pageSize == 0 {
    // Set the default page size to the OS page size.
    db.pageSize = defaultPageSize
  }

  // Initialize the database if it doesn't exist.
  if info, err := db.file.Stat(); err != nil {
    _ = db.close()
    return nil, err
  } else if info.Size() == 0 {
    // Initialize new files with meta pages.
    if err := db.init(); err != nil {
      // clean up file descriptor on initialization fail
      _ = db.close()
      return nil, err
    }
  } else {
    // Read the first meta page to determine the page size.
    var buf [0x1000]byte
    // If we can't read the page size, but can read a page, assume
    // it's the same as the OS or one given -- since that's how the
    // page size was chosen in the first place.
    //
    // If the first page is invalid and this OS uses a different
    // page size than what the database was created with then we
    // are out of luck and cannot access the database.
    //
    // TODO: scan for next page
    if bw, err := db.file.ReadAt(buf[:], 0); err == nil && bw == len(buf) {
      if m := db.pageInBuffer(buf[:], 0).meta(); m.validate() == nil {
        db.pageSize = int(m.pageSize)
      }
    } else {
      _ = db.close()
      return nil, ErrInvalid
    }
  }

  // Initialize page pool.
  db.pagePool = sync.Pool{
    New: func() interface{} {
      return make([]byte, db.pageSize)
    },
  }

  // Memory map the data file.
  if err := db.mmap(options.InitialMmapSize); err != nil {
    _ = db.close()
    return nil, err
  }

  if db.readOnly {
    return db, nil
  }

  db.loadFreelist()

  // Flush freelist when transitioning from no sync to sync so
  // NoFreelistSync unaware boltdb can open the db later.
  if !db.NoFreelistSync && !db.hasSyncedFreelist() {
    tx, err := db.Begin(true)
    if tx != nil {
      err = tx.Commit()
    }
    if err != nil {
      _ = db.close()
      return nil, err
    }
  }

  // Mark the database as opened and return.
  return db, nil
}
```

`flock` の `unix` (`+build !windows,!plan9,!solaris,!aix`)での実装。
[bolt_unix.go#L12-L42](https://github.com/etcd-io/bbolt/blob/v1.3.3/bolt_unix.go#L12-L42)
```go
// flock acquires an advisory lock on a file descriptor.
func flock(db *DB, exclusive bool, timeout time.Duration) error {
  var t time.Time
  if timeout != 0 {
    t = time.Now()
  }
  fd := db.file.Fd()
  flag := syscall.LOCK_NB
  if exclusive {
    flag |= syscall.LOCK_EX
  } else {
    flag |= syscall.LOCK_SH
  }
  for {
    // Attempt to obtain an exclusive lock.
    err := syscall.Flock(int(fd), flag)
    if err == nil {
      return nil
    } else if err != syscall.EWOULDBLOCK {
      return err
    }

    // If we timed out then return an error.
    if timeout != 0 && time.Since(t) > timeout-flockRetryTimeout {
      return ErrTimeout
    }

    // Wait for a bit and try again.
    time.Sleep(flockRetryTimeout)
  }
}
```
* `syscall.Flock` を呼んで `syscall.EWOULDBLOCK` が返ってきたときは以下のようにリトライ。
* `timeout` が `0` だったときは `flockRetryTimeout` の間隔で成功するか `syscall.EWOULDBLOCK` 以外のエラーになるまでリトライ。
* `timeout` が `0` 以外のときは `flock` の開始から `timeout` の間までは `flockRetryTimeout` の間隔でリトライ。

`defaultPageSize` 変数
[db.go#L40-L41](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L40-L41)
```go
// default page size for db is set to the OS page size.
var defaultPageSize = os.Getpagesize()
```
オプションでページサイズを指定しなかったときは OS のページサイズが使用される。
```go
  if db.pageSize = options.PageSize; db.pageSize == 0 {
    // Set the default page size to the OS page size.
    db.pageSize = defaultPageSize
  }
```

ページプール。ページサイズのバイト列を `sync.Pool` のオブジェクトプールで管理・再利用する。
```
  // Initialize page pool.
  db.pagePool = sync.Pool{
    New: func() interface{} {
      return make([]byte, db.pageSize)
    },
  }
```

`DB` の `mmap` メソッド
[db.go#L326-L378](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L326-L378)
```go
// mmap opens the underlying memory-mapped file and initializes the meta references.
// minsz is the minimum size that the new mmap can be.
func (db *DB) mmap(minsz int) error {
  db.mmaplock.Lock()
  defer db.mmaplock.Unlock()

  info, err := db.file.Stat()
  if err != nil {
    return fmt.Errorf("mmap stat error: %s", err)
  } else if int(info.Size()) < db.pageSize*2 {
    return fmt.Errorf("file size too small")
  }

  // Ensure the size is at least the minimum size.
  var size = int(info.Size())
  if size < minsz {
    size = minsz
  }
  size, err = db.mmapSize(size)
  if err != nil {
    return err
  }

  // Dereference all mmap references before unmapping.
  if db.rwtx != nil {
    db.rwtx.root.dereference()
  }

  // Unmap existing data before continuing.
  if err := db.munmap(); err != nil {
    return err
  }

  // Memory-map the data file as a byte slice.
  if err := mmap(db, size); err != nil {
    return err
  }

  // Save references to the meta pages.
  db.meta0 = db.page(0).meta()
  db.meta1 = db.page(1).meta()

  // Validate the meta pages. We only return an error if both meta pages fail
  // validation, since meta0 failing validation means that it wasn't saved
  // properly -- but we can recover using meta1. And vice-versa.
  err0 := db.meta0.validate()
  err1 := db.meta1.validate()
  if err0 != nil && err1 != nil {
    return err0
  }

  return nil
}
```

`DB` の `mmapSize` メソッド
[db.go#L388-L423](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L388-L423)
```go
// mmapSize determines the appropriate size for the mmap given the current size
// of the database. The minimum size is 32KB and doubles until it reaches 1GB.
// Returns an error if the new mmap size is greater than the max allowed.
func (db *DB) mmapSize(size int) (int, error) {
  // Double the size from 32KB until 1GB.
  for i := uint(15); i <= 30; i++ {
    if size <= 1<<i {
      return 1 << i, nil
    }
  }

  // Verify the requested size is not above the maximum allowed.
  if size > maxMapSize {
    return 0, fmt.Errorf("mmap too large")
  }

  // If larger than 1GB then grow by 1GB at a time.
  sz := int64(size)
  if remainder := sz % int64(maxMmapStep); remainder > 0 {
    sz += int64(maxMmapStep) - remainder
  }

  // Ensure that the mmap size is a multiple of the page size.
  // This should always be true since we're incrementing in MBs.
  pageSize := int64(db.pageSize)
  if (sz % pageSize) != 0 {
    sz = ((sz / pageSize) + 1) * pageSize
  }

  // If we've exceeded the max size then only grow up to the max size.
  if sz > maxMapSize {
    sz = maxMapSize
  }

  return int(sz), nil
}
```
* 最低 32KiB から 1GiB まで倍倍で増やして引数 `size` 以上になったらその値を返す。
* `size` が `maxMmapStep` (amd64の場合は256TiB) より多い場合はエラー。
* 256TiB 以下の場合は 1GiB 単位に切り上げ。
* 1GiB 単位に切り上げた後ページサイズ単位で切り上げ。
* 切り上げた結果が `maxMmapStep` より大きい場合は `maxMmapStep` にする。

amd64 での `maxMapSize` 定数
[bolt_amd64.go#L3-L4](https://github.com/etcd-io/bbolt/blob/v1.3.3/bolt_amd64.go#L3-L4)
```go
// maxMapSize represents the largest mmap size supported by Bolt.
const maxMapSize = 0xFFFFFFFFFFFF // 256TB
```

`mmap` 関数 (`+build !windows,!plan9,!solaris,!aix`)
[bolt_unix.go#L49-L69](https://github.com/etcd-io/bbolt/blob/v1.3.3/bolt_unix.go#L49-L69)
```go
// mmap memory maps a DB's data file.
func mmap(db *DB, sz int) error {
  // Map the data file to memory.
  b, err := syscall.Mmap(int(db.file.Fd()), 0, sz, syscall.PROT_READ, syscall.MAP_SHARED|db.MmapFlags)
  if err != nil {
    return err
  }

  // Advise the kernel that the mmap is accessed randomly.
  err = madvise(b, syscall.MADV_RANDOM)
  if err != nil && err != syscall.ENOSYS {
    // Ignore not implemented error in kernel because it still works.
    return fmt.Errorf("madvise: %s", err)
  }

  // Save the original byte slice and convert to a byte array pointer.
  db.dataref = b
  db.data = (*[maxMapSize]byte)(unsafe.Pointer(&b[0]))
  db.datasz = sz
  return nil
}
```
* `Open` 関数内で開いたファイル `db.file` に対して `syscall.Mmap` でメモリマッピングしている。 参考: [mmap (2)](https://manpages.ubuntu.com/manpages/bionic/en/man2/mmap.2.html)
* `syscall.PROT_READ` を指定しているので読み取りのみ（書き込みは mmap 経由ではなくファイル書き込みで実装している。下記参照）
* `madvise` で `syscall.MADV_RANDOM` を指定しランダムにアクセスされることをカーネルにアドヴァイスしている。
* `syscallMmap` したメモリ領域を `db.dataref` に保存。これは `syscall.Munmap` を呼ぶときにのみ使用。
* またそれを `unsafe.Pointer` 経由で `*[maxMapSize]byte` 型にキャストしたものを `db.data` に保存。

`madvise` 関数。
[bolt_unix.go#L86-L93](https://github.com/etcd-io/bbolt/blob/v1.3.3/bolt_unix.go#L86-L93)
```go
// NOTE: This function is copied from stdlib because it is not available on darwin.
func madvise(b []byte, advice int) (err error) {
  _, _, e1 := syscall.Syscall(syscall.SYS_MADVISE, uintptr(unsafe.Pointer(&b[0])), uintptr(len(b)), uintptr(advice))
  if e1 != 0 {
    err = e1
  }
  return
}
```

`db.data` の利用箇所は `DB` の `Info` メソッドと `page` メソッド。
[db.go#L877-L887](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L877-L887)
```go
// This is for internal access to the raw data bytes from the C cursor, use
// carefully, or not at all.
func (db *DB) Info() *Info {
  return &Info{uintptr(unsafe.Pointer(&db.data[0])), db.pageSize}
}

// page retrieves a page reference from the mmap based on the current page size.
func (db *DB) page(id pgid) *page {
  pos := id * pgid(db.pageSize)
  return (*page)(unsafe.Pointer(&db.data[pos]))
}
```
`Info` メソッドのコメントには C カーソルからの生のデータバイト列とあるが、コードを見ると最初のページを `Info` 型としてアクセスしている。

`Info` 型
[db.go#L1109-L1112](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L1109-L1112)
```go
type Info struct {
  Data     uintptr
  PageSize int
}
```
型定義を見ると実際のアプリケーションではあまり使い道無さそう。

## ファイルへの書き込み

`Open` 関数内で `db.ops.writeAt` に `db.file` (`*os.File` 型)の `WriteAt` メソッド [(*os.File).WriteAt](https://golang.org/pkg/os/#File.WriteAt) を指定している。
`db.file.WriteAt` を直接使用しないのはテストの際に `db.ops.writeAt` を差し替えるため。
[db.go#L228-L229](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L228-L229)
```go
  // Default values for test hooks
  db.ops.writeAt = db.file.WriteAt
```

`db.ops.writeAt` の利用箇所は以下の3か所。
* `DB` の `Init` メソッド [db.go#L425-L467](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L425-L467)
* `tx` の `write` メソッド [tx.go#L513-L584](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L513-L584)
* `tx` の `writeMeta` メソッド [tx.go#L586-L607](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L586-L607)

### `DB` の `Init` メソッドの実装
`DB` の `Init` メソッドは `Open` 関数内でファイルを `os.O_CREATE` フラグありで開いて作成したとき (ファイルサイズが 0 だったかで判定) に呼ばれる。

[db.go#L425-L467](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L425-L467)
```go
// init creates a new database file and initializes its meta pages.
func (db *DB) init() error {
  // Create two meta pages on a buffer.
  buf := make([]byte, db.pageSize*4)
  for i := 0; i < 2; i++ {
    p := db.pageInBuffer(buf[:], pgid(i))
    p.id = pgid(i)
    p.flags = metaPageFlag

    // Initialize the meta page.
    m := p.meta()
    m.magic = magic
    m.version = version
    m.pageSize = uint32(db.pageSize)
    m.freelist = 2
    m.root = bucket{root: 3}
    m.pgid = 4
    m.txid = txid(i)
    m.checksum = m.sum64()
  }

  // Write an empty freelist at page 3.
  p := db.pageInBuffer(buf[:], pgid(2))
  p.id = pgid(2)
  p.flags = freelistPageFlag
  p.count = 0

  // Write an empty leaf page at page 4.
  p = db.pageInBuffer(buf[:], pgid(3))
  p.id = pgid(3)
  p.flags = leafPageFlag
  p.count = 0

  // Write the buffer to our data file.
  if _, err := db.ops.writeAt(buf, 0); err != nil {
    return err
  }
  if err := fdatasync(db); err != nil {
    return err
  }

  return nil
}
```
* 先頭4ページの内容をセットアップしてファイルに書き込む。
* 最初の2ページはメタデータ、3ページ目は空のフリーリスト、4ページ目は空のリーフページ。

### `tx` の `write` メソッド
[tx.go#L513-L584](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L513-L584)
```go
// write writes any dirty pages to disk.
func (tx *Tx) write() error {
  // Sort pages by id.
  pages := make(pages, 0, len(tx.pages))
  for _, p := range tx.pages {
    pages = append(pages, p)
  }
  // Clear out page cache early.
  tx.pages = make(map[pgid]*page)
  sort.Sort(pages)

  // Write pages to disk in order.
  for _, p := range pages {
    size := (int(p.overflow) + 1) * tx.db.pageSize
    offset := int64(p.id) * int64(tx.db.pageSize)

    // Write out page in "max allocation" sized chunks.
    ptr := (*[maxAllocSize]byte)(unsafe.Pointer(p))
    for {
      // Limit our write to our max allocation size.
      sz := size
      if sz > maxAllocSize-1 {
        sz = maxAllocSize - 1
      }

      // Write chunk to disk.
      buf := ptr[:sz]
      if _, err := tx.db.ops.writeAt(buf, offset); err != nil {
        return err
      }

      // Update statistics.
      tx.stats.Write++

      // Exit inner for loop if we've written all the chunks.
      size -= sz
      if size == 0 {
        break
      }

      // Otherwise move offset forward and move pointer to next chunk.
      offset += int64(sz)
      ptr = (*[maxAllocSize]byte)(unsafe.Pointer(&ptr[sz]))
    }
  }

  // Ignore file sync if flag is set on DB.
  if !tx.db.NoSync || IgnoreNoSync {
    if err := fdatasync(tx.db); err != nil {
      return err
    }
  }

  // Put small pages back to page pool.
  for _, p := range pages {
    // Ignore page sizes over 1 page.
    // These are allocated using make() instead of the page pool.
    if int(p.overflow) != 0 {
      continue
    }

    buf := (*[maxAllocSize]byte)(unsafe.Pointer(p))[:tx.db.pageSize]

    // See https://go.googlesource.com/go/+/f03c9202c43e0abb130669852082117ca50aa9b1
    for i := range buf {
      buf[i] = 0
    }
    tx.db.pagePool.Put(buf)
  }

  return nil
}
```
* このコードから判断するとオーバーフローページがある(`p.overflow` が 0 より大きい)場合はメモリ上で連続して配置されているようだ。
* `maxAllocSize` 定数が 2GiB-1byte なので最大で 2GiB-2byte の塊で書き出す。

`maxAllocSize` 定数
[bolt_amd64.go#L6-L7](https://github.com/etcd-io/bbolt/blob/v1.3.3/bolt_amd64.go#L6-L7)
```go
// maxAllocSize is the size used when creating array pointers.
const maxAllocSize = 0x7FFFFFFF
```
`maxAllocSize` は2GiB-1byte。

`pages` 型
[page.go#L90-L94](https://github.com/etcd-io/bbolt/blob/v1.3.3/page.go#L90-L94)
```go
type pages []*page

func (s pages) Len() int           { return len(s) }
func (s pages) Swap(i, j int)      { s[i], s[j] = s[j], s[i] }
func (s pages) Less(i, j int) bool { return s[i].id < s[j].id }
```
ページIDの昇順でソートできるようにしてある。

`Tx` 型
[tx.go#L16-L41](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L16-L41)
```go
// Tx represents a read-only or read/write transaction on the database.
// Read-only transactions can be used for retrieving values for keys and creating cursors.
// Read/write transactions can create and remove buckets and create and remove keys.
//
// IMPORTANT: You must commit or rollback transactions when you are done with
// them. Pages can not be reclaimed by the writer until no more transactions
// are using them. A long running read transaction can cause the database to
// quickly grow.
type Tx struct {
  writable       bool
  managed        bool
  db             *DB
  meta           *meta
  root           Bucket
  pages          map[pgid]*page
  stats          TxStats
  commitHandlers []func()

  // WriteFlag specifies the flag for write-related methods like WriteTo().
  // Tx opens the database file with the specified flag to copy the data.
  //
  // By default, the flag is unset, which works well for mostly in-memory
  // workloads. For databases that are much larger than available RAM,
  // set the flag to syscall.O_DIRECT to avoid trashing the page cache.
  WriteFlag int
}
```
`Tx` 型の `pages` フィールドは `map[pgid]*page` 型。

`Tx` 型の `page` メソッド
[tx.go#L609-L621](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L609-L621)
```go
// page returns a reference to the page with a given id.
// If page has been written to then a temporary buffered page is returned.
func (tx *Tx) page(id pgid) *page {
  // Check the dirty pages first.
  if tx.pages != nil {
    if p, ok := tx.pages[id]; ok {
      return p
    }
  }

  // Otherwise return directly from the mmap.
  return tx.db.page(id)
}
```
のコメントによると `Tx` の `pages` フィールドにはダーティページ（ページの内容を変更したのでファイルに書き戻す必要があるページ）が保持されている。

### `Tx` の `writeMeta` メソッド
[tx.go#L586-L607](https://github.com/etcd-io/bbolt/blob/v1.3.3/tx.go#L586-L607)
```go
// writeMeta writes the meta to the disk.
func (tx *Tx) writeMeta() error {
  // Create a temporary buffer for the meta page.
  buf := make([]byte, tx.db.pageSize)
  p := tx.db.pageInBuffer(buf, 0)
  tx.meta.write(p)

  // Write the meta page to file.
  if _, err := tx.db.ops.writeAt(buf, int64(p.id)*int64(tx.db.pageSize)); err != nil {
    return err
  }
  if !tx.db.NoSync || IgnoreNoSync {
    if err := fdatasync(tx.db); err != nil {
      return err
    }
  }

  // Update statistics.
  tx.stats.Write++

  return nil
}
```

`DB` の `pageInBuffer` メソッド
[db.go#L889-L892](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L889-L892)
```go
// pageInBuffer retrieves a page reference from a given byte array based on the current page size.
func (db *DB) pageInBuffer(b []byte, id pgid) *page {
  return (*page)(unsafe.Pointer(&b[id*pgid(db.pageSize)]))
}
```

`pgid` 型
[page.go#L28](https://github.com/etcd-io/bbolt/blob/v1.3.3/page.go#L28)
```go
type pgid uint64
```

`page` 型
[page.go#L30-L36](https://github.com/etcd-io/bbolt/blob/v1.3.3/page.go#L30-L36)
```go

type page struct {
  id       pgid
  flags    uint16
  count    uint16
  overflow uint32
  ptr      uintptr
}
```

### `fdatasync` 関数
`fdatasync` 関数の Linux 用実装
[bolt_linux.go#L7-L10](https://github.com/etcd-io/bbolt/blob/v1.3.3/bolt_linux.go#L7-L10)
```go
// fdatasync flushes written data to a file descriptor.
func fdatasync(db *DB) error {
  return syscall.Fdatasync(int(db.file.Fd()))
}
```
* 参考: [fsync(2), fdatasync(2)](https://manpages.ubuntu.com/manpages/bionic/en/man2/fdatasync.2.html)

#### 参考: `(*os.File).Sync` メソッド

参考: [\(*os.File\).Sync](https://golang.org/pkg/os/#File.Sync) メソッドは `fsync` 。
[os/file_posix.go#L106-L117](https://github.com/golang/go/blob/go1.13.5/src/os/file_posix.go#L106-L117)

`os.File` 型
[os/types.go#L15-L18](https://github.com/golang/go/blob/go1.13.5/src/os/types.go#L15-L18)
```go
// File represents an open file descriptor.
type File struct {
  *file // os specific
}
```

unix での `file` 型
[os/file_unix.go#L45-L56](https://github.com/golang/go/blob/go1.13.5/src/os/file_unix.go#L45-L56)
```go
// file is the real representation of *File.
// The extra level of indirection ensures that no clients of os
// can overwrite this data, which could cause the finalizer
// to close the wrong file descriptor.
type file struct {
  pfd         poll.FD
  name        string
  dirinfo     *dirInfo // nil unless directory being read
  nonblock    bool     // whether we set nonblocking mode
  stdoutOrErr bool     // whether this is stdout or stderr
  appendMode  bool     // whether file is opened for appending
}
```

`internal/poll.FD` 型の `Fsync` メソッド
[internal/poll/fd_fsync_posix.go#L11-L18](https://github.com/golang/go/blob/go1.13.5/src/internal/poll/fd_fsync_posix.go#L11-L18)
```go
// Fsync wraps syscall.Fsync.
func (fd *FD) Fsync() error {
  if err := fd.incref(); err != nil {
    return err
  }
  defer fd.decref()
  return syscall.Fsync(fd.Sysfd)
}
```

### `fdatasync` 関数が呼ばれる条件

* `Tx` の `write` メソッドと `writeMeta` メソッドでは `!tx.db.NoSync || IgnoreNoSync` のときは呼ばれる。
* `Tx` の `commit` メソッドでは常に呼ばれる。

`IgnoreNoSync` 変数。 OS が OpenBSD の場合は `true` 。
[db.go#L27-L31](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L27-L31)
```go
// IgnoreNoSync specifies whether the NoSync field of a DB is ignored when
// syncing changes to a file.  This is required as some operating systems,
// such as OpenBSD, do not have a unified buffer cache (UBC) and writes
// must be synchronized using the msync(2) syscall.
const IgnoreNoSync = runtime.GOOS == "openbsd"
```

`db.Nosync` フィールドは `Open` 関数で `options.NoSync` で設定される。
[db.go#L186](https://github.com/etcd-io/bbolt/blob/v1.3.3/db.go#L186)
```go
  db.NoSync = options.NoSync
```

今回はここまで。
