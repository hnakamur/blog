github.com/facebookgo/graceパッケージでグレースフルリスタートを試してみた
#########################################################################

:date: 2017-04-13 07:10
:tags: go graceful-restart
:category: blog
:slug: 2017/04/13/tried-graceful-restart-with-facebookgo-grace


はじめに
--------

`go, go-carbon, carbonapiのrpmをfedora coprでビルドしてみた </blog/2017/04/13/built-go-carbon-and-carbonapi-rpm/>`_ でcarbonapiが
`facebookgo/grace: Graceful restart & zero downtime deploy for Go servers. <https://github.com/facebookgo/grace/>`_
を使っていることに気づいたので、それでグレースフルリスタートを試してみました。ということでメモです。

facebookgo/grace
----------------

goのグレースフルリスタートについては
`Go言語でGraceful Restartをする - Shogo's Blog <https://shogo82148.github.io/blog/2015/05/03/golang-graceful-restart/>`_
の記事にお世話になっていました。

この記事を読んで自分で書いたサーバプログラムでは facebookgo/grace ではなく
`lestrrat/go-server-starter: Go port of start_server utility (Server::Starter) <https://github.com/lestrrat/go-server-starter>`_
を利用させていただいています。

一方、carbonapiではfacebookgo/graceを利用しています。コードはこれだけ。簡単ですね。

`main.go#L1181-L1184 <https://github.com/go-graphite/carbonapi/blob/1ac234b878f90ba657f6ed332452bd808e7ccb6c/main.go#L1181-L1184>`_

.. code-block:: go

    err = gracehttp.Serve(&http.Server{
        Addr:    Config.Listen,
        Handler: handler,
    })

systemdならPIDFileを書くだけでOK
--------------------------------

`systemd.service <https://www.freedesktop.org/software/systemd/man/systemd.service.html#PIDFile=>`_ の :code:`PIDFile` の説明を読むと :code:`Type=forking` の場合には :code:`PIDFile` を設定するのがお勧めとあります。

:code:`Type=simle` でも機能するのかなと思って試してみるとうまく行きました！

実際のservice定義ファイルは
`carbonapi-rpm/carbonapi.service <https://github.com/hnakamur/carbonapi-rpm/blob/84659a13ce235f33a9c699f93cfe6d2864850b9e/SOURCES/carbonapi.service>`_
です。

.. code-block:: text

    [Unit]
    Description=carbonapi server
    Documentation=https://github.com/go-graphite/carbonapi
    Wants=network-online.target go-carbon.service
    After=network-online.target go-carbon.service

    [Service]
    User=carbon
    Group=carbon
    Type=simple
    Restart=on-failure
    EnvironmentFile=/etc/sysconfig/carbonapi
    ExecStart=/usr/sbin/carbonapi -z $ZIPPER_URL -pid /var/run/carbonapi/carbonapi.pid -graphite $GRAPHITEADDR -p $PORT -i $INTERVAL -cpus $CPUS -cache $CACHE_TYPE -memsize $MEMSIZE -l $CONCURRENCY_LIMIT -idleconns $IDLECONNS -logdir $LOGDIR
    ExecReload=/bin/pkill -USR2 --pidfile /var/run/carbonapi/carbonapi.pid
    PIDFile=/var/run/carbonapi/carbonapi.pid
    LimitNOFILE=65536

    [Install]
    WantedBy=multi-user.target

これで :code:`systemctl reload carbonapi` でグレースフルリスタートがかかります。
その後 :code:`systemctl status carbonapi` で確認するとacitveになっていて、表示されているpidも :code:`/var/run/carbonapi/carbonapi.pid` の内容に一致していました。

横でリクエストを打ち続けて取りこぼしがないかとかはまだ試していません。

なお、上のservice定義ファイルでは :code:`EnvironmentFile` を使っているので
pidファイルのパスも出来れば環境変数で設定・参照したいところです。
`systemd の Environment / EnvironmentFile では変数展開できません - Qiita <http://qiita.com/kobanyan/items/f8e8a3bd5406e1d290fb>`_
を読んで試行錯誤したのですが、うまくいかなかったので諦めました。

おわりに
--------

systemdを使うのであれば github.com/facebookgo/grace でのグレースフルリスタートはお手軽でよさそうです。ということで今後使っていきたいと思います。
