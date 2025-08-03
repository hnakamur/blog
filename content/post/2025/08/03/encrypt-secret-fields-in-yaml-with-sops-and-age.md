---
title: "sopsとageを使ってYAMLファイル内の機密情報だけを暗号化"
date: 2025-08-03T20:31:12+09:00
---

## はじめに

[fujiwaraさん](https://zenn.dev/fujiwara)の[sops+age](https://zenn.dev/fujiwara/scraps/d17a697903343a)のスクラップブックをみて、自分でも調べてみたメモです。

私が想定している使い方は、サーバー上で人間が関与せずに、設定ファイルを復号して参照するというものです。
復号に必要な情報はサーバー上にそろっているので、サーバーに侵入されてファイルを参照されると復号されてしまいますが、それは許容するものとします。

## sopsとageについて

* [getsops/sops: Simple and flexible tool for managing secrets](https://github.com/getsops/sops)
* [FiloSottile/age: A simple, modern and secure encryption tool (and Go library) with small explicit keys, no config options, and UNIX-style composability.](https://github.com/FiloSottile/age)

### age
先にageについてのメモ。

ageの作者[FiloSottile (Filippo Valsorda)](https://github.com/FiloSottile)さんは元Goチームメンバで現在もGoのcryptoパッケージのメンテナをされている暗号の専門家です。

[age and Authenticated Encryption](https://words.filippo.io/age-authentication/)によるとageはファイルの暗号化に特化したツールとして作ったそうです。GnuPGを置き換えるつもりではないが、GnuPGがファイルの暗号化に適していないので、そのギャップを埋めるために作ったとのこと。

READMEによるとFilippoさんはアゲと発音されているそうです。

### sops
sopsはREADMEによるとSecret OPerationSの略です。安全な運用をサポートするためのツールということでしょうか。

`SOPS is an editor of encrypted files that supports YAML, JSON, ENV, INI and BINARY formats and encrypts with AWS KMS, GCP KMS, Azure Key Vault, age, and PGP.`という説明文がありました。

「6. Motivation」の項によると元はMozillaで開発していたようです。

## インストール

sopsもageもリリースページにLinux amd64のスタティックリンクのバイナリがあります。それをダウンロードしてPATHの通ったディレクトリに置けばOKです。

## 準備
### ageでの鍵作成

sopsのREADMEの[2.3 Encrypting using age](https://github.com/getsops/sops?tab=readme-ov-file#id8)にsopsがageのキーを探すときのデフォルトのパスが書かれています。以下はそこに置く場合の手順です。

```
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
```

age-keygenを実行したときに、以下のように公開鍵が出力されます。
```
Public key: age1vhw6fwfr058c364r4lwfzq98gtdrz4arlf9lc4zpeu0h4xqckdcq9p4h5d
```

公開鍵はメモっておかなくても 秘密鍵があれば`age-keygen -y`で確認できます。

```
$ age-keygen -y ~/.config/sops/age/keys.txt
age1vhw6fwfr058c364r4lwfzq98gtdrz4arlf9lc4zpeu0h4xqckdcq9p4h5d
```

### `.sops.yaml`設定ファイルで暗号化対象のファイル名と項目を指定

[ドキュメント](https://getsops.io/docs/)の[Encrypting only parts of a file](https://getsops.io/docs/#encrypting-only-parts-of-a-file)の項に説明があります。

例えば拡張子が`.yaml`のファイル内の`password`の項目だけを暗号化の対象とする場合は、以下の内容で`.sops.yaml`ファイルを作成します。

```
creation_rules:
  - path_regex: '^.*\.yaml$'
    encrypted_regex: '^password$'
```

ファイル名は[`.sops.yml`だと警告を出す](https://github.com/getsops/sops/blob/v3.10.2/config/config.go#L39-L93)ようになっているので`.sops.yaml`にしてください。

他の指定方法もありますので、詳しくは上記のドキュメントを参照してください。

### `.sops.yaml`設定ファイルでYAMLのインデントを指定

[YAML indentation](https://getsops.io/docs/#yaml-indentation)に説明があります。

デフォルトではインデントは4になっています。2に変更したい場合は、都度引数で`--indent=2`と指定しても良いそうですが、以下の設定を追加するのが楽です。

```
stores:
  yaml:
    indent: 2
```

## 暗号化

例えば以下の`example.yaml`というファイルを暗号化してみます。
```
db:
  # ユーザー名
  user: foo
  # パスワード
  password: hogehoge
```

```
sops encrypt --age $(age-keygen -y ~/.config/sops/age/keys.txt) example.yaml > encrypted.yaml
```

暗号化されたファイルを見てみると以下のようになっていました。

```
db:
  # ユーザー名
  user: foo
  # パスワード
  password: ENC[AES256_GCM,data:2Gxd7D9xehA=,iv:qZSPph9pMMqPtOMDQVvzQc1gfagDuEdFpOkPJFbWUHw=,tag:Je12h+2ERRcYy0ebajNYGw==,type:str]
sops:
  age:
    - recipient: age1xwzkkvxll278p92rxawljdmm6rk0maufrsz668a26x30rnuwn53q2jr4m6
      enc: |
        -----BEGIN AGE ENCRYPTED FILE-----
        YWdlLWVuY3J5cHRpb24ub3JnL3YxCi0+IFgyNTUxOSBIM1Y3R0xmRVZudjVhOXRi
        bXhkaVkzc1AxNjVySkJYQlUxQXk5Qi9sUlRjCjF2YWZjRU5oNGhnbTZocjJ2VWRK
        NE52cDM2TU42ZDRHYTVZdENaWjVEZzgKLS0tIG5DRlpiUTd5WG1ucGZ4a3V4Q01X
        ZHgyYll4VlhYN2pLQVg1UTJXeUlFTWMKnfQkQ2/hz9SS4TsdMWyW+JDPHYy8yUgt
        lF5BkP94bOfqL0/KZiOcWmT/uIme8QEkdjwhXT5ZAyTi3QVUx91aCQ==
        -----END AGE ENCRYPTED FILE-----
  lastmodified: "2025-08-03T12:58:55Z"
  mac: ENC[AES256_GCM,data:S30XyB3F/W7sk6iAn/W9BXqx0KtTgxCt8wkVGPvSPMnCh1cMQfdxRIJAvJxq/0HCntl0Sq2wKRHoIDVYAnP4Hd9Rl6gcY5gv+MM1TUeK4jBgoC8D/qFYDBnPwNXIdb0GvmGDy9gaJcXOQjcMcDTXmAO4JCEBIHaJC14RCWw0nZY=,iv:t1I1QrmYO7C35Mvh27BG2hEhIkmzGeiKwr/HQwrc/jQ=,tag:hJkhLCSIa/EAlYUh/mLT0Q==,type:str]
  encrypted_regex: ^password$
  version: 3.10.2
```

`user`のキーは暗号化されずにそのままになっており、`password`のキーは暗号化されています。
また`sops`というキーに復号に必要な情報などが追加されています。

`age`の`recipient`は受信者という意味ですが、値としては公開鍵になっています。

今回は違いますが、秘密鍵を持っている人に向けて暗号を送るという使い方を想定したときに、送信側はその人の公開鍵で暗号化して、受け取った側は秘密鍵で復号するというところから来ているようです。

なお、`sops encrypt`の`--in-place`オプションを使えば、ファイルを暗号化した結果で上書きもできます。詳しくは`sops encrypt --help`を参照してください。

## 復号

上記で暗号化したファイルを復号してみます。

```
sops decrypt encrypted.yaml > decrypted.yaml
```

元のファイルと内容が一致していることを確認しました。

```
$ cmp decrypted.yaml example.yaml
$
```

`sops decrypt`の`--in-place`オプションを使えば、ファイルを暗号化した結果で上書きもできます。詳しくは`sops decrypt --help`を参照してください。

## ファイルが暗号化されているかをsopsコマンドで確認する

`sops filestatus ファイル名`でファイルが暗号化されているかいないかを確認できます。

```
$ sops filestatus encrypted.yaml
{"encrypted":true}
$ sops filestatus decrypted.yaml
{"encrypted":false}
```

## gitのpre-commitで暗号化されていないファイルをコミットするのを防ぐ

[Q: How to prevent unencrypted files from being committed · Issue #571 · getsops/sops](https://github.com/getsops/sops/issues/571)というイシューがありました。

[May 12, 2023のコメント](https://github.com/getsops/sops/issues/571#issuecomment-1545143527)のリンク先を見てみましたが、Pythonのpre-commitというモジュールに依存しているのが、個人的には好きになれませんでした。

そこでsopsコマンドを使ったシェルスクリプトを書いてみました。

dashでも動くように配列を使わないようにしています。その代わり空白を含んだファイル名が扱えないという制限があります。

`.git/hooks/pre-commit`を以下のような内容で作成します。`files_to_encypt`変数の値はレポジトリに応じて適宜調整してください。
```
#!/bin/sh
#
# A "pre-commit" hook script to prevent unencrypted files from being committed.
#

set -eu

#
# List of files that must be encrypted with the "sops" command.
#
# NOTE: This must be adjusted for each project.
#
files_to_encrypt="example.yaml example2.yaml"

if ! type sops >/dev/null 2>&1; then
  echo 1>&2 "Please install the \"sops\" command and ensure it is available in your PATH."
  exit 2
fi

staged_files=$(git diff --cached --name-only)

for file in $files_to_encrypt; do
  for staged_file in $staged_files; do
    if [ "$staged_file" = "$file" ]; then
      if [ $(sops filestatus "$staged_file") != '{"encrypted":true}' ]; then
        echo 1>&2 "Please encrypt \"$file\" with the \"sops\" command."
        exit 1
      fi
    fi
  done
done
```

## その他試してないことのメモ

[Adding and removing keys](https://getsops.io/docs/#adding-and-removing-keys)の項によると、暗号化したファイルに鍵を追加したり削除したりローテートなどもできるようです。

rotate commandのドキュメントではageについての記載がないですが、`sops rotate --help`で確認すると、`--add-age`や`--rm-age`オプションがあるのでageも対応しているようです。

また、`sops --help`を見ると`exec-env`や`exec-file`サブコマンドで復号した値を使ってコマンドを実行したり、`edit`サブコマンドで暗号化されたファイルを直接編集したりもできるようです。
