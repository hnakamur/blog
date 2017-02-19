Title: groongaのgoバインディングでWikipedia全文検索のサンプルウェブアプリを作ってみた
Date: 2015-05-12 21:24
Category: blog
Tags: groonga, go
Slug: blog/2015/05/12/cgoroonga_wikipedia_search_webapp

[データ登録用にgroongaのC APIのgoバインディングを書いてみた · hnakamur's blog at github](http://hnakamur.github.io/blog/2015/04/27/cgoroonga/)の続きで、APIを追加実装し、Wikipedia全文検索のサンプルウェブアプリを作ってみました。

## ソースコード

ウェブアプリのソースは
https://github.com/hnakamur/cgoroonga/tree/master/examples/search_wikipedia_webapp
にあります。

GroongaのC APIについては[7.20. API — Groonga v5.0.3ドキュメント](http://groonga.org/ja/docs/reference/api.html)を見つつ、ドキュメント化されていないものは[groongaのソース](https://github.com/groonga/groonga)を見て、goバインディングを作りました。

goバインディングもウェブアプリもとりあえず全文検索の動作確認ができればいいやということで、ゆるい感じで書いています。

ウェブアプリのサーバサイドのソースは
https://github.com/hnakamur/cgoroonga/blob/master/examples/search_wikipedia_webapp/main.go
で、groongaのgoバインディングのソースは
https://github.com/hnakamur/cgoroonga
の `*.go` です。

## フロントエンドについては別記事で

フロントエンドは[最速MVCフレームワークMithril.jsの速度の秘密 - Qiita](http://qiita.com/shibukawa/items/890d24874655439932ec)の記事を見て気になっていたので、[Mithril](https://lhorie.github.io/mithril/)で書いてみました。こちらについては別記事[mithril.jsを試してみた](/blog/2015/05/12/tried_mithril_js/)に書きました。

## インデクスの作成

groongaコマンドで以下のようにして作成しました。約27分かかりました。

```
$ echo 'column_create --table ArticleIndexes --name article_index --flags COLUMN_INDEX|WITH_POSITION|WITH_SECTION --type Articles --source _key,text' | time groonga ~/work/groonga/db/wikipedia.db
[[0,1431052924.67975,1555.13576507568],true]
     1660.80 real      1135.40 user       146.29 sys
```

Wikipediaのページタイトルと本文の両方を対象に検索したいので、 `--source` には \_keyカラム (タイトル) と text カラム (本文) の両方を指定しました。

## 検索の応答は約80〜250ms程度と満足な早さ

* 動作環境
    * マシン: MacBook Pro 15inch (Retina, Mid 2012) SSD
    * CPU: Intel Core i7 2.6GHz
    * RAM: 16GB 1600MHz DDR3
* データサイズ
    * データファイルの合計サイズ: 188MB
    * データ件数: 約193万件

```
$ du -sm ~/work/groonga/db
18848 /Users/hnakamur/work/groonga/db
$ echo 'select Articles --limit 0' | groonga ~/work/groonga/db/wikipedia.db
[[0,1431434283.68242,0.00117397308349609],[[[1932736],[["_id","UInt32"],["_key","ShortText"],["text","Text"],["updated_at","Time"]]]]]
```

JSON形式の検索APIの応答が約80〜250ms程度で、快適に検索できました。
Groongaすごいですね！
