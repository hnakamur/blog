go-carbonのdebパッケージをsbuildとPPAでビルドした
#################################################

:date: 2018-06-15 10:55
:modified: 2018-06-15 16:15
:tags: ubuntu, deb, sbuild, go-carbon
:category: blog
:slug: 2018/06/15/built-go-carbon-deb-using-sbuild-and-ppa

はじめに
========

`lomik/go-carbon: Golang implementation of Graphite/Carbon server with classic architecture: Agent -> Cache -> Persister <https://github.com/lomik/go-carbon>`_
のdebパッケージをsbuildとPPAでビルドしたときのメモです。

成果物は以下に有ります。

* PPA: `go-carbon : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/go-carbon>`_
* debソースレポジトリ: `hnakamur/go-carbon-deb: go-carbon deb package for Ubuntu 18.04 LTS <https://github.com/hnakamur/go-carbon-deb>`_

debianでのgoのパッケージング方針
================================

* `MichaelStapelberg/GoPackaging - Debian Wiki <https://wiki.debian.org/MichaelStapelberg/GoPackaging>`_
* `Debian Go Packaging <https://go-team.pages.debian.net/packaging.html>`_

に書いてあります。

Goのバイナリ実行ファイルを作る場合に依存ライブラリを別パッケージで作る方針になっていますが、現時点では個人的にはこれは賛同できないです。複数のバイナリパッケージがあるときに同じライブラリに依存するけど必要なバージョンが異なるケースがあり得るからです。

現状だとベンダリングとスタティックリンクで個々のバイナリパッケージ単独で完結するほうがお手軽なので、自作のdebパッケージではそうすることにしました。都合の良いことに go-carbon は dep を使ってベンダリングしており、依存ライブラリのソースは全て vendor ディレクトリに含まれています。

dh-golangとdh-make-golangをインストール
=======================================

dh-golang は goのパッケージを作るための dh (debhelper) のアドオンです。
dh-make-golang はgoのパッケージのソースからdebパッケージを作成するのを自動化するツールです。

.. code-block:: console

        sudo apt install dh-golang dh-make-golang

dh-make-golangでdebパッケージのソースのベースを作成
===================================================

dh-make-golang というツールを使えばdebianのgoのパッケージ方針に従ってパッケージを作成してくれるようなのですが、上記のように依存ライブラリの方針が違うので、debパッケージのソースを生成するところだけ使って、そこから先は手で編集することにしました。

.. code-block:: console

        mkdir -p ~/go-carbon-deb-work
        cd !$

:code:`dh-make-golang ビルド対象のgoパッケージ名` でdebパッケージのソースが作成されます。

.. code-block:: console

	$ dh-make-golang github.com/lomik/go-carbon
	2018/06/15 11:33:49 Downloading "github.com/lomik/go-carbon/..."
	2018/06/15 11:33:52 Deleting upstream vendor/ directory, installing remaining dependencies
	2018/06/15 11:35:57 Determining upstream version number
	2018/06/15 11:35:57 Package version is "0.12.0+git20180608.b1e6baf"
	2018/06/15 11:35:57 Determining package type
	2018/06/15 11:35:57 Assuming you are packaging a program (because "github.com/lomik/go-carbon" defines a main package), use -type to override
	2018/06/15 11:35:57 Determining dependencies
	2018/06/15 11:36:02 Build-Dependency "github.com/go-graphite/carbonzipper" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/lomik/stop" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/dgryski/go-expirecache" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/lomik/og-rek" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/dgryski/go-trigram" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/dgryski/httputil" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/go-graphite/go-whisper" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/go-graphite/protocol" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/lomik/zapwriter" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:02 Build-Dependency "github.com/lomik/graphite-pickle" is not yet available in Debian, or has not yet been converted to use XS-Go-Import-Path in debian/control
	2018/06/15 11:36:06
	2018/06/15 11:36:06 Packaging successfully created in /home/hnakamur/go-carbon-deb-work/go-carbon
	2018/06/15 11:36:06
	2018/06/15 11:36:06 Resolve all TODOs in itp-go-carbon.txt, then email it out:
	2018/06/15 11:36:06     sendmail -t < itp-go-carbon.txt
	2018/06/15 11:36:06
	2018/06/15 11:36:06 Resolve all the TODOs in debian/, find them using:
	2018/06/15 11:36:06     grep -r TODO debian
	2018/06/15 11:36:06
	2018/06/15 11:36:06 To build the package, commit the packaging and use gbp buildpackage:
	2018/06/15 11:36:06     git add debian && git commit -a -m 'Initial packaging'
	2018/06/15 11:36:06     gbp buildpackage --git-pbuilder
	2018/06/15 11:36:06
	2018/06/15 11:36:06 To create the packaging git repository on alioth, use:
	2018/06/15 11:36:06     ssh git.debian.org "/git/pkg-go/setup-repository go-carbon 'Packaging for go-carbon'"
	2018/06/15 11:36:06
	2018/06/15 11:36:06 Once you are happy with your packaging, push it to alioth using:
	2018/06/15 11:36:06     git remote set-url origin git+ssh://git.debian.org/git/pkg-go/packages/go-carbon.git
	2018/06/15 11:36:06     gbp push

