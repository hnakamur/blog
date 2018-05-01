Ubuntu 18.04でcopr-cliのdebパッケージを作ったときのメモ
#######################################################

:date: 2018-05-01 12:35
:tags: ubuntu
:category: blog
:slug: 2018/05/01/build-copr-cli-deb-pacakge-for-ubuntu18.04

はじめに
--------

`Ubuntu16.04でrpmビルド用にmockとcopr-cliをセットアップ <http://localhost:8000/2018/04/21/setup-mock-and-copr-cli-for-building-rpm-on-ubuntu-16.04/>`_ に書いた copr-cli パッケージのビルド手順をサボってメモしてなかったのですが、Ubuntu 18.04 用にビルドする時に手間取ったのでメモしておきます。と言いつつ作業後に思い出しながら書いているので適当です。

Ubuntu 18.04ではcoprとcopr-cliパッケージを作った
------------------------------------------------

Ubuntu 16.04のときは `copr-cliのPPA <https://launchpad.net/~hnakamur/+archive/ubuntu/copr-cli>`_ で以下の3つのパッケージをビルド・公開していました。

* marshmallow
* copr
* copr-cli

このうち marshmallow というバイナリ形式のシリアライズ用ライブラリは Ubuntu 18.04 には含まれるようになっていました。

.. code-block:: console

	$ dpkg -l python3-marshmallow
	Desired=Unknown/Install/Remove/Purge/Hold
	| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
	|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
	||/ Name                    Version          Architecture     Description
	+++-=======================-================-================-====================================================
	ii  python3-marshmallow     3.0.0b3-1        all              Lightweight library for converting complex datatypes

ということでpython3-marshmallowはUbuntu標準のパッケージを使うことにしてcoprとcopr-cliパッケージを作りました。

python-coprのdebパッケージ作成
------------------------------

coprのソースtarball作成
+++++++++++++++++++++++

upstreamのソースtarballを一時的に置くためのディレクトリを作ります。

.. code-block:: console

	mkdir ~/copr-cli-work

`coprのレポジトリ <https://pagure.io/copr/copr>`_ からソースを取得します。

.. code-block:: console

	ghq get https://pagure.io/copr/copr

取得したディレクトリに移動してgitのtagを確認します。

.. code-block:: console

	cd ~/.ghq/pagure.io/copr/copr
	git tag

.. code-block:: console

	git checkout python-copr-1.87-1
	cd python
	tar cf - . | gzip -9 > ~/copr-cli-work/python-copr-1.87.tar.gz

python-coprのdebパッケージ作成
++++++++++++++++++++++++++++++

`hnakamur/copr-deb <https://github.com/hnakamur/copr-deb>`_ のローカルディレクトリに移動して上記のtarballを取り込みます。

.. code-block:: console

	cd ~/.ghq/github.com/hnakamur/copr-deb
	gbp import-orig --pristine-tar -u 1.87 ~/copr-cli-work/python-copr-1.87.tar.gz

あとはいつもの手順でビルドして、ローカルのfreightに追加します。

ローカルのfreightレポジトリはnginxで以下のような設定をして :code:`http://127.0.0.1/freight` でアクセスできるようにしておきます。

.. code-block:: text

    location /freight {
        alias /var/cache/freight;
    }

copr-cliのdebパッケージ作成
---------------------------

ローカルのfreightレポジトリを加えたpbuilderのchroot環境作成
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

baseのchrootをコピーして変更していきます。

.. code-block:: console

	sudo cp /var/cache/pbuilder/{base,with-local-repo}.tar.gz

.. code-block:: console

	sudo pbuilder login --basetgz /var/cache/pbuilder/with-local-repo.tar.gz --save-after-login

chroot環境内で以下のようにしてレポジトリを追加します。

.. code-block:: console

	apt install -y curl gnupg2
	curl http://127.0.0.1/freight/pubkey.gpg | apt-key add -
	echo 'deb http://127.0.0.1/freight bionic main' | tee /etc/apt/sources.list.d/my-debs.list
	exit

`pbuilderのchroot環境にレポジトリを追加する <https://hnakamur.github.io/blog/2017/09/02/add-repositories-to-pbuilder-chroot-images/>`_ の「ビルド時に apt update するための設定」を行ってビルド時にfreightのレポジトリの最新の内容を参照できるようにしておきます。

copr-cliのソースtarball作成
+++++++++++++++++++++++++++

.. code-block:: console

	cd ~/.ghq/pagure.io/copr/copr
	git checkout copr-cli-1.67-1
	cd cli
	tar cf - . | gzip -9 > ~/copr-cli-work/copr-cli-1.67-1.tar.gZ

copr-cliのdebパッケージ作成
+++++++++++++++++++++++++++

`hnakamur/copr-cli-deb <https://github.com/hnakamur/copr-cli-deb>`_ のローカルディレクトリに移動して上記で作成したtarballを取り込みます。

.. code-block:: console

	cd ~/.ghq/github.com/hnakamur/copr-cli-deb
	gbp import-orig --pristine-tar -u 1.67 ~/copr-cli-work/copr-cli-1.67-1.tar.gZ

あとはいつもと同様にして debian/changelog の更新とコミット、タグ作成とソースパッケージの作成までを行います。

pbuilderでローカルでdebパッケージをビルドする際に :code:`--basetgz` オプションで上記で作成したchroot環境を指定します。

.. code-block:: console

	sudo pbuilder build --basetgz /var/cache/pbuilder/with-freight.tgz ../build-area/copr-cli_1.67-1ppa1.dsc

ローカルでのビルドが終わったらローカルのfreightのレポジトリに追加して、そこからインストールして動作確認を行います。

PPAでcoprとcopr-cliをビルド
---------------------------

まずcoprをPPAでビルドします。

.. code-block:: console

	cd ~/.ghq/github.com/hnakamur/copr-deb
	dput ppa:hnakamur/copr-cli ../build-area/copr_1.87-1ppa1_source.changes

無事ビルドが完了したら、次はcopr-cliをビルドします。

.. code-block:: console

	cd ~/.ghq/github.com/hnakamur/copr-cli-deb
	dput ppa:hnakamur/copr-cli ../build-area/copr-cli_1.67-1ppa1_source.changes

PPAでビルドしたcopr-cliをインストール
-------------------------------------

ローカルのfreightからインストールしたパッケージをアンインストールします。

.. code-block:: console

	sudo apt remove python3-copr python3-copr-cli

PPAからcopr-cliをインストールします。

.. code-block:: console

	sudo add-apt-repository ppa:hnakamur/copr-cli
	sudo apt-get update
	sudo apt install python3-copr-cli
