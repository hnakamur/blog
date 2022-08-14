---
title: "Arch Linux を試してみた"
date: 2022-08-14T02:03:26+09:00
---

## はじめに

Ubuntu を入れていた 2台の ThinkCentre のうち1台に mainline のカーネルを入れてみたら、再起動後 zfs のモジュールが読み込めくてハマったので、この機会に前から気になってた Arch Linux を試してみました。

[Arch Linux - Wikipedia](https://ja.wikipedia.org/wiki/Arch_Linux) を見たら GUI インストーラーでお手軽そうと思っていた Antergos はプロジェクト終了とのことでした。

検索すると [Arch Linux をおしゃれに最速インストール - おしゃれな気分でプログラミング](http://neko-mac.blogspot.com/2021/05/arch-linux.html) という良い記事が見つかったのでこちらを参考にインストールしました。

## インストールメディアは rufs で USB メモリに作成

Linux で dd も試したのですが、うまく起動しませんでした。

rufs では Syslinux をダウンロードしてインストールするか聞かれたのでそうしました([RufusでLinuxのインストールメディアを作る。 | PC-FREEDOM](https://pc-freedom.net/software/how-to-use-rufus/) の「Syslinuxとは」の項参照)。

## USB メモリからブートして SSD にインストール

今回のインストールの構成は以下の通りです。

* US キーボード
* 有線 LAN
* DHCP
* デュアルブート無し

USB メモリからブートしたライブシステムで DHCP が動いてインターネットに接続できる状態でした。

### NTP を有効にします

```bash
timedatectl set-ntp true
```

### パーティション作成

インストール先のディスク名を以下のコマンドで確認します。

```bash
lsblk
```

インストール先のディスクのパーティションを作成します。cgdisk か fdisk コマンドを使うとありましたが、 cgdisk は使ったことが無かったのでこちらを使ってみました。 TUI で操作できて簡単で良かったです。

スワップパーティションのサイズは [How Much Swap Should You Use in Linux? - It's FOSS](https://itsfoss.com/swap-size/) と [SwapFaq - Community Help Wiki](https://help.ubuntu.com/community/SwapFaq) の RAM が 1GB より大きい場合は最低で RAM のサイズの平方根というお勧めに従いました。

具体的には RAM が 64 GB なのでスワップは 8GB にしました。

| パーティション | サイズ | パーティションタイプ |
| -------------- | ------ | ---------------------|
| /dev/nvme0n1p1 | 512M   | EFI                  |
| /dev/nvme0n1p2 | EFIとスワップを引いた残り   | Linux filesystem |
| /dev/nvme0n1p3 | 8GB   | Linux swap |

フォーマットする。

```bash
mkfs.fat -F32 /dev/nvme0n1p1
```

```bash
mkfs.ext4 /dev/nvme0n1p2
```

```bash
mkswap /dev/nvme0n1p3
```

### パッケージをインストール

ルートパーティションをマウント。

```bash
mount /dev/nvme0n1p2 /mnt
```

`/mnt/boot` を作成して EFI パーティションをマウント。

```bash
mkdir /mnt/boot
mount /dev/nvme0n1p1 /mnt/boot
```

swapを有効にします。

```bash
mkswap /dev/nvme0n1p3
```

パッケージをインストール。

```bash
pacstrap /mnt base linux linux-firmware man-db vim
```

### chroot してさらにセットアップを実行

fstab 設定。

```bash
genfstab -U /mnt >> /mnt/etc/fstab
```

chroot を実行。

```bash
arch-chroot /mnt
```

タイムゾーン設定。

```bash
ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
```

システムの時刻をBIOSの時刻にコピー。タイムゾーンはUTCになる。

```bash
hwclock --systohc
```

`vim /etc/locale.gen` で `en_US.UTF-8 UTF-8` と `ja_JP.UTF-8 UTF-8` の行をアンコメントして以下のコマンドでロケールを生成。

```bash
locale-gen
```

`/etc/locale.conf` を以下のように編集。

```
LANG=en_US.UTF-8
```

コンソールのキーボード設定でCapsLockとCtrl入れ替え。

```bash
mkdir -p /usr/local/share/kbd/keymaps
gzip -cd /usr/share/kbd/keymaps/i386/qwerty/us.map.gz > /usr/local/share/kbd/keymaps/my_custom_us.map
```

`vim /usr/local/share/kbd/keymaps/my_custom_us.map` で編集して、以下のように入れ替え。

```
…(略）…
keycode  29 = Caps_Lock
…(略）…
keycode  58 = Control
…(略）…
```

以下のコマンドで読み込んで有効にします。

```bash
loadkeys /usr/local/share/kbd/keymaps/my_custom_us.map
```

キーを押してみて期待通りになっていたら、 `/etc/vconsole.conf` を以下のように編集。

```
KEYMAP=/usr/local/share/kbd/keymaps/my_custom_us.map
```

`/etc/hostname` を編集してお好みのホスト名を設定。ここでは thinkcentre とします。

`/etc/hosts` を以下のように編集。

```
127.0.0.1    localhost
::1          localhost
127.0.1.1    thinkcentre.localdomain thinkcentre
```

`passwd` を実行して root ユーザのパスワードを設定。

ブートローダに GRUB を使う設定。

```bash
pacman -S grub efibootmgr dosfstools os-prober mtools
```

```bash
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB_UEFI
```

初回と今後のgrubの設定変更時に以下のコマンドを実行。

```bash
grub-mkconfig -o /boot/grub/grub.cfg
```

マイクロプロセッサ用コードをインストール。CPUに応じて `intel-ucode` か `amd-ucode` を入れます。

```bash
pacman -S amd-ucode
```

```bash
grub-mkconfig -o /boot/grub/grub.cfg
```

### ネットワーク設定

参考にした記事はノートPCで無線LANなので NetworkManager を使っていますが、私は有線LANなので `systemd-networkd` にしました。

[ネットワーク設定 - ArchWiki](https://wiki.archlinux.jp/index.php/%E3%83%8D%E3%83%83%E3%83%88%E3%83%AF%E3%83%BC%E3%82%AF%E8%A8%AD%E5%AE%9A) の表を見ると Archiso の base に含まれていて DHCP クライアントも内蔵しているとのこと。

DNS はとりあえず [systemd-resolved - ArchWiki](https://wiki.archlinux.jp/index.php/Systemd-resolved) を使うことにしました。「systemd-resolved はデフォルトでインストールされる systemd パッケージの一部です。」とあるのでそのままで使えます。

```bash
systemctl enable --now systemd-networkd
systemctl enable --now systemd-resolved
```

### chroot を抜けて再起動

```bash
exit
```

```bash
reboot
```

## インストールしたディスクから起動後、さらにセットアップを進める

### ネットワークの動作確認と設定

インストールしたディスクから起動後、root でログインします。

`ping 8.8.8.8` インターネットに接続できることを確認。
`ping google.com` で名前解決が出来ることを確認。

後に gpg でリモートのキーサーバからキーをインストールするときに `gpg: keyserver receive failed: Server indicated a failure` というエラーになったのですが `/etc/resolv.conf` が空だったのが原因でした (https://unix.stackexchange.com/a/630182/135274 に書かれていました)。

[systemd-resolved - ArchWiki](https://wiki.archlinux.jp/index.php/Systemd-resolved) にも書かれているように以下のコマンドで解消しました。

```bash
ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
```

### 一般ユーザの作成と sudo の設定
ユーザ名はここでは hnakamur とします。

```bash
useradd -m -G wheel hnakamur
```

パスワードを設定。

```bash
passwd hnakamur
```

sudo パッケージをインストール。

```bash
pacman -S sudo
```

visudo を起動。

```bash
EDITOR=vim visudo
```

コメントアウトされている以下の行をアンコメントして有効にして保存して終了。

```
%wheel ALL=(ALL) ALL
```

root ユーザをログアウトして、作成したユーザでログインします。

### tmux をインストール

```bash
sudo pacman -S tmux
```

`https://github.com/hnakamur/dotfiles` の `.tmux.conf` をホームディレクトリにコピーしてキーバインドを変更。

### sshd のインストールと起動

```bash
sudo pacman -S openssh
```

`sudo vim /etc/ssh/sshd_config` で以下のように編集。

```
#PasswordAuthentication yes
PasswordAuthentication no # この行を追加
```

```
#UsePAM yes
UsePAM no # この行を追加
```

X11Forwarding はデフォルト値で no となっていたので変更無し。

```
#X11Forwarding no
```

sshd を起動し、自動起動を有効にします。

```bash
sudo systemctl enable --now sshd
```

### keepassxc-cli も試してみた

```bash
sudo pacman -S keepassxc
```

で `keepassxc-cli` という CLI もインストールされるので、初めて使ってみました。

keepassxc のデータベースファイルの入った USB 接続のハードディスクを接続してファイルをコピーしました。

`sudo dmesg` でデバイスファイル名を確認し、 `/dev/sda` だったので以下のようにしました。

```bash
sudo mount /dev/sda /mnt
cp /mnt/path/to/my_database.db ~/
sudo umount /mnt
```

[keepassxc-cli(1) — Arch manual pages](https://man.archlinux.org/man/keepassxc-cli.1.en) を参考に attachment-export サブコマンドを使って添付ファイルとして含めていた ssh の公開鍵を `~/.ssh/authorized_keys` ファイルに保存します。

```bash
mkdir -m 700 ~/.ssh
keepassxc-cli attachment-export my_database.db "DB内のエントリ名" 添付ファイル名 保存先ファイル名
```

DB内のエントリ名は search サブコマンドで調べられます。

open サブコマンドを使ってDBファイルを開いてインタラクティブにコマンドを実行することもできます。 `DBファイルのベース名>` のようなプリンプトでサブコマンドをDBファイル名無しで実行します。使い終わったら close サブコマンドでDBを閉じます。

インタラクティブにコマンドを実行する際、空白を含んだエントリ名を指定する際はシングルクォートで囲むと応答なしでプロンプトに戻って何も起きませんでした。ダブルクォートで囲むと正常に動作しました。

clip サブコマンドは xclip コマンドを試したが失敗したという主旨の出力が出ました。 `sudo pacman -S xclip` でインストールしましたが、 X11 をインストールしていないコンソールでは使えないらしくうまく動きませんでした。

代わりに show コマンドを `-s -a password` オプションを指定して実行することで指定したエントリのパスワードがクリアテキストで表示されたのでこれを tmux でコピー＆ペーストして利用しました。この方法は人に見られてしまう環境だとまずいですが、私の自宅では問題ありません。

### yay のインストール
[Jguer/yay: Yet another Yogurt - An AUR Helper written in Go](https://github.com/Jguer/yay) をインストールします。

```bash
sudo pacman -S --needed git base-devel
```

```bash
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
```

## Linux カーネル 5.19 を入れてみた

標準のカーネルのバージョンを `uname -r` で確認すると `5.18.16-arch1-1` でした。

[カーネル - ArchWiki](https://wiki.archlinux.jp/index.php/%E3%82%AB%E3%83%BC%E3%83%8D%E3%83%AB) を見て [AUR (en) - linux-mainline](https://aur.archlinux.org/packages/linux-mainline) パッケージを入れてみました。

```bash
yay -S linux-mainline
```

いくつかプロンプトが出て質問されるので適宜答えます。

途中で gpg のキーをリモートから取得してインストールするところで、前述の `gpg: keyserver receive failed: Server indicated a failure` のエラーが出ましたが、上記の手順で解消しました。

ビルド済みのカーネルをダウンロードしてインストールされるのではなく、ローカルでビルドされていました。

ビルドがいつまでも終わらないので Ctrl-C で一旦中止しました。
[makepkg - ArchWiki](https://wiki.archlinux.jp/index.php/Makepkg) を見て `MAKEFLAGS=-j8` をつけて以下のコマンドを実行してみました。

```bash
MAKEFLAGS=-j8 yay -S linux-mainline
```

すると ABAF11C65A2970B130ABE3C479BE3E4300411886 の gpg 鍵のインポートで今度は `gpg: keyserver receive failed: No data` というエラーになりました。

`gpg --recv 0xABAF11C65A2970B130ABE3C479BE3E4300411886` でも同じエラーになりました。

[\[SOLVED\] Cannot import Torvalds's GPG key / Newbie Corner / Arch Linux Forums](https://bbs.archlinux.org/viewtopic.php?id=249943) を見て以下のコマンドを実行すると `No data` ではなく `no user ID` になりました。

```bash
gpg --keyserver keys.openpgp.org --recv 0xABAF11C65A2970B130ABE3C479BE3E4300411886
```

以下のような出力が出ていました。

```bash
$ gpg --keyserver keys.openpgp.org --recv 0xABAF11C65A2970B130ABE3C479BE3E4300411886
gpg: data source: http://keys.openpgp.org:11371
gpg: armor header: ABAF 11C6 5A29 70B1 30AB  E3C4 79BE 3E43 0041 1886
gpg: pub  rsa2048/79BE3E4300411886 2011-09-20
gpg: key 79BE3E4300411886: no user ID
gpg: Total number processed: 1
```

[auto-key-retrieve](https://wiki.archlinux.jp/index.php/GnuPG) を参考に `~/.gnupg/dirmngr.conf` を以下の内容で作成してみました。

```
keyserver hkps://keys.openpgp.org
```

`ps auxwwf | grep dirmngr` で `/usr/bin/dirmngr --supervisord` の PID を調べて `kill -HUP そのPID` で設定ファイルを再読み込みさせて、再度試しました。が、以下のように `problem importing keys` というエラーになりました。

```
:: PGP keys need importing:
 -> ABAF11C65A2970B130ABE3C479BE3E4300411886, required by: linux-mainline
==> Import? [Y/n] y # y と入力
:: Importing keys with gpg...
gpg: key 79BE3E4300411886: no user ID
gpg: Total number processed: 1
 -> problem importing keys
```

[kernel - gpg2 locate keys wont work (immediately returns) - Ask Ubuntu](https://askubuntu.com/questions/1007287/gpg2-locate-keys-wont-work-immediately-returns/1027703#1027703) を参考に以下のコマンドを実行するとインポートできました。

```bash
gpg2 --auto-key-locate cert,pka,dane,wkd,keyserver --locate-keys torvalds@kernel.org
```

```bash
$ gpg2 --auto-key-locate cert,pka,dane,wkd,keyserver --locate-keys torvalds@kernel.org
gpg: error retrieving 'torvalds@kernel.org' via DNS CERT: No name
gpg: error retrieving 'torvalds@kernel.org' via PKA: No name
gpg: error retrieving 'torvalds@kernel.org' via DANE: No name
gpg: key 79BE3E4300411886: public key "Linus Torvalds <torvalds@kernel.org>" imported
gpg: Total number processed: 1
gpg:               imported: 1
pub   rsa2048 2011-09-20 [SC]
      ABAF11C65A2970B130ABE3C479BE3E4300411886
uid:          [ unknown ] Linus Torvalds <torvalds@kernel.org>
sub   rsa2048 2011-09-20 [E]
```

これで `gpg --list-keys` で鍵が一覧に出てきました。
再度 `MAKEFLAGS=-j8 yay -S linux-mainline` を実行すると今度は gpg 鍵のインポートのプロンプトは出ずに先に進みました。

その後時間がかかるので目を離していたら最後に sudo のプロンプトが出てタイムアウトになっていました。

```
==> Finished making: linux-mainline 5.19-1 (Sun 14 Aug 2022 06:24:16 AM JST)
==> Cleaning up...
[sudo] password for hnakamur:
sudo: timed out reading password
sudo: a password is required
 -> exit status 1
```

再度 `MAKEFLAGS=-j8 yay -S linux-mainline` を実行して `Packages to cleanBuild?` に [N]one の N で答えたら、途中で以下のようなメッセージが出力されてビルドはスキップされて進みました。

```
==> Sources are ready.
 -> linux-mainline-5.19-1 already made -- skipping build
[sudo] password for hnakmaur: ここでパスワードを入力
loading packages...
resolving dependencies...
looking for conflicing packages...

Packages (1) linux-mainline-5.19-1

Total Installed Size:  177.07 MiB

:: Proceed with installation? [Y/n] ここでEnterキーを押す

(1/1) checking keys in keyring                                                                                                                   [########################################################################################] 100%
(1/1) checking package integrity                                                                                                                 [########################################################################################] 100%
(1/1) loading package files                                                                                                                      [########################################################################################] 100%
(1/1) checking for file conflicts                                                                                                                [########################################################################################] 100%
(1/1) checking available disk space                                                                                                              [########################################################################################] 100%
:: Processing package changes...
(1/1) installing linux-mainline                                                                                                                  [########################################################################################] 100%
Optional dependencies for linux-mainline
    wireless-regdb: to set the correct wireless channels of your country
    linux-firmware: firmware images needed for some devices [installed]
:: Running post-transaction hooks...
(1/3) Arming ConditionNeedsUpdate...
(2/3) Updating module dependencies...
(3/3) Updating linux initcpios...
==> Building image from preset: /etc/mkinitcpio.d/linux-mainline.preset: 'default'
  -> -k /boot/vmlinuz-linux-mainline -c /etc/mkinitcpio.conf -g /boot/initramfs-linux-mainline.img
==> Starting build: 5.19.0-1-mainline
  -> Running build hook: [base]
  -> Running build hook: [udev]
  -> Running build hook: [autodetect]
  -> Running build hook: [modconf]
  -> Running build hook: [block]
==> WARNING: Possibly missing firmware for module: xhci_pci
  -> Running build hook: [filesystems]
  -> Running build hook: [keyboard]
  -> Running build hook: [fsck]
==> Generating module dependencies
==> Creating zstd-compressed initcpio image: /boot/initramfs-linux-mainline.img
==> Image generation successful
==> Building image from preset: /etc/mkinitcpio.d/linux-mainline.preset: 'fallback'
  -> -k /boot/vmlinuz-linux-mainline -c /etc/mkinitcpio.conf -g /boot/initramfs-linux-mainline-fallback.img -S autodetect
==> Starting build: 5.19.0-1-mainline
  -> Running build hook: [base]
  -> Running build hook: [udev]
  -> Running build hook: [modconf]
  -> Running build hook: [block]
==> WARNING: Possibly missing firmware for module: wd719x
==> WARNING: Possibly missing firmware for module: bfa
==> WARNING: Possibly missing firmware for module: qla1280
==> WARNING: Possibly missing firmware for module: qed
==> WARNING: Possibly missing firmware for module: qla2xxx
==> WARNING: Possibly missing firmware for module: aic94xx
==> WARNING: Possibly missing firmware for module: xhci_pci
  -> Running build hook: [filesystems]
  -> Running build hook: [keyboard]
  -> Running build hook: [fsck]
==> Generating module dependencies
==> Creating zstd-compressed initcpio image: /boot/initramfs-linux-mainline-fallback.img
==> Image generation successful
```

WARNING がいくつか出ているのが気になりますが、イメージの生成は試行したと最後に出ていました。

ここで grub の設定のバックアップを取ってから更新を実行します。

```bash
sudo cp /boot/grub/grub.cfg{,.bak}
sudo grub-mkconfig -o /boot/grub/grub.cfg
```

`diff -u /boot/grub/grub.cfg{.bak,}` で差分を見て linux-mainline のメニューが追加されていることを確認しました。

`sudo reboot` で再起動してみると起動できて `Arch Linux 5.19.0-1-mainline (tty1)` と表示されていました。

## GNOME をインストール

[GNOME - ArchWiki](https://wiki.archlinux.jp/index.php/GNOME) を読んで以下のコマンドでインストール。

```bash
sudo pacman -S gnome
```

いくつか質問されますが全てデフォルトで回答。

[ディスプレイマネージャ - ArchWiki](https://wiki.archlinux.jp/index.php/%E3%83%87%E3%82%A3%E3%82%B9%E3%83%97%E3%83%AC%E3%82%A4%E3%83%9E%E3%83%8D%E3%83%BC%E3%82%B8%E3%83%A3)

```bash
sudo pacman -S gdm
```

```bash
sudo systemctl enable --now gdm
```

## Wayland で左CtrlとCapsLock入れ替え

最初 Xorg が動いているのかなと思い [Xorg でのキーボード設定 - ArchWiki](https://wiki.archlinux.jp/index.php/Xorg_%E3%81%A7%E3%81%AE%E3%82%AD%E3%83%BC%E3%83%9C%E3%83%BC%E3%83%89%E8%A8%AD%E5%AE%9A) と [X KeyBoard extension - ArchWiki](https://wiki.archlinux.jp/index.php/X_KeyBoard_extension) を読んで以下のコマンドを実行しました。

```
setxkbmap -model pc101 -layout us -variant qwerty -option ctrl:swapcaps
```

が、 `WARNING: Running setxkbmap against an Wayland server` という警告が出て Xorg ではなく Wayland が動いていることを知りました。

[Wayland - ArchWiki](https://wiki.archlinux.jp/index.php/Wayland#.E3.82.AD.E3.83.BC.E3.83.9C.E3.83.BC.E3.83.89.E3.82.84.E3.83.9E.E3.82.A6.E3.82.B9.E3.82.AD.E3.83.BC.E3.81.AE.E3.83.AA.E3.83.9E.E3.83.83.E3.83.97) と [入力リマップユーティリティ - ArchWiki](https://wiki.archlinux.jp/index.php/%E5%85%A5%E5%8A%9B%E3%83%AA%E3%83%9E%E3%83%83%E3%83%97%E3%83%A6%E3%83%BC%E3%83%86%E3%82%A3%E3%83%AA%E3%83%86%E3%82%A3) を見て [wez/evremap: A keyboard input remapper for Linux/Wayland systems, written by @wez](https://github.com/wez/evremap) をインストール。

```bash
yay -S evremap
```

パッケージ内のファイル一覧を確認。

```bash
$ pacman -Ql evremap
evremap /usr/
evremap /usr/bin/
evremap /usr/bin/evremap
evremap /usr/lib/
evremap /usr/lib/systemd/
evremap /usr/lib/systemd/system/
evremap /usr/lib/systemd/system/evremap.service
```

サービス定義ファイルの内容を確認。

```bash
$ cat /usr/lib/systemd/system/evremap.service
[Service]
WorkingDirectory=/
# For reasons I don't care to troubleshoot, Fedora 31 won't let me start this
# unless I use `bash -c` around it.  Putting the command line in directly
# yields a 203 permission denied error with no logs about what it didn't like.
ExecStart=bash -c "/home/wez/github/evremap/target/release/evremap remap /home/wez/github/evremap/pixelbookgo.toml"
Restart=always

[Install]
WantedBy=gdm.service
```

evremap 用の設定ファイルを作成。

```bash
cat <<'EOF' | sudo tee /etc/evremap.toml > /dev/null
# The name of the device to remap.
# Run `sudo evremap list-devices` to see the devices available
# on your system.
device_name = "Lenovo ThinkPad Compact USB Keyboard with TrackPoint"

# If you have multiple devices with the same name, you can optionally
# specify the `phys` value that is printed by the `list-devices` subcommand
# phys = "usb-0000:07:00.3-2.1.1/input0"

# Swap CapsLock and left Control.
[[remap]]
input = ["KEY_LEFTCTRL"]
output = ["KEY_CAPSLOCK"]

[[remap]]
input = ["KEY_CAPSLOCK"]
output = ["KEY_LEFTCTRL"]
EOF
```

サービス定義ファイルを作成。

```bash
cat <<'EOF' | sudo tee /etc/systemd/system/evremap.service > /dev/null
[Service]
WorkingDirectory=/
ExecStart=/usr/bin/evremap remap /etc/evremap.toml
Restart=always

[Install]
WantedBy=gdm.service
EOF
```

サービスを起動し自動起動を有効にしました。これで期待通り左CtrlとCapsLockが入れ替わりました。

```bash
sudo systemctl enable --now evremap
```
