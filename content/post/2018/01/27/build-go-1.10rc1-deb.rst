go1.10rc1のdebパッケージを作ったときのメモ
##########################################

:date: 2018-01-27 10:00
:tags: go, deb
:category: blog
:slug: 2018/01/27/build-go-1.10rc1-deb

はじめに
--------

`golang 1.9rc1のUbuntu 16.04用debパッケージをビルドした </blog/2017/08/05/built-golang-1.9rc1-deb-package/>`_ 以降go1.9.xのdebパッケージを `git-buildpackage <https://honk.sigxcpu.org/piki/projects/git-buildpackage/>`_ で作っていましたが、今回 go1.10rc1 をビルドしたのでメモです。

上の記事ではよくわかっていなかったので手順に無駄がありましたが、今回は現状の私の理解での最適な手順を書きました。ビルドするところまでは。

ビルドが失敗して手直ししたのでそこは記録として残しておきます。

1.10.x用のブランチ作成
----------------------

.. code-block:: console

    git branch ubuntu-1.10 ubuntu-1.9
    git branch upstream-1.10 upstream-1.9

1.10rc1のtarballをダウンロード
------------------------------

.. code-block:: console

    mkdir -p ~/go-deb-work
    cd ~/go-deb-work
    curl -LO https://dl.google.com/go/go1.10rc1.src.tar.gz

ビルド対象を1.10.xに切り替え
----------------------------

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
----------------------------

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
-------------------------------

以下のコマンドでソースパッケージを作成します。

.. code-block:: console

    gbp buildpackage --git-export-dir=../build-area -S -sa -p/home/hnakamur/bin/gpg-passphrase

最後の :code:`-p` オプションは `git-buildpacakgeとfreightでパスフレーズをファイルから入力させる </blog/2017/08/28/use-passphrase-file-in-git-buildpackage-and-freight/>`_ にメモした通りパスフレーズを自動入力するためのものです。

1.10rc1のdebパッケージをローカルでビルド
----------------------------------------

.. code-block:: console

    sudo pbuilder build ../build-area/golang-1.10_1.10~rc1-1ubuntu1~hnakamur1.dsc

ビルド失敗
----------

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
https://github.com/golang/go/blob/go1.10rc1/src/cmd/go/internal/cache/default.go#L35-L55
上記の :code:`initializing cache in $GOCACHE: mkdir /nonexistent: permission denied`
のエラーは以下の43行目で出ているようです。

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

:code:`debian/rules:115: recipe for target 'override_dh_auto_build-arch' failed`
のエラーに対応する :code:`debian/rules` の 115行目あたりは以下のようになっていました。

.. code-block:: text
    :linenos: table
    :linenostart: 114

    override_dh_auto_build-arch:
            [ -f VERSION ] || echo "debian snapshot +$$(dpkg-parsechangelog -SVersion)" > VERSION
            export GOROOT_BOOTSTRAP=$$(env -i go env GOROOT) \
                    && cd src \
                    && $(CURDIR)/debian/helpers/goenv.sh \
                            bash ./make.bash --no-banner
            $(CURDIR)/bin/go install -v -buildmode=shared \
                    -ldflags '-extldflags "-Wl,-soname=libgolang-$(GOVER)-std.so.1"' \
                    std

:code:`debian/rules` の先頭のほうを見ると :code:`GOROOT` と :code:`GOROOT_FINAL` という環境変数が設定されていました。

.. code-block:: text
    :linenos: table
    :linenostart: 7

    export GOROOT := $(CURDIR)
    export GOROOT_FINAL := /usr/lib/go-$(GOVER)

ここに :code:`GOCACHE` の設定を追加して試してみたら行けたりしないかな、と例によって雰囲気で思いついて以下のように変更して試してみました。

.. code-block:: text
    :linenos: table
    :linenostart: 7

    export GOROOT := $(CURDIR)
    export GOCACHE := $(CURDIR)
    export GOROOT_FINAL := /usr/lib/go-$(GOVER)

上記のビルド失敗の出力で
:code:`I: user script /var/cache/pbuilder/build/8740/tmp/hooks/C10shell starting`
と出ているのは
`pbuilderのchroot環境にレポジトリを追加する </blog/2017/09/02/add-repositories-to-pbuilder-chroot-images/>`_
の「ビルド時にエラーになったときに chroot 環境に入る設定」の項の設定をしていたからです。

そこで chroot 環境内で :code:`debian/rules` を上記のように書き換えて、以下のコマンドで再度ビルドを試みました。

