---
layout: post
title: "mod_xsendfileでダウンロード後にサーバ上のファイル自動削除"
date: 2012-03-03 20:26
comments: true
categories: [Apache, PHP, Linux]
---

[mod_xsendfile](https://tn123.org/mod_xsendfile/)のホームページ上でリリースされているバージョン0.12には含まれていませんが、[Githubのレポジトリのソース](https://github.com/nmaier/mod_xsendfile/commit/f6b853ce0e555b61f83f928d9f927349346018b4)ではX-Sendfile-Temporaryという拡張ヘッダに対応しています。

Scientific Linux 6.1で実験しました。

## mod_xsendfileのインストール

以下の手順でインストールします。
``` bash
yum install -y httpd-devel
git clone https://github.com/nmaier/mod_xsendfile.git
cd mod_xsendfile
apxs -cia mod_xsendfile.c
```

実験スクリプト用にApacheの設定ファイルを作成します。
``` text /etc/httpd/conf.d/xsendfile_test.conf
<Directory /var/www/html/xsendfile>
    XSendFilePath /var/www/html/xsendfile/data AllowFileDelete
    <Files out.php>
      XSendFile on
    </Files>
</Directory>
```

Apache再起動。
``` bash
/etc/init.d/httpd graceful
```

## 実験

実験スクリプト用のフォルダを作ります。
``` bash
mkdir /var/www/html/xsendfile/data/
chown -R apache:apache /var/www/html/xsendfile
```

実験用のPHPスクリプトを作成します。
``` php /var/www/html/xsendfile/out.php
<?php
$path = '/var/www/html/xsendfile/data/file1.txt';
$fname = basename($path);
header("X-Sendfile-Temporary: $path");
header("Content-Type: application/octet-stream");
header("Content-Disposition: attachment; filename=\"$fname\"");
```

実験用のダウンロードファイルを作成します。
``` text /var/www/html/xsendfile/data/file1.txt
Hello, X-Sendfile-Temporary!
```

これで、ブラウザで http://your_host_here/xsendfile/out.php を開くとダウンロード後にサーバ上のファイルが削除されました。

## 今回のはまりポイント

``` text /etc/httpd/conf.d/xsendfile_test.conf
<Directory /var/www/html/xsendfile>
    XSendFilePath /var/www/html/xsendfile/data
    <Files out.php>
      XSendFile on
    </Files>
</Directory>
```
のようにAllowFileDeleteを忘れていたら、out.phpを開いた時に404 Not Foundエラーになり、Apacheのエラーログには以下のようなエラーが出ていました。
``` text /var/log/httpd/error_log
[Sat Mar 03 15:57:07 2012] [error] [client 192.168.11.3] (14)Bad address: xsendfile: cannot open file: (null)
```
AllowFileDeleteをつければOKでした。
