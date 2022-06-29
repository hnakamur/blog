---
title: "snap 版 LXD が aa-exec: Permission denied でエラーの対処"
date: 2022-06-29T11:54:03+09:00
---

snap で入れた LXD で `lxc list` が `aa-exec: Permission denied` というエラーになったときの対処のメモです。正確なエラーメッセージは以下のとおりです。

```
$ lxc list
cat: /proc/self/attr/current: Permission denied
/snap/lxd/23155/commands/lxc: 6: exec: aa-exec: Permission denied
```

[Snapped LXD has stopped working - aa-exec: Permission denied - snap - snapcraft.io](https://forum.snapcraft.io/t/snapped-lxd-has-stopped-working-aa-exec-permission-denied/2356) の [最初のコメント](https://forum.snapcraft.io/t/snapped-lxd-has-stopped-working-aa-exec-permission-denied/2356/2) の手順を実行したら解消しました。

```
$ sudo snap connect lxd:lxd-support core:lxd-support
$ sudo systemctl restart snap.lxd.daemon
```

```
$ lxc list
+---------------+---------+------+------+-----------+-----------+
|     NAME      |  STATE  | IPV4 | IPV6 |   TYPE    | SNAPSHOTS |
+---------------+---------+------+------+-----------+-----------+
| ats-dev-focal | STOPPED |      |      | CONTAINER | 0         |
+---------------+---------+------+------+-----------+-----------+
| chromium-dev  | STOPPED |      |      | CONTAINER | 0         |
+---------------+---------+------+------+-----------+-----------+
| envoy-dev     | STOPPED |      |      | CONTAINER | 0         |
+---------------+---------+------+------+-----------+-----------+
```

OS のバージョンと LXD のバージョンをメモしておきます。

```
$ grep ^VERSION= /etc/os-release
VERSION="22.04 LTS (Jammy Jellyfish)"
$ snap list lxd
Name  Version      Rev    Tracking       Publisher   Notes
lxd   5.2-79c3c3b  23155  latest/stable  canonical✓  -
```
