Title: GoのMessagePackのライブラリのベンチマークをしてみた
Date: 2016-06-04 22:17
Category: blog
Tags: golang, messagepack
Slug: 2016/06/04/benchmark_go_msgpack_libraries

[Go の msgpack ライブラリ比較 - Qiita](http://qiita.com/yosisa/items/f21d3476bc8d368d7494)の記事が最終更新日から1年以上経過しているとのことなので、現在の最新のコミットで試してみました。

`github.com/vmihailenco/msgpack` を `go get` すると

```
$ go get github.com/vmihailenco/msgpack
package github.com/vmihailenco/msgpack: code in directory /home/hnakamur/gocode/src/github.com/vmihailenco/msgpack expects import "gopkg.in/vmihailenco/msgpack.v2"
```

と言われたので `go get gopkg.in/vmihailenco/msgpack.v2` で取得し、この記事のコードの `"github.com/vmihailenco/msgpack"` を `"gopkg.in/vmihailenco/msgpack.v2"` に書き換え `msgpack_test.go` という名前で保存して試しました。

エンコードは `gopkg.in/vmihailenco/msgpack.v2` 、デコードは `github.com/ugorji/go/codec` が速いという結果になりましたが、総合的にはほぼ同等と言えると思います。

```
$ go test -bench . -benchmem
testing: warning: no tests to run
PASS
BenchmarkCodecEncode-2            500000              3236 ns/op              48 B/op          2 allocs/op
BenchmarkCodecDecode-2            200000              8998 ns/op             264 B/op         25 allocs/op
BenchmarkMsgpackEncode-2          500000              2624 ns/op              48 B/op          2 allocs/op
BenchmarkMsgpackDecode-2          200000             10604 ns/op             448 B/op         35 allocs/op
ok      bitbucket.org/hnakamur/msgpack_experiment       7.146s
```

ベンチマークに使用したライブラリとGoのバージョンは以下の通りです。

```
$ git -C $GOPATH/src/github.com/ugorji/go rev-parse HEAD
a396ed22fc049df733440d90efe17475e3929ccb
$ git -C $GOPATH/src/gopkg.in/vmihailenco/msgpack.v2 rev-parse HEAD
851cd631b60599a692b136c60eb6eb2899b0e664
$ go version
go version go1.6.2 linux/amd64
```

[vmihailenco/msgpack: MessagePack encoding for Golang](https://github.com/vmihailenco/msgpack)のベンチマークもやってみました。

```
$ go test -bench . -benchmem                                          
2016/06/04 22:12:13 
************************************************ 
package github.com/ugorji/go-msgpack has been deprecated (05/29/2013). 
It will be retired anytime from July 1, 2013.
Please update to faster and much much better github.com/ugorji/go/codec.
See https://github.com/ugorji/go/tree/master/codec#readme for more information.
************************************************ 
OK: 27 passed, 1 skipped
PASS
BenchmarkBool-2                         20000000                90.3 ns/op             0 B/op          0 allocs/op
BenchmarkInt0-2                         20000000                96.1 ns/op             0 B/op          0 allocs/op
BenchmarkInt1-2                         10000000               123 ns/op               0 B/op          0 allocs/op
BenchmarkInt2-2                         10000000               123 ns/op               0 B/op          0 allocs/op
BenchmarkInt4-2                         10000000               179 ns/op               0 B/op          0 allocs/op
BenchmarkInt8-2                         10000000               176 ns/op               0 B/op          0 allocs/op
BenchmarkInt0Binary-2                    5000000               340 ns/op              24 B/op          3 allocs/op
BenchmarkInt0UgorjiGoMsgpack-2           3000000               586 ns/op               8 B/op          1 allocs/op
BenchmarkInt0UgorjiGoCodec-2             5000000               360 ns/op               0 B/op          0 allocs/op
BenchmarkTime-2                          5000000               353 ns/op               0 B/op          0 allocs/op
BenchmarkDuration-2                     10000000               180 ns/op               0 B/op          0 allocs/op
BenchmarkByteSlice-2                     1000000              1021 ns/op            1024 B/op          1 allocs/op
BenchmarkByteArray-2                      500000              2741 ns/op            2112 B/op          4 allocs/op
BenchmarkByteSliceUgorjiGoCodec-2        2000000               647 ns/op               0 B/op          0 allocs/op
BenchmarkByteArrayUgorjiGoCodec-2        1000000              2632 ns/op            1088 B/op          3 allocs/op
BenchmarkMapStringString-2               1000000              1898 ns/op              16 B/op          4 allocs/op
BenchmarkMapStringStringPtr-2             500000              2461 ns/op              32 B/op          5 allocs/op
BenchmarkMapStringStringUgorjiGoCodec-2  1000000              1737 ns/op              16 B/op          4 allocs/op
BenchmarkMapIntInt-2                      500000              3424 ns/op             208 B/op         10 allocs/op
BenchmarkStringSlice-2                   3000000               530 ns/op              10 B/op          2 allocs/op
BenchmarkStringSlicePtr-2                1000000              1270 ns/op              26 B/op          3 allocs/op
BenchmarkStructVmihailencoMsgpack-2       100000             12732 ns/op            3152 B/op         27 allocs/op
BenchmarkStructMarshal-2                  300000              6003 ns/op            1808 B/op          8 allocs/op
BenchmarkStructUnmarshal-2                200000              5788 ns/op            1344 B/op         19 allocs/op
BenchmarkStructManual-2                   200000              6610 ns/op            2720 B/op         21 allocs/op
BenchmarkStructUgorjiGoMsgpack-2          100000             17138 ns/op            3616 B/op         70 allocs/op
BenchmarkStructUgorjiGoCodec-2            100000             21833 ns/op            7345 B/op         23 allocs/op
BenchmarkStructJSON-2                      20000             63809 ns/op            7896 B/op         26 allocs/op
BenchmarkStructGOB-2                       20000             96275 ns/op           14664 B/op        278 allocs/op
BenchmarkStructUnmarshalPartially-2       300000              5791 ns/op            2272 B/op         12 allocs/op
BenchmarkCSV-2                            200000              6971 ns/op            8748 B/op         12 allocs/op
BenchmarkCSVMsgpack-2                    1000000              1541 ns/op             384 B/op         13 allocs/op
ok      gopkg.in/vmihailenco/msgpack.v2 58.623s
```

## gopkg.in/vmihailenco/msgpack.v2 でGoのstructをエンコード・デコードするインターフェース
[Marshaler](https://godoc.org/gopkg.in/vmihailenco/msgpack.v2#Marshaler) はdeprecatedで[CustomEncoder](https://godoc.org/gopkg.in/vmihailenco/msgpack.v2#CustomEncoder)を使えとのことです。[CustomEncoder](https://godoc.org/gopkg.in/vmihailenco/msgpack.v2#CustomEncoder) の Example を見ると使い方も簡単そうです。


## gopkg.in/vmihailenco/msgpack.v2 を使うことにします

[github.com/vmihailenco/msgpack](https://github.com/vmihailenco/msgpack)も[go/codec at master · ugorji/go](https://github.com/ugorji/go/tree/master/codec)も活発にメンテナンスされているようです。

APIドキュメント [gopkg.in/vmihailenco/msgpack.v2](https://godoc.org/gopkg.in/vmihailenco/msgpack.v2)、[github.com/ugorji/go/codec](https://godoc.org/github.com/ugorji/go/codec) を見ると私は前者のほうがしっくりきました。ということで gopkg.in/vmihailenco/msgpack.v2 を使うことにします。
