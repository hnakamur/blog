LXDでコンテナの初期化に使われるテンプレート
###########################################

:date: 2019-08-15 11:00
:tags: lxd
:category: blog
:slug: 2019/08/15/lxd-container-templates

はじめに
========

`Custom network configuration with cloud-init - LXD - system container manager <https://cloudinit.readthedocs.io/en/latest/topics/dir_layout.html>`_ に説明がありますが、LXDのコンテナイメージにはいくつかのテンプレートファイルがメタデータとして含まれていて、コンテナの初期化の際に使用されます。

CentOS 7 のコンテナは cloud-init 非対応ですが、 Ubuntu のほうは cloud-init に対応していますので、 cloud-init を利用して初期化時に様々な設定が可能です。

今後の参照用にテンプレートの内容を以下にメモしておきます。

ローカルにダウンロードされたイメージ
====================================

:code:`lxc launch ubuntu:18.04 コンテナ名` で Ubuntu 18.04 LTS のコンテナを作成し、
:code:`lxc launch images:centos/7 コンテナ名` で CentOS 7 のコンテナを作成した後、
ローカルにダウンロードされたイメージを確認すると以下のようになっていました
（イメージの fingerprint はイメージのバージョンによって異なります）。

.. code-block:: console

   $ lxc image list
   +-------+--------------+--------+-----------------------------------------------+--------+----------+-------------------------------+
   | ALIAS | FINGERPRINT  | PUBLIC |                  DESCRIPTION                  |  ARCH  |   SIZE   |          UPLOAD DATE          |
   +-------+--------------+--------+-----------------------------------------------+--------+----------+-------------------------------+
   |       | 2dd611e2689a | no     | ubuntu 18.04 LTS amd64 (release) (20190813.1) | x86_64 | 177.60MB | Aug 14, 2019 at 11:07pm (UTC) |
   +-------+--------------+--------+-----------------------------------------------+--------+----------+-------------------------------+
   |       | a0f13708a581 | no     | Centos 7 amd64 (20190814_07:08)               | x86_64 | 84.07MB  | Aug 15, 2019 at 1:29am (UTC)  |
   +-------+--------------+--------+-----------------------------------------------+--------+----------+-------------------------------+

私は LXD を snap でインストールしているのでローカルにダウンロードされたイメージは :code:`/var/snap/lxd/common/lxd/images/` にあります。

file コマンドで確認すると fingerprint と同じ名前のファイルと :code:`.rootfs` の拡張子がついたファイルがあり、前者は xz で圧縮されたデータ、後者は squashfs のファイルシステム形式であることがわかります。前者は実際は .tar.xz 形式になっています。

.. code-block:: console

   $ sudo sh -c 'file /var/snap/lxd/common/lxd/images/*'
   /var/snap/lxd/common/lxd/images/2dd611e2689a8efc45807bd2a86933cf2da0ffc768f57814724a73b5db499eac:        XZ compressed data
   /var/snap/lxd/common/lxd/images/2dd611e2689a8efc45807bd2a86933cf2da0ffc768f57814724a73b5db499eac.rootfs: Squashfs filesystem, little endian, version 4.0, 186228545 bytes, 35653 inodes, blocksize: 131072 bytes, created: Tue Aug 13 16:35:42 2019
   /var/snap/lxd/common/lxd/images/a0f13708a581b3d73de64a785559ae1c5ce773e4b7eb009eedb032563c851994:        XZ compressed data
   /var/snap/lxd/common/lxd/images/a0f13708a581b3d73de64a785559ae1c5ce773e4b7eb009eedb032563c851994.rootfs: Squashfs filesystem, little endian, version 4.0, 88156577 bytes, 14110 inodes, blocksize: 1048576 bytes, created: Wed Aug 14 07:22:52 2019


Ubuntu 18.04 LTS イメージのテンプレート
=======================================

以下のコマンドでテンプレートを展開します。

.. code-block:: console

   $ mkdir /tmp/ubuntu-templates
   $ sudo tar xf /var/snap/lxd/common/lxd/images/2dd611e2689a8efc45807bd2a86933cf2da0ffc768f57814724a73b5db499eac -C /tmp/ubuntu-templates/

ファイル一覧は以下の通りです。

.. code-block:: console

   $ (cd /tmp/ubuntu-templates/; find . -type f | sort)
   ./metadata.yaml
   ./templates/cloud-init-meta.tpl
   ./templates/cloud-init-network.tpl
   ./templates/cloud-init-user.tpl
   ./templates/cloud-init-vendor.tpl
   ./templates/hostname.tpl

