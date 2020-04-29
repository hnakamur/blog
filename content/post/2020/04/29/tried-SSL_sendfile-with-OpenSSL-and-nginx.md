---
title: "OpenSSLのSSL_sendfileとパッチを当てたnginxでLinuxのkTLSを試してみた"
date: 2020-04-29T17:51:58+09:00
---

## 試したきっかけ

[Can a Rust web server beat nginx in serving static files? : rust](https://www.reddit.com/r/rust/comments/a82w9b/can_a_rust_web_server_beat_nginx_in_serving/#ec7ul6t) に以下のようなコメントがありました。

* nginx は sendfile を使っているが TLS では使えない。
* Netflix は FreeBSD カーネルにパッチを当てて暗号化した内容を sendfile で送っている。

余談ですが [Suboptimal block sizes · Issue #3 · seanmonstar/futures-fs](https://github.com/seanmonstar/futures-fs/issues/3) と [The lack of a zero-copy sendfile for ZFS is one of several reasons that we (Netf... | Hacker News](https://news.ycombinator.com/item?id=19698930) を見ると ZFS では sendfile が使えないそうで、 Netflix ではこれが ZFS ではなく UFS を使っている理由の 1 つだそうです。

Linux にも [kTLS](https://www.kernel.org/doc/html/latest/networking/tls-offload.html) があるけどどうなんだろうと検索してみると nginx へのパッチを見つけました。

* [\[PATCH\] Add support for using sendfile when openssl support ktls](https://forum.nginx.org/read.php?29,283706) (2019-04-10)
* [\[PATCH\] when we need to transfer data between file and socket we prefer to use sendfile instead of write because we save the copy to a buffer](https://forum.nginx.org/read.php?29,283833,283833#msg-283833) (2019-04-18)

最初のパッチにコメントを受けて改善されたのが 2 番目のパッチです。が、さらにコメントを受けて対応されずそのままになっていました。

上のパッチでは OpenSSL の
[SSL_sendfile](https://www.openssl.org/docs/manmaster/man3/SSL_sendfile.html)
という関数を使っています。
ページ下部の HISTORY に OpenSSL 3.0.0 で追加されたと書いてあります。
これはドキュメントが先行していますが、実際は 3.0.0-alpha1 が 2020-04-23 に出たところです。 [OpenSSL 3.0 Alpha1 Release - OpenSSL Blog](https://www.openssl.org/blog/blog/2020/04/23/OpenSSL3.0Alpha1/) 。
タグは打たれてないのですが [Prepare for release of 3.0 alpha 1 · openssl/openssl@05feb0a](https://github.com/openssl/openssl/commit/05feb0a0f1fecb6839888bb7590fb92be70d8d3c) のコミットが 3.0.0-alpha1 に対応します。

[openssl/ssl/ssl_lib.c at master · openssl/openssl](https://github.com/openssl/openssl/blame/master/ssl/ssl_lib.c#L2030) を見ると `SSL_sendfile` は 13 か月前に追加されてから変更は入っていません。追加されたのは [ssl: Add SSL_sendfile · openssl/openssl@7c3a756](https://github.com/openssl/openssl/commit/7c3a7561b536264b282f604efc959edad18807d7) のコミットでこれは 2019-04-13 でした。

上に貼ったパッチはこのコミット前後に作られていたんですね、早い。

ということで、今回は上記の 2 つ目のパッチを nginx に組み込んで試してみました。

わけもわからない状態から試行錯誤したのですが、全部書くとごちゃごちゃになるのである程度絞って書きます（自分用にはできれば試行錯誤の際に知ったことも記録しておきたいのですが、記事がごちゃごちゃしすぎるので省略）。

試行錯誤の結果、以下の 3 ステップで確認するのが良いことが分かったのでその順に書いていきます。

* OpenSSL 同梱のテストコードでの動作確認
* `openssl s_server` と `curl` での動作確認
* パッチを当てた `nginx` と `curl` での動作確認

## 検証環境

今回上記以外でもう一つ非常に参考にさせていただいた記事が
[Playing with kernel TLS in Linux 4.13 and Go](https://blog.filippo.io/playing-with-kernel-tls-in-linux-4-13-and-go/)
です。これによると Linux カーネル 4.13 以降なら kTLS が使えるらしいです。

私は今回以下の 2 つの環境で試しましたが、うまく動いたのは後者のみでした（前者で動かない原因は未調査）。

* Ubuntu 18.04 LTS + linux-image-generic-hwe-18.04 5.3.0.46.102
* Ubuntu 20.04 LTS + linux-image-unsigned-5.6.0-050600-generic 5.6.0-050600.202003292333

まずカーネルの tls モジュールがロードされているか確認します。

```console
lsmod | grep tls
```

出力が空の場合は以下のコマンドを実行してロードします。

```console
sudo modprobe tls
```

試行錯誤の時点では物理サーバーで試していましたが、この記事を書くために一から再検証する際は docker を使いました。

[Install Docker Engine on Ubuntu | Docker Documentation](https://docs.docker.com/engine/install/ubuntu/#os-requirements) の手順を試しましたが focal 用のレポジトリはまだないようでした。
[Install Docker Engine from binaries | Docker Documentation](https://docs.docker.com/engine/install/binaries/) から [Index of linux/static/stable/x86_64/](https://download.docker.com/linux/static/stable/x86_64/) を見ると upstream の最新版は 2020-04-29 時点で 19.0.3.8 ですが、 focal の Ubuntu の標準レポジトリでも同じバージョンが入るので、今回はそれを使いました。

```console
sudo apt install -y docker.io
```

## OpenSSL 同梱のテストコードでの動作確認

まず OpenSSL をビルドして
[test/sslapitest.c](https://github.com/openssl/openssl/blob/5e427a435b3b1db0fb0626b26e031f71bde65f7a/test/sslapitest.c) 内の
[test_ktls_sendfile](https://github.com/openssl/openssl/blob/5e427a435b3b1db0fb0626b26e031f71bde65f7a/test/sslapitest.c#L1070-L1169)
のテストを実行してみます。

ただそのまま実行しても kTLS が使われたのか確認できなかったので、試行錯誤中は気になるところに `printf` を入れまくって実行しました。

その後 [OpenSSL Tracing API](https://www.openssl.org/docs/manmaster/man3/OSSL_TRACE.html) というのを見つけたので `printf` の代わりにこちらを使うようにして見ました。 [Add trace category for kTLS · openssl/openssl@09f7dd6](https://github.com/openssl/openssl/commit/09f7dd6a4ffe71277ae114a8aeec4f5fa47c8d9b)

また `test_ktls_sendfile` だけ実行する方法がわからなかったので `test/sslapitest.c` の他のテストをコメントアウトしました。 [Temporarily delete tests other than test_ktls_sendfile · openssl/openssl@63e6ece](https://github.com/openssl/openssl/commit/63e6ecec1279f1afdc4213d13340b7e42593c70c)

この変更を加えた OpenSSL をビルドする手順を Dockerfile より抜粋します。
`./config` の引数に `enable-ktls` と `enable-trace` を指定しています。

```console
git clone https://github.com/hnakamur/openssl \
 && cd openssl \
 && git switch add_trace_category_ktls \
 && ./config enable-ktls enable-trace \
 && make \
 && make install
```

テストを実行するのは以下のようにします。

```console
sudo docker run --rm -it sslsendfile bash -c 'cd /openssl; make tests TESTS=test_sslapi OPENSSL_TRACE=KTLS'
```

実行例です。
TRACE メッセージで `BIO_set_ktls` が成功し、 [ktls_sendfile](https://github.com/openssl/openssl/blob/5e427a435b3b1db0fb0626b26e031f71bde65f7a/include/internal/ktls.h#L264-L271) が呼ばれていることが確認できます。

```console
$ sudo docker run --rm -it sslsendfile bash -c 'cd /openssl; make tests TESTS=test_sslapi NO_FIPS=1 V=1 OPENSSL_TRACE=KTLS'
make depend && make _tests
make[1]: Entering directory '/openssl'
make[1]: Leaving directory '/openssl'
make[1]: Entering directory '/openssl'
( SRCTOP=. \
  BLDTOP=. \
  PERL="/usr/bin/perl" \
  EXE_EXT= \
  /usr/bin/perl ./test/run_tests.pl test_sslapi )
90-test_sslapi.t ..
# The results of this test will end up in test-runs/test_sslapi
1..1
    # Subtest: ../../test/sslapitest
    1..1
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: Calling BIO_set_ktls, s=0x55b9737ac8d0, which=18
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: BIO_set_ktls succeeded, s=0x55b9737ac8d0, which=18
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: Calling BIO_set_ktls, s=0x55b9737aab10, which=33
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: BIO_set_ktls succeeded, s=0x55b9737aab10, which=33
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: Calling BIO_set_ktls, s=0x55b9737aab10, which=34
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: BIO_set_ktls succeeded, s=0x55b9737aab10, which=34
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: Calling BIO_set_ktls, s=0x55b9737ac8d0, which=17
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: BIO_set_ktls succeeded, s=0x55b9737ac8d0, which=17
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: ktls_sendfile ret=16384, s=0x55b9737aab10, wfd=5, fd=3, offset=0, size=16384, flags=0
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: ktls_sendfile ret=16384, s=0x55b9737aab10, wfd=5, fd=3, offset=16384, size=16384, flags=0
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: ktls_sendfile ret=16384, s=0x55b9737aab10, wfd=5, fd=3, offset=32768, size=16384, flags=0
TRACE[80:72:B2:D2:0E:7F:00:00]:KTLS: ktls_sendfile ret=16384, s=0x55b9737aab10, wfd=5, fd=3, offset=49152, size=16384, flags=0
    ok 1 - test_ktls_sendfile
../../util/wrap.pl ../../test/sslapitest ../../test/certs ../../test/recipes/90-test_sslapi_data/passwd.txt /tmp/qTAgg9B5PY default ../../test/default.cnf => 0
ok 1 - running sslapitest
ok
All tests successful.
Files=1, Tests=1,  1 wallclock secs ( 0.03 usr  0.01 sys +  0.66 cusr  0.08 csys =  0.78 CPU)
Result: PASS
make[1]: Leaving directory '/openssl'
```

`Calling BIO_set_ktls` と `BIO_set_ktls succeeded` のメッセージを出力しているのが以下の箇所です。

引用した最後の行に `skip_ktls:` のラベルがありますが、このコードの上のほうに様々な理由で `goto skip_ktls;` で飛んで `BIO_set_ktls` を呼ばないケースがあります。

[ssl/t1_enc.c#L525-L534](https://github.com/hnakamur/openssl/blob/63e6ecec1279f1afdc4213d13340b7e42593c70c/ssl/t1_enc.c#L525-L534)

```c
    /* ktls works with user provided buffers directly */
    OSSL_TRACE2(KTLS, "Calling BIO_set_ktls, s=%p, which=%d\n", s, which);
    if (BIO_set_ktls(bio, &crypto_info, which & SSL3_CC_WRITE)) {
        OSSL_TRACE2(KTLS, "BIO_set_ktls succeeded, s=%p, which=%d\n", s, which);
        if (which & SSL3_CC_WRITE)
            ssl3_release_write_buffer(s);
        SSL_set_options(s, SSL_OP_NO_RENEGOTIATION);
    }

 skip_ktls:
```

そのうち 2 つを以下に引用します。
TLS のバージョンが 1.2 以外だったり cipher が `AES_GCM_128` 以外だと kTLS は使われないことが確認できます。

[ssl/t1_enc.c#L445-L457](https://github.com/hnakamur/openssl/blob/63e6ecec1279f1afdc4213d13340b7e42593c70c/ssl/t1_enc.c#L445-L457)

```console
    /* check that cipher is AES_GCM_128 */
    if (EVP_CIPHER_nid(c) != NID_aes_128_gcm
        || EVP_CIPHER_mode(c) != EVP_CIPH_GCM_MODE
        || EVP_CIPHER_key_length(c) != TLS_CIPHER_AES_GCM_128_KEY_SIZE) {
        OSSL_TRACE2(KTLS, "Skip ktls because of cipher, s=%p, which=%d\n", s, which);
        goto skip_ktls;
    }

    /* check version is 1.2 */
    if (s->version != TLS1_2_VERSION) {
        OSSL_TRACE2(KTLS, "Skip ktls because of TLS version not 1.2, s=%p, which=%d\n", s, which);
        goto skip_ktls;
    }
```

## `openssl s_server` と `curl` での動作確認

### kTLS が使われるケースの検証

まず `openssl s_server` を以下のように起動します。

```console
sudo docker run --rm -it sslsendfile bash -c 'cd /usr/local/nginx/html; OPENSSL_TRACE=KTLS openssl s_server -WWW -cert /usr/local/nginx/conf/example.com.crt -key /usr/local/nginx/conf/example.com.key -accept 443 -no_tls1_3 -sendfile'
```

以下のように出力されたらリクエストを受け付ける準備完了です。

```text
Using default temp DH parameters
ACCEPT
```

別の端末で以下のように curl を実行します。

```console
sudo docker exec -it $(sudo docker ps -q) curl -kv --tlsv1.2 --ciphers AES128-GCM-SHA256 https://localhost/index.html
```

`openssl s_server` の端末には以下のようにトレースメッセージが出力され kTLS が使われたことが分かります。

```text
TRACE[80:82:CD:4F:31:7F:00:00]:KTLS: Calling BIO_set_ktls, s=0x555aa2d09b30, which=33
TRACE[80:82:CD:4F:31:7F:00:00]:KTLS: BIO_set_ktls succeeded, s=0x555aa2d09b30, which=33
TRACE[80:82:CD:4F:31:7F:00:00]:KTLS: Calling BIO_set_ktls, s=0x555aa2d09b30, which=34
TRACE[80:82:CD:4F:31:7F:00:00]:KTLS: BIO_set_ktls succeeded, s=0x555aa2d09b30, which=34
FILE:index.html
TRACE[80:82:CD:4F:31:7F:00:00]:KTLS: ktls_sendfile ret=612, s=0x555aa2d09b30, wfd=4, fd=5, offset=0, size=612, flags=0
KTLS SENDFILE 'index.html' OK
```

curl のほうの端末の出力のうち下記の 1 行で TLSv1.2 と AES128-GCM-SHA256 の cipher が使われたことが確認できます。

```text
* SSL connection using TLSv1.2 / AES128-GCM-SHA256
```

以下のコマンドを実行して Docker コンテナーを終了します。

```console
sudo docker kill $(sudo docker ps -q)
```

### kTLS が使われないケースその1: TLSv1.2 だが cipher が `AES_GCM_128` ではない

まず `openssl s_server` を以下のように起動します。

```console
sudo docker run --rm -it sslsendfile bash -c 'cd /usr/local/nginx/html; OPENSSL_TRACE=KTLS openssl s_server -WWW -cert /usr/local/nginx/conf/example.com.crt -key /usr/local/nginx/conf/example.com.key -accept 443 -no_tls1_3 -sendfile'
```

別端末で curl を以下のように実行します。

```console
sudo docker exec -it $(sudo docker ps -q) curl -kv --tlsv1.2 https://localhost/index.html
```

`openssl s_server` の端末には以下のように出力されました。

```text
TRACE[80:42:EB:65:D1:7F:00:00]:KTLS: Skip ktls because of cipher, s=0x559306cdab30, which=33
TRACE[80:42:EB:65:D1:7F:00:00]:KTLS: Skip ktls because of cipher, s=0x559306cdab30, which=34
FILE:index.html
```

curl の端末には以下のように出力されました。
TLSv1.2 ですが cipher は ECDHE-RSA-AES256-GCM-SHA384 が選ばれています。
また `openssl s_server` は `-sendfile` オプションを指定したのに `ktls_sendfile` が使えないパターンは想定してないようでエラーになってしまっています。

```console
$ sudo docker exec -it $(sudo docker ps -q) curl -kv --tlsv1.2 https://localhost/index.html
*   Trying 127.0.0.1:443...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
* successfully set certificate verify locations:
*   CAfile: /etc/ssl/certs/ca-certificates.crt
  CApath: /etc/ssl/certs
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.2 (IN), TLS handshake, Certificate (11):
* TLSv1.2 (IN), TLS handshake, Server key exchange (12):
* TLSv1.2 (IN), TLS handshake, Server finished (14):
* TLSv1.2 (OUT), TLS handshake, Client key exchange (16):
* TLSv1.2 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.2 (OUT), TLS handshake, Finished (20):
* TLSv1.2 (IN), TLS handshake, Finished (20):
* SSL connection using TLSv1.2 / ECDHE-RSA-AES256-GCM-SHA384
* ALPN, server did not agree to a protocol
* Server certificate:
*  subject: C=JP; ST=Osaka; L=Osaka City; CN=example.com
*  start date: Apr 29 11:47:10 2020 GMT
*  expire date: Apr 29 11:47:10 2021 GMT
*  issuer: C=JP; ST=Osaka; L=Osaka City; CN=example.com
*  SSL certificate verify result: self signed certificate (18), continuing anyway.
> GET /index.html HTTP/1.1
> Host: localhost
> User-Agent: curl/7.68.0
> Accept: */*
>
* Mark bundle as not supporting multiuse
* HTTP 1.0, assume close after body
< HTTP/1.0 200 ok
< Content-type: text/html
<
Error SSL_sendfile 'index.html'
80:42:EB:65:D1:7F:00:00:error:SSL routines:SSL_sendfile:uninitialized:ssl/ssl_lib.c:2046:
```

以下のコマンドを実行して Docker コンテナーを終了します。

```console
sudo docker kill $(sudo docker ps -q)
```

### kTLS が使われないケースその2: TLSv1.3

まず `openssl s_server` を以下のように起動します。

```console
sudo docker run --rm -it sslsendfile bash -c 'cd /usr/local/nginx/html; OPENSSL_TRACE=KTLS openssl s_server -WWW -cert /usr/local/nginx/conf/example.com.crt -key /usr/local/nginx/conf/example.com.key -accept 443 -sendfile'
```

別端末で curl を以下のように実行します。

```console
sudo docker exec -it $(sudo docker ps -q) curl -kv https://localhost/index.html
```

今度は `openssl s_server` の端末にはトレースメッセージは何も表示されず、 curl の端末は以下のような出力になりました。
接続には TLSv1.3 と `TLS_AES_256_GCM_SHA384` の cipher が使われ、今度も `openssl s_server` からエラーが返ってきています。

```console
$ sudo docker exec -it $(sudo docker ps -q) curl -kv https://localhost/index.html
*   Trying 127.0.0.1:443...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
* successfully set certificate verify locations:
*   CAfile: /etc/ssl/certs/ca-certificates.crt
  CApath: /etc/ssl/certs
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.3 (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN, server did not agree to a protocol
* Server certificate:
*  subject: C=JP; ST=Osaka; L=Osaka City; CN=example.com
*  start date: Apr 29 11:47:10 2020 GMT
*  expire date: Apr 29 11:47:10 2021 GMT
*  issuer: C=JP; ST=Osaka; L=Osaka City; CN=example.com
*  SSL certificate verify result: self signed certificate (18), continuing anyway.
> GET /index.html HTTP/1.1
> Host: localhost
> User-Agent: curl/7.68.0
> Accept: */*
>
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
* old SSL session ID is stale, removing
* Mark bundle as not supporting multiuse
* HTTP 1.0, assume close after body
< HTTP/1.0 200 ok
< Content-type: text/html
<
Error SSL_sendfile 'index.html'
80:02:AD:3C:5F:7F:00:00:error:SSL routines:SSL_sendfile:uninitialized:ssl/ssl_lib.c:2046:
* Closing connection 0
* TLSv1.3 (OUT), TLS alert, close notify (256):
```

## パッチを当てた `nginx` と `curl` での動作確認

記事の冒頭に書いたパッチは一か所 if の後を波括弧で囲む修正が必要でした。
また `SSL_sendfile` が使えるかどうかを `auto/configure` で判定するように改善して、パッチにもさらに少し手を入れてみました。

```console
sudo docker run --rm -it sslsendfile /usr/local/nginx/sbin/nginx -g 'daemon off;'
```
