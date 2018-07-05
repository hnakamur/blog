LXDのコンテナイメージのエクスポート・インポート
###############################################

:date: 2018-07-05 14:50
:tags: lxd
:category: blog
:slug: content/post/2018/07/05/export-and-import-lxd-container-image

はじめに
========

`nginxとshibbolethでSAML2のシングルサインオンを試してみた </blog/2018/07/04/saml2-single-sign-on-with-nginx-and-shibboleth/>`_ で使ったCentOS7のLXDコンテナのイメージをエクスポートし、別のマシンにコピーしてインポートするのを試してみたのでメモです。

LXD 3.2で試しました。

`Backup the container and install it on another server - LXD - Linux Containers Forum <https://discuss.linuxcontainers.org/t/backup-the-container-and-install-it-on-another-server/463/2>`_ の手順ほぼそのままでOKでした。

リモートのLXDにアクセスできる場合は、このコメントのように :code:`lxc copy` コマンド一発でコピーできるのですが、今回はエクスポートしてインポートする方式を試しました。


エクスポート
============

まずスナップショットを作成します。 以下のコマンドを :code:`CONTAINER_NAME` を実際の環境に合わせて変更して実行します。

.. code-block:: console

        lxc snapshot CONTAINER_NAME

コンテナのスナップショット一覧は以下のコマンドで確認できます。

.. code-block:: console

        lxc info CONTAINER_NAME --verbose

実行例を示します。

.. code-block:: console

        $ lxc info --verbose centos7
        Name: centos7
        …(略)…
        Snapshots:
          snap0 (taken at 2018/07/05 06:02 UTC) (stateless)


次に :code:`lxc publish` でスナップショットをイメージに変換します。
以下のコマンドを :code:`CONTAINER_NAME` と :code:`SNAPSHOT_NAME` を実際の環境に合わせて変更し :code:`--alias` の引数の :code:`my-export` をお好みの名前に変えて実行します。

.. code-block:: console

        lxc publish CONTAINER_NAME/SNAPSHOT_NAME --alias my-export

実行例です。

.. code-block:: console

        $ lxc publish centos7/snap0 --alias my-export
        Container published with fingerprint: fd1e60e8d58e3bad3e67eb5de3ac1ad148718f2339ad3709ad35bd636d65cf770

:code:`lxc image list` でローカルのイメージを一覧表示すると :code:`my-export` というエイリアスを持つイメージが含まれることが確認できます。

あとはイメージをエクスポートするだけです。

.. code-block:: console

        lxc image export my-export .

:code:`Image exported successfully!` と表示されたら成功です。カレントディレクトリに publish したときの fingerprint をベース名に持つtarballのファイルが作られていました。

.. code-block:: console

        $ ls
        fd1e60e8d58e3bad3e67eb5de3ac1ad148718f2339ad3709ad35bd636d65cf77.tar.gz

インポート
==========

事前準備として上記の手順でエクスポートしたtarballのファイルをインポートしたいマシンに何らかの方法でコピーしておきます。

まずtarballのファイルをイメージとしてインポートします。:code:`TARBALL` の部分を実際のファイル名に置き換えて以下のコマンドを実行してください。

.. code-block:: console

        lxc image import TARBALL --alias my-export

あとはこのイメージを元にコンテナを作成します。:code:`NEW-CONTAINER` の部分をお好みのコンテナ名に変更して以下のコマンドを実行してください。

.. code-block:: console

        lxc init my-export NEW-CONTAINER
