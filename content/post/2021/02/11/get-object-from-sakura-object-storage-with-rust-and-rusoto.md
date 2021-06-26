---
title: "RustとRusotoを使ってさくらのクラウドのオブジェクトストレージAPIでオブジェクトを取得してみた"
date: 2021-02-11T09:52:45+09:00
---
## 2021-06-26 追記

2021-05-07 に [A New AWS SDK for Rust – Alpha Launch | AWS Developer Tools Blog](https://aws.amazon.com/blogs/developer/a-new-aws-sdk-for-rust-alpha-launch/) という記事が出て、今後は [awslabs/aws-sdk-rust](https://github.com/awslabs/aws-sdk-rust) に移行していくそうです。

今日確認したところでは
[rusoto/rusoto: AWS SDK for Rust](https://github.com/rusoto/rusoto) の README に Rusoto is in maintenance mode. と書かれていました。
一方、 [awslabs/aws-sdk-rust](https://github.com/awslabs/aws-sdk-rust) のほうは 
Please Note: The SDK is currently released as an alpha and is intended strictly for feedback purposes only. Do not use this SDK for production workloads.
と書かれていました。

## はじめに

[オブジェクトストレージ | さくらのクラウド ドキュメント](https://manual.sakura.ad.jp/cloud/manual-objectstorage.html) の
[オブジェクトストレージ サービス基本情報](https://manual.sakura.ad.jp/cloud/objectstorage/about.html#id6) を読んで
Rust と [rusoto/rusoto: AWS SDK for Rust](https://github.com/rusoto/rusoto) で
API 経由でオブジェクトを1つ取得してボディーを標準出力に出力する（テキスト形式のオブジェクトを想定しています）サンプルを書いてみたのでメモです。

この記事は個人的に検証してみただけのメモであって公式情報ではないです。

なお [オブジェクトストレージ サービス基本情報](https://manual.sakura.ad.jp/cloud/objectstorage/about.html#id6) に書かれているように2021年3月31日まではオープンベータです。

[オブジェクトストレージのAPI](https://manual.sakura.ad.jp/cloud/objectstorage/api.html) によると「オブジェクトストレージはAmazon S3互換APIを備えており」とのことなので今回は Rust と Rusoto で試してみました。

プロジェクトは [hnakamur/rusoto-s3-example: さくらのクラウドのオブジェクトストレージからRustとRusotoでオブジェクト取得するサンプル](https://github.com/hnakamur/rusoto-s3-example) に置きました。

## Rusoto について

[AWS’ sponsorship of the Rust project | AWS Open Source Blog](https://aws.amazon.com/jp/blogs/opensource/aws-sponsorship-of-the-rust-project/) に Rust で AWS を使うならコミュニティーで開発されている AWS SDK である [Rusoto](https://github.com/rusoto/rusoto) を使うと良いようなことが書かれていたのでこれを試すことにしました（他にもライブラリーあるかもしれませんが調べてないです）。

[rusoto - crates.io: Rust Package Registry](https://crates.io/crates/rusoto) を見ると This crate for Rusoto is deprecated. と書いてあってあれってなったんですが、 リンクされている [Release Rusoto 0.25.0](https://github.com/rusoto/rusoto/releases/tag/rusoto-v0.25.0) を見ると `rusoto_core` や `rusoto_credential` などの複数のクレートに分割されたという話でした。これは2017年と結構前で、今この記事を書いている2021-02-11時点では [Release Rusoto 0.46.0 · rusoto/rusoto](https://github.com/rusoto/rusoto/releases/tag/rusoto-v0.46.0) が最新です。

`rusoto_core` の `Cargo.toml` の `[dependencies]` を確認すると以下のように tokio 1.0 に対応していました。良いですね。

https://github.com/rusoto/rusoto/blob/rusoto-v0.46.0/rusoto/core/Cargo.toml#L38

```
tokio = { version = "1.0", features = ["time", "io-util"] }
```

## オブジェクト取得の例を書くための参考情報

[Example of reading from rusoto_s3::GetObjectOutput.body asynchronously? · Issue #1352 · rusoto/rusoto](https://github.com/rusoto/rusoto/issues/1352) というイシューによるとサンプルコードはないけどテストを見ると良いとコメントがあったのでテストコードを見ました。

また
[amazon s3 - How to save a file downloaded from S3 with Rusoto to my hard drive? - Stack Overflow](https://stackoverflow.com/questions/51287360/how-to-save-a-file-downloaded-from-s3-with-rusoto-to-my-hard-drive)
もかなり参考になりました。

## さくらのクラウドのオブジェクストストレージ用に変えた箇所

[rusoto_core::Region](https://docs.rs/rusoto_core/0.46.0/rusoto_core/enum.Region.html) のドキュメントの
[AWS-compatible services](https://docs.rs/rusoto_core/0.46.0/rusoto_core/enum.Region.html#aws-compatible-services) に書かれているように `Region::Custom` を使ってリージョン名とエンドポイントの URL を指定すれば OK でした。

リージョン名は
[オブジェクトストレージのAPI | さくらのクラウド ドキュメント](https://manual.sakura.ad.jp/cloud/objectstorage/api.html)
には説明が見当たらないですが、とりあえず `us-east-1` を指定してみたら大丈夫でした。が、あくまで今回行けたというだけで今後もこれで大丈夫かは不明です。

エンドポイント URL は今回のサンプルでは `https://s3.isk01.sakurastorage.jp` としました。
[オブジェクトストレージ サービス基本情報](https://manual.sakura.ad.jp/cloud/objectstorage/about.html#id6) の [サイトの作成](https://manual.sakura.ad.jp/cloud/objectstorage/about.html#id24) を見るとサイト作成後にエンドポイントが作成されるとのことなので、本番運用する場合はコントロールパネルで確認したエンドポイントURLを指定するような方式にすべきです。
今回はサンプルなのでハードコーディングしています。

## オブジェクトのキー指定の際は先頭に / はつけない

例えば `/index.html` なら `index.html` とします。

## サンプルコード

`src/main.rs` は以下の通りです。

```rust
use anyhow::{Context, Result};
use rusoto_core::credential::ProfileProvider;
use rusoto_core::Region;
use rusoto_s3::{GetObjectOutput, GetObjectRequest, S3Client, S3};
use tokio::io;

const SAKURA_OBJECT_STORAGE_ENDPOINT: &str = "https://s3.isk01.sakurastorage.jp";

fn sakura_object_storage_region(endpoint: String) -> Region {
    Region::Custom {
        name: String::from(Region::UsEast1.name()),
        endpoint: endpoint,
    }
}

async fn get_object(region: Region, bucket_name: String, key: String) -> Result<GetObjectOutput> {
    let s3 = S3Client::new_with(
        rusoto_core::request::HttpClient::new()?,
        ProfileProvider::new()?,
        region,
    );
    let get_obj_req = GetObjectRequest {
        bucket: bucket_name,
        key: key,
        ..Default::default()
    };
    s3.get_object(get_obj_req)
        .await
        .context("get object from object storage")
}

#[tokio::main]
async fn main() {
    let region = sakura_object_storage_region(String::from(SAKURA_OBJECT_STORAGE_ENDPOINT));
    let bucket_name = String::from("gh-action-test");
    let key = String::from("index.html");
    let mut output = get_object(region, bucket_name, key).await.unwrap();
    let body = output.body.take().expect("The object has no body");
    let mut body = body.into_async_read();
    io::copy(&mut body, &mut tokio::io::stdout()).await.unwrap();
}
```
