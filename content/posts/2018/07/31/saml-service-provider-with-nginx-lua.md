+++
title="nginx luaでSAMLのService Providerを作ってみた"
date = "2018-07-31T10:00:00+09:00"
lastmod = "2018-08-01T20:55:00+09:00"
tags = ["nginx", "lua", "saml", "sso"]
categories = ["blog"]
+++


# はじめに

[nginxとshibbolethでSAML2のシングルサインオンを試してみた](/blog/2018/07/04/saml2-single-sign-on-with-nginx-and-shibboleth/) では [Service Provider – Shibboleth Consortium](https://www.shibboleth.net/products/service-provider/) を使いましたが、汎用的な分、設定方法のドキュメント
[NativeSPConfiguration - Shibboleth 2 - Shibboleth Wiki](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPConfiguration) を見ても圧倒される感がありました （なお、ページ上部の囲みを見ると Shibboleth SP は先日 3.x がリリースされて 2.x はEOLになったそうです）。

そこで、 nginx lua で SAML の Service Provider (以下 SP と略）を書いてみたところ、動くものが出来たので公開して説明を書いておきます。

[hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider)

ただし、この Service Provider は職場で動いている内製（非公開）の ID Provider （以下 IdP と略）で認証できることが目的であって、SAML 認証の仕様を全てカバーするつもりは全く無いです。そもそも SAML の仕様を読んですら無いです。

# SAML認証のシーケンス図

今回実装したSAML認証のシーケンス図です。

.. image:: {attach}/images/2018/07/31/saml-sequence.svg
        :width: 100%
	:alt: SAML sequence diagram

上記の構成ですが、背景として、今回 SAML 認証を実装するシステムがフロントに nginx を置く構成を採用しているというのがあります。また、今後いろんな社内サービスで SAML 認証対応することを考えると、 Upstream のアプリケーションの改修が最小限ですむほうが楽なので、極力 nginx 側で対応できる方が良いだろうと考えました。

今回の実装ですと、ログインしたユーザのメールアドレスが Upstream のリクエストへのリクエストヘッダに付与されるので、 Upstream 側は必要に応じてそれを利用するように改修します。特にユーザを区別必要する必要がなければ何もしなくて良いです。

実は当初は Service Provider は Go で実装したのですが、その後 nginx lua で実装できれば nginx 以外のデーモンが増えないので運用が楽だなと思って実装してみたというのが今回の経緯です。

図では役割として nginx と Service Provider を分けて書いていますが、今回の実装では nginx 上で Service Provider を動かしているので、プロセスとしては nginx と Service Provider は同一です。

# インストール手順

今回の動作環境は CentOS 7 です。

## nginx関連のセットアップ

nginx関連で必要なパッケージは自作のrpmに全て同梱しました。

* [hnakamur/nginx Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/nginx/)

以下の手順でインストールできます。

```console
sudo yum install epel-release
sudo curl -sSL -o /etc/yum.repos.d/hnakamur-luajit.repo https://copr.fedoraproject.org/coprs/hnakamur/luajit/repo/epel-7/hnakamur-luajit-epel-7.repo
sudo curl -sSL -o /etc/yum.repos.d/hnakamur-nginx.repo https://copr.fedoraproject.org/coprs/hnakamur/nginx/repo/epel-7/hnakamur-nginx-epel-7.repo
sudo yum install nginx
```

## xmlsec1のインストール

勤務先の IdP が `xmlsec1 --sign` で SAML Response XML の署名を行っていることもあり、今回作成した SAML Service Provider では `xmlsec1 --verify` で IdP から受け取った SAML Response XML の検証を行うように実装しました。

このため以下のようにして必要なパッケージをインストールします。

```console
sudo yum install xmlsec1 xmlsec1-openssl
```

CentOS 7 の `xmlsec1` マニュアルページがウェブ上で見つけられなかったので Ubuntu のを貼っておきます。
[man 1 xmlsec1](http://manpages.ubuntu.com/manpages/bionic/en/man1/xmlsec1.1.html)

## libz.so のシンボリックリンク作成
[hamishforbes/lua-ffi-zlib](https://github.com/hamishforbes/lua-ffi-zlib) が 
LuaJIT の [ffi.load](http://luajit.org/ext_ffi_api.html#ffi_load) を使って
:code:[ffi.load("z")` というコード ( `lua-ffi-zlib/ffi-zlib.lua:98](https://github.com/hamishforbes/lua-ffi-zlib/blob/3d6dbee710b4712b8d0e0235425abee04a22b1bd/lib/ffi-zlib.lua#L98) 参照)
を実行し、その結果 `libz.so` というファイル名を探すことになります。
しかし、 CentOS 7 では `libz.so.1` というファイルはあるのですが `libz.so` は無いため、以下のようにシンボリックリンクを作成する必要があります。

```console
ln -s libz.so.1 /lib64/libz.so
```

2018-08-01 追記。どうやらこれは LXD の CentOS 7 コンテナ特有の問題だったようで、他の環境では上記のシンボリックリンクは存在していました。

# 設定例

[hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider)
の
[/example_config/etc/nginx](https://github.com/hnakamur/nginx-lua-saml-service-provider/tree/master/example_config/etc/nginx) 以下に設定例を入れておきました。

`/etc/nginx/conf.d/default.conf`

```text
lua_package_path '/usr/lib/nginx/lua/?.lua;/etc/nginx/lua/?.lua;;';

lua_shared_dict sso_sessions 1m;
lua_shared_dict sso_redirect_urls 128k;

server {
    listen 443 ssl;
    server_name sp.example.com;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 5m;
    ssl_ciphers AESGCM:HIGH:!EXP:!RC4:!LOW:!aNULL;
    ssl_prefer_server_ciphers on;
    #ssl_protocols TLSv1.2;

    ssl_certificate /etc/pki/tls/certs/sp.example.com.crt;
    ssl_certificate_key /etc/pki/tls/private/sp.example.com.key;

    location / {
	access_by_lua_block {
	    local config = require "saml.service_provider.config"
	    local sp = require("saml.service_provider"):new(config)

	    local ok, err = sp:access()
	    if err ~= nil then
		ngx.log(ngx.ERR, err)
		ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
		return
	    end
	}

	proxy_pass http://127.0.0.1:8080;
    }

    location /sso/finish-login {
	content_by_lua_block {
	    local config = require "saml.service_provider.config"
	    local sp = require("saml.service_provider"):new(config)

	    local ok, err = sp:finish_login()
	    if err ~= nil then
		ngx.log(ngx.ERR, err)
		ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
		return
	    end
	}
    }

    location /sso/logout {
	content_by_lua_block {
	    local config = require "saml.service_provider.config"
	    local sp = require("saml.service_provider"):new(config)

	    local ok, err = sp:logout()
	    if err ~= nil then
		ngx.log(ngx.ERR, err)
		ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
		return
	    end
	}
    }
}
```

上記の設定例では `https://sp.example.com/sso/logout` にアクセスするとログアウトするようになっています。 Upstream 側の画面からログアウトできるようにするには、ここへのリンクを貼れば OK です。

`/etc/nginx/lua/saml/service_provider/config.lua`

```text
return {
    key_attribute_name = "mail",
    redirect = {
	url_after_login = "/",
	url_after_logout = "/"
    },
    request = {
	idp_dest_url = "https://idp.example.net/sso_redirect",
	sp_entity_id = "https://sp.example.com/sso",
	sp_saml_finish_url = "https://sp.example.com/sso/finish-login",
	urls_before_login = {
	    dict_name = "sso_redirect_urls",
	    expire_seconds = 180
	}
    },
    response = {
	xmlsec_command = "/usr/bin/xmlsec1",
	idp_cert_filename = "/usr/local/etc/idp.crt"
    },
    session = {
	cookie = {
	    name = "sso_session_id",
	    path = "/",
	    secure = true
	},
	store = {
	    dict_name = "sso_sessions",
	    expire_seconds = 600
	}
    }
}
```

この設定ファイルは [Lua](https://www.lua.org/) で書いています。 Lua はこのように設定ファイルを書くときに読みやすくなるようにも設計されたと聞いたことがありますが、確かに良い感じです。なお、ここでは書いていませんが `--` で始まるコメント行を含めることも出来ます。

あとは `/usr/local/etc/idp.crt` に IdP の証明書（PEM形式）を配備します。

```text
-----BEGIN CERTIFICATE-----
MIIDbDCCAlQCCQC2lvI/q52P9zANBgkqhkiG9w0BAQUFADB4MQswCQYDVQQGEwJK
…(略)…
MOnar9vP8eOYXOtO9laTow==
-----END CERTIFICATE-----
```

# SP が保持する状態についての説明

今回の SP の実装では [openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module) の
[ngx.shared.DICT](https://github.com/openresty/lua-nginx-module#ngxshareddict) を 2 つ使っています。

上記の設定例では `sso_redirect_urls` と `sso_sessions` です。

`sso_redirect_urls` はログイン直前に開いていた URL を保存しておいて、ログイン後にその URL にリダイレクトさせるようにさせるためのものです。ログインが必要な領域（上記の設定例では `/` 全般）に非ログイン状態でアクセスしたときに、 URL を保存して IdP のログイン画面にリダイレクトします。

`sso_sessions` のほうはセッション情報を保存するための dict です。 IdP でのログイン成功後、 IdP から SP に Base64 エンコードされた署名付きの SAML Response XML が送られてきます。その署名を検証し、 Response に含まれるユーザのメールアドレス （これは IdP の設定次第です）を取り出します。セッション ID を暗号レベルの 128bit 乱数として生成して、それをキーとしメールアドレスを値として、 `sso_sessions` に保存しています。

1 つの nginx で複数のバックエンドシステムを扱う場合でも、上記の設定を発展させればログイン状態を共有することが出来るでしょう。
