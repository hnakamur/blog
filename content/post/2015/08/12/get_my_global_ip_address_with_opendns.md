Title: 自分のグローバルアドレスをOpenDNSとdigコマンドで調べる方法を試してみた
Date: 2015-08-12 07:14
Category: blog
Slug: blog/2015/08/12/get_my_global_ip_address_with_opendns

[linux - How can I get my external IP address in bash? - Unix & Linux Stack Exchange](http://unix.stackexchange.com/questions/22615/how-can-i-get-my-external-ip-address-in-bash/81699)を読んで試してみたのでメモです。

この記事を読むまでは `curl -s http://ifconfig.me` しか知りませんでした。

処理時間を比べてみました（出力結果のIPアドレスは伏せ字XXX.XXX.XXX.XXXにしています）。

```
$ time dig +short myip.opendns.com @resolver1.opendns.com
XXX.XXX.XXX.XXX

real    0m0.061s
user    0m0.010s
sys     0m0.016s
$ time curl -s http://whatismyip.akamai.com
XXX.XXX.XXX.XXX
real    0m0.571s
user    0m0.011s
sys     0m0.009s
$ time curl -s http://ifconfig.me
XXX.XXX.XXX.XXX

real    0m0.581s
user    0m0.011s
sys     0m0.007s
```

私が試した環境では、whatismyip.akamai.comとifconfig.meにhttpで問い合わせる方法は約0.6秒弱ですが、OpenDNSにdigで問い合わせる方法だと約0.06秒と一桁速いということがわかりました。
