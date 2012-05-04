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
