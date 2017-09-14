Goのプロファイラを使ってメモリ割り当て回数を減らす
##################################################

:date: 2017-09-14 22:30
:tags: go, profiler
:category: blog
:slug: 2017/09/14/reduce-memory-allocations-using-go-profiler

はじめに
--------

Goのプロファイラを使ってメモリ割り当て回数を減らすように自分のプログラムを改善するのを試してみたのでメモです。

参考資料
--------

プロファイラの基本的な使い方の公式ブログ記事。

* `Profiling Go Programs - The Go Blog <https://blog.golang.org/profiling-go-programs>`_


プロファイラを使って最適化する説明動画とスライド。

* `Profiling & Optimizing in Go / Brad Fitzpatrick - YouTube <https://www.youtube.com/watch?v=xxDZuPEgbBU&feature=youtu.be>`_

    * `talk-yapc-asia-2015/talk.md <https://github.com/bradfitz/talk-yapc-asia-2015/blob/master/talk.md>`_


pprofをプロダクションのコードに使ってメモリーリークを見つける方法の説明動画。

* `Finding Memory Leaks in Go Programs - Oleg Shaldybin - YouTube <https://www.youtube.com/watch?v=ydWFpcoYraU>`_

サンプルプログラム
------------------

Linux で :code:`/proc/loadavg` からロードアベレージの値を読み取るプログラムを書いて試してみました。

:code:`~/go/src/github.com/hnakamur/systat` というディレクトリを作って、以下の2つのファイルを作成します。

:code:`loadavg.go`

.. code-block:: go

	package sysstat

	import (
		"os"
		"strconv"
		"strings"
	)

	// LoadAvg represents load averages for 1 minute, 5 minutes, and 15 minutes.
	type LoadAvg struct {
		Load1  float64
		Load5  float64
		Load15 float64
	}

	// ReadLoadAvg read the load average values.
	func ReadLoadAvg(a *LoadAvg) error {
		file, err := os.Open("/proc/loadavg")
		if err != nil {
			return err
		}
		defer file.Close()

		var buf [80]byte
		n, err := file.Read(buf[:])
		if err != nil {
			return err
		}
		return parseLoadAvg(string(buf[:n]), a)
	}

	func parseLoadAvg(b string, a *LoadAvg) error {
		fields := strings.Fields(b)
		load1, err := strconv.ParseFloat(fields[0], 64)
		if err != nil {
			return err
		}

		load5, err := strconv.ParseFloat(fields[1], 64)
		if err != nil {
			return err
		}

		load15, err := strconv.ParseFloat(fields[2], 64)
		if err != nil {
			return err
		}

		a.Load1 = load1
		a.Load5 = load5
		a.Load15 = load15
		return nil
	}

:code:`loadavg_test.go`

.. code-block:: go

	package sysstat

	import "testing"

	func TestParseLoadAvg(t *testing.T) {
		var a LoadAvg
		line := "1.31 1.39 1.43 2/1081 24188\n"
		err := parseLoadAvg(line, &a)
		if err != nil {
			t.Fatal(err)
		}
		if a.Load1 != 1.31 {
			t.Errorf("Load1 unmatch, got=%g, want=%g", a.Load1, 1.31)
		}
		if a.Load5 != 1.39 {
			t.Errorf("Load5 unmatch, got=%g, want=%g", a.Load5, 1.39)
		}
		if a.Load15 != 1.43 {
			t.Errorf("Load15 unmatch, got=%g, want=%g", a.Load15, 1.43)
		}
	}

	func BenchmarkReadLoadAvg(b *testing.B) {
		var a LoadAvg
		for i := 0; i < b.N; i++ {
			err := ReadLoadAvg(&a)
			if err != nil {
				b.Fatal(err)
			}
		}
	}

:code:`~/go/src/github.com/hnakamur/systat` ディレクトリで以下のコマンドを実行し、テストが通ることを確認します。

.. code-block:: console

	$ go test -v
	=== RUN   TestParseLoadAvg
	--- PASS: TestParseLoadAvg (0.00s)
	PASS
	ok      github.com/hnakamur/sysstat     0.001s

初回のベンチマーク
------------------

.. code-block:: console

	$ go test -count=10 -run=NONE -bench=. -benchmem -memprofile=loadavg.0.mprof -cpuprofile=loadavg.0.cprof | tee loadavg.0.bench
	goos: linux
	goarch: amd64
	pkg: github.com/hnakamur/sysstat
	BenchmarkReadLoadAvg-2   	  200000	      9378 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9381 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9404 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9370 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9372 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9369 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9348 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9450 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9438 ns/op	     216 B/op	       5 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      9429 ns/op	     216 B/op	       5 allocs/op
	PASS
	ok  	github.com/hnakamur/sysstat	19.925s

