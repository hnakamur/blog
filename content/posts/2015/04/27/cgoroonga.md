+++
Categories = []
Description = ""
Tags = ["groonga"]
date = "2015-04-27T00:44:23+09:00"
title = "データ登録用にgroongaのC APIのgoバインディングを書いてみた"

+++
## groongaで大量のデータを登録する方法を調べてみた

### 方法1: loadコマンドの文字列を組み立ててgroongaコマンドの標準入力に流し込む

groongaのデータの登録はチュートリアルの[データのロード](http://groonga.org/ja/docs/tutorial/introduction.html#load-records)にあるように[loadコマンド](http://groonga.org/ja/docs/reference/commands/load.html)を使えば出来ます。

外部ファイルから大量のデータを登録するときはどうするのかなと思って調べてみると、 groongaのソースの examples/dictionary/eijiro/ の例では `load` コマンドの文字列を組み立てて `groonga` コマンドの標準入力に流し込んでいました。

https://github.com/groonga/groonga/blob/59ef5d1d26b4ba47d163019a21a20519d349489b/examples/dictionary/eijiro/eijiro-import.sh#L10-L12

```
if iconv -f UCS2 -t UTF8 $2 | ${base_dir}/eijiro2grn.rb | groonga $1 > /dev/null; then
  echo "eijiro data loaded."
fi
```

### 方法2: groongaのC APIを使う
この方法はお手軽ですが、エラー処理が難しそうと重い、さらに調べてみると、groongaのC APIを使ってデータ登録する例を見つけました。

[C言語でGroongaのAPIを使う方法 - CreateField](http://createfield.com/C%E8%A8%80%E8%AA%9E%E3%81%A7Groonga%E3%81%AEAPI%E3%82%92%E4%BD%BF%E3%81%86%E6%96%B9%E6%B3%95)

## go言語用のライブラリを作ってみました

折角なのでCのライブラリのgo言語バインディングを作る練習を兼ねてgo言語用のライブラリを作ってみました。

[hnakamur/cgoroonga](https://github.com/hnakamur/cgoroonga)

### テーブルとカラムを作ってレコードを1件登録するサンプルコード

https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/examples/add_record/main.go

OSX + homebrewという環境で試しました。

```
brew install groonga
```

でgroongaをインストールして、以下の手順で実行します。

```
go get github.com/hnakamur/cgoroonga
cd $GOPATH/src/github.com/hnakamur/cgoroonga/examples/add_record
go build
./add_record
```

### Wikipedia日本語版の記事データを登録するサンプルコード

https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/examples/import_wikipedia/main.go

データファイルは
[jawiki dump progress on 20150422](http://dumps.wikimedia.org/jawiki/20150422/)
から以下の4つのファイルをダウンロードしました。

* jawiki-20150422-pages-articles1.xml.bz2
* jawiki-20150422-pages-articles2.xml.bz2
* jawiki-20150422-pages-articles3.xml.bz2
* jawiki-20150422-pages-articles4.xml.bz2

Wikipediaのデータファイルはxmlをbzip2で圧縮した形式になっているので、Goの標準ライブラリの[bzip2](http://golang.org/pkg/compress/bzip2/)と[xml](http://golang.org/pkg/encoding/xml/)パッケージを使って読み込むようにしています。

サイズの大きいXMLファイルを読み込んで処理するときにおすすめの方法が
[Parsing huge XML files with Go - david singleton](http://blog.davidsingleton.org/parsing-huge-xml-files-with-go/)で紹介されていたので、それを真似しました。ありがとうございます！

```
cd $GOPATH/src/github.com/hnakamur/cgoroonga/examples/import_wikipedia
go build
./import_wikipedia jawiki-20150422-pages-articles1.xml.bz2
```

のように実行します。

## Cライブラリのgoバインディングを書くときのtips

基本的には

* [cgo - The Go Programming Language](https://golang.org/cmd/cgo/)
* [cgo · golang/go Wiki](https://github.com/golang/go/wiki/cgo)

を読めばOKなのですが、ハマった点をメモしておきます。

### import "C"の上に空行を入れないように注意

たとえば
https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/column.go#L7
で `import "C"` の上に空行を入れて `go build` を実行すると以下の様なエラーになります。

```
$ go build
# github.com/hnakamur/cgoroonga
could not determine kind of name for C.free
could not determine kind of name for C.grn_column_create
could not determine kind of name for C.grn_obj_column
could not determine kind of name for C.grn_obj_flags
could not determine kind of name for C.strlen
```

### Cのマクロはgoから呼べないのでCの関数でラップする

https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/cgoroonga.c
のようにマクロをラップしたCの関数を書いて、それをgoから呼ぶようにします。

### エラーコードが有るエラーと無いエラーを統一的に扱うようにした

groongaのC APIはほとんどが[7.20.21. grn_table — Groonga v5.0.2ドキュメント](http://groonga.org/ja/docs/reference/api/grn_table.html)の [grn_table_delete](http://groonga.org/ja/docs/reference/api/grn_table.html#c.grn_table_delete)  のように [grn_rc](https://github.com/groonga/groonga/blob/v5.0.2/include/groonga/groonga.h#L44-L125) を返します。

が、 [grn_table_create](http://groonga.org/ja/docs/reference/api/grn_table.html#c.grn_table_create)

```
grn_obj *grn_table_create(grn_ctx *ctx, const char *name, unsigned int name_size, const char *path, grn_obj_flags flags, grn_obj *key_type, grn_obj *value_type)
```

のように `grn_rc` を返さないAPIもあります。ドキュメントには明記されていませんが、Cの慣例としてエラーのときはおそらく戻り値が `NULL` になるのだと予想します。

https://github.com/groonga/groonga/blob/v5.0.2/lib/db.c#L744-L930 を見るとやはりNULLを返すケースが有りました。

そこで、
https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/error.go
のようにエラーコードが有るエラーと無いエラーを全てGoの変数として定義するようにしてみました。

これにより
https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/examples/import_wikipedia/main.go#L59-L63

```
	table, err := ctx.TableOpenOrCreate("Articles", "",
		grn.OBJ_TABLE_HASH_KEY|grn.OBJ_PERSISTENT, keyType, nil)
	if err != nil {
		return
	}
```

のようにエラーを常に戻り値で受け取るように統一することができ、見通しのよいコードが実現できました。


## まとめ

データ登録用にgroongaのC APIのgoバインディングを書きました。
C APIがエラーコードを返さない場合でもGo側ではエラーを返し `if err != nil` というのようにエラーチェックの方式を統一することで、エラー処理の漏れに気づきやすくする事が出来ました。
