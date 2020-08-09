---
title: "Rust で書かれた UI Toolkit の OrbTk 0.3.1-alpha2 を試してみた"
date: 2020-08-10T07:58:44+09:00
---

## はじめに

Rust の GUI ライブラリーを
[GUI — list of Rust libraries/crates // Lib.rs](https://lib.rs/gui)
で見て、成熟してそうなのは gtk のようですが、
[OrbTk — Rust GUI library // Lib.rs](https://lib.rs/crates/orbtk)
というのも気になったので試してみました。

gtk のような既存のGUIライブラリーに依存しないのと
[redox-os/orbtk: The Rust UI-Toolkit.](https://github.com/redox-os/orbtk)
の
[Platforms](https://github.com/redox-os/orbtk#platforms)
を見てターゲットのプラットフォームの多さが良いなと思いました。

2020-08-10 時点のバージョンは
デフォルトブランチである devleop の最新のコミット
[@f0d53cd](https://github.com/redox-os/orbtk/commit/f0d53cd645f55f632173a89aee2fa85edbd9e96f) と
[0.3.1-alpha2](https://github.com/redox-os/orbtk/releases/tag/0.3.1-alpha2)
です。

結論を先に書くとまだアルファなのでアプリケーションをばりばり開発するにはまだ早そうです。
が、今後が楽しみです。

## Ubuntu 20.04 LTS

試した際の rustup, rustc, orbtk のバージョンは以下の通りです。

```console
$ rustup --version
rustup 1.22.1 (b01adbbc3 2020-07-08)
$ rustc --version
rustc 1.47.0-nightly (6c8927b0c 2020-07-26)
```

```console
hnakamur@thinkcentre:~/ghq/github.com/redox-os/orbtk$ git log -1
commit f0d53cd645f55f632173a89aee2fa85edbd9e96f (HEAD -> develop, origin/develop, origin/HEAD)
Author: Florian Blasius <flovanpt@posteo.de>
Date:   Fri Jul 31 00:11:50 2020

    text input fixes.
```

[examples](https://github.com/redox-os/orbtk/tree/develop/examples)
ディレクトリーにいくつか例があります。
そのうち widgets が現状用意されているコンポーネントを試せるサンプルになっています。

```console
cargo run --example widgets
```

{{< figure src="/blog/images/2020/08/10/orbtk-widgets-example.png" title="orbtk widgets example" >}}

試してみて気づいた点。

* ボタンなどは期待通り動きます
* TextBox では IME は有効になりませんでした
* TextBox では Emacs ライクなキーバィンディングは無しで
* TextBox では Ctrl-a で全選択になります

## Windows 10

試した際の rustup, rustc, orbtk のバージョンは以下の通りです。

```
C:\Users\hnakamur\ghq\github.com\redox-os\orbtk>rustup --version
rustup 1.22.1 (b01adbbc3 2020-07-08)

C:\Users\hnakamur\ghq\github.com\redox-os\orbtk>rustup toolchain list
stable-x86_64-pc-windows-gnu
stable-x86_64-pc-windows-msvc
nightly-x86_64-pc-windows-msvc (default)

C:\Users\hnakamur\ghq\github.com\redox-os\orbtk>rustc --version
rustc 1.47.0-nightly (6c8927b0c 2020-07-26)
```

```
C:\Users\hnakamur\ghq\github.com\redox-os\orbtk>git log -1
commit f0d53cd645f55f632173a89aee2fa85edbd9e96f (HEAD -> develop, origin/develop, origin/HEAD)
Author: Florian Blasius <flovanpt@posteo.de>
Date:   Thu Jul 30 17:11:50 2020 +0200

    text input fixes.
```

```console
cargo run --example widgets
```

{{< figure src="/blog/images/2020/08/10/orbtk-widgets-example-windows.png" title="orbtk widgets example on Windows" >}}

試してみて気づいた点。

* ボタンなどは期待通り動きます
* TextBox をクリックするとアプリケーション全体が反応しなくなります
    * ボタンも動作せず、タイトルバーをドラッグしてウィンドウ移動もできません

`git switch master` して 0.3.1-alpha2 でも試してみましたが同じでした。

```
C:\Users\hnakamur\ghq\github.com\redox-os\orbtk>git log -1
commit 4c2382a2f57166bdd8aa57651821b7dd68582934 (HEAD -> master, tag: 0.3.1-alpha2, origin/master)
Author: Florian Blasius <flovanpt@posteo.de>
Date:   Wed Apr 22 14:17:58 2020 +0200

    Up.
```

## おわりに

ちょうどたまたま
[Nora "Black Lives Matter" Codes ⌨️さんはTwitterを使っています 「are there any pure #Rust GUI libraries targeted at the desktop? a la GTK or Qt, rather than dear imgui or like that」 / Twitter](https://twitter.com/NoraDotCodes/status/1292208090675400710)
というツイートを見かけました。

Rust で書かれた UI ツールキットとして orbtk 以外に次の2つがあげられていました。

* [linebender/druid: A data-first Rust-native UI design toolkit.](https://github.com/linebender/druid)
* [hecrj/iced: A cross-platform GUI library for Rust, inspired by Elm](https://github.com/hecrj/iced)

成熟度で言うとやはり
[gtk-rs/gtk: GTK+ 3.x bindings and wrappers for Rust](https://github.com/gtk-rs/gtk)
らしいです。
