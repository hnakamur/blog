Title: Mockやcoprでrpmをビルドする際にサードパーティのレポジトリを追加する方法
Date: 2015-12-18 01:43
Category: blog
Tags: copr, mock, rpmbuild
Slug: blog/2015/12/18/add_third_party_to_build_on_mock_and_copr

## はじめに
[Mock](https://fedoraproject.org/wiki/Mock)や[copr](https://copr.fedoraproject.org/)でrpmをビルドする際にCentOS標準のレポジトリ以外のサードパーティのレポジトリのrpmに依存したい場合があります。この記事ではサードパーティのレポジトリの追加方法を説明します。

この記事では[libvmod-header](https://www.varnish-cache.org/vmod/header-manipulation)をビルドするために[varnish-cache.orgのRedHat用インストール手順](https://www.varnish-cache.org/installation/redhat)で提供されているEL7用のレポジトリを追加する例で説明します。

ビルドするために私が作成したDockerfileとシェルスクリプトは[hnakamur/libvmod-header-rpm](https://github.com/hnakamur/libvmod-header-rpm)にあります。

## Mockでのrpmビルド時にサードパーティのレポジトリを追加する方法

[Building SCL packages with mock](https://lists.fedorahosted.org/pipermail/softwarecollections/2012-November/000018.html)で紹介されていた方法です。

CentOS 7用のrpmをビルドする場合 `/etc/mock/epel-7-x86_64.cfg` をコピーして `/etc/mock/epel-7-varnish-x86_64.cfg` のように別名で保存します。

`/etc/mock/epel-7-varnish-x86_64.cfg` の最後に `config_opts['yum.conf']` の設定があります。変更前は以下のようになっています。

```
config_opts['root'] = 'epel-7-x86_64'
config_opts['target_arch'] = 'x86_64'
config_opts['legal_host_arches'] = ('x86_64',)
config_opts['chroot_setup_cmd'] = 'install @buildsys-build'
config_opts['dist'] = 'el7'  # only useful for --resultdir variable subst
config_opts['releasever'] = '7'

config_opts['yum.conf'] = """
[main]
keepcache=1
debuglevel=2
reposdir=/dev/null
logfile=/var/log/yum.log
retries=20
obsoletes=1
gpgcheck=0
assumeyes=1
syslog_ident=mock
syslog_device=

# repos
[base]
name=BaseOS
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=os
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-CentOS-7
gpgcheck=1

[updates]
name=updates
enabled=1
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=updates
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-CentOS-7
gpgcheck=1

[epel]
name=epel
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=epel-7&arch=x86_64
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-EPEL-7
gpgcheck=1

[extras]
name=extras
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=extras
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-EPEL-7
gpgcheck=1

[testing]
name=epel-testing
enabled=0
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=testing-epel7&arch=x86_64
failovermethod=priority


[local]
name=local
baseurl=http://kojipkgs.fedoraproject.org/repos/epel7-build/latest/x86_64/
cost=2000
enabled=0

[epel-debug]
name=epel-debug
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=epel-debug-7&arch=x86_64
failovermethod=priority
enabled=0
"""
```

### 失敗例1
varnish-cache.orgではEL7用のレポジトリ定義が https://repo.varnish-cache.org/redhat/varnish-4.1.el7.rpm で配布されています。

`config_opts['chroot_setup_cmd'] = 'install @buildsys-build'` にこのrpmのURLを追加して
`config_opts['chroot_setup_cmd'] = 'install @buildsys-build https://repo.varnish-cache.org/redhat/varnish-4.1.el7.rpm'` にするというのを試してみましたが、これは失敗でした。

`sudo mock -r epel-7-varnish-x86_64 --init` で `varnish-4.1` というレポジトリのrpmがインストールされるところまではOKでした。
が、 `sudo mock -r epel-7-varnish-x86_64 --install varnish` としてvarnishをインストールすると、このレポジトリからvarnish 4.1.0がインストールされずにepelから4.0.3がインストールされてしまいました。

### うまくいく方法

ということでmockで作成するchroot環境では `config_opts['yum.conf']` に予めレポジトリ定義を書いておく必要があるようです。

https://repo.varnish-cache.org/redhat/varnish-4.1.el7.rpm に含まれる `etc/yum.repos.d/varnish-4.1.repo` には以下の様なレポジトリ定義が含まれています。

```
[varnish-4.1]
name=Varnish Cache 4.1 for Enterprise Linux
baseurl=https://repo.varnish-cache.org/redhat/varnish-4.1/el7/$basearch
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-VARNISH
```

`/etc/pki/rpm-gpg/RPM-GPG-KEY-VARNISH` というgpgkeyが折角用意されているので使いたいのですが良い方法が思いつきませんでした。 `config_opts['chroot_setup_cmd']` にセットアップ時に実行されるコマンドを書けるのですが、先頭に `yum` を追加して実行されるので任意のコマンドを実行できるわけではないです。

今回は諦めてgpgkeyを使うのは諦めて、下記の内容を `config_opts['yum.conf']` の最後に追加するようにしました。

```
[varnish-4.1]
name=Varnish Cache 4.1 for Enterprise Linux
baseurl=https://repo.varnish-cache.org/redhat/varnish-4.1/el7/$basearch
enabled=1
gpgcheck=0
```

スクリプトでは以下のようにしています。
https://github.com/hnakamur/libvmod-header-rpm/blob/5d5b2e580b11944ee630c6fbc2bea81b9fa7bb9a/scripts/build.sh#L47-L75

```
create_varnish_repo_file() {
  varnish_repo_file=varnish-4.1.repo
  if [ ! -f $varnish_repo_file ]; then
    # NOTE: Although https://repo.varnish-cache.org/redhat/varnish-4.1.el7.rpm at https://www.varnish-cache.org/installation/redhat
    #       has the gpgkey in it, I don't use it since I don't know how to add it to /etc/mock/*.cfg
    cat > ${varnish_repo_file} <<EOF
[${varnish_repo_id}]
name=${varnish_repo_name}
baseurl=${varnish_repo_baseurl}
enabled=1
gpgcheck=0
EOF
  fi
}

create_mock_chroot_cfg() {
  create_varnish_repo_file

  # Insert ${scl_repo_file} before closing """ of config_opts['yum.conf']
  # See: http://unix.stackexchange.com/a/193513/135274
  #
  # NOTE: Support of adding repository was added to mock,
  #       so you can use it in the future.
  # See: https://github.com/rpm-software-management/ci-dnf-stack/issues/30
  (cd ${topdir} \
    && echo | sed -e '$d;N;P;/\n"""$/i\
' -e '/\n"""$/r '${varnish_repo_file} -e '/\n"""$/a\
' -e D /etc/mock/${base_chroot}.cfg - | sudo sh -c "cat > /etc/mock/${mock_chroot}.cfg")
}
```

sedでパターンにマッチした行の後にファイルを挿入するのは `/パターン/r ファイル名`ですが、マッチした行の前に挿入するのはトリッキーです。
ここでは http://unix.stackexchange.com/a/193513/135274 で紹介されていた `echo | sed -e '$d;N;P;/\nPointer/r file1' -e D file2 -` という手法を使っています。
ただし、ファイルを挿入する前後に改行を入れたかったので `i` や `a` も使っています。

これで `sudo mock -r epel-7-varnish-x86_64 --rebuild ${SRPMのパス}` でrpmをビルドできます。

## coprでのrpmビルド時にサードパーティのレポジトリを追加する方法

[API for Copr](https://copr.fedoraproject.org/api/)の"Create new project"のAPIにreposパラメータがありますので、ここに `*.repo` ファイルの `baseurl` の値、 `https://repo.varnish-cache.org/redhat/varnish-4.1/el7/$basearch` を指定すればOKです。

実際のスクリプトでは以下の箇所です。
https://github.com/hnakamur/libvmod-header-rpm/blob/5d5b2e580b11944ee630c6fbc2bea81b9fa7bb9a/scripts/build.sh#L108-L119

```
    # Create the project on copr.
    # We call copr APIs with curl to work around the InsecurePlatformWarning problem
    # since system python in CentOS 7 is old.
    # I read the source code of https://pypi.python.org/pypi/copr/1.62.1
    # since the API document at https://copr.fedoraproject.org/api/ is old.
    curl -s -X POST -u "${COPR_LOGIN}:${COPR_TOKEN}" \
      --data-urlencode "name=${project_name}" \
      --data-urlencode "${base_chroot}=y" \
      --data-urlencode "repos=${varnish_repo_baseurl}" \
      --data-urlencode "description=$copr_project_description" \
      --data-urlencode "instructions=$copr_project_instructions" \
      https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/new/
```
