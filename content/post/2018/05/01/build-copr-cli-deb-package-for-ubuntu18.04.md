+++
title="Ubuntu 18.04でcopr-cliのdebパッケージを作ったときのメモ"
date = "2018-05-01T12:35:00+09:00"
lastmod = "2020-05-31T15:33:00+09:00"
tags = ["ubuntu"]
categories = ["blog"]
+++


## はじめに

[Ubuntu16.04でrpmビルド用にmockとcopr-cliをセットアップ](http://localhost:8000/2018/04/21/setup-mock-and-copr-cli-for-building-rpm-on-ubuntu-16.04/) に書いた copr-cli パッケージのビルド手順をサボってメモしてなかったのですが、Ubuntu 18.04 用にビルドする時に手間取ったのでメモしておきます。と言いつつ作業後に思い出しながら書いているので適当です。

## Ubuntu 18.04ではcoprとcopr-cliパッケージを作った

Ubuntu 16.04のときは [copr-cliのPPA](https://launchpad.net/~hnakamur/+archive/ubuntu/copr-cli) で以下の3つのパッケージをビルド・公開していました。

* marshmallow
* copr
* copr-cli

このうち marshmallow というバイナリ形式のシリアライズ用ライブラリは Ubuntu 18.04 には含まれるようになっていました。

```console
$ dpkg -l python3-marshmallow
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                    Version          Architecture     Description
+++-=======================-================-================-====================================================
ii  python3-marshmallow     3.0.0b3-1        all              Lightweight library for converting complex datatypes
```

ということでpython3-marshmallowはUbuntu標準のパッケージを使うことにしてcoprとcopr-cliパッケージを作りました。

## python-coprのdebパッケージ作成

#### coprのソースtarball作成

upstreamのソースtarballを一時的に置くためのディレクトリを作ります。

```console
mkdir ~/copr-cli-work
```

[coprのレポジトリ](https://pagure.io/copr/copr) からソースを取得します。

```console
ghq get https://pagure.io/copr/copr
```

取得したディレクトリに移動してgitのtagを確認します。

```console
cd ~/.ghq/pagure.io/copr/copr
git tag
```

.. code-block:: console

	git checkout python-copr-1.87-1
	cd python
	tar cf - . | gzip -9 > ~/copr-cli-work/python-copr-1.87.tar.gz

#### python-coprのdebパッケージ作成

[hnakamur/copr-deb](https://github.com/hnakamur/copr-deb) のローカルディレクトリに移動して上記のtarballを取り込みます。

```console
cd ~/.ghq/github.com/hnakamur/copr-deb
gbp import-orig --pristine-tar -u 1.87 ~/copr-cli-work/python-copr-1.87.tar.gz
```

あとはいつもの手順でビルドして、ローカルのfreightに追加します。

ローカルのfreightレポジトリはnginxで以下のような設定をして `http://127.0.0.1/freight` でアクセスできるようにしておきます。

```text
location /freight {
    alias /var/cache/freight;
}
```

## copr-cliのdebパッケージ作成

#### ローカルのfreightレポジトリを加えたpbuilderのchroot環境作成

baseのchrootをコピーして変更していきます。

```console
sudo cp /var/cache/pbuilder/{base,with-local-repo}.tar.gz
```

.. code-block:: console

	sudo pbuilder login --basetgz /var/cache/pbuilder/with-local-repo.tar.gz --save-after-login

chroot環境内で以下のようにしてレポジトリを追加します。

```console
apt install -y curl gnupg2
curl http://127.0.0.1/freight/pubkey.gpg | apt-key add -
echo 'deb http://127.0.0.1/freight bionic main' | tee /etc/apt/sources.list.d/my-debs.list
exit
```

[pbuilderのchroot環境にレポジトリを追加する](https://hnakamur.github.io/blog/2017/09/02/add-repositories-to-pbuilder-chroot-images/) の「ビルド時に apt update するための設定」を行ってビルド時にfreightのレポジトリの最新の内容を参照できるようにしておきます。

#### copr-cliのソースtarball作成

```console
cd ~/.ghq/pagure.io/copr/copr
git checkout copr-cli-1.67-1
cd cli
tar cf - . | gzip -9 > ~/copr-cli-work/copr-cli-1.67-1.tar.gZ
```

#### copr-cliのdebパッケージ作成

[hnakamur/copr-cli-deb](https://github.com/hnakamur/copr-cli-deb) のローカルディレクトリに移動して上記で作成したtarballを取り込みます。

```console
cd ~/.ghq/github.com/hnakamur/copr-cli-deb
gbp import-orig --pristine-tar -u 1.67 ~/copr-cli-work/copr-cli-1.67-1.tar.gZ
```

あとはいつもと同様にして debian/changelog の更新とコミット、タグ作成とソースパッケージの作成までを行います。

pbuilderでローカルでdebパッケージをビルドする際に `--basetgz` オプションで上記で作成したchroot環境を指定します。

```console
sudo pbuilder build --basetgz /var/cache/pbuilder/with-freight.tgz ../build-area/copr-cli_1.67-1ppa1.dsc
```

ローカルでのビルドが終わったらローカルのfreightのレポジトリに追加して、そこからインストールして動作確認を行います。

## PPAでcoprとcopr-cliをビルド

まずcoprをPPAでビルドします。

```console
cd ~/.ghq/github.com/hnakamur/copr-deb
dput ppa:hnakamur/copr-cli ../build-area/copr_1.87-1ppa1_source.changes
```

無事ビルドが完了したら、次はcopr-cliをビルドします。

```console
cd ~/.ghq/github.com/hnakamur/copr-cli-deb
dput ppa:hnakamur/copr-cli ../build-area/copr-cli_1.67-1ppa1_source.changes
```

## PPAでビルドしたcopr-cliをインストール

ローカルのfreightからインストールしたパッケージをアンインストールします。

```console
sudo apt remove python3-copr python3-copr-cli
```

PPAからcopr-cliをインストールします。

```console
sudo add-apt-repository ppa:hnakamur/copr-cli
sudo apt-get update
sudo apt install python3-copr-cli
```

## Ubuntu 20.04 LTS では python3 の venv を使うことにした（2020-05-31 追記）

```console
sudo apt update
sudo apt -y install python3-venv
python3 -m venv ~/copr-cli-venv
source ~/copr-cli-venv/bin/activate
pip install wheel
pip install copr-cli
```

あとは [Ubuntu16.04でrpmビルド用にmockとcopr-cliをセットアップ · hnakamur's blog](/blog/2018/04/21/setup-mock-and-copr-cli-for-building-rpm-on-ubuntu-16.04/) に書いた通り、ブラウザで [API for Copr](https://copr.fedorainfracloud.org/api/)  を開き fedora coprアカウントでログインするとAPIトークンのファイルの内容が表示されますので、 それを ~/.config/copr というファイルに保存します。
