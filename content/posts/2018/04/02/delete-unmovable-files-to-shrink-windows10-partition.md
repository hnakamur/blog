+++
title="Windows10のパーティションを縮小するために移動できないファイルを消す"
date = "2018-04-02T00:16:00+09:00"
tags = ["windows"]
categories = ["blog"]
+++


# はじめに

WindowsとUbuntuでデュアルブートするためにWindowsのパーティションを縮小
するのですが、前回試したときは移動できないファイルがあるというようなことを
言われてあまり縮小できませんでした。

その後調べてみると移動できないファイルを一時的に削除して、もっと縮小できた
のでメモです。今回試したのはWindows 10 Proです。

# 参考URL

以下のページを参考にしました。有用な情報に感謝です。

* [hard drive - How to shrink a Windows 10 partition - Super User](https://superuser.com/questions/1017764/how-to-shrink-a-windows-10-partition)
* [ハイバネーション（hiberfil.sys）を無効にする･削除する - ぼくんちのTV 別館](https://freesoft.tvbok.com/tips/pc_windows/del_hiberfil_sys.html)
* [How to Delete All VSS Shadows and Orphaned Shadows](http://backupchain.com/i/how-to-delete-all-vss-shadows-and-orphaned-shadows)
* [How to shrink a partition with unmovable files in Windows 7 – Brandon Checketts](https://www.brandonchecketts.com/archives/how-to-shrink-a-partition-with-unmovable-files-in-windows-7)


# 一時的に削除

以下の各操作を実行するため、PowerShellを管理者権限で起動します。

Windowsキーを押してスタートメニューを開き powershell と入力して検索結果に PowerShell が表示されたら、マウスを右クリックして「管理者として実行」メニューを選ぶのが手軽でした。

[How to check PowerShell version in Windows 10](http://www.thewindowsclub.com/check-powershell-version-windows) にPowerShellのバージョンの確認方法が書いてありました。私の環境では以下のようになりました。

```console
PS C:\WINDOWS\system32> $PSversionTable

Name                           Value
----                           -----
PSVersion                      5.1.16299.251
PSEdition                      Desktop
PSCompatibleVersions           {1.0, 2.0, 3.0, 4.0...}
BuildVersion                   10.0.16299.251
CLRVersion                     4.0.30319.42000
WSManStackVersion              3.0
PSRemotingProtocolVersion      2.3
SerializationVersion           1.1.0.1
```

## ページファイルを無効にする

管理者権限のPowerShellで以下のように実行します。

ページファイル使用中であることを確認。

```console
wmic pagefileset list
```

ページファイルを無効にする。

```console
wmic computersystem set AutomaticManagedPagefile=False
wmic pagefileset delete
```

参考ページでは `wmic pagefileset where name="C:\\pagefile.sys" delete` と条件を指定していましたがエラーになってしまったので上記のようにしました。

## ハイバネーションを無効にする

管理者権限のPowerShellで以下のように実行します。

```console
powercfg /h off
```

以下のコマンドで状態を確認できます。

```console
powercfg /a
```

実行例（再起動した後に実行しました）。

```console
PS C:\WINDOWS\system32> powercfg /a
以下のスリープ状態がこのシステムで利用可能です:
    スタンバイ (S3)

以下のスリープ状態はこのシステムでは利用できません:
    スタンバイ (S1)
	システム ファームウェアはこのスタンバイ状態をサポートしていません。

    スタンバイ (S2)
	システム ファームウェアはこのスタンバイ状態をサポートしていません。

    休止状態
	休止状態は有効にされていません。

    スタンバイ (S0 低電力アイドル)
	システム ファームウェアはこのスタンバイ状態をサポートしていません。

    ハイブリッド スリープ
	休止状態は使用できません。
	ハイパーバイザーはこのスタンバイ状態をサポートしていません。

    高速スタートアップ
	休止状態は使用できません。
```

## システム復元を無効にする

管理者権限のPowerShellで以下のように実行します。

```console
Disable-ComputerRestore -Drive C:
```

よくわからないままコピペで実行してしまいましたが、私は復元ポイントを作っていなかったので、この操作は不要だったかもしれません。

* [Disable-ComputerRestore](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/disable-computerrestore?view=powershell-5.1) のドキュメント。
* 状態確認には [Get-ComputerRestorePoint](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-computerrestorepoint?view=powershell-5.1) を使うっぽい。


## 再起動

「ページファイルを無効にする」、「ハイバネーションを無効にする」、「システム復元を無効にする」の3つを行った後、Windowsを再起動しました。

# さらに削除

## 一時ファイルを削除

[Windows10 - 一時ファイルを削除する方法 - PC設定のカルマ](https://pc-karuma.net/windows-10-delete-temporary-files/) の手順で一時ファイルを削除しました。

1. コントロールパネルの設定のストレージを選択し、「PC (C:\)」のグラフをクリック。
2. ストレージ使用量の下の各種内訳グラフが並ぶ中の「一時ファイル」をクリック。
3. 「一時ファイル」画面で「一時ファイル」、「ダウンロードフォルダー」、「ごみ箱を空にする」のすべてにチェックして「ファイルの削除」ボタンを押す。

# ボリュームの縮小を試すもいまいち

「ディスクの管理」を開くのはWindowsキーを押してスタートメニューを開き disk と入力して検索結果に表示された「ハードディスク パーティションの作成とフォーマット」を選ぶのが手軽でした。

C: ドライブを選んでマウス右クリックでポップアップメニューを開き「ボリュームの縮小」を試しましたが、縮小可能な量はまだいまいちでした。


# VSS Shadows を削除

[hard drive - How to shrink a Windows 10 partition - Super User](https://superuser.com/questions/1017764/how-to-shrink-a-windows-10-partition) の
[May 10 '17 at 2:11](https://superuser.com/questions/1017764/how-to-shrink-a-windows-10-partition#comment1760829_1060508) にVSS Shadowsを全て消す必要があったいうコメントを見つけました。

検索してみると [How to Delete All VSS Shadows and Orphaned Shadows](http://backupchain.com/i/how-to-delete-all-vss-shadows-and-orphaned-shadows) に削除の手順が書かれていました。

## 移動不可なファイルの確認

また、 
[How to shrink a partition with unmovable files in Windows 7 – Brandon Checketts](https://www.brandonchecketts.com/archives/how-to-shrink-a-partition-with-unmovable-files-in-windows-7)
に移動不可なファイルを確認する手順が書かれていました。

1. Windowsキーを押してスタートメニューを開き event と入力し検索結果に表示された「イベント ビューアー」を選んで起動します。
2. 左のツリーで「Windows ログ」/「Application」を選びます。
3. 右の「操作」のリストで「現在のログをフィルタ」を選び、ダイアログが開いたら「＜すべてのイベントID＞」のテキスト欄をクリックして「259」と入力しリターンキーを押します。
4. 画面中央の一覧に検索結果が表示されますので一番上の最新のイベントを選択します。
5. 「操作」/「コピー」/「詳細をテキストとしてコピー」メニューを選び、お好みのテキストエディタでペーストすればファイルのパスを確認できます。

```text
ログの名前:         Application
ソース:           Microsoft-Windows-Defrag
日付:            2018/04/01 22:04:42
イベント ID:       259
タスクのカテゴリ:      なし
レベル:           情報
キーワード:         クラシック
ユーザー:          N/A
コンピューター:       sunshine7
説明:
ボリューム Windows (C:) に対して縮小の分析が開始されました。このイベント ログ エントリでは、再利用可能な最大領域 (バイト) の減少を招く可能性のある、最後に移動できなかったファイルについての詳細を提供します。
 
 診断の詳細:
 - 最後に移動できなかったと思われるファイル: \$BitMap::$DATA
 - このファイルの最後のクラスター: 0xbfbfe
 - 縮小対象の候補 (LCN アドレス): 0x7ca6b7
 - NTFS ファイル フラグ: -S--D
 - 縮小フェーズ: <analysis>
 
 このファイルの詳細については、"fsutil volume querycluster \\?\Volume{6a1301d0-ab28-4b33-98ca-e063ddba90bc} 0xbfbfe" コマンドを使用してください。
イベント XML:
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Defrag" />
    <EventID Qualifiers="16384">259</EventID>
    <Level>4</Level>
    <Task>0</Task>
    <Keywords>0x80000000000000</Keywords>
    <TimeCreated SystemTime="2018-04-01T13:04:42.083123700Z" />
    <EventRecordID>25945</EventRecordID>
    <Channel>Application</Channel>
    <Computer>sunshine7</Computer>
    <Security />
  </System>
  <EventData>
    <Data>Windows (C:)</Data>
    <Data>\\?\Volume{6a1301d0-ab28-4b33-98ca-e063ddba90bc}</Data>
    <Data>\$BitMap::$DATA</Data>
    <Data>0xbfbfe</Data>
    <Data>0x7ca6b7</Data>
    <Data>-S--D</Data>
    <Data>&lt;analysis&gt;</Data>
    <Binary>00000000D7000000BF00000000000000223679625372B2B9637B71360E00000000000000</Binary>
  </EventData>
</Event>
```

## VSS Shadowsの一覧表示

以下のコマンドで一覧を確認しました。

```console
vssadmin list shadows
```

すると先ほどイベントビューアに出ていた 6a1301d0-ab28-4b33-98ca-e063ddba90bc と一致するものが一覧に出ていました。

## VSS Shadowsの削除

以下のコマンドで削除できました。

```console
vssadmin delete shadows /all
```

# 再度ボリュームの縮小を試すと今度は良い感じ

今度は縮小可能なサイズがエクスプローラで見た空き容量と同程度になっていました。

ただ、一気に40GBぐらい縮小しようとしたら作業領域がないという感じのエラーになったので、20GBずつ段階を踏んで縮小したら無事できました。

最終的にはWindowsのパーティションを80GBにしてみました。

# 一時的に削除していたのを戻す

## ページファイルを有効にする

```console
wmic pagefileset create name="C:\\pagefile.sys"
wmic computersystem set AutomaticManagedPagefile=True
```

## ハイバネーションを有効にする

```console
powercfg /h on
```

## システム復元を有効にする

```console
Enable-ComputerRestore -Drive C:
```

[Enable-ComputerRestore](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/enable-computerrestore?view=powershell-5.1)

## 再起動

「ページファイルを有効にする」、「ハイバネーションを有効にする」、「システム復元を有効にする」の3つを行った後、Windowsを再起動しました。

管理者権限のPowerShellで以下のコマンドを実行してハイバネーション用のファイルとページファイルが作られたことを確認します。

```console
PS C:\WINDOWS\system32> get-childitem -force -file C:\
```

実行例を以下に示します。 hiberfil.sys, pagefile.sys, swapfile.sys の3つがあればOKです。

```console
PS C:\WINDOWS\system32> get-childitem -force -file C:\

    ディレクトリ: C:\

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
---h--       2018/02/18     22:15           1024 AMTAG.BIN
-a-hs-       2018/04/02      1:20     6818037760 hiberfil.sys
-a-hs-       2018/04/02      1:20     2550136832 pagefile.sys
-a-hs-       2018/04/02      1:20       16777216 swapfile.sys
```

# おわりに

ちょっと手間はかかりましたが、サードパーティのパーティションエディターソフトを使わなくてもここまで出来るということがわかったので良かったです。
