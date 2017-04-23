MastodonのER図を生成してみた
############################

:date: 2017-04-24 00:28
:tags: mastodon
:category: blog
:slug: 2017/04/24/mastodon-er-diagram

はじめに
--------

`voormedia/rails-erd: Generate Entity-Relationship Diagrams for Rails applications <https://github.com/voormedia/rails-erd>`_
を使って
`tootsuite/mastodon: A GNU Social-compatible microblogging server <https://github.com/tootsuite/mastodon/>`_
のER図を生成してみました、というだけの記事です。

`Relax Ruby version requirement (#1901) · tootsuite/mastodon@0611209 <https://github.com/tootsuite/mastodon/commit/0611209141d1dd446fcf2345084cef00538f6ee7>`_ のコミットに対して
生成したPDFが
`mastodon-er-diagram.pdf <{attach}/files/2017/04/24/mastodon-er-diagram.pdf>`_ です。
たぶん今後更新しないので新しいER図が欲しい方は自分で生成してください。

生成手順
--------

生成時にデータベースにアクセスするので、mastodonのソースを git clone しただけではだめでデータベースを構築しておく必要があります。

今回は `hnakamur/mastadon-ansible-playbook: さくらのVPSでmastodonをセットアップするAnsibleプレイブック <https://github.com/hnakamur/mastadon-ansible-playbook>`_ で構築した環境で作業しました。

rails-erdを動かすにはgraphivizが必要なのでインストールします。

.. code-block:: console

    sudo apt install graphviz

mastodonの :code:`Gemfile` に以下の行を追加しました。
本来は :code:`group :development do` のブロック内に書くべきなのでしょうが、作業した環境はproductionのデータベースしかないので、ブロック外に追記しました。

.. code-block:: ruby

    gem 'rails-erd'


あとは

.. code-block:: console

    bundle install

でインストールして

.. code-block:: console

    RAILS_ENV=production bundle exec erd

でER図のpdfを生成しました。erd.pdf というファイル名で生成されます。
