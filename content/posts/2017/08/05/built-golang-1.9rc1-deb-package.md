+++
title="golang 1.9rc1のUbuntu 16.04用debパッケージをビルドした"
date = "2017-08-05T10:15:00+09:00"
tags = ["go", "deb"]
categories = ["blog"]
+++


## はじめに

[Ubuntu · golang/go Wiki](https://github.com/golang/go/wiki/Ubuntu) で紹介されている
[Golang Backports : Simon Eisenmann](https://launchpad.net/~longsleep/+archive/ubuntu/golang-backports) を改変してgo 1.9rc1のUbuntu 16.04用debパッケージをビルドしたのでメモです。

[golang 1.9 : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.9) というPPAで配布しています。

この記事の手順は [git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順](https://hnakamur.github.io/blog/2017/07/05/how-to-build-deb-with-git-buildpackage/) で書いたセットアップが済んでいることが前提です。

## 今回ビルドしたdebのインストール手順

今回ビルドしたdebパッケージのインストール手順は以下の通りです。

```console
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:hnakamur/golang-1.9
sudo apt update
sudo apt install golang-go
```

LXDのコンテナを新規に作って試す場合の手順も書いておきます。以下ではコンテナ名を `go19` としていますが適宜変更してください。

```console
lxc launch images:ubuntu/xenial go19
lxc exec go19 bash
apt update
apt install software-properties-common
add-apt-repository ppa:hnakamur/golang-1.9
apt update
apt install golang-go
```

## goのdebパッケージの作成手順メモ

作成と言っても一からではなくて、 Simon Eisenmann (LaunchPadのアカウントID: longsleep) さんのdebパッケージのソースを取って来て、オリジンのソースを入れ替えて適宜書き換えるだけです。

### Simon さんのdebパッケージのソースをダウンロード

[Packages in “Golang Backports” : Golang Backports : Simon Eisenmann](https://launchpad.net/~longsleep/+archive/ubuntu/golang-backports/+packages) でパッケージ名のリストを確認すると、以下の3つのパッケージがあります。

* golang-1.8
* golang-1.8-race-detector-runtime
* golang-defaults

golang-1.8 のリンクをクリックして展開すると複数のパッケージファイルが並んでいますが、そのうち
golang-1.8-go というパッケージファイルをインストールすると /usr/lib/go-1.8/ 以下に /usr/lib/go-1.8/bin/go のように配置されるようになっています。

同様に golang-defaults のリンクをクリックして展開すると、 golang-go というパッケージファイルがあり、これをインストールすると `/usr/bin/go -> ../lib/go-1.8/bin/go` というシンボリックリンクなどが作られるようになっています。

golang-1.8-race-detector-runtime はよくわかってないので今回はスキップします。

以下のコマンドを実行して golang-1.8 と golang-defaults のソースパッケージをダウンロードします。
ここでは `~/longsleep-go-deb` という作業ディレクトリを作成していますが、適宜変更してください。

```console
sudo add-apt-repository ppa:longsleep/golang-backports
sudo apt-get update
mkdir ~/longsleep-go-deb
cd !$
apt source golang-1.8-go golang-defaults
```

### golang-1.8のパッケージを改変してgolang-1.9のパッケージを作成

最終結果は https://github.com/hnakamur/golang-deb で公開しています。
以下の手順は何回か試行錯誤した結果なのですが、上記のレポジトリと多少ずれているかもしれません。もう一度一からやり直して確認するの面倒なので、そのまま書いてしまいます。

以下ではレポジトリの作業ディレクトリを `~/.ghq/github.com/hnakamur/golang-deb` として説明します。適宜変更してください。

まず、 `.dsc` ファイルをインポートして、レポジトリを新規作成します。
ディレクトリ名を `golang` から `golang-deb` に変更して、そこに移動します。

```console
cd ~/.ghq/github.com/hnakamur
gbp import-dsc --pristine-tar \
	--debian-branch=ubuntu-1.8 --upstream-branch=upstream-1.8 \
	~/longsleep-go-deb/golang-1.8/golang-1.8_1.8.3-2ubuntu1~longsleep1-xenial.dsc
mv golang golang-deb
cd !$
```

ブランチを確認します。

```console
$ git branch
* master
  pristine-tar
  ubuntu-1.8
  upstream-1.8
```

タグを確認します。

```console
$ git tag
debian/1.8.3-2ubuntu1_longsleep1-xenial
upstream/1.8.3-2ubuntu1_longsleep1
```

このレポジトリには `debian/gbp.conf.in` というファイルがあって、gbp (git-buildpackage) 用のブランチやタグの形式が記載されています。

アップストリームのブランチは `upstream-X.Y` で、debパッケージのブランチは `ubuntu-X.Y` だということがわかります。 `X.Y` の部分は `debian/changelog` ファイルからバージョンを読み取って展開されるようになっています。

```console
$ cat debian/gbp.conf.in
[DEFAULT]
debian-branch = ubuntu-X.Y
debian-tag = debian/%(version)s
upstream-branch = upstream-X.Y
upstream-tag = upstream/%(version)s
pristine-tar = True

[git-dch]
meta = 1
```

試行錯誤していた時に、 `[git-dch]` というセクション名は古いので `[dch]` にせよという主旨の警告が出ました。そこで以下のコマンドを実行して変更しました。

```console
sed -i -e 's/^\[git-dch\]/[dch]/' debian/gbp.conf.in
```

さらに以下のコマンドを実行して `debian/gbp.conf.in` から `debian/gbp.conf` を生成して上書きします。

```console
debian/rules gencontrol
```

変更した `debian/gbp.conf.in` と `debian/gbp.conf` をコミットします。

```console
git commit -m 'Rename git-dch to dch in debian.gbp.conf.in' debian/gbp.conf.in debian/gbp.conf
```

`ubuntu-1.8` ブランチにも上記の変更をマージします。

```console
git checkout ubuntu-1.8
git merge --ff master
```

`upstream-1.8` ブランチから `upstream-1.9` ブランチを、
`ubuntu-1.8` ブランチから `ubuntu-1.9` ブランチを作成し、
`ubuntu-1.9` ブランチに切り替えます。

```console
git branch upstream-1.9 upstream-1.8
git checkout -b ubuntu-1.9 ubuntu-1.8
```

以下のコマンドを実行して `debian/changelog` にエントリを追加します。

```console
gbp dch -R --debian-branch ubuntu-1.9
```

エディタ (私の場合は vim) が起動しますので、先頭に追加されたエントリを以下のように編集します。

```text
golang-1.9 (1.9~rc1-1ubuntu1~hnakamur1-xenial) xenial; urgency=medium

  * New upstream release.

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Sat, 29 Jul 2017 00:38:32 +0900
```

以下のコマンドを実行して、ソースパッケージ内のgoのバージョンに依存したファイルを再生成します。

```console
debian/rules gencontrol
```

更新したファイルをコミットします。

```console
git add .
git commit -m 'Change control file to golang-1.9'
```

次に go 1.9rc1 のアップストリームのソースをインポートします。

```console
$ gbp import-orig --no-merge --no-interactive \
   --debian-branch=ubuntu-1.9 --upstream-branch=upstream-1.9 \
   --upstream-version=1.9~rc1 ~/go1.9rc1.src.tar.gz
gbp:info: Importing '/home/hnakamur/go1.9rc1.src.tar.gz' to branch 'upstream-1.9'...
gbp:info: Source package is golang-1.9
gbp:info: Upstream version is 1.9~rc1
gbp:info: Successfully imported version 1.9~rc1 of /home/hnakamur/go1.9rc1.src.tar.gz
```

`ubuntu-1.9` ブランチに切り替えて `upstream-1.9` ブランチの変更をマージします。

```console
git checkout ubuntu-1.9
git merge --no-ff upstream-1.9
```

今回作成するdebパッケージのバージョン `1.9~rc1-1ubuntu1~hnakamur1-xenial` の `~` を `_` に置き換えたタグを打っておきます。

```console
git tag upstream/1.9_rc1-1ubuntu1_hnakamur1 upstream-1.9
```

さらに `master` ブランチに `upstream-1.9` ブランチの内容をマージしておきました。

```console
git checkout master
git merge ubuntu-1.9
```

以下のコマンドでソースパッケージをビルドします。

```console
gbp buildpackage --git-pristine-tar-commit --git-export-dir=../build-area --git-debian-branch=ubuntu-1.9 -S -sa
```

以下のコマンドでバイナリパッケージをビルドします。

```console
sudo pbuilder build ../build-area/golang-1.9_1.9~rc1-1ubuntu1~hnakamur1-xenial.dsc
```

`/var/cache/pbuilder/result/` に生成されたdebファイルを、LXDの新規コンテナにコピー、インストールし、動作確認しました。動作確認と言っても `/usr/lib/go-1.9/bin/go version` を実行して出力を確認しただけです。

### golang-1.9のPPAを作成してソースパッケージをアップロード

[Launchpad](https://launchpad.net/) にログインして自分のページに移動して `golang-1.9` というPPAを作成しました。

すると Uploading packages to this PPA というところに
`dput ppa:hnakamur/golang-1.9 <source.changes>` 
と書かれていますので、以下のコマンドを実行してソースパッケージをアップロードしました。

```console
dput ppa:hnakamur/golang-1.9 ../build-area/golang-1.9_1.9~rc1-1ubuntu1~hnakamur1-xenial_source.changes
```

しばらく待ってビルド結果を見ると amd64 は通ったのですが i386 はビルドエラーになっていました。
自分で使うのは amd64 だけなので 
[nginx+luaのカスタムdebパッケージを作ってみた](https://hnakamur.github.io/blog/2017/07/18/created-nginx-custom-deb-package/)
の「PPAでビルドするアーキテクチャの変更」の手順で i386 は以降のビルド対象から外しました。

### go 1.8用のgolang-defaultsパッケージgo 1.9用に改変

まず、 `.dsc` ファイルをインポートして自分のレポジトリを作ります。

```console
cd ~/.ghq/github.com/hnakamur
gbp import-dsc --pristine-tar ~/longsleep-go-deb/golang-defaults_1.8~1ubuntu2~xenial.dsc
mv golang-defaults golang-defaults-deb
cd !$
```

新しいリリースを `gbp dch -R` で作ろうとしたらタグが無くてエラーになったので、直接 `dch` を使うようにしました。

```console
dch -R
```

前のエントリ

```text
golang-defaults (2:1.8~1ubuntu2~xenial) xenial; urgency=medium

  * Backport to 16.04.
  * Use Golang 1.8.

 -- Simon Eisenmann <simon@longsleep.org>  Tue, 03 Jan 2017 16:49:41 +0100
```

を参考にして、先頭に追加されたエントリを以下のように編集しました。

```text
golang-defaults (2:1.9~1ubuntu1~hnakamur1) xenial; urgency=medium

  * Use Golang 1.9.

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Sat, 05 Aug 2017 09:38:34 +0900
```

バージョンに対応したタグを打ちます。

```console
git tag debian/1.9_1ubuntu1_hnakamur1
```

ソースパッケージをビルドします。

```console
gbp buildpackage --git-export-dir=../build-area -S -sa
```

バイナリパッケージをビルドします。

```console
sudo pbuilder build ../build-area/golang-defaults_1.9~1ubuntu1~hnakamur1.dsc
```

生成されたバイナリパッケージの中身を確認します。

```console
$ dpkg -c /var/cache/pbuilder/result/golang-go_1.9~1ubuntu1~hnakamur1_amd64.deb
drwxr-xr-x root/root         0 2017-08-05 09:43 ./
drwxr-xr-x root/root         0 2017-08-05 09:43 ./usr/
drwxr-xr-x root/root         0 2017-08-05 09:43 ./usr/lib/
drwxr-xr-x root/root         0 2017-08-05 09:43 ./usr/share/
drwxr-xr-x root/root         0 2017-08-05 09:43 ./usr/share/doc/
drwxr-xr-x root/root         0 2017-08-05 09:43 ./usr/share/doc/golang-go/
-rw-r--r-- root/root       870 2017-08-05 09:39 ./usr/share/doc/golang-go/changelog.gz
-rw-r--r-- root/root      2890 2017-08-05 09:39 ./usr/share/doc/golang-go/copyright
drwxr-xr-x root/root         0 2017-08-05 09:43 ./usr/bin/
lrwxrwxrwx root/root         0 2017-08-05 09:43 ./usr/lib/go -> go-1.9
lrwxrwxrwx root/root         0 2017-08-05 09:43 ./usr/bin/gofmt -> ../lib/go-1.9/bin/gofmt
lrwxrwxrwx root/root         0 2017-08-05 09:43 ./usr/bin/go -> ../lib/go-1.9/bin/go
```

LXDコンテナにパッケージをコピーして動作確認した後、
PPAにソースパッケージをアップロードしてビルドしました。

```console
dput ppa:hnakamur/golang-1.9 ../build-area/golang-defaults_1.9~1ubuntu1~hnakamur1_source.changes
```

## おわりに

使い方は先頭の「今回ビルドしたdebのインストール手順」の項に書いた通りです。
今後、go 1.9.xの新しいリリース候補や正式版が出たら、debパッケージもすぐ更新するつもりです。

一方で dh-make-golang パッケージなどは Simon さんのパッケージに依存していますので、
正式版が出たら Simon さんにも更新をお願いしようと思います。
以前 1.8.3 を Simon さんにメールでお願いしたら数日で作ってくれました。

さらに、goで書かれたコマンドやサーバのうち自分で使うものはdebパッケージを作っていきたいと
考えています。というより、それがしたいからgoのパッケージを作ったわけなので。
