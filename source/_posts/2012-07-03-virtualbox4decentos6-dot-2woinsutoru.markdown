---
layout: post
title: "VirtualBox4でCentOS6.2をインストール"
date: 2012-07-03 23:52
comments: true
categories: VirtualBox4, CentOS6
---
## VirtualBoxのインストール
[Downloads – Oracle VM VirtualBox](https://www.virtualbox.org/wiki/Downloads)
からダウンロードしてインストールしてください。

## ネットワークインストールのISOイメージをダウンロード

[CentOS-6.2-x86_64-netinstall.iso](http://ftp.riken.jp/Linux/centos/6.2/isos/x86_64/CentOS-6.2-x86_64-netinstall.iso)

## ホストオンリーネットワークを作成

1. [VirualBox]/[環境設定...]
1. [ネットワーク]タブ
1. [+]アイコンボタンを押してvboxnet0を作成
1. ドライバーアイコンのボタン
1. [アダプタ]タブでIPv4アドレスが「192.168.56.1」となっていることを確認
1. [DHCPサーバー]タブ
1. [サーバーを有効化]のチェックを外す
1. [OK]
1. [OK]

## 仮想マシンの作成

### 仮想マシン名とOSタイプ
名前は「CentOS6」
オペレーティングシステムは「Linux」
バージョンは「Linux 2.6 (64bit)」

### メモリ
メインメモリのサイズは1024MB

### 仮想ハードディスク
変更なし

### the virtual disk creation wizard
File typeはVDI (VirtualBox Disk Image)

### Virtual disk storage details
Storage detailsはDyamically allocated

### Virtual disk file location and size
サイズは30GB

## インストール前の仮想マシンの設定変更
### DVDドライブにメディアを設定
1. [仮想マシン]/[設定]
1. [ストレージ]タブ
1. ストレージツリーでIDEコントローラ/空を選択
1. 属性のCD/DVDドライブの右のDVDメディアアイコンをクリックして
1. 上記でダウンロードしたCentOS-6.2-x86_64-netinstall.isoを選択
1. [OK]

### ネットワークアダプタ
以下の手順では[VirtualBox マネージャー]画面からでも操作可能な部分もありますが、説明しやすいのでメニューバーからの操作で説明します。

1. [仮想マシン]/[設定]
1. [ネットワーク]タブ
1. [アダプタ2]タブ
1. [ネットワークアダプタを有効化]にチェック
1. [割り当て]で「ホストオンリーアダプタ」を選択
1. [名前]で「vboxnet0」を選択
1. [OK]

## CentOS6.2のインストール
### テキストモードでインストール開始
1. [仮想マシン]/[起動]
1. Welcome to CentOS 6.2!」の画面でTABを押す
<pre>
> vmlinuz initrd=initrd.img
</pre>
と表示されているところに、スペース、text、リターンを入力し
<pre>
> vmlinuz initrd=initrd.img text
</pre>
としてインストール開始

### Disc Found
[Skip]を選択

### Choose a Language
[English]を選択

### Keyboard Type
[us]を選択

### Installation Method
[URL]を選択して[OK]

### Network Device
[eth0]を選択して[OK]

### Configure TCP/IP
[Enable IPv6 support]をオフにして[OK]

### URL Setup
http://ftp.riken.jp/Linux/centos/6.2/os/x86_64
と入力して[OK]

### Would you like to use VNC?
[Use text mode]を選択

### Error processing driveのWarning
[Re-initialize all]を選択

### Time Zone Selection
[System clock uses UTC]のチェックはオンで
[Asia/Tokyo]を選択して[OK]

### Root Password
[Password]と[Password (confirm)]を入力して[OK]

### Partition Type
[OK]

### Writing storage configuration to disk
[Write changes to disk]

### Complete
[Reboot]を押し、再起動が開始して[Welcome to CentOS 6.2!]の画面になったらTABを2回押して起動を中断
仮想マシンのウィンドウの閉じるボタンを押し、｢操作を選択]で[仮想マシンの電源オフ]を選択して[OK]

## インストール後の仮想マシンの設定変更
### DVDドライブのメディアを除去
1. [仮想マシン]/[設定]
1. [ストレージ]タブ
1. ストレージツリーでIDEコントローラ/CentOS-6.2-x86_64-netinstall.isoを選択
1. 属性のCD/DVDドライブの右のDVDメディアアイコンをクリックして
1. [仮想ドライブからディスクを除去]

### ネットワークアダプタでvirtio-netを選択
1. [仮想マシン]/[設定]
1. [ネットワーク]タブ
1. [アダプタ1]タブ
1. [高度]をクリック
1. アダプタタイプで「準仮想化ネットワーク(virtio-net)」を選択
1. [アダプタ2]タブ
1. [高度]をクリック
1. アダプタタイプで「準仮想化ネットワーク(virtio-net)」を選択
1. [OK]

## 仮想ディスクから仮想マシンを起動してネットワークの設定
[仮想マシン]/[起動]

[localhost login:]というログインプロンプトが表示されたらroot、リターンと入力し、[Password:]プロンプトでパスワード、リターンを入力し、ログイン。

### eth1の設定
vi /etc/sysconfig/network-scripts/ifcfg-eth1

#### 変更前
HWADDRの値はインストール毎に異なります。
```
DEVICE="eth1"
HWADDR="08:00:27:28:EB:27"
NM_CONTROLLED="yes"
ONBOOT="no"
```

#### 変更後
ONBOOTをyesに変更し、下記のようにTYPE, IPADDR, NETMASKの行を追加します。
```
DEVICE="eth1"
HWADDR="08:00:27:28:EB:27"
NM_CONTROLLED="yes"
ONBOOT="yes"
TYPE="Ethernet"
IPADDR="192.168.56.101"
NETMASK="255.255.255.0"
```

<pre>
/etc/init.d/network restart
</pre>
を実行しネットワークを再起動します。

### ネットワークの動作確認

以下のコマンドを実行し、DNS名前解決とインターネットへのアクセスができることを確認。
<pre>
ping ftp.riken.jp
</pre>

ホストマシンから仮想マシンにアクセスできることを確認。
<pre>
ping 192.168.56.101
</pre>

確認できたら仮想マシンからログアウト
<pre>
exit
</pre>

以降はホストマシンからsshでログインして操作可能です。
```
ssh root@192.168.56.101
```
