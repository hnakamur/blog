+++
Categories = []
Description = ""
Tags = ["golang","ltsv","logging"]
date = "2016-06-13T21:42:53+09:00"
title = "GoでLTSV形式でログ出力するライブラリを書いた"

+++
## なぜ書いたか
Goで高機能なサードパーティのログ出力ライブラリと言えば[Sirupsen/logrus](https://github.com/Sirupsen/logrus)が有名です。私も[doloopwhile/logrusltsv](https://github.com/doloopwhile/logrusltsv)と組み合わせてLTSV形式のログ出力するのに使っていました。

しかし、[logger のパフォーマンスについて \[Go\] - methaneのブログ](http://methane.hatenablog.jp/entry/2015/09/17/logger_%E3%81%AE%E3%83%91%E3%83%95%E3%82%A9%E3%83%BC%E3%83%9E%E3%83%B3%E3%82%B9%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6_%5BGo%5D)にも書かれていますが、[logrus.WithFields](https://godoc.org/github.com/Sirupsen/logrus#WithFields)は[Fields](https://godoc.org/github.com/Sirupsen/logrus#Fields)、つまり `map[string]interface{}` の値を渡す必要があります。これはGCに負荷をかけそうというのも気になりますが、Goのmapは順不同なのでログ出力の際にキーの順番がソースに書いた順番と必ずしも一致しないというのがイマイチだよなーと思っていました。

ログ出力ライブラリはライブラリによって違うものを使うのはよくないから、自作するよりメジャーなものを使うほうが良いと自重する思いもありました。

一方で、[Let’s talk about logging | Dave Cheney](http://dave.cheney.net/2015/11/05/lets-talk-about-logging)には賛同する点も多く、感銘を受けました。

で、一度自作してみようかなーと思っていたところに、[uber-go/zap](https://github.com/uber-go/zap)を見かけて、ログ出力の引数側を加工するという方式にインスパイアされ、ついに自分が欲しいものを自分で書いてみました。

* githubレポジトリ: [hnakamur/ltsvlog](https://github.com/hnakamur/ltsvlog)
* APIドキュメント: [ltsvlog - GoDoc](https://godoc.org/github.com/hnakamur/ltsvlog)

githubレポジトリのREADMEに使用例のコードがあります。

## ltsvlogの設計と実装

### ltsvlogのログレベル

[Let’s talk about logging | Dave Cheney](http://dave.cheney.net/2015/11/05/lets-talk-about-logging)にもありましたが、ログレベルが多すぎると使い分けで悩むので少ないほうが良いと私も思います。ただ、エラー以外にもなにかが成功したときに記録しておきたいことはあるので、ErrorとInfoは分けたほうが良いと思います。あと私はprintデバッグ信者なのでデバッグログ用のDebugレベルは必要です。

ということで、ltsvlogのログレベルはDebug, Info, Errorの3つです。

レベル毎に出力するかしないかの切り替えはDebugレベルのみ許可することにしました。InfoとErrorは本番運用時にもログ出力するものだけに使うという考えです。Debugレベルを出力するかどうかは[NewLTSVLogger](https://godoc.org/github.com/hnakamur/ltsvlog#NewLTSVLogger)でロガーを作るときに指定します。

またDebugレベルのログ出力は無効時には引数の評価もしたくないので、 [LTSVLogger.DebugEnabled()](https://godoc.org/github.com/hnakamur/ltsvlog#LTSVLogger.DebugEnabled)というメソッドも用意しました。使用例はこんな感じです。

{{< highlight go "linenos=inline,hl_lines=2 3" >}}
    if ltsvlog.Logger.DebugEnabled() {
        ltsvlog.Logger.Debug(ltsvlog.LV{"msg", "This is a debug message"},
            ltsvlog.LV{"key", "key1"}, ltsvlog.LV{"intValue", 234})
    }
{{< / highlight >}}

### スタックトレースの出力
[LTSVLogger.ErrorWithStack](https://godoc.org/github.com/hnakamur/ltsvlog#LTSVLogger.ErrorWithStack)でスタックトレース付きでログ出力できます。

LTSV形式ではログは1レコードで1行にする必要があります。[runtime.Stack](https://golang.org/pkg/runtime/#Stack)でスタックトレースをバッファに書いてくれるのですが、こちらは複数行の出力になっています。コードを適宜コピペして好きな形式で出力するようにしようかと思ったのですが、[src/runtime/mprof.go](https://golang.org/src/runtime/mprof.go?s=16037:16073#L574)のソースコードを見て思いとどまりました。

ということで、runtime.Stackの出力結果を加工するという方式で実装しています。
実際のコードは[ltsvlog/stack.go](https://github.com/hnakamur/ltsvlog/blob/v0.9.3/stack.go#L13-L60)です。コールスタックから不要な部分を取り除きつつ複数行から1行に変形するということで必ず元の長さより縮むので runtime.Stack で出力したバッファをそのまま使って変形しています。

[runtime.Stack](https://golang.org/pkg/runtime/#Stack)は呼び出し側がバッファを渡す必要があるのですが、サイズが小さいとスタックトレースが途中で切れてしまいます。デフォルトで 8192 というサイズにしたのですが、足りない場合は [NewLTSVLoggerCustomFormat](https://godoc.org/github.com/hnakamur/ltsvlog#NewLTSVLoggerCustomFormat) の引数でバッファサイズを指定できるようにしてます。

### 時刻とログレベルの出力
時刻はUTCでフォーマットは [time](https://golang.org/pkg/time/#pkg-constants)パッケージの `RFC3339Nano = "2006-01-02T15:04:05.999999999Z07:00"` に近いですが、ナノセカンドの部分は個人的な好みで9桁固定で出力するようにしました。

### 値の文字列化
上のコード例のようにラベルと値の組は[ltsvlog.LV](https://godoc.org/github.com/hnakamur/ltsvlog#LV)で指定します。

将来 LV にフィールドが追加されるかもしれないと防御的に実装するなら、以下のように書いたほうが良いわけですが、LabelとValueでLVということでフィールド追加するつもりは無いので `L:` や `V:` は省略して、上記の例のように書いています。

```go
    if ltsvlog.Logger.DebugEnabled() {
        ltsvlog.Logger.Debug(ltsvlog.LV{L: "msg", V: "This is a debug message"},
            ltsvlog.LV{L: "key", V: "key1"}, ltsvlog.LV{L: "intValue", V: 234})
    }
```

値の文字列化は https://github.com/hnakamur/ltsvlog/blob/v0.9.3/log.go#L175-L219 で行っています。[Type switches](https://golang.org/ref/spec#Type_switches)を使って、値の型に応じて文字列化しています。コメントにも書いていますが、byteとuint8、runeとuintは別のcaseとして書くとコンパイルエラーになったので諦めてuint8とuintのほうだけを残しています。

時刻とログレベルの出力形式と値の文字列化の方式を変えたい場合は関数を実装して[NewLTSVLoggerCustomFormat](https://godoc.org/github.com/hnakamur/ltsvlog#NewLTSVLoggerCustomFormat) の引数に指定すれば良いようにしてあります。

### グローバルロガー
標準の[log](https://golang.org/pkg/log/)パッケージではグローバルロガーの変数は非公開で[log.Print](https://golang.org/pkg/log/#Print)や[log.SetOutput](https://golang.org/pkg/log/#SetOutput)の関数で操作するようになっています。

私は関数を増やすのが嫌だったのとグローバルロガーの変数は公開しても良いのではと思ったのでそうしました。[ltsvlog.Logger](https://godoc.org/github.com/hnakamur/ltsvlog#pkg-variables)で参照できます。デフォルトでは標準出力にデバッグログありで出力するようになっています。デバッグログをオフにしたい場合はmain関数の最初のほうで(ログ出力する前に)以下のようにします。

```go
 ltsvlog.Logger = ltsvlog.NewLTSVLogger(os.Stdout, false)
```

ログ出力中に設定を変えることはないという想定です。

### LogWriterインタフェースと常に何も出力しないDiscard

後付ですが[ltsvlog.LogWriter](https://godoc.org/github.com/hnakamur/ltsvlog#LogWriter)というインタフェースも定義してみました。インタフェースは Logger という名前にしたいところでしたが、グローバルロガーに Logger という名前を使っていたので仕方なく LogWriter にしました。そして常に何も出力しない Discard というのも作りました。ただし、Infoなどの引数は評価されてしまうので実行コストが0なわけではないです。


## おわりに
[Benchmark result](https://github.com/hnakamur/ltsvlog#benchmark-result)に標準のlogパッケージと比較したベンチマーク結果を載せています。logパッケージよりは遅い手ですがほぼ同等だと言えると思います。

[hnakamur/ltsvlog](https://github.com/hnakamur/ltsvlog)はコード量も大したことないので、保守で困ることはないと楽観視しています。

ということで自分で書くライブラリやアプリケーションではどんどん使っていきたいと思います。
