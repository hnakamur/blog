+++
title="VictoriaMetricsのインストール"
date = "2019-12-23T00:05:00+09:00"
tags = ["victoriametrics"]
categories = ["blog"]
+++


参考: [github.com/VictoriaMetrics/VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) の [production build](https://github.com/VictoriaMetrics/VictoriaMetrics#production-build)

予め [Downloads - The Go Programming Language](https://golang.org/dl/) の手順で Go の最新版をインストールしておきます。

VictoriaMetrics の git レポジトリを clone して最新版のリリースに切り替えます。

```console
git clone https://github.com/VictoriaMetrics/VictoriaMetrics
cd VictoriaMetrics
git checkout v1.31.2
```

production 版をビルドし生成された実行ファイルを `/usr/local/bin/victoriametrics` にインストールします。

```console
make victoria-metrics-prod
sudo install bin/victoria-metrics-prod /usr/local/bin/victoriametrics
```

[Setting up service](https://github.com/VictoriaMetrics/VictoriaMetrics#setting-up-service) の [Documentation Addition for Creating a service · Issue #43 · VictoriaMetrics/VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/43) と [package/victoria-metrics.service](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/package/victoria-metrics.service) を参考に systemd のサービス定義ファイルを作成します。本番運用する際は root ユーザではなく専用のユーザを作るほうが良いと思いますが今回はとりあえず使ってみるだけなので手抜きします。ソースを見た感じでは PID のファイルは作らないようなのと [package/victoria-metrics.service](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/package/victoria-metrics.service) にもないので `PIDFile` は無しで。

`-retentionPeriod` は保管したい期間を月単位で指定します。下記の例は 6 か月です。 [lib/storage/table.go#L137](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.31.2/lib/storage/table.go#L137) を見ると1か月は31日として換算しています。

```console
cat <<'EOF' | sudo tee /etc/systemd/system/victoriametrics.serivce > /dev/null
[Unit]
Description=VictoriaMetrics
After=network.target

[Service]
Type=simple
StartLimitBurst=5
StartLimitInterval=0
Restart=on-failure
RestartSec=1
ExecStart=/usr/local/bin/victoriametrics -storageDataPath /var/lib/victoriametrics -retentionPeriod 6
ExecStop=/bin/kill -s SIGTERM $MAINPID
LimitNOFILE=65536
LimitNPROC=32000

[Install]
WantedBy=multi-user.target
EOF
```

以下では tank1 という zfs ボリュームが既にある想定で tank1/victoriametrics ボリュームを新規作成し /var/lib/victoriametrics にマウントポイントを設定します。

```console
sudo zfs create tank1/victoriametrics
sudo zfs set mountpoint=/var/lib/victoriametrics tank1/victoriametrics
```

設定ファイルを反映してサービスを起動します。

```console
sudo systemctl daemon-reload
sudo systemctl start victoriametrics
```
