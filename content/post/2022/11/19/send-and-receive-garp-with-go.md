---
title: "GoでGratious ARP (GARP)を送信と受信する"
date: 2022-11-19T21:20:07+09:00
---
## はじめに

GARP については [Gratuitous ARP - Wikipedia](https://ja.wikipedia.org/wiki/Gratuitous_ARP) や [Gratuitous_ARP](https://wiki.wireshark.org/Gratuitous_ARP) 参照。

2台のサーバからなる冗長構成でフェイルオーバーした際に、新しいプライマリサーバに仮想IPアドレス(Virtual IP; VIP)を追加してGARPを送信することで、他のサーバのARPテーブルを更新し仮想IPアドレスに対応するMACアドレスを新しいプライマリサーバのものに更新するという使い方があります。

GoでGratious ARP (GARP)を送信と受信するCLIを書いてみたのでメモです。
レポジトリは [hnakamur/netvip: A package for virtual IP address (VIP) written in Go](https://github.com/hnakamur/netvip) です。

## GARPの送信

[mdlayher/arp: Package arp implements the ARP protocol, as described in RFC 826. MIT Licensed.](https://github.com/mdlayher/arp) という便利なライブラリがあるので、これを使えば
https://github.com/hnakamur/netvip/blob/781a3c3647a234313ea17f8708265461d7aea0b5/garp.go#L15-L36
と数十行程度のコードを書くだけです。

もっと詳しく中身を知るには [Using raw sockets in Go](https://css.bz/2016/12/08/go-raw-sockets.html) の記事が良かったです。

## GARPの受信

https://github.com/hnakamur/netvip/blob/781a3c3647a234313ea17f8708265461d7aea0b5/garp.go#L38-L77

RAW ソケット作成部分は [Using raw sockets in Go](https://css.bz/2016/12/08/go-raw-sockets.html) の記事の最初のサンプルプログラムを参考にしつつ、keepalivedの
https://github.com/acassen/keepalived/blob/26c979eef9c57d0b62ba3c4a18d080878575e5a1/keepalived/vrrp/vrrp_arp.c#L212
を見て `syscall.ETH_P_ALL` を `syscall.ETH_P_ARP` に変えています。

受信する部分は
[DHCP discover with Go and raw sockets](https://gist.github.com/corny/5e4e3f8e6f2395726e46c3db9db17f12)
で `syscall.RecvFrom` を使っているのを見て真似しました。

ARP パケットをパースする関数は
[mdlayher/arp: Package arp implements the ARP protocol, as described in RFC 826. MIT Licensed.](https://github.com/mdlayher/arp) の非公開関数のコード
https://github.com/mdlayher/arp/blob/6706a2966875c189c24afd003ffe801ff69542a1/packet.go#L245-L261
をコピーしました。

## CLIを書いた

VIPを追加してGARPを送信するのと、GARPを受信したらVIPを削除するCLIを書きました。
https://github.com/hnakamur/netvip/blob/781a3c3647a234313ea17f8708265461d7aea0b5/cmd/vip/main.go
