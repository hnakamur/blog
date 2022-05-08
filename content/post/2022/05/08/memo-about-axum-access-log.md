---
title: "Axumでのアクセスログ出力の現状について調べてみた"
date: 2022-05-08T22:10:35+09:00
---

Axumでのアクセスログ出力の現状について調べてみたのでメモです。
個人的には特にヘッダとボディ（新しい用語だとフィールドとコンテント）を合わせた転送量をログに書きたいというニーズがあります。

結論を先に書くと現状は非対応で今のところ予定もないそうです。

## axum でのログ出力の実現方法について調査

[tokio-rs/axum: Ergonomic and modular web framework built with Tokio, Tower, and Hyper](https://github.com/tokio-rs/axum/) の [Getting Help](https://github.com/tokio-rs/axum/#getting-help) で紹介されている Discord での [axumのメインの開発者の davidpdrsn さんの発言](https://discord.com/channels/500028886025895936/870760546109116496/890916692530716682) によると

* axum側でデフォルトのアクセスログを提供する予定はない
* tower-http の TracingLayer の仕組みで作るのがお勧めらしい

とのことでした。

axum の [examples/tracing-aka-logging/src/main.rs](https://github.com/tokio-rs/axum/blob/main/examples/tracing-aka-logging/src/main.rs) を試してみたのですが、 `on_eos` は `End of Stream` ということでこれでレスポンスボディを送り切った最後に呼ばれるのかと思いきや、これは Transfer-Encoding: chunked でかつ最後に trailer のフィールドを送らないと呼ばれなさそうでした（ここはしっかりは確認してないです）。

[Question - getting last byte latency metric with trace layer · Issue #119 · tower-rs/tower-http](https://github.com/tower-rs/tower-http/issues/119) のやり取りを見ても hyper の polling の現状の実装だとにレスポンスの最後で呼ばれるメソッドというのは今後も出来なさそうでした。 [davidpdrsn さんの発言](https://github.com/tower-rs/tower-http/issues/119#issuecomment-900984344) に classifier はレスポンスボディが最後まで送信した後に drop されるというのを使った回避策的なコードが紹介されていました。

でもこの技を使っても [axum/main.rs at main · tokio-rs/axum](https://github.com/tokio-rs/axum/blob/b8514cf1c2cb514949edd2a8c04479f1a7b59e3c/examples/tracing-aka-logging/src/main.rs#L41-L60) の

```
            TraceLayer::new_for_http()
                .on_request(|_request: &Request<_>, _span: &Span| {
                    // ...
                })
                .on_response(|_response: &Response, _latency: Duration, _span: &Span| {
                    // ...
                })
                .on_body_chunk(|_chunk: &Bytes, _latency: Duration, _span: &Span| {
                    // ..
                })
                .on_eos(
                    |_trailers: Option<&HeaderMap>, _stream_duration: Duration, _span: &Span| {
                        // ...
                    },
                )
                .on_failure(
                    |_error: ServerErrorsFailureClass, _latency: Duration, _span: &Span| {
                        // ...
                    },
                ),
```

`on_body_chunk` でボディのチャンクサイズは取れるので合算していくとボディサイズは出せるとしてヘッダサイズは `on_response` の `Response` の `HeaderMap` からエンコード後のサイズを再度計算するのは出来れば避けたいなという印象です。 HTTP のバージョンによってエンコード方法も違いますし。

とりあえず現状では
[Question - getting last byte latency metric with trace layer · Issue #119 · tower-rs/tower-http](https://github.com/tower-rs/tower-http/issues/119) の
[lkts さんのコメント](https://github.com/tower-rs/tower-http/issues/119#issuecomment-901351196) のように Stream をラップして対応するほうが良さそうな気がします。と言いつつ私は具体的な方法が今のところ分かってないです。

## hyper での転送量取得について調査

hyper の tracing 対応について [Meta: Tracing · Issue #2678 · hyperium/hyper](https://github.com/hyperium/hyper/issues/2678) というトラッキング・イシューがありました。

そこからリンクされている 

横道ですが、 2022年2月に [hyper 1.0 timeline - seanmonstar](https://seanmonstar.com/post/676912131372875776/hyper-10-timeline) が出ていたのに先程気づきました。2022年に 1.0 をリリース予定らしいです。

## ちなみに actix-web のアクセスログのレスポンスサイズについても調べてみた

[Middleware](https://actix.rs/docs/middleware/) のドキュメントの [Logging](https://actix.rs/docs/middleware/#logging) の [Format](https://actix.rs/docs/middleware/#format) には

```
%b Size of response in bytes, including HTTP headers
```

と書いてありました。

ですが [src/middleware/logger.rs](https://github.com/actix/actix-web/blob/6a5b37020676fdfed4b8c7466d8542904bca825c/actix-web/src/middleware/logger.rs) を見るとボディのみのサイズになっているようです。

[examples/basic.rs](https://github.com/actix/actix-web/blob/6a5b37020676fdfed4b8c7466d8542904bca825c/actix-web/examples/basic.rs) を試してみても

```
$ curl -v 127.0.0.1:8080
*   Trying 127.0.0.1:8080...
* Connected to 127.0.0.1 (127.0.0.1) port 8080 (#0)
> GET / HTTP/1.1
> Host: 127.0.0.1:8080
> User-Agent: curl/7.81.0
> Accept: */*
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< content-length: 14
< content-type: text/plain; charset=utf-8
< x-version: 0.2
< date: Sun, 08 May 2022 14:11:55 GMT
<
Hello world!
```

に対してログは

```
[2022-05-08T14:11:55Z INFO  http_log] 127.0.0.1 "GET / HTTP/1.1" 200 14 "-" "curl/7.81.0" 0.000802
```

となっていてレスポンスサイズは 14 バイトで、やはりボディのみのサイズとなっていました。

```
$ printf 'Hello world!\r\n' | wc -c
14
```
