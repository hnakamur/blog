Title: direnvでgo1.5.2とgo1.6beta1を切り替える設定
Date: 2015-12-19 01:45
Category: blog
Tags: go, direnv
Slug: blog/2015/12/19/switch_go1.5.2_and_go1.6beta1_with_direnv

## はじめに
go1.6beta1がリリースされました。go1.5.2と切り替えて使いたいので、[direnv/direnv](https://github.com/direnv/direnv)用の設定を書きました。

## 設定内容
以下の様な配置で使うことにしました。

* go1.5.2
  * goのインストールディレクトリ: /usr/local/go
  * GOPATH: ~/gocode
* go1.6beta1
  * goのインストールディレクトリ: /usr/local/go1.6beta1
  * GOPATH: ~/gocode1.6

まず、~/.bash_profileや~/.bashからはgoへのPATH設定やGOPATHの設定は削除します。

次に以下のファイルを作成します。

~/gocode/.envrc
```
export GOPATH=$HOME/gocode
export PATH=$PATH:/usr/local/go/bin:$GOPATH/bin
export GO15VENDOREXPERIMENT=1
```

~/gocode1.6/.envrc
```
export GOROOT=/usr/local/go1.6beta1
export GOPATH=$HOME/gocode1.6
export PATH=$PATH:$GOROOT/bin:$GOPATH/bin
```

上記の2つのファイルを有効にします。
```
direnv allow ~/gocode
direnv allow ~/gocode1.6
```

## 使い方

go1.5.2を使うときは ~/gocode/ 配下のディレクトリにcdします。
すると~/gocode/.envrcがsourceされてgo1.5.2用の設定が有効になります。

go1.6beta1を使うときは ~/gocode1.6/ 配下のディレクトリにcdします。
すると~/gocode/.envrcで有効にされたgo1.5.2用の設定はアンロードされて、~/gocode1.6/.envrcがsourceされgo1.6beta1用の設定が有効になります。
