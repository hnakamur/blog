Title: node-http-proxyでバーチャルホストで振り分けつつhttp/https->websocketリバースプロキシの実験
Date: 2012-06-27 00:00
Category: blog
Tags: node.js websocket proxy
Slug: blog/2012/06/27/node-http-proxydebatiyaruhosutodezhen-rifen-ketutuhttp-slash-https->websocketribasupurokisifalseshi-yan

以下の2つのページを参考に、node-http-proxyでバーチャルホストで振り分けつつ
http/httpsからwebsocketにリバースプロキシする実験をしてみました。
環境はCentOS 6.2です。ソースは[hnakamur/node-http-proxy-websocket-sample](https://github.com/hnakamur/node-http-proxy-websocket-sample)にあります。

* [５分くらいで出来るnode.js(0.6) + socket.io(0.8x)のサンプルプログラム - 大人になったら肺呼吸](http://d.hatena.ne.jp/replication/20111108/1320762287)
* [nodejitsu/node-http-proxy](https://github.com/nodejitsu/node-http-proxy)


<pre>
                              +---------------+
                       +------+ VHost1App/app |
                       |      | port 3000     |
 +--------------+      |      +---------------+
-+ proxy-vhost  +------+
 | port 80, 443 |      |      +---------------+
 +--------------+      +------+ VHost2App/app |
                              | port 3001     |
                              +---------------+
</pre>

上記の構成で、
vhost1.example.comというホスト名でアクセスしたらVHost1/app、
vhost2.example.comというホスト名でアクセスしたらVHost2/app
にリバースプロキシするようにします。
\*.example.comというワイルドカードの自己証明書でproxy-vhostにてSSLを処理します。


## 実行手順

### 自己証明書とパスフレーズ無しの秘密鍵を生成。

以下、ドメインexample.comの部分は適宜変更してください。

```
openssl req -new -newkey rsa:2048 -x509 -nodes -days 365 -set_serial 0 \
  -subj '/C=JP/ST=Kanagawa/L=Yokohama City/CN=*.example.com' \
  -out /etc/pki/tls/certs/wildcard.example.com.crt \
  -keyout /etc/pki/tls/private/wildcard.example.com.key
```

### nodeモジュールインストール

私の環境では/usr/local/node-v0.6.19にnode.jsをインストールしているのでPATHを通してから実行します。
```
export PATH=/usr/local/node-v0.6.19/bin:$PATH
```

```
npm install socket.io -g
npm install express@2.5.10 -g
npm install ejs -g
npm install http-proxy -g
```
なお、モジュールをグルーバルにインストールしているのは[hnakamur/node-http-proxy-websocket-sample](https://github.com/hnakamur/node-http-proxy-websocket-sample)にモジュールを含めたくないからで、実際はローカルにインストールしても構いません。

### サーバ起動

私の環境では/usr/local/node-v0.6.19にnode.jsをインストールしているのでNODE_PATHを通してから実行します。
```
export NODE_PATH=/usr/local/node-v0.6.19/lib/node_modules
```

```
node VHost1App/app &
node VHost2App/app &
node proxy-vhost &
```


### ローカルマシンの/etc/hostsに以下のエントリ追加

IPアドレスは実際のサーバに合わせて変更してください。

```
192.0.2.2 vhost1.example.com vhost2.example.com
```

### ブラウザでアクセス

https://vhost1.example.com/
や
https://vhost2.example.com/
にアクセスします。自己証明書なのでエラーになりますが受け入れて進んでください。
バーチャルホスト毎にそれぞれ内容が異なることを確認します。
