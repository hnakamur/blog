+++
title="EdgeRouter Lite (ERLite-3)のファームウェアアップデート"
date = "2017-05-03T07:30:00+09:00"
tags = ["edgerouter"]
categories = ["blog"]
+++


## はじめに

[17,000円で買えるVyOSっぽいOSが動くルーター EdgeRouter Lite(ERLite-3)を使ってみる — どこか遠くでのんびり怠惰に暮らしたい](https://misc.mat2uken.net/blog/2015/11/09/edgerouter_lite3.html)
を読んで EdgeRouter Lite (ERLite-3)を買いました。

ということで初期設定内容をメモしておきます。今回はファームウェアのアップデートです。

ありがたいことに
[接続 - EdgeOS 日本語Wiki [非公式]](http://edge-os.net/wiki/view/%E6%8E%A5%E7%B6%9A)
に非常によくまとまっていました。

## 工場出荷状態の設定

* EdgeRouterのIPアドレスは `192.168.1.1`
* DHCPサーバはオフ
* SSHサーバはオン
* 管理者ユーザのIDとパスワードはともに `ubnt`

## LANケーブルで接続

Windows10が動いているThinkPadにLANケーブルを接続してEdgeRouterのeth0につないで設定しました。
別途WiFiで無線LANにもつないでいます。

* コントロールパネル > ネットワークとインターネット > ネットワークで「イーサネット」を選択してポップアップメニューの「プロパティ」を選択します。
* 「イーサネットのプロパティ」ダイアログが開いたら「ネットワーク」タブの「この接続は次の項目を使用します」のリストで「インターネットプロトコルバージョン 4 (TCP/IPv4)」を選んで「プロパティ」ボタンを押します。
* 「インターネットプロトコルバージョン 4 (TCP/IPv4)のプロパティ」ダイアログで以下のように設定します。
    - 「次のIPアドレスを使う」ラジオボタンを選択。
    - 「IPアドレス」に `192.168.1.2` と入力。
    - 「サブネットマスク」に `255.255.255.0` と入力。
    - 「デフォルトゲートウェイ」に `192.168.1.1` と入力。
    - 「次のDNSサーバのアドレスを使う」ラジオボタンを選択。
    - 「優先DNSサーバ」と「代替DNSサーバ」のアドレスは空のままにする。

## Web UIもしくはsshでCLIに接続

Web UIの場合はブラウザで `https://192.168.1.1` を開き、証明書のエラーを無視して進みます。
ブラウザウィンドウ内にログインダイアログが出たら、上記の管理者IDとパスワードを入力します。

右上の「CLI」ボタンを押すと、ブラウザウィンドウ内にCLIのウィンドウが開き、ログインプロンプトが表示されるので、再度上記の管理者IDとパスワードを入力します。

sshでCLIに接続するときは普通にsshコマンドでつなげばOKです。

```console
$ ssh ubnt@192.168.1.1
Welcome to EdgeOS

By logging in, accessing, or using the Ubiquiti product, you
acknowledge that you have read and understood the Ubiquiti
License Agreement (available in the Web UI at, by default,
http://192.168.1.1) and agree to be bound by its terms.

ubnt@192.168.1.1's password:
Linux ubnt 2.6.32.13-UBNT #1 SMP Tue Jun 4 14:54:28 PDT 2013 mips64
Welcome to EdgeOS
ubnt@ubnt:~$ ls
ubnt@ubnt:~$ pwd
/home/ubnt
ubnt@ubnt:~$ logout
Connection to 192.168.1.1 closed.
```

## Web UIからのファームウェアのアップデートは失敗

[EdgeRouter - Upgrading EdgeOS firmware – Ubiquiti Networks Support and Help Center](https://help.ubnt.com/hc/en-us/articles/205146110-EdgeRouter-Upgrading-EdgeOS-firmware)
にファームウェアのアップデート手順が書いてあります。
最初はVideo Tutorial (Web GUI)の動画の手順に従ってアップデートしようとしましたが、うまくいきませんでした。試した手順を記録しておきます。

まず、現在のバージョンを確認しておきます。Web GUIの表示は Edge Router Lite v1.2.0 でした。

CLIでも `show version` コマンドを実行し確認しておきました。

```console
ubnt@ubnt:~$ show version
Version:      v1.2.0
Build ID:     4574253
Build on:     06/26/13 12:48
Copyright:    2012-2013 Ubiquiti Networks, Inc.
HW model:     EdgeRouter Lite 3-Port
HW S/N:       F09FC2104B28
Uptime:       10:34:58 up 35 min,  2 users,  load average: 0.00, 0.00, 0.00
```

Web UIの左下のSystemボタンを押すと、設定画面のポップアップが開きます。
"Upgrade System Image" のグループボックス内の "To check for updates go to:" の後のリンクをクリックすると別タブでファームウェアやマニュアルをダウンロードできるページが開きます。
この後は上記の動画とはUIが変わっていました。
左のツリーで EdgeMax > EdgeRouter Lite > ERLite-3 を選んで、右のリストでFIRMWAREの一覧に表示されているファームウェアの行をクリックしてファームウェアをダウンロードします。

2017/04/28に登録された `ER-e100.v1.9.1.1.4977347.tar` をダウンロードしました。

あとはWeb UIのSystemのポップアップ内の "Upgrade System Image" のグループボックス内の"Upload a file" ボタンを押して、先ほどダウンロードしたファイルを選択してアップロードします。

が、やってみると Upload failed と表示されて失敗してしまいました。

バージョンが飛びすぎなのかと思い、 "SEE PAST FIRMWARE" ボタンを押して過去のファームウェアを表示し、適当に間をとって v1.7.0 をダウンロードして再度試してみました。
しかしやはり失敗でした。

これは1つずつ順番に上げる必要があるのかと思い、v1.2.0の次のv1.3.0でも試してみましたがやはりエラーでした。

## CLIからのファームウェアのアップデートは成功

しかたがないのでCLIからアップデートすることにしました。

上記のページの Instructions for Upgrading Via CLI の項ではファームウェアのURLを指定していますが、私はまだルータからインターネットにアクセスできるようにしていないので、上でダウンロードしたファイルを scp でコピーし、CLIからファイル名を指定してアップデートしました。


```console
$ scp ER-e100.v1.9.1.1.4977347.tar ubnt@192.168.1.1:
...
$ ssh ubnt@192.168.1.1
...
ubnt@ubnt:~$ add system image ER-e100.v1.9.1.1.4977347.tar
Checking upgrade image... Done
Preparing to upgrade... Done
Copying upgrade image... Done
Removing old image... Done
Checking upgrade image... Done
Finishing upgrade... Done
Upgrade completed
```

scpでコピーしたファイルはもう不要なので消しておきます。

```console
ubnt@ubnt:~$ rm ER-e100.v1.9.1.1.4977347.tar
```

今度は成功しました。現在の状態を確認します。

```console
ubnt@ubnt:~$ show system image
The system currently has the following image(s) installed:

v1.9.1.1.4977347.170426.0359   (default boot)
v1.2.0.4574253.130626.1248     (running image)

A reboot is needed to boot default image
```

.. code-block:: console

    ubnt@ubnt:~$ show system image storage
    Image name                        Read-Only   Read-Write        Total
    ------------------------------ ------------ ------------ ------------
    v1.9.1.1.4977347.170426.0359          78292           56        78348
    v1.2.0.4574253.130626.1248            62200        85232       147432

以下のコマンドで使用するシステムイメージを切り替えます。

```console
ubnt@ubnt:~$ set system image default-boot
The system currently has the following image(s) installed:

v1.9.1.1.4977347.170426.0359   (default boot)
v1.2.0.4574253.130626.1248     (running image)

A reboot is needed to boot default image
Are you sure you want to switch images? (Yes/No) [Yes]: Yes
Moving images...
Done
Switched from
  Version:      v1.9.1.1.4977347.170426.0359
to
  Version:      v1.2.0.4574253.130626.1248
```

と思ったら、既に切り替わっていたのを戻してしまいました。再度実行して新しいバージョンに切り替えました。

```console
ubnt@ubnt:~$ set system image default-boot
The system currently has the following image(s) installed:

v1.2.0.4574253.130626.1248     (running image) (default boot)
v1.9.1.1.4977347.170426.0359

Are you sure you want to switch images? (Yes/No) [Yes]: Yes
Moving images...
Done
Switched from
  Version:      v1.2.0.4574253.130626.1248
to
  Version:      v1.9.1.1.4977347.170426.0359
```

`reboot` コマンドを実行して再起動します。`Proceed with reboot? [confirm]` と表示されたら `y` を押します。Enterは不要です。

```console
ubnt@ubnt:~$ reboot
Proceed with reboot? [confirm]y

Broadcast message from root@ubnt (pts/0) (Wed Jun  1 11:26:15 2011):

The system is going down for reboot NOW!

Broadcast message from root@ubnt (pts/0) (Wed Jun  1 11:26:15 2011):

The system is going down for reboot NOW!
ubnt@ubnt:~$ Connection to 192.168.1.1 closed by remote host.
Connection to 192.168.1.1 closed.
```

再起動が終わったら Web UI を再度開き、画面左上でバージョンを確認すると無事に EdgeRouter Lite v1.9.1.1 となっていました。

## ファームウェアのアップデート情報

ファームウェアのアップデート情報は [EdgeMAX Updates Blog - Ubiquiti Networks Community](https://community.ubnt.com/t5/EdgeMAX-Updates-Blog/bg-p/Blog_EdgeMAX) を見れば良いそうです。

ページのソースを見ると https://community.ubnt.com/ubnt/rss/board?board.id=Blog_EdgeMAX にRSSフィードがありました。
ということでIFTTTでこのRSSフィードが来たらGmailで知らせるように設定してみました。
