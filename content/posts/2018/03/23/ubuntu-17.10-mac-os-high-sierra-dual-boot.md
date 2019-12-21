+++
title="Ubuntu 17.10とmacOS High Sierraでデュアルブート構成にしてみた"
date = "2018-03-23T14:50:00+09:00"
lastmod = "2018-05-06T08:45:00+09:00"
tags = ["ubuntu", "macOS"]
categories = ["blog"]
+++


# はじめに

個人的にLinuxデスクトップの機運が高まってきたので、Ubuntu 17.10のデスクトップ環境を試してみました。
例によって自分用メモです。

FlutterでiOSアプリをビルドするのを試してみたりするのにmacOSは引き続き必要なのでデュアルブート
構成にします。

Antergosを試そうかとも思ったのですが、自宅サーバでUbuntuを使っていてPPAで独自debパッケージを作る
のにも慣れてきていることもあり、まずはUbuntuのデスクトップ環境を試すことにしました。

1ヶ月後にはUbuntu 18.04 LTSが出るので、そちらのベータとかdaily buildを試すのも良さそうかとも
思ったのですが、 Linuxデスクトップを使うのは約10年ぶりなのでまずは安定版で慣れようということで
Ubuntu 17.10にしました。

今回試したのは MacBook Pro 15-inch, Mid 2012 (機種ID: MacBookPro10,1)です。

