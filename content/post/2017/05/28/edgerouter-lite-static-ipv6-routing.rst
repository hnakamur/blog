EdgeRouter LiteでIPv6の静的ルーティング設定
###########################################

:date: 2017-05-28 12:04
:tags: edgerouter
:category: blog
:slug: 2017/05/28/edgerouter-lite-static-ipv6-routing

はじめに
--------

`IIJmioひかりとEdgeRouter-LiteでDS-Liteを試してみた </blog/2017/05/13/tried-ds-lite-with-iij-mio-hikari-and-edgerouter-lite/>`_ の後、多少調整して一旦自分の希望通りの動きで落ち着いた状態になっていましたが、ブログに書いておかないと忘れそうなのでメモです。

IPv6の静的アドレスとルーティング設定
------------------------------------

`Edgerouter Lite-3でDS-Lite - Qiita <http://qiita.com/haccht/items/17ed2bed628d2fd17bea>`_ では

.. code-block:: text

    set interfaces ethernet eth0 ipv6 address autoconf

という設定でルータのWAN側のIPv6アドレスをホームゲートウェイからもらってルーティングも自動設定するようになっていました。

これは楽な反面、ルータ起動後10分程度しないとIPv6アドレスがつかないので、その間はIPv4 PPPoEにしないとインターネットに繋がりません。 ルータの再起動は約2分半かかるので、そこからさらに約10分かかるというのは中々辛い感じでした。

が、会社の同僚に教えてもらいつつ試行錯誤したところ、以下のように静的にアドレスとルートを設定すればOKでした。

.. code-block:: text

    delete interfaces ethernet eth0 ipv6 address autoconf
    set interfaces ethernet eth0 address 192.168.1.2/24
    set interfaces ethernet eth0 address '**:**:**:**:**:**:**:**/64'
    set protocols static route6 '::/0' next-hop 'fe80::***:****:****:****' interface eth0

:code:`set interfaces ethernet eth0 address` を2つ指定し、1つはIPv4アドレスでもう1つはIPv6アドレスにします。

また :code:`set protocols static route6 '::/0' next-hop` でホームゲートウェイのリンクローカルアドレスを指定します。

この2つのアドレスは autoconf で付与されたアドレスをメモっておいて、設定しました。

ルータのIPv6アドレスはホームゲートウェイの管理画面の「トップページ ＞ 情報 ＞ DHCPv6サーバ払い出し状況」のMACアドレスがルータのeth0になっている行（といってもこの1行しか表示されてないです）のIPv6プレフィックスの値で /60 を /64 に変えたものになっていました。

静的ルートに指定するホームゲートウェイのリンクローカルアドレスは
:code:`fe80::` の後にホームゲートウェイの管理画面の「トップページ ＞ 情報 ＞ DHCPv6サーバ払い出し状況」の「配布情報」の「DNSサーバアドレス」の16ビットグループの下位4個分をくっつけたアドレスになっていました。

ルータで :code:`ip -6 route` を実行すると最後の行に以下のように出力されてデフォルトゲートウェイにホームゲートウェイが設定できていることが確認できました。

.. code-block:: console

    $ ip -6 route
    …(略)…
    default via fe80::***:****:****:**** dev eth0  proto zebra  metric 1024

autoconfのときはprotoの値がra (router advertisement)となっていました。zebraというのはどういうものなのかは未調査です。

この設定により、ルータ再起動後すぐにIPv6で通信できるようになり快適になりました。

LAN内のIPv4の静的ルーティング設定
---------------------------------

この設定を入れる前はeth1につないだThinkPadからホームゲートウェイに通信できなくて、ホームゲートウェイの設定を確認・変更するときはLANケーブルでThinkPadをホームゲートウェイにいちいち繋いでいました。

が、ルータとホームゲートウェイで以下のようにIPv4の静的ルーティング設定を行うことで解決しました。

ルータには以下の設定を追加しました。

.. code-block:: text

    set protocols static table 1 interface-route 0.0.0.0/0 next-hop-interface pppoe0
    set protocols static table 1 interface-route 192.168.1.0/24 next-hop-interface eth0
    set protocols static table 2 interface-route 0.0.0.0/0 next-hop-interface v6tun0
    set protocols static table 2 interface-route 192.168.1.0/24 next-hop-interface eth0

ホームゲートウェイでは「トップページ ＞ 詳細設定 ＞ LAN側静的ルーティング設定」で「宛先IPアドレス/マスク長」を :code:`192.168.0.0/16` 、「ゲートウェイ」を :code:`192.168.1.2` とルータのeth0のIPv4に設定しました。

宛先のネットワークは 192.168.1.0～192.168.3.255 の範囲で十分なのですが、今後VLANとかで増やすかもしれないので上記の設定にしておきました。

