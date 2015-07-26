+++
Categories = []
Description = ""
Tags = ["python", "ubuntu"]
date = "2015-07-26T23:09:17+09:00"
title = "Ubuntu 14.04のPython3でvenvを使う手順のメモ"

+++
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
