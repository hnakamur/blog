pbuilderのchroot環境にレポジトリを追加する
##########################################

:date: 2017-09-02 16:00
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

ローカルにある自作debパッケージを使いたい場合のビルド手順
---------------------------------------------------------

ローカルにある自作パッケージをビルド時に含める方法は
`How to include local packages in the build <https://wiki.debian.org/PbuilderTricks#How_to_include_local_packages_in_the_build>`_
に書かれていました。

上記のように chroot 環境を作っておけば、gcc-7 を使いつつローカルにある自作debパッケージのディレクトリ :code:`/var/www/html/my-debs/cache` をレポジトリとして追加してビルドするには以下のようにすればOKです。

.. code-block:: console

        $ sudo pbuilder build --override-config \
                --othermirror 'deb [trusted=yes] file:/var/www/freight/cache xenial main' \
                dscファイル名
