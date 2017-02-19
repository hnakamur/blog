Title: Build UIAutomation samples in Windows SDK 7.1
Date: 2015-01-25 00:00
Category: blog
Tags: windows-sdk
Slug: 2015/01/25/build-uiautomation-samples-in-windows-sdk-7-dot-1

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
