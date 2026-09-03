import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
// フォントはセルフホスト（外部CDN依存を排除し、オフライン環境でも描画がブロックされないように）
import '@fontsource/m-plus-rounded-1c/400.css'
import '@fontsource/m-plus-rounded-1c/500.css'
import '@fontsource/m-plus-rounded-1c/700.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)
app.mount('#app')
