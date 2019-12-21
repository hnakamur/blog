---
layout: post
title: "d3.jsを使ったツールチップあり複数折れ線グラフのサンプルを作った"
date: 2013-03-02
comments: true
categories: d3.js
---
[D3.js - Data-Driven Documents](http://d3js.org/)を使ってツールチップあり複数折れ線グラフのサンプルを作ったのでメモ。

<a href="/downloads/code/2013-03-02-multi-series-line-chart-example-with-tooltip-using-d3-dot-js/3884955.html">サンプル</a>

[Multi-Series Line Chart](http://bl.ocks.org/mbostock/3884955)のサンプルをベースに改良しました。

## X軸のラベルを回転

[D3.js Tips and Tricks: How to rotate the text labels for the x Axis of a d3.js graph](http://www.d3noob.org/2013/01/how-to-rotate-text-labels-for-x-axis-of.html)を参考にして回転させました。

```
  svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(xAxis)
      .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", "-.6em")
        .attr("transform", "rotate(-90)");
```

## ツールチップを出す

[Simple D3 tooltip](https://gist.github.com/biovisualize/1016860#gistcomment-61316)の手法で、線でもツールチップは出せなくはないのですが、カーソル位置のデータが取れないので、データの点に円を作成することにしました。

[multi-line chart with circle points - Google グループ](https://groups.google.com/forum/?fromgroups=#!topic/d3-js/8XLzUYLoFnY)を参考に以下の様なコードで円を作成しました。

ツールチップを出す部分は[Simple D3 tooltip](https://gist.github.com/biovisualize/1016860#gistcomment-61316)を参考にしました。元のコードではイベントを```event```で参照していましたが、ChromeとSafariでは動くもののFirefoxではundefinedになっていました。[Selections · mbostock/d3 Wiki](https://github.com/mbostock/d3/wiki/Selections#wiki-on)を見ると、```d3.event```で参照するのが正しいので修正しました。


```
 city. selectAll("circle")
      .data(function(d) { return d.values.map(function(v) {
              return {date: v.date, temperature: v.temperature, name: d.name};
            }); })
    .enter().append("circle")
      .attr("cx", function(d, i) { return x(d.date); })
      .attr("cy", function(d, i) { return y(d.temperature); })
      .style("fill", function(d) { return color(d.name); })
      .attr("r", 1)
      .on("mouseover", function(){
        return tooltip.style("visibility", "visible");
      })
      .on("mousemove", function(d){
        return tooltip
          .style("top", (d3.event.pageY-10)+"px")
          .style("left",(d3.event.pageX+10)+"px")
          .html("<dl><dt>date</dt><dd>" + d3.time.format("%Y-%m-%d")(d.date) + "</dd><dt>temperature</dt><dd>" + d.temperature + "</dd><dt>name</dt><dd>" + d.name + "</dd></dl>");
      })
      .on("mouseout", function(){
        return tooltip.style("visibility", "hidden");
      });
```

見た目がうるさくないように円の半径は1とし、線だけ見えるような感じにしています。すると点にカーソルでポイントするのが大変なので、太めのストロークを透明色で指定して、ポイントしやすくしています。

```
.tooltip {
  border: 1px solid black;
  background-color: white;
  padding: 5px 8px 4px 8px;
  border-radius: 4px;
  -moz-border-radius: 4px;
  -webkit-border-radius: 4px;
}
```

## 線のデータ補完を止める

データ補完してしまうと、線とデータ点がずれてしまうので、補完は止めます。
interpolate()を呼ばなければOK。

```
var line = d3.svg.line()
    //.interpolate("basis")
    .x(function(d) { return x(d.date); })
    .y(function(d) { return y(d.temperature); });
```

