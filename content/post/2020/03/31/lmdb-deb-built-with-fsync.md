---
title: "fsyncを使うようにビルドしたLMDBのdebパッケージを作った"
date: 2020-03-31T20:46:39+09:00
---

## はじめに

[Introducing Quicksilver: Configuration Distribution at Internet Scale](https://blog.cloudflare.com/introducing-quicksilver-configuration-distribution-at-internet-scale/)
で LMDB というキーバリューストアを知ったので、いろいろ調査したメモ。

## Cloudflare での LMDB の使い方

上の記事によると Cloudflare で DNS 用のデータストアに昔は Kyoto Tycoon を使っていたのですが、2015年にシステムを一新する際に LMDB に変えたそうです。

LMDB は値のサイズが大きくなるとそのサイズの連続領域を探すため遅くなり何分もかかるようになってしまったので、値をページサイズのチャンクに分けて回避したそうです。

キー・バリューの単位で CRC のチェックサムを付与して、チャンクを結合したときにチェックするようにしたとのこと。

値は [Snappy](https://en.wikipedia.org/wiki/Snappy_\(compression%29) で圧縮しているそうです。

3 年本番稼働して遭遇した [バグ](https://www.openldap.org/lists/openldap-technical/201407/msg00078.html) は 1 度だけで、データ破損は 1 度もないとのこと。

秒間 25 億の読み取りリクエスト、 1 日に 3 千万の書き込みリクエスト (秒に換算すると 34 回) を数千のサーバー上の 9 万以上のデータベースでさばいているそうです。

## LMDB について調べたメモ

[Lightning Memory-Mapped Database - Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database) に詳しい説明がありました。

ソースは [openldap / OpenLDAP · GitLab](https://git.openldap.org/openldap/openldap) 内の  [libraries/liblmdb](https://git.openldap.org/openldap/openldap/-/tree/master/libraries%2Fliblmdb) ディレクトリに同梱されています。

[LMDB/lmdb: Read-only mirror of official repo on openldap.org. Issues and pull requests here are ignored. Use OpenLDAP ITS for issues.](https://github.com/LMDB/lmdb) に読み取り専用のミラーがあります。 こちらのデフォルトブランチは mdb.master になっているのですが、コミットログを見てみると mdb.master ブランチは古くて gitlab のほうの master ブランチのほうが新しいのでそちらを見るほうが良さそうです。

[libraries/liblmdb/intro.doc](https://git.openldap.org/openldap/openldap/-/blob/master/libraries/liblmdb/intro.doc) と [libraries/liblmdb/lmdb.h · master · openldap / OpenLDAP · GitLab](https://git.openldap.org/openldap/openldap/-/blob/master/libraries/liblmdb/lmdb.h) に詳細な説明がありました。

Wikipedia の記事と合わせて概要をメモ。

* B+ ツリーを使用。B+ ツリーのブロックサイズを OS のページサイズと同じにして共有メモリ上に LMDB のインスタンスを置くとメモリ効率が良い。
* マルチスレッドやマルチプロセスから同時アクセス可能。
* 書き込みトランザクションは同時には 1 つだけ。ただし、読み取りトランザクションはブロックせずに行える。
* MVCC (multiversion concurrency control) 方式で使用中のデータは上書きせず、変更時は Copy on Write で別の領域に書く。
* メモリマップトファイルを使っていて API で取得したキーとバリューはゼロコピーで参照可能。
* 使用しなくなったページは管理して再利用する。
* スパースファイルに対応。
* 読み取りだけのときも読み取り専用のトランザクションが必須。開始時点の一貫した状態が参照できる。横から変更が入ると変更前の状態を維持するためにリソースが必要となるので、必要な読み取りが終わったら速やかにコミットあるいはロールバックでトランザクションを終了すること。
* トランザクションログ (WAL ログ) は無し。

## カスタム deb パッケージを作成

[Lightning Memory-Mapped Database - Wikipedia](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database) の Reliability の項を見ると GNU/Linux のビルドでは fdatasync を使っていてデータ破損のリスクがあるらしいです。

[Ubuntu – focal の liblmdb0 パッケージに関する詳細](https://packages.ubuntu.com/focal/liblmdb0) のソースをダウンロードしてビルドしてみると確かに fdatasync を使っていました。

そこで fsync を使うように調整して Ubuntu 18.04 LTS 用にバックポートしてみました。

* PPA [lmdb : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/lmdb)
* ソースパッケージ [hnakamur/lmdb-deb](https://github.com/hnakamur/lmdb-deb)

fsync を使うようにした変更のコミットは [Use fsync instead of fdatasync · hnakamur/lmdb-deb@c318850](https://github.com/hnakamur/lmdb-deb/commit/c318850ad9620fa8cb0fb9a2557d17ed85fc2214) です。変更前はビルドして `nm liblmdb.a | grep fdatasync` がヒットしたのが、変更後はヒットしなくなったことを確認済みです。
