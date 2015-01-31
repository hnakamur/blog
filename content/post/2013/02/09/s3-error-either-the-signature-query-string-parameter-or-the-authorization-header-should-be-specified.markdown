---
layout: post
title: "S3 error: Either the Signature query string parameter or the Authorization header should be specified"
date: 2013-02-09
comments: true
categories: [S3, Apache]
---
## 現象
ApacheからAmazon S3にmod_proxyでリクエストを送ったら、ステータスが400になり、
"Either the Signature query string parameter or the Authorization header should be specified, not both"というエラーメッセージが出てハマったときのメモです。

開発中で、Apacheの設定でBASIC認証をかけていました。

一方、S3では
[Signing and Authenticating REST Requests - Amazon Simple Storage Service](http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#ConstructingTheAuthenticationHeader)
にあるように

```
Authorization: AWS AWSAccessKeyId:Signature
```

というリクエストヘッダで認証情報を渡すか、
[Using Query String Authentication - Amazon Simple Storage Service](http://docs.aws.amazon.com/AmazonS3/latest/dev/S3_QSAuth.html)
にあるように

```
http://quotes.s3.amazonaws.com/nelson?AWSAccessKeyId=AKIAIOSFODNN7EXAMPLE&Expires=1177363698&Signature=vjSAMPLENmGa%2ByT272YEAiv4%3D
```

のようなクエリストリングで認証情報を渡すことができます。

ですが、BASIC認証を使っていると、
[Basic認証 - Wikipedia](http://ja.wikipedia.org/wiki/Basic%E8%AA%8D%E8%A8%BC)
にあるように

```
Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==
```

というようなヘッダがついてしまうため、S3用の認証情報をクエリストリングで指定していると上記のようなエラーになるというわけでした。


## 解決法
RequetHeader unset ヘッダ名で削除すればOKでした。

```
    <Location /some/path>
        RequestHeader unset Authorization
    </Location>
    ProxyRequests Off
    ProxyPassMatch ^/some/path/(.*)$ http://yourdomain.s3-ap-northeast-1.amazonaws.com/$1
```

注意するべきはLocationでS3にプロキシする範囲に限定する必要があるということです。Location無しだとS3にプロキシしないURLについてもAuthorizationヘッダが削除され、BASIC認証のログインダイアログが延々と出続けてしまいました。
