go1.10rc1のdebパッケージを作ってみた
####################################

:date: 2018-01-28 21:30
:tags: go, deb
:category: blog
:slug: 2018/01/28/build-go-1.10rc1-deb

はじめに
--------

`golang 1.9rc1のUbuntu 16.04用debパッケージをビルドした </blog/2017/08/05/built-golang-1.9rc1-deb-package/>`_ 以降go1.9.xのdebパッケージを `git-buildpackage <https://honk.sigxcpu.org/piki/projects/git-buildpackage/>`_ で作っていましたが、今回 go1.10rc1 のdebパッケージを作ってみたのでメモです。

上の記事ではよくわかっていなかったので手順に無駄がありましたが、今回は現状の私の理解での最適な手順を書きました。ビルドするところまでは。

ビルドが失敗して試行錯誤したので記録として残そうかと思ったのですが長くなったので最終的な手順だけメモしておきます。

golang-1.10のパッケージ作成
---------------------------

パッケージのソースのレポジトリは
https://github.com/hnakamur/golang-deb
です。

1.10.x用のブランチ作成
++++++++++++++++++++++

.. code-block:: console

    git branch ubuntu-1.10 ubuntu-1.9
    git branch upstream-1.10 upstream-1.9

1.10rc1のtarballをダウンロード
++++++++++++++++++++++++++++++

.. code-block:: console

    mkdir -p ~/go-deb-work
    cd ~/go-deb-work
    curl -LO https://dl.google.com/go/go1.10rc1.src.tar.gz

ビルド対象を1.10.xに切り替え
++++++++++++++++++++++++++++

.. code-block:: console

    cd ~/.ghq/github.com/hnakamur/golang-deb
    git checkout ubuntu-1.10
    vi debian/changelog

先頭に以下の内容を追加。

.. code-block:: text

    golang-1.10 (1.10~rc1-1ubuntu1~hnakamur1) xenial; urgency=medium

      * Imported Upstream version 1.10rc1

     -- Hiroaki Nakamura <hnakamur@gmail.com>  Fri, 26 Jan 2018 22:53:00 +0900

.. code-block:: console

    git commit -m 'Release 1.10~rc1-1ubuntu1~hnakamur1' debian/changelog

:code:`debian/changelog` の先頭のエントリの :code:`golang-1.10` の部分を元に
:code:`debian/gbp.conf` などのファイルを上書き生成します。

.. code-block:: console

    ./debian/rules gencontrol

生成された debian/gbp.conf の内容を確認。

.. code-block:: console

    $ cat debian/gbp.conf
    #
    # WARNING: "debian/gbp.conf" is generated via "debian/rules gencontrol" (sourced from "debian/gbp.conf.in")
    #

    [DEFAULT]
    debian-branch = ubuntu-1.10
    debian-tag = debian/%(version)s
    upstream-branch = upstream-1.10
    upstream-tag = upstream/%(version)s
    pristine-tar = True

    [dch]
    meta = 1

他に以下のファイルも生成されていました。

.. code-block:: console

    $ git status -s
     M debian/control
     M debian/gbp.conf
     M debian/source/lintian-overrides
     M debian/watch

変更されたファイルをコミットします。

.. code-block:: console

    $ git commit -m 'Switch to go1.10.x' debian/

1.10rc1のtarballをインポート
++++++++++++++++++++++++++++

.. code-block:: console

    $ gbp import-orig --no-interactive -u1.10~rc1 ~/go-deb-work/go1.10rc1.src.tar.gz
    gbp:info: Importing '/home/hnakamur/go-deb-work/go1.10rc1.src.tar.gz' to branch 'upstream-1.10'...
    gbp:info: Source package is golang-1.10
    gbp:info: Upstream version is 1.10~rc1
    gbp:info: Merging to 'ubuntu-1.10'
    gbp:info: Successfully imported version 1.10~rc1 of /home/hnakamur/go-deb-work/go1.10rc1.src.tar.gz

これで以下の4つが実行されていました。

* :code:`pristine-tar` ブランチに 1.10rc1 用のコミットが追加された。
* :code:`upstream-1.10` ブランチに 1.10rc1 をインポートしたコミットが追加された。
* 上記のコミットに :code:`upstream/1.10_rc1` というタグが打たれた。
* :code:`ubuntu-1.10` ブランチに :code:`upstream-1.10` ブランチの内容がマージされた。

1.10rc1のソースパッケージを作成
+++++++++++++++++++++++++++++++

以下のコマンドでソースパッケージを作成します。

.. code-block:: console

    gbp buildpackage --git-export-dir=../build-area -S -sa -p/home/hnakamur/bin/gpg-passphrase

