Title: jetpackを試してみた
Date: 2015-04-23 01:27
Category: blog
Tags: jetpack
Slug: 2015/04/23/try-jetpack

## はじめに

[3ofcoins/jetpack](https://github.com/3ofcoins/jetpack#using-jetpack)はFreeBSD, Jail, ZFSを使った[App Container Spec](https://github.com/appc/spec)の実装です。まだプロトタイプレベルとのことです。Go言語で実装されています。

masterの最新を試しました。今後のためにコミットハッシュをメモしておきます。

```
sunshine5:jetpack hnakamur$ g log -1
commit 0792b938c7f9bdd43f9d117bfdec6cd91e223ee5
Author: Maciej Pasternacki <maciej@3ofcoins.net>
Date:   Mon Apr 13 06:26:57 2015

    Make image building work with per-app rootfs
```

## セットアップ

Vagrantfileが用意されているのでそれを使いました。
VirtualBox 4.3.26, Vagrant 1.7.2, OS X Yosemiteという環境で試しました。

VagrantのAnsibleプロビジョナを利用しているので、予めホスト側にAnsibleをセットアップしておいてください。

```
vagrant up
vagrant ssh
```

## Jetpackを使ってみる

[Using Jetpack](https://github.com/3ofcoins/jetpack#using-jetpack)の説明にそって、試してみました。

引数無しで単に `jetpack` と実行すると説明が出ます。

```
$ jetpack
Usage: jetpack [OPTIONS] COMMAND...
Options:
  -config=PATH  Configuration file (/usr/local/etc/jetpack.conf)
  -help, -h     Display this help screen
Commands:
  help                                    Display this help screen
  init                                    Initialize host
  info                                    Show global information
  test                                    Run integration tests
  image list [QUERY]                      List images
  image import ARCHIVE [MANIFEST]         Import image from an archive
  image IMAGE build [OPTIONS] COMMAND...  Build new image from an existing one
                    -dir=.                Location on build directory on host
                    -cp=PATH...           Copy additional files from host
  image IMAGE show                        Display image details
  image IMAGE export [PATH]               Export image to an AMI file
                                          Output to stdout if no PATH given
  image IMAGE destroy                     Destroy image
  pod list                                List pods
  pod create [FLAGS] IMAGE [IMAGE FLAGS] [IMAGE [IMAGE FLAGS] ...]
                                          Create new pod from image
             -help                        Show detailed help
  pod POD show                            Display pod details
  pod POD run                             Run pod's application
  pod POD console [USER]                  Open console inside the pod
  pod POD ps|top|killall [OPTIONS...]
                                          Manage pod's processes
  pod POD kill                Kill running pod
  pod POD destroy             Destroy pod
Needs Explanation:
  ARCHIVE, MANIFEST  May be filesystem paths or URLs.
            cp=PATH  This option can be given multiple times
              QUERY  Is an expression that looks like this:
                      - NAME[,LABEL=VALUE[,LABEL=VALUE[,...]]]
                      - NAME:VERSION (alias for NAME:version=VERSION)
              IMAGE  Can be:
                      - an UUID (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXX),
                      - a checksum (sha512-...), or
                      - a QUERY (which can't be ambiguous).
          POD  Has to be an UUID for now
Helpful Aliases:
  i|img ... -- image ...
  p ... -- pod ...
  image, images -- image list
  pod, pods -- pod list
  image build|show|export|destroy IMAGE ... -- image IMAGE build|show|... ...
```

`jetpack init` でZFSのデータセットとディレクトリ構造を初期化します。が、これはプロビジョニングで実行済みだったようです。

```
$ jetpack init
/vagrant/jetpack/host.go:82: Host already initialized
```

`jetpack info` で状態を確認してみました。

```
$ jetpack info
JetPack 0.0.1 (v0.0.1-81-g0792b93), compiled on 2015-04-22T15:38:43Z
ZFS Dataset zroot/jetpack
  Mountpoint  /var/jetpack
Configuration:
  root.zfs                zroot/jetpack
  root.zfs.mountpoint     /var/jetpack
  images.ami.store        no
  images.ami.compression  xz
  images.zfs.atime        off
  images.zfs.compress     lz4
  jail.interface          lo1
  jail.namePrefix         jetpack/
  debug                   off
```

`jetpack test` でスモークテストを実行してみましたが、一般ユーザでは権限不足でした。

```
$ jetpack test
ERROR: mkdir /var/jetpack/test.881699652: permission denied
run.Command[/usr/local/libexec/jetpack/test.integration dataset=zroot/jetpack]: exit status 2
```

スモークテストという言葉は知らなかったのですが、本格的なテストの前の簡易テストという意味だそうです。

* [ビジネス英語とアメリカ生活 | カリフォルニアの陽射しの中で: IT英語:　ソフトウェアの試験なのにSmoke Testとは、これいかに?](http://nolan00267.blogspot.jp/2013/12/itsmoke-test.html)
* [情報システム用語事典：スモークテスト（すもーくてすと） - ITmedia エンタープライズ](http://www.itmedia.co.jp/im/articles/1111/07/news166.html)


sudoつきで実行すると、さっきよりは進みましたが `resolv.conf` が無いというエラーになってしまいました。

```
$ sudo jetpack test
...(snip)...
Pod dying since 51.336704525s, waiting...
Image 6d058709-d7f9-45c5-a40b-0f9a5c81a90b
  Hash       sha512-3d526a2a0e40605d1d5f50a6596f210ff26d7486867f12f4ffa395c3600028a01473c126c11b1030a4c299c82799b56a3493773d008743ae33f1230dc71384a1
  Origin     b73f4bf5-8988-4e0f-87f4-31723167e2ef
  Timestamp  2015-04-22 16:24:15.597136136 +0000 UTC
  Manifest freebsd-base
    Labels
      version  10.1.9
      os       freebsd
      arch     amd64
    Annotations
      timestamp  2015-04-22T16:24:15.595105431Z
jetpack image freebsd-base build -cp=/usr/local/share/jetpack/jetpack.image.mk  /usr/bin/make .jetpack.build.
open /var/jetpack/test.467360619/pods/4c518b91-afa8-4e28-86ca-4c4d0fedc313/rootfs/0/etc/resolv.conf: no such file or directory
/vagrant/jetpack/pod.go:281:
/vagrant/jetpack/pod.go:500:
/vagrant/jetpack/pod.go:501:
/vagrant/jetpack/image.go:331:
*** Error code 1

Stop.
make: stopped in /usr/local/share/examples/jetpack/example.showenv
ERROR: run.Command[make -C /usr/local/share/examples/jetpack/example.showenv]: exit status 1
run.Command[/usr/local/libexec/jetpack/test.integration dataset=zroot/jetpack]: exit status 2
```

一旦置いておいて、先に進みます。

rootユーザで `/usr/local/share/examples/jetpack` 以下の `freebsd-base.release`, `freebsd-base`, `example.showenv` イメージを順に作成します。

まず `freebsd-base.release` イメージを作ります。

```
$ sudo -i
root@packer-freebsd-10:~ # cd /usr/local/share/examples/jetpack
root@packer-freebsd-10:/usr/local/share/examples/jetpack # cd freebsd-base.release/
root@packer-freebsd-10:/usr/local/share/examples/jetpack/freebsd-base.release # make
sha256 -c 2b028a894d25711ad496762622a52d74b1e32ee04693ad1cf056e3ddcdc23975 base.txz
SHA256 (base.txz) = 2b028a894d25711ad496762622a52d74b1e32ee04693ad1cf056e3ddcdc23975
jetpack image import base.txz manifest.json
-                                             100% of   63 MB 6067 kBps 00m11s
-                                             100% of  184  B  519 kBps 00m00s
Image 445da390-2e49-4b7f-921d-47ce6114cb02
  Hash       sha512-3e5767bda2018294312cce0d0ef2003cf886af246cbbfe5050a266a94bdcfe9df94c9e73ef4452b487cf8bdc8279806e70aef75ea8f644d24223cf227bc75df8
  Origin     base.txz
  Timestamp  2015-04-22 16:33:07.861508005 +0000 UTC
  Manifest freebsd-base/release
    Labels
      version  10.1
      os       freebsd
      arch     amd64
    Annotations
      timestamp  2015-04-22T16:33:18.685140617Z
```

次に `freebsd-base` イメージを作ります。

```
root@packer-freebsd-10:/usr/local/share/examples/jetpack/freebsd-base.release # cd ../freebsd-base
root@packer-freebsd-10:/usr/local/share/examples/jetpack/freebsd-base # make
jetpack image freebsd-base/release build -cp=/usr/local/share/jetpack/jetpack.image.mk  /usr/bin/make .jetpack.build.
sed -i '' 's|^Components.*|Components world/base|' /etc/freebsd-update.conf
install -v -m 0644 rc.conf /etc/rc.conf
install: rc.conf -> /etc/rc.conf
install -v -m 0600 entropy /entropy
install: entropy -> /entropy
patch /usr/sbin/freebsd-update < freebsd-update.patch
Hmm...  Looks like a unified diff to me...
The text leading up to this was:
--------------------------
|--- /usr/sbin/freebsd-update	2015-02-08 22:15:58.178818000 +0100
|+++ freebsd-update	2015-02-09 13:45:42.202917000 +0100
--------------------------
Patching file /usr/sbin/freebsd-update using Plan A...
Hunk #1 succeeded at 610 (offset -8 lines).
done
env PAGER=cat freebsd-update -s update6.freebsd.org fetch install
Looking up update6.freebsd.org mirrors... none found.
Fetching public key from update6.freebsd.org... done.
Fetching metadata signature for 10.1-RELEASE from update6.freebsd.org... done.
Fetching metadata index... done.
Fetching 2 metadata files... done.
Inspecting system... done.
Preparing to download files... done.
Fetching 706 patches.....10....20....30....40....50....60....70....80....90....100....110....120....130....140....150....160....170....180....190....200....210....220....230....240....250....260....270....280....290....300....310....320....330....340....350....360....370....380....390....400....410....420....430....440....450....460....470....480....490....500....510....520....530....540....550....560....570....580....590....600....610....620....630....640....650....660....670....680....690....700... done.
Applying patches... done.
Fetching 1 files... done.

The following files will be updated as part of updating to 10.1-RELEASE-p9:
/bin/freebsd-version
/boot/boot1.efi
/boot/boot1.efifat
...(略)...
/var/db/mergemaster.mtree
Installing updates... done.
rm -rf /var/db/freebsd-update/*
./manifest.json.sh > manifest.json
Pod dying since 64.761583ms, waiting...
...(略)...
Pod dying since 51.461102458s, waiting...
Image 9323ac42-0f39-4f42-90de-ac4de60420dd
  Hash       sha512-3fb309e4d9a998bd910ce07dbfcef447508ea2146fabd88056975abc224d49094b3ff22c61c6c3aae170ee5e69bff72c43fb6e1153ae4f68607246cb50cc4d3d
  Origin     445da390-2e49-4b7f-921d-47ce6114cb02
  Timestamp  2015-04-22 16:38:35.737407036 +0000 UTC
  Manifest freebsd-base
    Labels
      version  10.1.9
      os       freebsd
      arch     amd64
    Annotations
```

次に `freebsd-base` イメージを作ります。

```
root@packer-freebsd-10:/usr/local/share/examples/jetpack/freebsd-base # cd ../example.showenv/
root@packer-freebsd-10:/usr/local/share/examples/jetpack/example.showenv # make
jetpack image freebsd-base build -cp=/usr/local/share/jetpack/jetpack.image.mk  /usr/bin/make .jetpack.build.
open /var/jetpack/pods/eaa0ec11-a7ad-4170-ac30-472444b9f849/rootfs/0/etc/resolv.conf: no such file or directory
/vagrant/jetpack/pod.go:281:
/vagrant/jetpack/pod.go:500:
/vagrant/jetpack/pod.go:501:
/vagrant/jetpack/image.go:331:
*** Error code 1

Stop.
make: stopped in /usr/local/share/examples/jetpack/example.showenv
```

スモークテストの時と同じエラーが出ました。
とりあえず今回はここまでとします。
