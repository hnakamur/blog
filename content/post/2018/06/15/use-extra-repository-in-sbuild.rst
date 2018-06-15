sbuildで外部レポジトリを使う
############################

:date: 2018-06-15 10:12
:tags: ubuntu, deb, sbuild
:category: blog
:slug: 2018/06/15/use-extra-repository-in-sbuild

はじめに
========

外部レポジトリのdebパッケージに依存したdebパッケージをsbuildでビルドするための手順メモです。

以下の2つの方法がありますが、別のchroot環境を作る必要がないので2つめのほうが良いです。1つめの方法は別の用途にも使えるかもしれないので一応メモしておきます。

1. 外部レポジトリを追加したchroot環境を作成してそれを使ってビルド。
2. sbuildの :code:`--extra-repository` オプションを使ってビルド。

以下では拙作の
`golang 1.10 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10>`__
というPPAのレポジトリを追加する例で説明します。

Ubuntu 18.04 LTS では2018-06-13時点では go1.10.1 が配布されていますが、このPPAでは go1.10.3 を配布しています。

外部レポジトリを追加したchroot環境を作成してそれを使ってビルド
==============================================================

bionic-latest-golang という名前のchroot環境を新しく作成します。

.. code-block:: console

        mk-sbuild --name bionic-latest-golang bionic

作成したchroot環境に入ります。

.. code-block:: console

        schroot -c source:bionic-latest-golang-amd64 -u root -d /root

golang-1.10の自作PPAのレポジトリを追加します。

.. code-block:: console

        apt install software-properties-common
        add-apt-repository ppa:hnakamur/golang-1.0

chroot環境から抜けます。

.. code-block:: console

        exit

あとはdebパッケージをビルドする際にこのchroot環境を指定します。

.. code-block:: console

        TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd -c bionic-latest-golang-amd64

sbuildの :code:`--extra-repository` オプションを使ってビルド
==============================================================

chroot環境のホストで
`golang 1.10 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10>`__
のレポジトリを追加してあれば、以下のコマンドでdebパッケージをビルドできました。

.. code-block:: console

        TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd \
                --extra-repository="deb http://ppa.launchpad.net/hnakamur/golang-1.10/ubuntu bionic main" \
                --extra-repository-key /etc/apt/trusted.gpg.d/hnakamur_ubuntu_golang-1_10.gpg

:code:`--extra-repository` オプションに指定する値は :code:`/etc/apt/sources.list.d/hnakamur-ubuntu-golang-1_10-bionic.list` の :code:`deb` の行の内容です。

chroot環境のホスト側に
`golang 1.10 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10>`__
のレポジトリを追加していない場合は、このページで
"Technical details about this PPA" をクリックして "Display sources.list entries for: " の右の
ドロップダウンで "Bionic (18.04)" を選べば同じ内容が表示されます。

:code:`--extra-repository` オプションに指定する値は
`man 1 sbuild <http://manpages.ubuntu.com/manpages/bionic/en/man1/sbuild.1.html>`_ では
:code:`--extra-repository=file.asc` のように書かれていて、ASCIIのPEM形式のGPG公開鍵のファイルを指定する
必要があるようです。

ですが、 :code:`apt-key list` で表示される拡張子 :code:`.gpg` のファイルパスを指定してみたら、それでも動きました。

きちんとASCIIのPEM形式のGPG公開鍵を取り出すには以下のようにします。

.. code-block:: console

        apt-key --keyring /etc/apt/trusted.gpg.d/hnakamur_ubuntu_golang-1_10.gpg exportall

標準出力に以下のように鍵が表示されるので、ファイルにリダイレクトして使えばOKです。

