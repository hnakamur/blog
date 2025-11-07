---
title: "nginxでJA4 fingerprintを出力するモジュールを書いた"
date: 2025-11-07T23:47:56+09:00
---
## はじめに

TLSのJA3フィンガープリントを出力するnginxのサードバーティーのモジュールをベースにJA4対応してみたというメモです。

とりあえず動くものができたっぽいという段階なので、本番運用に使えるレベルかは不明です。

## JA3 / JA4について

JA3とJA4の概要については[Bot 対策の基礎技術 : JA3 / 4 Fingerprinting](https://zenn.dev/kameoncloud/articles/f90f2970f2aae3)の記事がわかりやすかったです。ありがとうございます。

JA3のレポジトリは[salesforce/ja3: JA3 is a standard for creating SSL client fingerprints in an easy to produce and shareable way.](https://github.com/salesforce/ja3)です。2025-05-02にアーカイブされています。オリジナルの作者であるJohn AlthouseさんがFoxIO-LLCで最新のTLSフィンガープリンティングを保守されているとの記載がありました。

JA4のレポジトリは[FoxIO-LLC/ja4: JA4+ is a suite of network fingerprinting standards](https://github.com/FoxIO-LLC/ja4/search?l=cmake)です。

JA4: TLS Client Fingerprintingの仕様は[ja4/technical_details/JA4.md](https://github.com/FoxIO-LLC/ja4/blob/2d81015d600c3ebad58caa5042d2fe98b675bbbf/technical_details/JA4.md)です。

`JA4`の他に`JA4_r`、`JA4_o`、`JA4_ro`というフィンガープリントもあります。[Raw Output](https://github.com/FoxIO-LLC/ja4/blob/2d81015d600c3ebad58caa5042d2fe98b675bbbf/technical_details/JA4.md#raw-output)の項に説明があります。一致するかどうかを見るだけなら`JA4`だけで良いですが、不一致な場合に原因を調査するには他の値も見ることになります。

## JA3 / JA4はWiresharkでも確認できる

公式の[FoxIO-LLC/ja4](https://github.com/FoxIO-LLC/ja4/search?l=cmake)に含まれるCLIでtcpdumpでキャプチャーしたファイルを読んで`JA4`、`JA4_r`、`JA4_o`、`JA4_ro`の値を出力できます。

WiresharkでもClient Helloのパケットを選んで[Transport Layer Security]の下を展開していくと`JA4`、`JA4_r`、`JA3 Fullstring`、`JA3`の値を見られます。

## JA3 / JA4のnginxモジュールについて

この組織に公式のnginxモジュールのレポジトリ [FoxIO-LLC/ja4-nginx-module: Nginx module that calcuates fingerprints from the JA4+ suite](https://github.com/FoxIO-LLC/ja4-nginx-module)もありました。しかし、READMEに他のことを優先するため開発は中断していて、公開されているバージョンでは正しいJA4の値が生成されないと書いてありました。さらに[LICENSE](https://github.com/FoxIO-LLC/ja4-nginx-module/blob/1568ee8caab4bae9c5c8424f2fbbf6d105e1d8eb/LICENSE)がFoxIO License 1.1という独自ライセンスだったので、こちらのレポジトリのコードは見ていません。

一方、[FoxIO-LLC/ja4](https://github.com/FoxIO-LLC/ja4/search?l=cmake)の[Licensing](https://github.com/FoxIO-LLC/ja4?tab=readme-ov-file#licensing)の項を見るとJA4: TLS Client Fingerprintingは3項BSDのオープンソースライセンスです。

> JA4: TLS Client Fingerprinting is open-source, BSD 3-Clause, same as JA3. FoxIO does not have patent claims and is not planning to pursue patent coverage for JA4 TLS Client Fingerprinting. This allows any company or tool currently utilizing JA3 to immediately upgrade to JA4 without delay.

ただしそれ以外のJA4+（JA4S、JA4L、JA4LS、JA4H、JA4X、JA4SSH、JA4T、JA4TS、JA4TScanや今後追加される種別）は[FoxIO License 1.1](https://github.com/FoxIO-LLC/ja4/blob/main/LICENSE)とのことです。

サードパーティのnginxのJA4のモジュールは検索したところなさそうでした。nginxのJA3のモジュールはサードパーティー製の2つが見つかりました。

[fooinha/nginx-ssl-ja3: nginx module for SSL/TLS ja3 fingerprint.](https://github.com/fooinha/nginx-ssl-ja3)はREADMEにプロダクションレディではないと書いてあったので、[phuslu/nginx-ssl-fingerprint: High performance ja3 and http2 fingerprint for nginx.](https://github.com/phuslu/nginx-ssl-fingerprint)のほうを試してみることにしました。

その後このモジュールを改変してJA3の改修とJA4の機能拡張を行いました。

## 作成したJA4のモジュール

https://github.com/hnakamur/nginx-ssl-fingerprint に置いています。

### 動的モジュールに対応

元のレポジトリはnginxの静的モジュールのみ対応だったので、[動的モジュールにも対応](https://github.com/hnakamur/nginx-ssl-fingerprint/commit/8cda9d82233244de49e2ce720090dabc27d45f5b)しました。


### OpenSSLのパッチを改修

JA3とJA4ではTLSのClient Helloに含まれる各種情報を収集してフィンガープリントの値を生成します。

そのうち、ClientHelloに含まれるTLS拡張タイプの一覧を取得する部分があります。

元のパッチでは [patches/openssl.openssl-3.4.patch#L75-L103](https://github.com/phuslu/nginx-ssl-fingerprint/blob/bd882b328d0999f07035ee77afdd958a4e813b79/patches/openssl.openssl-3.4.patch#L75-L103)の部分で取得していました。

ちなみに[apache/trafficserver](https://github.com/apache/trafficserver)にもJA3のプラグインとexperimentalなJA4のプラグインがあるのですが、そちらでは`SSL_client_hello_get1_extensions_present`というAPIを使用していました。

- [plugins/ja3_fingerprint/ja3_fingerprint.cc#L148](https://github.com/apache/trafficserver/blob/10.1.0/plugins/ja3_fingerprint/ja3_fingerprint.cc#L148)
- [plugins/experimental/ja4_fingerprint/plugin.cc#L283](https://github.com/apache/trafficserver/blob/10.1.0/plugins/experimental/ja4_fingerprint/plugin.cc#L283)

しかし、上記の方法ではChromeでアクセスしたときに公式CLIやWiresharkで確認した`JA4`や`JA3`の値と一致しないことが判明しました。ハッシュ値化する前の元の値を見比べるとClient Helloに含まれる拡張タイプの一覧が一部不足していました。

そこでOpenSSLの[tls_collect_extensions](https://github.com/openssl/openssl/blob/openssl-3.5.4/ssl/statem/extensions.c#L592-L728)関数を元に[openssl.openssl-3.5.4.ja4.patch](https://github.com/hnakamur/nginx-ssl-fingerprint/blob/ebfd72b6874fa603bc57d3491e020d186824f772/patches/openssl.openssl-3.5.4.ja4.patch)というパッチを作成しました。こちらはClient Helloに含まれる拡張をすべて取得します。

これでWiresharkの`JA4`や`JA3`の値と一致するようになりました。

### nginxのパッチも改修

元のパッチ[nginx-ssl-fingerprint/patches/nginx-1.27.patch](https://github.com/phuslu/nginx-ssl-fingerprint/blob/master/patches/nginx-1.27.patch)を[nginx-1.29.3.ja4.patch](https://github.com/hnakamur/nginx-ssl-fingerprint/blob/ja4_fingerprint/patches/nginx-1.29.3.ja4.patch)のように改修しました。

`struct ngx_ssl_connection_s`内に`JA3`関連のフィールドを追加するのに加えて、`JA4`関連のフィールドも追加するようにしました。

`ngx_ssl_handshake`関数内で`SSL_CTX_set_client_hello_cb`関数を呼んでClient Helloを処理するときのコールバック関数を設定します（設定できる関数は1つだけで複数回呼ぶと上書きされてしまいます）。

元は`ngx_ssl_client_hello_ja3_cb`という関数を設定していましたが、`JA3`に必要な情報に加えて`JA4`で必要な情報も取得するように変更し関数名も`ngx_ssl_client_hello_ja4_cb`に変更しました。

また動的モジュール対応にしたので、モジュールを読み込んだ場合にのみ`SSL_CTX_set_client_hello_cb`関数を呼ぶようにしました。これはモジュールを読み込まない場合になるべく不要な処理をしないようにという配慮です。

### nginx-ssl-fingerprintモジュール本体も改修

`JA4`、`JA4_r`、`JA4_o`、`JA4_ro`の値を取得する変数を追加しました。変更内容は[ebfd72b](https://github.com/hnakamur/nginx-ssl-fingerprint/commit/ebfd72b6874fa603bc57d3491e020d186824f772)です。

## Ubuntu 24.04/22.04用のdebパッケージ

Ubuntu 24.04/22.04用のdebパッケージも作成しました。

パッチを当てたOpenSSLを共有ライブラリとしてビルドするのは管理が大変そうなので、nginxにスタティックリンクすることにしました。バージョンは[Downloads | OpenSSL Library](https://openssl-library.org/source/)で最新のLTSである3.5.4です。

- [Releases 1.29.3+openssl.3.5.4+mod.1-1hn1ubuntu24.04](https://github.com/hnakamur/nginx-deb-docker/releases/tag/1.29.3%2Bopenssl.3.5.4%2Bmod.1-1hn1ubuntu24.04)
- [Releases 1.29.3+openssl.3.5.4+mod.1-1hn1ubuntu22.04](https://github.com/hnakamur/nginx-deb-docker/releases/tag/1.29.3%2Bopenssl.3.5.4%2Bmod.1-1hn1ubuntu22.04)
