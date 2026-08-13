# App.vue

### type scriptの宣言

```vue
<script setup lang="ts">
import { computed, onMounted } from "vue"; //{①値を自動的に計算してくれる機能 , ②画面が表示された直後に処理を実行するためのもの。}
import { useRoute } from "vue-router"; //③ページの現在地の取得
import {
  NConfigProvider,
  NMessageProvider,
  NNotificationProvider,
  dateJaJP,
  jaJP,
} from "naive-ui"; //{UI全体の設定 , メッセージ表示 , 通知表示 , 日付の日本語設定 , 日本語設定}
import HeaderBar from "@/components/HeaderBar.vue"; //ヘッダーバーの情報を読みこむ
import { useAuthStore } from "@/stores/auth"; //⑤認証情報を管理するための機能
const route = useRoute(); //③を使用（ページの現在地を取得する）
const auth = useAuthStore(); //⑤を使用(認証情報を管理する)

const showHeader = computed(
  () => route.meta.hideHeader !== true && auth.isAuthenticated,
); //①を使用（画面出力の合否確認）
onMounted(async () => {
  await auth.restore();
}); //②を使用（アプリの画面が表示されたら、ログイン状態を復元するという処理）
</script>
```

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
          //⑥app-shellの中身を適用
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

### サーバーと通信するためのお約束設定（Axious）

ここでは、画面（フロントエンド）とサーバー（バックエンド）がデータをやり取りするための「通信の基本ルール」を決めています。イメージとしては、**サーバーに手紙（データ）を届ける「専用の郵便屋さん」を作って、そのルールを教えている**ようなイメージです。

```vue
import axios from 'axios' const baseURL = import.meta.env.VITE_API_BASE_URL ||
'http://localhost:8000' export const api = axios.create({ baseURL:
`${baseURL}/api`, timeout: 30000, }) api.interceptors.request.use((config) => {
const token = localStorage.getItem('token') if (token && config.headers) {
config.headers.Authorization = `Bearer ${token}` } return config })
api.interceptors.response.use( (r) => r, (err) => { if (err.response?.status ===
401) { localStorage.removeItem('token') if
(!window.location.pathname.startsWith('/login')) { window.location.href =
'/login' } } return Promise.reject(err) }, )
```

①宛先（ベースURL）を決める

```vue
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
```

手紙を届けるための「基本の住所」です。本番環境の住所が設定されていればそれを使い、なければ自分のパソコンの住所（http://localhost:8000）を使います。

②専用の郵便屋さん（api）を作る

```vue
export const api = axios.create({ ... })
```

毎回長い住所を全部書くのは大変なので、「この住所に、３０秒以内に届けてね」というルールをあらかじめ覚えさせた、専門の郵便屋さん（api）を作成してます。

③データを送る前（リクエスト）の自動チェック

```vue
api.interceptors.request.use(...)
```

手紙を送る直前に、必ず「身分証明書（トークン）」を持っているかチェックする仕組みです。もし持っていれば、手紙の封筒にその証明書をペタッと張り付けてからサーバーに送ります。これで「怪しい人じゃないと」とサーバーに伝わります。

④データを受け取った（レスポンス）の自動チェック

```vue
api.interceptors.response.use(...)
```

サーバーから返事が返ってきた直後に行う処理です。
もしサーバーから「身分証明書が期限切れだよ！（エラー401）」と弾かれてしまったら、今持っている古い証明書をゴミ箱に捨てて、強制的にログイン画面に戻す（もう一度証明書を取り直させる）仕組みになっています。
