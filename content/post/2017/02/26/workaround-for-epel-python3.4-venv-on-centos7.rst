CentOS 7のepelでインストールしたpython3.4でvenvを使うとエラーになる件の回避策
#############################################################################

:date: 2017-02-25 00:45
:tags: centos, python, venv
:category: blog
:slug: 2017/02/26/workaround-for-epel-python3.4-venv-on-centos7

はじめに
--------

CentOS 7のpythonパッケージは2.7.xなので、3系を使うには別途インストールする必要があります。
EPELの ``python34`` パッケージを使うと ``python3 -m venv venv`` でエラーになるという問題が起きたのですが、 `Floating Octothorpe: Python3, CentOS and pip <https://f-o.org.uk/2016/python3-centos-and-pip.html>`_ の記事で解決したのでメモです。

IUS Community Repo のPython 3.6.x
---------------------------------

`AdditionalResources/Repositories - CentOS Wiki <https://wiki.centos.org/AdditionalResources/Repositories>`_ の `IUS Community Repo <https://ius.io/>`_ なら ``python36u`` というパッケージ名でPython 3.6.xがインストールできます。
`IUS Community Project Packages <https://github.com/iuscommunity-pkg?utf8=%E2%9C%93&q=python36u&type=&language=>`_ を見ると他に ``python36u-setuptools``, ``uwsgi-plugin-python36u``, ``python36u-pip``, ``python36u-lxml``, ``python36u-psycopg2`` パッケージが提供されています。

こちらは ``python3.6 -m venv venv`` で問題なくvirtualenv環境が作成できました。

Extra Packages for Enterprise Linux (EPEL)のPython 3.4.x
--------------------------------------------------------

EPELでも ``python34`` というパッケージ名でPython 3.4.xがインストールできます。 IUS Community Repoの3.6.xよりは古いですが、 ``python34-*`` のパッケージはこちらのほうが多いです（とは言え ``venv`` を使うのであればあまり関係無いとも言えますが）。
また、EPELは他でも使うので私は常に有効にしています。
サードパーティのレポジトリの種類はなるべく限定しておきたいと考えるとIUS Community Repoは使わずにEPELの ``python34`` を使うという選択肢もありえます。

EPELのPython 3.4でvenvを使うとエラー
------------------------------------

``python3.4 -m venv venv`` を実行すると以下のようなエラーが出ました（ここでは ``/home/admin/blog`` というディレクトリで実行しました）。

.. code-block:: console

    $ python3.4 -m venv venv
    Error: Command '['/home/admin/blog/venv/bin/python3.4', '-Im', 'ensurepip', '--upgrade', '--default-pip']' returned non-zero exit status 1

エラーになったコマンドを直接実行すると ``/usr/lib64/python3.4/ensurepip/_bundled/setuptools-20.10.1-py2.py3-none-any.whl`` というファイルが無くてエラーになっていることがわかります。

.. code-block:: console

    $ /home/admin/blog/venv/bin/python3.4 -Im ensurepip --upgrade --default-pip
    Traceback (most recent call last):
      File "/usr/lib64/python3.4/runpy.py", line 170, in _run_module_as_main
        "__main__", mod_spec)
      File "/usr/lib64/python3.4/runpy.py", line 85, in _run_code
        exec(code, run_globals)
      File "/usr/lib64/python3.4/ensurepip/__main__.py", line 4, in <module>
        ensurepip._main()
      File "/usr/lib64/python3.4/ensurepip/__init__.py", line 209, in _main
        default_pip=args.default_pip,
      File "/usr/lib64/python3.4/ensurepip/__init__.py", line 98, in bootstrap
        "_bundled/{}".format(wheel_name),
      File "/usr/lib64/python3.4/pkgutil.py", line 629, in get_data
        return loader.get_data(resource_name)
      File "<frozen importlib._bootstrap>", line 1623, in get_data
    FileNotFoundError: [Errno 2] No such file or directory: '/usr/lib64/python3.4/ensurepip/_bundled/setuptools-20.10.1-py2.py3-none-any.whl'

この問題は
`Bug 1263057 – pyvenv3.4 doesn't work without pip <https://bugzilla.redhat.com/show_bug.cgi?id=1263057>`_
に報告されています。

EPELのPython 3.4でvenvを使うための回避策
----------------------------------------

EPELのインストールからのコマンドをまとめると以下のようになります。

.. code-block:: console

    sudo yum install epel-release
    sudo yum install python34 python34-setuptools python34-pip
    sudo mkdir -p /usr/lib64/python3.4/ensurepip/_bundled
    sudo curl -o /usr/lib64/python3.4/ensurepip/_bundled/setuptools-20.10.1-py2.py3-none-any.whl \
        https://pypi.python.org/packages/c5/e2/72d706eeda837564b9fecdc8b2bf48b33467ae928ed05d4ac157463c90fb/setuptools-20.10.1-py2.py3-none-any.whl
    sudo curl -o /usr/lib64/python3.4/ensurepip/_bundled/pip-8.1.1-py2.py3-none-any.whl \
        https://pypi.python.org/packages/31/6a/0f19a7edef6c8e5065f4346137cc2a08e22e141942d66af2e1e72d851462/pip-8.1.1-py2.py3-none-any.whl

`Floating Octothorpe: Python3, CentOS and pip <https://f-o.org.uk/2016/python3-centos-and-pip.html>`_ に詳しく書かれていますが、
上記の ``setuptools`` と ``pip`` のバージョンは ``/usr/lib64/python3.4/ensurepip/__init__.py`` に書いてあるバージョンに一致させる必要があります。

.. code-block:: python
    :linenos: table
    :linenostart: 11

    _SETUPTOOLS_VERSION = "20.10.1"

    _PIP_VERSION = "8.1.1"

