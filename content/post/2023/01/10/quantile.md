---
title: "Quantileについて調査してみた(途中)"
date: 2023-01-10T21:39:28+09:00
---
## はじめに

[uint64で高速にLog2を計算する方法を知った · hnakamur's blog](/blog/2023/01/03/fast-log2-for-uint64/)のあと、本題のQuantileについて調査したのでメモです。実はまだ途中なのですが、この後一旦他のことをするので現状をメモしておくということで。

試したレポジトリは
https://github.com/hnakamur/quantile_experiment
です。

## Quantileを推測するアルゴリズムはいろいろある

まず推測する方式の前に、愚直に算出する方式を考えると、全ての入力値を取っておいてランクに対応する値を調べるということになります。ただ、それだと入力値が多くなってくると保管する領域も多くなってしまいます。

そこで入力値を適宜間引きながら、なるべく高精度で近似値を出すようなアルゴリズムがいろいろ考案されているというわけです。

## Greenwald-Khanna方式のコードをGoに移植して試してみた

[kazuhoさんのツイート](https://twitter.com/kazuho/status/1610109662346752002)で紹介されているコードは[Space-Efficient Online Computation of Quantile Summaries](https://www.cis.upenn.edu/~sanjeev/papers/sigmod01_quantiles.pdf)という論文のアルゴリズムを実装しているとのことでした。

検索して[Greenwald-Khanna quantile estimator | Andrey Akinshin](https://aakinshin.net/posts/greenwald-khanna-quantile-estimator/)という解説記事とC#実装を見つけました(記事からリンクされている[レポジトリ内](https://github.com/AndreyAkinshin/perfolizer/tree/master/src/Perfolizer/Perfolizer/Mathematics/QuantileEstimators)には他にもたくさんのアルゴリズムの実装がありました)。

これをGoに移植して、愚直に算出する方式を比較するようなproperty-based [テスト](https://github.com/hnakamur/quantile_experiment/blob/65a27e9aff5f802b02f8ba9eaf0665b5c0a9bfe4/summary_test.go#L138-L175)を[flyingmutant/rapid](https://github.com/flyingmutant/rapid)で書いてみました。指定したパーセントに対する値をestimatorで算出して、その値のランクを愚直方式で算出して、ランクのずれが指定の範囲内に収まっているかという確認の仕方をしています。この確認方法で良いのか、指定の範囲の計算方法がこれで正しいのかは私はまだよくわかっていません。

仮にこのテストが正しいとして、何回か失敗するケースがありました。[この変更](https://github.com/hnakamur/quantile_experiment/commit/e938ec567f47df59142d317120b0cb73aad486b0)を入れると失敗しなくなったのですが、これが正しいかも不明です。

## KLLというアルゴリズムを知った

[Quantile - Wikipedia](https://en.wikipedia.org/wiki/Quantile)で以下の文で他のアルゴリズムを知りました。

> The most popular methods are t-digest[16] and KLL.[17]

16は[\[1902.04023\] Computing Extremely Accurate Quantiles Using t-Digests](https://arxiv.org/abs/1902.04023)、17は[\[1603.05346\] Optimal Quantile Approximation in Streams](https://arxiv.org/abs/1603.05346)という論文にリンクされていました。KLLは17の論文の3名の著者の頭文字になっています。

> The KLL algorithm uses a more sophisticated

とあるのでt-digestよりはKLLのほうが良さそうな雰囲気です。

## Apache Dataskethes というライブラリとREQというアリゴリズムを知った

さらに検索して[Sketching Quantiles and Ranks Tutorial](https://datasketches.apache.org/docs/Quantiles/SketchingQuantilesAndRanksTutorial.html)というページを見つけました。natural rankとnormalized rankという概念や、サーチの際に境界を含める(inclusive)か含めない(exclusive)という選択があることなどを知れて良かったです。

[Introduction to the 3 Quantiles Sketches](https://datasketches.apache.org/docs/Quantiles/QuantilesOverview.html)を見ると2018年3月にKLLの実装がリリースされていますが、その後2021年2月にREQという別の実装がリリースされています。

ということはREQのほうが良いのかなと思って、Javaの実装をGoに移植してみました。値の追加とパーセンタイルを求める部分がとりあえず動いたっぽいという段階で、こちらも愚直方式の結果と付き合わせるテストを書いています。

本当にこれで合ってるかとか性能評価とかはこれからしたいなというところですが、冒頭に書いたように別のことを先にやりたいので一旦ペンディングします。
