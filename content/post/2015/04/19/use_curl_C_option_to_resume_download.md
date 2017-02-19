Title: curlでダウンロードを中断後再開するときは-Cオプションが便利
Date: 2015-04-19 01:07
Category: blog
Tags: curl
Slug: 2015/04/19/use_curl_C_option_to_resume_download


ISOイメージのようなサイズが大きなファイルを `curl` でダウンロードしようとして途中で中断してしまって再開するときに、 `-C` オプションが便利だったのでメモ。

[curlのマニュアル](http://manpages.ubuntu.com/manpages/trusty/en/man1/curl.1.html)の `-C` オプションのところを見ると `-C オフセットのバイト数` のように指定するのですが `-C -` と書けば自動でファイルサイズを指定してくれることがわかりました。

例えば以下のようにダウンロードしようとして

```
curl -O ftp://ftp3.jp.freebsd.org/pub/FreeBSD/ISO-IMAGES-amd64/10.1/FreeBSD-10.1-RELEASE-amd64-disc1.iso.xz
```

途中でマシンをスリープしてしまったりして中断した時は、以下のコマンドで再開します。

```
curl -O -C - ftp://ftp3.jp.freebsd.org/pub/FreeBSD/ISO-IMAGES-amd64/10.1/FreeBSD-10.1-RELEASE-amd64-disc1.iso.xz
```
