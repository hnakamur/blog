gpgで秘密鍵を作成する
#####################

:date: 2017-07-01 17:40
:tags: gpg
:category: blog
:slug: 2017/07/01/generate-secret-key-with-gpg

はじめに
--------

gpgの秘密鍵はdebパッケージを署名するために以前作成していたのですが、ググって適当に済ませていたので手順をメモしておきます。

`GPG Cheat Sheet <http://irtfweb.ifa.hawaii.edu/~lockhart/gpg/>`_ のチートシートが便利です。他にも参考にしていたページがあったかもしれませんが忘れました。

検証用のLXDコンテナとユーザ作成
-------------------------------

Ubuntu 16.04 xenialの自宅サーバで既に秘密鍵を作成済みでそちらは触りたくないので、LXDのコンテナでxenialの環境を作って試しました。

.. code-block:: console

    lxc launch images:ubuntu/xenial debuild
    lxc exec debuild bash

コンテナ内では以下のコマンドで :code:`build` というユーザを作ってそれで試しました。

.. code-block:: console

    root@debuild:~# useradd -m build

:code:`-m` はホームディレクトリを作成するオプションです。
:code:`adduser` コマンドだとオプション無しでホームディレクトリも作ってくれますが、こちらは対話式でパスワードの設定も求められます。

以下のコマンドでユーザを切り替えます。

.. code-block:: console

    root@debuild:~# su - build

gpgで秘密鍵の作成
-----------------

gpgはインストール済みなので、あとは :code:`gpg --gen-key` コマンドを実行するだけです。
RSAの4096bitにして有効期限は1年にします。

`プロフェッショナルSSL/TLS（紙書籍＋電子書籍） – 技術書出版と販売のラムダノート <https://www.lambdanote.com/products/tls>`_ を読んでからは秘密鍵の有効期限を3年とか無期限とかは止めたほうが良いと思うようになったので1年にしています。

.. code-block:: console

    build@debuild:~$ gpg --gen-key
    gpg (GnuPG) 1.4.20; Copyright (C) 2015 Free Software Foundation, Inc.
    This is free software: you are free to change and redistribute it.
    There is NO WARRANTY, to the extent permitted by law.

    gpg: directory `/home/build/.gnupg' created
    gpg: new configuration file `/home/build/.gnupg/gpg.conf' created
    gpg: WARNING: options in `/home/build/.gnupg/gpg.conf' are not yet active during this run
    gpg: keyring `/home/build/.gnupg/secring.gpg' created
    gpg: keyring `/home/build/.gnupg/pubring.gpg' created
    Please select what kind of key you want:
       (1) RSA and RSA (default)
       (2) DSA and Elgamal
       (3) DSA (sign only)
       (4) RSA (sign only)
    Your selection? 1 ←入力
    RSA keys may be between 1024 and 4096 bits long.
    What keysize do you want? (2048) 4096 ←入力
    Requested keysize is 4096 bits
    Please specify how long the key should be valid.
             0 = key does not expire
          <n>  = key expires in n days
          <n>w = key expires in n weeks
          <n>m = key expires in n months
          <n>y = key expires in n years
    Key is valid for? (0) 1y # ←入力
    Key expires at Sun 01 Jul 2018 05:14:28 AM UTC
    Is this correct? (y/N) y ←入力

    You need a user ID to identify your key; the software constructs the user ID
    from the Real Name, Comment and Email Address in this form:
        "Heinrich Heine (Der Dichter) <heinrichh@duesseldorf.de>"

    Real name: Hiroaki Nakamura ←入力
    Email address: hnakamur@gmail.com ←入力
    Comment: ←適宜入力
    You selected this USER-ID:
        "Hiroaki Nakamura <hnakamur@gmail.com>"

    Change (N)ame, (C)omment, (E)mail or (O)kay/(Q)uit? O ←入力
    You need a Passphrase to protect your secret key.

    Enter passphrase: 設定したいパスフレーズを入力
    Repeat passphrase: パスフレーズを再入力

    We need to generate a lot of random bytes. It is a good idea to perform
    some other action (type on the keyboard, move the mouse, utilize the
    disks) during the prime generation; this gives the random number
    generator a better chance to gain enough entropy.

    Not enough random bytes available.  Please do some other work to give
    the OS a chance to collect more entropy! (Need 233 more bytes)
    .+++++
    .........+++++
    We need to generate a lot of random bytes. It is a good idea to perform
    some other action (type on the keyboard, move the mouse, utilize the
    disks) during the prime generation; this gives the random number
    generator a better chance to gain enough entropy.
    ...+++++
    ................+++++
    gpg: /home/build/.gnupg/trustdb.gpg: trustdb created
    gpg: key DCD07C7F marked as ultimately trusted
    public and secret key created and signed.

    gpg: checking the trustdb
    gpg: 3 marginal(s) needed, 1 complete(s) needed, PGP trust model
    gpg: depth: 0  valid:   1  signed:   0  trust: 0-, 0q, 0n, 0m, 0f, 1u
    gpg: next trustdb check due at 2018-07-01
    pub   4096R/DCD07C7F 2017-07-01 [expires: 2018-07-01]
          Key fingerprint = 7114 B54F 36B5 4D85 1872  86B7 189B BBB3 DCD0 7C7F
    uid                  Hiroaki Nakamura <hnakamur@gmail.com>
    sub   4096R/D2DA0362 2017-07-01 [expires: 2018-07-01]

途中で :code:`Not enough random bytes available.` と言われて止まったので、調べてみると
`linux - GPG does not have enough entropy - Server Fault <https://serverfault.com/questions/214605/gpg-does-not-have-enough-entropy/214618#214618>`_ という方法が紹介されていました。

