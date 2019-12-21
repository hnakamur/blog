+++
title="グレースフルリスタートを支援するサーバ起動のGoライブラリを自作した"
date = "2017-07-08T21:25:00+09:00"
tags = ["go", "graceful-restart"]
categories = ["blog"]
+++


## はじめに

サーバプロセスを無停止で実行ファイルを更新し再起動できるグレースフルリスタートは
非常に便利な仕組みです。

今までは [Go言語でGraceful Restartをする - Shogo's Blog](https://shogo82148.github.io/blog/2015/05/03/golang-graceful-restart/) と一連の記事を参考に
[lestrrat/go-server-starter: Go port of start_server utility (Server::Starter)](https://github.com/lestrrat/go-server-starter) を使わせていただいていました。
ありがとうございます！

今回自分好みの構成にするためにサーバ起動のGoライブラリを自作してみたのでメモです。

検証環境は以下の通りです。

```console
$ go version
go version go1.9beta2 linux/amd64
$ grep ^VERSION= /etc/os-release
VERSION="16.04.2 LTS (Xenial Xerus)"
```

## 使ってみた既存のライブラリ

### github.com/lestrrat/go-server-starter

`github.com/lestrrat/go-server-starter` パッケージは Perl の `Server::Starter - a superdaemon for hot-deploying server programs - metacpan.org](https://metacpan.org/pod/Server::Starter) と互換性があり、 drop-in replacement として使えることを目的として開発されています。

`github.com/lestrrat/go-server-starter` パッケージでは
`start_server` という実行ファイルを提供しています。

まず自分のサーバプログラムを `github.com/lestrrat/go-server-starter/listener` パッケージのAPIを使って `start_server` からリスナーの情報を受け取るように改変します。

そして自分のサーバプロセスを起動するコマンドラインを `start_server` への起動引数で指定して起動するという仕組みになっています。

プロセスの親子関係は以下の図の通りです。

```text
start_server
 \_ 自分のサーバプロセス
```

`start_server` が `SIGHUP` のシグナルを受け取ると、まず新しいサーバプロセスを起動します。これ以降新しくリクエストが来たときは、新サーバプロセスで処理されます。

```text
start_server
 \_ 旧サーバプロセス
 \_ 新サーバプロセス
```

その後 `start_server` が旧サーバプロセスに `SIGTERM` を送り、旧サーバプロセスはそれを受け取って自分を終了させます。

この時いきなり終了するのではなく、クライアントのリクエストを処理中の場合はレスポンスを返して処理を完了してから終了するというグレースフルシャットダウンを行うようにすれば、グレースフルリスタートが実現できるというわけです。

この点は以下に説明する `github.com/facebookgo/grace` や今回自作したライブラリも同じです。つまりグレースフルリスタートはライブラリ側だけで実現できるものではなく、
サーバプロセス側でグレースフルシャットダウンを実装することが必須となります。
そこで、この記事の件名も「グレースフルリスタートを支援する」という言い方にしました。

```text
start_server
 \_ 新サーバプロセス
```

### github.com/facebookgo/grace

一方 [facebookgo/grace: Graceful restart & zero downtime deploy for Go servers.](https://github.com/facebookgo/grace/) は外部のプログラムは使わない仕組みになっています。

また自分のサーバプログラムの改修も
[net/http.Server](https://golang.org/pkg/net/http/#Server)
の
[func (*Server) ListenAndServe](https://golang.org/pkg/net/http/#Server.ListenAndServe) 、
[func (*Server) ListenAndServeTLS](https://golang.org/pkg/net/http/#Server.ListenAndServeTLS) 、
[func (*Server) Serve](https://golang.org/pkg/net/http/#Server.Serve)
を呼ぶところを
[github.com/facebookgo/grace/gracehttp](https://godoc.org/github.com/facebookgo/grace/gracehttp) の
[func Serve(servers ...*http.Server) error](https://godoc.org/github.com/facebookgo/grace/gracehttp#Serve) を使うように改変するだけです。

このように手軽に使えるのが魅力です。

プロセス構成は普段は自分のサーバプロセスが単体で存在するようになっています。

```console
自分のサーバプロセス
```

`SIGUSR2` を受け取ると新しいサーバプロセスを子プロセスとして起動します。

```console
旧サーバプロセス
 \_ 新サーバプロセス
```

新サーバプロセスは起動すると `SIGTERM` を親である旧サーバプロセスに送り、旧サーバプロセスはそれを受け取って終了します。その結果新サーバプロセスだけが残ります。

```console
新サーバプロセス
```

つまり元のプロセスIDとは異なるプロセスIDを持つプロセスだけが残ることになります。
この方式だと [daemontools](http://cr.yp.to/daemontools.html) や
Pythonの [Supervisor](http://supervisord.org/) から使えなくて困りそうです。

ただ、私個人は [systemd](https://www.freedesktop.org/wiki/Software/systemd/) から使えれば困らないので、この点は特に気にしていませんでした。

しかし、
[Go1.8のGraceful Shutdownとgo-gracedownの対応 - Shogo's Blog](https://shogo82148.github.io/blog/2017/01/21/golang-1-dot-8-graceful-shutdown/)
のベンチマークソフトを試してみるとHTTP/1.1のときは取りこぼし無しで良いのですが、 HTTP/2 のグレースフルスタートを試してみると取りこぼしがばんばん発生することがわかりました。


## 自作ライブラリ

ということで `github.com/facebookgo/grace/gracehttp` を改変してプルリクエストを送ろうかと思ったのですが、作っているうちにプロセス構成やAPIも全く違うものになったので別物のライブラリとして自作することにしました。

自作と言っても、肝となるコードは `facebookgo/grace` からコピーし、自分が使いたい構成のAPIに変更しつつ、必要な処理を少し追加で実装しただけです。

Linux用の `syscall` パッケージの関数を使いまくっているので動作環境はLinuxのみです。

[github.com/hnakamur/serverstarter](https://github.com/hnakamur/serverstarter) で公開しています。

### プロセス構成

プロセス構成は以下のようになっています。サーバプログラムを起動した直後はマスタープロセスだけがある状態ですが、マスタープロセスはポートのリッスンを行った後ワーカープロセスを起動します。

```console
マスタープロセス
 \_ ワーカープロセス
```

マスタープロセスが `SIGHUP` を受け取ると新しいワーカープロセスを起動します。

```console
マスタープロセス
 \_ 旧ワーカープロセス
 \_ 新ワーカープロセス
```

その後、マスタープロセスが旧ワーカープロセスに `SIGTERM` を送ると旧ワーカープロセスが自分を終了します。

```console
マスタープロセス
 \_ 新ワーカープロセス
```

### シンプルなコード例

このライブラリを使うには自分のサーバプログラムに組み込んで以下のような構成にします。

```go {linenos=table}
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/hnakamur/serverstarter"
)

func main() {
	addr := flag.String("addr", ":8080", "server listen address")
	flag.Parse()

	starter := serverstarter.New()
	if starter.IsMaster() {
		l, err := net.Listen("tcp", *addr)
		if err != nil {
			log.Fatalf("failed to listen %s; %v", *addr, err)
		}
		if err = starter.RunMaster(l); err != nil {
			log.Fatalf("failed to run master; %v", err)
		}
		return
	}

	listeners, err := starter.Listeners()
	if err != nil {
		log.Fatalf("failed to get listeners; %v", err)
	}
	l := listeners[0]

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "from pid %d.\n", os.Getpid())
	})
	srv := &http.Server{}
	go func() { srv.Serve(l) }()

	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGTERM)
	for {
		if <-sigC == syscall.SIGTERM {
			srv.Shutdown(context.Background())
			return
		}
	}
}
```

- 21行目で `serverstarter.New()` で `Starter](https://godoc.org/github.com/hnakamur/serverstarter#Starter) のインスタンスを作ります。
- 21～31行目がマスタープロセスの場合の処理です。

  * 23行目でポートのリッスンを行います。
  * 27行目でワーカープロセスを起動し、シグナルを受け取るループに入ります。

- 33行目以降がワーカープロセスの場合の処理です。

  * 33行目で `starter.Listeners()` でリスナー一覧を受け取り、43行目でそのリスナーを使って `net/http.Server` の `func (srv *Server) Serve(l net.Listener) error` メソッドを呼び出してサービスのループをgoroutineで起動しています。

上記の「Go1.8のGraceful Shutdownとgo-gracedownの対応 - Shogo's Blog」の記事によると

- `net/http.Server` の `Serve` メソッドは **シャットダウンが始まるとすぐ制御を返す**
- `net/http.Server` の `Shutdown` メソッドは **シャットダウンが終わるまで待つ**

とのことなので、グレースフルシャットダウンの完了を待つには、シグナル待ちのループと `Shutdown` を呼ぶ処理をメインで行い、 `Serve` の実行はgoroutineで行う構成にするのがポイントとなります。

`facebookgo/grace` よりはコード量が増えますが、マスタープロセスでの処理とワーカープロセスでの処理が目に見える形で明示的に書かれるので、何をやっているかはこちらのほうがわかりやすいと個人的には考えています。

### より複雑な例

より複雑な例を `github.com/hnakamur/servestarter` の `examples` ディレクトリに置いています。

サンプルサーバ
[examples/graceserver/main.go](https://github.com/hnakamur/serverstarter/blob/bf52ea60200f0d9c69be75b8b87180797df7af1d/examples/graceserver/main.go)
ではHTTP/1.1とHTTP/2のポートを片方または両方リッスンできるようにしています。

最初は HTTP/1.1とHTTP/2で別々に `net/http.Server` のインスタンスを作って、グレースフルシャットダウンのときは両方に `Shutdown` をgoroutineと `sync.WaitGroup` で並列に呼び出すようにしてみました。が、HTTP/2でグレースフルリスタートを試すと取りこぼしが発生してしまいました。

そこで、 `net/http.Server` のインスタンスを1つにして、別々のgoroutineでHTTP/1.1とHTTP/2のリスナーに対して `Server` を呼ぶようにし、グレースフルシャットダウンのときはその1つの `Server` に対して `Shutdown` を呼ぶという構成にしてみたらHTTP/2のグレースフルリスタートでも取りこぼしがなくなりました。

本題から外れますが、SSL自己証明書を作成するコードは
[Golang : Create x509 certificate, private and public keys](https://www.socketloop.com/tutorials/golang-create-x509-certificate-private-and-public-keys)
を参考にして、RSAではなくECDSAを使うように改変してみました。

ベンチマーククライアント
[examples/h2bench/main.go](https://github.com/hnakamur/serverstarter/blob/bf52ea60200f0d9c69be75b8b87180797df7af1d/examples/h2bench/main.go)
は「Go1.8のGraceful Shutdownとgo-gracedownの対応 - Shogo's Blog」の記事にあったコードそのままです。

試す手順は [A more advanced example](https://github.com/hnakamur/serverstarter#a-more-advanced-example) を参照してください。

実際試してみた結果、HTTP/1.1とHTTP/2のポートの両方をリッスンした状態で毎秒グレースフルリスタートをかけつつ、HTTP/1.1、HTTP/2のどちらのポートにベンチマーククライアントでアクセスをかけても取りこぼしは起きませんでした。

また、毎秒グレースフルリスタートをかけた状態で、元とは違う内容のレスポンスを返すようにサーバのコードを書き換えて `go build -race` で実行ファイルを置き換える試験もしてみましたが、この場合も取りこぼし無しで置き換えが出来ました。

またその際以下のコマンドでマスタープロセスとワーカープロセスのプロセスIDも見てみました。

```console
watch -n 0.1 "ps alwwf | grep -E '(^F|[.]/graceserver)'"
```

以下に出力例を示します。

```console
Every 0.1s: ps alwwf | grep -E '(^F|[.]/graceserver)'       Sat Jul  8 23:38:53 2017

F   UID   PID  PPID PRI  NI    VSZ   RSS WCHAN  STAT TTY        TIME COMMAND
0  1000 31459 17608  20   0 387856 29556 futex_ Sl+  pts/14     0:00  \_ ./graceserver -http=:9090 -https=:9443 -sleep=2s
0  1000  6646 31459  20   0 403468 32900 futex_ Sl+  pts/14     0:00      \_ ./graceserver -http=:9090 -https=:9443 -sleep=2s
0  1000  6720 31459  20   0 190296 29608 futex_ Sl+  pts/14     0:00      \_ ./graceserver -http=:9090 -https=:9443 -sleep=2s
```

グレースフルリスタートの度にワーカープロセスは新しく作られてプロセスIDが変わっていきますが、マスタープロセスのプロセスIDは同じままであることも確認できました。

## おわりに

例によって雰囲気で書いてみただけなので、タイミングによってちゃんと動かないなどの落とし穴が残っている可能性はありますが、とりあえず希望通りの動きにはなっています。
また、 `go build -race` つきでビルドして動作確認しましたが datarace は報告されていないので、その点もとりあえずは大丈夫そうです。

ということで自分好みのライブラリが作れたので今後使っていこうと思います。
