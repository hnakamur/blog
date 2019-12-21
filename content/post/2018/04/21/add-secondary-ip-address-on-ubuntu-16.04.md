+++
title="Ubuntu16.04でセカンダリIPアドレス追加"
date = "2018-04-21T12:30:00+09:00"
tags = ["ubuntu", "linux", "network"]
categories = ["blog"]
+++


[networking - How do I add an additional IP address to /etc/network/interfaces? - Ask Ubuntu](https://askubuntu.com/questions/313877/how-do-i-add-an-additional-ip-address-to-etc-network-interfaces?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa) とそこでコメントされていた
[NetworkConfiguration - Debian Wiki の iproute2 method](https://wiki.debian.org/NetworkConfiguration#iproute2_method)
を見て試してみたメモです。

[NetworkConfiguration - Debian Wiki の iproute2 method](https://wiki.debian.org/NetworkConfiguration#iproute2_method) で書かれていたのは `/etc/network/interfaces` で同じネットワークインタフェース名に対して `iface` セクションを繰り返して複数書くという方式です。ドライバとハードウェアの組み合わせによっては正しく動かず危険とのことなので要注意です。

`/etc/network/interfaces` を管理者権限で編集します。

```console
sudo vim /etc/network/interfaces
```

私の手元の環境で `enp0s25` の設定を以下のようにして試してみました。

```text
auto enp0s25
iface enp0s25 inet static
    address 192.168.2.200
    netmask 255.255.255.0
    gateway 192.168.2.1
    dns-nameservers 192.168.2.1
iface enp0s25 inet static
    address 192.168.2.203
    netmask 255.255.255.0
```

ネットワーク再起動。

```console
sudo systemctl restart networking
```

IPアドレスは期待通りついていました。

```console
$ ip a s dev enp0s25 | grep 'inet '
    inet 192.168.2.200/24 brd 192.168.2.255 scope global enp0s25
    inet 192.168.2.203/24 brd 192.168.2.255 scope global secondary enp0s25
```

ですが、DNSの名前解決ができない状態でした。
具体的には `ping 8.8.8.8` はOKですが `ping ping google-public-dns-a.google.com` はNGでした。

[NetworkConfiguration - Debian Wiki の iproute2 method](https://wiki.debian.org/NetworkConfiguration#iproute2_method) のManual approachを試してみるとこちらでは問題なかったです。
が、 `label $IFACE:0` と `:0` 付きだと Legacy method と実質同じだったりしないのかなと気になりました。

`:0` を取って試してみようかとも思ったのですが、ふと思いついて以下のように2個めの `iface` にも `dns-nameservers` を書くようにしてみたら、DNSの名前解決もできました。

```text
auto enp0s25
iface enp0s25 inet static
    address 192.168.2.200
    netmask 255.255.255.0
    gateway 192.168.2.1
    dns-nameservers 192.168.2.1
iface enp0s25 inet static
    address 192.168.2.203
    netmask 255.255.255.0
    dns-nameservers 192.168.2.1
```

正しい方法かは不明ですが、とりあえず手元の環境ではこれでできたということでメモでした。
