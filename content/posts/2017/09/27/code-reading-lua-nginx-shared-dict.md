+++
title="lua-nginx-moduleのshared dictのコードリーディング"
date = "2017-09-27T08:57:00+09:00"
tags = ["nginx"]
categories = ["blog"]
+++


## はじめに

[openresty/lua-nginx-module: Embed the Power of Lua into NGINX HTTP servers](https://github.com/openresty/lua-nginx-module)
の
[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict)
を使う際
[lua_shared_dict](https://github.com/openresty/lua-nginx-module#lua_shared_dict)
ディレクティブで

```text
http {
    lua_shared_dict dogs 10m;
    ...
}
```

のように dict のサイズを指定しますが、容量が足りているかを確認するため実際の使用量をモニタリングしたいと思いました。

systemtap を使った方法
[openresty-systemtap-toolkit/ngx-shm at 97fbeb0bef1aa85e758210d58063376de8eaed31 · openresty/openresty-systemtap-toolkit](https://github.com/openresty/openresty-systemtap-toolkit/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/ngx-shm)
が提供されているのは気付いたのですが、FreeBSDなどLinux以外では使えません。

ngx.shared.DICT のソースを見ると nginx の slab allocator を使ってメモリ割り当てを行っていました。
そこで slab allocator の統計情報から使用量を計算するメソッドを ngx.shared.DICT に追加するプルリクエスト
[Add FFI methods for taking stats to ngx.shared.DICT by hnakamur · Pull Request #1149 · openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module/pull/1149)
を書いてみました。これはまだマージされていません。

テストケースを用意して実際に試してみながら、lua-nginx-moduleのshared dict関連とnginxのslab allocatorのコードを読んでみたのでメモです。

対象バージョンは lua-nginx-module は現時点での最新コミット、nginx は 1.13.5 にしました。

(注) この記事は書きかけです。長くなって疲れてきたので途中ですが一旦上げます。

## lua_shared_dict ディレクティブ関連のコード

`lua_shared_dict` ディレクティブを処理する関数は `ngx_http_lua_shared_dict` です。

[lua-nginx-module/src/ngx_http_lua_module.c#L74-L95](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_module.c#L74-L95)

```c
static ngx_command_t ngx_http_lua_cmds[] = {

    { ngx_string("lua_max_running_timers"),
      NGX_HTTP_MAIN_CONF|NGX_CONF_TAKE1,
      ngx_conf_set_num_slot,
      NGX_HTTP_MAIN_CONF_OFFSET,
      offsetof(ngx_http_lua_main_conf_t, max_running_timers),
      NULL },

    { ngx_string("lua_max_pending_timers"),
      NGX_HTTP_MAIN_CONF|NGX_CONF_TAKE1,
      ngx_conf_set_num_slot,
      NGX_HTTP_MAIN_CONF_OFFSET,
      offsetof(ngx_http_lua_main_conf_t, max_pending_timers),
      NULL },

    { ngx_string("lua_shared_dict"),
      NGX_HTTP_MAIN_CONF|NGX_CONF_TAKE2,
      ngx_http_lua_shared_dict,
      0,
      0,
      NULL },
```

[lua-nginx-module/src/ngx_http_lua_directive.c#L73-L155](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_directive.c#L73-L155)

下記の `ngx_http_lua_shared_dict` 関数の110行目で `ngx_parse_size` 関数でshared dictのサイズをパーズして 127行目で `ngx_http_lua_shared_memory_add` 関数で `zone` の情報を作成しています。

145～150行目で `zone` の情報をlua-nginx-moduleの shared dict管理情報の配列 `lmcf->shdict_zones` に追加しています。

また142行目で `zone->init` に `ngx_http_lua_shdict_init_zone` 関数を設定しています。

`zone` に対応する共有メモリは後続の nginx の初期化処理で確保します。

```c {linenos=table,linenostart=73}
char *
ngx_http_lua_shared_dict(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
{
    ngx_http_lua_main_conf_t   *lmcf = conf;

    ngx_str_t                  *value, name;
    ngx_shm_zone_t             *zone;
    ngx_shm_zone_t            **zp;
    ngx_http_lua_shdict_ctx_t  *ctx;
    ssize_t                     size;

    if (lmcf->shdict_zones == NULL) {
        lmcf->shdict_zones = ngx_palloc(cf->pool, sizeof(ngx_array_t));
        if (lmcf->shdict_zones == NULL) {
            return NGX_CONF_ERROR;
        }

        if (ngx_array_init(lmcf->shdict_zones, cf->pool, 2,
                           sizeof(ngx_shm_zone_t *))
            != NGX_OK)
        {
            return NGX_CONF_ERROR;
        }
    }

    value = cf->args->elts;

    ctx = NULL;

    if (value[1].len == 0) {
        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "invalid lua shared dict name \"%V\"", &value[1]);
        return NGX_CONF_ERROR;
    }

    name = value[1];

    size = ngx_parse_size(&value[2]);

    if (size <= 8191) {
        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "invalid lua shared dict size \"%V\"", &value[2]);
        return NGX_CONF_ERROR;
    }

    ctx = ngx_pcalloc(cf->pool, sizeof(ngx_http_lua_shdict_ctx_t));
    if (ctx == NULL) {
        return NGX_CONF_ERROR;
    }

    ctx->name = name;
    ctx->main_conf = lmcf;
    ctx->log = &cf->cycle->new_log;

    zone = ngx_http_lua_shared_memory_add(cf, &name, (size_t) size,
                                          &ngx_http_lua_module);
    if (zone == NULL) {
        return NGX_CONF_ERROR;
    }

    if (zone->data) {
        ctx = zone->data;

        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "lua_shared_dict \"%V\" is already defined as "
                           "\"%V\"", &name, &ctx->name);
        return NGX_CONF_ERROR;
    }

    zone->init = ngx_http_lua_shdict_init_zone;
    zone->data = ctx;

    zp = ngx_array_push(lmcf->shdict_zones);
    if (zp == NULL) {
        return NGX_CONF_ERROR;
    }

    *zp = zone;

    lmcf->requires_shm = 1;

    return NGX_CONF_OK;
}
```

上記の145行目の `lmcf` に対応する `ngx_http_lua_main_conf_s` 構造体の定義は以下のようになっています。

[lua-nginx-module/src/ngx_http_lua_common.h#L163-L234](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_common.h#L163-L234)

```c {linenos=table,linenostart=163}
struct ngx_http_lua_main_conf_s {
    lua_State           *lua;

    ngx_str_t            lua_path;
    ngx_str_t            lua_cpath;

    ngx_cycle_t         *cycle;
    ngx_pool_t          *pool;

    ngx_int_t            max_pending_timers;
    ngx_int_t            pending_timers;

    ngx_int_t            max_running_timers;
    ngx_int_t            running_timers;

    ngx_connection_t    *watcher;  /* for watching the process exit event */

#if (NGX_PCRE)
    ngx_int_t            regex_cache_entries;
    ngx_int_t            regex_cache_max_entries;
    ngx_int_t            regex_match_limit;

#if (LUA_HAVE_PCRE_JIT)
    pcre_jit_stack      *jit_stack;
#endif

#endif

    ngx_array_t         *shm_zones;  /* of ngx_shm_zone_t* */

    ngx_array_t         *shdict_zones; /* shm zones of "shdict" */

    ngx_array_t         *preload_hooks; /* of ngx_http_lua_preload_hook_t */

    ngx_flag_t           postponed_to_rewrite_phase_end;
    ngx_flag_t           postponed_to_access_phase_end;

    ngx_http_lua_main_conf_handler_pt    init_handler;
    ngx_str_t                            init_src;

    ngx_http_lua_main_conf_handler_pt    init_worker_handler;
    ngx_str_t                            init_worker_src;

    ngx_http_lua_balancer_peer_data_t      *balancer_peer_data;
                    /* balancer_by_lua does not support yielding and
                     * there cannot be any conflicts among concurrent requests,
                     * thus it is safe to store the peer data in the main conf.
                     */

    ngx_uint_t                      shm_zones_inited;

    ngx_http_lua_sema_mm_t         *sema_mm;

    ngx_uint_t           malloc_trim_cycle;  /* a cycle is defined as the number
                                                of reqeusts */
    ngx_uint_t           malloc_trim_req_count;

#if nginx_version >= 1011011
    /* the following 2 fields are only used by ngx.req.raw_headers() for now */
    ngx_buf_t          **busy_buf_ptrs;
    ngx_int_t            busy_buf_ptr_count;
#endif

    unsigned             requires_header_filter:1;
    unsigned             requires_body_filter:1;
    unsigned             requires_capture_filter:1;
    unsigned             requires_rewrite:1;
    unsigned             requires_access:1;
    unsigned             requires_log:1;
    unsigned             requires_shm:1;
    unsigned             requires_capture_log:1;
};
```

次に `ngx_http_lua_shared_memory_add` 関数の実装を見ていきます。

[lua-nginx-module/src/ngx_http_lua_api.c#L86-L152](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_api.c#L86-L152)

115行目の `ngx_shared_memory_add` 関数で `zone` を作り、127行目で `ctx` 用のメモリを割りあてて 136行目で `ctx->zone` に `zone` の内容をコピーして 151行目で関数の戻り値として返しています。

138～143行目で lua-nginx-module で共有メモリのゾーンを管理する配列 `lmcf->shm_zones` に要素を追加しています。

また、146行目で `zone->init` に `ngx_http_lua_shared_memory_init` 関数を設定しています。

```c {linenos=table,linenostart=86}
ngx_shm_zone_t *
ngx_http_lua_shared_memory_add(ngx_conf_t *cf, ngx_str_t *name, size_t size,
    void *tag)
{
    ngx_http_lua_main_conf_t     *lmcf;
    ngx_shm_zone_t              **zp;
    ngx_shm_zone_t               *zone;
    ngx_http_lua_shm_zone_ctx_t  *ctx;
    ngx_int_t                     n;

    lmcf = ngx_http_conf_get_module_main_conf(cf, ngx_http_lua_module);
    if (lmcf == NULL) {
        return NULL;
    }

    if (lmcf->shm_zones == NULL) {
        lmcf->shm_zones = ngx_palloc(cf->pool, sizeof(ngx_array_t));
        if (lmcf->shm_zones == NULL) {
            return NULL;
        }

        if (ngx_array_init(lmcf->shm_zones, cf->pool, 2,
                           sizeof(ngx_shm_zone_t *))
            != NGX_OK)
        {
            return NULL;
        }
    }

    zone = ngx_shared_memory_add(cf, name, (size_t) size, tag);
    if (zone == NULL) {
        return NULL;
    }

    if (zone->data) {
        ctx = (ngx_http_lua_shm_zone_ctx_t *) zone->data;
        return &ctx->zone;
    }

    n = sizeof(ngx_http_lua_shm_zone_ctx_t);

    ctx = ngx_pcalloc(cf->pool, n);
    if (ctx == NULL) {
        return NULL;
    }

    ctx->lmcf = lmcf;
    ctx->log = &cf->cycle->new_log;
    ctx->cycle = cf->cycle;

    ngx_memcpy(&ctx->zone, zone, sizeof(ngx_shm_zone_t));

    zp = ngx_array_push(lmcf->shm_zones);
    if (zp == NULL) {
        return NULL;
    }

    *zp = zone;

    /* set zone init */
    zone->init = ngx_http_lua_shared_memory_init;
    zone->data = ctx;

    lmcf->requires_shm = 1;

    return &ctx->zone;
}
```

[nginx/src/core/ngx_cycle.c#L1204-L1274](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_cycle.c#L1204-L1274)

下記の `ngx_shared_memory_add` 関数の1264行目で `zone->data` に `NULL` を設定していますので、上記の関数 `ngx_http_lua_shared_memory_add` では 120行目の `if` の条件は `false` になり、125行目以降が実行されることになります。

`ngx_shared_memory_add` の1258～1271でnginxで共有メモリを管理しているリスト `cf->cycle->shared_memory` に共有メモリの管理情報を追加しています。

実際に共有メモリを割り当てるのは後述の `ngx_shm_alloc` 関数です。

```c {linenos=table,linenostart=1204}
ngx_shm_zone_t *
ngx_shared_memory_add(ngx_conf_t *cf, ngx_str_t *name, size_t size, void *tag)
{
    ngx_uint_t        i;
    ngx_shm_zone_t   *shm_zone;
    ngx_list_part_t  *part;

    part = &cf->cycle->shared_memory.part;
    shm_zone = part->elts;

    for (i = 0; /* void */ ; i++) {

        if (i >= part->nelts) {
            if (part->next == NULL) {
                break;
            }
            part = part->next;
            shm_zone = part->elts;
            i = 0;
        }

        if (name->len != shm_zone[i].shm.name.len) {
            continue;
        }

        if (ngx_strncmp(name->data, shm_zone[i].shm.name.data, name->len)
            != 0)
        {
            continue;
        }

        if (tag != shm_zone[i].tag) {
            ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                            "the shared memory zone \"%V\" is "
                            "already declared for a different use",
                            &shm_zone[i].shm.name);
            return NULL;
        }

        if (shm_zone[i].shm.size == 0) {
            shm_zone[i].shm.size = size;
        }

        if (size && size != shm_zone[i].shm.size) {
            ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                            "the size %uz of shared memory zone \"%V\" "
                            "conflicts with already declared size %uz",
                            size, &shm_zone[i].shm.name, shm_zone[i].shm.size);
            return NULL;
        }

        return &shm_zone[i];
    }

    shm_zone = ngx_list_push(&cf->cycle->shared_memory);

    if (shm_zone == NULL) {
        return NULL;
    }

    shm_zone->data = NULL;
    shm_zone->shm.log = cf->cycle->log;
    shm_zone->shm.size = size;
    shm_zone->shm.name = *name;
    shm_zone->shm.exists = 0;
    shm_zone->init = NULL;
    shm_zone->tag = tag;
    shm_zone->noreuse = 0;

    return shm_zone;
}
```

`ngx_http_lua_shared_memory_init` 関数の実装です。

[lua-nginx-module/src/ngx_http_lua_api.c#L155-L214](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_api.c#L155-L214)

```c {linenos=table,linenostart=155}
static ngx_int_t
ngx_http_lua_shared_memory_init(ngx_shm_zone_t *shm_zone, void *data)
{
    ngx_http_lua_shm_zone_ctx_t *octx = data;
    ngx_shm_zone_t              *ozone;
    void                        *odata;

    ngx_int_t                    rc;
    volatile ngx_cycle_t        *saved_cycle;
    ngx_http_lua_main_conf_t    *lmcf;
    ngx_http_lua_shm_zone_ctx_t *ctx;
    ngx_shm_zone_t              *zone;

    ctx = (ngx_http_lua_shm_zone_ctx_t *) shm_zone->data;
    zone = &ctx->zone;

    odata = NULL;
    if (octx) {
        ozone = &octx->zone;
        odata = ozone->data;
    }

    zone->shm = shm_zone->shm;
#if defined(nginx_version) && nginx_version >= 1009000
    zone->noreuse = shm_zone->noreuse;
#endif

    if (zone->init(zone, odata) != NGX_OK) {
        return NGX_ERROR;
    }

    dd("get lmcf");

    lmcf = ctx->lmcf;
    if (lmcf == NULL) {
        return NGX_ERROR;
    }

    dd("lmcf->lua: %p", lmcf->lua);

    lmcf->shm_zones_inited++;

    if (lmcf->shm_zones_inited == lmcf->shm_zones->nelts
        && lmcf->init_handler)
    {
        saved_cycle = ngx_cycle;
        ngx_cycle = ctx->cycle;

        rc = lmcf->init_handler(ctx->log, lmcf, lmcf->lua);

        ngx_cycle = saved_cycle;

        if (rc != NGX_OK) {
            /* an error happened */
            return NGX_ERROR;
        }
    }

    return NGX_OK;
}
```

`ngx_shm_zone_t` 構造体の定義です。

[nginx/src/core/ngx_cycle.h#L25-L35](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_cycle.h#L25-L35)

```c {linenos=table,linenostart=25}
typedef struct ngx_shm_zone_s  ngx_shm_zone_t;

typedef ngx_int_t (*ngx_shm_zone_init_pt) (ngx_shm_zone_t *zone, void *data);

struct ngx_shm_zone_s {
    void                     *data;
    ngx_shm_t                 shm;
    ngx_shm_zone_init_pt      init;
    void                     *tag;
    ngx_uint_t                noreuse;  /* unsigned  noreuse:1; */
};
```

`ngx_shm_t` 構造体の定義です。

[nginx/os/unix/ngx_shmem.h#L16-L26](https://github.com/nginx/nginx/blob/release-1.13.5/src/os/unix/ngx_shmem.h#L16-L26)

```c {linenos=table,linenostart=16}
typedef struct {
    u_char      *addr;
    size_t       size;
    ngx_str_t    name;
    ngx_log_t   *log;
    ngx_uint_t   exists;   /* unsigned  exists:1;  */
} ngx_shm_t;

ngx_int_t ngx_shm_alloc(ngx_shm_t *shm);
void ngx_shm_free(ngx_shm_t *shm);
```

`ngx_http_lua_shm_zone_ctx_t` 構造体などの定義です。

[lua-nginx-module/src/ngx_http_lua_shdict.h#L14-L55](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_shdict.h#L14-L55)

```c {linenos=table,linenostart=14}
typedef struct {
    u_char                       color;
    uint8_t                      value_type;
    u_short                      key_len;
    uint32_t                     value_len;
    uint64_t                     expires;
    ngx_queue_t                  queue;
    uint32_t                     user_flags;
    u_char                       data[1];
} ngx_http_lua_shdict_node_t;

typedef struct {
    ngx_queue_t                  queue;
    uint32_t                     value_len;
    uint8_t                      value_type;
    u_char                       data[1];
} ngx_http_lua_shdict_list_node_t;

typedef struct {
    ngx_rbtree_t                  rbtree;
    ngx_rbtree_node_t             sentinel;
    ngx_queue_t                   lru_queue;
} ngx_http_lua_shdict_shctx_t;

typedef struct {
    ngx_http_lua_shdict_shctx_t  *sh;
    ngx_slab_pool_t              *shpool;
    ngx_str_t                     name;
    ngx_http_lua_main_conf_t     *main_conf;
    ngx_log_t                    *log;
} ngx_http_lua_shdict_ctx_t;

typedef struct {
    ngx_log_t                   *log;
    ngx_http_lua_main_conf_t    *lmcf;
    ngx_cycle_t                 *cycle;
    ngx_shm_zone_t               zone;
} ngx_http_lua_shm_zone_ctx_t;
```

今回注目するのは `ngx_http_lua_shdict_ctx_t` 構造体の `shpool` の `ngx_slab_pool_t` 構造体です。

[nginx/src/core/ngx_slab.h#L16-L69](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.h#L16-L69)

`ngx_slab_pool_t` 構造体の `stats` フィールド `ngx_slab_stat_t` 構造体にメモリ割り当ての回数 `used` とメモリ割り当て合計バイト数 `total` があり、 `total` からメモリ使用量を計算できます。 詳細は後ほど見ていきます。

```c {linenos=table,linenostart=16}
typedef struct ngx_slab_page_s  ngx_slab_page_t;

struct ngx_slab_page_s {
    uintptr_t         slab;
    ngx_slab_page_t  *next;
    uintptr_t         prev;
};

typedef struct {
    ngx_uint_t        total;
    ngx_uint_t        used;

    ngx_uint_t        reqs;
    ngx_uint_t        fails;
} ngx_slab_stat_t;

typedef struct {
    ngx_shmtx_sh_t    lock;

    size_t            min_size;
    size_t            min_shift;

    ngx_slab_page_t  *pages;
    ngx_slab_page_t  *last;
    ngx_slab_page_t   free;

    ngx_slab_stat_t  *stats;
    ngx_uint_t        pfree;

    u_char           *start;
    u_char           *end;

    ngx_shmtx_t       mutex;

    u_char           *log_ctx;
    u_char            zero;

    unsigned          log_nomem:1;

    void             *data;
    void             *addr;
} ngx_slab_pool_t;

void ngx_slab_sizes_init(void);
void ngx_slab_init(ngx_slab_pool_t *pool);
void *ngx_slab_alloc(ngx_slab_pool_t *pool, size_t size);
void *ngx_slab_alloc_locked(ngx_slab_pool_t *pool, size_t size);
void *ngx_slab_calloc(ngx_slab_pool_t *pool, size_t size);
void *ngx_slab_calloc_locked(ngx_slab_pool_t *pool, size_t size);
void ngx_slab_free(ngx_slab_pool_t *pool, void *p);
void ngx_slab_free_locked(ngx_slab_pool_t *pool, void *p);
```

## ngx_slab_sizes_init 関数のコード

[nginx/src/core/ngx_slab.c#L80-L95](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.c#L80-L95)

```c {linenos=table,linenostart=80}
static ngx_uint_t  ngx_slab_max_size;
static ngx_uint_t  ngx_slab_exact_size;
static ngx_uint_t  ngx_slab_exact_shift;

void
ngx_slab_sizes_init(void)
{
    ngx_uint_t  n;

    ngx_slab_max_size = ngx_pagesize / 2;
    ngx_slab_exact_size = ngx_pagesize / (8 * sizeof(uintptr_t));
    for (n = ngx_slab_exact_size; n >>= 1; ngx_slab_exact_shift++) {
        /* void */
    }
}
```

`ngx_slab_sizes_init` は `main` 関数の280行目から呼ばれています。

[nginx/nginx.c at release-1.13.5 · nginx/nginx](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/nginx.c#L264-L298)

```c {linenos=table,linenostart=264}
if (ngx_os_init(log) != NGX_OK) {
    return 1;
}

/*
 * ngx_crc32_table_init() requires ngx_cacheline_size set in ngx_os_init()
 */

if (ngx_crc32_table_init() != NGX_OK) {
    return 1;
}

/*
 * ngx_slab_sizes_init() requires ngx_pagesize set in ngx_os_init()
 */

ngx_slab_sizes_init();

if (ngx_add_inherited_sockets(&init_cycle) != NGX_OK) {
    return 1;
}

if (ngx_preinit_modules() != NGX_OK) {
    return 1;
}

cycle = ngx_init_cycle(&init_cycle);
if (cycle == NULL) {
    if (ngx_test_config) {
        ngx_log_stderr(0, "configuration file %s test failed",
                       init_cycle.conf_file.data);
    }

    return 1;
}
```

`ngx_slab_sizes_init: 内で参照している `ngx_pagesize` は以下の場所で定義されています。

[nginx/ngx_alloc.c at release-1.13.5 · nginx/nginx](https://github.com/nginx/nginx/blob/release-1.13.5/src/os/unix/ngx_alloc.c#L12-L14)

```c {linenos=table,linenostart=12}
ngx_uint_t  ngx_pagesize;
ngx_uint_t  ngx_pagesize_shift;
ngx_uint_t  ngx_cacheline_size;
```

`ngx_pagesize` は下記の `ngx_os_init` 関数内の
50行目で
[getpagesize(2) - Linux manual page](http://man7.org/linux/man-pages/man2/getpagesize.2.html)
の値で初期化されています。
また `ngx_pagesize_shift` は53行目で 12 になります。

[nginx/src/os/unix/ngx_posix_init.c#L50-L53](https://github.com/nginx/nginx/blob/release-1.13.5/src/os/unix/ngx_posix_init.c#L50-L53)

```c {linenos=table,linenostart=50}
ngx_pagesize = getpagesize();
ngx_cacheline_size = NGX_CPU_CACHE_LINE;

for (n = ngx_pagesize; n >>= 1; ngx_pagesize_shift++) { /* void */ }
```

[getconf.1p - Linux manual page](http://man7.org/linux/man-pages/man1/getconf.1p.html)
と
[sysconf(3) - Linux manual page](http://man7.org/linux/man-pages/man3/sysconf.3.html)
を見て Ubuntu 16.04 環境で試したところ `getconf PAGESIZE` または `getconf PAGE_SIZE` で取得できました。

```console
$ getconf PAGESIZE
4096
$ getconf PAGE_SIZE
4096
```

詳細は省略しますがデバッグ版のnginxをgdbで動かして
`ngx_slab_max_size`, `ngx_slab_exact_size`, `ngx_slab_exact_shift` の値を確認すると以下のようになっていました。

```console
(gdb) break ngx_slab_sizes_init
Breakpoint 1 at 0x426fdc: file src/core/ngx_slab.c, line 90.
(gdb) run
...
Breakpoint 1, ngx_slab_sizes_init () at src/core/ngx_slab.c:90
90          ngx_slab_max_size = ngx_pagesize / 2;
(gdb) n
91          ngx_slab_exact_size = ngx_pagesize / (8 * sizeof(uintptr_t));
(gdb) n
92          for (n = ngx_slab_exact_size; n >>= 1; ngx_slab_exact_shift++) {
(gdb) n
main (argc=<optimized out>, argv=<optimized out>) at src/core/nginx.c:282
282         if (ngx_add_inherited_sockets(&init_cycle) != NGX_OK) {
(gdb) print ngx_slab_max_size
$1 = 2048
(gdb) print ngx_slab_exact_size
$2 = 64
(gdb) print ngx_slab_exact_shift
$3 = 6
```

## ngx_slab_init 関数のコード

`ngx_slab_init` 関数は上記に引用した `main` 関数の290行目から呼ばれる
`ngx_init_cycle` 関数の482行目を経由して `ngx_init_zone_pool` 関数から呼ばれます。

[nginx/src/core/ngx_cycle.c#L404-L493](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_cycle.c#L404-L493)

```c {linenos=table,linenostart=404}
/* create shared memory */

part = &cycle->shared_memory.part;
shm_zone = part->elts;

for (i = 0; /* void */ ; i++) {

    if (i >= part->nelts) {
        if (part->next == NULL) {
            break;
        }
        part = part->next;
        shm_zone = part->elts;
        i = 0;
    }

    if (shm_zone[i].shm.size == 0) {
        ngx_log_error(NGX_LOG_EMERG, log, 0,
                      "zero size shared memory zone \"%V\"",
                      &shm_zone[i].shm.name);
        goto failed;
    }

    shm_zone[i].shm.log = cycle->log;

    opart = &old_cycle->shared_memory.part;
    oshm_zone = opart->elts;

    for (n = 0; /* void */ ; n++) {

        if (n >= opart->nelts) {
            if (opart->next == NULL) {
                break;
            }
            opart = opart->next;
            oshm_zone = opart->elts;
            n = 0;
        }

        if (shm_zone[i].shm.name.len != oshm_zone[n].shm.name.len) {
            continue;
        }

        if (ngx_strncmp(shm_zone[i].shm.name.data,
                        oshm_zone[n].shm.name.data,
                        shm_zone[i].shm.name.len)
            != 0)
        {
            continue;
        }

        if (shm_zone[i].tag == oshm_zone[n].tag
            && shm_zone[i].shm.size == oshm_zone[n].shm.size
            && !shm_zone[i].noreuse)
        {
            shm_zone[i].shm.addr = oshm_zone[n].shm.addr;
```

    #if (NGX_WIN32)
                    shm_zone[i].shm.handle = oshm_zone[n].shm.handle;
    #endif

                    if (shm_zone[i].init(&shm_zone[i], oshm_zone[n].data)
                        != NGX_OK)
                    {
                        goto failed;
                    }

                    goto shm_zone_found;
                }

                ngx_shm_free(&oshm_zone[n].shm);

                break;
            }

            if (ngx_shm_alloc(&shm_zone[i].shm) != NGX_OK) {
                goto failed;
            }

            if (ngx_init_zone_pool(cycle, &shm_zone[i]) != NGX_OK) {
                goto failed;
            }

            if (shm_zone[i].init(&shm_zone[i], NULL) != NGX_OK) {
                goto failed;
            }

        shm_zone_found:

            continue;
        }

[nginx/src/core/ngx_cycle.c#L868-L930](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_cycle.c#L868-L930)

下記の `ngx_init_zone_pool` 関数の905行目で `ngx_slab_pool_t` の `min_shift` が `3` に初期化されています。

927行目で `ngx_slab_init` 関数を呼び出しています。

```c {linenos=table,linenostart=868}
static ngx_int_t
ngx_init_zone_pool(ngx_cycle_t *cycle, ngx_shm_zone_t *zn)
{
    u_char           *file;
    ngx_slab_pool_t  *sp;

    sp = (ngx_slab_pool_t *) zn->shm.addr;

    if (zn->shm.exists) {

        if (sp == sp->addr) {
            return NGX_OK;
        }

#if (NGX_WIN32)

        /* remap at the required address */

        if (ngx_shm_remap(&zn->shm, sp->addr) != NGX_OK) {
            return NGX_ERROR;
        }

        sp = (ngx_slab_pool_t *) zn->shm.addr;

        if (sp == sp->addr) {
            return NGX_OK;
        }

#endif

        ngx_log_error(NGX_LOG_EMERG, cycle->log, 0,
                      "shared zone \"%V\" has no equal addresses: %p vs %p",
                      &zn->shm.name, sp->addr, sp);
        return NGX_ERROR;
    }

    sp->end = zn->shm.addr + zn->shm.size;
    sp->min_shift = 3;
    sp->addr = zn->shm.addr;

#if (NGX_HAVE_ATOMIC_OPS)

    file = NULL;

#else

    file = ngx_pnalloc(cycle->pool, cycle->lock_file.len + zn->shm.name.len);
    if (file == NULL) {
        return NGX_ERROR;
    }

    (void) ngx_sprintf(file, "%V%V%Z", &cycle->lock_file, &zn->shm.name);

#endif

    if (ngx_shmtx_create(&sp->mutex, &sp->lock, file) != NGX_OK) {
        return NGX_ERROR;
    }

    ngx_slab_init(sp);

    return NGX_OK;
}
```

[nginx/src/core/ngx_slab.c#L98-L165](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.c#L98-L165)

上記で `pool->min_shift` は `3` に設定されていますので、
107行目で `pool->min_size` は `8` になります。

116行目の `n` は `12 - 3` で `9` になります。

118行目以降はまた後で読むので、ここでは一旦スキップします。

```c {linenos=table,linenostart=98}
void
ngx_slab_init(ngx_slab_pool_t *pool)
{
    u_char           *p;
    size_t            size;
    ngx_int_t         m;
    ngx_uint_t        i, n, pages;
    ngx_slab_page_t  *slots, *page;

    pool->min_size = (size_t) 1 << pool->min_shift;

    slots = ngx_slab_slots(pool);

    p = (u_char *) slots;
    size = pool->end - p;

    ngx_slab_junk(p, size);

    n = ngx_pagesize_shift - pool->min_shift;

    for (i = 0; i < n; i++) {
        /* only "next" is used in list head */
        slots[i].slab = 0;
        slots[i].next = &slots[i];
        slots[i].prev = 0;
    }

    p += n * sizeof(ngx_slab_page_t);

    pool->stats = (ngx_slab_stat_t *) p;
    ngx_memzero(pool->stats, n * sizeof(ngx_slab_stat_t));

    p += n * sizeof(ngx_slab_stat_t);

    size -= n * (sizeof(ngx_slab_page_t) + sizeof(ngx_slab_stat_t));

    pages = (ngx_uint_t) (size / (ngx_pagesize + sizeof(ngx_slab_page_t)));

    pool->pages = (ngx_slab_page_t *) p;
    ngx_memzero(pool->pages, pages * sizeof(ngx_slab_page_t));

    page = pool->pages;

    /* only "next" is used in list head */
    pool->free.slab = 0;
    pool->free.next = page;
    pool->free.prev = 0;

    page->slab = pages;
    page->next = &pool->free;
    page->prev = (uintptr_t) &pool->free;

    pool->start = ngx_align_ptr(p + pages * sizeof(ngx_slab_page_t),
                                ngx_pagesize);

    m = pages - (pool->end - pool->start) / ngx_pagesize;
    if (m > 0) {
        pages -= m;
        page->slab = pages;
    }

    pool->last = pool->pages + pages;
    pool->pfree = pages;

    pool->log_nomem = 1;
    pool->log_ctx = &pool->zero;
    pool->zero = '\0';
}
```

上記の 109 行目で呼ばれている `ngx_slab_slots` は以下で定義されたマクロでした。

[nginx/src/core/ngx_slab.c#L44-L45](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.c#L44-L45)

```c {linenos=table,linenostart=44}
#define ngx_slab_slots(pool)                                                  \
    (ngx_slab_page_t *) ((u_char *) (pool) + sizeof(ngx_slab_pool_t))
```

`ngx_slab_pool_t` 構造体のメモリを割り当てる際に、連続して `ngx_slab_page_t` 構造体のメモリも割り当ててそこを参照するということですね。

## ngx.shared.DICTのメソッドのコード

代表として
[ngx.shared.DICT.add](https://github.com/openresty/lua-nginx-module#ngxshareddictadd)
のコードを見ます。

`add` メソッドは `ngx_http_lua_shdict_add` 関数で実装されています。

[lua-nginx-module/src/ngx_http_lua_shdict.c#L347-L348](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_shdict.c#L347-L348)

```c {linenos=table,linenostart=347}
lua_pushcfunction(L, ngx_http_lua_shdict_add);
lua_setfield(L, -2, "add");
```

[lua-nginx-module/src/ngx_http_lua_shdict.c#L869-L873](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_shdict.c#L869-L873)

```c {linenos=table,linenostart=869}
static int
ngx_http_lua_shdict_add(lua_State *L)
{
    return ngx_http_lua_shdict_set_helper(L, NGX_HTTP_LUA_SHDICT_ADD);
}
```

[lua-nginx-module/src/ngx_http_lua_shdict.c#L905-L1246](https://github.com/openresty/lua-nginx-module/blob/97fbeb0bef1aa85e758210d58063376de8eaed31/src/ngx_http_lua_shdict.c#L905-L1246)

```c {linenos=table,linenostart=905}
static int
ngx_http_lua_shdict_set_helper(lua_State *L, int flags)
{
    int                          i, n;
    ngx_str_t                    key;
    uint32_t                     hash;
    ngx_int_t                    rc;
    ngx_http_lua_shdict_ctx_t   *ctx;
    ngx_http_lua_shdict_node_t  *sd;
    ngx_str_t                    value;
    int                          value_type;
    double                       num;
    u_char                       c;
    lua_Number                   exptime = 0;
    u_char                      *p;
    ngx_rbtree_node_t           *node;
    ngx_time_t                  *tp;
    ngx_shm_zone_t              *zone;
    int                          forcible = 0;
                         /* indicates whether to foricibly override other
                          * valid entries */
    int32_t                      user_flags = 0;
    ngx_queue_t                 *queue, *q;

    n = lua_gettop(L);

    if (n != 3 && n != 4 && n != 5) {
        return luaL_error(L, "expecting 3, 4 or 5 arguments, "
                          "but only seen %d", n);
    }

    if (lua_type(L, 1) != LUA_TTABLE) {
        return luaL_error(L, "bad \"zone\" argument");
    }

    zone = ngx_http_lua_shdict_get_zone(L, 1);
    if (zone == NULL) {
        return luaL_error(L, "bad \"zone\" argument");
    }

    ctx = zone->data;

    if (lua_isnil(L, 2)) {
        lua_pushnil(L);
        lua_pushliteral(L, "nil key");
        return 2;
    }

    key.data = (u_char *) luaL_checklstring(L, 2, &key.len);

    if (key.len == 0) {
        lua_pushnil(L);
        lua_pushliteral(L, "empty key");
        return 2;
    }

    if (key.len > 65535) {
        lua_pushnil(L);
        lua_pushliteral(L, "key too long");
        return 2;
    }

    hash = ngx_crc32_short(key.data, key.len);

    value_type = lua_type(L, 3);

    switch (value_type) {

    case SHDICT_TSTRING:
        value.data = (u_char *) lua_tolstring(L, 3, &value.len);
        break;

    case SHDICT_TNUMBER:
        value.len = sizeof(double);
        num = lua_tonumber(L, 3);
        value.data = (u_char *) &num;
        break;

    case SHDICT_TBOOLEAN:
        value.len = sizeof(u_char);
        c = lua_toboolean(L, 3) ? 1 : 0;
        value.data = &c;
        break;

    case LUA_TNIL:
        if (flags & (NGX_HTTP_LUA_SHDICT_ADD|NGX_HTTP_LUA_SHDICT_REPLACE)) {
            lua_pushnil(L);
            lua_pushliteral(L, "attempt to add or replace nil values");
            return 2;
        }

        ngx_str_null(&value);
        break;

    default:
        lua_pushnil(L);
        lua_pushliteral(L, "bad value type");
        return 2;
    }

    if (n >= 4) {
        exptime = luaL_checknumber(L, 4);
        if (exptime < 0) {
            return luaL_error(L, "bad \"exptime\" argument");
        }
    }

    if (n == 5) {
        user_flags = (uint32_t) luaL_checkinteger(L, 5);
    }

    ngx_shmtx_lock(&ctx->shpool->mutex);

#if 1
    ngx_http_lua_shdict_expire(ctx, 1);
#endif

    rc = ngx_http_lua_shdict_lookup(zone, hash, key.data, key.len, &sd);

    dd("shdict lookup returned %d", (int) rc);

    if (flags & NGX_HTTP_LUA_SHDICT_REPLACE) {

        if (rc == NGX_DECLINED || rc == NGX_DONE) {
            ngx_shmtx_unlock(&ctx->shpool->mutex);

            lua_pushboolean(L, 0);
            lua_pushliteral(L, "not found");
            lua_pushboolean(L, forcible);
            return 3;
        }

        /* rc == NGX_OK */

        goto replace;
    }

    if (flags & NGX_HTTP_LUA_SHDICT_ADD) {

        if (rc == NGX_OK) {
            ngx_shmtx_unlock(&ctx->shpool->mutex);

            lua_pushboolean(L, 0);
            lua_pushliteral(L, "exists");
            lua_pushboolean(L, forcible);
            return 3;
        }

        if (rc == NGX_DONE) {
            /* exists but expired */

            dd("go to replace");
            goto replace;
        }

        /* rc == NGX_DECLINED */

        dd("go to insert");
        goto insert;
    }

    if (rc == NGX_OK || rc == NGX_DONE) {

        if (value_type == LUA_TNIL) {
            goto remove;
        }

replace:

        if (value.data
            && value.len == (size_t) sd->value_len
            && sd->value_type != SHDICT_TLIST)
        {

            ngx_log_debug0(NGX_LOG_DEBUG_HTTP, ctx->log, 0,
                           "lua shared dict set: found old entry and value "
                           "size matched, reusing it");

            ngx_queue_remove(&sd->queue);
            ngx_queue_insert_head(&ctx->sh->lru_queue, &sd->queue);

            sd->key_len = (u_short) key.len;

            if (exptime > 0) {
                tp = ngx_timeofday();
                sd->expires = (uint64_t) tp->sec * 1000 + tp->msec
                              + (uint64_t) (exptime * 1000);

            } else {
                sd->expires = 0;
            }

            sd->user_flags = user_flags;

            sd->value_len = (uint32_t) value.len;

            dd("setting value type to %d", value_type);

            sd->value_type = (uint8_t) value_type;

            p = ngx_copy(sd->data, key.data, key.len);
            ngx_memcpy(p, value.data, value.len);

            ngx_shmtx_unlock(&ctx->shpool->mutex);

            lua_pushboolean(L, 1);
            lua_pushnil(L);
            lua_pushboolean(L, forcible);
            return 3;
        }

        ngx_log_debug0(NGX_LOG_DEBUG_HTTP, ctx->log, 0,
                       "lua shared dict set: found old entry but value size "
                       "NOT matched, removing it first");

remove:

        if (sd->value_type == SHDICT_TLIST) {
            queue = ngx_http_lua_shdict_get_list_head(sd, key.len);

            for (q = ngx_queue_head(queue);
                 q != ngx_queue_sentinel(queue);
                 q = ngx_queue_next(q))
            {
                p = (u_char *) ngx_queue_data(q,
                                              ngx_http_lua_shdict_list_node_t,
                                              queue);

                ngx_slab_free_locked(ctx->shpool, p);
            }
        }

        ngx_queue_remove(&sd->queue);

        node = (ngx_rbtree_node_t *)
                   ((u_char *) sd - offsetof(ngx_rbtree_node_t, color));

        ngx_rbtree_delete(&ctx->sh->rbtree, node);

        ngx_slab_free_locked(ctx->shpool, node);

    }

insert:

    /* rc == NGX_DECLINED or value size unmatch */

    if (value.data == NULL) {
        ngx_shmtx_unlock(&ctx->shpool->mutex);

        lua_pushboolean(L, 1);
        lua_pushnil(L);
        lua_pushboolean(L, 0);
        return 3;
    }

    ngx_log_debug0(NGX_LOG_DEBUG_HTTP, ctx->log, 0,
                   "lua shared dict set: creating a new entry");

    n = offsetof(ngx_rbtree_node_t, color)
        + offsetof(ngx_http_lua_shdict_node_t, data)
        + key.len
        + value.len;

    dd("overhead = %d", (int) (offsetof(ngx_rbtree_node_t, color)
       + offsetof(ngx_http_lua_shdict_node_t, data)));

    node = ngx_slab_alloc_locked(ctx->shpool, n);

    if (node == NULL) {

        if (flags & NGX_HTTP_LUA_SHDICT_SAFE_STORE) {
            ngx_shmtx_unlock(&ctx->shpool->mutex);

            lua_pushboolean(L, 0);
            lua_pushliteral(L, "no memory");
            return 2;
        }

        ngx_log_debug1(NGX_LOG_DEBUG_HTTP, ctx->log, 0,
                       "lua shared dict set: overriding non-expired items "
                       "due to memory shortage for entry \"%V\"", &key);

        for (i = 0; i < 30; i++) {
            if (ngx_http_lua_shdict_expire(ctx, 0) == 0) {
                break;
            }

            forcible = 1;

            node = ngx_slab_alloc_locked(ctx->shpool, n);
            if (node != NULL) {
                goto allocated;
            }
        }

        ngx_shmtx_unlock(&ctx->shpool->mutex);

        lua_pushboolean(L, 0);
        lua_pushliteral(L, "no memory");
        lua_pushboolean(L, forcible);
        return 3;
    }

allocated:

    sd = (ngx_http_lua_shdict_node_t *) &node->color;

    node->key = hash;
    sd->key_len = (u_short) key.len;

    if (exptime > 0) {
        tp = ngx_timeofday();
        sd->expires = (uint64_t) tp->sec * 1000 + tp->msec
                      + (uint64_t) (exptime * 1000);

    } else {
        sd->expires = 0;
    }

    sd->user_flags = user_flags;

    sd->value_len = (uint32_t) value.len;

    dd("setting value type to %d", value_type);

    sd->value_type = (uint8_t) value_type;

    p = ngx_copy(sd->data, key.data, key.len);
    ngx_memcpy(p, value.data, value.len);

    ngx_rbtree_insert(&ctx->sh->rbtree, node);

    ngx_queue_insert_head(&ctx->sh->lru_queue, &sd->queue);

    ngx_shmtx_unlock(&ctx->shpool->mutex);

    lua_pushboolean(L, 1);
    lua_pushnil(L);
    lua_pushboolean(L, forcible);
    return 3;
}
```

上記の1148行目の `insert:` ラベルの後の1172行目で `ngx_slab_alloc_locked` 関数を呼び出しています。

1164行目でメモリ割り当てするバイト数を計算しています。ログ出力を追加して動作確認したところ
`offsetof(ngx_rbtree_node_t, color)` は32、
`offsetof(ngx_http_lua_shdict_node_t, data)` は36 でした。

`ngx_slab_alloc_locked` 関数の実装は以下の通りです。

[nginx/src/core/ngx_slab.c#L183-L417](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.c#L183-L417)

```c {linenos=table,linenostart=183}
void *
ngx_slab_alloc_locked(ngx_slab_pool_t *pool, size_t size)
{
    size_t            s;
    uintptr_t         p, m, mask, *bitmap;
    ngx_uint_t        i, n, slot, shift, map;
    ngx_slab_page_t  *page, *prev, *slots;

    if (size > ngx_slab_max_size) {

        ngx_log_debug1(NGX_LOG_DEBUG_ALLOC, ngx_cycle->log, 0,
                       "slab alloc: %uz", size);

        page = ngx_slab_alloc_pages(pool, (size >> ngx_pagesize_shift)
                                          + ((size % ngx_pagesize) ? 1 : 0));
        if (page) {
            p = ngx_slab_page_addr(pool, page);

        } else {
            p = 0;
        }

        goto done;
    }

    if (size > pool->min_size) {
        shift = 1;
        for (s = size - 1; s >>= 1; shift++) { /* void */ }
        slot = shift - pool->min_shift;

    } else {
        shift = pool->min_shift;
        slot = 0;
    }

    pool->stats[slot].reqs++;

    ngx_log_debug2(NGX_LOG_DEBUG_ALLOC, ngx_cycle->log, 0,
                   "slab alloc: %uz slot: %ui", size, slot);

    slots = ngx_slab_slots(pool);
    page = slots[slot].next;

    if (page->next != page) {

        if (shift < ngx_slab_exact_shift) {

            bitmap = (uintptr_t *) ngx_slab_page_addr(pool, page);

            map = (ngx_pagesize >> shift) / (8 * sizeof(uintptr_t));

            for (n = 0; n < map; n++) {

                if (bitmap[n] != NGX_SLAB_BUSY) {

                    for (m = 1, i = 0; m; m <<= 1, i++) {
                        if (bitmap[n] & m) {
                            continue;
                        }

                        bitmap[n] |= m;

                        i = (n * 8 * sizeof(uintptr_t) + i) << shift;

                        p = (uintptr_t) bitmap + i;

                        pool->stats[slot].used++;

                        if (bitmap[n] == NGX_SLAB_BUSY) {
                            for (n = n + 1; n < map; n++) {
                                if (bitmap[n] != NGX_SLAB_BUSY) {
                                    goto done;
                                }
                            }

                            prev = ngx_slab_page_prev(page);
                            prev->next = page->next;
                            page->next->prev = page->prev;

                            page->next = NULL;
                            page->prev = NGX_SLAB_SMALL;
                        }

                        goto done;
                    }
                }
            }

        } else if (shift == ngx_slab_exact_shift) {

            for (m = 1, i = 0; m; m <<= 1, i++) {
                if (page->slab & m) {
                    continue;
                }

                page->slab |= m;

                if (page->slab == NGX_SLAB_BUSY) {
                    prev = ngx_slab_page_prev(page);
                    prev->next = page->next;
                    page->next->prev = page->prev;

                    page->next = NULL;
                    page->prev = NGX_SLAB_EXACT;
                }

                p = ngx_slab_page_addr(pool, page) + (i << shift);

                pool->stats[slot].used++;

                goto done;
            }

        } else { /* shift > ngx_slab_exact_shift */

            mask = ((uintptr_t) 1 << (ngx_pagesize >> shift)) - 1;
            mask <<= NGX_SLAB_MAP_SHIFT;

            for (m = (uintptr_t) 1 << NGX_SLAB_MAP_SHIFT, i = 0;
                 m & mask;
                 m <<= 1, i++)
            {
                if (page->slab & m) {
                    continue;
                }

                page->slab |= m;

                if ((page->slab & NGX_SLAB_MAP_MASK) == mask) {
                    prev = ngx_slab_page_prev(page);
                    prev->next = page->next;
                    page->next->prev = page->prev;

                    page->next = NULL;
                    page->prev = NGX_SLAB_BIG;
                }

                p = ngx_slab_page_addr(pool, page) + (i << shift);

                pool->stats[slot].used++;

                goto done;
            }
        }

        ngx_slab_error(pool, NGX_LOG_ALERT, "ngx_slab_alloc(): page is busy");
        ngx_debug_point();
    }

    page = ngx_slab_alloc_pages(pool, 1);

    if (page) {
        if (shift < ngx_slab_exact_shift) {
            bitmap = (uintptr_t *) ngx_slab_page_addr(pool, page);

            n = (ngx_pagesize >> shift) / ((1 << shift) * 8);

            if (n == 0) {
                n = 1;
            }

            /* "n" elements for bitmap, plus one requested */

            for (i = 0; i < (n + 1) / (8 * sizeof(uintptr_t)); i++) {
                bitmap[i] = NGX_SLAB_BUSY;
            }

            m = ((uintptr_t) 1 << ((n + 1) % (8 * sizeof(uintptr_t)))) - 1;
            bitmap[i] = m;

            map = (ngx_pagesize >> shift) / (8 * sizeof(uintptr_t));

            for (i = i + 1; i < map; i++) {
                bitmap[i] = 0;
            }

            page->slab = shift;
            page->next = &slots[slot];
            page->prev = (uintptr_t) &slots[slot] | NGX_SLAB_SMALL;

            slots[slot].next = page;

            pool->stats[slot].total += (ngx_pagesize >> shift) - n;

            p = ngx_slab_page_addr(pool, page) + (n << shift);

            pool->stats[slot].used++;

            goto done;

        } else if (shift == ngx_slab_exact_shift) {

            page->slab = 1;
            page->next = &slots[slot];
            page->prev = (uintptr_t) &slots[slot] | NGX_SLAB_EXACT;

            slots[slot].next = page;

            pool->stats[slot].total += 8 * sizeof(uintptr_t);

            p = ngx_slab_page_addr(pool, page);

            pool->stats[slot].used++;

            goto done;

        } else { /* shift > ngx_slab_exact_shift */

            page->slab = ((uintptr_t) 1 << NGX_SLAB_MAP_SHIFT) | shift;
            page->next = &slots[slot];
            page->prev = (uintptr_t) &slots[slot] | NGX_SLAB_BIG;

            slots[slot].next = page;

            pool->stats[slot].total += ngx_pagesize >> shift;

            p = ngx_slab_page_addr(pool, page);

            pool->stats[slot].used++;

            goto done;
        }
    }

    p = 0;

    pool->stats[slot].fails++;

done:

    ngx_log_debug1(NGX_LOG_DEBUG_ALLOC, ngx_cycle->log, 0,
                   "slab alloc: %p", (void *) p);

    return (void *) p;
}
```

`ngx_slab_max_size` は上記のように 2048 なのでそれより大きいサイズを割り当てる場合は
191行目の if の条件が true になり、193～205行目で処理されることになります。

2048バイト以下のサイズの場合は 208行目以降で処理されます。
`pool->min_size` は8なので、8バイトより大きい場合は209～211行目、8バイト以下なら214～215行目の分岐になります。

`size` が8以下なら `slot` は 0, `shift` は3になります。
`size` が9～16なら `slot` は 1, `shift` は4になります。
`size` が17～32なら `slot` は 2, `shift` は5になります。
以下同様に2倍になるごとに `slot` と `shift` が増えていき、
最後は `size` が1025～2048 で `slot` が 8, `shift` が11になります。

218行目でスロット毎のメモリ割り当て依頼回数をインクリメントしています。

226～330行目では既存のページを再利用しているようです。249、291、322行目でスロット毎の使用中カウンタ `pool->stats[slot].used` をインクリメントしています。

332行目では `ngx_slab_alloc_pages` 関数を呼んで新たにページを割り当てています。

334～405行目では `pool->stats[slot].used` をインクリメントしつつ、スロット毎の使用バイト数 `pool->stats[slot].total` も増やしています。

405行目までの処理で正常に割り当てできた場合は 411行目の `done` ラベルに飛びます。
失敗した場合は409行目でスロット毎の失敗回数 `pool->stats[slot].fails` をインクリメントしています。


`ngx_slab_alloc_pages` 関数の実装は以下の通りです。

[nginx/src/core/ngx_slab.c#L678-L731](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.c#L678-L731)

```c {linenos=table,linenostart=678}
static ngx_slab_page_t *
ngx_slab_alloc_pages(ngx_slab_pool_t *pool, ngx_uint_t pages)
{
    ngx_slab_page_t  *page, *p;

    for (page = pool->free.next; page != &pool->free; page = page->next) {

        if (page->slab >= pages) {

            if (page->slab > pages) {
                page[page->slab - 1].prev = (uintptr_t) &page[pages];

                page[pages].slab = page->slab - pages;
                page[pages].next = page->next;
                page[pages].prev = page->prev;

                p = (ngx_slab_page_t *) page->prev;
                p->next = &page[pages];
                page->next->prev = (uintptr_t) &page[pages];

            } else {
                p = (ngx_slab_page_t *) page->prev;
                p->next = page->next;
                page->next->prev = page->prev;
            }

            page->slab = pages | NGX_SLAB_PAGE_START;
            page->next = NULL;
            page->prev = NGX_SLAB_PAGE;

            pool->pfree -= pages;

            if (--pages == 0) {
                return page;
            }

            for (p = page + 1; pages; pages--) {
                p->slab = NGX_SLAB_PAGE_BUSY;
                p->next = NULL;
                p->prev = NGX_SLAB_PAGE;
                p++;
            }

            return page;
        }
    }

    if (pool->log_nomem) {
        ngx_slab_error(pool, NGX_LOG_CRIT,
                       "ngx_slab_alloc() failed: no memory");
    }

    return NULL;
}
```

`ngx_slab_pool_t *` 型の `pool` の `pool->free` は `ngx_slab_page_t` 型になっています。上に書いていますが再度引用します。

[nginx/src/core/ngx_slab.h#L16-L22](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.h#L16-L22)

```c {linenos=table,linenostart=16}
typedef struct ngx_slab_page_s  ngx_slab_page_t;

struct ngx_slab_page_s {
    uintptr_t         slab;
    ngx_slab_page_t  *next;
    uintptr_t         prev;
};
```

`next` と `prev` フィールドで双方向リンクトリストになっています。
683行目の `for` 文を見るとリストの最後の要素では `next` を自分自身に指すようになっているようです。

`slab` フィールドは `uintptr_t` 型で685行目ではページ数と比較しています。

704～719行目を見ると複数のページがメモリ上に連続して存在して、ページ割り付けの際に複数ページを使用する場合は、最初のページの `slab` フィールドにはページ数に `NGX_SLAB_PAGE_START` のフラグを追加し、継続するページの `slab` フィールドには `NGX_SLAB_PAGE_BUSY` を設定しています。

`NGX_SLAB_PAGE_START` や `NGX_SLAB_PAGE_BUSY` の定数は以下のように定義されています。

[nginx/src/core/ngx_slab.c#L17-L41](https://github.com/nginx/nginx/blob/release-1.13.5/src/core/ngx_slab.c#L17-L41)

```c {linenos=table,linenostart=17}
#if (NGX_PTR_SIZE == 4)

#define NGX_SLAB_PAGE_FREE   0
#define NGX_SLAB_PAGE_BUSY   0xffffffff
#define NGX_SLAB_PAGE_START  0x80000000

#define NGX_SLAB_SHIFT_MASK  0x0000000f
#define NGX_SLAB_MAP_MASK    0xffff0000
#define NGX_SLAB_MAP_SHIFT   16

#define NGX_SLAB_BUSY        0xffffffff

#else /* (NGX_PTR_SIZE == 8) */

#define NGX_SLAB_PAGE_FREE   0
#define NGX_SLAB_PAGE_BUSY   0xffffffffffffffff
#define NGX_SLAB_PAGE_START  0x8000000000000000

#define NGX_SLAB_SHIFT_MASK  0x000000000000000f
#define NGX_SLAB_MAP_MASK    0xffffffff00000000
#define NGX_SLAB_MAP_SHIFT   32

#define NGX_SLAB_BUSY        0xffffffffffffffff

#endif
```

`ngx_slab_alloc_pages` 関数のコードを改めて眺めてみると、この関数内では新たなメモリ割り当ては行っていないことに気づきます。
ということは `pool` の作成時に `pool->free` に割り当てられたメモリを使いまわしているだけということです。

遡って見てみると ngx_cycle.c の478行目で呼び出している `ngx_shm_alloc` 関数が 
[mmap(2)](http://man7.org/linux/man-pages/man2/mmap.2.html) システムコールを使ってメモリを割り当てていました。

OSによっては `ngx_shmem.c` の `#if` の違う分岐になりますが、Linuxでは上記の `mmap(2)` のマニュアルに `MAP_ANON` が deprecated ですが存在したので、Linuxでは下記の実装が使われていると思います。

[nginx/src/os/unix/ngx_shmem.c#L12-L28](https://github.com/nginx/nginx/blob/release-1.13.5/src/os/unix/ngx_shmem.c#L12-L28)

```c {linenos=table,linenostart=12}
#if (NGX_HAVE_MAP_ANON)

ngx_int_t
ngx_shm_alloc(ngx_shm_t *shm)
{
    shm->addr = (u_char *) mmap(NULL, shm->size,
                                PROT_READ|PROT_WRITE,
                                MAP_ANON|MAP_SHARED, -1, 0);

    if (shm->addr == MAP_FAILED) {
        ngx_log_error(NGX_LOG_ALERT, shm->log, ngx_errno,
                      "mmap(MAP_ANON|MAP_SHARED, %uz) failed", shm->size);
        return NGX_ERROR;
    }

    return NGX_OK;
}
```

ここで上で読み飛ばした `ngx_slab_init` 関数の続きを見ます。

109～111行目で `slots` と `p` は `*pool` の `ngx_slab_pool_t` 構造体の直後のアドレスに設定されます。

上記の通り `n` は 9 なので118～123行目で 0～8の9個のスロットを作成しています。

125行目で `p` は9個のスロットの直後のアドレスを指します。

そこから9個の `ngx_slab_stat_t` 構造体の領域が確保され、スロット毎の統計情報が保持されます。

130行目で `p` は統計情報の直後のアドレスを指します。

132行目で `size` は `ngx_slab_pool_t` 構造体と `ngx_slab_stat_t` 構造体の9組分のサイズを差し引かれます。

134行目で `pages` にページ数の計算結果を設定しています。上記の `size` を `(ngx_pagesize + sizeof(ngx_slab_page_t))` で割っていますので、各ページに対して 4096バイトのデータ領域と `ngx_slab_page_t` 構造体による管理情報が存在することがわかります。

136行目で `pool->pages` にページの先頭のアドレスをセットしています。

137行目で `pool->pages` から先頭 `pages * sizeof(ngx_slab_page_t)` バイトをゼロクリアしています。このことから上記の各ページに対応する 4096バイトのデータ領域と `ngx_slab_page_t` 構造体のうち `ngx_slab_page_t` 構造体が `pool->pages` の先頭にページ数分連続して存在し、その後に 4096 バイトのページがページ数分続くことがわかります。

139行目以降はリンクトリストの要素を設定しています。

```c {linenos=table,linenostart=98}
void
ngx_slab_init(ngx_slab_pool_t *pool)
{
    u_char           *p;
    size_t            size;
    ngx_int_t         m;
    ngx_uint_t        i, n, pages;
    ngx_slab_page_t  *slots, *page;

    pool->min_size = (size_t) 1 << pool->min_shift;

    slots = ngx_slab_slots(pool);

    p = (u_char *) slots;
    size = pool->end - p;

    ngx_slab_junk(p, size);

    n = ngx_pagesize_shift - pool->min_shift;

    for (i = 0; i < n; i++) {
        /* only "next" is used in list head */
        slots[i].slab = 0;
        slots[i].next = &slots[i];
        slots[i].prev = 0;
    }

    p += n * sizeof(ngx_slab_page_t);

    pool->stats = (ngx_slab_stat_t *) p;
    ngx_memzero(pool->stats, n * sizeof(ngx_slab_stat_t));

    p += n * sizeof(ngx_slab_stat_t);

    size -= n * (sizeof(ngx_slab_page_t) + sizeof(ngx_slab_stat_t));

    pages = (ngx_uint_t) (size / (ngx_pagesize + sizeof(ngx_slab_page_t)));

    pool->pages = (ngx_slab_page_t *) p;
    ngx_memzero(pool->pages, pages * sizeof(ngx_slab_page_t));

    page = pool->pages;

    /* only "next" is used in list head */
    pool->free.slab = 0;
    pool->free.next = page;
    pool->free.prev = 0;

    page->slab = pages;
    page->next = &pool->free;
    page->prev = (uintptr_t) &pool->free;

    pool->start = ngx_align_ptr(p + pages * sizeof(ngx_slab_page_t),
                                ngx_pagesize);

    m = pages - (pool->end - pool->start) / ngx_pagesize;
    if (m > 0) {
        pages -= m;
        page->slab = pages;
    }

    pool->last = pool->pages + pages;
    pool->pfree = pages;

    pool->log_nomem = 1;
    pool->log_ctx = &pool->zero;
    pool->zero = '\0';
}
