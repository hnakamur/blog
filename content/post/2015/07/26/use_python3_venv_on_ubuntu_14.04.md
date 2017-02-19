Title: Ubuntu 14.04のPython3でvenvを使う手順のメモ
Date: 2015-07-26 23:09
Category: blog
Tags: python, ubuntu
Slug: 2015/07/26/use_python3_venv_on_ubuntu_14.04

Ubuntu 14.04のPython3でvenv環境をつくろうとしたらエラーになったのですが、[thefourtheye's Tech Blog: Python's venv problem with ensurepip in Ubuntu](http://www.thefourtheye.in/2014/12/Python-venv-problem-with-ensurepip-in-Ubuntu.html)に回避方法が紹介されていました。

venv環境の作成手順をメモしておきます。

## 事前準備

```
sudo apt-get install python3 python3-pip
```

## venv環境作成手順

```
pyvenv-3.4 --without-pip venv
source venv/bin/activate
curl -LO https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
```

## 2015-08-29追記: スクリプトを書きました

以下の内容を~/bin/venv3などというファイル名で保存します。sourceで実行するので実行パーミションは付けないでください。

```
venv_dir="${1:-venv}"
pyvenv-3.4 --without-pip "${venv_dir}"
source "${venv_dir}/bin/activate"
curl -L https://bootstrap.pypa.io/get-pip.py | python3
```

使い方は `source ~/bin/venv3 作成するディレクトリ名` です。作成するディレクトリ名を省略するとカレントディレクトリ下のvenvになります。
使用例は以下の通りです。

```
vagrant@vagrant-ubuntu-trusty-64:/tmp$ source ~/bin/venv3 venv3
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 1379k  100 1379k    0     0  2741k      0 --:--:-- --:--:-- --:--:-- 2737k
Collecting pip
  Using cached pip-7.1.2-py2.py3-none-any.whl
Collecting setuptools
  Using cached setuptools-18.2-py2.py3-none-any.whl
Collecting wheel
  Using cached wheel-0.24.0-py2.py3-none-any.whl
Installing collected packages: pip, setuptools, wheel
Successfully installed pip-7.1.2 setuptools-18.2 wheel-0.24.0
(venv3) vagrant@vagrant-ubuntu-trusty-64:/tmp$
```
