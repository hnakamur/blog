+++
Categories = []
Description = ""
Tags = ["ddns", "ubuntu"]
date = "2016-05-02T09:39:31+09:00"
title = "Ubuntu 16.04でNo-IPのダイナミックDNSサービスを使ってみた"

+++
## 背景
[MacをPXEサーバにしてExpress5800/S70タイプRBにUbuntu16.04をインストールしてみた · hnakamur's blog at github](/blog/2016/05/01/install_ubuntu_xenial_with_pxe_boot/)で自宅サーバを起動したのですが、固定グローバルIPアドレスは持っていないので、ダイナミックDNS (DDNS) サービスを使うことにしました。

[DDNSの無料サービスでオススメな３つの「ieServer」「mydns」「No-IP」の特徴と利用手順をまとめてみた](http://viral-community.com/other-it/ddns-praise-service-2065/)を参考に「No-IP」を使ってみました。

## アカウント登録

https://www.noip.com/ でメールアドレス、ユーザ名、パスワードを入力してサインアップし、確認のHTMLメールが届いたら[Activate Account]ボタンをクリックすればOKです。

## ホストの登録

https://www.noip.com/ の右上の[Sign In]を押し、ユーザ名かメールアドレスとパスワードを入力してサインインします。サインイン後は https://my.noip.com/ に遷移します。

ホストの登録は新サイトの画面左の[Dashboard]を選んで、画面中央の[Quick Add]で[Hostname]を希望のホスト名を入力、[Doman]で使いたいドメインを選択して[Add Hostname]ボタンを押せばOKです。

あるいは画面左の[Dynamic DNS]の[Hostnames]メニューを選び、[Add Hostname]ボタンを押す方法でもOKです。この場合は[Add Hostname]というタイトルのポップアップが開きます。

[Hostname]に希望のホスト名を入力し、[Domain]は使いたいドメインを選びます。
[Record Type]はAのままでOKで、[IPv4 Address]にも自動で現在のグローバルIPアドレスが入力されているのでそのままでOKです。[Add Hostname]ボタンを押すと追加完了です。

なお、試していませんが、[Record Type]の[More Records]ボタンを押すと、以下の4つのラジオボタンが表示されました。

* DNS Host (A)
* DNS Alias (CNAME)
* Web Redirect
* AAAA (IPv6)

また、その下には "Manage your Round Robin, TXT, SRV and DKIM records." という文が書かれており、 "Manage" の部分がリンクになっていました。これを押すと https://www.noip.com/members/dns/ のManage Hostsページに遷移しました。 no-ip は管理画面をリニューアル中で、こちらは旧画面のようです。 https://my.noip.com/#!/ の画面上部にある [Use Old Site] というリンクでも旧サイトのManage Hostsページが開きました。

新サイトの[Dynamic DNS]の[Hostnames]メニューで画面右に "Free Hostnames expire every 30 days. Enhanced Hostnames never expire. Upgrade to Enhanced" と書いてあるのですが、 [Why did my free hostname expire or get deleted? | Support | No-IP](http://www.noip.com/support/faq/frequently-asked-questions/why-did-my-free-hostname-expire-or-get-deleted/) の説明によれば無料サービスでも30日毎に更新していれば消えないようです。

## IPアドレス自動更新用のクライアントnoip2をセットアップ

http://www.noip.com/ の画面上部の [Download] リンクをクリックすると、アクセスしているブラウザからOSを自動判定して、そのOS用のクライアントのダウンロードページが開きます。私の場合は Dynamic DNS Update Client (DUC) for Mac のページが開きました。

下の方にスクロールして [Other Downloads] の [Linux] をクリックして [Dynamic DNS Update Client (DUC) for Linux - No-IP](https://www.noip.com/download?page=linux) を開きます。

Installation のセクションに "UBUNTU USERS: You may install this with the apt-get command, see this guide" という文があり guide のリンクをクリックすると [How to Install the Linux Dynamic Update Client on Ubuntu](http://www.noip.com/support/knowledgebase/installing-the-linux-dynamic-update-client-on-ubuntu/) に遷移しました。このページの手順に従ってセットアップすればOKでした。

```
sudo -s
```

でパスワードを入力してrootになって以下のコマンドを実行します。

```
cd /usr/local/src
wget http://www.no-ip.com/client/linux/noip-duc-linux.tar.gz
tar xf noip-duc-linux.tar.gz
cd noip-2.1.9-1/
make install
```

noip-2.1.9-1 のディレクトリ内を見るとソースファイルは noip2.c の1つでした。中を見てみるとライセンスはGPLv2 or laterです。ざっと見た感じでは不正な通信はしてなさそうでした。

インストール後以下のコマンドを実行して設定ファイルを作成します。以下のコマンドは全てrootで実行しています。

```
/usr/local/bin/noip2 -C
```

プロンプトが表示されたらNo-IPのユーザ名、パスワードと登録したホスト名を入力します。すると /usr/local/etc/no-ip2.conf に設定ファイルが作られます。viで中を見てみると一部テキスト、一部バイナリのファイルでした。

あとは `/usr/local/bin/noip2` でデーモンが起動するのですが、systemdのサービスとして登録したいので、unitファイルを作りました。

ソースのディレクトリにdebian, gentoo, redhat用のinit.d用のスクリプトとmac用の自動起動スクリプトがありました。 `redhat.noip.sh` を見ると、起動は `/usr/local/bin/noip2` で、終了は `killproc noip2 -TERM` で行っていました。

Ubuntuで試したら `killproc` は無かったので `killall` で代用しました。

以下のコマンドでunitファイルを作成します。

```
cat <<'EOF' > /etc/systemd/system/noip2.service
[Unit]
Description=No-IP.com DDNS client
After=network.target auditd.service

[Service]
ExecStart=/usr/local/bin/noip2
ExecStop=/usr/bin/killall -TERM /usr/local/bin/noip2
Restart=on-failure
Type=forking

[Install]
WantedBy=multi-user.target
EOF
```

作成したファイルをsystemdに読み込ませます。

```
systemctl daemon-reload
```

以下のコマンドでサービスの起動とOS起動時の自動起動設定を行います。

```
systemctl start noip2
systemctl enable noip2
```

ちなみに、 `mac.osx.startup` では `noip2 -S` の出力からpidを取得して `noip -K $pid` で停止していました。こんな感じです。

```
    for i in `noip2 -S 2>&1 | grep Process | awk '{print $2}' | tr -d ','`
      do
        noip2 -K $i
      done
```

journalctlでログを見てみると以下のようなログが出ていました。

```
$ sudo journalctl | grep noip2
 5月 02 10:54:07 express noip2[1082]: v2.1.9 daemon started with NAT enabled
 5月 02 10:54:07 express noip2[1082]: xxxx.ddns.net was already set to xx.xx.xx.xx.
```

実際はxxxx.ddns.net はNo-IPで登録したホスト名と選択したドメインでxx.xx.xx.xxは自宅サーバのグローバルIPアドレスが出力されていましたが、セキュリティ上伏せています。

## ポートフォワーディング設定

### Ubuntuサーバを固定IPに設定

変更前の `/etc/network/interfaces` は以下のようになっていました。

```
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto enp0s25
iface enp0s25 inet dhcp
```

`enp0s25` の設定を [Static IP Address Assignment](https://help.ubuntu.com/lts/serverguide/network-configuration.html#static-ip-addressing) を参考に固定IPにしました。

```
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto enp0s25
iface enp0s25 inet static
    address 192.168.0.201
    netmask 255.255.255.0
    gateway 192.168.0.1
    dns-nameservers 192.168.0.1
```

```
systemctl restart networking
```

で反映しました。

`ip a` で確認すると、変更前にDHCPで発行されたIPアドレス `192.168.0.9` と上記で設定した固定アドレス `192.168.0.201` の両方が表示されました。

sshで作業していたのですが、以下のコマンドで消そうとしたらハマりました。

```
root@express:/etc/network# ip a del 192.168.0.9 dev enp0s25
Warning: Executing wildcard deletion to stay compatible with old scripts.
         Explicitly specify the prefix length (192.168.0.9/32) to avoid this warning.
         This special behaviour is likely to disappear in further releases,
         fix your scripts!
packet_write_wait: Connection to 192.168.0.9: Broken pipe
```

コンソールからログインして `ip a` で確認すると `enp0s25` の `inet` の行は両方共消えていました。

```
sudo systemctl restart networking
```

でネットワークを再起動して `ip a` を実行すると `inet` の行は固定IPの1行になりました。

上で表示されたWarningによると、正しくは以下のようにするべきだったようです。

```
ip a del 192.168.0.9/32 dev enp0s25
```

### AirMacユーティリティでポートフォワーディング設定

Finderで「アプリケーション/ユーティリティ/AirMac ユーティリティ」を起動し、
Time Capsuleをクリックして開くポップアップの「編集」ボタンを押します。

「ネットワーク」タブで「ルーターモード」を「DHCPとNAX」にしておきます。
先程固定IPを `192.168.0.201` にしたのは「DHCPの範囲」が `192.168.0.2〜192.168.0.200` なので範囲外の値を選んだからです。なお、この範囲は「ネットワークオプション…」ボタンを押して変更可能です。

ポート設定の下の「+」ボタンを押すとポップアップが開くのでポートフォワーディングの設定を追加します。
ファイアウォール・エントリー・タイプは「IPv4ポートマッピング」固定で、ドロップダウンが disabled の状態になっていました。

プライベートIPアドレスは上記で設定したExpress5800の固定IPを入力します。

パブリックUDPポート、パブリックTCPポート、プライベートUDPポート、プライベートTCPポートにはフォワーデング元と先のポートを転送したい内容に応じて設定します。今回はTCPでsshのポートを指定しました。
なお、この記事では書いてないですが、パスワードアタック攻撃を回避するため事前にsshdは鍵認証のみ許可しパスワード認証は許可しない設定に変更しています。

ちなみに[ポートの範囲を指定して転送できるように AirMac Extreme (802.11n) ベースステーションを設定する](https://support.apple.com/kb/TA24799?locale=ja_JP&viewlocale=ja_JP)によるとポートの入力欄は空白を開けずに `XXX-YYY` のように書けば範囲も指定できるそうです。

設定を追加したら「保存」ボタンを押してポップアップを閉じ、「アップデート」ボタンで反映します。

## おわりに

これでインターネットから自宅サーバにsshでログイン出来るようになって便利になりました。
