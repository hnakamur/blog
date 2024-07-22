---
title: "freenginxでAgeヘッダーの扱いが改善されました"
date: 2024-07-22T17:59:56+09:00
---

## はじめに

[nginx](https://nginx.org/)とそのフォークの[freenginx](https://freenginx.org/)は[Age](https://www.rfc-editor.org/rfc/rfc9111#name-age)レスポンスヘッダーの値を一切更新しないという挙動になっていましたが、freenginxではそれが改善されたという話です。

ただし、コミットはされましたがリリースはまだです。おそらく次のリリースに含まれると思います。

## 過去

2012年に[#146 (Age header for proxy_http_version 1.1) – nginx](https://trac.nginx.org/nginx/ticket/146)というイシューは作られていましたが、対応されないままになっていました。

## 今回の経緯

* 2024-06-14 nginx-develメーリングリストにパッチを投げてみました。
  * が、出来が悪かったようで[\[PATCH 0 of 3\] Update Age response header correctly](https://mailman.nginx.org/pipermail/nginx-devel/2024-June/5AX5GLDWW567TRODPL4RPPOR5OHYRJA2.html)、コメントがつきませんでした。
* 2024-06-20 freenginx-develメーリングリストにパッチを投げてみました。
  * [\[PATCH 0 of 3\] \[nginx\] cache: Update Age response header correctly](https://freenginx.org/pipermail/nginx-devel/2024-June/000376.html)
  * Maxim Douninさんから詳細なコメントを頂いて、何度かパッチを更新して送りました。
* 2024-07-18 Maixum Dounin さんから、私のパッチより格段に良いパッチが提案されました。
  * [\[PATCH 1 of 3\] Correctly calculate and set Age header](https://freenginx.org/pipermail/nginx-devel/2024-July/000411.html)
  * その後コミットしたとのお知らせ。 [\[PATCH 1 of 3\] Correctly calculate and set Age header](https://freenginx.org/pipermail/nginx-devel/2024-July/000417.html)

## 変更内容

本体のコミットは以下の2つです（公式ミラー https://github.com/freenginx/nginx 内のリンクを貼っています）。

 * [Upstream: using the "Age" header when caching responses. · freenginx/nginx@cc71639](https://github.com/freenginx/nginx/commit/cc71639841da38e55f4a13fd301187fd2c3a0e19)
    * upstreamからのレスポンスにAgeヘッダがついていてかつCache-Control: max-ageまたはs-maxageの値を採用する場合、キャッシュ有効期限の絶対日時を算出する際にAgeの値の分を引くという変更です。
 * [Upstream: $upstream_cache_age variable. · freenginx/nginx@70ee831](https://github.com/freenginx/nginx/commit/70ee831d648a547bbfc7fe2fe567f284b675cb6d)
    * `add_header Age $upstream_cache_age;`を指定することで、キャッシュ作成後に別のリクエストを受けてキャッシュを配信する際にAgeを作成時の値＋滞留時間に設定するという変更です。
    * なお、議論の結果、[RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)の[4.2.3. Calculating Age](https://www.rfc-editor.org/rfc/rfc9111#name-calculating-age)の`corrected_initial_age`はupstreamのAgeレスポンスヘッダー（`age_value`）をそのまま使用するという仕様となっています。

テストのコミットは以下の1つです（公式ミラー https://github.com/freenginx/nginx-tests 内のリンクを貼っています）。

 * [Tests: proxy cache Age header handling tests. · freenginx/nginx-tests@70889b9](https://github.com/freenginx/nginx-tests/commit/70889b9983e63386c2b2978d6aea791294d4bb6a)
