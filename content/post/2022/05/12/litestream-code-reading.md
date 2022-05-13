---
title: "Litestreamのコードリーディング"
date: 2022-05-12T18:18:49+09:00
---

## はじめに
対象バージョン
https://github.com/benbjohnson/litestream/tree/e6f7c6052d84b7265fd54d3a3ab33208948e126b

replicate と restore のコードを読んで見る。
順を追って全部書くのは大変なので気になったところだけメモ。

次回: [Litestreamのコードリーディングその2](/blog/2022/05/13/litestream-code-reading2/)

## replicate と restore のログ出力例

```
$ litestream replicate source.db file:///home/hnakamur/litestream-work/destination.db
litestream (development build)
initialized db: /home/hnakamur/litestream-work/source.db
replicating to: name="file" type="file" path="/home/hnakamur/litestream-work/destination.db"
litestream initialization complete
/home/hnakamur/litestream-work/source.db: init: no wal files available, clearing generation
/home/hnakamur/litestream-work/source.db: init: no wal files available, clearing generation
/home/hnakamur/litestream-work/source.db: sync: new generation "40e9bff6b361ab2f", no generation exists
/home/hnakamur/litestream-work/source.db(file): snapshot written 40e9bff6b361ab2f/0000000000000000
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/00000000
00000000:0000000000000000 sz=16512
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/0000000000000000:0000000000004080 sz=4120
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/0000000000000000:0000000000005098 sz=4120
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/0000000000000000:00000000000060b0 sz=4120
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/0000000000000000:00000000000070c8 sz=4120
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/0000000000000000:00000000000080e0 sz=4120
^Csignal received, litestream shutting down
/home/hnakamur/litestream-work/source.db: checkpoint(PASSIVE): [0,9,9]
/home/hnakamur/litestream-work/source.db(file): wal segment written: 40e9bff6b361ab2f/0000000000000001:0000000000000000 sz=4152
litestream shut down
```

```
$ litestream restore -o restored.db file:///home/hnakamur/litestream-work/destination.db
2022/05/12 18:10:26.394413 restoring snapshot 40e9bff6b361ab2f/0000000000000000 to restored.db.tmp
2022/05/12 18:10:26.404514 applied wal 40e9bff6b361ab2f/0000000000000000 elapsed=1.810673ms
2022/05/12 18:10:26.405770 applied wal 40e9bff6b361ab2f/0000000000000001 elapsed=1.237403ms
2022/05/12 18:10:26.405779 renaming database from temporary location
```

## データベースのオープン周り
### litestream-sqlite3 というカスタムのsqlドライバ

