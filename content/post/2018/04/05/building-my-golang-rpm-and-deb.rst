私のgoのrpmとdebをビルドする手順
################################

:date: 2018-04-05 11:21
:tags: go
:category: blog
:slug: 2018/04/05/building-my-golang-rpm-and-deb

はじめに
========

golangの非公式rpmとdebをビルドし始めてから結構経っていますが、自分のブログ記事に散らばっている
手順をピックアップしながら毎度ビルドしているのは良くないので、自分用にまとめておきます。
なおこの手順は私の手元の環境と自作コマンドに依存しているので、他の環境でコピペしても動きません。

以下ではバージョン1.10.1の例をメモします。

tarballのダウンロード
=====================

.. code-block:: console

	cd ~/golang-deb-work
        curl -LO https://dl.google.com/go/go1.10.1.src.tar.gz


golangのrpmをビルド
===================

srpmを作成
----------

rpmビルドの作業用gitレポジトリで新しいバージョン用にトピックブランチ作成。

.. code-block:: console

        cd ~/.ghq/github.com/hnakamur/golang-1.10-rpm
        g co -b 1_10_1

新しいtarballをSOURCESディレクトリに追加し、古いtarballはgitレポジトリから削除。

.. code-block:: console

        cp ~/go-deb-work/go1.10.1.src.tar.gz SOURCES/
        g rm SOURCES/go1.10.src.tar.gz

rpmのスペックファイルを更新。

.. code-block:: console

        vi SPECS/golang.spec

* :code:`%global go_version 1.10.1` の行を更新。
* nginxのバージョンの行 :code:`Version: 1.10.1` を更新。
* :code:`%changelog` セクションの先頭にエントリ追加。

.. code-block:: text

        %changelog
        * Thu Apr  5 2018 Hiroaki Nakamura <hnakamur@gmail.com> - 1.10.1-1
        - bump to 1.10.1

rpmビルドの作業用gitレポジトリに変更内容をコミット。

.. code-block:: console

        g a .
        g ci -m 'Update to 1.10.1'

srpmを作成。

