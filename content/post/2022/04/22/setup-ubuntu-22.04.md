---
title: "Ubuntu 22.04のセットアップメモ"
date: 2022-04-22T21:23:18+09:00
---

## ブート可能なUSBメモリ作成

### USBメモリをフォーマット

参考：[software recommendation - GUI tool for formating to exFAT - Ask Ubuntu](https://askubuntu.com/questions/750681/gui-tool-for-formating-to-exfat)

必要なパッケージをインストール。

```bash
sudo apt-get install exfat-utils exfat-fuse
```

1. サイズが8GB以上のUSBメモリをPCに挿す。
2. [Show Applications] を押して検索欄に [Disks] と入力して、Disksを起動。
3. 左の一覧で USBドライブを選択し、歯車アイコンを押して[Format Partition...]メニューを選択。
4. Volume Nameにはお好みの名前を入力（例: jammy）し、Eraseを有効にし Type は [Other] を選択し [Next]を押す。
5. Custom Formatの画面で exFAT を選択して [Next] を押す。
6. Confirm Details の画面で内容を確認の上 [Format] を押す。


### USBメモリにイメージファイルを書き込み

参考： [Installation/FromUSBStick - Community Help Wiki](https://help.ubuntu.com/community/Installation/FromUSBStick)

必要なパッケージをインストール。

```bash
sudo apt install usb-creator-gtk
```

[Ubuntu 22.04 LTS (Jammy Jellyfish)](https://releases.ubuntu.com/22.04/) から Desktop image をダウンロード。

サイズが4GB以上のUSBメモリを指して、[Show Applications]を押して[Startup Disk Creator]を実行し、ダウンロードしたイメージファイルを選択してUSBメモリに書き込み。
