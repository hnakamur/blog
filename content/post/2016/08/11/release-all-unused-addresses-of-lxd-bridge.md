+++
Categories = []
Description = ""
Tags = ["lxd","dnsmasq"]
date = "2016-08-11T22:58:21+09:00"
title = "LXDのDHCPで使っていないIPアドレスを一括で解放するスクリプトを書いた"

+++
[LXDコンテナで固定IPアドレスを使うための設定 · hnakamur's blog at github](/blog/2016/05/07/how-to-use-fixed-ip-address-for-a-lxd-container/) の設定を行ってもIPアドレスが指定通りにならないことがありました。

`journal -xe` で見てみると

```
Aug 11 22:46:55 bai1b7faf04 dnsmasq-dhcp[11082]: not using configured address 10.155.92.102 because it is leased to 00:16:3e:1e:08:8a
```

というメッセージが出ていて、他のMACアドレスに貸出中になっています。

ググってみると [\[SOLVED\] dnsmasq force release/renew of dhcp clients, how?](http://www.linuxquestions.org/questions/linux-newbie-8/dnsmasq-force-release-renew-of-dhcp-clients-how-933535/) に回答がありました。

## 使っていないIPアドレスを手動で消す

```
sudo systemctl stop lxd-bridge
```

で止めて

```
sudo vi /var/lib/lxd-bridge/dnsmasq.lxdbr0.leases
```

で使っていないIPアドレスの行を全て削除します。

その後

```
sudo systemctl start lxd-bridge
```

で再起動します。

## 自動で消すスクリプトも書きました

これでよいかと思ったら、
http://lists.thekelleys.org.uk/pipermail/dnsmasq-discuss/2013q3/007356.html
を見て `dhcp_release` というコマンドを使えば `lxd-bridge` の再起動が不要なことを知りました。

ということでスクリプトを書いてみました。
https://gist.github.com/hnakamur/7ed3f7c6175817b633586a1b468bd5c1

```
#!/bin/sh
set -eu

# Set value of LXD_BRIDGE
. /etc/default/lxd-bridge

addr_list_file=/tmp/lxd-addr-list.`date +%Y-%m-%dT%H:%M:%S`
lxc list | awk '$4=="RUNNING"{print $6}' > $addr_list_file
cleanup() {
  rm $addr_list_file
}
trap cleanup EXIT

awk -v addr_list_file=$addr_list_file -v interface=$LXD_BRIDGE '{
  mac_addr = $2
  addr = $3
  ret = system(sprintf("awk -v addr=%s '\''BEGIN{rc=1} $1==addr{rc=0} END{exit rc}'\'' %s", addr,  addr_list_file))
  if (ret == 1) {
    system(sprintf("sudo dhcp_release %s %s %s", interface, addr, mac_addr))
  }
}' /var/lib/lxd-bridge/dnsmasq.$LXD_BRIDGE.leases
```

Ubuntu 16.04 の場合 `dhcp_release` コマンドを使うには以下のように `dnsmasq-utils` パッケージをインストールする必要があります。

```
sudo apt -y install dnsmasq-utils
```
