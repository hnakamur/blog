Title: Go言語のos.Chtimesで設定可能な最大日時は 2262-04-11 23:47:16.854775807 +0000 UTC
Date: 2016-10-22 18:32
Modified: 2017-08-16 17:45
Category: blog
Tags: go
Slug: 2016/10/22/max-time-for-golang-os-chtimes


[os.Chtimes](https://golang.org/pkg/os/#Chtimes) のソース

* [src/os/file_posix.go - The Go Programming Language](https://golang.org/src/os/file_posix.go?s=3693:3758#L123)
* [go/file_posix.go at go1.7.3 · golang/go](https://github.com/golang/go/blob/go1.7.3/src/os/file_posix.go#L133-L141)

を見ると、引数は `time.Time` なのですが、 `syscall.Timespec` に変換するときに `time` の `UnixNano()` を使っています。 `UnixNano()` は 1970-01-01T00:00:00Z からの通算ナノ秒です。

`UnixNano()` で int64 の最大値を設定したときと、 `time.Time` で表現可能な最大の日時を調べてみました。

https://play.golang.org/p/eUj5L-eEkS

```
package main

import (
	"fmt"
	"math"
	"time"
)

func main() {
	fmt.Println(time.Unix(int64(math.MaxInt64)/1e9, int64(math.MaxInt64)%1e9).UTC())
	fmt.Println(time.Unix(math.MaxInt64, 1e9-1).UTC())
}
```

```
2262-04-11 23:47:16.854775807 +0000 UTC
219250468-12-04 15:30:07.999999999 +0000 UTC
```

となりました。

Linux amd64 環境だと [NsecToTimespec](https://github.com/golang/go/blob/go1.7.3/src/syscall/syscall_linux_amd64.go#L91-L95) と [Timespec](https://github.com/golang/go/blob/go1.7.3/src/syscall/ztypes_linux_amd64.go#L24-L27) は

```
func NsecToTimespec(nsec int64) (ts Timespec) {
	ts.Sec = nsec / 1e9
	ts.Nsec = nsec % 1e9
	return
}
```

```
type Timespec struct {
	Sec  int64
	Nsec int64
}
```

となっているので、 `NsecToTimespec` を使わずに

```
func Chtimes(name string, atime time.Time, mtime time.Time) error {
	var utimes [2]syscall.Timespec
	utimes[0] = syscall.Timespec(atime.Unix(), atime.Nanosecond())
	utimes[1] = syscall.Timespec(mtime.Unix(), mtime.Nanosecond())
	if e := syscall.UtimesNano(name, utimes[0:]); e != nil {
		return &PathError{"chtimes", name, e}
	}
	return nil
}
```

と書けば `time.Time` の限界まで渡すことは出来ます。とは言え `syscall.UtimesNano` が対応しているかはまた別問題ですが。

2262 年まで表現できれば個人的には困らないので、メモだけ残しておくということで。
