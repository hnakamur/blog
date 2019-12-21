+++
title="VagrantでUbuntu 18.04 LTSとLXDをインストールする手順"
date = "2018-07-05T15:40:00+09:00"
tags = ["vagrant", "ubuntu", "lxd"]
categories = ["blog"]
+++


# はじめに

私自身は職場でも自宅でも Ubuntu MATE 18.04 LTS を使っていてVagrantはもう使っていません。
ですが職場の同僚が macOS を使っていてLXDの環境をセットアップするのに少々手間どったのでメモしておきます。

VirtualBoxとVagrantはインストール済みという前提で、それ以降の手順です。

# Ubuntu 18.04 LTSのボックス追加

[Vagrant box ubuntu/bionic64 - Vagrant Cloud](https://app.vagrantup.com/ubuntu/boxes/bionic64)
にUbuntu 18.04 LTSのボックスがあったので、これを使いました。

が、Vagrantのバージョンが1.9.6と古いせいか (2018-07-05時点での最新版は2.1.2)、上記のページのようにVagrantfileを作成して `vagrant up` を実行しても404 Not Foundのエラーが出てしまいました。

作成済みのVMであれば
[vagrant box の 404 エラーに対処した - @znz blog](https://blog.n-z.jp/blog/2018-03-09-vagrant-box-404.html)
の手順で対応可能なようですが、新規にVMを作成する場合はどうすれば良いのかと、さらに検索してみると
[How to Download Vagrant Box Manually](https://gist.github.com/firmanelhakim/77b6ee7fb50883155eeefc9e0dc10b9b) というページを見つけました。

これを参考にして
[Vagrant box ubuntu/bionic64 - Vagrant Cloud](https://app.vagrantup.com/ubuntu/boxes/bionic64)
のこの記事執筆時点での最新版は v20180630.0.0 だったので以下のようにしてボックスのイメージをダウンロードしました。

```console
curl -Lo ubuntu-18.04.box https://app.vagrantup.com/ubuntu/boxes/bionic64/versions/20180630.0.0/providers/virtualbox.box
```

後は以下のようにしてボックスを登録します。

```console
vagrant box add ubuntu/bionic64 ubuntu-18.04.box
```

これで無事 `vagrant up` でVMが作れるようになりました。

# LXDのセットアップ

以下の手順は `vagrant ssh` してVMにログインした状態で実行してください。

[Snap パッケージ (ArchLinux, Debian, Fedora, OpenSUSE, Ubuntu)](https://linuxcontainers.org/ja/lxd/getting-started-cli/#snap-archlinux-debian-fedora-opensuse-ubuntu)
の手順でsnapパッケージのLXDをインストールします。

```console
sudo snap install lxd
```

[初期設定](https://linuxcontainers.org/ja/lxd/getting-started-cli/#_5)
の手順でLXDの初期化を行います。

```console
sudo lxd init
```

いくつか質問されますが、ほぼデフォルトで良いです。ストレージエンジンは開発環境なのでシンプルな構成で十分ということで `dir` にしました。

[アクセスコントール](https://linuxcontainers.org/ja/lxd/getting-started-cli/#_6)
の説明に従って、今のユーザ `vagrant` を `lxd` グループに追加します。

```console
sudo usermod -a -G lxd $USER
```

`exit` で一旦 VM から抜けて、再度 `vagrant ssh` でVMに入ればlxdが使える状態になります。


以下のコマンドを実行してコンテナ一覧を表示し、空の一覧が表示されればOKです。

```console
lxc list
