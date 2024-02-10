---
title: "ModSecurityについて調べた"
date: 2024-02-10T08:45:09+09:00
---

## レポジトリ
* [owasp-modsecurity/ModSecurity: ModSecurity is an open source, cross platform web application firewall (WAF) engine for Apache, IIS and Nginx that is developed by Trustwave's SpiderLabs. It has a robust event-based programming language which provides protection from a range of attacks against web applications and allows for HTTP traffic monitoring, logging and real-time analysis. With over 10,000 deployments world-wide, ModSecurity is the most widely deployed WAF in existence.](https://github.com/owasp-modsecurity/ModSecurity)
    * C++, Apache 2.0ライセンス
    * What is the difference between this project and the old ModSecurity (v2.x.x)? の項によるとv3のlibmodsecurityはApache依存のv2とは異なりApache非依存のライブラリ
    * 下のBindingsにPythonとVarnishのバインディングが書かれている。nginx用に[owasp-modsecurity/ModSecurity-nginx: ModSecurity v3 Nginx Connector](https://github.com/owasp-modsecurity/ModSecurity-nginx)、Apache用に[owasp-modsecurity/ModSecurity-apache: ModSecurity v3 Apache Connector](https://github.com/owasp-modsecurity/ModSecurity-apache)がある。
    * READMEにあるコード例は古いようだ。実際のヘッダファイルTransactionクラスのprocessConnectionメソッドのシグネチャは[int processConnection(const char *client, int cPort,
        const char *server, int sPort)](https://github.com/owasp-modsecurity/ModSecurity/blob/v3.0.12/headers/modsecurity/transaction.h#L342-L343)となっている。
    * [Ivan Ristic（@ivanristic）さん / X](https://twitter.com/ivanristic)のプロフィールに Chief Scientist at Red Sift. Founder of Hardenize and author of Bulletproof TLS and PKI. Previously, founder of SSL Labs and ModSecurity. とある。

## 2024-01にTrustwaveからOWASPへ移管された

* https://www.modsecurity.org/ に2024-01-25にそれまでModSecurityの開発とサポートをしていたTrustwaveからOWASPに移管した旨が書かれいてる。
* [Trustwave Transfers ModSecurity Custodianship to OWASP | OWASP Foundation](https://owasp.org/blog/2024/01/09/ModSecurity.html)
    * 移管前からCore Rule SetはOWASPが管理していたとのこと。
* [OWASP - Wikipedia](https://en.wikipedia.org/wiki/OWASP)によると Open Worldwide Application Security Project の略。

## Core Rule Set (CRS)

* [OWASP ModSecurity Core Rule Set – The 1st Line of Defense Against Web Application Attacks](https://coreruleset.org/)
* レポジトリ：[coreruleset/coreruleset: OWASP ModSecurity Core Rule Set (Official Repository)](https://github.com/coreruleset/coreruleset/)
* Xのアカウント：[Core Rule Set（@CoreRuleSet）さん / X](https://twitter.com/CoreRuleSet)
* [XユーザーのModSecurityさん: 「Congratulations on version 3.1.0 @corazaio!」 / X](https://twitter.com/ModSecurity/status/1755974502113046555)で知ったが、[corazawaf/coraza: OWASP Coraza WAF is a golang modsecurity compatible web application firewall library](https://github.com/corazawaf/coraza)というのもある。Go製、Apache 2.0ライセンス、OWASP Core Rule Set v4と100%互換性ありとのこと。

## CVE-2024-1019の脆弱性

* [NVD - CVE-2024-1019](https://nvd.nist.gov/vuln/detail/CVE-2024-1019?ref=blog.sicuranext.com)
* [ModSecurity: Path Confusion and really easy bypass on v2 and v3](https://blog.sicuranext.com/modsecurity-path-confusion-bugs-bypass/)
* [Xで@ModSecurityの2024-01-31のポスト](https://twitter.com/ModSecurity/status/1752372749824045547)によるとバージョン3.0.12で修正。これがOWASP移管後の初リリースとのこと。

## Debian 12のModSecurity関連パッケージ

* [modsecurity を名前に含むパッケージを、bookworm スイート、すべてのセクション、すべてのアーキテクチャで検索](https://packages.debian.org/search?keywords=modsecurity&searchon=names&suite=bookworm&section=all)
    * libmodsecurity-dev 3.0.9-1+deb12u1: ModSecurity v3 library component (development files)
    * libmodsecurity3 3.0.9-1+deb12u1: ModSecurity v3 library component
    * libnginx-mod-http-modsecurity 1.0.3-1+b2: WAF module for Nginx
    * modsecurity-crs 3.3.4-1: OWASP ModSecurity Core Rule Set

## 参考記事

* [ModSecurityとは？オープンソースWAFのメリット・デメリットを解説 | WebセキュリティのEGセキュアソリューションズ](https://siteguard.jp-secure.com/blog/what-is-oss-modsecurity)
