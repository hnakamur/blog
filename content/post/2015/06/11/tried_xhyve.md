Title: xhyveを試してみました
Date: 2015-06-11 00:45
Category: blog
Tags: xhyve, virtualization
Slug: 2015/06/11/tried_xhyve

[xhyve – Lightweight Virtualization on OS X Based on bhyve | pagetable.com](http://www.pagetable.com/?p=831)に沿って試してみました。


## 確認した環境

* MacBook Pro (Retina, Mid 2012)
* OS X Yosemite 10.10.3

## ソースからビルド

```
cd お好みの作業ディレクトリ
git clone https://github.com/mist64/xhyve
cd xhyve
make
```

## Tiny Core Linuxを起動

```
./xhyverun.sh
```

起動メッセージが流れた後、画面がクリアされて以下のように表示されたら起動完了です。ここまで3〜4秒です。速い！

```
(�-
 //\   Core is distributed with ABSOLUTELY NO WARRANTY.
 v_/_           www.tinycorelinux.com

tc@box:~$ Switched to clocksource tsc
```

プロンプトにかぶってメッセージが出ていますが、enterを押せばプロンプトが出ます。

```
tc@box:~$
```

シャットダウンするには以下のコマンドを実行します。

```
sudo halt
```

## Ubuntu Server 14.04.2のディスクイメージ作成

Ubuntu ServerのISOイメージをダウンロードして、ディスクイメージを作成するための準備を行います。元記事によると、OS Xがハイブリッドファイルシステムを認識しないので、Linux kernelとinitrdを取り出しているそうです。

```
mkdir ubuntu
cd ubuntu
curl -O ftp://ftp.kddilabs.jp/Linux/packages/ubuntu/releases-cd/14.04.2/ubuntu-14.04.2-server-amd64.iso
dd if=/dev/zero bs=2k count=1 of=/tmp/tmp.iso
dd if=ubuntu-14.04.2-server-amd64.iso bs=2k skip=1 >> /tmp/tmp.iso
hdiutil attach /tmp/tmp.iso
cp /Volumes/Ubuntu-Server\ 14/install/vmlinuz .
cp /Volumes/Ubuntu-Server\ 14/install/initrd.gz .
```

以下のコマンドでディスクイメージを作成します。ここでは `bs=1g count=8` でディスクサイズを8GBとしていますが、お好みで調整してください。

```
dd if=/dev/zero of=hdd.img bs=1g count=8
```

xhyve/ubuntuディレクトリではなくxhyveディレクトリにディスクイメージ作成用のスクリプトを作ります。

```
cd ..
cat <<'EOF' > xhyverun_ubuntu_install.sh
#!/bin/sh

KERNEL="ubuntu/vmlinuz"
INITRD="ubuntu/initrd.gz"
CMDLINE="earlyprintk=serial console=ttyS0 acpi=off"

MEM="-m 1G"
#SMP="-c 2"
NET="-s 2:0,virtio-net"
IMG_CD="-s 3,ahci-cd,ubuntu/ubuntu-14.04.2-server-amd64.iso"
IMG_HDD="-s 4,virtio-blk,ubuntu/hdd.img"
PCI_DEV="-s 0:0,hostbridge -s 31,lpc"
LPC_DEV="-l com1,stdio"

build/xhyve $MEM $SMP $PCI_DEV $LPC_DEV $NET $IMG_CD $IMG_HDD -f kexec,$KERNEL,$INITRD,"$CMDLINE"
EOF
```

スクリプトに実行パーミションをつけてsudo付きで実行します。

```
chmod +x xhyverun_ubuntu_install.sh
sudo ./xhyverun_ubuntu_install.sh
```

テキストインストーラが起動しますので、以下のように選択してインストールしました。

* Select a language: English
* Select your location: other -> Asia -> Japan
* Configure locales: United Status - en_US.UTF-8
* Hostname: お好みの名前
* Set up users and passwords: お好みのIDとパスワードで作成
* time zone: Asia/Tokyo
* Partition disks: Guided - use entire disk
* HTTP proxy: 無し
* manage upgrades: No automatic updates
* Software selection:
    * Basic Ubuntu Server
    * OpenSSH server
* Install GRUB to the master boot record: Yes
* Is the system clock set to UTC: No
* Installation complete: Go Back -> Execute a shell

Installation completeのところでContinueではなくGo Backでメニューに戻りExecute a shellを選んで進み、シェルが起動したら以下のコマンドを実行します。

```
cd /target
sbin/ifconfig
tar c boot | nc -l -p 1234
```

上記のコマンド実行のうちsbin/ifconfigで表示されたIPアドレスをメモしておきます。

```
/target # sbin/ifconfig
eth0      Link encap:Ethernet  HWaddr e6:0d:f2:6b:cf:32
          inet addr:192.168.64.3  Bcast:192.168.64.255  Mask:255.255.255.0
          inet6 addr: fe80::e40d:f2ff:fe6b:cf32/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:25405 errors:0 dropped:0 overruns:0 frame:85
          TX packets:13601 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:38179647 (38.1 MB)  TX bytes:931189 (931.1 KB)

lo        Link encap:Local Loopback
          inet addr:127.0.0.1  Mask:255.0.0.0
          inet6 addr: ::1/128 Scope:Host
          UP LOOPBACK RUNNING  MTU:65536  Metric:1
          RX packets:0 errors:0 dropped:0 overruns:0 frame:0
          TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:0
          RX bytes:0 (0.0 B)  TX bytes:0 (0.0 B)
```

Mac側では以下のコマンドを実行します。IPアドレスはifconfigで表示されたものに置き換えて実行してください。

```
cd ubuntu
nc 192.168.64.3 1234 | tar x
```

VMのシェルのプロンプトで以下のように入力してシェルを終了します。

```
exit
```

メニューに戻ったら `Finish the installation` を選びます。

* Is the system clock set to UTC?: No
* Installation complete: Continue


## Ubuntu Server 14.04.2の起動

Macでxhyve/ubuntuではなくxhyveのディレクトリで起動用のスクリプトを作成します。

```
cat <<'EOF' > ./xhyverun_ubuntu.sh
#!/bin/sh

KERNEL="ubuntu/boot/vmlinuz-3.16.0-30-generic"
INITRD="ubuntu/boot/initrd.img-3.16.0-30-generic"
CMDLINE="earlyprintk=serial console=ttyS0 acpi=off root=/dev/vda1 ro"

MEM="-m 1G"
#SMP="-c 2"
NET="-s 2:0,virtio-net"
IMG_HDD="-s 4,virtio-blk,ubuntu/hdd.img"
PCI_DEV="-s 0:0,hostbridge -s 31,lpc"
LPC_DEV="-l com1,stdio"

build/xhyve $MEM $SMP $PCI_DEV $LPC_DEV $NET $IMG_CD $IMG_HDD -f kexec,$KERNEL,$INITRD,"$CMDLINE"
EOF
```

スクリプトに実行パーミションをつけてsudo付きで実行してUbuntuを起動します。

```
chmod +x ./xhyverun_ubuntu.sh
sudo ./xhyverun_ubuntu.sh
```

起動してログインプロンプトが出たらインストール時に作成したユーザでログインします。IPアドレスはDHCPで取得する設定にしたのですが、確認してみると、ディスクイメージ作成時とは違う値になっていました。

```
$ ip a s eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 62:ca:c1:25:cf:32 brd ff:ff:ff:ff:ff:ff
    inet 192.168.64.4/24 brd 192.168.64.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::60ca:c1ff:fe25:cf32/64 scope link
       valid_lft forever preferred_lft forever
```

Macからsshでログインも出来ました。

```
ssh ubuntu@192.168.64.4
```

sshでログインすると初回だけ表示が24行に限定され、リターンを押しても24行の範囲でスクロールされるようになってしまいました。Mac側ではiTermで65行にしていました。と、この説明を書くためにiTermのウィンドウで高さを変えて行数を変えて戻してとやっていたら、次のsshログインからはiTermの行数で表示されるようになりました。

Ubuntuを停止するにはVM内で以下のコマンドを実行します。

```
sudo shutdown -h now
```

## Ubuntuの起動に必要なファイル

ubuntuフォルダにはビルドに使用したファイルも含まれていますが、起動スクリプトで参照されているファイル以外のファイルを別ディレクトリに移動して起動してみたら起動出来ました。ということで、起動には以下の4つのファイルだけあればOKです。

```
./xhyverun_ubuntu.sh
ubuntu/boot/initrd.img-3.16.0-30-generic
ubuntu/boot/vmlinuz-3.16.0-30-generic
ubuntu/hdd.img
```

# まとめ

xhyveをソースからビルドして、Tiny Core LinuxとUbuntu Server 14.04.2を動かしてみました。[TODO](https://github.com/mist64/xhyve#todo)によると、まだいろいろ対応予定の項目があるようです。今後が楽しみです！
