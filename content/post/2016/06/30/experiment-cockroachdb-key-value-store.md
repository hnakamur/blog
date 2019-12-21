+++
Categories = []
Description = ""
Tags = ["golang","cockroachdb"]
date = "2016-06-30T06:40:12+09:00"
title = "分散SQLデータベースCockroachDBのキーバリューストレージのデバッグコマンドを試してみた"

+++
## はじめに
[LSM-TreeとRocksDB、TiDB、CockroachDBが気になる](h/blog/2016/06/20/lsm-tree-and-rocksdb/) で紹介した [CockroachDB](https://github.com/cockroachdb/cockroach#client-drivers) は [What is CockroachDB?](https://github.com/cockroachdb/cockroach#what-is-cockroachdb) によるとスケールアウトできる分散SQLデータベースです。 [PostgreSQLのワイヤープロトコルをサポート](https://github.com/cockroachdb/cockroach#client-drivers) していて、 [Quickstart](https://github.com/cockroachdb/cockroach#quickstart) の例のようにPostgreSQLで扱えるSQLのサブセットが使えます。

[Overview](https://github.com/cockroachdb/cockroach#overview) によるとストレージには [RocksDB](http://rocksdb.org/) を使用し、複数台のサーバ間の合意アルゴリズムにはRaftを使用しています。

分散SQLデータベースという本来の機能も魅力的なのですが、書き込みが多いケースに最適化したLSM Treeというデータ構造の実装であるRocksDBをRaftを使って分散トランザクションを実現しているという部分も個人的には興味があります。

ということで、そのへんのソースを見ていこうと思います。といっても、まだ全体を把握しているわけではないので、だらだら書いていきます。
CockroachDBにデバッグ用のコマンドが用意されていたので、それで実験しつつ読み進めたいと思います。

## RocksDBラッパーレイヤとengineパッケージ

RocksDBはC++で書かれているので、Goから呼び出すためcgoでラッピングしているレイヤがあります。 [cockroach/storage/engine/rocksdb](https://github.com/cockroachdb/cockroach/tree/master/storage/engine/rocksdb) にC++で書かれたファイルがいくつかあります。 [cockroach/storage/engine](https://github.com/cockroachdb/cockroach/tree/master/storage/engine) パッケージのドキュメント [engine - GoDoc](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine) にこのパッケージで低レベルのストレージを提供しているという説明があります。

[Engine](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#Engine) はRocksDBなどのストレージバックエンドとやり取りするためのインターフェースです。 Engineは [ReadWriter](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#ReadWriter) インタフェースをエンベッドしていて、それがさらに [Reader](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#Reader) と [Writer](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#Writer) インタフェースをエンベッドしています。

Reader や Writer インタフェースのメソッドを見るとキーバリューストアのキーは [MVCCKey](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#MVCCKey) という型になっています。

```
type MVCCKey struct {
    Key       roachpb.Key
    Timestamp hlc.Timestamp
}
```

[roachpb.Key](https://godoc.org/github.com/cockroachdb/cockroach/roachpb#Key) は `[]byte` と定義されており、 [hlc.Timestamp](https://godoc.org/github.com/cockroachdb/cockroach/util/hlc#Timestamp) は以下のように定義されています。

```
type Timestamp struct {
    // Holds a wall time, typically a unix epoch time
    // expressed in nanoseconds.
    WallTime int64 `protobuf:"varint,1,opt,name=wall_time,json=wallTime" json:"wall_time"`
    // The logical component captures causality for events whose wall
    // times are equal. It is effectively bounded by (maximum clock
    // skew)/(minimal ns between events) and nearly impossible to
    // overflow.
    Logical int32 `protobuf:"varint,2,opt,name=logical" json:"logical"`
}
```

[engine - GoDoc](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine) にEngineインタフェースの上にMVCC (Multi-Version Concurrency Control) システムが提供されていて、それがCockroachDBが分散トランザクションをサポートするための基礎になっていると書かれています。

その下の [Notes on MVCC architecture](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#hdr-Notes_on_MVCC_architecture) にMVCCアーキテクチャについて詳細な説明があります。じっくり読んだほうが良いと思いますが、一旦飛ばして先に進みます。

[RocksDB](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#RocksDB) という構造体定義があり、これが Engine インタフェースを実装しています。  [NewRocksDB](https://godoc.org/github.com/cockroachdb/cockroach/storage/engine#NewRocksDB) 関数で RocksDB を作成できます。

## NewRocksDB関数の呼び出し箇所

NewRocksDB関数は、テストコード以外では、以下の2箇所で呼ばれていました。

* [server](https://godoc.org/github.com/cockroachdb/cockroach/server) パッケージの [func (*Context) InitStores](https://godoc.org/github.com/cockroachdb/cockroach/server#Context.InitStores)。
    - [cockroach/context.go at 549d9b575e06921fa96b6ff4881ea348d8b6d00c](https://github.com/cockroachdb/cockroach/blob/549d9b575e06921fa96b6ff4881ea348d8b6d00c/server/context.go#L260-L261)
* [cockroach/debug.go](https://github.com/cockroachdb/cockroach/blob/master/cli/debug.go) の `cli.openStore(cmd *cobra.Command, dir string, stopper *stop.Stopper) (engine.Engine, error)`
    - [cockroach/debug.go at 549d9b575e06921fa96b6ff4881ea348d8b6d00c](https://github.com/cockroachdb/cockroach/blob/549d9b575e06921fa96b6ff4881ea348d8b6d00c/cli/debug.go#L65-L71)

後者を呼び出している箇所を見ていくとデバッグ用のサブコマンドがあることがわかりました。

## デバッグ用サブコマンドを試してみた

前提条件としてLXDの3つのコンテナroach1, roach2, roach3で以下のようにCockroachDBを起動している状態とします。

roach1

```
/usr/local/sbin/cockroach start --host 192.168.0.13 --insecure
```

roach2

```
/usr/local/sbin/cockroach start --join 192.168.0.13:26257 --insecure --host 192.168.0.14
```

roach3

```
/usr/local/sbin/cockroach start --join 192.168.0.13:26257 --insecure --host 192.168.0.15
```

特にコンテナでなくても1台のサーバで [Quickstart](https://github.com/cockroachdb/cockroach#quickstart)のlocal clusterでも構いません。その場合は下記のコマンドの `--host` の部分を適宜読み替えてください。

### debug kv コマンドを試してみた

debug kvコマンドで、キー・バリュー・ストアに値を設定したり取得したり出来ます。

コンテナroach1で値をセットして取得してみました。
```
root@roach1:~# cockroach debug kv scan --host 192.168.0.13
0 result(s)
root@roach1:~# cockroach debug kv put --host 192.168.0.13 foo bar
root@roach1:~# cockroach debug kv get --host 192.168.0.13 foo
"bar"
root@roach1:~# cockroach debug kv scan --host 192.168.0.13
"foo"   "bar"
1 result(s)
```

上記で設定した値がコンテナroach2でも取得できました。
```
root@roach2:~# cockroach debug kv scan --host 192.168.0.14
"foo"   "bar"
1 result(s)
```

コンテナroach2からroach1上の値を変更も出来ます。
```
root@roach2:~# cockroach debug kv put --host 192.168.0.13 foo 'Hello, key value store in CockroachDB'
```

コンテナroach1上の値一覧を取得して更新されていることを確認しました。
```
root@roach1:~# cockroach debug kv scan --host 192.168.0.13
"foo"   "Hello, key value store in CockroachDB"
1 result(s)
```

### debug keys コマンドを試してみた

debug keysコマンドで、キー・バリュー・ストアの内部構造をダンプして見ることが出来ます。このコマンドはサーバを停止した状態でデータのディレクトリを指定して実行するようになっています。

サーバが起動したまま実行すると以下のようにロックが取得できないというエラーになります。

```
root@roach2:~# cockroach debug keys ./cockroach-data
Error: storage/engine/rocksdb.go:158: could not open rocksdb instance: IO error: lock ./cockroach-data/LOCK: Resource temporarily unavailable
Usage:
  cockroach debug keys [directory] [flags]

Flags:
      --from string
        Start key in pretty-printed format. See also --raw.

      --raw
        Interpret keys as raw bytes.

      --to string
        Exclusive end key in pretty-printed format. See also --raw.

      --values
        Print values along with their associated key.

Global Flags:
      --alsologtostderr value[=INFO]   logs at or above this threshold go to stderr (default NONE)
      --log-backtrace-at value         when logging hits line file:N, emit a stack trace (default :0)
      --log-dir value                  if non-empty, write log files in this directory
      --logtostderr                    log to standard error instead of files
      --no-color value                 disable standard error log colorization
      --verbosity value                log level for V logs
      --vmodule value                  comma-separated list of pattern=N settings for file-filtered logging

Failed running "debug"
```

そこでコンテナroach2のサーバを停止してみます。

```
root@roach2:~# cockroach quit --host 192.168.0.14
```

サーバを停止したらキーの一覧を表示してみます。以下の例では `foo` の前後5行を表示しています。
fooという文字列の後にタイムスタンプがついているのがわかります。

```
root@roach2:~# cockroach debug keys ./cockroach-data | grep -A 5 -B 5 foo
"/System/\"update-cluster\"/1466351519.447511853,0"
"/System/\"update-cluster\"/1466265107.436191749,0"
"/System/\"update-cluster\"/1466265097.406397710,0"
"/System/\"update-cluster\"/1466178687.396782782,0"
"/System/\"update-cluster\"/1466178677.619687555,85"
"\"foo\"/1467234744.564568969,0"
"\"foo\"/1467221373.376922221,0"
"/Table/2/1/0/\"bank\"/3/1/1466178749.722011447,0"
"/Table/2/1/0/\"system\"/3/1/1466178677.367397368,0"
"/Table/2/1/1/\"descriptor\"/3/1/1466178677.367397368,0"
"/Table/2/1/1/\"eventlog\"/3/1/1466178677.367397368,0"
"/Table/2/1/1/\"lease\"/3/1/1466178677.367397368,0"
```

`--values` オプションも追加すると、キーだけではなく値も表示されます。


```
cockroach debug keys --values cockroach-data/ | less
```

を実行して、 `foo` のキーに対応する部分を見てみると以下のようになっていました。横に長過ぎるので折り返して表示しています。

  /Local/RangeID/21/u/RaftLog/logIndex:104861: Type:EntryNormal Term:51415 Index:104861  by {2 2 2}
  Put ["foo",/Min)
  range_id:21 origin_replica:<node_id:2 store_id:2 replica_id:2 > cmd:<header:<timestamp:<wall_time:1467234744564568969 logical:0 > replica:<node_id:2 store_id:2 replica_id:2 > range_id:21 user_priority:NORMAL read_consistency:CONSISTENT trace:<trace_id:4947902158296355776 span_id:7041358067641207168 > max_scan_results:0 distinct_spans:false > requests:<put:<header:<key:"foo" > value:<raw_bytes:"s|S\306\003Hello, key value store in CockroachDB" timestamp:<wall_time:0 logical:0 > > inline:false blind:false > > > max_lease_index:990


## おわりに

CockroachDBのキーバリューストレージのデバッグコマンドを試してみました。対応するソースコードも読んでみたいところですが、
[ArangoDB 3.0 – A Solid Ground to Scale – ArangoDB](https://www.arangodb.com/2016/06/arangodb-3-0-a-solid-ground-to-scale/)
というニュースを知ったので、今後はArangoDBのほうを先に調べたいと思います。
