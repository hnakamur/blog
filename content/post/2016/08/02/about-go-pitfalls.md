Title: ブログ記事「Go言語(Golang) はまりどころと解決策」についてのコメント
Date: 2016-08-02 05:57
Category: blog
Slug: blog/2016/08/02/about-go-pitfalls

[Go言語(Golang) はまりどころと解決策](http://www.yunabe.jp/docs/golang_pitfall.html)の記事についてのコメント記事を誰かが書くだろうと思ってスルーしてましたが、見かけないので書いてみます。

ただし私はGo言語を使って開発していますが、言語自体を詳細に知るエキスパートでは無いです。Go言語にかぎらず個人的にはややこしいところにはなるべく近づかないスタンスなので、詳しい方から見ると物足りないかもしれません。そう感じた方は是非ブログ記事なりを書いていただけると嬉しいです。

## interface とnil (Goのinterfaceは単なる参照ではない)

特にコメントはなくてそのとおりだと思います。

[Frequently Asked Questions (FAQ)](https://golang.org/doc/faq)に加えて [Effective Go](https://golang.org/doc/effective_go.html)も早めに読んでおいたほうが良いと思います。

またnilに関する文献としては [Understanding Nil // Speaker Deck](https://speakerdeck.com/campoy/understanding-nil) もおすすめです。

## メソッド内でレシーバ(this, self)がnilでないことをチェックすることに意味がある

[Method declarations](https://golang.org/ref/spec#Method_declarations) に

> The type of a method is the type of a function with the receiver as first argument.

とあります。メソッドの型はメソッドの引数の前にレシーバを第一引数として入れた関数の型になるとのことです。

大雑把に言えば、メソッドは第一引数にレシーバを追加した関数と実質同じです。と考えればメソッド内でポインタ型のレシーバのnilチェックをすることは特に違和感ないと思います。

## errorしか返り値がない関数でerrorを処理し忘れる

[alecthomas/gometalinter](https://github.com/alecthomas/gometalinter)でチェックできました。

実行例を示します。

```
$ gometalinter 
main.go:8:6:warning: exported type Data should have comment or be unexported (golint)
main.go:4:2:error: could not import encoding/json (reading export data: /usr/local/go1.7rc3/pkg/linux_amd64/encoding/json.a: unknown version: v1json    E$GOROOT/src/encoding/json/decode.go?Un) (gotype)
-$GOROOT/src/fmt/scan.go not impStatr) (gotype)g export data: /usr/local/go1.7rc3/pkg/linux_amd64/fmt.a: unknown version: v1fmt
main.go:14:2:error: undeclared name: json (gotype)
main.go:15:2:error: undeclared name: fmt (gotype)
main.go:14:16:warning: error return value not checked (json.Unmarshal([]byte("not json"), d)) (errcheck)
main.go:9:2:warning: unused struct field github.com/hnakamur/forgotten-error-experiment.Data.a (structcheck)
```

jsonやfmt関連のエラーは何言ってるのかよくわからないで無視するとして

```
main.go:14:16:warning: error return value not checked (json.Unmarshal([]byte("not json"), d)) (errcheck)
```

で error の戻り値がチェックされていないことを指摘されています。

gometalinterのセットアップと使い方は[gometalinter で楽々 lint - Qiita](http://qiita.com/spiegel-im-spiegel/items/238f6f0ee27bdf1de2a0)にわかりやすい記事がありました。


## 基本型がメソッドを持たない

FAQの[Why is len a function and not a method?](https://golang.org/doc/faq#methods_on_basics)によると `len` などをメソッドにすることも検討したけど、 `len` がメソッドではなく関数でも実用上困らないし、そのほうが基本型の (Go言語の型の意味での) インタフェースについての質問を複雑にしないので、 `len` などは関数として実装することにしたそうです。

「インタフェースについての質問」あたりはとりあえずそう訳しましたが、意味はよくわかりません。詳しい方のコメントを期待したいところです。

## stringが単なるバイト列

「正直本当に正しいのかはよく分かりません」については私は正しいかどうかという話というよりは、Go言語ではそう決めたというだけの話かと思っています。

言語の利用者がハマりにくい決定をするほうが望ましいという意味で「正しいか」と言われているのだとは思いますが、私自身はほぼ常にUTF-8の文字列しか使ってないので特にハマったことはないです。

文字コード変換には[golang/text: \[mirror\] Go text processing support](https://github.com/golang/text)というパッケージがあります。

`io.Reader` からEUC-JP, Shift_JIS, ISO-2022-JPの文字列を読み込んで UTF-8に変換するのは

https://github.com/hnakamur/goqueryja/blob/01aead01dd3ac586c6256140a26a50fb30451971/lib.go#L27-L40

というコードで実現できます。


## 継承がない

継承を敢えて排除したのはGoの好きな点の1つです。


## Genericsがない

私が他の言語で知ってるのはJavaのGenericsとHaskellの型クラスです。Haskellは軽く勉強した程度ですが、型クラスはシンプルで汎用的で美しさを感じました。

一方Javaは10年近く仕事で書いてましたが、 `? extends` とか `? super` のあたりはよくわからなくて避けてました。当時はそれでも困らなかったです。

複雑なものが苦手な私としては、Javaのような複雑さになるぐらいならGenericsは無いほうが良いと思うので、Goの決断は私は賛成です。

Genericsが無いとMap, Each, Selectのような関数を []interface{} に対して書いてみたくなると思います。 [goでEach, Map, Selectのサンプル - Qiita](http://qiita.com/hnakamur/items/76b06603013279b14aeb)で私も昔書いてみました。でも[コメント](http://qiita.com/hnakamur/items/76b06603013279b14aeb#comment-3d16d66e68bad9626f56)に書いたように、Goの開発者のRob Pikeさんもこういう関数は使わずに `for` ループを使うべきと書かれています。

Goに入ってはGoに従え (When in Go, do as the gophers do) ということで `for` で書くのが良いと思います。


## goroutine はGCされない

同意です。

Dave Cheneyさんのツイート
https://twitter.com/davecheney/status/714053897841577985

とスライド
https://github.com/davecheney/high-performance-go-workshop/blob/ee2e7a82092a72d742b12b00308b0145f124d593/high-performance-go-workshop.slide#L648-L658

にある

> Never start a goroutine without knowing how it will stop.

というルールを守るのが良い習慣だと思います。


## goroutineはgenerator (yield) の実装には使えない

内容自体は同意です。

ちょっと脱線になりますが、こういう他の言語の仕組みを同じようなものを作ろうとするのは、そもそもGoの文化になじまないです。Goは他の言語では常識とされている仕組みも一から吟味して取捨選択して最低限のものだけを残して、それ以外は敢えて含めていないと感じていて、ミニマリストな私には非常に魅力的です。

less is moreの精神を感じます。言語の仕組みが最低限で、同じようなことは同じように書くことになるので、サードパーティのライブラリなど人のコードを読むときに非常に読みやすいというメリットがあります。

また、自分でコードを書くときにも、似たようなことを実現するために複数の仕組みがあるとこのケースではどれを選ぶべきかと考える必要がありますが、決まったパターンがあれば悩む時間がありません。

この結果Go言語だと言語でどう書くかよりもアプリケーションやライブラリの問題領域の方に注力しやすいと感じています。

yieldみたいなことはせずに、goroutineを複数動かしてchannelでデータをやり取りするか、変数を sync.Mutex などで排他制御してデータをやり取りするのがGo流だと思います。あるいは簡単なイテレータなら関数を返すような関数で実現可能だと思います。

## 例外が(推奨され)ない

Java, Python, Rubyなどを書いていた私としても例外がないのは不便なのではと最初は思いましたが、今では err が戻り値で毎回

```
if err != nil {
   return err
}
```

と書くほうが、エラーの処理漏れが無いことが明確で安心感を感じます。

[Errors are values - The Go Blog](https://blog.golang.org/errors-are-values)のbufioのScannerのようにエラーがチェックする関数が別になっている例もあります。が、個人的には、記事中にある、もしもの例で `Scan()` がエラーも返す例のほうがわかりやすいと思います。

というのも、初めて `bufio.Scanner` のドキュメントを見た時は `Err()` の存在に気づいて無かったです。ただし、 https://golang.org/pkg/bufio/#Scanner の Example (Lines) とかを見れば `Err()` を使ったサンプルコードが書いてあるんですけどね。

余談ですけど、APIドキュメントに Example でサンプルコードがついているときは必ず見たほうが良いです。関数のシグネチャ見ただけでは気づかない使い方が説明されていることが多いので。

エラー処理は[Error handling and Go - The Go Blog](https://blog.golang.org/error-handling-and-go)のブログ記事も読みましょう。

あと `panic` と `recover` で例外もどきを実現しようとするのも止めましょう。私は `recover` は一度足りとも使ったことが無いです。

panic はエラーがほぼ起きないケースでerrorをreturnして呼び出し側で処理したくないケースは使うこともあります。panicすると標準エラー出力にエラーメッセージとスタックトレースが出力されて異常終了します。

Goのアプリケーションをsystemdから起動する場合は、panicするとjournalctlでログが見られてそちらで発生日時もわかるので、それでチェックしています。


## 繰り返す if err != nil {return err}

ひとつ前の「例外が(推奨され)ない」にまとめて書きました。
個人的には同じパターンで繰り返すほうが、ケースバイケースで書き方が違うより、読みやすいです。

## return nil, err → このerrorどこで発生したの？

```
if err != nil {
  return nil, fmt.Errorf("Some context: %v", err)
}
```

でコンテキストを追加するのがGo流らしいです。

でも個人的にはスタックトレースのほうが楽だと感じます。あと個人的にはエラーが起きた地点での関連する変数もログ出力したいので、自作のログライブラリでは
[func (l *LTSVLogger) ErrorWithStack(lv ...LV)](https://godoc.org/github.com/hnakamur/ltsvlog#LTSVLogger.ErrorWithStack) というメソッドを用意して、エラーが起きた箇所でメッセージと変数の値とスタックトレースを出力するようにしています。


## 関数より狭いスコープで defer

わかりやすい名前がつけられるケースならprivateの関数に切り出してそちらでdeferするようにします。

```
func myFuncHelper(filename string) (*dataType, error) {
  r, err := os.Open(filename)
  if err != nil {
    return err
  }
  defer r.Close()
  data, err := readDataFromReader(r)  // 実際にはもう少し複雑な処理
  if err != nil {
    return nil, err
  }
  return data, nil
}

func myFunc() error {
  data, err := myFunHelper(filename)
  if err != nil {
    return err
  }
  // その後の他の処理
}
```

あとエラーで抜けるケースが少なければdeferを使わずに `Close()` を呼べば良いと思います。

```
func myFunc() error {
  // ...
  r, err := os.Open(filename)
  if err != nil {
    return err
  }
  data, err := readDataFromReader(r)  // 実際にはもう少し複雑な処理
  if err != nil {
    r.Close()
    return err
  }
  r.Close()
}
```

「実際にはもう少し複雑な処理」と書いているので、

```
  if err != nil {
    r.Close()
    return err
  }
```

が何回も出てくるのでしょうが、多すぎと感じたら別の方法を考える感じで。


## structとC++/Javaのクラスとの違い

### コンストラクタがない
コンストラクタは無いので `NewSomething` とか `somepackage.New` のような関数を定義する習慣というのはその通りです。


### ゼロ初期化が避けられない

> structが外部に公開されるのならばstructは全てがゼロ初期化された場合にも正しく動くように常に設計しなくてはならないのです。

これは現実には無理だと思います。例えばファイル名のフィールドのstringが空文字だった時にはどのファイルを処理すれば良いかはわかりっこないです。zero valueでも構わないフィールドについては、zero valueだとどう解釈されるかをAPIドキュメントに書いておけば良い話です。それ以外は呼び出し側が設定する責任があるということで。


### コピーされるのが避けられない

Go言語自体にコピー防止の仕組みを入れる議論はあったようです。[runtime: add NoCopy documentation struct type? · Issue #8005 · golang/go](https://github.com/golang/go/issues/8005)

このスレッドの[コメント](https://github.com/golang/go/issues/8005#issuecomment-190753527)で実現する方法が紹介されています。

[valyala/fasthttp](https://github.com/valyala/fasthttp)ではこの技を使っていて
[fasthttp/nocopy.go](https://github.com/valyala/fasthttp/blob/master/nocopy.go)に `noCopy` の定義があり、 https://github.com/valyala/fasthttp/blob/45697fe30a130ec6a54426a069c82f3abe76b63d/http.go#L16-L45 に使用例があります。


## 型が後置

[Go's Declaration Syntax - The Go Blog](https://blog.golang.org/gos-declaration-syntax) で理由が説明されています。


## 1.0 が浮動小数点型にならない(時がある)

これは知りませんでした。

```
e := float64(a / 3.0)
```

と書けば回避できました。 https://play.golang.org/p/Y7_LUdQeeq

## 名前が…

golang で検索すればOKです。
