---
title: "Prometheusのexporterのメトリックをcarbon-clickhouseに登録する"
date: 2024-12-02T14:22:25+09:00
---

## はじめに

Prometheusのexporterのメトリックを[carbon-clickhouse](https://github.com/go-graphite/carbon-clickhouse)に登録しようとして調べてみた際のメモです。
実際に調べたのは、[prometheus/node_exporter: Exporter for machine metrics](https://github.com/prometheus/node_exporter)だけなので、他のexporterだと違うことがあるかもしれません。

[prometheus/prometheus: The Prometheus monitoring system and time series database.](https://github.com/prometheus/prometheus)のソースも拾い読みしましたが、レポジトリがいろいろ分かれていて、正しい箇所を見れているかは不明です。

## Prometheusのexporterが出力するメトリックの形式

### テキスト形式

* [Data model | Prometheus](https://prometheus.io/docs/concepts/data_model/)にメトリック名とラベルの形式について書かれている。
* 例：`metric_name{label1="value1",label2="value2"} 123`
* メトリック名は`[a-zA-Z_:][a-zA-Z0-9_:]*`の正規表現にマッチすること。
* ラベル名は`[a-zA-Z_][a-zA-Z0-9_]*`の正規表現にマッチすること。
  * `__`で始まる名前は内部用で予約されているので使用禁止。
* ラベルの値は任意のUnicodeの文字を使用可。
  * `"`と`\`（実際は任意の文字）は`\`でエスケープ可能。
    https://github.com/prometheus/prometheus/blob/v2.55.1/model/textparse/promlex.l#L77
    https://github.com/prometheus/prometheus/blob/v3.0.1/model/textparse/promlex.l#L81
* ラベルの値が空文字列の場合は、そのラベルを指定しないのと同じ扱いになる。
* [`prompaser.nextToken()`](https://github.com/prometheus/prometheus/blob/v2.55.1/model/textparse/promparse.go#L265-L273)でTABと半角空白は読み飛ばす。  
  * 上記の例だと `metric_name { label1 = "value1" , label2 = "value2" } 123` のように空白を入れても同じ内容になる。

### Protocol Buffers形式

Protocol Buffersは以下protobufと略します。

* `Accept`ヘッダーに`application/vnd.google.protobuf;proto=io.prometheus.client.MetricFamily;encoding=delimited`と指定して`http://${node_exporter_address}:9100/metrics`にリクエストを送ると、Protocol Buffers形式のレスポンスボディが返ってくる。
  * この値は[github.com/prometheus/common/expfmtパッケージの定数](https://pkg.go.dev/github.com/prometheus/common@v0.60.1/expfmt#pkg-constants)の`FmtProtoDelim`に定義されているがdeprecated。
    * 代わりに`expfmt.NewFormat(expfmt.TypeProtoDelim)`を使えとのこと。
    * 戻り値の型[expfmt.Format](https://pkg.go.dev/github.com/prometheus/common@v0.60.1/expfmt#Format)は`string`に`typedef`されているので、文字列に変換するには`string(Formatの値)`で良い。
  * レスポンスボディは[github.com/prometheus/client_model/go.MetricFamily](https://pkg.go.dev/github.com/prometheus/client_model@v0.6.1/go#MetricFamily)のインスタンスが複数並べられた形式になる。
* [prometheus/client_model: Data model artifacts for Prometheus.](https://github.com/prometheus/client_model)
  * Deprecation noteを以下に抜粋。
  * Prometheus v2.0.0からPrometheusサーバーはprotobuf形式でのデータ取り込みはしなくなっていた。
  * そのため、Go以外の言語用のライブラリではprotobufサポートは外された。
  * しかしGo用の[prometheus/client_golang: Prometheus instrumentation library for Go applications](https://github.com/prometheus/client_golang)はprotobufサポートが消されずに残っている。
  * v2.40.0からネイティブヒストグラムの実験的なサポートがprotobuf形式に追加されたため、設定で有効にすればPrometheusサーバーはprotobuf形式でのデータ取り込みが出来るようになった。

## carbon-clickhouseへのメトリック登録

[go-graphite/carbon-clickhouse: Graphite metrics receiver with ClickHouse as storage](https://github.com/go-graphite/carbon-clickhouse)

### Graphiteのplaintext形式でのデータ登録

* [Feeding In Your Data — Graphite 1.2.0 documentation](https://graphite.readthedocs.io/en/latest/feeding-carbon.html#getting-your-data-into-graphite)
  * `メトリックのパス 値 タイムスタンプ\n`という形式でデータを送って登録（複数行指定可能）。
* メトリックパスはタグも使える。
  * [Graphite Tag Support — Graphite 1.2.0 documentation](https://graphite.readthedocs.io/en/latest/tags.html)
  * 例：`my.series_name;tag1=value1;tag2=value2`
  * タグ名は1文字以上で`;!^=`以外のASCII文字。
  * タグの値は1文字以上で`;`以外のASCII文字。先頭に`~`は禁止。
  * タグ名と値にUTF-8文字は動くかもしれないが、あまりテストされていない。
  * 少なくともplaintext形式でデータ登録する際は、タグ名はタグの値に半角空白は含められない。
    * [receiver/Base.PlainParseLine](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/receiver/plain.go#L53-L63)で行頭から半角空白を探しているため。
    * なお、本家のGraphiteプロジェクトのcarbonでも
      https://github.com/graphite-project/carbon/blob/1.1.10/lib/carbon/protocols.py#L196
      で行頭から半角空白で分割している。
    * [pickleプロトコル](https://graphite.readthedocs.io/en/latest/feeding-carbon.html#the-pickle-protocol)なら含められるかもしれない。
      * carbon-clickhouseでも[receiver/pickle.go](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/receiver/pickle.go)で実装されている。
      * ただし、登録した値をクエリで参照する際に問題が起きる可能性もあるので、半角空白は含めないほうが無難。
* carbon-clickhouseへのデータ登録は[設定例](https://github.com/go-graphite/carbon-clickhouse?tab=readme-ov-file#configuration)の`[udp]`か`[tcp]`の設定で指定したアドレスに上記の形式でデータを送ればよい。
  * この設定例を見ると[carbon.proto](https://github.com/lomik/carbon-clickhouse/blob/master/grpc/carbon.proto)のprotobuf形式で`[grpc]`の設定のアドレスに送るという手もある。

### Prometheusの形式でのメトリック登録

* carbon-clickhouseへのデータ登録は[設定例](https://github.com/go-graphite/carbon-clickhouse?tab=readme-ov-file#configuration)の`[prometheus]`の設定を`enabled = true`に変更し、ここで指定したアドレスにデータを送ればよい。
  * carbon-clickhouseで受信する実装は[receiver/PrometheusRemoteWrite.ServeHTTP](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/receiver/prometheus.go#L173-L191)にある。
    * リクエストボディをsnappyで解凍した後、[helper/prompb/remote.proto](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/helper/prompb/remote.proto)の[WriteRequest](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/helper/prompb/remote.proto#L21-L23)として解釈している。
    * データ送信側は`WriteRequest`のインスタンスを作り[Marshal](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/helper/prompb/remote.pb.go#L147-L155)メソッドでバイト列にシリアライズし、snappyで圧縮したものを送ればよい。

## ClickHouseでのデータ格納形式

* carbon-clickhouseでは[GraphiteMergeTree](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/graphitemergetree)テーブルエンジンを使用。
  * Graphite形式で登録しても、Prometheus形式で登録しても、格納される先は同じ。
  * テーブル定義例
    * [ClickHouse configuration](https://github.com/go-graphite/carbon-clickhouse?tab=readme-ov-file#clickhouse-configuration)
    * [go-graphite/graphite-clickhouse-tldr: Preconfigured graphite-web with ClickHouse backend](https://github.com/go-graphite/graphite-clickhouse-tldr)の[init.sql](https://github.com/go-graphite/graphite-clickhouse-tldr/blob/f2bf2f14bc58797fd111d5ffd067cd81fa05e399/init.sql)
    * [We have been developing our monitoring system for two years. Click to… | by Vladimir Kolobaev | AvitoTech | Medium](https://medium.com/avitotech/we-have-been-developing-our-monitoring-system-since-two-years-ago-click-to-63d399c61192)
  * `Path`カラムに格納されるメトリック名の形式は[GraphiteMergeTree](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/graphitemergetree)の`rule_type`のコードブロックの`tagged`に説明がある。
    * 具体的には`someName?tag1=value1&tag2=value2&tag3=value3`という形式になる。

## Goでcarbon-clickhouseのパッケージを使う際の注意

レポジトリのURLは https://github.com/go-graphite/carbon-clickhouse だが、[go.mod#L1](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/go.mod#L1)で`module github.com/lomik/carbon-clickhouse`と指定されている。Goからこのパッケージを使う際にはこのmoduleのパスのほうを指定する必要があるので要注意。

## データ参照はgrahite-clickhouseを使う

* [go-graphite/graphite-clickhouse: Graphite cluster backend with ClickHouse support](https://github.com/go-graphite/graphite-clickhouse)
* [doc/config.md](https://github.com/go-graphite/graphite-clickhouse/blob/v0.14.0/doc/config.md)の`[common]`のアドレスでGraphite形式、`[prometheus]`のアドレスでPrometheus形式でデータが取得できる。
  * [Graphite data source](https://grafana.com/docs/grafana/latest/datasources/graphite/)と[Prometheus data source](https://grafana.com/docs/grafana/latest/datasources/prometheus/)で設定すればGrafanaのデータソースとして使える。
* Graphiteデータソースでクエリを書く場合
  * [Graphite Tag Support](https://graphite.readthedocs.io/en/latest/tags.html)の[Querying](https://graphite.readthedocs.io/en/latest/tags.html#querying)の項を参照。
  * まず`seriesByTag('name=metric_name')`や`seriesByTag('tag1=value1')`などを使い、そこから必要に応じてさらに対象を絞ったり加工しつつ参照する。

## 試してみたコード

### 環境構築用Ansible playobok

[hnakamur/carbon-clickhouse-ansible-playbook](https://github.com/hnakamur/carbon-clickhouse-ansible-playbook)

  * [create_incus_containers.sh](https://github.com/hnakamur/carbon-clickhouse-ansible-playbook/blob/main/create_incus_containers.sh)で[Incus](https://linuxcontainers.org/ja/incus/)のコンテナを作り、このplaybookを実行する。
  * [graphite-clickhouse](https://github.com/go-graphite/graphite-clickhouse)のREADMEのTL;DRセクションの[Preconfigured docker-compose](https://github.com/lomik/graphite-clickhouse-tldr)を参考にした。

### exporterからのデータをcarbon-clickhouseに登録するサーバー

https://github.com/hnakamur/prometheus-exporter-to-carbon-clickhouse-relay

  * [prometheus/node_exporter](https://github.com/prometheus/node_exporter)を稼働中に、これを動かすとnode_exporterからメトリックを読み取ってcarbon-clickhouseに登録する。
  * 現状はとりあえず動いたレベル。今後いろいろ変更するかも。
  * [github.com/prometheus/client_model/go.MetricFamily](https://pkg.go.dev/github.com/prometheus/client_model@v0.6.1/go#MetricFamily)から[WriteRequest](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/helper/prompb/remote.proto#L21-L23)の[TimeSeries](https://github.com/go-graphite/carbon-clickhouse/blob/v0.11.8/helper/prompb/types.proto#L26-L29)への変換は[convertOneMetricFamilyToTimeSeries](https://github.com/hnakamur/prometheus-exporter-to-carbon-clickhouse-relay/blob/280b7e54430e8dbaf23e4696adc0a26c6670a1e6/main.go#L222-L330)関数で実装。
    * [Metric types | Prometheus](https://prometheus.io/docs/concepts/metric_types/)（コードでは[client_model/io/prometheus/client/metrics.proto](https://github.com/prometheus/client_model/blob/773bf3b3af440c3e678fc5fa7a0bdb3bdc0b94e0/io/prometheus/client/metrics.proto)の[enum MetricType](https://github.com/prometheus/client_model/blob/773bf3b3af440c3e678fc5fa7a0bdb3bdc0b94e0/io/prometheus/client/metrics.proto#L27-L40)）に応じて変換。
      * `COUNTER`、`GAUGE`、`SUMMARY`、`UNTYPED`は実装済み。
        * `SUMMARY`は`node_exporter`のテキスト形式のメトリック出力を参考に、1つの`SUMMARY`を複数の`TimeSeries`に変換するようにした。
      * `HISTOGRAM`、`GAUGE_HISTOGRAM`は未実装。
        * `node_exporter`のデフォルト設定ではこれらのタイプのメトリックは出力されなかったため。
    * 現状の実装ではどの[Metric types](https://prometheus.io/docs/concepts/metric_types/)だったかの情報は、変換後は失われる。
        * `metric_type`といったラベルを付与するようなオプションを付けるか要検討。
