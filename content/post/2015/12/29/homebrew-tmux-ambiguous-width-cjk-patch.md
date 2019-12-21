+++
Categories = []
Description = ""
Tags = []
date = "2015-12-29T00:53:53+09:00"
title = "ambiguous width cjk patchを当てたhomebrew用tmux"

+++
ほぼ[Homebrewでサクッとpatchを当てる - Qiita](http://qiita.com/macoshita/items/2ee3c15f362103d1e373)のそのままですが、tmuxのバージョンを2.1に上げたものを[hnakamur/homebrew-custom](https://github.com/hnakamur/homebrew-custom)に置きました。

## パッチ適用版tmuxのインストール

```
brew tap hnakamur/custom
brew install tmux-patched
```

## tmux.confへの設定追加

[Homebrewでサクッとpatchを当てる - Qiitaのコメント](http://qiita.com/macoshita/items/2ee3c15f362103d1e373#comment-ab2f10f09aefe1f3d8b6)にある通り、 `~/.tmux.conf` に以下の設定が必要でした。

```
set -g pane-border-ascii on
```
