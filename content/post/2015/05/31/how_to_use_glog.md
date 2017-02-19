Title: goでglogを使うときのメモ
Date: 2015-05-31 02:30
Category: blog
Tags: go, logging
Slug: 2015/05/31/how_to_use_glog

[go言語におけるロギングについて](http://blog.satotaichi.info/logging-frameworks-for-go/)の記事と[glog - GoDoc](http://godoc.org/github.com/golang/glog)を読んで試してみました。

`flag.Parse()` を呼ぶ必要があり、最後に `glog.Flush()` を呼ぶ必要があるので `main` で `defer` で書いておきます。

```
package main

import (
	"flag"

	"github.com/golang/glog"
)

func main() {
	flag.Parse()
	defer glog.Flush()

	if glog.V(0) {
		glog.Info("Hello, glog")
	}

	glog.V(0).Info("exiting")
}
```

ログレベルは `-v` オプションで指定できるのですがデフォルト値は0なので、デフォルトで出力したいログはレベル0で書くようにします。

[Verbose](http://godoc.org/github.com/golang/glog#Verbose)の説明によると、上の2つの書き方では前者のほうが実行時負荷が安上がりとのことです。これはログレベルの設定で出力を抑止した時に、 `Info` の引数の評価をしなくて済むからです。

使い分けるのも面倒なので、常に前者を使うことにします。

ログファイル名は非公開関数 [glog.logName()](https://github.com/golang/glog/blob/44145f04b68cf362d9c4df2182967c2275eaefed/glog_file.go#L83-L97) の形式になります。

ログのディレクトリは `-log_dir` オプションで指定可能ですが、デフォルトでは [os.TempDir()](http://golang.org/pkg/os/#TempDir) になっています。

OS Xの場合は環境変数 `$TMPDIR` になります。セキュリティ上 `/tmp` ではなくランダムは文字列のディレクトリになっています。

```
$ echo $TMPDIR
/var/folders/9p/r7jylfyd163bszlxvp0wk36h0000gn/T/
```

ということで、ログファイルを見るときは `less $TMPDIR/${プログラム名}.INFO` とすればOKです。`go build` でビルドしてプログラムを実行した時はその名前ですが、 `go run main.go` のときは `main` になるようで `$TMPDIR/main.INFO` というファイルが出来ていました。

このファイルはプログラム実行のたびに上書きされます。過去のログを見たいときは `less $TMPDIR/${プログラム名}` まで入力しTABでファイル名補完して見るようにします。

上記のサンプルで出力されたログは以下のようになっていました。

```
Log file created at: 2015/05/31 02:22:07
Running on machine: sunshine5
Binary: Built with gc go1.4.2 for darwin/amd64
Log line format: [IWEF]mmdd hh:mm:ss.uuuuuu threadid file:line] msg
I0531 02:22:07.343002   54353 main.go:14] Hello, glog
I0531 02:22:07.343897   54353 main.go:18] exiting
```

ログの行フォーマットは4行目に書いてありますが、 [glog.header()のコメント](https://github.com/golang/glog/blob/44145f04b68cf362d9c4df2182967c2275eaefed/glog.go#L518-L534) に詳細な説明があります。

各行の日付には年がないのですが、行のフォーマットは固定なので諦めましょう。ログファイルサイズ削減のために年は付けないようにしているのでしょう。先頭行に作成日時が年つきで書いてあるのでそちらを見れば良いです。

スレッドIDやログ出力したファイル名と行番号が出るのが便利です。

ということで開発時のデバッグログとしてはglog便利そうです。逆にシステムの運用ログとしては別のログライブラリのようが良いかもしれません。