.. code-block:: console

    debian/rules build

今度は先ほどひっかかっていた箇所は無事通ってビルドは終わったのですが、その後のテストでひっかかってしまいました。

.. code-block:: text

    make[1]: Entering directory '/build/golang-1.10-1.10~rc1'
    set -ex; \
            cd src; \
            export PATH="/build/golang-1.10-1.10~rc1/bin:$PATH"; \
            eval "$(go tool dist env)"; \
            bash run.bash -k -no-rebuild;
    + cd src
    + export PATH=/build/golang-1.10-1.10~rc1/bin:/usr/sbin:/usr/bin:/sbin:/bin
    + go tool dist env
    + eval GOROOT="/build/golang-1.10-1.10~rc1"
    GOBIN="/build/golang-1.10-1.10~rc1/bin"
    GOARCH="amd64"
    GOOS="linux"
    GOHOSTARCH="amd64"
    GOHOSTOS="linux"
    GOTOOLDIR="/build/golang-1.10-1.10~rc1/pkg/tool/linux_amd64"
    + GOROOT=/build/golang-1.10-1.10~rc1
    + GOBIN=/build/golang-1.10-1.10~rc1/bin
    + GOARCH=amd64
    + GOOS=linux
    + GOHOSTARCH=amd64
    + GOHOSTOS=linux
    + GOTOOLDIR=/build/golang-1.10-1.10~rc1/pkg/tool/linux_amd64
    + bash run.bash -k -no-rebuild

    ##### Testing packages.
    ok      archive/tar     0.044s
    ok      archive/zip     1.872s
    ok      bufio   0.047s
    ok      bytes   0.595s
    ok      compress/bzip2  0.058s
    ok      compress/flate  0.834s
    ok      compress/gzip   0.009s
    ok      compress/lzw    0.005s
    ok      compress/zlib   0.017s
    ok      container/heap  0.012s
    ok      container/list  0.002s
    ok      container/ring  0.019s
    ok      context 0.977s
    ok      crypto  0.001s
    ok      crypto/aes      0.022s
    ok      crypto/cipher   0.011s
    ok      crypto/des      0.007s
    ok      crypto/dsa      0.003s
    ok      crypto/ecdsa    0.147s
    ok      crypto/elliptic 0.035s
    ok      crypto/hmac     0.002s
    ok      crypto/md5      0.002s
    ok      crypto/rand     0.035s
    ok      crypto/rc4      0.080s
    ok      crypto/rsa      0.078s
    ok      crypto/sha1     0.022s
    ok      crypto/sha256   0.007s
    ok      crypto/sha512   0.003s
    ok      crypto/subtle   0.003s
    ok      crypto/tls      0.904s
    ok      crypto/x509     0.901s
    ok      database/sql    0.545s
    ok      database/sql/driver     0.001s
    ok      debug/dwarf     0.007s
    ok      debug/elf       0.022s
    ok      debug/gosym     0.134s
    ok      debug/macho     0.002s
    ok      debug/pe        0.004s
    ok      debug/plan9obj  0.001s
    ok      encoding/ascii85        0.005s
    ok      encoding/asn1   0.003s
    ok      encoding/base32 0.003s
    ok      encoding/base64 0.010s
    ok      encoding/binary 0.012s
    ok      encoding/csv    0.003s
    ok      encoding/gob    0.029s
    ok      encoding/hex    0.002s
    ok      encoding/json   0.416s
    ok      encoding/pem    0.009s
    ok      encoding/xml    0.015s
    ok      errors  0.001s
    ok      expvar  0.003s
    ok      flag    0.004s
    ok      fmt     0.085s
    ok      go/ast  0.003s
    ok      go/build        0.088s
    ok      go/constant     0.011s
    ok      go/doc  0.029s
    ok      go/format       0.007s
    ok      go/importer     0.071s
    ok      go/internal/gccgoimporter       0.008s
    ok      go/internal/gcimporter  0.181s
    ok      go/internal/srcimporter 0.663s
    ok      go/parser       0.029s
    ok      go/printer      0.312s
    ok      go/scanner      0.003s
    ok      go/token        0.016s
    ok      go/types        0.757s
    ok      hash    0.002s
    ok      hash/adler32    0.006s
    ok      hash/crc32      0.011s
    ok      hash/crc64      0.002s
    ok      hash/fnv        0.002s
    ok      html    0.004s
    ok      html/template   0.028s
    ok      image   0.086s
    ok      image/color     0.019s
    ok      image/draw      0.045s
    ok      image/gif       0.437s
    ok      image/jpeg      0.201s
    ok      image/png       0.032s
    ok      index/suffixarray       0.007s
    ok      internal/cpu    0.001s
    ok      internal/poll   0.005s
    ok      internal/singleflight   0.015s
    ok      internal/trace  0.829s
    ok      io      0.022s
    ok      io/ioutil       0.007s
    ok      log     0.011s
    ok      log/syslog      1.214s
    ok      math    0.003s
    ok      math/big        1.796s
    ok      math/bits       0.003s
    ok      math/cmplx      0.002s
    ok      math/rand       0.257s
    ok      mime    0.005s
    ok      mime/multipart  0.405s
    ok      mime/quotedprintable    0.130s
    ok      net     1.931s
    ok      net/http        6.404s
    ok      net/http/cgi    0.304s
    ok      net/http/cookiejar      0.006s
    ok      net/http/fcgi   0.004s
    ok      net/http/httptest       0.019s
    ok      net/http/httptrace      0.003s
    ok      net/http/httputil       0.049s
    ok      net/http/internal       0.002s
    ok      net/internal/socktest   0.002s
    ok      net/mail        0.016s
    ok      net/rpc 0.022s
    ok      net/rpc/jsonrpc 0.006s
    ok      net/smtp        0.008s
    ok      net/textproto   0.005s
    ok      net/url 0.004s
    ok      os      0.615s
    ok      os/exec 0.457s
    ok      os/signal       4.619s
    ok      os/user 0.003s
    ok      path    0.002s
    ok      path/filepath   0.009s
    ok      reflect 0.101s
    ok      regexp  0.111s
    ok      regexp/syntax   0.345s
    ok      runtime 22.006s
    ok      runtime/debug   0.006s
    ok      runtime/internal/atomic 0.056s
    ok      runtime/internal/sys    0.012s
    ok      runtime/pprof   3.213s
    ok      runtime/pprof/internal/profile  0.016s
    ok      runtime/trace   3.187s
    ok      sort    0.104s
    ok      strconv 0.825s
    ok      strings 0.145s
    ok      sync    0.185s
    ok      sync/atomic     0.081s
    --- FAIL: TestUnshareMountNameSpace (0.02s)
            exec_linux_test.go:345: unshare failed: , fork/exec /tmp/go-build208380392/b645/syscall.test: invalid argument
    --- FAIL: TestUnshareMountNameSpaceChroot (2.10s)
            exec_linux_test.go:404: unshare failed: , fork/exec /syscall.test: invalid argument
    FAIL
    FAIL    syscall 2.169s
    ok      testing 0.805s
    ok      testing/quick   0.107s
    ok      text/scanner    0.002s
    ok      text/tabwriter  0.010s
    ok      text/template   0.298s
    ok      text/template/parse     0.006s
    ok      time    2.587s
    ok      unicode 0.013s
    ok      unicode/utf16   0.002s
    ok      unicode/utf8    0.003s
    ok      vendor/golang_org/x/crypto/chacha20poly1305     0.141s
    ok      vendor/golang_org/x/crypto/chacha20poly1305/internal/chacha20   0.001s
    ok      vendor/golang_org/x/crypto/cryptobyte   0.003s
    ok      vendor/golang_org/x/crypto/curve25519   0.020s
    ok      vendor/golang_org/x/crypto/poly1305     0.001s
    ok      vendor/golang_org/x/net/http2/hpack     0.004s
    ok      vendor/golang_org/x/net/idna    0.002s
    ok      vendor/golang_org/x/net/lex/httplex     0.002s
    ok      vendor/golang_org/x/net/nettest 1.177s
    ok      vendor/golang_org/x/net/proxy   0.003s
    ok      vendor/golang_org/x/text/transform      0.002s
    ok      vendor/golang_org/x/text/unicode/norm   0.002s
    ok      cmd/addr2line   1.309s
    ok      cmd/api 0.005s
    ok      cmd/asm/internal/asm    0.268s
    ok      cmd/asm/internal/lex    0.002s
    ok      cmd/compile     7.194s
    ok      cmd/compile/internal/gc 36.331s
    ok      cmd/compile/internal/ssa        0.101s
    ok      cmd/compile/internal/syntax     0.017s
    ok      cmd/compile/internal/test       0.016s [no tests to run]
    ok      cmd/compile/internal/types      0.028s
    ok      cmd/cover       1.274s
    ok      cmd/doc 0.093s
    ok      cmd/fix 1.907s
    ok      cmd/go  43.690s
    ok      cmd/go/internal/cache   0.531s
    ok      cmd/go/internal/generate        0.002s
    ok      cmd/go/internal/get     0.008s
    ok      cmd/go/internal/load    0.004s
    ok      cmd/go/internal/work    0.003s
    ok      cmd/gofmt       0.040s
    ok      cmd/internal/buildid    0.189s
    ok      cmd/internal/dwarf      0.001s
    ok      cmd/internal/edit       0.001s
    ok      cmd/internal/goobj      0.360s
    ok      cmd/internal/obj        0.001s
    ok      cmd/internal/obj/arm64  0.001s
    ok      cmd/internal/obj/x86    0.251s
    ok      cmd/internal/objabi     0.013s
    ok      cmd/internal/src        0.002s
    ok      cmd/internal/test2json  0.102s
    ok      cmd/link        0.430s
    ok      cmd/link/internal/ld    44.080s
    ok      cmd/nm  3.856s
    ok      cmd/objdump     2.208s
    ok      cmd/pack        2.345s
    ok      cmd/trace       0.006s
    ok      cmd/vendor/github.com/google/pprof/internal/binutils    0.031s
    ok      cmd/vendor/github.com/google/pprof/internal/driver      12.204s
    ok      cmd/vendor/github.com/google/pprof/internal/elfexec     0.001s
    ok      cmd/vendor/github.com/google/pprof/internal/graph       0.010s
    ok      cmd/vendor/github.com/google/pprof/internal/measurement 0.002s
    ok      cmd/vendor/github.com/google/pprof/internal/report      0.079s
    ok      cmd/vendor/github.com/google/pprof/internal/symbolizer  0.004s
    ok      cmd/vendor/github.com/google/pprof/internal/symbolz     0.004s
    ok      cmd/vendor/github.com/google/pprof/profile      0.046s
    ok      cmd/vendor/github.com/ianlancetaylor/demangle   0.015s
    ok      cmd/vendor/golang.org/x/arch/arm/armasm 0.007s
    ok      cmd/vendor/golang.org/x/arch/arm64/arm64asm     0.072s
    ok      cmd/vendor/golang.org/x/arch/ppc64/ppc64asm     0.002s
    ok      cmd/vendor/golang.org/x/arch/x86/x86asm 0.067s
    ok      cmd/vet 1.567s
    ok      cmd/vet/internal/cfg    0.002s
    2018/01/26 14:46:50 Failed: exit status 1

    ##### GOMAXPROCS=2 runtime -cpu=1,2,4 -quick
    ok      runtime 14.556s

    ##### cmd/go terminal test
    PASS
    ok      _/build/golang-1.10-1.10~rc1/src/cmd/go/testdata/testterminal18153      0.001s

    ##### Testing without libgcc.
    ok      crypto/x509     1.875s
    ok      net     0.042s
    ok      os/user 0.018s

    ##### internal linking of -buildmode=pie
    ok      reflect 2.078s

    ##### sync -cpu=10
    ok      sync    0.391s

    ##### Testing race detector
    ok      runtime/race    22.385s
    ok      flag    1.035s
    ok      os      1.085s
    ok      os/exec 3.085s
    ok      encoding/gob    1.033s
    PASS
    scatter = 0x60c450
    hello from C
    sqrt is: 0
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/test      5.404s
    ok      flag    1.033s
    ok      os/exec 3.055s

    ##### ../misc/cgo/stdio

    ##### ../misc/cgo/life

    ##### ../misc/cgo/test
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/test      1.943s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/test      2.266s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/test      2.087s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/testtls   0.011s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/testtls   0.012s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/testtls   0.026s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/nocgo     0.001s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/nocgo     0.024s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/nocgo     0.001s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/test      2.000s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/testtls   0.014s
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/nocgo     0.013s

    ##### ../misc/cgo/testgodefs

    ##### ../misc/cgo/testso

    ##### ../misc/cgo/testsovar

    ##### ../misc/cgo/testcarchive
    PASS

    ##### ../misc/cgo/testcshared
    PASS

    ##### ../misc/cgo/testshared
    PASS
    ok      _/build/golang-1.10-1.10~rc1/misc/cgo/testshared        25.360s

    ##### ../misc/cgo/testplugin
    PASS
    something

    ##### ../misc/cgo/testasan

    ##### ../misc/cgo/testsanitizers
    PASS

    ##### ../misc/cgo/errors
    PASS

    ##### ../misc/cgo/testsigfwd

    ##### ../test/bench/go1
    testing: warning: no tests to run
    PASS
    ok      _/build/golang-1.10-1.10~rc1/test/bench/go1     4.439s

    ##### ../test

    ##### API check
    Go version is "go1.10rc1", ignoring -next /build/golang-1.10-1.10~rc1/api/next.txt

    FAILED
    debian/rules:62: recipe for target 'override_dh_auto_test-arch' failed
    make[1]: *** [override_dh_auto_test-arch] Error 1
    make[1]: Leaving directory '/build/golang-1.10-1.10~rc1'
    debian/rules:27: recipe for target 'build' failed
    make: *** [build] Error 2

