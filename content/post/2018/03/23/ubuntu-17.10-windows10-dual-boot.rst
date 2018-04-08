Ubuntu 17.10とWindows10でデュアルブート構成にしてみた
#####################################################

:date: 2018-03-23 20:15
:modified: 2018-04-08 19:25
:tags: ubuntu, windows
:category: blog
:slug: 2018/03/23/ubuntu-17.10-windows10-dual-boot

はじめに
========

`Ubuntu 17.10とmacOS High Sierraでデュアルブート構成にしてみた </blog/2018/03/23/ubuntu-17.10-mac-os-high-sierra-dual-boot/>`_ の後、ThinkPad X260でUbuntu 17.10とWindows10でデュアルブート構成も試してみたのでメモです。

いろいろ試した後に今まとめてブログを書いているので、書くほうが追いついていなくて大変です。
ひとつずつ書いてから次を試せばいいんですが、気になると先に試してみたくなるので仕方ないといえば
仕方ないです。

こちらもほとんどの部分は上の記事と同じです。Windows10特有の話と上の記事に書き忘れたところを書いておきます。

インストール前の話
==================

Windows側でUbuntuインストール用の領域確保
-----------------------------------------

`Ubuntu16.04をWindows10とデュアルブート in UEFI - 極楽とんぼのロボット製作記 <http://www.g104robo.com/entry/ubuntu-dualboot-win10-uefi>`_ の「Ubuntu用パーティション作成」を参考にしてUbuntu用のパーティションを作成しました。

MacBookのときと同様 この時点では最終的なUbuntu用のパーティション構成を作るわけではなくて、Ubuntuをインストールする領域を確保するために1つパーティションを作る感じです。

Windowsのボリュームの縮小では動かせないファイルがある的なことを言われてエクスプローラでみたディスク使用量よりもかなり大きいサイズにまでしか縮小できませんでした。

まあでもとりあえず試すには十分な容量が確保できたので、一旦進めてみることにしました。いつか気が向いたらパーティションを切り直してWindowsとLinuxをクリーンインストールしてみたいです。

BitLockerドライブ暗号化の解除
-----------------------------

BIOSでUSBメモリから起動するようにしてもLinuxインストーラが起動せず、Secure Bootを無効にする必要があるらしいと知ったのですが、Secure Bootを無効にするとBitLocker暗号化されたドライブからWindowsが起動できないということを知りました。

仕方ないので一旦Secure Bootを有効に戻してBitLocker暗号化を解除しました。

手順は `Windows10 [ BitLockerの設定 ・解除 ] | ドキュメント | <http://www.fir.riec.tohoku.ac.jp/document/drive/bitlockerwin10/>`_ がわかりやすかったです。

デュアルブート構成でWindowsのドライブも暗号化する方法がもしあるなら今後試してみたいところです。

Secure Bootの無効化
-------------------

BIOSから無効化しました。機種は違いますが
`How to disable Secure Boot on a Lenovo G50 laptop | LinuxBSDos.com <http://linuxbsdos.com/2015/07/27/how-to-disable-secure-boot-on-a-lenovo-g50-laptop/>`_
と同じ感じです。

インストール中の話
==================

Ubuntuのインストール時にホームディレクトリ暗号化
------------------------------------------------

以前Ubuntuでサーバを構築したときはホームディレクトリの暗号化を一度試した後sshの鍵認証でハマって止めていました。
`Ubuntuでホームディレクトリを暗号化するのを止めた <https://hnakamur.github.io/blog/2016/05/02/uninstall-encrypted-home-on-ubuntu/>`_

今回はデスクトップからログインするのでこの問題は起きないだろうということで試してみました（実際は暗号化無しでインストールを試した後、暗号化有りで再度インストールしてみました）。ThinkPadもMacBookも暗号化ありにしてみました。

手順は `Ubuntu 17.10インストールガイド【スクリーンショットつき解説】 | Linux Fan <https://linuxfan.info/ubuntu-17-10-install-guide>`_ の「ユーザー情報の設定」画面で「ホームフォルダーを暗号化する」にチェックをつけるだけです。

インストール時もWiFiは使えました
---------------------------------
ThinkPad X260ではインストール時もWiFiが使えました。

インストール後の話
==================

CapsLockとCtrlキーの入れ替え
----------------------------

私はThinkPadもMacBookもUSキーボードを選択しています。

私の場合CapsLockとCtrlキーの入れ替えをしないとタイプミス連発して何もできないレベルなので
WindowsでもmacOSでもまず最初に設定していました。

ということでUbuntuでの設定方法を検索して
`コマンド一発でCapsLockをCtrlに変える方法 | Linux Fan <https://linuxfan.info/capslock-ctrl>`_ の
「コンソールでもCapsLockの動作を変更する方法（UbuntuなどDebian系）」の「CapsLockキーとCtrlキーを入れ替える」の手順で設定しました。

