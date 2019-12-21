+++
title="EdgeOSの設定項目の階層構造を理解する"
date = "2017-05-13T10:48:00+09:00"
tags = ["edgerouter"]
categories = ["blog"]
+++


## はじめに

EdgeRouter Lite (ERLite-3)をCLI (Command Line Interface)で設定しているうちにようやく基本が理解できたのでメモです。

## EdgeOSとは

[EdgeOS 日本語Wiki [非公式]](http://edge-os.net/wiki/view/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8) の「EdgeOS とは」と「VyOS・Vyatta との違い」の説明がわかりやすかったです。

## CLIの設定の基本操作

[コマンド ＞ コマンド一覧 - EdgeOS 日本語Wiki [非公式]](http://edge-os.net/wiki/view/%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89_%EF%BC%9E_%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E4%B8%80%E8%A6%A7) の「CLI の基本操作」がとっかかりとしては良かったです。


## 公式のEdgeOS User Guideのダウンロード

[Ubiquiti NetworksのERLite-3用のファームウェアとドキュメントのダウンロードページ](https://www.ubnt.com/download/edgemax/edgerouter-lite/erlite3) から "EdgeOS(TM) User Guide" がダウンロードできました。

.. image:: {attach}/images/2017/05/13/Ubiquiti-Networks-Downloads-ERLite-3.png
    :width: 538px
    :height: 410px
    :alt: ERLite-3 document and firmware download page

このページへの行き方もメモしておきます。

1. [Ubiquiti Networks - Wireless networking products for broadband and enterprise](https://www.ubnt.com/) の右上の "Support" をクリック。
2. [Ubiquiti Networks Support and Help Center](https://help.ubnt.com/hc/en-us) で "EdgeMax" をクリック。
3. [EdgeMAX – Ubiquiti Networks Support and Help Center](https://help.ubnt.com/hc/en-us/categories/200321064-EdgeMAX) で "Latest Software" をクリック。
4. [Ubiquiti Networks - Downloads](https://www.ubnt.com/download/edgemax/) の左のツリーで "EdgeRouter Lite" の "ERLite-3" を選択。

## EdgeOS User GuideのCLIでの設定の流れの説明

Appendix AのCommand Line Interfaceにコマンドラインでの設定の流れについて図入りで詳しく説明されていますのでぜひご覧ください。

## CLIの補完とコマンド履歴検索

* CLIではTABキーでコマンドやサブコマンドの補完が効きます。
* またCtrl-Rでコマンド履歴検索も使えます。

## 設定の流れ

* CLIには操作 (Operational) モードと設定 (Configuration) モードという2つのモードがあります。
* 操作モードでは `ubnt@ubnt:~$` のように ユーザ名、ホスト名、カレントディレクトリの後に `$` が付いたプロンプトになっています。
* `configure` コマンドで設定モードに入ります。
* 設定モードでは `ubnt@ubnt#` のようにユーザ名、ホスト名の後に `#` がついたプロンプトになっています。
* 設定の追加・上書きは `set` コマンドを使い、ざっくり言うと「set 設定項目 値」のように指定します。
* 設定の削除は `delete` コマンドを使い、ざっくり言うと「delete 設定項目」のように指定します。
* さらには設定項目のコピーやリネームも出来ます。詳細はEdgeOS User Guideを参照してください。
* 設定項目は階層構造になっています。上で「ざっくり言うと」と書いた「設定項目」のところは階層構造のパスを指定することに相当します。
* 設定を変更したら `compare` コマンドで変更点を一覧できます。
* さらに `show` コマンドを実行して設定内容全体をJSON形式で表示します。削除された行の先頭には `-` 、追加された行の先頭には `+` 、変更された行の先頭には `>` が表示されます。また `show` の後に設定項目名または項目名のパスの一部を指定することで、一部の設定を確認することも出来ます。後ほど例を示します。
* 変更内容に問題がなければ `commit` コマンドで確定します。変更内容を破棄したい場合は `discard` コマンドを実行します。
* `commit` コマンドを実行した時点ではメモリ上の設定のみが更新されています。動作確認して問題がなければ `save` コマンドを実行して、設定内容をディスク上のファイル `/config/config.boot` に保存しておきます。するとEdgeRouterが再起動しても設定が維持されます。
* `save` コマンドの後にファイル名を指定して別名で保存したり、EdgeRouterから別のマシンにscp、ftp、tftpで接続して設定ファイルを保存したり、コミット履歴を指定した数だけ保持しておくということも可能です。が、私はPCのほうから `scp` コマンドを実行して `/config/config.boot` をEdgeRouterからPCにコピーして `git` でバージョン管理することにしました。
* 最後に `exit` コマンドを実行して設定モードから抜けて操作モードに戻ります。変更を破棄して抜けたいときは `discard` と `exit` を順に実行する代わりに `exit discard` でも可能です。

## 設定の構造を意識する必要がある例

DHCPサーバーの設定を例として示します。

```console
set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2 stop 192.168.3.99
```

この設定を削除するには以下のコマンドを実行すれば良いかと当初は思っていました。

```console
delete service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2 stop 192.168.3.99
```

`compare` コマンドを実行すると以下のように表示されました。

```console
ubnt@ubnt# compare
[edit service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2]
-stop 192.168.3.99
[edit]
```

仕組みを一旦理解した後ならこの出力でもわかるのですが、 `show` コマンドを実行したほうがわかりやすいです。出力が長いので以下では抜粋して示します。

```console
ubnt@ubnt# show
…(略)…
 service {
     dhcp-server {
         disabled false
         hostfile-update disable
…(略)…
         shared-network-name LAN2 {
             authoritative disable
             subnet 192.168.3.0/24 {
                 default-router 192.168.3.1
                 dns-server 192.168.3.1
                 lease 86400
                 start 192.168.3.2 {
-                    stop 192.168.3.99
                 }
             }
         }
         use-dnsmasq disable
     }
…(略)…
```

`service` > `dhcp-server` > `shared-network-name LAN2` というキーのパスになっていることがわかったので、以下のコマンドでその部分だけを表示してみます。

```console
ubnt@ubnt# show service dhcp-server shared-network-name LAN2
 authoritative disable
 subnet 192.168.3.0/24 {
     default-router 192.168.3.1
     dns-server 192.168.3.1
     lease 86400
     start 192.168.3.2 {
-        stop 192.168.3.99
     }
 }
[edit]
```

この後、以下のようにDHCPで払い出すIPアドレスの範囲の終端だけを違う値に設定するのであれば、変更内容は以下のようになり問題はありません。

```console
ubnt@ubnt# set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2 stop 192.168.3.199
[edit]
ubnt@ubnt# show service dhcp-server shared-network-name LAN2
 authoritative disable
 subnet 192.168.3.0/24 {
     default-router 192.168.3.1
     dns-server 192.168.3.1
     lease 86400
     start 192.168.3.2 {
>        stop 192.168.3.199
     }
 }
[edit]
```

ですが、開始と終端のアドレスを両方変えたい場合は、以下の手順ではまずいです。
ここでは上の変更を破棄するため一旦 `discard` コマンドを実行して `delete` をやり直した後、開始と終端のアドレスを変えようとしています。が、差分を見ると変更前の開始アドレス `start 192.168.3.2` の設定が残ってしまっています。

```console
ubnt@ubnt# discard
Changes have been discarded
[edit]
ubnt@ubnt# delete service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2 stop 192.168.3.99
[edit]
ubnt@ubnt# show service dhcp-server shared-network-name LAN2
 authoritative disable
 subnet 192.168.3.0/24 {
     default-router 192.168.3.1
     dns-server 192.168.3.1
     lease 86400
     start 192.168.3.2 {
-        stop 192.168.3.99
     }
 }
[edit]
ubnt@ubnt# set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.100 stop 192.168.3.199
[edit]
ubnt@ubnt# show service dhcp-server shared-network-name LAN2
 authoritative disable
 subnet 192.168.3.0/24 {
     default-router 192.168.3.1
     dns-server 192.168.3.1
     lease 86400
     start 192.168.3.2 {
-        stop 192.168.3.99
     }
+    start 192.168.3.100 {
+        stop 192.168.3.199
+    }
 }
[edit]
```

また、上記のように別の設定を追加するのではなく、単に削除したい場合も上記の手順ではまずいです。
今回の場合、古い設定の削除は以下のように `start` とその値までを指定して `stop` 以降は含めないのが正解でした。

```console
ubnt@ubnt# delete service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2
[edit]
ubnt@ubnt# show service dhcp-server shared-network-name LAN2
 authoritative disable
 subnet 192.168.3.0/24 {
     default-router 192.168.3.1
     dns-server 192.168.3.1
     lease 86400
-    start 192.168.3.2 {
-        stop 192.168.3.99
-    }
+    start 192.168.3.100 {
+        stop 192.168.3.199
+    }
 }
[edit]
```

ということで、設定項目の階層構造を把握しつつ設定の削除や変更を行う必要があるという話でした。
