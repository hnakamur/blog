Title: GeForce搭載の旧モデルMacBook ProでCaffeをビルドする手順メモ
Date: 2015-07-26 00:53
Category: blog
Tags: machine-learning, caffe
Slug: 2015/07/26/build_caffe_on_macbook_with_geforce

## はじめに
[GeForce搭載の旧モデルMacBook ProでCUDAをセットアップする手順のメモ](/blog/2015/07/25/setup_cuda_on_macbook_pro_with_geforce/)でCUDA 7.0.29をインストールしたMacBook Proで[Caffe | Deep Learning Framework](http://caffe.berkeleyvision.org/)をビルドしてみた手順メモです。

[PyPIでCaffeで検索](https://pypi.python.org/pypi?%3Aaction=search&term=caffe&submit=search)しても出てこないので、ソースからビルドするしかないようです。

[OS X Installation](http://caffe.berkeleyvision.org/install_osx.html)を参考にしつつ、一部手順を変更してインストールしました。

## CaffeはPython3非対応

[Python - はじめるDeep learning - Qiita](http://qiita.com/icoxfog417/items/65e800c3a2094457c3a0)で紹介されていた[Python3 support · Issue #293 · BVLC/caffe](https://github.com/BVLC/caffe/issues/293)によると、オフィシャルでPython3対応の予定はないとのこと。Python3でも動かないこともないそうですが、初心者なのでまずはPython2で動かすことにします。

## 依存ライブラリのインストール

依存するライブラリを以下のコマンドでインストールしました。

```
brew install -vd snappy leveldb gflags glog szip lmdb
brew tap homebrew/science
brew install hdf5 opencv
```

### protobufのインストール

以下のコマンドでprotobufをインストールします。

```
brew install protobuf
```

[OS X Installation](http://caffe.berkeleyvision.org/install_osx.html)の手順では `--with-python` オプションを指定していますが、 `brew info protobuf` で確認すると2.6.1用のformulaでは `--with-python` オプションは無くなって代わりに `--without-python` オプションが出来ていました。何も指定しなければpythonサポートが入るようです。

なお、インストール完了時に以下のメッセージが出ますが、後でvirtualenvで作った環境内で `pip install protobuf` すればいけるので、ここに書かれている対応は不要でした。

```
==> Caveats
Editor support and examples have been installed to:
  /usr/local/Cellar/protobuf/2.6.1/share/doc/protobuf

Python modules have been installed and Homebrew's site-packages is not
in your Python sys.path, so you will not be able to import the modules
this formula installed. If you plan to develop with these modules,
please run:
  mkdir -p
  echo 'import site; site.addsitedir("/usr/local/lib/python2.7/site-packages")' >> homebrew.pth
```

### boost 1.57.0, boost-python 1.57.0 のインストール

`brew install boost boost-python` だと1.58.0が入ったのですが、Caffeのビルド時にコンパイルエラーが出ました。[Itinerant Bioinformaticist: Caffe incompatible with Boost 1.58.0](http://itinerantbioinformaticist.blogspot.jp/2015/05/caffe-incompatible-with-boost-1580.html)と同じエラーですが、ここに回避方法も書かれていたので、これに従いました。

まず、boost 1.58.0, boost-python 1.58.0が入っている場合はアンインストールします。

```
brew uninstall boost boost-python
```

以下の手順で1.57.0をソースからインストールします。

```
cd `brew --prefix`/Library/Formula
curl -O https://raw.githubusercontent.com/Homebrew/homebrew/6fd6a9b6b2f56139a44dd689d30b7168ac13effb/Library/Formula/boost.rb
curl -O https://raw.githubusercontent.com/Homebrew/homebrew/3141234b3473717e87f3958d4916fe0ada0baba9/Library/Formula/boost-python.rb
brew install --build-from-source -vd boost boost-python
```

## Python2でvirtualenvで作業用の環境を作成して依存ライブラリをインストール

個人的にはAnaconda Pythonのようなオールインワンのインストーラはあまり好きではないので、[riywo/anyenv](https://github.com/riywo/anyenv)と[yyuu/pyenv](https://github.com/yyuu/pyenv)で入れたPython 2.7.10を使いました。

作業用のディレクトリ `~/work/caffe` を作ってvirtualenvで環境を作りました。

```
mkdir -p ~/work/caffe
cd !$
pyenv local 2.7.10
virtualenv venv
source venv/bin/activate
```

HomebrewでインストールしたPython 2.7.10でも `pyenv local 2.7.10` の行を除けば同じ手順で行けました。

Caffeで必要なprotobufとnumpyを以下の手順でインストールします。

```
pip install protobuf
pip install numpy
```

## Caffeのソースを取得してビルド

ソースを取得してディレクトリに入ります。

```
cd ~/work/caffe
git clone https://github.com/BVLC/caffe
cd caffe
```

[Installation](http://caffe.berkeleyvision.org/installation.html#compilation)を参考にビルドします。virtualenv環境のincludeとlibディレクトリを参照するように以下のように加工してMakefile.configを作成します。Caffeのソースを違うディレクトリに配置した場合は適宜変更してください。

```
sed '
s|/usr/include/python2.7|$(HOME)/work/caffe/venv/include/python2.7|
s|/usr/lib/python2.7/dist-packages|$(HOME)/work/caffe/venv/lib/python2.7/site-packages|
' Makefile.config.example > Makefile.config
```

Caffeをビルドします。

```
make all
```

テストコードをビルドします。

```
make test
```

テストを実行します。

```
(venv)$ make runtest
...(略)...
[----------] Global test environment tear-down
[==========] 1356 tests from 214 test cases ran. (306870 ms total)
[  PASSED  ] 1356 tests.

  YOU HAVE 2 DISABLED TESTS

```

ということで、Caffeをビルドする手順でした。
