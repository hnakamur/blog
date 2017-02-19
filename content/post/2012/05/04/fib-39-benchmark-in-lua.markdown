Title: lua, V8, ruby, mrubyでfib(39)の実行時間比較 2013-03-12版
Date: 2012-05-04 00:00
Category: blog
Tags: lua, v8, ruby
Slug: blog/2012/05/04/fib-39-benchmark-in-lua

2013-03-13追記

この記事が[@matz](https://twitter.com/yukihiro_matz)さんにツイートされたのを受けて、各処理系の最新版で再度試してみました。
[lua, V8, ruby, mrubyでfib(39)の実行時間比較 2013-03-12版](http://hnakamur.github.com/blog/2013/03/12/fib-39-benchmark-in-luajit/)をご参照ください。

<hr>

[mruby (軽量ruby) ソース公開 | quredo-style](http://www.quredo.net/2012/04/mruby-%E8%BB%BD%E9%87%8Fruby-%E3%82%BD%E3%83%BC%E3%82%B9%E5%85%AC%E9%96%8B/)を見て、自分の環境でlua, luajit, V8, ruby, mrubyで試してみた。

テスト環境

* Model: MacBook Air 13-inch, Mid 2011
* CPU: 1.7GHz Intel Core i5
* RAM: 4GB 1333MHz DDR3
* OS: Mac OS X Lion 10.7.3

## lua

fib.lua
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
$ lua -v
Lua 5.1.4  Copyright (C) 1994-2008 Lua.org, PUC-Rio
$ time lua fib.lua
63245986

real	0m21.368s
user	0m21.345s
sys	0m0.016s
```


```
$ ./lua -v
Lua 5.2.0  Copyright (C) 1994-2011 Lua.org, PUC-Rio
$ time ./lua fib.lua
63245986

real	0m19.603s
user	0m19.585s
sys	0m0.012s
```


```
$ ./luajit -v
Lua 5.1.5  Copyright (C) 1994-2012 Lua.org, PUC-Rio
LuaJIT 1.1.8  Copyright (C) 2005-2012 Mike Pall, http://luajit.org/
$ time ./luajit fib.lua
63245986

real	0m4.302s
user	0m4.292s
sys	0m0.006s
```


```
$ luajit -v
LuaJIT 2.0.0-beta9 -- Copyright (C) 2005-2011 Mike Pall. http://luajit.org/
$ time luajit fib.lua
63245986

real	0m1.299s
user	0m1.289s
sys	0m0.004s
```


## V8

```
function fib(n) {
  if (n < 2) return n;
  return fib(n-2) + fib(n-1);
}

print(fib(39));
```

```
$ v8
V8 version 3.9.24 [sample shell]
> quit()
$ time v8 fib.js
63245986

real	0m1.417s
user	0m1.407s
sys	0m0.013s
```

## ruby

```
def fib n
  return n if n < 2
  fib(n-2) + fib(n-1)
end

puts fib(39)
```

```
$ rbenv version
1.8.7-p358 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real	1m47.227s
user	1m46.945s
sys	0m0.132s
```


```
$ rbenv version
1.9.3-p125 (set by /Users/hnakamur/.rbenv/version)
$ time ruby fib.rb
63245986

real	0m16.504s
user	0m16.374s
sys	0m0.051s
```


```
$ time bin/mruby fib.rb 
63245986

real	0m35.465s
user	0m35.423s
sys	0m0.014s
```


[2012-05-03 23:21]

