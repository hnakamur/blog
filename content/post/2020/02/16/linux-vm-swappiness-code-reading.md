---
title: "Linuxのvm_swapinessについてコードリーディングしてみた"
date: 2020-02-16T20:10:48+09:00
draft: true
---

## はじめに

[スワップの弁護：よくある誤解を解く](https://chrisdown.name/ja/2018/01/02/in-defence-of-swap.html) と [大規模システムでの Linux のメモリ管理](https://chrisdown.name/ja/2019/07/18/linux-memory-management-at-scale.html) を読んで Linux のスワップについて理解を深めたところで、実際のコードを読んでみることにしました。今回のリーディングの対象バージョンは [torvalds/linux at v5.6-rc1](https://github.com/torvalds/linux/tree/v5.6-rc1) です。

なお、私は上記の記事以外の前提知識が無い状態で初めて読んでみたところなので、誤読しているかもしれません。あまり信用せず、おかしい箇所があったらご自分で確認してください。

## `vm_swappiness` の検索結果

```console
$ ag vm_swappiness
mm/vmscan.c
166:int vm_swappiness = 60;

mm/memcontrol.c
3827:           vm_swappiness = val;

include/uapi/linux/sysctl.h
182:    VM_SWAPPINESS=19,       /* Tendency to steal mapped memory */

include/linux/swap.h
364:extern int vm_swappiness;
633:            return vm_swappiness;
637:            return vm_swappiness;
644:    return vm_swappiness;

kernel/sysctl.c
1410:           .data           = &vm_swappiness,
1411:           .maxlen         = sizeof(vm_swappiness),
```

## sysctl の `vm_swappiness` の定義

[include/uapi/linux/sysctl.h#L182](https://github.com/torvalds/linux/blob/v5.6-rc1/include/uapi/linux/sysctl.h#L182)

`CTL_VM names` の enum に `VM_SWAPPINESS` が含まれていました。

```c
  VM_SWAPPINESS=19, /* Tendency to steal mapped memory */
```

[kernel/sysctl.c#L1408-L1416](https://github.com/torvalds/linux/blob/v5.6-rc1/kernel/sysctl.c#L1408-L1416)

`static struct ctl_table vm_table[]` の配列要素の 1 つに `swappiness` の設定の定義がありました。

```c
  {
    .procname = "swappiness",
    .data   = &vm_swappiness,
    .maxlen   = sizeof(vm_swappiness),
    .mode   = 0644,
    .proc_handler = proc_dointvec_minmax,
    .extra1   = SYSCTL_ZERO,
    .extra2   = &one_hundred,
  },
```

## `vm_swappiness` は `mem_cgroup_swappiness_write` 関数で設定

[mm/memcontrol.c#L3816-L3830](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/memcontrol.c#L3816-L3830)

`mem_cgroup_swappiness_write` 関数の中で `vm_swappiness` を設定しています。
`css->parent` の値によっては `vm_swapiness` の代わりに `memcg->swapiness` を設定しています。
メモリ cgroup にも swapiness の設定があるんですね。

```c
static int mem_cgroup_swappiness_write(struct cgroup_subsys_state *css,
				       struct cftype *cft, u64 val)
{
	struct mem_cgroup *memcg = mem_cgroup_from_css(css);

	if (val > 100)
		return -EINVAL;

	if (css->parent)
		memcg->swappiness = val;
	else
		vm_swappiness = val;

	return 0;
}
```

## `vm_swappiness` は `mem_cgroup_swappiness` 関数で参照

[include/linux/swap.h#L628-L646](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/swap.h#L628-L646)

ビルド時の設定で `CONFIG_MEMCG` が定義されている場合は、条件によってメモリ cgroup の swapiness あるいはグローバルの `vm_swappiness` を参照することが分かります。

```c
#ifdef CONFIG_MEMCG
static inline int mem_cgroup_swappiness(struct mem_cgroup *memcg)
{
	/* Cgroup2 doesn't have per-cgroup swappiness */
	if (cgroup_subsys_on_dfl(memory_cgrp_subsys))
		return vm_swappiness;

	/* root ? */
	if (mem_cgroup_disabled() || mem_cgroup_is_root(memcg))
		return vm_swappiness;

	return memcg->swappiness;
}
#else
static inline int mem_cgroup_swappiness(struct mem_cgroup *mem)
{
	return vm_swappiness;
}
#endif
```

## `vm_swappiness` のデフォルト値は 60

[mm/vmscan.c#L163-L166](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L163-L166)

グローバル変数の `vm_swappiness` の宣言箇所でデフォルト値の 60 を設定しています。
```c
/*
 * From 0 .. 100.  Higher means more swappy.
 */
int vm_swappiness = 60;
```

## `get_scan_count` 関数

[mm/vmscan.c#L2221-L2439](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2221-L2439)

長いので分割して引用します。

### 関数のコメントとシグネチャ

[mm/vmscan.c#L2221-L2232](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2221-L2232)

冒頭のコメントによると anonymous と file メモリの LRU リストをどれぐらいアグレッシブにスキャンするかを決定する関数だそうです。

```c
/*
 * Determine how aggressively the anon and file LRU lists should be
 * scanned.  The relative value of each set of LRU lists is determined
 * by looking at the fraction of the pages scanned we did rotate back
 * onto the active list instead of evict.
 *
 * nr[0] = anon inactive pages to scan; nr[1] = anon active pages to scan
 * nr[2] = file inactive pages to scan; nr[3] = file active pages to scan
 */
static void get_scan_count(struct lruvec *lruvec, struct scan_control *sc,
			   unsigned long *nr)
{
```

### 関数内のローカル変数宣言

[mm/vmscan.c#L2233-L2244](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2233-L2244)

上述の `mem_cgroup_swappiness` 関数で値を取得してローカル変数の `swappiness` に設定しています。

```c
	struct mem_cgroup *memcg = lruvec_memcg(lruvec);
	int swappiness = mem_cgroup_swappiness(memcg);
	struct zone_reclaim_stat *reclaim_stat = &lruvec->reclaim_stat;
	u64 fraction[2];
	u64 denominator = 0;	/* gcc */
	struct pglist_data *pgdat = lruvec_pgdat(lruvec);
	unsigned long anon_prio, file_prio;
	enum scan_balance scan_balance;
	unsigned long anon, file;
	unsigned long ap, fp;
	enum lru_list lru;

```

### `enum scan_balance`

`enum scan_balance` の定義は `get_scan_count` 関数の上にあります。

[mm/vmscan.c#L2214-L2219](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2214-L2219)

```c
enum scan_balance {
	SCAN_EQUAL,
	SCAN_FRACT,
	SCAN_ANON,
	SCAN_FILE,
};
```

次項の `get_scan_count` 関数の「条件に応じた `scan_balance` の設定」の箇所を見た感じでは以下のような意味のようです。

* `SCAN_EQUAL`: anonymous メモリと file メモリを同程度に回収する。
* `SCAN_FRACT`: `swapiness` の値に応じた割合で anonymous メモリと file メモリを回収する。 FRACT は fraction (割合) の略。
* `SCAN_ANON`: anonymous メモリを優先で回収する。
* `SCAN_FILE`: file メモリを優先で回収する。

### 条件に応じた `scan_balance` の設定

[mm/vmscan.c#L2245-L2298](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2245-L2298)

以下のコードを見ると様々な条件によって `scan_balance` が選択されることが分かります。
`swapiness` の設定値 0～100 のうち 0 だけ特別扱いされるのも 2 箇所あります。

[スワップの弁護：よくある誤解を解く](https://chrisdown.name/ja/2018/01/02/in-defence-of-swap.html) の記事の「swappiness の設定はどうするべきでしょうか？」の項にあった swappiness の値がそのまま `anon_prio` になり、 `file_prio` は `200 - swappiness` になるというのは下記の引用の最後に出てきます。これは `scan_balance` が `SCAN_FRACT` の場合の話だったんですね。

```c
	/* If we have no swap space, do not bother scanning anon pages. */
	if (!sc->may_swap || mem_cgroup_get_nr_swap_pages(memcg) <= 0) {
		scan_balance = SCAN_FILE;
		goto out;
	}

	/*
	 * Global reclaim will swap to prevent OOM even with no
	 * swappiness, but memcg users want to use this knob to
	 * disable swapping for individual groups completely when
	 * using the memory controller's swap limit feature would be
	 * too expensive.
	 */
	if (cgroup_reclaim(sc) && !swappiness) {
		scan_balance = SCAN_FILE;
		goto out;
	}

	/*
	 * Do not apply any pressure balancing cleverness when the
	 * system is close to OOM, scan both anon and file equally
	 * (unless the swappiness setting disagrees with swapping).
	 */
	if (!sc->priority && swappiness) {
		scan_balance = SCAN_EQUAL;
		goto out;
	}

	/*
	 * If the system is almost out of file pages, force-scan anon.
	 */
	if (sc->file_is_tiny) {
		scan_balance = SCAN_ANON;
		goto out;
	}

	/*
	 * If there is enough inactive page cache, we do not reclaim
	 * anything from the anonymous working right now.
	 */
	if (sc->cache_trim_mode) {
		scan_balance = SCAN_FILE;
		goto out;
	}

	scan_balance = SCAN_FRACT;

	/*
	 * With swappiness at 100, anonymous and file have the same priority.
	 * This scanning priority is essentially the inverse of IO cost.
	 */
	anon_prio = swappiness;
	file_prio = 200 - anon_prio;

```

[mm/vmscan.c#L2299-L2341](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2299-L2341)

`scan_balance` が `SCAN_FRACT` に annoymous メモリと file メモリを回収する「圧力」を計算する。

```c
	/*
	 * OK, so we have swap space and a fair amount of page cache
	 * pages.  We use the recently rotated / recently scanned
	 * ratios to determine how valuable each cache is.
	 *
	 * Because workloads change over time (and to avoid overflow)
	 * we keep these statistics as a floating average, which ends
	 * up weighing recent references more than old ones.
	 *
	 * anon in [0], file in [1]
	 */

	anon  = lruvec_lru_size(lruvec, LRU_ACTIVE_ANON, MAX_NR_ZONES) +
		lruvec_lru_size(lruvec, LRU_INACTIVE_ANON, MAX_NR_ZONES);
	file  = lruvec_lru_size(lruvec, LRU_ACTIVE_FILE, MAX_NR_ZONES) +
		lruvec_lru_size(lruvec, LRU_INACTIVE_FILE, MAX_NR_ZONES);

	spin_lock_irq(&pgdat->lru_lock);
	if (unlikely(reclaim_stat->recent_scanned[0] > anon / 4)) {
		reclaim_stat->recent_scanned[0] /= 2;
		reclaim_stat->recent_rotated[0] /= 2;
	}

	if (unlikely(reclaim_stat->recent_scanned[1] > file / 4)) {
		reclaim_stat->recent_scanned[1] /= 2;
		reclaim_stat->recent_rotated[1] /= 2;
	}

	/*
	 * The amount of pressure on anon vs file pages is inversely
	 * proportional to the fraction of recently scanned pages on
	 * each list that were recently referenced and in active use.
	 */
	ap = anon_prio * (reclaim_stat->recent_scanned[0] + 1);
	ap /= reclaim_stat->recent_rotated[0] + 1;

	fp = file_prio * (reclaim_stat->recent_scanned[1] + 1);
	fp /= reclaim_stat->recent_rotated[1] + 1;
	spin_unlock_irq(&pgdat->lru_lock);

	fraction[0] = ap;
	fraction[1] = fp;
	denominator = ap + fp + 1;
```

### `enum lru_list`

先に進む前にローカル変数宣言の `lru` について確認します。

```c
	enum lru_list lru;
```

[include/linux/mmzone.h#L249-L273](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/mmzone.h#L249-L273)

anonymous, file メモリのそれぞれに inactive と active な LRU リストと unevictable (退去不可、つまりスワップできない) LRU リストがあることが分かります。

次項で出てくる `for_each_evictable_lru` マクロの定義を見ると `LRU_INACTIVE_ANON`, `LRU_ACTIVE_ANON`, `LRU_INACTIVE_FILE`, `LRU_ACTIVE_FILE` の 4 つについて `for` ループで回すことが分かります。

```c
/*
 * We do arithmetic on the LRU lists in various places in the code,
 * so it is important to keep the active lists LRU_ACTIVE higher in
 * the array than the corresponding inactive lists, and to keep
 * the *_FILE lists LRU_FILE higher than the corresponding _ANON lists.
 *
 * This has to be kept in sync with the statistics in zone_stat_item
 * above and the descriptions in vmstat_text in mm/vmstat.c
 */
#define LRU_BASE 0
#define LRU_ACTIVE 1
#define LRU_FILE 2

enum lru_list {
	LRU_INACTIVE_ANON = LRU_BASE,
	LRU_ACTIVE_ANON = LRU_BASE + LRU_ACTIVE,
	LRU_INACTIVE_FILE = LRU_BASE + LRU_FILE,
	LRU_ACTIVE_FILE = LRU_BASE + LRU_FILE + LRU_ACTIVE,
	LRU_UNEVICTABLE,
	NR_LRU_LISTS
};

#define for_each_lru(lru) for (lru = 0; lru < NR_LRU_LISTS; lru++)

#define for_each_evictable_lru(lru) for (lru = 0; lru <= LRU_ACTIVE_FILE; lru++)
```

### `lru` についてのループ処理その1

[mm/vmscan.c#L2342-L2352](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2342-L2352)

`scan_balance` のすべての値に共通な処理。 `lru` のそれぞれについてループしています。
まずループの開始部分。

```c
out:
	for_each_evictable_lru(lru) {
		int file = is_file_lru(lru);
		unsigned long lruvec_size;
		unsigned long scan;
		unsigned long protection;

		lruvec_size = lruvec_lru_size(lruvec, lru, sc->reclaim_idx);
		protection = mem_cgroup_protection(memcg,
						   sc->memcg_low_reclaim);

```

### `mem_cgroup_protection` 関数

[include/linux/memcontrol.h#L64](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/memcontrol.h#L64)

```c
#ifdef CONFIG_MEMCG
```

上記の `CONFIG_MEMCG` が定義されている場合の `mem_cgroup_protection` 関数の実装。
[include/linux/memcontrol.h#L347-L358](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/memcontrol.h#L347-L358)

* メモリ cgroup が無効な場合は 0 になる
* メモリ cgroup が有効な場合
    - `in_low_reclaim` が `true` の場合は `memcg->memory.emin` の値になる
    - `in_low_reclaim` が `false` の場合は `memcg->memory.emin` と `memcg->memory.elow)` の大きいほうの値になる

```c
static inline unsigned long mem_cgroup_protection(struct mem_cgroup *memcg,
						  bool in_low_reclaim)
{
	if (mem_cgroup_disabled())
		return 0;

	if (in_low_reclaim)
		return READ_ONCE(memcg->memory.emin);

	return max(READ_ONCE(memcg->memory.emin),
		   READ_ONCE(memcg->memory.elow));
}
```

上記の `CONFIG_MEMCG` が定義されていない場合の `mem_cgroup_protection` 関数の実装。

[include/linux/memcontrol.h#L837-L841](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/memcontrol.h#L837-L841)

```c
static inline unsigned long mem_cgroup_protection(struct mem_cgroup *memcg,
						  bool in_low_reclaim)
{
	return 0;
}
```

### `lru` についてのループ処理その2


[mm/vmscan.c#L2353-L2402](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2353-L2402)

前項の `mem_cgroup_protection` 関数で返された `protection` が 0 以外か 0 かに応じて異なるルールで `scan` の値が一旦設定された後、 `sc->priority` の値で調整されます。

```c
		if (protection) {
			/*
			 * Scale a cgroup's reclaim pressure by proportioning
			 * its current usage to its memory.low or memory.min
			 * setting.
			 *
			 * This is important, as otherwise scanning aggression
			 * becomes extremely binary -- from nothing as we
			 * approach the memory protection threshold, to totally
			 * nominal as we exceed it.  This results in requiring
			 * setting extremely liberal protection thresholds. It
			 * also means we simply get no protection at all if we
			 * set it too low, which is not ideal.
			 *
			 * If there is any protection in place, we reduce scan
			 * pressure by how much of the total memory used is
			 * within protection thresholds.
			 *
			 * There is one special case: in the first reclaim pass,
			 * we skip over all groups that are within their low
			 * protection. If that fails to reclaim enough pages to
			 * satisfy the reclaim goal, we come back and override
			 * the best-effort low protection. However, we still
			 * ideally want to honor how well-behaved groups are in
			 * that case instead of simply punishing them all
			 * equally. As such, we reclaim them based on how much
			 * memory they are using, reducing the scan pressure
			 * again by how much of the total memory used is under
			 * hard protection.
			 */
			unsigned long cgroup_size = mem_cgroup_size(memcg);

			/* Avoid TOCTOU with earlier protection check */
			cgroup_size = max(cgroup_size, protection);

			scan = lruvec_size - lruvec_size * protection /
				cgroup_size;

			/*
			 * Minimally target SWAP_CLUSTER_MAX pages to keep
			 * reclaim moving forwards, avoiding decremeting
			 * sc->priority further than desirable.
			 */
			scan = max(scan, SWAP_CLUSTER_MAX);
		} else {
			scan = lruvec_size;
		}

		scan >>= sc->priority;

```

### `lru` についてのループ処理その3

[mm/vmscan.c#L2403-L2409](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2403-L2409)

```c
		/*
		 * If the cgroup's already been deleted, make sure to
		 * scrape out the remaining cache.
		 */
		if (!scan && !mem_cgroup_online(memcg))
			scan = min(lruvec_size, SWAP_CLUSTER_MAX);

```

### `mem_cgroup_online` 関数

[include/linux/memcontrol.h#L514-L519](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/memcontrol.h#L514-L519)

`CONFIG_MEMCG` が定義されている場合の `mem_cgroup_online` 関数の実装。

```c
static inline bool mem_cgroup_online(struct mem_cgroup *memcg)
{
	if (mem_cgroup_disabled())
		return true;
	return !!(memcg->css.flags & CSS_ONLINE);
}
```

[include/linux/memcontrol.h#L970-L973](https://github.com/torvalds/linux/blob/v5.6-rc1/include/linux/memcontrol.h#L970-L973)

`CONFIG_MEMCG` が定義されていない場合の `mem_cgroup_online` 関数の実装。

```c
static inline bool mem_cgroup_online(struct mem_cgroup *memcg)
{
	return true;
}
```

### `lru` についてのループ処理その4

[mm/vmscan.c#L2410-L2439](https://github.com/torvalds/linux/blob/v5.6-rc1/mm/vmscan.c#L2410-L2439)

```c
		switch (scan_balance) {
		case SCAN_EQUAL:
			/* Scan lists relative to size */
			break;
		case SCAN_FRACT:
			/*
			 * Scan types proportional to swappiness and
			 * their relative recent reclaim efficiency.
			 * Make sure we don't miss the last page
			 * because of a round-off error.
			 */
			scan = DIV64_U64_ROUND_UP(scan * fraction[file],
						  denominator);
			break;
		case SCAN_FILE:
		case SCAN_ANON:
			/* Scan one type exclusively */
			if ((scan_balance == SCAN_FILE) != file) {
				lruvec_size = 0;
				scan = 0;
			}
			break;
		default:
			/* Look ma, no brain */
			BUG();
		}

		nr[lru] = scan;
	}
}
```

上記のループの最後で `nr[lru]` に値を設定していて、これは `get_scan_count` 関数の前のコメントの下記の部分に対応しています。 `nr` は number の略でコメントと合わせると LRU の種別毎にスキャンするページ数ということのようです。

```c
 * nr[0] = anon inactive pages to scan; nr[1] = anon active pages to scan
 * nr[2] = file inactive pages to scan; nr[3] = file active pages to scan
```

`get_scan_count` 関数で設定した `nr` の値を使ってページをスキャンする処理のほうも気になりますが、長くなってきたので今回はこの辺で。
