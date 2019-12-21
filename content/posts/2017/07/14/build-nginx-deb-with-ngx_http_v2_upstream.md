+++
title="ngx_http_v2_upstreamモジュールを追加したnginxのdebパッケージを作ってみた"
date = "2017-07-14T06:07:00+09:00"
tags = ["deb", "nginx"]
categories = ["blog"]
+++


## はじめに

[Nginxのリバースプロキシでバックエンドとhttp2通信する - ASnoKaze blog](http://asnokaze.hatenablog.com/entry/2017/07/03/083530) で紹介されていたngx_http_v2_upstreamモジュールを組み込んだnginxのdebianパッケージを作ってみたのでメモです。

[git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順](/blog/2017/07/05/how-to-build-deb-with-git-buildpackage/) のdquiltでパッチを適用するところでこの記事とは違うパターンが出てきたので、そこを重点的に書いておきます。

なお、なるべくupstreamに近いものを使いたいので、ベースはUbuntuのパッケージではなく [nginx.org](http://nginx.org/) のパッケージを使います。

[nginx: download](http://nginx.org/en/download.html) のページのPre-Built Packagesにはstable versionとmainline versionの2種類がありますが、 [どのバージョンのnginxを使うべきか？ - 考える人、コードを書く人](http://bokko.hatenablog.com/entry/2014/05/24/220554) を読んで以来私はmainlineを使っています。

今回使用した nginx のバージョンは 1.13.3 で、作業した環境は Ubuntu 16.04 です。

## ソースパッケージのダウンロード

[Pre-Built Packages for Mainline version](http://nginx.org/en/linux_packages.html#mainline) を参考に以下の内容を `/etc/apt/sources.list.d/nginx-org.list` というファイルに保存します。

```text
deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx
deb-src http://nginx.org/packages/mainline/ubuntu/ xenial nginx
```

作業ディレクトリを作って nginx.org で配布しているdebのソースパッケージをダウンロードします。

```console
mkdir -p ~/nginx.org-deb/nginx-1.13.3-deb
cd !$
sudo apt update
sudo apt source nginx
```

ダウンロードされたファイルは以下の通りです。

```console
$ ls -F
nginx-1.13.3/                        nginx_1.13.3-1~xenial.dsc
nginx_1.13.3-1~xenial.debian.tar.xz  nginx_1.13.3.orig.tar.gz
```

## パッチファイルをDEP-3準拠にして保存

`~/nginx.org-deb/ngx_http_v2_upstream-patches` というディレクトリを作り、そこに以下の14個のパッチを保存しました。

* [[PATCH 01 of 14] Output chain: propagate last_buf flag to c->send_chain()](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010209.html)
* [[PATCH 02 of 14] Upstream keepalive: preserve c->data](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010210.html)
* [[PATCH 03 of 14] HTTP/2: add debug logging of control frames](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010211.html)
* [[PATCH 04 of 14] HTTP/2: s/client/peer/](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010212.html)
* [[PATCH 05 of 14] HTTP/2: introduce h2c->conf_ctx](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010213.html)
* [[PATCH 06 of 14] HTTP/2: introduce stream->fake_connection](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010214.html)
* [[PATCH 07 of 14] HTTP/2: introduce ngx_http_v2_handle_event()](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010215.html)
* [[PATCH 08 of 14] HTTP/2: add HTTP/2 to upstreams](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010216.html)
* [[PATCH 09 of 14] Proxy: add "proxy_ssl_alpn" directive](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010217.html)
* [[PATCH 10 of 14] Proxy: always emit "Host" header first](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010218.html)
* [[PATCH 11 of 14] Proxy: split configured header names and values](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010219.html)
* [[PATCH 12 of 14] Proxy: add HTTP/2 support](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010221.html)
* [[PATCH 13 of 14] Proxy: add "proxy_pass_trailers" directive](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010220.html)
* [[PATCH 14 of 14] Cache: add HTTP/2 support](http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010222.html)

[8. Patches to Packages — Ubuntu Packaging Guide](http://packaging.ubuntu.com/html/patches-to-packages.html) でもお勧めされている通り、 パッチは [Debian Enhancement Proposals](http://dep.debian.net/) の [DEP-3: Patch Tagging Guidelines](http://dep.debian.net/deps/dep3/) に準拠した形式にしておきます。

今回は `Subject` 、 `Author` 、 `Description` 、 `Origin` ヘッダを付けるようにしました。

例えば `[PATCH 09 of 14] Proxy: add "proxy_ssl_alpn" directive` は以下のようになっています。

```text
# HG changeset patch
# User Piotr Sikora <piotrsikora at google.com>
# Date 1489621682 25200
#      Wed Mar 15 16:48:02 2017 -0700
# Node ID 96075d4cd2a6e8bd67caf1d7b78f8e87d757c48d
# Parent  154ca6c5e62a1931a616e9f2b99ef2553b7c2c8b
Proxy: add "proxy_ssl_alpn" directive.

ALPN is used here only to indicate which version of the HTTP protocol
is going to be used and we doesn't verify that upstream agreed to it.

Please note that upstream is allowed to reject SSL connection with a
fatal "no_application_protocol" alert if it doesn't support it.

Signed-off-by: Piotr Sikora <piotrsikora at google.com>

diff -r 154ca6c5e62a -r 96075d4cd2a6 src/event/ngx_event_openssl.c
…(略)…
```

これは以下の内容で `~/nginx.org-deb/ngx_http_v2_upstream-patches/` ディレクトリに
`ngx_http_v2_upstream-09-of-14.diff` というファイル名で保存しました。

```text
Subject: Proxy: add "proxy_ssl_alpn" directive
Description: ALPN is used here only to indicate which version of the HTTP protocol
 is going to be used and we doesn't verify that upstream agreed to it.
 .
 Please note that upstream is allowed to reject SSL connection with a
 fatal "no_application_protocol" alert if it doesn't support it.
Author: Piotr Sikora <piotrsikora at google.com>
Origin: http://mailman.nginx.org/pipermail/nginx-devel/2017-June/010217.html

diff -r 154ca6c5e62a -r 96075d4cd2a6 src/event/ngx_event_openssl.c
…(略)…
```

変更内容は以下の通りです。

* 最後の `#` の行の次の行を `Subject` にしました。
* `Signed-off-by` の値を `Author` にしました。実際は ` at ` を `@` に置き換えて保存しています。
* そしてその間の部分を `Description` にしました。継続行はスペース1つでインデントし、空行は ` .` にします。間の部分がない場合は `Description` ヘッダを省略します。
* 最後に上記のパッチのメーリングリストでのアーカイブのURLを `Origin` にしました。 `#` のコメントの先頭行にHG (Mercurial)のchangeset patchと書いてあるので、それの公開URLがあればそちらにしたほうが良いと思いますが、不明なのでこれで良しとしました。

## ソースパッケージをインポートしてgitレポジトリを作成

レポジトリのディレクトリは `~/.ghq/github.com/hnakamur/nginx-deb` にしたいので、その親ディレクトリの `~/.ghq/github.com/hnakamur` に移動してインポートします。

```console
cd ~/.ghq/github.com/hnakamur
gbp import-dsc --pristine-tar ~/nginx.org-deb/nginx-1.13.3-deb/nginx_1.13.3-1~xenial.dsc
```

`~/.ghq/github.com/hnakamur/nginx` ディレクトリが作られるので 
`~/.ghq/github.com/hnakamur/nginx-deb` にリネームしてそこに移動します。

```console
mv nginx nginx-deb
cd !$
```

## dquiltでパッチをインポート

`quilt` の使い方については以下の2つの記事が参考になりました。

* [How to use quilt to manage patches in Debian packages](https://raphaelhertzog.com/2012/08/08/how-to-use-quilt-to-manage-patches-in-debian-packages/)
* [www.geocities.jp/xsybr354/debian/devel-notes/quilt.txt](http://www.geocities.jp/xsybr354/debian/devel-notes/quilt.txt)

「git-buildpackageでdebパッケージをビルドしてPPAにアップロードする手順」の記事で書いたように `dquilt` というエイリアスを登録していますので、 `quilt` の代わりに `dquilt` を使って同様に実行していきます。

以下のコマンドで14個のパッチをインポートします。パッチはスタックとして管理されるので14番のパッチから1番のパッチへと逆順にインポートしています。

```console
$ for i in {14..01}; do dquilt import ~/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-$i-of-14.diff; done
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-14-of-14.diff (stored as ngx_http_v2_upstream-14-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-13-of-14.diff (stored as ngx_http_v2_upstream-13-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-12-of-14.diff (stored as ngx_http_v2_upstream-12-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-11-of-14.diff (stored as ngx_http_v2_upstream-11-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-10-of-14.diff (stored as ngx_http_v2_upstream-10-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-09-of-14.diff (stored as ngx_http_v2_upstream-09-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-08-of-14.diff (stored as ngx_http_v2_upstream-08-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-07-of-14.diff (stored as ngx_http_v2_upstream-07-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-06-of-14.diff (stored as ngx_http_v2_upstream-06-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-05-of-14.diff (stored as ngx_http_v2_upstream-05-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-04-of-14.diff (stored as ngx_http_v2_upstream-04-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-03-of-14.diff (stored as ngx_http_v2_upstream-03-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-02-of-14.diff (stored as ngx_http_v2_upstream-02-of-14.diff)
Importing patch /home/hnakamur/nginx.org-deb/ngx_http_v2_upstream-patches/ngx_http_v2_upstream-01-of-14.diff (stored as ngx_http_v2_upstream-01-of-14.diff)
```

`debian/patches/` ディレクトリを `ls` で見るとパッチファイルと `series` ファイルが作られています。

```console
$ ls debian/patches/
ngx_http_v2_upstream-01-of-14.diff  ngx_http_v2_upstream-06-of-14.diff  ngx_http_v2_upstream-11-of-14.diff
ngx_http_v2_upstream-02-of-14.diff  ngx_http_v2_upstream-07-of-14.diff  ngx_http_v2_upstream-12-of-14.diff
ngx_http_v2_upstream-03-of-14.diff  ngx_http_v2_upstream-08-of-14.diff  ngx_http_v2_upstream-13-of-14.diff
ngx_http_v2_upstream-04-of-14.diff  ngx_http_v2_upstream-09-of-14.diff  ngx_http_v2_upstream-14-of-14.diff
ngx_http_v2_upstream-05-of-14.diff  ngx_http_v2_upstream-10-of-14.diff  series
```

`dquilt series` コマンドを実行して今取り込んだパッチが1番から14番の順に表示されることを確認します。

```console
$ dquilt series
ngx_http_v2_upstream-01-of-14.diff
ngx_http_v2_upstream-02-of-14.diff
ngx_http_v2_upstream-03-of-14.diff
ngx_http_v2_upstream-04-of-14.diff
ngx_http_v2_upstream-05-of-14.diff
ngx_http_v2_upstream-06-of-14.diff
ngx_http_v2_upstream-07-of-14.diff
ngx_http_v2_upstream-08-of-14.diff
ngx_http_v2_upstream-09-of-14.diff
ngx_http_v2_upstream-10-of-14.diff
ngx_http_v2_upstream-11-of-14.diff
ngx_http_v2_upstream-12-of-14.diff
ngx_http_v2_upstream-13-of-14.diff
ngx_http_v2_upstream-14-of-14.diff
```

なお、ここで逆順になってしまっても、少なくともこの時点であれば `debian/patches/series` を編集して順序を入れ替えれば大丈夫でした。一部のパッチを適用した後は試してないです。

`dquilt next` で次のパッチが1番目のパッチであることを確認して、 `dquilt push` でパッチを適用します。

```console
$ dquilt next
ngx_http_v2_upstream-01-of-14.diff
$ dquilt push
Applying patch ngx_http_v2_upstream-01-of-14.diff
patching file src/core/ngx_output_chain.c

Now at patch ngx_http_v2_upstream-01-of-14.diff
```

gitレポジトリの状態を確認します。ここでは省略しますが `git diff` で差分も見てみました。

```console
$ git status -sb
## master
 M src/core/ngx_output_chain.c
 ?? .pc/
 ?? debian/patches/
```

`.pc/` ディレクトリにはパッチの適用状況が管理されています。前回の記事では適用後は消すようにしていましたが、消すと `dquilt applied` で適用状態を確認したりできなくなることがわかったので今回は残しておくことにしました。この記事では省略しますが、パッチを1つずつ適用するたびに中を見ていくとパッチごとのディレクトリが作られて状態を管理していることがわかります。

同様にして順次パッチを適用していきます。

8番目のパッチを適用しようとすると一部当たらずエラーになりました。

```console
$ dquilt next
ngx_http_v2_upstream-08-of-14.diff
$ dquilt push
Applying patch ngx_http_v2_upstream-08-of-14.diff
patching file auto/modules
patching file src/core/ngx_connection.h
patching file src/http/ngx_http_upstream.c
Hunk #2 succeeded at 190 (offset 2 lines).
Hunk #3 succeeded at 1523 (offset 7 lines).
Hunk #4 succeeded at 1558 (offset 7 lines).
Hunk #5 succeeded at 1626 (offset 7 lines).
Hunk #6 succeeded at 1649 (offset 7 lines).
Hunk #7 FAILED at 1742.
Hunk #8 succeeded at 1878 (offset 15 lines).
Hunk #9 succeeded at 2017 (offset 15 lines).
Hunk #10 succeeded at 2219 (offset 15 lines).
Hunk #11 succeeded at 2282 (offset 15 lines).
Hunk #12 succeeded at 2400 (offset 15 lines).
Hunk #13 succeeded at 2436 (offset 15 lines).
Hunk #14 succeeded at 2684 (offset 15 lines).
Hunk #15 succeeded at 4192 (offset 15 lines).
Hunk #16 succeeded at 4373 (offset 15 lines).
1 out of 16 hunks FAILED -- rejects in file src/http/ngx_http_upstream.c
patching file src/http/ngx_http_upstream.h
patching file src/http/v2/ngx_http_v2.c
patching file src/http/v2/ngx_http_v2.h
patching file src/http/v2/ngx_http_v2_filter_module.c
patching file src/http/v2/ngx_http_v2_module.c
patching file src/http/v2/ngx_http_v2_upstream.c
Patch ngx_http_v2_upstream-08-of-14.diff does not apply (enforce with -f)
```

メッセージの最後に書かれているように `-f` をつけて `dquilt push -f` を実行して強制的に適用します。

```console
$ dquilt push -f
Applying patch ngx_http_v2_upstream-08-of-14.diff
patching file auto/modules
patching file src/core/ngx_connection.h
patching file src/http/ngx_http_upstream.c
Hunk #2 succeeded at 190 (offset 2 lines).
Hunk #3 succeeded at 1523 (offset 7 lines).
Hunk #4 succeeded at 1558 (offset 7 lines).
Hunk #5 succeeded at 1626 (offset 7 lines).
Hunk #6 succeeded at 1649 (offset 7 lines).
Hunk #7 FAILED at 1742.
Hunk #8 succeeded at 1878 (offset 15 lines).
Hunk #9 succeeded at 2017 (offset 15 lines).
Hunk #10 succeeded at 2219 (offset 15 lines).
Hunk #11 succeeded at 2282 (offset 15 lines).
Hunk #12 succeeded at 2400 (offset 15 lines).
Hunk #13 succeeded at 2436 (offset 15 lines).
Hunk #14 succeeded at 2684 (offset 15 lines).
Hunk #15 succeeded at 4192 (offset 15 lines).
Hunk #16 succeeded at 4373 (offset 15 lines).
1 out of 16 hunks FAILED -- saving rejects to file src/http/ngx_http_upstream.c.rej
patching file src/http/ngx_http_upstream.h
patching file src/http/v2/ngx_http_v2.c
patching file src/http/v2/ngx_http_v2.h
patching file src/http/v2/ngx_http_v2_filter_module.c
patching file src/http/v2/ngx_http_v2_module.c
patching file src/http/v2/ngx_http_v2_upstream.c
Applied patch ngx_http_v2_upstream-08-of-14.diff (forced; needs refresh)
```

`src/http/ngx_http_upstream.c.rej` を確認すると以下のような内容でした。

```text
--- src/http/ngx_http_upstream.c
+++ src/http/ngx_http_upstream.c
@@ -1742,6 +1775,16 @@ ngx_http_upstream_ssl_handshake(ngx_conn
		 c->write->handler = ngx_http_upstream_handler;
		 c->read->handler = ngx_http_upstream_handler;

+#if (NGX_HTTP_V2)
+
+        if (u->http2 && u->stream == NULL) {
+            if (ngx_http_upstream_v2_init_connection(r, u, c) != NGX_OK) {
+                return;
+            }
+        }
+
+#endif
+
		 c = r->connection;

		 ngx_http_upstream_send_request(r, u, 1);
```

`src/http/ngx_http_upstream.c` の1742行付近を見た感じ、1769行目の前に入れればよさそうな雰囲気です。

```text {linenos=table,linenostart=1736}
static void
ngx_http_upstream_ssl_handshake(ngx_http_request_t *r, ngx_http_upstream_t *u,
	ngx_connection_t *c)
{
	long  rc;

	if (c->ssl->handshaked) {

		if (u->conf->ssl_verify) {
			rc = SSL_get_verify_result(c->ssl->connection);

			if (rc != X509_V_OK) {
				ngx_log_error(NGX_LOG_ERR, c->log, 0,
							  "upstream SSL certificate verify error: (%l:%s)",
							  rc, X509_verify_cert_error_string(rc));
				goto failed;
			}

			if (ngx_ssl_check_host(c, &u->ssl_name) != NGX_OK) {
				ngx_log_error(NGX_LOG_ERR, c->log, 0,
							  "upstream SSL certificate does not match \"%V\"",
							  &u->ssl_name);
				goto failed;
			}
		}

		if (u->conf->ssl_session_reuse) {
			u->peer.save_session(&u->peer, u->peer.data);
		}

		c->write->handler = ngx_http_upstream_handler;
		c->read->handler = ngx_http_upstream_handler;

		ngx_http_upstream_send_request(r, u, 1);

		return;
	}

	if (c->write->timedout) {
		ngx_http_upstream_next(r, u, NGX_HTTP_UPSTREAM_FT_TIMEOUT);
		return;
	}

failed:

	ngx_http_upstream_next(r, u, NGX_HTTP_UPSTREAM_FT_ERROR);
}
```

編集後、 `dquilt refresh` でパッチを更新します。

```console
$ dquilt refresh
Refreshed patch ngx_http_v2_upstream-08-of-14.diff
```

11番目のパッチは全く当たりませんでした。

```console
$ dquilt push
Applying patch ngx_http_v2_upstream-11-of-14.diff
patching file src/http/modules/ngx_http_proxy_module.c
Hunk #1 FAILED at 1151.
Hunk #2 FAILED at 1265.
Hunk #3 FAILED at 1369.
Hunk #4 FAILED at 3528.
4 out of 4 hunks FAILED -- rejects in file src/http/modules/ngx_http_proxy_module.c
```

`-f` を付けて再実行し強制的に適用します。

```console
$ dquilt push -f
Applying patch ngx_http_v2_upstream-11-of-14.diff
patching file src/http/modules/ngx_http_proxy_module.c
Hunk #1 FAILED at 1151.
Hunk #2 FAILED at 1265.
Hunk #3 FAILED at 1369.
Hunk #4 FAILED at 3528.
4 out of 4 hunks FAILED -- saving rejects to file src/http/modules/ngx_http_proxy_module.c.rej
Applied patch ngx_http_v2_upstream-11-of-14.diff (forced; needs refresh)

	Patch ngx_http_v2_upstream-11-of-14.diff does not apply (enforce with -f)
```

`src/http/modules/ngx_http_proxy_module.c.rej` と `src/http/modules/ngx_http_proxy_module.c` を見比べてみると、多少変更されていますがパッチが当たらなかった内容と等価なものは全て含まれていました。

おそらくコードに変更を加えた上で別途既に取り込まれていたようです。

ということで11番目のパッチは削除します。


```console
$ dquilt delete -r debian/patches/ngx_http_v2_upstream-11-of-14.d
iff
Removing patch ngx_http_v2_upstream-11-of-14.diff
Now at patch ngx_http_v2_upstream-10-of-14.diff
Removed patch ngx_http_v2_upstream-11-of-14.diff
```

12番目のパッチを適用します。　

```console
$ dquilt next
ngx_http_v2_upstream-12-of-14.diff
$ dquilt push
Applying patch ngx_http_v2_upstream-12-of-14.diff
patching file src/http/modules/ngx_http_proxy_module.c
patching file src/http/v2/ngx_http_v2.h
patching file src/http/v2/ngx_http_v2_filter_module.c

Now at patch ngx_http_v2_upstream-12-of-14.diff
```

あとは同様にして最後の14番目のパッチまで適用しました。

gitレポジトリの状態は以下のようになっていました。

```console
$ git status -sb
## master
 M auto/modules
 M src/core/ngx_connection.h
 M src/core/ngx_output_chain.c
 M src/event/ngx_event_openssl.c
 M src/event/ngx_event_openssl.h
 M src/http/modules/ngx_http_fastcgi_module.c
 M src/http/modules/ngx_http_memcached_module.c
 M src/http/modules/ngx_http_proxy_module.c
 M src/http/modules/ngx_http_scgi_module.c
 M src/http/modules/ngx_http_ssl_module.c
 M src/http/modules/ngx_http_upstream_keepalive_module.c
 M src/http/modules/ngx_http_uwsgi_module.c
 M src/http/ngx_http.h
 M src/http/ngx_http_cache.h
 M src/http/ngx_http_file_cache.c
 M src/http/ngx_http_upstream.c
 M src/http/ngx_http_upstream.h
 M src/http/v2/ngx_http_v2.c
 M src/http/v2/ngx_http_v2.h
 M src/http/v2/ngx_http_v2_filter_module.c
 M src/http/v2/ngx_http_v2_module.c
 M src/http/v2/ngx_http_v2_table.c
?? .pc/
?? debian/patches/
?? src/http/modules/ngx_http_proxy_module.c.rej
?? src/http/ngx_http_upstream.c.rej
?? src/http/v2/ngx_http_v2_upstream.c
```

`*.rej` ファイルは削除してから、コミットします。

```console
$ find . -name '*.rej' -exec rm {} \;
$ git add .
$ git commit -m 'Apply ngx_http_v2_upstream patches'
```

## debian/changelogの編集

以下のコマンドを実行して `debian/changelog` を編集します。

```console
$ gbp dch --release
```

エディタが起動されて、ファイルの先頭は以下のようになっていました。

```text
nginx (1.13.3-1~xenialubuntu1) xenial; urgency=medium

  * Apply ngx_http_v2_upstream patches

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Fri, 14 Jul 2017 09:35:07 +0900

nginx (1.13.3-1~xenial) xenial; urgency=low
```

バージョンで `xenial` と `ubuntu1` がくっついているのは良くないのと、公式パッケージではなくPPAなので、
バージョンを `1.13.3-1~xenial1ppa1` を書き換えて保存してエディタを終了しました。

gitレポジトリの状態を確認し、 `debian/changelog` をコミットします。

```console
$ git status -sb
## master
 M debian/changelog
```

.. code-block:: console

	$ git commit -m 'Release 1.13.3-1~xenial1ppa1' debian/changelog

## ソースパッケージのビルド

ソースパッケージのビルドですが、今回はupstreamのソースに対してdfsg対応の修正は加えておらずそのままなので `--git-pristine-tar-commit` オプションは指定せず以下のコマンドを実行します。

```console
gbp buildpackage --git-export-dir=../build-area -S -sa
```

gpgのパスフレーズを2回聞かれるので入力します。

## バイナリパッケージのビルド

以下のコマンドでバイナリパッケージをビルドします。

```console
sudo pbuilder build ../build-area/nginx_1.13.3-1~xenial1ppa1.dsc
```

## gitのタグ作成

ビルドしたバイナリパッケージを壊しても良いコンテナなどにインストールして動作確認が取れたらgitのタグを打っておきます。

debのバージョンに `~` が入っていますが、gitのタグに `~` は使えないだろうからどうしようかと思って、今のタグを見ると `~` は `_` で置き換えていました。

```console
$ git tag
debian/1.13.3-1_xenial
upstream/1.13.3
```

ということで以下のようにタグを打っておきました。

```console
$ git tag debian/1.13.3-1_xenial1ppa1
