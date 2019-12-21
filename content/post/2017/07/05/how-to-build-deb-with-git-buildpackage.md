+++
title="git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順"
date = "2017-07-05T21:04:00+09:00"
tags = ["deb", "git-buildpackage"]
categories = ["blog"]
+++


## はじめに

.. _git-buildpackage: https://honk.sigxcpu.org/piki/projects/git-buildpackage/

git-buildpackage_ を使ってカスタムdebパッケージをビルドして [Personal Package Archives : Ubuntu](https://launchpad.net/ubuntu/+ppas) (PPA) にアップロードする手順のメモです。

自分で試行錯誤してまとめた手順なので、他のニーズには合わなかったり、改善の余地があるかもしれません。

UbuntuのLTS (Long Time Support)版を使うにあたって、古いdebパッケージをアップデートしてPPAにアップデートするのが主な用途です。

ということで以下では Ubuntu 16.04 (xenial) で提供されている luajit 2.0.4 を2.0.5にアップデートしてPPAにアップロードする例で説明します。

## まず読む参考文献

debパッケージ作成についての文書はたくさんあるのですが、
[Debian 開発者向けマニュアル](https://www.debian.org/doc/devel-manuals#packaging-tutorial) が概要を把握するのに役立ちました。

次に [Debian 新メンテナガイド](https://www.debian.org/doc/devel-manuals#maint-guide) を見ました。といってもどちらも斜め読みです。

## 使用するツールの選択

debパッケージをビルドするツールも多数あるのですが、
[git-buildpackageコマンドとその仲間](https://www.debian.org/doc/manuals/maint-guide/build.ja.html#git-buildpackage) でお勧めされていた git-buildpackage_ を使うことにしました。

[Building Debian Packages with git-buildpackage](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.html) を読んで試行錯誤した結果、以下のツールを使う手順にひとまず落ち着きました。

* git-buildpackage_: gitでdebパッケージのソースを管理してビルドするための支援ツール
* [Quilt](http://savannah.nongnu.org/projects/quilt): パッチ管理ツール。
* pbuilder (personal builder): chrootでクリーンな環境でdebパッケージをビルドするためのツール。
* dput: debのソースパッケージをPPAにアップロードするツール

## 事前準備

### gpgで秘密鍵作成

PPAにdebパッケージをアップロードするにはdebソースパッケージに署名する必要があるので [gpgで秘密鍵を作成する](https://hnakamur.github.io/blog/2017/07/01/generate-secret-key-with-gpg/) の手順で秘密鍵を生成しておきます。

### gpgの設定追加

[packaging - How to automate the pass phrases when GPG signing dpkg-buildpackage? - Ask Ubuntu](https://askubuntu.com/questions/186329/how-to-automate-the-pass-phrases-when-gpg-signing-dpkg-buildpackage/186359#186359)
を参考にして `~/.bash_profile` に以下のような設定を追加しました。
`DEBFULLNAME` 、 `DEBEMAIL` 、 `GPGKEY` 環境変数の値は、適宜自分のものに書き換えてください。

```text
# http://manpages.ubuntu.com/manpages/precise/en/man1/dch.1.html
export DEBFULLNAME="Hiroaki Nakamura"
export DEBEMAIL="hnakamur@gmail.com"

# https://askubuntu.com/questions/186329/how-to-automate-the-pass-phrases-when-gpg-signing-dpkg-buildpackage
export GPGKEY=0x1DFBC664
```

Ubuntuでは `~/.bash_profile` が存在すると `~/.bashrc` が読まれないようなので、以下のようなコードを
`~/.bash_profile` に追加しました。

```text
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
```

ログインし直すか以下のコマンドを実行して、上記の設定を反映します。

```console
exec $SHELL -l
```

### 必要なパッケージのインストール

次に Ubuntu 16.04 xenialで以下のコマンドを実行して必要なツールをインストールします。

```console
sudo apt install git-buildpackage quilt pbuilder debootstrap devscripts dput debhelper
```

2018-03-20 追記 debhelper も必要だったので上記に追記しました。

### pbuilderで使うchroot環境作成

[PbuilderHowto - Ubuntu Wiki](https://wiki.ubuntu.com/PbuilderHowto) と [Ubuntu Manpage: pbuilder - personal package builder](http://manpages.ubuntu.com/manpages/xenial/en/man8/pbuilder.8.html) を参考に、以下のコマンドでdebパッケージビルド用のchroot環境のtarballを作成します。

`--components` オプションで `main` に加えて `universe` も指定しているのはビルド時に必要となる `quilt` が `main` ではなく `universe` に含まれるからです。

```console
sudo pbuilder create --components 'main universe' --debootstrapopts --variant=buildd
```

### quiltのセットアップ

[quilt のセットアップ](https://www.debian.org/doc/manuals/maint-guide/modify.ja.html#quiltrc) の手順に沿ってdebパッケージビルド用にquiltの設定を追加し、 `dquilt` というエイリアスを登録します。

`~/.bashrc` に以下の2行を追加します。

```text
alias dquilt="quilt --quiltrc=${HOME}/.quiltrc-dpkg"
complete -F _quilt_completion -o filenames dquilt
```

以下の内容で `~/.quiltrc-dpkg` ファイルを作成します。

```text
d=. ; while [ ! -d $d/debian -a `readlink -e $d` != / ]; do d=$d/..; done
if [ -d $d/debian ] && [ -z $QUILT_PATCHES ]; then
    # if in Debian packaging tree with unset $QUILT_PATCHES
    QUILT_PATCHES="debian/patches"
    QUILT_PATCH_OPTS="--reject-format=unified"
    QUILT_DIFF_ARGS="-p ab --no-timestamps --no-index --color=auto"
    QUILT_REFRESH_ARGS="-p ab --no-timestamps --no-index"
    QUILT_COLORS="diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:diff_hunk=1;33:diff_ctx=35:diff_cctx=33"
    if ! [ -d $d/debian/patches ]; then mkdir $d/debian/patches; fi
fi
```

### PPAのアカウント作成

その前に、なぜPPAでdebパッケージをビルド・配布することにしたかですが、これは
[Launchpadを利用してパッケージを公開するには - ククログ(2014-06-10)](http://www.clear-code.com/blog/2014/6/10.html)
の記事を読んで、私の場合もデメリットよりメリットが大きいと思ったからです。

この記事の「最初にする作業」の「Launchpadへのユーザー登録」から「PPAの登録」までを行ってください。「dputの設定」の設定は不要です。なお、私自身はLaunchPadへのユーザ登録は11年前にしていて今回登録手順は確認しておらず、この記事も3年前なので、今の手順は多少変わっているかもしれません。

うまくいかない場合は
[YourAccount/NewAccount - Launchpad Help](https://help.launchpad.net/YourAccount/NewAccount)
や
[YourAccount/ImportingYourPGPKey - Launchpad Help](https://help.launchpad.net/YourAccount/ImportingYourPGPKey)
などで手順を確認して登録を行ってください。

PPA (Personal Package Archive) についての公式な説明は
[Packaging/PPA - Launchpad Help](https://help.launchpad.net/Packaging/PPA)
にあります。

## 既存のdebパッケージのソースを取得

`/etc/apt/sources.list` に以下のように `deb-src` の行があるか確認します。私の環境では対応する `deb` の行の下にばらけて書かれていました。

```text
deb-src http://jp.archive.ubuntu.com/ubuntu/ xenial main restricted
deb-src http://jp.archive.ubuntu.com/ubuntu/ xenial-updates main restricted
deb-src http://jp.archive.ubuntu.com/ubuntu/ xenial universe
deb-src http://jp.archive.ubuntu.com/ubuntu/ xenial-updates universe
```

`deb-src` の行がない場合は `/etc/apt/sources.list` に追記するか `/etc/apt/sources.list.d/` ディレクトリに `src.list` のように拡張子 `.list` のファイルを作成して、 `sudo apt update` コマンドを実行します。


作業用のディレクトリを作成してそこに移動します。以下では `~/deb-tutorial/luajit` を作業ディレクトリとします。

```console
mkdir -p ~/deb-tutorial/luajit
cd !$
```

以下のコマンドを実行して `luajit` のdebソースパッケージをダウンロードします。

```console
apt source luajit
```

以下のような1つのディレクトリと3つのファイルが作成されます。

```console
$ ls -F
luajit-2.0.4+dfsg/  luajit_2.0.4+dfsg-1.debian.tar.xz  luajit_2.0.4+dfsg-1.dsc  luajit_2.0.4+dfsg.orig.tar.gz
```

## debパッケージのgitレポジトリを作成

### debパッケージ用にgitレポジトリを分けて管理する理由

当初はupstreamであるluajitのgitレポジトリにdebパッケージ用のブランチを作って管理しようかと思っていました。

ですが [Debian Enhancement Proposals](http://dep.debian.net/) に [DEP-14: Recommended layout for Git packaging repositories](http://dep.debian.net/deps/dep14/) という文書があって、なるべくこのgitブランチモデルに合わせたほうが良いかなと思い、 [git.debian.org](https://anonscm.debian.org/cgit/) にあるDebianのパッケージのgitレポジトリの実例をいくつか見て合わせることにしました。

それにupstreamのgitコミットログとdebパッケージ用のコミットログが混在するより、debパッケージのgitレポジトリが分かれているほうがdebパッケージのコミットログだけを見やすそうだと思い直しました。


### upstreamのソースをインポートしてdebパッケージのgitレポジトリを作成

[Importing Sources](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.import.html) の [Importing already existing Debian packages](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.import.html#GBP.IMPORT.EXISTING) の手順でインポートします。
コマンド名は `git-buildpackage` の略で `gbp` となっています。

```console
gbp import-dsc --pristine-tar luajit_2.0.4+dfsg-1.dsc
```

すると `luajit` というディレクトリが作成されます。

```console
$ ls -F
luajit/  luajit-2.0.4+dfsg/  luajit_2.0.4+dfsg-1.debian.tar.xz  luajit_2.0.4+dfsg-1.dsc  luajit_2.0.4+dfsg.orig.tar.gz
```

`luajit` という名前のままだと、後で github にdebパッケージのレポジトリを上げるときに upstream の `luajit` をフォークするときに自分のディレクトリの下で名前が衝突するので `luajit-deb` に改名してそこに移動します。

```console
mv luajit luajit-deb
cd !$
```

`master` 、 `pristine-tar` 、 `upstream` の3つのブランチがあり今は `master` ブランチにいます。

```console
$ git branch
* master
  pristine-tar
  upstream
```

`ls -F` で見ると luajit のソースに加えてdebパッケージ用の `debian/` ディレクトリがあることがわかります。

```console
$ ls -F
COPYRIGHT  debian/  dynasm/  etc/  Makefile  README  src/
```

## luajitのgitレポジトリをクローンしてバージョン2.0.5のソースを準備

`pushd` で一旦別のディレクトリに移動して、そちらでluajitのgitレポジトリをクローンし、 `v2.0.5` のタグに切り替えて `~/deb-tutorial/luajit/luajit_2.0.5.orig.tar.gz` というtarballを作成し `popd` で元の作業ディレクトリに戻ります。

```console
pushd ..
git clone http://luajit.org/git/luajit-2.0.git
cd luajit-2.0
```

.. code-block:: console

    hnakamur@express:~/deb-tutorial/luajit/luajit-2.0$ git tag
    v2.0.0
    v2.0.0-beta1
    v2.0.0-beta10
    v2.0.0-beta11
    v2.0.0-beta2
    v2.0.0-beta2-hotfix2
    v2.0.0-beta3
    v2.0.0-beta4
    v2.0.0-beta5
    v2.0.0-beta6
    v2.0.0-beta7
    v2.0.0-beta8
    v2.0.0-beta8-fixed
    v2.0.0-beta9
    v2.0.0-rc1
    v2.0.0-rc2
    v2.0.0-rc3
    v2.0.1
    v2.0.1-fixed
    v2.0.2
    v2.0.3
    v2.0.4
    v2.0.5
    v2.1.0-beta1
    v2.1.0-beta2
    v2.1.0-beta3

```console
git checkout v2.0.5
```

.. code-block:: console

    git archive --format=tar.gz --prefix=luajit/ -o ../luajit_2.0.5.orig.tar.gz tags/v2.0.5

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-2.0$ popd
~/deb-tutorial/luajit/luajit-deb
```

## luajitバージョン2.0.5のソースをインポート

### debパッケージのDFSG対応

luajitのdebパッケージのバージョンは `2.0.4+dfsg-1` のように `+dfsg` を含んでいます。

DFSGについては [Debian フリーソフトウェアガイドライン (DFSG)](https://www.debian.org/social_contract#guidelines) に説明があり、 debパッケージの DFSG 対応については [第2章 はじめの一歩](https://www.debian.org/doc/manuals/maint-guide/first.ja.html#namever) に説明があります。

luajitの場合は `debian/README.source` に具体的な説明があり、 `doc/` ディレクトリにあるファイルのライセンスが DSFG に合わないので削除してdebパッケージに含めないという対応にしているそうです。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ cat debian/README.source
The upstream sources contain .css files that do not conform to DFSG, since
the following banner prevents their reuse.

  /* Copyright (C) 2004-2009 Mike Pall.
   *
   * You are welcome to use the general ideas of this design for your own
   * sites.  But please do not steal the stylesheet, the layout or the
   * color scheme.
   */

Moreover the upstream made explicit that .html files (will) be licensed
under terms not suitable for Debian:

  > If you insist it is unreadable, I can write a simple css to just format
  > the page, and make it MIT/X.

  The HTML files contain a copyright, too. And I haven't decided on
  a license for them, either. I.e. they are unacceptable for Debian.

  Most users search online for the docs, anyway. And the online URL
  for the docs is e.g. printed at startup.

The sources has been repackaged removing doc/*.
```

### DFSGクリーンでないupstreamのソースのインポート

[Handling non-DFSG clean upstream sources](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.special.html#GBP.SPECIAL.DFSGFREE) に沿ってluajitのバージョン2.0.5のソースをインポートしていきます。

まず `upstream` ブランチから `dfsg_clean` というブランチを作成します。

```console
git branch dfsg_clean upstream
```

`master` ブランチに切り替えてから、先程生成した `~/deb-tutorial/luajit/luajit_2.0.5.orig.tar.gz` をインポートします。
(2018-04-25修正。 `gbp import-orig` を実行するときは `upstream` ではなく `master` ブランチに切り替えておく必要がありました。)

```console
git checkout master
gbp import-orig --no-merge -u 2.0.5 --pristine-tar ~/.ghq/luajit.org/git/luajit_2.0.5.orig.tar.gz
```

この時点で `upstream/2.0.5` というタグが追加されています。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ git tag
debian/2.0.4+dfsg-1
upstream/2.0.4+dfsg
upstream/2.0.5
```

`dfsg_clean` ブランチに切り替えて `upstream` ブランチの内容をマージして取り込みます。

```console
git checkout dfsg_clean
git pull . upstream
```

ディレクトリの内容を確認するとupstreamのソースを取り込んだので `doc/` ディレクトリが復活しています。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ ls -F
COPYRIGHT  doc/  dynasm/  etc/  Makefile  README  src/
```

DFSGクリーンにするため、 `doc/` ディレクトリを削除してコミットします。

```console
git rm -r doc
git commit -m "Make source dfsg clean"
```

この後 `git-buildpackage` の `gbp` コマンドでdebソースパッケージをビルドする際に参照するため `upstream/2.0.5+dfsg` タグを打っておきます。

```console
git tag upstream/2.0.5+dfsg
```

`upstream` ブランチ上ではなく `dfsg_clean` ブランチ上に `upstream/*` というタグを打つのは最初混乱したのですが、 `gbp` コマンドから DFSGクリーンなソースのタグを参照するためにこうする必要があります。（元々DSFGクリーンなパッケージの場合は上記の `gbp import-orig` を実行した時に作成される `upstream/バージョン` というタグだけで大丈夫です）。

次に `master` ブランチに切り替えて `dfsg_clean` ブランチの内容をマージして取り込みます。

```console
git checkout master
git pull . dfsg_clean
```

## dquiltでパッチファイルを更新

### debパッケージでのパッチファイルのファイル構成

`debian/patches/` ディレクトリを見ると以下のように1つのパッチファイルがあります。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ ls debian/patches/
0001-consider-Hurd-as-a-POSIX-system.patch  series
```

`debian/patches/series` ファイルにパッチファイル名一覧が書かれています。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ cat debian/patches/series
0001-consider-Hurd-as-a-POSIX-system.patch
```

### dquiltでのパッチの更新

[アップストリームのバグを修正する](https://www.debian.org/doc/manuals/maint-guide/modify.ja.html#fixupstream) に新規パッチ作成例が書かれていますが、今回は既存のパッチの更新なのでこれとは違います。

`man quilt` やそこで紹介されていた `/usr/share/doc/quilt/quilt.pdf` を読むべきところですが、 `パッチ管理ツール quilt の使い方](http://tokyodebian.alioth.debian.org/html/debianmeetingresume200701se7.html.tmp) がわかりやすかったのでお勧めです。

ここでは上記の事前準備に書いたように `quilt` そのままではなく をカスタマイズしたエイリアス `dquilt` を利用します。

まず `dquilt push` でパッチを当ててみるとオフセットがありつつもパッチ当てに成功しました。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ dquilt push
Applying patch 0001-consider-Hurd-as-a-POSIX-system.patch
patching file src/Makefile
Hunk #1 succeeded at 326 (offset -1 lines).
patching file src/lj_arch.h
Hunk #1 succeeded at 75 with fuzz 2 (offset 4 lines).

Now at patch 0001-consider-Hurd-as-a-POSIX-system.patch
```

gitレポジトリの状態を確認すると以下のようになっていました。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ git status -sb
## master
 M src/Makefile
 M src/lj_arch.h
?? .pc/
```

差分は以下の通りです。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ git diff -w
diff --git a/src/Makefile b/src/Makefile
index f7f81a4..0251f43 100644
--- a/src/Makefile
+++ b/src/Makefile
@@ -326,6 +326,9 @@ else
   ifeq (GNU/kFreeBSD,$(TARGET_SYS))
     TARGET_XLIBS+= -ldl
   endif
+  ifeq (GNU,$(TARGET_SYS))
+    TARGET_XLIBS+= -ldl
+  endif
 endif
 endif
 endif
diff --git a/src/lj_arch.h b/src/lj_arch.h
index e04c4ee..f16db22 100644
--- a/src/lj_arch.h
+++ b/src/lj_arch.h
@@ -75,6 +75,8 @@
 #elif defined(__CYGWIN__)
 #define LJ_TARGET_CYGWIN       1
 #define LUAJIT_OS      LUAJIT_OS_POSIX
+#elif defined(__GNU__)
+#define LUAJIT_OS      LUAJIT_OS_POSIX
 #else
 #define LUAJIT_OS      LUAJIT_OS_OTHER
 #endif
```

パッチの内容も問題なさそうなので `dquilt refresh` でパッチを更新します。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ dquilt refresh
Refreshed patch 0001-consider-Hurd-as-a-POSIX-system.patch
```

`.pc/` というディレクトリが出来ていますが不要なので削除し、 `src/Makefile` と `src/lj_arch.h` はコミットします。

```console
rm -rf .pc
git commit -a -m 'Update patch'
```

## debian/changelogの更新

[Releases and Snapshots](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.releases.html) を参考に以下のコマンドを実行します。

```console
gbp dch --release
```

するとエディタが起動して `debian/changelog` ファイルを開いた状態になり、ファイルの先頭には `gbp` コマンドが追加した以下のようなエントリが表示されていました。

```text
luajit (2.0.5-1) xenial; urgency=medium

  * Imported Upstream version 2.0.5
  * Make source dfsg clean
  * Update patch

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Thu, 06 Jul 2017 00:55:06 +0900
```

これを以下のように編集しました。
バージョン番号は [Packaging/PPA/BuildingASourcePackage - Launchpad Help](https://help.launchpad.net/Packaging/PPA/BuildingASourcePackage) の命名規則に沿って `2.0.5+dfsg-1ppa1` としました。これでこの後ビルドするときに `upstream/2.0.5+dfsg` タグが参照されるというわけです。

```text
luajit (2.0.5+dfsg-1ppa1) xenial; urgency=medium

  * New upstream release

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Thu, 06 Jul 2017 00:55:06 +0900

luajit (2.0.4+dfsg-1) unstable; urgency=medium
```

gitレポジトリの状態を確認すると `debian/changelog` が変更された状態になっています。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ git status -sb
## master
 M debian/changelog
```

`debian/changelog` をコミットします。

```console
git commit -m 'Release 2.0.5' debian/changelog
```

## ソースパッケージのビルド

後ほどPPAにアップロードするときはdebのソースパッケージのみをアップロードする必要があります。

まず以下のコマンドを実行してソースパッケージのみをビルドします。
[Options when building](https://help.launchpad.net/Packaging/PPA/BuildingASourcePackage)
によると既存のパッケージの別バージョンの場合は `-S -sd` というオプションを使うと書いてあるのですが、
今回はPPAに luajit を初めて登録するので `-S -sa` にしました。

このオプションについては `man gbp-buildpackage` 、 `man debuild` 、 `man dpkg-buildpackage`
と辿って
[man dpkg-genchanges](http://manpages.ubuntu.com/manpages/xenial/en/man1/dpkg-genchanges.1.html)
に説明がありました。

途中 `Enter passphrase:` というプロンプトが2回表示されるのでgpgのパスフレーズを入力します。
`gpg: gpg-agent is not available in this session` というメッセージが
`Enter passphrase:` と同じ行に続いて表示される場合があって気づきにくいので注意してください。

```console
$ gbp buildpackage --git-pristine-tar-commit --git-export-dir=../build-area -S -sa
gbp:info: Exporting 'HEAD' to '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-tmp'
gbp:info: Moving '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-tmp' to '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-2.0.5+dfsg'
 dpkg-buildpackage -rfakeroot -d -us -uc -i -I -S -sa
dpkg-buildpackage: source package luajit
dpkg-buildpackage: source version 2.0.5+dfsg-1ppa1
dpkg-buildpackage: source distribution xenial
dpkg-buildpackage: source changed by Hiroaki Nakamura <hnakamur@gmail.com>
 dpkg-source -i -I --before-build luajit-2.0.5+dfsg
 fakeroot debian/rules clean
dh --with quilt clean
   dh_testdir
   dh_auto_clean
        make -j1 clean
make[1]: Entering directory '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-2.0.5+dfsg'
make -C src clean
make[2]: Entering directory '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-2.0.5+dfsg/src'
rm -f luajit libluajit.a libluajit.so host/minilua host/buildvm lj_vm.s lj_bcdef.h lj_ffdef.h lj_libdef.h lj_recdef.h lj_folddef.h host/buildvm_arch.h jit/vmdef.lua *.o host/*.o *.obj *.lib *.exp *.dll *.exe *.manifest *.pdb *.ilk
make[2]: Leaving directory '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-2.0.5+dfsg/src'
make[1]: Leaving directory '/home/hnakamur/deb-tutorial/luajit/build-area/luajit-2.0.5+dfsg'
   dh_quilt_unpatch
No patch removed
   dh_clean
 dpkg-source -i -I -b luajit-2.0.5+dfsg
dpkg-source: info: using source format '3.0 (quilt)'
dpkg-source: info: building luajit using existing ./luajit_2.0.5+dfsg.orig.tar.gz
dpkg-source: info: building luajit in luajit_2.0.5+dfsg-1ppa1.debian.tar.xz
dpkg-source: info: building luajit in luajit_2.0.5+dfsg-1ppa1.dsc
 dpkg-genchanges -S -sa >../luajit_2.0.5+dfsg-1ppa1_source.changes
dpkg-genchanges: including full source code in upload
 dpkg-source -i -I --after-build luajit-2.0.5+dfsg
dpkg-buildpackage: full upload (original source is included)
Now running lintian...
W: luajit source: ancient-standards-version 3.9.4 (current is 3.9.7)
Finished running lintian.
Now signing changes and any dsc files...
 signfile luajit_2.0.5+dfsg-1ppa1.dsc Hiroaki Nakamura <hnakamur@gmail.com>

You need a passphrase to unlock the secret key for
user: "Hiroaki Nakamura <hnakamur@gmail.com>"
4096-bit RSA key, ID 1DFBC664, created 2015-11-14

Enter passphrase: gpg: gpg-agent is not available in this session ←gpgのパスフレーズを入力

 signfile luajit_2.0.5+dfsg-1ppa1_source.changes Hiroaki Nakamura <hnakamur@gmail.com>

You need a passphrase to unlock the secret key for
user: "Hiroaki Nakamura <hnakamur@gmail.com>"
4096-bit RSA key, ID 1DFBC664, created 2015-11-14

gpg: gpg-agent is not available in this session
Enter passphrase: ←gpgのパスフレーズを入力

Successfully signed dsc and changes files
```

`../build-area/` ディレクトリを見るとdebソースパッケージが作成されています。

```console
hnakamur@express:~/deb-tutorial/luajit/luajit-deb$ ls ../build-area/
luajit_2.0.5+dfsg-1ppa1.debian.tar.xz  luajit_2.0.5+dfsg-1ppa1_source.changes
luajit_2.0.5+dfsg-1ppa1.dsc            luajit_2.0.5+dfsg.orig.tar.gz
luajit_2.0.5+dfsg-1ppa1_source.build
```

## バイナリパッケージのビルド

上記で作成したソースパッケージの内容に絶対の自信があれば `dput` コマンドでLaunchPadにアップロードしてバイナリパッケージをビルドしても良いですが、ローカルでバイナリパッケージが正常にビルドできることを確認してからアップロードするほうが良いです。

以下のコマンドでバイナリパッケージをビルドします。

```console
sudo pbuilder build ../build-area/luajit_2.0.5+dfsg-1ppa1.dsc
```

無事ビルドが完了したら、 `/var/cache/pbuilder/result/` ディレクトリにバイナリパッケージが生成されています。

```console
$ ls /var/cache/pbuilder/result/*luajit*
/var/cache/pbuilder/result/libluajit-5.1-2_2.0.5+dfsg-1ppa1_amd64.deb
/var/cache/pbuilder/result/libluajit-5.1-common_2.0.5+dfsg-1ppa1_all.deb
/var/cache/pbuilder/result/libluajit-5.1-dev_2.0.5+dfsg-1ppa1_amd64.deb
/var/cache/pbuilder/result/luajit_2.0.5+dfsg-1ppa1_amd64.changes
/var/cache/pbuilder/result/luajit_2.0.5+dfsg-1ppa1_amd64.deb
/var/cache/pbuilder/result/luajit_2.0.5+dfsg-1ppa1.debian.tar.xz
/var/cache/pbuilder/result/luajit_2.0.5+dfsg-1ppa1.dsc
/var/cache/pbuilder/result/luajit_2.0.5+dfsg.orig.tar.gz
```

`*.deb` ファイルを新規に作成したLXDコンテナなどの別環境にコピー、インストールして動作確認します。
動作確認して大丈夫であれば、ソースパッケージをPPAにアップロードします。

## ソースパッケージをPPAにアップロード

### PPAの作成とアクティベート

初回はパッケージのアップロード先となるPPAを作成しアクティベートする必要があります。
手順は [Activating a PPA](https://help.launchpad.net/Packaging/PPA) に説明があります。
自分のアカウントのプロファイルページにある Create a new PPA というリンクをクリックし、Activate a Personal Package ArchiveというページでURL、Display Nameと必要に応じてDescriptionを入力してActivateボタンを押しアクティベートします。

今回私は `ppa:hnakamur/luajit` というPPAを作成しました。

### ソースパッケージのアップロード

[Packaging/PPA/Uploading - Launchpad Help](https://help.launchpad.net/Packaging/PPA/Uploading) に説明があります。
ソースパッケージの `.dsc` ファイルを指定して以下のコマンドを実行します。

```console
$ dput ppa:hnakamur/luajit ../build-area/luajit_2.0.5+dfsg-1ppa1_source.changes
Checking signature on .changes
gpg: Signature made Thu 06 Jul 2017 02:11:13 AM JST using RSA key ID 1DFBC664
gpg: Good signature from "Hiroaki Nakamura <hnakamur@gmail.com>"
gpg: WARNING: This key is not certified with a trusted signature!
gpg:          There is no indication that the signature belongs to the owner.
Primary key fingerprint: 3240 E02B 14E1 5B7B 5C53  4B81 153C 7660 1DFB C664
Good signature on ../build-area/luajit_2.0.5+dfsg-1ppa1_source.changes.
Checking signature on .dsc
gpg: Signature made Thu 06 Jul 2017 02:11:05 AM JST using RSA key ID 1DFBC664
gpg: Good signature from "Hiroaki Nakamura <hnakamur@gmail.com>"
gpg: WARNING: This key is not certified with a trusted signature!
gpg:          There is no indication that the signature belongs to the owner.
Primary key fingerprint: 3240 E02B 14E1 5B7B 5C53  4B81 153C 7660 1DFB C664
Good signature on ../build-area/luajit_2.0.5+dfsg-1ppa1.dsc.
Package includes an .orig.tar.gz file although the debian revision suggests
that it might not be required. Multiple uploads of the .orig.tar.gz may be
rejected by the upload queue management software.
Uploading to ppa (via ftp to ppa.launchpad.net):
  Uploading luajit_2.0.5+dfsg-1ppa1.dsc: done.
  Uploading luajit_2.0.5+dfsg.orig.tar.gz: done.
  Uploading luajit_2.0.5+dfsg-1ppa1.debian.tar.xz: done.
  Uploading luajit_2.0.5+dfsg-1ppa1_source.changes: done.
Successfully uploaded packages.
```

上記のように `Successfully uploaded packages.` と表示されたらひとまずはアップロード成功です。

### アップロード受付結果のメール確認

アップロードしたあと数分ぐらいするとアップロード受付結果のメールが届きます。

以下は受付拒否のメールの例です。間違ってソースパッケージとバイナリパッケージをアップロードしてしまったときのものです。
[Packaging/UploadErrors - Launchpad Help](https://help.launchpad.net/Packaging/UploadErrors) にアップロードに関するエラーについての説明があるのでこちらも参照してください。

```console
From: Launchpad PPA <no_reply@launchpad.net>
Subject: [~hnakamur/ubuntu/luajit] luajit_2.0.5+dfsg-1ubuntu1ppa1_amd64.changes (Rejected)

Rejected:
Source/binary (i.e. mixed) uploads are not allowed.

luajit (2.0.5+dfsg-1ubuntu1ppa1) xenial; urgency=medium

  * New upstream release

===
If you don't understand why your files were rejected please send an email
to launchpad-users@lists.launchpad.net for help (requires membership).
```

以下は受付成功のときのメールの例です。

```console
From: Launchpad PPA <no_reply@launchpad.net>
Subject: [~hnakamur/ubuntu/luajit/xenial] luajit 2.0.5+dfsg-1ubuntu1ppa1 (Accepted)

Accepted:
 OK: luajit_2.0.5+dfsg.orig.tar.gz
 OK: luajit_2.0.5+dfsg-1ubuntu1ppa1.debian.tar.xz
 OK: luajit_2.0.5+dfsg-1ubuntu1ppa1.dsc
     -> Component: main Section: interpreters

luajit (2.0.5+dfsg-1ubuntu1ppa1) xenial; urgency=medium

  * New upstream release

--
https://launchpad.net/~hnakamur/+archive/ubuntu/luajit
You are receiving this email because you made this upload.
```

### ビルド経過の確認

[The Launchpad build farm](https://launchpad.net/builders) で各ビルドサーバが今どのパッケージをビルドしているか見られます。ビルドサーバがすいているときはすぐここに表示されます。

また [ppa:hnakamur/luajit](https://launchpad.net/~hnakamur/+archive/ubuntu/luajit) のページの右上にある
View package details リンクをクリックし、Packages in “luajit” ページの右上にある View all builds リンクをクリックするとBuilds for luajitというページが開き、ここの検索フォームでPPA内のパッケージの状態を確認できます。

## 注意：パッケージを消して同じバージョンで上げ直すことは出来ません

ここでハマりネタです。

今回実は一度 `2.0.5+dfsg-1ubuntu1ppa1` というバージョンでパッケージをアップロードしてビルド成功した後、ビルド手順を整理して再度試そうと思い、パッケージの詳細ページからView package detailsリンク、Delete packagesリンクと辿ってバージョン `2.0.5+dfsg-1ubuntu1ppa1` を削除していました。

元のパッケージのバージョンは `2.0.4+dfsg-1` とバージョン名に `ubuntu1` はついていなかったので、再度作り直す際は上記のように `2.0.5+dfsg-1ppa1` というバージョンにしてみました。

しかしソースパッケージをアップロードした後以下の受付拒否メールが届きました。

```console
From: Launchpad PPA <no_reply@launchpad.net>
Subject: [~hnakamur/ubuntu/luajit] luajit_2.0.5+dfsg-1ppa1_source.changes (Rejected)

Rejected:
File luajit_2.0.5+dfsg.orig.tar.gz already exists in luajit, but uploaded version has different contents. See more information about this error in https://help.launchpad.net/Packaging/UploadErrors.
Files specified in DSC are broken or missing, skipping package unpack verification.

luajit (2.0.5+dfsg-1ppa1) xenial; urgency=medium

  * New upstream release

===

If you don't understand why your files were rejected please send an email
to launchpad-users@lists.launchpad.net for help (requires membership).

--
https://launchpad.net/~hnakamur/+archive/ubuntu/luajit
You are receiving this email because you made this upload.
```

upstreamのソースをDFSGクリーンにしたtarball `luajit_2.0.5+dfsg.orig.tar.gz` が一度アップロードしたものと内容が異なっているため拒否されたということです。

調べてみると
[Packaging/PPA/Deleting - Launchpad Help](https://help.launchpad.net/Packaging/PPA/Deleting) の最後にファイルが削除された後に同じバージョンのソースを再度アップロードしても拒否されると書かれていました。
ですので、何か間違えた場合もリリースの番号を上げて再度アップロードすることで対応する必要があります。

### 今回の回避策

今回はupstreamのtarballで引っかかっているのでリリース番号ではなくupstreamのバージョンを上げる必要があります。
とはいっても、本当は2.0.5なのに2.0.5.1とかにするわけにも行かないしなーと悩みました。

[What does “dfsg” in the version string mean?](https://wiki.debian.org/DebianMentorsFaq#What_does_.2BIBw-dfsg.2BIB0_in_the_version_string_mean.3F) を見て、DFSGのために調整されたパッケージのバージョンは `<UPSTREAM_VERSION>+dfsg.<REPACK_COUNT>-<DEBIAN_RELEASE>` という形式が良いというのを知りました。

そこで今回は `2.0.5+dfsg.2-1ppa1` というバージョンに変更（手順は省略）して再度アップロードすることで回避しました。

## ビルドされたパッケージを他の環境にインストールしてみる

LXDで新たなコンテナを作るなどしてテストするサーバを用意し、そこで以下のコマンドを実行してインストールしてみます。

```console
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:hnakamur/luajit
sudo apt update
sudo apt install luajit
```

以下のコマンドでインストールされたパッケージのバージョンを確認します。

```console
root@debtmp:~# dpkg-query -W -f 'pkg:${package}\tver:${version}\tarch:${architecture}\n' '*luajit*'
pkg:libluajit-5.1-common        ver:2.0.5+dfsg.2-1ppa1  arch:all
pkg:luajit      ver:2.0.5+dfsg.2-1ppa1  arch:amd64
```

以下のコマンドで簡易的な動作確認を行います。

```console
root@debtmp:~# luajit
LuaJIT 2.0.5 -- Copyright (C) 2005-2017 Mike Pall. http://luajit.org/
JIT: ON CMOV SSE2 SSE3 SSE4.1 fold cse dce fwd dse narrow loop abc sink fuse
> print('Hello luajit!')
Hello luajit!
> （Ctrl-Dを入力して抜ける）
```

## 新しいリリースのタグ作成

動作確認がOKだったので、新しいリリースのタグを作成しておきます。

```console
git tag debian/2.0.5+dfsg.2-1ppa1 master
```

## おわりに

以上で Ubuntu 16.04 (xenial) で提供されている luajit 2.0.4 を2.0.5にアップデートしてPPAにアップロードすることができました。パッケージによってはパッチの更新の手順がもっと複雑になったりといろいろ変わってくると思いますが、とりあえずこれで基本パターンは出来たということで。
