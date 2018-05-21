ClamAVをUbuntu MATE 18.04 LTSにセットアップ
###########################################

:date: 2018-05-21 15:00
:tags: ubuntu, ubuntu-mate, clamav
:category: blog
:slug: 2018/05/21/setup-clamav-on-ubuntu-mate-18.04-lts

はじめに
========

Ubuntu MATE 18.04 LTSの環境にオープンソースのアンチウィルスソフト `ClamAV <https://www.clamav.net/>`_ をセットアップしてみたメモです。例によっていろいろ試行錯誤した後に思い出しながら書いているので、多少抜けがあるかも。

インストール
============

.. code-block:: console

        sudo apt install clamav-daemon clamav-freshclam

初回のパターンファイル更新と手動スキャンの動作確認
==================================================

`Ubuntu 18.04 LTS : Clamav アンチウィルス : Server World <https://www.server-world.info/query?os=Ubuntu_18.04&p=clamav>`_
を参考に試しました。

初回のパターンファイル更新
--------------------------

以下の手順で初回のパターンファイル更新を行います。

.. code-block:: console

        sudo sed -i -e "s/^NotifyClamd/#NotifyClamd/g" /etc/clamav/freshclam.conf 
        sudo systemctl stop clamav-freshclam
        sudo freshclam
        sudo systemctl start clamav-freshclam
        sudo sed -i -e "s/^#NotifyClamd/NotifyClamd/g" /etc/clamav/freshclam.conf 

手動スキャンの動作確認
----------------------

ウィルスがない状態での手動スキャンの動作確認。

.. code-block:: console

	$ clamscan --infected --remove --recursive ~/Downloads/

	----------- SCAN SUMMARY -----------
	Known viruses: 9436590
	Engine version: 0.99.4
	Scanned directories: 1
	Scanned files: 1
	Infected files: 0
	Data scanned: 0.64 MB
	Data read: 0.19 MB (ratio 3.40:1)
	Time: 13.025 sec (0 m 13 s)

実験用の無害なウィルスをダウンロード。

.. code-block:: console

	$ curl -o ~/Downloads/eicar.com http://www.eicar.org/download/eicar.com

ウィルスがある状態での手動スキャンの動作確認。

.. code-block:: console

	$ clamscan --infected --remove --recursive ~/Downloads/
	/home/hnakamur/Downloads/eicar.com: Eicar-Test-Signature FOUND
	/home/hnakamur/Downloads/eicar.com: Removed.

	----------- SCAN SUMMARY -----------
	Known viruses: 9436590
	Engine version: 0.99.4
	Scanned directories: 1
	Scanned files: 2
	Infected files: 1
	Data scanned: 0.64 MB
	Data read: 0.19 MB (ratio 3.40:1)
	Time: 12.698 sec (0 m 12 s)

設定
====

scan on-access というリアルタイムスキャンと `Thunderbird <https://www.thunderbird.net/ja/>`_ の `clamdrib LIN <https://addons.mozilla.org/ja/thunderbird/addon/clamdrib-lin/>`_ アドオンでメールをスキャンするのを試しました。

`how to scan on-access with clamav in 14.04 - Ask Ubuntu <https://askubuntu.com/questions/591325/how-to-scan-on-access-with-clamav-in-14-04/821510#821510>`_ と
`ScanningEmail - Community Help Wiki <https://help.ubuntu.com/community/ScanningEmail>`_
を参考にしました。

aptでインストールした時点ではclamavユーザでclamdを動かすようになっていたのですが、
:code:`/etc/clamav/clamd.conf` で :code:`ScanOnAccess` をtrueにして動かすと
journalログに :code:`ScanOnAccess: clamd must be started by root` というエラーが出たので
rootユーザで動かすように変更しました。

:code:`/etc/clamav/clamd.conf` の変更内容は以下のとおりです。

