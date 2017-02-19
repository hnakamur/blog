Title: LXDのdnsmasqの固定IP設定をSIGHUPで更新する
Date: 2016-08-12 06:38
Category: blog
Tags: lxd,dnsmasq
Slug: 2016/08/12/update-lxd-dnsmasq-dhcp-hosts-config-with-sighup

[LXDコンテナで固定IPアドレスを使うための設定 · hnakamur's blog at github](/blog/2016/05/07/how-to-use-fixed-ip-address-for-a-lxd-container/) では `/etc/dnsmasq.conf` に直接 `dhcp-host` で設定を書いていましたが、変更するためには `lxd-bridge` の再起動が必要でした。

その後 [Ubuntu Manpage: dnsmasq - A lightweight DHCP and caching DNS server.](http://manpages.ubuntu.com/manpages/xenial/en/man8/dnsmasq.8.html) を見て `--dhcp-hostsfile=<path>` または `--dhcp-hostsdir=<path>` を使っておけば `lxd-bridge` を再起動しなくても `dnsmasq` に `SIGHUP` を送れば更新できることを知りました。 `--dhcp-hostsdir=<path>` の場合は、指定したディレクトリ以下のファイルを追加・更新する場合は SIGHUP すら不要で、ファイルを削除した後に反映するときだけ SIGHUP が必要です。

ですが、実際に試してみると `--dhcp-hostsdir` のほうは SIGHUP を送ると `duplicate dhcp-host IP address` というエラーになってしまったので (下記のハマりメモ参照)、 `--dhcp-hostsfile` のほうを使うことにしました。

## lxd-bridgeのdnsmasqで--dhcp-hostsfile を使う設定

`/var/lib/lxd-bridge/dhcp-hosts` というファイルを作って、そこを見るように切り替えてみます。

```
sudo touch /var/lib/lxd-bridge/dhcp-hosts
echo 'dhcp-hostsfile=/var/lib/lxd-bridge/dhcp-hosts' | sudo tee /etc/dnsmasq.conf > /dev/null
sudo systemctl restart lxd-bridge
```

## IPアドレスを指定して新規コンテナを作成する

例えば `web01` というコンテナを `10.155.92.201` というアドレスで作成したい場合は以下のようにします。 [Ubuntu Manpage: dnsmasq - A lightweight DHCP and caching DNS server.](http://manpages.ubuntu.com/manpages/xenial/en/man8/dnsmasq.8.html) によると `--dhcp-range` で指定した範囲の外でも良いが `--dhcp-range` と同じサブネットである必要があるとのことです。 `ps auxww | grep dnsmasq` で見たところ `/etc/default/lxd-bridge` の `LXD_IPV4_DHCP_RANGE` の値が `--dhcp-range` に使われています。

```
echo web01,10.155.92.201 | sudo tee /var/lib/lxd-bridge/dhcp-hosts > /dev/null
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
lxc launch images:centos/7/amd64 web01
```

数秒してから `lxc list` を実行すると指定したアドレスになっていることが確認できます。

なお、この例では dhcp-hosts 内のエントリが web01 の1つだけなので echo と tee で作成・更新していますが、実際の利用時には複数エントリがあるので既存のエントリを残しつつエントリを追加・更新する必要がありますのでご注意ください。

## 既存のコンテナのIPアドレスを変更する

上記で作成した `web01` というコンテナのアドレスを `10.155.92.202` に変更してみます。変更にはコンテナの再起動が必要になります。

```
echo web01,10.155.92.202 | sudo tee /var/lib/lxd-bridge/dhcp-hosts > /dev/null
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
lxc restart -f web01
```

数秒してから `lxc list` を実行すると指定したアドレスになっていることが確認できます。

この方法でIPアドレスを変更すると `/var/lib/lxd-bridge/dnsmasq.lxdbr0.leases` に変更前のアドレスが残らないので、そのアドレスをすぐに他で再利用することが出来ます。

## コンテナを削除後、同じIPアドレスを他のコンテナで使う

一方、コンテナを削除しても使っていたIPアドレスはまだ貸出中になっています。

上記の状態の後

```
lxc delete -f web01
: | sudo tee /var/lib/lxd-bridge/dhcp-hosts
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
```

としても `/var/lib/lxd-bridge/dnsmasq.lxdbr0.leases` には

```
1470963716 00:16:3e:45:a6:d1 10.155.92.202 web01 *
```

のようなエントリが残っています。
このアドレスを他のコンテナで使うためには一旦解放する必要があります。

```
sudo dhcp_release lxdbr0 10.155.92.202 00:16:3e:45:a6:d1
```

のように実行するか、あるいは [LXDのDHCPで使っていないIPアドレスを一括で解放するスクリプトを書いた · hnakamur's blog at github](/blog/2016/08/11/release-all-unused-addresses-of-lxd-bridge/) で書いたスクリプトを実行して解放します。以下では後者のスクリプトを `~/bin/lxd-bridge-release-all-unused-addresses.sh` に保存してあるものとして説明します。

IPアドレスを解放した後で

```
echo web02,10.155.92.202 | sudo tee /var/lib/lxd-bridge/dhcp-hosts > /dev/null
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
lxc launch images:centos/7/amd64 web02
```

のように実行すれば、IPアドレスを `10.155.92.202` にして `web02` というコンテナを作成・起動できました。

## --dhcp-hostsdirのハマりメモ

### lxd-bridgeのdnsmasqで--dhcp-hostsdir を使う設定

`/var/lib/lxd-bridge/dhcp-hosts` というディレクトリを作って、そこを見るように切り替えてみます。

```
[ -f /var/lib/lxd-bridge/dhcp-hosts ] && sudo rm /var/lib/lxd-bridge/dhcp-hosts
sudo mkdir -p /var/lib/lxd-bridge/dhcp-hosts
echo 'dhcp-hostsdir=/var/lib/lxd-bridge/dhcp-hosts' | sudo tee /etc/dnsmasq.conf > /dev/null
sudo systemctl restart lxd-bridge
```

### IPアドレスを指定して新規コンテナを作成する

例えば `web01` というコンテナを `10.155.92.201` というアドレスで作成したい場合は以下のようにします。

```
echo web01,10.155.92.201 | sudo tee /var/lib/lxd-bridge/dhcp-hosts/web01 > /dev/null
lxc launch images:centos/7/amd64 web01
```

数秒してから `lxc list` を実行すると指定したアドレスになっていることが確認できます。

と、ここまでは良かったのですが、

```
journalctl -f
```

でログを見ておいて、別端末で

```
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
```

と実行すると

```
Aug 12 08:39:56 lxdhostname dnsmasq-dhcp[2455]: read /var/lib/lxd-bridge/dhcp-hosts/web01
Aug 12 08:39:56 lxdhostname dnsmasq[2455]: duplicate dhcp-host IP address 10.155.92.201 at line 1 of /var/lib/lxd-bridge/dhcp-hosts/web01
```

のようなエラーが出てしまいました。 `duplicate dhcp-host IP address` から後ろは赤字で表示されました。

### コンテナを削除後、同じIPアドレスを他のコンテナで使いたいが失敗

以下では [LXDのDHCPで使っていないIPアドレスを一括で解放するスクリプトを書いた · hnakamur's blog at github](/blog/2016/08/11/release-all-unused-addresses-of-lxd-bridge/) のスクリプトを `~/bin/lxd-bridge-release-all-unused-addresses.sh` に保存してあるものとして説明します。

上記の状態の後、 `journalctl -f` を引き続き別端末で実行しておいて

```
lxc delete -f web01
sudo rm /var/lib/lxd-bridge/dhcp-hosts/web01
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
~/bin/lxd-bridge-release-all-unused-addresses.sh
echo web02,10.155.92.201 | sudo tee /var/lib/lxd-bridge/dhcp-hosts/web02 > /dev/null
```

と実行すると

```
Aug 12 08:44:13 lxdhostname dnsmasq-dhcp[2455]: read /var/lib/lxd-bridge/dhcp-hosts/web02
Aug 12 08:44:13 lxdhostname dnsmasq[2455]: duplicate dhcp-host IP address 10.155.92.201 at line 1 of /var/lib/lxd-bridge/dhcp-hosts/web02
```

と先程と同様のエラーが出ました。ここから

```
lxc launch images:centos/7/amd64 web02
```

と実行しても、指定した `10.155.92.201` とは異なるアドレスになってしまいました。

ということで `--dhcp-hostsdir=<path>` は正しい使い方がわからなかったので、諦めて `--dhcp-hostsfile=<path>` のほうを使うことにしました。
