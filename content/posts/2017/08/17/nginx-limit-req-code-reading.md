+++
title="ngx_http_limit_req_moduleのコードリーディング"
date = "2017-08-17T09:38:00+09:00"
tags = ["nginx"]
categories = ["blog"]
+++


## はじめに

[Module ngx_http_limit_req_module](http://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
を使おうと思ってコードを読んでみたのでメモです。

## leaky bucket

上記のドキュメントに "leaky bucket" を使ってリクエスト数の制御を行っていると書かれています。

leaky bucketについては
[Leaky Bucket Algorithm| Computer Networks - GeeksforGeeks](http://www.geeksforgeeks.org/leaky-bucket-algorithm/)
の説明が具体例もあってわかりやすかったです。

## nginxの実装

### rateとlimitの値を読み取る

設定からrateとlimitを読み取るコードは以下の部分です。内部的には秒間リクエスト数を1000倍して管理しています。

[ngx_http_limit_req_module.c#L792-L828](https://github.com/nginx/nginx/blob/release-1.13.4/src/http/modules/ngx_http_limit_req_module.c#L792-L828)

```c
if (ngx_strncmp(value[i].data, "rate=", 5) == 0) {

    len = value[i].len;
    p = value[i].data + len - 3;

    if (ngx_strncmp(p, "r/s", 3) == 0) {
        scale = 1;
        len -= 3;

    } else if (ngx_strncmp(p, "r/m", 3) == 0) {
        scale = 60;
        len -= 3;
    }

    rate = ngx_atoi(value[i].data + 5, len - 5);
    if (rate <= 0) {
        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "invalid rate \"%V\"", &value[i]);
        return NGX_CONF_ERROR;
    }

    continue;
}

ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                   "invalid parameter \"%V\"", &value[i]);
return NGX_CONF_ERROR;
```

    }

    if (name.len == 0) {
        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "\"%V\" must have \"zone\" parameter",
                           &cmd->name);
        return NGX_CONF_ERROR;
    }

    ctx->rate = rate * 1000 / scale;

[ngx_http_limit_req_module.c#L885-L937](https://github.com/nginx/nginx/blob/release-1.13.4/src/http/modules/ngx_http_limit_req_module.c#L885-L937)

```c
if (ngx_strncmp(value[i].data, "burst=", 6) == 0) {

    burst = ngx_atoi(value[i].data + 6, value[i].len - 6);
    if (burst <= 0) {
        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "invalid burst rate \"%V\"", &value[i]);
        return NGX_CONF_ERROR;
    }

    continue;
}

if (ngx_strcmp(value[i].data, "nodelay") == 0) {
    nodelay = 1;
    continue;
}

ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                   "invalid parameter \"%V\"", &value[i]);
return NGX_CONF_ERROR;
```

    }

    if (shm_zone == NULL) {
        ngx_conf_log_error(NGX_LOG_EMERG, cf, 0,
                           "\"%V\" must have \"zone\" parameter",
                           &cmd->name);
        return NGX_CONF_ERROR;
    }

    limits = lrcf->limits.elts;

    if (limits == NULL) {
        if (ngx_array_init(&lrcf->limits, cf->pool, 1,
                           sizeof(ngx_http_limit_req_limit_t))
            != NGX_OK)
        {
            return NGX_CONF_ERROR;
        }
    }

    for (i = 0; i < lrcf->limits.nelts; i++) {
        if (shm_zone == limits[i].shm_zone) {
            return "is duplicate";
        }
    }

    limit = ngx_array_push(&lrcf->limits);
    if (limit == NULL) {
        return NGX_CONF_ERROR;
    }

    limit->shm_zone = shm_zone;
    limit->burst = burst * 1000;

### nginxのlimit_reqのleaky bucket

nginxの実装は（おそらく軽く動かすために）ちょっと変わった方法をとっていて、タイマーで定期的に許容できる量を更新していくのではなく、以下のように前回のアクセスから今回のアクセスまでの時間にレートを掛けて引くという方式を取っています。

[ngx_http_limit_req_module.c#L400-L412](https://github.com/nginx/nginx/blob/release-1.13.4/src/http/modules/ngx_http_limit_req_module.c#L400-L412)

```c
ms = (ngx_msec_int_t) (now - lr->last);

excess = lr->excess - ctx->rate * ngx_abs(ms) / 1000 + 1000;

if (excess < 0) {
    excess = 0;
}

*ep = excess;

if ((ngx_uint_t) excess > limit->burst) {
    return NGX_BUSY;
}
```

もし2つのアクセスがほぼ同時にあったとすると `now - lr->last` の部分がほぼ `0` になります。
すると `excess = lr->excess - ctx->rate * ngx_abs(ms) / 1000 + 1000;` は
`excess = lr->excess + 1000;` とほぼ同じことになります。

その下の if 文で `excess` がマイナスの場合は0にしています。
`lr->excess` を設定する箇所はここでは省略しますが、前回の `excess` の値になっています。
ということでほぼ同時にアクセスがあると `excess = lr->excess + 1000;` の結果、 `excess` は
1000より大きな値になります。

すると `limit->burst` が 0 だと `NGX_BUSY` を返してリミットに引っかかることになります。
同時にアクセスがあっただけでひっかかるのは困るので `burst` を良い感じに調整して設定しておく必要があります。

また上記の `excess` の式でわかるように `rate` の設定値は秒間リクエスト数と言っても、秒単位で制御しているわけではないので、正確な値というよりおおよその目安として考えておいたほうが良いと思います。
