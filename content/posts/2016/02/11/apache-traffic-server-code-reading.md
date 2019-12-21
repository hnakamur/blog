+++
Categories = []
Description = ""
Tags = ["apache-traffic-server", "code-reading"]
date = "2016-02-11T23:11:50+09:00"
title = "Apache Traffic Server のコードリーディング"

+++
Apache Traffic Server のコードリーディングを少しやってみたので、将来の自分に向けてメモ。

## コードリーディングの方法についての参考文献

* [WEB+DB PRESS Vol.69｜技術評論社](http://gihyo.jp/magazine/wdpress/archive/2012/vol69)
    * [アリエル・ネットワーク㈱の井上さん](http://dev.ariel-networks.com/wp/archives/author/inoue)による「大規模コードリーディング」の特集
    * 私は[WEB+DB PRESS総集編［Vol.1～72］：書籍案内｜技術評論社](http://gihyo.jp/book/2013/978-4-7741-5783-2)を買ってたので、これに入っています。
    * [WEB+DB PRESS総集編［Vol.1～84］：書籍案内｜技術評論社](http://gihyo.jp/book/2015/978-4-7741-7538-6)というのも出ていました。将来チェックするときはより新しい総集編が出ているかチェックしましょう。
* [大規模ソースコードの読み方](http://www.slideshare.net/satorutakeuchi18/viewing-source-code)


## ツール

以下の 2 つのツールを使ってみました。

* [Doxygen](http://www.doxygen.jp/)
* [GNU GLOBAL](http://www.tamacom.com/global-j.html)

Apache Traffic Server は C++ で書かれています。 C 言語に対応したツールなら他にもあるのですが、 C++ に対応していてちゃんと動いたのはこの 2 つでした。

[GCC-XML](http://gccxml.github.io/HTML/Index.html) とその後継の [CastXML/CastXML: C-family Abstract Syntax Tree XML Output](https://github.com/CastXML/CastXML#readme) はうまくいかなくて諦めました。

### Doxygen

* [Doxygen](http://www.doxygen.jp/starting.html)
* [Doxygen/Graphvizでドキュメントを自動生成する -でじうぃき](http://onlineconsultant.jp/pukiwiki/?Doxygen%2FGraphviz%E3%81%A7%E3%83%89%E3%82%AD%E3%83%A5%E3%83%A1%E3%83%B3%E3%83%88%E3%82%92%E8%87%AA%E5%8B%95%E7%94%9F%E6%88%90%E3%81%99%E3%82%8B)

あたりを参考にしました。

https://github.com/apache/trafficserver を `git clone` したディレクトリで作業しました。

```
doxygen -g
```

で `Doxyfile` を生成して、以下のように編集しました。

```
--- Doxyfile.generated	2016-02-11 23:27:47.000000000 +0900
+++ Doxyfile	2016-01-22 20:52:30.000000000 +0900
@@ -32,13 +32,13 @@
 # title of most generated pages and in a few other places.
 # The default value is: My Project.
 
-PROJECT_NAME           = "My Project"
+PROJECT_NAME           = "Apache Traffic Server"
 
 # The PROJECT_NUMBER tag can be used to enter a project or revision number. This
 # could be handy for archiving the generated documentation or if some version
 # control system is used.
 
-PROJECT_NUMBER         =
+PROJECT_NUMBER         = 6.0
 
 # Using the PROJECT_BRIEF tag one can provide an optional one line description
 # for a project that appears at the top of each page and should give viewer a
@@ -58,7 +58,7 @@
 # entered, it will be relative to the location where doxygen was started. If
 # left blank the current directory will be used.
 
-OUTPUT_DIRECTORY       =
+OUTPUT_DIRECTORY       = ../trafficserver-doxygen
 
 # If the CREATE_SUBDIRS tag is set to YES then doxygen will create 4096 sub-
 # directories (in 2 levels) under the output directory of each output format and
@@ -802,7 +802,7 @@
 # be searched for input files as well.
 # The default value is: NO.
 
-RECURSIVE              = NO
+RECURSIVE              = YES
 
 # The EXCLUDE tag can be used to specify files and/or directories that should be
 # excluded from the INPUT source files. This way you can easily exclude a
@@ -933,13 +933,13 @@
 # also VERBATIM_HEADERS is set to NO.
 # The default value is: NO.
 
-SOURCE_BROWSER         = NO
+SOURCE_BROWSER         = YES
 
 # Setting the INLINE_SOURCES tag to YES will include the body of functions,
 # classes and enums directly into the documentation.
 # The default value is: NO.
 
-INLINE_SOURCES         = NO
+INLINE_SOURCES         = YES
 
 # Setting the STRIP_CODE_COMMENTS tag to YES will instruct doxygen to hide any
 # special comment blocks from generated source code fragments. Normal C, C++ and
@@ -1865,7 +1865,7 @@
 # captures the structure of the code including all documentation.
 # The default value is: NO.
 
-GENERATE_XML           = NO
+GENERATE_XML           = YES
 
 # The XML_OUTPUT tag is used to specify where the XML pages will be put. If a
 # relative path is entered the value of OUTPUT_DIRECTORY will be put in front of
@@ -2250,7 +2250,7 @@
 # The default value is: NO.
 # This tag requires that the tag HAVE_DOT is set to YES.
 
-CALL_GRAPH             = NO
+CALL_GRAPH             = YES
 
 # If the CALLER_GRAPH tag is set to YES then doxygen will generate a caller
 # dependency graph for every global function or class method.
@@ -2262,7 +2262,7 @@
 # The default value is: NO.
 # This tag requires that the tag HAVE_DOT is set to YES.
 
-CALLER_GRAPH           = NO
+CALLER_GRAPH           = YES
 
 # If the GRAPHICAL_HIERARCHY tag is set to YES then doxygen will graphical
 # hierarchy of all classes instead of a textual one.
```

`Doxyfile` を編集したら、以下のように実行するとドキュメントが生成されます。

```
doxygen
```

上記では `GENERATE_XML` を `YES` にしていますが、通常は `NO` で良いです。生成された HTML に不満がある場合は `YES` にして xml ファイルを生成し好みに加工すれば良いということです。

CALL_GRAPH と CALLER_GRAPH を作るには GraphViz をインストールしておく必要があります。メソッドの呼び出し図ではなくファイルのインクルード関係図っぽかったです (図のあるページへのたどり着き方を見失ってしまって現在確認できず)。

### GNU GLOBAL

コードリーディング用にはこちらのほうが使いやすかったです。Homebrewからインストールしました。

```
brew install global
```

https://github.com/apache/trafficserver を `git clone` したディレクトリで以下のコマンドを実行して `HTML` ディレクトリにドキュメントが生成しました。

```
htags -sa
```

`-s` をつけると関数などの定義箇所で名前がリンクになり、クリックすると参照箇所一覧のページに飛べます。

`-a` はアルファベットの索引を作るオプションです。

以下のように `-n` も追加するとソースリストに行番号が追加されます。ただし、コピペしようとコードを選択すると行番号も混ざってしまいます。

```
htags -sa
```

ソースコードのフォントを Monaco にするには `HTML/styles.css` に以下のコードを追加します。

```
pre {
        font-family: Monaco;
}
```

時々参照箇所へのリンクが違うクラスに飛んだりすることがあったので、その場合は [the_platinum_searcher](https://github.com/monochromegane/the_platinum_searcher) で

```
pt -G '\.(h|cc)$' 文字列
```

や

```
pt -e -G '\.(h|cc)$' 正規表現
```

で検索しました。

## コードリーディングのメモ

[hnakamur/trafficserver-code-reading: This is my code reading memo for Apache Traffic Server](https://github.com/hnakamur/trafficserver-code-reading) に置きました。
