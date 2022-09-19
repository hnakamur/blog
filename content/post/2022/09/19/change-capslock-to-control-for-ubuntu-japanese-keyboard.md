---
title: "Ubuntuで日本語キーボードのCapsLockをControlに変更する"
date: 2022-09-19T10:25:42+09:00
---
## はじめに
英語キーボードだけ使うようになって随分経つのですが、また日本語キーボードも併用できるようにしようと日本語キーボードも使い始めています。

## 英語キーボードでCapsLockとControl入れ替え

英語キーボードのときは以下のように設定変更してCapsLockとControlと入れ替えていました。

```bash
sudo sed -i 's/^XKBOPTIONS=.*/XKBOPTIONS="ctrl:swapcaps"/' /etc/default/keyboard
```

XKBOPTIONSの設定値は /usr/share/X11/xkb/rules/xorg.lst に書いてあります (`man 5 keyboard` のFILESセクションで知りました)。

反映はGNOMEをログアウト、ログインにしていましたが、[Ubuntu/Caps-LockキーをCtrlキーにする方法 - Linuxと過ごす](https://linux.just4fun.biz/?Ubuntu/Caps-Lock%E3%82%AD%E3%83%BC%E3%82%92Ctrl%E3%82%AD%E3%83%BC%E3%81%AB%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95) によると `sudo systemctl restart console-setup` で良いそうです。

## 日本語キーボードではCapsLockをControlに置き換え

CapsLockとControl入れ替えだとControl+Shiftを押したときにCapsLockが動いてしまうことがわかりました。

ターミナルでのコピーとペーストに Control+Shift+C と Control+Shift+V を多用するのでこれはつらいです。

そこで以下のようにCapsLockをControlにする設定を試してみました。

```bash
sudo sed -i 's/^XKBOPTIONS=.*/XKBOPTIONS="ctrl:nocaps"/' /etc/default/keyboard
```

が、これでも Control+Shift を押したときに CapsLock が動いてしまうようです。

`gsettings` で `org.gnome.desktop.input-sources` の `xkb-options` を確認してみたところ、以下のように `ctrl:swapcaps` になっていました。

```
$ gsettings get org.gnome.desktop.input-sources xkb-options
['ctrl:swapcaps']
```

以下のように `gsettings` でも `ctrl:nocaps` に設定すると期待の動きになりました。 `gsettings set` は追加の操作なしで即座に反映されるようです。

```bash
gsettings set org.gnome.desktop.input-sources xkb-options "['ctrl:nocaps']"
```

## 余談: `ctrl:nocaps` と `caps:ctrl_modifier` の違い

検索してたら `caps:ctrl_modifier` というのもあることを知りました。
ただ `/usr/share/X11/xkb/rules/xorg.lst` の説明は以下のようになっていて違いがよくわかりません。

```
$ grep -E '(ctrl:nocaps|caps:ctrl_modifier)' /usr/share/X11/xkb/rules/xorg.lst
  ctrl:nocaps          Caps Lock as Ctrl
  caps:ctrl_modifier   Make Caps Lock an additional Ctrl
```

検索すると
[setxkbmap: What's the difference between caps:ctrl_modifier and ctrl:nocaps? : commandline](https://www.reddit.com/r/commandline/comments/4gusjx/setxkbmap_whats_the_difference_between_capsctrl/) で2つの定義などがコメントされていました。

Ubuntu 22.04 LTS の環境では以下のようになっていました。

`/usr/share/X11/xkb/symbols/ctrl`

```
…(略)…
// Eliminate CapsLock, making it another Ctrl.
partial modifier_keys
xkb_symbols "nocaps" {
    replace key <CAPS> { [ Control_L, Control_L ] };
    modifier_map  Control { <CAPS>, <LCTL> };
};
…(略)…
```

`/usr/share/X11/xkb/symbols/capslock`

```
…(略)…
// This changes the <CAPS> key to become a Control modifier,
// but it will still produce the Caps_Lock keysym.
hidden partial modifier_keys
xkb_symbols "ctrl_modifier" {
    replace key <CAPS> {
        type[Group1] = "ONE_LEVEL",
        symbols[Group1] = [ Caps_Lock ],
        actions[Group1] = [ SetMods(modifiers=Control) ]
    };
    modifier_map Control { <CAPS> };
};
…(略)…
```

私の用途では `ctrl:nocaps` で良さそうです。

上のコメントでは左右のShift同時押しでCapsLockにする設定 `shift:both_capslock` も紹介されていました。

`/usr/share/X11/xkb/symbols/shift`

```
…(略)…
// Toggle CapsLock when pressed together with the other Shift key.
partial modifier_keys
xkb_symbols "lshift_both_capslock" {
  key <LFSH> {
    type[Group1]="TWO_LEVEL",
    symbols[Group1] = [ Shift_L, Caps_Lock ]
  };
};
// Toggle CapsLock when pressed together with the other Shift key.
partial modifier_keys
xkb_symbols "rshift_both_capslock" {
  key <RTSH> {
    type[Group1]="TWO_LEVEL",
    symbols[Group1] = [ Shift_R, Caps_Lock ]
  };
};
partial modifier_keys
xkb_symbols "both_capslock" {
  include "shift(lshift_both_capslock)"
  include "shift(rshift_both_capslock)"
};
…(略)…
```
