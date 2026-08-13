# App.vue

- [Vue.jsの基本知識（初心者向け）](https://qiita.com/EasyCoder/items/6b3d0fd15051de519705)参照

### 設定の定義

```vue
<script setup lang="ts">
import { computed, onMounted } from "vue"; //{値を自動的に計算してくれる機能--① , 画面が表示された直後に処理を実行するためのもの--②}
import { useRoute } from "vue-router"; //ページの現在地の取得--③
import {
  NConfigProvider,
  NMessageProvider,
  NNotificationProvider,
  dateJaJP,
  jaJP,
} from "naive-ui"; //{UI全体の設定 , メッセージ表示 , 通知表示 , 日付の日本語設定 , 日本語設定}
import HeaderBar from "@/components/HeaderBar.vue"; //ヘッダーバーの情報を読みこむ
import { useAuthStore } from "@/stores/auth"; //認証情報を管理するための機能--④
const route = useRoute(); //③を使用（ページの現在地を取得する）
const auth = useAuthStore(); //⑤を使用(認証情報を管理する)

const showHeader = computed(
  () => route.meta.hideHeader !== true && auth.isAuthenticated,
); //①を使用（画面出力の合否確認）
const showHeader = computed(
  () => route.meta.hideHeader !== true && auth.isAuthenticated,
); //①を使用（画面出力の合否確認）
onMounted(async () => {
  await auth.restore();
}); //②を使用（アプリの画面が表示されたら、ログイン状態を復元するという処理）
</script>
```

---

### 実際の見た目（HTML）

```vue
<template>
  <n-config-provider :locale="jaJP" :date-locale="dateJaJP">
    //日本語設定
    <n-message-provider>
      //メッセージ表示
      <n-notification-provider>
        //通知機能
        <div class="app-shell">
          //app-shellの中身を適用
          <HeaderBar v-if="showHeader" /> //showHeaderがTrueの時HeaderBarを表示
          <main class="app-main">
            //メイン <router-view /> //現在のURLに対応するページを表示する
          </main>
        </div>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>
```

---

### スタイル

```vue
<style>
:root {
  --page-max-width: 1400px;
}
body {
  margin: 0;
  font-family:
    'Hiragino Kaku Gothic ProN',
    'Noto Sans JP',
    system-ui,
    sans-serif;
  background: #f6f7fb;
  color: #202226;
}
.app-shell {　　　　　　　　                                   //⑥アプリ全体のレイアウト
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-main {
  flex: 1;
  padding: 24px;
  max-width: var(--page-max-width);
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
```

# client.ts

###

```vue
import axios from 'axios' // axios本体を読み込み
```

// APIのベースURLを環境変数から取得。なければローカルのAPIを使う
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// axiosインスタンスを作成（共通設定をまとめる）
export const api = axios.create({
baseURL: `${baseURL}/api`, // すべてのリクエストの先頭に付くURL
timeout: 30000, // タイムアウト３０秒
})

// リクエストインターセプター（送信前に毎回実行される）
api.interceptors.request.use((config) => {
const token = localStorage.getItem('token') // ローカルストレージからJWT取得
if (token && config.headers) {
config.headers.Authorization = `Bearer ${token}`
}
return config
})

api.interceptors.response.use(
(r) => r,
(err) => {
if (err.response?.status === 401) {
localStorage.removeItem('token')
if (!window.location.pathname.startsWith('/login')) {
window.location.href = '/login'
}
}
return Promise.reject(err)
},
)

````



---
---
# eslint.config.js
-[eslintとは](https://eslint.vuejs.org/user-guide/) (typescript-eslintとPrettierを使用した設定例参照)

### 設定の定義
```vue

import vue from 'eslint-plugin-vue'                          //VueのコードをESLintでチェックできるようにする
import ts from '@vue/eslint-config-typescript'               //TypeScriptを使ったESLintを設定する
import prettier from '@vue/eslint-config-prettier'           //EslintとPrettierのルールの衝突を防ぐ--①

````

-[①：](https://github.com/vuejs/eslint-config-prettier)参照

---

### 設定の適用と独自ルールの制定

```vue　

export default [
  --設定の適用--
  ...vue.configs['flat/recommended'],                        //一貫性確保のためにデフォルト設定を強制するルール--②
  ...ts(),                                                   //TypeScript用の設定を取得する
  prettier,
  {
  --ルールの制定--
    rules: {
      'vue/multi-word-component-names': 'off',               //１単語のコンポーネント名を許可する--③
    },
  },
]

```

-[②：](https://eslint.vuejs.org/user-guide/)参照(バンドル構成) -[③：](https://qiita.com/Jimonull/items/1032c46f519e085eb922)参照

---

---

# index.html

```vue
<!DOCTYPE html>
<html lang="ja">
  //日本語のページであることを指定
  <head>
    <meta charset="UTF-8" />
    //文字コードはUTF-8であることを指定
    <link rel="icon" href="/favicon.ico" />
    　　　　　　　　　　　　　　　　　　　　//ファビコンを指定（ページのアイコン）
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    //デバイスに応じた表示を可能にする--①
    <title>AI-Shifts-Management</title>
    //タイトル
  </head>
  <body>
    <div id="app"></div>
    //Vue.jsがマウントする場所を用意する場所--②
    <script type="module" src="/src/main.ts"></script>
    //src/main.tsというTypeScriptファイルを読み込んで実行する
  </body>
</html>
```

-[①：](https://developer.mozilla.org/ja/docs/Web/HTML/Reference/Elements/meta/name/viewport)参照(ビューポートの幅と画面の幅) -[②：](https://team-lab.github.io/skillup-nodejs/vuejs.html#vue-js%E3%81%AE%E8%B5%B7%E5%8B%95)参照

---

---

# nginx.conf

### サーバーの設定

```vue
server { listen 80; //80番ポートでWebアクセスを受け付ける server_name _;
//このサーバー設定でアクセスを受け付ける root /usr/share/nginx/html;
//Webサイトのファイルが/usr/share/nginx/htmlにあることを指定 index index.html;
//ファイル名を指定せずにアクセスされたらindex.htmlを使う location / { try_files
$uri $uri/ /index.html; //要求されたファイルが存在しなければindex.htmlを返す--①
} }
```

-[①：](https://tsyama.hatenablog.com/entry/try_files_is_difficult)参照

---

---

# package.json

### プロジェクト情報一覧

```vue
{ "name": "ai-shifts-management-frontend", //名前 "version": "0.1.0",
//バージョン "private": true, //情報公開の有無 "type": "module",
//JavaScriptをES Modules形式で扱う設定
```

---

### npmコマンドで何を実行するか

[package.json](https://note.shiftinc.jp/n/n9c5fcd207680#55141af7-6245-40b3-b693-99bd07a42f59)参照

```vue
"scripts": { "dev": "vite",
//開発モードでプロジェクトをローカル環境で実行する--① "build": "vue-tsc --noEmit
&& vite build", //プロジェクトをビルドする--① "preview": "vite preview --port
4173", //プロダクションビルドが問題ないかどうかを自分のローカル環境で確認する--②
"lint": "eslint . --ext .vue,.ts,.tsx --fix",
//コードの書き方を自動チェックする--③ "format": "prettier -w src",
//ルートディレクトリ全体を対象にファイルを修正する-④ "test:unit": "vitest run"
//Vitestを使って単体テストを実行する },
```

-[①：](https://commte.net/nextjs-npmCommands)参照 -[②：](https://ja.vite.dev/guide/static-deploy)参照 -[③：](https://qiita.com/Udy03/items/154a80fb7ac9ccc01855)参照 -[④：](https://zenn.dev/2192/articles/9a3a576da1583c)参照

---

### 使用するライブラリ

```vue
"dependencies": { "@vueuse/core": "^11.1.0", //Vueで便利な機能を使う "axios":
"^1.7.4", //Backendと通信する "date-fns": "^3.6.0", //日付を計算・加工する
"naive-ui": "^2.39.0", //ボタン・フォーム・通知などを作る "pinia": "^2.2.0",
//データ・ログイン状態を管理 "vue": "^3.5.0", //画面を作る "vue-router":
"^4.4.0" //ページを切り替える },
```

---

### 開発・テスト・ビルドなどに使うツール

```vue
"devDependencies": { "@types/node": "^20.14.0", "@vitejs/plugin-vue": "^5.1.0",
"@vue/eslint-config-prettier": "^9.0.0", "@vue/eslint-config-typescript":
"^13.0.0", "@vue/test-utils": "^2.4.6", "@vue/tsconfig": "^0.5.1", "eslint":
"^8.57.0", //コードチェック "eslint-plugin-vue": "^9.28.0",
//Vue専用のESLintプラグイン "jsdom": "^25.0.0",
//Node.js上で、ブラウザのHTML・DOM環境を再現するライブラリ "prettier": "^3.3.0",
//コード成型 "typescript": "^5.5.0", //Type Script "vite": "^5.4.0",
//開発サーバ・ビルド "vitest": "^2.1.0", //テスト "vue-tsc": "^2.1.0"
//VueとTypeScriptの型のチェック } }
```

---

---

# tsconfig.json

### 基本設定の引継ぎ

```vue
{ "extends": "@vue/tsconfig/tsconfig.dom.json",
//Vueプロジェクトを拡張するためのTSConfig--①
```

[①：](https://github.com/vuejs/tsconfig)参照

---

### TypeScriptのルール

```vue
"compilerOptions": { "baseUrl": ".", //現在のプロジェクトのフォルダ--② "paths":
{ "@/*": ["./src/*"] //src/stores/auth--③ },
```

[②：](https://zenn.dev/hayato94087/articles/198646f23bc841)参照
[③：](https://zenn.dev/hayato94087/articles/9f3bf702543431)参照

---

### TypeScriptのルール続き

```vue
"types": ["vite/client", "vitest/globals"], //TypeScriptに追加の型情報を教える:
　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　[Viteの機能をTypeScriptに認識させる,vitestの機能をTypeScriptに認識させる]
"strict": true, //TypeScriptのチェックを厳しくする "noImplicitAny": true
//anyを使った型指定を否定する--④ }, "include": ["src/**/*", "src/**/*.vue",
"vite.config.ts"] //TypeScriptがチェックするファイルを指定する }
```

[④：](https://www.typescriptlang.org/tsconfig/#noImplicitAny)参照(暗黙のAnyなし)

---

---

# vite.config.ts

### 機能の設定

[Configuring Vite](https://vite.dev/config/)参照

```vue
import { fileURLToPath, URL } from 'node:url'
//ファイルの絶対パスやディレクトリ名を取得する--① import { defineConfig } from
'vite' //Viteの設定を取り入れるための機能--② import vue from
'@vitejs/plugin-vue' //ViteでVueを扱えるようにするプラグイン
```

[①：](https://stackoverflow.com/questions/75004188/what-does-fileurltopathimport-meta-url-do)参照

---

### 機能の有効化

```vue
export default defineConfig({ //②の使用 plugins: [vue()], //vueの有効化
```

**tsconfig.jsonとつながりがある　⤵**

```vue
（二重で同じことを定義している） resolve: { //TypeScript側の設定 alias: {
//Vite側の設定 '@': fileURLToPath(new URL('./src', import.meta.url)), //@ =
src/(tsconfig.json参照) }, },
```

---

### サーバオプション

[サーバオプション](https://ja.vite.dev/config/server-options.html)参照

```vue
server: { //Viteの開発サーバーの操作 host: '0.0.0.0', //LAN
やパブリックアドレスを含むすべてのアドレスをアクセス可能にする port: 5173,
//http://localhost:5173で起動する watch: { usePolling: true,
//ファイルの変更を検知する--③ interval: 100,
//100ミリ秒ごとにファイルの変更を確認する--③ }, },
```

[③：](https://zenn.dev/hctaw_srp/articles/1f7f67de03d710)参照

---

### テストツール

```vue
test: { environment: 'jsdom', //テストを行うライブラリ--④ globals: true,
//グローバルAPIとして使用できるようにする--④ }, })
```

[④：](https://zenn.dev/longbridge/articles/9d9ec773cb3814)参照

---

---

# vite.config.ts.timestamp-1785578376639-4bdf97258a132.mjs

- **vite.config.tsファイルをViteによって変換されたファイル**（人が触るファイルではない）###　機能の設定

```vue
// vite.config.ts import { fileURLToPath, URL } from "node:url"; import {
defineConfig } from
"file:///workspace/frontend/node_modules/vite/dist/node/index.js"; import vue
from
"file:///workspace/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs"; var
__vite_injected_original_import_meta_url =
"file:///workspace/frontend/vite.config.ts";
```

---

### 機能の有効化

```vue
var vite_config_default = defineConfig({ plugins: [vue()],
```

```vue
resolve: { alias: { "@": fileURLToPath(new URL("./src",
__vite_injected_original_import_meta_url)) } },
```

---

### サーバオプション

```vue
server: { host: "0.0.0.0", port: 5173 },
```

---

### テストツール

```vue
test: { environment: "jsdom", globals: true } });
```

---

- 機能の有効化に入っていたexport defaultの変換

```vue
export { vite_config_default as default };
```

---

### 変換後のJavaScriptと元のTypeScriptコードを対応付けるための情報(気にしなくてよい)

```vue
//#
sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvd29ya3NwYWNlL2Zyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCIvd29ya3NwYWNlL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy93b3Jrc3BhY2UvZnJvbnRlbmQvdml0ZS5jb25maWcudHNcIjtpbXBvcnQgeyBmaWxlVVJMVG9QYXRoLCBVUkwgfSBmcm9tICdub2RlOnVybCdcclxuaW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXHJcblxyXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xyXG4gIHBsdWdpbnM6IFt2dWUoKV0sXHJcbiAgcmVzb2x2ZToge1xyXG4gICAgYWxpYXM6IHtcclxuICAgICAgJ0AnOiBmaWxlVVJMVG9QYXRoKG5ldyBVUkwoJy4vc3JjJywgaW1wb3J0Lm1ldGEudXJsKSksXHJcbiAgICB9LFxyXG4gIH0sXHJcbiAgc2VydmVyOiB7XHJcbiAgICBob3N0OiAnMC4wLjAuMCcsXHJcbiAgICBwb3J0OiA1MTczLFxyXG4gIH0sXHJcbiAgdGVzdDoge1xyXG4gICAgZW52aXJvbm1lbnQ6ICdqc2RvbScsXHJcbiAgICBnbG9iYWxzOiB0cnVlLFxyXG4gIH0sXHJcbn0pXHJcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBMk8sU0FBUyxlQUFlLFdBQVc7QUFDOVEsU0FBUyxvQkFBb0I7QUFDN0IsT0FBTyxTQUFTO0FBRjhILElBQU0sMkNBQTJDO0FBSS9MLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxJQUFJLENBQUM7QUFBQSxFQUNmLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssY0FBYyxJQUFJLElBQUksU0FBUyx3Q0FBZSxDQUFDO0FBQUEsSUFDdEQ7QUFBQSxFQUNGO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixNQUFNO0FBQUEsRUFDUjtBQUFBLEVBQ0EsTUFBTTtBQUFBLElBQ0osYUFBYTtBQUFBLElBQ2IsU0FBUztBQUFBLEVBQ1g7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
```
