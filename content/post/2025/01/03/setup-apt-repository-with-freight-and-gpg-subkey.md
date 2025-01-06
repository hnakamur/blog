---
title: "freightでGPGの副鍵を使ってaptレポジトリをセットアップ"
date: 2025-01-03T21:14:54+09:00
draft: true
---

## はじめに

久しぶりにaptレポジトリをセットアップしたので手順のメモです。せっかくなので今回はGPGで署名用の副鍵を使うようにしました。

昔[freightでプライベートdebレポジトリ作成 · hnakamur's blog](https://hnakamur.github.io/blog/2017/08/05/create-private-deb-repository-with-freight/)という記事を書きました。
しかし、その後`sudo apt install ./debファイル名`で依存パッケージも含めてインストールできることを知り、これで十分と思っていました。

しかし、自作のパッケージが増えてきたので、aptレポジトリを作ることにしました。

## GPGで署名用の副鍵を作る

作業用のIncusコンテナ名を変数に設定します。

```
gpgwork_container=gpgwork
```

以下のコマンドを実行してUbuntu 24.04のIncusコンテナを作ります。下記では`sources_list`の`URIs`をデフォルトの`http://archive.ubuntu.com/ubuntu`からさくらインターネットの非公式ミラーに変更しています。

```
incus launch images:ubuntu/24.04/cloud "$gpgwork_container" -c user.user-data="#cloud-config
timezone: Asia/Tokyo
apt:
  sources_list: |
    Types: deb deb-src
    URIs: http://ftp.sakura.ad.jp/ubuntu/
    Suites: noble noble-updates noble-backports
    Components: main universe restricted multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
    
    Types: deb deb-src
    URIs: http://security.ubuntu.com/ubuntu/
    Suites: noble-security
    Components: main universe restricted multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
package_update: true
package_upgrade: true
packages:
  - gpg
"
```

以下のコマンドを実行してIncusコンテナにシェルを起動します。

```
incus shell "$gpgwork_container"
```

`eth0`をリンクダウンしてネットワークをオフラインにします。

```
ip link set dev eth0 down
```

{{< details summary="(参考) 使用したgpgのバージョンは2.4.4。" >}}
```
root@gpgnaruh:~# gpg --version
gpg (GnuPG) 2.4.4
libgcrypt 1.10.3
Copyright (C) 2024 g10 Code GmbH
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
{{< /details >}}

この後使う変数を設定しておきます。値は適宜してください。

```
NAME_REAL="Hiroaki Nakamura"
NAME_COMMENT="for apt.naruh.org"
NAME_EMAIL=hnakamur@naruh.org
USER_ID="$NAME_REAL <$NAME_EMAIL> $NAME_COMMENT"
PASSPHRASE=パスフレーズ
```

GPGで主鍵を作成します。下記ではアルゴリズムはed25519で有効期限は無期限としています。

```
gpg --batch --passphrase "$passphrase" \
 --quick-gen-key "$user_id" ed25519 cert never
```

今作成した鍵のフィンガープリントを下記で利用するため`KEY`変数に設定します。

```
KEY=$(gpg --list-options show-only-fpr-mbox --list-secret-keys $NAME_EMAIL | cut -d ' ' -f 1)
```

署名用の副鍵を作成します。下記ではアルゴリズムはed25519で有効期限は1年としています。

```
gpg --batch --passphrase "$PASSPHRASE" --pinentry-mode=loopback \
 --quick-add-key $KEY ed25519 sign 1y
```

副鍵をエクスポートします。

```
gpg --batch --passphrase "$PASSPHRASE" --pinentry-mode=loopback \
 --output $NAME_EMAIL-gpg-subkeys.gpg \
 --export-secret-subkeys $KEY
```

`$gpgwork_container`のコンテナから抜けます。

```
exit
```

Incusのホストで以下のコマンドを実行して、上記でエクスポートした副鍵をホストにコピーします。

```
NAME_EMAIL=hnakamur@naruh.org
```

```
incus file pull $gpgwork_container/root/$NAME_EMAIL-gpg-subkeys.gpg .
```

## freightのコンテナをセットアップする

### freight用のコンテナを作って、署名用副鍵をインポート

freight用のIncusコンテナ名を変数に設定します。

```
freight_container=freight
```

以下のコマンドを実行してUbuntu 24.04のIncusコンテナを作ります。今回は`gpg`に加えて`git`と`make`パッケージもインストールします。

```
incus launch images:ubuntu/24.04/cloud "$freight_container" -c user.user-data="
#cloud-config
timezone: Asia/Tokyo
apt:
  sources_list: |
    Types: deb deb-src
    URIs: http://ftp.sakura.ad.jp/ubuntu/
    Suites: noble noble-updates noble-backports
    Components: main universe restricted multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
    
    Types: deb deb-src
    URIs: http://security.ubuntu.com/ubuntu/
    Suites: noble-security
    Components: main universe restricted multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
runcmd:
  - [touch, /run/cloud.init.ran.debug]
package_update: true
package_upgrade: true
packages:
  - gpg
  - git
  - make
"
```

{{< details summary="(注意) 上記のYAMLのリストのインデントは必須" >}}
`packages`のリストは上記のようにインデントが必須です。
以下のようにインデントなしで書くと、パッケージがインストールされませんでした。
```
packages:
- gpg
- git
```
{{< /details >}}

署名用の副鍵をfreight用のコンテナにコピー。

```
incus file push $NAME_EMAIL-gpg-subkeys.gpg $freight_container/root/
```

freight用のコンテナでシェルを起動。

```
incus shell $freight_container
```

cloud-initの処理が終わるのを待つ。

```
cloud-init status -w
```

{{< details summary="cloud-init status -wの出力例" >}}
```
root@freight:~# cloud-init status -w
.......................................status: done
```
{{< /details >}}

この後使う変数を設定しておきます。GPG鍵を作った時と同じ値を設定してください。

```
NAME_EMAIL=hnakamur@naruh.org
PASSPHRASE=パスフレーズ
```

署名用の副鍵をインポートします。

```
gpg --batch --passphrase "$PASSPHRASE" --pinentry-mode=loopback \
 --import $NAME_EMAIL-gpg-subkeys.gpg
```

{{< details summary="上記のコマンドの出力例" >}}
```
root@docker:~# gpg --batch --passphrase "$PASSPHRASE" --pinentry-mode=loopback \
 --import hnakamur\@naruh.org-gpg-subkeys.gpg
gpg: /root/.gnupg/trustdb.gpg: trustdb created
gpg: key E867B9D8764E1BD5: public key "Hiroaki Nakamura <hnakamur@naruh.org> for apt.naruh.org" imported
gpg: To migrate 'secring.gpg', with each smartcard, run: gpg --card-status
gpg: key E867B9D8764E1BD5: secret key imported
gpg: Total number processed: 1
gpg:               imported: 1
gpg:       secret keys read: 1
gpg:   secret keys imported: 1
```
{{< /details >}}

下記で使用するため、インポートした鍵のフィンガープリントを変数に設定しておきます。

```
KEY=$(gpg --list-options show-only-fpr-mbox --list-secret-keys $NAME_EMAIL | cut -d ' ' -f 1)
```

### インポートした署名用副鍵のパスフレーズを変更する

前項に引き続き、freight用のコンテナで作業します。

この後使う変数を設定します。

```
NEW_PASSPHRASE=副鍵用の新しいパスフレーズ
```

インポートした鍵のパスフレーズを変更します。

```
gpg --command-fd 0 --pinentry-mode loopback \
 --change-passphrase $KEY <<EOF
$PASSPHRASE
$NEW_PASSPHRASE
EOF
```

新しいパスフレーズをファイルに保存します。これは、のちほどaptレポジトリにdebパッケージを追加する際に使用します。

```
echo "$NEW_PASSPHRASE" > ~/.config/gpg-sign-subkey-passphrase
```

### freightをセットアップする

freightのgitレポジトリをcloneします。

```
git clone https://github.com/freight-team/freight.git
```

レポジトリのディレクトリに移動します。

```
cd freight
```

freightをインストールします。

```
make install
```

freightの設定ファイルを作成します。

```
cat <<EOF > /etc/freight.conf
VARLIB="/var/lib/freight"
VARCACHE="/var/cache/freight"
ORIGIN="Freight"
LABEL="Freight"
CACHE="off"
GPG="${NAME_EMAIL}"
GPG_DIGEST_ALGO="SHA512"
SYMLINKS="off"
EOF
```

## freightで作成したaptレポジトリにdebパッケージを追加する