.. code-block:: text

        -----BEGIN PGP PUBLIC KEY BLOCK-----

        mQINBFcTVU8BEADjFbrMyBLXPRodLMF4pGKdjd6FDn/5URnwx1g10NkPzM6jxK9J
        4CKkQWWMHpM1Qtk/r1z6e1CJEDdWdWds0TDyRh18bwEPFGE9FYsQWJihBb1GNKWa
        AM++FwArbTc0tInaLBWcrJsL0NPqJE0ttvL2g7ZFfOlS8VTzYr+sKWWReq9kCyaA
        DUe7aKgft+q7Rw/5Y+gw47msWh2ESnLUltPP71C7FRaFp8k5CrNHRLCXqL0LggTQ
        aWzyZBdfmD7tzqTn4szOz0BMM1DyyzZmj5W/zzpRx1vLOCICpedYg99w+5ZeeoLp
        egVYjCkYzQnKIK7kq4GDX/9SUgLMrNFJFbilxJd1ibEsMrWB+NzIO1jcL/t+rF4J
        YShtsOeNiwc6qzAT+tMLFR4hxpVwTY7RWTIU/+4Y2fOosw1mdcaWHvxavef6Yt8B
        qy2G51RKctcO1jt4U9IPjUKVKeXdTW5Y9sGpag91z15+GHuerrj3DKZa8om+nMls
        Oz1V4yASz7JyhFPedLNPHURE6rgexDk8ebb1gOf5sc5G3iVNpev0agbq+1msqxdg
        pEV78cILERVxWCyEUCjSHk7aNKpJnnZN1+J3vpSj53A/dcovR8fkkxkILCMWJjFn
        ClbyLx8brJkAuwHEBdXYPxUFKM2rzKT2AvcPHA+4cm/Gy0uXBC16ht+4/QARAQAB
        tCJMYXVuY2hwYWQgUFBBIGZvciBIaXJvYWtpIE5ha2FtdXJhiQI4BBMBAgAiBQJX
        E1VPAhsDBgsJCAcDAgYVCAIJCgsEFgIDAQIeAQIXgAAKCRBg2VShEBc0Hig+D/9i
        LGIqiLESEYPq+LrLE29ZU63h9kShsg89kJVxu1G5Knj6c9oAut8faS7MyA92vbXq
        kEa3IygxbpXhFj79MAq2d1RHzg37A/1vvdY1rRBoPTBCUNkl9E9jDiUFw10w3Rma
        QN3Ap3saqf+wCA1OIIgdmJDsnYk8WEDCYtfKsCHoHJCa8iSoRsNo2GpVnyNpSNrE
        J2m8VldFJ1BGC6pYP77XcbG/jb01g2mG7XoHDnVtGeTma/8ps85W+0FlzFxyEfU4
        pr86RfwALSkUmGglNlYqv6yyhKQx4mj3Dq4qrxrmFIw49volysWdruYZp69YZmc7
        aBNH98EpIKSJgbW78eeH0MbGY5bp9rMK1SzxYz5DLktT57AbsIqzu0fZ4HzeLjn1
        UFYs5g5MTt1iTLypLhsDYmeFoYqi8XYaWHKYnp4PTUitvGfLeevg7Z7PcgIGZ6Su
        5AWC8xYn/tHiOg5Pzl4GtxA4A01UGirRfF8kAB7C8rpJkhS0IG4xbvVjArVeApPV
        jXdrDiuT17US1RCJ0hztA/NCDYA2800/U9U83d1yxza04miyY++a1crSKAuR3+kM
        L8XtToVZNBbFZsIuitx30xhm1uhF8+saAZhavwmhzCa5Z5vKVFxvt8MC+I1uik06
        5KY++bMCM+8GWGvPCJ/XYSKwrMDVdZzQZ1cTNwY9yA==
        =4arz
        -----END PGP PUBLIC KEY BLOCK-----

chroot環境のホスト側に
`golang 1.10 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10>`__
のレポジトリを追加していない場合は、このページで
"Technical details about this PPA" をクリックして "Signing key:" の下の
"4096R/532A4A026239FC3BAEB7869C60D954A11017341E"
リンクをクリックし、
遷移先のページのkeyIDのリンクをクリックすると鍵が表示されます。

今回の例では以下の1017341EがkeyIDです。

.. code-block:: text

        Type bits/keyID     Date       User ID

        pub  4096R/1017341E 2016-04-17 Launchpad PPA for Hiroaki Nakamura
                 Fingerprint=532A 4A02 6239 FC3B AEB7  869C 60D9 54A1 1017 341E

リンク先のURLは :code:`https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x60D954A11017341E`
で、中身は以下のようなHTMLになっています。

