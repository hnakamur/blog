+++
Categories = []
Description = ""
Tags = ["ubuntu", "lxd"]
date = "2016-05-07T14:12:49+09:00"
title = "Ubuntu 16.04 LTSでLXD 2.0を試してみた"

+++
## はじめに
[LXC 2.0でCentOS 7のコンテナを動かしてみた · hnakamur's blog at github](/blog/2016/04/19/run_centos7_containers_on_lxc2/)でLXC 2.0を試しましたが、今度はLXD 2.0を試してみました。

実は私は、コンテナをローカルホストでしか動かさないならLXC、リモートホストでも動かすならLXDという使い分けなのかなと漠然と思っていました。

上記の記事ではrootユーザでコンテナを作成するという特権コンテナについて書きましたが、非rootユーザでコンテナを作成する非特権コンテナについては書いていませんでした。

実は CentOS 7 の非特権コンテナも試していたのですが、 DHCP で IPアドレスが付与されないという現象が起きていました。私の当面の用途は開発環境構築でありホストOS側でroot権限はあることが前提なので非特権コンテナは調査しないことにしました。

一方、LXDはデフォルトで非特権コンテナを作るようになっています。今回試してみたところ、 CentOS 7 のコンテナも DHCP で無事 IPアドレスが付与されました。

root権限を使うのは必要最小限にするのが望ましいので、この状況を見ると今後新規に環境構築するならLXCよりもLXDを使うほうが良いかなと思います。

ちなみに https://github.com/lxc/lxd によると、LXD は lex-dee と発音するそうです。カタカナで書くとレックスディーもしくはレクスディーでしょうか。

## 記事リスト

いろいろ試していたら記事が長くなってきたので分割しました。例によって他の方に向けた入門記事ではなく、自分用の調査メモです。

* [Ubuntu 16.04 LTSでLXD 2.0をセットアップして使ってみる](/blog/2016/05/07/start-using-lxd-2.0-on-ubuntu-16.04/)
* [LXCの特定の1つのコンテナの起動状態をシェルスクリプトで確認したいときのお勧めの方法](/blog/2016/05/07/script-to-check-running-status-of-lxd-container/)
* [LXDコンテナで固定IPアドレスを使うための設定](/blog/2016/05/07/how-to-use-fixed-ip-address-for-a-lxd-container/)
* [AnsibleのLXDコネクションプラグインを試してみた](/blog/2016/05/07/tried-ansible-lxd-connection-plugin/)
* [LXDのREST APIをcurlで試してみた](/blog/2016/05/07/tried-lxd-rest-api-with-curl/)
* [LXDのREST APIクライアントライブラリpylxdを試してみた](/blog/2016/05/07/tried-pylxd/)

なお、記事によってコンテナのIPアドレスのネットワークが違う場合がありますが、何回か環境を作りなおして毎回ランダムなネットワークを使っているためなので気にしないでください。
