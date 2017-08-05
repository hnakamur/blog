golang 1.9rc1のUbuntu 16.04用debパッケージをビルドした
######################################################

:date: 2017-08-05 10:15
:tags: go, deb
:category: blog
:slug: 08/05/built-golang-1.9rc1-deb-package

はじめに
--------

`Ubuntu · golang/go Wiki <https://github.com/golang/go/wiki/Ubuntu>`_ で紹介されている
`Golang Backports : Simon Eisenmann <https://launchpad.net/~longsleep/+archive/ubuntu/golang-backports>`_ を改変してgo 1.9rc1のUbuntu 16.04用debパッケージをビルドしたのでメモです。

`golang 1.9 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.9>`_ というPPAで配布しています。

この記事の手順は `git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順 <https://hnakamur.github.io/blog/2017/07/05/how-to-build-deb-with-git-buildpackage/>`_ で書いたセットアップが済んでいることが前提です。

今回ビルドしたdebのインストール手順
-----------------------------------

今回ビルドしたdebパッケージのインストール手順は以下の通りです。

.. code-block:: console

	sudo apt update
	sudo apt install software-properties-common
	sudo add-apt-repository ppa:hnakamur/golang-1.9
	sudo apt update
	sudo apt install golang-go

LXDのコンテナを新規に作って試す場合の手順も書いておきます。以下ではコンテナ名を :code:`go19` としていますが適宜変更してください。

.. code-block:: console

	lxc launch images:ubuntu/xenial go19
	lxc exec go19 bash
	apt update
	apt install software-properties-common
	add-apt-repository ppa:hnakamur/golang-1.9
	apt update
	apt install golang-go

goのdebパッケージの作成手順メモ
-------------------------------

作成と言っても一からではなくて、 Simon Eisenmann (LaunchPadのアカウントID: longsleep) さんのdebパッケージのソースを取って来て、オリジンのソースを入れ替えて適宜書き換えるだけです。

Simon さんのdebパッケージのソースをダウンロード
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Packages in “Golang Backports” : Golang Backports : Simon Eisenmann <https://launchpad.net/~longsleep/+archive/ubuntu/golang-backports/+packages>`_ でパッケージ名のリストを確認すると、以下の3つのパッケージがあります。

* golang-1.8
* golang-1.8-race-detector-runtime
* golang-defaults

golang-1.8 のリンクをクリックして展開すると複数のパッケージファイルが並んでいますが、そのうち
golang-1.8-go というパッケージファイルをインストールすると /usr/lib/go-1.8/ 以下に /usr/lib/go-1.8/bin/go のように配置されるようになっています。

同様に golang-defaults のリンクをクリックして展開すると、 golang-go というパッケージファイルがあり、これをインストールすると :code:`/usr/bin/go -> ../lib/go-1.8/bin/go` というシンボリックリンクなどが作られるようになっています。

golang-1.8-race-detector-runtime はよくわかってないので今回はスキップします。

以下のコマンドを実行して golang-1.8 と golang-defaults のソースパッケージをダウンロードします。
ここでは :code:`~/longsleep-go-deb` という作業ディレクトリを作成していますが、適宜変更してください。

.. code-block:: console

	sudo add-apt-repository ppa:longsleep/golang-backports
	sudo apt-get update
	mkdir ~/longsleep-go-deb
	cd !$
	apt source golang-1.8-go golang-defaults

golang-1.8のパッケージを改変してgolang-1.9のパッケージを作成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

最終結果は https://github.com/hnakamur/golang-deb で公開しています。
以下の手順は何回か試行錯誤した結果なのですが、上記のレポジトリと多少ずれているかもしれません。もう一度一からやり直して確認するの面倒なので、そのまま書いてしまいます。

以下ではレポジトリの作業ディレクトリを :code:`~/.ghq/github.com/hnakamur/golang-deb` として説明します。適宜変更してください。

まず、 :code:`.dsc` ファイルをインポートして、レポジトリを新規作成します。
ディレクトリ名を :code:`golang` から :code:`golang-deb` に変更して、そこに移動します。

.. code-block:: console

	cd ~/.ghq/github.com/hnakamur
	gbp import-dsc --pristine-tar \
		--debian-branch=ubuntu-1.8 --upstream-branch=upstream-1.8 \
		~/longsleep-go-deb/golang-1.8/golang-1.8_1.8.3-2ubuntu1~longsleep1-xenial.dsc
	mv golang golang-deb
	cd !$

ブランチを確認します。

