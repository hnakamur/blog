---
title: "Linuxのkernel TLSでnginxのSSL_sendfileを試してみた"
date: 2021-10-31T01:10:06+09:00
---

## はじめに
[OpenSSLのSSL_sendfileとパッチを当てたnginxでLinuxのkTLSを試してみた · hnakamur's blog](/blog/2020/04/29/tried-ssl_sendfile-with-openssl-and-nginx/) を書いてから1年半経って状況が変わっていたので再度試してみました。

9日前に [SSL: SSL_sendfile() support with kernel TLS. · nginx/nginx@1fc61b7](https://github.com/nginx/nginx/commit/1fc61b7b1ff182e86078200a59d3c523419c7b3b) で Linux の kernel TLS を使って sendfile するコードが nginx に入っていました。

コミットメッセージによると enable-tls オプションを有効にした OpenSSL 3.0 が必要とのことです。

## 検証環境

```
$ cat /etc/os-release | grep ^VERSION=
VERSION="20.04.3 LTS (Focal Fossa)"
$ uname -r
5.11.0-38-generic
$ uname -m
x86_64
```

Docker を使った検証手順を https://github.com/hnakamur/ktls_sendfile_experiment に置きました。
以下の手順でビルドします。

```bash
git clone https://github.com/hnakamur/ktls_sendfile_experiment
cd ktls_sendfile_experiment
docker build -t tks_sendfile .
```

手順の詳細は [Dockerfile](https://github.com/hnakamur/ktls_sendfile_experiment/blob/f99569f9b7a3230df5c5e773813afc7e86e619e1/Dockerfile) を参照してください。

OpenSSL はこの記事を書いた時の最新のコミット
[Remove redundant RAND_get0_private() call · openssl/openssl@a87c324](https://github.com/openssl/openssl/commit/a87c3247ca641f2593391bf44d47e3dccc7f8d73)
にデバッグログを追加した
[Use fprintf for debug log · hnakamur/openssl@4194d73](https://github.com/hnakamur/openssl/commit/4194d733bb52a76940aa96b25a5ea062c2d05951) のコミットを使用しています。

nginx も同様に最新のコミット
[Core: removed unnecessary restriction in hash initialization. · nginx/nginx@3253b34](https://github.com/nginx/nginx/commit/3253b346fb8b067d68a79ae72e08a376f234b0b3)
にデバッグログを追加した
[Add debug log for BIO_get_ktls_send · hnakamur/nginx@2499956](https://github.com/hnakamur/nginx/commit/2499956347b088e7f4f6ee761b86a705eb68417e) のコミットを使用しています。

## OpenSSL の ktls_sendfile のテスト実行

以下のコマンドで実行できます。

```bash
docker run --rm -it ktls_sendfile test_sslapi.sh
```

デバッグログ出力の抜粋を以下に示します。

```
DEBUG_KTLS: after create_ssl_objects2, serverssl=0x563af62a1740, clientssl=0x563af62a3500, clientssl->options=0x120000
DEBUG_KTLS: SSL_set_options(serverssl, SSL_OP_ENABLE_KTLS) OK, serverssl->options=0x120108, SSL_OP_ENABLE_KTLS=0x8, serverssl=0x563af62a1740.
DEBUG_KTLS: Skip ktls for s=0x563af62a3500 because compressed or ktls disabled, s->compress=(nil), s->options=0x120000, disabled=1.
DEBUG_KTLS: s=0x563af62a3500 after s->statem.enc_write_state = ENC_WRITE_STATE_VALID.
DEBUG_KTLS: calling BIO_set_ktls s=0x563af62a1740, which=0x21, SSL3_CC_WRITE=0x2, which & SSL3_CC_WRITE=0x0
DEBUG_KTLS: s=0x563af62a1740 BIO_set_ktls(bio, &crypto_info, which & SSL3_CC_WRITE) returned true, which=0x21, SSL3_CC_WRITE=0x2, which & SSL3_CC_WRITE=0x0
DEBUG_KTLS: s=0x563af62a1740 after s->statem.enc_write_state = ENC_WRITE_STATE_VALID.
DEBUG_KTLS: calling BIO_set_ktls s=0x563af62a1740, which=0x22, SSL3_CC_WRITE=0x2, which & SSL3_CC_WRITE=0x2
DEBUG_KTLS: s=0x563af62a1740 BIO_set_ktls(bio, &crypto_info, which & SSL3_CC_WRITE) returned true, which=0x22, SSL3_CC_WRITE=0x2, which & SSL3_CC_WRITE=0x2
DEBUG_KTLS: s=0x563af62a1740 after s->statem.enc_write_state = ENC_WRITE_STATE_VALID.
DEBUG_KTLS: Skip ktls for s=0x563af62a3500 because compressed or ktls disabled, s->compress=(nil), s->options=0x120000, disabled=1.
DEBUG_KTLS: s=0x563af62a3500 after s->statem.enc_write_state = ENC_WRITE_STATE_VALID.
DEBUG_KTLS: ktls_sendfile ret=16384, s=0x563af62a1740, wfd=5, fd=3, offset=0, size=16384, flags=0
DEBUG_KTLS: ktls_sendfile ret=16384, s=0x563af62a1740, wfd=5, fd=3, offset=16384, size=16384, flags=0
DEBUG_KTLS: ktls_sendfile ret=16384, s=0x563af62a1740, wfd=5, fd=3, offset=32768, size=16384, flags=0
DEBUG_KTLS: ktls_sendfile ret=16384, s=0x563af62a1740, wfd=5, fd=3, offset=49152, size=16384, flags=0
```

[execute_test_ktls_sendfile](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/test/sslapitest.c#L1276) 関数内で
[create_ssl_objects2 関数を呼び出して](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/test/sslapitest.c#L1322-L1323) `serverssl` と `clientssl` を作成しています。

その後 [SSL_set_options(serverssl, SSL_OP_ENABLE_KTLS)](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/test/sslapitest.c#L1326) を実行して `serverssl` で KTLS を有効にしています。

[tls1_change_cipher_state](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/ssl/t1_enc.c#L186) 関数内で
[if (s->compress || (s->options & SSL_OP_ENABLE_KTLS) == 0)](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/ssl/t1_enc.c#L437)
という条件判定がありますがで `clientssl` のほうは KTLS を有効にしていないのでその下の `goto skip_ktls;` で
[skip_tls:](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/ssl/t1_enc.c#L507) ラベルに飛びます。

serverssl のほうは
[BIO_set_ktls](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/ssl/t1_enc.c#L501) を呼び出しています。

その後
[SSL_sendfile 関数](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/ssl/ssl_lib.c#L2049) 内で
[ret = ktls_sendfile(SSL_get_wfd(s), fd, offset, size, flags);](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/ssl/ssl_lib.c#L2096) として `ktls_sendfile` 関数を呼んでいます。

`ktls_sendfile` は Linux 用の実装が [include/internal/ktls.h#L332-L335](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/include/internal/ktls.h#L332-L335)、FreeBSD用の実装が [include/internal/ktls.h#L188-L198](https://github.com/openssl/openssl/blob/a87c3247ca641f2593391bf44d47e3dccc7f8d73/include/internal/ktls.h#L188-L198) にあります。
どちらもほぼ OS の sendfile を呼んでいるだけです。 Linux と FreeBSD でインタフェースを合わせるためにラップしているということのようです。 Linux のほうは frags 引数が無視されるとコメントに書いてありました。


## OpenSSL の s_server と curl での検証

以下のコマンドで `openssl s_server` を起動します。

```bash
docker run --rm -it ktls_sendfile run_s_server.sh
```

[run_s_server.sh](https://github.com/hnakamur/ktls_sendfile_experiment/blob/f99569f9b7a3230df5c5e773813afc7e86e619e1/run_s_server.sh)
では
```
openssl s_server -WWW -cert /work/example.com.crt -key /work/example.com.key -accept 443 -ktls -sendfile
```
のように起動しています。

別の端末を開いて以下のように curl を実行します。

```bash
docker exec -it $(docker ps -q) curl -sSkv -o /dev/null https://localhost/index.html
```

`openssl s_server` 側の出力は以下のようになり `ktls_sendfile` が呼ばれていることがわかります。
```
Using default temp DH parameters
ACCEPT
FILE:index.html
DEBUG_KTLS: ktls_sendfile ret=615, s=0x56490fd4b870, wfd=4, fd=5, offset=0, size=615, flags=0
KTLS SENDFILE 'index.html' OK
```

curl の出力には以下の行があり、 TLSv1.3 で接続したことがわかります。

```
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
```

## nginx と curl での検証

以下のコマンドで nginx を起動します。

```bash
docker run --rm -it ktls_sendfile
```

nginx のコマンドラインは
[Dockerfile](https://github.com/hnakamur/ktls_sendfile_experiment/blob/f99569f9b7a3230df5c5e773813afc7e86e619e1/Dockerfile) 内の [CMD の行](https://github.com/hnakamur/ktls_sendfile_experiment/blob/f99569f9b7a3230df5c5e773813afc7e86e619e1/Dockerfile#L32) で指定していて、シェルからの実行形式だと
```
/usr/local/nginx/sbin/nginx -g 'daemon off;'
```
です。

別の端末を開いて以下のように curl を実行します。

```bash
docker exec -it $(docker ps -q) curl -sSkv -o /dev/null https://localhost
```

nginx の標準エラー出力の抜粋を以下に示します。
nginx と OpenSSL に追加したデバッグログで nginx 側の `BIO_get_ktls_send` 関数呼び出しで OpenSSL 側では `ktls_sendfile` が呼ばれていることが確認できました。

```
2021/10/30 17:07:06 [notice] 7#0: *1 ngx_ssl_handshake: calling BIO_get_ktls_send() while SSL handshaking, client: 127.0.0.1, server: 0.0.0.0:443
2021/10/30 17:07:06 [notice] 7#0: *1 ngx_ssl_handshake: BIO_get_ktls_send(): 1 while SSL handshaking, client: 127.0.0.1, server: 0.0.0.0:443
DEBUG_KTLS: ktls_sendfile ret=615, s=0x55ef95f596c0, wfd=3, fd=10, offset=0, size=615, flags=0
```

また curl の出力には以下の行があり TLSv1.3 で接続したことがわかります。

```
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
```
