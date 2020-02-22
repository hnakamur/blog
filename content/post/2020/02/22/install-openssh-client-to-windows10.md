---
title: "Windows 10 に OpenSSH クライアントをインストール"
date: 2020-02-22T22:08:54+09:00
---

# はじめに

Windows Subsystem for Linux で ssh クライアントをしばらく使っていたのですが、
[Windows 10にオンデマンド機能のOpenSSHサーバをインストールする方法：企業ユーザーに贈るWindows 10への乗り換え案内（45） - ＠IT](https://www.atmarkit.co.jp/ait/articles/1903/28/news005.html)
で Windows 10 1803 以降では標準で OpenSSH が使えるようになっていることを知りました。
試してみたら快適だったのでインストール手順をメモしておきます。

# OpenSSH クライアントのインストール

[Windows 用 OpenSSH のインストール | Microsoft Docs](https://docs.microsoft.com/ja-jp/windows-server/administration/openssh/openssh_install_firstuse) の手順に従って OpenSSH のクライアントをインストールします。

ここではPowerShell での手順をメモしておきます。

PowerShell を管理者権限で開き以下のコマンドで OpenSSH 機能の一覧をバージョンを確認します（ちなみに PowerShell Core だと帰ってきませんでした）。

```
Get-WindowsCapability -Online | ? Name -like 'OpenSSH*'
```

出力例

```
Name  : OpenSSH.Client~~~~0.0.1.0
State : NotPresent
Name  : OpenSSH.Server~~~~0.0.1.0
State : NotPresent
```

以下のように実行し OpenSSH クライアントの機能をインストールします。

```
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

# ssh-agent サービスの状態確認

```
Get-Service ssh-agent | Select Name,DisplayName,Status,StartType
```

出力例

```
Name      DisplayName                   Status StartType
----      -----------                   ------ ---------
ssh-agent OpenSSH Authentication Agent Running Automatic
```

# ssh-agent サービスの状態変更

もし StartType や Status が違う場合は下記を参考に自動起動と起動中にします。

* [Enable/Disable a Service via PowerShell - Risual](https://www.risual.com/2011/06/enabledisable-a-service-via-powershell/)
* [Set-Service](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-service?view=powershell-7)
* [Start-Service](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-service?view=powershell-7)

自動起動にする

```
Set-Service ssh-agent -StartupType Automatic
```

起動する

```
Set-Serice ssh-agent -Status Running -PassThru
```
あるいは
```
Start-Service ssh-agent
```

## 脱線: サービス一覧表示

```
Get-Service
```

と実行するとサービス一覧が表示されますが `Name` と `DisplayName` の値が長い場合は途中から `...` で省略されます。

[How do I increase the column width in Powershell to avoid truncation?](https://social.technet.microsoft.com/Forums/windowsserver/en-US/eee5be42-f412-4661-9b30-3b43005aeca1/how-do-i-increase-the-column-width-in-powershell-to-avoid-truncation?forum=winserverpowershell) で紹介されていた `| Format-Table -Wrap -AutoSize` を使って

```
Get-Service | Format-Table -Wrap -AutoSize
```

とすると省略されずに表示されました。

また

```
Get-Service | Select Status,StartType,Name,DisplayName
```

のように `Select` を使った場合も省略されずに表示されました。
自動起動タイプも見たいのでこの最後の方式が普段使いには良さそうです。

# ssh-agent に登録された鍵一覧表示

以下はユーザ権限の PowerShell で実行します。

```
ssh-add -l
```

# ssh-agent 鍵追加

```
ssh-add 秘密鍵ファイル名
```
