---
title: "Neluaを試してみた"
date: 2023-01-27T17:31:37+09:00
---

[LuaJITでたらい回し関数のベンチマークを試してみた · hnakamur's blog](/blog/2022/12/28/tried-tarai-benchmark-with-luajit/)と[luajit-remakeを試してみた · hnakamur's blog](/blog/2022/12/28/tried-luajit-remake/)に続いて今度は[Nelua](https://nelua.io/)を試しました。

NeluaはJITコンパイラではなく、事前にCにコンパイルするAOT (Ahead of Time)コンパイラです。
[FAQ](https://nelua.io/faq/)に[Why does Nelua compile to C first?](https://nelua.io/faq/#why-does-nelua-compile-to-c-first)という項がありました。

[Installing - Nelua](https://nelua.io/installing/)の手順でソースからインストールしました。

試したコミット: https://github.com/edubart/nelua-lang/commit/d10cc61bc54050b07874a8597f8df20534885105


NeluaはLuaのスクリプトそのままでは動かず、関数の引数と戻り値に型を明記する必要がありました。
https://github.com/hnakamur/tarai-benchmark/blob/269659a6e6d97602e3d853e698bb91eb8d0fbb36/tarai-no-time.nelua

とりあえず手軽にneluaの起動時間込みで計測してみました。

```
k$ /usr/bin/time -f '%e %M' nelua tarai-no-time.nelua
14
1.03 7932
$ /usr/bin/time -f '%e %M' nelua tarai-no-time.nelua
14
1.05 7836
$ /usr/bin/time -f '%e %M' nelua tarai-no-time.nelua
14
1.03 7924
```

[LuaJITでたらい回し関数のベンチマークを試してみた · hnakamur's blog](/blog/2022/12/28/tried-tarai-benchmark-with-luajit/)は起動済み状態で関数のみの処理時間を計測しているので、[luajit-remakeを試してみた · hnakamur's blog](/blog/2022/12/28/tried-luajit-remake/)の結果と比べてみるとLuaJITの約2倍程度の速さでした。

[LuaJITでたらい回し関数のベンチマークを試してみた · hnakamur's blog](/blog/2022/12/28/tried-tarai-benchmark-with-luajit/)のCソースで起動時間込み(面倒なのでclock_gettimeは外してない)も調べてみました。

```
$ /usr/bin/time -f '%e %M' ./tarai_O3
0.438385 14
0.43 1360
$ /usr/bin/time -f '%e %M' ./tarai_O3
0.428702 14
0.42 1316
$ /usr/bin/time -f '%e %M' ./tarai_O3
0.443142 14
0.44 1432
```

Cよりは約2.3倍遅いです。

[Libraries - Nelua](https://nelua.io/libraries/)を見ると、hashmapやvectorもあるし、GCにarenaアロケータもありました。基本は標準ライブラリを使うのがお勧めだけど、Cで書かれたライブラリを利用しやすくするために[C libraries - Nelua](https://nelua.io/clibraries/)も用意されているとのことです。
