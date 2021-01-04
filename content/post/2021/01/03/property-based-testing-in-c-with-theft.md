---
title: "theftを使ってC言語で property based testing を試してみた"
date: 2021-01-03T17:49:10+09:00
---

## はじめに

これまで私は Go 言語では [flyingmutant/rapid](https://github.com/flyingmutant/rapid) ([例](https://github.com/hnakamur/property-based-test-example))、 C++ では 
[emil-e/rapidcheck](https://github.com/emil-e/rapidcheck) ([例](https://github.com/hnakamur/rapidcheck-experiment)) を使って property based testing を試してみました。

先日 [QuickCheck in Every Language - Hypothesis](https://hypothesis.works/articles/quickcheck-in-every-language/) で C言語用にも [silentbicycle/theft](https://github.com/silentbicycle/theft) というライブラリーがあることを知ったので試してみました。

まず README からリンクされている [doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md) と作者のブログ記事 [Introducing theft Property-Based Testing for C](https://spin.atomicobject.com/2014/09/17/property-based-testing-c/) を眺めたのですが、サンプルコードの断片はありますが完全なコードがありませんでした。

ブログ記事からリンクされている [atomicobject/heatshrink: data compression library for embedded/real-time systems](https://github.com/atomicobject/heatshrink) に [test_heatshrink_dynamic_theft.c](https://github.com/atomicobject/heatshrink/blob/master/test_heatshrink_dynamic_theft.c) というテストがあったのですが、 `rbuf_alloc_cb` 関数のシグネチャーが [doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md) の [alloc - allocate an instance from a random bit stream](https://github.com/silentbicycle/theft/blob/master/doc/usage.md#alloc---allocate-an-instance-from-a-random-bit-stream) とは違いました。たぶん使っている theft のバージョンが違うのでしょう。

ということで theft のソースをちら見しつつ自分で例を書いてみましたのでメモです。

書いてみた例は
[hnakamur/c-property-based-testing-example: An example of property based testing in C programming language using theft](https://github.com/hnakamur/c-property-based-testing-example) に置きました。

使い方自体は [doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md) を読む前提でこの記事ではそれ以外の点についてメモしておきます。

## ランダムな入力パラメータを複数使う方法

[doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md)
の先頭にプロパティーの関数定義の例が載っていて引数が `struct theft *t, void *arg1` となっていますが、 `void *arg2` を追加すればランダムな入力パラメータを2つに出来ます。

[inc/theft_types.h#L61-L76](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft_types.h#L61-L76) で分かりますが、ランダムな入力パラメータは最大7個です。

[doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md) の `theft_run` を呼ぶところで `theft_run_config` 構造体の `prop1` というメンバーにプロパティーの関数を設定していますが、ランダムな入力パラメータが 2 つの場合は `prop2` メンバーに設定します。

[inc/theft_types.h#L481-L493](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft_types.h#L481-L493) の通り `prop1` ～ `prop7` まで用意されています。

また [theft/theft_types.h at master · silentbicycle/theft](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft_types.h#L495-L497) と [inc/theft_types.h#L472-L473](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft_types.h#L472-L473) で分かるように `type_info` も要素数が 7 の配列となっています。

[doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md)
の例では `type_info` は要素は 1 つですが、ランダムな入力パラメータが 2 つの場合は `type_info` の配列要素も 2 つ指定する必要があります。

## theft にビルトインのランダムな入力値生成

[doc/usage.md](https://github.com/silentbicycle/theft/blob/master/doc/usage.md)
では `theft_type_info` 構造体の `alloc`, `free`, `print` メンバーにそれぞれコールバック関数を設定してカスタムなランダム値生成を行うように説明されていますが、 [inc/theft.h#L174-L235](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft.h#L174-L235) を見ると Built-in generators  というのが用意されています。

例えば `THEFT_BUILTIN_uint64_t` の `alloc` コールバックは
[src/theft_aux_builtin.c#L126-L129](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/src/theft_aux_builtin.c#L126-L129)
と [ALLOC_USCALAR](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/src/theft_aux_builtin.c#L25-L46) マクロを使って定義されています。
unsigned な整数型は `ALLOC_USCALAR` で signed な整数型は `ALLOC_SSCALAR`、浮動小数点数の型は `ALLOC_FSCALAR` を使っています。

Built-in generators のコメントの
[inc/theft.h#L189-L194](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft.h#L189-L194) に値の範囲を限定するサンプルコードが書かれていますが、マクロの実装を見ると
[src/theft_aux_builtin.c#L39-L43](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/src/theft_aux_builtin.c#L39-L43) のように `limit` で割った剰余を使っています。
一様な乱数を生成したいときにはこの手法だと偏りが出るのでまずいですが、 property based testing の入力値として使う分には完全に一様である必要もないので問題ないという判断なのかなと思いました。

また [src/theft_aux_builtin.c#L30-L36](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/src/theft_aux_builtin.c#L30-L36) の箇所を見ると一定の確率で [src/theft_aux_builtin.c#L127-L129](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/src/theft_aux_builtin.c#L127-L129) に指定した値を生成するようになっていることが分かります。

それ以外のケースでは `theft_random_bits` 関数を呼んでランダムなビット列を生成しています。

## カスタムなランダム値生成の際に使える関数群

`theft.h` の Getting random bits
[inc/theft.h#L31-L63](https://github.com/silentbicycle/theft/blob/62e093d9e33bb4218736dce2535eedda2904b8ba/inc/theft.h#L31-L63)
にカスタムなランダム値生成の際に使える関数群が提供されています。

上記の `theft_random_bits` 以外に 3 つの関数がありますが、かなり基本的なものになっています。

脱線ですが property based testing ではなく fuzzing ですが
[dvyukov/go-fuzz: Randomized testing for Go](https://github.com/dvyukov/go-fuzz)
には
[dvyukov/go-fuzz-corpus: Corpus for github.com/dvyukov/go-fuzz examples](https://github.com/dvyukov/go-fuzz-corpus)
というのがあって、画像や HTTP リクエストなどさまざまな形式のランダムな入力を正しい例を元に生成する仕組みが用意されています。
また [Usage](https://github.com/dvyukov/go-fuzz#usage) にあるように生成された値に対して、 1, 0, -1 のどれかをフィードバックすることで、その後のランダム値生成でより効果的な値の列を得られるようになっています。

この部分だけ切り出して汎用化できれば、 fuzzing でも property based testing でも使えて便利そうな気がします。

## 今回試した簡単な例について

[Step by Step Toward Property Based Testing | LeadingAgile](https://www.leadingagile.com/2018/04/step-by-step-toward-property-based-testing/) では自明すぎる例だと property based testing をわざわざ使う価値が無い、逆に複雑すぎる例だと property based testing を既に知っている人でないとついていけないという話が書かれていました。

確かにと思いつつ、今回はとても簡単なマクロ
[source/round.h#L4](https://github.com/hnakamur/c-property-based-testing-example/blob/1abd77cd62721147d62acd503b6742bd30b655ea/source/round.h#L4)
を対象にしました（引数の名前 d と a は [nginx/ngx_config.h at release-1.19.6 · nginx/nginx](https://github.com/nginx/nginx/blob/release-1.19.6/src/core/ngx_config.h#L100) に合わせました。ちなみにこちらは 2 のべき乗に切り上げるマクロです）。

これを効率は少し悪いけどより愚直に実装したインライン関数
[test/round_up_prop_test.c#L7-L10](https://github.com/hnakamur/c-property-based-testing-example/blob/1abd77cd62721147d62acd503b6742bd30b655ea/test/round_up_prop_test.c#L7-L10)
と突き合せて同じ結果になることを確認しました。

property based testing の前に theft と同じ作者の方のユニットテストライブラリー [silentbicycle/greatest: A C testing library in 1 file. No dependencies, no dynamic allocation. ISC licensed.](https://github.com/silentbicycle/greatest) を使って [test/round_up_test.c](https://github.com/hnakamur/c-property-based-testing-example/blob/1abd77cd62721147d62acd503b6742bd30b655ea/test/round_up_test.c) でテストしてから property based testing に進みました。

0 で割って異常終了になるケースと掛け算で uint64 の範囲を超えてオーバーフローしてエラーになるケースに気づかされました。と書きましたが、
[c++ - How do I detect unsigned integer multiply overflow? - Stack Overflow](https://stackoverflow.com/questions/199333/how-do-i-detect-unsigned-integer-multiply-overflow) の [回答](https://stackoverflow.com/questions/199333/how-do-i-detect-unsigned-integer-multiply-overflow/1514309#1514309) と [コメント](https://stackoverflow.com/questions/199333/how-do-i-detect-unsigned-integer-multiply-overflow/1514309#comment1368689_1514309) によると C/C++ では unsigned な整数にはオーバーフローという概念はなく signed な整数はオーバーフローは未定義動作 (Undefined Behavior、よく UB と略される) らしいです（私は一次情報未確認）。

とりあえず今回は
[test/round_up_prop_test.c#L17](https://github.com/hnakamur/c-property-based-testing-example/blob/1abd77cd62721147d62acd503b6742bd30b655ea/test/round_up_prop_test.c#L17)
のようにして分母 (d) が 0 な場合と (分母 * 分子) = (d * a) がオーバーフローする場合は `THEFT_TRIAL_SKIP` を返してスキップするようにしました。

オーバーフローのほうは正確には `((d / a) + 1) * a` が uint64 に収まる必要があるので `d > UINT64_MAX / a` ではだめなんじゃないかと思いつつ、とりあえず書いて何回かテスト実行してみたらエラーが起きなかったのでそのままにしています。

任意の入力値を受け付ける場合は正確な条件でガードすべきところですが、今回試したマクロを実際に使う際は分母は固定で分子も管理者が設定ファイルで指定する想定なのでオーバーフローは起きないということでガード無しで良いかなと思います。

ただ、 property based testing をすることで入力値によってはオーバーフローが起きることを思い出させてくれたというのは良かったです。暗黙の前提で忘れがちなので。

## 関連記事と動画のメモ

今回試すにあたっていろいろ読んだり見たりした記事と動画のメモです。

* [Choosing properties for property-based testing | F# for fun and profit](https://fsharpforfunandprofit.com/posts/property-based-testing-2/) と [Intro to Property-Based Testing - DEV Community 👩‍💻👨‍💻](https://dev.to/jdsteinhauser/intro-to-property-based-testing-2cj8) にプロパティーの選び方のガイドが分かりやすくまとまっていて良かったです。
* [QuickCheck Advice. hints and tips for the interested who… | by Jesper L. Andersen | Medium](https://medium.com/@jlouis666/quickcheck-advice-c357efb4e7e6) property based testing をする際に様々な観点からのアドバイスが書かれています。
* リンク元を紛失してしまったのですが [John Hughes - Testing the Hard Stuff and Staying Sane - YouTube](https://www.youtube.com/watch?v=zi0rHwfiX1Q) の [28:59](https://www.youtube.com/watch?v=zi0rHwfiX1Q&feature=youtu.be&t=1739) から QuviQ 社の QuickCheck で Erlang のプログラムの race condition を検知する例を紹介されていました。 [QuickCheck in Every Language - Hypothesis](https://hypothesis.works/articles/quickcheck-in-every-language/) の Special case: Erlang を見ると QuviQ 社の QuickCheck は有償製品で結構高価らしいですが race condition を検知できるのはすごいなと思いました。
    * property based testing ではないですが Rust + Tokio には [tokio-rs/loom: Concurrency permutation testing tool for Rust.](https://github.com/tokio-rs/loom) というのがあってこれも便利そうです。
* Shrinking について、いつか必要になったら [Introducing theft Property-Based Testing for C](https://spin.atomicobject.com/2014/09/17/property-based-testing-c/) や [Shrinking](https://propertesting.com/book_shrinking.html) が参考になりそうなのでじっくり読もうと思います。
* 各種言語用のライブラリーについては [QuickCheck in Every Language - Hypothesis](https://hypothesis.works/articles/quickcheck-in-every-language/) の他に [QuickCheck - Wikipedia](https://en.wikipedia.org/wiki/QuickCheck) も充実していました。
