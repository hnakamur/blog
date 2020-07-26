---
title: "pgregory.net/rapidを使ってGoでProperty Based Testingをやってみた"
date: 2020-07-26T16:54:19+09:00
---

## はじめに

以前から Go で Property Based Testing をやってみたいと思っていたのですが
@objectxplosive さんの [ツイート](https://twitter.com/objectxplosive/status/1284837906520006657)
を見て [pgregory.net/rapid package · pkg.go.dev](https://pkg.go.dev/pgregory.net/rapid?tab=doc) を試してみたのでメモです。

## Property Based Testing について

@dgryski さんの [ツイート](https://twitter.com/dgryski/status/1277647928690008064) で紹介されていた
[The lazy programmer's guide to writing thousands of tests - Scott Wlaschin - YouTube](https://www.youtube.com/watch?v=IYzDFHx6QPY&feature=emb_logo) が分かりやすかったです。
この動画では Go 言語ではなく別の言語 (Haskell?) を使って説明されています。

通常のユニットテストではサンプルの入力データをテストケースとして用意し、それをテスト対象に投入して出力や結果を確認します。
境界値などを考えながらテストケースを準備するわけですが、開発者が予想もしないような入力は漏れてしまいがちです。

Property Based Testing はランダムなテストケースを生成してテストを実行することで想定外の入力もカバーするようなテスト手法です。
予め自分で用意したテストケースの場合はその個々のケースに対して出力を事前に準備しておくことができます。

しかし、ランダムなテストケースに対しては事前には準備できないので、入力に対して出力が必ず満たす法則や特性のようなものを考えて、それを満たすことを確認します。

その特性が property で、なので Property Based Testing というわけです。

例えば足し算の場合は以下の特性が考えられます。

* x + y = y + x (交換法則, commutativity) 
* x + 1 + 1 = x + 2 (結合法則, associativity)
* x + 0 = x (同一性法則(※1) , identity)

※1: 検索しても一般的な訳語が見つけらなかったので今適当につけました。

上の 3 つは加算に対する Property Based Test の最終形ですが、上記の動画では順を追って説明されているので、気になる方はぜひご覧ください。

さらに、動画では Shrinking についても説明されています。

ランダムな入力値で property を満たさないケースが発見された後、その失敗を再現する最小限の入力を探すことをそう呼ぶようです。
[Shrinking](https://propertesting.com/book_shrinking.html) にも説明がありました。

テスト対象が状態マシンの場合、失敗が見つかったときの入力のステップ数が膨大な場合もありえます。
すると再現テストを動かすのに時間がかかって効率が悪いので、最小化するということのようです。

## `pgregory.net/rapid` パッケージ

レポジトリは [flyingmutant/rapid: Rapid is a Go library for property-based testing that supports state machine ("stateful" or "model-based") testing and fully automatic test case minimization ("shrinking")](https://github.com/flyingmutant/rapid) にあります。
Go で書かれていてライセンスは MPL-2.0 です。
2020-07-26 時点ではバージョン v0.4.0 です。
README によると今はアルファで、今後 API が非互換で変更される可能性があるとのことです。

### stateless な property based test

API ドキュメントを参考に上記の動画で説明されていた足し算のテストを書いてみたのが
[property-based-test-example/add_test.go](https://github.com/hnakamur/property-based-test-example/blob/master/add_test.go)
です。

一部を以下に抜粋します。

```go
func TestAdd(t *testing.T) {
  t.Run("commutativity", rapid.MakeCheck(func(t *rapid.T) {
    x := rapid.Int().Draw(t, "x").(int)
    y := rapid.Int().Draw(t, "y").(int)
    result1 := add(x, y)
    result2 := add(y, x)
    if result1 != result2 {
      t.Fatalf("add must be commutative, x=%d, y=%d, result1=%d, result2=%d", x, y, result1, result2)
    }
  }))
```

動画では足し算の特性 (property) を表す関数をテストライブラリに渡すという方式でしたが、`pgregory.net/rapid` パッケージでは Go のテストとして標準的な書き方に合わせていて、失敗する場合は `t.Errorf` などを呼ぶという API となっています。

ただし、 `*testing.T` とは別に独自の `*rapid.T` という型があって、そちらの `Errorf` などのメソッドを呼ぶのが Go の通常のテストとは違うところです。

またランダムな入力値は [rapid.Int()](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Int) などで
[\*rapid.Generator](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Generator)
のインスタンスを作成し、 [Draw](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Generator.Draw) メソッドや [Example](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Generator.Example) メソッドで値を生成します。

上記の `add_test.go` はそのままだとテストが通る状態ですが、 [add.go](https://github.com/hnakamur/property-based-test-example/blob/master/add.go) の `add` 関数の実装を `return x - y` などとわざと間違えてテストを実行してみると以下のようになります。

```
$ go test -v
=== RUN   TestAdd
=== RUN   TestAdd/commutativity
    TestAdd/commutativity: add_test.go:10: [rapid] failed after 0 tests: add must be commutative, x=0, y=-1, result1=1, result2=-1
        To reproduce, specify -run="TestAdd/commutativity" -rapid.seed=1595763150563185679
        Failed test output:
    TestAdd/commutativity: add_test.go:11: [rapid] draw x: 0
    TestAdd/commutativity: add_test.go:12: [rapid] draw y: -1
    TestAdd/commutativity: add_test.go:16: add must be commutative, x=0, y=-1, result1=1, result2=-1
=== RUN   TestAdd/associativity
    TestAdd/associativity: add_test.go:19: [rapid] OK, passed 100 tests (48.497µs)
=== RUN   TestAdd/identity
    TestAdd/identity: add_test.go:27: [rapid] OK, passed 100 tests (42.924µs)
--- FAIL: TestAdd (0.00s)
    --- FAIL: TestAdd/commutativity (0.00s)
    --- PASS: TestAdd/associativity (0.00s)
    --- PASS: TestAdd/identity (0.00s)
FAIL
exit status 1
FAIL    github.com/hnakamur/property-based-test-example 0.007s
```

`To reproduce, ` の後に今回の失敗を再現するための `go test` の引数を出力してくれています。
上記の例だと以下のように実行すれば再現できるというわけです。

```
go test -run="TestAdd/commutativity" -rapid.seed=1595763150563185679
```

今回の例は実装が単純なので間違いは明らかですが、実際のケースではデバッグログ出力などを追加して再現テストを実行するというのを繰り返していけば、問題の原因が調査できます。


### stateful な property based test

上記の `add` 関数は stateless でしたが、 stateful なテスト対象の場合は [StateMachine](https://pkg.go.dev/pgregory.net/rapid?tab=doc#StateMachine) というインタフェースを実装した構造体を定義してテスト対象をラップします。

[Run(m \*SateMachine) func(\*T)](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Run) 関数の
[例](https://pkg.go.dev/pgregory.net/rapid?tab=doc#example-Run-Queue) を展開するとコード例が見られます（リンク先に飛んで少し上にスクロールバックすると `Example (Queue)` というのがありますのでクリックして展開してください）。

この例では `Queue` 構造体がテストの対象ですが、テストを実行するための状態遷移マシンとして `queueMachine` という構造体を定義しています。

`queueMachine` の `Init` メソッドで初期化処理を実装します。
初期化が不要な場合は `Init` メソッドは省略可能です。

また後処理が必要な場合は `Cleanup` メソッドに実装します。

なんらかのアクション（操作）を行った後、状態遷移マシンがあるべき状態を満たしているかを確認する処理を `Check` メソッドに実装します。

それ以外のメソッドに各種アクションを実装します。

`Run` 関数のドキュメントにある通り、最初に `Init` を呼んで `Check` で確認し、その後はランダムにアクションを呼んで `Check` で確認を繰り返します。
`Cleanup` メソッドがあれば、最後に後処理の際に呼び出します。

ドキュメントでは概要ということで `for` は無限ループになっていますが、実際は十分な回数を実行したあと終了するようになっています。

#### 状態遷移マシンは初期パラメータごとに型を定義する必要あり

[Run(m \*SateMachine) func(\*T)](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Run) 関数のドキュメントに書かれていますが、 `Init` の前に状態遷移マシンを生成する疑似コードは
`m := new(StateMachineType)` となっています。

つまり引数の `m *StateMachine` のインスタンスがそのまま使われるわけではなく、その型情報を使って reflect でインスタンスを生成するようになっています。 `m` の中のデータは無視されると明記されています。

ですので、初期パラメータを変えたい場合はそれごとに型を定義する必要があります。

実際の例がこちらです。 [all_actions_test.go#L13-L108](https://github.com/hnakamur/whispertool/blob/ec224ff12e8097d2efe0fbd266ce682add9c90b2/internal/compattest/all_actions_test.go#L13-L108)

長いので抜粋するとこんな感じです。

```go
type allActionsMachineSmallSum0 struct{ allActionsMachine }

func (m *allActionsMachineSmallSum0) Init(t *rapid.T) {
  m.allActionsMachine.retentionDefs = "1s:2s,2s:4s,4s:8s"
  m.allActionsMachine.aggregationMethod = "sum"
  m.allActionsMachine.xFilesFactor = 0.0
  m.allActionsMachine.Init(t)
}

type allActionsMachineSmallSum05 struct{ allActionsMachine }

func (m *allActionsMachineSmallSum05) Init(t *rapid.T) {
  m.allActionsMachine.retentionDefs = "1s:2s,2s:4s,4s:8s"
  m.allActionsMachine.aggregationMethod = "sum"
  m.allActionsMachine.xFilesFactor = 0.5
  m.allActionsMachine.Init(t)
}
```

#### 独自の型のランダムな入力値は `rapid.Custom` 関数を使って生成する

上記の足し算のテストでの失敗例を見ると、その時の入力値が出力されます。

```
    TestAdd/commutativity: add_test.go:11: [rapid] draw x: 0
    TestAdd/commutativity: add_test.go:12: [rapid] draw y: -1
```

独自の型の値の場合は [Custom](https://pkg.go.dev/pgregory.net/rapid?tab=doc#Custom) 関数でカスタムのジェネレーターを定義してそれを使うと、失敗時の値が同様に出力されるので便利です。

[Custom 関数の例](https://pkg.go.dev/pgregory.net/rapid?tab=doc#example-Custom) にシンプルな例があります。

私が書いた実際の例がこちらです。
[generator_test.go#L39-L56](https://github.com/hnakamur/whispertool/blob/ec224ff12e8097d2efe0fbd266ce682add9c90b2/internal/compattest/generator_test.go#L39-L56)

```go
func NewPointsForArchiveGenerator(db *WhispertoolDB, archiveID int) *rapid.Generator {
  return rapid.Custom(func(t *rapid.T) Points {
    var points Points
    now := whispertool.TimestampFromStdTime(clock.Now())
    archiveInfo := db.ArciveInfoList()[archiveID]
    step := archiveInfo.SecondsPerPoint()
    oldest := now.Add(-archiveInfo.MaxRetention()).Add(step)
    fillRatio := rapid.Float64Range(0, 1).Draw(t, "fillRatio").(float64)
    for timestamp := oldest; timestamp <= now; timestamp = timestamp.Add(step) {
      ptFillRatio := rapid.Float64Range(0, 1).Draw(t, "ptFillRatio").(float64)
      if ptFillRatio < fillRatio {
        v := rapid.Float64().Draw(t, "v").(float64)
        points = append(points, whispertool.Point{Time: timestamp, Value: whispertool.Value(v)})
      }
    }
    return points
  })
}
```

失敗時には値は [fmt](https://golang.org/pkg/fmt/) パッケージの書式 `%#v` で [出力されます](https://github.com/flyingmutant/rapid/blob/v0.4.0/engine.go#L351)。

そこでテストのときのみ `%#v` の出力形式を変えるために、テスト専用の構造体を用意し [fmt.Formatter](https://golang.org/pkg/fmt/#Formatter) インターフェースの `Format` メソッドを実装するようにしてみました。

[generator_test.go#L10-L14](https://github.com/hnakamur/whispertool/blob/ec224ff12e8097d2efe0fbd266ce682add9c90b2/internal/compattest/generator_test.go#L10-L14)

```go
type Points whispertool.Points

func (pp Points) Format(f fmt.State, c rune) {
  f.Write([]byte(whispertool.Points(pp).String()))
}
```

## Property Based Testing で既存の別実装との挙動の互換性を確認する使い方もある

上記の動画でも例として紹介されていますが、テスト対象の実装と同じ実装をテスト側にも書いて同じ結果になることを確認するのは無意味です。

ですが、既存の別実装があってそれが正しい挙動をすると分かっている場合、自分の代替実装がその別実装と同じ挙動をするということを Property Based Testing で確認するのは有効な活用方法です。
上記の動画では test oracle と呼ばれていました。

## おわりに

pgregory.net/rapid パッケージはまだアルファとのことですが、手軽に使えることが分かったので今後活用していこうと思います。