最後の :code:`-p` オプションは `git-buildpacakgeとfreightでパスフレーズをファイルから入力させる </blog/2017/08/28/use-passphrase-file-in-git-buildpackage-and-freight/>`_ にメモした通りパスフレーズを自動入力するためのものです。

1.10rc1のdebパッケージをローカルでビルド
++++++++++++++++++++++++++++++++++++++++

.. code-block:: console

    sudo pbuilder build ../build-area/golang-1.10_1.10~rc1-1ubuntu1~hnakamur1.dsc

ビルド失敗と回避策
++++++++++++++++++

これで無事ビルドできるかと思いきや以下のようなエラーが出てビルド失敗しました。

.. code-block:: text

    Building packages and commands for linux/amd64.
    /build/golang-1.10-1.10~rc1/bin/go install -v -buildmode=shared \
            -ldflags '-extldflags "-Wl,-soname=libgolang-1.10-std.so.1"' \
            std
    initializing cache in $GOCACHE: mkdir /nonexistent: permission denied
    debian/rules:115: recipe for target 'override_dh_auto_build-arch' failed
    make[1]: *** [override_dh_auto_build-arch] Error 1
    make[1]: Leaving directory '/build/golang-1.10-1.10~rc1'
    debian/rules:26: recipe for target 'build' failed
    make: *** [build] Error 2
    dpkg-buildpackage: error: debian/rules build gave error exit status 2
    I: copying local configuration
    E: Failed autobuilding of package
    I: user script /var/cache/pbuilder/build/8740/tmp/hooks/C10shell starting

go1.10rc1のソースを見てみました。
上記の :code:`initializing cache in $GOCACHE: mkdir /nonexistent: permission denied`
のエラーは以下の43行目で出ているようです。

https://github.com/golang/go/blob/go1.10rc1/src/cmd/go/internal/cache/default.go#L35-L55

.. code-block:: go
    :linenos: table
    :linenostart: 35

    // initDefaultCache does the work of finding the default cache
    // the first time Default is called.
    func initDefaultCache() {
        dir := DefaultDir()
        if dir == "off" {
            return
        }
        if err := os.MkdirAll(dir, 0777); err != nil {
            base.Fatalf("initializing cache in $GOCACHE: %s", err)
        }
        if _, err := os.Stat(filepath.Join(dir, "README")); err != nil {
            // Best effort.
            ioutil.WriteFile(filepath.Join(dir, "README"), []byte(cacheREADME), 0666)
        }

        c, err := Open(dir)
        if err != nil {
            base.Fatalf("initializing cache in $GOCACHE: %s", err)
        }
        defaultCache = c
    }

いろいろ調べたり試行錯誤した結果、pbuilderが :code:`$HOME` の指すディレクトリを書き込み不可にする一方、goのビルドとテストでは :code:`$HOME` 以下にディレクトリやファイルを作ろうとするのでエラーになることがわかりました。

そこで以下のように :code:`debian/rules` を書き換えて回避しました。

.. code-block:: text

    diff --git a/debian/rules b/debian/rules
    index b6d44ae..3bc70c9 100755
    --- a/debian/rules
    +++ b/debian/rules
    @@ -22,6 +22,14 @@ shlib_archs = $(shell GOVER=$(GOVER) perl debian/helpers/getshlibarches.pl)

     multiarch := $(shell dpkg-architecture -qDEB_HOST_MULTIARCH)

    +# NOTE: We need $HOME to be writable in order to run builds
    +# and tests successfully.
    +# pbuilder sets $HOME to /nonexistent and make it non-writable.
    +# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=441052
    +ifneq (0,$(shell test -w "$(HOME)"; echo $$?))
    +        export HOME := /tmp
    +endif
    +
     %:
            +dh --parallel $(opt_no_act) $@

これをコミットして再度ソースパッケージとdebパッケージをビルドすると今度は成功しました。

gitタグ作成
+++++++++++

動作確認後以下のタグを打っておきました。

.. code-block:: console

    git tag debian/1.10_rc1-1ubuntu1_hnakamur1

golang-defaultsのパッケージ作成
-------------------------------

パッケージのソースのレポジトリは
https://github.com/hnakamur/golang-defaults-deb
です。

changelogにエントリ追加
+++++++++++++++++++++++

:code:`debian/changelog` の先頭に以下のエントリを追加します。

.. code-block:: text

    golang-defaults (2:1.10~1ubuntu1~hnakamur1) xenial; urgency=medium

      * Use Golang 1.10.

     -- Hiroaki Nakamura <hnakamur@gmail.com>  Sun, 28 Jan 2018 16:52:00 +0900

上記の変更をコミットします。