インストールの手順自体は
[Ubuntu 17.10インストールガイド【スクリーンショットつき解説】 | Linux Fan](https://linuxfan.info/ubuntu-17-10-install-guide) に詳しい説明があるのでそちらを参照してください。

# 日本語Remixイメージをダウンロード

[Ubuntuの入手 | Ubuntu Japanese Team](https://www.ubuntulinux.jp/download) からダウンロードしました。

実は最初は [Download Ubuntu Desktop | Download | Ubuntu](https://www.ubuntu.com/download/desktop) のイメージを使ってインストールしてみたのですが、日本語入力の設定がよくわからなかったので、日本語Remixイメージで再インストールしました。最初から良い感じに設定されていて快適でした。ありがとうございます！


# EtcherでUbuntuインストール用のUSBメモリ作成

[Create a bootable USB stick on macOS | Ubuntu tutorials](https://tutorials.ubuntu.com/tutorial/tutorial-create-a-usb-stick-on-macos#3) で紹介されていた [Etcher](https://etcher.io/) を初めて使ってみました。

USBメモリを1つだけ挿しておくと書き込み先は自動選択されるので、ダウンロードしたISOイメージファイルを選んで書き込み開始のボタンを押すだけで良くて非常に簡単でした。macOS、 Windows とLinuxのGUI環境でISOイメージをUSBメモリに書くときは Etcher おすすめです！


# macOS側でUbuntuインストール用の領域確保

[ひょんなことからMacにUbuntuをインストールすることになった。後悔はしていない。 | カレリエ](https://www.karelie.net/move-from-osx-to-ubuntu/) と [How to Install and Dual Boot Linux and Mac OS](https://www.lifewire.com/dual-boot-linux-and-mac-os-4125733) を参考に、macOS のディスクユーティリティでUbuntu用にパーティションを作成しました。

この時点では最終的なUbuntu用のパーティション構成を作るわけではなくて、macOSのパーティションサイズを小さくしてUbuntuをインストールする領域を確保するために1つパーティションを作る感じです。

で、後ほどUbuntuのインストーラでそのパーティションを一旦削除して、最終的なUbuntu用のパーティション構成を作りました。

High Sierraのディスクユーティリティは初めて使ったのですが、ボリュームとパーティションというのがあってどう違うのかと思ったのですが [Is a Container, Volume, or Partition all the Same?](https://www.lifewire.com/volume-vs-partition-2260237) にわかりやすい記事がありました。

私のMacBook ProのSSDは512GB (約500GiB)だったので250GiBずつにわけることにしました。多少時間はかかりますが、macOSが起動したパーティションをその場で縮小できるのはすごいなと思いました。

# ブートマネージャ rEFInd は不要

昔 OSX, Windows, Linux というトリプルブート環境を作ったときは [The rEFInd Boot Manager](http://www.rodsbooks.com/refind/) を使ったのですが、 [Installing Ubuntu 17.10 on Macbook Pro Retina mid-2012](https://www.cberner.com/2017/12/03/installing-ubuntu-17-10-macbook-pro-retina-mid-2012/) にUbuntu 17.10では16.10からの改善点の1つとしてrEFIndが不要になったと書いてあったので、今回は使いませんでした。


# インストール時は有線LANを使用

Ubuntuのインストーラには MacBook Pro 2012 の無線LANのデバイスドライバが含まれておらず、インストーラ実行時にWifiが使えません。

[Installing Ubuntu 17.10 on Macbook Pro Retina mid-2012](https://www.cberner.com/2017/12/03/installing-ubuntu-17-10-macbook-pro-retina-mid-2012/) にはインストーラ時にはパッケージアップデートをしないようにしておいて、予めmacOSでWifiドライバと依存ライブラリをダウンロードしUSBメモリにコピーしておいてあとでUbuntuで起動したときにそこからインストールする手順が紹介されていました。

私は [Apple Thunderbolt - ギガビットEthernetアダプタ - Apple（日本）](https://www.apple.com/jp/shop/product/MD463ZM/A/apple-thunderbolt%E3%82%AE%E3%82%AC%E3%83%93%E3%83%83%E3%83%88ethernet%E3%82%A2%E3%83%80%E3%83%97%E3%82%BF) を持っているので、インストール時は有線LANを使うことにしました。

インストール後SSDからUbuntuを起動した後で以下のコマンドでWifiドライバをインストールしました。

```console
sudo apt update
sudo apt install -y bcmwl-kernel-source
```

このコマンド実行後はWifiが使えるようになりました。

# NVIDIAのプロプリエタリドライバは非使用

[MacBook Pro (15-inch, Mid 2012) - 技術仕様](https://support.apple.com/kb/SP694?locale=ja_JP&viewlocale=ja_JP) の「グラフィックスおよびビデオ」に以下のようにありますが、このMacBook ProにはNVIDIA GeForce GT 650Mが載っています。

* Intel HD Graphics 4000
* NVIDIA GeForce GT 650M、512MB GDDR5メモリ（15インチ2.3GHzモデル）またはNVIDIA GeForce GT 650M、1GB GDDR5メモリ（15インチ2.6GHzモデル）、グラフィックス自動切替機能
* デュアルディスプレイおよびビデオミラーリング：本体ディスプレイで標準解像度、外部ディスプレイで最大2,560 x 1,600ピクセル表示を同時サポート（数百万色以上対応）

標準の nouveau driver で特に問題なさそうでしたので、 NVIDIAのプロプリエタリドライバは使わないことにしました。

# Ubuntuのパーティション構成

メモリが十分あればスワップパーティションは無しでも良いかと一時期思っていたのですが
[In defence of swap: common misconceptions](https://chrisdown.name/2018/01/02/in-defence-of-swap.html)
という記事によるとあったほうが良いらしいので作っておくことにしました。

パーティション構成は [DiskSpace - Community Help Wiki](https://help.ubuntu.com/community/DiskSpace) を参考にして以下のようにしました。

* /boot : ext4 1GB
* swap : (物理RAMと同じ)16GB
* / : ext4 残り

後から見つけた [SwapFaq - Community Help Wiki](https://help.ubuntu.com/community/SwapFaq) によるとハイバネーションを使うなら最低で物理RAMと同じサイズが必要で、使わないなら `round(sqrt(RAM))` から物理RAMの2倍の間で選ぶ感じらしいです。

ブートローダのインストール先デバイスは `/dev/sda` にしました。
[Grub2/Installing - Community Help Wiki](https://help.ubuntu.com/community/Grub2/Installing)

# デュアルブートの起動切り替え

* 特に何もしないで起動するとUbuntuが起動します。
* macOSを起動したいときは option (alt) キーを押しながら起動してmacOSを選択して起動します。

# ファンクションキーのfnをデフォルトと逆に

デフォルトではfnなしでF1〜F12を押すと画面の明るさやボリューム調整になり、
fnキーを押しながらF1などを押すとファンクションキーになります。

私はmacOSでも逆のほうが好きでそのように設定していたのでUbuntuでもそうすることにしました。

これも [Installing Ubuntu 17.10 on Macbook Pro Retina mid-2012](https://www.cberner.com/2017/12/03/installing-ubuntu-17-10-macbook-pro-retina-mid-2012/) の記事に沿って設定しました。元ネタは [AppleKeyboard - Community Help Wiki](https://help.ubuntu.com/community/AppleKeyboard) だそうです。

```console
echo options hid_apple fnmode=2 | sudo tee -a /etc/modprobe.d/hid_apple.conf
sudo update-initramfs -u -k all
sudo reboot
```

# 解像度の変更

[Change the resolution or rotation of the screen](https://help.gnome.org/users/gnome-help/stable/look-resolution.html.en) に手順が書いてあります。

画面左上の「アクティビティ」を押して Displays と入力していきます。インクリメンタルサーチで下にマッチしたものが出ますので、「設定」の「ディスプレイ」を選びます。


デフォルトでは解像度が「2800x1800(16:10)」でサイズ調整が「200%」になっていました。
解像度を「1920x1280(16:10)」、サイズ調整を「100%」にすると私がmacOSで使っていたときと
同じになりました。

元の設定のほうが文字はくっきりして綺麗ですが、画面が広いほうが良いのでこれで使っています。


# 未調査の課題

シャットダウンとリブートが妙に遅いときがあります。体感で2分ぐらいかかってるような。すぐ再起動するときもあるので謎です。

# おわりに

macOSやWindowsに慣れていた私ですが違和感なく使えて非常に快適です。
Linuxデスクトップや日本語環境を作ってきてきた人たちに感謝しつつ、今後使っていこうと思います。
