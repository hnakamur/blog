---
title: "gbpとsbuildとPPAでUbuntu 20.04 LTS用のdebパッケージをビルド"
date: 2020-04-24T19:49:58+09:00
---

## はじめに

このブログの過去記事でも書いたように（とっちらかってますが、いつか整理したい）、私は [git-buildpackage](https://github.com/agx/git-buildpackage) と [sbuild](https://wiki.ubuntu.com/SimpleSbuild) と [PPA](https://launchpad.net/ubuntu/+ppas) で Ubuntu 18.04 LTS (以下 bionic と略) 用のカスタム deb パッケージをビルドしてきました。

Ubuntu 20.04 LTS (以下 focal と略) がリリースされたので今後 focal に移行が完了するまでは focal と bionic 用の deb をビルドしようと思います。

ということで bionic 用にもビルドできるようにしつつ focal 用にもビルドするための手順をメモしておきます（今は [hnakamur/openresty-luajit-deb](https://github.com/hnakamur/openresty-luajit-deb) の 1 つしか試してないので今後修正するかもしれません）。

## gbp での対応

これまで gbp の debian-branch を master にしていましたが、 master は focal 用にして、 bionic 用には ubuntu/bionic というブランチを作ることにします。

各 deb 用のディレクトリで以下のようにします。

なお [Highlights from Git 2.23 - The GitHub Blog](https://github.blog/2019-08-16-highlights-from-git-2-23/) で `git checkout` が `git switch/restore` に変わったのは知っていますが、私が今使っている bionic の git は 2.17.1 なので以下の説明は古いコマンドで書きます。

```console
git checkout master
git checkout -b ubuntu/bionic
```

`debian/gbp.conf` が無い場合は以下の内容で作成します。有る場合は以下の内容を含むように編集します。

```text
[DEFAULT]
debian-branch = ubuntu/bionic
```

`debian/gbp.conf` を追加しておきます。

```console
git add debian/gbp.conf
git commit -v
```

## `debian/changelog` での書き方

```console
git checkout master
```

で focal 用の master ブランチに切り替えて以下のコマンドで `debian/changelog` にエントリを追加します（普段は `gbp dch -R` ですが今回は master ブランチは何も変更していないので `dch -R` を使う必要があります）。

```console
dch -R
```

以下の用にリリース番号内のディストリビューションの部分とセミコロンの前の部分を focal に変更します。

```text
luajit (2.1.0~beta3.20200102+dfsg-1ppa1~focal) focal; urgency=medium

  * Port to Ubuntu 20.04 LTS

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Fri, 24 Apr 2020 18:42:42 +0900

luajit (2.1.0~beta3.20200102+dfsg-1ppa1~bionic) bionic; urgency=medium

  * New upstream version 2.1.0_beta3.20200102

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Tue, 21 Jan 2020 23:39:21 +0900

…(略)…
```

## gbp buildpackage でのソースパッケージの作成

git-buildpackage は [git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順 · hnakamur's blog](https://hnakamur.github.io/blog/2017/07/05/how-to-build-deb-with-git-buildpackage/) の手順でセットアップ済みとします。

`gbp buildpackage` では `--git-dist` オプションで focal を指定します（ [gbp-buildpackage (1)](https://manpages.ubuntu.com/manpages/focal/en/man1/gbp-buildpackage.1.html) 参照）。

pristine-tar を使う場合。

```console
gbp buildpackage --git-pristine-tar --git-export-dir=.. -p/home/hnakamur/bin/gpg-passphrase -S -sa -d --git-dist=focal
```

pristine-tar を使わない場合（私の場合 nginx ＋モジュールのソースのように upstream の tarball が pristine-tar で取り込んだ tarball と異なる場合）。

```console
gbp buildpackage --git-export-dir=.. -p/home/hnakamur/bin/gpg-passphrase -S -sa -d --git-dist=focal
```

なお `-p` オプションについては [git-buildpackageとfreightでパスフレーズをファイルから入力させる · hnakamur's blog](/blog/2017/08/28/use-passphrase-file-in-git-buildpackage-and-freight/) を参照してください。

## sbuild で focal 用の deb をビルド

sbuild は [Ubuntu 18.04 LTSでsbuildをセットアップ · hnakamur's blog](/blog/2018/06/07/setup-sbuild-on-ubuntu-18.04-lts/) の手順でセットアップ済みとします。

focal 用の chroot 環境を作成します。これは一度だけ実行すれば OK です。

```console
mk-sbuild focal
```

sbuild のビルド時には `-d` (`--dist`) オプションで focal を指定します（ [sbuild (1)](https://manpages.ubuntu.com/manpages/focal/en/man1/sbuild.1.html) 参照）。

```console
TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd \
  -d focal dscファイルのパス
```

以下は [hnakamur/openresty-luajit-deb](https://github.com/hnakamur/openresty-luajit-deb) を sbuild でビルドしたときの例です。

```console
TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd \
  -d focal ../luajit_2.1.0~beta3.20200102+dfsg-1ppa1~focal.dsc
```

## PPA での deb のビルド

`dput` コマンドの実行は bionic でも focal でも同じです
（PPA ではディストリビューションは `debian/changelog` のバージョンの行のセミコロンの前で決まるため）。

```console
dput ppa:ユーザ名/PPA名 source_changesのパス
```

以下は [hnakamur/openresty-luajit-deb](https://github.com/hnakamur/openresty-luajit-deb) を PPA でビルドしたときの例です。

```console
dput ppa:hnakamur/openresty-luajit \
  ../luajit_2.1.0~beta3.20200102+dfsg-1ppa1~focal_source.changes
```
