+++
Categories = []
Description = ""
Tags = []
date = "2015-06-14T16:40:05+09:00"
title = "mecab-ipadicでconfigure実行したらmatrix.defが無いというエラー"

+++
## TL;DR

https://github.com/taku910/mecab/tree/master/mecab-ipadic を取得して
`./configure --with-charset="utf-8"` と実行したら
`configure: error: cannot find sources (matrix.def) in . or ..` というエラーが出て困ってます。解決策を知っている方ぜひ教えてください。

## 経緯と詳細な手順

[rmecab](https://sites.google.com/site/rmecab/)をインストールしたくて、[RMeCab - RとLinuxと...](http://rmecab.jp/wiki/index.php?RMeCab)に沿ってまずはMeCabをインストールしました。

[MeCab - Wikipedia](http://ja.wikipedia.org/wiki/MeCab)によると公式サイトはsourceforge.netだったようですが、実際のページは[MeCab: Yet Another Part-of-Speech and Morphological Analyzer](http://mecab.googlecode.com/svn/trunk/mecab/doc/index.html)とgooglecodeにあり、ソースをダウンロードしようと探すと[Google Project Hosting](https://code.google.com/hosting/moved?project=mecab)とあり、githubに移ったようです。

ということで[taku910/mecab](https://github.com/taku910/mecab)からソースを取得してビルドしてみました。確認した環境はOS X 10.10.3です。

mecabのconfigureオプションは[Mac OS X 版バイナリ のインストール方法](http://rmecab.jp/wiki/index.php?RMeCab#content_1_2)の手順に合わせて `--with-charset="utf8"` をつけました。mecabは無事ビルド、インストール出来ました。

```
git clone https://github.com/taku910/mecab
cd mecab
./configure --with-charset="utf8"
make
make check
sudo make install
```

次はmecab-ipadicをビルドしようとしたのですが、configureでエラーになりました。configureのオプションは上記のリンクの「c. 辞書もインストールします」の説明に合わせて `--with-charset="utf-8"` をつけています。

```
$ cd ../mecab-ipadic
$ ./configure --with-charset="utf-8"
configure: error: cannot find sources (matrix.def) in . or ..
```

matrix.defがどういうものか私は全く知らないのですが、mecab-jumandicにも同名のファイルがあったので、それを使ってビルドしてみたら通ることは通りました。

```
ln -s ../mecab-jumandic/matrix.def
./configure --with-charset="utf-8"
make
sudo make install
```

ただ、「すもももももももものうち」で試してみると「すもも」「も」の後の「もも」が正しく切り出せていません。

```
$ mecab
すもももももももものうち
すもも  名詞,一般,*,*,*,*,すもも,スモモ,スモモ
も  助詞,係助詞,*,*,*,*,も,モ,モ
も  助詞,係助詞,*,*,*,*,も,モ,モ
も  助詞,係助詞,*,*,*,*,も,モ,モ
も  助詞,係助詞,*,*,*,*,も,モ,モ
も  助詞,係助詞,*,*,*,*,も,モ,モ
もの  名詞,非自立,一般,*,*,*,もの,モノ,モノ
うち  名詞,非自立,副詞可能,*,*,*,うち,ウチ,ウチ
EOS
```

ということで、mecab-ipadicの正しいビルド方法をご存知のかたはぜひ教えてください！

と書いてたら、イシュー立てるべきと気づいたので立てました。[mecab-ipadicでconfigure実行したらmatrix.defが無いというエラーが出る · Issue #18 · taku910/mecab](https://github.com/taku910/mecab/issues/18) ぜひそちらにコメントお願いします！

## 2015-06-17追記

イシューにコメントを頂きました。
https://github.com/taku910/mecab/issues/18#issuecomment-112474144

IPA辞書は http://taku910.github.io/mecab/#download  からtarballをダウンロードするのが推奨とのことです。
