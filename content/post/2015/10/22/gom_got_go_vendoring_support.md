Title: mattn/gomにGoのvendoringサポートが追加されました
Date: 2015-10-22 01:22
Category: blog
Tags: go, vendoring, gom
Slug: 2015/10/22/gom_got_go_vendoring_support

以前[Go言語のDependency/Vendoringの問題と今後．gbあるいはGo1.5 | SOTA](http://deeeet.com/writing/2015/06/26/golang-dependency-vendoring/)を読んだのですが、その時は様子見にしていました。

しかし、仕事でGoを書くとなるとやはりVendoringは必要だろうと思い、遅ればせながら今回[gb](https://getgb.io/examples/getting-started/), [tools/godep](https://github.com/tools/godep), [mattn/gom](https://github.com/mattn/gom)を試してみました。

## gbの不満

[gb](https://getgb.io/examples/getting-started/)の例を見ると、自分のプロジェクトのトップディレクトリに `src/cmd` あるいは `src/github.com/ユーザID/プロジェクト名` というディレクトリを作ってそこにソースを置く必要があるようです。

[FAQ](http://getgb.io/faq/#cannot-build-src-root)にも[Why can't I place source in $PROJECT/src?](http://getgb.io/faq/#cannot-build-src-root)という項があるので、これは仕様のようです。

でもこれだと、自分のプロジェクトを他のプロジェクトで使いたい時に `go get` で使えないですよね。
FAQに "Can I use gb if I am working on a Go library?" とか "Copying code is gross! Can I use git submodules?" とかあるんですが、git submoduleにせよgit subtreeにせよ面倒だなと思いました。

## godepsの不満

[tools/godep](https://github.com/tools/godep) の"Go 1.5 vendor/ experiment"の項を読んで試してみたところ、`go build` が使用する環境変数 `GO15VENDOREXPERIMENT` を `export GO15VENDOREXPERIMENT=1` のように設定しておくと、そうでないときは `Godeps/_workspace/` に置かれる依存ライブラリが `vendor/` 以下に置かれるようになることがわかりました。

`vendor/` を `.gitignore` で除外してコミットしたいので、後から `Godeps/Godeps.json` から `vendor/` を再構成する必要があります。READMEには書いてないですが、 `godep get` でダウンロードして、 `godep save` で `vendor/` に反映できることがわかりました。

ただ、 `godep get` でダウンロードする先は環境変数 `GOPATH` で指しているディレクトリなんですよね。 `godep save` は `$GOPATH` から `vendor/` に反映するコマンドです。

ちなみに `godep restore` というコマンドもありますが、これは `vendor/` から `$GOPATH` に反映します。GoにVendoringサポートがなかったときは、これで `$GOPATH` に反映してから `go build` という手順も妥当な気がしますが、Vendoringがある今となってはグローバルの `$GOPATH` 配下は触らずに `vendor/` 以下を直接更新したいところです。

とりあえずイシュー[Download dependency to vendor/ directory with godep get when GO15VENDOREXPERIMENT=1 · Issue #299 · tools/godep](https://github.com/tools/godep/issues/299) を立ててみたところ、同じことを考えていたというコメントがついていました。

## gomならバッチリ！

[mattn/gom](https://github.com/mattn/gom)を見ると[Consider adding GO15VENDOREXPERIMENT support · Issue #51 · mattn/gom](https://github.com/mattn/gom/issues/51)というイシューがあったので、対応するコードを書いて [Support go15vendorexperiment by mattn · Pull Request #57 · mattn/gom](https://github.com/mattn/gom/pull/57)で追加修正の上マージしていただきました。

`gom install` では内部的に `go get` を呼び出しているので、ターゲットディレクトリを `vendor/` にしても `vendor/src/github.com/...` のように `src` フォルダが作られてしまいます。上の修正では対処療法的に `gom install` 内で `vendor/*` を `vendor/src/*` に移動して、終わったら `vendor/src/*` を `vendor/*` に移動して対応しています。

正確には最初の移動では `vendor/` 以下の `bin`, `pkg`, `src` は除外しています。

これで、 `export GO15VENDOREXPERIMENT=1` さえしておけば、 `gom install` で `$GOPATH` 配下は変更せずに直接 `vendor/` 以下を更新できるようになりました。

READMEには書いてないですが、 `gom lock` を実行すれば `Gomfile.lock` が作られて、以降の `gom install` では依存ライブラリのバージョンを正確に反映できます。

ということで、gomならバッチリ私の希望を満たしてくれることがわかりました。
mattnさん、便利なツールをありがとうございます！
