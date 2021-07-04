---
title: "ThinkPad P14s AMD Gen 2 のセットアップ"
date: 2021-07-04T13:30:00+09:00
---

## はじめに

購入した ThinkPad P14s AMD Gen 2 が届いたのでセットアップのメモです。

## 構成

[ThinkPad P14s AMD Gen 2 | レノボジャパン](https://www.lenovo.com/jp/ja/notebooks/thinkpad/p-series/P14s-AMD-G2/p/22WSP144SA2)

* 構成内容: ThinkPad P14s Gen 2 AMD
* 製品番号: 21A0CTO1WWJAJP3
* 単価(税込): 134,618 円
* Configuration Details
    - AMD Ryzen 7 PRO 5850U (1.90GHz, 12MB)
    - Windows 10 Pro 64bit - 日本語版
    - 16GB DDR4 3200MHz (オンボード)
    - 128GB ソリッドステートドライブ (M.2 2242, PCIe-NVMe)
    - 14.0型FHD液晶(1920x1080) IPS、400nit、72%NTSC、マルチタッチ非対応
    - ブラック
    - なし
    - 内蔵グラフィックス
    - IR & 720p HDカメラ(マイクロホン付)
    - 指紋センサーあり (ブラック)
    - 英語キーボード
    - Wi-Fi 6対応 (IEEE802.11ax/ac/a/b/g/n準拠) (2x2) +Bluetooth
    - TPMあり(TCG V2.0準拠，ハードウェアチップ搭載)
    - BIOS Absolute有効
    - 3セル リチウムイオンバッテリー (50Wh)
    - 65W ACアダプター (2ピン)(USB Type-C)
    - 14.0型FHD液晶(1920x1080)IPS、400nit、72%NTSC、マルチタッチ非対応、IR&720p HDカメラ、マイク、WLAN、WWAN非対応、FreeSync
    - 日本語
    - なし
    - 1年間 引き取り修理

### RAMとSSDは別途ヨドバシ・ドット・コムで購入

* RAM CT32G4SFD832A [32GB DDR4 3200 MT/s PC4-25600 CL22 DR x8 Unbuffered SODIMM 260pin]
    - 単価(税込): 21,180 円
* SSD WDS100T2B0C [バルクSSD WD SN550シリーズ 1TB]
    - 単価(税込): 14,920 円

## 注文と発送

* 2021-06-19 注文
* 2021-06-28 発送
* 2021-07-03 到着

## Windows 10 のプロダクトキー確認

[(1) How can I retrieve my Windows 10 product key from my Lenovo's and HP's laptop? - Quora](https://www.quora.com/How-can-I-retrieve-my-Windows-10-product-key-from-my-Lenovos-and-HPs-laptop)

管理者権限でコマンドプロンプトまたはパワーシェルを開いて以下のコマンドを実行。

```
wmic path SoftwareLicensingService get OA3xOriginalProductKey
```

表示されたプロダクトキーはいつも使っているパスワードマネージャ KeePassXC に登録して管理。

## ハードウェアキーボードレイアウトを英語に変更

初期セットアップのときに設定を間違えたのか、キーボードレイアウトが「日本語キーボード(106/109キー)」になってしまっていました。

[英語キーボードと日本語キーボードの切り替え | Windows 10 | 初心者のためのOffice講座](https://hamachan.info/win10-win-ekeybord/) を参考に英語に切り替え。Windowsの再起動が必要です。

1. Windows キー + i を押して設定画面を表示
2. 「時刻と言語」を選択
3. 左のメニューの「言語」を選択
4. 「優先する言語」の一覧の「日本語」を選択し「オプション」ボタンを押す
5. ハーソウェアキーボードレイアウトの「レイアウトを変更する」ボタンを押す
6. 「英語キーボード(101/102キー)」を選択して「今すぐ再起動する」ボタンを押す　

## Windows 10 クリーン・インストール

[ThinkPad および Lenovo LaVie コンピューター上での Windows 10 のクリーン・インストール - Lenovo Support JP](https://support.lenovo.com/jp/ja/solutions/ht103617-clean-install-of-windows-10-on-thinkpad-and-lenovo-lavie-computers) に BIOS を最新にするよう書かれていました。

[Lenovo サポート Web サイト](http://www.lenovo.com/support) から該当の機種の最新の BIOS をダウンロードしてインストールすれば良いとのことです。

サポート Web サイトにアクセスして、「製品グループを選択する」のページの「PC」の「製品を検出する」を押してみると [Lenovo Service Bridge: 自動的にシステムタイプとシリアル番号を検出 - Lenovo Support RO](https://support.lenovo.com/ro/ja/solutions/ht104055) のインストールのダイアログがブラウザ内に表示されました。

一方 Windows のスタートメニューを見てみると [Commercial Vantage（企業向け） - Lenovo Support JP](https://support.lenovo.com/jp/ja/solutions/hf003321-lenovo-vantage-for-enterprise)  というアプリケーションがインストール済みになっていました。

そこで Lenovo Service Bridge は使わずに Commercial Vantage (以下 Vantage と略します)のほうを使うことにして、そちらでシステムの更新を行いました。

ちなみに Vantage では機種名は ThinkPad P14s Gen 2a という表示になっていました。

Vantage で表示される BIOS バージョンは R1MET35W 1.05 でした。

[Lenovo サポート Web サイト](http://www.lenovo.com/support) で「製品グループを選択する」のページの「PC」の「PC製品サポートへ」を押し、検索欄に「ThinkPad P14s」と入力し「ThinkPad P14s Gen 2 (マシンタイプ 21A0,21A1) ノートブック」を選択すると [laptops and netbooks :: thinkpad p series laptops :: thinkpad p14s gen 2 type 21a0 21a1 - Lenovo Support JP](https://pcsupport.lenovo.com/jp/ja/products/laptops-and-netbooks/thinkpad-p-series-laptops/thinkpad-p14s-gen-2-type-21a0-21a1/?linkTrack=Homepage%3ABody_Search%20Products&searchType=3&keyWordSearch=ThinkPad%20P14s%20Gen%202%20%28%E3%83%9E%E3%82%B7%E3%83%B3%E3%82%BF%E3%82%A4%E3%83%97%2021A0,%2021A1%29%20%E3%83%8E%E3%83%BC%E3%83%88%E3%83%96%E3%83%83%E3%82%AF) が表示されました。

左の「ドライバーとソフトウェア」を選んで右で「BIOS」を選んでバージョンを確認すると 1.05 だったので最新になっていることが確認できました。

### リカバリーメディアをダウンロードしてUSBメモリに書き込み

1. [laptops and netbooks :: thinkpad p series laptops :: thinkpad p14s gen 2 type 21a0 21a1 - Lenovo Support JP](https://pcsupport.lenovo.com/jp/ja/products/laptops-and-netbooks/thinkpad-p-series-laptops/thinkpad-p14s-gen-2-type-21a0-21a1/?linkTrack=Homepage%3ABody_Search%20Products&searchType=3&keyWordSearch=ThinkPad%20P14s%20Gen%202%20%28%E3%83%9E%E3%82%B7%E3%83%B3%E3%82%BF%E3%82%A4%E3%83%97%2021A0,%2021A1%29%20%E3%83%8E%E3%83%BC%E3%83%88%E3%83%96%E3%83%83%E3%82%AF) で 左の「ドライバーとソフトウェア」を選んで右で「リカバリーメディアを注文する」タブを選択し、「クリックして続ける」ボタンを押します。
2. 「資格を確認する」のステップで「シリアル番号を入力」の下の入力欄に Vantage で表示されているシリアル番号を入力します。
3. 「注文する」のステップで「マシンタイプ」が「21A0」、「オペレーティングシステム」が「Win10PROx64」と正しく表示されたことを確認した上で、「国/地域」は「日本」、「OSの言語を選ぶ」は「Japanese」を選択し、保証ポリシーの左の「同意します」チェックボックスをオンにして「次へ」ボタンを押します。
4. 「顧客情報を入力」のステップでは、名、性、メールアドレスを入力して「送信」ボタンを押します。


https://support.lenovo.com/documents/ht103653 を開いて[Lenovo USB Recovery Creator tool for Windows® 8 または以降 (例： Windows® 10)](https://s3-us-west-2.amazonaws.com/ddstools.gdi.lenovo/win8/USBRecoveryCreator.exe) (USBRecoveryCreator.exe という Windows の実行ファイル)をダウンロード、実行します。

実行すると Lenovo ID とパスワードを聞かれるので入力し、先程の注文を選択して、リカバリーメディアをダウンロードします。

ダウンロードが終わった時点で一旦終了して、ダウンロードしたディレクトリを [圧縮・解凍ソフト 7-Zip](https://sevenzip.osdn.jp/) で無圧縮の zip 形式で固めて USBRecoveryCreator.exe とともにバックアップしました。

その後 16GBのUSBメモリを刺して再度 USBRecoveryCreator.exe を実行し、ダウンロードディクトリ内の `*.REM` ファイルを選択してUSBメモリにリカバリーディスクの内容を書き込みます。書き込んだ後の検証が結構時間がかかりますが、書き込みエラーがあるとまずいので終わるまでおとなしく待ちます。

#### 参考: USB メモリにパーティションがあった場合に消す手順

USBRecoveryCreator.exe でUSBメモリに書き込む前の話ですが、私が使おうとしていたUSBメモリはパーティションが複数作られていたので [USBメモリに出来た複数のパーティーションをWindowsの標準機能だけで削除する - Qiita](https://qiita.com/ktyubeshi/items/e71dd89722db85081284) を参考に消しました。

1. Windows キー + R を押して diskpart と入力して起動。
2. `list disk` でディスク一覧を表示し USB メモリのディスク番号を確認。　
3. `select disk ディスク番号` で対象のUSBメモリに切り替え。
4. `detail disk` で選択に間違いがないことを確認。
5. `clean` でパーティションを全て削除。
6. `create parition primary` でプライマリパーティションを作成。
7. `exit` で diskpart を終了。

Windows キーを押して `disk manager` と入力して絞り込み「ハードディスク パーティションの作成とフォーマット」を選択して「ディスクの管理」を起動します。

USBメモリのパーティションをFAT32でフォーマットします。


### メモリ増設とSSD換装

[Lenovo Thinkpad P14s (and T14, T15, P15s) Overview and Upgrade options - YouTube](https://www.youtube.com/watch?v=swlpvRz5w3g) と [ThinkPadの分解はコツがあった！コツを知れば自分でメモリは簡単に交換できる](https://27kamimen.com/bunkai/) を参考に背面カバーを外します。

メモリはオンボードで16GBで増設スロット1つに32GBを追加します。

SSD は128GB のを 1TB に換装します。
SSD を止めているネジと金具を外した後 128GB のSSDを外し、1TBのSSDをつけてネジ止めします。元のSSDと金具は保管しておきます。

### リカバリーの実行

リカバリー用のUSBメモリを刺して電源を入れ、指示に従ってリカバリーを実行します。
終わるとUSBメモリを抜いて再起動するように言われるのでそうします。

ここから結構時間かかりました。

再起動後コマンドプロンプトがポコポコ開いて自動でコマンドが実行されるので終わるまで待ちます。待っていると再起動して Lenovo のロゴが出ている画面でいろいろセットアップが進みまた再起動されます。

その後 Windows の画面で Administrator のユーザーが表示されたかと思ったら [Windows Setup] というダイアログが出てさらにセットアップが続きます。ダイアログには以下のようなメッセージが出ていました。

```
Windows is now setting up the following items:

AuditOne - DoWork
```

その後さらにセットアップと再起動が続いて、今度は Administrator で自動ログインしてセットアップが進み、さらに再起動がかかりました。

そしてまたコマンドプロンプトが開いてセットアップが続き、再起動がかかって続きが来ました (wpeinit の文字を見るのは2回めでループになってないかちょっと心配でしたが下記のダイアログで進んでいるとわかりました)。

今度は「Windows セットアップ」というダイアログで次のようなメッセージが出ました。

```
次の項目を設定します:

AuditTwo - DoWork
AuditTwo - Finish
```

最初は `AuditTwo - DoWork` が太字になっていました。セットアップと再起動が進むうちに `AuditTwo - DoWork` の左に緑のチェックマーク✅ (実際は前景色と背景色が逆)が付き `AuditTwo - Finish` のほうが太字になりました。


## Windows の初期セットアップ

長いリカバリが終わってついに「お住いの地域はこちらでよろしいですか？」のダイアログが出ました。ここから初期セットアップです。

途中は省略して、「アカウントを追加しましょう」では左下の「オフラインアカウント」を選択し、その次は「制限付きエクスペリエンス」を選択しました。

「このPCを使うのはだれですか？」でローカルで作成するアカウント名を入力します。

3つのセキュリティの質問は省略不可なので、選んだ選択肢とパスワードマネージャで生成したランダムな文字列を入力し、パスワードマネージャーに登録しました。

Windows Helloでは「顔認識の使用」か「指紋認証の使用」が選べますが、初めて指紋センサーつきの ThinkPad を買ったので指紋認証を設定しました。

「PIN のセットアップ」では「英字と記号を含める」をチェックしてパスワードマネージャで生成したランダムな文字列を設定しました。

「デバイスのプライバシー設定の選択」は全て「いいえ」にしました。

デバイス登録でメールアドレスを入力する箇所ではやはり英語キーボードなのに日本語配列になっていました。アットマーク `@` は `P` の右の `[` で入力しました。

## Windows の各種設定

### キーボードを英語配列に変更

上記の手順で英語配列に変更しました。

### Ctrl + Space で IME オン/オフ の設定

1. Windows キー + i を押して設定画面を表示
2. 「時刻と言語」を選択
3. 左のメニューの「言語」を選択
4. 「優先する言語」の一覧の「日本語」を選択し「オプション」ボタンを押す
5. 「キーボード」の一覧の「Microsoft IME」を選んで「オプション」ボタンを押す
6. 「キーとタッチのカスタマイズ」を押す
7. 「各キーに好みの機能を割り当てる」のスイッチをオンにする。
8. 「Ctrl + Space」を「IME-オン/オフ」に変更する。

### タッチパッドの設定

1. Windows キー + i を押して設定画面を表示
2. 「デバイス」を選択
3. 左で「タッチパッド」を選択
4. 「カーソルの速度を変更する」を適宜調整
5. 「右クリックするにはタッチパッドの右下を押します」をオフにする
6. 「3本指ジェスチャ」と「4本指ジェスチャ」は「何もしない」に変更

### ディスプレイの設定

1. デスクトップでポップアップメニューの「ディスプレイ設定」を選択
2. 「テキスト、アプリ、その他の項目のサイズを変更する」を「100%」に変更

### 電源とスリープ

スリープはなしに変更

### キーボードの Ctrl と CapsLock 入れ替え

BIOS に Fn と Ctrl の入れ替えという設定はありましたが、Ctrl と CapsLock 入れ替えはなかったので、いつも使ってるレジストリ設定を投入します。

[ASCII.jp：CtrlとCapsを入れ替え！　Windowsのキー配列をカスタマイズ (1/2)](https://ascii.jp/elem/000/000/927/927191/)

[windows10_keyboard_swap_ctrl_caps.reg](/blog/windows10_keyboard_swap_ctrl_caps.reg) を名前をつけて保存して、エクスプローラで選んでポップアップメニューの「結合」を選んでレジストリに登録します。その後 Windows を再起動して反映します。

### マルチタスク設定

1. Windows キー + i を押して設定画面を表示
2. 「システム」を選択
3. 左で「マルチタスク」を選択
4. 「ウィンドウのスナップ」と「タイムライン」をオフ
5. 「AltキーとTabキーを押すと表示されます」を「ウィンドウのみを開く」に変更


### ホスト名設定

参考: [ホスト名の設定（Windows 10）](http://alpha.shudo-u.ac.jp/~helpdesk/network/hostname-win10.html) と [Windows 10でパソコンの名前（PC名）を確認/変更する方法 - Lenovo Support RS](https://support.lenovo.com/rs/ja/solutions/ht105079)

1. Windows キー + x を押して開いたメニューで「システム」をクリック
2. 「このPCの名前を変更」ボタンを押す
3. 「PC名を変更する」ダイアログで希望のPC名を入力後、再起動して反映

### エクスプローラの表示設定

1. Windows キー + e を押してエクスプローラーを開く
2. [表示] / [詳細] メニューをクリック
3. [表示] / [オプション] メニューをクリック
4. 「フォルダー オプション」ダイアログで「表示」タブに切り替え
5. 詳細設定で以下のように変更して「適用」ボタンを押す
    - 「隠しファイル、隠しフォルダー、および隠しドライブを表示する」をクリック
    - 「登録されている拡張子は表示しない」をオフ
    - 「保護されたオペレーティングシステムファイルを表示しない(推奨)」をオフ
6. 「フォルダーを表示」グループボックス内の「フォルダーに適用」ボタンを押す

### Bluetooth をオフ

1. Windows キー + i を押して設定画面を表示
2. 「デバイス」をクリック
3. 「Bluetoothとその他のデバイス」でBluetoothのスイッチをオフに変更


## パスワードマネージャー KeePassXC インストール

[KeePassXC Password Manager](https://keepassxc.org/) からインストーラーをダウンロードしてインストールします。

データファイルは既存のPCからUSB外付けハードディスクにコピーし、それを新しいPCに繋ぎ変えてコピーします。

## Firefox と Chrome のセットアップ

### Firefox

[Mozilla から高速、プライベート、無料の Firefox ブラウザー をダウンロード](https://www.mozilla.org/ja/firefox/new/) からダウンロードしてインストールします。

私はFirefoxは敢えてログインしない使い方にしています。

ブックマークは他の PC の Firefox からエクスポートしたものをインポートします。

パスワードは保存しないように設定変更します。

拡張は Diigo と拙作の Format Link を入れます。

#### Google の英語での検索設定

Firefox は設定の検索から「他の検索エンジンを追加」リンクをクリックすると `addons.mozilla.org` に登録された検索エンジンを追加できます。

しかしこれだと自分で好きな設定に出来ないので、ブックマークを使う方式にしています。

場所はどこでも良いので以下のようなブックマークを作ります。

1. ハンバーガーメニューの「ブックマーク」の「ブックマークを管理」をクリック
2. 左のツリーで「他のブックマーク」を選び(他でも可)、[管理]/[ブックマークを追加]メニューを選択
3. 「新しいブックマークを追加」ダイアログで以下のように入力して「保存」ボタンを押す。
    * 名前: Google en
    * URL: `https://www.google.com/search?q=%s&hl=en`
    * タグ: (空のまま)
    * キーワード: g

これでURL欄に g スペースと入れてその後に検索ワードを入れてEnterを押すと英語で検索されます。

### Chrome

[Google Chrome - Google の高速で安全なブラウザをダウンロード](https://www.google.com/intl/ja_jp/chrome/) からダウンロードしてインストールします。

自分のアカウントでサインインすると設定(拡張のインストールとブックマーク)が同期されます。自分の写真がブラウザに常に表示されるのはうっとおしいのでアバターはChromeで用意されているアイコンに変更します。

#### Google の英語での検索設定

設定で同期されるので変更は不要ですが、「検索エンジンの管理」では以下の設定を追加しています。

* 検索エンジン: Google en
* キーワード: g
* URL (%s=検索語): `https://www.google.com/search?q=%s&hl=en`

これでURL欄に g とスペースを押すと Google en と表示され、続いて検索ワードを入れて Enter を押すと英語で検索されます。


## WSL2 セットアップ

参考: [WSL2のUbuntuとDocker Desktop for Windowsを試してみた · hnakamur's blog](/blog/2020/05/28/setup-wsl2-ubuntu-and-docker-desktop-for-windows/)

今回も手順をミスって一旦 WSL1 で作った後 WSL2 に変換したので、下記の手順で一発で行けるかは不明です。

管理者権限の PowerShell を開いて以下のコマンドを実行し Microsoft-Windows-Subsystem-Linux の機能を有効にします。

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

ここで一度Windowsを再起動します。

管理者権限の PowerShell を開いて以下のコマンドを実行し "仮想マシン プラットフォーム"のオプション コンポーネントを有効にします。

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

[WSL 2 Linux カーネルの更新 | Microsoft Docs](https://docs.microsoft.com/ja-jp/windows/wsl/wsl2-kernel) から Linux カーネル更新プログラム パッケージ（ファイル名： wsl_update_x64.msi ）をダウンロード、インストールします。

以下のコマンドを実行し、WSLのデフォルトバージョンを2にします。

```powershell
wsl --set-default-version 2
```

タスクバーの「Microsoft Store」を開き検索欄に「Ubuntu 20.04」と入力して「Ubuntu 20.04 LTS」を選択しインストールします。

## Visual Studio Code インストール

[Visual Studio Code - Code Editing. Redefined](https://code.visualstudio.com/) からインストーラーをダウンロードしてインストールします。

## Cica フォントインストール

[miiton/Cica: プログラミング用日本語等幅フォント Cica(シカ)](https://github.com/miiton/Cica) の [Releases · miiton/Cica](https://github.com/miiton/Cica/releases) から最新リリースの絵文字ありの zip ファイルをダウンロードします。

エクスプローラで開いて `*.ttf` ファイルを zip の外にコピーして、選択してポップアップメニューの「インストール」でインストールします。

## Windows Terminal インストールと設定

## Windows Terminal のインストール

タスクバーの「Microsoft Store」を開き検索欄に「terminal」と入力して「Windows Terminal」を選択しインストールします。

### Windows Terminal の設定

参考: [Windows Terminalの私の設定 · hnakamur's blog](/blog/2020/05/16/my-settings-for-windows-terminal/)

ウィンドウの列数、行数と位置は以下のようにしました。

```
    "initialCols": 200,
    "initialRows": 54,
    "initialPosition": "0,0",
```

## 7-Zip をインストール

[圧縮・解凍ソフト 7-Zip](https://sevenzip.osdn.jp/) から 7-Zip をダウンロードしてインストールします。
(以前は次項の wsl-ssh-agent の配布物の解凍に必要だったのですが、最新版は通常のzip形式になっていたのでこの点だけなら不要です)

## WSL2 と KeePassXC で ssh-agent を使う設定

### ssh-agent のサービス自動起動設定

#### OpenSSH クライアントはプリインストールされていました

参考: [OpenSSH をインストールする | Microsoft Docs](https://docs.microsoft.com/ja-jp/windows-server/administration/openssh/openssh_install_firstuse) と [Windows 10 に OpenSSH クライアントをインストール · hnakamur's blog](/blog/2020/02/22/install-openssh-client-to-windows10/)

管理権限の PowerShell を開いて以下のコマンドを実行して OpenSSH クライアントがインストール済みかを確認します。

```powershell
Get-WindowsCapability -Online | ? Name -like 'OpenSSH*'
```

私の環境では以下の出力となり OpenSSH クライアントはプリインストール済みでした。

```
Name  : OpenSSH.Client~~~~0.0.1.0
State : Installed

Name  : OpenSSH.Server~~~~0.0.1.0
State : NotPresent
```

#### ssh-agent サービスの自動起動設定

管理権限の PowerShell を開いて以下のコマンドを実行して ssh-agent サービスの状態を確認します。

```powershell
Get-Service ssh-agent | Select Name,DisplayName,Status,StartType
```

私の環境では Status が Stopped, StartType が Disabled になっていました。

StartType が Disabled のままだとサービスを起動できないので、以下のコマンドで自動起動にします。

```powershell
Set-Service ssh-agent -StartupType Automatic
```

その後以下のコマンドを実行して ssh-agent サービスを起動します。

```powershell
Start-Service ssh-agent
```

再度

```powershell
Get-Service ssh-agent | Select Name,DisplayName,Status,StartType
```

を実行して Status が Running, StartType が Automatic になったことを確認します。

### WSL2 で wsl-ssh-agent のセットアップ
参考:
* [rupor-github/wsl-ssh-agent: Helper to interface with Windows ssh-agent.exe service from Windows Subsystem for Linux (WSL)](https://github.com/rupor-github/wsl-ssh-agent) の [WSL 2 compatibility](https://github.com/rupor-github/wsl-ssh-agent#wsl-2-compatibility)
* [KeePassとKeeAgentでWSL2用にssh-agentを動かす · hnakamur's blog](/blog/2020/05/29/run-ssh-agent-with-keepass-and-keeagent-for-wsl2/)

手順:

1. [Releases · rupor-github/wsl-ssh-agent](https://github.com/rupor-github/wsl-ssh-agent/releases) から最新版をダウンロードします。 2021-07-04 時点では v1.5.2 で `wsl-ssh-agent.zip` というファイル名でした。
2. エクスプローラーでダウンロードした zip ファイルを開き `npiperelay.exe` を zip の外にコピーします。私は `C:\wsl-ssh-agent` というフォルダーを作ってそこにコピーすることにしました。
3. WSL2 の Ubuntu-20.04 のシェルで以下のコマンドを実行し `socat` パッケージをインストールします。

```sh
sudo apt update && sudo apt install -y socat
```

4. [WSL 2 compatibility](https://github.com/rupor-github/wsl-ssh-agent#wsl-2-compatibility) に書かれている設定を `npiperelay.exe` のパスを自分の環境に応じて書き換えて `~/.bashrc` に追記します。

```sh
# Use ssh-agent through wwl-ssh-agent
export SSH_AUTH_SOCK=$HOME/.ssh/agent.sock
ss -a | grep -q $SSH_AUTH_SOCK
if [ $? -ne 0 ]; then
    rm -f $SSH_AUTH_SOCK
    ( setsid socat UNIX-LISTEN:$SSH_AUTH_SOCK,fork EXEC:"/mnt/c/wsl-ssh-agent/npiperelay.exe -ei -s //./pipe/openssh-ssh-agent",nofork & ) >/dev/null 2>&1
fi
```

5. WSL2 のターミナルを起動し直すか以下のコマンドを実行してログインシェルを再起動します。

```sh
exec $SHELL -l
```

### KeePassXC から ssh-agent への接続設定

1. KeePassXC の [ツール]/[設定] メニューをクリック
2. 左の「SSHエージェント」をクリック
3. 「SSHエージェント統合を有効にする」と「Pagentの代わりにOpenSSH for Windowsを使用する」にチェックして「OK」ボタンを押す
4. KeePassXC を一旦終了して再起動
5. [ツール]/[設定]メニューをクリックし左の「SSHエージェント」をクリックして「SSHエージェント接続が動作中です！」と表示されていればOKです。

鍵の追加はエントリー一覧上でSSH秘密鍵を添付してあるエントリー(パスワード欄にパスフレーズを設定しています)を選択して[エントリー]/[SSHエージェントに鍵を追加]メニューで行います。

また `~/.ssh/config` のファイルを添付してあるエントリーからファイルを一旦Windowsのフォルダーに保存し、WSL2 のシェルを開いて WSL2 側に移動します。

例えば Documents フォルダーに保存したとして WSL2 のシェルでは以下のようにします。

```sh
mkdir -m 700 ~/.ssh
mv /mnt/c/Users/hnakamur/Documents/config ~/.ssh/config
chmod 600 ~/.ssh/config
```

これで KeePassXC がロック中の状態では `ssh-add -l` で確認すると `The agent has no identities.` となり、アンロック中は指定の鍵が登録された状態になります。
