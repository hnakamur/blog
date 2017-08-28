git-buildpacakgeとfreightでパスフレーズをファイルから入力させる
###############################################################

:date: 2017-08-28 22:00
:tags: gpg, git-buildpackage, freight, deb
:category: blog
:slug: 2017/08/28/use-passphrase-file-in-git-buildpackage-and-freight

はじめに
--------

`git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順 <https://hnakamur.github.io/blog/2017/07/05/how-to-build-deb-with-git-buildpackage/>`_
の :code:`gbp buildpackage` でソースパッケージをビルドする時と
`freightでプライベートdebレポジトリ作成 <https://hnakamur.github.io/blog/2017/08/05/create-private-deb-repository-with-freight/>`_
の :code:`freight cache` でレポジトリを更新する際にgpgのパスフレーズを入力する必要があります。

何度も実行しているとパスワードマネージャからコピペするのが面倒になってきてファイルから入力する方法を調べたのでメモです。

git-buildpackage でのパスフレーズ自動入力
-----------------------------------------

gpg-agentを使う方法も試したが不採用
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:code:`gbp buildpackage` でソースパッケージをビルドする際に
:code:`gpg: gpg-agent is not available in this session` というメッセージと共に
:code:`Enter passphrase:` というプロンプトが出るので、当初はgpg-agentを使えば良いのではないかと思いました。

gpg-agent を使うには gnupg-agent パッケージをインストールするのが簡単ですが、これはgpg 2.x系となっています。

.. code-block:: console

	$ dpkg -l | grep gnupg
	ii  gnupg                                1.4.20-1ubuntu3.1                          amd64        GNU privacy guard - a free PGP replacement
	ii  gnupg-agent                          2.1.11-6ubuntu2                            amd64        GNU privacy guard - cryptographic agent
	ii  gnupg2                               2.1.11-6ubuntu2                            amd64        GNU privacy guard - a free PGP replacement (new v2.x)

gbp-buildpackage から呼び出される debsign の :code:`-p` オプションで署名の際に使うgpgのプログラムを変更できます。

`Ubuntu Manpage: debsign - sign a Debian .changes and .dsc file pair using GPG <http://manpages.ubuntu.com/manpages/xenial/en/man1/debsign.1.html>`_

.. code-block:: text

       -pprogname
              When  debsign  needs to execute GPG to sign it will run progname
              (searching the PATH if necessary), instead of gpg.

:code:`-pgpg2` のように指定することで署名の際に gpg2 を使うことが出来ます。
:code:`-p` の後にスペースを開けてはいけないことと、 :code:`"-pgpg2 foo"` のように空白を含んだコマンドラインを
指定はできないので要注意です。

gpg2 を使うように指定すると gpg-agent が自動的に起動されてCUIのダイアログが開いてパスフレーズを入力すれば
しばらくは再入力しなくて良くなるようです。

連続してdebパッケージを作るとき以外はgpg-agentに再度パスフレーズを入力する必要がありました。

gpg v1の--passphrase-fdオプションを使ってファイルからパスフレーズを入力
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

自宅サーバでdebパッケージをビルドしている場合はファイルから読めたほうが楽なので別の手を探して見つけました。

まず :code:`/home/hnakamur/.gpg-passphrase` というファイルを作ってそこにパスフレーズを書いておきます。自宅サーバで他にユーザはいないですが、一応パーミションは :code:`400` にしました。

で次に、以下のスクリプトを :code:`/home/hnakamur/bin/gpg-passphrase` というファイル名で作成し実行パーミションを付与します。

.. code-block:: text

	#!/bin/sh
	exec </home/hnakamur/.gpg-passphrase /usr/bin/gpg --batch --passphrase-fd 0 --no-use-agent "$@"

ファイルからのリダイレクトは
:code:`exec /usr/bin/gpg --batch --passphrase-fd 0 --no-use-agent "$@" < /home/hnakamur/.gpg-passphrase`
と書くのが普通ですが、上記のように手前にも書けるというのをどこかで見たので忘れないようにこの書き方にしてみました。

また、gpg の :code:`--passphrase` オプションを使って
:code:`exec /usr/bin/gpg --batch --passphrase ここにパスフレーズを記入 --no-use-agent "$@"`
とする手もあります。ただ、freight ではパスフレーズをファイルから読むこむのでファイルに書きたいのと、
この方式だと ps でパスフレーズが見られるリスクがあるかもしれないので、この方式は止めました。

なお、gpg の :code:`--passphrase-file` オプションを使って
:code:`exec /usr/bin/gpg --batch --passphrase-file /home/hnakmaur/.gpg-passphrase --no-use-agent "$@"`
というのも試したのですが、なぜかうまく動きませんでした。

あとは :code:`gbp buildpackage` の際に :code:`-p/home/hnakamur/bin/gpg-passphrase` を指定すればOKです。

freightのキャッシュ更新時にファイルからパスフレーズを入力
---------------------------------------------------------

:code:`man freight-cache` すると

.. code-block:: text

       -p passphrase file, --passphrase-file=passphrase file
              Use an alternate file containing the GPG key passphrase. This file should obviously be protected  and
              only readable by the user running Freight.

のように説明があります。

ということで、 :code:`freight cache -p /home/hnakamur/.gpg-passphrase` でOKです。

sudo つきで実行すると以下のような警告が出ますが、所有者と実行者が違うので仕方ないと気にしないことにします。
あるいは root ユーザで自分のgpgキーを読み込むようにしたほうが良いのかもしれません。

.. code-block:: console

	hnakamur@express:/var/www/html/my-debs$ sudo freight cache -p /home/hnakamur/.gpg-passphrase
	gpg: WARNING: unsafe ownership on configuration file `/home/hnakamur/.gnupg/gpg.conf'
	gpg: WARNING: unsafe ownership on configuration file `/home/hnakamur/.gnupg/gpg.conf'

