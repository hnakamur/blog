---
title: "Litestreamのコードリーディングその2"
date: 2022-05-13T14:48:24+09:00
---

## はじめに
対象バージョン
https://github.com/benbjohnson/litestream/tree/e6f7c6052d84b7265fd54d3a3ab33208948e126b

前回: [Litestreamのコードリーディング](/blog/2022/05/12/litestream-code-reading/)

今回は upstream の URL を指定した場合の挙動関連。

## DB 構造体

// DB represents a managed instance of a SQLite database in the file system.

[type DB struct](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L46-L125)

### DB 構造体の StreamClient のコメント

```
	// Client used to receive live, upstream changes. If specified, then
	// DB should be used as read-only as local changes will conflict with
	// upstream changes.
	StreamClient StreamClient
```

[StreamClient インタフェース](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/litestream.go#L595-L600)

```
// StreamClient represents a client for streaming changes to a replica DB.
type StreamClient interface {
	// Stream returns a reader which contains and optional snapshot followed
	// by a series of WAL segments. This stream begins from the given position.
	Stream(ctx context.Context, pos Pos) (StreamReader, error)
}
```

## db.StreamSlient を設定しているのは1箇所

[cmd/litestream/main.go#L318](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/main.go#L318)

```
db.StreamClient = http.NewClient(upstreamURL, upstreamPath)
```

// NewDBFromConfigWithPath instantiates a DB based on a configuration and using a given path.

[func NewDBFromConfigWithPath(dbc *DBConfig, path string) (*litestream.DB, error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/main.go#L306-L348) 関数内

## NewDBFromConfigWithPath 関数を呼ぶのは2箇所

```
$ vgrep NewDBFromConfigWithPath
Index File                        Line Content
    0 cmd/litestream/main.go       303 return NewDBFromConfigWithPath(dbc, path)
    1 cmd/litestream/main.go       306 // NewDBFromConfigWithPath instantiates a DB based on a configuration and using a given path.
    2 cmd/litestream/main.go       307 func NewDBFromConfigWithPath(dbc *DBConfig, path string) (*litestream.DB, error) {
    3 cmd/litestream/replicate.go  121 return NewDBFromConfigWithPath(dbConfig, path)
```

* [Index 0](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/main.go#L303) は [NewDBFromConfig 関数](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/main.go#L297-L304) 内
* [Index 3](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/replicate.go#L121) は [ReplicateCommand.Run メソッド](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/replicate.go#L98-L183) 内

## db.StreamSlient の Stream メソッドの呼び出し元

```
$ vgrep db.StreamClient
Index File                   Line Content
    0 cmd/litestream/main.go  318 db.StreamClient = http.NewClient(upstreamURL, upstreamPath)
    1 db.go                   930 if db.StreamClient != nil {
    2 db.go                  1649 if db.StreamClient != nil {
    3 db.go                  1716 sr, err := db.StreamClient.Stream(ctx, pos)
```

// Continuously stream and apply records from client.

[sr, err := db.StreamClient.Stream(ctx, pos)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1716)

// stream initializes the local database and continuously streams new upstream data.

[func (db *DB) stream(ctx context.Context) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1708-L1746) メソッド内

↑

// monitorUpstream runs in a separate goroutine and streams data into the local DB.

[func (db *DB) monitorUpstream(ctx context.Context) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1689-L1706)

↑

[func (db *DB) monitor(ctx context.Context) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1648-L1653)

↑

```
	// If an upstream client is specified, then we should simply stream changes
	// into the database. If it is not specified, then we should monitor the
	// database for local changes and replicate them out.
	db.g.Go(func() error { return db.monitor(db.ctx) })
```

[db.go#L428](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L428)

↑

// Open initializes the background monitoring goroutine.

[func (db *DB) Open() (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L404-L431)

↑

```
	// Start watching the database for changes.
	if err := db.Open(); err != nil {
```

[server.go#L106-L107](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/server.go#L106-L107)

// Watch adds a database path to be managed by the server.

[func (s *Server) Watch(path string, fn func(path string) (*DB, error)) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/server.go#L95-L126)

↑

```
		if err := c.server.Watch(path, func(path string) (*litestream.DB, error) {
			return NewDBFromConfigWithPath(dbConfig, path)
		}); err != nil {
```

[cmd/litestream/replicate.go#L120-L122](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/replicate.go#L120-L122)

↑

// Run loads all databases specified in the configuration.

[func (c *ReplicateCommand) Run(ctx context.Context) (err error)](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/cmd/litestream/replicate.go#L98-L183)

## db.StreamSlient の stream メソッドの処理を追ってみる


// stream initializes the local database and continuously streams new upstream data.

[func (db *DB) stream(ctx context.Context) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1708-L1746)

```
// stream initializes the local database and continuously streams new upstream data.
func (db *DB) stream(ctx context.Context) error {
	pos, err := db.readPositionFile()
	if err != nil {
		return fmt.Errorf("read position file: %w", err)
	}

	// Continuously stream and apply records from client.
	sr, err := db.StreamClient.Stream(ctx, pos)
	if err != nil {
		return fmt.Errorf("stream connect: %w", err)
	}
	defer sr.Close()

	// Initialize the database and create it if it doesn't exist.
	if err := db.initReplica(sr.PageSize()); err != nil {
		return fmt.Errorf("init replica: %w", err)
	}

	for {
		hdr, err := sr.Next()
		if err != nil {
			return err
		}

		switch hdr.Type {
		case StreamRecordTypeSnapshot:
			if err := db.streamSnapshot(ctx, hdr, sr); err != nil {
				return fmt.Errorf("snapshot: %w", err)
			}
		case StreamRecordTypeWALSegment:
			if err := db.streamWALSegment(ctx, hdr, sr); err != nil {
				return fmt.Errorf("wal segment: %w", err)
			}
		default:
			return fmt.Errorf("invalid stream record type: 0x%02x", hdr.Type)
		}
	}
}
```

### db.streamSnapshot メソッド

// streamSnapshot reads the snapshot into the WAL and applies it to the main database.

[func (db *DB) streamSnapshot(ctx context.Context, hdr *StreamRecordHeader, r io.Reader) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1748-L1808)

* `PRAGMA wal_checkpoint(TRUNCATE)` クエリを実行して WAL ファイルをトランケート
* `pageN := int(hdr.Size / int64(db.pageSize))` でページ数を計算
* `ww := NewWALWriter(db.WALPath(), db.fileMode, db.pageSize)` で WAL のライターを作成
* `ww.Open()` で WAL ファイルをオープン
    * エラー時用に defer で `_ = ww.Close()` で閉じる。正常時は後続の `ww.Close()` と合わせて計2回呼ばれる
* `ww.WriteHeader()` でヘッダーを書き込み
* `buf := make([]byte, db.pageSize)` で読み込み用バッファ作成
* `r` から `db.pageSize` 分のデータを読んで `ww.WriteFrame(pgno, commit, buf)` で WAL frame に書き込みをページ数分繰り返す
    * `commit` は最後のページ以外は 0 で最後のページ合はページ数 `pageN` にセット
* `ww.Close()` で WALライターを閉じる
* `invalidateSHMFile(db.path)` で WAL のインデクスをインバリデート
* `db.writePositionFile(hdr.Pos())` で書き込み位置をファイルに書き、他のプロセスが読めるようにする
* `"snapshot applied"` をログ出力

### db.streamWALSegment メソッド

// streamWALSegment rewrites a WAL segment into the local WAL and applies it to the main database.

[func (db *DB) streamWALSegment(ctx context.Context, hdr *StreamRecordHeader, r io.Reader) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1810-L1870)

* `zr := lz4.NewReader(r)` で lz4 を解凍するリーダ `zr` を作成
* `hdr.Offset == 0` の場合 `zr` から `WALHeaderSize` バイト数分のデータを読み捨てる
* `ww := NewWALWriter(db.WALPath(), db.fileMode, db.pageSize)` で WAL ライター作成
* `ww := NewWALWriter(db.WALPath(), db.fileMode, db.pageSize)` で WAL のライターを作成
* `ww.Open()` で WAL ファイルをオープン
    * エラー時用に defer で `_ = ww.Close()` で閉じる。正常時は後続の `ww.Close()` と合わせて計2回呼ばれる
* `ww.WriteHeader()` でヘッダーを書き込み
* `buf := make([]byte, WALFrameHeaderSize+db.pageSize)` で読み込み用バッファ作成
* `io.ReadFull(zr, buf)` でデータを読み込み、EOFならループを抜ける
* `WALFrameHeaderSize` バイト数の部分から番号 `pgno` と `commit` を取得
* `ww.WriteFrame(pgno, commit, buf[WALFrameHeaderSize:])` でページを WAL frame に書き込み
* `ww.Close()` で WALライターを閉じる
* `invalidateSHMFile(db.path)` で WAL のインデクスをインバリデート
* `db.writePositionFile(hdr.Pos())` で書き込み位置をファイルに書き、他のプロセスが読めるようにする
* `"wal segment applied: %s", hdr.Pos().String()` をログ出力

### invalidateSHMFile 関数

```
// invalidateSHMFile clears the iVersion field of the -shm file in order that
// the next transaction will rebuild it.
```

[func invalidateSHMFile(dbPath string) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L2019-L2062)

* `db, err := sql.Open("sqlite3", dbPath)` で DB をオープン
    * ここでは接続時フックありのカスタムドライバではなく通常の `sqlite3` ドライバを使っている
    * defer で `_ = db.Close()` でDBを閉じる
* `PRAGMA wal_checkpoint(PASSIVE)` クエリを実行
* `f, err := os.OpenFile(dbPath+"-shm", os.O_RDWR, 0666)` で共有メモリファイルをオープン
* `buf := make([]byte, WALIndexHeaderSize)` で読み込みバッファを作成
* `io.ReadFull(f, buf)` でバッファに読み込み
* `buf[12], buf[60] = 0, 0` で "isInit" フィールドをインバリデート
* `f.Seek(0, io.SeekStart)` で共有メモリファイルの先頭に移動
    * 上で OpenFile で開いているのでこれは不要ではないか?
* `f.Write(buf)` で変更したバッファを書き込み
* `f.Close()` で共有メモリファイルを閉じる
    * 閉じる前に `f.Sync()` しなくてOK?
* `PRAGMA wal_checkpoint(TRUNCATE)` クエリを実行して WAL ファイルを再びトランケート

### DB.writePositionFile メソッド

// writePositionFile writes pos as the current position.

[func (db *DB) writePositionFile(pos Pos) error](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L1452-L1455)

* `internal.WriteFile(db.PositionPath(), []byte(pos.String()+"\n"), db.fileMode, db.uid, db.gid)` で `position` ファイルに位置を書き込み

[(db *DB) PositionPath() string](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L199-L203)

```
// PositionPath returns the path of the file that stores the current position.
// This file is only used to communicate state to external processes.
func (db *DB) PositionPath() string {
	return filepath.Join(db.MetaPath(), "position")
}
```

## ファイル構成

### リプリケーション元のディレクトリ・ファイル構成

DBファイル、共有メモリファイル、WALファイル

```
$ LC_ALL=C ls -lR source.db{,-shm,-wal}
-rw-r--r-- 1 hnakamur hnakamur 16384 May 12 17:05 source.db
-rw-r--r-- 1 hnakamur hnakamur 32768 May 12 17:05 source.db-shm
-rw-r--r-- 1 hnakamur hnakamur 37112 May 12 17:05 source.db-wal
```

[func (db *DB) MetaPath() string](https://github.com/benbjohnson/litestream/blob/e6f7c6052d84b7265fd54d3a3ab33208948e126b/db.go#L181-L185) はリプリケーション元の DB ファイル名に `-litestream` を加えた名前のディレクトリ

その配下のディレクトリ・ファイル構成の例

```
$ LC_ALL=C ls -lR source.db-litestream/
source.db-litestream/:
total 3
-rw-r--r-- 1 hnakamur hnakamur 17 May 12 17:04 generation
drwxrwxr-x 3 hnakamur hnakamur  3 May 12 17:04 generations
-rw-r--r-- 1 hnakamur hnakamur 51 May 12 17:05 position

source.db-litestream/generations:
total 1
drwxrwxr-x 3 hnakamur hnakamur 3 May 12 17:04 40e9bff6b361ab2f

source.db-litestream/generations/40e9bff6b361ab2f:
total 1
drwxrwxr-x 4 hnakamur hnakamur 4 May 12 17:05 wal

source.db-litestream/generations/40e9bff6b361ab2f/wal:
total 10
drwxrwxr-x 2 hnakamur hnakamur 9 May 12 17:05 0000000000000000
drwxrwxr-x 2 hnakamur hnakamur 4 May 12 17:05 0000000000000001

source.db-litestream/generations/40e9bff6b361ab2f/wal/0000000000000000:
total 19
-rw-r--r-- 1 hnakamur hnakamur  51 May 12 17:04 0000000000000000.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 444 May 12 17:04 0000000000000020.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur  91 May 12 17:05 0000000000004080.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur  97 May 12 17:05 0000000000005098.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 102 May 12 17:05 00000000000060b0.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 111 May 12 17:05 00000000000070c8.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 122 May 12 17:05 00000000000080e0.wal.lz4

source.db-litestream/generations/40e9bff6b361ab2f/wal/0000000000000001:
total 2
-rw-r--r-- 1 hnakamur hnakamur 51 May 12 17:05 0000000000000000.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 91 May 12 17:05 0000000000000020.wal.lz4
```

### リプリケーション先のディレクトリ・ファイル構成

```
$ LC_ALL=C ls -lR destination.db/
destination.db/:
total 1
drwxrwxr-x 3 hnakamur hnakamur 3 May 12 17:04 generations

destination.db/generations:
total 1
drwxrwxr-x 4 hnakamur hnakamur 4 May 12 17:04 40e9bff6b361ab2f

destination.db/generations/40e9bff6b361ab2f:
total 2
drwxrwxr-x 2 hnakamur hnakamur 3 May 12 17:04 snapshots
drwxrwxr-x 4 hnakamur hnakamur 4 May 12 17:05 wal

destination.db/generations/40e9bff6b361ab2f/snapshots:
total 5
-rw-r--r-- 1 hnakamur hnakamur 348 May 12 17:04 0000000000000000.snapshot.lz4

destination.db/generations/40e9bff6b361ab2f/wal:
total 10
drwxrwxr-x 2 hnakamur hnakamur 8 May 12 17:05 0000000000000000
drwxrwxr-x 2 hnakamur hnakamur 3 May 12 17:05 0000000000000001

destination.db/generations/40e9bff6b361ab2f/wal/0000000000000000:
total 18
-rw-r--r-- 1 hnakamur hnakamur 464 May 12 17:04 0000000000000000.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur  91 May 12 17:05 0000000000004080.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur  97 May 12 17:05 0000000000005098.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 102 May 12 17:05 00000000000060b0.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 111 May 12 17:05 00000000000070c8.wal.lz4
-rw-r--r-- 1 hnakamur hnakamur 122 May 12 17:05 00000000000080e0.wal.lz4

destination.db/generations/40e9bff6b361ab2f/wal/0000000000000001:
total 5
-rw-r--r-- 1 hnakamur hnakamur 119 May 12 17:05 0000000000000000.wal.lz4
```
