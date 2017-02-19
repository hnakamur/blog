Title: GeForce搭載の旧モデルMacBook ProでCUDAをセットアップする手順のメモ
Date: 2015-07-25 17:37
Category: blog
Tags: cuda
Slug: 2015/07/25/setup_cuda_on_macbook_pro_with_geforce

## はじめに
[MacBook Pro現行モデルの技術仕様](http://www.apple.com/jp/macbook-pro/specs-retina/)を見ると最上位機種のグラフィックスチップはIntel Iris Pro GraphicsとAMD Radeon R9 M370Xとなっており、NVIDIA GeForceは搭載されていません。

ですが、[MacBook Pro (15-inch, Mid 2012) - 技術仕様](https://support.apple.com/kb/SP694?locale=ja_JP&viewlocale=ja_JP)を見ると、私が持っているMacBook Proは15インチ2.6GHzモデルなのでNVIDIA GeForce GT 650M、1GB GDDR5メモリが搭載されています。

[GeForce GT 650M | NVIDIA](http://www.nvidia.co.jp/object/geforce-gt-650m-jp.html#pdpContent=2)には「プログラミング環境」の行に「CUDA」とあるのでCUDAが使えるようです。

ということでCUDAを試してみたので、手順をメモしておきます。試した時のOS Xのバージョンは10.10.4、Xcodeのバージョンは6.4です。

## CUDAドライバのインストールとアップデート

後述のCUDAツールキットのインストール中の画面にCUDAドライバも含まれているような記述があったので、この手順は不要かもしれません。が、今回はそれを知らずに先にCUDAドライバを単体でインストールしたので、一応書いておきます。

[MAC アーカイブ用CUDA ドライバ | NVIDIA](http://www.nvidia.co.jp/object/mac-driver-archive-jp.html)から最新のドライバをダウンロード、インストールします。

[NVIDIA DRIVERS 7.0.36](http://www.nvidia.co.jp/object/macosx-cuda-7.0.36-driver-jp.html)の「リリースハイライト」によると、[システム環境設定]→[CUDA]でインストール済みのCUDAドライバのバージョンと最新バージョンの確認が出来て、アップデートもできるそうです。

早速確認してみると、インストール済みのCUDA Driver Versionは7.0.29となっており、CUDA 7.0.52 Driver update is availableと表示されていました。

7.0.36のドライバを単体でインストールしたのに7.0.29になっているのは後述のCUDAツールキットのインストールで上書きされたのだと思われます。ついでなので、[Install CUDA Update]ボタンを押してアップデートしておきました。

## CUDAツールキットのインストール

[CUDA Toolkit Documentation](http://docs.nvidia.com/cuda/index.html#axzz3gt2fIbGh)のページから[Getting Started Mac OS X](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#axzz3gt2fIbGh)に進み、[3. Installation](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#installation)を参考にCUDAツールキットをインストールしました。

[CUDA 7 Downloads](https://developer.nvidia.com/cuda-downloads)で[Mac OSX]のタブに切り替えてインストーラをダウンロードします。最初Network Installerを試したのですが、ダウンロードしたdmgファイルを開いてCUDAMacOSXInstallerをダブルクリックしたら「“CUDAMacOSXInstaller”はこわれているため開けません。」というエラーが出たので、Local Installer (977MB)を試したら、こちらは無事インストール出来ました。

その後、cuFFT Patchをダウンロードして、[README](http://developer.download.nvidia.com/compute/cuda/7_0/Prod/cufft_update/README_mac.txt)を参考にターミナルで以下のコマンドを実行してパッチを適用しました。

```
sudo tar zxf ~/Downloads/cufft_patch_mac.tar.gz -C /Developer/NVIDIA/CUDA-7.0
```

### CUDAツールキット用の環境変数設定

[Getting Started Mac OS X](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#axzz3gt2fIbGh)の[3.2. Install](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#install)で環境変数 `PATH` と `DYLD_LIBRARY_PATH` の設定方法が書いてあるのですが、この通りだとあとでPyCUDAをインストールするときに `-lcuda` が見つからずリンクエラーになりました。

検索してみると[Issue 248 - pyrit - Build script can't find CUDA library directory on OS X. - WPA/WPA2-PSK and a world of affordable many-core platforms - Google Project Hosting](https://code.google.com/p/pyrit/issues/detail?id=248) で `/usr/local/cuda` というディレクトリがあることを知り、`/usr/local/cuda/lib` と `/Developer/NVIDIA/CUDA-7.0/lib` の中身を見てみると `libcuda.dylib` だけは前者にしか無いことが判明しました。

結局以下のように設定する必要がありました (bash以外の場合は適宜変更してください)。

```
echo <<'EOF' >> ~/.bash_profile
# CUDA
export CUDA_ROOT=/usr/local/cuda
export PATH=$CUDA_ROOT/bin:$PATH
export DYLD_LIBRARY_PATH=$CUDA_ROOT/lib:$PATH
EOF
```

設定ファイルを書き換えたら以下のコマンドでシェルを再起動して設定を読み込んでおきます。

```
exec $SHELL -l
```

### 統合GPUではなくGeForceを使うように切り替える設定

[Getting Started Mac OS X](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#axzz3gt2fIbGh)の[3.2. Install](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#install)の説明に従って、以下のように設定しました。

* [システム環境設定]→[省エネルギー]を開きます
* [グラフィックスの自動切り替え]のチェックを外します
* 電源アダプタに繋いでいる場合は[電源アダプタ]、繋いでいない場合は[バッテリー]を選びます
* [コンピュータのスリープ]のスライダーを[しない]に調節します。


## CUDAのサンプルを試す

[Getting Started Mac OS X](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#axzz3gt2fIbGh)の[3.2. Install](http://docs.nvidia.com/cuda/cuda-getting-started-guide-for-mac-os-x/index.html#install)の説明に従って、 `cuda-install-samples-7.0.sh` を使ってサンプルプログラムを取得して試してみました。

`~/sandbox/cuda` という作業用のディレクトリを作って以下の手順で試しました。 `cuda-install-samples-7.0.sh` はインストール先のディレクトリを引数で指定する必要がありました。

```
mkdir -p ~/sandbox/cuda
cd !$
cuda-install-samples-7.0.sh .
```

実行すると `NVIDIA_CUDA-7.0_Samples` というディレクトリが作成され、配下にサンプルプログラムのソースファイルが展開されていました。

そのうちの1つ `asyncAPI` というのを試してみました。以下の手順でビルドします。

```
cd NVIDIA_CUDA-7.0_Samples/0_Simple/asyncAPI
make
```

実行してみました。

```
$ ../../bin/x86_64/darwin/release/asyncAPI
[../../bin/x86_64/darwin/release/asyncAPI] - Starting...
GPU Device 0: "GeForce GT 650M" with compute capability 3.0

CUDA device [GeForce GT 650M]
time spent executing by the GPU: 99.45
time spent by CPU in CUDA calls: 0.05
CPU executed 583004 iterations while waiting for GPU to finish
```

動きました！
