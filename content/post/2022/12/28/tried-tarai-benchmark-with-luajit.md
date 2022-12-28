---
title: "LuaJITでたらい回し関数のベンチマークを試してみた"
date: 2022-12-28T16:22:42+09:00
---
## はじめに

[Pythonが速度改善に本気出すと聞いたので恒例のたらい回しベンチをとってみたら、RubyがYJITですごく速くなっていて驚いた話 - Smalltalkのtは小文字です](https://sumim.hatenablog.com/entry/2022/09/08/173557)の記事を見ました。

[ハッカーの遺言状──竹内郁雄の徒然苔第18回：問題児も悪くない | サイボウズ式](https://cybozushiki.cybozu.co.jp/articles/m000434.html)には以下のように書かれていました。

> 竹内関数ことタライ回し関数は、アッカーマン関数に比べればヒヨコのヒヨコだが、それでも十分に時間がかかる。それでいて、計算の途中で使うメモリはほんのちょっとしかない。上の例では途中に現れる数は -1 から 2n の間の整数だし、計算に必要なスタックの長さは n の数倍程度である。洗濯機の中のマイコンでも計算できる。つまり、ベンチマークとしては無差別級として使える問題だったのだ。

[NGINX](http://nginx.org/)の[openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module)と[Apache Traffic Server](https://trafficserver.apache.org/)の[Lua Plugin](https://docs.trafficserver.apache.org/en/latest/admin-guide/plugins/lua.en.html)でLuaJITをがっつり使っている私としては、LuaJITだとどれぐらいなのかなと興味がわいたので試してみました。

処理時間に加えてメモリ消費量も気になったので、[ChatGPT](https://openai.com/blog/chatgpt/)に聞いてみたら`/usr/bin/time -v`コマンドでRSS (resident set size)の最大値がKilobyte単位で表示されると教えてもらいました。

[time (1)](https://manpages.ubuntu.com/manpages/jammy/en/man1/time.1.html)を見て`/usr/bin/time -f %M`でRSSの最大値だけ出力できると分かったので、今回はこれを使っています。

```
 M      Maximum resident set size of the process during its lifetime, in Kilobytes.
```

## レポジトリ

https://github.com/hnakamur/tarai-benchmark.git

## 実行結果

```
$ make run-all-3-times
seq 1 3 | xargs -I {} make run-all
make[1]: Entering directory '/home/hnakamur/tarai-benchmark'
2>&1 /usr/bin/time -f %M ./tarai_O3
0.429032 14
1436
2>&1 /usr/bin/time -f %M luajit tarai-ffi-time.lua
2.763897 14
2176
2>&1 /usr/bin/time -f %M node tarai.js
1.594 14
21928
2>&1 /usr/bin/time -f %M ruby --yjit tarai.rb
14
3.446833922
23428
2>&1 /usr/bin/time -f %M sbcl --script tarai-g1.lisp
Evaluation took:
  0.592 seconds of real time
  0.588501 seconds of total run time (0.588501 user, 0.000000 system)
  99.49% CPU
  1,822,123,115 processor cycles
  0 bytes consed
  
14
36080
make[1]: Leaving directory '/home/hnakamur/tarai-benchmark'
make[1]: Entering directory '/home/hnakamur/tarai-benchmark'
2>&1 /usr/bin/time -f %M ./tarai_O3
0.424106 14
1448
2>&1 /usr/bin/time -f %M luajit tarai-ffi-time.lua
2.777932 14
2088
2>&1 /usr/bin/time -f %M node tarai.js
1.596 14
21812
2>&1 /usr/bin/time -f %M ruby --yjit tarai.rb
14
3.431343189
23460
2>&1 /usr/bin/time -f %M sbcl --script tarai-g1.lisp
Evaluation took:
  0.592 seconds of real time
  0.590194 seconds of total run time (0.590194 user, 0.000000 system)
  99.66% CPU
  1,826,274,449 processor cycles
  0 bytes consed
  
14
36120
make[1]: Leaving directory '/home/hnakamur/tarai-benchmark'
make[1]: Entering directory '/home/hnakamur/tarai-benchmark'
2>&1 /usr/bin/time -f %M ./tarai_O3
0.430504 14
1440
2>&1 /usr/bin/time -f %M luajit tarai-ffi-time.lua
2.787522 14
2148
2>&1 /usr/bin/time -f %M node tarai.js
1.583 14
21884
2>&1 /usr/bin/time -f %M ruby --yjit tarai.rb
14
3.447886121
23432
2>&1 /usr/bin/time -f %M sbcl --script tarai-g1.lisp
Evaluation took:
  0.592 seconds of real time
  0.592078 seconds of total run time (0.591549 user, 0.000529 system)
  100.00% CPU
  1,832,438,954 processor cycles
  0 bytes consed
  
14
36116
make[1]: Leaving directory '/home/hnakamur/tarai-benchmark'
```

* 元記事ではSBCLのほうがCより速いとありましたが、私の環境ではCが一番速かったです。
* RubyはJIT無しとmjitも試しましたがyjitが一番速かったのでyjitのみにしています。
* LuaJITはNode.jsよりは遅いですが、メモリ消費量がC以外の言語の中では約10分の1と少ないです。

Apache Traffic ServerのLuaプラグインだと[Configuration for number of Lua states](https://docs.trafficserver.apache.org/en/latest/admin-guide/plugins/lua.en.html#configuration-for-number-of-lua-states)に説明があるように最大かつデフォルトで256個のLuaJITのVMを作成するようになっています。ですのでメモリ消費量が少ないのはありがたいです。

## 実行環境

実行環境もメモしておきます。

* ThinkCentre M75q Tiny Gen2
* CPU: AMD Ryzen 7 PRO 4750GE
* RAM: PATOIOT SODIMM DDR4 3200MHz PC4-25600 32GB CL22 PSD432G32002S x 2
* SSD: Western Digital 1TB WD Blue SN550 NVMe WDS100T2B0C-EC 
* OS: Ubuntu 22.04 LTS

今回のベンチマークだとSSDは関係なさそうですが、今後他でも自分の環境を参照するとき用に一式書いておきます。

### GCC

Ubuntu標準パッケージでインストールしたバージョン4:11.2.0-1ubuntu1。

```
$ dpkg-query -W -f '${Version}\n' gcc
4:11.2.0-1ubuntu1
```

### LuaJIT

OpenRestyのフォーク版を自分のPPAでビルドしたもの。バージョン2.1.0~beta3.20220915+dfsg-1ppa1~ubuntu22.04。

* upstreamのソース: https://github.com/openresty/luajit2/releases/tag/v2.1-20220915
* 自作debパッケージのソース: https://github.com/hnakamur/openresty-luajit-deb/releases/tag/debian%2F2.1.0_beta3.20220915%2Bdfsg-1ppa1_ubuntu22.04
    * [Personal Package Archives : Ubuntu](https://launchpad.net/ubuntu/+ppas)の https://launchpad.net/~hnakamur/+archive/ubuntu/openresty-luajit でビルドしたものですが、PPAは最新版しか残らないので、試したバージョンのdebをGitHubレポジトリのReleaseに置いてます(ただしこのままaptレポジトリとしては使用できません)。

### Node.js

[nvm-sh/nvm: Node Version Manager](https://github.com/nvm-sh/nvm)でインストールしたバージョン18.2.0。

```
$ node --version
v18.2.0
$ type node
node is hashed (/home/hnakamur/.nvm/versions/node/v18.2.0/bin/node)
```

### Ruby

rbenvとruby-buildでインストールしたバージョン3.2.0。

```
$ ruby --version
ruby 3.2.0 (2022-12-25 revision a528908271) [x86_64-linux]
$ type ruby
ruby is /home/hnakamur/.rbenv/shims/ruby
```

インストール手順は https://github.com/rbenv/rbenv#basic-git-checkout と https://github.com/rbenv/ruby-build#clone-as-rbenv-plugin-using-git を参考にしました。途中libyamlが必要と言われたのでlibyaml-devも入れています。

```
git clone https://github.com/rbenv/rbenv.git ~/.rbenv
echo 'eval "$(~/.rbenv/bin/rbenv init - bash)"' >> ~/.bashrc
```

```
exec $SHELL -l
```

```
git clone https://github.com/rbenv/ruby-build.git "$(rbenv root)"/plugins/ruby-build
```

```
sudo apt-get install libyaml-dev
```

```
rbenv install 3.2.0
rbenv global 3.2.0
```

### SBCL ([Steel Bank Common Lisp](https://www.sbcl.org/))

Ubuntu標準パッケージでインストールしたバージョン2.1.11-1。

```
$ dpkg-query -W -f '${Version}\n' sbcl
2:2.1.11-1
```

## 以下はついでのメモ

他の方に読んで頂く用の記事なら分けたほうが良いのでしょうが、このブログはあくまで自分用メモなのでついでに書いてしまいます。

### JavaScriptのMAX_SAFE_INTEGERについてLuaJITでも試してみた

[LuaJIT](https://luajit.org/luajit.html)はLua 5.1互換のJITコンパイラで、Number型は[2.2 – Values and Types](https://www.lua.org/manual/5.1/manual.html#2.2)にあるように倍精度の浮動小数点数となっています。

そのため、JavaScriptのNumber型と同様、整数値で扱える範囲は
[Number.MIN_SAFE_INTEGER](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MIN_SAFE_INTEGER)から[Number.MAX_SAFE_INTEGER](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER)となります。具体的には`-9007199254740991 // -(2 ** 53 - 1)`から`9007199254740991 // 2 ** 53 - 1`です。

上のページに書いてあったサンプルを試してみると、以下のようにLuaJITでも`max_safe_integer + 1 == max_safe_integer + 2`が`true`となることが確認できました。

ただ、`max_safe_integer == max_safe_integer + 1`は`false`なので`max_safe_integer`はもう1多くても良いのではという素朴な疑問がわきましたが、[Number.isSafeInteger() - JavaScript | MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/isSafeInteger)に説明がありました。

```
$ cat safe-integer.lua
local max_safe_integer = 9007199254740991
local min_safe_integer = -9007199254740991

local w = max_safe_integer
local x = max_safe_integer + 1
local y = max_safe_integer + 2
print(string.format('w=%d, x=%d, w==x: %s', w, x, w == x))
print(string.format('x=%d, y=%d, x==y: %s', x, y, x == y))

local w2 = min_safe_integer
local x2 = min_safe_integer - 1
local y2 = min_safe_integer - 2
print(string.format('w2=%d, x2=%d, w2==x2: %s', w2, x2, w2 == x2))
print(string.format('x2=%d, y2=%d, x2==y2: %s', x2, y2, x2 == y2))

function check_safe_integer(v)
    if v < min_safe_integer or v > max_safe_integer then
        print(string.format("number %g is not a safe integer", v))
    end
end

check_safe_integer(max_safe_integer)
check_safe_integer(max_safe_integer + 1)
check_safe_integer(min_safe_integer)
check_safe_integer(min_safe_integer - 1)
```

```
$ luajit safe-integer.lua
w=9007199254740991, x=9007199254740992, w==x: false
x=9007199254740992, y=9007199254740992, x==y: true
w2=-9007199254740991, x2=-9007199254740992, w2==x2: false
x2=-9007199254740992, y2=-9007199254740992, x2==y2: true
number 9.0072e+15 is not a safe integer
number -9.0072e+15 is not a safe integer
```

今回LuaJITの[FFI Library](https://luajit.org/ext_ffi.html)で[clock_gettime (2)](https://manpages.ubuntu.com/manpages/jammy/en/man2/clock_gettime.2.html)を呼んでいるのですが、`struct timespec`の2つのフィールドはともに64bit整数なのでNumber型で扱える範囲を超える可能性が定義上はあります。

ということで念のためチェックするようにしてみました。ただ`clock_gettime`で得られる値だと`tv_nsec`は1^9未満ですし`tv_sec`もこの記事を書いている2022-12-28時点で1672217792と相当余裕があるので、この用途に限ればチェックは不要です。

```lua
local ffi = require "ffi"
local C = ffi.C

ffi.cdef[[
    typedef int clockid_t;
    typedef int64_t time_t;

    struct timespec {
        time_t   tv_sec;        /* seconds */
        long     tv_nsec;       /* nanoseconds */
    };

    int clock_gettime(clockid_t clockid, struct timespec *tp);
]]

local CLOCK_REALTIME = 0

function tarai(x, y, z)
    if x > y then
        return tarai( tarai(x-1, y, z), tarai(y-1, z, x), tarai(z-1, x, y) )
    else
        return y
    end
end

-- See
-- https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER
-- https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MIN_SAFE_INTEGER
local max_safe_integer = 9007199254740991
local min_safe_integer = -9007199254740991

function check_safe_integer(v)
    if v < min_safe_integer or v > max_safe_integer then
        print(string.format("number %g is not a safe integer", v))
        os.exit(1)
    end
end

function timespecdiffsec(t, u)
    check_safe_integer(tonumber(t.tv_sec))
    check_safe_integer(tonumber(t.tv_nsec))
    check_safe_integer(tonumber(u.tv_sec))
    check_safe_integer(tonumber(u.tv_nsec))

    local sec = tonumber(t.tv_sec) - tonumber(u.tv_sec)
    local nsec = tonumber(t.tv_nsec) - tonumber(u.tv_nsec)
    if nsec < 0 then
        sec = sec - 1
        nsec = nsec + 1000000000
    end
    return sec + nsec / 1000000000
end

local t1 = ffi.new("struct timespec[1]")
local t2 = ffi.new("struct timespec[1]")

C.clock_gettime(CLOCK_REALTIME, t1[0])
local ans = tarai(14, 7, 0)
C.clock_gettime(CLOCK_REALTIME, t2[0])

local delta = timespecdiffsec(t2[0], t1[0])
print(string.format("%f %d", delta, ans))
```

### たらい回し関数が呼び出される回数も調べてみた

今回のベンチマークで使っている`tarai(14, 7, 0)`でたらい関数が何回くらい呼ばれるのか気になったので、以下のように改変して試してみました。

```
$ sed -n '/^local called/,/^end/p' tarai-count.lua
local called = 0
function tarai(x, y, z)
    called = called + 1
    if x > y then
        return tarai( tarai(x-1, y, z), tarai(y-1, z, x), tarai(z-1, x, y) )
    else
        return y
    end
end
```

```
$ luajit tarai-count.lua
elapsed=5.985 ans=14 called=588802013
```

約5.9億回も呼ばれていました。

### bashのシェルスクリプトで同じコマンドをn回実行する

さらに脱線ですが、ベンチマークは1回だけ実行するのではなく何回か実行したほうが良いという話を聞いたことがあったので、繰り返し実行する方法を検索してみたところ、[Linux Commands – Repeat a Command n Times | Baeldung on Linux](https://www.baeldung.com/linux/repeat-command)にいろんな方法が詳解されていました。

私は普段はforループを使っているのですが、5番の`repeat`という関数を定義しておく方法は、よく使うなら便利かもと思いました。

```
function repeat(){
  for ((i=0;i<$1;i++)); do
    eval ${*:2}
  done
}
```

複数のコマンドも指定可能とのことで、試してみると確かにできました。
```
$ repeat 3 uname -r ";" hostname
5.15.0-56-generic
thinkcentre2
5.15.0-56-generic
thinkcentre2
5.15.0-56-generic
thinkcentre2
```

試しに`;`をクォートしないと以下のようになりました。なるほど、そりゃそうか。
```
$ repeat 3 uname -r ; hostname
5.15.0-56-generic
5.15.0-56-generic
5.15.0-56-generic
thinkcentre2
```

ということでセミコロンをクォートするのが意味があるケースもあるということを学びました。
`';'`や`\;`でもOKでした。

そういえばfindの`-exec`で`\;`は昔から使ってましたが、意味は考えてなかった。なおfindでコマンドを実行する際は`-exec {} +`のほうが良くて、削除するには`-delete`があるそうです。

* https://twitter.com/matsuu/status/1440827429497409551
* [POSIX 準拠のシェルスクリプトでは find | xargs よりも find -exec {} + を使うべき！ - Qiita](https://qiita.com/ko1nksm/items/9ff1f212255e8520070c)