:code:`~/go-carbon-deb-work/go-carbon` ディレクトリが新たに作られてdebパッケージのソースがそこに生成されています。
上記の出力にあるとおり、go-carbonに含まれるvendorディレクトリは削除されて、依存ライブラリのソースが別途取得されています。

というわけで :code:`debian/*` ファイルだけ頂くことにします。

gbp import-origでgo-carbonのソースをインポート
==============================================


まず今回ビルドする go-carbon の v0.12.0 のソースを取得します。

.. code-block:: console

        mkdir -p ~/go-carbon-deb-work
        cd !$
        curl -LO https://github.com/lomik/go-carbon/archive/v0.12.0.tar.gz

debパッケージ用の作業ディレクトリを作成してそちらに移動しgitレポジトリを作成します。

.. code-block:: console

        mkdir -p ~/.ghq/github.com/hnakamur/go-carbon-deb
        cd !$
        git init

:code:`gbp import-orig` でgo-carbonのソースをインポートします。以下のようにソースパッケージ名を聞かれるので go-carbon と入力します。

.. code-block:: console

        $ gbp import-orig --pristine-tar -u 0.12.0 ~/go-carbon-deb-work/v0.12.0.tar.gz
        What will be the source package name? [] go-carbon

dh-make-golangで生成したdebianディレクトリのファイルをコピー
============================================================

上記で dh-make-golangで生成した :code:`debian/*` ファイルをコピーして、一旦コミットします。

.. code-block:: console

	rsync -a ~/go-carbon-deb-work/go-carbon/debian .
	git add .
	git commit -m "Add debian/* files generated by dh-make-golang"

debianディレクトリのファイルを編集
==================================

以下は主なところだけ説明します。

debian/controlを編集
--------------------

Build-Dependsから依存ライブラリを外します。
また、Maintainerなど他の項目も適宜変更しました。

.. code-block:: diff

	diff --git a/debian/control b/debian/control
	index 486eb87..b5ee819 100644
	--- a/debian/control
	+++ b/debian/control
	@@ -1,397 +1,19 @@
	 Source: go-carbon
	 Section: devel
	 Priority: optional
	-Maintainer: Debian Go Packaging Team <pkg-go-maintainers@lists.alioth.debian.org>
	-Uploaders: Hiroaki Nakamura <hnakamur@gmail.com>
	+Maintainer: Hiroaki Nakamura <hnakamur@gmail.com>
	 Build-Depends: debhelper (>= 10),
			dh-golang,
	-               golang-any,
	-               golang-github-klauspost-compress-dev,
	-               golang-github-nytimes-gziphandler-dev,
	-               golang-github-sevlyar-go-daemon-dev,
	-               golang-github-shopify-sarama-dev,
	-               golang-github-stretchr-testify-dev,
	-               golang-go.uber-zap-dev,
	-               golang-gogoprotobuf-dev,
	-               golang-golang-x-net-dev,
	-               golang-goleveldb-dev,
	-               golang-google-api-dev,
	-               golang-google-cloud-dev,
	-               golang-google-grpc-dev,
	-               golang-toml-dev
	+               golang-any
	…（略） …

debian/go-carbon.dirsを作成
---------------------------

インストール時に作成するディレクトリを指定します。

.. code-block:: text

	/etc/go-carbon
	/var/lib/graphite/whisper
	/var/log/go-carbon

debian/go-carbon.postinstを作成
-------------------------------

インストール後に実行するスクリプトを作成します。

nginx.orgのdebパッケージに含まれる debian/nginx.postinst を参考にしました。そちらではsystemdではないinit.dにも対応していましたが、私は不要なのでsystemd限定にしています。

.. code-block:: sh

	#!/bin/sh
	
	set -e
	
	if [ "$1" != "configure" ]; then
	    exit 0
	fi
	
	# Set permisions on default data directory on installation
	if [ -z "$2" ]; then
	    chown carbon:carbon /var/lib/graphite/whisper
	fi
	
	if [ -f /var/run/go-carbon.pid ] && kill -0 $(cat /var/run/nginx.pid) >/dev/null; then
	    echo "######################################"
	    echo "# Please restart go-carbon manually. #"
	    echo "######################################"
	else
	    invoke-rc.d go-carbon start || true
	fi
	
	#DEBHELPER#
	
	exit 0