.. code-block:: console

    $ git branch
    * master
      pristine-tar
      ubuntu-1.8
      upstream-1.8

タグを確認します。

.. code-block:: console

    $ git tag
    debian/1.8.3-2ubuntu1_longsleep1-xenial
    upstream/1.8.3-2ubuntu1_longsleep1

このレポジトリには :code:`debian/gbp.conf.in` というファイルがあって、gbp (git-buildpackage) 用のブランチやタグの形式が記載されています。

アップストリームのブランチは :code:`upstream-X.Y` で、debパッケージのブランチは :code:`ubuntu-X.Y` だということがわかります。 :code:`X.Y` の部分は :code:`debian/changelog` ファイルからバージョンを読み取って展開されるようになっています。

.. code-block:: console

    $ cat debian/gbp.conf.in
    [DEFAULT]
    debian-branch = ubuntu-X.Y
    debian-tag = debian/%(version)s
    upstream-branch = upstream-X.Y
    upstream-tag = upstream/%(version)s
    pristine-tar = True

    [git-dch]
    meta = 1

試行錯誤していた時に、 :code:`[git-dch]` というセクション名は古いので :code:`[dch]` にせよという主旨の警告が出ました。そこで以下のコマンドを実行して変更しました。

.. code-block:: console

    sed -i -e 's/^\[git-dch\]/[dch]/' debian/gbp.conf.in

さらに以下のコマンドを実行して :code:`debian/gbp.conf.in` から :code:`debian/gbp.conf` を生成して上書きします。

.. code-block:: console

    debian/rules gencontrol

変更した :code:`debian/gbp.conf.in` と :code:`debian/gbp.conf` をコミットします。

.. code-block:: console

    git commit -m 'Rename git-dch to dch in debian.gbp.conf.in' debian/gbp.conf.in debian/gbp.conf

:code:`ubuntu-1.8` ブランチにも上記の変更をマージします。

.. code-block:: console

    git checkout ubuntu-1.8
    git merge --ff master

:code:`upstream-1.8` ブランチから :code:`upstream-1.9` ブランチを、
:code:`ubuntu-1.8` ブランチから :code:`ubuntu-1.9` ブランチを作成し、
:code:`ubuntu-1.9` ブランチに切り替えます。

.. code-block:: console

    git branch upstream-1.9 upstream-1.8
    git checkout -b ubuntu-1.9 ubuntu-1.8

以下のコマンドを実行して :code:`debian/changelog` にエントリを追加します。

.. code-block:: console

    gbp dch -R --debian-branch ubuntu-1.9

エディタ (私の場合は vim) が起動しますので、先頭に追加されたエントリを以下のように編集します。

.. code-block:: text

    golang-1.9 (1.9~rc1-1ubuntu1~hnakamur1-xenial) xenial; urgency=medium

      * New upstream release.

     -- Hiroaki Nakamura <hnakamur@gmail.com>  Sat, 29 Jul 2017 00:38:32 +0900

以下のコマンドを実行して、ソースパッケージ内のgoのバージョンに依存したファイルを再生成します。

.. code-block:: console

    debian/rules gencontrol

更新したファイルをコミットします。

.. code-block:: console

    git add .
    git commit -m 'Change control file to golang-1.9'

次に go 1.9rc1 のアップストリームのソースをインポートします。

.. code-block:: console

    $ gbp import-orig --no-merge --no-interactive \
       --debian-branch=ubuntu-1.9 --upstream-branch=upstream-1.9 \
       --upstream-version=1.9~rc1 ~/go1.9rc1.src.tar.gz
    gbp:info: Importing '/home/hnakamur/go1.9rc1.src.tar.gz' to branch 'upstream-1.9'...
    gbp:info: Source package is golang-1.9
    gbp:info: Upstream version is 1.9~rc1
    gbp:info: Successfully imported version 1.9~rc1 of /home/hnakamur/go1.9rc1.src.tar.gz

:code:`ubuntu-1.9` ブランチに切り替えて :code:`upstream-1.9` ブランチの変更をマージします。

.. code-block:: console

    git checkout ubuntu-1.9
    git merge --no-ff upstream-1.9

今回作成するdebパッケージのバージョン :code:`1.9~rc1-1ubuntu1~hnakamur1-xenial` の :code:`~` を :code:`_` に置き換えたタグを打っておきます。

.. code-block:: console

    git tag upstream/1.9_rc1-1ubuntu1_hnakamur1 upstream-1.9

さらに :code:`master` ブランチに :code:`upstream-1.9` ブランチの内容をマージしておきました。

