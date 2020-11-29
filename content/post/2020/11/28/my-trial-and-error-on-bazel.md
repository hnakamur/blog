---
title: "Bazel で試行錯誤したときのメモ"
date: 2020-11-28T22:32:54+09:00
---

## はじめに

[envoyproxy/envoy: Cloud-native high-performance edge/middle/service proxy](https://github.com/envoyproxy/envoy) がビルドツールとして
[Bazel - a fast, scalable, multi-language and extensible build system" - Bazel](https://www.bazel.build/) を使っているので少し慣れておこうと2日ぐらい試行錯誤してみたメモです。

具体的には
[A Universal I/O Abstraction for C++ | cor3ntin](https://cor3ntin.github.io/posts/iouring/)
で紹介されている
[facebookexperimental/libunifex: Unified Executors](https://github.com/facebookexperimental/libunifex) のサンプルのビルドを試しました。

libunifex 本家では cmake で libunifex 本体とサンプルをビルドするようになっていますが、 Bazel の勉強のためあえて Bazel でトライしてみました。
現状は libunifex が依存している [axboe/liburing](https://github.com/axboe/liburing) と libunifex 自体のビルドまでは一応できた（正しくビルドできたとは言っていない）けど、サンプルのビルドは出来ていません。が、今回はこのへんで止めようと思い、将来再度試すときのためにメモを残しておきます。

試したファイルは
[github.com/hnakamur/libunifex_bazel](https://github.com/hnakamur/libunifex_bazel) に残しておきます。

## Bazel のインストール

[bazelbuild/bazel: a fast, scalable, multi-language and extensible build system](https://github.com/bazelbuild/bazel) は主に Java で書かれています。

[Installing Bazel on Ubuntu - Bazel 3.7.0](https://docs.bazel.build/versions/3.7.0/install-ubuntu.html) を参考にして以下のようにインストールしました。

```console
sudo apt install curl gnupg
curl -fsSL https://bazel.build/bazel-release.pub.gpg | gpg --dearmor > bazel.gpg
sudo mv bazel.gpg /etc/apt/trusted.gpg.d/
echo "deb [arch=amd64] https://storage.googleapis.com/bazel-apt stable jdk1.8" | sudo tee /etc/apt/sources.list.d/bazel.list
```

```console
sudo apt update && sudo apt install bazel
```

これで bazel 3.7.1 が入りました。
[Releases · bazelbuild/bazel](https://github.com/bazelbuild/bazel/releases) の最新です。

"Step 3: Install a JDK (optional)" には Bazel はプライベートな JRE (Java Runtime Environment) を同梱していると書いてあったのでそれを使うことにして JDK (Java Development Kit) のインストールはスキップしました。

## Bazel の概要を把握して C++ のチュートリアルを試す

ドキュメントのページの左上のドロップダウンで Bazel のバージョンが選択できます。
ググってヒットしたドキュメントページの Bazel のバージョンが古い場合はこれで切り替えます。

まず
[Bazel Overview - Bazel](https://docs.bazel.build/versions/master/bazel-overview.html)
と
[Bazel vision - Bazel](https://docs.bazel.build/versions/master/bazel-vision.html)
を見ました。

再現可能なビルド (reproducible build) を目指していて、ビルド対象のライブラリーのバージョンやコンパイラーツールチェインなどの入力全体を制御すれば出力であるビルド結果は同じものになるはずなのでそれをサーバーで共有すれば他のチームメンバーではビルドせずに結果を使えるといったあたりがウリのようです。

次に
[Build Tutorial - C++ - Bazel](https://docs.bazel.build/versions/master/tutorial/cpp.html)
を試しました。

## Bazel のドキュメントのメモ

他のドキュメントもいろいろ読みましたが、古いバージョンの記法が非推奨になって新しい記法に移行中というのがちょくちょくあるので要注意だなと思いました。

そのうちの1つが toolchain です。C++ で GCC や LLVM のどのツールを使うかを指定するのに使うもののようですが [C++ toolchain configuration - Bazel](https://docs.bazel.build/versions/master/cc-toolchain-config-reference.html) の `--cpu`, `--compiler`, `--crosstool_top` で切り替えるのは旧式らしく、
[Toolchains - Bazel](https://docs.bazel.build/versions/master/toolchains.html) と [Platforms - Bazel](https://docs.bazel.build/versions/master/platforms.html) が新しい仕組みのようです。

[Building with platforms - Bazel](https://docs.bazel.build/versions/master/platforms-intro.html) にも Android や iOS のプロジェクトではまだ `--cpu` と `--crosstool_top` で切り替える方式を使っているとありました（masterのリンクだと将来変わるかもしれないので、その場合は [Building with platforms - Bazel 3.7.0](https://docs.bazel.build/versions/3.7.0/platforms-intro.html) を参照）。

もう1つが [Workspace Rules - Bazel](https://docs.bazel.build/versions/master/be/workspace.html) の `bind` です。

Warning: use of bind() is not recommended. See "Consider removing bind" for a long discussion of its issues and alternatives.

という警告が書かれていて [Consider removing bind() · Issue #1952 · bazelbuild/bazel](https://github.com/bazelbuild/bazel/issues/1952) を見てみると
[We have no plans to deprecate bind.](https://github.com/bazelbuild/bazel/issues/1952#issuecomment-629113959) というコメントがあるので deprecated にはしないようです。

他にもいろいろありそうです。

ちなみに envoy は [bazel](https://github.com/envoyproxy/envoy/tree/master/bazel) ディレクトリーに大量に `.bzl` ファイルがあるのですが、その中で `native.bind` を多用していました。

[envoy/bazel at v1.16.1 · envoyproxy/envoy](https://github.com/envoyproxy/envoy/tree/v1.16.1/bazel)

## Bazel を使ってない外部プロジェクトの利用には `rules_foreign_cc` が便利

外部プロジェクトの扱いについては
[External dependencies - Bazel](https://docs.bazel.build/versions/master/external.html)
に書いてあります。
"Depending on non-Bazel projects" の項を見ると、外部プロジェクト用の `BUILD` ファイルを書くのがあるべき姿のようです。

が、外部プロジェクトが configure + make だったり cmake を採用している場合に、自前で Bazel の `BUILD` ファイル書くのも大変だよなあと思って検索すると
[bazelbuild/rules_foreign_cc: Build rules for interfacing with "foreign" (non-Bazel) build systems (CMake, configure-make, GNU Make, boost)](https://github.com/bazelbuild/rules_foreign_cc)
というのがありました。
ただし、これは公式にサポートされる Google のプロダクトではないので、サポートが限定的だったり新しいリリースが出ない可能性があるとのことです。

ドキュメントは README にあるだけですが、 examples ディレクトリーに例がたくさんあります。

configure + make を使っているプロジェクトには `configure_make` を、 cmake を使っているプロジェクトには `cmake_external` が使えます。

envoy でも `rules_foreign_cc` を使っていますが  `cmake_external` を Starlark で書かれた `.bzl` ファイルでラップして独自の `envoy_cmake_external` を定義していたりします。

### cofigure + make で configure の前に独自コマンドを実行するには `make` の `make_commands` を使う

検索してたら
[autotools - Bazel for packages with a "bootstrap->configure->make" build? - Stack Overflow](https://stackoverflow.com/questions/60048460/bazel-for-packages-with-a-bootstrap-configure-make-build) の回答で知りました。

`configure_make` ではなく `make` を使いつつ `make_commands` に実行したいコマンドや `configure` を実行するコマンドを並べて書くという技を使えば良いそうです。

```text
make(
    name = "libhttpserver",
    lib_source = "@libhttpserver//:all",
    make_commands = [
        "./bootstrap",
        "mkdir build_dir",
        "cd build_dir",
        "../configure --prefix=${INSTALLDIR}",
        "make",
        "make install",
    ],
    deps = [":libmicrohttpd", ":libgnutls"],
)
```

この回答者の方が作った
[megamegabits/libhttpserver-bazel-example: Example for building libhttpserver with Bazel.](https://github.com/megamegabits/libhttpserver-bazel-example)
は、実際に動く例として非常に参考になりました。ただし、依存関係で各種の `*-dev` パッケージが必要だったのでエラーになるたびに `sudo apt install` でインストールしました。

## ビルドがうまく行かないときの調査方法

### bazel build のオプション

* [`--subcommands` オプション](https://docs.bazel.build/versions/master/command-line-reference.html#flag--subcommands) 。ショートオプションは `-s`。これを指定すると各ステップで実行するコマンドが出力されます。
* [`--sandbox_debug` オプション](https://docs.bazel.build/versions/master/command-line-reference.html#flag--sandbox_debug)。 sandbox 環境でビルドする際の中間ディレクトリは通常はビルドエラー時も消されてしまうのですが、このオプションを指定すれば残るので後から中身を確認できます。
* [`--verbose_failures` オプション](https://docs.bazel.build/versions/master/command-line-reference.html#flag--verbose_failures)

うまく行かないときはこれらのオプションを使って以下のような感じで毎回クリーンビルドしていました（対象のラベルは適宜変更してください）。

```console
bazel clean && bazel build -s --sandbox_debug --verbose_failures //src:your_target_here
```

### `rules_foreign_cc` で生成されるスクリプトとエラーログ

`configure_make` を使った設定でエラーが起きるといろいろメッセージが出ますが、その中に

```console
rules_foreign_cc: Build script location: bazel-out/k8-fastbuild/bin/src/liburing/logs/Configure_script.sh
rules_foreign_cc: Build log location: bazel-out/k8-fastbuild/bin/src/liburing/logs/Configure.log
```

とか

```console
export BUILD_SCRIPT="bazel-out/k8-fastbuild/bin/src/liburing/logs/Configure_script.sh"
export BUILD_LOG="bazel-out/k8-fastbuild/bin/src/liburing/logs/Configure.log"
```

というのが出ます。このログファイルの最後の方に具体的なエラーが出ていたので、これを見て対処します。

例えば上記の
[megamegabits/libhttpserver-bazel-example: Example for building libhttpserver with Bazel.](https://github.com/megamegabits/libhttpserver-bazel-example)
では configure 時にライブラリが見つからないというエラーが出たので、対応する Ubuntu のパッケージを調べてインストールして再実行し、また別のライブラリが無いと言われたらインストールしを繰り返すと最終的にはビルド成功しました。

ついでに生成されたスクリプトの例の抜粋を貼っておきます。

```
export EXT_BUILD_ROOT=$(pwd)
export BUILD_TMPDIR=$(mktemp -d)
export EXT_BUILD_DEPS=$(mktemp -d)
export INSTALLDIR=$EXT_BUILD_ROOT/bazel-out/k8-fastbuild/bin/liburing
export PATH="$EXT_BUILD_ROOT:$PATH"
mkdir -p $INSTALLDIR
printf "Environment:______________\n"
env
printf "__________________________\n"
children_to_path $EXT_BUILD_DEPS/bin
export PATH="$EXT_BUILD_DEPS/bin:$PATH"
cd $BUILD_TMPDIR
export INSTALL_PREFIX="liburing"

echo "PKG_CONFIG_PATH=$PKG_CONFIG_PATH"
CFLAGS="-U_FORTIFY_SOURCE -fstack-protector -Wall -Wunused-but-set-parameter -Wno-free-nonheap-object -fno-omit-frame-pointer -fno-canonical-system-headers -Wno-builtin-macro-redefined -D__DATE__=\"redacted\" -D__TIMESTAMP__=\"redacted\" -D__TIME__=\"redacted\"" CXXFLAGS="-U_FORTIFY_SOURCE -fstack-protector -Wall -Wunused-but-set-parameter -Wno-free-nonheap-object -fno-omit-frame-pointer -std=c++0x -fno-canonical-system-headers -Wno-builtin-macro-redefined -D__DATE__=\"redacted\" -D__TIMESTAMP__=\"redacted\" -D__TIME__=\"redacted\"" ARFLAGS="rcsD" ASFLAGS="-U_FORTIFY_SOURCE -fstack-protector -Wall -Wunused-but-set-parameter -Wno-free-nonheap-object -fno-omit-frame-pointer -fno-canonical-system-headers -Wno-builtin-macro-redefined -D__DATE__=\"redacted\" -D__TIMESTAMP__=\"redacted\" -D__TIME__=\"redacted\"" LDFLAGS="-fuse-ld=gold -Wl,-no-as-needed -Wl,-z,relro,-z,now -B/usr/bin -pass-exit-codes -lstdc++ -lm" CC="/usr/bin/gcc" CXX="/usr/bin/gcc" AR="/usr/bin/ar" CPPFLAGS="" "$EXT_BUILD_ROOT/external/liburing/configure" --prefix=$BUILD_TMPDIR/$INSTALL_PREFIX
make
make install
```

このスクリプトの内容は
[tools/build_defs/framework.bzl#L231-L268](https://github.com/bazelbuild/rules_foreign_cc/blob/d54c78ab86b40770ee19f0949db9d74a831ab9f0/tools/build_defs/framework.bzl#L231-L268) あたりで生成しています。

### `rules_foreign_cc` の Starlark を print デバッグ

[Need Tutorial about Using the Starlark Debugger · Issue #184 · bazelbuild/vscode-bazel](https://github.com/bazelbuild/vscode-bazel/issues/184) や [Bazel - Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=BazelBuild.vscode-bazel&ssr=false#overview) を見ると Starlark のデバッガーもあるようなのですが、私はたいていのケースでは print デバッグのほうが好きなので、その方法を探りました。

まず `WORKSPACE` で `rules_foreign_cc` を `http_archive` で取得するのを止めて `local_repository` にします。

変更前の `WORKSPACE` 抜粋。

```
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "rules_foreign_cc",
    strip_prefix = "rules_foreign_cc-master",
    url = "https://github.com/bazelbuild/rules_foreign_cc/archive/master.tar.gz",
)

load("@rules_foreign_cc//:workspace_definitions.bzl", "rules_foreign_cc_dependencies")

rules_foreign_cc_dependencies()
```

変更後の `WORKSPACE` 抜粋。 path は環境に応じて適宜調整してください。指定した path に `git clone https://github.com/bazelbuild/rules_foreign_cc` で配置しておきます。

```
local_repository(
    name = "rules_foreign_cc",
    path = "../../bazelbuild/rules_foreign_cc",
)

load("@rules_foreign_cc//:workspace_definitions.bzl", "rules_foreign_cc_dependencies")

rules_foreign_cc_dependencies()
```

上記の path で指定した `rules_foreign_cc` の `.bzl` ファイルを改変して `print` 文を埋め込むと `bazel build` 実行時の出力に DEBUG ログとして出てきました。

また上記のスクリプト生成箇所をいじって `ls` などを実行するように追加して `configure` 前後でファイルが存在するかをみたりしました。

## ハマったネタと回避策

### 対象のレポジトリで直接 `configure_make` を使うとconfigure呼び出し時のパスが変 → 別のレポジトリで `http_archive` で参照

最初 [axboe/liburing](https://github.com/axboe/liburing) を `git clone` したディレクトリーに `WORKSPACE` と `BUILD` ファイルを作って試していたのですが、生成されるスクリプトで `configure` を実行するときの `configure` のパスがおかしくなるという現象が起きました。

フルパスで `configure` を呼び出しているのですが、レポジトリ内のファイルをディレクトリーと誤認識してその下の `configure` というパスになっていました。具体的には `"$EXT_BUILD_ROOT/config-host.h/configure"` のような感じです。

`configure_make` の `source` に指定したソースファイル名群から
[tools/build_defs/detect_root.bzl](https://github.com/bazelbuild/rules_foreign_cc/blob/master/tools/build_defs/detect_root.bzl) の `detect_root` 関数で
ルートディレクトリーを判定しているのですが、これが上記の構成で使うことは想定していないようです。

回避策というかたぶん正しい使い方は、プロジェクト用のディレクトリーを別に作ってそちらから `http_archive` で対象のプロジェクトを参照することです。
`rules_foreign_cc` と名前に foreign が入っているぐらいなので外部レポジトリーを参照する想定なのでしょう。

こうすると参照するプロジェクト用にサブディレクトリーが切られるので `detect_root` が正しく機能するようになります。
具体的には `"$EXT_BUILD_ROOT/external/liburing/configure"` のようなパスになります。

### ソースとは別のディレクトリーで `configure` が実行されるためエラーが起きるケースがある → `configure_in_place` を `True` に設定する

`configure_make` で生成されるスクリプトではビルドする際のソースのディレクトリー  `$EXT_BUILD_ROOT` とは別の作業ディレクトリー `$BUILD_TMPDIR` で configure, make を実行します。

[megamegabits/libhttpserver-bazel-example: Example for building libhttpserver with Bazel.](https://github.com/megamegabits/libhttpserver-bazel-example) の `libgnutls` などはそれでも configure, make が実行できるのですが、 `liburing` では configure でサブディレクトリーにヘッダーファイルを生成しようとしてディレクトリーがないためエラーになりました（個人的には configure, make をソースディレクトリーと別の場所で実行するという発想はなかったです）。

`configure_make` の
[configure_in_place](https://github.com/bazelbuild/rules_foreign_cc/blob/d54c78ab86b40770ee19f0949db9d74a831ab9f0/tools/build_defs/configure.bzl#L94-L96)
を `True` に設定すれば、エラー無く configure, make が実行できました。

## サンプルのビルドがエラーになるのは未解決

大量にコンパイルエラーが出たのですが、最初のエラーはこれです。

```
In file included from bazel-out/k8-fastbuild/bin/src/libunifex/include/unifex/linux/io_uring_context.hpp:33,
                 from src/io_uring_test.cpp:24:
bazel-out/k8-fastbuild/bin/src/libunifex/include/unifex/linux/monotonic_clock.hpp:182:60: error: missing terminating ' character
  182 |   constexpr std::int64_t nanoseconds_per_second = 1'000'000'000;
      |                                                            ^~~~~
```

[数値リテラルの桁区切り文字 - cpprefjp C++日本語リファレンス](https://cpprefjp.github.io/lang/cpp14/digit_separators.html) を認識できていないということでビルドに使っているコンパイラーとC++標準のバージョン指定を修正する必要がありそうです。

が、このへんで疲れてきて
[CMake vs Meson vs Bazel ? : cpp](https://www.reddit.com/r/cpp/comments/eppqhj/cmake_vs_meson_vs_bazel/)
や
[CMake vs Bazel | Daniel Galvez’s Website](http://danielgalvez.me/jekyll/update/2018/01/12/CMake-vs.-Bazel.html)
や
[Bazel, CMake - 調べる - Google トレンド](https://trends.google.co.jp/trends/explore?q=%2Fg%2F11bzyq50jp,%2Fm%2F0cxh7f)
を見て C++ に関しては当面は cmake を勉強するほうが良さそうかなあと思ったので、今回はここで止めることにしました。

## toolchain について

最後に試してないけどメモだけ。

[bazelbuild/bazel-toolchains: Repository that hosts Bazel toolchain configs for remote execution and related support tools.](https://github.com/bazelbuild/bazel-toolchains) の [configs/ubuntu16_04_clang/11.0.0/bazel_3.7.1](https://github.com/bazelbuild/bazel-toolchains/tree/master/configs/ubuntu16_04_clang/11.0.0/bazel_3.7.1) に Ubuntu 16.04 LTS 上で bazel 3.7.1 を使って LLVM clang 11.0.0 を toolchain として使うための設定があるのを見つけました。これを参考に改変していけば指定のコンパイラーを使うのは出来そうな雰囲気です。
