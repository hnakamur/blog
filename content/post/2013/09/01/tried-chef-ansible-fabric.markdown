Title: Chef-soloとAnsibleとFabricを試した感想
Date: 2013-09-01 00:00
Category: blog
Slug: blog/2013/09/01/tried-chef-ansible-fabric

Chef-soloとAnsibleとFabricを試してみたので感想をメモ。どれもそんなに深くは使い込んではいない。

このメモは自分の脳内の考えを整理するためのもので、人が使うことについてどうこう言うつもりはないです。

## Chef-solo

- 書いてみたcookbookはこちら。[hnakamur/chef-cookbooks](https://github.com/hnakamur/chef-cookbooks) [hnakamur/chef-repo](https://github.com/hnakamur/chef-repo)
- クックブックは手順を書くのではなくて結果を書くというのがどうも本質的に違うと私は思ってしまう。料理のレシピだって手順を書くし。書結果がこうあるべきというのはserverspecが出来た今となってはそちらに任せて、クックブックは本来手順を書くべきものだと思う。
- RubyのDSLだけど結局上から順に評価されるので、実は手続きを書いていることになっている。でもファイル単位でしか再利用できないので、一部だけ使いたいと思ってコピペするしかなくなるのが悲しい。
- Berkshelfでコミュニティクックブックをダウンロードして、ラッパークックブックを書くのがベストプラクティスってのが、無駄な苦行に思えてどうしても受け入れられない。自分のニーズに合わせて一から書くほうが早いしコンパクトで見やすい。これってDSLだからそうなるのかなー。
- もしDSLではなくRubyのクラスとして定義するようになっていて、各タスクをメソッドとして定義するようになっていたら、もっと再利用しやすかったのではないかと思う。それってむしろrakeのほうが近い気がする。[Vlad the Deployer](http://rubyhitsquad.com/Vlad_the_Deployer.html)とかVladから切りだされた[rake-remote_task | RubyGems.org | your community gem host](http://rubygems.org/gems/rake-remote_task)ベースで組み立てる感じ。なんでVladは人気出なかったのかな～。Capistranoよりいいと思うんだけど。

## Ansible

- 書いてみたplaybookはこちら。[hnakamur/ansible-playbooks](https://github.com/hnakamur/ansible-playbooks)
- 手続きを記述するのにyamlというのは力不足。基本は順次処理で実行条件で実行するしないの制御ができるだけ。単一のタスクではパラメータでループはできるけど、複数のタスクをまとめてループとかはできない。
- モジュールとして用意されている処理はすっきり書けるが、そうでない場合はshellモジュールでゴリゴリ書くか自前モジュールを作るかになる。自前モジュールを作るのは簡単だが配布の仕組みが確立されていないので、自前でコピーする必要がある。
- やはり手続きはプログラミング言語で記述するほうが自由度は高いと感じた。

2013-09-02 追記

- 訂正です。自作モジュール配布の仕組みは標準で用意されていました。libraryフォルダにモジュールを置いておけば自動で読み込まれます。[Bundling Ansible Modules With Playbooks](http://www.ansibleworks.com/docs/bestpractices.html#bundling-ansible-modules-with-playbooks)
- それ以外の場所に置きたい場合は環境変数ANSIBLE\_LIBRARYを設定するかコマンドラインオプションに--module-pathを指定すればOKです。 [Module Development | AnsibleWorks](http://www.ansibleworks.com/docs/moduledev.html#module-development)
- [しろう](https://twitter.com/r_rudi)さん、[ご指摘](https://twitter.com/r_rudi/status/374375071000702976)ありがとうございました！

## Fabric

- 書いてみたfabfileはこちら。[hnakamur/my-fabfiles](https://github.com/hnakamur/my-fabfiles)
- Pythonで手続きを書けるので、処理の流れは自由に書けて良い。
- rpmがインストール済みならダウンロードしないといった処理も自然に書ける。chefやansibleだと素直に書くとsha256sumを計算するという処理が毎回走ってしまう。自分で条件判定処理を記述して実行条件をつければ可能だが、ごちゃごちゃして見づらくなる。
- 細かく関数に分けておけば必要なところだけの再利用も簡単。
- Ansibleのモジュールのようなものも、ユーティリティ関数を書くだけの話なので、レシピを書くのとなんら変わらない。レシピとモジュールの開発を同じ枠組みでできるのは便利。モジュールつくって本家にpull requestとかしなくてもすぐ使えるし。
- 基本的にはコマンドを順次実行するだけという思想なので、冪等性について考慮した設計になってないのは不便。
- vagrantでfabricでprovisionするプラグインも作ってみた。 [hnakamur/vagrant-fabric-provisioner](https://github.com/hnakamur/vagrant-fabric-provisioner)
- テンプレートからファイル生成も標準では毎回上書きされてしまう。Ansibleと同じようにチェックサムを計算して違う時だけ上書きするような関数を自作してみた。[my-fabfiles/fabfile/common/lib/template.py at master · hnakamur/my-fabfiles](https://github.com/hnakamur/my-fabfiles/blob/master/fabfile/common/lib/template.py) 変更したかどうかも戻り値で返すようにした。これによって変更した場合だけサービス再起動とかは可能になった。
- が、本当はchefのnotificationのように、ホスト毎の処理が終わった後にサービス再起動をまとめて実行したいところ。post-processキューみたいな仕組みが必要そう。
- 処理をpythonで書けるのはいいのだが、リモートでの処理は基本コマンド実行になるのでpythonで直接ファイルを読み書きとかは出来ない。これがもどかしい感じ。
- 今バージョン1.7で2.0でオーバーホールするRoadmapのようだがどうなっていくかまだわからない感じ。

## 思いつき

- ふと思いついたのだが、Goでライブラリを用意してレシピもGoで書くのは面白いかも。
- Goならクロスコンパイルも簡単なので、ターゲットマシン用のバイナリを生成してrsync/scpでコピーしてターゲットマシン上で実行するという手が使える。するとファイルの読み書きもコマンド実行でもGoの関数からでもどちらでも実行できる。
- dockerみたいに一つのバイナリで複数の役割を持てせるようにすれば、デーモンとして実行しておいて、さらにsshからコマンド実行して制御ということも可能かも。あるいはエージェントみたいにして相互通信とかサーバと通信して連携するという道も有り得る。
- よくよく考えたら別にGoでなくても、言語処理系とライブラリとレシピのファイルをrsyncで送り込んで実行すれば同じか。
- でもGoならタスクキューとか作ってgoroutineで並列処理したり、channelで連携制御したりというのが書きやすそうなので夢は広がるな〜。

まずはローカルでコマンド実行するとか、テンプレートからファイル生成する（但し変更が無い場合は上書きしない）ユーティリティ関数群のライブラリを作ってみようということで今作り中。

他にもいろいろやることがあるので、ツールとして完成するところまで行くかは期待薄。でも、ツールとしては完成しなくてもユーティリティ関数のライブラリでも有効活用できるしGoの勉強にもなるので、気が向いた時にマイペースでやってみよう。

2013-09-02 追記その2

- [Ansibleで自作モジュールを作成してplaybookと一緒に配布 - Qiita \[キータ\]](http://qiita.com/hnakamur/items/b20458110777c3ceea3a)に書きましたが、Ansibleのモジュール作成は簡単です。一定のルールに従ってスクリプトファイルを作るだけです。
- しかも、今頃気づいたのですが、モジュールはターゲットマシン上で実行されます。なので、例えばPythonで書く場合は直接ターゲットマシン上のファイルを読み書きできるわけです。
- ということで、FabricはPythonだけどターゲットマシン上で実行されないのでもどかしいと思っていた問題はAnsibleのモジュールでは無関係です。
- あとは、処理のフローが複雑な箇所はモジュールとして実装することにすれば、全体の流れはyamlで順次処理というのでも殆どの場合はカバーできるような気がしてきました。
