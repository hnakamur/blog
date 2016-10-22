+++
Description = ""
Tags = ["goa", "swagger"
]
Categories = [
]
date = "2016-10-22T16:52:02+09:00"
title = "LocaleOverlaySwaggerというgoaプラグインを書いた"

+++
## まず Swagger 仕様を複数ファイル出力する goa プラグイン Multiswagger を試してみました

まずは [Swagger 仕様を複数ファイル出力する goa プラグイン Multiswagger を作った - tchsskのブログ](http://tchssk.hatenablog.com/entry/2016/10/18/122215) を読んで試してみました。

[goadesign/goa: Design-based APIs and microservices in Go](https://github.com/goadesign/goa/) の README からリンクされているサンプル [goadesign/goa-cellar: goa winecellar example service](https://github.com/goadesign/goa-cellar) の `design.go` の各種項目の `Title` や `Description` の値に JSON を書いて英語と日本語の説明を書いてみた例が [goa-getting-started/design.go](https://github.com/hnakamur/goa-getting-started/blob/use_multiswagger/design/design.go) です。　

私が試したバージョンの [Multiswagger at 7ad4f69b2209316035dd222819228f90327cd1f3](https://github.com/tchssk/multiswagger/tree/7ad4f69b2209316035dd222819228f90327cd1f3) では [API定義](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/design/design.go#L8-L19) の `Title` や `Definition` は非対応だったので、 [Comparing tchssk:master...hnakamur:support_more_fields · tchssk/multiswagger](https://github.com/tchssk/multiswagger/compare/master...hnakamur:support_more_fields) のように変更して試してみました。

変更に際して以下の点にハマりました。

ハマった点その1。 API定義は [github.com/goadesign/goagen/genswagger/Swagger](https://godoc.org/github.com/goadesign/goa/goagen/gen_swagger#Swagger) の `Definitions` に保持されるのですが、値の型が `map[string]*genschema.JSONSchema` となっていて、 `JSONSchema` の値は [goa/json_schema.go のグローバル変数 Definitions](https://github.com/goadesign/goa/blob/4d19425396efa86b61d97c3cda0b00ec21f103f7/goagen/gen_schema/json_schema.go#L100) に保持されています。

このため [extract 関数](https://github.com/hnakamur/multiswagger/blob/ec57ee4e1b17d0b13091e0b3d17649796967ed64/generator.go#L142-L173) 内で JSON 文字列から最初のキーの値を取り出して書き変えた後、 [generator.go#L72](https://github.com/hnakamur/multiswagger/blob/ec57ee4e1b17d0b13091e0b3d17649796967ed64/generator.go#L72) で次のキー用に `Swagger` の値を作り直しても JSONSchema は古い値が再利用されてしまいます。そこで [generator.go#L71](https://github.com/hnakamur/multiswagger/blob/ec57ee4e1b17d0b13091e0b3d17649796967ed64/generator.go#L71) で `genschema.Definitions` を初期化することで対応できました。

ハマった点その2。生成された [swagger.ja.yaml の 8 行目](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/swagger/swagger.ja.yaml#L8)  を見ると `definitions` の `description` に ` (default view)` という値が自動的に追加されています。  [design.go#L42-L45](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/design/design.go#L42-L45) に JSON を書いていても ` (default view)` という値が追加されるので JSON としてパースしようとするとエラーになってしまいます。そこで、値が ` (default view)` で終わっていたら、それを取り除いてから JSON としてパース可能か調べるようにしました。そしてパースできる場合はパースして特定のキーの値を取り出してから最後に ` (default view)` とつけるようにしました。

やれやれこれで大丈夫かと思ったのですが、 [swagger.ja.yaml#L33-L69](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/swagger/swagger.ja.yaml#L33-L69) の `error` の `description` は英語になっています。 [design.go](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/design/design.go) に書いていないデフォルト値が出力されているようです。

また、 [swagger.ja.yaml#L95](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/swagger/swagger.ja.yaml#L95) の `summary` も show bottle と英語になっています。これは今はコメントにしていますが [design.go#L36](https://github.com/hnakamur/goa-getting-started/blob/4bef7925510700d8797831f3bb665eb87c8ca6b9/design/design.go#L36) のように `Metadata("swagger:summary", value)` で設定可能なことがわかりました。

しかしこの値を JSON で書くとなると [walk 関数](https://github.com/hnakamur/multiswagger/blob/ec57ee4e1b17d0b13091e0b3d17649796967ed64/generator.go#L175-L253) で Metadata で `"swagger:summary"` 特定のキーの場合だけ処理するという改修が必要です。

このあたりで辛くなってきました。 `design.go` の DSL はそのままで値に JSON を書くという設計は `design.go` で各言語のメッセージが一覧できるという利点がある一方、 generator の実装が面倒だと思います。あと、言語が増えると `design.go` の API 定義に対するメッセージ文字列の行が増えて API 定義が見にくくなるという欠点もあると思いました。


## ということで LocaleOvrerlaySwagger という別の Swagger 仕様生成プラグインを作りました

ソースは [hnakamur/localeoverlayswagger](https://github.com/hnakamur/localeoverlayswagger) で公開しています。

使い方は [README の Usage](https://github.com/hnakamur/localeoverlayswagger#usage) をご参照ください。メッセージの書き方ですが、 [design.go](https://github.com/hnakamur/goa-getting-started/blob/overlay_japanese_yaml/design/design.go) の各種 Description は標準通り英語で書きます。

英語の Swagger 仕様は標準と同じ内容で [swagger/swagger.yaml](https://github.com/hnakamur/goa-getting-started/blob/overlay_japanese_yaml/swagger/swagger.yaml) のように生成されます。 この内置き換えた部分だけのキーを含む YAML ファイルを [overlay_japanese_yaml](https://github.com/hnakamur/goa-getting-started/blob/overlay_japanese_yaml/locales/ja.yaml) のように書いておくと、 [swagger/swagger.ja.yaml](https://github.com/hnakamur/goa-getting-started/blob/overlay_japanese_yaml/swagger/swagger.ja.yaml) のようにその部分だけ上書きされた YAML が生成されるという仕組みです。

英語のメッセージに対応する日本語のメッセージを離れたところに書く必要があるのでその点は不便なのですが、生成された英語の YAML を見ながら対応するキーに日本語メッセージを書くだけで良いので、トータルではこちらのほうが管理が楽だと個人的には思います。

ということで、良かったらご利用ください。
