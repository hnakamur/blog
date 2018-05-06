Ubuntuでsnapを使って最新バージョンのgoをインストール
####################################################

:date: 2018-05-06 15:10
:tags: ubuntu, snap, go
:category: blog
:slug: 2018/05/06/install-latest-version-of-golang-using-snap-on-ubuntu

結論
====

私が今後あちこちの環境でインストールすることになるので結論を先にメモしておきます。

Ubuntuでsnapを使ってgo 1.10.xの最新版をインストールするには以下のコマンドを実行すればOKです。

.. code-block:: console

        $ sudo snap install --channel=1.10/stable --classic go

背景
====

Ubuntu 18.04をリリースしてすぐに試してみたところ、aptでgoの1.10.1がインストールできました。その後 2018-05-01 に 1.10.2 がリリースされました (`Release History - The Go Programming Language <https://golang.org/doc/devel/release.html>`_ 参照)が、2018-05-16時点ではaptでインストールできるdebパッケージは1.10.1のままでした。

.. code-block:: console

        $ apt show golang-1.10 | head -10

        WARNING: apt does not have a stable CLI interface. Use with caution in scripts.

        Package: golang-1.10
        Version: 1.10.1-1ubuntu2
        Priority: optional
        Section: devel
        Origin: Ubuntu
        Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
        Original-Maintainer: Go Compiler Team <pkg-golang-devel@lists.alioth.debian.org>
        Bugs: https://bugs.launchpad.net/ubuntu/+filebug
        Installed-Size: 86.0 kB
        Depends: golang-1.10-doc (>= 1.10.1-1ubuntu2), golang-1.10-go (>= 1.10.1-1ubuntu2), golang-1.10-src (>= 1.10.1-1ubuntu2)

一方、snap (`Snapcraft - Snaps are universal Linux packages <https://snapcraft.io/>`_ ) ではチャンネルを選択することで1.10.2がインストール可能でした。ということで手順をメモしておきます。

snapでgoの最新版をインストール
==============================

チャンネルごとのバージョン確認
------------------------------

snapのパッケージは複数のチャンネルを持つことができ、安定版とベータ版を両方インストールしておいて切り替えて使うことができるようです。 `Channels - Snaps are universal Linux packages <https://docs.snapcraft.io/reference/channels>`_ を参照してください。

まずgoパッケージの情報を表示してチャンネル毎のバージョンを確認します。

.. code-block:: console

        $ snap info go
        name:      go
        summary:   Go programming language compiler, linker, stdlib
        publisher: mwhudson
        contact:   michael.hudson@ubuntu.com
        license:   BSD-3-Clause
        description: |
          This snap provides an assembler, compiler, linker, and compiled libraries for the Go programming
          language.
        snap-id: Md1HBASHzP4i0bniScAjXGnOII9cEK6e
        channels:
          stable:         1.10.1        (1688) 66MB classic
          candidate:      ↑
          beta:           ↑
          edge:           devel-5cf3e34 (1904) 77MB classic
          1.10/stable:    1.10.2        (1880) 66MB classic
          1.10/candidate: ↑
          1.10/beta:      ↑
          1.10/edge:      ↑
          1.6/stable:     1.6.4         (122)  49MB classic
          1.6/candidate:  ↑
          1.6/beta:       ↑
          1.6/edge:       ↑
          1.7/stable:     1.7.6         (324)  48MB classic
          1.7/candidate:  ↑
          1.7/beta:       ↑
          1.7/edge:       ↑
          1.8/stable:     1.8.7         (1407) 51MB classic
          1.8/candidate:  ↑
          1.8/beta:       ↑
          1.8/edge:       ↑
          1.9/stable:     1.9.6         (1873) 58MB classic
          1.9/candidate:  ↑
          1.9/beta:       ↑
          1.9/edge:       ↑

デフォルトのstableチャンネルではgoのバージョンは1.10.1ですが、1.10/stableチャンネルなら1.10.2であることがわかります。

(参考) snapのconfinementについて
--------------------------------

1.10/stableチャンネルを指定してgoをインストールしようとすると、以下のエラーが出ました。

.. code-block:: console

        $ sudo snap install --channel=1.10/stable go
        error: This revision of snap "go" was published using classic confinement and thus may perform
               arbitrary system changes outside of the security sandbox that snaps are usually confined to,
               which may put your system at risk.

               If you understand and want to proceed repeat the command including --classic.


