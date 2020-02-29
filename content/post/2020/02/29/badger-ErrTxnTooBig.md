---
title: "BadgerのErrTxnTooBigについて"
date: 2020-02-29T15:44:41+09:00
---

## はじめに

[badgerのREADME](https://github.com/dgraph-io/badger)
の
[Read-write transactions](https://github.com/dgraph-io/badger#read-write-transactions)
に Badger の ErrTxnTooBig について以下のような説明がありました。

> An ErrTxnTooBig will be reported in case the number of pending writes/deletes in the transaction exceeds a certain limit. In that case, it is best to commit the transaction and start a new transaction immediately. Here is an example (we are not checking for errors in some places for simplicity):

```go
updates := make(map[string]string)
txn := db.NewTransaction(true)
for k,v := range updates {
  if err := txn.Set([]byte(k),[]byte(v)); err == badger.ErrTxnTooBig {
    _ = txn.Commit()
    txn = db.NewTransaction(true)
    _ = txn.Set([]byte(k),[]byte(v))
  }
}
_ = txn.Commit()
```

実際のところどれぐらいの大きさで `ErrTxnTooBig` が出るのか気になったのでコードを読んでみました。

## `ErrTxnTooBig` を返している個所

2 箇所ありました。

その 1: `DB` の `sendToWriteCh` メソッド内。
[db.go#L735-L742](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L735-L742)
```go
  var count, size int64
  for _, e := range entries {
    size += int64(e.estimateSize(db.opt.ValueThreshold))
    count++
  }
  if count >= db.opt.maxBatchCount || size >= db.opt.maxBatchSize {
    return nil, ErrTxnTooBig
  }
```

その 2: `Txn` の `checkSize` メソッド内。
[txn.go#L295-L304](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/txn.go#L295-L304)
```go
func (txn *Txn) checkSize(e *Entry) error {
  count := txn.count + 1
  // Extra bytes for the version in key.
  size := txn.size + int64(e.estimateSize(txn.db.opt.ValueThreshold)) + 10
  if count >= txn.db.opt.maxBatchCount || size >= txn.db.opt.maxBatchSize {
    return ErrTxnTooBig
  }
  txn.count, txn.size = count, size
  return nil
}
```

## `db.opt` の `maxBatchCount` と `maxBatchSize`

`Options` 構造体（抜粋）
[options.go#L95-L98](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/options.go#L95-L98)
```go
  // 4. Flags for testing purposes
  // ------------------------------
  maxBatchCount int64 // max entries in batch
  maxBatchSize  int64 // max batch size in bytes
```

設定箇所は `Open` 関数内にありました。
[db.go#L195-L196](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/db.go#L195-L196)
```go
  opt.maxBatchSize = (15 * opt.MaxTableSize) / 100
  opt.maxBatchCount = opt.maxBatchSize / int64(skl.MaxNodeSize)
```

`skl.MaxNodeSize` は定数で Visual Studio Code によると 96 です。
[skl/skl.go#L49-L50](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/skl/skl.go#L49-L50)
```go
// MaxNodeSize is the memory footprint of a node of maximum height.
const MaxNodeSize = int(unsafe.Sizeof(node{}))
```

`DefaultOptions` 関数内を見ると `MaxTableSize` のデフォルト値は 64MiB です。
[options.go#L114](https://github.com/dgraph-io/badger/blob/617ed7c7db9d618b6511adfff5d22dcde2233049/options.go#L114)
```go
    MaxTableSize:            64 << 20,
```

これから計算すると `opt.maxBatchSize` は 9.6MiB です。

```
>>> 15 * 64 / 100.0
9.6
```

`opt.maxBatchCount` は `9.6 / 96` で 0.1Mi = 102.4Ki = 104,857 です。
