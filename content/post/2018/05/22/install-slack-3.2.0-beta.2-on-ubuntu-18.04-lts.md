+++
title="Ubuntu 18.04 LTSにSlack 3.2.0-beta.2をインストール"
date = "2018-05-22T15:10:00+09:00"
tags = ["ubuntu", "ubuntu-mate", "slack"]
categories = ["blog"]
+++


# はじめに

Ubuntu MATE 18.04 LTSにSlack 3.2.0-beta.2をインストールしたときのメモです。


# snapパッケージでのインストール

[Linux版 Slack  (β版) – Slack](https://get.slack.help/hc/ja/articles/212924728-Linux%E7%89%88-Slack-%CE%B2%E7%89%88-) によると、snapパッケージが提供されていて以下のコマンドでインストールできます。

```console
sudo snap install slack --classic
```

これでバージョン3.1.1がインストールされたのですが、私の環境ではAlt+`で日本語入力に切り替えることができませんでした。

ということでアンインストールしました。

```console
sudo snap remove slack
```

# debパッケージでのインストール

そこで [Linux | ダウンロード | Slack](https://slack.com/intl/ja-jp/downloads/linux) からdebパッケージをダウンロードし下記の手順でインストールしました。

`dpkg -i` でインストールすると、依存パッケージが足りないという主旨のエラーが出たので、 `apt install -f` で依存パッケージをインストールしています。

```console
sudo dpkg -i slack-desktop-3.2.0-beta25a7a50e-amd64.deb
sudo apt install -f
```

# 3.2.0-beta.2での変更点

[Linux 版 Slack (ベータ版) - リリースノート | Slack](https://slack.com/intl/ja-jp/release-notes/linux) によると2018-05-08に出た3.2.0-beta.2ではGTK2からGTK3に変更されたり、クラッシュバグの大掃除をされたりと、かなり改善されているようです。

アップデートのことを考えるとdebパッケージでインストールするよりaptかsnapのほうがありがたいので、snapパッケージで新しいバージョンが出たら、そちらに切り替えようと思います。
