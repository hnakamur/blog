Title: Hugoに移行した私のブログの記事追加手順
Date: 2015-04-19 00:17
Category: blog
Tags: hugo
Slug: 2015/04/19/my_hugo_blog_workflow


## はじめに

[OctopressからHugoへ移行した | SOTA](http://deeeet.com/writing/2014/12/25/hugo/)を参考に私のブログもしばらく前にHugoに移行しました。deeeetさん、ありがとうございます！

で、ブログ書く間隔が開くと手順を忘れて、毎回hugoのドキュメントを読むのが面倒なので、自分用メモです。

## 記事のファイルを作成

Octorpressのときのpermalinkを維持するために、記事ファイルのパスは `content/post/YYYY/MM/DD/foo.md` というような感じになっています。

`hugo new` でファイルを作成する際は `content` を除いた部分を指定して以下のようにします。


```
hugo new post/2015/04/19/my_hugo_blog_workflow.md
```

## 記事を編集してローカルで表示確認

以下のコマンドでローカルマシンでサーバを起動しておきます。

```
hugo server --watch
```

http://localhost:1313/blog/ をブラウザで開いて編集した内容を確認します。

## テーマの調整

私のブログでは [eliasson/liquorice](https://github.com/eliasson/liquorice) を改変した独自テーマ [hnakamur/liquorice-hn](https://github.com/hnakamur/liquorice-hn) を使っています。

テーマを調整したい場合は [hnakamur/blog](https://github.com/hnakamur/blog) を `git clone` したディレクトリの `themes/liquorice-hn` フォルダ配下のファイルを書き換えます。

CSSを変えた場合は [hnakamur/liquorice-hn](https://github.com/hnakamur/liquorice-hn#build-with-npm-run) の手順でminifyします。

テーマの修正が終わったら、テーマの修正したファイル `git add` して `git commit` します。その後 [hnakamur/blog](https://github.com/hnakamur/blog) を `git clone` したディレクトリで以下のコマンドを実行してgithubにpushします。

```
git subtree push --prefix themes/liquorice-hn liquorice-hn master
```

初回のみの事前準備として以下のようにremoteを追加しておきます。

```
git remote add liquorice-hn https://github.com/hnakamur/liquorice-hn
```

## 記事を発行

記事を書き終えて、ローカルで表示を確認したら、[hnakamur/blog](https://github.com/hnakamur/blog) を `git clone` したディレクトリで以下のコマンドを実行してgithub-pages上のブログを更新します。

```
./deploy.sh
```