.. code-block:: html

        <?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd" >
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <title>Public Key Server -- Get "0x60d954a11017341e "</title>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <style type="text/css">
        /*<![CDATA[*/
         .uid { color: green; text-decoration: underline; }
         .warn { color: red; font-weight: bold; }
        /*]]>*/
        </style></head><body><h1>Public Key Server -- Get "0x60d954a11017341e "</h1>
        <pre>
        -----BEGIN PGP PUBLIC KEY BLOCK-----
        Version: SKS 1.1.6
        Comment: Hostname: keyserver.ubuntu.com

        mQINBFcTVU8BEADjFbrMyBLXPRodLMF4pGKdjd6FDn/5URnwx1g10NkPzM6jxK9J4CKkQWWM
        HpM1Qtk/r1z6e1CJEDdWdWds0TDyRh18bwEPFGE9FYsQWJihBb1GNKWaAM++FwArbTc0tIna
        LBWcrJsL0NPqJE0ttvL2g7ZFfOlS8VTzYr+sKWWReq9kCyaADUe7aKgft+q7Rw/5Y+gw47ms
        Wh2ESnLUltPP71C7FRaFp8k5CrNHRLCXqL0LggTQaWzyZBdfmD7tzqTn4szOz0BMM1DyyzZm
        j5W/zzpRx1vLOCICpedYg99w+5ZeeoLpegVYjCkYzQnKIK7kq4GDX/9SUgLMrNFJFbilxJd1
        ibEsMrWB+NzIO1jcL/t+rF4JYShtsOeNiwc6qzAT+tMLFR4hxpVwTY7RWTIU/+4Y2fOosw1m
        dcaWHvxavef6Yt8Bqy2G51RKctcO1jt4U9IPjUKVKeXdTW5Y9sGpag91z15+GHuerrj3DKZa
        8om+nMlsOz1V4yASz7JyhFPedLNPHURE6rgexDk8ebb1gOf5sc5G3iVNpev0agbq+1msqxdg
        pEV78cILERVxWCyEUCjSHk7aNKpJnnZN1+J3vpSj53A/dcovR8fkkxkILCMWJjFnClbyLx8b
        rJkAuwHEBdXYPxUFKM2rzKT2AvcPHA+4cm/Gy0uXBC16ht+4/QARAQABtCJMYXVuY2hwYWQg
        UFBBIGZvciBIaXJvYWtpIE5ha2FtdXJhiQI4BBMBAgAiBQJXE1VPAhsDBgsJCAcDAgYVCAIJ
        CgsEFgIDAQIeAQIXgAAKCRBg2VShEBc0Hig+D/9iLGIqiLESEYPq+LrLE29ZU63h9kShsg89
        kJVxu1G5Knj6c9oAut8faS7MyA92vbXqkEa3IygxbpXhFj79MAq2d1RHzg37A/1vvdY1rRBo
        PTBCUNkl9E9jDiUFw10w3RmaQN3Ap3saqf+wCA1OIIgdmJDsnYk8WEDCYtfKsCHoHJCa8iSo
        RsNo2GpVnyNpSNrEJ2m8VldFJ1BGC6pYP77XcbG/jb01g2mG7XoHDnVtGeTma/8ps85W+0Fl
        zFxyEfU4pr86RfwALSkUmGglNlYqv6yyhKQx4mj3Dq4qrxrmFIw49volysWdruYZp69YZmc7
        aBNH98EpIKSJgbW78eeH0MbGY5bp9rMK1SzxYz5DLktT57AbsIqzu0fZ4HzeLjn1UFYs5g5M
        Tt1iTLypLhsDYmeFoYqi8XYaWHKYnp4PTUitvGfLeevg7Z7PcgIGZ6Su5AWC8xYn/tHiOg5P
        zl4GtxA4A01UGirRfF8kAB7C8rpJkhS0IG4xbvVjArVeApPVjXdrDiuT17US1RCJ0hztA/NC
        DYA2800/U9U83d1yxza04miyY++a1crSKAuR3+kML8XtToVZNBbFZsIuitx30xhm1uhF8+sa
        AZhavwmhzCa5Z5vKVFxvt8MC+I1uik065KY++bMCM+8GWGvPCJ/XYSKwrMDVdZzQZ1cTNwY9
        yA==
        =4arz
        -----END PGP PUBLIC KEY BLOCK-----
        </pre>
        </body></html>

鍵の部分だけを切り出すには以下のようなコマンドを使い、あとはファイルにリダイレクトするようにすればOKです。

.. code-block:: console

        curl -sSL 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x60D954A11017341E' \
                | sed -n '/^-----BEGIN/,/^-----END/p'
