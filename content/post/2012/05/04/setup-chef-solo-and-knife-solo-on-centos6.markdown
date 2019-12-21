---
layout: post
title: "CentOS6でchef-soloとknife-soloをセットアップ"
date: 2012-05-04
comments: true
categories: [CentOS, chef-solo]
---
## なぜ？

[chef-soloで作業環境構築の自動化 | ひげろぐ](http://higelog.brassworks.jp/?p=654) を参考に、Chefサーバは使いたくないけど、chef-soloとknifeを使いたい！
ということで、そういう環境を作るためのスクリプトを作りました。
だいぶ前から試行錯誤してたけど、ようやくできたので公開。


## セットアップスクリプト

chef-soloやknifeはrootユーザで実行する想定です。

このスクリプトではruby、rubygems、ruby-devel、make、gccをyumで、
chefとknife-soloをgemでインストールします。

chef-soloやknife実行時にオプションをなるべく指定不要にするため、設定ファイルはデフォルトの場所に配置しています。

* /etc/chef/solo.rb
* /root/.chef/knife.rb

その他の詳細は
[install_chef-solo.sh](https://github.com/hnakamur/setup_linux/blob/master/centos6/install_chef-solo.sh)
を参照してください。

ちょっと注意が必要なのは、shのヒアドキュメントで<code>\`hostname\`</code>が展開されるのを避けるために、<code>\\\`hostname\\\`</code>とエスケープしていることです。
＃余談ですが、markdownだとバックスラッシュやバックティックはエスケープしないといけないんですね。


knife.rbの設定は
[Base "knife" configuration for a standard chef-solo setup — Gist](https://gist.github.com/1039666) を書き換えて作りました。が、まだよく理解していません。


## セットアップ手順

特に設定変更が不要であれば
```
curl https://raw.github.com/hnakamur/setup_linux/master/centos6/install_chef-solo.sh | sudo sh
```
でセットアップできます。変更したい場合はとってきて書き換えてから実行してください。


## クックブック作成例

例えば

```
knife cookbook create ntp
```

と実行すると、/etc/chef/site-cookbooks/ntp/ 以下にフォルダ構成とファイルが作られます。あとは編集して作ります。


## 実行例


/root/.chef/chef.json
```
{
  "run_list":["recipe[ntp]"]
}
```
というファイルを用意して
```
sudo chef-solo -j /root/.chef/chef.json
```
で実行します。


## 私のスタンス
minimalistな私は正直 [Chef](http://wiki.opscode.com/display/chef/Home) はそんなに好きじゃないです。

[Architecture](http://wiki.opscode.com/display/chef/Architecture) を見ると、CouchDB, Solr, RabbitMQ が必要って、高々サーバをセットアップするのになんでこんなにいろいろ稼働させる必要があるの？って感じてしまいます。セットアップ手順が自動化されたとしても、自分のマシンでそれだけのサーバが動いているのがもったいない、無駄にマシンリソースを消費してエコじゃない、と思います。

そもそも私がやるような3台構成ぐらいの環境構築にそこまで大掛かりな仕組みはいらないというのもありますし。

[(R)?ex - A simple framework to simplify systemadministration](http://rexify.org/) はsshの鍵認証またはパスワード認証で接続してリモートで処理を実行できるのでこちらのほうが好きです。リモートマシンのセットアップにsshサーバ以外に何か必要というのは、なんか違う気がするんですよね。

それからクックブック1つに対して、フォルダやファイルがたくさんできるのもあまり好きじゃないです。設定管理ツールじゃなくてパッケージ管理ツールですけどHomebrewはFormulaが1つのrubyスクリプトでこれは非常に編集が楽なんです。RexはRexfileにテンプレートファイルを含めることも可能なので

あと処理を手続き的に記述するではなく、最終的な状態を宣言的に記述するというスタイルですが、これも限定的だと思っています。結局のところ、複雑な処理だと処理順序も関係するので、やらせたいことを手続き的にかける方がストレートなのかなと。実行する必要があるかチェックする処理を最初に入れて、それを含めた一連の処理を一つのコマンドとして提供すれば、利用側のコードはシンプルになるのでそれで十分だと思います。

あと、実行対象の処理をJSONファイルに書いて、ファイル名を引数で指定して実行ってのもイケてない。rakeやRexのようにタスクを引数に指定させて欲しいです。

と文句ばかり言っているようですが、DevOpsを提唱したopscode.comが出しているツールだし、一度は使ってみるべきということで。あと、まわりでも使っているので、ツールは揃えておいたほうが良いかなという思いもあります。私自身はいいのですが、まわりで使わされる人が何種類も覚えることを強要されるのは無駄だろうし。
