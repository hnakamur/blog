---
title: "Envoy と envoy-filter-example をビルドしてみた"
date: 2020-08-02T15:55:58+09:00
---

## はじめに

[Sonmuさんのツイート](https://twitter.com/songmu/status/1289230625933680641) で紹介されていた
[How we migrated Dropbox from Nginx to Envoy - Dropbox](https://dropbox.tech/infrastructure/how-we-migrated-dropbox-from-nginx-to-envoy)
を読みました。

nginx や Go でプロキシーサーバーを構築することについて、ずっと気になっていたけど私の力不足で性能検証できなくてもやもやしていたことについて詳しく書かれていて非常に参考になりました。

Envoy は moonjit という LuaJIT のフォーク版が組み込まれているが出来ることは限定的なので Dropbox ではこれは使わずに C++ で拡張しているとのことでした。

<!--
Envoy はバイナリパッケージを提供していますが、インストールしてみるとスタティックリンクの実行ファイルになっていました。
-->

そこでまずは Hello world 的なものを探すと
[envoyproxy/envoy-filter-example: Example of consuming Envoy and adding a custom filter](https://github.com/envoyproxy/envoy-filter-example)
というのがありました。

Building の項を見ると、サンプルのフィルター単体ではなく Envoy と合わせてスタティックな実行ファイルのバイナリーをビルドする方式らしいです。

ということでビルドを試してみたメモです。

## サンプルではなく Envoy の Docker イメージのビルド

上記のサンプルを試すにはこの項は不要ですが、興味本位で先に Envoy の Docker ビルド手順を試してみることにしました。

[Modifying Envoy](https://www.envoyproxy.io/docs/envoy/v1.15.0/install/building#modifying-envoy)
から
[Building an Envoy Docker image — envoy tag-v1.15.0 documentation](https://www.envoyproxy.io/docs/envoy/v1.15.0/install/sandboxes/local_docker_build)
を読んで試しました。

### Ubuntu 20.04 LTS に docker 公式パッケージをインストール

[Install Docker Engine on Ubuntu | Docker Documentation](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository) の apt のレポジトリを追加してインストールしました。

```console
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
```

のところはレポジトリのファイルを分けたいので以下のように変えています。

```console
echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable" | sudo tee /etc/apt/sources.list.d/docker.list
```

### Envoy の Docker イメージをビルドを試みるも問題発生

で [Building an Envoy Docker image — envoy tag-v1.15.0 documentation](https://www.envoyproxy.io/docs/envoy/v1.15.0/install/sandboxes/local_docker_build)
の Step 1: Build Envoy を試すわけですが、まず Envoy の git レポジトリを取得して移動します。

```console
git clone https://github.com/envoyproxy/envoy
cd envoy
```

次に手順通り以下のコマンドで Envoy の Docker イメージのビルドを試してみました。

```console
./ci/run_envoy_docker.sh './ci/do_ci.sh bazel.release'
```

[試してた時の私のツイートのスレッド](https://twitter.com/hnakamur2/status/1289481821709688840) にもありますが、いくつか問題が発生しました。

#### Docker で IPv6 を有効にする必要がある

まずテストで `cannot bind '[::1]:0'` というエラーが出ました。

[Control Docker with systemd | Docker Documentation](https://docs.docker.com/config/daemon/systemd/) と
[Enable IPv6 support | Docker Documentation](https://docs.docker.com/config/daemon/ipv6/) を見て
`/etc/docker/daemon.json` を以下の内容で作成しました。

```json
{
  "ipv6": true,
  "fixed-cidr-v6": "2001:db8:1::/64"
}
```

その後以下のコマンドを実行して反映します。

```console
sudo systemctl reload docker
```

#### ビルドの中間ファイルに 220GB 程度空きが必要

10 時間超えてもビルドが終わらないと思ったらルートファイルシステムの使用量が 100%  になって Ubuntu の Gnome に警告ダイアログが表示されました。
調べてみると `/tmp/envoy-docker-build` というディレクトリが作られて約 200GB もディスクを消費していました。

ビルドを試していたマシンは Windows とのデュアルブート構成にしていたのですが、 Windows のパーティションを消して Ubuntu 20.04 LTS を再インストールして十分な空きを確保しました。

また `/tmp/` 以下だと Linux の再起動時に消されてしまうと思ったので、場所を変える設定を調べました。

`ci/README.md` の `Building and running tests as a developer` の
[On Linux](https://github.com/envoyproxy/envoy/blob/master/ci/README.md#on-linux)
を見ると `ENVOY_DOCKER_BUILD_DIR` 環境変数で指定可能なことが分かりました。

が、下の

ただし、例の `~/build` のように `~` を使うとエラーになり、文字通り `~` というディレクトリが作られてしまいました。

ビルドに時間がかかるので time コマンドで計測しようと思い、以下のコマンドでビルドしました。

```console
time env "ENVOY_DOCKER_BUILD_DIR=$HOME/envoy-docker-build" ./ci/run_envoy_docker.sh './ci/do_ci.sh bazel.release'
```

上記のコマンドで以下の環境でビルドに4時間45分程度かかりました。

* PC: ThinkCenter m75q-1 Tiny
* CPU: AMD Ryzen 5 PRO 3400GE 4コア8スレッド
* RAM: 16GB (Crucial ノートPC用 メモリ PC4-21300(DDR4-2666) 8GB SODIMM CT8G4SFS8266 2毎セット)
* SSD: WesternDigital SSD WD Blue SN550シリーズ NVMe M.2 2280 1.0TB WDS100T2B0C

#### Docker の Spectre 対策を切る

3950Xで30分かからないくらいなので、上記は遅すぎではないかとツッコミのツイートを頂きました。
[Lizan ZhouさんはTwitterを使っています 「@hnakamur2 それはかかりすぎな気がします、3950Xで30分かからないくらいなので。ディスクが遅いか、DockerのSpectre対策がオンのままになっているかでは？」 / Twitter](https://twitter.com/lizan/status/1289804557724160004)

[CPU律速なRuby/Pythonコードはデフォルト設定のdocker上で遅くなる - まめめも](https://mametter.hatenablog.com/entry/2020/05/23/032650) によると docker の実行時に
`--security-opt seccomp=unconfined` あるいは `--privileged` を付けると Sepctre 対策が無効になるそうです。

一般にはここに書かれているように「Spectre攻撃に対して脆弱になるのでやめたほうがいい」でしょうが、自宅PCのような占有環境なら付けても良さそうです。

## envoy-filter-example のビルド

* [Hiroaki NakamuraさんはTwitterを使っています 「次は https://github.com/envoyproxy/envoy-filter-example のビルドを試してます。 https://docs.bazel.build/versions/3.4.0/install-ubuntu.html でbazel入れて https://github.com/pypa/pip/issues/5356#issuecomment-385688328 でpython3-distutils入れてエラーログ見てcmake入れて試したら今度はNinja。 https://github.com/ninja-build/ninja/releases を入れて再度実行中。」 / Twitter](https://twitter.com/hnakamur2/status/1289811629194899456)
    * https://github.com/envoyproxy/envoy-filter-example
    * https://docs.bazel.build/versions/3.4.0/install-ubuntu.html
    * https://github.com/pypa/pip/issues/5356#issuecomment-385688328
    * https://github.com/ninja-build/ninja/releases
* [Hiroaki NakamuraさんはTwitterを使っています 「あー、 /usr/bin/env: 'python': No such file or directory が。これは python3 へシンボリックリンク貼ればいいのかな。あ、ninjaは https://github.com/envoyproxy/envoy/blob/master/bazel/README.md みたらninja-buildで入れられたのか。」 / Twitter](https://twitter.com/hnakamur2/status/1289812481687220224)
    * https://github.com/envoyproxy/envoy/blob/master/bazel/README.md

でビルドしていたら

* [Lizan ZhouさんはTwitterを使っています 「@hnakamur2 ビルドコンテナ通りにまずは環境設定することをオススメします https://github.com/envoyproxy/envoy-build-tools/blob/master/build_container/build_container_ubuntu.sh」 / Twitter](https://twitter.com/lizan/status/1289817401467392002)
    * https://github.com/envoyproxy/envoy-build-tools/blob/master/build_container/build_container_ubuntu.sh

というツッコミを頂きました。ありがとうございます！

* [Hiroaki NakamuraさんはTwitterを使っています 「46分ぐらいでビルド完了しました。 この後教えていただいた https://github.com/envoyproxy/envoy-build-tools/blob/master/build_container/build_container_ubuntu.sh に環境を合わせて再度やってみます。 あー apt-add-repository のところだけはレポジトリファイルを分けたいのでアレンジして。」 / Twitter](https://twitter.com/hnakamur2/status/1289825477457133573)
