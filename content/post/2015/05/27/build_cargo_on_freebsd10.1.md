+++
Categories = []
Description = ""
Tags = ["rust"]
date = "2015-05-27T05:20:42+09:00"
title = "FreeBSD 10.1 amd64でrustのcargoのビルドに挑戦"

+++
[FreeBSD 10.1 amd64でRustをビルドしてみた · hnakamur's blog at github](/blog/2015/05/17/build_rust_on_freebsd/)でrustのコンパイラrustcは使えるようになりますが、 [cargo](https://github.com/rust-lang/cargo)は使えません。

## multirustはバイナリパッケージが必要なため挫折

まず、[brson/multirust](https://github.com/brson/multirust)でrustとcargoをインストール出来ないか試してみたのですがダメでした。これはバイナリをダウンロードするようになっていてFreeBSD用のバイナリは無いのでエラーになります。

なお、FreeBSD 10.1でスクリプトが一部エラーになったのでプルリクエスト [Freebsd support by hnakamur · Pull Request #67 · brson/multirust](https://github.com/brson/multirust/pull/67) を送ってこれ自体はマージされました。が、multirustでインストールでrustとcargoがインストール出来ない状況はそのままです。

## FreeBSDでcargoをビルドするスクリプトを試してみた

cargoのイシューで[How to build Cargo from GIT on FreeBSD? · Issue #429 · rust-lang/cargo](https://github.com/rust-lang/cargo/issues/429)というのを見つけました。

### ebfeさんのスクリプトは今のcargoには非対応

[ebfeさんの2014-10-04のコメント](https://github.com/rust-lang/cargo/issues/429#issuecomment-57814722)に[build-cargo-freebsd.sh](https://gist.github.com/ebfe/dcb914d907c4a54a7b8d)があったので、試してみました。

```
curl -LO https://gist.githubusercontent.com/ebfe/dcb914d907c4a54a7b8d/raw/b36e7f3999d309f4931efe158918f28fe2fdecd0/build-cargo-freebsd.sh
chmod +x build-cargo-freebsd.sh
./build-cargo-freebsd.sh
```

すると途中で `regex` crateが見つけられずエラーになってしまいました。

```
Checking connectivity... done.
deps/docopt.rs/src/lib.rs:218:1: 218:20 error: can't find crate for `regex`
deps/docopt.rs/src/lib.rs:218 extern crate regex;
                              ^~~~~~~~~~~~~~~~~~~
                              error: aborting due to previous error
```

[CaptainHayashiさんの2014-12-10のコメント](https://github.com/rust-lang/cargo/issues/429#issuecomment-66389947)でも `@ebfe's gist no longer works.` と書かれていました。

cratesを追加した版[build-cargo-freebsd.sh](https://gist.github.com/hnakamur/4b85c051bfbc518c64df)
を作って試してみたのですが
https://gist.github.com/hnakamur/4b85c051bfbc518c64df#comment-1461070
に書いたように、rust-encodingのcrateビルド中にrustがpanicを起こしてしまいました。

https://github.com/rust-lang/cargo/issues/429#issuecomment-105679347 にコメントして助けを求めています。

### csperkinsさんのスクリプトを試す

[csperkinsさんの2015-01-02のコメント](https://github.com/rust-lang/cargo/issues/429#issuecomment-68529665)に[Building Cargo on FreeBSD 10.1-RELEASE](https://csperkins.org/research/misc/2015-01-02-cargo-freebsd.html)へのリンクが貼られていました。

Cargoをbuildするには古いバージョンのCargoが必要なので、FreeBSD用の2014-12-12のスナップショットビルドから順番に新しいバージョンをビルドしていくというスクリプトとのことです。何世代もビルドするので相当時間がかかります。

途中でlibflateやlibssh2がなくてエラーになったのでインストールしました。整理した手順は以下の通りです。

```
mkdir build-cargo
cd build-cargo
sudo pkg install -y pkgconf cmake libflate libssh2
curl -LO https://csperkins.org/research/misc/build-cargo-freebsd-v9.sh
chmod +x build-cargo-freebsd-v9.sh
./build-cargo-freebsd-v9.sh
```

この記事を書いている間もビルドはまだ続いています。終わったら結果を追記する予定です。
