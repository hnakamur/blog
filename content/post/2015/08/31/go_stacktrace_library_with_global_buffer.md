Title: Goでグローバルなバッファを使いまわしてスタックトレースを取得するライブラリを書いてみた
Date: 2015-08-31 00:43
Category: blog
Tags: go
Slug: blog/2015/08/31/go_stacktrace_library_with_global_buffer

## 背景と経緯

Goでもエラー処理にpanicを使えばスタックトレースが出力されます。でも、ライブラリでは `panic` するとエラー処理して続行したいときに困るのでpanicではなく `return err` を使うのが普通です。すると今度はスタックトレースが取れないのが残念だと思っていました。エラーが出た箇所でログ出力はするとして、やはりスタックトレースがあるほうがその関数までの呼出経路がわかってデバッグが捗ります。

標準ライブラリを見てみると、[runtime.debug.PrintStack()](http://golang.org/pkg/runtime/debug/#PrintStack) という便利そうな関数を見つけました。が、これは出力先が標準エラー出力固定となっています。私はログファイルに出したいんですよね。

そこでドキュメントの関数のリンクをクリックしてソースを見てみます。
[src/runtime/debug/stack.go - The Go Programming Language](http://golang.org/src/runtime/debug/stack.go?s=516:533#L15)

```
func PrintStack() {
  os.Stderr.Write(stack())
}

// Stack returns a formatted stack trace of the goroutine that calls it.
// For each routine, it includes the source line information and PC value,
// then attempts to discover, for Go functions, the calling function or
// method and the text of the line containing the invocation.
//
// Deprecated: Use package runtime's Stack instead.
func Stack() []byte {
  return stack()
}
```

お、`Stack()` のほうを使えば `[]byte` で取得できるじゃないですか。あれ、でもdeprecatedなので [runtime.Stack](http://golang.org/pkg/runtime/#Stack) のほうを使えとあります。シグネチャ見ると `func Stack(buf []byte, all bool) int` となっていて、こちらからバッファを渡す必要があるんですね。

関数定義 [src/runtime/mprof.go - The Go Programming Language](http://golang.org/src/runtime/mprof.go?s=15278:15314#L552)を見てみると、バッファサイズが足りない場合は、途中までしか書かれないようです。またどれだけのサイズがあれば大丈夫かを調べる方法もないようです。

```
func Stack(buf []byte, all bool) int {
  if all {
    stopTheWorld("stack trace")
  }

  n := 0
  if len(buf) > 0 {
    gp := getg()
    sp := getcallersp(unsafe.Pointer(&buf))
    pc := getcallerpc(unsafe.Pointer(&buf))
    systemstack(func() {
      g0 := getg()
      g0.writebuf = buf[0:0:len(buf)]
      goroutineheader(gp)
      traceback(pc, sp, 0, gp)
      if all {
        tracebackothers(gp)
      }
      n = len(g0.writebuf)
      g0.writebuf = nil
    })
  }

  if all {
    startTheWorld()
  }
  return n
}
```

実はさっきの `stack()` の定義[src/runtime/debug/stack.go - The Go Programming Language](http://golang.org/src/runtime/debug/stack.go?s=516:533#L40)を見ると[runtime.Caller](http://golang.org/pkg/runtime/#Caller)というより低レベルな関数があってこれを使って自前で実装すれば好きに作れそうではあります。

しかし、私は手抜きで済ませたいので大きめのバッファをグローバルに予め確保しておいてそれを[runtime.Stack](http://golang.org/pkg/runtime/#Stack)に渡す方式にしました。
バッファを予め確保しておくのは、エラーが起きてからメモリ確保しようとして失敗するケースを避けたいからです。

と言いつつ、[runtime.Stack](http://golang.org/pkg/runtime/#Stack)内でメモリ割り当てが発生するかまでは確認していません。

## 実装と使い方

というわけで実装してみました。レポジトリは[hnakamur/stacktrace](https://github.com/hnakamur/stacktrace)で、ライセンスはMITです。


使用例はこちらです。[example.go](https://github.com/hnakamur/stacktrace/blob/ed0a2c8b61528e59f349f6c108a84a6b9dd8e981/example/main.go)

```
package main

import (
  "errors"
  "log"

  "github.com/hnakamur/stacktrace"
)

func logErrorWithStackTrace(msg interface{}) {
  log.Printf("error: %s\nstacktrace: %s\n", msg, stacktrace.LockBufAndGetStackWithSkip(2))
  defer stacktrace.UnlockBuf()
}

func b() {
  err := errors.New("some error")
  logErrorWithStackTrace(err)
}

func a() {
  b()
}

func main() {
  a()
}
```

まずお好みのロギングライブラリ用にスタックトレースを取得してログ出力する関数を定義します。この例の場合は `logErrorWithStackTrace` です。メモリ割り当て回数を最低限にしたかったので、 `stacktrace.LockBufAndGetStackWithSkip()` はグローバルバッファをロックした状態でそのまま返すようにしています。ですので使い終わったら、`stacktrace.UnlockBuf()` でロックを解放する必要があります。

`stacktrace.LockBufAndGetStackWithSkip()` の引数で2を渡しているのはスタックトレースから `stacktrace.LockBufAndGetStackWithSkip` と `logErrorWithStackTrace` の2つを除外するためです。

出力例は以下の通りです。

```
$ go run main.go
2015/08/31 01:24:42 error: some error
stacktrace: goroutine 1 [running]:
main.b()
        /Users/hnakamur/gocode/src/github.com/hnakamur/stacktrace/example/main.go:17 +0xce
main.a()
        /Users/hnakamur/gocode/src/github.com/hnakamur/stacktrace/example/main.go:21 +0x14
main.main()
        /Users/hnakamur/gocode/src/github.com/hnakamur/stacktrace/example/main.go:25 +0x14
```

これでスタックトレース付きのエラーログを簡単に出力できて快適ですね！
