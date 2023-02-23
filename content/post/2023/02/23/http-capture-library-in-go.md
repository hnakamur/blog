---
title: "GoでHTTPの通信をキャプチャーするライブラリを書いた"
date: 2023-02-23T18:04:15+09:00
---

## はじめに

[Apache Traffic Server](https://trafficserver.apache.org/)の挙動を調べるときに、tcpdumpでパケットをキャプチャすることがあります。
アクセスログを見るだけだと、upstreamへのアクセスが失敗してリトライするようなケースでもログは1件しか出ないのですが、パケットのログを見れば全てのHTTPリクエストとレスポンスが見られて便利です。
私は以下のようなスクリプトを使っています(対象のポートは適宜調整)。

```bash
#!/bin/bash
set -eu
log_basename=tcpdump-$(hostname)-$(date +%Y%m%d-%H%M%S)
tcpdump -i any -U -w ${log_basename}.dat tcp port '(80 or 8080)'
tcpdump -A -n -vvv -r ${log_basename}.dat > ${log_basename}.log
```
通信を行う前にこのスクリプトを実行しておいて、通信後 Ctrl-C を押すと1つめのtcpdumpが終了して、2つめのtcpdumpでバイナリのデータファイルをテキストに変換します。

ただ、tcpdumpはあくまでTCPのレベルなので、HTTPのリクエストとレスポンスを対応して表示してくれるわけではありません。
IPアドレスとポートの組み合わせを見て人間が対応付けて見る必要があります。

[github.com/google/gopacket](https://pkg.go.dev/github.com/google/gopacket)というライブラリを以前見かけて気になっていたのですが、今回試してみたのでメモです。
作ったライブラリは[hnakamur/httpcapt](https://github.com/hnakamur/httpcapt)に置きました。

## github.com/google/gopacket について

ネットワークデバイスからキャプチャーする部分は[github.com/google/gopacket/pcap](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcap)と[github.com/google/gopacket/pcapgo](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcapgo)という2つのサブパッケージが利用可能です。

[github.com/google/gopacket/pcap](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcap)はLinuxだとlibpcapとCgoを使います。
[github.com/google/gopacket/pcapgo](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcapgo)はLinuxのみ対応ですが pure Go で実装されています。

## パケットのデータをHTTPリクエストとレスポンスに変換

[examples](https://github.com/google/gopacket/tree/master/examples)ディレクトリの[gopacket/main.go](https://github.com/google/gopacket/blob/master/examples/httpassembly/main.go)にパケットのデータをHTTPリクエストに変換する例があります。今回のライブラリはこれを参考に発展させて作りました。

[net/http](https://pkg.go.dev/net/http@go1.20.1)の[ReadRequest](https://pkg.go.dev/net/http@go1.20.1#ReadRequest)でHTTPリクエストのヘッダまでを読み込んでいます。ドキュメントにHTTP/1.1のみ対応とあり、HTTP/2は[golang.org/x/net/http2](https://pkg.go.dev/golang.org/x/net/http2)を使えと書かれていました。が、私の用途ではとりあえずHTTP/1.1のみで十分です。

[ReadRequest](https://pkg.go.dev/net/http@go1.20.1#ReadRequest)で返される[Request](https://pkg.go.dev/net/http@go1.20.1#Request)のBodyはパケットデータのReaderを指すようになっているので最後まで読み取る必要があります。上記のサンプルはtcpreader.DiscardBytesToEOF](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/tcpassembly/tcpreader#DiscardBytesToEOF)でEOFまで読み捨てています。

が、私はボディの内容も参照したいので[io.ReadAll](https://pkg.go.dev/io@go1.20.1#ReadAll)で最後まで読み取って、`io.NopCloser(bufio.NewReader(data))`でReadCloserを作ってBodyを上書きしています。これは[net/http/httptest.ResponseRecorder.Result](https://pkg.go.dev/net/http/httptest@go1.20.1#ResponseRecorder.Result)メソッドの[実装](https://cs.opensource.google/go/go/+/refs/tags/go1.20.1:src/net/http/httptest/recorder.go;l=201)で見たコードを真似しました。

なお、ボディ全体をメモリ上に持つので巨大な場合は良くないのですが、このライブラリは私は自動テストで使う想定でそこまで大きなボディは扱わないので大丈夫です。

レスポンスは[ReadResponse](https://pkg.go.dev/net/http@go1.20.1#ReadResponse)メソッド
```go
func ReadResponse(r *bufio.Reader, req *Request) (*Response, error)
```
を使い、ボディはリクエストと同様に最後まで読み取ってBodyにセットしています。

[引数のreqはResponseのRequestフィールドに設定されます](https://cs.opensource.google/go/go/+/refs/tags/go1.20.1:src/net/http/response.go;l=157)。

[httpStreamFactory.New](https://github.com/hnakamur/httpcapt/blob/8e0a85300f10c374ae6725fb13b9c7f1272ac66b/http_stream.go#L48)メソッド
```go
func (f *httpStreamFactory) New(net, transport gopacket.Flow) tcpassembly.Stream
```
の`net.Src()`で送信元のIPアドレス、`transport.Src()`で送信元のポート、`net.Dst()`で送信先のIPアドレス、`transport.Dst()`で送信先のポートが分かるので、これを
[addrPortPair](https://github.com/hnakamur/httpcapt/blob/8e0a85300f10c374ae6725fb13b9c7f1272ac66b/http_stream.go#L194-L197)に変換し、それをキーにしたmapにリクエストを保管しておきます。
```go
type addrPortPair struct {
	src netip.AddrPort
	dst netip.AddrPort
}
```
レスポンスをデコードするときに、送信元と送信先を逆にしたキーでリクエストを取得してそれを[ReadResponse](https://pkg.go.dev/net/http@go1.20.1#ReadResponse)メソッドのreq引数に渡しています。

## bpfのフィルタのコンパイル

bpfのフィルタは冒頭のスクリプトの `tcp port '(80 or 8080)'` のような文字列です。

[github.com/google/gopacket/pcap](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcap)のほうは[Handle.SetBPFFilter](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcap#Handle.SetBPFFilter)メソッド
```go
func (p *Handle) SetBPFFilter(expr string) (err error)
```
にフィルタ文字列をそのまま渡せます。

一方、[github.com/google/gopacket/pcapgo](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcapgo)の[EthernetHandle.SetBPF](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcapgo#EthernetHandle.SetBPF)メソッドは
```go
func (h *EthernetHandle) SetBPF(filter []bpf.RawInstruction) error
```
のように[golang.org/x/net/bpf](https://pkg.go.dev/golang.org/x/net/bpf)の[RawInstruction](https://pkg.go.dev/golang.org/x/net/bpf#RawInstruction)構造体のスライスを渡す必要があります。

これは困ったと思ったら[github.com/packetcap/go-pcap](https://pkg.go.dev/github.com/packetcap/go-pcap)の[filter](https://pkg.go.dev/github.com/packetcap/go-pcap@v0.0.0-20221020071412-2b2e94010282/filter)パッケージでフィルタ文字列を[golang.org/x/net/bpf.Instruction](https://pkg.go.dev/golang.org/x/net/bpf#Instruction)インタフェースのスライスに変換できることがわかりました。そこから[golang.org/x/net/bpf.Assemble](https://pkg.go.dev/golang.org/x/net/bpf#Assemble)関数で[RawInstruction](https://pkg.go.dev/golang.org/x/net/bpf#RawInstruction)構造体のスライスに変換できます。

## go:buildタグでCgoありとなしで実装を切り替え

Cgoありのタグを`//go:build Cgo`、Linuxでpure Goのタグを`//go:build linux && !Cgo`とし、それぞれで実装ファイルを分けて切り替えるようにしました(ビルドタグの詳細は[Build constraints](https://pkg.go.dev/cmd/go#hdr-Build_constraints)参照)。

## サンプルCLIの実行例

事前に80番ポートでHTTPサーバが稼働中という前提とします。
[README.md](https://github.com/hnakamur/httpcapt/blob/main/README.md)の手順でインストールした後、以下のコマンドで起動します。

```
$ sudo httpcapt
```

別端末でcurlを実行します。
```
$ curl -v -X GET -d 'Hi, this is request body!' 'http://localhost?a=1'
*   Trying 127.0.0.1:80...
* Connected to localhost (127.0.0.1) port 80 (#0)
> GET /?a=1 HTTP/1.1
> Host: localhost
> User-Agent: curl/7.81.0
> Accept: */*
> Content-Length: 25
> Content-Type: application/x-www-form-urlencoded
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Server: nginx/1.23.3
< Date: Thu, 23 Feb 2023 11:18:04 GMT
< Content-Type: text/plain
< Connection: keep-alive
< content-length: 40
<
Welcome to localhost, request_uri=/?a=1
* Connection #0 to host localhost left intact
```

httpcaptの端末には以下のようなログが出力されます。
```
2023/02/23 20:18:04 result: reqTime=2023-02-23 20:18:04.36914 +0900 JST, respTime=2023-02-23 20:18:04.369369 +0900 JST, client=127.0.0.1:44594, server=127.0.0.1:80, request=&{Method:GET URL:/?a=1 Proto:HTTP/1.1 ProtoMajor:1 ProtoMinor:1 Header:map[Accept:[*/*] Content-Length:[25] Content-Type:[application/x-www-form-urlencoded] User-Agent:[curl/7.81.0]] Body:{Reader:0xc00021e090} GetBody:<nil> ContentLength:25 TransferEncoding:[] Close:false Host:localhost Form:map[] PostForm:map[] MultipartForm:<nil> Trailer:map[] RemoteAddr: RequestURI:/?a=1 TLS:<nil> Cancel:<nil> Response:<nil> ctx:<nil>}, requestBody=Hi, this is request body!, response=&{Status:200 OK StatusCode:200 Proto:HTTP/1.1 ProtoMajor:1 ProtoMinor:1 Header:map[Connection:[keep-alive] Content-Length:[40] Content-Type:[text/plain] Date:[Thu, 23 Feb 2023 11:18:04 GMT] Server:[nginx/1.23.3]] Body:{Reader:0xc00021e0f0} ContentLength:40 TransferEncoding:[] Close:false Uncompressed:false Trailer:map[] Request:0xc000220000 TLS:<nil>}, responseBody=Welcome to localhost, request_uri=/?a=1
```

httpcatの端末でCtrl-Cを押すと終了します。
```
^C2023/02/23 20:18:06 context canceled
```

## 特殊なデバイス名anyの扱い

`tcpdump`の`-i`オプションや[github.com/google/gopacket/pcap](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcap)の[OpenLive](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcap#OpenLive)関数
```go
func OpenLive(device string, snaplen int32, promisc bool, timeout time.Duration) (*Handle, error)
```
のdevice引数では特殊なデバイス名として`any`を指定すると、ホスト上の全てのデバイスがキャプチャ対象になります。

一方、[github.com/google/gopacket/pcapgo](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcapgo)の[NewEthernetHandle](https://pkg.go.dev/github.com/google/gopacket@v1.1.19/pcapgo#NewEthernetHandle)関数
```go
func NewEthernetHandle(ifname string) (*EthernetHandle, error)
```
のifname引数は`any`には対応していません。

そこでラップしたAPIのほうでpure Goの実装では`any`の場合は[net.Interfaces](https://pkg.go.dev/net@go1.20.1#Interfaces)関数でホスト上の全てのデバイス一覧を取得して内部的に複数の`EthernetHandle`を作って対応するようにしました。

今回のライブラリのサンプルCLIも`-i`オプションでデバイス名を指定しますが、Cgo版と pure Go 版ともにanyに対応しており、デフォルト値もanyとしています。

## (横道) 自ホストのIPアドレスを指定した場合もloデバイスを通る

通常はデバイス名anyですべてのデバイスの通信をキャプチャーする想定なので気にする必要はないのですが、実装中に気付いたのでメモです。

```
$ ip -br -4 a s dev lo; ip -br -4 a s dev enp1s0f1
lo               UNKNOWN        127.0.0.1/8
enp1s0f1         UP             192.168.2.3/24
```

という環境で試していたのですが、curlのURLを`http://192.168.2.3`と指定した場合、HTTPサーバと同じマシン上で実行するとCLIで`-i lo`としたときはキャプチャーできますが`-i enp1s0f1`としたときはキャプチャーできませんでした。知っている方には当然なのでしょうが、知らなかった私には意外でした。

一方別のマシンからアクセスする場合は`-i lo`ではキャプチャーできず`-i enp1s0f1`ならキャプチャーできました(これは普通)。

私の用途だと同じサーバと別のサーバからの両方のリクエストをキャプチャーしたいので、複数のデバイスを指定する必要があります。またデバイス名はコンテナならだいたいeth0でしょうけど、物理マシンだと環境ごとに異なります。いちいち調べて指定するのは面倒なのでデバイス名にanyを指定して全てのデバイスを見てくれると便利です。

キャプチャーを実行したいLinuxマシンにlibpcapをインストールしたくない場合もあるかもしれないので、pure Goでも全てデバイスを見てくれるのが理想です。そこで前項のように実装したというわけでした。

## 「深いモジュール」になるよう心掛けた

しばらく前に https://twitter.com/thorstenball/status/1624465909816467459 のツイートを見て[Favorite Sayings](https://web.stanford.edu/~ouster/cgi-bin/sayings.php)を読んで良いなと思い、 https://twitter.com/og_fhools/status/1624466123969433602 のツイートも見て [Software Design Book](https://web.stanford.edu/~ouster/cgi-bin/book.php) を見て [Amazon.co.jp: A Philosophy of Software Design, 2nd Edition (English Edition) 電子書籍: Ousterhout, John K. : 洋書](https://www.amazon.co.jp/dp/B09B8LFKQL/) を買って読みました。こちらも素晴らしいと思いました。

本の中で Modules Should Be Deep という章があり、浅いモジュールより深いモジュールが良いという話があったので、今回はそれを心掛けてAPIを設計してみました。
