Title: nginxのカスタムrpmをmockでビルドできることを確認してからcoprでビルド・配布する環境を作りました
Date: 2015-12-15 04:19
Category: blog
Tags: mock, copr, rpm, nginx, docker
Slug: blog/2015/12/15/using_mock_and_copr_to_build_nginx_rpm_on_docker

## はじめに
[Travis CIとcopr.fedoraproject.orgを使ってrpmをビルド・配布するのを試してみた · hnakamur's blog at github](/blog/2015/11/26/use_travis_and_copr_to_build_and_host_rpm/)と[mockコマンドでrpmをビルドする · hnakamur's blog at github](/blog/2015/12/05/build_rpm_with_mock/)の環境でいくつかrpmをビルド・配布してみたのですが、手元の環境でビルドを成功させるまでに試行錯誤するのと、coprにsrpmをアップロードしてビルド・配布するのが別の環境だと面倒なことに気付きました。

そこで、1つのdockerコンテナで両方を行えるようにしました。

## Travis CIは外しました
また、Travis CIは使わないようにしました。理由は2つあります。1つめの理由はgithubのプロジェクトごとにTravis CIのプロジェクトを作ってcopr APIのログイン名、ユーザ名、トークンを環境変数で設定するのが面倒だったからです。これ自体はTravisのAPIを使えば解決する問題かもしれません。

2つめの理由は、結局手元の環境でビルドを試すので、そこからそのままcoprにsrpmを上げるほうが手っ取り早いことに気づいたからです。これは初回にrpmのspecファイルを作成するときも、その後specファイルのバージョンを更新して新しいバージョンのrpmを作成するときもそうです。

## nginxのカスタムrpmをビルド・配布するためのdockerコンテナ

