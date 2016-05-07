+++
Categories = []
Description = ""
Tags = ["lxd"]
date = "2016-05-07T14:12:49+09:00"
title = "LXCの特定の1つのコンテナの起動状態をシェルスクリプトで確認したいときのお勧めの方法"

+++
## イマイチな方法1: lxc listの出力をawkで加工

`lxc list -h` を見ると `lxc list [resource] [filters] [--format table|json] [-c columns] [--fast]` というコマンドラインになっていて、 `-c` オプションで表示するカラムを指定可能です。

例えば　以下のようにすれば `cent01` コンテナの起動状態だけを表示できます。

```
$ lxc list -c s cent01
+---------+
|  STATE  |
+---------+
| RUNNING |
+---------+
```

ただ、デフォルトの `--format table` だとASCII文字の罫線が表示されるので、状態を抜き出すにはawkで加工する必要があります。

```
$ lxc list -c s cent01 | awk 'NR==4{print $2}'
RUNNING
```

## イマイチな方法2: lxc list --format jsonの出力をjqで加工

`--format json` でJSON形式で出力できるのですが、この場合は `-c` オプションで項目を限定することは出来ませんでした。

```
$ lxc list --format json -c s cent01
[{"architecture":"x86_64","config":{"volatile.base_image":"a027d59858d663fb2bc12b5ba767e92196a4aee8dbb2a607db53d718b91eb5d2","volatile.eth0.hwaddr":"00:16:3e:5f:01:7e","volatile.last_state.idmap":"[{\"Isuid\":true,\"Isgid\":false,\"Hostid\":100000,\"Nsid\":0,\"Maprange\
":65536},{\"Isuid\":false,\"Isgid\":true,\"Hostid\":100000,\"Nsid\":0,\"Maprange\":65536}]"},"created_at":"2016-05-06T18:56:46+09:00","devices":{"root":{"path":"/","type":"disk"}},"ephemeral":false,"expanded_config":{"volatile.base_image":"a027d59858d663fb2bc12b5ba767e9
2196a4aee8dbb2a607db53d718b91eb5d2","volatile.eth0.hwaddr":"00:16:3e:5f:01:7e","volatile.last_state.idmap":"[{\"Isuid\":true,\"Isgid\":false,\"Hostid\":100000,\"Nsid\":0,\"Maprange\":65536},{\"Isuid\":false,\"Isgid\":true,\"Hostid\":100000,\"Nsid\":0,\"Maprange\":65536}
]"},"expanded_devices":{"eth0":{"name":"eth0","nictype":"bridged","parent":"lxdbr0","type":"nic"},"root":{"path":"/","type":"disk"}},"name":"cent01","profiles":["default"],"stateful":false,"status":"Running","status_code":103,"state":null,"snapshots":null}]
```

`sudo apt install jq` で `jq` コマンドをインストールして、それで状態を抜き出すことは可能です。

```
$ lxc list --format json cent01 | jq -r '.[0].status'
Running
```

## お勧めの方法: lxc infoの出力をawkで加工

`lxc list` の場合は指定した文字列は完全一致ではなくて前方一致で表示されました。上記の例のように `cent01` と `cent02` の2つのコンテナがあるときに、 `lxc list -c s cent0` と実行すると以下のようになります。

```
$ lxc list -c s cent0
+---------+
|  STATE  |
+---------+
| RUNNING |
+---------+
| RUNNING |
+---------+
```

これだとどの行がどのコンテナかわからないのでコンテナ名の列も付ける必要があります。

```
$ lxc list -c ns cent0
+--------+---------+
|  NAME  |  STATE  |
+--------+---------+
| cent01 | RUNNING |
+--------+---------+
| cent02 | RUNNING |
+--------+---------+
```

この結果をawkで加工するのでも良いのですが、もっと良いのは `lxc info` コマンドを使うことです。

```
$ lxc info cent01
コンテナ名: cent01
アーキテクチャ: x86_64
作成日時: 2016/05/06 09:56 UTC
状態: Running
タイプ: persistent
プロファイル: default
Pid: 29354
IPアドレス:
  eth0: inet    10.155.92.101   vethG4XSE4
  eth0: inet6   fe80::216:3eff:fe5f:17e vethG4XSE4
  lo:   inet    127.0.0.1
  lo:   inet6   ::1
リソース:
  プロセス数: 10
  メモリ消費量:
    メモリ (現在値): 23.60MB
    メモリ (ピーク): 43.08MB
  ネットワーク使用状況:
    eth0:
      受信バイト数: 24.16kB
      送信バイト数: 8.06kB
      受信パケット: 232
      送信パケット: 88
    lo:
      受信バイト数: 0 bytes
      送信バイト数: 0 bytes
      受信パケット: 0
      送信パケット: 0
```

存在しないコンテナ名を指定するとエラーになります。これは標準エラー出力に出力されています。

```
$ lxc info hoge
エラー: not found
```

シェルスクリプトで加工するには英語出力のほうが良いので `LANG=C` 付きで実行します。

```
$ LANG=C lxc info cent01
Name: cent01
Architecture: x86_64
Created: 2016/05/06 09:56 UTC
Status: Running
Type: persistent
Profiles: default
Pid: 29354
Ips:
  eth0: inet    10.155.92.101   vethG4XSE4
  eth0: inet6   fe80::216:3eff:fe5f:17e vethG4XSE4
  lo:   inet    127.0.0.1
  lo:   inet6   ::1
Resources:
  Processes: 10
  Memory usage:
    Memory (current): 23.60MB
    Memory (peak): 43.08MB
  Network usage:
    eth0:
      Bytes received: 24.58kB
      Bytes sent: 8.56kB
      Packets received: 235
      Packets sent: 93
    lo:
      Bytes received: 0 bytes
      Bytes sent: 0 bytes
      Packets received: 0
      Packets sent: 0
$ LANG=C lxc info hoge
error: not found
```

結局以下のように実行するのがお勧めです。

```
$ LANG=C lxc info cent01 2> /dev/null | awk '$1=="Status:"{print $2}'
Running
```

存在しない場合は空文字列になります。

```
$ LANG=C lxc info hoge 2> /dev/null | awk '$1=="Status:"{print $2}'
```

判定例はこんな感じです。

```
$ [ x`LANG=C lxc info cent01 2> /dev/null | awk '$1=="Status:"{print $2}'` == xRunning ] && echo "container is running"
container is running
$ [ x`LANG=C lxc info hoge 2> /dev/null | awk '$1=="Status:"{print $2}'` == xRunning ] && echo "container is running"
$
```
