---
title: "さくらのVPSでUbuntu 24.04をLUKSでディスク暗号化ありでインストール"
date: 2024-07-14T11:25:52+09:00
---
## はじめに

さくらのVPSでUbuntu 24.04をLUKSでディスク暗号化ありでインストールしたときのメモです。
もっと良いやり方があるかもしれませんが、とりあえずこれでできたという手順を書いています。

## インストール手順

### インストール用のISOから起動

1. コントロールパネルで対象のサーバーの行の「操作」列の「…」/「サーバー詳細へ移動」メニューを選ぶ
2. 「OS再インストール」ボタンを押す
3. OSインストール方法は「ISOイメージ」を選ぶ
4. インストールするOSは「Ubuntu 24.04 amd64」を選ぶ
5. ネットワークは「接続先を初期化」のまま
6. 「内容確認」ボタンを押し、確認ダイアログが表示されたら「OS再インストール」ボタンを押す
7. 画面右下に「OSインストール」というウィンドウが表示されたら「VNCコンソールを起動」ボタンを押す

### インストーラでの操作

ポイントとなる箇所だけ書きます。

### インストールタイプ選択まで
1. 言語は「English」を選ぶ
2. キーボードのレイアウトは適宜選ぶ
3. インストールのタイプは「Ubuntu Server (minimized)」を選ぶ

### ネットワーク設定

1. ネットワーク設定のens3は「Edit IPv4」で「Manual」を選択し、コントロールパネルのネットワークタブを参照して各項目を入力する（以下はアドレスを192.2.0.200として説明）
   * コントロールパネルのネットマスクが255.255.254.0の場合は/23なのでSubnetは「192.2.0.0/23」と入力（別のLinuxマシンで`ipcalc 192.2.0.200 255.255.254.0`と入力するとNetworkにこの結果が出力されます）
   * Addressにはコントロールパネルのアドレスの値を入力（この例では192.2.0.200）
   * Gatewayにはコントロールパネルのゲートウェイの値を入力
   * Name ServerにはコントロールパネルのプライマリDNSとセカンダリDNSの値を半角カンマで区切って入力
   * Search Domainsは空のままで良い
2. ネットワーク設定のens4とens5は「Edit IPv4」の「Disabled」を選ぶ

### シェルを起動してパーティションテーブルとディスクの中身をクリア

一度ディスクを使用していた場合は、LUKS暗号化ありでインストールする際にエラーになってしまいました。

[FrequentlyAskedQuestions · Wiki · cryptsetup / cryptsetup · GitLab](https://gitlab.com/cryptsetup/cryptsetup/-/wikis/FrequentlyAskedQuestions)を参考に、ストレージの設定に入る前にパーティションテーブルとディスクの中身をクリアすると大丈夫でした。

ここではインストール先のSSDのデバイス名が`/dev/vda`として説明します。

まず、右上の「Help」の「Enter shell」を選んでシェルを起動します。

1. `wipefs -a /dev/vda`を実行して、パーティションテーブルを削除します。
2. `parted /dev/vda print`を実行して、パーティションテーブルが消えたことを確認します。
3. `dd if=/dev/zero of=/dev/vda bs=4M status=progress`を実行してディスク全体をゼロクリアします。
   上記のようにcountを指定しないと、書き込み続けた後No space left on deviceのようなメッセージが出て
   終了します。100GBで10分程度かかりました。
4. `exit`と入力してインストーラに戻ります。

### ストレージ設定

1. 「Use Entire Disk」の「Set up this disk as an LVM group」の「Encrypt the LVM group with LUKS」を有効にしてパスフレーズを設定します。
2. その後「Custom storage layout」を有効にして「Done」を押して、ガイドで作られたパーティション構成を変更します。
   * LVMの論理ボリュームを一旦消します
   * LVMの論理ボリュームで2GBのスワップ領域を作ります
   * LVMの論理ボリュームで残りをbtrfsで作り「/」にマウントします

## 起動時にLUKSのパスフレーズを入力

OSの起動時にVNCコンソールを起動します。以下のプロンプトが出たら、インストール時に設定したパスフレーズを入力します。

```
Please unlock disk dm_crypt-1:
```

実際にはほかのメッセージに続いて以下のように表示され、ちょっとわかりにくいので気を付けてください。

```
begin: mounting root file system ... Begin: Running /script/local-top ...  Please unlock disk dm_crypt-1:
```

## 再起動後の設定
### タイムゾーンをJSTに変更

再起動後、以下のコマンドでタイムゾーンをJSTに変更しておきます。

```
sudo timedatectl set-timezone Asia/Tokyo
```

### 時刻同期の状態確認

インストーラでsystemd-timesyncdがセットアップされています。以下のコマンドで時刻同期の状態を確認できます。

```
timedatectl timesync-status
```