メモリ割り当て量が多い箇所の確認
--------------------------------

:code:`go tool pprof` に :code:`--alloc_space` オプションを指定して起動するとメモリ割り当て量を調べられます。
起動すると :code:`(pprof)` というプロンプトが表示されます。

.. code-block:: console

	$ go tool pprof --alloc_space sysstat.test loadavg.0.mprof
	File: sysstat.test
	Type: alloc_space
	Time: Sep 14, 2017 at 10:55am (JST)
	Entering interactive mode (type "help" for commands, "o" for options)
	(pprof)

:code:`top` コマンドを実行すると、メモリ割り当て量が多かった top 10 のソースコードの箇所が表示されます。

.. code-block:: console

	(pprof) top
	Showing nodes accounting for 420.03MB, 99.38% of 422.63MB total
	Dropped 14 nodes (cum <= 2.11MB)
	Showing top 10 nodes out of 13
		  flat  flat%   sum%        cum   cum%
	  174.01MB 41.17% 41.17%   174.01MB 41.17%  os.newFile /usr/lib/go-1.9/src/os/file_unix.go
	  154.51MB 36.56% 77.73%   154.51MB 36.56%  strings.Fields /usr/lib/go-1.9/src/strings/strings.go
	   60.50MB 14.32% 92.05%   420.03MB 99.38%  github.com/hnakamur/sysstat.ReadLoadAvg /home/hnakamur/go/src/github.com/hnakamur/sysstat/loadavg.go
		  31MB  7.34% 99.38%       31MB  7.34%  syscall.ByteSliceFromString /usr/lib/go-1.9/src/syscall/syscall.go
			 0     0% 99.38%   420.03MB 99.38%  github.com/hnakamur/sysstat.BenchmarkReadLoadAvg /home/hnakamur/go/src/github.com/hnakamur/sysstat/loadavg_test.go
			 0     0% 99.38%   154.51MB 36.56%  github.com/hnakamur/sysstat.parseLoadAvg /home/hnakamur/go/src/github.com/hnakamur/sysstat/loadavg.go
			 0     0% 99.38%   205.01MB 48.51%  os.Open /usr/lib/go-1.9/src/os/file.go
			 0     0% 99.38%   205.01MB 48.51%  os.OpenFile /usr/lib/go-1.9/src/os/file_unix.go
			 0     0% 99.38%       31MB  7.34%  syscall.BytePtrFromString /usr/lib/go-1.9/src/syscall/syscall.go
			 0     0% 99.38%       31MB  7.34%  syscall.Open /usr/lib/go-1.9/src/syscall/syscall_linux.go


メモリ割り当て回数が多い箇所の確認
----------------------------------

Ctrl-D を押して抜けて、今度は :code:`go tool pprof` に :code:`--alloc_objects` オプションを指定して起動し、 :code:`top` コマンドを実行して、メモリ割り当て回数の top 10 を確認します。

.. code-block:: console

	$ go tool pprof --alloc_objects sysstat.test loadavg.0.mprof
	File: sysstat.test
	Type: alloc_objects
	Time: Sep 14, 2017 at 10:55am (JST)
	Entering interactive mode (type "help" for commands, "o" for options)
	(pprof) top
	Showing nodes accounting for 9853756, 100% of 9853762 total
	Dropped 14 nodes (cum <= 49268)
	Showing top 10 nodes out of 13
		  flat  flat%   sum%        cum   cum%
	   3814369 38.71% 38.71%    3814369 38.71%  os.newFile /usr/lib/go-1.9/src/os/file_unix.go
	   2031647 20.62% 59.33%    2031647 20.62%  syscall.ByteSliceFromString /usr/lib/go-1.9/src/syscall/syscall.go
	   2025216 20.55% 79.88%    2025216 20.55%  strings.Fields /usr/lib/go-1.9/src/strings/strings.go
	   1982524 20.12%   100%    9853756   100%  github.com/hnakamur/sysstat.ReadLoadAvg /home/hnakamur/go/src/github.com/hnakamur/sysstat/loadavg.go
			 0     0%   100%    9853756   100%  github.com/hnakamur/sysstat.BenchmarkReadLoadAvg /home/hnakamur/go/src/github.com/hnakamur/sysstat/loadavg_test.go
			 0     0%   100%    2025216 20.55%  github.com/hnakamur/sysstat.parseLoadAvg /home/hnakamur/go/src/github.com/hnakamur/sysstat/loadavg.go
			 0     0%   100%    5846016 59.33%  os.Open /usr/lib/go-1.9/src/os/file.go
			 0     0%   100%    5846016 59.33%  os.OpenFile /usr/lib/go-1.9/src/os/file_unix.go
			 0     0%   100%    2031647 20.62%  syscall.BytePtrFromString /usr/lib/go-1.9/src/syscall/syscall.go
			 0     0%   100%    2031647 20.62%  syscall.Open /usr/lib/go-1.9/src/syscall/syscall_linux.go


