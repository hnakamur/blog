+++
title="LXDのproxyを使ってポートフォワーディング"
date = "2018-07-05T08:50:00+09:00"
tags = ["lxd"]
categories = ["blog"]
+++


# はじめに

LXDのコンテナでnginxを動かして、ホストからChromeなどのブラウザでアクセスしたいことがよくあります。

LXDのイシューを見るとiptablesで実現可能とのことなのですが、iptablesとネットワークに弱い私がコマンド例を見て雰囲気で実行してもうまくできず、回避策としてホストでnginxを動かしてリバースプロキシでLXDコンテナのnginxに繋いで使っていました。

しかし、これはhttpなら良いのですがhttpsの場合はホストでSSLを終端することになるのがいまいちです。

検索してみるとLXD 3.0からproxyという種別のデバイスが追加されており ([Linux Containers - LXD - ニュース](https://linuxcontainers.org/ja/lxd/news/) 参照) 、これを使えばポートフォワーディングできるようになっていました。

公式ドキュメントは [Type: proxy](https://lxd.readthedocs.io/en/latest/containers/#type-proxy) にあります。

snapでインストールしたLXD 3.2で試してみたのでメモです。

# プロキシーの追加

例えば 192.0.2.2 というIPv4アドレスを持つ c1 というコンテナにホストの80番と443番ポートをそれぞれコンテナの80番と443番ポートにフォワーディングする場合は以下のようにします。以下で指定しているhttpとhttpsは追加するプロキシーデバイスの名前です。お好みで変えてください。

```console
lxc config device add c1 http proxy listen=tcp:0.0.0.0:80 connect=tcp:10.138.67.13:80 bind=host
lxc config device add c1 https proxy listen=tcp:0.0.0.0:443 connect=tcp:10.138.67.13:443 bind=host
```

# 状態確認

以下のコマンドでc1というコンテナのデバイス一覧を表示します。

```console
lxc config device show c1
```

実行例を示します。

```console
$ lxc config device show c1
http:
  bind: host
  connect: tcp:192.0.2.2:80
  listen: tcp:0.0.0.0:80
  type: proxy
https:
  bind: host
  connect: tcp:192.0.2.2:443
  listen: tcp:0.0.0.0:443
  type: proxy
```

# プロキシーの削除

例えば コンテナ c1 から http と https という名前のプロキシーデバイスを削除する場合は以下のようにします。

```console
lxc config device rm c1 http https
```

実行例を示します。

```console
$ lxc config device rm c1 http https
Device http, https removed from c1
```

デバイスがない状態で一覧表示するとJSONの空オブジェクトが表示されました。

```console
$ lxc config device show bionic
{}
