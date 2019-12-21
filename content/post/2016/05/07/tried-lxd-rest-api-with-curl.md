+++
Categories = []
Description = ""
Tags = ["lxd", "curl"]
date = "2016-05-07T21:17:34+09:00"
title = "LXDのREST APIをcurlで試してみた"

+++
## LXDのREST API
[Linux Containers - LXD - REST API](https://linuxcontainers.org/ja/lxd/rest-api/)と[lxd/rest-api.md at master · lxc/lxd](https://github.com/lxc/lxd/blob/master/doc/rest-api.md)にLXDのREST APIについて説明があります。

また[Using the REST API](https://github.com/lxc/lxd#using-the-rest-api)に `curl` コマンドでのAPI呼び出し例が書かれていました。

## curlでhttpsのエンドポイントにアクセスしてみたがエラー

まずはhttpsのURLで [/1.0](https://github.com/lxc/lxd/blob/master/doc/rest-api.md#10) エンドポイントを試してみたのですが、 `ALPN, server did not agree to a protocol` というエラーになってしまいました。

```
$ curl -k -v --cert ~/.config/lxc/client.crt --key ~/.config/lxc/client.key https://127.0.0.1:8443/1.0
*   Trying 127.0.0.1...
* Connected to 127.0.0.1 (127.0.0.1) port 8443 (#0)
* found 173 certificates in /etc/ssl/certs/ca-certificates.crt
* found 692 certificates in /etc/ssl/certs
* ALPN, offering http/1.1
* SSL connection using TLS1.2 / ECDHE_RSA_AES_128_GCM_SHA256
*        server certificate verification SKIPPED
*        server certificate status verification SKIPPED
*        common name: root@express (does not match '127.0.0.1')
*        server certificate expiration date OK
*        server certificate activation date OK
*        certificate public key: RSA
*        certificate version: #3
*        subject: O=linuxcontainers.org,CN=root@express
*        start date: Tue, 03 May 2016 11:26:51 GMT
*        expire date: Fri, 01 May 2026 11:26:51 GMT
*        issuer: O=linuxcontainers.org,CN=root@express
*        compression: NULL
* ALPN, server did not agree to a protocol
> GET /1.0 HTTP/1.1
> Host: 127.0.0.1:8443
> User-Agent: curl/7.47.0
> Accept: */*
>
< HTTP/1.1 200 OK
< Content-Type: application/json
< Date: Sat, 07 May 2016 12:25:53 GMT
< Content-Length: 162
<
{"type":"sync","status":"Success","status_code":200,"metadata":{"api_extensions":[],"api_status":"stable","api_version":"1.0","auth":"untrusted","public":false}}
* Connection #0 to host 127.0.0.1 left intact
```

この件は[\[lxc-users\] The error "ALPN, server did not agree to a protocol" from LXD Rest API](https://lists.linuxcontainers.org/pipermail/lxc-users/2016-May/011603.html)で質問してみました。

## curlでunix domain socket経由でアクセスしてみたら成功

[curlでunix domain socket経由アクセスする - Qiita](http://qiita.com/toritori0318/items/193df8f749a9c4bda883)を参考に以下のようにアクセスしてみると成功しました。

```
$ curl -s --unix-socket /var/lib/lxd/unix.socket https:/1.0 | jq .
{
  "type": "sync",
  "status": "Success",
  "status_code": 200,
  "metadata": {
    "api_extensions": [],
    "api_status": "stable",
    "api_version": "1.0",
    "auth": "trusted",
    "config": {
      "core.https_address": "127.0.0.1:8443",
      "core.trust_password": true
    },
    "environment": {
      "addresses": [
        "127.0.0.1:8443"
      ],
      "architectures": [
        "x86_64",
        "i686"
      ],
      "certificate": "-----BEGIN CERTIFICATE-----\n …(略)… \n-----END CERTIFICATE-----\n",
      "driver": "lxc",
      "driver_version": "2.0.0",
      "kernel": "Linux",
      "kernel_architecture": "x86_64",
      "kernel_version": "4.4.0-21-generic",
      "server": "lxd",
      "server_pid": 6446,
      "server_version": "2.0.0",
      "storage": "dir",
      "storage_version": ""
    },
    "public": false
  }
}
```

`sudo lxd init` でLXDをネットワーク越しに使うかの問いにnoと答えた環境では以下のような出力になりました。

```
$ curl -s --unix-socket /var/lib/lxd/unix.socket http:/1.0 | jq .
{
  "type": "sync",
  "status": "Success",
  "status_code": 200,
  "metadata": {
    "api_extensions": [],
    "api_status": "stable",
    "api_version": "1.0",
    "auth": "trusted",
    "config": {},
    "environment": {
      "addresses": [],
      "architectures": [
        "x86_64",
        "i686"
      ],
      "certificate": "-----BEGIN CERTIFICATE-----\n …(略)… \n-----END CERTIFICATE-----\n",
      "driver": "lxc",
      "driver_version": "2.0.0",
      "kernel": "Linux",
      "kernel_architecture": "x86_64",
      "kernel_version": "4.4.0-21-generic",
      "server": "lxd",
      "server_pid": 2150,
      "server_version": "2.0.0",
      "storage": "dir",
      "storage_version": ""
    },
    "public": false
  }
}
```
