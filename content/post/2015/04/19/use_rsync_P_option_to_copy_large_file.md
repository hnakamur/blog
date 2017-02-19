Title: サイズが大きなファイルのコピーにはrsyncの-Pオプションが便利
Date: 2015-04-19 00:56
Category: blog
Tags: rsync
Slug: 2015/04/19/use_rsync_P_option_to_copy_large_file


Vagrantの自作boxファイルをインターネット上のサーバにアップロードするときなどに、 `rsync` の `-P` オプションが便利だったのでメモ。

[rsyncのマニュアル](http://manpages.ubuntu.com/manpages/utopic/en/man1/rsync.1.html) によると `-P` オプションは `--partial --progress` と同じとのこと。

`--progress` を指定されると以下の実行例のように、コピー中に進捗状況が表示され、完了した時に結果情報が出力されます。


```
$ rsync -P freebsd-10.1-amd64.box hoge
freebsd-10.1-amd64.box
   449371583 100%  112.62MB/s    0:00:03 (xfer#1, to-check=0/1)

sent 449426538 bytes  received 42 bytes  99872573.33 bytes/sec
total size is 449371583  speedup is 1.00
```

`--partial` を指定するとコピーが中断されてしまっても、コピーしかけのファイルが消されないので、再度実行すると続きからコピーを再開できます。
