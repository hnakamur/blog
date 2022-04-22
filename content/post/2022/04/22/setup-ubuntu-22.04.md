---
title: "Ubuntu 22.04のセットアップメモ"
date: 2022-04-22T21:23:18+09:00
---

## ブート可能なUSBメモリ作成

今回は [How to Install Ubuntu 22.04 LTS Desktop (Jammy Jellyfish)](https://phoenixnap.com/kb/ubuntu-22-04-lts) の "Option 2: Make a Bootable USB Drive on Windows" の手順を参考にしました。

1. [Ubuntu 22.04 LTS (Jammy Jellyfish)](https://releases.ubuntu.com/22.04/) から Desktop image をダウンロード。
2. サイズが4GB以上のUSBメモリをPCに挿す。
3. [Rufus - Create bootable USB drives the easy way](https://rufus.ie/en/) の Portable 版をダウンロードして実行。
4. 以下のように選択して[スタート]ボタンを押して書き込み。
    * [ブートの種類]の右のほうの[選択]ボタンを押して上でダウンロードしたイメージファイルを選択。
    * [パーティション構成]は[MBR]、[ターゲットシステム]は[BIOSまたはUEFI]のまま。
    * [ボリュームラベル]も自動入力される[Ubuntu 22.04 LTS amd64]のまま。
    * [ファイルシステム]は[FAT32]、[クラスターサイズ]は[4096バイト(規定)]。
        * これは容量4GBのUSBメモリの場合。容量がもっと大きい場合は異なる可能性あり。

約18分とかなり時間がかかりましたが、書き込み完了後、USBメモリからインストーラを起動して無事インストールできました。

## キーボードの Ctrl と CapsLock 入れ替え

```
sudo sed -i -e '/^XKBOPTIONS=/s/""/"ctrl:swapcaps"/' /etc/default/keyboard
```

## KeePassXC セットアップ

[KeePassXC Password Manager](https://keepassxc.org/)

```bash
mkdir ~/AppImage
cd !$
curl -LO https://github.com/keepassxreboot/keepassxc/releases/download/2.7.1/KeePassXC-2.7.1-x86_64.AppImage
chmod +x KeePassXC-2.7.1-x86_64.AppImage
```

[FUSE · AppImage/AppImageKit Wiki](https://github.com/AppImage/AppImageKit/wiki/FUSE) に沿って libfuse2 をセットアップ。

```bash
sudo apt install fuse libfuse2
sudo modprobe fuse
sudo groupadd fuse

user="$(whoami)"
sudo usermod -a -G fuse $user
```

Dock に KeePassXC を登録。

```bash
mkdir -p ~/.icons ~/.local/share/applications
(cd ~/.icons; curl -LO https://keepassxc.org/images/keepassxc-logo.svg)
```

```bash
cat > ~/.local/share/applications/keepassxc.desktop <<EOF
#!/usr/bin/env xdg-open
[Desktop Entry]
Version=2.7.1
Type=Application
Terminal=false
Exec=/home/hnakamur/AppImage/KeePassXC-2.7.1-x86_64.AppImage
Name=KeepassXC
Comment=Cross-Platform Password Manager
Icon=keepassxc-logo
EOF
```

