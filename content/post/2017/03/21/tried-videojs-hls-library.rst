video.jsのHLSライブラリを試してみた
###################################

:date: 2017-03-21 14:52
:tags: video video.js hls
:category: blog
:slug: 2017/03/21/tried-videojs-hls-library


はじめに
--------

`MPEG DASHを知る - Qiita <http://qiita.com/gabby-gred/items/c1a3dbe026f83dd7e1ff>`_ を見て、HTML5のvideoタグでHLSと `Dash-Industry-Forum/dash.js: A reference client implementation for the playback of MPEG DASH via Javascript and compliant browsers. <https://github.com/Dash-Industry-Forum/dash.js>`_ でMPEG DASHを試してみたところ、各ブラウザの対応状況は以下のような感じでした。

* iOSのSafari, iOSのChrome, Microsoft EdgeはHLSのみ対応。
* WindowsのChrome, FirefoxはMPEG DASHのみ対応。

いちいち動画を2セット用意するのは大変だよなーと思っていたら、 `videojs/video.js: Video.js - open source HTML5 & Flash video player <https://github.com/videojs/video.js>`_ 用に `videojs/videojs-contrib-hls: HLS library for video.js <https://github.com/videojs/videojs-contrib-hls>`_ というライブラリがあるのを見つけたので試してみました。

結論を先に書いておくと、上記の環境全てで無事に再生できました。

動画ファイルの分割
------------------

YouTube で :code:`license:cc0` で検索して見つけた `Creative Commons licences explained - YouTube <https://www.youtube.com/watch?v=4ZvJGV6YF6Y>`_ をFirefoxの `Video DownloadHelper :: Add-ons for Firefox <https://addons.mozilla.org/ja/firefox/addon/video-downloadhelper/>`_ で1280x720と640x480のmp4ファイルをダウンロードして試してみました。

分割にはUbuntu 16.04のffmpeg 2.8.11-0ubuntu0.16.04.1を使いました。

1280x720の動画は `FFMpeg HLS Video Transcoding Generating Partial Playlist - Stack Overflow <http://stackoverflow.com/questions/35444324/ffmpeg-hls-video-transcoding-generating-partial-playlist/35452686#35452686>`_ を参考に以下のようにして分割しました。

.. code-block:: console

    destdir=1280x720
    mkdir -p "$destdir"
    ffmpeg -y \
     -i Creative-Commons-licences-explained-1280x720.mp4 \
     -codec copy \
     -bsf h264_mp4toannexb \
     -map 0 \
     -f segment \
     -segment_time 10 \
     -segment_format mpegts \
     -segment_list "$destdir/playlist.m3u8" \
     -segment_list_type m3u8 \
     "$destdir/segment%03d.ts"

640x480の動画は同様にして実行すると以下のエラーが出ました。

.. code-block:: console

    Failed to open bitstream filter h264_mp4toannexb for stream 0 with codec copy: Invalid argument
    [mpegts @ 0x121e2c0] AAC bitstream not in ADTS format and extradata missing
    av_interleaved_write_frame(): Invalid data found when processing input
    frame=  302 fps=0.0 q=-1.0 Lsize=N/A time=00:00:12.21 bitrate=N/A    
    video:566kB audio:143kB subtitle:0kB other streams:0kB global headers:0kB muxing overhead: unknown
    Conversion failed!

エラーの内容はよくわかってないですが、対処療法としては音声だけ再エンコードすると分割できました。
オプションはググって見つけた `HTML5のvideoタグで利用するmp4の動画を作る時のTips - Qiita <http://qiita.com/joker1007/items/def9d58ddb00fafc936d>`_ を真似していますが、私はちゃんと理解していません。

.. code-block:: console

    destdir=640x360
    mkdir -p "$destdir"
    ffmpeg -y \
     -i Creative-Commons-licences-explained-640x360.mp4 \
     -vcodec copy \
     -strict -2 -acodec aac -b:a 256k \
     -flags +loop-global_header \
     -bsf h264_mp4toannexb \
     -map 0 \
     -f segment \
     -segment_time 10 \
     -segment_format mpegts \
     -segment_list "$destdir/playlist.m3u8" \
     -segment_list_type m3u8 \
     "$destdir/segment%03d.ts"

AACのエンコーダの選択
---------------------

`Fraunhofer FDK AAC - Hydrogenaudio Knowledgebase <http://wiki.hydrogenaud.io/index.php?title=Fraunhofer_FDK_AAC>`_ にAACのエンコーダおすすめトップ6が載っています。

Apple AACはソース非公開でLinuxでは使えず、Fraunhofer FDK AACはライセンスの関係で :code:`apt install` では使えず、Nero AACは開発終了とのことで、今回はffmpeg内蔵のAACエンコーダを使いました。

`HTML5のvideoタグで利用するmp4の動画を作る時のTips - Qiita <http://qiita.com/joker1007/items/def9d58ddb00fafc936d>`_ で :code:`-acodec libfaac -b:a 128k -flags +loop-global_header -map 0` の部分で :code:`libfaac` を :code:`aac` に変えて実行したら

.. code-block:: console

    The encoder 'aac' is experimental but experimental codecs are not enabled, add '-strict -2' if you want to use it.

というエラーが出ました。
そこで `Native FFmpeg AAC encoder <https://trac.ffmpeg.org/wiki/Encode/AAC#NativeFFmpegAACencoder>`_ を見て :code:`-strict -2` オプションをつけたら問題なく動きました。

ブラウザの幅に応じて動画の解像度自動選択
----------------------------------------

