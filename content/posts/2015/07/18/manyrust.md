+++
Categories = []
Description = ""
Tags = ["rust", "shell-script"]
date = "2015-07-18T23:13:32+09:00"
title = "manyrustという複数バージョンのrustインストールスクリプトを書いた"

+++
## multirustがあるのに、なぜ新たに書いたのか

rustのインストールは[Install · The Rust Programming Language](http://www.rust-lang.org/install.html)にあるように複数のチャネルから選んでインストールします。

* stable (安定版)チャネル
* beta (ベータ版)チャネル
* nightly (毎晩ビルドされる)チャネル

rustでunstableなAPIを使うにはnightlyを使う必要があるので、たいていはstableとnightlyの両方をインストールして使い分けたくなるはずです。
その用途には定番のスクリプトとして[brson/multirust](https://github.com/brson/multirust)があります。

私も使っていましたが、rustのソースコードの整形ツール[nrc/rustfmt](https://github.com/nrc/rustfmt)をビルドして起動しようとするとエラーになってしまいました。

既に[building cargo atop multirust fails, dyn link problems (Mac OS X) · Issue #43 · brson/multirust](https://github.com/brson/multirust/issues/43)にイシューが上がっていて、[コメント106758695](https://github.com/brson/multirust/issues/43#issuecomment-106758695)にあるように環境変数 `DYLD_LIBRARY_PATH` を設定すれば問題は解消するとのことです。

ディレクトリによって環境変数を切り替えるのは[direnv/direnv](https://github.com/direnv/direnv)が便利です。ただ、`direnv` を使うのであれば、そもそも `multirust` のように `rustc` などの実行ファイルをラップしたシェルスクリプトを作る必要は無いわけです。

rustの複数のバージョンを異なるディレクトリにインストールしておいて、利用するディレクトリごとに環境変数 `PATH` と `DYLD_LIBRARY_PATH` を切り替えればいいだけです。

であれば、 `multirust` 使わなくてももっとシンプルなスクリプトでいいよね、ということで書いたのが `manyrust` です。現状はOSXのみサポートしています。

## インストール手順

以下のようにして `~/bin` に `manyrust` スクリプトを配置します。

```
mkdir ~/bin
curl -s -o ~/bin/manyrust https://raw.githubusercontent.com/hnakamur/manyrust/master/manyrust
chmod +x ~/bin/manyrust
```

環境変数 `PATH` に `$HOME/bin` を追加して有効にします。
bashの場合はこんな感じです。

```
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bash_profilie
exec $SHELL -l
```

## rustのインストール

stableチャネルの最新版をインストール

```
manyrust install
```

betaチャネルの最新版をインストール

```
manyrust install beta
```

nightlyチャネルの最新版をインストール

```
manyrust install nightly
```

## rustを利用する側の作業ディレクトリでの設定

stableチャネルの最新版を使うディレクトリでの設定

```
manyrust showcfg >> .envrc
direnv allow .
```

nightlyチャネルの最新版を使うディレクトリでの設定

```
manyrust showcfg nightly >> .envrc
direnv allow .
```

nightlyチャネルの特定のバージョン2015-07-14を使うディレクトリでの設定

```
manyrust showcfg nightly 2015-07-14 >> .envrc
direnv allow .
```

### 応用例

基本的にはstableチャネルのrustを使いたいが、特定のディレクトリ下ではnightlyを使いたい場合は `$HOME/.envrc` にstableを使う設定を書いておいて、特定のディレクトリの `.envrc` ではnightlyを使う設定を書いておけばOKです。

```
$ manyrust showcfg >> ~/.envrc
direnv: error .envrc is blocked. Run `direnv allow` to approve its content.
$ direnv allow ~
direnv: loading ../../../../.envrc
direnv: export +DYLD_LIBRARY_PATH ~PATH
$ mkdir ~/nightly_work
$ cd !$
cd ~/nightly_work
$ manyrust showcfg nightly >> .envrc
direnv: error .envrc is blocked. Run `direnv allow` to approve its content.
$ direnv allow .
direnv: loading .envrc
direnv: export +DYLD_LIBRARY_PATH ~PATH
$ rustc --version
rustc 1.3.0-nightly (e4e93196e 2015-07-14)
$ echo $DYLD_LIBRARY_PATH
/Users/hnakamur/rust/nightly/2015-07-14/rust/lib:
$ cd
direnv: loading .envrc
direnv: export +DYLD_LIBRARY_PATH ~PATH
$ rustc --version
rustc 1.1.0 (35ceea399 2015-06-19)
$ echo $DYLD_LIBRARY_PATH
/Users/hnakamur/rust/stable/1.1.0/rust/lib:
```

### direnvを使って設定を切り替えることの利点

上の例で生成した設定ファイルは以下のようになっています。

```
$ cat ~/.envrc
source "${MANYRUST_ROOT:-$HOME/rust}/stable/current/etc/bashrc"
$ cat ~/nightly_work/.envrc
source "${MANYRUST_ROOT:-$HOME/rust}/nightly/current/etc/bashrc"
```

`souce` で読み込むファイルは `manyrust install` で以下のように生成されています。

```
$ cat ~/rust/stable/current/etc/bashrc
rust_root="${RUSTS_HOME:-$HOME/rust}/stable/1.1.0/rust"
export PATH="$rust_root/bin:$PATH"
export DYLD_LIBRARY_PATH="$rust_root/lib:$DYLD_LIBRARY_PATH"
$ cat ~/rust/nightly/current/etc/bashrc
rust_root="${RUSTS_HOME:-$HOME/rust}/nightly/2015-07-14/rust"
export PATH="$rust_root/bin:$PATH"
export DYLD_LIBRARY_PATH="$rust_root/lib:$DYLD_LIBRARY_PATH"
```

`direnv` を使わずに何回もこういうファイルを `source` すると、 `PATH` や `DYLD_LIBRARY_PATH` の中身がどんどん増えてしまいます。

```
$ eval `manyrust showcfg beta`
$ echo $DYLD_LIBRARY_PATH
/Users/hnakamur/rust/beta/1.2.0-beta.2/rust/lib:
$ eval `manyrust showcfg stable`
$ echo $DYLD_LIBRARY_PATH
/Users/hnakamur/rust/stable/1.1.0/rust/lib:/Users/hnakamur/rust/beta/1.2.0-beta.2/rust/lib:
```

長いだけではなく、この例だとstableには無いがnightlyにあるライブラリが存在するとstableのライブラリを使いたいのにnightly側が使われてしまうという問題が起きてしまいます。

`direnv` を使っていれば、上の応用例のように `DYLD_LIBRARY_PATH` の値が追加されるのではなく設定が切り替えられるので、この問題は起きません。

## rustfmtのビルドとインストール

で、ここまで書いてから `rustfmt` をビルド、インストールしようとして問題に気付きました。 `rustfmt` は `~/rust/nightly/current/rust/bin/` に置いて上記のように `.envrc` で切り替えればいいかと思っていたのですが、そうすると `stable` を使うように `.envrc` を設定したディレクトリでは `rustfmt` が使えなくなってしまいます。

またnightlyのバージョンが上がると `rustfmt` をビルドし直す必要もあります。

これを回避するためにはビルドした `rustfmt` は `~/bin/rustfmt.bin` と名前を変えて `~/bin` に置いて、ラップしたスクリプトを `~/bin/rustfmt` という名前で作成します。

具体的な手順は以下の通りです。

```
git clone https://github.com/nrc/rustfmt
cd rustfmt
manyrust showcfg nightly >> .envrc
direnv allow .
cargo build --release
cp target/release/rustfmt ~/bin/rustfmt.bin
cat <<'EOF' > ~/bin/rustfmt
#!/bin/sh
DYLD_LIBRARY_PATH="${MANYRUST_ROOT:-$HOME/rust}/nightly/2015-07-14/rust/lib" $HOME/bin/rustfmt.bin "$@"
EOF
```

今後nightlyを追加インストールした時に `rustfmt` が依存しているディレクトリが新しいバージョンの `lib` ディレクトリに存在しない場合に備えて、 `DYLD_LIBRARY_PATH` は `~/rust/nightly/current/rust/lib` ではなく特定のバージョンの `lib` ディレクトリを指定しています。

ということで、 `rustfmt` に関しては `multirust` でも `manyrust` でも同じことで、`DYLD_LIBRARY_PATH` を設定して実行するようなスクリプトを書いてラップする必要があるというオチでした。
