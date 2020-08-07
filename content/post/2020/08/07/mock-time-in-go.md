---
title: "Goで時刻をモックする"
date: 2020-08-07T09:56:52+09:00
---
## はじめに

初めてこの話題を聞いたのは [umeda.go #2 で発表してきた - kawaken's blog](https://kawaken.hateblo.jp/entry/2017/07/31/150015) でした（スライドは [Goの時刻に関するテスト](https://www.slideshare.net/kawaken/golang-testingfortime-77668188)）。
その節は良いお話をありがとうございました。

この時点ではGoのアプリケーションのビルド時にGoの標準ライブラリーのコードを差し替えるのは別の用途で試して便利だったものの、時刻に関するテストは自分では試してませんでした。

その後、自分でも試そうと思い、紹介されていたライブラリー以外のライブラリーも調べてみたのでメモです。

[Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) の記事がとても詳しくて素晴らしいです。

こちらのサンプルコードをベースにしたもので検証してみました。

## `time.Now()` だけならライブラリーを使わない選択もある

[Goの時刻に関するテスト](https://www.slideshare.net/kawaken/golang-testingfortime-77668188) でも説明されていますが `time.Now()` を差し替えるだけならサードパーティのライブラリーを使わない選択もあり得ます。

[Stubbing Time.Now() in golang - labs.yulrizka.com](https://labs.yulrizka.com/en/stubbing-time-dot-now-in-golang/) にも詳しい説明がありました。

## 時刻をモックすることの難しさ

[Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) の記事がとても参考になりました。

`time.Now()` を呼び出している個所の他に、 `time.Timer` や `time.Ticker` のチャンネルを待っていたり `time.Sleep()` を呼んでいるコードがあると、時刻をモックするのは大変になってくるんですね。

モックで時刻を設定したあと時刻を進める際に、`time.Timer` や `time.Ticker` のチャンネルに適宜時刻を送り、 `time.Sleep()` でブロックしていたコードを実行させるのが理想なのですが、なかなか難しいということがわかりました。

### time.Ticker のチャンネルについて

モックで時刻を進めて `time.Timer` の発動時刻を過ぎていたらチャンネルに時刻を送るのは良いとして、 `time.Ticker` のほうは 2 回以上の tick を過ぎていたらどうするべきでしょうか。

そもそもモックではなく実時間の場合に `time.Ticker` のチャンネルから tick を受け取る前に次の tick が来てしまったらどうなるのでしょうか。

[NewTicker](https://golang.org/pkg/time/#NewTicker) の API ドキュメントには記載がありませんが、関数名の [NewTicker のリンク](https://golang.org/src/time/tick.go?s=706:740#L11) をクリックして実装を見ると、以下のようなコメントとコードがありました。

```go
	// Give the channel a 1-element time buffer.
	// If the client falls behind while reading, we drop ticks
	// on the floor until the client catches up.
	c := make(chan Time, 1)
	t := &Ticker{
		C: c,
		r: runtimeTimer{
			when:   when(d),
			period: int64(d),
			f:      sendTime,
			arg:    c,
		},
	}
```

バッファーサイズ 1 でチャンネルを作っていて、受け取り側が追い付かない場合は残りの tick は捨てられるとのことです。

[src/time/sleep.go at go1.14.5](https://github.com/golang/go/blob/go1.14.5/src/time/sleep.go#L130-L140)
で `sendTime` 関数でチャンネルに時刻を送る処理の実装を見ると確かにそのようになっています。

```go
func sendTime(c interface{}, seq uintptr) {
	// Non-blocking send of time on c.
	// Used in NewTimer, it cannot block anyway (buffer).
	// Used in NewTicker, dropping sends on the floor is
	// the desired behavior when the reader gets behind,
	// because the sends are periodic.
	select {
	case c.(chan Time) <- Now():
	default:
	}
}
```

### モックの時刻を進めた後、チャンネルを受信するgoroutineを動かす必要がある

[Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) の "Letting other goroutines run" の項に詳しく書かれています。

Timer や Ticker のチャンネルを受信している goroutine がいる場合、発動前は受信待ちでブロックしている状態になっています。

モックの時計を指定の時刻まで進めると、 Timer や Ticker の発動時刻を過ぎる場合は、時刻が古いほうから順番に発動させるのが理想です。

このためにはチャンネルに時刻を送った後、チャンネルを受信待ちの goroutine を動かして受信してその後の処理を実行させる必要があります。

が goroutine をどのように実行するかは Go のランタイムに任されていて、明示的に実行を進める手段は用意されていません。

そこで [github.com/benbjohnson/clock](https://github.com/benbjohnson/clock) では回避策として `time.Sleep(time.Millisecond)` でスリープして他の goroutine を進めるという技が使われています。
ここはモックの時刻ではなく実時間でスリープするということです。

場合によっては 1ms スリープではうまく行かないケースもあるということで [github.com/benbjohnson/clock](https://github.com/benbjohnson/clock) の fork の [github.com/dimonomid/clock](https://github.com/dimonomid/clock) ではモックの時計作成時に別の処理を行う関数が指定可能になっています。

## サードパーティーのライブラリーを比較検討してみた

[Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) のサンプルコードをベースにしたテストコードを書いて試してみました。

### github.com/Songmu/flextime

[Goでテスト中に現在時刻を差し替えたりするflextimeというのを作った | おそらくはそれさえも平凡な日々](https://songmu.jp/riji/entry/2020-01-19-flextime.html) に作者の Songmu さんの紹介記事があります。

#### time パッケージからの移行

`time` パッケージの代わりに `github.com/Songmu/flextime` パッケージを使うように書き換えれば OK という手軽さが良いです。

`flextime.Fix` では設定した時刻に固定、 `flextime.Set` では指定した時刻から進んでいく出来るのも便利です。 [flextime.Set](https://pkg.go.dev/github.com/Songmu/flextime?tab=doc#Set) の説明を見ると `flextime.Set` を呼んだ後 `flextime.Sleep` を呼ぶと実時間で待つことなくモックの時計を進められるとのことです。

また `Clock` インタフェースを実装してカスタムの時計を作って `flextime.Switch()` で差し替えられるのも良いです。

一方、内部では `sync.Mutex` で時計のグローバル変数を排他制御しており、 `flextime.Now()` など全ての関数実行時にロック取得・解放のオーバーヘッドがあるのが気になるところです。

個人的には production ではほぼオーバーヘッドなしで動く方式が良いです。
production では予め実時間のグローバル変数が設定されていて
テストの場合は [TestMain](https://golang.org/pkg/testing/#hdr-Main) で初期化時に差し替えるようにし、各関数の実行時にはロックなしで参照できるのが私の希望する使い方です。
ライブラリー提供側の立場としては使い方が限定されるのは避けたいので今の API になっているのは理解できます。

#### テストコード

flextime v0.0.7 を使ったテストコードを [hnakamur/go-mock-clock-experiment の using_github_com_Songmu_flextime ブランチ](https://github.com/hnakamur/go-mock-clock-experiment/tree/using_github_com_Songmu_flextime) に置いています。

下記に引用します。

`timeFormat` はナノ秒まで出すと Go のランタイムの実行のゆらぎで値がずれてしまうので、あえてミリ秒単位にしています。

```go
package main

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/Songmu/flextime"
	"github.com/kylelemons/godebug/diff"
)

const timeFormat = "2006-01-02T15:04:05.999Z07:00"

type strLog struct {
	b  strings.Builder
	mu sync.Mutex
}

func (l *strLog) Write(p []byte) (int, error) {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.b.Write(p)
}

func (l *strLog) String() string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.b.String()
}

func TestMockTime(t *testing.T) {
	l := &strLog{}
	log.SetOutput(l)
	log.SetFlags(0)

	time0 := time.Date(2020, 5, 1, 0, 0, 0, 0, time.UTC)
	flextime.Set(time0)

	// Create some timers using AfterFunc with a custom callback
	flextime.AfterFunc(200*time.Millisecond, func() {
		log.Printf("AfterFunc1 fired, time:%s", flextime.Now().Format(timeFormat))
	})
	flextime.AfterFunc(50*time.Millisecond, func() {
		log.Printf("AfterFunc2 fired, time:%s", flextime.Now().Format(timeFormat))
	})

	// Create some regular timers
	var mytimers []*flextime.Timer
	mytimers = append(mytimers, flextime.NewTimer(1*time.Second))
	mytimers = append(mytimers, flextime.NewTimer(2*time.Second))
	mytimers = append(mytimers, flextime.NewTimer(5*time.Second))
	mytimers = append(mytimers, flextime.NewTimer(100*time.Millisecond))

	// Create some tickers
	var mytickers []*flextime.Ticker
	mytickers = append(mytickers, flextime.NewTicker(500*time.Millisecond))

	go func() {
		flextime.Sleep(2 * time.Second)
		log.Printf("Came after Sleep 2 seconds, time:%s", flextime.Now().Format(timeFormat))
	}()

	flextime.Sleep(3 * time.Second)

	// This is needed to let other goroutines run
	time.Sleep(time.Millisecond)

	for i, tmr := range mytimers {
		var val string
		select {
		case t := <-tmr.C:
			val = fmt.Sprintf("fired, time:%s", t.Format(timeFormat))
		default:
			val = "not fired yet"
		}

		log.Printf("Timer #%d: %s", i, val)
	}

	for i, tkr := range mytickers {
		var val string
		select {
		case t := <-tkr.C:
			val = fmt.Sprintf("fired, time:%s", t.Format(timeFormat))
		default:
			val = "not fired yet"
		}

		log.Printf("Ticker #%d: %s", i, val)
	}

	got := l.String()
	want := strings.Join([]string{
		"AfterFunc2 fired, time:2020-05-01T00:00:00.05Z",
		"AfterFunc1 fired, time:2020-05-01T00:00:00.2Z",
		"Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z",
		"Timer #0: fired, time:2020-05-01T00:00:01Z",
		"Timer #1: fired, time:2020-05-01T00:00:02Z",
		"Timer #2: not fired yet",
		"Timer #3: fired, time:2020-05-01T00:00:00.1Z",
		"Ticker #0: fired, time:2020-05-01T00:00:00.5Z",
	}, "\n") + "\n"
	if got != want {
		t.Errorf("logs unmatched,\ngot:\n%s\nwant:\n%s\ndiff:\n%s", got, want, diff.Diff(got, want))
	}
}
```

#### テストの結果

`time.Sleep(time.Millisecond)` を消したときのテスト結果

```
$ go test -v
=== RUN   TestMockTime
    main_test.go:104: logs unmatched,
        got:
        Timer #0: not fired yet
        Timer #1: not fired yet
        Timer #2: not fired yet
        Timer #3: not fired yet
        Ticker #0: not fired yet

        want:
        AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z
        Timer #0: fired, time:2020-05-01T00:00:01Z
        Timer #1: fired, time:2020-05-01T00:00:02Z
        Timer #2: not fired yet
        Timer #3: fired, time:2020-05-01T00:00:00.1Z
        Ticker #0: fired, time:2020-05-01T00:00:00.5Z

        diff:
        -Timer #0: not fired yet
        -Timer #1: not fired yet
        +AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        +AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        +Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z
        +Timer #0: fired, time:2020-05-01T00:00:01Z
        +Timer #1: fired, time:2020-05-01T00:00:02Z
         Timer #2: not fired yet
        -Timer #3: not fired yet
        -Ticker #0: not fired yet
        +Timer #3: fired, time:2020-05-01T00:00:00.1Z
        +Ticker #0: fired, time:2020-05-01T00:00:00.5Z

--- FAIL: TestMockTime (0.00s)
FAIL
exit status 1
FAIL    github.com/hnakamur/go-mock-clock-experiment    0.002s
```

`time.Sleep(time.Millisecond)` がある状態でのテスト結果

```
$ go test -v
=== RUN   TestMockTime
    main_test.go:107: logs unmatched,
        got:
        Came after Sleep 2 seconds, time:2020-05-01T00:00:05Z
        AfterFunc1 fired, time:2020-05-01T00:00:05Z
        AfterFunc2 fired, time:2020-05-01T00:00:05Z
        Timer #0: fired, time:2020-05-01T00:00:01Z
        Timer #1: fired, time:2020-05-01T00:00:02Z
        Timer #2: fired, time:2020-05-01T00:00:05Z
        Timer #3: fired, time:2020-05-01T00:00:00.1Z
        Ticker #0: fired, time:2020-05-01T00:00:00.5Z

        want:
        AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z
        Timer #0: fired, time:2020-05-01T00:00:01Z
        Timer #1: fired, time:2020-05-01T00:00:02Z
        Timer #2: not fired yet
        Timer #3: fired, time:2020-05-01T00:00:00.1Z
        Ticker #0: fired, time:2020-05-01T00:00:00.5Z

        diff:
        -Came after Sleep 2 seconds, time:2020-05-01T00:00:05Z
        -AfterFunc1 fired, time:2020-05-01T00:00:05Z
        -AfterFunc2 fired, time:2020-05-01T00:00:05Z
        +AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        +AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        +Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z
         Timer #0: fired, time:2020-05-01T00:00:01Z
         Timer #1: fired, time:2020-05-01T00:00:02Z
        -Timer #2: fired, time:2020-05-01T00:00:05Z
        +Timer #2: not fired yet
         Timer #3: fired, time:2020-05-01T00:00:00.1Z
         Ticker #0: fired, time:2020-05-01T00:00:00.5Z

--- FAIL: TestMockTime (0.00s)
FAIL
exit status 1
FAIL    github.com/hnakamur/go-mock-clock-experiment    0.003s
```

`Came after Sleep` と `AfterFunc1` と `AfterFunc2` の順番と時刻が違うのと `Timer #2` が発動してしまっています。

これは `flextime.Sleep` がモックの時計の時刻を進めるという実装なので、複数の gorotine で呼ぶと合計の時間がすぐに進むからと推測されます。

実は私も `time.Now()` だけ差し替える実装を書いたときに `Sleep` でモックの時計を進めるように書いていました。
複数の goroutine で `Sleep` を呼ぶケースを考えるとモックの時計がその時間過ぎるまではブロックする必要があるので、他のライブラリーのように `Sleep` とは別にモックの時計を進める API を用意する必要がありそうです。

### code.cloudfoundry.org/clock

#### time パッケージからの移行

[clock package · pkg.go.dev](https://pkg.go.dev/code.cloudfoundry.org/clock?tab=doc) の Clock インタフェースを使うように書き換える必要があります。

production では [NewClock](https://pkg.go.dev/code.cloudfoundry.org/clock?tab=doc#NewClock)、テスト時は [fakeclock.NewFakeClock](https://pkg.go.dev/code.cloudfoundry.org/clock@v1.0.0/fakeclock?tab=doc#NewFakeClock) 関数でインスタンスを作ります。

モックの時計を進めるのは [Increment](https://pkg.go.dev/code.cloudfoundry.org/clock@v1.0.0/fakeclock?tab=doc#FakeClock.Increment) か [IncrementBySeconds](https://pkg.go.dev/code.cloudfoundry.org/clock@v1.0.0/fakeclock?tab=doc#FakeClock.IncrementBySeconds) メソッドを使います。

Clock インタフェースに `AfterFunc` メソッドは無いので `NewTimer` を使って以下のテストコードのように自前で実装する必要があります。

#### テストコード

code.cloudfoundry.org/clock v1.0.0 を使ったサンプルを [hnakamur/go-mock-clock-experiment の using_cloudfoundry_clock ブランチ](https://github.com/hnakamur/go-mock-clock-experiment/tree/using_cloudfoundry_clock) に置いています。

```go
package main

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"testing"
	"time"

	"code.cloudfoundry.org/clock"
	"code.cloudfoundry.org/clock/fakeclock"
	"github.com/kylelemons/godebug/diff"
)

const timeFormat = "2006-01-02T15:04:05.999Z07:00"

type strLog struct {
	b  strings.Builder
	mu sync.Mutex
}

func (l *strLog) Write(p []byte) (int, error) {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.b.Write(p)
}

func (l *strLog) String() string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.b.String()
}

func afterFunc(c clock.Clock, d time.Duration, f func()) clock.Timer {
	timer := c.NewTimer(d)
	go func() {
		<-timer.C()
		f()
	}()
	return timer
}

func TestMockTime(t *testing.T) {
	l := &strLog{}
	log.SetOutput(l)
	log.SetFlags(0)

	c := fakeclock.NewFakeClock(time.Date(2020, 5, 1, 0, 0, 0, 0, time.UTC))

	// Create some timers using AfterFunc with a custom callback
	afterFunc(c, 200*time.Millisecond, func() {
		log.Printf("AfterFunc1 fired, time:%s", c.Now().Format(timeFormat))
	})
	afterFunc(c, 50*time.Millisecond, func() {
		log.Printf("AfterFunc2 fired, time:%s", c.Now().Format(timeFormat))
	})

	// Create some regular timers
	var mytimers []clock.Timer
	mytimers = append(mytimers, c.NewTimer(1*time.Second))
	mytimers = append(mytimers, c.NewTimer(2*time.Second))
	mytimers = append(mytimers, c.NewTimer(5*time.Second))
	mytimers = append(mytimers, c.NewTimer(100*time.Millisecond))

	// Create some tickers
	var mytickers []clock.Ticker
	mytickers = append(mytickers, c.NewTicker(500*time.Millisecond))

	// Create goroutine calling sleep
	go func() {
		c.Sleep(2 * time.Second)
		log.Printf("Came after Sleep 2 seconds, time:%s", c.Now().Format(timeFormat))
	}()

	c.Increment(3 * time.Second)

	// This is needed to let other goroutines run.
	// See https://dmitryfrank.com/articles/mocking_time_in_go
	time.Sleep(time.Millisecond)

	for i, tmr := range mytimers {
		var val string
		select {
		case t := <-tmr.C():
			val = fmt.Sprintf("fired, time:%s", t.Format(timeFormat))
		default:
			val = "not fired yet"
		}

		log.Printf("Timer #%d: %s", i, val)
	}

	for i, tkr := range mytickers {
		var val string
		select {
		case t := <-tkr.C():
			val = fmt.Sprintf("fired, time:%s", t.Format(timeFormat))
		default:
			val = "not fired yet"
		}

		log.Printf("Ticker #%d: %s", i, val)
	}

	got := l.String()
	want := strings.Join([]string{
		"AfterFunc2 fired, time:2020-05-01T00:00:00.05Z",
		"AfterFunc1 fired, time:2020-05-01T00:00:00.2Z",
		"Came after Sleep 2 seconds, time:2020-05-01T00:00:05Z",
		"Timer #0: fired, time:2020-05-01T00:00:01Z",
		"Timer #1: fired, time:2020-05-01T00:00:02Z",
		"Timer #2: not fired yet",
		"Timer #3: fired, time:2020-05-01T00:00:00.1Z",
		"Ticker #0: fired, time:2020-05-01T00:00:00.5Z",
	}, "\n") + "\n"
	if got != want {
		t.Errorf("logs unmatched,\ngot:\n%s\nwant:\n%s\ndiff:\n%s", got, want, diff.Diff(got, want))
	}
}
```

#### テストの結果

```
$ go test -v
=== RUN   TestMockTime
    main_test.go:118: logs unmatched,
        got:
        AfterFunc1 fired, time:2020-05-01T00:00:03Z
        AfterFunc2 fired, time:2020-05-01T00:00:03Z
        Timer #0: fired, time:2020-05-01T00:00:03Z
        Timer #1: fired, time:2020-05-01T00:00:03Z
        Timer #2: not fired yet
        Timer #3: fired, time:2020-05-01T00:00:03Z
        Ticker #0: fired, time:2020-05-01T00:00:03Z

        want:
        AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        Came after Sleep 2 seconds, time:2020-05-01T00:00:05Z
        Timer #0: fired, time:2020-05-01T00:00:01Z
        Timer #1: fired, time:2020-05-01T00:00:02Z
        Timer #2: not fired yet
        Timer #3: fired, time:2020-05-01T00:00:00.1Z
        Ticker #0: fired, time:2020-05-01T00:00:00.5Z

        diff:
        -AfterFunc1 fired, time:2020-05-01T00:00:03Z
        -AfterFunc2 fired, time:2020-05-01T00:00:03Z
        -Timer #0: fired, time:2020-05-01T00:00:03Z
        -Timer #1: fired, time:2020-05-01T00:00:03Z
        +AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        +AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        +Came after Sleep 2 seconds, time:2020-05-01T00:00:05Z
        +Timer #0: fired, time:2020-05-01T00:00:01Z
        +Timer #1: fired, time:2020-05-01T00:00:02Z
         Timer #2: not fired yet
        -Timer #3: fired, time:2020-05-01T00:00:03Z
        -Ticker #0: fired, time:2020-05-01T00:00:03Z
        +Timer #3: fired, time:2020-05-01T00:00:00.1Z
        +Ticker #0: fired, time:2020-05-01T00:00:00.5Z

--- FAIL: TestMockTime (0.00s)
FAIL
exit status 1
FAIL    github.com/hnakamur/go-mock-clock-experiment    0.003s
```

Sleep の後のコードが実行されておらず、Timer, Ticker, AfterFunc の時刻がモックの時計を進めた後の時刻になっています。


### github.com/thejerf/abtime

[What approach do you use to mock time.Now() ? : golang](https://www.reddit.com/r/golang/comments/640vz3/what_approach_do_you_use_to_mock_timenow/) の [コメント](https://www.reddit.com/r/golang/comments/640vz3/what_approach_do_you_use_to_mock_timenow/dfyrx1c/) で知りました。

#### time パッケージからの移行

[abtime package · pkg.go.dev](https://pkg.go.dev/github.com/thejerf/abtime?tab=doc) に `AbstractTime` というインターフェースがありこれを使うように書き換える必要があります。

production では [NewRealTime](https://pkg.go.dev/github.com/thejerf/abtime?tab=doc#NewRealTime)、テストでは [NewManual](https://pkg.go.dev/github.com/thejerf/abtime?tab=doc#NewManual) か [NewManualAtTime](https://pkg.go.dev/github.com/thejerf/abtime?tab=doc#NewManualAtTime) でインスタンスを生成します。

モックの時計の時刻を進めるのは [Advance](https://pkg.go.dev/github.com/thejerf/abtime?tab=doc#ManualTime.Advance) メソッドです。

`AbstractTime` インターフェースで `Timer` や `Ticker` などを作る際にユニークな ID を指定する必要があり、これが厳しいです。

さらにそれを発動させるには [Trigger](https://pkg.go.dev/github.com/thejerf/abtime?tab=doc#ManualTime.Trigger) メソッドを呼ぶ必要があります。

一応テストはしてみましたが結果も芳しくないので省略します。

### github.com/facebookarchive/clock 

[facebookarchive/clock: Clock is a small library for mocking time in Go.](https://github.com/facebookarchive/clock) はアーカイブされていたのでスルーしました。

[benbjohnson/clock: Clock is a small library for mocking time in Go.](https://github.com/benbjohnson/clock) の fork でした。

### github.com/jmhodges/clock

[clock package · pkg.go.dev](https://pkg.go.dev/github.com/jmhodges/clock?tab=doc) の `Clock` インターフェースに `NewTimer` メソッドはありますが `NewTicker` メソッドは無いのを見てスルーしました。

### github.com/benbjohnson/clock

v1.0.3 を [hnakamur/go-mock-clock-experiment の using_github_com_benbjohnson_clock ブランチ](https://github.com/hnakamur/go-mock-clock-experiment/tree/using_github_com_benbjohnson_clock) で試しました。

#### time パッケージからの移行

[clock package · pkg.go.dev](https://pkg.go.dev/github.com/benbjohnson/clock?tab=doc#pkg-examples) の `Clock` インターフェースに合わせて書き換える必要があります。

production では [New](https://pkg.go.dev/github.com/benbjohnson/clock?tab=doc#New)、テストでは [NewMock](https://pkg.go.dev/github.com/benbjohnson/clock?tab=doc#NewMock) でインスタンスを作成します。

モックの時計は [Add](https://pkg.go.dev/github.com/benbjohnson/clock?tab=doc#Mock.Add) メソッドで進めます。

[Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) でも指摘されていますが、 Go 標準ライブラリーの [time](https://golang.org/pkg/time/) パッケージでは `NewTimer` や `NewTicker` という関数名ですが、 `Clock` インターフェースでは対応するメソッド名が `Timer` と `Ticker` と違うので要注意です。

#### テストコード

```go
package main

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/benbjohnson/clock"
	"github.com/kylelemons/godebug/diff"
)

const timeFormat = "2006-01-02T15:04:05.999Z07:00"

type strLog struct {
	b  strings.Builder
	mu sync.Mutex
}

func (l *strLog) Write(p []byte) (int, error) {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.b.Write(p)
}

func (l *strLog) String() string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.b.String()
}

func TestMockTime(t *testing.T) {
	l := &strLog{}
	log.SetOutput(l)
	log.SetFlags(0)

	c := clock.NewMock()
	c.Set(time.Date(2020, 5, 1, 0, 0, 0, 0, time.UTC))

	// Create some timers using AfterFunc with a custom callback
	c.AfterFunc(200*time.Millisecond, func() {
		log.Printf("AfterFunc1 fired, time:%s", c.Now().Format(timeFormat))
	})
	c.AfterFunc(50*time.Millisecond, func() {
		log.Printf("AfterFunc2 fired, time:%s", c.Now().Format(timeFormat))
	})

	// Create some regular timers
	var mytimers []*clock.Timer
	mytimers = append(mytimers, c.Timer(1*time.Second))
	mytimers = append(mytimers, c.Timer(2*time.Second))
	mytimers = append(mytimers, c.Timer(5*time.Second))
	mytimers = append(mytimers, c.Timer(100*time.Millisecond))

	// Create some tickers
	var mytickers []*clock.Ticker
	mytickers = append(mytickers, c.Ticker(500*time.Millisecond))

	go func() {
		c.Sleep(2 * time.Second)
		log.Printf("Came after Sleep 2 seconds, time:%s", c.Now().Format(timeFormat))
	}()

	c.Add(3 * time.Second)

	for i, tmr := range mytimers {
		var val string
		select {
		case t := <-tmr.C:
			val = fmt.Sprintf("fired, time:%s", t.Format(timeFormat))
		default:
			val = "not fired yet"
		}

		log.Printf("Timer #%d: %s", i, val)
	}

	for i, tkr := range mytickers {
		var val string
		select {
		case t := <-tkr.C:
			val = fmt.Sprintf("fired, time:%s", t.Format(timeFormat))
		default:
			val = "not fired yet"
		}

		log.Printf("Ticker #%d: %s", i, val)
	}

	got := l.String()
	want := strings.Join([]string{
		"AfterFunc2 fired, time:2020-05-01T00:00:00.05Z",
		"AfterFunc1 fired, time:2020-05-01T00:00:00.2Z",
		"Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z",
		"Timer #0: fired, time:2020-05-01T00:00:01Z",
		"Timer #1: fired, time:2020-05-01T00:00:02Z",
		"Timer #2: not fired yet",
		"Timer #3: fired, time:2020-05-01T00:00:00.1Z",
		"Ticker #0: fired, time:2020-05-01T00:00:00.5Z",
	}, "\n") + "\n"
	if got != want {
		t.Errorf("logs unmatched,\ngot:\n%s\n\nwant:\n%s\n\ndiff:\n%s", got, want, diff.Diff(got, want))
	}
}
```

#### テストの結果

テストはブロックしてしまい、 Ctrl-C を押して止める必要がありました。

```
$ go test -v
=== RUN   TestMockTime
^Csignal: interrupt
FAIL    github.com/hnakamur/go-mock-clock-experiment    4.420s
```

### github.com/dimonomid/clock

[Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) の著者による github.com/benbjohnson/clock の fork です。

#### time パッケージからの移行

github.com/benbjohnson/clock と同様です。

#### テストコード

github.com/benbjohnson/clock と同じですが、 github.com/dimonomid/clock は fork ですがパッケージ名は変えていないので `go.mod` に以下のように replace を書く必要がありました（replace についての詳細は [When should I use the replace directive?](https://github.com/golang/go/wiki/Modules#when-should-i-use-the-replace-directive) を参照）。

```
replace github.com/benbjohnson/clock => github.com/dimonomid/clock v0.0.0-20200123114523-8d1048cafc4d
```

#### テストの結果

```
$ go test -v
=== RUN   TestMockTime
    main_test.go:104: logs unmatched,
        got:
        AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        Came after Sleep 2 seconds, time:2020-05-01T00:00:02.5Z
        Timer #0: fired, time:2020-05-01T00:00:01Z
        Timer #1: fired, time:2020-05-01T00:00:02Z
        Timer #2: not fired yet
        Timer #3: fired, time:2020-05-01T00:00:00.1Z
        Ticker #0: fired, time:2020-05-01T00:00:00.5Z

        want:
        AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
        AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z
        Timer #0: fired, time:2020-05-01T00:00:01Z
        Timer #1: fired, time:2020-05-01T00:00:02Z
        Timer #2: not fired yet
        Timer #3: fired, time:2020-05-01T00:00:00.1Z
        Ticker #0: fired, time:2020-05-01T00:00:00.5Z

        diff:
         AfterFunc2 fired, time:2020-05-01T00:00:00.05Z
         AfterFunc1 fired, time:2020-05-01T00:00:00.2Z
        -Came after Sleep 2 seconds, time:2020-05-01T00:00:02.5Z
        +Came after Sleep 2 seconds, time:2020-05-01T00:00:02Z
         Timer #0: fired, time:2020-05-01T00:00:01Z
         Timer #1: fired, time:2020-05-01T00:00:02Z
         Timer #2: not fired yet
         Timer #3: fired, time:2020-05-01T00:00:00.1Z
         Ticker #0: fired, time:2020-05-01T00:00:00.5Z

--- FAIL: TestMockTime (0.02s)
FAIL
exit status 1
FAIL    github.com/hnakamur/go-mock-clock-experiment    0.017s
```

不一致なのは `Sleep` の後の時刻だけで他は全て期待通りです。素晴らしい！

`Sleep` した後の時刻は Go のランタイム次第で `Sleep` の次の行の時刻が変わりうるので、そもそも特定の時刻を期待してはいけないです。

と言いつつ、ミリ秒の単位なら良いのではないかという甘い期待で上記のテストコードにしています。
ですが、上記の結果では 500ms のずれが起きています。

[clock/clock.go at master · dimonomid/clock](https://github.com/dimonomid/clock/blob/8d1048cafc4d6c8e8087c3e1c8bddf361331bfa5/clock.go) を見てみたのですが、どこにも 500ms という値は無く、この現象が起きる理由はわかりませんでした。

## おわりに

今回試した中では [dimonomid/clock: Clock is a small library for mocking time in Go.](https://github.com/dimonomid/clock) が一番良かったです。

ただ、 [Mocking time and testing event loops in Go \[Dmitry Frank\]](https://dmitryfrank.com/articles/mocking_time_in_go) で詳しく解説されているように、チャンネルを扱っている部分ではさらに対応が必要な場合があります。

[O'Reilly Japan - Go言語による並行処理](https://www.oreilly.co.jp/books/9784873118468/) でも紹介されているように同期用のフック関数を用意しておき production は何もしない no-op 的な関数をセットし、テストでは同期用のチャンネルと送受信して、タイミングを制御するという技などを使ったりします。

ですが、それで制御できるのはあくまで特定の時点までブロックさせることだけです。
チャンネルを送信・受信したあとのコードがどのタイミングで実行されるかは Go のランタイム次第だということを忘れないよう注意が必要です。
