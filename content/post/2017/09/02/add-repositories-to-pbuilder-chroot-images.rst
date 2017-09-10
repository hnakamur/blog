pbuilderのchroot環境にレポジトリを追加する
##########################################

:date: 2017-09-02 16:00
:modified: 2017-09-10 09:13
:tags: deb, pbuilder
:category: blog
:slug: 2017/09/02/add-repositories-to-pbuilder-chroot-images

はじめに
--------

`pbuilder <https://pbuilder.alioth.debian.org/>`_ を使っていくつかdebパッケージを作ってみて、chroot環境をカスタマイズするベストプラクティスが自分の中で出来たのでメモです。

* Ubuntu Xenialと同じapt-lineを使いたい
* xenial-updates にあるパッケージを使いたい
* PPAにあるgcc 7を使いたい
* ローカルにある自作debパッケージを使いたい

というニーズを満たすためのものです。

ベースの chroot 環境の作成手順
------------------------------

試行錯誤の結果、 Ubuntu Xenial と同じ apt-line の chroot 環境の作成手順は以下のように落ち着きました。

.. code-block:: console

        $ sudo pbuilder create \
                --mirror http://jp.archive.ubuntu.com/ubuntu/ \
                --distribution xenial \
                --components "main restricted universe multiverse"

.. code-block:: console

        $ sudo mkdir -p /var/cache/pbuilder/scripts
        $ cat <<'EOS' | sudo tee /var/cache/pbuilder/scripts/add-updates-backports-security.sh
        echo 'deb http://jp.archive.ubuntu.com/ubuntu/ xenial-updates main restricted universe multiverse' \
                > /etc/apt/sources.list.d/xenial-updates.list
        echo 'deb http://jp.archive.ubuntu.com/ubuntu/ xenial-backports main restricted universe multiverse' \
                > /etc/apt/sources.list.d/xenial-backports.list
        echo 'deb http://security.ubuntu.com/ubuntu xenial-security main restricted universe multiverse' \
                > /etc/apt/sources.list.d/xenial-security.list
        apt update -y
        apt upgrade -y
        EOS

.. code-block:: console

        $ sudo pbuilder execute --save-after-exec \
                -- /var/cache/pbuilder/scripts/add-updates-backports-security.sh

追加の apt-line は :code:`pbuilder create` に :code:`--othermirror` オプションで :code:`|` で区切って複数指定する方法もあります。
しかし、ローカルにある自作debパッケージを使いたいとき、ビルド時に :code:`pbuilder build` で :code:`--override-config` オプションとともに :code:`--othermirror` オプションで変更したいのですが、上記の xenial-updates などの追加レポジトリも全て書く必要があって面倒です。

そこで、 xenial-updates などのレポジトリは :code:`--othermirror` オプションを使わずに上記の手順で追加するようにしました。

作った chroot 環境の中身を確認するのは :code:`sudo pbuilder login` で出来ます。
:code:`/etc/apt/sources.list.d/xenial-updates.list` などが意図通りに追加されていることを確認したら Ctrl-D で抜けます。

gcc-7を使う際の chroot 環境の作成手順
-------------------------------------

:code:`/var/cache/pbuilder/base.tgz` をコピーして :code:`/var/cache/pbuilder/gcc7.tgz` を作り変更していきます。

.. code-block:: console

        $ sudo cp /var/cache/pbuilder/base.tgz /var/cache/pbuilder/gcc7.tgz

.. code-block:: console

        $ cat <<'EOS' | sudo tee /var/cache/pbuilder/scripts/add-gcc-7-repo.sh
        apt-key adv --keyserver keyserver.ubuntu.com --recv BA9EF27F
        echo 'deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main' \
                > /etc/apt/sources.list.d/ubuntu-toolchain-r-ubuntu-test-xenial.list
        apt update -y
        EOS

.. code-block:: console

        $ sudo pbuilder execute --basetgz /var/cache/pbuilder/gcc7.tgz --save-after-exec \
                -- /var/cache/pbuilder/scripts/add-gcc-7-repo.sh

:code:`/var/cache/pbuilder/scripts/add-gcc-7-repo.sh` でのレポジトリの追加は
`add-apt-repositoryを使わずにPPAをapt-lineに追加する方法 </2017/09/02/add-ppa-to-apt-line-without-add-apt-repository/>`_
で説明した方法を使っています。

ここで作った chroot 環境の中身は
:code:`sudo pbuilder login --basetgz /var/cache/pbuilder/gcc7.tgz`
で確認できます。

pbuilder の chroot 環境の手動更新
---------------------------------

chroot 環境は一度作成すると更新されないので、ときどき以下の手順で :code:`apt update` と :code:`apt upgrade` 相当の更新をする必要があります。

:code:`/var/cache/pbuilder/base.tgz` を更新する場合は以下のコマンドを実行します。

.. code-block:: console

        $ sudo pbuilder update
       
:code:`/var/cache/pbuilder/gcc7.tgz` を更新する場合は以下のコマンドを実行します。

.. code-block:: console

        $ sudo pbuilder update --basetgz /var/cache/pbuilder/gcc7.tgz

ビルド時に apt update するための設定
------------------------------------

:code:`~/.pbuilderrc` に以下の設定を追加します。

.. code-block:: text

        HOOKDIR="/var/cache/pbuilder/hook.d"

:code:`mkdir -p /var/cache/pbuilder/hook.d` でディレクトリを作成し、以下の内容で :code:`/var/cache/pbuilder/hook.d/D70apt-update` というファイルを作成し実行パーミションを付与します。

.. code-block:: text

        #!/bin/sh
        /usr/bin/apt update


ローカルにある自作debパッケージを使いたい場合のビルド手順
---------------------------------------------------------

ローカルにある自作パッケージをビルド時に含める方法は
`How to include local packages in the build <https://wiki.debian.org/PbuilderTricks#How_to_include_local_packages_in_the_build>`_
に書かれていました。

上記のように chroot 環境を作っておけば、gcc-7 を使いつつローカルにある自作debパッケージのレポジトリ :code:`http://localhost/my-debs/cache` をレポジトリとして追加してビルドするには以下のようにします。

.. code-block:: console

        $ sudo pbuilder build --basetgz /var/cache/pbuilder/gcc7.tgz \
                --override-config \
                --othermirror 'deb [trusted=yes] http://localhost/my-debs/cache xenial main' \
                dscファイル名

なお、上記の「ビルド時に apt update するための設定」を行っておく必要があります。

ビルド時にエラーになったときに chroot 環境に入る設定
----------------------------------------------------

上記の「ビルド時に apt update するための設定」の :code:`~/.pbuilderrc` の設定追加と
:code:`HOOKDIR` のディレクトリを作成するのをやった上で、以下のコマンドで
:code:`/var/cache/pbuilder/hook.d/C10shell` というシンボリックリンクを作成します。

.. code-block:: console

        $ sudo ln -s /usr/share/doc/pbuilder/examples/C10shell /var/cache/pbuilder/hook.d/
