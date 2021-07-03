---
title: "ThinkPad P14s AMD Gen 2 のセットアップ"
date: 2021-07-03T15:32:49+09:00
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


続く


