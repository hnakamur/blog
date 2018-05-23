nginxのコードリーディングにrtagsを使う
######################################

:date: 2018-05-23 22:25
:tags: ubuntu, rtags, nginx
:category: blog
:slug: 2018/05/23/use-rtags-for-nginx-code-reading

はじめに
========

`Ubuntu 18.04 LTS用にrtagsのdebパッケージを作成した </blog/2018/05/23/build-rtags-deb-for-ubuntu-18.04-lts/>`__ で作成したrtagsを使ってnginxのコードリーディングをするための手順メモです。

configure で生成される :code:`ngx_auto_config.h` と :code:`ngx_auto_headers.h` も含めて読みたいというのと、rtagsのREADMEの `Setup <https://github.com/Andersbakken/rtags#setup>`_ のうちnginxでは `Bear <https://github.com/rizsotto/Bear>`_ を使って :code:`compile_commands.json` を生成するという関係もあり、 `debパッケージを使ってnginxモジュールをビルド・デバッグする <https://hnakamur.github.io/blog/2018/05/10/build-and-debug-nginx-module-using-deb-package/>`_ と似た感じでビルドしていくことになります。

例によってこの記事に書いているのは試行錯誤してとりあえず動いたという手順なので、もっと良い手順があるかもしれません。

rtagsとvim-rtagsのインストール
==============================

`Ubuntu 18.04 LTS用にrtagsのdebパッケージを作成した </blog/2018/05/23/build-rtags-deb-for-ubuntu-18.04-lts/>`__ の手順で rtags をインストールして rdm を実行しておきます。またvim-rtagsもインストールしておきます。

必要なソフトのインストール
==========================

debパッケージのビルドに必要なツールをインストールします。 equivs は後述の mk-build-deps コマンドで必要になります。

.. code-block:: console

        sudo apt install build-essential devscripts equivs bear

nginxのdebパッケージのソースの取得
==================================

普段使っているモジュール込みでコードリーディングしたいので自作debパッケージのソースを使います。
適当な作業ディレクトリで以下のコマンドを実行します。

.. code-block:: console

        git clone https://github.com/hnakamur/nginx-deb
        cd nginx-deb

依存ライブラリのインストール
============================

.. code-block:: console

        mk-build-deps debian/control
        sudo dpkg -i ./nginx-build-deps*.deb
        sudo apt install -f

パッチ適用
==========

debパッケージに含まれるパッチを適用します。この記事を書いている2018-05-23時点ではパッチを当てないとlua-nginx-moduleがUbuntu 18.04のlibluajit-5.1-devパッケージのファイルを見つけられないので当てる必要があります。

以下のコマンドでパッチを当てます。ちなみにこの手順はバイナリパッケージをビルドするコマンド :code:`dpkg-buildpackage -b` を実行したときに出力されていて知りました。

.. code-block:: console

        dpkg-source --before-build .

この時点で :code:`git status` を実行するとカレントディクレクトリ配下のソースが変更されていました。後ほど :code:`git checkout .` で元に戻しておきます。

ソースのコピーとconfigure実行
=============================

.. code-block:: console

        ./debian/rules config.status.nginx

これで :code:`debian/build-nginx` ディレクトリが作成されてnginxとモジュールのソースがコピーされconfigureが実行されます。この結果として :code:`debian/build-nginx` 以下に :code:`Makefile`, :code:`objs/ngx_auto_config.h`, :code:`objs/ngx_auto_headers.h` やその他のファイルが作られます。

また、カレントディレクトリには :code:`config.env.nginx` と :code:`config.status.nginx` というファイルが生成されます。 :code:`debian/rules` の中を見るとMakefileになっているのですが、これらはmakeのターゲットになっています。

もしcleanしてやり直したい場合は :code:`fakeroot ./debian/rules clean` でcleanできますが、 :code:`debian/build-nginx` 以下の :code:`Makefile` も消えてしまうので、再度 :code:`./debian/rules config.status.nginx` を実行する必要があります。その際は :code:`config.env.nginx` と :code:`config.status.nginx` を消しておく必要があります。

bearを使ってcompile_commands.json作成
=====================================

rtagsのインデクスを作るための元ネタになる :code:`compile_commands.json` をbearを使って作ります。
:code:`compile_commands.json` にはソースコードのフルパスが含まれるので、コードを読むのを別のディレクトリで行いたい場合は、このタイミングで移動すると良いです。

ここでは :code:`~/nginx-code-reading` に移動してみました。

.. code-block:: console

        mv debian/build-nginx ~/nginx-code-reading
        cd !$
        bear make

これで :code:`compile_commands.json` が作られますので、あとは以下を実行してインデクスを作成します。

.. code-block:: console

        rc -J

すると :code:`~/.cache/rtags` ディレクトリの下に :code:`_home_hnakamur_nginx-code-reading_` というディレイクトリが作られていました。これは :code:`/home/hnakamur/nginx-code-reading` というディレクトリに対応したものです（ :code:`/` を :code:`_` に置換して最後に :code:`_` を追加している）。

rtagsを使ってコードを読む
=========================

lyuts/vim-rtags の `Mappings <https://github.com/lyuts/vim-rtags#mappings>`_ のキー操作により定義にジャンプしたり関数などの参照箇所を表示します。

:code:`<Leader>rj` での定義へのジャンプは関数で使えるのはもちろんですが、構造体のフィールドを参照している箇所にカーソルをおいて :code:`<Leader>rj` を押すと構造体の定義のフィールドの行に飛べるのが便利でした。

ジャンプから戻るのは :code:`Ctrl-O` でできました。

おわりに
========

まだ使い始めたばかりなのでよくわかっていませんが、かなり便利そうなので使いこなしていきたいです。
