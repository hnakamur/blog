---
title: "Go言語でMultiErrorというのを考えてみたが微妙かも"
date: 2022-07-03T10:40:10+09:00
---

## はじめに

Go の標準ライブラリの [database/sql](https://pkg.go.dev/database/sql@go1.18.3) パッケージや
サードパーティライブラリの [github.com/jmoiron/sqlx](https://pkg.go.dev/github.com/jmoiron/sqlx) でトランザクションを使う際に、成功したらコミット、失敗したらロールバックというのを毎回書くのは面倒だし、書き漏れが出そうなので避けたいです。

で、 WithTx みたいな名前の関数を用意して、引数のコールバック関数がエラーを返さない場合はコミット、エラーを返す場合はロールバックするように書いて使っています。

このときコールバック関数がエラーを返したときのロールバックでエラーが起きたときにどう処理するかが悩ましいところです。アプリケーションだとログに書けば良いのですが、ライブラリではログは書かずにエラーを返してアプリケーション側でログを書くのが理想かなと思います。ログの出力方法や形式はアプリケーションによりまちまちなので。

## MultiError というのを考えてみた

そこで、 MultiError というのを考えてみました。

`NewMultiError(errors ...error) *MultiError` 関数で作成します。
error インタフェースを満たすため `Error() String` メソッドが必要ですが、これは全てのエラーのメッセージを ` | ` で連結した文字列を返すようにします。 `,` や `;` だと個々のエラーのメッセージに含まれてそうなので違う文字列にしました。

最初のエラーがメインで、残りは付随するサブ的なものと捉えて `Unwrap() error` は最初のエラーを返すようにしています。

```go
type MultiError struct {
  errors []error
}

func NewMultiError(errors ...error) *MultiError {
  if len(errors) == 0 {
    panic("one or more errors needed")
  }
  if ShouldNotWrapError(errors[0]) {
    panic("error like io.EOF shoud not be wrapped")
  }
  return &MultiError{errors: errors}
}

func ShouldNotWrapError(err error) bool {
  return err == io.EOF
}

func (e *MultiError) Error() string {
  var b strings.Builder
  for i, err := range e.errors {
    if i > 0 {
      b.WriteString(" | ")
    }
    b.WriteString(err.Error())
  }
  return b.String()
}

func (e *MultiError) Unwrap() error {
  return e.errors[0]
}

func (e *MultiError) Errors() []error {
  errors2 := make([]error, len(e.errors))
  copy(errors2, e.errors)
  return errors2
}
```

これを使って `WithTx` と `WithTxContext` というのを書いてみるとこんな感じです。

```go
func WithTx(db *sqlx.DB, cb func(tx *sqlx.Tx) error) error {
  tx, err := db.Beginx()
  if err != nil {
    return err
  }

  err = cb(tx)
  if err != nil {
    if err2 := tx.Rollback(); err2 != nil {
      if !ShouldNotWrapError(err) {
        return NewMultiError(err, err2)
      }
      // We have to log err2 here since err should not be wrapped.
      log.Printf("rollback: %s", err2)
    }
    return err
  }
  return tx.Commit()
}

func WithTxContext(ctx context.Context, db *sqlx.DB, opts *sql.TxOptions, cb func(ctx context.Context, tx *sqlx.Tx) error) error {
  tx, err := db.BeginTxx(ctx, opts)
  if err != nil {
    return err
  }

  err = cb(ctx, tx)
  if err != nil {
    if err2 := ctx.Err(); err2 != nil {
      if !ShouldNotWrapError(err) {
        return NewMultiError(err, err2)
      }
      // We have to log err2 here since err should not be wrapped.
      log.Printf("context: %s", err2)
      return err
    }

    if err2 := tx.Rollback(); err2 != nil {
      if !ShouldNotWrapError(err) {
        return NewMultiError(err, err2)
      }
      // We have to log err2 here since err should not be wrapped.
      log.Printf("rollback: %s", err2)
    }
    return err
  }
  return tx.Commit()
}
```

実は sql 関連で `context.Context` 付きのメソッドは存在は知ってましたが使ったことはなかったので、 `WithTxContext` は今初めて書いてみたところで正しいかは不明です。[database/sql.DB.BeginTx](https://pkg.go.dev/database/sql@go1.18.3#DB.BeginTx) によると context がキャンセルされたときはロールバックされるとあるのでたぶんこれで良いはず。

## io.EOF はラップしないほうが良い

[errors.Is](https://pkg.go.dev/errors@go1.18.3#Is) 登場以前の `if err == io.EOF` のようなコードが巷に多数あることを考えると、 `io.EOF` はラップしないようにすべきです。

その場合は仕方がないのでログに書くようにしています。
上のコードでは [log.Printf](https://pkg.go.dev/log@go1.18.3#Printf) で書いていますが、アプリケーションに応じて変更する必要があります。

`WithTx` をライブラリとして提供するなら、そこをカスタマイズできるような仕組みを用意したほうが良さそうです。
が、構造化ログライブラリとかも考えると API を考えるのは大変そうな気がします。

[Go Proverbs](https://go-proverbs.github.io/) の [A little copying is better than a little dependency.](https://www.youtube.com/watch?v=PAAkCSZUG1c&t=9m28s) を考えるとこれくらいのコードならアプリケーション側にコピーして使うほうが良さそうな気がします。
ただ、それなら Rollback のようなエラーの後処理のエラーは MutliError 使わずに常にその場でログ出力で良さそうな気もします。
