Ubuntu 18.04でgit-buildpackageとfreightを使うときのメモ
#######################################################

:date: 2018-05-01 12:35
:modified: 2018-05-29 10:55
:tags: ubuntu
:category: blog
:slug: 2018/05/01/ubuntu-18.04-git-buildpackage-freight

はじめに
--------

* `git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順 </blog/2017/07/05/how-to-build-deb-with-git-buildpackage/>`_
* `freightでプライベートdebレポジトリ作成 </blog/2017/08/05/create-private-deb-repository-with-freight/>`_
* `git-buildpacakgeとfreightでパスフレーズをファイルから入力させる </blog/2017/08/28/use-passphrase-file-in-git-buildpackage-and-freight/>`__

に書いた git-buildpackage と freight の環境を Ubuntu 18.04 でも作ったのですが、少し変更が必要だったのでメモです。


gbp buildpacakgeには-dオプションを指定
--------------------------------------

Ubuntu 16.04 のときには以下のコマンドでソースパッケージをビルドしていました。

.. code-block:: console

        gbp buildpackage --git-export-dir=../build-area -p/home/hnakamur/bin/gpg-passphrase -S -sa

が、Ubuntu 18.04ではgit-buildpackageのバージョンが変わった影響で :code:`gbp buildpackage` でのソースパッケージの作成時にdebパッケージの依存関係のエラーが出るようになりました。

調べてみたところ :code:`gbp` が呼び出している :code:`dpkg-buildpackage` に依存関係をチェックする :code:`-D` オプションとチェックしない :code:`-d` オプションがあることがわかりました。

`Ubuntu Manpage: dpkg-buildpackage - build binary or source packages from sources <http://manpages.ubuntu.com/manpages/bionic/en/man1/dpkg-buildpackage.1.html>`_

.. code-block:: text

       -D, --check-builddeps
              Check build dependencies and conflicts; abort if unsatisfied (long option since dpkg 1.18.8).  This is the default behavior.

       -d, --no-check-builddeps
              Do not check build dependencies and conflicts (long option since dpkg 1.18.8).

Ubuntu 16.04 で gbp buildpackage を実行していたときは dpkg-buildpackage を呼ぶ時に -d が指定されていましたが、Ubuntu 18.04 では指定されなくなっていました。 gbp buildpackage のソースを見るとオプションを指定するとそのまま dpkg-buildpackage に渡すようになっていました。

ということで以下のように -d を指定することで解決しました。

.. code-block:: console

        gbp buildpackage --git-export-dir=../build-area -p/home/hnakamur/bin/gpg-passphrase -S -sa -d

GnuPG 2.xでパスフレーズをファイルから読み込ませるための対応
-----------------------------------------------------------

Ubuntu 16.04では /usr/bin/gpg は gnupg という GnuPG 1.x のパッケージに含まれる実行ファイルでした。
で gnupg2 という GnuPG 2.x のパッケージの実行ファイルは /usr/bin/gpg2 という名前でした。

.. code-block:: console

        $ ls -l /usr/bin/gpg{,2}
        -rwxr-xr-x 1 root root 1008632 Aug 18  2016 /usr/bin/gpg
        -rwxr-xr-x 1 root root  917032 Apr  8  2016 /usr/bin/gpg2

.. code-block:: console

        $ dpkg -l gnupg gnupg2 gnupg-agent
        Desired=Unknown/Install/Remove/Purge/Hold
        | Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
        |/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
        ||/ Name                    Version          Architecture     Description
        +++-=======================-================-================-====================================================
        ii  gnupg                   1.4.20-1ubuntu3. amd64            GNU privacy guard - a free PGP replacement
        ii  gnupg-agent             2.1.11-6ubuntu2  amd64            GNU privacy guard - cryptographic agent
        ii  gnupg2                  2.1.11-6ubuntu2  amd64            GNU privacy guard - a free PGP replacement (new v2.x

Ubuntu 18.04では /usr/bin/gpg は gnupg2 パッケージのファイルになり、gnupg1 パッケージの実行ファイルは /usr/bin/gpg1 という名前に変えられています。また、 /usr/bin/gpg2 は /usr/bin/gpg へのシンボリックリンクになりました。

.. code-block:: console

        $ ls -l /usr/bin/gpg{,1,2}
        -rwxr-xr-x 1 root root 1021480 Jan 11 22:33 /usr/bin/gpg
        -rwxr-xr-x 1 root root  889720 Nov 11 23:41 /usr/bin/gpg1
        lrwxrwxrwx 1 root root       3 Jan 11 22:33 /usr/bin/gpg2 -> gpg

.. code-block:: console

        $ dpkg -l gnupg gnupg2 gnupg1
        Desired=Unknown/Install/Remove/Purge/Hold
        | Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
        |/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
        ||/ Name                    Version          Architecture     Description
        +++-=======================-================-================-====================================================
        ii  gnupg                   2.2.4-1ubuntu1   amd64            GNU privacy guard - a free PGP replacement
        ii  gnupg1                  1.4.22-3ubuntu2  amd64            GNU privacy guard - a PGP implementation (deprecated
        ii  gnupg2                  2.2.4-1ubuntu1   all              GNU privacy guard - a free PGP replacement (dummy tr

GnuPG 2.xでは 
`git-buildpacakgeとfreightでパスフレーズをファイルから入力させる </blog/2017/08/28/use-passphrase-file-in-git-buildpackage-and-freight/>`__
に書いた `--passphrase-fd` を使った手法はそのままでは使えませんでした。

ArchWikiのGnuPGのページの `Unattended passphrase <https://wiki.archlinux.org/index.php/GnuPG#Unattended_passphrase>`_  に回避策が書かれていました。元のオプションに :code:`--pinentry-mode loopback` を追加すれば良いとのことです。

gbp buildpackageの-pオプションに指定するファイルの修正
++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. code-block:: console

        gbp buildpackage --git-export-dir=../build-area -p/home/hnakamur/bin/gpg-passphrase -S -sa -d

の -p オプションで指定している /home/hnakamur/bin/gpg-passphrase の中身は以下のように書き換えました。

.. code-block:: bash

        #!/bin/sh
        exec </home/hnakamur/.gpg-passphrase /usr/bin/gpg --batch --pinentry-mode loopback --passphrase-fd 0 "$@"

frightの-pオプションを使うには修正が必要
++++++++++++++++++++++++++++++++++++++++

freightのほうはfreightのソースを変更する必要があったので、変更してプルリクエストを送りました。
`Support gpg2 in freight cache passphrase file option by hnakamur · Pull Request #84 · freight-team/freight <https://github.com/freight-team/freight/pull/84>`_ 
（2018-05-29追記。マージされました！）

この変更を加えた状態ですと、以前と同じ以下のコマンドでOKです。

.. code-block:: console

        sudo freight cache -p /home/hnakamur/.gpg-passphrase
