apt-markを使ってdebパッケージのバージョン固定
#############################################

:date: 2018-05-04 21:05
:tags: ubuntu, deb
:category: blog
:slug: 2018/05/04/hold-deb-package-version-using-apt-mark

はじめに
--------

`nginx <http://nginx.org/>`_ にはmainline版とstable版がありますが、
`どのバージョンのnginxを使うべきか？ - 考える人、コードを書く人 <https://bokko.hatenablog.com/entry/2014/05/24/220554>`_ を参考に私はmainline版をベースにして `openresty/lua-nginx-module <https://github.com/openresty/lua-nginx-module/>`_ などのモジュールを加えたカスタムdebパッケージを作っています。

この記事を書いている時点ではmainline版は1.13.xでstable版は1.14.0でUbuntu 18.04には1.14.0が入っているので、自作debをインストールした状態で apt update を実行するとstable版の1.14.0がアップデート対象として表示されてしまいます。

調べてみると `apt-mark (8) <http://manpages.ubuntu.com/manpages/bionic/en/man8/apt-mark.8.html>`_ というコマンドでバージョン固定できたのでメモです。

バージョン固定
--------------

:code:`sudo apt-mark hold パッケージ名` でバージョン固定します。実行例を示します。

.. code-block:: console

        sudo apt-mark hold nginx

バージョン固定状態確認
----------------------

:code:`apt-mark showhold` コマンドで状態確認できます。実行例を示します。

.. code-block:: console

        $ apt-mark showhold
        nginx

バージョン固定解除
------------------

:code:`sudo apt-mark unhold パッケージ名` でバージョン固定解除します。実行例を示します。

.. code-block:: console

        sudo apt-mark unhold nginx

パッケージをどこからインストールしたかの確認
--------------------------------------------

ついでにパッケージをどこからインストールしたかの確認手順もメモしておきます。

:code:`apt policy パッケージ名` で表示できます。実行例を示します。

.. code-block:: console

	$ apt policy nginx
	nginx:
	  Installed: 1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04
	  Candidate: 1.14.0-0ubuntu1
	  Version table:
	     1.14.0-0ubuntu1 500
		500 http://ftp.iij.ad.jp/pub/linux/ubuntu/archive bionic/main amd64 Packages
		500 http://ftp.iij.ad.jp/pub/linux/ubuntu/archive bionic/main i386 Packages
	 *** 1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04 500
		500 http://ppa.launchpad.net/hnakamur/nginx/ubuntu bionic/main amd64 Packages
		100 /var/lib/dpkg/status
