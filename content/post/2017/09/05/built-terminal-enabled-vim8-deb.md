+++
title="terminal機能を有効にしたvim8のdebパッケージを作成した"
date = "2017-09-05T22:38:00+09:00"
tags = ["deb", "vim"]
categories = ["blog"]
+++


## はじめに

terminal機能を有効にしたvim8のdebパッケージを作成したのでメモです。

## インストール方法

ビルドしたパッケージは
[vim : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/vim)
で公開しています。

以下の手順でインストール出来ます。

```console
sudo apt install software-properties-common
sudo add-apt-repository ppa:hnakamur/vim
sudo apt update
sudo apt install vim
```

vim が既にインストール済みの場合は `apt upgrade` でアップグレードすればOKです。
もし、他のパッケージはアップグレードせずに vim だけアップグレードしたい場合は以下のようにします。

```console
sudo apt install --only-upgrade vim vim-common vim-runtime vim-tiny xxd
```

この方法は [How to upgrade a single package using apt-get? - Ask Ubuntu](https://askubuntu.com/questions/44122/how-to-upgrade-a-single-package-using-apt-get) で知りました。

## パッケージ作成時のメモ

[zesty の vim パッケージ](https://packages.ubuntu.com/zesty/vim) をベースにして xenial 用に改変しました。

追加の改変内容は以下の通りです。

* debian/rules に `OPTFLAGS+=--enable-terminal` を追加して terminal 機能を有効化
* Launchpad では tty が無くて terminal のテストが失敗するのを回避するため、 TERM 環境変数が空の場合は terminal のテストをスキップ

pbuilder では TERM が空ではないようで上記のパッチを入れても terminal のテストが走るのですがエラーになってしまいます。原因は未調査です。

しかたないので、手元の環境でのビルドは pbuilder ではなく、 LXD コンテナ上で `debuild -us -uc -b` でとりあえず行っています。
