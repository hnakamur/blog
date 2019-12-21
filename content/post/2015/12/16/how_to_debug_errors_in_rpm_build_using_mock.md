+++
Categories = []
Description = ""
Tags = ["mock", "rpmbuild"]
date = "2015-12-16T01:10:33+09:00"
title = "mockを使ったrpmビルドが失敗した時の調査方法"

+++

## はじめに
[nginxのカスタムrpmをmockでビルドできることを確認してからcoprでビルド・配布する環境を作りました · hnakamur's blog at github](/blog/2015/12/15/using_mock_and_copr_to_build_nginx_rpm_on_docker/)でspecファイルを書いている最中はmockでのrpmのビルドに失敗することがよくあります。

私は「なんとなくこんな感じか？」と書いて動かしてみてエラーを見て修正していくスタイルなので、失敗時の調査は重要です。

## ビルドログ

`sudo mock -r epel-7-x86_64 --rebuild ${srpmファイル名}` のように実行してビルドした場合、 `/var/lib/mock/epel-7-x86_64/result/` に `build.log` というファイルができるのでそれを見ます。

## mockコマンドでchroot環境内に入る

[mock(1)のmanページ](http://linux.die.net/man/1/mock)によると `sudo mock -r epel-7-x86_64 --shell` でchroot環境内に入ることが出来ます。 `exit` で抜けます。

mockで作られるchroot環境はビルドに必要な最低限のパッケージしかインストールされておらず、 `vim` や `less` も使えません。 `yum` で入れようにも `yum` も無いと言われてしまいます。

chroot環境に入る前に `sudo mock -r epel-7-x86_64 --install vim less` のようにしてインストールしておけばchroot内でvimやlessが使えます。

あるいはchroot外で `/var/lib/mock/epel-7-x86_64/root/` 配下のファイルをvimやlessで見るという手もあります。


## chroot環境内のrpmビルドディレクトリ

chroot環境内では `/builddir/build/` 以下に `BUILD`, `BUILDDIR`, `SOURCES`, `SPECS` などのディレクトリが作られているので、これらの中を見ればビルド失敗時の状況を調べられます。


## chroot環境内でファイルを修正してビルドを再実行

mockを使ったrpmビルドはchroot環境を作成してその中で行われるのですが、毎回chroot環境を作るところからやっていると時間がかかって効率が悪いです。

ですので、chroot環境内のspecファイルや `SOURCES` ディレクトリ下のファイルを直接修正して、その後 `rpmbuild -bb ${specファイル名}` でrpmのビルドを再度試します。


## 修正したファイルをdockerコンテナ外に取り出す

修正のきりが良い所で、chroot環境内の修正したファイルを `docker cp` コマンドでdockerコンテナ内からコンテナ外に取り出します。

まずdockerホストで `docker ps` コマンドでコンテナIDかコンテナ名を調べます。

```
$ docker ps
CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
363ad4f85fda        nginxrpm            "/bin/bash"         18 hours ago        Up 18 hours                             romantic_fermi
```

次に `docker cp` コマンドでファイルをコピーします。例えばこんな感じです。

```
$ docker cp romantic_fermi:/var/lib/mock/epel-7-x86_64/root/builddir/build/SPECS/nginx.spec SPECS/nginx.spec
```

取り出した修正ファイルはgitにコミットして、さらに修正作業を続けていきます。

修正が一通り終わったら、クリーンな状態からビルドが成功することを確認するため、dockerコンテナを一度破棄して[nginxのカスタムrpmをmockでビルドできることを確認してからcoprでビルド・配布する環境を作りました · hnakamur's blog at github](http://localhost:1313/blog/2015/12/15/using_mock_and_copr_to_build_nginx_rpm_on_docker/) の手順で再度ビルドしてみます。これでエラーが出なければOKです。

## まとめ
mockを使ったrpmのビルドが失敗した場合の調査方法を紹介しました。もっと良い方法などありましたら、ぜひ教えてください。
