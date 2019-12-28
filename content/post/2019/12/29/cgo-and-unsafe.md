+++
title="cgoとunsafeについてのメモ"
date = "2019-12-29T03:00:00+09:00"
tags = ["go", "cgo", "unsafe"]
categories = ["blog"]
+++

## 背景

まず大前提として cgo や unsafe を使ったプログラムは Go の将来のバージョンで動く保証がないので極力避けるべきです（unsafeについては[Go 1 and the Future of Go Programs - The Go Programming Language](https://golang.org/doc/go1compat)で明示的に互換性保証の対象外と書かれています。cgo は [Go 1.12 Release Notes - The Go Programming Language](https://golang.org/doc/go1.12#cgo) に変更された実例があります）。

が、現実には cgo や unsafe を使いたいケースがあります。

一番の理由は C で書かれた資産が既にあってそれを使いたい場合です。安全性や保守性では Go に移植するほうが望ましいですが、難しかったり性能が出ない場合もあります。例えば [VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) の [all: use gozstd instead of pure Go zstd for GOARCH=amd64](https://github.com/VictoriaMetrics/VictoriaMetrics/commit/5cb8d9774308031b13f9d0feb2c8c6d7d0d87026) というコミットでは pure go の zstd を cgo の zstd に切り替えています。

また、別の理由として省メモリなデータ構造を作りたいというのがあります。 Go の slice や interface のサイズが気になったので以下のコードで調べてみました。

```go
package main

import (
    "fmt"
    "unsafe"
)

func main() {
    fmt.Printf("slice          size=%d\n", unsafe.Sizeof([]byte{}))
    var a interface{}
    fmt.Printf("interface      size=%d\n", unsafe.Sizeof(a))
    var p unsafe.Pointer
    fmt.Printf("unsafe.Pointer size=%d\n", unsafe.Sizeof(p))
}
```

amd64 の Linux 環境では以下のような結果になりました。

```console
$ go run main.go
slice          size=24
interface      size=16
unsafe.Pointer size=8
```

slice は長さ (len) とキャパシテイ (cap) とポインタがそれぞれ 8 バイトで計 24 バイト、
interface は型の種別とポインタがそれぞれ 8 バイトで計 16 バイトということだと思います。

C 言語だと union や [Tagged pointer - Wikipedia](https://en.wikipedia.org/wiki/Tagged_pointer) のような手法を使えるので差が開きます。

CPU のキャッシュラインに載るようなサイズのデータ構造を設計するといった文脈では
このサイズのハンディキャップは気になるところです。

と思っていた時に [VictoriaMetrics/fastcache](https://github.com/VictoriaMetrics/fastcache)  の [malloc_mmap.go](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/malloc_mmap.go) のコードを見ると GC を介さずにメモリを割り当てるために `syscall.Mmap` を使っていました（mmap はファイルをメモリアドレス空間にマップするのが本来の使い方ですがファイルにマップしない使い方も出来ます）。

なるほどこういう手もあるのかと感心しました。で、この機会に cgo と unsafe についてまとめておこうとこの記事を書きました。

## cgo

* [cgo · golang/go Wiki](https://github.com/golang/go/wiki/cgo)
    * [cgo - The Go Programming Language](https://golang.org/cmd/cgo/)
    * [C? Go? Cgo! - The Go Blog](https://blog.golang.org/c-go-cgo)
* [Go Proverbs](https://www.youtube.com/watch?v=PAAkCSZUG1c&t=7m36s)
    * [Cgo must always be guarded with build tags.](https://www.youtube.com/watch?v=PAAkCSZUG1c&t=11m53s)
    * [Cgo is not Go.](https://www.youtube.com/watch?v=PAAkCSZUG1c&t=12m37s)
    * [With the unsafe package there are no guarantees.](https://www.youtube.com/watch?v=PAAkCSZUG1c&t=13m49s)
* [cgo is not Go | Dave Cheney](https://dave.cheney.net/2016/01/18/cgo-is-not-go)
    * [cgo is not Go : golang @reddit](https://www.reddit.com/r/golang/comments/41hk4b/cgo_is_not_go/)
* [Why cgo is slow @ CapitalGo 2018 - Speaker Deck](https://speakerdeck.com/filosottile/why-cgo-is-slow-at-capitalgo-2018)
    * Go から C の関数を呼び出すのもその逆も遅いので、細かい粒度ではなく大きな粒度で呼ぶようにし回数を減らすのが良い。
* [GopherCon 2018 - Adventures in Cgo Performance](https://about.sourcegraph.com/go/gophercon-2018-adventures-in-cgo-performance)
* [The Cost and Complexity of Cgo | Cockroach Labs](https://www.cockroachlabs.com/blog/the-cost-and-complexity-of-cgo/)
* [Statically Linking C to Go · Made with Drew](https://blog.madewithdrew.com/post/statically-linking-c-to-go/)
    * Linux では以下のようにビルドすればスタティックビルドできる（file.go は適宜変更）。

```console
go build --ldflags '-extldflags "-static"' file.go
```

## unsafe

* [unsafe - The Go Programming Language](https://golang.org/pkg/unsafe/)
* [Package unsafe](https://golang.org/ref/spec#Package_unsafe) section in The Go Language Specification
* [garbage collection - Does Go guarantee constant addresses? - Stack Overflow](https://stackoverflow.com/questions/22195919/does-go-guarantee-constant-addresses)
    * もし GC がメモリを移動した場合 ポインタ型と `unsafe.Pointer` の変数の値は更新されるとのこと。
    * ただし [unsafe.Pointer](https://golang.org/pkg/unsafe/#Pointer) のドキュメントには GC がメモリを移動しても `uintptr` の変数の値を更新しないことしか書かれていない。が `uintptr` と別に `unsafe.Pointer` が用意されていることを考えると `unsafe.Pointer` のアドレスは GC によって更新されるのは当てにしてもよさそう。

## malloc

確実にメモリのアドレスが GC によって移動されないようにするには mmap か malloc を使う手がある。

* [Go GC and mmap : golang](https://www.reddit.com/r/golang/comments/2tifyv/go_gc_and_mmap/)
    * mmap や malloc で割り当てたメモリは GC の対象外。
    * GC で使うメモリ領域は予約されていて、 malloc など GC 以外で割り当てたメモリは別の領域になる。

* [cmd/cgo: link error when binding C.malloc to a Go variable · Issue #18889 · golang/go](https://github.com/golang/go/issues/18889)
    * `C.malloc` は `_CMalloc` というビルトインのラッパ関数に置き換えられる。 [ビルトインのラッパ関数一覧](https://github.com/golang/go/blob/go1.13.5/src/cmd/cgo/out.go#L1698)
    * `C.malloc` をラップしているのは以下の2つの理由のため。
        1. `#include <stdlib.h>` を書かなくても `C.malloc` を使えるようにするため。
        2. `C.malloc` が `nil` を決して返さないようにするため。


`#include <stdlib.h>` は `C.malloc` では不要だが `C.free` を使う場合には必要。

`C.malloc` が `nil` を返さないと保証されているのは [cgo - The Go Programming Language](https://golang.org/cmd/cgo/#hdr-Go_references_to_C) の最後に記載があった。なので `C.malloc` の戻り値の `nil` チェックは不要。

malloc と free を使うサンプルコード。

```go
// +build cgo
package main

// #include <stdlib.h>
import "C"

import (
    "fmt"
    "log"
)

func main() {
    if err := run(); err != nil {
        log.Fatal(err)
    }
}

func run() error {
    data := C.malloc(8)
    defer C.free(data)

    *(*int64)(data) = 1234
    a := *(*int64)(data)
    fmt.Printf("a=%d\n", a)
    return nil
}
```

スタティックビルド。

```console
$ go build --ldflags '-extldflags "-static"' -o main
```

スタティックバイナリになったことを確認。

```console
$ ldd main
        not a dynamic executable
```

`C.malloc` を使う場合は細切れに割り当てるのではなく上記の
[malloc_mmap.go](https://github.com/VictoriaMetrics/fastcache/blob/c9a5939fd508ba790b708b23929feea13623d735/malloc_mmap.go) のように [Region-based memory management - Wikipedia](https://en.wikipedia.org/wiki/Region-based_memory_management) 方式が良さそうです。
手動メモリ管理の手間をなるべく減らすのとメモリ断片化を防ぐ意味で。

ただ GC の負荷が許容範囲内なら [make](https://golang.org/pkg/builtin/#make) で `[]byte` をメモリ割り当てして `unsafe.Pointer` で参照するほうがメモリ管理を GC に任せられるので良いです。
