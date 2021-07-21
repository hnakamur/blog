---
title: "Ubuntu 20.10 で apt-key add が deprecated になっていたので代替スクリプトを書いた"
date: 2020-12-10T22:37:26+09:00
lastmod: 2021-07-21T10:06:06+09:00
---
## 2021-07-21 追記：このスクリプトは使わないでください

[第675回　apt-keyはなぜ廃止予定となったのか：Ubuntu Weekly Recipe｜gihyo.jp … 技術評論社](https://gihyo.jp/admin/serial/01/ubuntu-recipe/0675)
によると
`/etc/apt/trusted.gpg.d/` にファイルを作るのはリスク管理として完全な対応ではなく、Debian Wiki では禁止(MUST NOT)との記載があるとのことです。

## はじめに

Ubuntu 20.10 環境でサードパーティのレポジトリを追加しようと `apt-key add` を実行したところ deprecated と言われました。

[apt-key (8)](http://manpages.ubuntu.com/manpages/groovy/en/man8/apt-key.8.html) によると
`/etc/apt/trusted.gpg.d/` にファイルを作れとのことです。

> Note: Instead of using this command a keyring should be placed directly in the
> /etc/apt/trusted.gpg.d/ directory with a descriptive name and either "gpg" or "asc" as
> file extension.

検索してみると
[How to download public key used to verify GnuPG signature for the repository – sleeplessbeastie's notes](https://blog.sleeplessbeastie.eu/2018/08/08/how-to-download-public-key-used-to-verify-gnupg-signature-for-the-repository/)
に手順が紹介されていました。

`gpg --import` を使ってキーをインポートした後、パーミションを 644 に変えれば良いそうです。
これを毎回手で打つのは面倒と思ったのでスクリプトにしました。

### 代替スクリプトの内容

以下のスクリプトを PATH の通った場所に `apt-key-add` というファイル名で保存します。

```sh
#!/bin/bash
set -e
if [ $# -ne 2 -o $UID -ne 0 ]; then
  cat <<EOF >&2
Usage: my-apt-key-add src dest_basename

Specify - for src to use stdin as input.
The imported key filename will be "/etc/apt/trusted.gpg.d/\${dest_basename}.gpg".

This script must be executed by root.
EOF
  exit 2
fi

src="$1"
dest="/etc/apt/trusted.gpg.d/$2.gpg"
if [ -f "$dest" ]; then
  echo "Exiting without adding key since destination file $dest already exists." >&2
  exit 1
fi

gpg --no-default-keyring --keyring "gnupg-ring:$dest" --import "$src"
chmod 644 "$dest"
rm "$dest~"
```

### 使い方

従来は

```console
curl キーのURL | sudo apt-key add -
```

でしたが、 `apt-key add -` の代わりに `apt-key-add - 出力ファイルのベース名` と置き換えて

```console
curl キーのURL | sudo apt-key-add - 出力ファイルのベース名
```

と実行します。

すると `/etc/apt/trusted.gpg.d/出力ファイルのベース名.gpg` というファイル名で保存されます。

可能なら `apt-key add -` と同じような呼び出し方にしたいところでしたが `apt-key add` は `/etc/apt/trusted.gpg` という固定のファイル名にキーを追加していくのに対し、代替スクリプトの `apt-key-add` は `/etc/apt/trusted.gpg.d/` ディレクトリに新規ファイルを作るという違いがあるので、ベース名は明示的に指定するしかないのでこうなっています。

### 代替スクリプトの実装メモ

使うだけなら以下は読まなくて大丈夫です。

#### `gpg --import` はASCII形式とバイナリ形式どちらもインポート可能

この代替スクリプトを書くにあたって [LLVM Debian/Ubuntu packages](https://apt.llvm.org/) の [llvm-snapshot.gpg.key](https://apt.llvm.org/llvm-snapshot.gpg.key) で検証しました。

file コマンドでは ASCII 形式とバイナリ形式の GPG 鍵は以下のように表示されました。

```console
$ file llvm-snapshot.gpg.key
llvm-snapshot.gpg.key: PGP public key block Public-Key (old)
```

```console
$ file /etc/apt/trusted.gpg.d/llvm-snapshot.gpg
/etc/apt/trusted.gpg.d/llvm-snapshot.gpg: PGP/GPG key public ring (v4) created Mon Mar 11 17:22:04 2013 RSA (Encrypt or Sign) 4096 bits MPI=0xe2d1650002933f9a...
```

import してできたバイナリ形式を再度別の新しいファイルに `gpg --import` でインポートするのも問題なくできました。
この場合は入力ファイルと出力ファイルは全く同じ内容になっていました (cmp コマンドで比較して確認)。