[litestream.go 内の init() 関数](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/litestream.go#L60-L69) で litestream-sqlite3 という名前のドライバを sql.Register で登録している。接続時のフックで `conn.SetFileControlInt("main", sqlite3.SQLITE_FCNTL_PERSIST_WAL, 1)` を呼んで WAL を閉じた後も消さないようにしている。

詳細は SQLite の レファレンス [SQLITE_FCNTL_PERSIST_WAL](https://www.sqlite.org/c3ref/c_fcntl_begin_atomic_write.html#sqlitefcntlpersistwal) 参照。

### データベースを開くのは 3 箇所

```
$ vgrep litestream-sqlite3
Index File          Line Content
    0 db.go          540 if db.db, err = sql.Open("litestream-sqlite3", dsn); err != nil {
    1 db.go          667 if db.db, err = sql.Open("litestream-sqlite3", dsn); err != nil {
    2 db.go         1880 d, err := sql.Open("litestream-sqlite3", dbPath)
    3 litestream.go   61 sql.Register("litestream-sqlite3", &sqlite3.SQLiteDriver{
```

* [Index 0](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L540) は DB.init メソッド内。
* [Index 1](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L667) は DB.initReplica メソッド内。
* [Index 2](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1880) は ApplyWAL 関数内。

### DB.init メソッド

```
// init initializes the connection to the database. Skipped if already
// initialized or if the database file does not exist.
```

[func (db *DB) init() (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L515-L646)

* DBファイル名に `?_busy_timeout=ビジータイムアウトのミリ秒` を追加したデータソース名で、データベースをオープン。
* 開いたら `PRAGMA journal_mode = wal;` を実行して WAL を使うよう設定 ([PRAGMA schema.journal_mode](https://www.sqlite.org/pragma.html#pragma_journal_mode) 参照)。
* `PRAGMA wal_autocheckpoint = 0;` を実行して autocheckpoint を無効化 ([PRAGMA wal_autocheckpoint](https://www.sqlite.org/pragma.html#pragma_wal_autocheckpoint) 参照)。
* `CREATE TABLE IF NOT EXISTS _litestream_seq (id INTEGER PRIMARY KEY, seq INTEGER);` を実行して `_litestream_seq` テーブルが存在しない場合は作成。
* `CREATE TABLE IF NOT EXISTS _litestream_lock (id INTEGER);` を実行して `_litestream_lock` テーブルが存在しない場合は作成。
* db.acquireReadLock を呼んで長い読み取りトランザクションを開始し、他のトランザクションがcheckpointを発行できないようにする。
    * db.acquireReadLock 内ではトランザクションを開始して `SELECT COUNT(1) FROM _litestream_seq;` のクエリを実行している。
* `PRAGMA page_size;` のクエリを実行してページサイズを取得 ([PRAGMA schema.page_size](https://www.sqlite.org/pragma.html#pragma_page_size) 参照)。
   * 取得したページサイズは `db.pageSize` に保管
* db.MetaPath() (DBのファイル名に `-litestream` を追加) のディレクトリ作成。
* db.invalidate() を呼んでDBファイルから位置、ソルト、チェックサムを読み取ってキャッシュ。
* db.verifyHeadersMatch() を呼んで WAL ファイルのヘッダと db 内に保持している最終のシャドー WAL のヘッダが一致するか確認。
* db.clean() を呼んで以前の世代とその WAL ファイルを削除。
* db.Replicas のそれぞれ (`r`) について `r.Start(db.ctx)` を呼んでレプリケーションを開始。

### db.acquireReadLock メソッド

// acquireReadLock begins a read transaction on the database to prevent checkpointing.

[func (db *DB) acquireReadLock() error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L837-L858)

* すでにロック済み(`db.rtx != nil`)な場合は何もせず抜ける
* `db.db.Begin()` を呼んでトランザクション `tx` を開始
* トランザクション `tx` で `SELECT COUNT(1) FROM _litestream_seq;` クエリを実行して読み取りロックを取得
* `db.rtx` に `tx` を保管

### db.releaseReadLock メソッド

// releaseReadLock rolls back the long-running read transaction.

[func (db *DB) releaseReadLock() error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L860-L871)

* 読み取りロックを保持していない(`db.rtx == nil`)場合は何もせず抜ける
* `db.rtx.Rollback()` を呼んでトランザクションをロールバックし読み取りロックを解放
* `db.rtx` を `nil` にクリア

## スナップショットと WAL ファイル書き出し
### db.Sync メソッド

// Sync copies pending data from the WAL to the shadow WAL.

[func (db *DB) Sync(ctx context.Context) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L928-L950)

* db.StreamClient が nil 以外の場合は何もせず抜ける。
* db.mu のロックを取って `db.sync(ctx)` を呼ぶ。失敗した場合はリトライ。初回も含めて最大5回。

### db.sync メソッド

[func (db *DB) sync(ctx context.Context) (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L952-L1067)

* db.init メソッド呼び出し。
* db.pos がゼロ値なら db.invalidate メソッドを呼び出して取得。
* [db.ensureWALExists メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1069-L1079) を呼び出して WAL ファイルが存在するようにする。
    * 存在しない場合はこのメソッド内で `INSERT INTO _litestream_seq (id, seq) VALUES (1, 1) ON CONFLICT (id) DO UPDATE SET seq = seq + 1` というSQLを実行して WAL ファイルが作られるようにしている。
* [db.verify メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1081-L1144) を呼んで [syncInfo](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1146-L1152) を取得。
* `info.reason != ""` (verify に失敗した) 場合は [db.createGeneration メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L890-L926) を呼んで generation を作成。
* [db.copyToShadowWAL メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1205-L1328) を呼んで `db` の `pos`, `chksum0`, `chksum1`, `frame` を更新。
* WAL ファイルの終端にいる (`info.start`) 場合、 [db.initShadowWALIndex メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1154-L1203) を呼んで新しいインデクスの開始から WAL を再開。
* checkpoint が必要か判定。
* checkpoint が必要な場合 [db.checkpoint メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1525-L1595) を呼ぶ。
* [db.clean メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1525-L1595) を呼んで古い generation と WAL ファイルを削除。

### db.checkpoint メソッド

// checkpointAndInit performs a checkpoint on the WAL file and initializes a new shadow WAL file.

[func (db *DB) checkpoint(ctx context.Context, generation, mode string) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1525-L1595)

* checkpoint の前に readWALHeader 関数で WAL ヘッダを読んで `hdr` ローカル変数に保管し、再開されたかを確認。
* [db.copyToShadowWAL メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1205-L1328) を呼んで `db` の `pos`, `chksum0`, `chksum1`, `frame` を更新。
* [db.execCheckpoint メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1597-L1646) を呼ぶ。
    * エラーが起きたときは `INSERT INTO _litestream_seq (id, seq) VALUES (1, 1) ON CONFLICT (id) DO UPDATE SET seq = seq + 1` の SQL を実行。
* readWALHeader 関数を読んで `hdr` と同じだった場合は抜ける。
* db.db.Begin を呼んでトランザクションを開始。
* `INSERT INTO _litestream_lock (id) VALUES (1);` のSQLを実行して書き込みのトランザクションにする。トランザクションは後でロールバックするので更新はしない。
* [db.verifyLastShadowFrame メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1330-L1359) を呼んで `db.pos.Offset` の位置の手前が `db.frame` の内容と一致するかを確認。
* [db.copyToShadowWAL メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1205-L1328) を呼んで `db` の `pos`, `chksum0`, `chksum1`, `frame` を更新。
* [db.initShadowWALIndex メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1154-L1203) を呼んで新しいインデクスの開始から WAL を再開。
* トランザクションをロールバック。

## db.execCheckpoint メソッド

[func (db *DB) execCheckpoint(mode string) (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1597-L1646)

* [db.releaseReadLock メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L860-L871) を呼んで checkpoint 発行の前に読み取りロックを外しておく。
* `PRAGMA wal_checkpoint(` + mode + `);` の SQL を実行して checkpoint を実行。mode は `PASSIVE` か `RESTART`
    * [PRAGMA schema.wal_checkpoint](https://www.sqlite.org/pragma.html#pragma_wal_checkpoint) 参照
    * PASSIVE: DBのreaderとwriterの処理が終了するのを待たずに可能な範囲の frame を checkpoint する。ログ内の全ての frame がcheckpointされた場合は DB を sync する。
    * RESTART: FULLの動作に加えてログファイルを checkpoint した後全てのreaderがログファイルの読み取りを完了するまでブロックして待つ
    * FULL: DBのwriterがいなくなり、全てのreaderが一番新しいスナップショットから読むようになるまでブロックして待つ。その後ログ内の全てのframeをcheckpointしてDBをsyncする。FULL実行中は他のconcurrentなwriterをブロックするがreaderは処理を実行できる。
* [db.clean メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1525-L1595) を呼んで古い generation と WAL ファイルを削除。
* db.acquireReadLock メソッドを呼んで長い読み取りトランザクションを開始し、他のトランザクションがcheckpointを発行できないようにする。

## リストア

### Restore 関数

// Restore restores the database to the given index on a generation.

[func Restore(ctx context.Context, client ReplicaClient, filename, generation string, snapshotIndex, targetIndex int, opt RestoreOptions) (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/replica_client.go#L398-L475)

* リストア先のファイル名のファイルがすでにある場合はエラーで抜ける
* 以下では一旦 filename 引数のファイル名に `.tmp` を加えたファイル名で処理して最後に `os.Rename` で filename 引数のファイル名にアトミックにリネームしている
* RestoreSnapshot 関数を呼んでスナップショットをリストア
* NewWALDownloader 関数を呼んで戻り値 `d` に対して `d.Next()` で繰り返し WAL のインデクスとパスを取得し、 ApplyWAL 関数で WAL を適用
* filename + ".tmp" から filename に os.Rename でリネーム

### RestoreSnapshot 関数

// RestoreSnapshot copies a snapshot from the replica client to a file.

[func RestoreSnapshot(ctx context.Context, client ReplicaClient, filename, generation string, index int, mode os.FileMode, uid, gid int) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/replica_client.go#L499-L519)

* `internal.CreateFile` 関数を呼んでファイル `f` を作成
* `client.SnapshotReader` メソッドを呼んでリーダー `rd` を作成
* `lz4.NewReader(rd)` で lz4 を解凍しつつ `io.Copy` で `f` にコピー
* `f.Sync` と `f.Close` を呼んでファイルを閉じる

### NewWALDownloader 関数

// NewWALDownloader returns a new instance of WALDownloader.

[func NewWALDownloader(client ReplicaClient, prefix string, generation string, minIndex, maxIndex int) *WALDownloader](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/wal_downloader.go#L57-L74)

* [WALDownloader 構造体](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/wal_downloader.go#L15-L55) のインスタンスを作成して返す
    * WALDownloader 構造体のコメントによると複数の WAL ファイルを並列にダウンロードするが Next メソッドでは WAL の順序通りに返すようになっているとのこと

### WALDownloader.Next メソッド

// Next returns the index & local file path of the next downloaded WAL file.

[func (d *WALDownloader) Next(ctx context.Context) (int, string, error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/wal_downloader.go#L185-L206)

* `d.err` が設定済みに場合は抜ける
* [d.init メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/wal_downloader.go#L92-L125)を呼ぶ
* select で `ctx.Done()`, `d.ctx.Done()`, `d.output` から一番早くレシーブしたものを使う
    * `v, ok := <-d.output` でレシーブして `ok` な場合に`v.index`, `v.path`, `v.err` を返す

### ApplyWAL 関数

// ApplyWAL performs a truncating checkpoint on the given database.

[func ApplyWAL(ctx context.Context, dbPath, walPath string) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1872-L1893)

* `walPath` を `dbPath+"-wal"` に `os.Rename` でリネーム
* `d, err := sql.Open("litestream-sqlite3", dbPath)` でDBをオープン
    * `defer` で `_ = db.Close()` クローズ。主にエラーで抜ける時用。成功時は `d.Close()` が関数最後でも呼んでいるので計2回呼ばれる
* `PRAGMA wal_checkpoint(TRUNCATE);` のSQLを実行
    * [PRAGMA schema.wal_checkpoint(TRUNCATE);](https://www.sqlite.org/pragma.html#pragma_wal_checkpoint) 参照。
    * TRUNCATE は RESTART と同様だが成功で完了時は WAL ファイルがトランケートされる
    * 3つの整数のカラムからなる1行が返ってくる
    * 1カラム目は通常は0だが、完了前にブロックされた場合は1
* 上記のSQL実行結果の1カラム目が0以外の場合はエラーを返す
* `d.Close()` を呼んでDBをクローズし、戻り値をそのまま返す

### db.close メソッド

// Close flushes outstanding WAL writes to replicas, releases the read lock, and closes the database.

[func (db *DB) Close() (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L433-L491)

* `db.db != nil` の場合に `db.db.Close()` を呼ぶ以外にもいろいろやっている。
* 特に `db.rtx != nil` の場合は `db.releaseReadLock()` を呼んで他のアプリケーションが checkpoint を発行可能にしている

