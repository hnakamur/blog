---
title: "Zabbixのデータベースのパーティショニングについて検索してみた"
date: 2022-12-18T08:20:34+09:00
---
## はじめに

Zabbixのデータベースのパーティショニングについて検索してみたメモです。

## Zabbixの長期サポート版

[Zabbix Life Cycle & Release Policy](https://www.zabbix.com/life_cycle_and_release_policy)の表でバージョンの後にLTS (Long Term Support)とついているのが長期サポート版です。

今回は6.0のドキュメントを確認しました。

## Zabbixのデータベースのパーティショニング

[2 Requirements](https://www.zabbix.com/documentation/6.0/en/manual/installation/requirements)のThird-party external surrounding softwareの表を見ると、PostgreSQLの場合はTimescaleDBが使えます。

ちなみにMySQLとMariaDBはInnoDBが必須とのこと。Zabbix公式ブログの[Partitioning a Zabbix MySQL(8) database with Perl or Stored Procedures – Zabbix Blog](https://blog.zabbix.com/partitioning-a-zabbix-mysql-database-with-perl-or-stored-procedures/13531/)にMySQLでパーティショニングする説明がありました。

## 以下は関連して調べたメモ

### TimescaleDB

#### PostgreSQL 15は未対応

TimescaleDBは2022-12-18時点ではPostgreSQL15未サポート。[2 Requirements](https://www.zabbix.com/documentation/6.0/en/manual/installation/requirements)のThird-party external surrounding softwareの表にも書いてありました。[\[Enhancement\]: Support PostgreSQL 15 · Issue #3985 · timescale/timescaledb](https://github.com/timescale/timescaledb/issues/3985)のコメントを見ると対応中でexpect some news soonとのことでした。

[Timescale Documentation | Upgrade PostgreSQL](https://docs.timescale.com/timescaledb/latest/how-to-guides/upgrades/upgrade-pg/)にTimescaleDBがサポートしているPostgreSQLのバージョンの表がありました。

#### Timescale License

レポジトリのtslフォルダ配下は[Timescale License](https://github.com/timescale/timescaledb/blob/main/tsl/LICENSE-TIMESCALE)という独自ライセンスというのを[README.md](https://github.com/timescale/timescaledb/blob/main/LICENSE)と[tsl/README.md](https://github.com/timescale/timescaledb/blob/main/tsl/README.md)で知りました。

### MySQLとMariaDBのストレージエンジン

上に書いたようにZabbixではInnoDB必須なので今回の話では関係ないのですが、気付く前に調べたのでメモ。

* [MySQL :: MySQL 8.0 Reference Manual :: 16 Alternative Storage Engines](https://dev.mysql.com/doc/refman/8.0/en/storage-engines.html)
* [Storage Engines - MariaDB Knowledge Base](https://mariadb.com/kb/en/storage-engines/)

[MyRocks - MariaDB Knowledge Base](https://mariadb.com/kb/en/myrocks/)ストレージエンジンはMySQLにはなくMariaDBだけなんですね。[About MyRocks for MariaDB - MariaDB Knowledge Base](https://mariadb.com/kb/en/about-myrocks-for-mariadb/)のBenefitsのGreater Writing Efficiencyの項に以下のように書かれていました。

> 2x lower write rates to storage
>
> MyRocks has a 10x less write amplification compared to InnoDB, giving you better endurance of flash storage and improving overall throughput. 

