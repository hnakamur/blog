Title: Riot.jsでタグエディターのサンプルを作ってみた
Date: 2015-02-28 21:12
Category: blog
Tags: javascript, riot.js
Slug: 2015/02/28/riot-tag-editor-example


## Riot.js

Riot.jsについては[Riot.js 2.0 情報まとめ - Qiita](http://qiita.com/cognitom/items/54ae38c9a50dbbe28367)に良いまとめがありますのでそちらをどうぞ。良いまとめをありがとうございます。

## 本家が提供しているToDoアプリをgoemonでライブリロードして開発を高速化するサンプル

今回のタグエディターの前に、環境整備ということで本家が提供しているToDoアプリをgoemonでライブリロードして開発を高速化するサンプルを作ってみました。

[hnakamur/riotjs-todo-goemon-livereload-example](https://github.com/hnakamur/riotjs-todo-goemon-livereload-example)

[Riot developer guide](https://muut.com/riotjs/guide/)にあるアプリからどのように変更したかはgitのコミットを小分けにしてあるので、そちらをご参照ください。
[Commits · hnakamur/riotjs-todo-goemon-livereload-example](https://github.com/hnakamur/riotjs-todo-goemon-livereload-example/commits/master)

## タグエディターのサンプルをRiot.jsでも作ってみた

で、本題のタグエディターのサンプルです。以前にjQuery, Backbone.js, Vue.jsで同じものを作っていました。

* [jQuery - タグ・エディターを作ってみた - Qiita](http://qiita.com/hnakamur/items/ac5f04930d0c08f141e5)
* [Backbone.jsでタグ・エディターを作ってみた - Qiita](http://qiita.com/hnakamur/items/bfdade12bc5db21fa771)
* [vue.jsでタグ・エディターを作ってみた - Qiita](http://qiita.com/hnakamur/items/a73ff28621e06193a228)

今回はRiot.jsで作ってみました。

ソース: [hnakamur/riot-tag-editor-live-reload-example-with-goemon](https://github.com/hnakamur/riot-tag-editor-live-reload-example-with-goemon)
コンパイル済みのデモ: [Riot tag editor example](https://hnakamur.github.io/riot-tag-editor-live-reload-example-with-goemon/demo/)

セットアップ手順はソースの[README](https://github.com/hnakamur/riot-tag-editor-live-reload-example-with-goemon/blob/master/README.md)を参照してください。

タグエディターのタグのソースは[tag-editor.tag](https://github.com/hnakamur/riot-tag-editor-live-reload-example-with-goemon/blob/master/assets/tag-editor.tag)です。

```
<tag-editor>
  <div class="tag-editor-field" onclick={ click }>
    <div class="tag-editor-tag tag-editor-tag-measure">
      <div id="measure" class="tag-editor-text"></div>
      <a class="tag-editor-delete">x</a>
    </div>
    <div each={ tags } class="tag-editor-tag">
      <div class="tag-editor-text">{ name }</div>
      <a class="tag-editor-delete" onclick={ parent.clickDelete }>x</a>
    </div>
    <input name="editor" class="tag-editor-input" style="width: 0" onkeyup={ keyup } onkeydown={ keydown } onblur={ blur }>
  </div>

  <script>
    this.tags = opts.tags
    this.separator = /[, ]+/

    click(e) {
      adjustEditorWidth(this)
      this.editor.focus()
      return false
    }

    keyup(e) {
      var val = this.editor.value
      if (this.separator.test(val)) {
        mayInsertTags(this)
      } else {
        adjustEditorWidth(this)
      }
      return false
    }

    keydown(e) {
      if (e.which == 13 /* Enter */ && this.editor.value !== '') {
        mayInsertTags(this)
        return true
      } else if (e.which == 8 /* Backspace */ && this.editor.value === '' && this.tags.length > 0) {
        this.tags.pop()
      }
      return true
    }

    blur(e) {
      mayInsertTags(this)
      return true
    }

    clickDelete(e) {
      e.stopPropagation()
      this.tags.splice(this.tags.indexOf(e.item), 1)
      return false
    }

    function adjustEditorWidth(elem) {
      elem.measure.innerText = elem.editor.value + 'WW'
      elem.editor.style.width = elem.measure.offsetWidth + 'px'
    }

    function mayInsertTags(elem) {
      var values = elem.editor.value.split(elem.separator),
          i = 0,
          len = values.length,
          value
      elem.editor.value = ''
      adjustEditorWidth(elem)
      for (; i < len; i++) {
        value = values[i]
        if (value !== '' && !containsTag(elem, value)) {
          elem.tags.push({name: value})
        }
      }
    }

    function containsTag(elem, tag) {
      var i = 0, 
          len = elem.tags.length
      for (; i < len; i++) {
        if (elem.tags[i].name === tag) {
          return true
        }
      }
      return false
    }
  </script>

</tag-editor>
```

HTMLのタグとJavaScriptのコードを一箇所にかけて、イベントもonclickとかで書くので、コンパクトで見やすいです。
onclickとかに指定した関数は `function` なしで書けるようになっていますが、そうでない関数には `function` を明記する必要がありました。

タグエディターを利用する側のHTMLのコードは以下の様な感じで、こちらもシンプルです。

https://github.com/hnakamur/riot-tag-editor-live-reload-example-with-goemon/blob/621d58d0d9774c710f61ad993da451cf948fce22/assets/index.html#L31-L41

```
    <script src="tag-editor.tag" type="riot/tag"></script>
    <script src="https://cdn.jsdelivr.net/g/riot@2.0(riot.min.js+compiler.min.js)"></script>

    <script>
    riot.mount('tag-editor', {
      tags: [
        {name: 'foo'},
        {name: 'bar'},
      ]
    })
    </script>
```

## プリコンパイル済みのソースの作成

```
riot assets/ demo/
```

で `assets/tag-editor.tag` から `demo/tag-editor.js` が生成されます。

利用する側のHTMLは以下のようにします。 riot.jsの読み込み方法と、タグエディターのソースを読み込む順番が開発時とは違うので要注意です。

https://github.com/hnakamur/riot-tag-editor-live-reload-example-with-goemon/blob/621d58d0d9774c710f61ad993da451cf948fce22/demo/index.html#L30-L40

```
    <script src="https://cdn.jsdelivr.net/riot/2.0/riot.min.js"></script>
    <script src="tag-editor.js"></script>

    <script>
    riot.mount('tag-editor', {
      tags: [
        {name: 'foo'},
        {name: 'bar'},
      ]
    })
    </script>
```

## Riot.jsの魅力

[Riot vs React vs Polymer](https://muut.com/riotjs/compare.html)を見ても、riot.min.jsは6.7KBとコンパクトなのが魅力です。それでいてカスタムタグもすっきりシンプルに書けますし。これは今後に期待ですね！
