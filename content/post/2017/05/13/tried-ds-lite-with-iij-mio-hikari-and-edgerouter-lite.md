+++
title="IIJmioひかりとEdgeRouter-LiteでDS-Liteを試してみた"
date = "2017-05-13T16:23:00+09:00"
lastmod = "2017-07-20T23:38:00+09:00"
tags = ["edgerouter"]
categories = ["blog"]
+++



## はじめに

会社の同僚と話していて、私もそろそろIPv6に触れる機会を作っておかないとまずいなと思い、IIJmioひかりとIPoEとひかり電話を契約してDS-Liteというのを試してみることにしました。

ネットワークは経験不足で苦手な意識の強い私ですが、少しずつでも経験を積んで多少は理解できるようになりたいという思いもあります。

で、先人たちのブログ記事に助けられながら、なんとか設定できたので一旦メモです。

[Edgerouter Lite-3でDS-Lite - Qiita](http://qiita.com/haccht/items/17ed2bed628d2fd17bea)
が、NTT東日本と西日本という違い以外は同じ構成なので大いに参考にさせていただきました。

実は当初は、パスワードなど環境に応じて異なる部分の値だけ書き換えて流せばよいかと甘く考えていました。が、実際やってみて、細かく分けて1歩1歩設定を進めていくほうが良いというか、そうでないと私には無理だということがわかりました。

ということで以下のメモも手順に分けて書くことにします。
EdgeRouter Liteのウェブの管理画面から設定を初期状態に戻して、1歩ずつ設定しながら書いていきます。

## IIJmioひかりのレンタル機材

マンションタイプでVDSLの100MbpsなのでVSDLモデムと、ひかり電話も契約したのでひかり電話対応ホームゲートウェイがレンタルされました。

* VSDLモデム : `VDSL<N>B-100E` (オンラインのドキュメントは見つけられなかったので、必要時は付属の紙ドキュメントを参照)
* ホームゲートウェイ : RT-500KI [ドキュメント](http://www.ntt-west.co.jp/kiki/download/flets/rt500ki/index.html)
    - 無線LANカード: SC-40NE「2」

## まずはRT-500KIでIPv4 PPPoEを試した

PPPoE遅いという話もネットで見かけたので、まずはRT-500KIでIPv4 PPPoEを試して実際どうなのかを検証しました。

IPv4のスピード計測は [速度.jp スピードテスト(回線速度・通信速度測定サイト) シンプル版](http://zx.sokudo.jp/) がFlash Player無しで上り下り両方計測できたのでここで計ってみました。

通常時は下りが90Mbps以上で上りが50Mbps程度と100MbpsのVDSLにしてはかなり速くて驚きました。が、土曜の深夜は下りが2.44Mbpsという時が一度ありました。ただそのときでも上りは45Mbpsと通常時と同程度でした。DS-Liteの設定で試行錯誤していてPPPoEのほうはこまめに計ってなかったので、どの時間帯が遅いかはまだ詳しくはわかっていません。

## RT-500KIのIPv4 PPPoEとIPv6ファイアウォール機能を無効に変更

ThinkPadからLANケーブルでRT-500KIに繋いでChromeで管理画面を開いて、
RT-500KIのIPv4 PPPoEとIPv6ファイアウォール機能を無効に変更しました。

IPv4 PPPoEは[基本先設定]/[接続先設定（IPv4 PPPoE）]で接続中の行の[切断]ボタンを押して切断します。
[状態]列が未接続になったら[接続可]のチェックボックスをオフにして[設定]ボタンを押して間違って接続されないようにしておきます。

IPv6ファイアウォール機能は[詳細設定]/[IPv6パケットフィルタ設定（IPoE）]で[IPv6ファイアウォール機能]で[無効]のラジオボタンを選んで[設定]ボタンを押します。

## EdgeRouter Liteの設定

### PCをThinkPadに接続

Windows10が動いているThinkPadにLANケーブルを接続してEdgeRouterのeth0につないで設定しました。

* コントロールパネル > ネットワークとインターネット > ネットワークで「イーサネット」を選択してポップアップメニューの「プロパティ」を選択します。
* 「イーサネットのプロパティ」ダイアログが開いたら「ネットワーク」タブの「この接続は次の項目を使用します」のリストで「インターネットプロトコルバージョン 4 (TCP/IPv4)」を選んで「プロパティ」ボタンを押します。
* 「インターネットプロトコルバージョン 4 (TCP/IPv4)のプロパティ」ダイアログで以下のように設定します。
    - 「次のIPアドレスを使う」ラジオボタンを選択。
    - 「IPアドレス」に `192.168.1.2` と入力。
    - 「サブネットマスク」に `255.255.255.0` と入力。
    - 「デフォルトゲートウェイ」に `192.168.1.1` と入力。
    - 「次のDNSサーバのアドレスを使う」ラジオボタンを選択。
    - 「優先DNSサーバ」と「代替DNSサーバ」のアドレスは空のままにする。

以下のコマンドを実行しデフォルトのパスワード `ubnt` でログインします。
ThinkPadではBash on Windowsを使っています。

```console
ssh ubnt@192.168.1.1
```

### 管理者ユーザの作成

EdgeOS User Guideにはデフォルトの `ubnt` ユーザとは別にユーザを作るのが望ましいようなことが書いてあったので作って `ubnt` は消すことにします。また ssh は鍵認証だけに変更します。

* [Vyatta/VyOSでユーザの作成・パスワード変更・ユーザの削除を行う | 俺的備忘録 〜なんかいろいろ〜](https://orebibou.com/2015/01/vyattavyos%E3%81%A7%E3%83%A6%E3%83%BC%E3%82%B6%E3%81%AE%E4%BD%9C%E6%88%90%E3%83%BB%E5%A4%89%E6%9B%B4%E3%83%BB%E5%89%8A%E9%99%A4%E3%82%92%E8%A1%8C%E3%81%86/)

以下は設定モード内の設定のコマンドのみ書いていきます。 `configure` 、 `commit` などの設定反映の流れは
[EdgeOSの設定項目の階層構造を理解する](/blog/2017/05/13/understanding-edge-os-config-hierarchy-structure/) を参照してください。

以下の例ではユーザ名を `admin1` 、パスワードを `admin1pass` としていますが、実際に設定するときは、ちゃんとしたユーザ名とパスワードにしてください。

```text
set system login user admin1 level admin
set system login user admin1 authentication-password admin1pass
```

補足1: `level` の指定はしなくてもデフォルトで `admin` になるようです。以下に書いたように `sudo` で確認しました。

補足2: ついでにユーザが消した時の挙動を試してみたのですが、EdgeRouter Lite v1.9.1.1では再起動しなくても上の記事のように設定が一部残るということはなくなっていました。

一方で、再度同じ名前のユーザ名を作ると、以下のようにホームディレクトリが既にあるという警告が出ました。ということでユーザを削除したときはホームディレクトリも消しておくほうがセキュリティ上は良さそうです。

```console
ubnt@ubnt# commit
[ system login ]
useradd: warning: the home directory already exists.
Not copying any file from skel directory into it.
```

ubntユーザのほうはsshをログアウトして新しいユーザとパスワードでログイン出来ることを確認します。

```console
$ ssh admin1@192.168.1.1
```

`sudo` で管理者になれるか確認します。パスワード不要で `root` ユーザになれました。

```console
admin1@ubnt:~$ sudo whoami
root
```

### 公開鍵認証の設定

毎回パスワードを入力するのは面倒なのでssh-agentを使うようにするため、公開鍵でログインできるようにします。

* [VyattaのSSHサーバで公開鍵でログインする — どこか遠くでのんびり怠惰に暮らしたい](https://misc.mat2uken.net/blog/2013/06/03/vyatta_ssh_use_public_key.html)

公開鍵でログインできるように以下の設定をします。 `public-keys` の後の `admin1@some-host` のホスト名は何を設定すれば良いのかと悩みましたが、Vyattaのドキュメントを見ると  `public-keys` の後の `admin1@some-host` 鍵のIDとのことなのでホスト名は付けなくても良いようです。インターネット越しに接続したりする場合は接続元のホスト名を書いておくと良さそうです。

```text
set system login user admin1 authentication public-keys admin1@some-host type ssh-rsa
set system login user admin1 authentication public-keys admin1@some-host key ssh公開鍵の本体部分(先頭のssh-rsaと末尾のuser@some-hostのようなコメントを除いた部分)
```

一度sshを抜けて、ssh-agentを動かして鍵を追加した状態で再度sshログインし、パスワードを聞かれずにログインできることを確認します。

```console
$ ssh admin1@192.168.1.1
```

### パスワード認証を無効にして公開鍵認証のみに限定

```text
set service ssh disable-password-authentication
```

一旦sshを抜けて `ubnt` ユーザで接続を試みるとエラーになることを確認します。

```console
$ ssh ubnt@192.168.1.1
Welcome to EdgeOS

By logging in, accessing, or using the Ubiquiti product, you
acknowledge that you have read and understood the Ubiquiti
License Agreement (available in the Web UI at, by default,
http://192.168.1.1) and agree to be bound by its terms.

Permission denied (publickey).
```

### 初期ユーザ ubnt を削除

再度 `admin1` ユーザでsshでログインします。以降はこのユーザで作業します。

```console
$ ssh admin1@192.168.1.1
```

.. code-block:: text

    delete system login user ubnt

### eth1とeth2にLAN用のアドレスを設定

EdgeRouterの初期状態のIPv4アドレスは 192.168.1.1 ですが、RT-500KIも同じアドレスです。

RT-500KIのほうはなるべく設定を変更しないで済ませたいので、RT-500KIからDHCPでIPv4アドレスをもらうことにします。

ということでEdgeRouterのIPv4のネットワークは以下のように設定することにしました。

* eth0 (WAN):  192.168.1.2/24 (RT-500KIからDHCPでアドレスをもらう)
* eth1 (LAN1): 192.168.2.1/24
* eth2 (LAN2): 192.168.3.1/24

この後順を追って設定していきます。

eth0の設定を変えてRT-500KIとLANケーブルを接続したらThinkPadから設定を行うためにeth0には繋げなくなるので、eth1かeth2につないで設定できるようにします。

```text
set interfaces ethernet eth1 address 192.168.2.1/24
set interfaces ethernet eth1 description LAN1
set interfaces ethernet eth1 duplex auto
set interfaces ethernet eth1 speed auto

set interfaces ethernet eth2 address 192.168.3.1/24
set interfaces ethernet eth2 description LAN2
set interfaces ethernet eth2 duplex auto
set interfaces ethernet eth2 speed auto
```

commitとsaveを実行したらsshを抜けます。
eth0からケーブルを外してThinkPadで有線EthernetアダプタのTCP/IPv4のプロパティで以下のように設定を変えてからeth1にケーブルを指します。

* IPアドレス: 192.168.2.2
* サブネットマスク: 255.255.255.0 (そのまま)
* デフォルトゲートウェイ: 192.168.2.1

詳細は省略しますが、別途コマンドプロンプトを起動していて、ケーブルを抜き差ししたときは `ipconfig /all` コマンドを実行してEthernetアダプタに付与されたIPv4およびIPv6アドレスを確認しています。正しいアドレスがつかないときは、ケーブルを抜いて暫く待ってから挿すとか、挿した後しばらく待ってみます。

eth1のアドレスを指定してsshでログインできることを確認します。

```console
$ ssh admin1@192.168.2.1
```

### eth0をRT-500KIに繋いでDHCPでIPv4のアドレスをもらう

eth0の静的IPv4アドレスの設定を消してDHCPクライアントを起動します。

```text
delete interfaces ethernet eth0 address
set interfaces ethernet eth0 address dhcp
set interfaces ethernet eth0 duplex auto
set interfaces ethernet eth0 speed auto
set interfaces ethernet eth0 description WAN
```

上記の反映後にeth0をRT-500KIに繋いでDHCPでIPv4のアドレスをもらいます。

操作モードに戻って `ip a` コマンドを実行し、eth0に 192.168.1.x/24 のアドレスが付与されたことを確認します。以下では 192.168.1.2/24 として説明します。

この時点でのpingでの疎通確認は以下の通りでした。

* EdgeRouterから `ping 192.168.1.1` は通る。
* EdgeRouterから `ping 192.168.2.1` は通る。
* EdgeRouterから `ping 192.168.2.2` は通らない。
* ThinkPadから `ping 192.168.2.1` は通る。
* ThinkPadから `ping 192.168.1.2` は通らない。

### RT-500KIからeth0にIPv6アドレスをもらう

冒頭に書いたQiitaの記事によると

  今回はひかり電話契約ありなので、HGWからのRAをもとにeth0のIPv6アドレスはautoconfする。
  またDHCPv6-PDによりHGWには/60のprefixが
  割り当てられている。これを/64のprefixに分割してLAN内のIPv6アドレスに利用する。

とのことなので、この通りにします。

実はここは私はまだよくわかってないです。1行ずつ実行して `compare` で確認したところ、1行目を実行すると2行目の内容も反映されていて、3行目を実行すると4行目の内容も反映されていました。これ自体は単に依存関係があるものは自動で設定されることだと思います。

```text
set interfaces ethernet eth0 ipv6 address autoconf
set interfaces ethernet eth0 ipv6 dup-addr-detect-transmits 1
set interfaces ethernet eth0 ipv6 router-advert other-config-flag true
set interfaces ethernet eth0 ipv6 router-advert send-advert true
```

ただ、 `commit` した後、別端末でEdgeRouterにsshして操作モードで `ip a` を実行してもIPv4アドレスはついていますが、IPv6アドレスはついていませんでした。

正確に言うと `inet6` で `fe80:` から始まるIPv6アドレスは元からついていましたが、
[IPv6アドレス - Wikipedia](https://ja.wikipedia.org/wiki/IPv6%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9) によるとこれはリンクローカルアドレスというもので、RT-500KIから付与されるIPv6アドレスではないです。

暫く待って何回か `ip a` を実行してもeth0にIPv6アドレスはつきませんでした。
次項で参照するので `ip a` の結果が表示された端末は閉じずに残しておくか出力結果をテキストエディタなどにコピペしておいてください。

### RT-500KIにつないでIPv6アドレスの払い出し状況を確認

ThinkPadからEdgeRouterのeth1に繋いでいたケーブルを外して、有線Ethernetアダプタの設定を以下のようにDHCPクライアントを使うように変えてからRT-500KIに繋ぎました。

    - 「IPアドレスを自動的に取得する」ラジオボタンを選択。
    - 「DNSサーバーのアドレスを自動的に取得する」ラジオボタンを選択。

Chromeで管理画面を開いて[情報]/[DHCPv6サーバ払い出し状況]を確認し、画面下部の一覧にMACアドレスがEdgeRouterのeth0のMACアドレスと一致する行が1行あり、他には行がない状態でした。

IPv6プレフィクスは `2409:` で始まる値がついていて最後は `/60` になっていました。

IPv6プレフィックスの値は次項で参照するので管理画面のウィンドウを閉じずに残しておくか、値をテキストエディタなどにコピペしておいてください。

確認が終わったら、RT-500KIからケーブルを抜いて、再度有線EthernetアダプタをEdgeRouterのeth1に繋ぐための静的アドレス設定に戻してからeth1に挿します。

この設定変更を抜き差しするたびに行うのは面倒なので、次項でeth1とeth2にDHCP設定を行います。

### EdgeRouterでeth1とeth2に対してIPv4のDHCPサーバを動かす

補足: この手順は実際は最後に実行したのですが、話の流れ上ここに書いておくことにしました。
振り返ってみて考えると「eth1とeth2にLAN用のアドレスを設定」の直後に実行するのが良さそうです。

冒頭のQiitaの記事からはアドレスの範囲を好みで変更して設定してみました。

```text
set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 default-router 192.168.2.1
set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 dns-server 192.168.2.1
set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 lease 86400
set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 start 192.168.2.2 stop 192.168.2.99

set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 default-router 192.168.3.1
set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 dns-server 192.168.3.1
set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 lease 86400
set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2 stop 192.168.3.99
```

ThinkPadからEdgeRouterのeth1に繋いでいたケーブルを外して、有線Ethernetアダプタの設定を以下のようにDHCPクライアントを使うように変えてから、再度EdgeRouterのeth1に挿してIPv4のアドレスが付与され `ssh admin1@192.168.2.1` で接続できることを確認しました。

    - 「IPアドレスを自動的に取得する」ラジオボタンを選択。
    - 「DNSサーバーのアドレスを自動的に取得する」ラジオボタンを選択。

### 再度EdgeRouterでip aで確認するとeth0にIPv6アドレスがついてました

ご飯食べて続きをやろうとThinkPadからケーブルをeth1に繋いでsshで入って `ip a` を実行するとeth0に先ほどRT-500KIの管理画面で確認したIPv6プレフィクスの `/60` を `/64` に変えたアドレスが付与されていました。どれぐらいの時間で付与されたのかはちょっとわかりません。

確認するため

```text
delete interfaces ethernet eth0 ipv6
```

で設定を一旦消した後、操作モードで

```console
admin1@ubnt:~$ ip del eth0のIPv6アドレス/64 dev eth 0
```

でIPv6アドレスを消してから、再度設定を入れてみました。ちゃんと計っていませんが10～15分で `2409:` で始まるIPv6アドレスが付与されたようです。

操作モードで `ping6` コマンドで `www.iij.ad.jp` にアクセスしてみると通りました。

```console
admin1@ubnt:~$ ping6 www.iij.ad.jp
PING www.iij.ad.jp(www.iij.ad.jp) 56 data bytes
64 bytes from www.iij.ad.jp: icmp_seq=1 ttl=52 time=15.4 ms
64 bytes from www.iij.ad.jp: icmp_seq=2 ttl=52 time=14.0 ms
64 bytes from www.iij.ad.jp: icmp_seq=3 ttl=52 time=14.1 ms
^C
--- www.iij.ad.jp ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 14.039/14.546/15.492/0.683 ms
```

試しにThinkPadからも `ping6 www.iij.ad.jp` を実行してみたら、数秒固まった後、通るようになりました。あれおかしいな、まだ通らないはずと思ったのですがtimeを見ると124~127 msと1桁多い時間がかかっていました。ThinkPadのWi-Fiを無効にしてから再度試すと今度は通らなくなりました。話がややこしくなるのでWi-Fiなど関係のない通信は切っておいたほうが良さそうです。

### DHCPv6-PDでeth1とeth2にIPv6アドレスを付与

以下の設定を追加してDHCPv6-PDというのでeth1とeth2にIPv6アドレスを付与します。

DHCPv6-PDは初耳だったのでググって見つけた
[書いて覚えるDHCPv6-PD - SSSSLIDE](http://sssslide.com/speakerdeck.com/jitomesky/shu-itejue-erudhcpv6-pd)
を眺めてみました。

```text
set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth1 host-address '::1'
set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth1 prefix-id ':1'
set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth1 service slaac
set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth2 host-address '::1'
set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth2 prefix-id ':2'
set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth2 service slaac
set interfaces ethernet eth0 dhcpv6-pd pd 0 prefix-length /60
set interfaces ethernet eth0 dhcpv6-pd rapid-commit enable
```

実行後、操作モードで `ip a` で確認すると eth1とeth2に `2409:` で始めるIPv6アドレスが付与されていました。

### ThinkPadからIPv6でインターネットに通信できることを確認

またThinkPadで `ip a` を実行すると有線Ethernetアダプタのeth0に `2409:` で始まるIPv4アドレスが2つ付いていました。1つは `/64` でもう1つは `/128` になっていました。コマンドプロンプトで `ipconfig /all` でも確認すると、こちらは `/64` などが無いアドレスのみで表示されていて `/64` のアドレスのほうは "IPv6 Address" というラベル、 `/128` のアドレスのほうは "Temporary IPv6 Address" というラベルになっていました。 

この状態でChromeで http://www.iij.ad.jp にアクセスしてみると画面上部に "CONNECTED via IPv6" という表示が出ました！

一方、IPv6に未対応のサイトにアクセスしようとしても表示されない状態であることを確認しました。


### ファイアウォール設定

ファイアウォール無しでインターネットに長時間繋いでおくのは怖いので、ここでファイアウォールを設定します。今回の手順をマスターして確実に繋げられるようになったら、先にファイアウォールの設定をしてからインターネットに繋ぐようにするほうがよいと思います。

[設定例 ＞ Firewall ＞ 基本設定 - EdgeOS 日本語Wiki [非公式]](http://edge-os.net/wiki/view/%E8%A8%AD%E5%AE%9A%E4%BE%8B_%EF%BC%9E_Firewall_%EF%BC%9E_%E5%9F%BA%E6%9C%AC%E8%A8%AD%E5%AE%9A) も参考にしつつ、冒頭に上げたQiitaの記事の設定をそのまま頂きました。

```text
set firewall ipv6-name WANv6_IN default-action drop
set firewall ipv6-name WANv6_IN description 'WAN to LAN'
set firewall ipv6-name WANv6_IN enable-default-log
set firewall ipv6-name WANv6_IN rule 10 action accept
set firewall ipv6-name WANv6_IN rule 10 description 'Allow established/related'
set firewall ipv6-name WANv6_IN rule 10 state established enable
set firewall ipv6-name WANv6_IN rule 10 state related enable
set firewall ipv6-name WANv6_IN rule 20 action drop
set firewall ipv6-name WANv6_IN rule 20 description 'Drop invalid state'
set firewall ipv6-name WANv6_IN rule 20 state invalid enable
set firewall ipv6-name WANv6_IN rule 30 action accept
set firewall ipv6-name WANv6_IN rule 30 description 'Allow IPv6 ICMP'
set firewall ipv6-name WANv6_IN rule 30 protocol ipv6-icmp
set firewall ipv6-name WANv6_LOCAL default-action drop
set firewall ipv6-name WANv6_LOCAL description 'WAN to Router'
set firewall ipv6-name WANv6_LOCAL enable-default-log
set firewall ipv6-name WANv6_LOCAL rule 10 action accept
set firewall ipv6-name WANv6_LOCAL rule 10 description 'Allow established/related'
set firewall ipv6-name WANv6_LOCAL rule 10 state established enable
set firewall ipv6-name WANv6_LOCAL rule 10 state related enable
set firewall ipv6-name WANv6_LOCAL rule 20 action drop
set firewall ipv6-name WANv6_LOCAL rule 20 description 'Drop invalid state'
set firewall ipv6-name WANv6_LOCAL rule 20 state invalid enable
set firewall ipv6-name WANv6_LOCAL rule 30 action accept
set firewall ipv6-name WANv6_LOCAL rule 30 description 'Allow IPv6 ICMP'
set firewall ipv6-name WANv6_LOCAL rule 30 protocol ipv6-icmp
set firewall ipv6-name WANv6_LOCAL rule 40 action accept
set firewall ipv6-name WANv6_LOCAL rule 40 description 'Allow DHCPv6'
set firewall ipv6-name WANv6_LOCAL rule 40 destination port 546
set firewall ipv6-name WANv6_LOCAL rule 40 protocol udp
set firewall ipv6-name WANv6_LOCAL rule 40 source port 547
set firewall ipv6-name WANv6_LOCAL rule 50 action accept
set firewall ipv6-name WANv6_LOCAL rule 50 description 'Allow DS-Lite'
set firewall ipv6-name WANv6_LOCAL rule 50 protocol ipip

set firewall name WAN_IN default-action drop
set firewall name WAN_IN description 'WAN to LAN'
set firewall name WAN_IN rule 10 action accept
set firewall name WAN_IN rule 10 description 'Allow established/related'
set firewall name WAN_IN rule 10 state established enable
set firewall name WAN_IN rule 10 state related enable
set firewall name WAN_IN rule 20 action drop
set firewall name WAN_IN rule 20 description 'Drop invalid state'
set firewall name WAN_IN rule 20 state invalid enable
set firewall name WAN_LOCAL default-action drop
set firewall name WAN_LOCAL description 'WAN to Router'
set firewall name WAN_LOCAL rule 10 action accept
set firewall name WAN_LOCAL rule 10 description 'Allow established/related'
set firewall name WAN_LOCAL rule 10 state established enable
set firewall name WAN_LOCAL rule 10 state related enable
set firewall name WAN_LOCAL rule 20 action drop
set firewall name WAN_LOCAL rule 20 description 'Drop invalid state'
set firewall name WAN_LOCAL rule 20 state invalid enable

set interfaces ethernet eth0 firewall in ipv6-name WANv6_IN
set interfaces ethernet eth0 firewall in name WAN_IN
set interfaces ethernet eth0 firewall local ipv6-name WANv6_LOCAL
set interfaces ethernet eth0 firewall local name WAN_LOCAL
```

この設定を入れた状態でEdgeRouterとThinkPadから `ping6 www.iij.ad.jp` が引き続き通ることを確認しました。
本来はインターネット上からアクセスしてファイアウォールに弾かれることを確認すべきですが、他にIPv6でアクセスできる環境を今持ってないので省略しました。

### DS-Liteの設定をしてIPv6未対応のサイトにアクセス

DS-Liteについては
[Vyatta改めVyOSでDS-Liteを使う(IIJmio+フレッツIPoE) — どこか遠くでのんびり怠惰に暮らしたい](https://misc.mat2uken.net/blog/2014/12/19/using_dslite_with_iijmio.html)
と
[てくろぐ: DS-LiteでIPv4してみませんか？](http://techlog.iij.ad.jp/archives/1254)
を眺めました。

ここも冒頭の記事の設定をほぼそのまま頂きました。

remote-ip のアドレスはNTT東日本と西日本で違うということで
[YAMAHA NVR500](http://www.mfeed.ad.jp/transix/ds-lite/contents/yamaha_nvr500.html)
を見て西日本のほうの1つめのアドレスを指定しました。この情報は事前に同僚に教わっていました。自力では解決できなかったこと間違いなし！感謝です！

```text
set interfaces ipv6-tunnel v6tun0 encapsulation ipip6
set interfaces ipv6-tunnel v6tun0 firewall in name WAN_IN
set interfaces ipv6-tunnel v6tun0 local-ip 【eth0に付与されたIPv6アドレスを/64無しで指定】
set interfaces ipv6-tunnel v6tun0 mtu 1500
set interfaces ipv6-tunnel v6tun0 multicast disable
set interfaces ipv6-tunnel v6tun0 remote-ip '2404:8e01::feed:100'
set interfaces ipv6-tunnel v6tun0 ttl 64

set protocols static interface-route 0.0.0.0/0 next-hop-interface v6tun0
```

これでThinkPadでChromeでIPv6未対応のサイトにアクセスしても表示できました！

補足: ちょっと気になったのは `ipv6-tunnel` はVyattaやVyOSのドキュメントでは見当たらずそちらでは `tunnel` になっていました。最初試行錯誤してたときに `tunnel` も試してみたのですが `local-ip` や `remote-ip` にIPv6を指定して実行すると、コマンド実行時か `commit` 実行時かは忘れましたが、 【指定したアドレス】 is not valid type of ipv4というエラーになりました。

ということでipv6-tunnelはEdgeOSがVyattaからフォークした後独自に拡張した部分なのかもしれません。ググってはみたんですが特に情報が見つけられていません。

### DNSフォワーディングの設定追加

2017-05-14 追記。一晩たって再度試してみるとEdgeRouterからは `ping6 www.iij.ad.jp` で接続できますが、ThinkPadからは出来ないという状態になっていました。

冒頭のQiitaの記事で行っていたdns forwardingの設定を入れれば解決しました。

```text
set service dns forwarding cache-size 150
set service dns forwarding listen-on eth1
set service dns forwarding listen-on eth2
set service dns forwarding name-server 192.168.1.1
```

DNSサーバのアドレスですが、最初試行錯誤してた時は `192.168.1.1` ではなくIIJmioひかりのプライマリDNSのIPv6とセカンダリDNSのアドレスを指定していました。

```text
set service dns forwarding name-server 【IIJmioひかりのプライマリDNSのIPv6アドレス】
set service dns forwarding name-server 【IIJmioひかりのセカンダリDNSのIPv6アドレス】
```

IIJmioひかりの「サービス詳細情報」ページ (ホーム > 設定と利用 > サービス詳細情報 > IIJmioひかり、要ログイン）の
「インターネット（IPv6 PPPoE）接続で接続する場合」の項に載っていました。
IPv6 PPPoEを使っているわけではないですが、DNSサーバは共通で行けました。

ですが、なるべくなら自動で取得してほしいので、RT-500KIに任せるように 192.168.1.1 に変えてみたらそれでも動いたので、今は上記の設定にしています。

## スピードテスト

[IIJmioのIPv6スピードテスト](http://speedtest6.iijmio.jp) で試しました。Flash Playerが必要なので、Chromeで chrome://settings/content にアクセスしてFlashの[例外を管理]ボタンを押して http://speedtest6.iijmio.jp を許可で追加しておきます。
何回か時間を変えて計測してみると 93 Mbps ぐらいでした。

[光回線でどのくらい速度が出ているか測定したい。 | 会員サポート ＞ Q&A（よくあるご質問） : @nifty](http://qa.nifty.com/cs/catalog/faq_nqa/qid_10463/1.htm) の「NTT西日本」の「IPv6接続の場合」から辿って大阪のサーバで測定できるフレッツ速度測定サイト http://osaka.speed.flets-west.jp でも計ってみました。こちらも下り91 Mbpsとだいたい90ちょっとでした。

## おわりに

動いている設定の紹介記事を読みつつも、私がよくわかっていない状態で1歩1歩試行錯誤しながらだったのでほぼ丸一日かかってしまいましたが、無事DS-Liteを試すことが出来ました！
実際に動かしてみることで、少しずつですが理解が深まってきた気がします。

冒頭のQiitaの記事では pppoe も併用していたり、
[EdgeMAX – Ubiquiti Networks Support and Help Center](https://help.ubnt.com/hc/en-us/categories/200321064-EdgeMAX) の設定事例集でもWANを複数指定してロードバランシングしたりフェールオーバーもできるようなので、そのへんもおいおいやっていきたいです。
