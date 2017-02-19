Title: LXD 0.7ではlxc execでシェルの対話操作もできるようになっていました
Date: 2015-04-23 00:08
Category: blog
Tags: lxd
Slug: 2015/04/23/try-lxd-0.7-with-vagrant

## はじめに

[LXDを試してみた · hnakamur's blog at github](/blog/2014/12/01/lxd-the-linux-container-daemon/)の記事を書いて以来、LXD触る時間を作れてなかったのですが、久々に試してみました。

今では[lxc/lxd](https://github.com/lxc/lxd)にVagrantfileが同梱されているので、それを使うだけで簡単に試せます。

VirtualBox 4.3.26, Vagrant 1.7.2, OS X Yosemiteという環境で試しました。

## 操作手順

### VagrantでVMを起動

まずOS X上で以下のコマンドを実行します。

```
git clone https://github.com/lxc/lxd
cd lxd
vagrant up
```

[Vagrantfile](https://github.com/lxc/lxd/blob/lxd-0.7/Vagrantfile)を見てみると、Vagrantのシェルプロビジョナでgoとlxdをインストールするようになっています。

[lxd/install-lxd.sh at lxd-0.7 · lxc/lxd](https://github.com/lxc/lxd/blob/lxd-0.7/scripts/vagrant/install-lxd.sh)を見てみると、[lxdのREADME](https://github.com/lxc/lxd)と同様のセットアップ手順に加えてlxdをサービスとして登録して起動する処理まで含まれています。

### VMにログインしてlxcコマンドを試してみる

以下のコマンドを実行してVMにログインします。

```
vagrant ssh
```

以降のコマンドはVM上で実行します。

`lxc` と `lxd` にはPATHが通った状態になっていることを確認しました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ which lxc
/home/vagrant/go/bin/lxc
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ which lxd
/home/vagrant/go/bin/lxd
```

バージョンを確認してみると、 `lxc`, `lxd` ともに0.7でした。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxd --version
0.7
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc --version
0.7
```

[lxdのREADMEのFirst steps](https://github.com/lxc/lxd#first-steps)に添って、ubuntuとdebianのイメージを取得します。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ ./scripts/lxd-images import lxc ubuntu trusty amd64 --alias ubuntu --alias ubuntu/trusty
Downloading the GPG key for https://images.linuxcontainers.org
Downloading the image list for https://images.linuxcontainers.org
Validating the GPG signature of /tmp/tmpsccxc1fa/index.json.asc
Downloading the image: https://images.linuxcontainers.org/images/ubuntu/trusty/amd64/default/20150420_03:49/lxd.tar.xz
Validating the GPG signature of /tmp/tmpsccxc1fa/ubuntu-trusty-amd64-default-20150420_03:49.tar.xz.asc
Image imported as: c9176e837c0012d6d0eed221312ee9fc761765319701f57e65e63542ad9beade
Setup alias: ubuntu
Setup alias: ubuntu/trusty
```

debianのほうは最初コピペミスでaliasに2回同じ値を指定してしまってエラーになりましたが、再度実行すると成功しました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ scripts/lxd-images import lxc debian wheezy amd64 --alias debian --alias debian/wheezy --alias debian/wheezy
Downloading the GPG key for https://images.linuxcontainers.org
Downloading the image list for https://images.linuxcontainers.org
Validating the GPG signature of /tmp/tmp_d1gz0q6/index.json.asc
Downloading the image: https://images.linuxcontainers.org/images/debian/wheezy/amd64/default/20150419_22:42/lxd.tar.xz
Validating the GPG signature of /tmp/tmp_d1gz0q6/debian-wheezy-amd64-default-20150419_22:42.tar.xz.asc
Image imported as: cd398814f6e4e1e50799ba8249b80aa3558e5b05edf71a996a174def87569ae5
Setup alias: debian
Setup alias: debian/wheezy
Traceback (most recent call last):
  File "scripts/lxd-images", line 410, in <module>
    args.func(parser, args)
  File "scripts/lxd-images", line 367, in import_lxc
    setup_alias(parser, args, fingerprint)
  File "scripts/lxd-images", line 330, in setup_alias
    lxd.aliases_create(alias, fingerprint)
  File "scripts/lxd-images", line 83, in aliases_create
    raise Exception("Failed to create alias: %s" % name)
Exception: Failed to create alias: debian/wheezy
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ scripts/lxd-images import lxc debian wheezy amd64 --alias debian --alias debian/wheezy --alias debian/wheezy/amd64
Downloading the GPG key for https://images.linuxcontainers.org
Downloading the image list for https://images.linuxcontainers.org
Validating the GPG signature of /tmp/tmpeqkwuvfw/index.json.asc
Downloading the image: https://images.linuxcontainers.org/images/debian/wheezy/amd64/default/20150419_22:42/lxd.tar.xz
Validating the GPG signature of /tmp/tmpeqkwuvfw/debian-wheezy-amd64-default-20150419_22:42.tar.xz.asc
This image is already in the store.
```

コンテナを起動します。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc launch ubuntuCreating container...done
Starting container...done
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc launch debian debian01
Creating container...done
Starting container...done
```

コンテナの一覧を表示してみます。ubuntuのほうはコンテナ名を指定しなかったので、自動で付けられています。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc list
+---------------------+---------+------------+------+-----------+
|        NAME         |  STATE  |    IPV4    | IPV6 | EPHEMERAL |
+---------------------+---------+------------+------+-----------+
| preterhuman-araceli | RUNNING | 10.0.3.188 |      | NO        |
| debian01            | RUNNING |            |      | NO        |
+---------------------+---------+------------+------+-----------+
```

debianのほうはIPアドレスが空になっていて、あれ？と思ったのですが、実行するタイミングが早すぎたようで、数秒立ってから再度実行するとアドレスが表示されました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc list
+---------------------+---------+------------+------+-----------+
|        NAME         |  STATE  |    IPV4    | IPV6 | EPHEMERAL |
+---------------------+---------+------------+------+-----------+
| preterhuman-araceli | RUNNING | 10.0.3.188 |      | NO        |
| debian01            | RUNNING | 10.0.3.42  |      | NO        |
+---------------------+---------+------------+------+-----------+
```

以前未実装だった `lxc shell` の代わりに `lxc exec` でコマンド実行やシェルでの対話操作ができるようになっていました。

`lxc exec コンテナ名 コマンド 引数` のように指定すると、コンテナ内でコマンドを実行できます。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
6: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether 00:16:3e:01:bd:a1 brd ff:ff:ff:ff:ff:ff
    inet 10.0.3.42/24 brd 10.0.3.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::216:3eff:fe01:bda1/64 scope link
       valid_lft forever preferred_lft forever
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec preterhuman-araceli ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
4: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 00:16:3e:5e:6c:79 brd ff:ff:ff:ff:ff:ff
    inet 10.0.3.188/24 brd 10.0.3.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::216:3eff:fe5e:6c79/64 scope link
       valid_lft forever preferred_lft forever
```

`uname -a` のようなコマンドを `lxc exec コンテナ名 コマンド 引数` のように指定するとlxcのオプションと解釈するようで、以下のエラーになりました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec preterhuman-araceli uname -a
error: flag provided but not defined: -a
```

コンテナ名のあとに `--` を入れれば回避出来ました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec preterhuman-araceli -- uname -a
Linux preterhuman-araceli 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux
```

ただ、原因は不明なのですが、何回か実行してみると、時々何も出力されないことがありました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec debian01 -- uname -a
Linux debian01 3.13.0-48-generic #80-Ubuntu SMP Thu Mar 12 11:16:15 UTC 2015 x86_64 GNU/Linux
```

`lxc exec コンテナ名 /bin/bash` のようにコマンドにシェルを指定すると、コンテナ内でシェルが起動され対話操作が出来ました。ubuntuコンテナの実際の画面では `ls` の結果もカラー表示されていました。

```
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$ lxc exec preterhuman-araceli /bin/bash
root@preterhuman-araceli:~# ls
root@preterhuman-araceli:~# pwd
/root
root@preterhuman-araceli:~# cd /
root@preterhuman-araceli:/# ls -l
total 60
drwxr-xr-x   2 root   root    4096 Apr 20 03:55 bin
drwxr-xr-x   2 root   root    4096 Apr 10  2014 boot
drwxr-xr-x   5 root   root     420 Apr 22 13:51 dev
drwxr-xr-x  63 root   root    4096 Apr 22 13:51 etc
drwxr-xr-x   3 root   root    4096 Apr 20 03:55 home
drwxr-xr-x  12 root   root    4096 Apr 20 03:54 lib
drwxr-xr-x   2 root   root    4096 Apr 20 03:54 lib64
drwxr-xr-x   2 root   root    4096 Apr 20 03:53 media
drwxr-xr-x   2 root   root    4096 Apr 10  2014 mnt
drwxr-xr-x   2 root   root    4096 Apr 20 03:53 opt
dr-xr-xr-x 109 nobody nogroup    0 Apr 22 13:51 proc
drwx------   2 root   root    4096 Apr 20 03:53 root
drwxr-xr-x   9 root   root     380 Apr 22 13:51 run
drwxr-xr-x   2 root   root    4096 Apr 20 03:55 sbin
drwxr-xr-x   2 root   root    4096 Apr 20 03:53 srv
dr-xr-xr-x  13 nobody nogroup    0 Apr 22 13:51 sys
drwxrwxrwt   2 root   root    4096 Apr 20 03:55 tmp
drwxr-xr-x  10 root   root    4096 Apr 20 03:53 usr
drwxr-xr-x  11 root   root    4096 Apr 20 03:53 var
root@preterhuman-araceli:/# ls
bin   dev  home  lib64  mnt  proc  run   srv  tmp  var
boot  etc  lib   media  opt  root  sbin  sys  usr
root@preterhuman-araceli:/# pwd
/
root@preterhuman-araceli:/# exit
vagrant@vagrant-ubuntu-trusty-64:~/go/src/github.com/lxc/lxd$
```

## おわりに

以前試した時に比べて、かなり進歩してますね。

ten_forwardさんのライブマイグレーションの記事とかも、今後試してみようと思います。

* [lxd を使ったライブマイグレーション (1) - TenForwardの日記](http://d.hatena.ne.jp/defiant/20150415/1429089615)
* [lxd を使ったライブマイグレーション (2) - TenForwardの日記](http://d.hatena.ne.jp/defiant/20150415/1429090896)
