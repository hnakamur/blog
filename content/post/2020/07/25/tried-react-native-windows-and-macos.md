---
title: "React Native for Windows + macOS を試してみた"
date: 2020-07-25T10:38:36+09:00
---

## はじめに

voluntas さんの [ツイート](https://twitter.com/voluntas/status/1286568276676370433) と [MS Build SK119 React Native: Build cross platform apps that target Windows, Mac, and more! - YouTube](https://www.youtube.com/watch?v=QMFbrHZnvvw) の紹介動画を見て自分でも試してみたのでメモです。

## React Native for Windows

### 必要なソフトウェアのインストール

[microsoft/react-native-windows: A framework for building native Windows apps with React.](https://github.com/microsoft/react-native-windows#getting-started) の [Requirements](https://github.com/microsoft/react-native-windows#requirements) から
[System Requirements · React Native for Windows + macOS](https://microsoft.github.io/react-native-windows/docs/rnw-dependencies) を開いてここに書いてある PowerShell のスクリプトを実行して必要なソフトウェアをインストールしました。

[Git for Windows](https://gitforwindows.org/) は私は事前にインストール済みでした。

管理者として PowerShell を起動し、以下のスクリプトを実行します。

```powershell
Start-Process -Verb RunAs powershell -ArgumentList @("-command", "iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/microsoft/react-native-windows/master/vnext/Scripts/rnw-dependencies.ps1'))")
```

Visual Studio 2019 Community や Node.js などをインストールするか逐次聞かれるので `y` と Enter を押してインストールします。

### React Native for Windows のサンプルプロジェクトを試してみるが起動失敗

[Getting Started](https://github.com/microsoft/react-native-windows#getting-started) の [Getting Started Guide](https://microsoft.github.io/react-native-windows/docs/getting-started) の手順に従って試してみました。

通常権限のコマンドプロンプトを開いて以下のコマンドを実行します。
ここではプロジェクト名は `hello_react_native` として TypeScript のテンプレートを指定しています。

```cmd
npx react-native init hello_react_native --template react-native-template-typescript@6.4.*
```

ちなみにプロジェクト名に `-` を含むと以下のようなエラーが出ました。 alphanumeric しか使えないと言っていますが `_` は使えます。そういえば冒頭の動画でも `_` は使っていました。

```
error "hello-react-native" is not a valid name for a project. Please use a valid identifier name (alphanumeric). Run CLI with --verbose flag for more details.
```

プロジェクトが生成されたら、プロジェクトのディレクトリに移動します。

```cmd
cd hello_react_native
```

以下のコマンドを実行して React Native for Windows のパッケージをインストールします。実行するとプロジェクト内に `windows` というフォルダーとサブフォルダー階層が作成されます。

```cmd
npx react-native-windows-init --overwrite
```

以下のコマンドを実行してアプリケーションを起動します。エラーが起きると `--logging` を付けて再度実行するようメッセージが出るので私は常につけておくことにしました。

```cmd
npx react-native run-windows --logging
```

### `msvcp140d_app.dll` が無いと言われるのでインストール

ここが今回の最大のはまりポイントでした。上記のコマンドを実行すると、しばらくビルドが続いた後、以下のエラーが出ました。
`Microsoft.VCLibs.140.00.Debug` というフレームワークが無いとのことです。

```
√ Building Solution
 √ Starting the React-Native Server
 ? Applying Add-AppDevPackage.ps1 workaround for VS 16.5-16.6 bug - see https://developercommunity.visualstudio.com/content/problem/1012921/uwp-packaging-generates-incompatible-certificate.html
 √ Removing old version of the app
 √ Enabling Developer Mode
 Add-AppxPackage : Deployment failed with HRESULT: 0x80073CF3, パッケージの更新、依存関係、または競合の検証に失敗しました。
パッケージ 11173bc7-90b1-4e0d-87cb-9b82d39848c3_1.0.0.0_x86__bgae2mfp0tfdt は、見つからないフレームワークに依存しているためインストールできません。インストールする>このパッケージには、フレームワーク "Microsoft.VCLibs.140.00.Debug" (公開元 "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US"、ニュ>ートラルまたは x86 プロセッサ アーキテクチャ、最少バージョン 14.0.27810.0) が必要です。現在インストールされている "Microsoft.VCLibs.140.00.Debug" という名前のフレー
ムワークは次のとおりです: {Microsoft.VCLibs.140.00.Debug_14.0.25547.0_x86__8wekyb3d8bbwe Microsoft.VCLibs.140.00.Debug_14.0.25547.0_x64__8wekyb3d8bbwe}
NOTE: For additional information, look for [ActivityId] 95d6bf9d-620c-0000-411c-d9950c62d601 in the Event Log or use the command line Get-AppPackageLog -Acti
vityID 95d6bf9d-620c-0000-411c-d9950c62d601
At C:\Users\hnakamur\hello_react_native\node_modules\react-native-windows\local-cli\runWindows\utils\WindowsStoreAppUtils.ps1:183 char:5
+     Add-AppxPackage -Path $Path -Register -ForceApplicationShutdown
+     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : WriteError: (C:\Users\hnakam...ppxManifest.xml:String) [Add-AppxPackage], IOException
    + FullyQualifiedErrorId : DeploymentError,Microsoft.Windows.Appx.PackageManager.Commands.AddAppxPackageCommand

× Installing new version of the app from layout
 × Failed to deploy: Installing new version of the app from layout
```

いろいろ検索して調べたところ https://developercommunity.visualstudio.com/solutions/49987/view.html に書かれている手順で解決できました。

1. 管理者権限で PowerShell を開きます。

2. 以下のコマンドを実行して、2つのパッケージをインストールします。

```powershell
add-appxpackage "C:\Program Files (x86)\Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Debug\x64\Microsoft.VCLibs.x64.Debug.14.00.appx"

add-appxpackage "C:\Program Files (x86)\Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Debug\x86\Microsoft.VCLibs.x86.Debug.14.00.appx"
```

3. 上記の2つのパッケージが正しくインストールされたことを確認します。

```
PS C:\WINDOWS\system32> get-appxpackage | where-object {$_.Name -eq "Microsoft.VCLibs.140.00.Debug"}


Name              : Microsoft.VCLibs.140.00.Debug
Publisher         : CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US
Architecture      : X64
ResourceId        :
Version           : 14.0.27810.0
PackageFullName   : Microsoft.VCLibs.140.00.Debug_14.0.27810.0_x64__8wekyb3d8bbwe
InstallLocation   : C:\Program Files\WindowsApps\Microsoft.VCLibs.140.00.Debug_14.0.27810.0_x64__8wekyb3d8bbwe
IsFramework       : True
PackageFamilyName : Microsoft.VCLibs.140.00.Debug_8wekyb3d8bbwe
PublisherId       : 8wekyb3d8bbwe
IsResourcePackage : False
IsBundle          : False
IsDevelopmentMode : False
NonRemovable      : False
IsPartiallyStaged : False
SignatureKind     : Developer
Status            : Ok

Name              : Microsoft.VCLibs.140.00.Debug
Publisher         : CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US
Architecture      : X86
ResourceId        :
Version           : 14.0.27810.0
PackageFullName   : Microsoft.VCLibs.140.00.Debug_14.0.27810.0_x86__8wekyb3d8bbwe
InstallLocation   : C:\Program Files\WindowsApps\Microsoft.VCLibs.140.00.Debug_14.0.27810.0_x86__8wekyb3d8bbwe
IsFramework       : True
PackageFamilyName : Microsoft.VCLibs.140.00.Debug_8wekyb3d8bbwe
PublisherId       : 8wekyb3d8bbwe
IsResourcePackage : False
IsBundle          : False
IsDevelopmentMode : False
NonRemovable      : False
IsPartiallyStaged : False
SignatureKind     : Developer
Status            : Ok
```

```powershell
PS C:\WINDOWS\system32> Get-ChildItem -Path "C:\Program Files\WindowsApps\Microsoft.VCLibs.140.00.Debug*\msvcp140d_app.dll" | Select FullName                                                                                                   
FullName
--------
C:\Program Files\WindowsApps\Microsoft.VCLibs.140.00.Debug_14.0.27810.0_x64__8wekyb3d8bbwe\msvcp140d_app.dll
C:\Program Files\WindowsApps\Microsoft.VCLibs.140.00.Debug_14.0.27810.0_x86__8wekyb3d8bbwe\msvcp140d_app.dll
```

### (横道) Linux の ldd 相当は dumpbin /dependents で OK

調査中に、実行ファイルが依存しているライブラリを調べる（Linux の `ldd` 相当）のは `dumpbin /dependents` で出来ることを知ったのでメモ。

```
C:\Users\h-nakamura\hello_react_native>"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC\14.26.28801\bin\Hostx64\arm\dumpbin.exe" /dependents C:\Users\h-nakamura\hello_react_native\windows\Debug\hello_react_native\hello_react_native.exe
Microsoft (R) COFF/PE Dumper Version 14.26.28806.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file C:\Users\h-nakamura\hello_react_native\windows\Debug\hello_react_native\hello_react_native.exe

File Type: EXECUTABLE IMAGE

  Image has the following dependencies:

    MSVCP140D_APP.dll
    VCRUNTIME140D_APP.dll
    ucrtbased.dll
    api-ms-win-core-processthreads-l1-1-0.dll
    api-ms-win-core-synch-l1-1-0.dll
    api-ms-win-core-synch-l1-2-0.dll
    api-ms-win-core-debug-l1-1-0.dll
    api-ms-win-core-errorhandling-l1-1-0.dll
    api-ms-win-core-string-l1-1-0.dll
    api-ms-win-core-processthreads-l1-1-1.dll
    api-ms-win-core-winrt-l1-1-0.dll
    api-ms-win-core-profile-l1-1-0.dll
    api-ms-win-core-sysinfo-l1-1-0.dll
    api-ms-win-core-libraryloader-l1-2-0.dll
    api-ms-win-core-interlocked-l1-1-0.dll
    api-ms-win-core-heap-l1-1-0.dll
    api-ms-win-core-memory-l1-1-0.dll
    api-ms-win-core-com-l1-1-0.dll
    api-ms-win-core-libraryloader-l1-2-1.dll
    OLEAUT32.dll

  Summary

        1000 .00cfg
        D000 .data
        3000 .idata
        1000 .msvcjmc
       45000 .rdata
        E000 .reloc
      125000 .text
       88000 .textbss
        1000 .tls
```

### React Native for Windows のサンプルプロジェクトを再実行して今度は成功

通常のコマンドプロンプトに戻って、再び以下のコマンドを実行すると今度は起動できました。

```cmd
npx react-native run-windows --logging
```

元のコマンドプロンプトから、さらに以下のウィンドウが開きます。

* npm というタイトルのコマンドプロンプト。以下のような内容が出力されます。 `BUNDLE` のところはロード中はプログレスバーになっています（冒頭の動画参照）。

```
               ######                ######
             ###     ####        ####     ###
            ##          ###    ###          ##
            ##             ####             ##
            ##             ####             ##
            ##           ##    ##           ##
            ##         ###      ###         ##
             ##  ########################  ##
          ######    ###            ###    ######
      ###     ##    ##              ##    ##     ###
   ###         ## ###      ####      ### ##         ###
  ##           ####      ########      ####           ##
 ##             ###     ##########     ###             ##
  ##           ####      ########      ####           ##
   ###         ## ###      ####      ### ##         ###
      ###     ##    ##              ##    ##     ###
          ######    ###            ###    ######
             ##  ########################  ##
            ##         ###      ###         ##
            ##           ##    ##           ##
            ##             ####             ##
            ##             ####             ##
            ##          ###    ###          ##
             ###     ####        ####     ###
               ######                ######

                 Welcome to React Native!
                Learn once, write anywhere



To reload the app press "r"
To open developer menu press "d"

info Launching Dev Tools...
[Sat Jul 25 2020 11:22:17.922]  BUNDLE  ./index.js

[Sat Jul 25 2020 11:22:21.760]  BUNDLE  ./index.js

[Sat Jul 25 2020 11:22:27.229]  LOG      JavaScript logs will appear in your browser console
```

* React Native Debugger というタイトルのブラウザーのウィンドウ。
* プロジェクト名 `hello_react_native` のアプリケーションウィンドウ。

### React Native for Windows のサンプルプロジェクトを変更してみる

プロジェクト内の `App.tsx` をお好みのエディターで開いて `<Text>` の中の文字列を適当に変更して保存し、アプリケーションウィンドウに切り替えると即座に反映されていました。日本語もちゃんと表示されます。

```typescript
import {
  SafeAreaView,
  StyleSheet,
  ScrollView,
  View,
  Text,
  StatusBar,
} from 'react-native';
```

に `TextInput,` を追加し、適当な `<View>` の子供に `<TextInput />` を追加して保存すると、テキスト入力欄が表示されました。
Microsoft IME での日本語入力も問題なく実行でき、 Backspace キーでの削除も正しく1文字ずつ削除できました。

## React Native for macOS

### 必要なソフトウェアのインストール

[microsoft/react-native-macos: A framework for building native macOS apps with React.](https://github.com/microsoft/react-native-macos) の
[Requirements](https://github.com/microsoft/react-native-macos#requirements) から
[System Requirements](https://microsoft.github.io/react-native-windows/docs/rnm-dependencies) を開き、書かれている手順に従います。

* Xcode 11.3.1 以降をインストール。
* Xcode Command Line Tools をインストール。
    1. Xcode を起動し、 Xcode の "Preferences..." メニューを選択。
    2. Locations パネルを選んで Command Line Tools のドロップダウンで最新のバージョンを選択（私の場合は選択肢は1つだけでした）。
* CocoaPods をインストール。ターミナルで以下のコマンドを実行します。

```
sudo gem install cocoapods
```

* [macOS（またはLinux）用パッケージマネージャー — Homebrew](https://brew.sh/index_ja) で [Node.js](https://nodejs.org/en/) のバージョン 12 LTS 以降をインストール。ターミナルで以下のコマンドを実行します。

```
brew install node
```

* 同様に [Watchman A file watching service | Watchman](https://facebook.github.io/watchman/) をインストールします。

```
brew install watchman
```

### React Native for macOS のサンプルプロジェクトを試してみる

[Getting Started](https://github.com/microsoft/react-native-macos#getting-started) から
[Getting Started Guide](https://microsoft.github.io/react-native-windows/docs/rnm-getting-started) を開き、書かれている手順に従って実行します。

まずプロジェクトを作成しますが、ここでは書かれている手順とは違い、上記の React Native for Windows での手順に従って TypeScript 用にプロジェクトを作成します。
プロジェクト名は上記の React Native for Windows のときと同じ `hello_react_native` としました。
なお `--template` の後の引数はシングルクォートで囲まないと zsh のエラーになりました。

```zsh
npx react-native init hello_react_native --template 'react-native-template-typescript@6.4.*'
```

プロジェクトが作成されたら、プロジェクトのディレクトリに移動します。

```zsh
cd hello_react_native
```

React Native for macOS のパッケージをインストールします。

```zsh
npx react-native-macos-init
```

以下のコマンドを実行してアプリケーションを起動します。 `run-macos` のほうは `--logging` を指定すると `error: unknown option` となったので付けずに実行します。

```cmd
npx react-native run-macos
```

起動すると以下の2つのウィンドウが開きました。

* Metro Bundler というタイトルのターミナルのウィンドウ。以下のような内容が出力されていました。

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Running Metro Bundler on port 8081.                                         │
│                                                                              │
│  Keep Metro running while developing on any JS projects. Feel free to        │
│  close this tab and run your own Metro instance if you prefer.               │
│                                                                              │
│  https://github.com/facebook/react-native                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Looking for JS files in
   /Users/hnakamur/hello_react_native 

Loading dependency graph, done.

To reload the app press "r"
To open developer menu press "d"

 BUNDLE  [macos, dev] ./index.js ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100.0% (474/474), done.
```

* プロジェクト名の `hello_react_native` というタイトルのアプリケーションウィンドウ

### React Native for macOS のサンプルプロジェクトを変更してみる

「React Native for Windows のサンプルプロジェクトを変更してみる」と同様に変更してこちらも期待通り動作することを確認しました。

## おわりに

少し苦労しましたがとりあえず動かせるようになりました。

あとは冒頭の動画によると [GitHub - microsoft/fluentui-react-native: A react-native component library that implements the Fluent Design System.](https://github.com/microsoft/fluentui-react-native) でキーボードフォーカスやアクセサビリティ対応もされるらしいので、こちらも気になります。
README によるとまだアルファとのことですが今後に期待です。


