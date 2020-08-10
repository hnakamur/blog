---
title: "gtk-rs 0.9.0を試した"
date: 2020-08-10T14:45:42+09:00
---

## はじめに

[gtk-rs/gtk: GTK+ 3.x bindings and wrappers for Rust](https://github.com/gtk-rs/gtk) 0.9.0 を試したメモです。

[rustup.rs - The Rust toolchain installer](https://rustup.rs/)
はインストールしてセットアップ済みとします。

## Windows 10

[Building](https://github.com/gtk-rs/gtk#building) から
[Requirements](http://gtk-rs.org/docs/requirements.html) を開いて
Windows のセクションを参考に MSYS2 と GTK をインストールしました。

### MSYS2 のインストール

[MSYS2](https://www.msys2.org/) からインストーラー `msys2-x86_64-20200720.exe` をダウンロードして実行。
インストール先はデフォルトの `C:\msys64` です（上記のページの画面イメージでは `C:\msys32` となっていますが）。

セットアップ後 MSYS2 の端末を起動して以下のコマンドでパッケージデータベースとコアシステムをアップデートします。

```
pacman -Syu
```

その後 MSYS2 の端末を開きなおして以下のコマンドで残りのパッケージをアップデートします。

```
pacman -Su
```

(横道) pacman コマンドについては [pacman - ArchWiki](https://wiki.archlinux.jp/index.php/Pacman) が詳しいです。

ローカルにインストール済みのパッケージ名をキーワード検索するときは
```
pacman -Qs キーワード
```
です。

### Windows Terminal に MSYS2 の端末を開く設定追加

[Windows Terminalでもmsys2を使おう - Qiita](https://qiita.com/yumetodo/items/4aa03d1eb3d887bca1a8) を参考に追加しました。

PowerShell で以下のコマンドを実行して GUID を生成します。

```
[guid]::NewGuid()
```

Windows Terminal の設定メニューで表示された設定の `"profiles"` の `"list"` に以下のような設定を追加しました
（私はフォントは `"profiles"` の `"defaults"` のほうに共通で設定しています）。

```
{
// …(略)…
    "profiles":
    {
        "defaults":
        {
            // Put settings here that you want to apply to all profiles.
            "fontFace": "Cica",
            "fontSize": 16,
            "cursorColor": "#FFFFFF",
            "cursorShape": "filledBox",
            "colorScheme": "Tango Dark"
        },
        "list":
        [
// …(略)…
            {
                "guid" : "{8573f40a-ca5e-4739-b9a6-fb318315836d}",
                "closeOnExit" : true,
                "commandline" : "cmd.exe /c \"set MSYSTEM=MINGW64&& set MSYS=winsymlinks:nativestrict&& C:/msys64/usr/bin/bash.exe --login\"",
                "historySize" : 9001,
                "icon": "C:/msys64/msys2.ico",
                "name" : "MSYS2",
                "startingDirectory" : "C:/msys64/home/hnakamur"
            }
// …(略)…
```

startingDirectory はユーザー名に合わせて調整します。

### GTK for Windows のセットアップ

[The GTK Project - A free and open-source cross-platform widget toolkit](https://www.gtk.org/docs/installations/windows/#using-gtk-from-msys2-packages) によると MSYS2 と gvsbuild の 2 種類のインストール方法があります。

今回は MSYS2 のほうを試しています。
MSYS2 は上記でインストールしたので
[Using GTK from MSYS2 packages](https://www.gtk.org/docs/installations/windows/#using-gtk-from-msys2-packages)
の手順で GTK をインストールします。

MSYS2 の端末で以下のコマンドを実行して GTK3 と依存パッケージをインストールします。

```
pacman -S mingw-w64-x86_64-gtk3
```

Glade もインストールしました。

```
pacman -S mingw-w64-x86_64-glade
```

[Building and distributing your application](https://www.gtk.org/docs/installations/windows/#using-gtk-from-msys2-packages) は読みましたが、とりあえずスキップしました。

また、 GTK を自作アプリケーションに同梱して配布する場合は [Legal notes on distributing GTK with your application](https://www.gtk.org/docs/installations/windows/#using-gtk-from-msys2-packages) をよく読む必要があります。これもとりあえずスキップ。

### C 言語での GTK のサンプルを動かしてみる

[Getting Started](https://www.gtk.org/docs/getting-started/hello-world/) を参考にして試しました。

このページに書かれている内容で `hello-world-gtk.c` というファイルを作成し、以下のコマンドでビルドしました。

```console
gcc `pkg-config --cflags gtk+-3.0` -o hello-world-gtk hello-world-gtk.c `pkg-config --libs gtk+-3.0`
```

しかし pkg-config で glib-2.0 が見つからないという趣旨のエラーが出ました。

[pkg-config fails to find cairo.pc and glib-2.0.pc on MSYS2 Win64 · Issue #23 · rust-lang/pkg-config-rs](https://github.com/mitaa) の [コメント](https://github.com/rust-lang/pkg-config-rs/issues/23#issuecomment-239558109) を見て以下のコマンドを実行すると解消しました。

```
pacman -S mingw-w64-x86_64-pkg-config
```

今気づきましたが [Requirements](http://gtk-rs.org/docs/requirements.html)
の "Using the MSYS2 MinGW shell" の項に以下のコマンドで pkg-config のセットアップができる旨書いてありました。

```
pacman -S mingw-w64-x86_64-toolchain
```

あと、状況を忘れてしまいましたが
[windows - Step by step instruction to install Rust and Cargo for mingw with Msys2? - Stack Overflow](https://stackoverflow.com/questions/47379214/step-by-step-instruction-to-install-rust-and-cargo-for-mingw-with-msys2/47380501#47380501)
も参考にして以下の設定を行いました。

MSYS2 の端末で `~/.bashrc` に以下の行を追加。

```
export PATH=/c/Users/hnakamur/.cargo/bin:$PATH
```

`C:\Users\hnakamur\.cargo\config` (ユーザー名は適宜変更) を以下の内容で作成。

```
[target.x86_64-pc-windows-gnu]
linker = "C:\\msys64\\usr\\bin\\gcc.exe"
ar = "C:\\msys64\\usr\\bin\\ar.exe"
```

### Rust での GTK のサンプルを動かしてみる

上記の続きで以下のように rustup のツールチェインをインストールして、デフォルトにしまいｓた。

```
rustup toolchain install stable-x86_64-pc-windows-gnu
rustup default stable-x86_64-pc-windows-gnu
```

その後 [Gtk-rs](https://gtk-rs.org/#using) のサンプルを動かしてみました。

さらに Box と TextView も追加してみましたが、 IME で日本語入力・編集も問題なく行えました。

結果は [hnakamur/gtk-rs-example](https://github.com/hnakamur/gtk-rs-example) に置きました。


## Ubuntu 20.04 LTS

[Requirements](http://gtk-rs.org/docs/requirements.html)
に沿って必要なパッケージをインストール。

```console
sudo apt install libgtk-3-dev
```

あとは
[hnakamur/gtk-rs-example](https://github.com/hnakamur/gtk-rs-example)
を `git clone` してきて `cargo run` で試しました。

こちらも日本語入力も大丈夫でした。
