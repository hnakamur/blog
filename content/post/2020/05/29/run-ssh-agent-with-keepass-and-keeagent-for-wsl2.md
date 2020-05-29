---
title: "KeePassとKeeAgentでWSL2用にssh-agentを動かす"
date: 2020-05-29T19:59:34+09:00
---

## はじめに

[wsl-ssh-agentでWindows Subsystem for LinuxからWindowsのssh-agentを使う設定手順 · hnakamur's blog](/blog/2020/03/06/setup-wsl-ssh-agent/) は快適だったのですが WSL2 では使えないことが分かりました。

[wsl-ssh-agent](https://github.com/rupor-github/wsl-ssh-agent) の
[WSL 2 compatibility](https://github.com/rupor-github/wsl-ssh-agent#wsl-2-compatibility) に回避策が書いてあるのを見つけ
[Use an ssh-agent in WSL with your ssh setup from windows 10](https://medium.com/@pscheit/use-an-ssh-agent-in-wsl-with-your-ssh-setup-in-windows-10-41756755993e) も読んで設定してみたので手順をメモしておきます。

## KeePass と KeeAgent プラグインをセットアップ

[KeePass Password Safe](https://keepass.info/) はパスワードマネージャーですが、 [KeeAgent – lechnology.com](https://lechnology.com/software/keeagent/) プラグインを入れると experimental ではありますが ssh-agent が動かせるんですね。

私は以前 KeePass から [KeePassXC Password Manager](https://keepassxc.org/) に乗り換えていたのですが、今回 KeePass に戻しました。

セットアップの手順は以下の通りです。

1. [Downloads - KeePass](https://keepass.info/download.html) から KeePass 2.x のインストーラーをダウンロードしてインストール。
2. [KeeAgent の Download](https://lechnology.com/software/keeagent/#download) から KeeAgent の zip ファイルをダウンロード。
3. KeePass を起動し [Tools]/[Plugins] メニューを開き、 Plugins ダイアログ下部の [Open Folder] ボタンを押す。
4. エクスプローラーで KeePass のプラグインのフォルダーが開いたら、 KeeAgent の zip ファイル内の `KeeAgent.plgx` ファイルをそこにコピー。
5. KeeAgent プラグインのインストールが終わったら KeePass の [Tools]/[Options] メニューを選んで Options ダイアログを開き KeeAgent タブの [Enable agent for Windows OpenSSH (experimental)] チェックボックスにチェックして [OK] ボタンを押す。

## npiperelay.exe のセットアップ

[Releases · rupor-github/wsl-ssh-agent](https://github.com/rupor-github/wsl-ssh-agent/releases/tag/v1.4.2) の最新リリース "WSL 2 workaround" の Assets の `wsl-ssh-agent.7z` をダウンロードします。

解凍のために [圧縮・解凍ソフト 7-Zip](https://sevenzip.osdn.jp/) をダウンロード、インストールします。

インストール後、エクスプローラーで `wsl-ssh-agent.7z` を選んでポップアップメニューを開き [7-Zip]/[展開...] メニューを選んで解凍します。

wsl-ssh-agent というフォルダーが作られますので、お好みの場所に移動します。

ここでは `C:\wsl-ssh-agent` に移動したとして説明を続けます。

このフォルダーには今回使用する `npiperelay.exe` が含まれています。

## WSL2 の Ubuntu で socat パッケージをインストール

以下のコマンドを実行してインストールします。

```console
sudo apt update
sudo apt -y install socat
```

## WSL2 の Ubuntu で ~/.bashrc を編集

[WSL 2 compatibility](https://github.com/rupor-github/wsl-ssh-agent#wsl-2-compatibility) に書いてある設定のうち `npireplay.exe` のパスを自分の環境に応じて書き換えて `~/.bashrc` に追記します。

```txt
export SSH_AUTH_SOCK=$HOME/.ssh/agent.sock
ss -a | grep -q $SSH_AUTH_SOCK
if [ $? -ne 0 ]; then
    rm -f $SSH_AUTH_SOCK
    ( setsid socat UNIX-LISTEN:$SSH_AUTH_SOCK,fork EXEC:"/mnt/c/wsl-ssh-agent/npiperelay.exe -ei -s //./pipe/openssh-ssh-agent",nofork & ) >/dev/null 2>&1
fi
```

## WSL2 で ssh-agent を使う

WSL2 の端末を開きなおすか `exec $SHELL -l` を実行すれば ssh-agent が使える状態になります。

あとは普段通り `ssh-add -l` で登録済みの鍵一覧表示、 `ssh-add ~/.ssh/id_ed25519` などで鍵を ssh-agent に追加します。

## KeePass + KeeAgent の通知設定

デフォルトでは ssh-agent の鍵を利用するたびに Windows の通知バナーが表示され、音が鳴ります。

Windows のタスクバーのアクションセンターのアイコン（あるいは Win+A キー）を押してアクションセンターを開き [通知の管理] を押します。

[送信元ごとの通知の受信設定] の一覧で KeePass をクリックしてお好みで調整します。
