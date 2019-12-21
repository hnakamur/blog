+++
title="PPAでのビルドの予行演習にsbuildを使う"
date = "2018-06-13T18:00:00+09:00"
tags = ["ubuntu", "deb", "sbuild"]
categories = ["blog"]
+++


# はじめに

PPAでビルドする前に手元でビルドが通ることを確認したくてpbuilderを使っていましたが、pbuilderではビルドが通るのにPPAでは通らないケースが何度か起きたのでsbuildを使い始めました。使い方がある程度わかってきたのでメモです。

sbuildのセットアップ手順は
[Ubuntu 18.04 LTSでsbuildをセットアップ](https://hnakamur.github.io/blog/2018/06/07/setup-sbuild-on-ubuntu-18.04-lts/)
に書きました。

# PPAでビルド時に設定されている環境変数の例

例えば以前 universal-ctags をPPAでビルドしたときの [ログ](https://launchpadlibrarian.net/373686872/buildlog_ubuntu-bionic-amd64.universal-ctags_0+SNAPSHOT20180608-1ubuntu1ppa2~ubuntu18.04.1_BUILDING.txt.gz) を見ると以下のように環境変数が設定されていました。

```text
User Environment
----------------

APT_CONFIG=/var/lib/sbuild/apt.conf
DEB_BUILD_OPTIONS=parallel=4
HOME=/sbuild-nonexistent
LANG=C.UTF-8
LC_ALL=C.UTF-8
LOGNAME=buildd
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games
SCHROOT_ALIAS_NAME=build-PACKAGEBUILD-14993824
SCHROOT_CHROOT_NAME=build-PACKAGEBUILD-14993824
SCHROOT_COMMAND=env
SCHROOT_GID=2501
SCHROOT_GROUP=buildd
SCHROOT_SESSION_ID=build-PACKAGEBUILD-14993824
SCHROOT_UID=2001
SCHROOT_USER=buildd
SHELL=/bin/sh
TERM=unknown
USER=buildd
V=1
```

ちなみに、ビルドログへは以下の手順でたどり着きました。

1. [universal-ctags : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/universal-ctags) で "View package details" をクリック。
2. Packagesの表の "universal-ctags - 0+SNAPSHOT20180608-1ubuntu1ppa2~ubuntu18.04.1" をクリック。
3. 展開された中の Builds の amd64 をクリック。
4. 切り替わったページ内の Build Status の buildlog をクリック。

# PPAでの環境変数に似せて手元のsbuildでビルドする手順

`TERM` や `V` などの環境変数を外から設定できるようにするため `~/.sbuildrc` に以下の設定を追加します。 `environment_filter` の説明とデフォルト値については
[man sbuild.conf](http://manpages.ubuntu.com/manpages/bionic/en/man5/sbuild.conf.5.html)
を参照してください。

```perl
$environment_filter = [
                        '^AR$',
                        '^ARFLAGS$',
                        '^AS$',
                        '^AWK$',
                        '^CC$',
                        '^CFLAGS$',
                        '^CPP$',
                        '^CPPFLAGS$',
                        '^CXX$',
                        '^CXXFLAGS$',
                        '^DEB_BUILD_OPTIONS$',
                        '^DEB_BUILD_PROFILES$',
                        '^DEB_VENDOR$',
                        '^DPKG_ADMINDIR$',
                        '^DPKG_DATADIR$',
                        '^DPKG_GENSYMBOLS_CHECK_LEVEL$',
                        '^DPKG_ORIGINS_DIR$',
                        '^DPKG_ROOT$',
                        '^FC$',
                        '^FFLAGS$',
                        '^GCJFLAGS$',
                        '^LANG$',
                        '^LC_ADDRESS$',
                        '^LC_ALL$',
                        '^LC_COLLATE$',
                        '^LC_CTYPE$',
                        '^LC_IDENTIFICATION$',
                        '^LC_MEASUREMENT$',
                        '^LC_MESSAGES$',
                        '^LC_MONETARY$',
                        '^LC_NAME$',
                        '^LC_NUMERIC$',
                        '^LC_PAPER$',
                        '^LC_TELEPHONE$',
                        '^LC_TIME$',
                        '^LD$',
                        '^LDFLAGS$',
                        '^LD_LIBRARY_PATH$',
                        '^LEX$',
                        '^M2C$',
                        '^MAKE$',
                        '^MAKEFLAGS$',
                        '^OBJC$',
                        '^OBJCFLAGS$',
                        '^OBJCXX$',
                        '^OBJCXXFLAGS$',
                        '^PC$',
                        '^RANLIB$',
                        '^SOURCE_DATE_EPOCH$',
                        '^TERM$',
                        '^V$',
                        '^YACC$'
                      ];
```

`~/.sbuildrc` はPerlのスクリプトになっていて、ファイル末尾に以下のような行があるので、それよりは上に上記の設定を書きます。

```perl
# don't remove this, Perl needs it:
1;
```

この設定を入れた上で、以下のコマンドでビルドするようにしました。

```console
TERM=unknown DEB_BUILD_OPTIONS=parallel=2 V=1 sbuild --sbuild-mode=buildd
```

`DEB_BUILD_OPTIONS` の値は上記のPPAのログでは `parallel=4` でしたが、自宅サーバはコア数が2なので2にしています。

`--sbuild-mode` オプションは
[man sbuild](http://manpages.ubuntu.com/manpages/bionic/en/man1/sbuild.1.html) と
[man sbuild.conf](http://manpages.ubuntu.com/manpages/bionic/en/man5/sbuild.conf.5.html)
を見ると `user` と `buildd` という選択肢があってデフォルトは `user` でした。

PPAのビルドログをみると launchpad-buildd というツールを使っているようなので `buildd` にしました。


# ビルド失敗したchroot環境に入る

[Ubuntu 18.04 LTSでsbuildをセットアップ](https://hnakamur.github.io/blog/2018/06/07/setup-sbuild-on-ubuntu-18.04-lts/)
で `~/.sbuildrc` に以下の設定を入れているので、ビルド失敗時にはchroot環境のセッションが削除されずに残ります。

```perl
$purge_build_directory = 'successful';
$purge_session = 'successful';
$purge_build_deps = 'successful';
```

ビルドログに以下のようにビルドセッションのIDが出力されます。

```text
+------------------------------------------------------------------------------+
| Cleanup                                                                      |
+------------------------------------------------------------------------------+

Not cleaning session: cloned chroot in use
Keeping session: bionic-amd64-sbuild-ec0f01f1-fc92-4ac0-940f-15acf7a9346c
E: Build failure (dpkg-buildpackage died)
```

ちなみにビルド成功時は以下のように出力されビルドセッションは削除されます。

```text
+------------------------------------------------------------------------------+
| Cleanup                                                                      |
+------------------------------------------------------------------------------+

Purging /<<BUILDDIR>>
Not cleaning session: cloned chroot in use
```

`schroot -l --all-sessions` と実行するとセッションの一覧を確認できます。

```console
$ schroot -l --all-sessions
session:bionic-amd64-sbuild-06716ae7-5bfd-4845-80bc-fa6df4f9a2f9
session:bionic-amd64-sbuild-119e026d-45df-45c6-b1a3-f2f750c0be86
session:bionic-amd64-sbuild-1fa47574-b8e4-4bf3-b4b4-d2d247882bad
session:bionic-amd64-sbuild-2298d959-a0c0-4b34-84b6-da0cf55b4e69
session:bionic-amd64-sbuild-2d8e08f5-0f6d-4586-b73e-6fbe32d25a00
session:bionic-amd64-sbuild-578bd0b0-e053-4ba1-80bd-eedc63b786f0
session:bionic-amd64-sbuild-6778cf73-a495-4568-b75e-575955204012
session:bionic-amd64-sbuild-903e3529-eb26-4d6c-a1de-b6271f899ee2
session:bionic-amd64-sbuild-db7a2953-5321-420b-b14d-bda5c9c8845b
session:bionic-amd64-sbuild-ec0f01f1-fc92-4ac0-940f-15acf7a9346c
```

ちなみにchroot環境の一覧は `schroot -l` で確認できます。

```console
$ schroot -l
chroot:bionic-amd64
chroot:bionic-amd64-sbuild
source:bionic-amd64
source:bionic-amd64-sbuild
```

特定のセッションにユーザと実行ディレクトリを指定して入るのは以下のようにします（セッションIDとユーザIDとディレクトリは適宜変更してください）。

```console
schroot -r -c bionic-amd64-sbuild-ec0f01f1-fc92-4ac0-940f-15acf7a9346c -u root -d /root
```

# chrootのセッションを削除

特定のセッションを終了して削除するには `schroot -e -c セッションID` と実行します。
その後 `schroot -l --all-sessions` 指定したセッションがなくなっていることを確認します。

全てのセッションを終了するには `schroot -e --all-sessions` とします。
[SimpleSbuild - Ubuntu Wiki](https://wiki.ubuntu.com/SimpleSbuild) の Expiring active schroot sessions に書いていました。
