+++
title="EdgeOSのドキュメントのリンクまとめ"
date = "2017-05-13T15:35:00+09:00"
tags = ["edgerouter"]
categories = ["blog"]
+++


## はじめに

[EdgeOSの設定項目の階層構造を理解する](/blog/2017/05/13/understanding-edge-os-config-hierarchy-structure/) にも一部書きましたが、EdgeOSのドキュメントのリンクをまとめておきます。

## 公式ドキュメント

* [Ubiquiti NetworksのERLite-3用のファームウェアとドキュメントのダウンロードページ](https://www.ubnt.com/download/edgemax/edgerouter-lite/erlite3) の "EdgeOS(TM) User Guide"
    - Appendix AにCLIの使い方の説明があります。
    - しかし、コマンドのレファレンスマニュアルは含まれていません。後述のようにfork元のVyattaのドキュメントを参照するのが現状では良さそうです。
* [EdgeMAX – Ubiquiti Networks Support and Help Center](https://help.ubnt.com/hc/en-us/categories/200321064-EdgeMAX) にはGetting Standardや各種設定事例集や独自コマンドの作り方などいろいろなドキュメントがあります。まだほとんど見てないので、いつか必要になったら見ます。

## 非公式ドキュメント

* [EdgeOS 日本語Wiki [非公式]](http://edge-os.net/wiki/view/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8)

## VyOSのコミュニティによるドキュメント

* [VyOS - Wikipedia](https://ja.wikipedia.org/wiki/VyOS)
* [VyOSの本家ページ(Wiki)](https://wiki.vyos.net/wiki/Main_Page)
* [日本 VyOS ユーザー会](http://www.vyos-users.jp/)
* [VyOSの本家ページ(Wiki)の日本語版(翻訳中とのこと)](http://wiki.vyos-users.jp/%E3%83%A1%E3%82%A4%E3%83%B3%E3%83%9A%E3%83%BC%E3%82%B8)

## Vyattaのドキュメント

[VyOSの本家ページ(Wiki)](https://wiki.vyos.net/wiki/Main_Page) のページ上部の囲みによるとVyatta 6.5のドキュメントが参考になるそうです。
また、
[Edgemax CLI Reference Manual - Ubiquiti Networks Community](https://community.ubnt.com/t5/EdgeMAX/Edgemax-CLI-Reference-Manual/td-p/1628869)
のスレッドのコメントによるとEdgeOSはVyatta 6.3からフォークしたそうなので、そちらのドキュメントも参照すると良いかもしれません。
このスレッド内に [Index of /vyatta/6.3/](https://dl.networklinx.com/vyatta/6.3/) と [Index of /vyatta/6.5/](https://dl.networklinx.com/vyatta/6.5/) のドキュメントへのリンクがあるので、そこからダウンロード可能です。
以下のコマンドでまとめてダウンロードしました。

```console
wget -r -np http s://dl.networklinx.com/vyatta/6.3/
wget -r -np http s://dl.networklinx.com/vyatta/6.5/
