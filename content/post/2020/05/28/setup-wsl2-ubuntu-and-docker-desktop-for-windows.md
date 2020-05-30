---
title: "WSL2のUbuntuとDocker Desktop for Windowsを試してみた"
date: 2020-05-28T19:46:07+09:00
lastmod: 2020-05-31T02:58:00+09:00
---

## Docker Desktop for Windows を使わない方法もあります （2020-05-31 追記）

[WSL2のUbuntuでsystemdとsnapdとLXDを動かしてみた · hnakamur's blog](/blog/2020/05/30/run-systemd-snapd-and-lxd-on-wsl2-ubuntu/) の手順で systemd を動かして、あとは WSL2 の Ubuntu 内で docker を動かすという方法もあります。

上記の記事の「Docker Desktop for Windows をアンインストールして docker を動かしてみた」の項に手順を書いています。

私は Docker Desktop for Windows を入れていたのでアンインストールの手順が必要でしたが、最初から入れない場合はその手順を飛ばせば大丈夫だと思います。

## はじめに

[「Windows 10 May 2020 Update」が一般公開 ～年2回の大規模アップデート - 窓の杜](https://forest.watch.impress.co.jp/docs/news/1255259.html) ということで [WSL 2 対応 Docker Desktop for Windowsを使うための手順 - Qiita](https://qiita.com/zembutsu/items/22a5cae1d13df0d04e7b) の記事を参考に WSL2 の Ubuntu と Docker Desktop for Windows を試してみました。いつもわかりやすい記事をありがとうございます！

自分用に手順と調査メモを書いておきます。

## WSL2 の構築手順メモ

### Windows 10 May 2020 Update の適用

更新対象が 2 台以上だったのでダウンロードを1回で済ませたいと思い、 [Windows 10 のダウンロード](https://www.microsoft.com/ja-jp/software-download/windows10) でメディア作成ツールをダウンロードし、そこから Windows の ISO イメージをダウンロードしました。

DVD-R に焼いたりしなくてもエクスプローラーで ISO イメージを選んでポップアップメニューからマウントし setup.exe を実行すると更新することが出来ました。

更新の途中は何度か再起動するので、これがうまく行ったということは再起動の前に必要なファイルをマウントした ISO イメージから内蔵 SSD にコピーしているのだと推測します。

### Windows Subsystem for Linux 2 (WSL2) のインストール

[Windows Subsystem for Linux (WSL) を Windows 10 にインストールする | Microsoft Docs](https://docs.microsoft.com/ja-jp/windows/wsl/install-win10) の手順に沿ってインストールします。

#### dsim.exe で Windows の特定の機能が有効か確認する手順

[How to check if Windows Feature is installed and enabled with DISM.exe? - Super User](https://superuser.com/questions/700991/how-to-check-if-windows-feature-is-installed-and-enabled-with-dism-exe) で知りました。
公式ドキュメントは [To find available Windows features in an image](https://docs.microsoft.com/en-us/windows-hardware/manufacture/desktop/enable-or-disable-windows-features-using-dism#to-find-available-windows-features-in-an-image) です。

機能一覧表示。

```console
dism /online /get-features
```

実行例の抜粋です。

```txt
PS C:\WINDOWS\system32> dism /online /get-features
展開イメージのサービスと管理ツール
バージョン: 10.0.19041.1
イメージのバージョン: 10.0.19041.264
パッケージの機能の一覧 : Microsoft-Windows-Foundation-Package~31bf3856ad364e35~amd64~~10.0.19041.1
…(略)…
機能名 : Microsoft-Windows-Subsystem-Linux
状態 : 有効
機能名 : HypervisorPlatform
状態 : 無効
機能名 : VirtualMachinePlatform
状態 : 有効
…(略)…
```

単一の機能の状態・情報表示（下記の XXXXX を適宜置き換えて実行）。

```console
dism /online /get-featureinfo /featurename:XXXXX
```

実行例。

```txt
PS C:\WINDOWS\system32> dism /online /get-featureinfo /featurename:Microsoft-Windows-Subsystem-Linux
展開イメージのサービスと管理ツール
バージョン: 10.0.19041.1
イメージのバージョン: 10.0.19041.264
機能情報:
機能名 : Microsoft-Windows-Subsystem-Linux
表示名 : Linux 用 Windows サブシステム
説明 : ネイティブなユーザー モードの Linux シェルおよびツールを Windows で実行するためのサービスと環境を提供します。
再起動が必要 : Possible
状態 : 有効
カスタム プロパティ:
ServerComponent\Description : ネイティブなユーザー モードの Linux シェルおよびツールを Windows で実行するためのサービス と環境を提供します。
ServerComponent\DisplayName : Linux 用 Windows サブシステム
ServerComponent\Id : 1033
ServerComponent\Type : Feature
ServerComponent\UniqueName : Microsoft-Windows-Subsystem-Linux
ServerComponent\Deploys\Update\Name : Microsoft-Windows-Subsystem-Linux
操作は正常に完了しました。
```

```txt
PS C:\WINDOWS\system32> dism /online /get-featureinfo /featurename:VirtualMachinePlatform
展開イメージのサービスと管理ツール
バージョン: 10.0.19041.1
イメージのバージョン: 10.0.19041.264
機能情報:
機能名 : VirtualMachinePlatform
表示名 : 仮想マシン プラットフォーム
説明 : 仮想マシンのプラットフォーム サポートを有効にします
再起動が必要 : Possible
状態 : 有効
カスタム プロパティ:
(カスタム プロパティが見つかりません)
操作は正常に完了しました。
```

#### Windows Subsystem for Linux のインストール

管理者権限で PowerShell を開いて以下のコマンドを実行します。

```console
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

実行例を示します。実行前に Microsoft-Windows-Subsystem-Linux の機能が有効でも下記のようにバージョンが上がることがあるので、上記のコマンドは省略せず実行が必要なようです。

前項の状態確認手順の出力でも「バージョン」と「イメージのバージョン」が出ているので違う場合は実行するようにすれば良さそうです。

```txt
PS C:\WINDOWS\system32> dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
展開イメージのサービスと管理ツール
バージョン: 10.0.19041.1
イメージのバージョン: 10.0.19041.264
機能を有効にしています
[==========================100.0%==========================]
操作は正常に完了しました
```

実行後 Windows を再起動するよう書いてありますが、私は次項も実行してから再起動しました。

#### "仮想マシン プラットフォーム" のオプション コンポーネントを有効にする

管理者権限で PowerShell を開いて以下のコマンドを実行します。

```console
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

実行例です。

```txt
PS C:\WINDOWS\system32> dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
展開イメージのサービスと管理ツール
バージョン: 10.0.19041.1
イメージのバージョン: 10.0.19041.264
機能を有効にしています
[==========================100.0%==========================]
操作は正常に完了しました。
```

実行後 Windows を再起動します。

#### WSL 2 を既定のバージョンとして設定する

PowerShell を起動して以下のコマンドを実行します。

```console
wsl --set-default-version 2
```

`wsl -h` を見る限りは設定された既定のバージョンを確認するオプションは `wsl.exe` には無いようです。

私の環境では実行すると以下のようなメッセージが出力されました。

```txt
PS C:\Users\hnakamur> wsl --set-default-version 2
WSL 2 を実行するには、カーネル コンポーネントの更新が必要です。詳細については https://aka.ms/wsl2kernel を参照してください
```

このように表示されたときは上記のリンクから [WSL 2 Linux カーネルの更新 | Microsoft Docs](https://docs.microsoft.com/ja-jp/windows/wsl/wsl2-kernel) を開き、Linux カーネル更新プログラム パッケージ（ファイル名： `wsl_update_x64.msi` ）をダウンロード、インストールします。

その後以下のコマンドをやり直す必要がありました。

```console
wsl --set-default-version 2
```

今度は以下のように表示されました。

```
PS C:\Users\hnakamur> wsl --set-default-version 2
WSL 2 との主な違いについては、https://aka.ms/wsl2 を参照してください
```

#### Linux ディストリビューションのインストール

[Microsoft Store](https://aka.ms/wslstore) を開いてお好みの Linux ディストリビューションをインストールします。

私は Ubuntu を WSL1 でインストールしていたので、別の環境として Ubuntu 20.04 LTS をインストールしてみました（Ubuntu のほうは最新の LTS に追随するものらしいです）。

WSL2 のウィンドウが開いて以下のように表示されたので、ユーザー名とパスワードを入力すればセットアップが完了し、Ubuntu のプロンプトが表示されます。

```
Installing, this may take a few minutes...
Please create a default UNIX user account. The username does not need to match your Windows username.
For more information visit: https://aka.ms/wslusers
Enter new UNIX username: hnakamur
New password:
Retype new password:
passwd: password updated successfully
Installation successful!
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

Welcome to Ubuntu 20.04 LTS (GNU/Linux 4.19.104-microsoft-standard x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System information as of Thu May 28 22:00:20 JST 2020

  System load:  0.19               Processes:             8
  Usage of /:   0.4% of 250.98GB   Users logged in:       0
  Memory usage: 0%                 IPv4 address for eth0: 172.26.134.224
  Swap usage:   0%

0 updates can be installed immediately.
0 of these updates are security updates.


The list of available updates is more than a week old.
To check for new updates run: sudo apt update


This message is shown once once a day. To disable it please create the
/home/hnakamur/.hushlogin file.
```

（参考） WSL1 の場合は以下のような感じでした（IPv6のグローバルアドレスは伏せています）。

```
Installing, this may take a few minutes...
Please create a default UNIX user account. The username does not need to match your Windows username.
For more information visit: https://aka.ms/wslusers
Enter new UNIX username: hnakamur
New password:
Retype new password:
passwd: password updated successfully
Installation successful!
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

Welcome to Ubuntu 20.04 LTS (GNU/Linux 4.4.0-19041-Microsoft x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System information as of Thu May 28 21:52:05 JST 2020

  System load:           0.52
  Usage of /home:        unknown
  Memory usage:          57%
  Swap usage:            0%
  Processes:             7
  Users logged in:       0
  IPv4 address for eth0: 192.168.2.208
  IPv6 address for eth0: xxxx:xxx:xxx:xxxx:yyyy:yyyy:yyyy:yyyy
  IPv6 address for eth0: xxxx:xxx:xxx:xxxx:zzzz:zzzz:zzzz:zzzz
  IPv4 address for eth1: 172.25.32.1
  IPv4 address for eth3: 192.168.254.1

0 updates can be installed immediately.
0 of these updates are security updates.


The list of available updates is more than a week old.
To check for new updates run: sudo apt update


This message is shown once once a day. To disable it please create the
/home/hnakamur/.hushlogin file.
```

PowerShell を開いて `wsl -l -v` を実行すると、 Ubuntu-20.04 が WSL2 で作られたことが確認できました。

```
PS C:\Users\hnakamur> wsl -l -v
  NAME            STATE           VERSION
* Ubuntu          Running         1
  Ubuntu-20.04    Running         2
```

## WSL2 の VM の調査メモ

### カーネルバージョン

```console
hnakamur@sunshine7:~$ uname -r
4.19.104-microsoft-standard
hnakamur@sunshine7:~$ uname -a
Linux sunshine7 4.19.104-microsoft-standard #1 SMP Wed Feb 19 06:37:35 UTC 2020 x86_64 x86_64 x86_64 GNU/Linux
```

WSL2 の Linux カーネルのレポジトリは [microsoft/WSL2-Linux-Kernel: The source for the Linux kernel used in Windows Subsystem for Linux 2 (WSL2)](https://github.com/microsoft/WSL2-Linux-Kernel) にあります。

### メモリとスワップ

RAM 16GB のマシンですが、 WSL2 の Ubuntu には 12GB のメモリが割り当てられ、 4GB のスワップファイルが作られていました。

```console
hnakamur@sunshine7:~$ free -h
              total        used        free      shared  buff/cache   available
Mem:           12Gi        58Mi        12Gi       0.0Ki        62Mi        12Gi
Swap:         4.0Gi          0B       4.0Gi
hnakamur@sunshine7:~$ swapon
NAME       TYPE SIZE USED PRIO
/swap/file file   4G   0B   -2
```

同じく RAM 16GB の別のマシンで WSL1 で作成後 WSL2 に変換した Ubuntu ではメモリ 10GB でスワップファイル 3GB になっていました。

### プロセス一覧

PID 1 は `/init` で `systemd` は動いていません（ちなみに物理サーバーの Ubuntu では PID 1 は `/sbin/init` でした）。

```console
hnakamur@sunshine7:~$ ps auxwwf
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0    892   552 ?        Sl   22:00   0:00 /init
root        49  0.0  0.0    892    84 ?        Ss   22:00   0:00 /init
root        50  0.0  0.0    892    84 ?        S    22:00   0:00  \_ /init
hnakamur    51  0.0  0.0  10036  5056 pts/0    Ss   22:00   0:00      \_ -bash
hnakamur   132  0.0  0.0  10604  3272 pts/0    R+   22:16   0:00          \_ ps auxwwf
```

### ネットワークインターフェースとIPアドレス

`lo` と `eth0` の他に `bond0`, `dummy0`, `sit0@NONE` というインターフェースもありますが、何に使われているか私は分かっていません。

`eth0` の IPv4 アドレスのネットワークは `/20` になってました。


```console
hnakamur@sunshine7:~$ ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: bond0: <BROADCAST,MULTICAST,MASTER> mtu 1500 qdisc noop state DOWN group default qlen 1000
    link/ether 3a:7c:e0:d3:44:a7 brd ff:ff:ff:ff:ff:ff
3: dummy0: <BROADCAST,NOARP> mtu 1500 qdisc noop state DOWN group default qlen 1000
    link/ether 4a:1b:ad:a2:76:eb brd ff:ff:ff:ff:ff:ff
4: sit0@NONE: <NOARP> mtu 1480 qdisc noop state DOWN group default qlen 1000
    link/sit 0.0.0.0 brd 0.0.0.0
5: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 00:15:5d:de:27:a0 brd ff:ff:ff:ff:ff:ff
    inet 172.26.134.224/20 brd 172.26.143.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::215:5dff:fede:27a0/64 scope link
       valid_lft forever preferred_lft forever
```

外部のドメインを指定して ping も通りました。

Windows には IPv6 のグローバルアドレスがついているのですが、 WSL2 の仮想マシンには上記の通りついていません。

[cannot reach ipv6 only address · Issue #4518 · microsoft/WSL](https://github.com/microsoft/WSL/issues/4518) の [コメント](https://github.com/microsoft/WSL/issues/4518#issuecomment-534267533) によると現状 WSL2 は IPv6 は使えないそうです。

PowerShell で `ipconfig /all` で確認すると WSL 用に以下のような仮想のネットワークインタフェースが作成されていました。

```
イーサネット アダプター vEthernet (WSL):

   接続固有の DNS サフィックス . . . . .:
   説明. . . . . . . . . . . . . . . . .: Hyper-V Virtual Ethernet Adapter #3
   物理アドレス. . . . . . . . . . . . .: 00-15-5D-3E-F8-EE
   DHCP 有効 . . . . . . . . . . . . . .: いいえ
   自動構成有効. . . . . . . . . . . . .: はい
   リンクローカル IPv6 アドレス. . . . .: fe80::fde6:af3f:d161:518d%71(優先)
   IPv4 アドレス . . . . . . . . . . . .: 172.26.128.1(優先)
   サブネット マスク . . . . . . . . . .: 255.255.240.0
   デフォルト ゲートウェイ . . . . . . .:
   DHCPv6 IAID . . . . . . . . . . . . .: 1191187805
   DHCPv6 クライアント DUID. . . . . . .: 00-01-00-01-20-40-55-86-C8-5B-76-D1-3D-7E
   DNS サーバー. . . . . . . . . . . . .: fec0:0:0:ffff::1%1
                                          fec0:0:0:ffff::2%1
                                          fec0:0:0:ffff::3%1
   NetBIOS over TCP/IP . . . . . . . . .: 有効
```

### ディスク

```console
hnakamur@sunshine7:~$ df -h -T
Filesystem     Type      Size  Used Avail Use% Mounted on
/dev/sdb       ext4      251G  1.1G  238G   1% /
tmpfs          tmpfs     6.2G     0  6.2G   0% /mnt/wsl
tools          9p        238G  181G   57G  77% /init
none           devtmpfs  6.2G     0  6.2G   0% /dev
none           tmpfs     6.2G  8.0K  6.2G   1% /run
none           tmpfs     6.2G     0  6.2G   0% /run/lock
none           tmpfs     6.2G     0  6.2G   0% /run/shm
none           tmpfs     6.2G     0  6.2G   0% /run/user
tmpfs          tmpfs     6.2G     0  6.2G   0% /sys/fs/cgroup
C:\            9p        238G  181G   57G  77% /mnt/c
```

WSL2 の Ubuntu のプロンプトで `explorer.exe .` と実行すると、 `\\wsl$\Ubuntu-20.04\home\hnakamur` のパスでエクスプローラーが開きます。

### `/proc/sys/fs/binfmt_misc/WSLInterop`

[Linux との Windows の相互運用性 | Microsoft Docs](https://docs.microsoft.com/ja-jp/windows/wsl/interop)
の [相互運用性の無効化](https://docs.microsoft.com/ja-jp/windows/wsl/interop#disable-interoperability) の項に `/proc/sys/fs/binfmt_misc/WSLInterop` についての情報がありました。

[Scripting With WSL Interoperability: Tips & Tricks | Listener](https://patrickwu.space/wslconf/) も参考になりそうです。

初期状態での `/proc/sys/fs/binfmt_misc/WSLInterop` の内容を確認すると以下のようになっていました。

```console
hnakamur@sunshine7:~$ ls -l /proc/sys/fs/binfmt_misc/WSLInterop
-rw-r--r-- 1 root root 0 May 28 21:59 /proc/sys/fs/binfmt_misc/WSLInterop
hnakamur@sunshine7:~$ cat /proc/sys/fs/binfmt_misc/WSLInterop
enabled
interpreter /tools/init
flags: F
offset 0
magic 4d5a
```

## Docker Desktop for Windows のインストール手順メモ

[Docker Desktop for Mac and Windows | Docker](https://www.docker.com/products/docker-desktop) から Windows の Stable のインストーラーをダウンロードして実行します。

インストーラーの表示によるとバージョンは Docker Desktop 2.3.0.3 (45519) です。

インストーラーの Configuration の画面で以下の2つのチェックボックスが表示されます。

* Enable WSL 2 Windows Features
* Add shortcut to desktop

初期状態で両方チェックオンになっていますので、 1 つめはオンのまま OK ボタンを押してインストールします。

インストールが完了したら Windows のスタートメニューから Docker Desktop を起動します。

起動が完了したら "Get started with Docker in a few easy steps!" という画面が表示されるので Start ボタンを押してチュートリアルを見るか、下の "Skip tutorial" リンクを押してスキップします。

[Docker Desktop WSL 2 backend | Docker Documentation](https://docs.docker.com/docker-for-windows/wsl/#prerequisites) の Install の 7. の手順を実行します。

1. Windows のタスクトレイで Docker のポップアップメニューの Settings を選んで設定画面を開きます。
2. Settings 画面が開いたら、左の Resources を開いて WSL INTEGRATION を選び、右で "Enable integration with my default WSL distro" のチェックボックスとその下の "Enable integration with additional distros:" の下のトグルボタンを適宜調整し、右下の [Apply & Restart] ボタンを押します。私の環境ではデフォルトは WSL1 の Ubuntu なので additional distros のほうの Ubuntu-20.04 を有効にしました。
3. PowerShell を開き `wsl -t ubuntu-20.04` （ディストリビューションは適宜調整）を実行して、 WSL2 の VM を再起動します。

これで WSL2 の VM のプロンプトを開いて `docker ps` を実行すると正常に動きます。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ docker ps
CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
```

`docker run hello-world` も正常に動きました。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ docker run hello-world
Unable to find image 'hello-world:latest' locally
latest: Pulling from library/hello-world
0e03bdcc26d7: Pull complete
Digest: sha256:6a65f928fb91fcfbc963f7aa6d57c8eeb426ad9a20c7ee045538ef34847f44f1
Status: Downloaded newer image for hello-world:latest

Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
 https://hub.docker.com/

For more examples and ideas, visit:
 https://docs.docker.com/get-started/
```

## Docker Desktop for Windows の調査メモ

この状態で `df -h -T` を実行してみると Docker Desktop for Windows 用のマウントが追加されていました。


```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ df -h -T
Filesystem     Type      Size  Used Avail Use% Mounted on
/dev/sdb       ext4      251G  1.1G  238G   1% /
tmpfs          tmpfs     6.2G     0  6.2G   0% /mnt/wsl
/dev/sdd       ext4      251G  949M  238G   1% /mnt/wsl/docker-desktop-data/isocache
none           tmpfs     6.2G   12K  6.2G   1% /mnt/wsl/docker-desktop/shared-sockets/host-services
/dev/sdc       ext4      251G  117M  239G   1% /mnt/wsl/docker-desktop/docker-desktop-proxy
/dev/loop0     iso9660   244M  244M     0 100% /mnt/wsl/docker-desktop/cli-tools
tools          9p        238G  185G   53G  78% /init
none           devtmpfs  6.2G     0  6.2G   0% /dev
none           tmpfs     6.2G  8.0K  6.2G   1% /run
none           tmpfs     6.2G     0  6.2G   0% /run/lock
none           tmpfs     6.2G     0  6.2G   0% /run/shm
none           tmpfs     6.2G     0  6.2G   0% /run/user
tmpfs          tmpfs     6.2G     0  6.2G   0% /sys/fs/cgroup
C:\            9p        238G  185G   53G  78% /mnt/c
```

`docker` と `docker-compose` はマウント先のファイルへのシンボリックリンクになっていました。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ which docker
/usr/bin/docker
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ which docker-compose
/usr/bin/docker-compose
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ ls -l /usr/bin/docker*
lrwxrwxrwx 1 root root 48 May 28 23:08 /usr/bin/docker -> /mnt/wsl/docker-desktop/cli-tools/usr/bin/docker
lrwxrwxrwx 1 root root 56 May 28 23:08 /usr/bin/docker-compose -> /mnt/wsl/docker-desktop/cli-tools/usr/bin/docker-compose
```

Ubuntu の docker コンテナーも試してみました。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ docker run -it ubuntu bash
root@a0f4ec92b72f:/# apt update && apt -y install iproute2 iputils-ping
…(略)…
root@a0f4ec92b72f:/# ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: sit0@NONE: <NOARP> mtu 1480 qdisc noop state DOWN group default qlen 1000
    link/sit 0.0.0.0 brd 0.0.0.0
9: eth0@if10: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether 02:42:ac:11:00:02 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 172.17.0.2/16 brd 172.17.255.255 scope global eth0
       valid_lft forever preferred_lft forever
```

外部のドメインへの ping も通りました。

このとき WSL2 の VM の `ip a` と Windows での `ipconfig /all` は変更無しでした。

`/var/run/` に `docker.sock` というソケットファイルと `docker-desktop-proxy.pid` という PID ファイルがありました。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ ls -l /var/run/docker*
-rw-r--r-- 1 root root   2 May 28 23:08 /var/run/docker-desktop-proxy.pid
srw-rw---- 1 root docker 0 May 28 23:08 /var/run/docker.sock
```

`docker-desktop-proxy.pid` の PID のプロセスは以下のようなコマンドでした。

```console
hnakamur@sunshine7:/mnt/c/Users/hnakamur$ ps ww -p $(cat /var/run/docker-desktop-proxy.pid)
  PID TTY      STAT   TIME COMMAND
   47 pts/1    Ssl+   0:00 /mnt/wsl/docker-desktop/docker-desktop-proxy --distro-name Ubuntu-20.04 --docker-desktop-root /mnt/wsl/docker-desktop
```

## docker-desktop-data と docker-desktop は WSL2 のディストリビューションだった (2020-05-29 追記)

Docker Desktop for Windows のセットアップ後に PowerShell で `wsl -l -v` でディストリビューション一覧を表示してみると以下のようになりました。

```console
PS C:\Users\hnakamur> wsl -l -v
  NAME                   STATE           VERSION
* Ubuntu                 Running         2
  docker-desktop-data    Running         2
  docker-desktop         Running         2
```

上記で `df -h -T` を実行したときに `/mnt/wsl/docker-desktop-data` と `/mnt/wsl/docker-desktop` というのがありましたが、これは WSL2 のディストリビューションとして作られたものがマウントされているようです。

## WSL2 の記事 (2020-05-30 追記)

WSL2 についての詳しい記事を見つけたのでリンクを貼っておきます。

* [ASCII.jp：20H1の完成とともにWindows Subsystem for Linux 2が来る (1/2)](https://ascii.jp/elem/000/004/007/4007561/)
* [ASCII.jp：20H1とともに正式に来るWindows Subsystem for Linux 2の実力を見る (1/2)](https://ascii.jp/elem/000/004/012/4012149/)

1 つめの記事内に他の記事へのリンクも貼ってあってそちらもためになりました。
