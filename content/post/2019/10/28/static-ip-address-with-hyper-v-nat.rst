Hyper-VのWindows NAT機能を使ってVMのIPアドレスを固定
####################################################

:date: 2019-10-29 12:00
:tags: multipass, virtualization, hyper-v, network
:category: blog
:slug: 2019/10/28/static-ip-address-with-hyper-v-nat

はじめに
========

multipassでVMを作成すると vEthernet (Default Switch) という仮想イーサネットアダプタが使用されますが、Windowsの再起動のたびにIPアドレスが変わるという問題があります。このため hosts ファイルのVMのアドレスを Windows を再起動するたびに書き換えなければなりません。これは面倒です。

`Windows 10／Windows Server 2016のHyper-VでNAT（ネットワークアドレス変換）機能を利用する：Tech TIPS - ＠IT <https://www.atmarkit.co.jp/ait/articles/1612/16/news039.html>`_
で紹介されているHyper-Vの「Windows NAT（以下WinNATと呼ぶ）」機能を使えば、VMのIPアドレスを固定することができます。ただし、multipass 0.8.0 は非対応なのでWinNATに切り替えるのは手作業で行う必要があります。さらに切り替え後のVMはmultipassでは操作できないのでHyper-Vマネージャで起動・停止を行う必要があります。multipass の管理からは外れることになりますが、IPアドレスが固定されるメリットのほうが大きいと判断しこの設定で使うことにしてみました。

以下に WinNAT のネットワークインタフェースのアドレスを :code:`192.168.254.1/24` 、VMのIPアドレスを :code:`192.168.254.2/24` に設定するという例の設定手順をメモしておきます。

VMのmultipassユーザにパスワードを設定
=====================================

まずVMのmultipassユーザにパスワードを設定しておきます。これはネットワーク設定を間違えた場合にHyper-VマネージャからVMのコンソールを開いてログインできるようにするためです。

:code:`multiapss shell` あるいは :code:`ssh wa-pdev-vm` でVMにmultipassユーザでログインした状態で以下のコマンドを実行してパスワードを設定します。

.. code-block:: console

   sudo passwd multipass

パスワードはお好みで設定してください。

WinNAT用のネットワークインタフェースを作成
==========================================

PowerShellを管理者権限で開いて `New-VMSwitch <https://docs.microsoft.com/en-us/powershell/module/hyper-v/New-VMSwitch?view=win10-ps>`_ コマンドを使って以下のように実行します。

.. code-block:: powershell

   New-VMSwitch -SwitchName WinNAT -SwitchType Internal

`Get-NetAdapter <https://docs.microsoft.com/en-us/powershell/module/netadapter/Get-NetAdapter?view=win10-ps>`_ コマンドを実行してネットワークインタフェース一覧を表示します。

.. code-block:: powershell

   Get-NetAdapter

実行例。

