+++
title="仮想マシンマネージャmultipassをWindowsとmacOSで試してみた"
date = "2019-10-17T06:00:00+09:00"
tags = ["multipass", "virtualization"]
categories = ["blog"]
+++


# はじめに

multipass は私は Linux で [Snapcraft - Snaps are universal Linux packages](https://snapcraft.io/first-snap#) のチュートリアルで snap パッケージを作ってみた時にインストールされたのが初めての出会いでしたが、その時はなんかまた新しい仮想マシンのツールが増えたのかぐらいに思っていました。

そこに [第590回　Windows/macOS/Linuxで使える仮想マシン管理ツール『multipass』：Ubuntu Weekly Recipe｜gihyo.jp … 技術評論社](https://gihyo.jp/admin/serial/01/ubuntu-recipe/0590) の記事を見かけて、Linux以外に Windows と macOS でも使えることを知りました。

私は仕事で Linux のサーバサイドの開発環境を Windows と macOS 上に構築するのに [VirtualBox](https://www.virtualbox.org/) と [Vagrant](https://www.vagrantup.com/) で Ubuntu 仮想マシンを作ってそこで [Linux Containers - LXD](https://linuxcontainers.org/ja/lxd/introduction/) を使って複数のコンテナを作るようにしています。

しかし [Windows 10 WSL 2の詳細が明らかに、VMware/VirtualBoxとの併用不可 | マイナビニュース](https://news.mynavi.jp/article/20190515-823235/) にあるように、 WSL2 が Hyper-V のサブセットを使っていて VirtualBox と共存できないという問題があるので、どうしようか悩んでいました。私は Windows Insiders は使って無いので通常版の Windows で WSL2 がリリースされるのを待っている段階ですがリリースされたらぜひ使いたいのですが、一方で Windows と macOS で構築手順が分かれると構築用のスクリプトのメンテナンスが面倒なので出来れば統一しておきたいという思いもあるからです。

[Is it Possible to Run WSL2 and Oracle VirtualBox? · Issue #4174 · microsoft/WSL](https://github.com/microsoft/WSL/issues/4174) のコメントからリンクされている [virtualbox.org • View topic - VirtualBox 6.0 and Hyper-V](https://forums.virtualbox.org/viewtopic.php?f=6&t=90853&start=60#p445491) によると VirtualBox 6.0 から Hyper-V 環境でも動かすためのサポートが入ったのですが highly pre-alpha という状態で、私も ThinkPad X260 の Windows 10 Pro で試してみたのですがうまく動きませんでした（詳細は失念）。

[CanonicalLtd/multipass: Multipass orchestrates virtual Ubuntu instances](https://github.com/CanonicalLtd/multipass) を見るとLinuxではKVM、WindowsではHyper-V、macOSではHyperKitを使い、WindowsとmacOSではVirtualBoxも使えるとあり、これで上記の問題が解決できるのでは、ということで喜んで試してみました。

macOS 用には [macOS で multipass やってみようぜ - Qiita](https://qiita.com/satokaz/items/ab974af5632d1389add2) という良いまとめ記事があったのでこちらを参考にしつつ試して調べた内容をメモしておきます。

# Windows版とmacOS版のインストール

[Releases · CanonicalLtd/multipass](https://github.com/CanonicalLtd/multipass/releases) にWindows版とmacOS版のインストーラがあるのでダウンロードしてインストールします。今回試したのはバージョン0.8.0です。

# まずWindowsでVirtualBoxのドライバで試す

職場のThinkPadではVirtualBoxを利用中ですぐにHyper-Vを有効には出来ない状態なので、まずはVirtualBoxドライバで試してみました。

現在選択されているドライバは管理者コマンドプロンプトで以下のコマンドで確認できます（一般ユーザのコマンドプロンプトでは権限不足でした）。

```console
C:\>multipass get local.driver
hyperv
```

上記のようにHyper-V無効の環境でも初期状態ではhypervになっています。そこで以下のコマンドを実行しvirtualboxドライバを使うように切り替えます。

```console
multipass set local.driver virtualbox
```

[第590回　Windows/macOS/Linuxで使える仮想マシン管理ツール『multipass』：Ubuntu Weekly Recipe｜gihyo.jp … 技術評論社](https://gihyo.jp/admin/serial/01/ubuntu-recipe/0590) の記事にも書かれていますがドライバの切り替えは気軽に行えるものではなく、インストール直後に設定してそれでずっと使うという感じのようです。

ここからは一般ユーザのコマンドプロンプトで実行可能でした（ただし管理者権限はついたユーザで試していて、管理者権限なしのユーザでも可能かは不明です）。

あと、別の環境で Hyper-V を有効にした Windows 10 Pro と macOS Mojave でも試しました。

# 仮想マシンの基本操作

以下の操作は `multipass` を `multipass.exe` とすれば `wsltty](https://github.com/mintty/wsltty) でも可能でした（ただし後述のようにホストのディレクトリのマウントの初回実行はコマンドプロンプトで行う必要があるようでした）。

## 仮想マシンの作成・起動

以下のようにして仮想マシンを作成・起動します（オプションの説明は `multipass launch -h` を参照してください）。

```console
multipass launch -n primary -c 2 -m 4G -d 100G
```

`-n` オプションを省略すると `petit-shrew` のようなランダムな名前が自動で設定されました。仮想マシンのシェルを実行する `multipass shell` コマンドなどがデフォルトでは `primary` という仮想マシンを対象とするので、仮想マシンを1つだけ作るのであれば上記のように `primary` という名前で作成するのが良いです。

## 仮想マシンのシェル実行

`primary` の仮想マシンの場合は以下のように実行すると、インタラクティブなシェルが起動します。

```console
multipass shell
```

それ以外の場合は `multipass shell petit-shrew` のように仮想マシン名を引数に指定して起動します（`-n` オプションではないので注意。詳細は `multipass shell -h` を参照してください）。

上記のコマンドを実行すると `multipass` ユーザでログインした状態になります。シェルを終了するのは `exit` コマンドを実行するか Ctrl-D を押します。

## ホストのディレクトリのマウント

仮想マシンのホストであるWindowsのディレクトリを仮想マシンにマウントするのは以下のようにします。ディレクトリ名は適宜変更してください。マウント先のディレクトリは自動的に作成されました。

```console
multipass mount C:/Users/hnakamur/foo primary:foo
```

マウント先は `primary` のようにマウント先ディレクトリ名を省略して仮想マシン名だけでも可能です。が、 `/home/multipass/C:/Users/hnakamur/foo` のようなディレクトリにマウントされ、しかも `/home/multipass/C:` ディレクトリの所有者が `root` になってしまいました。

上記のようにマウント先を `primary:foo` のように仮想マシン名とディレクトリの指定にすると `/home/multipass/foo` にマウントされ、所有者も `multipass` ユーザになります。こちらのほうがお勧めです。

マウントの初回実行時は `Enabling support for mounting` というメッセージと `\|/-` の文字がくるくる回るインジケータがしばらく表示されました。初回実行を wsltty から行ったときはこれがいつまでも続いたので待ちきれず端末のウィンドウを閉じました。初回だけコマンドプロンプトから実行しておけば、あとはwslttyからでも問題ないようです。

## 仮想マシンの一覧表示

実行例を以下に示します。

```console
C:\>multipass list
Name                    State             IPv4             Image
primary                 Running           192.168.133.102  Ubuntu 18.04 LTS
```

## 仮想マシンの情報表示

実行例を以下に示します。マウント状態も確認できます。

```console
C:\>multipass info --all
Name:           primary
State:          Running
IPv4:           192.168.133.102
Release:        Ubuntu 18.04.3 LTS
Image hash:     6204b6bff4ce (Ubuntu 18.04 LTS)
Load:           0.22 0.08 0.02
Disk usage:     1.7G out of 96.7G
Memory usage:   3.0G out of 3.9G
Mounts:         C:/Users/hnakamur/foo => foo
                    UID map: -2:default
                    GID map: -2:default
```

## アンマウント

以下のようにマウント先の仮想マシンとディレクトリを指定してアンマウントします。

```console
multipass umount primary:foo
```

## 仮想マシン停止

```console
multipass stop VM名
```

## 仮想マシン起動

```console
multipass start VM名
```

## 仮想マシン削除

`-p` のpurgeオプションを付けて削除します。 `-p` なしだとファイルが残ったままになるらしいです。

```console
multipass delete -p VM名
```

## ヘルプ表示

他にもサブコマンドがあります。 `-h` オプションでヘルプを見るのが手っ取り早いです。

```console
C:\>multipass -h
Usage: multipass [options] <command>
Create, control and connect to Ubuntu instances.

This is a command line utility for multipass, a
service that manages Ubuntu instances.

Options:
  -?, -h, --help  Display this help
  -v, --verbose   Increase logging verbosity, repeat up to three times for more
                  detail

Available commands:
  delete    Delete instances
  exec      Run a command on an instance
  find      Display available images to create instances from
  get       Get a configuration option
  help      Display help about a command
  info      Display information about instances
  launch    Create and start an Ubuntu instance
  list      List all available instances
  mount     Mount a local directory in the instance
  purge     Purge all deleted instances permanently
  recover   Recover deleted instances
  restart   Restart instances
  set       Set a configuration option
  shell     Open a shell on a running instance
  start     Start instances
  stop      Stop running instances
  suspend   Suspend running instances
  transfer  Transfer files between the host and instances
  umount    Unmount a directory from an instance
  version   Show version details
```

# 調査メモ

以下こまごまとしたメモ。


## C++とQt5で書かれている

[CanonicalLtd/multipass: Multipass orchestrates virtual Ubuntu instances](https://github.com/CanonicalLtd/multipass) を見るとソースはC++とQt5で書かれています。 [COPYING.GPL.txt](https://github.com/CanonicalLtd/multipass/blob/v0.8.0/COPYING.GPL.txt) を見るとライセンスは GPLv3 です。

## WindowsでVirtualBoxドライバで試したときのメモ

* ネットワークインタフェース名は `enp0s3` になった。
* IPアドレスは 10.0.2.15/24。なのでVirtualBoxのNATのネットワークアダプタが使われている模様。
* `multipass info --all` の出力で IPv4 のアドレスは N/A と表示。
* VirtualBoxマネージャにはVMは表示されない。
* 仮想マシンのイメージファイルは `C:\Windows\System32\config\systemprofile\VirtualBox VMs\Multipass` 以下に仮想マシン名のディレクトリが作られてそこに置かれている。ファイル名は仮想マシン名 + .vbox。
* `%USERPROFILE%\AppData\Roaming\multipass\client-certificate` というディレクトリに `multipass_cert.pem` と `multipass_cert_key.pem` という鍵と証明書がある。

## WindowsでHyper-Vドライバで試したときのメモ

* ネットワークインタフェース名は `eth0` になった。
* IPアドレスはランダムに割り当てられる（例： 192.168.133.102）。 `multipass info` コマンドのIPv4の欄でも確認可能。
* 仮想マシンのイメージファイルは `C:\Windows\System32\config\systemprofile\AppData\Roaming\multipassd\vault\instances` 以下に仮想マシン名のディレクトリが作られてそこに置かれている。拡張子は `.vhdx` と `.avhdx` 。 また `cloud-init-config.iso` というファイルもあった。
* `%USERPROFILE%\AppData\Roaming\multipass\client-certificate` というディレクトリに `multipass_cert.pem` と `multipass_cert_key.pem` という鍵と証明書がある（これはVirtualBoxドライバの場合と同じ）。

## macOS Mojaveで試したときのメモ

* ネットワークインタフェース名は `enp0s2` になった。
* IPアドレスはランダムに割り当てられる（例： 192.168.64.2）。 `multipass info` コマンドのIPv4の欄でも確認可能。
* 仮想マシンのイメージファイルは `/var/root/Library/Application Support/multipassd/vault/instances/` 以下に仮想マシン名のディレクトリが作られてそこに置かれている。また `cloud-init-config.iso` というファイルもあった。
* `~/Library/Application Support/multipass/client-certificates` ディレクトリに `multipass_cert.pem` と `multipass_cert_key.pem` という鍵と証明書がある。

## 仮想マシン内の/root/.ssh/authorized_keys

私は面倒くさがりなのでホストからrootユーザでsshできるように `~multipass/.ssh/authorized_keys` を `/root/.ssh` にコピーしようとしたら既にファイルがあることに気づきました。内容を確認すると以下のようになっていました。

```console
multipass@primary:~$ sudo cat /root/.ssh/authorized_keys
no-port-forwarding,no-agent-forwarding,no-X11-forwarding,command="echo 'Please login as the user \"multipass\" rather than the user \"root\".';echo;sleep 10" ssh-rsa AAAAB...(snip)...Ybx multipass@localhost
```

`root` ユーザでログインせずに `multipass` ユーザでログインせよとのことです。ここまでして啓蒙してくれているのでおとなしく従おうかなという気になりました。

# おわりに

とりあえず試してみた感じでは良さそうです。VM起動時に `--clout-init` オプションで [cloud-init](https://github.com/cloud-init/cloud-init/) を使った初期設定も行えるのでこちらも試していきたいところです。
