Title: sleuthというGoのライブラリでサービスディスカバリを試してみた
Date: 2016-06-15 06:56
Category: blog
Tags: golang,service-discovery,sleuth
Slug: blog/2016/06/15/tried-service-discovery-with-sleuth

## はじめに
[Service autodiscovery in Go with sleuth - darian.af](http://darian.af/post/master-less-peer-to-peer-micro-service-autodiscovery-in-golang-with-sleuth/)という記事を見かけて試してみたのでメモです。

## github.com/ursiform/sleuthのセットアップ

[Installation](https://github.com/ursiform/sleuth#installation)を見ながらセットアップします。

いきなりgo getでインストールしてみるとZeroMQ version 4が必要というエラーメッセージが出ました。

```
$ go get -u github.com/ursiform/sleuth
# github.com/pebbe/zmq4
In file included from ../../../pebbe/zmq4/ctxoptions_unix.go:7:0:
zmq4.h:2:2: error: #error "You need ZeroMQ version 4 to build this"
 #error "You need ZeroMQ version 4 to build this"
  ^
```

Ubuntu 16.04では

```
sudo apt install -y libzmq3-dev
```

CentOS 7では

```
sudo yum install -y zeromq-devel
```

でZeroMQ 4.xのライブラリとヘッダファイルがインストールできます。

このあとで go get でsleuthをインストールすると今度は大丈夫でした。

```
$ go get -u github.com/ursiform/sleuth
```

## 動作確認のためエコーバックのサービスの例を試す

[Examples](https://github.com/ursiform/sleuth#examples)のExample (1)にエコーバックのサーバとクライアントがあるのでそれを試します。

コードをコピペするのが面倒な人は

```
go get -d github.com/hnakamur/sleuth-echo-example
```

で取得できます。

以下のコマンドでプロジェクトのディレクトリに移動します。

```
cd $GOPATH/src/github.com/hnakamur/sleuth-echo-example
```

以下のコマンドでエコーバックのサーバを起動します。

```
(cd echo-server && go run main.go &)
```

起動すると以下のようなログが出力されます。

```
2016/06/15 06:54:06 [**warning**] sleuth: config.Interface not defined [801]
2016/06/15 06:54:06 [ listening ] sleuth: [SLEUTH-v0:5670][echo-service E13055]
```

以下のコマンドでクライアントを実行し、"It works." と表示されれば成功です。

```
$ (cd echo-client && go run main.go)
It works.
```

curlでも試してみます。

```
$ curl -s -d Hello 127.0.0.1:9873/echo-service/
Hello
```

## サービスディスカバリの例を試す

```
go get -u github.com/afshin/sleuth-example/...
```

でサンプルのコードと依存するライブラリを取得し

```
cd $GOPATH/src/github.com/afshin/sleuth-example
```

でプロジェクトのディレクトリに移動します。

この例にはarticle-serviceとcomment-serviceという2つのサービスが含まれています。

まずは article-service を起動します。article-serviceはポート9872で起動されます。

```
$ (cd article-service && go run main.go)
2016/06/14 22:38:08 [**warning**] sleuth: config.Interface not defined [801]
2016/06/14 22:38:08 [ listening ] sleuth: [SLEUTH-v0:5670][client-only EC740A]
2016/06/14 22:38:08 [**blocked**] sleuth: waiting for client to find [comment-service]
```

ログに書かれているようにcomment-serviceが見つからなくて待っている状態です。

別の端末を開いて以下のコマンドを実行してcomment-serviceを起動します。comment-serviceはポート9871で起動されます。

```
$ (cd comment-service && go run main.go)
2016/06/15 07:47:42 [**warning**] sleuth: config.Interface not defined [801]
2016/06/15 07:47:42 [ listening ] sleuth: [SLEUTH-v0:5670][comment-service 0DBE04]
ready...
```

comment-serviceを起動するとarticle-serviceの端末には以下のログが追加で出力されます。

```
2016/06/15 07:47:43 [*unblocked*] sleuth: client found [comment-service]
ready...
```

つまりarticle-serviceがcomment-serviceを発見（サービスディカバリ）出来たということです。

別の端末を開いて以下のコマンドを実行してcurlでarticle-serviceから記事のデータを1件取得してみます。

```
$ curl -s localhost:9872/articles/049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d | jq .
{
  "success": true,
  "data": {
    "guid": "049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d",
    "byline": "Kristen Rasmussen",
    "headline": "Wanting the Unwanted: Why Eat Weeds",
    "url": "http://www.rootedfood.com/musings/2015/4/1/a-foraged-affair",
    "time": 1428168580
  }
}
```

comment-serviceからコメントのデータを1件取得します。

```
$ curl -s localhost:9871/comments/06500da3-f9b0-4731-b0fa-fbc6cbe8c155 | jq .
{
  "success": true,
  "data": [
    {
      "guid": "d7041752-6854-4b2c-ad6d-1b48d898668d",
      "article": "06500da3-f9b0-4731-b0fa-fbc6cbe8c155",
      "text": "Star Trek, on the other hand, consistently presents an optimistic view of our capacity for civilization. I love science-fiction, even when it&#x27;s dystopian. But why does so much of it have to be dystopian?",
      "time": 1452738329
    }
  ]
}
```

次に2つのサービスを連携させた使い方として、以下のコマンドで1件の記事とそれに紐づくコメントを取得します。

```
$ curl -s localhost:9872/articles/049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d?includecomments=true | jq .
{
  "success": true,
  "data": {
    "guid": "049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d",
    "byline": "Kristen Rasmussen",
    "comments": [
      {
        "guid": "1b1e937b-8521-4c88-a13c-105d421ea030",
        "article": "049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d",
        "text": "I believe the premise to be false, while it is true that you can eat many different &quot;weeds&quot; I cannot find any methodology or theory where that doing so increases the efficiency of land use. There are some key things like nutrients in == nutrie
nts out and digestibility in humans which is not a given.<p>That said, there were some interesting recipes for what are nominally weeds in the Foxfire[1], and Euell Gibbons books[2] which were certainly edible although nothing I&#x27;ve tried really struck me as excepti
onal. As Boy Scouts we got a merit badge for creating a meal out of locally harvested plants, that was fun.<p>[1] <a href=\"http:&#x2F;&#x2F;www.foxfire.org&#x2F;thefoxfirebooks.aspx\" rel=\"nofollow\">http:&#x2F;&#x2F;www.foxfire.org&#x2F;thefoxfirebooks.aspx</a><p>[2]
 <a href=\"http:&#x2F;&#x2F;www.amazon.com&#x2F;Euell-Gibbons-Handbook-Edible-Plants&#x2F;dp&#x2F;0915442787\" rel=\"nofollow\">http:&#x2F;&#x2F;www.amazon.com&#x2F;Euell-Gibbons-Handbook-Edible-Plants&#x2F;d...</a>",
        "time": 1428172888
      },
      {
        "guid": "1ffa59ea-1b62-41fe-87c3-98ec6901d768",
        "article": "049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d",
        "text": "Something to keep in mind here is that once a viable market is found then the product will be fully commercialised and mass-produced.  No longer will poor conditions be good enough when compared to the yield you get from ideal conditions.<p>Then we will
 start fertilising them, then tweaking the seeds etc etc etc. And before long it will be just like anything else grown on the land.",
        "time": 1428188859
      },
…(略)…
        "guid": "587b528f-f4fe-4620-959e-f0d087c97348",
        "article": "049cd8fc-a66b-4a3d-956b-7c2ab5fb9c5d",
        "text": "The premise that weeds are a suitable food for humans is wrong. Most of these plants are loaded with toxins. You can&#x27;t eat them in any quantity for calories without getting poisoned.<p>Cows and goats and sheep can eat these things, though, because 
they have more advanced digestive systems. The udder provides an added toxin filtration system.<p>In theory you might be able to design an efficient system to detoxify wild plants such as grass and weeds directly into a high quality human food. At this moment cheese is 
already an incredibly effective way to use wild forage to make human food.",
        "time": 1428192718
      }
    ],
    "headline": "Wanting the Unwanted: Why Eat Weeds",
    "url": "http://www.rootedfood.com/musings/2015/4/1/a-foraged-affair",
    "time": 1428168580
  }
}
```

## sleuthのQ & Aを見てみる

[Q & A](https://github.com/ursiform/sleuth#q--a)を見ると、sleuthのメッセージプロトコルはJSONをgzipしてHTTPで通信しているとのことです。Protocol Buffersなどの他のライブラリに依存するのを避けたいという意図で、マイクロサービスのAPIレスポンスのほとんどは小さいのでJSONをgzipする方式で十分だし、そのほうがGo以外の言語でも利用しやすいので良いだろうということです。

sleuthは熊のグループの集合名詞とのことです。

## おわりに
sleuthはzeromqとGoさえあれば使えるということでセットアップが簡単です。

サービスの実装[sleuth-example/main.go](https://github.com/afshin/sleuth-example/blob/master/article-service/main.go)と[sleuth-example/main.go](https://github.com/afshin/sleuth-example/blob/master/comment-service/main.go)も、Goで普通にウェブサービスを実装したところに、sleuthを使うためのコードを少し足すだけでいいのでお手軽でいいですね。
