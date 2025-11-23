---
title: "docker composeプロジェクト内のコンテナでtcpdumpを実行するスクリプトを書く"
date: 2025-11-23T17:19:58+09:00
---

## はじめに

[network programming - How to capture packets for single docker container - Stack Overflow](https://stackoverflow.com/questions/39362730/how-to-capture-packets-for-single-docker-container)で紹介されている2つの方法を試してみたのでメモです。

## 1つ目の方法：nsenterを使う

対象のコンテナのpidを取得します。
```
docker inspect --format "{{ .State.Pid }}" "$CONTAINER_ID_OR_NAME"
```

`nsenter`の`-t`でターゲットの指定し、`-n`でnetwork namespace`に入ってtcpdumpコマンドを実行します。
```
sudo nsenter -n -t "$PID" tcpdump -i any -U -w "$OUTPUT_FILE" "$FILTER"
```

nsenterの実行にroot権限が必要なため、sudoを使っています。

## 2つ目の方法：dockerの`--net`オプションを使う

```
docker run -it --rm container:$CONTAINER_ID_OR_NAME utils/tcpdump -i any -U -w "$OUTPUT_FILE" "$FILTER"
```

`--net container:$CONTAINER_ID_OR_NAME`については[Networking | Docker Docs](https://docs.docker.com/engine/network/)の[Container networks](https://docs.docker.com/engine/network/#container-networks)に記載がありました。

また、関連する話として、docker composeの[Release notes](https://docs.docker.com/compose/releases/release-notes/)の[1.2.0](https://docs.docker.com/compose/releases/release-notes/#120)に以下の記載がありました（今回は試してないですが、docker composeのYAMLファイルを書き換えてtcpdumpを実行するコンテナーを追加するというのもできそう）。

> A service can now share another service's network namespace with `net: container:<service>`.

tcpdumpのDockerイメージは[utils/tcpdump](https://hub.docker.com/r/utils/tcpdump/)にしました。
[docker-utilities/tcpdump: Docker image with tcpdump](https://github.com/docker-utilities/tcpdump)にDockerfileがあり、内容もalpineでtcpdumpパッケージを追加するだけとミニマムです。

## 実際の例：coraza-caddyのテスト

[corazawaf/coraza-caddy: OWASP Coraza middleware for Caddy. It provides Web Application Firewall capabilities](https://github.com/corazawaf/coraza-caddy)の[ftw](https://github.com/corazawaf/coraza-caddy/tree/66e7c64ecc5fe8e028d28d4ec9ea0cee75673041/ftw)ディレクトリにdocker composeを使ってテストを実行するためのファイル群があります。

テスト実行中にftw、caddy、backendと3つのコンテナ内の通信に対してtcpdumpを実行し、テスト終了時にkillするシェルスクリプトを書いてみました。

### nsenterでtcpdumpを実行するスクリプト

```sh
#!/bin/sh
set -eu

# Cache sudo credential before running nsenter and tcpdump in the background.
sudo -p "[sudo] password for $USER to run nsenter and tcpdump: " -s :

bg_pids=""

capture() {
  service="$1"
  filter="$2"

  container="$(docker compose ps --format '{{.Name}}' $service)"
  c_pid=$(docker inspect --format "{{ .State.Pid }}" "$container")
  sudo nsenter -n -t $c_pid tcpdump -i any -U -w "${service}.pcap" "$filter" 2>/dev/null &
  bg_pids="$bg_pids $!"
}

stop_capture() {
  kill $bg_pids
}

trap stop_capture EXIT

crs_ver=$(go list -m -f '{{.Version}}' github.com/corazawaf/coraza-coreruleset/v4)
docker compose build --pull --build-arg CRS_VERSION=$crs_ver

docker compose up -d
docker compose pause

capture ftw 'tcp port 8080'
capture caddy 'tcp port (8080 or 8081)'
capture backend 'tcp port (8080 or 8081)'

docker compose unpause

# note this process terminates after running docker compose down.
(docker compose logs -f --no-log-prefix ftw 2>&1 | tee ../build/run-ftw.log > /dev/null) &

set +e
docker compose wait --down-project ftw
rc=$?
echo service "ftw" exited with status code $rc
exit $rc
```

以下補足説明。

- サービス名からコンテナ名を取得するために `docker compose ps --format '{{.Name}}' サービス名`を使っています。
  - これで取得するためにはコンテナのプロセスが起動した状態である必要がありますが、テストが実行される前にtcpdumpを実行したいので、`docker compose up -d`と`docker compose pause`でデタッチ状態で起動し直後に一時停止しています。
  - tcpdumpをバックグラウンドで実行開始したら、`docker compose unpause`でプロジェクトのコンテナ実行再開しています。
- 最初にsudoを実行しているのは、sudo nsenterでtcpdumpを実行する際にプロンプトでの入力を不要にするためです。
  - tcpdumpをバックグラウンドで実行する都合上、プロンプトが出ても入力できません。直前に`sudo -s :`を実行しておくことで、クレデンシャルがキャッシュに入り、tcpdump実行時はプロンプトでの入力を不要にしています。

### dockerでtcpdumpを実行するスクリプト

dockerコマンドはsudo無しで実行できるので、sudoのパスワード入力が不要な分こちらのほうが使いやすいです。

```sh
#!/bin/sh
set -eu

bg_pids=""

capture() {
  service="$1"
  filter="$2"

  container="$(docker compose ps --format '{{.Name}}' $service)"
  docker run --rm -v ../build:/home --net container:${container} utils/tcpdump -i any -U -w /home/${service}.pcap "$filter" 2>/dev/null &
  bg_pids="$bg_pids $!"
}

stop_capture() {
  echo $bg_pids | xargs -r kill
}

trap stop_capture EXIT

crs_ver=$(go list -m -f '{{.Version}}' github.com/corazawaf/coraza-coreruleset/v4)
docker compose build --pull --build-arg CRS_VERSION=$crs_ver

docker compose up -d
docker compose pause

capture ftw 'tcp port 8080'
capture caddy 'tcp port (8080 or 8081)'
capture backend 'tcp port (8080 or 8081)'

docker compose unpause

# note this process terminates after running docker compose down.
(docker compose logs -f --no-log-prefix ftw 2>&1 | tee ../build/run-ftw.log > /dev/null) &

set +e
docker compose wait --down-project ftw
rc=$?
echo service "ftw" exited with status code $rc
exit $rc
```

## 汎用化はあえてしてないです

スクリプトの引数を`サービス1 フィルター1 サービス2 ファイルター2 ...`のような形にして汎用化できるかもと一瞬思いましたが、呼び出すコマンドラインが長くなって結局ラッパースクリプトを書きたくなるので、それだったらdocker composeのプロジェクト毎に上記のようなスクリプトを書き換えて使うほうが良いなと思ったので。

