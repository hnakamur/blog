---
title: "Rustで書かれたUIツールキットdruid 0.6.0を試した"
date: 2020-08-13T19:07:20+09:00
---

## はじめに

[Rust で書かれた UI Toolkit の OrbTk 0.3.1-alpha2 を試してみた · hnakamur's blog](/blog/2020/08/10/tried-rust-ui-toolkit-orbtk-0.3.1-alpha2/) の「おわりに」に書いたツールキットのうちgtk-rsとicedは試して
[gtk-rs 0.9.0を試した · hnakamur's blog](/blog/2020/08/10/tried-gtk-rs-0.9.0/)と
[Rustで書かれたGUIライブラリーのicedを試してみた · hnakamur's blog](/blog/2020/08/11/tried-rust-gui-library-iced/)に書きました。

icedが良さそうなのでdruidは試さなくてもいいかなとも思ったのですが
[How do Mozilla layoffs affect Rust? : rust](https://www.reddit.com/r/rust/comments/i7stjy/how_do_mozilla_layoffs_affect_rust/)のスレッドの
[コメント](https://www.reddit.com/r/rust/comments/i7stjy/how_do_mozilla_layoffs_affect_rust/g17ug2d/)
を見て試してみました。


試したバージョンは 0.6.0 です。
試したコードは [hnakamur/druid-example](https://github.com/hnakamur/druid-example) に置きました。

## Windows 10

{{< figure src="/blog/images/2020/08/13/druid-example-on-windows.png" title="druid example on Windows" >}}

* Windows ではフォントの設定を特に変えなくても日本語が文字化けせず表示されました。
    * 上記のスクリーンショットは Noto Sans CJK JP を指定しています。
* IMEはオンになるのですが入力確定してもテキストフィールドに反映されませんでした。

## Ubuntu 20.04 LTS

{{< figure src="/blog/images/2020/08/13/druid-example-on-ubuntu.png" title="druid example on Ubuntu" >}}

README の "Platform notes" の
[Linux](https://github.com/linebender/druid#linux)
の項によるとLinuxではGTK3に依存するので適宜インストールが必要です。

* Ubuntuではラベルのテキストに日本語を指定しても文字化けするのでフォントの設定が必要でした。
    * 上記のスクリーンショットは Noto Sans CJK JP を指定しています。
* IMEはオンにならず、私は Alt + \` にしているのですが \` が入力されてしまいました。

## おわりに

* iced ではフォントのバイナリデータを渡す必要がありましたが、druidではフォント名で指定可能なところは良いです。
* 日本語入力については iced のほうが良いです。

0.7 へのロードマップが
[0.7 Roadmap · Issue #1059 · linebender/druid](https://github.com/linebender/druid/issues/1059)
にありました。今後に期待です。

[Goals](https://github.com/linebender/druid#Goals) とその下の Non-Goals を見ると、druidはウェブをターゲットにHTMLを生成するのはスコープ外です。
なので、ネイティブアプリとウェブ両方をターゲットにしたいなら iced が良さそうです。
