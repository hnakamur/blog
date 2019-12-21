+++
Categories = []
Description = ""
Tags = ["golang","cli","gist"]
date = "2016-06-14T00:52:22+09:00"
title = "gistを作成するGoのCLIを見つけた"

+++
[delta24/gist: A command line gister in Go](https://github.com/delta24/gist)です。期待通りに動かない点があったのでプルリクエストを送ったら、すぐにマージされました。

## インストール

Goはインストール済みという前提で、以下のコマンドを実行します。

```
go get -u github.com/delta24/gist
```

## 事前準備
[Creating an access token for command-line use - User Documentation](https://help.github.com/articles/creating-an-access-token-for-command-line-use/)の手順でアクセストークンを作って、 `~/.bash_profile` とかに `export GITHUB_TOKEN=...` のように書くなどして環境変数として設定するか、 あるいは `~/.gist` というファイルを作ってトークンの値を書いておきます。

## 使い方の例

自分のユーザでpublicなgistを作成

```
gist -a=false -d '説明' ファイル名
```

自分のユーザでprivate (secret)なgistを作成

```
gist -a=false -p=false -d '説明' ファイル名
```

anonymousユーザでpublicなgistを作成

```
gist -d '説明' ファイル名
```
