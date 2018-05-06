Ubuntu 18.04でVPN切断後にホスト名解決が動くようにするための回避策
#################################################################

:date: 2018-05-06 20:35
:tags: ubuntu, l2tp, vpn
:category: blog
:slug: 2018/05/06/workaround-to-get-dns-working-after-vpn-disconnection-on-ubuntu-18.04

はじめに
========

`Ubuntu 17.10でL2TPのVPN接続を試してみた </blog/2018/03/31/l2tp-vpn-on-ubuntu-17.10/>`_ でVPN切断後にホスト名解決が動かなくなるのでWifiを一旦オフにしてオンにしていたのですが、それよりはマシな回避策を見つけたのでメモです。

回避策の設定手順
================

.. code-block:: console

        cat <<'EOF' | sudo tee /etc/NetworkManager/dispatcher.d/02-workaround-for-vpn-down > /dev/null
        #!/bin/sh -e
        interface=$1 status=$2
        case $status in
            vpn-down)
                logger -t workaround-for-vpn restarting systemd-resolved after vpn-down
                systemctl restart systemd-resolved
                logger -t workaround-for-vpn restarted systemd-resolved after vpn-down: status=$?
                ;;
        esac
        EOF
        sudo chmod +x /etc/NetworkManager/dispatcher.d/02-workaround-for-vpn-down


回避策の説明
============

Ubuntu 18.04ではサーバー、デスクトップともに :code:`/etc/resolv.conf` には :code:`nameserver 127.0.0.53` という設定があるだけでした。

.. code-block:: text

        # This file is managed by man:systemd-resolved(8). Do not edit.
        #
        # This is a dynamic resolv.conf file for connecting local clients to the
        # internal DNS stub resolver of systemd-resolved. This file lists all
        # configured search domains.
        #
        # Run "systemd-resolve --status" to see details about the uplink DNS servers
        # currently in use.
        #
        # Third party programs must not access this file directly, but only through the
        # symlink at /etc/resolv.conf. To manage man:resolv.conf(5) in a different way,
        # replace this symlink by a static file or a different symlink.
        #
        # See man:systemd-resolved.service(8) for details about the supported modes of
        # operation for /etc/resolv.conf.

        nameserver 127.0.0.53

これで、 
`systemd-resolved (8) <http://manpages.ubuntu.com/manpages/bionic/en/man8/systemd-resolved.8.html>`_
というサービスと
`systemd-resolve (1) <http://manpages.ubuntu.com/manpages/bionic/en/man1/systemd-resolve.1.html>`_
というコマンドの存在を知りました。

で、VPN切断前後で :code:`systemd-resolve --status` や :code:`systemd-resolve ホスト名` などを試していたのですが、ふと systemd-resolved を再起動してみたらどうかと思って試してみたら、うまくいったという感じです。
