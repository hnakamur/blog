+++
title="EdgeRouter LiteでDuckDNSとCloudFlareでダイナミックDNSを試してみた"
date = "2018-03-19T17:26:00+09:00"
tags = ["edgerouter"]
categories = ["blog"]
+++


[EdgeRouter X - 5. ダイナミック DNS の設定 ( DDNS ) | yabe.jp](https://yabe.jp/gadgets/edgerouter-x-05-ddns/)
という素晴らしい記事を見つけて、試してみたメモです。

私の環境では設定対象のネットワークインターフェースは `pppoe0` です。

# DuckDNSを使う設定

[Duck DNS](https://www.duckdns.org/) で `duckdns.org` のサブドメインとして
希望する名前を登録し、以下の設定の `host-name` のところに設定します。
`password` は Duck DNS でサブドメインを登録すると表示される token の値を設定します。

```console
set service dns dynamic interface pppoe0 service custom-duckdns host-name *****
set service dns dynamic interface pppoe0 service custom-duckdns login nouser
set service dns dynamic interface pppoe0 service custom-duckdns password **********
set service dns dynamic interface pppoe0 service custom-duckdns protocol dyndns2
set service dns dynamic interface pppoe0 service custom-duckdns server www.duckdns.org
```

端折って設定項目のみ書いていますが、実際には
[EdgeOSの設定項目の階層構造を理解する](https://hnakamur.github.io/blog/2017/05/13/understanding-edge-os-config-hierarchy-structure/)
の「設定の流れ」の手順に沿って設定変更します。

# Cloudflareを使う設定

最初 Cloudflare でサイト追加する際に自分が所有しているドメインのサブドメインを追加しようとしたのですが、
ルートドメインである必要がある旨のエラーメッセージが出たので諦めてルートドメインで試しました。
以下の設定の例では `example.net` としています。

で、そのサブドメインで希望の名前を付けて Cloudflare の管理画面から一旦ダミーのIPアドレスのAレコードを
追加します。 "Add Record" ボタンを押す前に左のアイコンをクリックしてグレーの状態にすることを忘れずに。
グレーだとツールチップが "Traffic to this hostname will not go through Cloudflare." となります。

```console
set service dns dynamic interface pppoe0 service custom-cloudflare host-name *****.example.net
set service dns dynamic interface pppoe0 service custom-cloudflare login ********@*****.***
set service dns dynamic interface pppoe0 service custom-cloudflare options zone=example.net
set service dns dynamic interface pppoe0 service custom-cloudflare password **********
set service dns dynamic interface pppoe0 service custom-cloudflare protocol cloudflare
set service dns dynamic interface pppoe0 service custom-cloudflare server www.cloudflare.com
```

login は Cloudflare に登録したログインIDです。 password には Global API Key を設定します。
管理画面の右上のログインIDのドロップダウンから My Profile のページを開きAPI Keyのセクションで確認できます。

コマンドで protocol を cloudflare に設定していますが、 EdgeRouter のウェブ管理画面の Services タブの DNS タブで設定後の状態を確認すると cloudflare のほうは Protocol が `-` (ハイフン) になっていました。Duck DNSのほうは `dyndns2` とコマンドで設定した通りに表示されていました。
Protocolのドロップダウンの選択肢に `cloudflare` が無いので表示上の問題のようです。


# ダイナミックDNSの登録状態の確認

元記事からリンクされていた [EdgeRouter - Custom Dynamic DNS – Ubiquiti Networks Support and Help Center](https://help.ubnt.com/hc/en-us/articles/204976324-EdgeMAX-Custom-Dynamic-DNS-with-Cloudflare) に確認用のコマンドが書かれていました。 `show dns dynamic status` です。

実行例はこんな感じです。

```console
admin@ubnt:~$ show dns dynamic status 
interface    : eth0
ip address   : <PublicIP>
host-name    : <hostname>
last update  : Thu Mar 30 13:29:42 2017
update-status: good
```

複数設定していると全て表示されます。
設定してすぐの時は `update-status` が空になっていましたが、しばらくしてから実行すると上記のような表示になりました。

ちなみに、以前行っていた no-ip.com 用の設定は `update-status` が `bad` になっていました。
実は更新がうまく行ってないのは知っていて約30日ごとにもうすぐ切れるという通知メールが来るのでそこから更新していました。
このコマンドで状態を確認できたんですね。

Duck DNS と Cloudflare の2か所でダイナミックDNSが使えるようになったので、 no-ip.com の設定は消しておきました。
