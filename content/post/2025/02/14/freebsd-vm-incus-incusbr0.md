---
title: "ZFSを使っているUbuntuのIncus上でincusbr0を使ってFreeBSDの仮想マシンを動かす"
date: 2025-02-14T20:35:49+09:00
---

## はじめに

[ZFSを使っているUbuntuのIncus上でmacvlanを使ってFreeBSDの仮想マシンを動かす · hnakamur's blog](../freebsd-vm-incus-macvlan/)の続編です。

[FreeBSD VM under Incus on Debian :: agren.cc](https://agren.cc/p/freebsd-vm-incus/)からリンクされていた[No IPV4 address for freebsd vm - Incus - Linux Containers Forum](https://discuss.linuxcontainers.org/t/no-ipv4-address-for-freebsd-vm/21083/5)の情報を元にincusbr0（Incusが管理しているブリッジ）でFreeBSDのVMを使うメモです。

## incusbr0でFreeBSDのVMを使う際はtx checksumを無効にする必要がある

特に何もしない場合、incusbr0のtxのchecksumがonになっています。

```
$ ethtool --show-offload incusbr0 | grep -i checksum
rx-checksumming: off [fixed]
tx-checksumming: on
        tx-checksum-ipv4: off [fixed]
        tx-checksum-ip-generic: on
        tx-checksum-ipv6: off [fixed]
        tx-checksum-fcoe-crc: off [fixed]
        tx-checksum-sctp: off [fixed]
```

この状態で以下のコマンドでdefaultプロファイルに含まれるincusbr0を使ってVMを起動すると、DHCPでIPアドレスを受け取れない状態で起動されてしまいネットワークが使えません。

```
incus launch freebsd14-image vm1 --vm -c limits.cpu=2 -c limits.memory=2GB -c security.secureboot=false -d root,size=80GB --console
```

以下のコマンドでincusbr0のTXのチェックサムを無効にします。
```
sudo ethtool --offload incusbr0 tx off
```

{{< details summary="（詳細）man ethtoolの説明抜粋" >}}
`man ethtool`の説明を抜粋します。
```
       -K --features --offload
              Changes the offload parameters and other features of the specified network device.  The following fea‐
              ture names are built-in and others may be defined by the kernel.
…(略)…
           tx on|off
                  Specifies whether TX checksumming should be enabled.
```
{{< /details >}}

{{< details summary="（詳細）上記の実行例と事後確認" >}}
```
$ sudo ethtool --offload incusbr0 tx off
Actual changes:
tx-checksum-ip-generic: off
tx-tcp-segmentation: off [not requested]
tx-tcp-ecn-segmentation: off [not requested]
tx-tcp-mangleid-segmentation: off [not requested]
tx-tcp6-segmentation: off [not requested]
$ ethtool --show-offload incusbr0 | grep -i checksum
rx-checksumming: off [fixed]
tx-checksumming: off
        tx-checksum-ipv4: off [fixed]
        tx-checksum-ip-generic: off
        tx-checksum-ipv6: off [fixed]
        tx-checksum-fcoe-crc: off [fixed]
        tx-checksum-sctp: off [fixed]
```
{{< /details >}}

この状態で以下のようなコマンドを実行すると、ネットワークが使える状態で起動できます。
```
incus launch freebsd14-image vm1 --vm -c limits.cpu=2 -c limits.memory=2GB -c security.secureboot=false -d root,size=80GB --console
```

## OS起動時にincusbr0のtx checksumを無効にする手順

これが正しい手順かはわかりませんが、とりあえず動く方法を見つけたのでメモしておきます。

```
<<EOF sudo tee /etc/systemd/system/disable-incusbr0-tx-checksum.service > /dev/null
[Unit]
Description=Disable incusbr0 tx checksum for FreeBSD VMs
After=incus-startup.service
Requires=incus.socket

[Service]
Type=oneshot
ExecStart=ethtool --offload incusbr0 tx off

[Install]
WantedBy=multi-user.target
EOF
```

```
sudo systemctl daemon-reload
```

```
sudo systemctl enable disable-incusbr0-tx-checksum
```
