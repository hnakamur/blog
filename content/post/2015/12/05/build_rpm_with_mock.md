Title: mockコマンドでrpmをビルドする
Date: 2015-12-05 22:10
Category: blog
Tags: centos
Slug: blog/2015/12/05/build_rpm_with_mock

## 2015-12-15 追記

[nginxのカスタムrpmをmockでビルドできることを確認してからcoprでビルド・配布する環境を作りました · hnakamur's blog at github](/blog/2015/12/15/using_mock_and_copr_to_build_nginx_rpm_on_docker/)という記事を書きましたのでそちらもご参照ください。

## 以下元記事です

[Travis CIとcopr.fedoraproject.orgを使ってrpmをビルド・配布するのを試してみた · hnakamur's blog at github](/blog/2015/11/26/use_travis_and_copr_to_build_and_host_rpm/)でrpmを外部のサーバでビルドできるようになりましたが、試行錯誤中はこの手順だと時間がかかりますので、手元の環境でビルドしたいところです。

## rpmbuild

私は最近までrpmbuildでrpmをビルドしていました。以下のコマンドでspecファイルの `BuildRequires` に書いたrpmをまとめてインストールすることが出来ることも最近知りました。

```
sudo yum-builddep -y specファイルのパス
```

これだけでも十分便利ですが、1つの環境でいろんなrpmをビルドするような使い方をしていると不満が出てきます。ビルドに必要なパッケージを `BuildRequires` に書き忘れていても、別のrpmのビルドの際にインストールされていてビルドが通ってしまい気づかない恐れがあるからです。

## mock

[Mock - FedoraProject](https://fedoraproject.org/wiki/Mock)を使えば、chrootでクリーンな環境でrpmをビルドしてくれるので、上記のように `BuildRequires` に必要なパッケージを書き忘れた場合はビルドエラーになり間違いに気づくことができます。

また、実行環境と異なるCPUアーキテクチャやRHELのバージョン用のrpmもビルドできます。 [mock(1): build SRPMs in chroot - Linux man page](http://linux.die.net/man/1/mock)によると `-r` オプションで `/etc/mock/<chroot>.cfg` の `<chroot>` の部分を指定すればよいそうです。

CentOS 7で `/etc/mock` を見てみたところ、以下のような環境が用意されていました。

```
[vagrant@localhost ~]$ ls /etc/mock/
default.cfg            fedora-21-armhfp.cfg   fedora-22-i386.cfg     fedora-23-ppc64.cfg         fedora-rawhide-ppc64le.cfg
epel-5-i386.cfg        fedora-21-i386.cfg     fedora-22-ppc64.cfg    fedora-23-ppc64le.cfg       fedora-rawhide-s390.cfg
epel-5-ppc.cfg         fedora-21-ppc64.cfg    fedora-22-ppc64le.cfg  fedora-23-s390.cfg          fedora-rawhide-s390x.cfg
epel-5-x86_64.cfg      fedora-21-ppc64le.cfg  fedora-22-s390.cfg     fedora-23-s390x.cfg         fedora-rawhide-sparc.cfg
epel-6-i386.cfg        fedora-21-s390.cfg     fedora-22-s390x.cfg    fedora-23-x86_64.cfg        fedora-rawhide-x86_64.cfg
epel-6-ppc64.cfg       fedora-21-s390x.cfg    fedora-22-x86_64.cfg   fedora-rawhide-aarch64.cfg  logging.ini
epel-6-x86_64.cfg      fedora-21-x86_64.cfg   fedora-23-aarch64.cfg  fedora-rawhide-armhfp.cfg   site-defaults.cfg
epel-7-x86_64.cfg      fedora-22-aarch64.cfg  fedora-23-armhfp.cfg   fedora-rawhide-i386.cfg
fedora-21-aarch64.cfg  fedora-22-armhfp.cfg   fedora-23-i386.cfg     fedora-rawhide-ppc64.cfg
```

[Caching in mock 0.8.x and later](https://fedoraproject.org/wiki/Using_Mock_to_test_package_builds#Caching_in_mock_0.8.x_and_later)を見るとmockの今のバージョンでは `mock` を実行してchroot環境を作ってyumでダウンロードしたrpmはホスト環境にキャッシュされるそうです。

ですので、複数のrpmをビルドしたり、同じrpmを試行錯誤で何度もビルドする場合に、キャッシュによる高速化が期待できます。

まとめると、mockの利点は以下の2つです。

* chrootによりクリーンな環境でビルドできるのでspecファイルの間違いに気づきやすい
* yumのキャッシュがあるのでビルドの際の `yum install` が高速化される

### coprもmockを使用しています

[copr](https://copr.fedoraproject.org/)でビルドした結果のmockchaing.log.gzを見ると、以下の様な行がありました。

```
[2015-12-05 11:13:20,751][  INFO][PID:19554] executing: /usr/bin/mockchain -r epel-7-x86_64 -l /var/tmp/mockremote-ZTm5H/build/ -a https://copr-be.cloud.fedoraproject.org/results/hnakamur/nginx/epel-7-x86_64 -a https://copr-be.cloud.fedoraproject.org/results/hnakamur/nginx/epel-7-x86_64/devel -m '--define=copr_username hnakamur' -m '--define=copr_projectname nginx' -m '--define=vendor Fedora Project COPR (hnakamur/nginx)' /tmp/build_package_repo/nginx/nginx-1.9.7-1.el7.ngx.src.rpm
```

[mockchain(1): chain package builder - Linux man page](http://linux.die.net/man/1/mockchain)によると複数のrpmを一括ビルドするためのコマンドだそうです。

### mockを使うためのセットアップ

epelを入れればmockはyumでインストール可能です。他にもsrpmを作るためにrpm-buildなどもyumでインストールする必要があるので、Vagrant用とDocker用にそれぞれセットアップ手順をまとめたものを作りました。

* [hnakamur/centos-mock-vagrant](https://github.com/hnakamur/centos-mock-vagrant)
* [hnakamur/centos-mock-docker](https://github.com/hnakamur/centos-mock-docker)

Vagrant環境のほうは単に `vagrant up` で起動して `vagrant ssh` でログインし、 `sudo su - mockbuild` で `mockbuild` ユーザになって作業します。

Docker環境でmockを利用する場合、mockがunshareシステムコールを呼ぶので `SYS_ADMIN` ケーパビリティが必要になります。そこで `docker run` の際に `--cap-add=SYS_ADMIN` オプションが必要です。

`docker build -t mock .` で `mock` という名前でdockerイメージをビルドした場合、
`docker run --cap-add=SYS_ADMIN -it mock` でbashプロンプトが起動しますので、 `su - mockbuild` で `mockbuild` ユーザになって作業します。

mockのyumキャッシュを有効活用するには、複数のビルド間に環境を破棄せずに維持したほうが良いです。dockerのほうはbashを抜けると環境が消えてしまうので、もう少しDockerfileを工夫したようが良さそうです。

とりあえず私はVagrantの環境の方を使っています。

### mockでのビルド

まずsrpmファイルを作ります。
上記の環境ですと、`mockbuild` ユーザの `/home/mockbuild/rpmbuild/` の下に `SPECS` や `SOURCES` ディレクトリが作ってありますので、そこにspecファイルやソースを置いて以下のコマンドを実行して作成します。

```
rpmbuild -bs specファイルのパス
```

上記の環境では `/home/mockbuild/rpmbuild/SRPMS/` にsrpmファイルが生成されます。
その後、以下のようにmockコマンドを実行してビルドします。

```
mock --rebuild srpmファイルのパス
```

ビルドで生成されたrpmとsrpmファイルは `/var/lib/mock/<chroot>/result/` に置かれます。
また、ビルドの作業ディレクトリは `/var/lib/mock/<chroot>/root/builddir/build/` 以下に `BUILD`, `BUILDROOT`, `RPMS`, `SOURCES`, `SPECS`, `SRPMS` ディレクトリが作成されていますので、ビルドが失敗した場合はこの中を見て調査できます。

## おわりに

実は[Mock - FedoraProject](https://fedoraproject.org/wiki/Mock)や[Project List](https://copr.fedoraproject.org/)はしばらく前に存在を知っていたのですが、ググっても情報が少ないしよくわからないのでスルーしていました。今回ついに使ってみたのですが、非常に便利なツールとサービスだということがわかりました。もっと前から使っておけばよかったです。

みなさんも[Mock - FedoraProject](https://fedoraproject.org/wiki/Mock)と[Project List](https://copr.fedoraproject.org/)を活用して、快適なrpmビルド・配布環境を手に入れましょう！
