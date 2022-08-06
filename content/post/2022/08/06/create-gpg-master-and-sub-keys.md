---
title: "GPGのプライマリーキーとサブキーを作成"
date: 2022-08-06T19:49:49+09:00
---

## はじめに

以下の記事を参考にGPGのプライマリーキーとサブキーを作成してGitのコミットの署名をやってみたメモです。
脱線多めですが、自分用の記録ということで。

* [GnuPG - ArchWiki](https://wiki.archlinux.jp/index.php/GnuPG)
* [GPGで自分用の秘密鍵を1つに統一する · JoeMPhilips](http://joemphilips.com/post/gpg_memo/)
* [ED25519のGPGキーを生成してコミットに署名する - Weblog by shuuji3](https://weblog.shuuji3.xyz/post/2020-05-05-generate-and-sign-with-ed15519-gpg-key/)
* [GitのコミットにGnuPGで署名する - Qiita](https://qiita.com/usamik26/items/6b816db27b7661611d59)

## LXD でオフラインのコンテナを作成して起動

[How to switch off networking for a container? - LXD - Linux Containers Forum](https://discuss.linuxcontainers.org/t/how-to-switch-off-networking-for-a-container/6174) によると eth0 をコンテナから削除すればオフラインで実行できるとのことなので、これでやってみました。

通常はコンテナの作成と起動は `lxc launch` サブコマンドを使いますが、今回は `lxc init` で停止状態のまま作成して、eth0 を削除してから起動します(`lxc init` はなぜか `lxc help` のサブコマンド一覧には載っていません)。と思ったのですが、試してみたらインスタンスから直接eth0を削除するのはうまく行かなかったので eth0 無しのプロファイルを作成することにしました。

ここでは offline というプロファイル名にします。 default のプロファイルをコピーして作成し、 eth0 を削除して description を Offline LXD profile に変更します。

```bash
lxc profile copy default offline
lxc profile device remove offline eth0 
lxc profile show offline \
  | sed 's/^description:.*/description: Offline LXD profile/' \
  | lxc profile edit offline
```

作成した offline プロファイルの内容を確認します。

```bash
$ lxc profile show offline
config: {}
description: Offline LXD profile
devices:
  root:
    path: /
    pool: default
    type: disk
name: offline
used_by: []
```

上記で作成した offline プロファイルを使用してインスタンスを作成・起動します。プロファイルを使うことにしたので `lxc init` で一旦作成してから `lxc start` で起動する必要はないので、いつもどおり `lxc launch` で作成と起動します。

```bash
lxc launch ubuntu:22.04 my-gpg-master -p offline
```

実行してみると以下のようなメッセージが表示されました。ネットワークが全くアタッチされていないということで、期待通りです。

```bash
$ lxc launch ubuntu:22.04 my-gpg-master -p offline
Creating my-gpg-master

The instance you are starting doesn't have any network attached to it.
  To create a new network, use: lxc network create
  To attach a network to an instance, use: lxc network attach

Starting my-gpg-master
```

`lxc list` でも IP アドレスが付与されていないことを確認します。

```bash
$ lxc list my-gpg-master
+---------------+---------+------+------+-----------+-----------+
|     NAME      |  STATE  | IPV4 | IPV6 |   TYPE    | SNAPSHOTS |
+---------------+---------+------+------+-----------+-----------+
| my-gpg-master | RUNNING |      |      | CONTAINER | 0         |
+---------------+---------+------+------+-----------+-----------+
```

`lxc info` でも eth0 が無いことを確認します。

```bash
$ lxc info my-gpg-master
Name: my-gpg-master
Status: RUNNING
Type: container
Architecture: x86_64
PID: 4011455
Created: 2022/08/06 20:17 JST
Last Used: 2022/08/06 20:17 JST

Resources:
  Processes: 57
  Disk usage:
    root: 24.02MiB
  CPU usage:
    CPU usage (in seconds): 14
  Memory usage:
    Memory (current): 210.56MiB
  Network usage:
    lo:
      Type: loopback
      State: UP
      MTU: 65536
      Bytes received: 12.00kB
      Bytes sent: 12.00kB
      Packets received: 164
      Packets sent: 164
      IP addresses:
        inet:  127.0.0.1/8 (local)
        inet6: ::1/128 (local)
```

## コンテナの中に入って GPG のプライマリーキーを作成

```bash
lxc exec my-gpg-master bash
```

gpg のバージョンを確認します。

```bash
# gpg --version
gpg (GnuPG) 2.2.27
libgcrypt 1.9.4
Copyright (C) 2021 Free Software Foundation, Inc.
License GNU GPL-3.0-or-later <https://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Home: /root/.gnupg
Supported algorithms:
Pubkey: RSA, ELG, DSA, ECDH, ECDSA, EDDSA
Cipher: IDEA, 3DES, CAST5, BLOWFISH, AES, AES192, AES256, TWOFISH,
        CAMELLIA128, CAMELLIA192, CAMELLIA256
Hash: SHA1, RIPEMD160, SHA256, SHA384, SHA512, SHA224
Compression: Uncompressed, ZIP, ZLIB, BZIP2
```

Ubuntu 22.04 の LXD コンテナでは初期状態で gpg の他に gpg-agent や gpgsm もインストールされていました。

```bash
# dpkg -l | grep gpg
ii  gpg                             2.2.27-3ubuntu2.1                       amd64        GNU Privacy Guard -- minimalist public key operations
ii  gpg-agent                       2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - cryptographic agent
ii  gpg-wks-client                  2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - Web Key Service client
ii  gpg-wks-server                  2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - Web Key Service server
ii  gpgconf                         2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - core configuration utilities
ii  gpgsm                           2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - S/MIME version
ii  gpgv                            2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - signature verification tool
ii  libgpg-error0:amd64             1.43-3                                  amd64        GnuPG development runtime library
ii  libgpgme11:amd64                1.16.0-1.2ubuntu4                       amd64        GPGME - GnuPG Made Easy (library)
```

まず、とりあえず特に指定せずにデフォルトでプライマリーキーを作成してみました。

```bash
gpg --gen-key
```

私の場合の実行例。

```bash
# gpg --gen-key
gpg (GnuPG) 2.2.27; Copyright (C) 2021 Free Software Foundation, Inc.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

gpg: directory '/root/.gnupg' created
gpg: keybox '/root/.gnupg/pubring.kbx' created
Note: Use "gpg --full-generate-key" for a full featured key generation dialog.

GnuPG needs to construct a user ID to identify your key.

Real name: Hiroaki Nakamura
Email address: hnakamur@gmail.com
You selected this USER-ID:
    "Hiroaki Nakamura <hnakamur@gmail.com>"

Change (N)ame, (E)mail, or (O)kay/(Q)uit? O
```

すると以下のように表示されるので、適当にキーボードをタイプします。

```
We need to generate a lot of random bytes. It is a good idea to perform
some other action (type on the keyboard, move the mouse, utilize the
disks) during the prime generation; this gives the random number
generator a better chance to gain enough entropy.
```

すると以下のメッセージが表示されてプライマリーキーが作成されました (key の後の XXXX は念の為伏せてます)。
使用されたアルゴリズムは RSA 3072 bit でした。

```
asdlfkgpg: /root/.gnupg/trustdb.gpg: trustdb created
gpg: key XXXXXXXXXXXXXXXX marked as ultimately trusted
gpg: directory '/root/.gnupg/openpgp-revocs.d' created
jasdfgpg: revocation certificate stored as '/root/.gnupg/openpgp-revocs.d/6BACB1D1D76C87D24BAEAB9DB89D3B8FDEF900B9.rev'
public and secret key created and signed.

pub   rsa3072 2022-08-06 [SC] [expires: 2024-08-05]
      6BACB1D1D76C87D24BAEAB9DB89D3B8FDEF900B9
uid                      Hiroaki Nakamura <hnakamur@gmail.com>
sub   rsa3072 2022-08-06 [E] [expires: 2024-08-05]
```

その後以下のページを見て ed25519 を使ってプライマリーキーを作成し直すことにしました。

* [Comparison of the SSH Key Algorithms | by Nicolas Béguier | Medium](https://nbeguier.medium.com/a-real-world-comparison-of-the-ssh-key-algorithms-b26b0b31bfd9)
* [An abridged guide to using ed25519 PGP keys with GnuPG and SSH | MuSigma](https://musigma.blog/2021/05/09/gpg-ssh-ed25519.html)

`~/.gpg` を削除します。

```bash
rm -rf ~/.gpg
```

ed25519 でプライマリーキーを作成します。

```bash
gpg --quick-generate-key \
    'Your Name <your.email@example.com> (optional comment)' \
    ed25519 cert never
```

私の場合は以下のようにしました。

```bash
gpg --quick-generate-key 'Hiroaki Nakamura <hnakamur@gmail.com>' ed25519 cert never
```

実行してみると以下のメッセージが出ました。単に `~/.gnupg` を消すだけではだめなようです。

```
gpg: A key for "Hiroaki Nakamura <hnakamur@gmail.com>" already exists
```

ということで exit でコンテナを抜けて、コンテナを作り直して再度試しました。

```
exit
lxc delete -f my-gpg-master
lxc launch ubuntu:22.04 my-gpg-master -p offline
lxc exec my-gpg-master bash
```

```bash
gpg --quick-generate-key 'Hiroaki Nakamura <hnakamur@gmail.com>' ed25519 cert never
```

作成するキー用のパスフレーズの入力を求められますので、パスワードマネージャでランダム文字列を生成して入力しました。

以下のようなメッセージが表示されました (key の後の XXXX は念の為伏せてます)。

```
gpg: directory '/root/.gnupg' created
gpg: keybox '/root/.gnupg/pubring.kbx' created
We need to generate a lot of random bytes. It is a good idea to perform
some other action (type on the keyboard, move the mouse, utilize the
disks) during the prime generation; this gives the random number
generator a better chance to gain enough entropy.
gpg: /root/.gnupg/trustdb.gpg: trustdb created
gpg: key XXXXXXXXXXXXXXXX marked as ultimately trusted
gpg: directory '/root/.gnupg/openpgp-revocs.d' created
gpg: revocation certificate stored as '/root/.gnupg/openpgp-revocs.d/0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C.rev'
public and secret key created and signed.

pub   ed25519 2022-08-06 [C]
      0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C
uid                      Hiroaki Nakamura <hnakamur@gmail.com>
```

[An abridged guide to using ed25519 PGP keys with GnuPG and SSH | MuSigma](https://musigma.blog/2021/05/09/gpg-ssh-ed25519.html) を再度見てみると

> Note that certification and authentication keys use signature algorithms internally, thus for our key, we’ll use `ed25519` for all but our encryption subkey which will instead use `cv25519`

と書いてありました。 `ed25519` とは別に `cv25519` というのもあるんですね。暗号化には `cv25519`、署名には `ed25519` を使うそうです。

[elliptic curves - Why is Curve25519 in the GPG “expert” options? - Cryptography Stack Exchange](https://crypto.stackexchange.com/questions/52859/why-is-curve25519-in-the-gpg-expert-options) にも

> Support for what GnuPG calls cv25519 public-key encryption keys, and for ed25519 public-key signature keys, is neither standardized nor widespread, so you're likely to hit compatibility issues with anyone else using OpenPGP.

というコメントがありました。

* [gnupg - RSA 4096 vs. ECC Curve 25519 - Information Security Stack Exchange](https://security.stackexchange.com/questions/205600/rsa-4096-vs-ecc-curve-25519)
* [public key - How do I get the equivalent strength of an ECC key? - Cryptography Stack Exchange](https://crypto.stackexchange.com/questions/31439/how-do-i-get-the-equivalent-strength-of-an-ecc-key)

も見てみて、今回は ed25519 / cv25519 で行くことにしました。今回はといってもプライマリーキーは何年も使う想定なので、将来 ed25519 / cv25519 では不十分となったら、作り直す必要が出てくるかもしれません。

* [Can GPG key Curve 25519 be stored on Yubikey? : yubikey](https://www.reddit.com/r/yubikey/comments/gjwkpd/can_gpg_key_curve_25519_be_stored_on_yubikey/)
* [YubiKey 5.2 Enhancements to OpenPGP 3.4 Support – Yubico](https://support.yubico.com/hc/en-us/articles/360016649139-YubiKey-5-2-3-Enhancements-to-OpenPGP-3-4-Support)

によると YubiKey 5.2 以上のファームウェアでは Elliptic Curve Cryptographic Algorithms をサポートしているとのこと。

私が持っているのは

* YubiKey 5 NFC
* YubiKey 5C
* YubiKey Bio - FIDO Edition
* YubiKey C Bio - FIDO Edition

ということでたぶん大丈夫。

[An abridged guide to using ed25519 PGP keys with GnuPG and SSH | MuSigma](https://musigma.blog/2021/05/09/gpg-ssh-ed25519.html) の続きを進めます。

プライマリーキーを作成したときに表示された pub の後のフィンガープリントをこの後実行するコマンド用に KEYFP 環境変数に設定しておきます。
今回の例だと以下のようにします。

```bash
export KEYFP=0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C
```

署名、暗号化、認証用のサブキーを作成します。各コマンドでパスフレーズを聞かれるので、上記で設定したパスフレーズを入力します。


```bash
gpg --quick-add-key $KEYFP ed25519 sign 1y
gpg --quick-add-key $KEYFP cv25519 encr 1y
gpg --quick-add-key $KEYFP ed25519 auth 1y
```

`gpg --list-secret-keys` で秘密鍵の一覧を表示します。

```bash
root@my-gpg-master:~# gpg --list-secret-keys
/root/.gnupg/pubring.kbx
------------------------
sec   ed25519 2022-08-06 [C]
      0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C
uid           [ultimate] Hiroaki Nakamura <hnakamur@gmail.com>
ssb   ed25519 2022-08-06 [S] [expires: 2023-08-06]
ssb   cv25519 2022-08-06 [E] [expires: 2023-08-06]
ssb   ed25519 2022-08-06 [A] [expires: 2023-08-06]
```

## 顔写真の登録

以下は [GPGで自分用の秘密鍵を1つに統一する · JoeMPhilips](http://joemphilips.com/post/gpg_memo/) を参考に進めます。この記事で `MASTERID` と書いているところは `$KEYFP` と読み替えて実行します。

[Creating a small JPEG photo for your OpenPGP key – Simon Josefsson's blog](https://blog.josefsson.org/2014/06/19/creating-a-small-jpeg-photo-for-your-openpgp-key/) によると GnuPG では 240x288 の解像度が良いらしいです。
リンク先の [git.gnupg.org Git - gnupg.git/blob - g10/photoid.c](http://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob;f=g10/photoid.c;h=517fa21d7808596e2b0a96d3500e849c494a3ec6;hb=6209c6d9ad00a17bef4780ff22f0e9f588343c00#l83) を GitHub で 2022-08-06 現在の最新コミット [gnupg/photoid.c at master · gpg/gnupg](https://github.com/gpg/gnupg/blob/25ae80b8eb6e9011049d76440ad7d250c1d02f7c/g10/photoid.c#L84) で確認するとお勧めは変わらず 240x288 でした。

が、私の twitter アイコンの画像は 100x100 なので気にせずそれを使うことにしました。
ホストマシンから自分の顔写真の画像を作業用コンテナにコピー。

```bash
lxc file push ~/Pictures/my_icon_100x100.jpg my-gpg-master/root/
```

[bash - gpg2 --edit-key addphoto / keytocard without password prompt - Super User](https://superuser.com/questions/1191963/gpg2-edit-key-addphoto-keytocard-without-password-prompt) を参考に以下のコマンドで設定してみました。

プライマリーキーのIDは `gpg --list-secret-keys --keyid-format short` で確認して `keyid` 変数に設定します。

```bash
keyid=プライマリーキーのID
var_photo_path=my_icon_100x100.jpg
cmd="addphoto\n$var_photo_path\ny\nパスフレーズ\nquit\ny\n" 
echo -e "$cmd" | gpg --command-fd 0 --pinentry-mode=loopback --status-fd 2 --edit-key "$keyid"
```

試してみたのですがエラーメッセージが出てうまく行きませんでした。期待する入力順序とあってなさそうな感じのメッセージになってました。

ということでおとなしくインタラクティブに画像ファイルを登録することにしました。

```
gpg --edit-key $keyid
```

```
gpg> addphoto

Pick an image to use for your photo ID.  The image must be a JPEG file.
Remember that the image is stored within your public key.  If you use a
very large picture, your key will become very large as well!
Keeping the image close to 240x288 is a good size to use.

Enter JPEG filename for photo ID: my_icon_100x100.jpg
Is this photo correct (y/N/q)? y

gpg> quit
Save changes? (y/N) y
```

## プライマリーキーの執行証明書を作成

`gpg --output $KEYFP.gpg-revocation-certificate --gen-revoke $KEYFP` を実行すると以下のように理由が聞かれました。一旦 Q を入力してキャンセルして抜けました。

```
root@my-gpg-master:~# gpg --output $KEYFP.gpg-revocation-certificate --gen-revoke $KEYFP

sec  ed25519/0629F2A2680DEB3C 2022-08-06 Hiroaki Nakamura <hnakamur@gmail.com>

Create a revocation certificate for this key? (y/N) y
Please select the reason for the revocation:
  0 = No reason specified
  1 = Key has been compromised
  2 = Key is superseded
  3 = Key is no longer used
  Q = Cancel
(Probably you want to select 1 here)
Your decision? Q
```

1, 2, 3 のどれも将来使う可能性がありそうなので、ファイル名を変えて3通り作っておくことにしました。

```
root@my-gpg-master:~# gpg --output $KEYFP.gpg-revocation-certificate-compromised --gen-revoke $KEYFP

sec  ed25519/0629F2A2680DEB3C 2022-08-06 Hiroaki Nakamura <hnakamur@gmail.com>

Create a revocation certificate for this key? (y/N) y
Please select the reason for the revocation:
  0 = No reason specified
  1 = Key has been compromised
  2 = Key is superseded
  3 = Key is no longer used
  Q = Cancel
(Probably you want to select 1 here)
Your decision? 1
Enter an optional description; end it with an empty line:
>
Reason for revocation: Key has been compromised
(No description given)
Is this okay? (y/N) y
ASCII armored output forced.
Revocation certificate created.

Please move it to a medium which you can hide away; if Mallory gets
access to this certificate he can use it to make your key unusable.
It is smart to print this certificate and store it away, just in case
your media become unreadable.  But have some caution:  The print system of
your machine might store the data and make it available to others!
```

```
# gpg --output $KEYFP.gpg-revocation-certificate-superseded --gen-revoke $KEYFP

sec  ed25519/0629F2A2680DEB3C 2022-08-06 Hiroaki Nakamura <hnakamur@gmail.com>

Create a revocation certificate for this key? (y/N) y
Please select the reason for the revocation:
  0 = No reason specified
  1 = Key has been compromised
  2 = Key is superseded
  3 = Key is no longer used
  Q = Cancel
(Probably you want to select 1 here)
Your decision? 2
Enter an optional description; end it with an empty line:
>
Reason for revocation: Key is superseded
(No description given)
Is this okay? (y/N) y
ASCII armored output forced.
Revocation certificate created.

Please move it to a medium which you can hide away; if Mallory gets
access to this certificate he can use it to make your key unusable.
It is smart to print this certificate and store it away, just in case
your media become unreadable.  But have some caution:  The print system of
your machine might store the data and make it available to others!
```

```
# gpg --output $KEYFP.gpg-revocation-certificate-no-longer-used --gen-revoke $KEYFP

sec  ed25519/0629F2A2680DEB3C 2022-08-06 Hiroaki Nakamura <hnakamur@gmail.com>

Create a revocation certificate for this key? (y/N) y
Please select the reason for the revocation:
  0 = No reason specified
  1 = Key has been compromised
  2 = Key is superseded
  3 = Key is no longer used
  Q = Cancel
(Probably you want to select 1 here)
Your decision? 3
Enter an optional description; end it with an empty line:
>
Reason for revocation: Key is no longer used
(No description given)
Is this okay? (y/N) y
ASCII armored output forced.
Revocation certificate created.

Please move it to a medium which you can hide away; if Mallory gets
access to this certificate he can use it to make your key unusable.
It is smart to print this certificate and store it away, just in case
your media become unreadable.  But have some caution:  The print system of
your machine might store the data and make it available to others!
```

## ホストマシンに Paperkey をインストール

[GPGで自分用の秘密鍵を1つに統一する · JoeMPhilips](http://joemphilips.com/post/gpg_memo/) の optar でリンクされていた [Paperkey - an OpenPGP key archiver](http://www.jabberwocky.com/software/paperkey/) を使ってみます。

Ubuntu 22.04 LTS には paperkey のパッケージがありました。 Homepage の URL も上のリンク先と一致しています。

```
$ apt show paperkey
Package: paperkey
Version: 1.6-1
Priority: optional
Section: universe/utils
Origin: Ubuntu
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Peter Palfrader <weasel@debian.org>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Installed-Size: 56.3 kB
Depends: libc6 (>= 2.14)
Recommends: gnupg
Enhances: gnupg
Homepage: http://www.jabberwocky.com/software/paperkey/
Download-Size: 26.7 kB
APT-Sources: http://jp.archive.ubuntu.com/ubuntu jammy/universe amd64 Packages
…(略)…
```

## 失効証明書を印刷

ここでホストマシンの LAN ケーブルを抜いて WiFi もオフにしてオフラインにしました。

`lxc file pull` コマンドを使って上記で作成した失効証明書をホストマシンにコピーして Text Editor で開いて印刷しました。 ゼロとオーなどが区別が付きやすいようにフォントは Cica フォントを使いました。

## 秘密鍵を印刷

コンテナで以下のコマンドを実行して秘密鍵をエクスポートします (パスフレーズを聞かれるので入力します)。

```
gpg --export-secret-keys > my-gpg-master-key-for-github.gpg
```

その後 `lxc file pull` コマンドを使ってホストマシンにコピーし、 paperkey コマンドでテキストに変換します。このときパスフレーズは聞かれなかったのでパスフレーズで守られた状態のプライマリーキーをテキスト化しているようです。 `man paperkey` にも書いてありました。パスフレーズがついている、ついていないに応じてそのままの状態でテキスト化しているとのことです。

(確認のため試しに別のオフラインのコンテナを作って my-gpg-master-key-for-github.gpg をコピーして `gpg --import my-gpg-master-key-for-github.gpg` を実行するとパスフレーズを聞かれました。と、パスフレーズ入力ダイアログを表示したままこの文章を書いていたらタイムアウトになったのかダイアログが閉じて public key ... imported という表示が出ました。 `gpg --list-keys` では鍵が表示されていましたが `gpg --list-secret-keys` では何も表示されませんでした。公開鍵の方だけインポートされたようです)。

```
paperkey --secret-key my-gpg-master-key-for-github.gpg --output my-gpg-master-key-for-github.gpg.txt
```



出力されたテキストファイルは以下のような内容になっていました。もちろんキーの内容は伏せています。

```
# Secret portions of key 0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C
# Base16 data extracted Sat Aug  6 23:14:29 2022
# Created with paperkey 1.6 by David Shaw
#
# File format:
# a) 1 octet:  Version of the paperkey format (currently 0).
# b) 1 octet:  OpenPGP key or subkey version (currently 4)
# c) n octets: Key fingerprint (20 octets for a version 4 key or subkey)
# d) 2 octets: 16-bit big endian length of the following secret data
# e) n octets: Secret data: a partial OpenPGP secret key or subkey packet as
#              specified in RFC 4880, starting with the string-to-key usage
#              octet and continuing until the end of the packet.
# Repeat fields b through e as needed to cover all subkeys.
#
# To recover a secret key without using the paperkey program, use the
# key fingerprint to match an existing public key packet with the
# corresponding secret data from the paper key.  Next, append this secret
# data to the public key packet.  Finally, switch the public key packet tag
# from 6 to 5 (14 to 7 for subkeys).  This will recreate the original secret
# key or secret subkey packet.  Repeat as needed for all public key or subkey
# packets in the public key.  All other packets (user IDs, signatures, etc.)
# may simply be copied from the public key.
#
# Each base16 line ends with a CRC-24 of that line.
# The entire block of data ends with a CRC-24 of the entire block of data.

  1: XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XX XXXXXX
…(略)…
```

## USB メモリにバックアップ

上記で作成したファイル一式と [GPGで自分用の秘密鍵を1つに統一する · JoeMPhilips](http://joemphilips.com/post/gpg_memo/) をテキストファイルに保存して、普段使用しない USB メモリにバックアップしました。将来故障して読めなくなるリスクを考えて 2 つの USB メモリにコピーしました。


USB メモリは念の為 LUKS で暗号化しておきました。


## 作業用コンテナ内からサブキーをエクスポートしてホストマシンにインポート

作業用コンテナで以下のコマンドを実行してサブキーをエクスポート (パスフレーズを聞かれるので入力)。

```
gpg --output hnakamur-gpg-subkeys.gpg --export-secret-subkeys $KEYFP
```

その後 `lxc file pull` コマンドを使ってホストマシンにコピー。

ホストマシンで以下のコマンドを実行してサブキーをインポート (パスフレーズをモーダルダイアログで聞かれるので事前にパスワードマネージャでコピーしておいて入力)。

```
gpg --import hnakamur-gpg-subkeys.gpg
```

インポートした結果を確認すると sec の後に # がついています。

```
$ gpg --list-secret-keys 0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C
sec#  ed25519 2022-08-06 [C]
      0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C
uid           [ unknown] Hiroaki Nakamura <hnakamur@gmail.com>
uid           [ unknown] [jpeg image of size 2607]
ssb   ed25519 2022-08-06 [S] [expires: 2023-08-06]
ssb   cv25519 2022-08-06 [E] [expires: 2023-08-06]
ssb   ed25519 2022-08-06 [A] [expires: 2023-08-06]
```

`man gpg` の `--list-secret-keys` には以下のように書かれていました。

> A # after the initial tags sec or ssb means that the secret key
> or subkey is currently not usable. 


## サブキーのフィンガープリントの確認方法

[How can I get a subkey's fingerprint?](https://lists.gnupg.org/pipermail/gnupg-users/2005-March/025169.html) で知りました。 `man gpg` の `--fingerprint` の説明にも2回指定するとサブキーのフィンガープリントも出力されると書かれていました。

```
$ gpg --fingerprint --fingerprint 0629F2A2680DEB3C
pub   ed25519 2022-08-06 [C]
      0A9E CAD8 01E0 EBFC F7B7  7F69 0629 F2A2 680D EB3C
uid           [ unknown] Hiroaki Nakamura <hnakamur@gmail.com>
uid           [ unknown] [jpeg image of size 2607]
sub   ed25519 2022-08-06 [S] [expires: 2023-08-06]
      13F0 F726 6E46 D846 A741  FF4B F7AD BE58 173B 8F2E
sub   cv25519 2022-08-06 [E] [expires: 2023-08-06]
      6867 353C 336F 958F 4E6E  02DB 0DDE 7B81 65A0 4D70
sub   ed25519 2022-08-06 [A] [expires: 2023-08-06]
      453B 5C4D DE2A 8CDA 2038  FF2D 4428 346A 4DA6 7825
```

## 作業用のコンテナを削除

ホストマシンで以下のコマンドを実行し作業用のコンテナを削除します。

```
lxc delete -f my-gpg-master
```

そしてホストマシンの LAN ケーブルをつないでオンラインに戻しました。

## パスワード入力のモーダルダイアログを GUI から TUI に変更

GUI のモーダルダイアログだとパスワードマネージャに切り替えてコピペできないので TUI に変更します。
現状を確認すると以下のようになっていました。

```
$ ls -l /usr/bin/pinentry*
lrwxrwxrwx 1 root root    26  5月  7 18:14 /usr/bin/pinentry -> /etc/alternatives/pinentry
-rwxr-xr-x 1 root root 60056  3月 25 01:31 /usr/bin/pinentry-curses
-rwxr-xr-x 1 root root 76448  3月 25 01:31 /usr/bin/pinentry-gnome3
lrwxrwxrwx 1 root root    30  5月  7 18:14 /usr/bin/pinentry-x11 -> /etc/alternatives/pinentry-x11
```

```
$ ls -l /etc/alternatives/pinentry
lrwxrwxrwx 1 root root 24  5月  7 18:14 /etc/alternatives/pinentry -> /usr/bin/pinentry-gnome3
```

update-alternatives での変更前に選択肢を表示。

```
$ sudo update-alternatives --list pinentry
/usr/bin/pinentry-curses
/usr/bin/pinentry-gnome3
```

変更と確認。

```
$ sudo update-alternatives --set pinentry /usr/bin/pinentry-curses
update-alternatives: using /usr/bin/pinentry-curses to provide /usr/bin/pinentry (pinentry) in manual mode
$ ls -l /etc/alternatives/pinentry
lrwxrwxrwx 1 root root 24  8月  7 00:51 /etc/alternatives/pinentry -> /usr/bin/pinentry-curses
``` 

## サブキーのパスワード変更

`gpg --keyid-format short --list-keys` で一覧を表示して、変更したいサブキーの ID (ed25519/ や cv25519/ の後ろ) を指定して、以下のコマンドで変更します。

```
gpg --edit-key 鍵のID passwd
```

変更後 `gpg> ` のプロンプトになるので `quit` で抜けます。

変更後の鍵一覧の表示での鍵ID は long 形式で出力されていました。ということで鍵一覧を表示するときは `gpg --keyid-format long --list-keys` のように long 形式で出力しておくのが良さそうです。

試してみたところ `gpg --edit-key 鍵のID passwd` で鍵のIDにプライマリーキーのIDを指定してもサブキーのIDを指定しても元のパスフレーズを1回聞かれた後、新しいパスワードは3つのサブキーのパスフレーズに対して順に聞かれます。自信が無いのですが、3つのサブキーのパスフレーズが共通になっている気がします。

## GitHub に署名用の副鍵を登録

[Generating a new GPG key - GitHub Docs](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key) と [githubで使うGPG鍵の作成 - Qiita](https://qiita.com/kanatatsu64/items/85104644d1599c244f35) を参考に登録します。

```
gpg --export --armor プライマリーキーID
```

以下のように公開鍵が出力されました。

```
-----BEGIN PGP PUBLIC KEY BLOCK-----

mDMEYu5UmRYJKwYBBAHaRw8BAQdAomlYh4adsDQ/KJwfIU/Y88prO/fpa24/8RmR
…(略)…
iSJrhHPvY443N2s3EzxituVIq91htDlrjmdDiHUHHQk=
=5vbz
-----END PGP PUBLIC KEY BLOCK-----
```

ブラウザで https://github.com/settings/keys を開いて [New GPG key] ボタンを押し、上記のコマンドで出力された鍵の内容を Key のテキストエリアにコピーペーストします。
Title のテキストフィールドは Hiroaki Nakamura と入力しました。

[GitHub に登録した OpenPGP 公開鍵を取り出す](https://zenn.dev/spiegel/articles/20201014-openpgp-pubkey-in-github) を参考に登録した GPG 鍵を確認してみた。
レスポンスを見ると、プライマリーキーと3つのサブキーのIDも含まれているのでこれらは公開情報ということがわかりました。上記で伏せる必要はなかったのでした。

```
$ curl -s https://api.github.com/users/hnakamur/gpg_keys
[
  {
    "id": 2049443,
    "primary_key_id": null,
    "key_id": "0629F2A2680DEB3C",
    "raw_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\r\n\r\nmDMEYu5UmRYJKwYBBAHaRw8BAQdAomlYh4adsDQ/KJwfIU/Y88prO/fpa24/8RmR\r\nXiRa/bm0JUhpcm9ha2kgTmFrYW11cmEgPGhuYWthbXVyQGdtYWlsLmNvbT6IkAQT\r\nFggAOBYhBAqeytgB4Ov897d/aQYp8qJoDes8BQJi7lSZAhsBBQsJCAcCBhUKCQgL\r\nAgQWAgMBAh4BAheAAAoJEAYp8qJoDes8rIsBAKL/np9gMjcE7QQLNGCKQnEVduRL\r\nhgPCFzd4W/fyQ6SuAP4tEY3HkartZW28mzTE3do15ZeW35bw/8ZTeuH+kNpyAtHJ\r\ngsmAARAAAQEAAAAAAAAAAAAAAAD/2P/gABBKRklGAAEBAQBIAEgAAP/+AE9WZW5k\r\nZXI6U0hBUlAKTW9kZWw6ODEyU0gKU29mdHdhcmUgVmVyc2lvbjoxLjEzUiAgIApE\r\nYXRldGltZToyMDA4MDcyMiAwMToyNTowMP/bAEMABwUFBgUEBwYFBggHBwgKEQsK\r\nCQkKFQ8QDBEYFRoZGBUYFxseJyEbHSUdFxgiLiIlKCkrLCsaIC8zLyoyJyorKv/b\r\nAEMBBwgICgkKFAsLFCocGBwqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioq\r\nKioqKioqKioqKioqKioqKioqKv/AABEIAGQAZAMBIQACEQEDEQH/xAAcAAABBAMB\r\nAAAAAAAAAAAAAAAFAAIEBgEDBwj/xAAyEAABAwQBAgUDAgUFAAAAAAABAAIDBAUR\r\nIRIGMRMiQVFxBxRhMpEVQmKBwSMzUqLh/8QAGgEAAgMBAQAAAAAAAAAAAAAAAwQB\r\nAgUABv/EACYRAAICAgICAgICAwAAAAAAAAABAhEDIRIxBEEiURNhBXEjMoH/2gAM\r\nAwEAAhEDEQA/AKi2LWTpbGxYzja7rQBsf4e8HCf4WDkhVkq6IqkYeY4z53gfJSY+\r\nJ36Xg/BVK0ds2tiDjkb+FkQb7bVSRxiOAcJNi/CjjrRS6VGfC0NYCz4fl2okumRa\r\nGmMjskpV0TS+jSyMEb2tjYfLk6TLsh9kauuVHb2cqh45Y00bJ/shjLpNcARGPCjz\r\nofzfuqSqMbYbHDm7LLYunmVh5vjDj/ydtW2n6LaRkxsPwkXl32aX4daJEnQkEhHE\r\n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\r\n=5vbz\r\n-----END PGP PUBLIC KEY BLOCK-----",
    "public_key": "xjMEYu5UmRYJKwYBBAHaRw8BAQdAomlYh4adsDQ/KJwfIU/Y88prO/fpa24/8RmRXiRa/bk=",
    "emails": [
      {
        "email": "hnakamur@gmail.com",
        "verified": true
      }
    ],
    "subkeys": [
      {
        "id": 2049444,
        "primary_key_id": 2049443,
        "key_id": "F7ADBE58173B8F2E",
        "raw_key": null,
        "public_key": "zjMEYu5i5RYJKwYBBAHaRw8BAQdAu/KOfEhOX5ka/VF/sGWS8xnn4zMEF0EWyn3MCW+HJTI=",
        "emails": [

        ],
        "subkeys": [

        ],
        "can_sign": true,
        "can_encrypt_comms": false,
        "can_encrypt_storage": false,
        "can_certify": false,
        "created_at": "2022-08-06T16:49:56.000Z",
        "expires_at": "2023-08-06T12:47:33.000Z",
        "revoked": false
      },
      {
        "id": 2049445,
        "primary_key_id": 2049443,
        "key_id": "0DDE7B8165A04D70",
        "raw_key": null,
        "public_key": "zjgEYu5i/RIKKwYBBAGXVQEFAQEHQBQbzskGmbcuwDQcRVRZFKD8RkB7gddPHYbMDc+VAxcYAwEIBw==",
        "emails": [

        ],
        "subkeys": [

        ],
        "can_sign": false,
        "can_encrypt_comms": true,
        "can_encrypt_storage": true,
        "can_certify": false,
        "created_at": "2022-08-06T16:49:56.000Z",
        "expires_at": "2023-08-06T12:47:57.000Z",
        "revoked": false
      },
      {
        "id": 2049446,
        "primary_key_id": 2049443,
        "key_id": "4428346A4DA67825",
        "raw_key": null,
        "public_key": "zjMEYu5jBxYJKwYBBAHaRw8BAQdAGjhfLpYnwwP3D2Pxun9IFAL4BCRGpG65ogtbZQ6QZGY=",
        "emails": [

        ],
        "subkeys": [

        ],
        "can_sign": false,
        "can_encrypt_comms": false,
        "can_encrypt_storage": false,
        "can_certify": false,
        "created_at": "2022-08-06T16:49:56.000Z",
        "expires_at": "2023-08-06T12:48:07.000Z",
        "revoked": false
      }
    ],
    "can_sign": false,
    "can_encrypt_comms": false,
    "can_encrypt_storage": false,
    "can_certify": true,
    "created_at": "2022-08-06T16:49:56.000Z",
    "expires_at": null,
    "revoked": false,
    "name": "Hiroaki Nakamura"
  }
]
```

## git でコミットに署名する設定

常にコミットに署名する設定をします。
[Jente Hidskes' website - PSA: want to use a new subkey to sign your commits?](https://www.hjdskes.nl/blog/psa-github-gpg/) を見るとサブキーを使う場合は git の `user.signingkey` 設定の鍵IDの最後に `!` を追加する必要があり、[Git - Signing Your Work](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work) を見ると鍵IDはサブキーではなくプライマリーキーのほうを指定する必要があるようです。と思ったのですがサブキーを `!` 無しで指定するのが正解でした（下記参照）。

```
git config --global user.signingkey 0629F2A2680DEB3C\! # プライマリーキーIDの後に感嘆符 (バックスラッシュは zsh の場合のエスケープ)
git config --global commit.gpgsign true
```

`man git-config` で `gpg.program` の説明を見るとデフォルト値は gpg なので、 `gpg.program` は未設定としておきます。

これでこのブログ記事をコミットしてどうなるか試してみたところ以下のエラーになりました。

```
error: gpg failed to sign the data
fatal: failed to write commit object
```

[How to understand the `gpg failed to sign the data` problem in git](https://gist.github.com/paolocarrasco/18ca8fe6e63490ae1be23e84a7039374) で `git commit` 実行時に `GIT_TRACE=1 git commit` のように `GIT_TRACE=1` をつけるとトレースメッセージが出力されることを知りました。

その一部で以下のように git から呼んでいる gpg のコマンドが出力されます。

```
trace: run_command: gpg --status-fd=2 -bsau '0629F2A2680DEB3C'\!''
```

これをコピペして実行してみると `Unusable secret key` と表示されました。

```
$ gpg --status-fd=2 -bsau '0629F2A2680DEB3C'\!''
[GNUPG:] KEY_CONSIDERED 0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C 1
gpg: skipped "0629F2A2680DEB3C!": Unusable secret key
[GNUPG:] INV_SGNR 9 0629F2A2680DEB3C!
[GNUPG:] FAILURE sign 54
gpg: signing failed: Unusable secret key
```

署名用のサブキー (鍵一覧の表示で `[S]` がついている鍵) のIDで試すと上のエラーは出ずに待ち状態になったので Ctrl-C で止めました。

```
$ gpg --status-fd=2 -bsau F7ADBE58173B8F2E
[GNUPG:] KEY_CONSIDERED 0A9ECAD801E0EBFCF7B77F690629F2A2680DEB3C 0
[GNUPG:] BEGIN_SIGNING H8
^C
gpg: signal 2 caught ... exiting
```

というわけで以下のように設定を変更しました。

```
git config --global user.signingkey F7ADBE58173B8F2E # 署名用サブキーID
```

しかし、 `git commit` では相変わらず同じエラーが出ました。

[Telling Git about your signing key - GitHub Docs](https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key)
の 5 の手順を忘れていたのが原因でした。以下のコマンドを実行して `GPG_TTY` 環境変数を設定しておく必要がありました。

```
[ -f ~/.bashrc ] && echo 'export GPG_TTY=$(tty)' >> ~/.bashrc
```

その場で反映するため、ログインシェルを再起動します。

```
exec $SHELL -l
```

`GPG_TTY` 環境変数が設定されたことを確認します。

```
$ echo $GPG_TTY
/dev/pts/2
```

これで `git commit` が成功しました。

## コミットまたはタグがどの鍵で署名されているかを確認

[gnupg - How do I know which subkey GitHub is using for signing? - Information Security Stack Exchange](https://security.stackexchange.com/questions/128437/how-do-i-know-which-subkey-github-is-using-for-signing) で知りました。 `git verify-commit コミット` や `git verify-tag タグ名` で確認できます。

```
$ git verify-commit HEAD
gpg: Signature made 2022年08月07日 03時07分49秒 JST
gpg:                using EDDSA key 13F0F7266E46D846A741FF4BF7ADBE58173B8F2E
gpg: Good signature from "Hiroaki Nakamura <hnakamur@gmail.com>" [unknown]
gpg:                 aka "[jpeg image of size 2607]" [unknown]
gpg: WARNING: This key is not certified with a trusted signature!
gpg:          There is no indication that the signature belongs to the owner.
Primary key fingerprint: 0A9E CAD8 01E0 EBFC F7B7  7F69 0629 F2A2 680D EB3C
     Subkey fingerprint: 13F0 F726 6E46 D846 A741  FF4B F7AD BE58 173B 8F2E
```

## 公開鍵をキーサーバにアップロード

上記でメールアドレスの後が `[unknown]` になっているのを見て [GPGで自分用の秘密鍵を1つに統一する · JoeMPhilips](http://joemphilips.com/post/gpg_memo/) の公開鍵のアップロードをしてみることにしました。

`apt show gnupg-curl` を実行してみると、そういう名前のパッケージは無さそうでした。 `dpkg -l | grep gpg` してみたところ gpg-wks-client というパッケージの説明に Web Key Service client というのがあってこれが気になりました。

```
$ dpkg -l | grep gpg
ii  gpg                                        2.2.27-3ubuntu2.1                       amd64        GNU Privacy Guard -- minimalist public key operations
ii  gpg-agent                                  2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - cryptographic agent
ii  gpg-wks-client                             2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - Web Key Service client
ii  gpg-wks-server                             2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - Web Key Service server
ii  gpgconf                                    2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - core configuration utilities
ii  gpgsm                                      2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - S/MIME version
ii  gpgv                                       2.2.27-3ubuntu2.1                       amd64        GNU privacy guard - signature verification tool
ii  libgpg-error-l10n                          1.43-3                                  all          library of error values and messages in GnuPG (localization files)
ii  libgpg-error0:amd64                        1.43-3                                  amd64        GnuPG development runtime library
ii  libgpg-error0:i386                         1.43-3                                  i386         GnuPG development runtime library
ii  libgpgme11:amd64                           1.16.0-1.2ubuntu4                       amd64        GPGME - GnuPG Made Easy (library)
ii  python3-gpg                                1.16.0-1.2ubuntu4                       amd64        Python interface to the GPGME GnuPG encryption library (Python 3)
```

`apt show gpg-wks-client` で説明を見てみると [draft-koch-openpgp-webkey-service-14](https://datatracker.ietf.org/doc/html/draft-koch-openpgp-webkey-service) に規定されているプロトコルでキーサーバにアップロードするようです。

```
$ apt show gpg-wks-client
Package: gpg-wks-client
Version: 2.2.27-3ubuntu2.1
Priority: optional
Section: utils
Source: gnupg2
Origin: Ubuntu
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Debian GnuPG Maintainers <pkg-gnupg-maint@lists.alioth.debian.org>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Installed-Size: 188 kB
Depends: dirmngr (= 2.2.27-3ubuntu2.1), gpg (= 2.2.27-3ubuntu2.1), gpg-agent (= 2.2.27-3ubuntu2.1), libassuan0 (>= 2.5.0), libc6 (>= 2.34), libgcrypt20 (>= 1.9.0), libgpg-error0 (>= 1.42)
Recommends: gnupg (= 2.2.27-3ubuntu2.1)
Homepage: https://www.gnupg.org/
Task: ubuntu-desktop-minimal, samba-server, ubuntu-desktop, cloud-image, ubuntu-desktop-raspi, ubuntu-wsl, mail-server, server, ubuntu-server-raspi, kubuntu-desktop, xubuntu-core, xubuntu-desktop, lubuntu-desktop, ubuntustudio-desktop-core, ubuntustudio-desktop, ubuntukylin-desktop, ubuntu-mate-core, ubuntu-mate-desktop, ubuntu-budgie-desktop, ubuntu-budgie-desktop-raspi
Download-Size: 62.7 kB
APT-Manual-Installed: no
APT-Sources: http://jp.archive.ubuntu.com/ubuntu jammy-updates/main amd64 Packages
Description: GNU privacy guard - Web Key Service client
 GnuPG is GNU's tool for secure communication and data storage.
 It can be used to encrypt data and to create digital signatures.
 It includes an advanced key management facility and is compliant
 with the proposed OpenPGP Internet standard as described in RFC4880.
 .
 This package provides the GnuPG client for the Web Key Service
 protocol.
 .
 A Web Key Service is a service that allows users to upload keys per
 mail to be verified over https as described in
 https://tools.ietf.org/html/draft-koch-openpgp-webkey-service
 .
 For more information see: https://wiki.gnupg.org/WKS

N: There is 1 additional record. Please use the '-a' switch to see it
```

gpg-wks-client パッケージのファイル一覧を見てみると `/usr/bin/` 以下のプログラムは無く、 `/usr/lib/gnupg/gpg-wks-client` というファイルがあるので、これが gpg のプラグインなっていそうです。

```
$ dpkg -L gpg-wks-client
/.
/usr
/usr/lib
/usr/lib/gnupg
/usr/lib/gnupg/gpg-wks-client
/usr/share
/usr/share/doc
/usr/share/doc/gpg-wks-client
/usr/share/doc/gpg-wks-client/copyright
/usr/share/lintian
/usr/share/lintian/overrides
/usr/share/lintian/overrides/gpg-wks-client
/usr/share/man
/usr/share/man/man1
/usr/share/man/man1/gpg-wks-client.1.gz
/usr/share/doc/gpg-wks-client/NEWS.Debian.gz
/usr/share/doc/gpg-wks-client/changelog.Debian.gz
```

`man gpg-wks-client` も見てみましたが、`gpg --send-key` で使われるのかはよくわかりませんでした。とりあえず今回は気にしないことにします。

あとは vDistributing keys](https://www.gnupg.org/gph/en/manual/x457.html) と [Key server (cryptographic) - Wikipedia](https://en.wikipedia.org/wiki/Key_server_%28cryptographic%29) を見て keyserver.ubuntu.com のキーサーバにアップロードしてみました。

```
gpg --keyserver keyserver.ubuntu.com --send-key F7ADBE58173B8F2E
```

実行結果。これを見るとプライマリーキーのIDを指定するのが正しそうです。また hkp://keyserver.ubuntu.com とあるので hkp プロトコルが使われたようです。
[Key server (cryptographic) - Wikipedia](https://en.wikipedia.org/wiki/Key_server_%28cryptographic%29) に [draft-shaw-openpgp-hkp-00](https://datatracker.ietf.org/doc/html/draft-shaw-openpgp-hkp-00) へのリンクがありました。

```
$ gpg --keyserver keyserver.ubuntu.com --send-key F7ADBE58173B8F2E
gpg: sending key 0629F2A2680DEB3C to hkp://keyserver.ubuntu.com
```

ブラウザで [OpenPGP Keyserver](https://keyserver.ubuntu.com/) を開いて F7ADBE58173B8F2E と入力して [Search Key] ボタンを押すと以下のような結果が表示されました。
uat の右には登録した顔写真も出ていました。

```
Search results for '0xF7ADBE58173B8F2E'

Type bits/keyID            cr. time   exp time   key expir

pub eddsa263/0a9ecad801e0ebfcf7b77f690629f2a2680deb3c 2022-08-06T11:46:33Z
   Hash=5d1e66d498df3b5c16bef55eb11a3e63

uid Hiroaki Nakamura <hnakamur@gmail.com>
sig  sig  0629f2a2680deb3c 2022-08-06T11:46:33Z ____________________ ____________________ [selfsig]

uat 
sig  sig  0629f2a2680deb3c 2022-08-06T13:28:00Z ____________________ ____________________ [selfsig]

sub eddsa263/453b5c4dde2a8cda2038ff2d4428346a4da67825 2022-08-06T12:48:07Z            
sig sbind 0629f2a2680deb3c 2022-08-06T12:48:07Z ____________________ 2023-08-06T12:48:07Z []

sub ecdh263/6867353c336f958f4e6e02db0dde7b8165a04d70 2022-08-06T12:47:57Z            
sig sbind 0629f2a2680deb3c 2022-08-06T12:47:57Z ____________________ 2023-08-06T12:47:57Z []

sub eddsa263/13f0f7266e46d846a741ff4bf7adbe58173b8f2e 2022-08-06T12:47:33Z            
sig sbind 0629f2a2680deb3c 2022-08-06T12:47:33Z ____________________ 2023-08-06T12:47:33Z []
```

検索欄に 0629F2A2680DEB3C と入力した場合は Not Found となりました。


`gpg --search-key` で確認する場合は公開鍵のフィンガープリントを指定する必要がありました。

```
$ gpg --keyserver keyserver.ubuntu.com --search-key F7ADBE58173B8F2E
gpg: data source: http://162.213.33.9:11371
gpg: key "F7ADBE58173B8F2E" not found on keyserver
gpg: keyserver search failed: Not found
$ gpg --keyserver keyserver.ubuntu.com --search-key 0629F2A2680DEB3C
gpg: data source: http://162.213.33.9:11371
gpg: key "0629F2A2680DEB3C" not found on keyserver
gpg: keyserver search failed: Not found
$ gpg --keyserver keyserver.ubuntu.com --search-key 0x0629F2A2680DEB3C
gpg: data source: http://162.213.33.9:11371
gpg: key "0x0629F2A2680DEB3C" not found on keyserver
gpg: keyserver search failed: Not found
$ gpg --keyserver keyserver.ubuntu.com --search-key 0a9ecad801e0ebfcf7b77f690629f2a2680deb3c
gpg: data source: http://162.213.33.9:11371
(1)     Hiroaki Nakamura <hnakamur@gmail.com>
          263 bit EDDSA key 0629F2A2680DEB3C, created: 2022-08-06
Keys 1-1 of 1 for "0a9ecad801e0ebfcf7b77f690629f2a2680deb3c".  Enter number(s), N)ext, or Q)uit > 1
gpg: key 0629F2A2680DEB3C: "Hiroaki Nakamura <hnakamur@gmail.com>" not changed
gpg: Total number processed: 1
gpg:              unchanged: 1
```

