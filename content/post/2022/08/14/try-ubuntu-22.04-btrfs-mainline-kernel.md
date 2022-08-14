---
title: "Ubuntu 22.04でbtrfsとmainline kernelを試してみた"
date: 2022-08-14T12:29:56+09:00
---

## はじめに

[Arch Linux を試してみた · hnakamur's blog](/blog/2022/08/14/try-archlinux/) でとりあえずセットアップできることを確認したので、再度 Ubuntu をセットアップすることにしました。

## インストーラをUSBメモリに書き込み

[Ubuntu 22.04のセットアップメモ · hnakamur's blog](/blog/2022/04/22/setup-ubuntu-22.04/) と同様に今回も [Rufus - Create bootable USB drives the easy way](https://rufus.ie/en/) のポータブル版 (バージョン 3.20p) を使いました。

[Download Ubuntu Desktop | Download | Ubuntu](https://ubuntu.com/download/desktop) から ubuntu-22.04.1-desktop-amd64.iso をダウンロードしました。sha256 のチェックサムは [Ubuntu 22.04.1 LTS (Jammy Jellyfish)](http://releases.ubuntu.com/jammy/) の `SHA256SUM` にありました。

## ルートパーティションを Btrfs にした

"Installation type" のダイアログで "Something else" のラジオボタンを押し、ルートパーティションを btrfs にして "Format the partition" のチェックをオンにした。

| パーティション | サイズ | パーティションタイプ |
| -------------- | ------ | ---------------------|
| /dev/nvme0n1p1 | 512M   | EFI                  |
| /dev/nvme0n1p2 | EFIとスワップを引いた残り   | btrfs |
| /dev/nvme0n1p3 | 8GB   | Linux swap |

## mainline kernel を試してみた

インストール完了して再起動した後 [You Can Now Install Linux Kernel 5.19 on Ubuntu and Ubuntu-Based Distributions - 9to5Linux](https://9to5linux.com/you-can-now-install-linux-kernel-5-19-on-ubuntu-and-ubuntu-based-distributions) を参考に mainline kernel の 5.19.1 を入れてみました。

```bash
sudo add-apt-repository ppa:cappelikan/ppa
sudo apt update
sudo apt -y install mainline
```

1. Windows キーを押して Mainline と入力して Ubuntu Mainline を起動
2. Ubuntu Mainline Kernel Installer の画面で Refresh ボタンを押す
3. カーネルのバージョンの一覧が表示されたら 5.19.1 を選んで Install ボタンを押す