転記しておくと具体的には :code:`/etc/default/keyboard` の :code:`XKBOPTIONS` の値を以下のように書き換えて再起動です。

.. code-block:: console

    XKBOPTIONS="ctrl:swapcaps"

たぶんOS再起動までしなくても反映する方法はあるんでしょうが、調べてないです。
ThinkPadとMacBook両方でこの設定で使えています。


WindowsとAltの入れ替えはトライしたが断念
-----------------------------------------

MacBookとThinkPadに入れたUbuntuを触っていて違和感があると思ったら、
Super (Windowsキーとmacのcommandキー) とAltの並び順が逆なんでした。

ThinkPadでは左からWindowsキー、Altキー、スペースキーですが、
MacBook Proは左からaltキー、commandキー、スペースキーです。

:code:`/usr/share/X11/xkb/rules/base` に :code:`altwin:swap_alt_win` という設定があるのを見つけて
:code:`XKBOPTIONS="ctrl:swapcaps,altwin:swap_alt_win"` と設定してみたのですが、効かないようでした。
この件は深追いせずに断念しました。いつか気が向いたらまた調べるかも。

ファンクションのfnの挙動は最初から希望通り
------------------------------------------

MacBookのときとは違い、ThinkPadではfnなしでF1〜F12を押すとファンクションキーとして動作するようになってました。

タッチパッドの速度を最大に変更
------------------------------

これもmacOSでもWindowsでもいつもこの設定なのでUbuntuでも同様に設定しました。
設定→デバイス→マウスとタッチパッドと進んだところで設定できます。

タップでクリックなど他の設定はデフォルトで全て希望通りなのでそのまま使ってます。

WaylandからXorgに切り替え
-------------------------

`Canonical、Ubuntu 18.04 LTSではXorgをデフォルトに | スラド Linux <https://linux.srad.jp/story/18/01/27/1830219/>`_ という話は聞いていたので `【Ubuntu 17.10】WaylandからXorgに切り替えるべき7つの理由 | Linux Fan <https://linuxfan.info/ubuntu-17-10-switch-wayland-xorg>`_ という記事を見てXorgに切り替えておきました。

画面の解像度はデフォルトのまま
------------------------------

私のThinkPadの内蔵ディスプレイの解像度は1920x1080ですが、当たり前ですがディスプレイ設定もそうなっていてそのまま使っています。

ターミナルのフォントをCicaに変更
--------------------------------

私はWindowsでもmacOSでもターミナルのフォントはCicaにしています。
`miiton/Cica: プログラミング用日本語等幅フォント Cica(シカ) <https://github.com/miiton/Cica>`_ 

見やすいですし、絵文字や記号も充実していて非常に快適です。ありがとうございます！

`Releases · miiton/Cica <https://github.com/miiton/Cica/releases>`_ から最新版をダウンロードし、
`Ubuntu 17.10をインストールした直後に行う設定 & インストールするソフト <https://sicklylife.jp/ubuntu/1710/settings.html#font_in>`_ の「フォントを追加する」の手順で追加しました。

具体的には以下の手順です。

1. ブラウザでダウンロードしたzipファイルをファイルアプリでダブルクリックします。
2. アーカイブマネージャで*.ttfファイルを1つずつダブルクリックして開くとウィンドウのタイトルバーにインストールボタンがあるのでそれを押してインストールします。

その後Gnomeの端末アプリで以下の手順でCica Regularフォントに切り替えました。

1. [編集]→[プロファイルの設定]メニューを選択
2. [全般]タブの[フォントを指定する]にチェックを入れて、右のボタンを押してフォントを選択して設定

Windowsでブートしたときの時刻のずれを解消 (2018-04-08追記)
----------------------------------------------------------

UbuntuをインストールするとハードウェアクロックはUTCに設定されます。
一方Windowsはデフォルトではローカルタイムを想定しているので、Windowsでブートすると時刻がずれた状態になります。
自動設定を一度オフにして再度オンにすると治るのですが、リブートすると再発して困ってました。

過去のページを参考に設定したら解消できました。

* `UbuntuTime - Community Help Wiki <https://help.ubuntu.com/community/UbuntuTime#Multiple_Boot_Systems_Time_Conflicts>`_
* `Linux_Windowsデュアルブート環境時における時刻ずれの解決 - Varg <http://d.hatena.ne.jp/gin135/20140304/1393943319>`_

WindowsがハードウェアクロックのタイムゾーンをUTCとして扱うように変更するには、管理者権限でコマンドプロンプトを起動して以下のコマンドを実行し、再起動します。

.. code-block:: console

    reg add HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation /v RealTimeIsUniversal /t REG_DWORD /d 1

もし元に戻す場合は以下のコマンドを実行して再起動します。

.. code-block:: console

    reg delete HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation /v RealTimeIsUniversal /f

おわりに
========

覚えている範囲での設定変更はこんなものだと思います。デスクトップのキーボード・ショートカットの話とかは長くなるので別の記事にします。
