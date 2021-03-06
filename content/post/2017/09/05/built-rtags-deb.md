+++
title="rtagsのdebパッケージを作成した"
date = "2017-09-05T23:07:00+09:00"
tags = ["deb", "rtags"]
categories = ["blog"]
+++


## はじめに

[最強のC/C++インデクサー "Rtags" を本気で使う - Qiita](http://qiita.com/kota65535/items/39aa4d6e8adf6ab5f98c) で
[Andersbakken/rtags: A c/c++ client/server indexer for c/c++/objc[++] with integration for Emacs based on clang.](https://github.com/Andersbakken/rtags)
の存在を知り、deb パッケージを作ってみたのでメモです。

rtags は emacs 連携が入っているのですが、私は vim ユーザで emacs 使って無くて動作確認するのが面倒なので、自作 deb パッケージでは emacs 連携は外しています。

rtags 用の vim プラグインは
[lyuts/vim-rtags: Vim bindings for rtags, llvm/clang based c++ code indexer.](https://github.com/lyuts/vim-rtags)
を私は使っています。

## インストール方法

ビルドしたパッケージは
[vim : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/vim)
で公開しています。

以下の手順でインストール出来ます。

```console
sudo apt install software-properties-common
sudo add-apt-repository ppa:hnakamur/vim
sudo apt update
sudo apt install rtags
```

ちょっと試してみた感じでは xenial の vim だと動きませんでした。
私は vim8 も試してみたかったので
[terminal機能を有効にしたvim8のdebパッケージを作成した](/blog/2017/09/05/built-terminal-enabled-vim8-deb/)
に書いた vim 8 のパッケージを使っています。

vim-rtags はお好みのプラグインマネージャでインストールしてください。
一覧を開くときに location リストではなく quickfix ウィンドウを使いたいときは `~/.vimrc` に以下の設定を追加します。

```console
" Use quickfix window for rtags
let g:rtagsUseLocationList = 0
```

## 使い方

### 初期設定

以下の内容で `~/.rdmrc` を作ってください。

```text
-s usr/lib/llvm-4.0/lib/clang/4.0.0/include
```

### インデクス作成

rtags のサーバは手動で `rdm` を起動してください。
rdm は下記のインデクス生成とソースコードを参照する際の両方で起動しておく必要があります。

インデクスを作るのは、私は今のところ上記のQiitaの記事の cmake を使う方法を使っています。

コードを読みたいソースディレクトリで `-DCMAKE_EXPORT_COMPILE_COMMANDS=1` を付けて

```console
cmake . -DCMAKE_EXPORT_COMPILE_COMMANDS=1
```

のように cmake を実行して `compile_commands.json` を生成し、

```console
rc -J .
```

でインデクスを作成します。インデクスは `~/.cache/rtags/` 以下に作られます。

### インデクス参照

vim-rtags の README に説明がありますが、そのままのバインディングの場合、メソッド名などの上にカーソルを置いて `<Leader>rj` で定義に飛ぶのを最もよく使います。ヘッダファイルと実装ファイル間で相互にも飛べました。

`<Leader>rb` でジャンプ前の位置に戻ります。 jump の j と back の b で覚えやすいので、3ストロークかかりますが、とりあえずそのまま使っています。

あとは `<Leader>rf` で参照している個所一覧を見られます。

## パッケージ作成時のメモ

[rtags-testing : Hasan Yavuz Özderya](https://launchpad.net/~hyozd/+archive/ubuntu/rtags-testing) をベースにして xenial 用にし、rtags のバージョンを上げて作りました。

C と C++ のコンパイラは
[Toolchain test builds : “PPA for Ubuntu Toolchain Uploads (restricted)” team](https://launchpad.net/~ubuntu-toolchain-r/+archive/ubuntu/test)
gcc-7 と g++-7 を使っています。

pbuilder でのビルド時は [pbuilderのchroot環境にレポジトリを追加する](/blog/2017/09/02/add-repositories-to-pbuilder-chroot-images/) で書いた gcc-7 の環境を使っています。

```console
sudo pbuilder build --basetgz /var/cache/pbuilder/gcc7.tgz ../build-area/rtagsのdscファイル
```

実行時の依存関係に clang と llvm の 4.0 を加えています。なるべく新しいバージョンのほうが C++ の新しい規格で書かれたソースを正しく解釈できるだろうと思ったので 3.x ではなく 4.0 にしました。

## おわりに

clang の構文解析インターフェースを利用しているだけあって、正確に定義に飛べてかなり便利です。
ただ、たまに定義に飛ばないときもありました。

そこで
[GNU GLOBAL source code tagging system](https://www.gnu.org/software/global/)
も併用しています。

[xenial の global パッケージ](https://packages.ubuntu.com/xenial/global) もあるのですが 5.7.1 と古かったので
[artful の global パッケージ](https://packages.ubuntu.com/artful/global)
を xenial にバックポートしました。
[global : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/global)
で公開しています。
