---
title: "IncusのUbuntuコンテナでcloud-initを使ってIPv6を無効化"
date: 2024-11-17T17:51:14+09:00
---
## 手順

```
incus launch images:ubuntu/24.04/cloud "$container_name" \
  -c user.network-config="#cloud-config
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      dhcp-identifier: mac
      link-local: [ ipv4 ]"
```

## メモ

### 試したけど良くなかった方法

[Disable IPv6 address on certain containers - Incus - Linux Containers Forum](https://discuss.linuxcontainers.org/t/disable-ipv6-address-on-certain-containers/21485/6)で`ipv6.address`を`none`にしたネットワークを作って、コンテナ作成時にそのネットワークを指定するという方法があり試してみました。
しかしリンクローカルのIPv6アドレスがついてしまいました。

### 冒頭の手順についての補足
その後、[ubuntu serverでipv6を無効にする – ブーログ](https://ambiesoft.com/blog/archives/5978#primary)でnetplanで`link-local`を`[ ipv4 ]`にするという方法を知りました。
[YAML configuration - Netplan documentation](https://netplan.readthedocs.io/en/latest/netplan-yaml/)も確認し、試してみるとこちらはうまくいきました。

通常のIncusのUbuntuコンテナ(`images:ubuntu/24.04`)では
https://github.com/lxc/lxc-ci/blob/2a6c9cdef744c05bec739bbdde94e486308831ee/images/ubuntu.yaml#L332-L345
の内容で `/etc/netplan/10-lxc.yaml` が作られていました。

cloud-initを使うためには`images:ubuntu/24.04/cloud`と`/cloud`つきのイメージを使う必要があります。

ということで冒頭の手順になりました。
