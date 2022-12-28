---
title: "luajit-remakeを試してみた"
date: 2022-12-28T18:20:31+09:00
---
## はじめに
[LuaJITでたらい回し関数のベンチマークを試してみた · hnakamur's blog](/blog/2022/12/28/tried-tarai-benchmark-with-luajit/)のついでに[luajit-remake/luajit-remake: An ongoing attempt to re-engineer LuaJIT from scratch](https://github.com/luajit-remake/luajit-remake)も試してみたのでメモです。

## ビルド

Dockerはインストール済みという前提で、以下のコマンドを実行すると、カレントディレクトリに`luajitr`という実行ファイルが生成されます。

```
git clone https://github.com/luajit-remake/luajit-remake
cd luajit-remake
./ljr-build make release
```

ビルドに使用するLLVMなどのツールチェインは
[haoranxu510/ljr-build - Docker Image | Docker Hub](https://hub.docker.com/r/haoranxu510/ljr-build)のv0.0.3のイメージをpullしてくるようになっていました。

これを手元でビルドする場合は、上記のコマンドを実行する前に以下のようにすればOKでした。

```
cd dockerfile
docker build -t ljr-build:v0.0.3 .
```

ただ、ljr-buildのDockerイメージのv0.0.3がgitのどのコミットに対応しているかが分からなかったので、正しくは手元でljr-buildのDockerイメージをビルドする際はv0.0.3と付けずにビルドして`./ljr-build`のスクリプトのほうをコピペ改変してv0.0.3ではなく手元のビルドを使うように改変したほうが良さそうです。

ツールチェインのDockerイメージのビルドには[dockerfile/build_docker_image.sh](https://github.com/luajit-remake/luajit-remake/blob/master/dockerfile/build_docker_image.sh)というスクリプトを使っていますが、CMakeをソースからインストールして、独自パッチを当てたLLVM 12でLLVM 15.0.3をビルドしたりしています。また[rui314/mold: mold: A Modern Linker 🦠](https://github.com/rui314/mold/)も使われていました。

## 付属のベンチマークを実行

ここでは[haoranxu510/ljr-build - Docker Image | Docker Hub](https://hub.docker.com/r/haoranxu510/ljr-build)のv0.0.3のイメージのツールチェインを使って以下のコミットのソースでビルドしたluajitrで試しました。

```
$ git log -1
commit f2701c3dfdfb4e14ec0875804704177720582bd8 (HEAD -> master, origin/master, origin/HEAD)
Author:     Haoran Xu <haoranxu510@gmail.com>
AuthorDate: Thu Dec 1 21:52:55 2022
Commit:     Haoran Xu <haoranxu510@gmail.com>
CommitDate: Thu Dec 1 21:52:55 2022

    more refactoring in preparation for baseline jit
```

`./run_bench.sh`と実行するとコンソールに出力されつつ`benchmark.log`というログファイルが生成されます。

`run_bench.sh`ではテストデータをluaで作るようになっているのですがそこをluajitに書き換えた版と、luajitrではなくluajitを使うようにした`run_bench_luajit.sh`を作って、luajitrとluajitでベンチマークを実行して見ました。

結果は[hnakamur/luajit-remake at compare-benchmark-with-luajit](https://github.com/hnakamur/luajit-remake/tree/compare-benchmark-with-luajit)の[benchmark-luajitr.log](https://github.com/hnakamur/luajit-remake/blob/compare-benchmark-with-luajit/benchmark-luajitr.log)と[benchmark-luajit.log](https://github.com/hnakamur/luajit-remake/blob/compare-benchmark-with-luajit/benchmark-luajit.log)に置いています。ほとんどのテストではluajitのほうが速いですが、一部のテストはluajitrのほうが速かったです。

## たらい回し関数のベンチマークを試してみた

LuaJITのFFIや`os.time`はluajitrでは未実装でした。

```
$ ~/ghq/github.com/luajit-remake/luajit-remake/luajitr tarai-ffi-time.lua
Uncaught error: Library function 'require' is not implemented yet!
$ ~/ghq/github.com/luajit-remake/luajit-remake/luajitr tarai-os-time.lua
Uncaught error: Library function 'os.time' is not implemented yet!
```

ということで`/usr/bin/time`で処理時間とメモリ消費量を調べてLuaJITと比べました。[LuaJITでたらい回し関数のベンチマークを試してみた · hnakamur's blog](/blog/2022/12/28/tried-tarai-benchmark-with-luajit/)の`clock_gettime`を使う方式とは異なり、`luajit`と`luajitr`の起動時間も含まれるので、そちらの記事とは別の比較になります。

```
$ set -x; for i in {1..3}; do /usr/bin/time -f '%e %M' ~/ghq/github.com/luajit-remake/luajit-remake/luajitr tarai-no-time.lua ; /usr/bin/time -f '%e %M' luajit tarai-no-time.lua; done; set +x
+ for i in {1..3}
+ /usr/bin/time -f '%e %M' /home/hnakamur/ghq/github.com/luajit-remake/luajit-remake/luajitr tarai-no-time.lua
ans=14
5.51 3140
+ /usr/bin/time -f '%e %M' luajit tarai-no-time.lua
ans=14
2.12 2164
+ for i in {1..3}
+ /usr/bin/time -f '%e %M' /home/hnakamur/ghq/github.com/luajit-remake/luajit-remake/luajitr tarai-no-time.lua
ans=14
5.50 3256
+ /usr/bin/time -f '%e %M' luajit tarai-no-time.lua
ans=14
1.91 2092
+ for i in {1..3}
+ /usr/bin/time -f '%e %M' /home/hnakamur/ghq/github.com/luajit-remake/luajit-remake/luajitr tarai-no-time.lua
ans=14
5.50 3132
+ /usr/bin/time -f '%e %M' luajit tarai-no-time.lua
ans=14
2.23 2104
+ set +x
```

このベンチマークに関しては、現状ではOpenRestyのフォーク版LuaJITのほうが速くてメモリ消費量も少ないようです。

ただ、[Building the fastest Lua interpreter.. automatically!](https://sillycross.github.io/2022/11/22/2022-11-22/)の記事を読むとtail-call approachは良さそうな感じなので将来に期待したいところです。
