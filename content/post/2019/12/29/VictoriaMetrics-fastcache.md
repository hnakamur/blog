+++
title="VictoriMetrics/fastcacheによるGoのGC負荷の回避方法"
date = "2019-12-29T16:00:00+09:00"
tags = ["go", "key-value-store", "victoria-metrics"]
categories = ["blog"]
+++

## 背景

[VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) で `foo.bar.baz` といったメトリクス名からIDへのマッピングは
[VictoriaMetrics/fastcache](https://github.com/VictoriaMetrics/fastcache) というキーバリューストアで保管されています。ということで調査したメモ。

## ベンチマーク

ベンチマークがついているので自分のサーバでも試してみました。

```console
$ GOMAXPROCS=4 go test github.com/VictoriaMetrics/fastcache -bench='Set|Get' -benchtime=10s
go: downloading github.com/allegro/bigcache v1.2.1-0.20190218064605-e24eb225f156
go: extracting github.com/allegro/bigcache v1.2.1-0.20190218064605-e24eb225f156
goos: linux
goarch: amd64
pkg: github.com/VictoriaMetrics/fastcache
BenchmarkSetBig-4                 445272             26828 ns/op        9771.25 MB/s           3 B/op          0 allocs/op
BenchmarkGetBig-4                 520488             22983 ns/op        11806.75 MB/s          5 B/op          0 allocs/op
BenchmarkBigCacheSet-4              1003          12917688 ns/op           5.07 MB/s     4508913 B/op         10 allocs/op
BenchmarkBigCacheGet-4              1406           7261204 ns/op           9.03 MB/s      751703 B/op     131077 allocs/op
BenchmarkBigCacheSetGet-4            601          20793950 ns/op           6.30 MB/s     5055210 B/op     131087 allocs/op
BenchmarkCacheSet-4                 2865           3851611 ns/op          17.02 MB/s        1994 B/op          4 allocs/op
BenchmarkCacheGet-4                 2983           3733081 ns/op          17.56 MB/s        1916 B/op          3 allocs/op
BenchmarkCacheSetGet-4              1483           7788285 ns/op          16.83 MB/s        3851 B/op          7 allocs/op
BenchmarkStdMapSet-4                 756          15678413 ns/op           4.18 MB/s      278780 B/op      65539 allocs/op
BenchmarkStdMapGet-4                3852           2794116 ns/op          23.46 MB/s        3328 B/op         17 allocs/op
BenchmarkStdMapSetGet-4              127          96927749 ns/op           1.35 MB/s      361095 B/op      65554 allocs/op
BenchmarkSyncMapSet-4                271          43889357 ns/op           1.49 MB/s     3442234 B/op     262636 allocs/op
BenchmarkSyncMapGet-4               2641           3788181 ns/op          17.30 MB/s        4816 B/op        149 allocs/op
BenchmarkSyncMapSetGet-4             596          18809556 ns/op           6.97 MB/s     3423522 B/op     262367 allocs/op
PASS
ok      github.com/VictoriaMetrics/fastcache    193.857s
```

```console
$ go version
go version go1.13.5 linux/amd64
```

```console
hnakamur@express:~/ghq/github.com/VictoriaMetrics/fastcache$ git rev-parse HEAD
c9a5939fd508ba790b708b23929feea13623d735
```

CPU は [インテル® Core™ i5-650 プロセッサー (4M キャッシュ、3.20 GHz) 製品仕様](https://ark.intel.com/content/www/jp/ja/ark/products/43546/intel-core-i5-650-processor-4m-cache-3-20-ghz.html) で2コア4スレッドです。

API [fastcache package · go.dev](https://pkg.go.dev/github.com/VictoriaMetrics/fastcache?tab=doc) は README にある通りシンプルです。ちょっと変わっているのは `Get`, `Set` の他に 64KB 以上の値用に `GetBig`, `SetBig` という別の API が用意されている点です。

上記のベンチマークのうち SetBig, GetBig, CacheSet, CacheGet, CacheSetGet が fastcache の API です。どれも1操作当たりのメモリ割り当て回数 (allocs/op) が非常に少なく高速であることがわかります。メモリ割り当て回数が少ないのは [sync.Pool](https://golang.org/pkg/sync/#Pool) を活用しているからです。 VictoriaMetrics の開発者は [valyala/fasthttp](https://github.com/valyala/fasthttp) と同じ方でそちらでも [sync.Pool](https://golang.org/pkg/sync/#Pool) を活用することで高速化を実現されています。

## fastcache のアーキテクチャ

READMEの [Architecture details](https://github.com/VictoriaMetrics/fastcache#architecture-details) に説明があります。

そこからリンクされている [Further Dangers of Large Heaps in Go - Ravelin Tech Blog](https://syslog.ravelin.com/further-dangers-of-large-heaps-in-go-7a267b57d487) が GC のオーバーヘッドについての素晴らしい記事でした。一言で言うとポインタが増えすぎると GC がそれらをスキャンして回るのが追い付かなくなるということです。 GC も銀の弾丸ではなく限界があるというわけです。冷静に考えれば当然のことで、アプリケーションの処理を進めるために GC に使う時間を限定すると、その時間の中で出来ることには限界があるわけです。

（実は私も過去に似た体験をしてました。 [lomik/go-carbon](https://github.com/lomik/go-carbon) の負荷テストの CLI を Go で書いて1週間流しっぱなしにしたときに ps でみると使用メモリがじわじわ増えていくという現象が起きました）

回避策として mmap でメモリ割り当てして GC の対象外 (off-heap) なところでデータを扱うという方法があります。ただしその中に Go のオブジェクトは置けないので、バイト列として [unsafe](https://golang.org/pkg/unsafe/) でアクセスするか、そこから読み取った値を元に Go のオブジェクトを別途作成する必要があります。でも後者だと二重管理になってメモリも二重に必要になるので、極力前者の方式をとるべきです。すると mmap で割り当てたメモリ領域の中で整数や浮動小数点やバイト列を置くのは良いとして、ポインタに関してはポインタを使わずなんらかのインデクスやオフセットでデータ構造を実現することになります。もしくはポインタの先を Go でメモリ割り当てしたデータ構造ではなく別の mmap 呼び出しで割り当てたメモリ領域内のアドレスにする手もありますね。

[Architecture details](https://github.com/VictoriaMetrics/fastcache#architecture-details) に戻ると mmap で一度に割り当てるメモリのチャンクサイズが大きいと GC の負荷が大きくなるので fastcache では 64KiB にしているそうです。これによりメモリのフラグメンテーションとトータルのメモリ使用量が抑えられるとのことです。

（[cgoとunsafeについてのメモ · hnakamur's blog](/blog/2019/12/29/cgo-and-unsafe/) を書いたときは mmap の代わりに `C.malloc` でも良いかもと思ったのですが [c++ - Why does the free() function not return memory to the operating system? - Stack Overflow](https://stackoverflow.com/questions/52417318/why-does-the-free-function-not-return-memory-to-the-operating-system/52417370) や [freed memory does not return to system , is it able to used by running application](https://www.linuxquestions.org/questions/linux-newbie-8/freed-memory-does-not-return-to-system-is-it-able-to-used-by-running-application-4175521572/) を見ると `free` を読んでも OS にメモリが返却されないので mmap を使うほうが良さそうです。）

上で書いた 64KB 以上の値用に `GetBig`, `SetBig` という別の API が用意されているのはこれが理由だったんですね。

## まとめ

まとめると VictoriMetrics/fastcache によるGoのGC負荷の回避方法は以下の2点です。

* Goのオブジェクトは極力 [sync.Pool](https://golang.org/pkg/sync/#Pool) を使って再利用することでメモリ割り当て回数を減らす。
* Goのポインタを使わずに表せるデータ構造は mmap で割り当てて GC の対象外とし GC の負担を減らす。
