---
title: "マイナンバーカードに含まれる2つの電子証明書について調べてみた"
date: 2022-11-01T21:39:34+09:00
lastmod: 2022-11-06T21:25:00+09:00
---
## はじめに

マイナンバーカードに含まれる2つの電子証明書について調べてみたのでメモです。

## マイナンバーカードに含まれる2つの電子証明

[総務省｜マイナンバー制度とマイナンバーカード｜公的個人認証サービスによる電子証明書](https://www.soumu.go.jp/kojinbango_card/kojinninshou-01.html) によるとマイナンバーカードには2つの電子証明書が含まれています。

* 署名用電子証明書
* 利用者証明用電子証明書

上のページでは図の画像が小さいですが [マイナンバーカードと公的個人認証制度の概要について (PDF)](https://www.soumu.go.jp/main_content/000528384.pdf) では大きな図が見られます。
なお、署名用秘密鍵と利用者証明用秘密鍵は「秘密鍵を無理に読み出そうとすると、ICチップが壊れる仕組み」とのことです。

## 電子証明書の表示方法
[証明書の表示方法 | 公的個人認証サービス ポータルサイト](https://www.jpki.go.jp/download/howto_android/certificate_p01.html) の左のメニューに従ってAndroid用JPKI利用者ソフトアプリをインストールし、このページの手順で確認しました。

表示の際に以下のようにパスワードまたは暗証番号の入力を求められました。
ファイルに出力することもできました。

| 表示対象の証明書       | 入力するパスワード   | 出力ファイル名                 | 基本4情報 |
| ----------------       | -------------------- | --------------                 | --------- |
| 署名用電子証明書       | 英数のパスワード     | CertUserSignYYYYMMDDHHMMSS.cer | あり      |
| 利用者証明用電子証明書 | 数字4桁の暗証番号    | CertUserAuthYYYYMMDDHHMMSS.cer | なし      |


出力ファイル名の日付部分は出力した際の日時になっていました。

## 基本4情報

[総務省｜マイナンバー制度とマイナンバーカード｜マイナンバーカード](https://www.soumu.go.jp/kojinbango_card/03.html) に以下の説明があります。

>「署名用電子証明書」は、氏名、住所、生年月日、性別の4情報が記載され、e-Taxの確定申告など電子文書を送信する際に使用できます。

openssl で 署名用電子証明書の SAN (Subject Alternative Name) を見てみると以下のようになっていました。

```
$ openssl x509 -noout -ext subjectAltName -in CertUserSign*.cer
X509v3 Subject Alternative Name:
    othername: 1.2.392.200149.8.5.5.1::【氏名】, othername: 1.2.392.200149.8.5.5.4::【生年月日XYYYYMMDD】, othername: 1.2.392.200149.8.5.5.3::【性別】, othername: 1.2.392.200149.8.5.5.5::【住所】, othername: 1.2.392.200149.8.5.5.2::00000, othername: 1.2.392.200149.8.5.5.6::0000000000000000000000
```

氏名は氏と名が全角空白で区切られていました。住所は郵便番号はなしで都道府県から書かれていました。

2次情報ですが [マイナンバーカード（個人番号カード）に含まれている個人情報・電子証明書の詳細 | Japanese PKI Blog](https://pki.world-tls.com/kojinbango-card/) に説明がありましたので引用します。

```
X509v3 Subject Alternative Name:
    othername: 1.2.392.200149.8.5.5.1::[氏名：JIS 第 1 水準、第 2 水準、補助漢字以外の文字は代替文字に変換], 
    othername: 1.2.392.200149.8.5.5.4::[生年月日：EYYYYMMDD E=1:明治、2:大正、3:昭和、4:平成、5:令和、0:不明], 
    othername: 1.2.392.200149.8.5.5.3::[性別：1:男、2:女、3:不明], 
    othername: 1.2.392.200149.8.5.5.5::[住所：JIS 第 1 水準、第 2 水準、補助漢字以外の文字は代替文字に変換　全角ハイフン設定可能　最大文字数 200 文字], 
    othername: 1.2.392.200149.8.5.5.2::[利用者の氏名代替文字の使用位置情報：0 代替文字でない　1 代替文字], 
    othername: 1.2.392.200149.8.5.5.6::[利用者の住所代替文字の使用位置情報：0 代替文字でない　1 代替文字]
```

1次情報では [署名用認証局の運営に関する情報 | 公的個人認証サービス ポータルサイト](https://www.jpki.go.jp/ca/ca_rules3.html) の [署名用認証局運用規程（PDF・574KB）](https://www.jpki.go.jp/ca/pdf/sign_cps.pdf) (PDF内のタイトル：公的個人認証サービス 署名用認証局 運用規程 第 2.1 版 2021 年 9 月 1 日) の「1.2. 文書名と識別」に OID (Object Identifier) について記載があったのですが、 1.2.392.200149.8.5.1.1.X のみで上の 1.2.392.200149.8.5.5.X については記載なしでした。

このファイルのp.12 (PDFのページではp.17) の「3. 識別と認証」の表にsubjectAltName, commonName, dataOfBirth, gender, address について説明がありました。次のページの「3.1.7. 署名用電子証明書の拡張領域に記録する名称の種類と形式」と「3.1.8. 署名用電子証明書の拡張領域に記録する名称の記録方法に関する規則」に使用する文字種についての説明がありました。

## 鍵用途

```
$ openssl x509 -noout -ext keyUsage -in CertUserSign*.cer
X509v3 Key Usage: critical
    Digital Signature, Non Repudiation
```

```
$ openssl x509 -noout -ext keyUsage -in CertUserAuth*.cer
X509v3 Key Usage: critical
    Digital Signature
```

[RFC 5280: Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile](https://www.rfc-editor.org/rfc/rfc5280.html) の [4.2.1.3.  Key Usage](https://www.rfc-editor.org/rfc/rfc5280#section-4.2.1.3) に KeyUsage の値が書かれていました。

```
      KeyUsage ::= BIT STRING {
           digitalSignature        (0),
           nonRepudiation          (1), -- recent editions of X.509 have
                                -- renamed this bit to contentCommitment
           keyEncipherment         (2),
           dataEncipherment        (3),
           keyAgreement            (4),
           keyCertSign             (5),
           cRLSign                 (6),
           encipherOnly            (7),
           decipherOnly            (8) }
```

digitalSignature とnonRepudiation の説明を引用します。

```
      The digitalSignature bit is asserted when the subject public key
      is used for verifying digital signatures, other than signatures on
      certificates (bit 5) and CRLs (bit 6), such as those used in an
      entity authentication service, a data origin authentication
      service, and/or an integrity service.

      The nonRepudiation bit is asserted when the subject public key is
      used to verify digital signatures, other than signatures on
      certificates (bit 5) and CRLs (bit 6), used to provide a non-
      repudiation service that protects against the signing entity
      falsely denying some action.  In the case of later conflict, a
      reliable third party may determine the authenticity of the signed
      data.  (Note that recent editions of X.509 have renamed the
      nonRepudiation bit to contentCommitment.)
```

### 2022-11-06 追記。鍵用途もドキュメントに記載されていました。

[お問い合わせ | 公的個人認証サービス ポータルサイト](https://www.jpki.go.jp/contact/index.html) から署名用電子証明書と利用者証明用電子証明書の鍵用途についてもサイトに記載してほしいという要望を出していたのですが、 [公的個人認証サービス プロファイル仕様書 2.2 版](https://www.j-lis.go.jp/file/13_profile_genkou.pdf) に記載されているとご回答をいただきました。このドキュメントは [J-LIS 利用者クライアントソフトに係る技術仕様について](https://www.j-lis.go.jp/jpki/procedure/procedure1_2_3.html) からリンクされていました。


## X509v3 Issuer Alternative Name

署名用電子証明書と利用者証明用電子証明書の両方で以下のようになっていました。

```
$ openssl x509 -noout -ext issuerAltName -in CertUserSign*.cer
X509v3 Issuer Alternative Name:
    DirName:/C=JP/O=\xE5\x85\xAC\xE7\x9A\x84\xE5\x80\x8B\xE4\xBA\xBA\xE8\xAA\x8D\xE8\xA8\xBC\xE3\x82\xB5\xE3\x83\xBC\xE3\x83\x93\xE3\x82\xB9
```

```
$ openssl x509 -noout -ext issuerAltName -in CertUserAuth*.cer
X509v3 Issuer Alternative Name:
    DirName:/C=JP/O=\xE5\x85\xAC\xE7\x9A\x84\xE5\x80\x8B\xE4\xBA\xBA\xE8\xAA\x8D\xE8\xA8\xBC\xE3\x82\xB5\xE3\x83\xBC\xE3\x83\x93\xE3\x82\xB9
```

UTF-8文字列をエスケープした部分はデコードしてみると「公的個人認証サービス」でした。

## 認証局の自己署名証明書

以下のページに説明と証明書がありました。

* [署名用認証局の運営に関する情報 | 公的個人認証サービス ポータルサイト](https://www.jpki.go.jp/ca/ca_rules3.html)
* [利用者証明用認証局の運営に関する情報 | 公的個人認証サービス ポータルサイト](https://www.jpki.go.jp/ca/ca_rules4.html)
