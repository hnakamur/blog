---
title: "NAXSIを動的モジュールとしてビルドしたnginxのdebパッケージを作成した"
date: 2025-07-21T18:24:00+09:00
---

## ビルドのメモ

[wargio/naxsi: NAXSI is an open-source, high performance, low rules maintenance WAF for NGINX](https://github.com/wargio/naxsi)をビルドしたメモです。
オリジナル[nbs-system/naxsi](https://github.com/nbs-system/naxsi) は2023-11-08にアーカイブ済み。

ビルド用のレポジトリは https://github.com/hnakamur/nginx-deb-docker です。

* stableブランチ
  * nginxのstableバージョンをビルドしていて、現在は1.28.0です。
  * naxsiは2024-12-26にリリースされたバージョン[1.7](https://github.com/wargio/naxsi/releases/tag/1.7)をビルドしました。
  * 作成したリリース:
    * [1.28.0+mod.3-2hn1ubuntu22.04](https://github.com/hnakamur/nginx-deb-docker/releases/tag/1.28.0%2Bmod.3-2hn1ubuntu22.04)
    * [1.28.0+mod.3-2hn1ubuntu24.04](https://github.com/hnakamur/nginx-deb-docker/releases/tag/1.28.0%2Bmod.3-2hn1ubuntu24.04)
* mainlineブランチ
  * nginxのmainlineバージョンをビルドしていて、現在は1.29.0です。
  * naxsiはmasterブランチの[7a6df55edfe7ee190f2490cc1ca3ff1cf851d0e5](https://github.com/wargio/naxsi/commit/7a6df55edfe7ee190f2490cc1ca3ff1cf851d0e5)のコミットをビルドしました。
  * 作成したリリース:
    * [1.29.0+mod.3-2hn1ubuntu22.04](https://github.com/hnakamur/nginx-deb-docker/releases/tag/1.29.0%2Bmod.3-2hn1ubuntu22.04)
    * [1.29.0+mod.3-2hn1ubuntu24.04](https://github.com/hnakamur/nginx-deb-docker/releases/tag/1.29.0%2Bmod.3-2hn1ubuntu24.04)

## 補足メモ

本題は以上で、以下は細かい話ですが、ついでにメモ。

### Dependsのライブラリの一部をRecommendsとSuggetsに移動

今回の変更前はnginxの動的モジュールが使用する共有ライブラリがすべてDependsに含まれていました。
そのため、aptでインストールする際にそれらのライブラリすべてをインストールする必要がありました。

動的モジュールなのでnginxの設定によって使わないこともあるのにインストールを強制されるのは
望ましくないです。

そこで一部をRecommendsとSuggetsに移動しました。

`debian/rules`は1行目のshebangが`#!/usr/bin/make -f`となっており、2行目以降はMakefile形式になっています。
[debian/rules#L292-L308](https://github.com/hnakamur/nginx-deb-docker/blob/1.29.0%2Bmod.3-2hn1ubuntu24.04/debian/rules#L292-L308)の`binary-arch`ターゲットの`dh_shlibdeps -a`の後に、これで生成される`debian/nginx.substvars`ファイルを加工するためのコマンドを追加しました。

```
binary-arch: install build-dbg
	dh_testdir
	dh_testroot
	dh_installchangelogs -a
	dh_installdocs -a
	dh_lintian -a
	dh_link -aA
	dh_compress -a
	dh_perl -a
	dh_fixperms -a
	dh_installdeb -a
	dh_shlibdeps -a
	mv debian/nginx.substvars debian/nginx.substvars.orig
	debian/modify-substvars < debian/nginx.substvars.orig > debian/nginx.substvars
	dh_gencontrol -a
	dh_md5sums -a
	dh_builddeb $(foreach p,$(DO_PKGS),-p$(p))
```

上記で呼んでいる[debian/modify-substvars](https://github.com/hnakamur/nginx-deb-docker/blob/1.29.0%2Bmod.3-2hn1ubuntu24.04/debian/modify-substvars)は今回の変更で追加したPerlスクリプトです。
`libssl3(t64)? `の箇所はUbuntu 24.04ではlibssl3t64、Ubuntu 22.04ではlibssl3というパッケージ名の両方に対応するためです。

```
#!/usr/bin/perl
use strict;
use warnings;

my $line = <STDIN>;
chomp $line;
$line =~ s/^shlibs:Depends=//;

my @depends = ();
my @recommends = ();
my @suggests = ();
my @fields = split /, /, $line;
foreach my $field (@fields) {
  if ($field =~ /^(libc6 |libcrypt1 |libpcre3$|libssl3(t64)? |zlib1g )/) {
    push @depends, $field;
  } elsif ($field =~ /^libluajit-5.1-2 /) {
    push @recommends, $field;
  } else {
    push @suggests, $field;
  }
}
my $depends = join(", ", @depends);
my $recommends = join(", ", @recommends);
my $suggests = join(", ", @suggests);
print "shlibs:Depends=$depends\nshlibs:Recommends=$recommends\nshlibs:Suggests=$suggests\n";
```

[debian/control#L30-L34](https://github.com/hnakamur/nginx-deb-docker/blob/1.29.0%2Bmod.3-2hn1ubuntu24.04/debian/control#L30-L34)の部分を今回変更して、RecommendsとSugguestsの行を追加しました。

```
Package: nginx
Architecture: any
Depends: ${misc:Depends}, ${shlibs:Depends}, lsb-base (>= 3.0-6), adduser
Recommends: ${shlibs:Recommends}
Suggests: ${shlibs:Suggests}
```

ビルドしたnginxをインストールした環境で`apt show nginx`でDepends、Recommends、Suggestsを確認すると以下のようになっていました。

```
# dpkg-query -W -f 'Version: ${Version}\nDepends: ${Depends}\nRecommends: ${Recommends}\nSuggests: ${Suggests}\n' nginx
Version: 1.29.0+mod.3-2hn1ubuntu24.04
Depends: libc6 (>= 2.38), libcrypt1 (>= 1:4.1.0), libpcre3, libssl3t64 (>= 3.0.0), zlib1g (>= 1:1.1.4), lsb-base (>= 3.0-6), adduser
Recommends: libluajit-5.1-2 (>= 2.1.20250117)
Suggests: libcares2 (>= 1.11.0~rc1), libgcc-s1 (>= 3.3.1), libgd3 (>= 2.1.0~alpha~), libgeoip1t64 (>= 1.6.12), libmhash2 (>= 0.9.9.9), libmodsecurity3 (>= 3.0.14), libperl5.38t64 (>= 5.38.2), libstdc++6 (>= 13.1), libxml2 (>= 2.7.4), libxslt1.1 (>= 1.1.25)
```

```
# dpkg-query -W -f 'Version: ${Version}\nDepends: ${Depends}\nRecommends: ${Recommends}\nSuggests: ${Suggests}\n' nginx
Version: 1.29.0+mod.3-2hn1ubuntu22.04
Depends: libc6 (>= 2.35), libcrypt1 (>= 1:4.1.0), libpcre3, libssl3 (>= 3.0.0~~alpha1), zlib1g (>= 1:1.1.4), lsb-base (>= 3.0-6), adduser
Recommends: libluajit-5.1-2 (>= 2.1.20250117)
Suggests: libc-ares2 (>= 1.11.0~rc1), libgcc-s1 (>= 3.3.1), libgd3 (>= 2.1.0~alpha~), libgeoip1 (>= 1.6.12), libmhash2 (>= 0.9.9.9), libmodsecurity3 (>= 3.0.14), libperl5.34 (>= 5.34.0), libstdc++6 (>= 11), libxml2 (>= 2.7.4), libxslt1.1 (>= 1.1.25)
```

```
# dpkg-query -W -f 'Version: ${Version}\nDepends: ${Depends}\nRecommends: ${Recommends}\nSuggests: ${Suggests}\n' nginx
Version: 1.28.0+mod.3-2hn1ubuntu24.04
Depends: libc6 (>= 2.38), libcrypt1 (>= 1:4.1.0), libpcre3, libssl3t64 (>= 3.0.0), zlib1g (>= 1:1.1.4), lsb-base (>= 3.0-6), adduser
Recommends: libluajit-5.1-2 (>= 2.1.20250117)
Suggests: libcares2 (>= 1.11.0~rc1), libgcc-s1 (>= 3.3.1), libgd3 (>= 2.1.0~alpha~), libgeoip1t64 (>= 1.6.12), libmhash2 (>= 0.9.9.9), libmodsecurity3 (>= 3.0.14), libperl5.38t64 (>= 5.38.2), libstdc++6 (>= 13.1), libxml2 (>= 2.7.4), libxslt1.1 (>= 1.1.25)
```

```
# dpkg-query -W -f 'Version: ${Version}\nDepends: ${Depends}\nRecommends: ${Recommends}\nSuggests: ${Suggests}\n' nginx
Version: 1.28.0+mod.3-2hn1ubuntu22.04
Depends: libc6 (>= 2.35), libcrypt1 (>= 1:4.1.0), libpcre3, libssl3 (>= 3.0.0~~alpha1), zlib1g (>= 1:1.1.4), lsb-base (>= 3.0-6), adduser
Recommends: libluajit-5.1-2 (>= 2.1.20250117)
Suggests: libc-ares2 (>= 1.11.0~rc1), libgcc-s1 (>= 3.3.1), libgd3 (>= 2.1.0~alpha~), libgeoip1 (>= 1.6.12), libmhash2 (>= 0.9.9.9), libmodsecurity3 (>= 3.0.14), libperl5.34 (>= 5.34.0), libstdc++6 (>= 11), libxml2 (>= 2.7.4), libxslt1.1 (>= 1.1.25)
```

[man apt-get](https://manpages.ubuntu.com/manpages/noble/en/man8/apt-get.8.html)のOPTIONSの項に以下の説明があります。

```
--no-install-recommends
    Do not consider recommended packages as a dependency for installing. Configuration Item:
    APT::Install-Recommends.

--install-suggests
    Consider suggested packages as a dependency for installing. Configuration Item:
    APT::Install-Suggests.
```

これらのオプション無しだとlibluajit-5.1-2はインストールされますが、libcares2などはインストールされないということになります。

[lua-nginx-module](https://github.com/openresty/lua-nginx-module)を使わない場合は`--no-install-recommends`を指定してインストールすればよいです。ただし、deb内のnginx設定ファイルは使う設定になっているので、インストール後に設定ファイルを書き換えてから起動する必要があります。

```
# sed -i '/^load_module/d' /etc/nginx/nginx.conf
# sed -i '/^lua_package/d' /etc/nginx/conf.d/default.conf
```

### このレポジトリのdebianディレクトリのファイルについて

なお、 https://github.com/hnakamur/nginx-deb-docker のdebビルドの設定ファイルはかなり昔に（DebianやUbuntuのパッケージのではなく）nginx.orgで提供しているものをコピーして改変したものです。

おそらく https://github.com/nginx/pkg-oss からコピーしたと思います。
[debian/nginx.rules.in#L129-L143](https://github.com/nginx/pkg-oss/blob/d6e73108f7b037bd559ba449bf4d6f8d6f81b99a/debian/debian/nginx.rules.in#L129-L143)を見ると、上記に引用したdebian/rulesのbinary-archターゲットの今回の変更前の内容と一致していました。
