Title: pgpool-IIを使ってPostgreSQLのアクティブ・スタンバイ(1+1構成)を試してみた
Date: 2016-09-15 06:28
Category: blog
Slug: 2016/09/15/experiment-postgresql-active-standby-using-pgpool-ii

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

pgpool-II から PostgreSQL を監視するのは heartbeat という仕組みを今回は使っています。

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

## 状態確認のコマンド説明

### PostgreSQL のプロセス確認

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

ただし、PostgreSQL のプライマリが切り替わってしばらくの間はこのプロセスは存在しないので、 次項の方法を使います。

### pgpool-II から見た PostgreSQL ノードの状態確認

[PostgreSQLのマスタ判断 - Marlock Homes Diary](http://tyawan080.hatenablog.com/entry/2014/05/12/234226) で知りました。

`select pg_is_in_recovery()` を実行して `t` であればスタンバイ、 `f` であればプライマリかスタンドアロンです。

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

### pgpool-II から見た PostgreSQL ノードの状態確認

[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [SHOWコマンド](http://www.pgpool.net/docs/latest/pgpool-ja.html#show-commands) の [pool_nodes](http://www.pgpool.net/docs/latest/pgpool-ja.html#pool_nodes) に対応します。

どちらかのコンテナで以下のコマンドを実行します。

```
[root@pgsql1 ~]# sudo -i -u postgres psql -h localhost -p 9999 -c "show pool_nodes"
 node_id |   hostname    | port | status | lb_weight |  role   | select_cnt 
---------+---------------+------+--------+-----------+---------+------------
 0       | 10.155.92.101 | 5432 | 2      | 0.500000  | primary | 0
 1       | 10.155.92.102 | 5432 | 2      | 0.500000  | standby | 0
(2 rows)
```

なお、 今回の設定では `postgres` ユーザのパスワードを `/var/lib/pgsql/.pgpass` に書いているのでパスワード入力は不要です。実運用時は書かないほうが良いでしょう。

`role` 列の primary か standby で PostgreSQL のプライマリかスタンバイもわかるようですが、切替時はすぐに更新されなかったことがあったような気がします。

切り替え直後は `select pg_is_in_recovery()` を実行する方式のほうが良さそうです。

status 列の値については [pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [pcp_node_info](http://www.pgpool.net/docs/latest/pgpool-ja.html#pcp_node_info) に説明があります。

* 0 - 初期化時のみに表われる。PCP コマンドで表示されることはない。
* 1 - ノード稼働中。接続無し
* 2 - ノード稼働中。接続有り
* 3 - ノードダウン

### watchdog から見た pgpool-II の状態確認

[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [pcp_watchdog_info](http://www.pgpool.net/docs/latest/pgpool-ja.html#pcp_watchdog_info) に対応します。

以下のコマンドを実行します。 pgpool-II の管理者 `pgpool2` のパスワードを聞かれますので入力してください。

```
[root@pgsql1 ~]# sudo -i -u postgres /usr/pgpool-9.5/bin/pcp_watchdog_info -h localhost -U pgpool2 -v
Password: 
Watchdog Cluster Information 
Total Nodes          : 2
Remote Nodes         : 1
Quorum state         : QUORUM EXIST
Alive Remote Nodes   : 1
VIP up on local node : YES
Master Node Name     : Linux_pgsql1_9999
Master Host Name     : 10.155.92.101

Watchdog Node Information 
Node Name      : Linux_pgsql1_9999
Host Name      : 10.155.92.101
Delegate IP    : 10.155.92.100
Pgpool port    : 9999
Watchdog port  : 9000
Node priority  : 1
Status         : 4
Status Name    : MASTER

Node Name      : Linux_pgsql2_9999
Host Name      : 10.155.92.102
Delegate IP    : 10.155.92.100
Pgpool port    : 9999
Watchdog port  : 9000
Node priority  : 1
Status         : 7
Status Name    : STANDBY

```

`Status Name` の種類は src/watchdog/watchdog.c 内にで定義されていました。 `Status` はこの配列内のゼロオリジンのインデクスです。

```
char *wd_state_names[] = {
        "DEAD",
        "LOADING",
        "JOINING",
        "INITIALIZING",
        "MASTER",
        "PARTICIPATING IN ELECTION",
        "STANDING FOR MASTER",
        "STANDBY",
        "LOST",
        "IN NETWORK TROUBLE",
        "SHUTDOWN",
        "ADD MESSAGE SENT"};
```

## pgsql1 (プライマリ)の PostgreSQL を強制停止してフェイルオーバーのテスト

### フェイルオーバー時に呼び出されるスクリプト

[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [Streaming Replicationでのフェイルオーバ](http://www.pgpool.net/docs/latest/pgpool-ja.html#failover_in_stream_mode) に対応します。

フェイルオーバー時には `/etc/pgpool-II-95/pgpool.conf` の `failover_command` に設定したスクリプトが実行されます。今回の構成では以下のような設定にしました。

```
failover_command = '/var/lib/pgsql/9.5/data/pgpool_failover %d %P %H %R'
                   # NOTE: %dなどの値は src/main/pgpool_main.c の trigger_failover_command で設定しています。
                   # Executes this command at failover
                   # Special values:
                   #   %d = node id
                   #   %h = host name
                   #   %p = port number
                   #   %D = database cluster path
                   #   %m = new master node id
                   #   %H = hostname of the new master node
                   #   %M = old master node id
                   #   %P = old primary node id
                   #   %r = new master port number
                   #   %R = new master database cluster path
                   #   %% = '%' character
```

`/var/lib/pgsql/9.5/data/pgpool_failover` は [roles/postgresql_db/templates/pgpool_failover.j2](https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook/blob/7f3ef8af54a4f9ec948d65bfc47e33db4792737d/roles/postgresql_db/templates/pgpool_failover.j2) から Ansible の template モジュールで生成しています。

### フェイルオーバーの実行

実行後にどう動いたか確認できるように `logger` コマンドでログを出力するようにしています。 `journalctl -f` でログを `tail -f` 的な感じで見られるので、これで見ながら実行します。

初期状態では pgsql1 が PostgreSQL のプライマリになっています。

pgsql2 で以下のコマンドを実行します。

```
[root@pgsql2 ~]# journalctl -f | grep pgpool_failover
```

pgsql1 で以下のコマンドを実行しバックグラウンド ( `&` は 1つ) で PostgreSQL を強制停止しつつ、 journald のログを表示します。

```
[root@pgsql1 ~]# sudo -i -u postgres /usr/pgsql-9.5/bin/pg_ctl stop -m immediate -D /var/lib/pgsql/9.5/data & journalctl -f | grep pgpool_failover
```

何回か試してみたのですが、 `/var/lib/pgsql/9.5/data/pgpool_failover` は pgsql1 で実行される場合と pgsql2 で実行される場合があり、どうやらランダムにどちらか一方で実行されるということのようです。また今回の構成では root ユーザで実行されました。

以下は pgsql1 での出力結果です。
Ctrl-C で `journalctl -f` を停止します。

```
[1] 2319
waiting for server to shut down.... done
server stopped

^C
[1]+  Done                  sudo -i -u postgres /usr/pgsql-9.5/bin/pg_ctl stop -m immediate -D /var/lib/pgsql/9.5/data
```

以下は pgsql2 での出力結果です。
Ctrl-C で `journalctl -f` を停止します。

```
Sep 15 13:06:47 pgsql2 pgpool[1432]: 2016-09-15 13:06:47: pid 1432: LOG:  execute command: /var/lib/pgsql/9.5/data/pgpool_failover 0 0 10.155.92.102 /var/lib/pgsql/9.5/data
Sep 15 13:06:47 pgsql2 pgpool_failover[32612]: start args=0 0 10.155.92.102 /var/lib/pgsql/9.5/data UID=0
Sep 15 13:06:47 pgsql2 pgpool_failover[32620]: created promote_trigger file
^C
```

少ししてから PostgreSQL のノードの状態を確認すると以下のようになりました。
pgsql2 (10.155.92.102) の role が primary になり、 pgsql1 (10.155.92.101) は
role が standby で status が `3` (ノードダウン) になっています。

```
[root@pgsql2 ~]# sudo -i -u postgres psql -h localhost -p 9999 -c "show pool_nodes"
 node_id |   hostname    | port | status | lb_weight |  role   | select_cnt 
---------+---------------+------+--------+-----------+---------+------------
 0       | 10.155.92.101 | 5432 | 3      | 0.500000  | standby | 0
 1       | 10.155.92.102 | 5432 | 2      | 0.500000  | primary | 0
(2 rows)
```

pgsql2 で `select pg_is_in_recovery()` を実行すると `f` になってプライマリになっていることがわかります。

```
[root@pgsql2 pgsql]# sudo -i -u postgres psql -c "select pg_is_in_recovery()"
 pg_is_in_recovery 
-------------------
 f
(1 row)
```

pgsql2 側での変更実験としてデータベースを作成してみます。

```
[root@pgsql2 ~]# sudo -i -u postgres createdb foo
[root@pgsql2 ~]# sudo -i -u postgres psql -l
                             List of databases
   Name    |  Owner   | Encoding | Collate | Ctype |   Access privileges   
-----------+----------+----------+---------+-------+-----------------------
 foo       | postgres | UTF8     | C       | C     | 
 postgres  | postgres | UTF8     | C       | C     | 
 template0 | postgres | UTF8     | C       | C     | =c/postgres          +
           |          |          |         |       | postgres=CTc/postgres
 template1 | postgres | UTF8     | C       | C     | =c/postgres          +
           |          |          |         |       | postgres=CTc/postgres
(4 rows)
```

なお、 pgpool-II 自体のマスタ・スタンバイの役割は変わらず同じで、 pgsql1 がマスタ、 pgsql2 がスタンバイで、 仮想IP は pgsql1 についた状態です。

## pgsql1 の PostgreSQL をオンラインリカバリしスタンバイとして復帰させる

### オンラインリカバリで呼び出される2つのスクリプト

[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [Streaming Replicationでのオンラインリカバリ](http://www.pgpool.net/docs/latest/pgpool-ja.html#online_recovery_in_stream_mode) に対応します。

オンラインリカバリで呼び出されるスクリプトは2つあります。この2つのスクリプトは `failover_command` とは違って、必ずプライマリ側で `postgres` ユーザで実行されます。

1つ目は `/etc/pgpool-II-95/pgpool.conf` の `recovery_1st_stage_command` に指定したスクリプトです。
ここではファイル名のみが指定可能で、ディレクトリは PostgreSQL のデータディレクトリ (今回の構成では /var/lib/pgsql/9.5/data ) と決められています。
[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [recovery_1st_stage_command](http://www.pgpool.net/docs/latest/pgpool-ja.html#RECOVERY_1ST_STAGE_COMMAND) によるとセキュリティ上の観点からそうしているそうです。

```
recovery_1st_stage_command = 'recovery_1st_stage'
```

`/var/lib/pgsql/9.5/data/recovery_1st_stage` は [roles/postgresql_db/templates/recovery_1st_stage.j2](https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook/blob/7f3ef8af54a4f9ec948d65bfc47e33db4792737d/roles/postgresql_db/templates/recovery_1st_stage.j2) から Ansible の template モジュールで生成しています。

今回の構成では古いデータディレクトリを `mv` コマンドでリネームして、 `pg_basebackup` コマンドでプライマリ・データベースの複製を作り、 `recovery.conf` を作ってスタンバイとして稼働させる準備をしています。

2つ目は PostgreSQL のデータディレクトリ下の `pgpool_remote_start` というファイル名のスクリプトです。

[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [pgpool_remote_start](http://www.pgpool.net/docs/latest/pgpool-ja.html#pool_remote_start) に説明があります。

こちらはファイル名が pgpool-II のソースコード `src/sql/pgpool-recovery/pgpool-recovery.c` 内に

```
#define REMOTE_START_FILE "pgpool_remote_start"
```

のように固定の定義になっています。

`/var/lib/pgsql/9.5/data/pgpool_remote_start` は [roles/postgresql_db/templates/pgpool_remote_start.j2](https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook/blob/7f3ef8af54a4f9ec948d65bfc47e33db4792737d/roles/postgresql_db/templates/pgpool_remote_start.j2) から Ansible の template モジュールで生成しています。

処理内容はリモートのノードの PostgreSQL を起動するというものになっています。
ファイル名は `pgpool_remote_start` なので最初見たときは `pgpool` を起動するのかと勘違いしましたが、 `pgpool_` は `pgpool` のファイルであることを示す接頭辞的な意味合いのようです。
`pgpool` を起動するなら `start_remote_pgoool` のほうがわかりやすいでしょうしね。

なお、 [pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [pgpool_remote_start](http://www.pgpool.net/docs/latest/pgpool-ja.html#pool_remote_start) で書かれているサンプルスクリプトでは `pg_ctl` コマンドで PostgreSQL を起動していますが、 `systemctl status postgresql-9.5` でサービス状態が確認できなくなってしまうため、 [roles/postgresql_db/templates/pgpool_remote_start.j2](https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook/blob/7f3ef8af54a4f9ec948d65bfc47e33db4792737d/roles/postgresql_db/templates/pgpool_remote_start.j2) では `sudo systemctl start postgresql-9.5` で起動しています。
またそのために postgres ユーザ用の sudoers 設定も [roles/postgresql/templates/sudoers_postgres.j2](https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook/blob/7f3ef8af54a4f9ec948d65bfc47e33db4792737d/roles/postgresql/templates/sudoers_postgres.j2) を元に `/etc/sudoers.d/01_postgres` を生成し行っています。

### リカバリの実行

今回は [リカバリの実行](http://www.pgpool.net/docs/latest/pgpool-ja.html#perform_online_recovery) で説明されている [pcp_recovery_node](http://www.pgpool.net/docs/latest/pgpool-ja.html#pcp_recovery_node) コマンドを使います。

`pcp_recovery_node` コマンドは pgpool-II のユーザ `pgpool2` のパスワードを入力する必要があるためフォアグラウンドで実行し ( `&` は `&&` と2つ)、ログを表示します。

`pcp_recovery_node` コマンドは pgsql1 と pgsql2 のどちらで実行しても良いようです。ここでは対象のサーバが pgsql1 なので対応する `node_id` の `0` を引数の最後に指定しています。 `node_id` は上記の `show pool_nodes` の出力で確認できます。

```
[root@pgsql2 pgsql]# sudo -i -u postgres /usr/pgpool-9.5/bin/pcp_recovery_node -h localhost -p 9898 -U pgpool2 0
Password: 
pcp_recovery_node -- Command Successful
```

ログを確認すると以下のようになっていました。

```
[root@pgsql2 pgsql]# journalctl | grep -E '(recovery_1st_stage|pgpool_remote_start)'
Sep 15 14:03:38 pgsql2 pgpool[1416]: 2016-09-15 14:03:38: pid 1700: DETAIL:  starting recovery command: "SELECT pgpool_recovery('recovery_1st_stage', '10.155.92.101', '/var/lib/pgsql/9.5/data', '5432')"
Sep 15 14:03:38 pgsql2 recovery_1st_stage[1704]: start args=/var/lib/pgsql/9.5/data 10.155.92.101 /var/lib/pgsql/9.5/data 5432 UID=26
Sep 15 14:03:39 pgsql2 recovery_1st_stage[1713]: pg_basebackup done.
Sep 15 14:03:39 pgsql2 recovery_1st_stage[1716]: created archive_status.
Sep 15 14:03:39 pgsql2 recovery_1st_stage[1719]: created recovery.conf.
Sep 15 14:03:39 pgsql2 pgpool_remote_start[1722]: start args=10.155.92.101 /var/lib/pgsql/9.5/data UID=26
Sep 15 14:03:42 pgsql2 pgpool_remote_start[1738]: finished to start postgresql service
```

しばらくして PostgreSQL の状態を確認すると以下のように pgsql1 の role が standby で status が 2 (ノード稼働中。接続有り) になりました。

```
[root@pgsql2 pgsql]# sudo -i -u postgres psql -h localhost -p 9999 -c "show pool_nodes"
 node_id |   hostname    | port | status | lb_weight |  role   | select_cnt 
---------+---------------+------+--------+-----------+---------+------------
 0       | 10.155.92.101 | 5432 | 2      | 0.500000  | standby | 0
 1       | 10.155.92.102 | 5432 | 2      | 0.500000  | primary | 0
(2 rows)
```

ps を実行してみると pgsql2 で `postgres: wal sender process` が稼働しており、 pgsql1 で `postgres: wal receiver process` が稼働しており、ストリーミング・レプリケーションが動いていることが確認できました。

## pgsql1 (スタンバイ) の PostgreSQL を強制停止してみる

### スタンバイの PostgreSQL を強制停止

pgsql2 で以下のコマンドを実行します。

```
[root@pgsql2 ~]# journalctl -f | grep pgpool_failover
```

pgsql1 で以下のコマンドを実行します。

```
[root@pgsql1 ~]# sudo -i -u postgres /usr/pgsql-9.5/bin/pg_ctl stop -m immediate -D /var/lib/pgsql/9.5/data & journalctl -f | grep pgpool_failover
```

今回は pgsql2 に以下のログが出ました。

```
Sep 15 14:21:05 pgsql2 pgpool[1416]: 2016-09-15 14:21:05: pid 1416: LOG:  execute command: /var/lib/pgsql/9.5/data/pgpool_failover 0 1 10.155.92.102 /var/lib/pgsql/9.5/data
Sep 15 14:21:05 pgsql2 pgpool_failover[2466]: start args=0 1 10.155.92.102 /var/lib/pgsql/9.5/data UID=0
Sep 15 14:21:05 pgsql2 pgpool_failover[2468]: do nothing since failed node was not primary
```

停止された PostgreSQL がプライマリではなかったのでフェイルオーバは行わず、プライマリ (pgsql2) をそのままスタンドアロンで稼働させています。

[pgpool-II ユーザマニュアル](http://www.pgpool.net/docs/latest/pgpool-ja.html) の [Streaming Replicationでのフェイルオーバ](http://www.pgpool.net/docs/latest/pgpool-ja.html#failover_in_stream_mode) に上げられているフェイルオーバ用スクリプトではノード 0 がプライマリで 1 がスタンバイという想定で書かれているため、今回の状況ではうまく行きませんでした。
が、 [roles/postgresql_db/templates/pgpool_failover.j2](https://github.com/hnakamur/postgresql-pgpool2-failover-example-playbook/blob/7f3ef8af54a4f9ec948d65bfc47e33db4792737d/roles/postgresql_db/templates/pgpool_failover.j2) では `pgpool.conf` の `failover_command` の4つの引数のうち、最初の2つに停止したノード `%d` と旧プライマリノード %P を渡していて、値が違う場合はスタンバイと判定していますので、一度フェイルオーバ→リカバリをした後でも大丈夫です。

`show pool_nodes` の実行結果は以下の通りです。

```
[root@pgsql2 pgsql]# sudo -u postgres psql -h localhost -p 9999 -c "show pool_nodes"
 node_id |   hostname    | port | status | lb_weight |  role   | select_cnt 
---------+---------------+------+--------+-----------+---------+------------
 0       | 10.155.92.101 | 5432 | 3      | 0.500000  | standby | 0
 1       | 10.155.92.102 | 5432 | 2      | 0.500000  | primary | 0
(2 rows)
```

pgsql2 で postgres のプロセスを見ると `wal sender` がいないので、スタンドアロン状態であることがわかります。

```
[root@pgsql2 pgsql]# ps axf | grep [p]ostgres
 1370 ?        S      0:00 /usr/pgsql-9.5/bin/postgres -D /var/lib/pgsql/9.5/data
 1371 ?        Ss     0:00  \_ postgres: logger process   
 1378 ?        Ss     0:00  \_ postgres: checkpointer process   
 1379 ?        Ss     0:00  \_ postgres: writer process   
 1381 ?        Ss     0:00  \_ postgres: stats collector process   
 1554 ?        Ss     0:00  \_ postgres: wal writer process   
 1555 ?        Ss     0:00  \_ postgres: autovacuum launcher process   
 1556 ?        Ss     0:00  \_ postgres: archiver process   last was 000000020000000000000004.00000060.backup
```

スタンドアロン状態であることは `select * from pg_stat_replication` の結果が 0であることからもわかります。

```
[root@pgsql2 pgsql]# sudo -i -u postgres psql -x -c "select * from pg_stat_replication"
(0 rows)
```

### スタンバイの PostgreSQL を復活させる

#### 単に PostgreSQL を起動すれば動く場合

実運用の際はデータディレクトリの状況を調査したりするところですが、ここでは問題ないという前提で、 pgsql1 で PostgreSQL を起動して pgpool-II の管理下に追加します。

```
[root@pgsql1 pgsql]# systemctl start postgresql-9.5
```

で起動し

```
[root@pgsql1 pgsql]# systemctl status postgresql-9.5
```

で状態を確認します。
Active の行が以下のように `active (running)` になっていれば OK です。

```
   Active: active (running) since Thu 2016-09-15 14:36:12 UTC; 3s ago
```

しばらくすると pgpool-II の heartbeat で pgsql1 の PostgreSQL が稼働していることを検知し、 pgsql2 をプライマリとするリプリケーションが再開されます。

```
[root@pgsql1 pgsql]# ps axf | grep [p]ostgres
 2778 ?        S      0:00 /usr/pgsql-9.5/bin/postgres -D /var/lib/pgsql/9.5/data
 2779 ?        Ss     0:00  \_ postgres: logger process   
 2780 ?        Ss     0:00  \_ postgres: startup process   recovering 000000020000000000000005
 2785 ?        Ss     0:00  \_ postgres: checkpointer process   
 2786 ?        Ss     0:00  \_ postgres: writer process   
 2787 ?        Ss     0:00  \_ postgres: stats collector process   
 2788 ?        Ss     0:00  \_ postgres: wal receiver process   streaming 0/5000680
```

```
[root@pgsql2 pgsql]# ps axf | grep [p]ostgres
 1370 ?        S      0:00 /usr/pgsql-9.5/bin/postgres -D /var/lib/pgsql/9.5/data
 1371 ?        Ss     0:00  \_ postgres: logger process   
 1378 ?        Ss     0:00  \_ postgres: checkpointer process   
 1379 ?        Ss     0:00  \_ postgres: writer process   
 1381 ?        Ss     0:00  \_ postgres: stats collector process   
 1554 ?        Ss     0:00  \_ postgres: wal writer process   
 1555 ?        Ss     0:00  \_ postgres: autovacuum launcher process   
 1556 ?        Ss     0:00  \_ postgres: archiver process   last was 000000020000000000000004.00000060.backup
 3111 ?        Ss     0:00  \_ postgres: wal sender process repl_user 10.155.92.101(57142) streaming 0/5000680
[root@pgsql2 pgsql]# sudo -i -u postgres psql -x -c "select * from pg_stat_replication"
-[ RECORD 1 ]----+------------------------------
pid              | 3111
usesysid         | 16394
usename          | repl_user
application_name | walreceiver
client_addr      | 10.155.92.101
client_hostname  | 
client_port      | 57142
backend_start    | 2016-09-15 14:36:12.312321+00
backend_xmin     | 1842
state            | streaming
sent_location    | 0/5000680
write_location   | 0/5000680
flush_location   | 0/5000680
replay_location  | 0/5000680
sync_priority    | 0
sync_state       | async
```

#### スタンバイデータベースを作り直す場合

スタンバイデータベースの損傷がひどくて起動できない場合は、プライマリデータベースを `pg_basebackup` コマンドで複製して作り直し、スタンバイ用の設定を加えて起動することになります。

これは上記の「リカバリの実行」でやっていることと同じなので、今のプライマリである pgsql2 で以下のコマンドを実行すれば OK です。

```
[root@pgsql2 pgsql]# sudo -i -u postgres /usr/pgpool-9.5/bin/pcp_recovery_node -h localhost -p 9898 -U pgpool2 0
Password: 
pcp_recovery_node -- Command Successful
```

## おわりに

さらに pgpool-II が落ちたときやサーバ全体が落ちたときなども検証が必要ですがこのブログ記事を書くのに、今日の早朝と今でなんだかんだで4時間ぐらいはかかっているので (環境構築と動作検証には3日かかってます)、一旦ここまでとします。

pgpool-II でのフェイルオーバ、リカバリは呼び出されるスクリプトをどうすれば良いのかが最初は全くわからなくて苦労しましたが、ドキュメントとソースを読んで理解できたので良かったです。

Pacemaker は高機能なんですが複雑すぎるように私には思えたので、 pgpool-II のほうが好感触です。
