pbuilderで特定のディストリビューションのchroot環境を作成
########################################################

:date: 2018-05-04 21:10
:tags: ubuntu, pbuilder
:category: blog
:slug: 2018/05/04/create-pbuilder-chroot-of-specified-distribution

はじめに
--------

Ubuntu 18.04上のpbuilderでUbuntu 16.04用のchroot環境を作成するというようにホストと違うディストリビューションのchroot環境を作成する手順のメモです。
といっても :code:`pbuilder` の :code:`--distribution` オプションを指定するだけです。

Ubuntu 16.04のchroot作成例
--------------------------

:code:`--basetgz` 無しで作成したchroot環境 :code:`/var/cache/pbuilder/base.tgz` はホストと同じUbuntu 18.04にしているので、 :code:`--distribution` オプションとともに :code:`--basetgz` オプションで違うファイル名を指定します。

以下の例ではついでにIIJのミラーからインストールするようにしています。

.. code-block:: console

        sudo pbuilder create --basetgz /var/cache/pbuilder/xenial.tgz --distribution xenial \
                --components 'main universe' --debootstrapopts --variant=buildd \
                --mirror http://ftp.iij.ad.jp/pub/linux/ubuntu/archive/ 

さらについでにホスト側もIIJのミラーを使うように変更する手順もメモです。

.. code-block:: console

        sudo sed -i.bak -e 's|http://jp.archive.ubuntu.com/ubuntu/|http://ftp.iij.ad.jp/pub/linux/ubuntu/archive/|' /etc/apt/sources.list
