---
title: "PowershellでEmacsライクなキーバインドを使う"
date: 2020-02-22T22:09:32+09:00
---

## はじめに

[PSReadLine で PowerShell を bash のキーバインドにする - Qiita](https://qiita.com/StoneDot/items/c9f4178be53aebea696e) と [PowerShellのキーバインドをEmacs風にする【PSReadLine】 - メモ.org](https://maskaw.hatenablog.com/entry/2019/02/08/193256) を参考に設定したメモです。

## インストール手順

[PowerShell/PSReadLine: A bash inspired readline implementation for PowerShell](https://github.com/PowerShell/PSReadLine) と [PowerShellGet のインストール - PowerShell | Microsoft Docs](https://docs.microsoft.com/ja-jp/powershell/scripting/gallery/installing-psget?view=powershell-7)

PowerShell を管理者権限で開き、以下のコマンドで `PowerShellGet` をインストールします。

```
Install-Module -Name PowerShellGet
```

次に `PSReadLine` をインストールします。

```
Install-Module -Name PSReadLine
```

## 設定ファイル作成

[Post Installation](https://github.com/PowerShell/PSReadLine#post-installation) の Alternatively のほうで設定することにします。

まず `C:\Users\[User]\Documents\WindowsPowerShell` ディレクトリを作成します。

[New-Item](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item?view=powershell-7) だと以下のようにします。

```
New-Item -Path "${Env:USERPROFILE}\Documents\WindowsPowerShell2" -ItemType "directory"
```

次に `C:\Users\[User]\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` ファイルを以下の内容で作成します。

```
Import-Module PSReadLine
Set-PSReadlineOption -EditMode Emacs
Set-PSReadLineKeyHandler -Key Ctrl+d -Function DeleteChar
```

Ctrl-d を押しすぎて PowerShell を抜けないように `DeleteChar` に変更しました。
終了するときは `exit` で。

## キーバインド

基本の Ctrl-f, Ctrl-b, Ctrl-a, Ctrl-e での移動の他に Ctrl-w での単語削除、 Ctrl-u での行全体削除も使えました。
Ctrl-n と Ctrl-p でコマンド履歴を前後に移動できます。
