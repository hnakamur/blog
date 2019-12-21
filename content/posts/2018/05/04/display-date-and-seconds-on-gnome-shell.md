+++
title="GNOME Shellの時刻表示に日付や秒を表示"
date = "2018-05-04T21:25:00+09:00"
tags = ["ubuntu", "gnome"]
categories = ["blog"]
+++


## はじめに

[How do I change the date format in Gnome 3 shell? - Ask Ubuntu](https://askubuntu.com/questions/312138/how-do-i-change-the-date-format-in-gnome-3-shell?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa)
を参考にしました。

日本語環境の場合デフォルトでは「金曜日 21 : 32」のようになっていました。

## 日付を表示

以下のコマンドを実行すると「5月 4日 (金) 21 : 32」という形式で日付も表示されるようになります。

```console
gsettings set org.gnome.desktop.interface clock-show-date true
```

## 秒を表示

さらに以下のコマンドを実行すると「5月 4日 (金) 21 : 32 : 52」という形式で秒も表示されるようになります。

```console
gsettings set org.gnome.desktop.interface clock-show-seconds true
```

## 表示形式をカスタマイズ

表示形式をカスタマイズしたい場合は
[GNOME Shellのパネルに日付を表示する方法 | Linux Fan](https://linuxfan.info/gnome-shell-clock-show-date)
の手順に従ってDate FormatというGNOME Shell拡張機能を入れればOKです。

ただし [GNOME Shellのカスタマイズに必須！拡張機能をインストールする方法 | Linux Fan](https://linuxfan.info/setup-gnome-shell-extensions) にあるとおりGNOME Shell拡張機能をインストールするにはそれを管理するためにFirefoxやChromeでExtensionsというブラウザ拡張をインストールする必要があります。

一度試してみて表示形式のカスタマイズは希望通りできたのですが、ブラウザにログインしているとWindowsやmacOS上のブラウザにも同期されて拡張がインストールされてしまうのがいまいちです。ということで、表示形式はデフォルトで良しとして他にどうしてもカスタマイズしたい項目が出てくるまではExtensionsは使わないことにしました。
