---
title: "PCGと乱数生成について調べた"
date: 2023-02-06T23:11:11+09:00
---

## はじめに

テストでランダムな入力値を生成するのにどういうアルゴリズムを使うのが良いのかと調べていたのですが、
今回いろいろ知ったのでメモです。Goだとmath/randパッケージを使っておけば良いのですが、C言語だと下記のリンク先からコードをコピペ改変して使うのが良さそうです。

なお、暗号用の乱数はこの記事のスコープ外です。

## pcg32が良さそう

今回調べるまでは[Xorshift - Wikipedia](https://en.wikipedia.org/wiki/Xorshift)が処理が軽くて周期も長くて良いかなと思ってました。

が、[PCG, A Family of Better Random Number Generators | PCG, A Better Random Number Generator](https://www.pcg-random.org/index.html)の比較表を見ると、PCGのほうが良さそうです(ただ、PCGの作者によるサイトなので他の専門家の意見も聞いてみたいところではあります)。

[Download the PCG Library | PCG, A Better Random Number Generator](https://www.pcg-random.org/download.html#minimal-c-implementation)に開発者によるCとC++の実装があり、最小限のC実装は5行と非常にコンパクトです。

[Permuted congruential generator - Wikipedia](https://en.wikipedia.org/wiki/Permuted_congruential_generator)に`pcg32_fast`というのも紹介されていますが、通常は`pcg32`の通常版を使うほうが良いらしいです。

## 乱数のテスト用にTestU01というライブラリがある

[良い xorshift、悪い xorshift](https://www.cepstrum.co.jp/hobby/xorshift/xorshift.html)で生成した乱数をプロットして規則的な模様が出るケースは良くないというのを見てなるほどと思いました。一方で良いほうは感覚的にしか分からないよなと思ったのですが、[Xorshift - Wikipedia](https://en.wikipedia.org/wiki/Xorshift)や[Permuted congruential generator - Wikipedia](https://en.wikipedia.org/wiki/Permuted_congruential_generator)で紹介されていた[TestU01 - Empirical Testing of Random Number Generators](http://simul.iro.umontreal.ca/testu01/tu01.html)が良いみたいです。

[TestU01 - Wikipedia](https://en.wikipedia.org/wiki/TestU01)にも説明がありました。[TestU01 - Empirical Testing of Random Number Generators](http://simul.iro.umontreal.ca/testu01/tu01.html)に[github.com/umontreal-simul/TestU01-2009](https://github.com/umontreal-simul/TestU01-2009/)へのリンクがありました。論文のリンクもありました(が私は読んでないです)。

Ubuntu 22.04 LTSでは[testu01 ソースパッケージ](https://packages.ubuntu.com/source/jammy/testu01)があったのですが、`testu01-doc`パッケージ内にexamplesのソースが入っているけど[github.com/umontreal-simul/TestU01-2009のexamples/](https://github.com/umontreal-simul/TestU01-2009/tree/c884a9ce4e6698194e0f0ca67024dd4410975773/examples)にある`testxoshiro128plusplus.c`など一部のファイルは含まれていませんでした。

というわけでdebパッケージは使わずに[github.com/umontreal-simul/TestU01-2009](https://github.com/umontreal-simul/TestU01-2009/)のほうを取ってきて試してみました。

なぜか`configure`に実行パーミッションが付いていないので
```
sh configure
```
で実行して
```
make -j
sudo make install
```
でビルド・インストールします。

あとは`cd examples`して[testxoshiro128plusplus.c](https://github.com/umontreal-simul/TestU01-2009/blob/c884a9ce4e6698194e0f0ca67024dd4410975773/examples/testxoshiro128plusplus.c)と[testpcg32.c](https://github.com/umontreal-simul/TestU01-2009/blob/c884a9ce4e6698194e0f0ca67024dd4410975773/examples/testpcg32.c)の先頭のコメントに書いてあるコマンドでコンパイルして実行します。

`bbattery_SmallCrush`だとすぐ終わるのですが、ソース内のコメントに`bbattery_BigCrush`に変えてもよいとあり、`BigCrush`は[Xorshift - Wikipedia](https://en.wikipedia.org/wiki/Xorshift)でも言及されていたなということで試してみました。どちらも2時間ぐらいかかってテストはパスしていました。実行中`htop`で見てみると、CPUの1つのコアが100%近く使われて、行程が変わると別の1つのコアが100%近く使われるという挙動になっていました。複数コアを並列では使ってくれないようです。

[PCGのblog記事一覧](https://www.pcg-random.org/blog/)でもTestU01が何度か出てきてました(が、今回は読んでないです)。

## シード値について

### 横道: Xorshift用に良いシード値を生成する方法 SplitMix64

[Xorshift - Wikipedia](https://en.wikipedia.org/wiki/Xorshift)のInitializationの項でSplitMix64 generatorというのを知りました。
[良い xorshift、悪い xorshift](https://www.cepstrum.co.jp/hobby/xorshift/xorshift.html)でも「レジスタ内に0のbitが固まって多く存在すると、しばらくの間0が多く含まれる値が出力されます」と説明されていました。
ということでSplitMix64でシード値を加工して使うのがお勧めらしいです。

### pcg32のシード値について

https://www.pcg-random.org/using-pcg-c-basic.html#pcg32-srandom-r-rngptr-initstate-initseq によると`/dev/random`が使えればそれを使うか、quick and dirtyにしたい場合は現在時刻とRNGの状態変数のアドレスを使うと良いらしいです。

## 指定した範囲の整数の乱数を効率よく生成するアルゴリズム

https://github.com/golang/go/blob/go1.20/src/math/rand/rand.go#L151-L173 のコードを見て
https://lemire.me/blog/2016/06/27/a-fast-alternative-to-the-modulo-reduction/ と https://lemire.me/blog/2016/06/30/fast-random-shuffling/ の記事を読みました。
さらに[Efficiently Generating a Number in a Range | PCG, A Better Random Number Generator](https://www.pcg-random.org/posts/bounded-rands.html)でも同じ題材について詳しく書かれていました。

`[0, n)`の整数の乱数を生成する際、バイアスありでも良い場合は`pcg32`で`[0, 2^32)`の整数`x`を生成して`x % n`が一番シンプルです。が、剰余は遅いので、代わりに乗算とシフト演算で算出する方法が紹介されています。さらに[Rejection sampling - Wikipedia](https://en.wikipedia.org/wiki/Rejection_sampling)という手法でバイアス無しにする方法も紹介されていました。

記事からリンクされていた https://github.com/lemire/Code-used-on-Daniel-Lemire-s-blog/tree/master/2016/06/25 のコードを試してみた結果は以下の通りです。

```
~/ghq/github.com/lemire/Code-used-on-Daniel-Lemire-s-blog/2016/06/25$ ./fastrange
N = 31
modsum(z,N,accesses,nmbr):  30.01 cycles per operation
fastsum(z,N,accesses,nmbr):  2.36 cycles per operation
N = 1500
modsum(z,N,accesses,nmbr):  26.60 cycles per operation
fastsum(z,N,accesses,nmbr):  2.67 cycles per operation
N = 15000
modsum(z,N,accesses,nmbr):  21.27 cycles per operation
fastsum(z,N,accesses,nmbr):  2.05 cycles per operation
N = 32
modsum(z,N,accesses,nmbr):  23.44 cycles per operation
fastsum(z,N,accesses,nmbr):  1.86 cycles per operation
maskedsum(z,N,accesses,nmbr):  1.49 cycles per operation
N = 4096
modsum(z,N,accesses,nmbr):  19.65 cycles per operation
fastsum(z,N,accesses,nmbr):  1.74 cycles per operation
maskedsum(z,N,accesses,nmbr):  1.36 cycles per operation
N = 65536
modsum(z,N,accesses,nmbr):  17.98 cycles per operation
fastsum(z,N,accesses,nmbr):  1.98 cycles per operation
maskedsum(z,N,accesses,nmbr):  1.61 cycles per operation
```

あと、[Efficiently Generating a Number in a Range | PCG, A Better Random Number Generator](https://www.pcg-random.org/posts/bounded-rands.html)の最後に書かれていたのですが、nが2^32未満の場合、uint64_tの乱数を生成するよりuint32_tの乱数を生成してそれを使うほうが速いそうです。Goのmath/randのIntnもそういう実装になっていました。 https://github.com/golang/go/blob/go1.20/src/math/rand/rand.go#L175-L185

自分でテストで使うケースを考えると、ほとんどの場合はnは2^32未満で使うと思うので、pcg32だけ使っておけば良いかもと思いました。

## 効率良くシャッフルするアルゴリズム Fisher–Yates shuffle

[math/rand.Rand.Shuffle](https://github.com/golang/go/blob/go1.20/src/math/rand/rand.go#L243-L266)のコメントで[Fisher–Yates shuffle - Wikipedia](https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle)を知りました。[Fast random shuffling – Daniel Lemire's blog](https://lemire.me/blog/2016/06/30/fast-random-shuffling/)の冒頭でも紹介されていました。

記事からリンクされていた https://github.com/lemire/Code-used-on-Daniel-Lemire-s-blog/tree/master/2016/06/29 のコードを試してみた結果は以下の通りです。

```
~/ghq/github.com/lemire/Code-used-on-Daniel-Lemire-s-blog/2016/06/29$ ./shuffle
Shuffling arrays of size 10000
Time reported in number of cycles per array element.
Tests assume that array is in cache as much as possible.
shuffle_pcg(testvalues,size)                                :  33.20 cycles per input key
shuffle_pcg_go(testvalues,size)                             :  33.15 cycles per input key
shuffle_pcg_java(testvalues,size)                           :  16.42 cycles per input key
shuffle_pcg_divisionless(testvalues,size)                   :  3.75 cycles per input key
shuffle_pcg_divisionless_with_slight_bias(testvalues,size)  :  3.43 cycles per input key
```

## 横道: Daniel Lemireさんはsimdjsonの作者でもある

https://lemire.me/blog/ から https://github.com/lemire を見て気づいたのですが、Daniel Lemireさんはsimdjsonの作者でもあったんですね。それと、他のブログ記事もいくつかチラ見したのですが、いろいろ面白そうな記事があったので、いつか読んで試してみたいところです。

