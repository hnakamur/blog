---
layout: post
title: "IAM管理コンソールでAWSの管理画面用のユーザを作成"
date: 2013-02-09 09:37
comments: true
categories: [AWS, AIM]
---
AWS (Amazon Web Services)の管理コンソールを複数人で使う場合に大元のIDとパスワードを共有するのは避けたい場合、IAMでユーザを作成するのがよいと[@fujiwara](https://twitter.com/fujiwara)さんに教わりました。これは実際に試した時のメモです。

なお、IAMはIdentity and Access Managementの略です。

## 管理者: AIMユーザのログインURLの設定

初期状態では https://{ランダムな数字}.signin.aws.amazon.com/console のようなURLになっていますが、好きなサブドメインに変更が可能です。

1. AWSの管理コンソールにログイン
2. [IAM]をクリック
3. 左のメニューで[Dashboard]をクリック
4. [Create Account Alias]ボタンを押し、[Account Alias]にサブドメインを入力します。すると https://{入力したサブドメイン}.signin.aws.amazon.com/console がログインURLになります。

元に戻したい場合は[Remove Account Alias]ボタンを押します。

## 管理者: AIMユーザの作成

### ユーザの作成とAPIアクセスキーのダウンロード
1. AWSの管理コンソールにログイン
2. [IAM]をクリック
3. 左のメニューで[Users]をクリック
4. 上のツールバーで[Create New Users]ボタンを押す
5. [Create User]ダイアログで[Enter User Names:]に作成したいユーザのIDを入力。
   * 同時に5人までつくれるようです(実際に試したのは1人だけです)。
   * AWSサービスのAPIを使う場合は[Generate an access key for each User]チェックボックスをオンのままにしておきます。ここでオフにしていても後からキーを発行できるので、不明の場合はオフでいいです。
6. [Create User]ダイアログで[Create]ボタンを押す
7. [Download Credentials]ボタンを押して、"User Name","Access Key Id","Secret Access Key"が書かれたCSVファイルをダウンロード
8. [Close Windows]ボタンを押す

### ユーザの初期パスワード作成とダウンロード

1. ユーザ一覧でユーザを選択して、上のツールバーの[User Actions]ボタンを押すか、右クリックのポップアップメニューから[Manage Password]メニューを選択
2. [Manage Password]ダイアログで[Assign an auto-generated password]ラジオボタンを選択した状態で[Apply]ボタンを押す
3. [Download Credentials]ボタンを押し、"User Name","Password","Direct Signin Link"が書かれたCSVファイルをダウンロード
4. [Close Windows]ボタンを押す

## 利用者: 初回ログインとパスワード変更

1. "User Name","Password","Direct Signin Link"が書かれたCSVファイルのURLをブラウザで開き、ID、パスワードを入力してログインします。
2. ツールバー右上のユーザIDのドロップダウンメニューを開き、[Security Credentials]を選択
3. 現在のパスワードと新しいパスワードを入力して[Change Password]ボタンを押して変更

## 管理者: 利用者のパスワード変更
ユーザ一覧でポップアップメニューの[Manage Password]メニューから変更できます。

## 管理者: 利用者のAPIアクセスキー追加、削除
ユーザ一覧でポップアップメニューの[Manage Access Keys]メニューから変更できます。

## 管理者: 利用者のユーザ削除
ユーザ一覧でポップアップメニューの[Delete User]メニューから削除できます。
