---
layout: post
title: "パスフレーズ無しの秘密鍵と自己証明書をコマンド一発で作る"
date: 2012-06-21
comments: true
categories: openssl
---

以下はワイルドカード証明書の例です。適宜変更して使います。
```
openssl req -new -newkey rsa:2048 -x509 -nodes -days 365 -set_serial 0 \
  -subj '/C=JP/ST=Kanagawa/L=Yokohama City/CN=*.example.com' \
  -out wildcard.example.com.crt -keyout wildcard.example.com.key
```

## 証明書の内容確認

```
# openssl x509 -in wildcard.example.com.crt -text
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 0 (0x0)
        Signature Algorithm: sha1WithRSAEncryption
        Issuer: C=JP, ST=Kanagawa, L=Yokohama City, CN=*.example.com
        Validity
            Not Before: Jun 21 10:52:07 2012 GMT
            Not After : Jun 21 10:52:07 2013 GMT
        Subject: C=JP, ST=Kanagawa, L=Yokohama City, CN=*.example.com
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                Public-Key: (512 bit)
                Modulus:
                    00:ba:ce:42:5a:26:10:97:8a:fa:e8:44:b6:d0:1a:
                    3c:4e:f6:80:7b:69:df:a7:cf:c1:64:26:79:0c:5e:
                    c9:2f:ba:03:08:d2:14:f8:f0:df:f6:bf:49:79:1e:
                    ec:6f:1b:04:79:65:c1:ba:14:7f:40:f7:52:bb:b8:
                    7d:f0:aa:fc:8d
                Exponent: 65537 (0x10001)
        X509v3 extensions:
            X509v3 Subject Key Identifier: 
                49:83:EC:88:55:ED:E3:1E:61:E9:12:B6:52:9E:63:6F:D9:03:88:41
            X509v3 Authority Key Identifier: 
                keyid:49:83:EC:88:55:ED:E3:1E:61:E9:12:B6:52:9E:63:6F:D9:03:88:41

            X509v3 Basic Constraints: 
                CA:TRUE
    Signature Algorithm: sha1WithRSAEncryption
        b9:92:5a:89:1e:9c:dc:fc:44:d3:55:10:06:af:43:e8:0d:30:
        4f:03:6c:10:c9:8e:68:16:28:7a:4c:a7:28:e8:73:04:c0:1b:
        ce:bd:82:e7:8f:d4:b9:0f:00:32:47:5a:d1:3e:65:01:3c:a9:
        23:e8:07:e0:03:48:24:dd:53:7c
-----BEGIN CERTIFICATE-----
MIIB3TCCAYegAwIBAgIBADANBgkqhkiG9w0BAQUFADBOMQswCQYDVQQGEwJKUDER
MA8GA1UECAwIS2FuYWdhd2ExFjAUBgNVBAcMDVlva29oYW1hIENpdHkxFDASBgNV
BAMMCyoubmFydWgubmV0MB4XDTEyMDYyMTEwNTIwN1oXDTEzMDYyMTEwNTIwN1ow
TjELMAkGA1UEBhMCSlAxETAPBgNVBAgMCEthbmFnYXdhMRYwFAYDVQQHDA1Zb2tv
aGFtYSBDaXR5MRQwEgYDVQQDDAsqLm5hcnVoLm5ldDBcMA0GCSqGSIb3DQEBAQUA
A0sAMEgCQQC6zkJaJhCXivroRLbQGjxO9oB7ad+nz8FkJnkMXskvugMI0hT48N/2
v0l5HuxvGwR5ZcG6FH9A91K7uH3wqvyNAgMBAAGjUDBOMB0GA1UdDgQWBBRJg+yI
Ve3jHmHpErZSnmNv2QOIQTAfBgNVHSMEGDAWgBRJg+yIVe3jHmHpErZSnmNv2QOI
QTAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA0EAuZJaiR6c3PxE01UQBq9D
6A0wTwNsEMmOaBYoekynKOhzBMAbzr2C54/UuQ8AMkda0T5lATypI+gH4ANIJN1T
fA==
-----END CERTIFICATE-----
```


## 参考

* [Certificate Management and Generation with OpenSSL](http://gagravarr.org/writing/openssl-certs/ca.shtml)
* [openssl コマンド](http://www.nina.jp/server/slackware/openssl/openssl-command.html)
