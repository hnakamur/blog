---
title: "ルートパーティションをZFSにしてUbuntu 20.04 LTSをインストールしてみた"
date: 2020-04-26T15:13:33+09:00
---

## はじめに

実はルートパーティションをZFSにするのは以前から試してみたいと思っていました。

[Trying Out Ubuntu 20.04 With ZFS + Zsys Automated APT Snapshots - Phoronix](https://www.phoronix.com/scan.php?page=news_item&px=Trying-Ubuntu-20.04-ZFS-Snaps)
をみて Ubuntu 20.04 LTS のデスクトップインストーラーで advanced features に追加されたというのを知りました。
ただし、 ZFS をルートファイルシステムにするのは引き続き experimental です。

ということで、今回普段使って無い物理サーバーでルートパーティションをZFSにしてUbuntu 20.04 LTSをインストールするのを試してみました。

ただし、上記のデスクトップインストーラーのメニューからではなく
[Ubuntu 18.04 Root on ZFS · openzfs/zfs Wiki](https://github.com/openzfs/zfs/wiki/Ubuntu-18.04-Root-on-ZFS) を参考に試行錯誤しました。

またインストーラーはデスクトップ用を使いますが、セットアップしたのは GUI 無しのサーバーです（ただし Wiki の手順を見るとデスクトップ版も同様にできそう）。

一部変更したので手順をメモしておきます。

試行錯誤の途中、上記のWiki以外にいろんなページを参照しましたが、主なのは以下の2つです。

* [Ubuntu server 20.04 zfs root and OCI – Riaan's SysAdmin Blog](https://blog.ls-al.com/category/zfs/)
* [zfsonlinux new feature: systemd mount integration : zfs](https://www.reddit.com/r/zfs/comments/8lf9d1/zfsonlinux_new_feature_systemd_mount_integration/)

また、使用するサーバーの起動方法がレガシー BIOS か UEFI かによって一部手順が異なります。私はレガシー BIOS のサーバーしか試してないので、ここではそちらの手順を書きます（ UEFI の場合は適宜 Wiki のほうを参照してください）。

## デスクトップインストーラーをダウンロードして USB メモリに書き出す

[Download Ubuntu Desktop | Download | Ubuntu](https://ubuntu.com/download/desktop)
から `ubuntu-20.04-desktop-amd64.iso` をダウンロードします。

サイズは約 2.6 GB なので、これ以上の容量を持つ USB メモリを用意します。

次に [balenaEtcher - Flash OS images to SD cards & USB drives](https://www.balena.io/etcher/) をダウンロードして上記の iso ファイルを USB メモリに書き出します。

## Step. 1:  インストール環境の整備
### デスクトップインストーラーを起動しsshの環境整備

サーバーに USB メモリを挿して、 BIOS のメニューで起動順序で USB メモリの優先度を上げて USB メモリから起動します。

GUI インストーラーが立ち上がって Welcome という画面が表示されたら、 TAB キーを押して Try Ubuntu ボタンにフォーカスを移動して（ボタンにオレンジの枠がつきます） Enter キーを押します（画面のスクリーンショットは [How to install Ubuntu 20.04 Focal Fossa Desktop - LinuxConfig.org](https://linuxconfig.org/how-to-install-ubuntu-20-04-focal-fossa-desktop) 参照）。

私は DHCP でネットワークが自動で設定されましたが、そうでない場合は手動で設定します。

ここからはターミナルで作業します。

Ctrl + Alt + T キーを押してターミナルを開き、以下のコマンドを実行します。

```console
sudo apt-add-repository universe
sudo apt update
```

アップグレード可能なパッケージがある旨表示されるかもしれませんが、 Live CD 環境は一時的なものなのでここでは更新せずに次に進みます。

passwd コマンドを実行して ubuntu ユーザーのパスワードを設定します。プロンプトが表示されますので設定したいパスワードを入力します。

```console
passwd
```

openssh-server をインストールします。

```console
sudo apt install --yes openssh-server
```

以下のコマンドを実行して IP アドレスを確認しておきます。

```console
ip a s
```

### 別のマシンから対象のサーバーに ssh してインストール作業を続行

以下の手順でコマンドをコピペして実行したいので、以下は別のマシンから対象のサーバーに ssh して作業します。

```console
ssh ubuntu@対象のサーバーのIPアドレス
```

以下のコマンドを実行し、上記で設定したパスワードを入力して root ユーザーになります。

```console
sudo -i
```

以下のコマンドを実行して Live CD の環境に ZFS をインストールします。

```console
apt install --yes debootstrap gdisk zfs-initramfs
```

## Step. 2: ディスクのフォーマット

以下のコマンドを実行して、インストール先のディスクエイリアスを確認します。

```console
ls -l /dev/disk/by-id/
```

仮想マシンにインストールするなどで上記で対象のディスクが出ない場合は Wiki を参照してください。

以下の作業のため、ディスク名を `DISK` という変数に設定しておきます。

```console
DISK=/dev/disk/by-id/インストール先のディスクエイリアス
```

私の場合は
`DISK=/dev/disk/by-id/ata-INTEL_SSDSA2M160G2GC_CVPO999999SN160AGN`
のような感じでした（999…のところは伏せてます）。

ディスクのパーティションテーブルを一旦全削除します。当然データは失われますので注意。

```console
sgdisk --zap-all $DISK
```

次にパーティションを作成していきます。

レガシーBIOSの場合は以下を実行します（ UEFI の場合は Wiki 参照）。

```console
sgdisk -a1 -n1:24K:+1000K -t1:EF02 $DISK
```

ブート (/boot) パーティションを作成します（ `-t` の後のパーティション番号は詰めて 2 にしても良いのですが、 Wiki の手順と合わせて UEFI 用の 2 を欠番とし、 3 としています）。

```console
sgdisk     -n3:0:+1G      -t3:BF01 $DISK
```

ルート (/) パーティションを作成します。
今回は暗号化しない方式を選択しました（もし暗号化する場合は Wiki に書かれている LUKS より [ZFSのネイティブ暗号化](https://wiki.archlinux.jp/index.php/ZFS#.E3.83.8D.E3.82.A4.E3.83.86.E3.82.A3.E3.83.96.E6.9A.97.E5.8F.B7.E5.8C.96) を使うほうが良さそうです）。

```console
sgdisk     -n4:0:0        -t4:BF01 $DISK
```

なお、 `-t` オプションのコロンの後の値は `sgdisk -L` で一覧が確認できます。
上記で使っているものを抜粋します。

```text
bf01 Solaris /usr & Mac ZFS
ef02 BIOS boot partition
```

EF02 は良いとして BF01 については下記の 83XX のほうが良さそうに思うのですが、よくわからないので今回は Wiki に従っておきました。

```text
8200 Linux swap                          8300 Linux filesystem
8301 Linux reserved                      8302 Linux /home
8303 Linux x86 root (/)                  8304 Linux x86-64 root (/)
8305 Linux ARM64 root (/)                8306 Linux /srv
8307 Linux ARM32 root (/)                8308 Linux dm-crypt
8309 Linux LUKS                          830a Linux IA-64 root (/)
830b Linux x86 root verity               830c Linux x86-64 root verity
830d Linux ARM32 root verity             830e Linux ARM64 root verity
830f Linux IA-64 root verity             8310 Linux /var
8311 Linux /var/tmp
```

（省略可）作成したパーティション一覧は `sgdisk -p ディスク名` で確認できます。以下に実行例を示します（一部情報を伏せてます）。

```console
# sgdisk -p $DISK
Disk /dev/disk/by-id/ata-INTEL_SSDSA2M160G2GC_CVPO999999SN160AGN: 312581808 sectors, 149.0 GiB
Sector size (logical/physical): 512/512 bytes
Disk identifier (GUID): xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Partition table holds up to 128 entries
Main partition table begins at sector 2 and ends at sector 33
First usable sector is 34, last usable sector is 312581774
Partitions will be aligned on 16-sector boundaries
Total free space is 14 sectors (7.0 KiB)

Number  Start (sector)    End (sector)  Size       Code  Name
   1              48            2047   1000.0 KiB  EF02
   3            2048         2099199   1024.0 MiB  BF01
   4         2099200       312581774   148.0 GiB   BF01
```

ブート (/boot) パーティション用の ZFS プール `bpool` を作成します。

```console
zpool create -o ashift=12 -d \
    -o feature@async_destroy=enabled \
    -o feature@bookmarks=enabled \
    -o feature@embedded_data=enabled \
    -o feature@empty_bpobj=enabled \
    -o feature@enabled_txg=enabled \
    -o feature@extensible_dataset=enabled \
    -o feature@filesystem_limits=enabled \
    -o feature@hole_birth=enabled \
    -o feature@large_blocks=enabled \
    -o feature@lz4_compress=enabled \
    -o feature@spacemap_histogram=enabled \
    -o feature@userobj_accounting=enabled \
    -O acltype=posixacl -O canmount=off -O compression=lz4 -O devices=off \
    -O normalization=formD -O relatime=on -O xattr=sa \
    -O mountpoint=/ -R /mnt bpool ${DISK}-part3
```

試行錯誤して 2 回目以降のときは `zfs list` では空なのに上記の `zfs create` では以下のエラーが出ました。この場合はメッセージにあるように bpool の前あたりに `-f` を付ければ OK でした。

```text
invalid vdev specification
use '-f' to override the following errors:
/dev/disk/by-id/ata-INTEL_SSDSA2M160G2GC_CVPO999999SN160AGN-part3 is part of exported pool 'bpool'
```

`normalization=formD` は Unicode の normalization の NFD に相当します。
昔 Subversion で Windows は NFC, Mac OS X は NFD と違うせいで全角カナの濁点が分かれない、分かれるで苦労したので NFC にしようかと思いましたが、 formD でも Windows と mac から繋いで問題ないと聞いたので formD にしておきました。

他のオプションの説明は Wiki を参照してください。

ルート (/) パーティション用の ZFS プール `rpool` を作成します（こちらも 2 回目以降は `-f` を付けてください）。

```console
zpool create -o ashift=12 \
    -O acltype=posixacl -O canmount=off -O compression=lz4 \
    -O dnodesize=auto -O normalization=formD -O relatime=on -O xattr=sa \
    -O mountpoint=/ -R /mnt rpool ${DISK}-part4
```

オプションの説明は Wiki を参照してください。

（省略可）作成したプール一覧を確認しておきます。

```console
# zpool list
NAME    SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
bpool   960M   420K   960M        -         -     0%     0%  1.00x    ONLINE  /mnt
rpool   148G   432K   148G        -         -     0%     0%  1.00x    ONLINE  /mnt
```

## Step. 3: システムのインストール

`rpool/ROOT` と `bpool/BOOT` のデータセットを作成します。

```console
zfs create -o canmount=off -o mountpoint=none rpool/ROOT
zfs create -o canmount=off -o mountpoint=none bpool/BOOT
```

ルート (/) とブート (/boot) ファイルシステム用のデータセットを作成します。

```console
zfs create -o canmount=noauto -o mountpoint=/ rpool/ROOT/ubuntu
zfs mount rpool/ROOT/ubuntu

zfs create -o canmount=noauto -o mountpoint=/boot bpool/BOOT/ubuntu
zfs mount bpool/BOOT/ubuntu
```

データセットを作成します。ここは各自のシステムの利用方法に応じて Wiki を参照しつつ調整してください。

```console
zfs create                                 rpool/home
zfs create -o mountpoint=/root             rpool/home/root
zfs create -o canmount=off                 rpool/var
zfs create -o canmount=off                 rpool/var/lib
zfs create                                 rpool/var/log
zfs create                                 rpool/var/spool

zfs create -o canmount=off                 rpool/usr
zfs create                                 rpool/usr/local

zfs create                                 rpool/var/snap

zfs create -o com.sun:auto-snapshot=false  rpool/var/lib/docker
```

`/var/cache` と `/var/tmp` を ZFS のスナップ対象から除外する場合に実行するコマンドも書かれていましたが、良く分からないのでとりあえず止めておきました。

`/tmp` については後述の tmpfs を使う設定のほうがお勧めとのことなのでデータセットは作成しません。

以下のように `debootstrap` を実行して最小限のシステムをインストールします。
Wiki で第 1 引数は bionic でしたが、ここでは focal にします。
第 2 引数は、今はインストール先のディスクを `/mnt` にマウントした状態ですので、それを指定しています。

```console
debootstrap focal /mnt
```

インターネットからパッケージをダウンロード、インストールするのでしばらく時間がかかります。

終わったら以下のコマンドを実行します。

```console
zfs set devices=off rpool
```

## Step. 4: システム設定

設定したいお好みのホスト名を一旦 `HOSTNAME` 変数に設定します。以下は例です。

```console
HOSTNAME=beagle
```

以下のコマンドで `/mnt/etc/hostname` にホスト名を保存します。

```console
echo ${HOSTNAME} > /mnt/etc/hostname
```

（省略可） 変更前の `/mnt/etc/hosts` を確認します。

```console
root@ubuntu:~# cat /mnt/etc/hosts
127.0.0.1       localhost
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters

```

以下のコマンドで `/mnt/etc/hosts` にエントリを追加します。

```console
sed -i -e "/^127.0.0.1/a\
127.0.1.1       ${HOSTNAME}
" /mnt/etc/hosts
```

（省略可） 変更後の `/mnt/etc/hosts` を確認します。

```console
root@ubuntu:~# cat /mnt/etc/hosts
127.0.0.1       localhost
127.0.1.1       beagle
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters

```

netplan のネットワーク設定ファイル `/mnt/etc/netplan/01-netcfg.yaml` を作成します。以下は作成するコマンドの例です（IPv6 アドレスの一部は伏せてます）。

```console
cat > /mnt/etc/netplan/01-netcfg.yaml <<'EOF'
# This file describes the network interfaces available on your system
# For more information, see netplan(5).
network:
  version: 2
  renderer: networkd
  ethernets:
    enp3s0:
      dhcp4: no
      addresses: [192.168.2.5/24, "xxxx:xxx:xxx:xxxx::5/60"]
      gateway4: 192.168.2.1
      nameservers:
        addresses: [192.168.1.1]
      dhcp6: yes
EOF
```

（省略可）変更前の `/mnt/etc/apt/sources.list` を確認します。

```console
root@ubuntu:~# cat /mnt/etc/apt/sources.list
deb http://archive.ubuntu.com/ubuntu focal main
```

`/mnt/etc/apt/sources.list` を変更します。

```console
cat > /mnt/etc/apt/sources.list <<'EOF'
deb http://jp.archive.ubuntu.com/ubuntu focal main universe
deb-src http://jp.archive.ubuntu.com/ubuntu focal main universe

deb http://security.ubuntu.com/ubuntu focal-security main universe
deb-src http://security.ubuntu.com/ubuntu focal-security main universe

deb http://jp.archive.ubuntu.com/ubuntu focal-updates main universe
deb-src http://jp.archive.ubuntu.com/ubuntu focal-updates main universe
EOF
```

Live CD 環境の仮想ファイルシステムをバインドマウントして、上記でセットアップした環境に chroot します（ `--bind` ではなく `--rbind` を使っていることに注意）。

```
mount --rbind /dev  /mnt/dev
mount --rbind /proc /mnt/proc
mount --rbind /sys  /mnt/sys
chroot /mnt /usr/bin/env DISK=$DISK bash --login
```

（省略可）Wiki ではここで
`ln -s /proc/self/mounts /etc/mtab`
を実行せよとありますが、以下のように既に同等のシンボリックリンクがありエラーになるのでスキップします。

```console
root@ubuntu:/# ls -l /etc/mtab
lrwxrwxrwx 1 root root 19 Apr 25 09:07 /etc/mtab -> ../proc/self/mounts
```

以下のコマンドを実行して chroot 環境内の apt のインデクスを更新します。

```console
apt update
```

この後のロケールとタイムゾーンの設定は [Ubuntu server 20.04 zfs root and OCI – Riaan's SysAdmin Blog](https://blog.ls-al.com/category/zfs/) を参考にしつつ、変更した手順としています。


ロケールは `en_US.UTF-8` と `ja_JP.UTF-8` を作成し、デフォルトは `en_US.UTF-8` にします。

```console
locale-gen --purge en_US.UTF-8 ja_JP.UTF-8
update-locale LANG=en_US.UTF-8 LANGUAGE=en_US
dpkg-reconfigure --frontend noninteractive locales
```

タイムゾーンは `Asia/Tokyo` にします。

```console
ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
dpkg-reconfigure -f noninteractive tzdata
```

以下のように出力されれば OK です。

```text
Current default time zone: 'Asia/Tokyo'
Local time is now:      Sat Apr 25 20:25:44 JST 2020.
Universal Time is now:  Sat Apr 25 11:25:44 UTC 2020.
```

Linux のカーネルイメージと ZFS を chroot 環境にインストールします（ HWE カーネルを使いたい場合は linux-image-generic の代わりに linux-image-generic-hwe-20.04 を指定します）。

```console
apt install --yes --no-install-recommends linux-image-generic zfs-initramfs
```

上記のコマンド実行の出力の最後に以下のようなメッセージが出ました。
`update-initramfs` が `/boot/initrd.img-5.4.0-26-generic` を生成したというのが重要です。この後 grub のインストール時に必要になるためです。

```text
update-initramfs: Generating /boot/initrd.img-5.4.0-26-generic
W: Possible missing firmware /lib/firmware/ast_dp501_fw.bin for module ast
```

また `/lib/firmware/ast_dp501_fw.bin` というファームウェアがみつらかないという警告が出ていますが、これは無視して進みました。


GRUB をレガシー BIOS 用にインストールします。

Wiki の手順では `apt install --yes grub-pc` ですが、CUI のダイアログが開いてインストール先を選択する必要があり、今後自動化したいときに困るので、代わりにググって見つけた以下のコマンドを実行します。

```console
DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install grub-pc
```

これだとインストール先を選べないのですが、 後述の手順で `/etc/default/grub` を変更した後 `grub-install $DISK` でインストールするので問題ありません。

passwd コマンドを実行して root ユーザーのパスワードを設定します。

```console
root@ubuntu:/# passwd
New password:
Retype new password:
passwd: password updated successfully
```

`4.10 Enable importing bpool` はスキップして、 代わりに zfs-mount-generator を使った手順を実行します。

bpool のマウントの設定を行います。

Wiki の手順では後の `5.8 Fix filesystem mount ordering` でブート (/boot) パーティション用の ZFS のプール bpool をマウントするための作業が入るのですが、そこで ZFS の systemd mount generator が出来るまではという但し書きがあります。

[zfsonlinux new feature: systemd mount integration : zfs](https://www.reddit.com/r/zfs/comments/8lf9d1/zfsonlinux_new_feature_systemd_mount_integration/)
で紹介されているように zfs-mount-generator というのが今はあるのでそれを使います。

一次情報としては [zfs-mount-generator (8)](https://manpages.ubuntu.com/manpages/focal/en/man8/zfs-mount-generator.8.html) を参照してください。

ただ、 chroot 環境で zfs のセットアップを行っている関係で手順を変更する必要がありました。

<!--
`/etc/zfs/zfs-list.cache` ディレクトリを作成し、その下に 2 つのプール名 bpool, rpool に対応した空のファイルを作成します。

```console
# mkdir /etc/zfs/zfs-list.cache
# touch /etc/zfs/zfs-list.cache/{b,r}pool
```
-->

次で利用する `/usr/lib/zfs-linux/zed.d/history_event-zfs-list-cacher.sh` が含まれる zfs-zed パッケージをインストールします。

```console
apt install --yes zfs-zed
```

次に manpage に書かれたようにシンボリックリンクを作成します。

```console
ln -s /usr/lib/zfs-linux/zed.d/history_event-zfs-list-cacher.sh /etc/zfs/zed.d/
```

通常の zfs の環境ならこの後 manpage の手順に従うと `/etc/zfs/zfs-list.cache/` 以下に zfs の pool の情報が反映されるのですが、今は chroot 環境で状況が異なるので、以下のコマンドで手動で作成します。

<!--
manpage には zfs-zed サービスの自動起動を有効にし、再起動するとありますが、インストールした時点で自動起動は有効になってるのと、再起動は `Running in chroot, ignoring request: restart` というエラーが出たのでスキップします。

```console
systemctl enable zfs-zed.service
systemctl restart zfs-zed.service
```

manpage によると `/etc/zfs/zfs-list.cache/` 以下のファイルを更新するのに以下のコマンドを使うとのことなので、手動で実行してみます。

```console
# zfs list -H -o name,mountpoint,canmount,atime,relatime,devices,exec,readonly,setuid,nbmand,encroot,keylocation
rpool   /       off     on      on      off     on      off     on      off     -       none
rpool/ROOT      none    off     on      on      off     on      off     on      off     -       none
rpool/ROOT/ubuntu       /       noauto  on      on      off     on      off     on      off     -       none
rpool/home      /home   on      on      on      off     on      off     on      off     -       none
rpool/home/hnakamur     /home/hnakamur  on      on      on      off     on      off     on      off     -       none
rpool/home/root /root   on      on      on      off     on      off     on      off     -       none
rpool/swap      -       -       -       -       -       -       off     -       -       -       none
rpool/usr       /usr    off     on      on      off     on      off     on      off     -       none
rpool/usr/local /usr/local      on      on      on      off     on      off     on      off     -       none
rpool/var       /var    off     on      on      off     on      off     on      off     -       none
rpool/var/lib   /var/lib        off     on      on      off     on      off     on      off     -       none
rpool/var/lib/docker    /var/lib/docker on      on      on      off     on      off     on      off     -       none
rpool/var/log   legacy  on      on      on      off     on      off     on      off     -       none
rpool/var/snap  /var/snap       on      on      on      off     on      off     on      off     -       none
rpool/var/spool legacy  on      on      on      off     on      off     on      off     -       none
```

manpage によると 1 つのプールにつき、どれか 1 つのデータセットについて `canmount` を同じ値で良いので設定すれば `/etc/zfs/zfs-list.cache/` 以下のファイルを更新されるとのことです。

上記だと項目が多すぎてわかりにくいので name と canmount のみの一覧を出してみます。

```console
# zfs list -H -o name,canmount
bpool   off
bpool/BOOT      off
bpool/BOOT/ubuntu       noauto
rpool   off
rpool/ROOT      off
rpool/ROOT/ubuntu       noauto
rpool/home      on
rpool/home/hnakamur     on
rpool/home/root on
rpool/swap      -
rpool/usr       off
rpool/usr/local on
rpool/var       off
rpool/var/lib   off
rpool/var/lib/docker    on
rpool/var/log   on
rpool/var/snap  on
rpool/var/spool on
```

以下のように bpool と rpool 内のそれぞれ 1 つのデータセットの canmount の値を同じ値で設定してみました。

```console
zfs set canmount=off bpool/BOOT
zfs set canmount=on rpool/home
```
-->


今の chroot 環境では `/mnt` にマウントしてますが、再起動後は `/` になるので sed で置換しつつ保存します。

```console
mkdir -p /etc/zfs/zfs-list.cache
zfs list -H -o name,mountpoint,canmount,atime,relatime,devices,exec,readonly,setuid,nbmand,encroot,keylocation | grep ^bpool | sed -e 's|/mnt/|/|;s|/mnt|/|' | tee /etc/zfs/zfs-list.cache/bpool
zfs list -H -o name,mountpoint,canmount,atime,relatime,devices,exec,readonly,setuid,nbmand,encroot,keylocation | grep ^rpool | sed -e 's|/mnt/|/|;s|/mnt|/|' | tee /etc/zfs/zfs-list.cache/rpool
```

<!--
`ls -l /etc/zfs/zfs-list.cache/` を実行すると bpool と rpool のファイルが空でなくなっていました。※この手順だと空のままだった。
-->

以下のコマンドで次回起動時に tmpfs を /tmp にマウントするようにします。

```console
cp /usr/share/systemd/tmp.mount /etc/systemd/system/
systemctl enable tmp.mount
```

lpadmin と sambashare のグループ作成はスキップしました。

## Step. 5: GRUB のインストール

`grub-probe /boot` で ZFS のブートファイルシステムが認識されていることを確認します。
以下のように zfs と出力されれば OK です。

```console
# grub-probe /boot
zfs
```

`update-initramfs -u -k all` は [Ubuntu server 20.04 zfs root and OCI – Riaan's SysAdmin Blog](https://blog.ls-al.com/category/zfs/) でもうまくいかないと書いてあったので、手順を変更して以下のように実行していました。が、再度確認してみると、どちらでも以下のように実行できました。さらに言うと上記の grub-pc インストールのタイミングでも生成されているので、ここでは実行は不要そうな気もします。

```console
root@ubuntu:/# update-initramfs -u -k $(uname -r)
update-initramfs: Generating /boot/initrd.img-5.4.0-26-generic
W: Possible missing firmware /lib/firmware/ast_dp501_fw.bin for module ast
```

```console
root@ubuntu:/# update-initramfs -u -k all
update-initramfs: Generating /boot/initrd.img-5.4.0-26-generic
W: Possible missing firmware /lib/firmware/ast_dp501_fw.bin for module ast
```

上記のように `/lib/firmware/ast_dp501_fw.bin` というファームウェアがみつらかないという警告が出ましたが、これは無視して進みました。

（省略可）`cat /etc/default/grub` で変更前のファイルの内容を確認します。
私の環境では以下のようになっていました。

```console
root@ubuntu:/# cat /etc/default/grub
# If you change this file, run 'update-grub' afterwards to update
# /boot/grub/grub.cfg.
# For full documentation of the options in this file, see:
#   info -f grub -n 'Simple configuration'

GRUB_DEFAULT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_TIMEOUT=0
GRUB_DISTRIBUTOR=`lsb_release -i -s 2> /dev/null || echo Debian`
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""

# Uncomment to enable BadRAM filtering, modify to suit your needs
# This works with Linux (no patch required) and with any kernel that obtains
# the memory map information from GRUB (GNU Mach, kernel of FreeBSD ...)
#GRUB_BADRAM="0x01234567,0xfefefefe,0x89abcdef,0xefefefef"

# Uncomment to disable graphical terminal (grub-pc only)
#GRUB_TERMINAL=console

# The resolution used on graphical terminal
# note that you can use only modes which your graphic card supports via VBE
# you can see them in real GRUB with the command `vbeinfo'
#GRUB_GFXMODE=640x480

# Uncomment if you don't want GRUB to pass "root=UUID=xxx" parameter to Linux
#GRUB_DISABLE_LINUX_UUID=true

# Uncomment to disable generation of recovery mode menu entries
#GRUB_DISABLE_RECOVERY="true"

# Uncomment to get a beep at grub start
#GRUB_INIT_TUNE="480 440 1"
```

以下のコマンドで `/etc/default/grub` を更新します。

```console
sed -i -e '/^GRUB_TIMEOUT=/{s/=.*/=5/;a\
GRUB_RECORDFAIL_TIMEOUT=5
}
/^GRUB_CMDLINE_LINUX_DEFAULT=/s/quiet splash//
s|^GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX="root=ZFS=rpool/ROOT/ubuntu"|
/^#GRUB_TERMINAL=console/s/#//
' /etc/default/grub
```

（省略可）変更後の `/etc/default/grub` も確認しておきます。

```console
root@ubuntu:/# cat /etc/default/grub
# If you change this file, run 'update-grub' afterwards to update
# /boot/grub/grub.cfg.
# For full documentation of the options in this file, see:
#   info -f grub -n 'Simple configuration'

GRUB_DEFAULT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_TIMEOUT=5
GRUB_RECORDFAIL_TIMEOUT=5
GRUB_DISTRIBUTOR=`lsb_release -i -s 2> /dev/null || echo Debian`
GRUB_CMDLINE_LINUX_DEFAULT=""
GRUB_CMDLINE_LINUX="root=ZFS=rpool/ROOT/ubuntu"

# Uncomment to enable BadRAM filtering, modify to suit your needs
# This works with Linux (no patch required) and with any kernel that obtains
# the memory map information from GRUB (GNU Mach, kernel of FreeBSD ...)
#GRUB_BADRAM="0x01234567,0xfefefefe,0x89abcdef,0xefefefef"

# Uncomment to disable graphical terminal (grub-pc only)
GRUB_TERMINAL=console

# The resolution used on graphical terminal
# note that you can use only modes which your graphic card supports via VBE
# you can see them in real GRUB with the command `vbeinfo'
#GRUB_GFXMODE=640x480

# Uncomment if you don't want GRUB to pass "root=UUID=xxx" parameter to Linux
#GRUB_DISABLE_LINUX_UUID=true

# Uncomment to disable generation of recovery mode menu entries
#GRUB_DISABLE_RECOVERY="true"

# Uncomment to get a beep at grub start
#GRUB_INIT_TUNE="480 440 1"
```

grub の設定変更を反映します。

```console
update-grub
```

実行例を示します。 `Found linux image` と `Found initrd image` の行が出ていれば大丈夫です。
`/dev/sda1` でエラーが出ていますがこれは USB メモリなので大丈夫です。
osprober でも絵エラーが出ていますが Wiki に問題ないと書いてあるのでこれも OK です。

```console
root@ubuntu:/# update-grub
Sourcing file `/etc/default/grub'
Sourcing file `/etc/default/grub.d/init-select.cfg'
Generating grub configuration file ...
Found linux image: vmlinuz-5.4.0-26-generic in rpool/ROOT/ubuntu
Found initrd image: initrd.img-5.4.0-26-generic in rpool/ROOT/ubuntu
grub-probe: error: cannot find a GRUB drive for /dev/sda1.  Check your device.map.
device-mapper: reload ioctl on osprober-linux-sdb4  failed: Device or resource busy
Command failed.
done
```

レガシー BIOS 用に GRUB をインストールします。

```console
grub-install $DISK
```

実行例を示します。

```console
root@ubuntu:/# grub-install $DISK
Installing for i386-pc platform.
Installation finished. No error reported.
```

ZFS のモジュールがインストールされていることを確認。

```console
ls /boot/grub/*/zfs.mod
```

私の環境では以下のようになりました。

```console
root@ubuntu:/# ls /boot/grub/*/zfs.mod
/boot/grub/i386-pc/zfs.mod
```

`5.8 Fix filesystem mount ordering` のところは、上記の zfs-mount-generator の手順で対応済みなのでスキップします。

## Step. 6: 初回のブート

初回インストールのスナップショットを作成しておきます。

```console
zfs snapshot bpool/BOOT/ubuntu@install
zfs snapshot rpool/ROOT/ubuntu@install
```

chroot 環境から抜けて Live CD 環境に戻ります。

```console
exit
```

Live CD 環境でマウント中のファイルシステムを全てアンマウントします。

```console
mount | grep -v zfs | tac | awk '/\/mnt/ {print $3}' | xargs -i{} umount -lf {}
zpool export -a
```

リブートします。

```console
systemctl reboot
```

起動したらサーバーのコンソールで root ユーザーで上記で設定したパスワードを入力してログインします。

ログインしたら、自分用のユーザーを作成します。まずユーザー名を一旦変数にセットします。以下は例です。

```console
YOURUSERNAME=hnakamur
```

ユーザーを作成します（私は `adduser` より `useradd` のほうがプロンプト出たりしないので好きです）。

```console
useradd -m $YOURUSERNAME
```

作成したユーザーのパスワードを設定します。

```console
passwd $YOURUSERNAME
```

作成したユーザーを adm などのグループに所属させます。上記で lpadmin と sambashare グループの作成を私はスキップしたので、ここでもその 2 つは除いています。

```console
usermod -a -G adm,cdrom,dip,plugdev,sudo $YOURUSERNAME
```

レガシー BIOS 用に GRUB の設定を再度行います。本当に必要かは調べていませんが、とりあえず Wiki の手順に従います。上記で grub-pc をインストールしたときと同様に TUI で対象のディスクを選択します。

```console
dpkg-reconfigure grub-pc
```

## Step. 7: スワップを設定します。

[物理メモリが十分にあってもスワップは重要](https://twitter.com/hnakamur2/status/1228885297917620226) ですので、スワップは必ず設定します。

容量は適宜変更してください。ここではサーバーの RAM と同じ 16GB にしてみました。

まずスワップ用のデータセットを作成します。

```console
zfs create -V 16G -b $(getconf PAGESIZE) -o compression=zle \
    -o logbias=throughput -o sync=always \
    -o primarycache=metadata -o secondarycache=none \
    -o com.sun:auto-snapshot=false rpool/swap
```

次にスワップの設定を行います。

```console
mkswap -f /dev/zvol/rpool/swap
echo /dev/zvol/rpool/swap none swap discard 0 0 >> /etc/fstab
echo RESUME=none > /etc/initramfs-tools/conf.d/resume
```

以下のコマンドでスワップを有効にします。

```console
swapon -av
```

`swapon --show` コマンドで有効になったことを確認します。以下は実行例です。

```
$ swapon --show
NAME     TYPE      SIZE USED PRIO
/dev/zd0 partition  16G   0B   -2
```

## Step. 8: フルのソフトウェアインストール

ミニマムインストールをアップグレードします。

```console
apt dist-upgrade --yes
```

今回はコマンドライン環境のみをインストールするので以下を実行します（ GUI 環境をインストールする場合は Wiki 参照）。

```console
apt install --yes ubuntu-standard
```

オプションでログの圧縮を無効化します。 ZFS で圧縮する設定にしたので、ログのローテートのほうでは圧縮しないことにする場合は以下のコマンドを実行して無効にします。

が、後で他のサーバーに転送したりする場合は無効にしないほうが良いかもしれません。

```console
for file in /etc/logrotate.d/* ; do
    if grep -Eq "(^|[^#y])compress" "$file" ; then
        sed -i -r "s/(^|[^#y])(compress)/\1#\2/" "$file"
    fi
done
```

リブートします。

```console
systemctl reboot
```

## Step. 9: 最終クリーンアップ

再起動が正常に出来ることを確認し、上記で作成した自分用のユーザーでログインできることを確認します。

オプションで上記で作成したスナップショットを削除します。

```console
sudo zfs destroy bpool/BOOT/ubuntu@install
sudo zfs destroy rpool/ROOT/ubuntu@install
```

上記で設定した root ユーザーのパスワードを削除します。

```console
sudo usermod -p '*' root
```

今後は root 権限で作業するときは自分のユーザーから sudo つきでコマンドを実行するか、 `sudo -i` で root ユーザーに切り替えます。

Wiki には書いていませんが、 ssh の設定も行います。

他の作業用マシンの `~/.ssh/config` にこのサーバーのエントリを追加します。以下は例です。

```console
Host beagle
  Hostname 192.168.2.5
```

まず他の作業用マシンからこのサーバーに自分のユーザーでパスワードでログイン出来ることを確認します。以下の例でホスト名は適宜変更してください。

```console
ssh beagle
````


ログイン出来たら作業用マシンの別端末で ssh の公開鍵を設定します。

```console
ssh-copy-id beagle
```

その後再度 ssh でログインし、今度はパスワード入力無しで鍵認証で入れることを確認します。

```console
ssh beagle
```

ssh サーバーの設定を変更し、パスワード入力を無効にします。

```console
sudo sed -i -e '/^#PasswordAuthentication yes/a\
PasswordAuthentication no
/^UsePAM yes/{s/^/#/;a\
UsePAM no
}
/^X11Forwarding yes/{s/^/#/;a\
X11Forwarding no
}
' /etc/ssh/sshd_config
```

上記の設定変更を反映します。

```console
systemctl reload sshd
```

別の作業マシンから鍵認証で ssh 出来ることを確認します。

```console
ssh beagle
```

以下のようにパスワード認証を優先にしてログインできないことを確認します。

```console
$ ssh -o PreferredAuthentications=password 192.168.2.5
hnakamur@192.168.2.5: Permission denied (publickey).
```
