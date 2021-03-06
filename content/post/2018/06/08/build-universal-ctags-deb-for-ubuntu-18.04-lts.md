+++
title="universal-ctagsのUbuntu 18.04 LTS用debパッケージをビルドした"
date = "2018-06-08T00:30:00+09:00"
lastmod = "2018-06-09T12:25:00+09:00"
tags = ["ubuntu", "deb", "universal-ctags"]
categories = ["blog"]
+++


# はじめに

ctagsというと Ubuntu 18.04 LTS には
[exuberant-ctags (1:5.9~svn20110310-11)](https://packages.ubuntu.com/bionic/exuberant-ctags)
というパッケージがあります。ですが、バージョン番号のsvnの後の日付が2011年とあるようにかなり古いです。

検索してみると
[universal-ctags/ctags: A maintained ctags implementation](https://github.com/universal-ctags/ctags)
活発に開発されているので、こちらを使うことにしました。

[Add debian packaging information to the repository · Issue #655 · universal-ctags/ctags](https://github.com/universal-ctags/ctags/issues/655) というイシューの [コメント](https://github.com/universal-ctags/ctags/issues/655#issuecomment-377423868) で
[Debian -- buster の universal-ctags パッケージ](https://packages.debian.org/buster/universal-ctags)
があることを知りました。

その下の [コメント](https://github.com/universal-ctags/ctags/issues/655#issuecomment-377699060) にmanページを追加してlibxml2をリンクしたほうが良いとアドバイスがありました。

そこで、これらに対応したdebパッケージをビルドしてみました。

* [universal-ctagsのPPAのページ](https://launchpad.net/~hnakamur/+archive/ubuntu/universal-ctags)
* [universal-ctagsのdebのソース](https://github.com/hnakamur/universal-ctags-deb)

# 使い方(インストール手順)

後から参照する時用に、ビルドしたパッケージを利用する手順を先に書いておきます。

```console
sudo apt install software-properties-common
sudo add-apt-repository ppa:hnakamur/universal-ctags
sudo apt update
sudo apt install universal-ctags
```

# debパッケージをビルドしたときのメモ

## リンクするライブラリの追加

libxml2, libjansson, libseccomp, libyaml, libaspellのdevパッケージを `debian/control` の `Build-Depends` に追加しました。
テストの実行時に必要になるので aspell-en パッケージも追加しました。

また libaspell-dev パッケージには pkg-config のファイルが何故か含まれていないので `ASPELL_CFLAGS` と `ASPELL_LIBS` 環境変数を configure に引き渡すように変更しました。

```diff
diff --git a/debian/control b/debian/control
index 86c233c..17cc873 100644
--- a/debian/control
+++ b/debian/control
@@ -2,7 +2,9 @@ Source: universal-ctags
 Section: editors
 Priority: optional
 Maintainer: Alessandro Ghedini <ghedo@debian.org>
-Build-Depends: debhelper (>= 11), autoconf, automake, pkg-config
+Build-Depends: debhelper (>= 11), autoconf, automake, pkg-config,
+  libxml2-dev, libjansson-dev, libseccomp-dev, libyaml-dev,
+  libaspell-dev, aspell-en
 Standards-Version: 4.1.3
 Vcs-Git: https://salsa.debian.org/debian/universal-ctags.git
 Vcs-Browser: https://salsa.debian.org/debian/universal-ctags
diff --git a/debian/rules b/debian/rules
index aa15ce4..d6e3363 100755
--- a/debian/rules
+++ b/debian/rules
@@ -14,5 +14,12 @@ override_dh_autoreconf:
        dh_autoreconf
 
 override_dh_auto_configure:
+	# We need to pass ASPELL_CFLAGS and ASPELL_LIBS here
+	# because the libaspell-dev package does not include pkg-config file.
+	ASPELL_CFLAGS=-I/usr/include ASPELL_LIBS=-laspell \
        dh_auto_configure -- \
                --program-transform-name='s/ctags/ctags-universal/'
+
+override_dh_install:
+	mv man/ctags.1 man/ctags-universal.1
+	dh_auto_install
```

また、 `/usr/share/man/man1/ctags.1.gz` というファイルは exuberant-ctags パッケージと衝突するので 
`/usr/share/man/man1/ctags-universal.1.gz` となるように変更しています。

## manページ用にupdate-alternativesの調整

ビルド時に実行される `make rst2man` で必要な `python3-docutils` パッケージを Build-Requires に追加しました。

```diff
diff --git a/debian/control b/debian/control
index 17cc873..590afd6 100644
--- a/debian/control
+++ b/debian/control
@@ -4,7 +4,7 @@ Priority: optional
 Maintainer: Alessandro Ghedini <ghedo@debian.org>
 Build-Depends: debhelper (>= 11), autoconf, automake, pkg-config,
   libxml2-dev, libjansson-dev, libseccomp-dev, libyaml-dev,
-  libaspell-dev, aspell-en
+  libaspell-dev, aspell-en, python3-docutils
 Standards-Version: 4.1.3
 Vcs-Git: https://salsa.debian.org/debian/universal-ctags.git
 Vcs-Browser: https://salsa.debian.org/debian/universal-ctags
diff --git a/debian/postinst b/debian/postinst
index b179db6..c53102e 100644
--- a/debian/postinst
+++ b/debian/postinst
@@ -4,8 +4,9 @@ set -e
 
 case "$1" in
     configure)
-        update-alternatives --install \
-            /usr/bin/ctags ctags /usr/bin/ctags-universal 30
+        update-alternatives \
+	    --install /usr/bin/ctags ctags /usr/bin/ctags-universal 30 \
+	    --slave /usr/share/man/man1/ctags.1.gz ctags.1.gz /usr/share/man/man1/ctags-universal.1.gz
     ;;
 
     abort-upgrade|abort-remove|abort-deconfigure)
diff --git a/debian/universal-ctags.manpages b/debian/universal-ctags.manpages
new file mode 100644
index 0000000..ac25efb
--- /dev/null
+++ b/debian/universal-ctags.manpages
@@ -0,0 +1,3 @@
+man/ctags-incompatibilities.7
+man/ctags-optlib.7
+man/ctags-universal.1
```

exuberant-ctags パッケージだけをインストールした状態で update-alternatives の設定を確認すると以下のようになっていたので、 `debian/postinst` 内で実行している universal-ctags 用の update-alternatives の設定を上記のdiff内にのように変更しました。

```console
$ update-alternatives --display ctags
ctags - auto mode
  link best version is /usr/bin/ctags-exuberant
  link currently points to /usr/bin/ctags-exuberant
  link ctags is /usr/bin/ctags
  slave ctags.1.gz is /usr/share/man/man1/ctags.1.gz
/usr/bin/ctags-exuberant - priority 30
  slave ctags.1.gz: /usr/share/man/man1/ctags-exuberant.1.gz
```

universal-ctags のパッケージをビルド後、exuberant-ctags とともにインストールされている環境で、update-alternativesで切り替えるのは以下のようにします。

```console
root@nginx-dev:~# update-alternatives --config ctags
There are 2 choices for the alternative ctags (providing /usr/bin/ctags).

  Selection    Path                      Priority   Status
------------------------------------------------------------
* 0            /usr/bin/ctags-universal   30        auto mode
  1            /usr/bin/ctags-exuberant   30        manual mode
  2            /usr/bin/ctags-universal   30        manual mode

Press <enter> to keep the current choice[*], or type selection number: 2
```

切り替え後に update-alternatives の設定を確認すると以下のようになっていました。

```console
root@nginx-dev:~# update-alternatives --display ctags
ctags - manual mode
  link best version is /usr/bin/ctags-universal
  link currently points to /usr/bin/ctags-universal
  link ctags is /usr/bin/ctags
  slave ctags.1.gz is /usr/share/man/man1/ctags.1.gz
/usr/bin/ctags-exuberant - priority 30
  slave ctags.1.gz: /usr/share/man/man1/ctags-exuberant.1.gz
/usr/bin/ctags-universal - priority 30
  slave ctags.1.gz: /usr/share/man/man1/ctags-universal.1.gz
```

実際にファイルを確認して見ると以下のようなシンボリックリンクになっていました。

```console
root@nginx-dev:~# ls -l /usr/bin/ctags
lrwxrwxrwx 1 root root 23 May 10 05:47 /usr/bin/ctags -> /etc/alternatives/ctags
root@nginx-dev:~# ls -l /etc/alternatives/ctags
lrwxrwxrwx 1 root root 24 Jun  7 07:15 /etc/alternatives/ctags -> /usr/bin/ctags-universal
root@nginx-dev:~# ls -l /usr/share/man/man1/ctags.1.gz
lrwxrwxrwx 1 root root 28 Jun  7 04:00 /usr/share/man/man1/ctags.1.gz -> /etc/alternatives/ctags.1.gz
root@nginx-dev:~# ls -l /etc/alternatives/ctags.1.gz
lrwxrwxrwx 1 root root 40 Jun  7 07:15 /etc/alternatives/ctags.1.gz -> /usr/share/man/man1/ctags-universal.1.gz
```

## ローカルのpbuilderでは問題ないがPPAではエラーになるテストをスキップ

[PPAでのビルド失敗時のログその1](https://launchpadlibrarian.net/373545107/buildlog_ubuntu-bionic-amd64.universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa2~ubuntu18.04.1_BUILDING.txt.gz) ではテストの1つで以下のようなエラーが出ていました。

```text
Testing parser-own-fields
------------------------------------------------------------
stdout                                                      failed (diff: /<<BUILDDIR>>/universal-ctags-0+SNAPSHOT20180606/Tmain/parser-own-fields.d/stdout-diff.txt)
```

`misc/units` や `Makefile` を読んだところ、テスト実行時に
`SHOW_DIFF_OUTPUT=--show-diff-output` のように環境変数を設定しておけばdiffが表示されることがわかったので、 `debian/rules` を以下のように変更しました。

```diff
diff --git a/debian/rules b/debian/rules
index d6e3363..62f9835 100755
--- a/debian/rules
+++ b/debian/rules
@@ -20,6 +20,10 @@ override_dh_auto_configure:
	dh_auto_configure -- \
		--program-transform-name='s/ctags/ctags-universal/'
 
+override_dh_auto_test:
+	SHOW_DIFF_OUTPUT=--show-diff-output \
+	dh_auto_test
+
 override_dh_install:
	mv man/ctags.1 man/ctags-universal.1
	dh_auto_install
```

[PPAでのビルド失敗時のログその2](https://launchpadlibrarian.net/373545107/buildlog_ubuntu-bionic-amd64.universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa2~ubuntu18.04.1_BUILDING.txt.gz) では以下のようにdiffが表示されていました。

```text
Detail [compare]
------------------------------------------------------------
/<<BUILDDIR>>/universal-ctags-0+SNAPSHOT20180606/Tmain/parser-own-fields.d/stdout-diff.txt

	--- /<<BUILDDIR>>/universal-ctags-0+SNAPSHOT20180606/Tmain/parser-own-fields.d/stdout-actual.txt	2018-06-07 13:20:17.380303536 +0000
	+++ ./Tmain/parser-own-fields.d/stdout-expected.txt	2018-06-07 05:45:08.000000000 +0000
	@@ -1,0 +2,3 @@
	+bar	input.unknown	/^protected func bar(n);$/;"	f
	+baz	input.unknown	/^private func baz(n,...);$/;"	f
	+foo	input.unknown	/^public func foo(n, m);$/;"	f
	@@ -2,0 +6,3 @@
	+bar	input.unknown	/^protected func bar(n);$/;"	f	signature:(n)
	+baz	input.unknown	/^private func baz(n,...);$/;"	f	signature:(n,...)
	+foo	input.unknown	/^public func foo(n, m);$/;"	f	signature:(n, m)
	@@ -3,0 +10,3 @@
	+bar	input.unknown	/^protected func bar(n);$/;"	f	protection:protected 
	+baz	input.unknown	/^private func baz(n,...);$/;"	f	protection:private 
	+foo	input.unknown	/^public func foo(n, m);$/;"	f	protection:public 
	@@ -4,0 +14,3 @@
	+bar	input.unknown	/^protected func bar(n);$/;"	f	protection:protected 	signature:(n)
	+baz	input.unknown	/^private func baz(n,...);$/;"	f	protection:private 	signature:(n,...)
	+foo	input.unknown	/^public func foo(n, m);$/;"	f	protection:public 	signature:(n, m)

Makefile:7158: recipe for target 'tmain' failed
make[2]: *** [tmain] Error 1
```

ローカル環境でpbuilderやsbuildでビルドしても発生せず、PPAでビルドしたときのみ発生する現象で、調査が難しそうなので、対処療法として以下のパッチを当てて、問題のテストをスキップするようにしました。

```diff
diff --git a/debian/patches/0001-Skip-Tmain-parser-own-fields-stdout-comparison-test.patch b/debian/patches/0001-Skip-Tmain-parser-own-fields-stdout-comparison-test.patch
new file mode 100644
index 0000000..ebaaa9c
--- /dev/null
+++ b/debian/patches/0001-Skip-Tmain-parser-own-fields-stdout-comparison-test.patch
@@ -0,0 +1,32 @@
+From: Hiroaki Nakamura <hnakamur@gmail.com>
+Date: Thu, 7 Jun 2018 22:46:46 +0900
+Subject: Skip Tmain parser-own-fields stdout comparison test
+
+This is a workaround for avoiding the diff which happens only on the Ubuntu PPA build.
+---
+ Tmain/parser-own-fields.d/stdout-expected.txt | 16 ----------------
+ 1 file changed, 16 deletions(-)
+ delete mode 100644 Tmain/parser-own-fields.d/stdout-expected.txt
+
+diff --git a/Tmain/parser-own-fields.d/stdout-expected.txt b/Tmain/parser-own-fields.d/stdout-expected.txt
+deleted file mode 100644
+index 77ffecc..0000000
+--- a/Tmain/parser-own-fields.d/stdout-expected.txt
++++ /dev/null
+@@ -1,16 +0,0 @@
+-# disabling fields
+-bar	input.unknown	/^protected func bar(n);$/;"	f
+-baz	input.unknown	/^private func baz(n,...);$/;"	f
+-foo	input.unknown	/^public func foo(n, m);$/;"	f
+-# enabling signature only
+-bar	input.unknown	/^protected func bar(n);$/;"	f	signature:(n)
+-baz	input.unknown	/^private func baz(n,...);$/;"	f	signature:(n,...)
+-foo	input.unknown	/^public func foo(n, m);$/;"	f	signature:(n, m)
+-# enabling protection only
+-bar	input.unknown	/^protected func bar(n);$/;"	f	protection:protected 
+-baz	input.unknown	/^private func baz(n,...);$/;"	f	protection:private 
+-foo	input.unknown	/^public func foo(n, m);$/;"	f	protection:public 
+-# enabling both signature and protection
+-bar	input.unknown	/^protected func bar(n);$/;"	f	protection:protected 	signature:(n)
+-baz	input.unknown	/^private func baz(n,...);$/;"	f	protection:private 	signature:(n,...)
+-foo	input.unknown	/^public func foo(n, m);$/;"	f	protection:public 	signature:(n, m)
diff --git a/debian/patches/series b/debian/patches/series
new file mode 100644
index 0000000..31a44df
--- /dev/null
+++ b/debian/patches/series
@@ -0,0 +1 @@
+0001-Skip-Tmain-parser-own-fields-stdout-comparison-test.patch
```

これでPPAでも無事ビルドできました。

2018-06-09 追記。その後universal-ctagsの開発者の方から連絡をいただき、PPAのビルド時に `V=1` という環境変数を設定している影響でテストが誤作動していることが判明しました。回避策を教えていただいたのでdebのビルド時にパッチを当てて回避できることを確認しました。その後
[Tmain: initialize "V" variable explicitly by masatake · Pull Request #1762 · universal-ctags/ctags](https://github.com/universal-ctags/ctags/pull/1762)
でupstream側に取り込んでくださったので、次回upstreamのソースを更新するタイミングでdeb側のパッチを削除予定です。
