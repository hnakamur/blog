Title: EC2で同じリージョンの全ホストのプライベートIPを起動時にhostsに自動登録
Date: 2013-02-16 00:00
Category: blog
Tags: aws
Slug: blog/2013/02/16/aws-update-hosts-for-servers-in-same-region

Elastic IPの上限数にひっかかって使えない自体に遭遇したので作りました。

[Elastic IP アドレス上限緩和申請 | アマゾン ウェブ サービス（AWS 日本語）](http://aws.amazon.com/jp/contact-us/eip_limit_request/) から緩和申請できるようです。

が、申請完了画面で、3〜5営業日かかる、緊急の場合は、完了画面に表示されるCase Numberを添えて ec2-request@amazon.com に送るようにと書かれていました。

（Case Numberを添えてというのは今気付いた。再度メールしました。ブログに書くために読み返してよかった）

そこで、hostsにプライベートアドレスを登録するスクリプトを書くことにしました。

[EC2 - 動的プライベートIPアドレスをどうにかする | code up](http://frmmpgit.blog.fc2.com/blog-entry-123.html) を参考にしました。ありがとうございます。

最初は対象のホストの一覧を指定するようなスクリプトを書いていたのですが、ホストを増やすことを考えると編集と反映が面倒だと予想して、リージョン内の全ホストを一括登録することにしました。

## 情報取得用のAIMユーザ作成

AIMでUserを作ってUser PolicyにReadOnlyAccessを与えます。


## スクリプト設置
以下の設定ファイルとスクリプトを設置します。

アクセスキーとシークレットキーは上で作ったユーザのものを設定します。

/root/.amazon_address_finder_key

```
export AWS_ACCESS_KEY=${your_access_key_here}
export AWS_SECRET_KEY=${your_secret_key_here}
```

/usr/local/sbin/update_hosts.sh

```
#!/bin/sh
. /root/.amazon_address_finder_key
region=`ec2-metadata | sed -n 's/^local-hostname: ip-[0-9-]*\.\(.*\)\.compute\.i
nternal/\1/p'`

ec2-describe-instances --region $region -H --show-empty-fields | gawk '
BEGIN {OFS="\t"; print "127.0.0.1", "localhost localhost.localdomain"}
/^INSTANCE/ {ip = $18}  
/^TAG/ {print ip, gensub(/.*\tName\t([^\t]*).*/, "\\1", $0)}  
' > /etc/hosts
```

/etc/cron.d/update_hosts

```
@reboot root /usr/local/sbin/update_hosts.sh
```

## 実行
これで、OS起動時にhostsが上書き更新されます。

インタンスのNameタグに設定した値がホスト名になります。

出力例

```
127.0.0.1       localhost localhost.localdomain
10.132.102.199  web01
10.128.21.174   web02
10.120.32.111   app01
10.132.103.238  app02
```

## githubに移動しました

さらにhostnameも更新するようにして、スクリプトが発展してきたので、
[hnakamur/aws_scripts · GitHub](https://github.com/hnakamur/aws_scripts)
に移動しました。