`VideoJS setup guide to scale for responsive design on all browsers & mobile <https://coolestguidesontheplanet.com/videodrome/videojs/>`_ を参考にして画面の幅一杯に動画を表示するようにしてみました。
動画の解像度の縦横比に合わせて :code:`video` タグの :code:`class` 属性に :code:`vjs-16-9` または :code:`vjs-4-3` 属性をつけるだけです。

せっかくなので、ブラウザの幅 (正確には :code:`video` タグの幅) に応じて再生する動画を自動的に選択するようにしてみました。
:code:`video` の子供の :code:`source` タグに :code:`data-width` 属性をつけておいて、 :code:`video` タグの幅と比較して選択するようにしています。

.. code-block:: html

    <link href="//vjs.zencdn.net/5.11/video-js.min.css" rel="stylesheet">

    <video id="example-video" class="video-js vjs-default-skin vjs-16-9 vjs-big-play-centered" controls
      preload="none" poster="poster-640x360.jpg">
      <source data-width="640" src="640x360/playlist.m3u8" type="application/x-mpegURL">
      <source data-width="1280" src="1280x720/playlist.m3u8" type="application/x-mpegURL">
    </video>
    <script src="//vjs.zencdn.net/5.11/video.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/videojs-contrib-hls/5.3.3/videojs-contrib-hls.min.js"></script>
    <script>
    var player = videojs('example-video');
    player.one("loadedmetadata", function() {
      var playerWidth = player.currentWidth();
      var sources = player.$$('source');
      var len = sources.length;
      for (var i = 0; i < len; i++) {
        var source = sources[i];
        var srcWidth = +source.getAttribute('data-width');
        if (playerWidth <= srcWidth || i === len - 1) {
          if (i > 0) {
            player.src({src: source.getAttribute('src'), type: source.getAttribute('type')});
            player.play();
          }
          break;
        }
      }
    });
    </script>

上記のHTMLで :code:`video` タグに :code:`autoplay` 属性を指定すれば自動再生もできました。

:code:`video` タグの幅が640px以下の時のアクセスログ
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HTMLファイルを表示した時点では :code:`/hls/640x360/playlist.m3u8` の行までで、その後再生ボタンを押すと以降のアクセスがあります。このケースでは無駄なアクセスはありません。

.. code-block:: text

    192.168.0.22 - - [21/Mar/2017:16:09:52 +0900] "GET /hls/ HTTP/1.1" 200 576 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:09:52 +0900] "GET /hls/poster-640x360.jpg HTTP/1.1" 200 23701 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:09:52 +0900] "GET /hls/640x360/playlist.m3u8 HTTP/1.1" 200 1222 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:09:55 +0900] "GET /hls/640x360/segment000.ts HTTP/1.1" 200 1098484 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:09:55 +0900] "GET /hls/640x360/segment001.ts HTTP/1.1" 200 824192 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:09:55 +0900] "GET /hls/640x360/segment002.ts HTTP/1.1" 200 658940 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:09:55 +0900] "GET /hls/640x360/segment003.ts HTTP/1.1" 200 875892 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"

:code:`video` タグの幅が640pxより大きいの時のアクセスログ
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HTMLファイルを表示した時点では :code:`/hls/640x360/playlist.m3u8` の行までで、その後再生ボタンを押すと以降のアクセスがあります。
このケースでは :code:`/hls/640x360/playlist.m3u8` と :code:`/hls/640x360/segment000.ts` へのアクセスは無駄です。
無駄な転送量をなるべく少なくしたいので :code:`video` タグの :code:`source` の並び順は解像度が小さいものから順に並べるようにしました。
遅い回線で画面が小さい時に、必要以上に解像度の大きな画像を無駄にダウンロードするのが一番無駄が大きいと思うので、そういう意味でも小さい順が良いと思いました。

.. code-block:: text

    192.168.0.22 - - [21/Mar/2017:16:11:01 +0900] "GET /hls/ HTTP/1.1" 200 576 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:01 +0900] "GET /hls/poster-640x360.jpg HTTP/1.1" 200 23701 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:02 +0900] "GET /hls/640x360/playlist.m3u8 HTTP/1.1" 200 1222 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:04 +0900] "GET /hls/640x360/segment000.ts HTTP/1.1" 200 1098484 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:04 +0900] "GET /hls/1280x720/playlist.m3u8 HTTP/1.1" 200 1196 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:04 +0900] "GET /hls/1280x720/segment000.ts HTTP/1.1" 200 1668876 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:05 +0900] "GET /hls/1280x720/segment001.ts HTTP/1.1" 200 1667372 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:05 +0900] "GET /hls/1280x720/segment002.ts HTTP/1.1" 200 1664364 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
    192.168.0.22 - - [21/Mar/2017:16:11:07 +0900] "GET /hls/1280x720/segment003.ts HTTP/1.1" 200 1651204 "http://192.168.0.201/hls/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"

多少無駄なアクセスが発生するものの一応これで切り替えは出来ました。
ただ `<video> - HTML | MDN <https://developer.mozilla.org/en-US/docs/Web/HTML/Element/video>`_ を見た感じでは :code:`video` タグの :code:`poster` 属性には画像のURLを1つしか指定できないようです。
これも併せて考えると、 :code:`video` タグを作る前にブラウザの幅を調べておいて :code:`poster` 属性や :code:`source` タグを動的に生成するほうが良いのかもしれません。
具体的には :code:`video` タグを置くための :code:`div` を先に作って幅を調べるとか。
