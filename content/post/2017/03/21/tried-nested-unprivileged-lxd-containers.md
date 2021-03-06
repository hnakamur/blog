+++
title="LXDでネストした非特権コンテナを試してみた"
date = "2017-03-21T21:00:00+09:00"
tags = ["lxd"]
categories = ["blog"]
+++



## はじめに

https://twitter.com/ten_forward/status/844107303099932676

https://twitter.com/ten_forward/status/844142416282054658

というツイートを受けて自分でもLXDでネストした非特権コンテナを試してみました。
環境はUbuntu 16.04です。
lxdのバージョンは2.0.9です。

```console
$ uname -a
Linux bai1b7faf04 4.4.0-53-generic #74-Ubuntu SMP Fri Dec 2 15:59:10 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux
$ lxd --version
2.0.9
```

## subuidとsubgidファイルを編集しつつ作成

まずは [Nested containers in LXD | Ubuntu Insights](https://insights.ubuntu.com/2015/10/30/nested-containers-in-lxd/) に従って `/etc/subuid` と `/etc/subgid` を編集しつつ試しました。

一段ネストして `lxc launch images:ubuntu/xenial c2` するところで、


```console
error: Get https://images.linuxcontainers.org/streams/v1/index.json: x509: failed to load system roots and no roots provided
```

というエラーが出ました。 これは [失敗: Alpine 3.5.1上でLXD 2.8を使おうと試行錯誤した - Qiita](http://qiita.com/tukiyo3/items/2833e6c5cdf1b8ae9eeb) の「トラブルシューティング」にあるように `ca-certificates` と `openssl` をインストールしたら解消しました。

その後3段目まで無事作れました。そこで調子に乗って4段目も作ってみると、なんと作れてしまいました。
しかも `lxc launch` の際に `-c security.nesting=true` を指定してなかったような気がします。

[Nested containers in LXD | Ubuntu Insights](https://insights.ubuntu.com/2015/10/30/nested-containers-in-lxd/) の記事にあった uid の話は関係なかったのでしょうか。

## subuidとsubgidファイルを元に戻して再度実験

```console
$ lxc launch images:ubuntu/xenial c1
Creating c1
Starting c1
$ lxc exec c1 bash
root@c1:~#
```

.. code-block:: console

    root@c1:~# apt update && apt install -y lxd ca-certificates openssl
    root@c1:~# lxd init
    # 質問やダイアログは全てEnterキーで進む

```console
root@c1:~# su - ubuntu
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

ubuntu@c1:~$ lxc list
Generating a client certificate. This may take a minute...
If this is your first time using LXD, you should also run: sudo lxd init
To start your first container, try: lxc launch ubuntu:16.04

+------+-------+------+------+------+-----------+
| NAME | STATE | IPV4 | IPV6 | TYPE | SNAPSHOTS |
+------+-------+------+------+------+-----------+
ubuntu@c1:~$ lxc launch images:ubuntu/xenial c2
Creating c2
Starting c2
error: Error calling 'lxd forkstart c2 /var/lib/lxd/containers /var/log/lxd/c2/lxc.conf': err='exit status 1'
  lxc 20170321123841.200 ERROR lxc_utils - utils.c:safe_mount:1751 - Permission denied - Failed to mount proc onto /usr/lib/x86_64-linux-gnu/lxc/proc
  lxc 20170321123841.200 ERROR lxc_conf - conf.c:lxc_mount_auto_mounts:801 - Permission denied - error mounting proc on /usr/lib/x86_64-linux-gnu/lxc/proc flags 14
  lxc 20170321123841.200 ERROR lxc_conf - conf.c:lxc_setup:3859 - failed to setup the automatic mounts for 'c2'
  lxc 20170321123841.200 ERROR lxc_start - start.c:do_start:811 - Failed to setup container "c2".
  lxc 20170321123841.200 ERROR lxc_sync - sync.c:__sync_wait:57 - An error occurred in another process (expected sequence number 3)
  lxc 20170321123841.239 ERROR lxc_start - start.c:__lxc_start:1346 - Failed to spawn container "c2".
  lxc 20170321123841.801 ERROR lxc_conf - conf.c:run_buffer:405 - Script exited with status 1.
  lxc 20170321123841.801 ERROR lxc_start - start.c:lxc_fini:546 - Failed to run lxc.hook.post-stop for container "c2".

Try `lxc info --show-log local:c2` for more info
```

## 1段目のみsecurity.nestingはつけて再実験

```console
$ lxc launch images:ubuntu/xenial c1 -c security.nesting=true
Creating c1
Starting c1
$ lxc exec c1 bash
root@c1:~# apt update && apt install -y lxd ca-certificates openssl
root@c1:~# lxd init
# 質問やダイアログは全てEnterキーで進む
```

.. code-block:: console

    root@c1:~# su - ubuntu
    ubuntu@c1:~$ lxc list
    Generating a client certificate. This may take a minute...
    If this is your first time using LXD, you should also run: sudo lxd init
    To start your first container, try: lxc launch ubuntu:16.04

    +------+-------+------+------+------+-----------+
    | NAME | STATE | IPV4 | IPV6 | TYPE | SNAPSHOTS |
    +------+-------+------+------+------+-----------+
    ubuntu@c1:~$ lxc launch images:ubuntu/xenial c2
    Creating c2
    Starting c2
    ubuntu@c1:~$ lxc exec c2 bash
    root@c2:~# apt update && apt install -y lxd ca-certificates openssl
    ...(略)...
    Setting up apparmor (2.10.95-0ubuntu2.5) ...
    update-rc.d: warning: start and stop actions are no longer supported; falling back to defaults
    Skipping profile in /etc/apparmor.d/disable: usr.sbin.rsyslogd
    /sbin/apparmor_parser: Unable to replace "/sbin/dhclient".  Permission denied; attempted to load a profile while confined?
    Skipping profile in /etc/apparmor.d/disable: usr.sbin.rsyslogd
    /sbin/apparmor_parser: Unable to replace "/sbin/dhclient".  Permission denied; attempted to load a profile while confined?
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    diff: /var/lib/apparmor/profiles/.apparmor.md5sums: No such file or directory
    Setting up rsync (3.1.1-3ubuntu1) ...
    Setting up lxd-client (2.0.9-0ubuntu1~16.04.2) ...
    Setting up libfuse2:amd64 (2.9.4-1ubuntu3.1) ...
    Setting up lxcfs (2.0.6-0ubuntu1~16.04.1) ...
    Setting up squashfs-tools (1:4.3-3ubuntu2) ...
    Setting up uidmap (1:4.2-3.1ubuntu5) ...
    Setting up xz-utils (5.1.1alpha+20120614-2ubuntu2) ...
    update-alternatives: using /usr/bin/xz to provide /usr/bin/lzma (lzma) in auto mode
    Setting up openssl (1.0.2g-1ubuntu4.6) ...
    Setting up ca-certificates (20160104ubuntu1) ...
    Setting up libcap-ng0:amd64 (0.7.7-1) ...
    Setting up dbus (1.10.6-1ubuntu3.3) ...
    Setting up dns-root-data (2015052300+h+1) ...
    Setting up liblxc1 (2.0.7-0ubuntu1~16.04.2) ...
    Setting up lxd (2.0.9-0ubuntu1~16.04.2) ...
    apparmor_parser: Unable to replace "/usr/lib/lxd/lxd-bridge-proxy".  Permission denied; attempted to load a profile while confined?

    The default LXD bridge, lxdbr0, comes unconfigured by default.
    Only limited HTTP connectivity through a PROXY will be available.
    To go through the initial LXD configuration, run: lxd init

    Setting up lxc-common (2.0.7-0ubuntu1~16.04.2) ...
    apparmor.service is not active, cannot reload.
    invoke-rc.d: initscript apparmor, action "reload" failed.
    apparmor_parser: Unable to replace "/usr/bin/lxc-start".  Permission denied; attempted to load a profile while confined?

## 2段目もsecurity.nestingをつけて再実験

```console
root@c2:~# exit
ubuntu@c1:~$ lxc delete -f c2
ubuntu@c1:~$ lxc launch images:ubuntu/xenial c2 -c security.nesting=true
ubuntu@c1:~$ lxc exec c2 bash
root@c2:~# apt update && apt install -y lxd ca-certificates openssl
```

同じエラーが出ました。
とりあえず無視して続けてみました。

```console
root@c2:~# lxd init
# 質問やダイアログは全てEnterキーで進む
ubuntu@c2:~$ lxc launch images:ubuntu/xenial c3
ubuntu@c2:~$ lxc exec c3 bash
```

ホストでプロセスを確認して見ました。

```console
$ ps auxww | grep 'lxc exec c[1-3]'
hnakamur 10810  0.0  0.1 217644 16368 pts/25   Sl+  21:45   0:00 lxc exec c1 bash
101000   19687  0.0  0.0 208436 14836 pts/13   Sl+  21:54   0:00 lxc exec c2 bash
101000   26461  0.0  0.0 202800  8952 pts/1    Sl+  23:21   0:00 lxc exec c3 bash
```

## 1段目のみsecurity.nestingをつけて一からやり直し

```console
$ lxc delete -f c1
$ lxc launch images:ubuntu/xenial c1 -c security.nesting=true
$ lxc exec c1 bash
root@c1:~# apt update && apt install -y lxd ca-certificates openssl
root@c1:~# lxd init
# 質問やダイアログは全てEnterキーで進む
```

.. code-block:: console

    root@c1:~# su - ubuntu
    ubuntu@c1:~$ lxc launch images:ubuntu/xenial c2
    ubuntu@c1:~$ lxc exec c2 bash
    root@c2:~# apt update && apt install -y lxd ca-certificates openssl
    ...(略)...
    Skipping profile in /etc/apparmor.d/disable: usr.sbin.rsyslogd
    /sbin/apparmor_parser: Unable to replace "/sbin/dhclient".  Permission denied; attempted to load a profile while confined?
    Skipping profile in /etc/apparmor.d/disable: usr.sbin.rsyslogd
    /sbin/apparmor_parser: Unable to replace "/sbin/dhclient".  Permission denied; attempted to load a profile while confined?
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    sh: echo: I/O error
    diff: /var/lib/apparmor/profiles/.apparmor.md5sums: No such file or directory
    Setting up rsync (3.1.1-3ubuntu1) ...
    Setting up lxd-client (2.0.9-0ubuntu1~16.04.2) ...
    Setting up libfuse2:amd64 (2.9.4-1ubuntu3.1) ...
    Setting up lxcfs (2.0.6-0ubuntu1~16.04.1) ...
    Setting up squashfs-tools (1:4.3-3ubuntu2) ...
    Setting up uidmap (1:4.2-3.1ubuntu5) ...
    Setting up xz-utils (5.1.1alpha+20120614-2ubuntu2) ...
    update-alternatives: using /usr/bin/xz to provide /usr/bin/lzma (lzma) in auto mode
    Setting up openssl (1.0.2g-1ubuntu4.6) ...
    Setting up ca-certificates (20160104ubuntu1) ...
    Setting up libcap-ng0:amd64 (0.7.7-1) ...
    Setting up dbus (1.10.6-1ubuntu3.3) ...
    Setting up dns-root-data (2015052300+h+1) ...
    Setting up liblxc1 (2.0.7-0ubuntu1~16.04.2) ...
    Setting up lxd (2.0.9-0ubuntu1~16.04.2) ...
    apparmor_parser: Unable to replace "/usr/lib/lxd/lxd-bridge-proxy".  Permission denied; attempted to load a profile while confined?

    The default LXD bridge, lxdbr0, comes unconfigured by default.
    Only limited HTTP connectivity through a PROXY will be available.
    To go through the initial LXD configuration, run: lxd init

    Setting up lxc-common (2.0.7-0ubuntu1~16.04.2) ...
    apparmor.service is not active, cannot reload.
    invoke-rc.d: initscript apparmor, action "reload" failed.
    apparmor_parser: Unable to replace "/usr/bin/lxc-start".  Permission denied; attempted to load a profile while confined?
    Processing triggers for libc-bin (2.23-0ubuntu6) ...
    Processing triggers for systemd (229-4ubuntu16) ...
    Processing triggers for ureadahead (0.100.0-19) ...
    Processing triggers for ca-certificates (20160104ubuntu1) ...
    Updating certificates in /etc/ssl/certs...
    173 added, 0 removed; done.
    Running hooks in /etc/ca-certificates/update.d...
    done.
    root@c2:~#

```console
root@c2:~# lxd init
# 質問やダイアログは全てEnterキーで進む
...(略)...
apparmor_parser: Unable to replace "/usr/lib/lxd/lxd-bridge-proxy".  Permission denied; attempted to load a profile while confined?
LXD has been successfully configured.
root@c2:~#
```

.. code-block:: console

    root@c2:~# su - ubuntu
    ubuntu@c2:~$ lxc launch images:ubuntu/xenial c3
    ubuntu@c2:~$ lxc exec c3 bash


ホストでプロセスを確認。

```console
$ ps auxww | grep 'lxc exec c[1-3]'
101000    3380  0.0  0.0 141844 13336 pts/17   Sl+  23:36   0:00 lxc exec c2 bash
101000    3692  0.0  0.0 207380 12304 pts/1    Sl+  23:37   0:00 lxc exec c3 bash
hnakamur 27103  0.0  0.0 152108 14228 pts/25   Sl+  23:27   0:00 lxc exec c1 bash
```

`apparmor_parser: Unable to replace "ファイル名".  Permission denied; attempted to load a profile while confined?` のエラーが気になりますが、とりあえずネストして非特権コンテナが動いているっぽいです。

