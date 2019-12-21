+++
title="MastodonのER図を生成してみた"
date = "2017-04-24T00:28:00+09:00"
tags = ["mastodon"]
categories = ["blog"]
+++


## はじめに

[voormedia/rails-erd: Generate Entity-Relationship Diagrams for Rails applications](https://github.com/voormedia/rails-erd)
を使って
[tootsuite/mastodon: A GNU Social-compatible microblogging server](https://github.com/tootsuite/mastodon/)
のER図を生成してみました、というだけの記事です。

[Relax Ruby version requirement (#1901) · tootsuite/mastodon@0611209](https://github.com/tootsuite/mastodon/commit/0611209141d1dd446fcf2345084cef00538f6ee7) のコミットに対して
生成したPDFが
[mastodon-er-diagram.pdf]({attach}/files/2017/04/24/mastodon-er-diagram.pdf) です。
たぶん今後更新しないので新しいER図が欲しい方は自分で生成してください。

## 生成手順

生成時にデータベースにアクセスするので、mastodonのソースを git clone しただけではだめでデータベースを構築しておく必要があります。

今回は [hnakamur/mastadon-ansible-playbook: さくらのVPSでmastodonをセットアップするAnsibleプレイブック](https://github.com/hnakamur/mastadon-ansible-playbook) で構築した環境で作業しました。

rails-erdを動かすにはgraphivizが必要なのでインストールします。

```console
sudo apt install graphviz
```

mastodonの `Gemfile` に以下の行を追加しました。
本来は `group :development do` のブロック内に書くべきなのでしょうが、作業した環境はproductionのデータベースしかないので、ブロック外に追記しました。

```ruby
gem 'rails-erd'
```

あとは

```console
bundle install
```

でインストールして

```console
RAILS_ENV=production bundle exec erd
```

でER図のpdfを生成しました。erd.pdf というファイル名で生成されます。
