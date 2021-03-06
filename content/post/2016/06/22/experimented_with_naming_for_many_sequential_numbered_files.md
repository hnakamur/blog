+++
Categories = []
Description = ""
Tags = ["filesystem","golang"]
date = "2016-06-22T23:40:27+09:00"
title = "連番ファイル名の命名規則について実験してみた"

+++
## はじめに
0〜1,000,000といった連番のファイルを作るときに、1つのディレクトリに全てのファイルを入れると、遅くなるとか取り扱いが面倒になるという懸念があります。

そこで、ディレクトリを切って分割するのですが、数が少ない場合でも多い場合でも良さそうな方法を思いついたのでメモです。

## 素朴な案
最初に思いついたのは以下のような命名規則です。

```
0/000/000
0/000/001
...
0/000/999
0/001/000
0/001/001
...
0/001/999
0/002/000
...
0/999/999
1/000/000
```

この方式には2つの欠点があります。

* ファイルを1つしか作らない場合でも、ディレクトリが必要になる。
* ゼロパディングする際にファイルの最大数を考えて桁数を決めておく必要がある。

## 改善案

上記の2つの欠点を解消する案を思いつきました。

```
0.b
1.b
...
999.b
1/000.b
1/001.b
...
1/999.b
2/000.b
...
999/999.b
1/000/000.b
```

ファイル名とディレクトリ名が衝突しないようにするため、ファイル名に拡張子を付ける必要があります。

この方式には以下の利点があります。

* ファイル数が1000個以下ならディレクトリを作る必要が無い
* 1つのディレクトリ直下にはファイルが最大1000、ディレクトリが最大1000で最大でも合計2000エントリで済む
* ファイルの最大数を事前に決めなくても、パスの長さ制限の範囲内であればこの命名規則でどんどん深いディレクトリを作ってファイルを格納できる。

## サンプルコード
[hnakamur/many_files_experiment](https://github.com/hnakamur/many_files_experiment) におきました。
