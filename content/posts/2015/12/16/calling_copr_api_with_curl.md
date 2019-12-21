+++
Categories = []
Description = ""
Tags = ["copr"]
date = "2015-12-16T00:06:39+09:00"
title = "coprのAPIをcurlで呼び出す"

+++
## はじめに
[copr](https://fedorahosted.org/copr/)を利用するには以下の3つの手段があります。

* ウェブ管理画面を使う
  * [スクリーンショットつきのチュートリアル](https://fedorahosted.org/copr/wiki/ScreenshotsTutorial)
* [copr-cli](https://apps.fedoraproject.org/packages/copr-cli)というコマンドラインツールを使う
  * 内部的に下記の[API for Copr](https://copr.fedoraproject.org/api/)を呼び出しています
* [API for Copr](https://copr.fedoraproject.org/api/)を使う

## copr-cliを使わずにcurlでAPIを呼ぶ理由

折角copr-cliというコマンドラインツールが用意されているのでそれを活用すれば良いのですが、以下のような問題に遭遇したのでAPIをcurlで呼ぶようにしてみました。

* CentOS 7でyumでインストールできるcopr-cliはバージョンが古くてsrpmのアップロード機能が未サポート
* CentOS 7のPythonが古いのでInsecurePlatformWarningが出てしまう

### CentOS 7でyumでインストールできるcopr-cliはバージョンが古くてsrpmのアップロード機能が未サポート

正確にはcopr-cliが利用している[python-copr](https://apps.fedoraproject.org/packages/python-copr/)のバージョンの問題です。
[python-coprのChangelog](https://apps.fedoraproject.org/packages/python-copr/changelog)を見ると1.58-1でsrpmをアップロードする機能が追加されています。

一方、CentOS 7のepelにあるpython-coprは1.57-1です。srpmをアップロードする機能を使わないとなると、インターネット上にsrpmを置いてURLを指定する必要があり面倒です。

### CentOS 7のPythonが古いのでInsecurePlatformWarningが出てしまう

copr-cliはpipからインストールすれば1.58-1が使えて解決と思ったのですが、今度はPythonのバージョンが古くてhttps通信時にInsecurePlatformWarningが出ました。

[Security: Verified HTTPS with SSL/TLS — urllib3 dev documentation](https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning)を見るとPythonを2.7.9以上にするのが一番理想なのですが、CentOS 7に入っているPythonは2.7.5です。
softwarecollection.orgの[python27-python](https://www.softwarecollections.org/repos/rhscl/python27/epel-7-x86_64/python27-python-2.7.8-3.el7/)でも2.7.8です。

[Without modifying code](https://urllib3.readthedocs.org/en/latest/security.html#without-modifying-code)の手順で警告を無視するというあまり良くない方法も使ってみたのですが、手元のDocker環境ではよかったもののTravis CIだとエラーになってしまうという現象が起きました。

## copr APIの認証方法

というわけでcopr-cliを使わずにcurlでCoprのAPIを呼び出す方法を調べました。

まずは認証ですが、[API for Copr](https://copr.fedoraproject.org/api/)の先頭にcopr-cli用の設定ファイル形式でAPIトークンの情報が表示されています。が、APIの認証方法は記載されていません。

しかたがないので、python-coprのソースを読んでみるとcopr/client/client.pyに以下のようなコードがありました。

```
...(snip)...
    def _fetch(self, url, data=None, username=None, method=None,
               skip_auth=False, on_error_response=None, headers=None):
...(snip)...
        if not skip_auth:
            kwargs["auth"] = (self.login, self.token)
...(snip)...
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                **kwargs
            )
...(snip)...
```

[PythonのRequestsライブラリ](http://docs.python-requests.org/en/latest/)の[Basic Authentication](http://docs.python-requests.org/en/latest/user/authentication/#basic-authentication)のドキュメントを見ると、上記のコードは `self.login` の値をユーザ名、 `self.token` の値をパスワードとしてBASIC認証していることがわかりました。

## APIの呼び出し例

[hnakamur/nginx-rpm](https://github.com/hnakamur/nginx-rpm/)の[scripts/build.sh](https://github.com/hnakamur/nginx-rpm/blob/358d646a22c9c516a9247595e296b256d61a86f6/scripts/build.sh#L72-L95)のコードで説明します。

```
build_rpm_on_copr() {
  build_srpm

  # Check the project is already created on copr.
  status=`curl -s -o /dev/null -w "%{http_code}" https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/${copr_project_name}/detail/`
  if [ $status = "404" ]; then
    # Create the project on copr.
    # We call copr APIs with curl to work around the InsecurePlatformWarning problem
    # since system python in CentOS 7 is old.
    # I read the source code of https://pypi.python.org/pypi/copr/1.62.1
    # since the API document at https://copr.fedoraproject.org/api/ is old.
    curl -s -X POST -u "${COPR_LOGIN}:${COPR_TOKEN}" \
      --data-urlencode "name=${copr_project_name}" \
      --data-urlencode "${mock_chroot}=y" \
      --data-urlencode "description=$copr_project_description" \
      --data-urlencode "instructions=$copr_project_instructions" \
      https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/new/
  fi
  # Add a new build on copr with uploading a srpm file.
  curl -s -X POST -u "${COPR_LOGIN}:${COPR_TOKEN}" \
    -F "${mock_chroot}=y" \
    -F "pkgs=@${topdir}/SRPMS/${srpm_file};type=application/x-rpm" \
    https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/${copr_project_name}/new_build_upload/
}
```

最初の `https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/${copr_project_name}/detail/` はプロジェクトの詳細情報取得です。これはログイン不要です。

次の `https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/new/` にPOSTしているのがプロジェクト作成です。


最後の `https://copr.fedoraproject.org/api/coprs/${COPR_USERNAME}/${copr_project_name}/new_build_upload/` がsrpmをアップロードしてビルド開始のAPIです。[API for Copr](https://copr.fedoraproject.org/api/)には `/new_build/` は記載がありますが、 `/new_build_upload/` は記載が無いです。python-coprのcopr/client/client.pyのソースで見つけました。

```
...(snip)...
    def create_new_build(self, projectname, pkgs, username=None,
                         timeout=None, memory=None, chroots=None,
                         progress_callback=None):
...(snip)...
        if urlparse(pkgs[0]).scheme != "":
            api_endpoint = "new_build"
            data["pkgs"] = " ".join(pkgs)
        else:
            try:
                api_endpoint = "new_build_upload"
                f = open(pkgs[0], "rb")
                data["pkgs"] = (os.path.basename(f.name), f, "application/x-rpm")
            except IOError as e:
                raise CoprRequestException(e)

        url = "{0}/coprs/{1}/{2}/{3}/".format(
            self.api_url, username, projectname, api_endpoint
        )
...(snip)...
```

## まとめ
[API for Copr](https://copr.fedoraproject.org/api/)のAPIドキュメントが不完全ですが、python-coprのソースを参考にしてcurlでCopr APIを呼び出すことが出来ました。

これによりCentOS 7でcopr-cliやPythonのバージョンが古いことによる問題を回避できるので良かったです。curlでのcopr APIの呼び出しも上記のようにシンプルに書けるのでこれで十分だと思います。
