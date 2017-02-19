Title: Homebrewを辞めてMacPorts 2.3.3を入れてpkgngをビルドしてみた
Date: 2015-06-11 01:09
Category: blog
Tags: osx, macports, pkgng
Slug: 2015/06/11/tried_macports

# はじめに
https://twitter.com/shibu_jp/status/598332736638582785 と [第2回　パッケージ管理システム「pkg 1.5」と基本的な使い方：BSD界隈四方山話｜gihyo.jp … 技術評論社](http://gihyo.jp/admin/serial/01/bsd-yomoyama/0002)で、実験段階ですがOS Xもサポート対象となったという話を見て `pkg` と `MacPorts` をシームレスに組み合わせて使えるかが気になっていました。

FreeBSDではpkgコマンドでバイナリパッケージをインストールし、Ports Collectionでソースからビルドというのが簡単にできるようになっているのですが、上記の記事によるとpkgとPorts Collectionがシームレスに連動しているそうです。

なので、OS X上では `pkg` と `MacPorts` が連動するのかな、するといいなあ、と思って、まずは `MacPorts` を試してみます。

私はだいぶ前に MacPorts から Homebrew に切り替えていたので、MacPortsは久々に試します。

## 確認した環境

* MacBook Pro (Retina, Mid 2012)
* OS X Yosemite 10.10.3


# Homebrewのアンインストール

