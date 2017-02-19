Title: LuaのGo実装GopherLuaを試してみた
Date: 2015-06-03 05:29
Category: blog
Tags: go, lua
Slug: blog/2015/06/03/tried_gopher_lua

## はじめに
[inforno :: LuaのGo言語実装を公開しました](http://inforno.net/articles/2015/02/15/gopher-lua-released)を以前読んでましたが、試してなかったので試しました。

[Lua: about](http://www.lua.org/about.html)の"What is Lua?"に

> making it ideal for configuration, scripting, and rapid prototyping.

とあるようにLuaは設定ファイルとして使うことも想定されています。

ということで試してみました。

## GopherLuaの利用例

hello.lua

```
print("hello")

a = 2
b = {
    c = 4,
    d = a + 3
}
```

main.go

```
package main

import (
	"fmt"

	"github.com/yuin/gopher-lua"
)

func main() {
	l := lua.NewState()
	defer l.Close()

	if err := l.DoFile("hello.lua"); err != nil {
		panic(err)
	}

	a := l.GetGlobal("a")
	fmt.Printf("a=%v\n", a)

	b := l.GetGlobal("b").(*lua.LTable)
	b.ForEach(func(key, value lua.LValue) {
		fmt.Printf("b.%v=%v\n", key, value)
	})
}
```

実行結果

```
$ go run main.go
hello
a=2
b.c=4
b.d=5
```

hello.luaに `print("hello")` を入れているのはLuaからの出力を試してみたかったからで、実際に設定ファイルとして使うときは変数設定だけの使い方になるでしょう。

上記では単に値を出力していますが、変数の値がプリミティブの場合は

* [LVAsBool](http://godoc.org/github.com/yuin/gopher-lua#LVAsBool)
* [LVAsString](http://godoc.org/github.com/yuin/gopher-lua#LVAsString)
* [LVAsNumber](http://godoc.org/github.com/yuin/gopher-lua#LVAsNumber)

を使えばbool, string, LNumberに変換できます。

[LNumberの定義](http://godoc.org/github.com/yuin/gopher-lua#LNumber) を見ると

```
type LNumber float64
```

となっているので、Goでも数値として扱えます。

なお、[Luaは5.3で数値に整数型が追加されています](http://www.lua.org/manual/5.3/manual.html#8.1)が、[gopher-lua](https://github.com/yuin/gopher-lua)はLua 5.1相当なので数値型は64bit浮動小数点数のみです。

で、table (ハッシュテーブル) 型は `lua.LValue` から `.(*lua.Table)` でTableに変換できます。

ちなみに、[2.2 – Values and Type - sLua 5.1 Reference Manual](http://www.lua.org/manual/5.1/manual.html#2.2)にあるようにLuaのtable型は連想配列と整数インデクスでの配列を兼用したデータ型となっています。

## まとめ

設定ファイルをLuaで書くようにすると、上記の hello.lua で `b.d` を `a + 3` としているように変数や式が使えます。

table型があるのでネストしたデータ構造も表現できます。

ということで、Goのプログラムの設定ファイルをluaで書いて[gopher-lua](https://github.com/yuin/gopher-lua)で解釈するというのは、かなり便利そうですね。今後活用していきたいです。yuinさん、便利なライブラリをありがとうございます！

## 2015-06-03 21:35 頃追記

作者の方からご指摘頂いたのですが、LValueからTableへの変換方法はREADMEの[Data model](https://github.com/yuin/gopher-lua#data-model)に書いてありました。失礼いたしました。

またLuaを設定ファイルとして使う場合は、そのためのライブラリも書かれているので、そちらを使うほうがよいそうです。
[inforno :: GopherLuaを設定ファイルで使うライブラリを書きました](http://inforno.net/articles/2015/03/23/gluamapper-released)をご参照ください。Goのstructの各フィールドの値をLuaのtableのデータに応じて設定してくれます。ますます便利ですね！
