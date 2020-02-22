---
title: "PowerShellでZIPファイルを解凍する"
date: 2020-02-22T23:30:22+09:00
---

## PowerShell の Expand-Archive で ZIP ファイルを解凍

[逆引き！PowerShellで圧縮ファイル(ZIP)の解凍する方法【Expand-Archive】 | 【ﾁｪｼｬわら】Powershellとは、から学ぶ入門者の教科書-脱コマンドプロンプト-](https://cheshire-wara.com/powershell/ps-cmdlets/item-file/expand-archive/) で紹介されていた [Expand-Archive](https://docs.microsoft.com/ja-jp/PowerShell/module/microsoft.powershell.archive/expand-archive?view=powershell-5.1) コマンドで解凍できます。

カレントディレクトリに解凍する場合。

```
Expand-Archive -Path foo.zip
```

解凍先を指定して解凍する場合。

```
Expand-Archive -Path foo.zip -DestinationPath C:\Bar
```

## 脱線: コマンドのエイリアス

ついつい Linux の癖で PowerShell でも `ls` などと入力してしまいますが、 PowerShell のコマンドレットにエイリアスされているので一応動作はします。

```
Alias
```

で一覧が確認できます。

ただしあくまでコマンドレットへのエイリアスなので `rm -rf ディレクトリ名` などと実行してもエラーになります。

`alias rm` で確認すると `rm` は `Remove-Item` へのエイリアスになっています。

## 脱線: コマンドのオンラインヘルプ

`Get-Help Remove-Item` などとするとヘルプが見られるのですが、注釈に
`Get-Help Remove-Item -Online` とするとデフォルトブラウザでオンラインヘルプが見られます。

[Remove-Item](https://docs.microsoft.com/ja-jp/powershell/module/microsoft.powershell.management/remove-item?view=powershell-6) が開きました。

しかし `Get-Help Expand-Archive -Online` は 404 Not Found となってしまいました。

## ディレクトリ一括削除

で、 `Remove-Item` には `-Recurse` オプションがあるので

```
Remove-Item -Recurse ディレクトリ
```

でディレクトリを再帰的に削除できます。
