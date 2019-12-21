+++
title="ブログのソフトウェアをHugoからPelicanに切り替えた"
date = "2017-02-19T23:20:00+09:00"
lastmod = "2017-02-20T16:34:00+09:00"
tags = ["pelican"]
+++


## はじめに

[Hugo](https://gohugo.io/) はビルドも速くて快適に使わせてもらっていました。ただ、コードブロックのシンタクスハイライトを使いたいと思って [Syntax Highlighting](https://gohugo.io/extras/highlighting/) を読んだときにHugo独自の記法に依存するのが好ましくないなと思いました。Markdownには拡張の仕組みがないので仕方ないのですが。以前から [reStructuredText](http://docutils.sourceforge.net/rst.html) を使うようにしたいと思いつつ使えてなかったので、この機会に reStructuredText を使ってブログを書くようにしたいと思いました。

Hugoにも [Add support for native Go implementation of reStructuredText (reST) · Issue #1436 · spf13/hugo](https://github.com/spf13/hugo/issues/1436) というイシューがあったのですが、まだ先は長そうな感じです。 また [Syntax Highlighting](https://gohugo.io/extras/highlighting/) を見るとシンタクスハイライトで行番号を付けたい場合は [Pygments](http://pygments.org/) というPythonで書かれたパッケージを使うということがわかりました。 それと reStructuredText 関連もGoよりPythonのほうが充実しています。

ということで、 Python で reStructuredText を扱えるブログパッケージを探してみると [Pelican Static Site Generator, Powered by Python](https://blog.getpelican.com/) というのが見つかったので、これに乗り換えました。

この記事は乗り換えた時の作業メモと今後の記事を書く時の私用の手順メモです。


# Pelicanのインストール

CentOS 7環境を作りました。 [IUS](https://ius.io/) のレポジトリから python36u パッケージをインストールした状態で以下のコマンドでインストールしました。

```console
python3.6 -m venv venv
source venv/bin/activate
pip install pelican pygments ghp-import
```

その後 [`pip freeze > pip_requirements.txt`` してあるので、後から `hnakamur/blog: hnakamur's blog at github](https://github.com/hnakamur/blog/) を ``git clone`` したときは以下の手順で構築できます。

```console
python3.6 -m venv venv
source venv/bin/activate
pip install -r pip_requirements.txt
```

# 設定

私は Octporess → Hugo → Pelican と移行しているので記事のURLがそのままになるように設定を調整しました。

[pelicanconf.py#L43-L47](https://github.com/hnakamur/blog/blob/47217f6dc80d6148f9c9265014dee85e0b0f8408/pelicanconf.py#L43-L47)

```python {linenos=table,linenostart=43}
RELATIVE_URLS = True
ARTICLE_URL = '{slug}/'
ARTICLE_SAVE_AS = '{slug}/index.html'
PAGE_URL = 'pages/{slug}/'
PAGE_SAVE_AS = 'pages/{slug}/index.html'
```

他にも、日付のフォーマット、出力先ディレクトリ名、Google Analyticsの設定などを行っています。

# 記事のメタ情報書き変え

Pelican は Markdown と reStructuredText の両方が扱えるので、既存のMarkdownの記事は流用することにしました。
ただし作成日などのメタ情報は [File metadata](http://docs.getpelican.com/en/stable/content.html#file-metadata) の形式に合わせる必要があります。
そこでPythonでその場限りのスクリプト [hugo2pelican.py](https://github.com/hnakamur/blog/blob/47217f6dc80d6148f9c9265014dee85e0b0f8408/hugo2pelican.py) を書いて変換しました。

その後 slug の値に [`blog/`` が入っていたのを削るため `hugo2pelican2.py](https://github.com/hnakamur/blog/blob/47217f6dc80d6148f9c9265014dee85e0b0f8408/hugo2pelican2.py) で更に変換しました。
本来はデータを戻してスクリプトを書き変えて再実行するのが良いのですが、変換後にコミットしたりタグを手動修正したりしていたので、追加で変換しました。

# テーマのカスタマイズ

デフォルトのテーマ ``notmyidea`` のディレクトリ ``venv/lib/python3.6/site-packages/pelican/themes/notmyidea`` を ``themes`` ディレクトリ以下に ``notmyidea-custom``  という名前に変えてコピーしカスタマイズしました。

### シンタクスハイライト用のCSS追加

[themes/notmyidea-custom/static/css/pygment.css#L1-L12](https://github.com/hnakamur/blog/blob/47217f6dc80d6148f9c9265014dee85e0b0f8408/themes/notmyidea-custom/static/css/pygment.css#L1-L12)

```python {linenos=table}
.highlighttable td {
padding: 0;
}
.highlighttable td.linenos {
width: 4rem;
}
.highlighttable td.linenos pre {
text-align: right;
}
.highlighttable pre {
margin: 4px;
}
```

## トップページの内容を記事一覧に変更

Hugoを使っていた時はトップページは記事一覧にしていたので、テンプレートを大幅に書き変えて同じような内容にしました。
[Adjust theme for article list · hnakamur/blog@b59771b](https://github.com/hnakamur/blog/commit/b59771b74408a71fae78a7a0d32fcd5348c6867e#diff-a88c508419b8e3db74c1a64be7f9d96f)

Pelicanは テンプレートエンジンとして [Jinja2](http://jinja.pocoo.org/docs/2.9/) を使っています。
Ansibleでも使っていて私は慣れているのでさくっと変更できました。

## 幅を広げる

文章メインのブログでは元のテーマのほうが読みやすいと思いますが、コードブロックはなるべく幅を広くしておきたいので調整しました。
[Modify theme to widen nav to 940px and content to 900px · hnakamur/blog@b6fba1e](https://github.com/hnakamur/blog/commit/b6fba1ec659b53d38254d843e46ee396b64a7499#diff-a88c508419b8e3db74c1a64be7f9d96f)

# 記事を書く手順

以下のコマンドを実行して、 ``content`` ディレクトリ以下のファイルに変更を検知したらサイトのHTMLを自動生成するようにします。

```console
source venv/bin/activate
pelican -r content
```

別の端末で以下のコマンドを実行して開発サーバを起動してプレビューできるようにしておきます。

```console
source venv/bin/activate
(cd public && python -m pelican.server)
```

この状態で ``contents/YYYY/MM/DD/my-super-title.rst`` という形式でファイルを作って編集します。
件名とメタ情報を [File metadata](http://docs.getpelican.com/en/stable/content.html#file-metadata) の reStructuredText の形式で書きます。


```rst
My super title
##############

:date: 2017-02-19 23:20
:modified: 2017-02-20 16:34
:tags: thats, awesome
:category: blog
:slug: YYYY/MM/DD/my-super-title
```

保存する度に自動生成が動きます。
[さくらのVPS](http://vps.sakura.ad.jp/) の1Gプランの環境で記事数119で12秒前後かかります。
Hugoのときに比べると長いですが、許容範囲です。

[`code-block`` によるとシンタクスハイライトで使える言語一覧は `Available lexers — Pygments](http://pygments.org/docs/lexers/) にあります。

記事を書き終わったら、以下のコマンドを実行して変更をコミットします。

```console
git add .
git commit -v
```

実際はbashのエイリアスと ``~/.gitconfig`` でサブコマンドもエイリアスを付けているので以下の通りです。

```console
g a .
g ci
```

# 記事をGitHub Pagesに公開

[Publishing to GitHub](http://docs.getpelican.com/en/stable/tips.html?highlight=github%20pages#publishing-to-github) に説明があります。
私は Hugo のときに使っていた ``deploy.sh`` を以下のように書き変えました。

[deploy.sh](https://github.com/hnakamur/blog/blob/47217f6dc80d6148f9c9265014dee85e0b0f8408/deploy.sh)

```bash
#!/bin/bash

echo -e "\033[0;32mDeploying updates to GitHub...\033[0m"

pelican content
ghp-import public
git push origin master gh-pages
```

今まで通り以下のコマンドで公開できます。

```console
./deploy.sh