:code:`unshare failed` というエラーが2か所出ています。おそらく chroot 環境内ではうまく動かないのだろうと推測してテスト対象外にすることにします。

失敗しているテスト :code:`TestUnshareMountNameSpace` と :code:`TestUnshareMountNameSpaceChroot` のコードは
https://github.com/golang/go/blob/go1.10rc1/src/syscall/exec_linux_test.go#L314-L425
です。共に先頭で :code:`skipInContainer(t)` という関数を呼んでいます。

実装を見てみると以下のようになっていました。
https://github.com/golang/go/blob/go1.10rc1/src/syscall/exec_linux_test.go#L26-L42

.. code-block:: go
    :linenos: table
    :linenostart: 26

    func isDocker() bool {
        _, err := os.Stat("/.dockerenv")
        return err == nil
    }

    func isLXC() bool {
        return os.Getenv("container") == "lxc"
    }

    func skipInContainer(t *testing.T) {
        if isDocker() {
            t.Skip("skip this test in Docker container")
        }
        if isLXC() {
            t.Skip("skip this test in LXC container")
        }
    }

というわけで :code:`debian/rules` の先頭のほうを以下のように変えることにしました。

.. code-block:: text
    :linenos: table
    :linenostart: 7

    export GOROOT := $(CURDIR)
    export GOROOT_FINAL := /usr/lib/go-$(GOVER)

    # NOTE: Set GOCACHE environment variable to avoid the following error.
    #   initializing cache in $GOCACHE: mkdir /nonexistent: permission denied
    # See https://github.com/golang/go/blob/go1.10rc1/src/cmd/go/internal/cache/default.go#L35-L55
    export GOCACHE := $(CURDIR)

    # NOTE: Set container environment variable to skip tests which fail in pbuilder chroot.
    # See https://github.com/golang/go/blob/go1.10rc1/src/syscall/exec_linux_test.go#L26-L42
    export container = lxc

