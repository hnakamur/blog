ChromeとFirefoxの拡張機能を書くのにasync/awaitを使ってみた
##########################################################

:date: 2017-09-18 12:35
:tags: javascript, async-await
:category: blog
:slug: 2017/09/18/use-async-await-in-writing-chrome-and-firefox-extensions

はじめに
--------

私はChromeとFirefox用に以下の拡張機能を書いて使っています。

* `FormatLink-Chrome <https://github.com/hnakamur/FormatLink-Chrome>`_
* `FormatLink-Firefox <https://github.com/hnakamur/FormatLink-Firefox>`_

今回UIを改変する際についでに async と await を使って書くように変更してみたのでメモです。


async/await が使える Firefox と Chrome のバージョン
---------------------------------------------------

`Can I use... Support tables for HTML5, CSS3, etc <https://caniuse.com/#feat=async-functions>`_
で "Showing all" をクリックして確認すると Chrome はバージョン 55 、 Firefox はバージョン 52 から async/await をサポートしているとのことです。

Promise を返す API を async/await で呼び出す
--------------------------------------------

`async function - JavaScript | MDN <https://developer.mozilla.org/ja/docs/Web/JavaScript/Reference/Statements/async_function>`_ に分かりやすい説明と例がありました。

Firefox の拡張機能を書くのにasync/awaitを使う
---------------------------------------------

`WebExtensions とは何か？ - Mozilla | MDN <https://developer.mozilla.org/ja/Add-ons/WebExtensions/What_are_WebExtensions>`_ で説明されていますが、以前は Firefox の拡張は XUL などの技術を使っていましたが、今後は WebExtensions のみが利用可能となります。

`WebExtensions - Mozilla | MDN <https://developer.mozilla.org/ja/Add-ons/WebExtensions>`_
のページ右の「JavaScript API 群」はほとんどは Promise を返すようになっています。

例えば自分の拡張機能のコンテキストメニューを全て消す API
`menus.removeAll() <https://developer.mozilla.org/en-US/Add-ons/WebExtensions/API/menus/removeAll>`_
の syntax は

.. code-block:: javascript

    var removing = browser.menus.removeAll()

のように Promise を返します。

これらの API は上記の方法で async/await で呼び出すことが可能です。

一方で、コンテキストメニューを作成する API
`menus.create() - Mozilla | MDN <https://developer.mozilla.org/en-US/Add-ons/WebExtensions/API/menus/create>`_
の syntax は

.. code-block:: javascript

    browser.menus.create(
      createProperties, // object
      function() {...}  // optional function
    )

のようにコールバック関数をオプショナルで受け取るようになっています。

そこでまず :code:`browser.menus.create` を Promise でラップした関数を作ります。

https://github.com/hnakamur/FormatLink-Firefox/blob/0e5d21c5ab4d87b758ef2da4f671406bc64a940b/common.js#L50-L61

.. code-block:: javascript

    function creatingContextMenuItem(props) {
      return new Promise((resolve, reject) => {
        browser.contextMenus.create(props, () => {
          var err = browser.runtime.lastError;
          if (err) {
            reject(err);
          } else {
            resolve();
          }
        });
      });
    }

あとは同様に async/await で呼び出せば OK です。

https://github.com/hnakamur/FormatLink-Firefox/blob/0e5d21c5ab4d87b758ef2da4f671406bc64a940b/common.js#L63-L83

.. code-block:: javascript

    async function createContextMenus(options) {
      await browser.contextMenus.removeAll();
      if (options.createSubmenus) {
        var count = getFormatCount(options);
        for (var i = 0; i < count; i++) {
          var format = options['title' + (i + 1)];
          await creatingContextMenuItem({
            id: "format-link-format" + (i + 1),
            title: "as " + format,
            contexts: ["link", "selection", "page"]
          });
        }
      } else {
        var defaultFormat = options['title' + options['defaultFormat']];
        await creatingContextMenuItem({
          id: "format-link-format-default",
          title: "Format Link as " + defaultFormat,
          contexts: ["link", "selection", "page"]
        });
      }
    }

