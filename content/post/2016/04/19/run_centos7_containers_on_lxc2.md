Title: LXC 2.0でCentOS 7のコンテナを動かしてみた
Date: 2016-04-19 06:37
Category: blog
Tags: lxc
Slug: 2016/04/19/run_centos7_containers_on_lxc2


## はじめに
### なぜDockerではなくLXCを使うのか

コンテナと言えばDockerが有名です。Docker 1.9からネットワーク機能が大幅に良くなっていて、Docker Composeでコンテナを作成するとコンテナ名で名前解決できるようになっています。

また公式のCentOS 7コンテナも良くなっていて、Dockerfileに `CMD ["/bin/init"]` と書いておけば普通に systemd が起動するようになっています。

そして `docker run` に `--privileged` オプションを付けて実行すれば実行時に `/etc/` などの下のファイルを書き換えることも出来ます。

しかしこのような使い方は[Best practices for writing Dockerfiles](https://docs.docker.com/engine/userguide/eng-image/dockerfile_best-practices/)と全く合いません。Dockerのベストプラクティスでは1コンテナ1プロセス、コンテナは最小限で使い捨て、ログやデータはコンテナ外部に保存するというスタンスなのです。

一方、本番環境でDockerを使わずAnsibleでプロビジョニングする前提であれば、開発環境もAnsibleでプロビジョニングしたいところです。サーバが1台ならVagrant + VirtualBoxで良いのですが、複数台となると仮想マシンではメモリがたくさん必要になりますのでコンテナを使いたいところです。LXCなら従来のLinuxサーバと同じ感覚で利用できます。

### 2016-05-07 追記

[Ubuntu 16.04 LTSでLXD 2.0を試してみた](http://hnakamur.github.io/blog/2016/05/07/tried-lxd-2.0-on-ubuntu-16.04/)を書きました。試してみて思ったのは、今から使うならLXC 2.0よりもLXD 2.0のほうが良いということです。この記事よりもこちらをお勧めします。

### Ubuntu 14.04/16.04でLXC 2.0を使う

LXCもコンテナなのでLinuxカーネルはホストとコンテナで同じものが使われます。CentOS 7単独の環境に近づけるにはホストもCentOS 7にしたいところです。が、現時点ではCentOS 7ではLXCはepelにバージョン1.0.8があるだけです。

LXCはCanonical LtdがUbuntu上で開発しているので、Ubuntu上で使うほうがトラブルは少なくて済むと予想します。ということで、LinuxカーネルのバージョンがCentOS 7と違ってしまうというデメリットはあるのですが、ホストはUbuntuを使うことにします。

Ubuntu 14.04のカーネルのほうがCentOS 7のカーネルより新しいので、アプリケーション開発に使う分にはLinuxカーネルのバージョン違いで影響が出ることはほぼ無いと思います。

2016-04-06にLXC 2.0がリリースされました。[Linux Containers - LXC - ニュース](https://linuxcontainers.org/ja/lxc/news/)

これは長期サポート(Long-term support; LTS) リリースです。ということで、今から使うなら2.0が良いと思います。


## LXCのセットアップ

セットアップ用のスクリプトとVagrantfileを書きました。
[hnakamur/setup_lxc_on_vagrant: Vagrantfile to set up LXC 2.x on Ubuntu 14.04 or 16.04](https://github.com/hnakamur/setup_lxc_on_vagrant)

これを使うと以下の手順でセットアップ出来ます。

```
cp Vagrantfile.ubuntu1404 Vagrantfile
vagrant up && vagrant reload
```

セットアップした後ネットワークの再起動が必要なので `vagrant up` に加えて `vagrant reload` を実行しています。

セットアップは[setup_lxc.sh](https://github.com/hnakamur/setup_lxc_on_vagrant/blob/master/setup_lxc.sh)というシェルスクリプトになっているので設定内容が気になる方はこちらを参照してください。Vagrantを使わないUbuntu 14.04/16.04環境でもこのスクリプトを実行すればLXCをセットアップできます。

Vagrantの仮想マシンの再起動が終わったら

```
vagrant ssh
```

で仮想マシンに入ってLXCを使います。

## コンテナ作成

例えばweb01という名前のCentOS 7コンテナを作成するには以下のようにします。

```
sudo lxc-create -n web01 -t download -- -d centos -r 7 -a amd64
```

`-t` はテンプレートを指定するオプションです。centosというテンプレートもあるのですが、それを使うとコンテナの挙動に問題があった (これについては今後別記事で書く予定です) ので、downloadテンプレートを使っています。

初回はコンテナのイメージファイルをダウンロードするので時間がかかります。イメージファイルのサイズは約60MBとそれほど大きくもないのですが、私の環境では20分程度かかる場合もありました。

## コンテナ起動

web01というコンテナを起動するには以下のコマンドを実行します。

```
sudo lxc-start -n web01
```

## コンテナ一覧表示

以下のコマンドを実行します。

```
sudo lxc-ls -f
```

出力例はこんな感じになります。

```
vagrant@vagrant-ubuntu-trusty-64:~$ sudo lxc-ls -f
NAME    STATE   AUTOSTART GROUPS IPV4       IPV6
web01   RUNNING 0         -      10.0.3.244  -
```

起動直後に実行するとIPv4の列が-になっています。数秒立ってから再度実行するとIPアドレスがDHCPで設定されて表示されます。

### コンテナ名でDNSを引けるか確認

```
vagrant@vagrant-ubuntu-trusty-64:~$ dig +short web01
10.0.3.244
```

なお、LXCのdnsmasqで引けるようにするために[LXCコンテナに名前でアクセスする方法 - ククログ(2014-07-30)](http://www.clear-code.com/blog/2014/7/30.html#.2Fetc.2Fresolve.conf.E3.81.ABnameserver.E3.82.92.E8.BF.BD.E5.8A.A0.E3.81.99.E3.82.8B)を参考に https://github.com/hnakamur/setup_lxc_on_vagrant/blob/8dac97e2c0dafe3bad275f733a549f7b03477cb4/setup_lxc.sh#L40-L43 で設定しています。情報共有ありがとうございます！


## コンテナ内に入る

web01というコンテナ内に入るには以下のコマンドを実行します。

```
sudo lxc-attach -n web01
```

コンテナ内でシェルのプロンプトが表示されますので、好きなコマンドを実行してください。 `exit` で抜けます。実行例を以下に示します。

```
vagrant@vagrant-ubuntu-trusty-64:~$ sudo lxc-attach -n web01
bash-4.2# ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
9: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether fe:74:45:50:85:27 brd ff:ff:ff:ff:ff:ff
    inet 10.0.3.11/24 brd 10.0.3.255 scope global dynamic eth0
       valid_lft 3219sec preferred_lft 3219sec
    inet6 fe80::fc74:45ff:fe50:8527/64 scope link
       valid_lft forever preferred_lft forever
bash-4.2# exitvagrant@vagrant-ubuntu-trusty-64:~$
```

↑exitの後returnキーを押しても改行されませんでした。

## コンテナを停止する

以下のようにして停止します。

```
$ sudo lxc-stop -n web01
vagrant@vagrant-ubuntu-trusty-64:~$ sudo lxc-ls -f
NAME    STATE   AUTOSTART GROUPS IPV4       IPV6
web01   STOPPED 0         -      -          -
```

### lxc-stopですぐに停止するには以下の設定が必要

downloadテンプレートで作成したCentOS 7コンテナはそのままだと、lxc-stopで停止するのに1分間待たされます。

[\[lxc-users\] lxc-stop doesn't stop centos, waits for the timeout](https://lists.linuxcontainers.org/pipermail/lxc-users/2014-February/006304.html)を参考に、コンテナ内で

```
ln -s /usr/lib/systemd/system/halt.target /etc/systemd/system/sigpwr.target
```

を実行すれば、lxc-stopですぐに停止できました。


## コンテナを削除する

```
vagrant@vagrant-ubuntu-trusty-64:~$ sudo lxc-destroy -n web01
Destroyed container web01
vagrant@vagrant-ubuntu-trusty-64:~$ sudo lxc-ls -f
vagrant@vagrant-ubuntu-trusty-64:~$
```

### ホストでLXCサービス起動時にコンテナを自動起動する

`/var/lib/lxc/${コンテナ名}/config` ファイルに以下の行を追加します。

```
lxc.start.auto = 1
```

複数コンテナ間の依存関係を指定して起動の順序を制御するなど高度な指定については加藤泰文さんの[第25回　LXCの構築・活用 \[11\] ─lxc-autostartコマンドによるコンテナの自動起動：LXCで学ぶコンテナ入門 －軽量仮想化環境を実現する技術｜gihyo.jp … 技術評論社](http://gihyo.jp/admin/serial/01/linux_containers/0025?page=1)の記事をご参照ください。私は複雑な指定は試してないです。

## おわりに

Ubuntu 14.04上でLXC 2.0をセットアップして使う手順についてまとめました。

コンテナの作成とプロビジョニングについてはAnsible playbookのサンプルも作ったので今後別記事で書く予定です。また、この記事では触れなかったハマりネタもいくつかあったのでそれも今度書こうと思います。
