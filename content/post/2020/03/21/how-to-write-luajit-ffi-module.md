---
title: "LuaJIT FFIでモジュールを書く時のハウツー"
date: 2020-03-21T23:10:18+09:00
---

## はじめに

[XMLSecでの証明書検証のコードリーディング · hnakamur's blog](/blog/2020/03/17/xmlsec-verify-code-reading/) の結果を元に [hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider) で SAML レスポンスを検証する処理を外部コマンド呼び出し方式から LuaJIT FFI でのライブラリ関数呼び出し方式に書き換えました。
[Add response:verify_response_memory method by hnakamur · Pull Request #4 · hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider/pull/4)

今回の作業で LuaJIT FFI でモジュールを書く際の知見が少し溜まったのでメモしておきます。とは言ってもガーベジコレクションといった深いところは触ってないので対象外です。

## 背景: なぜ C 言語で Lua 用のモジュールを書くのではなく LuaJIT FFI でモジュールを書くのか

場合によりますが、そのほうが動作が速いからです。 [When FFI Function Calls Beat Native C « null program](https://nullprogram.com/blog/2018/05/27/) に詳しい説明があります。

## 参考資料

* [Lua 5.1 Reference Manual - contents](http://www.lua.org/manual/5.1/index.html)
    * [Extensions](https://luajit.org/extensions.html) に書かれているように LuaJIT は Lua 5.1 (と 5.2 の一部の機能）互換ですので Lua 5.1 のドキュメントは重要です。
* LuaJIT の FFI 関連の公式ドキュメント: [FFI Library](https://luajit.org/ext_ffi.html) と左のメニューにある子供のページ。
    * 重要なことがいろいろ書いてあるので頑張って読みましょう。情報の密度が高くて一度に理解できないので、必要に応じて何度も参照します。
* 実例: [openresty/lua-resty-core](https://github.com/openresty/lua-resty-core/) など [OpenResty](https://github.com/openresty) の `lua-resty-*` のプロジェクト群で `require "ffi"` で検索。
    * [openresty/lua-nginx-module: Embed the Power of Lua into NGINX HTTP servers](https://github.com/openresty/lua-nginx-module) には C 言語で書かれた Lua 用のモジュールが含まれていますが [lua_load_resty_core](https://github.com/openresty/lua-nginx-module/tree/3908769d39b40b6973cc2e2002cff8d5b3169b13#lua_load_resty_core) の説明にあるように v0.10.15 から `resty.core` モジュールは [openresty/lua-resty-core: New FFI-based API for lua-nginx-module](https://github.com/openresty/lua-resty-core) に移行しています。他にも [OpenResty](https://github.com/openresty) には LuaJIT FFI で書かれたモジュールが多数あり、私はこれらのコードをお手本にしています。
* [Extensions](https://luajit.org/extensions.html) からリンクされている [Lua Bit Operations Module](https://bitop.luajit.org/) と [BitOp API Functions](https://bitop.luajit.org/api.html)
    * LuaJIT に組み込みの bit モジュールの関数でビット操作を行うことができます。

## C 言語で書かれた共有ライブラリをロードして Lua から呼び出す。

[FFI Tutorial](https://luajit.org/ext_ffi_tutorial.html) の例を見ると標準ライブラリの場合は以下のようなコードになります。

```lua
local ffi = require("ffi")

ffi.cdef[[
int poll(struct pollfd *fds, unsigned long nfds, int timeout);
]]

ffi.C.poll(nil, 0, s*1000)
```

標準ライブラリ以外の場合は Accessing the zlib Compression Library の項に書いてあるように上記とは少し違うコードになります。以下は libxml2 の例です。

`ffi.load` の引数に指定する文字列は使用する共有ライブラリのファイル名から先頭の `lib` と拡張子の `.so` を除いたものになります。下記の例だと `libxml2.so` なので `"xml2"` になるわけです。

`ffi.cdef` には C 言語の宣言の書式で書くのでライブラリ名は関係しません。
一方 Lua から C の共有ライブラリ内の関数を呼び出すときは `ffi.load` の戻り値の table 内のフィールドに設定された関数を呼び出すことになります。

```lua
local ffi = require "ffi"
local xml2 = ffi.load("xml2")

ffi.cdef[[
void xmlInitParser(void);
]]

xml2.xmlInitParser()
```

Lua の文法についての補足ですが `ffi.cdef` の後の `[[` から `]]` までは複数行文字列リテラルです（ [2.1 – Lexical Conventions](http://www.lua.org/manual/5.1/manual.html#2.1) 参照）。
また、Lua では関数呼び出しの際に引数が table 1 つか文字列が 1 つのときは括弧を省略できるというシンタクスシュガーがあります（ [2.5.8 – Function Calls](http://www.lua.org/manual/5.1/manual.html#2.5.8) 参照）。。
ということで、 `ffi.cdef` の箇所は複数行文字列リテラルを引数として関数を呼び出しているというわけです。

## C 言語で書かれたライブラリの関数宣言、型定義、定数を `ffi.cdef` に書く

[ffi.cdef(def)](https://luajit.org/ext_ffi_api.html#ffi_cdef) のドキュメントに書かれていますが、引数の複数行文字列に書かれた C 言語の宣言の内容は Ｃ のプリプロセッサーにはかけられません。

このため `#define` や `#ifdef` などは含まないように適宜書き換えが必要になります。

FFI ライブラリに同梱されている C のパーサーがサポートしている範囲は [C Language Support](https://luajit.org/ext_ffi_semantics.html#clang) に書かれています。

LuaJIT FFI でモジュールを書くときに一番大変なのがこの書き換えです。

[koreader/ffi-cdecl: Automated C declaration extraction for FFI interfaces](https://github.com/koreader/ffi-cdecl) というツールを見かけて一度試してみたのですが、うまく行かず空の `ffi.cdef` が生成されたので諦めて手動で書き換えています。

一方で、これさえ出来れば後は非常に簡単です。

### C 言語で書かれたライブラリのヘッダーを検索する

### 実行時に使いたいライブラリーのヘッダーファイルを参照する

例えば Ubuntu で libxml2 パッケージの共有ライブラリを呼び出す場合は libxml2-dev パッケージをインストールします。実行時には dev パッケージは不要です。

### 関数の呼び出しに必要な宣言を探して追加していく

私の場合はまず関数呼び出しを書いてファイルに保存し luajit で実行して出たエラーに対して修正するというサイクルで進めています。

例えば

```lua
local ffi = require "ffi"
local xml2 = ffi.load("xml2")

ffi.cdef[[
]]

xml2.xmlInitParser()
```

という内容を `test.lua` というファイル名で保存し

```console
luajit test.lua
```

と実行すると

```console
$ luajit test.lua
luajit: test.lua:7: missing declaration for symbol 'xmlInitParser'
stack traceback:
        [C]: in function '__index'
        test.lua:7: in main chunk
        [C]: at 0x561836ac34a0
```

のようにエラーが出ます。

`dpkg -L libxml2-dev` でファイル一覧を確認し、使いたい関数の宣言を探します。
以下は `ag` コマンドで `xmlInitParser` を検索する例です。

```console
ag xmlInitParser /usr/include/libxml2/
```

すると

```
XMLPUBFUN void XMLCALL
                xmlInitParser           (void);
```

という宣言が見つかりますので `#define` されているマクロを消して

```lua
ffi.cdef[[
void xmlInitParser(void);
]]
```

のように書くか、マクロをコメントアウトして

```lua
ffi.cdef[[
/* XMLPUBFUN */ void /* XMLCALL */
                xmlInitParser           (void);
]]
```

のように書きます。

この例だと引数と戻り値は `void` なのでこれで完了です。

再度 luajit で実行すると今度はエラーなしで実行できました。

引数や戻り値に `typedef` された型がある場合は、その宣言も探して `ffi.cdef` に追加していきます。

型定義を検索する場合は

```
ag 'typedef.*型名' /usr/include/
```

などとまずは限定して検索して、もし見つからない場合は `'#define.*型名' も試し、それでもだめなら諦めて単に型名で検索して結果の中から頑張って探します。

例えば以下のような例で `xmlSecPtrListId` を検索するときは `typedef.*xmlSecPtrListId` はヒットしないので単に `xmlSecPtrListId` で探して頑張ることになります。

```c
typedef const struct _xmlSecPtrListKlass xmlSecPtrListKlass,
                                         *xmlSecPtrListId;
```

一方下記の例のように `*Ptr` は最後になるというパターンが決まっていれば `xmlSecPtrListPtr;` で検索するという手もあります。

```c
typedef struct _xmlSecPtrList xmlSecPtrList,
                              *xmlSecPtrListPtr;
```

この辺はライブラリ毎の書き方にも依存するのでヘッダーファイルを見てみて法則性を見つけて試す感じです。

さらに次の関数呼び出しを Lua ファイルに追加して同じ手順を繰り返します。

これによって自分が書きたいプログラムについて最低限必要な宣言だけで済ませることができます。

### `#define` での数値定数の定義は `enum` で書き換える

例えば以下のように書き換えます。

```lua
ffi.cdef[[
// #define XML_DETECT_IDS              2
enum {
  XML_DETECT_IDS        = 2,
};
]]
```

ただこれは私がそうしているというだけで、もっと良い方法があるかもしれません。

### `#ifdef` の定数定義がどうなっているか調べる



#### pkg-config で定数定義されているか見てみる

例えば libxmlsec1 の `xmlSecSize` を以下のように検索して

```
ag '#define.*xmlSecSize' /usr/include/xmlsec1/
```

以下のように定義されているのがわかりました。

```c
#ifdef XMLSEC_NO_SIZE_T
#define xmlSecSize                              unsigned int
#else /* XMLSEC_NO_SIZE_T */
#define xmlSecSize                              size_t
#endif /* XMLSEC_NO_SIZE_T */
```

libxmlsec1-dev パッケージに pkgconfig のファイルが含まれるか調べます。

```console
$ dpkg -L libxmlsec1-dev | grep pkgconfig/
/usr/lib/x86_64-linux-gnu/pkgconfig/xmlsec1-gcrypt.pc
/usr/lib/x86_64-linux-gnu/pkgconfig/xmlsec1-gnutls.pc
/usr/lib/x86_64-linux-gnu/pkgconfig/xmlsec1-nss.pc
/usr/lib/x86_64-linux-gnu/pkgconfig/xmlsec1-openssl.pc
/usr/lib/x86_64-linux-gnu/pkgconfig/xmlsec1.pc
```

以下のようにして cflags を確認します。 `--libs` 引数には上記の `*.pc` ファイルのベース名を指定します。

```console
$ pkg-config --cflags --libs xmlsec1
-D__XMLSEC_FUNCTION__=__func__ -DXMLSEC_NO_SIZE_T -DXMLSEC_NO_GOST=1 -DXMLSEC_NO_GOST2012=1 -DXMLSEC_NO_CRYPTO_DYNAMIC_LOADING=1 -DXMLSEC_CRYPTO_OPENSSL=1 -I/usr/include/xmlsec1 -I/usr/include/libxml2 -lxmlsec1-openssl -lxmlsec1 -lssl -lcrypto -lxslt -lxml2
```

`-DXMLSEC_NO_SIZE_T` が含まれていますので `XMLSEC_NO_SIZE_T` は定義されています。

ということで `ffi.cdef` には以下のように書きます。ビルド時の設定によって変わることが後から確認できるように元の定義をコメントアウトして残すようにしてます。

```lua
ffi.cdef[[
// #ifdef XMLSEC_NO_SIZE_T
// #define xmlSecSize                              unsigned int
// #else /* XMLSEC_NO_SIZE_T */
// #define xmlSecSize                              size_t
// #endif /* XMLSEC_NO_SIZE_T */
typedef unsigned int                            xmlSecSize;
]]
```

pkgconfig の `*.pc` ファイル名の命名規則はパッケージによって違うので都度確認が必要です。例えば libxml2-dev の場合は以下のようになっていました。

```
$ dpkg -L libxml2-dev | grep pkgconfig/
/usr/lib/x86_64-linux-gnu/pkgconfig/libxml-2.0.pc
```

#### deb パッケージをビルドして生成された config.status や config.h を確認してみる

例えば libxmlsec1 の `struct _xmlSecKeyInfoCtx` は以下のような定義になっていました。

```c
struct _xmlSecKeyInfoCtx {
// …略…
#ifndef XMLSEC_NO_XMLENC
    /* EncryptedKey */
    xmlSecEncCtxPtr                     encCtx;
    int                                 maxEncryptedKeyLevel;
#endif /* XMLSEC_NO_XMLENC */
// …略…
```

上記の `pkgconfig --cflags` の出力には `XMLSEC_NO_XMLENC` を定義する設定は無いので未定義かもしれませんが、別の箇所で定義されているかもしれません。

確認するために deb のソースパッケージを取得してビルドし、生成された config.status や config.h を確認してみました。

作業ディレクトリを作成してそこに `cd` します。その後以下のコマンドで libxmlsec1 の deb ソースパッケージを取得します。

```console
apt source libxmlsec1
```

以下のようにファイルが取得され、 xmlsec1-1.2.25/ ディレクトリに upstream の tarball xmlsec1_1.2.25.orig.tar.gz と debian/ のファイル群の xmlsec1_1.2.25-1build1.debian.tar.xz が展開されます。

```console
~/libxmlsec1-work$ ls -F
xmlsec1-1.2.25/                       xmlsec1_1.2.25-1build1.dsc
xmlsec1_1.2.25-1build1.debian.tar.xz  xmlsec1_1.2.25.orig.tar.gz
```

xmlsec1-1.2.25 ディレクトリに移動し

```console
~/libxmlsec1-work$ cd xmlsec1-1.2.25/
~/libxmlsec1-work/xmlsec1-1.2.25$
```

以下のコマンドで libxmlsec1 パッケージのビルドに必要なパッケージをまとめてインストールするための deb パッケージを生成してインストールします。

```console
$ sudo mk-build-deps -i
…(略)…
dpkg-deb: building package 'xmlsec1-build-deps' in '../xmlsec1-build-deps_1.2.25-1build1_all.deb'.
…(略)…
Setting up xmlsec1-build-deps (1.2.25-1build1) ...
```

deb パッケージをビルドするときにソースディレクトリに余分なファイルがあるとエラーになるので親ディレクトリに移動しておきます

```console
$ mv xmlsec1-build-deps_1.2.25-1build1_all.deb ..
```

以下のコマンドで deb パッケージをビルドします。 `man dpkg-buildpackage` を見ても configure のみ行うオプションが見当たらないのでバイナリパッケージをビルドするオプション `-b` を指定します。またパッケージを配布するわけはなく署名は不要なので `--no-sign` も指定しています。

```console
$ dpkg-buildpackage -b --no-sign
```

ビルドが終わったら（あるいは出力を見て configure が終わったところで Ctrl-C で止めてもいいかもしれません）、先程インストールした依存パッケージの deb をアンインストールしておきます。

```console
sudo dpkg -e ../xmlsec1-build-deps_1.2.25-1build1_all.deb
```

以下のコマンドで configure で生成された config.h と config.status のパスを調べます。

```console
$ find . -name config.h -or -name config.status
./config.h
./config.status
```

この中で `XMLSEC_NO_XMLENC` を検索してみると定義していないことが確認できました。

```console
$ grep XMLSEC_NO_XMLENC $(find . -name config.h -or -name config.status)
./config.status:S["XMLSEC_NO_XMLENC"]="0"
./config.status:S["XMLSEC_NO_XMLENC_FALSE"]=""
./config.status:S["XMLSEC_NO_XMLENC_TRUE"]="#"
```

ということで `ffi.cdef` では以下のように書きます。

```lua
ffi.cdef[[
struct _xmlSecKeyInfoCtx {
// …略…
// #ifndef XMLSEC_NO_XMLENC
    /* EncryptedKey */
    xmlSecEncCtxPtr                     encCtx;
    int                                 maxEncryptedKeyLevel;
// #endif /* XMLSEC_NO_XMLENC */
// …略…
};
]]
```

この例では config.h と config.status を見ましたが、ソフトウェアによっては違うファイルにマクロ定義が生成される場合もありますので、適宜調べてください。

### C 言語で書かれたライブラリの構造体と `ffi.cdef` に書いた構造体のサイズやフィールドのオフセットが一致するか確認

上記の `pkg-config --cflags` で調べた例

```lua
ffi.cdef[[
// #ifdef XMLSEC_NO_SIZE_T
// #define xmlSecSize                              unsigned int
// #else /* XMLSEC_NO_SIZE_T */
// #define xmlSecSize                              size_t
// #endif /* XMLSEC_NO_SIZE_T */
typedef unsigned int                            xmlSecSize;
]]]
```

はさも最初からそうやって調べたように書いてますが、実際は分かってなくて逆の分岐の宣言を以下のように書いて開発していました。

```lua
ffi.cdef[[
typedef size_t xmlSecSize;
]]]
```

すると関数の実行自体は出来るのですが、挙動がおかしいことに気づきました。
具体的には実行結果として 0 か 1 が入るはずの構造体のフィールドを出力してい見ると全然違う値が表示されるという現象でした。

具体的には下記の `struct _xmlSecDSigCtx` の `status` フィールドです。

```c
struct _xmlSecDSigCtx {
    /* these data user can set before performing the operation */
    void*                       userData;
    unsigned int                flags;
    unsigned int                flags2;
    xmlSecKeyInfoCtx            keyInfoReadCtx;
    xmlSecKeyInfoCtx            keyInfoWriteCtx;
    xmlSecTransformCtx          transformCtx;
    xmlSecTransformUriType      enabledReferenceUris;
    xmlSecPtrListPtr            enabledReferenceTransforms;
    xmlSecTransformCtxPreExecuteCallback referencePreExecuteCallback;
    xmlSecTransformId           defSignMethodId;
    xmlSecTransformId           defC14NMethodId;
    xmlSecTransformId           defDigestMethodId;

    /* these data are returned */
    xmlSecKeyPtr                signKey;
    xmlSecTransformOperation    operation;
    xmlSecBufferPtr             result;
    xmlSecDSigStatus            status;
//…(略)…
};
```

そこで Lua は [ffi.\* API Functions](https://luajit.org/ext_ffi_api.html#ffi_cdef) の `ffi.sizeof` と `ffi.offsetof` を使い、 C では `sizeof` と `offsetof` を使って構造体のサイズとフィールドのオフセットを表示して比較してみました。

```lua
print(string.format("sizeof(struct _xmlSecDSigCtx)=%d", ffi.sizeof("struct _xmlSecDSigCtx"))
print(string.format("offsetof(struct _xmlSecDSigCtx, stattus)=%d", ffi.offsetof("struct _xmlSecDSigCtx", "status"))
```


```c
printf("sizeof(struct _xmlSecDSigCtx)=%d\n", sizeof(struct _xmlSecDSigCtx);
printf("offsetof(struct _xmlSecDSigCtx, stattus)=%d", offsetof(struct _xmlSecDSigCtx, status);
```

これでずれていることが分かったら先頭と `status` の真ん中あたりのフィールドのオフセットを比較してという感じで繰り返し比較して原因の箇所を特定します。

その後上述の `pkg-config --cflags` の方法を思いついて確定したという感じです。

## Lua から C 言語で書かれたライブラリの関数を呼び出す
### C 言語で書かれたライブラリと Lua のコードで引数や戻り値の受け渡す際の型変換

[C Type Conversion Rules](https://luajit.org/ext_ffi_semantics.html#clang) に C からの戻り値から Lua の変数に値を受け取る際の変換と、 Lua の値を C の関数の引数へ渡す際の変換の表がありますのでこれに沿って変換します。

多くの型はそのまま渡せます。気を付けるのは戻り値の受け取りで C の `char *` の文字列は `ffi.tostring` 関数で Lua の文字列に変換する必要がある点です。
C での整数は値が 52bit の範囲ならそのまま Lua の変数で受け取れます。
[2.2 – Values and Types](http://www.lua.org/manual/5.1/manual.html#2.2) に書かれているように Lua の number 型は倍精度浮動小数点数ですので、 52bit の範囲を超える整数値は `tonumber` 関数で変換する必要があります。が精度が落ちて違う値になる場合があります。

LuaJIT で 64bit 整数を扱いたいというイシューが [64-bit Integer Hack · Issue #182 · LuaJIT/LuaJIT](https://github.com/LuaJIT/LuaJIT/issues/182) にあるのですが却下されています。
Lua 側では扱わず `ffi.new` でメモリ領域を割り当てて C 側で扱う必要があるそうです（私自身は試してないです）。

あと引数に渡すほうは `const char *` の場合は Lua の文字列をそのまま渡せますが、 `const` なしの `char *` で C 側で変更するときは https://stackoverflow.com/a/33485288/1391518 にあるように `ffi.new` でメモリ割り当てしてコピーして渡す必要があります。

```lua
local text = "text"
local c_str = ffi.new("char[?]", #text)
ffi.copy(c_str, text)
lib.drawText(fb, px, py, c_str, color)
```

### C 言語の int の戻り値を Lua の if 文で boolean として扱う場合の注意

```c
int xmlStrEqual              (const xmlChar *str1,
                              const xmlChar *str2);
```

という関数があって

```c
if xmlStrEqual(str1, str2) {
   /* …(略)… */
}
```

のように利用しているコードを

```lua
if xmlsec1.xmlStrEqual(str1, str2) then
   --  …(略)…
end
```

のように書き換えて常に `if` 文の中身が実行されてハマりました。

理由は Lua の `if`, `while`, `repeat ... until` の条件式では `false` と `nil` が `false` 扱いになり、それ以外の値は全て `true` 扱いになるからです（  [2.4.4 – Control Structures](http://www.lua.org/manual/5.1/manual.html#2.4.4) 参照）。

上記の `xmlStrEqual` 関数は一致の場合は 1 、不一致の場合は 0 を返すので、正しくは

```lua
if xmlsec1.xmlStrEqual(str1, str2) == 1 then
   --  …(略)…
end
```

か

```lua
if xmlsec1.xmlStrEqual(str1, str2) ~= 0 then
   --  …(略)…
end
```

と書く必要があります。
Lua の `~=` は C でいう `!=` です（ [2.5.2 – Relational Operators](http://www.lua.org/manual/5.1/manual.html#2.5.2) 参照）。

`同様に C の `!xmlStrEqual(str1, str2)` は Lua では `not xmlsec1.xmlStrEqual(str1, str2)` ではなく `xmlsec1.xmlStrEqual(str1, str2) ~= 1` または `xmlsec1.xmlStrEqual(str1, str2) == 0` と書く必要があります。
定数を定義するかラップした関数を定義したほうが良いかもしれません。

### エラーの返し方とエラー処理

Lua にはエラー関連の関数として [error](http://www.lua.org/manual/5.1/manual.html#pdf-error), [pcall](http://www.lua.org/manual/5.1/manual.html#pdf-pcall), [xpcall](http://www.lua.org/manual/5.1/manual.html#pdf-xpcall) が用意されています。
大雑把に言うと Go 言語の panic と recover に近いです。

ですが、これを使わない道もあります。
Lua の関数は複数の値を返せるので 2 つめ以降に err の値を返すという方式です。

例えば [lua-nginx-module](https://github.com/openresty/lua-nginx-module) の 
[ngx.req.get_uri_args](https://github.com/openresty/lua-nginx-module#ngxreqget_uri_args) のシグネチャは `args, err = ngx.req.get_uri_args(max_args?)` となっています。

`err` はエラーなしの時は `nil` を返し、 エラーありの場合はエラーメッセージの文字列を返すのが定番の方法です。

```lua
local args, err = ngx.req.get_uri_args()
if err ~= nil then
   -- エラー処理
end
```

Go に近い感覚で書けますし、実行時の処理としても軽いと思いますので LuaJIT FFI で関数を書くときはこちらの方式が良いです。


### エラーで抜ける際の後処理をすっきり書く方法

関数内で複数の変数を初期化して最後で後処理するような場合、 C だと後処理の箇所にラベルを付けてエラーのときは goto で飛ぶのが良くあります。また Go では defer を使って後処理する方法があります。

Lua には goto も defer も無いのですが関数クロージャーは使えますので、無名関数の即時呼び出しを使って以下のようにすれば、すっきり書けます。

以下の例では `initA` は失敗の場合は戻り値が `nil` になり、 `initB` は第 2 引数で err を返すという想定です。


```lua
function foo()
    local a, b
    local err = (function()
        a = initA()
        if a == nil then
            return "failed to initialize A"
        end

        b, err = initB()
        if err ~= nil then
            return string.format("failed to initialize B: %s", err)
        end

        -- a と b を使った処理

        return nil
    end)()
    if b ~= nil then
        destroyB(b)
    end
    if a ~= nil then
        destroyA(a)
    end
    return err
end
```

インデントが一段深くなるのが唯一の欠点ですが、それ以外は満足できると思います。

## おわりに

[openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module#ngxreqget_uri_args) と LuaJIT FFI の組み合わせは nginx をフロントに立てているときに、ちょっとした処理を高速に処理して低レイテンシーを実現したいときには魅力的な選択肢だと考えています。

リバースプロキシーで他のプロセスと通信する方式に比べて、 nginx のワーカープロセス内で処理を実行できるので通信が不要という利点は大きいと私は思います。

一方で LuaJIT の懸念材料としては LuaJIT の元々の作者である Mike Pall さんが別の仕事で忙しくて LuaJIT のメインの開発からは外れているという点があります （[LuaJIT's main developer is retiring and is looking for new developers : programming](https://www.reddit.com/r/programming/comments/3gin5e/luajits_main_developer_is_retiring_and_is_looking/), [Clone Mike Pall · Issue #45 · LuaJIT/LuaJIT](https://github.com/LuaJIT/LuaJIT/issues/45) 参照）。
[openresty/luajit2: OpenResty's Branch of LuaJIT 2](https://github.com/openresty/luajit2) などいくつかフォークもありますが、今後どうなっていくかはなんとも言えません。

ということで 2020-03-05 に出た [Istio / Redefining extensibility in proxies - introducing WebAssembly to Envoy and Istio](https://istio.io/blog/2020/wasm-announce/) という記事が気になっていて今後調査していきたいと思っています。
