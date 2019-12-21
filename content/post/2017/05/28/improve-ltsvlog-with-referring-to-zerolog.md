+++
title="zerologを参考にしてltsvlogを改良してみた"
date = "2017-05-28T21:52:00+09:00"
tags = ["ltsv", "go", "benchmark"]
categories = ["blog"]
+++


## はじめに

こちらも少し前の話なのですがブログに書いておきます。

[( ꒪⌓꒪)さんのツイート: "zero allocation をうたう logger #golang / “GitHub - rs/zerolog: Zero Allocation JSON Logger” https://t.co/3t2qt9Qgbm"](https://twitter.com/mattn_jp/status/864993516149022720) というmattnさんのツイートを見かけて
[rs/zerolog: Zero Allocation JSON Logger](https://github.com/rs/zerolog)
zerologの仕組みを調べ、自作のLTSVログ出力ライブラリ
[hnakamur/ltsvlog: a minimalist LTSV logging library in Go](https://github.com/hnakamur/ltsvlog)
を改善してみたメモです。

## zerologの仕組み

zerologはJSON形式でログ出力する構造化ログライブラリです。
[zerolog - GoDoc](https://godoc.org/github.com/rs/zerolog)
を見ると `Logger` の `Info` や `Debug` を呼ぶと `*Event` が返されるようになっています。

そして `*Event` の `Str` メソッドにキーと値を指定して呼ぶと

[zerolog/event.go#L110-L117 at bf4b44614c4fe42f071ba7162e4898edaef8fa1e · rs/zerolog](https://github.com/rs/zerolog/blob/bf4b44614c4fe42f071ba7162e4898edaef8fa1e/event.go#L110-L117)

のように `[]byte` のバッファに文字列を追加するようになっています。

最後に `Msg` か `Msgf` メソッドを呼び出すと指定したメッセージをバッファに追加した上でログ出力されます。

そして `[]byte` のバッファを
[zerolog/event.go#L10-L16 at bf4b44614c4fe42f071ba7162e4898edaef8fa1e · rs/zerolog](https://github.com/rs/zerolog/blob/bf4b44614c4fe42f071ba7162e4898edaef8fa1e/event.go#L10-L16)
のように `sync.Pool` で管理して再利用することでゼロアロケーションを実現しているという仕組みになっていました。

## ベンチマークでメモリ割り当てや実行速度の改善具合を調べる

以下の記事を参考にしながら、いろいろ試行錯誤して自作のログライブラリを改善してみました。

* [DSAS開発者の部屋:Goでアロケーションに気をつけたコードを書く方法](http://dsas.blog.klab.org/archives/52191778.html)
* [Big Sky :: golang でパフォーマンスチューニングする際に気を付けるべきこと](https://mattn.kaoriya.net/software/lang/go/20161019124907.htm)
* [GolangでFlame Graphを描く | SOTA](http://deeeet.com/writing/2016/05/29/go-flame-graph/)

ベンチマーク比較ツールの
[rsc/benchstat: Benchstat computes and compares statistics about benchmarks.](https://github.com/rsc/benchstat)
は
[benchstat - GoDoc](https://godoc.org/golang.org/x/perf/cmd/benchstat)
に移動していました。
さらに
[benchcmp - GoDoc](https://godoc.org/golang.org/x/tools/cmd/benchcmp)
というのもありました。
改善前後の比較という意味でbenchcmpのほうが名前がわかりやすいと思ってしばらくそちらを使っていました。が、今改めてドキュメントを見比べてみると、ベンチマークを複数回実行して比較するにはbenchstatのほうが良さそうです。

benchstatは以下のコマンドでインストールします。

```console
go get -u golang.org/x/perf/cmd/benchstat/...
```

ベンチマークを書いたら改善前の状態で一旦ベンチマークを取ります。

```console
go test -count=10 -run=NONE -bench . -benchmem -cpuprofile=cpu-old.prof | tee old.log
```

コードを改善したら再度ベンチマークを取ります。

```console
go test -count=10 -run=NONE -bench . -benchmem -cpuprofile=cpu-new.prof | tee new.log
```

benchstatを実行して改善度合いを確認します。

```console
hnakamur@express:~/go/src/github.com/hnakamur/ltsvlog$ benchstat old.log new.log
name            old time/op    new time/op    delta
Info-2            1.90µs ± 1%    1.60µs ± 1%     -16.00%  (p=0.000 n=9+10)
ErrWithStack-2    13.9µs ± 1%    18.3µs ± 4%     +31.11%  (p=0.000 n=9+9)

name            old alloc/op   new alloc/op   delta
Info-2             32.0B ± 0%      0.0B         -100.00%  (p=0.000 n=10+10)
ErrWithStack-2     80.0B ± 0%   8260.0B ± 0%  +10225.00%  (p=0.000 n=10+7)

name            old allocs/op  new allocs/op  delta
Info-2              2.00 ± 0%      0.00         -100.00%  (p=0.000 n=10+10)
ErrWithStack-2      4.00 ± 0%      3.00 ± 0%     -25.00%  (p=0.000 n=10+10)
```

またgo-torchでフレームグラフのsvgファイルを出力してブラウザなどで表示し、ベンチマークで実行しているコードのどの部分が主に時間がかかっているかを確認します。

go-torchは

```console
go get -u github.com/uber/go-torch/...
```

でインストールして

```console
go-torch -f torch-new.svg cpu-new.prof 
```

で実行します。

## ltsvlogのAPIの設計メモ

### InfoとDebugはEventのLogメソッドでログ出力

zerologはEventのMsgかMsgfメソッドを呼び出すとメッセージを追加したうえでログ出力するというAPIになっています。私はメッセージの位置をもっと前にしたいのでログ出力にはLogという専用のメソッドを追加することにしました。

### エラーにスタックトレースとキーバリューを付与して呼び出しの上位階層でログ出力

エラーは1回発生したら、理想的には1回だけログに書くようにしたいところです。

Goのコアチームでは呼び出し階層の上位でエラーを受け取ったら
`return fmt.Errorf("failed to connect to server, err=%v", err)`
のような感じでエラーのコンテキスト情報を追加して1段ずつ上に上げるのが定番のようです。

ですが、私はスタックトレースのほうが便利だと思うのでスタックトレースを使っています。
上記のような文言を他と重複せずに付け分けるのは大変ですがスタックトレースがあればどういう経路で呼び出されたか一目瞭然なのでありがたいです。

また、エラーが発生箇所でエラーに関連する変数の値も出力したいです。
これらを総合するとエラーにスタックトレースや関連する変数の値を付与しておいて、呼び出し階層の上位にエラーを返していき、上位でそれらの情報をログ出力できると良いと思います。
構造化ログならぬ構造化エラーとでも言いましょうか。

[pkg/errors: Simple error handling primitives](https://github.com/pkg/errors) ではスタックトレースの付与は出来るのですが、キーバリューの追加はデザインディシジョンとして含めない決定がされていました。知らずにイシューを立ててコメントを受けてその事実を知りました。

今回の方式はGoのコアチームの流儀と違うので導入すべきか悩んだのですが、ついに導入してみました。
`return ltsvlog.Err(err).String("key", "value").Stack("")` のような感じでエラーを返して、
呼び出し階層の上位で `ltsvlog.Logger.Err(err)` でログ出力します。

その場でログ出力する場合はこれらを組み合わせて
`ltsvlog.Logger.Err(ltsvlog.Err(err).String("key", "value").Stack(""))` でログ出力します。

LTSVの1項目としてキー・バリューを出力できるので、後からログを検索しやすいのが利点だと考えています。

個々のエラーログ呼び出しをもうちょっとコンパクトに書けるようにできないかと、Goのコアチームの方式と共存できないかは今後考えてみたいと思います。

## ltsvlogの速度改善のメモ

### 日時のフォーマット

フレームグラフを作ってみてみると日時のフォーマットはかなり重い処理でした。
[uber-go/zap: Blazing fast, structured, leveled logging in Go.](https://github.com/uber-go/zap) では開発時は日時をフォーマットし、プロダクションではタイムスタンプを出力することで高速化を図っていました。
でも私としては常に日時をフォーマットのほうが好みです。
Goの標準ライブラリのlogパッケージではtimeのFormatを使わず、固定フォーマットで年月日時分秒をゼロパディングして文字列化する処理をlogパッケージのプライベート関数itoaで行って高速化を図っていました。
ltsvlogはこのコードをコピーして改変して利用しています。

logのitoaは1の位から始めて次は10の位と順番に数値の文字列を埋めていくようになっています。
そして年月日時分秒のゼロパディングありの固定長とファイルの行数のゼロパディング無しの可変長の両方の用途があるため、一旦内部バッファで文字列を生成してから出力先にコピーしなおしていました。

ゼロパディングありの固定長の用途に限定すれば、最初から出力先で文字列を組み立てるようにすると最後のコピーが無くせて12%前後の高速化が出来ました。
[log: Optimize formatting time in header with avoiding buffer copy in ioa (Ic4072cd8) · Gerrit Code Review](https://go-review.googlesource.com/c/42891/)
でGo標準ライブラリのlogパッケージにもフィードバックを送っています（取り込まれるかは未定）。

ltsvlogではログの日時のタイムゾーンはUTC固定で精度もマイクロ秒に固定しています。
タイムゾーンを出力するにはtimeパッケージのFormatメソッドを使うしかなさそうなので避けたいのと、タイムゾーンによってはサマータイムがあってややこしいので、システム的な日時はUTC固定のほうが良いという判断にしました。

また精度も短時間の処理の前後でログ出力するとミリ秒では足りないケースもありそうで、かといってナノ秒までは不要だろうということでマイクロ秒固定にしました。速度的にもナノ秒まで出すよりマイクロ秒のほうが速かったです。記録取ってなかったので改善率はうろ覚えですが1～3%ぐらいだった気がします。

### sync.Poolは使うとかえってメモリ割り当てが増えて遅くなることもあった

まず基本方針として、文字列を作るときにメモリ割り当てを減らすには、個々の文字列を作ってから `+` 演算子や `fmt.Sprintf` で連結するのではなく、 `[]byte` のバッファに対して `buf = append(buf, "string"...)` や `strconv - The Go Programming Language](https://golang.org/pkg/strconv/) の `AppendInt` のような関数を使うのが良いようです。これは私が試行錯誤した範囲ではそのようだというところで、違う場合もあるかもしれません。

で、次は `[]byte` のバッファを毎回割り当てるのではなく `sync.Pool` を使って再利用するのが良いようです。

ですが、
[ltsvlog/log.go#L335-L348 at v1.5.1 · hnakamur/ltsvlog](https://github.com/hnakamur/ltsvlog/blob/v1.5.1/log.go#L335-L348)

```go
func appendUTCTime(buf []byte, t time.Time) []byte {
	t = t.UTC()
	tmp := []byte("0000-00-00T00:00:00.000000Z")
	year, month, day := t.Date()
	hour, min, sec := t.Clock()
	itoa(tmp[:4], year, 4)
	itoa(tmp[5:7], int(month), 2)
	itoa(tmp[8:10], day, 2)
	itoa(tmp[11:13], hour, 2)
	itoa(tmp[14:16], min, 2)
	itoa(tmp[17:19], sec, 2)
	itoa(tmp[20:26], t.Nanosecond()/1e3, 6)
	return append(buf, tmp...)
}
```

のtmpをsync.Poolを使うようにしてみたらメモリ割り当てがむしろ増えて速度も遅くなってしまいました。
関数内で確保して使い終わるケースでは素直に確保するほうが良いようです。
Goのコンパイラで出力されるGoのアセンブラのコードを見てみれば良いのでしょうが、そこまではしていません。

## おわりに

zerologの手法を真似することで、ltsvlogでもシンプルなケースではメモリ割り当てゼロでログ出力できるようになりました。

[hnakamur/go-log-benchmarks](https://github.com/hnakamur/go-log-benchmarks) に私が気になるログライブラリのベンチマーク結果を載せています。ベンチマークと言ってもそれぞれのライブラリで出力している内容が異なるのでフェアな比較ではありませんが、おおまかな目安としては良いかなということで。
