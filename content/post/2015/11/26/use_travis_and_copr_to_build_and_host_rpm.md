Title: Travis CIとcopr.fedoraproject.orgを使ってrpmをビルド・配布するのを試してみた
Date: 2015-11-26 22:33
Category: blog
Tags: centos, rpm
Slug: blog/2015/11/26/use_travis_and_copr_to_build_and_host_rpm

## 2015-12-15 追記

[nginxのカスタムrpmをmockでビルドできることを確認してからcoprでビルド・配布する環境を作りました · hnakamur's blog at github](/blog/2015/12/15/using_mock_and_copr_to_build_nginx_rpm_on_docker/)という記事を書きましたのでそちらもご参照ください。


## はじめに

CentOSを使っていると、パッケージのバージョンが古いのでspecファイルを改変してrpmをビルドすることがちょくちょくあります。
一度ビルドした後は、自作rpmのレポジトリサーバを立ててそこに置いておくのが本来は良いんだろうなと思います。
ですが、サーバの運用の手間を考えると面倒だなと思って、AnsibleやDockerでのプロビジョニング中にビルドするようにしていました。

[fedora projectのcoprというサービス](https://copr.fedoraproject.org/coprs/)を使うと、自分でサーバを用意しなくても
自作rpmのビルドとホスティングが出来ることを知り、試してみました。

### 今回試したサンプル

githubのレポジトリは[hnakamur/nodejs-rpm](https://github.com/hnakamur/nodejs-rpm)にあります。Node.jsをビルドするrpmです。

specファイルは[kazuhisya/nodejs-rpm](https://github.com/kazuhisya/nodejs-rpm)のをほぼ流用しています。ありがとうございます！
一点変更したのはダウンロードするNode.jsのソースのtarballを `node-v*.tar.gz` ではなく `node-v*.tar.xz` にしています。

## coprについて

[copr](https://fedorahosted.org/copr/)に説明があります。FAQの[How is Copr pronounced?](https://fedorahosted.org/copr/wiki/UserDocs#HowisCoprpronounced)によると、銅(copper)と同じでカッパーと発音するそうです。

[How long do you keep the builds?](https://fedorahosted.org/copr/wiki/UserDocs#Howlongdoyoukeepthebuilds)によるとプロジェクトごとに最後に成功したビルドだけが保持されて、古いバージョンのビルドや失敗したビルドは14日後に削除されるそうです。

ですので、古いバージョンも残しておきたい場合は、coprは使えません。その場合は自前でレポジトリサーバを立てて運用するしかなさそうです。

### 参考: coprのウェブ管理画面にsrpmをアップロードしてrpmをビルドする手順
[ScreenshotsTutorial – copr](https://fedorahosted.org/copr/wiki/ScreenshotsTutorial)にcoprのウェブ管理画面からsrpmをアップロードしてrpmをビルドする手順がスクリーンショット満載で説明されています。


## 今回試したビルド手順の流れ

今回試したビルド手順の流れは以下の通りです。

1. githubのプロジェクトにspecファイルを置きます。
2. git pushしたときにTravis CIでdockerコンテナを動かしてsrpmを作ってcoprに投入します。
3. coprでrpmをビルドしてホスティングしてもらいます。

## 事前準備

### Fedora account 登録

まずは [Sign up for a Fedora account](https://admin.fedoraproject.org/accounts/user/new) からアカウント登録します。手順はメモしてなかったので省略します。

私のアカウントのログイン後の「アカウントの詳細」のページを見ると「あなたの役割」のところにSigned CLA GroupとSigners of the Fedora Project Contributor Agreementという項目があり、共にステータスが「承認されました」となっているので、これらの申請の手順が必要だったと思います。

承認されるまでしばらく時間がかかって、その間にrpmをビルドしてみたら署名されないことがありました。今ではプロジェクトごとに鍵が自動生成されてrpmが署名されるようになっています。

### Travis CIのプロジェクト作成

[Travis CI上にhnakamur/nodejs-rpmプロジェクト](https://travis-ci.org/hnakamur/nodejs-rpm)を作成して、githubのレポジトリ[hnakamur/nodejs-rpm](https://github.com/hnakamur/nodejs-rpm)に対応付けておきます。手順はメモしてなかったので省略します。

### Travis CIでdockerでコンテナを動かしてsrpmを作る

Travis CIでdockerを使う方法は [Using Docker in Builds - Travis CI](https://docs.travis-ci.com/user/docker/) で説明されています。

試行錯誤の結果、以下のような [.travis.yml]( https://github.com/hnakamur/nodejs-rpm/blob/0ed19cd5504fcb11875f12184bdb3ccd27caa6aa/.travis.yml )を作成しました。

```
sudo: required

services:
  - docker

branches:
  only:
    - master
    - LTS

install:
  - docker build -t hnakamur/nodejsrpm .

script:
  - case $TRAVIS_BRANCH in master) project=nodejs5;; LTS) project=nodejs;; esac
  - docker run hnakamur/nodejsrpm "$COPR_LOGIN" "$COPR_USERNAME" "$COPR_TOKEN" "$project"
```

[hnakamur/nodejs-rpm](https://github.com/hnakamur/nodejs-rpm)では、mainブランチでNode.jsのv5.x (Stable)、LTSブランチでNode.jsのv4.x (LTS)のspecファイルを保持しています。

coprは上記の通り1つのプロジェクトで複数バージョンは保持できないので、 [hnakamur/nodejs5 Copr](https://copr.fedoraproject.org/coprs/hnakamur/nodejs5/) と [hnakamur/nodejs Copr](https://copr.fedoraproject.org/coprs/hnakamur/nodejs/) の2つのプロジェクトを作ることにしました。

[Environment Variables - Travis CI](https://docs.travis-ci.com/user/environment-variables/#Default-Environment-Variables)によると `TRAVIS_BRANCH` 環境変数でgitのブランチが取得できます。ブランチ名に応じてプロジェクト名を切り替え、 `docker run` で呼び出すスクリプトの引数に渡しています。

COPR_LOGIN、COPR_USERNAME、COPR_TOKENの3つの環境変数ですが、Fedora accountにログインした状態で [API for Copr](https://copr.fedoraproject.org/api/)にアクセスし表示された値を使います。表示されているのはcoprのコマンドラインクライアント [copr-cli](https://pypi.python.org/pypi/copr-cli)用の設定ファイル `~/.config/copr` の内容です。

APIのアクセストークンなどは秘密にすべき情報なのでgithubのレポジトリ内のファイルには含めてはいけません。

そこでこれらの値は[Travis CI上のhnakamur/nodejs-rpmプロジェクト](https://travis-ci.org/hnakamur/nodejs-rpm)で[Defining Variables in Repository Settings](https://docs.travis-ci.com/user/environment-variables/#Defining-Variables-in-Repository-Settings)の手順に従って設定しておきます。

プロジェクトの管理画面の右上の[Settings]/[Settings]メニュー (このメニューはプロジェクトの管理者にのみ表示されます)を選んでCOPR_LOGIN、COPR_USERNAME、COPR_TOKENの3つの環境変数を追加します。COPR_LOGINとCOPR_TOKENの2つは[Display value in build log]を[ON]にしてログに出力しないようにしました。

docker runで実行されるスクリプトの内容は以下の通りです。

https://github.com/hnakamur/nodejs-rpm/blob/0ed19cd5504fcb11875f12184bdb3ccd27caa6aa/copr-build.sh

```
#!/bin/bash
set -e
copr_login=$1
copr_username=$2
copr_token=$3
project_name=$4

spec_file=/root/rpmbuild/SPECS/nodejs.spec

mkdir -p /root/.config
cat > /root/.config/copr <<EOF
[copr-cli]
login = ${copr_login}
username = ${copr_username}
token = ${copr_token}
copr_url = https://copr.fedoraproject.org
EOF

status=`curl -s -o /dev/null -w "%{http_code}" https://copr.fedoraproject.org/api/coprs/${copr_username}/${project_name}/detail/`
if [ $status = "404" ]; then
  copr-cli create --chroot epel-7-x86_64 --description 'node.js repository' ${project_name}
fi
version=`awk '$1=="Version:" {print $2}' ${spec_file}`
release=$(rpm --eval `awk '$1=="Release:" {print $2}' ${spec_file}`)
srpm_file=/root/rpmbuild/SRPMS/nodejs-${version}-${release}.src.rpm
copr-cli build --nowait ${project_name} ${srpm_file}

rm /root/.config/copr
```

まず、引数で渡された情報を元にcopr-cliの設定ファイル `/root/.config/copr` を生成します。
次にcoprのAPIでプロジェクトが作成済みかチェックし、作成されていなければ作成します。
その後、 `copr-cli build` でsrpmをcoprにアップロードしてビルドを開始します。

curlでhttpステータスだけを出力する方法は [Getting curl to output HTTP status code? - Super User](http://superuser.com/questions/272265/getting-curl-to-output-http-status-code/442395#442395) で知りました。ありがとうございます！

ビルド完了までTravis側で待つようにするのはムダだと思ったので `copr-cli build` には `--nowait` オプションを指定しました。代わりに [Fedora Notifications](https://apps.fedoraproject.org/notifications/)でメール通知を有効にして、ビルド終了時には `notifications@fedoraproject.org` からメールが届くようにして使っています。

### srpmのビルドとcopr-cliのインストール

話が前後しますが、srpmのビルドとcopr-cliのインストールは `docker build` で行っています。
[Dockerfile](https://github.com/hnakamur/nodejs-rpm/blob/0ed19cd5504fcb11875f12184bdb3ccd27caa6aa/Dockerfile)の内容は以下の通りです。

```
FROM centos:7
MAINTAINER Hiroaki Nakamura <hnakamur@gmail.com>

RUN yum -y install rpmdevtools rpm-build \
 && rpmdev-setuptree

RUN yum -y install epel-release \
 && yum -y install python-pip \
 && pip install copr-cli

ADD nodejs.spec /root/rpmbuild/SPECS/
ADD node-js.*patch /root/rpmbuild/SOURCES/

RUN version=`awk '$1=="Version:" {print $2}' /root/rpmbuild/SPECS/nodejs.spec` \
 && curl -sL -o /root/rpmbuild/SOURCES/node-v${version}.tar.xz https://nodejs.org/dist/v${version}/node-v${version}.tar.xz \
 && rpmbuild -bs /root/rpmbuild/SPECS/nodejs.spec

ADD copr-build.sh /root/
ENTRYPOINT ["/bin/bash", "/root/copr-build.sh"]
```

copr-cliはCentOS 7だとepelから `yum install` でインストール可能なのですが、バージョンが古いため `copr-cli build` でsrpmファイルのパスを指定してアップロードする機能が無いようです。サイトにアップロードしておいてURLを指定することは可能なのですが、それだと面倒なので `pip` を使って最新版の `copr-cli` をインストールしています。

長く運用するサーバならrpmでインストールされるパスと同じパスにpipでインストールしてしまうのは良くないかもしれませんが、ビルド終了したら破棄するコンテナなので気にせず上書きインストールとしています。

## rpmを使う手順

例えば[hnakamur/nodejs Copr](https://copr.fedoraproject.org/coprs/hnakamur/nodejs/)だと右の方の[Quick Enable]という欄に `dnf copr enable hnakamur/nodejs` というコマンドで有効にできるという説明があります。

その下のリンクをたどると[HowToEnableRepo – copr](https://fedorahosted.org/copr/wiki/HowToEnableRepo)に
yumの場合は `yum copr enable user/project` となるとあります。ただし、 `yum-plugin-copr` という `yum` のプラグインが必要です。

これはepelとかには無いようで、[alonid/yum-plugin-copr Copr](https://copr.fedoraproject.org/coprs/alonid/yum-plugin-copr/)にありました。が、これをインストールするにはこのプロジェクトを有効にする必要があるので面倒です。


コマンドを使わなくても[hnakamur/nodejs Copr](https://copr.fedoraproject.org/coprs/hnakamur/nodejs/)のActive Releasesセクションの表のRepo Downloadの列にある[Epel 7]というボタンを押すと以下のようにレポジトリの設定ファイルが表示されます。

https://copr.fedoraproject.org/coprs/hnakamur/nodejs/repo/epel-7/hnakamur-nodejs-epel-7.repo

```
[hnakamur-nodejs]
name=Copr repo for nodejs owned by hnakamur
baseurl=https://copr-be.cloud.fedoraproject.org/results/hnakamur/nodejs/epel-7-$basearch/
skip_if_unavailable=True
gpgcheck=1
gpgkey=https://copr-be.cloud.fedoraproject.org/results/hnakamur/nodejs/pubkey.gpg
enabled=1
enabled_metadata=1
```


なので、これを `/etc/yum.repos.d/hnakamur-nodejs-epel-7.repo` に保存して `yum install nodejs` でインストールすればOKです。

## まとめ

これでスペックファイルを書いてgithubにプッシュすれば、coprでrpmをビルドして公開されるようになり便利になりました。

ただし問題もあって、coprのビルドはときどき失敗してしまうようです。スペックファイルの中身を変えずにREADMEに無意味な空行を入れるなどして再度pushしてビルドを再実行すると成功したりしました。

## さらに気になっていること

[ScreenshotsTutorial – copr](https://fedorahosted.org/copr/wiki/ScreenshotsTutorial)の[New Build]タブのスクリーンショットには[From URLs]と[Upload SRPM]という2つのタブしかないですが、実際の画面ではそれに加えて [Git and Tito]、[Mock SCM]というタブがあります。

これらを使うとTravis CIを使わずにビルドできるかもしれないと期待しているのですが、使い方の説明を見つけられておらず使い方がわからない状態です。ということで一旦この記事を書きました。

## 2015-12-06 追記

rpmのビルドが通るまでの試行錯誤中は毎回coprでビルドするより手元の環境でビルドするほうが快適です。そのための手順を[mockコマンドでrpmをビルドする · hnakamur's blog at github](/blog/2015/12/05/build_rpm_with_mock/)に書きましたので、ご参照ください。
