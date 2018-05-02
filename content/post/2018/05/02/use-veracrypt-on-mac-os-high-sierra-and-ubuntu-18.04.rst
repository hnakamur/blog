macOS High SierraとUbuntu 18.04でVeraCryptを使う
################################################

:date: 2018-05-02 21:00
:tags: veracrypt, mac, ubuntu
:category: blog
:slug: 2018/05/02/use-veracrypt-on-mac-os-high-sierra-and-ubuntu-18.04

はじめに
--------

`VeraCryptでデータパーティションを暗号化してみた </blog/2018/04/22/use-VeraCrypt-for-data-partition/>`_ ではWindows 10とUbuntu 17.10のデュアルブート環境でデータ用パーティションをマウントするというのを試しましたが、今回はmacOS High SierraとUbuntu 18.04のデュアルブート環境で試しました。前回と違うところだけメモしておきます。

データ用パーティションのフォーマットはexFATにした
-------------------------------------------------

`gerard/ext4fuse: EXT4 implementation for FUSE <https://github.com/gerard/ext4fuse>`_
というのを見つけたのですが現状は読み取り専用とのことなので見送りました。

FAT32よりはexFATのほうがファイルサイズの制限などもマシなのでそちらを使うことにしました。

macOSにVeraCryptをインストール
------------------------------

`VeraCrypt のダウンロードページ <https://www.veracrypt.fr/en/Downloads.html>`_ からmacOS用のインストーラをダウンロードしてインストールするのですが、そこに書いてあるように先に `FUSE for macOS <https://osxfuse.github.io/>`_ をインストールしてからにします。

macOSログイン時にお気に入りを自動マウント
+++++++++++++++++++++++++++++++++++++++++

自動マウント用のスクリプトを書いてシステム環境設定の「ユーザとグループ」にある「ログイン項目」に設定しようかと思ったのですが、 `terminal - Can Login Items be added via the command line in High Sierra? - Ask Different <https://apple.stackexchange.com/questions/310495/can-login-items-be-added-via-the-command-line-in-high-sierra>`_ とそこからリンクされている `Can't remove 'unknown login items'? - Apple Community <https://discussions.apple.com/thread/8086931>`_ を見るとHigh Sierraでは挙動がおかしいらしいです。

また `Customizing Login and Logout <https://developer.apple.com/library/content/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CustomLogin.html#//apple_ref/doc/uid/10000172i-SW10-BAJCGEGG>`_ というのも見つけたのですがdeprecatedらしいです。

ということで、そこからリンクされている `Creating Launch Daemons and Agents <https://developer.apple.com/library/content/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html#//apple_ref/doc/uid/10000172i-SW7-BCIEDDBJ>`_ のLaunch Agentsで対応することにしました。

以下の内容で :code:`~/Library/LaunchAgents/veracrypt.auto-mount-favorites.plist` というファイルを作成します。

.. code-block:: xml

        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>veracrypt.auto-mount-favorites</string>
            <key>ProgramArguments</key>
            <array>
                <string>/Applications/VeraCrypt.app/Contents/MacOS/VeraCrypt</string>
                <string>--auto-mount=favorites</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
        </dict>
        </plist>

以下のコマンドを実行して設定を反映します。

.. code-block:: console

        launchctl load ~/Library/LaunchAgents/veracrypt.auto-mount-favorites.plist

これでログイン時にダイアログが表示されて、お気に入りを自動マウント出来ます。
ダイアログは2つ表示されます。1つめは管理者権限になるために自分のユーザのパスワードを入力し、2つめはVeraCryptでパーティションを暗号化した時に設定したパスワードを入力します。

Ubuntu 18.04にVeraCryptをインストール
-------------------------------------

前回同様 `Encryption software : Unit 193 <https://launchpad.net/~unit193/+archive/ubuntu/encryption>`_ のPPAを見て見るとUbuntu 18.04用のパッケージも提供されていたのでこちらを使わせて頂きました。

.. code-block:: console

        sudo add-apt-repository ppa:unit193/encryption
        sudo apt update
        sudo apt install veracrypt

インストールして使っていると libcanberra-gtk-module というモジュールが見つからないという警告が出ていたので追加でインストールしました
。

.. code-block:: console

        sudo apt install libcanberra-gtk-module
