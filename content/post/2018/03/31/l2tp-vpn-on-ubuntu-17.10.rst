Ubuntu 17.10でL2TPのVPN接続を試してみた
#######################################

:date: 2018-03-31 08:40
:tags: ubuntu, l2tp, vpn
:category: blog
:slug: 2018/03/31/l2tp-vpn-on-ubuntu-17.10

はじめに
========

Ubuntu 17.10でL2TPのVPN接続を試してみたのでメモです。
以下の手順の一部は接続先の設定に依存して変動がありえます。


セットアップ
============

必要なソフトウェアをインストール
--------------------------------

network-manager-l2tp-gnomeをインストール。依存関係でnetwork-manager-l2tpやxl2tpdも入ります。

.. code-block:: console

        sudo apt install -y network-manager-l2tp-gnome

xl2tpdはVPN接続するときに起動されるのでOS起動時に起動しないようにしておきます。

.. code-block:: console

        sudo systemctl stop xl2tpd
        sudo systemctl disable xl2tpd

VPN設定を追加
-------------

1. 「設定」→「ネットワーク」→「VPN」の右上の「＋」ボタンを押します。

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/start-adding-vpn.png
        :width: 490px
        :height: 355px
	:alt: start adding vpn

2. 「VPNの追加」ダイアログで「Layer 2 Tunneling Protocol (L2TP)」を選択します。

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/select-l2tp-protocol.png
        :width: 500px
        :height: 341px
	:alt: select l2tp

3. 「VPNの追加」ダイアログの「Identity」タブの項目設定

   * 名前: (任意)
   * ゲートウェイ: 接続先のホスト名
   * ユーザー名: 接続に必要なユーザ名
   * パスワード: 空のまま

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/vpn-identity.png
        :width: 556px
        :height: 409px
	:alt: vpn identity

4. 「VPNの追加」ダイアログの「IPSec Settings」ボタンを押して以下の項目を設定。

   * 「Enable IPsec tunnel to L2TP host」チェックボックスをオン。
   * Pre-shared keyに接続先で設定されている事前共有キーの値を設定。
   * 「Advanced」を展開して「Phase1 Algorithms」に aes256-sha1-modp1536 と設定。アルゴリズムの設定値の調べ方については後述。

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/ipsec-options.png
        :width: 364px
        :height: 333px
	:alt: ipsec options

5. 「VPNの追加」ダイアログの「PPP Settings」ボタンを押して以下の項目を設定。

   1. 「MPPE暗号を使用する」チェックボックスをオン。
   2. 認証方式の「MSCHAP」と「MSCHAPｖ２」の2つのみがチェックされた状態になるので「MSCHAP」のチェックを外す。
   3. 「PPP Echoパケットを送信する」チェックボックスをオン（これは絶対に必要かは不明ですが試行錯誤した感じではオンにしたほうが良さそうな感じ）。

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/ppp-options.png
        :width: 401px
        :height: 669px
	:alt: ppp options

6. Ubuntuを再起動。

   * 再起動は不要かもしれませんが、何回か試行錯誤したときの挙動にばらつきがあったので、確実にするために再起動しておきます。


VPN接続の手順
=============

1. パスワードマネージャ KeePassX で接続先の自分のユーザー名に対応するパスワードをコピーします。

2. デスクトップ右上のWifiのアイコンをクリックし、「VPNオフ」メニューを展開して「接続」のメニューを選択。

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/start-connecting.png
        :width: 387px
        :height: 462px
	:alt: start connecting

3. パスワードダイアログがモーダルで表示されるのでコピーしておいたパスワードをペースト。

接続中

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/connecting.png
        :width: 456px
        :height: 80px
	:alt: connecting

接続完了

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/connected.png
        :width: 405px
        :height: 84px
	:alt: connected


VPN切断の手順
=============

1. デスクトップ右上のVPNのアイコンをクリックし、上記設定で追加したVPN名のメニューを展開して「オフにする」メニューを選択。

.. image:: {attach}/images/2018/03/31/l2tp-vpn-on-ubuntu-17.10/start-disconnecting.png
        :width: 366px
        :height: 469px
	:alt: start disconnecting

