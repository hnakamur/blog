+++
Categories = ["automation"]
Description = ""
Tags = ["jxa"]
date = "2015-04-06T04:40:43+09:00"
title = "JXA (JavaScript for Automation)を使ってOSXの初期設定を半自動化してみた"

+++
## 概要

OSXを再インストールしたときなどキーボードやトラックパッドの設定を行いますが、
設定する項目が意外と多くて時間がかかります。

そこでJXA (JavaScript for Automation)で自動化してみました。
全自動ではなく半自動化と書いているのはパスワードの入力などは手動で行う必要があるからです。

## きっかけはAppleScriptのUI elementsの記事を読んだこと

以前からAppleScriptでOSXの初期設定の自動化をやってみたかったのですが、
UI要素の調べ方がわからず諦めていました。

StackOverflowの[applescript - How to know the name of UI elements using Accessibility inspector (or any other tool) - Ask Different](http://apple.stackexchange.com/questions/40436/how-to-know-the-name-of-ui-elements-using-accessibility-inspector-or-any-other/87412#87412)のコメントから
[n8henrie.com | A Strategy for UI Scripting in AppleScript](http://n8henrie.com/2013/03/a-strategy-for-ui-scripting-in-applescript/)という記事を見つけて、これがブレイクスルーになりました。

で、いろいろ試していくうちにJavaScriptで書くほうがクロージャが使えて便利ということに気づいたのでJavaScriptに切り替えました。

以下の記事が参考になりました。ありがとうございます！

* [Home · dtinth/JXA-Cookbook Wiki · GitHub](https://github.com/dtinth/JXA-Cookbook/wiki)
* [Macのキーボード入力、マウスクリックをJavaScriptで (JXA) - Qiita](http://qiita.com/zakuroishikuro/items/afab0e33ad2030ba2f92)

## 自分用セットアップスクリプト

私用のセットアップスクリプトを[hnakamur/my-macbook-initial-setup · GitHub](https://github.com/hnakamur/my-macbook-initial-setup)に置きました。完全に自分仕様ですが、ライセンスはMITなので適宜変更してご利用ください。

## AppleScriptやJXAで設定している内容

最初はAppleScriptで書いていたので一部はそのままです。

* App Store経由でのXcodeのインストール
* Xcodeコマンドラインツールのインストール
* キーボードの設定
    * リピート率の設定
    * ControlとCapsの入れ替え
* トラックパッドの設定
    * 使う機能と使わない機能の設定
    * ドラッグロック設定
* ショートカットキーの設定
    * 次のウィンドウのショートカットキー変更
* スクリーンロックのタイミング調整
* キーボードの入力ソースにGoogle日本語入力のひらがなを追加
* [Spark](http://www.shadowlab.org/Software/spark.php)のショートカット追加
* [MacPass](http://mstarke.github.io/MacPass/)のメニューショートカット設定

## AppleScriptに比べてJXAが嬉しいところ

上にも書きましたが、クロージャが使えるのが便利です。

例えば特定の要素が出現するまで待つために以下の様な関数を定義しました。
https://github.com/hnakamur/my-macbook-initial-setup/blob/df0eb48db189d39de9103a53c06f85a5acfaf347/run.sh#L9-L26

```
function isInvalidIndexError(e) {
  return e.toString() === 'Error: Invalid index.'
}
function waitUntilSuccess(f) {
  var ret
  do {
    delay(1)
    try {
      ret = f()
    } catch (e) {
      if (!isInvalidIndexError(e)) {
        throw e
      }
    }
  } while (!ret)
  return ret
}
```

こんな感じで使用します。

https://github.com/hnakamur/my-macbook-initial-setup/blob/df0eb48db189d39de9103a53c06f85a5acfaf347/run.sh#L39-L47

```
  var storeProc = Application('System Events').processes.byName('App Store')
  storeProc.frontmost = true
  var win = storeProc.windows.byName('App Store')
  // Search for Xcode
  var textField = waitUntilSuccess(function() {
    return win.toolbars[0].groups[6].textFields[0]
  })
  textField.value = 'Xcode'
  textField.buttons[0].click()
```

try catchを使わずにUI要素の存在をチェックするのは、上のように深い要素だと
面倒なので、アクセスするコードを動かしてみて `Error: Invalid index.` の
エラーが出たら要素が存在しないと判断するようにしています。

## うまくいってないところ

### Sparkのショートカット追加がうまくいかないときがある

[Spark](http://www.shadowlab.org/Software/spark.php)というアプリを使って
ショートカットを登録しておくと、キーボードの1ストロークで登録したアプリの
起動や起動済みの場合は最前面に持ってこれるので愛用しています。

フリーですがソースは非公開で設定ファイル形式も不明なのでJXAで登録しています。

しかし、アプリケーションのパスを選ぶところが、うまくいくときと行かない時があります。ファイル選択画面でパスを/から入力すると選べるのでその方式で実装しているのですが、 例えばFinderのパスを `/System/Library/CoreServices/Finder.app` のように入力してreturnキーを押す操作をJXAで行うと、そのフォルダの中が開いた状態になってしまう時があります。

カラムビューにすると成功するようだったので⌘3を押して切り替えるようにしてみたのですが、2秒ディレイを入れても全体を通して実行していると途中から失敗することがあります。

その後run.shを書き換えてSparkのショートカット設定の部分だけ実行すると、うまくいきます。なぜ全体を通して実行した時は失敗するのかが謎です。

## まとめ

上記のように一部問題はありますが、大部分の操作は自動化できたので、全て手動で設定するのに比べるとずいぶん楽になりました。JXA (JavaScript for Automation)便利です。
