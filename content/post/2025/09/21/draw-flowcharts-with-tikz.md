---
title: "TikZでフローチャートを書く"
date: 2025-09-21T09:26:49+09:00
lastmod: 2025-09-21T21:06:00+09:00
---

## はじめに

[Mermaidでフローチャート](https://mermaid.js.org/syntax/flowchart.html)を書けるのですが、複雑になってくると配置に不満が出ます。

一方、[draw.io Diagrams - Windows に無料でダウンロードしてインストールする | Microsoft Store](https://apps.microsoft.com/detail/9mvvszk43qqw?hl=ja-JP&gl=JP)だと図を書くのに時間がかかります。

[TikZでフローチャートを書く | Molina Tech Hub](https://molina.jp/blog/tikz%E3%81%A7%E3%83%95%E3%83%AD%E3%83%BC%E3%83%81%E3%83%A3%E3%83%BC%E3%83%88%E3%82%92%E6%9B%B8%E3%81%8F/)という素晴らしい記事を見つけたので、試してみました。TikZ初心者の私ですが、とりあえず希望通りの図が書けたということでメモです。

## UbuntuでLuaLaTeXをセットアップ

LaTeXはいろいろ種類があるそうですが、[［改訂第9版］LaTeX美文書作成入門 | Gihyo Digital Publishing … 技術評論社の電子書籍](https://gihyo.jp/dp/ebook/2023/978-4-297-13890-5)を見てLuaLaTeXを使うことにしました。

[Linux/Linux Mint - TeX Wiki](https://texwiki.texjp.org)の[TeX Live/Debian](https://texwiki.texjp.org/?Linux%2FLinux%20Mint#qcd9ce14)の「日本語関連のパッケージのみインストールする場合」の手順でセットアップします。

```
sudo apt install texlive-lang-japanese texlive-latex-extra texlive-luatex
```

{{< details summary="横道: jlreq文書クラスも入ってます" >}}

[日本語 LaTeX の新常識 2021 #LaTeX - Qiita](https://qiita.com/wtsnjp/items/76557b1598445a1fc9da)によると日本語の文書クラスは[abenori/jlreq](https://github.com/abenori/jlreq/search?l=html)を使うと良さそうです。

jlreq文書クラスはtexlive-lang-japaneseパッケージに含まれています。

```
$ dpkg -L texlive-lang-japanese | grep -F jlreq.cls
/usr/share/texlive/texmf-dist/tex/latex/jlreq/jlreq.cls
```
{{< /details >}}

## 描いてみたフローチャート

{{< svg src="RESPONSE-980-CORRELATION.svg" title="図1 flowchart for OWASP CRS RESPONSE-980.CORRELATION.conf" >}}

{{< details summary="ソース：RESPONSE-980-CORRELATION.tex" >}}

```latex
\documentclass[tikz, border=8pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric}
\usetikzlibrary {shapes.misc}
\usetikzlibrary{positioning}
\begin{document}
\begin{tikzpicture}
  \tikzset{Terminal/.style={rounded rectangle, draw, text centered, text width=5cm, minimum height=1.5cm}};
  \tikzset{Process/.style={rectangle, draw, text centered, text width=5cm, minimum height=1.5cm}};
  \tikzset{Decision/.style={diamond, draw, text centered, aspect=6,text width=10cm, minimum height=1.5cm}};
  \node[Terminal] (start) at (0,0){Start};
  \node[Decision, below=1 of start.south](id_980041){REPORTING\_LEVEL == 0};
  \draw[->, thick] (start) -- (id_980041);

  \node[Decision, below=1 of id_980041.south](id_980042){REPORTING\_LEVEL >= 5};
  \draw[->, thick] (id_980041.south) -- (id_980042) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980042.south](id_980043){DETECTION\_ANOMALY\_SCORE == 0};
  \draw[->, thick] (id_980042.south) -- (id_980043) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980043.south](id_980044){BLOCKING\_INBOUND\_ANOMALY\_SCORE >= inbound\_anomaly\_score\_threshold};
  \draw[->, thick] (id_980043.south) -- (id_980044) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980044.south](id_980045){BLOCKING\_OUTBOUND\_ANOMALY\_SCORE >= outbound\_anomaly\_score\_threshold};
  \draw[->, thick] (id_980044.south) -- (id_980045) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980045.south](id_980046){REPORTING\_LEVEL < 2};
  \draw[->, thick] (id_980045.south) -- (id_980046) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980046.south](id_980047){DETECTION\_INBOUND\_ANOMALY\_SCORE >= inbound\_anomaly\_score\_threshold};
  \draw[->, thick] (id_980046.south) -- (id_980047) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980047.south](id_980048){DETECTION\_OUTBOUND\_ANOMALY\_SCORE >= outbound\_anomaly\_score\_threshold};
  \draw[->, thick] (id_980047.south) -- (id_980048) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980048.south](id_980049){REPORTING\_LEVEL < 3};
  \draw[->, thick] (id_980048.south) -- (id_980049) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980049.south](id_980050){BLOCKING\_ANOMALY\_SCORE > 0};
  \draw[->, thick] (id_980049.south) -- (id_980050) node[pos=0, anchor=north west]{No};

  \node[Decision, below=1 of id_980050.south](id_980051){REPORTING\_LEVEL < 4};
  \draw[->, thick] (id_980050.south) -- (id_980051) node[pos=0, anchor=north west]{No};

  \node[Terminal, below=1 of id_980051.south](log_reporting){LOG-REPORTING};
  \draw[->, thick] (id_980051.south) -- (log_reporting) node[pos=0, anchor=north west]{No};
  \draw[->, thick] (id_980042) -- ++(-10,0) node[pos=0, anchor=north east]{Yes} |- (log_reporting.west);
  \draw[-, thick] (id_980044) -- ++(-10,0) node[pos=0, anchor=north east]{Yes};
  \draw[-, thick] (id_980045) -- ++(-10,0) node[pos=0, anchor=north east]{Yes};
  \draw[-, thick] (id_980047) -- ++(-10,0) node[pos=0, anchor=north east]{Yes};
  \draw[-, thick] (id_980048) -- ++(-10,0) node[pos=0, anchor=north east]{Yes};
  \draw[-, thick] (id_980050) -- ++(-10,0) node[pos=0, anchor=north east]{Yes};

  \node[Process, below=1 of log_reporting.south](id_980170){msg: Anomaly Scores};
  \draw[->, thick] (log_reporting) --(id_980170);

  \node[Terminal, below=1 of id_980170.south](end_reporting){END-REPORTING};
  \draw[->, thick] (id_980170) --(end_reporting);
  \draw[->, thick] (id_980041) -- ++(10,0) node[pos=0, anchor=north west]{Yes} |- (end_reporting.east);
  \draw[-, thick] (id_980043) -- ++(10,0) node[pos=0, anchor=north west]{Yes};
  \draw[-, thick] (id_980046) -- ++(10,0) node[pos=0, anchor=north west]{Yes};
  \draw[-, thick] (id_980049) -- ++(10,0) node[pos=0, anchor=north west]{Yes};
  \draw[-, thick] (id_980051) -- ++(10,0) node[pos=0, anchor=north west]{Yes};
\end{tikzpicture}
\end{document}
```
{{< /details >}}


## PDFの生成手順

```
lualatex texファイルのベース名
```

{{< details summary="横道: エラーが起きたときはXで終了" >}}

エラーの場合はエラーメッセージの後に`?`というプロンプトが出ます。
`?` Enterで説明が出ます。`X` Enterで終了です。

出力例：

```
$ lualatex RESPONSE-980-CORRELATION
…（略）…
See the pgf package documentation for explanation.
Type  H <return>  for immediate help.
 ...

l.17   \draw[->, thick] (start) -- (id_980041x)
                                             ;
? H
This error message was generated by an \errmessage
command, so I can't give any explicit help.
Pretend that you're Hercule Poirot: Examine all clues,
and deduce the truth by order and method.
? ?
Type <return> to proceed, S to scroll future error messages,
R to run without stopping, Q to run quietly,
I to insert something, E to edit your file,
1 or ... or 9 to ignore the next 1 to 9 tokens of input,
H for help, X to quit.
? X
 1402 words of node memory still in use:
   22 hlist, 2 vlist, 1 rule, 2 disc, 2 local_par, 4 dir, 25 glue, 4 kern, 2 pe
nalty, 29 glyph, 67 attribute, 50 glue_spec, 67 attribute_list, 3 temp, 2 if_st
ack, 1 write, 38 pdf_literal, 2 pdf_colorstack nodes
   avail lists: 2:9,3:1,4:2,5:12,10:1

warning  (pdf backend): no pages of output.
Transcript written on RESPONSE-980-CORRELATION.log.
```
{{< /details >}}

## PDFからSVGの生成手順

```
pdftocairo -svg pdfファイル名
```
ファイル名の拡張子を.svgにしたファイルが生成されます。

## 「TikZの使い方」(2025-09-21 21:06 追記)

TikZの公式マニュアルは[PGF/TikZ Manual - Complete Online Documentation](https://tikz.dev/)です。
フッターの[Official PDF version](https://pgf-tikz.github.io/pgf/pgfmanual.pdf)でPDFもダウンロードできます。
このPDFは英語で書かれていて1323ページ(2025-09-21時点)と長大です。

[TikZ - TeX Wiki](https://www.amazon.co.jp/TikZ%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9-alg-d/dp/B0D1MJJBVD)からリンクされていた
[TeXについて | 壱大整域](https://alg-d.com/math/tex.html)からダウンロードできる
[TikZの使い方](https://alg-d.com/math/tikz.pdf)というPDFは日本語で書かれていて111ページ(2025-09-21時点)です。

というわけで、まずはこちらをありがたく読むのが良さそうです。

## 余談

### 文書内の図として作るか図単体として作るか

[TikZ - TeX Wiki](https://texwiki.texjp.org/TikZ)の[図画のみの出力](https://texwiki.texjp.org/TikZ#nf2ceec5)では以下のような書き方を紹介していました。

```
\documentclass{jlreq}
\usepackage{tikz}
\pgfrealjobname{RESPONSE-980-CORRELATION}
…（略）…

\begin{document}
\beginpgfgraphicnamed{RESPONSE-980-CORRELATION-fig1}
\begin{tikzpicture}
…（略）…
\end{tikzpicture}
\endpgfgraphicnamed
\end{document}
```

`RESPONSE-980-CORRELATION-fig1`だけコンパイルするには以下のようにします。

```
lualatex --jobname=RESPONSE-980-CORRELATION-fig1 RESPONSE-980-CORRELATION.tex
```

これ自体は期待通り動きました。一方で文書全体でコンパイルすると2ページになり、1ページ目はページ番号のみで、2ページ目はページからはみ出た状態になってしまいました。

そこで、Google Geminiに聞いて、文書クラスを以下のようにして図単体として作っています。

```
\documentclass[tikz, border=8pt]{standalone}
```

### 線を重ねて核と太くなるので重ねない

複数の菱形の判断(Decision)からlog_reportingへの線は当初は以下のように書いていました。
```
  \draw[->, thick] (id_980042)node[below, xshift=-200]{Yes} -- ++(-10,0) |- (log_reporting.west);
  \draw[->, thick] (id_980044)node[below, xshift=-250]{Yes} -- ++(-10,0) |- (log_reporting.west);
```

ですが、重なった箇所が太くなるので、以下のように2つ以降は交わるところまでだけを書くようにしました。

```
  \draw[->, thick] (id_980042)node[below, xshift=-200]{Yes} -- ++(-10,0) |- (log_reporting.west);
  \draw[-, thick] (id_980044)node[below, xshift=-250]{Yes} -- ++(-10,0);
```

### 判断から横に伸びる線は中心から描く

菱形の判断(Decision)は以下のような定義になっています。
```
  \tikzset{Decision/.style={diamond, draw, text centered, aspect=6,text width=10cm, minimum height=1.5cm}};
```

text widthに固定の長さを指定していますが、文字数が増えると自動的にサイズが大きくなりました。

そのため線の引き出しを以下のように左端からにしてしまうと、線の先のX軸の値がそろわなくなってしまいます。
```
  \draw[->, thick] (id_980042.west)node[below, xshift=-200]{Yes} -- ++(-10,0) |- (log_reporting.west);
  \draw[-, thick] (id_980044.west)node[below, xshift=-250]{Yes} -- ++(-10,0);
```

そのため、`.west`は省略して中心から引くようにしています。

### 判断からの線のYesラベルの配置はposとanchorを使うのが良い (2025-09-21 21:06更新)

~~前項のとおり、菱形の判断から横に伸びる線は判断の中心から引いているため、Yesのラベルを配置する際は`xshift`に中心からの距離を指定する必要があります。~~

```
  \draw[->, thick] (id_980042.west)node[below, xshift=-200]{Yes} -- ++(-10,0) |- (log_reporting.west);
  \draw[-, thick] (id_980044.west)node[below, xshift=-250]{Yes} -- ++(-10,0);
```

~~実は単位がよくわかっていないのですが、試行錯誤して希望の配置になるような数値を指定しています。~~

~~判断が文字数に応じてサイズが変わるので、それに合わせてxshiftも調整する必要があります。~~

~~ここはもう少し良い方法を調べたいところです。~~

(↑xshiftの単位を省略したときのデフォルトはptでした。)

上記の[TikZの使い方](https://alg-d.com/math/tikz.pdf)を読んで、線の横に書くYesやNoのラベルの配置はposとanchorを使うのが良いことが分かりました。

```
  \draw[->, thick] (id_980051.south) -- (log_reporting) node[pos=0, anchor=north west]{No};
  \draw[->, thick] (id_980042) -- ++(-10,0) node[pos=0, anchor=north east]{Yes} |- (log_reporting.west);
```

上記の「ソース：RESPONSE-980-CORRELATION.tex」の箇所もこの方式で書き換えたもので更新済みです。
