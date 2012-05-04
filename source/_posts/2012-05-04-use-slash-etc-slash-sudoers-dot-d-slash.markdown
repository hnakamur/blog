---
layout: post
title: "/etc/sudoers.d/を使う"
date: 2012-05-04 11:16
comments: true
categories: [CentOS, sudo]
---
これまでいつも/etc/sudoersを編集していたのですが、よくみるとファイル末尾に

```
## Read drop-in files from /etc/sudoers.d (the # here does not mean a comment)
#includedir /etc/sudoers.d
```

と書いてあって、/etc/sudoers.d/にファイルを置けば/etc/sudoersを編集しなくても済むんですね。（しかしなんでincludedirには#をつける仕様なんだろ。今までずっとコメントアウトされていると思ってました。その上のコメント行に#ついててもコメントじゃないと書いてあるのに気づいたのが今日です）

/etc/sudoers.d/hnakamur を
```
Defaults:hnakamur !requiretty
hnakamur ALL=(ALL)      NOPASSWD: ALL
```
として試してみました。

sudoすると
```
sudo: /etc/sudoers.d/hnakamur is mode 0644, should be 0440
```
というエラー。

```
chmod 0440 /etc/sudoers.d/hnakamur
```
して再度試すとOKでした。

visudoではこのファイルは編集対象ではないので、複数人で同時に編集しないよう連絡しあうなどの運用が別途必要です。このせいでみんな使ってないんだろうか？

## /etc/sudoers.d/\* の罠にはまった
(2012-05-05 追記)

使うべきでない理由がわかりました！

/etc/sudoers.d/*のファイルで文法エラーのまま保存してしまうと、次にsudoを実行した時に以下の様なエラーが出ました。

```
$ sudo -s
>>> /etc/sudoers.d/hnakamur: syntax error near line 2 <<<
sudo: parse error in /etc/sudoers.d/hnakamur near line 2
sudo: no valid sudoers sources found, quitting
```

こうなるとsu -でrootになるしかないです。/etc/sudoers.d/*を使わずvisudoで編集する場合は、保存時に文法エラーがある場合は抜けずに再編集が可能なので安全です。

## visudoを使えば/etc/sudoers.d/\* でも大丈夫
(2012-05-05 追記)

さらに追記。visudoは/etc/sudoers.d/*に文法がエラーがある場合も抜ける前にプロンプトが出ました。人手で編集するときは必ずvisudoを使うよう肝に銘じます。
