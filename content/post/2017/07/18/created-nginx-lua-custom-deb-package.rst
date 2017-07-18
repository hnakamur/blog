nginx+luaのカスタムdebパッケージを作ってみた
############################################

:date: 2017-07-18 15:20
:tags: deb nginx lua
:category: blog
:slug: 2017/07/18/created-nginx-custom-deb-package

はじめに
--------

`ngx_http_v2_upstreamモジュールを追加したnginxのdebパッケージを作ってみた </blog/2017/07/14/build-nginx-deb-with-ngx_http_v2_upstream/>`_ 、 `git-buildpackageのpatch-queue機能を試してみた </blog/2017/07/14/tried-git-buildpackage-patch-queue/>`_ の続きです。

私はCentOS 6と7用のnginx + luaのカスタムrpmを
`hnakamur/nginx-rpm: A Dockerfile to build nginx rpm for CentOS 6 and 7 using fedora copr <https://github.com/hnakamur/nginx-rpm>`_
で作っていましたが、それとほぼ同じ内容のdebパッケージを作ってみました。

debパッケージのソースは
`hnakamur/nginx-deb: my nginx custom deb package for Ubuntu 16.04 LTS <https://github.com/hnakamur/nginx-deb>`_
で公開しています。

今回は手順ではなくて説明メモだけ書きます。
一般的なdebパッケージ作成の話というよりは、nginx.orgのdebパッケージをベースにカスタマイズしたときの固有の話が多いです。

パッチの起源をOriginヘッダで記録
--------------------------------

`DEP-3: Patch Tagging Guidelines <http://dep.debian.net/deps/dep3/>`_ では :code:`Origin` ヘッダは
:code:`Author` ヘッダが存在しない場合のみ必須となっています。

でも、パッチの元ネタがどこかは将来のバージョンアップ時に必要になるケースが出てくるので、 :code:`Author` ヘッダを書く場合でも :code:`Origin` ヘッダも付けておきたいと思いました。

しかし :code:`patch-queue` ブランチの各コミットでパッチを管理して :code:`gbp pq export` でパッチを再生成すると、
code:`From` ヘッダ、 :code:`Date` ヘッダ、 :code:`Subject` ヘッダは残るのですが :code:`Origin` ヘッダは消されてしまうことがわかりました。

そこで回避策として以下のようにパッチの前の本文の部分の先頭に :code:`Origin` ヘッダを入れて、本文との区切りがわかるように改行を入れるようにしました。

.. code-block:: console

	From: Piotr Sikora <piotrsikora at google.com>
	Date: Sat, 8 Apr 2017 20:26:21 -0700
	Subject: Output chain: propagate last_buf flag to c->send_chain().

	Origin: http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010209.html

	Signed-off-by: Piotr Sikora <piotrsikora at google.com>
	---

サードパーティのnginxモジュールのソースはupstreamブランチで追加
---------------------------------------------------------------

現状ではnginxのモジュールはサードパーティのモジュールもnginx本体と同時にビルドする必要があります。
サードパーティのnginxモジュールのソースをパッチで管理すると、パッチが増えすぎて現実的ではないのでupstreamブランチで管理することにしました。

するとnginxのバージョンが例えば1.13.3でもサードパーティのモジュールのソースを追加・更新・削除など行った場合は
アップストリームのtarballのバージョンを変える必要があります。

そこで
`パッケージ名とバージョン <https://www.debian.org/doc/manuals/maint-guide/first.ja.html#namever>`_ と
`What does “dfsg” in the version string mean? <https://wiki.debian.org/DebianMentorsFaq#What_does_.2BIBw-dfsg.2BIB0_in_the_version_string_mean.3F>`_
を参考にして、アップストリームのバージョンに :code:`+mod.1` のようにモジュール用のバージョンを追加し
:code:`1.13.3+mod.1~xenial1ppa1` のようなバージョンにしました。

nginxのアップストリームのバージョンを変えずに、サードパーティのソースを変更した場合は :code:`mod.` の後の数字を増やしてバージョンを変更し、そのタグを打ちます。

サードパーティのnginxモジュールのソースをダウンロードしてサブディレクトリに展開するスクリプトを追加
---------------------------------------------------------------------------------------------------

例えば
`openresty/lua-nginx-module <https://github.com/openresty/lua-nginx-module>`_
だったら :code:`lua-nginx-module` というサブディレクトリを作ってそこに置くようにしました。

nginxのアップストリームのソース更新時にまた行うことになるかもしれないので、簡単なスクリプトを書いておきました。
`debian/download-module-sources.sh <https://github.com/hnakamur/nginx-deb/blob/48c12f3100a568024027ee5de74579f44e78de98/debian/download-module-sources.sh>`_

モジュールの追加に応じてdebian/rulesを編集
------------------------------------------

サードパーティのモジュールをビルドに追加するには :code:`./configure` オプションに
:code:`--add-module=` または :code:`--add-dynamic-module=` でモジュールのソースディレクトリを指定します。

nginx.orgのdebパッケージの :code:`debian/rules` はshbangに :code:`#!/usr/bin/make -f` と書いてあって2行目以降は
Makefileの形式になっています。

デバッグシンボル有りと無しの2つをビルドする関係で :code:`./configure` は `debian/rules <https://github.com/hnakamur/nginx-deb/blob/48c12f3100a568024027ee5de74579f44e78de98/debian/rules>`_ の :code:`config.status.nginx` ターゲットと
:code:`config.status.nginx_debug` ターゲットの2箇所あり、ビルドする際に別ディレクトリにコピーするための :code:`config.env.%` ターゲットもあるので、サードパーティのモジュールを追加する際は合計3箇所を編集する必要があります。

