---
layout: post
title: LXDを試してみた
date: 2014-12-01
comments: true
categories: [lxc, lxd]
---
## はじめに

LXDに関するページをいくつか紹介します。

* [\[lxc-users\] LXD an "hypervisor" for containers (based on liblxc)](https://lists.linuxcontainers.org/pipermail/lxc-users/2014-November/007978.html)
    * LXCメーリングリストに投稿されたLXDのアナウンスメール
* [LXDのホームページ](http://www.ubuntu.com/cloud/tools/lxd)
* [lxc/lxd githubレポジトリ](https://github.com/lxc/lxd)
* [Dustin KirklandさんによるLXDの紹介 (2分7秒)](https://insights.ubuntu.com/2014/11/04/lxd-the-linux-container-daemon/)
    * LXDの発音は[1分18秒あたり]( https://www.youtube.com/watch?v=U-lXf85Mhno&t=1m18s )
* [Ubuntu LXD: Not a Docker replacement, a Docker enhancement | ZDNet](http://www.zdnet.com/ubuntu-lxd-not-a-docker-replacement-a-docker-enhancement-7000035463/)
    * 「LXDはdockerを置き換えるものではなく強化するもの」というタイトルの解説記事


目指しているのは以下の様なものらしいです。

* デフォルトでセキュア
    * コンテナを非rootユーザで稼働できる
    * コンテナを隔離して安全に動かせる
* コンテナでは単一プロセスを動かすだけではなく完全なOS環境を動かす
* リモートのイメージ管理サービスと連携してライブマイグレーションを可能にする
* OpenStackとも連携

## セットアップ

Ubuntu 14.04で試しました。
バイナリパッケージをインストールする手順とソースからビルドする手順を書いておきますが、実際に試したのは後者です。正確には最初前者を試したのですが、その後何してよいかドキュメントが見当たらないので後者を試した感じです。

### バイナリパッケージをインストールする手順

[The next hypervisor: LXD is fast, secure container management for Linux | Cloud | Ubuntu](http://www.ubuntu.com/cloud/tools/lxd)の"Getting started with LXD"に書いてあります。

add-apt-repositoryを使うため事前にsoftware-properties-commonパッケージをインストールしておく必要があります。

```
sudo aptitude install software-properties-common
```

その後以下のコマンドを実行します。

```
sudo add-apt-repository cloud-archive:juno
sudo apt-get update
sudo apt-get install nova-compute-flex
```

### ソースからビルドする手順

[lxc/lxd](https://github.com/lxc/lxd#installing-the-dependencies)の手順に従います。

以下のコマンドで依存ライブラリをインストールします。

```
sudo apt-get install lxc lxc-dev mercurial git pkg-config
```

Goをインストールします。

```
sudo apt-get install software-properties-common
sudo add-apt-repository ppa:ubuntu-lxc/lxd-daily
sudo apt-get update
sudo apt-get install golang
```

GOPATHのディレクトリを作成して、GOPATH環境変数を設定します。
以下はbashを使っている想定で ~/.bashrc に追加してシェルを再起動する例です。

```
mkdir -p ~/go
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
exec $SHELL -l
```

go getしてソースディレクトリに移動してビルドします。

```
go get github.com/lxc/lxd
cd $GOPATH/src/github.com/lxc/lxd
go get -v -d ./...
make
```

./lxc/lxcと./lxd/lxdという2つの実行ファイルが作られます。

```
vagrant@ubuntu-1404:~/go/src/github.com/lxc/lxd$ file ./lxc/lxc ./lxd/lxd
./lxc/lxc: ELF 64-bit LSB  executable, x86-64, version 1 (SYSV), dynamically linked (uses shared libs), for GNU/Linux 2.6.24, BuildID[sha1]=a317752267685a543f724c02c2fb827e03564236, not stripped
./lxd/lxd: ELF 64-bit LSB  executable, x86-64, version 1 (SYSV), dynamically linked (uses shared libs), for GNU/Linux 2.6.24, BuildID[sha1]=8f4ff9b64ecda66a2269c18fd5c440620d548da3, not stripped
```

lxdはlxdのデーモンです。lxcはlxdに通信するクライアントプログラムです。[go-lxc.v2 - gopkg.in/lxc/go-lxc.v2](http://gopkg.in/lxc/go-lxc.v2)というLXCのGoバインディングライブラリを使用しています。

## セットアップ
ビルド後以下の環境整備が必要です。

```
sudo mkdir -p /var/lib/lxd
sudo chown $USER:$USER /var/lib/lxd
echo "$USER:1000000:65536" | sudo tee -a /etc/subuid /etc/subgid
```

## 使い方

### lxdの起動

```
./lxd/lxd &
```

### lxcのコンテナ作成

```
./lxc/lxc create iamge:ubuntu foo
```

READMEでは `image:ubuntu` をつけていませんが、これだと以下の様なエラーになりました。

```
$ ./lxc/lxc create baz
error: Only the default ubuntu image is supported. Try `lxc create images:ubuntu foo`.
```

### lxcのコンテナ起動

```
./lxc/lxc start foo
```

### lxcのコンテナ一覧表示

```
$ ./lxc/lxc
foo
```

なお、通常のlxcとはコンテナの管理が別になっているのか(要確認)、 `lxc-ls` しても fooは表示されませんでした。

### lxcのコンテナ停止

```
./lxc/lxc stop foo
```

### lxcのコンテナ停止

```
./lxc/lxc delete foo
```

### lxc shellが未実装！

コンテナでコマンドを実行してみたいところなのですが、 `lxc shell` というサブコマンドは未実装だそうです。

```
$ ./lxc/lxc help
Usage: lxc [subcommand] [options]
Available commands:
  config     - Manage configuration.
  create     - lxc create images:ubuntu <name>
  delete     - lxc delete <resource>
  finger     - Fingers the lxd instance to check if it is up and working.
  freeze     - Changes a containers state to freeze.
  help       - Presents details on how to use lxd.
  list       - Lists the available resources.
  remote     - Manage remote lxc servers.
  restart    - Changes a containers state to restart.
  shell      - Start a shell or specified command (NOT IMPLEMENTED) in a container.
  start      - Changes a containers state to start.
  stop       - Changes a containers state to stop.
  unfreeze   - Changes a containers state to unfreeze.
  version    - Prints the version number of lxd.
```

ソースを見ても [lxd/shell.go at a315c07c632188f7d37fa8dbbe3f1b7d87ab34de · lxc/lxd](https://github.com/lxc/lxd/blob/a315c07c632188f7d37fa8dbbe3f1b7d87ab34de/lxc/shell.go#L38-L42) のあたりにTODOと書かれています。

ただ、[lxc/go-lxc](https://github.com/lxc/go-lxc)のソースを見ると、コンテナ内でコマンドを実行するための関数はあるのですが、

https://github.com/lxc/go-lxc/blob/bc0a9447e0be56f8e35d0affe83a92e638308e2f/container.go#L422-L423

```
// Execute executes the given command in a temporary container.
func (c *Container) Execute(args ...string) ([]byte, error) {
```

コマンド実行後に標準出力の結果を戻り値で受け取るようになっています。

シェルを起動してインタラクティブに入出力するには、標準入力、標準出力、標準エラー出力をストリームのようにリアルタイムにやりとりするような関数が必要だと思います。

## おわりに

早く `lxc shell` が実装されて欲しいですね！

2015-04-23 追記

[LXD 0.7ではlxc execでシェルの対話操作もできるようになっていました](/blog/2015/04/23/try-lxd-0.7-with-vagrant/)に書きましたが、 `lxc exec コンテナ名 /bin/bash` でシェルの対話操作もできるようになっていました。
