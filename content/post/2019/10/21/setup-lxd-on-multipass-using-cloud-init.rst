multipassのVM作成時にcloud-initでLXDをセットアップ
##################################################

:date: 2019-10-21 06:05
:tags: multipass, virtualization, lxd
:category: blog
:slug: 2019/10/21/setup-lxd-on-multipass-using-cloud-init

はじめに
========

`multipass <https://github.com/CanonicalLtd/multipass>`_ ではVMの作成時に :code:`multipass launch` の :code:`--cloud-init` オプションで `cloud-init <https://github.com/cloud-init/cloud-init>`_ を使って初期化を行えます。

LXD をセットアップする手順を試行錯誤したのでメモです。

参考資料
========

* `cloud-init の Modules のドキュメント <https://cloudinit.readthedocs.io/en/latest/topics/modules.html>`_
* `Ubuntu 18.04 LTS の cloud-init の cc_lxd.py のソース <https://github.com/cloud-init/cloud-init/blob/ubuntu/19.2-36-g059d049c-0ubuntu2_18.04.1/cloudinit/config/cc_lxd.py>`_

cloud-initの設定ファイル例その1
===============================

* まず apt の設定でURLを日本のミラーサイトにします。
* zfs でループバックのストレージを 80GB で作成します。
* LXD のストレージバックエンドを zfs にします。
* LXDのブリッジをデフォルト設定で新規作成します。

.. code-block:: yaml

   #cloud-config
   locale: en_US.utf8
   timezone: Asia/Tokyo
   package_upgrade: true
   package_reboot_if_required: true
   apt:
     primary:
       - arches:
           - amd64
           - default
         uri: "http://jp.archive.ubuntu.com/ubuntu/"
   lxd:
     init:
       storage_backend: zfs
       storage_create_loop: 80
     bridge:
       mode: new
       name: lxdbr0

上記のファイルを :code:`lxd-cloud-config.yml` などお好みの名前で保存し、以下のコマンドを実行してVMを作成・起動します。ディスクサイズは上記の zfs のプールサイズ80GBにシステム領域で20GBを使う想定で合計100GBとしています。

.. code-block:: cosole

   multipass launch -n primary -c 2 -m 4G -d 100G --cloud-init lxd-cloud-config.yml

cloud-initの設定ファイル例その2
===============================

その1の例に加えて以下の設定を追加しています。

* LXDのブリッジのIPv4アドレスをランダムではなく明示的に指定。
* IPv6アドレスは無効。
* ドメインを指定。
* cloud-init の :code:`runcmd` モジュールを使って、LXD のコンテナをIPアドレスを指定して作成。

.. code-block:: yaml

   #cloud-config
   locale: en_US.utf8
   timezone: Asia/Tokyo
   package_upgrade: true
   package_reboot_if_required: true
   apt:
     primary:
       - arches:
           - amd64
           - default
         uri: "http://jp.archive.ubuntu.com/ubuntu/"
   lxd:
     init:
       storage_backend: zfs
       storage_create_loop: 80
     bridge:
       mode: new
       name: lxdbr0
    ipv4_address: 192.168.255.1
    ipv4_netmask: 24
    ipv4_nat: !!str "true"
    ipv6_address: none
    domain: my-lxd.test
   runcmd:
     - 'sudo -u multipass lxc init ubuntu:18.04 u1'
     - 'sudo -u multipass lxc network attach lxdbr0 u1 eth0 eth0'
     - 'sudo -u multipass lxc config device set u1 eth0 ipv4.address 192.168.255.2'
     - 'sudo -u multipass lxc start u1'

ハマりポイントのメモ。

:code:`ipv4_nat` のデフォルト値は :code:`"true"` なので省略しても良いです。
ただ、書く場合は文字列の :code:`"true"` が必要で単に :code:`"true"` だとうまく行かず上記のように :code:`!!str` を付けるとうまく行きました。
YAMLパーサが対応しているバージョンの違いっぽいですが、詳しく調べていません。

:code:`runcmd` のドキュメントを見るとコマンドは :code:`[sudo, -u, multipass, lxc, init, ubuntu:18.04, u1]` のように文字列ではなく配列形式でも書けるようなのですが、どうもうまく行かなかったので文字列形式にしています。

cloud-init に以下の設定も追加してホスト名のFQDNを設定しようと試みたが

.. code-block:: yaml

   preserve_hostname: false
   hostname: hoge.my-lxd.test

以下のエラーが発生した。VMのホスト名は変更しないほうが良さそう。

.. code-block:: console

   timed out waiting for initialization to complete
   mount failed: The following errors occurred:
   error mounting "setup": ssh connection failed: 'Failed to resolve hostname primary.mshome.net (そのようなホストは不明です。 )'

multipassの cloud-init での初期化のタイムアウトは5分間。

https://github.com/CanonicalLtd/multipass/blob/v0.8.0/src/daemon/daemon.cpp#L77

.. code-block:: c++

   constexpr auto cloud_init_timeout = 5min;

上記の例ではruncmdでLXDのコンテナ作成までやろうとしていますが、実はこのときは :code:`package_upgrade: true` はまだ入れてませんでした。パッケージノアップデートとLXDのセットアップまでにして、コンテナの作成はcloud-init終わって起動してからにするほうが無難。

おわりに
========

これで Windows と macOS でも手軽に LXD の環境がセットアップ出来て良い感じです。