metadata.yaml の内容は以下の通りです。上記の :code:`*.tpl` のテンプレートファイルがどのパスに展開されるかの対応が分かります。

.. code-block:: yaml

   architecture: "x86_64"
   creation_date: 1565716206
   properties:
       architecture: "x86_64"
       description: "Ubuntu 18.04 LTS server (20190813.1)"
       os: "ubuntu"
       release: "bionic"
   templates:
       /etc/hostname:
	   when:
	       - create
	       - copy
	   template: hostname.tpl
       /var/lib/cloud/seed/nocloud-net/meta-data:
	   when:
	       - create
	       - copy
	   template: cloud-init-meta.tpl
       /var/lib/cloud/seed/nocloud-net/network-config:
	   when:
	       - create
	       - copy
	   template: cloud-init-network.tpl
       /var/lib/cloud/seed/nocloud-net/user-data:
	   when:
	       - create
	       - copy
	   template: cloud-init-user.tpl
	   properties:
	       default: |
		   #cloud-config
		   {}
       /var/lib/cloud/seed/nocloud-net/vendor-data:
	   when:
	       - create
	       - copy
	   template: cloud-init-vendor.tpl
	   properties:
	       default: |
		   #cloud-config
		   {}

templates/cloud-init-meta.tpl の内容は以下の通りです。

.. code-block:: yaml

   instance-id: {{ container.name }}
   local-hostname: {{ container.name }}
   {{ config_get("user.meta-data", "") }}

templates/cloud-init-network.tpl の内容は以下の通りです。

.. code-block:: yaml

   {% if config_get("user.network-config", "") == "" %}version: 1
   config:
       - type: physical
	 name: eth0
	 subnets:
	     - type: {% if config_get("user.network_mode", "") == "link-local" %}manual{% else %}dhcp{% endif %}
	       control: auto{% else %}{{ config_get("user.network-config", "") }}{% endif %}

templates/cloud-init-user.tpl の内容は以下の通りです。

.. code-block:: yaml

   {{ config_get("user.user-data", properties.default) }}

templates/cloud-init-vendor.tpl の内容は以下の通りです。

.. code-block:: yaml

   {{ config_get("user.vendor-data", properties.default) }}

templates/hostname.tpl の内容は以下の通りです。

.. code-block:: yaml

   {{ container.name }}

CentOS 7 イメージのテンプレート
===============================

以下のコマンドでテンプレートを展開します。

.. code-block:: console

   $ mkdir /tmp/centos7-templates
   $ sudo tar xf /var/snap/lxd/common/lxd/images/a0f13708a581b3d73de64a785559ae1c5ce773e4b7eb009eedb032563c851994 -C /tmp/centos7-templates

ファイル一覧は以下の通りです。

.. code-block:: console

   $ (cd /tmp/centos7-templates/; find . -type f | sort)
   ./metadata.yaml
   ./templates/hosts.tpl
   ./templates/ifcfg-eth0.lxd.tpl
   ./templates/network.lxd.tpl

metadata.yaml の内容は以下の通りです。上記の :code:`*.tpl` のテンプレートファイルがどのパスに展開されるかの対応が分かります。

.. code-block:: console

   architecture: x86_64
   creation_date: 1565767338
   expiry_date: 1568359338
   properties:
     architecture: x86_64
     description: Centos 7 x86_64 (20190814_07:08)
     name: centos-7-x86_64-default-20190814_07:08
     os: centos
     release: "7"
     serial: "20190814_07:08"
     variant: default
   templates:
     /etc/hosts:
       when:
       - create
       - copy
       create_only: false
       template: hosts.tpl
       properties: {}
     /etc/sysconfig/network:
       when:
       - create
       - copy
       create_only: false
       template: network.lxd.tpl
       properties: {}
     /etc/sysconfig/network-scripts/ifcfg-eth0:
       when:
       - create
       - copy
       create_only: false
       template: ifcfg-eth0.lxd.tpl
       properties: {}

templates/hosts.tpl の内容は以下の通りです。

.. code-block:: console

   127.0.1.1	{{ container.name }}
   127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
   ::1         localhost localhost.localdomain localhost6 localhost6.localdomain6

templates/ifcfg-eth0.lxd.tpl の内容は以下の通りです。

.. code-block:: console

   DEVICE=eth0
   BOOTPROTO=dhcp
   ONBOOT=yes
   HOSTNAME={{ container.name }}
   NM_CONTROLLED=no
   TYPE=Ethernet
   MTU=
   DHCP_HOSTNAME=`hostname`

templates/network.lxd.tpl の内容は以下の通りです。

.. code-block:: console

   NETWORKING=yes
   HOSTNAME={{ container.name }}
