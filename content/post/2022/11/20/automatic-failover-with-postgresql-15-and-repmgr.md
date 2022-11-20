---
title: "PostgreSQL 15とrepmgrで自動フェイルオーバーを試してみた"
date: 2022-11-20T18:49:33+09:00
---
## はじめに

[repmgr - Replication Manager for PostgreSQL clusters](https://repmgr.org/) というのを最近知ったので PostgreSQL 15 との組み合わせで自動フェールオーバーを試してみたメモです。

## 試した環境

* LXD 5.6
* Ubuntu 22.04 LTS
* PostgreSQL 15
* repmgr 5.3.3

## 構築手順メモ

LXD で repmgr のプロジェクトを作って切り替えます。

```bash
lxc project create repmgr -c features.images=false -c features.profiles=false
lxc project switch repmgr
```

2 つのコンテナ名を変数にセットします。

```bash
containers=$(for c in node{1,2}; do echo $c; done)
```

コンテナを作成起動します。

```bash
for c in $containers; do
  lxc launch ubuntu:22.04 $c
done
```

`apt-get update` を実行します。

```bash
for c in $containers; do
  lxc exec $c -- apt-get update
done
```

[2.2.2. Debian/Ubuntu](https://repmgr.org/docs/current/installation-packages.html#INSTALLATION-PACKAGES-DEBIAN) に書かれていた PostgreSQL Community APT repository (https://apt.postgresql.org/) から deb パッケージをインストールする手順にしました。

PostgreSQL Global Development Group (PGDG) のレポジトリの鍵をインポートして、レポジトリを追加。

```bash
for c in $containers; do
  lxc exec $c -- mkdir -p /usr/local/share/keyrings
done
for c in $containers; do
  lxc exec $c -- curl -sS -o /usr/local/share/keyrings/pgdg.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc
done
for c in $containers; do
  lxc exec $c -- sh -c 'echo "deb [signed-by=/usr/local/share/keyrings/pgdg.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
done
```

`apt-get update` した後必要なパッケージをインストール。
[4.1. Prerequisites for configuration](https://repmgr.org/docs/current/configuration-prerequisites.html) に Debian パッケージのように PostgreSQL のデータディレクトリ外に設定ファイルがある場合は rsync が必要とのことなので、openssh-server とともに入れています。

```bash
for c in $containers; do
  lxc exec $c -- apt-get update
done

for c in $containers; do
  lxc exec $c -- apt-get -y install postgresql-15 postgresql-15-repmgr sudo openssh-server rsync
done
```

ロケール作成。

```bash
for c in $containers; do
  lxc exec $c -- sed -i '/^# ja_JP.UTF-8 UTF-8/s/^# //' /etc/locale.gen
done
for c in $containers; do
  lxc exec $c -- locale-gen
done
```

postgresユーザでパスフレーズ無しの鍵で2つのコンテナ間でsshできるようにセットアップ。

```bash
ssh-keygen -t ed25519 -f postgres.id_ed25519 -C postgres -N ''

for c in $containers; do
  lxc exec $c -- sudo -u postgres mkdir -m 700 /var/lib/postgresql/.ssh
  lxc file push --mode 400 postgres.id_ed25519 $c/var/lib/postgresql/.ssh/id_ed25519
  lxc file push --mode 600 postgres.id_ed25519.pub $c/var/lib/postgresql/.ssh/authorized_keys
  lxc exec $c -- sh -c 'chown postgres: /var/lib/postgresql/.ssh/*'
done
lxc exec node1 -- sudo -u postgres sh -c 'ssh-keyscan -H node2 > /var/lib/postgresql/.ssh/known_hosts'
lxc exec node2 -- sudo -u postgres sh -c 'ssh-keyscan -H node1 > /var/lib/postgresql/.ssh/known_hosts'
```

PostgreSQLの設定ファイル作成。
[3.2. PostgreSQL configuration](https://repmgr.org/docs/current/quickstart-postgresql-configuration.html) と [4.1. Prerequisites for configuration](https://repmgr.org/docs/current/configuration-prerequisites.html#CONFIGURATION-POSTGRESQL) を参考にしました。

```bash
for c in $containers; do
  cat <<EOF | lxc exec $c -- sudo -u postgres sh -c 'cat > /etc/postgresql/15/main/conf.d/01-custom.conf'
listen_addresses = '*'
port = 5432
timezone = 'Asia/Tokyo'
log_timezone = 'Asia/Tokyo'
logging_collector = on
log_directory = '/var/log/postgresql/15-main'
max_wal_senders = 10
wal_level = replica
wal_log_hints = on
archive_mode = on
archive_command = '/bin/true'

external_pid_file = '/run/postgresql/15-main.pid'

tcp_keepalives_idle = 60
tcp_keepalives_interval = 5
tcp_keepalives_count = 6

shared_buffers = 1024MB
work_mem = 8MB

hot_standby = on
hot_standby_feedback = on
max_replication_slots = 10
max_standby_streaming_delay = -1
max_standby_archive_delay = -1
reload_after_crash = off
synchronous_commit = on
wal_keep_size = 16GB
wal_receiver_status_interval = 2

# Use repmgrd for automatic failover
shared_preload_libraries = 'repmgr'
EOF
done
```

repmgrユーザとrepmgrデータベースを作成。パスワードは適宜変更してください。

```bash
for c in $containers; do
  lxc exec $c -- sudo -iu postgres mkdir -p /var/log/postgresql/15-main
done

for c in $containers; do
  lxc exec $c -- sudo -iu postgres psql -c "CREATE USER repmgr SUPERUSER PASSWORD 'repmgrpass';"
done

for c in $containers; do
  lxc exec $c -- sudo -iu postgres createdb repmgr -O repmgr
done

for c in $containers; do
  lxc exec $c -- sudo -iu postgres sh -c "install -m 600 /dev/null /var/lib/postgresql/.pgpass"
  cat <<EOF | lxc exec $c -- sudo -u postgres sh -c 'cat > /var/lib/postgresql/.pgpass'
*:*:*:repmgr:repmgrpass
EOF
done
```

`pg_hba.conf` に repmgr ユーザ用の設定を追加。

```bash
for c in $containers; do
  lxc exec $c -- cp /etc/postgresql/15/main/pg_hba.conf /etc/postgresql/15/main/pg_hba.conf.orig
done

for c in $containers; do
  cat <<EOF | lxc exec $c -- sudo -u postgres tee -a /etc/postgresql/15/main/pg_hba.conf > /dev/null

#
# custom entries for repmgr
#
host    replication     repmgr          samenet                 scram-sha-256
host    repmgr          repmgr          samenet                 scram-sha-256
EOF
done
```

リロードして反映。

```bash
for c in $containers; do
  lxc exec $c -- systemctl reload postgresql@15-main
done
```

接続テスト。

```bash
lxc exec node1 -- sudo -iu postgres psql -c "SELECT 1" 'host=node1 user=repmgr dbname=repmgr connect_timeout=2'
```

フェイルオーバー成功時に仮想IPアドレス(VIP)を追加するスクリプトを作成。
以下ではVIPを192.0.2.2/32としていますが、環境に合わせて適宜変更してください。
`/usr/local/bin/vip` はVIPを追加してGARPを送信する自作CLIです (詳細は [GoでGratious ARP (GARP)を送信と受信する · hnakamur's blog](/blog/2022/11/19/send-and-receive-garp-with-go/) 参照)。

```
for c in $containers; do
  lxc exec $c -- install -m 755 /dev/null /usr/local/sbin/add-vip-on-standby-promote.sh
  cat <<'EOF' | lxc exec $c -- tee /dev/null /usr/local/sbin/add-vip-on-standby-promote.sh > /dev/null
#!/bin/bash
success="$1"
logger -t repmgr-event add-vip-on-standby-promote "$success"
if [ "$success" -eq 1 ]; then
  /usr/bin/sudo /usr/local/bin/vip add --interface eth0 --label eth0:0 --address 192.0.2.2/32
fi
EOF
done
```

repmgrの設定ファイル `/etc/repmgr.conf` を作成。
repmgrのCLIで `-f` オプションを明示的に指定しない場合に設定ファイルを読み込むパスが
https://github.com/EnterpriseDB/repmgr/blob/v5.3.3/configfile.c#L151-L225
に書かれているので、このうち `/etc/repmgr.conf` に置くことにしました。

```bash
for id in {1,2}; do
  cat <<EOF | lxc exec node$id -- tee /etc/repmgr.conf > /dev/null
node_id=$id
node_name='node$id'
conninfo='host=node$id user=repmgr dbname=repmgr connect_timeout=2'
pg_bindir='/usr/lib/postgresql/15/bin'
data_directory='/var/lib/postgresql/15/main'
service_start_command='/usr/bin/sudo /usr/bin/systemctl start postgresql'
service_stop_command='/usr/bin/sudo /usr/bin/systemctl stop postgresql'
service_reload_command='/usr/bin/sudo /usr/bin/systemctl restart postgresql'
service_reload_command='/usr/bin/sudo /usr/bin/systemctl reload postgresql'
failover=automatic
promote_command='/usr/bin/repmgr standby promote --log-to-file'
follow_command='/usr/bin/repmgr standby follow --log-to-file --upstream-node-id=%n'
monitoring_history=yes
log_file='/var/log/postgresql/15-main/repmgr.log'
repmgrd_pid_file='/var/run/postgresql/repmgrd.pid'
event_notification_command='/usr/local/sbin/add-vip-on-standby-promote.sh %s'
event_notifications='standby_promote'
EOF
done
```

repmgrdを使うために設定ファイルを編集します。

```sudo
for c in $containers; do
  lxc exec $c -- sed -i -e 's|^REPMGRD_ENABLED=no$|REPMGRD_ENABLED=yes|;s|^#REPMGRD_CONF="/path/to/repmgr.conf"$|REPMGRD_CONF="/etc/repmgr.conf"|' /etc/default/repmgrd
done
```

postgresユーザが以下のコマンドをパスワード無しでsudoで実行できるように設定を追加。

```sudo
for c in $containers; do
  cat <<'EOF' | lxc exec $c -- sh -c 'cat > /etc/sudoers.d/01-postgres'
Defaults:postgres !requiretty
postgres ALL = NOPASSWD: /usr/bin/systemctl start postgresql, \
                         /usr/bin/systemctl stop postgresql, \
                         /usr/bin/systemctl reload postgresql, \
                         /usr/bin/systemctl reload postgresql, \
                         /usr/local/bin/vip add --interface eth0 --label eth0\:0 --address 192.0.2.2/32
EOF
done
```

[3.7. Register the primary server](https://repmgr.org/docs/current/quickstart-primary-register.html) に従ってプライマリサーバを登録。

```bash
lxc exec node1 -- sudo -u postgres repmgr primary register

lxc exec node1 -- sudo -u postgres repmgr cluster show

lxc exec node1 -- sudo -u postgres psql -U repmgr -h localhost -c '\x on' -c 'SELECT * FROM repmgr.nodes;' repmgr
```

[3.8. Clone the standby server](https://repmgr.org/docs/current/quickstart-standby-clone.html) を参考にスタンバイサーバをセットアップ。スタンバイサーバのPostgreSQLを停止し、データディレクトリを削除し、`repmgr standby clone` を `--dry-run` つきで実行。

```bash

lxc exec node2 -- systemctl stop postgresql
lxc exec node2 -- sudo -iu postgres sh -c 'rm -rf /var/lib/postgresql/15/main/*'

lxc exec node2 -- sudo -iu postgres repmgr -h node1 -U repmgr -d repmgr standby clone --dry-run
```

ドライランの出力結果。

```
$ lxc exec node2 -- sudo -iu postgres repmgr -h node1 -U repmgr -d repmgr standby clone --dry-run
NOTICE: destination directory "/var/lib/postgresql/15/main" provided
INFO: connecting to source node
DETAIL: connection string is: host=node1 user=repmgr dbname=repmgr
DETAIL: current installation size is 29 MB
INFO: "repmgr" extension is installed in database "repmgr"
INFO: replication slot usage not requested;  no replication slot will be set up for this standby
INFO: parameter "max_wal_senders" set to 10
NOTICE: checking for available walsenders on the source node (2 required)
INFO: sufficient walsenders available on the source node
DETAIL: 2 required, 10 available
NOTICE: checking replication connections can be made to the source server (2 required)
INFO: required number of replication connections could be made to the source server
DETAIL: 2 replication connections required
NOTICE: standby will attach to upstream node 1
HINT: consider using the -c/--fast-checkpoint option
INFO: would execute:
  /usr/lib/postgresql/15/bin/pg_basebackup -l "repmgr base backup"  -D /var/lib/postgresql/15/main -h node1 -p 5432 -U repmgr -X stream
INFO: all prerequisites for "standby clone" are met
```

`--dry-run` なしで実際に実行。

```bash
lxc exec node2 -- sudo -iu postgres repmgr -h node1 -U repmgr -d repmgr standby clone
```

出力結果。

```
$ lxc exec node2 -- sudo -iu postgres repmgr -h node1 -U repmgr -d repmgr standby clone
NOTICE: destination directory "/var/lib/postgresql/15/main" provided
INFO: connecting to source node
DETAIL: connection string is: host=node1 user=repmgr dbname=repmgr
DETAIL: current installation size is 29 MB
INFO: replication slot usage not requested;  no replication slot will be set up for this standby
NOTICE: checking for available walsenders on the source node (2 required)
NOTICE: checking replication connections can be made to the source server (2 required)
INFO: checking and correcting permissions on existing directory "/var/lib/postgresql/15/main"
NOTICE: starting backup (using pg_basebackup)...
HINT: this may take some time; consider using the -c/--fast-checkpoint option
INFO: executing:
  /usr/lib/postgresql/15/bin/pg_basebackup -l "repmgr base backup"  -D /var/lib/postgresql/15/main -h node1 -p 5432 -U repmgr -X stream
NOTICE: standby clone (using pg_basebackup) complete
NOTICE: you can now start your PostgreSQL server
HINT: for example: pg_ctl -D /var/lib/postgresql/15/main start
HINT: after starting the server, you need to register this standby with "repmgr standby register"
```

自動生成されたPostgreSQLの追加設定のファイルを確認。

```bash
lxc exec node2 -- cat /var/lib/postgresql/15/main/postgresql.auto.conf
```

実行結果。

```
$ lxc exec node2 -- cat /var/lib/postgresql/15/main/postgresql.auto.conf
# Do not edit this file manually!
# It will be overwritten by the ALTER SYSTEM command.
primary_conninfo = 'host=node1 user=repmgr application_name=node2 connect_timeout=2'
```

スタンバイサーバのPostgreSQLサービスを起動。

```bash
lxc exec node2 -- systemctl start postgresql
```

レプリケーションの状態確認。

```bash
lxc exec node1 -- sudo -iu postgres psql -h node1 -U repmgr -d repmgr -c "\x on" -c "SELECT * FROM pg_stat_replication"
lxc exec node2 -- sudo -iu postgres psql -h node2 -U repmgr -d repmgr -c "\x on" -c "SELECT * FROM pg_stat_wal_receiver"
```

実行結果。

```
$ lxc exec node1 -- sudo -iu postgres psql -h node1 -U repmgr -d repmgr -c "\x on" -c "SELECT * FROM pg_sta
t_replication"
Expanded display is on.
-[ RECORD 1 ]----+---------------------------------------
pid              | 4402
usesysid         | 16388
usename          | repmgr
application_name | node2
client_addr      | fd42:b136:20b6:1c77:216:3eff:fec2:d2c8
client_hostname  |
client_port      | 45718
backend_start    | 2022-11-09 23:40:02.953572+09
backend_xmin     | 743
state            | streaming
sent_lsn         | 0/5000298
write_lsn        | 0/5000298
flush_lsn        | 0/5000298
replay_lsn       | 0/5000298
write_lag        |
flush_lag        |
replay_lag       |
sync_priority    | 0
sync_state       | async
reply_time       | 2022-11-09 23:42:06.7976+09

$ lxc exec node2 -- sudo -iu postgres psql -h node2 -U repmgr -d repmgr -c "\x on" -c "SELECT * FROM pg_stat_wal_receiver"
Expanded display is on.
-[ RECORD 1 ]---------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
pid                   | 4275
status                | streaming
receive_start_lsn     | 0/5000000
receive_start_tli     | 1
written_lsn           | 0/50002D0
flushed_lsn           | 0/50002D0
received_tli          | 1
last_msg_send_time    | 2022-11-09 23:42:37.629225+09
last_msg_receipt_time | 2022-11-09 23:42:37.62934+09
latest_end_lsn        | 0/50002D0
latest_end_time       | 2022-11-09 23:42:07.595489+09
slot_name             |
sender_host           | node1
sender_port           | 5432
conninfo              | user=repmgr passfile=/var/lib/postgresql/.pgpass channel_binding=prefer connect_timeout=2 dbname=replication host=node1 port=5432 application_name=node2 fallback_application_name=15/main sslmode=prefer sslcompression=0 sslsni=1 ssl_min_protocol_version=TLSv1.2 gssencmode=prefer krbsrvname=postgres target_session_attrs=any
```

スタンバイサーバをrepmgrに登録。

```bash
lxc exec node2 -- sudo -u postgres repmgr standby register
```

実行結果。

```
$ lxc exec node2 -- sudo -u postgres repmgr standby register
INFO: connecting to local node "node2" (ID: 2)
INFO: connecting to primary database
WARNING: --upstream-node-id not supplied, assuming upstream node is primary (node ID: 1)
INFO: standby registration complete
NOTICE: standby node "node2" (ID: 2) successfully registered
```

クラスタの状態確認。

```bash
lxc exec node1 -- sudo -u postgres repmgr cluster show
```

2つのコンテナでの実行結果。同じ内容が出力された。

```
$ lxc exec node1 -- sudo -u postgres repmgr cluster show
 ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string
----+-------+---------+-----------+----------+----------+----------+----------+--------------------------------------------------------
 1  | node1 | primary | * running |          | default  | 100      | 1        | host=node1 user=repmgr dbname=repmgr connect_timeout=2
 2  | node2 | standby |   running | node1    | default  | 100      | 1        | host=node2 user=repmgr dbname=repmgr connect_timeout=2
```

```
$ lxc exec node2 -- sudo -u postgres repmgr cluster show
 ID | Name  | Role    | Status    | Upstream | Location | Priority | Timeline | Connection string
----+-------+---------+-----------+----------+----------+----------+----------+--------------------------------------------------------
 1  | node1 | primary | * running |          | default  | 100      | 1        | host=node1 user=repmgr dbname=repmgr connect_timeout=2
 2  | node2 | standby |   running | node1    | default  | 100      | 1        | host=node2 user=repmgr dbname=repmgr connect_timeout=2
```

GARPを受信したらVIPを削除する自作CLIのサービスを登録して起動。

```bash
for c in $containers; do
  cat <<'EOF' | lxc exec $c -- sh -c 'cat >> /etc/systemd/system/vip-delete.service'
[Unit]
Description=vip delete when GARP received
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/vip del --watch --interface eth0 --address 192.0.2.2/32

[Install]
WantedBy=multi-user.target
EOF
done
```

```bash
for c in $containers; do
  lxc exec $c -- systemctl daemon-reload
  lxc exec $c -- systemctl enable --now vip-delete.service
done
```

repmgrdは最初は止めた状態で

* [Chapter 6. Promoting a standby server with repmgr](https://repmgr.org/docs/current/promoting-standby.html)
* [Chapter 8. Performing a switchover with repmgr](https://repmgr.org/docs/current/performing-switchover.html)

を試して、その後

```bash
for c in $containers; do
  lxc exec $c -- systemctl enable --now repmgrd
done
```

でrepmgrdの自動起動を有効にしつつ起動して

* [Chapter 12. Automatic failover with repmgrd](https://repmgr.org/docs/current/repmgrd-automatic-failover.html)

を試しました。

テスト用のサンプルアプリケーション [hnakamur/postgresql-ha-test-webapp](https://github.com/hnakamur/postgresql-ha-test-webapp) を書いて試したところ、フェイルオーバー時は2秒程度接続エラーが出ますが、その後は復旧してデータベースに接続して更新処理が出来ていました。
