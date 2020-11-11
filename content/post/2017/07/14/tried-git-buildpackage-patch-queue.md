+++
title="git-buildpackageのpatch-queue機能を試してみた"
date = "2017-07-14T11:20:00+09:00"
tags = ["deb", "nginx"]
categories = ["blog"]
+++


## はじめに

[ngx_http_v2_upstreamモジュールを追加したnginxのdebパッケージを作ってみた](/blog/2017/07/14/build-nginx-deb-with-ngx_http_v2_upstream/) で `quilt` を使ったパッチ適用を経験してみて、不慣れなこともありちょっと面倒な気がしました。

そこで、 `git-buildpackage` の `Working with patches](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.patches.html) を試してみることにしました。

前回作業したgitのレポジトリで以下のコミットに戻してから、以下の手順を試しました。

```text
commit a2bfcc9998da58bebd5b5fc7e355cf9a8ff95d60
Author: Konstantin Pavlov <thresh@nginx.com>
Date:   Tue Jul 11 22:06:07 2017

	Imported Debian patch 1.13.3-1~xenial
```

## パッチの準備

上記のページを見ると `debian/patches/` ディレクトリに `git-quiltimport (1)` でパース可能なパッチファイルをおいておく必要があるとのことです。

### hg形式のパッチをgit形式のパッチに変換するスクリプト

今回は元のパッチが `hg (mercurial)` の形式なので、これを変換できないかと検索してみると

[moz-git-tools/hg-patch-to-git-patch at master · mozilla/moz-git-tools](https://github.com/mozilla/moz-git-tools/blob/master/hg-patch-to-git-patch)

というPythonスクリプトが見つかったので、ありがたくこれを使わせていただくことにしました。

私が試したバージョンは以下の通りです。

[moz-git-tools/hg-patch-to-git-patch at d9009081a467ace43c0a8f535089a7c66a22c587 · mozilla/moz-git-tools](https://github.com/mozilla/moz-git-tools/blob/d9009081a467ace43c0a8f535089a7c66a22c587/hg-patch-to-git-patch)

これを `/usr/local/bin/hg-patch-to-git-patch` というファイル名で保存し、実行パーミションをつけておきます。　

### hg形式のパッチを保存

`~/nginx.org-deb/ngx_http_v2_upstream-hg-patches` というディレクトリにhg形式のパッチを保存することにしました。
スパムメール防止用に変換されているメールアドレス内の `at` と前後のスペースを `@` に戻してパッチを保存します。

```console
$ ls
ngx_http_v2_upstream-01-of-14.diff  ngx_http_v2_upstream-06-of-14.diff  ngx_http_v2_upstream-11-of-14.diff
ngx_http_v2_upstream-02-of-14.diff  ngx_http_v2_upstream-07-of-14.diff  ngx_http_v2_upstream-12-of-14.diff
ngx_http_v2_upstream-03-of-14.diff  ngx_http_v2_upstream-08-of-14.diff  ngx_http_v2_upstream-13-of-14.diff
ngx_http_v2_upstream-04-of-14.diff  ngx_http_v2_upstream-09-of-14.diff  ngx_http_v2_upstream-14-of-14.diff
ngx_http_v2_upstream-05-of-14.diff  ngx_http_v2_upstream-10-of-14.diff
```

### git形式のパッチに変換

git形式のパッチを保存するディレクトリ `~/nginx.org-deb/ngx_http_v2_upstream-git-patches` を作成し、上記のスクリプトで変換します。

```console
$ mkdir ../ngx_http_v2_upstream-git-patches
$ for i in *; do hg-patch-to-git-patch $i > ../ngx_http_v2_upstream-git-patches/$i ; done
```

変換後のgit形式のパッチの先頭は以下のようになっていました（メールアドレス内の `@` はスパムメール防止用に `at` ＋前後の空白に置換しています）。

```console
$ head ../ngx_http_v2_upstream-git-patches/ngx_http_v2_upstream-01-of-14.diff
From: Piotr Sikora <piotrsikora at google.com>
Date: 1491708381 -0700
Subject: Output chain: propagate last_buf flag to c->send_chain().

Signed-off-by: Piotr Sikora <piotrsikora at google.com>