自宅サーバに複数のIPv4アドレスを設定してIPv4 PPPoEとIPv6 IPoEを併用
-------------------------------------------------------------------

インターネットから自宅サーバにはIPv4 PPPoE経由で繋いで、自宅サーバ発の通信はIPv6 IPoEにするのもできました。

冒頭のQiitaの記事の LAN_PBR のPBRってなんだろうと思っていのですが、
`EdgeRouter - Policy-based routing (source address based) – Ubiquiti Networks Support and Help Center <https://help.ubnt.com/hc/en-us/articles/204952274-EdgeRouter-Policy-based-routing-source-address-based->`_ というページを見てPolicy Based Routingの略だということがわかり、ようやくQiitaの記事の設定内容が理解できました。

このサポート記事ではVLANで分けていますが、私はひとまずThinkPadと自宅サーバは同じeth1というシンプルな構成にすることにしました。

ググってみるとIPv4アドレスを追加すれば行けそうということで試してみるとうまくいきました。

自宅サーバではブリッジを使っているので

`networking - How to add an IP alias on a bridged interface? - Ask Ubuntu <https://askubuntu.com/questions/45086/how-to-add-an-ip-alias-on-a-bridged-interface/45098#45098>`_

を参考に :code:`/etc/network/interfaces` に以下のように設定しました。

.. code-block:: text

	auto br0
	iface br0 inet static
		address 192.168.2.201
		netmask 255.255.255.0
		gateway 192.168.2.1
		dns-nameservers 10.155.92.1
		dns-nameservers 192.168.2.1
		bridge_ports enp0s25
		up /sbin/ip a add 192.168.2.202/24 dev br0
		down /sbin/ip a del 192.168.2.202/24 dev br0

10.155.92.1 はLXDのdnsmasqです。 Policy Based Routingで192.168.2.201はIPv6 IPoE、192.168.2.202はIPv4 PPPoEを使うようにしています。

EdgeRouter Liteの設定まとめ
---------------------------

ID、パスワード、MACアドレス、IPv6アドレスなどを伏せた現在の設定を載せておきます。

