+++
title="macOS→VagrantのUbuntu→LXDコンテナへのポートフォワーディング"
date = "2018-07-05T16:20:00+09:00"
tags = ["lxd", "macOS", "vagrant", "ubuntu"]
categories = ["blog"]
+++


# はじめに

[VagrantでUbuntu 18.04 LTSとLXDをインストールする手順](/blog/2018/07/05/install-lxd-on-ubuntu-18.04-lts-on-vagrant/) で構築したLXDの環境で、macOS→VagrantのUbuntu→LXDコンテナへのポートフォワーディングをしたのでメモです。

今回はhttpsの443番ポートで試しました。

# macOSからVagrantへのポートフォワーディング

基本的にはVagrantの公式ドキュメント
[Forwarded Ports - Networking - Vagrant by HashiCorp](https://www.vagrantup.com/docs/networking/forwarded_ports.html)
のように `forwarded_port` という設定をVagrantfileに追加すればOKです。

ただし、ホストでバインドするポートをhttpの80番やhttpsの443番のように1024番以下にするときは、すんなりとは行きません。上記のページの Options Reference の host の説明によると rootで `vagrant up` を実行すれば可能ですが、推奨されないとのことです。

ということで guestは443、hostは8443 と指定しました。

[OSX における Vagrant 80番ポートフォワーディング - Qiita](https://qiita.com/hidekuro/items/a94025956a6fa5d5494f) ではvagrant-triggersというプラグインを使ってVMの起動・停止時にmacOSの `pfctl` コマンドを実行して、ホストのローカルホストでポートフォワーディングすると良いらしいです。

今回はちょっと試すだけだったのでvagrant-triggersは使わず、手動で `pfctl` を実行しました。

[Mac pfctl Port Forwarding | Sal Ferrarello](https://salferrarello.com/mac-pfctl-port-forwarding/)
も参考にして macOS で以下のコマンドを実行して 443から8443 へのポートフォワードを行いました。

```console
echo "
rdr pass inet proto tcp from any to any port 443 -> 127.0.0.1 port 8443
" | sudo pfctl -ef -
```

ポートフォワードの設定確認は以下のコマンドで行います。

```console
sudo pfctl -s nat
```

ポートフォワードの削除は以下のコマンドで行います。

```console
sudo pfctl -F all -f /etc/pf.conf
```

`pfctl` とVagrantのforwarded_portの合わせ技で macOS のローカルホストの443番ポートからVagrant上のUbuntuの443番ポートへのポートフォワードができるようになりました。


# Ubuntuのファイアウォールで443番ポートを許可

Ubuntuには `ufw` というファイアウォールの管理用コマンドがあります。が、慣れているということで今回は iptables を使うことにしました。

まず ufw の状態を確認してみると無効になっていました。

```console
$ sudo ufw status
Status: inactive
```

以下のコマンドで `iptables-persistent` をインストールします。

```console
sudo apt install iptables-persistent
```

CUIのダイアログでIPv4とIPv6のファイアウォールの現在の設定を保存するか聞かれるのではいと答えます。
するとそれぞれ `/etc/iptables/rules.v4` と `/etc/iptables/rules.v6` に保存されます。

このうち前者を編集します。

```console
sudo vim /etc/iptables/rules.v4
```

`*filter` セクションの `-A INPUT` の行が複数ありますが最後の後に以下の行を追加します。

```text
-A INPUT -i lxdbr0 -p tcp -m tcp --dport 443 -j ACCEPT
```

保存してvimを抜けた後、以下のコマンドを実行して反映します。

```console
sudo apt iptables-restore < /etc/iptables/rules.v4
```

以下のコマンドを実行して指定通り反映されたかを確認します。

```console
sudo apt iptables-save
```

# UbuntuからLXDコンテナへのポートフォワーディング

[LXDのproxyを使ってポートフォワーディング](/blog/2018/07/05/port-forwarding-using-lxd-proxy/) の手順で設定してください。


# 動作確認

これでmacOS上のブラウザで https://localhost にアクセスするとLXDコンテナの443番ポートにアクセスできるようになりました。
まとめると macOS 443→ macOS 8443→ Vagrant 443→LXD 443 という4段フォワードとなっています。
