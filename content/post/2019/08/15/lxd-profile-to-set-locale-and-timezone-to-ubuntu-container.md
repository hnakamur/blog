+++
title="LXDでUbuntuコンテナにロケールとタイムゾーンを設定するプロファイル"
date = "2019-08-15T12:45:00+09:00"
tags = ["lxd"]
categories = ["blog"]
+++


# はじめに

[How to preconfigure LXD containers with cloud-init – Mi blog lah!](https://blog.simos.info/how-to-preconfigure-lxd-containers-with-cloud-init/) に cloud-init を使って Ubuntu コンテナの初期化時にロケールとタイムゾーンを設定する方法が紹介されていたのでメモしておきます。

# Ubuntu 用のプロファイル作成

[LXDでコンテナの初期化に使われるテンプレート](/blog/2019/08/15/lxd-container-templates/) に書いたように CentOS 7 コンテナは cloud-init 非対応ですので、 Ubuntu 用のプロファイルを作成して、そこにロケールとタイムゾーンの設定を入れることにします。

`default` プロファイルは

まず以下のコマンドで Ubuntu 用のプロファイルを作成します。

```console
lxc profile create ubuntu
```

次に今作成したプロファイルを編集します。

```console
lxc profile edit ubuntu
```

`config:` と `description:` の部分を以下のように書き換えます。

```yaml
config:
  environment.LANG: en_US.UTF-8
  user.user-data: |
    #cloud-config
    locale: ja_JP.UTF-8
    timezone: Asia/Tokyo
description: Additional settings for Ubuntu
```

# Ubuntu コンテナの作成と起動

`default` プロファイルと上記で作成した `ubuntu` プロファイルを使用して
`c1` という Ubuntu 18.04 LTS のコンテナを作成・起動するには以下のようにします。

```console
lxc launch -p default -p ubuntu ubuntu:18.04 c1
```

## タイムゾーンの確認

私の環境だと cloud-init が完了するまで 10 秒程度かかるため、 起動直後に `/etc/timezone` の中身を確認し、 `date` コマンドを実行すると UTC になっています。
10 秒ほどしてから再度実行するとタイムゾーンとロケールが指定通りになっていました。

```console
$ lxc exec c1 -- sh -c 'cat /etc/timezone; date'
Etc/UTC
Thu Aug 15 03:00:12 UTC 2019
$ lxc exec c1 -- sh -c 'cat /etc/timezone; date'
Asia/Tokyo
Thu Aug 15 12:00:21 JST 2019
```

cloud-init の初期化が完了すると `/run/cloud-init/result.json` というファイルが作られるので、以下のようにすれば完了を待つことができます。

```console
$ lxc launch -p default -p ubuntu ubuntu:18.04 c2 \
  && lxc exec c2 -- sh -c 'while ! [ -f /run/cloud-init/result.json ]; do sleep 1; done' \
  && lxc exec c2 -- sh -c 'cat /etc/timezone; date'
Creating c2
Starting c2
Asia/Tokyo
Thu Aug 15 12:06:42 JST 2019
```

シェルスクリプトで自動化するときにこの手が使えます。

とは言っても、 Ubuntu コンテナの場合は cloud-init の [Modules](https://cloudinit.readthedocs.io/en/latest/topics/modules.html) でパッケージのインストールやコマンドの実行を行うことができます。

パッケージのインストールやコマンド実行は [How to preconfigure LXD containers with cloud-init – Mi blog lah!](https://blog.simos.info/how-to-preconfigure-lxd-containers-with-cloud-init/) にあるように profile の config に以下のように設定すればできるそうです。

```yaml
config:
  user.user-data: |
    #cloud-config
    package_upgrade: true
    packages:
      - build-essential
    locale: es_ES.UTF-8
    timezone: Europe/Madrid
    runcmd:
      - [touch, /tmp/simos_was_here]
```

これらの処理を cloud-init で行ってそれの完了を待つには、上記の通り `/run/cloud-init/result.json` というファイルが作られるのを待てば OK です。

## ロケールの確認

システムのロケールは指定通り `ja_JP.UTF-8` になっています。

```console
$ lxc exec c2 -- localectl
   System Locale: LANG=ja_JP.UTF-8
       VC Keymap: n/a
      X11 Layout: us
       X11 Model: pc105
```

`LANG` 環境変数は指定通り `en_US.UTF-8` になっているので `ls -l` の日付は英語で出力されます。

```console
$ lxc exec c2 -- sh -c 'echo $LANG'
en_US.UTF-8
$ lxc exec c2 -- ls -ld /
drwxr-xr-x 22 root root 4096 Aug 14 01:34 /
```

`LANG` 環境変数を `ja_JP.UTF-8` にすれば日本語で出力されます。

```console
$ lxc exec c2 -- sh -c 'LANG=ja_JP.UTF-8 ls -ld /'
drwxr-xr-x 22 root root 4096  8月 14 01:34 /
```

# default プロファイルを書き換えるのもありかも

私が作るのはほぼ Ubuntu コンテナで、たまに CentOS 7 という感じなので `default` プロファイルを書き換えるのもありかもと思いました。

`lxc profile show default` で `default` プロファイルの内容を確認すると以下のようになっていました。

```yaml
config:
  environment.LANG: en_US.utf8
description: Default LXD profile
devices:
  eth0:
    nictype: bridged
    parent: lxdbr0
    type: nic
  root:
    path: /
    pool: default
    type: disk
name: default
used_by:
- /1.0/containers/c2
- …(略)…
```

これをコピーして `centos` 用のプロファイルを作ります。

```console
$ lxc profile copy default centos
```

で `lxc profile edit default` を実行して上記のように Ubuntu 用の設定を追加します。

すると Ubuntu のコンテナの作成・起動は以下のコマンドになり

```console
$ lxc launch ubuntu:18.04 ubuntu1
```

CentOS 7 のコンテナの作成・起動は以下のコマンドになります。

```console
$ lxc launch -p centos images:centos/7 cent1
```

プロファイルの `devices:` の設定が `default` と `centos` のプロファイルの2箇所に重複することになるので、変更の際は両方変える必要があるのが欠点です。

が、普段のコンテナ作成・起動はこちらのほうが楽で良さそうです。
