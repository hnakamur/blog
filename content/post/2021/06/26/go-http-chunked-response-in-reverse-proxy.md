---
title: "GoのHTTPリバースプロキシーでのchunkedレスポンス"
date: 2021-06-26T16:55:00+09:00
---

## HTTPサーバーのリクエストハンドラー内からの chunked 出力

まずはリバースプロキシー無しでHTTPサーバー単体での chunked 出力について調べました。

そもそもどうやって Go の net/http パッケージで chunked なレスポンスを返すかですが、 [StackOverflow の回答](https://stackoverflow.com/a/30603654/1391518) にコードと telnet で受信したレスポンスのサンプルが紹介されていました。

`Content-Length` レスポンスヘッダーをつけないようにしつつ、リクエストハンドラーの `func ServeHTTP(w http.ResponseWriter, r *http.Request)` の `w` を [net/http.Flusher](https://golang.org/pkg/net/http/#Flusher) インタフェースに type assertion して OK ならその Flush メソッドを呼ぶと chunked なレスポンスを返せます。

自分でも試してみました。

```go
package main

import (
	"flag"
	"fmt"
	"html"
	"log"
	"net/http"
	"time"
)

func main() {
	addr := flag.String("addr", ":9090", "listen address")
	flag.Parse()

	if err := run(*addr); err != nil {
		log.Fatal(err)
	}
}

func run(addr string) error {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintf(w, "Hello, %q\n", html.EscapeString(r.URL.Path))
		flusher, ok := w.(http.Flusher)
		log.Printf("w type=%T, is flusher=%v", w, ok)
		if !ok {
			panic("expected http.ResponseWriter to be an http.Flusher")
		}
		for i := 1; i <= 3; i++ {
			fmt.Fprintf(w, "Chunk #%d\n", i)
			flusher.Flush() // Trigger "chunked" encoding and send a chunk...
			time.Sleep(500 * time.Millisecond)
		}
	})

	return http.ListenAndServe(addr, nil)
}
```

telnet での検証結果。Hostリクエストヘッダの後の空行を入れるとchunkedレスポンスが返ってきます。
最後は ^] (Ctrl-]) を押した後 ^D (Ctrl-D) を押してtelnetを抜けます。

```
$ telnet localhost 9090
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
GET / HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: text/plain
Date: Sat, 26 Jun 2021 01:38:54 GMT
Transfer-Encoding: chunked

14
Hello, "/"
Chunk #1

9
Chunk #2

9
Chunk #3

0

^]
telnet> Connection closed.
```

サーバー側の `log.Printf("w type=%T, is flusher=%v", w, ok)` の出力は `w type=*http.response, is flusher=true` となりました。

つまり、リクエストハンドラーの `func ServeHTTP(w http.ResponseWriter, r *http.Request)` の `w` は `*net/http.response` が渡されます。

[http.response 構造体の定義](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L417-L485)。

