+++
Categories = []
Description = ""
Tags = ["ansible","python"]
date = "2016-07-01T22:44:12+09:00"
title = "lxd_containerというAnsibleモジュールを書いたときに学んだtips"

+++
## はじめに
lxd_containerというAnsibleのモジュールを書いたときに学んだtipsのメモです。

## モジュールでデバッグ出力は出来ないのでデバッグ情報は戻り値のJSONに入れる

[ansible-dev MLでの投稿](https://groups.google.com/d/msg/ansible-devel/s0iSb7phnqY/UB9vaLFJAwAJ)によるとモジュールは何も出力できないとのことなので、デバッグ情報は戻り値のJSONに入れる必要があります。

Ansible 2.1からはAnsibleModuleクラスでは `_verbosity`、それ以外では `_ansible_verbosity` で `-v`, `-vv`, `-vvv`, `-vvvv` を指定した場合の `v` の個数が取得できるので、それに応じて戻り値のJSONにデバッグ情報を含めるかどうか制御することが出来ます。値は `-v` を指定しない場合は 0 で、 `-vvvv` だと4という感じです。

## コードフォーマットのチェック

[Ansibleのコミッタの方からのコメント](https://github.com/ansible/ansible-modules-extras/pull/2208#discussion_r62996064) で `pep8` というツールでコードフォーマットのチェックを行っているということを知りました。

```
pep8 -r --ignore=E501,E221,W291,W391,E302,E251,E203,W293,E231,E303,E201,E225,E261,E241,E402 *.py
```

という感じで使います。 pep8はUbuntu 16.04 では `sudo apt install pep8` でインストールできました。


## Ansibleモジュールのチェック

[ansible/ansible-modules-extras](https://github.com/ansible/ansible-modules-extras) にプルリクエストを送ると Travis CI でチェックが走るのですが、そのチェックの1つで `ansible-validate-modules` というコマンドが使われていました。

いろいろチェックしているようなのですが、例えばモジュール内にYAMLで書いたドキュメントの書式が間違っていると `ansible-validate-modules` エラーになりました。コミットをプッシュしてからエラーになると面倒なのでローカルで先にチェックしておくのが良いです。

私はPythonのvirtualenv環境内で `pip install ansible-testing` でインストールしました。

```
ansible-validate-modules 対象ディレクトリ
```

でチェックできます。


## サードパーティのrequestsを使うとansible.module_utils.urlsを使うべきというエラーが出る

[Requests: HTTP for Humans](http://docs.python-requests.org/en/master/)を使っているとansible-validate-modulesが `ansible.module_utils.urls` を使うべきという[エラーを出してきます](https://github.com/ansible/ansible-modules-extras/pull/2208#issuecomment-228027653)。

今回書いたlxd_containerモジュールは[LXD REST API](https://github.com/lxc/lxd/blob/master/doc/rest-api.md)を使うのですが (1) Unixドメインソケットでの通信、(2) クライアント証明書を使ったhttps通信の2つが必要です。が `ansible.module_utils.urls` での実現方法がわからなかったので、今回はPython2標準ライブラリのhttplibを使って実装しました。

サードパーティのライブラリを使わず標準ライブラリを使うことで、lxd_containerモジュールを使うときに依存するライブラリを入れる手間が発生しないので結果的には良かったと思います。
