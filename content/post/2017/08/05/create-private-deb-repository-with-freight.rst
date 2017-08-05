freightでプライベートdebレポジトリ作成
######################################

:date: 2017-08-05 17:40
:tags: deb, freight
:category: blog
:slug: 2017/08/05/create-private-deb-repository-with-freight

はじめに
--------

CentOS だとカスタムrpmを作って :code:`yum install rpmファイル名` で依存パッケージとともにインストールできますが、Ubuntuだと :code:`dpkg -i debファイル名` でインストールは出来ますが依存パッケージは入りません。

`How to let \`dpkg -i\` install dependencies for me? - Ask Ubuntu <https://askubuntu.com/questions/40011/how-to-let-dpkg-i-install-dependencies-for-me>`_ によると :code:`dpkg -i` の後に :code:`apt -f install` するか、 :code:`gdebi-core` パッケージを入れておいて :code:`sudo gdebi debファイル名` という手はあるようです。

とはいえ、PPAにアップロードする前に :code:`apt install` で動作確認したいとか、PPAで公開しないdebパッケージを :code:`apt` コマンドでインストールしたいというケースはあるので、プライベートdebレポジトリを作りたいところです。

`DebianRepository/Setup - Debian Wiki <https://wiki.debian.org/DebianRepository/Setup>`_ に多くのツールが紹介されていますが、
`Create deb repository with several versions of the same package - Ask Ubuntu <https://askubuntu.com/questions/84788/create-deb-repository-with-several-versions-of-the-same-package#comment1444951_668791>`_ で紹介されていた https://github.com/freight-team/freight を使ってみたところ、私のニーズに丁度良い感じでした。ということでメモです。

手順の作成で試行錯誤したのですが
`Créer un repository Debian signé avec Freight | VaLouille <http://blog.valouille.fr/2014/03/creer-un-depot-debian-signe-avec-freight/>`_
をGoogle翻訳で英訳して読んで動かせるようになりました。先人の記事に感謝です。

freightのインストール手順
-------------------------

`From a Debian archive <https://github.com/freight-team/freight#from-a-debian-archive>`_
の手順を少し変えて以下のようにインストールしました。

.. code-block:: console

    sudo apt update
    sudo apt -y install curl
    curl -k https://swupdate.openvpn.net/repos/repo-public.gpg | sudo apt-key add -
    echo "deb http://build.openvpn.net/debian/freight_team $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/freight.list
    sudo apt update
    sudo apt -y install freight

私はdebをビルドしたサーバとは別にLXDのコンテナを作ってその中で root ユーザで実行していたので :code:`sudo` は不要なのですが、そうでない環境でセットアップすることも想定して :code:`sudo` は付けておきます。

:code:`curl` に :code:`-k` オプションを指定しないと以下のエラーが出たので、上の手順では :code:`-k` を指定しています。

.. code-block:: console

    $ curl https://swupdate.openvpn.net/repos/repo-public.gpg
    curl: (77) Problem with the SSL CA cert (path? access rights?)

gpgの秘密鍵のインポート
-----------------------

debをビルドしたサーバで
`gpgで秘密鍵を作成する <https://hnakamur.github.io/blog/2017/07/01/generate-secret-key-with-gpg/>`_ の「秘密鍵をエクスポートする」の手順を実行して :code:`lxc file push` コマンドを使ってLXDコンテナに秘密鍵を転送し、以下のコマンドでインポートしました。

.. code-block:: console

    gpg --import gpg-hnakamur-secret.key.pem

レポジトリの初期化
------------------

以下の手順でレポジトリのディレクトリを作成して初期化します。ディレクトリや各引数は適宜調整してください。今回は xenial 上で golang-1.9 用のレポジトリを作るので :code:`--suite` は :code:`xenial-golang-1.9` としましたが、特にレポジトリを分ける必要がなければ :code:`xenial` だけで良いです。

.. code-block:: console

    mkdir -p /var/www/freight
    cd /var/www/freight
    freight-init --gpg=hnakamur@gmail.com --libdir=/var/www/freight/lib \
        --cachedir=/var/www/freight/cache --archs="amd64 all" \
        --origin="My Internal Repository" --label="My Internal Reposiroty" \
        --suite="xenial-golang-1.9"

レポジトリにdebパッケージを追加
-------------------------------

debをビルドしたサーバで :code:`lxc file push` コマンドを使って作成した deb パッケージをLXDコンテナの :code:`/root/` ディレクトリに転送しておいて、LXDコンテナで以下のコマンドを実行しdebファイルをレポジトリに追加します。

.. code-block:: console

    freight add /root/*.deb apt/xenial-golang-1.9
    freight cache apt/xenial-golang-1.9

gpgのパスフレーズを求めるプロンプトが表示されますので、パスフレーズを入力してください。

ローカルレポジトリを使うための設定
----------------------------------

ローカルレポジトリを使うには以下のように :code:`.list` ファイルを作ればOKです。
:code:`xenial-golang-1.9` の部分は :code:`fright-init` の :code:`--suite` の引数に指定した値に合わせます。ディレクトリや :code:`.list` のファイル名も適宜調整してください。

.. code-block:: console

    echo "deb file:/var/www/freight/cache xenial-golang-1.9 main" | sudo tee /etc/apt/sources.list.d/local-golang-1.9.list

ローカルレポジトリの公開鍵をapt-keyに追加
-----------------------------------------

以下のコマンドでローカルレポジトリの公開鍵を追加します。

.. code-block:: console

    apt-key add /var/www/freight/cache/pubkey.gpg

パッケージのインストール
------------------------

これでローカルパッケージが使えるようになりました。あとは :code:`apt update` して :code:`apt install` するだけです。今回は golang-go パッケージを作ったので以下のようになります。

.. code-block:: console

    sudo apt update
    sudo apt -y install golang-go

これで依存するパッケージとともにインストールされました。素晴らしい！

おわりに
--------

今回は試していませんが、 :code:`/var/www/freight/cache` を nginx などのウェブサーバで公開して、 :code:`.list` ファイルの :code:`deb` の後の :code:`file:/var/www/freight/cache` の部分を公開したURLに変えればリモートのマシンでインストールも出来ると思います。

