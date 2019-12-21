+++
title="GNOME上でEmacsライクなキーバインディングを使う"
date = "2018-05-06T14:40:00+09:00"
tags = ["ubuntu", "GNOME"]
categories = ["blog"]
+++


# はじめに

元々macOSのChromeでURL欄を編集するときにEmacsライクなキーバインディングを使うのに慣れていたので、GNOMEのChromeもそう変更できないかと思って調べると以下の記事を見つけました。

[GNOMEのキーバインドをEmacs風に変更する - YAMAGUCHI::weblog](https://ymotongpoo.hatenablog.com/entry/2012/09/10/152133)

# 変更前の設定確認

変更前の設定を確認すると `Default` となっていました。

```console
$ gsettings get org.gnome.desktop.interface gtk-key-theme
'Default'
```

# 設定変更

以下のコマンドを実行して設定変更します。

```console
gsettings set org.gnome.desktop.interface gtk-key-theme Emacs
