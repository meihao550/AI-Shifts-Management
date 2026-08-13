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
