+++
title="goで書いたコードがヒープ割り当てになるかを確認する方法"
date = "2018-01-30T06:10:00+09:00"
tags = ["go"]
categories = ["blog"]
+++


## はじめに

[Allocation Efficiency in High-Performance Go Services · Segment Blog](https://segment.com/blog/allocation-efficiency-in-high-performance-go-services/) という記事を読みました。素晴らしいのでぜひ一読をお勧めします。

この記事は自分の理解と実際に試してみた結果のメモです。

一番のポイントは `go build -gcflags '-m'` のようにオプションを指定してビルドすればコードのどの箇所でヒープ割り当てが発生したかを確認できるということです。

`pprof` や `go test -benchmem` でもヒープ割り当ての発生回数は確認できますが、上の方法ではコードのどこ(何行目の何カラム目)でヒープ割り当てが発生したかとなぜ発生したかの理由を確認できます。

## 元記事の内容メモ

冒頭にあげた記事を読んで私が理解した内容のメモです。
元記事の全ての内容を書いているわけでないので、元記事もぜひご覧ください。

一方、元記事にないけど読んで私が思った内容も追記していて、間違ったことを書いている可能性もあります。その場合はtwitterなどでご指摘いただけるとありがたいです。

* 大前提
    * 時期尚早な最適化は避ける。
    * 最適化の際はツールで計測してボトルネックを見つける。
      Go公式ブログの [Profiling Go Programs - The Go Blog](https://blog.golang.org/profiling-go-programs) の記事が素晴らしいのでそちらを参照。
* Goのメモリ割り当て
    * スタックへの割り当てとヒープへの割り当ての2種類。
    * スタック割り当ては安い(軽い処理)がヒープへの割り当ては高くつく(重い処理)。
    * スタックの割り当てと解放にはCPUの命令が2つで済む(割り当てと解放で1つずつ)ので軽い。
    * Goコンパイラはコードを分析して可能ならスタック割り当てにするが、
      それ以外はヒープ割り当てになる。
    * スタック割り当てが可能なのは変数の寿命とメモリ使用量がコンパイル時に
      確定できる場合のみ。
    * ヒープの割り当ては実行時に `malloc` を呼び出してヒープに動的に割り当てる
      必要があるのと、割り当て後にガベージコレクタが割り当てたオブジェクトが
      もう参照されなくなったかを定期的にスキャンする必要がある。
      そのためヒープ割り当てはスタック割り当てに比べると相当重い処理になる。
* エスケープ分析 (escape analysis)
    * Goコンパイラはエスケープ分析と呼ばれる手法を使って、スタック割り当てとヒープ割り当てのどちらを使うかを選択する。
    * 基本的な考え方はガベージコレクション作業をコンパイル時に行える部分は行うということ。
    * コンパイラがコードの領域にわたって変数のスコープを追跡し、寿命が特定のスコープに限定でき且つメモリサイズがコンパイル時に確定できる場合はスタック割り当てになる。
    * 確定できない場合はエスケープしたと呼ばれ (上記の追跡から逃れたというイメージか)、ヒープ割り当てを行う必要がある。
    * エスケープ分析のルールはGoの言語仕様では規定されていない (Goのバージョンが上がってコンパイラが進化するとスタック割り当てできるケースが増えるためだと思われる)。
    * `go build -gcflags '-m'` のようにオプションを指定してビルドすればエスケープ分析の結果が出力される。
    * `go build -gcflags '-m -m'` のように `-gcflags` の `-m` オプションを複数回指定してビルドすればさらに詳細な結果が出力される。
* ポインタはスタック割り当ての阻害要因なので可能なら避ける。
    * ポインタを使うとほとんどの場合ヒープ割り当てになってしまう。
* ポインタを避けたほうが良い理由。
    * 関数の引数やメソッドのレシーバもポインタにせず値をコピーするほうが多くの場合は軽い処理になる。
    * ポインタのデレファレンスする際は実行時に `nil` チェックが行われる分処理が増える。
    * ポインタを使わず値をコピーするほうがメモリ上で局所化してCPUのキャッシュヒット率も上がる。
    * キャッシュラインに含まれるオブジェクトのコピーは単一のポインタのコピーとほぼ同等の軽さ。 
        * x86だと64バイト以下のオブジェクトであればこれが言える。
        * Goは [Duff’s devices](https://luciotato.svbtle.com/golangs-duffs-devices) という手法を用いてメモリコピーなどのよくある処理について非常に効率的なアセンブラコードを生成する。
    * ポインタの使いどころは所有権を表す場合とミュータブル(値を変更可能にする)場合。
    * 基本は値渡しにして必要な時だけポインタ渡しにするのがお勧め。
    * 値渡しなら `nil` チェックが不要という利点もある。
    * ポインタを含まないメモリ領域はガベージコレクタがスキャンをスキップできる(例: `[]byte` のバックストアのメモリ領域はスキャン不要)。
    * 逆に言うと、ポインタがあるとガベージコレクタはポインタの参照先をスキャンする必要がある。参照先がポインタを含む構造体などだとさらにそのポインタの参照先もスキャンが必要になる。するとメモリ上に点在した領域を次々読み込むことになるので処理としても重いし、読み込むことでCPUキャッシュから他のデータを追い出してCPUキャッシュヒット率も悪くなる。
* スライスと文字列にも注意
    * スライスはサイズが動的でコンパイル時には未決定なのでバックストア(スライス内のポインタが参照する先)の配列がヒープ割り当てになる。
    * 文字列もバイトのスライスなので同様。
    * スライスではなく配列が使えるなら、配列はサイズ固定なのでスタック割り当てできる可能性が出てくる。必要なサイズの最大値が事前に分かってスタックにおいても問題ないくらいのサイズのときはバックストアの配列をローカル変数として宣言して利用すればよい。
    * `append` を使うことによって元のバックストアのキャパシティでは足りなくなりサイズ拡張する場合、拡張後のバックストアはヒープ割り当てになる。
    * スライスを受け取る関数に配列 `a` を渡すには `a[:]` といった `Slice expressions](https://golang.org/ref/spec#Slice_expressions) を使えばよい。
* time.Time に注意
    * タイムゾーン情報をポインタで持っている。
    * ヒープに保持するときは time.Time で保持するよりUnix timeの整数で持つほうがガベージコレクタには優しい。
    * 元記事ではUnix timeの秒数を `int64` とナノ秒部分を `uint32` で持っていましたが、1678年から2262年までの日付を扱うのであればUnix timeをナノ秒で `int64` で持つという手もあります。
        * [time.UnixNano()](https://golang.org/pkg/time/#Time.UnixNano)
        * [Go言語のos.Chtimesで設定可能な最大日時は 2262-04-11 23:47:16.854775807 +0000 UTC](/blog/2016/10/22/max-time-for-golang-os-chtimes/)
* 戻り値で文字列やスライスを返す関数には注意。
    * 例えば [func (t Time) Format(layout string) string](https://golang.org/pkg/time/#Time.Format) の戻り値のstringの値(正確にはバックストアの配列)はヒープ割り当てになる。
    * もし戻り値の文字列の使い道が別のバイトスライスに追加したいのであれば [func (t Time) AppendFormat(b []byte, layout string) []byte](https://golang.org/pkg/time/#Time.AppendFormat) を使うのが良い。引数 `b` のバックストアの配列のキャパシティが十分大きければそこに直接書き込めばよいので余分なヒープ割り当てが発生しない。キャパシティ不足の場合は拡張したバックストアがヒープ割り当てにはなる。が、戻り値で返してから追記だと2回のヒープ割り当てになるので、1回で済む分こちらのほうが良い。
    * 同様に `strconv` の `Itoa` や `FormatFloat` などは、用途として可能なら `AppendInt` や `AppendFloat` を使うのが良い。
* インターフェースのメソッド呼び出しは構造体のそれより重い処理
    * インターフェースのメソッド呼び出しはダイナミックディスパッチで実行される。
    * 元記事には書いてないですが、インターフェースを保持する変数に保持される値は実装の構造体へのポインタになるので、上のポインタの話にも通じることになります。
    * 繰り返し実行されボトルネックになる処理であれば、インタフェースを使わないコードに書き換えてヒープ割り当てが発生しないようにするというのも一つの手。ただしインターフェースによる拡張性は失われるのでトレードオフではある。
 

## 動作確認した環境

動作確認した環境はUbuntu16.04でgoのバージョンは以下の通りです。

```console
$ go version
go version go1.10rc1 linux/amd64
```

## 実際に試してみた

#### 例1

```go {linenos=table}
package main

import "fmt"

func main() {
        x := 42
        fmt.Println(x)
}
```

`-gcflags '-m'` つきでビルドしてみた例。
7行目の `x` はスタック割り当てかと思いきやヒープ割り当てになります。

```console
$ go build -gcflags '-m' main.go
# command-line-arguments
./main.go:7:13: x escapes to heap
./main.go:7:13: main ... argument does not escape
```

`-gcflags '-m -m'` つきでビルドするとより詳細な出力が出ます。

```console
$ go build -gcflags '-m -m' main.go
# command-line-arguments
./main.go:5:6: cannot inline main: non-leaf function
./main.go:7:13: x escapes to heap
./main.go:7:13:         from ... argument (arg to ...) at ./main.go:7:13
./main.go:7:13:         from *(... argument) (indirection) at ./main.go:7:13
./main.go:7:13:         from ... argument (passed to call[argument content escapes]) at ./main.go:7:13
./main.go:7:13: main ... argument does not escape
```

`x` は `fmt.Println` という関数の引数に渡されて、その引数がエスケープするので、 `x` もエスケープするということがわかります。

他の例も試しましたが、この記事では省略します。気になる方は元記事をご覧ください。

ちょっと注意
^^^^^^^^^^^^

ちなみに `-gcflags` の指定を変えずに2回実行すると何も出力されませんでした。
コンパイルされたバイナリファイル (この場合は `./main`) を消してから再度実行すれば出力されました。
ファイルを消さずに `touch main.go` してビルドしても出力されませんでした。

ファイルを消さずに `go build` の `-a` オプションを指定するという手でも出来ましたが、コンパイル時間が長かったのでファイルを消すほうが良さそうです。

なお、 `main.go` を書き換えてから再度ビルドしたときはエスケープ分析の結果が出力されました。
普通はコード変更せずに2度ビルドしたりはせず、変更してからビルドするでしょうから、普段は意識する必要はなさそうです。

## おわりに

元記事の最後にあったまとめを訳しておきます。

1. 時期尚早な最適化はしないこと! 最適化するときは計測したデータに基づいて行うこと。
2. スタック割り当ては安い(軽い処理)がヒープへの割り当ては高くつく(重い処理)。
3. エスケープ分析のルールを理解することでより効率的なコードを書くことができる。
4. ポインターがあるとほとんどの場合はスタック割り当てにできずヒープ割り当てになる。
5. パフォーマンスクリティカルなコードのセクションではメモリ割り当てを制御できるAPIを提供することを検討する。
6. ホットパス(繰り返し実行される処理)ではインターフェース型の使用は控えめにする(多用しない)。

補足すると 4. は上記の [func (t Time) AppendFormat(b []byte, layout string) []byte](https://golang.org/pkg/time/#Time.AppendFormat) のようにAPIの利用者が予め必要なメモリ割り当てをすることを可能にするようなAPIという意味です。
[func (t Time) Format(layout string) string](https://golang.org/pkg/time/#Time.Format) のほうが手軽に使えますが、戻り値がヒープ割り当てになってしまいます。パフォーマンスが重要な局面では `AppendFormat` のほうが制御する余地があるわけです。

あと元記事では出てませんでしたが、一時的なオブジェクトを繰り返し利用する場合は
[sync.Pool](https://golang.org/pkg/sync/#Pool) もパフォーマンス改善に役立ちます。
顕著な例が [valyala/fasthttp: Fast HTTP package for Go. Tuned for high performance. Zero memory allocations in hot paths. Up to 10x faster than net/http](https://github.com/valyala/fasthttp) でHTTPリクエストやレスポンスなどのオブジェクトを `sync.Pool` で管理し、リクエスト処理が終わったら回収して次のリクエスト処理で再利用することで高速化を実現しています。

ただ、 `sync.Pool` ではオブジェクトを使い終わった時点で
[func (p *Pool) Put(x interface{})](https://golang.org/pkg/sync/#Pool.Put)
を明示的に呼ぶ必要があるのが面倒なところです。使い終わったことを伝えないとプールに回収できないので当然なのですが、メモリ管理をガベージコレクタに任せて気にしなくてよくなるという理想からは遠のくのがちょっと残念です。つまり自動ではなく手動管理なんですよね。
とはいえパフォーマンスクリティカルな箇所では速くなるほうが嬉しいのでトレードオフではあります。

ということで `pprof` や `go test -benchmem` に加えて
`go build -gcflags '-m'` も活用していきたいですね。
