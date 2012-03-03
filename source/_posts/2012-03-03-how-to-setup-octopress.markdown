---
layout: post
title: "octopressでgithubにブログ開設"
date: 2012-03-03 18:34
comments: true
categories: octopress
---
rbenvとoctopressをインストールしてgithubにブログを作る手順のメモです。

## rbenvをインストール

* [sstephenson/rbenv](https://github.com/sstephenson/rbenv#section_2.1)
* [sstephenson/ruby-build]( https://github.com/sstephenson/ruby-build)

を参考にインストールしました。

インストール先は~/.rbenvとしました。

```
cd
git clone git://github.com/sstephenson/rbenv.git .rbenv

echo 'export PATH="$HOME/.rbenv/bin:$PATH"' >> .bash_profile
echo 'eval "$(rbenv init -)"' >> .bash_profile

. ~/.bash_profile
```


ruby-buildをインストールします。なお、私はHomebrewを使っているので/usr/localには書き込み権限をつけてあります。

```
cd
git clone git://github.com/sstephenson/ruby-build.git
cd ruby-build
./install.sh
```

rbenvでruby 1.9.2-p290をインストール。
```
rbenv install 1.9.2-p290
```

```
$ rbenv versions
* 1.9.2-p290 (set by /Users/hnakamur/octopress/.rbenv-version)
```
でインストールされたrubyがrbenvで認識されたことを確認。

```
rbenv global 1.9.2-p290
```
で切替。

```
$ which ruby
/Users/hnakamur/.rbenv/shims/ruby
$ ruby --version
ruby 1.9.2p290 (2011-07-09 revision 32553) [x86_64-darwin11.3.0]
```


## octopressでgitにブログをセットアップ

[Deploying to Github Pages - Octopress](http://octopress.org/docs/deploying/github/)
を参考にセットアップしました。

ここでは~/octopressを作業ディレクトリとしました。

```
cd
git clone git://github.com/imathis/octopress.git octopre
cd octopress
ruby --version
gem install bundler
rbenv rehash
rake install
```

ブラウザでgithubを開き、自分のアカウント(私の場合はhnakamur)でblogというプロジェクトを作ります。ブラウザで https://github.com/hnakamur/blog を開き、"Next steps:"に
```
git remote add origin git@github.com:hnakamur/blog.git
```
と書かれている行のgitのURL(ここではgit@github.com:hnakamur/blog.git)をコピーします。

その後
```
rake setup_github_pages
```
を実行し、"Enter the read/write url for your repository:"というプロンプトが出たらURLを貼り付けます。
```
Enter the read/write url for your repository: git@github.com:hnakamur/blog.git
```

```
vi _config.yml
```

```
title: "hnakamur's blog at github"
subtitle: my trial and error log
author: Hiroaki Nakamura
…(略)…
date_format: "%Y-%m-%d"
```

## 記事の作成と投稿

```
rake new_post['Hello, octopress!']
```
と実行すると、最後に
```
Creating new post: source/_posts/2012-03-03-hello.markdown
```
と作成されたファイルが表示されます。

エディタでこのファイルを開いて記事を書きます。
```
vi source/_posts/2012-03-03-hello.markdown
```

```
---
layout: post
title: "Hello, octopress!"
date: 2012-03-03 17:57
comments: true
categories: octopress
---
octopressでブログ記事を投稿してみるテスト。
```

```
rake generate
```
でHTMLが生成されます。

```
rake preview
```
を実行して、ブラウザで
http://localhost:4000/blog/
を開くと、プレビューできます。

```
rake deploy
```
でgithubにプッシュされ、10分ぐらい待つと
http://hnakamur.github.com/blog/
に記事のページで作られました。

時間がかかるのは初回にgithub pagesを作るときだけで、次回以降は即座に作られました。

## 記事のソースをgithubにプッシュ

リモートの設定にoriginを追加して、そこをデフォルトのブランチに設定。
```
git remote add origin git@github.com:hnakamur/blog.git
git config branch.master.remote origin
```

設定の変更と生成されたソースをコミット、プッシュします。
```
git add .
git commit -m 'Modify config. Add source and sass'
git push origin source
```

## ローカルのApacheでプレビュー

Apacheは事前にセットアップ済みという前提で、プレビュー用の設定を追加します。

```
sudo vi /etc/apache2/other/blog.conf
```
と実行して、以下の内容で作成します(hnakamurの部分は自分のアカウント名で置換してください)。
```
Alias /blog /Users/hnakamur/octopress/public/blog
<Directory /Users/hnakamur/octopress/public/blog>
	AllowOverride None
  DirectoryIndex index.html
	Order allow,deny
	Allow from all
</Directory>
```

```
sudo apachectl restart
```
でApacheを再起動します。

これ以降は記事を編集してrake generateだけ実行すれば [http://localhost/blog/](http://localhost/blog/) を開いてプレビューできます。

## 今回のはまりポイント

### YAMLで文字列を""で囲む必要があった

```
$ rake generate
(in /Users/hnakamur/octopress)
## Generating Site with Jekyll
unchanged sass/screen.scss
/Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/1.9.1/psych.rb:148:in `parse': couldn't parse YAML at line 16 column 13 (Psych::SyntaxError)
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/1.9.1/psych.rb:148:in `parse_stream'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/1.9.1/psych.rb:119:in `parse'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/1.9.1/psych.rb:106:in `load'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/1.9.1/psych.rb:205:in `load_file'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/gems/1.9.1/gems/jekyll-0.11.0/lib/jekyll.rb:119:in `configuration'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/gems/1.9.1/gems/jekyll-0.11.0/bin/jekyll:207:in `<top (required)>'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/gems/1.9.1/bin/jekyll:19:in `load'
	from /Users/hnakamur/.rbenv/versions/1.9.2-p290/lib/ruby/gems/1.9.1/bin/jekyll:19:in `<main>'
```
_config.ymlの
```
date_format: %Y-%m-%dT%k:%M:%S%z
```
を
```
date_format: "%Y-%m-%dT%k:%M:%S%z"
```
と修正して再実行したらOKでした。


### git push origin sourceでエラー

```
$ git push origin source
error: src refspec source does not match any.
error: failed to push some refs to 'git@github.com:hnakamur/blog.git'
```

ググって
Error when "git push" to github - Stack Overflow
http://stackoverflow.com/questions/959477/error-when-git-push-to-github
を発見。

```
git push origin HEAD:source
```
にしたらOK。
