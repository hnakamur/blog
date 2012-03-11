---
layout: post
title: "Xcode 4.3.1のファイルテンプレートをカスタマイズ"
date: 2012-03-11 20:22
comments: true
categories: Xcode
---
[Creating Custom Xcode 4 File Templates](http://meandmark.com/blog/2011/11/creating-custom-xcode-4-file-templates/)を参考に作成してみました。

Apple提供のファイルテンプレートは
/Developer/Platforms/iPhoneOS.platform/Developer/Library/Xcode/Templates/File Templates
にあるとのこと。ですが、Xcode 4.3.1からは/Developperではなく/Applications/Xcodeにインストールされるので、Xcode 4.3.1のみの環境ではここにはないかもしれません。

私は[MacRubyのgithubレポジトリ](https://github.com/MacRuby/MacRuby)をクローンして、misc/xcode4-templates/File Templates/Ruby/Ruby File.xctemplate/ をコピーして書き換えてカスタマイズしました。

コピー先は
/Users/ユーザ名/Library/Developer/Xcode/Templates/File Templates/グループ名/ファイルタイプ.xctemplate/
です。

コピー後Xcodeを再起動すると認識されました。

なお、オリジナルと同じグループ名とファイルタイプにすると、同じ名前のものが2つ並んで紛らわしい状態になります。ですので、違う名前にしたほうが良いです。
