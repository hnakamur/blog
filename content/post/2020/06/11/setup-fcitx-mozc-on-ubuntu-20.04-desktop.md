---
title: "Ubuntu 20.04 LTS デスクトップでのfcitxとMozcの設定手順"
date: 2020-06-11T15:56:12+09:00
---

例によって自分用メモです。
英語キーボードを使っていて、言語は英語でインストールした想定です。

## キーボードのCapsLockとCtrl入れ替え

```console
sudo sed -i -e '/^XKBOPTIONS=/s/""/"ctrl:swapcaps"/' /etc/default/keyboard
```

## 日本語環境の追加インストール

1. Settings 画面を開いて左のリストで [Region & Language] を選び、右の [Manage Installed Languages] をクリック
2. "The language support is not installed completely" というメッセージボックス
が出たら [Install] ボタンを押す
3. Language Support ダイアログの [Close] ボタンを押して閉じる
4. ターミナルで `sudo apt update && sudo apt -y install fcitx-mozc` を実行して fcitx-mozc をインストール
5. [Manage Installed Languages] ボタンを再度押して [Language Support] ダイアログの [Keyboard input method system] を fcitx に変更して [Close] ボタンを押す
6. ターミナルで `sudo apt -y purge ibus` で ibus をアンインストール
7. ここで一度再起動

## fcitx の設定

1. 画面右上のキーボードの形のアイコンをクリックして [Confiugre Current Input Method] メニューを選択
2. [Input Method Configuration] ダイアログで左下の [+] ボタンを押し [Only Show Current Language] のチェックを外して、その下の検索欄に Mozc と入力し、上のリストに表示された Mozc の行を選んで [OK] ボタンを押す
3. [Input Method Configuration] ダイアログの [Global Config] タブを開いて [Trigger Input Method] の右の Ctrl+Space のところをクリックして Alt+\` に変更
3. 端末を開いて Ctrl+Space を押すと Mozc が使えることを確認
4. Settings 画面を開いて左のリストで [Keyboard Shortcuts] を選び、右のリストで [Switch windows of an application] を選んでデフォルトの Super+\` から Super+F1 など別のキーに変える
5. Ctrl+Alt+T を押してターミナルを開き、 Alt+\` で Mozc が起動することを確認
