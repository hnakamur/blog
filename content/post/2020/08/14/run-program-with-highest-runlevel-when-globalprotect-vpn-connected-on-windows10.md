---
title: "Windows10上のGlobalProtectでVPN接続後にプログラムを最上位の特権で実行する"
date: 2020-08-14T11:16:18+09:00
---

## はじめに

勤務先で共有されているVPN用のルート追加プログラムがあるのですが、
今まではショートカットを作ってGlobalProtectでVPN接続後に手動で実行していました。

今日時間を取って調査したら自動化できたのでメモです。
なおログインしているユーザーに管理者権限がある前提です。

## Windows10のGlobalProtectでVPN接続後にプログラムを実行する設定

[Deploy Scripts Using the Windows Registry](https://docs.paloaltonetworks.com/globalprotect/9-0/globalprotect-admin/globalprotect-apps/deploy-app-settings-transparently/deploy-app-settings-to-windows-endpoints/deploy-scripts-using-the-windows-registry.html) に説明がありました。

レジストリエディターで
`HKEY_LOCAL_MACHINE\SOFTWARE\Palo Alto Networks\GlobalProtect\Settings\post-vpn-connect` というキーを作成し、そこに `command` という文字列値で起動したいプログラムと引数を作成すればVPN接続後に実行されます。

まずは

```
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\Palo Alto Networks\GlobalProtect\Settings\post-vpn-connect]
"command"="C:\\Windows\\System32\\notepad.exe"

```

のようにメモ帳を起動する設定を追加して実験してみるとVPN接続後に無事起動されました。


## Windows10のタスクスケジューラに最上位の特権で実行するタスクを登録

ルートを追加するのは一般ユーザー権限では出来ず管理者権限で実行する必要があります。

通常であれば、管理者権限が必要なコマンドを動かすとWindowsのユーザーアカウント制御(UAC)ダイアログが表示され許可すると実行されます。

一方上記のGlobalProtectでVPN接続後にプログラムを実行する設定では、UACダイアログが表示されず実行もされないことがわかりました。

[5 Ways to Disable User Account Control (UAC) for Specific Software • Raymond.CC](https://www.raymond.cc/blog/task-scheduler-bypass-uac-prompt/)
の "5. Manually Bypass User Account Control Prompts Using The Task Scheduler" にタスクスケジューラを使う方法が紹介されていました。

[Windows10 - 管理者権限が必要なアプリを自動起動（スタートアップ） - PC設定のカルマ](https://pc-karuma.net/windows-10-task-schedule-without-uac-prompt/) などに日本語の記事もありました。

その後 PowerShell でタスクを登録する方法も見つけたのでこちらも書いておきます。
以下の2つのどちらかで登録すればOKです。

* タスクスケジューラのGUIでタスクを登録する方法
* PowerShellでタスクスケジューラにタスクを登録する方法

### タスクスケジューラのGUIでタスクを登録する方法

1. タスクスケジューラを起動します。
    * Windowsキーを押して「スケジュ」と入力してインクリメンタルサーチでタスクスケジュールが表示されたら選択するなど。
2. 左のツリーで「タスクスケジューラライブラリ」を選択して[操作]/[タスクの作成]メニューを実行します。
3. [全般]タブの[名前]に作成したいタスク名を入力します。
4. [全般]タブの[説明]に適宜説明を書いておきます。
5. [全般]タブの[最上位の特権で実行する]チェックボックスをオンにします。
6. [操作]タブの[新規]ボタンを押して[プログラム/スクリプト]に実行ファイル名を入力し、引数が必要な場合は[引数の追加(オプション)]に入力します。
7. [新しい操作]ダイアログで[OK]ボタンを押して閉じ[タスクの作成]でも[OK]を押して閉じます。

### PowerShellでタスクスケジューラにタスクを登録する方法

以下の一連のコマンドを適宜修正して、管理者権限で PowerShell を起動して実行します。

```
$A = New-ScheduledTaskAction -Execute "実行ファイルのフルパス" -Argument "必要な場合は引数"
$P = New-ScheduledTaskPrincipal -UserID $env:USERDOMAIN\$env:USERNAME -RunLevel Highest
$S = New-ScheduledTaskSettingsSet
$D = New-ScheduledTask -Action $A -Principal $P -Settings $S -Description "適宜説明をここに書きます"
Register-ScheduledTask 作りたいタスク名 -InputObject $D
```

上のスクリプトは
[New-ScheduledTask](https://docs.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtask?view=win10-ps#related-links) の Examples をベースに左のツリーから関連のコマンドレットのドキュメントも参照して書きました。

## GlobalProtectでVPN接続後にタスクを実行する設定

「作成したタスク名」を適宜変更して以下の内容でレジストリに登録します。

```
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\Palo Alto Networks\GlobalProtect\Settings\post-vpn-connect]
"command"="C:\Windows\System32\schtasks.exe /run /TN 作成したタスク名"

```

Goで標準出力に出力しつつroute addを実行するプログラムを使っているのですが、この設定をしてGlobalProtectでVPNに接続すると、コマンドプロンプトっぽいウィンドウが一瞬表示されてすぐ閉じた後、しばらくしてから再度コマンドプロンプトが開いて実行されるという挙動になりました。

ちょっと気になる挙動ではあるのですが、とりあえず目的は達成できたので気にしないことにしました。
