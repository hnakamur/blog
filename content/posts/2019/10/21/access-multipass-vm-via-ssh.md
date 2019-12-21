+++
title="multipassのVMにsshで接続"
date = "2019-10-21T06:00:00+09:00"
tags = ["multipass", "virtualization"]
categories = ["blog"]
+++


# はじめに

`multipass shell` サブコマンドでmultipassで作成したVMにアクセスできますが、ホストから ssh したいケースもあります。

というわけでセットアップ手順のメモです。

# sshの秘密鍵をコピー

Windows の WSL の場合。

```console
install -m 600 /mnt/c/Windows/System32/config/systemprofile/AppData/Roaming/multipassd/ssh-keys/id_rsa ~/.ssh/multipass.id_rsa
```

macOSの場合。

```console
sudo install -m 600 -o $USER -g $(id -g) /var/root/Library/Application\ Support/multipassd/ssh-keys/id_rsa ~/.ssh/multipass.id_rsa
```

# ~/.ssh/configにエントリ追加

~/.ssh/config に以下のようなエントリを追加します。ホスト名はお好みでIPアドレスはVMのアドレスに合わせます。

```text
Host mp-primary
  Hostname 192.0.2.2
  User multipass
  IdentityFile ~/.ssh/multipass.id_rsa
```

# VirtualBoxではうまくいかず

VirtualBoxドライバを使っているmultipassの環境ではIPアドレスに10.0.2.15を指定して試してみたのですがつながりませんでした。 Vagrant で使っていた時もNATアダプターのインタフェースとは別にホストオンリーアダプターでネットワークインターフェースを作る必要があったのですが、multipassでの方法は検索してみましたがわかりませんでした。

Hyper-V なら上記の方法で問題なく使えました。私はHyper-Vのほうに移行しようとしているのでVirtualBoxのほうは深追いしません。

