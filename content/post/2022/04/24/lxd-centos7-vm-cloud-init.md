---
title: "LXDでCentOS7の仮想マシンのネームサーバをcloud-initで設定"
date: 2022-04-24T09:05:35+09:00
---

## はじめに

Ubuntu 22.04 LTS はデフォルトで cgroup v2 を使っているので LXD で CentOS 7 のコンテナはそのままでは動きません。
一方、 CentOS 7 の仮想マシンはそのままではネームサーバが設定されなかったので cloud-init で設定する必要がありました。
ということで手順をメモしておきます。

## Ubuntu 22.04 LTS はそのままでは CentOS 7 のコンテナは動かない

デフォルトでは cgroup v2 なので cgroup v1 が必要な CentOS 7 のコンテナはそのままでは動きません。

具体的には `lxc launch images:centos/7 centos7` を試すと以下のようなエラーが出ました。

```
Error: The image used by this instance requires a CGroupV1 host system
```

[Error: The image used by this instance requires a CGroupV1 host system when using clustering - LXD - Linux Containers Forum](https://discuss.linuxcontainers.org/t/error-the-image-used-by-this-instance-requires-a-cgroupv1-host-system-when-using-clustering/13885) や [cgroups - ArchWiki](https://wiki.archlinux.org/title/Cgroups) によるとカーネルのブート引数に `systemd.unified_cgroup_hierarchy=0` を指定すれば使えるようになるらしいです。

[ImpishIndri/ReleaseNotes/Ja - Ubuntu Wiki](https://wiki.ubuntu.com/ImpishIndri/ReleaseNotes/Ja) によると Ubuntu 21.10 から cgroup v2 がデフォルトになったそうです。

## LXD で CentOS 7 の仮想マシンのネームサーバを cloud-init で設定

私は LTS を使っているので Ubuntu 22.04 LTS が cgroup v2 がデフォルトの初めての環境となります。
せっかくなのでこの状態で使ってみたいということで LXD で CentOS 7 をコンテナではなく仮想マシンで動かすことにしました。

LXD で使える CentOS 7 の仮想マシンイメージの一覧を `lxc image list -h` と
[How to use lxc image list - LXD - Linux Containers Forum](https://discuss.linuxcontainers.org/u/stgraber) を参考に以下のように確認しました。

```
$ lxc image list images: arch=amd64 type=disk-kvm.img centos/7
+-------------------------+--------------+--------+---------------------------------+--------------+-----------------+----------+-------------------------------+
|          ALIAS          | FINGERPRINT  | PUBLIC |           DESCRIPTION           | ARCHITECTURE |      TYPE       |   SIZE   |          UPLOAD DATE          |
+-------------------------+--------------+--------+---------------------------------+--------------+-----------------+----------+-------------------------------+
| centos/7 (3 more)       | 37bde9772123 | yes    | Centos 7 amd64 (20220423_19:21) | x86_64       | VIRTUAL-MACHINE | 402.69MB | Apr 23, 2022 at 12:00am (UTC) |
+-------------------------+--------------+--------+---------------------------------+--------------+-----------------+----------+-------------------------------+
| centos/7/cloud (1 more) | d5495dbcdb7f | yes    | Centos 7 amd64 (20220423_19:21) | x86_64       | VIRTUAL-MACHINE | 415.13MB | Apr 23, 2022 at 12:00am (UTC) |
+-------------------------+--------------+--------+---------------------------------+--------------+-----------------+----------+-------------------------------+
```

[cloud-init - LXD ドキュメント](https://lxd-ja.readthedocs.io/ja/latest/cloud-init/) で説明されているように ALIAS の最後に `/cloud` とついているのが cloud-init 対応のイメージです。

そこで `lxc launch images:centos/7/cloud centos7-cloud-vm` で仮想マシンを作成・起動後、 `lxc exec centos7-cloud-vm bash` で中に入ってみたら IP アドレスは設定されているのですが `/etc/resolv.conf` にネームサーバが設定されていない状態でした。

[cloud-init - LXD ドキュメント](https://lxd-ja.readthedocs.io/ja/latest/cloud-init/) と
[LXDとcloud-initを使ってコンテナインスタンスを自動作成する - Qiita](https://qiita.com/yo-yamada/items/74fff9418f681acace64) を参考に、cloud-init でネームサーバを設定して CentOS 7 の仮想マシンを作成・起動するスクリプトを書きました。

```
#!/bin/bash
set -eu

vm_name=centos7-cloud-vm

lxdbr0_ipv4_addr_with_mask=$(lxc network get lxdbr0 ipv4.address)
lxdbr0_ipv4_addr=$(echo $lxdbr0_ipv4_addr_with_mask | sed 's|/.*||')

config_file=/tmp/$vm_name-cloud-init.yml
cat > $config_file <<EOF
network:
  version: 1
  config:
    - type: physical
      name: eth0
      subnets:
        - type: dhcp
          control: auto
    - type: nameserver
      address: $lxdbr0_ipv4_addr
EOF

lxc init images:centos/7/cloud $vm_name --vm
lxc config set $vm_name cloud-init.network-config - < $config_file
lxc start $vm_name
```

ちなみに既に作成・起動済みの仮想マシンで再度 cloud-init を実行したい場合は [How to update user.network-config and re-run cloud-init to apply the new config? - LXD - Linux Containers Forum](https://discuss.linuxcontainers.org/t/how-to-update-user-network-config-and-re-run-cloud-init-to-apply-the-new-config/6204) に手順が書かれていました。

ネットワーク設定を変更したい場合は以下のようにします。cloud-init-config.yml は上記のスクリプトで作っているのと同じ形式のファイルを作成しておきます。

```
lxc config set $vm_name cloud-init.network-config - < cloud-init-config.yml
lxc exec $vm_name -- cloud-init clean
lxc config set $vm_name volatile.apply_template create
lxc restart $vm_name
```

なお、 LXD で仮想マシンで cloud-init を実行すると数十秒程度時間がかかり途中で再起動がかかるようです。

実行中に `lxc exec インスタンス名 bash` で仮想マシン内に入ろうとしてもエラーになったり、 `lxc list` で確認すると STATE が RUNNING だったのが STOPPED になってまた RUNNING になるという状況でした。
