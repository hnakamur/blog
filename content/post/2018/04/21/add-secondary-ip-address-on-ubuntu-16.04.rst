Ubuntu16.04でセカンダリIPアドレス追加
#####################################

:date: 2018-04-21 12:30
:tags: ubuntu, linux, network
:category: blog
:slug: 2018/04/21/add-secondary-ip-address-on-ubuntu-16.04

`networking - How do I add an additional IP address to /etc/network/interfaces? - Ask Ubuntu <https://askubuntu.com/questions/313877/how-do-i-add-an-additional-ip-address-to-etc-network-interfaces?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa>`_ とそこでコメントされていた
`NetworkConfiguration - Debian Wiki の iproute2 method <https://wiki.debian.org/NetworkConfiguration#iproute2_method>`__
を見て試してみたメモです。

`NetworkConfiguration - Debian Wiki の iproute2 method <https://wiki.debian.org/NetworkConfiguration#iproute2_method>`__ で書かれていたのは :code:`/etc/network/interfaces` で同じネットワークインタフェース名に対して :code:`iface` セクションを繰り返して複数書くという方式です。ドライバとハードウェアの組み合わせによっては正しく動かず危険とのことなので要注意です。

:code:`/etc/network/interfaces` を管理者権限で編集します。

.. code-block:: console

	sudo vim /etc/network/interfaces

私の手元の環境で :code:`enp0s25` の設定を以下のようにして試してみました。

.. code-block:: text

	auto enp0s25
	iface enp0s25 inet static
	    address 192.168.2.200
	    netmask 255.255.255.0
	    gateway 192.168.2.1
	    dns-nameservers 192.168.2.1
	iface enp0s25 inet static
	    address 192.168.2.203
	    netmask 255.255.255.0

ネットワーク再起動。

.. code-block:: console

	sudo systemctl restart networking

IPアドレスは期待通りついていました。

.. code-block:: console

	$ ip a s dev enp0s25 | grep 'inet '
	    inet 192.168.2.200/24 brd 192.168.2.255 scope global enp0s25
	    inet 192.168.2.203/24 brd 192.168.2.255 scope global secondary enp0s25

ですが、DNSの名前解決ができない状態でした。
具体的には :code:`ping 8.8.8.8` はOKですが :code:`ping ping google-public-dns-a.google.com` はNGでした。

`NetworkConfiguration - Debian Wiki の iproute2 method <https://wiki.debian.org/NetworkConfiguration#iproute2_method>`__ のManual approachを試してみるとこちらでは問題なかったです。
が、 :code:`label $IFACE:0` と :code:`:0` 付きだと Legacy method と実質同じだったりしないのかなと気になりました。

:code:`:0` を取って試してみようかとも思ったのですが、ふと思いついて以下のように2個めの :code:`iface` にも :code:`dns-nameservers` を書くようにしてみたら、DNSの名前解決もできました。

.. code-block:: text

	auto enp0s25
	iface enp0s25 inet static
	    address 192.168.2.200
	    netmask 255.255.255.0
	    gateway 192.168.2.1
	    dns-nameservers 192.168.2.1
	iface enp0s25 inet static
	    address 192.168.2.203
	    netmask 255.255.255.0
	    dns-nameservers 192.168.2.1

正しい方法かは不明ですが、とりあえず手元の環境ではこれでできたということでメモでした。
