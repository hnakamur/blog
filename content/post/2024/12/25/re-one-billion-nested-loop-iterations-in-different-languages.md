---
title: "One Billion Nested Loop Iterations in Different Languagesについて調べてみた"
date: 2024-12-25T09:36:32+09:00
draft: true
---

<!--
## テーマ
* なぜ（背景）
  * CとRustに比べてGoが遅いのが気になった

* 何を（結果）
  * Goのコードを調整したら、CとRustとほぼ同等の速さになった

* どうやって（実現の手段）
  * 0除算チェックをループの外で明示的に実行した
  * ループ内で合計を計算するのにローカル変数を使うようにした

## アウトライン
-->
## 概要
## なぜ（背景）
### CとRustに比べてGoが遅いのが気になった
## 何を（結果）
### Goのコードを調整したら、CとRustとほぼ同等の速さになった
### 検証環境
## どうやって（実現の手段）
### 0除算チェックをループの外で明示的に実行した
### ループ内で合計を計算するのにローカル変数を使うようにした
## 結論

<!--
## はじめに

https://x.com/jalva_dev/status/1871480949332197706 のポストを見て、CとRustに比べてGoが遅いのが気になったので調べてみましたが、原因は私にはわかりませんでした。

調べたことをメモしておきます。

* 上記のポストのアニメーション: https://benjdd.com/languages/
* GitHubレポジトリ: https://github.com/bddicken/languages

なお、 https://news.ycombinator.com/item?id=42250205 でも指摘されていますが、このようなマイクロベンチマークは何を計測しているかをよく確認したほうがよいです。

## このベンチマークではCLIの実行時間を計っている

https://github.com/bddicken/languages/blob/1b18dd2126ff226e8e01ec28834e70d2be8a5f2f/run.sh#L32 を見ると [sharkdp/hyperfine: A command-line benchmarking tool](https://github.com/sharkdp/hyperfine) でCLIの実行時間を計測しています。

ですので、ランタイムの起動に時間がかかる言語ではそれも含んだ時間になります。

## 手元でビルドして試してみる

https://github.com/hnakamur/languages-microbenchmarks/commit/cc48087f147b6b3f2f93d678a7f9b6b03831bf13 のように変更して試しました。

C、Go、Rustのコンパイルの箇所のみ以下に抜粋します。

```
compile 'c' 'clang -O3 c/code.c -o c/code'
compile 'go' 'go build -ldflags "-s -w" -o go/code go/code.go'
compile 'rust' 'cargo build --manifest-path rust/Cargo.toml --release'
```

Rustは下記と上記の2行になっていましたが、上記のほうだけで試しました。
```
compile 'rust' 'RUSTFLAGS="-Zlocation-detail=none" cargo +nightly build --manifest-path rust/Cargo.toml --release'
```

Goは上記のスクリプトだと`-ldflags "-s -w"`の箇所がシェルスクリプト内のcompile関数で適切に展開できずコンパイルがエラーになってしまうため、手動で`go build -ldflags "-s -w" -o go/code go/code.go`でビルドする必要がありました。

loopディレクトリに移動し、`../compile.sh`を実行してコンパイルします。下記ではGoのコンパイルが失敗してるのを分かるように`bash -x`をつけて実行しています。
```
$ cd loop
$ bash -x ../compile.sh
+ compile c 'clang -O3 c/code.c -o c/code'
+ '[' -d c ']'
+ echo ''

+ echo 'Compiling c'
Compiling c
+ clang -O3 c/code.c -o c/code
+ result=0
+ '[' 0 -eq 1 ']'
+ compile go 'go build -ldflags "-s -w" -o go/code go/code.go'
+ '[' -d go ']'
+ echo ''

+ echo 'Compiling go'
Compiling go
+ go build -ldflags '"-s' '-w"' -o go/code go/code.go
+ result=2
+ '[' 2 -eq 1 ']'
+ compile rust 'cargo build --manifest-path rust/Cargo.toml --release'
+ '[' -d rust ']'
+ echo ''

+ echo 'Compiling rust'
Compiling rust
+ cargo build --manifest-path rust/Cargo.toml --release
+ result=0
+ '[' 0 -eq 1 ']'
```

