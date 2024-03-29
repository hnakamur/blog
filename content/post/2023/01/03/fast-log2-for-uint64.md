---
title: "uint64で高速にLog2を計算する方法を知った"
date: 2023-01-03T17:09:58+09:00
lastmod: 2023-01-10T21:19:00+09:00
---
## はじめに

[kazuhoさんのツイート](https://twitter.com/kazuho/status/1610109662346752002)とソースを見て、本題のパーセンタイル値をインクリメンタルに更新する方法の前に、
[`static uint64_t ullog2(uint64_t x)`](https://github.com/h2o/h2o/blob/0f08b675c8244fc4552a93e9b35271ecf5e0f8fa/deps/libgkc/gkc.c#L109-L127)というuint64の整数のlog2を高速に計算する関数に興味がわいて調べてみたのでメモです。

試したコードは[hnakamur/log2_experiment](https://github.com/hnakamur/log2_experiment)に置いてます。

## 2022-01-10追記 その後さらに更新しました

2022-01-04追記の説明、今から見ると自分でもよくわかりませんが、`x=0`では呼ばないという前提で以下のように変えました。

```go
// ILog2 calculates log2 of a uint64 value.
// Ported from
// https://github.com/h2o/h2o/pull/3177/files
func ILog2(x uint64) int64 {
	return 63 - int64(bits.LeadingZeros64(x))
}
```
元の`x |= (x >> 1)`などを並べたコードも条件分岐がないというのが利点とあったので、上のコードも条件分岐無しのほうが良いかなということで。

なお、`bits.LeadingZeros64(x)`も `__builtin_clzll(x)`も`x=0`のときは64になるのは同じでした。上の関数は`x=0`では呼ばない前提です。

[herumiさんとのその後のやり取り](https://twitter.com/herumi/status/1610586811860127745)で、倍精度浮動小数点数での`math.Log(float64)`のほうが正しくないケースがあると教えていただきました。

そこで[The GNU MPFR Library](https://www.mpfr.org/)というライブラリを使って[ilog2_ref.c](https://github.com/hnakamur/log2_experiment/blob/47873251e237dc5fdf43cdf20500aadc4ae9d3dd/c/ilog2_ref.c)でlog2をfloat64より高精度で計算して`63 - __builtin_clzll(x)`と比べてみた[ilog2_test.c](https://github.com/hnakamur/log2_experiment/blob/47873251e237dc5fdf43cdf20500aadc4ae9d3dd/c/ilog2_test.c)ところ、`x>=1`について[check_fn](https://github.com/hnakamur/log2_experiment/blob/47873251e237dc5fdf43cdf20500aadc4ae9d3dd/c/ilog2_test.c#L77-L89)で指定した入力値については全て一致することが確認できました。そして、テストしてない値についても`__builtin_clzll(x)`が同じ値になればそこから先は同じなので、`x>=1`については大丈夫だという確信が持てました。

Goの`bits.LeadingZeros64(x)`は`__builtin_clzll(x)`と同等なのでこちらも大丈夫です。念のため[ilog2_ref.c](https://github.com/hnakamur/log2_experiment/blob/47873251e237dc5fdf43cdf20500aadc4ae9d3dd/c/ilog2_ref.c)の出力と突き合わせる[テスト](https://github.com/hnakamur/log2_experiment/blob/47873251e237dc5fdf43cdf20500aadc4ae9d3dd/log2_test.go)も書いて確認しました。

## 2022-01-04追記 herumiさんのツイートでさらに別の実装を知った

* [一旦doubleに変換する方式](https://twitter.com/herumi/status/1610248792254844929)
* `__builtin_clzll`を使う方式。[Ilog2 by herumi · Pull Request #3177 · h2o/h2o](https://github.com/h2o/h2o/pull/3177)。
    * [テストコード](https://github.com/herumi/misc/blob/main/ilog2.c)

これを見て自分でも試してみました。

* [math.hのlogと比較してみました](https://wandbox.org/permlink/a103Ixk5NYiYfpAL)。
* [Goに移植してみた](https://github.com/hnakamur/log2_experiment/commit/87c3d50d211a3ba4c6f38ee65074c81dd45b3a32)

```go
// ILog2 calculates log2 of a uint64 value.
// Ported from
// https://github.com/h2o/h2o/pull/3177/files
func ILog2(x uint64) int64 {
	if x == 0 {
		return 0
	}
	return 63 - int64(bits.LeadingZeros64(x))
}

// ILog2B calculates log2 of a uint64 value.
// Ported from
// https://twitter.com/herumi/status/1610248792254844929
func ILog2B(x uint64) int64 {
	f := float64(x)
	v := math.Float64bits(f)
	return int64(v>>52) - 1023
}
```

そもそもlogは0では無限大になるので上のILog2の`return 0`は変ではあるのですが、Cでの実装の結果に合わせるとこれが必要でした。

math.Logを使う方式と比較したテストの結果は以下のようになりました。

```
=== RUN   TestILog2
    log2_test.go:45: result mismatch, x=0, got=0, want=-9223372036854775808
    log2_test.go:45: result mismatch, x=1ffffffffffff, got=48, want=49
    log2_test.go:45: result mismatch, x=3ffffffffffff, got=49, want=50
    log2_test.go:45: result mismatch, x=7ffffffffffff, got=50, want=51
    log2_test.go:45: result mismatch, x=fffffffffffff, got=51, want=52
    log2_test.go:45: result mismatch, x=1fffffffffffff, got=52, want=53
    log2_test.go:45: result mismatch, x=3fffffffffffff, got=53, want=54
    log2_test.go:45: result mismatch, x=7fffffffffffff, got=54, want=55
    log2_test.go:45: result mismatch, x=ffffffffffffff, got=55, want=56
    log2_test.go:45: result mismatch, x=1ffffffffffffff, got=56, want=57
    log2_test.go:45: result mismatch, x=3ffffffffffffff, got=57, want=58
    log2_test.go:45: result mismatch, x=7ffffffffffffff, got=58, want=59
    log2_test.go:45: result mismatch, x=fffffffffffffff, got=59, want=60
    log2_test.go:45: result mismatch, x=1fffffffffffffff, got=60, want=61
    log2_test.go:45: result mismatch, x=3fffffffffffffff, got=61, want=62
    log2_test.go:45: result mismatch, x=7fffffffffffffff, got=62, want=63
    log2_test.go:45: result mismatch, x=ffffffffffffffff, got=63, want=64
--- FAIL: TestILog2 (0.00s)
=== RUN   TestILog2B
    log2_test.go:45: result mismatch, x=0, got=-1023, want=-9223372036854775808
    log2_test.go:45: result mismatch, x=1ffffffffffff, got=48, want=49
    log2_test.go:45: result mismatch, x=3ffffffffffff, got=49, want=50
    log2_test.go:45: result mismatch, x=7ffffffffffff, got=50, want=51
    log2_test.go:45: result mismatch, x=fffffffffffff, got=51, want=52
    log2_test.go:45: result mismatch, x=1fffffffffffff, got=52, want=53
--- FAIL: TestILog2B (0.00s)
=== RUN   TestLog2ByAvernar
    log2_test.go:45: result mismatch, x=0, got=0, want=-9223372036854775808
    log2_test.go:45: result mismatch, x=1ffffffffffff, got=48, want=49
    log2_test.go:45: result mismatch, x=3ffffffffffff, got=49, want=50                                                                                                                                                  log2_test.go:45: result mismatch, x=7ffffffffffff, got=50, want=51                                                                                                                                                  log2_test.go:45: result mismatch, x=fffffffffffff, got=51, want=52                                                                                                                                                  log2_test.go:45: result mismatch, x=1fffffffffffff, got=52, want=53                                                                                                                                                 log2_test.go:45: result mismatch, x=3fffffffffffff, got=53, want=54                                                                                                                                                 log2_test.go:45: result mismatch, x=7fffffffffffff, got=54, want=55
    log2_test.go:45: result mismatch, x=ffffffffffffff, got=55, want=56
    log2_test.go:45: result mismatch, x=1ffffffffffffff, got=56, want=57
    log2_test.go:45: result mismatch, x=3ffffffffffffff, got=57, want=58
    log2_test.go:45: result mismatch, x=7ffffffffffffff, got=58, want=59
    log2_test.go:45: result mismatch, x=fffffffffffffff, got=59, want=60
    log2_test.go:45: result mismatch, x=1fffffffffffffff, got=60, want=61
    log2_test.go:45: result mismatch, x=3fffffffffffffff, got=61, want=62
    log2_test.go:45: result mismatch, x=7fffffffffffffff, got=62, want=63
    log2_test.go:45: result mismatch, x=ffffffffffffffff, got=63, want=64
--- FAIL: TestLog2ByAvernar (0.00s)
```

ベンチマークの結果。

```
$ go test -v -run ^$ -bench . -benchmem
goos: linux
goarch: amd64
pkg: github.com/hnakamur/log2_experiment
cpu: AMD Ryzen 7 PRO 4750GE with Radeon Graphics
BenchmarkILog2
BenchmarkILog2-16                4560423               245.8 ns/op             0 B/op          0 allocs/op
BenchmarkILog2B
BenchmarkILog2B-16               4428868               247.3 ns/op             0 B/op          0 allocs/op
BenchmarkLogByAvernar
BenchmarkLogByAvernar-16          782736              1566 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernarU8
BenchmarkLogByAvernarU8-16        794042              1561 ns/op               0 B/op          0 allocs/op
BenchmarkLogByStdlib
BenchmarkLogByStdlib-16            80896             15269 ns/op               0 B/op          0 allocs/op
PASS
ok      github.com/hnakamur/log2_experiment     7.322s
```

## アルゴリズム

### 一番近い2のべき乗から1を引いた値の計算

[algorithm - How does one find the floor of the log-base-2 of an n-bit integer using bitwise operators? - Stack Overflow](https://stackoverflow.com/questions/68677658/how-does-one-find-the-floor-of-the-log-base-2-of-an-n-bit-integer-using-bitwise)の[回答](https://stackoverflow.com/a/68681396/1391518)の1によると以下のコードはx以上の一番近い2のべき乗から1を引いた値を計算しているそうです。

```
    x |= (x >> 1);
    x |= (x >> 2);
    x |= (x >> 4);
    x |= (x >> 8);
    x |= (x >> 16);
    x |= (x >> 32);
```

その後の説明を読んでもピンとこなかったのですが、実際に試すとわかりました(なお以下のコードはちゃんとしたテストではないですが、ちょっと結果を見たいときに私はこういうことをしています)。

```
func TestDebugPow2Minus1Good(t *testing.T) {
	fDebug := func(n uint64) uint64 {
		fmt.Printf("fDebug start n=%#0b\n", n)
		n |= n >> 1
		fmt.Printf("fDebug #1    n=%#0b\n", n)
		n |= n >> 2
		fmt.Printf("fDebug #2    n=%#0b\n", n)
		n |= n >> 4
		fmt.Printf("fDebug #3    n=%#0b\n", n)
		n |= n >> 8
		fmt.Printf("fDebug #4    n=%#0b\n", n)
		n |= n >> 16
		fmt.Printf("fDebug #5    n=%#0b\n", n)
		n |= n >> 32
		fmt.Printf("fDebug final n=%#0b\n", n)
		return n
	}
	fDebug(0x80000000000)
}
```

```
$ go test -v -run TestDebugPow2Minus1Good
=== RUN   TestDebugPow2Minus1
fDebug start n=0b10000000000000000000000000000000000000000000
fDebug #1    n=0b11000000000000000000000000000000000000000000
fDebug #2    n=0b11110000000000000000000000000000000000000000
fDebug #3    n=0b11111111000000000000000000000000000000000000
fDebug #4    n=0b11111111111111110000000000000000000000000000
fDebug #5    n=0b11111111111111111111111111111111000000000000
fDebug final n=0b11111111111111111111111111111111111111111111
…(略)…
```

シフトの量を変えて繰り返すと一番左の1のビットの右が全て1になるというわけです。

途中で`|=`でnを更新しているのは重要です。下記はそうしないとうまくいかないことを確認したものです。

```
func TestDebugPow2Minus1Bad(t *testing.T) {
	gDebug := func(n uint64) uint64 {
		fmt.Printf("gDebug start n=%#0b\n", n)
		n1 := n >> 1
		fmt.Printf("gDebug      n1=%#0b, n|n1=%#0b\n", n1, n|n1)
		n2 := n >> 2
		fmt.Printf("gDebug      n2=%#0b, n|n1|n2=%#0b\n", n2, n|n1|n2)
		n4 := n >> 4
		fmt.Printf("gDebug      n4=%#0b, n|n1|n2|n4=%#0b\n", n4, n|n1|n2|n4)
		n8 := n >> 8
		fmt.Printf("gDebug      n8=%#0b, n|n1|n2|n4|n8=%#0b\n", n8, n|n1|n2|n4|n8)
		n16 := n >> 16
		fmt.Printf("gDebug     n16=%#0b, n|n1|n2|n4|n8|n16=%#0b\n", n16, n|n1|n2|n4|n8|n16)
		n32 := n >> 32
		fmt.Printf("gDebug     n32=%#0b, n|n1|n2|n4|n8|n16|n32=%#0b\n", n32, n|n1|n2|n4|n8|n16|n32)
		return n | n1 | n2 | n4 | n8 | n16 | n32
	}
	gDebug(0x80000000000)
}
```

```
$ go test -v -run TestDebugPow2Minus1Bad
=== RUN   TestDebugPow2Minus1Bad
gDebug start n=0b10000000000000000000000000000000000000000000
gDebug      n1=0b1000000000000000000000000000000000000000000, n|n1=0b11000000000000000000000000000000000000000000
gDebug      n2=0b100000000000000000000000000000000000000000, n|n1|n2=0b11100000000000000000000000000000000000000000
gDebug      n4=0b1000000000000000000000000000000000000000, n|n1|n2|n4=0b11101000000000000000000000000000000000000000
gDebug      n8=0b100000000000000000000000000000000000, n|n1|n2|n4|n8=0b11101000100000000000000000000000000000000000
gDebug     n16=0b1000000000000000000000000000, n|n1|n2|n4|n8|n16=0b11101000100000001000000000000000000000000000
gDebug     n32=0b100000000000, n|n1|n2|n4|n8|n16|n32=0b11101000100000001000000000000000100000000000
…(略)…
```

### テーブルをひくときのインデクスの計算

[h2o/gkc.c at master · h2o/h2o](https://github.com/h2o/h2o/blob/0f08b675c8244fc4552a93e9b35271ecf5e0f8fa/deps/libgkc/gkc.c#L126)の`((x & ~(x>>1))*debruijn_magic)>>58`の`(x & ~(x>>1)`の部分は1番左のビットの残して右側の1が並んだ部分を0クリアしているんですね。シフトが58なのは上の[回答](https://stackoverflow.com/a/68681396/1391518)の3に説明がありました。64ビットの場合はlog2(64)=6ビットだけが必要ということで(64-6)=58ビット右シフトしているとのことです。

[c - Fast computing of log2 for 64-bit integers - Stack Overflow](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)に32ビットの例もあって、そちらはlog2(32)=5ビットなので(32-5)=27ビット右シフトしています。

[上の回答のコメント](https://stackoverflow.com/questions/68677658/how-does-one-find-the-floor-of-the-log-base-2-of-an-n-bit-integer-using-bitwise#comment121383127_68681396)に
[de Bruijn sequence - Wikipedia](https://en.wikipedia.org/wiki/De_Bruijn_sequence)の[Construction](https://en.wikipedia.org/wiki/De_Bruijn_sequence#Construction)へのリンクが貼られていました。

さらに探すと[c - Fast computing of log2 for 64-bit integers - Stack Overflow](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers)の[Avernarさんの回答](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)で`((x & ~(x>>1))*debruijn_magic)>>58`の`((x & ~(x>>1))`をせずに`(x*C)>>58`で済むようなCとルックアップテーブルを使う方法も紹介されていました。Cはde Bruijn sequenceのB(2, 6)の1つである0x07EDD5E59A4E28C2を2で割った値です。

そこからリンクされていた[Find the log base 2 of an N-bit integer in O(lg(N)) operations with multiply and lookup](http://graphics.stanford.edu/~seander/bithacks.html#IntegerLogDeBruijn)に

> On December 10, 2009, Mark Dickinson shaved off a couple operations by requiring v be rounded up to one less than the next power of 2 rather than the power of 2. 

とありました。

さらに、そこから[Count the consecutive zero bits (trailing) on the right with multiply and lookup](http://graphics.stanford.edu/~seander/bithacks.html#ZerosOnRightMultLookup)へのリンクもあり

> More information can be found by reading the paper Using de Bruijn Sequences to Index 1 in a Computer Word by Charles E. Leiserson, Harald Prokof, and Keith H. Randall. 

と書かれていました。ここはリンク切れでしたが検索すると http://supertech.csail.mit.edu/papers/debruijn.pdf にありました。

これを読むとルックアップテーブルはパーフェクトハッシュになっているそうです。それを知って改めて実装のルックアップテーブルを見ると0～63が1回ずつ出現していることに気付いてなるほどとなりました。

## 正しい結果が出る値の範囲を調べてみた

まず入力が0の場合はmath.Log2(0)はマイナス無限大ですが、今回の実装は0になります。

次に、あるxまでは正しい結果を返し、それを超えると正しくない結果を返すと仮定して(この仮定が正しいかは不明)、正しい結果(`math.Floor(math.Log2(x))`)を返すxの最大値を調べてみると0xffffffffffff4bffでした。
0xffffffffffff4bff+1～0xffffffffffffffff(=math.MaxUint64)では正しい値は64ですが、今回の実装は63を返します。

[flyingmutant/rapid: Rapid is a Go library for property-based testing that supports state machine ("stateful" or "model-based") testing and fully automatic test case minimization ("shrinking")](https://github.com/flyingmutant/rapid)を使って1～0xffffffffffff4bffの値で1億回(100,000,000)テストしてみた範囲では全て正しい値を返していました。

```
$ go test -v -run TestLog2ByAvernarPropertyEqualToStdlib -rapid.checks=100000000
=== RUN   TestLog2ByAvernarPropertyEqualToStdlib
    log2_test.go:118: [rapid] OK, passed 100000000 tests (48.773136105s)
--- PASS: TestLog2ByAvernarPropertyEqualToStdlib (48.77s)
PASS
ok      github.com/hnakamur/log2_experiment     48.779s
```

## ルックアップテーブルの作り方を確認

以下のコードを書いて生成したテーブルが[Avernarさんの回答](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)のテーブルに一致することを確認しました。
```
func buildTable(c uint64) []uint8 {
	v := make([]uint8, 64)
	for i := uint64(0); i < 64; i++ {
		x := uint64(1) << i
		x |= x - 1
		v[(x*c)>>58] = uint8(i)
	}
	return v
}

var u8Table = []uint8{
	0, 58, 1, 59, 47, 53, 2, 60, 39, 48, 27, 54, 33, 42, 3, 61,
	51, 37, 40, 49, 18, 28, 20, 55, 30, 34, 11, 43, 14, 22, 4, 62,
	57, 46, 52, 38, 26, 32, 41, 50, 36, 17, 19, 29, 10, 13, 21, 56,
	45, 25, 31, 35, 16, 9, 12, 44, 24, 15, 8, 23, 7, 6, 5, 63,
}
```

```
func TestBuildTableAvernar(t *testing.T) {
	got := buildTable(0x03f6eaf2cd271461)
	want := u8Table
	if !slices.Equal(got, want) {
		t.Errorf("table mismatch, got=%v, want=%v", got, want)
	}
}
```

[Desmond Humeさんの回答](https://stackoverflow.com/a/11398748/1391518)では`(value - (value >> 1))*0x07EDD5E59A4E28C2)`としているのに対し、[Avernarさんの回答](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)では`(value - (value >> 1))`の部分を`value`と2倍弱にする代わりに0x07EDD5E59A4E28C2を半分にした値を使っているのでなんとなく帳尻があっているのかなとぼんやり思いました。

[Avernarさんの回答](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)のルックアップテーブルは[Desmond Humeさんの回答](https://stackoverflow.com/a/11398748/1391518)のルックアップテーブル(下記に抜粋)を1つ左にローテートしたものになっていることに気付きました。

```
const int tab64[64] = {
    63,  0, 58,  1, 59, 47, 53,  2,
    60, 39, 48, 27, 54, 33, 42,  3,
    61, 51, 37, 40, 49, 18, 28, 20,
    55, 30, 34, 11, 43, 14, 22,  4,
    62, 57, 46, 52, 38, 26, 32, 41,
    50, 36, 17, 19, 29, 10, 13, 21,
    56, 45, 25, 31, 35, 16,  9, 12,
    44, 24, 15,  8, 23,  7,  6,  5};
```

de Bruijn sequence自体はローテートした値でも良いのですが、自分で2つほど試してみたところ`(x*C)>>58`のCはどんなB(2, 6)の半分でも良いわけではないということが分かりました。[nwellnhofさんのコメント](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers#comment75512059_23000588)に`0x07EDD5E59A4E28C2`は先頭に0が6ビット連続して、その後に1が6ビット連続しているのが良いのではないかとあったのですが、私にはよくわかりませんでした。

先頭に0が6ビット連続して、その後に1が6ビット連続していること自体は以下のテストで確認できました(実際はwantを空文字で実行してエラーメッセージからコピペしました)。

```
func TestBinAvernarDeBruijn(t *testing.T) {
	got := fmt.Sprintf("%#064b", 0x07EDD5E59A4E28C2)
	want := "0b0000011111101101110101011110010110011010010011100010100011000010"
	if got != want {
		t.Errorf("result mismatch, got=%s, want=%s", got, want)
	}
}
```

## ベンチマーク

* Log2は[h2o内のullog2](https://github.com/h2o/h2o/blob/0f08b675c8244fc4552a93e9b35271ecf5e0f8fa/deps/libgkc/gkc.c#L109-L127)の移植版
* LogByAvernarは[Avernarさんの回答](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)の移植版
* LogByAvernarU8は[Avernarさんの回答](https://stackoverflow.com/questions/11376288/fast-computing-of-log2-for-64-bit-integers/23000588#23000588)のルックアップテーブルを`[]uint64`から`[]uint8`に買えた版

```
hnakamur@thinkcentre2:~/ghq/github.com/hnakamur/log2_experiment$ go test -v -run ^$ -bench . -benchmem
goos: linux
goarch: amd64
pkg: github.com/hnakamur/log2_experiment
cpu: AMD Ryzen 7 PRO 4750GE with Radeon Graphics
BenchmarkLog2
BenchmarkLog2-16                  616564              1840 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernar
BenchmarkLogByAvernar-16           793698              1554 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernarU8
BenchmarkLogByAvernarU8-16         751774              1570 ns/op               0 B/op          0 allocs/op
BenchmarkLogByStdlib
BenchmarkLogByStdlib-16            78012             15425 ns/op               0 B/op          0 allocs/op
PASS
ok      github.com/hnakamur/log2_experiment     6.681s
hnakamur@thinkcentre2:~/ghq/github.com/hnakamur/log2_experiment$ go test -v -run ^$ -bench . -benchmem
goos: linux
goarch: amd64
pkg: github.com/hnakamur/log2_experiment
cpu: AMD Ryzen 7 PRO 4750GE with Radeon Graphics
BenchmarkLog2
BenchmarkLog2-16                  650958              1871 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernar
BenchmarkLogByAvernar-16           793904              1551 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernarU8
BenchmarkLogByAvernarU8-16         754802              1537 ns/op               0 B/op          0 allocs/op
BenchmarkLogByStdlib
BenchmarkLogByStdlib-16            77786             14849 ns/op               0 B/op          0 allocs/op
PASS
ok      github.com/hnakamur/log2_experiment     7.297s
hnakamur@thinkcentre2:~/ghq/github.com/hnakamur/log2_experiment$ go test -v -run ^$ -bench . -benchmem
goos: linux
goarch: amd64
pkg: github.com/hnakamur/log2_experiment
cpu: AMD Ryzen 7 PRO 4750GE with Radeon Graphics
BenchmarkLog2
BenchmarkLog2-16                  628119              1896 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernar
BenchmarkLogByAvernar-16           745449              1553 ns/op               0 B/op          0 allocs/op
BenchmarkLogByAvernarU8
BenchmarkLogByAvernarU8-16         677878              1564 ns/op               0 B/op          0 allocs/op
BenchmarkLogByStdlib
BenchmarkLogByStdlib-16            66051             15387 ns/op               0 B/op          0 allocs/op
PASS
ok      github.com/hnakamur/log2_experiment     6.174s
```