.. code-block:: console

   PS C:\WINDOWS\system32> Get-NetAdapter
   
   Name                      InterfaceDescription                    ifIndex Status       MacAddress             LinkSpeed
   ----                      --------------------                    ------- ------       ----------             ---------
   …(略)…
   vEthernet (Default Swi... Hyper-V Virtual Ethernet Adapter             35 Up           00-15-5D-D3-29-0A        10 Gbps
   vEthernet (WinNAT)        Hyper-V Virtual Ethernet Adapter #2           5 Up           00-15-5D-DF-51-0F        10 Gbps

上記で作成した vEthernet (WinNAT) インタフェースの ifIndex 列の値を確認しておきます。上記の例では 5 です。

`New-NetIPAddress <https://docs.microsoft.com/en-us/powershell/module/nettcpip/new-netipaddress?view=win10-ps>`_ コマンドを使い、
vEthernet (WinNAT) インタフェースに 192.168.254.1/24 のアドレスを設定します。 :code:`-ifIndex` の値は適宜変更してください。

.. code-block:: powershell

   New-NetIPAddress -IPAddress 192.168.254.1 -PrefixLength 24 -ifIndex 5 

`New-NetIPAddress <https://docs.microsoft.com/en-us/powershell/module/nettcpip/new-netipaddress?view=win10-ps>`_ のドキュメントを見ると
:code:`-ifIndex` オプションでインデクスを指定する代わりに :code:`-InterfaceAlias` でインタフェース名を指定してIPアドレスを設定することもできるようです。

.. code-block:: powershell

   New-NetIPAddress -IPAddress 192.168.254.1 -PrefixLength 24 -InterfaceAlias "vEthernet (WinNAT)"

`Get-NetIPAddress <https://docs.microsoft.com/en-us/powershell/module/nettcpip/get-netipaddress?view=win10-ps>`_ でIPアドレスを確認できます。

.. code-block:: console

   PS C:\WINDOWS\system32> Get-NetIPAddress -InterfaceAlias "vEthernet (WinNAT)"
   
   
   IPAddress         : fe80::xxxx:xxxx:xxxx:xxxx%5
   InterfaceIndex    : 5
   InterfaceAlias    : vEthernet (WinNAT)
   AddressFamily     : IPv6
   Type              : Unicast
   PrefixLength      : 64
   PrefixOrigin      : WellKnown
   SuffixOrigin      : Link
   AddressState      : Preferred
   ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
   PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
   SkipAsSource      : False
   PolicyStore       : ActiveStore
   
   IPAddress         : 192.168.254.1
   InterfaceIndex    : 5
   InterfaceAlias    : vEthernet (WinNAT)
   AddressFamily     : IPv4
   Type              : Unicast

WinNATの設定
============

`New-NetNat <https://docs.microsoft.com/en-us/powershell/module/netnat/New-NetNat?view=win10-ps>`_ コマンドを実行して作成します。

.. code-block:: powershell

   New-NetNat -Name WinNAT -InternalIPInterfaceAddressPrefix 192.168.254.0/24

作成後の状態は `Get-NetNat <https://docs.microsoft.com/en-us/powershell/module/netnat/Get-NetNat?view=win10-ps>`_ コマンドで確認できます。

.. code-block:: console

   PS C:\WINDOWS\system32> Get-NetNat
   
   
   Name                             : WinNAT
   ExternalIPInterfaceAddressPrefix :
   InternalIPInterfaceAddressPrefix : 192.168.254.0/24
   IcmpQueryTimeout                 : 30
   TcpEstablishedConnectionTimeout  : 1800
   TcpTransientConnectionTimeout    : 120
   TcpFilteringBehavior             : AddressDependentFiltering
   UdpFilteringBehavior             : AddressDependentFiltering
   UdpIdleSessionTimeout            : 120
   UdpInboundRefresh                : False
   Store                            : Local
   Active                           : True

VM側のネットワーク設定を固定IPアドレスに変更
============================================

VMにログインした状態で以下のコマンドを実行して :code:`/etc/netplan/50-cloud-init.yaml` を編集します。

.. code-block:: console

   sudo vim /etc/netplan/50-cloud-init.yaml

変更前（macaddressの値はVM毎に異なるはずなのでコピペしないよう注意）

.. code-block:: yaml

   # This file is generated from information provided by
   # the datasource.  Changes to it will not persist across an instance.
   # To disable cloud-init's network configuration capabilities, write a file
   # /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg with the following:
   # network: {config: disabled}
   network:
       ethernets:
           eth0:
               dhcp4: true
               match:
                   macaddress: 00:15:5d:df:51:0e
               set-name: eth0
       version: 2

変更後

.. code-block:: yaml

   # This file is generated from information provided by
   # the datasource.  Changes to it will not persist across an instance.
   # To disable cloud-init's network configuration capabilities, write a file
   # /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg with the following:
   # network: {config: disabled}
   network:
       ethernets:
           eth0:
               dhcp4: false
               addresses:
                   - 192.168.254.2/24
               gateway4: 192.168.254.1
               match:
                   macaddress: 00:15:5d:df:51:0e
               set-name: eth0
       version: 2

Hyper-VマネージャでVMのネットワークアダプタをWinNATに変更
=========================================================

* Hyper-Vマネージャでmultipassで作成したVMを選択して[操作]/[シャットダウン]メニューを選んでVMをシャットダウンします。
* [ファイル]/[設定]メニューで設定を開き、設定ダイアログの左のツリーで[ネットワークアダプター]を選択します。
* 画面右の仮想スイッチのドロップダウンを開きDefault SwitchからWinNATに変更して[OK]ボタンを押します。

ホストOSのhostsファイルのVMのアドレスを変更する
================================================

Windows 上のブラウザや Windows Subsystem for Linux の ssh や curl で VMにアクセスできるように VM のIPアドレスを hosts ファイルに書いている場合は変更します。

Windows の :code:`C:\Windows\System32\drivers\etc\hosts` と Windows Subsystem for Linux の :code:`/etc/hosts` でVMのアドレスを :code:`192.168.254.2` に変更します。

VMの起動と接続
==============

Hyper-V マネージャから VM を起動してください。

WinNAT に切り替え後は multipass のサービスが起動できなくなり、 multipass start や multipass shell は一切使えなくなります。

VMへの接続は ssh を使ってください。
