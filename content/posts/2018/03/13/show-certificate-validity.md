+++
title="特定のドメインの証明書の有効期限をコマンドで確認する"
date = "2018-03-13T11:40:00+09:00"
tags = ["https"]
categories = ["blog"]
+++


職場で見かけたので、ちょっとアレンジしてメモ。

```console
openssl s_client -connect example.com:443 -showcerts < /dev/null 2> /dev/null \
   | openssl x509 -text | grep -A 2 Validity
```

実行例。

```console
$ openssl s_client -connect example.com:443 -showcerts < /dev/null 2> /dev/null | openssl x509 -text | grep -A 2 Validity
        Validity
            Not Before: Nov  3 00:00:00 2015 GMT
            Not After : Nov 28 12:00:00 2018 GMT
