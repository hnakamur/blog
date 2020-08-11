---
title: "Rustで書かれたGUIライブラリーのicedを試してみた"
date: 2020-08-11T22:11:09+09:00
---
## はじめに

[Rust で書かれた UI Toolkit の OrbTk 0.3.1-alpha2 を試してみた · hnakamur's blog](/blog/2020/08/10/tried-rust-ui-toolkit-orbtk-0.3.1-alpha2/) の最後に書いていた
[hecrj/iced: A cross-platform GUI library for Rust, inspired by Elm](https://github.com/hecrj/iced)
も試してみたのでメモです。

## ToDo サンプルアプリケーションを試す手順

git clone でレポジトリ取って来てそこに移動。

```
git clone https://github.com/hecrj/iced
cd iced
```

試したときの最新のコミットは以下の通りでした。

```
$ git log -1 master
commit 9ba4cfd23f4620bab93df9616617643604db2c79 (origin/master, origin/HEAD, master)
Author: Héctor Ramón Jiménez <hector0193@gmail.com>
Date:   Sat Aug 1 15:18:52 2020

    Add `height` method to `Slider`
```

[examples/todos/README.md](https://github.com/hecrj/iced/blob/00d66da0cee1dc7faeccc5b3f0794a0393a38da7/examples/todos/README.md) にある ToDo アプリのサンプルを試しました。

```
cargo run --package todos
```

Ubuntu 20.04 LTS と Windows 10 で試してみてどちらも正常に動きました。

## 日本語フォント設定

日本語は入力は出来るけど文字化けしていました。
[Does not support chinese? · Issue #213 · hecrj/iced](https://github.com/hecrj/iced/issues/213)
というイシューを見て日本語フォントを設定してみると、正しく表示されました。

Ubuntu 20.04 LTS では NotoSansCJK-Regular.ttc を todos/fonts/ にコピーし
`examples/todos/src/main.rs` の `main` 関数を以下のように変更すればOKでした。

```
pub fn main() {
    Todos::run(Settings {
        default_font: Some(include_bytes!("../fonts/NotoSansCJK-Regular.ttc")),
        ..Settings::default()
    })
}
```

Windows 10 では NotoSansCJKjp-Regular.otf を todos/fonts/ にコピーし
`examples/todos/src/main.rs` の `main` 関数を以下のように変更すればOKでした。

```
pub fn main() {
    Todos::run(Settings {
        default_font: Some(include_bytes!("../fonts/NotoSansCJKjp-Regular.otf")),
        ..Settings::default()
    })
}
```

{{< figure src="/blog/images/2020/08/11/iced-todo-example-with-japanese-font.png" title="iced to-do example with japanese font" >}}
