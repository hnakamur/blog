Title: LXDコンテナでPostgreSQLの非同期リプリケーションを試してみた
Date: 2016-07-23 21:13
Category: blog
Tags: lxd, postgresql
Slug: 2016/07/23/tried-postgresql-async-replication-in-lxd-containers

[ストリーミング・レプリケーションの構築 — Let's Postgres](http://lets.postgresql.jp/documents/technical/replication/1/) と [PostgreSQL9.1ためしてみた【非同期レプリケーション編】 - ごろねこ日記](http://d.hatena.ne.jp/hiroe_orz17/20111113/1321180635) を読んで、2台のLXDコンテナを使ってPostgreSQLの非同期リプリケーションを試してみたのでメモです。

また[PostgreSQL Replication - Second Edition | PACKT Books](https://www.packtpub.com/big-data-and-business-intelligence/postgresql-replication-second-edition)が $10 と安かったので、買って非同期レプリケーションの章まで読みました。

手順はAnsible playbookとしてまとめました。 [hnakamur/postgresql-async-replication-example-playbook](https://github.com/hnakamur/postgresql-async-replication-example-playbook)

`ansible.cfg` で `ask_vault_pass = True` と指定しているので、プレイブック実行時に `Vault password: ` と聞かれます。パスワードは `password` です。サンプルなので単純なパスワードにしていますが、実案件でのプレイブックはきちんとしたパスワードをつけています。

## テスト環境構築

ホストマシンのディストリビューションはUbuntu 16.04でLXD 2.0.3, curl, jqをインストール済みの状態で試しました。

作業ディレクトリを作って、そこに移動し上記のプレイブックを取得します。

```
git clone https://github.com/hnakamur/postgresql-async-replication-example-playbook
cd postgresql-async-replication-example-playbook
```

`lxd_container` モジュールを使うため、 github から最新のAnsibleをインストールします。

```
virtualenv venv
source venv/bin/activate
pip install git+https://github.com/ansible/ansible
```

## masterとstandbyのコンテナを作成

```
ansible-playbook launch_containers.yml
```

実行すると `development` というインベントリファイルを生成します。初期状態ではコンテナ `pgsql1` が master, コンテナ `pgsql2` が standby になります。

```
[development]
pgsql1 postgresql_peer_ipaddr=10.155.92.234 postgressql_master_standby_type=master
pgsql2 postgresql_peer_ipaddr=10.155.92.202 postgressql_master_standby_type=standby

[development:vars]
ansible_connection=lxd
```

## コンテナ内にPostgreSQLの非同期レプリケーションの環境設定

以下のコマンドを実行してセットアップを実行します。

```
ansible-playbook initial_setup.yml
```

完了したら、2つ端末を開いて片方で

```
lxc exec pgsql1 bash
sudo -u postgres -i
```

を実行し、もう片方で

```
lxc exec pgsql2 bash
sudo -u postgres -i
```

を実行し、データベースを作ったり pgbench を動かしたりして変更が同期されるのを確認します。

test というデータベースを作ってpgbenchを実行する手順は以下の通りです。

```
createdb test
/usr/pgsql-9.5/bin/pgbench -i test
/usr/pgsql-9.5/bin/pgbench -T 180 test
```

上記の手順を1歩ずつ試し、 test データベースを作る前は pgsql2 では `psql test` が失敗しますが作った後は成功するなどで同期が確認できます。

## レプリケーションの状態確認

### master側での確認

以下のコマンドを実行します。

```
watch -n 0.5 'psql -x -c "SELECT * FROM pg_stat_replication"'
```

こんな感じで確認できます。

```
Every 0.5s: psql -x -c "SELECT * FROM pg_stat_replication"         Sat Jul 23 12:47:27 2016

-[ RECORD 1 ]----+------------------------------
pid              | 2160
usesysid         | 16384
usename          | repl_user
application_name | walreceiver
client_addr      | 10.155.92.234
client_hostname  |
client_port      | 44822
backend_start    | 2016-07-23 08:34:43.696331+00
backend_xmin     |
state            | streaming
sent_location    | 0/30031E0
write_location   | 0/30031E0
flush_location   | 0/30031E0
replay_location  | 0/30031E0
sync_priority    | 0
sync_state       | async
```

### standby側での確認

以下のコマンドを実行します。

```
watch -n 0.5 'ps auxww | grep "[p]ostgres:"'
```

こんな感じで確認できます。

```
Every 0.5s: ps auxww | grep "[p]ostgres:"                                   Sat Jul 23 12:49:30 2016
ailabl
postgres  2051  0.0  0.0  86736  3420 ?        Ss   08:34   0:00 postgres: logger process
postgres  2052  0.0  0.0 233948  5996 ?        Ss   08:34   0:00 postgres: startup process   recover
ing 000000010000000000000003
postgres  2071  0.0  0.0 234012  7016 ?        Ss   08:34   0:00 postgres: checkpointer process
postgres  2072  0.0  0.0 233912  5916 ?        Ss   08:34   0:00 postgres: writer processl
postgres  2073  0.0  0.0  88856  3444 ?        Ss   08:34   0:00 postgres: stats collector process

postgres  2078  0.0  0.0 240632  7016 ?        Ss   08:34   0:05 postgres: wal receiver process   st
reaming 0/30031E0
```

## フェイルオーバー

masterのPostgreSQLを停止し、 standbyをmasterにpromote (昇格)させます。

```
ansible-playbook failover.yml
```

## 旧masterを新standbyとして稼働再開

ここでインベントリファイル `development` 内の `postgressql_master_standby_type` 変数の `master` と `standby` を入れ替えます。

その後、新standbyのPostgreSQLを起動します。

```
ansible-playbook start_new_standby.yml
```

もし復旧できない自体になった場合は、今のstandbyであるpgsql1 のデータディレクトリを退避して一からリプリケーション環境を構築します。

```
lxc exec pgsql1 -- mv /var/lib/pgsql/9.5/data /var/lib/pgsql/9.5/data.bak
ansible-playbook initial_setup.yml
```

## フェイルバック

masterとstandbyを入れ替えているので、フェイルバックの手順はフェイルオーバーと同じです。

```
ansible-playbook failover.yml
```

## コンテナの削除

```
ansible-playbook delete_containers.yml
```

## Ansible vaultを使う際の変数命名規則のtips

`ansible-vault encrypt` で暗号化したファイルの内容を確認するには `ansible-vault decrypt` で復号化する必要があります。どんな変数があったかを確認する度に行うのは面倒なので、以下のように暗号化するファイル内で定義する変数を一旦別の変数で受け取ってplaybookではそれを参照するようにしました。

playbookの構成として環境ごとに development, production のようにグループを分けるようにしています（このサンプルでは development だけです）。暗号化するファイルとしないファイルを以下のような配置で作っています。

```
group_vars/development/secrets.yml
group_vars/development/vars.yml
```

`group_vars/development/secrets.yml` では

```
development:
  secrets:
    postgresql_replication_password: _YOUR_PASSWORD_HERE_
```

のように定義します。


`group_vars/development/vars.yml` では

```
postgresql_replication_password: "{{ development.secrets.postgresql_replication_password }}"
```

のようにその変数を参照するようにするという具合です。


## おわりに

LXDを使えば複数サーバ構成のテスト環境も簡単に作れてとても便利です！
