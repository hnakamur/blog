---
title: "ハッシュ化された~/.ssh/known_hostsにエントリを追加・検索・削除する"
date: 2021-07-23T09:53:07+09:00
---

## はじめに

[~/.ssh/known_hostsのホスト名](https://zenn.dev/yoichi/articles/host-in-ssh-known-hosts) を読みました。ハッシュ化された `~/.ssh/known_hosts` のフォーマットについて詳しく説明されていて良いですね。

関連して私が LXD で複数コンテナ間で ssh するために `~/.ssh/known_hosts` を自動構築している際に使っている手順をメモしておきます。実際はコンテナ作成を自動化するスクリプト内で呼び出していますが、この記事では各操作のコマンドを単独で説明します。

この記事は IPv6 には非対応です。元ネタが IPv6 無効で作成した LXD コンテナーの環境用だからです。

## エントリを追加

以下のように [ssh-keyscan (1)](http://manpages.ubuntu.com/manpages/focal/en/man1/ssh-keyscan.1.html) で接続対象のサーバーにアクセスして SSH ホストキーを表示して `~/.ssh/known_hosts` に追加します。

```sh
ssh-keyscan -H -4 -t ed25519 ホスト名かIPv4アドレス 2>/dev/null \
  | tee -a ~/.ssh/known_hosts > /dev/null
```

指定しているオプションは以下の通りです。

* `-H`: ハッシュ形式で出力
* `-4`: IPv4アドレスのみ出力
* `-t ed25519`: ed25519形式のホストキーのみ出力

短いホスト名、FQDN、IPv4アドレスのどれでもアクセスする場合はそれぞれ `ssh-keyscan` を実行して `~/.ssh/known_hosts` にエントリを追加しておきます。一部の方法でしかアクセスしないのであればそのパターンだけ追加しておけばOKです。

## エントリを検索

[ssh-keygen (1)](http://manpages.ubuntu.com/manpages/focal/en/man1/ssh-keygen.1.html) の `-F` オプションに対象を指定して検索します。

```sh
ssh-keygen -F ホスト名かIPv4アドレス
```

終了コードはエントリが見つかった場合は0、見つからなかった場合は1になります。

## エントリを削除

[ssh-keygen (1)](http://manpages.ubuntu.com/manpages/focal/en/man1/ssh-keygen.1.html) の `-R` オプションに対象を指定して削除します。

```sh
ssh-keygen -R ホスト名かIPv4アドレス
```

## エントリを更新

これは上記の組み合わせで可能です。具体的にはエントリを検索して存在する場合は削除してから追加します。

接続先のコンテナーを作り直したときに便利です。


以下の例は `TARGET_HOST` という変数に対象のホスト名かIPv4アドレスを設定して実行するものとします。

```sh
if [ -f "$HOME/.ssh/known_hosts" ] && ssh-keygen -F $TARGET_HOST > /dev/null; then
  ssh-keygen -R $TARGET_HOST > /dev/null
fi
ssh-keyscan -H -4 -t ed25519 $TARGET_HOST 2>/dev/null \
  | tee -a ~/.ssh/known_hosts > /dev/null
```
