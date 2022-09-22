---
title: "LXDとDockerを同時利用するためにiptables設定を調整"
date: 2022-06-18T15:49:54+09:00
lastmod: 2022-09-23T16:40:00+09:00
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

## iptablesの設定の自動化

OS再起動の度に起動時に毎回上記のコマンドを手動で実行するのは面倒なので、OS起動時に自動実行するように設定するスクリプト [setup-iptables-for-lxd-with-docker.sh](https://github.com/hnakamur/setup-my-ubuntu-desktop/blob/acea2b1b7fe854b00654a47a65a7db10482fb435/setup-iptables-for-lxd-with-docker.sh) を書きました。

このスクリプトでは以下のような systemd の service 定義ファイルを `/etc/systemd/system/iptables-for-lxd-with-docker.service` というファイル名で作成します。

```
[Unit]
Description=Add iptables rules for LXD coexisting with Docker
After=docker.service

[Service]
Type=oneshot
# https://discuss.linuxcontainers.org/t/lxd-and-docker-firewall-redux-how-to-deal-with-forward-policy-set-to-drop/9953/7
ExecStart=iptables -I FORWARD -o lxdbr0 -m comment --comment "generated for LXD network lxdbr0" -j ACCEPT
ExecStart=iptables -I FORWARD 2 -i lxdbr0 -m comment --comment "generated for LXD network lxdbr0" -j ACCEPT

[Install]
WantedBy=multi-user.target
```

`After=docker.service` によってDockerのサービスが起動してDocker用のiptables設定が投入された後に実行されるようにしています。

iptablesコマンドを実行するだけなのでTypeはoneshotとし、ExecStartは複数指定可能なので2つのコマンドを実行するのに2つのExecStartを使っています。

`/etc/systemd/system/iptables-for-lxd-with-docker.service` を作成した後、以下のコマンドでOS起動時に自動実行されるように登録します。

```
sudo systemctl daemon-reload
sudo systemctl enable --now iptables-for-lxd-with-docker
```

また初回はその場でも実行したいので `systemctl enable` の `--now` オプションを使っています。これは [(小ネタ) systemctlでサービスの有効化と起動を同時に設定 - zaki work log](https://zaki-hmkc.hatenablog.com/entry/2020/03/19/183459) で知りました。
