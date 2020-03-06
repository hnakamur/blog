---
title: "wsl-ssh-agentでWindows Subsystem for LinuxからWindowsのssh-agentを使う設定手順"
date: 2020-03-06T18:48:43+09:00
---

## はじめに

[Windows 10 に OpenSSH クライアントをインストール · hnakamur's blog](/blog/2020/02/22/install-openssh-client-to-windows10/) で Windows の ssh-agent を使いだしてから Windows Subsystem for Linux （以下WSLと略）からも使いたいと思うようになりました。

調べてみると [wsl-ssh-agent](https://github.com/rupor-github/wsl-ssh-agent) で出来るそうなので設定手順をメモ。

## 設定手順

### wsl-ssh-agent のダウンロードと解凍

[Releases · rupor-github/wsl-ssh-agent](https://github.com/rupor-github/wsl-ssh-agent/releases) から最新版の wsl-ssh-agent.7z をダウンロードします。

解凍するには [ダウンロード | 7-Zip](https://sevenzip.osdn.jp/download.html) から 7-Zip をダウンロードするか、あるいは WSL で p7zip パッケージを入れて 7zr コマンドを使います。

解凍すると `wsl-ssh-agent-gui.exe` と `changelog.txt` というファイルが作られますので、 `wsl-ssh-agent-gui.exe` をお好みの場所に配置します。

私は `C:\wsl-ssh-agent` というフォルダーを作って `C:\wsl-ssh-agent\wsl-ssh-agent-gui.exe` に置きました。

### ショートカットを作成してスタートアップに配置

以下のようにリンク先を指定してショートカットを作成します。
`-socket` オプションに指定したパスにソケットファイルが作られます。パスは適宜変更してください。

```
C:\wsl-ssh-agent\wsl-ssh-agent-gui.exe -socket C:\Users\hnakamur\.ssh\ssh-agent.sock
```

Windows キー + R で 「ファイル名を指定して実行」ダイアログを開き `shell:startup` と入力してスタートアップのフォルダーを開き、上記で作成したショートカットをそこに移動します。

### WSL の Ubuntu で `SSH_AUTH_SOCK` 環境変数を設定

次は WSL の Ubuntu の設定です。

`~/.profile` で以下のように `SSH_AUTH_SOCK` 環境変数を設定します。
上記で `wsl-ssh-agent-gui.exe` の `-socket` に指定したパスを WSL からアクセスできるよう `/mnt/c/...` の形式で指定します。

```
SSH_AUTH_SOCK=/mnt/c/Users/hnakamur/.ssh/ssh-agent.sock
export SSH_AUTH_SOCK
```

### WSL で元々使っていた ssh-agent 用の設定を削除

私の場合は [Windows 10のWindows Subsystem for Linux（WSL）を日常的に活用する - ククログ(2017-11-08)](https://www.clear-code.com/blog/2017/11/8.html) で紹介されていた weasel-pageant と WSL の Ubuntu の keychain パッケージを使っていました。

`~/.bashrc` に以下のような設定を書いていたのでこれを消します。

```
eval $(/mnt/c/Program\ Files\ \(x86\)/weasel-pageant/weasel-pageant -r -a "/tmp/.weasel-pageant-$USER")
eval $(keychain --eval $HOME/.ssh/id_ed25519)
```

### WSL の端末を再起動して動作確認

私は [Windows Terminal](https://github.com/microsoft/terminal) を使ってるので、これのウィンドウを一旦閉じて終了し、再度実行します。

`ssh-add -l` を実行して登録済みの鍵一覧を確認し、未登録なら `ssh-add 鍵ファイル名` で追加します。

手順は以上です。

## 脱線: wsl-ssh-agent の実装についてのメモ

[wsl-ssh-agent](https://github.com/rupor-github/wsl-ssh-agent) は Go で書かれているので一部をちょっとだけ見てみました。

まず README を見ると wsl-ssh-agent-gui.exe は [Go 1.12 から使えるようになった](https://golang.org/doc/go1.12#syscall) AF_UNIX ソケットを使っているそうです。

あと [systray サブパッケージの README](https://github.com/rupor-github/wsl-ssh-agent/tree/a305054739d6ce1fa6261a8b4cb673df083b160e/systray) を見ると github.com/getlantern/systray をフォーク、改変しているそうです。

変更内容が気になったので [Diff from github.com/getlantern/systray@6f0e5a3 to github.com/rupor-github/wsl-ssh-agent@a305054](https://gist.github.com/hnakamur/cb07c460b81873a2290565f4f180672f) に貼っておきました。

ロガーを Go 標準の log パッケージに変更しているのと、 `WM_WTSSESSION_CHANGE` という Windows のメッセージに対応して処理を行うようになっていました。

`WM_WTSSESSION_CHANGE` を初めて知ったので参考情報を貼っておきます。

* [WM_WTSSESSION_CHANGE message (Winuser.h) - Win32 apps | Microsoft Docs](https://docs.microsoft.com/en-us/windows/win32/termserv/wm-wtssession-change)
* [ユーザー切り替えに対応する | re-Think things](https://togarasi.wordpress.com/2009/07/11/%E3%83%A6%E3%83%BC%E3%82%B6%E3%83%BC%E5%88%87%E3%82%8A%E6%9B%BF%E3%81%88%E3%81%AB%E5%AF%BE%E5%BF%9C%E3%81%99%E3%82%8B/)
