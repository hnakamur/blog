---
title: "Apache Traffic ServerのAutestによるテストを高速化"
date: 2025-04-28T01:15:43+09:00
---

## 結果

結論から言うと、並列化無しで1時間46分かかっていたのを、24コアのPCで24並列で5分以下に短縮できました。

正確には記事の最後のログのとおり、269.6秒です。

```
$ python3 -c 'print((60+46)*60/269.6)'
23.590504451038573
```

24並列で1/23.59の時間になったということで、いわゆる[Embarrassingly parallel - Wikipedia](https://en.wikipedia.org/wiki/Embarrassingly_parallel)と言われる理想的なケースです。

試したことをメモしておきます。

## Apache Traffic ServerのAutestによるテストについて

[apache/trafficserver](https://github.com/apache/trafficserver)の[testsディレクトリ](https://github.com/apache/trafficserver/tree/590fb85acf100ba2debdfd117a3701044ae840cc/tests)に含まれるE2Eテストです。[tests/README.md](https://github.com/apache/trafficserver/blob/master/tests/README.md)に説明があります。

このディレクトリ配下の`*.test.py`というファイルがテストケースになっています。2025-04-27時点では379あります。

```
$ find tests -name '*.test.py' | wc -l
379
```

テスト実行用のスクリプトファイルは[tests/autest.sh](https://github.com/apache/trafficserver/blob/590fb85acf100ba2debdfd117a3701044ae840cc/tests/autest.sh)です。

### Reusable Gold Testing System (AuTest)

このテストはReusable Gold Testing System (AuTest) というテスト用エンジンを使って書かれています。

* PyPIのページ：[autest · PyPI](https://pypi.org/project/autest/)
* ソースレポジトリ：[autestsuite / reusable-gold-testing-system — Bitbucket](https://bitbucket.org/autestsuite/reusable-gold-testing-system/src/master/)
* ドキュメント：[Welcome to AuTest’s documentation! — AuTest 1.4.0 documentation](https://autestsuite.bitbucket.io/)

また、trafficserverのレポジトリの[tests/gold_tests/autest-site/](https://github.com/apache/trafficserver/tree/590fb85acf100ba2debdfd117a3701044ae840cc/tests/gold_tests/autest-site)ディレクトリ配下に、trafficserver用の拡張が含まれています。

### Proxy Verifier

一部のテストケースではProxy Verifierというツールも使われています。

* ソースレポジトリ：[yahoo/proxy-verifier](https://github.com/yahoo/proxy-verifier) 

proxy-verifierにはverifier-clientとverifier-serverという実行ファイルが含まれています。

verifier-client -> traficserver -> verfier-server という流れでリクエストを送信・受信して、期待する動作になっているかを確認します。

verifier-clientとverfier-serverはreplayファイルとよばれるyamlファイルを読んで動作します。

verfier-clientはreplayファイルを読んで、そこにかかれたリクエストを順次送信します。verifier-serverはreplayファイルを読んで、そこに書かれたリクエストに対応するリクエストを受信したら、replayファイル内に書かれた対応するレスポンスを返します。

## 現行のCIでの4並列のシャーディング方式

trafficserverのレポジトリにプルリクエストを送るとCIで様々なチェックが走ります。そのうちの1つにJenkins上で4並列のシャーディングで実行するAuTestのテストがあります。

これは[apache/trafficserver-ci](https://github.com/apache/trafficserver-ci)レポジトリ内の[jenkins/github/autest.pipeline#L137-L164](https://github.com/apache/trafficserver-ci/blob/a7645e571311e1e799d37630a6ac0398d9af6b42/jenkins/github/autest.pipeline#L137-L164)の部分が、一部分のテストを実行する処理です。

```bash
testsall=( $( find . -iname "*.test.py" | awk -F'/' '{print $NF}' | awk -F'.' '{print $1}' ) )
# …（略）…
if [ ${SHARDCNT} -le 0 ]; then
        ./autest.sh ${autest_args} || true
else
        testsall=( $(
          for el in  "${testsall[@]}" ; do
            echo $el
          done | sort) )
        ntests=${#testsall[@]}

        shardsize=$((${ntests} / ${SHARDCNT}))
        [ 0 -ne $((${ntests} % ${shardsize})) ] && shardsize=$((${shardsize} + 1))
        shardbeg=$((${shardsize} * ${SHARD}))
        sliced=${testsall[@]:${shardbeg}:${shardsize}}
        ./autest.sh ${autest_args} -f ${sliced[@]} || true

fi
```

まず、`find tests -name '*.test.py'`でテストの一覧のリストを作ります。

4つの実行環境のすべてでSHARDCNT=4としておきます。
SHARDのほうは4つの環境で0、1、2、3と異なる値を設定します。これにより、1つめの環境では最初の4分の1、2つめの環境では次の4分の1、といった感じで分担して実行します。

autestの[--filter (-f)](https://autestsuite.bitbucket.io/usage/cli.html#cmdoption-autest-run-filter)オプションに実行対象のテストを複数指定できるので、それぞれの実行環境（シャード）で上記のように分割したテストを指定して実行します。

ただ、現状ではテストの一覧をテスト名でソートして4分割しているだけなので、実行時間が長いテストが多く含まれるシャードは他のシャードよりも実行時間が長くなってしまいます。

## 一番長いremap_aclテストは10分もかかる

[tests/gold_tests/remap/remap_acl.test.py](https://github.com/apache/trafficserver/blob/590fb85acf100ba2debdfd117a3701044ae840cc/tests/gold_tests/remap/remap_acl.test.py)はremap.config（[10.0.xのドキュメント](https://docs.trafficserver.apache.org/en/10.0.x/admin-guide/files/remap.config.en.html)）のACL (Access Control List)機能のテストです。

これはいくつかの項目のすべての組み合わせのテストを行っていることもあり、実行時間が長く、私の環境では10分かかります。

### trafficserverの起動・停止回数を減らすのを試したが、むしろ遅くなってしまった

[Reduce the execution time of Remap ACL AuTest · Issue #11917 · apache/trafficserver](https://github.com/apache/trafficserver/issues/11917)に複数のテストケースのremap.configを結合して、trafficserverの起動・停止回数を減らせば早くなるのではないかという話が上がっていました。

[hnakamur/trafficserver at make_remap_acl_fast](https://github.com/hnakamur/trafficserver/tree/make_remap_acl_fast)で試してみたのですが、11分47秒とむしろ遅くなってしまいました。クライアントがリクエストを送った後にログファイルをチェックするテストが含まれているため、SIGUSR2のシグナルを送ってログファイルをローテートするように改修したので、その影響かもしれません。が、どこがボトルネックかは計測していないです。

### 単純に分割して別のシャードで並列に実行したら早くなった

テストケースごとにtrafficserverを起動・停止する方式はそのままで、単純に[tests/gold_tests/remap/remap_acl.test.py](https://github.com/apache/trafficserver/blob/590fb85acf100ba2debdfd117a3701044ae840cc/tests/gold_tests/remap/remap_acl.test.py)内のテストケースを4分割して、別のシャードで実行するようにしたところ速くなりました。

試したコードは[hnakamur/trafficserver at split_remap_acl_tests](https://github.com/hnakamur/trafficserver/tree/split_remap_acl_tests)に置いています。

remap_aclを4分割しての実行時間は以下のようになりました。

```
remap_acl_part0 68.0 s
remap_acl_part1 170.9 s
remap_acl_part2 156.3 s
remap_acl_part3 195.9 s
```

単に分割しただけだから当然ですが、合計は約10分で分割前と変わっていません。

また、[tests/gold_tests/h2/http2_flow_control.test.py](https://github.com/apache/trafficserver/blob/590fb85acf100ba2debdfd117a3701044ae840cc/tests/gold_tests/h2/http2_flow_control.test.py)も349.9 sと長いので、これも2分割すると154.5 sと168.3 sになりました。

## テストをIncusで並列実行するPythonスクリプトを書いた

[hnakamur/ats-autest](https://github.com/hnakamur/ats-autest)に置いてます。実際は先にこちらを作って試していました。現行のCIのように最初に分担を決めて実行する方式だと、早く終わったシャードは終了してしまい、効率がいまいちです。そこで複数のワーカーが1つのタスクキューからテスト名を受け取って実行するような方式にしました。

シェルスクリプトよりPythonのasyncioを使ったほうが楽に書けそうだったのでPythonで書いてみました。AuTest自体やtrafficserverのAuTestのテストケースもPythonで書かれているので、それに合わせたというのもあります。とはいえ私はバリバリのPython使いではないので、asyncioも初めて使ったのですがChatGPTにいろいろ聞きつつ公式ドキュメントを見て書きました。できればvenv環境を作らずに手軽に実行できるようにしたいと思って、標準ライブラリだけを使うようにしてみました。

### ソケットの空きポートを探す方式を変更

[autest-on-incus](https://github.com/hnakamur/ats-autest/blob/08a0153913566b5e98358b858e2e2a456a33c860/autest-on-incus)では、各シャードのワーカーがタスクキューから対象のテスト名を1つ受け取るたびに、autestの-fオプションでそのタスクを指定して実行するようにしています。ところが実装して試してみると、`Address already in use`エラーでソケットのリッスンに失敗するケースが多発しました。

trafficserverのAuTestのテストでは[tests/gold_tests/autest-site/ports.py](https://github.com/apache/trafficserver/blob/590fb85acf100ba2debdfd117a3701044ae840cc/tests/gold_tests/autest-site/ports.py)でソケットの空きポートを探しています。これはLinuxの`net.ipv4.ip_local_port_range`の範囲が十分広ければ、その範囲のポート番号を順番に使うという仕組みになっています。

trafficserverのCI環境のようにautestの-fオプションで多数のテストを指定して実行する場合は、この方式のほうだとテストごとに範囲内のポートを順番に使っていくので`Address already in use`エラーが出にくいということです。

一方、autestの-fオプションで1つずつテストを実行する場合は、この方式だと同じポート番号ばかりを使おうとするので、むしろ`Address already in use`エラーが出やすくなってしまいます。

[tests/gold_tests/autest-site/ports.py](https://github.com/apache/trafficserver/blob/590fb85acf100ba2debdfd117a3701044ae840cc/tests/gold_tests/autest-site/ports.py)では`net.ipv4.ip_local_port_range`の範囲がある程度狭くなると、ポート0を指定してリッスンすることで空きポートを探してもらう方式に切り替わるようになっています。

そこで、[autest-on-incus](https://github.com/hnakamur/ats-autest/blob/08a0153913566b5e98358b858e2e2a456a33c860/autest-on-incus)では実行時に`net.ipv4.ip_local_port_range`の範囲の範囲を狭めるようにしています。

ポート0で空きポートを探す方式で`Address already in use`エラーが出にくくはなりましたが、完全には無くなりませんでした。そこで、テストが一通り終わったら、失敗したテストだけをリトライする仕組みを追加しました。デフォルトで最大3回までリトライします。

## 長いテストを先に実行するようにソート順を調整

1つのタスクキューにテスト名を流し込む方式にしても、テスト一覧を単純にアルファベット順にソートして流し込むと、最後のほうに長いテストがあるとその分遅くなってしまいます。

具体的には[tests/gold_tests/next_hop/zzz_strategies_peer/zzz_strategies_peer.test.py](https://github.com/apache/trafficserver/blob/master/tests/gold_tests/next_hop/zzz_strategies_peer/zzz_strategies_peer.test.py)と[tests/gold_tests/next_hop/zzz_strategies_peer2/zzz_strategies_peer2.test.py](https://github.com/apache/trafficserver/blob/master/tests/gold_tests/next_hop/zzz_strategies_peer2/zzz_strategies_peer2.test.py)は50秒程度とそこそこ長いので早めに実行するほうが良いことが分かりました。

[autest-on-incus](https://github.com/hnakamur/ats-autest/blob/08a0153913566b5e98358b858e2e2a456a33c860/autest-on-incus)ではテストごとの実行時間もログ出力するようにしてあります。一度実行してみて長いテストをtier1、tier2にグルーピングして、ソートの際に先頭に持ってくるようにしました。

[autest-on-incus#L310-L325](https://github.com/hnakamur/ats-autest/blob/08a0153913566b5e98358b858e2e2a456a33c860/autest-on-incus#L310-L325)で実装しています。

```python
def is_long_test_tier1(test):
    return re.match(r'(remap_acl|http2_flow_control)', test)


def is_long_test_tier2(test):
    return re.match(
        r'(parent-retry|stale_response|proxy_protocol|quick_server|active_timeout|'
        r'ja3_fingerprint|dns_down_nameserver|regex_revalidate_miss|zzz_strategies_peer|'
        r'proxy_serve_stale_dns_fail|config|cache-control|number_of_redirects|ip_allow|'
        r'dns_ttl|inactive_timeout|strategies_ch2|background_fill|chunked_encoding|x_remap|'
        r'tls_client_alpn_configuration|per_client_connection_max|traffic_ctl_config_output)', test)


def sort_tests(tests):
    # Move remap_acl to first since it takes a long time to run
    return sorted(tests, key=lambda x: (f'01{x}' if is_long_test_tier1(x) else f'02{x}' if is_long_test_tier2(x) else x))
```

これらの改修により、冒頭の結論に書いたとおり5分以下に短縮することが出来ました。

以下はログの抜粋です。round #1では384個のテストを実行して、1つ失敗したためround #2でリトライし成功していたことがわかります。

```
2025-04-28 00:26:02.619 INFO === start running tests ===
2025-04-28 00:26:11.259 INFO === running round #1 of tests, count=384 ===
2025-04-28 00:26:11.313 INFO worker 0 http2_flow_control_part1 start
2025-04-28 00:26:11.315 INFO worker 14 http2_flow_control_part2 start
2025-04-28 00:26:11.317 INFO worker 13 remap_acl_part0 start
2025-04-28 00:26:11.318 INFO worker 10 remap_acl_part1 start
2025-04-28 00:26:11.319 INFO worker 20 remap_acl_part2 start
2025-04-28 00:26:11.327 INFO worker 16 remap_acl_part3 start
…（略）…
2025-04-28 00:30:14.100 INFO worker 20 url_sig FAILED elapsed: 9.8 (s)
2025-04-28 00:30:21.276 INFO worker 22 uri passed elapsed: 17.9 (s)
2025-04-28 00:30:23.923 INFO worker 2 x_cache_info passed elapsed: 18.1 (s)
2025-04-28 00:30:24.327 INFO worker 3 x_effective_url passed elapsed: 18.3 (s)
2025-04-28 00:30:24.328 INFO finished running round #1 of tests, failed_test count=1, elapsed: 253.1 (s)
2025-04-28 00:30:24.328 INFO === running round #2 of tests, count=1 ===
2025-04-28 00:30:24.378 INFO worker 6 url_sig start
2025-04-28 00:30:29.602 INFO worker 6 url_sig passed elapsed: 5.2 (s)
2025-04-28 00:30:29.602 INFO finished running round #2 of tests, failed_test count=0, elapsed: 5.3 (s)
2025-04-28 00:30:32.261 INFO deleted shards, elapsed: 2.7 (s)
2025-04-28 00:30:32.267 INFO cleaned passed directories, elapsed: 0.0 (s)
2025-04-28 00:30:32.267 INFO === finished running tests. elapsed: 269.6 (s) ===
```
