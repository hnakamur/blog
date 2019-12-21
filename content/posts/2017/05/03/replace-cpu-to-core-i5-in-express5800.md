+++
title="自宅サーバExpress5800/S70タイプRBのCPUをCore i5 650に換装してみた"
date = "2017-05-03T21:30:00+09:00"
tags = ["hardware", "cpu"]
categories = ["blog"]
+++


## はじめに

私は
[NEC Express5800／S70 タイプRB - usyWiki](http://pc.usy.jp/wiki/378.html)
を2011年に買って自宅サーバとして活用しています。一時期使って無い時期もありましたが、ここ2年ぐらいは使っています。

メモリを16GBに増設し、IntelのSSD (SSDSA2M160G2GC)を入れて使ってきましたが、CPUは出荷時の
Pentium G6950 (2.80GHz) のままでした。

性能面で特に不満はなかったのですが、最近見つけた
[ClickHouse — open source distributed column-oriented DBMS](https://clickhouse.yandex/)
を試そうと思ったところ
[System requirements](https://clickhouse.yandex/reference_en.html#System requirements)
にx86_64アーキテクチャでSSE4.2の拡張命令セットが必要と書かれていました。

確認用のコマンドを実行してみると、SSE4.2はサポートされていませんでした。

```console
$ grep -q sse4_2 /proc/cpuinfo && echo "SSE 4.2 supported" || echo "SSE 4.2 not supported"
SSE 4.2 not supported
```

ということで、人生初のCPU換装をやってみることにしました。

## CPUとグリスの購入

なるべく安く上げたいということで会社の同僚に相談したところソフマップで中古品として売っていた
[製品の仕様情報 - Intel® Core™ i5-650 Processor (4M Cache, 3.20 GHz)](https://ark.intel.com/ja/products/43546/Intel-Core-i5-650-Processor-4M-Cache-3_20-GHz)
(クーラー付き)を勧められて4,298円で購入しました。

グリスはアイネックスの1回分使い切りサイズのシリコングリス [GS-01 | Ainex](http://www.ainex.jp/products/gs-01/) をヨドバシで143円で購入しました。

グリスの選択は [CPUグリス6製品の性能を比較してみた（2015年9月版） | メモトラ](https://memotora.com/2015/09/09/cpu-grease-comparison-2015-september/) の記事を参考にしました。

## 換装

初めての経験なのでうまくできるか心配でしたが、以下の記事などを見てなんとか出来ました。わかりやすく解説されていてとても助かりました。ありがとうございます！

* [CPUクーラー取り外し　パソコン初心者講座](http://www.pc-master.jp/jisaku/cpu-cooler-t.html)
* [CPUグリスの交換・塗り直し　パソコン初心者講座](http://www.pc-master.jp/jisaku/cpu-grease-k.html)
* [CPU・CPUクーラー・メモリーの取り付け　パソコン初心者講座](http://www.pc-master.jp/jisaku/cpu-t.html)
* [[評判・口コミ]　アイネックス シリコングリス1.5g GS-01：人気のPC冷却パーツ・ファン関連の評価・口コミを真面目にお知らせ!](http://dzl79.xyz/k2507kc/entry1-54.html)  

まずはCPUクーラーを取り外しました。

.. image:: {attach}/images/2017/05/03/fan-Delta-Electronics-AFB0912VHD.photo1.jpg
    :width: 504px
    :height: 378px
    :alt: fan Delta Electoronics AFB0912VHD photo1

.. image:: {attach}/images/2017/05/03/fan-Delta-Electronics-AFB0912VHD.photo2.jpg
    :width: 504px
    :height: 378px
    :alt: fan Delta Electoronics AFB0912VHD photo2

型番を見て検索して Delta Electoronics AFB0912VHD というCPUクーラーだとわかりました。

次に、CPUソケットのレバーをどう動かすかがわからず困りました。
トルクスねじのT20のドライバーでねじが回せたので外してみたのですが、これは余計なことでした。
ねじを外してみてわかったのですが、手前のCPUソケットに対応してマザーボードの裏側に金属板が入っていてこれに対してねじ止めされていたのが外れてしまいました。

.. image:: {attach}/images/2017/05/03/CPU-socket.jpg
    :width: 504px
    :height: 378px
    :alt: CPU socket

再びつけるために一旦マザーボードのねじをすべて外して持ち上げる必要がありました。ケースに対してマザーボードがぎりぎりのサイズなのでなかなか大変でした。
取り付けるときにようやくわかったのですが、CPUクーラーのレバーは上の写真で右方向に引き出してから手前に上げればよかったんですね。

この後、ソケットにCPUを載せてグリスを塗りました。上の記事に

  グリスの目的が表面の反りと粗さを埋めるものですから、厚さとして0.05~0.1ミリあれば十分。

とあったので薄めにしました。「1回分使い切りサイズ」というのは相当余裕を見ているようで、ほんのちょっとしか使わなかったです。

購入したCPUに付属していたCPUクーラーは Intel E41997-002 でした。

.. image:: {attach}/images/2017/05/03/fan-Intel-E41997-002.photo1.jpg
    :width: 504px
    :height: 378px
    :alt: fan Intel E41997-002 photo1

.. image:: {attach}/images/2017/05/03/fan-Intel-E41997-002.photo2.jpg
    :width: 504px
    :height: 378px
    :alt: fan Intel E41997-002 photo2

2時間弱かかってようやく換装が終了しました。
ちゃんと起動するかドキドキでしたが、電源を入れてみると無事起動しました！

## cpuinfoの比較

#### 換装前のPentium G6950 (2.80GHz)

```console
$ cat /proc/cpuinfo
processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 37
model name      : Intel(R) Pentium(R) CPU        G6950  @ 2.80GHz
stepping        : 5
microcode       : 0x2
cpu MHz         : 1197.000
cache size      : 3072 KB
physical id     : 0
siblings        : 2
core id         : 0
cpu cores       : 2
apicid          : 0
initial apicid  : 0
fpu             : yes
fpu_exception   : yes
cpuid level     : 11
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm pcid popcnt lahf_lm tpr_shadow vnmi flexpriority ept vpid dtherm arat
bugs            :
bogomips        : 5585.76
clflush size    : 64
cache_alignment : 64
address sizes   : 36 bits physical, 48 bits virtual
power management:

processor       : 1
vendor_id       : GenuineIntel
cpu family      : 6
model           : 37
model name      : Intel(R) Pentium(R) CPU        G6950  @ 2.80GHz
stepping        : 5
microcode       : 0x2
cpu MHz         : 1197.000
cache size      : 3072 KB
physical id     : 0
siblings        : 2
core id         : 2
cpu cores       : 2
apicid          : 4
initial apicid  : 4
fpu             : yes
fpu_exception   : yes
cpuid level     : 11
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm pcid popcnt lahf_lm tpr_shadow vnmi flexpriority ept vpid dtherm arat
bugs            :
bogomips        : 5585.76
clflush size    : 64
cache_alignment : 64
address sizes   : 36 bits physical, 48 bits virtual
power management:
```

#### 換装後のCore i5 650 (3.20GHz)

```console
$ cat /proc/cpuinfo
processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 37
model name      : Intel(R) Core(TM) i5 CPU         650  @ 3.20GHz
stepping        : 2
microcode       : 0xc
cpu MHz         : 3193.000
cache size      : 4096 KB
physical id     : 0
siblings        : 2
core id         : 0
cpu cores       : 2
apicid          : 0
initial apicid  : 0
fpu             : yes
fpu_exception   : yes
cpuid level     : 11
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm sse4_1 sse4_2 popcnt aes lahf_lm tpr_shadow vnmi flexpriority ept vpid dtherm ida arat
bugs            :
bogomips        : 6384.15
clflush size    : 64
cache_alignment : 64
address sizes   : 36 bits physical, 48 bits virtual
power management:

processor       : 1
vendor_id       : GenuineIntel
cpu family      : 6
model           : 37
model name      : Intel(R) Core(TM) i5 CPU         650  @ 3.20GHz
stepping        : 2
microcode       : 0xc
cpu MHz         : 3193.000
cache size      : 4096 KB
physical id     : 0
siblings        : 2
core id         : 2
cpu cores       : 2
apicid          : 4
initial apicid  : 4
fpu             : yes
fpu_exception   : yes
cpuid level     : 11
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm sse4_1 sse4_2 popcnt aes lahf_lm tpr_shadow vnmi flexpriority ept vpid dtherm ida arat
bugs            :
bogomips        : 6384.15
clflush size    : 64
cache_alignment : 64
address sizes   : 36 bits physical, 48 bits virtual
power management:
```

## sysbenchの比較

#### 換装前のPentium G6950 (2.80GHz)

```console
$ sysbench --test=cpu --num-threads=2 run
sysbench 0.4.12:  multi-threaded system evaluation benchmark

Running the test with following options:
Number of threads: 2

Doing CPU performance benchmark

Threads started!
Done.

Maximum prime number checked in CPU test: 10000

Test execution summary:
    total time:                          5.1692s
    total number of events:              10000
    total time taken by event execution: 10.3368
    per-request statistics:
         min:                                  1.03ms
         avg:                                  1.03ms
         max:                                  5.32ms
         approx.  95 percentile:               1.04ms

Threads fairness:
    events (avg/stddev):           5000.0000/3.00
    execution time (avg/stddev):   5.1684/0.00
```

#### 換装後のCore i5 650 (3.20GHz)

```console
$ sysbench --test=cpu --num-threads=2 run
sysbench 0.4.12:  multi-threaded system evaluation benchmark

Running the test with following options:
Number of threads: 2

Doing CPU performance benchmark

Threads started!
Done.

Maximum prime number checked in CPU test: 10000

Test execution summary:
    total time:                          4.3400s
    total number of events:              10000
    total time taken by event execution: 8.6786
    per-request statistics:
         min:                                  0.86ms
         avg:                                  0.87ms
         max:                                  3.32ms
         approx.  95 percentile:               0.87ms

Threads fairness:
    events (avg/stddev):           5000.0000/3.00
    execution time (avg/stddev):   4.3393/0.00
```

## SSE 4.2がサポートされている確認

```console
$ grep -q sse4_2 /proc/cpuinfo && echo "SSE 4.2 supported" || echo "SSE 4.2 not supported"
SSE 4.2 supported
```

サポートされています！

## おわりに

苦労はしましたが、無事に換装出来てよかったです。良い経験になりました。
