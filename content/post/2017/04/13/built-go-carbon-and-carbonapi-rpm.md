+++
title="go, go-carbon, carbonapiのrpmをfedora coprでビルドしてみた"
date = "2017-04-13T05:13:00+09:00"
tags = ["go", "rpm", "carbon"]
categories = ["blog"]
+++



## はじめに

go, go-carbon, carbonapiのrpmをfedora coprでビルドしたのでメモです。

goのrpmはCentOS 6と7、go-carbonとcarbonapiはCentOS 7用のrpmをビルドしました。


## goのrpm

今まではgoの公式バイナリを
[Downloads - The Go Programming Language](https://golang.org/dl/)
からダウンロードして使っていました。通常の利用では公式バイナリを使うほうが安心感があって良いのですが、goで書かれたライブラリやプログラムのrpmを
[Fedora Copr](https://copr.fedorainfracloud.org/)
でビルドするとなると、rpmのspecファイルに `BuildRequires: golang >= 1.8` のように書いてgoのrpmを参照するようにしたいところです。

この記事を書いている時点ではCentOS7のbaseレポジトリでgolangというパッケージ名でバージョン1.6.3が提供されています。

```console
$ yum info golang
...(snip)...
Available Packages
Name        : golang
Arch        : x86_64
Version     : 1.6.3
Release     : 2.el7
...(snip)...
```

しかしやはり最新版が使いたいです。

##### Ubuntu 16.04でのgoのパッケージ

ちなみにUbuntu 16.04の標準パッケージではgolangというパッケージ名で1.6が提供されています。

```console
$ apt show golang
Package: golang
Version: 2:1.6-1ubuntu4
Priority: optional
Section: devel
Source: golang-defaults
Origin: Ubuntu
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
...(snip)...
```

`Ubuntu · golang/go Wiki <https://github.com/golang/go/wiki/Ubuntu>`
に Ubuntu 16.04用の PPA
[Golang Backports : Simon Eisenmann](https://launchpad.net/~longsleep/+archive/ubuntu/golang-backports)
が紹介されていて1.8がインストール可能らしいです。
[Golang 1.8 PPA for Ubuntu 16.04 Xenial - Stdin.xyz](https://www.stdin.xyz/2017/01/04/golang-1.8-ppa-for-ubuntu-16.04-xenial/)
にブログ記事がありました。

さらに検索してみると
[golang-1.8 package : Ubuntu](https://launchpad.net/ubuntu/+source/golang-1.8)
というページもあって、これはUbuntu developersがメンテナになっていて2017-04-11に1.8.1が提供されていました。

なお、どちらもまだ試してないです。

#### fedora coprでredhatの方によるrpmを発見

CentOS 7用のrpmを探してみると
[jcajka/golang1.8 Copr](https://copr.fedorainfracloud.org/coprs/jcajka/golang1.8/)
というのを見つけました。
ページ右の Homepage のリンクを辿ると
[jcajka/copr-golang: Spec files for golang builds in COPR(https://copr.fedoraproject.org)](https://github.com/jcajka/copr-golang)
でソースも公開されています。
`golang1.8` ブランチが1.8.xリリース用となっています。

READMEに Based on Fedora dist-git(http://pkgs.fedoraproject.org/cgit/golang.git/). と書かれており、
[copr-golang/golang.spec at golang1.8 · jcajka/copr-golang](https://github.com/jcajka/copr-golang/blob/golang1.8/golang.spec)
のChangelogを見るとredhatの方が作られているので、独自パッチが当たってはいますが安心して使えそうです。

ですが
[jcajka/golang1.8 Copr](https://copr.fedorainfracloud.org/coprs/jcajka/golang1.8/)
を見るとCentOS 7はビルド対象ですが、CentOS 6は含まれていません。
また、
[Builds for jcajka/golang1.8](https://copr.fedorainfracloud.org/coprs/jcajka/golang1.8/builds/)
を見ると、この記事を書いている2017-04-13時点ではgo 1.8が提供されていますが最新版の1.8.1は提供されていません。

#### specファイルを書き換えて1.8.1のrpmを作成

ということで、
[copr-golang/golang.spec at golang1.8 · jcajka/copr-golang](https://github.com/jcajka/copr-golang/blob/golang1.8/golang.spec)
を元にバージョンを1.8.1に書き換えてビルドしてみました。

[hnakamur/golang-1.8 Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/golang-1.8/)
から以下のコマンドでインストール可能です。

```console
ver=$(rpm -q --qf %{VERSION} --whatprovides redhat-release)

sudo curl -sL -o /etc/yum.repos.d/hnakamur-golang-1.8.repo https://copr.fedoraproject.org/coprs/hnakamur/golang-1.8/repo/epel-${ver}/hnakamur-golang-1.8-epel-${ver}.repo

sudo yum install golang
```

rpmのソースは
[hnakamur/golang-1.8-rpm](https://github.com/hnakamur/golang-1.8-rpm)
で公開しています。
[nginxのカスタムrpmをmockでビルドできることを確認してからcoprでビルド・配布する環境を作りました](http://blog-preview.naruh.com/blog/2015/12/15/using_mock_and_copr_to_build_nginx_rpm_on_docker/) で書いた方法で、手元のdockerでビルドが通ることを確認後、sprmをcoprにアップロードしてビルドしました。

今後1.8.xがリリースされたら適宜更新していく予定です。なお、fedora coreでは最新版以外はそのうち消されるので、将来1.8.2をビルド、公開すると1.8.1はそのうちこのレポジトリからは消えます。

特定のバージョンのrpmのレポジトリを維持したい方はこのレポジトリは当てにせず、自前でレポジトリを作ってください。

## go-carbonとcarbonapi

* [lomik/go-carbon: Golang implementation of Graphite/Carbon server with classic architecture: Agent -> Cache -> Persister](https://github.com/lomik/go-carbon)
* [go-graphite/carbonapi: API server for github.com/dgryski/carbonzipper](https://github.com/go-graphite/carbonapi)

は

* [graphite-project/carbon: Carbon is one of the components of Graphite, and is responsible for receiving metrics over the network and writing them down to disk using a storage backend.](https://github.com/graphite-project/carbon)
* [graphite-project/graphite-web: A highly scalable real-time graphing system](https://github.com/graphite-project/graphite-web)

をGoで再実装したものです。完全互換ではなくサブセットですが実用上必要な機能は揃っていると思います。
環境構築にPythonのインストールが不要なのとパフォーマンスが良いのでGo版のほうが魅力的です。

Go版の作者の1人である [Damian Gryskiさんのツイート: "@icecrime here's a talk about our stack from fosdem this year: https://t.co/MT04Z7Embm"](https://twitter.com/dgryski/status/847308606722588673)
で紹介されている動画
[FOSDEM 2017 - Graphite@Scale or How to store millions metrics per second](https://fosdem.org/2017/schedule/event/graphite_at_scale/)
を見たのですが、最初はPython版を使っていたが規模が大きくなるにつれて大変になったので、コンポーネントをひとつずつGoで再実装して置き換えていったという話がされていて素晴らしかったです。
また今後の展望についても話されていて、whisperファイルに代わるフォーマットを検討するなどこちらも期待が持てる内容でした。


## go-carbonのrpm

[lomik/go-carbon: Golang implementation of Graphite/Carbon server with classic architecture: Agent -> Cache -> Persister](https://github.com/lomik/go-carbon) の
[go-carbon/go-carbon.spec.centos at 061fa9139b1912206b4ec09dbcba51678d8e97ad · lomik/go-carbon](https://github.com/lomik/go-carbon/blob/061fa9139b1912206b4ec09dbcba51678d8e97ad/deploy/go-carbon.spec.centos)
にrpmのspecファイルが提供されているのですがCentOS 6用となっていて
[initスクリプト](https://github.com/lomik/go-carbon/blob/master/deploy/go-carbon.init.centos)
は用意されていますが、CentOS 7のsystemd用のserviceファイルはありません。
またインストール先が `/usr/local/sbin` になっているのもrpmパッケージとしてはいまいちです。

そこで、CentOS 7用のrpmを作成しました。
[hnakamur/go-carbon Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/go-carbon/)

ソースは
[hnakamur/go-carbon-rpm](https://github.com/hnakamur/go-carbon-rpm)
で公開しています。

specファイルは
[go-carbon-rpm/go-carbon.spec](https://github.com/hnakamur/go-carbon-rpm/blob/67bb23168fe8b56fe6b83b482b2e2129f2dfd2b9/SPECS/go-carbon.spec)
です。

rpmパッケージを作るにあたって、バージョンのつけ方は
[PackagingDrafts/Go - FedoraProject](https://fedoraproject.org/wiki/PackagingDrafts/Go)
の方針に合わせました。

当初
[Release Version 0.9.1 · lomik/go-carbon](https://github.com/lomik/go-carbon/releases/tag/v0.9.1)
のタグに対してrpmを作ろうと思ったのですが
[Release 0.7.0 · go-graphite/carbonapi](https://github.com/go-graphite/carbonapi/releases/tag/0.7.0)
との組み合わせだと動かなかったので、新しいコミットで動くものを選びました。

#### fedora coprでビルドするには必要なファイルを全てsrpmに入れておく必要があります

当初手元でビルドしていたときはspecファイルの `%prep` セクションで `go get` や `git clone` や `make submodules` してソースをネットワーク経由で取得していたのですが、fedora copr上ではホスト名が解決できないというエラーが出てダメでした。

そこで
[go-carbon-rpm/go-carbon.specのコメント](https://github.com/hnakamur/go-carbon-rpm/blob/67bb23168fe8b56fe6b83b482b2e2129f2dfd2b9/SPECS/go-carbon.spec#L23-L29)
に書いた手順で予め必要なソースファイルを全てtarballに入れてsrpm内に含めるようにしました。

## carbonapiのrpm

当初は最新のコミットでrpmを作ろうとしていたのですが、grafanaでグラフが表示されないという問題に遭遇しました。調べてみると
[Current master seems to always force caching and return no results · Issue #198 · go-graphite/carbonapi](https://github.com/go-graphite/carbonapi/issues/198)
というイシューを発見。タグが打たれたリリースを使ってくださいとコメントされていたので、それに従って
[Release 0.7.0](https://github.com/go-graphite/carbonapi/releases/tag/0.7.0)
のrpmを作りました。

[hnakamur/carbonapi Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/carbonapi/)

ソースは
[hnakamur/carbonapi-rpm](https://github.com/hnakamur/carbonapi-rpm)
で
specファイルは
[carbonapi-rpm/carbonapi.spec at 84659a13ce235f33a9c699f93cfe6d2864850b9e · hnakamur/carbonapi-rpm](https://github.com/hnakamur/carbonapi-rpm/blob/84659a13ce235f33a9c699f93cfe6d2864850b9e/SPECS/carbonapi.spec)
です。

ソースのtarballは
[carbonapi-rpm/carbonapi.specのコメント](https://github.com/hnakamur/carbonapi-rpm/blob/84659a13ce235f33a9c699f93cfe6d2864850b9e/SPECS/carbonapi.spec#L21-L33)
に書いた手順で作っています。
carbonapiのgithubレポジトリはつい最近
https://github.com/dgryski/carbonapi
から
https://github.com/go-graphite/carbonapi
に移管されました。
タグ0.7.0の頃は
https://github.com/dgryski/carbonapi
だったので、tarball内のソースのディレクトリをそれに合わせて調整しています。

## おわりに

goのrpmとそれを使ってgo-carbonとcarbonapiのrpmを作ってみました。

[go-carbon with built-in carbonserver enabled, carbonapi and grafana setup memo](https://gist.github.com/hnakamur/0a0e18acc1a8c452c0d64124a61a7d94)
の最後のほうに書いた手順でgrafanaを入れて軽く動作確認はしましたが、高負荷時にちゃんと動くかは未検証です。

これでgoで書かれたツールもrpmパッケージを作れるようになったので、自分が使うものはパッケージを作っていきたいと思います。
