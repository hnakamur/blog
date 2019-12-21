+++
title="Ubuntu 16.04上にUbuntu 18.04のPXEブートサーバをセットアップ"
date = "2018-04-24T01:00:00+09:00"
tags = ["ubuntu"]
categories = ["blog"]
+++


## はじめに

[Ubuntu 16.04をルーター化](/blog/2018/04/23/setup-router-on-ubuntu16.04/) したところに
Ubuntu 18.04のPXEブートサーバをセットアップしたメモです。

Ubuntu 18.04はリリース前の
[2018-04-21版](http://archive.ubuntu.com/ubuntu/dists/bionic/main/installer-amd64/20101020ubuntu538/)
を使いました。

手順は
[Ubuntu 16.04 / Debian 8: PXEブートサーバをインストールしてネットワークインストール環境を整える - Narrow Escape](https://www.hiroom2.com/2016/05/05/ubuntu-16-04-debian-8%E3%81%ABpxe%E3%83%96%E3%83%BC%E3%83%88%E3%82%B5%E3%83%BC%E3%83%90%E3%82%92%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E3%81%97%E3%81%A6%E3%83%8D%E3%83%83%E3%83%88%E3%83%AF%E3%83%BC%E3%82%AF%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E7%92%B0%E5%A2%83%E3%82%92%E6%95%B4%E3%81%88%E3%82%8B/)
を参考にしましたが、preseedは今回は使わないようにしました。

## tftpサーバのインストールと起動

`tftpd-hpa` パッケージをインストール。

```console
sudo apt install tftpd-hpa
```

うろ覚えですが、インストールして状態確認すると、起動して自動起動も有効になっていたと思います。

```console
systemctl status tftpd-hpa
```

## dhcpサーバのインストールと起動

`isc-dhcp-server` パッケージをインストール。

```console
sudo apt install isc-dhcp-server
```

設定ファイル `/etc/dhcp/dhcpd.conf` に自分の環境に応じた設定を追記。
`hardware ethernet` の後のMACアドレス `xx:xx:xx:xx:xx:xx` は実際の値に置き換えてください。
PXEブートのときにコンソールに表示されていたのでそれを見ながら設定しました。
事前に設定するならBIOSで確認すれば良さそうです。

```text
subnet 192.168.3.0 netmask 255.255.255.0 {
  option domain-name-servers 192.168.2.1;
  option routers 192.168.3.1;
  filename "pxelinux.0";
}

host ubuntu-18.04-pxeboot {
  hardware ethernet xx:xx:xx:xx:xx:xx;
  fixed-address 192.168.3.2;
}
```

コマンドで追記にするなら以下の2つのどちらかで。後者のほうがクォートが不要というメリットがあります。

```console
sudo sh -c 'cat <<EOF >> /etc/dhcp/dhcpd.conf
subnet 192.168.3.0 netmask 255.255.255.0 {
  option domain-name-servers 192.168.2.1;
  option routers 192.168.3.1;
  filename "pxelinux.0";
}

host ubuntu-18.04-pxeboot {
  hardware ethernet xx:xx:xx:xx:xx:xx;
  fixed-address 192.168.3.2;
}
EOF
'
```

.. code-block:: console

	sudo cat <<EOF | sudo tee -a /etc/dhcp/dhcpd.conf > /dev/null
	subnet 192.168.3.0 netmask 255.255.255.0 {
	  option domain-name-servers 192.168.2.1;
	  option routers 192.168.3.1;
	  filename "pxelinux.0";
	}

	host ubuntu-18.04-pxeboot {
	  hardware ethernet xx:xx:xx:xx:xx:xx;
	  fixed-address 192.168.3.2;
	}
	EOF

こちらもうろ覚えですが、起動と自動起動有効化はすでにされていたと思うので、再起動して設定変更を反映しました。

```console
sudo systemctl restart isc-dhcp-server
```

## Ubuntu 18.04のネットブートイメージの取得と設置

参考にした記事ではpreseedを使うためにネットブートイメージのtarballを取得・展開した後、小分けにコピーしていましたが、preseed無しなら単にtarballをtfptd-hpaの公開ディレクトリ `/var/lib/tftpboot` に展開して所有者を `tftp` にするだけでOKでした。

```console
curl -LO http://archive.ubuntu.com/ubuntu/dists/bionic/main/installer-amd64/current/images/netboot/netboot.tar.gz
sudo tar xf netboot.tar.gz -C /var/lib/tftpboot
sudo chown -R tftp:tftp /var/lib/tftpboot