サードパーティのnginxモジュールへのパッチ
-----------------------------------------

サードパーティのnginxモジュールへのパッチもpatch-queueブランチで管理してみました。

パッチの元ネタ作成はサードパーティのモジュールでトピックブランチを切って変更したコミットを追加し以下のコマンドで行いました。 :code:`<n>` の部分は :code:`debian/patches` にある最後のパッチの番号の次の番号にします。

.. code-block:: console

	git format-patch --starting-number <n> -1 HEAD

私のnginxカスタムパッケージではサードパーティモジュールのソースはサブディレクトリに入れていますので、
パッチを当てるソースのパスを手動で変更する必要があります。

例えば
`nginx-deb/0014-Update-config-to-be-used-as-external-module-for-ngin.patch <https://github.com/hnakamur/nginx-deb/blob/48c12f3100a568024027ee5de74579f44e78de98/debian/patches/0014-Update-config-to-be-used-as-external-module-for-ngin.patch>`_
は :code:`nginx-dav-ext-module` を動的モジュールとしてビルド可能にするパッチなのですが、

.. code-block:: text

	diff --git a/config b/config
	index 98b2b7a..00ac047 100644
	--- a/config
	+++ b/config

とサードパーティモジュールのソースではディレクトリ直下にあった :code:`config` ファイルが
今回作成しているnginxパッケージでは :code:`nginx-dav-ext-module/config` というパスになるので、下記のように手動で書き換えています。

.. code-block:: text

	diff --git a/nginx-dav-ext-module/config b/nginx-dav-ext-module/config
	index 98b2b7a..00ac047 100644
	--- a/nginx-dav-ext-module/config
	+++ b/nginx-dav-ext-module/config

このようにパッチを作ってから :code:`gbp pq apply パッチファイル名` で適用し、 :code:`gbp pq export` でパッチを再生成するという手順でパッチを作成、適用しました。

今回は試してないですが、場合によっては、 :code:`patch-queue/master` ブランチで直接ファイルを編集してコミットし、 :code:`gbp pq export` でパッチを再生成するほうが楽かもしれません。パッチの元ネタが自分以外の方の場合は :code:`git commit` の :code:`--author` や :code:`--date` でコミットの著者や日時を元のパッチに合わせるようにしておけば、この手順で良さそうな気がします。

インストールするファイルが増えたらdebian/nginx.installに追加
------------------------------------------------------------

nginx本体またはサードパーティのモジュールをダイナミックモジュールでビルドするようにした場合は :code:`/usr/lib/nginx/modules/` に :code:`*.so` ファイルがインストールされるので :code:`debian/nginx.install` にエントリを追加します。

今回の具体例は
`nginx-deb/nginx.install <https://github.com/hnakamur/nginx-deb/blob/48c12f3100a568024027ee5de74579f44e78de98/debian/nginx.install>`_
です。

途中でサードパーティのダイナミックモジュールは別パッケージに分けようかとも思ったのですが、ソースをnginx本体とサードパーティのモジュールを一括で管理し、パッケージも :code:`1.13.3+mod.1~xenial1ppa1` のようなバージョンにしているので、分けるとバージョンが紛らわしいと思い、分けないことにしました。

サードパーティのモジュールのビルドに必要なライブラリをdebian/controlのBuild-Dependsに追加
-----------------------------------------------------------------------------------------

今回の例
`nginx-deb/control <https://github.com/hnakamur/nginx-deb/blob/48c12f3100a568024027ee5de74579f44e78de98/debian/control>`_
では :code:`libluajit-5.1-dev` 以降を追加しています。

:code:`pbuilder` でビルドしてエラーになったら必要なものを追加するという手順で追記していきました。

作成したdebパッケージの依存ライブラリをdebian/controlのDependsに追加
--------------------------------------------------------------------

LXDのコンテナを新規作成するなどしてクリーンな環境に作成したdebパッケージをインストールしてみて
必要と言われたパッケージを :code:`debian/control` の :code:`Depends` に追記しました。

横道にそれますが、
`How to let \`dpkg -i\` install dependencies for me? - Ask Ubuntu <https://askubuntu.com/questions/40011/how-to-let-dpkg-i-install-dependencies-for-me>`_
にローカルのdebファイルを :code:`dpkg -i` でインストールする時に必要なライブラリをインストールする方法が紹介されていました。以下の2つの方法を試してみて両方うまくいくことを確認しました。

* debファイルのインストールは :code:`dpkg -i debパッケージファイル名` で行って、必要なライブラリが足りなくてエラーになった後 :code:`apt install -f` でそれらをインストールする。
* :code:`gdebi-core` パッケージをインストールしておいて、 :code:`gdebi debパッケージファイル名` でインストールする。

そしてdebソースパッケージのmasterブランチを適宜rebaseしつつ、再ビルドして作成したdebパッケージが問題なくインストールできるようになったら完成です。

PPAでビルドするアーキテクチャの変更
-----------------------------------

ローカルでビルドが通るようになったのでPPAを作ってアップロードしてみたのですが、amd64ではビルド成功するけどi386ではビルド失敗しました。

i386のdebパッケージは私は不要なのでビルド対象から外すことにしました。

`Packaging/PPA - Launchpad Help <https://help.launchpad.net/Packaging/PPA?action=show&redirect=PPA>`_ の
`ARM builds <https://dev.launchpad.net/CommunityARMBuilds>`_ にARMをビルド対象に追加する手順が書かれていました。

これを参考にi386を削除しました。自分のnginxのPPAのページの右上に Change details というリンクがあるので、
それをクリックし Processors の下のチェックボックスの選択を変更してSaveボタンを押せばOKです。
