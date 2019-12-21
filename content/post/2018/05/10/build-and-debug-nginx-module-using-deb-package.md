+++
title="debパッケージを使ってnginxモジュールをビルド・デバッグする"
date = "2018-05-10T09:25:00+09:00"
tags = ["deb", "nginx", "gdb"]
categories = ["blog"]
+++


# はじめに

私は [私のnginxのカスタムrpmとdebをビルドする手順](https://hnakamur.github.io/blog/2018/04/05/building-my-custom-nginx-rpm-and-deb/) でサードパーティモジュールを含んだnginxのパッケージをビルドしています。

このパッケージに自作モジュールを追加して開発するためのビルド手順を考えてみたのでメモです。

普通にソースのtarballを展開してconfigure, make, make installでも良いのですが、本番運用時はdebパッケージを使うので同じ構成のほうが良いというのとnginx-dbgというデバッグシンボルパッケージも作ってくれるのでこれも活用したいということで、以下の手順にしてみました。

例として [nginx moduleをつくろう その1〜Hello, World〜 - bokko bokkoにしてやんよ](http://cubicdaiya.github.io/blog/ja/blog/2013/01/08/nginx1/) の [cubicdaiya/ngx_http_hello_world: Hello, World with nginx](https://github.com/cubicdaiya/ngx_http_hello_world) を使わせて頂きました。

# セットアップ手順

## LXDコンテナ作成

ホストの環境を汚したくないので、開発用にLXDのコンテナを作ってそこで作業します。

```console
lxc launch images:ubuntu/18.04 nginx-dev
lxc exec nginx-dev bash
```

ここ以降は全てコンテナ内で実行します。 `lxc exec` ではコンテナ内で root ユーザになっているので `sudo` は使いません。また、以下のコマンド実行例でプロンプトを示す場合はrootユーザということで `#` とします。

## ビルドに必要なパッケージをインストール

debパッケージのビルドに必要なツールをインストールします。 `equivs` は後述の `mk-build-deps` コマンドで必要になります。

```console
apt install build-essential devscripts equivs
```

## 自作debパッケージのソースを取得

```console
git clone https://github.com/hnakamur/nginx-deb
cd nginx-deb
```

## hello_worldモジュールのソースを取得

gitサブモジュールとして追加します。

```console
git submodule add https://github.com/cubicdaiya/ngx_http_hello_world
```

## hello_worldモジュール開発用にdebパッケージのファイルを編集

#### debian/rules

`debian/rules` は1行目に `#!/usr/bin/make -f` と書いてあるので Makefile の書式になっています。
通常の Makefile なら `make ターゲット` と実行するところを `./debian/rules ターゲット` で実行できます。

hello_worldモジュールをビルドするために以下の2つの変更を行います。

* リリースビルドとデバッグビルドのソースをビルド用のディレクトリにコピーするためのターゲット `config.env.%`
* リリースビルドとデバッグビルドのconfigureのオプションにhello_worldをダイナミックモジュールとしてビルドするためのオプションを追加。

さらにhello_worldモジュールを変更・ビルド・動作確認のサイクルを効率化するために以下の2つの変更を行います。
ビルドディレクトリを残したままhello_worldモジュールのソースのみをビルドディレクトリに上書きコピーしてdebパッケージを作るための変更です。

* hello_worldモジュールのソースだけをビルドディレクトリにコピーするためのmakeターゲット `copy_hello_src` を追加し、 `.PHONY` に `copy_hello_src` を追加。
* post-build と install ターゲットでシンボリックリンク作成する際に `-f` オプションを追加して、リンクが既にあってもエラーにならないようにする。

```diff
diff --git a/debian/rules b/debian/rules
index c97ab1a..3eef083 100755
--- a/debian/rules
+++ b/debian/rules
@@ -50,8 +50,14 @@ config.env.%:
        cp -Pa $(CURDIR)/redis2-nginx-module $(BUILDDIR_$*)/
        cp -Pa $(CURDIR)/set-misc-nginx-module $(BUILDDIR_$*)/
        cp -Pa $(CURDIR)/srcache-nginx-module $(BUILDDIR_$*)/
+	cp -Pa $(CURDIR)/ngx_http_hello_world $(BUILDDIR_$*)/
        touch $@
 
+copy_hello_src.%:
+	cp -Pa $(CURDIR)/ngx_http_hello_world $(BUILDDIR_$*)/
+
+copy_hello_src: copy_hello_src.nginx copy_hello_src.nginx_debug
+
 config.status.nginx: config.env.nginx
        cd $(BUILDDIR_nginx) && \
        CFLAGS="" ./configure \
@@ -114,6 +120,7 @@ config.status.nginx: config.env.nginx
                --add-dynamic-module=./redis2-nginx-module \
                --add-dynamic-module=./set-misc-nginx-module \
                --add-dynamic-module=./srcache-nginx-module \
+		--add-dynamic-module=./ngx_http_hello_world \
                --with-cc-opt="$(CFLAGS)" \
                --with-ld-opt="$(LDFLAGS)"
        touch $@
@@ -180,6 +187,7 @@ config.status.nginx_debug: config.env.nginx_debug
                --add-dynamic-module=./redis2-nginx-module \
                --add-dynamic-module=./set-misc-nginx-module \
                --add-dynamic-module=./srcache-nginx-module \
+		--add-dynamic-module=./ngx_http_hello_world \
                --with-cc-opt="$(CFLAGS)" \
                --with-ld-opt="$(LDFLAGS)" \
                --with-debug
@@ -221,7 +229,7 @@ clean:
 
 post-build:
        mv $(BUILDDIR_nginx_debug)/objs/nginx $(BUILDDIR_nginx_debug)/objs/nginx-debug
-	ln -s $(BUILDDIR_nginx)/objs $(CURDIR)/objs
+	ln -sf $(BUILDDIR_nginx)/objs $(CURDIR)/objs
        cp $(BUILDDIR_nginx)/objs/nginx.8 $(BUILDDIR_nginx)/objs/nginx-debug.8
 
 install:
@@ -235,7 +243,7 @@ install:
        mkdir -p $(INSTALLDIR)/usr/share/doc/nginx
        install -m 644 debian/CHANGES $(INSTALLDIR)/usr/share/doc/nginx/changelog
        install -m 644 debian/nginx.vh.default.conf $(INSTALLDIR)/etc/nginx/conf.d/default.conf
-	ln -s /usr/lib/nginx/modules $(INSTALLDIR)/etc/nginx/modules
+	ln -sf /usr/lib/nginx/modules $(INSTALLDIR)/etc/nginx/modules
 
 binary-indep: build post-build install
        dh_testdir
@@ -272,4 +280,4 @@ binary-arch: install build-dbg
 
 binary: binary-indep binary-arch
 
-.PHONY: build clean binary-indep binary-arch binary install
+.PHONY: build clean binary-indep binary-arch binary install copy_hello_src
```

#### debian/nginx.install

ビルドしたhello_worldモジュールをdebパッケージに含めるために以下のように変更します。

```diff
diff --git a/debian/nginx.install b/debian/nginx.install
index 7f2825a..f692042 100644
--- a/debian/nginx.install
+++ b/debian/nginx.install
@@ -16,6 +16,7 @@ objs/ngx_http_echo_module.so		usr/lib/nginx/modules
 objs/ngx_http_enhanced_memcached_module.so	usr/lib/nginx/modules
 objs/ngx_http_geoip_module.so		usr/lib/nginx/modules
 objs/ngx_http_headers_more_filter_module.so	usr/lib/nginx/modules
+objs/ngx_http_hello_world_module.so	usr/lib/nginx/modules
 objs/ngx_http_image_filter_module.so	usr/lib/nginx/modules
 objs/ngx_http_lua_upstream_module.so	usr/lib/nginx/modules
 objs/ngx_http_memc_module.so		usr/lib/nginx/modules
```

#### debian/nginx.conf

`/etc/nginx/nginx.conf` で hello_world モジュールをロードするように以下のように変更します。
なお、後述のgdbでワーカープロセスのプロセスにアタッチしてデバッグする場合は、以下のように `worker_processes` は 1 にしておくのが楽です。

```diff
diff --git a/debian/nginx.conf b/debian/nginx.conf
index e4bad8d..e89be3d 100644
--- a/debian/nginx.conf
+++ b/debian/nginx.conf
@@ -2,6 +2,8 @@
 user  nginx;
 worker_processes  1;
 
+load_module modules/ngx_http_hello_world_module.so;
+
 error_log  /var/log/nginx/error.log warn;
 pid        /var/run/nginx.pid;
```

#### debian/nginx.vh.default.conf

`/etc/nginx/conf.d/default.conf` に hello_world モジュールをテストするためのロケーションを追加するため以下のように変更します。

```diff
diff --git a/debian/nginx.vh.default.conf b/debian/nginx.vh.default.conf
index 299c622..6f856d7 100644
--- a/debian/nginx.vh.default.conf
+++ b/debian/nginx.vh.default.conf
@@ -10,6 +10,10 @@ server {
         index  index.html index.htm;
     }
 
+    location ~ /hello_world$ {
+        hello_world;
+    }
+
     #error_page  404              /404.html;
 
     # redirect server error pages to the static page /50x.html
```

#### debian/control

今回は不要ですが、ビルド時の依存ライブラリが増える場合は `debian/control` の `Build-Depends` に追加します。

## 依存ライブラリのインストール

`mk-build-deps` コマンドを使って依存ライブラリをインストールするためのdebパッケージを作成します。

```console
# mk-build-deps debian/control
…(略)…
dpkg-deb: building package 'nginx-build-deps' in '../nginx-build-deps_1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04_all.deb'.

The package has been created.
Attention, the package has been created in the current directory,
not in ".." as indicated by the message above!
```

上記のように作成されたdebパッケージ名が表示されるので、それを指定してインストールします。
最後の3行で説明されているように親ディレクトリ `..` ではなくカレントディレクトリ `.` に作られているので以下のようにします。

```console
dpkg -i ./nginx-build-deps_1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04_all.deb
```

これでこのパッケージ自体はインストールされるのですが、依存ライブラリはまだインストールされていない状態です。

[How to let \`dpkg -i\` install dependencies for me? - Ask Ubuntu](https://askubuntu.com/questions/40011/how-to-let-dpkg-i-install-dependencies-for-me?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa) を参考に以下のようにしてインストールします。

```console
apt install -f -y
```

# 初回のビルドと動作確認

初回のビルドは通常通り行います。

```console
# dpkg-buildpackage -b
…(略)…
dpkg-deb: building package 'nginx' in '../nginx_1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04_amd64.deb'.
dpkg-deb: building package 'nginx-dbg' in '../nginx-dbg_1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04_amd64.deb'.
…(略)…
```

作成されたdebパッケージのファイル名が表示されるので、これを指定してインストールします。
ここでは手抜きしてワイルドカードで指定します。この手順どおりでは無いはずですが、もし親ディレクトリにこれでマッチする他のファイルがある場合は上記の2つのファイルだけがマッチするように指定してください。

```console
dpkg -i ../nginx*.deb
```

nginxのサービスを起動します。

```console
systemctl start nginx
```

`/hello_world` のロケーションにアクセスして動作確認します。

```console
# curl localhost/hello_world
Hello, World!
```

# 2回め以降のビルドと動作確認

初回のビルドが終わると `debian/build-nginx` にリリースビルド、 `debian/build-nginx-debug` にデバッグビルドのソースとビルド結果が残っています。

hello_world モジュールのソースを変更してビルド、インストール、動作確認をしてみます。

## hello_world モジュールのソース変更

`vim ngx_http_hello_world/ngx_http_hello_world_module.c` でソースを変更します。

なお `ngx_http_hello_world` はgitサブモジュールにした関係で、差分を表示するときは `git diff ngx_http_hello_world/ngx_http_hello_world_module.c` ではなく以下のようにする必要がありました（サブシェルで実行しているのはカレントディレクトリを移動したくないため）。

```console
(cd ngx_http_hello_world/; git diff)
```

.. code-block:: diff

	diff --git a/ngx_http_hello_world_module.c b/ngx_http_hello_world_module.c
	index 2760468..6a84d12 100644
	--- a/ngx_http_hello_world_module.c
	+++ b/ngx_http_hello_world_module.c
	@@ -6,7 +6,7 @@
	 #include <ngx_core.h>
	 #include <ngx_http.h>

	-#define NGX_HTTP_HELLO_WORLD "Hello, World!\n"
	+#define NGX_HTTP_HELLO_WORLD "Hello, World!!\n"

	 static char *ngx_http_hello_world(ngx_conf_t *cf, ngx_command_t *cmd, void *conf);
	 static ngx_int_t ngx_http_hello_world_handler(ngx_http_request_t *r);

## ビルド、インストール、動作確認

ソース変更とビルド、インストール、動作確認は繰り返し行うので以下のように `&&` で繋いで一連で実行するようにします。あるいはシェルスクリプトファイルを作って実行しても良いでしょう。

```console
./debian/rules copy_hello_src && \
  dpkg-buildpackage -nc && \
  dpkg -i --force-overwrite ../nginx_1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04_amd64.deb ../nginx-dbg_1.13.11+mod.1-1ubuntu1ppa2~ubuntu18.04_amd64.deb && \
  systemctl restart nginx && \
  curl -v localhost/hello_world
```

`curl` の実行結果は以下のようになり、上記の変更がただしく反映されたことを確認できました。

```text
*   Trying ::1...
* TCP_NODELAY set
* connect to ::1 port 80 failed: Connection refused
*   Trying 127.0.0.1...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 80 (#0)
> GET /hello_world HTTP/1.1
> Host: localhost
> User-Agent: curl/7.58.0
> Accept: */*
>
< HTTP/1.1 200 OK
< Server: nginx/1.13.11
< Date: Thu, 10 May 2018 01:59:43 GMT
< Content-Type: text/plain
< Content-Length: 15
< Connection: keep-alive
<
Hello, World!!
```

# デバッガの実行

ついでにデバッガで実行する手順もメモしておきます。

gdbの操作方法は公式ドキュメントのページ  [GDB Documentation](http://www.gnu.org/software/gdb/documentation/) にあるGDB User Manualを参照してください。

まずgdbをインストールします。

```console
apt install gdb
```

リリースビルドのnginxのサービスを停止し、デバッグビルドのnginxのサービスを起動します。

```console
systemctl stop nginx && systemctl start nginx-debug
```

nginxのワーカープロセスのPIDを確認します。

```console
# ps auxwwf | grep [n]ginx
root     11380  0.0  0.0  43844   988 ?        Ss   02:21   0:00 nginx: master process /usr/sbin/nginx-debug -c /etc/nginx/nginx.conf
nginx    11381  0.0  0.0  48664  4744 ?        S    02:21   0:00  \_ nginx: worker process
```

デバッグビルドのnginxのソースディレクトリとnginxワーカープロセスのPIDを指定してgdbを起動してワーカープロセスにアタッチします。 [既に起動しているプロセスをgdbで制御する:Geekなぺーじ](http://www.geekpage.jp/blog/?id=2007/1/17) にわかりやすい解説がありました。

```console
gdb --directory debian/build-nginx-debug -p 11381
```

あるいはデバッグビルドのソースディレクトリに移動して実行しても良いです。

```console
cd debian/build-nginx-debug; gdb -p 11381
```

起動すると以下のようなメッセージが出力された後、gdbのプロンプトが出力されます。

PID 11381のプロセスにアタッチし、nginx-debugのシンボルが読み込めたことがわかります。
一方 `epoll_wait.c` が無いので `epoll_wait` のシンボル情報は読み込めていませんが、ここをデバッガで追わない場合は無視して構いません。デバッガで負いたい場合は対応するデバッグパッケージをインストールすれば良いはずです。

nginx-debugのシンボルは

```text
…(略)…
Attaching to process 11381
Reading symbols from /usr/sbin/nginx-debug...Reading symbols from /usr/lib/debug/.build-id/92/48720f057ba2391859b2bade2edabb6f050487.debug...done.
done.
…(略)…
0x00007fecd781fb77 in epoll_wait (epfd=8, events=0x55ca9383b300, maxevents=512, timeout=timeout@entry=-1)
    at ../sysdeps/unix/sysv/linux/epoll_wait.c:30
30      ../sysdeps/unix/sysv/linux/epoll_wait.c: No such file or directory.
(gdb)
```

[Useful commands in gdb](https://ccrma.stanford.edu/~jos/stkintro/Useful_commands_gdb.html) にgdbのよく使うコマンド一覧がありました。

gdbのプロンプトに `b ngx_http_hello_world/ngx_http_hello_world_module.c:ngx_http_hello_world_handler` と入力し、hello_worldモジュールの `ngx_http_hello_world_handler` 関数にブレークポイントを設定してみます。
以下のように、このあと共有ライブラリがロードされたらブレークポイントを設定するか聞かれるので `y` と入力します。

```text
(gdb) b ngx_http_hello_world/ngx_http_hello_world_module.c:ngx_http_hello_world_handler
No source file named ngx_http_hello_world/ngx_http_hello_world_module.c.
Make breakpoint pending on future shared library load? (y or [n]) y
Breakpoint 1 (ngx_http_hello_world/ngx_http_hello_world_module.c:ngx_http_hello_world_handler) pending.
```

念のためgdbのプロンプトに `i b` と入力してブレークポイントが設定されたことを確認します。

```text
(gdb) i b
Num     Type           Disp Enb Address            What
1       breakpoint     keep y   0x00007fecd67048f0 in ngx_http_hello_world_handler
						   at ./ngx_http_hello_world/ngx_http_hello_world_module.c:57
```

gdbのプロンプトに `c` を入力して処理を続行 (continue) します。

```text
(gdb) c
Continuing.
```

別の端末で `curl localhost/hello_world` と実行すると、gdbがブレークポイントで止まって以下のようにプロンプトが表示されます。

```text
Breakpoint 1, ngx_http_hello_world_handler (r=0x55ca9385efd0)
    at ./ngx_http_hello_world/ngx_http_hello_world_module.c:57
warning: Source file is more recent than executable.
57      {
(gdb)
```

ここで `C-x C-a` と入力すると画面が上下に分割され、上にソースコード、下にgdbのプロンプトが表示されます。
これはTUIモードと呼ばれるもので [Debugging with GDB: TUI](https://sourceware.org/gdb/current/onlinedocs/gdb/TUI.html#TUI) に説明があります。

```text
┌──./ngx_http_hello_world/ngx_http_hello_world_module.c────────────────────────────────────────────────────────────┐
│46          NULL,                             /* init master */                                                   │
│47          NULL,                             /* init module */                                                   │
│48          NULL,                             /* init process */                                                  │
│49          NULL,                             /* init thread */                                                   │
│50          NULL,                             /* exit thread */                                                   │
│51          NULL,                             /* exit process */                                                  │
│52          NULL,                             /* exit master */                                                   │
│53          NGX_MODULE_V1_PADDING                                                                                 │
│54      };                                                                                                        │
│55                                                                                                                │
│56      static ngx_int_t ngx_http_hello_world_handler(ngx_http_request_t *r)                                      │
```

	B+>│57      {                                                                                                         │
	   │58          ngx_int_t                    rc;                                                                      │
	   │59          ngx_chain_t                  out;                                                                     │
	   │60          ngx_buf_t                   *b;                                                                       │
	   │61          ngx_str_t                    body = ngx_string(NGX_HTTP_HELLO_WORLD);                                 │
	   │62                                                                                                                │
	   │63          if (r->method != NGX_HTTP_GET && r->method != NGX_HTTP_HEAD) {                                        │
	   │64              return NGX_HTTP_NOT_ALLOWED;                                                                      │
	   │65          }                                                                                                     │
	   │66                                                                                                                │
	   │67          if (r->headers_in.if_modified_since) {                                                                │
	   │68              return NGX_HTTP_NOT_MODIFIED;                                                                     │
	   │69          }                                                                                                     │
	   │70                                                                                                                │
	   └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
	multi-thre Thread 0x7fecd914b7 In: ngx_http_hello_world_handler                               L57   PC: 0x7fecd67048f0
	(gdb)

TUIモードのキー操作については [Debugging with GDB: TUI Keys](https://sourceware.org/gdb/current/onlinedocs/gdb/TUI-Keys.html#TUI-Keys) を参照してください。

gdbプロンプトで `C-x 2` と入力するとCとアセンブラのウィンドウが表示されます。

```text
┌──./ngx_http_hello_world/ngx_http_hello_world_module.c────────────────────────────────────────────────────────────┐
```

	B+>│57      {                                                                                                         │
	   │58          ngx_int_t                    rc;                                                                      │
	   │59          ngx_chain_t                  out;                                                                     │
	   │60          ngx_buf_t                   *b;                                                                       │
	   │61          ngx_str_t                    body = ngx_string(NGX_HTTP_HELLO_WORLD);                                 │
	   │62                                                                                                                │
	   │63          if (r->method != NGX_HTTP_GET && r->method != NGX_HTTP_HEAD) {                                        │
	   │64              return NGX_HTTP_NOT_ALLOWED;                                                                      │
	   │65          }                                                                                                     │
	   │66                                                                                                                │
	   │67          if (r->headers_in.if_modified_since) {                                                                │
	   │68              return NGX_HTTP_NOT_MODIFIED;                                                                     │
	   │69          }                                                                                                     │
	   └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
	B+>│0x7fecd67048f0 <ngx_http_hello_world_handler>           push   %rbx                                               │
	   │0x7fecd67048f1 <ngx_http_hello_world_handler+1>         sub    $0x20,%rsp                                         │
	   │0x7fecd67048f5 <ngx_http_hello_world_handler+5>         mov    %fs:0x28,%rax                                      │
	   │0x7fecd67048fe <ngx_http_hello_world_handler+14>        mov    %rax,0x18(%rsp)                                    │
	   │0x7fecd6704903 <ngx_http_hello_world_handler+19>        xor    %eax,%eax                                          │
	   │0x7fecd6704905 <ngx_http_hello_world_handler+21>        mov    0x3d0(%rdi),%rax                                   │
	   │0x7fecd670490c <ngx_http_hello_world_handler+28>        lea    -0x2(%rax),%rdx                                    │
	   │0x7fecd6704910 <ngx_http_hello_world_handler+32>        mov    $0x195,%eax                                        │
	   │0x7fecd6704915 <ngx_http_hello_world_handler+37>        test   $0xfffffffffffffffd,%rdx                           │
	   │0x7fecd670491c <ngx_http_hello_world_handler+44>        jne    0x7fecd6704930 <ngx_http_hello_world_handler+64>   │
	   │0x7fecd670491e <ngx_http_hello_world_handler+46>        cmpq   $0x0,0xb0(%rdi)                                    │
	   │0x7fecd6704926 <ngx_http_hello_world_handler+54>        mov    %rdi,%rbx                                          │
	   │0x7fecd6704929 <ngx_http_hello_world_handler+57>        mov    $0x130,%eax                                        │
	   │0x7fecd670492e <ngx_http_hello_world_handler+62>        je     0x7fecd6704950 <ngx_http_hello_world_handler+96>   │
	   └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
	multi-thre Thread 0x7fecd914b7 In: ngx_http_hello_world_handler                               L57   PC: 0x7fecd67048f0
        …(略)…
	(gdb)

`C-x o` でアクティブウィンドウを切り替えられます。押す度に、ソース、アセンブラ、コマンドと切り替わっていきます。あるいは `TUI-specific Commands](https://sourceware.org/gdb/current/onlinedocs/gdb/TUI-Commands.html#TUI-Commands) の `focus` コマンドを使って切り替えることもできます。ソースかアセンブラがアクティブな場合はウィンドウ枠が反転表示になります。

ソースかアセンブラのウィンドウがアクティブな時に、カーソルキーの上下か PgUp, PgDown キーを押すと前後のソースまたはアセンブリコードが見られます。

`wh` (winheightの省略形) コマンドでウィンドウの高さを調節できます。引数なしで実行すると使い方が表示されます。

```text
(gdb) wh
Usage: winheight <win_name> [+ | -] <#lines>
```

ウィンドウの名前と現在の高さを見るには `i win` (info winの省略形) を実行します。

```text
(gdb) i win
	src     (15 lines)
	asm     (16 lines)
	cmd     (11 lines)  <has focus>
```

例えば `src` ウィンドウの高さを30行にするなら `winheight src 30` 、現在の行数より5行広げるなら `winheight src +5` のようにします。

ソースだけの表示に戻すには `C-x 1` 、TUIモードを抜けるには `C-x a` を押します。

[Single Key Mode](https://sourceware.org/gdb/current/onlinedocs/gdb/TUI-Single-Key-Mode.html#TUI-Single-Key-Mode) というのも便利でした。
これを知るまでは [Continuing and Stepping](https://sourceware.org/gdb/current/onlinedocs/gdb/Continuing-and-Stepping.html#Continuing-and-Stepping) の `next` コマンドの省略形の `n` を使って `n` リターンを繰り返してステップ実行していました。
`C-x s` でシングルキーモードに入れば `n` だけでステップ実行できるので楽です。 `q` でシングルキーモードから抜けてgdbのプロンプトに戻ります。
