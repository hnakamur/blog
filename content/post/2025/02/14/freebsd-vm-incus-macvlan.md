---
title: "ZFSを使っているUbuntuのIncus上でmacvlanを使ってFreeBSDの仮想マシンを動かす"
date: 2025-02-14T15:48:05+09:00
---

## はじめに

[FreeBSD VM under Incus on Debian :: agren.cc](https://agren.cc/p/freebsd-vm-incus/)を読んで試してみたメモです。

[FreeBSD instructions do not work anymore - Incus - Linux Containers Forum](https://discuss.linuxcontainers.org/t/freebsd-instructions-do-not-work-anymore/20138)で紹介されているFreeBSDのインストーラーのISOイメージを使ってインストールする方式と異なり、FreeBSDで提供されているraw diskイメージを使って仮想マシン（以下VM (Virtual Machineの略)とします）を構築します。

この構成ではmacvlanを使うため、ホストのLiuxマシンは物理サーバーである必要があります（参考：[第6回　Linuxカーネルのコンテナ機能［5］ ─ネットワーク | gihyo.jp](https://gihyo.jp/admin/serial/01/linux_containers/0006)）。

## Incusでmacvlanのネットワーク作成

この記事では`macvlan0`というネットワーク名を使うことにします。以下のようにして作成します。

parentにはホストの物理インタフェースを指定する必要があります。`ip a`などで確認して環境に応じたデバイス名を指定してください。

```
incus network create macvlan0 --type=macvlan parent=enp6s0
```

実行後`incus network list`を実行して、一覧に`macvlan0`が含まれることを確認します。

## FreeBSD 14.2のraw diskイメージのダウンロードと展開

バージョン14.2の場合は以下のようにします。

```
curl -LO https://download.freebsd.org/ftp/releases/VM-IMAGES/14.2-RELEASE/amd64/Latest/FreeBSD-14.2-RELEASE-amd64-ufs.raw.xz
xz -cd FreeBSD-14.2-RELEASE-amd64-ufs.raw.xz > FreeBSD-14.2-RELEASE-amd64-ufs.raw
```

最新のバージョンは https://download.freebsd.org/ftp/releases/VM-IMAGES/ で確認して、上記のコマンドを適宜調整してください。

## FreeBSDのVMを作成して設定する

試行錯誤の記録を横道として残しておきますが、正しい手順だけを知りたい場合は読み飛ばして良いです。

{{< details summary="(失敗) incus initで設定ファイルを食わせるのはうまく行かず" >}}

`incus init`で`--empty`を使いつつ設定ファイルを食わせるとstoarge poolが見つからなかった。
```
cat <<EOF > macvlan-vm-config.yaml
config:
  limits.cpu: '2'
  limits.memory: 2GB
  security.secureboot: 'false'
devices:
  root:
    path: /
    pool: default
    size: 40GB
    type: disk
  vtnet0:
    name: vtnet0
    network: macvlan0
    type: nic
EOF
```

```
incus init freebsd14 --empty --vm < macvlan-vm-config.yaml
```

```
Error: Failed creating instance record: Failed initializing instance: Failed loading storage pool: Storage pool not found
```
{{< /details >}}



{{< details summary="(失敗) incus editで設定ファイルを食わせるのもうまく行かず" >}}

config.volatile.uuidなどが消えてしまって起動できなかった。

なお、macvlan-vm-config.yaml は一つ前の手順で作成したものを使用。
```
$ incus init freebsd14 --empty --vm
Creating freebsd14
$ incus config show freebsd14
architecture: x86_64
config:
  volatile.apply_template: create
  volatile.cloud-init.instance-id: e863022a-9026-4a12-8d64-370162b5036b
  volatile.eth0.hwaddr: 00:16:3e:b6:e2:77
  volatile.uuid: 3b208d9e-c856-4102-a0e0-4d81a8b63e24
  volatile.uuid.generation: 3b208d9e-c856-4102-a0e0-4d81a8b63e24
devices: {}
ephemeral: false
profiles:
- default
stateful: false
description: ""
$ incus config edit freebsd14 < macvlan-vm-config.yaml 
$ incus config show freebsd14
architecture: x86_64
config:
  limits.cpu: "2"
  limits.memory: 2GB
  security.secureboot: "false"
  volatile.cloud-init.instance-id: 6d4125f1-a71d-44f4-b635-32ce865f40da
  volatile.vtnet0.hwaddr: 00:16:3e:e6:31:9c
devices:
  root:
    path: /
    pool: default
    size: 40GB
    type: disk
  vtnet0:
    name: vtnet0
    network: macvlan0
    type: nic
ephemeral: false
profiles: []
stateful: false
description: ""
$ incus start freebsd14
Error: Failed to parse instance UUID from volatile.uuid: invalid UUID length: 0
Try `incus info --show-log freebsd14` for more info
```
{{< /details >}}


設定オプションを指定しつつ、VMのインスタンスを初期化。ここではfreebsd14というインスタンス名にしています。
```
incus init freebsd14 --empty --vm \
  -c limits.cpu=2 -c limits.memory=2GB -c security.secureboot=false
```

{{< details summary="上記で初期化したVMの設定確認" >}}

```
$ incus config show freebsd14 -e
architecture: x86_64
config:
  limits.cpu: "2"
  limits.memory: 2GB
  security.secureboot: "false"
  volatile.apply_template: create
  volatile.cloud-init.instance-id: c5bda933-f917-4f69-9d86-c458765cac2e
  volatile.eth0.hwaddr: 00:16:3e:68:0e:8b
  volatile.uuid: 0cd6d317-ed63-46e2-b852-b9fd1ac9a17e
  volatile.uuid.generation: 0cd6d317-ed63-46e2-b852-b9fd1ac9a17e
devices:
  eth0:
    name: eth0
    network: incusbr0
    type: nic
  root:
    path: /
    pool: default
    type: disk
ephemeral: false
profiles:
- default
stateful: false
description: ""
```

補足：`incus config show`の`-e (--expaneded)`はプロファイル側の設定も含めて表示するオプション。
`-e`無しだと`default`プロファイルに含まれる`eth0`と`root`デバイスは表示されない。
```
$ incus config show freebsd14
architecture: x86_64
config:
  limits.cpu: "2"
  limits.memory: 2GB
  security.secureboot: "false"
  volatile.apply_template: create
  volatile.cloud-init.instance-id: c5bda933-f917-4f69-9d86-c458765cac2e
  volatile.eth0.hwaddr: 00:16:3e:68:0e:8b
  volatile.uuid: 0cd6d317-ed63-46e2-b852-b9fd1ac9a17e
  volatile.uuid.generation: 0cd6d317-ed63-46e2-b852-b9fd1ac9a17e
devices: {}
ephemeral: false
profiles:
- default
stateful: false
description: ""
```
{{< /details >}}

デバイス追加とdefaultプロファイルを解除。

```
incus config device add freebsd14 root disk pool=default path=/ size=20GB
incus config device add freebsd14 vtnet0 nic name=vtnet0 network=macvlan0
incus profile remove freebsd14 default
```

{{< details summary="上記で変更後のVMの設定確認" >}}
```
$ incus config show freebsd14 -e
architecture: x86_64
config:
  limits.cpu: "2"
  limits.memory: 2GB
  security.secureboot: "false"
  volatile.apply_template: create
  volatile.cloud-init.instance-id: f7e8c3e2-cf6e-422b-b56b-ef9452730776
  volatile.uuid: 0cd6d317-ed63-46e2-b852-b9fd1ac9a17e
  volatile.uuid.generation: 0cd6d317-ed63-46e2-b852-b9fd1ac9a17e
  volatile.vtnet0.hwaddr: 00:16:3e:54:bd:a2
devices:
  root:
    path: /
    pool: default
    size: 40GB
    type: disk
  vtnet0:
    name: vtnet0
    network: macvlan0
    type: nic
ephemeral: false
profiles: []
stateful: false
description: ""
```
{{< /details >}}

一旦空のディスクのままVMを起動。

```
incus start freebsd14
```

{{< details summary="作成されたVMのブロックデバイスのディスクのデバイスを確認。この手順はZFSに依存しています" >}}

```
$ ls -alh /dev/zvol/rpool/incus/virtual-machines/freebsd14.block
lrwxrwxrwx 1 root root 15 Feb 14 16:54 /dev/zvol/rpool/incus/virtual-machines/freebsd14.block -> ../../../../zd0
```

```
$ readlink -f /dev/zvol/rpool/incus/virtual-machines/freebsd14.block
/dev/zd0
```
上記はまっさらなIncusの環境での例ですが、既存のIncus環境で試したときは`/dev/zd80`など違う番号になっていました。

{{< /details >}}

上記で展開したディスクイメージをVMのrootデバイスのディスクにコピー。この手順はZFSに依存しています。

```
sudo dd if=FreeBSD-14.2-RELEASE-amd64-ufs.raw of=$(readlink -f /dev/zvol/rpool/incus/virtual-machines/freebsd14.block) bs=4M status=progress
```

VMを強制停止。

```
incus stop freebsd14 --force
```

## FreeBSDのVMを起動して適宜パッケージをインストール

VMを起動します。
CUIでコンソールに接続した状態で起動します（コンソールから抜けるには`Ctrl-a q`を押します）。

```
incus start freebsd14 --console
```

`login:`プロンプトが出たら`root`ユーザーでパスワード無しで入れます。

`ifconfig`を実行するとvtnet0にDHCPで付与されたアドレスがついていて、pingで外部のマシンにも通信できました。
ただし、macvlanの制限のため、Incusホストには通信できません。

{{< details summary="（横道）コンソールに接続せずに起動しておいて、あとからコンソールに接続もできる" >}}
`--console`なしで`incus start freebsd14` のように起動した場合`incus console freebsd14` でコンソールに接続できます。この手順だとコンソールに接続後しばらく表示が乱れますが、その後正常になりました。
この場合もコンソールから切断するには`Ctrl-a q`を押します。
{{< /details >}}

このあと、今後別のVMを作成するためのイメージを作成する前に、毎回インストールするようなパッケージを入れておきます。

VM上で`pkg update`を実行します。
```
pkg update
```

{{< details summary="（詳細）pkg updateの出力例" >}}

`Do you want to fetch and install it now? [y/N]: `のプロンプトで`y`を入力します。　

```
root@freebsd:~ # pkg update
The package management tool is not yet installed on your system.
Do you want to fetch and install it now? [y/N]: y
Bootstrapping pkg from pkg+https://pkg.FreeBSD.org/FreeBSD:14:amd64/quarterly, please wait...
Verifying signature with trusted certificate pkg.freebsd.org.2013102301... done
Installing pkg-1.21.3...
Extracting pkg-1.21.3: 100%
Updating FreeBSD repository catalogue...
Fetching meta.conf: 100%    178 B   0.2kB/s    00:01    
Fetching data.pkg: 100%    7 MiB   7.5MB/s    00:01    
Processing entries: 100%
FreeBSD repository update completed. 35857 packages processed.
All repositories are up to date.
```
{{< /details >}}


VM上で`pkg install vim`を実行します。
```
pkg install vim
```
{{< details summary="（詳細）pkg install vimの出力例" >}}

`Proceed with this action? [y/N]: `のプロンプトで`y`を入力します。

```
root@freebsd:~ # pkg install vim
Updating FreeBSD repository catalogue...
FreeBSD repository is up to date.
All repositories are up to date.
Updating database digests format: 100%
The following 8 package(s) will be affected (of 0 checked):

New packages to be INSTALLED:
        gettext-runtime: 0.23
        indexinfo: 0.3.1
        libffi: 3.4.6
        mpdecimal: 4.0.0
        python311: 3.11.11
        readline: 8.2.13_2
        vim: 9.1.0984
        xxd: 9.1.0984

Number of packages to be installed: 8

The process will require 246 MiB more space.
37 MiB to be downloaded.

Proceed with this action? [y/N]: y
[1/8] Fetching mpdecimal-4.0.0.pkg: 100%  156 KiB 159.3kB/s    00:01    
[2/8] Fetching gettext-runtime-0.23.pkg: 100%  236 KiB 241.2kB/s    00:01    
[3/8] Fetching vim-9.1.0984.pkg: 100%    9 MiB   9.7MB/s    00:01    
[4/8] Fetching indexinfo-0.3.1.pkg: 100%    6 KiB   5.9kB/s    00:01    
[5/8] Fetching xxd-9.1.0984.pkg: 100%   20 KiB  20.2kB/s    00:01    
[6/8] Fetching libffi-3.4.6.pkg: 100%   45 KiB  46.0kB/s    00:01    
[7/8] Fetching readline-8.2.13_2.pkg: 100%  397 KiB 406.3kB/s    00:01    
[8/8] Fetching python311-3.11.11.pkg: 100%   27 MiB  14.0MB/s    00:02    
Checking integrity... done (0 conflicting)
[1/8] Installing indexinfo-0.3.1...
[1/8] Extracting indexinfo-0.3.1: 100%
[2/8] Installing mpdecimal-4.0.0...
[2/8] Extracting mpdecimal-4.0.0: 100%
[3/8] Installing gettext-runtime-0.23...
[3/8] Extracting gettext-runtime-0.23: 100%
[4/8] Installing libffi-3.4.6...
[4/8] Extracting libffi-3.4.6: 100%
[5/8] Installing readline-8.2.13_2...
[5/8] Extracting readline-8.2.13_2: 100%
[6/8] Installing xxd-9.1.0984...
[6/8] Extracting xxd-9.1.0984: 100%
[7/8] Installing python311-3.11.11...
[7/8] Extracting python311-3.11.11: 100%
[8/8] Installing vim-9.1.0984...
[8/8] Extracting vim-9.1.0984: 100%
=====
Message from python311-3.11.11:

--
Note that some standard Python modules are provided as separate ports
as they require additional dependencies. They are available as:

py311-gdbm       databases/py-gdbm@py311
py311-sqlite3    databases/py-sqlite3@py311
py311-tkinter    x11-toolkits/py-tkinter@py311
```
{{< /details >}}

## FreeBSDのVMを停止してイメージを作成

VMで`poweroff`を実行して停止します。
```
poweroff
```

以下のコマンドで、freebsd14のVMをイメージ化します。

```
incus publish freebsd14
```

結構時間がかかります。完了すると以下のように、イメージのフィンガープリントが表示されます。

```
Instance published with fingerprint: 08d24f086ed48e1263cf91068c8b937159260527f523184ebdc75989983d93a3
```

フィンガープリントの先頭7文字ぐらいを指定して`incus image list`を実行すると、作成したイメージの概要が確認できます。
```
$ incus image list 08d24f08
+-------+--------------+--------+-------------+--------------+-----------------+------------+----------------------+
| ALIAS | FINGERPRINT  | PUBLIC | DESCRIPTION | ARCHITECTURE |      TYPE       |    SIZE    |     UPLOAD DATE      |
+-------+--------------+--------+-------------+--------------+-----------------+------------+----------------------+
|       | 08d24f086ed4 | no     |             | x86_64       | VIRTUAL-MACHINE | 1413.47MiB | 2025/02/14 17:26 JST |
+-------+--------------+--------+-------------+--------------+-----------------+------------+----------------------+
```

今後利用しやすいようにイメージにエイリアスを作成します。
```
incus image alias create freebsd14-image 08d24f086ed4
```

エイリアスを指定してイメージ一覧を表示し、エイリアスが設定されたことを確認します。
```
$ incus image list freebsd14-image
+-----------------+--------------+--------+-------------+--------------+-----------------+------------+----------------------+
|      ALIAS      | FINGERPRINT  | PUBLIC | DESCRIPTION | ARCHITECTURE |      TYPE       |    SIZE    |     UPLOAD DATE      |
+-----------------+--------------+--------+-------------+--------------+-----------------+------------+----------------------+
| freebsd14-image | 08d24f086ed4 | no     |             | x86_64       | VIRTUAL-MACHINE | 1413.47MiB | 2025/02/14 17:26 JST |
+-----------------+--------------+--------+-------------+--------------+-----------------+------------+----------------------+
```

## 作成したイメージを使ってVMを起動

上記で作成したイメージを使ってVMを初期化しても、イメージ作成元のVMに行った設定の変更が含まれないため、追加で設定を変更する必要があります。

{{< details summary="（詳細）作成したイメージを使ってVMを初期化した設定には上記での変更が含まれない" >}}
```
$ incus init freebsd14-image vm1
Creating vm1
$ incus config show vm1 -e
architecture: x86_64
config:
  volatile.apply_template: create
  volatile.base_image: 08d24f086ed48e1263cf91068c8b937159260527f523184ebdc75989983d93a3
  volatile.cloud-init.instance-id: 1c49e1da-97e9-4e18-adef-452e64aaa395
  volatile.eth0.hwaddr: 00:16:3e:11:13:96
  volatile.uuid: 80db0fd5-3804-41e4-9c71-0227dc780767
  volatile.uuid.generation: 80db0fd5-3804-41e4-9c71-0227dc780767
devices:
  eth0:
    name: eth0
    network: incusbr0
    type: nic
  root:
    path: /
    pool: default
    type: disk
ephemeral: false
profiles:
- default
stateful: false
description: ""
$ incus delete vm1 --force
```
{{< /details >}}

ここでは2つの方法を試しました。

### Incusのプロファイルを作らずに済ませる方法

`incus init`ではプロファイルに含まれるディスクのサイズをオーバーライドしたり、設定の追加はできます。
が、プロファイルに含まれないデバイスの追加はエラーになったので、`incus init`のあとに別のコマンドで実行しています。
その後defaultプロファイルを外しています。

```
incus init freebsd14-image vm1 --vm \
  -c limits.cpu=2 -c limits.memory=2GB -c security.secureboot=false \
  -d root,size=80GB
incus config device add vm1 vtnet0 nic name=vtnet0 network=macvlan0
incus profile remove vm1 default
```

{{< details summary="（詳細）上記を実行したあとのVMの設定確認" >}}
```
$ incus config show vm1 -e
architecture: x86_64
config:
  limits.cpu: "2"
  limits.memory: 2GB
  security.secureboot: "false"
  volatile.apply_template: create
  volatile.base_image: 08d24f086ed48e1263cf91068c8b937159260527f523184ebdc75989983d93a3
  volatile.cloud-init.instance-id: b51a9b25-2ad4-4501-b413-afadab27b90b
  volatile.uuid: 7e9eae8f-c064-4181-9b70-f64d815bb25a
  volatile.uuid.generation: 7e9eae8f-c064-4181-9b70-f64d815bb25a
  volatile.vtnet0.hwaddr: 00:16:3e:c3:58:66
devices:
  root:
    path: /
    pool: default
    size: 80GB
    type: disk
  vtnet0:
    name: vtnet0
    network: macvlan0
    type: nic
ephemeral: false
profiles: []
stateful: false
description: ""
```
{{< /details >}}

あとは `incus start vm1 --console` などで起動できます。

次項の説明の都合上 `incus delete --force vm1`でVMを強制削除しておきます。

### macvlan用のIncusのプロファイルを作る方法

以下のようにmacvlan用のプロファイルを作成します。
```
profile_name=macvlan0
incus profile create ${profile_name}
incus profile set ${profile_name} limits.cpu=2 limits.memory=2GB security.secureboot=false
incus profile device add ${profile_name} root disk path=/ pool=default size=20GB
incus profile device add ${profile_name} vtnet0 nic name=vtnet0 network=macvlan0
```

このプロファイルを使えば、コマンド一発でrootディスクサイズもオーバーライドしつつ作成と起動までできます。

```
incus launch freebsd14-image vm1 --profile macvlan0 -d root,size=80GB
```
このあと`incus console vm1`でコンソールに接続します。あるいは`incus launch`のときに`--console`をつけておいても良いです。

## rootディスクのパーティション拡張

ディスクのサイズを80GBなどに増やして作成した場合、起動後にVMでパーティションを拡張する必要があります。

以下のように`- free -`が大きなサイズの場合は拡張が必要です。
```
root@freebsd:~ # gpart show da0
=>       34  156249949  da0  GPT  (75G)
         34        122    1  freebsd-boot  (61K)
        156      66584    2  efi  (33M)
      66740    2097152    3  freebsd-swap  (1.0G)
    2163892   75961092    4  freebsd-ufs  (36G)
   78124984   78124999       - free -  (37G)
```

以下のコマンドで拡張します。`gpart resize -i`のあとの4は上記の`freebsd-ufs`の左に書かれているパーティション番号を指定しています。

```
gpart resize -i 4 da0
growfs /
```

{{< details summary="（詳細）上記の実行例と事後確認" >}}
```
root@freebsd:~ # gpart resize -i 4 da0
da0p4 resized
root@freebsd:~ # growfs /
Device is mounted read-write; resizing will result in temporary write suspension for /.
It's strongly recommended to make a backup before growing the file system.
OK to grow filesystem on /dev/gpt/rootfs, mounted on /, from 36GB to 73GB? [yes/no] yes
super-block backups (for fsck_ffs -b #) at:
 76961472, 78244160, 79526848, 80809536, 82092224, 83374912, 84657600, 85940288, 87222976, 88505664, 89788352, 91071040, 92353728, 93636416, 94919104, 96201792, 97484480,
 98767168, 100049856, 101332544, 102615232, 103897920, 105180608, 106463296, 107745984, 109028672, 110311360, 111594048, 112876736, 114159424, 115442112, 116724800, 118007488,
 119290176, 120572864, 121855552, 123138240, 124420928, 125703616, 126986304, 128268992, 129551680, 130834368, 132117056, 133399744, 134682432, 135965120, 137247808,
 138530496, 139813184, 141095872, 142378560, 143661248, 144943936, 146226624, 147509312, 148792000, 150074688, 151357376, 152640064, 153922752
root@freebsd:~ # gpart show da0
=>       34  156249949  da0  GPT  (75G)
         34        122    1  freebsd-boot  (61K)
        156      66584    2  efi  (33M)
      66740    2097152    3  freebsd-swap  (1.0G)
    2163892  154086084    4  freebsd-ufs  (73G)
  156249976          7       - free -  (3.5K)
```
{{< /details >}}

## macvlanではなくincusbr0を使う方式は別記事で

[ZFSを使っているUbuntuのIncus上でincusbr0を使ってFreeBSDの仮想マシンを動かす · hnakamur's blog](../freebsd-vm-incus-incusbr0/)を参照してください。

