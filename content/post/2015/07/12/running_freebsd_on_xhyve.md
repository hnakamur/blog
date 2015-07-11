+++
Categories = []
Description = ""
Tags = ["xhyve", "freebsd"]
date = "2015-07-12T06:34:46+09:00"
title = "xhyveでFreeBSDを動かしてみた"

+++
下記の記事を参考に動かしただけですが、後々使うときに手順を忘れているはずなのでメモ。

* [xhyve で FreeBSD を動かしてみた - blog.holidayworking.org](http://blog.holidayworking.org/entry/2015/06/27/xhyve_%E3%81%A7_FreeBSD_%E3%82%92%E5%8B%95%E3%81%8B%E3%81%97%E3%81%A6%E3%81%BF%E3%81%9F)
* [FreeBSD on xhyve でディスクをマウントすることができた - blog.holidayworking.org](http://blog.holidayworking.org/entry/2015/07/05/FreeBSD_on_xhyve_%E3%81%A7%E3%83%87%E3%82%A3%E3%82%B9%E3%82%AF%E3%82%92%E3%83%9E%E3%82%A6%E3%83%B3%E3%83%88%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%9F)

なお、FreeBSD対応のプルリクエストは既に本家のmasterにマージ済みです。
また、今回使ったスクリプトは [hnakamur/xhyveのadd_scripts_for_freebsdブランチ](https://github.com/hnakamur/xhyve/tree/add_scripts_for_freebsd) に上げています。

## FreeBSDのVMイメージダウンロードと解凍

```
./download_freebsd_image.sh
```

FreeBSD-10.1-RELEASE-amd64.raw.xzを取得、解凍します。解凍後のファイルサイズは約21GBです。


## FreeBSDのVM起動

```
./xhyverun-freebsd.sh
```

起動したら、IDはroot、パスワード無しでログインできます。


## FreeBSDのVM停止

VM内で以下のコマンドを実行するとVMをシャットダウンしてホストOSであるOSXのシェルプロンプトに戻ります。

```
shutdown -p now
```
