---
title: "IncusのDebian 12コンテナでpingが遅かったのをsystemd-resolvedのLLMNRを無効にしたら解決"
date: 2024-04-29T16:13:56+09:00
draft: false
---

## IncusのDebian 12コンテナでpingが遅かった

以下のようにpingが出力する行の`time=`の値は遅くないのですが、
各行を出力する間隔が非常に遅い状態でした。

```bash
root@debian12:~# time ping -c 3 iij.ad.jp
PING iij.ad.jp (202.232.2.191) 56(84) bytes of data.
64 bytes from 202.232.2.191: icmp_seq=1 ttl=57 time=5.95 ms
64 bytes from 202.232.2.191: icmp_seq=2 ttl=57 time=9.26 ms
64 bytes from 202.232.2.191: icmp_seq=3 ttl=57 time=7.99 ms

--- iij.ad.jp ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 20036ms
rtt min/avg/max/mdev = 5.950/7.733/9.264/1.364 ms

real    0m21.073s
user    0m0.004s
sys     0m0.000s
```

## ChatGPT 4に相談しつつ調査

実際はいろいろ試行錯誤したのですが、ここでは整理して書きます。

iij.ad.jpのIPアドレスを指定すると遅くないことがわかりました。

```
root@debian12:~# time ping -c 3 202.232.2.191
PING 202.232.2.191 (202.232.2.191) 56(84) bytes of data.
64 bytes from 202.232.2.191: icmp_seq=1 ttl=57 time=5.85 ms
64 bytes from 202.232.2.191: icmp_seq=2 ttl=57 time=6.08 ms
64 bytes from 202.232.2.191: icmp_seq=3 ttl=57 time=6.13 ms

--- 202.232.2.191 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 5.849/6.019/6.127/0.122 ms

real    0m2.013s
user    0m0.004s
sys     0m0.000s
```

同じIncusの環境内の Ubuntu 24.04 コンテナではホスト名を指定しても
遅くありませんでした。
```
root@numbat:~# time ping -6 -c 3 iij.ad.jp                                                                
PING iij.ad.jp (2001:240:bb81::10:191) 56 data bytes
64 bytes from 2001:240:bb81::10:191: icmp_seq=1 ttl=54 time=5.34 ms
64 bytes from 2001:240:bb81::10:191: icmp_seq=2 ttl=54 time=5.08 ms
64 bytes from 2001:240:bb81::10:191: icmp_seq=3 ttl=54 time=5.33 ms

--- iij.ad.jp ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2095ms
rtt min/avg/max/mdev = 5.083/5.251/5.343/0.119 ms

real    0m2.104s
user    0m0.004s
sys     0m0.000s
```

Debian 12コンテナ内で tcpdump を取りながら ping を実行すると、
DNSの逆引きが遅いことがわかりました。

```
root@debian12:~# time ping -c 1 iij.ad.jp
PING iij.ad.jp (202.232.2.191) 56(84) bytes of data.
64 bytes from 202.232.2.191: icmp_seq=1 ttl=57 time=5.98 ms

--- iij.ad.jp ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 5.982/5.982/5.982/0.000 ms

real    0m10.005s
user    0m0.004s
sys     0m0.000s
```

```
root@debian12:~# sudo tcpdump -i any -n 'port 53'
tcpdump: data link type LINUX_SLL2
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on any, link-type LINUX_SLL2 (Linux cooked v2), snapshot length 262144 bytes
06:29:00.227772 lo    In  IP 127.0.0.1.59882 > 127.0.0.53.53: 48407+ [1au] A? iij.ad.jp. (38)
06:29:00.227790 lo    In  IP 127.0.0.1.59882 > 127.0.0.53.53: 25868+ [1au] AAAA? iij.ad.jp. (38)
06:29:00.228250 lo    In  IP 127.0.0.53.53 > 127.0.0.1.59882: 48407 1/2/5 A 202.232.2.191 (180)
06:29:00.228501 lo    In  IP 127.0.0.53.53 > 127.0.0.1.59882: 25868 1/2/5 AAAA 2001:240:bb81::10:191 (192)
06:29:00.235127 lo    In  IP 127.0.0.1.52984 > 127.0.0.53.53: 11525+ [1au] PTR? 191.2.232.202.in-addr.arpa. (55)
06:29:05.240260 lo    In  IP 127.0.0.1.52984 > 127.0.0.53.53: 11525+ [1au] PTR? 191.2.232.202.in-addr.arpa. (55)
^C
6 packets captured
12 packets received by filter
0 packets dropped by kernel
```

