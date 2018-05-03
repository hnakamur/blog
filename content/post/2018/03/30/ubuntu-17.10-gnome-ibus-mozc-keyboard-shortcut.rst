Ubuntu 17.10とgnomeとIBus mozcのキーボードショートカットを自分好みに設定
########################################################################

:date: 2018-03-30 16:30
:modified: 2018-05-03 21:00
:tags: ubuntu, windows
:category: blog
:slug: 2018/03/30/ubuntu-17.10-gnome-IBus-mozc-keyboard-shortcut

はじめに
========

私はThinkPadとMacBook ProでともにUSキーボードを使っています。
Windows、macOS、Ubuntuでウィンドウ切り替えと日本語入力切り替えのキーボードショートカットを設定したのでメモです。
日本語入力はWindowsとmacOSでは `Google 日本語入力 – Google <https://www.google.co.jp/ime/>`_ 、
UbuntuではIBusと `google/mozc: Mozc - a Japanese Input Method Editor designed for multi-platform <https://github.com/google/mozc>`_ です。

デフォルトのキーボードショートカット
====================================

* `GNOME 3 keyboard shortcuts <https://gist.github.com/rothgar/7079722>`_
* `Keyboard shortcuts in Windows - Windows Help <https://support.microsoft.com/en-us/help/12445/windows-keyboard-shortcuts>`_
* `Mac のキーボードショートカット - Apple サポート <https://support.apple.com/ja-jp/HT201236>`_

上記に書いていないのもありますが、今回設定したいのは以下の3つの操作です。

========================== ================= =============== ===============
操作                       GNOME             Windows         macOS
========================== ================= =============== ===============
アプリ切り替え             alt + tab         alt + tab       command + tab
アプリ内ウィンドウ切り替え super + backquote (なし)          command + F1
日本語入力切り替え         super + space     alt + backquote command + space
========================== ================= =============== ===============

* superはThinkPadではWindowsキー、MacBook Proではcommandキーです。
* super, altのキーの並びはThinkPadでは左からsuper, altでMacBook Proではalt, superです。

日本語入力切り替えについての補足。
* Windowsでは入力ソースはGoogle日本語入力だけにしていて、Google日本語入力内で直接入力とひらがなを切り替えています。日本語キーボードだと全角/半角キーで切り替えですが、USキーボードだとalt + backquoteです。
* macOSではシステム環境設定のキーボードの入力ソースを「U.S.」と「ひらがな(Google)」の2つにしています。で、キーボードのショートカットの「入力メニューの次のソースを選択」のショートカットで切り替えています。
* Ubuntuでは「設定」の「地域と言語」で入力ソースを「英語(US)」と「日本語(Mozc)」の2つにしています（ `Ubuntuの日本語Remix <https://www.ubuntulinux.jp/japanese>`_ でセットアップするとこうなっていました）。で、「設定」→「デバイス」→「キーボード」の「次の入力ソースへ切り替える」のショートカットで切り替えています。

変更後のキーボードショートカット
================================

結論を先に書くと以下のように設定しました。

========================== ================= ================= =============== ===================
操作                       GNOME (ThinkPad)  GNOME (MacBook)   Windows         macOS
========================== ================= ================= =============== ===================
アプリ切り替え             alt + tab         super + tab       alt + tab       command + tab
アプリ内ウィンドウ切り替え super + backquote alt + backquote   (なし)          alt + backquote
日本語入力切り替え         alt + backquote   super + backquote alt + backquote command + backquote
========================== ================= ================= =============== ===================

設定変更手順は以下の通りです。

* GNOME (ThinkPad)

    * 「設定」→「デバイス」→「キーボード」の「次の入力ソースへ切り替える」を alt + backquote に変更。「前の入力ソースへ切り替える」は自動的にshift + alt + backquoteに変更される。

* GNOME (MacBook)

    * 「設定」→「デバイス」→「キーボード」の「次の入力ソースへ切り替える」を super + backquote に変更。「前の入力ソースへ切り替える」は自動的にshift + super + backquoteに変更される。

2018-05-03追記。初期状態では「設定」→「デバイス」→「キーボード」の「ひとつのアプリケーション内のウィンドウを切り替える」は「無効」となっていますが、実際は super + backquote と alt + backquote の両方が割り当てられています。上記のように super + backquote を「次の入力ソースに切り替える」に割り当てるだけではウィンドウ切り替えのほうが優先されてしまったので「ひとつのアプリケーション内のウィンドウを切り替える」を alt + backquote に明示的に設定する必要がありました。

ついでにもうひとつ。「すべての通常のウィンドウを隠す」も初期状態ではCtrl+Super+DとCtrl+Alt+Dの両方が割り当てられています。このうちCtrl+Alt+Dは私が愛用しているChromeでdiigoの拡張のショートカットと衝突しています。そこで「すべての通常のウィンドウを隠す」にCtrl+Super+Dを明示的に設定することでCtrl+Alt+Dの割り当てが解除されてdiigoで使えるようになります。

* Windows

   * 設定変更なし

* macOS

    * 「システム環境設定」→「キーボード」→「ショートカット」タブで「入力ソース」の「入力メニューの次のソースを選択」をcommand + backquote、「前の入力ソースを選択」をshift + command + backquoteに変更。
    * 「システム環境設定」→「キーボード」→「ショートカット」タブで「キーボード」の「次のウィンドウを捜査対象にする」をalt + backquoteに変更。


IBus mozcの初期状態をひらがなにする
===================================

IBus 1.5以降はデフォルトではIBus mozcの初期状態は「ひらがな」ではなく「直接入力」になっています。
おそらく入力ソースをmozcのみにして日本語キーボードの全角/半角キーで切り替えることを想定しているのだと推測します。

mozcの設定ではIMEの有効化や無効化の設定にaltやsuperのキーを含めることはできないようでした。
私はsuper + backquoteやalt + backquoteで日本語入力を切り替えたいのでmozcの設定はそのままにして
「英語(US)」と「日本語(Mozc)」の2つの入力ソースの切り替えを使うことにしました。

そうなるとmozcは起動状態で入力モードが「ひらがな」になってほしいわけです。検索してみると
`Is there a way to set hiragana as default? · Issue #381 · google/mozc <https://github.com/google/mozc/issues/381>`_ というイシューがあってそれを見ると `パッチ <https://github.com/hnakamur/mozc-deb/blob/90658a834d2905fe7b4aef2be4c39647689a4fd1/debian/patches/activate-on-launch.patch>`_ を当ててmozcをビルドすれば良いそうです。

ということでビルドして 
`mozc : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/mozc>`_
に置きました。

debパッケージのソースレポジトリは https://github.com/hnakamur/mozc-deb に置いています。
せっかくなので新しいパッケージをベースにしようと思い、Ubuntu 18.04用のパッケージ `Ubuntu – bionic の ibus-mozc パッケージに関する詳細 <https://packages.ubuntu.com/bionic/ibus-mozc>`_ をベースにしました。

これをインストールして再起動すれば私にとっては快適な環境になりました。
