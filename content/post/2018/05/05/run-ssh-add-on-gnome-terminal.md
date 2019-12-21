+++
title="GNOMEの端末でssh-addを自動実行"
date = "2018-05-05T00:30:00+09:00"
tags = ["ubuntu", "ssh-agent"]
categories = ["blog"]
+++


## はじめに

UbuntuのGNOME環境では「自動起動するアプリケーションの設定」でSSH鍵エージェントが設定されています。
端末を起動したときに自動的に `ssh-add` で秘密鍵を追加して一度だけパスフレーズを入力すれば
後はパスフレーズ無しで行けるようにするための設定メモです。

## 「自動起動するアプリケーションの設定」でSSH鍵エージェントの設定

予め設定されている内容を参考までにメモ。

* 名前: SSH鍵エージェント
* コマンド: `/usr/bin/gnome-keyring-daemon --start --components=ssh`
* 説明: GNOMEキーリング: SSHエージェント

## ssh-addの自動実行設定

[Windows 10のWindows Subsystem for Linux（WSL）を日常的に活用する - ククログ(2017-11-08)](http://www.clear-code.com/blog/2017/11/8.html) を参考にして `~/.bashrc` に以下の設定を追加することにしました。

以下の例では秘密鍵のパスが `$HOME/.ssh/id_rsa` という想定ですが環境に応じて調整してください。

```bash
# Add ssh key if not added yet.
if [ -S "$SSH_AUTH_SOCK" ]; then
  if ! ssh-add -l > /dev/null; then
    ssh-add "$HOME/.ssh/id_rsa"
  fi
fi
