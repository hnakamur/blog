+++
title="Ubuntu 18.04 LTSでsbuildをセットアップ"
date = "2018-06-07T21:10:00+09:00"
tags = ["ubuntu", "deb", "sbuild"]
categories = ["blog"]
+++


# はじめに

手元でpbuilderでdebパッケージのビルドが通ってからPPAでビルドしたらテストの1つがエラーになるという問題が起きてしまい、ビルドログを見てみると以下のような行があって `sbuild` を使っていることに気づきました。

```text
Buildd toolchain package versions: launchpad-buildd_161 python-lpbuildd_161 sbuild_0.67.0-2ubuntu7.1 bzr-builder_0.7.3+bzr174~ppa13~ubuntu14.10.1 bzr_2.7.0-2ubuntu3.1 git-build-recipe_0.3.4~git201611291343.dcee459~ubuntu16.04.1 git_1:2.7.4-0ubuntu1.4 dpkg-dev_1.18.4ubuntu1.4 python-debian_0.1.27ubuntu2.
```

そこで [SimpleSbuild - Ubuntu Wiki](https://wiki.ubuntu.com/SimpleSbuild) を参考に `sbuild` をセットアップしてみたのでメモです。

# sbuildのセットアップ手順

必要なパッケージをインストールし、自分のユーザを `sbuild` グループに追加します。追加後一旦ログアウトして再ログインしておきます。

```console
sudo apt install sbuild debhelper ubuntu-dev-tools piuparts
sudo adduser $USER sbuild
```

`$HOME/ubuntu/scratch` ディレクトリを作成し、 chroot環境から `/scratch` でマウントするように設定します。

```console
mkdir -p $HOME/ubuntu/scratch
echo "/home/$USER/ubuntu/scratch  /scratch          none  rw,bind  0  0" | sudo tee -a /etc/schroot/sbuild/fstab
```

`~/.buildrc` ファイルを作成します。
`$maintainer_name` の名前とメールアドレスは適宜変更してください。

```console
cat <<'EOF' > ~/.sbuildrc
# Name to use as override in .changes files for the Maintainer: field
# (mandatory, no default!).
$maintainer_name='Your Name <your_name@example.com>';

# Default distribution to build.
$distribution = "bionic";
# Build arch-all by default.
$build_arch_all = 1;

# When to purge the build directory afterwards; possible values are "never",
# "successful", and "always".  "always" is the default. It can be helpful
# to preserve failing builds for debugging purposes.  Switch these comments
# if you want to preserve even successful builds, and then use
# "schroot -e --all-sessions" to clean them up manually.
$purge_build_directory = 'successful';
$purge_session = 'successful';
$purge_build_deps = 'successful';
# $purge_build_directory = 'never';
# $purge_session = 'never';
# $purge_build_deps = 'never';

# Directory for writing build logs to
$log_dir=$ENV{HOME}."/ubuntu/logs";

# don't remove this, Perl needs it:
1;
EOF
```

`$HOME/ubuntu/build` と `$HOME/ubuntu/logs` ディレクトリを作成します。

```console
mkdir -p $HOME/ubuntu/{build,logs}
```

`~/.mk-sbuild.rc` を作成します。

```console
cat <<'EOF' > ~/.mk-sbuild.rc
SCHROOT_CONF_SUFFIX="source-root-users=root,sbuild,admin
source-root-groups=root,sbuild,admin
preserve-environment=true"
# you will want to undo the below for stable releases, read `man mk-sbuild` for details
# during the development cycle, these pockets are not used, but will contain important
# updates after each release of Ubuntu
SKIP_UPDATES="1"
SKIP_PROPOSED="1"
# if you have e.g. apt-cacher-ng around
# DEBOOTSTRAP_PROXY=http://127.0.0.1:3142/
EOF
```

`sbuild` グループに切り替えます。

```console
sg sbuild
```

`sbuild` で使うGPG鍵ペアを生成します。

```console
sbuild-update --keygen
```

Ubuntu 18.04 LTSのchroot環境をビルドします。

```console
mk-sbuild bionic
```

ビルドが完了すると以下のようなメッセージが表示されます。

```text
Done building bionic-amd64.

 To CHANGE the golden image: sudo schroot -c source:bionic-amd64 -u root
 To ENTER an image snapshot: schroot -c bionic-amd64
 To BUILD within a snapshot: sbuild -A -d bionic-amd64 PACKAGE*.dsc
 To BUILD for : sbuild -A -d bionic-amd64 --host  PACKAGE*.dsc
```

# sbuildでのdebパッケージビルド例

ここでは例として universal-ctags のdebパッケージをビルドしてみました。

試行錯誤したのでもっと良いやり方があるかもしれません。最初は上のメッセージのように引数で `.dsc` のファイルパスを指定する方法を試したのですが `../build-area/universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1.dsc` のように相対パスで指定するとログディレクトリを作るところでおかしくなってしまいました。一方で、カレントディレクトリに `debian` ディレクトリがある状態で実行する必要があるようです。

`gbp-buildpackage buildpackage` でビルドしたソースパッケージを `~/ubuntu/scratch` ディレクトリにコピーします。コピー後の状態は以下のような感じです。

```console
hnakamur@primergy:~/ubuntu/scratch$ ls universal-ctags_0*
universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1.debian.tar.xz
universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1.dsc
universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1_source.build
universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1_source.buildinfo
universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1_source.changes
universal-ctags_0+SNAPSHOT20180606.orig.tar.gz
```

ビルド用のディレクトリ `~/ubuntu/scratch/universal-ctags` を作って `debian` ディレクトリのファイルを展開します。

```console
mkdir universal-ctags
tar xf universal-ctags_0+SNAPSHOT20180606-1ubuntu1ppa3~ubuntu18.04.1.debian.tar.xz -C universal-ctags
```

ビルド用のディレクトリ `~/ubuntu/scratch/universal-ctags` に移動して引数なしで `sbuild` コマンドを実行してパッケージをビルドします。

```console
cd universal-ctags
sbuild
