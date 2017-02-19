Title: LXDコンテナ上でPacemakerを使って仮想IPとApacheのアクティブ・パッシブ・クラスタを試してみた
Date: 2016-08-12 18:54
Category: blog
Tags: pacemaker,virtual-ip
Slug: blog/2016/08/12/experiment-vip-and-apache-with-pacemaker-on-lxd-containers

[Cluster Labs - Pacemaker Documentation](http://clusterlabs.org/doc/) の "Pacemaker 1.1 for Corosync 2.x and pcs" の "Clusters from Scratch (en-US)" を参考にしつつ、多少手順を変更して試してみました。

## 実験用コンテナの環境構築

### コンテナの作成

[LXDのdnsmasqの固定IP設定をSIGHUPで更新する · hnakamur's blog at github](/blog/2016/08/12/update-lxd-dnsmasq-dhcp-hosts-config-with-sighup/) の手法を使って、2つのコンテナ用のIPアドレスを設定しておきます。

```
lxdhost:~$ cat /var/lib/lxd-bridge/dhcp-hosts 
pcmk-1,10.155.92.101
pcmk-2,10.155.92.102
```

また、仮想IPとして `10.155.92.100` を使用しますので、 `/var/lib/lxd-bridge/dnsmasq.lxdbr0.leases` で使われていないことを確認しておきます。

```
sudo kill -HUP `cat /var/run/lxd-bridge/dnsmasq.pid`
```

で設定を dnsmasq に反映します。

なお、  [2.1.3. Configure Network](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/ch02.html#_configure_network) の "Important" の囲み部分によるとDHCPはcorosyncと干渉するので、 **クラスタのマシンはDHCPを決して使うべきではない** そうです。この記事はあくまでPacemakerの使い方を把握するために試してみるだけなので気にしないことにしますが、実運用の際には DHCP を使わない構成にする必要があります。

以下のコマンドでコンテナ `pcmk-1` と `pcmk-2` を作成します。

```
lxdhost:~$ lxc launch images:centos/7/amd64 pcmk-1
lxdhost:~$ lxc launch images:centos/7/amd64 pcmk-2
```

### コンテナ内の /etc/hosts 設定

端末を2つ開いて `lxc exec pcmk-1 bash` と `lxc exec pcmk-2 bash` を実行し、それぞれ環境構築していきます。

まず、コンテナ作成直後の `pcmk-1` の `/etc/hosts` を確認すると以下のようになっていました。

```
127.0.0.1   localhost
127.0.1.1   pcmk-1

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
```

当初 `pcmk-1` ではIPv4の部分を

```
127.0.0.1   localhost
127.0.1.1   pcmk-1
10.155.92.102 pcmk-2
```

と変更し、 `pcmk-2` では

```
127.0.0.1   localhost
127.0.1.1   pcmk-2
10.155.92.101 pcmk-1
```

と変更してみたのですが、Pacemakerがうまく動かなかったようです（要追試）。

`pcmk-1` と `pcmk-2` で `/etc/hosts` の IPv4 部分を以下のコマンドで変更したら、うまくいったので、とりあえずこれで試しました。

```
# cat > /etc/hosts <<'EOF'
127.0.0.1   localhost

10.155.92.101   pcmk-1
10.155.92.102   pcmk-2

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF
```

### Pacemakerのインストール

`pcmk-1` と `pcmk-2` で以下のコマンドを実行します。

```
# yum -y update
# yum -y install pacemaker pcs psmisc policycoreutils-python which
```

whichは仮想IPを使うための ocf:heartbeat:IPaddr2 のリソース用の resource agent スクリプト `/usr/lib/ocf/resource.d/heartbeat/IPaddr2` で必要となります。

`pcsd` サービスを起動し、OS起動時に自動起動するようにします。

```
# systemctl start pcsd
# systemctl enable pcsd
```

## クラスタを作成して仮想IPの作成・移動実験

### クラスタの作成と開始

`hacluster` のパスワードを設定します。ここでは `password` という値にしていますが適宜変更してください。

```
# echo password | passwd --stdin hacluster
```

ここから先は `pcmk-1` だけでコマンドを実行します。 `-p` の値は上で設定したパスワードに合わせてください。

```
# pcs cluster auth pcmk-1 pcmk-2 -u hacluster -p password
# pcs cluster setup --name mycluster pcmk-1 pcmk-2
```

この時点で `/etc/corosync/corosync.conf` が作られます。

以下のコマンドでクラスタを開始します。

```
# pcs cluster start --all
```


起動してすぐにステータスを確認すると Node の行が UNCLEAN (offline) になりました。

```
[root@pcmk-1 ~]# pcs status
Cluster name: mycluster
WARNING: no stonith devices and stonith-enabled is not false
Last updated: Thu Aug 11 15:55:17 2016          Last change: Thu Aug 11 15:55:16 2016 by hacluster via crmd on pcmk-1
Stack: unknown
Current DC: NONE
2 nodes and 0 resources configured

Node pcmk-1: UNCLEAN (offline)
Node pcmk-2: UNCLEAN (offline)

Full list of resources:


PCSD Status:
  pcmk-1: Online
  pcmk-2: Online

Daemon Status:
  corosync: active/disabled
  pacemaker: active/disabled
  pcsd: active/enabled
```


しばらくしてから再度ステータスを確認すると pcmk-1 も pcmk-2 も Online になっていました。

```
# pcs status
Cluster name: mycluster
WARNING: no stonith devices and stonith-enabled is not false
Last updated: Thu Aug 11 15:56:41 2016          Last change: Thu Aug 11 15:55:37 2016 by hacluster via crmd on pcmk-2
Stack: corosync
Current DC: pcmk-2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 0 resources configured

Online: [ pcmk-1 pcmk-2 ]

Full list of resources:


PCSD Status:
  pcmk-1: Online
  pcmk-2: Online

Daemon Status:
  corosync: active/disabled
  pacemaker: active/disabled
  pcsd: active/enabled
```

### STONITHを無効化

[Chapter 5. Create an Active/Passive Cluster](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/ch05.html)の手順でクラスタの設定エラーを確認します。

```
# crm_verify -L -V
   error: unpack_resources:     Resource start-up disabled since no STONITH resources have been defined
   error: unpack_resources:     Either configure some or disable STONITH with the stonith-enabled option
   error: unpack_resources:     NOTE: Clusters with shared data need STONITH to ensure data integrity
Errors found during check: config not valid
```

ここでは簡単に Pacemaker を試すために STONITH を無効にします。無効にしたあと設定エラーを再度確認すると、今度はエラーが無くなりました。

```
# pcs property set stonith-enabled=false
# crm_verify -L -V
```

なお、 [Chapter 5. Create an Active/Passive Cluster](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/ch05.html) の最後の Warning にもある通り、 **実運用では STONITH を無効にするのは全く不適切** とのことなので、きちんと設定する必要があります。 STONITH についての説明は上記の Warning の囲み内からもリンクされている [Chapter 8. Configure STONITH](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/ch08.html#_what_is_stonith) を参照してください。

### 仮想IPアドレス用のリソース作成

`pcmk-1` で以下のコマンドを実行して、仮想IPアドレス `10.155.92.100` 用のリソースを作成します。

```
# pcs resource create ClusterIP ocf:heartbeat:IPaddr2 \
    ip=10.155.92.100 cidr_netmask=32 op monitor interval=30s
```

数秒してから状態を確認してみます。

```
# pcs status
Cluster name: mycluster
Last updated: Thu Aug 11 16:04:50 2016          Last change: Thu Aug 11 16:04:47 2016 by root via cibadmin on pcmk-1
Stack: corosync
Current DC: pcmk-2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 1 resource configured

Online: [ pcmk-1 pcmk-2 ]

Full list of resources:

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1

PCSD Status:
  pcmk-1: Online
  pcmk-2: Online

Daemon Status:
  corosync: active/disabled
  pacemaker: active/disabled
  pcsd: active/enabled
```

```
# pcs resource --full
 Resource: ClusterIP (class=ocf provider=heartbeat type=IPaddr2)
  Attributes: ip=10.155.92.100 cidr_netmask=32 
  Operations: start interval=0s timeout=20s (ClusterIP-start-interval-0s)
              stop interval=0s timeout=20s (ClusterIP-stop-interval-0s)
              monitor interval=30s (ClusterIP-monitor-interval-30s)
```

`ip` コマンドを実行して、仮想IPアドレスが `pcmk-1` 側についており `pcmk-2` 側にはついていないことを確認します。

```
[root@pcmk-1 ~]# ip a s eth0
120: eth0@if121: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP qlen 1000
    link/ether 00:16:3e:e6:fb:ab brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 10.155.92.101/24 brd 10.155.92.255 scope global dynamic eth0
       valid_lft 3203sec preferred_lft 3203sec
    inet 10.155.92.100/32 brd 10.155.92.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::216:3eff:fee6:fbab/64 scope link 
       valid_lft forever preferred_lft forever
```

```
[root@pcmk-2 ~]# ip a s eth0
122: eth0@if123: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP qlen 1000
    link/ether 00:16:3e:4b:6d:b1 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 10.155.92.102/24 brd 10.155.92.255 scope global dynamic eth0
       valid_lft 3560sec preferred_lft 3560sec
    inet6 fe80::216:3eff:fe4b:6db1/64 scope link 
       valid_lft forever preferred_lft forever
```

### `pcmk-1` をクラスタから離脱させて仮想IPアドレスが `pcmk-2` に移動するか確認

以下のコマンドで `pcmk-1` をクラスタから離脱させます。

```
[root@pcmk-1 ~]# pcs cluster stop pcmk-1
pcmk-1: Stopping Cluster (pacemaker)...
pcmk-1: Stopping Cluster (corosync)...
```

`pcmk-1` で状態を確認すると以下のようになります。

```
[root@pcmk-1 ~]# pcs status
Error: cluster is not currently running on this node
```


`pcmk-2` で状態を確認すると以下のようになります。 `pcmk-1` は `OFFLINE` となっていますが、 `pcsd` は動いているので `PCSD Status` のほうは `Online` のままです。

```
[root@pcmk-2 ~]# pcs status
Cluster name: mycluster
Last updated: Thu Aug 11 16:10:04 2016          Last change: Thu Aug 11 16:04:47 2016 by root via cibadmin on pcmk-1
Stack: corosync
Current DC: pcmk-2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 1 resource configured

Online: [ pcmk-2 ]
OFFLINE: [ pcmk-1 ]

Full list of resources:

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2

PCSD Status:
  pcmk-1: Online
  pcmk-2: Online

Daemon Status:
  corosync: active/disabled
  pacemaker: active/disabled
  pcsd: active/enabled
```

`ip` コマンドを実行して、仮想IPアドレスが `pcmk-2` 側についており `pcmk-1` 側にはついていないことを確認します。

```
[root@pcmk-1 ~]# ip a s eth0
120: eth0@if121: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP qlen 1000
    link/ether 00:16:3e:e6:fb:ab brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 10.155.92.101/24 brd 10.155.92.255 scope global dynamic eth0
       valid_lft 3024sec preferred_lft 3024sec
    inet6 fe80::216:3eff:fee6:fbab/64 scope link 
       valid_lft forever preferred_lft forever
```

```
[root@pcmk-2 ~]# ip a s eth0
122: eth0@if123: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP qlen 1000
    link/ether 00:16:3e:4b:6d:b1 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 10.155.92.102/24 brd 10.155.92.255 scope global dynamic eth0
       valid_lft 3385sec preferred_lft 3385sec
    inet 10.155.92.100/32 brd 10.155.92.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::216:3eff:fe4b:6db1/64 scope link 
       valid_lft forever preferred_lft forever
```

### `pcmk-1` をクラスタに復帰させる

以下のコマンドで `pcmk-1` をクラスタに復帰させます。

```
[root@pcmk-1 ~]# pcs cluster start pcmk-1
pcmk-1: Starting Cluster...
```

状態を確認してみると、仮想IP は `pcmk-2` のほうについたままです。
[5.3. Perform a Failover](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/_perform_a_failover.html) の最後の Note によると Pacemakerのより古いバージョンでは `pcmk-1` のほうに切り替わっていたそうですが、挙動が変更されたとのことです。

```
[root@pcmk-1 ~]# pcs status
Cluster name: mycluster
Last updated: Thu Aug 11 16:12:35 2016          Last change: Thu Aug 11 16:04:47 2016 by root via cibadmin on pcmk-1
Stack: corosync
Current DC: pcmk-2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 1 resource configured

Online: [ pcmk-1 pcmk-2 ]

Full list of resources:

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2

PCSD Status:
  pcmk-1: Online
  pcmk-2: Online

Daemon Status:
  corosync: active/disabled
  pacemaker: active/disabled
  pcsd: active/enabled
```

以下のコマンドを実行して、仮想IPを `pcmk-1` のほうに移動します。

```
pcs cluster stop pcmk-2 && pcs cluster start pcmk-2
```

## ApacheのActive/Passiveクラスタを作って仮想IPと連動させる

### リソースのスティッキネスのデフォルト値を設定

[5.4. Prevent Resources from Moving after Recovery](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/_prevent_resources_from_moving_after_recovery.html) を見て設定します。

```
[root@pcmk-1 ~]# pcs resource defaults resource-stickiness=100
[root@pcmk-1 ~]# pcs resource defaults 
resource-stickiness: 100
```

### Apache のインストールと設定

`pcmk-1` と `pcmk-2` で以下のコマンドを実行します。

```
# yum -y install httpd wget
# mkdir -p /var/www/html /var/log/httpd
# cat > /var/www/html/index.html <<EOF
<html>
<body>My Test Site - $(hostname)</body>
</html>
EOF
# cat > /etc/httpd/conf.d/status.conf <<'EOF'
<Location /server-status>
  SetHandler server-status
  Require ip 127.0.0.1
</Location>
EOF
```

### Apache の Active/Passive クラスタ作成

`pcmk-1` か `pcmk-2` のどちらか一方で以下のコマンドを実行します。
公式のドキュメントでは、 `pcmk-2` で開始した後、制約を追加しただけでは `pcmk-1` に移動しないというデモをしていますが、ここでは `--disabled` つきでリソースを作成後、制約を追加してから有効化することで最初から `pcmk-1` で開始させています。

また、制約を追加するごとに `crm_simulate -sL` を実行してリソースをどのノードに割り当てるかのスコアを確認しています。

まず WebSite という名前のリソースを `disabled` 状態で作成します。

```
# pcs resource create WebSite ocf:heartbeat:apache \
    configfile=/etc/httpd/conf/httpd.conf \
    statusurl="http://localhost/server-status" \
    op monitor interval=3s on-fail=restart \
    --disabled
```

WebSite リソースは ClusterIP リソースと同じノードで動かすという制約を追加します。

```
# pcs constraint colocation add WebSite with ClusterIP INFINITY
# crm_simulate -sL

Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        (target-role:Stopped) Stopped

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 100
native_color: ClusterIP allocation score on pcmk-2: 0
native_color: WebSite allocation score on pcmk-1: -INFINITY
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
```

リソースの開始順序を ClusterIP、 WebSite にする制約を追加します。

```
# pcs constraint order ClusterIP then WebSite
```

WebSite のリソースをなるべく `pcmk-1` 側で動かすようにする制約を追加します。 `250` という値はこの後の操作を一度試行錯誤してみて適当に選びましたが、希望通りの動作が実現できさえすれば違う値でも構いません。

```
# pcs constraint location WebSite prefers pcmk-1=250
# crm_simulate -sL

Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        (target-role:Stopped) Stopped

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 350
native_color: ClusterIP allocation score on pcmk-2: 0
native_color: WebSite allocation score on pcmk-1: -INFINITY
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
```

希望する制約を一通り追加したので、 WebSite リソースを稼働開始します。

```
# pcs resource enable WebSite
# crm_simulate -sL

Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        Started pcmk-1

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 450
native_color: ClusterIP allocation score on pcmk-2: 0
native_color: WebSite allocation score on pcmk-1: 350
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
```

`pcmk-1` と `pcmk-2` で `ps auxww | grep httpd` すると `pcmk-1` 側で Apache が稼働して `pcmk-2` 側では稼働していないことを確認できます。

### 手動で制約を調整して仮想IPとApacheを `pcmk-2` に移動する

以下のコマンドで制約を調整し、移動が完了するまでのスコアの変遷を確認します。 `500` という値は前項の最後の `pcmk-1` の ClusterIP のスコアを上回る値として選びました。

```
# pcs constraint location WebSite prefers pcmk-2=500 \
  && for i in `seq 1 20`; do crm_simulate -sL; sleep 0.1; done
```

出力結果のうち変化があったものだけを抜粋します。
まず開始直後の状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        Started pcmk-1

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 450
native_color: ClusterIP allocation score on pcmk-2: 500
native_color: WebSite allocation score on pcmk-1: -INFINITY
native_color: WebSite allocation score on pcmk-2: 500

Transition Summary:
 * Move    ClusterIP    (Started pcmk-1 -> pcmk-2)
 * Move    WebSite      (Started pcmk-1 -> pcmk-2)
```

WebSiteが停止した状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        Stopped

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 350
native_color: ClusterIP allocation score on pcmk-2: 500
native_color: WebSite allocation score on pcmk-1: -INFINITY
native_color: WebSite allocation score on pcmk-2: 500

Transition Summary:
 * Move    ClusterIP    (Started pcmk-1 -> pcmk-2)
 * Start   WebSite      (pcmk-2)
```

ClusterIPがpcmk-2に移った状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2
 WebSite        (ocf::heartbeat:apache):        Stopped

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 250
native_color: ClusterIP allocation score on pcmk-2: 600
native_color: WebSite allocation score on pcmk-1: -INFINITY
native_color: WebSite allocation score on pcmk-2: 500

Transition Summary:
 * Start   WebSite      (pcmk-2)
```

WebSiteが `pcmk-2` で稼働開始した状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2
 WebSite        (ocf::heartbeat:apache):        Started pcmk-2

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 250
native_color: ClusterIP allocation score on pcmk-2: 700
native_color: WebSite allocation score on pcmk-1: -INFINITY
native_color: WebSite allocation score on pcmk-2: 600

Transition Summary:
```

### 手動で制約を調整して仮想IPとApacheを `pcmk-1` に戻す

次に `pcmk-2` から `pcmk-1` に戻してみます。
以下のコマンドで制約のIDを確認します。

```
[root@pcmk-1 ~]# pcs constraint --full
Location Constraints:
  Resource: WebSite
    Enabled on: pcmk-1 (score:250) (id:location-WebSite-pcmk-1-250)
    Enabled on: pcmk-2 (score:500) (id:location-WebSite-pcmk-2-500)
Ordering Constraints:
  start ClusterIP then start WebSite (kind:Mandatory) (id:order-ClusterIP-WebSite-mandatory)
Colocation Constraints:
  WebSite with ClusterIP (score:INFINITY) (id:colocation-WebSite-ClusterIP-INFINITY)
```

以下のコマンドで `pcmk-2` 側の制約を削除し、 `pcmk-1` 側に戻るまでのスコアの動きを確認します。

```
# pcs constraint remove location-WebSite-pcmk-2-500 \
  && for i in `seq 1 20`; do crm_simulate -sL; sleep 0.1; done
```

開始直後の状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2
 WebSite        (ocf::heartbeat:apache):        Started pcmk-2

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 250
native_color: ClusterIP allocation score on pcmk-2: 200
native_color: WebSite allocation score on pcmk-1: 250
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
 * Move    ClusterIP    (Started pcmk-2 -> pcmk-1)
 * Move    WebSite      (Started pcmk-2 -> pcmk-1)
```

WebSiteが停止した状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2
 WebSite        (ocf::heartbeat:apache):        Stopped

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 250
native_color: ClusterIP allocation score on pcmk-2: 100
native_color: WebSite allocation score on pcmk-1: 250
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
 * Move    ClusterIP    (Started pcmk-2 -> pcmk-1)
 * Start   WebSite      (pcmk-1)
```

ClusterIPが `pcmk-1` に移動した状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        Stopped

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 350
native_color: ClusterIP allocation score on pcmk-2: 0
native_color: WebSite allocation score on pcmk-1: 250
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
 * Start   WebSite      (pcmk-1)
```

WebSiteが `pcmk-1` で稼働開始した状態。

```
Current cluster status:
Online: [ pcmk-1 pcmk-2 ]

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-1
 WebSite        (ocf::heartbeat:apache):        Started pcmk-1

Allocation scores:
native_color: ClusterIP allocation score on pcmk-1: 450
native_color: ClusterIP allocation score on pcmk-2: 0
native_color: WebSite allocation score on pcmk-1: 350
native_color: WebSite allocation score on pcmk-2: -INFINITY

Transition Summary:
```

## Active側のコンテナに障害が発生してコンテナごと落ちるケースの模擬実験

### Active側 `pcmk-1` のコンテナを停止させたときの挙動を確認

LXDホストで以下のコマンドを実行して `pcmk-1` を停止させます。

```
$ lxc stop -f pcmk-1
```

`pcmk-2` で `pcs status` を実行すると `pcmk-1` が OFFLINE になったことがわかりますが、 `PCSD Status:` の後を表示するところでブロックしたので Ctrl-C で止めました。

```
[root@pcmk-2 ~]# pcs status
Cluster name: mycluster
Last updated: Fri Aug 12 13:13:37 2016          Last change: Fri Aug 12 09:34:39 2016 by root via cibadmin on pcmk-1
Stack: corosync
Current DC: pcmk-2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 2 resources configured

Online: [ pcmk-2 ]
OFFLINE: [ pcmk-1 ]

Full list of resources:

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2
 WebSite        (ocf::heartbeat:apache):        Started pcmk-2

PCSD Status:
^C
```

`ip a s eth0` と `ps auxww | grep httpd` で仮想IPとApacheが `pcmk-2` で動いていることが確認できました。


### `pcmk-1` のコンテナを起動させた時の挙動を確認

LXDホストで以下のコマンドを実行して `pcmk-1` を起動し、コンテナ内に入ります。

```
$ lxc satrt pcmk-1
$ lxc exec pcmk-1 bash
```

`pcmk-1` 側は `pcsd` は起動していますが、クラスタには所属していない状態です。

理由は [Chapter 4. Start and Verify Cluster](http://clusterlabs.org/doc/en-US/Pacemaker/1.1-pcs/html/Clusters_from_Scratch/ch04.html#_start_the_cluster) に説明があります。 `pcsd` は `systemctl enable` でOS起動時の自動起動を有効にしていますが `corosync` と `pacemaker` はしていないからです。

実運用時に物理的な障害などで `pcmk-1` がクラスタから外れた場合、その後電源をいれて起動できたとしても、障害の原因を調査して、正常にサービスを稼働できるかを確認してからクラスタに復帰させたいので、この設定で良いと思います。

```
[root@pcmk-1 ~]# pcs status
Error: cluster is not currently running on this node
```

`pcmk-2` で `pcs status` は今度はブロックせずに完了します。

```
[root@pcmk-2 ~]# pcs status
Cluster name: mycluster
Last updated: Fri Aug 12 13:18:22 2016          Last change: Fri Aug 12 09:34:39 2016 by root via cibadmin on pcmk-1
Stack: corosync
Current DC: pcmk-2 (version 1.1.13-10.el7_2.4-44eb2dd) - partition with quorum
2 nodes and 2 resources configured

Online: [ pcmk-2 ]
OFFLINE: [ pcmk-1 ]

Full list of resources:

 ClusterIP      (ocf::heartbeat:IPaddr2):       Started pcmk-2
 WebSite        (ocf::heartbeat:apache):        Started pcmk-2

PCSD Status:
  pcmk-1: Online
  pcmk-2: Online

Daemon Status:
  corosync: active/disabled
  pacemaker: active/disabled
  pcsd: active/enabled
```

以下のコマンドを実行して `pcmk-1` をクラスタに復帰させます。

```
[root@pcmk-1 ~]# pcs cluster start pcmk-1
pcmk-1: Starting Cluster...
```

しばらくして `pcs status` を確認すると `pcmk-1` がオンラインになり、 ClusterIP と WebSite リソースが `pcmk-1` に移動することが確認できました。
