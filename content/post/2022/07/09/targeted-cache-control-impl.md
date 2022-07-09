---
title: "Targeted Cache Control のライブラリをC言語で書いた"
date: 2022-07-09T22:38:40+09:00
---

## はじめに

C11 のような最近(と言っても2022年だと11年前ですが)のC言語の勉強を兼ねて [RFC 8941 - Structured Field Values for HTTP](https://datatracker.ietf.org/doc/rfc8941/) のライブラリを書いてみました。
さらに [RFC 9213 - Targeted HTTP Cache Control](https://datatracker.ietf.org/doc/rfc9213/) のフィールド値をパースする関数も書いてみました。

ビルドツールはこれも勉強を兼ねて CMake を使いました。

得られた知見などをメモしておきます。なお、例によって間違っていたり、もっと良い方法が他にあるかもしれませんが、その場合はやさしくご指摘いただけるとありがたいです。

ライブラリは [hnakamur/http-sfv](https://github.com/hnakamur/http-sfv) で公開しています。
ただ、[RFC 8941 - Structured Field Values for HTTP](https://datatracker.ietf.org/doc/rfc8941/)
のほうは毎回メモリ割り当てする素朴な実装なので実用向きではないです。
[RFC 9213 - Targeted HTTP Cache Control](https://datatracker.ietf.org/doc/rfc9213/) のフィールド値をパースする関数のほうはメモリ割り当て不要で実用でも使えそうかと思ってますが、まだ実際には使ってないです。

## 参考書籍

* [O'Reilly Japan - Cクイックリファレンス 第2版](https://www.oreilly.co.jp/books/9784873117812/)
* [Professional CMake: A Practical Guide - 12th Edition](https://crascit.com/professional-cmake/)

「Cクイックリファレンス」はC99とC11の言語とライブラリについてコンパクトにまとめられていて、C言語は一応知っているけど、C11のような最近の標準を知らない私にはとても良い本でした。

[C11 (C standard revision) - Wikipedia](https://en.wikipedia.org/wiki/C11_%28C_standard_revision%29) からリンクされている C11 の最終ドラフト [N1570 の PDF](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) も少し参照しました。

Professional CMake のほうは 7th Edition は持っていたのですが [Release Notes](https://crascit.com/professional-cmake/release-notes/) を見て 12th Edition まで出ているということで買ってみました。

## 実装メモ

### Zigのスタイルを取り入れ

Zigを勉強したのでそれの影響を受けたスタイルにしてみました。

* エラーコードは `hsfv_err_t` という enum を作って、エラーが起きうる関数は全て戻り値を `hsfv_err_t` にし、それ以外の出力は引数でポインタを渡して値をセットする。
* メモリ割り当て用に `hsfv_allocator_t` というアロケータの型を定義し、メモリ割り当てが必要な関数にはこれを引数で渡す。
* 構造体ごとのメモリ解放などの後処理は `*_deinit` という関数の命名規則にする。

### その他の実装メモ

* データ構造やメモリ割り当ては、とりあえず素朴に単純な構造にし、メモリも逐一割り当てる方式とした。
   * 最初から効率を考えると実装が難しいので、まずは素直に実装してみました。と言いつつ今後最適化をするかは未定です。
* Base64 のエンコード、デコードのコードは nginx から頂きました。

### C99の利点

今回感じた利点は以下のとおりです。

* `//` で始める行コメントが使える。
* `bool` 型が使える
    * C99 で `_Bool` 型が入って `#include <stdbool.h>` すれば `bool` が使える
* `uint64_t` などの正確なビット数の整数型が使える
    * `#include <stdint.h>` で使える
* 配列の特定要素の初期化
    * ほとんどの要素は 0 で一部の要素だけ 0 以外の値を持つような整数の配列を初期化する際に `int a[] = { [5] = 1 };` のような書き方が出来る。
    * キーやトークンなどに使える文字種チェックの表を配列で作るのに便利（以下の例参照）。

[http-sfv/bare_item.c at main · hnakamur/http-sfv](https://github.com/hnakamur/http-sfv/blob/9496ab08ec045a59a27c88f6b7ff54179d66d07e/lib/bare_item.c#L15-L23)

```c
const char hsfv_key_trailing_char_map[256] = {
    ['*'] = '\1',
    ['-'] = '\1', ['.'] = '\1',
    ['0'] = '\1', '\1', '\1', '\1', '\1', '\1', '\1', '\1', '\1', '\1', // to '9'
// …(略)…
```

ちなみに C89 で書かれている nginx ではこんな技を使っているのを見つけました。

[nginx/ngx_http_parse.c at release-1.23.0 · nginx/nginx](https://github.com/nginx/nginx/blob/release-1.23.0/src/http/ngx_http_parse.c#L835-L845)

```c
    /* the last '\0' is not needed because string is zero terminated */

    static u_char  lowcase[] =
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0-\0\0" "0123456789\0\0\0\0\0\0"
        "\0abcdefghijklmnopqrstuvwxyz\0\0\0\0\0"
        "\0abcdefghijklmnopqrstuvwxyz\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0";
```

最後の行だけ1文字わざと短くしていて文字列の終端の NUL 文字を添字255の要素として使うというものです。この手の表は添え字255の要素の値はたいてい0なので、この技は C89 では便利かもと思いました。

### 最近接偶数への丸め

[RFC 8941 3.3.2. Decimals](https://www.rfc-editor.org/rfc/rfc8941.html#name-decimals) では Decimal は以下の形式と定められています。

```
sf-decimal  = ["-"] 1*12DIGIT "." 1*3DIGIT
```

[IEEE 754 - Wikipedia](https://en.wikipedia.org/wiki/IEEE_754) の [Basic and interchange formats](https://en.wikipedia.org/wiki/IEEE_754#Basic_and_interchange_formats) の binary64 の Decimal digits 列の値は 15.95 とあります。 Decimal は整数部12桁、小数部3桁で合計15桁でこれを考慮しているのだなと思います。

[RFC 8941 4.1.5. Serializing a Decimal](https://www.rfc-editor.org/rfc/rfc8941.html#name-serializing-a-decimal) には Decimal をシリアライズする場合は小数部3桁で最近接偶数へ丸めると書かれています。

最初 `snprintf` で `"%.3f"` という書式で実装してみたら [httpwg/structured-field-tests: Tests for HTTP Structured Field Values](https://github.com/httpwg/structured-field-tests) のテストが通りませんでした。

そこで `fesetround` と `rint` を使って実装するように変更しました。

`fegetround` で現在の丸めモードを取得して最近接偶数への丸め `FE_TONEAREST` でない場合は `fesetround` でモードを切り替えて、 `rint` で丸めます。丸めモードを変更した場合は元に戻します。

[http-sfv/bare_item.c at main · hnakamur/http-sfv](https://github.com/hnakamur/http-sfv/blob/9496ab08ec045a59a27c88f6b7ff54179d66d07e/lib/bare_item.c#L224-L267)

```c
#pragma STDC FENV_ACCESS ON
hsfv_err_t hsfv_serialize_decimal(double decimal, hsfv_allocator_t *allocator, hsfv_buffer_t *dest)
{
    int prev_rounding = fegetround();
    if (prev_rounding != FE_TONEAREST && fesetround(FE_TONEAREST)) {
        return HSFV_ERR_FLOAT_ROUNDING_MODE;
    }

    double rounded = rint(decimal * 1000);

    if (prev_rounding != FE_TONEAREST && fesetround(prev_rounding)) {
        return HSFV_ERR_FLOAT_ROUNDING_MODE;
    }

    char tmp[decimal_tmp_bufsize];
    int n = snprintf(tmp, decimal_tmp_bufsize, "%.3f", rounded / 1000);
// …(略)…
    return HSFV_OK;
}
#pragma STDC FENV_ACCESS OFF
```

## テスト

### テストライブラリは Catch2 の v3.0.1 を使ってみた

[catchorg/Catch2: A modern, C++-native, test framework for unit-tests, TDD and BDD - using C++14, C++17 and later (C++11 support is in v2.x branch, and C++03 on the Catch1.x branch)](https://github.com/catchorg/Catch2)

Catch2 自体は C++ で書かれていますが、私のテストコードは C で書きました。使い方がシンプルで良かったです。

### メモリ割り当て失敗時のテスト

Zig の [lib/std/testing/failing_allocator.zig](https://github.com/ziglang/zig/blob/0.9.1/lib/std/testing/failing_allocator.zig) を参考に指定した回に失敗するようなアロケータ [hsfv_failing_allocator](https://github.com/hnakamur/http-sfv/blob/9496ab08ec045a59a27c88f6b7ff54179d66d07e/lib/allocator.c#L24-L57) を実装してそれを使ってテストしました。

### Address Sanitizer を使ってみた

テストコードでメモリリークや二重解放などがあるとソースコードの行数とともに教えてくれるので便利でした。
Zigの`std.testing.allocator` で出来てて便利と思っていたのですが、Cでも出来たんですね。

### Clangの Source-based Code Coverage を使ってみた

[Source-based Code Coverage](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html)

行より細かいリージョンという単位でカバレッジが見れて便利でした。

### JSONファイルの読み込みには yyjson を使用

mattn さんの [Big Sky :: RapidJSON や simdjson よりも速いC言語から使えるJSONライブラリ「yyjson」](https://mattn.kaoriya.net/software/lang/c/20220320234556.htm) を読みつつ [ibireme/yyjson: The fastest C JSON library](https://github.com/ibireme/yyjson) を使ってみました。使いやすい API で良かったです。
[httpwg/structured-field-tests: Tests for HTTP Structured Field Values](https://github.com/httpwg/structured-field-tests) のテストデータはJSONファイルで提供されているのでそれを読み込む必要があります。

### base32 もサードパーティのライブラリを使用

[httpwg/structured-field-tests: Tests for HTTP Structured Field Values](https://github.com/httpwg/structured-field-tests) のJSONファイル内でbase32が使用されているので [paolostivanin/libbaseencode: Library written in C for encoding and decoding data using base32 or base64 (RFC-4648)](https://github.com/paolostivanin/libbaseencode) を使いました。

## Targeted HTTP Cache Control のフィールド値のパース関数の実装メモ

Structured Field Values for HTTP のパーサとシリアライザがとりあえず動くようになった後、データ構造やメモリ割り当ての効率化をどうしようかなと考えていたときに [RFC 8941 A.1. Why Not JSON?](https://www.rfc-editor.org/rfc/rfc8941.html#name-why-not-json) を見て、JSONのライブラリがどうやってるか見ると参考になるかもと思いました。

で、[yyjson: Data Structures](https://ibireme.github.io/yyjson/doc/doxygen/html/md_doc__data_structure.html) を見るといろいろ工夫されていて勉強になりました。

が、[The simdjson library](https://simdjson.org/) のベンチマークのグラフを見ると、 simdjson のほうが3倍以上速かったので、こちらも見てみました。このベンチマークでは [The Basics: Loading and Parsing JSON Documents](https://github.com/simdjson/simdjson/blob/master/doc/basics.md#the-basics-loading-and-parsing-json-documents) で説明されている `ondemand::parser` というが使われていました。これは JSON 全体を解釈してデータ構造を作るのではなく、利用側のコードで参照する箇所だけ局所的に解釈するようになっています。yyjsonのパースはJSON全体のデータ構造を作るのでこのベンチマークは apple to apple な比較にはなっていないのではという気もしますが、JSONを読み込んで一部のキーだけ参照するという利用ケースを想定するのであれば妥当なのかもしれません。

それはともかく、Targeted HTTP Cache Control のフィールド値のパースのことを考えてみると、これも必要なキー以外は無視することになるので、全体のデータ構造を作る必要はないことに気づきました。

[RFC 9213 2.1. Syntax](https://www.rfc-editor.org/rfc/rfc9213.html#name-syntax) を見ると Target Cached Control のフィールド値は Structured Field Values の Dictionary として解釈するという仕様です。仕様通りパースできない場合はフィールド全体を無視せよとあります。

`max-age` に整数値ではなく少数付きのdecimal値が指定されていた場合もエラーにするという厳格な方針になっています。

昔はネットワークのプロトコルは送信側は仕様に厳格に沿うが受信側は寛容にするというスタイルがあったが、近年ではセキュリティ上問題になるので受信側も厳格にするという流れになっています。[intarchboard/draft-protocol-maintenance: Don't apply the robustness principle, look after your protocol instead](https://github.com/intarchboard/draft-protocol-maintenance)

ということで、以下の方針としました。

* `must-revalidate` などのbooleanもDictionaryのシリアライズではtrueは省略するので、省略しているものだけを受け付ける。
* Dictionaryでは同じキーが重複する場合は値は上書きになるが、上書きされる前の値が不正な場合もエラーとする。
* パラメータは無視するよう書かれているので無視する。
* `max-age` は非負整数だけ許可する。
    * RFC 8941 には整数とdecimalは両対応のパース仕様だけが書かれているが、別途非負整数だけ許可する処理を実装してそれを使う。最大桁数は仕様に従う。
* boolのtrueと非負整数以外は仕様通りパースできるか確認して値は破棄するような関数を実装しました。

Target Cached Control のフィールドが複数ある場合はカンマで連結後パースすることになります。実装上は実際に連結しなくても各フィールドを順にパースすれば同等の処理になります。

この結果、動的メモリ割り当てを全く行わずにパースする実装ができました。

## CMake 関連メモ

### cmake-format

`cmake` の実行時に `cmake-format` で `CMakeLists.txt` をフォーマットするようにしてみました。

### clang-format

`make` の実行時に `clang-format` でソースコードをフォーマットにするようにしてみました。

### Address Sanitizer

上でも書きましたが、テストのコードを `-fsanitize=address` つきでビルドして Address Sanitizer を有効にしました。

### Source-based Code Coverage

上でも書きましたが、テスト実行後にカバレッジを取得するカスタムターゲットを追加し、 `make check` で実行できるようにしました。
