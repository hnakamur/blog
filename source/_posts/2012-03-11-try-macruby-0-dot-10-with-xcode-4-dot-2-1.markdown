---
layout: post
title: "XCode 4.2.1でMacRuby 0.10を試す"
date: 2012-03-11 10:42
comments: true
categories: [MacRuby, XCode]
---
## XCode 4.1やXCode 4.3.1ではうまくいかずXCode 4.2.1ならOKだった
最終的にうまく行ったバージョンの組み合わせは以下の通りです。

* Mac OS X 10.7.3
* XCode 4.2.1
* MacRuby 0.10

最初は以下の環境でした。

* Mac OS X 10.7.3
* XCode 4.1 (4.1.xのxはうろ覚えだけど4.1.1だったかな)

[MacRuby » Download MacRuby](http://www.macruby.org/downloads.html)
からMacRuby 0.10をダウンロードし、インストールしました。

[MacRuby » Introductory Tutorial](http://www.macruby.org/documentation/tutorial.html)を試していたのですが、XCodeのInterface BuilderでHelloWorldControllerを作ってもoutletが認識されないという問題が発生しました。

ググってみると[#1322 (Xcode 4.1/4.2) – MacRuby](http://www.macruby.org/trac/ticket/1322)というページが。で、とりあえず最新のXCode 4.3.1をApp Storeからインストールしてみました。インストール時には元のXCode 4.1は消さずに残すようにしました。
で、XCode 4.3.1で試したのですが[File]/[New]/[Project ...]メニューを選んで、[Mac OS X]の[Application]を選んでも[MacRuby Application]が出てこない。

MacRubyより後にXCode 4.3.1をインストールしたので認識されていないのかなと思い、再度MacRuby 0.10のインストーラを実行するも変わらず。

XCode 4.3.1のインストーラに古いXCodeを消すか聞かれた時に、XCode 4.1とInstall XCode 4.2.1が並んでいて、Install XCode 4.2.1の行には/Applications/Install XCode.appと書かれていました。そこでそれを実行してみると、XCode 4.1が4.2.1にアップグレードされました。

これでようやくInterface BuilderでHelloWorldControllerのoutletが認識されるようになりました。

[What's New In Xcode: New Features in Xcode 4.3](https://developer.apple.com/library/mac/#documentation/DeveloperTools/Conceptual/WhatsNewXcode/Articles/xcode_4_3.html)にも書かれていますが、XCode 4.1/4.2は/Developer、XCode 4.3.1は/Applications/XCode.appにインストールされます。

さらに、[osx - Can I have multiple XCode versions installed? - Stack Overflow](http://stackoverflow.com/questions/669367/can-i-have-multiple-xcode-versions-installed)によるとXCodeのインストーラ実行時に[location...]プルダウンでインストール先のディレクトリを変えておけば複数バージョンの同居は可能らしいです。私は既に4.1を4.2.1にアップグレードしてしまったので4.2.1と4.3.1のみですが、これを知ってたら4.1も残しておきたかった。

[xcode-select(1) Mac OS X Developer Tools Manual Page](https://developer.apple.com/library/mac/#documentation/Darwin/Reference/ManPages/man1/xcode-select.1.html)によると、4.2.1への切替は
```
xcode-select -switch /Developer
```
[MacRuby/MacRuby](https://github.com/MacRuby/MacRuby)によると、4.3.1への切替は
```
sudo xcode-select -switch /Applications/Xcode.app/Contents/Developer/
```
で出来るようです。と書きながら気付いたのですが、上のリンクにMacRubyのインストール前にこれをやる必要があるかもと書いてますね。しかし、これをやってからMacRubyを再度インストールしてみましたが、やっぱり新規プロジェクト作成で[MacRuby Application]は出て来ませんでした。

ただ、xcode-selectで何が変わるのかはよくわかりません。XCode自体は4.2.1は/Developer/Applications/XCode.app、4.3.1は/Applications/XCode.appで起動すればよいだけですし。