.. code-block:: text

    set firewall all-ping enable
    set firewall broadcast-ping disable
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
    set firewall ipv6-receive-redirects disable
    set firewall ipv6-src-route disable
    set firewall ip-src-route disable
    set firewall log-martians enable
    set firewall modify LAN_PBR rule 10 action modify
    set firewall modify LAN_PBR rule 10 description 'Traffic from DMZ'
    set firewall modify LAN_PBR rule 10 modify table 1
    set firewall modify LAN_PBR rule 10 source address 192.168.2.202-192.168.2.254
    set firewall modify LAN_PBR rule 20 action modify
    set firewall modify LAN_PBR rule 20 description 'Traffic from LAN'
    set firewall modify LAN_PBR rule 20 modify table 2
    set firewall modify LAN_PBR rule 20 source address 192.168.2.0/24
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
    set firewall options mss-clamp interface-type pppoe
    set firewall options mss-clamp mss 1414
    set firewall receive-redirects disable
    set firewall send-redirects enable
    set firewall source-validation disable
    set firewall syn-cookies enable
    set interfaces ethernet eth0 address 192.168.1.2/24
    set interfaces ethernet eth0 address '**:**:**:**:**:**:**:**/64'
    set interfaces ethernet eth0 description WAN
    set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth1 host-address '::1'
    set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth1 prefix-id ':1'
    set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth1 service slaac
    set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth2 host-address '::1'
    set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth2 prefix-id ':2'
    set interfaces ethernet eth0 dhcpv6-pd pd 0 interface eth2 service slaac
    set interfaces ethernet eth0 dhcpv6-pd pd 0 prefix-length /60
    set interfaces ethernet eth0 dhcpv6-pd rapid-commit enable
    set interfaces ethernet eth0 duplex auto
    set interfaces ethernet eth0 firewall in ipv6-name WANv6_IN
    set interfaces ethernet eth0 firewall in name WAN_IN
    set interfaces ethernet eth0 firewall local ipv6-name WANv6_LOCAL
    set interfaces ethernet eth0 firewall local name WAN_LOCAL
    set interfaces ethernet eth0 ipv6 dup-addr-detect-transmits 1
    set interfaces ethernet eth0 ipv6 router-advert cur-hop-limit 64
    set interfaces ethernet eth0 ipv6 router-advert link-mtu 0
    set interfaces ethernet eth0 ipv6 router-advert managed-flag true
    set interfaces ethernet eth0 ipv6 router-advert max-interval 600
    set interfaces ethernet eth0 ipv6 router-advert other-config-flag true
    set interfaces ethernet eth0 ipv6 router-advert reachable-time 0
    set interfaces ethernet eth0 ipv6 router-advert retrans-timer 0
    set interfaces ethernet eth0 ipv6 router-advert send-advert true
    set interfaces ethernet eth0 pppoe 0 default-route auto
    set interfaces ethernet eth0 pppoe 0 description 'PPPoE IPv4'
    set interfaces ethernet eth0 pppoe 0 firewall in name WAN_IN
    set interfaces ethernet eth0 pppoe 0 firewall local name WAN_LOCAL
    set interfaces ethernet eth0 pppoe 0 mtu 1454
    set interfaces ethernet eth0 pppoe 0 name-server auto
    set interfaces ethernet eth0 pppoe 0 password **********
    set interfaces ethernet eth0 pppoe 0 user-id **********@***.**.**
    set interfaces ethernet eth0 speed auto
    set interfaces ethernet eth1 address 192.168.2.1/24
    set interfaces ethernet eth1 description LAN1
    set interfaces ethernet eth1 duplex auto
    set interfaces ethernet eth1 firewall in modify LAN_PBR
    set interfaces ethernet eth1 speed auto
    set interfaces ethernet eth2 address 192.168.3.1/24
    set interfaces ethernet eth2 description LAN2
    set interfaces ethernet eth2 duplex auto
    set interfaces ethernet eth2 speed auto
    set interfaces ipv6-tunnel v6tun0 encapsulation ipip6
    set interfaces ipv6-tunnel v6tun0 firewall in name WAN_IN
    set interfaces ipv6-tunnel v6tun0 ****:***:***:****:****:****:****:****
    set interfaces ipv6-tunnel v6tun0 mtu 1500
    set interfaces ipv6-tunnel v6tun0 multicast disable
    set interfaces ipv6-tunnel v6tun0 remote-ip '2404:8e01::feed:100'
    set interfaces ipv6-tunnel v6tun0 ttl 64
    set interfaces loopback lo
    set port-forward auto-firewall enable
    set port-forward hairpin-nat enable
    set port-forward lan-interface eth1
    set port-forward rule 1 forward-to address 192.168.2.202
    set port-forward rule 1 forward-to port 22
    set port-forward rule 1 original-port 22
    set port-forward rule 1 protocol tcp_udp
    set port-forward rule 2 forward-to address 192.168.2.202
    set port-forward rule 2 forward-to port 80
    set port-forward rule 2 original-port 80
    set port-forward rule 2 protocol tcp_udp
    set port-forward rule 3 forward-to address 192.168.2.202
    set port-forward rule 3 forward-to port 443
    set port-forward rule 3 original-port 443
    set port-forward rule 3 protocol tcp_udp
    set port-forward wan-interface pppoe0
    set protocols static interface-route 0.0.0.0/0 next-hop-interface v6tun0
    set protocols static route6 '::/0' next-hop 'fe80::***:****:****:****' interface eth0
    set protocols static table 1 interface-route 0.0.0.0/0 next-hop-interface pppoe0
    set protocols static table 1 interface-route 192.168.1.0/24 next-hop-interface eth0
    set protocols static table 2 interface-route 0.0.0.0/0 next-hop-interface v6tun0
    set protocols static table 2 interface-route 192.168.1.0/24 next-hop-interface eth0
    set service dhcp-server disabled false
    set service dhcp-server hostfile-update disable
    set service dhcp-server shared-network-name LAN1 authoritative disable
    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 default-router 192.168.2.1
    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 dns-server 192.168.2.1
    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 lease 86400
    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 start 192.168.2.2 stop 192.168.2.99
    set service dhcp-server shared-network-name LAN2 authoritative disable
    set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 default-router 192.168.3.1
    set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 dns-server 192.168.3.1
    set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 lease 86400
    set service dhcp-server shared-network-name LAN2 subnet 192.168.3.0/24 start 192.168.3.2 stop 192.168.3.99
    set service dhcp-server use-dnsmasq disable
    set service dns dynamic interface pppoe0 service noip host-name *****.****.***
    set service dns dynamic interface pppoe0 service noip login ********@*****.***
    set service dns dynamic interface pppoe0 service noip password **********
    set service dns forwarding cache-size 150
    set service dns forwarding listen-on eth1
    set service dns forwarding listen-on eth2
    set service dns forwarding listen-on eth0
    set service dns forwarding name-server 192.168.1.1
    set service gui http-port 80
    set service gui https-port 443
    set service gui older-ciphers enable
    set service nat rule 5010 description 'masquerade for WAN'
    set service nat rule 5010 outbound-interface pppoe0
    set service nat rule 5010 type masquerade
    set service ssh disable-password-authentication
    set service ssh port 22
    set service ssh protocol-version v2
    set system host-name ubnt
    set system login user ***** authentication encrypted-password *********************
    set system login user ***** plaintext-password ''
    set system login user ***** authentication public-keys **** key ********************
    set system login user ***** authentication public-keys **** type ssh-rsa
    set system login user ***** level admin
    set system ntp server 0.ubnt.pool.ntp.org
    set system ntp server 1.ubnt.pool.ntp.org
    set system ntp server 2.ubnt.pool.ntp.org
    set system ntp server 3.ubnt.pool.ntp.org
    set system offload hwnat disable
    set system offload ipv4 forwarding enable
    set system offload ipv6 forwarding enable
    set system syslog global facility all level notice
    set system syslog global facility protocols level debug
    set system time-zone Asia/Tokyo


