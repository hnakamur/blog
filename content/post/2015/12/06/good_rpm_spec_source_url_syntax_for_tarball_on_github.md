Title: rpmのspecファイルのSourceにGitHubの任意のコミットのtarballのURLを指定するときの良い書き方
Date: 2015-12-06 00:07
Category: blog
Tags: github, rpmbuild
Slug: blog/2015/12/06/good_rpm_spec_source_url_syntax_for_tarball_on_github

[Packaging:SourceURL - FedoraProject](https://fedoraproject.org/wiki/Packaging:SourceURL?rd=Packaging/SourceURL#Commit_Revision)で知ったtipsの紹介です。

GitHubでプロジェクトの[Download ZIP]ボタンを押すと、ソースをZIP形式でダウンロードできます。
コミット数が多いプロジェクトだと `git clone` するよりも高速に取得できるので履歴が不要な場合には便利な方法です。

例えば[openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module)なら `https://github.com/openresty/lua-nginx-module/archive/master.zip` というURLになるのですが、 `.zip` を `.tar.gz` に変えればtar.gz形式でダウンロードできます。

また、 `master` の部分はブランチ名、タグ名、コミットハッシュを指定することも出来るので任意のコミットのソースを取得可能です。

好みのファイル名でダウンロードするのは、通常ならダウンロードするツール側で対応すれば良い話です。例えば[curl(1): transfer URL - Linux man page](http://linux.die.net/man/1/curl)を使う場合は `-o` オプションで `-o ファイル名` のように指定すれば良いだけです。

ただ、RPMのspecファイルの `Source:` に指定するときはちょっと厄介です。
[SPEC file overview](https://fedoraproject.org/wiki/How_to_create_an_RPM_package#SPEC_file_overview)の `Source0` の説明を読むと、URLのベースネーム (最後のスラッシュの後の部分) が `~/rpmbuild/SOURCES` ディレクトリ配下に置くファイル名になるようにするべきとあります。

しかし、上述のようにGitHubでソースのtarballのURLのベースネームは `コミットハッシュなど.tar.gz` という形式となっています。これだと複数のソースをダウンロードした時に、どれがどれかわかりにくいですし、 `バージョン番号.tar.gz` の場合だとファイル名が衝突する恐れもあります。

解決策ですが、元のURLに `#/` をつけてその後に好きなファイル名を指定すればOKです。具体的には `https://github.com/ユーザ名/プロジェクト名/archive/コミットハッシュなど.tar.gz#/プロジェクト名-コミットハッシュなど.tar.gz` のように書きます。

[Packaging:SourceURL - FedoraProject](https://fedoraproject.org/wiki/Packaging:SourceURL?rd=Packaging/SourceURL#Commit_Revision)にはbitbucket.orgとgitlab.comの場合の書き方も紹介されていますので、必要に応じてご参照ください。
