+++
title="freightでプライベートdebレポジトリ作成"
date = "2017-08-05T17:40:00+09:00"
tags = ["deb", "freight"]
categories = ["blog"]
+++


## はじめに

CentOS だとカスタムrpmを作って `yum install rpmファイル名` で依存パッケージとともにインストールできますが、Ubuntuだと `dpkg -i debファイル名` でインストールは出来ますが依存パッケージは入りません。

[How to let \`dpkg -i\` install dependencies for me? - Ask Ubuntu](https://askubuntu.com/questions/40011/how-to-let-dpkg-i-install-dependencies-for-me) によると `dpkg -i` の後に `apt -f install` するか、 `gdebi-core` パッケージを入れておいて `sudo gdebi debファイル名` という手はあるようです。

とはいえ、PPAにアップロードする前に `apt install` で動作確認したいとか、PPAで公開しないdebパッケージを `apt` コマンドでインストールしたいというケースはあるので、プライベートdebレポジトリを作りたいところです。

[DebianRepository/Setup - Debian Wiki](https://wiki.debian.org/DebianRepository/Setup) に多くのツールが紹介されていますが、
[Create deb repository with several versions of the same package - Ask Ubuntu](https://askubuntu.com/questions/84788/create-deb-repository-with-several-versions-of-the-same-package#comment1444951_668791) で紹介されていた https://github.com/freight-team/freight を使ってみたところ、私のニーズに丁度良い感じでした。ということでメモです。

手順の作成で試行錯誤したのですが
[Créer un repository Debian signé avec Freight | VaLouille](http://blog.valouille.fr/2014/03/creer-un-depot-debian-signe-avec-freight/)
をGoogle翻訳で英訳して読んで動かせるようになりました。先人の記事に感謝です。

## freightのインストール手順

[From a Debian archive](https://github.com/freight-team/freight#from-a-debian-archive)
の手順を少し変えて以下のようにインストールしました。

```console
sudo apt update
sudo apt -y install curl
curl -k https://swupdate.openvpn.net/repos/repo-public.gpg | sudo apt-key add -
echo "deb http://build.openvpn.net/debian/freight_team $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/freight.list
sudo apt update
sudo apt -y install freight
```

私はdebをビルドしたサーバとは別にLXDのコンテナを作ってその中で root ユーザで実行していたので `sudo` は不要なのですが、そうでない環境でセットアップすることも想定して `sudo` は付けておきます。

`curl` に `-k` オプションを指定しないと以下のエラーが出たので、上の手順では `-k` を指定しています。

```console
$ curl https://swupdate.openvpn.net/repos/repo-public.gpg
curl: (77) Problem with the SSL CA cert (path? access rights?)
```

## gpgの秘密鍵のインポート

debをビルドしたサーバで
[gpgで秘密鍵を作成する](https://hnakamur.github.io/blog/2017/07/01/generate-secret-key-with-gpg/) の「秘密鍵をエクスポートする」の手順を実行して `lxc file push` コマンドを使ってLXDコンテナに秘密鍵を転送し、以下のコマンドでインポートしました。

```console
gpg --import gpg-hnakamur-secret.key.pem
```

## レポジトリの初期化

以下の手順でレポジトリのディレクトリを作成して初期化します。ディレクトリや各引数は適宜調整してください。今回は xenial 上で golang-1.9 用のレポジトリを作るので `--suite` は `xenial-golang-1.9` としましたが、特にレポジトリを分ける必要がなければ `xenial` だけで良いです。

```console
mkdir -p /var/www/freight
cd /var/www/freight
freight-init --gpg=hnakamur@gmail.com --libdir=/var/www/freight/lib \
    --cachedir=/var/www/freight/cache --archs="amd64 all" \
    --origin="My Internal Repository" --label="My Internal Reposiroty" \
    --suite="xenial-golang-1.9"
```

## レポジトリにdebパッケージを追加

debをビルドしたサーバで `lxc file push` コマンドを使って作成した deb パッケージをLXDコンテナの `/root/` ディレクトリに転送しておいて、LXDコンテナで以下のコマンドを実行しdebファイルをレポジトリに追加します。

```console
freight add /root/*.deb apt/xenial-golang-1.9
freight cache apt/xenial-golang-1.9
```

gpgのパスフレーズを求めるプロンプトが表示されますので、パスフレーズを入力してください。

## ローカルレポジトリを使うための設定

ローカルレポジトリを使うには以下のように `.list` ファイルを作ればOKです。
`xenial-golang-1.9` の部分は `fright-init` の `--suite` の引数に指定した値に合わせます。ディレクトリや `.list` のファイル名も適宜調整してください。

```console
echo "deb file:/var/www/freight/cache xenial-golang-1.9 main" | sudo tee /etc/apt/sources.list.d/local-golang-1.9.list
```

## ローカルレポジトリの公開鍵をapt-keyに追加

以下のコマンドでローカルレポジトリの公開鍵を追加します。

```console
apt-key add /var/www/freight/cache/pubkey.gpg
```

## パッケージのインストール

これでローカルパッケージが使えるようになりました。あとは `apt update` して `apt install` するだけです。今回は golang-go パッケージを作ったので以下のようになります。

```console
sudo apt update
sudo apt -y install golang-go
```

これで依存するパッケージとともにインストールされました。素晴らしい！

## おわりに

今回は試していませんが、 `/var/www/freight/cache` を nginx などのウェブサーバで公開して、 `.list` ファイルの `deb` の後の `file:/var/www/freight/cache` の部分を公開したURLに変えればリモートのマシンでインストールも出来ると思います。