githubレポジトリ[hnakamur/nginx-rpm](https://github.com/hnakamur/nginx-rpm)に公開しています。対応するcoprのプロジェクトは[hnakamur/nginx Copr](https://copr.fedoraproject.org/coprs/hnakamur/nginx/)です。

## ビルド前の準備
### copr APIトークンを.envrcにコピー
coprを使うにはFedoraアカウントが必要です。[Sign up for a Fedora account](https://admin.fedoraproject.org/accounts/user/new) から登録してください。

Fedoraアカウントにログインした状態で [API for Copr](https://copr.fedoraproject.org/api/)を開くと、ページの先頭にAPI Tokenというセクションがあり、以下のような内容が表示されます。

```
[copr-cli]
login = ログインID
username = ユーザ名
token = トークン
copr_url = https://copr.fedoraproject.org
# expiration date: 2016-05-12
```

以下のコマンドを実行して上記のgithubレポジトリを手元にコピーします。

```
git clone https://github.com/hnakamur/nginx-rpm
```

`.envrc.example` を `.envrc` にコピーして、上で表示したログインID、ユーザ名、トークンを `.envrc` 内の `COPR_LOGIN`, `COPR_USERNAME`, `COPR_TOKEN` 環境変数に設定します。

```
# NOTE: Copy this file to .envrc and edit the values
# Go https://copr.fedoraproject.org/api/ and login in and see the values to set.
export COPR_LOGIN=_your_login_here_
export COPR_USERNAME=_your_username_here_
export COPR_TOKEN=_your_token_here_
```

セキュリティを考慮してこれらの値はdockerのイメージには埋め込まず、実行時にdockerの `-e` オプションで渡すようにしています。具体的には [docker_wrapper.sh](https://github.com/hnakamur/nginx-rpm/blob/master/docker_wrapper.sh) の `docker run` の行を参照してください。

### specファイルの調整

specファイルは [SPECS/nginx](https://github.com/hnakamur/nginx-rpm/blob/master/SPECS/nginx.spec) にあります。各自のニーズに応じて適宜調整します。現時点では http://nginx.org/packages/centos/7/SRPMS/ で配布されているCentOS 7用のsrpmをベースに以下の3つのモジュールを組み込んだものになっています。

* [openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module)
* [yaoweibin/nginx_upstream_check_module](https://github.com/yaoweibin/nginx_upstream_check_module)
* [replay/ngx_http_consistent_hash](https://github.com/replay/ngx_http_consistent_hash)

nginx.orgで配布されているsrpm内のnginx.specからの差分は https://github.com/hnakamur/nginx-rpm/compare/7e234d2a222778c0a46204dba4e2dcaae8bf7894...ce4e842731a9b90034f9e00796e16839d8bda826 で見られます。

### SOURCES/*ファイルの調整

[SOURCES/](https://github.com/hnakamur/nginx-rpm/tree/master/SOURCES)にsrpmで必要なソースファイルを置いています。必要に応じて調整してください。今は http://nginx.org/packages/centos/7/SRPMS/ で配布されているCentOS 7用のsrpmから頂いたものをそのまま使用しています。

なお、nginx自体のソースコード(例: nginx-1.9.9.tar.gz)や各エクステンションのソースコードは含めず、ビルド時にダウンロードするようにしています。これはgitレポジトリの肥大化を防ぐためです。

### ビルドスクリプトの調整

ビルドスクリプト[scripts/build.sh](https://github.com/hnakamur/nginx-rpm/blob/master/scripts/build.sh)も適宜調整します。

* copr_project_name、copr_project_description、copr_project_instructions、rpm_nameをお好みで編集してください。
* `download_source_files` 関数はspecファイルの `/^Source[0-9]*:` にマッチするパターンで値がhttpから始まるURLについてダウンロードするようにしています。そしてURLの最後のスラッシュ以降をファイル名として採用しています。このルールから外れる場合は、この関数を適宜変更してください。

### Dockerfileとdockerのラッパースクリプトを調整

[Dockerfile](https://github.com/hnakamur/nginx-rpm/blob/master/Dockerfile)と[docker_wrapper.sh](https://github.com/hnakamur/nginx-rpm/blob/master/docker_wrapper.sh)を適宜調整してください。

通常は[docker_wrapper.sh](https://github.com/hnakamur/nginx-rpm/blob/fa051c195e030c2e7f247fa258c6fad1ef9f0dde/docker_wrapper.sh)のdockerimageを好きな名前に変えるぐらいで大丈夫だと思います。

## dockerイメージを作成

以下のコマンドを実行してdockerイメージをビルドします。

```
./docker_wrapper.sh build
```

## dockerイメージを起動してmockでrpmをビルド

以下のコマンドを実行してdockerイメージを起動してbashプロンプトを表示します。

```
source .envrc
./docker_wrapper.sh bash
```

ちなみに私は[direnv/direnv](https://github.com/direnv/direnv)を使っているので、 `source .envrc` の行は自分で入力しなくても[direnv/direnv](https://github.com/direnv/direnv)が実行してくれるので便利です。direnvについては[改めて、direnvを使いましょう！ - HDE BLOG](http://blog.hde.co.jp/entry/2015/02/27/182117)などの記事を参照してください。

dockerイメージのbashプロンプトで以下のコマンドを実行してmockでrpmをビルドします。


```
./build.sh mock
```

mockはchroot環境を作ってそこでrpmをビルドするようになっているので、chroot環境の作成にちょっと時間がかかります。

dockerコンテナという独立空間が既にあるのにmockでchroot環境を作るのは無駄なんですが、coprがmockを使っているためmockでビルドが成功することを確認してからcoprにsrpmをアップロードするほうが、coprでのビルド失敗を減らせて良いですのでこうしています。


## coprにsrpmをアップロードして、rpmをビルド・配布

mockでrpmのビルドが成功することを確認できたら、dockerコンテナ内で以下のコマンドを実行してsrpmをcoprにアップロードします。

```
./build.sh copr
```

[scripts/build.sh](https://github.com/hnakamur/nginx-rpm/blob/master/scripts/build.sh)の `copr_project_name` で指定した名前のプロジェクトがcopr上に存在しない場合はまず作成してからsrpmをアップロードするようになっています。

coprのプロジェクト `https://copr.fedoraproject.org/coprs/${COPR_USER_NAME}/${copr_project_name}/` でビルドが完了すれば、rpmのレポジトリとして利用可能です。

## まとめ
mockとcoprを使ってnginxのカスタムrpmをビルド・配布する環境について説明しました。

mockを使ってクリーンな環境でビルドできるので、今回のスクリプトでdockerコンテナを使う必要性は特にありません。Dockerfileでセットアップしたのと同等のCentOS7環境があれば [scripts/build.sh](https://github.com/hnakamur/nginx-rpm/blob/master/scripts/build.sh)を使ってsrpmのビルド、rpmのビルド、srpmのcoprへのアップロードを行えます。

mockでのrpmのビルドが失敗した場合の調査方法とかcoprのAPIをcopr-cliではなくcurlで呼び出している話とか、いくつか書きたい話があるので日を改めて別記事として書こうと思います。
