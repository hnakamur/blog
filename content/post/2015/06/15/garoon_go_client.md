Title: Cybozu Garoon APIのファイル管理の部分だけのgoライブラリを書いた
Date: 2015-06-15 20:24
Category: blog
Tags: go, xml
Slug: 2015/06/15/garoon_go_client

# はじめに
Cybozu [Garoon API](https://cybozudev.zendesk.com/hc/ja/categories/200157760-Garoon-API)のファイル管理のうち、フォルダ一覧取得、フォルダ内のファイル一覧取得、ファイルダウンロードのAPIを呼び出すライブラリをGoで書いてみました。

ただし、汎用的なライブラリではなく、自分が必要な機能のみを実装しています。レスポンスの中の項目も自分が必要な部分だけ取り出して残りは破棄しています。
[sigbus.info: コードを書くことは無限の可能性を捨てて一つのやり方を選ぶということ](http://blog.sigbus.info/2015/01/p1.html)を読んでから、汎用性をあまり気にせず自分の用途に合わせて書くようになって楽で良いです。

# 実装方法についてのメモ
まず、Garoon APIの手動での呼び出し方は[garoon - Cybozu ガルーン API を使ってみる - Qiita](http://qiita.com/yamasaki-masahide/items/fff1c84e65043ac4caf7)を参考にして試してみました。

## リクエストのXML組み立て
Garoon APIはSOAPなので、リクエストやレスポンスはXMLになります。

リクエストを送るところは[Cybozu ガルーン API を golang で叩いてみる - Qiita](http://qiita.com/yamasaki-masahide/items/03dfa6cd70ff20607b58)を見たのですが、[Goのencoding/xmlを使いこなす - Qiita](http://qiita.com/ono_matope/items/70080cc33b75152c5c2a)を参考にMarshalXMLを実装する方式にしてみました。

[xml.Marshaler](http://golang.org/pkg/encoding/xml/#Marshaler)の `MarshalXML(e *Encoder, start StartElement) error` は `start` をエンコードするのが本来の使い方だとは思うのですが、下記の例のように `CabinetGetFolderInfo` といったリクエスト本体を渡すと `soap:Envelope` でラップしてエンコードしてくれる方が使うときに楽なので、 `MarshalXML` 内でデータ構造を組み立ててエンコードするようにしてみました。

```
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Header>
    <Action>CabinetGetFolderInfo</Action>
    <Security>
      <UsernameToken>
        <Username>foo</Username>
        <Password>password</Password>
      </UsernameToken>
    </Security>
    <Timestamp>
      <Created>2010-08-12T14:45:00Z</Created>
      <Expires>2037-08-12T14:45:00Z</Expires>
    </Timestamp>
    <Locale>jp</Locale>
  </soap:Header>
  <soap:Body>
    <CabinetGetFolderInfo>
      <parameters></parameters>
    </CabinetGetFolderInfo>
  </soap:Body>
</soap:Envelope>
```

`soap:Envelope` でラップした構造を作るところは、

https://github.com/hnakamur/garoonclient/blob/d8aceb8ae09c6094dd65a1623fc99ca89a1ccebd/request.go#L44-L62

```

func buildRequestStruct(h RequestHeader, apiName string, parameters interface{}) envelope {
	return envelope{
		Xmlns: "http://www.w3.org/2003/05/soap-envelope",
		Header: header{
			Action:   apiName,
			Username: h.Username,
			Password: h.Password,
			Created:  h.Created,
			Expires:  h.Expires,
			Locale:   h.Locale,
		},
		Body: body{
			Content: bodyContent{
				XMLName:    xml.Name{Local: apiName},
				Parameters: parameters,
			},
		},
	}
}
```

で共通処理として実装し、各API用のリクエストの構造体では

https://github.com/hnakamur/garoonclient/blob/d8aceb8ae09c6094dd65a1623fc99ca89a1ccebd/cabinet.go#L16-L26

```
type CabinetGetFolderInfoRequest struct {
	Header RequestHeader
}

func (r CabinetGetFolderInfoRequest) MarshalXML(e *xml.Encoder, start xml.StartElement) error {
	return e.Encode(buildRequestStruct(
		r.Header,
		"CabinetGetFolderInfo",
		struct{}{},
	))
}
```

のようにして呼び出しています。

また、日時の項目は構造体側では `time.Time` にしたいところですが、[Issue 2771 - go - encoding/xml: MarshalXML interface is not good enough - The Go Programming Language - Google Project Hosting](https://code.google.com/p/go/issues/detail?id=2771#c2)の[コメント#2](https://code.google.com/p/go/issues/detail?id=2771#c2)を読んで `string` にしました。

## レスポンスのパース処理
レスポンスのパースは[Cybozu ガルーン API のレスポンスのXMLを golang でパースする - Qiita](http://qiita.com/yamasaki-masahide/items/f20a2ca4700e00777303)を見たのですが、[Parsing huge XML files with Go - david singleton](http://blog.davidsingleton.org/parsing-huge-xml-files-with-go/)の方法のほうが楽なのでこちらを参考にしました。

共通のユーテリティ関数としては
https://github.com/hnakamur/garoonclient/blob/d8aceb8ae09c6094dd65a1623fc99ca89a1ccebd/response.go

```
var ResponseTagNotFoundError = errors.New("response tag not found")

func parseResponse(r io.Reader, localName string, v interface{}) error {
	decoder := xml.NewDecoder(r)
	for {
		t, _ := decoder.Token()
		if t == nil {
			break
		}
		switch se := t.(type) {
		case xml.StartElement:
			if se.Name.Local == localName {
				return decoder.DecodeElement(v, &se)
			}
		}
	}
	return ResponseTagNotFoundError
}
```

のように定義して、

https://github.com/hnakamur/garoonclient/blob/d8aceb8ae09c6094dd65a1623fc99ca89a1ccebd/cabinet.go#L115-L127

```
func parseCabinetGetFolderInfoResponse(r io.Reader) (*CabinetGetFolderInfoResponse, error) {
	exclude := NewExclude(func(b byte) bool {
		return b == 0x08 || b == 0x0B
	})
	r2 := transform.NewReader(r, exclude)
	var resp CabinetGetFolderInfoResponse
	err := parseResponse(r2, "CabinetGetFolderInfoResponse", &resp)
	if err != nil {
		return nil, err
	}
	resp.fillPath()
	return &resp, err
}
```

という感じで呼び出しています。

## レスポンスからU+0008などの制御文字を除去
あと、レスポンスのXMLをそのまま[xml.Decoder](http://golang.org/pkg/encoding/xml/#Decoder)に渡すとUTF-8の不正なバイト列といったエラーが出ました。U+0008やU+000Bというデータが入っていたので、これを除去するようにしました。

日本語の文字コード変換用のライブラリ[golang.org/x/text/encoding/japanese](https://godoc.org/golang.org/x/text/encoding/japanese)で使っているインターフェース[golang.org/x/text/transform/Transformer](https://godoc.org/golang.org/x/text/transform#Transformer)に合わせて実装しました。

https://github.com/hnakamur/garoonclient/blob/d8aceb8ae09c6094dd65a1623fc99ca89a1ccebd/cabinet.go#L28-L50

```
type exclude struct {
	transform.NopResetter
	excluder func(byte) bool
}

func NewExclude(excluder func(byte) bool) transform.Transformer {
	return exclude{excluder: excluder}
}

func (e exclude) Transform(dst, src []byte, atEOF bool) (nDst, nSrc int, err error) {
	for nSrc = 0; nSrc < len(src); nSrc++ {
		b := src[nSrc]
		if !e.excluder(b) {
			if nDst >= len(dst) {
				err = transform.ErrShortDst
				return
			}
			dst[nDst] = b
			nDst++
		}
	}
	return
}
```

利用するときは[golang.org/x/text/transform/NewReader](https://godoc.org/golang.org/x/text/transform#NewReader)を使います。

# まとめ
Cybozu Garoon APIの一部のクライアントライブラリをGoで実装しました。

* MarshalXMLを実装することで、構造体とXMLの構造がかなり違う場合でも、XMLに合わせて一々構造体を定義することなく楽に対応出来ました。
* [xml.DecoderのToken](http://golang.org/pkg/encoding/xml/#Decoder.Token)を使うことでXMLの一部だけをパースしました。
* 制御文字除去の処理を[golang.org/x/text/transform/Transformer](https://godoc.org/golang.org/x/text/transform#Transformer)インタフェースに合わせて実装しました。