.. code-block:: console

    sudo apt install rng-tools
    sudo rngd -r /dev/urandom

試してみたのですが、コンテナの中で実行しても相変わらず止まったままで、コンテナの親ホストで実行すると、コンテナの :code:`gpg --gen-key` のほうで :code:`.+++++` と出力されて進むようになりました。

秘密鍵のエクスポート
--------------------

他の環境に秘密鍵をコピーしたり、秘密鍵をバックアップするためにエクスポートしておきます。

.. code-block:: console

    build@debuild:~$ gpg --export-secret-key -a 'Hiroaki Nakamura' > gpg-hnakamur-secret.key.pem

生成されたPEMファイルの先頭と終端はこんな感じでした。

.. code-block:: console

    build@debuild:~$ head -4 gpg-build-private.key.pem.key
    -----BEGIN PGP PRIVATE KEY BLOCK-----
    Version: GnuPG v1

    lQdGBFlXL+kBEACmCvShw49DAEGD/hdZ3aAOYK3aYyOJ61uinvih1VyjndxDefLJ
    build@debuild:~$ tail -4 gpg-build-private.key.pem.key
    Ej4RU9NnoFQBvSRS+lwRZNp09igV6myNK6/lajF8oHkzH2Nvlz6bYf6OX1m27Cqk
    zVo=
    =6LVK
    -----END PGP PRIVATE KEY BLOCK-----

秘密鍵のインポート
------------------

別のコンテナ :code:`debuild2` とその中にユーザを作り、そちらに上記の秘密鍵をコピーしてインポートも試してみました。

冒頭のチートシートでは :code:`--allow-secret-key-import` オプションを指定しているけど obsolete と言われるとあったので、そちらは指定せずに :code:`--import` オプションのみ指定してみたら無事インポートできました。

.. code-block:: console

    build@debuild2:~$ gpg --import gpg-hnakamur-secret.pem.key
    gpg: directory `/home/build/.gnupg' created
    gpg: new configuration file `/home/build/.gnupg/gpg.conf' created
    gpg: WARNING: options in `/home/build/.gnupg/gpg.conf' are not yet active during this run
    gpg: keyring `/home/build/.gnupg/secring.gpg' created
    gpg: keyring `/home/build/.gnupg/pubring.gpg' created
    gpg: key DCD07C7F: secret key imported
    gpg: /home/build/.gnupg/trustdb.gpg: trustdb created
    gpg: key DCD07C7F: public key "Hiroaki Nakamura <hnakamur@gmail.com>" imported
    gpg: Total number processed: 1
    gpg:               imported: 1  (RSA: 1)
    gpg:       secret keys read: 1
    gpg:   secret keys imported: 1

一覧を確認してみるとインポートした鍵が一覧に出ていました。

.. code-block:: console

    build@debuild2:~$ gpg --list-key
    /home/build/.gnupg/pubring.gpg
    ------------------------------
    pub   4096R/DCD07C7F 2017-07-01 [expires: 2018-07-01]
    uid                  Hiroaki Nakamura <hnakamur@gmail.com>
    sub   4096R/D2DA0362 2017-07-01 [expires: 2018-07-01]

