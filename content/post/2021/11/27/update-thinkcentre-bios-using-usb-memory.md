---
title: "USBメモリを使ってThinkCentreのBIOSをアップデート"
date: 2021-11-27T21:17:29+09:00
---
## はじめに

私物の ThinkPad P14s AMD Gen 2 は Windows で使っているので Lenovo Commercial Vantage で BIOS をアップデートしています。
ですが ThinkCentre M75q Tiny Gen2 のほうは Windows を消して Ubuntu Linux を入れているので別の方法でアップデートする必要があります。今回調べてアップデートしたのでメモです。

なお今回の方法は USB メモリが必要です。

## うまく行かなかった方法: BIOSのISOイメージをgenisoimageパッケージのgeteltoritoで変換

### 参考にしたページ

* [How to update your Thinkpad's bios with Linux or OpenBSD](https://blog.raveland.tech/post/thinkpad_update_bios/)
* [How to update Lenovo BIOS from Linux without using Windows - nixCraft](https://www.cyberciti.biz/faq/update-lenovo-bios-from-linux-usb-stick-pen/)
* [How to upgrade BIOS on a Lenovo laptop running linux | Andrea Fortuna](https://www.andreafortuna.org/2019/10/08/how-to-upgrade-bios-on-a-lenovo-laptop-running-linux/)

### 試した手順

1. [フラッシュ BIOS アップデート - ThinkCentre M75q Gen 2 - Lenovo Support JP](https://support.lenovo.com/jp/ja/downloads/ds547344-flash-bios-update-thinkcentre-m75q-gen-2) から BIOS アップデート (ISO イメージ版) Windows 10 64bit用 m3cj92fusa.iso をダウンロード。
2. ダウンロードしたファイルのSHA256を確認。 `openssl dgst -sha256 m3cj92fusa.iso` の出力を上記のページのCHECKSUMのリンクを押して表示される値と比較。
3. genisoimage パッケージをインストール。 `sudo apt install genisoimage` でインストール。
4. genisoimage パッケージに含まれる geteltorito コマンドで ISO イメージを USB メモリ用に変換。

ですが私の環境 (Ubuntu 20.04 LTS) では以下のように Out of memory となってしまいました。

```
$ geteltorito -o bios_update.img m3cj92fusa.iso
Booting catalog starts at sector: 18
Manufacturer of CD: M3CJT2FA
Image architecture: x86
Boot media type is: harddisk
El Torito image starts at sector 8218 and has 1919645539 sector(s) of 512 Bytes
Out of memory!
```

## うまく行った方法: BIOSのzipファイルをFAT32のUSBメモリに展開

[ThinkCentre M75q-1の BIOSを USBメモリの UEFIブートでアップデートする方法、写真付き解説手順 (Lenovo ThinkCentre M75q-1 Tinyのファームウェア BIOS更新を写真付きで手順を解説します)](http://www.neko.ne.jp/~freewing/hardware/lenovo_m75q_amd_ryzen_5_pro_3400ge_update_bios_usb_uefi/) を参考にしました。ありがとうございます！

まず事前に一度 BIOS を起動してアップデート前のバージョンを確認しました（スマホで取った写真から下記に転記）。

```
BIOS Revision Level         M3CKT21A
Boot Block Revision Level   1.21
BIOS Date (MM/DD/YYYY)      10/21/2020
```

1. [フラッシュ BIOS アップデート - ThinkCentre M75q Gen 2 - Lenovo Support JP](https://support.lenovo.com/jp/ja/downloads/ds547344-flash-bios-update-thinkcentre-m75q-gen-2) から BIOS アップデート (USB ドライブ パッケージ) m3cjt2fusa.zip をダウンロード。
2. 中身を消しても OK な USB メモリを用意して Windows で FAT32 形式でフォーマットし、上記でダウンロードした zip ファイルの中身をコピー（試してないですが Linux でも大丈夫だと思います）。
3. USB メモリを ThinkCentre に挿して再起動し BIOS でブート順を調整して USB メモリから起動 （Linux を入れているので Secure Boot は Disabled 済み）。
4. USB メモリから起動したら画面に表示される質問に適宜答えて BIOS を更新。
    * "Would you like to update the Serial Number?" と聞かれるがシリアルナンバーは更新しないので「n」と「Enter」を押す。
    * "Would you like to update the Machine Type and Model?" もマシンのタイプやモデルは更新しないので「n」と「Enter」を押す。
    * このあと BIOS を更新するかの確認メッセージが出たかもしれません（写真撮るの忘れたのでうろ覚え）。出た場合は「y」と「Enter」を押します。
    * 更新が終わるまで待ちます。 **途中で電源を切らないよう注意。** 更新終わった後自動で再起動かかるとのことでしたが、ここからは参考にしたページとは挙動が違いました。画面が真っ暗になってから5分ぐらいたってようやく再起動したのですが、 USB メモリから起動したら以下のようなメッセージが出ました。

```
BIOS ROM file is older than (or same as) the current BIOS ROM image.
Continue any way? (Y/y or N/n only)
```

既に更新できているようですので「n」と「Enter」を押して中止しました。
その後 USB メモリを抜いて再起動し、 BIOS に入ってバージョンを確認しました。

バージョンを確認すると以下のようになっていました。

```
BIOS Revision Level         M3CKT2FA
Boot Block Revision Level   1.2F
BIOS Date (MM/DD/YYYY)      08/02/2021
```

無事更新できたようです。

