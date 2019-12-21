+++
title="rustupでrustをセットアップ"
date = "2018-01-29T01:06:00+09:00"
tags = ["rust"]
categories = ["blog"]
+++


## はじめに

Ubuntu 16.04の環境にrustをセットアップしたときのメモです。

## インストール手順のドキュメント

rustup の
[Installation](https://github.com/rust-lang-nursery/rustup.rs#installation) には
[www.rustup.rs](https://www.rustup.rs/) の手順に従うように書いてありますが、
Windowsで見るとWindows用の手順が表示されてLinux用の手順が見れないので、
[Other installation methods](https://github.com/rust-lang-nursery/rustup.rs#other-installation-methods) のほうを見ます。

## 安定版のインストール

```console
curl https://sh.rustup.rs -sSf | sh
```

と書いていますが、中身を確認してから実行したかったのでまずはインストーラをダウンロードだけしました。

```console
$ curl -o rustup-init.sh https://sh.rustup.rs
```

`rustup-init.sh` の中身を確認した後、インストーラを実行しました。

```console
$ sh rustup-init.sh
info: downloading installer

Welcome to Rust!

This will download and install the official compiler for the Rust programming
language, and its package manager, Cargo.

It will add the cargo, rustc, rustup and other commands to Cargo's bin
directory, located at:

  /home/hnakamur/.cargo/bin

This path will then be added to your PATH environment variable by modifying the
profile files located at:

  /home/hnakamur/.profile
  /home/hnakamur/.bash_profile

You can uninstall at any time with rustup self uninstall and these changes will
be reverted.

Current installation options:

   default host triple: x86_64-unknown-linux-gnu
     default toolchain: stable
  modify PATH variable: yes

1) Proceed with installation (default)
2) Customize installation
3) Cancel installation
```

`1` とエンターを入力すると以下のように出力されてインストールは完了です。

```console
info: updating existing rustup installation

Rust is installed now. Great!

To get started you need Cargo's bin directory ($HOME/.cargo/bin) in your PATH
environment variable. Next time you log in this will be done automatically.

To configure your current shell run source $HOME/.cargo/env
```

次回のログインからはPATHが通っていますが、その場で使うには上記の最終行の通り以下のコマンドを実行します。

```console
source $HOME/.cargo/env
```

バージョンを確認してみると1.9.0と古いです。

```console
$ rustc --version
rustc 1.9.0 (e4e8b6668 2016-05-18)
```

以下のコマンドでアップデートします。

```console
rustup update
```

最新版になりました。

```console
$ rustc --version
rustc 1.23.0 (766bd11c8 2018-01-01)
```

## nightlyのインストール

[Working with nightly Rust](https://github.com/rust-lang-nursery/rustup.rs/#working-with-nightly-rust) に手順が書いてありました。

以下のコマンドでインストールします。

```console
rustup install nightly
```

バージョン確認。

```console
$ rustup run nightly rustc --version
rustc 1.25.0-nightly (7d6e5b9da 2018-01-27)
```

nightlyをデフォルトに切り替えてバージョン確認。

```console
$ rustup default nightly
info: using existing install for 'nightly-x86_64-unknown-linux-gnu'
info: default toolchain set to 'nightly-x86_64-unknown-linux-gnu'

  nightly-x86_64-unknown-linux-gnu unchanged - rustc 1.25.0-nightly (7d6e5b9da 2018-01-27)

$ rustc --version
rustc 1.25.0-nightly (7d6e5b9da 2018-01-27)
