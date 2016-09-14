+++
Categories = []
Description = ""
Tags = []
date = "2016-09-15T06:28:34+09:00"
title = "pgpool-IIを使ってPostgreSQLのアクティブ・スタンバイ(1+1構成)を試してみた"

+++
## はじめに
pgool-IIを使ってPostgreSQLのアクティブ・スタンバイ(1+1構成)を試したのでメモです。

以下のページを参考にしました。

* [pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html)
* [pgpool-II watchdog チュートリアル（master-slave mode）](http://www.pgpool.net/pgpool-web/contrib_docs/watchdog_master_slave_3.3/ja.html)
* [pgpool-II 3.3 の watchdog 機能 — Let's Postgres](http://lets.postgresql.jp/documents/technical/pgpool-II-3.3-watchdog/1)

## テスト用のAnsible playbook

https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook に置きました。

LXD をセットアップ済みの Ubuntu 16.04 上で試しました。

LXD で CentOS 7 のコンテナを2つ作って環境構築しています。
PostgreSQL と pgpool-II は [PostgreSQL RPM Repository (with Yum)](http://yum.postgresql.org/repopackages.php) からインストールしました。
PostgreSQL のバージョンは 9.5.4、 pgpool-II のバージョンは 3.5.4 です。


## 今回の構成

[pgpool-II watchdog チュートリアル（master-slave mode）](http://www.pgpool.net/pgpool-web/contrib_docs/watchdog_master_slave_3.3/ja.html) の図と同様の構成となっています。

ただし、今回の構成では pgpool-II と PostgreSQL を別のコンテナにせず1つのコンテナに同居させていて、以下の2つのコンテナで構成しています。

* pgsql1 (IPアドレス `10.155.92.101`)
* pgsql2 (IPアドレス `10.155.92.102`)

pgpool-II は watchdog で相互監視するマスタ・スタンバイ構成 (
[pgpool-II の設定](http://www.pgpool.net/docs/latest/pgpool-ja.html#config) のマスタスレーブモード ) です。
pgpool-II のマスタが仮想 IP `10.155.92.100` を持ちます。

レプリケーションは pgpool-II ではなく PostgreSQL の非同期ストリーミング・レプリケーションを使っています。

また、 pgpool-II の負荷分散 (ロードバランサ) 機能は今回は使っていません。

なお、仮想 IP はあくまで pgpool-II のマスタと連動するもので、 PostgreSQL のプライマリとは別のコンテナになることもあります。

pgpool-II のドキュメントやコマンドの出力を見ると、 pgpool-II のマスタはマスタ、 PostgreSQL のマスタはプライマリと用語を使い分けているようです。この記事もそれに従います。

pgpool-II と PostgreSQL のポートはそれぞれデフォルトの 9999 と 5432 としています。
pgpool-II は他に管理用のポートとして 9898、 watchdog 用のポートで 9000 を使います。

## セットアップの事前準備

[Pacemakerを使ってPostgreSQLのアクティブ・スタンバイ(1+1構成)を試してみた · hnakamur's blog at github](/blog/2016/08/21/experiment-postgresql-active-standby-cluster-using-pacemaker/) と同様です。


## pgpool-II の管理者ユーザとパスワード

[pcp.conf の設定](http://www.pgpool.net/docs/latest/pgpool-ja.html#pcp_config) に従って pgpool-II の管理者のユーザ名と md5 暗号化したパスワードを `/etc/pgpool-II-95/pcp.conf` に設定しています。

管理者ユーザ名は `pgpool2` としました。

パスワードは以下のコマンドを実行して `group_vars/development/secrets.yml` を復号化し、 `development.secrets.pgpool2_admin_password` の値を参照してください。

```
$ ansible-vault decrypt group_vars/development/secrets.yml 
Vault password: 
Decryption successful
```

## コンテナの作成

以下のコマンドを実行して `pgsql1` と `pgsql2` という2つのコンテナを作成します。

```
$ ansible-playbook launch_containers.yml -D -v
```

vaultのパスワードを聞かれますので入力してください。

## コンテナ内に PostgreSQL と pgpool-II をセットアップ

以下のコマンドを実行して、コンテナ内に PostgreSQL と pgpool-II をセットアップします。

```
$ ansible-playbook setup_containers.yml -D -v
```


セットアップが完了したときの初期状態では `pgsql1` の pgpool-II がマスタで仮想IPを持ち、 PostgreSQL も `pgsql1` がプライマリとなっています。

## PostgreSQL のプロセス確認

起動してしばらく経ってから `pgsql1` コンテナの PostgreSQL プロセスを ps で見ると以下のようになります。

```
[root@pgsql1 ~]# ps axf | grep [p]ostgres
 1464 ?        S      0:00 /usr/pgsql-9.5/bin/postgres -D /var/lib/pgsql/9.5/data
 1465 ?        Ss     0:00  \_ postgres: logger process   
 1467 ?        Ss     0:00  \_ postgres: checkpointer process   
 1468 ?        Ss     0:00  \_ postgres: writer process   
 1469 ?        Ss     0:00  \_ postgres: wal writer process   
 1470 ?        Ss     0:00  \_ postgres: autovacuum launcher process   
 1471 ?        Ss     0:00  \_ postgres: archiver process   last was 000000010000000000000002.00000028.backup
 1472 ?        Ss     0:00  \_ postgres: stats collector process   
 1720 ?        Ss     0:00  \_ postgres: wal sender process repl_user 10.155.92.102(43074) streaming 0/3000060
```

`pgsql2` ではこうなります。

```
[root@pgsql2 ~]# ps axf | grep [p]ostgres
 1386 ?        S      0:00 /usr/pgsql-9.5/bin/postgres -D /var/lib/pgsql/9.5/data
 1387 ?        Ss     0:00  \_ postgres: logger process   
 1388 ?        Ss     0:00  \_ postgres: startup process   recovering 000000010000000000000003
 1394 ?        Ss     0:00  \_ postgres: checkpointer process   
 1395 ?        Ss     0:00  \_ postgres: writer process   
 1396 ?        Ss     0:00  \_ postgres: stats collector process   
 1399 ?        Ss     0:00  \_ postgres: wal receiver process   streaming 0/3000060
```

`postgres: wal sender` のプロセスがあれば PostgreSQL のプライマリ、 `postgres: wal receiver` のプロセスがあれば PostgreSQL のスタンバイと判断することが出来ます。


ただし、PostgreSQL のプライマリが切り替わってしばらくの間はこのプロセスは存在しないので、 [PostgreSQLのマスタ判断 - Marlock Homes Diary](http://tyawan080.hatenablog.com/entry/2014/05/12/234226) の方法を使います。
`select pg_is_in_recovery()` を実行して `f` であればプライマリ、 `t` であればスタンバイです。

```
[root@pgsql1 ~]# sudo -i -u postgres psql -c "select pg_is_in_recovery()"
 pg_is_in_recovery 
-------------------
 f
(1 row)
```

```
[root@pgsql2 ~]# sudo -i -u postgres psql -c "select pg_is_in_recovery()"
 pg_is_in_recovery 
-------------------
 t
(1 row)
```

## pgpool-II から見た PostgreSQL ノードの状態確認

どちらかのコンテナで以下のコマンドを実行します。

```
[root@pgsql1 ~]# sudo -i -u postgres psql -h localhost -p 9999 -c "show pool_nodes"
 node_id |   hostname    | port | status | lb_weight |  role   | select_cnt 
---------+---------------+------+--------+-----------+---------+------------
 0       | 10.155.92.101 | 5432 | 2      | 0.500000  | primary | 0
 1       | 10.155.92.102 | 5432 | 2      | 0.500000  | standby | 0
(2 rows)
```

なお、 今回の設定では `postgres` ユーザのパスワードを `/var/lib/pgsql/.pgpass` に書いているのでパスワード入力は不要です。実運用時は書かないほうが良いです。

`role` 列の primary か standby で PostgreSQL のプライマリかスタンバイもわかるようですが、切替時はすぐに更新されなかったことがあったような気がします。

切り替え直後は `select pg_is_in_recovery()` を実行する方式のほうが良さそうです。

status 列の値については [pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [pcp_node_info](http://www.pgpool.net/docs/latest/pgpool-ja.html#pcp_node_info) に説明があります。

## プライマリの PostgreSQL を強制停止してフェールオーバーのテスト


