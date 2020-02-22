---
title: "Hyper-VとmultipassでUbuntu VMを起動してcloud-initで初期化する手順"
date: 2020-02-22T23:45:32+09:00
---

## Windows では multipass から Hyper-V に移行してました

[仮想マシンマネージャmultipassをWindowsとmacOSで試してみた  hnakamur's blog](/blog/2019/10/17/multipass-on-windows-and-macos/) を書いた後しばらく使っていましたが、Windows では Hyper-V を直接使うように切り替えました。

移行の主な理由は `vEthernet (Default Switch)` の IP アドレスが Windows 再起動の度に変わってしまうからです。

`multipass のインスタンス名.mshome.net` で名前解決できると [イシューのコメント](https://github.com/canonical/multipass/issues/1153#issuecomment-546940937) で教わったのですが、私は LXD で複数コンテナを起動するので 1 つのインスタンスにつき 1 つのホスト名では不足でした。

ググると固定する方法も見つかったのですが Windows Update でバージョンが上がるとその方法は使えなくなったという記事もありました。

そこで [Hyper-VのWindows NAT機能を使ってVMのIPアドレスを固定](/blog/2019/10/29/static-ip-address-with-hyper-v-nat/) するようにしました。

その後 [BenjaminArmstrong/Hyper-V-PowerShell](https://github.com/BenjaminArmstrong/Hyper-V-PowerShell) で multipass 無しで Hyper-V だけで VM を作成できるようになったので、これを改変して自分用に手順を整備しました。

## 私が cloud-init で行う初期化の概要

### multipass での cloud-init を使った VM の初期化
macOS では引き続き multipass を使います。
multipass バージョン 1.0.0 の cloud-init の初期化には [5分の時間制限](https://github.com/canonical/multipass/blob/v1.0.0/src/daemon/daemon.cpp#L78) がありますので、最低限の初期化のみを行うようにします。

`multipass launch` の `--cloud-init` オプションには [cloud-init](https://cloud-init.io/) の user-data のファイルを指定できます。
ドキュメントのサイトに [user-data の例](https://cloudinit.readthedocs.io/en/latest/topics/examples.html) と [module のドキュメント](https://cloudinit.readthedocs.io/en/latest/topics/modules.html) があります。

いろいろ試した結果、以下のような設定にすることにしました。

```yaml
#cloud-config
locale: en_US.UTF8
timezone: Asia/Tokyo
package_upgrade: true
package_reboot_if_required: true
apt:
  primary:
    arches:
    - amd64
    - default
    uri: http://jp.archive.ubuntu.com/ubuntu/
password: $6$...SALT...$...HASHED_PASSWORD_HERE...
chpasswd:
  expire: false
ssh_authorized_keys:
- |
  ssh-ed25519 ...YOUR_PUBLIC_KEY_HERE...
```

上記のうち `password` と `ssh_authorized_keys` の内容は個人ごとに変えるので、 git レポジトリに含めるサンプルファイルには含めたくありません。

ちなみに multipass を使うと ssh の鍵ペアを生成して、公開鍵を VM のデフォルトユーザ `ubuntu` の `~/.ssh/authorized_keys` に追加してくれるのでそれを使えば良いのですが、 Windows で Hyper-V で VM を作成する場合は自分で作成した鍵ペアの公開鍵を追加するので揃えています。

そこでこの 2 つ以外を書いた YAML ファイルを入力とし、この 2 つを追加したファイルを出力して使うことにします。

### Hyper-V での cloud-init を使った VM の初期化

cloud-init の `user-data` に関しては前項と同じです。

Hyper-V での cloud-init ではさらに [ネットワーク設定](https://cloudinit.readthedocs.io/en/latest/topics/network-config.html) で Hyper-V の `vEthernet (WinNAT)` を使った静的 IP アドレスの設定を行います。

[Network Configuration Sources](https://cloudinit.readthedocs.io/en/latest/topics/network-config.html#network-configuration-sources) の NoCloud の [Networking Config Version 1](https://cloudinit.readthedocs.io/en/latest/topics/network-config-format-v1.html#network-config-v1) の例が [cloud-init "nocloud" networking setup](https://gist.github.com/Informatic/0b6b24374b54d09c77b9d25595cdbd47) にあったので、これを参考に [Networking Config Version 2](https://cloudinit.readthedocs.io/en/latest/topics/network-config-format-v2.html#network-config-v2) の方式での設定内容を考えて `network-config` ファイルは以下のようにしました
（トップレベルに `network:` がなくその下のキーをトップレベルに書くことに注意してください）。

```yaml
version: 2
ethernets:
    eth0:
        dhcp4: false
        addresses:
            - 192.168.254.2/24
        gateway4: 192.168.254.1
        nameservers:
            addresses: [8.8.8.8, 8.8.4.4]
```

`vEthernet (WinNAT)` のアドレスが `192.168.254.1/24` で VM のアドレスが `192.168.254.2/24` という想定です。

Hyper-V で cloud-init での初期化を行うには上記の `user-data`, `network-config` と空の `meta-data` ファイルを含む ISO イメージを作って VM 起動時に読ませる必要があります。

[第561回　ローカルインストール時もcloud-initを活用する：Ubuntu Weekly Recipe｜gihyo.jp  技術評論社](https://gihyo.jp/admin/serial/01/ubuntu-recipe/0561?page=2) で紹介されている `cloud-localds` コマンドを使えばこの ISO イメージ作成を行うことができます。
Ubuntu だと cloud-image-utils パッケージに含まれています。

ただ、今後 Hyper-V での VM の利用が主体になると Windows Subsystem for Linux は入れずに使いたい場合もあると考えました。
そこで `user-data` ファイルに `password` と `ssh_authorized_keys` の値を追加するのと、 cloud-init の ISO イメージを作るコマンドラインツール [hnakamur/cloudinittool](https://github.com/hnakamur/cloudinittool) を Go で書きました。

## Windows での Hyper-V での作業手順

### cloudinittool のダウンロードとインストール

[Releases  hnakamur/cloudinittool](https://github.com/hnakamur/cloudinittool/releases) から Windows 用の zip ファイルをダウンロード、展開し `cloudinittool.exe` を PATH が通った場所に置きます。

PowerShell で展開する場合は [PowerShellでZIPファイルを解凍する](/blog/2020/02/22/extract-zip-on-powershell/) の記事を参照してください。

### OpenSSH クライアントのインストール

`ssh-keygen` を使うため [Windows 10 に OpenSSH クライアントをインストール](/blog/2020/02/22/install-openssh-client-to-windows10/) の手順で OpenSSH クライアントをインストールします。

### qemu-img for Windows のインストール

[qemu-img for Windows - Cloudbase Solutions](https://cloudbase.it/qemu-img-windows/) に Windows 用の qemu-img がありますので、ダウンロードして `C:\qemu-img\` に展開します。

もし違う場所に置く場合は
[example-scripts/hyper-v/launch.ps1#L24](https://github.com/hnakamur/cloudinittool/blob/v0.1.0/example-scripts/hyper-v/launch.ps1#L24)
の `C:\qemu-img\qemu-img` を合わせて変更してください。


### PowerShell のキーバインドを Emacs ライクにする

本題とは関係ないですがお好みで [PowershellでEmacsライクなキーバインドを使う  hnakamur's blog](/blog/2020/02/22/powershell-emacs-like-keybindings/) の設定をしておきます。

### vEthernet (WinNAT) の作成

PowerShell を管理者権限で開き、 cloudinittool の zip ファイルを展開した中の `example-scripts/hyper-v` フォルダに移動します。

[example-scripts/hyper-v/create-winnat.ps1](https://github.com/hnakamur/cloudinittool/blob/v0.1.0/example-scripts/hyper-v/create-winnat.ps1) の内容を確認し、お好みでアドレスを変更します。

以下のように実行して `vEthernet (WinNAT)` を作成します。

```
.\create-winnat.ps1
```

作成した結果は以下のコマンドレットで確認できます。

* [Get-VMSwitch](https://docs.microsoft.com/ja-jp/powershell/module/hyper-v/Get-VMSwitch?view=win10-ps)
* [Get-NetIPAddress](https://docs.microsoft.com/ja-jp/powershell/module/nettcpip/Get-NetIPAddress?view=win10-ps)
* [Get-NetNat](https://docs.microsoft.com/ja-jp/powershell/module/netnat/Get-NetNat?view=win10-ps)

### VM の作成と起動

[example-scripts/hyper-v/launch.ps1](https://github.com/hnakamur/cloudinittool/blob/v0.1.0/example-scripts/hyper-v/launch.ps1) の内容を確認し、適宜変更します。

管理者権限の PowerShell で cloudinittool の zip ファイルを展開した中の `example-scripts/hyper-v` フォルダにて以下のコマンドを実行します。

```
.\launch.ps1
```

ssh 鍵ペアを生成する際のパスフレーズの入力を求められるので入力します。
私は後で VM 内に LXD コンテナを作ってそこでもこの鍵ペアを流用するつもりでコンテナでいちいち ssh-agent 動かすのは面倒なのでパスフレーズは空にしました。

鍵ペアは `${Env:USERPROFILE}\.ssh\vm.id_ed25519` と `${Env:USERPROFILE}\.ssh\vm.id_ed25519.pub` に作るようになっています。

その後 VM の Ubuntu のデフォルトユーザ ubuntu のパスワードを決定するため `Password: ` と `Confirm password: ` というプロンプトが出ますので入力します。

すると `user-data.in.yml` にパスワードと公開鍵を追加した `user-data` を生成し、
その `user-data` と `network-config` を含む cloud-init の ISO イメージを作って Hyper-V で VM を作成、起動します。

### VM へ ssh で接続

Hyper-V の VM のウィンドウが開いて起動が進んでログインプロンプトが出たら、 ユーザ権限の PowerShell のプロンプトで以下のように実行すれば ssh で接続できます。

```
ssh -i ~/.ssh/vm.id_ed25519 ubuntu@192.168.254.2
```

## macOS での multipass での作業手順

### multipass のダウンロードとインストール

[canonical/multipass](https://github.com/canonical/multipass) の [Releases](https://github.com/canonical/multipass/releases) から macOS 用のインストーラをダウンロードしてインストールします。

2020-02-22 時点では 1.0.0 の Assets を開いたところにある `multipass-1.0.0+mac-Darwin.pkg` が最新でした。

### cloudinittool のダウンロードとインストール

[Releases  hnakamur/cloudinittool](https://github.com/hnakamur/cloudinittool/releases) から macOS 用の tar.gz ファイルをダウンロード、展開し `cloudinittool` を PATH が通った場所に置きます。

### VM の作成と起動

cloudinittool の tar.gz ファイルを展開した中の `example-scripts/multipass` フォルダにて以下のコマンドを実行します。

```
./launch.sh
```

ssh 鍵ペアを生成する際のパスフレーズの入力を求められるので入力します。
私は後で VM 内に LXD コンテナを作ってそこでもこの鍵ペアを流用するつもりでコンテナでいちいち ssh-agent 動かすのは面倒なのでパスフレーズは空にしました。

鍵ペアは `~/.ssh/vm.id_ed25519` と `~/.ssh/vm.id_ed25519.pub` に作るようになっています。

その後 VM の Ubuntu のデフォルトユーザ ubuntu のパスワードを決定するため `Password: ` と `Confirm password: ` というプロンプトが出ますので入力します。

すると `user-data.in.yml` にパスワードと公開鍵を追加した `user-data` を生成し、 `multipass launch` に `--cloud-init` オプションでこの `user-data` を指定して VM を作成、起動します。

### VM へ ssh で接続

`multipass launch` が完了したら `multipass list` で VM を一覧表示し、 `primary` インスタンスの IP アドレスを確認します。
その IP アドレスを指定して以下のように実行すれば ssh で接続できます。

```
ssh -i ~/.ssh/vm.id_ed25519 ubuntu@primaryインスタンスのIPアドレス
```

もちろん `multipass shell` コマンドも使えます。