digでも逆引きを試すとタイムアウトエラーになりました。
```
root@debian12:~# time dig -x 202.232.2.191
;; communications error to 127.0.0.53#53: timed out
;; communications error to 127.0.0.53#53: timed out
;; communications error to 127.0.0.53#53: timed out

; <<>> DiG 9.18.24-1-Debian <<>> -x 202.232.2.191
;; global options: +cmd
;; no servers could be reached


real    0m15.045s
user    0m0.012s
sys     0m0.008s
```

## systemd-resolved の LLMNR が Ubuntu 24.04 では無効だが Debian 12 では有効という差異に気づく

Ubuntu 24.04:
```
root@numbat:~# resolvectl status
Global
         Protocols: -LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
  resolv.conf mode: stub

Link 9 (eth0)
    Current Scopes: DNS
         Protocols: +DefaultRoute -LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
Current DNS Server: 10.41.177.1
       DNS Servers: 10.41.177.1 fd42:3fbb:de08:f160::1 fe80::216:3eff:fec5:55bc
        DNS Domain: incus
```

Debian 12:
```
root@debian12:~# resolvectl status                   
Global                                               
       Protocols: +LLMNR +mDNS -DNSOverTLS DNSSEC=no/unsupported
resolv.conf mode: stub                               
                                                     
Link 7 (eth0)                                        
    Current Scopes: DNS LLMNR/IPv4 LLMNR/IPv6        
         Protocols: +DefaultRoute +LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
Current DNS Server: 10.41.177.1                      
       DNS Servers: 10.41.177.1 fe80::216:3eff:fec5:55bc
        DNS Domain: incus
```

`eth0`の`Current Scopes`がUbuntu 24.04はDNSのみですが、Debian 12はDNSに加えて
LLMNR/IPv4 LLMNR/IPv6があります。
またProtocolsもUbuntu 24.04は-LLMNRに対しDebianは+LLMNRとなっています。

https://wiki.archlinux.jp/index.php/Systemd-resolved#LLMNR によると
> [Link-Local Multicast Name Resolution](https://en.wikipedia.org/wiki/Link-Local_Multicast_Name_Resolution) は Microsoft によって作られたホストネーム解決プロトコルです。

とのことです。

`/etc/systemd/resolved.conf` を見るとLLMNRはUbuntu 24.04コンテナでは
デフォルトで無効、Debian 12コンテナではデフォルトで有効でした。

```
root@numbat:~# grep '^#LLMNR=' /etc/systemd/resolved.conf
#LLMNR=no
```

```
root@debian12:~# grep '^#LLMNR=' /etc/systemd/resolved.conf                                                                                                                                                         
#LLMNR=yes
```

## systemd-resolved の LLMNR を無効にして解決

以下のコマンドでLLMNRを無効にしました。
```
root@debian12:~# sed -i '/#LLMNR=yes/a\
LLMNR=no' /etc/systemd/resolved.conf
root@debian12:~# systemctl restart systemd-resolved
```

これでホスト名を指定してpingを実行すると遅い問題が解消できました。

```
root@debian12:~# time ping -c 3 iij.ad.jp
PING iij.ad.jp (202.232.2.191) 56(84) bytes of data.
64 bytes from 202.232.2.191 (202.232.2.191): icmp_seq=1 ttl=57 time=5.98 ms
64 bytes from 202.232.2.191 (202.232.2.191): icmp_seq=2 ttl=57 time=5.61 ms
64 bytes from 202.232.2.191 (202.232.2.191): icmp_seq=3 ttl=57 time=6.17 ms

--- iij.ad.jp ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2004ms
rtt min/avg/max/mdev = 5.607/5.916/6.167/0.232 ms

real    0m2.015s
user    0m0.000s
sys     0m0.005s
```

## 余談

ちなみに、物理マシンの Debian 12 環境もあったのですが、そちらではこの問題は起きていませんでした。
DHCPで固定アドレスを付与していて`/etc/resolve.conf`の`nameserver`がDHCPサーバのアドレス
になっており、systemd-resolvedは使っていないからでした。

また、IncusでDebian 12の仮想マシンでも問題ありませんでした。こちらは
`/etc/systemd/resolved.conf`で`#LLMNR=no`とLLMNRがデフォルトで無効になっていました。

https://images.linuxcontainers.org/ からリンクされていた
https://github.com/lxc/lxc-ci を git clone して
git log -p して大文字小文字無視で llmnr で検索してみましたがヒットなしでした。

ChatGPT 4 は今回非常に頼りになりました。自力では解決できなかったと思います。感謝。