これで再度以下のコマンドでビルドしてみると今度は無事にビルドできました。

.. code-block:: console

    debian/rules build

Ctrl-D を押してpbuilderのchroot環境を抜け、 :code:`debian/rules` を上記の通り変更してコミットしてソースパッケージを作り直して再度ビルドしました。

コミット後の差分は以下の通りです。

.. code-block:: console

    $ git diff HEAD~
    diff --git a/debian/rules b/debian/rules
    index b6d44ae..20751cf 100755
    --- a/debian/rules
    +++ b/debian/rules
    @@ -7,6 +7,15 @@ export GOVER := $(shell perl -w -mDpkg::Version -e 'Dpkg::Version->new(`dpkg-par
     export GOROOT := $(CURDIR)
     export GOROOT_FINAL := /usr/lib/go-$(GOVER)

    +# NOTE: Set GOCACHE environment variable to avoid the following error.
    +#   initializing cache in $GOCACHE: mkdir /nonexistent: permission denied
    +# See https://github.com/golang/go/blob/go1.10rc1/src/cmd/go/internal/cache/default.go#L35-L55
    +export GOCACHE := $(CURDIR)
    +
    +# NOTE: Set container environment variable to skip tests which fail in pbuilder chroot.
    +# See https://github.com/golang/go/blob/go1.10rc1/src/syscall/exec_linux_test.go#L26-L42
    +export container = lxc
    +
     DEB_HOST_ARCH := $(shell dpkg-architecture -qDEB_HOST_ARCH 2>/dev/null)
     RUN_TESTS := true
     # armel: ???

Local symbolizationが失敗
-------------------------

再度のビルドで今度はまた別のエラーが出ました。

.. code-block:: console

       dh_auto_build -Ngolang-1.10-go -Ngolang-1.10-src -Nlibgolang-1.10-std1 -Ngolang-1.10-go-shared-dev
       debian/rules override_dh_auto_test-arch
    make[1]: Entering directory '/build/golang-1.10-1.10~rc1'
    set -ex; \
            cd src; \
            export PATH="/build/golang-1.10-1.10~rc1/bin:$PATH"; \
            eval "$(go tool dist env)"; \
            bash run.bash -k -no-rebuild;
    + cd src
    + export PATH=/build/golang-1.10-1.10~rc1/bin:/usr/sbin:/usr/bin:/sbin:/bin
    + go tool dist env
    + eval GOROOT="/build/golang-1.10-1.10~rc1"
    GOBIN="/build/golang-1.10-1.10~rc1/bin"
    GOARCH="amd64"
    GOOS="linux"
    GOHOSTARCH="amd64"
    GOHOSTOS="linux"
    GOTOOLDIR="/build/golang-1.10-1.10~rc1/pkg/tool/linux_amd64"
    + GOROOT=/build/golang-1.10-1.10~rc1
    + GOBIN=/build/golang-1.10-1.10~rc1/bin
    + GOARCH=amd64
    + GOOS=linux
    + GOHOSTARCH=amd64
    + GOHOSTOS=linux
    + GOTOOLDIR=/build/golang-1.10-1.10~rc1/pkg/tool/linux_amd64
    + bash run.bash -k -no-rebuild

    ##### Testing packages.
    ok      archive/tar     0.053s
    ok      archive/zip     1.973s

    ...(略)...

    Local symbolization failed for cppbench_server_main: stat cppbench_server_main: no such file or directory
    Local symbolization failed for libpthread-2.15.so: stat /libpthread-2.15.so: no such file or directory
    Some binary filenames not available. Symbolization may be incomplete.
    Try setting PPROF_BINARY_PATH to the search path for local binaries.
    --- FAIL: TestHttpsInsecure (10.03s)
            proftest.go:114: Could not use temp dir /nonexistent/pprof: mkdir /nonexistent: permission denied
    FAIL
    FAIL    cmd/vendor/github.com/google/pprof/internal/driver      12.171s


/usr/lib/go-1.6/pkg/tool/linux_amd64/pprof


override_dh_auto_build-arch:
        [ -f VERSION ] || echo "debian snapshot +$$(dpkg-parsechangelog -SVersion)" > VERSION
        export GOROOT_BOOTSTRAP=$$(env -i go env GOROOT) \
                && cd src \
                && $(CURDIR)/debian/helpers/goenv.sh \
                        bash ./make.bash --no-banner
        $(CURDIR)/bin/go install -v -buildmode=shared \
                -ldflags '-extldflags "-Wl,-soname=libgolang-$(GOVER)-std.so.1"' \
                std


https://github.com/golang/go/blob/go1.10rc1/src/cmd/vendor/github.com/google/pprof/internal/driver/fetch.go#L283-L303

.. code-block:: go
    :linenos: table
    :linenostart: 283

    // setTmpDir prepares the directory to use to save profiles retrieved
    // remotely. It is selected from PPROF_TMPDIR, defaults to $HOME/pprof, and, if
    // $HOME is not set, falls back to os.TempDir().
    func setTmpDir(ui plugin.UI) (string, error) {
        var dirs []string
        if profileDir := os.Getenv("PPROF_TMPDIR"); profileDir != "" {
            dirs = append(dirs, profileDir)
        }
        if homeDir := os.Getenv(homeEnv()); homeDir != "" {
            dirs = append(dirs, filepath.Join(homeDir, "pprof"))
        }
        dirs = append(dirs, os.TempDir())
        for _, tmpDir := range dirs {
            if err := os.MkdirAll(tmpDir, 0755); err != nil {
                ui.PrintErr("Could not use temp dir ", tmpDir, ": ", err.Error())
                continue
            }
            return tmpDir, nil
        }
        return "", fmt.Errorf("failed to identify temp dir")
    }


https://github.com/golang/go/blob/go1.10rc1/src/syscall/exec_linux_test.go#L44-L53

.. code-block:: go
    :linenos: table
    :linenostart: 44

    // Check if we are in a chroot by checking if the inode of / is
    // different from 2 (there is no better test available to non-root on
    // linux).
    func isChrooted(t *testing.T) bool {
        root, err := os.Stat("/")
        if err != nil {
            t.Fatalf("cannot stat /: %v", err)
        }
        return root.Sys().(*syscall.Stat_t).Ino != 2
    }



hnakamur@express:~/.ghq/github.com/hnakamur/golang-deb$ gbp pq switch
gbp:info: Switching to 'patch-queue/ubuntu-1.10'

