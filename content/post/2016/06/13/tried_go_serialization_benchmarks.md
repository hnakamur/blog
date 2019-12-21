+++
Categories = []
Description = ""
Tags = ["golang","serialization"]
date = "2016-06-13T23:34:16+09:00"
title = "Goのシリアライゼーションのベンチマークを自分でも試してみた"

+++
2015年12月の記事ですが[最速という噂のFlatbuffersの速度のヒミツと、導入方法の紹介(Go) - Qiita](http://qiita.com/shibukawa/items/878c5fe8ec09935fccd2)を読んで、「gobは遅いのかー、残念」、「一方Flatbuffersは面倒そうだなー」と思っていました。

で、[alecthomas/go_serialization_benchmarks at 48e2bb8b7b6c38c24c88a0b027b30c80175a7b59](https://github.com/alecthomas/go_serialization_benchmarks/tree/48e2bb8b7b6c38c24c88a0b027b30c80175a7b59#results)のベンチマーク結果を見てみると、あれgob遅くないよ、というかVmihailencoMsgpackとUgorjiCodecMsgpackより速くなってました。

自宅サーバ (NEC Express5800/S70)でもベンチマークを試してみました。

```
$ go test -bench . -benchmem | tee bench.txt                                                                                                                                               

A test suite for benchmarking various Go serialization methods.

See README.md for details on running the benchmarks.

PASS
BenchmarkMsgpMarshal-2                   3000000               423 ns/op             128 B/op          1 allocs/op
BenchmarkMsgpUnmarshal-2                 2000000               741 ns/op             112 B/op          3 allocs/op
BenchmarkVmihailencoMsgpackMarshal-2      500000              3107 ns/op             368 B/op          6 allocs/op
BenchmarkVmihailencoMsgpackUnmarshal-2    300000              4469 ns/op             352 B/op         13 allocs/op
BenchmarkJsonMarshal-2                    200000              7070 ns/op            1232 B/op         10 allocs/op
BenchmarkJsonUnmarshal-2                  200000              7331 ns/op             416 B/op          7 allocs/op
BenchmarkEasyJsonMarshal-2                500000              3116 ns/op             784 B/op          5 allocs/op
BenchmarkEasyJsonUnmarshal-2              500000              2936 ns/op             160 B/op          4 allocs/op
BenchmarkBsonMarshal-2                    500000              3031 ns/op             392 B/op         10 allocs/op
BenchmarkBsonUnmarshal-2                  500000              4047 ns/op             248 B/op         21 allocs/op
BenchmarkGobMarshal-2                    1000000              2189 ns/op              48 B/op          2 allocs/op
BenchmarkGobUnmarshal-2                  1000000              2226 ns/op             112 B/op          3 allocs/op
BenchmarkXdrMarshal-2                     500000              3862 ns/op             456 B/op         21 allocs/op
BenchmarkXdrUnmarshal-2                   500000              2885 ns/op             239 B/op         11 allocs/op
BenchmarkUgorjiCodecMsgpackMarshal-2      200000              7052 ns/op            2752 B/op          8 allocs/op
BenchmarkUgorjiCodecMsgpackUnmarshal-2    200000              7586 ns/op            3008 B/op          6 allocs/op
BenchmarkUgorjiCodecBincMarshal-2         200000              7347 ns/op            2784 B/op          8 allocs/op
BenchmarkUgorjiCodecBincUnmarshal-2       200000              8163 ns/op            3168 B/op          9 allocs/op
BenchmarkSerealMarshal-2                  200000              7518 ns/op             912 B/op         21 allocs/op
BenchmarkSerealUnmarshal-2                200000              7039 ns/op            1008 B/op         34 allocs/op
BenchmarkBinaryMarshal-2                  500000              2757 ns/op             256 B/op         16 allocs/op
BenchmarkBinaryUnmarshal-2                500000              3057 ns/op             336 B/op         22 allocs/op
BenchmarkFlatBuffersMarshal-2            3000000               573 ns/op               0 B/op          0 allocs/op
BenchmarkFlatBuffersUnmarshal-2          3000000               538 ns/op             112 B/op          3 allocs/op
BenchmarkCapNProtoMarshal-2              2000000               874 ns/op              56 B/op          2 allocs/op
BenchmarkCapNProtoUnmarshal-2            2000000               817 ns/op             200 B/op          6 allocs/op
BenchmarkCapNProto2Marshal-2             1000000              1991 ns/op             244 B/op          3 allocs/op
BenchmarkCapNProto2Unmarshal-2           1000000              2064 ns/op             320 B/op          6 allocs/op
BenchmarkHproseMarshal-2                 1000000              1797 ns/op             479 B/op          8 allocs/op
BenchmarkHproseUnmarshal-2                500000              2250 ns/op             320 B/op         10 allocs/op
BenchmarkProtobufMarshal-2               1000000              2052 ns/op             200 B/op          7 allocs/op
BenchmarkProtobufUnmarshal-2             1000000              1700 ns/op             192 B/op         10 allocs/op
BenchmarkGoprotobufMarshal-2             1000000              1141 ns/op             312 B/op          4 allocs/op
BenchmarkGoprotobufUnmarshal-2           1000000              1721 ns/op             432 B/op          9 allocs/op
BenchmarkGogoprotobufMarshal-2           5000000               291 ns/op              64 B/op          1 allocs/op
BenchmarkGogoprotobufUnmarshal-2         3000000               445 ns/op              96 B/op          3 allocs/op
BenchmarkColferMarshal-2                 5000000               260 ns/op              64 B/op          1 allocs/op
BenchmarkColferUnmarshal-2               5000000               387 ns/op             112 B/op          3 allocs/op
BenchmarkGencodeMarshal-2                5000000               322 ns/op              80 B/op          2 allocs/op
BenchmarkGencodeUnmarshal-2              5000000               392 ns/op             112 B/op          3 allocs/op
BenchmarkGencodeUnsafeMarshal-2         10000000               196 ns/op              48 B/op          1 allocs/op
BenchmarkGencodeUnsafeUnmarshal-2        5000000               322 ns/op              96 B/op          3 allocs/op
BenchmarkXDR2Marshal-2                   5000000               333 ns/op              64 B/op          1 allocs/op
BenchmarkXDR2Unmarshal-2                 5000000               313 ns/op              32 B/op          2 allocs/op
ok      github.com/alecthomas/go_serialization_benchmarks       81.009s
$ go version
go version go1.6.2 linux/amd64
```

こちらも同じくgobはVmihailencoMsgpackとUgorjiCodecMsgpackより速かったです。Goのバージョンの違いなのかライブラリの進化なのかは調べてないですが、いつのまにか逆転していたようです。

ということで、Go以外の言語との相互運用性を考えなくて良いなら、gobもシリアライゼーションのライブラリ選択の候補に入れて良さそうと思いました。[gob](https://golang.org/pkg/encoding/gob/)を見る限りはstructに対して特に何もしなくても使えるようなのでお手軽さでは一番良さそうですし。
