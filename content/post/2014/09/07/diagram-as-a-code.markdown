---
layout: post
title: "Diagram as a Code"
date: 2014-09-07
comments: true
categories: diagram
---
この記事はpplogに書いた記事 https://www.pplog.net/u/hnakamur2 の転載です。


## 背景
プログラマである私は、既存の作図ツールやシステムに不満があります。こうなってたらいいのにという点を整理してみます。

### 図の変更履歴をわかりやすい形で見たい
ここでの前提として図は概要をつかむためのものと考えています。

データベースのテーブル定義から完全なE-R図を自動作成したり、ソースコードから全ての属性を含んだクラス図を作るといったケースは今回の想定外です。

私が図が欲しいと思うのは概要を把握したい場合なので、むしろ枝葉末節は省いて大まかな構造だけを見たいわけです。何が重要で何が枝葉末節かは人の主観が入るので、図の元ネタは人が書くことになります。となるとバージョン管理して変更履歴を追えるようにしたいと思うのは自然でしょう。

文書はAsciiDocなどのテキスト形式で書けばgitでバージョン管理で差分も見られます。しかし、図はどうするか。バイナリ形式だと差分を表示しても理解できないですし、SVGなら差分は表示可能ですが理解しやすいとは言えないと思います。

### 図の要素を半自動で配置したい
たいていのGUIの作図ツールでは図の要素をマウスで配置するようになっています。整列メニューがあったりはしますが、サイズを幅だけ揃える機能はなかったりして1つずつちまちまと設定することになります。

一方、PlantUMLのようにテキストで図の要素を記述する仕組みの場合、完全自動で配置されるシステムが多いです。というより手動配置のものは見たことが無いです。

要素数が少ないうちは自動配置でも良いのですが、多くなってくると不満が強くなってきます。関連する要素を近くにひとかたまりで配置して、他のグループとは遠くに配置したいのです。また、グループの中でもどの順序で並べるかは明示的に指定したい。

同様に、要素間を結ぶ線の引き回しの配置も半自動にしたい。図に要素を追加していく時に、配置を調整するわけですが、接続線の配置が完全手動だと修正が面倒すぎます。かと言って完全自動だと、引き回しの配置が希望通りにならなくて不満が出ます。

ということで、接続線の配置のルールの一部は自動化して、残りは手動で指定するという半自動方式が欲しいわけです。

## 解決案
ということで、図の要素のテキストと配置のうち手動で指定したい部分だけをユーザが指定するテキストデータとして記述し、残りはプログラムで自動化すれば良いのではという考えが浮かびました。

これはまさに[D3.js - Data-Driven Documents]( http://d3js.org/ )の名前の通りの考え方です。データドリブンでドキュメントを作るわけです。

インフラ界隈で言われているInfrastracture as a Codeという言葉にのっかると、Diagram as a Codeとも言えると思います。2つ合わせるとData-Driven Diagram as a Codeかなw

まだ荒削りですけど、実際にd3.jsを使ったサンプルプログラムを書いて試しています。
[d3.jsでクラス図を書いてみた - Qiita]( http://qiita.com/hnakamur/items/cd7610f63f5275e774a4 )

AsciiDocの文書に埋め込むためにasciidoctor-diagramのプラグインも作っています。
https://github.com/hnakamur/asciidoctor-diagram-d3js

## Diagram as a Codeのノウハウを共有し合えるようになりたい
図の要素や接続線を半自動で配置するためには、幾何学の計算アルゴリズムが重要になってきます。例えば、[d3.js - 円の中心までベジェ曲線を引くときに円との交点に矢印終端を配置するサンプル - Qiita]( http://qiita.com/hnakamur/items/3ce1e90aecd36883add6 )でもベジェ曲線と円の交点を求める計算が必要です。ネットの情報を見ながら独学でやっているだけだと、時間もかかるし挫折しがちです。

ということで、Diagram as a Codeの流れが広まって、幾何学の計算のノウハウを共有し合えるようになると嬉しいなあというのが願いです。
