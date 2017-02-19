Title: AnsibleのLXDコネクションプラグインを試してみた
Date: 2016-05-07 20:32
Category: blog
Tags: lxd, ansible
Slug: 2016/05/07/tried-ansible-lxd-connection-plugin

LXDを使うとなるとAnsibleのLXDコネクションプラグインが欲しいなと思って[ansible/ansibleのgithubのレポジトリ](https://github.com/ansible/ansible)を眺めていたら [lib/ansible/plugins/connection/lxd.py](https://github.com/ansible/ansible/blob/fca5ba153e9258d6a9a28c418d8339d507eee81c/lib/ansible/plugins/connection/lxd.py) に既に作られていることに気付きました。

ソースを見ると `lxc` コマンドを使った実装になっていました。aptでインストールしたansible 2.0.0.2にこのファイルだけ追加して使えないか試してみたのですが、 `AttributeError: 'PlayContext' object has no attribute 'executable'` というエラーが出て使えませんでした。

そこでvirtualenvで環境を作ってpipでgithubのmasterのansibleをインストールして試してみました。

## インストール手順

インストール手順は以下の通りです。
まず、virtualenv環境でAnsibleをインストールするのに必要なパッケージをインストールします。

```
sudo apt update
sudo apt install -y virtualenv build-essential python-dev libffi-dev libssl-dev
```

作業ディレクトリを作ってそこに移動し、virtualenvで環境を作ってansibleをインストールします。

```
mkdir ~/ansible-lxd-example
cd ~/ansible-lxd-example
virtualenv venv
. venv/bin/activate
pip install git+https://github.com/ansible/ansible
```

## 使ってみる

以下のような設定ファイルとテスト用のプレイブックを作りました。

```
$ cat ansible.cfg
[defaults]
inventory = hosts
$ cat hosts
[containers]
cent01 ansible_connection=lxd
cent02 ansible_connection=lxd
$ cat test.yml
---
- hosts: containers
  remote_user: root
  tasks:
    - debug: msg=ipv4_address={{ ansible_default_ipv4.address }}
```

実行してみると、問題なく動作しました。

```
$ ansible-playbook test.yml

PLAY [containers] **************************************************************

TASK [setup] *******************************************************************
ok: [cent01]
ok: [cent02]

TASK [debug] *******************************************************************
ok: [cent01] => {
    "msg": "ipv4_address=10.155.92.101"
}
ok: [cent02] => {
    "msg": "ipv4_address=10.155.92.103"
}

PLAY RECAP *********************************************************************
cent01                     : ok=2    changed=0    unreachable=0    failed=0
cent02                     : ok=2    changed=0    unreachable=0    failed=0

```
