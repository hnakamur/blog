+++
Categories = []
Description = ""
Tags = ["groonga"]
date = "2015-04-26T23:53:06+09:00"
title = "Groongaのチュートリアルを試してみた"

+++

Groongaのチュートリアルを試してみたメモです。
試した環境は Groonga 5.0.2, Ubuntu 14.04.2 です。

## セットアップ手順

[2.4. Ubuntu — Groonga v5.0.2ドキュメント](http://groonga.org/ja/docs/install/ubuntu.html#ppa-personal-package-archive)にそってセットアップしました。

セットアップ手順は[Dockerfile](https://github.com/hnakamur/groonga-dockerfiles/blob/b4d64e23eaf9afda47c31bc34794eb2e56b7614d/dockerfiles/trusty/Dockerfile)にまとめておきました。

さらにVirtualBox + VagrantでUbuntuにdockerとdocker-composeをインストールして、上のDockerfileでコンテナを作る手順を自動化するVagrantfileを作成して
[hnakamur/groonga-dockerfiles](https://github.com/hnakamur/groonga-dockerfiles)
で公開しています。

VirtualBoxとVagrantをインストールしてあれば、以下の手順ですぐ試せます。

```
git clone https://github.com/hnakamur/groonga-dockerfiles
cd groonga-dockerfiles
vagrant up
```

起動後コンテナを作って起動するまでには結構時間がかかります。

```
$ vagrant ssh
```

でVMにログインして、以下のようにCommandでgroonga-httpdが実行されたら起動完了です。

```
$ cd /vagrant/dockerfiles
$ sudo docker-compose ps
      Name             Command             State              Ports
-------------------------------------------------------------------------
dockerfiles_groo   /usr/sbin          Up                 0.0.0.0:80->1004
ngatrusty_1        /groonga-httpd                        1/tcp
                   -g ...
```

## 管理画面とgroongaコマンドの起動方法

http://192.168.33.12/ でgroongaの管理画面にアクセスできます。

groongaコマンドの起動方法は以下の通りです。

```
vagrant ssh
```

でVMにログインし、

```
sudo docker exec -it dockerfiles_groongatrusty_1 /bin/bash
```

でコンテナ内に入り

```
sudo -u groonga groonga /var/lib/groonga/db/db
```

でgroongaコマンドを実行します。


### groongaコマンドの実行ユーザをrootにするとハマるので注意

groongaコマンドはgroongaで実行するのが重要です。

rootユーザで実行してしまうとエラーにはならないのですが、テーブルなどを作成してもgroongaの管理画面で表示されずハマりました。

groongaのデータベースは最初は1つのファイルですが、テーブルなどを作るとファイルが追加で作成されます。

```
root@b95446c72160:/# cd /var/lib/groonga/db
root@b95446c72160:/var/lib/groonga/db# ll
total 15332
drwxr-xr-x 2 groonga groonga     4096 Apr 26 14:34 ./
drwxr-xr-x 3 groonga groonga     4096 Apr 26 01:49 ../
-rw-r--r-- 1 groonga groonga     4096 Apr 26 14:33 db
-rw-r--r-- 1 groonga groonga 21245952 Apr 26 14:33 db.0000000
-rw-r--r-- 1 groonga groonga 16842752 Apr 26 14:34 db.0000100
-rw-r--r-- 1 groonga groonga 12857344 Apr 26 14:26 db.0000101
-rw-r--r-- 1 groonga groonga  8437760 Apr 26 14:28 db.0000102
-rw-r--r-- 1 groonga groonga  1085440 Apr 26 14:28 db.0000103
-rw-r--r-- 1 groonga groonga  4198400 Apr 26 14:28 db.0000103.c
-rw-r--r-- 1 groonga groonga  8437760 Apr 26 14:34 db.0000104
-rw-r--r-- 1 groonga groonga  4198400 Apr 26 14:34 db.0000105
-rw-r--r-- 1 groonga groonga  1085440 Apr 26 14:34 db.0000106
-rw-r--r-- 1 groonga groonga  4198400 Apr 26 14:34 db.0000106.c
-rw-r--r-- 1 groonga groonga  1048576 Apr 26 14:34 db.001
```

rootユーザでgroongaコマンドを実行すると作成されたファイルの所有者がrootユーザになり、groonga-httpdから見えないようです。

`chown groonga: /var/lib/groonga/db/db*` で所有者をgroongaユーザに変更すれば見えるようになりました。

ということで、上記のようにgroongaユーザでgroongaコマンドを実行するのが良いです。

## チュートリアルの一部手順でエラーが出てハマった

[4. チュートリアル — Groonga v5.0.2ドキュメント](http://groonga.org/ja/docs/tutorial.html)の手順で試してみました。ほとんどはすんなり実行できましたが、1箇所ハマりました。

### インデックス付きジオサーチのところでnonexistent sourceというエラー

[4.6.3. インデックス付きジオサーチ](http://groonga.org/ja/docs/tutorial/index.html#geo-location-search-with-index)のところで以下の様なエラーが出ました。

```
> table_create --name GeoIndex --flags TABLE_PAT_KEY --key_type WGS84GeoPoint
[[0,1429178015.01179,0.00191092491149902],true]
> column_create --table GeoIndex --name index_point --type Site --flags COLUMN_INDEX --source location
[[-22,1429178020.73797,0.00554323196411133,"[column][create] nonexistent source: <location>",[["proc_column_create_resolve_source_name","proc.c",1774]]],false]
```

Siteテーブルは[4.1.5. テーブルの作成](http://groonga.org/ja/docs/tutorial/introduction.html#create-a-table)で

```
table_create --name Site --flags TABLE_HASH_KEY --key_type ShortText
```

として作成していますが、その後 `location` カラムを作る箇所がなかったようです。

2015-04-28追記 https://twitter.com/kenhys/status/592901925089189889 でご指摘いただいたのですが、実は[4.4.3. 位置情報を用いた絞込・ソート](http://groonga.org/ja/docs/tutorial/search.html#narrow-down-sort-by-using-location-information)で `location` カラムを作っているのを私が見落としていました。失礼いたしました。

```
column_create --table Site --name location --type WGS84GeoPoint
```

のようにカラムを作成すれば大丈夫でした。

```
table_create --name GeoIndex --flags TABLE_PAT_KEY --key_type WGS84GeoPoint
column_create --table GeoIndex --name index_point --type Site --flags COLUMN_INDEX --source location
```

でインデクス用のテーブルとカラムを作成して、

```
load --table Site
[
 {"_key":"http://example.org/","location":"128452975x503157902"},
 {"_key":"http://example.net/","location":"128487316x502920929"}
]
```

で、データをロードします。

```
> select --table Site --filter 'geo_in_circle(location, "128515259x503187188", 5000)' --output_columns _key,location
[[0,1430061299.24235,0.00105690956115723],[[[1],[["_key","ShortText"],["location","WGS84GeoPoint"]],["http://example.org/","128452975x503157902"]]]]
```

で検索できました。

## まとめ

2箇所ハマりましたが解決してとりあえず使えるようになりました。今後さらに調査していきたいと思います。
