---
title: "otelcol-contribでClickHouseにOpenTelemetryのデータ投入を試してみた"
date: 2025-01-06T21:11:06+09:00
---

## はじめに

[ISUCON 14: ClickHouse と OpenTelemetry で ISUCON の計測環境を作ったら快適だった - Unyablog.](https://nonylene.hatenablog.jp/entry/2024/12/09/010951)の記事を見て、私もClickHouseにOpenTelemetryのデータを投入するのは気になっていたので試してみた、というメモです。

メトリクス、ログ、トレースの3種類のデータ投入を試しました。

## otelcol-contrib について

* バイナリ配布用レポジトリ: https://github.com/open-telemetry/opentelemetry-collector-releases
  * `otelcol-contrib_${version}_linux_amd64.deb` のようなビルド済みバイナリが提供されています。
  * `otelcol-contrib_${version}_linux_amd64.deb`をインストールすると、systemdで`otelcol-contrib`というサービスが起動されます。
  * 使用する設定ファイルは`/etc/otelcol-contrib/config.yaml`です。
* opentelemetry-collector-contribのソースレポジトリ: https://github.com/open-telemetry/opentelemetry-collector-contrib
  * レポジトリ名から察するに otelcolは opentelemetry-collector の略のようです。
  * receiver、processor、exporterディレクトリにさまざまなレシーバー、プロセッサー、エクスポーターが含まれています。
    * レシーバーは外界から`otelcol-contrib`にデータを取り込むものです。
    * プロセッサーは取り込んだデータを加工するものです。
    * エクスポーターは加工したデータを外界に送るものです。
      * Prometheusの文脈だとexporterという用語はPrometheusがデータをスクレイピングしに来るところにメトリクスデータを提供するものですが、otelcolの文脈では外界からotelcolに取り込んだデータをClickHouseのような外界のデータベースに送るものということのようです。
  * 今回試したものは以下のとおりです。
    * [File Log Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/b938631b9c319da90de38e4d25d31a4916297ad7/receiver/filelogreceiver)
      * nginxなど外部のミドルウェアが出力したファイルを読んでotelcolにログデータを取り込むレシーバーです。
      * READMEによると、2025-01-06時点での安定度はベータです。
    * [Prometheus Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/b938631b9c319da90de38e4d25d31a4916297ad7/receiver/prometheusreceiver)
      * Prometheus用の各種exporterからメトリクスデータを読み取ってotelcolにログデータを取り込むreceiverです。
      * READMEによると、2025-01-06時点での安定度はベータです。現在work in progressでいくつかの制限事項があり、それが問題になるケースでは使わないよう注意書きがあります。
    * [Attributes Processor](https://github.com/open-telemetry/opentelemetry-collector-releases/tree/main/distributions/otelcol-k8s)
      * 各種receiverで取り込んだデータに、属性データを付与するプロセッサーです。
      * READMEによると、2025-01-06時点での安定度はメトリクス、トレース、ログともにベータです。
      * 今回は取り込んだデータにホスト名を付与するのに使ってみました（が、こういう使い方で良いのかは未確認）。
    * [ClickHouse Exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/b938631b9c319da90de38e4d25d31a4916297ad7/exporter/clickhouseexporter)
      * OpenTelemetryのデータをClickHouseに送るためのエクスポーターです。
      * READMEによると、2025-01-06時点での安定度はメトリクスはアルファ、トレースとログはベータです。
* opentelemetry-collectorのソースレポジトリ: https://github.com/open-telemetry/opentelemetry-collector
  * `otelcol-contrib`の実行ファイルに`opentelemetry-collector`の機能も含まれています。
  * 今回試したものは以下のとおりです。
    * [OLTP Receiver](https://github.com/open-telemetry/opentelemetry-collector/tree/57c6c151279ee0b4988ac427feffbb2613926b22/receiver/otlpreceiver)
      * READMEによると、2025-01-06時点での安定度はログがベータ、トレースとメトリクスはstableです。

## ClickHouse exporterの設定オプションとテーブル名

[Configuration options](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/b938631b9c319da90de38e4d25d31a4916297ad7/exporter/clickhouseexporter#configuration-options)に設定オプションについての説明があります。

* `Connection options:`の項の`create_schema`（デフォルト値:true）が`true`だと`otelcol-contrib`がClickHouseに接続したときにデータベースとテーブルがない場合は作成します。
* `ClickHouse tables:`にログ、トレース、メトリクスのデータを保管するテーブル名の設定があります。デフォルト値は以下のとおりです。
  * ログ：`otel_logs`
  * トレース：`otel_traces`
  * メトリクス
    * `otel_metrics_gauge` Prometheusのgaugeのデータ保管用
    * `otel_metrics_sum` Prometheusのcounterのデータ保管用
    * `otel_metrics_summary` Prometheusのsummaryのデータ保管用
    * `otel_metrics_histogram` Prometheusのclassic(非native)ヒストグラムのデータ保管用
    * `otel_metrics_exp_histogram` Prometheusのnativeヒストグラムのデータ保管用

## ClickHouseのメトリクスをClickHouseにデータ投入するのを試した

* https://github.com/hnakamur/clickhouse-ansible-playbook の [ec576b3](https://github.com/hnakamur/clickhouse-ansible-playbook/commit/ec576b31d34c53fbd356350cc9d382baa08590c9)のコミットで試しました。
* `otelcol-contrib`の設定ファイルのテンプレートは [roles/otelcol_contrib/templates/config.yaml.j2](https://github.com/hnakamur/clickhouse-ansible-playbook/blob/ec576b31d34c53fbd356350cc9d382baa08590c9/roles/otelcol_contrib/templates/config.yaml.j2) です。

## nginxのログとトレースをClickHouseにデータ投入するのを試した

* こちらはplaybook化していません。
* `/etc/otelcol-contrib/config.yaml`の設定は以下のとおりです。

```
# https://clickhouse.com/docs/en/observability/integrating-opentelemetry
# config-traces.yaml
# clickhouse-config.yaml
#
# https://github.com/open-telemetry/opentelemetry-collector/issues/11337
receivers:
  filelog:
    include:
      - /var/log/nginx/access.json.log
    start_at: beginning
    operators:
      - type: json_parser
        timestamp:
          parse_from: attributes.time_local
          layout_type: 'gotime'
          layout: '02/Jan/2006:15:04:05 -0700'
  prometheus/nginx:
    config:
      scrape_configs:
      - job_name: 'otel-collector'
        scrape_interval: 10s
        static_configs:
        - targets: ['127.0.0.1:9113']
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317

processors:
  attributes/host:
    actions:
    - key: host.name
      value: 'ggear3'
      action: insert
  attributes/nginx:
    actions:
    - key: middleware.id
      value: 'nginx'
      action: insert
  resource:
    attributes:
    - key: otel.host.name
      value: 'ggear2'
      action: insert
  batch:
    timeout: 5s
    send_batch_size: 5000
exporters:
  clickhouse:
    endpoint: tcp://【ClickHouseのIPアドレス】:9000?dial_timeout=10s&compress=lz4&async_insert=1&username=【ClickHouseのユーザー名】&password=【ClickHouseのパスワード】
    # ttl: 72h
    traces_table_name: otel_traces
    logs_table_name: otel_logs
    create_schema: true
    timeout: 5s
    cluster_name: cluster01
    table_engine:
      name: ReplicatedMergeTree
    database: otel
    sending_queue:
      queue_size: 1000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

service:
  pipelines:
    metrics:
      receivers: [prometheus/nginx]
      processors: [attributes/nginx, attributes/host, batch]
      exporters: [clickhouse]
    logs:
      receivers: [filelog]
      processors: [resource, attributes/host, batch]
      exporters: [clickhouse]
    traces:
      receivers: [otlp]
      processors: [resource, attributes/host, batch]
      exporters: [clickhouse]
```

* 上記の設定のserviceのpipelinesでデータの流れを定義しています。
  * メトリクスは[nginxinc/nginx-prometheus-exporter](https://github.com/nginxinc/nginx-prometheus-exporter)から、receiversに指定したPrometheus receiverで読み取って、processorsに指定した加工を施して、exportersに指定したClickHouse exporterでClickHouseにデータ投入します。
  * ログはnginxの設定でJSON形式で`/var/log/nginx/access.json.log`というファイルに出力するようにしていて、それをFile Log Receiverで読み取り、加工して、ClickHouseにデータ投入します。
  * トレースは[nginxinc/nginx-otel](https://github.com/nginxinc/nginx-otel)モジュールからOLTP Receiverにデータを送り、加工して、ClickHouseにデータ投入します。
