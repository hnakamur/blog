---
layout: post
title: "node.jsのfs.watch()で設定ファイルが更新されたらリロード"
date: 2012-06-27
comments: true
categories: node.js
---
[javascript - Auto-reload of files in Node.js - Stack Overflow](http://stackoverflow.com/questions/1972242/auto-reload-of-files-in-node-js)によると、モジュールをリロードするには[isaacs/node-supervisor](https://github.com/isaacs/node-supervisor)がよさそうです。

が、今回は設定ファイルのリロードなのでfs.watch(filename, [options], [listener]) で十分ということで試してみました。
[File System Node.js v0.8.0 Manual & Documentation](http://nodejs.org/api/fs.html#fs_fs_watch_filename_options_listener)
によると環境によっては使えないそうなので注意が必要です。

CentOS 6.2では使えました。

watch.js
```
var fs = require('fs');
fs.watch('router.json', function(ev, filename) {
  if (filename) {
    fs.readFile(filename, function(err, data) {
      if (err) throw err;
      var router = JSON.parse(data);
      console.log(router);
    });
  }
});
```

router.json
```
{
  "vhost1.example.com": "127.0.0.1:3000",
  "vhost2.example.com": "127.0.0.1:3001",
  "vhost3.example.com": "127.0.0.1:3002",
  "vhost4.example.com": "127.0.0.1:3003"
}
```

```
node watch
```
で起動して
```
touch router.json
```
を実行すると
```
{ 'vhost1.example.com': '127.0.0.1:3000',
  'vhost2.example.com': '127.0.0.1:3001',
  'vhost3.example.com': '127.0.0.1:3002',
  'vhost4.example.com': '127.0.0.1:3003' }
```
と出力されます。

ただし、vimでrouter.jsonを開いて:wで保存すると下記のエラーでnodeが異常終了してしまいました。
```
/var/www/app/watch-sample/watch.js:6
      if (err) throw err;
                     ^
Error: ENOENT, open 'router.json'
```

```
node watch
```
再起動後、vimでrouter.jsonを開いて:wqで保存して終了すると異常終了はしませんでしたが、下記のようにコールバックが4回も呼び出されてしまいました。
```
{ 'vhost1.example.com': '127.0.0.1:3000',
  'vhost2.example.com': '127.0.0.1:3001',
  'vhost3.example.com': '127.0.0.1:3002',
  'vhost4.example.com': '127.0.0.1:3003' }
{ 'vhost1.example.com': '127.0.0.1:3000',
  'vhost2.example.com': '127.0.0.1:3001',
  'vhost3.example.com': '127.0.0.1:3002',
  'vhost4.example.com': '127.0.0.1:3003' }
{ 'vhost1.example.com': '127.0.0.1:3000',
  'vhost2.example.com': '127.0.0.1:3001',
  'vhost3.example.com': '127.0.0.1:3002',
  'vhost4.example.com': '127.0.0.1:3003' }
{ 'vhost1.example.com': '127.0.0.1:3000',
  'vhost2.example.com': '127.0.0.1:3001',
  'vhost3.example.com': '127.0.0.1:3002',
  'vhost4.example.com': '127.0.0.1:3003' }
```
実用するには前回の設定内容と比較して変わっている場合だけ処理するとか、設定ファイルを直接見るのではなく更新完了通知用の専用ファイルを用意してそちらをtouchするとか、何らかの対処が必要そうです。
