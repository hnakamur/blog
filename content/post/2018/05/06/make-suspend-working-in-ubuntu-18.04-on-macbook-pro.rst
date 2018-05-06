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