これはルータで :code:`show configuration commands > config.commands` でファイルに保存したものを以下のスクリプトで加工したものです。このスクリプトは汎用ではないですが、私の設定の機密情報を伏せるように加工するようになっています。

.. code-block:: text

    #!/bin/sh
    sed -e "
    /mac-address/s/..:..:..:..:..:../**:**:**:**:**:**/
    /address '.*:.*'/s/'.*:.*\(\/[^']*\)'/'**:**:**:**:**:**:**:**\1'/
    /^set interfaces ethernet eth0 pppoe 0 password/s/password .*/password **********/
    /^set interfaces ethernet eth0 pppoe 0 user-id/s/user-id .*/user-id **********@***.**.**/
    /^set interfaces ipv6-tunnel v6tun0 local-ip/s/local-ip .*/****:***:***:****:****:****:****:****/
    /^set service dns dynamic interface pppoe0 service noip host-name/s/host-name .*/host-name *****.****.***/
    /^set service dns dynamic interface pppoe0 service noip login/s/login .*/login ********@*****.***/
    /^set service dns dynamic interface pppoe0 service noip password/s/password .*/password **********/
    /^set system login user [^ ]* authentication encrypted-password/s/user .*/user ***** authentication encrypted-password *********************/
    /^set system login user [^ ]* authentication plaintext-password/s/user .*/user ***** plaintext-password ''/
    /^set system login user [^ ]* authentication public-keys [^ ]* key/s/user .*/user ***** authentication public-keys **** key ********************/
    /^set system login user [^ ]* authentication public-keys [^ ]* type/s/user .* type \(.*\)/user ***** authentication public-keys **** type \1/
    /^set system login user [^ ]* level/s/user .* level \(.*\)/user ***** level \1/
    /set protocols static route6 '::\/0' next-hop/s/next-hop '[^']*'/next-hop 'fe80::***:****:****:****'/
    "

ThinkPadでPPPoEを使うときの切り替え方法
---------------------------------------

192.168.2.202以降のアドレスにすればPPPoEを使うようになっているので、コントロールパネルのイーサネットの「アダプターのオプションを設定する」からWiFiのTCP/IPv4のプロパティで固定IPで192.168.2.203などを指定すれば切り替わります。

ThinkPadでPPPoEを使うときの切り替え方法（ボツ案）
---------------------------------------------------

上記の案になる前にはDHCPでThinkPadのMACアドレスに対して固定のIPv4アドレスを設定して切り替えるというのを考えて試していました。

まずルータに以下の設定を固定で入れておきます。

.. code-block:: text

    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 static-mapping 10 ip-address 192.168.2.203
    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 static-mapping 10 mac-address **:**:**:**:**:**

`EdgeRouter - How can I use scripts to change the configuration? – Ubiquiti Networks Support and Help Center <https://help.ubnt.com/hc/en-us/articles/204976394-EdgeRouter-How-can-I-use-scripts-to-change-the-configuration->`_ にルータのコマンドをシェルスクリプトから実行する方法が載っていたのでこれを使って以下のような切り替えスクリプトを書いてみました。

:code:`ipoe.sh`

.. code-block:: text

    #!/bin/vbash
    source /opt/vyatta/etc/functions/script-template
    configure
    set service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 static-mapping 10 disable
    commit
    exit

:code:`pppoe.sh`

.. code-block:: text

    #!/bin/vbash
    source /opt/vyatta/etc/functions/script-template
    configure
    delete service dhcp-server shared-network-name LAN1 subnet 192.168.2.0/24 static-mapping 10 disable
    commit
    exit

ルータにsshしてこれらのスクリプトを実行してDHCPでアドレスを固定するか動的にするか切り替えて、その後ThinkPadではコマンドプロンプトで :code:`ipconfig /release && ipcnfig /renew` でIPv4アドレスを解放・更新して切り替えます。

これで動きはしたのですが、手数を考えると上に書いたように単にThinkPad側で固定IPを指定するほうが楽だと思いました。

おわりに
--------

一旦満足良く設定になりました。今後はインターネットから自宅サーバにIPv6で接続できるようにしたいです。IPv6のファイアウォールをかけるのをルータでこれもPolicy Based Routingで書けば良さそうな気がしますが、今後考えて試してみようと思います。
