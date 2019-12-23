+++
title="tcpdumpとss -antpを同時に実行するシェルスクリプトの例"
date = "2019-12-23T22:20:00+09:00"
tags = ["tcpdump"]
categories = ["blog"]
+++

仕事で調査の時に書いた `tcpdump` と `ss -antp` を同時に実行するスクリプトの例をメモ。

* tcpdump で複数のポートを調べたいときはtcpdumpを複数起動せずにportをorで繋いで複数指定。
* tcpdump で取得時は余計な名前解決をして遅くならないように `-n` を指定。
* tcpdump の取得結果はファイルに書いておいて、後でファイルから読み込んでじっくり見る。

```bash
#!/bin/sh
if [ $# -ne 1 ]; then
  echo "Usage: tcpdump-and-ss-antp.sh logprefix"
  exit 1
fi

logprefix="$1"
pids=""

ss_antp_loop() {
  while :; do
    date +%FT%T.%N
    ss -antp
    sleep 0.5
  done
}

stop_background_processes() {
  echo killing $pids
  kill $pids
}
# 2=SIGINT
trap stop_background_processes 2

host=$(hostname)

ss_antp_loop > /tmp/${logprefix}-${host}-ss-antp.log &
pids="$pids $!"

tcpdump -n -vvv -i any -w /tmp/${logprefix}-${host}-tcpdump.log tcp port '(80 or 443 or 8080 or 9090)' &
pids="$pids $!"

echo background pids=$pids
wait
```

複数台のサーバで同時に調査するときは上記のようなスクリプトを各サーバに配置してポートを適宜調整。

curl実行用のスクリプト。

* 独自リクエストIDヘッダにナノ秒単位のタイムスタンプを設定。
* date コマンドでもナノ秒単位で開始時間を記録。
* bash 内蔵の time コマンドで所要時間を記録。

```bash
#!/bin/sh
if [ $# -ne 1 ]; then
  echo "Usage: $0 logprefix"
  exit 1
fi

logprefix="$1"

url=http://example.com

date +%FT%T.%N | tee -a ${logprefix}-curl.log
time curl -sSv -o /dev/null -H "X-Req-ID: $(date +%FT%T.%N)" $url 2>&1 | tee -a ${logprefix}-curl.log
sleep 5

date +%FT%T.%N | tee -a ${logprefix}-curl.log
time curl -sSv -o /dev/null -H "X-Req-ID: $(date +%FT%T.%N)" $url 2>&1 | tee -a ${logprefix}-curl.log
sleep 5

date +%FT%T.%N | tee -a ${logprefix}-curl.log
time curl -sSv -o /dev/null -H "X-Req-ID: $(date +%FT%T.%N)" $url 2>&1 | tee -a ${logprefix}-curl.log
```

実行するときはtmuxで複数ペインで表示して以下のような感じでコマンドラインを入力した後、全ペインでキー入力同期をオンにしてEnterを押して同時に開始。curlのスクリプトが終わったら少し待ってから Ctrl-C で止める。その後キー入力同期をオフにする。

```console
# クライアント
$ sleep 1; curlのスクリプト

# サーバ1
$ tcpdumpのスクリプト

# サーバ2
$ tcpdumpのスクリプト
```

複数ペインのキーの同期オン・オフは `~/.tmux.conf` に以下のように設定しています。

```text
# Synchronize panes
set-option -g synchronize-panes off
bind e setw synchronize-panes on
bind E setw synchronize-panes off
```

tcpdump ファイルで http プロトコルのダンプを見るときは `-A` で ASCII でパケットの内容を表示するとリクエストとレスポンスがそのまま見れて便利。バイナリのプロトコルの場合は `-A` の代わりに `-X` を使うと16進ダンプが見れる。

```console
tcpdump -n -A -r tcpdumpのダンプファイル
```

上記で読み込んだヘッダの例。

* 先頭は時刻の時分秒とマイクロ秒。
* 次が送信元IPアドレスとポートと送信先IPアドレスとポート。エフェメラルポートの場合は `ss -antp` のログと突き合せればどのプロセスかわかる。

```text
09:57:20.260518 IP 192.0.2.1.34042 > 192.0.2.2.80: Flags [P.], seq 1:154, ack 1, win 229, options [nop,nop,TS val 2026493290 ecr 2786517801], length 153: HTTP: GET /hello.png HTTP/1.1
```