.. code-block:: console

    git commit -m 'Release 2:1.10~1ubuntu1~hnakamur1' debian/changelog

ソースパッケージを作成
++++++++++++++++++++++

.. code-block:: console

    gbp buildpackage --git-export-dir=../build-area -S -sa -p/home/hnakamur/bin/gpg-passphrase

debパッケージをローカルでビルド
+++++++++++++++++++++++++++++++

.. code-block:: console

    sudo pbuilder build ../build-area/golang-defaults_1.10~1ubuntu1~hnakamur1.dsc

gitタグ作成
+++++++++++

動作確認後以下のタグを打っておきました。

.. code-block:: console

    git tag debian/1.10_1ubuntu1_hnakamur1

golang-1.10-race-detector-runtimeのパッケージ作成
-------------------------------------------------

パッケージのソースのレポジトリは
https://github.com/hnakamur/golang-1.10-race-detector-runtime-deb
です。

ソースレポジトリを作成
++++++++++++++++++++++

1.9のrace-detector-runtimeのレポジトリをコピーして作成しました。

.. code-block:: console

    cp -pr ~/.ghq/github.com/hnakamur/golang-1.{9,10}-race-detector-runtime-deb

:code:`debian/control` 内のパッケージ名を1.10用に書き換えます。

.. code-block:: console

    sed -i 's/golang-1\.9/golang-1.10/' debian/control

:code:`debian/golang-1.8-race-detector-runtime.lintian-overrides` というファイルがあり、中身を見ると前回1.9用に作ったときに1.9用に書き換えてあったのですが、ファイル名は1.8のままになっていました。

ということでファイル名を1.10用に変えつつ中身も1.10用に変えます。

.. code-block:: console

    git mv debian/golang-1.{8,10}-race-detector-runtime.lintian-overrides
    sed -i 's/golang-1\.9/golang-1.10/;s/go-1\.9/go-1.10/' debian/golang-1.10-race-detector-runtime.lintian-overrides

https://github.com/golang/go/blob/go1.10rc1/src/runtime/race/README
を見ると、goのrace detectorのランタイムはLLVMプロジェクトの
ThreadSanitizer race detectorがベースになっていると書いてあります。