2. デスクトップ右上のVPN接続のアイコンが消えたら切断完了ですが、ウェブブラウザでインターネットのどこかのサイトを開いてアクセスできない場合Wifiを一旦オフにしてからオンにします。

デバッグ
========

接続のデバッグ
--------------

接続がうまく行かないときは
`network-manager-l2tpのDebuggingのDebian and Ubuntuの手順 <https://github.com/nm-l2tp/network-manager-l2tp#debian-and-ubuntu>`_
でデバッグします。

.. code-block:: console

        sudo killall -TERM nm-l2tp-service
        sudo /usr/lib/NetworkManager/nm-l2tp-service --debug

例えば上記の「PPP Echoパケットを送信する」チェックボックスをオンにしていなかったときは以下のようなエラーが出ていました。

.. code-block:: text

        xl2tpd[3698]: control_finish: sending ICRQ
        xl2tpd[3698]: check_control: Received out of order control packet on tunnel 61298 (got 0, expected 1)
        xl2tpd[3698]: handle_packet: bad control packet!
        xl2tpd[3698]: network_thread: bad packet

IPsecのアルゴリズムのスキャン
-----------------------------

IPsec Optionsダイアログに設定したAlgorithmは以下のようにして検出しました。

1. ike-scan パッケージをインストール

.. code-block:: console

   sudo apt install -y ike-scan

2. 検出用スクリプトを作成

   https://github.com/nm-l2tp/network-manager-l2tp/wiki/Known-Issues#querying-vpn-server-for-its-ikev1-algorithm-proposals

   以下のスクリプトを ike-scan.sh という名前で保存。

.. code-block:: bash

	#!/bin/sh
	 
	# Encryption algorithms: 3des=5, aes128=7/128, aes192=7/192, aes256=7/256
	ENCLIST="5 7/128 7/192 7/256"
	# Hash algorithms: md5=1, sha1=2, sha256=5, sha384=6, sha512=7
	HASHLIST="1 2 5 6 7"
	# Diffie-Hellman groups: 1, 2, 5, 14, 15, 19, 20, 21
	GROUPLIST="1 2 5 14 15 19 20 21"
	# Authentication method: Preshared Key=1
	AUTH=1
	 
	for ENC in $ENCLIST; do
	   for HASH in $HASHLIST; do
	       for GROUP in $GROUPLIST; do
		  echo ike-scan --trans=$ENC,$HASH,$AUTH,$GROUP -M "$@"
		  ike-scan --trans=$ENC,$HASH,$AUTH,$GROUP -M "$@"
	      done
	   done
	done


3. 実行パーミションを付与。

.. code-block:: console

	chmod +x ike-scan.sh

LT2Pの接続先を引数に指定して実行し、利用可能なアルゴリズム一覧を表示。下記の「接続先のホスト」は実際のホスト名に置き換えてください。

.. code-block:: console

	./ike-scan.sh 接続先のホスト | grep 'SA='

実行例は以下の通りです。

.. code-block:: console

	$ ./scan-vpn-algo 接続先のホスト | grep 'SA='
		SA=(Enc=3DES Hash=SHA1 Auth=PSK Group=2:modp1024 LifeType=Seconds LifeDuration(4)=0x00007080)
		SA=(Enc=3DES Hash=SHA1 Auth=PSK Group=5:modp1536 LifeType=Seconds LifeDuration(4)=0x00007080)
		SA=(Enc=AES Hash=SHA1 Auth=PSK Group=2:modp1024 KeyLength=256 LifeType=Seconds LifeDuration(4)=0x00007080)
		SA=(Enc=AES Hash=SHA1 Auth=PSK Group=5:modp1536 KeyLength=256 LifeType=Seconds LifeDuration(4)=0x00007080)

上記の内容をIPsec Optionsにフルで指定する場合は以下のように書くことになります。

* Phase1 Algorithms: aes256-sha1-modp1536,aes256-sha1-modp1024
* Phase2 Algorithms: 3des-sha1-modp1536,3des-sha1-modp1024

ですが、わざわざ弱いアルゴリズムを指定する必要もないので、上記では一番強い aes256-sha1-modp1536 のみを指定する手順としました。
