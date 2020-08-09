---
title: "ksarでsysstatのメトリックをグラフで表示"
date: 2020-08-09T09:28:33+09:00
---

## はじめに

サーバーのメトリックを確認するのに [sysstat](http://sebastien.godard.pagesperso-orange.fr/) の sar コマンドが便利ですが、 ksar でグラフで見るほうがさらに便利です。

ということで手順をメモしておきます。

## sysstat のインストールと設定

### sysstat のインストール

Ubuntu では以下のように sysstat パッケージをインストールします。

```console
sudo apt install sysstat
```

### 1分単位に記録するように設定変更

パッケージに含まれる sysstat の cron 用の設定ファイル `/etc/cron.d/sysstat` は以下のように10分ごとにメトリックを記録するようになっています。

```
# The first element of the path is a directory where the debian-sa1
# script is located
PATH=/usr/lib/sysstat:/usr/sbin:/usr/sbin:/usr/bin:/sbin:/bin

# Activity reports every 10 minutes everyday
5-55/10 * * * * root command -v debian-sa1 > /dev/null && debian-sa1 1 1

# Additional run at 23:59 to rotate the statistics file
59 23 * * * root command -v debian-sa1 > /dev/null && debian-sa1 60 2
```

以下のコマンドを実行して1分単位に記録するように変更します
（横道の補足ですが `sed -i` を使って上書きする場合は事前に `-i` 無しで実行して期待通りの出力になっているか確認してから `-i` 付きで実行して上書きするのが確実です）。

```console
sudo sed -i 's/every 10 minutes/every minute/;s|5-55/10|*|' /etc/cron.d/sysstat
```

### sysstatを有効にする

パッケージに含まれる `/etc/default/sysstat` は以下のようになっています。

```
#
# Default settings for /etc/init.d/sysstat, /etc/cron.d/sysstat
# and /etc/cron.daily/sysstat files
#

# Should sadc collect system activity informations? Valid values
# are "true" and "false". Please do not put other values, they
# will be overwritten by debconf!
ENABLED="false"
```

以下のコマンドを実行して有効にします。

```console
sudo sed -i 's/^ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
```

## sar コマンドで出力する際に時刻を24時間制にする方法

sar では様々なメトリックが出力できます（詳しくは `man sar` を参照）。
ksar でグラフを見るためには `sar -A` で全ての種類のメトリックを出力します。

単に `sar -A` とすると時刻が `12:01:01 AM` のような12時間制になってしまいます。
以下のように `LC_TIME=C` をつけて実行すれば24時間制になります
（[time - How to get sar command value in 24 hour format (from 00:00:00 to 23:59:59) in Linux? - Stack Overflow](https://stackoverflow.com/questions/28092728/how-to-get-sar-command-value-in-24-hour-format-from-000000-to-235959-in-li) で知りました）。

```console
LC_TIME=C sar -A
```

前日以前のメトリックを見たい場合は `-f` でファイルを指定します。
下記の saDD の DD の部分は日付をゼロパディングして指定します。

```console
LC_TIME=C sar -A -f /var/log/sysstat/saDD
```

事前に `ls -l /var/log/sysstat/` でどのファイルがあるか確認してから実行すると良いです。とあるサーバーでは以下のようになっていました。

```console
# ls -l /var/log/sysstat/
total 51576
-rw-r--r-- 1 root root 3657616 Aug  2 00:00 sa01
-rw-r--r-- 1 root root 3660152 Aug  3 00:00 sa02
-rw-r--r-- 1 root root 3657616 Aug  4 00:00 sa03
-rw-r--r-- 1 root root 3660152 Aug  5 00:00 sa04
-rw-r--r-- 1 root root 3660152 Aug  6 00:00 sa05
-rw-r--r-- 1 root root 3660152 Aug  7 00:00 sa06
-rw-r--r-- 1 root root 3660152 Aug  8 00:00 sa07
-rw-r--r-- 1 root root 3660152 Aug  9 00:00 sa08
-rw-r--r-- 1 root root 1534984 Aug  9 10:03 sa09
-rw-r--r-- 1 root root 2744272 Aug  2 00:06 sar01
-rw-r--r-- 1 root root 2744272 Aug  3 00:09 sar02
-rw-r--r-- 1 root root 2744272 Aug  4 00:09 sar03
-rw-r--r-- 1 root root 2744272 Aug  5 00:09 sar04
-rw-r--r-- 1 root root 2744272 Aug  6 00:06 sar05
-rw-r--r-- 1 root root 2744272 Aug  7 00:08 sar06
-rw-r--r-- 1 root root 2744272 Aug  8 00:07 sar07
-rw-r--r-- 1 root root 2744272 Aug  9 00:08 sar08
```

```console
# ls -lh /var/log/sysstat/
total 51M
-rw-r--r-- 1 root root 3.5M Aug  2 00:00 sa01
-rw-r--r-- 1 root root 3.5M Aug  3 00:00 sa02
-rw-r--r-- 1 root root 3.5M Aug  4 00:00 sa03
-rw-r--r-- 1 root root 3.5M Aug  5 00:00 sa04
-rw-r--r-- 1 root root 3.5M Aug  6 00:00 sa05
-rw-r--r-- 1 root root 3.5M Aug  7 00:00 sa06
-rw-r--r-- 1 root root 3.5M Aug  8 00:00 sa07
-rw-r--r-- 1 root root 3.5M Aug  9 00:00 sa08
-rw-r--r-- 1 root root 1.7M Aug  9 11:05 sa09
-rw-r--r-- 1 root root 2.7M Aug  2 00:06 sar01
-rw-r--r-- 1 root root 2.7M Aug  3 00:09 sar02
-rw-r--r-- 1 root root 2.7M Aug  4 00:09 sar03
-rw-r--r-- 1 root root 2.7M Aug  5 00:09 sar04
-rw-r--r-- 1 root root 2.7M Aug  6 00:06 sar05
-rw-r--r-- 1 root root 2.7M Aug  7 00:08 sar06
-rw-r--r-- 1 root root 2.7M Aug  8 00:07 sar07
-rw-r--r-- 1 root root 2.7M Aug  9 00:08 sar08
```

中身を見てみると `sarDD` のほうはテキスト形式で時刻も24時間制になっていました。

これは `/etc/cron.daily/sysstat` で実行される [sa2 (8)](http://manpages.ubuntu.com/manpages/focal/en/man8/sa2.8.html) で作成されることが分かりました。

ということで既に作成済みであれば `sarDD` ファイルを見れば良いです。

未作成の場合は以下のように実行して手動で作成します。
/var/log/sysstat/` で作成すると紛らわしいので `/var/log/sysstat/` 以外の作業ディレクトリで作成するようにします。

```console
LC_TIME=C sar -A -f /var/log/sysstat/saDD > sarDD
```

## ksarのforkのセットアップと使い方

#### OpenJDK のダウンロードとセットアップ

職場のPCがWindowsなので、Windows用の手順を書いておきます。
[OpenJDK](https://openjdk.java.net/) から https://jdk.java.net/14/ を開いてWindows/x64のzipのリンクをクリックしてダウンロードします。

2020-08-09時点の最新版は 14.0.2 でした。
ダウンロードした zip ファイルをエクスプローラーで見ると中に `jdk-14.0.2` というディレクトリーがあるのでこれをお好みの場所に展開します。
ここでは `C:\jdk-14.0.2` とします。

#### ksarのforkのダウンロードとセットアップ

ここではksarのforkである
[vlsi/ksar: fork of http://sourceforge.net/projects/ksar/](https://github.com/vlsi/ksar)
を使います
（[ksar : a sar grapher download | SourceForge.net](https://sourceforge.net/projects/ksar/) の UserReviews のコメントで知りました）。

[Releases · vlsi/ksar](https://github.com/vlsi/ksar/releases) から最新のリリースのAssetsから
`ksar-5.2.4-b369_g27d96e71-SNAPSHOT-all.jar` のような jar ファイルをダウンロードします。

ダウンロード後お好みのディレクトリーに移動します。
ここでは `C:\ksar` というディレクトリーを作成してそこに移動したとします。

エクスプローラーで jar ファイルを選んでポップアップメニューの[ショートカットの作成]を選びます。

作成されたショートカットをエクスプローラーで選んで名前を ksar などお好みで変更します。

そしてポップアップメニューの[プロパティ]を選んでリンク先を以下のように変更します。

```
C:\jdk-14.0.2\bin\javaw.exe -jar C:\ksar\ksar-5.2.4-b369_g27d96e71-SNAPSHOT-all.jar
```

### ksarの使い方

対象のサーバーで上記で作成された sarDD ファイルををサーバーからksarをセットアップしたPCに転送します。

上記で作成したショートカットをダブルクリックして起動します。

{{< figure src="/blog/images/2020/08/09/ksar-launched.png" title="ksar launched" >}}

ksar は Java の [Swing - Wikipedia](https://ja.wikipedia.org/wiki/Swing) という GUI ツールキットで作成されています。

内側のウィンドウの [Data]/[Load from file...] メニューを選び、ファイル選択ダイアログで上記で PC に転送してきた sarDD ファイルを選択します。

ダイアログが表示されたら [Select date format:] のドロップダウンはデフォルトの [Automatic Detection] のままで [Ok] ボタンを押します。

{{< figure src="/blog/images/2020/08/09/ksar-file-loaded.png" title="ksar file loaded" >}}

左のツリーでメトリックの種類を選ぶとグラフが表示されます。例として Swap を選んだ時のグラフを以下に示します。

{{< figure src="/blog/images/2020/08/09/ksar-swap.png" title="ksar swap" >}}

グラフ内でドラッグして矩形選択するとズームインできます。
横軸（時間軸）のみズームインしたい場合は縦方向は全体を選ぶようにします。

グラフ内でポップアップメニューを開き[ズームアップ]の[両軸]メニューなどでズームアウトできますが、[自動サイジング]/[両軸] で初期状態に戻るほうが使いやすいと思います。

## (横道) sysstat を毎秒記録する

この記事を書くにあたって改めて確認していたらsysstatを毎秒記録することも出来ることが分かったのでメモしておきます。

`/etc/cron.d/sysstat` から `/usr/lib/sysstat/` の `debian-sa1` と `sa1` （[sa1 (8)](https://manpages.ubuntu.com/manpages/focal/en/man8/sa1.8.html) 参照）を見ると `sa1` まではシェルスクリプトでそこから 
[sadc (8)](https://manpages.ubuntu.com/manpages/focal/en/man8/sadc.8.html)
を `exec ${ENDIR}/sadc -F -L ${SADC_OPTIONS} $* ${SA_DIR}` で実行しています。

`sadc` に渡される2つの数値は秒単位の interval と count となっています。

また `-D` オプションを指定すると saDD の代わりに saYYYYMMDD というファイルが作成されるようになり、上書きされずにずっと保管しておくことができるんですね。

というわけで `/etc/cron.d/sysstat` を以下のように変えて試してみることにしました。

```
# The first element of the path is a directory where the debian-sa1
# script is located
PATH=/usr/lib/sysstat:/usr/sbin:/usr/sbin:/usr/bin:/sbin:/bin

# Activity reports every second everyday
* * * * * root command -v debian-sa1 > /dev/null && debian-sa1 -D 1 60
```

元の設定ではログローテートのために23:59にも別途起動していましたが、下記の設定で出来るか試してみます。
また作成されるファイルサイズも気になるところです。後日確認して追記しようと思います。
