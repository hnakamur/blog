---
title: "Apache Traffic Serverで400 Bad Reqeuestエラーが出る問題"
date: 2024-08-31T23:18:22+09:00
---
## はじめに

upstreamをnginxとしてApache Traffic Serverをリバースプロキシとして使う場合に、コンテンツありのリクエストを多数送ると、upstreamのnginxで400 Bad Requestが出る場合があるという問題があります。

以前 [hnakamur/ats-nginx-bad-request](https://github.com/hnakamur/ats-nginx-bad-request) に再現環境を作っていたのですが、[Release 10.0.0 · apache/trafficserver](https://github.com/apache/trafficserver/releases/tag/10.0.0)が出たので再度確認してみたら再現しました。原因究明はできていませんが、とりあえずメモ。

リクエストの送信は[hey](https://github.com/rakyll/hey)を使っています。

## [ats-10.0.x ブランチ](https://github.com/hnakamur/ats-nginx-bad-request/tree/ats-10.0.x)

10.0.0でリリースビルドした環境。

[hey.log#L88-L90](https://github.com/hnakamur/ats-nginx-bad-request/blob/0ee064deb554191e170b29f5d5b3671b786affd8/hey.log#L88-L90)に以下のように400 Bad Requestが出ています。

```
Status code distribution:
  [400]	2 responses
  [405]	254 responses
```

## [ats-10.0.x-O2 ブランチ](https://github.com/hnakamur/ats-nginx-bad-request/tree/ats-10.0.x-O2)

[ats-10.0.x ブランチ](https://github.com/hnakamur/ats-nginx-bad-request/tree/ats-10.0.x)ではコンパイラの最適化オプションが`-O3`ですが、これを`-O2`にして試してみました。

これでも 400 Bad Request は再現しました。`-O3`の問題では無さそうです。


## [ats-10.0.x-debug-tsan ブランチ](https://github.com/hnakamur/ats-nginx-bad-request/tree/ats-10.0.x-debug-tsan)

デバッグビルドにしてThread Sanitizer （以下TSAN）を使ってみた版。TSANを使うのは初めてです。

[Dockerfile#L36-L62](https://github.com/hnakamur/ats-nginx-bad-request/blob/71646840ca20b90da6f279a79340d45beef49da8/ats/Dockerfile#L36-L62)

```
ARG GIT_COMMIT=63bb35dfa7926f468f66e0f2279dd5b529a18a84
RUN curl -sSL https://github.com/apache/trafficserver/archive/${GIT_COMMIT}.tar.gz | tar zxf - --strip-component=1 -C ${SRC_DIR}/trafficserver
WORKDIR ${SRC_DIR}/trafficserver
ARG BUILD_DIR=/src/trafficserver/build
RUN cmake -B ${BUILD_DIR} -G Ninja \
	-DCMAKE_BUILD_TYPE=Debug \
	-DCMAKE_CXX_FLAGS_DEBUG="-g -fsanitize=thread" \
	-DCMAKE_C_FLAGS_DEBUG="-g -fsanitize=thread" \
	-DCMAKE_INSTALL_PREFIX=/opt/trafficserver \
	-DCMAKE_INSTALL_BINDIR=bin \
	-DCMAKE_INSTALL_SBINDIR=bin \
	-DCMAKE_INSTALL_LIBDIR=lib \
	-DCMAKE_INSTALL_LIBEXECDIR=lib/modules \
	-DCMAKE_INSTALL_SYSCONFDIR=etc \
	-DCMAKE_INSTALL_LOCALSTATEDIR=var \
	-DCMAKE_INSTALL_RUNSTATEDIR=var/run \
	-DCMAKE_INSTALL_DATAROOTDIR=share \
	-DCMAKE_INSTALL_DATADIR=share/data \
	-DCMAKE_INSTALL_DOCDIR=share/doc \
	-DCMAKE_INSTALL_LOGDIR=var/log \
	-DCMAKE_INSTALL_CACHEDIR=var/cache \
	-DBUILD_EXPERIMENTAL_PLUGINS=ON \
	-DENABLE_MAXMIND_ACL=ON \
	-DENABLE_URI_SIGNING=ON \
	-DENABLE_JEMALLOC=ON \
	-DENABLE_AUTEST=OFF
RUN cmake --build ${BUILD_DIR} --parallel --verbose
```

ビルド時に `FATAL: ThreadSanitizer: unexpected memory mapping` というエラーが出ました。
[c - FATAL: ThreadSanitizer: unexpected memory mapping when running on Linux Kernels 6.6+ - Stack Overflow](https://stackoverflow.com/questions/77850769/fatal-threadsanitizer-unexpected-memory-mapping-when-running-on-linux-kernels)というページによるとUbuntu 24.04では`vm.mmap_rnd_bits`が32でTSANを使うためには変更が必要とのこと。

私はUbuntu 24.04上のIncusコンテナ内でDocker Composeを動かして試していました。
ということでIncusホストのUbuntu 24.04上で以下のように28に変更してみました。

```
sudo sysctl vm.mmap_rnd_bits=28
```

これでビルドが通るようになりました。

そしてこの環境でも 400 Bad Request は再現しました。

https://github.com/hnakamur/ats-nginx-bad-request/commit/d83a65c014f981ca7d7687d8ad4d3d3a23dad8a1
のコミットメッセージにTSANが報告したdata raceの出力の抜粋を含めています（完全な出力は`ats.log.zst`参照）。

これらのdata raceが400 Bad Requestの原因かは不明です。一方data raceの出力の1つに`src/tscore/ink_queue.cc:559`があり、それは[TSan: ink atomic queue not so atomic · Issue #11640 · apache/trafficserver](https://github.com/apache/trafficserver/issues/11640)にも報告されていました。

[is:issue is:open tsanでissueを検索](https://github.com/apache/trafficserver/issues?q=is%3Aissue+is%3Aopen+tsan)すると他にもTSANで報告されたdata raceのイシューが上がってました。

https://github.com/hnakamur/ats-nginx-bad-request/commit/71646840ca20b90da6f279a79340d45beef49da8
のコミットではログやtcpdumpの出力を特定のポートのものに絞ったものを作っています。

コミットメッセージにtcpdumpのログの抜粋を貼りましたが、リクエスト行の前にたぶんその前のリクエストのコンテンツの断片が送られており、このせいで400 Bad Requestになっているようです。リクエストのコンテンツはすべて1024バイトで試していたのですが、この断片は344バイトとなっていました。
