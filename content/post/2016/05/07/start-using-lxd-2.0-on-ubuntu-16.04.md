+++
Categories = []
Description = ""
Tags = ["ubuntu", "lxd"]
date = "2016-05-07T14:12:49+09:00"
title = "Ubuntu 16.04 LTSでLXD 2.0をセットアップして使ってみる"

+++
## 参考記事

公式ドキュメントの[Linux Containers - LXD - はじめに - コマンドライン](https://linuxcontainers.org/ja/lxd/getting-started-cli/)によくまとまっているのですが、より詳細には [The LXD 2.0 Story (Prologue) | Ubuntu Insights](http://insights.ubuntu.com/2016/03/14/the-lxd-2-0-story-prologue/) にリストアップされている記事がわかりやすかったです。

### Ubuntu 16.04 serverでのLXDの初期セットアップ

Ubuntu 16.04 serverならLXDはインストール済みなので、 `apt-get install lxd` と `newgrp lxd` は不要でした。

LXCではコンテナ一覧表示は `lxc-ls`、コンテナ作成は `lxc-create` のように別々のコマンドになっていましたが、 LXDではそれぞれ `lxc list`, `lxc launch` と `lxc` コマンドのサブコマンドになっています。

また `lxd` というプログラムもあります。 `man lxd` と `man lxc` してみると `lxd` はコンテナのハイパーバイザのデーモンで、 `lxc` はコンテナのハイパーバイザのクライアントです。

まずバージョンを確認してみます。

```
$ lxd --version
2.0.0
$ lxc --version
2.0.0
```

ちなみに、 `lxc` のほうは `lxc version` と `version` サブコマンドも用意されていますが、 `lxd version` は `error: Unknown arguments` とエラーになりました。

コンテナ一覧を表示してみます。まだ1つもコンテナを作っていないので一覧は空です。

```
$ lxc list
Generating a client certificate. This may take a minute...
If this is your first time using LXD, you should also run: sudo lxd init

+------+-------+------+------+------+-----------+
| NAME | STATE | IPV4 | IPV6 | TYPE | SNAPSHOTS |
+------+-------+------+------+------+-----------+
```

`lxc list` の出力の1行目にある通り、初回実行時にはクライアント証明書が生成されます。 `~/.config/lxc/client.key` に秘密鍵、 `~/.config/lxc/client.crt` に証明書が作られました。

また、 `lxc list` の出力の2行目に LXDを初めて使うときは `sudo lxd init` を実行するようにも書かれていますので、実行します。

すると、いくつか質問されるので入力していきます。

```
$ sudo lxd init
sudo: unable to resolve host ubuntu-xenial
Name of the storage backend to use (dir or zfs): dir
Would you like LXD to be available over the network (yes/no)? no
Do you want to configure the LXD bridge (yes/no)? yes
Warning: Stopping lxd.service, but it can still be activated by:
  lxd.socket
LXD has been successfully configured.
```

1つ目はストレージバックアップの選択です。選択肢は `dir` か `zfs` ですが、上記では `dir` にしました。

2つ目はLXDをネットワーク越しで利用するかどうかです。上記では `no` にしました。
すると上記の警告にあるとおり `lxd.service` が停止されました。 `sudo systemctl status lxd` で確認すると `Active:` の右が `inactive (dead)` になっていました。

一方で、 `lxd.socket` は稼働しています。 `sudo systemctl status lxd.socket` で確認すると `Active:` の右が `active (running)` になっていました。

`/lib/systemd/system/lxd.socket` を見ると `/var/lib/lxd/unix.socket` というファイル名でUnixドメインソケットが作られていることがわかりました。

3つ目はLXDのブリッジを設定するかどうかです。上記は `yes` にしました。すると CUI でダイアログが次々開いて DHCPで発行するIPv4やIPv6のアドレスの範囲などを聞かれるので、順次入力していきます。ランダムなアドレスの範囲が事前入力されているので、特に変更不要な場合はenterキーを連打していけばOKでした。

再度 `lxc list` を実行してみると、今度はクライアント証明書を生成したとか、 `sudo lxc init` を実行せよとかの文言は表示されなくなりました。

```
$ lxc list
+------+-------+------+------+------+-----------+
| NAME | STATE | IPV4 | IPV6 | TYPE | SNAPSHOTS |
+------+-------+------+------+------+-----------+
```

#### 別パターンの初期化の検証

このパターンではLXDをネットワーク越しに使うかの質問に `yes` と答えました。すると、バインドするアドレスとポートを聞かれます。ポートは `8443` がお勧めと書かれていますが、enterキー空打ちではだめで、ちゃんと値を入力する必要がありました。

```
$ sudo lxd init
sudo: unable to resolve host ubuntu-xenial
Name of the storage backend to use (dir or zfs): dir
Would you like LXD to be available over the network (yes/no)? yes
Address to bind LXD to (not including port): 0.0.0.0
Port to bind LXD to (8443 recommended):
Invalid input, try again.

Port to bind LXD to (8443 recommended): 8443
Trust password for new clients:
Again:
Do you want to configure the LXD bridge (yes/no)? no
LXD has been successfully configured.
```

この設定の後に `sudo systemctl status lxd` を実行すると `Active:` の右は `active (running)` になっていました。

また、上記ではLXDブリッジを設定するかの質問に `no` と答えてみました。この場合は CUIのダイアログは開かれず、すぐに `LXD has been successfully configured.` が表示されて完了しました。

`ip a` で確認すると、この場合も `lxdbr0` というネットワークインターフェース自体は作成されていました。ただし、IPアドレスは設定されていない状態です。

```
$ ip a
...(略)...
4: lxdbr0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000
    link/ether 0a:b4:d4:fa:b3:71 brd ff:ff:ff:ff:ff:ff
    inet6 fe80::8b4:d4ff:fefa:b371/64 scope link
       valid_lft forever preferred_lft forever
    inet6 fe80::1/64 scope link
       valid_lft forever preferred_lft forever
```

ただ、その後 `lxc launch` でコンテナを起動した後再度確認すると `lxdbr0` の左の番号が `4:` から `5:` に変わっていて、IPv4アドレスも設定されていました。また `lxc.service` も起動していました。

`sudo ss -antp` で確認したところ、LXDをネットワーク越しに使う設定を `yes` にしたときは `lxd` のプロセスが指定したポート（上記の例では8443番ポート）をLISTENしていますが、 `no` にしたときはLISTENしていませんでした。

### リモートとローカルのイメージ一覧表示

`lxc image` サブコマンドでイメージを取り扱います。 `lxc image -h` と入力すると使用方法が表示されます。

`lxc image list` の説明の部分を以下に引用します。 `LANG` 環境変数が `ja_JP.UTF8` ならヘルプメッセージは日本語で表示されます。

```
lxc image list [remote:] [filter]
    LXD のイメージストア内のイメージを一覧表示します。プロパティでフィルタ
    を行う場合は、フィルタは <key>=<value> の形になります。フィルタはイメー
    ジハッシュの一部やイメージエイリアス名の一部も指定できます。
```

英語のヘルプメッセージを見たい場合は `LANG=C` をつけて `LANG=C lxc image` のように実行すればOKです。 `lxc image list` の英語ヘルプメッセージを以下に引用します。

```
lxc image list [remote:] [filter]
    List images in the LXD image store. Filters may be of the
    <key>=<value> form for property based filtering, or part of the image
    hash or part of the image alias name.
```

リモートのイメージ一覧は `lxc image list images:` で表示できます。最後の `:` はリモートの指定か区別するために必要です。

ローカルのイメージ一覧は `lxc image list` で表示できます。1つもコンテナを作っていない時は空になります。

`[remote:]` の部分に指定可能なリモートの一覧は `lxc remote list` で確認できます。

```
$ lxc remote list
+-----------------+------------------------------------------+---------------+--------+--------+
|      NAME       |                   URL                    |   PROTOCOL    | PUBLIC | STATIC |
+-----------------+------------------------------------------+---------------+--------+--------+
| images          | https://images.linuxcontainers.org       | lxd           | YES    | NO     |
+-----------------+------------------------------------------+---------------+--------+--------+
| local (default) | unix://                                  | lxd           | NO     | YES    |
+-----------------+------------------------------------------+---------------+--------+--------+
| ubuntu          | https://cloud-images.ubuntu.com/releases | simplestreams | YES    | YES    |
+-----------------+------------------------------------------+---------------+--------+--------+
| ubuntu-daily    | https://cloud-images.ubuntu.com/daily    | simplestreams | YES    | YES    |
+-----------------+------------------------------------------+---------------+--------+--------+
```

フィルタを指定してリモートのcentosのイメージ一覧を表示すると以下の3つがヒットしました。

```
$ lxc image list images: centos
+-------------------------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
|          ALIAS          | FINGERPRINT  | PUBLIC |            DESCRIPTION            |  ARCH  |  SIZE   |         UPLOAD DATE         |
+-------------------------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
| centos/6/amd64 (1 more) | 81c42e7d8c4e | yes    | Centos 6 (amd64) (20160507_02:16) | x86_64 | 52.23MB | May 7, 2016 at 3:15am (UTC) |
+-------------------------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
| centos/6/i386 (1 more)  | 74c61c775024 | yes    | Centos 6 (i386) (20160507_02:16)  | i686   | 52.16MB | May 7, 2016 at 3:16am (UTC) |
+-------------------------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
| centos/7/amd64 (1 more) | 9c8a52ca68e4 | yes    | Centos 7 (amd64) (20160507_02:16) | x86_64 | 62.93MB | May 7, 2016 at 3:16am (UTC) |
+-------------------------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
```

### CentOS 7のコンテナを起動してみる

起動に使用するのは `lxc launch` サブコマンドです。 `lxc launch -h` でヘルプが見られます。

ここでは `images` のリモートの `centos/7/amd64` のエイリアスのイメージを起動して `cent01` というコンテナ名を付けてみます。どれぐらい時間がかかるか計測するため `time` コマンドを付けて実行してみました。

```
$ time lxc launch images:centos/7/amd64 cent01
Creating cent01
Retrieving image: 100%
Starting cent01

real    0m58.036s
user    0m0.056s
sys     0m0.036s
```

`Retrieving image: 100%` と表示されているように初回はイメージのダウンロードを行うので少し時間がかかります。私の環境では1分弱でした。

起動直後に `lxc list` を実行すると、 IPv6アドレスは付与されていますが、 IPv4アドレスはまだ空です。

```
$ lxc list
+--------+---------+------+-----------------------------------------------+------------+-----------+
|  NAME  |  STATE  | IPV4 |                     IPV6                      |    TYPE    | SNAPSHOTS |
+--------+---------+------+-----------------------------------------------+------------+-----------+
| cent01 | RUNNING |      | fd36:b946:6537:931e:216:3eff:fec9:2e18 (eth0) | PERSISTENT | 0         |
+--------+---------+------+-----------------------------------------------+------------+-----------+
```

数秒立ってから再度実行するとIPv4アドレスが付与されていました。

```
$ lxc list
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
|  NAME  |  STATE  |         IPV4         |                     IPV6                      |    TYPE    | SNAPSHOTS |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
| cent01 | RUNNING | 10.64.177.167 (eth0) | fd36:b946:6537:931e:216:3eff:fec9:2e18 (eth0) | PERSISTENT | 0         |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
```

この時点でローカルのイメージ一覧を表示してみると、CentOS 7のイメージが追加されていました。

```
$ lxc image list
+-------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
| ALIAS | FINGERPRINT  | PUBLIC |            DESCRIPTION            |  ARCH  |  SIZE   |         UPLOAD DATE         |
+-------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
|       | 9c8a52ca68e4 | no     | Centos 7 (amd64) (20160507_02:16) | x86_64 | 62.93MB | May 7, 2016 at 7:13am (UTC) |
+-------+--------------+--------+-----------------------------------+--------+---------+-----------------------------+
```

同じイメージで2つめのコンテナを起動してみると今度はローカルのイメージを使うので起動時間は短くてすみました。私の環境では約10秒でした。

```
$ time lxc launch images:centos/7/amd64 cent02
Creating cent02
Starting cent02

real    0m10.189s
user    0m0.044s
sys     0m0.008s
```

起動直後にコンテナ一覧を確認すると、今起動した `cent02` コンテナのIPv4アドレスはやはり空です。

```
$ lxc list
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
|  NAME  |  STATE  |         IPV4         |                     IPV6                      |    TYPE    | SNAPSHOTS |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
| cent01 | RUNNING | 10.64.177.167 (eth0) | fd36:b946:6537:931e:216:3eff:fec9:2e18 (eth0) | PERSISTENT | 0         |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
| cent02 | RUNNING |                      | fd36:b946:6537:931e:216:3eff:fe18:680a (eth0) | PERSISTENT | 0         |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
```

数秒立ってから再度確認すると `centos02` コンテナにもIPv4アドレスが付与されていました。

```
$ lxc list
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
|  NAME  |  STATE  |         IPV4         |                     IPV6                      |    TYPE    | SNAPSHOTS |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
| cent01 | RUNNING | 10.64.177.167 (eth0) | fd36:b946:6537:931e:216:3eff:fec9:2e18 (eth0) | PERSISTENT | 0         |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
| cent02 | RUNNING | 10.64.177.34 (eth0)  | fd36:b946:6537:931e:216:3eff:fe18:680a (eth0) | PERSISTENT | 0         |
+--------+---------+----------------------+-----------------------------------------------+------------+-----------+
```

### コンテナ内でコマンドを実行する

例えば `cent01` コンテナで `bash` を起動するには `lxc exec cent01 bash` と実行します。するとコンテナ内で root ユーザになってプロンプトが表示されるので、好きなコマンドを入力して実行します。

```
$ lxc exec cent01 bash
[root@cent01 ~]# ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN qlen 1
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
37: eth0@if38: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP qlen 1000
    link/ether 00:16:3e:5f:01:7e brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 10.155.92.101/24 brd 10.155.92.255 scope global dynamic eth0
       valid_lft 2508sec preferred_lft 2508sec
    inet6 fe80::216:3eff:fe5f:17e/64 scope link
       valid_lft forever preferred_lft forever
[root@cent01 ~]# ping -c 3 cent02
PING cent02.lxd (10.64.177.34) 56(84) bytes of data.
64 bytes from cent02.lxd (10.64.177.34): icmp_seq=1 ttl=64 time=0.034 ms
64 bytes from cent02.lxd (10.64.177.34): icmp_seq=2 ttl=64 time=0.068 ms
64 bytes from cent02.lxd (10.64.177.34): icmp_seq=3 ttl=64 time=0.081 ms

--- cent02.lxd ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 1998ms
rtt min/avg/max/mdev = 0.034/0.061/0.081/0.019 ms
[root@cent01 ~]# exit
exit
```

上記の `ping` の例でも分かる通り、コンテナ内から別のコンテナの名前を指定して通信可能です。 `ping` の出力を見ると `.lxd` というトップレベルドメインがつけられていて、 `ping -c 3 cent02.lxd` でも大丈夫でした。この `.lxd` という値は `/etc/default/lxd-bridge` の `LXD_DOMAIN="lxd"` という設定で指定されています。

Control-Dを押すか、`exit` に続いてenterキーで `bash` から抜けます。

単一のコマンドを実行したい場合は `bash` の代わりにコマンドを書きます。

```
$ lxc exec cent01 ls /
bin  boot  dev  etc  home  lib  lib64  media  mnt  opt  proc  root  run  sbin  selinux  srv  sys  tmp  usr  var
```

コマンドにオプションを指定するとエラーになりますが、コマンドの前に `--` を入れれば大丈夫です。

```
$ lxc exec cent01 ls -a /
error: flag provided but not defined: -a
$ lxc exec cent01 -- ls -a /
.  ..  .autorelabel  bin  boot  dev  etc  home  lib  lib64  media  mnt  opt  proc  root  run  sbin  selinux  srv  sys  tmp  usr  var
```


## ホストOSを再起動するとコンテナは自動起動されます

LXCではホストOS起動時にコンテナを自動起動するには設定ファイルの編集が必要でしたが、LXDは特に設定は不要でした。　
ホストOSを再起動して `lxc list` を実行してみると上記で作成した2つのコンテナのSTATEがRUNNINGになっていました。

## コンテナの停止と削除

停止は `lxc stop コンテナ名` 、削除は `lxc delete コンテナ名` で出来ます。が、 CentOS 7 のコンテナを停止するには以下の事前準備が必要でした。

### CentOS 7 のコンテナを停止可能にするための設定

`cent01` のところは実際のコンテナ名に置き換えて、各コンテナで実行が必要です。

```
lxc exec cent01 -- sh -c 'ln -s /usr/lib/systemd/system/halt.target /etc/systemd/system/sigpwr.target && systemctl daemon-reload'
```

この回避方法は [\[lxc-users\] lxc-stop doesn't stop centos, waits for the timeout](https://lists.linuxcontainers.org/pipermail/lxc-users/2014-February/006304.html) で紹介されていました。

[\[lxc-users\] lxc stop does not stop a CentOS 7 container](https://lists.linuxcontainers.org/pipermail/lxc-users/2016-May/011602.html) で `images:` で公開しているイメージにこの修正を取り込めないか問い合わせ中です。

## コンテナやイメージのファイルの在り処

コンテナのファイルは `/var/lib/lxd/containers/` にありました。操作しているユーザのuidとgidは1000なのですが、コンテナのディレクトリは100000と異なっていました。どこかでマッピングを持っているのだと思いますが、未調査です。

```
$ sudo ls -l /var/lib/lxd/containers/
合計 24
drwxr-xr-x+ 4 100000 100000  4096  5月  6 18:56 cent01
drwxr-xr-x+ 4 100000 100000  4096  5月  7 03:18 cent02
-rw-r--r--  1 root   root   10756  5月  7 19:47 lxc-monitord.log
drwxr-xr-x+ 4 100000 100000  4096  5月  3 20:46 my-ubuntu
$ sudo ls -l /var/lib/lxd/containers/cent01
合計 12
-rw-r--r--  1 root   root    628  1月  1  1970 metadata.yaml
dr-xr-xr-x 18 100000 100000 4096  5月  6 18:56 rootfs
drwxr-xr-x  2 root   root   4096  5月  6 18:56 templates
1$ sudo ls -l /var/lib/lxd/containers/cent01/rootfs/
合計 64
lrwxrwxrwx  1 100000 100000    7  5月  6 11:25 bin -> usr/bin
dr-xr-xr-x  2 100000 100000 4096  8月 12  2015 boot
drwxr-xr-x  4 100000 100000 4096  5月  6 11:25 dev
drwxr-xr-x 55 100000 100000 4096  5月  7 12:13 etc
drwxr-xr-x  2 100000 100000 4096  8月 12  2015 home
lrwxrwxrwx  1 100000 100000    7  5月  6 11:25 lib -> usr/lib
lrwxrwxrwx  1 100000 100000    9  5月  6 11:25 lib64 -> usr/lib64
drwxr-xr-x  2 100000 100000 4096  8月 12  2015 media
drwxr-xr-x  2 100000 100000 4096  8月 12  2015 mnt
drwxr-xr-x  2 100000 100000 4096  8月 12  2015 opt
dr-xr-xr-x  2 100000 100000 4096  8月 12  2015 proc
dr-xr-x---  3 100000 100000 4096  5月  7 03:42 root
drwxr-xr-x  7 100000 100000 4096  5月  6 11:25 run
lrwxrwxrwx  1 100000 100000    8  5月  6 11:25 sbin -> usr/sbin
drwxr-xr-x  2 100000 100000 4096  5月  6 11:25 selinux
drwxr-xr-x  2 100000 100000 4096  8月 12  2015 srv
dr-xr-xr-x  2 100000 100000 4096  8月 12  2015 sys
drwxrwxrwt  7 100000 100000 4096  5月  7 12:54 tmp
drwxr-xr-x 13 100000 100000 4096  5月  6 11:25 usr
drwxr-xr-x 19 100000 100000 4096  5月  6 18:56 var
```

イメージのファイルは `/var/lib/lxd/images/` にありました。 `lxc image list` で表示されるフィンガープリント名のファイルとフィンガープリントに `.rootfs` を追加した名前のファイルがあります。調べてみるとtar.xz形式のファイルになっていました。

```
$ sudo ls -l /var/lib/lxd/images/
合計 205244
-rw-r--r-- 1 root root       588  5月  6 18:54 a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2
-rw-r--r-- 1 root root  65931516  5月  6 18:55 a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2.rootfs
-rw-r--r-- 1 root root       792  5月  3 20:32 f4c4c60a6b752a381288ae72a1689a9da00f8e03b732c8d1b8a8fcd1a8890800
-rw-r--r-- 1 root root 144223868  5月  3 20:46 f4c4c60a6b752a381288ae72a1689a9da00f8e03b732c8d1b8a8fcd1a8890800.rootfs
$ sudo file /var/lib/lxd/images/a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2
/var/lib/lxd/images/a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2: XZ compressed data
$ sudo file /var/lib/lxd/images/a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2.rootfs
/var/lib/lxd/images/a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2.rootfs: XZ compressed data
$ sudo tar tvf /var/lib/lxd/images/a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2
-rw-r--r-- 0/0             239 1970-01-01 09:00 templates/hosts.tpl
-rw-r--r-- 0/0             628 1970-01-01 09:00 metadata.yaml
-rw-r--r-- 0/0              21 1970-01-01 09:00 templates/hostname.tpl
$ sudo tar tvf /var/lib/lxd/images/a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2.rootfs | head
dr-xr-xr-x 0/0               0 2016-05-06 11:25 ./
drwxr-xr-x 0/0               0 2016-05-06 11:25 ./dev/
crw-rw-rw- 0/0             5,2 2016-05-06 11:25 ./dev/ptmx
prw------- 0/0               0 2016-05-06 11:25 ./dev/initctl
crw-rw-rw- 0/0             1,7 2016-05-06 11:25 ./dev/full
crw------- 0/0             5,1 2016-05-06 11:25 ./dev/console
crw-rw-rw- 0/0             4,4 2016-05-06 11:25 ./dev/tty4
crw-rw-rw- 0/0             4,3 2016-05-06 11:25 ./dev/tty3
crw-rw-rw- 0/0             4,2 2016-05-06 11:25 ./dev/tty2
crw-rw-rw- 0/0             4,1 2016-05-06 11:25 ./dev/tty1
```

`/var/lib/lxd/` には他にもディレクトリやファイルが存在しています。

```
$ ls -l /var/lib/lxd
合計 84
drwx--x--x 5 root root  4096  5月  7 12:54 containers
drwx--x--x 5 root root  4096  5月  7 12:54 devices
drwxr-xr-x 2 root root  4096  5月  7 19:41 devlxd
drwx------ 2 root root  4096  5月  7 06:13 images
-rw-r--r-- 1 root root 43008  5月  7 19:46 lxd.db
drwx------ 4 root root  4096  5月  3 20:46 security
-rw-r--r-- 1 root root  2004  5月  3 20:26 server.crt
-rw------- 1 root root  3247  5月  3 20:26 server.key
drwx--x--x 5 root root  4096  5月  7 12:54 shmounts
drwx------ 2 root root  4096  5月  3 20:26 snapshots
srw-rw---- 1 root lxd      0  5月  7 12:51 unix.socket
```