.. code-block:: diff

	--- /etc/clamav/clamd.conf.orig	2018-05-21 09:10:20.517179341 +0900
	+++ /etc/clamav/clamd.conf	2018-05-21 15:16:22.140152503 +0900
	@@ -7,7 +7,7 @@
	 LocalSocketMode 666
	 # TemporaryDirectory is not set to its default /tmp here to make overriding
	 # the default with environment variables TMPDIR/TMP/TEMP possible
	-User clamav
	+#User clamav
	 ScanMail true
	 ScanArchive true
	 ArchiveBlockEncrypted false
	@@ -58,15 +58,15 @@
	 MaxQueue 100
	 ExtendedDetectionInfo true
	 OLE2BlockMacros false
	-ScanOnAccess false
	+#ScanOnAccess false
	 AllowAllMatchScan true
	 ForceToDisk false
	 DisableCertCheck false
	 DisableCache false
	-MaxScanSize 100M
	-MaxFileSize 25M
	+#MaxScanSize 100M
	+#MaxFileSize 25M
	 MaxRecursion 16
	-MaxFiles 10000
	+#MaxFiles 10000
	 MaxPartitions 50
	 MaxIconsPE 100
	 PCREMatchLimit 10000
	@@ -87,3 +87,26 @@
	 Bytecode true
	 BytecodeSecurity TrustSigned
	 BytecodeTimeout 60000
	+
	+# NOTE: The max possible value for MaxScanSize and MaxFileSize is 4000M.
	+# When I used the value like 4096M, I got the following warnings.
	+# WARNING: Numerical value for option MaxScanSize too high, resetting to 4G
	+# WARNING: Numerical value for option MaxFileSize too high, resetting to 4G
	+MaxScanSize 4000M
	+MaxFileSize 4000M
	+MaxFiles 100000
	+
	+# NOTE: User must be root in order to use ScanOnAccess.
	+# When I ran clamav-daemon with clamav User with ScanOnAccess true,
	+# I got the following error in journalctl.
	+# clamd[14963]: ScanOnAccess: clamd must be started by root
	+User root
	+ScanOnAccess true
	+OnAccessMountPath /home
	+VirusEvent /usr/local/bin/clamd-response
	+
	+# Config for Thunderbird clamdrib LIN extension
	+TCPSocket 3310
	+TCPAddr 127.0.0.1

:code:`/etc/systemd/system/clamav-daemon.socket` というファイルを以下のコマンドで作成しました。

.. code-block:: console

	cat <<'EOF' | sudo tee /etc/systemd/system/clamav-daemon.socket 
	[Unit]
	Description=clamav clamd socket

	[Socket]
	SocketUser=clamav
	ListenStream=127.0.0.1:3310
	EOF

さらに以下のコマンドを実行して設定ファイルの変更をsystemdに反映させます。

.. code-block:: console

	sudo systemctl daemon-reload

上記の :code:`VirusEvent` に指定した :code:`/usr/local/bin/clamd-response` は以下のコマンドで作成しました。ユーザ名の hnakamur の箇所は適宜変更してください。

.. code-block:: console

	cat <<'EOF' | sudo tee /usr/local/bin/clamd-response
	#!/bin/sh
	echo "$(date) - $CLAM_VIRUSEVENT_VIRUSNAME > $CLAM_VIRUSEVENT_FILENAME" >> /var/log/clamav/infected.log
	rm $CLAM_VIRUSEVENT_FILENAME
	sudo -u hnakamur DISPLAY=:0.0 notify-send "Virus Found $CLAM_VIRUSEVENT_VIRUSNAME" "$CLAM_VIRUSEVENT_FILENAME has been removed"
	EOF
	sudo chmod +x /usr/local/bin/clamd-response

以下のコマンドでサービスを再起動します。

.. code-block:: console

	sudo systemctl restart clamav-daemon.service clamav-daemon.socket clamav-freshclam.service

以下のコマンドでサービスの状態を確認します。

.. code-block:: console

	sudo systemctl status clamav-daemon.service clamav-daemon.socket clamav-freshclam.service

Scan On Accessの動作確認
========================

上記の実験用の無害なウィルスをChromeでダウンロードすると、上記のスクリプト :code:`/usr/local/bin/clamd-response` が動いて :code:`/var/log/clamav/infected.log` にメッセージが追記され、通知ポップアップが表示されることを確認しました。

Thunderbirdでのウィルスチェックの動作確認
=========================================

`ぺんぎん戦記 Thnderbirdアドオン clamdribの導入 <http://spacesheriffsharivan.blog9.fc2.com/blog-entry-98.html>`_ を参考に動作確認しました。

Thunderbirdとcramdlib LINアドオンをセットアップした状態で、clamdへの接続確認は cramdlib LINアドオンの設定画面の :code:`Test settings` ボタンを押して Success と表示されればOKです。

動作確認ですが、メールを1件選択すると「返信」ボタンが並んでいる上に :code:`ClamAV status: CLEAN` (CLEANは緑で表示)と無事表示されました。

ちなみに :code:`clamav-daemon` サービスを止めて試すと 
:code:`ClamAV status: CONNECTION PROBLEMS` (CONNECTION PROBLEMSは黄色で表示)という表示になりました。
