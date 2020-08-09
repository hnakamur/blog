---
title: "sysstatのバイナリファイルフォーマット"
date: 2020-08-09T16:31:09+09:00
---

## はじめに

[sysstat](http://sebastien.godard.pagesperso-orange.fr/) のバイナリファイルのフォーマットを調べてみたメモです。

[Documents](http://sebastien.godard.pagesperso-orange.fr/documentation.html) のページを見てみましたが、ファイルフォーマットについての記述は見つけられませんでした。

[FAQ](http://sebastien.godard.pagesperso-orange.fr/faq.html) の "2.5. Are sar daily data files fully compatible with Sun Solaris format sar files?" で Solaris と Linux では形式が違うことはわかりました。

[portability of sa data files · Issue #135 · sysstat/sysstat](https://github.com/sysstat/sysstat/issues/135) というイシューの2016年のコメントで sqlite などを使うことも考えているとも書かれていましたが、 2020-08-09 時点では独自のバイナリファイル形式です。

ということでコードリーディングしてみました。
対象は Ubuntu 20.04 LTS の sysstat パッケージに合わせて 12.2.0 にします（ちなみに 2020-08-09 時点の最新リリースの 12.4.0 で、 Ubuntu 18.04 LTS の sysstat パッケージは 11.6.1 でした）。

## ファイル全体の構成図

sa.h 内のコメントにファイル全体の構成図が書いてありました。

[sa.h#L347-L445](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L347-L445)

## 全ての書き込みは write_all 関数で行う

`ag 'write\('` で検索してみた感じでは、全ての書き込みは
[write_all](https://github.com/sysstat/sysstat/blob/v12.2.0/sa_common.c#L403-L438)
関数で行っているようです。

一部 [pmiWrite (3)](https://manpages.ubuntu.com/manpages/focal/en/man3/pmiWrite.3.html) という関数を使っている箇所もありますでが、今回は対象外とします。

## sadc.c 内の write_all 関数の呼び出し箇所

write_all 関数の呼び出し箇所は sa_conv.c にもありますが、ここでは sadc.c のみを見ていきます。
sadc.c 内での write_all 関数の呼び出し箇所は以下の9箇所です。

```
sadc.c
480:    if (write_all(fd, &file_magic, FILE_MAGIC_SIZE) != FILE_MAGIC_SIZE) {
530:    if (write_all(fd, &file_hdr, FILE_HEADER_SIZE) != FILE_HEADER_SIZE) {
561:                    if (write_all(fd, &file_act, FILE_ACTIVITY_SIZE) != FILE_ACTIVITY_SIZE) {
584:    if (write_all(ofd, &(act[p]->nr_ini), sizeof(__nr_t)) != sizeof(__nr_t)) {
625:    if (write_all(ofd, &record_hdr, RECORD_HEADER_SIZE) != RECORD_HEADER_SIZE) {
635:            if (write_all(ofd, comment, MAX_COMMENT_LEN) != MAX_COMMENT_LEN) {
664:    if (write_all(ofd, &record_hdr, RECORD_HEADER_SIZE) != RECORD_HEADER_SIZE) {
678:                            if (write_all(ofd, &(act[p]->_nr0), sizeof(__nr_t)) != sizeof(__nr_t)) {
682:                    if (write_all(ofd, act[p]->_buf0, act[p]->fsize * act[p]->_nr0 * act[p]->nr2) !=
```

### 1. `setup_file_hdr` 関数で `file_magic` 構造体を書く

[setup_file_hdr](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L461-L568) 関数内の
[sadc.c#L480](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L480) (下記にインデント省略して引用)

```c
if (write_all(fd, &file_magic, FILE_MAGIC_SIZE) != FILE_MAGIC_SIZE) {
```

でファイルのマジックヘッダーを書き込んでいます。

[fill_magic_header](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L435-L459)
関数と
[struct file_magic](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L471-L514)
構造体などを見るとファイルのマジックヘッダーは以下のようになります。

`struct file_magic` 構造体76バイト。実際の例は下記のとおりです。

```console
$ xxd -l 76 /var/log/sysstat/sa09
00000000: 96d5 7521 0c02 0000 5001 0000 0000 0000  ..u!....P.......
00000010: 0100 0000 0100 0000 0c00 0000 0000 0000  ................
00000020: 0000 0000 0000 0000 0000 0000 0000 0000  ................
00000030: 0000 0000 0000 0000 0000 0000 0000 0000  ................
00000040: 0000 0000 0000 0000 0000 0000            ............
```

* `sysstat_magic` (2バイト): 0xd596
* `format_magic`(2バイト): 0x2175
* `sysstat_version` (1バイト): 0x0c
* `sysstat_patchlevel` (1バイト): 0x02
* `sysstat_sublevel` (1バイト): 0x00
* `sysstat_extraversion` (1バイト): 0x00
    * `sysstat_version` 以下の4つは 12.2.0 に対応した値ですので、別のバージョンでは違う値になります。
* `header_size` (4バイト): `sizeof(struct file_header)` = 0x00000150 = 336
* `upgraded` (4バイト): 0x000000
    * 別バージョンで作成後アップグレードされた場合は [sa.h#L495-L501](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L495-L501) 参照。
* `hdr_types_nr[3]` (12バイト) [hdr_types_nr](https://github.com/sysstat/sysstat/blob/v12.2.0/sa_common.c#L52)
    * `hdr_types_nr[0]` (4バイト): 0x00000001 = 1 [FILE_HEADER_ULL_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L595)
    * `hdr_types_nr[1]` (4バイト): 0x00000001 = 1 [FILE_HEADER_UL_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L596)
    * `hdr_types_nr[2]` (4バイト): 0x0000000c = 12 [FILE_HEADER_U_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L597)
* `pad` パディング (48バイト)


### 2. `setup_file_hdr` 関数で `file_header` 構造体を書く

[setup_file_hdr](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L461-L568) 関数内の
[sadc.c#L530](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L530)

```c
if (write_all(fd, &file_hdr, FILE_HEADER_SIZE) != FILE_HEADER_SIZE) {
```

で
[struct file_header](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L518-L592)
構造体を書いています。

`struct file_header` 構造体336バイト。

```console
$ xxd -s 76 -l 336 /var/log/sysstat/sa09
0000004c: 2949 2f5f 0000 0000 6400 0000 0000 0000  )I/_....d.......
0000005c: 0900 0000 1000 0000 7800 0000 0000 0000  ........x.......
0000006c: 0000 0000 0900 0000 0200 0000 0000 0000  ................
0000007c: 0100 0000 2400 0000 1800 0000 0000 0000  ....$...........
0000008c: 0907 084c 696e 7578 0000 0000 0000 0000  ...Linux........
0000009c: 0000 0000 0000 0000 0000 0000 0000 0000  ................
000000ac: 0000 0000 0000 0000 0000 0000 0000 0000  ................
000000bc: 0000 0000 0000 0000 0000 0000 0000 0000  ................
000000cc: 0000 0000 7468 696e 6b63 656e 7472 6500  ....thinkcentre.
000000dc: 0000 0000 0000 0000 0000 0000 0000 0000  ................
000000ec: 0000 0000 0000 0000 0000 0000 0000 0000  ................
000000fc: 0000 0000 0000 0000 0000 0000 0000 0000  ................
0000010c: 0000 0000 0035 2e34 2e30 2d34 322d 6765  .....5.4.0-42-ge
0000011c: 6e65 7269 6300 0000 0000 0000 0000 0000  neric...........
0000012c: 0000 0000 0000 0000 0000 0000 0000 0000  ................
0000013c: 0000 0000 0000 0000 0000 0000 0000 0000  ................
0000014c: 0000 0000 0000 7838 365f 3634 0000 0000  ......x86_64....
0000015c: 0000 0000 0000 0000 0000 0000 0000 0000  ................
0000016c: 0000 0000 0000 0000 0000 0000 0000 0000  ................
0000017c: 0000 0000 0000 0000 0000 0000 0000 0000  ................
0000018c: 0000 0000 0000 004a 5354 0000 0000 0000  .......JST......
```

* `sa_ust_time` (8バイト): 0x5f2f4929 (実際の日時によって変わります)
    * `date +%Y-%m-%dT%H:%M:%SZ --date @$(echo $((16#5f2f4929)))` で確認すると 2020-08-09T09:54:01Z でした（16進数から10進数への変換は [Convert Hexadecimal to Decimal in Bash – Linux Hint](https://linuxhint.com/convert_hexadecimal_decimal_bash/) を参考にしました）。
* `sa_hz` (4バイト, 8バイトアライン): 0x00000064 = 100
    *  `sysconf(_SC_CLK_TCK)` の値
* `sa_cpu_nr` (4バイト, 8バイトアライン): 0x00000009 = 9 = (8 + 1)
    * 4コア8スレッドのCPUの場合。+1はALLの分。
* `sa_act_nr` (4バイト): 0x0000010 = 16 （ファイル内のアクティビティ数）
* `sa_year` (4バイト): 0x00000078 = 120 （今年 - 1900）
* `act_types_nr` (12バイト) [act_types_nr](https://github.com/sysstat/sysstat/blob/v12.2.0/sa_common.c#L53)
    * `act_types_nr[0]` (4バイト): 0x00000000 = 0 [FILE_ACTIVITY_ULL_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L650)
    * `act_types_nr[1]` (4バイト): 0x00000000 = 0 [FILE_ACTIVITY_UL_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L651)
    * `act_types_nr[2]` (4バイト): 0x00000009 = 1 [FILE_ACTIVITY_U_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L652)
* `rec_types_nr` (12バイト) [rec_types_nr](https://github.com/sysstat/sysstat/blob/v12.2.0/sa_common.c#L54)
    * `rec_types_nr[0]` (4バイト): 0x00000002 = 2 [RECORD_HEADER_ULL_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L748)
    * `rec_types_nr[1]` (4バイト): 0x00000000 = 0 [RECORD_HEADER_UL_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L749)
    * `rec_types_nr[2]` (4バイト): 0x00000001 = 1 [RECORD_HEADER_U_NR](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L750)
* `act_size` (4バイト): 0x00000024 = 36
    * [FILE_ACTIVITY_SIZE](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L648) = `sizeof(struct file_activity)`
* `rec_size` (4バイト): 0x00000018 = 24
    * [RECORD_HEADER_SIZE](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L746) = `sizeof(struct record_header)`
* `extra_next` (4バイト): 0x00000000 (TRUE if an extra_desc structure exists.)
* `sa_day` (1バイト): 0x09 = 9 (9日)
* `sa_month` (1バイト): 0x07 = 7 (0が1月なので7は8月)
* `sa_sizeof_long` (1バイト): 0x08 = 8 (Size of a long integer.)
* `sa_sysname` (65バイト): Linux (Operating system name.) [UTSNAME_LEN](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L261) = 65
* `sa_nodename` (65バイト): thinkcentre (Machine hostname.)
* `sa_release` (65バイト): 5.4.0-42-generic (Operating system release number.)
* `sa_machine` (65バイト): x86_64 (Machine architecture.)
* `sa_tzname` (65バイト): JST (Timezone value.)


### 3. `setup_file_hdr` 関数で `file_activity` 構造体を書く

[setup_file_hdr](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L461-L568) 関数内の
[sadc.c#L561](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L561)

```c
if (write_all(fd, &file_act, FILE_ACTIVITY_SIZE) != FILE_ACTIVITY_SIZE) {
```

で
[struct file_activity](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L613-L646)
構造体を書いています。

[sadc.c#L538](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L538) の `for` ループで最大
[NR_ACT](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L23) = 39 個の `struct file_activity` を書きます。

実際の個数は `file_header` 構造体の `sa_act_nr` に保持されていて今回の例では 16 です。

```console
$ echo '76 + 336' | bc
412
$ echo '16 * 36' | bc
576
```

16個の `file_activity`。

```console
$ xxd -s 412 -l 576 /var/log/sysstat/sa09
0000019c: 0100 0000 8b00 0000 0900 0000 0100 0000  ................
000001ac: 0100 0000 5000 0000 0a00 0000 0000 0000  ....P...........
000001bc: 0000 0000 0200 0000 8b00 0000 0100 0000  ................
000001cc: 0100 0000 0000 0000 1000 0000 0100 0000  ................
000001dc: 0100 0000 0000 0000 0400 0000 8a00 0000  ................
000001ec: 0100 0000 0100 0000 0000 0000 1000 0000  ................
000001fc: 0000 0000 0200 0000 0000 0000 0500 0000  ................
0000020c: 8a00 0000 0100 0000 0100 0000 0000 0000  ................
0000021c: 4000 0000 0000 0000 0800 0000 0000 0000  @...............
0000022c: 0600 0000 8b00 0000 0100 0000 0100 0000  ................
0000023c: 0000 0000 3800 0000 0700 0000 0000 0000  ....8...........
0000024c: 0000 0000 0700 0000 8b00 0000 0100 0000  ................
0000025c: 0100 0000 0000 0000 8800 0000 1100 0000  ................
0000026c: 0000 0000 0000 0000 2200 0000 8b00 0000  ........".......
0000027c: 0100 0000 0100 0000 0000 0000 2000 0000  ............ ...
0000028c: 0400 0000 0000 0000 0000 0000 0800 0000  ................
0000029c: 8b00 0000 0100 0000 0100 0000 0000 0000  ................
000002ac: 2000 0000 0400 0000 0000 0000 0000 0000   ...............
000002bc: 0900 0000 8c00 0000 0100 0000 0100 0000  ................
000002cc: 0000 0000 2800 0000 0300 0000 0000 0000  ....(...........
000002dc: 0300 0000 0b00 0000 8c00 0000 0e00 0000  ................
000002ec: 0100 0000 0100 0000 5000 0000 0300 0000  ........P.......
000002fc: 0300 0000 0800 0000 0c00 0000 8d00 0000  ................
0000030c: 0300 0000 0100 0000 0100 0000 5000 0000  ............P...
0000031c: 0700 0000 0000 0000 0100 0000 0d00 0000  ................
0000032c: 8c00 0000 0300 0000 0100 0000 0100 0000  ................
0000033c: 5800 0000 0900 0000 0000 0000 0000 0000  X...............
0000034c: 0e00 0000 8a00 0000 0100 0000 0100 0000  ................
0000035c: 0000 0000 1800 0000 0000 0000 0000 0000  ................
0000036c: 0600 0000 0f00 0000 8a00 0000 0100 0000  ................
0000037c: 0100 0000 0000 0000 2c00 0000 0000 0000  ........,.......
0000038c: 0000 0000 0b00 0000 1000 0000 8a00 0000  ................
0000039c: 0100 0000 0100 0000 0000 0000 1800 0000  ................
000003ac: 0000 0000 0000 0000 0600 0000 2700 0000  ............'...
000003bc: 8a00 0000 0900 0000 0100 0000 0100 0000  ................
000003cc: 1400 0000 0000 0000 0000 0000 0500 0000  ................
```

最初の1個の `file_activity`。

```console
$ xxd -s 412 -l 36 /var/log/sysstat/sa09
0000019c: 0100 0000 8b00 0000 0900 0000 0100 0000  ................
000001ac: 0100 0000 5000 0000 0a00 0000 0000 0000  ....P...........
000001bc: 0000 0000                                ....
```

[struct file_activity](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L613-L646) 構造体。

[sadc.c#L540-L563](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L540-L563)
で
[unsigned int id_seq\[NR_ACT\]](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L76)
と
[struct activity *act\[NR_ACT\]](https://github.com/sysstat/sysstat/blob/v12.2.0/activity.c#L1895-L1943)
を参照して、 `act` の要素をローカル変数の [struct file_activity file_act](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L475) に移し替えてからファイルに書きます。

* `id` (4バイト): Identification value of activity.
* `magic` (4バイト): Activity magical number.
* `nr` (4バイト): ファイル作成時のこのアクティビティのアイテム数
     * [__nr_t](https://github.com/sysstat/sysstat/blob/v12.2.0/rd_stats.h#L46-L47) は int に `#define` されている
* `nr2` (4バイト): このアクティビティのサブアイテム数
* `has_nr` (4バイト): statistics の前に構造体の数がある場合は TRUE
* `size` (4バイト): item構造体のサイズ
* `types_nr[3]` (12バイト)
    * `types_nr[0]` (4バイト): long long のサイズ
    * `types_nr[1]` (4バイト): long のサイズ
    * `types_nr[2]` (4バイト): int のサイズ

### 4. `write_new_cpu_nr` 関数内で CPU 番号を書く

[write_new_cpu_nr](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L570-L587) 関数内の
[sadc.c#L584](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L584)

```c
if (write_all(ofd, &(act[p]->nr_ini), sizeof(__nr_t)) != sizeof(__nr_t)) {
```

で
RESTART レコードの後に CPU の新しい番号を書きます。


### 5. `write_special_record` 関数で `record_header` 構造体を書く

[write_special_record](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L589-L639) 関数内の
[sadc.c#L625](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L625)の

```c
if (write_all(ofd, &(act[p]->_nr0), sizeof(__nr_t)) != sizeof(__nr_t)) {
```

で [struct record_header](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L718-L744) 構造体の
グローバル変数 [record_hdr](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L72) を書きます。

`struct record_header` 構造体のサイズは24バイトです。

### 6. `write_special_record` 関数で `comment` を書く

[write_special_record](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L589-L639) 関数内の
[sadc.c#L635](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L635)の

```c
if (write_all(ofd, comment, MAX_COMMENT_LEN) != MAX_COMMENT_LEN) {
```

で
[char comment\[MAX_COMMENT_LEN\]](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L74)
を書きます。

コメントの最大長 [MAX_COMMENT_LEN](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L715-L716) は64です。

### 7. `write_stats` 関数で `record_header` 構造体を書く

[write_stats](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L641-L688) 関数内の
[sadc.c#L664](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L664)

```c
if (write_all(ofd, &record_hdr, RECORD_HEADER_SIZE) != RECORD_HEADER_SIZE) {
```

で [struct record_header](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L718-L744) 構造体の
グローバル変数 [record_hdr](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L72) を書きます。

### 8. `write_stats` 関数で `activity` 構造体の `nr[0]` を書く

[write_stats](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L641-L688) 関数内の
[sadc.c#L678](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L678)の

```c
if (write_all(ofd, &(act[p]->_nr0), sizeof(__nr_t)) != sizeof(__nr_t)) {
```

と
[sa.h#L829](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L829)

```c
#define _nr0	nr[0]
```

で

[struct activity](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L845-L1065) 構造体の
[sa.h#L1020-L1024](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L1020-L1024) の

```c
/*
 * Number of items, as read and saved in corresponding buffer (@buf: See below).
 * The value may be zero for a particular sample if no items have been found.
 */
__nr_t nr[3];
```

の `nr[0]` (4バイト) を書きます。

### 9. `write_stats` 関数で `activity` 構造体の `buf[0]` を書く

[write_stats](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L641-L688) 関数内の
[sadc.c#L682](https://github.com/sysstat/sysstat/blob/v12.2.0/sadc.c#L682) (下記にインデント省略して引用)の

```c
if (write_all(ofd, act[p]->_buf0, act[p]->fsize * act[p]->_nr0 * act[p]->nr2) !=
```

と
[sa.h#L828](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L828)
の

```c
#define _buf0	buf[0]
```

で
[struct activity](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L845-L1065) 構造体の
[sa.h#L1052-L1059](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L1052-L1059) の

```c
/*
 * Buffers that will contain the statistics read. Its size is @nr * @nr2 * @size each.
 * [0]: used by sadc.
 * [0] and [1]: current/previous statistics values (used by sar).
 * [2]: Used by sar to save first collected stats (used later to
 * compute average).
 */
void *buf[3];
```

の `buf[0]` を書きます。
サイズは `act[p]->fsize * act[p]->_nr0 * act[p]->nr2` です。

`fsize` は
[sa.h#L1030-L1035](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L1030-L1035) の

```c
/*
 * Size of an item.
 * This is the size of the corresponding structure, as read from or written
 * to a file, or read from or written by the data collector.
 */
int fsize;
```

です。

`_nr0` は前項に書いた `activity` 構造体の `nr[0]` です。

`nr2` は
[sa.h#L996-L1013](https://github.com/sysstat/sysstat/blob/v12.2.0/sa.h#L996-L1013)
の

```c
/*
 * Number of sub-items on the system.
 * @nr2 is in fact the second dimension of a matrix of items, the first
 * one being @nr. @nr is the number of lines, and @nr2 the number of columns.
 * A negative value (-1) is the default value and indicates that this number
 * has still not been calculated by the f_count2() function.
 * A value of 0 means that this number has been calculated, but no sub-items have
 * been found.
 * A positive value (>0) has either been calculated or is a constant.
 * Rules:
 * 1) IF @nr2 = 0 THEN @nr = 0
 *    Note: If @nr = 0, then @nr2 is undetermined (may be -1, 0 or >0).
 * 2) IF @nr > 0 THEN @nr2 > 0.
 *    Note: If @nr2 > 0 then @nr is undetermined (may be -1, 0 or >0).
 * 3) IF @nr <= 0 THEN @nr2 = -1 (this is the default value for @nr2,
 * meaning that it has not been calculated).
 */
__nr_t nr2;
```

です。


つまり、サイズは (アイテムのサイズ * アイテム数 * サブアイテム数) です。

## `activity` 構造体の `buf[0]` への値のセット

例えば CPU の統計情報の場合、 `struct activity` 型のグローバル変数
[cpu_act](https://github.com/sysstat/sysstat/blob/v12.2.0/activity.c#L63-L114) の
[activity.c#L78](https://github.com/sysstat/sysstat/blob/v12.2.0/activity.c#L78)

```c
.f_read		= wrap_read_stat_cpu,
```
で設定している
[wrap_read_stat_cpu](https://github.com/sysstat/sysstat/blob/v12.2.0/sa_wrap.c#L56-L87)関数

```c
/*
 ***************************************************************************
 * Read CPU statistics.
 *
 * IN:
 * @a	Activity structure.
 *
 * OUT:
 * @a	Activity structure with statistics.
 ***************************************************************************
 */
__read_funct_t wrap_read_stat_cpu(struct activity *a)
{
	struct stats_cpu *st_cpu
		= (struct stats_cpu *) a->_buf0;
	__nr_t nr_read = 0;

	/* Read CPU statistics */
	do {
		nr_read = read_stat_cpu(st_cpu, a->nr_allocated);

		if (nr_read < 0) {
			/* Buffer needs to be reallocated */
			st_cpu = (struct stats_cpu *) reallocate_buffer(a);
		}
	}
	while (nr_read < 0);

	a->_nr0 = nr_read;

	return;
}
```

で `activity` 構造体の `buf[0]` へのポインタを `struct stats_cpu *` にキャストし、そこに
[read_stat_cpu](https://github.com/sysstat/sysstat/blob/v12.2.0/rd_stats.c#L44-L152) 関数で
[common.h#L71](https://github.com/sysstat/sysstat/blob/v12.2.0/common.h#L71) で定義されている

```c
#define STAT			PRE "/proc/stat"
```

のファイルを読んで `struct stats_cpu` 構造体に読み込んだ値を設定しています。
