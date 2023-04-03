---
title: "LMDBをGoとnginxとtrafficserver上のLuaJITから使ってみた"
date: 2023-04-03T21:21:25+09:00
---

## はじめに

[Apache Traffic Serverとnginxで使えるLuaJIT用shared dictを作ってみた · hnakamur's blog](https://hnakamur.github.io/blog/2023/01/01/ats-ngx-lua-shdict/#%E3%83%99%E3%83%BC%E3%82%B9%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9%E3%81%8B%E3%82%89%E3%81%AE%E3%82%AA%E3%83%95%E3%82%BB%E3%83%83%E3%83%88%E3%82%92%E6%9B%B8%E3%81%8F%E3%82%88%E3%81%86%E3%81%AB%E6%94%B9%E5%A4%89%E3%81%97%E3%81%A6%E5%AF%BE%E5%BF%9C)ものの、実際には使わないままでした。

## LMDB

その後、ライブラリとして使えるキーバリューストアを調べて[LMDB (Lightning Memory-Mapped Database)](https://www.symas.com/lmdb)にたどり着きました。
説明を読むとOpenLDAP用に開発されたとのことですが、[Symas LMDB Tech Info](https://www.symas.com/symas-lmdb-tech-info)の Other Projects を見ると他にも多数のプロジェクトから利用されています。
[OpenLDAP, Source Repository](https://www.openldap.org/software/repo.html)にリポジトリのリンクがあり、GitHubにも読み取り専用の[ミラー](https://github.com/LMDB/lmdb)があります。

## nginx + LuaJIT 用のモジュール

さらに、nginx + LuaJIT 用のモジュール [Kong/lua-resty-lmdb](https://github.com/Kong/lua-resty-lmdb) もあり、それについての記事が [【日本語訳ブログ】Kong Hybrid 展開と DB レス展開のための新しいストレージ エンジン - KongHQ](https://jp.konghq.com/blog/new-storage-engine-for-kong-hybrid-and-db-less-deployments) にありました。まずは、こちらを試してみたのですが、私は trafficserver の LuaJIT からも LMDB を使いたいのでラッパーライブラリを自作することにしました。

## nginx と trafficserver の LuaJIT から使えるラッパーライブラリを自作してみた

* レポジトリ: https://github.com/hnakamur/ngx-ats-lmdb
* Ubuntu 用 deb パッケージのソースレポジトリ: https://github.com/hnakamur/ngx-ats-lmdb-deb

このラッパーライブラリは、nginx のモジュールや trafficserver のプラグインとしては作っていません。
そうではなく、 C 言語で書いた LMDB の薄いラッパーの共有ライブラリとそれを使った LuaJIT 用の Lua のライブラリで構成されています。
この Lua のライブラリをロードできるように適宜 [package.path](http://www.lua.org/manual/5.1/manual.html#pdf-package.path) を設定して使う想定です。

LuaJIT 単体から利用する例が [nal_lmdb_stderr_ex.lua](https://github.com/hnakamur/ngx-ats-lmdb/blob/005c1ec5d2558f34c4857ded1e0a78c5731158a7/nal_lmdb_stderr_ex.lua) にあります。
1行目の

```lua
local lmdb = require "nal_lmdb_stderr"
```

の `"nal_lmdb_stderr"` のところを、nginxで使う場合は `"nal_lmdb_ngx"`、trafficserverで使う場合は `"nal_lmdb_ats"` に変える必要があります。

また、 `lmdb.env_init` の呼び出しは nginx の場合は [init_worker_by_lua](https://github.com/openresty/lua-nginx-module#init_by_lua_file) ではなく [init_worker_by_lua](https://github.com/openresty/lua-nginx-module#init_worker_by_lua_file) で行う必要があります。trafficserver の [Lua プラグイン](https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/plugins/lua.en.html) では `__init__` 関数内で行います。

### ログ出力について

`nal_lmdb_{stderr,ngx,ats}` の違いは [lib/log/](https://github.com/hnakamur/ngx-ats-lmdb/tree/005c1ec5d2558f34c4857ded1e0a78c5731158a7/lib/log) ディレクトリのログ出力の実装だけです。stderrでは標準エラー出力にログ出力し、nginxではnginxのログ出力APIを呼び出してエラーログファイルに出力し、trafficserverではtrafficserverのログ出力APIを呼び出してtrafficserverのログファイルに出力するようになっています。

nginxのログ出力APIはnginxのソースコードをコピーして改変したサブセットを [lib/log/](https://github.com/hnakamur/ngx-ats-lmdb/tree/005c1ec5d2558f34c4857ded1e0a78c5731158a7/lib/log) ディレクトリに置いてあります。もし将来 nginx のログ出力API周りの実装が変更された場合は、こちらも追随する必要があります。

### MDB_env *型のインスタンスを保持するグローバル変数

[src/nal_lmdb.c#L8-L20](https://github.com/hnakamur/ngx-ats-lmdb/blob/005c1ec5d2558f34c4857ded1e0a78c5731158a7/src/nal_lmdb.c#L8-L20) で `MDB_env *` 型のインスタンスを保持する `nal_env_t` 型とその型のグローバル変数を定義しています。そしてこのグローバル変数は[pthread_once](https://manpages.ubuntu.com/manpages/jammy/en/man3/pthread_once.3.html)で一度だけ初期化するようにしています。

これは LMDB の [intro.doc#L49-L52](https://github.com/LMDB/lmdb/blob/3947014aed7ffe39a79991fa7fb5b234da47ad1a/libraries/liblmdb/intro.doc#L49-L52) の説明を読んでそのようにしています。

そもそも共有ライブラリ内にグローバル変数を定義して良いのかというのが私はよくわかってなかったのですが、[c - can I declare a global variable in a shared library? - Stack Overflow](https://stackoverflow.com/questions/39394971/can-i-declare-a-global-variable-in-a-shared-library)によるとオペレーティングシステムに依存する話らしいです。とりあえず Ubuntu で試してみた感じでは、これで期待通り動いているようです。が、また軽く動作確認しただけなので今後問題が発覚する可能性はあり得ます。

## Goでは github.com/bmatsuo/lmdb-go を使いました

最初 https://github.com/armon/gomdb を試してみたのですが、サンプルコードを書いてビルドするとエラーが出たので、 https://github.com/bmatsuo/lmdb-go にしました。
[lmdb package - github.com/bmatsuo/lmdb-go/lmdb - Go Packages](https://pkg.go.dev/github.com/bmatsuo/lmdb-go/lmdb) に分かりやすい説明があり [Example](https://pkg.go.dev/github.com/bmatsuo/lmdb-go/lmdb#example-package) と [Example (Worker)](https://pkg.go.dev/github.com/bmatsuo/lmdb-go/lmdb#example-package-Worker) をベースに少し改変するだけで、私がやりたいことは実現できて簡単で良かったです。



