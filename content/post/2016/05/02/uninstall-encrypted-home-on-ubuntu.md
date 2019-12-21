+++
Categories = []
Description = ""
Tags = ["crypt", "ubuntu"]
date = "2016-05-02T12:28:08+09:00"
title = "Ubuntuでホームディレクトリを暗号化するのを止めた"

+++
## 背景
[MacをPXEサーバにしてExpress5800/S70タイプRBにUbuntu16.04をインストールしてみた · hnakamur's blog at github](/blog/2016/05/01/install_ubuntu_xenial_with_pxe_boot/)でホームディレクトリを暗号化してみたのですが、OS起動後に鍵認証でsshしようとすると鍵は正しく指定しているのに `Permission denied (publickey).` と拒否されてしまうケースがありました。コンソールで一度ログインするとsshでもログイン出来るようになります。

これはホームディレクトリを暗号化した影響で `~/.ssh/authorized_keys` が読めない状態になっているようです。

## authorized_keys をホームディレクトリの外に置く手もある

[Ubuntu server ssh after reboot: Permission denied (publickey) - Ask Ubuntu](http://askubuntu.com/questions/254776/ubuntu-server-ssh-after-reboot-permission-denied-publickey/254787#254787)によると `/etc/ssh/sshd_config` で `AuthorizedKeysFile` の設定を変える手もあるようです。

変更前の状態は

```
#AuthorizedKeysFile     %h/.ssh/authorized_keys
```

とデフォルト値がコメントアウトされて書かれていました。

[Ubuntu Manpage: sshd_config — OpenSSH SSH daemon configuration file](http://manpages.ubuntu.com/manpages/precise/en/man5/sshd_config.5.html)によると `%h` はホームディレクトリに展開されます。ユーザ名に展開される `%u` というのもあるそうです。

ここでは `/etc/%u/.ssh/authorized_keys` に変更するのを試してみました。
先に自分のユーザID `hnakamur` 用のディレクトリを作って所有者を変更します。

```
sudo mkdir -p /etc/hnakamur/.ssh
sudo chmod -R 700 /etc/hnakamur
sudo chown -R hnakamur: /etc/hnakamur
```

```
cp ~/.ssh/authorized_keys /etc/hnakamur/.ssh/authorized_keys
```

その後 `sudo vi /etc/ssh/sshd_config` を実行し以下の行を追加します。

```
AuthorizedKeysFile /etc/%u/.ssh/authorized_keys
```

これでOSを再起動後、コンソールでログインしない状態でもsshで鍵認証でログンできることを確認しました。

ただし、ログインは出来ましたが、暗号化の解除は手動で行う必要がありました。作ったはずの `~/.bash_profile` が無いので気付きました。ホームディレクトリの中身は以下のようになっていました。

```
hnakamur@express:~$ ls -la
合計 8
dr-x------ 2 hnakamur hnakamur 4096  5月  2 01:31 .
drwxr-xr-x 4 root     root     4096  5月  2 01:31 ..
lrwxrwxrwx 1 hnakamur hnakamur   33  5月  2 01:31 .Private -> /home/.ecryptfs/hnakamur/.Private
lrwxrwxrwx 1 hnakamur hnakamur   34  5月  2 01:31 .ecryptfs -> /home/.ecryptfs/hnakamur/.ecryptfs
lrwxrwxrwx 1 hnakamur hnakamur   56  5月  2 01:31 Access-Your-Private-Data.desktop -> /usr/share/ecryptfs-utils/ecryptfs-mount-private.desktop
lrwxrwxrwx 1 hnakamur hnakamur   52  5月  2 01:31 README.txt -> /usr/share/ecryptfs-utils/ecryptfs-mount-private.txt
```

`README.txt` を見てみました。

```
hnakamur@express:~$ cat README.txt
THIS DIRECTORY HAS BEEN UNMOUNTED TO PROTECT YOUR DATA.

From the graphical desktop, click on:
 "Access Your Private Data"

or

From the command line, run:
 ecryptfs-mount-private
```

`ecryptfs-mount-private` を実行してログインパスワードを入力し `cd /home/hnakamur` でホームディレクトリに入り直すと、復号化された内容が見えるようになりました。

```
hnakamur@express:~$ ecryptfs-mount-private
Enter your login passphrase:
Inserted auth tok with sig [d094f2376006dce9] into the user session keyring

INFO: Your private directory has been mounted.
INFO: To see this change in your current shell:
  cd /home/hnakamur

hnakamur@express:~$ ls -la
合計 8
dr-x------ 2 hnakamur hnakamur 4096  5月  2 01:31 .
drwxr-xr-x 4 root     root     4096  5月  2 01:31 ..
lrwxrwxrwx 1 hnakamur hnakamur   33  5月  2 01:31 .Private -> /home/.ecryptfs/hnakamur/.Private
lrwxrwxrwx 1 hnakamur hnakamur   34  5月  2 01:31 .ecryptfs -> /home/.ecryptfs/hnakamur/.ecryptfs
lrwxrwxrwx 1 hnakamur hnakamur   56  5月  2 01:31 Access-Your-Private-Data.desktop -> /usr/share/ecryptfs-utils/ecryptfs-mount-private.desktop
lrwxrwxrwx 1 hnakamur hnakamur   52  5月  2 01:31 README.txt -> /usr/share/ecryptfs-utils/ecryptfs-mount-private.txt
hnakamur@express:~$ cd /home/hnakamur
hnakamur@express:~$ ls -la
合計 128
drwx------ 6 hnakamur hnakamur 4096  5月  2 12:43 .
drwxr-xr-x 4 root     root     4096  5月  2 01:31 ..
lrwxrwxrwx 1 hnakamur hnakamur   33  5月  2 01:31 .Private -> /home/.ecryptfs/hnakamur/.Private
-rw------- 1 hnakamur hnakamur 1908  5月  2 12:43 .bash_history
-rw-r--r-- 1 hnakamur hnakamur  220  5月  2 01:31 .bash_logout
-rw-r--r-- 1 hnakamur hnakamur  100  5月  2 08:50 .bash_profile
-rw-r--r-- 1 hnakamur hnakamur 3771  5月  2 01:31 .bashrc
drwx------ 2 hnakamur hnakamur 4096  5月  2 01:36 .cache
lrwxrwxrwx 1 hnakamur hnakamur   34  5月  2 01:31 .ecryptfs -> /home/.ecryptfs/hnakamur/.ecryptfs
-rw------- 1 hnakamur hnakamur   41  5月  2 09:00 .lesshst
-rw-r--r-- 1 hnakamur hnakamur  675  5月  2 01:31 .profile
drwx------ 2 hnakamur hnakamur 4096  5月  2 01:38 .ssh
-rw-r--r-- 1 hnakamur hnakamur    0  5月  2 01:38 .sudo_as_admin_successful
-rw------- 1 hnakamur hnakamur 6841  5月  2 12:43 .viminfo
drwxr-xr-x 2 hnakamur hnakamur 4096  5月  2 03:13 docs
drwxr-xr-x 5 hnakamur hnakamur 4096  5月  2 08:47 gocode
```

## LVM暗号化を使っているのでホームディレクトリの暗号化は止めることにした

[\[all variants\] Encrypted LVM vs Encrypted Home](http://ubuntuforums.org/showthread.php?t=1335046)を見ると、ホームディレクトリを暗号化してもスワップや `/tmp` などが暗号化されていないので情報漏えいのリスクがあるので、ホームディレクトリの暗号化よりもLVMの暗号化のほうが良いとのことです。

そもそも自宅サーバでユーザは私だけということもあり、ホームディレクトリの暗号化は止めることにしました。

以下のページを参考にしつつやってみました。

* [How to Disable Home Folder Encryption After Installing Ubuntu](http://www.howtogeek.com/116179/how-to-disable-home-folder-encryption-after-installing-ubuntu/)
* [EncryptedHome - Community Help Wiki](https://help.ubuntu.com/community/EncryptedHome)

バックアップ用のディレクトリを作って、所有者を変えます。

```
sudo mkdir /home/hnakamur.backup
sudo chown hnakamur:hnakamur /home/hnakamur.backup
```

`tar` でバックアップして `.encryptfs` ディレクトリは消します。シンボリックリンクもそのままコピーしたいので `tar` を使っています。

```
(cd /home/hnakamur; tar cf - .) | (cd /home/hnakamur.backup; tar xf -)
rm -rf /home/hnakamur.backup/.ecryptfs
```

ホームディレクトリを暗号化するためのパッケージをアンインストールしました。

```
sudo apt-get remove ecryptfs-utils libecryptfs0
```

上記は手順ミスです。先に別の管理者ユーザを作って元のユーザ `hnakamur` はログアウトし、別の管理ユーザで作業すべきでした。

`df -h` で確認すると `hnakamur` ユーザのホームディレクトリがマウントされたままになっていました。

```
root@express:~# df -h
Filesystem                    Size  Used Avail Use% Mounted on
udev                          7.8G     0  7.8G   0% /dev
tmpfs                         1.6G  8.8M  1.6G   1% /run
/dev/mapper/express--vg-root  131G  2.1G  122G   2% /
tmpfs                         7.8G  4.0K  7.8G   1% /dev/shm
tmpfs                         5.0M     0  5.0M   0% /run/lock
tmpfs                         7.8G     0  7.8G   0% /sys/fs/cgroup
/dev/sdc1                     472M   55M  393M  13% /boot
tmpfs                         100K     0  100K   0% /run/lxcfs/controllers
/home/hnakamur/.Private       131G  2.1G  122G   2% /home/hnakamur
```

この後、別のユーザを作りました。セカンダリグループに `sudo` を指定して `sudo` で `root` になれるようにします。

```
sudo useradd -m -G sudo -s /bin/bash hnakamur2
sudo mkdir -p /etc/hnakamur2/.ssh
sudo chmod -R 700 /etc/hnakamur2
sudo cp /etc/hnakamur/.ssh/authorized_keys /etc/hnakamur2/.ssh/
sudo chown -R hnakamur2: /etc/hnakamur2
```

パスワードが空だとsshログイン出来ないので、パスワードを設定します。

```
root@express:~# passwd hnakamur2
新しい UNIX パスワードを入力してください:
新しい UNIX パスワードを再入力してください:
passwd: パスワードは正しく更新されました
```

これで `hnakamur2` ユーザの作成が終わったので、Macからsshで hnakamur2 ユーザにログインします。

```
ssh hnakamur2@express
```

`root` ユーザになって作業します。

```
sudo -i
umount /home/hnakamur
```

`df -h` を実行してマウントが解除されたことを確認しました。
`/home/hnakamur` の中身を確認すると以下のようになっていました。

```
root@express:~# ll -a /home/hnakamur
合計 8
dr-x------ 2 hnakamur hnakamur 4096  5月  2 01:31 ./
drwxr-xr-x 7 root     root     4096  5月  2 14:42 ../
lrwxrwxrwx 1 hnakamur hnakamur   33  5月  2 01:31 .Private -> /home/.ecryptfs/hnakamur/.Private/
lrwxrwxrwx 1 hnakamur hnakamur   34  5月  2 01:31 .ecryptfs -> /home/.ecryptfs/hnakamur/.ecryptfs/
lrwxrwxrwx 1 hnakamur hnakamur   56  5月  2 01:31 Access-Your-Private-Data.desktop -> /usr/share/ecryptfs-utils/ecryptfs-mount-private.desktop
lrwxrwxrwx 1 hnakamur hnakamur   52  5月  2 01:31 README.txt -> /usr/share/ecryptfs-utils/ecryptfs-mount-private.txt
```

`hnakamur` のホームディレクトリを消して、バックアップした内容に戻します。

```
rm -rf /home/hnakamur
mv /home/hnakamur.backup/ /home/hnakamur
```

戻した中身を確認します。

```
root@express:~# ll -a /home/hnakamur/
合計 56
drwx------ 6 hnakamur hnakamur 4096  5月  2 13:04 ./
drwxr-xr-x 6 root     root     4096  5月  2 14:53 ../
lrwxrwxrwx 1 hnakamur hnakamur   33  5月  2 01:31 .Private -> /home/.ecryptfs/hnakamur/.Private/
-rw------- 1 hnakamur hnakamur 1908  5月  2 12:43 .bash_history
-rw-r--r-- 1 hnakamur hnakamur  220  5月  2 01:31 .bash_logout
-rw-r--r-- 1 hnakamur hnakamur  100  5月  2 08:50 .bash_profile
-rw-r--r-- 1 hnakamur hnakamur 3771  5月  2 01:31 .bashrc
drwx------ 2 hnakamur hnakamur 4096  5月  2 01:36 .cache/
-rw------- 1 hnakamur hnakamur   41  5月  2 09:00 .lesshst
-rw-r--r-- 1 hnakamur hnakamur  675  5月  2 01:31 .profile
drwx------ 2 hnakamur hnakamur 4096  5月  2 01:38 .ssh/
-rw-r--r-- 1 hnakamur hnakamur    0  5月  2 01:38 .sudo_as_admin_successful
-rw------- 1 hnakamur hnakamur 6841  5月  2 12:43 .viminfo
drwxr-xr-x 2 hnakamur hnakamur 4096  5月  2 03:13 docs/
drwxr-xr-x 5 hnakamur hnakamur 4096  5月  2 08:47 gocode/
```

`.Private` も不要なので消します。

```
rm /home/hnakamur/.Private
```

これで Mac から元のユーザ `hnakamur` でsshログイン可能になります。
念のため `hnakamur2` はログインしたままにしておいて、ターミナルの別端末でログインしました。

```
ssh hnakamur@express
```

`/etc/ssh/sshd_config` の `AuthorizedKeysFile` の設定も元に戻すことにします。
`sudo vi /etc/ssh/sshd_config` を実行し以下の行を削除します。

```
AuthorizedKeysFile /etc/%u/.ssh/authorized_keys
```

以下のコマンドで `sshd` を再起動します。

```
sudo systemctl restart sshd
```

`/etc/hnakamur` 以下に置いた `hnakamur` ユーザの鍵もディレクトリごと消します。

```
sudo rm -r /etc/hnakamur
```

Mac のターミナルの別端末から `hnakamur` ユーザでsshログインできることと、sudoでrootになれることを確認しました。

`hnakamur2` ユーザのほうはログアウトして、 `hnakamur` ユーザでログインした端末で `hnakamur2` ユーザを削除します。メールスプールのディレクトリが無いというメッセージが出ますが問題ありません。

```
root@express:~# sudo userdel -r hnakamur2
userdel: hnakamur2 のメールスプール (/var/mail/hnakamur2) がありません
root@express:~# echo $?
0
```

`/etc/hnakamur2` 以下に置いた `hnakamur2` ユーザの鍵もディレクトリごと消します。

```
sudo rm -r /etc/hnakamur2
```

その後

```
sudo shutdown -r now
```

で再起動して、コンソールでLVM暗号化のパスフレーズを入力して起動し、コンソールでログインすることなしに、ssh鍵認証でログインできることを確認しました。

余談ですが、ちょっと不思議なのは、今まで構築したLinux環境ではsshで繋いで `sudo shutdown -h now` や `sudo shutdown -r now` を実行すると接続が切れていたのが、今回の環境ではプロンプトに戻らないまま残ってしまうということです。Ctrl-Cを入力すると `Host is down` と表示されていました。

```
root@express:~# shutdown -r now
packet_write_poll: Connection to 192.168.0.201: Host is down
```

## まとめ
今回のサーバのユーザは自分1人なのでホームディレクトリの暗号化は不要と判断し、解除しました。
