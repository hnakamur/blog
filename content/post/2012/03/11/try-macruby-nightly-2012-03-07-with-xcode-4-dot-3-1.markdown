Title: macruby-nightly-2012-03-07をXcode 4.3.1で試す
Date: 2012-03-11 00:00
Category: blog
Tags: macruby, xcode
Slug: 2012/03/11/try-macruby-nightly-2012-03-07-with-xcode-4-dot-3-1

[おまいらもMacRubyでMacアプリ作ろう - @sugamasao.blog.title # => ”コードで世界を変えたい”](http://d.hatena.ne.jp/seiunsky/20111225/1324740191)を見て、ファイルやプロジェクトのテンプレートを追加すればXcode 4.3.1も使えそうだと思い、[Snow LeopardのXcodeにRubyCocoaのテンプレートをインストール - 高尾宏治日記 on はてな](http://d.hatena.ne.jp/kouji0625/20090919/p1)を参考にコピーしてみようかと思ったのですが、[#1466 (does not install MacRuby's Templetes and rb_nibtool into Xcode 4.3) – MacRuby](http://www.macruby.org/trac/ticket/1466)というページを見つけました。

```
sudo xcode-select -switch /Applications/Xcode.app/Contents/Developer/ 
```
を実行しておいてから、
[MacRuby » Files](http://www.macruby.org/files/nightlies/)から[macruby_nightly-2012-03-07.pkg](http://www.macruby.org/files/nightlies/macruby_nightly-2012-03-07.pkg)を実行してインストールしてみました。

これでばっちりになりました。新規プロジェクト作成で[MacRuby Application]も選択可能ですし、Interface BuilderでHelloWorldControllerのoutletも認識されました。
