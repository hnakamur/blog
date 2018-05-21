Ubuntu MATE 18.04 LTSの私用設定メモ
###################################

:date: 2018-05-21 12:20
:modified: 2018-05-22 06:30
:tags: ubuntu, ubuntu-mate
:category: blog
:slug: 2018/05/21/my-settings-on-ubunt-mate

はじめに
========

USキーボードのThinkPad T480sでUbuntu MATE 18.04 LTSを試してみました。ということで自分用の設定メモです。

インストール
============

インストールはごくごく普通に
`Ubuntu flavours | Ubuntu <https://www.ubuntu.com/download/flavours>`_
からインストーラをダウンロードして `Etcher <https://etcher.io/>`_ でUSBメモリに書き出してインストールしました。
今回は試しに experimental CLI をLinux上で使ってみましたが、快適に使えました。

インストーラでの種類選択ではminimum installにしてみました。

Chromeのインストール
--------------------

`Ubuntu 18.04でaptを使ってchromeをインストール </blog/2018/05/04/install-chrome-using-apt-on-ubuntu-18.04/>`_ の手順でインストールしました。

KeepassXCのインストール
-----------------------

.. code-block:: console

        sudo apt install -y keepassxc


セットアップ
============

キーボードのCtrlとCapsLock入れ替え
----------------------------------

以下のコマンドを実行後、再起動で反映させました。

.. code-block:: console

        sudo sed -i -e 's/^XKBOPTIONS=""/XKBOPTIONS="ctrl:swapcaps"/' /etc/default/keyboard

タッチパッド設定
----------------

システムトレイの歯車アイコンから「システム設定」メニューを選び、「ハードウェア」の「マウス」を選んで「タッチパッド」タブで以下の設定をしました。

* 全般

    * 2本指クリックエミュレーション： 右ボタン
    * 3本指クリックエミュレーション： 中ボタン

* スクロール

    * 垂直エッジスクロール： オフ
    * 水平エッジスクロール： オフ
    * 垂直二本指スクロール： オン
    * 水平二本指スクロール： オン
    * 自然なスクロールを有効にする： オン

* ポインターの速度

    * 加速： 最大
    * 感度： 最大

キーボードショートカット
------------------------

システム設定の「ハードウェア」の「キーボードショートカット」で設定しました。無効にするには対象の行のショートカットの列を左クリックしたあとBackspaceキーを押します。左クリックした後、変更せずに抜けたい場合はEscを押します。

Windowsキーは Mod4 と表示されました。

* デスクトップ

    * 端末の起動： 無効

* ウィンドウの管理

    * ポップアップ・ウィンドウを利用してアプリケーションのウィンドウの間を移動する： Mod4+`
    * すべての通常のウィンドウを隠してデスクトップにフォーカスを移す： Shift+Mod4+D

「ポップアップ・ウィンドウを利用してアプリケーションのウィンドウの間を移動する」は同じアプリケーション内の複数のウィンドウを切り替えるショートカットですが、Firefoxではうまく動いたのですがChromeではうまく動きませんでした。

なお、Alt+Tabは「ポップアップ・ウィンドウを利用して、ウィンドウ間を移動する」になっていて、1アプリケーションで複数ウィンドウがある場合も順次移動する方式になっていました。個人的にはAlt+Tabはアプリケーションの切り替えにして、Windows+`など別のショートカットでアプリケーション内のウィンドウを切り替えたいのですが、Ubuntu MATEでの実現方法がわからないので、とりあえずこのまま使っています。

「すべての通常のウィンドウを隠してデスクトップにフォーカスを移す」を変更しているのは `Diigo Web Highlighter and Bookmark for Chrome | Diigo <https://www.diigo.com/tools/chrome_extension>`_ でCtrl+Shift+Dのショートカットを使いたいので、他のショートカットにしています。

端末の起動にデフォルトでCtrl+Shift+Tのショートカットが設定されているのですが、このショートカットで最大化して起動するようにしたかったので、上記のように元のショートカットを無効にして以下のように独自のショートカットを追加しました。

* 独自のショートカット

    * 名前： 端末を最大化で起動
    * コマンド： mate-terminal --window --maximize
    * ショートカット： Ctrl+Shift+T

なお、全てのウィンドウを最大化して開きたい場合は、この設定を使わずに、システム設定のMATE Tweakのウィンドウで「新しいウィンドウを自動で最大化しない」のチェックを外すという方法で対応可能です。が、私はターミナルだけ最大化で開きたいので上記の設定にしました。

日本語入力の切り替え
--------------------

インストーラで日本語を選択するとfcitxとmozcがインストールされて使える状態になっていました。

