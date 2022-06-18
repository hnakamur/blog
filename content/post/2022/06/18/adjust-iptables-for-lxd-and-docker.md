---
title: "LXDとDockerを同時利用するためにiptables設定を調整"
date: 2022-06-18T15:49:54+09:00
---

## はじめに

Ubuntu 22.04 LTS 上で snapcraft で入れた LXD 5.2 と Docker 公式パッケージの docker-ce 20.10.17 を入れているのですが、 LXD コンテナから `ping 8.8.8.8` のように実行しても通信できないという症状が起きていました。

[ファイアウォールを設定するには - LXD ドキュメント](https://lxd-ja.readthedocs.io/ja/latest/howto/network_bridge_firewalld/) の [LXD と Docker の問題を回避する](https://lxd-ja.readthedocs.io/ja/latest/howto/network_bridge_firewalld/#lxd-docker) のコマンドも試してみたのですが、通信できませんでした（正しく指定できたかは自信なし）。

LXD のフォーラムで [Lxd and Docker Firewall Redux - How to deal with FORWARD policy set to drop - LXD - Linux Containers Forum](https://discuss.linuxcontainers.org/t/lxd-and-docker-firewall-redux-how-to-deal-with-forward-policy-set-to-drop/9953) の [コメント](https://discuss.linuxcontainers.org/t/lxd-and-docker-firewall-redux-how-to-deal-with-forward-policy-set-to-drop/9953/7) の手順で無事通信できるようになったということでメモ。

## 設定手順

事前の iptables の設定確認

```
sudo iptables -n -L
```
と

```
sudo iptables-save
```

で確認します。

`-A FORWARD -j DOCKER-USER` の前に `lxdbr0` のブリッジに関する設定を追加するということで、以下のコマンドで先頭と2行目に入れるようにしました。

```
sudo iptables -I FORWARD -o lxdbr0 -m comment --comment "generated for LXD network lxdbr0" -j ACCEPT
sudo iptables -I FORWARD 2 -i lxdbr0 -m comment --comment "generated for LXD network lxdbr0" -j ACCEPT
```
