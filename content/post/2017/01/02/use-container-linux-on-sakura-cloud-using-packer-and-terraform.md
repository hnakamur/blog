+++
date = "2017-01-02T15:34:23+09:00"
title = "さくらのクラウドでPackerとTerraformを使ってContainer Linuxの環境構築をしてみた"
Categories = []
Tags = ["kubernetes", "container-linux", "sakura-cloud", "terraform", "packer"]
Description = ""

+++
## はじめに
さくらのクラウドでPackerとTerraformを使って[CoreOS Container Linux](https://coreos.com/os/docs/latest/)の環境構築をしてみたのでメモです。

[パブリックアーカイブ・ISOイメージ](http://cloud-news.sakura.ad.jp/public_archive_iso/)にCoreOSはあるのですが、現状では残念ながらバージョンが 367.1.0 (stable) とかなり古い状態です。

そこで https://stable.release.core-os.net/amd64-usr/ 以下にある安定版公式ISOイメージの現時点の最新版である 1185.5.0 を使ってPackerでさくらのクラウド上にマイアーカイブを作成し、それを元にサーバで使用するディスクとサーバを作成します。

さくらのクラウドには[スタートアップスクリプト](http://cloud-news.sakura.ad.jp/startup-script/)という機能がありサーバの起動時に設定を行うことができるのですが、これが使えるのはCentOS、Debian、Ubuntuに限定されるようでCoreOSでは使えませんでした。

これだと構成はほぼ同じで静的IPアドレスだけが異なる複数のサーバを作りたい場合も、サーバ1台毎にPackerでマイアーカイブを作ってそこからサーバを作る必要があり、実用には厳しいなと思って一度は断念していました。

ルータを使わない構成であれば、まずはDHCPで起動してアドレスをもらってからプロビジョニング時に静的IPアドレスに切り替えるという手はあります。ですがルータを使う場合はDHCPサーバがいないのでこの手は使えません。

そんな時、[さくらのクラウド用Packerプラグイン](https://github.com/sacloud/packer-builder-sakuracloud)、[Terraform for さくらのクラウド](https://github.com/yamamoto-febc/terraform-provider-sakuracloud)、[Upload ISO image to SAKURA CLOUD](https://github.com/yamamoto-febc/sacloud-upload-image)などの便利なツールを作ってくださっている山本さんのツイートでContainer Linuxの[Customize with Config-Drive](https://coreos.com/os/docs/latest/config-drive.html)という機能を知りました。便利なツールに加えて有用な情報、いつもありがとうございます！

この記事はこの機能と上記の3つのツールを使ってContainer Linuxの環境構築をしてみたメモです。

## Container LinuxのISOイメージ作成

### Packerとさくらのクラウド用Packerプラグインの事前準備

[Packer by HashiCorp](https://www.packer.io/)と[さくらのクラウド用Packerプラグイン](https://github.com/sacloud/packer-builder-sakuracloud)をインストールしていない場合はそれぞれのドキュメントに従ってインストールしてください。

また[APIキーの取得](https://github.com/yamamoto-febc/terraform-provider-sakuracloud/blob/master/docs/installation.md#%E3%81%95%E3%81%8F%E3%82%89%E3%81%AE%E3%82%AF%E3%83%A9%E3%82%A6%E3%83%89api%E3%82%AD%E3%83%BC%E3%81%AE%E5%8F%96%E5%BE%97)と[APIキーの設定](https://github.com/sacloud/packer-builder-sakuracloud#apiキーの設定)も行っておいてください。

### PackerでさくらのクラウドにContainer Linuxのマイアーカイブを作成

以下の内容を `containerlinux.json` というファイルに保存します。
「ここにパスワードを設定」にはContainer Linuxで予め用意されている `core` ユーザに設定するパスワードを設定します。
「ここにパスワードのハッシュを設定」には [Generating a password hash](https://github.com/coreos/coreos-cloudinit/blob/master/Documentation/cloud-config.md#generating-a-password-hash) の手順で生成したパスワードのハッシュを設定します。

`sakuracloud_zone` は[さくらのクラウド API v1.1 ドキュメント](http://developer.sakura.ad.jp/cloud/api/1.1/)の一般注記事項のAPI URLに書いてあるゾーンのうち、自分が利用したいゾーンを指定します。以下の例では `is1b` (石狩第2ゾーン)としています。

```
{
  "variables": {
    "sakuracloud_zone": "is1b",
    "archive_name": "CoreOS 1185.5.0",
    "iso_url": "https://stable.release.core-os.net/amd64-usr/1185.5.0/coreos_production_iso_image.iso",
    "iso_checksum": "1c8e7948bdc54980df87a9a2b08fa744104f977950002f1605b60bf44d2021b9",
    "iso_checksum_type": "sha256",
    "install_disk_device": "/dev/vda",
    "tmp_password": "ここにパスワードを設定",
    "tmp_password_hash": "ここにパスワードのハッシュを設定"
  },
  "builders": [{
    "type": "sakuracloud",
    "zone": "{{user `sakuracloud_zone`}}",
    "os_type": "iso",
    "iso_url": "{{user `iso_url`}}",
    "iso_checksum": "{{user `iso_checksum`}}",
    "iso_checksum_type": "{{user `iso_checksum_type`}}",
    "us_keyboard": true,
    "boot_wait": "20s",
    "boot_command": [
      "cat <<'EOF' > /tmp/cloud-config.yml<enter>",
      "#cloud-config<enter>",
      "users:<enter>",
      "  - name: core<enter>",
      "    passwd: {{user `tmp_password_hash`}}<enter>",
      "EOF<enter><wait>",
      "sudo coreos-install -c /tmp/cloud-config.yml -d {{user `install_disk_device`}}<enter><wait>",
      "<wait10><wait10><wait10><wait10><wait10><wait10>",
      "<wait10><wait10><wait10>",
      "reboot<enter><wait>"
    ],
    "user_name": "core",
    "password": "{{user `tmp_password`}}",
    "archive_name": "{{user `archive_name`}}",
    "archive_tags": ["@size-extendable", "current-stable", "arch-64bit", "distro-containerlinux"]
  }],
  "provisioners": [{
    "type": "shell",
    "inline": [
      "sudo passwd -d core"
    ],
    "pause_before": "20s"
  }]
}
```

以下のコマンドを実行すると、一時的にサーバを作ってISOイメージからインストールし、その後シャットダウンしてマイアーカイブを作るという一連の処理を行ってくれます。

```
packer build containerlinux.json
```

## Terraform for さくらのクラウドでまずルータだけ作成

### Terraform for さくらのクラウドの事前準備
[Terraform](https://www.terraform.io/)と[Terraform for さくらのクラウド](https://github.com/yamamoto-febc/terraform-provider-sakuracloud)をインストールしていない場合は、それぞれのドキュメントに従ってインストールしてください。

またAPIキーと利用したいゾーンの設定も必要です。

APIキーの設定は[さくらのクラウド用Packerプラグイン](https://github.com/sacloud/packer-builder-sakuracloud)で行ったものと同じなので、ゾーンの設定を追加で行う必要があります。

```
$ export SAKURACLOUD_ACCESS_TOKEN=[APIトークン]
$ export SAKURACLOUD_ACCESS_TOKEN_SECRET=[APIシークレット]
$ export SAKURACLOUD_ZONE=is1b
```

### Terraform for さくらのクラウドでルータを作成

Terraformを使うなら本来は1つのtfファイルでルータとサーバを一気に作成したいところなのですが、サーバ1台毎の設定ファイルを含むISOイメージを作る部分をTerraform外のスクリプトで作成する都合上、2ステップに分ける必要があります。

まずは以下の内容を `server.tf` というファイルに保存します。

```
resource "sakuracloud_internet" "router01" {
    name = "router01"
    description = "by Terraform"
    tags = ["Terraform"]
    nw_mask_len = 28
    band_width = 100
}

output "router01_ipaddress" {
    value = "${sakuracloud_internet.router01.nw_address}"
}

output "router01_gateway" {
    value = "${sakuracloud_internet.router01.nw_gateway}"
}

output "router01_min_ipaddress" {
    value = "${sakuracloud_internet.router01.nw_min_ipaddress}"
}

output "router01_max_ipaddress" {
    value = "${sakuracloud_internet.router01.nw_max_ipaddress}"
}

output "router01_ipaddresses" {
    value = ["${sakuracloud_internet.router01.nw_ipaddresses}"]
}
```

`nw_mask_len` は[Terraform for さくらのクラウドのルーター](https://github.com/yamamoto-febc/terraform-provider-sakuracloud/blob/master/docs/configuration/resources/internet.md)のドキュメントのパラメーターの項を参考に、必要なIPアドレスの数に応じて `/28`, `/27`, `/26` から選択してください。設定する値は `/` 無しの数値です。

なお、[「ルータ＋スイッチ」 一部の追加IPアドレス個数でのお申込み方法変更のお知らせ | さくらのクラウドニュース](http://cloud-news.sakura.ad.jp/2015/03/31/ipaddr24-25/) を見ると `/25`, `/24` も利用可能ですが営業に問い合わせが必要なため、APIからは利用不可となっています。

`name` や `description` はお好みで変更してください。

ルーターに付与されるIPアドレスの範囲はルーター作成後に確定し[Terraform for さくらのクラウドのルーター](https://github.com/yamamoto-febc/terraform-provider-sakuracloud/blob/master/docs/configuration/resources/internet.md)のドキュメントの属性 `nw_address` などに設定されます。

上記の `server.tf` ではTerraformの[Configuring Outputs](https://www.terraform.io/docs/configuration/outputs.html)の機能を使ってこれらの属性を出力するようにしています。

Terraformの使い方自体は通常通りです。

```
terraform plan
```

でプランを確認し、

```
terraform apply
```

で適用します。

すると以下のように出力が出ます。以下ではIPアドレスを伏せています。

```
Outputs:

router01_gateway = xxx.yyy.zzz.145
router01_ipaddress = xxx.yyy.zzz.144
router01_ipaddresses = [
    xxx.yyy.zzz.148,
    xxx.yyy.zzz.149,
    xxx.yyy.zzz.150,
    xxx.yyy.zzz.151,
    xxx.yyy.zzz.152,
    xxx.yyy.zzz.153,
    xxx.yyy.zzz.154,
    xxx.yyy.zzz.155,
    xxx.yyy.zzz.156,
    xxx.yyy.zzz.157,
    xxx.yyy.zzz.158
]
router01_max_ipaddress = xxx.yyy.zzz.158
router01_min_ipaddress = xxx.yyy.zzz.148
```

## 作成したいサーバ1台毎にContainer LinuxのConfig DriveのISOイメージを作成

[Customize with Config-Drive](https://coreos.com/os/docs/latest/config-drive.html)の手順に従ってConfig DriveのISOイメージを作成し、[Upload ISO image to SAKURA CLOUD](https://github.com/yamamoto-febc/sacloud-upload-image)を使ってさくらのクラウドにアップロードします。

### 事前準備

私はCentOSで作業したので、ISOイメージの作成に使う `mkisofs` を以下のコマンドでインストールしました。

```
sudo yum install -y mkisofs
```

macOSをお使いの場合は `mkisofs` は不要ですが、次項の `mkupload.sh` で `mkisofs` を呼び出しているところを[Customize with Config-Drive](https://coreos.com/os/docs/latest/config-drive.html)を参考に書き変えてください。

[Upload ISO image to SAKURA CLOUD](https://github.com/yamamoto-febc/sacloud-upload-image)をインストールしていない場合はインストールしてください。

APIキーの取得とAPIキー及びゾーンの環境変数設定は上記のTerraform for さくらのクラウドのときと同じなので既に行っていれば不要です。

### サーバを作成するリージョンの推奨ネームサーバのIPアドレスを調べる

この記事を書いた当初はネームサーバの調べ方がわからなくて、GoogleのDNS 8.8.8.8 を指定していましたが、サーバを作成した後さくらのクラウドのコントロールパネルでサーバの詳細情報のNICタブを選択すると「このリージョンの推奨ネームサーバ: 133.242.0.3, 133.242.0.4」のように表示されていることに気づきました。

リージョン毎のネームサーバ一覧はさくらのクラウドのドキュメントでは見つけられなかったのですが、[設備関連API - さくらのクラウド API v1.1 ドキュメント](http://developer.sakura.ad.jp/cloud/api/1.1/facility/)のリージョン一覧を取得のレスポンスにリージョン毎のネームサーバのIPアドレスが含まれていました。

実際に試した結果は以下の通りです。

```
$ curl -su $SAKURACLOUD_ACCESS_TOKEN:$SAKURACLOUD_ACCESS_TOKEN_SECRET \
  https://secure.sakura.ad.jp/cloud/zone/$SAKURACLOUD_ZONE/api/cloud/1.1/region \
  | jq .
{
  "From": 0,
  "Count": 3,
  "Total": 3,
  "Regions": [
    {
      "Index": 0,
      "ID": 210,
      "Name": "東京",
      "Description": "東京",
      "NameServers": [
        "210.188.224.10",
        "210.188.224.11"
      ]
    },
    {
      "Index": 1,
      "ID": 290,
      "Name": "Sandbox",
      "Description": "Sandbox",
      "NameServers": [
        "133.242.0.3",
        "133.242.0.4"
      ]
    },
    {
      "Index": 2,
      "ID": 310,
      "Name": "石狩",
      "Description": "石狩",
      "NameServers": [
        "133.242.0.3",
        "133.242.0.4"
      ]
    }
  ],
  "is_ok": true
}
```

### Config DriveのISOイメージを作成・アップロード

以下のシェルスクリプトを `mkupload.sh` という名前で保存し、 `chmod +x mkupload.sh` で実行パーミションを付けます。

```
#!/bin/sh
set -eu
basedir=/tmp/configdrive.$$
server="$SERVER"
ssh_pub_key="$SSH_PUB_KEY"
dns1="$DNS1"
dns2="$DNS2"
address="$ADDRESS"
gateway="$GATEWAY"

mkdir -p "$basedir/openstack/latest"

cat <<EOF > "$basedir/openstack/latest/user_data"
#cloud-config

users:
  - name: "core"
    ssh-authorized-keys:
      - "${ssh_pub_key}"
coreos:
  units:
    - name: 00-eth0.network
      runtime: true
      content: |
        [Match]
        Name=eth0

        [Network]
        DNS=${dns1}
        DNS=${dns2}
        Address=${address}
        Gateway=${gateway}
EOF

config_name="${server}-config"
mkisofs -R -V config-2 -o "${config_name}.iso" "${basedir}"
sacloud-upload-image -f "${config_name}.iso" "${config_name}"
```

[Customize with Config-Drive](https://coreos.com/os/docs/latest/config-drive.html)では `DNS=` の行は1つだけですが、[systemd.network](https://www.freedesktop.org/software/systemd/man/systemd.network.html#DNS=)のドキュメントによると複数指定可能なので2つ指定するようにしました。

以下のように実行します。公開鍵のパスはとIPアドレスは適宜変更してください。

```
SERVER=server01 \
SSH_PUB_KEY="`cat ~/.ssh/id_rsa.pub`" \
DNS1=133.242.0.3 \
DNS2=133.242.0.4 \
ADDRESS=xxx.yyy.zzz.148/28 \
GATEWAY=xxx.yyy.zzz.145 \
./mkuploadconfig.sh
```

```
SERVER=server02 \
SSH_PUB_KEY="`cat ~/.ssh/id_rsa.pub`" \
DNS1=133.242.0.3 \
DNS2=133.242.0.4 \
ADDRESS=xxx.yyy.zzz.149/28 \
GATEWAY=xxx.yyy.zzz.145 \
./mkuploadconfig.sh
```

`ADDRESS` の値は上記で出力された `router01_ipaddresses` の値を上から順番に使い、ネットワークマスク付きで指定しています。

作成されるISOイメージの名前は `${SERVER}-config` となります。上記の例だと `server01-config` と `server02-config` です。


## Terraform for さくらのクラウドでルータに繋がったサーバを作成

上記で作成していた `server.tf` にサーバ、ディスクのリソースを追記します。

```
resource "sakuracloud_internet" "router01" {
    name = "router01"
    description = "by Terraform"
    tags = ["Terraform"]
    nw_mask_len = 28
    band_width = 100
}

resource "sakuracloud_server" "server01" {
    name = "server01"
    disks = ["${sakuracloud_disk.disk01.id}"]
    cdrom_id = "${data.sakuracloud_cdrom.server01_config.id}"
    tags = ["@virtio-net-pci", "Terraform"]
    description = "by Terraform"
    core = "1"
    memory = "1"
    base_interface = "${sakuracloud_internet.router01.switch_id}"
    additional_interfaces = [""]
}
resource "sakuracloud_disk" "disk01" {
    name = "disk01"
    source_archive_id = "${data.sakuracloud_archive.containerlinux.id}"
    size = "40"
    description = "by Terraform"
}
data "sakuracloud_cdrom" "server01_config" {
    filter = {
        name   = "Name"
        values = ["server01-config"]
    }
}

resource "sakuracloud_server" "server02" {
    name = "server02"
    disks = ["${sakuracloud_disk.disk02.id}"]
    cdrom_id = "${data.sakuracloud_cdrom.server02_config.id}"
    tags = ["@virtio-net-pci", "Terraform"]
    description = "by Terraform"
    core = "1"
    memory = "1"
    base_interface = "${sakuracloud_internet.router01.switch_id}"
    additional_interfaces = [""]
}
resource "sakuracloud_disk" "disk02" {
    name = "disk02"
    source_archive_id = "${data.sakuracloud_archive.containerlinux.id}"
    size = "40"
    description = "by Terraform"
}
data "sakuracloud_cdrom" "server02_config" {
    filter = {
        name   = "Name"
        values = ["server02-config"]
    }
}

data "sakuracloud_archive" "containerlinux" {
    filter = {
        name   = "Tags"
        values = ["current-stable", "arch-64bit", "distro-containerlinux"]
    }
}

output "router01_ipaddress" {
    value = "${sakuracloud_internet.router01.nw_address}"
}

output "router01_gateway" {
    value = "${sakuracloud_internet.router01.nw_gateway}"
}

output "router01_min_ipaddress" {
    value = "${sakuracloud_internet.router01.nw_min_ipaddress}"
}

output "router01_max_ipaddress" {
    value = "${sakuracloud_internet.router01.nw_max_ipaddress}"
}

output "router01_ipaddresses" {
    value = ["${sakuracloud_internet.router01.nw_ipaddresses}"]
}
```

serverの `core`, `memory` やdiskの `size` などはお好みで変更してください。
設定可能な値の一覧は[サーバー/ディスク機能の仕様・料金| さくらのクラウド](http://cloud.sakura.ad.jp/specification/server-disk/)を参照してください。

あとは通常通りTerraformを実行するだけです。

```
terraform plan
```

でプランを確認し、

```
terraform apply
```

で適用します。

これでルーターに繋がったContainer Linuxのサーバを静的IPアドレス設定で作成できました！


## 気になった点

### 作成したサーバをコンパネでみるとIPアドレスが表示されていない

コンパネのサーバ詳細の「NIC」タブのルータ＋スイッチの行の「IPv4アドレス」がハイフンになっていました。またコンパネの「マップ」で見てもIPアドレスが表示されていませんでした。

まあこれはディスクの修正機能を使っていないので仕方ない気もします。
が、[マップ画面に表示されるIPアドレス編集機能を追加しました | さくらのクラウドニュース](http://cloud-news.sakura.ad.jp/2014/09/19/map-ipaddr-modifying/)の手順で設定すれば大丈夫でした。

実現可能かどうかまだよくわかっていないのですが[Terraform for さくらのクラウド](https://github.com/yamamoto-febc/terraform-provider-sakuracloud)でのサーバ作成時にこのIPアドレスを設定できると理想的だなあと思います。

### Container LinuxのConfig DriveをTerraformで作成できたらさらに理想的

現状だとこの記事で書いたように一旦ルーターだけ作って、IPアドレスを調べてから、サーバを作るという手順を踏む必要があります。このため、Terraformの設定ファイルを書き変えて2回適用する必要があります。

もしContainer LinuxのConfig DriveをTerraformで作成できたら、Terraformの設定ファイルを最初からサーバ込みで記述して1回の適用でルータとサーバを一気に作成できることになるので、こうなれば最高だなーと思います。が、どういう仕様にするかと実装を推測してみるとこれはかなり難しそうな気がします。

### Packerで作ったマイアーカイブでcoreユーザのパスワードを消せていない

Container Linuxはcoreユーザでssh鍵認証でログインすることが前提となっていて、パスワードは元々設定されていません。が、Packerでは `boot_command` でセットアップした後パスワード認証でssh (Windowsの場合はwinrm)で接続してprovisionerを動かすようになっています。

そこで上記の `containerlinux.json` では `boot_command` 内でcoreユーザにパスワードを設定し、ssh接続した後にshell provisionerで `sudo passwd -d core` というコマンドを実行してパスワードを消そうとしています。

Packerの実行結果は以下のようになり、 `passwd: password expiry information changed.` の出力でパスワード削除がうまく行っているように見えます。

```
$ packer build containerlinux.json
sakuracloud output will be in this color.

==> sakuracloud: Downloading or copying ISO
    sakuracloud: Downloading or copying: https://stable.release.core-os.net/amd64-usr/1185.5.0/coreos_production_iso_image.iso
==> sakuracloud: Creating temporary SSH key for instance...
==> sakuracloud: Creating server...
==> sakuracloud: Waiting 20s for boot...
==> sakuracloud: Waiting for server to become active...
==> sakuracloud: Connecting to VM via VNC
==> sakuracloud: Typing the boot command over VNC...
==> sakuracloud: Waiting for SSH to become available...
==> sakuracloud: Connected to SSH!
==> sakuracloud: Pausing 20s before the next provisioner...
==> sakuracloud: Provisioning with shell script: /tmp/packer-shell837255893
    sakuracloud: passwd: password expiry information changed.
==> sakuracloud: Gracefully shutting down server...
==> sakuracloud: Creating archive: CoreOS 1185.5.0
==> sakuracloud: Destroying server...
Build 'sakuracloud' finished.

==> Builds finished. The artifacts of successful builds are:
--> sakuracloud: A archive was created: 'CoreOS 1185.5.0' (ID: 112900007545) in zone 'is1b'
```

が、実際に作成したアーカイブをコピーしてディスクとサーバを作成して、sshを試してみるとパスワードでログインできてしまいます。sshでログインした後 `sudo passwd -d core` でパスワードを消すとその後はパスワード認証は失敗し鍵認証だけ成功するようになります。

`sudo passwd -d core` と実行したときにはPackerで実行したときと同じ `sakuracloud: passwd: password expiry information changed.` というメッセージが表示されていました。何が原因かわかりませんが、現状は今書いたとおりです。

ということでパスワード認証をしたく無い場合は、サーバ起動後に `sudo passwd -d core` してください。

## おわりに
ということで少々不便な点はありますが、さくらのクラウドでContainer Linuxの最新版を使うことが出来ました！

### サーバ1台毎にConfig DriveのISOイメージを作成することの利点

サーバ1台毎にConfig DriveのISOイメージを作成するのは面倒な気もしますが、実際に使ってみるとそれを上回る利点がありました。

* 利点1: サーバ1台毎にマイアーカイブを作るよりは早くて手軽
    - Packerで `boot_command` と provisioners でプロビジョニングした後サーバを停止してディスクのアーカイブを作成するのですが、この最後の工程が結構時間がかかる時があります。早いときは5分もかからないのですが、混んでいる時は遅くなるらしく1時間弱待たされることもありました。
    - 一方、Config DriveのISOイメージのアップロードはいつも数十秒程度でサクッと終わりました。
    - この記事の方式だと利用したいディストリビューションのバージョン1つに対してマイアーカイブを作成するのは1回で済むので、時間が節約できます。
* 利点2: 一度ルーターを作ってIPアドレスが確定した後はConfig DriveのISOイメージは割と使いまわせる
    - こちらは普通の使い方ではあまり関係ないかもしれませんが、今回Packerでマイアーカイブを作るときに `boot_command` や provisioners の設定を変えて何度も試行錯誤して作り直しました。その度にサーバと付随するディスクも作り直したのですが、Config DriveのISOイメージはそのまま残しておいて使いまわすことが出来ました。
    - このようにベースのアーカイブを何度も変えてサーバを作り直すような試行錯誤をするケースではサーバ1台毎の設定を別出しにしておけるConfig DriveのISOイメージはなかなか便利だなと思いました。

## 編集履歴

### 2017-01-02 21:16頃
ISOイメージは[データソース](https://github.com/yamamoto-febc/terraform-provider-sakuracloud/blob/master/docs/configuration/resources/data_resource.md)の機能ですでに参照可能とのご指摘を山本さんから頂きました。
すみません、私のドキュメントの読み込み不足でした。
検証してみたら無事使えました！元記事に打ち消し線いれて追記しようかと思ったのですが、わかりにくくなるので直接書き換えました。

変更内容が気になる方は[gitの差分](https://github.com/hnakamur/blog/commit/20170102_2116)を参照してください。

### 2017-01-02 21:40頃
「気になった点」に「Packerで作ったマイアーカイブでcoreユーザのパスワードを消せていない」を追記しました。

### 2017-01-02 22:30頃
さくらのクラウドのリージョンごとの推奨ネームサーバを使うように改良しました。
変更内容は[gitの差分](https://github.com/hnakamur/blog/commit/20170102_2230)を参照してください。

### 2017-01-02 22:50頃
「おわりに」に「サーバ1台毎にConfig DriveのISOイメージを作成することの利点」を追記しました。
