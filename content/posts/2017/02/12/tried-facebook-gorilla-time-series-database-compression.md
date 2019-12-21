+++
Tags = ["time-series-database","go"]
Description = ""
date = "2017-02-12T23:00:03+09:00"
title = "Facebookの時系列データベースGorillaのデータ圧縮方式を試してみた"
Categories = []

+++
## はじめに
[Beringei: A high-performance time series storage engine | Engineering Blog | Facebook Code](https://code.facebook.com/posts/952820474848503/beringei-a-high-performance-time-series-storage-engine/) という記事を読んで、Facebookが2015年に ["Gorilla: A Fast, Scalable, In-Memory Time Series Database"](http://www.vldb.org/pvldb/vol8/p1816-teller.pdf) という論文でGorillaという時系列データベースについて発表したものを[Beringei](https://github.com/facebookincubator/beringei)としてオープンソースで公開したのを知りました。

この論文は読んだことがなかったので読んでみたのですが、時系列データベースのデータの特徴をうまく活かした独自の圧縮方法が興味深かったので、自分でも試してみたのでメモです。

Gorillaでは高い圧縮率によってデータをオンメモリで扱うことができるようになり、書き込みと問い合わせの速度がそれまで使っていたディスクベースの時系列と比べて飛躍的に改善したそうです。

Gorillaもディスクに書き出して永続化は行うのですが、RDBのようなACIDのトランザクションは持たず障害発生時には数秒程度のデータは消失するおそれがあるという割り切った設計にしているそうです。その代わり書き込みが高速に行えるというのが利点です。

## サードパーティの実装
[Beringei](https://github.com/facebookincubator/beringei)は C++ で書かれていて、ライセンスは3項BSDですが、最近のFacebookのOSSでは定番の[PATENTS](https://github.com/facebookincubator/beringei/blob/master/PATENTS)ファイルがあります。

Goの実装はないかと調べてみると、[dgryski/go-tsz: Time series compression algorithm from Facebook's Gorilla paper](https://github.com/dgryski/go-tsz) というサードパーティの実装がありました。が、ライセンスが明記されていないので、私のポリシーとしてはソースコードを参照するわけにはいきません。 [Add a license · Issue #18 · dgryski/go-tsz](https://github.com/dgryski/go-tsz/issues/18) というイシューはあるのですが昨年9月から放置状態になっています。私もコメントしてみたのですがまだ反応はないです。また、 [dgryski/go-tszのGoDoc](https://godoc.org/github.com/dgryski/go-tsz)は見てみたのですが、私が期待するAPIとはちょっと違う感じでした。

`[]byte` とデータを相互変換するMarshal, Unmarshalとか、ストリームと相互変換するEncoder, Decoderが欲しいところです。

さらに調べてみると [burmanm/gorilla-tsc: Implementation of time series compression method from the Facebook's Gorilla paper](https://github.com/burmanm/gorilla-tsc/) というJavaのサードパーティの実装がありました。こちらはありがたいことにApache 2ライセンスです。ということで、このコードを参考にして、自分で実装してみました。

[hnakamur/timeseries: a Go package for encoding and decoding time-series data point in similar way to Facebook Gorilla time-series database](https://github.com/hnakamur/timeseries)

例によって雰囲気で実装しているので、uint32とuint64などに入れたビット列をとint64などに相互変換しているあたりなどは特にバグがある可能性があります。むやみに信用せず疑いの目で見てください。

ビットストリームは、[dgryski/go-tsz](https://github.com/dgryski/go-tsz)と同じ作者の方の [dgryski/go-bitstream: go-bitstream: read and write bits from io.Reader and io.Writer](https://github.com/dgryski/go-bitstream) を使わせていただいています。こちらはMITライセンスです。

## 試してみて気づいたこと

### 高い圧縮率を保つためには時刻の精度はミリ秒ではなく秒が良い

["Gorilla: A Fast, Scalable, In-Memory Time Series Database"](http://www.vldb.org/pvldb/vol8/p1816-teller.pdf) の "4.1.1 Compressing time stamps" でデータポイントの時刻の圧縮について説明されています。

時刻の差分の差分 (delta of delta) をなるべくビット数が少なくなるような独自の方式でエンコードするようになっています。

モニタリングは60秒毎のように一定の間隔で行うことが多いので、差分の差分であれば、ほぼ常に0になります。Gorillaのエンコード方式では0は1ビットの0で表すので、0が多いとデータサイズが小さくて済みます。

多少ずれて間隔が 59秒, 61秒のようになったとしても、差分の差分は-1, 1と絶対値が小さい数値になり、0のように1ビットとは行きませんが、絶対値が大きい数値よりは少ないビット数で済みます。

一方 https://github.com/burmanm/gorilla-tsc/blob/fb984aefffb63c7b4d48c526f69db53813df2f28/src/main/java/fi/iki/yak/ts/compression/gorilla/Compressor.java#L90 のコメントにあるように時刻をミリ秒の精度にすると圧縮には良くないです。ミリ秒にすると各データ点の時刻のミリ秒部分はばらつきがあり等間隔にならないので、差分の差分の数値の桁数が増え、エンコードしてもビット数が多くなってしまうからです。

### 小数の値が増えると圧縮率は下がる

["Gorilla: A Fast, Scalable, In-Memory Time Series Database"](http://www.vldb.org/pvldb/vol8/p1816-teller.pdf) の "4.1.2 Compressing values" でデータポイントの値の圧縮について説明されています。

各値を浮動小数点数の64ビット列に変換して1つ前のデータ点とのXORをとるようにしています。全く同じ値の場合は0になるので、エンコードすると1ビットの0で済みます。

またXORの結果を毎回64ビットで記録するのではなく、先頭からのビットで0が続く部分 (LeadingZeros) と終端からのビットで0が続く部分 (TrailingZeros) は、それらのビット数をエンコードし、残りのビット列を記録するようにしています。

さらに、1つ前の値の LeadingZeros と TrailingZeros の桁数よりも多い場合は、そのままにして残りのビット列のみ記録するようになっています。

そうでない場合は新しい LeadingZeros と TrailingZeros の値と残りのビット列を記録します。

このエンコーディング方式は、値が12.0や12.5など浮動小数点数の仮数部の途中から最後まで0のビットが多く続く場合は、少ないビット数で済みます。が、0.1 のような数だと仮数部の多くのビットが0でないため、LeadingZerosとTrailingZerosの値が小さくなり、残りのビット列を記録するのに、多くのビット数を消費してしまいます。

### 時刻が等間隔で、同じ値が続く場合は高圧縮率になる

上に書いたように、圧縮率が悪くなるケースもあります。ですが、時刻が等間隔で、同じ値が続く場合は1つのデータポイントで時刻で1ビット、値で1ビットの2ビットで済むというのは凄いと思いました。

## おわりに
時系列データベースの特性を考慮して、典型的なデータで高圧縮率を実現していることがわかりました。一方で、圧縮率が悪くなるケースについても理解できました。

また、エンコード方式以外にも["Gorilla: A Fast, Scalable, In-Memory Time Series Database"](http://www.vldb.org/pvldb/vol8/p1816-teller.pdf) の "4.3 On disk structures" にはディスク上のレイアウトについて、 "4.4 Handling failures" には障害発生時に対応についてそれぞれ書かれていて、こちらも興味深いです。時系列データベースに興味のある方は、一読をお勧めします。