[Homebrewをアンインストールするには - Qiita](http://qiita.com/UmedaTakefumi/items/dc52f008586cbf06582f)を参考にといいつつ、いきなりバッサリ消すとなにかあったときに戻れないので、アンインストールはせずにHomebrewでインストールしたパッケージのサービスを停止して、/usr/localディレクトリを/usr/local.bakに退避しておくことにします。移行が無事完了したらアンインストールするということで。

以下のコマンドを実行して~/Library/LaunchAgents/にシンボリックリンクを張ったサービスを停止・解除します。

```
for f in ~/Library/LaunchAgents/homebrew.*; do launchctl unload $f; done
```

/usr/localを/usr/local.bakに退避します。

```
sudo mv /usr/local /usr/local.bak
```

# MacPortsのインストール

MacPortsのバイナリパッケージをダウンロードしてインストールします。MacPorts-2.3.3-10.10-Yosemite.pkgをFinderでダブルクリックしてもいいのですが、将来スクリプトで自動化することを見据えて、OS Xの `installer` コマンドでインストールしてみます。

```
cd ~/Downloads
curl -O https://distfiles.macports.org/MacPorts/MacPorts-2.3.3-10.10-Yosemite.pkg
sudo installer -pkg MacPorts-2.3.3-10.10-Yosemite.pkg -target /
```

[2.5.1. The Postflight Script](https://guide.macports.org/#installing.shell)の説明に従って、環境変数PATHとMANPATHの設定を追加します。以下はシェルはbashを使っていて~/.bash_profileに追加する場合の例です。

```
cat <<'EOF' >> ~/.bash_profile
export PATH=/opt/local/bin:/opt/local/sbin:$PATH
export MANPATH=/opt/local/share/man:$MANPATH
EOF
```

以下のコマンドを実行して、上で追加した設定を有効にします。

```
exec $SHELL -l
```

portコマンドにPATHが通ったことを確認します。

```
$ which port
/opt/local/bin/port
```

[Mac OS X Package (.pkg) Installer](https://www.macports.org/install.php#pkg)の説明に従って、MacPorts自体のアップデートを行います。

```
sudo port -v selfupdate
```

出力の最後に以下のように表示されたので、既に最新版になっていたそうです。

```
--->  MacPorts base is already the latest version

The ports tree has been updated. To upgrade your installed ports, you should run
  port upgrade outdated
```

上記の説明によるとインストールしたportsをアップグレードするときは `ports upgrade outdated` と実行すればよいそうです。

# pkgngをソースからビルド

FreeBSDのpkgはpkgngと呼ばれることもあります。[pkgng - FreeBSD Wiki](https://wiki.freebsd.org/pkgng)によるとngはNext Generationの略のようです。

githubにソースレポジトリ [freebsd/pkg](https://github.com/freebsd/pkg)があったので、ソースからビルドして入れてみます。

ホームディレクトリ直下にpkgディレクトリを作るようにして入れてみました。

```
cd
git clone https://github.com/freebsd/pkg
cd pkg
```

`git tag` で確認すると最新のリリースは 1.5.3 でしたので、それにしてみます。

```
git checkout 1.5.3
git checkout -b 1.5.3
```

[freebsd/pkg](https://github.com/freebsd/pkg#building-pkg-using-sources-from-git)を参考にやってみました。この手順ではビルドに必要なパッケージをFreeBSDにインストール済みの古いバージョンの `pkg` コマンドで入れていますが、OS Xの場合は無いのでMacPortsで入れます。

また `pkgconf` はMacPortsでは `pkgconfig` という名前なのでそこも変えています。

```
sudo port install autoconf automake libtool pkgconfig
```

```
./autogen.sh
./configure
```

`./configure` が以下のようにエラーになってしまいました。

```
…(略)…
checking for library containing archive_read_open... -larchive
checking archive.h usability... no
checking archive.h presence... no
checking for archive.h... no
configure: error: Unable to find the libarchive headers
```

そこでlibarchiveをMacPortsでインストールしました。

```
sudo port install libarchive
```

MacPortsでインストールしたパッケージを見つけてもらうため、[Compile against libraries installed with MacPorts | Blog de François Maillet](http://blog.francoismaillet.com/compile-against-libraries-installed-with-macports/)を参考に以下のようにオプションをつけて `./configure` を再度実行しました。pkgのsrcディレクトリを見ると、pkgはC++ではなくCで実装されていますので、 `configure` の引数もCPPFLAGSではなくCFLAGSにしています。
今度は `configure` が成功しました。

```
./configure CFLAGS="-I/opt/local/include" LDFLAGS="-L/opt/local/lib"
```

`configure` の次は `make` を実行します。

```
make
```

1つ警告が出ました。

```
…(略)…
  CCLD     pkg-static
libtool: warning: complete static linking is impossible in this configuration
  CCLD     pkg
…(略)…
```

`./configure --help` してみると

```
  --with-staticonly       Only build the static version (default is no)
```

というオプションがあり、デフォルトではスタティックリンクするバージョンとしないバージョンの両方を作るようになっているようです。

とりあえずスタティックリンクしないバージョンはビルドできているのでとりあえず先に進みます。

以下のコマンドを実行してインストールします。

```
sudo make install
```

/usr/localに以下のようなファイルとディレクトリが作られました。

```
$ find /usr/local
/usr/local
/usr/local/etc
/usr/local/etc/bash_completion.d
/usr/local/etc/bash_completion.d/_pkg.bash
/usr/local/etc/periodic
/usr/local/etc/periodic/daily
/usr/local/etc/periodic/daily/411.pkg-backup
/usr/local/etc/periodic/daily/490.status-pkg-changes
/usr/local/etc/periodic/security
/usr/local/etc/periodic/security/410.pkg-audit
/usr/local/etc/periodic/security/460.pkg-checksum
/usr/local/etc/periodic/weekly
/usr/local/etc/periodic/weekly/400.status-pkg
/usr/local/etc/pkg.conf.sample
/usr/local/include
/usr/local/include/pkg.h
/usr/local/lib
/usr/local/lib/libpkg.3.dylib
/usr/local/lib/libpkg.dylib
/usr/local/lib/libpkg.la
/usr/local/lib/libpkg_static.a
/usr/local/lib/libpkg_static.la
/usr/local/libdata
/usr/local/libdata/pkgconfig
/usr/local/libdata/pkgconfig/pkg.pc
/usr/local/man
/usr/local/man/man3
/usr/local/man/man3/pkg_printf.3
/usr/local/man/man3/pkg_repos.3
/usr/local/man/man5
/usr/local/man/man5/pkg-repository.5
/usr/local/man/man5/pkg.conf.5
/usr/local/man/man8
/usr/local/man/man8/pkg-add.8
/usr/local/man/man8/pkg-alias.8
/usr/local/man/man8/pkg-annotate.8
/usr/local/man/man8/pkg-audit.8
/usr/local/man/man8/pkg-autoremove.8
/usr/local/man/man8/pkg-backup.8
/usr/local/man/man8/pkg-check.8
/usr/local/man/man8/pkg-clean.8
/usr/local/man/man8/pkg-config.8
/usr/local/man/man8/pkg-convert.8
/usr/local/man/man8/pkg-create.8
/usr/local/man/man8/pkg-delete.8
/usr/local/man/man8/pkg-fetch.8
/usr/local/man/man8/pkg-info.8
/usr/local/man/man8/pkg-install.8
/usr/local/man/man8/pkg-lock.8
/usr/local/man/man8/pkg-query.8
/usr/local/man/man8/pkg-register.8
/usr/local/man/man8/pkg-remove.8
/usr/local/man/man8/pkg-repo.8
/usr/local/man/man8/pkg-rquery.8
/usr/local/man/man8/pkg-search.8
/usr/local/man/man8/pkg-set.8
/usr/local/man/man8/pkg-shell.8
/usr/local/man/man8/pkg-shlib.8
/usr/local/man/man8/pkg-ssh.8
/usr/local/man/man8/pkg-static.8
/usr/local/man/man8/pkg-stats.8
/usr/local/man/man8/pkg-unlock.8
/usr/local/man/man8/pkg-update.8
/usr/local/man/man8/pkg-updating.8
/usr/local/man/man8/pkg-upgrade.8
/usr/local/man/man8/pkg-version.8
/usr/local/man/man8/pkg-which.8
/usr/local/man/man8/pkg.8
/usr/local/sbin
/usr/local/sbin/pkg
/usr/local/sbin/pkg-static
/usr/local/sbin/pkg2ng
/usr/local/share
/usr/local/share/zsh
/usr/local/share/zsh/site-functions
/usr/local/share/zsh/site-functions/_pkg
```

pkgコマンドとpkg-staticコマンドは/usr/local/sbinにインストールされていました。
`otool -L` で確認すると両方ともダイナミックリンクになっていました。

```
$ otool -L /usr/local/sbin/pkg
/usr/local/sbin/pkg:
        /usr/local/lib/libpkg.3.dylib (compatibility version 4.0.0, current version 4.0.0)
        /opt/local/lib/libssl.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
        /usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1213.0.0)
        /usr/lib/libutil.dylib (compatibility version 1.0.0, current version 1.0.0)
        /opt/local/lib/libcrypto.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
        /usr/lib/libresolv.9.dylib (compatibility version 1.0.0, current version 1.0.0)
        /opt/local/lib/libarchive.13.dylib (compatibility version 15.0.0, current version 15.2.0)
        /opt/local/lib/libz.1.dylib (compatibility version 1.0.0, current version 1.2.8)
        /opt/local/lib/libbz2.1.0.dylib (compatibility version 1.0.0, current version 1.0.6)
        /opt/local/lib/liblzma.5.dylib (compatibility version 8.0.0, current version 8.1.0)
$ otool -L /usr/local/sbin/pkg-static
/usr/local/sbin/pkg-static:
        /usr/lib/libutil.dylib (compatibility version 1.0.0, current version 1.0.0)
        /opt/local/lib/libssl.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
        /opt/local/lib/libcrypto.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
        /usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1213.0.0)
        /usr/lib/libresolv.9.dylib (compatibility version 1.0.0, current version 1.0.0)
        /opt/local/lib/libarchive.13.dylib (compatibility version 15.0.0, current version 15.2.0)
        /opt/local/lib/libz.1.dylib (compatibility version 1.0.0, current version 1.2.8)
        /opt/local/lib/libbz2.1.0.dylib (compatibility version 1.0.0, current version 1.0.6)
        /opt/local/lib/liblzma.5.dylib (compatibility version 8.0.0, current version 8.1.0)
```

/usr/local/sbinにはPATHが通っていなかったので、設定を変更して有効にしました。

```
echo 'export PATH=/usr/local/sbin:$PATH' >> ~/.bash_profile
exec $SHELL -l
```

```
$ which pkg
/usr/local/sbin/pkg
$ pkg --version
1.5.3-cfa5423
```

というわけでビルドは出来ました。が OS X用のバイナリパッケージレポジトリの情報は見つけられず。

pkgコマンドの使い方については[freebsd/pkg](https://github.com/freebsd/pkg#a-quick-usage-introduction-to-pkg)のREADMEに[A quick usage introduction to pkg](https://github.com/freebsd/pkg#a-quick-usage-introduction-to-pkg)というセクションがありました。

# 情報収集中
[Baseline Mac OS X Support merged into FreeBSD package manager | Hacker News](https://news.ycombinator.com/item?id=8828866)にいくつか有用な情報がありました。

* [This change was written by Landon Fuller, one of the founders of MacPorts. There... | Hacker News](https://news.ycombinator.com/item?id=8829040)
    * pkgngをOS X対応にするプルリクエスト [Baseline Mac OS X Support by landonf · Pull Request #1113 · freebsd/pkg](https://github.com/freebsd/pkg/pull/1113)はMacPorts創始者の1人によるもので、[Baseline Mac OS X Support by landonf · Pull Request #1113 · freebsd/pkg](https://github.com/freebsd/pkg/pull/1113#issuecomment-68063964)のコメントによるとMacPortsのtclで書いている部分をlibpkgを使って書き直すことが出来るかを模索するつもりらしいです。
* [You can already have that with pkgsrc for osx - joyent maintains the osx binary ... | Hacker News](https://news.ycombinator.com/item?id=8829179)
    * このスレッドによるとpkgngがOS X対応する前から[pkgsrc](http://pkgsrc.joyent.com/)というパッケージ管理システムがあるそうです。Node.jsのJoyent, Inc.が作ってるんですね。
    * [saveosx](http://www.saveosx.org/)にYosemite 64bit用のバイナリパッケージがあるようです。

ということで、今後どうなっていくか要注目です。

# 2015-06-13追記 pkgsrcについて訂正

[pkgsrc](https://www.pkgsrc.org/)自体はFreeBSDのportsからフォークしてNetBSDで開発されているもので、Joyent, Inc.が提供しているのはSmartOS/illumos, Mac OS X, and Linux用のバイナリバッケージでした。

* [pkgsrc](http://pkgsrc.joyent.com/)
* [pkgsrc - Wikipedia, the free encyclopedia](https://en.wikipedia.org/wiki/Pkgsrc)

また [saveosx](http://www.saveosx.org/)は[cmacrae/saveosx](https://github.com/cmacrae/saveosx)を見るとOS X用のpkgsrcをインストールするためのスクリプトでした。パッケージ自体はJoyentが提供しているそうです。
