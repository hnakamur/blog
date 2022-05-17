---
title: add-apt-repositoryを使わずにPPAをapt-lineに追加する方法
date: 2017-09-02T11:47:00+09:00
tags: ["deb", "apt"]
categories: ["blog"]
lastmod: 2022-05-17T21:50:00+09:00
---

## 2022-05-17 追記：代替スクリプトを書きました

https://github.com/hnakamur/setup-my-ubuntu-desktop/blob/main/my-apt-add-repository

事前に curl, gpg, coreutils パッケージがインストールされている必要があります。

使用例

```
my-apt-add-repository ppa:hnakamur/nginx
```

GPG公開鍵の登録は [第675回　apt-keyはなぜ廃止予定となったのか：Ubuntu Weekly Recipe｜gihyo.jp … 技術評論社](https://gihyo.jp/admin/serial/01/ubuntu-recipe/0675) で解説されている手順に沿っています。

## はじめに

PPAのページにはPPAを追加するには `add-apt-respository` コマンドを使うように書かれています。

例えば gcc-7 などを配布しているPPA
[Toolchain test builds : “PPA for Ubuntu Toolchain Uploads (restricted)” team](https://launchpad.net/~ubuntu-toolchain-r/+archive/ubuntu/test)
の Adding this PPA to your system には以下のように書かれています。

```console
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
```

ですが、LXDのコンテナの Ubuntu Xenial のイメージなどでは add-apt-repository が入っていないので、 `apt install software-properties-common` でインストールする必要があります。

わざわざこれだけのために入れるのも面倒ですし、ディスクも消費するので、 add-apt-repository を使わない方法を調べました。

## add-apt-repositoryを使わないPPAの追加手順

以下の2ステップで追加します。

1. PPAの公開鍵の追加
2. apt-lineの追加

### PPAの公開鍵の追加

公開鍵のIDを調べて、以下のコマンドでPPAの公開鍵を追加します。以下は公開鍵のIDが BA9EF27F の場合です。

```console
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv BA9EF27F
```

`man apt-key` で確認したところ `adv` サブコマンドは引数を `gpg` に渡すようになっています。

この方法は [linux - sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10 command returns error - Super User](https://superuser.com/questions/620765/sudo-apt-key-adv-keyserver-keyserver-ubuntu-com-recv-7f0ceb10-command-return/621258#621258) で見つけました。コメントでポート80を明示的に指定する必要があるとありましたが試してみると不要でした。

公開鍵のIDは以下の手順で調べられます。

1. PPA のページの "Adding this PPA to your system" セクションにある "Technical details about this PPA" というリンクをクリック
2. 展開されて表示された "Signing Key:" の下のリンクをクリック
3. "Search results for ..." のページで検索結果の keyID の部分をコピー

上記の例のPPAだと以下のように表示されて、 keyID は BA9EF27F となります。

```text
Search results for '0x60c317803a41ba51845e371a1e9377a2ba9ef27f'

Type bits/keyID     Date       User ID
pub  1024R/BA9EF27F 2009-10-22 Launchpad Toolchain builds
         Fingerprint=60C3 1780 3A41 BA51 845E  371A 1E93 77A2 BA9E F27F 
```

正しく追加できたかは `sudo apt-key list` で確認できます。

```text
root@addrepomanual:~# apt-key list
/etc/apt/trusted.gpg
--------------------
pub   1024D/437D05B5 2004-09-12
uid                  Ubuntu Archive Automatic Signing Key <ftpmaster@ubuntu.com>
sub   2048g/79164387 2004-09-12

pub   4096R/C0B21F32 2012-05-11
uid                  Ubuntu Archive Automatic Signing Key (2012) <ftpmaster@ubuntu.com>

pub   4096R/EFE21092 2012-05-11
uid                  Ubuntu CD Image Automatic Signing Key (2012) <cdimage@ubuntu.com>

pub   1024D/FBB75451 2004-12-30
uid                  Ubuntu CD Image Automatic Signing Key <cdimage@ubuntu.com>

pub   1024R/BA9EF27F 2009-10-22
uid                  Launchpad Toolchain builds
```

BA9EF27F の鍵が追加されていることがわかります。

ちなみに別環境で `add-apt-repository ppa:ubuntu-toolchain-r/test` でPPAを追加した場合は `apt-key list` の結果は以下のようになりました。
PPA用に `/etc/apt/trusted.gpg.d/ubuntu-toolchain-r_ubuntu_test.gpg` という別のファイルが作られてそちらに鍵がインポートされています。

```text
root@addrepo:~# sudo apt-key list
/etc/apt/trusted.gpg
--------------------
pub   1024D/437D05B5 2004-09-12
uid                  Ubuntu Archive Automatic Signing Key <ftpmaster@ubuntu.com>
sub   2048g/79164387 2004-09-12

pub   4096R/C0B21F32 2012-05-11
uid                  Ubuntu Archive Automatic Signing Key (2012) <ftpmaster@ubuntu.com>

pub   4096R/EFE21092 2012-05-11
uid                  Ubuntu CD Image Automatic Signing Key (2012) <cdimage@ubuntu.com>

pub   1024D/FBB75451 2004-12-30
uid                  Ubuntu CD Image Automatic Signing Key <cdimage@ubuntu.com>

/etc/apt/trusted.gpg.d/ubuntu-toolchain-r_ubuntu_test.gpg
---------------------------------------------------------
pub   1024R/BA9EF27F 2009-10-22
uid                  Launchpad Toolchain builds
```

手動で同じ構成にするのは以下のようにすれば出来ます。

```console
gpg --no-default-keyring --keyring /etc/apt/trusted.gpg.d/ubuntu-toolchain-r_ubuntu_test.gpg --fingerprint
curl -sS 'http://keyserver.ubuntu.com:11371/pks/lookup?op=get&search=0x1E9377A2BA9EF27F' \
        | apt-key --keyring /etc/apt/trusted.gpg.d/ubuntu-toolchain-r_ubuntu_test.gpg add -
```

gpg でデフォルトと別のkeyringファイルを作る方法は
[gnupg - How to create additional gpg keyring - Super User](https://superuser.com/questions/399938/how-to-create-additional-gpg-keyring/991139#991139) で見つけました。

curl に指定しているURLは以下の手順で調べられます。

1. PPA のページの "Adding this PPA to your system" セクションにある "Technical details about this PPA" というリンクをクリック
2. 展開されて表示された "Signing Key:" の下のリンクをクリック
3. "Search results for ..." のページで検索結果の keyID のリンクのURLをコピー

このリンク先のページは公開鍵を含むHTMLになっていますが、 `apt-key add` サブコマンドは公開鍵の前後は無視して処理してくれました。

ただし、この手順にはcurlが必要で、LXDのxenialイメージには含まれていないので `apt install curl` でインストールが必要です。なので手軽に実行するには冒頭の手順のほうが良いです。

ちなみに gpg で keyring を作っておいて
`sudo apt-key adv --keyserver keyserver.ubuntu.com --keyring /etc/apt/trusted.gpg.d/ubuntu-toolchain-r_ubuntu_test.gpg --recv BA9EF27F` というのも試してみたのですが、 /etc/apt/trusted.gpg のほうにインポートされてしまいました。

### apt-lineの追加

これは `/etc/apt/sources.list` に追記するか `/etc/apt/sources.list.d/` に `.list` という拡張子を持つファイルを作ればOKです。後者のほうが管理しやすいと思います。

例えば ubuntu-toolchain-r/test の場合は以下のようにします。

```console
echo 'deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main' \
         | sudo tee /etc/apt/sources.list.d/ubuntu-toolchain-r-ubuntu-test-xenial.list
```

追加する内容は、 PPA のページの "Adding this PPA to your system" セクションにある "Technical details about this PPA" を展開し、 "Display sources.list entries for:" の右のドロップダウンリストでお使いのディストリビューションを選べば表示されます。

今回の例だと以下の内容です。

```console
deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main 
deb-src http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main 
```

deb-src の行は `apt source パッケージ名` でdebのソースパッケージをダウンロードするときに必要ですが、それ以外では不要なので上記では省略しています。

あとは `apt update` すれば `apt install パッケージ名` で必要なパッケージをインストール可能になります。
