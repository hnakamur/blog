Title: lua, V8, ruby, mrubyでfib(39)の実行時間比較
Date: 2013-03-12 00:00
Category: blog
Tags: lua, ruby, v8
Slug: 2013/03/12/fib-39-benchmark-in-luajit

[lua, V8, ruby, mrubyでfib(39)の実行時間比較 - hnakamur's blog at github](http://hnakamur.github.com/blog/2012/05/04/fib-39-benchmark-in-lua/)が[@matz](https://twitter.com/yukihiro_matz)さんにツイートされたのを受けて、各処理系の最新版で再度試してみました。

## テスト環境その1（前回とは違う環境です）

* Model: MacBook Pro Retina, Mid 2012
* CPU: 2.6GHz Intel Core i7
* RAM: 16GB 1600MHz DDR3
* OS: Mac OS X 10.8.2

### 2013-03-24 追記

goでも試してみました

### go 1.0.3

```
package main

import "fmt"

func fib(n int) int {
  if n < 2 {
    return n
  }
  return fib(n - 1) + fib(n - 2)
}

func main() {
  fmt.Println(fib(39))
}
```

```
$ time fib39
63245986

real    0m0.484s
user    0m0.481s
sys     0m0.002s
```

### lua

```
function fib(n)
  if n < 2 then
    return n
  end
  return fib(n-2) + fib(n-1)
end

print(fib(39))
```

```
$ luajit -v
LuaJIT 2.0.1 -- Copyright (C) 2005-2013 Mike Pall. http://luajit.org/
$ time luajit fib.lua
63245986

real  0m0.906s
user  0m0.901s
sys 0m0.003s
```

```
$ lua -v
Lua 5.1.5  Copyright (C) 1994-2012 Lua.org, PUC-Rio
$ time lua fib.lua
63245986

real  0m12.278s
user  0m12.271s
sys 0m0.006s
```

```
$ src/lua -v
Lua 5.2.1  Copyright (C) 1994-2012 Lua.org, PUC-Rio
$ time src/lua ~/bench/fib.lua
63245986

real  0m13.971s
user  0m13.965s
sys 0m0.005s
```

### v8

```
function fib(n) {
  if (n < 2) return n;
  return fib(n-2) + fib(n-1);
}

print(fib(39));
```

```
$ v8
V8 version 3.16.14 [sample shell]
> ^D
$ time v8 fib.js
63245986

real  0m0.804s
user  0m0.798s
sys 0m0.008s
```

### ruby

```
def fib n
  return n if n < 2
  fib(n-2) + fib(n-1)
end

puts fib(39)
```

```
$ git log -1 | grep commit
commit 46d8c51763bd13b69a4234f0d4be05cbfd8ae401

$ time bin/mruby fib.rb
63245986

real  0m16.357s
user  0m16.345s
sys 0m0.008s
```

```
$ rbenv version
1.9.3-p374 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real  0m16.225s
user  0m16.169s
sys 0m0.043s
```

```
$ rbenv version
1.9.3-p392 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real  0m36.813s
user  0m36.746s
sys 0m0.043s
```

```
$ rbenv version
2.0.0-p0 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb 
63245986

real  0m31.828s
user  0m31.743s
sys 0m0.045s
```

### 2013-03-12 23:15 追記
1.9.3-p374と1.9.3-p392でこんなに違うのは変だなと思って、1.9.3-p374を入れなおして再度測ってみました。

```
$ rbenv version
1.9.3-p374 (set by /Users/hnakamur/.rbenv/version)
$ time ruby ~/bench/fib.rb 
63245986

real  0m38.909s
user  0m38.834s
sys 0m0.045s
```

以前1.9.3-p374を入れた時から、XCodeのバージョンが変わっているので、コンパイラが違うせいで大幅に時間が変わったようです。

## テスト環境その2

[lua, V8, ruby, mrubyでfib(39)の実行時間比較 - hnakamur's blog at github](http://hnakamur.github.com/blog/2012/05/04/fib-39-benchmark-in-lua/)と同じマシンです。
OSはLionのままですがアップデートはしています。XCodeもバージョンアップしました。

* Model: MacBook Air 13-inch, Mid 2011
* CPU: 1.7GHz Intel Core i5
* RAM: 4GB 1333MHz DDR3
* OS: Mac OS X Lion 10.7.5

### lua

```
$ src/luajit -v
LuaJIT 2.0.1 -- Copyright (C) 2005-2013 Mike Pall. http://luajit.org/
$ time src/luajit ~/fib_bench/fib.lua
63245986

real    0m1.268s
user    0m1.256s
sys     0m0.003s
```

```
$ cd ../lua-5.2.1
$ src/lua -v
Lua 5.2.1  Copyright (C) 1994-2012 Lua.org, PUC-Rio
$ time src/lua ~/fib_bench/fib.lua
63245986

real    0m20.299s
user    0m20.299s
sys     0m0.006s
```

```
$ src/lua -v
Lua 5.1.5  Copyright (C) 1994-2012 Lua.org, PUC-Rio
$ time src/lua ~/fib_bench/fib.lua
63245986

real    0m20.100s
user    0m20.089s
sys     0m0.012s
```

### V8

```
$ v8
V8 version 3.16.14 [sample shell]
> ^D

$ time v8 fib.js
63245986

real    0m1.105s
user    0m1.099s
sys     0m0.011s
```

### ruby

```
$ rbenv version
1.9.3-p194 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real    0m23.462s
user    0m23.431s
sys     0m0.039s
```

この1.9.3-p194は以前のXCodeでビルドしたものです。


```
$ rbenv version
1.9.3-p392 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real    0m51.765s
user    0m51.679s
sys     0m0.048s
```

```
$ rbenv version
2.0.0-p0 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real    0m47.074s
user    0m47.048s
sys     0m0.045s
```

## テスト環境その3

* Model: NEC Express5800/S70 type RB
* CPU: Intel Pentium G6950 (2.8GHz)
* RAM: 16GB DDR3-1333
* OS: CentOS 6.4 x86_64

### lua

```
$ luajit -v
LuaJIT 2.0.1 -- Copyright (C) 2005-2013 Mike Pall. http://luajit.org/
$ time luajit fib.lua
63245986

real  0m1.244s
user  0m1.241s
sys 0m0.000s
```

```
$ src/lua -v
Lua 5.2.1  Copyright (C) 1994-2012 Lua.org, PUC-Rio
$ time src/lua ~hnakamur/fib_bench/fib.lua 
63245986

real  0m15.804s
user  0m15.774s
sys 0m0.002s
```

```
$ time src/lua ~hnakamur/fib_bench/fib.lua 
63245986

real  0m15.658s
user  0m15.627s
sys 0m0.002s
```

### V8

```
$ ./out/x64.release/d8   
V8 version 3.16.14 [console: dumb]
d8> 
Segmentation fault
$ time ./out/x64.release/d8 ~hnakamur/fib_bench/fib.js
63245986

real  0m1.311s
user  0m1.314s
sys 0m0.004s
```

### ruby

```
$ rbenv version
1.9.3-p374 (set by /usr/local/rbenv/version)
$ time ruby fib.rb
63245986

real  0m40.485s
user  0m40.365s
sys 0m0.038s
```

```
$ rbenv version
1.9.3-p392 (set by /usr/local/rbenv/version)
$ time ruby fib.rb
63245986

real  0m38.841s
user  0m38.749s
sys 0m0.013s
```

```
$ rbenv version
2.0.0-p0 (set by /usr/local/rbenv/version)
$ time ruby fib.rb 
63245986

real  0m32.491s
user  0m32.410s
sys 0m0.014s
```

```
$ git log -1|grep commit
commit f63cd331da6257f9b44778dabff60be55b0721fa
$ time bin/mruby ~hnakamur/fib_bench/fib.rb 
63245986

real  0m20.752s
user  0m20.713s
sys 0m0.002s
```
