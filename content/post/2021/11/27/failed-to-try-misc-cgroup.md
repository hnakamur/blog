---
title: "Misc Cgroup を試そうと調べてみたけど手持ちのCPUが非対応でした"
date: 2021-11-27T21:56:08+09:00
---
## はじめに

https://twitter.com/ten_forward/status/1464396509055635456
のスレッドを見て Misc Cgroup を試してみようかと調べてみたけど手持ちのハードウェアは非対応で試せなかったというメモです。

## Misc Cgroup についての調査メモ

検索すると cgroup v1 のドキュメント [Misc controller — The Linux Kernel documentation](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v1/misc.html) がヒットしました。

[Control Group v2 — The Linux Kernel documentation](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html) の [Misc](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html#misc) を参照せよとのことです。

カーネルのビルドコンフィグで `CONFIG_CGROUP_MISC` が有効になっている必要があるとのこと。

[このKernel、どんなKernel？ - Qiita](https://qiita.com/takeoverjp/items/6f4f30cf634307fe25cc) によると Ubuntu では `/boot/config-X.Y.Z` ファイルでカーネルビルドコンフィグが確認できるとのこと。

```
$ grep CONFIG_CGROUP_MISC /boot/config-5.11.0-40-generic
```

で確認するとヒット無しでした。

さらに検索してみると [Linux 5.13 Introducing Misc Cgroup Controller - Phoronix](https://www.phoronix.com/scan.php?page=news_item&px=Linux-5.13-Misc-Cgroup-Control) で Misc Cgroup はカーネル 5.13 以降で使えるというのを知りました。

そこで [Kernel/MainlineBuilds - Ubuntu Wiki](https://wiki.ubuntu.com/Kernel/MainlineBuilds) の手順に沿って mainline のカーネル 5.15.5 を入れてみました。以下のようにカーネルのビルドコンフィグで `CONFIG_CGROUP_MISC` が有効になっていることを確認できました。

```
$ grep CONFIG_CGROUP_MISC /boot/config-5.15.5-051505-generic
CONFIG_CGROUP_MISC=y
```

[Mounting](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html#mounting) によると cgroup v1 と違って cgroup v2 は単一の階層しか持たないとのことです。

以下のコマンドを実行すると Ubntu では `/sys/fs/cgroup/unified` に cgroup2 がマウントされているようです。

```
$ mount | grep cgroup2
cgroup2 on /sys/fs/cgroup/unified type cgroup2 (rw,nosuid,nodev,noexec,relatime,nsdelegate)
```

[Misc](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html#misc) を見た感じ `misc.capacity`, `misc.current`, `misc.max` というファイルがあるらしい。ということで確認してみましたが私の環境ではありませんでした。

```
$ ls /sys/fs/cgroup/unified/misc*
ls: cannot access '/sys/fs/cgroup/unified/misc*': No such file or directory
```

`include/linux/misc_cgroup.h` に `enum misc_res_type` があるということで見てみると以下のようになっていました。
[include/linux/misc_cgroup.h#L11-L22](https://github.com/torvalds/linux/blob/v5.15/include/linux/misc_cgroup.h#L11-L22)

```
/**
 * Types of misc cgroup entries supported by the host.
 */
enum misc_res_type {
#ifdef CONFIG_KVM_AMD_SEV
  /* AMD SEV ASIDs resource */
  MISC_CG_RES_SEV,
  /* AMD SEV-ES ASIDs resource */
  MISC_CG_RES_SEV_ES,
#endif
  MISC_CG_RES_TYPES
};
```

kernel/cgroup/misc.c のほうも見てみると
[linux/misc.c#L19-L27](https://github.com/torvalds/linux/blob/v5.15/kernel/cgroup/misc.c#L19-L27)
に以下のように書かれていました。

```
/* Miscellaneous res name, keep it in sync with enum misc_res_type */
static const char *const isc_res_name[] = {
#ifdef CONFIG_KVM_AMD_SEV
  /* AMD SEV ASIDs resource */
  "sev",
  /* AMD SEV-ES ASIDs resource */
  "sev_es",
#endif
};
```

ということで AMD の SEV と SEV-ES というものがあるらしいです。

## AMD の (SEV Secure Encrypted Virtualization) について調査

検索すると以下のページが見つかりました。

* [AMD Secure Encrypted Virtualization (SEV) - AMD](https://developer.amd.com/sev/)
* [Secure Encrypted Virtualization (SEV) — The Linux Kernel documentation](https://www.kernel.org/doc/html/latest/virt/kvm/amd-memory-encryption.html)
* [第10章 インスタンスのメモリーを暗号化するための AMD SEV コンピュートノードの設定 Red Hat OpenStack Platform 16.1 | Red Hat Customer Portal](https://access.redhat.com/documentation/ja-jp/red_hat_openstack_platform/16.1/html/configuring_the_compute_service_for_instance_creation/configuring-amd-sev-compute-nodes-to-provide-memory-encryption-for-instances)

上の Red Hat のページによると「AMD EPYC™ 7002 Series (「Rome」) から利用」できるそうです。

一方 [What processors support SEV? · Issue #1 · AMDESE/AMDSEV](https://github.com/AMDESE/AMDSEV/issues/1) では EPYC のみというコメントや Ryzen PRO も OK と情報が錯綜しています。また AMD Ryzen 7 4800H で lscpu の出力に `sev` と `sev_es` が含まれるというコメントもありました。

残念ながら私の ThinkCentre M75q Tiny Gen2 の Ryzen PRO 4750GE は lscpu の出力に `sev` も `sev_es` も含まれていませんでした。

AMD の [Processor Specifications | AMD](https://www.amd.com/en/products/specifications/processors/)
から [AMD Ryzen™ 7 4800H | AMD](https://www.amd.com/en/product/9081) と [AMD Ryzen™ 7 PRO 4750GE | AMD](https://www.amd.com/en/product/10256) を見たのですが仮想化技術についての記載は見当たりません。

[AMD Ryzen 7 4800H Full Specifications - CPUAgent](https://www.cpuagent.com/cpu/amd-ryzen-7-4800h/specs/nvidia-geforce-rtx-2080-ti?res=1&quality=ultra) では AMD Ryzen 7 4800H Virtualization Technologies が AMD-V, SEV となっていました。 が [AMD Ryzen Embedded V1605B vs AMD Ryzen 7 4800H - GadgetVersus](https://gadgetversus.com/processor/amd-ryzen-embedded-v1605b-vs-amd-ryzen-7-4800h/) では AMD Ryzen Embedded V1605B の Crypto engine は Advanced Encryption Standard, Secure Memory Encryption, Secure Encrypted Virtualization と SEV も入っていますが 4800H のほうはハイフンとなってました。ただ AES は入っているはずのにハイフンなのでこのサイトでの 4800H のデータが情報不足な可能性もありそうです。

なお Linux の AMD SEV 対応については [AMD SEV - Phoronix](https://www.phoronix.com/scan.php?page=search&q=AMD+SEV) の検索結果で Phoronix の記事一覧が見られるのでここをチェックするのがよさそうです。

SEV が使える CPU があれば [AMD SME/SEV on Ubuntu 20 | OVH Guides](https://docs.ovh.com/asia/en/dedicated/enable-and-use-amd-sme-sev/) の手順を参考に SME (Secure Memory Encryption) と SEV (Secure Encrypted Virtualization) を有効にできそうです。

## 関連: AMD Secure Memory Encryption (SME) は 5.15 からデフォルト無効になったらしい

[Linux To No Longer Enable AMD SME Usage By Default Due To Problems With Some Hardware - Phoronix](https://www.phoronix.com/scan.php?page=news_item&px=Linux-SME-No-Default-Use)