:code:`invoke-rc.d` コマンドは今回初めて知ったのですが
`man invoke-rc.d <http://manpages.ubuntu.com/manpages/bionic/en/man8/invoke-rc.d.8.html>`_
のDESCRIPTIONに以下のように書かれているので、debパッケージのスクリプトでサービス起動するときは :code:`systemctl` ではなくこちらを使うのが良いようです。

.. code-block:: text

	All access to the init scripts by Debian packages' maintainer scripts should be done through invoke-rc.d.

また、go-carbonは graceful restart に対応していないので、プロセス起動中にパッケージアップデートする場合はメッセージを表示するだけで再起動はしないようにしました。別途再起動を行う想定です。

debian/go-carbon.postrmを作成
-----------------------------

アンインストール後に実行するスクリプトを作成します。

nginxの :code:`debian/nginx.postrm` ではサービスを止めるようなコマンドも含まれていたのですが、試してみると自分で書かなくても止めてくれたので省きました。

.. code-block:: sh

	#!/bin/sh

	set -e

	case "$1" in
	    purge)
		rm -rf /var/lib/graphite/whisper /var/log/go-carbon
		;;
	    remove|upgrade|failed-upgrade|abort-install|abort-upgrade|disappear)
		;;
	    *)
		echo "postrm called with unknown argument \`$1'" >&2
		exit 1
	esac

	#DEBHELPER#

	exit 0

:code:`apt remove go-carbon` でアンインストールした後
:code:`apt purge go-carbon` を実行すると、whisperファイルとログファイルを消すようにしました。

nginxの :code:`debian/nginx.postrm` では設定ファイルのディレクトリ :code:`/etc/nginx/` も消すように書かれていましたが、試してみるとgo-carbonの設定ファイルのディレクトリ :code:`/etc/go-carbon` は明示的に消すように書かなくても自動で消されたので上記のスクリプトでは省いています。

go-carbonのソースに含まれていたsystemd service定義ファイルを改良
----------------------------------------------------------------

:code:`PIDFile` の項目がなかったので追加しました。
これを書いておくと :code:`systemctl stop go-carbon` でサービスを止めたり、起動中に :code:`apt remove go-carbon` でアンインストールしたときにPIDファイルを自動で消してくれました。

.. code-block:: text

	diff --git a/debian/go-carbon.service b/debian/go-carbon.service
	index 0d933dd..a421bb7 100644
	--- a/debian/go-carbon.service
	+++ b/debian/go-carbon.service
	@@ -6,6 +6,7 @@ After=network.target
	 [Service]
	 Type=forking
	 ExecStart=/usr/bin/go-carbon -config /etc/go-carbon/go-carbon.conf -pidfile /var/run/go-carbon.pid -daemon
	+PIDFile=/var/run/go-carbon.pid
	 ExecReload=/bin/kill -HUP $MAINPID
	 KillSignal=USR2
	 Restart=on-failure
	@@ -15,4 +16,4 @@ LimitNOFILE=55555
	 LimitMEMLOCK=infinity

	 [Install]
	-WantedBy=multi-user.target
	\ No newline at end of file
	+WantedBy=multi-user.target

ビルド手順
==========

他にも :code:`debian/changelog` などを編集、コミット、タグ打ちをして準備ができた状態で、以下のコマンドでビルドしました。

ソースパッケージのビルド
------------------------

.. code-block:: console

	gbp buildpackage --git-export-dir=.. -p/home/hnakamur/bin/gpg-passphrase -S -sa -d

以前は :code:`--git-export-dir` は :code:`../build-area` としていましたが、この後のsbuildでupstreamのソースを :code:`../go-carbon_0.12.0.orig.tar.gz` というパスで参照しようとするので :code:`..` に変えました。

バイナリパッケージのビルド
--------------------------

.. code-block:: console

	TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd \
	    --extra-repository="deb http://ppa.launchpad.net/hnakamur/golang-1.10/ubuntu bionic main" \
	    --extra-repository-key /etc/apt/trusted.gpg.d/hnakamur_ubuntu_golang-1_10.gpg

何度も試行錯誤しているとPPAからダウンロードする時間が気になってくるので、以下のコマンドでchrootのホストのfreightを使うようにしました。

.. code-block:: console

	TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd \
		--extra-repository="deb http://127.0.0.1/freight bionic main" \
		--extra-repository-key /var/cache/freight/pubkey.gpg

:code:`/etc/nginx/conf.d/default.conf` には以下のように設定しています。

.. code-block:: text

	server {
	    listen       80;

	…（略） …

	    location /freight {
		alias  /var/cache/freight;
		index  index.html index.htm;
	    }

	…（略） …
