rustのHTTPライブラリについて情報収集した
########################################

:date: 2018-01-29 05:08
:tags: rust
:category: blog
:slug: 2018/01/29/rust-http-libraries

はじめに
--------

rustのHTTPライブラリの現状について検索して軽く情報収集したので、
HTTPに関連したIOライブラリも含めてメモしておきます。

非同期IO関連の動向
------------------

* `RFC: Tokio reform, take 2 by aturon · Pull Request #3 · tokio-rs/tokio-rfcs <https://github.com/tokio-rs/tokio-rfcs/pull/3>`_
    * `Question: What's the future of tokio-proto and should new libraries depend on it? · Issue #202 · tokio-rs/tokio-proto <https://github.com/tokio-rs/tokio-proto/issues/202>`_
* `Rustの『RFC 2033: 実験的なコルーチン』の要約メモ <https://gist.github.com/sile/87f0732236e2ebc6d108ac95a2d444c6>`_
    * RFCは2017-06-09にマージされてた。 `eRFC: Experimentally add coroutines to Rust by alexcrichton · Pull Request #2033 · rust-lang/rfcs <https://github.com/rust-lang/rfcs/pull/2033#issuecomment-309603972>`_
    * `alexcrichton/futures-await <https://github.com/alexcrichton/futures-await>`_
        * Async/await syntax for Rust and the futures crate
    * `rust-lang-nursery/futures-rs: Zero-cost futures and streams in Rust <https://github.com/rust-lang-nursery/futures-rs>`_
        * Zero-cost futures and streams in Rust

HTTPライブラリ
--------------

HTTP/2
++++++

* https://github.com/carllerche/h2
    * HTTP/2のクライアントとサーバ実装。
    * Tokioベース。
    * このライブラリ単体ではHTTP/1.0からのアップグレードやTLSなどはサポートしない。
    * hyperがこのライブラリを使うようになることでフル実装になることを目指している。
    * 最終コミットは3日前。
    * https://github.com/hyperium/hyper/issues/304#issuecomment-357338916
        * 16日前にh2のv0.1が出て、今後hyperへの組み込みが始まっていきそう。

* https://github.com/mlalic/solicit
    * 低レベルのHTTP/2の実装。
    * 高レベルの他のライブラリがこのライブラリを使えるようにするという位置づけ。
    * 特定のIOライブラリのAPIに依存せず、イベントドリブンなIOライブラリでもブロッキングIOのライブラリを使う場合でも同じAPIを提供するべきとのこと。
    * 現時点ではパフォーマンスは主なゴールではない。
    * 最終コミットは1年前。

HTTP/1.1
++++++++

* https://github.com/swindon-rs/tk-http/
    * Full featured HTTP and Websockets library for rust/tokio
    * Status: Beta
    * APIは変えずに将来HTTP/2をサポート予定。
    * Apache2とMITのデュアルライセンス。
    * 最終コミットは19日前。

* https://github.com/SergejJurecko/mio_httpc
    * mio based async and sync http client
    * TLSバックエンドはnative, OpenSSL, rtls (rustls) のどれか1つを選んで使う。
    * Chunked encoding uploadとHTTP/2はTODO。
    * Apache2とMITのデュアルライセンス。
    * 最終コミットは4時間前。

Webフレームワーク
-----------------

以下の2つの記事を読んだ。各レポジトリを見てみるとその後状況が変わっているところもあったが、結論としてはやはりironが無難そう。

* 2017-04-29 `Comparison of Rust Web Frameworks | WIRED IN <https://mayoyamasaki.github.io/post/comparison-of-rust-web-frameworks/#fn:2>`_
* 2017-01-20 `Performance: Iron vs Nickel « Oliver's Development Musings <https://ojensen5115.github.io/rust/performance-nickel-vs-iron>`_


* `iron/iron: An Extensible, Concurrent Web Framework for Rust <https://github.com/iron/iron>`_
    * `hyperベース。 <https://github.com/iron/iron/blob/4c0b68d367597c67ef4879c9b80dcd159508b0e3/Cargo.toml#L33>`__
    * ライセンスはMIT。
    * 最終コミットは3か月前。

* `nickel-org/nickel.rs: An expressjs inspired web framework for Rust <https://github.com/nickel-org/nickel.rs>`_
    * `hyperベース。 <https://github.com/nickel-org/nickel.rs/blob/fd33495934c3f8b85de36823fee5f39c0a748f1f/Cargo.toml#L32-L34>`__
    * ライセンスはMIT。
    * 最終コミットは1か月前。

* `SergioBenitez/Rocket: A web framework for Rust. <https://github.com/SergioBenitez/Rocket>`_
    * rustのnightlyが必要。
    * `hyperベース。 <https://github.com/SergioBenitez/Rocket/blob/f2331a831ababc485269178588804cd49e235db0/lib/Cargo.toml#L34>`__
    * Apache2とMITのデュアルライセンス。
    * 最終コミットは5日前。
    * `将来は非同期IOベースに移行予定。 <https://github.com/SergioBenitez/Rocket/issues/17>`_ （移行時はAPI変わりそう）

直接関係ないけどついでにメモ
----------------------------

WebやHTTPと関係ないが上の記事でJinja2のテンプレートエンジンのRust実装も紹介されていたのでメモ。
`Keats/tera: A template engine for Rust based on Jinja2/Django <https://github.com/Keats/tera>`_

あと multi-producer multi-consumer な channel 実装について調べていたら 
`crossbeam-rs/crossbeam-channel <https://github.com/crossbeam-rs/crossbeam-channel>`_
についてのredditのスレッドの `コメント <https://www.reddit.com/r/rust/comments/7bszr4/crossbeam_rfcs_introduce_crossbeamchannel/dpl6fv1/>`__ で
https://github.com/stjepang/rfcs-crossbeam/blob/channel/text/2017-11-09-channel.md が紹介されていて読んでみると非常にしっかり書かれていたのでこれもメモ。
