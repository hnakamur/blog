---
title: "psgreptree というコマンドラインツールを Rust で書いた"
date: 2020-09-22T18:47:59+09:00
---
## はじめに

私は仕事で Ubuntu の物理サーバーに ssh して 
`LC_TIME=C ps auxwwf | grep [n]ginx` とか `LC_TIME=C ps auxwwf | grep -E '(nginx|traffic)' | grep -v grep` のようなコマンドを実行することがよくあります。

しかし、ヘッダー行が出ない（grepのパターンに `^USER` を追加すれば出せますが）とか、 grep 自体を出力させない小技が面倒という問題がありました。

[実践Rustプログラミング入門 - 秀和システム](https://www.shuwasystem.co.jp/book/9784798061702.html) も買ったことですし、 Rust でこれを代替するコマンドラインツールを書いてみました。

[hnakamur/psgreptree](https://github.com/hnakamur/psgreptree)

Rust で何か書くのは [hnakamur/tokio-xattr: Filesystem xattr (extended attributes) API for Rust/Tokio](https://github.com/hnakamur/tokio-xattr) から約1年ぶりです（そういえばこれも書いたけど使ってなくて放置しているので更新しないと）。

このツール自体というより、このツールを書く過程で学んだことについてメモしておきます。

## 非同期 I/O ライブラリー stjepang/smol を使ってみた

そもそも大量のリクエストをさばくウェブサーバーというわけでもないので非同期 I/O にする必要性もないのですが、今後 Rust で非同期 I/O のソフトウェアーを書いていきたいので練習としてそうしました。

現状だと [tokio-rs/tokio](https://github.com/tokio-rs/tokio/) と [async-rs/async-std](https://github.com/async-rs/async-std) が 2 大メジャーどころという認識ですが [Stjepan’s blog](https://stjepang.github.io/) のいくつかの記事を呼んで、今回は [stjepang/smol: A small and fast async runtime for Rust](https://github.com/stjepang/smol) を使ってみました。

上記のブログの [Build your own executor](https://stjepang.github.io/2020/01/31/build-your-own-executor.html) と [Build your own block_on()](https://stjepang.github.io/2020/01/25/build-your-own-block-on.html) の他に Why I’m building a new async runtime という非常に良い記事があったのですが、 2020-09-22 時点では無くなっていました。以前にも一度ブログまるごとが 404 Not Found になって、その数日後に復活したのですがまた消されてしまったようです。

非同期 I/O ランタイムをこれ以上増やすなという圧力があるんですかねえ。あまり乱立してエコシステムが分断するのは良くないですが、競合の存在が改善を促進するという面もあると思うので歓迎して良いと思うのですが。

README にあるとおり smol は [stjepang (Stjepan Glavina)](https://github.com/stjepang/) にある複数の crate を re-export しているだけになっています。それぞれシンプルでわかりやすく書かれていて、コードを読んで理解しやすいのが良いです。

## プロセスツリーのデータ構造

[Idiomatic tree and graph like structures in Rust – Rust Leipzig](https://rust-leipzig.github.io/architecture/2016/12/20/idiomatic-trees-in-rust/) にあるように Rust でのツリー構造の素朴な実装として思いつくのは `Rc<RefCell<Box<Node<T>>>>` とか `Arc<Mutex<Box<Node<T>>>>` で他のノードを参照する方式ですが、循環参照が起きないように注意が必要とのことです。

そこで Arena 方式でノードで Vec で保持しておいて、ツリー内で参照するときはノードのID (=Vec内のインデクス) を使うという手法があります。これの実装としては上の記事の最後に紹介されている [saschagrunert/indextree: Arena based tree 🌲 structure by using indices instead of reference counted pointers](https://github.com/saschagrunert/indextree) があります。

また別の手法として raw pointer を使った実装の [oooutlk/trees](https://github.com/oooutlk/trees) というのも見つけました。

今回は Arena 方式の独自実装を書いてそれでとりあえず動いているのでそのままにしました。
PID でソートしたいので BTreeSet で PID をキーにしてノードを持ち、他のノードは PID で参照しています。

[saschagrunert/indextree](https://github.com/saschagrunert/indextree) だとアプリケーションドメインのキー（今回だと PID）と indextree 内でのインデクスの対応を管理する必要が出てくるので、だったら直接 PID をキーにするほうが楽という判断で、 PID は途中に空きがあるので Vec ではなく BTreeSet で保持するようにしたというわけです。

[oooutlk/trees](https://github.com/oooutlk/trees) もちらっと見た感じ良さそうで興味はあるのでまた別の機会にじっくりコードを読んで試してみたいです。

## バイト数を人間が見やすく表示する `humanize_number` を FreeBSD から移植した

Linux の ps コマンドでは VSZ と RSS を KiB 単位で表示するのですが、大きいプロセスだと桁数が溢れてその後の TTY カラムで調整するようになっています。一旦その挙動も実装しては見たのですが、 MiB や GiB などにオートスケールするほうが便利なのでそうすることにしました。

一旦 [human_format](https://crates.io/crates/human_format) を使って実装してみたのですが `df -h` や `du -sh` のように整数部が 1 桁のときのみ小数第一位まで表示する方式のほうが、狭い幅で情報量が多くて良いなと思い FreeBSD の [humanize_number (3)](https://www.freebsd.org/cgi/man.cgi?query=humanize_number&apropos=0&sektion=0&manpath=FreeBSD+12.1-RELEASE+and+Ports&arch=default&format=html) (ソース: [freebsd/humanize_number.c](https://github.com/freebsd/freebsd/blob/master/lib/libutil/humanize_number.c)、テスト: [freebsd/humanize_number_test.c](https://github.com/freebsd/freebsd/blob/master/lib/libutil/tests/humanize_number_test.c) )を移植してみました。

### `&str` の `char_indices()` の char は使わなければデコードのコストは発生しない

FreeBSD の `humanize_number` では [snprintf (3)](https://www.freebsd.org/cgi/man.cgi?query=snprintf&apropos=0&sektion=0&manpath=FreeBSD+12.1-RELEASE+and+Ports&arch=default&format=html) で指定の文字数までしか出力しないということをしています。
Rust の `write!` マクロや [std::fmt::write](https://doc.rust-lang.org/beta/std/fmt/fn.write.html) だと難しいかと思ったのですが [std::fmt::Write](https://doc.rust-lang.org/beta/std/fmt/trait.Write.html) トレイトを実装した独自の struct を実装すればよいということに気づいて LimitedWriter というのを書いてみました。

そのときに `&str` 内の UTF-8 のコードポイント単位で書くようにしたいのですが [char_indices()](https://doc.rust-lang.org/beta/std/primitive.str.html#method.char_indices) だと各コードポイントの先頭のインデクスだけではなくデコードした char も受け取るようになっています。

そこで [Pre-RFC: Add len_utf8_at method to str - libs - Rust Internals](https://internals.rust-lang.org/t/pre-rfc-add-len-utf8-at-method-to-str/13101) というのを投稿してみたのですが、 `char_indices()` の char のほうを参照しなければ release ビルドで inline 化される際に最適化でデコードの処理は消えるはずというご指摘をいただきました。

これを確認するため、次項の手順で出力されたアセンブラーを見てみました。

### Rust のビルド後のアセンブラーを Rust のコードと対比して確認する方法

[rust - How to get assembly output from building with Cargo? - Stack Overflow](https://stackoverflow.com/questions/39219961/how-to-get-assembly-output-from-building-with-cargo/54287770#54287770) で知りました。

`cargo-asm` をインストールします。

```console
cargo install cargo-asm
```

調べたい crate をリリースモードでビルドします。

```console
cargo build --release
```

後は調べたい関数名を crate 名と共に指定して以下のようにしてアセンブラーを出力します
（下記の `your_crate_name` と `your_function_name` を適宜変更して実行します）。

```console
cargo asm --no-color --rust your_crate_name::your_function_name > your_function_name.s
```

するとコンパイル結果のアセンブラーが対応する Rust のコードと共に見られます。
これで `char_indices()` を iterate してもらえる char を参照しなければデコードの処理は発生しないことが確認できました。

### criterion crate によるベンチマーク

Rust の nightly では cargo bench でベンチマークできますが [What is the standard way to run benchmarks in stable rust? : rust](https://www.reddit.com/r/rust/comments/8tplwr/what_is_the_standard_way_to_run_benchmarks_in/) によると stable では [criterion](https://crates.io/crates/criterion) が良さそうなので試してみました。

User Guide の [Comparing Functions](https://bheisler.github.io/criterion.rs/book/user_guide/comparing_functions.html) に2種類の実装をベンチマークして結果をわかりやすくグラフで表示してくれる方法の説明があるのでこれを試してみました。

gnuplot があれば使うので Ubuntu のパッケージでインストールしておきます。

```console
sudo apt install gnuplot
```

[Add Dependency to Cargo.toml](https://bheisler.github.io/criterion.rs/book/getting_started.html#step-1---add-dependency-to-cargotoml) のように設定して、 [Comparing Functions](https://bheisler.github.io/criterion.rs/book/user_guide/comparing_functions.html) を参考にベンチマークを書いて `cargo bench` で実行します。

すると `target/criterion/${ベンチマークグループ名}/report/index.html` に HTML ファイルが生成されます（ベンチマークグループ名は `Criterion` の `benchmark_group` メソッドに指定した名前です）。

これを開くと Violin Plot や Line Chart で結果がわかりやすく表示されます。

## バイナリサイズの最適化

[実践Rustプログラミング入門 - 秀和システム](https://www.shuwasystem.co.jp/book/9784798061702.html) を参考にバイナリサイズの最適化をしてみると 5.9MiB から 1.7MiB まで小さくなりました。

## おわりに

プロファイラーで挙動を見て最適化とかもやってみたいところですが、現状でも体感で満足する速度が出ているので今回はスキップしてまた別の機会に。
