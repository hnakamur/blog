Title: Homebrew Caskを使わずにdmgファイルのアプリをコマンドでインストールする
Date: 2015-04-06 00:45
Category: blog
Slug: blog/2015/04/06/install-apps-without-homebrew-cask

## なぜHomebrew Caskをやめたか

[Mac の開発環境構築を自動化する (2015 年初旬編) - t-wadaのブログ](http://t-wada.hatenablog.jp/entry/mac-provisioning-by-ansible)でもHomebrew Caskの不安な点について書かれていますが、私もHomebrew Caskは便利と思いつつも止めたいなと思っていました。

私が使うアプリに関してはほとんどがアプリ側で最新版のお知らせとバージョンアップの仕組みを持っています。あとHomebrew Caskは/opt/homebrew-cask/以下に実体を置いて~/Applications/や/Applications/にシンボリックリンクを貼るようになっています。

私はそこまで複雑な仕組みは要らないので、初期インストールがコマンドで半自動化できれば十分です。

## dmgファイルのアプリをコマンドラインからインストールする

[osx - Install dmg package on MAC OS from Terminal - Stack Overflow](http://stackoverflow.com/questions/22934083/install-dmg-package-on-mac-os-from-terminal/22940943#22940943)や[Command Line Mac: Installing a .dmg application from the command line](http://commandlinemac.blogspot.jp/2008/12/installing-dmg-application-from-command.html)を見て実際にやってみました。

ソースは[hnakamur/my-macbook-initial-setup · GitHub](https://github.com/hnakamur/my-macbook-initial-setup)にあります。

以下のアプリをdmgファイルからインストールしています。

* [splhack/macvim-kaoriya · GitHub](https://github.com/splhack/macvim-kaoriya)
* [calibre - E-book management](http://calibre-ebook.com/)
* [Chrome](https://www.google.co.jp/chrome/browser/desktop/index.html)
* [Firefox](https://www.mozilla.org/ja/firefox/new/)
* [Google 日本語入力](https://www.google.co.jp/ime/)
* [iTerm2 - Mac OS Terminal Replacement](http://iterm2.com/)
* [Java (JRE)](https://java.com/ja/download/)
* [GrandPerspective](http://grandperspectiv.sourceforge.net/)
* [MySQL Workbench](https://www-jp.mysql.com/products/workbench/)
* [MacPass](http://mstarke.github.io/MacPass/)
* [Spark](http://www.shadowlab.org/Software/spark.php)
* [Oracle VM VirtualBox](https://www.virtualbox.org/)
* [Vagrant](https://www.vagrantup.com/)
* [XQuartz](http://xquartz.macosforge.org/landing/)

## dmgファイルのマウントとアンマウント

共通の処理として、dmgファイルのマウントは `hdiutil attach` 、アンマウントは `hdiutil detach` コマンドで行います。

マウントした時の /Volumes/〜 のディレクトリ名は `hdiutil attach` の実行結果の最後の行から取得できます。

最初は

```
  mount_dir=`hdiutil attach $dmg_file | awk 'END{print $NF}'`
```

のようにして最後の行の一番右のフィールドを取得していましたが、 `/Volumes/Google Chrome` のように空白を含む場合があることがわかりました。

[osx - Install dmg package on MAC OS from Terminal - Stack Overflow](http://stackoverflow.com/questions/22934083/install-dmg-package-on-mac-os-from-terminal/22940943#22940943)では第1フィールドと第2フィールドを消して第3フィールド以降にしていますが、試してみると余分な空白（実際はタブと判明）が付いてきました。

`hdiutil attach` の結果をファイルに落として見てみたら、空白に加えてタブで区切られていてタブで区切るほうがシンプルなことがわかりました。

そこで、以下のようにして取得するようにしました。

```
  mount_dir=`hdiutil attach $dmg_file | awk -F '\t' 'END{print $NF}'`
```

## インストール方法のパターン

上記のアプリの範囲では4パターンありました。

### dmgファイル内に〜.appフォルダがあるパターン

Chromeなどがこのパターンです。[ditto](https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/ditto.1.html)コマンドで/Applications/〜.appにコピーするようにしました。

https://github.com/hnakamur/my-macbook-initial-setup/blob/df0eb48db189d39de9103a53c06f85a5acfaf347/run.sh#L731-L740

```
install_google_chrome() {
  download_url=https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg
  dmg_file=${download_url##*/}

  curl -LO $download_url
  mount_dir=`hdiutil attach $dmg_file | awk -F '\t' 'END{print $NF}'`
  sudo /usr/bin/ditto "$mount_dir/Google Chrome.app" "/Applications/Google Chrome.app"
  hdiutil detach "$mount_dir"
  rm $dmg_file
}
```

### dmgファイル内に*.pkgのインストーラがあるパターン

Google日本語入力などがこのパターンです。OSXの[installer](https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man8/installer.8.html)コマンドでインストールします。

https://github.com/hnakamur/my-macbook-initial-setup/blob/df0eb48db189d39de9103a53c06f85a5acfaf347/run.sh#L742-L751

```
install_google_japanese_input() {
  download_url=https://dl.google.com/japanese-ime/latest/GoogleJapaneseInput.dmg
  dmg_file=${download_url##*/}

  curl -LO $download_url
  mount_dir=`hdiutil attach $dmg_file | awk -F '\t' 'END{print $NF}'`
  sudo installer -pkg $mount_dir/GoogleJapaneseInput.pkg -target /
  hdiutil detach "$mount_dir"
  rm $dmg_file
}
```

### dmgファイル内に独自形式のインストーラがあるパターン

Javaがこのパターンでした。インストーラを実行してインストールします。

https://github.com/hnakamur/my-macbook-initial-setup/blob/df0eb48db189d39de9103a53c06f85a5acfaf347/run.sh#L762-L772

```
install_java() {
  download_url=http://javadl.sun.com/webapps/download/AutoDL?BundleId=105219
  dmg_file=jre.dmg

  curl -L -o $dmg_file "$download_url"
  mount_dir=`hdiutil attach $dmg_file | awk -F '\t' 'END{print $NF}'`
  java_dir="${mount_dir##*/}"
  sudo "$mount_dir/${java_dir}.app/Contents/MacOS/MacJREInstaller"
  hdiutil detach "$mount_dir"
  rm $dmg_file
}
```

### zipファイル内に〜.appがあるパターン

iTerm2などがこのパターンです。unzipコマンドの-dオプションで解凍先を/Applicationsにして解凍してインストールします。

https://github.com/hnakamur/my-macbook-initial-setup/blob/df0eb48db189d39de9103a53c06f85a5acfaf347/run.sh#L753-L760

```
install_iterm2() {
  download_url=https://iterm2.com/downloads/stable/iTerm2_v2_0.zip
  zip_file=${download_url##*/}

  curl -LO $download_url
  sudo unzip $zip_file -d /Applications
  rm $zip_file
}
```

## まとめ

Homebrew Caskを使わずにコマンドラインでOSXのアプリのインストールを半自動化しました。全自動ではなく半自動化といっているのは、アプリによってパスワード入力が必要だったり、ダイアログが表示されてボタンを押す必要があるからです。

アプリのバージョンが今後上がった時にダウンロードURLを再度調べる必要があるのが面倒ではありますが、OSXを一からセットアップするのはたまにしか行わないのでよしとします。
