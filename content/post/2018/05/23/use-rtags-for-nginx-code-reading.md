+++
title="nginxのコードリーディングにrtagsを使う"
date = "2018-05-23T22:25:00+09:00"
tags = ["ubuntu", "rtags", "nginx"]
categories = ["blog"]
+++


# はじめに

[Ubuntu 18.04 LTS用にrtagsのdebパッケージを作成した](/blog/2018/05/23/build-rtags-deb-for-ubuntu-18.04-lts/) で作成したrtagsを使ってnginxのコードリーディングをするための手順メモです。

configure で生成される `ngx_auto_config.h` と `ngx_auto_headers.h` も含めて読みたいというのと、rtagsのREADMEの `Setup](https://github.com/Andersbakken/rtags#setup) のうちnginxでは [Bear](https://github.com/rizsotto/Bear) を使って `compile_commands.json` を生成するという関係もあり、 `debパッケージを使ってnginxモジュールをビルド・デバッグする](https://hnakamur.github.io/blog/2018/05/10/build-and-debug-nginx-module-using-deb-package/) と似た感じでビルドしていくことになります。

例によってこの記事に書いているのは試行錯誤してとりあえず動いたという手順なので、もっと良い手順があるかもしれません。

# rtagsとvim-rtagsのインストール

[Ubuntu 18.04 LTS用にrtagsのdebパッケージを作成した](/blog/2018/05/23/build-rtags-deb-for-ubuntu-18.04-lts/) の手順で rtags をインストールして rdm を実行しておきます。またvim-rtagsもインストールしておきます。

# 必要なソフトのインストール

debパッケージのビルドに必要なツールをインストールします。 equivs は後述の mk-build-deps コマンドで必要になります。

```console
sudo apt install build-essential devscripts equivs bear
```

# nginxのdebパッケージのソースの取得

普段使っているモジュール込みでコードリーディングしたいので自作debパッケージのソースを使います。
適当な作業ディレクトリで以下のコマンドを実行します。

```console
git clone https://github.com/hnakamur/nginx-deb
cd nginx-deb
```

# 依存ライブラリのインストール

```console
mk-build-deps debian/control
sudo dpkg -i ./nginx-build-deps*.deb
sudo apt install -f
```

# パッチ適用

debパッケージに含まれるパッチを適用します。この記事を書いている2018-05-23時点ではパッチを当てないとlua-nginx-moduleがUbuntu 18.04のlibluajit-5.1-devパッケージのファイルを見つけられないので当てる必要があります。

以下のコマンドでパッチを当てます。ちなみにこの手順はバイナリパッケージをビルドするコマンド `dpkg-buildpackage -b` を実行したときに出力されていて知りました。

```console
dpkg-source --before-build .
```

この時点で `git status` を実行するとカレントディクレクトリ配下のソースが変更されていました。後ほど `git checkout .` で元に戻しておきます。

# ソースのコピーとconfigure実行

```console
./debian/rules config.status.nginx
```

これで `debian/build-nginx` ディレクトリが作成されてnginxとモジュールのソースがコピーされconfigureが実行されます。この結果として `debian/build-nginx` 以下に `Makefile`, `objs/ngx_auto_config.h`, `objs/ngx_auto_headers.h` やその他のファイルが作られます。

また、カレントディレクトリには `config.env.nginx` と `config.status.nginx` というファイルが生成されます。 `debian/rules` の中を見るとMakefileになっているのですが、これらはmakeのターゲットになっています。

もしcleanしてやり直したい場合は `fakeroot ./debian/rules clean` でcleanできますが、 `debian/build-nginx` 以下の `Makefile` も消えてしまうので、再度 `./debian/rules config.status.nginx` を実行する必要があります。その際は `config.env.nginx` と `config.status.nginx` を消しておく必要があります。

# bearを使ってcompile_commands.json作成

rtagsのインデクスを作るための元ネタになる `compile_commands.json` をbearを使って作ります。
`compile_commands.json` にはソースコードのフルパスが含まれるので、コードを読むのを別のディレクトリで行いたい場合は、このタイミングで移動すると良いです。

ここでは `~/nginx-code-reading` に移動してみました。

```console
mv debian/build-nginx ~/nginx-code-reading
cd !$
bear make
```

これで `compile_commands.json` が作られますので、あとは以下を実行してインデクスを作成します。

```console
rc -J
```

すると `~/.cache/rtags` ディレクトリの下に `_home_hnakamur_nginx-code-reading_` というディレイクトリが作られていました。これは `/home/hnakamur/nginx-code-reading` というディレクトリに対応したものです（ `/` を `_` に置換して最後に `_` を追加している）。

# rtagsを使ってコードを読む

lyuts/vim-rtags の [Mappings](https://github.com/lyuts/vim-rtags#mappings) のキー操作により定義にジャンプしたり関数などの参照箇所を表示します。

`<Leader>rj` での定義へのジャンプは関数で使えるのはもちろんですが、構造体のフィールドを参照している箇所にカーソルをおいて `<Leader>rj` を押すと構造体の定義のフィールドの行に飛べるのが便利でした。

ジャンプから戻るのは `Ctrl-O` でできました。

# おわりに

まだ使い始めたばかりなのでよくわかっていませんが、かなり便利そうなので使いこなしていきたいです。
