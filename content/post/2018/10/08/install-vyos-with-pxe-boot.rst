PXEブートでVyOSをインストール
#############################

:date: 2018-10-08 18:40
:modified:  2018-10-08 19:00
:tags: vyos
:category: blog
:slug: 2018/10/08/install-vyos-with-pxe-boot

はじめに
========

半年前くらいに `yamamasa23 <https://twitter.com/yamamasa23>`_ さんの真似して中古で買った
`Quad Beagle ZG <https://store.atworks.co.jp/eol/eol2012/quad-beagle-zg/>`_
に PXE ブートで `VyOS <https://vyos.io/>`_ をインストールしてみたメモです。

手順は `PXE - VyOS Wiki <https://wiki.vyos.net/wiki/PXE>`__ を参考にしました。

私は EdgeRouter-Lite で EdgeOS は利用していますが、 VyOS は今回が初めてです。

一通り設定してから、まとめてブログを書きたいのですが、分量が増えると書くのが
大変 (自分用のメモといっても、後から読んで理解できるように書こうとすると
なんだかんだで結構時間がかかってます) になるので、小分けにして書くことにします。

DebianのPXE ブート環境の整備
============================

`PXE - VyOS Wiki <https://wiki.vyos.net/wiki/PXE>`__ に PXELINUX の設定が必要と
書かれているので、整備しました。

`Ubuntu 16.04をルーター化 </blog/2018/04/23/setup-router-on-ubuntu16.04/>`_ と
`Ubuntu 16.04上にUbuntu 18.04のPXEブートサーバをセットアップ </blog/2018/04/24/ubuntu18.04-pxe-boot-server-on-ubuntu16.04/>`_
に書いた環境を今回は Ubuntu 18.04 上で構築しました。

一言で言うと :code:`tftpd-hpa` と :code:`isc-dhcp-server` の2つのパッケージを
インストールします。

.. code-block:: console

    sudo apt install tftpd-hpa isc-dhcp-server

なお私は以前使っていた :code:`/var/lib/tftpboot` ディレクトリは :code:`/var/lib/tftpboot.bak` に退避して、空のディレクトリを作りました。

`VyOS - Wikipedia <https://ja.wikipedia.org/wiki/VyOS>`_ によると VyOS は
Debian 6.0 (Squeeze) をベースにしているとのことなので、
http://ftp.riken.jp/Linux/debian/debian/dists/ 以下から
http://ftp.riken.jp/Linux/debian/debian/dists/wheezy/main/installer-amd64/current/images/netboot/netboot.tar.gz
をダウンロードして :code:`/var/lib/tftpboot` 以下に展開しました。

.. code-block:: console

    curl -L http://ftp.riken.jp/Linux/debian/debian/dists/wheezy/main/installer-amd64/current/images/netboot/netboot.tar.gz | sudo tar xf - -C /var/lib/tftpboot

:code:`/etc/dhcp/dhcpd.conf` には以下の設定を追加しました。

.. code-block:: text

    subnet 192.168.3.0 netmask 255.255.255.0 {
      option domain-name-servers 192.168.2.1;
      option routers 192.168.3.1;
      filename "pxelinux.0";
    }

    host beagle {
      hardware ethernet XX:XX:XX:XX:XX:XX;
      fixed-address 192.168.3.2;
    }

VyOSのPXE ブート環境の整備
==========================

`PXE - VyOS Wiki <https://wiki.vyos.net/wiki/PXE>`__ にはパッチを当てた initrd.img を使ったと書いていましたが、リンク切れになっていたのと `Fix PXE booting helium · Pull Request #1 · vyos/live-initramfs <https://github.com/vyos/live-initramfs/pull/1>`_ のコメントによると VyOS 1.1.8 には取り込まれたようだったので、 1.1.8 のをそのまま使いました。

作業用ディレクトリを作成して、VyOS のダウンロードページから ISO イメージをダウンロードし、マウント用ディレクトリ mnt を作ってそこにループバックマウントします。

.. code-block:: console

    mkdir ~/vyos
    cd !$
    curl -LO https://downloads.vyos.io/release/1.1.8/vyos-1.1.8-amd64.iso
    mkdir mnt
    sudo mount -o loop vyos-1.1.8-amd64.iso mnt

mnt/live ディレクトリ内の vmlinuz と initrd.img を tftpd の公開領域に vyos というディレクトリを作ってコピーします。

.. code-block:: console

    sudo mkdir /var/lib/tftpboot/vyos
    sudo cp -p mnt/live/{vmlinuz,initrd.img} !$

HTTP サーバで配信するためのディレクトリを作り、 mnt/live ディレクトリ内の filesystem.squashfs をそこにコピーします。

.. code-block:: console

    sudo mkdir -p /opt/kickstart/export/vyos
    sudo mnt/live/filesystem.squashfs !$


nginx で以下の設定を :code:`/etc/nginx/conf.d/vyos-pxe-boot.conf` として作成し(他の設定がある場合は適宜調整し) :code:`systemctl reload nginx` で反映させます。

.. code-block:: text

    server {
        listen 80;
        server_name localhost;

        location /vyos {
            root /opt/kickstart/export;
        }
    }

:code:`/var/lib/tftpboot/pxelinux.cfg/default` に以下の内容を追加します。
:code:`append` 行の最後の :code:`verbose debug=vc` の部分はデバッグ用なので無くても良いですが、指定しておくとシェルスクリプトが :code:`set -x` つきで実行されるので便利です。

.. code-block:: text

    label vyos
       kernel /vyos/vmlinuz
       append initrd=/vyos/initrd.img console=ttyS0 console=tty0 boot=live nopersistent noautologin nonetworking nouser hostname=vyos fetch=http://192.168.3.1/vyos/filesystem.squashfs verbose debug=vc
       ipappend 2


PXEブートしてインストール
=========================

PXEブートし、上記で追加した vyos メニューを選び、あとは
`Installation - User Guide - VyOS Wiki <https://wiki.vyos.net/wiki/User_Guide#Installation>`_
(`日本語訳 <https://wiki.vyos-users.jp/index.php/%E3%83%A6%E3%83%BC%E3%82%B6%E3%83%BC%E3%82%AC%E3%82%A4%E3%83%89#.E3.82.A4.E3.83.B3.E3.82.B9.E3.83.88.E3.83.BC.E3.83.AB>`_)
に従ってインストールすれば OK でした。
