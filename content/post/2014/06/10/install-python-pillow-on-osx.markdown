Title: OSX上でPythonのPILの代わりにPillowをインストールする
Date: 2014-06-10 00:00
Category: blog
Tags: python
Slug: blog/2014/06/10/install-python-pillow-on-osx


試したバージョン

* Python: 2.7.7
* OSX: 10.8.5

以前作った[Google App Engine OAuth 2.0 sample](https://github.com/hnakamur/gae-oauth2-sample/)について問合せを受けたので、動作確認しようと思ったらPILのインストールでエラーになってしまいました。
とりあえず、このサンプルではPIL無くても問題なかったので、[pip_install](https://github.com/hnakamur/gae-oauth2-sample/blob/master/pip_install)からPILを外して試しました。

[【ライブラリ】Pillow : PIL (Python Imaging Library )の現代的フォーク版 | DERiVE ブログ & メルマガ](http://derivecv.tumblr.com/post/79130719546)によるとPILは開発停止していて[Pillow — Pillow v2.4.0 (PIL fork)](http://pillow.readthedocs.org/en/latest/)を使うのが良いそうです。

[python - Can't install PIL after Mac OS X 10.9 - Stack Overflow](http://stackoverflow.com/questions/19532125/cant-install-pil-after-mac-os-x-10-9)を見るとPillowのインストールには[XQuartz](http://xquartz.macosforge.org/landing/)が必要らしいです。

調べてみると、[Homebrew Cask](http://caskroom.io/)に[xquartz.rb](https://github.com/caskroom/homebrew-cask/blob/master/Casks/xquartz.rb)が含まれていました。
ということで、OSXでのインストール手順は以下で行けました。


```
brew cask install xquartz
pip install Pillow
```
