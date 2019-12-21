+++
title="CoreDNSをWindowsのサービスとして登録するためのラッパをGoで書いてみた"
date = "2019-10-30T15:25:00+09:00"
tags = ["dns", "go", "windows"]
categories = ["blog"]
+++


# はじめに

Windows の Hyper-V の Linux 上でサーバサイドの開発をしていると Windows 上のウェブブラウザや Windows Subsystem for Linux の curl からアクセスする際に好みの FQDN でアクセスできるようにしたいというニーズがあります。

Windows は `C:\Windows\System32\drivers\etc\hosts` 、 Windows Subsystm for Linux は `/etc/hosts` を編集してエントリを追加して対応していたのですが 2 箇所変更するのが面倒です。

そんなときふと、手元でDNSサーバを動かせば良いのではと思いました。そうすれば、変更が1か所で済むしCNAMEやTXTレコードも扱えるという利点もあります。

そこで [CoreDNS](https://coredns.io/) を試してみたら、手軽に使えて良さそうでした。

常用するとなると Windows の起動時に自動で CoreDNS も起動したいところです。スタートアップアプリとして実行するのでも良さそうですが、サービスとして実行できると便利かと思い、調べてみるとGoの良さそうなライブラリ [kardianos/service: Run go programs as a service on major platforms.](https://github.com/kardianos/service) を見つけたので、サービス登録用のラッパ [hnakamur/corednsservice](https://github.com/hnakamur/corednsservice) を書いてみました。

以下に設定手順とラッパの実装についてメモしておきます。

# 環境構築手順

## CoreDNS のインストールと設定

[CoreDNS](https://coredns.io/) の Download から Windows 用の実行ファイルを含んだ tarball （例: coredns_1.6.4_windows_amd64.tgz） をダウンロードします。

CoreDNS 用のディレクトリを作成してそこに展開します。以下は `C:\CoreDNS` として説明します。

以下は Windows Subsystem for Linux での実行例を示します（なお真面目には tarball を保存して sha256 ファイルとチェックしたほうが良いです）。

```console
mkdir /mnt/c/CoreDNS
cd /mnt/c/CoreDNS
curl -LO https://github.com/coredns/coredns/releases/download/v1.6.4/coredns_1.6.4_windows_amd64.tgz | tar zxf -
```

設定は [CoreDNS: DNS and Service Discovery](https://coredns.io/manual/toc/) を参考に適宜行います。

例として以下のファイルを作ってみました。
`example.org` のドメインはファイルでDNSレコードを設定してそれ以外は Google Public DNSにフォワードする設定です。

`C:\CoreDNS\Corefile`

```text
example.org {
    file C:\CoreDNS\db.example.org
    log
}

. {
    forward . 8.8.8.8 8.8.4.4
    log
}
```

`C:\CoreDNS\db.example.org`

```text
$ORIGIN example.org.
@       3600 IN SOA sns.dns.icann.org. noc.dns.icann.org. (
                                2019103001 ; serial
                                7200       ; refresh (2 hours)
                                3600       ; retry (1 hour)
                                1209600    ; expire (2 weeks)
                                3600       ; minimum (1 hour)
                                )

sv01    IN A 192.0.2.11
sv02    IN A 192.0.2.12
```

ローカルで使うだけなら上記のようにNSレコードは省略しても動きました。

## corednsserviceのインストールと設定

[hnakamur/corednsservice](https://github.com/hnakamur/corednsservice) の releases から `corednsservice.exe` をダウンロードして `C:\CoreDNS` に保存します。

Windows Subsystem for Linux での実行例を示します。

```console
curl -LO https://github.com/hnakamur/corednsservice/releases/download/v0.1.0/corednsservice.exe -C /mnt/c/CoreDNS
```

設定ファイルは `corednsservice.exe` と同じディレクトリに `corednsservice.yml` というファイル名で配置する必要があります。

以下に例を示します。

```yaml
name: CoreDNS
display_name: CoreDNS service
description: CoreDNS service for local development.
exec: "C:\\CoreDNS\\coredns.exe"
args: ["-conf", "Corefile"]
dir: "C:\\CoreDNS"
stdout:
  filename: "C:\\CoreDNS\\coredns.log"
  maxsize: 100
  maxbackups: 50
  maxage: 30
  compress: true
```

サービスの登録は管理者権限のコマンドプロンプトを開いて以下のように実行します。
タスクマネージャを開いて[サービス]タブに CoreDNS というサービスが登録されたことを確認します。

```text
cd \CoreDNS
corednsservice -service install
```

サービス起動はコマンドプロンプトで以下のように実行します。あるいはタスクマネージャの[サービス]タブで CoreDNS を選んでポップアップメニューの開始でも良いです。

起動成功するとタスクマネージャの[サービス]タブの CoreDNS が実行中になり、[詳細]タブでは `coredns.exe` と `corednsservice.exe` が実行中になります。

```text
corednsservice -service start
```

ちなみにサービス停止は以下のようにします。

```text
corednsservice -service stop
```

サービスの登録解除は以下のようにします。

```text
corednsservice -service uninstall
```

CoreDNS のサービスを動かした状態で Windows Subsystem for Linux の端末から動作確認した例を示します。

```console
$ dig @localhost sv01.example.org

; <<>> DiG 9.11.3-1ubuntu1.9-Ubuntu <<>> @localhost sv01.example.org
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 9988
;; flags: qr aa rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; COOKIE: 9f20a2550c810519 (echoed)
;; QUESTION SECTION:
;sv01.example.org.              IN      A

;; ANSWER SECTION:
sv01.example.org.       3600    IN      A       192.0.2.11

;; Query time: 0 msec
;; SERVER: 127.0.0.1#53(127.0.0.1)
;; WHEN: Wed Oct 30 12:25:14 JST 2019
;; MSG SIZE  rcvd: 89
```

また `dig @localhost example.net` など `example.org` 以外のドメインの名前解決も試してフォワーディングが動いていることを確認します。

## WindowsでローカルのDNSを使う設定

コントロールパネルの[ネットワークとインターネット]→[イーサネット]と進んで、[アダプターのオプションを変更する]リンクをクリックします。

[Wi-Fi]と[イーサネット]についてそれぞれ以下の設定を行います。

* プロパティの[インターネット プロトコル バージョン 4 (TCP/IP)]で優先DNSサーバを `127.0.0.1` 、代替DNSサーバを空に変更。もし元々固定で設定していた場合は元の構成に戻すときのために変更前の値をどこかにメモしておきます。
* プロパティの[インターネット プロトコル バージョン 4 (TCP/IP)]で優先DNSサーバを `::1` 、 代替DNSサーバを空に変更。

設定したらコマンドプロンプトを開いて動作確認します。

```text
C:\>nslookup sv01.example.org
サーバー:  UnKnown
Address:  ::1

名前:    sv01.example.org
Address:  192.0.2.11
```

## Windows Subsystem for LinuxでローカルのDNSを使う設定

[DNS not working in fresh Ubuntu 18.04 that installed from Windows Store · Issue #3268 · microsoft/WSL](https://github.com/microsoft/WSL/issues/3268) というイシューの [コメント](https://github.com/microsoft/WSL/issues/3268#issuecomment-543190053) で知った [Fix DNS resolution in WSL2](https://gist.github.com/coltenkrauter/608cfe02319ce60facd76373249b8ca6) の手順で設定します。 WSL2 と書かれていますが WSL1 でもこの手順で行けました。

Windows Subsystem for Linux の端末で変更前の `/etc/resolve.conf` を確認してみると上記のリンク先に書かれているように `../run/resolvconf/resolv.conf` へのシンボリックリンクになっていました。

```console
$ ls -l /etc/resolv.conf
lrwxrwxrwx 1 root root 29 May 25  2018 /etc/resolv.conf -> ../run/resolvconf/resolv.conf
```

Windows Subsystem for Linux の端末で以下のように実行して設定を変更します。

```console
mv /etc/resolv.conf{,.bak}
echo 'nameserver 127.0.0.1' | sudo tee /etc/resolv.conf
```

これで今度は `@localhost` なしで `dig sv01.example.org` などとして動作確認します。

```console
$ dig sv01.example.org

; <<>> DiG 9.11.3-1ubuntu1.9-Ubuntu <<>> sv01.example.org
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 38075
;; flags: qr aa rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; COOKIE: 797c9c0a9107764c (echoed)
;; QUESTION SECTION:
;sv01.example.org.              IN      A

;; ANSWER SECTION:
sv01.example.org.       3600    IN      A       192.0.2.11

;; Query time: 0 msec
;; SERVER: 127.0.0.1#53(127.0.0.1)
;; WHEN: Wed Oct 30 12:51:03 JST 2019
;; MSG SIZE  rcvd: 89
```

ここまで確認出来たら後は実際の利用ケースに応じて、設定ファイルを書き換えて CoreDNS のサービスを再起動すればOKです。


# 開発メモ

[hnakamur/corednsservice](https://github.com/hnakamur/corednsservice) は
[kardianos/service](https://github.com/kardianos/service) の
[example/runner/runner.go](https://github.com/kardianos/service/blob/4df36c9fc1c6ac86231851ad6fa5627e184c94e5/example/runner/runner.go) をベースにしています。

変更点は以下の通りです。

* 設定ファイルをJSONからYAMLに変更。
* ログをファイルに保存するようにした。
    * `gopkg.in/natefinch/lumberjack.v2` パッケージを使ってローテートするようにしています。といいつつ実際にログがローテートされるかの確認はまだです。
* ログの各行にタイムスタンプを追加。
    * CoreDNS の [log](https://coredns.io/plugins/log/) プラグインはドキュメントを見るとログに日時を出力できるとあるのですが設定項目が見当たりません。調べてみると [pkg/log: remove timestamp by miekg · Pull Request #3218 · coredns/coredns](https://github.com/coredns/coredns/pull/3218) で出力しないように変更されていました。ということで自前で出力するようにしました。

# 脱線: vEthernet (Default Switch) のアドレス

はじめにに入れるには長すぎるので別項目にしました。

Multipass で作成した VM は vEthernet (Default Switch) のネットワークインターフェースを使うのですが、Windowsの再起動の都度IPアドレスが変わってしまいます。

[[feature request] Support for NAT network on Hyper-V virtual switch · Issue #1153 · CanonicalLtd/multipass](https://github.com/CanonicalLtd/multipass/issues/1153) にNAT対応の要望を上げてみたところ、 `インスタンス名.mshome.net` で名前解決できると教わりました。例えば `primary` という VM なら `primary.mshome.net` です。

調べてみると `C:\Windows\System32\drivers\etc\hosts.ics` というファイルにVMに対応したエントリが作られていました。

[Internet Connection Sharing](https://en.wikipedia.org/wiki/Internet_Connection_Sharing) （インターネット接続共有）というWinodwsの機能らしいです。

ですが、これだと Windows 上のブラウザでは名前解決できるのですが、 Windows Subsystem for Linux の curl や ssh からは参照できないのと、 `mshome.net` 以外のドメインを使いたいというニーズも満たせないなあと思いました。

で、DNSサーバをローカルに立てて CNAME で `primary.mshome.net` に向ければ良いかもと思ったのが発端です。

ただ、やっぱり Multipass で扱えなくても NAT にして Hyper-V で直接VMを使う方式のほうが良いかなあと考え中です。

いずれにせよローカルでDNSが動いていると開発には便利なのでCoreDNS使ってみようと思います。
