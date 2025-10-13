---
title: "fluent-bitにLTSV独自エスケープをアンエスケープするパッチ作成"
date: 2025-10-13T13:36:05+09:00
---

## はじめに

[fluent-bit](https://github.com/fluent/fluent-bit)にLTSV独自エスケープをアンエスケープするパッチを作成したメモです。

## LTSV独自エスケープ

[Labeled Tab-separated Values (LTSV)](http://ltsv.org/)に以下の独自のエスケープを追加したものです。

LTSVはラベルと値を`:`でつなぎ、それらをTABでつないで、1行の終端はLFで改行します。

ラベルは管理者が決めるので、`:`、TAB、LFを含まないような文字列のみを使うようにできます。

一方、値は外界からのリクエストに含まれるものなので、TABやLFの文字を含む可能性があります。
例えばUser-AgentにTABが入るようなケースがあったり、悪意の攻撃ではリクエスト行やURLのパスに制御文字が含まれるケースもあり得ます。

そこで、以下の独自のエスケープを行うようにしています。

* 値に含まれるTABは`\t`、LFは`\n`とバックスラッシュでエスケープする
* 値に含まれる`\`も`\\`とバックスラッシュでエスケープする

ログを解釈する側では、これらをアンエスケープする必要があります。

* `\t`→TAB
* `\n`→LF
* `\\`→`\`

## LTSV独自エスケープ対応のfluent-bitのUbuntu用debパッケージ

いつものようにUbuntuの独自debパッケージを作りました。

https://github.com/hnakamur/fluent-bit-deb-docker

LTSV独自エスケープのアンエスケープ対応のパッチは[debian/patches/unescape_ltsv.patch](https://github.com/hnakamur/fluent-bit-deb-docker/blob/4.0.12-1hn1ubuntu24.04/debian/patches/unescape_ltsv.patch)です。

また以下の変更も加えています。

* [hnakamur/openresty-luajit-deb-docker](https://github.com/hnakamur/openresty-luajit-deb-docker)でビルドした[OpenRestyのLuaJIT](https://github.com/openresty/luajit2)のdebパッケージを使う
* [hnakamur/openresty-lua-cjson-deb-docker](https://github.com/hnakamur/openresty-lua-cjson-deb-docker)でビルドした[OpenRestyのLua CJSON](https://github.com/openresty/lua-cjson)のdebパッケージを使う
* Ubuntu標準パッケージのjemallocを使う

### LTSV独自エスケープのアンエスケープの設定

fluent-bit.yaml内の`parsers`の`format: ltsv`の要素に以下のように`unescape: true`と指定するとアンエスケープします。

```
parsers:
  - name: nginx_access_ltsv
    format: ltsv
    time_key: time
    time_format: '%Y-%m-%dT%H:%M:%S%z'
    unescape: true
```

### 動作確認

https://github.com/hnakamur/fluent-bit-deb-dockerのtestディレクトリに[Incus](https://incus-ja.readthedocs.io/ja/latest/)を使った動作確認用のスクリプトを置きました。

実行例
```
$ ~/ghq/github.com/hnakamur/fluent-bit-deb-docker/test$ ./launch-incus-container-and-test.sh 24.04 fluentbit-noble
…（略）…
+ tail -1 /var/log/nginx/access.ltsv.log
time:2025-10-13T05:17:32+00:00  msec:1760332652.525     host:localhost  http_host:localhost     status:200      scheme:http     request:GET /?a=1 HTTP/1.1      request_id:0201c592df20769c34c3b9c81bd96d51     request_time:0.000  request_length:76       body_bytes_sent:615     bytes_sent:853  remote_addr:127.0.0.1   remote_port:59448       remote_user:    pid:1207        referer:        x_forwarded_for:        user_agent:tab\tinside
…（略）…
+ systemctl status --no-pager -l fluent-bit
…（略）…
Oct 13 05:17:33 fluentbit-noble fluent-bit[1213]: [{"date":1760332652.0,"msec":"1760332652.525","host":"localhost","http_host":"localhost","status":"200","scheme":"http","request":"GET /?a=1 HTTP/1.1","request_id":"0201c592df20769c34c3b9c81bd96d51","request_time":"0.000","request_length":"76","body_bytes_sent":"615","bytes_sent":"853","remote_addr":"127.0.0.1","remote_port":"59448","remote_user":"","pid":"1207","referer":"","x_forwarded_for":"","user_agent":"tab\tinside"}]
```

nginxのアクセスログでは`user_agent`の値が`tab\tinside`とTABが`\t`にエスケープされています。

これは[hnakamur/nginx-deb-docker](https://github.com/hnakamur/nginx-deb-docker/)でビルドしたnginxで[nginx.conf#L20-L40](https://github.com/hnakamur/fluent-bit-deb-docker/blob/3ef9e3e6840ff8c2cf6b375236778c77726928cf/test/nginx.conf#L20-L40)のように`log_format`に`escape=ltsv`という独自拡張した設定を行うことで実現しています。

fluent-bitの出力では`"user_agent":"tab\tinside"`となっておりTABが維持できていることが確認できます（JSONのエスケープでTABが`\t`になっています）。

試しに、fluent-bitの設定で`unescape: true`をコメントアウトして試すと以下のようになります。

```
Oct 13 05:20:32 fluentbit-noble2 fluent-bit[1213]: [{"date":1760332831.0,"msec":"1760332831.526","host":"localhost","http_host":"localhost","status":"200","scheme":"http","request":"GET /?a=1 HTTP/1.1","request_id":"195674a1389e61693288ed51d16bd5ef","request_time":"0.000","request_length":"76","body_bytes_sent":"615","bytes_sent":"853","remote_addr":"127.0.0.1","remote_port":"57586","remote_user":"","pid":"1207","referer":"","x_forwarded_for":"","user_agent":"tab\\tinside"}]
```

アンエスケープなしだと`"user_agent"`の値が`"tab\\tinside"`となっています。JSONのエスケープで`\`が`\\`とエスケープされており、tabとinsideの実際の間はTABではなく`\t`のままになってしまっていることがわかります。
