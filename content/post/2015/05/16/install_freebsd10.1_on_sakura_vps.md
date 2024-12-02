+++
Categories = []
Description = ""
Tags = ["sakura-vps", "freebsd"]
date = "2015-05-16T11:39:29+09:00"
title = "さくらのVPSにFreeBSD 10.1をクリーンインストールした時のメモ"

+++
## はじめに

さくらのVPSにFreeBSD 10.1をクリーンインストールしてみましたので、手順をメモしておきます。作業した環境は MacBook Pro (USキーボード) です。
インストール後以下の設定を行います。

* ファイルシステムはZFSを選択
* sshの鍵認証の設定
* sudoのインストールと設定

なお、インストールには下記のページを参考にしました。ありがとうございます！

* [FreeBSD 10.1 導入 — emaita 備忘録](http://blog.emaita.jp/2015/03/06/freebsd10_1.html)
* [\[FreeBSD\] さくらのVPSに FreeBSD 9.1 amd64 をインストールする方法 (1) : saba nano - へっぽこ管理者のサーバ管理日誌（LV.2）](http://blog.livedoor.jp/saba_nano/archives/28363307.html)

## インストール準備
### ISOイメージをミラーから取得してVPSにsftpでアップロード

[FreeBSD-related Sites in Japan](http://www.jp.freebsd.org/mirror.html)を見てftp3.jp.FreeBSD.org (ftp.sakura.ad.jp)からダウンロードすることにしました。

ブラウザで
ftp://ftp3.jp.freebsd.org/pub/FreeBSD/releases/ISO-IMAGES/10.1/
を開き
ftp://ftp3.jp.freebsd.org/pub/FreeBSD/releases/ISO-IMAGES/10.1/FreeBSD-10.1-RELEASE-amd64-bootonly.iso
をダウンロードします。

これを[ISOイメージインストール｜さくらインターネット公式サポートサイト](https://help.sakura.ad.jp/app/answers/detail/a_id/2405)の手順を参考にアップロードします。

OS Xにはsftpコマンドが標準で入っているのでそれを使います。接続情報は、さくらのVPSのコントロールパネルで確認します。
ここでは、ユーザ名をvpsXXXXXXXXXXXX, ホスト名をvps-isoY.sakura.ad.jpとして説明します。

isoファイルのあるディレクトリでsftpを実行し、以下の手順で上記のisoファイルをアップロードします。

```
$ sftp vpsXXXXXXXXXXXX@vps-isoY.sakura.ad.jp
vpsXXXXXXXXXXXX@vps-isoY.sakura.ad.jp's password: (パスワードを入力)
sftp> cd iso
sftp> put FreeBSD-10.1-RELEASE-amd64-bootonly.iso
sftp> quit
```

アップロードが完了したらsftpコマンドは終了します。さくらのVPSのコントロールパネルの「ISOイメージインストール」のポップアップの「ISOイメージ情報」に今アップロードしたisoファイルが表示されたことを確認し、「マウント設定」の「設定内容を確認する」ボタンを押し、「インストールを実行する」ボタンを押します。

## インストール

「VNCコンソール(HTML5版)を起動」ボタンを押してコンソールで作業します。

### キーマップの確認

HTML5版のVNCコンソールは、どうも日本語キーボードを想定しているようで、USキーボードだと以下のように一部の記号の配置が異なっています。
なお、キーマップはデフォルト(US配列)を選択しています。

押したキーを左、入力された文字を右に示します。

|押したキー|入力された文字|
|----------|--------------|
|`` ` ``|`[`|
|``~ (Shift+`)``|`+`|
|`@ (Shift+2)`|`{`|
|`^ (Shift+6)`|`+`|
|`& (Shift+7)`|`^`|
|`* (Shift+8)`|`"`|
|`( (Shift+9)`|`*`|
|`) (Shift+0)`|`(`|
|`_ (Shift+-)`|何も入力されない|
|`=`|`-`|
|`+ (Shift+=)`|`:`|
|`[`|`]`|
|`{ (Shift+[)`|`}`|
|`]`|`\`|
|`} (Shift+})`|`|`|
|`\`|何も入力されない|
|`\| (Shift+\)`|何も入力されない|
|`: (Shift+;)`|`"`|
|`'`|`7`|
|`" (Shift+')`|`@`|

### ホスト名設定

"Please choose a hostname for this machine."の画面ではVPSのコンソールの標準ホスト名を入力します。

### インストールするコンポーネントの選択

初期選択状態は以下のようになっていました。

* [ ] doc: Additional documentation
* [*] games: Games (fortune, etc.)
* [*] lib32: 32-bit compatiblity libraries
* [*] ports: Ports tree
* [ ] src: System source code

gamesとlib32を外して、docとsrcを追加しました。

### ネットワーク設定

* 「Network Configuration」では「vtnet0」を選び「OK」を押します。
* "Would you like to configure IPv4 for this interface" → [Yes]を押す
* "Would you like to use DHCP to configure this interface?" → [No]を押す
* 「Static Netowrk Interface Configuration」の画面でIP Address, Subnet Mask, Default Routerを入力します。VPSのコントロールパネルのIPv4のアドレス、ネットマスク、ゲートウェイの値をそれぞれ入力します。
* "Would you like to configure IPv6 for this interface?" → NoYes]を押す
* 「Resolver Configuration」の画面でSearch, IPv4 DNS #1, IPv4 DNS #2を入力します。順にVPSコントロールパネルの標準ホスト名のドメイン部分(私の場合はvs.sakura.ne.jp)、IPv4のプライマリDNS、セカンダリDNSを入力します。


#### (ボツ) IPv6を有効にすると失敗しました
* "Would you like to configure IPv6 for this interface?" → [Yes]を押す
* "Would you like to try stateless address autoconfiguration (SLAAC)?" → [No]を押す
* 「Static IPv6 Network Interface Configuration」の画面でIPv6 AddressとDefault RouterにVPSのコントロールパネルのIPv6のアドレスとゲートウェイを入力します。上記のキーマップの確認に書いたように:を入力するにはUSキーボードではShift+=を押してください。
* 「Resolver Configuration」の画面でSearch, IPv6 DNS #1, IPv6 DNS #2, IPv4 DNS #1, IPv4 DNS #2を入力します。順にVPSコントロールパネルの標準ホスト名のドメイン部分(私の場合はvs.sakura.ne.jp)、IPv6のDNS、空欄、IPv4のプライマリDNS、セカンダリDNSを入力します。

ダウンロードは無事に進んだようなのですが、その後以下のエラーが出ました。

```
Abort
Distribution extract failed

An installation step has been aborted. Would you
like to restart the installation or exit
the installer?
```

### ミラーサイト選択

「Mirror Selection」の画面では「ftp://ftp3.jp.freebsd.org Japan #3」を選択します。

### パーティション作成

* Auto (UFS): Guided Disk Setup
* Manual: Manual Disk Setup (experts)
* Shell: Open a shell and partition by hand
* Auto (ZFS): Guided Root-on-ZFS

今回は「Auto (ZFS)」にしました。
「ZFS Configuration」ではそのまま「>>> Install     Proceed with Installation」を選びます。

### ZFSの仮想デバイスタイプ

* stripe: Stripe - No Redundancy
* mirror: Mirror - n-Way Mirroring
* raidz1: RAID-Z1 - Single Redundant RAID
* raidz2: RAID-Z2 - Single Redundant RAID
* raidz3: RAID-Z3 - Single Redundant RAID

「stripe」を選びました。

### ブロックデバイス選択
「vtbd0 VirtIO Block Device」をスペースキーを押して選択します。

"Last Chance! Are you sure you want to destroy the current contents of the following disks: vtbd0" では[YES]を選びます。

### rootユーザのパスワード設定

以下のようにrootユーザのパスワードを設定します。なぜかreturnキーが効かないようなのでCtrl-Jで代用しました。

```
Please select a password for the system management account (root):
Changing local password for root
New Password: (パスワードを入力してCtrl-Jを押す)
Retype New Password: (パスワードを入力してCtrl-Jを押す)
```

表示も変で、Ctrl-Jを押した時に行が次の行に進みますが、行頭には戻らず続きのカラムから表示されていました。

### タイムゾーン設定

"Is this machine's CMOS clock set to UTC?  If it is set to local time, or you don't know, please choose NO here!" ではハードウェアの設定はわからないので「No」を選びます。

「Select a region」では「5 Asia」を選び、「Select a country or region」では「18 Japan」を選びます。
"Does the abbreviation `JST' look reasonable?"に「Yes」を選びます。

### 自動起動するサービス選択

```
Choose the services you would like to be started at boot:
  [ ] local_unbound  Local caching validating resolver
  [*] sshd           Secure shell daemon
  [ ] moused         PS/2 mouse pointer on console
  [ ] ntpd           Synchronize system and network time
  [ ] powerd         Adjust CPU frequency dynamically if supported
  [*] dumpev         Enable kernel crash dumps to /var/crash
```
ntpdを追加選択します。

### ユーザ追加

sshでログインする管理用のユーザとして「admin」という名前のユーザを追加することにします。あとでsudoersに追加するのでadminユーザのセカンダリグループにwheelを追加します。

"Would you like to add users to the installed systems now?"に「Yes」を選びます。

```
Add Users
Username: admin
Full name: admin
Uid (Leave empty for default): (Ctrl-Jを押す)
Login group [admin]: (Ctrl-Jを押す)
Login group is admin. Invite admin into other groups? []: (wheelと入力してCtrl-Jを押す)
Login class [default]: (Ctrl-Jを押す)
Shell (ch csh tcsh nologin) [sh]: (Ctrl-Jを押す)
Home directory [/home/admin]: (Ctrl-Jを押す)
Home directory permissions (Leave empty for default): (Ctrl-Jを押す)
Use password-based authentication? [yes]: (Ctrl-Jを押す)
Use an empty password? (yes/no) [no]: (Ctrl-Jを押す)
Use a random password? (yes/no) [no]: (Ctrl-Jを押す)
Enter password: (パスワードを入力してCtrl-Jを押す)
Enter password again: (パスワードを入力してCtrl-Jを押す)
Lock out the accout after creation? [no]: (Ctrl-Jを押す)
OK? (yes/no): (yesと入力してCtrl-Jを押す)
adduser: INFO Successfully added (admin) to the user database.
Add another user? (yes/no): (noと入力してCtrl-Jを押す)
```

### インストールの終了

```
Setup of you FreeBSD system is nearly complete.  You can now
modify your configuration choices. After this screen, you will
have an opportunity to make more complex changes using a shell.
```

上記の画面では「Exit」を選択して「OK」を押します。

```
The installation is now finished.
Before exiting the installer, yould
you like to open a shell in the new
system to make any final manual
modifications?
```

上記の画面では「No」を選択します。

```
Installation of FreeBSD
complete! Would you like
to reboot into the
installed system now?
```

上記の画面では「Reboot」を押しても、またインストーラの画面が起動してしまいます。
そこで、さくらのVPSのコンソールで「OSインストール」→「ISOイメージインストール」を選び、「ISOイメージアップロード情報」の「アカウントの削除」ボタンを押します。
「アカウントを削除してよろしいですか？アップロードしたファイルも削除されます。」と表示されたら「削除する」ボタンを押します。

その後「ISOイメージインストール」のポップアップで「キャンセル」を押してVPSのコンソールに戻りツールバーの「強制停止」ボタンを押して停止した後「起動」ボタンを押して起動します。

## インストール後の設定

### adminユーザの公開鍵の設置

ここでは、OS X側で秘密鍵・公開鍵を作成済みとし、秘密鍵は ~/.ssh/id_rsa、公開鍵は ~/.ssh/id_rsa.pub とします。

OSX上で以下の操作を行い、公開鍵をサーバに転送します。

```
scp ~/.ssh/id_rsa.pub admin@サーバのIPアドレス:
```

adminユーザのパスワードを聞かれるので入力します。

その後sshでサーバにログインします。

```
ssh admin@サーバのIPアドレス
```

パスワードを入力すると以下のようなメッセージが表示されます。アドレスのXXX.XXX.XXX.XXXとRSA鍵のフィンガープリントはここでは伏せていますが実際は異なる値になります。「yes」と入力してログインしてください。

```
The authenticity of host 'XXX.XXX.XXX.XXX (XXX.XXX.XXX.XXX)' can't be established.
RSA key fingerprint is yy:yy:yy:yy:yy:yy:yy:yy:yy:yy:yy:yy:yy:yy:yy:yy.
Are you sure you want to continue connecting (yes/no)?
```

パスワードを入力してサーバにログインしたらサーバ上で以下のコマンドを実行し、カギ認証でログインできるようにします。

```
mkdir ~/.ssh
chmod 700 ~/.ssh
mv id_rsa.pub ~/.ssh/authorized_keys
```

今度はOS X側で ~/.ssh/configというファイルが無い場合は新規作成した上で、以下の内容を追加します。

```
Host 接続に使用するお好みのホスト名エイリアス
  Hostname サーバのIPアドレス
  User admin
  PasswordAuthentication no
  IdentityFile ~/.ssh/id_rsa
```

IdentityFileの行は ~/.ssh/id_rsa はデフォルト値なので、この場合はこの行自体不要です。別のファイル名にしていた場合は設定が必要です。

この設定を加えた状態で、OS Xから以下のようにコマンドを実行しパスワードを聞かれずにログインできれば成功です。

```
ssh ホスト名エイリアス
```

### sshパスワード認証の無効化

鍵認証でssh接続できるようになったら、悪意を持った第三者の攻撃でパスワードを当ててログインされてしまうのを防ぐため、パスワードでのログインを無効にします。

サーバ上で以下の手順を実行します。まず以下のコマンドを実行してrootユーザになります。

```
su -
```

rootユーザのパスワードを聞かれますので入力します(1行が長いのでブラウザでコピペする際は右の方までスクロールしてください)。

```
sed -i .orig -e 's/^#\(PasswordAuthentication no\)/\1/;s/^#\(UsePAM\) yes/\1 no/;s/^#\(X11Forwarding\) yes/\1 no/' /etc/ssh/sshd_config
```

```
less /etc/ssh/sshd_config
```

で設定内容を確認します。

```
…(略)…
PasswordAuthentication no
…(略)…
UsePAM no
…(略)…
X11Forwarding no
…(略)…
```

となっていればOKですのでqを押してlessを終了します。

以下のコマンドを実行してsshdを再起動します。

```
/etc/rc.d/sshd restart
```

次に実際にパスワード認証が無効化されたことを確認します。

一旦このrootユーザの接続は残しておいて、OS X上で別のターミナルを開き、~/.ssh/configを以下のように編集します。

```
Host 接続に使用するお好みのホスト名エイリアス
  Hostname サーバのIPアドレス
  User admin
  PasswordAuthentication yes
  PubkeyAuthentication no
  #PasswordAuthentication no
  #IdentityFile ~/.ssh/id_rsa
```

この状態で

```
ssh ホスト名エイリアス
```

のようにコマンドを実行した時にパスワードを聞かれることなく以下のように表示されれば、パスワード認証は正しく無効化できています。

```
Permission denied (publickey,keyboard-interactive).
```

上記の確認ができたらOS Xの~/.ssh/configは元の内容に戻しておいてください。


### セキュリティパッチの適用

先ほどのrootで接続していたターミナルに戻ってセキュリティパッチを適用します。

[18.2. FreeBSD Update](https://www.freebsd.org/doc/ja_JP.eucJP/books/handbook/updating-upgrading-freebsdupdate.html)の「セキュリティパッチの適用」の項を参考にします。

[Bug 198030 – /usr/src/crypto/openssl/util/mkbuildinf.pl: No such file or directory on freebsd-update install](https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=198030)のバグを回避するため
[Comment 7](https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=198030#c7)の手順を実行してから、パッチを適用します。

```
# freebsd-update fetch
# mkdir -p /usr/src/crypto/openssl/util
# freebsd-update install
```

`freebsd-update patch` を実行すると、アップデートを取得後moreコマンドが起動して更新されたファイル一覧を確認できます。スペースキーを押してページを進め、確認したらqを押して終了します。

### sudoのインストールと設定

rootユーザで以下のコマンドを実行します。

```
pkg install -y sudo
```

すると以下のようにpkgコマンド自体をインストールするか聞かれますので、yと入力します。

```
The package management tool is not yet installed on your system.
Do you want to fetch and install it now? [y/N]:
```

pkgとsudoのインストールが終わったら、以下のコマンドを実行してsudoの設定を変更します。

```
visudo
```

ここではwheelグループにsudoを許可します。

```
# %wheel ALL=(ALL) ALL
```

の行を

```
%wheel ALL=(ALL) ALL
```

のように変更して:wqで保存して終了します。

sudoの設定を確認するため、rootのターミナルは一旦置いておいて、OS Xからsshでadminユーザでログインし、以下のコマンドを実行します。

```
sudo -i
```

以下のようにメッセージが表示されますので、adminユーザのパスワードを入力します。
rootユーザのプロンプトが出れば成功です。

```
$ sudo -i

We trust you have received the usual lecture from the local System
Administrator. It usually boils down to these three things:

    #1) Respect the privacy of others.
    #2) Think before you type.
    #3) With great power comes great responsibility.

Password:
root@ホスト名からドメインを除いたもの:~ #
```

確認できたら、このターミナルでCtrl-Dを押してadminユーザに戻り、さらにCtrl-Dを押してログアウトします。
先程残しておいたrootユーザのターミナルも同様にしてログアウトします。

## おわりに

いくつかハマりどころがありましたが、さくらのVPSにFreeBSD 10.1をクリーンインストールできました。
