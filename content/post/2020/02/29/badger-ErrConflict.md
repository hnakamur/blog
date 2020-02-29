---
title: "BadgerのErrConflictについて"
date: 2020-02-29T16:34:32+09:00
---
## はじめに

[badger の README.md](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md) の [Read-write transactions](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md#read-write-transactions) に `ErrConflict` について以下のように説明があります。

> An ErrConflict error will be reported in case of a conflict. Depending on the state of your application, you have the option to retry the operation if you receive this error.

一方 `DB` の `NewWriteBatch` メソッドの API ドキュメントに blind writes は `ErrConflict` が起きないと書かれています。
[batch.go#L35-L39](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L35-L39)
```
// NewWriteBatch creates a new WriteBatch. This provides a way to conveniently do a lot of writes,
// batching them up as tightly as possible in a single transaction and using callbacks to avoid
// waiting for them to commit, thus achieving good performance. This API hides away the logic of
// creating and committing transactions. Due to the nature of SSI guaratees provided by Badger,
// blind writes can never encounter transaction conflicts (ErrConflict).
```

`ErrConflict` は具体的にどういうときに起きるか気になったのでコードを読みました。

## `ErrConflict` を返している個所

`Txn` の `commitAndSend` メソッド内の 1 箇所です。
[txn.go#L466-L469](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L466-L469)
```go
  commitTs := orc.newCommitTs(txn)
  if commitTs == 0 {
    return nil, ErrConflict
  }
```

`oracle` の `newCommitTs` メソッド
[txn.go#L167-L191](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L167-L191)
```go
func (o *oracle) newCommitTs(txn *Txn) uint64 {
	o.Lock()
	defer o.Unlock()

	if o.hasConflict(txn) {
		return 0
	}

	var ts uint64
	if !o.isManaged {
		// This is the general case, when user doesn't specify the read and commit ts.
		ts = o.nextTxnTs
		o.nextTxnTs++
		o.txnMark.Begin(ts)

	} else {
		// If commitTs is set, use it instead.
		ts = txn.commitTs
	}

	for _, w := range txn.writes {
		o.commits[w] = ts // Update the commitTs.
	}
	return ts
}
```


`oracle` の `hasConflict` メソッド
[txn.go#L152-L165](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L152-L165)
```go
// hasConflict must be called while having a lock.
func (o *oracle) hasConflict(txn *Txn) bool {
	if len(txn.reads) == 0 {
		return false
	}
	for _, ro := range txn.reads {
		// A commit at the read timestamp is expected.
		// But, any commit after the read timestamp should cause a conflict.
		if ts, has := o.commits[ro]; has && ts > txn.readTs {
			return true
		}
	}
	return false
}
```
`Txn` の `reads` フィールドと `oracle` の `commit` フィールドを突き合せてコンフリクトがあるかを判定しています。

## `oracle` の `commits` フィールド

`oracle` 構造体
[txn.go#L34-L59](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L34-L59)
```go
type oracle struct {
	// A 64-bit integer must be at the top for memory alignment. See issue #311.
	refCount  int64
	isManaged bool // Does not change value, so no locking required.

	sync.Mutex // For nextTxnTs and commits.
	// writeChLock lock is for ensuring that transactions go to the write
	// channel in the same order as their commit timestamps.
	writeChLock sync.Mutex
	nextTxnTs   uint64

	// Used to block NewTransaction, so all previous commits are visible to a new read.
	txnMark *y.WaterMark

	// Either of these is used to determine which versions can be permanently
	// discarded during compaction.
	discardTs uint64       // Used by ManagedDB.
	readMark  *y.WaterMark // Used by DB.

	// commits stores a key fingerprint and latest commit counter for it.
	// refCount is used to clear out commits map to avoid a memory blowup.
	commits map[uint64]uint64

	// closer is used to stop watermarks.
	closer *y.Closer
}
```

`commits` フィールドの値を更新しているのは上記にもある `oracle` の `newCommitTs` メソッド内の 1 箇所だけでした。

[txn.go#L187-L189](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L187-L189)
```go
	for _, w := range txn.writes {
		o.commits[w] = ts // Update the commitTs.
	}
```

`oracle` の `decrRef` メソッド内で `commits` のマップを作り直す場合があります。
[txn.go#L99-L101](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L99-L101)
```go
	if len(o.commits) >= 1000 { // If the map is still small, let it slide.
		o.commits = make(map[uint64]uint64)
	}
```

## `Txn` の `reads` フィールドの更新箇所

`Txn` 構造体
[txn.go#L201-L218](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L201-L218)
```go
// Txn represents a Badger transaction.
type Txn struct {
	readTs   uint64
	commitTs uint64

	update bool     // update is used to conditionally keep track of reads.
	reads  []uint64 // contains fingerprints of keys read.
	writes []uint64 // contains fingerprints of keys written.

	pendingWrites map[string]*Entry // cache stores any writes done by txn.

	db        *DB
	discarded bool

	size         int64
	count        int64
	numIterators int32
}
```

`Txn` の `reads` は `addReadKey` メソッドで追加されていました。
[txn.go#L429-L434](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L429-L434)
```go
func (txn *Txn) addReadKey(key []byte) {
	if txn.update {
		fp := z.MemHash(key)
		txn.reads = append(txn.reads, fp)
	}
}
```
`txn.update` が true つまり read-write トランザクションの場合のみ追加されます。

### `z.MemHash` 関数

`z.MemHash` は [dgraph-io/ristretto: A high performance memory-bound Go cache](https://github.com/dgraph-io/ristretto) で定義されています。
[ristretto/z/rtutil.go#L37-L52](https://github.com/dgraph-io/ristretto/blob/8f368f2f2ab3a54cbe62fb9772cd75ce55e07802/z/rtutil.go#L37-L52)
```go
type stringStruct struct {
	str unsafe.Pointer
	len int
}

//go:noescape
//go:linkname memhash runtime.memhash
func memhash(p unsafe.Pointer, h, s uintptr) uintptr

// MemHash is the hash function used by go map, it utilizes available hardware instructions(behaves
// as aeshash if aes instruction is available).
// NOTE: The hash seed changes for every process. So, this cannot be used as a persistent hash.
func MemHash(data []byte) uint64 {
	ss := (*stringStruct)(unsafe.Pointer(&data))
	return uint64(memhash(ss.str, 0, uintptr(ss.len)))
}
```

`//go:linkname` というコメントを使って `runtime` パッケージの `memhash` という非公開関数を呼び出しています。
Go 1.14 以降であれば [hash/maphash](https://golang.org/pkg/hash/maphash/) を使うところでしょうが、それ以前に作られたのでこのような実装になっています。

本題に戻ると `z.MemHash` は処理内容としてはバイト列のハッシュ値を計算しているということになります。

## `Txn` の `addReadKey` メソッドの呼び出し箇所

2 箇所あります。

1. `Txn` の `Get` メソッド内。
[txn.go#L401-L403](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L401-L403)
```go
		// Only track reads if this is update txn. No need to track read if txn serviced it
		// internally.
		txn.addReadKey(key)
```

2. `Iterator` の `Item` メソッド内。
[iterator.go#L504](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/iterator.go#L504)
```go
	tx.addReadKey(it.item.Key())
```

## `Txn` の `writes` フィールドの更新箇所

`Txn` の `modify` メソッド内の 1 箇所です。
[txn.go#L335-L336](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L335-L336)
```go
	fp := z.MemHash(e.Key) // Avoid dealing with byte arrays.
	txn.writes = append(txn.writes, fp)
```

`Txn` の `modify` メソッドの呼び出しは `SetEntry` と `Delete` メソッドの 2 箇所です。
[txn.go#L350-L373](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L350-L373)
```go
// SetEntry takes an Entry struct and adds the key-value pair in the struct,
// along with other metadata to the database.
//
// The current transaction keeps a reference to the entry passed in argument.
// Users must not modify the entry until the end of the transaction.
func (txn *Txn) SetEntry(e *Entry) error {
	return txn.modify(e)
}

// Delete deletes a key.
//
// This is done by adding a delete marker for the key at commit timestamp.  Any
// reads happening before this timestamp would be unaffected. Any reads after
// this commit would see the deletion.
//
// The current transaction keeps a reference to the key byte slice argument.
// Users must not modify the key until the end of the transaction.
func (txn *Txn) Delete(key []byte) error {
	e := &Entry{
		Key:  key,
		meta: bitDelete,
	}
	return txn.modify(e)
}
```

## `Txn` の `readTs` の設定箇所

`Txn` の `readTs` は `DB` の `newTransaction` メソッド内で設定されていました。

[txn.go#L653-L667](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L653-L667)
```go
	// It is important that the oracle addRef happens BEFORE we retrieve a read
	// timestamp. Otherwise, it is possible that the oracle commit map would
	// become nil after we get the read timestamp.
	// The sequence of events can be:
	// 1. This txn gets a read timestamp.
	// 2. Another txn working on the same keyset commits them, and decrements
	//    the reference to oracle.
	// 3. Oracle ref reaches zero, resetting commit map.
	// 4. This txn increments the oracle reference.
	// 5. Now this txn would go on to commit the keyset, and no conflicts
	//    would be detected.
	// See issue: https://github.com/dgraph-io/badger/issues/574
	if !isManaged {
		txn.readTs = db.orc.readTs()
	}
```
上記のコメントの先頭に read timestamp を取得する前に oracle addRef を実行することが重要とありますが、このコメントの直前で呼んでいます。

`oracle` の `readTs` メソッド。
[txn.go#L104-L121](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L104-L121)
```go
func (o *oracle) readTs() uint64 {
	if o.isManaged {
		panic("ReadTs should not be retrieved for managed DB")
	}

	var readTs uint64
	o.Lock()
	readTs = o.nextTxnTs - 1
	o.readMark.Begin(readTs)
	o.Unlock()

	// Wait for all txns which have no conflicts, have been assigned a commit
	// timestamp and are going through the write to value log and LSM tree
	// process. Not waiting here could mean that some txns which have been
	// committed would not be read.
	y.Check(o.txnMark.WaitForMark(context.Background(), readTs))
	return readTs
}
```

## `oracle` の `nextTxnTs` の更新箇所

以下の 5 箇所です。

1. `oracle` の `newCommitTs` メソッド内。
[txn.go#L177-L180](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L177-L180)
```go
		// This is the general case, when user doesn't specify the read and commit ts.
		ts = o.nextTxnTs
		o.nextTxnTs++
		o.txnMark.Begin(ts)
```

2. `oracle` の `incrementNextTs` メソッド内。
[txn.go#L129-L133](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L129-L133)
```go
func (o *oracle) incrementNextTs() {
	o.Lock()
	defer o.Unlock()
	o.nextTxnTs++
}
```

3. `StreamWriter` の `Flush` メソッド内。
[stream_writer.go#L235](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/stream_writer.go#L235)
```go
		sw.db.orc.nextTxnTs = sw.maxVersion
```

4. `DB` の `Load` メソッド内。
[backup.go#L241-L245](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/backup.go#L241-L245)
```go
			// Update nextTxnTs, memtable stores this
			// timestamp in badger head when flushed.
			if kv.Version >= db.orc.nextTxnTs {
				db.orc.nextTxnTs = kv.Version + 1
			}
```

5. `DB` の `replayFunction` メソッドで返す関数 `func(Entry, valuePointer) error` 内。
[db.go#L125-L127](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L125-L127)
```go
		if db.orc.nextTxnTs < y.ParseTs(e.Key) {
			db.orc.nextTxnTs = y.ParseTs(e.Key)
		}
```

## `oracle` の `incrementNextTs` の呼び出し箇所
以下の 2 箇所です。

1. `Open` 関数。
[db.go#L373](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L373)
```go
	db.orc.incrementNextTs()
```

2. `StreamWriter` の `Flush` メソッド内。
[stream_writer.go#L238](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/stream_writer.go#L238)
```go
		sw.db.orc.incrementNextTs()
```

## `oracle` の `newCommitTs` の呼び出し元

`oracle` の `newCommitTs` メソッドの呼び出し元は `commitAndSend` メソッド内の 1 箇所です（この記事の冒頭参照）。

`Txn` の `commitAndSend` メソッドの呼び出し元は以下の 2 箇所です。

1. `Txn` の `Commit` メソッド内。
[txn.go#L546](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L546)
[txn.go#L520-L555](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L520-L555)
```go
// Commit commits the transaction, following these steps:
//
// 1. If there are no writes, return immediately.
//
// 2. Check if read rows were updated since txn started. If so, return ErrConflict.
//
// 3. If no conflict, generate a commit timestamp and update written rows' commit ts.
//
// 4. Batch up all writes, write them to value log and LSM tree.
//
// 5. If callback is provided, Badger will return immediately after checking
// for conflicts. Writes to the database will happen in the background.  If
// there is a conflict, an error will be returned and the callback will not
// run. If there are no conflicts, the callback will be called in the
// background upon successful completion of writes or any error during write.
//
// If error is nil, the transaction is successfully committed. In case of a non-nil error, the LSM
// tree won't be updated, so there's no need for any rollback.
func (txn *Txn) Commit() error {
	txn.commitPrecheck() // Precheck before discarding txn.
	defer txn.Discard()

	if len(txn.writes) == 0 {
		return nil // Nothing to do.
	}

	txnCb, err := txn.commitAndSend()
	if err != nil {
		return err
	}
	// If batchSet failed, LSM would not have been updated. So, no need to rollback anything.

	// TODO: What if some of the txns successfully make it to value log, but others fail.
	// Nothing gets updated to LSM, until a restart happens.
	return txnCb()
}
```
メソッドのコメントの 2. が `commitAndSend` メソッドの呼び出しに対応していてエラーが返ってきたらそれを返します。


2. `Txn` の `CommitWith` メソッド内。
[txn.go#L579-L606](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L579-L606)
```go
// CommitWith acts like Commit, but takes a callback, which gets run via a
// goroutine to avoid blocking this function. The callback is guaranteed to run,
// so it is safe to increment sync.WaitGroup before calling CommitWith, and
// decrementing it in the callback; to block until all callbacks are run.
func (txn *Txn) CommitWith(cb func(error)) {
	txn.commitPrecheck() // Precheck before discarding txn.
	defer txn.Discard()

	if cb == nil {
		panic("Nil callback provided to CommitWith")
	}

	if len(txn.writes) == 0 {
		// Do not run these callbacks from here, because the CommitWith and the
		// callback might be acquiring the same locks. Instead run the callback
		// from another goroutine.
		go runTxnCallback(&txnCb{user: cb, err: nil})
		return
	}

	commitCb, err := txn.commitAndSend()
	if err != nil {
		go runTxnCallback(&txnCb{user: cb, err: err})
		return
	}

	go runTxnCallback(&txnCb{user: cb, commit: commitCb})
}
```

ここで使用している `txnCb` 構造体と `runTxnCallback` 関数の定義は以下の通りです。
[txn.go#L557-L577](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L557-L577)
```go
type txnCb struct {
	commit func() error
	user   func(error)
	err    error
}

func runTxnCallback(cb *txnCb) {
	switch {
	case cb == nil:
		panic("txn callback is nil")
	case cb.user == nil:
		panic("Must have caught a nil callback for txn.CommitWith")
	case cb.err != nil:
		cb.user(cb.err)
	case cb.commit != nil:
		err := cb.commit()
		cb.user(err)
	default:
		cb.user(nil)
	}
}
```


## `newOracle` 関数の定義と呼び出し元
[txn.go#L61-L76](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L61-L76)
```go
func newOracle(opt Options) *oracle {
	orc := &oracle{
		isManaged: opt.managedTxns,
		commits:   make(map[uint64]uint64),
		// We're not initializing nextTxnTs and readOnlyTs. It would be done after replay in Open.
		//
		// WaterMarks must be 64-bit aligned for atomic package, hence we must use pointers here.
		// See https://golang.org/pkg/sync/atomic/#pkg-note-BUG.
		readMark: &y.WaterMark{Name: "badger.PendingReads"},
		txnMark:  &y.WaterMark{Name: "badger.TxnTimestamp"},
		closer:   y.NewCloser(2),
	}
	orc.readMark.Init(orc.closer, opt.EventLogging)
	orc.txnMark.Init(orc.closer, opt.EventLogging)
	return orc
}
```

`newOracle` の呼び出し元は以下の 2 箇所です。

1. `Open` 関数内。
[db.go#L282-L293](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L282-L293)
```go

	db = &DB{
		imm:           make([]*skl.Skiplist, 0, opt.NumMemtables),
		flushChan:     make(chan flushTask, opt.NumMemtables),
		writeCh:       make(chan *request, kvWriteChCapacity),
		opt:           opt,
		manifest:      manifestFile,
		elog:          elog,
		dirLockGuard:  dirLockGuard,
		valueDirGuard: valueDirLockGuard,
		orc:           newOracle(opt),
		pub:           newPublisher(),
	}
```

2. `StreamWriter` の `Flush` メソッド内。
[stream_writer.go#L231-L238](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/stream_writer.go#L231-L238)
```go
		if sw.db.orc != nil {
			sw.db.orc.Stop()
		}
		sw.db.orc = newOracle(sw.db.opt)
		sw.db.orc.nextTxnTs = sw.maxVersion
		sw.db.orc.txnMark.Done(sw.maxVersion)
		sw.db.orc.readMark.Done(sw.maxVersion)
		sw.db.orc.incrementNextTs()
```

## 通常の read write トランザクションでの `ErrConflict`

まとめると通常の read write トランザクションについては以下のようになります。

* `Open` 関数内で作られる `oracle` は `DB` 内に 1 対 1 で保持されます。
* トランザクションの開始時点の `oracle` の `nextTxnTs - 1` が `txn` の `readTs` に設定されます。
* その後 `Txn` の `Get` メソッドか `Iterator` の `Item` メソッドで参照されたキーのハッシュが `txn` の `reads` フィールドに追加されていきます。
* 一方 `Txn` の `SetEntry` と `Delete` メソッドが呼ばれると対象のキーのハッシュが `txn` の `writes` フィールドに追加されていきます。
* `Txn` の `Commit` か `CommitWith` メソッドが呼ばれると `oracle` の `nextTxnTs` の現在値を取得してインクリメントし、 `txn` の `writes` のキーのハッシュ全てについて `oracle` の `commits` に `nextTxnTs` のインクリメント前の値を設定します。
* `oracle` の `hasConflict` メソッド内では `txn` の `reads` に含まれるキーのハッシュについて `oracle` の `commits` に設定されたタイムスタンプを取得し `txn` の `readTs` より大きいものがあればコンフリクトありと判定します。
* `oracle` の `nextTxnTs` は以下の操作でインクリメントされます。
    * `Txn` の `Commit` か `CommitWith` メソッドが呼ばれてコミットしたとき。
    * `Open` 関数でデータベースが開かれたとき。
    * `StreamWriter` の `Flush` メソッドが呼ばれたとき。

## `StreamWriter` は新規 DB 作成専用

[badger/README.md](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md) に [Stream](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md#stream) という項がありますが、 `StreamWriter` はこれとは別です。

`StreamWriter` は `DB` の `NewStreamWriter` メソッドで作成します。
[stream_writer.go#L54-L66](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/stream_writer.go#L54-L66)

コメントによると直後に `Prepare` メソッドを呼ぶ必要があります。
[stream_writer.go#L68-L79](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/stream_writer.go#L68-L79)

`Prepare` 内では `DB` の `dropAll` メソッド [db.go#L1478-L1517](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L1478-L1517) が呼ばれています。

`dropAll` メソッドは上記の `StreamWriter` の `Prepare` メソッド以外では `DB` の `DropAll` メソッドから呼ばれます。
[db.go#L1458-L1476](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L1458-L1476)
コメントによると名前の通り DB 内のすべてのデータを削除するメソッドのようです。

`StreamWriter` 構造体のコメント [stream_writer.go#L33-L52](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/stream_writer.go#L33-L52) に用途が書いてありました。
既存の DB インスタンスに対して使うものではなく、新しい DB を作成するときのみ使用するものとのことです。

## `WriteBatch`

[badger/README.md](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md) の FAQ の [My writes are really slow. Why?](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md#my-writes-are-really-slow-why) に `WriteBatch` の使い方の説明があります。

説明の最後に `WriteBatch` API では DB の値を読み取ることは出来ないと書いてあります。読み取りと書き込みが必要な場合は `Transaction` API を使う必要があります。

`WriteBatch` の使用例も書かれています。
```go
wb := db.NewWriteBatch()
defer wb.Cancel()

for i := 0; i < N; i++ {
  err := wb.Set(key(i), value(i), 0) // Will create txns as needed.
  handle(err)
}
handle(wb.Flush()) // Wait for all txns to finish.
```

### `DB` の `NewWriteBatch` メソッド
[batch.go#L35-L53](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L35-L53)
```go
// NewWriteBatch creates a new WriteBatch. This provides a way to conveniently do a lot of writes,
// batching them up as tightly as possible in a single transaction and using callbacks to avoid
// waiting for them to commit, thus achieving good performance. This API hides away the logic of
// creating and committing transactions. Due to the nature of SSI guaratees provided by Badger,
// blind writes can never encounter transaction conflicts (ErrConflict).
func (db *DB) NewWriteBatch() *WriteBatch {
	if db.opt.managedTxns {
		panic("cannot use NewWriteBatch in managed mode. Use NewWriteBatchAt instead")
	}
	return db.newWriteBatch()
}

func (db *DB) newWriteBatch() *WriteBatch {
	return &WriteBatch{
		db:       db,
		txn:      db.newTransaction(true, true),
		throttle: y.NewThrottle(16),
	}
}
```

コメントにある `SSI` は [badger/README.md](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md) の Design の [Comparisons](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/README.md#comparisons) に説明がありました。

Transactions の行の Badger の列に Yes, ACID, concurrent with SSI とあり、表の下の注釈に以下のように書かれています。

> SSI: Serializable Snapshot Isolation. For more details, see the blog post [Concurrent ACID Transactions in Badger - Dgraph Blog](https://blog.dgraph.io/post/badger-txn/)

このブログ記事に `ErrConflict` について説明されていました。

コードに戻ると `DB` の `newWriteBatch` メソッド内で `newTransaction` メソッドを呼んで read write トランザクションを作っていることが分かります。

### `WriteBatch` の `SetEntry` メソッド
[batch.go#L91-L110](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L91-L110)
```go
// SetEntry is the equivalent of Txn.SetEntry.
func (wb *WriteBatch) SetEntry(e *Entry) error {
	wb.Lock()
	defer wb.Unlock()

	if err := wb.txn.SetEntry(e); err != ErrTxnTooBig {
		return err
	}
	// Txn has reached it's zenith. Commit now.
	if cerr := wb.commit(); cerr != nil {
		return cerr
	}
	// This time the error must not be ErrTxnTooBig, otherwise, we make the
	// error permanent.
	if err := wb.txn.SetEntry(e); err != nil {
		wb.err = err
		return err
	}
	return nil
}
```

* `wb.txn` の `SetEntry` メソッドを呼びエラーが `nil` か `ErrTxnTooBig` 以外のエラーが出たらそれを返します。
* `ErrTxnTooBig` だった場合は `commit` メソッドを呼び、エラーが起きた場合はそのエラーを返します。
* エラーが起きなかった場合は再度 `wb.txn` の `SetEntry` メソッドを呼びます。コメントによるとここでは `ErrTxnTooBig` は起きないそうです。エラーが起きたら `wb.err` に設定しつつ返します。

### `WriteBatch` の `Set` メソッド
`Entry` のインスタンスを作って `SetEntry` メソッドを呼んでいるだけです。
[batch.go#L112-L116](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L112-L116)
```go
// Set is equivalent of Txn.Set().
func (wb *WriteBatch) Set(k, v []byte) error {
	e := &Entry{Key: k, Value: v}
	return wb.SetEntry(e)
}
```

### `WriteBatch` の `Delete` メソッド
`wb.txn` の `SetEntry` ではなく `Delete` を呼ぶ点を除いて `WriteBatch` の `SetEntry` と全く同じ構造です。
[batch.go#L118-L134](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L118-L134)
```go
// Delete is equivalent of Txn.Delete.
func (wb *WriteBatch) Delete(k []byte) error {
	wb.Lock()
	defer wb.Unlock()

	if err := wb.txn.Delete(k); err != ErrTxnTooBig {
		return err
	}
	if err := wb.commit(); err != nil {
		return err
	}
	if err := wb.txn.Delete(k); err != nil {
		wb.err = err
		return err
	}
	return nil
}
```

### `WriteBatch` の `commit` メソッド
[batch.go#L136-L149](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L136-L149)
```go
// Caller to commit must hold a write lock.
func (wb *WriteBatch) commit() error {
	if wb.err != nil {
		return wb.err
	}
	if err := wb.throttle.Do(); err != nil {
		return err
	}
	wb.txn.CommitWith(wb.callback)
	wb.txn = wb.db.newTransaction(true, true)
	wb.txn.readTs = 0 // We're not reading anything.
	wb.txn.commitTs = wb.commitTs
	return wb.err
}
```
この中で `wb.callback` メソッドを引数にして `wb.txn` の `CommitWith` メソッドを呼んでいます。

### `WriteBatch` の `callback` メソッド
[batch.go#L76-L89](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L76-L89)
```go
func (wb *WriteBatch) callback(err error) {
	// sync.WaitGroup is thread-safe, so it doesn't need to be run inside wb.Lock.
	defer wb.throttle.Done(err)
	if err == nil {
		return
	}

	wb.Lock()
	defer wb.Unlock()
	if wb.err != nil {
		return
	}
	wb.err = err
}
```

### `y.Throttle`
`DB` の `newWriteBatch` メソッド内で `y.NewThrottle` 関数を呼んで作成している `y.Throttle` について見ていきます。

`y.Throttle` 構造体。
[y/y.go#L236-L245](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/y/y.go#L236-L245)
```go
// Throttle allows a limited number of workers to run at a time. It also
// provides a mechanism to check for errors encountered by workers and wait for
// them to finish.
type Throttle struct {
	once      sync.Once
	wg        sync.WaitGroup
	ch        chan struct{}
	errCh     chan error
	finishErr error
}
```

`NewThrottle` 関数。
[y/y.go#L247-L253](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/y/y.go#L247-L253)
```go
// NewThrottle creates a new throttle with a max number of workers.
func NewThrottle(max int) *Throttle {
	return &Throttle{
		ch:    make(chan struct{}, max),
		errCh: make(chan error, max),
	}
}
```

`Do` メソッド。
[y/y.go#L255-L270](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/y/y.go#L255-L270)
```go
// Do should be called by workers before they start working. It blocks if there
// are already maximum number of workers working. If it detects an error from
// previously Done workers, it would return it.
func (t *Throttle) Do() error {
	for {
		select {
		case t.ch <- struct{}{}:
			t.wg.Add(1)
			return nil
		case err := <-t.errCh:
			if err != nil {
				return err
			}
		}
	}
}
```
`t.ch` を使って同時に実行するワーカーの最大数が `NewThrottle` 関数の引数の `max` に限定されるようになっています。既に `max` 個のワーカーが動いている場合は、どれかが正常終了するかエラーを返すまで待つことになります。

`Done` メソッド。
[y/y.go#L272-L284](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/y/y.go#L272-L284)
```go
// Done should be called by workers when they finish working. They can also
// pass the error status of work done.
func (t *Throttle) Done(err error) {
	if err != nil {
		t.errCh <- err
	}
	select {
	case <-t.ch:
	default:
		panic("Throttle Do Done mismatch")
	}
	t.wg.Done()
}
```

`Finish` メソッド。
[y/y.go#L286-L303](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/y/y.go#L286-L303)
```go
// Finish waits until all workers have finished working. It would return any error passed by Done.
// If Finish is called multiple time, it will wait for workers to finish only once(first time).
// From next calls, it will return same error as found on first call.
func (t *Throttle) Finish() error {
	t.once.Do(func() {
		t.wg.Wait()
		close(t.ch)
		close(t.errCh)
		for err := range t.errCh {
			if err != nil {
				t.finishErr = err
				return
			}
		}
	})

	return t.finishErr
}
```

### `WriteBatch` の `Flush` メソッド
[batch.go#L151-L164](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/batch.go#L151-L164)
```go
// Flush must be called at the end to ensure that any pending writes get committed to Badger. Flush
// returns any error stored by WriteBatch.
func (wb *WriteBatch) Flush() error {
	wb.Lock()
	_ = wb.commit()
	wb.txn.Discard()
	wb.Unlock()

	if err := wb.throttle.Finish(); err != nil {
		return err
	}

	return wb.err
}
```

### `WriteBatch` のまとめ
`WriteBatch` の `commit` メソッドで `callback` メソッドを引数に `Txn` の `CommitWith` メソッドを呼び、エラーが出たら `WriteBatch` の `err` フィールドにセットしています。
このエラーは `WriteBatch` の `SetEntry`, `Delete`, `Flush` メソッドの戻り値として返ってきます。

これまでの上記のコードを見返してみて `NewWriteBatch` 関数のコメントの最後の文

> Due to the nature of SSI guaratees provided by Badger, blind writes can never encounter transaction conflicts (ErrConflict).

は読み取りなしで書き込みだけのトランザクションでは `oracle` の `hasConflict` メソッドが `false` を返すので `ErrConflict` は絶対に起きないという意味だということに気づきました。

また `WriteBatch` の `SetEntry` か `Delete` を呼んだときに `ErrTxnTooBig` が起きた時は自動的に一旦コミットして、次のトランザクションを開始し元の `SetEntry` か `Delete` の処理を新しいトランザクションで行うようになっています。
