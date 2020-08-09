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

## sa.h 内のコメントにファイルのフォーマットが書いてありました。

[sa.h#L355-L453](https://github.com/sysstat/sysstat/blob/v12.4.0/sa.h#L355-L453)

## 全ての書き込みは write_all 関数で行う

`ag 'write\('` で検索してみた感じでは、全ての書き込みは [write_all](https://github.com/sysstat/sysstat/blob/v12.4.0/sa_common.c#L400-L435) 関数で行っているようです。

一部 [pmiWrite (3)](https://manpages.ubuntu.com/manpages/focal/en/man3/pmiWrite.3.html) という関数を使っている箇所もありますでが、今回は対象外とします。

## sadc.c 内の write_all 関数の呼び出し箇所

write_all 関数の呼び出し箇所は sa_conv.c にもありますが、ここでは sadc.c のみを見ていきます。
sadc.c 内での write_all 関数の呼び出し箇所は以下の8箇所です。

```
sa_conv.c
144:    if (write_all(stdfd, &fm, FILE_MAGIC_SIZE) != FILE_MAGIC_SIZE) {
387:    if ((n = write_all(stdfd, &fh, FILE_HEADER_SIZE)) != FILE_HEADER_SIZE) {
1433:           if (write_all(stdfd, &fa, FILE_ACTIVITY_SIZE) != FILE_ACTIVITY_SIZE) {
1483:   if (write_all(stdfd, &rec_hdr, RECORD_HEADER_SIZE) != RECORD_HEADER_SIZE) {
1514:   if (write_all(stdfd, file_comment, sizeof(file_comment)) != sizeof(file_comment)) {
1589:   if (write_all(stdfd, &cpu_nr, sizeof(__nr_t)) != sizeof(__nr_t)) {
1805:                   if (write_all(stdfd, &nr, sizeof(__nr_t)) != sizeof(__nr_t))
1813:                           if (write_all(stdfd,
```

### 1. `setup_file_hdr` 関数内

[sadc.c#L493](https://github.com/sysstat/sysstat/blob/v12.4.0/sadc.c#L493) でファイルのマジックヘッダーを書き込んでいます。

[fill_magic_header](https://github.com/sysstat/sysstat/blob/v12.4.0/sadc.c#L448-L472) 関数と
[struct file_magic](https://github.com/sysstat/sysstat/blob/v12.4.0/sa.h#L479-L522) 構造体などを見るとファイルのマジックヘッダーは以下のようになります。

* `sysstat_magic`: 0xd596 (2バイト)
* `format_magic`: 0x2175 (2バイト)
* `sysstat_version`: 0x0c (1バイト)
* `sysstat_patchlevel`: 0x02 (1バイト)
* `sysstat_sublevel`: 0x00 (1バイト)
* `sysstat_extraversion`: 0x00 (1バイト)
