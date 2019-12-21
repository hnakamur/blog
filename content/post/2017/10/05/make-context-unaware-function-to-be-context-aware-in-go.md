+++
title="Goでcontext非対応の関数をcontext対応にするラッパ関数を書いた"
date = "2017-10-05T20:32:00+09:00"
tags = ["go"]
categories = ["blog"]
+++


## はじめに

Goの [net/http.Server](https://golang.org/pkg/net/http/#Server) でグレースフルシャットダウンを行う際の注意点として
[Go1.8のGraceful Shutdownとgo-gracedownの対応 - Shogo's Blog](https://shogo82148.github.io/blog/2017/01/21/golang-1-dot-8-graceful-shutdown/)
のブログ記事で以下の3点が紹介されていました。

    * `Server.Shutdown` を使う( `Serer.Close` もあるけど、そっちはGracefulではない)
    * `Server.Serve` は **シャットダウンが始まる** とすぐに制御を返す(**シャットダウンが終わる** とではない)
    * `Server.Shutdow` は **シャットダウンが終わる** と制御を返す(**シャットダウンが始まる** とではない)

これに対応するために [func (*Server) Serve](https://golang.org/pkg/net/http/#Server.Serve) をgoroutineで実行し、メインのコードでシグナルを待つという書き方が紹介されており、ありがたく真似させていただいていました。

しかし、 https://twitter.com/kaoriya/status/912553754171338758 のツイートで以下のような指摘がありました。

    goroutineの中でServeを呼んでメインの方でシグナルまってる。これだとシャットダウン以外の理由でServeが停止した時に、シグナル待ちでプログラム終わらないんじゃないか? 

あー、確かに。一度検証してみないとなー、と思いつつしてませんでした。

そこへ、今日
[Video: Ways To Do Things - Peter Bourgon #GoSF - Golang News](https://golangnews.com/stories/2744-video-ways-to-do-things-peter-bourgon-gosf)
という動画をツイッターで知って見てみたのですが、
その中で
[github.com/oklog/oklog/pkg/group](https://godoc.org/github.com/oklog/oklog/pkg/group)
というパッケージが紹介されていました。

これは標準ライブラリの [context](https://golang.org/pkg/context/) パッケージに対応していないライブラリで動作している goroutine を停止する枠組みを提供するもので、以下のような型とメソッドを持っています。

```go
type Group
	func (g *Group) Add(execute func() error, interrupt func(error))
	func (g *Group) Run() error
```

## Goでcontext非対応の関数をcontext対応にする

なるほどー便利そうだなーと思ったのですが、逆に context 非対応のライブラリの関数をラップして context 対応にするほうが良いなと思い当たりました。

[WithCancel](https://golang.org/pkg/context/#WithCancel) で作った `context.Context` を渡して実行しておけば、停止したいときは `WithCancel` の戻り値の `cancel` を呼ぶだけで良いのが楽です。

特に、複数の goroutine を実行していたり goroutine からさらに別の goroutine を実行していたりした場合に、それぞれ個別の停止方法を呼び出す場合は context を使わない場合はかなり面倒だと推測します。

ということで書いてみました。

* ソース: [hnakamur/contextify](https://github.com/hnakamur/contextify)
* ドキュメント: https://godoc.org/github.com/hnakamur/contextify

ソースは 53 行と短いので、以下に引用します。
公開APIは `Contextify` という関数1つだけで、これは `context` 非対応の実行用関数 `run` とキャンセルを行う関数 `cancel` を受け取って、 `context` 対応の関数を返すというものです。

```go {linenos=table}
// Package contextify provides a utility function to convert a context-unaware
// run function and a cancel function to a context-aware function.
package contextify

import "context"

// Contextify convert a context-unaware run function and a cancel function to
// a context-aware function.
//
// If context.Context is not cancelled before run() finishes, the return value
// function waits for run() to be finished and returns the return value of run().
//
// If context.Context is cancelled before run() finishes, the return value
// function waits for both the run() and cancel() to be finished.
//
// If pickError is nil, the first non-nil error will be retruned of the return
// value of run(), cancel(), and context.Context.Err().
// You can change this behavior with writing a function to pick a desired error
// and pass it to the pickError argument.
func Contextify(run func() error, cancel func() error,
	pickError func(errFromRun, errFromCancel, errFromContext error) error) func(context.Context) error {

	return func(ctx context.Context) error {
		var errFromRun error
		done := make(chan struct{})
		go func() {
			errFromRun = run()
			close(done)
		}()

		select {
		case <-done:
			return errFromRun
		case <-ctx.Done():
			errFromCancel := cancel()
			<-done
			if pickError == nil {
				pickError = defaultPickError
			}
			return pickError(errFromRun, errFromCancel, ctx.Err())
		}
	}
}

func defaultPickError(errFromRun, errFromCancel, errFromContext error) error {
	if errFromRun != nil {
		return errFromRun
	}
	if errFromCancel != nil {
		return errFromCancel
	}
	return errFromContext
}
```

`run` が終わるのを待つために 25行目で `done` というチャンネルを作っています。

キャンセルが行われない (上記の `WithCancel` の戻り値の `cancel` が実行されない) まま `run` が終了した場合は、32行目の `case` が処理されて `run` の戻り値のエラーを返します。

一方 `run` が終わる前にキャンセル依頼が来た場合は、 34行目の `case` が処理されて、元々受け取った `cancel` 関数を呼び出して `cancel` 関数の実行完了を待ちます。
その後 `done` チャンネルからの受信を待つことで `run` 関数の終了を待ちます。

こうすることで、当初指定された `run` と `cancel` の両方が終わるまで待つことができます。

`Contextify` 関数の第3引数は `run`, `cancel`, `ctx.Err()` のどのエラーを返すかを選択するためのものです。 `nil` を指定するとデフォルトの処理として上記の順番で最初の非 `nil` なエラーを返します。
違う動きにしたい場合は関数を書いて渡せばよいようになっています。

## 使用例

`net/http.Server` でグレースフルシャットダウンを行う場合の使用例を示します。

```go {linenos=table}
ctx, cancel := context.WithCancel(context.Background())
go func() {
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)

	s := <-c
	log.Printf("received signal, %s", s)
	cancel()
	log.Printf("cancelled context")
}()

http.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
	w.Write([]byte("Hello, example http server\n"))
})
s := http.Server{Addr: ":8080"}
run := contextify.Contextify(func() error {
	return s.ListenAndServe()
}, func() error {
	return s.Shutdown(context.Background())
}, nil)
err := run(ctx)
if err != nil {
	log.Printf("got error, %v", err)
}
log.Print("exiting")
```

17行目が実行用の処理で、19行目がキャンセルつまりグレースフルシャットダウンを開始する処理です。

21行目では `Contextify` 関数の戻り値の `run` に1行目で `WithCancel` で作った `ctx` を引数に渡して実行します。

2～10行目の goroutine では `os.Interrupt` シグナルを受け取ったら、1行目の `WithCancel` の戻り値の `cancel` 関数を呼び出すことでキャンセルを実行しています。

すると 17行目の処理と19行目の処理の両方が終わるのを待ってから 22行目以降の処理が行われます。

実際に試しやすいように
[example/httpserver/main.go](https://github.com/hnakamur/contextify/blob/master/example/httpserver/main.go)
という例も含めています。

処理の関数とキャンセルの関数のどちらが後に戻るかを簡単に変えてテストするために
[example/sleep/main.go](https://github.com/hnakamur/contextify/blob/master/example/sleep/main.go)
という例も作りました。

起動後何もせずに5秒待つと、キャンセル無しで終了するケースになります。

起動後5秒以内に Ctrl-C を押すと、キャンセルを依頼したほうは1msですぐに戻って来て、キャンセル依頼を受けたほうは受けてから1秒で戻るようになっています。

一方 `-trigger` オプションに `2s` と指定して起動して5秒以内に Ctrl-C を押すと、今度はキャンセルを依頼したほうが後に終わるようになります。

## おわりに

このライブラリを使えば `context` 非対応の関数で処理本体とキャンセル処理のどちらが後に終わるかを気にする必要はなくなります。
気にすることが減るのは良いことなので今後使っていこうと思います。
