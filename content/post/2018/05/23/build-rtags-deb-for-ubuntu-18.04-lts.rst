Ubuntu 18.04 LTS用にrtagsのdebパッケージを作成した
##################################################

:date: 2018-05-23 14:10
:tags: ubuntu, rtags, deb
:category: blog
:slug: 2018/05/23/build-rtags-deb-for-ubuntu-18.04-lts

はじめに
========

`rtagsのdebパッケージを作成した </blog/2017/09/05/built-rtags-deb/>`__ のときのメモを端折りすぎて、Ubuntu 18.04 LTS用に rtags 2.18のパッケージを作ろうと思ったら苦労したのでメモしておきます。

ビルドのメモ
============

(参考) gcc-8とLLVM 6.0入りのpbuilderのchroot環境作成
----------------------------------------------------

よくよく考えたらこの手順は不要ですが、今後別件で使うかもしれないのでメモ。

まず既存のchroot環境のtarballをお好みの名前のファイルにコピーします。

.. code-block:: console

        sudo cp /var/cache/pbuilder/bionic-{base,gcc8-llvm6}.tar.gz

:code:`--save-after-login` オプションを指定しつつ、新しく作成したchroot環境にログインします。

.. code-block:: console

        sudo pbuilder login --save-after-login --basetgz /var/cache/pbuilder/bionic-gcc8-llvm6.tar.gz

chroot環境内でお好みのパッケージをインストールし、exitで抜ければ保存されます。

.. code-block:: console

        apt install gcc-8 g++-8 llvm-6.0-dev libclang-6.0-dev
        exit

利用時は pbuilder に :code:`--basetgz /var/cache/pbuilder/bionic-gcc8-llvm6.tar.gz` を指定して実行します。

ただ、今回は :code:`debian/control` の :code:`Build-Depends` に必要なパッケージを書いているので上記の手順は不要でした。

gitサブモジュールのソースも含めてオリジンのソースtarball作成
------------------------------------------------------------

`Andersbakken/rtags: A c/c++ client/server indexer for c/c++/objc[++] with integration for Emacs based on clang. <https://github.com/Andersbakken/rtags>`_ ではgitサブモジュールを使っているので、オリジンのソースtarballを作成する際はサブモジュールのソースも含めておく必要が有ります。

rtagsの `.gitmodules <https://github.com/Andersbakken/rtags/blob/163c81ea636c2aaca78e76df174bfd5679015bd7/.gitmodules>`_ は以下のようになっていてサブモジュールの特定のコミットを指定するのではなく master で最新のコミットを参照するようになっていました。

.. code-block:: text

        [submodule "src/rct"]
                path = src/rct
                url = https://github.com/Andersbakken/rct
                branch = master
        [submodule "src/selene"]
                path = src/selene
                url = https://github.com/jeremyong/Selene.git
            branch = master
        [submodule "src/lua"]
                path = src/lua
                url = https://github.com/LuaDist/lua.git
            branch = master

ということでrtagsの過去のリリースの際に参照していたサブモジュールのコミットはわからないので、最新を使うことにします。

以下のコマンドでサブモジュール入りのソースtarballを作成しました。

.. code-block:: console

        git clone --recursive https://github.com/Andersbakken/rtags.git
        cd rtags
        git checkout v2.18
        cd ..
        mkdir -p ~/rtags-deb-work
        tar cf - --exclude=.git ./rtags | gzip -9 > ~/rtags-deb-work/rtags-2.18-with-submodules.tar.gz

作成したtarballをdebパッケージビルド用レポジトリにインポート
------------------------------------------------------------

debパッケージビルド用レポジトリの作業ディレクトリに移動して以下のようにインポートしました。

.. code-block:: console

        cd ~/.ghq/github.com/hnakamur/rtags-deb
        gbp import-orig --pristine-tar -u 2.18 ~/rtags-deb-work/rtags-2.18-with-submodules.tar.gz

rtagsのテストの実行方法を修正するパッチ作成
-------------------------------------------

あとはいつもの手順でdebパッケージをビルドすればOKかと思いきや、テストの実行時に :code:`/usr/bin/rdm` というファイルがないというエラーになってしまいました。

:code:`rdm` は rtags で提供されるサーバプログラムですが、ビルド時はまだ /usr/bin/ にはインストールしていないので /usr/bin/rdm を参照するのは不適切です。

`cmake-variables(7) — CMake 3.0.2 Documentation <https://cmake.org/cmake/help/v3.0/manual/cmake-variables.7.html>`_ を参照しつつ、twitter で `眼力 玉壱號さんからのアドバイス <https://twitter.com/objectxplosive/status/999151356249235456>`_ を頂いて以下のような
`パッチ <https://github.com/hnakamur/rtags-deb/blob/e63073a4275260a446af3fe3201e13749bd1b345/debian/patches/0001-Fix-bin-dir-for-tests.patch>`_
を作成しました。

