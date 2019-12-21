+++
title="私のnginxのカスタムrpmとdebをビルドする手順"
date = "2018-04-05T08:30:00+09:00"
tags = ["nginx"]
categories = ["blog"]
+++


# はじめに

nginxのカスタムrpmとdebをビルドし始めてから結構経っていますが、自分のブログ記事に散らばっている
手順をピックアップしながら毎度ビルドしているのは良くないので、自分用にまとめておきます。
なおこの手順は私の手元の環境と自作コマンドに依存しているので、他の環境でコピペしても動きません。

以下ではバージョン1.13.11の例をメモします。

# 必要に応じてluajitのrpmをビルド

[Releases · openresty/luajit2](https://github.com/openresty/luajit2/releases) を見て新しいリリースが出ていたら
[hnakamur/luajit-rpm](https://github.com/hnakamur/luajit-rpm) を更新してluajitのrpmを
[hnakamur/luajit Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/luajit/) でビルドします。手順はこのnginxのrpmとほぼ同様なので省略します。

# tarballのダウンロード

```console
cd ~/nginx-deb-work
```

        curl -LO http://nginx.org/download/nginx-1.13.11.tar.gz

https://www.openssl.org/ を見てOpenSSLの新しいバージョンが出ていたらそれもダウンロード。

```console
curl -LO https://www.openssl.org/source/openssl-1.0.2o.tar.gz
```

# nginxのrpmをビルド

## srpmを作成

rpmビルドの作業用gitレポジトリで新しいバージョン用にトピックブランチ作成。

```console
cd ~/.ghq/github.com/hnakamur/nginx-rpm
g co -b 1_13_11
```

新しいtarballをSOURCESディレクトリに追加し、古いtarballはgitレポジトリから削除。

```console
cp ~/nginx-deb-work/nginx-1.13.11.tar.gz SOURCES/
g rm SOURCES/nginx-1.13.10.tar.gz
```

OpenSSLを更新する場合、新しいtarballをSOURCESディレクトリに追加し、古いtarballはgitレポジトリから削除。

```console
cp ~/nginx-deb-work/openssl-1.0.2o.tar.gz SOURCES/
g rm SOURCES/openssl-1.0.2n.tar.gz
```

サードバーティモジュールのソースをダウンロード。

```console
./download-module-sources.sh
```

上記のスクリプトから出力される各モジュールのコミットハッシュをコピー。

```text
%define echo_nginx_module_commit c65f5c638d0501b482fbc3ebbda9a49648022d40
%define headers_more_nginx_module_commit a9f7c7e86cc7441d04e2f11f01c2e3a9c4b0301d
%define lua_nginx_module_commit 91a0ad236c9661f38b78cdc99e05025f7ce5cccb
%define lua_upstream_nginx_module_commit 6ebcda3c1ee56a73ba73f3a36f5faa7821657115
%define memc_nginx_module_commit 66de925b7da5931badf24c7e675e2ee62c697069
%define redis2_nginx_module_commit 4b7ff9bdf669d487efd32ac3d06d3ee981f5a2f6
%define set_misc_nginx_module_commit 77ae35bfb00e81196d8dbae48c359e1d591a8d01
%define srcache_nginx_module_commit 53a98806b0a24cc736d11003662e8b769c3e7eb3
%define lua_resty_core_commit 6ea0dea70647a54c68ca02be47c3deb83b15a6ad
%define stream_lua_nginx_module_commit a9e856564ccae54a43f27d909ce9af80064f5688
%define ngx_cache_purge_commit 331fe43e8d9a3d1fa5e0c9fec7d3201d431a9177
%define nginx_rtmp_module_commit 791b6136f02bc9613daf178723ac09f4df5a3bbf
%define nginx_dav_ext_module_commit 430fd774fe838a04f1a5defbf1dd571d42300cf9
%define ngx_http_enhanced_memcached_module_commit a9b76b6c9e0623e3ee84fecb04284dc8c91dfdb4
%define ngx_http_secure_download_commit f379a1acf2a76f63431a12fa483d9e22e718400b
%define ngx_devel_kit_commit a22dade76c838e5f377d58d007f65d35b5ce1df3
%define nginx_sorted_querystring_module_commit e5bbded07fd67e2977edc2bc145c45a7b3fc4d26
%define ngx_http_pipelog_module_commit 2503d5ef853ff2542ee7e08d898a85a7747812e5
```

rpmのスペックファイルを更新。

```console
vi SPECS/nginx.spec
```

* 上記のモジュールのコミットハッシュを更新。
* OpenSSLのバージョンを更新する場合は `%define ngx_openssl_version 1.0.2o` の値を更新。
* nginxのバージョンの行 `Version: 1.13.11` を更新。
* `%changelog` の先頭に以下のようにエントリを追加。モジュールのバージョンリストは上記の出力をコピペした後 `:'<,'>s/%define \(.*\)_commit/- \1/` で置換。

```text
%changelog
* Mon Apr  5 2018 Hiroaki Nakamura <hnakamur@gmail.com> - 1.13.11-1
- 1.13.11
- echo_nginx_module c65f5c638d0501b482fbc3ebbda9a49648022d40
- headers_more_nginx_module a9f7c7e86cc7441d04e2f11f01c2e3a9c4b0301d
- lua_nginx_module 91a0ad236c9661f38b78cdc99e05025f7ce5cccb
- lua_upstream_nginx_module 6ebcda3c1ee56a73ba73f3a36f5faa7821657115
- memc_nginx_module 66de925b7da5931badf24c7e675e2ee62c697069
- redis2_nginx_module 4b7ff9bdf669d487efd32ac3d06d3ee981f5a2f6
- set_misc_nginx_module 77ae35bfb00e81196d8dbae48c359e1d591a8d01
- srcache_nginx_module 53a98806b0a24cc736d11003662e8b769c3e7eb3
- lua_resty_core 6ea0dea70647a54c68ca02be47c3deb83b15a6ad
- stream_lua_nginx_module a9e856564ccae54a43f27d909ce9af80064f5688
- ngx_cache_purge 331fe43e8d9a3d1fa5e0c9fec7d3201d431a9177
- nginx_rtmp_module 791b6136f02bc9613daf178723ac09f4df5a3bbf
- nginx_dav_ext_module 430fd774fe838a04f1a5defbf1dd571d42300cf9
- ngx_http_enhanced_memcached_module a9b76b6c9e0623e3ee84fecb04284dc8c91dfdb4
- ngx_http_secure_download f379a1acf2a76f63431a12fa483d9e22e718400b
- ngx_devel_kit a22dade76c838e5f377d58d007f65d35b5ce1df3
- nginx_sorted_querystring_module e5bbded07fd67e2977edc2bc145c45a7b3fc4d26
- ngx_http_pipelog_module 2503d5ef853ff2542ee7e08d898a85a7747812e5
```

rpmビルドの作業用gitレポジトリに変更内容をコミット。

```console
g a .
g ci -m 'Update nginx to 1.13.11 and also update modules'
```

srpmを作成。

```console
mkdir ~/rpmbuild/SOURCES/nginx-1.13.10-1.ngx
ln -s $PWD/SOURCES/* !$
rpmbuild -bs SPECS/nginx.spec
```

ここで以下のように `warning: bogus date in %changelog` と出た場合は日付と曜日が不一致なので修正して
`g ci --amend -m 'Update nginx to 1.13.11 and also update modules' .` でコミットした後やり直す。

```console
hnakamur@express:~/.ghq/github.com/hnakamur/nginx-rpm$ rpmbuild -bs SPECS/nginx.spec
warning: bogus date in %changelog: Mon Apr  5 2018 Hiroaki Nakamura <hnakamur@gmail.com> - 1.13.11-1
Wrote: /home/hnakamur/rpmbuild/SRPMS/nginx-1.13.11-1.ngx.src.rpm
```

## mockコマンドを使ってローカルでビルド

mockコマンドを使ってローカルでビルド。

```console
/usr/bin/mock -r epel-7-x86_64-with-luajit --resultdir=~hnakamur/mockresult-nginx-1.13.11-1 --rebuild ~/rpmbuild/SRPMS/nginx-1.13.11-1.ngx.src.rpm
```

うまくビルドできたときは `~/mockresult-nginx-1.13.11-1/` 以下に生成された `*.rpm` をCentOS7の環境にコピーして `yum install -y nginx*.x86_64.rpm` でインストールして動作確認します。
ビルド失敗した場合はこのディレクトリの `build.log` を見てエラーの内容を確認します。

```console
hnakamur@express:~/.ghq/github.com/hnakamur/nginx-rpm$ ls -lt ~/mockresult-nginx-1.13.11-1/
total 20748
-rw-rw-r-- 1 hnakamur hnakamur  116664 Apr  5 09:05 root.log
-rw-rw-r-- 1 hnakamur hnakamur    1610 Apr  5 09:05 state.log
-rw-rw-r-- 1 hnakamur hnakamur 1643094 Apr  5 09:05 build.log
-rw-rw-r-- 1 hnakamur mock     4617220 Apr  5 09:05 nginx-debuginfo-1.13.11-1.el7.centos.ngx.x86_64.rpm
-rw-rw-r-- 1 hnakamur mock     3681552 Apr  5 09:05 nginx-1.13.11-1.el7.centos.ngx.x86_64.rpm
-rw-rw-r-- 1 hnakamur mock       14935 Apr  5 08:59 installed_pkgs
-rw-rw-r-- 1 hnakamur mock     8356143 Apr  5 08:58 nginx-1.13.11-1.el7.centos.ngx.src.rpm
-rw-rw-r-- 1 root     root     2793745 Apr  5 08:58 available_pkgs
```

## coprでビルド

```console
copr-cli build hnakamur/nginx ~/mockresult-nginx-1.13.11-1/nginx-1.13.11-1.el7.centos.ngx.src.rpm
```

ビルドが完了したら
[hnakamur/nginx Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/nginx/) のレポジトリを追加しているテスト環境にてnginxを更新して動作確認します。

## rpmのgitレポジトリの更新とリリース作成

今回のトピックブランチをgithubにプッシュ。

```console
g push origin 1_13_11
```

[hnakamur/nginx-rpm](https://github.com/hnakamur/nginx-rpm) でプルリクエストを作成してマージ。

ローカルのmasterブランチを更新してトピックブランチを削除。

```console
g f
g co master
g me origin/master --ff
g delete-merged-branches
```

タグを作成してプッシュ。

```console
g tag 1.13.11-1
g push origin !$
```

coprでビルドされたrpmをダウンロードし、githubレポジトリにリリースを作成してアップロード。

```console
copr-files-downloader -user hnakamur -repo nginx -dest ./tmp
cd ./tmp
github-release release --user hnakamur --repo nginx-rpm --tag 1.13.11-1
for i in $(ls); do github-release upload --user hnakamur --repo nginx-rpm --tag 1.13.11-1 --name $i --file $i; done
cd ..
rm -r ./tmp
```

# nginxのdebをビルド

## debのソースパッケージ作成

debビルドの作業用gitレポジトリで新しいtarballを取り込む。 `gbp import-orig` の `--pristine-tar` オプションを忘れないこと。これを忘れると後でソースパッケージをビルドする時にoriginのtarballがgitレポジトリから再構築され、後ほどPPAでビルドする時になってoriginのtarballが既に他のレポジトリでアップロードされていると同じファイル名で中身が一致しなくてエラーになってしまう。ただしこのnginxのパッケージの場合はサードパーティのモジュールを追加したものがoriginのtarballなので他でアップロードされていることはないので実はたぶん問題ない。が、他のパッケージで実際にハマったので、結論としては `--pristine-tar` 重要。

```console
cd ~/.ghq/github.com/hnakamur/nginx-deb
gbp import-orig --pristine-tar -u 1.13.11 ~/nginx-deb-work/nginx-1.13.11.tar.gz
```

サードバーティモジュールのソースをダウンロード。

```console
g co upstream
../download-module-sources.sh
```

上記のスクリプトの出力をコピーしておきます。

```text
openresty/echo-nginx-module c65f5c638d0501b482fbc3ebbda9a49648022d40
openresty/headers-more-nginx-module a9f7c7e86cc7441d04e2f11f01c2e3a9c4b0301d
openresty/lua-nginx-module 91a0ad236c9661f38b78cdc99e05025f7ce5cccb
openresty/lua-upstream-nginx-module 6ebcda3c1ee56a73ba73f3a36f5faa7821657115
openresty/memc-nginx-module 66de925b7da5931badf24c7e675e2ee62c697069
openresty/redis2-nginx-module 4b7ff9bdf669d487efd32ac3d06d3ee981f5a2f6
openresty/set-misc-nginx-module 77ae35bfb00e81196d8dbae48c359e1d591a8d01
openresty/srcache-nginx-module 53a98806b0a24cc736d11003662e8b769c3e7eb3
openresty/lua-resty-core 6ea0dea70647a54c68ca02be47c3deb83b15a6ad
openresty/stream-lua-nginx-module a9e856564ccae54a43f27d909ce9af80064f5688
FRiCKLE/ngx_cache_purge 331fe43e8d9a3d1fa5e0c9fec7d3201d431a9177
arut/nginx-rtmp-module 791b6136f02bc9613daf178723ac09f4df5a3bbf
arut/nginx-dav-ext-module 430fd774fe838a04f1a5defbf1dd571d42300cf9
bpaquet/ngx_http_enhanced_memcached_module a9b76b6c9e0623e3ee84fecb04284dc8c91dfdb4
replay/ngx_http_secure_download f379a1acf2a76f63431a12fa483d9e22e718400b
simplresty/ngx_devel_kit a22dade76c838e5f377d58d007f65d35b5ce1df3
wandenberg/nginx-sorted-querystring-module e5bbded07fd67e2977edc2bc145c45a7b3fc4d26
pandax381/ngx_http_pipelog_module 2503d5ef853ff2542ee7e08d898a85a7747812e5
```

upstreamモジュールにサードパーティのモジュールのソースを追加しコミットします。

```console
g a .
g ci
```

コミットメッセージは以下のようにします。モジュールのコミットハッシュをペーストする前にvimで `:paste` を実行しておきます。

```text
Add module sources

openresty/echo-nginx-module c65f5c638d0501b482fbc3ebbda9a49648022d40
openresty/headers-more-nginx-module a9f7c7e86cc7441d04e2f11f01c2e3a9c4b0301d
openresty/lua-nginx-module 91a0ad236c9661f38b78cdc99e05025f7ce5cccb
openresty/lua-upstream-nginx-module 6ebcda3c1ee56a73ba73f3a36f5faa7821657115
openresty/memc-nginx-module 66de925b7da5931badf24c7e675e2ee62c697069
openresty/redis2-nginx-module 4b7ff9bdf669d487efd32ac3d06d3ee981f5a2f6
openresty/set-misc-nginx-module 77ae35bfb00e81196d8dbae48c359e1d591a8d01
openresty/srcache-nginx-module 53a98806b0a24cc736d11003662e8b769c3e7eb3
openresty/lua-resty-core 6ea0dea70647a54c68ca02be47c3deb83b15a6ad
openresty/stream-lua-nginx-module a9e856564ccae54a43f27d909ce9af80064f5688
FRiCKLE/ngx_cache_purge 331fe43e8d9a3d1fa5e0c9fec7d3201d431a9177
arut/nginx-rtmp-module 791b6136f02bc9613daf178723ac09f4df5a3bbf
arut/nginx-dav-ext-module 430fd774fe838a04f1a5defbf1dd571d42300cf9
bpaquet/ngx_http_enhanced_memcached_module a9b76b6c9e0623e3ee84fecb04284dc8c91dfdb4
replay/ngx_http_secure_download f379a1acf2a76f63431a12fa483d9e22e718400b
simplresty/ngx_devel_kit a22dade76c838e5f377d58d007f65d35b5ce1df3
wandenberg/nginx-sorted-querystring-module e5bbded07fd67e2977edc2bc145c45a7b3fc4d26
pandax381/ngx_http_pipelog_module 2503d5ef853ff2542ee7e08d898a85a7747812e5
```

upstreamブランチにタグを打ちます。

```console
g tag upstream/1.13.11+mod.1
```

masterブランチに切り替えてupstreamブランチの内容をマージします。

```console
g co master
g pull --no-edit . upstream
```

`debian/patches/*` のパッチがnginxの新しいバージョンでも問題なく当たるか確認します。
パッチがうまく当たらないときはパッチを適宜調整します。

```console
gbp pq rebase
gbp pq export
```

実行例。

```console
hnakamur@express:~/.ghq/github.com/hnakamur/nginx-deb$ gbp pq rebase
gbp:info: Switching to 'patch-queue/master'
First, rewinding head to replay your work on top of it...
Applying: Make replay/ngx_http_secure_download as dynamic module as well
Applying: Convert a config file to build a dynamic module
Applying: Fix compatibility with nginx-1.11.6+
Applying: feat(purge all): Include option to purge all the cached files
Applying: feat(partial keys): Support partial keys to purge multiple keys.
Applying: added cache_purge_response_type directive, selecting a response type (html|json|xml|text)
Applying: SSL: handled SSL_CTX_set_cert_cb() callback yielding.
hnakamur@express:~/.ghq/github.com/hnakamur/nginx-deb$ gbp pq export
gbp:info: On 'patch-queue/master', switching to 'master'
gbp:info: Generating patches from git (master..patch-queue/master)
On branch master
nothing to commit, working tree clean
```

`debian/changelog` の先頭にエントリを追加します。
以下のコマンドを実行すると前バージョンのタグ以降のコミットのコミットメッセージを並べて自動的にコミットメッセージを入力した状態で `debian/changelog` を開いてくれます。

```console
gbp dch -R
```

前バージョンのタグをうまく見つけられなかったときは以下のようなエラーになります。

```console
hnakamur@express:~/.ghq/github.com/hnakamur/nginx-deb$ gbp dch -R
gbp:error: Version 1.13.10+mod.1-1ubuntu1ppa1~ubuntu16.04.1 not found
```

この場合は `--since` オプションで前バージョンのタグを指定して実行します。

```console
gbp dch -R --since=debian/1.13.10+mod.1-1ubuntu1ppa1-ubuntu16.04.1
```

今回の例では `debian/changelog` の先頭に以下のようにエントリが追加された状態で vim で開かれました。

```text
nginx (1.13.11-1) xenial; urgency=medium

  * Imported Upstream version 1.13.11
  * Add module sources

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Thu, 05 Apr 2018 09:20:05 +0900
```

これを以下のように変更します。

```text
nginx (1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1) xenial; urgency=medium

  * Imported Upstream version 1.13.11
  * Add module sources
  * openresty/echo-nginx-module c65f5c638d0501b482fbc3ebbda9a49648022d40
  * openresty/headers-more-nginx-module a9f7c7e86cc7441d04e2f11f01c2e3a9c4b0301d
  * openresty/lua-nginx-module 91a0ad236c9661f38b78cdc99e05025f7ce5cccb
  * openresty/lua-upstream-nginx-module 6ebcda3c1ee56a73ba73f3a36f5faa7821657115
  * openresty/memc-nginx-module 66de925b7da5931badf24c7e675e2ee62c697069
  * openresty/redis2-nginx-module 4b7ff9bdf669d487efd32ac3d06d3ee981f5a2f6
  * openresty/set-misc-nginx-module 77ae35bfb00e81196d8dbae48c359e1d591a8d01
  * openresty/srcache-nginx-module 53a98806b0a24cc736d11003662e8b769c3e7eb3
  * openresty/lua-resty-core 6ea0dea70647a54c68ca02be47c3deb83b15a6ad
  * openresty/stream-lua-nginx-module a9e856564ccae54a43f27d909ce9af80064f5688
  * FRiCKLE/ngx_cache_purge 331fe43e8d9a3d1fa5e0c9fec7d3201d431a9177
  * arut/nginx-rtmp-module 791b6136f02bc9613daf178723ac09f4df5a3bbf
  * arut/nginx-dav-ext-module 430fd774fe838a04f1a5defbf1dd571d42300cf9
  * bpaquet/ngx_http_enhanced_memcached_module a9b76b6c9e0623e3ee84fecb04284dc8c91dfdb4
  * replay/ngx_http_secure_download f379a1acf2a76f63431a12fa483d9e22e718400b
  * simplresty/ngx_devel_kit a22dade76c838e5f377d58d007f65d35b5ce1df3
  * wandenberg/nginx-sorted-querystring-module e5bbded07fd67e2977edc2bc145c45a7b3fc4d26
  * pandax381/ngx_http_pipelog_module 2503d5ef853ff2542ee7e08d898a85a7747812e5

 -- Hiroaki Nakamura <hnakamur@gmail.com>  Thu, 05 Apr 2018 09:20:05 +0900
```

`debian/changelog` の変更をコミットしてタグを打ちます。

```console
g ci . -m 'Release 1.13.11.mod.1-1ubuntu1ppa1~ubuntu16.04.1'
g tag debian/1.13.11+mod.1-1ubuntu1ppa1-ubuntu16.04.1
```

## pbuilderを使ってローカルでdebパッケージをビルド

debのソースパッケージをビルドします。

```console
gbp buildpackage --git-export-dir=../build-area -p/home/hnakamur/bin/gpg-passphrase -S -sa
```

`pbuilder` を使ってdebパッケージをビルドします。

```console
sudo pbuilder build ../build-area/nginx_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1.dsc
```

無事にビルドが終わったら `/var/cache/pbuilder/result/nginx*1.13.11*` にdebパッケージが作られます。

```console
hnakamur@express:~/.ghq/github.com/hnakamur/nginx-deb$ ls -lt /var/cache/pbuilder/result/nginx*1.13.11*
-rw-r--r-- 1 hnakamur hnakamur     3639 Apr  5 09:36 /var/cache/pbuilder/result/nginx_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.changes
-rw-r--r-- 1 hnakamur hnakamur 13551210 Apr  5 09:36 /var/cache/pbuilder/result/nginx-dbg_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.deb
-rw-r--r-- 1 hnakamur hnakamur  1215456 Apr  5 09:36 /var/cache/pbuilder/result/nginx_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1_amd64.deb
-rw-r--r-- 1 hnakamur hnakamur     1185 Apr  5 09:32 /var/cache/pbuilder/result/nginx_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1.dsc
-rw-r--r-- 1 hnakamur hnakamur   120532 Apr  5 09:32 /var/cache/pbuilder/result/nginx_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1.debian.tar.xz
-rw-r--r-- 1 hnakamur hnakamur  2913781 Apr  5 09:28 /var/cache/pbuilder/result/nginx_1.13.11+mod.1.orig.tar.gz
```

作られたdebパッケージをfreightのローカルdebレポジトリに追加します。

```console
pushd /var/www/html/my-debs
sudo freight add /var/cache/pbuilder/result/nginx*1.13.11*.deb apt/xenial
sudo freight cache -p /home/hnakamur/.gpg-passphrase apt/xenial
popd
```

テスト用のUbuntu環境にてfreightのdebレポジトリからnginxを更新します。

```console
sudo apt update
sudo apt upgrade -y nginx
```

## PPAでdebパッケージをビルド

動作確認して問題なければPPAでdebパッケージをビルドします。

```console
dput ppa:hnakamur/nginx ../build-area/nginx_1.13.11+mod.1-1ubuntu1ppa1~ubuntu16.04.1_source.changes
```

[Packages in “nginx with thirdparty modules” : nginx with thirdparty modules : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/nginx/+packages) でこのバージョンのBuild Statusの列が緑のチェックマークになるまで待ちます（時計や緑の歯車のときはまだです）。

無事ビルドが完了したら [nginx with thirdparty modules : Hiroaki Nakamura](https://launchpad.net/~hnakamur/+archive/ubuntu/nginx) のレポジトリを追加してあるテスト環境にてnginxを更新して動作確認します。

```console
sudo apt update
sudo apt upgrade -y nginx
```

## debのgitレポジトリの更新とリリース作成

ローカルのgitレポジトリでの変更をgithubに反映します。

一旦以下のコマンドでプッシュを試みます。

```console
g push origin --all
```

`patch-queue` ブランチがconflictする場合は、乱暴ですが `-f` つきで再度プッシュします。まあ、 `patch-queue` は一時的な作業用ブランチなのとこのgitレポジトリはチームではなく一人作業用なのでよしということで。

```console
g push origin --all -f
```

タグもプッシュします。

```console
g push origin --tags
```

PPAでビルドされたrpmをダウンロードし、githubレポジトリにリリースを作成してアップロード。

```console
ppa-files-downloader -user hnakamur -repo nginx -pkg nginx -dest ./tmp
cd ./tmp
github-release release --user hnakamur --repo nginx-deb --tag debian/1.13.11+mod.1-1ubuntu1ppa1-ubuntu16.04.1
for i in $(ls); do github-release upload --user hnakamur --repo nginx-deb --tag debian/1.13.11+mod.1-1ubuntu1ppa1-ubuntu16.04.1 --name $i --file $i; done
cd ..
rm -r ./tmp
