---
title: "HAProxyのserver stateについてコードリーディング"
date: 2022-12-15T19:52:54+09:00
---
## はじめに

kazeburoさんの[ツイート](https://twitter.com/kazeburo/status/1603243011038552064)を見て興味が湧いたのでちょっと見てみました。なお私自身は普段HAProxy使ってないです。

リーディング対象は https://github.com/haproxy/haproxy/commit/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0 です。

なお以下のコードの引用ではインデントが深い行は適宜調整しています。

## コードリーディング

まず UP 1/3 の文字列を組み立てている箇所を探してみます。

```
$ rg '"UP '
src/stats.c
2045:   [SRV_STATS_STATE_UP_GOING_DOWN]         = "UP %d/%d",

src/check.c
958:                                  "UP %d/%d", "UP",
```

### stats.c

https://github.com/haproxy/haproxy/blob/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0/src/stats.c#L2025-L2053

```c
enum srv_stats_state {
	SRV_STATS_STATE_DOWN = 0,
	SRV_STATS_STATE_DOWN_AGENT,
	SRV_STATS_STATE_GOING_UP,
	SRV_STATS_STATE_UP_GOING_DOWN,
	SRV_STATS_STATE_UP,
	SRV_STATS_STATE_NOLB_GOING_DOWN,
	SRV_STATS_STATE_NOLB,
	SRV_STATS_STATE_DRAIN_GOING_DOWN,
	SRV_STATS_STATE_DRAIN,
	SRV_STATS_STATE_DRAIN_AGENT,
	SRV_STATS_STATE_NO_CHECK,

	SRV_STATS_STATE_COUNT, /* Must be last */
};

static const char *srv_hlt_st[SRV_STATS_STATE_COUNT] = {
	[SRV_STATS_STATE_DOWN]			= "DOWN",
	[SRV_STATS_STATE_DOWN_AGENT]		= "DOWN (agent)",
	[SRV_STATS_STATE_GOING_UP]		= "DOWN %d/%d",
	[SRV_STATS_STATE_UP_GOING_DOWN]		= "UP %d/%d",
	[SRV_STATS_STATE_UP]			= "UP",
	[SRV_STATS_STATE_NOLB_GOING_DOWN]	= "NOLB %d/%d",
	[SRV_STATS_STATE_NOLB]			= "NOLB",
	[SRV_STATS_STATE_DRAIN_GOING_DOWN]	= "DRAIN %d/%d",
	[SRV_STATS_STATE_DRAIN]			= "DRAIN",
	[SRV_STATS_STATE_DRAIN_AGENT]		= "DRAIN (agent)",
	[SRV_STATS_STATE_NO_CHECK]		= "no check"
};
```

`enum srv_stats_state`が`SRV_STATS_STATE_UP_GOING_DOWN`に`"UP %d/%d"`という文字列が対応しています。

`srv_hlt_st` で検索してみると`/`の前後の値を指定している箇所がありました。

https://github.com/haproxy/haproxy/blob/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0/src/stats.c#L2242-L2245

```c
chunk_appendf(out,
  srv_hlt_st[state],
  (ref->cur_state != SRV_ST_STOPPED) ? (ref->check.health - ref->check.rise + 1) : (ref->check.health),
  (ref->cur_state != SRV_ST_STOPPED) ? (ref->check.fall) : (ref->check.rise));
```

`SRV_ST_STOPPED`の定義を見ると`enum srv_state`の中にありました。

https://github.com/haproxy/haproxy/blob/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0/include/haproxy/server-t.h#L46-L52
```c
/* server states. Only SRV_ST_STOPPED indicates a down server. */
enum srv_state {
	SRV_ST_STOPPED = 0,              /* the server is down. Please keep set to zero. */
	SRV_ST_STARTING,                 /* the server is warming up (up but throttled) */
	SRV_ST_RUNNING,                  /* the server is fully up */
	SRV_ST_STOPPING,                 /* the server is up but soft-stopping (eg: 404) */
} __attribute__((packed));
```

`SRV_STATS_STATE_UP_GOING_DOWN`はおそらく`SRV_ST_STOPPING`だろうということで、`"UP %d/%d"`の`/`の前は`ref->check.health - ref->check.rise + 1`、`/`の後は`ref->check.fall`になりそうです。

`health`, `fall`, `rise`フィールドの定義は`struct check`内にありました。
https://github.com/haproxy/haproxy/blob/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0/include/haproxy/check-t.h#L171-L173

```c
	int health;				/* 0 to rise-1 = bad;
						 * rise to rise+fall-1 = good */
	int rise, fall;				/* time in iterations */
```

HAProxy "server status" rise fallとかで検索すると[Using HAProxy as an API Gateway, Part 3 \[Health Checks\] - HAProxy Technologies](https://www.haproxy.com/blog/using-haproxy-as-an-api-gateway-part-3-health-checks/)にriseとfallの説明がありました。

```
fall 	The number of failed checks before marking the server as down.
rise 	The number of successful checks before marking a server as up again.
```

### check.c

`"UP `の文字列があるのは以下の箇所です。
https://github.com/haproxy/haproxy/blob/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0/src/check.c#L950-L981

```c
/* Builds the server state header used by HTTP health-checks */
int httpchk_build_status_header(struct server *s, struct buffer *buf)
{
	int sv_state;
	int ratio;
	char addr[46];
	char port[6];
	const char *srv_hlt_st[7] = { "DOWN", "DOWN %d/%d",
				      "UP %d/%d", "UP",
				      "NOLB %d/%d", "NOLB",
				      "no check" };

	if (!(s->check.state & CHK_ST_ENABLED))
		sv_state = 6;
	else if (s->cur_state != SRV_ST_STOPPED) {
		if (s->check.health == s->check.rise + s->check.fall - 1)
			sv_state = 3; /* UP */
		else
			sv_state = 2; /* going down */

		if (s->cur_state == SRV_ST_STOPPING)
			sv_state += 2;
	} else {
		if (s->check.health)
			sv_state = 1; /* going up */
		else
			sv_state = 0; /* DOWN */
	}

	chunk_appendf(buf, srv_hlt_st[sv_state],
		      (s->cur_state != SRV_ST_STOPPED) ? (s->check.health - s->check.rise + 1) : (s->check.health),
		      (s->cur_state != SRV_ST_STOPPED) ? (s->check.fall) : (s->check.rise));
```

`"UP %d/%d"`に対応するのは`sv_state = 2; /* going down */`のケースです。`chunk_appendf`で引数に指定している`/`の前後の数は`stats.c`と同じです。

`health =`の箇所を見ていたら`set_server_check_status`という関数内に`health`の値を増減している箇所が見つかりました。
https://github.com/haproxy/haproxy/blob/c4913f6b54e8b323b9ecbd2a711b2cbf486afae0/src/check.c#L486-L519

ヘルスチェックに成功すると増えて失敗すると減るようになっています。

```c
	switch (check->result) {
	case CHK_RES_FAILED:
		/* Failure to connect to the agent as a secondary check should not
		 * cause the server to be marked down.
		 */
		if ((!(check->state & CHK_ST_AGENT) ||
		    (check->status >= HCHK_STATUS_L57DATA)) &&
		    (check->health > 0)) {
			_HA_ATOMIC_INC(&s->counters.failed_checks);
			report = 1;
			check->health--;
			if (check->health < check->rise)
				check->health = 0;
		}
		break;

	case CHK_RES_PASSED:
	case CHK_RES_CONDPASS:
		if (check->health < check->rise + check->fall - 1) {
			report = 1;
			check->health++;

			if (check->health >= check->rise)
				check->health = check->rise + check->fall - 1; /* OK now */
		}

		/* clear consecutive_errors if observing is enabled */
		if (s->onerror)
			HA_ATOMIC_STORE(&s->consecutive_errors, 0);
		break;

	default:
		break;
	}
```

これを踏まえてもう一度

```
(s->cur_state != SRV_ST_STOPPED) ? (s->check.health - s->check.rise + 1) : (s->check.health),
(s->cur_state != SRV_ST_STOPPED) ? (s->check.fall) : (s->check.rise));
```

のコードを見ると、理解しやすいのは`s->cur_state != SRV_ST_STOPPED`が`false`のケース(`:`の右側)、つまり分子が`health`で分母が`rise`です。こちらは`rise`回ヘルスチェックが成功したらサーバを起動状態(up)とマークするけど現在はそのうち`health`回成功したという状況ということですね。

`s->cur_state != SRV_ST_STOPPED`が`true`のケース(`:`の左側)、つまり分子が`health-rise+1`で分母が`fall`です。こちらは分母の方は`fall`回ヘルスチェックが失敗したらサーバを停止状態(down)とマークすることを意味しているのでしょうが、分子はちょっと複雑です。

上のコードに
```
			if (check->health >= check->rise)
				check->health = check->rise + check->fall - 1; /* OK now */
```
という箇所があって`health`の最大値を`rise+fall-1`にしています。

`struct check`の`health`フィールドのコメントにも

```c
	int health;				/* 0 to rise-1 = bad;
						 * rise to rise+fall-1 = good */
```

とあるので最大値は一致しています。ここから`fall`を引いた`rise-1`まで`health`が下がるとdownになるけど、そこまであと何回猶予があるかというのが`health-(rise-1)`つまり`health-rise+1`になるということですね。　

というわけで`UP 1/3`はあと一回ヘルスチェックが失敗したらDOWNになる状態だと思われます。
