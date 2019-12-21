+++
title="Goで書き込み中のファイルをHTTPレスポンスとして返す"
date = "2019-01-31T11:50:00+09:00"
tags = ["go", "http"]
categories = ["blog"]
+++


# はじめに

Goで別のgoroutineで書き込み中のファイルをHTTPレスポンスとして返せないかなと思って試行錯誤してみたところ、出来たのでメモです。

成果物は
https://github.com/hnakamur/readwhilewrite
で公開しています。

# WriterとReaderの同期

io.Writer と io.Reader インタフェースを実装したstructを作るのが汎用的でよいかと思い、まずは作ってみました。
1つのWriterがファイルに書き込み中に、複数のReaderが同じファイルを開いて読み出せるという想定です。
ReaderがEOFを受け取ったらビジーループでCPUを専有することなくWriterが更に書き込みを行うのを待って、書き込まれたら更に読み出すようにします。
WriterがCloseした後にReaderがEOFを受け取ったら、それは本物のEOFとして処理します。

[最初のバージョン](https://github.com/hnakamur/readwhilewrite/commit/23b92d448bf5272571a8623f2613244b0350a9f6) ではReaderがWriterを待つ箇所は [sync.Cond](https://golang.org/pkg/sync/#Cond) を使って実装してみました。

しかし、これだと待つ途中でキャンセルが出来ないのでchannelベースの実装に切り替えました。
Readerが最初にWriterにsubscribeするとバッファサイズ1のchannelを作ります。

[notifier.go#L7-L22](https://github.com/hnakamur/readwhilewrite/blob/68a26aa56e8f0f07a5c5301494128ccfc37b365c/notifier.go#L7-L22)

```go
type notifier struct {
        mu       sync.Mutex
        channels []chan struct{}
        closed   bool
}

func (n *notifier) Subscribe() <-chan struct{} {
        c := make(chan struct{}, 1)
        n.mu.Lock()
        if n.closed {
     	   close(c)
        }
        n.channels = append(n.channels, c)
        n.mu.Unlock()
        return c
}
```

Writerが書き込んだらこのchannelに通知しますが、selectとdefaultを使ってReaderが前回送ったのを受け取ってない時はブロックせずに捨てるようにしています。こうすることにより遅いReaderがいても引きずられること無く書き込みを継続できます。

[notifier.go#L35-L44](https://github.com/hnakamur/readwhilewrite/blob/68a26aa56e8f0f07a5c5301494128ccfc37b365c/notifier.go#L35-L44)

```go
func (n *notifier) Notify() {
        n.mu.Lock()
        for _, c := range n.channels {
                select {
                case c <- struct{}{}:
                default:
                }
        }
        n.mu.Unlock()
}
```

一方、Readerはまだ処理していない更新（＝書き込み）が1回以上あったことは分かるというわけです。更新の回数を知りたいとか空のstructではなくデータを送って最新の値を参照したいという場合にはこれでは困るわけですが、今回の用途にはこの方式で十分です。

WriterがCloseしたときは各Reader用のchannelをcloseします。

[notifier.go#L46-L53](https://github.com/hnakamur/readwhilewrite/blob/68a26aa56e8f0f07a5c5301494128ccfc37b365c/notifier.go#L46-L53)

```go
func (n *notifier) Close() {
        n.mu.Lock()
        for _, c := range n.channels {
     	   close(c)
        }
        n.closed = true
        n.mu.Unlock()
}
```

タイミングによっては既にWriterがCloseした後にSubscribeすることもあり得るので、上記のSubscribe内ではClose済みの場合はchannelをcloseするようにしています。


# GoでLinuxのsendfileシステムコールを使っている箇所の調査

前節で動くものが出来たのでGoで書いたHTTPサーバで使おうと思ったのですが、可能ならLinuxのsendfileシステムコールを使いたいと思い調べてみました。調査したバージョンはGo 1.11.5 です。

まずGoのソースでsendfileで検索してみると以下の箇所で syscall.Sendfile を呼び出していました。


https://github.com/golang/go/blob/go1.11.5/src/internal/poll/sendfile_linux.go#L28

```go {linenos=}
// Copyright 2011 The Go Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package poll

import "syscall"

// maxSendfileSize is the largest chunk size we ask the kernel to copy
// at a time.
const maxSendfileSize int = 4 << 20

// SendFile wraps the sendfile system call.
func SendFile(dstFD *FD, src int, remain int64) (int64, error) {
        if err := dstFD.writeLock(); err != nil {
     	   return 0, err
        }
        defer dstFD.writeUnlock()

        dst := int(dstFD.Sysfd)
        var written int64
        var err error
        for remain > 0 {
     	   n := maxSendfileSize
     	   if int64(n) > remain {
     		   n = int(remain)
     	   }
     	   n, err1 := syscall.Sendfile(dst, src, nil, n)
     	   if n > 0 {
     		   written += int64(n)
     		   remain -= int64(n)
     	   }
     	   if n == 0 && err1 == nil {
     		   break
     	   }
     	   if err1 == syscall.EAGAIN {
     		   if err1 = dstFD.pd.waitWrite(dstFD.isFile); err1 == nil {
     			   continue
     		   }
     	   }
     	   if err1 != nil {
     		   // This includes syscall.ENOSYS (no kernel
     		   // support) and syscall.EINVAL (fd types which
     		   // don't implement sendfile)
     		   err = err1
     		   break
     	   }
        }
        return written, err
}
```

internal/poll.SendFileは
https://github.com/golang/go/blob/go1.11.5/src/net/sendfile_linux.go#L35
で呼ばれています。
コードを見るとsendfileが使われるのは `r io.Reader` が `*os.File` か `*os.File` をラップした `*io.LimitedReader` のときだけだということがわかります。

```go {linenos=,linenostart=13}
// sendFile copies the contents of r to c using the sendfile
// system call to minimize copies.
//
// if handled == true, sendFile returns the number of bytes copied and any
// non-EOF error.
//
// if handled == false, sendFile performed no work.
func sendFile(c *netFD, r io.Reader) (written int64, err error, handled bool) {
        var remain int64 = 1 << 62 // by default, copy until EOF

        lr, ok := r.(*io.LimitedReader)
        if ok {
     	   remain, r = lr.N, lr.R
     	   if remain <= 0 {
     		   return 0, nil, true
     	   }
        }
        f, ok := r.(*os.File)
        if !ok {
     	   return 0, nil, false
        }

        written, err = poll.SendFile(&c.pfd, int(f.Fd()), remain)

        if lr != nil {
     	   lr.N = remain - written
        }
        return written, wrapSyscallError("sendfile", err), written > 0
}
```

sendFile関数は `net/tcp.TCPConn` のreadFrom関数から呼ばれています。
https://github.com/golang/go/blob/go1.11.5/src/net/tcpsock_posix.go#L47-L55

```go {linenos=,linenostart=47}
func (c *TCPConn) readFrom(r io.Reader) (int64, error) {
        if n, err, handled := splice(c.fd, r); handled {
     	   return n, err
        }
        if n, err, handled := sendFile(c.fd, r); handled {
     	   return n, err
        }
        return genericReadFrom(c, r)
}
```

`net/tcp.TCPConn` のreadFrom関数は同じく `net/tcp.TCPConn` のReadFrom関数から呼ばれています。
https://github.com/golang/go/blob/go1.11.5/src/net/tcpsock.go#L98-L108

```go {linenos=,linenostart=98}
// ReadFrom implements the io.ReaderFrom ReadFrom method.
func (c *TCPConn) ReadFrom(r io.Reader) (int64, error) {
        if !c.ok() {
     	   return 0, syscall.EINVAL
        }
        n, err := c.readFrom(r)
        if err != nil && err != io.EOF {
     	   err = &OpError{Op: "readfrom", Net: c.fd.net, Source: c.fd.laddr, Addr: c.fd.raddr, Err: err}
        }
        return n, err
}
```

# GoのhttpでLinuxのsendfileシステムコールが使われる条件の調査

前節で動くものが出来たのでGoで書いたHTTPサーバで使おうと思ったのですが、可能ならLinuxのsendfileシステムコールを使いたいと思いました。

ソースコードを検索して調べるのが大変になってきたので、以下のようなサンプル用のコードを書いて動かして調べることにしました。

以下の2つの方法を試したので両方メモしておきます。通常は delve を使うほうが楽です。

* delveを使ってSendFile呼び出しまでのスタックトレースを調査
* Goの標準ライブラリにデバッグログを埋め込んで調査

## delveを使ってSendFile呼び出しまでのスタックトレースを調査

```go
package main

import (
    "flag"
    "io/ioutil"
    "log"
    "net/http"
    "os"
)

func main() {
    addr := flag.String("addr", ":8080", "listen address in host:port form")
    flag.Parse()

    err := run(*addr)
    if err != nil {
        log.Fatal(err)
    }
}

func run(addr string) error {
    file, err := ioutil.TempFile("", "test")
    if err != nil {
        return err
    }
    defer os.Remove(file.Name())

    err = ioutil.WriteFile(file.Name(), []byte("hello\n"), 0644)
    if err != nil {
        return err
    }

    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        http.ServeFile(w, r, file.Name())
    })

    s := &http.Server{
        Addr: addr,
    }
    return s.ListenAndServe()
}
```

このサンプルを [delve](https://raw.githubusercontent.com/go-delve/delve/master/assets/delve_horizontal.png) というデバッガで動かします。使い方は [Golangのデバッガdelveの使い方 - Qiita](https://qiita.com/minamijoyo/items/4da68467c1c5d94c8cd7) がわかりやすかったです。

```console
dlv debug
```

で起動して SendFile 関数にブレークポイントを設定し、別の端末で curl でリクエストを打ちました。で止まったところでスタックトレースを表示すると以下のようになりました。

```txt
(dlv) b SendFile
Breakpoint 2 set at 0x4a67b8 for internal/poll.SendFile() /usr/local/go/src/internal/poll/sendfile_linux.go:14
(dlv) c
> internal/poll.SendFile() /usr/local/go/src/internal/poll/sendfile_linux.go:14 (hits goroutine(20):1 total:1) (PC: 0x4a67b8)
     9: // maxSendfileSize is the largest chunk size we ask the kernel to copy
    10: // at a time.
    11: const maxSendfileSize int = 4 << 20
    12:
    13: // SendFile wraps the sendfile system call.
=>  14: func SendFile(dstFD *FD, src int, remain int64) (int64, error) {
    15:         if err := dstFD.writeLock(); err != nil {
    16:                 return 0, err
    17:         }
    18:         defer dstFD.writeUnlock()
    19:
(dlv) stack
 0  0x00000000004a67b8 in internal/poll.SendFile
    at /usr/local/go/src/internal/poll/sendfile_linux.go:14
 1  0x00000000005b7346 in net.sendFile
    at /usr/local/go/src/net/sendfile_linux.go:35
 2  0x00000000005bc535 in net.(*TCPConn).readFrom
    at /usr/local/go/src/net/tcpsock_posix.go:51
 3  0x00000000005ba8e5 in net.(*TCPConn).ReadFrom
    at /usr/local/go/src/net/tcpsock.go:103
 4  0x00000000006c54fe in net/http.(*response).ReadFrom
    at /usr/local/go/src/net/http/server.go:602
 5  0x000000000047e20c in io.copyBuffer
    at /usr/local/go/src/io/io.go:388
 6  0x000000000047dd87 in io.Copy
    at /usr/local/go/src/io/io.go:364
 7  0x000000000047dc0b in io.CopyN
    at /usr/local/go/src/io/io.go:340
 8  0x000000000067895c in net/http.serveContent
    at /usr/local/go/src/net/http/fs.go:296
 9  0x000000000067bbab in net/http.serveFile
    at /usr/local/go/src/net/http/fs.go:620
10  0x000000000067c29b in net/http.ServeFile
    at /usr/local/go/src/net/http/fs.go:681
11  0x0000000000708ab4 in main.run.func1
    at ./main.go:34
12  0x00000000006cecb4 in net/http.HandlerFunc.ServeHTTP
    at /usr/local/go/src/net/http/server.go:1964
13  0x00000000006d1934 in net/http.(*ServeMux).ServeHTTP
    at /usr/local/go/src/net/http/server.go:2361
14  0x00000000006d26c9 in net/http.serverHandler.ServeHTTP
    at /usr/local/go/src/net/http/server.go:2741
15  0x00000000006ce026 in net/http.(*conn).serve
    at /usr/local/go/src/net/http/server.go:1847
16  0x000000000045f091 in runtime.goexit
    at /usr/local/go/src/runtime/asm_amd64.s:1333
(dlv) c
```

## Goの標準ライブラリにデバッグログを埋め込んで調査

dlvを使わない別の方法としてGoの標準ライブラリのソースを書き換えてデバッグログ出力のコードを埋め込み、
ビルドして実行するという手もあります。

[Goのダウンロードページ](https://golang.org/dl/) からバイナリをダウンロードして /usr/local/go/ に展開している場合 /usr/local/go/src/ に標準ライブラリのソースがあります。

/usr/local/go/src/internal/poll/sendfile_linux.go を以下のように書き換えて上記のサンプルをビルドします。
ちなみに os パッケージを使おうとするとimportが循環参照でコンパイルエラーになってしまったので標準出力のファイルディスクリプタ 1 はハードコーディングしています。

```diff
diff -u /usr/local/go/src/internal/poll/sendfile_linux.go.orig /usr/local/go/src/internal/poll/sendfile_linux.go
--- /usr/local/go/src/internal/poll/sendfile_linux.go.orig      2019-01-30 01:05:32.271820060 +0000
+++ /usr/local/go/src/internal/poll/sendfile_linux.go   2019-01-30 01:01:36.240575572 +0000
@@ -4,7 +4,10 @@

 package poll

-import "syscall"
+import (
+       "runtime"
+       "syscall"
+)

 // maxSendfileSize is the largest chunk size we ask the kernel to copy
 // at a time.
@@ -12,6 +15,12 @@

 // SendFile wraps the sendfile system call.
 func SendFile(dstFD *FD, src int, remain int64) (int64, error) {
+       func() {
+               buf := make([]byte, 64 * 1024)
+               _ = runtime.Stack(buf, false)
+               syscall.Write(1, buf)
+       }()
+
        if err := dstFD.writeLock(); err != nil {
     	   return 0, err
        }
```

サンプルを起動してcurlでリクエストを打つと以下のようなスタックトレースが出力されました。

```txt
goroutine 5 [running]:
internal/poll.SendFile.func1()
        /usr/local/go/src/internal/poll/sendfile_linux.go:20 +0x79
internal/poll.SendFile(0xc0000da080, 0x7, 0x6, 0x0, 0x0, 0x0)
        /usr/local/go/src/internal/poll/sendfile_linux.go:22 +0x3d
net.sendFile(0xc0000da080, 0x705c00, 0xc00014a760, 0x0, 0x0, 0x0, 0x0)
        /usr/local/go/src/net/sendfile_linux.go:35 +0x98
net.(*TCPConn).readFrom(0xc00000e050, 0x705c00, 0xc00014a760, 0xc0000a9810, 0x5fba90, 0xc0000582c0)
        /usr/local/go/src/net/tcpsock_posix.go:51 +0x88
net.(*TCPConn).ReadFrom(0xc00000e050, 0x705c00, 0xc00014a760, 0xc, 0xc0000c44c0, 0x6acd01)
        /usr/local/go/src/net/tcpsock.go:103 +0x5d
net/http.(*response).ReadFrom(0xc0000121c0, 0x705c00, 0xc00014a760, 0x0, 0x0, 0x0)
        /usr/local/go/src/net/http/server.go:602 +0x2af
io.copyBuffer(0x705fa0, 0xc0000121c0, 0x705c00, 0xc00014a760, 0x0, 0x0, 0x0, 0x684560, 0x705f01, 0xc00014a760)
        /usr/local/go/src/io/io.go:388 +0x303
io.Copy(0x705fa0, 0xc0000121c0, 0x705c00, 0xc00014a760, 0x6acd00, 0x6ca200, 0x705fa0)
        /usr/local/go/src/io/io.go:364 +0x5a
io.CopyN(0x705fa0, 0xc0000121c0, 0x706020, 0xc00000e060, 0x6, 0x0, 0x0, 0x0)
        /usr/local/go/src/io/io.go:340 +0x86
net/http.serveContent(0x7088e0, 0xc0000121c0, 0xc0000dc300, 0xc00001e2a5, 0xd, 0xf009351, 0xed3e2ee9a, 0x8c4300, 0xc00000c300, 0x7f3248d43fd0, ...)
        /usr/local/go/src/net/http/fs.go:296 +0x285
net/http.serveFile(0x7088e0, 0xc0000121c0, 0xc0000dc300, 0x706560, 0xc000010cb0, 0xc00001e205, 0xd, 0x0)
        /usr/local/go/src/net/http/fs.go:620 +0x5f9
net/http.ServeFile(0x7088e0, 0xc0000121c0, 0xc0000dc300, 0xc00001e200, 0x12)
        /usr/local/go/src/net/http/fs.go:681 +0x13f
main.run.func1(0x7088e0, 0xc0000121c0, 0xc0000dc300)
        /root/go/src/bitbucket.org/hnakamur/http-sendfile-experiment/main.go:34 +0x5a
net/http.HandlerFunc.ServeHTTP(0xc000010c10, 0x7088e0, 0xc0000121c0, 0xc0000dc300)
        /usr/local/go/src/net/http/server.go:1964 +0x44
net/http.(*ServeMux).ServeHTTP(0x8c3fa0, 0x7088e0, 0xc0000121c0, 0xc0000dc300)
        /usr/local/go/src/net/http/server.go:2361 +0x127
net/http.serverHandler.ServeHTTP(0xc000073040, 0x7088e0, 0xc0000121c0, 0xc0000dc300)
        /usr/local/go/src/net/http/server.go:2741 +0xab
net/http.(*conn).serve(0xc0000808c0, 0x708aa0, 0xc000058280)
        /usr/local/go/src/net/http/server.go:1847 +0x646
created by net/http.(*Server).Serve
        /usr/local/go/src/net/http/server.go:2851 +0x2f5
```

この方法はデバッグログ出力以外にも好きにコードを改変して実行できるので、振る舞いを変えて調査したいときには便利です。調査が終わったら標準ライブラリのコードを元に戻すのを忘れないようにしましょう。あるいはLXDやDockerなどで使い捨ての環境を作ってそこで行うと良いと思います。


## GoのhttpでLinuxのsendfileシステムコールが使われる条件

[io.Copy](https://golang.org/pkg/io/#Copy) のドキュメントを見ると、 src がWriteToインタフェースを実装していればそれが呼ばれ、dstがReadFromインタフェースを実装していればそれが呼ばれると書いてあります。

```go
func Copy(dst Writer, src Reader) (written int64, err error)
```

http.response (http.Responseではなく非公開の方)がReadFromインタフェースを実装しています。

https://github.com/golang/go/blob/go1.11.5/src/net/http/server.go#L566-L611

```go {linenos=,linenostart=566}
// ReadFrom is here to optimize copying from an *os.File regular file
// to a *net.TCPConn with sendfile.
func (w *response) ReadFrom(src io.Reader) (n int64, err error) {
        // Our underlying w.conn.rwc is usually a *TCPConn (with its
        // own ReadFrom method). If not, or if our src isn't a regular
        // file, just fall back to the normal copy method.
        rf, ok := w.conn.rwc.(io.ReaderFrom)
        regFile, err := srcIsRegularFile(src)
        if err != nil {
     	   return 0, err
        }
        if !ok || !regFile {
     	   bufp := copyBufPool.Get().(*[]byte)
     	   defer copyBufPool.Put(bufp)
     	   return io.CopyBuffer(writerOnly{w}, src, *bufp)
        }

        // sendfile path:

        if !w.wroteHeader {
     	   w.WriteHeader(StatusOK)
        }

        if w.needsSniff() {
     	   n0, err := io.Copy(writerOnly{w}, io.LimitReader(src, sniffLen))
     	   n += n0
     	   if err != nil {
     		   return n, err
     	   }
        }

        w.w.Flush()  // get rid of any previous writes
        w.cw.flush() // make sure Header is written; flush data to rwc

        // Now that cw has been flushed, its chunking field is guaranteed initialized.
        if !w.cw.chunking && w.bodyAllowed() {
     	   n0, err := rf.ReadFrom(src)
     	   n += n0
     	   w.written += n0
     	   return n, err
        }

        n0, err := io.Copy(writerOnly{w}, src)
        n += n0
        return n, err
}
```

573行目で呼ばれている srcIsRegularFile 関数
https://github.com/golang/go/blob/go1.11.5/src/net/http/server.go#L551-L564
の実装を見ると、先程のinternal/poll.SendFileと同様
`src io.Reader` が `*os.File` か `*os.File` をラップした `*io.LimitedReader` のときだけtrueを返すことがわかります。

```go {linenos=,linenostart=511}
func srcIsRegularFile(src io.Reader) (isRegular bool, err error) {
        switch v := src.(type) {
        case *os.File:
     	   fi, err := v.Stat()
     	   if err != nil {
     		   return false, err
     	   }
     	   return fi.Mode().IsRegular(), nil
        case *io.LimitedReader:
     	   return srcIsRegularFile(v.R)
        default:
     	   return
        }
}
```

また601行目を見ると `w.cw.chunking` がtrueの場合はReadFromが使われないことがわかります。

これは
https://github.com/golang/go/blob/go1.11.5/src/net/http/server.go#L1402
で true に設定されています。長いので引用は省略しますがリンク先を見ると `Transfer-Encoding: chunked` の場合に対応しています。この上の方を見ると Content-Length を設定しておけばtrueにはならないことがわかります。

まとめるとGoのhttpでLinuxのsendfileシステムコールが使われる条件は以下の2つです。

* os.Fileまたはそれをラップしたio.LimitReaderをhttp.ResponseWriterにio.Copyでコピーしている。
* `Transfer-Encoding: chunked` ではない（＝Content-Lengthを指定している）


# GoのhttpでLinuxのsendfileシステムコールを使って書き込み中のファイルを配信するサンプル

上記の調査にの結果、io.Readerインタフェースを実装した独自のstructを使うとLinuxのsendfileシステムコールは使われないことがわかりました。そこで github.com/hnakamur/readwhilewrite パッケージに [SendFileHTTP](https://godoc.org/github.com/hnakamur/readwhilewrite#SendFileHTTP) という関数を実装しました。

[send_file_http.go#L10-L49](https://github.com/hnakamur/readwhilewrite/blob/68a26aa56e8f0f07a5c5301494128ccfc37b365c/send_file_http.go#L10-L49)

```go {linenos=,linenostart=10}
// SendFileHTTP serves a file as a HTTP response while fw is writing to the same file.
//
// Once it gets an EOF, it waits more writes by the writer. If the ctx is done while
// waiting, SendFileHTTP returns. Typically you want to pass r.Context() as ctx for
// r *http.Request.
//
// If you set the Content-Length header before calling SendFileHTTP, the sendfile
// system call is used on Linux.
func SendFileHTTP(ctx context.Context, w http.ResponseWriter, file *os.File, fw *Writer) (n int64, err error) {
        wroteC := fw.subscribe()
        defer fw.unsubscribe(wroteC)

        var n1 int64
        for {
     	   n1, err = io.Copy(w, file)
     	   n += n1
     	   if err != nil && err != io.EOF {
     		   return
     	   }

     	   select {
     	   case _, ok := <-wroteC:
     		   if ok {
     			   continue
     		   }

     		   if fw.err != nil {
     			   err = fw.err
     			   return
     		   }

     		   n1, err = io.Copy(w, file)
     		   n += n1
     		   return
     	   case <-ctx.Done():
     		   err = ctx.Err()
     		   return
     	   }
        }
}
```

Writerからの書き込みを待っている間に処理を中断できるようにcontext.Contextを渡しています。
理想を言うとファイルからの読み込み中にも中断できると良いなと思ったのですが、現状これはできなさそうです。
妥協案として [os/File.SetDeadline()](https://golang.org/pkg/os/#File.SetDeadline) が使えるかとも思ったのですが、ドキュメントを読むと殆どのシステムで通常ファイルにDeadlineを設定するのは非サポートとのことでした。

使用例としてテストコードから以下に抜粋します。

[send_file_http_test.go#L17-L71](https://github.com/hnakamur/readwhilewrite/blob/68a26aa56e8f0f07a5c5301494128ccfc37b365c/send_file_http_test.go#L17-L71)

```go {linenos=,linenostart=17}
ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
```

		   file, err := ioutil.TempFile("", "test")
		   if err != nil {
			   httpError(w, http.StatusInternalServerError)
			   return
		   }
		   filename := file.Name()
		   defer os.Remove(filename)

		   w2 := readwhilewrite.NewWriter(file)

		   rerrC := make(chan error, 1)
		   go func() {
			   defer close(rerrC)

			   f, err := os.Open(filename)
			   if err != nil {
				   rerrC <- err
				   return
			   }
			   defer f.Close()

			   w.Header().Set("Content-Type", "text/plain")
			   w.Header().Set("Content-Length", "81920")

			   _, err = readwhilewrite.SendFileHTTP(r.Context(), w, f, w2)
			   if err != nil {
				   rerrC <- err
				   return
			   }
		   }()

		   rnd := rand.New(rand.NewSource(time.Now().UnixNano()))

		   buf := make([]byte, 4096)
		   hexBuf := make([]byte, len(buf)*2)
		   var n int64
		   var n0 int
		   for i := 0; i < 10; i++ {
			   rnd.Read(buf)
			   hex.Encode(hexBuf, buf)
			   n0, err = w2.Write(hexBuf)
			   if err != nil {
				   httpError(w, http.StatusInternalServerError)
				   return
			   }
			   n += int64(n0)
		   }
		   w2.Close()

		   rerr := <-rerrC
		   if rerr != nil {
			   t.Fatal(err)
		   }
	   }))

* 26行目で github.com/hnakamur/readwhilewrite パッケージのWriterを作って、49〜65行目でランダムなデータを16進表記で書き出しています。
* 32行目で同じファイルをオープンし、40行目でContent-Lengthレスポンスヘッダを設定し、42行目で github.com/hnakamur/readwhilewrite パッケージの SendFileHTTP 関数を呼び出してファイルをレスポンスに書き出しています。

動作確認の手順は省略しますが、テストではない単体のサンプルコードで上記と同じ確認方法で `internal/poll.SendFile()` が呼ばれていることを確認しました。

なお、この例は手抜きでリクエストを受けたときにファイルを書きつつ、別のgoroutineでファイルを読み出して配信していますが、実際の利用シーンではあるリクエストの処理でファイルを書きつつ、別のリクエストの処理でそのファイルを配信するという想定です。
