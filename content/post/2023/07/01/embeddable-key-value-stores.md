---
title: "Embeddableなkey value storeについてのメモ"
date: 2023-07-01T14:28:11+09:00
---

## はじめに

書き込みも読み取りも低遅延なキーバリューストアが欲しいということで調べてみたメモです。ただし、このメモに書いたキーバリューストアがそうであるかは不明です。

## sled

* [spacejam/sled: the champagne of beta embedded databases](https://github.com/spacejam/sled)
* READMEのperfomanceの項に "LSM tree-like write performance with traditional B+ tree-like read performance" と書かれていて魅力的。
* [Remove old io_uring support before rewrite by spacejam · Pull Request #1424 · spacejam/sled](https://github.com/spacejam/sled/pull/1424)でrioへの依存がなくなっていた。
   * rioは[GPL-3.0でスポンサーにはMIT/Apache-2.0というライセンス](https://github.com/spacejam/rio/blob/319f7fb04014aa88540c3539bd97d5a0006a1eb9/Cargo.toml#L6)

### marble

* [komora-io/marble: garbage-collecting on-disk object store, supporting higher level KV stores and databases.](https://github.com/komora-io/marble)
* READMEに "Marble is sled's future storage engine." とあった。
* https://github.com/komora-io のPeopleはsledの作者の[spacejam](https://github.com/spacejam)さん1人。[Twitterアカウント](https://twitter.com/komora_io)を見ると所在地はドイツのベルリンらしい。

## redb

* [cberner/redb: An embedded key-value database in pure Rust](https://github.com/cberner/redb)
* [RFC: redb (embedded key-value store) nearing version 1.0 : r/rust](https://www.reddit.com/r/rust/comments/13dtd2y/rfc_redb_embedded_keyvalue_store_nearing_version/)で知った。
    * [作者のコメント](https://www.reddit.com/r/rust/comments/13dtd2y/comment/jjm4xfs/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button)によるとしばらく前にmmapを外したとのこと。
* この記事はもうすぐ1.0というタイトルだが、 https://github.com/cberner/redb/releases を見るとここ数日で 1.0.1, 1.0.2, 1.0.3 とpanicするバグの修正リリースが出ている。

## LevelDB

* [google/leveldb: LevelDB is a fast key-value storage library written at Google that provides an ordered mapping from string keys to string values.](https://github.com/google/leveldb)
* READMEのLimitationsに "Only a single process (possibly multi-threaded) can access a particular database at a time." とあった。

## agatedb

* [tikv/agatedb: A persistent key-value storage in rust.](https://github.com/tikv/agatedb)
* READMEによるとTiKVの experimental engine として開発中とのこと。

## LMDB

* [LMDB: Lightning Memory-Mapped Database Manager (LMDB)](http://www.lmdb.tech/doc/)
* [LMDB/lmdb: Read-only mirror of official repo on openldap.org. Issues and pull requests here are ignored. Use OpenLDAP ITS for issues.](https://github.com/LMDB/lmdb)

* Mozillaで2018年に採用検討したときのドキュメント
    * [Design Review: Key-Value Storage](https://mozilla.github.io/firefox-browser-architecture/text/0015-rkv.html)
        * Summaryの冒頭に "There is no one-size-fits-all solution for storage." とあった。
        * "You can get a quite good performance out of the box, without any fuss or configuration like RocksDB." という意見があった。
    * [LMDB vs. LevelDB](https://mozilla.github.io/firefox-browser-architecture/text/0017-lmdb-vs-leveldb.html)
        * Referencesからリンクされていた2013年の記事 [LMDB: The Leveldb Killer? - by Paul Banks](https://banksco.de/p/lmdb-the-leveldb-killer.html)

## redbに付属のベンチマークを試してみた

* 試したバージョン [1.0.3](https://github.com/cberner/redb/tree/v1.0.3)
* `cargo bench` で実行したベンチマークの結果のうち、[benches/lmdb_benchmark.rs](https://github.com/cberner/redb/blob/v1.0.3/benches/lmdb_benchmark.rs)の表の部分を抜粋。

```
+---------------------------+--------+--------+---------+--------+-----------+
|                           | redb   | lmdb   | rocksdb | sled   | sanakirja |
+============================================================================+
| bulk load                 | 4080ms | 1417ms | 9710ms  | 7828ms | 29011ms   |              
|---------------------------+--------+--------+---------+--------+-----------|               
| individual writes         | 58ms   | 116ms  | 44ms    | 45ms   | 95ms      |               
|---------------------------+--------+--------+---------+--------+-----------|               
| batch writes              | 4577ms | 3481ms | 703ms   | 1067ms | 5787ms    |               
|---------------------------+--------+--------+---------+--------+-----------|               
| random reads              | 1968ms | 1036ms | 9649ms  | 2591ms | 1132ms    |
|---------------------------+--------+--------+---------+--------+-----------|
| random reads              | 1553ms | 917ms  | 9755ms  | 2379ms | 1128ms    |
|---------------------------+--------+--------+---------+--------+-----------|
| random range reads        | 3548ms | 1470ms | 14841ms | 6819ms | 1662ms    |    
|---------------------------+--------+--------+---------+--------+-----------|     
| random range reads        | 3518ms | 1474ms | 14822ms | 6858ms | 1702ms    |               
|---------------------------+--------+--------+---------+--------+-----------|               
| random reads (4 threads)  | 451ms  | 207ms  | 2679ms  | 587ms  | 359ms     |               
|---------------------------+--------+--------+---------+--------+-----------|               
| random reads (8 threads)  | 240ms  | 108ms  | 1522ms  | 317ms  | 717ms     |               
|---------------------------+--------+--------+---------+--------+-----------|               
| random reads (16 threads) | 161ms  | 71ms   | 1438ms  | 205ms  | 2233ms    |
|---------------------------+--------+--------+---------+--------+-----------|
| random reads (32 threads) | 170ms  | 77ms   | 1474ms  | 226ms  | 5345ms    |
|---------------------------+--------+--------+---------+--------+-----------|
| removals                  | 3042ms | 972ms  | 4775ms  | 3421ms | 2691ms    |
+---------------------------+--------+--------+---------+--------+-----------+
```

## 個人の感想

個人的な感想としては、LMDBは individual writes が比較的遅いもののそこまででもないし、readやremovalsは他よりかなり速いので、総合的にはLMDBが良いという印象。

あと、要件として、書き込みは1箇所のみで良いけど、読み取りは1台のサーバー上の複数プロセスから行いたいというのがあるのを思い出しました。するとメモリマップトファイルを使う方式のほうがありがたいわけです。キャッシュなどのデータ構造をメモリ上に持つ方式だとプロセスごとにコピーを持つことになるので。あ、でもプロセスごとに別のキーを参照するケースが多い場合は別々にメモリ上にキャッシュ持つほうが、キャッシュのヒット率が高いという可能性はあるのか。

[Are You Sure You Want to Use MMAP in Your Database Management System? (CIDR 2022)](https://db.cs.cmu.edu/mmap-cidr2022/)が気になるところですが、[mmapbench/mmapbench.cpp at main · viktorleis/mmapbench · GitHub](https://github.com/viktorleis/mmapbench/blob/e1f594532c16565e8f3cf3da3b33ddd75bf1db42/mmapbench.cpp#L110)を見ると、ファイルサイズ2TiBと巨大な場合の話なので、そこまで大きくなければ大丈夫なのではないかと思いたいところですが、どうなんでしょうね。

あと、[Glauber Costa](https://twitter.com/glcst)さんの2020年の記事 [Modern storage is plenty fast. It is the APIs that are bad. | by Glauber Costa | ITNEXT](https://itnext.io/modern-storage-is-plenty-fast-it-is-the-apis-that-are-bad-6a68319fbc1a) も気になったのでメモ。

上の記事からリンクされている [Direct I/O writes: the best way to improve your credit score. | by Glauber Costa | ITNEXT](https://itnext.io/direct-i-o-writes-the-best-way-to-improve-your-credit-score-bd6c19cdfe46) も興味深かったです。
