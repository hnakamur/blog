---
title: "多段HTTPプロキシでのAgeヘッダ"
date: 2024-06-17T21:19:26+09:00
---

## はじめに

[RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)の[4.2.3. Calculating Age](https://www.rfc-editor.org/rfc/rfc9111#name-calculating-age)ではAgeの計算式は以下のように定義されています。

```
A response's age can be calculated in two entirely independent ways:

the "apparent_age": response_time minus date_value, if the implementation's clock is reasonably well synchronized to the origin server's clock. If the result is negative, the result is replaced by zero.

the "corrected_age_value", if all of the caches along the response path implement HTTP/1.1 or greater. A cache MUST interpret this value relative to the time the request was initiated, not the time that the response was received.

  apparent_age = max(0, response_time - date_value);

  response_delay = response_time - request_time;
  corrected_age_value = age_value + response_delay;

The corrected_age_value MAY be used as the corrected_initial_age. In circumstances where very old cache implementations that might not correctly insert Age are present, corrected_initial_age can be calculated more conservatively as

  corrected_initial_age = max(apparent_age, corrected_age_value);

The current_age of a stored response can then be calculated by adding the time (in seconds) since the stored response was last validated by the origin server to the corrected_initial_age.

  resident_time = now - response_time;
  current_age = corrected_initial_age + resident_time;
```

nginxでAgeヘッダをこの仕様に沿って更新するようにパッチを作った後、テストをしているうちにいろいろ気付いたのでメモです。

## `request_time`、`response_time`の単位

まず、`date_value`は[Date](https://www.rfc-editor.org/rfc/rfc9110.html#name-date)、`age_value`もupstreamの[Age](https://www.rfc-editor.org/rfc/rfc9111#name-age)に対応する値なので秒単位です。

`corrected_age_value = age_value + response_delay;`という式で`corrected_age_value`も`age_value`も秒単位なので、`response_delay`も必然的に秒単位になります。

一方、`request_time`と`response_time`は以下の説明となっていますが、時間の単位は明記されていません。
```
"request_time"
  The value of the clock at the time of the request that resulted in the stored response.
"response_time"
  The value of the clock at the time the response was received.
```

例えば、`request_time`が00:00:00.999、`response_time`が00:00:01.001の場合（日付部分は省略）を考えます。

ミリ秒単位であれば、`response_delay`は0.002秒ですが、秒単位に切り捨てると0秒になります。
秒単位であれば、`request_time`は00:00:00、`response_time`は00:00:01となり`response_delay`は1秒となります。

このように`request_time`、`response_time`の単位を秒単位にするかもっと細かい単位にするかで、`response_delay`の値が変わってくる場合があるわけです。

### Apache Traffic Serverでは`request_time`、`response_time`は秒単位

[HttpTransactHeaders::calculate_document_age](https://github.com/apache/trafficserver/blob/9.2.4/proxy/http/HttpTransactHeaders.cc#L355-L421)メソッドの引数を見ると`request_time`と`response_time`の型はともに`ink_time_t`でこれは[`time_t`に`#define`されている](https://github.com/apache/trafficserver/blob/9.2.4/proxy/http/HttpTransactHeaders.h#L26)ので秒単位です。

## 多段プロキシの場合は`response_delay`が多重に効いてくる

`client -> child proxy -> parent proxy -> origin server`という2段構成を考えます（->はリクエストの流れの向き）。

child proxyとparent proxyにともにキャッシュがない初期状態で、以下のようになったとします。

```
00:00:00 chlid proxyの`request_time`
00:00:00 parent proxyの`request_time`
00:00:00 origin serverの`date_value`
00:00:01 parent proxyの`response_time`と`date_value`
00:00:01 child proxyの`response_time`
```

parent proxyでは以下のようになります。
```
  apparent_age = max(0, response_time - date_value) = 1

  response_delay = response_time - request_time = 1
  corrected_age_value = age_value + response_delay = 0 + 1 = 1

  corrected_initial_age = max(apparent_age, corrected_age_value) = 1
```

child proxyでは以下のようになります。
```
  apparent_age = max(0, response_time - date_value) = 0

  response_delay = response_time - request_time = 1
  corrected_age_value = age_value + response_delay = 1 + 1 = 2

  corrected_initial_age = max(apparent_age, corrected_age_value) = 2
```

実際はオリジンからchild proxyまでのレスポンスの転送に1秒しかかかってないのに、Ageは2になってしまいます。

`response_delay`がラウンドトリップの時間になっていて、child proxyでの値はparent proxyでの値を含んでいる上に、`corrected_age_value`では`response_delay`が各hopごとに足されていくので、こういう結果になるわけです。

改めて考えてみると、以下の計算式が自然な気がします。
```
  response_receiving_delay = response_time - date_value;
  corrected_initial_age2 = age_value + response_receiving_delay;
```

冒頭に貼った[4.2.3. Calculating Age](https://www.rfc-editor.org/rfc/rfc9111#name-calculating-age)の説明を読むと、originやproxyがすべて正しくAgeヘッダを設定する場合は`corrected_age_value`を`corrected_initial_age`として使ってもよい（MAY）とあります。そうだとしても
```
  response_delay = response_time - request_time;
  corrected_age_value = age_value + response_delay;
```
で`response_delay`がupstreamからのレスポンス転送時間ではなくラウンドトリップの時間なので、上の例ではchild proxyのAgeはやはり2になります。

なぜこういう定義になっているのかは私にはよくわかりません。しかし
```
the "corrected_age_value", if all of the caches along the response path implement HTTP/1.1 or greater. A cache MUST interpret this value relative to the time the request was initiated, not the time that the response was received.
```
とリクエスト開始日時からの相対値でなければならない（MUST）と書いてあるので意図的なものであることは間違いなさそうです。

一つありそうな理由としてはdownstreamとupstreamでサーバのシステム日時がずれている場合でも問題ないように、`request_time`を起点にしているのかもしれません。こうすると`response_time`と`request_time`が同一のサーバ上のシステム日時なのでサーバ間のずれの問題は回避できるので。
