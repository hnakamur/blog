+++
title="Ubuntu16.04でrpmビルド用にmockとcopr-cliをセットアップ"
date = "2018-04-21T21:00:00+09:00"
tags = ["ubuntu", "rpm"]
categories = ["blog"]
+++


## はじめに

Ubuntu 16.04で [mock](https://github.com/rpm-software-management/mock) でローカルでrpmをビルドするための環境構築の手順メモです。

[Copr Build Service](https://developer.fedoraproject.org/deployment/copr/about.html) でrpmをビルドする際に、ビルドが通ることを事前に確認するために mock を使ってローカルでrpmをビルドするようにしています。

mockはchrootを使っているのですがLXDでcentos7コンテナを作ってそこでmockを実行するとエラーでうまく動かなかったので、以前はdockerでcentos7のコンテナを作ってそこでmockを実行していました。

その後、ubuntuにもmockコマンドのパッケージがあることを知り、そちらを使うようになりました。で、今回別のサーバで再度環境を構築する必要が出てきたので、この機会にメモしておきます。

また Copr Build Service で rpm をビルドするときに [copr-cli](https://developer.fedoraproject.org/deployment/copr/copr-cli.html) を使っていたので、こちらのセットアップ手順も合わせて書いておきます。

## mockのセットアップ

以下のコマンドで mock をインストールします。

```console
sudo apt install mock
```

[hnakamur/my-mock-configs-for-building-rpm-on-ubuntu](https://github.com/hnakamur/my-mock-configs-for-building-rpm-on-ubuntu) にあるchroot環境の設定ファイルを `/etc/mock/` にコピーします。

```console
git clone https://github.com/hnakamur/my-mock-configs-for-building-rpm-on-ubuntu
sudo cp ./my-mock-configs-for-building-rpm-on-ubuntu/*.cfg /etc/mock/
```

#### (参考) mockのchroot設定にレポジトリ追加

脱線してmockのchroot設定にレポジトリ追加する方法を説明しておきます。
例えば `/etc/mock/epel-7-x86_64-with-luajit.cfg` は
`/etc/mock/epel-7-x86_64.cfg` をコピーして以下のようにレポジトリ設定を追加しています。

```console
$ diff -u /etc/mock/epel-7-x86_64{,-with-luajit}.cfg
--- /etc/mock/epel-7-x86_64.cfg 2018-04-20 21:05:09.303104170 +0900
+++ /etc/mock/epel-7-x86_64-with-luajit.cfg     2018-04-20 20:50:33.082617365 +0900
@@ -68,4 +68,11 @@
 mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=epel-debug-7&arch=x86_64
 failovermethod=priority
 enabled=0
+
+[hnakamur-luajit]
+name=Copr repo for luajit owned by hnakamur
+baseurl=https://copr-be.cloud.fedoraproject.org/results/hnakamur/luajit/epel-7-$basearch/
+enabled=1
+gpgcheck=0
+
 """
```

#### CentOS 7とEPEL 7のgpg鍵ファイルインストール

ウェブから鍵を取得する場合は以下の場所を参照します。

* [CentOS GPG Keys](https://www.centos.org/keys/) のCentOS 7 Signing Key

    * `/usr/share/distribution-gpg-keys/centos/RPM-GPG-KEY-CentOS-7` に設置。

* [Package Signing Keys](https://getfedora.org/en/keys/) のEPEL 7

    * `/usr/share/distribution-gpg-keys/epel/RPM-GPG-KEY-EPEL-7` に設置。

```console
sudo mkdir -p /usr/share/distribution-gpg-keys/{centos,epel}
sudo curl -L -o /usr/share/distribution-gpg-keys/centos/RPM-GPG-KEY-CentOS-7 \
  https://www.centos.org/keys/RPM-GPG-KEY-CentOS-7
sudo curl -L -o /usr/share/distribution-gpg-keys/epel/RPM-GPG-KEY-EPEL-7 \
  https://getfedora.org/static/352C64E5.txt
```

と書きましたが、実際はLXDのCentOS7コンテナからコピーしたファイルを設置しました。
[How to list, import and remove archive signing keys on CentOS 7 - LinuxConfig.org](https://linuxconfig.org/how-to-list-import-and-remove-archive-signing-keys-on-centos-7) で説明されていますが
`/etc/pki/rpm-gpg/` に鍵ファイルがありました。

```console
# ls /etc/pki/rpm-gpg/
RPM-GPG-KEY-CentOS-7  RPM-GPG-KEY-CentOS-Debug-7  RPM-GPG-KEY-CentOS-Testing-7
```

#### mockグループを作成し自ユーザをmockグループに追加

ubuntuのmockパッケージをインストールしてもmockグループは作られないので手動で作る必要がありました。

```console
sudo groupadd -r mock
```

その後、自ユーザをmockグループに追加します。

```console
sudo usermod -a -G mock $USER
```

## copr-cliのセットアップ

copr-cli は自作のパッケージをPPAに置いてあるので、そこからインストールします。

```console
sudo add-apt-repository ppa:hnakamur/copr-cli
sudo apt update
sudo apt install python3-copr-cli
```

ブラウザで [API for Copr](https://copr.fedorainfracloud.org/api/) を開き
fedora coprアカウントでログインするとAPIトークンのファイルの内容が表示されますので、
それを `~/.config/copr` というファイルに保存します。

## 実際のビルドの例

* [私のnginxのカスタムrpmとdebをビルドする手順](/blog/2018/04/05/building-my-custom-nginx-rpm-and-deb/)
* [私のgoのrpmとdebをビルドする手順](/blog/2018/04/05/building-my-golang-rpm-and-deb/)