classic confinementというのは何だろうと思って検索すると
`How to snap: introducing classic confinement | Ubuntu Insights <https://insights.ubuntu.com/2017/01/09/how-to-snap-introducing-classic-confinement>`_
とそこからリンクされている `Confinement - Snaps are universal Linux packages <https://docs.snapcraft.io/reference/confinement>`_ に説明がありました。

`confinementの意味・用例｜英辞郎 on the WEB：アルク <https://eow.alc.co.jp/search?q=confinement>`_ によるとconfiementは「監禁」や「閉じ込め」という意味です。

snapのパッケージのconfinementはデフォルトではstrictというのになっていて、パッケージが依存するライブラリはすべてバンドルし、パッケージが読み書き可能なディレクトリはsnap用の特定のディレクトリに限定されるようになっているそうです。

一方classic confinementでは従来のdebパッケージのようにシステム全体にフルアクセスが可能とのことです。

go 1.10.xの最新版1.10.2をインストール
-------------------------------------

:code:`snap install` のオプションを確認します。

.. code-block:: console

        $ snap install --help
        Usage:
          snap [OPTIONS] install [install-OPTIONS] <snap>...

        The install command installs the named snap in the system.

        Application Options:
              --version              Print the version and exit

        Help Options:
          -h, --help                 Show this help message

        [install command options]
                  --channel=         Use this channel instead of stable
                  --edge             Install from the edge channel
                  --beta             Install from the beta channel
                  --candidate        Install from the candidate channel
                  --stable           Install from the stable channel
                  --devmode          Put snap in development mode and disable security confinement
                  --jailmode         Put snap in enforced confinement mode
                  --classic          Put snap in classic mode and disable security confinement
                  --revision=        Install the given revision of a snap, to which you must have developer access
                  --dangerous        Install the given snap file even if there are no pre-acknowledged signatures for it, meaning it was not verified and
                                     could be dangerous (--devmode implies this)
                  --unaliased        Install the given snap without enabling its automatic aliases

以下のコマンドで1.10.xの最新版をインストールします。

.. code-block:: console

        sudo snap install --channel=1.10/stable --classic go

インストールしたgoのパスとバージョンを確認すると以下のようになっていました。

.. code-block:: console

        $ which go
        /snap/bin/go
        $ go version
        go version go1.10.2 linux/amd64

(参考) インストール後のチャンネル切り替えはsnap refreshで
---------------------------------------------------------

最初に試したときはまず以下のコマンドで stable チャンネルのgo 1.10.1をインストールしていました。

.. code-block:: console

        sudo snap install --classic go

goのパスとバージョンは以下のとおりです。

ちなみに、aptでもgolangをインストールしているとそちらが優先されます。 :code:`PATH` 環境変数を確認すると :code:`/usr/bin` が :code:`/snap/bin` よりも先に指定されていました。

.. code-block:: console

        $ which go
        /snap/bin/go
        $ go version
        go version go1.10.1 linux/amd64

この状態で :code:`1.10/stable` チャンネルのgoをインストールしようとして以下のコマンドを試してみるとすでにインストール済みなので snap refresh を使うように言われました。

.. code-block:: console

        $ sudo snap install --classic --channel=1.10/stable go
        snap "go" is already installed, see "snap refresh --help"

以下のようにすればインストールして切り替えできました。

.. code-block:: console

        sudo snap refresh --classic --channel=1.10/stable go

.. code-block:: console

        $ which go
        /snap/bin/go
        $ go version
        go version go1.10.2 linux/amd64

godocは別途インストールが必要
=============================

godocを使おうとしたら以下のエラーになり :code:`golang-golang-x-tools` パッケージをインストールすれば使えるとのことでした。

.. code-block:: console

        $ godoc -http=:6060
        The program 'godoc' is currently not installed. You can install it by typing:
        sudo apt install golang-golang-x-tools

2018-05-06時点では :code:`golang-golang-x-tools` パッケージのバージョンは以下のように 2016-03-15時点の
`go/gcimporter15: require go1.6 for binary import/export (fix build) · golang/tools@f42ec61 <https://github.com/golang/tools/commit/f42ec616d3061dd0a453e8f174d62b38eddab928>`_
のコミットに対応したものになっていました。

.. code-block:: console

        $ sudo apt show golang-golang-x-tools | grep ^Version:
        Version: 1:0.0~git20160315.0.f42ec61-2

これより新しい版を使いたい場合は `golang/tools: [mirror] Go Tools <https://github.com/golang/tools>`_ にあるように :code:`go get` でインストールするのが手軽そうです。

.. code-block:: console

        go get -u golang.org/x/tools/...
