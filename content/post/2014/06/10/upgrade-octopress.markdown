---
layout: post
title: "久々にoctopressをアップデート"
date: 2014-06-10
comments: true
categories: octopress
---

octopressをアップデートした時にハマったのでメモ。
アップデート手順は[octopressをアップデートしてisolateを使い始めた - @znz blog](http://blog.n-z.jp/blog/2013-12-21-update-octopress.html)の「octopress のアップデート」の部分を参考にしました。ありがとうございます。

## Octopressのアップデート

[Updating Octopress - Octopress](http://octopress.org/docs/updating/)の"How to Update"のコマンドを順に実行しました。

```
git pull octopress master     # Get the latest Octopress
bundle install                # Keep gems updated
rake update_source            # update the template's source
rake update_style             # update the template's style
```

git pullではconflictsが起きたので、適宜修正しました。基本的にはHEAD側を採用。

## sass-globbingをGemfileに追加。

```
bundle exec rake generate
```

を実行した時に

```
LoadError on line ["161"] of /Users/hnakamur/octopress/vendor/bundle/ruby/2.1.0/gems/compass-0.12.6/lib/compass/configuration/data.rb: cannot load such file -- sass-globbing
```

というエラーが出ました。

Gemfileにsass-globbingを追加して、```bundle```でインストールするとエラーは解消しました。
