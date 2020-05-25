---
title: "macOSでHypervisor.frameworkのVMのサブネットIPアドレスを変える"
date: 2020-05-25T14:10:55+09:00
---
## はじめに

[Troubleshooting networking on macOS | Multipass documentation](https://multipass.run/docs/troubleshooting-networking-on-macos) に Hypervisor.framework のVMのIPアドレスの変更方法が書いてあるのを見つけて試してみたのでメモ。

## multipass のVM停止

```console
multipass stop
```

## vmnet の設定変更

`/Library/Preferences/SystemConfiguration/com.apple.vmnet.plist` という設定ファイルにVMのサブネットのアドレス設定があります。

ちなみに vmnet macOS で検索すると macOS には vmnet というframeworkがあることがわかりました。
[vmnet | Apple Developer Documentation](https://developer.apple.com/documentation/vmnet) 

拡張子の `.plist` はプロパティリスト形式の設定ファイルを意味しています。

以下のコマンドを実行して編集します。

```console
sudo vim /Library/Preferences/SystemConfiguration/com.apple.vmnet.plist
```

ファイルの最後の方に以下のような行があります。

```xml
        <key>Shared_Net_Address</key>
        <string>192.168.64.1</string>
        <key>Shared_Net_Mask</key>
        <string>255.255.255.0</string>
```

`Shared_Net_Address` をお好みで `192.168.255.1` などと変更します。

[Troubleshooting networking on macOS | Multipass documentation](https://multipass.run/docs/troubleshooting-networking-on-macos) の
"Possible other option - configure Multipass to use a different subnet?" には `192.168.` が multipass 内にハードコーディングされているので `192.168.` 以外にはしないよう書かれています。ソースコードを検索した限りではそうでもなさそうでしたが、 `192.168.` 以外のアドレスは試していません。

## DHCP のリースファイル削除

私の環境では multipass で primary という名前でVMを作っていて、それが 192.168.64.2 というIPアドレスでしたが、
`/var/db/dhcpd_leases` が以下のような内容になっていました。

```text
{
        name=primary
        ip_address=192.168.64.2
        hw_address=1,XX:XX:XX:X:XX:XX
        identifier=1,XX:XX:XX:X:XX:XX
        lease=0x5ecc5f63
}
```

`hw_address` と `identifier` のMACアドレスは伏せてますが、VMの `enp0s2` インタフェースのMACアドレスで先頭の0は外したものになっていました。

以下のコマンドでDHCPのリースファイルを削除します。

```console
sudo rm /var/db/dhcpd_leases
```

## multipass のVM起動

以下のコマンドで起動します。

```console
multipass start
```

以下のよう起動がタイムアウトになる場合がありました。

```console
% multipass start
start failed: The following errors occurred:                                    
primary: timed out waiting for response
```

`multipass list` で確認すると状態が Unknown で IPv4 アドレスも不明になっています。

```console
% multipass list 
Name                    State             IPv4             Image
primary                 Unknown           --               Ubuntu 18.04 LTS
```

試しに再度 `multipass start` を実行してみると、今度は成功して `multipass list` でも正しく状態が確認できるようになりました。

```console
% multipass list
Name                    State             IPv4             Image
primary                 Running           192.168.64.2     Ubuntu 18.04 LTS
```
