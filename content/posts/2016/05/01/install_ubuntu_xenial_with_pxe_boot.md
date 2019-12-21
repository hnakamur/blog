+++
Categories = []
Description = ""
Tags = ["ubuntu", "macos", "pxe-boot"]
date = "2016-05-01T22:36:19+09:00"
title = "MacをPXEサーバにしてExpress5800/S70タイプRBにUbuntu16.04をインストールしてみた"

+++
## 背景
Goで書いたプログラムをMacBook Pro上で負荷試験をしていたら、ビーチボールカーソルが回りっぱなしになって大変でした。そういえば、負荷試験するときは極力余計なプロセスを止めて外界の影響を受けない状態でやるべきという話を思い出しました。

そこで5年前に買ったけど、ここ2年は全く電源を入れていなかった自宅サーバを再び活用することにしました。起動してみるとCentOS 6.4が入っていました。せっかくなので人生初のPXEブートでUbuntu 16.04をインストールしてみました。ということで自分用メモです。

## サーバハードウェア構成

ハードウェアの情報は有志のまとめWikiに詳しく載っています。
[NEC Express5800／S70 タイプRB - usyWiki](http://pc.usy.jp/wiki/index.php?NEC%20Express5800%A1%BFS70%20%A5%BF%A5%A4%A5%D7RB)

私のExpress5800の構成は以下の通りです。

* Express5800/S70タイプRB
* CPU: Intel Pentium G6950 (2.8GHz)
* RAM: 16GBに増設済み
* SSD: Intel SSDSA2M160G2GC (換装済み)
* BIOS: Phoenix

## MacをPXEサーバにする

今まではこの方法を知らなくてPXEブートを諦めていたのですが、 [MacをPXEサーバーにする - Qiita](http://qiita.com/honeniq/items/d020368ea31b2f052a12) と [MacOSXをPXEブートサーバーにしてLinuxのインストールに使う | C-RTX BLOG](http://c-rtx.com/2015/09/21/macosx-pxe-server/) の記事のおかげで私にも出来ました。ありがとうございます！

### 環境

* MacBook Pro (Retina, Mid 2012)
* OS X El Capitan
* tftpd (OS X 標準)
* bootpd (OS X 標準)

### 構成図

```
+--------+  Ethernet   +-------------+  Wi-Fi   +----------+ 
| Server | ----------> | MacBook Pro | -------> | Wi-Fi AP | -----> Internet
+--------+             +-------------+          +----------+
```

### tftpdの起動とnetbootのファイル配置

tftpd起動

```
$ sudo launchctl load -w /System/Library/LaunchDaemons/tftp.plist
```

osx上でのtftpについて私はよく知らないのですが、起動後

```
sudo ps auxww | grep tftp
```

としてもヒットしませんでした。

以下のように実際に繋いでみて試すか、

```
$ tftp
tftp> quit
```

lsofで確認すれば大丈夫でした。後者は [Macでtftpサーバを起動 - Qiita](http://qiita.com/tukiyo3/items/c9ca4bc6c62e78e80ae3) を参考にしました。

```
$ sudo lsof -i:69
COMMAND PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
launchd   1 root   42u  IPv6 0x4d07726546506a3f      0t0  UDP *:tftp
launchd   1 root   47u  IPv4 0x4d0772654650a3ff      0t0  UDP *:tftp
launchd   1 root   48u  IPv4 0x4d0772654650a3ff      0t0  UDP *:tftp
launchd   1 root   49u  IPv6 0x4d07726546506a3f      0t0  UDP *:tftp
```

Ubuntuのセットアップが終わった後は以下のコマンドでtftpdを停止します。

```
sudo launchctl unload /System/Library/LaunchDaemons/tftp.plist
```

/private/tftpboot/ 以下にUbuntuのネットワークインストールに必要なファイルを配置します。

最初は http://archive.ubuntu.com/ubuntu/dists/xenial/main/installer-amd64/current/images/netboot/ から pxelinux.0 をダウンロードして置いていたのですが、ブートしてみると他のファイルも必要なことがわかりました。

試行錯誤した結果、 [日本国内のダウンロードサイト | Ubuntu Japanese Team](https://www.ubuntulinux.jp/ubuntu/mirrors) に載っているミラーの1つの ftp://ftp.kddilabs.jp/Linux/packages/ubuntu/archive/dists/xenial/main/installer-amd64/current/images/netboot/ から netboot.tar.gz をダウンロードして展開すれば大丈夫でした。

### bootpd

私がよくわかっていなくて、ここはちょっと苦労しました。まず、インターネット共有を切にした状態では /etc/bootpd.plist は以下のようになっていました。

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>bootp_enabled</key>
	<false/>
	<key>detect_other_dhcp_server</key>
	<false/>
	<key>dhcp_enabled</key>
	<false/>
	<key>dhcp_ignore_client_identifier</key>
	<true/>
	<key>use_server_config_for_dhcp_options</key>
	<false/>
</dict>
</plist>
```

「システム環境設定」→「共有」と進んで「インターネット共有」のチェックボックスをオンにしようとしたのですが、画面中央に「接続を共有するためのポートを選択していないため、インターネット共有を開始できません。」と表示されていてオンにならない状態でした。

試行錯誤した結果、MacをWi-FiでWi-Fi AP (Time Capsule)に繋ぎつつ[Apple Thunderbolt - ギガビットEthernetアダプタ - Apple (日本)](http://www.apple.com/jp/shop/product/MD463ZM/A/apple-thunderbolt%E3%82%AE%E3%82%AC%E3%83%93%E3%83%83%E3%83%88ethernet%E3%82%A2%E3%83%80%E3%83%97%E3%82%BF?afid=p238%7CsKTonmsKf-dc_mtid_18707vxu38484_pcrid_96182712077_&cid=aos-jp-kwg-pla-btb-product-MD463ZM/A)でも有線で繋いだ状態で、「共有する接続経路」で「Wi-Fi」を選び、「相手のコンピュータでのポート」で「Thunderbolt Ethernet」にチェックをつけた状態で「インターネット共有」にチェックをつけるとうまくいきました。

この時はよく分かってなかったのですが、参考にした記事にもある通り、Express 5800のLANケーブルはMacに繋ぐのが正しいです。上記の構成図も正しい構成のほうを書いています。

この状態で5秒ぐらいすると /etc/bootpd.plist が以下のように変更されました。

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Subnets</key>
	<array>
		<dict>
			<key>_creator</key>
			<string>com.apple.NetworkSharing</string>
			<key>allocate</key>
			<true/>
			<key>dhcp_domain_name_server</key>
			<array>
				<string>192.168.2.1</string>
			</array>
			<key>dhcp_router</key>
			<string>192.168.2.1</string>
			<key>interface</key>
			<string>bridge100</string>
			<key>lease_max</key>
			<integer>86400</integer>
			<key>lease_min</key>
			<integer>86400</integer>
			<key>name</key>
			<string>192.168.2/24</string>
			<key>net_address</key>
			<string>192.168.2.0</string>
			<key>net_mask</key>
			<string>255.255.255.0</string>
			<key>net_range</key>
			<array>
				<string>192.168.2.2</string>
				<string>192.168.2.254</string>
			</array>
		</dict>
	</array>
	<key>bootp_enabled</key>
	<false/>
	<key>detect_other_dhcp_server</key>
	<array>
		<string>bridge100</string>
	</array>
	<key>dhcp_enabled</key>
	<array>
		<string>bridge100</string>
	</array>
	<key>dhcp_ignore_client_identifier</key>
	<true/>
	<key>ignore_allow_deny</key>
	<array>
		<string>bridge100</string>
	</array>
	<key>use_server_config_for_dhcp_options</key>
	<false/>
</dict>
</plist>
```

Subnets キーの `</dict>` の前に以下の設定を追加します。 `cHhlbGludXguMAA=` は `pxelinux.0` をBase64エンコーディングした値です。

```
		<key>dhcp_option_66</key>
		<string>192.168.2.1</string>
		<key>dhcp_option_67</key>
		<data>cHhlbGludXguMAA=</data>
```

ここで追記した内容を反映させる際に、「システム環境設定」の「共有」で「インターネット共有」をオフ→オンにすると設定ファイルが元に戻されてしまってダメでした。

/etc/bootpd.plist を書き換えた後、以下のようにコマンドで bootpd を再起動すると大丈夫でした。

```
sudo launchctl unload /System/Library/LaunchDaemons/bootps.plist
sudo launchctl load -w /System/Library/LaunchDaemons/bootps.plist
```

/etc/bootpub を作成・編集して固定アサインの設定もやっておきました。
が、今思えば私はこれはいらないかなと思います。後述の通り、ネットワークブートが終わったらLANケーブルを繋ぎ変えて、Wi-Fi APのDHCPを使ってIPアドレスを取得してその後のインストールを行うので。

```
# hostname      hwtype  hwaddr              ipaddr          bootfile
client1         1       01:02:03:04:05:06   192.168.2.11    pxelinux.0
```

hwaddrの値は実際には事前に Express 5800 で `ip a` で調べたMACアドレスに書き換えました。PXEブート中にもMACアドレスが表示されていたのでそれを見て書き換えるのでも良さそうです。

Macで `ifconfig` を実行すると `bridge100` というのが作られていました。最初は `bridge0` というのが作られたのですが、このときは接続を間違えていて ServerをWi-Fi APに有線でつなぎ、MacはWi-Fi APにWi-Fiと有線でつないでいました。

その後上記の構成図の配線に修正したりしているうちに `bridge0` とは別に `bridge100` というのが作られていました。

`ifconfig` の結果は以下のようになっていました。

```
$ ifconfig
...(snip)...
bridge100: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
        options=3<RXCSUM,TXCSUM>
        ether ba:f6:b1:71:3c:64
        inet 192.168.2.1 netmask 0xffffff00 broadcast 192.168.2.255
        inet6 fe80::b8f6:b1ff:fe71:3c64%bridge100 prefixlen 64 scopeid 0x12
        Configuration:
                id 0:0:0:0:0:0 priority 0 hellotime 0 fwddelay 0
                maxage 0 holdcnt 0 proto stp maxaddr 100 timeout 1200
                root id 0:0:0:0:0:0 priority 0 ifcost 0 port 0
                ipfilter disabled flags 0x2
        member: en4 flags=3<LEARNING,DISCOVER>
                ifmaxaddr 0 port 17 priority 0 path cost 0
        nd6 options=1<PERFORMNUD>
        media: autoselect
        status: active
```


### OS Xのファイアウォールを切る必要はない

初回はたぶんファイアウォールは切る必要があるだろうと思って切っておきました。

「システム環境設定」→「セキュリティとプライバシー」→「ファイアウォール」タブ
左下の「変更するにはカギをクリックします」を押してパスワードを入力し、
「ファイアウォールを切にする」ボタンを押してオフにしました。

Ubuntuのインストールが終わったら「ファイアウォールを入にする」ボタンを押して
オンに戻しておきます。

が、2回目の検証でファイアウォールを切らなくても大丈夫なことがわかりました。

### Phoenix BIOSでPXEブートを有効にする

[BIOS 設定方法](http://changineer.info/server/server_hardware_management/server_hardware_bios.html#Phoenix_BIOS_8211BIOS_PXE_boot)を参考にしました。

Express 5800を再起動し、起動時に[F2]キーを押してPhoenix BIOSの設定画面に入ります。カーソルキーの左右で[Boot]メニューを選びます。私はPXEブートを無効にしていたので、[PCI BEV]は画面下部の[Excluded from boot order:]のほうにありました。カーソルキーの上下で[PCI BEV]を選んでxキーを押し、画面上部の[Boot priority order:]のほうに移動します。
その後テンキーの+を押して[PCI BEV]を1番上に持ってきます。購入時に同梱されていた日本語キーボードを使っているのですがフルキーの-は効くのですが+ (Shift+;)は効きませんでした。

なお、一旦有効にした後は[PCI BEV]の項目は[PCI BEV: IBA GE Slot 00C8 v1352]という表示になっていました。

変更したら[F10]を押してBIOSの設定を保存して終了します。

Ubuntuの設定が終わったら[PCI BEV]を[Excluded from boot order:]のほうに戻しておきます。

### PXEブートでUbuntuのインストール

Express 5800を再起動すると、Ubuntuのインストーラが起動しました。
予めMacで `tail -f /var/log/system.log | grep DHCP` を実行しておくとDHCPのログが確認できました。

```
$ tail -f /var/log/system.log | grep DHCP
May  2 00:55:44 machostname bootpd[8589]: DHCP REQUEST [bridge100]: 1,01:02:03:04:05:06
May  2 00:56:37 machostname bootpd[8589]: DHCP DISCOVER [bridge100]: 1,01:02:03:04:05:06
...
```

実際には `machostname` の部分はMacBook Proのホスト名が、 `01:02:03:04:05:06` の部分は Express 5800 のネットワークカードのMACアドレスが出力されていますが、セキュリティ上伏せています。

後は普通にUbuntuのインストーラに沿ってインストールすれば良いのですが、インストーラが起動した後はMacを経由せずに通信するほうが効率が良いので、Express 5800とMacをつないでいるLANケーブルをMacから外してWi-Fi APに繋ぎ直します。

```
+--------+  Ethernet   +----------+ 
| Server | ----------> | Wi-Fi AP | -----> Internet
+--------+             +----------+
```

インストーラの「Ubuntu アーカイブのミラーを選択」のところで「戻る」を選び、
「Ubuntu インストーラメインメニュー」で「ネットワークの設定」を選びます。
するとDHCPでIPアドレスを再取得してくれます。

### Ubuntuのセットアップ

以下はUbuntuのセットアップのメモです。

ホームパーティションの暗号化とパーティショニングの暗号化LVMを選んでみました。
後者を選ぶと暗号化用のパスフレーズを求められるので設定します。設定するとサーバの起動時にパスフレーズの入力が必要になります。

インストールするソフトウェアの選択では以下の3つを選びました。

* 標準システムユーティリティ
* OpenSSH server
* Basic Ubuntu server

GRUBブートローダはSSDのデバイスにインストールしました。

タイムゾーンは日本にし、システム時間はUTCにしました。

## おわりに

PXEブート便利です！