`go/code.go`のビルドを手動で実行します。
```
$ go build -ldflags "-s -w" -o go/code go/code.go
```

ベンチマークスクリプトを実行します。
```
$ ../run.sh

Checking C
Check passed
Benchmarking C
Benchmark 1: ./c/code 40
  Time (mean ± σ):      1.117 s ±  0.000 s    [User: 1.116 s, System: 0.000 s]
  Range (min … max):    1.117 s …  1.118 s    3 runs

Checking Go
Check passed
Benchmarking Go
Benchmark 1: ./go/code 40
  Time (mean ± σ):      1.252 s ±  0.000 s    [User: 1.251 s, System: 0.002 s]
  Range (min … max):    1.251 s …  1.252 s    3 runs

Checking Rust
Check passed
Benchmarking Rust
Benchmark 1: ./rust/target/release/code 40
  Time (mean ± σ):      1.116 s ±  0.001 s    [User: 1.115 s, System: 0.000 s]
  Range (min … max):    1.115 s …  1.117 s    3 runs

```

CとRustは同程度ですが、Goは約0.14秒遅いです。

## Goのベンチマークコードの乱数生成とループの処理時間を計測

[loops/go/code.go](https://github.com/hnakamur/languages-microbenchmarks/blob/1b18dd2126ff226e8e01ec28834e70d2be8a5f2f/loops/go/code.go)は最初に乱数を1つ生成して、それから1万と10万の2重ループの処理を実行しています。

https://github.com/hnakamur/languages-microbenchmarks/commit/b831bce0209daea7597a5c2114317e1989336772 で2つの処理の時間を計ってみました。
`rand=4.585µs, loop=1.272208584s`とほぼループ処理の時間になっており、乱数生成の時間は無視できるレベルでした。

## アセンブラのコードを見比べてみる

https://github.com/hnakamur/languages-microbenchmarks/commit/0ade38ea0d6c71ce825db88cbb4024044258fa3d のコミットで確認しました。

`objdump -d -S`でソースコード入りでディスアセンブルするために以下の変更をしました。

* Cは`clang`に`-g`オプションを指定
* Rustは`Cargo.toml`の`[profile.release]`の`strip`を`false`に変更し、`debug = true`を追加
* Goは`-ldflags '"-s' '-w"'`なしでビルド

https://manpages.ubuntu.com/manpages/noble/en/man1/ld.1.html によると`-s`が`--strip-all`なのでこれだけ外せば良さそうでした。

```
       -s
       --strip-all
           Omit all symbol information from the output file.
```

```
       -w
       --no-warnings
           Do not display any warning or error messages.  This overrides --fatal-warnings if it
           has been enabled.  This option can be used when it is known that the output binary
           will not work, but there is still a need to create it.
```

上記のようにビルドして、下記のコマンドでディスアセンブルしました。

```
$ objdump -d -S --no-show-raw-insn go/code > go/code.s
$ objdump -d -S --no-show-raw-insn c/code > c/code.s
$ objdump -d -S --no-show-raw-insn rust/target/release/code > rust/code.s
```

上記のファイルの一部の範囲のリンクを貼ろうと思ったのですが、ファイルが大きすぎて無理でした。
そこでmain関数の部分のみを下記に抜粋します。

```text {linenos=inline}
func main() {
  4916e0:	mov    %rsp,%r12
  4916e3:	sub    $0x9c08,%r12
  4916ea:	jb     491831 <main.main+0x151>
  4916f0:	cmp    0x10(%r14),%r12
  4916f4:	jbe    491831 <main.main+0x151>
  4916fa:	push   %rbp
  4916fb:	mov    %rsp,%rbp
  4916fe:	sub    $0x9c80,%rsp
  input, e := strconv.Atoi(os.Args[1]) // Get an input number from the command line
  491705:	mov    0xc742c(%rip),%rcx        # 558b38 <os.Args+0x8>
  49170c:	cmp    $0x1,%rcx
  491710:	jbe    491826 <main.main+0x146>
  491716:	mov    0xc7413(%rip),%rcx        # 558b30 <os.Args>
  49171d:	mov    0x10(%rcx),%rax
  491721:	mov    0x18(%rcx),%rbx
  491725:	call   471540 <strconv.Atoi>
  if e != nil { panic(e) }
  49172a:	test   %rbx,%rbx
  49172d:	jne    491815 <main.main+0x135>
  input, e := strconv.Atoi(os.Args[1]) // Get an input number from the command line
  491733:	mov    %rax,0x9c68(%rsp)
  u := int32(input)
  r := rand.Int31n(10000)              // Get a random number 0 <= r < 10k
  49173b:	mov    $0x2710,%eax
  491740:	call   4910c0 <math/rand.Int31n>
  var a[10000]int32                      // Array of 10k elements initialized to 0
  491745:	lea    0x28(%rsp),%rdi
  49174a:	mov    $0x1388,%ecx             ## 0x1388 = 5000
  49174f:	mov    %eax,%edx
  491751:	xor    %eax,%eax
  491753:	rep stos %rax,%es:(%rdi)
  for i := int32(0); i < 10000; i++ {         // 10k outer loop iterations
  491756:	mov    0x9c68(%rsp),%rcx
  49175e:	xor    %eax,%eax
  491760:	jmp    49176b <main.main+0x8b>
    for j := int32(0); j < 100000; j++ {      // 100k inner loop iterations, per outer loop iteration
      a[i] = a[i] + j%u                // Simple sum
    }
    a[i] += r                          // Add a random value to each element in array
  491762:	movslq %eax,%rbx
  491765:	add    %edx,0x28(%rsp,%rbx,4)
  for i := int32(0); i < 10000; i++ {         // 10k outer loop iterations
  491769:	inc    %eax
  49176b:	cmp    $0x2710,%eax
  491770:	jge    491779 <main.main+0x99>
  491772:	xor    %ebx,%ebx
    for j := int32(0); j < 100000; j++ {      // 100k inner loop iterations, per outer loop iteration
  491774:	jmp    491800 <main.main+0x120>
  }
  fmt.Println(a[r])                    // Print out a single element from the array
  491779:	movups %xmm15,0x9c70(%rsp)
  491782:	movslq %edx,%rax
  491785:	cmp    $0x2710,%rax
  49178b:	jae    4917d9 <main.main+0xf9>
  49178d:	mov    0x28(%rsp,%rax,4),%eax
  491791:	call   40a560 <runtime.convT32>
  491796:	lea    0x92e3(%rip),%rcx        # 49aa80 <type:*+0x8a80>
  49179d:	mov    %rcx,0x9c70(%rsp)
  4917a5:	mov    %rax,0x9c78(%rsp)
	return Fprintln(os.Stdout, a...)
  4917ad:	mov    0xc70bc(%rip),%rbx        # 558870 <os.Stdout>
  4917b4:	lea    0x4601d(%rip),%rax        # 4d77d8 <go:itab.*os.File,io.Writer>
  4917bb:	lea    0x9c70(%rsp),%rcx
  4917c3:	mov    $0x1,%edi
  4917c8:	mov    %rdi,%rsi
  4917cb:	call   48bd20 <fmt.Fprintln>
}
  4917d0:	add    $0x9c80,%rsp
  4917d7:	pop    %rbp
  4917d8:	ret
  fmt.Println(a[r])                    // Print out a single element from the array
  4917d9:	mov    $0x2710,%ecx
  4917de:	xchg   %ax,%ax
  4917e0:	call   46be20 <runtime.panicIndex>
      a[i] = a[i] + j%u                // Simple sum
  4917e5:	movslq %eax,%rsi
  for i := int32(0); i < 10000; i++ {         // 10k outer loop iterations
  4917e8:	mov    %eax,%edi
      a[i] = a[i] + j%u                // Simple sum
  4917ea:	mov    %ebx,%eax
  r := rand.Int31n(10000)              // Get a random number 0 <= r < 10k
  4917ec:	mov    %edx,%r8d
      a[i] = a[i] + j%u                // Simple sum
  4917ef:	cltd
  4917f0:	idiv   %ecx
  4917f2:	add    %edx,0x28(%rsp,%rsi,4)
    for j := int32(0); j < 100000; j++ {      // 100k inner loop iterations, per outer loop iteration
  4917f6:	inc    %ebx
      a[i] = a[i] + j%u                // Simple sum
  4917f8:	mov    %edi,%eax
    a[i] += r                          // Add a random value to each element in array
  4917fa:	mov    %r8d,%edx
  4917fd:	nopl   (%rax)
    for j := int32(0); j < 100000; j++ {      // 100k inner loop iterations, per outer loop iteration
  491800:	cmp    $0x186a0,%ebx
  491806:	jge    491762 <main.main+0x82>
      a[i] = a[i] + j%u                // Simple sum
  49180c:	test   %ecx,%ecx
  49180e:	jne    4917e5 <main.main+0x105>
  491810:	call   430c00 <runtime.panicdivide>
  if e != nil { panic(e) }
  491815:	je     49181b <main.main+0x13b>
  491817:	mov    0x8(%rbx),%rbx
  49181b:	mov    %rbx,%rax
  49181e:	mov    %rcx,%rbx
  491821:	call   464ba0 <runtime.gopanic>
  input, e := strconv.Atoi(os.Args[1]) // Get an input number from the command line
  491826:	mov    $0x1,%eax
  49182b:	call   46be20 <runtime.panicIndex>
  491830:	nop
func main() {
  491831:	call   469d00 <runtime.morestack_noctxt.abi0>
  491836:	jmp    4916e0 <main.main>

000000000049183b <runtime.etext>:
  49183b:	int3
```

* 491751で`xor %eax,%eax`でeaxを0にしているのが外側のforループの`i := int32(0)`に対応。違うかも。
* 491772で`xor %ebx,%ebx`でebxを0にしているのが内側のforループの`j := int32(0)`に対応。
* 4917f0の`idiv %ecx`が`j%u`に対応。
* 491800、491806が内側のforループの繰り返しに対応。
* 49180c、49180eが外側のforループの繰り返しに対応。

変数
| アドレス | バイト数オフセット |変数 |
| ---------|--------------|----------------|
| 0x28(%rsp) | - | var a[10000]int32 |
| 0x9c68(%rsp) | 40000 | input, u |
| 0x9c70(%rsp) | 8 | | i |
| 0x9c78(%rsp) | 8 | | j |

* 49174f:	`mov    %eax,%edx` // %edx = r

* 491756: `mov    0x9c68(%rsp),%rcx` // %rcx = u
* 49175e: `xor    %eax,%eax` // for i := int32(0)
* 491760: `jmp    49176b <main.main+0x8b>`

* 49176b: `cmp    $0x2710,%eax` // i < 10000
* 491770:	`jge    491779 <main.main+0x99>`
* 491772:	`xor    %ebx,%ebx` // for j := int32(0)
* 491774:	`jmp    491800 <main.main+0x120>`
* 491779:	`movups %xmm15,0x9c70(%rsp)` 




ループ回数の1万と10万は、16進数ではそれぞれ0x2710と0x186a0。
```
$ printf "0x2710=%d, 0x186a0=%d\n" 0x2710 0x186a0
0x2710=10000, 0x186a0=100000
```
-->
