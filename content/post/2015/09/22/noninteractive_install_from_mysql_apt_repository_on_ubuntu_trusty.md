Title: MySQL APT repositoryからMySQL 5.7.xをインストールするスクリプト
Date: 2015-09-22 22:35
Category: blog
Slug: blog/2015/09/22/noninteractive_install_from_mysql_apt_repository_on_ubuntu_trusty

Ubuntu 14.04 (Trusty)に[MySQL APT Repository](http://dev.mysql.com/downloads/repo/apt/)からMySQL 5.7 (Development Release)を
インストールするスクリプトを書きました。

Vagrantfileと共に[hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty)に置いてあります。

## 使い方

[MySQL :: Download MySQL APT Repository](http://dev.mysql.com/downloads/repo/apt/)をブラウザで見てmysql-apt-config_x.x.x-1ubuntu14.04_all.debのファイルのバージョンを確認し、スクリプト内の [mysql_apt_deb_file](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L4)変数の値をを適宜修正してください。

スクリプト内の[mysql_root_password](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L8)変数の値を設定したいMySQLのrootユーザのパスワードに変更してください。

あとはスクリプトを実行すればOKです。

## スクリプトの実装メモ

### noninteractiveなmysql-apt-configのインストール

単に `sudo dpkg -i mysql-apt-config_0.3.7-1ubuntu14.04_all.deb` のように実行すると、途中でCUIのダイアログが開いてMySQLサーバのバージョンなどを聞かれてしまいます。自動インストール用のスクリプトではインタラクティブに聞かれてほしくないので `export DEBIAN_FRONTEND=noninteractive` を指定する必要があります。
[Ubuntu Manpage: debconf - Debian package configuration system](http://manpages.ubuntu.com/manpages/trusty/man7/debconf.7.html)に説明があります。

またその後 `sudo dpkg ...` だと環境変数を引き継がないので `sudo -E dpkg ...` のように `-E` オプションを指定しています。[bash - install mysql on ubuntu without password prompt - Stack Overflow](http://stackoverflow.com/questions/7739645/install-mysql-on-ubuntu-without-password-prompt#comment37966911_7740393)で知りました。

実行するのが1回だけなら `sudo DEBIAN_FRONTEND=noninteractive dpkg ...` のほうがシンプルで良いと思います。が、今回は後でmysql-community-serverをインストールするときにも必要なので上記の方式にしました。

`export DEBIAN_FRONTEND=noninteractive` だけで良い場合もありますが、ダイアログで選ぶ値を予め設定しておく必要がある場合もあります。
[dpkg - How to configure the MySQL APT repo on Ubuntu, on a non-interactive shell? - Unix & Linux Stack Exchange](http://unix.stackexchange.com/questions/158052/how-to-configure-the-mysql-apt-repo-on-ubuntu-on-a-non-interactive-shell?newreg=31ba47900d6f4e01ba1625f43da05f82)で mysql-apt-config のインストールには `echo mysql-apt-config mysql-apt-config/enable-repo select mysql-5.7-dmr | sudo debconf-set-selections` としておけば良いらしいという情報を得ました。

ですが、調査のために mysql-apt-config を手動インストールしてその前後で

```
sudo debconf-get-selections | grep mysql
```

して設定される項目を見てみると違う名前になっていました。スクリプトでは[手動インストールで設定される項目に合わせて設定するようにしました。](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L16-L21)


### noninteractiveなmysql-community-serverのインストール

こちらも同様に `export DEBIAN_FRONTEND=noninteractive` のあと `sudo -E apt-get -y install ...` でインストールしています。設定値は
[bash - install mysql on ubuntu without password prompt - Stack Overflow](http://stackoverflow.com/questions/7739645/install-mysql-on-ubuntu-without-password-prompt/20037235#20037235)を参考にしつつ、まず手動インストールして `sudo debconf-get-selections | grep mysql` で設定値を確認し、[それに合わせて設定するようにしました。](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L28-L29)


### noninteractiveなmysql_secure_installationの実行

[コードで実行！ mysql_secure_installation プロビジョニング | サイブリッジラボブログ](http://labs.cybridge.jp/cybridge/development/1312.html)にも書かれていますが、MySQL 5.5の頃はインタラクティブな入力を要求するシェルスクリプトだったので、中身を読んで等価な処理をすることができました。私も以前[等価なスクリプト](https://github.com/hnakamur/ansible-playbooks/blob/490b782d57ed93442c981dab5612ff396027ba98/roles/mysql/server/files/mysql_secure_installation.sh)を書いていました。

しかし、5.7ではmysql_secure_installationはバイナリになってしまいました。 `man mysql_secure_installation` で確認したところ、`--password` もしくは `-p` オプションはあるが無視して必ずパスワードプロンプトを出すと書いてありました。自動インストール用スクリプトでは困るのですが、

[./.mysql_root_password.cnf](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L34-L35)


```
[client]
password=${mysql_root_password}
```

といった内容のファイルを作って `--defaults-extra-file` オプションで指定すれば回避できました。

プロンプトが出て入力する部分は[標準入力にリダイレクトで流し込めば](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L38-L45) OKでした。ただし、MySQLのrootユーザのパスワードを変えるパターンは試してないです。

[上記の入力に対する出力結果](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L51-L101)をコメントとして残しています。

* MySQLのrootユーザのパスワードは変えない
* パスワードの強度チェッカーはインストールしない
* anonymousユーザは削除する
* リモートからのrootユーザのログインは許可しない
* testデータベースは削除
* 権限をリロード

という設定となっています。

標準入力に流し込むのではなく `--use-default` オプションを使うという手もあります。
[--use-defaultの場合の出力結果](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L109-L163)もコメントとして残しています。 この場合の設定内容は以下の通りです。

* MySQLのrootユーザのパスワードは変えない
* パスワードの強度チェッカーをSTRONGの強度に設定する
* anonymousユーザは削除する
* リモートからのrootユーザのログインは許可しない
* testデータベースは削除
* 権限をリロード


[パスワードチェッカーのSTRONGの強度の説明](https://github.com/hnakamur/noninteractive_install_mysql_from_apt_repository_to_ubuntu_trusty/blob/3d7392a1d99dbfc3eb26eecef75dee5549a2cca7/provision.sh#L123)によると、8文字以上で、文字種は数値、英字大文字、英字小文字、記号を全て含める必要があり、辞書に登録されている単語は弾くようです。実際には試してないので違うかもしれません。

### 参考: debconf-set-selections で設定した項目の削除方法

`debconf-set-selections` で設定した項目は `debconf-get-selections` で確認できますが、削除はどうするのかとググってみたら [debian - How do I delete values from the debconf database? - Server Fault](http://serverfault.com/questions/332459/how-do-i-delete-values-from-the-debconf-database/332490#332490) に説明を見つけました。

```
echo PURGE | debconf-communicate パッケージ名
```

のようにすると「パッケージ名」に対する全ての設定を削除できました (スクリプトでは使っていませんが、試行錯誤中に試しました)。
[Configuration management](https://www.debian.org/doc/packaging-manuals/debconf_specification.html#AEN106) にPURGEと他のコマンドについて説明があるとのことです。

## おわりに

というわけで何とか自動化出来ました。個人的にはインストール用のコマンドはコマンドラインオプションか環境変数を設定したらノンインタラクティブで実行できるように作っておいて欲しいなあと思います。インタラクティブにしたい場合もインタラクティブモードで起動するようなコマンドラインオプションをつけて、ダイアログで選択が終わったらそれに対応するコマンドラインオプションを指定して起動したかのように処理をするような作りにすればいいのではないでしょうか。


