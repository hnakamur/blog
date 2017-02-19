Title: LSM-TreeとRocksDB、TiDB、CockroachDBが気になる
Date: 2016-06-20 22:23
Category: blog
Tags: lsmtree,rocksdb,tidb
Slug: blog/2016/06/20/lsm-tree-and-rocksdb

## はじめに
キーバリューストアについて調べていたらLSM-Treeというデータ構造とRocksDBが気になったということで調査メモです。ただし、それぞれの技術詳細を調査したり自分で検証してみたというメモではないです。

そうではなく、いろんな記事で言及されていたり、ソフトウェアで採用されているのが気になったというだけの浅いメモです。が、脳内バッファからあふれる量になったので自分用に軽くまとめ。

## LSM Tree

Log-structured merge-treeを略してLSM Treeと呼ぶそうです。概要は[Log-structured merge-tree - Wikipedia](https://en.wikipedia.org/wiki/Log-structured_merge-tree)を参照してください。

CockroachDBのデザインドキュメントの[Read vs. Write Optimization Spectrum](https://github.com/cockroachdb/cockroach/blob/master/docs/design.md#read-vs-write-optimization-spectrum)によると、B+ Treeというデータ構造は書き込みより読み取りが多いケースに最適化されているが、LSM Treeのほうは書き込みが多いケースに最適化されているそうです。

一方、LSM Treeのほうはディスク使用量は肥大化しがちで定期的にコンパクションする必要があって、コンパクションには負荷がかかるので、この方式を各実装で工夫しているという話を何処かで読んだんですがリンクを紛失してしまいました。

## InfluxDBの事例

[InfluxData | Documentation | Storage Engine](https://docs.influxdata.com/influxdb/v0.13/concepts/storage_engine/)によるとInfluxDBのストレージエンジンは以下の変遷を辿ったそうです。

1. LSM Treeの実装の1つである[LevelDB](https://github.com/google/leveldb)を採用
2. B+Treeの実装の1つである[BoltDB](https://github.com/boltdb/bolt)を採用
3. LSM Treeに似た独自のデータ構造でストレージエンジンを自作


## TiDBの事例

[pingcap/tidb: TiDB is a distributed NewSQL database compatible with MySQL protocol](https://github.com/pingcap/tidb)

* TiDB自体はGoで書かれている。
* MySQLのプロトコルを解釈できる。
* MySQLで使用できるSQLのサブセットを実装している。
* TiDBはRustで書かれRaftアルゴリズムを使った分散トランザクション対応のキーバリューデータベース [TiKV](https://github.com/pingcap/tikv)を使っている。
    - [What is TiDB?](https://github.com/pingcap/tidb#what-is-tidb)にはGolevelDB, LevelDB, RocksDB, LMDB, BoltDBに対応しているとあるのですが、TiDBの開発者のLi Shenさんによるとgoleveldbはローカルストレージとしてのみ利用可能で、分散環境ではTiKVを使っているそうです。
    - TiKVのストレージエンジンはLSM Treeの実装である[RocksDB](http://rocksdb.org/)を採用。Li ShenさんによるとTiDBの開発チームはRocsDBのチームとも連絡をとっているそうです。
    - TiKV用の[Goのクライアント](https://github.com/pingcap/tidb/blob/master/store/tikv/txn.go)もある。
* 現在バリバリ開発中。[ロードマップ](https://github.com/pingcap/tidb/blob/master/docs/ROADMAP.md)
* TiDBの紹介記事: [MySQL は分散DBの夢を見るか、Google F1 論文を実装した TiDB を使ってみた | 株式会社インフィニットループ技術ブログ](https://www.infiniteloop.co.jp/blog/2016/05/install-tidb/)
* TiDBの起源についてのブログ記事。[Thoughts behind TiDB - Part I](http://0xffff.me/thoughts-behind-tidb-part-1/)。私は中国語読めないのでGoogle翻訳で英語にして読みました。

## CockroachDBの事例

[cockroachdb/cockroach: A Scalable, Survivable, Strongly-Consistent SQL Database](https://github.com/cockroachdb/cockroach)

名前の由来: [Why the name Cockroach?](https://github.com/cockroachdb/cockroach/wiki#why-the-name-cockroach)

* CoackroachDBはGoで書かれている。
* PostgreSQLのプロトコルを解釈できる。
* PostgreSQLで使用できるSQLのサブセットを実装している。
* ストレージエンジンは[RocksDB](http://rocksdb.org/)を採用。
* 現在バリバリ開発中。
    - バージョン1.0に向けてベータ版を頻繁に出している。 [Releases](https://github.com/cockroachdb/cockroach/releases)
    - [ロードマップ](https://github.com/cockroachdb/cockroach/wiki)
* デザインドキュメント [Design overview](https://github.com/cockroachdb/cockroach#design), [full design doc](https://github.com/cockroachdb/cockroach/blob/master/docs/design.md)と[Frequently Asked Questions](https://www.cockroachlabs.com/docs/frequently-asked-questions.html)がとても充実しています
    - [Lock-Free Distributed Transactions](https://github.com/cockroachdb/cockroach/blob/master/docs/design.md#lock-free-distributed-transactions)にCockroachDBの分散トランザクションの設計について解説があります。


## LSM Treeの実装はいろいろあるがRocksDBが良いらしい

InfluxDBの開発元influxdataのブログのベンチマーク記事 [Benchmarking LevelDB vs. RocksDB vs. HyperLevelDB vs. LMDB Performance for InfluxDB | InfluxData](https://influxdata.com/blog/benchmarking-leveldb-vs-rocksdb-vs-hyperleveldb-vs-lmdb-performance-for-influxdb/)でも値の書き込みとクエリ実行の性能が良いのはRocksDBとなっています。

[Small Datum: Comparing LevelDB and RocksDB, take 2](http://smalldatum.blogspot.jp/2015/04/comparing-leveldb-and-rocksdb-take-2.html)にRocksDBとLevelDBのベンチマークがありますが、RocksDBのほうが良い感じです。

上記の通りTiDBでもCockroachDBでもRocksDBを採用していますし、現在のところ有望そうです。

[Rocksdb: The History of RocksDB](http://rocksdb.blogspot.jp/2013/11/the-history-of-rocksdb.html)にRocksDBを開始した頃の話が書かれていました。

[RocksDB FAQ](https://github.com/facebook/rocksdb/wiki/RocksDB-FAQ)の "Q: What's the maximum key and value sizes supported?" によると、RocksDBは大きなサイズのキー用にはデザインされておらず、推奨されるキーと値の最大サイズはそれぞれ8MBと3GBとのことです。

## おわりに
書き込みが多いケースに向いているキーバリューストアであるRocksDBと、RocksDBをつかて分散トランザクションを実現しているデータベースであるTiDBとCockroachDBの今後に注目したいと思います。
