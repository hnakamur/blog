---
title: "Vue.jsのアプリ開発でローカルの依存ライブラリを参照してデバッグログを追加する手順"
date: 2024-07-05T17:28:33+09:00
---

## はじめに

[Vue.js](https://vuejs.org/)と[VeeValidate V4](https://vee-validate.logaretm.com/v4/)でアプリケーションを書いているときに、VeeValidateにデバッグログを追加して挙動を調査したときの手順をメモ。
例によって、真っ当な方法かは不明です。とりあえずこれでやりたいことはできました。

## 手順

### アプリケーションのpackage.jsonを編集


```json
{
//…(略)…
  "dependencies": {
//…(略)…
    "vee-validate": "file:../ghq/github.com/logaretm/vee-validate/packages/vee-validate",
//…(略)…
  }
//…(略)…
}
```

参考: https://docs.npmjs.com/cli/v10/configuring-npm/package-json#local-paths

### VeeValidateを取得してビルド

ここではパッケージマネージャは[pnpm](https://pnpm.io/ja/)を使っています。

デバッグログとして `console.log()` を適宜追加してビルドします。

```bash
ghq get logaretm/vee-validate
cd ~/ghq/github.com/logaretm/vee-validate
pnpm i
npm run build
```

### アプリケーションをdevモードで実行

VeeValidateをビルドするたびに以下のコマンドを実行し、ビルド結果を参照しつつ実行します。

```bash
rm -rf node_modules/.vite; pnpm i && npm run dev
```
