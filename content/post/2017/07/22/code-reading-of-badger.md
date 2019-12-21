+++
title="badgerのコードリーディング"
date = "2017-07-22T21:57:00+09:00"
lastmod = "2017-07-23T09:54:00+09:00"
tags = ["go", "badger"]
categories = ["blog"]
+++


## はじめに

約一年前に [LSM-TreeとRocksDB、TiDB、CockroachDBが気になる](/blog/2016/06/20/lsm-tree-and-rocksdb/) を書いた後、結局RocksDB触ってなかったのですが、もっと良さそうなしかも pure Go のライブラリ
[dgraph-io/badger: Fastest key-value store in Go.](https://github.com/dgraph-io/badger)
がしばらく前に出てきてとても期待しています。上のページのREADMEやそこからリンクされているブログ記事を読んだ感じ素晴らしいです。

ちょっとだけですが試してコードを読んだのでメモしておきます。

## 1つのデータディレクトリは複数のプロセスから同時アクセスは出来ない

`NewKV` を読んだ時点でロックファイルを作るようになっているので、複数のプロセスから同じデータディレクトリに対して同時にアクセスは出来ません。やってみたらエラーになりました。

なので、1つのプロセスで開いておいて、そのプロセスにアクセスを依頼する構成にする必要があります。

`NewKV` で返ってくる `KV` がスレッドセーフ (正確にはgoroutineセーフ)、つまり複数のgoroutineから扱えるかは私はまだわかっていなくて、イシューで質問してみました。

回答を頂いて複数のgoroutineから扱えるとのことでした。その後気づいたのですが、パフォーマンスを上げるには複数のgoroutineから `BatchSet` でまとめて設定するのが良いと `FAQ](https://github.com/dgraph-io/badger#frequently-asked-questions) にも書いてありました。


## SetやCompareAndSetなども内部ではBatchSetを呼んでいる

`Set` も `CompareAndSet` も以下のように `Entry` を1個作って `BatchSet`  を呼び出しています。

[kv.go#L770-L778](https://github.com/dgraph-io/badger/blob/5ae0851516a27bd02958c266f380a7fdb9096093/kv.go#L770-L778)

```go
// Set sets the provided value for a given key. If key is not present, it is created.
// If it is present, the existing value is overwritten with the one provided.
func (s *KV) Set(key, val []byte) error {
	e := &Entry{
		Key:   key,
		Value: val,
	}
	return s.BatchSet([]*Entry{e})
}
```

[kv.go#L800-L813](https://github.com/dgraph-io/badger/blob/5ae0851516a27bd02958c266f380a7fdb9096093/kv.go#L800-L813)

```go
// CompareAndSet sets the given value, ensuring that the no other Set operation has happened,
// since last read. If the key has a different casCounter, this would not update the key
// and return an error.
func (s *KV) CompareAndSet(key []byte, val []byte, casCounter uint16) error {
    e := &Entry{
        Key:             key,
        Value:           val,
        CASCounterCheck: casCounter,
    }
    if err := s.BatchSet([]*Entry{e}); err != nil {
        return err
    }
    return e.Error
}
```

## CompareAndSetでcasCounterを0にするとSetとほぼ同じ

上記のコードを見ると `casCounter` を `0` にして `CompareAndSet` を呼び出すと
`Set` と同じ内容の `Entry` を作ることになるので同じ動きになることがわかります。

`Set` はキーが無い場合は作成し、有る場合は上書き更新しますので、 `CompareAndSet` でも `casCounter` を `0` にした場合は上書きされ得るということです。

また、 `Set` と違って `CompareAndSet` のほうは `BatchSet` が返す `err` が `nil` の場合にエントリ `e` の `Error` フィールドの値を返していますが、この違いがどういうことなのかは私はまだわかっていません。これもイシューで聞いてみました。

その後回答を頂き、自分でもコードを改変してテストを実行するとエラーが出るのを確認して違いがわかりました。
https://github.com/dgraph-io/badger/issues/113#issuecomment-317217631

`CasMismatch` のエラーは `Entry` にセットされますが、 `BatchSet` からは返されないので追加でチェックする必要があるというわけでした。

## casCounterが0になることはない

`casCounter` の値を発行しているコードを探すと以下のように、 `math/rand.Uint32()` を使って65535で割った余りに1を加えた値にしていました。

[util.go#L139-L157](https://github.com/dgraph-io/badger/blob/5ae0851516a27bd02958c266f380a7fdb9096093/util.go#L19-L29)

```go
import (
    "bytes"
    "io/ioutil"
    "math/rand"
    "sync/atomic"
    "time"

    "github.com/dgraph-io/badger/table"
    "github.com/dgraph-io/badger/y"
    "github.com/pkg/errors"
)
```

[util.go#L139-L157 at 5ae0851516a27bd02958c266f380a7fdb9096093 · dgraph-io/badger](https://github.com/dgraph-io/badger/blob/5ae0851516a27bd02958c266f380a7fdb9096093/util.go#L139-L157)

```go
// mod65535 mods by 65535 fast.
func mod65535(a uint32) uint32 {
    a = (a >> 16) + (a & 0xFFFF) /* sum base 2**16 digits */
    if a < 65535 {
        return a
    }
    if a < (2 * 65535) {
        return a - 65535
    }
    return a - (2 * 65535)
}

func newCASCounter() uint16 {
    return uint16(1 + mod65535(rand.Uint32()))
}

func init() {
    rand.Seed(time.Now().UnixNano())
}
```

## casCounterが偶然衝突する確率は0.0015%

`casCounter` の型は `uint16` で上記の通り0は使わないので65535通り。

```text
>>> 1.0 / 65535 * 100
0.0015259021896696422
```

0.0015% が十分低いのかは私はよくわかりません。

## Touchが設定する値は空のbyteスライス

[Touch - GoDoc](https://godoc.org/github.com/dgraph-io/badger#KV.Touch) にはキーが存在する場合はそのまま帰って来て、キーが存在しない場合は設定すると書いてあります。が、どんな値が設定されるのか気になったので、テストを書いて確認してみたところ、空のbyteスライスでした。

ドキュメントに明記してほしいと思ったので、テストの追加とドキュメント修正のプルリクエストを投げてみました。

[Document the value created by Touch is an empty byte slice by hnakamur · Pull Request #115 · dgraph-io/badger](https://github.com/dgraph-io/badger/pull/115/files)

その後このプルリクエストはマージされました。
