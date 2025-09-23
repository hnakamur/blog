---
title: "Fluent BitでClickHouseへ出力するプラグインの例を書いてみた"
date: 2025-09-23T22:34:21+09:00
---

## はじめに

[Golang output plugins | Fluent Bit: Official Manual](https://docs.fluentbit.io/manual/fluent-bit-for-developers/golang-output-plugins)を見て試したメモです。

作った例は https://github.com/hnakamur/fluentbit_out_clickhouse_example に置いています。

## Ubuntuでの環境構築手順

作業は[Incus](https://incus-ja.readthedocs.io/ja/latest/)のUbuntuコンテナ内で行っています。
デフォルトで非特権コンテナなのでセキュリティ的にも安心です。

コンテナ内ではrootユーザーのため、以下の手順ではsudoは省略しています。

### clickhouse-localのインストール

今回は手軽にということでclickhouse-localを使いました。

[clickhouse-local | ClickHouse Docs](https://clickhouse.com/docs/operations/utilities/clickhouse-local)の手順でセットアップ。

以下のコマンドを実行すると、カレントディレクトリに`clickhouse`という実行ファイルがダウンロードされます。
```
curl https://clickhouse.com/ | sh
```

最後に以下のように出力されます。直接実行して使っても良いし、インストールもできるとのこと。

```
Successfully downloaded the ClickHouse binary, you can run it as:
    ./clickhouse

You can also install it:
sudo ./clickhouse install
```

今回はインストールしてみました。以下のコマンドを実行。
```
sudo ./clickhouse install
```

途中で以下のプロンプトが出るので、デフォルトユーザーのパスワードを設定します。
```
Set up the password for the default user:
```

その後以下のようにlocalhost以外からの接続も許可するか聞かれます。
今回はとりあえずのお試し用なので`N`にしました
（がっつり使う場合は[Install ClickHouse | ClickHouse Docs](https://clickhouse.com/docs/install)の手順でインストールするほうが良いと思います）。

```
Password for the default user is saved in file /etc/clickhouse-server/users.d/default-password.xml.
Setting capabilities for clickhouse binary. This is optional.
Allow server to accept connections from the network (default is localhost only), [y/N]:
```

インストール完了して以下のメッセージが出ました。
サーバーの開始とクライアントの起動方法が書かれています。

```
ClickHouse has been successfully installed.

Start clickhouse-server with:
 sudo clickhouse start

Start clickhouse-client with:
 clickhouse-client --password
```

`sudo clickhouse start`はバックグラウンドでサーバーを起動してシェルのプロンプトに戻ります。
`sudo clickhouse stop`で停止できます。

クライアントの起動は`--password`なしの`clickhouse-client`だけでも大丈夫です。
`--password`ありでもなしでも`Password for user (default):`というプロンプトが出るので、
インストール時に設定したパスワードを入力します。

ただし、クエリを指定して非インタラクティブに実行する場合は`--password`オプションの指定が必要です。

### fluent-bitのインストール

[Ubuntu | Fluent Bit: Official Manual](https://docs.fluentbit.io/manual/installation/downloads/linux/ubuntu)の手順でインストールします。

今回は手軽にSingle line installの手順にしました。

[Incus](https://incus-ja.readthedocs.io/ja/latest/)のUbuntuコンテナだと先にgpgとcurlをインストールしておく必要があります。
```
apt-get -y install gpg curl
```

その後以下のコマンドでfluent-bitをインストールします。

```
curl https://raw.githubusercontent.com/fluent/fluent-bit/master/install.sh | sh
```

systemdでfluent-bitのサービスが設定されますが、インストール直後は停止状態です。

#### fluent-bitの設定はYAMLファイルで

`/etc/fluent-bit/`ディレクトリに`fluent-bit.conf`という設定ファイルがあります。

[Configure Fluent Bit | Fluent Bit: Official Manual](https://docs.fluentbit.io/manual/administration/configuring-fluent-bit)によると旧式の設定は2026年末で非推奨とのことなので、これから書くならYAMLにしておくのが良いです。

インストール時点でのfluent-bitサービスのExecStartの値は以下のようになっています。

```
root@tmp-jammy:~# systemctl cat fluent-bit | grep ^ExecStart=
ExecStart=/opt/fluent-bit/bin/fluent-bit -c //etc/fluent-bit/fluent-bit.conf
```

以下のコマンドを実行して`/etc/fluent-bit/fluent-bit.yaml`を設定ファイルとして使うようにします。

```
SYSTEMD_EDITOR=tee systemctl edit fluent-bit <<EOF
[Service]
ExecStart=
ExecStart=/opt/fluent-bit/bin/fluent-bit -c /etc/fluent-bit/fluent-bit.yaml
EOF
```

[systemd - Using systemctl edit via bash script? - Unix & Linux Stack Exchange](https://unix.stackexchange.com/questions/459942/using-systemctl-edit-via-bash-script)によるとsystemd v256以降なら`systemctl edit`の`--stdin`オプションが使えるそうです（が、2025-09-23時点ではUbuntu 24.04のsystemdはv255で`--stdin`オプションは使えないです）。

```
systemctl edit --stdin fluent-bit <<EOF
[Service]
ExecStart=
ExecStart=/opt/fluent-bit/bin/fluent-bit -c /etc/fluent-bit/fluent-bit.yaml
EOF
```

動作確認のため最低限の設定ファイルを作成します。

```
cat <<'EOF' > /etc/fluent-bit/fluent-bit.yaml
service:
  flush: 1
  log_level: info
  http_server: false
  http_listen: 0.0.0.0
  http_port: 2020
  hot_reload: on

pipeline:
  inputs:
    - name: cpu
      tag:  cpu.local
  outputs:
    - name:  stdout
      match: '*'
EOF
```

以下のコマンドでfluent-bitサービスを起動します。
```
systemctl start fluent-bit
```

以下のコマンドで起動状態を確認します。

```
systemctl status fluent-bit
```

最後のほうに以下のようにcpu.localのログが出力されていればOKです。
```
Sep 23 14:26:25 tmp-jammy fluent-bit[4139]: [0] cpu.local: [[1758637582.985419715, {}], {"cpu_p"=>0.625000, "user_p"=>0.291667, "system_p"=>0.333333, "cpu0.p_cpu"=>0.000000, "cpu0.p_user"=>0.000000, "cpu0.p_syst…（略）…
```

### プラグインをビルドする準備

レポジトリをクローンするためにgitと、プラグインはCGoを使っているのでコンパイラをインストールします。

```
apt-get -y install git build-essential
```

[All releases - The Go Programming Language](https://go.dev/dl/)からGoの最新版をダウンロードとインストールします。

```
curl -sSL https://go.dev/dl/go1.25.1.linux-amd64.tar.gz | tar zx -C /usr/local
```

その後`/usr/local/go/bin`をPATH環境変数に追加します。

```
echo 'PATH=/usr/local/go/bin:$PATH' >> ~/.profile
```

シェルを起動し直して上記の設定を読み込みます。
```
exec $SHELL -l
```

`type go`を実行してgoにPATHが通ったことを確認します。
実行例：

```
# type go
go is /usr/local/go/bin/go
```

今回作成したプラグインの例のレポジトリをクローンします。

```
git clone https://github.com/hnakamur/fluentbit_out_clickhouse_example
```

### プラグインをビルド

上記でクローンしたレポジトリのディレクトリに移動します。

```
cd /root/fluentbit_out_clickhouse_example
```

以下のコマンドでプラグインをビルドしインストールします。

```
make install
```

### nginxのアクセスログを読むように設定変更

nginxをインストール（この記事では手順は省略）して、
https://github.com/hnakamur/fluentbit_out_clickhouse_example/blob/a09e27d314155ef56ed49a7311bcac0fbc51e5f8/fluent-bit.yaml
のコメントに書いているアクセスログ設定をnginxの設定ファイルに反映します。

その後、このファイルの内容で`/etc/fluent-bit/fluent-bit.yaml`を更新します（`outputs`の`name: clickhouse_example`の`database`、`password`、`table`は適宜変更してください）。

`database`に指定した名前のデータベースを作成します（以下はfluentbitという名前にした場合）。

```
root@tmp-jammy:~# clickhouse-client --password -q 'create database fluentbit'
Password for user (default):
```

最後にfluent-bitサービスを再起動します。

```
systemctl restart fluent-bit
```

fluent-bitサービス起動時にout_clickhouse_exampleプラグインが読み込まれClickHouseのデータベースに接続して

これでcurlでnginxにアクセスすると、指定のデータベースの指定のテーブルにデータが登録されます。
確認の実行例：
```
# clickhouse-client --password -q 'select * from fluentbit.jsonlogs2'
Password for user (default):
2025-09-23 14:54:42.372 {"body_bytes_sent":"612","bytes_sent":"859","host":"localhost","http_host":"localhost","pid":"8501","referer":"","remote_addr":"127.0.0.1","remote_port":"47904","remote_user":"","request":"GET \\/?a=2 HTTP\\/1.1","request_id":"950c8f8d132e25b5a1bbad5f75ae7a18","request_length":"77","request_time":"0.000","scheme":"http","status":"200","user_agent":"curl\\/7.81.0","x_forwarded_for":""}
```
