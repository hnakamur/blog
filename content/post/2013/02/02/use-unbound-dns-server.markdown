Title: Unboundで在宅時に自宅サーバの名前解決
Date: 2013-02-02 00:00
Category: blog
Tags: centos, unbound
Slug: 2013/02/02/use-unbound-dns-server


## 背景
私の自宅ではブロードバンドルータがグローバルIPを持っていて、DNSで自分のドメイン(以下ではexample.comとして説明します)のIPアドレスをそこにしています。ルータからLAN内のLinuxサーバ(CentOS 6.x)へはNATで繋いでいます。

外出時はこれでよいのですが、在宅時にLAN内からexample.comという名前でアクセスしようとするとサーバにアクセスできません。

今までは [hnakamur/switch_net_configs · GitHub](https://github.com/hnakamur/switch_net_configs) を使って外出時と在宅時に/etc/hostsと~/.ssh/configを切り替えてしのいでいました。が、VirtualBoxのゲストとかを考えると面倒です。

そこで、自宅サーバにDNSサーバを入れてみることにしました。
bindはセキュリティフィクスが頻発しているから避けて他のにしようと思い、[Comparison of DNS server software - Wikipedia, the free encyclopedia](http://en.wikipedia.org/wiki/Comparison_of_DNS_server_software) を見てみました。
moreに対してlessが生まれたように、bindに対してunboundというネーミングセンスが気に入ったのと、 [＠IT：DNSリゾルバのニューフェイス「Unbound」（1/2）](http://www.atmarkit.co.jp/flinux/special/unbound/unbounda.html) の記事を読んで、簡単に導入できそうと思ったのでUnboundにしました。

## 導入手順

unboundはepelにあるので、yumでインストールします。

```
yum install unbound
```

/etc/unbound/unbound.confを編集します。編集結果はこんな感じ。
```
# diff -u /etc/unbound/unbound.conf.orig /etc/unbound/unbound.conf
--- /etc/unbound/unbound.conf.orig  2013-02-02 01:56:13.541249978 +0900
+++ /etc/unbound/unbound.conf 2013-02-02 02:15:52.559227483 +0900
@@ -28,7 +28,7 @@
  extended-statistics: yes
 
  # number of threads to create. 1 disables threading.
- num-threads: 2
+ num-threads: 1
 
  # specify the interfaces to answer queries from by ip-address.
  # The default is to listen to localhost (127.0.0.1 and ::1).
@@ -40,6 +40,8 @@
  # interface: 192.0.2.153
  # interface: 192.0.2.154
  # interface: 2001:DB8::5
+ interface: 127.0.0.1
+ interface: 192.168.11.103
  #
  # for dns over tls and raw dns over port 80
  # interface: 0.0.0.0@443
@@ -69,6 +71,10 @@
  # number of ports to allocate per thread, determines the size of the
  # port range that can be open simultaneously.
  # outgoing-range: 4096
+ outgoing-range: 900
+ # Note: The value outgoing-range was set to avoid the warning below:
+ # unbound[28716:0] warning: increased limit(open files) from 1024 to 1080
+ # This server is used only by me, so a small value should be OK.
 
  # permit unbound to use this port number or port range for
  # making outgoing queries, using an outgoing interface.
@@ -178,6 +184,8 @@
  # access-control: ::0/0 refuse
  # access-control: ::1 allow
  # access-control: ::ffff:127.0.0.1 allow
+ access-control: 127.0.0.0/8 allow
+ access-control: 192.168.11.0/24 allow
 
  # if given, a chroot(2) is done to the given directory.
  # i.e. you can chroot to the working directory, for example,
```

* 自宅サーバのCPUはシングルコアなのでnum-threadsは1にしました。
* interfaceを0.0.0.0にしていないのは、KVMが別のネットワークインタフェースでdnsmaskでDNSのポート53を既に使っているためです。192.168.11.103はDNSサーバのアドレスです。
* outgoing-rangeはopen filesの警告が出ないように下げてみました。どうせ使うのは私一人なので小さくてもいいだろうし。
* access-controlはLAN内からのみ許可するようにしました。

/etc/unbound/local.d/example.com.confにlocal-dataの設定を書きます。
```
local-data: "example.com A 192.168.11.103"
```

あとは、iptablesでUDPのポート53を開けて、unboundのサービスを起動してchkconfigで自動起動をオンにすればOKです。

## クライアントの設定

Linuxの場合は、
/etc/sysconfig/networkに
```
DNS1="192.168.11.103"
```
と書いて、以下のコマンドで反映します。

```
service network restart
```

Macでは[システム環境設定]/[ネットワーク]→[詳細]ボタン→[DNS]タブで「192.168.11.103」を指定すれば設定出来ます。

が、iPhoneでDNSの設定が出来ないようなので(ちょっと試しただけで未調査)、どうせならルータ側で設定したいなーと思ったら、
[ONU一体型ひかり電話ルータ PR-400KI のDNS設定 - matshのふらふら日記](http://matsh.jp/d/0365)
というブログ記事を見つけました。

[詳細設定]-[DNS設定]の[ローカルドメイン問合せテーブル]で、ドメイン名(ワイルドカード指定可能)に対してエントリを追加してドメイン毎にプライマリDNSサーバとセカンダリDNSサーバを登録できるようになっています。

ただし、サーバの指定がIPv6形式のみ受け付けるようになっています。IPv4射影アドレスをIPv6形式で指定すると解決するとのことでした。
[IPv6 IPv4射影アドレス とは](http://kaworu.jpn.org/kaworu/2010-08-16-1.php)

DNSサーバのIPv4アドレス192.168.11.103の各オクテットを16進数に変換すると
192→C0、168→A8、11→B、103→67となり、IPv4射影アドレスは
::FFFF:C0A8:B67
となりました。

これでMacでもiPhoneでもexample.comで参照できるようになりました。快適！
