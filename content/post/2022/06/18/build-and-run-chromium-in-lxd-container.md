---
title: "LXDコンテナ内でChromiumをビルド・実行してみた"
date: 2022-06-18T14:52:08+09:00
---

## はじめに

背景は https://twitter.com/hnakamur2/status/1537786550716489728 のスレッドに書きましたが、こちらにも残しておきます。

Chrome 拡張の API のコンテキストメニューをクリックしたときに呼ばれる onClick ハンドラの引数に渡される [chrome.contextMenus.OnClickData](https://developer.chrome.com/docs/extensions/reference/contextMenus/#type-OnClickData) に `linkUrl` というプロパティがあるのですが `linkText` は無いのでこれを追加したいということです（ちなみに Firefox の [menus.OnClickData - Mozilla | MDN](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/menus/OnClickData) には `linkText` もあります）。

自作の Chrome 拡張 [hnakamur/FormatLink-Chrome: Format a link and title of the active tab of Chrome and MS Edge and copy it the clipboard](https://github.com/hnakamur/FormatLink-Chrome/) でページ内のリンクにマウスカーソルをおいた状態でコンテキストメニューを選ぶと `onClick` ハンドラが呼ばれて `linkUrl` でリンクの URL は分かるけど、リンクのテキストが取得できないので困っているからです。

回避策として現状はページ内のリンクを順に見ていって同じ URL のリンクがあったらそのテキストを使っているのですが、ページ内に同じリンクが複数あると別のテキストになってしまう場合があるという問題があります。

5年前に機能追加要望のイシュー [766074 - Feature request: Please add info.linkText property to context menu click callback - chromium](https://bugs.chromium.org/p/chromium/issues/detail?id=766074) を立てたのですが、2018年に `Owner: a_deleted_user` と担当者不在になっていました。

## ビルド

[chromium/build_instructions.md at main · chromium/chromium](https://github.com/chromium/chromium/blob/main/docs/linux/build_instructions.md) の手順に沿ってビルドしてみました。

### 最初 Docker でビルドしようとしたが snapcraft を入れ始めたのでやめた

以下のような Dockerfile で試行錯誤中でした。

最初は Ubuntu 22.04 LTS のホスト環境でビルドしようとしていたのですが、
`./build/install-build-deps.sh` で以下の Dockerfile 内のコメントのようなエラーが出ました。

そこでサポートされているディストリビューション内で Ubuntu の最新の LTS で 20.04 を使って Docker でビルドしようとしました。

が、途中で snapcraft をセットアップ？とかいうメッセージが出てきたところで Ctrl-C を押して中断しました。 snapcraft は systemd が必要で Docker で systemd を使うのは面倒だと思ったので。

```
FROM ubuntu:20.04
# NOTE: ubuntu:22.04 is not supported as of 2022-06-18.
#
# $ ./build/install-build-deps.sh
# ERROR: The only supported distros are
#         Ubuntu 14.04 LTS (trusty with EoL April 2022)
#         Ubuntu 16.04 LTS (xenial with EoL April 2024)
#         Ubuntu 18.04 LTS (bionic with EoL April 2028)
#         Ubuntu 20.04 LTS (focal with Eol April 2030)
#         Ubuntu 20.10 (groovy)
#         Debian 10 (buster) or later

RUN apt-get update \
 && apt-get install -y build-essential git python3 curl lsb-release sudo

WORKDIR /
RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
ENV PATH="${PATH}:/depot_tools"

RUN mkdir /chromium
WORKDIR /chromium
RUN fetch --nohooks --no-history chromium

WORKDIR /chromium/src
RUN ./build/install-build-deps.sh
RUN gclient runhooks
RUN gn gen out/Default
RUN autoninja -C out/Default chrome
```

### LXD コンテナで Chromium をビルド

そこで LXD で Ubuntu 20.04 LTS のコンテナを作ってそこでビルドしてみました。

```
lxc launch ubuntu:20.04 chromium-dev
```

で起動後

```
lxc exec chromium-dev bash
```

でコンテナ内で bash を起動します。

後は上記の Dockerfile の手順と同様です。

```
apt-get update
apt-get install -y build-essential git python3 curl lsb-release sudo

cd /
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH="${PATH}:/depot_tools"

mkdir /chromium
cd /chromium
fetch --nohooks --no-history chromium

cd /chromium/src
./build/install-build-deps.sh
gclient runhooks
gn gen out/Default
autoninja -C out/Default chrome
```

ですが
```
Running depot tools as root is sad.
Running: gclient sync --nohooks --no-history
Running depot tools as root is sad.
```
のようなメッセージが出ていたので、 `apt-get install` の後は `sudo -iu ubuntu` で ubuntu ユーザに切り替えて作業したほうが良さそうでした。

私は全部 root ユーザのままでビルドしたのですが、root ユーザのままだと起動時にエラーになったので、 `chown -R ubuntu: /chromium` で所有者を変更しました。

ビルドは以下の環境で約 2 時間かかりました。

* ThinkCentre M75q Tiny Gen 2 (価格.com限定 プレミアム、製品番号: 11JJCTO1WW、購入日: 2020-11-02)
* CPU: [AMD Ryzen™ 7 PRO 4750GE](https://www.amd.com/ja/products/apu/amd-ryzen-7-pro-4750ge)
* RAM: PATRIOT パトリオットメモリ ノートパソコン用メモリ SODIMM DDR4 3200MHz PC4-25600 32GB CL22 PSD432G32002S x 2
* SSD: Western Digital SSD 1TB WD Blue SN550 PC M.2-2280 NVMe WDS100T2B0C-EC
* OS: Ubuntu 22.04 LTS
* ファイルシステム: ZFS （圧縮・暗号化は無し）

## LXD コンテナ内で Chromium を実行してホスト環境に表示

以下の記事を参考にしつつ、最初の記事の手順を真似しました。

* [How to easily run graphics-accelerated GUI apps in LXD containers on your Ubuntu desktop – Mi blog lah!](https://blog.simos.info/how-to-easily-run-graphics-accelerated-gui-apps-in-lxd-containers-on-your-ubuntu-desktop/)
* [Running Gui apps in LXD - LXD - Linux Containers Forum](https://discuss.linuxcontainers.org/t/running-gui-apps-in-lxd/9515)
* [LXD で作る仮想化 GUI 環境 - Qiita](https://qiita.com/yoshi10ryu1/items/9bbe1434874b3cc88e57)
* [DockerもいいけどLXDもね 1 〜LXDEデスクトップ環境の構築〜](https://zenn.dev/tantan_tanuki/articles/7796a4f1d6d1b0)

以下の内容で `lxdguiprofile.txt` というファイルを作成します。

```
config:
  environment.DISPLAY: :0
  raw.idmap: both 1000 1000
  user.user-data: |
    #cloud-config
    runcmd:
      - 'sed -i "s/; enable-shm = yes/enable-shm = no/g" /etc/pulse/client.conf'
      - 'echo export PULSE_SERVER=unix:/tmp/.pulse-native | tee --append /home/ubuntu/.profile'
    packages:
      - x11-apps
      - mesa-utils
      - pulseaudio
description: GUI LXD profile
devices:
  PASocket:
    path: /tmp/.pulse-native
    source: /run/user/1000/pulse/native
    type: disk
  X0:
    path: /tmp/.X11-unix/X0
    source: /tmp/.X11-unix/X0
    type: disk
  mygpu:
    type: gpu
name: gui
used_by:
```

その後以下のコマンドを実行して `gui` という名前で LXD のプロファイルを作成します。

```
lxc profile create gui
cat lxdguiprofile.txt | lxc profile edit gui
```

作成したプロファイルを上記で作成したコンテナ `chromium-dev` に反映します。

```
lxc profile assign chromium-dev default,gui
```

コンテナを再起動します。

```
lxc restart chromium-dev
```

コンテナ内に ubuntu ユーザで bash シェルを起動します。
```
lxc exec chromium-dev -- sudo -iu ubuntu
```

LXD コンテナ内で Chromium を起動してみると、無事ホスト環境に表示されました。

```
/chromium/src/out/Default/chrome
```

## 改変してビルド

コンテナ内の `/chromium/src` 以下で
[Add linkText property to extension chrome.contextMenus.OnClickData · hnakamur/chromium@fdb048d](https://github.com/hnakamur/chromium/commit/fdb048d6d75e9d43a32ed1dce267af35a9f954bb)
の変更を加えて再度ビルドしてみました。

```
cd /chromium/src
autoninja -C out/Default chrome
```

今度は変更した `chrome/browser/extensions/menu_manager.cc` だけがコンパイルされて、リンクが走って数分程度で済みました。

## ホスト環境上の自作拡張のソースディレクトリをコンテナでマウント

[LXD で作る仮想化 GUI 環境 - Qiita](https://qiita.com/yoshi10ryu1/items/9bbe1434874b3cc88e57) の [ホストのディレクトリをmountする](https://qiita.com/yoshi10ryu1/items/9bbe1434874b3cc88e57#%E3%83%9B%E3%82%B9%E3%83%88%E3%81%AE%E3%83%87%E3%82%A3%E3%83%AC%E3%82%AF%E3%83%88%E3%83%AA%E3%82%92mount%E3%81%99%E3%82%8B) を参考にマウントしました。

```
lxc exec chromium-dev -- mkdir -p /mnt/disk1/chrome1
mkdir /home/hnakamur/chromium-dev-share-disk
lxc config device add chromium-dev share-drdata disk source=/mnt/disk1/chrome1 path=/home/hnakamur/chromium-dev-share-disk
```

これでホスト環境の `/home/hnakamur/chromium-dev-share-disk` 以下に自作拡張 [hnakamur/FormatLink-Chrome](https://github.com/hnakamur/FormatLink-Chrome/) のソースを配置して Chrome の extensions の Devloper mode の Launch unpacked で読み込んで動作確認しました。
