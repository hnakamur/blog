+++
Categories = []
Description = ""
Tags = []
date = "2016-01-08T01:12:13+09:00"
title = "rsyslogで信頼性のあるログ転送について調べたメモ"

+++
事の発端は fluentd を使ってみようかと思って [fluentd(td-agent)のインストールと設定](http://changineer.info/server/logging/fluentd-td-agent.html) を読んだことで す。fluentd のデメリットのところを読んで、ちょっと気になりました。

Goで書かれた[moriyoshi/ik](https://github.com/moriyoshi/ik)も気になったのですが、最近話聞かないし最終コミットも3ヶ月前だったので、今回は見送りました。

そこで、rsyslogでのログ転送について調査してみようと思いました。

rsyslog自体についてはこちらのスライド[#logstudy 01 rsyslog入門](http://www.slideshare.net/ttkzw/logstudy01-rsyslog-primer)が分かりやすかったです。

## syslog形式での出力サポート

### nginx
* [Logging to syslog](http://nginx.org/en/docs/syslog.html)

### Apache HTTP server

* [Sending our web logs to syslog](http://www.fnal.gov/docs/products/apache/syslog_logs_notes.html)
    * ErrorLogやCustomLogに以下の様な感じで書く。
    * `CustomLog "|/usr/bin/tee -a /var/log/www/access.log | /usr/bin/logger -thttpd -plocal6.notice" combined`
    * teeでファイルに出力しつつloggerコマンドでsyslogにも出力。
* [syslogで複数のapacheサーバのログを集積する - orattaの日記](http://d.hatena.ne.jp/oratta/20101121/1290341166)
    * こちらもCustomLogでloggerコマンドを呼び出す方式。
* [DSAS開発者の部屋:Apacheのアクセスログをsyslog経由で出力するためのモジュールを作りました](http://dsas.blog.klab.org/archives/51500856.html)
    * Apache 2.2以降で使えるカスタムモジュール
    * Cのsyslog関数を使っている
* [mod_syslog - Apache HTTP Server Version 2.5](https://httpd.apache.org/docs/trunk/mod/mod_syslog.html)
    * Apache 2.5からは標準モジュールになったらしい

### Apache Traffic Server
* [proxy.config.syslog_facility](http://trafficserver.readthedocs.org/en/latest/admin-guide/files/records.config.en.html#proxy-config-syslog-facility)
* [proxy.config.diags.output.emergency](http://trafficserver.readthedocs.org/en/latest/admin-guide/files/records.config.en.html#proxy-config-diags-output-emergency)

###  Cのsyslog出力関数
* [syslog(3): send messages to system logger - Linux man page](http://linux.die.net/man/3/syslog)

### Goのsyslogクライアントライブラリ
* [syslog - The Go Programming Language](https://golang.org/pkg/log/syslog/)

### loggerコマンド (シェルスクリプトから出力したい時に使用)
* [logger(1) - Linux man page](http://linux.die.net/man/1/logger)

## 信頼性のあるログ転送のためのRELPプロトコル

UDPで転送するとパケットロスしてログが消失する恐れがあります。

[#logstudy 01 rsyslog入門](http://www.slideshare.net/ttkzw/logstudy01-rsyslog-primer)の[81枚目のスライド](http://www.slideshare.net/ttkzw/logstudy01-rsyslog-primer/81)によると、TCPで転送しておけば、転送先のsyslogサーバがダウンしたら、キューイングして、復活したら再送するそうです。

これで十分そうな気もしたのですが、syslog forwardでググっていると[\[SOLVED\] Rsyslog forward log to other syslog server](http://ubuntuforums.org/showthread.php?t=2151986)というページからリンクされている[Rainer's Blog: On the (un)reliability of plain tcp syslog...](http://blog.gerhards.net/2008/04/on-unreliability-of-plain-tcp-syslog.html)という記事を見つけました。

さらにそこからリンクされている[Rainer's Blog: why you can't build a reliable TCP protocol without app-level acks...](http://blog.gerhards.net/2008/05/why-you-cant-build-reliable-tcp.html)という記事も読んでみました。

一言で言うと、信頼性の有るログ転送を実現するためには、TCPレベルでACKがあってもだめで、アプリケーションレベルのACKが必要ということです。

アプリケーションレベルのACKが無いと、サーバのバッファスペースが溢れてもクライアントが気づけないというのが問題の本質のようです。

これを解決するために作られたのが、[Rainer's Blog: RELP - the reliable event logging protocol](http://blog.gerhards.net/2008/03/relp-reliable-event-logging-protocol.html)です。

[librelp - a reliable logging library](http://www.librelp.com/)というのがCの実装で、ソースを見るとライセンスはGPLv3でした。

RELPはrsyslogdにすでに取り込まれていました。

* [Reliable Forwarding of syslog Messages with Rsyslog — rsyslog 8.14.0 documentation](http://www.rsyslog.com/doc/v8-stable/tutorials/reliable_forwarding.html)
* [imrelp: RELP Input Module — rsyslog 8.14.0 documentation](http://www.rsyslog.com/doc/v8-stable/configuration/modules/imrelp.html?highlight=relp)
* [omrelp: RELP Output Module — rsyslog 8.14.0 documentation](http://www.rsyslog.com/doc/v8-stable/configuration/modules/omrelp.html?highlight=relp)

ただし、imrelpの `Ruleset` パラメータはrsyslogdのバージョン7.5.0以降が必要らしいです。CentOS 7のrsyslogdは `yum info rsyslogd` によると 7.4.7 なのでこれは使えないようです。

CentOS 7では `rsyslog-relp.x86_64 : RELP protocol support for rsyslog` というパッケージをインストールすればRELPが使えるようです (まだ試してないです)。


## 参考: goで書かれたrsyslogサーバ

[mcuadros/go-syslog](https://github.com/mcuadros/go-syslog)というgoで書かれたrsyslogサーバも見つけました。

UDP、TCP、Unixソケットでの受信が出来るそうです。READMEに"using RFC3164, RFC6587 or RFC5424"とありますが、どこまで対応しているかは未調査です。

RELPは非対応のようです。ソースコードで大文字小文字無視でrelpで検索してヒットしなかったので。

