+++
title = "HomebrewのPython2とPython3でvirtualenv環境を作成する手順メモ"
date = "2015-07-26T02:28:00+09:00"
categories = ["blog"]
tags = ["python"]
slug = "2015/07/26/how_to_use_venv_with_homebrew_python2_and_3"
+++

## はじめに
ここしばらく[riywo/anyenv](https://github.com/riywo/anyenv)と[yyuu/pyenv](https://github.com/yyuu/pyenv)でPython 2.7.10をPython 3.4.3を使い分けてきたのですが、私の用途だと2系と3系の最新だけ使えればいいことがわかりました。

そこで、pyenvを止めてhomebrewのpython2と3を使うことにしました。自分用にPython2のvirtualenvとPython3のvenvで仮想環境を作る手順のメモを書いておきます。

## 事前準備

Python2とvirtualenvのインストール。

```
brew install python
pip install virtualenv
```

Python3のインストール。

```
brew install python3
```

インストールされるコマンドはpythonとpipがPython2用で、python3とpip3がPython3用となっています。

## Python2の仮想環境の作成と有効化の手順

作業ディレクトリを作ってそこに移動し、venvというサブディレクトリにPython2用のvirtualenvを作って有効化するのは以下のようにします。

```
mkdir -p $(作業ディレクトリ名)
cd !$
virtualenv venv
source venv/bin/activate
```

## Python3の仮想環境の作成と有効化の手順

Python3では`virtualenv`コマンドではなくPython 3.3で追加された[venv](https://docs.python.org/3/library/venv.html?highlight=venv#module-venv)という標準モジュールを使います。

作業ディレクトリを作ってそこに移動し、venvというサブディレクトリにPython2用のvirtualenvを作って有効化するのは以下のようにします。

```
mkdir -p $(作業ディレクトリ名)
cd !$
python3 -m venv venv
source venv/bin/activate
```

`python3 -m venv venv` の1つめの `venv` はモジュール名で2つめの `venv` は作成するサブディレクトリ名です。

`source venv/bin/activate` でvenv環境を有効化した後は `python3` と `pip3` ではなく `python` と `pip` でコマンドを実行します。
