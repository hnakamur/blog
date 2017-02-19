Title: LXDのREST APIクライアントライブラリpylxdを試してみた
Date: 2016-05-07 21:17
Category: blog
Tags: lxd, python
Slug: blog/2016/05/07/tried-pylxd

Python Package Index (PyPI)の [pylxd 2.0.0](https://pypi.python.org/pypi/pylxd/2.0.0)のページにインストール方法と使い方の例が書いてあるので、これに沿って試しました。

## インストール

Ubuntu 16.04だとaptでインストール可能なのでそちらでインストールしました。Python3用のpython3-pylxdパッケージとPython2用のpython-pylxdパッケージがありますが、今後Ansibleのモジュールを作ることを想定してPython2用のパッケージをインストールして試してみました。

```
sudo apt install -y python-pylxd
```

インストールしたpython-pylxdのバージョンは `2.0.0-0ubuntu1` です。

```
$ dpkg-query -W -f='${Version}\n' python-pylxd
2.0.0-0ubuntu1
```

## 試してみる

```
$ python
Python 2.7.11+ (default, Apr 17 2016, 14:00:29)
[GCC 5.3.1 20160413] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> from pylxd import api
>>> lxd = api.API()
>>> lxd.container_defined('cent01')
True
>>> lxd.container_defined('hoge')
False
>>> lxd.container_list()
[u'cent01', u'cent02']
```

ここから先は [pylxd/client.py](https://github.com/lxc/pylxd/blob/master/pylxd/client.py) と [pylxd/container.py](https://github.com/lxc/pylxd/blob/master/pylxd/container.py) の ソースを見ながら試しました。

```
>>> from pylxd.client import Client
>>> client = Client()
>>> client.containers.all()
[<pylxd.container.Container object at 0x7fd44065db00>, <pylxd.container.Container object at 0x7fd44065db98>]
>>> client.containers.get(u'cent01')
<pylxd.container.Container object at 0x7fd44065dc30>
>>> client.containers.get(u'cent01').status
u'Running'
```
