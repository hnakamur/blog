Title: Go言語用のメモリマップトファイルのライブラリを探してみた
Date: 2015-06-03 06:29
Category: blog
Tags: go, mmap
Slug: 2015/06/03/go_mmap_libraries

ふとGo言語でメモリマップトファイルを扱えるライブラリってあるのかなと気になったので探してみました。

## 標準ライブラリ

[Goのホームページ](http://golang.org/)で[mmapで検索してみる](http://golang.org/search?q=mmap)とUnix系では実装があるみたいです。

Did you mean: [Mmap](http://golang.org/search?q=Mmap) と表示されているのでクリックしてみるとsyscallパッケージに[Mmap](http://golang.org/pkg/syscall/#Mmap)があることがわかりました。

[Munmapで検索してみる](http://golang.org/search?q=Munmap)とこちらはMmapよりは実装されているOSが少ないです。syscallパッケージに[Mummap](http://golang.org/pkg/syscall/#Munmap)もあります。

[Msyncで検索してみる](http://golang.org/search?q=Msync)と5件ヒットしますが、未実装となっていました。

また、syscallパッケージにMmapとMunmapがあるといっても、Windowsでは実装されていません。

## github.com/edsrzf/mmap-go

* ソース: [edsrzf/mmap-go](https://github.com/edsrzf/mmap-go)
* GoDoc:  [mmap - GoDoc](https://godoc.org/github.com/edsrzf/mmap-go)
* ライセンス: 3項BSD

[README](https://github.com/edsrzf/mmap-go)によるとポータブルなAPIで、Linux (386, amd64), OS X, Windows (386)でテスト済みとのことです。

mprotect, mincoreなどはサポートしていないのでそういうUnix特有の機能を使いたい場合はGustavo Niemeyerさんの[gommap](http://labix.org/gommap)がおすすめとのことです。

## github.com/tysontate/gommap

Gustavo Niemeyerさんの[gommap](http://labix.org/gommap)はプロジェクトがlaunchpat.netにホスティングされているので、github.comにミラーリングされていないかなと調べると[tysontate/gommap](https://github.com/tysontate/gommap)がありました。

READMEによるとOS X用のパッチも適用済みとのことです。 `mmap_*.go` のファイル名から判断すると対応OSはLinux (386, amd64), OS Xのようです。

## まとめ

[edsrzf/mmap-go](https://github.com/edsrzf/mmap-go)の機能で足りる場合はそちらを、Unix限定になってもいいからmprotectとかを使いたい場合は[tysontate/gommap](https://github.com/tysontate/gommap)を使うのがよさそうです。