diff -r a39bc74873fa -r 5f5d70428655 src/core/ngx_output_chain.c
--- a/src/core/ngx_output_chain.c
+++ b/src/core/ngx_output_chain.c
@@ -658,6 +658,7 @@ ngx_chain_writer(void *data, ngx_chain_t
```

```console
$ head -13 ../ngx_http_v2_upstream-git-patches/ngx_http_v2_upstream-09-of-14.diff
From: Piotr Sikora <piotrsikora at google.com>
Date: 1489621682 -0700
Subject: Proxy: add "proxy_ssl_alpn" directive.

ALPN is used here only to indicate which version of the HTTP protocol
is going to be used and we doesn't verify that upstream agreed to it.

Please note that upstream is allowed to reject SSL connection with a
fatal "no_application_protocol" alert if it doesn't support it.

Signed-off-by: Piotr Sikora <piotrsikora at google.com>

diff -r 154ca6c5e62a -r 96075d4cd2a6 src/event/ngx_event_openssl.c
```

## パッチのインポート

パッチをインポートは前回同様 `dquilt import` で行います。
パッチはスタックとして管理されるので14番のパッチから1番のパッチへと逆順にインポートしています。

```console
$ cd ~/.ghq/github.com/hnakamur/nginx-deb
$ for i in {14..01}; do dquilt import ~/nginx.org-deb/ngx_http_v2_upstream-git-patches/ngx_http_v2_upstream-$i-of-14.diff; done
```

インポートしたパッチをgitに追加してコミットしておきます。

```console
$ git status -sb
## patch-queue/master
?? debian/patches/
$ git add .
$ git status -sb
## patch-queue/master
A  debian/patches/ngx_http_v2_upstream-01-of-14.diff
A  debian/patches/ngx_http_v2_upstream-02-of-14.diff
A  debian/patches/ngx_http_v2_upstream-03-of-14.diff
A  debian/patches/ngx_http_v2_upstream-04-of-14.diff
A  debian/patches/ngx_http_v2_upstream-05-of-14.diff
A  debian/patches/ngx_http_v2_upstream-06-of-14.diff
A  debian/patches/ngx_http_v2_upstream-07-of-14.diff
A  debian/patches/ngx_http_v2_upstream-08-of-14.diff
A  debian/patches/ngx_http_v2_upstream-09-of-14.diff
A  debian/patches/ngx_http_v2_upstream-10-of-14.diff
A  debian/patches/ngx_http_v2_upstream-11-of-14.diff
A  debian/patches/ngx_http_v2_upstream-12-of-14.diff
A  debian/patches/ngx_http_v2_upstream-13-of-14.diff
A  debian/patches/ngx_http_v2_upstream-14-of-14.diff
A  debian/patches/series
$ git commit -m 'Add ngx_http_v2_upstream patches'
```

## パッチの適用

次は `gbp pq import` コマンドを実行します。8番目のパッチが当たらずエラーになりました。

```console
$ gbp pq import
gbp:info: Trying to apply patches at 'a2bfcc9998da58bebd5b5fc7e355cf9a8ff95d60'
gbp:error: Failed to apply 'debian/patches/ngx_http_v2_upstream-08-of-14.diff': Error running git apply: error: patch failed: src/http/ngx_http_upstream.c:1709
error: src/http/ngx_http_upstream.c: patch does not apply

gbp:error: Couldn't apply patches
```

`-v` を付けて再度試してみました。

```console
$ gbp pq import -v
gbp:debug: ['git', 'rev-parse', '--show-cdup']
gbp:debug: ['git', 'rev-parse', '--is-bare-repository']
gbp:debug: ['git', 'symbolic-ref', 'HEAD']
gbp:debug: ['git', 'show-ref', 'refs/heads/master']
gbp:debug: ['git', 'show-ref', 'refs/heads/patch-queue/master']
gbp:debug: ['git', 'log', '--pretty=format:%H', '-1', '--first-parent', '--']
gbp:info: Trying to apply patches at 'a2bfcc9998da58bebd5b5fc7e355cf9a8ff95d60'
gbp:debug: ['git', 'branch', 'patch-queue/master', 'a2bfcc9998da58bebd5b5fc7e355cf9a8ff95d60']
gbp:debug: ['git', 'symbolic-ref', 'HEAD']
gbp:debug: ['git', 'show-ref', 'refs/heads/master']
gbp:debug: ['git', 'checkout', 'patch-queue/master']
gbp:debug: Applying debian/patches/ngx_http_v2_upstream-01-of-14.diff
…(略)…
gbp:debug: ['git', 'apply', '--index', 'debian/patches/ngx_http_v2_upstream-07-of-14.diff']
gbp:debug: ['git', 'write-tree']
gbp:debug: ['git', 'rev-parse', '--quiet', '--verify', 'HEAD']
gbp:debug: ['git', 'commit-tree', '04ca7796412675740f5b1b89f0ca19ad8dd19756', '-p', '43b9919966a4321ec76d9ccdd9921bac449abf8c']
gbp:debug: ['git', 'update-ref', '-m', 'gbp-pq import debian/patches/ngx_http_v2_upstream-07-of-14.diff', 'HEAD', 'd8e3319aac2d07f18f719df074cf21de90482a16']
gbp:debug: Applying debian/patches/ngx_http_v2_upstream-08-of-14.diff
gbp:debug: ['git', 'apply', '--index', 'debian/patches/ngx_http_v2_upstream-08-of-14.diff']
gbp:error: Failed to apply 'debian/patches/ngx_http_v2_upstream-08-of-14.diff': Error running git apply: error: patch failed: src/http/ngx_http_upstream.c:1709
error: src/http/ngx_http_upstream.c: patch does not apply

gbp:debug: ['git', 'rev-parse', '--quiet', '--verify', 'HEAD']
gbp:debug: ['git', 'reset', '--quiet', '--hard', 'd8e3319aac2d07f18f719df074cf21de90482a16', '--']
gbp:debug: ['git', 'symbolic-ref', 'HEAD']
gbp:debug: ['git', 'show-ref', 'refs/heads/patch-queue/master']
gbp:debug: ['git', 'checkout', 'master']
gbp:debug: ['git', 'symbolic-ref', 'HEAD']
gbp:debug: ['git', 'show-ref', 'refs/heads/master']
gbp:debug: ['git', 'branch', '-D', 'patch-queue/master']
gbp:error: Couldn't apply patches
```

`man gbp-pq` すると `apply` サブコマンドで1つずつパッチを当てられるようなので、そちらを試してみました。
`apply` の後に何も指定せずに実行するとパッチ名が無いというエラーになりました。

```console
$ gbp pq apply
gbp:error: No patch name given.
```

ファイル名を指定して実行してみるとうまく動きました。

```console
$ gbp pq apply debian/patches/ngx_http_v2_upstream-01-of-14.diff
gbp:info: Switching to 'patch-queue/master'
gbp:info: Applied ngx_http_v2_upstream-01-of-14.diff
```

gitレポジトリの状態を確認すると `patch-queue/master` ブランチが作られてそこに切り替わっていました。

```console
$ git status -sb
  master
* patch-queue/master
  pristine-tar
  upstream
```

gitのログを確認すると1番目のパッチを取り込んだコミットが作られています。

```console
$ git log
commit bdd197591d9f85f9a2f9c95ce9e38d4557947bce
Author: Piotr Sikora <piotrsikora@google.com>
Date:   Sun Apr 9 12:26:21 2017

	Output chain: propagate last_buf flag to c->send_chain().

	Signed-off-by: Piotr Sikora <piotrsikora@google.com>

commit 2f8475f406a170123a9598b6a0a3a217c66421f3
Author: Hiroaki Nakamura <hnakamur@gmail.com>
Date:   Fri Jul 14 14:50:43 2017

	Add ngx_http_v2_upstream patches

commit a2bfcc9998da58bebd5b5fc7e355cf9a8ff95d60
Author: Konstantin Pavlov <thresh@nginx.com>
Date:   Tue Jul 11 22:06:07 2017

	Imported Debian patch 1.13.3-1~xenial

commit 8483de20a8ef51e65ca23e855c8354ad4193cbe5
Author: Hiroaki Nakamura <hnakamur@gmail.com>
Date:   Fri Jul 14 00:25:32 2017

	Imported Upstream version 1.13.3
```

`git diff HEAD^` を実行すると1番目のパッチと同じ差分になっていました。

同様にして7番目のパッチまで適用します。

```console
$ gbp pq apply debian/patches/ngx_http_v2_upstream-02-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-02-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-03-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-03-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-04-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-04-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-05-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-05-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-06-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-06-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-07-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-07-of-14.diff
```

8番目のパッチはうまく当たらずエラーになるのは同じです。

```console
$ gbp pq apply debian/patches/ngx_http_v2_upstream-08-of-14.diff
gbp:error: Error running git apply: error: patch failed: src/http/ngx_http_upstream.c:1709
error: src/http/ngx_http_upstream.c: patch does not apply
```

`git-buildpackage` の Working with patches のページにはパッチが当たらない場合の手順は書いてないので、試行錯誤してみることにしました。

まず `git am` コマンドでパッチを当てて見ると以下のようになりました。

```console
$ git am debian/patches/ngx_http_v2_upstream-08-of-14.diff
Applying: HTTP/2: add HTTP/2 to upstreams.
error: patch failed: src/http/ngx_http_upstream.c:1709
error: src/http/ngx_http_upstream.c: patch does not apply
Patch failed at 0001 HTTP/2: add HTTP/2 to upstreams.
The copy of the patch that failed is found in: .git/rebase-apply/patch
When you have resolved this problem, run "git am --continue".
If you prefer to skip this patch, run "git am --skip" instead.
To restore the original branch and stop patching, run "git am --abort".
```

`man git-am` を見ると `--reject` オプションがあったので、一旦 `git am --abort` で中断してからこれを試しました。

```console
$ git am --abort
$ git am --reject debian/patches/ngx_http_v2_upstream-08-of-14.diff
Applying: HTTP/2: add HTTP/2 to upstreams.
Checking patch auto/modules...
Checking patch src/core/ngx_connection.h...
Checking patch src/http/ngx_http_upstream.c...
Hunk #2 succeeded at 190 (offset 2 lines).
Hunk #3 succeeded at 1523 (offset 7 lines).
Hunk #4 succeeded at 1558 (offset 7 lines).
Hunk #5 succeeded at 1626 (offset 7 lines).
Hunk #6 succeeded at 1649 (offset 7 lines).
error: while searching for:
		c->write->handler = ngx_http_upstream_handler;
		c->read->handler = ngx_http_upstream_handler;

		c = r->connection;

		ngx_http_upstream_send_request(r, u, 1);

error: patch failed: src/http/ngx_http_upstream.c:1709
Hunk #8 succeeded at 1878 (offset 5 lines).
Hunk #9 succeeded at 2017 (offset 5 lines).
Hunk #10 succeeded at 2219 (offset 5 lines).
Hunk #11 succeeded at 2282 (offset 5 lines).
Hunk #12 succeeded at 2400 (offset 5 lines).
Hunk #13 succeeded at 2436 (offset 5 lines).
Hunk #14 succeeded at 2684 (offset 5 lines).
Hunk #15 succeeded at 4192 (offset 5 lines).
Hunk #16 succeeded at 4373 (offset 5 lines).
Checking patch src/http/ngx_http_upstream.h...
Checking patch src/http/v2/ngx_http_v2.c...
Checking patch src/http/v2/ngx_http_v2.h...
Checking patch src/http/v2/ngx_http_v2_filter_module.c...
Checking patch src/http/v2/ngx_http_v2_module.c...
Checking patch src/http/v2/ngx_http_v2_upstream.c...
Applied patch auto/modules cleanly.
Applied patch src/core/ngx_connection.h cleanly.
Applying patch src/http/ngx_http_upstream.c with 1 reject...
Hunk #1 applied cleanly.
Hunk #2 applied cleanly.
Hunk #3 applied cleanly.
Hunk #4 applied cleanly.
Hunk #5 applied cleanly.
Hunk #6 applied cleanly.
Rejected hunk #7.
Hunk #8 applied cleanly.
Hunk #9 applied cleanly.
Hunk #10 applied cleanly.
Hunk #11 applied cleanly.
Hunk #12 applied cleanly.
Hunk #13 applied cleanly.
Hunk #14 applied cleanly.
Hunk #15 applied cleanly.
Hunk #16 applied cleanly.
Applied patch src/http/ngx_http_upstream.h cleanly.
Applied patch src/http/v2/ngx_http_v2.c cleanly.
Applied patch src/http/v2/ngx_http_v2.h cleanly.
Applied patch src/http/v2/ngx_http_v2_filter_module.c cleanly.
Applied patch src/http/v2/ngx_http_v2_module.c cleanly.
Applied patch src/http/v2/ngx_http_v2_upstream.c cleanly.
Patch failed at 0001 HTTP/2: add HTTP/2 to upstreams.
The copy of the patch that failed is found in: .git/rebase-apply/patch
When you have resolved this problem, run "git am --continue".
If you prefer to skip this patch, run "git am --skip" instead.
To restore the original branch and stop patching, run "git am --abort".
```

gitのレポジトリの状態は以下のようになっていました。

```console
$ git status -sb
## patch-queue/master
 M auto/modules
 M src/core/ngx_connection.h
 M src/http/ngx_http_upstream.c
 M src/http/ngx_http_upstream.h
 M src/http/v2/ngx_http_v2.c
 M src/http/v2/ngx_http_v2.h
 M src/http/v2/ngx_http_v2_filter_module.c
 M src/http/v2/ngx_http_v2_module.c
?? src/http/ngx_http_upstream.c.rej
?? src/http/v2/ngx_http_v2_upstream.c
```

`src/http/ngx_http_upstream.c.rej` を見ながら `src/http/ngx_http_upstream.c` を編集します。

その後 `src/http/ngx_http_upstream.c.rej` は消して `git add` で変更のあったファイルを追加して
`git am --continue` を実行するとパッチが適用できました。

```console
$ rm src/http/ngx_http_upstream.c.rej
$ git add .
$ g am --continue

Applying: HTTP/2: add HTTP/2 to upstreams.
```

ログで最新2つのコミットを見てみると、前のコミットと同様に `Author` や `Date` の内容も正しく設定されているようです。

```console
$ git log -2
commit b2ea482abd9c1cfbd9966316370759bc01095df3
Author: Piotr Sikora <piotrsikora@google.com>
Date:   Wed Mar 29 14:59:40 2017

	HTTP/2: add HTTP/2 to upstreams.

	Signed-off-by: Piotr Sikora <piotrsikora@google.com>

commit 052e2e79cb13eff69bffcfa2cd4bc2bcfdb54fc1
Author: Piotr Sikora <piotrsikora@google.com>
Date:   Fri Mar 10 12:00:45 2017

	HTTP/2: introduce ngx_http_v2_handle_event().

	No functional changes.

	Signed-off-by: Piotr Sikora <piotrsikora@google.com>
```

9番目と10番目のパッチは `gbp pq apply` で適用します。

```console
$ gbp pq apply debian/patches/ngx_http_v2_upstream-09-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-09-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-10-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-10-of-14.diff
```

11番目のパッチは再びエラーになります。

```console
$ gbp pq apply debian/patches/ngx_http_v2_upstream-11-of-14.diff
gbp:error: Error running git apply: error: patch failed: src/http/modules/ngx_http_proxy_module.c:1151
error: src/http/modules/ngx_http_proxy_module.c: patch does not apply
```

`git am --reject` で適用を試みます。

```console
$ git am --reject debian/patches/ngx_http_v2_upstream-11-of-14.diff
```

gitレポジトリの状態を確認します。

```console
$ git status -sb
## patch-queue/master
?? src/http/modules/ngx_http_proxy_module.c.rej
```

前回の記事に書いたように、このパッチと等価な変更が既に適用されているので、このパッチはスキップします。

```console
$ rm src/http/modules/ngx_http_proxy_module.c.rej
$ git am --skip
```

12番目から14番目のパッチは `gbp pq apply` で適用します。

```console
$ gbp pq apply debian/patches/ngx_http_v2_upstream-12-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-12-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-13-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-13-of-14.diff
$ gbp pq apply debian/patches/ngx_http_v2_upstream-14-of-14.diff
gbp:info: Applied ngx_http_v2_upstream-14-of-14.diff
```

## パッチの再生成

上記で作成したコミットの内容からパッチを再生成して `debian/patches/` ディレクトリのファイルを上書き更新してコミットします
。

```console
$ gbp pq export --commit
gbp:info: On 'patch-queue/master', switching to 'master'
gbp:info: Generating patches from git (master..patch-queue/master)
gbp:info: Added patches 0003-HTTP-2-add-debug-logging-of-control-frames.patch, 0011-Proxy-add-HTTP-2-support.patch, 0007-HTTP-2-introduce-ngx_http_v2_handle_event.patch, 0013-Cache-add-HTTP-2-support.patch, 0010-Proxy-always-emit-Host-header-first.patch, 0008-HTTP-2-add-HTTP-2-to-upstreams.patch, 0001-Output-chain-propagate-last_buf-flag-to-c-send_chain.patch, 0004-HTTP-2-s-client-peer.patch, 0009-Proxy-add-proxy_ssl_alpn-directive.patch, 0006-HTTP-2-introduce-stream-fake_connection.patch, 0005-HTTP-2-introduce-h2c-conf_ctx.patch, 0002-Upstream-keepalive-preserve-c-data.patch, 0012-Proxy-add-proxy_pass_trailers-directive.patch to patch series
gbp:info: Removed patches ngx_http_v2_upstream-08-of-14.diff, ngx_http_v2_upstream-13-of-14.diff, ngx_http_v2_upstream-09-of-14.diff, ngx_http_v2_upstream-06-of-14.diff, ngx_http_v2_upstream-03-of-14.diff, ngx_http_v2_upstream-04-of-14.diff, ngx_http_v2_upstream-10-of-14.diff, ngx_http_v2_upstream-12-of-14.diff, ngx_http_v2_upstream-07-of-14.diff, ngx_http_v2_upstream-01-of-14.diff, ngx_http_v2_upstream-05-of-14.diff, ngx_http_v2_upstream-02-of-14.diff, ngx_http_v2_upstream-14-of-14.diff, ngx_http_v2_upstream-11-of-14.diff from patch series
```

gitレポジトリの状態を確認すると、 `master` ブランチに切り替わっていました。

```console
$ git status -sb
## master
```

gitのログを確認すると `patch-queue/master` ブランチはそのままでした。

```console
$ git log -1 patch-queue/master
commit 9e63d82fcbc542cd7fb19bb1facad31998b7d7f8
Author: Piotr Sikora <piotrsikora@google.com>
Date:   Wed Apr 12 08:51:41 2017

	Cache: add HTTP/2 support.

Signed-off-by: Piotr Sikora <piotrsikora@google.com>
```

`master` ブランチには `gbp pq export --commit` によってコミットが作られていました。

```console
$ git log -1 master
commit 359f8e450d47336bc5c798961472c022efd39f1a
Author: Hiroaki Nakamura <hnakamur@gmail.com>
Date:   Fri Jul 14 15:32:49 2017

	Rediff patches

	Added 0003-HTTP-2-add-debug-logging-of-control-frames.patch: <REASON>
	Added 0011-Proxy-add-HTTP-2-support.patch: <REASON>
	Added 0007-HTTP-2-introduce-ngx_http_v2_handle_event.patch: <REASON>
	Added 0013-Cache-add-HTTP-2-support.patch: <REASON>
	Added 0010-Proxy-always-emit-Host-header-first.patch: <REASON>
	Added 0008-HTTP-2-add-HTTP-2-to-upstreams.patch: <REASON>
	Added 0001-Output-chain-propagate-last_buf-flag-to-c-send_chain.patch: <REASON>
	Added 0004-HTTP-2-s-client-peer.patch: <REASON>
	Added 0009-Proxy-add-proxy_ssl_alpn-directive.patch: <REASON>
	Added 0006-HTTP-2-introduce-stream-fake_connection.patch: <REASON>
	Added 0005-HTTP-2-introduce-h2c-conf_ctx.patch: <REASON>
	Added 0002-Upstream-keepalive-preserve-c-data.patch: <REASON>
	Added 0012-Proxy-add-proxy_pass_trailers-directive.patch: <REASON>
	Dropped ngx_http_v2_upstream-08-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-13-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-09-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-06-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-03-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-04-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-10-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-12-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-07-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-01-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-05-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-02-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-14-of-14.diff: <REASON>
	Dropped ngx_http_v2_upstream-11-of-14.diff: <REASON>
```

`debian/patches/` ディレクトリを確認すると、 `<4桁の連番>-<Subject>patch` という形式のファイル名で
パッチファイルが作られていました。

8番目のパッチの中身は上記でパッチが当たらなくて修正した部分が反映されたものになっていました。
また11番目のパッチは削除されてそれ以降のパッチが番号を詰められて作られていました。

```console
$ ls -1 debian/patches/
0001-Output-chain-propagate-last_buf-flag-to-c-send_chain.patch
0002-Upstream-keepalive-preserve-c-data.patch
0003-HTTP-2-add-debug-logging-of-control-frames.patch
0004-HTTP-2-s-client-peer.patch
0005-HTTP-2-introduce-h2c-conf_ctx.patch
0006-HTTP-2-introduce-stream-fake_connection.patch
0007-HTTP-2-introduce-ngx_http_v2_handle_event.patch
0008-HTTP-2-add-HTTP-2-to-upstreams.patch
0009-Proxy-add-proxy_ssl_alpn-directive.patch
0010-Proxy-always-emit-Host-header-first.patch
0011-Proxy-add-HTTP-2-support.patch
0012-Proxy-add-proxy_pass_trailers-directive.patch
0013-Cache-add-HTTP-2-support.patch
series
```

## debian/changelog編集

後は前回と同様です。

まず、 `debian/changelog` を編集します。

```console
$ gbp dch -R
```

エディタで表示される内容の先頭のほうは以下のようになっていました。

```text
nginx (1.13.3-1~xenialubuntu1) xenial; urgency=medium

  * Add ngx_http_v2_upstream patches
  * Rediff patches

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Fri, 14 Jul 2017 16:07:32 +0900

nginx (1.13.3-1~xenial) xenial; urgency=low
```

これを以下のように編集しました。

```text
nginx (1.13.3-1~xenial1ppa1) xenial; urgency=medium

  * Add ngx_http_v2_upstream patches

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Fri, 14 Jul 2017 16:07:32 +0900

nginx (1.13.3-1~xenial) xenial; urgency=low
```

gitレポジトリの状態を確認し、 `debian/changelog` をコミットします。

```console
$ git status -sb
## master
 M debian/changelog
```

```console
$ git commit -m 'Release 1.13.3-1~xenial1ppa1' debian/changelog
```

## ソースパッケージのビルド

ソースパッケージのビルドですが、今回はupstreamのソースに対してdfsg対応の修正は加えておらずそのままなので `--git-pristine-tar-commit` オプションは指定せず以下のコマンドを実行します。

```console
$ gbp buildpackage --git-export-dir=../build-area -S -sa
```

gpgのパスフレーズを2回聞かれるので入力します。

## バイナリパッケージのビルド

以下のコマンドでバイナリパッケージをビルドします。

```console
$ sudo pbuilder build ../build-area/nginx_1.13.3-1~xenial1ppa1.dsc
```

## gitのタグ作成

前回と同じタグなので `-f` を指定して付け替えます。

```console
$ git tag -f debian/1.13.3-1_xenial1ppa1
Updated tag 'debian/1.13.3-1_xenial1ppa1' (was d718489)
```

## upstreamのソースをバージョンアップしたときのパッチ更新

今回は試していませんが、 `git-buildpackage` の Working with patches のページによると
今後upstreamのソースの新しいバージョンを取り込んだときには以下のコマンドでパッチを更新できるようです。

```console
$ gbp pq rebase
$ gbp pq export
```

## おわりに

以前は `git-quiltimport (1)` でパース可能なパッチファイルを作る手順がわかってなかったので
挫折しましたが、そこがわかってしまえば `quilt` コマンドは不慣れで `git` は慣れている私には
こちらのほうが作業しやすそうに感じました。

パッチの適用順序を入れ替えるのも `git rebase` でコミットの順序を入れ替えれば良さそうです。
ということで今後はこちらの方式を主に使うようにしてみます。
