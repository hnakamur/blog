Title: GeForce搭載の旧モデルMacBook ProでPyCUDAを試してみた
Date: 2015-07-25 18:31
Category: blog
Tags: cuda, python
Slug: blog/2015/07/25/setup_pycuda_on_macbook_pro_with_geforce

## はじめに

[GeForce搭載の旧モデルMacBook ProでCUDAをセットアップする手順のメモ](../setup_cuda_on_macbook_pro_with_geforce/)でCUDAをセットアップした後、[PyCUDA](http://mathema.tician.de/software/pycuda/)も試してみたのでメモしておきます。

[PyCUDA](http://mathema.tician.de/software/pycuda/)のページの `Prerequisites` に `Boost`, `CUDA`, `Numpy` が書かれています。

CUDAは[GeForce搭載の旧モデルMacBook ProでCUDAをセットアップする手順のメモ](../setup_cuda_on_macbook_pro_with_geforce/)でセットアップ済みです。

## Boostのインストール

Boostは [Homebrew — The missing package manager for OS X](http://brew.sh/) でインストールしました。

```
brew update
brew install boost
```

インストールされたboostのバージョンは以下の通りです。

```
$ brew info boost
boost: stable 1.58.0 (bottled), HEAD
Collection of portable C++ source libraries
http://www.boost.org
/usr/local/Cellar/boost/1.58.0 (10718 files, 486M) *
  Poured from bottle
From: https://github.com/Homebrew/homebrew/blob/master/Library/Formula/boost.rb
==> Dependencies
Optional: icu4c ✘
==> Options
--c++11
	Build using C++11 mode
--universal
	Build a universal binary
--with-icu4c
	Build regexp engine with icu support
--with-mpi
	Build with MPI support
--without-single
	Disable building single-threading variant
--without-static
	Disable building static library variant
--HEAD
	Install HEAD version
```

## NumpyとPyCUDAをインストールして試してみる

[riywo/anyenv](https://github.com/riywo/anyenv)と[yyuu/pyenv](https://github.com/yyuu/pyenv)で入れたPython 3.4.3を使い、 `~/sandbox/pycuda` という作業ディレクトリを作成してvenv環境を作って試しました。

以下の手順でvenv環境を作って有効にします。

```
mkdir -p ~/sandbox/pycuda
cd !$
python -m venv venv
source venv/bin/activate
```

`(venv) $` プロンプト内で以下のコマンドでNumPyとPyCUDAをインストールします。

```
pip install numpy
pip install pycuda
```

PyCUDAのほうは以下のような警告が出ましたが、インストールは出来ました。

```
    /Users/hnakamur/sandbox/pycuda/venv/lib/python3.4/site-packages/numpy/core/include/numpy/npy_1_7_deprecated_api.h:15:2: warning: "Using deprecated NumPy API, disable it by "          "#defining NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION" [-W#warnings]
    #warning "Using deprecated NumPy API, disable it by " \
     ^
    src/wrapper/_pvt_struct_v3.cpp:1047:30: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        static char *kwlist[] = {"format", 0};
                                 ^
    src/wrapper/_pvt_struct_v3.cpp:1166:30: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        static char *kwlist[] = {"buffer", "offset", 0};
                                 ^
    src/wrapper/_pvt_struct_v3.cpp:1166:40: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        static char *kwlist[] = {"buffer", "offset", 0};
                                           ^
    src/wrapper/_pvt_struct_v3.cpp:1224:17: warning: unused variable 'isstring' [-Wunused-variable]
                int isstring;
                    ^
    src/wrapper/_pvt_struct_v3.cpp:1430:6: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        {"format", (getter)s_get_format, (setter)NULL, "struct format string", NULL},
         ^
    src/wrapper/_pvt_struct_v3.cpp:1430:52: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        {"format", (getter)s_get_format, (setter)NULL, "struct format string", NULL},
                                                       ^
    src/wrapper/_pvt_struct_v3.cpp:1431:6: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        {"size", (getter)s_get_size, (setter)NULL, "struct size in bytes", NULL},
         ^
    src/wrapper/_pvt_struct_v3.cpp:1431:48: warning: conversion from string literal to 'char *' is deprecated [-Wc++11-compat-deprecated-writable-strings]
        {"size", (getter)s_get_size, (setter)NULL, "struct size in bytes", NULL},
                                                   ^
    src/wrapper/_pvt_struct_v3.cpp:1720:1: warning: duplicate 'extern' declaration specifier [-Wduplicate-decl-specifier]
    PyMODINIT_FUNC
    ^
    /Users/hnakamur/.anyenv/envs/pyenv/versions/3.4.3/include/python3.4m/pyport.h:778:39: note: expanded from macro 'PyMODINIT_FUNC'
    #               define PyMODINIT_FUNC extern "C" PyObject*
                                          ^
    10 warnings generated.
```

## PyCUDAのサンプルを試す

[Tutorial — PyCUDA 2015.1.2 documentation](http://documen.tician.de/pycuda/tutorial.html)と[Windows7 64bitにPyCUDAとTheanoをインストールしてGPU計算する - Qiita](http://qiita.com/masato/items/713fa8876e50a65d575c)の[テスト](http://qiita.com/masato/items/713fa8876e50a65d575c#%E3%83%86%E3%82%B9%E3%83%88)を参考にして、以下の内容で `pycuda-test.py` を作って実行してみました。

Python 3.xを使っているので `print` の引数は括弧で囲むように書き換えています。

```
import pycuda.gpuarray as gpuarray
import pycuda.driver as cuda
import pycuda.autoinit
import numpy

a_gpu = gpuarray.to_gpu(numpy.random.randn(4,4).astype(numpy.float32))
a_doubled = (2*a_gpu).get()
print(a_doubled)
print(a_gpu)
```

実行してみると、以下のように出力されPyCUDAが無事動きました！

```
(venv) $ python pycuda-test.py
[[-0.72795004 -0.16994514  0.02276878 -1.07509565]
 [ 0.20851769  2.08421874 -0.51877511 -1.27585149]
 [ 0.29300559 -0.40393201  3.15332532 -1.90199065]
 [ 2.87024021  0.64773476  2.65404892 -2.97092891]]
[[-0.36397502 -0.08497257  0.01138439 -0.53754783]
 [ 0.10425884  1.04210937 -0.25938755 -0.63792574]
 [ 0.14650279 -0.201966    1.57666266 -0.95099533]
 [ 1.43512011  0.32386738  1.32702446 -1.48546445]]
```
