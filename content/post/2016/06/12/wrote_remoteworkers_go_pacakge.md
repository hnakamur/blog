Title: Goで複数のリモートのワーカーにジョブを実行させるremoteworkersというパッケージを書いた
Date: 2016-06-12 21:53
Category: blog
Tags: golang,websocket
Slug: 2016/06/12/wrote_remoteworkers_go_pacakge

## なぜ書いたか
仕事で複数のサーバで同じ処理を実行して結果を集めたいというニーズがあって、各サーバをgRPCのサーバにするという実装でとりあえず実現していました。でも、出来れば処理を実行するワーカーサーバから制御サーバに接続して繋ぎっぱなしにしておいて、制御サーバからジョブを送り込む方式にしたいなーと思っていて、家で実装を進めていました。

## これまでに試したこと
gRPCに[Bidirectional streaming RPC](http://www.grpc.io/docs/tutorials/basic/go.html#bidirectional-streaming-rpc)というのがあったので、[hnakamur/grpc_notification_experiment](https://github.com/hnakamur/grpc_notification_experiment)で試してみたのですが、複数クライアントがサーバに接続した状態で、サーバからクライアントにジョブを投げても、1つのクライアントでしか処理が実行されないということがわかりました。

次に、ワーカーサーバから制御サーバにTCPのソケットで接続しておいて、制御サーバからワーカーサーバにジョブを投げて結果を集めるサンプルを書いてみました。
[hnakamur/tcp_pubsubreply_experiment](https://github.com/hnakamur/tcp_pubsubreply_experiment)

複数のワーカーに同じジョブを投げて結果を集めて、全てのワーカーからの結果が揃ったらクライアントに結果を返すというものです。 https://github.com/hnakamur/tcp_pubsubreply_experiment/blob/f9201c075661c5d58895f9a30b47f73f5c4cc13d/main.go#L167-L189 でジョブを各ワーカーのコネクションが持つチャンネルに送って、各ワーカーの結果を返すチャンネルから受け取るという素朴な実装になっています。

しかし、この実装では1つのジョブを実行中は他のジョブを実行できないという制限があります。また試しているとタイミングによっては期待通りの動きにならないことがありました。

## 今回の実装
実装は[hnakamur/remoteworkers](https://github.com/hnakamur/remoteworkers)で公開しています。使用例は[remoteworkers/example](https://github.com/hnakamur/remoteworkers/tree/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/example)、APIドキュメントは[remoteworkers - GoDoc](https://godoc.org/github.com/hnakamur/remoteworkers)を参照してください。

最初はWebSocketのライブラリ[github.com/gorilla/websocket](https://github.com/gorilla/websocket)の[examples](https://github.com/gorilla/websocket/tree/a68708917c6a4f06314ab4e52493cc61359c9d42/examples)のchatとechoのclientを組み合わせて改変していきました。chatは1つのクライアントからのメッセージを他のクライアントに送って終わりですが、今回はジョブを実行して結果を集めたいので、その処理を追加で実装しました。また、元のサンプルはグローバル変数や設定用の定数を使うようになっていたのでstructを定義してグローバル変数をやめて設定もstructのメンバーに持つようにしました。

ワーカーはサーバにwebsocketで接続しますが、クライアントは通常のhttpリクエストでジョブを投げてレスポンスで結果を受け取るようにしてみました。ワーカーとサーバの間のメッセージは[GoのMessagePackのライブラリのベンチマークをしてみた · hnakamur's blog at github](/blog/2016/06/04/benchmark_go_msgpack_libraries/)で試した[vmihailenco/msgpack](https://github.com/vmihailenco/msgpack)を使ってMessagePackでエンコード・デコードしています。

以下実装メモです。

### ConnとHub
サーバ側のメインの処理は、サーバとワーカーのコネクションを扱う[Conn](https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/conn.go)と複数のConnの間を取り持つ[Hub](https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/hub.go)が担当しています。

### 読み取りと書き出しでgoroutineを分ける
上記の[hnakamur/tcp_pubsubreply_experiment](https://github.com/hnakamur/tcp_pubsubreply_experiment)では、ワーカーとサーバ間のTCPコネクション1つのに対して1つgoroutineを作ってデータの読み書きをしていました。

一方、[github.com/gorilla/websocketのAPIドキュメント](https://godoc.org/github.com/gorilla/websocket)の[Concurrency](https://godoc.org/github.com/gorilla/websocket#hdr-Concurrency)にコネクションは1つのコンカレントなリーダーと1つのコンカレントなライターをサポートすると書いてあります。

chatのexampleを見ると[Conn.readPump()](https://github.com/gorilla/websocket/blob/a68708917c6a4f06314ab4e52493cc61359c9d42/examples/chat/conn.go#L50-L69)で読み取り処理のループ、[Conn.writePump()](https://github.com/gorilla/websocket/blob/a68708917c6a4f06314ab4e52493cc61359c9d42/examples/chat/conn.go#L78-L116)で書き出し処理のループを実装していて https://github.com/gorilla/websocket/blob/a68708917c6a4f06314ab4e52493cc61359c9d42/examples/chat/conn.go#L127-L128 でgoroutineを使って並行(concurrent)に実行しています。

この方式により上記の[Concurrency](https://godoc.org/github.com/gorilla/websocket#hdr-Concurrency)の1つのコネクションに1つのコンカレントなリーダーと1つのコンカレントなライターという条件を自動的に満たすことが出来ます。

さらに、ワーカーでのジョブの実行も https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/worker.go#L200-L214 のように別のgoroutineで実行するようにしました。読み取りと書き出しのgoroutineを分け、ジョブ実行のgoroutineも別にしたことで、ワーカーでジョブを実行中でも別のジョブを受け取って実行することが出来るようになりました。

### ジョブのディスパッチと結果の収集
各ワーカーからにジョブを投げて結果を集める部分も https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/hub.go#L139-L171 のように書くことで、複数のジョブを並行で実行できるようになっています。

例えば、あるジョブを依頼されてそれの結果が集まる前に、次のジョブを受け取ってそちらの結果が先に集まった場合はそちらを先に返すことができます。

### 自動で再接続
ワーカーとの接続が切れた場合は、残ったワーカーだけで処理を実行する仕様としました。ジョブを受け取った時にワーカーが1つもいない場合はエラーとしています。また、ワーカーからサーバへの接続が切れた場合は1秒待って再起動を無限に繰り替えすようにしています。時間は設定で変更可能です。ただし、だんだん間隔を開けるといったことは出来ないのでその場合はフォークして改変してください。

### 返信用のチャンネルを渡して実行
サーバとワーカのコネクションをHubに登録する箇所 https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/conn.go#L86-L92 とクライアントから依頼されたジョブをHubに投げて全ワーカーからの結果を受け取る箇所 https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/hub.go#L194-L203 では、結果を受け取るためのチャンネルをHubへのチャンネルに渡して実行するという方法を取りました。

これによってHubとのやり取りは全てチャンネル経由になりシンプルになりました。さらに関数の中に閉じ込めることで、ライブラリの利用者はチャンネルを意識することなく単なる関数呼び出しで使えるようになっています。

### ジョブのエンコード・デコード

まずクライアントではジョブをJSONでエンコードしています。
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/example/client/client.go#L25-L30

サーバでは受け取ったジョブをJSONでデコードします。
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/example/server/main.go#L52-L54

その後[Hub.RequestWork()](https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/hub.go#L193-L205)でHubにジョブが渡されて
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/hub.go#L142
でMessagePackでエンコードしてワーカーに送ります。

ワーカーでは
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/worker.go#L187-L188
で受け取ったジョブをMessagePackでデコードします。

ワーカーでジョブを受け取って処理する部分は
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/example/worker/main.go#L47-L58
です。[vmihailenco/msgpack](https://github.com/vmihailenco/msgpack)で `map[string]string` 型をエンコードしてデコードすると `map[interface{}]interface{}` になったので[type assertion](https://golang.org/ref/spec#Type_assertions)を使って参照する必要がありました。

### 結果のエンコード・デコード
ワーカーでの結果は
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/worker.go#L202-L206
でMessagePackにエンコードしています。

サーバでは
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/conn.go#L148-L163
で結果をMessagePackでデコードしてHubに送っています。

Hubでは
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/hub.go#L165-L171
で1つのワーカーからの結果を受け取り、全てのワーカーからの結果が揃ったらクライアントへ返信するためのチャンネルに集めた結果を送ります。

サーバでは
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/example/server/main.go#L28-L39
で集めた結果の構造を変形し、
https://github.com/hnakamur/remoteworkers/blob/0ee6c4fa0ffe12af7ff6e7aefd5e3f0ebe042e31/example/server/main.go#L69-L70
でJSONにエンコードしています。

### TCPソケットからWebSocketにして良かったところ

ワーカーからサーバに接続したときにワーカーのIDを登録しているのですが、TCPソケットのときはそのためにワーカーから登録用のメッセージを送って成功失敗の結果を送る必要がありました。一方WebSocketではエンドポイントに接続するときにリクエストヘッダで追加の情報を送れるので `X-Worker-ID` と言うヘッダ名でワーカーIDを送るようにしました。

また、TCPソケットだと1つのポートでクライアントとワーカーからの通信を受ける場合はメッセージの内容で区別がつくようにしておく必要があります。WebSocketの場合は1つのポートでもURLのPathを別にするという手が使えるので楽です。しかも今回のようにワーカーはWebSocketで接続し、クライアントはhttpで接続ということも出来て便利です。

## おわりに
当初やりたいと思っていたことがようやく実現できました。しかも、これだけ並列性が高いプログラムなのにgoroutineとchannelのおかげですっきりシンプルなコードで実装出来ています。これなら保守や改変もしやすくて助かります。やっぱりGoは素晴らしいです！
