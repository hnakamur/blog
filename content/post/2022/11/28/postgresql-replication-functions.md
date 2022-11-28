---
title: "PostgreSQLのレプリケーション関連の関数についてメモ"
date: 2022-11-28T21:25:10+09:00
---
## はじめに

[［改訂3版］内部構造から学ぶPostgreSQL ―設計・運用計画の鉄則 | Gihyo Digital Publishing](https://gihyo.jp/dp/ebook/2022/978-4-297-13207-1) の「11.5.2：プライマリ／スタンバイの監視」を読んで知ったPostgreSQLのレプリケーション関連の関数についてコードリーディングしたメモです。

## [9.27.4. Recovery Control Functions](https://www.postgresql.org/docs/15/functions-admin.html#FUNCTIONS-RECOVERY-CONTROL)

* `pg_is_in_recovery` [src/backend/access/transam/xlogfuncs.c#L540-L547](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogfuncs.c#L540-L547)
    * `RecoveryInProgress` [src/backend/access/transam/xlog.c#L5769-L5803](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L5769-L5803)
* `pg_last_wal_receive_lsn` [src/backend/access/transam/xlogfuncs.c#L281-L298)
](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogfuncs.c#L281-L298)
    * `GetWalRcvFlushRecPtr` [src/backend/replication/walreceiverfuncs.c#L323-L346](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/replication/walreceiverfuncs.c#L323-L346)
        * `recptr = walrcv->flushedUpto;`
        * `WalRcvData` [src/include/replication/walreceiver.h#L56-L161](https://github.com/postgres/postgres/blob/REL_15_1/src/include/replication/walreceiver.h#L56-L161)

```c
/* Shared memory area for management of walreceiver process */
typedef struct
{
//…(略)…
	/*
	 * receiveStart and receiveStartTLI indicate the first byte position and
	 * timeline that will be received. When startup process starts the
	 * walreceiver, it sets these to the point where it wants the streaming to
	 * begin.
	 */
	XLogRecPtr	receiveStart;
	TimeLineID	receiveStartTLI;

	/*
	 * flushedUpto-1 is the last byte position that has already been received,
	 * and receivedTLI is the timeline it came from.  At the first startup of
	 * walreceiver, these are set to receiveStart and receiveStartTLI. After
	 * that, walreceiver updates these whenever it flushes the received WAL to
	 * disk.
	 */
	XLogRecPtr	flushedUpto;
	TimeLineID	receivedTLI;
//…(略)…
} WalRcvData;
```

* `pg_last_wal_replay_lsn` [src/backend/access/transam/xlogfuncs.c#L300-L317](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogfuncs.c#L300-L317)
    * `GetXLogReplayRecPtr` [src/backend/access/transam/xlogrecovery.c#L4469-L4488](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogrecovery.c#L4469-L4488)
        * `recptr = XLogRecoveryCtl->lastReplayedEndRecPtr;`
        * `XLogRecoveryCtlData` [src/backend/access/transam/xlogrecovery.c#L299-L360](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogrecovery.c#L299-L360)

```c
/*
 * Shared-memory state for WAL recovery.
 */
typedef struct XLogRecoveryCtlData
//…(略)…
	/*
	 * Last record successfully replayed.
	 */
	XLogRecPtr	lastReplayedReadRecPtr; /* start position */
	XLogRecPtr	lastReplayedEndRecPtr;	/* end+1 position */
	TimeLineID	lastReplayedTLI;	/* timeline */
```

## [9.27.3. Backup Control Functions](https://www.postgresql.org/docs/15/functions-admin.html#FUNCTIONS-ADMIN-BACKUP)

* `pg_current_wal_flush_lsn` [src/backend/access/transam/xlogfuncs.c#L260-L279](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogfuncs.c#L260-L279)
    * `GetFlushRecPtr` [src/backend/access/transam/xlog.c#L5935-L5957](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L5935-L5957)
        * `LogwrtResult = XLogCtl->LogwrtResult;`
        * `return LogwrtResult.Flush;`
        * `XLogCtlData` [src/backend/access/transam/xlog.c#L452-L556](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L452-L556)
* `pg_current_wal_insert_lsn` [src/backend/access/transam/xlogfuncs.c#L239-L258](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogfuncs.c#L239-L258)
    * `GetXLogInsertRecPtr` [src/backend/access/transam/xlog.c#L8819-L8833](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L8819-L8833)
        * `XLogCtlInsert *Insert = &XLogCtl->Insert;`
        * `current_bytepos = Insert->CurrBytePos;`
        * `XLogCtlInsert` [src/backend/access/transam/xlog.c#L396-L450](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L396-L450)
* `pg_current_wal_lsn` [src/backend/access/transam/xlogfuncs.c#L216-L237](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlogfuncs.c#L216-L237)
    * `GetXLogWriteRecPtr` [src/backend/access/transam/xlog.c#L8835-L8846](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L8835-L8846)
        * `LogwrtResult = XLogCtl->LogwrtResult;`
        * `return LogwrtResult.Write;`

`XLogCtlInsert` の `CurrBytePos` フィールド [postgres/xlog.c at REL_15_1 · postgres/postgres](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L396-L411)

```c
/*
 * Shared state data for WAL insertion.
 */
typedef struct XLogCtlInsert
//…(略)…
	/*
	 * CurrBytePos is the end of reserved WAL. The next record will be
	 * inserted at that position. PrevBytePos is the start position of the
	 * previously inserted (or rather, reserved) record - it is copied to the
	 * prev-link of the next record. These are stored as "usable byte
	 * positions" rather than XLogRecPtrs (see XLogBytePosToRecPtr()).
	 */
	uint64		CurrBytePos;
	uint64		PrevBytePos;
```

`XLogCtlData` の `LogwrtResult` フィールド [src/backend/access/transam/xlog.c#L476-L480](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L476-L480)

```c
/*
 * Total shared-memory state for XLOG.
 */
typedef struct XLogCtlData
//…(略)…
	/*
	 * Protected by info_lck and WALWriteLock (you must hold either lock to
	 * read it, but both to update)
	 */
	XLogwrtResult LogwrtResult;
```

`XLogwrtResult` [src/backend/access/transam/xlog.c#L328-L332](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/access/transam/xlog.c#L328-L332)

```c
typedef struct XLogwrtResult
{
	XLogRecPtr	Write;			/* last byte + 1 written out */
	XLogRecPtr	Flush;			/* last byte + 1 flushed */
} XLogwrtResult;
```

## [28.2. The Cumulative Statistics System](https://www.postgresql.org/docs/current/monitoring-stats.html)

* `pg_stat_replication` [src/backend/catalog/system_views.sql#L871-L895](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/catalog/system_views.sql#L871-L895)
    * `pg_stat_get_wal_senders` [src/backend/replication/walsender.c#L3466-L3628](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/replication/walsender.c#L3466-L3628)

```c
/*
 * Returns activity of walsenders, including pids and xlog locations sent to
 * standby servers.
 */
Datum
pg_stat_get_wal_senders(PG_FUNCTION_ARGS)
{
//…(略)…
	for (i = 0; i < max_wal_senders; i++)
	{
		WalSnd	   *walsnd = &WalSndCtl->walsnds[i];
		XLogRecPtr	sentPtr;
		XLogRecPtr	write;
		XLogRecPtr	flush;
		XLogRecPtr	apply;
//…(略)…
		sentPtr = walsnd->sentPtr;
		state = walsnd->state;
		write = walsnd->write;
		flush = walsnd->flush;
		apply = walsnd->apply;
```

`WalSnd` [src/include/replication/walsender_private.h#L31-L81](https://github.com/postgres/postgres/blob/REL_15_1/src/include/replication/walsender_private.h#L31-L81)

```c
/*
 * Each walsender has a WalSnd struct in shared memory.
 *
 * This struct is protected by its 'mutex' spinlock field, except that some
 * members are only written by the walsender process itself, and thus that
 * process is free to read those members without holding spinlock.  pid and
 * needreload always require the spinlock to be held for all accesses.
 */
typedef struct WalSnd
//…(略)…
	/*
	 * The xlog locations that have been written, flushed, and applied by
	 * standby-side. These may be invalid if the standby-side has not offered
	 * values yet.
	 */
	XLogRecPtr	write;
	XLogRecPtr	flush;
	XLogRecPtr	apply;
```

* `pg_stat_wal_receiver` [src/backend/catalog/system_views.sql#L910-L928](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/catalog/system_views.sql#L910-L928)
    * `pg_stat_get_wal_receiver` [src/backend/replication/walreceiver.c#L1335-L1469](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/replication/walreceiver.c#L1335-L1469)
        * `WalRcvData *WalRcv = NULL;` [src/backend/replication/walreceiverfuncs.c#L34](https://github.com/postgres/postgres/blob/REL_15_1/src/backend/replication/walreceiverfuncs.c#L34)

```c
/*
 * Returns activity of WAL receiver, including pid, state and xlog locations
 * received from the WAL sender of another server.
 */
Datum
pg_stat_get_wal_receiver(PG_FUNCTION_ARGS)
//…(略)…
	receive_start_lsn = WalRcv->receiveStart;
	receive_start_tli = WalRcv->receiveStartTLI;
	flushed_lsn = WalRcv->flushedUpto;
	received_tli = WalRcv->receivedTLI;
```
