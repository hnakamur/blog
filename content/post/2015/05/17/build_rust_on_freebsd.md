+++
Categories = []
Description = ""
Tags = ["freebsd", "rust"]
date = "2015-05-17T07:51:14+09:00"
title = "FreeBSD 10.1 amd64でRustをビルドしてみた"

+++

[Install · The Rust Programming Language](http://www.rust-lang.org/install.html)
を見ると現在のところRustのバイナリが提供されているのはLinux, Mac, Windowsのみです。

FreeBSD 10.1 amd64でソースからビルドしてみました。
[Building from Source](https://github.com/rust-lang/rust#building-from-source)に従ってビルドするとすんなり行けました。

FreeBSDでの手順は以下のとおりです。標準でclangとcurlがインストールされていたのでそれを使っています。

```
sudo pkg install -y python gmake git
git clone https://github.com/rust-lang/rust.git
cd rust
./configure
gmake
sudo gmake install
```
