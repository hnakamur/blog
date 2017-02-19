Title: 1台のサーバに異なる設定でApache Traffic Serverを複数立ち上げるためのビルド設定
Date: 2016-07-02 01:00
Category: blog
Tags: apachetrafficserver
Slug: 2016/07/02/config-for-multiple-installations-of-apache-traffic-server

## はじめに
Apache Traffic Serverには[Hierarchical Caching](https://docs.trafficserver.apache.org/en/latest/admin-guide/configuration/hierachical-caching.en.html)という機能があって、キャッシュを親と子の2階層にすることが出来ます。

CentOSで1つのサーバに親と子の2つのTraffic Server 6.1.1を異なる設定で起動するような構成にしたかったのですが、本家のrpmでは出来ないようでした。
ソースを見ていたらconfigureオプションをうまく指定すれば可能だとわかり、カスタムrpmを作りました。

rpmのspecファイルは[apache-traffic-server-rpm/trafficserver.spec](https://github.com/hnakamur/apache-traffic-server-rpm/blob/d1688aec09f6761841bbc638938577cae49beccd/SPECS/trafficserver.spec)、ビルドしたrpmは [hnakamur/apache-traffic-server-6 Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/apache-traffic-server-6/) で公開しています。

## 起動オプションではやりたいことは出来なさそうでした

カスタムrpmを作る前に、本家のrpmを使いつつコマンドラインオプションや環境変数の設定によってやりたいことが実現できないか調べてみたのですが、出来なさそうでした。

バージョン6.1.1のソースを見た時のメモです。

まず、 `traffic_server` コマンドには `-conf_dir` というオプションがあります。ソースは [proxy/Main.cc](https://github.com/apache/trafficserver/blob/6.1.1/proxy/Main.cc#L206) です。[traffic_serverのドキュメント](https://docs.trafficserver.apache.org/en/6.1.x/appendices/command-line/traffic_server.en.html)には記載がありません。

一方、 `traffic_manager` コマンドには `-tsArgs` というオプションがあります。 ソースは [cmd/traffic_manager/traffic_manager.cc](https://github.com/apache/trafficserver/blob/6.1.1/cmd/traffic_manager/traffic_manager.cc#L453) で [traffic_managerのドキュメント](https://docs.trafficserver.apache.org/en/6.1.x/appendices/command-line/traffic_manager.en.html#cmdoption-traffic_manager--tsArgs) にも説明はありませんが載っています。

しかし、 `traffic_cop` コマンドが `traffic_manager` コマンドを起動する際には `-tsArgs` オプションは指定していません。ソースは [cmd/traffic_cop/traffic_cop.cc](https://github.com/apache/trafficserver/blob/6.1.1/cmd/traffic_cop/traffic_cop.cc#L758) です。 [traffic_cop](https://docs.trafficserver.apache.org/en/6.1.x/appendices/command-line/traffic_cop.en.html) のドキュメントを見ても traffic_manager にオプションを渡すためのオプションは無いようです。

rpmでインストールされるサービス起動スクリプトだと `traffic_cop` →　`traffic_manger` →　`traffic_sever` という呼び出し関係になるので、こ `traffic_server`   に `-conf_dir` オプションを渡すことは出来なさそうです。

## TS_ROOTという環境変数を発見

[lib/ts/Layout.cc](https://github.com/apache/trafficserver/blob/6.1.1/lib/ts/Layout.cc#L146-L187) で `TS_ROOT` という環境変数を参照しているのを見つけました。

```
Layout::Layout(const char *_prefix)
{
  if (_prefix) {
    prefix = ats_strdup(_prefix);
  } else {
    char *env_path;
    char path[PATH_NAME_MAX];
    int len;

    if ((env_path = getenv("TS_ROOT"))) {
      len = strlen(env_path);
      if ((len + 1) > PATH_NAME_MAX) {
        ink_error("TS_ROOT environment variable is too big: %d, max %d\n", len, PATH_NAME_MAX - 1);
        return;
      }
      ink_strlcpy(path, env_path, sizeof(path));
      while (len > 1 && path[len - 1] == '/') {
        path[len - 1] = '\0';
        --len;
      }
    } else {
      // Use compile time --prefix
      ink_strlcpy(path, TS_BUILD_PREFIX, sizeof(path));
    }

    prefix = ats_strdup(path);
  }
  exec_prefix = layout_relative(prefix, TS_BUILD_EXEC_PREFIX);
  bindir = layout_relative(prefix, TS_BUILD_BINDIR);
  sbindir = layout_relative(prefix, TS_BUILD_SBINDIR);
  sysconfdir = layout_relative(prefix, TS_BUILD_SYSCONFDIR);
  datadir = layout_relative(prefix, TS_BUILD_DATADIR);
  includedir = layout_relative(prefix, TS_BUILD_INCLUDEDIR);
  libdir = layout_relative(prefix, TS_BUILD_LIBDIR);
  libexecdir = layout_relative(prefix, TS_BUILD_LIBEXECDIR);
  localstatedir = layout_relative(prefix, TS_BUILD_LOCALSTATEDIR);
  runtimedir = layout_relative(prefix, TS_BUILD_RUNTIMEDIR);
  logdir = layout_relative(prefix, TS_BUILD_LOGDIR);
  mandir = layout_relative(prefix, TS_BUILD_MANDIR);
  infodir = layout_relative(prefix, TS_BUILD_INFODIR);
  cachedir = layout_relative(prefix, TS_BUILD_CACHEDIR);
}
```

[layout_relative関数の定義](https://github.com/apache/trafficserver/blob/6.1.1/lib/ts/Layout.cc#L51-L70) と [ink_filepath_merge関数の定義](https://github.com/apache/trafficserver/blob/d6906e2a59858005d09018994262562b03ca24e9/lib/ts/ink_file.cc#L132-L323) を見ると、 layout_relative の第2引数が `/` で始まっていると第2引数がそのまま使われ、 `/` で始まっていないと第1引数と第2引数を必要に応じて `/` を挟んで連結した値になることがわかりました。

`TS_BUILD_SYSCONFDIR` などは[trafficserver/ink_config.h.in](https://github.com/apache/trafficserver/blob/6.1.1/lib/ts/ink_config.h.in#L110-L125) で定義されていました。

```
/* Various "build" defines */
#define TS_BUILD_PREFIX "@prefix@"
#define TS_BUILD_EXEC_PREFIX "@rel_exec_prefix@"
#define TS_BUILD_BINDIR "@rel_bindir@"
#define TS_BUILD_SBINDIR "@rel_sbindir@"
#define TS_BUILD_SYSCONFDIR "@rel_sysconfdir@"
#define TS_BUILD_DATADIR "@rel_datadir@"
#define TS_BUILD_INCLUDEDIR "@rel_includedir@"
#define TS_BUILD_LIBDIR "@rel_libdir@"
#define TS_BUILD_LIBEXECDIR "@rel_libexecdir@"
#define TS_BUILD_LOCALSTATEDIR "@rel_localstatedir@"
#define TS_BUILD_RUNTIMEDIR "@rel_runtimedir@"
#define TS_BUILD_LOGDIR "@rel_logdir@"
#define TS_BUILD_MANDIR "@rel_mandir@"
#define TS_BUILD_CACHEDIR "@rel_cachedir@"
#define TS_BUILD_INFODIR "@rel_infodir@"
```

`rel_*` という値は `configure` 実行時にbuild/common.m4の [TS_SUBST_LAYOUT_PATH](https://github.com/apache/trafficserver/blob/5a0952b01d01ef927a65fc44bac5f68c345747aa/build/common.m4#L252-L263) で設定されるようです。

```
dnl
dnl TS_SUBST_LAYOUT_PATH
dnl Export (via TS_SUBST) the various path-related variables that
dnl trafficserver will use while generating scripts and
dnl the default config file.
AC_DEFUN([TS_SUBST_LAYOUT_PATH], [
  TS_EXPAND_VAR(exp_$1, [$]$1)
  TS_PATH_RELATIVE(rel_$1, [$]exp_$1, ${prefix})
  TS_SUBST(exp_$1)
  TS_SUBST(rel_$1)
  TS_SUBST($1)
])
```

ここから呼ばれる [TS_PATH_RELATIVE](https://github.com/apache/trafficserver/blob/5a0952b01d01ef927a65fc44bac5f68c345747aa/build/common.m4#L223-L241) で実際の値が作られます。

```
dnl
dnl Removes the value of $3 from the string in $2, strips of any leading
dnl slashes, and returns the value in $1.
dnl
dnl Example:
dnl orig_path="${prefix}/bar"
dnl TS_PATH_RELATIVE(final_path, $orig_path, $prefix)
dnl    $final_path now contains "bar"
AC_DEFUN([TS_PATH_RELATIVE], [
ats_stripped=`echo $2 | sed -e "s#^$3##"`
# check if the stripping was successful
if test "x$2" != "x${ats_stripped}"; then
# it was, so strip of any leading slashes
    $1="`echo ${ats_stripped} | sed -e 's#^/*##'`"
else
# it wasn't so return the original
    $1="$2"
fi
])
```

ということで、例えば `sysconfdir` の値が `prefix` の値で始まっていれば `rel_sysconfdir` は `prefix` からの相対パスになり、そうでなければ `sysconfdir` そのままになるということがわかりました。


## configureオプションの指定方法

上記を踏まえて、私が作成した [/trafficserver.spec](https://github.com/hnakamur/apache-traffic-server-rpm/blob/d1688aec09f6761841bbc638938577cae49beccd/SPECS/trafficserver.spec) では [1行目](https://github.com/hnakamur/apache-traffic-server-rpm/blob/d1688aec09f6761841bbc638938577cae49beccd/SPECS/trafficserver.spec#L1)で

```
%define _prefix /opt/trafficserver
```

と設定し、 [85〜94行目](https://github.com/hnakamur/apache-traffic-server-rpm/blob/d1688aec09f6761841bbc638938577cae49beccd/SPECS/trafficserver.spec#L85-L94) で以下のような configure オプションを指定しています。

```
%configure \
  --enable-layout=opt \
  --sysconfdir=%{_prefix}%{_sysconfdir} \
  --localstatedir=%{_prefix}%{_localstatedir} \
  --libexecdir=%{_prefix}/%{_lib}/plugins \
  --with-tcl=/usr/%{_lib} \
  --enable-luajit \
  --with-user=ats --with-group=ats \
  --disable-silent-rules \
  --enable-experimental-plugins
```

これでビルドしたtrafficserverを実行する際に、環境変数TS_ROOTを設定することで以下のようなディレクトリを参照することが出来ました。

* sysconfdir: ${TS_ROOT}/etc
* localstatedir: ${TS_ROOT}/var/run
* libexecdir: ${TS_ROOT}/lib64/plugins

## 私が使っているディレクトリ構成

実際には以下のようなシンボリックリンクを貼って使っています。

* 1段目
    - /opt/trafficserver-first/etc -> /etc/trafficserver-first 
    - /opt/trafficserver-first/bin -> /opt/trafficserver/bin
    - /opt/trafficserver-first/lib64 -> /opt/trafficserver/lib64
    - /opt/trafficserver-first/var/cache -> /var/cache/trafficserver-first
    - /opt/trafficserver-first/var/logs -> /var/log/trafficserver-first
    - /opt/trafficserver-first/var/run -> /var/run/trafficserver-first
* 2段目
    - /opt/trafficserver-second/etc -> /etc/trafficserver-second 
    - /opt/trafficserver-second/bin -> /opt/trafficserver/bin
    - /opt/trafficserver-second/lib64 -> /opt/trafficserver/lib64
    - /opt/trafficserver-second/var/cache -> /var/cache/trafficserver-second
    - /opt/trafficserver-second/var/logs -> /var/log/trafficserver-second
    - /opt/trafficserver-second/var/run -> /var/run/trafficserver-second

## コマンド実行時の環境変数指定

コマンドを実行するときはPATHを通すかフルパスで指定するだけではなく、 TS_ROOT 環境変数も指定する必要があります。

例えば、1段目のキャッシュを全クリアするときは [Clearing the Cache](https://docs.trafficserver.apache.org/en/6.1.x/admin-guide/storage/index.en.html#clearing-the-cache) の説明では `traffic_server -Cclear` ですが、このrpmの場合は

```
TS_ROOT=/opt/trafficserver-first /opt/trafficserver-first/bin/traffic_server -Cclear
```

と実行する必要があります。
