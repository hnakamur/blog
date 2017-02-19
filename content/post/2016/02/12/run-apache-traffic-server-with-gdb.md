Title: Apache Traffic Server を GDB で動かす
Date: 2016-02-12 00:02
Category: blog
Tags: apache-traffic-server, gdb
Slug: blog/2016/02/12/run-apache-traffic-server-with-gdb

## はじめに

[WEB+DB PRESS Vol.69｜技術評論社](http://gihyo.jp/magazine/wdpress/archive/2012/vol69) にあった [アリエル・ネットワーク㈱の井上さん](http://dev.ariel-networks.com/wp/archives/author/inoue)による「大規模コードリーディング」の特集を読んで、静的解析 (コードを読んで理解する手法) と動的解析 (実行時の動作を予測しながら構造を理解する方法) を行ったり来たり繰り返すのが良いと理解しました。

というわけで、 [Apache Traffic Server のコードリーディング · hnakamur's blog at github](/blog/2016/02/11/apache-traffic-server-code-reading/) でコードを読みつつ、デバッガ上で動かしてみました。手順は整理してないですが、とりあえず自分向けメモです。

## 試した環境

試した環境は [hnakamur/trafficserver-ansible-playbook](https://github.com/hnakamur/trafficserver-ansible-playbook) で構築したものです。Apache Traffic Server のバージョンは 6.1.1 です。

## 事前準備

### debuginfo パッケージのインストール

gdb でプログラムを実行するにはプログラムのパッケージと依存パッケージの debuginfo が必要です。これは、たぶん以下のコマンドでインストールできます。

```
sudo yum install -y yum-utils
sudo debuginfo-install -y trafficserver
```

### debuginfo パッケージのインストールの試行錯誤メモ

この項は上のコマンドを知る前に試した手順のメモです。

まずデバッグ情報のパッケージが必要だと思ったので、以下のコマンドでインストールしました。

```
sudo yum install -y trafficserver-debuginfo
```

次に

```
systemctl start trafficserver
```

を実行して trafficserver のサービスを起動した状態で

```
ps auxww | grep traffic
```

を実行して `traffic_server` のコマンドラインをメモします。

```
/usr/bin/traffic_server -M --bind_stdout /var/log/trafficserver/traffic.out --bind_stderr /var/log/trafficserver/traffic.out --httpport 80:fd=9
```

となっていました。 [traffic_server — Apache Traffic Server 6.2.0 documentation](https://docs.trafficserver.apache.org/en/latest/appendices/command-line/traffic_server.en.html) を見ると `-M` は `--remote_management` のショートオプションです。 `systemctl start trafficserver` でサービスを起動すると `traffic_cop` と `traffic_manager` 経由で `traffic_server` が起動するのですが、その場合に必要になるオプションのようです。 gdb で実行するときは `-M` は外します。

```
systemctl stop trafficserver
```

でサービスを停止します。


```
gdb /usr/bin/traffic_server
```

で gdb を起動します。

```
break HttpSM::set_next_state
```

などとブレークポイントを設定します。ブレークポイントは Apache Traffic Server のソースコードを読んで、自分が止めたい場所にお好みで設定します。

gdb のプロンプトで以下のように入力して、 Apache Traffic Server を実行します。

```
run --bind_stdout /var/log/trafficserver/traffic.out --bind_stderr /var/log/trafficserver/traffic.out --httpport 80:fd=9
```

ところがdebuginfoが足りず、以下のようなエラーになってしまいました。

```
[Inferior 1 (process 17590) exited with code 01]
Missing separate debuginfos, use: debuginfo-install glibc-2.17-106.el7_2.1.x86_64 hwloc-libs-1.7-5.el7.x86_64 keyutils-libs-1.5.8-3.el7.x86_64 krb5-libs-1.13.2-10.el7.x86_64 libcom_err-1.42.9-7.el7.x86_64 libgcc-4.8.5-4.el7.x86_64 libpciaccess-0.13.4-2.el7.x86_64 libselinux-2.2.2-6.el7.x86_64 libstdc++-4.8.5-4.el7.x86_64 libxml2-2.9.1-6.el7_2.2.x86_64 nss-softokn-freebl-3.16.2.3-13.el7_1.x86_64 numactl-libs-2.0.9-5.el7_1.x86_64 openssl-libs-1.0.1e-51.el7_2.2.x86_64 pcre-8.32-15.el7.x86_64 tcl-8.5.13-8.el7.x86_64 xz-libs-5.1.2-12alpha.el7.x86_64 zlib-1.2.7-15.el7.x86_64
```

`use:` の後をコピペして実行して途中で (y/n) で聞かれたら y を押すと、必要な debuginfo をイントール出来ました。

調べてみると、最初から以下のコマンドを実行しておけば依存するライブラリの debuginfo もインストールできるようです。

```
sudo debuginfo-install -y trafficserver
```

なお、 `debuginfo-install` コマンドは `yum-utils` パッケージに入っているので予めインストールしておきます。

## 実行例

まず、

```
gdb /usr/bin/traffic_server
```

で gdb を起動し `HttpSM::set_next_state` にブレークポイントを設定して traffic_server を実行しました。

```
[root@localhost ~]# gdb /usr/bin/traffic_server
GNU gdb (GDB) Red Hat Enterprise Linux 7.6.1-80.el7
Copyright (C) 2013 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.  Type "show copying"
and "show warranty" for details.
This GDB was configured as "x86_64-redhat-linux-gnu".
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>...
Reading symbols from /usr/bin/traffic_server...Reading symbols from /usr/lib/debug/usr/bin/traffic_server.debug...done.
done.
(gdb) break HttpSM::set_next_state
Breakpoint 1 at 0x151510: file HttpSM.cc, line 6940.
(gdb) run --bind_stdout /var/log/trafficserver/traffic.out --bind_stderr /var/log/trafficserver/traffic.out --httpport 80:fd=9
Starting program: /usr/bin/traffic_server --bind_stdout /var/log/trafficserver/traffic.out --bind_stderr /var/log/trafficserver/traffic.out --httpport 80:fd=9
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".
traffic_server: using root directory '/usr'
[New Thread 0x7ffff3bde700 (LWP 19929)]
[New Thread 0x7ffff1249700 (LWP 19930)]
[New Thread 0x7ffff1047700 (LWP 19931)]
[New Thread 0x7ffff0a3c700 (LWP 19932)]
[New Thread 0x7fffebefe700 (LWP 19933)]
[New Thread 0x7fffebcfc700 (LWP 19934)]
[New Thread 0x7fffebafa700 (LWP 19935)]
[New Thread 0x7fffeb8f8700 (LWP 19936)]
[New Thread 0x7fffeb6f6700 (LWP 19937)]
[New Thread 0x7fffeb4f4700 (LWP 19938)]
[New Thread 0x7fffeb2f2700 (LWP 19939)]
[New Thread 0x7fffeb0f0700 (LWP 19940)]
[New Thread 0x7fffeac5d700 (LWP 19941)]
[New Thread 0x7fffea95a700 (LWP 19942)]
[New Thread 0x7fffea859700 (LWP 19943)]
[New Thread 0x7fffea657700 (LWP 19944)]
```

ここで別の端末で

```
curl -sv http://192.168.33.131/
```

を実行しました。

`HttpSM` というクラス名は `Http State Machine` の略と思われます。 HTTP を処理する状態遷移マシンになっています。以下のセッションでは HttpSM クラスの t_state メンバ変数の next_action を表示して、状態の遷移を確認してみました。

```
Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) where
#0  HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
#1  0x000055555569aa96 in HttpSM::state_read_client_request_header (this=0x7fffea0d0080, event=<optimized out>, data=<optimized out>)
    at HttpSM.cc:771
#2  0x00005555556a7600 in HttpSM::main_handler (this=0x7fffea0d0080, event=100, data=0x7fffe0017e38) at HttpSM.cc:2561
#3  0x00005555556a0f13 in HttpSM::state_api_callout (this=0x7fffea0d0080, event=<optimized out>, data=<optimized out>)
    at HttpSM.cc:1464
#4  0x00005555556a19a8 in do_api_callout (this=0x7fffea0d0080) at HttpSM.cc:391
#5  HttpSM::state_add_to_list (this=0x7fffea0d0080, event=<optimized out>) at HttpSM.cc:418
#6  0x00005555556a719b in HttpSM::attach_client_session (this=0x7fffea0d0080, client_vc=0x555556592d40, buffer_reader=0x555556575ea8)
    at HttpSM.cc:544
#7  0x0000555555682ec5 in HttpClientSession::new_transaction (this=0x555556592d40) at HttpClientSession.cc:141
#8  0x000055555565e901 in ProxyClientSession::state_api_callout (this=0x555556592d40, event=<optimized out>)
    at ProxyClientSession.cc:123
#9  0x00005555556824b2 in HttpClientSession::new_connection (this=0x555556592d40, new_vc=<optimized out>, iobuf=<optimized out>,
    reader=<optimized out>, backdoor=<optimized out>) at HttpClientSession.cc:220
#10 0x000055555567d969 in HttpSessionAccept::accept (this=0x55555621cab0, netvc=0x7fffe0017d20, iobuf=<optimized out>,
    reader=0x555556575ea8) at HttpSessionAccept.cc:74
#11 0x000055555565e683 in ProtocolProbeTrampoline::ioCompletionEvent (this=0x5555563bc880, event=<optimized out>,
    edata=<optimized out>) at ProtocolProbeSessionAccept.cc:123
#12 0x000055555581de76 in handleEvent (data=0x7fffe0017e38, event=100, this=<optimized out>)
    at ../../iocore/eventsystem/I_Continuation.h:153
#13 read_signal_and_update (vc=0x7fffe0017d20, event=100) at UnixNetVConnection.cc:150
#14 read_from_net (nh=0x7ffff31e0b90, vc=0x7fffe0017d20, thread=0x7ffff31dd010) at UnixNetVConnection.cc:390
#15 0x000055555580e6b0 in NetHandler::mainNetEvent (this=0x7ffff31e0b90, event=<optimized out>, e=<optimized out>) at UnixNet.cc:518
#16 0x000055555583c2d0 in handleEvent (data=0x555556172dc0, event=5, this=<optimized out>) at I_Continuation.h:153
#17 EThread::process_event (this=this@entry=0x7ffff31dd010, e=0x555556172dc0, calling_code=calling_code@entry=5) at UnixEThread.cc:128
#18 0x000055555583cdab in EThread::execute (this=0x7ffff31dd010) at UnixEThread.cc:252
#19 0x000055555560af60 in main (argv=<optimized out>) at Main.cc:1918
(gdb) p t_state.next_action
$1 = HttpTransact::SM_ACTION_API_READ_REQUEST_HDR
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$2 = HttpTransact::SM_ACTION_API_PRE_REMAP
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$3 = HttpTransact::SM_ACTION_REMAP_REQUEST
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$4 = HttpTransact::SM_ACTION_API_POST_REMAP
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$5 = HttpTransact::SM_ACTION_CACHE_LOOKUP
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$6 = HttpTransact::SM_ACTION_API_READ_CACHE_HDR
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$7 = HttpTransact::SM_ACTION_API_CACHE_LOOKUP_COMPLETE
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$8 = HttpTransact::SM_ACTION_DNS_LOOKUP
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$9 = HttpTransact::SM_ACTION_API_OS_DNS
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$10 = HttpTransact::SM_ACTION_CACHE_ISSUE_WRITE
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$11 = HttpTransact::SM_ACTION_ORIGIN_SERVER_OPEN
(gdb) c
Continuing.

Breakpoint 1, HttpSM::set_next_state (this=0x7fffea0d0080) at HttpSM.cc:6940
6940    {
(gdb) p t_state.next_action
$12 = HttpTransact::SM_ACTION_SERVER_READ
(gdb) c
Continuing.
```

## gdb でよく使うコマンドのメモ

ブレークポイント一覧表示あたりをよく忘れるのでメモ。ググってみると [マイクロデータベース管理システムの実装](http://wombat.cc.tsukuba.ac.jp/~furuse/jikken/text-07/text-07.html) にわかりやすくまとまっていました。

* b: break。ブレークポイント設定。b の後に「クラス名::メソッド名」、「関数名」、「ファイル名:行番号」のように止めたい箇所を指定します。
* i b: info breakpointsの略。ブレークポイント一覧表示。
* del [ブレークポイント番号]。ブレークポイント削除。番号を省略すると全て削除。
* where: ブレークポイントで止まったときにコールスタックを表示します。
* p: print。ブレークポイントで止まったときに変数の値を表示します。
* c: continue。実行継続。ブレークポイントを設定していればそこで止まります。
* n: next。ステップオーバー。関数呼び出しの際には中に入らずにステップ実行します。
* s: step。ステップイン。関数呼び出しの際にの中に入ってステップ実行します。
* q: quit。実行終了。まだ実行中だと `Quit anyway? (y or n)` と聞かれるので y を押して終了します。

ブレークポイントで止まっていない場合も、実行中に Ctrl-C で gdb のプロンプトが出るので、そこで上記のコマンドを実行できます。その後 c で実行再開できます。
