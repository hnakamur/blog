---
title: "LuaJIT+FFIで共有メモリを試してみた"
date: 2022-12-04T21:23:06+09:00
---

## はじめに

[openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module) の [ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict) のような仕組みが [Apache Traffic Server™](https://github.com/apache/trafficserver) の
[Lua Plugin](https://docs.trafficserver.apache.org/en/latest/admin-guide/plugins/lua.en.html) にも欲しいなあと以前から思っていました。

私の場合は公式の [Lua](https://www.lua.org/) の実装ではなく [LuaJIT](https://luajit.org/) を使用していますので、複数の LuaJIT の VM でデータを共有して排他制御しつつ読み書きしたいというわけです。NGINX の場合はワーカーがマルチプロセス構成なのでプロセス間で参照できる共有メモリが必要です。Traffic Server の場合はシングルスレッド・マルチスレッドですが、可能なら同じサーバ上で稼働している NGINX とも共有したいという思いがあって、そうなるとやはりマルチプロセスとなります。

マルチプロセスでの排他制御について、以前調べたときは良い方法を見つけられず諦めていたのですが、改めて検索してみると [linux - Using pthread mutex shared between processes correctly - Stack Overflow](https://stackoverflow.com/questions/42628949/using-pthread-mutex-shared-between-processes-correctly) というページが見つかりました。ここに書かれている手法を試してみたので、その際に調べたり試したりしたことをメモしておきます。

試してみたソースコードは https://github.com/hnakamur/luajit-pshared-mmapf-experiment にあります。

## マルチプロセスで共有メモリを使う際の要約

* [shm_open](https://manpages.ubuntu.com/manpages/jammy/en/man3/shm_open.3.html)で共有メモリを作成または開いて[mmap](https://manpages.ubuntu.com/manpages/kinetic/en/man3/mmap.3posix.html)でメモリにマップすると複数のプロセス間で共有できる。
    * `mmap`では`MAP_SHARED`か`MAP_SHARED_VALIDATE`を指定。
    * 存在しない場合に作成する処理を排他制御するには`shm_open`で`O_CREAT`と`O_EXCL`を指定する。
* マップしたメモリ上に`pthread_mutex_t`か`pthread_rwlock_t`のインスタンスを作って排他制御することができる
    * 複数プロセスで共有して使うため、作成時に[pthread_mutexattr_setpshared](https://manpages.ubuntu.com/manpages/jammy/en/man3/pthread_mutexattr_setpshared.3.html)か[pthread_rwlockattr_setpshared](https://manpages.ubuntu.com/manpages/kinetic/en/man3/pthread_rwlockattr_setpshared.3posix.html)で`PTHREAD_PROCESS_SHARED` を指定。
    * `pthread_rwlock_t`はデフォルトではreader優先だが、非標準でGNU拡張の[pthread_rwlockattr_setkind_np](https://manpages.ubuntu.com/manpages/jammy/en/man3/pthread_rwlockattr_setkind_np.3.html)を使えばwriter優先にもできる。
    * 今回は試してないが[man 7 shm_overview](https://manpages.ubuntu.com/manpages/jammy/en/man7/shm_overview.7.html)によるとPOSIXセマフォを使う方法もある ([man 7 sem_overview](https://manpages.ubuntu.com/manpages/jammy/en/man7/sem_overview.7.html)参照)。

## 排他制御にmutexとrwlockのどちらを使うかとrwlockのreader/writer starvationについて

NGINXは共有メモリの排他制御に独自実装のmutex ([src/core/ngx_shmtx.h](https://github.com/nginx/nginx/blob/release-1.23.2/src/core/ngx_shmtx.h))を使っています。[src/core/ngx_cycle.c#L413-L500](https://github.com/nginx/nginx/blob/release-1.23.2/src/core/ngx_cycle.c#L413-L500)で共有メモリを作成していて、そこから呼ばれる[ngx_init_zone_pool](https://github.com/nginx/nginx/blob/release-1.23.2/src/core/ngx_cycle.c#L951-L1014)関数内の[src/core/ngx_cycle.c#L1007](https://github.com/nginx/nginx/blob/release-1.23.2/src/core/ngx_cycle.c#L1007)で[ngx_shmtx_create](https://github.com/nginx/nginx/blob/release-1.23.2/src/core/ngx_shmtx.c#L18-L43)関数を呼んでいます。

mutexではなくrwlockのほうが複数のreaderが同時に実行できて良さそうなのに、なぜmutexにしてるんだろう、なぜ[src/core/ngx_rwlock.h](https://github.com/nginx/nginx/blob/release-1.23.2/src/core/ngx_rwlock.h)と単一プロセス用のはあるのに`ngx_shrwlock`は無いんだろうという素朴な疑問がありました。

[embeddedmonologue - rwlock and reader/writer starvation](https://sites.google.com/site/embeddedmonologue/home/mutual-exclusion-and-synchronization/rwlock-and-reader-writer-starvation?pli=1)というブログにrwlockではreader starvationとwriter starvationの両方を防ぐことはできないと説明されていました。利用ケースに応じて、reader優先にしてwriter starvationは許容するか、writer優先にしてreader starvationは許容するか、どちらかを選ぶ必要があります。

これを知って、利用ケースを限定できないような汎用的な仕組みを提供するとなるとmutexにしておいたほうが無難だなと納得しました。

## [The Allegory SDK](https://github.com/allegory-software/allegory-sdk)がLuaJIT＋FFIでコードを書く教材として役立つ

[luapower - The LuaJIT distribution for Windows, Linux and OS X](https://luapower.com/) (2022-12-04現在証明書期限切れになってました。[file-show-cert-info-server-sh](https://gist.github.com/hnakamur/2021a1a42c9d449517240ba2a185cf53#file-show-cert-info-server-sh)で調べると`notAfter=Dec  3 07:11:35 2022 GMT`でした)のコードを時々参考にしていたのですが、更新停止のお知らせとアクティブに開発中の[The Allegory SDK](https://github.com/allegory-software/allegory-sdk)へのリンクがあって知りました。

サーバサイドはLuaJITで書かれていてLinux、macOS、Windowsに対応しています。ですが私の場合はLinuxのみで良いのと、細かいところでいろいろ調整したいので、そのまま利用するのではなくコードを参考にしました。

`pthread_mutex`と`pthread_rwlock`のFFI周りのコードはここから頂きました。感謝！

## LuaJITの[ffi.metatype](https://luajit.org/ext_ffi_api.html#ffi_metatype)の使い方も学べた

また[The Allegory SDK](https://github.com/allegory-software/allegory-sdk)のコードを見て、[ffi.metatype](https://luajit.org/ext_ffi_api.html#ffi_metatype)の使い方も学びました。
[pshared_rwlock.lua](https://github.com/hnakamur/luajit-pshared-mmapf-experiment/blob/main/pshared_rwlock.lua)で`pthread_rwlock_t`をラップしてメソッドを追加するのに使っています。

## Goのエラー処理を参考にして構造化エラーのコードを書いてみた

ここで突然Goの話になりますが、[errors: add support for wrapping multiple errors · Issue #53435 · golang/go](https://github.com/golang/go/issues/53435)は個人的にはかなり嬉しいと思っています。今までだと複数エラーが出てもreturnで返せるのは1つだけなので、残りはログ出力するしかありませんでした。エラーのログは呼ばれた側で出力するのではなく、呼び出し側がにエラーを返してそちらで1回だけログ出力するのが理想だと私は思っています。呼ばれた側で出力するとログが一か所ではなく分散してしまい確認が大変なので。

また、[Proposal: Structured Logging](https://go.googlesource.com/proposal/+/master/design/56345-structured-logging.md)が来たことで、構造化エラーを文字列化するのではなく構造を維持したままログ出力するのもしやすくなりそうということでこちらも期待しています。

ということでLuaJITでコードを書く場合も、エラーを構造化できないかと思って今回書いてみました ([errors.lua](https://github.com/hnakamur/luajit-pshared-mmapf-experiment/blob/main/errors.lua))。といってもGoの[errors package](https://pkg.go.dev/errors@go1.19.3)のような`errors.Is`や`errors.As`のような判定の仕組みはなくて、エラーの値を構築するところだけです。

エラーは`Error`のインスタンスとして生成し、必要に応じて属性をフィールドとして設定できます。
ログ出力時は`error`メソッドを呼ぶと[cJSON](https://github.com/DaveGamble/cJSON)で文字列化します。

エラーインスタンスのフィールドを見てエラー処理を分岐する処理は以下のような感じで書けます。

```lua
    local f, err = open(shm_name, map_len)
    if err ~= nil then
        if err.errno ~= errors.ENOENT and err.errno ~= errors.EACCES then
            return nil, err
        end

        -- err.errnoがerrors.ENOENTかerrors.EACCESの場合のエラー処理
```

## Visual Studio Code の[Lua拡張](https://marketplace.visualstudio.com/items?itemName=sumneko.lua)が便利

今回初めて使ってみたのですが便利でした。静的型付けではないLua言語でここまで出来るのかと驚きました。

コードフォーマットも出来ますし、ホバーで関数などの定義が表示されますし、Rename Symbolでは参照側のファイルも連動して変更されました (ただこれはされない場合もあるようです。詳しく調べてないです)。

またnilチェックしないで参照しているとPROBLEMSに警告が出るというのもすごいなと思いました。

ただ、Goっぽく `local value, err = some_function()` のように値とエラーを返すようにしていると、errが非nilの場合にreturnで抜けると、その後はvalueは非nilなんだけどなー(と言っても関数の実装次第)、と思いつつ、上の警告を消すために以下のようにnilチェックを入れるようにしてみました。

unreachableは[Rustのunreachable](https://doc.rust-lang.org/std/macro.unreachable.html)や[Zigのunreachable](https://ziglang.org/documentation/master/#unreachable)の名前を頂きました。

```lua
local ms, err = mmap_shm.open_or_create(shm_name, map_len,
    pshared_rwlock.PTHREAD_RWLOCK_PREFER_WRITER_NONRECURSIVE_NP)
if err ~= nil then
    print(err:error())
    return
end
if ms == nil then
    return errors.unreachable()
end
-- この下でmsを参照。
```

## LuaJIT+FFIでuint64を扱うためのハック

今回の例の最終版では使わなくなっていますが、LuaJIT+FFIでuint64を扱うコードも[The Allegory SDK](https://github.com/allegory-software/allegory-sdk)の[fs.lua#L1375-L1388](https://github.com/allegory-software/allegory-sdk/blob/45ce7d77481391e9c5f631bcd9c97ee65b25ca21/lua/fs.lua#L1375-L1388)から頂きました ([uint64.lua](https://github.com/hnakamur/luajit-pshared-mmapf-experiment/blob/main/uint64.lua))。

Luaの数値型はfloat64で64bit整数の範囲の数は表せないので、以下の共用体を使って32bit整数を2つ指定して64bit整数を作ります (この共用体はLittle Endian用です)。

```c
	union {
		struct { uint32_t lo; uint32_t hi; };
		uint64_t x;
	}
```

[fs.lua#L1375-L1388](https://github.com/allegory-software/allegory-sdk/blob/45ce7d77481391e9c5f631bcd9c97ee65b25ca21/lua/fs.lua#L1375-L1388)ではインスタンスを1つだけ作って使いまわす方式ですが、[uint64.lua](https://github.com/hnakamur/luajit-pshared-mmapf-experiment/blob/main/uint64.lua)では、その都度インスタンスを生成する方式にしてみました。FFIの関数に2つ以上の64bit引数を渡す場合はこの方式が必要になるはずということで。

[Creating cdata Objects](https://luajit.org/ext_ffi_api.html#create)に`ffi.new()`を何度も呼ぶ場合は`ffi.typeof()`を一度読んで戻り値の関数をコンストラクタとして呼び出してインスタンス生成するほうがパフォーマンスが良いと書いてあったので、そのようにしてみました。

```lua
local ffi = require "ffi"

local uint64_union_t = ffi.typeof [[
  union {
    struct { uint32_t lo; uint32_t hi; };
    uint64_t x;
  }
]]

local function split(x)
    local m = uint64_union_t()
    m.x = x
    return m.hi, m.lo
end

local function join(hi, lo)
    local m = uint64_union_t()
    m.hi, m.lo = hi, lo
    return m.x
end
```

## おわりに

長らく方法がわからずに諦めていたマルチプロセスでの共有メモリの使い方が[linux - Using pthread mutex shared between processes correctly - Stack Overflow](https://stackoverflow.com/questions/42628949/using-pthread-mutex-shared-between-processes-correctly)で知れて非常にありがたいです。

また今回の例を書いてみてLuaJIT+FFIでの実装スキルが以前よりは上がった気がします。
[The Allegory SDK](https://github.com/allegory-software/allegory-sdk)は参考になりまくりで本当に感謝しています。

LuaJIT+FFIは[ffi.string(ptr \[,len\])](https://luajit.org/ext_ffi_api.html#ffi_string)でコピーが発生するという不利な点もあるのですが、まだまだお世話になるので感謝しつつ使っていきたいところです。

また、[Building the fastest Lua interpreter.. automatically!](https://sillycross.github.io/2022/11/22/2022-11-22/index.html)の[luajit-remake/luajit-remake: An ongoing attempt to re-engineer LuaJIT from scratch](https://github.com/luajit-remake/luajit-remake)も気になるので今後試してみたいところです。