[net/http/httputil/NewChunkedWriter](https://golang.org/pkg/net/http/httputil/#NewChunkedWriter) という公開APIはあるがそちらは使わず、非公開の chunkWriter 構造体を使っています。

```go
// A response represents the server side of an HTTP response.
type response struct {
// …(略)…
	w  *bufio.Writer // buffers output in chunks to chunkWriter
	cw chunkWriter
// …(略)…
}
```

`http.response` の w と cw は [conn の readRequest メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L956-L1058) 内で設定されます。

```go
// Read next request from connection.
func (c *conn) readRequest(ctx context.Context) (w *response, err error) {
// …(略)…
	w = &response{
		conn:          c,
// …(略)…
	}
// …(略)…
	w.cw.res = w
	w.w = newBufioWriterSize(&w.cw, bufferBeforeChunkingSize)
	return w, nil
}
```

[http.response の Flush メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L1677-L1683)。


```go
func (w *response) Flush() {
	if !w.wroteHeader {
		w.WriteHeader(StatusOK)
	}
	w.w.Flush()
	w.cw.flush()
}
```

[chunkedWriter 構造体の定義](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L335-L361)。

```go
// chunkWriter writes to a response's conn buffer, and is the writer
// wrapped by the response.bufw buffered writer.
//
// chunkWriter also is responsible for finalizing the Header, including
// conditionally setting the Content-Type and setting a Content-Length
// in cases where the handler's final output is smaller than the buffer
// size. It also conditionally adds chunk headers, when in chunking mode.
//
// See the comment above (*response).Write for the entire write flow.
type chunkWriter struct {
	res *response

	// header is either nil or a deep clone of res.handlerHeader
	// at the time of res.writeHeader, if res.writeHeader is
	// called and extra buffering is being done to calculate
	// Content-Type and/or Content-Length.
	header Header

	// wroteHeader tells whether the header's been written to "the
	// wire" (or rather: w.conn.buf). this is unlike
	// (*response).wroteHeader, which tells only whether it was
	// logically written.
	wroteHeader bool

	// set by the writeHeader method:
	chunking bool // using chunked transfer encoding for reply body
}
```

`chunking` は [chunkWriter の writeHeader メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L1214-L1488) 内の以下の条件を全て満たす場合に `true` に設定されます。

* メソッドが HEAD ではない
* ボディが許されるステータスコードである
* Content-Length がない
* リクエストプロトコルが HTTP/1.1 以上である
* Transfer-Encoding が存在しないか、存在するが値が identity ではない　

```go
// writeHeader finalizes the header sent to the client and writes it
// to cw.res.conn.bufw.
//
// p is not written by writeHeader, but is the first chunk of the body
// that will be written. It is sniffed for a Content-Type if none is
// set explicitly. It's also used to set the Content-Length, if the
// total body size was small and the handler has already finished
// running.
func (cw *chunkWriter) writeHeader(p []byte) {
// …(略)…
	te := header.get("Transfer-Encoding")
	hasTE := te != ""
// …(略)…
	if w.req.Method == "HEAD" || !bodyAllowedForStatus(code) {
		// do nothing
	} else if code == StatusNoContent {
		delHeader("Transfer-Encoding")
	} else if hasCL {
		delHeader("Transfer-Encoding")
	} else if w.req.ProtoAtLeast(1, 1) {
		// HTTP/1.1 or greater: Transfer-Encoding has been set to identity, and no
		// content-length has been provided. The connection must be closed after the
		// reply is written, and no chunking is to be done. This is the setup
		// recommended in the Server-Sent Events candidate recommendation 11,
		// section 8.
		if hasTE && te == "identity" {
			cw.chunking = false
			w.closeAfterReply = true
		} else {
			// HTTP/1.1 or greater: use chunked transfer encoding
			// to avoid closing the connection at EOF.
			cw.chunking = true
			setHeader.transferEncoding = "chunked"
			if hasTE && te == "chunked" {
				// We will send the chunked Transfer-Encoding header later.
				delHeader("Transfer-Encoding")
			}
		}
	} else {
		// HTTP version < 1.1: cannot do chunked transfer
		// encoding and we don't know the Content-Length so
		// signal EOF by closing connection.
		w.closeAfterReply = true
		delHeader("Transfer-Encoding") // in case already set
	}

	// Cannot use Content-Length with non-identity Transfer-Encoding.
	if cw.chunking {
		delHeader("Content-Length")
	}
// …(略)…
```

[chunkWriter の Write メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L368-L391)。

cw.chunking が true の場合は内容を書き出す前に長さと CR+LF を出力します。
さらに内容を書き出した際にエラーが起きていなければその後に CR+LF を出力します。

```go
func (cw *chunkWriter) Write(p []byte) (n int, err error) {
	if !cw.wroteHeader {
		cw.writeHeader(p)
	}
	if cw.res.req.Method == "HEAD" {
		// Eat writes.
		return len(p), nil
	}
	if cw.chunking {
		_, err = fmt.Fprintf(cw.res.conn.bufw, "%x\r\n", len(p))
		if err != nil {
			cw.res.conn.rwc.Close()
			return
		}
	}
	n, err = cw.res.conn.bufw.Write(p)
	if cw.chunking && err == nil {
		_, err = cw.res.conn.bufw.Write(crlf)
	}
	if err != nil {
		cw.res.conn.rwc.Close()
	}
	return
}
```

[chunkWriter の flush メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L393-L398)。

```go
func (cw *chunkWriter) flush() {
	if !cw.wroteHeader {
		cw.writeHeader(nil)
	}
	cw.res.conn.bufw.Flush()
}
```

[chunkWriter の close メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/server.go#L400-L415)。

chunked の終わりを示す 0+CR+LF を書いた後、あればトレーラーを書いて、最後に CR+LF を書いています。

```go
func (cw *chunkWriter) close() {
	if !cw.wroteHeader {
		cw.writeHeader(nil)
	}
	if cw.chunking {
		bw := cw.res.conn.bufw // conn's bufio writer
		// zero chunk to mark EOF
		bw.WriteString("0\r\n")
		if trailers := cw.res.finalTrailers(); trailers != nil {
			trailers.Write(bw) // the writer handles noting errors
		}
		// final blank line after the trailers (whether
		// present or not)
		bw.WriteString("\r\n")
	}
}
```

## ReverseProxy を経由した chunked 出力

[httputil.NewSingleHostReverseProxy](https://golang.org/pkg/net/http/httputil/#NewSingleHostReverseProxy) を使ったリバースプロキシーのサンプルです。

```go
package main

import (
	"flag"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
)

func main() {
	addr := flag.String("addr", ":9900", "listen address")
	upstream := flag.String("upstream", "http://localhost:9090", "upstream URL")
	flag.Parse()

	if err := run(*addr, *upstream); err != nil {
		log.Fatal(err)
	}
}

func run(addr, upstream string) error {
	rpURL, err := url.Parse(upstream)
	if err != nil {
		return err
	}
	http.Handle("/", httputil.NewSingleHostReverseProxy(rpURL))

	return http.ListenAndServe(addr, nil)
}
```

telnet での検証結果。

```
$ telnet localhost 9900
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
GET / HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: text/plain
Date: Sat, 26 Jun 2021 01:45:36 GMT
Transfer-Encoding: chunked

14
Hello, "/"
Chunk #1

9
Chunk #2

9
Chunk #3

0

^]
telnet> Connection closed.
```

オリジンサーバの `time.Sleep(500 * time.Millisecond)` をコメントアウトして再度試してみると Chunk #2 と Chunk #3 が1つにまとめて出力されました。

```
$ telnet localhost 9900
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
GET / HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: text/plain
Date: Sat, 26 Jun 2021 01:48:37 GMT
Transfer-Encoding: chunked

14
Hello, "/"
Chunk #1

12
Chunk #2
Chunk #3

0

^]
telnet> Connection closed.
```

オリジンに直接アクセスするとこちらはまとめられてはいません。

```
$ telnet localhost 9090
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
GET / HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: text/plain
Date: Sat, 26 Jun 2021 01:50:30 GMT
Transfer-Encoding: chunked

14
Hello, "/"
Chunk #1

9
Chunk #2

9
Chunk #3

0

^]
telnet> Connection closed.
```

[ReverseProxy の ServeHTTP メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/httputil/reverseproxy.go#L212-L358) 内の以下の行

```go
	err = p.copyResponse(rw, res.Body, p.flushInterval(res))
```

でオリジンのレスポンスボディをクライアントに返しているようです。

ここで Go の標準ライブラリーのソースにデバッグログ出力を埋め込んで調査しました。
これは [umeda.go #2 で発表してきた - kawaken's blog](https://kawaken.hateblo.jp/entry/2017/07/31/150015) で教わったものです。公式ドキュメントに書かれているわけではないので、将来もできるかの保証はありませんが、ソースを書き換えて自分のアプリケーションをビルドするだけで良いので手軽で便利です。デバッグが終わったらソースを元に戻すのを忘れずに。私は以下のような感じで /usr/local/go 全体でインストールし直しています。

```
rm -rf /usr/local/go; tar xf ~/go1.16.5.linux-amd64.tar.gz -C /usr/local/
```

またGoの標準ライブラリーのソースを Visual Studio Code で開くときは [File] / [Add Folder to Workspace ...] メニューで /usr/local/go ではなく /usr/local/go/src を開くと [Go to Definition] なども動いて便利です。

[ReverseProxy の copyResponse メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/httputil/reverseproxy.go#L413-L437) に以下のように 2 箇所ログ出力を入れてみました。

```go
func (p *ReverseProxy) copyResponse(dst io.Writer, src io.Reader, flushInterval time.Duration) error {
	log.Printf("ReverseProxy.copyResponse, dst type=%T, flushInterval=%s", dst, flushInterval)
	if flushInterval != 0 {
		if wf, ok := dst.(writeFlusher); ok {
			log.Print("ReverseProxy.copyResponse, dst is writeFlusher")
			mlw := &maxLatencyWriter{
				dst:     wf,
				latency: flushInterval,
			}
			defer mlw.stop()

			// set up initial timer so headers get flushed even if body writes are delayed
			mlw.flushPending = true
			mlw.t = time.AfterFunc(flushInterval, mlw.delayedFlush)

			dst = mlw
		}
	}

	var buf []byte
	if p.BufferPool != nil {
		buf = p.BufferPool.Get()
		defer p.BufferPool.Put(buf)
	}
	_, err := p.copyBuffer(dst, src, buf)
	return err
}
```

これで再度試すと以下のようなログが出ました。

```
2021/06/26 10:56:12 ReverseProxy.copyResponse, dst type=*http.response, flushInterval=-1ns
2021/06/26 10:56:12 ReverseProxy.copyResponse, dst is writeFlusher
```

ということで ReverseProxy の copyResponse の引数の dst は `*http.response` 型ですが、中で `maxLatencyWriter` 構造体のインスタンスを作って dst を差し替えていることがわかります。

[writeFlusher](https://github.com/golang/go/blob/go1.16.5/src/net/http/httputil/reverseproxy.go#L480-L483) は以下のようなインターフェースです。

```go
type writeFlusher interface {
	io.Writer
	http.Flusher
}
```

[maxLatencyWriter](https://github.com/golang/go/blob/go1.16.5/src/net/http/httputil/reverseproxy.go#L485-L492) 構造体の定義。

```go
type maxLatencyWriter struct {
	dst     writeFlusher
	latency time.Duration // non-zero; negative means to flush immediately

	mu           sync.Mutex // protects t, flushPending, and dst.Flush
	t            *time.Timer
	flushPending bool
}
```

今回は上のログ出力でわかったように dst は `*http.response` 型の値で latency は -1 になっています。

[maxLatencyWriter の Write メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/httputil/reverseproxy.go#L494-L512) にもログを入れました。

```go
func (m *maxLatencyWriter) Write(p []byte) (n int, err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	n, err = m.dst.Write(p)
	log.Printf("httputil.maxLatencyWriter.Write, n=%d, err=%v, latency=%d, flushPending=%v, dst type=%T", n, err, m.latency, m.flushPending, m.dst)
	if m.latency < 0 {
		m.dst.Flush()
		return
	}
// …(略)…
```

以下のように2回呼ばれていました。n=20は16進数だと14、n=18は16進数だと12なので、上でtelnetでChunk #2とChunk #3がまとめられたときのチャンクのサイズと一致しています。

```
2021/06/26 11:25:47 httputil.maxLatencyWriter.Write, n=20, err=<nil>, latency=-1, flushPending=true, dst type=*http.response
```

```
2021/06/26 11:25:47 httputil.maxLatencyWriter.Write, n=18, err=<nil>, latency=-1, flushPending=true, dst type=*http.response
```

[ReverseProxy の copyBuffer メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/httputil/reverseproxy.go#L439-L470) にもログを入れました。

```go
// copyBuffer returns any write errors or non-EOF read errors, and the amount
// of bytes written.
func (p *ReverseProxy) copyBuffer(dst io.Writer, src io.Reader, buf []byte) (int64, error) {
	if len(buf) == 0 {
		buf = make([]byte, 32*1024)
	}
	var written int64
	for {
		nr, rerr := src.Read(buf)
		log.Printf("ReverseProxy.copyBuffer, dst type=%T, src type=%T, nr=%d, nerr=%v", dst, src, nr, rerr)
		if rerr != nil && rerr != io.EOF && rerr != context.Canceled {
			p.logf("httputil: ReverseProxy read error during body copy: %v", rerr)
		}
		if nr > 0 {
			nw, werr := dst.Write(buf[:nr])
			if nw > 0 {
				written += int64(nw)
			}
			if werr != nil {
				return written, werr
			}
			if nr != nw {
				return written, io.ErrShortWrite
			}
		}
		if rerr != nil {
			if rerr == io.EOF {
				rerr = nil
			}
			return written, rerr
		}
	}
}
```

出力はこうなりました。

```
2021/06/26 11:35:16 ReverseProxy.copyBuffer, dst type=*httputil.maxLatencyWriter, src type=*http.bodyEOFSignal, nr=20, nerr=<nil>
```

```
2021/06/26 11:35:16 ReverseProxy.copyBuffer, dst type=*httputil.maxLatencyWriter, src type=*http.bodyEOFSignal, nr=18, nerr=EOF
```

[bodyEOFSignal 構造体の定義](https://github.com/golang/go/blob/go1.16.5/src/net/http/transport.go#L2731-L2749)。

```go
// bodyEOFSignal is used by the HTTP/1 transport when reading response
// bodies to make sure we see the end of a response body before
// proceeding and reading on the connection again.
//
// It wraps a ReadCloser but runs fn (if non-nil) at most
// once, right before its final (error-producing) Read or Close call
// returns. fn should return the new error to return from Read or Close.
//
// If earlyCloseFn is non-nil and Close is called before io.EOF is
// seen, earlyCloseFn is called instead of fn, and its return value is
// the return value from Close.
type bodyEOFSignal struct {
	body         io.ReadCloser
	mu           sync.Mutex        // guards following 4 fields
	closed       bool              // whether Close has been called
	rerr         error             // sticky Read error
	fn           func(error) error // err will be nil on Read io.EOF
	earlyCloseFn func() error      // optional alt Close func used if io.EOF not seen
}
```

ところで何回も telnet で試していたらリクエストを手入力するのが大変です。標準入力に流し込めないのかなと検索すると [StackOverflowの回答](https://unix.stackexchange.com/a/160597/135274) で telnet では無理なので nc を使えと言われていました。以下のようにすると出来ました。

```
$ (echo GET / HTTP/1.1; echo Host: example.com; echo Connection: close; echo) | nc localhost 9900
HTTP/1.1 200 OK
Content-Type: text/plain
Date: Sat, 26 Jun 2021 04:21:31 GMT
Connection: close
Transfer-Encoding: chunked

14
Hello, "/"
Chunk #1

12
Chunk #2
Chunk #3

0


```

話を元に戻して bodyEOFSignal ですが [persistConn の readLoop メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/transport.go#L2048-L2226) 内で resp.Body に設定されていました。

```go
		waitForBodyRead := make(chan bool, 2)
		body := &bodyEOFSignal{
			body: resp.Body,
			earlyCloseFn: func() error {
				waitForBodyRead <- false
				<-eofc // will be closed by deferred call at the end of the function
				return nil

			},
			fn: func(err error) error {
				isEOF := err == io.EOF
				waitForBodyRead <- isEOF
				if isEOF {
					<-eofc // see comment above eofc declaration
				} else if err != nil {
					if cerr := pc.canceled(); cerr != nil {
						return cerr
					}
				}
				return err
			},
		}

		resp.Body = body
```

[bodyEOFSignal の Read メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/transport.go#L2753-L2774) を見てもチャンクをまとめてはいなさそうなので、この中で呼び出している `es.body.Read` のほうを見ることにします。またログを追加して es.body の型を調べます。

```go
func (es *bodyEOFSignal) Read(p []byte) (n int, err error) {
	es.mu.Lock()
	closed, rerr := es.closed, es.rerr
	es.mu.Unlock()
	if closed {
		return 0, errReadOnClosedResBody
	}
	if rerr != nil {
		return 0, rerr
	}

	log.Printf("bodyEOFSignal.Read, es.body type=%T", es.body)
	n, err = es.body.Read(p)
	if err != nil {
		es.mu.Lock()
		defer es.mu.Unlock()
		if es.rerr == nil {
			es.rerr = err
		}
		err = es.condfn(err)
	}
	return
}
```

```
2021/06/26 13:38:31 bodyEOFSignal.Read, es.body type=*http.body
```

[http.body 構造体の定義](https://github.com/golang/go/blob/go1.16.5/src/net/http/transfer.go#L805-L820)。

```go
// body turns a Reader into a ReadCloser.
// Close ensures that the body has been fully read
// and then reads the trailer if necessary.
type body struct {
	src          io.Reader
	hdr          interface{}   // non-nil (Response or Request) value means read trailer
	r            *bufio.Reader // underlying wire-format reader for the trailer
	closing      bool          // is the connection to be closed after reading body?
	doEarlyClose bool          // whether Close should stop early

	mu         sync.Mutex // guards following, and calls to Read and Close
	sawEOF     bool
	closed     bool
	earlyClose bool   // Close called and we didn't read to the end of src
	onHitEOF   func() // if non-nil, func to call when EOF is Read
}
```

[http.body の Read メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/transfer.go#L828-L835)。

```go
func (b *body) Read(p []byte) (n int, err error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.closed {
		return 0, ErrBodyReadAfterClose
	}
	return b.readLocked(p)
}
```

[http.body の readLocked メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/transfer.go#L837-L884)。またログを入れます。

```go
// Must hold b.mu.
func (b *body) readLocked(p []byte) (n int, err error) {
	log.Printf("http.body.readLocked, src type=%T, sawEOF=%v", b.src, b.sawEOF)
	if b.sawEOF {
		return 0, io.EOF
	}
	n, err = b.src.Read(p)

	if err == io.EOF {
		b.sawEOF = true
		// Chunked case. Read the trailer.
		if b.hdr != nil {
			if e := b.readTrailer(); e != nil {
				err = e
				// Something went wrong in the trailer, we must not allow any
				// further reads of any kind to succeed from body, nor any
				// subsequent requests on the server connection. See
				// golang.org/issue/12027
				b.sawEOF = false
				b.closed = true
			}
			b.hdr = nil
		} else {
			// If the server declared the Content-Length, our body is a LimitedReader
			// and we need to check whether this EOF arrived early.
			if lr, ok := b.src.(*io.LimitedReader); ok && lr.N > 0 {
				err = io.ErrUnexpectedEOF
			}
		}
	}

	// If we can return an EOF here along with the read data, do
	// so. This is optional per the io.Reader contract, but doing
	// so helps the HTTP transport code recycle its connection
	// earlier (since it will see this EOF itself), even if the
	// client doesn't do future reads or Close.
	if err == nil && n > 0 {
		if lr, ok := b.src.(*io.LimitedReader); ok && lr.N == 0 {
			err = io.EOF
			b.sawEOF = true
		}
	}

	if b.sawEOF && b.onHitEOF != nil {
		b.onHitEOF()
	}

	return n, err
}
```

ログ出力。

```
2021/06/26 13:45:38 http.body.readLocked, src type=*internal.chunkedReader, sawEOF=false
```

[net/http パッケージの readTransfer 関数](https://github.com/golang/go/blob/go1.16.5/src/net/http/transfer.go#L481-L597) 内で tranferReader のインスタンス t を作っていて `t.Chunked` が true でボディーありの場合に `internal.NewChunkedReader` 関数で生成されて http.body 型の src フィールドに設定されています。

関数の前のコメントに msg は `*Request` か `*Response` とあるようにこの関数はHTTPリクエストとレスポンスで共通となっています。

```go
// msg is *Request or *Response.
func readTransfer(msg interface{}, r *bufio.Reader) (err error) {
	t := &transferReader{RequestMethod: "GET"}

	// Unify input
	isResponse := false
	switch rr := msg.(type) {
	case *Response:
		t.Header = rr.Header
		t.StatusCode = rr.StatusCode
		t.ProtoMajor = rr.ProtoMajor
		t.ProtoMinor = rr.ProtoMinor
		t.Close = shouldClose(t.ProtoMajor, t.ProtoMinor, t.Header, true)
		isResponse = true
		if rr.Request != nil {
			t.RequestMethod = rr.Request.Method
		}
	case *Request:
		t.Header = rr.Header
		t.RequestMethod = rr.Method
		t.ProtoMajor = rr.ProtoMajor
		t.ProtoMinor = rr.ProtoMinor
		// Transfer semantics for Requests are exactly like those for
		// Responses with status code 200, responding to a GET method
		t.StatusCode = 200
		t.Close = rr.Close
	default:
		panic("unexpected type")
	}

	// Default to HTTP/1.1
	if t.ProtoMajor == 0 && t.ProtoMinor == 0 {
		t.ProtoMajor, t.ProtoMinor = 1, 1
	}

	// Transfer-Encoding: chunked, and overriding Content-Length.
	if err := t.parseTransferEncoding(); err != nil {
		return err
	}
// …(略)…
	// Prepare body reader. ContentLength < 0 means chunked encoding
	// or close connection when finished, since multipart is not supported yet
	switch {
	case t.Chunked:
		if noResponseBodyExpected(t.RequestMethod) || !bodyAllowedForStatus(t.StatusCode) {
			t.Body = NoBody
		} else {
			t.Body = &body{src: internal.NewChunkedReader(r), hdr: msg, r: r, closing: t.Close}
		}
	case realLength == 0:
		t.Body = NoBody
	case realLength > 0:
		t.Body = &body{src: io.LimitReader(r, realLength), closing: t.Close}
	default:
		// realLength < 0, i.e. "Content-Length" not mentioned in header
		if t.Close {
			// Close semantics (i.e. HTTP/1.0)
			t.Body = &body{src: r, closing: t.Close}
		} else {
			// Persistent connection (i.e. HTTP/1.1)
			t.Body = NoBody
		}
	}

	// Unify output
	switch rr := msg.(type) {
	case *Request:
		rr.Body = t.Body
		rr.ContentLength = t.ContentLength
		if t.Chunked {
			rr.TransferEncoding = []string{"chunked"}
		}
		rr.Close = t.Close
		rr.Trailer = t.Trailer
	case *Response:
		rr.Body = t.Body
		rr.ContentLength = t.ContentLength
		if t.Chunked {
			rr.TransferEncoding = []string{"chunked"}
		}
		rr.Close = t.Close
		rr.Trailer = t.Trailer
	}

	return nil
}
```

`t.Chunked` は [transferReader の parseTransferEncoding メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/transfer.go#L621-L660) 内でプロトコルが HTTP/1.1 以上かつ `Transfer-Encoding` ヘッダーが chunked のときに true に設定されています。またその際は `Content-Length` ヘッダーは消されています。

```go
// parseTransferEncoding sets t.Chunked based on the Transfer-Encoding header.
func (t *transferReader) parseTransferEncoding() error {
	raw, present := t.Header["Transfer-Encoding"]
	if !present {
		return nil
	}
	delete(t.Header, "Transfer-Encoding")

	// Issue 12785; ignore Transfer-Encoding on HTTP/1.0 requests.
	if !t.protoAtLeast(1, 1) {
		return nil
	}

	// Like nginx, we only support a single Transfer-Encoding header field, and
	// only if set to "chunked". This is one of the most security sensitive
	// surfaces in HTTP/1.1 due to the risk of request smuggling, so we keep it
	// strict and simple.
	if len(raw) != 1 {
		return &unsupportedTEError{fmt.Sprintf("too many transfer encodings: %q", raw)}
	}
	if strings.ToLower(textproto.TrimString(raw[0])) != "chunked" {
		return &unsupportedTEError{fmt.Sprintf("unsupported transfer encoding: %q", raw[0])}
	}

	// RFC 7230 3.3.2 says "A sender MUST NOT send a Content-Length header field
	// in any message that contains a Transfer-Encoding header field."
	//
	// but also: "If a message is received with both a Transfer-Encoding and a
	// Content-Length header field, the Transfer-Encoding overrides the
	// Content-Length. Such a message might indicate an attempt to perform
	// request smuggling (Section 9.5) or response splitting (Section 9.4) and
	// ought to be handled as an error. A sender MUST remove the received
	// Content-Length field prior to forwarding such a message downstream."
	//
	// Reportedly, these appear in the wild.
	delete(t.Header, "Content-Length")

	t.Chunked = true
	return nil
}
```

[net/http/internal.chunkedReader 構造体の定義](https://github.com/golang/go/blob/go1.16.5/src/net/http/internal/chunked.go#L37-L43)。

```go
type chunkedReader struct {
	r        *bufio.Reader
	n        uint64 // unread bytes in chunk
	err      error
	buf      [2]byte
	checkEnd bool // whether need to check for \r\n chunk footer
}
```

[net/http/internal.chunkedReader の Read メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/internal/chunked.go#L70-L115) の最後に以下のようにログ出力を入れました。今回はスタックトレースも出してみました。今は呼び出し順を追って書いてるから不要ですが、気になる箇所がどこから呼ばれているかわかってない段階ではスタックトレースを出して調べるのは便利です（実は最初の方で気になるところにスタックトレース出力を入れてたのですが説明上は不要なので省略してました。使い方のメモということでここに入れておきます）。

```go
func (cr *chunkedReader) Read(b []uint8) (n int, err error) {
	for cr.err == nil {
		if cr.checkEnd {
			if n > 0 && cr.r.Buffered() < 2 {
				// We have some data. Return early (per the io.Reader
				// contract) instead of potentially blocking while
				// reading more.
				break
			}
			if _, cr.err = io.ReadFull(cr.r, cr.buf[:2]); cr.err == nil {
				if string(cr.buf[:]) != "\r\n" {
					cr.err = errors.New("malformed chunked encoding")
					break
				}
			}
			cr.checkEnd = false
		}
		if cr.n == 0 {
			if n > 0 && !cr.chunkHeaderAvailable() {
				// We've read enough. Don't potentially block
				// reading a new chunk header.
				break
			}
			cr.beginChunk()
			continue
		}
		if len(b) == 0 {
			break
		}
		rbuf := b
		if uint64(len(rbuf)) > cr.n {
			rbuf = rbuf[:cr.n]
		}
		var n0 int
		n0, cr.err = cr.r.Read(rbuf)
		n += n0
		b = b[n0:]
		cr.n -= uint64(n0)
		// If we're at the end of a chunk, read the next two
		// bytes to verify they are "\r\n".
		if cr.n == 0 && cr.err == nil {
			cr.checkEnd = true
		}
	}
	{
		var buf [4096]byte
		n2 := runtime.Stack(buf[:], false)
		log.Printf("chunkedReader.Read, n=%d, err=%v, stack=%s", n, cr.err, buf[:n2])
	}
	return n, cr.err
}
```

```
2021/06/26 16:05:31 chunkedReader.Read, n=20, err=<nil>, stack=goroutine 6 [running]:
net/http/internal.(*chunkedReader).Read(0xc000286060, 0xc0002a6014, 0x7fec, 0x7fec, 0x2, 0x6e2060, 0xc000298000)
        /usr/local/go/src/net/http/internal/chunked.go:118 +0x1b6
net/http.(*body).readLocked(0xc00028e000, 0xc0002a6000, 0x8000, 0x8000, 0xc00008c050, 0x2, 0xc00029a060)
        /usr/local/go/src/net/http/transfer.go:844 +0xf2
net/http.(*body).Read(0xc00028e000, 0xc0002a6000, 0x8000, 0x8000, 0x0, 0x0, 0x0)
        /usr/local/go/src/net/http/transfer.go:835 +0xf9
net/http.(*bodyEOFSignal).Read(0xc00028e040, 0xc0002a6000, 0x8000, 0x8000, 0x0, 0x0, 0x0)
        /usr/local/go/src/net/http/transport.go:2765 +0x13d
net/http/httputil.(*ReverseProxy).copyBuffer(0xc00008c140, 0x7491a0, 0xc0002860c0, 0x748f80, 0xc00028e040, 0xc0002a6000, 0x8000, 0x8000, 0x1, 0x0, ...)
        /usr/local/go/src/net/http/httputil/reverseproxy.go:450 +0xbe
net/http/httputil.(*ReverseProxy).copyResponse(0xc00008c140, 0x749140, 0xc0000e40e0, 0x748f80, 0xc00028e040, 0xffffffffffffffff, 0x0, 0x0)
        /usr/local/go/src/net/http/httputil/reverseproxy.go:438 +0x190
net/http/httputil.(*ReverseProxy).ServeHTTP(0xc00008c140, 0x74d280, 0xc0000e40e0, 0xc0000fe000)
        /usr/local/go/src/net/http/httputil/reverseproxy.go:325 +0x8a5
net/http.(*ServeMux).ServeHTTP(0x8c3660, 0x74d280, 0xc0000e40e0, 0xc0000fe000)
        /usr/local/go/src/net/http/server.go:2462 +0x1ad
net/http.serverHandler.ServeHTTP(0xc0000e4000, 0x74d280, 0xc0000e40e0, 0xc0000fe000)
        /usr/local/go/src/net/http/server.go:2901 +0xa3
net/http.(*conn).serve(0xc0000a8a00, 0x74d700, 0xc0000802c0)
        /usr/local/go/src/net/http/server.go:1966 +0x8cd
created by net/http.(*Server).Serve
        /usr/local/go/src/net/http/server.go:3027 +0x39b
```

```
2021/06/26 16:05:31 chunkedReader.Read, n=18, err=EOF, stack=goroutine 6 [running]:
net/http/internal.(*chunkedReader).Read(0xc000286060, 0xc0002a6012, 0x7fee, 0x7fee, 0x2, 0x6e2060, 0xc000122000)
        /usr/local/go/src/net/http/internal/chunked.go:118 +0x1b6
net/http.(*body).readLocked(0xc00028e000, 0xc0002a6000, 0x8000, 0x8000, 0xc00008c050, 0x2, 0xc000148000)
        /usr/local/go/src/net/http/transfer.go:844 +0xf2
net/http.(*body).Read(0xc00028e000, 0xc0002a6000, 0x8000, 0x8000, 0x0, 0x0, 0x0)
        /usr/local/go/src/net/http/transfer.go:835 +0xf9
net/http.(*bodyEOFSignal).Read(0xc00028e040, 0xc0002a6000, 0x8000, 0x8000, 0x0, 0x0, 0x0)
        /usr/local/go/src/net/http/transport.go:2765 +0x13d
net/http/httputil.(*ReverseProxy).copyBuffer(0xc00008c140, 0x7491a0, 0xc0002860c0, 0x748f80, 0xc00028e040, 0xc0002a6000, 0x8000, 0x8000, 0x1, 0x0, ...)
        /usr/local/go/src/net/http/httputil/reverseproxy.go:450 +0xbe
net/http/httputil.(*ReverseProxy).copyResponse(0xc00008c140, 0x749140, 0xc0000e40e0, 0x748f80, 0xc00028e040, 0xffffffffffffffff, 0x0, 0x0)
        /usr/local/go/src/net/http/httputil/reverseproxy.go:438 +0x190
net/http/httputil.(*ReverseProxy).ServeHTTP(0xc00008c140, 0x74d280, 0xc0000e40e0, 0xc0000fe000)
        /usr/local/go/src/net/http/httputil/reverseproxy.go:325 +0x8a5
net/http.(*ServeMux).ServeHTTP(0x8c3660, 0x74d280, 0xc0000e40e0, 0xc0000fe000)
        /usr/local/go/src/net/http/server.go:2462 +0x1ad
net/http.serverHandler.ServeHTTP(0xc0000e4000, 0x74d280, 0xc0000e40e0, 0xc0000fe000)
        /usr/local/go/src/net/http/server.go:2901 +0xa3
net/http.(*conn).serve(0xc0000a8a00, 0x74d700, 0xc0000802c0)
        /usr/local/go/src/net/http/server.go:1966 +0x8cd
created by net/http.(*Server).Serve
        /usr/local/go/src/net/http/server.go:3027 +0x39b
```

[net/http/internal.chunkedReader の beginChunk メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/internal/chunked.go#L45-L59)

```go
func (cr *chunkedReader) beginChunk() {
	// chunk-size CRLF
	var line []byte
	line, cr.err = readChunkLine(cr.r)
	if cr.err != nil {
		return
	}
	cr.n, cr.err = parseHexUint(line)
	if cr.err != nil {
		return
	}
	if cr.n == 0 {
		cr.err = io.EOF
	}
}
```

[net/http/internal.chunkedReader の readChunkLine メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/internal/chunked.go#L117-L142)

```go
// Read a line of bytes (up to \n) from b.
// Give up if the line exceeds maxLineLength.
// The returned bytes are owned by the bufio.Reader
// so they are only valid until the next bufio read.
func readChunkLine(b *bufio.Reader) ([]byte, error) {
	p, err := b.ReadSlice('\n')
	if err != nil {
		// We always know when EOF is coming.
		// If the caller asked for a line, there should be a line.
		if err == io.EOF {
			err = io.ErrUnexpectedEOF
		} else if err == bufio.ErrBufferFull {
			err = ErrLineTooLong
		}
		return nil, err
	}
	if len(p) >= maxLineLength {
		return nil, ErrLineTooLong
	}
	p = trimTrailingWhitespace(p)
	p, err = removeChunkExtension(p)
	if err != nil {
		return nil, err
	}
	return p, nil
}
```

[net/http/internal.chunkedReader の chunkHeaderAvailable メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/internal/chunked.go#L61-L68)

```go
func (cr *chunkedReader) chunkHeaderAvailable() bool {
	n := cr.r.Buffered()
	if n > 0 {
		peek, _ := cr.r.Peek(n)
		return bytes.IndexByte(peek, '\n') >= 0
	}
	return false
}
```

[bufio.Reader 構造体](https://golang.org/pkg/bufio/#Reader) の [Buffered メソッド](https://golang.org/pkg/bufio/#Reader.Buffered) でバッファ内の残りバイト数を調べて 0 より大きい場合は [Peek メソッド](https://golang.org/pkg/bufio/#Reader.Peek) で `'\n'` が含まれるかを調べています。

[net/http/internal.chunkedReader の Read メソッド](https://github.com/golang/go/blob/go1.16.5/src/net/http/internal/chunked.go#L70-L115) にデバッグログ出力を大量に入れて再度試しました。

```go
func (cr *chunkedReader) Read(b []uint8) (n int, err error) {
	log.Printf("chunkedReader.Read start, len(b)=%d", len(b))
	for cr.err == nil {
		log.Printf("chunkedReader.Read, came into for loop, cr.checkEnd=%v", cr.checkEnd)
		if cr.checkEnd {
			log.Printf("chunkedReader.Read checkEnd, n=%d, cr.r.Buffered()=%d", n, cr.r.Buffered())
			if n > 0 && cr.r.Buffered() < 2 {
				// We have some data. Return early (per the io.Reader
				// contract) instead of potentially blocking while
				// reading more.
				log.Print("chunkedReader.Read break since n > 0 && cr.r.Buffered() < 2")
				break
			}
			if _, cr.err = io.ReadFull(cr.r, cr.buf[:2]); cr.err == nil {
				if string(cr.buf[:]) != "\r\n" {
					cr.err = errors.New("malformed chunked encoding")
					break
				}
			}
			cr.checkEnd = false
			log.Print("chunkedReader.Read, set cr.checkEnd to false")
		}
		log.Printf("chunkedReader.Read, before if cr.n == 0, cr.n=%d", cr.n)
		if cr.n == 0 {
			if n > 0 && !cr.chunkHeaderAvailable() {
				// We've read enough. Don't potentially block
				// reading a new chunk header.
				log.Print("chunkedReader.Read break n > 0 && !cr.chunkHeaderAvailable()")
				break
			}
			cr.beginChunk()
			continue
		}
		log.Printf("chunkedReader.Read, before if len(b) == 0, len(b)=%d", len(b))
		if len(b) == 0 {
			log.Print("chunkedReader.Read break len(b) == 0")
			break
		}
		rbuf := b
		log.Printf("chunkedReader.Read, before if uint64(len(rbuf)) > cr.n, uint64(len(rbuf))=%d, cr.n=%d", uint64(len(rbuf)), cr.n)
		if uint64(len(rbuf)) > cr.n {
			rbuf = rbuf[:cr.n]
		}
		var n0 int
		n0, cr.err = cr.r.Read(rbuf)
		n += n0
		b = b[n0:]
		cr.n -= uint64(n0)
		log.Printf("chunkedReader.Read, before if cr.n == 0 && cr.err == nil, n0=%d, len(b)=%d, cr.n=%d, cr.err=%v", n0, len(b), cr.n, cr.err)
		// If we're at the end of a chunk, read the next two
		// bytes to verify they are "\r\n".
		if cr.n == 0 && cr.err == nil {
			cr.checkEnd = true
			log.Print("chunkedReader.Read, set cr.checkEnd to true")
		}
	}
	log.Printf("chunkedReader.Read exiting, n=%d, err=%v", n, cr.err)
	return n, cr.err
}
```

```
2021/06/26 16:38:37 chunkedReader.Read start, len(b)=32768
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=0
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=20
2021/06/26 16:38:37 chunkedReader.Read, before if len(b) == 0, len(b)=32768
2021/06/26 16:38:37 chunkedReader.Read, before if uint64(len(rbuf)) > cr.n, uint64(len(rbuf))=32768, cr.n=20
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0 && cr.err == nil, n0=20, len(b)=32748, cr.n=0, cr.err=<nil>
2021/06/26 16:38:37 chunkedReader.Read, set cr.checkEnd to true
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=true
2021/06/26 16:38:37 chunkedReader.Read checkEnd, n=20, cr.r.Buffered()=2
2021/06/26 16:38:37 chunkedReader.Read, set cr.checkEnd to false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=0
2021/06/26 16:38:37 chunkedReader.Read break n > 0 && !cr.chunkHeaderAvailable()
2021/06/26 16:38:37 chunkedReader.Read exiting, n=20, err=<nil>
```

```
2021/06/26 16:38:37 chunkedReader.Read start, len(b)=32768
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=0
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=9
2021/06/26 16:38:37 chunkedReader.Read, before if len(b) == 0, len(b)=32768
2021/06/26 16:38:37 chunkedReader.Read, before if uint64(len(rbuf)) > cr.n, uint64(len(rbuf))=32768, cr.n=9
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0 && cr.err == nil, n0=9, len(b)=32759, cr.n=0, cr.err=<nil>
2021/06/26 16:38:37 chunkedReader.Read, set cr.checkEnd to true
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=true
2021/06/26 16:38:37 chunkedReader.Read checkEnd, n=9, cr.r.Buffered()=21
2021/06/26 16:38:37 chunkedReader.Read, set cr.checkEnd to false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=0
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=9
2021/06/26 16:38:37 chunkedReader.Read, before if len(b) == 0, len(b)=32759
2021/06/26 16:38:37 chunkedReader.Read, before if uint64(len(rbuf)) > cr.n, uint64(len(rbuf))=32759, cr.n=9
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0 && cr.err == nil, n0=9, len(b)=32750, cr.n=0, cr.err=<nil>
2021/06/26 16:38:37 chunkedReader.Read, set cr.checkEnd to true
2021/06/26 16:38:37 chunkedReader.Read, came into for loop, cr.checkEnd=true
2021/06/26 16:38:37 chunkedReader.Read checkEnd, n=18, cr.r.Buffered()=7
2021/06/26 16:38:37 chunkedReader.Read, set cr.checkEnd to false
2021/06/26 16:38:37 chunkedReader.Read, before if cr.n == 0, cr.n=0
2021/06/26 16:38:37 chunkedReader.Read exiting, n=18, err=EOF
```

ということで

* 1つもチャンクを読んでない場合はループしてチャンクが来るのを待つ。
* 1つチャンクを読んだ後は次のチャンクのヘッダがバッファ内にあれば読む。なければ抜ける。
* バッファがフルになるか、チャンクを読んだ後次のチャンクのヘッダがバッファ内にないか、 EOF が来たら抜ける。

という感じになっていることがわかりました。

まとめとしては Go の net/http では Request, Response ともボディが chunked な場合は内部で net/http/internal の chunkedReader が使われて Read すると chunked をデコードしたデータが返ってくるが、その際に受信していた複数のチャンクがまとめられるということです。
