+++
Categories = []
Description = ""
Tags = ["postgresql","pacemaker","lxd","ansible"]
date = "2016-08-21T11:23:01+09:00"
title = "Pacemakerを使ってPostgreSQLのアクティブ・スタンバイ(1+1構成)を試してみた"

+++
## はじめに

STONITH無し、quorum無しのアクティブ・スタンバイ(1+1構成)がとりあえず動くところまでは来たので、一旦メモです。

## 参考資料

以下の資料と連載記事がわかりやすくて非常に参考になりました。ありがとうございます！

* [JPUG 第23回しくみ+アプリケーション勉強会 セミナー資料公開 « Linux-HA Japan](http://linux-ha.osdn.jp/wp/archives/3244)
    - [HAクラスタでPostgreSQLを高可用化(前編) ～Pacemaker入門編～(PDF)](http://linux-ha.osdn.jp/wp/wp-content/uploads/pacemaker_20120526JPUG.pdf)
    - [PostgreSQLを高可用化(後編) 〜レプリケーション編〜(PDF)](http://linux-ha.osdn.jp/wp/wp-content/uploads/b754c737d835c2546415009387407b7b.pdf)
* [OSC 2013 Tokyo/Spring 講演資料公開 « Linux-HA Japan](http://linux-ha.osdn.jp/wp/archives/3589)
    - [Pacemaker+PostgreSQLレプリケーションで共有ディスクレス高信頼クラスタの構築＠OSC 2013 Tokyo/Spring](http://www.slideshare.net/takmatsuo/osc-tokyospring2013-16694861)
* [Pacemakerでかんたんクラスタリング体験してみよう！：連載｜gihyo.jp … 技術評論社](http://gihyo.jp/admin/serial/01/pacemaker)

さらに以下の記事と電子書籍も参考にしました。

* [PgSQL Replicated Cluster - ClusterLabs](http://clusterlabs.org/wiki/PgSQL_Replicated_Cluster)
* [PostgreSQL Replication, 2nd Edition - O'Reilly Media](http://shop.oreilly.com/product/9781783550609.do)

## テスト用のAnsible playbook

https://github.com/hnakamur/postgresql-pacemaker-example-playbook
に置きました。

LXD をセットアップ済みの Ubuntu 16.04 上で試しました。

## セットアップの事前準備

上記のplaybookを取得します。

```
git clone https://github.com/hnakamur/postgresql-pacemaker-example-playbook
cd postgresql-pacemaker-example-playbook
```

Ansibleの `lxd_container` モジュールを使うので、virtualenvで仮想環境を作ってAnsibleのmaster版をインストールします。

```
virtualenv venv
source venv/bin/activate
pip install git+https://github.com/ansible/ansible
```

今回はコンテナのIPアドレスをDHCPではなく静的アドレスを使うようにしてみました。

`/etc/default/lxd-bridge` の `LXD_IPV4_DHCP_RANGE` に DHCP のアドレス範囲が設定されているので、ファイルを編集して範囲を狭めます。私の環境では以下のようにしました。

```
## IPv4 network (e.g. 10.0.8.0/24)
LXD_IPV4_NETWORK="10.155.92.1/24"

## IPv4 DHCP range (e.g. 10.0.8.2,10.0.8.254)
LXD_IPV4_DHCP_RANGE="10.155.92.200,10.155.92.254"
```

LXDをインストールしたときに `LXD_IPV4_NETWORK` はランダムなアドレスになるかあるいは自分で指定しますので、それに応じた値に適宜変更してください。

変更したら `lxd-bridge` を再起動して変更を反映します。

```
sudo systemctl restart lxd-bridge
```

`group_vars/development/vars.yml` ファイル内のIPアドレスも適宜変更します。

また、 `group_vars/development/secrets.yml` 内にパスワードやsshの鍵ペアなどが含まれています。これを違う値に変更したい場合は以下のようにします。

まず、以下のコマンドを実行して一旦復号化します。

```
ansible-vault decrypt group_vars/development/secrets.yml
```

vaultのパスワードを聞かれますので入力します。この例では `password` としています。これはあくまで例なのでこういう弱いパスワードにしていますが、実際の案件で使うときは、もっと強いパスワードを指定してください。

`group_vars/development/secrets.yml` 内の変数を適宜変更したら、以下のコマンドを実行して暗号化します。

```
ansible-vault encrypt group_vars/development/secrets.yml
```

vaultの新しいパスワードを聞かれますので入力してください。


## コンテナの作成

以下のコマンドを実行して `node1` と `node2` という2つのコンテナを作成します。

```
$ ansible-playbook launch_containers.yml -D -v
```

vaultのパスワードを聞かれますので入力してください。

## コンテナ内にPostgreSQLとPacemakerをセットアップ

以下のコマンドを実行して、コンテナ内にPostgreSQLとPacemakerをセットアップします。

```
$ ansible-playbook setup_containers.yml -D -v
```

ここでは、セットアップ完了後、アクティブスタンバイ構成が開始するまでの時間を図りたいので、以下のように `date -u` コマンドも実行するようにします。

```
$ ansible-playbook setup_containers.yml -D -v; date -u
…(略)…
Sun Aug 21 13:51:21 UTC 2016
```

以下のコマンドを実行して `node2` コンテナに入ります。

```
$ lxc exec node2 bash
```

以下のコマンドを実行して、クラスタの状態をモニターします。
`node1`, `node2` が両方 Slaves の状態を経て、 `node1` が Master になり master-ip が `node1` につくまで待ちます。

```
Last updated: Sun Aug 21 13:52:07 2016          Last change: Sun Aug 21 13:52:03 2016 by root via crm_attribute on node1
Stack: corosync
Current DC: node1 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 3 resources configured

Online: [ node1 node2 ]

 Master/Slave Set: pgsql-master [pgsql]
     Masters: [ node1 ]
     Slaves: [ node2 ]
master-ip       (ocf::heartbeat:IPaddr2):       Started node1

Node Attributes:
* Node node1:
    + master-pgsql                      : 1000
    + pgsql-data-status                 : LATEST
    + pgsql-master-baseline             : 0000000003000098
    + pgsql-status                      : PRI
    + pgsql-xlog-loc                    : 0000000003000098
* Node node2:
    + master-pgsql                      : -INFINITY
    + pgsql-data-status                 : STREAMING|ASYNC
    + pgsql-status                      : HS:async
    + pgsql-xlog-loc                    : 0000000003000000

Migration Summary:
* Node node2:
* Node node1:
```

この端末は開いたままにしておきます。

## node1 コンテナを強制停止してフェールオーバのテスト

別の端末を開いて以下のコマンドを実行し、 `node1` コンテナを強制停止し時刻を記録します。

```
$ lxc stop -f node1; date -u
Sun Aug 21 13:52:57 UTC 2016
```

しばらくすると　`crm_mon -fA` の出力が以下のようになります。

```
Last updated: Sun Aug 21 13:53:11 2016          Last change: Sun Aug 21 13:53:05 2016 by root via crm_attribute on node2
Stack: corosync
Current DC: node2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 3 resources configured

Online: [ node2 ]
OFFLINE: [ node1 ]

 Master/Slave Set: pgsql-master [pgsql]
     Masters: [ node2 ]
master-ip       (ocf::heartbeat:IPaddr2):       Started node2

Node Attributes:
* Node node2:
    + master-pgsql                      : 1000
    + pgsql-data-status                 : LATEST
    + pgsql-master-baseline             : 00000000030001A8
    + pgsql-status                      : PRI
    + pgsql-xlog-loc                    : 0000000003000000

Migration Summary:
* Node node2:
```

LXDホストで以下のコマンドを実行して `node1` を起動します。

```
$ lxc start node1; date -u
Sun Aug 21 13:53:58 UTC 2016
```

起動後しばらくしても `node1` はオフラインのままですが、これは意図した挙動です。実際のケースではディスク障害などが起きているかもしれないので、マシンの状況を確認してから手動でクラスタに復帰させることになるためです。

以下のコマンドで `node1` コンテナに入ります。

```
$ lxc exec node1 bash
```

PacemakerがPostgreSQLのロックファイルを作っているのでそれを削除します。

```
[root@node1 ~]# ll /var/run/postgresql/
total 4
-rw-r----- 1 root     root      0 Aug 21 13:52 PGSQL.lock
-rw-r----- 1 postgres postgres 36 Aug 21 13:52 rep_mode.conf
[root@node1 ~]# rm /var/run/postgresql/PGSQL.lock
rm: remove regular empty file '/var/run/postgresql/PGSQL.lock'? y
```

以下のコマンドで `node1` をクラスタに復帰させ、時刻を記録します。

```
[root@node1 ~]# pcs cluster start node1; date -u
node1: Starting Cluster...
Sun Aug 21 13:55:30 UTC 2016
```

15秒後、 `crm_mon -fA` の画面で `node1` の PostgreSQL が Slaves に追加されました。

```
Last updated: Sun Aug 21 13:55:45 2016          Last change: Sun Aug 21 13:55:42 2016 by root via crm_attribute on node2
Stack: corosync
Current DC: node2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 3 resources configured

Online: [ node1 node2 ]

 Master/Slave Set: pgsql-master [pgsql]
     Masters: [ node2 ]
     Slaves: [ node1 ]
master-ip       (ocf::heartbeat:IPaddr2):       Started node2

Node Attributes:
* Node node1:
    + master-pgsql                      : 100
    + pgsql-data-status                 : STREAMING|SYNC
    + pgsql-status                      : HS:sync
* Node node2:
    + master-pgsql                      : 1000
    + pgsql-data-status                 : LATEST
    + pgsql-master-baseline             : 00000000030001A8
    + pgsql-status                      : PRI
    + pgsql-xlog-loc                    : 0000000003000000

Migration Summary:
* Node node2:
* Node node1:
```

ここで、 `node2` で `crm_mon -fA` を実行していた端末で Control-C を入力してモニターを終了します。

## PostgreSQLのプロセスを強制終了してフェールオーバのテスト

今度は `node2` の PostgreSQL のプロセスを強制終了してフェールオーバしてみます。

経過を見るために `node1` で以下のコマンドを実行して、その端末を開いたままにしておきます。

```
[root@node1 ~]# crm_mon -fA
```

開始時点では以下のような出力になっていました。

```
Last updated: Sun Aug 21 13:57:17 2016          Last change: Sun Aug 21 13:55:42 2016 by root via crm_attribute on node2
Stack: corosync
Current DC: node2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 3 resources configured

Online: [ node1 node2 ]

 Master/Slave Set: pgsql-master [pgsql]
     Masters: [ node2 ]
     Slaves: [ node1 ]
master-ip       (ocf::heartbeat:IPaddr2):       Started node2

Node Attributes:
* Node node1:
    + master-pgsql                      : 100
    + pgsql-data-status                 : STREAMING|SYNC
    + pgsql-status                      : HS:sync
* Node node2:
    + master-pgsql                      : 1000
    + pgsql-data-status                 : LATEST
    + pgsql-master-baseline             : 00000000030001A8
    + pgsql-status                      : PRI
    + pgsql-xlog-loc                    : 0000000003000000

Migration Summary:
* Node node2:
* Node node1:
```

`node2` で以下のコマンドを実行して PostgreSQL のプロセスを強制終了し、時刻を記録します。

```
[root@node2 ~]# kill -KILL `head -1 /var/lib/pgsql/9.5/data/postmaster.pid`; date -u
Sun Aug 21 13:58:20 UTC 2016
```

11秒後 `node1` の PostgreSQL が Masterに昇格されました。

```
Last updated: Sun Aug 21 13:58:31 2016          Last change: Sun Aug 21 13:58:27 2016 by root via crm_attribute on node1
Stack: corosync
Current DC: node2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 3 resources configured

Online: [ node1 node2 ]

 Master/Slave Set: pgsql-master [pgsql]
     Masters: [ node1 ]
master-ip       (ocf::heartbeat:IPaddr2):       Started node1

Node Attributes:
* Node node1:
    + master-pgsql                      : 1000
    + pgsql-data-status                 : LATEST
    + pgsql-master-baseline             : 0000000003000398
    + pgsql-status                      : PRI
* Node node2:
    + master-pgsql                      : -INFINITY
    + pgsql-data-status                 : DISCONNECT
    + pgsql-status                      : STOP

Migration Summary:
* Node node2:
   pgsql: migration-threshold=2 fail-count=1000000 last-failure='Sun Aug 21 13:58:23 2016'
* Node node1:

Failed Actions:
* pgsql_start_0 on node2 'unknown error' (1): call=23, status=complete, exitreason='My data may be inconsistent. You have to remove /va
r/run/postgresql/PGSQL.lock file to force start.',
    last-rc-change='Sun Aug 21 13:58:23 2016', queued=0ms, exec=383ms
```

次に、 `node2` の PostgreSQL を再び稼働してスタンバイにさせてみます。

まず Pacemaker が作成した PostgreSQL のロックファイル `/var/run/postgresql/PGSQL.lock` を削除します。

```
[root@node2 ~]# ll /var/run/postgresql/
total 4
-rw-r----- 1 root     root      0 Aug 21 13:53 PGSQL.lock
-rw-r----- 1 postgres postgres 31 Aug 21 13:58 rep_mode.conf
[root@node2 ~]# \rm /var/run/postgresql/PGSQL.lock
```

次に以下のコマンドを実行して `node2` のPostgreSQL の failcount をリセットし、時刻を記録します。

```
[root@node2 ~]# pcs resource failcount reset pgsql node2; date -u
Sun Aug 21 14:00:04 UTC 2016
```

9秒後、 `node1` での `crm_mon -fA` の出力を見ると `node2` がスタンバイになりました。

```
Last updated: Sun Aug 21 14:00:13 2016          Last change: Sun Aug 21 14:00:10 2016 by root via crm_attribute on node1
Stack: corosync
Current DC: node2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 3 resources configured

Online: [ node1 node2 ]

 Master/Slave Set: pgsql-master [pgsql]
     Masters: [ node1 ]
     Slaves: [ node2 ]
master-ip       (ocf::heartbeat:IPaddr2):       Started node1

Node Attributes:
* Node node1:
    + master-pgsql                      : 1000
    + pgsql-data-status                 : LATEST
    + pgsql-master-baseline             : 0000000003000398
    + pgsql-status                      : PRI
* Node node2:
    + master-pgsql                      : 100
    + pgsql-data-status                 : STREAMING|SYNC
    + pgsql-status                      : HS:sync

Migration Summary:
* Node node2:
* Node node1:

Failed Actions:
* pgsql_start_0 on node2 'unknown error' (1): call=23, status=complete, exitreason='My data may be inconsistent. You have to remove /va
r/run/postgresql/PGSQL.lock file to force start.',
    last-rc-change='Sun Aug 21 13:58:23 2016', queued=0ms, exec=383ms
```

## おわりに

STONITH無し、quorum無しという簡易構成ですが、アクティブ・スタンバイ(1+1構成)でフフェールオーバする検証ができました。本番運用するにはSTONITHやquorumも重要そうなので、そちらも調べて行きたいです。
