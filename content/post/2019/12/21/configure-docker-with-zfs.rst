DockerでZFSストレージドライバを使う
###################################

:date: 2019-12-21 21:00
:tags: docker, zfs
:category: blog
:slug: 2019/12/21/configure-docker-with-zfs

参考: `Use the ZFS storage driver | Docker Documentation <https://docs.docker.com/storage/storagedriver/zfs-driver/>`_

:code:`/var/lib/docker` を :code:`/var/lib/docker.bak` にリネームして :code:`/var/lib/docker` を作り直しパーミションを合わせます。

.. code-block:: console

   sudo mv /var/lib/docker{,.bak}
   sudo mkdir /var/lib/docker
   sudo 711 /var/lib/docker

以下では :code:`tank1` というボリュームが既にある想定で :code:`tank1/docker` ボリュームを新規作成し :code:`/var/lib/docker` にマウントポイントを設定します。

.. code-block:: console

   sudo zfs create tank1/docker
   sudo zfs set mountpoint=/var/lib/docker tank1/docker

:code:`/var/lib/docker.bak` の内容を :code:`/var/lib/docker` にコピーします。

.. code-block:: console

   sudo tar cf - . -C /var/lib/docker.bak | sudo tar xf - -C /var/lib/docker

動作確認して問題なければ :code:`/var/lib/docker.bak` を消します。

.. code-block:: console

   sudo rm -rf /var/lib/docker.bak
