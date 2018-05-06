GNOME上でEmacsライクなキーバインディングを使う
##############################################

:date: 2018-05-06 14:40
:tags: ubuntu, GNOME
:category: blog
:slug: 2018/05/06/use-emacs-like-keybindings-on-gnome

はじめに
========

元々macOSのChromeでURL欄を編集するときにEmacsライクなキーバインディングを使うのに慣れていたので、GNOMEのChromeもそう変更できないかと思って調べると以下の記事を見つけました。

`GNOMEのキーバインドをEmacs風に変更する - YAMAGUCHI::weblog <https://ymotongpoo.hatenablog.com/entry/2012/09/10/152133>`_

変更前の設定確認
================

変更前の設定を確認すると :code:`Default` となっていました。

.. code-block:: console

        $ gsettings get org.gnome.desktop.interface gtk-key-theme
        'Default'


設定変更
========

以下のコマンドを実行して設定変更します。

.. code-block:: console

        gsettings set org.gnome.desktop.interface gtk-key-theme Emacs
