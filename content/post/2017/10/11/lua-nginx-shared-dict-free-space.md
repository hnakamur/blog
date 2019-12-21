+++
title="lua-nginx-moduleのshared dictの空き容量について"
date = "2017-10-11T11:10:00+09:00"
tags = ["nginx", "lua"]
categories = ["blog"]
+++


## はじめに

[openresty/lua-nginx-module: Embed the Power of Lua into NGINX HTTP servers](https://github.com/openresty/lua-nginx-module) の
[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)
は複数ワーカープロセス間でデータを共有することができ、非常に便利です。

使用する際は
[lua_shared_dict](https://github.com/openresty/lua-nginx-module#lua_shared_dict) ディレクティブ
で以下のように shared dict の名称とサイズを指定する必要があります。

```text
lua_shared_dict dogs 10m;
```

しかし、このサイズをどれぐらいにしたらよいかわからず、適当に設定していました。

そこでコードを読んで、おおよそのメモリ使用量の目安の計算について調査しました。
また、概略の残り容量を把握するための仕組みを追加するプルリクエストを送ってマージされました。
ということでメモしておきます。

## shared dictのメモリ管理

[lua-nginx-moduleのshared dictのコードリーディング](/blog/2017/09/27/code-reading-lua-nginx-shared-dict/) で shared dict のメモリ割り当てについてコードを読んでみました。

https://github.com/openresty/lua-nginx-module/tree/bf14723e4e7749c989134c029742185db1c78255

要約すると以下のようになっています。

* `lua_shared_dict` で宣言したサイズの共有メモリを mmap で確保
* slab allocatorで 〜8, 9〜16, 17〜32, 33〜64, 65〜128, 129〜256, 257〜512, 513〜1024, 1025〜2048 バイト用に9個のスロットを作成
* 割り当てた共有メモリのうちスラブアロケータとスロットの管理領域を除いた残りを4KiB単位のページに区切ってリンクリストで管理
* キーと値を追加するときはキーと値に管理情報を加えたサイズから対応するスロットを決定
* そのスロットにページがないか割り当て済みのページに空きがなければ、空きページのリンクリストからページを取得してスロットに割り当てる。2049バイト以上のときはスロットを使わず直接空きページを使用する。
* スロットに割り当て済みのページ内に空きがあるときは、ページ内の空き領域を使用する。

また `ngx_http_lua_shdict_init_zone` 関数で slab allocator から2つメモリ割り当てを行っています。

1つめは `sizeof(ngx_http_lua_shdict_shctx_t)` = 80バイトを割り当てるので128バイトのスロットの1エントリを消費します。

[lua-nginx-module/ngx_http_lua_shdict.c#L108](https://github.com/openresty/lua-nginx-module/blob/bf14723e4e7749c989134c029742185db1c78255/src/ngx_http_lua_shdict.c#L108)

```c
ctx->sh = ngx_slab_alloc(ctx->shpool, sizeof(ngx_http_lua_shdict_shctx_t));
```

2つめは `sizeof(" in lua_shared_dict zone \"\"") + shm_zone->shm.name.len` バイトの割り当てです。

[lua-nginx-module/ngx_http_lua_shdict.c#L120](https://github.com/openresty/lua-nginx-module/blob/bf14723e4e7749c989134c029742185db1c78255/src/ngx_http_lua_shdict.c#L120)

```c
len = sizeof(" in lua_shared_dict zone \"\"") + shm_zone->shm.name.len;
```

.. code-block:: text

        (gdb) print sizeof(" in lua_shared_dict zone \"\"")
        $4 = 28

shared dictの名前が5〜36バイトであれば33〜64バイト用のスロットのエントリを1つ消費します。
名前が4バイト以下なら17〜32バイトのスロットになりますし、37〜100バイトなら65〜128バイトのスロットになります。 

名前が 37〜100バイトで128バイトのスロットを使う場合は、上記の `ngx_http_lua_shdict_shctx_t` の割り当てに使うのと同じページを使うことになります。
が、ほとんどの場合はそこまで長い名前にはしないでしょうから、 `ngx_http_lua_shdict_shctx_t` で128バイトのスロットに1ページ、 `sizeof(" in lua_shared_dict zone \"\"") + shm_zone->shm.name.len` で32バイトか64バイトのスロットに1ページが初期状態で割り当てられることになります。


## ページ数の見積もり

例えば `lua_shared_dict` で `12k` と最低容量で宣言していたケースを考えます。

管理領域の合計は
`sizeof(ngx_slab_pool_t) + 9 * (sizeof(ngx_slab_page_t) + sizeof(ngx_slab_stat_t))`
で、以下の計算により 704 バイトです。

```text
>>> 200 + 9 * (24 + 32)
704
```

この704バイトを除いた領域を4KiB単位のページに分割します。この例ではページ数は以下の計算により 2 です。

```text
>>> (12 * 1024 - 704) // 4096
2
```

しかし、上記の通り `ngx_http_lua_shdict_init_zone` で 64バイトと128バイトのスロットを1つずつ使っていますので、それぞれのスロットにページが割り当てられて、空きページ数は0となっています。

ですので、この後これ以外のスロットに対応するメモリ割り当てを行おうとすると空きページが無いのでエラーになります。

## エントリ追加時のメモリ消費量

以下のコードの通り、追加しようとするキーの長さ `key.len` と値の長さ `value.len` に
`offsetof(ngx_rbtree_node_t, color)` と `offsetof(ngx_http_lua_shdict_node_t, data)` を加えたサイズのメモリ割り当てを行います。

[lua-nginx-module/ngx_http_lua_shdict.c#L1164-L1167](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_shdict.c#L1164-L1167)

```c
n = offsetof(ngx_rbtree_node_t, color)
    + offsetof(ngx_http_lua_shdict_node_t, data)
    + key.len
    + value.len;
```

`offsetof(ngx_rbtree_node_t, color)` は32、 `offsetof(ngx_http_lua_shdict_node_t, data)` は36だったので、 68 + キーの長さ + 値の長さということになります。

例えば、 `12k` のshared dictではキーの長さ4バイト、値の長さ57バイトのエントリを追加しようとすると 68 + 4 + 57 = 129バイトで256バイトのスロットにエントリ追加が必要になりますが、空きページはもう無いので

[ngx.shared.DICT.set](https://github.com/openresty/lua-nginx-module#ngxshareddictset)

```c
success, err, forcible = ngx.shared.DICT:set(key, value, exptime?, flags?)
```

で `err` に `no memory` というエラーが返ってきます。

一方、キーの長さが8バイト、値の長さが8バイトであれば、 68 + 8 + 8 = 84バイトなので128バイトのスロットを1つ消費します。128 - 68 = 60なのでキーと値のサイズ合計が60バイト以下であれば128バイトのスロットというこになります。

128バイトのスロットでは4KiBの1ページあたりのエントリ数は

```text
>>> 4096 // 128
32
```

です。ただし、128バイトのスロットの最初のページは初期化時に `sizeof(ngx_http_lua_shdict_shctx_t)` で1エントリ消費されているので、残りのエントリ数は31です。

以下のような設定

```text
lua_shared_dict cats 12k;

server {
    // ...

    location /cats2 {
        content_by_lua_block {
            local cats = ngx.shared.cats;
            for i = 1, 33 do
                local key = string.format('key%05d', i)
                local val = string.format('val%05d', i)
                local success, err, forcible = cats:set(key, val)
                if not success or err ~= nil or forcible then
                    ngx.say(string.format("failed to set to shared.dict, i=%d, success=%s, err=%s, forcible=%s", i, success, err, forcible))
                end
            end
            for i = 1, 3 do
                local key = string.format('key%05d', i)
                local val = cats:get(key)
                ngx.say(string.format("key=%s, val=%s", key, val))
            end
        }
    }
}
```

で /cats にアクセスしてみると i が 32 以降は forcible が true になります。

```console
$ curl localhost/cats2
failed to set to shared.dict, i=32, success=true, err=nil, forcible=true
failed to set to shared.dict, i=33, success=true, err=nil, forcible=true
key=key00001, val=nil
key=key00002, val=nil
key=key00003, val=val00003
```

`forcible` については `ngx.shared.DICT.set` のドキュメントに

    forcible: a boolean value to indicate whether other valid items have been removed forcibly when out of storage in the shared memory zone.

と説明があります。

ソースコードでは以下の部分に対応します。

[lua-nginx-module/ngx_http_lua_shdict.c#L2759-L2785](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_shdict.c#L2759-L2785)

```c {linenos=table,linenostart=2413}
node = ngx_slab_alloc_locked(ctx->shpool, n);

if (node == NULL) {

    ngx_log_debug2(NGX_LOG_DEBUG_HTTP, ctx->log, 0,
                   "lua shared dict incr: overriding non-expired items "
                   "due to memory shortage for entry \"%*s\"", key_len,
                   key);

    for (i = 0; i < 30; i++) {
        if (ngx_http_lua_shdict_expire(ctx, 0) == 0) {
            break;
        }

        *forcible = 1;

        node = ngx_slab_alloc_locked(ctx->shpool, n);
        if (node != NULL) {
            goto allocated;
        }
    }

    ngx_shmtx_unlock(&ctx->shpool->mutex);

    *err = "no memory";
    return NGX_ERROR;
}
```

分岐としては以下のケースになります。

* 2413行の `ngx_slab_alloc_locked` で `NULL` が返る
* 2423行の `ngx_http_lua_shdict_expire` で 0以外が返る
* 2427行で `*forcible` に1が設定される
* 2429行で `ngx_slab_alloc_locked` で `NULL` 以外が返る

つまり、空きページが無い場合は古いキーを破棄させてスロットに空きを作って新しいキーを設定しています。
上記の例では `key00001` と `key00002` のキーが破棄されており値を参照しても `nil` になってしまいます。

## 空き容量の確認のためのcapacity, free_spaceメソッド

空き容量を監視するために以下のプルリクエストを送りました。

* [Add FFI methods for taking stats to ngx.shared.DICT by hnakamur · Pull Request #1149 · openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module/pull/1149)
* [Add get_stats method to ngx.shared.DICT by hnakamur · Pull Request #141 · openresty/lua-resty-core](https://github.com/openresty/lua-resty-core/pull/141)

lua-nginx-module だけではなく lua-resty-core にもプルリクエストを送っているのは、ngx.shared.DICT のメソッドは C API として実装してLuaから呼び出す方式から luajit の [FFI Library](http://luajit.org/ext_ffi.html) を利用して呼び出す方式に移行中だったからです。

内容ですが、当初は `ngx_slab_stat_t` の `total` を合計すれば使用量合計が出せるのではないかと思ったのですが、コードを読んで考えた結果、監視項目としては空きページサイズ合計を見るのが良いという結論に至りました。

あるスロットに割り当て済みのページに空きがある場合は、同じスロットの割り当ては成功するのですが、上記の例のように別のスロットのページが埋まっていて空きページも無い場合は no memory のエラーが発生するからです。

最終的には以下のコミットになりました。

* [feature: shdict: added pure C API for getting free page size and tota… · openresty/lua-nginx-module@f829065](https://github.com/openresty/lua-nginx-module/commit/f829065b794025c856c9f86d469395e464e782ed)
* [feature: resty.core.shdict: added new methods free_space() and capaci… · openresty/lua-resty-core@3343ea1](https://github.com/openresty/lua-resty-core/commit/3343ea159201da764e9a0f78f0857e5e7be11cf2)

追加でドキュメントの記法修正のプルリクエストも送ってマージされています。

[Fix strike-through in shdict.free_space markdown doc by hnakamur · Pull Request #1170 · openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module/pull/1170)

`ngx.shared.DICT` の `capacity` メソッドで `lua_shared_dict` ディレクティブで設定した容量をバイト数で取得できます。

`ngx.shared.DICT` の `free_space` メソッドで slab allocator の空きページの合計バイト数が取得できます。

監視用のロケーションを作って free_space の値を capacity で割って100をかければ空き容量をパーセントで計算できますし、free_space そのものを見れば空き容量のバイト数が得られます。

ただし、上記の通りこれはあくまで目安であって実際には free_space がゼロであっても、キーの追加に成功するケースもあります。ですが余裕を持っておきたいので、悲観的なケースに倒して空き容量を計算しています。


## capacity, free_spaceメソッド入りのnginxのrpm, debパッケージ

CentOS 6/7用のrpmパッケージとUbuntu 16.04 用のdebパッケージをビルドしました。

* [hnakamur/nginx Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/nginx/)
* [nginx with thirdparty modules : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/nginx)

## まとめ

* `lua_shared_dict` で指定したサイズから 704 バイトを引いたものを4096バイトで割ってページ数を計算する
* slab allocatorには8, 16, 32, 64, 128, 256, 512, 1024, 2048 バイト用に9個のスロットがあり、各スロットにページを割り当てて分割して使用する。
* 例えば128バイトのスロットでは実際に使うのが80バイトでも128バイトを消費する。
* 2049バイト以上の割り当てにはスロットは使わず直接空きページを割り当てる。
* shared dictの1エントリはキーと値のサイズに加えて管理情報として68バイトが必要。例えばキーと値が8バイトでも 8 + 8 + 68 = 84 バイトとなり128バイトのスロットを1つ消費することになる。
* あるスロットに対して割り当て済みのページが無く空きページも無い場合は no memory のエラーが返る。
* あるスロットに対してページが割り当て済みだが空きページが無い場合は、古いキーを強制的に expire して空きを作ってキーを設定し、戻り値の forcible が true になる。
