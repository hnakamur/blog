Title: mithril.jsを試してみた
Date: 2015-05-12 22:02
Category: blog
Slug: 2015/05/12/tried_mithril_js

## はじめに

[groongaのgoバインディングでWikipedia全文検索のサンプルウェブアプリを作ってみた · hnakamur's blog at github](/blog/2015/05/12/cgoroonga_wikipedia_search_webapp/)のフロントエンドを[Mithril](https://lhorie.github.io/mithril/)で書いてみました。

## 参考にした記事

mithril.jsについてはまず以下の記事

* [最速MVCフレームワークMithril.jsの速度の秘密 - Qiita](http://qiita.com/shibukawa/items/890d24874655439932ec)
* [JavaScript - 速くて軽いらしいMithril.jsを試してみた - Qiita](http://qiita.com/mmyoji/items/211679de86f567e741f4)

を読み、その後本家の[Guide](https://lhorie.github.io/mithril/getting-started.html)の左のリンクから辿れる記事と[Learn Mithril](http://lhorie.github.io/mithril-blog/)の記事をひと通り読みました。

今回は試していませんが、
[Velocity.js animations in Mithril](http://lhorie.github.io/mithril-blog/velocity-animations-in-mithril.html)の記事で、[Velocity.js](http://julian.com/research/velocity/)を組み合わせてアニメーションを実現する方法も紹介されていました。


## データバインディングの仕組み
 
mithril.jsを読み込むと `m` というグローバル変数にmithrilのモジュールが定義されます。モジュールと言ってもビューの関数としても使いますし、他の関数の名前空間としても使っています。

まずモデルの定義ですが、[Getting Started](https://lhorie.github.io/mithril/getting-started.html#model)の[Model](https://lhorie.github.io/mithril/getting-started.html#model)のところにあるように、[m.prop](https://lhorie.github.io/mithril/mithril.prop.html)を使って

`プロパティ = m.prop(初期値)`

と書くことで、プロパティが作られます。プロパティは値ではなくてgetter-setterの関数になっていて、 `プロパティ()` で値を取得、 `プロパティ(値)` で値を設定します。

モデル層はドメインモデルに限定して、UIの状態は[View-Model](https://lhorie.github.io/mithril/getting-started.html#view-model)として定義します。

[Controller](https://lhorie.github.io/mithril/getting-started.html#controller)はビューモデルを保持し、ビューでのイベントハンドラやビューを操作する関数を定義します。

HTMLの構造は[View](https://lhorie.github.io/mithril/getting-started.html#view)の例にあるように、 [m](https://lhorie.github.io/mithril/mithril.html) という関数を使って記述します。JavaScriptで書くのですが宣言的に書けるので、見やすいです。

* 第一引数にCSSクエリ文字列を書くと、そのタグ名や属性を持った要素が作られます。
* 第二引数は省略可能ですが、属性のハッシュを指定できます。
* 最後の引数で子要素を指定します。複数の場合は配列、単一の子要素なら `m` の呼び出し、テキスト要素なら文字列を指定します。

あとは[m.mount](https://lhorie.github.io/mithril/mithril.mount.html)か[m.component](https://lhorie.github.io/mithril/mithril.component.html)でマウントすると、モデルの値が変わったらビューの表示もmithrilが更新してくれます。

## 今回作成したソース

基本的な構造は[Components](https://lhorie.github.io/mithril/components.html)の[Classic MVC](https://lhorie.github.io/mithril/components.html#classic-mvc)のパターンを真似しました。

ソースは[cgoroonga/index.html](https://github.com/hnakamur/cgoroonga/blob/8fd6f566f84fd2564a17e38bc96d8a346d2a120a/examples/search_wikipedia_webapp/public/index.html)にあります。お手軽に試していたレベルなのでstyleタグやscriptタグもhtml内に書いちゃってます。

コンポーネントの階層は以下のようになっています。

* SearchWidget: 検索画面全体のウィジェット
    * SearchForm: 検索フォーム
        * SelectWidget: ドロップダウンウィジェット（検索期間選択用）
    * SearchResultWidget: 検索結果表示ウィジェット
    * PaginationWidget: ページネーションウィジェット

検索フォームをサブミットした時とページネーションのリンクをクリックした時は、
[The observer pattern](https://lhorie.github.io/mithril/components.html#the-observer-pattern)の `Observable` 経由で検索処理を実行しています。

一方、検索期間のSelectWidgetの選択を切り替えた時は、SelectWidgetのコントローラの `onchange` →SelectWidgetのビューモデルの `onchange` →SearchWidgetのコントローラの `onchangetimespan` と呼び出しを連鎖して検索処理を実行するようにしてみました。

ビューの定義時に `m.component` でサブコンポーネントを埋め込むときに引数でビューモデルやイベントハンドラを渡しておいて、ビューではそのビューモデルを参照し、イベントが起きたら引数で渡されていたイベントハンドラを呼び出すというパターンです。

## おわりに

mithril.jsを使うとコンポーネントごとにMVCパターンで実装できて、コンポーネント間はObservableで連携するか、ビューでサブコンポーネントを利用する際に引数で渡したビューモデルとイベントハンドラで連携することが出来、見通しが良いと感じました。

[mithril.jsのソース](https://github.com/lhorie/mithril.js/blob/next/mithril.js)も現時点で1161行とコンパクトなのも魅力です。まだバージョン v0.2.0 ですが、今後が楽しみなフレームワークですね。
