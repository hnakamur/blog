Ubuntu 16.04をルーター化
########################

:date: 2018-04-23 00:30
:tags: ubuntu, network
:category: blog
:slug: 2018/04/23/setup-router-on-ubuntu16.04

はじめに
--------

LANポートが2つついているFUJITSU PRIMERGY TX1310 M1でUbuntu 16.04をルーター化したメモです。

`Ubuntu 14.04のルーター化 - Qiita <https://qiita.com/koshilife/items/2fa1436248f1d4938861>`_ を参考にしました。

ネットワークインターフェースの定義
----------------------------------

* enp0s25: 外に繋がっているインタフェース
* enp2s0: 新規で切るセグメント

:code:`/etc/network/interfaces` で以下のように設定しました。

.. code-block:: text

	auto enp0s25
	iface enp0s25 inet static
	    address 192.168.2.200
	    netmask 255.255.255.0
	    gateway 192.168.2.1
	    dns-nameservers 192.168.2.1
	iface enp0s25 inet6 auto

	auto enp2s0
	iface enp2s0 inet static
	    address 192.168.3.1
	    netmask 255.255.255.0
	    gateway 192.168.2.1
	iface enp2s0 inet6 auto

IPフォワードはすでに有効でした
------------------------------

:code:`/etc/sysctl.conf` では :code:`net.ipv4.ip_forward` の設定はコメントアウトされていました。

.. code-block:: console

	$ grep net.ipv4.ip_forward /etc/sysctl.conf
	#net.ipv4.ip_forward=1

ですが設定自体は有効になっていました。

.. code-block:: console

	$ sysctl net.ipv4.ip_forward
	net.ipv4.ip_forward = 1

以前に `Linux Containers - LXD - Getting started - command line <https://linuxcontainers.org/lxd/getting-started-cli/#snap-package-archlinux-debian-fedora-opensuse-and-ubuntu>`_ の手順でsnapパッケージでLXDをインストールしていたので、そのときに自動で設定されたのかどこかで設定したのかもしれません。

IPマスカレードの設定
--------------------

:code:`sudo iptables-save` で現状を確認するとlxd用の設定は :code:`-m comment --comment` で設定にコメントが
ついていたので、真似してコメント付きで設定してみました。

.. code-block:: console

	sudo /sbin/iptables -t nat -A POSTROUTING -s 192.168.3.0/255.255.255.0 \
	  -m comment --comment "Route back from outer network to enp2s0" -j MASQUERADE

実行したら :code:`sudo iptables-save` で結果を確認します。


設定を間違えていたなどで削除する場合は、追加時の :code:`-A` オプションを :code:`-D` に変えて
以下のようにします。

.. code-block:: console

	sudo /sbin/iptables -t nat -D POSTROUTING -s 192.168.3.0/255.255.255.0 \
	  -m comment --comment "Route back from outer network to enp2s0" -j MASQUERADE

iptables-persistentのインストールと設定保存
-------------------------------------------

iptablesのルールを保存しておいて起動時に読み込むために iptables-persistent というパッケージが用意されているのでそれをインストールします。

.. code-block:: console

	sudo apt install iptables-persistent

:code:`dpkg -L iptables-persistent` でファイルリストを確認すると以下の2つのファイルが含まれていました。

* /usr/share/netfilter-persistent/plugins.d/15-ip4tables
* /usr/share/netfilter-persistent/plugins.d/25-ip6tables

中身を確認するとシェルスクリプトになっていて、それぞれ :code:`/etc/iptables/rules.v4` , :code:`/etc/iptables/rues.v6` を読み込むようになっていました。

以下のコマンドで IPv4 の設定を保存しました。

.. code-block:: console

	sudo iptables-save -c | sudo tee /etc/iptables/rules.v4
