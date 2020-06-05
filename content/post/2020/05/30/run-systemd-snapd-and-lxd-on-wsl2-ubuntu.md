---
title: "WSL2のUbuntuでsystemdとsnapdとLXDとdockerを動かしてみた"
date: 2020-05-30T15:50:00+09:00
lastmod: 2020-06-05T17:30:00+09:00
---

## はじめに

[WSL2のUbuntuとDocker Desktop for Windowsを試してみた · hnakamur's blog](/blog/2020/05/28/setup-wsl2-ubuntu-and-docker-desktop-for-windows/) で Docker は動いたので、次は LXD を動かそうと調べました。

すると WSL2 では標準では systemd が動いていないため snapd や LXD が使えないことが分かりました。

検索して見ると有志の方が systemd を動かす方法を紹介されていたので試してみたところ、 snapd と LXD も動かせました。

そこで手順と調査メモを残しておきます。

なお systemd を動かすのは Microsoft の WSL2 チームのサポート外の可能性が高いと思いますので、あくまで自己責任で。

## Ubuntu 20.04 LTS で LXD を動かすには snapd が必要と判明

当初 apt で lxd をインストールしようとして以下のコマンドを実行しました。

```console
sudo apt update
apt show lxd
```

すると `apt show lxd` で以下のように出力され、lxd の deb パッケージはダミーで snap でインストールするように書かれていました。

```console
$ apt show lxd
Package: lxd
Version: 1:0.9
Priority: optional
Section: universe/admin
Origin: Ubuntu
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Installed-Size: 79.9 kB
Pre-Depends: debconf, snapd
Depends: debconf (>= 0.5) | debconf-2.0
Breaks: lxd-client (<< 1:0.0~), lxd-tools (<< 1:0.0~)
Replaces: lxd-client (<< 1:0.0~), lxd-tools (<< 1:0.0~)
Homepage: https://linuxcontainers.org/
Download-Size: 5444 B
APT-Sources: http://archive.ubuntu.com/ubuntu focal/universe amd64 Packages
Description: Transitional package - lxd -> snap (lxd)
 This is a transitional dummy package. It can safely be removed.
 .
 lxd is now replaced by the LXD snap.
```

WSL2 の Ubuntu で snap を動かす方法を調べると以下のイシューを見つけました。
[WSL2- Ubuntu 20.04 Snap store doesn't work due to systemd dependency · Issue #5126 · microsoft/WSL](https://github.com/microsoft/WSL/issues/5126)

そこのコメントに回避策として
[Running Snaps on WSL2 (Insiders only for now) - snapd - snapcraft.io](https://forum.snapcraft.io/t/running-snaps-on-wsl2-insiders-only-for-now/13033)
が紹介されていました。

冒頭にスクリプトが書かれていますが、下のコメントを見ていくと
[GUI アプリも動いたとのコメント](https://forum.snapcraft.io/t/running-snaps-on-wsl2-insiders-only-for-now/13033/3) がありました。

また [DamionGans さんのコメント](https://forum.snapcraft.io/t/running-snaps-on-wsl2-insiders-only-for-now/13033/29) で
[DamionGans/ubuntu-wsl2-systemd-script: Script to enable systemd support on current Ubuntu WSL2 images from the Windows store](https://github.com/DamionGans/ubuntu-wsl2-systemd-script) のレポジトリを作ったと書かれています。

[トピ主の daniel さんのコメント](https://forum.snapcraft.io/t/running-snaps-on-wsl2-insiders-only-for-now/13033/38) で冒頭のスクリプトは古いので最新版はこののレポジトリを参照するように書かれていました（最初の投稿から日にちがある程度経つとロックされて編集不可になるとのこと）。

細かいところで少し気になるところがあったのでフォークして改変しました。改変についてはプルリクエストを送ったところです。

2020-06-01 追記。私の 3 つのプルリクエストはマージされました。また [Too many levels of symbolic links when running ls -l /proc/sys/fs/binfmt_misc · Issue #15 · DamionGans/ubuntu-wsl2-systemd-script](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/issues/15) というイシューを立てたところ [Add binfmt_misc override by diddledan · Pull Request #17 · DamionGans/ubuntu-wsl2-systemd-script](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/pull/17/files) で修正頂きました。

以下の手順ではこの修正版を使います。

## （横道） /var/lib/ubuntu-release-upgrader/release-upgrade-available 作成のパーミションエラー （2020-06-01 追記）

一度 ubuntu-wsl2-systemd-script の古い版を組み込んでいたのを外して起動したときに以下のエラーが出ました。

```
/usr/lib/ubuntu-release-upgrader/release-upgrade-motd: 31: cannot create /var/lib/ubuntu-release-upgrader/release-upgrade-available: Permission denied
```

`grep -r release-upgrade-motd /etc/` で調べると `/etc/update-motd.d/91-release-upgrade` と `/etc/cron.weekly/update-notifier-common` が `/usr/lib/ubuntu-release-upgrader/release-upgrade-motd` を呼んでいます。

このスクリプトを見ると `[ "$(id -u)" = 0 ]` という分岐があって root で実行される場合とそうでない場合があるようです。で root で作ったファイルを非 root ユーザーで更新しようとしてエラーになっているということのようです。

一旦置いときます。

## WSL2 で systemd と snapd を動かす手順

以下のコマンドを実行して上記のスクリプトをダウンロード、展開して移動します。

```console
cd
curl -sSL https://github.com/diddledan/ubuntu-wsl2-systemd-script/archive/binfmt_misc.tar.gz | tar zx
cd ubuntu-wsl2-systemd-script-binfmt_misc
```

あるいはお好みで `git clone` を使う方式でも構いません。

```console
cd
git clone https://github.com/diddledan/ubuntu-wsl2-systemd-script
cd ubuntu-wsl2-systemd-script
git switch binfmt_misc
```

以下のコマンドを実行すると、 `/etc/bash.bashrc` を改変し、 WSL2 の起動時に systemd を実行するようになります。

```console
bash ubuntu-wsl2-systemd-script.sh
```

最後の `ubuntu-wsl2-systemd-script.sh` を実行すると sudo のパスワードプロンプトが出るのでパスワードを入力します。

実行されるコマンドを確認したいので bash の `-x` つきで実行したときの出力を参考のため貼っておきます（実は今回は事前に sudo つきのコマンドを実行していたので sudo のパスワードプロンプトは出ませんでしたが、そうでない場合は `sudo apt-get update` のところでパスワード入力を求められます）。

```
$ bash -x ubuntu-wsl2-systemd-script.sh
+ '[' -z '' ']'
+ return
+ '[' -f /usr/sbin/start-systemd-namespace ']'
++ dirname ubuntu-wsl2-systemd-script.sh
+ self_dir=.
+ sudo apt-get update
Hit:1 http://archive.ubuntu.com/ubuntu focal InRelease
Hit:2 http://ppa.launchpad.net/hnakamur/libsxg/ubuntu focal InRelease
Get:3 http://security.ubuntu.com/ubuntu focal-security InRelease [107 kB]
Get:4 http://archive.ubuntu.com/ubuntu focal-updates InRelease [107 kB]
Hit:5 http://ppa.launchpad.net/hnakamur/nginx/ubuntu focal InRelease
Hit:6 http://ppa.launchpad.net/hnakamur/openresty-luajit/ubuntu focal InRelease
Get:7 http://archive.ubuntu.com/ubuntu focal-backports InRelease [98.3 kB]
Get:8 http://archive.ubuntu.com/ubuntu focal-updates/main amd64 Packages [148 kB]
Get:9 http://archive.ubuntu.com/ubuntu focal-updates/universe amd64 Packages [74.9 kB]
Fetched 535 kB in 3s (205 kB/s)
Reading package lists... Done
+ sudo apt-get install -yqq daemonize dbus-user-session fontconfig
+ sudo cp ./start-systemd-namespace /usr/sbin/start-systemd-namespace
+ sudo cp ./enter-systemd-namespace /usr/sbin/enter-systemd-namespace
+ sudo chmod +x /usr/sbin/enter-systemd-namespace
+ sudo tee /etc/sudoers.d/systemd-namespace
+ grep start-systemd-namespace /etc/bash.bashrc
+ sudo sed -i '2a# Start or enter a PID namespace in WSL2\nsource /usr/sbin/start-systemd-namespace\n' /etc/bash.bashrc
+ sudo rm /etc/systemd/user/sockets.target.wants/dirmngr.socket
+ sudo rm /etc/systemd/user/sockets.target.wants/gpg-agent-browser.socket /etc/systemd/user/sockets.target.wants/gpg-agent-extra.socket /etc/systemd/user/sockets.target.wants/gpg-agent-ssh.socket /etc/systemd/user/sockets.target.wants/gpg-agent.socket
+ sudo rm /lib/systemd/system/sysinit.target.wants/proc-sys-fs-binfmt_misc.automount
+ sudo rm /lib/systemd/system/sysinit.target.wants/proc-sys-fs-binfmt_misc.mount
rm: cannot remove '/lib/systemd/system/sysinit.target.wants/proc-sys-fs-binfmt_misc.mount': No such file or directory
+ sudo rm /lib/systemd/system/sysinit.target.wants/systemd-binfmt.service
+ '[' -f /proc/sys/fs/binfmt_misc/WSLInterop ']'
++ head -n1 /proc/sys/fs/binfmt_misc/WSLInterop
+ '[' enabled == enabled ']'
+ cmd.exe /C setx WSLENV BASH_ENV/u

成功: 指定した値は保存されました。
+ cmd.exe /C setx BASH_ENV /etc/bash.bashrc

成功: 指定した値は保存されました。
```

`ps auxwwf` でプロセス一覧を確認すると、この時点ではまだ WSL2 の独自 init が動いています。


```console
hnakamur@sunshine7:~/ubuntu-wsl2-systemd-script-modify$ ps auxwwf
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0    900   568 ?        Sl   16:04   0:00 /init
root         6  0.0  0.0    892    76 ?        Ss   16:04   0:00 /init
root         7  0.0  0.0    892    76 ?        S    16:04   0:00  \_ /init
hnakamur     8  0.0  0.0  10176  5120 pts/0    Ss   16:04   0:00      \_ -bash
hnakamur  1552  0.0  0.0  10604  3248 pts/0    R+   16:23   0:00      |   \_ ps auxwwf
hnakamur    25  0.0  0.0   6968  1772 ?        Ss   16:04   0:00      \_ socat UNIX-LISTEN:/home/hnakamur/.ssh/agent.sock,fork EXEC:/mnt/c/wsl-ssh-agent/npiperelay.exe -ei -s //./pipe/openssh-ssh-agent,nofork
root        48  0.0  0.0    892    76 ?        Ss   16:04   0:00 /init
root        49  0.0  0.0    892    76 ?        S    16:04   0:00  \_ /init
root        50  0.0  0.1 487988 21888 pts/1    Ssl+ 16:04   0:00      \_ /mnt/wsl/docker-desktop/docker-desktop-proxy --distro-name Ubuntu-20.04 --docker-desktop-root /mnt/wsl/docker-desktop
```

`wsl.exe -t ubuntu-20.04` を実行して WSL2 の VM を終了させます。ディストリビューション名はお使いの環境に応じて適宜変更してください。

```console
hnakamur@sunshine7:~/ubuntu-wsl2-systemd-script-modify$ wsl.exe -t ubuntu-20.04

[プロセスはコード 1 で終了しました]
```

このコマンドは WSL2 の VM 上で実行しても大丈夫です。
ただし上記のように [Windows Terminal](https://github.com/microsoft/terminal) のセッションは終了するので、閉じて再度開きなおす必要があります。

端末を開きなおすと `/etc/bash.bashrc` から `source /usr/sbin/start-systemd-namespace` を実行するところで以下のようなメッセージが出力されました。

```text
Sleeping for 2 seconds to let systemd settle
```

その後いつもの Welcome メッセージとプロンプトが表示されました。

```text
Welcome to Ubuntu 20.04 LTS (GNU/Linux 4.19.104-microsoft-standard x86_64)
…(略)…
```

`ps auxwwf` でプロセス一覧を確認すると、以下のように systemd と snapd が動いていました。
nginx が動いているのは別途インストールして `systemctl enable nginx` していたからです。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ ps auxwwf
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root           2  0.0  0.0  10560  4588 pts/1    S    16:27   0:00 /bin/login -p -f          'HOSTTYPE=x86_64' 'PWD=/mnt/c/Users/hnakamur' 'TERM=xterm-256color' 'WSLENV=WT_SESSION::WT_PROFILE_ID' 'WSL_DISTRO_NAME=Ubuntu-20.04' 'WSL_INTEROP=/run/WSL/37_interop' 'WT_PROFILE_ID={07b52e3e-de2c-5db4-bd2d-ba144ed6c273}' 'WT_SESSION=fc0d0da7-2ebf-446f-adec-b6424ccc2fdf'
hnakamur     321  0.6  0.0  10048  5088 pts/1    S    16:27   0:00  \_ -bash
hnakamur    1124  0.0  0.0  10604  3296 pts/1    R+   16:28   0:00      \_ ps auxwwf
root           1 10.1  0.0 107632 12776 ?        Rs   16:27   0:01 /lib/systemd/systemd --system-unit=basic.target
root          58  5.2  0.0  37056 12240 ?        S<s  16:27   0:00 /lib/systemd/systemd-journald
root          80  2.5  0.0  18260  5124 ?        Ss   16:27   0:00 /lib/systemd/systemd-udevd
systemd+      84  4.0  0.0  18680  7908 ?        Ss   16:27   0:00 /lib/systemd/systemd-networkd
systemd+     300  3.8  0.0  24052 12200 ?        Ss   16:27   0:00 /lib/systemd/systemd-resolved
systemd+     301  4.0  0.0  90392  6408 ?        Ssl  16:27   0:00 /lib/systemd/systemd-timesyncd
hnakamur     342  0.0  0.0   6968  1856 ?        Ss   16:27   0:00 socat UNIX-LISTEN:/home/hnakamur/.ssh/agent.sock,fork EXEC:/mnt/c/wsl-ssh-agent/npiperelay.exe -ei -s //./pipe/openssh-ssh-agent,nofork
root         345  0.1  0.0 237304  6940 ?        Ssl  16:28   0:00 /usr/lib/accountsservice/accounts-daemon
message+     346  2.1  0.0   7352  4684 ?        Ss   16:28   0:00 /usr/bin/dbus-daemon --system --address=systemd: --nofork --nopidfile --systemd-activation --syslog-only
root         349  0.1  0.0  81816  3788 ?        Ssl  16:28   0:00 /usr/sbin/irqbalance --foreground
root         351  1.2  0.1  29224 17964 ?        Ss   16:28   0:00 /usr/bin/python3 /usr/bin/networkd-dispatcher --run-startup-triggers
syslog       352  0.2  0.0 224328  4788 ?        Ssl  16:28   0:00 /usr/sbin/rsyslogd -n -iNONE
root         355  7.7  0.0  16764  7656 ?        Ss   16:28   0:01 /lib/systemd/systemd-logind
root         362  0.0  0.0   8540  2928 ?        Ss   16:28   0:00 /usr/sbin/cron -f
daemon       367  0.0  0.0   3796  2188 ?        Ss   16:28   0:00 /usr/sbin/atd -f
root         385  0.0  0.0   5832  1852 tty1     Ss+  16:28   0:00 /sbin/agetty -o -p -- \u --noclear tty1 linux
root         431  0.0  0.0 232704  6536 ?        Ssl  16:28   0:00 /usr/lib/policykit-1/polkitd --no-debug
root         436  0.0  0.0  11368  1228 ?        Ss   16:28   0:00 nginx: master process /usr/sbin/nginx -c /etc/nginx/nginx.conf
nginx        437  0.0  0.0  12012  3840 ?        S    16:28   0:00  \_ nginx: worker process
root         452  0.9  0.1 108044 20912 ?        Ssl  16:28   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
root         477  0.3  0.1 641816 24976 ?        Ssl  16:28   0:00 /usr/bin/snap wait system seed.loaded
root         754 15.8  0.2 1235704 33868 ?       Ssl  16:28   0:01 /usr/lib/snapd/snapd
root        1112  0.0  0.0   2928  2276 ?        R    16:28   0:00  \_ /usr/lib/snapd/snap-confine --base core18 snap.lxd.hook.install /usr/lib/snapd/snap-exec --hook=install lxd
root        1125  0.0  0.0   2928   196 ?        S    16:28   0:00      \_ /usr/lib/snapd/snap-confine --base core18 snap.lxd.hook.install /usr/lib/snapd/snap-exec --hook=install lxd
```

## LXD を動かす

`snap list` を実行してみると lxd は既にインストール済みでした。

```console
$ snap list
Name    Version   Rev    Tracking         Publisher   Notes
core18  20200311  1705   latest/stable    canonical✓  base
lxd     4.0.1     14804  latest/stable/…  canonical✓  -
snapd   2.44.3    7264   latest/stable    canonical✓  snapd
```

あとはいつもの lxd の手順で OK です。

まず自分のユーザーを lxd グループに追加します。

```console
sudo usermod -a -G lxd $USER
```

実行後端末を開きなおします。

`lxd init` を実行して LXD の初期セットアップを行います。
いくつかプロンプトが出力されるので、お好みで選択します。

ストレージバックエンドがデフォルトで btrfs になってるんですね。
今回は試しにそれにしてサイズは 100 GB に増やしました。

[WSL2のUbuntuとDocker Desktop for Windowsを試してみた · hnakamur's blog](/blog/2020/05/28/setup-wsl2-ubuntu-and-docker-desktop-for-windows/) に書きましたが、 WSL2 は現状は IPv6 は使えないので IPv6 address のところは none と答えて無効にしておきます。

```console
$ lxd init
2020/05/30 16:48:35 usbid: failed to load: open /usr/share/misc/usb.ids: no such file or directory
Would you like to use LXD clustering? (yes/no) [default=no]:
Do you want to configure a new storage pool? (yes/no) [default=yes]:
Name of the new storage pool [default=default]:
Name of the storage backend to use (ceph, btrfs, dir, lvm) [default=btrfs]:
Create a new BTRFS pool? (yes/no) [default=yes]:
Would you like to use an existing block device? (yes/no) [default=no]:
Size in GB of the new loop device (1GB minimum) [default=50GB]: 100GB
Would you like to connect to a MAAS server? (yes/no) [default=no]:
Would you like to create a new local network bridge? (yes/no) [default=yes]:
What should the new bridge be called? [default=lxdbr0]:
What IPv4 address should be used? (CIDR subnet notation, “auto” or “none”) [default=auto]:
What IPv6 address should be used? (CIDR subnet notation, “auto” or “none”) [default=auto]: none
Would you like LXD to be available over the network? (yes/no) [default=no]:
Would you like stale cached images to be updated automatically? (yes/no) [default=yes]
Would you like a YAML "lxd init" preseed to be printed? (yes/no) [default=no]: yes
config: {}
networks:
- config:
    ipv4.address: auto
    ipv6.address: none
  description: ""
  name: lxdbr0
  type: ""
storage_pools:
- config:
    size: 100GB
  description: ""
  name: default
  driver: btrfs
profiles:
- config: {}
  description: ""
  devices:
    eth0:
      name: eth0
      network: lxdbr0
      type: nic
    root:
      path: /
      pool: default
      type: disk
  name: default
cluster: null
```

以下のコマンドで Ubuntu 20.04 LTS のコンテナーを作成し起動します。
最後の focal はコンテナー名なのでお好みで変えてください。

```console
$ lxc launch ubuntu:20.04 focal
Creating focal
Starting focal
```

作成したコンテナー内で bash を起動してみます。

```console
$ lxc exec focal bash
root@focal:~#
```

コンテナー内からネットワークも普通に使えます。

```console
root@focal:~# ping -c 1 www.ubuntu.com
PING www.ubuntu.com (91.189.88.181) 56(84) bytes of data.
64 bytes from davybones.canonical.com (91.189.88.181): icmp_seq=1 ttl=49 time=225 ms

--- www.ubuntu.com ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 225.115/225.115/225.115/0.000 ms
```

`exit` でコンテナーから抜けます。

```console
root@focal:~# exit
exit
$
```

## 未解決の課題: `/proc/sys/fs/binfmt_misc` の参照でエラー → 解決 （2020-06-01 追記）

上記の手順で systemd を動かすと `/proc/sys/fs/binfmt_misc` を参照しようとすると以下のようなエラーになります。

```console
$ ls -l /proc/sys/fs/binfmt_misc
ls: cannot open directory '/proc/sys/fs/binfmt_misc': Too many levels of symbolic links
```

原因は分からないので、とりあえずイシューを立ててみました。
[Too many levels of symbolic links when running ls -l /proc/sys/fs/binfmt_misc · Issue #15 · DamionGans/ubuntu-wsl2-systemd-script](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/issues/15)

[Add binfmt_misc override by diddledan · Pull Request #17 · DamionGans/ubuntu-wsl2-systemd-script](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/pull/17/files) で修正されました。

古いバージョンを消して再起動した後、このバージョンを実行して再起動すると、以下のように参照できていました。

```console
$ ls -l /proc/sys/fs/binfmt_misc
total 0
-rw-r--r-- 1 root root 0 Jun  1 01:38 WSLInterop
--w------- 1 root root 0 Jun  1 01:38 register
-rw-r--r-- 1 root root 0 Jun  1 01:38 status
$ cat /proc/sys/fs/binfmt_misc/WSLInterop
enabled
interpreter /tools/init
flags: F
offset 0
magic 4d5a
```

## systemd を起動しないように戻す場合の手順 （2020-06-01 更新）

今回利用したスクリプトの
[ubuntu-wsl2-systemd-script.sh#L27](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/blob/5a5dd97114c81ee82d24353e3f9d9f2f1782d1a5/ubuntu-wsl2-systemd-script.sh#L27) で `/etc/bash.bashrc` の 3,4 行目に以下の内容を追加していますので、これをコメントアウトか削除すれば、次回の起動では systemd を実行しないようになります。

```
# Start or enter a PID namespace in WSL2
source /usr/sbin/start-systemd-namespace
```

[Add binfmt_misc override by diddledan · Pull Request #17 · DamionGans/ubuntu-wsl2-systemd-script](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/pull/17/files) で 2 重インストールしないようにチェックが厳しくなったので、綺麗に消す必要があります。

ということで以下のようなコマンドを実行して削除します。

```console
sudo sed -i -e '/^# Start or enter a PID namespace in WSL2$/,/^$/d' /etc/bash.bashrc
sudo rm /usr/sbin/{start,enter}-systemd-namespace
```

削除後 WSL2 の Ubuntu を終了します。 `wsl.exe -t` の後のディストリビューション名は環境に応じて適宜変更。

```console
wsl.exe -t ubuntu-20.04
```

これで端末を開きなおして `ps auxwwf` を実行すると PID 1 は `/init` に戻り `ls -l /proc/sys/fs/binfmt_misc` や `cat /proc/sys/fs/binfmt_misc/WSLInterop` も正常に実行されます。

## おわりに

[Running Snaps on WSL2 (Insiders only for now) - snapd - snapcraft.io](https://forum.snapcraft.io/t/running-snaps-on-wsl2-insiders-only-for-now/13033/23) の冒頭の投稿には "Optional: Strict confinement support" というセクションがあります。

オプションでカスタムカーネルを使うことにより厳格な confinement がサポートできるそうです。
が、カーネルの脆弱性の度にビルドするのも大変なので今回はスキップしました。
いつか気が向いたら試してみてもいいかも。

また [izznatsir さんのコメント](https://forum.snapcraft.io/t/running-snaps-on-wsl2-insiders-only-for-now/13033/25) によるとこの手順に従って systemd を動かすと Docker Desktop for Windows 無しで WSL2 の Ubuntu 内だけで docker を動かせたそうです（カスタムカーネルを使う手順を試されたそうですが、カスタムカーネルなしでも動くかも）とのこと。
こちらも別途試してみたいところです。

それと [DamionGans/ubuntu-wsl2-systemd-script: Script to enable systemd support on current Ubuntu WSL2 images from the Windows store](https://github.com/DamionGans/ubuntu-wsl2-systemd-script) の [enter-systemd-namespace](https://github.com/DamionGans/ubuntu-wsl2-systemd-script/blob/master/enter-systemd-namespace) のスクリプト内では `unshare` コマンドや `nsenter` コマンドを実行していて興味深いので、今後もう少し時間かけて理解したいところです。


## Docker Desktop for Windows をアンインストールして docker を動かしてみた （2020-05-31 追記、 2020-06-05 更新）

2020-06-05 追記: 2020-05-31 の時点では Ubuntu の標準パッケージの docker.io を入れる手順を書いていましたが、その後 [Install Docker Engine on Ubuntu | Docker Documentation](https://docs.docker.com/engine/install/ubuntu/) を確認すると Docker の apt レポジトリが Ubuntu 20.04 LTS も対応になっていたので、そちらの手順に書き換えました。

カスタムカーネル無しで動きました。

手順は以下の通りです。

1. Docker Desktop for Windows をアンインストールして、Windows を再起動。
2. WSL2 を起動し `~/.docker/config.json` を削除。
3. WSL2 の Ubuntu で docker 公式レポジトリを追加して docker-ce と docker-compose をインストール。

[Install using the repository](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository) の手順にほぼ従います。

まず必要なソフトウェアを追加します。

```console
sudo apt update
sudo apt -y install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common
```

docker の GPG 鍵を追加します。

```console
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
```

上記で追加した鍵のフィンガープリントを確認します。

```console
$ sudo apt-key fingerprint 0EBFCD88
pub   rsa4096 2017-02-22 [SCEA]
      9DC8 5822 9FC7 DD38 854A  E2D8 8D81 803C 0EBF CD88
uid           [ unknown] Docker Release (CE deb) <docker@docker.com>
sub   rsa4096 2017-02-22 [S]
```

apt のレポジトリを追加します。
[Install using the repository](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository) の手順では `add-apt-repository` を使っていますが、これだと `/etc/apt/sources.list` が変更されます。
私は `/etc/apt/sources.list.d/` にファイルを追加するほうが好きなので、以下の手順にします。

```console
echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
```

以下のコマンドで docker-ce と関連パッケージをインストールします。

```console
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```

4. docker グループに自ユーザーを追加

```console
sudo usermod -a -G docker $USER
```

一旦端末を閉じて開きなおすか `newgrp docker` を実行すれば docker グループにも所属した状態になります。

`docker ps` が実行できるかを確認します。

```console
$ docker ps
CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
```

5. docker で hello-world コンテナーを実行

```console
docker run hello-world
```

6. WSL2 の Ubuntu を停止（-t の後のディストリビューション名は環境に応じて変更）

```console
wsl.exe -t ubuntu-20.04
```

7. WSL2 の端末を開きなおして docker サービスが動いているか確認すると動いていました。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ systemctl status docker
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Fri 2020-06-05 17:55:28 JST; 4s ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 279 (dockerd)
      Tasks: 12
     Memory: 121.9M
     CGroup: /system.slice/docker.service
             └─279 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock

Jun 05 17:55:27 sunshine7 dockerd[279]: time="2020-06-05T17:55:27.908189300+09:00" level=warning msg="Your kernel does not support cgroup blkio throttle.write_bp>
Jun 05 17:55:27 sunshine7 dockerd[279]: time="2020-06-05T17:55:27.908200000+09:00" level=warning msg="Your kernel does not support cgroup blkio throttle.read_iop>
Jun 05 17:55:27 sunshine7 dockerd[279]: time="2020-06-05T17:55:27.908210100+09:00" level=warning msg="Your kernel does not support cgroup blkio throttle.write_io>
Jun 05 17:55:27 sunshine7 dockerd[279]: time="2020-06-05T17:55:27.908412800+09:00" level=info msg="Loading containers: start."
Jun 05 17:55:28 sunshine7 dockerd[279]: time="2020-06-05T17:55:28.078619400+09:00" level=info msg="Default bridge (docker0) is assigned with an IP address 172.17>
Jun 05 17:55:28 sunshine7 dockerd[279]: time="2020-06-05T17:55:28.147477000+09:00" level=info msg="Loading containers: done."
Jun 05 17:55:28 sunshine7 dockerd[279]: time="2020-06-05T17:55:28.248031800+09:00" level=info msg="Docker daemon" commit=42e35e61f3 graphdriver(s)=overlay2 versi>
Jun 05 17:55:28 sunshine7 dockerd[279]: time="2020-06-05T17:55:28.249390500+09:00" level=info msg="Daemon has completed initialization"
Jun 05 17:55:28 sunshine7 systemd[1]: Started Docker Application Container Engine.
Jun 05 17:55:28 sunshine7 dockerd[279]: time="2020-06-05T17:55:28.272997200+09:00" level=info msg="API listen on /run/docker.sock"
```

Docker Compose のインストールは [Install Docker Compose | Docker Documentation](https://docs.docker.com/compose/install/) を参考に以下のようにしました。

```console
release="$(basename $(curl -s -o /dev/null -w '%{redirect_url}' https://github.com/docker/compose/releases/latest))"
sudo curl -L "https://github.com/docker/compose/releases/download/$release/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```
