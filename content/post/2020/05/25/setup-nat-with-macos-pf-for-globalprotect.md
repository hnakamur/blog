---
title: "macOSのpfでGlobalProtect用にNATを設定する"
date: 2020-05-25T14:57:27+09:00
---

## はじめに

macOS で [GlobalProtect - Palo Alto Networks](https://www.paloaltonetworks.jp/products/secure-the-network/subscriptions/globalprotect) でVPNに接続した際に [Multipass](https://multipass.run/) で作成したHypervisor.frameworkベースのVMとそのVM上のLXDコンテナからの通信をNATにする方法を調べたのでメモです。

[Troubleshooting networking on macOS | Multipass documentation](https://multipass.run/docs/troubleshooting-networking-on-macos) の "Potential workaround for VPN conflicts" に書いてありました。

## GlobalProtect のネットワークインターフェース名を ifconfig で確認

GlobalProtect でVPNに接続した状態で、以下のコマンドを実行して GlobalProtect のネットワークインターフェース名を確認します。

```console
ifconfig
```

私の環境では `gpd0` でした。
また WiFi のインターフェース名は `en0` で、 Hypervisor.framework のブリッジのインターフェース名は `bridge100` でした。

## pf.conf を編集して反映

`man pf.conf` すると `pf.conf` は `packet filter configuration file` とのことです。 [PF (firewall) - Wikipedia](https://en.wikipedia.org/wiki/PF_\(firewall%29) も参照。 

`/etc/pf.conf` は変更前はコメントを除くと以下のようになっていました。

```text
scrub-anchor "com.apple/*"
nat-anchor "com.apple/*"
rdr-anchor "com.apple/*"
dummynet-anchor "com.apple/*"
anchor "com.apple/*"
load anchor "com.apple" from "/etc/pf.anchors/com.apple"
```

これを以下のコマンドを実行し

```console
sudo vim /etc/pf.conf
```

以下のように編集しました。

```text
scrub-anchor "com.apple/*"
nat-anchor "com.apple/*"
table <privbutvm> const { 10/8, 172.16/12, 192.168/16, !192.168.254/24, !192.168.255/24 }
table <myglobal> const { 0/0, !10/8, !172.16/12, !192.168/16 }
nat on gpd0 from bridge100:network to <privbutvm> -> (gpd0)
nat on en0 from bridge100:network to <myglobal> -> (en0)
rdr-anchor "com.apple/*"
dummynet-anchor "com.apple/*"
anchor "com.apple/*"
load anchor "com.apple" from "/etc/pf.anchors/com.apple"
```
`192.168.254/24` と `192.168.255/24` は [macOSでHypervisor.frameworkのVMのサブネットIPアドレスを変える · hnakamur's blog](/blog/2020/05/25/change-macos-hypervisor.framework-vm-subnet-ip-address/) に書いたようにVMとLXDコンテナーのネットワークです。これを除いたプライベートアドレスは GlobalProtect に、グローバルアドレスは WiFi に向けてそれぞれNATを設定しました。

以下のコマンドで反映します。

```console
sudo pfctl -f /etc/pf.conf
```

実行すると以下のようなメッセージが出ました。

```console
% sudo pfctl -f /etc/pf.conf
pfctl: Use of -f option, could result in flushing of rules
present in the main ruleset added by the system at startup.
See /etc/pf.conf for further details.
No ALTQ support in kernel
ALTQ related functions disabled
```

## macOSでtcpdumpを実行しつつ VMやLXDコンテナから ping で動作確認

macOS 側で以下のように tcpdump を実行しておきます。
`-k A` を指定しておくとインターフェース名も出力されるので便利です。

```console
sudo tcpdump -n -k A -vvv -i any icmp
```

対象のインターフェースを限定したいが複数指定したい場合は `man tcpdump` に書いてある pktap を使ってこの後に複数のインターフェースを指定できます。

```console
sudo tcpdump -n -k A -vvv -i pktap,bridge100,gpd0,en0 icmp
```

LXDコンテナ内からグローバルアドレスに ping を打ったときの出力は以下のような感じでした。
`ping 8.8.8.8` で試しました。 `192.168.2.207` は `en0` についている IP アドレスです。

```
15:28:09.233218 (en7, svc BE, in) IP (tos 0x0, ttl 64, id 39934, offset 0, flags [DF], proto ICMP (1), length 84)
    192.168.254.2 > 8.8.8.8: ICMP echo request, id 9752, seq 1, length 64
15:28:09.233225 (bridge100, svc BE, in) IP (tos 0x0, ttl 64, id 39934, offset 0, flags [DF], proto ICMP (1), length 84)
    192.168.254.2 > 8.8.8.8: ICMP echo request, id 9752, seq 1, length 64
15:28:09.233277 (en0, proc :0:, eproc :0:, svc BE, out) IP (tos 0x0, ttl 63, id 39934, offset 0, flags [none], proto ICMP (1), length 84)
    192.168.2.207 > 8.8.8.8: ICMP echo request, id 35952, seq 1, length 64
15:28:09.238693 (en0, svc BE, in) IP (tos 0x0, ttl 57, id 0, offset 0, flags [none], proto ICMP (1), length 84)
    8.8.8.8 > 192.168.2.207: ICMP echo reply, id 35952, seq 1, length 64
15:28:09.238717 (bridge100, proc :0:, eproc :0:, svc BE, out) IP (tos 0x0, ttl 56, id 0, offset 0, flags [none], proto ICMP (1), length 84, bad cksum 0 (->b3ee)!)
    8.8.8.8 > 192.168.254.2: ICMP echo reply, id 9752, seq 1, length 64
15:28:09.238720 (en7, proc :0:, eproc :0:, svc BE, out) IP (tos 0x0, ttl 56, id 0, offset 0, flags [none], proto ICMP (1), length 84)
```

LXDコンテナ内から VPN 内のプライベートアドレス (XXX.XXX.XXX.XXX とします) に ping を打ったときの出力は以下のような感じでした。 gpd0 のアドレスを YYY.YYY.YYY.YYY とします。

```
15:25:30.464462 (en7, svc BE, in) IP (tos 0x0, ttl 63, id 44537, offset 0, flags [DF], proto ICMP (1), length 84)
    192.168.254.2 > XXX.XXX.XXX.XXX: ICMP echo request, id 3367, seq 1, length 64
15:25:30.464468 (bridge100, svc BE, in) IP (tos 0x0, ttl 63, id 44537, offset 0, flags [DF], proto ICMP (1), length 84)
    192.168.254.2 > XXX.XXX.XXX.XXX: ICMP echo request, id 3367, seq 1, length 64
15:25:30.464517 (gpd0, proc :0:, eproc :0:, svc BE, out) IP (tos 0x0, ttl 62, id 44537, offset 0, flags [none], proto ICMP (1), length 84)
    YYY.YYY.YYY.YYY > XXX.XXX.XXX.XXX: ICMP echo request, id 56265, seq 1, length 64
15:25:30.495240 (gpd0, svc BE, in) IP (tos 0x0, ttl 60, id 38184, offset 0, flags [none], proto ICMP (1), length 84)
    XXX.XXX.XXX.XXX > YYY.YYY.YYY.YYY: ICMP echo reply, id 56265, seq 1, length 64
15:25:30.495273 (bridge100, proc :0:, eproc :0:, svc BE, out) IP (tos 0x0, ttl 59, id 38184, offset 0, flags [none], proto ICMP (1), length 84, bad cksum 0 (->1f8a)!)
    XXX.XXX.XXX.XXX > 192.168.254.2: ICMP echo reply, id 3367, seq 1, length 64
15:25:30.495277 (en7, proc :0:, eproc :0:, svc BE, out) IP (tos 0x0, ttl 59, id 38184, offset 0, flags [none], proto ICMP (1), length 84)
    XXX.XXX.XXX.XXX > 192.168.254.2: ICMP echo reply, id 3367, seq 1, length 64
```

`en7` は `ifconfig` で確認すると以下のようになっています（MACアドレスは伏せてます）が、これが何のインターフェースなのかは私はわかっていません。

```
en7: flags=8b63<UP,BROADCAST,SMART,RUNNING,PROMISC,ALLMULTI,SIMPLEX,MULTICAST> mtu 1500
        options=400<CHANNEL_IO>
        ether xx:xx:xx:xx:xx:xx 
        media: autoselect
        status: active
```

NATを設定する前は `192.168.254.2` からターゲットのIPアドレスへのパケットだけがあって、 `en0` や `gpd0` のアドレスからターゲットのIPアドレスへのパケットはありませんでした。

## ついでにルーティングの表示・追加・削除コマンドをメモ

[Troubleshooting networking on macOS | Multipass documentation](https://multipass.run/docs/troubleshooting-networking-on-macos) を見て最初はルーティングも変更してみたので、ついでにメモ。

ルーティング表示

```console
netstat -rn
```

ルーティング追加（ターゲットは `-interface bridge100` のような指定方法もある。また `-static` というオプションもある）。

```console
sudo route add -net 192.168.255.0/24 192.168.64.2
```


ルーティング削除

```console
sudo route delete -net 192.168.255.0/24
```