.. code-block:: diff

        From: Hiroaki Nakamura <hnakamur@gmail.com>
        Date: Wed, 23 May 2018 12:08:35 +0900
        Subject: Fix bin dir for tests

        ---
         CMakeLists.txt | 2 +-
         1 file changed, 1 insertion(+), 1 deletion(-)

        diff --git a/CMakeLists.txt b/CMakeLists.txt
        index 4284e30..e7accfe 100644
        --- a/CMakeLists.txt
        +++ b/CMakeLists.txt
        @@ -87,7 +87,7 @@ set(BIN ${CMAKE_INSTALL_PREFIX}/bin)
         if (RTAGS_NO_INSTALL)
             set(BIN ${CMAKE_BINARY_DIR}/bin)
         endif ()
        -add_test(SBRootTest perl "${CMAKE_SOURCE_DIR}/tests/sbroot/sbroot_test.pl" "${BIN}")
        +add_test(SBRootTest perl "${CMAKE_SOURCE_DIR}/tests/sbroot/sbroot_test.pl" "${CMAKE_BINARY_DIR}/bin")
         find_program(NOSETEST NAMES nosetests nosetests-2.7 PATHS "$ENV{HOME}/.local/bin")
         if (NOSETEST)
             add_test(nosetests ${NOSETEST} -w ${CMAKE_SOURCE_DIR} -v)

あとはいつもどおりの手順でビルドできました。

使い方
======

インストール手順
----------------

ビルドしたパッケージは
`vim : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/vim>`_
で公開しています。

以下の手順でインストール出来ます。

.. code-block:: console

        sudo apt install software-properties-common
        sudo add-apt-repository ppa:hnakamur/vim
        sudo apt update
        sudo apt install rtags

`rtagsのdebパッケージを作成した </blog/2017/09/05/built-rtags-deb/>`__ のときとは違って、
Ubuntu 18.04 LTSでは標準パッケージのvim8で問題なく動きました。また :code:`~/.rdmrc` の作成も不要でした。

vim-rtagsのインストール
-----------------------

`lyuts/vim-rtags: Vim bindings for rtags, llvm/clang based c++ code indexer. <https://github.com/lyuts/vim-rtags>`_ の手順に沿ってインストールします。

私は `junegunn/vim-plug: Minimalist Vim Plugin Manager <https://github.com/junegunn/vim-plug>`_ を使っているので :code:`vim ~/.vimrc` で :code:`~/.vimrc` を開き
:code:`call plug#begin('~/.vim/plugged')` と :code:`call plug#end()` の間に

.. code-block:: text

        Plug 'lyuts/vim-rtags'

の行を追加して vim 上で以下のように実行してインストールします。

.. code-block:: vim

        :so %
        :PlugInstall

rtagsのサーバ起動
-----------------

起動方法1: 単にバックグラウンドで起動
+++++++++++++++++++++++++++++++++++++

以下のようにバックグラウンドで rdm を起動します。

.. code-block:: console

        rdm -L ~/.rdm.log &

:code:`-L` でログファイルを指定しておくと、後から :code:`tail -f ~/.rdm.log` としてインデクスの作成状況や問い合わせ状況を確認できて便利です。

起動方法2: systemdのユーザ毎サービスとして起動
++++++++++++++++++++++++++++++++++++++++++++++

Ubuntuのデスクトップ環境のようにD-busが使える環境であればsystemdのユーザ毎サービスとして起動するという手もあります。
以下のような内容で :code:`~/.config/systemd/user/rtags-daemon.service` を作成します。

.. code-block:: text

        [Unit]
        Description=Rtags daemon
        Documentation=man:rdm(7) https://github.com/Andersbakken/rtags

        [Service]
        ExecStart=/usr/bin/rdm
        StandardOutput=syslog

        [Install]
        WantedBy=default.target

作成から起動と自動起動設定まで行うコマンドは以下のとおりです。

.. code-block:: console

        mkdir -p ~/.config/systemd/user
        cat <<'EOF' > ~/.config/systemd/user/rtags-daemon.service
        [Unit]
        Description=Rtags daemon
        Documentation=man:rdm(7) https://github.com/Andersbakken/rtags

        [Service]
        ExecStart=/usr/bin/rdm
        StandardOutput=syslog

        [Install]
        WantedBy=default.target
        EOF
        systemctl daemon-reload --user
        systemctl start --user rtags-daemon
        systemctl enable --user rtags-daemon

こちらの方法で起動した場合は :code:`journalctl --user -f` でログを見つつ、下記の :code:`rc -J` でインデクス作成などを行うことができます。

読みたいソースのインデクス作成
------------------------------

酔いたいソースがあるディレクトリに移動して rtags の README の `Setup <https://github.com/Andersbakken/rtags#setup>`__ のいずれかの手順に従って、 :code:`compile_commands.json` というファイルを生成し、生成したディクレクトリで

.. code-block:: console

        rc -J

を実行してインデクスを作成します。実行すると :code:`~/.cache/rtags/` 以下にディレクトリとバイナリ形式のインデクスデータファイルが生成されます。

rtagsを利用してソースを読む
---------------------------

lyuts/vim-rtags の `Mappings <https://github.com/lyuts/vim-rtags#mappings>`_ のキー操作により定義にジャンプしたり関数などの参照箇所を表示します。