.. code-block:: console

        mkdir ~/rpmbuild/SOURCES/golang-1.10.1-1
        ln -s $PWD/SOURCES/* !$
        rpmbuild -bs SPECS/golang.spec

mockコマンドを使ってローカルでビルド
------------------------------------

mockコマンドを使ってローカルでビルド。

.. code-block:: console

        /usr/bin/mock -r epel-7-x86_64 --resultdir=~hnakamur/mockresult-golang-1.10.1-1 --rebuild ~/rpmbuild/SRPMS/golang-1.10.1-1.src.rpm

うまくビルドできたときは :code:`~/mockresult-golang-1.10.1-1/` 以下に生成された :code:`*.rpm` をCentOS7の環境にコピーして :code:`yum install -y golang*.x86_64.rpm` でインストールして動作確認します。
ビルド失敗した場合はこのディレクトリの :code:`build.log` を見てエラーの内容を確認します。

.. code-block:: console

        hnakamur@express:~/.ghq/github.com/hnakamur/golang-1.10-rpm$ ls -lt ~/mockresult-golang-1.10.1-1
        total 136048
        -rw-rw-r-- 1 hnakamur hnakamur    81122 Apr  5 11:48 root.log
        -rw-rw-r-- 1 hnakamur hnakamur     1586 Apr  5 11:48 state.log
        -rw-rw-r-- 1 hnakamur hnakamur  1768912 Apr  5 11:48 build.log
        -rw-rw-r-- 1 hnakamur mock      8735608 Apr  5 11:48 golang-race-1.10.1-1.el7.centos.x86_64.rpm
        -rw-rw-r-- 1 hnakamur mock     15588632 Apr  5 11:48 golang-shared-1.10.1-1.el7.centos.x86_64.rpm
        -rw-rw-r-- 1 hnakamur mock     75041160 Apr  5 11:48 golang-bin-1.10.1-1.el7.centos.x86_64.rpm
        -rw-rw-r-- 1 hnakamur mock      5686740 Apr  5 11:46 golang-src-1.10.1-1.el7.centos.noarch.rpm
        -rw-rw-r-- 1 hnakamur mock      6831176 Apr  5 11:46 golang-tests-1.10.1-1.el7.centos.noarch.rpm
        -rw-rw-r-- 1 hnakamur mock       716016 Apr  5 11:46 golang-misc-1.10.1-1.el7.centos.noarch.rpm
        -rw-rw-r-- 1 hnakamur mock      2494336 Apr  5 11:46 golang-docs-1.10.1-1.el7.centos.noarch.rpm
        -rw-rw-r-- 1 hnakamur mock      1315652 Apr  5 11:46 golang-1.10.1-1.el7.centos.x86_64.rpm
        -rw-rw-r-- 1 hnakamur mock         9707 Apr  5 11:33 installed_pkgs
        -rw-rw-r-- 1 hnakamur mock     18221830 Apr  5 11:32 golang-1.10.1-1.el7.centos.src.rpm
        -rw-rw-r-- 1 root     root      2793543 Apr  5 11:32 available_pkgs

テスト環境でインストールしたgoのバージョン確認。

.. code-block:: console

        [root@centos7 ~]# go version
        go version go1.10.1 linux/amd64

dataraceチェッカー付きで実行可能なことを確認。

.. code-block:: console

        [root@centos7 ~]# mkdir -p ~/go/src/github.com/hnakamur/hello-go
        [root@centos7 ~]# cd !$
        [root@centos7 ~]# vi main.go

以下の内容で :code:`main.go` を作成。

.. code-block:: golang

        package main

        import (
                "fmt"
                "runtime"
        )

        func main() {
                fmt.Printf("Hello, %s!\n", runtime.Version())
        }

以下のように動作確認。

.. code-block:: golang

        [root@centos7 hello-go]# go run -race main.go
        Hello, go1.10.1!

coprでビルド
------------

.. code-block:: console

        copr-cli build hnakamur/golang-1.10 ~/mockresult-golang-1.10.1-1/golang-1.10.1-1.el7.centos.src.rpm

ビルドが完了したら
`hnakamur/nginx Copr <https://copr.fedorainfracloud.org/coprs/hnakamur/golang-1.10/>`_ のレポジトリを追加しているテスト環境にてgolangを更新して動作確認します。

rpmのgitレポジトリの更新とリリース作成
--------------------------------------

今回のトピックブランチをgithubにプッシュ。

.. code-block:: console

        g push origin 1_10_1

`hnakamur/nginx-rpm <https://github.com/hnakamur/nginx-rpm>`_ でプルリクエストを作成してマージ。

ローカルのmasterブランチを更新してトピックブランチを削除。

.. code-block:: console

        g f
        g co master
        g me origin/master --ff
        g delete-merged-branches

タグを作成してプッシュ。

.. code-block:: console

        g tag 1.10.1-1
        g push origin !$

coprでビルドされたrpmをダウンロードし、githubレポジトリにリリースを作成してアップロード。

.. code-block:: console

        copr-files-downloader -user hnakamur -repo golang-1.10 -dest ./tmp
        cd ./tmp
        github-release release --user hnakamur --repo golang-1.10-rpm --tag 1.10.1-1
        for i in $(ls); do github-release upload --user hnakamur --repo golang-1.10-rpm --tag 1.10.1-1 --name $i --file $i; done
        cd ..
        rm -r ./tmp

nginxのdebをビルド
==================

debのソースパッケージ作成
-------------------------

debビルドの作業用gitレポジトリで新しいtarballを取り込む。 :code:`gbp import-orig` の :code:`--pristine-tar` オプションを忘れないこと。これを忘れると後でソースパッケージをビルドする時にoriginのtarballがgitレポジトリから再構築され、後ほどPPAでビルドする時になってoriginのtarballが既に他のレポジトリでアップロードされていると同じファイル名で中身が一致しなくてエラーになってしまう。

.. code-block:: console

        cd ~/.ghq/github.com/hnakamur/golang-deb
        gbp import-orig --pristine-tar -u 1.10.1 ~/go-deb-work/go1.10.1.src.tar.gz

golang-debの場合は :code:`upstream-1.10` ブランチにオリジンのtarballを取り込んだ後 :code:`ubuntu-1.10` ブランチにマージするところまでやってくれます。

:code:`debian/changelog` の先頭にエントリを追加します。
以下のコマンドを実行すると前バージョンのタグ以降のコミットのコミットメッセージを並べて自動的にコミットメッセージを入力した状態で :code:`debian/changelog` を開いてくれます。

.. code-block:: console

        gbp dch -R

今回の例では :code:`debian/changelog` の先頭に以下のようにエントリが追加された状態で vim で開かれました。

.. code-block:: text

        golang-1.10 (1.10.1-1) xenial; urgency=medium

          * Imported Upstream version 1.10.1

         -- Hiroaki Nakamura <hnakamur@gmail.com>  Thu, 05 Apr 2018 11:41:04 +0900


これを以下のように変更します。

.. code-block:: text

        golang-1.10 (1.10.1-1ubuntu1ppa1~ubuntu16.04.1) xenial; urgency=medium

          * Imported Upstream version 1.10.1

         -- Hiroaki Nakamura <hnakamur@gmail.com>  Thu, 05 Apr 2018 11:41:04 +0900


:code:`debian/changelog` の変更をコミットしてタグを打ちます。

.. code-block:: console

        g ci . -m 'Release 1.10.1-1ubuntu1ppa1~ubuntu16.04.1'
        g tag debian/1.10.1-1ubuntu1ppa1-ubuntu16.04.1

pbuilderを使ってローカルでdebパッケージをビルド
-----------------------------------------------

debのソースパッケージをビルドします。

.. code-block:: console

        gbp buildpackage --git-export-dir=../build-area -p/home/hnakamur/bin/gpg-passphrase -S -sa

:code:`pbuilder` を使ってdebパッケージをビルドします。

.. code-block:: console

        sudo pbuilder build ../build-area/golang-1.10_1.10.1-1ubuntu1ppa1~ubuntu16.04.1.dsc

無事にビルドが終わったら :code:`/var/cache/pbuilder/result/golang*1.10.1*` にdebパッケージが作られます。

.. code-block:: console

        hnakamur@express:~/.ghq/github.com/hnakamur/golang-deb$ ls -lt /var/cache/pbuilder/result/golang*1.10.1*
        -rw-r--r-- 1 hnakamur hnakamur     4179 Apr  5 12:03 /var/cache/pbuilder/result/golang-1.10_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.changes
        -rw-r--r-- 1 hnakamur hnakamur  6600814 Apr  5 12:03 /var/cache/pbuilder/result/golang-1.10-go-shared-dev_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.deb
        -rw-r--r-- 1 hnakamur hnakamur    30042 Apr  5 12:03 /var/cache/pbuilder/result/golang-1.10_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_all.deb
        -rw-r--r-- 1 hnakamur hnakamur  2436718 Apr  5 12:03 /var/cache/pbuilder/result/golang-1.10-doc_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_all.deb
        -rw-r--r-- 1 hnakamur hnakamur 10182508 Apr  5 12:03 /var/cache/pbuilder/result/golang-1.10-src_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.deb
        -rw-r--r-- 1 hnakamur hnakamur 99426882 Apr  5 12:02 /var/cache/pbuilder/result/golang-1.10-go_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.deb
        -rw-r--r-- 1 hnakamur hnakamur     1996 Apr  5 11:46 /var/cache/pbuilder/result/golang-1.10_1.10.1-1ubuntu1ppa1~ubuntu16.04.1.dsc
        -rw-r--r-- 1 hnakamur hnakamur    32972 Apr  5 11:46 /var/cache/pbuilder/result/golang-1.10_1.10.1-1ubuntu1ppa1~ubuntu16.04.1.debian.tar.xz
        -rw-r--r-- 1 hnakamur hnakamur 18305765 Apr  5 11:43 /var/cache/pbuilder/result/golang-1.10_1.10.1.orig.tar.gz

作られたdebパッケージをfreightのローカルdebレポジトリに追加します。

.. code-block:: console

        pushd /var/www/html/my-debs
        sudo freight add /var/cache/pbuilder/result/golang*1.10.1*.deb apt/xenial
        sudo freight cache -p /home/hnakamur/.gpg-passphrase apt/xenial
        popd

テスト用のUbuntu環境にてfreightのdebレポジトリからgoのパッケージを更新します。

.. code-block:: console

        sudo apt update
        sudo apt upgrade -y golang-1.10-go golang-1.10-doc golang-1.10-src

rpmの場合と同様に :code:`go version` と :code:`go run -race main.go` で動作確認。

PPAでdebパッケージをビルド
--------------------------

動作確認して問題なければPPAでdebパッケージをビルドします。

.. code-block:: console

        dput ppa:hnakamur/golang-1.10 ../build-area/golang-1.10_1.10.1-1ubuntu1ppa1~ubuntu16.04.1_source.changes

`Packages in “golang 1.10” : golang 1.10 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10/+packages>`_ でこのバージョンのBuild Statusの列が緑のチェックマークになるまで待ちます（時計や緑の歯車のときはまだです）。

なかなかビルドが始まらない場合は https://launchpad.net/builders で状況を確認します。といっても結局待つしか無いです。

無事ビルドが完了したら `golang 1.10 : Hiroaki Nakamura <https://launchpad.net/~hnakamur/+archive/ubuntu/golang-1.10>`_ のレポジトリを追加してあるテスト環境にてgoのパッケージを更新して動作確認します。

.. code-block:: console

        sudo apt update
        sudo apt upgrade -y golang-1.10-go golang-1.10-doc golang-1.10-src

動作確認はrpmの場合と同様に :code:`go version` と :code:`go run -race main.go` です。

debのgitレポジトリの更新とリリース作成
--------------------------------------

ローカルのgitレポジトリでの変更をgithubに反映します。

一旦以下のコマンドでプッシュを試みます。

.. code-block:: console

        g push origin --all

:code:`patch-queue` ブランチがconflictする場合は、乱暴ですが :code:`-f` つきで再度プッシュします。まあ、 :code:`patch-queue` は一時的な作業用ブランチなのとこのgitレポジトリはチームではなく一人作業用なのでよしということで。

.. code-block:: console

        g push origin --all -f

タグもプッシュします。

.. code-block:: console

        g push origin --tags

PPAでビルドされたrpmをダウンロードし、githubレポジトリにリリースを作成してアップロード。

.. code-block:: console

        ppa-files-downloader -user hnakamur -repo golang-1.10 -pkg golang-1.10 -dest ./tmp
        cd ./tmp
        github-release release --user hnakamur --repo golang-deb --tag debian/1.10.1-1ubuntu1ppa1-ubuntu16.04.1
        for i in $(ls); do github-release upload --user hnakamur --repo golang-deb --tag debian/1.10.1-1ubuntu1ppa1-ubuntu16.04.1 --name $i --file $i; done
        cd ..
        rm -r ./tmp

