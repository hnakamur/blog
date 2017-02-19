Title: xhyveでFreeBSDを動かしてみた
Date: 2015-07-12 06:34
Category: blog
Tags: xhyve, freebsd
Slug: blog/2015/07/12/running_freebsd_on_xhyve

下記の記事を参考に動かしただけですが、後々使うときに手順を忘れているはずなのでメモ。

* [xhyve で FreeBSD を動かしてみた - blog.holidayworking.org](http://blog.holidayworking.org/entry/2015/06/27/xhyve_%E3%81%A7_FreeBSD_%E3%82%92%E5%8B%95%E3%81%8B%E3%81%97%E3%81%A6%E3%81%BF%E3%81%9F)
* [FreeBSD on xhyve でディスクをマウントすることができた - blog.holidayworking.org](http://blog.holidayworking.org/entry/2015/07/05/FreeBSD_on_xhyve_%E3%81%A7%E3%83%87%E3%82%A3%E3%82%B9%E3%82%AF%E3%82%92%E3%83%9E%E3%82%A6%E3%83%B3%E3%83%88%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%9F)

なお、FreeBSD対応のプルリクエストは既に本家のmasterにマージ済みです。
また、今回使ったスクリプトは [hnakamur/xhyveのadd_scripts_for_freebsdブランチ](https://github.com/hnakamur/xhyve/tree/add_scripts_for_freebsd) に上げています。

## FreeBSDのVMイメージダウンロードと解凍

```
./download_freebsd_image.sh
```

FreeBSD-10.1-RELEASE-amd64.raw.xzを取得、解凍します。解凍後のファイルサイズは約21GBです。


## FreeBSDのVM起動

ネットワークを使うためには `./xhyverun-freebsd.sh` の `NET="-s 2:0,virtio-net"` の行を有効にする必要がありました。これを有効にすると起動には `sudo` が必要でしたので、VM起動は以下のように実行します。

```
sudo ./xhyverun-freebsd.sh
```

起動したら、IDはroot、パスワード無しでログインできます。

## ネットワークの設定

初回起動時は手動でDHCPクライアントを実行してIPアドレスを取得します。

```
dhclient vtnet0
```

完了後 `ifconfig` で確認すると 192.168.64.10 というIPアドレスが取得できていました。

```
root@:~ # ifconfig
vtnet0: flags=8943<UP,BROADCAST,RUNNING,PROMISC,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=80028<VLAN_MTU,JUMBO_MTU,LINKSTATE>
        ether 6a:c9:2c:45:cf:32
        inet 192.168.64.10 netmask 0xffffff00 broadcast 192.168.64.255
        nd6 options=29<PERFORMNUD,IFDISABLED,AUTO_LINKLOCAL>
        media: Ethernet 10Gbase-T <full-duplex>
        status: active
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> metric 0 mtu 16384
        options=600003<RXCSUM,TXCSUM,RXCSUM_IPV6,TXCSUM_IPV6>
        inet6 ::1 prefixlen 128
        inet6 fe80::1%lo0 prefixlen 64 scopeid 0x2
        inet 127.0.0.1 netmask 0xff000000
        nd6 options=21<PERFORMNUD,AUTO_LINKLOCAL>
```

次回以降の起動時に自動的にDHCPクライアントを実行するために、以下のコマンドを実行します。 `/etc/rc.conf` は存在していないので `>>` ではなく `>` でも良いですが、良い習慣付けとして `>>` にしておきます。

```
echo ifconfig_vtnet0="DHCP" >> /etc/rc.conf
```

## FreeBSDのVM停止

VM内で以下のコマンドを実行するとVMをシャットダウンしてホストOSであるOSXのシェルプロンプトに戻ります。

```
shutdown -p now
```

