Title: Goでdeferの処理中のエラーを返す書き方を工夫してみた
Date: 2015-04-27 02:06
Category: blog
Tags: go
Slug: 2015/04/27/write_function_for_go_defer

go-nutsのメーリングリストの記事
https://groups.google.com/d/msg/golang-nuts/qTTBENO_Em0/Y4MCVZZ3c5sJ
によるとdeferで呼ばれた関数の戻り値は捨てられるそうです。
https://groups.google.com/d/msg/golang-nuts/qTTBENO_Em0/UlI77BM2PUkJ
で戻り値の変数に代入するという方法が紹介されていました。

これを参考に、deferでの後処理でエラーが起きた時はそのエラーを返す、ただし複数のエラーが起きた時は最初のエラーを返したいというときの書き方を考えてみました。

最初に書いたのは、上の記事で紹介されていたように無名関数を即時呼び出しする方式です。
https://github.com/hnakamur/cgoroonga/blob/70aafdeb2eb754505efe60afa1ae6d995831a063/examples/add_record/main.go

```
func run() (err error) {
	err = grn.Init()
	if err != nil {
		return
	}
	defer func() {
		err2 := grn.Fin()
		if err2 != nil && err == nil {
			err = err2
		}
	}()

	ctx, err := grn.CtxOpen(0)
	if err != nil {
		return
	}
	defer func() {
		err2 := ctx.Close()
		if err2 != nil && err == nil {
			err = err2
		}
	}()

	var db *grn.Obj
	db, err = ctx.DBOpenOrCreate("hello.db", nil)
	if err != nil {
		return
	}
	defer func() {
		err2 := ctx.ObjClose(db)
		if err2 != nil && err == nil {
			err = err2
		}
	}()

	keyType := ctx.At(grn.DB_SHORT_TEXT)
	table, err := ctx.TableOpenOrCreate("table1", "",
		grn.OBJ_TABLE_HASH_KEY|grn.OBJ_PERSISTENT, keyType, nil)
	if err != nil {
		return
	}
	fmt.Printf("table=%x\n", table)
	defer func() {
		err2 := ctx.ObjClose(table)
		if err2 != nil && err == nil {
			err = err2
		}
	}()
…(略)…
```

これでやりたいことは実現できているのですが、deferのところの行数が多すぎて読みにくいコードになっています。

そこでこの部分を関数として定義するようにしてみました。

https://github.com/hnakamur/cgoroonga/blob/5eb6e092c4f6d53257b499cffacd51b8dd194ca3/examples/add_record/main.go

```
func run() (err error) {
	err = grn.Init()
	if err != nil {
		return
	}
	defer grn.FinDefer(&err)

	ctx, err := grn.CtxOpen(0)
	if err != nil {
		return
	}
	defer ctx.CloseDefer(&err)

	var db *grn.Obj
	db, err = ctx.DBOpenOrCreate("hello.db", nil)
	if err != nil {
		return
	}
	defer ctx.ObjCloseDefer(&err, db)

	keyType := ctx.At(grn.DB_SHORT_TEXT)
	table, err := ctx.TableOpenOrCreate("table1", "",
		grn.OBJ_TABLE_HASH_KEY|grn.OBJ_PERSISTENT, keyType, nil)
	if err != nil {
		return
	}
	fmt.Printf("table=%x\n", table)
	defer ctx.ObjCloseDefer(&err, table)
…(略)…
```

関数定義は例えば `FinDefer` なら
https://github.com/hnakamur/cgoroonga/blob/master/init.go#L25-L30

```
func FinDefer(err *error) {
	err2 := Fin()
	if err2 != nil && *err == nil {
		*err = err2
	}
}
```

のようになります。他の関数も同様です。

書き換えた `run()` のほうが読みやすくていい感じです。
