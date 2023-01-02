---
title: "Apache Traffic Serverとnginxで使えるLuaJIT用shared dictを作ってみた"
date: 2023-01-01T15:53:38+09:00
lastmod: 2023-01-12T14:08:00+09:00
---
## はじめに

レポジトリは[hnakamur/ats-ngx-lua-shdict](https://github.com/hnakamur/ats-ngx-lua-shdict)です。

作ってみたといっても、0から作り上げたわけではなく、nginxとlua-nginx-moduleの[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)のソースをコピペして改変しただけです。私がLinuxでしか使う予定がないので、対象環境はLinuxのみです。

コミットログを見ると去年の12月11日から作り始めていたので3週間かかっています。

なお、現状はとりあえず実装と単体テストを書いただけで、実運用に耐えるレベルなのかは不明です。が、このタイミングでメモしておかないと、この後他の事をするとだんだん忘れてきて、後からだと書くのが面倒になってくるので今書いておきます。

背景として、私は[NGINX](http://nginx.org/)の[openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module)と[Apache Traffic Server](https://trafficserver.apache.org/)の[Lua Plugin](https://docs.trafficserver.apache.org/en/latest/admin-guide/plugins/lua.en.html)でLuaJITでスクリプトを書いて大変便利に使っています。

その中でも[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)という共有メモリ上のキーバリューストアのような仕組みが便利で、各種設定を登録・参照するのに使っているのですが、Traffic Serverでも似たような仕組みが欲しいなと思っていました。
nginxはワーカープロセスがマルチプロセス構成なのに対して、Traffic Serverはシングルプロセスでマルチスレッドなので、実は普通にメモリ上にデータ構造作ってmutexで排他制御すれば良いという話もあります。

ただ、[Hierarchical Caching](https://docs.trafficserver.apache.org/en/latest/admin-guide/configuration/hierarchical-caching.en.html?highlight=hierarchical%20cache#hierarchical-caching)を使って、かつ1台のサーバにnginxのサービス1組とtrafficserverのサービスを2組動かして、それを複数台並べる構成だと、1台のサーバ上の1組のnginxと2組のtrafficserverのサービス間でもデータを共有したいという思いがありました。

## 共有メモリにアドレスをそのまま書く方式だと複数サービス間では共有できない

[LuaJIT+FFIで共有メモリを試してみた · hnakamur's blog](http://192.168.2.202:1313/blog/2022/12/04/tried-shared-memory-in-luajit-and-ffi/)の次のステップとして、[shm_open](https://manpages.ubuntu.com/manpages/jammy/en/man3/shm_open.3.html)で開いた共有メモリを[mmap](https://manpages.ubuntu.com/manpages/kinetic/en/man3/mmap.3posix.html)でメモリにマップして、その上に[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)のデータ構造を作るのを試してみました。

プロセス終了後も`/dev/shm/`配下に共有メモリのファイル(`/dev/shm/`配下は疑似的なファイルシステムなので実際はメモリ上のデータです)が残るので、再度プロセスを起動した場合はそれを開いて利用するように実装したのですが、Segmentation faultが起きました。

ちょっと考えるとそれは当たり前で、[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)ではポインタのアドレスをそのままメモリ上に書いていて、それが`/dev/shm/`配下の共有メモリに書かれますが、次にプロセスが起動してそれを開いてmmapしたり、別のプロセスから開いてmmapすると、最初とは別のアドレスにマップされるので、保存されていたアドレスの値は変なところを指しているからです。

### 横道: nginxの共有メモリ
なお、nginxの場合は、[managerプロセスで共有メモリを作成](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_cycle.c#L413-L500)して、それを複数のworkerプロセスに渡しているので、同じアドレスのまま参照できているということのようです。そして[ngx_shm_alloc](https://github.com/nginx/nginx/blob/release-1.23.3/src/os/unix/ngx_shmem.c#L14-L28)関数ではLinuxなど`MAP_ANON`が利用できる環境では[mmap (2)](https://manpages.ubuntu.com/manpages/jammy/en/man2/mmap.2.html)で`flags`に`MAP_ANON|MAP_SHARED`を指定して共有メモリを作っています。

この方式だと`/dev/shm/`配下にはファイルは作られず、nginxを終了すると内容は失われ、nginxを再起動すると新たに作られることになります。

## ベースアドレスからのオフセットを書くように改変して対応

そこで、共有メモリ上のデータ構造内ではポインタの代わりにmmapしたときのベースアドレスからのオフセットを持つようにしてみました。

[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)はnginxの[共有メモリ](http://nginx.org/en/docs/dev/development_guide.html#shared_memory)の仕組みの上にスラブアロケータ(ngx_slab_pool_t)、[赤黒木 (ngx_rbtree_t)](http://nginx.org/en/docs/dev/development_guide.html#red_black_tree)、[キュー (ngx_queue_t)](http://nginx.org/en/docs/dev/development_guide.html#queue)を使って実装されています。キューは双方向リンクトリストで共有メモリがいっぱいになったときにLeast Recently Used (LRU)アルゴリズムで古いキーを破棄するために使っています。

### オフセットを表す型定義

オフセットを表す型として[`typedef uintptr mps_ptroff_t;`](https://github.com/hnakamur/ats-ngx-lua-shdict/blob/8565c6e379beec724cdab58dc492ec4caa773dc5/src/mps_slab.h#L18)というのを定義しました(mps_は今回作ったソフトウェアの接頭辞でmulti process sharedの略です)。

C++だと[std::ptrdiff_t - cpprefjp C++日本語リファレンス](https://cpprefjp.github.io/reference/cstddef/ptrdiff_t.html)というのがあるそうなのですが、こちらはdiffでポインタ同士の差分ということで符号付き整数型となっています。

今回表したいのはベースアドレスからのオフセットなので符号無しで良いので、これとは違う名前にしてみました。Cの`off_t`も符号付きなので紛らわしいかもとは思ったのですが、他に良い名前が思いつかず。

元のポインタは対応する構造体へのポインタですが、`mps_ptroff_t`だとどの構造体に対するオフセットだったかという情報は欠落してしまっています。RustやC++ならそれぞれの構造体に対するオフセット型を導入して違う方のオフセットを間違って使わないようにとかしそうな気がします(深く考えずにそんな感じかなと思ってるだけ)が、今回はCなのと構造体の種類も少ししかないのでこれで十分です。

[オフセットとポインタの相互変換用のマクロを定義](https://github.com/hnakamur/ats-ngx-lua-shdict/blob/8565c6e379beec724cdab58dc492ec4caa773dc5/src/mps_slab.h#L55-L57)しています。

```
#define mps_offset(pool, ptr) (mps_ptroff_t)((u_char *)(ptr) - (u_char *)(pool))

#define mps_ptr(pool, offset) ((u_char *)(pool) + (offset))
```

スラブアロケータの`mps_slab_pool_t *pool`が共有メモリのベースアドレスです。
また、NULLポインタに対応するオフセットは `#define mps_nulloff 0` と定義しています。これはpoolの先頭にはスラブアロケータの管理データがあり、スラブアロケータで割り当てられるメモリ領域は絶対にpoolとは異なる値になるため、オフセットが0になることはないからです。

オフセット用の型を用意したら、あとは以下の方針で書き換えていきました。

* スラブアロケータとそれで割り当てる構造体のフィールドのポインタ型を全てオフセット型に変更。
* ローカル変数は基本的にはポインタ型にして、値をオフセットからポインタに変換して保持。
* 構造体のフィールドのオフセットに設定する際に、値をポインタからオフセットに変換して設定。

## 文字列キーのハッシュ関数はngx_crc32_shortからngx_murmur_hash2に変更

[ngx_crc32_short](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_crc32.h#L20-L35)は[uint32_t  ngx_crc32_table16[]](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_crc32.c#L26-L31)をCPUのキャッシュラインのサイズに応じて[ngx_crc32_table_init](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_crc32.c#L105-L129)でアラインしなおすという処理が必要でちょっと面倒なのと、[マイクロベンチマーク](https://github.com/hnakamur/ats-ngx-lua-shdict/commit/e278ac8e4a1589c52e117b96b19c4c9e5b2870ca)をしてみた感じでは[ngx_murmur_hash2](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_murmurhash.c#L11-L52)のほうが約10倍速かったので、こちらに変更しました。

どちらも、入力は長さ指定の文字列で、出力は`uint32_t`と同じです。

## nginxとtrafficserverのログ出力関数の利用

[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)はnginxのモジュールとして実装されていますが、今回作ったのは単なる共有ライブラリでLuaJITから[ffi.load](https://luajit.org/ext_ffi_api.html#ffi_load)で読み込んで使う方式としています。実際はFFIの関数をラップするLuaJITのスクリプトファイルを提供していて、それを[require](http://www.lua.org/manual/5.1/manual.html#pdf-require)して使います。

nginx用とtrafficserver用で別々の共有ライブラリを作るようにしていて、nginx用では
[ngx_log_error](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_log.h#L85-L86)と[ngx_log_debug](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_log.h#L91-L93)を、trafficserver用では
[TSStatus, TSNote, TSWarning, TSError](https://github.com/apache/trafficserver/blob/9.1.4-rc0/include/ts/ts.h#L280-L283)と[TSDebug](https://github.com/apache/trafficserver/blob/9.1.4-rc0/include/ts/ts.h#L2146)を使うようにしています。

nginxの[ngx_log_error](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_log.h#L85-L86)用の[ログレベル定義](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_log.h#L17-L23)とtrafficserverの[TSNote～TSEmergency](https://github.com/apache/trafficserver/blob/9.1.4-rc0/include/ts/ts.h#L280-L286)は数が同じなので、当初は全て使おうかと思ったのですが、TSFatal, TSAlert, TSEmergencyはログ出力後プロセスを終了するようになっていて、一方nginxのほうは全レベルで終了しないという違いがあって、運用時に紛らわしいことになりそうと思ったので、TSFatal, TSAlert, TSEmergencyのレベルはこのライブラリでは使わないことにしました。

ということでnginxとlua-nginx-module内で`NGX_LOG_CRIT`以上のレベルでログ出力していた箇所も`NGX_LOG_ERR`相当に変更しました。

[mps_log.h](https://github.com/hnakamur/ats-ngx-lua-shdict/blob/8565c6e379beec724cdab58dc492ec4caa773dc5/src/mps_log.h)で`mps_log_debug`、`mps_log_status`、`mps_log_note`、`mps_log_warning`、`mps_log_error`を定義してビルド時に`#ifdef`でnginx用のログ関数を使うか、trafficserver用のログ関数を使うか、単体テスト用に標準エラー出力に出力する関数を使うかを切り替えるようにしています。

なお、メッセージのフォーマット文字列内の`%`での指定方法に違いがあるので、真っ当にはnginxかtrafficserverのどちらかに合わせるような関数を書いてラップするほうが良いかもしれません。

nginxのほうは最終的には[ngx_vslprintf](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_string.c#L164-L481)に行きついてこちらは[src/core/ngx_string.c#L90-L119](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_string.c#L90-L119)のフォーマットをサポートしています。

一方trafficserverのほうは最終的には[Diags::print_va](https://github.com/apache/trafficserver/blob/9.1.4-rc0/src/tscore/Diags.cc#L222-L332)に行きついてこれは[vfprintf (3)](https://manpages.ubuntu.com/manpages/jammy/en/man3/vfprintf.3.html)を呼んでいます。

最大長さを指定した文字列出力はnginxでは`%*s`、trafficserverでは`%.*s`と違う指定が必要なので、[mps_log.h](https://github.com/hnakamur/ats-ngx-lua-shdict/blob/8565c6e379beec724cdab58dc492ec4caa773dc5/src/mps_log.h)に`LogLenStr`というマクロを定義してとりあえずしのいでいます。

### 2023-01-02 ログ書式をvsnprintfに統一しました

[e14b679](https://github.com/hnakamur/ats-ngx-lua-shdict/commit/e14b679436c202d7a6d4835e94d0648bb7b4d4b6)と[8cdd4be](https://github.com/hnakamur/ats-ngx-lua-shdict/commit/8cdd4befa63d4038485293e80f78b8ba0a1cd768)のコミットで統一しました。

`"%" PRId64`みたいに書くのは割と面倒なので、[ngx_vslprintf](https://github.com/nginx/nginx/blob/release-1.23.3/src/core/ngx_string.c#L164-L481)をコピペ改変しようかと一度は思ったのですが、書式と引数が一致しないときにコンパイル時に警告が出るのは便利だなと思い直して、nginx用のログ出力をvsnprintfを使って文字列を作ってからnginxのログ出力関数に渡すように改修しました。

また、[tslog.h](https://github.com/hnakamur/ats-ngx-lua-shdict/blob/8cdd4befa63d4038485293e80f78b8ba0a1cd768/src/tslog.h)で使用されていた[Clang format attribute](https://clang.llvm.org/docs/AttributeReference.html#format)を、nginxと標準エラー出力用のログ関数にも付けました。

これで上に書いた`LogLenStr`のマクロは不要になったので直接`"%.*s"`と書くようにしました。
なお、テストでは面倒だったので`"%" PRId64`ではなく`"%ld"`のように書いています。

このへんを試していて気づいたのですが、フォーマット文字列と値の間で改行が入っていると、以下のように警告メッセージにフォーマット文字列が出力されないんですね。

```
src/mps_slab.c:108:9: warning: format specifies type 'int' but the argument has type 'ngx_uint_t' (aka 'unsigned long') [-Wformat]
        mps_pagesize, mps_slab_max_size, mps_slab_exact_size);
        ^~~~~~~~~~~~
src/mps_log.h:11:48: note: expanded from macro 'mps_log_debug'
#define mps_log_debug(tag, ...) TSDebug((tag), __VA_ARGS__)
                                               ^~~~~~~~~~~
1 warning generated.
```

フォーマット文字列と値の間に改行が入っていない場合は、フォーマット文字列と修正後のフォーマットも出力されます。

```
src/mps_slab.c:105:51: warning: format specifies type 'int' but the argument has type 'ngx_uint_t' (aka 'unsigned long') [-Wformat]
    mps_log_debug(MPS_LOG_TAG, "mps_pagesize=%d", mps_pagesize);
                                             ~~   ^~~~~~~~~~~~
                                             %lu
src/mps_log.h:20:48: note: expanded from macro 'mps_log_debug'
#define mps_log_debug(tag, ...) TSDebug((tag), __VA_ARGS__)
                                               ^~~~~~~~~~~
1 warning generated.
```

1回のログ出力で多数の値を出してフォーマット文字列が長くなりがちな私としてはちょっと残念ですが、警告メッセージを見れば分かるので慣れればよいかという気もしました。

## リスト関連のメソッド(lpush, rpush, lpop, rpop, llen)

[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)にはLuaの文字列、Number、booleanの値の設定・取得などのメソッドに加えて、リスト関連のメソッド(lpush, rpush, lpop, rpop, llen)も用意されています。

個人的には使ってないので、非対応にしようかとも思ったのですが、一旦対応してみました。getなどのメソッドはLuaJIT FFI用の関数が実装されているのですが、リスト関連のメソッドはLua用の関数しかなかったのでFFI用の関数に改変して対応しました。

LuaJIT FFI用の関数は普通のCの関数として書けばよいので楽で、これに慣れると[lua_pushlstring](http://www.lua.org/manual/5.1/manual.html#lua_pushlstring)などを使ってLua用の関数を書くのはかなり面倒に感じます。Luaの入出力のスタックから引数を取得したり戻り値をスタックに積むときに、インデクスを随時意識する必要があるのがかなり大変ですし、LuaJIT FFIのほうが実行時の呼び出しも速いとのことなので、個人的にはLuaJIT FFI一択です。

## 単体テストとカバレッジ

単体テストは[ThrowTheSwitch/Unity: Simple Unit Testing for C](https://github.com/ThrowTheSwitch/Unity)というフレームワークを初めて使ってみました。テストの`.c`ファイルを分けるとアサーションエラーの時にファイル名が正しく出ないようだったので、とりあえず`.c`ファイルは1つにしました(深く調査してないです)。

カバレッジは[llvm-cov - emit coverage information](https://llvm.org/docs/CommandGuide/llvm-cov.html)で出力しています。[Targeted Cache Control のライブラリをC言語で書いた · hnakamur's blog](https://hnakamur.github.io/blog/2022/07/09/targeted-cache-control-impl/)で初めて使って、今回が2回目です。行単位ではなく式単位でカバレッジが表示されるのが便利です。

`make test`でテストを実行して`make cov`でカバレッジを出力するようにしています。端末にそのまま出力されるのでtmuxでスクロールをさかのぼってすぐに確認できるのが良いです。

## 関連: Handles are the better pointers

ポインタの代わりにオフセットを使うというので、似た話をどこかで聞いたようなと思ったのですが
[A Practical Guide to Applying Data-Oriented Design](https://media.handmade-seattle.com/practical-data-oriented-design/)
の13:49あたりからのポインタの代わりにインデクスを使うという話でした。

こちらはメモリ使用量削減のために64bitのポインタの代わりに32bitとかのインデクスの整数を使って、
構造体のサイズを削減するという文脈です。

その中で[Handles are the better pointers](https://floooh.github.io/2018/06/17/handles-vs-pointers.html)が紹介されていました([Handles Are the Better Pointers (2018) | Hacker News](https://news.ycombinator.com/item?id=24141541))。

インデクスにするには構造体の種類ごとに別の配列に集める必要があると思うのですが、lua-nginx-moduleだと
[ngx_http_lua_shdict.c#L1495-L1500](https://github.com/openresty/lua-nginx-module/blob/f488965b89238e0bba11c13fdb9b11b4a0f20d67/src/ngx_http_lua_shdict.c#L1495-L1500)のようにノードの構造体とキーと値を連結したものを1回のメモリ割り当てで作成するといういかにもC言語的な手法を使っていてサイズがまちまちなので、インデクス方式にするにはさらに改変が必要になりそうです。

ということで、とりあえず現状で使ってみて問題なければこのままでも良いかなという気分です。
もし、将来さらに性能が必要となったときには検討してもよいかもしれません。

## データベースではmmapは使うべきではないという話

以前[CMU Database Group - YouTube](https://www.youtube.com/@CMUDatabaseGroup)でAndy Pavloさんのデータベース講義のオンラインコースを見たのですが、その中でもデータベースではmmapを使うべきではないという話が出ていました。

検索してみると[Issues with mmap – Shekhar Gulati](https://shekhargulati.com/2022/01/23/issues-with-mmap/)に良いまとめがありました。

私の場合はLinux対応のみで良いので、Windowsでmmapが使えないというのは置いておくとして、ディスクへの書き込みが同期的でブロッキングするのが良くないというのと、ディスクへの読み書きの際にキャッシュ管理をカーネル任せにするのではなくデータベースシステムが自分で管理すべきという話です。

データベースの場合はトランザクションのコミットでディスクに確実に書き込んだことを確認する必要があるので納得です。ちなみに[etcd-io/bbolt: An embedded key/value database for Go.](https://github.com/etcd-io/bbolt)は読み取り専用でmmapを使って書き込みは自前で行っています。

一方、私の用途は元データは別にあって、キャッシュ的に保持する用途なので、そこまで厳密に書き込みを制御できなくても大丈夫です。RAMディスク上のファイルであれば、同期的でブロッキングというのも特に問題にならないのかなと思っていたところに[linux - Using pthread mutex shared between processes correctly - Stack Overflow](https://stackoverflow.com/questions/42628949/using-pthread-mutex-shared-between-processes-correctly)で`shm_open`を使った共有メモリのほうがさらに良いと知ってこれで良さそうとなった次第です。

## 共有メモリに加えてメモリマップトファイルも対応してみました

一方で、たまにしか書き込みしない用途ならディスク上のファイルでも良いかも、と思って`shm_open`の代わりに`open`でファイルを作るまたは開くのも対応してみました。引数ではファイル名を指定するようにして`/dev/shm/`で始まっていれば`shm_open`を使い、そうでなければ`open`を使うようにしているだけです。
