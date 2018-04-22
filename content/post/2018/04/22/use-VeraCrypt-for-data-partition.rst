VeraCryptでデータパーティションを暗号化してみた
###############################################

:date: 2018-04-22 20:45
:tags: ubuntu, veraCcypt
:category: blog
:slug: 2018/04/22/use-VeraCrypt-for-data-partition

はじめに
--------

Windows 10とUbuntu 16.04のデュアルブート環境でデータ用のパーティションを `VeraCrypt - Free Open source disk encryption with strong security for the Paranoid <https://www.veracrypt.fr/en/Home.html>`_ で暗号化して
両方からマウントするというのを試してみたのでメモです。

`VeraCrypt - Wikipedia <https://ja.wikipedia.org/wiki/VeraCrypt>`_ によると開発が終了したTrueCryptというソフトウェアのフォークらしいです。

ファイルシステムはNTFSを選択
----------------------------

データパーティションのファイルシステムは何にしようかと思って検索してみると
`Ext2Fsd Project <http://www.ext2fsd.com/>`_ というのもみつけました。
これで、Windowsからext3やext4をマウントするという案もちょっとだけ考えたのですが、
2017-11-02の "Ext2Fsd 0.69 released !" の記事を眺めてみるとまだデータ消失のリスクがありそうな感じでした。

FAT32はジャーナルが無いのでファイルシステムで不整合が起きたときのことを考えると
ジャーナルのあるNTFSをLinuxからマウントするほうが良さそうと思いました。

検索してみると `NTFS-3G - Tuxera <https://www.tuxera.com/community/open-source-ntfs-3g/>`_ という
ドライバがあって読み書きともに安定して使えるようです。
`NTFS-3G - Wikipedia <https://ja.wikipedia.org/wiki/NTFS-3G>`_ と
`NTFS-3G - ArchWiki <https://wiki.archlinux.jp/index.php/NTFS-3G>`_ も眺めてみましたが良さそうです。

ということでNTFSを選択しました。

WindowsにVeraCryptをインストールしてデータパーティションを暗号化
----------------------------------------------------------------

データのドライブの作成とNTFSでのフォーマットは
`Windows10でのハードディスク（HDD）のフォーマット方法 - 株式会社センチュリー <http://www.century.co.jp/support/faq/windows-10-format.html>`_
のような感じで行いました。

「ドライブ文字またはパスの割り当て」では「ドライブ文字またはドライブパスを割り当てない」を選択しました。
VeraCrypt経由でアクセスするためのドライブを別に作るのでそちらにドライブ文字を割り当てるので、
元のパーティションでは不要という判断です。

ドライブ文字を割り当てても動作に問題はないのですが、エクスプローラで元のパーティションのドライブを選んでも
エラーになるだけなので割り当てる利点は薄いと思います。

VeraCryptについては `「VeraCypt」で暗号化された仮想ドライブを作成する手順 <https://freepc.jp/post-14806>`_ を参考にしました。
ただしダウンロードは `VeraCryptのダウンロードページ <https://www.veracrypt.fr/en/Downloads.html>`__ からにしました。また、VeraCryptボリューム作成ウィザードの箇所では「非システムパーティション/ドライブを暗号化」を選んで、上記で作成したデータ用のパーティションを選択しました。

Windowsのログオン時に自動的にマウントする設定
+++++++++++++++++++++++++++++++++++++++++++++

`VeraCryptのFAQ <https://www.veracrypt.fr/en/FAQ.html>`_ の
"Can a volume be automatically mounted whenever I log on to Windows?" に書かれていた手順で出来ました。

1. 対象のパーティションをマウントする。
2. VeraCryptのメインウィンドウでマウントしたドライブを選んで右クリックし "Add to Favorites" (お気に入りに追加)メニューを選択。
3. Favorites Orgranizerのウィンドウで "Mount selected volume upon logon" を有効にしてOKを押す。

Windowsのシャットダウンや再起動時は自動的にアンマウント
+++++++++++++++++++++++++++++++++++++++++++++++++++++++

また、同じページの
"Do I have to dismount VeraCrypt volumes before shutting down or restarting Windows?"
によるとWindowsのシャットダウンや再起動時は自動的にアンマウントされるとのことなので、手動でのアンマウントは不要です。

UbuntuにVeraCryptをインストールしてWindowsのVeraCryptで暗号化したパーティションをマウント
-----------------------------------------------------------------------------------------

`VeraCryptのダウンロードページ <https://www.veracrypt.fr/en/Downloads.html>`__ を見るとLinux用にもインストーラが用意されているのですが
`Encryption software : Unit 193 <https://launchpad.net/~unit193/+archive/ubuntu/encryption>`_ というPPAにUbuntu 16.04用のパッケージがありましたので、これを使わせて頂きました。ありがとうございます！

.. code-block:: console

        sudo add-apt-repository ppa:unit193/encryption
        sudo apt update
        sudo apt install veracrypt

インストール後は `死んだ後も安心！？VeraCryptで秘密のファイル置き場を作る方法 | Linux Fan <https://linuxfan.info/veracrypt>`_ を参考にして、上記でWindowsのVeraCryptで暗号化したパーティションをマウントしました。

マウントしたらWindowsのときと同様にお気に入りに追加しておきます。

LinuxのGUIでのログイン時に自動的にマウントする設定
++++++++++++++++++++++++++++++++++++++++++++++++++

1. 「アプリケーションを表示する」→「自動起動するアプリケーションの設定」をクリック。
2. 追加を押して以下の内容を追加。

    - 名前: VeraCryptボリュームマウント
    - コマンド: :code:`veracrypt --auto-mount=favorites`

Linuxのシャットダウンや再起動時も自動的にアンマウント
++++++++++++++++++++++++++++++++++++++++++++++++++++++

`mount - Do I have to dismount VeraCrypt volumes before shutting down or restarting Ubuntu? - Ask Ubuntu <https://askubuntu.com/questions/799277/do-i-have-to-dismount-veracrypt-volumes-before-shutting-down-or-restarting-ubunt/921884#921884>`_ によるとLinuxではシャットダウン時に自動でアンマウントはされないとあったのですが、実際に試してみるとjournalログにアンマウントされたようなメッセージが表示されていました。

VeraCrypt_1.22_Source.tar.bz2 内の Driver/Fuse/FuseService.cpp にも以下のようなコードがあったのでシグナルを受けたらアンマウントするようです。

.. code-block:: c++

        void FuseService::OnSignal (int signal)
        {
                try
                {
                        shared_ptr <VolumeInfo> volume = Core->GetMountedVolume (SlotNumber);

                        if (volume)
                                Core->DismountVolume (volume, true);
                }
                catch (...) { }

                _exit (0);
        }


おわりに
--------

これで暗号化したパーティションをデュアルブートのWindowsとLinuxの両方からマウント出来ました。
KeePass のデータファイルなどを置いています。

`System Encryption <https://www.veracrypt.fr/en/System%20Encryption.html>`_
や `How to Encrypt Your Windows System Drive With VeraCrypt <https://www.howtogeek.com/howto/6169/use-truecrypt-to-secure-your-data/>`_ によるとWindowsのシステムパーティションの暗号化も出来るようなので、いつか気が向いたらこちらも試してみたいです。
