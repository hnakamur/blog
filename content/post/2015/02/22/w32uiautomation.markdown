+++
date = "2015-02-22T00:09:24+09:00"
draft = false
title = "Windows UI Automation APIを使うためのGoライブラリw32uiautomationを書いた"

+++

# なぜ

ウェブアプリ開発をしているとInternet Explorerでの動作確認のため[modern.IE](https://www.modern.ie/ja-jp)が欠かせません。が、インストール直後は英語環境になっているので、日本語環境での動作確認のためにはセットアップが必要です。

セットアップ手順は以下のQiitaの記事に書いたのですが、手数が多くて面倒でした。

* [VirtualBox - modern.IEのWindows 7で日本語の表示と入力をできるようにする - Qiita](http://qiita.com/hnakamur/items/5f2f9e817dd0de60abb2)
* [Windows8.xのmodern.IEで日本語を入力、表示できるようにする。 - Qiita](http://qiita.com/hnakamur/items/cd37c9c8826afe4b4dda)

それを自動化するコマンドラインツール[moderniejapanizer](https://github.com/hnakamur/moderniejapanizer)を作りました。実は2年ぐらい前に[AutoIt](https://www.autoitscript.com/site/autoit/)を使って作り始めたのですが自動制御がうまくいかないときがあって挫折していました。昨年暮れぐらいから再挑戦して、今回は勉強を兼ねてGoで実装してみました。

日本語化のほとんどはWin32 APIとレジストリの操作で実現できたのですが、Windows 8で言語に日本語を追加して英語を削除する操作だけはWin32 APIやレジストリで実現する方法を見つけられませんでした。

そこでコントロールパネルの操作をUIオートメーションで行うことにしました。
mattnさんの[go-ole](https://github.com/mattn/go-ole)を利用して、UIオートメーション APIの一部をGoで実装したのが、[hnakamur/w32uiautomation](https://github.com/hnakamur/w32uiautomation)です。

UIオートメーションAPIの全部をカバーするつもりはなくて自分が使う部分だけを実装しています。とりあえず動くようにはなりましたが、まだまだ試行錯誤中なのでAPIは互換性無く変更予定です。

# Windows UI オートメーションについて

下記のページに説明とリファレンスがありました。

* [UI オートメーションの概要](https://msdn.microsoft.com/ja-jp/library/ms747327(v=vs.110%29.aspx)
* [UI Automation (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/ee684009(v=vs.85%29.aspx)

また、始めの一歩として以下の記事も参考にさせて頂きました。ありがとうございます！

* [UI AutomationをJScript.NETで動かす: korokaraのブログ](http://180.cocolog-nifty.com/blog/2011/10/ui-automationjs.html)
* [WindowsアプリのUI自動操作をUI Automation PowerShell Extensionで行う | d.sunnyone.org](http://d.sunnyone.org/2014/09/windowsuiui-automation-powershell.html)

# w32uiautomationの実装について

## UIオートメーションAPIはIDispatchインタフェースを実装していない

実はw32uiautomationを実装する前に、[Windows Update Agent API (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/aa387099(v=vs.85%29.aspx)の実装も作りました。 [hnakamur/windowsupdate](https://github.com/hnakamur/windowsupdate)です。これはWindows 7で日本語の言語パックをWindows Update経由でインストールするために作りました。

Windows Update Agent APIの各インタフェースは例えば[IAutomaticUpdates interface (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/aa385821(v=vs.85%29.aspx)のように[IDispatch interface (Automation)](https://msdn.microsoft.com/en-us/library/windows/desktop/ms221608(v=vs.85%29.aspx)を実装しています。

ですので、 https://github.com/hnakamur/windowsupdate/blob/a878b9dbfeadeb768f27011d6bfd97bfecdd5d9d/search.go#L32

```
	searcher, err := toIDispatchErr(oleutil.CallMethod((*ole.IDispatch)(s), "CreateUpdateSearcher"))
```

のように[oleutil.CallMethod](https://github.com/mattn/go-ole/blob/7d0136ad48c228000c2abdea549674c498110124/oleutil/oleutil.go#L47)などのoleutilパッケージの各種メソッドを使ってWindows Update Agent APIのメソッド呼び出しやプロパティ値の設定・取得を動的に行うことが出来ます。

一方、UIオートメーションAPIのほうは、[IUIAutomation interface (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/ee671406(v=vs.85%29.aspx)のようにIDsipatchインタフェースは実装しておらず、IUnknownインタフェースを実装しているだけです。

そこで、UIオートメーションのインタフェースごとにGoのstructを定義していく必要があります。

mattnさんのgo-oleの[iunknown.go](https://github.com/mattn/go-ole/blob/master/iunknown.go)や[idispatch.go](https://github.com/mattn/go-ole/blob/master/idispatch.go)を見よう見まねで実装してみました。きちんと理解せず雰囲気で書いているので、おかしなところがあるかもしれません。


## IUIAutomationElement::FindFirstは実装してみたが挙動が変

[IUIAutomationElement::FindFirst method (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/ee696029(v=vs.85%29.aspx)は

* https://github.com/hnakamur/w32uiautomation/blob/e469741ce0aeaf5b4f8661a0887f9004a01688ab/iuiautomationelement.go#L113-L115
* https://github.com/hnakamur/w32uiautomation/blob/e469741ce0aeaf5b4f8661a0887f9004a01688ab/iuiautomationelement.go#L141-L155

あたりで実装しています。実行すると戻り値の*IUIAutomationElementはnilではない値になって目的のUI要素が見つかっているようです。しかし、[Microsoft Windows SDK for Windows 7 and .NET Framework 4](http://www.microsoft.com/en-us/download/details.aspx?id=8279)同梱のinspect.exeで見るとnameプロパティに空ではない値が設定されているのに[Get_CurrentName](https://github.com/hnakamur/w32uiautomation/blob/e469741ce0aeaf5b4f8661a0887f9004a01688ab/iuiautomationelement.go#L129)などで名前を取得してみると空文字になってしまうというトラブルに見舞われました。

[IUIAutomation::CreatePropertyCondition](https://msdn.microsoft.com/en-us/library/windows/desktop/ee671529(v=vs.85%29.aspx)でVARIANT型を引数で渡すところがあって、VARIANT型のサイズはuintptrのサイズより大きいので分割してsyscall.Syscallファミリーの関数を呼ぶ必要があります。

* https://github.com/hnakamur/w32uiautomation/blob/e469741ce0aeaf5b4f8661a0887f9004a01688ab/variant_386.go#L14-L22
* https://github.com/hnakamur/w32uiautomation/blob/e469741ce0aeaf5b4f8661a0887f9004a01688ab/iuiautomation_386.go#L11-L29

あたりで実装しているのですが、どこかおかしいのかもしれません。

## 回避策としてTreeWalkerで自前で探すメソッドを実装

FindFirstがうまく動かせなかったので、回避策としてTreeWalkerで自前で探すメソッドを実装してみました。

https://github.com/hnakamur/w32uiautomation/blob/e469741ce0aeaf5b4f8661a0887f9004a01688ab/search.go

幅優先探索でUI要素のツリーを探すようにしています。
また、ウィンドウがまだ存在しない場合はポーリングして存在するまで待ってから返す関数も実装しています。

## 現状だとウィンドウ切り替わり時にSleepを入れる必要がある

実際に試してみるとウィンドウを開いた後すぐにUI要素を探そうとすると見つからない場合がありました。おそらくウィンドウ内のUI要素が作られる前のタイミングで探そうとしているのだと思います。

ただ上記のようにポーリングをしているのでUI要素が作られれば見つかると想定していたのですが、実際はいつまでもポーリングを続けてしまいました。

しかたがないので、

https://github.com/hnakamur/moderniejapanizer/blob/fcc9eb9f51560916ae8831e9c042a789ced298cf/imeja.go#L58

のようにウィンドウが切り替わった後、ウィンドウを探す前に1秒のスリープを入れています。が、これだとマシンが重い状態だと1秒では足りなくてUI要素が見つからずにポーリングし続けてしまうケースが起こりえます。

## IUIAutomation::AddStructureChangedEventHandlerを使いたいがGoの関数をコールバックしてもらう方法がわからず挫折中

おそらくあるべき姿としてはポーリングではなく[IUIAutomation::AddStructureChangedEventHandler method (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/ee671512(v=vs.85%29.aspx)を使うのだと思います。

が、[IUIAutomationStructureChangedEventHandler interface (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/ee696197(v=vs.85%29.aspx)の[IUIAutomationStructureChangedEventHandler::HandleStructureChangedEvent method (Windows)](https://msdn.microsoft.com/en-us/library/windows/desktop/ee696198(v=vs.85%29.aspx)をGoの関数で書いてコールバックで読んでもらう方法がわからず挫折中です。

[Trying AddStructureChangedEventHandler but no luck yet · c76d7df · hnakamur/w32uiautomation](https://github.com/hnakamur/w32uiautomation/commit/c76d7dfb476cd13723bed6da5581639d66b6ffbb)でよくわからないまま雰囲気でトライしてみたのですが、実行時エラーになってしまいました。

# とりあえず当初の目的には使えていますが、まだまだ改良が必要

なのですが、行き詰まっているのでなにかアドバイスありましたらぜひお願いします。

# 2015-02-23 01:07頃追記

## UIAutomationElement::FindFirstがちゃんと動くようになりました

やはり [VariantToUintptrArray](https://github.com/hnakamur/w32uiautomation/blob/0c48ebfdce27726587ae6797643b29b7fe0b99f7/variant_386.go#L14)がバグっていました。
[Fix 32bit VariantToUintptrArray · 0c48ebf · hnakamur/w32uiautomation](https://github.com/hnakamur/w32uiautomation/commit/0c48ebfdce27726587ae6797643b29b7fe0b99f7)で修正しました。

FindFirstがちゃんと動くようになったので、回避策で作ったTreeWalkerで自前で探すメソッドは削除しました。[Remove WaitFindFirstWithBreadthFirstSearch in favor of FindFirst. · 733229d · hnakamur/w32uiautomation](https://github.com/hnakamur/w32uiautomation/commit/733229d4bd779da9e44241b4b581951ff1c4643e)

## コールバックを使うためのsyscall.NewCallbackという関数を見つけました

[go/syscall_windows.go at edadffa2f3464c48a234f3cf2fc092a03f91824f · golang/go](https://github.com/golang/go/blob/edadffa2f3464c48a234f3cf2fc092a03f91824f/src/syscall/syscall_windows.go#L113-L118)で定義されていました。

```
// Converts a Go function to a function pointer conforming
// to the stdcall calling convention. This is useful when
// interoperating with Windows code requiring callbacks.
func NewCallback(fn interface{}) uintptr {
	return compileCallback(fn, true)
}
```

後日試してみたいと思います。
