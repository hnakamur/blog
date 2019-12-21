---
layout: post
title: "daemontoolsの使い方"
date: 2012-06-21
comments: true
categories: [daemontools, CentOS]
---
[daemontoolsを使う | Netsphere Laboratories](http://www.nslabs.jp/daemontools.rhtml)を参考にしました。ありがとうございます。

## 私的ルール

### 無効化したサービスは/service/.disabled/に移動
/service/以下に.で始まるフォルダ名にすると無視されるということですが、my_service_nameを.my_service_nameと変えるのはタイプが面倒なので、/service/.disabledというフォルダを作って無効化するときはその下に移動することにしました。

### 作業するときは/serviceに移動
svcやsvstatにフルパスを指定しても動くのですが、/service/と/service/.disabled間で移動するときにタイプ量が増えるので、最初にcd /serviceしてから作業することにしました。


## 手順
### サービス追加
node-virtualhost1.example.comという名前でサービスを追加する例。
exec -cの後はサービスに応じて変更します。

```
cd /service
mkdir -p .disabled/node-virtualhost1.example.com
cat <<EOF > .disabled/node-virtualhost1.example.com/run
#!/bin/sh
exec -c /usr/local/node-v0.6.19/bin/node /var/www/app/virtualhost1.example.com/hello.js
EOF
chmod 755 .disabled/node-virtualhost1.example.com/run
```

### サービス有効化

```
cd /service
mv .disabled/node-virtualhost1.example.com .
```

#### 状態確認
```
# svstat node-virtualhost1.example.com/
node-virtualhost1.example.com/: up (pid 1493) 3 seconds
```

### サービス無効化

```
cd /service
mv node-virtualhost1.example.com .disabled/
svc -tx .disabled/node-virtualhost1.example.com
```

#### 状態確認
```
# svstat .disabled/node-virtualhost1.example.com/
.disabled/node-virtualhost1.example.com/: supervise not running
```

### サービス一時停止(Down)

```
cd /service
svc -d node-virtualhost1.example.com
```

#### 状態確認
```
# svstat node-virtualhost1.example.com/
node-virtualhost1.example.com/: down 1 seconds, normally up
```

### サービス一時停止からの再開(Up)
```
cd /service
svc -u node-virtualhost1.example.com
```

#### 状態確認
```
# svstat node-virtualhost1.example.com/
node-virtualhost1.example.com/: up (pid 1512) 1 seconds
```

