---
layout: post
title: "Build UIAutomation samples in Windows SDK 7.1"
date: 2015-01-25 16:50:44 +0900
comments: true
categories: windows-sdk
---
## Windows SDK 7.1 をインストール

[Download Microsoft Windows SDK for Windows 7 and .NET Framework 4 from Official Microsoft Download Center](http://www.microsoft.com/en-us/download/details.aspx?id=8279)からダウンロード、インストールします。後でMSBuild.exeを使うため、Installation Optionsのツリーでは.NET Developmentを外さずに入れるようにしてください。

## サンプルソースをコピー

サンプルソースは C:\Program Files\Microsoft SDKs\Windows\v7.1\Samples\winui\uiautomation\ にありますが、ここだと一般ユーザで書き込みができないのでホームディレクトリ以下に作業ディレクトリを作ってコピーします。

## ビルド用にコマンドプロンプトを起動

[スタートメニュー]/[Microsoft Windows SDK v7.1]/[Windows SDK 7.1 Command Prompt]メニューでコマンドプロンプトを起動します（通常のコマンドプロンプトだとMSBuild.exeがPATHに入っていません）。


## サンプルのビルド

例としてUIAFragmentProviderのサンプルをビルドする場合です。

```
cd C:\Users\user\Documents\uiautomation_samples\UIAFragmentProvider\CPP
vcupgrade UIAFragmentProvider.vcproj
setenv /x86
msbuild UIAFragmentProvider.vcxproj
```

C:\Users\user\Documents\uiautomation_samples\UIAFragmentProvider\CPP\Debug\UIAFragmentProvider.exe が生成されます。