.. code-block:: text

    runtime/race package contains the data race detector runtime library.
    It is based on ThreadSanitizer race detector, that is currently a part of
    the LLVM project (http://llvm.org/git/compiler-rt.git).

    To update the .syso files use golang.org/x/build/cmd/racebuild.

    Current runtime is built on rev 68e1532492f9b3fce0e9024f3c31411105965b11.

:code:`debian/changelog` の先頭に以下のエントリを追加します。
バージョン番号内の :code:`+git` の後の文字列は上のREADMEの最終行に書いてあるgitのコミットハッシュの先頭6桁にします。

.. code-block:: text

    golang-1.10-race-detector-runtime (0.0+git68e153~ubuntu16.04.1hnakamur1) xenial; urgency=medium

      * Update package name for Go 1.10.
      * Update to version used by Go 1.10.
      * Get orig source from the LLVM compiler-rt git repository.

     -- Hiroaki Nakamura <hnakamur@gmail.com>  Sun, 28 Jan 2018 17:40:00 +0900

変更内容をコミットします。

.. code-block:: console

    git commit -m 'Update for go1.10' debian/

オリジンのソース取得
++++++++++++++++++++

:code:`debian/rules` の :code:`get-orig-source` ターゲットはgo1.9のときはLLVMのsubversionレポジトリから取得するようになっていたのですが、今回はgitなので処理を書き換えました。

.. code-block:: text

    diff --git a/debian/rules b/debian/rules
    index b28630a..44e0ea6 100755
    --- a/debian/rules
    +++ b/debian/rules
    @@ -35,13 +35,15 @@ override_dh_auto_build:

     PKD  = $(abspath $(dir $(MAKEFILE_LIST)))
     PKG  = $(shell dpkg-parsechangelog -l$(PKD)/changelog --show-field=Source)
    -REVNO = $(shell dpkg-parsechangelog  -SVersion | sed -e 's/.*svn\([0-9]\+\)-.*/\1/')
    +COMMIT = $(shell dpkg-parsechangelog -SVersion | sed -rne 's/[^+]*\+git([0-9a-f]+).*/\1/p')

     get-orig-source:
    -       svn co http://llvm.org/svn/llvm-project/compiler-rt/trunk compiler-rt
    -       cd compiler-rt && svn export -r $(REVNO) . "../$(PKG)_0.0+svn$(REVNO)"
    -       tar czf $(PKG)_0.0+svn$(REVNO).orig.tar.gz $(PKG)_0.0+svn$(REVNO)
    -       rm -rf compiler-rt $(PKG)_0.0+svn$(REVNO)
    +       ls | grep -v '^debian$$' | xargs rm -rf
    +       git clone http://llvm.org/git/compiler-rt.git
    +       cd compiler-rt \
    +               && echo .gitignore export-ignore > .gitattributes \
    +               && git archive --worktree-attributes $(COMMIT) | tar x -C ..
    +       rm -rf compiler-rt

     %:
            dh $@

以下のコマンドを実行してオリジンのソースを取得します。

.. code-block:: console

    ./debian/rules get-orig-source

ソースの差分は以下の一か所だけで実質は変わっていませんでした。

.. code-block:: text

    diff --git a/lib/tsan/go/buildgo.sh b/lib/tsan/go/buildgo.sh
    index 812cb93..42d4790 100755
    --- a/lib/tsan/go/buildgo.sh
    +++ b/lib/tsan/go/buildgo.sh
    @@ -125,7 +125,7 @@ if [ "$SILENT" != "1" ]; then
     fi
     $CC $DIR/gotsan.cc -c -o $DIR/race_$SUFFIX.syso $FLAGS $CFLAGS

    -$CC $OSCFLAGS test.c $DIR/race_$SUFFIX.syso -m64 -g -o $DIR/test $OSLDFLAGS $LDFLAGS
    +$CC $OSCFLAGS test.c $DIR/race_$SUFFIX.syso -m64 -g -o $DIR/test $OSLDFLAGS

     export GORACE="exitcode=0 atexit_sleep_ms=0"
     if [ "$SILENT" != "1" ]; then

取得したソースはコミットしておきます。

ソースパッケージを作成
++++++++++++++++++++++

.. code-block:: console

    gbp buildpackage --git-export-dir=../build-area -S -sa -p/home/hnakamur/bin/gpg-passphrase

debパッケージをローカルでビルド
+++++++++++++++++++++++++++++++

.. code-block:: console

    sudo pbuilder build ../build-area/golang-1.10-race-detector-runtime_0.0+git68e153~ubuntu16.04.1hnakamur1.dsc

gitタグ作成
+++++++++++

動作確認後以下のタグを打っておきました。

.. code-block:: console

    git tag debian/0.0+git68e153_ubuntu16.04.1hnakamur1

PPAでビルド
-----------

`freightでプライベートdebレポジトリ作成 </blog/2017/08/05/create-private-deb-repository-with-freight/>`_ の手順でローカルのレポジトリに登録してLXDのUbuntu Xenialコンテナで動作確認して問題ないことを確認した後、PPAでビルドしました。

今回新たに
https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10
というPPAを作成しました。

作成後、画面右の Change details リンクをクリックして以下のように変更しました。

* Build debug symbols にチェック
* Publish debug symbols にチェック
* Processors の Intel x86 (i386) のチェックを外す

以下のコマンドを実行してPPAでビルドしました。

.. code-block:: console

    dput ppa:hnakamur/golang-1.10 ../build-area/golang-1.10_1.10~rc1-1ubuntu1~hnakamur1_source.changes
    dput ppa:hnakamur/golang-1.10 ../build-area/golang-defaults_1.10~1ubuntu1~hnakamur1_source.changes
    dput ppa:hnakamur/golang-1.10 ../build-area/golang-1.10-race-detector-runtime_0.0+git68e153~ubuntu16.04.1hnakamur1_source.changes

PPAでのビルド完了後、ローカルのレポジトリからインストールしたdebパッケージはアンインストールして、以下の手順でPPAからインストールして再度動作確認しました。

PPAからのインストール方法
-------------------------

:code:`add-apt-repository` コマンドを使うために :code:`software-properties-common` パッケージが必要です。インストールしていない場合は以下のコマンドでインストールします。

.. code-block:: console

    sudo apt update
    sudo apt install software-properties-common

以下のコマンドで必要なパッケージ一式がインストールできます。
:code:`golang-1.10-doc` パッケージは :code:`godoc` コマンドを使うために必要ですので入れておきます。

.. code-block:: console

    sudo add-apt-repository ppa:hnakamur/golang-1.10
    sudo apt update
    sudo apt install golang-go golang-1.10-doc

インストールされたgoでバージョンや実行ファイルのパスを確認してみました。

.. code-block:: console

    root@xenial:~# go version
    go version go1.10rc1 linux/amd64
    root@xenial:~# which go
    /usr/bin/go
    root@xenial:~# ls -l /usr/bin/go
    lrwxrwxrwx 1 root root 21 Jan 28 12:01 /usr/bin/go -> ../lib/go-1.10/bin/go

おわりに
--------

まだ作ったばかりで軽い動作確認しかしてませんが、今後使っていこうと思います。
