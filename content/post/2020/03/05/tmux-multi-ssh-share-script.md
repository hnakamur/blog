---
title: "tmuxで複数サーバー同時オペレーションのセッション共有"
date: 2020-03-05T18:00:51+09:00
---

## はじめに

職場で [tmuxで複数サーバの同時オペレーション – NaviPlus Engineers' Blog](http://tech.naviplus.co.jp/2014/01/09/tmux%E3%81%A7%E8%A4%87%E6%95%B0%E3%82%B5%E3%83%BC%E3%83%90%E3%81%AE%E5%90%8C%E6%99%82%E3%82%AA%E3%83%9A%E3%83%AC%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3/) のスクリプトを使わせて頂いているのですが、リモートワークに伴って他のユーザーの tmux セッションを閲覧したいという話になりました。

当初 tmux をソケットファイルを使うという単純な改変をしてみたのですが、スクリプト内で tmux セッションを作っているので、作業者がこのスクリプトを実行するたびに閲覧者が接続する必要がありました。

そこで閲覧者が一度接続したら、作業者はずっとそのセッション内で作業を継続し、複数サーバー同時オペレーションに切り替えてまた戻ってと行ったり来たりできるようにスクリプトを改変してみました。まだ練習で一度試してみただけですが、うまく動いているようなのでメモしておきます。

## sudo 権限設定で他のユーザーの tmux ソケットの読み取りだけ許可する

踏み台サーバー上で異なる Linux ユーザーで作業する想定ですが、この記事で紹介されている wemux を導入せずにすませたいと思いました。代わりに sudoers の権限設定で実現する方法を [@yamamasa23](https://twitter.com/yamamasa23) さんが考えたのでそれを使うところから始まりました。

具体的には `/usr/bin/tmux -2 -S /tmp/* attach -r -t guest` というコマンドに sudo 権限を付けています。 `tmux` の `attach` コマンドに `-r` オプションも付けているので読み取り専用のみの許可になっています。

[visudo (8)](https://manpages.ubuntu.com/manpages/bionic/en/man8/visudo.8.html) と [suders (5)](https://manpages.ubuntu.com/manpages/bionic/en/man5/sudoers.5.html) を参考にしてシステム管理者が適宜設定します。 operator グループのユーザーに許可する例は以下のような感じです。

```
Cmnd_Alias TMUX = /usr/bin/tmux -2 -S /tmp/* attach -r -t guest

%operator ALL = NOPASSWD: TMUX
```

[tmux (1)](https://manpages.ubuntu.com/manpages/bionic/en/man1/tmux.1.html) の `-2` は 256色表示を強制するオプションなのでお好みで。

## 通常の tmux のセッション共有と接続

複数サーバーでの使い方の前に通常の tmux のセッション共有を説明します。

セッションを公開するには以下のようにして tmux を起動します。

```console
tmux -2 -S /tmp/tmux_share_$USER new -s guest
```

同じマシン上で別のユーザーが以下のコマンドを実行して tmux のセッションに読み取り専用で接続します。
`$CONNECT_USER` の部分は上記の手順でセッションを公開しているユーザー名に置き換えて実行してください。

```console
sudo tmux -2 -S /tmp/tmux_share_$CONNECT_USER attach -r -t guest
```

公開したユーザーが tmux を終了すると接続していたユーザー側の tmux も終了します。
逆に接続したユーザーが切断したい場合は通常のデタッチ操作（tmux のプリフィクスキー、 d）で OK でした。


## `multi_ssh` スクリプトを `tmux` のソケットファイルを使うように改変

次は複数サーバーでの同時オペレーションでもセッションを共有できるようにします。

最初は [tmuxで複数サーバの同時オペレーション – NaviPlus Engineers' Blog](http://tech.naviplus.co.jp/2014/01/09/tmux%E3%81%A7%E8%A4%87%E6%95%B0%E3%82%B5%E3%83%BC%E3%83%90%E3%81%AE%E5%90%8C%E6%99%82%E3%82%AA%E3%83%9A%E3%83%AC%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3/) のスクリプトの `tmux` に `-S /tmp/tmux_share_$USER` のオプションを付けて回るという改変をしてみて、とりあえず動くようになりました。

しかしこのスクリプトは新規に tmux のセッションを作成するようになっているので、作成後に閲覧ユーザーに接続してもらって終了したら接続が切れて、その後の作業でまた tmux を起動したら再度接続してもらう必要があり、ちょっと面倒だなと思いました。

そこで既に tmux を起動している状態から、 tmux の pane を追加して複数サーバーに ssh するようにスクリプトを改変してみました。

```sh
#!/bin/sh
if [ $# -eq 0 ]; then
  echo "Usage: multi_ssh_share hosts..." 1>&2
  exit 2
fi
 
socket=/tmp/tmux_share_$USER
  
### paneの同期モードを一旦解除
tmux -2 -S $socket set-window-option synchronize-panes off
   
### 各ホストにsshログイン
# 最初の1台のホスト名をとっておく
sv1=$1
shift
  
# 残りのホスト用にpaneを作成してからssh
for i in $*; do
  tmux -2 -S $socket split-window
  tmux -2 -S $socket select-layout tiled
  tmux -2 -S $socket send-keys "ssh $i" C-m
done
  
### 最初のpaneを選択状態にして最初の1台にssh
tmux -2 -S $socket select-pane -t 0
tmux -2 -S $socket send-keys "ssh $sv1" C-m
  
### paneの同期モードを設定
tmux -2 -S $socket set-window-option synchronize-panes on
```

## 事前準備

1. 上記のスクリプトを PATH の通った場所において実行パーミションを付けます。ここでは `multi_ssh_share` というファイル名で保存したとします。
2. `~/.bash_aliaes` に以下のようなエイリアスを追加します。

```
alias tmuxshare='tmux -2 -S /tmp/tmux_share_$USER new -s guest'
```

3. `~/.tmux.conf` に以下のようなキーバインド設定を追加します。

```
bind-key -T prefix X confirm-before -p "kill all other panes? (y/n)" "kill-pane -a"
bind e setw synchronize-panes on
bind E setw synchronize-panes off
```

## 使い方

1. 公開するユーザーは上で定義した `tmuxshare` エイリアスで tmux を共有しつつ起動します。

```
$ tmuxshare
```

2. 閲覧するユーザーは以下のコマンドの `$CONNECT_USER` の部分を公開したユーザー名に置き換えて実行します。

```
$ sudo tmux -2 -S /tmp/tmux_share_$CONNECT_USER attach -r -t guest
```

3. 公開するユーザー側で tmux の pane を開いて複数のサーバーに ssh するには以下のように実行します。

```
$ multi_ssh_share sv{01..03}.example.com
```

4. これで tmux の全ての pane にキー入力が同期された状態になりますので、お好みのコマンドを実行します。

5. 実行したいコマンドが完了したら exit で各サーバーの ssh を終了します。

6. tmux のプリフィクスキー、 E を押して tmux の複数 pane にキー入力を同期するのをオフにします。

7. tmux のプリフィクスキー、 X を押すと `kill all other panes? (y/n)` のプロンプトが表示されるので y を押して tmux のカレント以外の全ての pane を閉じます。

このあと引き続き踏み台サーバー上でコマンドを実行しても良いですし、再度 `multi_ssh_share` で複数サーバー同時オペレーションしても良いです。閲覧しているユーザーはその間も接続したままになります。

## この方法の欠点：tmuxの操作画面が作業者と閲覧者の端末サイズの小さいほうになる

実際に試してみると [tmuxで操作画面がterminalウィンドウサイズより小さくなる場合の対応方法 | 技術者魂](http://engineerspirit.com/2017/02/06/post-798/) のスクリーンショットのような画面になり、右下に `(size WWxHH from a smaller client)` (WWとHHは実際の幅と高さのサイズになる）と表示される現象になりました。

ネットで検索すると `tmux attach` のときに `-d` を付けて他のクライアントをでタッチしてから、アタッチするという解決策が出てきますが、これは他のクライアントの接続を切って繋ぎなおすことでセッションを共有しないという話なので、今回のケースでは使えません。

公開側と閲覧側の端末のウィンドウサイズと表示スケール（Windowsだとコントロールパネルのディスプレイの「テキスト、アプリ、その他の項目のサイズを変更する」の%の数値）で変わってくるようです。

端末のウィンドウサイズのほうはディスプレイの解像度により限界がありますし、表示スケールもあまり下げると文字が小さくて見にくいでしょうから、できる範囲で調整して、あとは諦めるしかないかなあと思ってます。
