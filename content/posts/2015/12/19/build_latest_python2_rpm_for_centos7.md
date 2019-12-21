+++
Categories = []
Description = ""
Tags = ["centos", "python", "rpmbuild", "software-collections"]
date = "2015-12-19T11:51:30+09:00"
title = "CentOS 7用にPython2最新版のrpmを作ってみた"

+++
## はじめに
[coprのAPIをcurlで呼び出す · hnakamur's blog at github](/blog/2015/12/16/calling_copr_api_with_curl/)にも書きましたが、CentOS 7のPythonは古くてhttps通信時にInsecurePlatformWarningが出てしまいます。

そこで、[Software CollectionsのPython27のpythonパッケージ](https://www.softwarecollections.org/repos/rhscl/python27/epel-7-x86_64/python27-python-2.7.8-3.el7/)を改変してPython2の最新版2.7.11のrpmを作ってみました。
[Software Collections](https://www.softwarecollections.org/en/)のrpmをベースにしていますので、CentOS 7にインストールされているPythonとは共存可能となっています。

## Python2の最新版rpmの利用方法

先に利用方法を書いておきます。

### インストール手順

dockerのcentos:7コンテナにインストールする例で説明します。まず以下のコマンドでコンテナを起動します。

```
docker run -it centos:7 /bin/bash
```

次に以下のコマンドを実行してPython2をインストールします。

```
curl -sL -o /etc/yum.repos.d/hnakamur-hnscl-python2.repo https://copr.fedoraproject.org/coprs/hnakamur/hnscl-python2/repo/epel-7/hnakamur-hnscl-python2-epel-7.repo
curl -sL -o /etc/yum.repos.d/hnakamur-hnscl-python2-python.repo https://copr.fedoraproject.org/coprs/hnakamur/hnscl-python2-python/repo/epel-7/hnakamur-hnscl-python2-python-epel-7.repo
yum -y install hn-python2-python
```


### 使い方

以下のコマンドでPython2最新版用のシェルを起動します。

```
scl enable hn-python2 bash
```

あとは通常通りpythonコマンドを実行すればOKです。

```
# which python
/opt/hn/hn-python2/root/usr/bin/python
# python -V
Python 2.7.11
```

使い終わったら `exit` で上記で起動したシェルを抜けてください。

ちなみに、Software Collectionsで提供されているPython 2.7のインストール方法は[Python 2.7 — Software Collections](https://www.softwarecollections.org/en/scls/rhscl/python27/)です。

## Python2の最新版rpmを作った時のメモ

以下はrpmを作った時のメモです。[Packaging Guide — Software Collections](https://www.softwarecollections.org/en/docs/guide/)を読みながら試行錯誤してrpmを作りました。

### Software Collectionsのメタパッケージ

[Packaging Guide — Software Collections](https://www.softwarecollections.org/en/docs/guide/#sect-Package_Layout)で説明されていますが、Software Collectionsではメタパッケージというのを作成します。

例えば今回ベースにしたPython 2.7だと[python27](https://www.softwarecollections.org/repos/rhscl/python27/epel-7-x86_64/python27-1.1-20.el7/)というのがメタパッケージで、　Python2本体のパッケージは[Software CollectionsのPython27のpythonパッケージ](https://www.softwarecollections.org/repos/rhscl/python27/epel-7-x86_64/python27-python-2.7.8-3.el7/)です。

Software Collectionsを自作する場合は、パッケージ名が衝突しないように「組織名-」という接頭辞をつけるようにと[2.4. The Software Collection Prefix](https://www.softwarecollections.org/en/docs/guide/#sect-The_Software_Collections_Prefix)に書かれています。公式のソフトウェアコレクションは接頭辞無しで `python27` のようなコレクション名になっています。

また、[2.2. The File System Hierarchy](https://www.softwarecollections.org/en/docs/guide/#sect-The_File_System_Hierarchy)に書かれているように、ソフトウェアコレクションのrpmに含まれるファイルは `/opt/提供者名/ソフトウェアコレクション名/` というディレクトリ構成を取ります。公式のソフトウェアコレクションは `/opt/rh/ソフトウェアコレクション名/` というディレクトリになっています。rhはredhatの略だと思います。

今回は `hn-python2` というメタパッケージ名とし、ディレクトリは `/opt/hn/python2/` としました。

### Software Collectionsのメタパッケージのビルド

ビルド用のファイルは[hnakamur/hnscl-python2-rpm](https://github.com/hnakamur/hnscl-python2-rpm)に置いてあります。

[2.3. The Software Collection Root Directory](https://www.softwarecollections.org/en/docs/guide/#sect-The_Software_Collection_Root_Directory)によるとspecファイルに以下のように書けばよいそうです。providerの箇所は提供者ごとの値に変えます。

```
%global _scl_prefix /opt/provider
```

ですが、実際に試してみるとこの設定だけだと、ビルドされたrpm内のファイルパスだったりファイルの中身に `/opt/rh/` というパスが残ってしまいました。試行錯誤の結果以下のように書くことで全て `/opt/hn/` に変わりました。

[hn-python2-spec](https://github.com/hnakamur/hnscl-python2-rpm/blob/06a6fa366bd485d722139f0637ce2def364eaef3/SPECS/hn-python2.spec#L1-L22)

```
%global scl_name_prefix hn-
%global scl_name_base python
%global scl_name_version 2
%global scl %{scl_name_prefix}%{scl_name_base}%{scl_name_version}

# NOTE: You must set _scl_prefix before '%scl_package %scl'.
%global _scl_prefix /opt/hn
# NOTE: The following variables must be re-evaluated after changing _scl_prefix above.
# I got these settings after trials and errors.
# I don't know this is the right way to set directories with my _scl_prefix.
%global _scl_scripts            %{_scl_prefix}/%{scl}
%global _scl_root               %{_scl_prefix}/%{scl}/root
%global _prefix                 %{_scl_root}/usr
%global _sysconfdir             %{_scl_root}/etc
%global _sharedstatedir         %{_scl_root}/var/lib
%global _localstatedir          %{_scl_root}/var
%global _datadir                %{_scl_root}/share
%global _docdir                 %{_datadir}/doc
%global _mandir                 %{_datadir}/man


%scl_package %scl
...(snip)...
```

### Python本体のパッケージのビルド

ビルド用のファイルは[hnakamur/hnscl-python2-python-rpm](https://github.com/hnakamur/hnscl-python2-python-rpm)に置いてあります。

インストールディレクトリを `/opt/hn/` 以下にするため、試行錯誤した結果specファイルに以下のように書けばOKでした。

[python.spec](https://github.com/hnakamur/hnscl-python2-python-rpm/blob/3a13fe74587d6beca871d28a68149a2273488672/SPECS/python.spec#L1-L31)

```
%global scl_name_prefix hn-
%global scl_name_base python
%global scl_name_version 2
%global scl %{scl_name_prefix}%{scl_name_base}%{scl_name_version}

# NOTE: You must set _scl_prefix before '%scl_package %scl'.
%global _scl_prefix /opt/hn
# NOTE: The following variables must be re-evaluated after changing _scl_prefix above.
%global _scl_scripts            %{_scl_prefix}/%{scl}
%global _scl_root               %{_scl_prefix}/%{scl}/root
%global _prefix                 %{_scl_root}/usr
%global _sysconfdir             %{_scl_root}/etc
%global _sharedstatedir         %{_scl_root}/var/lib
%global _localstatedir          %{_scl_root}/var

%global _includedir             %{_prefix}/include
%if "%{_lib}" == "lib64"
%global _libdir                 %{_prefix}/lib64
%else
%global _libdir                 %{_prefix}/lib
%endif
%global _datadir                %{_prefix}/share
%global _docdir                 %{_prefix}/share/doc
%global _datarootdir            %{_prefix}/share
%global _infodir                %{_prefix}/share/info
%global _mandir                 %{_prefix}/share/man
%global _defaultdocdir          %{_prefix}/share/doc

%global _exec_prefix            %{_prefix}
%global _bindir                 %{_exec_prefix}/bin
%global _sbindir                %{_exec_prefix}/sbin
...(snip)...
```

### Python本体のspecファイルのパッチ更新

[python.spec](https://github.com/hnakamur/hnscl-python2-python-rpm/blob/3a13fe74587d6beca871d28a68149a2273488672/SPECS/python.spec)には約60個のパッチが含まれています。

Pythonのソースのバージョンを上げたのでパッチが当たらなくなるケースが出てきました。patchを実行した時に生成される `*.rej` ファイルを見て、なんとなくこんな感じだろという軽いノリでパッチを一通り更新しました。

作業手順は[mockを使ったrpmビルドが失敗した時の調査方法 · hnakamur's blog at github](/blog/2015/12/16/how_to_debug_errors_in_rpm_build_using_mock/)に書いた手順で、mockのchroot環境内でパッチを修正して `rpmbuild -bp specファイル名` でパッチを当てるというのをひたすら繰り返した感じです。

パッチ1つごとの修正を[Commits · hnakamur/hnscl-python2-python-rpm](https://github.com/hnakamur/hnscl-python2-python-rpm/commits/master)のだいたい1つのコミットにしています。ただ、後からさらに修正が必要だったものは別コミットになっていますが。

また、CentOSのPythonのspecファイルではリリースビルドとデバッグビルドを作ってテストも実行するようになっています。これがかなり時間がかるので、ビルドが通らない段階では[リリースビルドだけにしてテストは実行しないようにしていました](https://github.com/hnakamur/hnscl-python2-python-rpm/commit/ebb31040e3e5bfe0ceb62cd4eb67793bd1a333b0)。ビルドが落ち着いてきたところで[この変更をgit revert](https://github.com/hnakamur/hnscl-python2-python-rpm/commit/8a293e3dbd25f6cb6638b00efc07ce5cf962a397)してビルド・テストするようにしました。

## おわりに
[Software CollectionsのPython27のpythonパッケージ](https://www.softwarecollections.org/repos/rhscl/python27/epel-7-x86_64/python27-python-2.7.8-3.el7/)を改変して作ったPython2の最新版2.7.11のrpmについて説明しました。

CentOS 7でもPython2の最新版が手軽に利用可能になるので、ぜひご活用ください。

