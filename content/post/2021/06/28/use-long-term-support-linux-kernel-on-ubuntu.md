---
title: "Ubuntuで長期サポートのLinuxカーネルを使用する"
date: 2021-06-28T05:12:14+09:00
---

## はじめに

[The Linux Kernel Archives - Releases](https://www.kernel.org/category/releases.html) と [Linux kernel version history - Wikipedia](https://en.wikipedia.org/wiki/Linux_kernel_version_history) を見て Linux カーネルは長期サポート版とそうでない版があることを知りました。なるべくなら長期サポート版を使うほうが安心だなと思ったので切り替えることにしました。その際のメモです。

ちなみに「長期サポート」は [The Linux Kernel Archives - Releases](https://www.kernel.org/category/releases.html) では "longterm maintenance" kernel release とか longterm release kernel と書かれていました。
[Linux kernel version history - Wikipedia](https://en.wikipedia.org/wiki/Linux_kernel_version_history) のほうでは Long-Term Support (LTS) と書かれていました。

## Ubuntu での長期サポート版 Linux カーネルパッケージ

* Ubuntu 18.04 LTS では linux-image-generic-hwe-18.04 が 5.4.x
* Ubuntu 20.04 LTS では linux-image-oem-20.04b が 5.10.x

`sudo apt install linux-image-oem-20.04b` のようにインストールすればOKです。


## カーネルのバージョンを下げてブートする場合の手順

長期サポートの Linux カーネルのことを知る前に Ubuntu 20.04 LTS で linux-image-generic-hwe-20.04-edge で 5.11.x をインストールしていたのですが、その後 linux-image-oem-20.04b で 5.10.x を入れました。

このようにバージョンを下げる場合は [第639回　Ubuntuに「トラブル時に」ログインするいろいろな方法：Ubuntu Weekly Recipe｜gihyo.jp … 技術評論社](https://gihyo.jp/admin/serial/01/ubuntu-recipe/0639) の手順で起動時に GRUB メニューを表示して切り替えればよいのですが、わりと面倒なので
[How to Change the Default Ubuntu Kernel - Meetrix.IO](https://meetrix.io/blog/aws/changing-default-ubuntu-kernel.html) の手順で一時的にデフォルトのカーネルを切り替えるようにしました。

この手順をメモしておきます。

GRUB のメニューに登録されているカーネル一覧を以下のコマンドで確認します。

```sh
grep -A100 submenu /boot/grub/grub.cfg | grep menuentry
```

実行結果の例です。

```
$ grep -A100 submenu /boot/grub/grub.cfg | grep menuentry
submenu 'Advanced options for Ubuntu' $menuentry_id_option 'gnulinux-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e' {
        menuentry 'Ubuntu, with Linux 5.11.0-22-generic' --class ubuntu --class gnu-linux --class gnu --class os $menuentry_id_option 'gnulinux-5.11.0-22-generic-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e' {
        menuentry 'Ubuntu, with Linux 5.11.0-22-generic (recovery mode)' --class ubuntu --class gnu-linux --class gnu --class os $menuentry_id_option 'gnulinux-5.11.0-22-generic-recovery-0e6937b5-14c5-496d-ba95-42efe61cd35e' {
        menuentry 'Ubuntu, with Linux 5.10.0-1034-oem' --class ubuntu --class gnu-linux --class gnu --class os $menuentry_id_option 'gnulinux-5.10.0-1034-oem-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e' {
        menuentry 'Ubuntu, with Linux 5.10.0-1034-oem (recovery mode)' --class ubuntu --class gnu-linux --class gnu --class os $menuentry_id_option 'gnulinux-5.10.0-1034-oem-recovery-0e6937b5-14c5-496d-ba95-42efe61cd35e' {
menuentry 'UEFI Firmware Settings' $menuentry_id_option 'uefi-firmware' {
```

ブートしたいカーネルの submenu と menuentry の ID をメモします。

上記の例だと `submenu 'Advanced options for Ubuntu'` の ID は gnulinux-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e です。
`menuentry 'Ubuntu, with Linux 5.10.0-1034-oem'` の ID は gnulinux-5.10.0-1034-oem-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e です。
これを `>` で連結した文字列を `/etc/default/grub` の `GRUB_DEFAULT` に指定すればOKです。


GRUB 設定を編集します。

```sh
sudo vim /etc/default/grub
```

編集前は以下のような内容になっていました。

```
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
…(略)…
```

上記の例の場合は `GRUB_DEFAULT` の設定を以下のように変更します。

```
GRUB_DEFAULT="gnulinux-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e>gnulinux-5.10.0-1034-oem-advanced-0e6937b5-14c5-496d-ba95-42efe61cd35e"
```

あとは `update-grub` で変更を反映して再起動します。

```sh
sudo update-grub
```

```sh
sudo reboot
```

## 再起動後不要なカーネルパッケージを削除してGRUBの設定を戻す

無事アップデートできたら不要なカーネルパッケージを削除します。

まず念のため今ブートしたカーネルのバージョンを確認します。

```sh
uname -r
```

実行例です。

```
$ uname -r
5.10.0-1034-oem
```

次に削除対象のパッケージ一覧を確認します。grepのパターンは適宜調整してください。

```
dpkg -l | grep linux.*5\.11
```

実行例です。

```
$ dpkg -l | grep linux.*5\.11
ii  linux-image-5.11.0-22-generic                 5.11.0-22.23~20.04.1                                             amd64        Signed kernel image generic
ii  linux-image-generic-hwe-20.04-edge            5.11.0.22.23~20.04.6                                             amd64        Generic Linux kernel image
ii  linux-modules-5.11.0-22-generic               5.11.0-22.23~20.04.1                                             amd64        Linux kernel extra modules for version 5.11.0 on 64 bit x86 SMP
ii  linux-modules-extra-5.11.0-22-generic         5.11.0-22.23~20.04.1                                             amd64        Linux kernel extra modules for version 5.11.0 on 64 bit x86 SMP
```

ちなみに `dpkg -l` の出力結果のヘッダー行は以下のようになっています。
行頭の ii は Desired が Install で Status が Inst になっていることを表しています。

```
$ dpkg -l | head -5
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                                          Version                                                          Architecture Description
+++-=============================================-================================================================-============-===============================================================================
```

希望の一覧になっていることを確認したら以下のコマンドでパッケージを削除します。

```
dpkg -l | grep linux.*5\.11 | awk '{print $2}' | xargs sudo apt remove -y
```

削除後一部のパッケージが設定ファイルだけ残った状態になるので以下のコマンドで確認します。

```
dpkg -l | grep ^.c
```

実行例です。先頭の rc は Desired が Removed で Status が Conf-files を表しています。

```
$ dpkg -l | grep ^.c
rc  linux-image-5.11.0-22-generic                 5.11.0-22.23~20.04.1                                             amd64        Signed kernel image generic
rc  linux-modules-5.11.0-22-generic               5.11.0-22.23~20.04.1                                             amd64        Linux kernel extra modules for version 5.11.0 on 64 bit x86 SMP
rc  linux-modules-extra-5.11.0-22-generic         5.11.0-22.23~20.04.1                                             amd64        Linux kernel extra modules for version 5.11.0 on 64 bit x86 SMP
```

対象を確認したら以下のコマンドでパージします。

```sh
dpkg -l | grep ^.c | awk '{print $2}' | xargs sudo apt purge -y
```

あとは GRUB の設定を元に戻します。

```sh
sudo vim /etc/default/grub
```

で

```
GRUB_DEFAULT=0
```

に戻して

```sh
sudo update-grub
```

を実行して反映します。