システム設定の「Fcitx設定」の「全体の設定」タブで「入力メソッドのオンオフ」を Alt+` に変更しました。

時計の表示設定
--------------

システムトレイの時計で右クリックして「設定」メニューの「全般」タブにて設定しました。

* 時計の書式： 24時間制
* 日付を表示する： オン
* 秒を表示する： オン
* カレンダに週番号を表示： オフ
* 天気を表示する： オフ
* 気温を表示する： オフ


MATE Tweak
----------

システム設定の「ルック＆フィール」の「MATE Tweak」で設定しました。

* デスクトップアイコン

    * デスクトップのアイコンを表示する： オフ 

私はデスクトップは使わないのでオフにしました。


「ダウンロード」などのフォルダ名を英語に変更
--------------------------------------------

`Ubuntu Mate 16.04 でフォルダ名を英語化したら Blueman のパスも修正する <https://rseiub.com/ubuntu-mate-folder-blueman-error>`_ を参考に変更しました。

.. code-block:: console

        env LANGUAGE=C LC_MESSAGES=C xdg-user-dirs-gtk-update

その後bluemanというBluetoothマネージャが「ダウンロード」ディレクトリがないとエラーを出すようになるので、以下のコマンドで設定変更しました。

.. code-block:: console

        gsettings set org.blueman.transfer shared-path "'/home/$USER/Downloads'"

設定できたかの確認は以下のようにします。

.. code-block:: console

        $ gsettings get org.blueman.transfer shared-path
        '/home/hnakamur/Downloads'

VeraCryptのインストールと設定
=============================

`VeraCryptでデータパーティションを暗号化してみた </blog/2018/04/22/use-VeraCrypt-for-data-partition/>`_ と 
`macOS High SierraとUbuntu 18.04でVeraCryptを使う </blog/2018/05/02/use-veracrypt-on-mac-os-high-sierra-and-ubuntu-18.04/>`_
の手順でインストールとセットアップしました。


L2TPでのVPN接続
===============

`Ubuntu 17.10でL2TPのVPN接続を試してみた </blog/2018/03/31/l2tp-vpn-on-ubuntu-17.10/>`_
と
`Ubuntu 18.04でVPN切断後にホスト名解決が動くようにするための回避策 </blog/2018/05/06/workaround-to-get-dns-working-after-vpn-disconnection-on-ubuntu-18.04/>`_ の手順でインストールとセットアップしました。

設定後、一度再起動ではVPNに接続エラーになったのですが、二度再起動したら接続できるようになりました。実は記事を書いた後何箇所かで同じ設定を試したのですが一度の再起動ではうまくいってなくて、試行錯誤しているうちに接続できるようになるというパターンになってました。原因は未調査です。

GUIのキーバインディングをEmacsライクにする
==========================================

`GNOME上でEmacsライクなキーバインディングを使う <http://127.0.0.1:8000/2018/05/06/use-emacs-like-keybindings-on-gnome/>`_ とほぼ同じですが、Ubuntu MATEの場合は :code:`org.gnome.desktop.interface` ではなく :code:`org.mate.interface` でした。

Emacsライクにするには以下のようにします。

.. code-block:: console

        $ gsettings set org.mate.interface gtk-key-theme Emacs

設定の確認は以下のようにします。

.. code-block:: console

        $ gsettings get org.mate.interface gtk-key-theme 
        'Emacs'

デフォルトに戻すには以下のようにします。

.. code-block:: console

        $ gsettings set org.mate.interface gtk-key-theme Default

Emacsライクなキーバインディングは便利ではあるのですが、URL欄にフォーカスがあるときにCtrl+Nで新しいウィンドウが開けないのが不便なのでデフォルトに戻しました。

ウィンドウ枠を広げてリサイズしやすくする
========================================

ウィンドウをリサイズするときに枠にマウスカーソルをポイントするのですが、リサイズカーソルになる範囲が狭すぎてタッチパッドの操作が辛いと思っていたら
`linux - MATE: how to increase window resizing area - Super User <https://superuser.com/questions/1012464/mate-how-to-increase-window-resizing-area/1027320#1027320>`_
に解決策が書かれていました。

以下のコマンドを実行して通常時のウィンドウ枠の左、右、下の太さを1から3に変えて再起動すると快適になりました。

.. code-block:: console

        sudo sed -e '/^<frame_geometry name="frame_geometry_normal"/,/<\/frame_geometry>/{
        s|<distance name="left_width" value="1"/>|<distance name="left_width" value="3"/>|
        s|<distance name="right_width" value="1"/>|<distance name="right_width" value="3"/>|
        s|<distance name="bottom_height" value="1"/>|<distance name="bottom_height" value="3"/>|
        }' /usr/share/themes/Ambiant-MATE/metacity-1/metacity-theme-1.xml