一番割り当て回数が多い :code:`os.newFile` 関数について :code:`list` コマンドを実行し、関数内のどこでメモリ割り当てが行われているかを確認します。

.. code-block:: console

	(pprof) list os.newFile
	Total: 9853762
	ROUTINE ======================== os.newFile in /usr/lib/go-1.9/src/os/file_unix.go
	   3814369    3814369 (flat, cum) 38.71% of Total
			 .          .     82:func newFile(fd uintptr, name string, pollable bool) *File {
			 .          .     83:   fdi := int(fd)
			 .          .     84:   if fdi < 0 {
			 .          .     85:           return nil
			 .          .     86:   }
	   1703949    1703949     87:   f := &File{&file{
			 .          .     88:           pfd: poll.FD{
			 .          .     89:                   Sysfd:         fdi,
			 .          .     90:                   IsStream:      true,
			 .          .     91:                   ZeroReadIsEOF: true,
			 .          .     92:           },
	   2110420    2110420     93:           name: name,
			 .          .     94:   }}
			 .          .     95:
			 .          .     96:   // Don't try to use kqueue with regular files on FreeBSD.
			 .          .     97:   // It crashes the system unpredictably while running all.bash.
			 .          .     98:   // Issue 19093.

:code:`os.File` 構造体を作るためにメモリ割り当てが行われているようです。

os.Openなどを止めてsyscall.Openなどを使うように改変
---------------------------------------------------

:code:`loadavg.go` の :code:`ReadLoadAvg` 関数を以下のように書き換えてみます。

.. code-block:: go

	// ReadLoadAvg read the load average values.
	func ReadLoadAvg(a *LoadAvg) error {
		fd, err := syscall.Open("/proc/loadavg", os.O_RDONLY, 0)
		if err != nil {
			return err
		}
		defer syscall.Close(fd)

		var buf [80]byte
		n, err := syscall.Read(fd, buf[:])
		if err != nil {
			return err
		}
		return parseLoadAvg(string(buf[:n]), a)
	}

import 文も適宜変更します。私は `fatih/vim-go: Go development plugin for Vim <https://github.com/fatih/vim-go>`_ と `goimports <https://godoc.org/golang.org/x/tools/cmd/goimports>`_ を使ってファイルの保存時に自動的に変更するようにしています。

詳しくは vim-go チュートリアルの `imports <https://github.com/fatih/vim-go-tutorial#imports>`_ あるいは
その日本語訳の `import文 <https://github.com/hnakamur/vim-go-tutorial-ja#import%E6%96%87>`_ を参照してください。

改変後のベンチマーク
--------------------

出力ファイル名を変えて再度ベンチマークを実行します。

.. code-block:: console

	$ go test -count=10 -run=NONE -bench=. -benchmem -memprofile=loadavg.1.mprof | tee loadavg.1.bench
	goos: linux
	goarch: amd64
	pkg: github.com/hnakamur/sysstat
	BenchmarkReadLoadAvg-2   	  200000	      6275 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      6233 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      6204 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  300000	      6205 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      8682 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      7113 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  300000	      6178 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  300000	      6229 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      6209 ns/op	     128 B/op	       3 allocs/op
	BenchmarkReadLoadAvg-2   	  200000	      6206 ns/op	     128 B/op	       3 allocs/op
	PASS
	ok  	github.com/hnakamur/sysstat	15.753s

ベンチマーク結果の比較
----------------------

`zerologを参考にしてltsvlogを改良してみた </blog/2017/05/28/improve-ltsvlog-with-referring-to-zerolog/>`_ に書いた :code:`benchstat` コマンドを使って結果を比較します。

.. code-block:: console

	$ benchstat loadavg.0.bench loadavg.1.bench
	name          old time/op    new time/op    delta
	ReadLoadAvg-2    9.39µs ± 1%    6.22µs ± 1%  -33.81%  (p=0.000 n=10+8)

	name          old alloc/op   new alloc/op   delta
	ReadLoadAvg-2      216B ± 0%      128B ± 0%  -40.74%  (p=0.000 n=10+10)

	name          old allocs/op  new allocs/op  delta
	ReadLoadAvg-2      5.00 ± 0%      3.00 ± 0%  -40.00%  (p=0.000 n=10+10)

ReadLoadAvg の1回の呼び出しに対して、
メモリ割り当て回数 :code:`allocs/op` は5回から3回、
メモリ割り当て量 :code:`alloc/op` は216バイトから128バイト、
実行時間 :code:`time/op` は9.39マイクロ秒から6.22マイクロ秒に改善されました。
