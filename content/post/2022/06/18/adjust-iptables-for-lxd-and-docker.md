---
title: "LXDとDockerを同時利用するためにiptables設定を調整"
date: 2022-06-18T15:49:54+09:00
lastmod: 2024-04-29T02:15:50:00+09:00
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

## iptablesの設定の自動化 (2022-09-23追記)

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

## nftablesのコマンドを直接使うよう切り替え (2022-10-25追記)

### Ubuntu 21.10 以降は iptables は nftables のラッパになっている

[ufw - Ubuntu 21.10 switched to nftables, so why is iptables still available? - Ask Ubuntu](https://askubuntu.com/questions/1370901/ubuntu-21-10-switched-to-nftables-so-why-is-iptables-still-available) と [Impish Indri Release Notes - Release - Ubuntu Community Hub](https://discourse.ubuntu.com/t/impish-indri-release-notes/21951) によると Ubuntu 21.10 から nftables がデフォルトのファイアウォールとして使用されています。

Ubuntu 22.04 LTS でも iptables コマンドはまだ使えますが、 `/usr/sbin/iptables` からシンボリックリンクをたどると `/usr/sbin/xtables-nft-multi` となっています。

```
$ ls -l /usr/sbin/iptables
lrwxrwxrwx 1 root root 26 May  7 18:14 /usr/sbin/iptables -> /etc/alternatives/iptables
$ ls -l /etc/alternatives/iptables
lrwxrwxrwx 1 root root 22 May  7 18:14 /etc/alternatives/iptables -> /usr/sbin/iptables-nft
$ ls -l /usr/sbin/iptables-nft
lrwxrwxrwx 1 root root 17 May  7 18:14 /usr/sbin/iptables-nft -> xtables-nft-multi
```

`man xtables-nft-multi` すると iptables using nftables kernel api とのことでした。

### nft コマンドを使う

実は2022-09-23に追記したときも、一旦 nftables のネイティブの nft コマンドを使う手順も調べていて、そちらも書こうかと思ったのですが、 Ubuntu 20.04 LTS を使うときは iptables になるから iptables のほうだけで良いかと思って書いてませんでした(あと記事が長くなりすぎかなと思って)。

が、今日 `sudo iptables --flush` しても `sudo iptables -n -L` ではルールが空になっているように見えるけど `sudo nft list table ip nat` ではDockerのルールが残っているというケースに遭遇したので、やっぱり直接 nft を使うようにしたほうが良いなと思いました。

[Moving from iptables to nftables - nftables wiki](https://wiki.nftables.org/wiki-nftables/index.php/Moving_from_iptables_to_nftables) の iptables-translate コマンドを使うと iptables のコマンドを nft のコマンドに変換できます。

実行例:

```
$ iptables-translate -I FORWARD -o lxdbr0 -m comment --comment "generated for LXD network lxdbr0" -j ACCEPT
nft insert rule ip filter FORWARD oifname "lxdbr0" counter accept comment \"generated for LXD network lxdbr0\"
$ iptables-translate -I FORWARD 2 -i lxdbr0 -m comment --comment "generated for LXD network lxdbr0" -j ACCEPT
nft insert rule ip filter FORWARD iifname "lxdbr0" counter accept comment \"generated for LXD network lxdbr0\"
```

というわけで上記のサービス定義ファイルを nft で書き直すと以下のようになります。
ファイル名は `/etc/systemd/system/nftables-for-lxd-with-docker.service` に変えました。

```
[Unit]
Description=Add iptables rules for LXD coexisting with Docker
After=docker.service

[Service]
Type=oneshot
# https://discuss.linuxcontainers.org/t/lxd-and-docker-firewall-redux-how-to-deal-with-forward-policy-set-to-drop/9953/7
ExecStart=nft insert rule ip filter FORWARD oifname "lxdbr0" counter accept comment \"generated for LXD network lxdbr0\"
ExecStart=nft insert rule ip filter FORWARD iifname "lxdbr0" counter accept comment \"generated for LXD network lxdbr0\"

[Install]
WantedBy=multi-user.target
```

nft の使い方は [Quick reference-nftables in 10 minutes - nftables wiki](https://wiki.nftables.org/wiki-nftables/index.php/Quick_reference-nftables_in_10_minutes) がわかりやすかったです。

まずはテーブル一覧を表示。

```
$ sudo nft list tables
table ip nat
table ip filter
table inet lxd
```

テーブルの中身の確認の例。

```
$ sudo nft list table ip filter
table ip filter {
        chain DOCKER {
                iifname != "br-6c11e51eda49" oifname "br-6c11e51eda49" meta l4proto tcp ip daddr 172.27.0.2 tcp dport 6443 counter packets 0 bytes 0 accept
        }

        chain DOCKER-ISOLATION-STAGE-1 {
                iifname "docker0" oifname != "docker0" counter packets 0 bytes 0 jump DOCKER-ISOLATION-STAGE-2
                iifname "br-bf4815aedad2" oifname != "br-bf4815aedad2" counter packets 0 bytes 0 jump DOCKER-ISOLATION-STAGE-2
…(略)…
        }

        chain DOCKER-ISOLATION-STAGE-2 {
                oifname "docker0" counter packets 0 bytes 0 drop
                oifname "br-bf4815aedad2" counter packets 0 bytes 0 drop
…(略)…
        }

        chain FORWARD {
                type filter hook forward priority filter; policy drop;
                iifname "lxdbr0" counter packets 102 bytes 19387 accept comment "generated for LXD network lxdbr0"
                oifname "lxdbr0" counter packets 0 bytes 0 accept comment "generated for LXD network lxdbr0"
…(略)…
```

`/etc/systemd/system/nftables-for-lxd-with-docker.service` で指定したルールが追加されていることを確認できました。

この状態でのコンテナからインターネットと、コンテナ間の通信の動作確認。
コンテナからインターネット上のIPv4アドレスと他のコンテナのIPv4アドレスを指定して通信が通ることを確認。
コンテナから他のコンテナ名を指定して通信すると IPv6 アドレスでの通信になっている。

```
$ lxc list
+-----------+---------+---------------------+-----------------------------------------------+-----------+-----------+
|   NAME    |  STATE  |        IPV4         |                     IPV6                      |   TYPE    | SNAPSHOTS |
+-----------+---------+---------------------+-----------------------------------------------+-----------+-----------+
| apt-cache | STOPPED |                     |                                               | CONTAINER | 0         |
+-----------+---------+---------------------+-----------------------------------------------+-----------+-----------+
| server1   | RUNNING | 10.2.210.94 (eth0)  | fd42:b136:20b6:1c77:216:3eff:feca:f6f5 (eth0) | CONTAINER | 0         |
+-----------+---------+---------------------+-----------------------------------------------+-----------+-----------+
| server2   | RUNNING | 10.2.210.121 (eth0) | fd42:b136:20b6:1c77:216:3eff:feaf:a4fd (eth0) | CONTAINER | 0         |
+-----------+---------+---------------------+-----------------------------------------------+-----------+-----------+
| server3   | RUNNING | 10.2.210.21 (eth0)  | fd42:b136:20b6:1c77:216:3eff:fe24:8455 (eth0) | CONTAINER | 0         |
+-----------+---------+---------------------+-----------------------------------------------+-----------+-----------+
$ lxc exec server1 -- ping -c 1 8.8.8.8
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=6.19 ms

--- 8.8.8.8 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 6.189/6.189/6.189/0.000 ms
$ lxc exec server1 -- ping -c 1 10.2.210.121
PING 10.2.210.121 (10.2.210.121) 56(84) bytes of data.
64 bytes from 10.2.210.121: icmp_seq=1 ttl=64 time=0.064 ms

--- 10.2.210.121 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.064/0.064/0.064/0.000 ms
$ lxc exec server1 -- ping -c 1 server2
PING server2(server2.lxd (fd42:b136:20b6:1c77:216:3eff:feaf:a4fd)) 56 data bytes
64 bytes from server2.lxd (fd42:b136:20b6:1c77:216:3eff:feaf:a4fd): icmp_seq=1 ttl=64 time=0.048 ms

--- server2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.048/0.048/0.048/0.000 ms
```

## やっぱりiptablesコマンドを使うように戻した (2024-04-29追記)

Debian 12のIncusで同じことを試していたら `sudo nft list table ip filter` や `sudo nft list ruleset` の結果に
```
# Warning: table ip filter is managed by iptables-nft, do not touch!
```
という警告が出ていることに気づきました。

Dockerがiptablesでルールを追加する結果iptables-nftで管理されているので、
そこにルールを追加する際もiptablesを使うほうが無難そうということでそちらに戻しました。

設定するスクリプトを
https://github.com/hnakamur/setup-my-ubuntu-desktop/blob/1d7c4a4cfd2af2dd8ecb20991d03c97f48bd8c53/setup-iptables-for-lxd-with-docker.sh
に置きました。
