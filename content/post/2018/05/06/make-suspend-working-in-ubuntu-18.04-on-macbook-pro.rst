MacBook Pro上のUbuntu 18.04でサスペンドが動くようにする
#######################################################

:date: 2018-05-06 09:45
:tags: ubuntu, macOS
:category: blog
:slug: 2018/05/06/make-suspend-working-in-ubuntu-18.04-on-macbook-pro

はじめに
========

MacBook Pro 15-inch, Mid 2012 (機種ID: MacBookPro10,1)にUbuntu 18.04をインストールしてみたのですが、動かしたまま画面を閉じるとAppleマークのライトは消えるのですがファンは回り続け、その後画面を開いても復帰しない状態でした。

検索してみると `Getting suspend in Linux working on a MacBook Pro <https://joshtronic.com/2017/03/13/getting-suspend-in-linux-working-on-a-macbook-pro/>`_ という記事があったので、これを参考に設定してみました。

設定方法
--------

ちょうど良さそうなので
`systemd.service (5) <http://manpages.ubuntu.com/manpages/bionic/en/man5/systemd.service.5.html>`_
の :code:`type=oneshot` を使ってみました。

.. code-block:: console

        cat <<EOF | sudo tee /etc/systemd/system/workaround-for-suspend.service > /dev/null
        [Unit]
        Description=A workaround to get suspend work properly when lid are closed
        # https://joshtronic.com/2017/03/13/getting-suspend-in-linux-working-on-a-macbook-pro/

        [Service]
        Type=oneshot
        ExecStart=/bin/sh -c 'echo XHC1 > /proc/acpi/wakeup && echo LID0 > /proc/acpi/wakeup'
        RemainAfterExit=yes

        [Install]
        WantedBy=multi-user.target
        EOF
        sudo systemctl daemon-reload
        sudo systemctl start workaround-for-suspend
        sudo systemctl enable workaround-for-suspend

今回知ったのですが、ずっと稼働し続けるようなサービスではなくて、実行して終了するようなプログラムを指定する場合は :code:`RemainAfterExit=yes` を指定しておけば、サービスの状態確認では :code:`active` と表示されます。意図通り正常に実行されているというのがわかりやすいのでつけてみました。

.. code-block:: console

	$ sudo systemctl status workaround-for-suspend
	● workaround-for-suspend.service - A workaround to get suspend work properly when lid are closed
	   Loaded: loaded (/etc/systemd/system/workaround-for-suspend.service; enabled; vendor preset: enabled)
	   Active: active (exited) since Sun 2018-05-06 09:39:59 JST; 14min ago
	 Main PID: 2976 (code=exited, status=0/SUCCESS)
	    Tasks: 0 (limit: 4915)
	   CGroup: /system.slice/workaround-for-suspend.service

	 5月 06 09:39:59 sunshine7 systemd[1]: Starting A workaround to get suspend work properly when lid are closed...
	 5月 06 09:39:59 sunshine7 systemd[1]: Started A workaround to get suspend work properly when lid are closed.


(参考) /etc/rc.localはType=forkingを使っていた
----------------------------------------------

:code:`/etc/rc.local` について調べていたら、これもsystemdのサービスとして実装されていました。

.. code-block:: console

	$ LC_ALL=C ls -l /lib/systemd/system/rc?local.service
	-rw-r--r-- 1 root root 716 Apr 21 01:55 /lib/systemd/system/rc-local.service
	lrwxrwxrwx 1 root root  16 Apr 29 00:52 /lib/systemd/system/rc.local.service -> rc-local.service

脱線しますが、上のコマンドで :code:`LC_ALL=C` のところを最初は :code:`LANG=C` にして試したら日付が日本語で出てしまいました。検索してみると
`[覚書]ざけんな。”LANG=C” “LANGUAGE=C”で日本語！！英語にならない！！の怒りの対策。”LC_ALL＝C”？”LANG=POSIX”?、suでdpkg-reconfigure locales情けないぞ！ | Deginzabi163's Blog <https://deginzabi163.wordpress.com/2014/01/05/%E8%A6%9A%E6%9B%B8langc%E3%81%97%E3%81%A6%E3%82%82%E5%87%BA%E5%8A%9B%E3%81%8C%E6%97%A5%E6%9C%AC%E8%AA%9E%E3%81%AE%E3%81%BE%E3%81%BE%EF%BC%81%EF%BC%81%EF%BC%81%E3%81%A8%E5%AF%BE%E7%AD%96/>`_ という記事がありました。

Ansibleのモジュール内でコマンドを実行するときも :code:`LANG=C` を使っている箇所があるのでこれは困るなーと思うのですが、なぜこんなことになっていたのか。

話を戻して :code:`/lib/systemd/system/rc-local.service` の中身は以下のようになっていました。

.. code-block:: text

	#  SPDX-License-Identifier: LGPL-2.1+
	#
	#  This file is part of systemd.
	#
	#  systemd is free software; you can redistribute it and/or modify it
	#  under the terms of the GNU Lesser General Public License as published by
	#  the Free Software Foundation; either version 2.1 of the License, or
	#  (at your option) any later version.

	# This unit gets pulled automatically into multi-user.target by
	# systemd-rc-local-generator if /etc/rc.local is executable.
	[Unit]
	Description=/etc/rc.local Compatibility
	Documentation=man:systemd-rc-local-generator(8)
	ConditionFileIsExecutable=/etc/rc.local
	After=network.target

	[Service]
	Type=forking
	ExecStart=/etc/rc.local start
	TimeoutSec=0
	RemainAfterExit=yes
	GuessMainPID=no

Typeはoneshotではなくforkingを使っています。理由はわからないです。
ここでも :code:`RemainAfterExit=yes` を使っています。というより、実はこれを見て知りました。