.. code-block:: console

    git checkout master
    git merge ubuntu-1.9

以下のコマンドでソースパッケージをビルドします。

.. code-block:: console

    gbp buildpackage --git-pristine-tar-commit --git-export-dir=../build-area --git-debian-branch=ubuntu-1.9 -S -sa

以下のコマンドでバイナリパッケージをビルドします。

.. code-block:: console

    sudo pbuilder build ../build-area/golang-1.9_1.9~rc1-1ubuntu1~hnakamur1-xenial.dsc

:code:`/var/cache/pbuilder/result/` に生成されたdebファイルを、LXDの新規コンテナにコピー、インストールし、動作確認しました。動作確認と言っても :code:`/usr/lib/go-1.9/bin/go version` を実行して出力を確認しただけです。

golang-1.9のPPAを作成してソースパッケージをアップロード
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Launchpad <https://launchpad.net/>`_ にログインして自分のページに移動して :code:`golang-1.9` というPPAを作成しました。

すると Uploading packages to this PPA というところに
:code:`dput ppa:hnakamur/golang-1.9 <source.changes>` 
と書かれていますので、以下のコマンドを実行してソースパッケージをアップロードしました。

.. code-block:: console

    dput ppa:hnakamur/golang-1.9 ../build-area/golang-1.9_1.9~rc1-1ubuntu1~hnakamur1-xenial_source.changes

しばらく待ってビルド結果を見ると amd64 は通ったのですが i386 はビルドエラーになっていました。
自分で使うのは amd64 だけなので 
`nginx+luaのカスタムdebパッケージを作ってみた <https://hnakamur.github.io/blog/2017/07/18/created-nginx-custom-deb-package/>`_
の「PPAでビルドするアーキテクチャの変更」の手順で i386 は以降のビルド対象から外しました。

go 1.8用のgolang-defaultsパッケージgo 1.9用に改変
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

まず、 :code:`.dsc` ファイルをインポートして自分のレポジトリを作ります。

.. code-block:: console

    cd ~/.ghq/github.com/hnakamur
    gbp import-dsc --pristine-tar ~/longsleep-go-deb/golang-defaults_1.8~1ubuntu2~xenial.dsc
    mv golang-defaults golang-defaults-deb
    cd !$

新しいリリースを :code:`gbp dch -R` で作ろうとしたらタグが無くてエラーになったので、直接 :code:`dch` を使うようにしました。

.. code-block:: console

    dch -R

前のエントリ

.. code-block:: text

    golang-defaults (2:1.8~1ubuntu2~xenial) xenial; urgency=medium

      * Backport to 16.04.
      * Use Golang 1.8.

     -- Simon Eisenmann <simon@longsleep.org>  Tue, 03 Jan 2017 16:49:41 +0100

を参考にして、先頭に追加されたエントリを以下のように編集しました。

.. code-block:: text

    golang-defaults (2:1.9~1ubuntu1~hnakamur1) xenial; urgency=medium

      * Use Golang 1.9.

     -- Hiroaki Nakamura <hnakamur@gmail.com>  Sat, 05 Aug 2017 09:38:34 +0900

バージョンに対応したタグを打ちます。

.. code-block:: console

    git tag debian/1.9_1ubuntu1_hnakamur1

ソースパッケージをビルドします。

.. code-block:: console

    gbp buildpackage --git-export-dir=../build-area -S -sa

バイナリパッケージをビルドします。

.. code-block:: console

    sudo pbuilder build ../build-area/golang-defaults_1.9~1ubuntu1~hnakamur1.dsc

生成されたバイナリパッケージの中身を確認します。

.. code-block:: console

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


LXDコンテナにパッケージをコピーして動作確認した後、
PPAにソースパッケージをアップロードしてビルドしました。

.. code-block:: console

    dput ppa:hnakamur/golang-1.9 ../build-area/golang-defaults_1.9~1ubuntu1~hnakamur1_source.changes

おわりに
--------

使い方は先頭の「今回ビルドしたdebのインストール手順」の項に書いた通りです。
今後、go 1.9.xの新しいリリース候補や正式版が出たら、debパッケージもすぐ更新するつもりです。

一方で dh-make-golang パッケージなどは Simon さんのパッケージに依存していますので、
正式版が出たら Simon さんにも更新をお願いしようと思います。
以前 1.8.3 を Simon さんにメールでお願いしたら数日で作ってくれました。

さらに、goで書かれたコマンドやサーバのうち自分で使うものはdebパッケージを作っていきたいと
考えています。というより、それがしたいからgoのパッケージを作ったわけなので。