Chrome の拡張機能を書くのに async/await を使う
----------------------------------------------

Chrome の拡張機能用の API
`JavaScript APIs - Google Chrome <https://developer.chrome.com/extensions/api_index>`_
は Promise を返す方式ではなく、コールバック関数を引数にとる方式になっています。

例えばコンテキストメニューを作成するAPI
`chrome.contextMenus.create <https://developer.chrome.com/extensions/contextMenus#method-create>`_

のシグネチャは

.. code-block:: text

    integer or string chrome.contextMenus.create(object createProperties, function callback)

となっています。

ということでまず Promise を返すラッパー関数を書く必要があるのですが、
`KeithHenry/chromeExtensionAsync: Promise wrapper for the Chrome extension API so that it can be used with async/await rather than callbacks <https://github.com/KeithHenry/chromeExtensionAsync>`_
という便利なライブラリがありました。
これを使えば元の API の関数名のまま呼び出せば Promise を返すようになります。

Chrome で for ループ内で await を呼んでハマったが Promise.all で解決
--------------------------------------------------------------------

自作の拡張 Format Link では初期化時と設定ページで設定を保存したときに、コンテキストメニューを一旦全部消して作り直すようにしています。

Firefox 用の拡張では上記の :code:`createContextMenus` のように :code:`for` ループ内で :code:`await creatingContextMenuItem` で正常に作成できていました。

ですが、 Chrome では同様なコードだと、初期化時は問題ないのですが、設定ページで "Create submenus" をオンにして設定を保存したときに 4 つのサブメニューが作られるべきところが最初の 2 つしか作られないという現象が発生しました。

とりあえずの回避策として :code:`await` を使わずに
https://github.com/hnakamur/FormatLink-Chrome/blob/4828a677776b81ef3ca66132fea366c60ccd7d4f/common.js#L55-L77

.. code-block:: javascript

    async function createContextMenus(options) {
      await chrome.contextMenus.removeAll();
      if (options.createSubmenus) {
        var count = getFormatCount(options);
        for (var i = 0; i < count; i++) {
          var format = options['title' + (i + 1)];
          // NOTE: Some of menu items weren't created when I added 'await' here.
          // So I deleted 'await' as a workaround.
          chrome.contextMenus.create({
            id: "format-link-format" + (i + 1),
            title: "as " + format,
            contexts: ["link", "selection", "page"]
          });
        }
      } else {
        var defaultFormat = options['title' + options['defaultFormat']];
        await chrome.contextMenus.create({
          id: "format-link-format-default",
          title: "Format Link as " + defaultFormat,
          contexts: ["link", "selection", "page"]
        });
      }
    }

としたら、とりあえず期待通りの動きになりました。
が、これだと完了を待てないので、この後さらに処理をつなげたいときには困ります。

その後 `Promise.all() - JavaScript | MDN <https://developer.mozilla.org/ja/docs/Web/JavaScript/Reference/Global_Objects/Promise/all>`_ というのを見つけて、以下のように書き換えました。

https://github.com/hnakamur/FormatLink-Chrome/blob/6445fd5f8a2df38c54706f3415f732e6a654140d/common.js#L55-L77

.. code-block:: javascript

    async function createContextMenus(options) {
      await chrome.contextMenus.removeAll();
      if (options.createSubmenus) {
        var promises = [];
        var count = getFormatCount(options);
        for (var i = 0; i < count; i++) {
          var format = options['title' + (i + 1)];
          promises[i] = chrome.contextMenus.create({
            id: "format-link-format" + (i + 1),
            title: "as " + format,
            contexts: ["link", "selection", "page"]
          });
        }
        await Promise.all(promises);
      } else {
        var defaultFormat = options['title' + options['defaultFormat']];
        await chrome.contextMenus.create({
          id: "format-link-format-default",
          title: "Format Link as " + defaultFormat,
          contexts: ["link", "selection", "page"]
        });
      }
    }

おわりに
--------

例によって雰囲気で書いてますが、 Firefox でも Chrome でも拡張機能を書くのに async/await が使えることが分かったのでとりあえずよかったです。
