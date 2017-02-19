Title: LXD で privileged な CentOS 7コンテナを作る
Date: 2016-10-22 18:54
Category: blog
Tags: lxd, centos
Slug: blog/2016/10/22/lxd-privileged-centos-container

小ネタのメモです。

先日 LXD 2.0.5 で CentOS 7 コンテナを起動して `journalctl -xe` を実行すると以下のようなエラーが出ていました。

```
Oct 22 09:53:58 centos systemd-sysctl[36]: Failed to write '16' to '/proc/sys/kernel/sysrq': Permission denied
Oct 22 09:53:58 centos systemd-sysctl[36]: Failed to write '1' to '/proc/sys/fs/protected_hardlinks': Permission denied
Oct 22 09:53:58 centos systemd-sysctl[36]: Failed to write '1' to '/proc/sys/kernel/core_uses_pid': Permission denied
Oct 22 09:53:58 centos systemd-sysctl[36]: Failed to write '1' to '/proc/sys/fs/protected_symlinks': Permission denied
Oct 22 09:53:58 centos systemd-remount-fs[35]: /bin/mount for / exited with exit status 32.
```

コンテナ作成時に以下のように config で `security.privileged` を true に設定しておけば出なくなりました。

```
lxc launch -c security.privileged=true images:centos/7/amd64 コンテナ名
```

設定の確認は以下のコマンドで行います。

```
$ lxc config show コンテナ名
name: centos
profiles:
- default
config:
  security.privileged: "true"
  volatile.base_image: d2a0b3cf928778ad1582ee1feb39a0bbcd57edce01a60868f04e78d959886d71
  volatile.eth0.hwaddr: 00:16:3e:b2:dc:5e
  volatile.last_state.idmap: '[]'
devices:
  root:
    path: /
    type: disk
ephemeral: false
```

もっと限定した設定でも対応可能かもしれませんが、とりあえずこれで。

## 2016-10-23 追記
security.privileged を true にするのは良くないと指摘されました。

{{<tweet 789838146083098625 >}}

CentOS にバグ報告というのはよくわからなかったので、LXDにイシューを立ててみました。
[CentOS 7 container gets errors like systemd-sysctl\[36\]: Failed to write '16' to '/proc/sys/kernel/sysrq': Permission denied · Issue #2544 · lxc/lxd](https://github.com/lxc/lxd/issues/2544)
