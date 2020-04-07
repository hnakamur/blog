---
title: "io_uringのサンプルを試してみた"
date: 2020-04-07T17:34:14+09:00
---

## はじめに

io_uring について以下の素晴らしい入門記事を知ったので試してみたメモです。

* [io_uring By Example: An Article Series - Unixism](https://unixism.net/2020/04/io-uring-by-example-article-series/)
* [io_uring by example: Part 1 - Introduction - Unixism](https://unixism.net/2020/04/io-uring-by-example-part-1-introduction/)
* [io_uring By Example: Part 2 - Queuing multiple requests - Unixism](https://unixism.net/2020/04/io-uring-by-example-part-2-queuing-multiple-requests/)
* [io_uring By Example: Part 3 - A Web Server with io_uring - Unixism](https://unixism.net/2020/04/io-uring-by-example-part-3-a-web-server-with-io-uring/)

サンプルソースコード
[shuveb/io_uring-by-example: A companion repository for the io_uring by Example article series](https://github.com/shuveb/io_uring-by-example)
README に書いてありますが Linux カーネル 5.5 以上が必要となります。


Hacker News のスレッド
[Io_uring By Example: cat, cp and a web server with io_uring | Hacker News](https://news.ycombinator.com/item?id=22794396)

## 環境構築

自宅サーバーの Ubuntu 18.04 LTS に `linux-generic-hwe-18.04` を入れていますが、これの Linux カーネルは 5.3.x です。この環境に mainline のカーネルは入れたくなかったので別に環境を作ることにしました。

### Ubuntu 19.10 を Ubuntu 20.04 LTS beta にアップグレード

別の自宅サーバーで Ubuntu 19.10 があったのでこれをアップグレードしました。

[How To Upgrade Ubuntu To 20.04 LTS Focal Fossa - LinuxConfig.org](https://linuxconfig.org/how-to-upgrade-ubuntu-to-20-04-lts-focal-fossa) の手順を参考にしました。

まず元のバージョンで最新にします。

```console
$ sudo apt update 
$ sudo apt upgrade
$ sudo apt dist-upgrade
$ sudo apt autoremove
```

```console
$ sudo apt install update-manager-core
```

の後

```console
$ sudo do-release-upgrade
```

は `No new release found` となりました。

```console
$ sudo do-release-upgrade -d
```

を試すと先に再起動をするようメッセージが出たので、再起動後再度実行したら Ubuntu 20.04 LTS Focal Fossa beta のダウンロードとインストールが始まりました。

TUI のインストーラーで途中何回か設定ファイルをパッケージので上書きするか聞かれたので、差分を確認しつつ選択しました。

Ubuntu 20.04 LTS のインストールが終わったら再起動して、 Linux カーネルのバージョンを確認すると 5.4.x でした。 `apt show linux-generic-hwe-20.04` も同じバージョンでした。まだリリース前だからですかね。

## mainline のカーネルをインストール

[How to Install Kernel 5.6 in Ubuntu / Linux Mint | UbuntuHandbook](http://ubuntuhandbook.org/index.php/2020/03/install-kernel-5-6-ubuntu-linux-mint/) を参考にインストールしました。

[Index of /~kernel-ppa/mainline/v5.6](https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.6/0005-configs-based-on-Ubuntu-5.6.0-6.6.patch) から amd64 の `-all` と `-generic` の deb をダウンロードしました。

```console
$ curl -LO https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.6/linux-headers-5.6.0-050600_5.6.0-050600.202003292333_all.deb
$ curl -LO https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.6/linux-headers-5.6.0-050600-generic_5.6.0-050600.202003292333_amd64.deb
$ curl -LO https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.6/linux-headers-5.6.0-050600-generic_5.6.0-050600.202003292333_amd64.deb
$ curl -LO https://kernel.ubuntu.com/~kernel-ppa/mainline/v5.6/linux-modules-5.6.0-050600-generic_5.6.0-050600.202003292333_amd64.deb
```

その後以下のコマンドでインストールしました。

```console
sudo dpkg -i *.deb
```

## liburing の deb のビルドとインストール

[axboe/liburing](https://github.com/axboe/liburing) を見ると debian というディレクトリがあったので` ローカルで deb パッケージをビルドしてインストールしました。

```console
$ git clone https://github.com/axboe/liburing
$ cd liburing
```

`build-essential` と `mk-build-deps` を使うために必要なパッケージをインストールします。

```console
$ sudo apt install build-essential devscripts equivs
```

liburing のビルドに必要なパッケージをインストールするためのパッケージをビルド、インストールします。

```console
$ sudo mk-build-deps -i
```

`dpkg -l liburing-build-deps` でインストールされたことを確認します。

作成された `liburing-build-deps_0.4-2_all.deb` を親ディレクトリに移動します。

```console
$ mv liburing-build-deps_0.4-2_all.deb ..
```

liburing の deb パッケージをビルドします。

```console
$ dpkg-buildpackage -b --no-sign
```

完了したら `ls ../*.deb` で作成されたパッケージを確認し、インストールします。

```console
$ sudo dpkg -i ../liburing1_0.4-2_amd64.deb ../liburing-dev_0.4-2_amd64.deb
```

また `liburing-build-deps` パッケージはアンインストールしておきます。

```console
$ sudo dpkg -e ../liburing-build-deps_0.4-2_all.deb
```

## サンプルのビルドと実行

[shuveb/io_uring-by-example: A companion repository for the io_uring by Example article series](https://github.com/shuveb/io_uring-by-example) の `01_regular_cat` と `02_cat_uring` はディレクトリに cd して以下のようにビルドしました。

```console
$ cc main.c
```

実行は `./a.out 対象ファイル名` です。

`03_cat_liburing`, `04_cp_liburing`, `05_webserver_liburing` は liburing が必要なので以下のようにビルドします。

```console
$ cc main.c -luring
```

実行は以下のようにします。

* `03_cat_liburing` は `./a.out 対象ファイル名`
* `04_cp_liburing` は `./a.out コピー元ファイル名 コピー先ファイル名`
* `05_webserver_liburing` は `public` ディレクトリーを作ってそこに index.html などのファイルを作成し、別端末で `curl -v http://localhost:8000/` などとアクセスする感じです。

`05_webserver_liburing` のサンプル内には
`Linux kernel 5.5 has support for readv, but not for recv() or read()`
というコメントがありますが 5.6 ではサポートされているので、書き換えて試してみたいところです。
