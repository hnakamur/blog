+++
Categories = []
Description = ""
Tags = ["rust", "rustfmt"]
date = "2015-07-19T00:33:15+09:00"
title = "OSX上でmultirustを使ったrustfmtのインストール手順"

+++
OSXでは[building cargo atop multirust fails, dyn link problems (Mac OS X) · Issue #43 · brson/multirust](https://github.com/brson/multirust/issues/43)のイシューの[コメント106758695](https://github.com/brson/multirust/issues/43#issuecomment-106758695)にあるように `rustfmt` の実行時に環境変数 `DYLD_LIBRARY_PATH` を設定する必要があります。

そこで、 `rustfmt` の実行ファイルを `~/bin/rustfmt.bin` と別の名前にして、起動用のスクリプトを `~/bin/rustfmt` として作成します。

インストール手順は以下のとおりです。

```
git clone https://github.com/nrc/rustfmt
cd rustfmt
cargo build --release
cp target/release/rustfmt ~/bin/rustfmt.bin
cat <<'EOF' > ~/bin/rustfmt
#!/bin/sh
DYLD_LIBRARY_PATH="$HOME/.multirust/toolchains/nightly/lib" $HOME/bin/rustfmt.bin "$@"
EOF
```
