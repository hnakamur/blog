---
title: "AWS SigV4のCのライブラリを見つけた"
date: 2023-01-10T22:44:43+09:00
---

AWS SigV4のCのライブラリを見つけたというメモです。

レポジトリは[aws/SigV4-for-AWS-IoT-embedded-sdk: AWS library to sign AWS HTTP requests with Signature Version 4 Signing Process.](https://github.com/aws/SigV4-for-AWS-IoT-embedded-sdk)でorganizationがawsなので公式ライブラリです。

[Reference examples](https://github.com/aws/SigV4-for-AWS-IoT-embedded-sdk#reference-examples)からリンクされている[HTTP demos](https://github.com/aws/aws-iot-device-sdk-embedded-C/tree/main/demos/http)にサンプルコードがあるとのことでちらっと見てみました。

[http_demo_s3_download.c#L1383-L1411](https://github.com/aws/aws-iot-device-sdk-embedded-C/blob/c70269486b3fdcb6d6e85e999059d0bd35e732cd/demos/http/http_demo_s3_download/http_demo_s3_download.c#L1383-L1411)あたりが主な部分のようです。

私としてはAWS S3互換の他のオブジェクトストレージでも使えるのか、つまり、エンドポイントやリージョンが変更できるかが気になるところです。

[http_demo_s3_download.c#L106-L109](https://github.com/aws/aws-iot-device-sdk-embedded-C/blob/c70269486b3fdcb6d6e85e999059d0bd35e732cd/demos/http/http_demo_s3_download/http_demo_s3_download.c#L106-L109)を見ると`AWS_S3_BUCKET_REGION`をビルド時に渡すようになっています。

[http_demo_s3_download.c#L162-L167](https://github.com/aws/aws-iot-device-sdk-embedded-C/blob/c70269486b3fdcb6d6e85e999059d0bd35e732cd/demos/http/http_demo_s3_download/http_demo_s3_download.c#L162-L167)では`AWS_S3_BUCKET_REGION`を参照して`AWS_S3_ENDPOINT`というのを定義しています。

[http_demo_s3_download.c#L528-L542](https://github.com/aws/aws-iot-device-sdk-embedded-C/blob/c70269486b3fdcb6d6e85e999059d0bd35e732cd/demos/http/http_demo_s3_download/http_demo_s3_download.c#L528-L542)で`SigV4Parameters_t sigv4Params`の値を設定する際に`AWS_S3_BUCKET_REGION`を参照しているのでリージョンの値は変更できそうです。

`AWS_S3_ENDPOINT`のほうは`connectToS3Server`という関数内の[http_demo_s3_download.c#L936-L937](https://github.com/aws/aws-iot-device-sdk-embedded-C/blob/c70269486b3fdcb6d6e85e999059d0bd35e732cd/demos/http/http_demo_s3_download/http_demo_s3_download.c#L936-L937)で参照していて接続先の指定に使っているだけのようなのでこちらも変更できそうです。

[署名バージョン 4 を使用した AWS リクエストへの署名 - AWS 全般のリファレンス](https://docs.aws.amazon.com/ja_jp/general/latest/gr/sigv4_signing.html)と[タスク 3: AWS 署名バージョン 4 の署名を計算する - AWS 全般のリファレンス](https://docs.aws.amazon.com/ja_jp/general/latest/gr/sigv4-calculate-signature.html)を見ても署名の計算の際にリージョンは使っていますが、エンドポイントは使ってないのでやはり大丈夫そうです。
