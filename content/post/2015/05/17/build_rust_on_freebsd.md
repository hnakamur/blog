Title: FreeBSD 10.1 amd64でRustをビルドしてみた
Date: 2015-05-17 07:51
Category: blog
Tags: freebsd, rust
Slug: blog/2015/05/17/build_rust_on_freebsd


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
