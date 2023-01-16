---
title: "Apache Traffic Serverのautest.sh"
date: 2023-01-16T16:45:13+09:00
---
## はじめに

[trafficserver 9.2.0-rc0](https://github.com/apache/trafficserver/releases/tag/9.2.0-rc0)の[tests](https://github.com/apache/trafficserver/tree/9.2.0-rc0/tests)ディレクトリのautest.shを実行する際のメモです。

[Apache Traffic Server](https://trafficserver.apache.org/)の[The ASF Slack](https://the-asf.slack.com/)で[masaori335](https://github.com/masaori335)さんにいろいろ教えていただきました。ありがとうございました！

Docker上のUbuntu 22.04 LTSと20.04 LTSでautest.shを動かす手順を
[GitHub - hnakamur/trafficserver-run-autest-docker](https://github.com/hnakamur/trafficserver-run-autest-docker)
においています。

## DockerでIPv6を使う

autestのテストでIPv6が必要になるので、DockerでIPv6を使えるようにする必要があります。以下のページを参考にしました。

1. [Enable IPv6 support | Docker Documentation](https://docs.docker.com/config/daemon/ipv6/)
2. [Enable IPv6 for Docker containers on Ubuntu 18.04 | Medium](https://medium.com/@skleeschulte/how-to-enable-ipv6-for-docker-containers-on-ubuntu-18-04-c68394a219a2)
3, [DockerでIPv6化 – mahori blog](https://mahori.jp/docker-ipv6/)

1の公式ドキュメントでは[IPv6アドレス - Wikipedia](https://ja.wikipedia.org/wiki/IPv6%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9)の[文書記述用アドレスプレフィックス](https://ja.wikipedia.org/wiki/IPv6%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9#.E6.96.87.E6.9B.B8.E8.A8.98.E8.BF.B0.E7.94.A8.E3.82.A2.E3.83.89.E3.83.AC.E3.82.B9.E3.83.97.E3.83.AC.E3.83.95.E3.82.A3.E3.83.83.E3.82.AF.E3.82.B9)のアドレスの`/32`を`/64`にしたアドレスが使われています。

実際にどういうアドレスを使えばよいかですが、2のドキュメントによるとグローバルのIPv6アドレスを使うと設定は簡単ですが、インターネットからDockerコンテナにアクセスできてしまうとのことでした。

そこで2と3のページを参考に`/etc/docker/daemon.json`は以下のようにしました。

```
{
  "ipv6": true,
  "fixed-cidr-v6": "fd6d:6168:6f72:6900::/64"
}
```

その後dockerサービスを再起動します。

```
sudo systemctl restart docker
```

最後にIPv6のNATを設定します。

```
ip6tables -t nat -A POSTROUTING -s fd6d:6168:6f72:6900::/64 ! -o docker0 -j MASQUERADE
```

その後

```
docker network inspect bridge
```

で確認するとIPAMのConfigにIPv4とIPv6のエントリが出てきました。

```
            "Config": [
                {
                    "Subnet": "172.17.0.0/16",
                    "Gateway": "172.17.0.1"
                },
                {
                    "Subnet": "fd6d:6168:6f72:6900::/64"
                }
            ]
```

この後、コンテナを作成して `docker inspect <コンテナID>` で確認するとNetworkSettingsのGlobalIPv6AddressにIPv6アドレスがついていました。

## autestのレポジトリ

PyPIのプロジェクトは[autest · PyPI](https://pypi.org/project/autest/)で、ソースレポジトリは[autestsuite / reusable-gold-testing-system — Bitbucket](https://bitbucket.org/autestsuite/reusable-gold-testing-system/src/master/)です。

今回はautestのソースまでは見ていませんが、一応メモ。

## trafficserverのJenkinsでのautest

[apache/trafficserver-ci](https://github.com/apache/trafficserver-ci)にCI用のレポジトリがあります。

9.2.xのautestの実行結果は
https://ci.trafficserver.apache.org/view/9.2.x/job/9.2.x/job/autest/
で見られます。

実行するテストを分けて4つのジョブを並列で実行しています。左のジョブ一覧で`9.2.x 0of4`のリンクをクリック後、左メニューの`Pipeline Steps`を押すとパイプラインが見られます。configureとmakeをしている箇所を見て[apache/trafficserver-ci](https://github.com/apache/trafficserver-ci)で検索すると
[jenkins/github/autest.pipeline](https://github.com/apache/trafficserver-ci/blob/377c7232f3b90a0189a72ccd792da3de5b407b0d/jenkins/github/autest.pipeline)に対応するようです。

先頭のagentのdockerの箇所を見ると`image 'ci.trafficserver.apache.org/ats/rockylinux:8'`となっていて、
[docker/rockylinux8/](https://github.com/apache/trafficserver-ci/tree/377c7232f3b90a0189a72ccd792da3de5b407b0d/docker/rockylinux8)の[docker/rockylinux8/Dockerfile](https://github.com/apache/trafficserver-ci)に対応しているようです。

## autest.shの--sandboxオプションを指定すると失敗したテストのログなどが残る

`-C none`([Command Line options — AuTest 1.4.0 documentation](https://autestsuite.bitbucket.io/usage/cli.html)参照)をつけると成功したテストのログなども残ります。

`-f テスト名`で実行するテストをフィルタリングできます。テスト名はファイル名に対応しています。例えば`chunked_encoding`というテストなら

```
~/ghq/github.com/apache/trafficserver-9.2.0-rc0$ find ./tests -name 'chunked_encoding.test.py'
./tests/gold_tests/chunked_encoding/chunked_encoding.test.py
```
のように探します。

## テスト失敗のログ

例としてchunked_encodingが失敗したログを見てみます。

テストのファイルは[tests/gold_tests/chunked_encoding/chunked_encoding.test.py](https://github.com/apache/trafficserver/blob/9.2.0-rc0/tests/gold_tests/chunked_encoding/chunked_encoding.test.py)です。`tr = Test.AddTestRun()`が5回出てくるので5つのステップが追加されています([Local objects types](https://autestsuite.bitbucket.io/basics/general_design.html#local-objects-types)の`TestRun`がステップに対応)。

テストのログで見ると以下のようになっていて`.`が成功したステップで`F`が失敗したステップです。

```
Running Test chunked_encoding:....F Failed
```

ログの後ろの方に成功/失敗の詳細が出力されています。

```
 Test: chunked_encoding: Failed
    File: chunked_encoding.test.py
    Directory: /src/trafficserver/tests/gold_tests/chunked_encoding
   Setting up : recycling port: 61178, queue size: 999 - Passed
…(略)…
   Run: 4-tr: Failed
     Setting up : Copying 'server4.sh' to 'None' - Passed
     Setting up : Copying 'case4.sh' to 'None' - Passed
     Time-Out : TestRun finishes within expected time - Passed
        Reason: Returned value: 1.1100995540618896 < 5.0
     Starting TestRun 4-tr : No Issues found - Passed
        Reason: Started!
     Process: Default: Failed
       Test : Checking that ReturnCode == 0 - Failed
          Reason: Returned Value 1 != 0
       Time-Out : Process finishes within expected time - Passed
          Reason: Returned value: 1.0053956508636475 < 600.0
       file /src/autest-sandbox/chunked_encoding/_output/4-tr-Default/stream.all.txt : Response should not include content length - Passed
          Reason: Contents of /src/autest-sandbox/chunked_encoding/_output/4-tr-Default/stream.all.txt excludes expression
```

今回は`Run: 4-tr`がFailedで、詳細は`Test : Checking that ReturnCode == 0`であるべきところが1が返ってきたため失敗となったことがわかります。

## sandbox内のディレクトリ・ファイル構成

例えば `--sandbox /src/autest-sandbox -C none -f chunked_encoding`をつけて実行した場合、`/src/autest-sandbox/chunked_encoding/`に以下のようにディレクトリが残ります。

```
# ls -F /src/autest-sandbox/chunked_encoding/
_output/  case4.sh  outserver4  server/  server2/  server3/  server4.sh  smuggle-client*  ts/
```

`server`, `server2`, `server3`, `ts`フォルダは[tests/gold_tests/chunked_encoding/chunked_encoding.test.py#L104-L108](https://github.com/apache/trafficserver/blob/9.2.0-rc0/tests/gold_tests/chunked_encoding/chunked_encoding.test.py#L104-L108)の`StartBefore`で起動しているオリジンサーバとtrafficserverにプロセスに対応します。

```
tr.Processes.Default.StartBefore(server)
tr.Processes.Default.StartBefore(server2)
tr.Processes.Default.StartBefore(server3)
# Delay on readiness of our ssl ports
tr.Processes.Default.StartBefore(Test.Processes.ts)
```

`ts/`フォルダにはtrafficserverの設定ファイルやログファイルが含まれています。
```
# ls -F /src/autest-sandbox/chunked_encoding/ts/
bin/  cache/  config/  log/  plugin/  runtime/  ssl/  storage/
```

`_output/`フォルダは以下のようになっています。

```
# # ls -F /src/autest-sandbox/chunked_encoding/_output/
0-tr-Default/  4-tr-Default/              chunked_encoding-ts/
1-tr-Default/  chunked_encoding-server/   condition-CheckOutput-86fe/
2-tr-Default/  chunked_encoding-server2/
3-tr-Default/  chunked_encoding-server3/
```


例えば`0-tr-Default`フォルダの下は以下のようなファイルが入っています。

```
# ls /src/autest-sandbox/chunked_encoding/_output/0-tr-Default/                                                                    
command.txt  stream.all.txt    stream.error.txt   stream.stdout.txt   stream.warning.txt
replay.sh    stream.debug.txt  stream.stderr.txt  stream.verbose.txt
```

## sandboxのディレクトリでのテストの再実行

`replay.sh`でリプレイ実行できます。実行パーミションがついていないので`bash`をつけて実行する必要があります。

まず`docker run --rm -it イメージ名 bash`でコンテナを起動しつつ入って

```
cd /src/autest-sandbox/chunked_encoding
bash _output/chunked_encoding-server/replay.sh
```
でオリジンサーバ`server`を起動します。

別の端末で`docker exec -it $(docker ps -lq) bash`で同じコンテナに入って
```
cd /src/autest-sandbox/chunked_encoding
bash _output/chunked_encoding-server2/replay.sh
```
で`server2`を起動します。

別の端末で`docker exec -it $(docker ps -lq) bash`で同じコンテナに入って
```
cd /src/autest-sandbox/chunked_encoding
bash _output/chunked_encoding-server3/replay.sh
```
で`server3`を起動します。

別の端末で`docker exec -it $(docker ps -lq) bash`で同じコンテナに入って
```
cd /src/autest-sandbox/chunked_encoding
bash _output/chunked_encoding-ts/replay.sh
```
でtrafficserverを起動します。

さらに別の端末で`docker exec -it $(docker ps -lq) bash`で同じコンテナに入って
```
cd /src/autest-sandbox/chunked_encoding
seq 0 4 | xargs -I {} bash _output/{}-tr-Default/replay.sh
```
でテストを実行します。

以下のような出力になりました。
```
# seq 0 4 | xargs -I {} bash _output/{}-tr-Default/replay.sh
…(略)…
microserverapachetrafficserver*   Trying 127.0.0.1:61179...                                  
* Connected to 127.0.0.1 (127.0.0.1) port 61179 (#0)                                         
> POST / HTTP/1.1                             
> Host: www.yetanotherexample.com
> User-Agent: curl/7.81.0
> Accept: */*                                 
> Transfer-Encoding: chunked
> Content-Type: application/x-www-form-urlencoded                                            
>                                             
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK                             
< Server: ATS/9.2.0                           
< Date: Mon, 16 Jan 2023 11:18:25 GMT
< Age: 0                                      
< Transfer-Encoding: chunked
< Connection: keep-alive
<                                             
* Connection #0 to host 127.0.0.1 left intact
microserverapachetrafficserverNcat: bind to :::61178: Address already in use. QUITTING.      
using address: 127.0.0.1 and port: 61181
Send request                                  
Received 128 bytes HTTP/1.1 200 
Date: Mon, 16 Jan 2023 11:18:27 GMT
Age: 1                                        
Transfer-Encoding: chunked
Connection: close                             
Server: ATS/9.2.0                             


Received 25 bytes F                           
123456789012345                               
0                                             


./case4.sh: 20: kill: No such process
```

`bind to :::61178: Address already in use. QUITTING.`のエラーが問題のようです。

61178で検索してみると

```
# grep -r 61178 .                       
./ts/config/remap.config:map / http://127.0.0.1:61178
./ts/log/traffic.out:[Jan 16 08:47:38.876] [ET_NET 15] DEBUG: <URL.cc:1730 (url_describe)> (http)       PORT: "61178", PORT_LEN: 5, PORT_NUM: 61178
…(略)…
./ts/log/traffic.out:[Jan 16 11:18:27.004] [ET_NET 0] DEBUG: <HttpSessionManager.cc:491 (removeSession)> (http_ss) Remove session 0x7f51680b9740 127.0.0.1:61178 m_fqdn_pool size=1 m_ip_p
ool_size=1
./outserver4:Host: 127.0.0.1:61178
./_output/4-tr-Default/command.txt:Command= sh ./case4.sh 61181 61178
./_output/4-tr-Default/replay.sh:sh ./case4.sh 61181 61178
```

`case4.sh`の中身は以下のようになっていました。

```
# cat case4.sh 
…(略)…
nc -l ${2} -o outserver4 -c "sh ./server4.sh" &
sleep 1
./smuggle-client 127.0.0.1 ${1}
kill %1
```

ここでncが61178番ポートでリッスンするようです。

しばらく待ってから再度テストのステップを実行してみると、出力が変わりました。

```
# seq 0 4 | xargs -I {} bash _output/{}-tr-Default/replay.sh
…(略)…
microserverapachetrafficserver*   Trying 127.0.0.1:61179...
* Connected to 127.0.0.1 (127.0.0.1) port 61179 (#0)
> POST / HTTP/1.1
> Host: www.yetanotherexample.com
> User-Agent: curl/7.81.0
> Accept: */*
> Content-Length: 11
> Content-Type: application/x-www-form-urlencoded
> 
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Server: ATS/9.2.0
< Date: Mon, 16 Jan 2023 11:22:39 GMT
< Age: 0
< Transfer-Encoding: chunked
< Connection: keep-alive
< 
* Connection #0 to host 127.0.0.1 left intact
microserverapachetrafficserver*   Trying 127.0.0.1:61179...
* Connected to 127.0.0.1 (127.0.0.1) port 61179 (#0)
> POST / HTTP/1.1
> Host: www.yetanotherexample.com
> User-Agent: curl/7.81.0
> Accept: */*
> Transfer-Encoding: chunked
> Content-Type: application/x-www-form-urlencoded
> 
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Server: ATS/9.2.0
< Date: Mon, 16 Jan 2023 11:22:39 GMT
< Age: 0
< Transfer-Encoding: chunked
< Connection: keep-alive
< 
* Connection #0 to host 127.0.0.1 left intact
microserverapachetrafficserverusing address: 127.0.0.1 and port: 61181
Send request
Received 128 bytes HTTP/1.1 200 
Date: Mon, 16 Jan 2023 11:22:40 GMT
Age: 0
Transfer-Encoding: chunked
Connection: close
Server: ATS/9.2.0


Received 25 bytes F
123456789012345
0


./case4.sh: 20: kill: No such process

root@f16ca3320b70:/src/autest-sandbox/chunked_encoding# echo $?
123
```

```
# pgrep -f '(traffic_server|microserver)' | xargs -r ps uwwf -p
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
nobody       145  3.1  0.1 2024184 85840 pts/4   Sl+  11:18   0:21 traffic_server --bind_stderr /src/autest-sandbox/chunked_encoding/ts/log/traffic.out --bind_stdout /src/autest-sandbox/chunked_encoding/ts/log/traffic.out
root          94  0.0  0.0 173012 15824 pts/2    Sl+  11:13   0:00 /root/.local/share/virtualenvs/tests-L5-scKRl/bin/python /root/.local/share/virtualenvs/tests-L5-scKRl/bin/microserver --data-dir /src/autest-sandbox/chunked_encoding/server3 --ip_address 127.0.0.1 --lookupkey {PATH} --port 61187
root          79  0.0  0.0 173456 17316 pts/1    Sl+  11:12   0:00 /root/.local/share/virtualenvs/tests-L5-scKRl/bin/python /root/.local/share/virtualenvs/tests-L5-scKRl/bin/microserver --data-dir /src/autest-sandbox/chunked_encoding/server2 --ip_address 127.0.0.1 --lookupkey {PATH} --ssl --key /src/trafficserver/tests/gold_tests/autest-site/../../tools/microserver/ssl/server.pem --cert /src/trafficserver/tests/gold_tests/autest-site/../../tools/microserver/ssl/server.crt --s_port 61186
root          76  0.0  0.0 173012 15364 pts/0    Sl+  11:12   0:00 /root/.local/share/virtualenvs/tests-L5-scKRl/bin/python /root/.local/share/virtualenvs/tests-L5-scKRl/bin/microserver --data-dir /src/autest-sandbox/chunked_encoding/server --ip_address 127.0.0.1 --lookupkey {PATH} --port 61185
```

そこで
```
# nc -l 61178 -o outserver4 -c "sh ./server4.sh"                                                                                  
```
と実行して、さらに別の端末を起動して`./smuggle-client 127.0.0.1 61181`を実行すると
```
# ./smuggle-client 127.0.0.1 61181
using address: 127.0.0.1 and port: 61181
Send request
Received 128 bytes HTTP/1.1 200 
Date: Mon, 16 Jan 2023 11:32:27 GMT
Age: 0
Transfer-Encoding: chunked
Connection: close
Server: ATS/9.2.0


Received 25 bytes F
123456789012345
0


```
となり、`nc`のほうは終了していました。どちらも`echo $?`で確認すると終了コードは0でした。


ncの引数に指定している`server4.sh`と`outserver4`は以下のような内容でした。

```
# tail -2 server4.sh 
printf "HTTP/1.1 200\r\nTransfer-encoding: chunked\r\n\r\n"
printf "F\r\n123456789012345\r\n0\r\n\r\n"
```

```
# cat outserver4
GET / HTTP/1.1
Host: 127.0.0.1:61178
Client-ip: 127.0.0.1
X-Forwarded-For: 127.0.0.1
Via: https/1.1 traffic_server[7bb817a4-f398-4af8-b7a7-529823a85330] (ApacheTrafficServer/9.2.0)
Transfer-Encoding: chunked

0

HTTP/1.1 200
Transfer-encoding: chunked

F
123456789012345
0

```

```
# cat case4.sh 
…(略)…
nc -l ${2} -o outserver4 -c "sh ./server4.sh" &
sleep 1
./smuggle-client 127.0.0.1 ${1}
kill %1
```
を見返すと、smuggle-clientが終了してkillする前にncが終了して`kill: No such process`になったようです。

## 以下細かいメモ

### ncはncatパッケージのを使う

今日知ったのですがUbuntuのncは、netcat-openbsd、netcat-traditional、ncatというパッケージがあり、`-w`オプションの挙動が違います。
trafficserverのautestではncatを使う必要があります。

ncatでは`-w`は接続タイムアウトですが、他2つでは接続と通信合わせてのタイムアウトです。
`-w 1`として標準入力から送信するリクエストを流し込むとncatはレスポンスを受け取るとすぐ終了しますが、他2つではレスポンスを受け取っても1秒経たないと終了しませんでした(テストではサーバ側は`Connection: keep-alive`を返すようになっていました)。

ncatを使え、以上なのですが、ついでにメモ。

netcat-openbsdだと`-N` (Shutdown the network socket after EOF stdin)を指定すればすぐ終了しました。netcat-traditionalだと`-q secs` (quit after EOF on stdin and delay of secs)というのがありました。試してみると`-q 0`だとレスポンスが全く表示されず、`-q 1`だとレスポンスは表示されるが1秒待つことなくすぐ終了しました。

trafficserverのautestではncの`-o`を使いますが、netcat-openbsdのncは`-o`は非対応です。netcat-traditionalにはあります。

### pipenvはautestではrootユーザで実行

[Pipenv: Python Dev Workflow for Humans — pipenv 2022.12.20.dev0 documentation](https://pipenv.pypa.io/en/latest/)によると

```
pip install --user pipenv
```

と一般ユーザでインストールするのが推奨とのことです。

ただ、それでautestを実行するとroot権限が必要なテストをスキップする旨のメッセージが出たためrootでインストールしてrootで実行するようにしました。
