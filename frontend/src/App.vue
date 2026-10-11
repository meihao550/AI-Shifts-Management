<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  NConfigProvider,
  NMessageProvider,
  NNotificationProvider,
  NSpin,
  dateJaJP,
  jaJP,
} from 'naive-ui'
import HeaderBar from '@/components/HeaderBar.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const showHeader = computed(() => route.meta.hideHeader !== true && auth.isAuthenticated)

// 起動時、auth.restore()（router guard 内）が解決するまで全画面ローディングを出す。
// 無料構成では backend/DB のコールドスタートで初回に数秒かかるため。
const booting = computed(() => !auth.hydrated)
const slowStart = ref(false)
let slowTimer: ReturnType<typeof setTimeout> | undefined

// 2.5 秒待っても終わらなければ「起動中」文言に切替えて不安を和らげる。
watch(
  booting,
  (isBooting) => {
    if (isBooting) {
      slowTimer = setTimeout(() => {
        slowStart.value = true
      }, 2500)
    } else {
      if (slowTimer) clearTimeout(slowTimer)
      slowStart.value = false
    }
  },
  { immediate: true },
)

// naive-ui 全体を Duty Board パレットへ寄せる（表・ボタン・カードが自動追従）
const themeOverrides = {
  common: {
    fontFamily:
      "'M PLUS Rounded 1c', 'Hiragino Kaku Gothic ProN', 'Noto Sans', system-ui, sans-serif",
    primaryColor: '#3b4e8c',
    primaryColorHover: '#33447c',
    primaryColorPressed: '#2a3a6a',
    primaryColorSuppl: '#33447c',
    infoColor: '#3b4e8c',
    infoColorHover: '#33447c',
    successColor: '#3c7a60',
    warningColor: '#b9791f',
    errorColor: '#b23a3a',
    textColorBase: '#191c18',
    textColor1: '#191c18',
    textColor2: '#3a3e36',
    textColor3: '#787c71',
    bodyColor: '#edefea',
    cardColor: '#faf9f3',
    modalColor: '#faf9f3',
    popoverColor: '#faf9f3',
    borderColor: '#d6d8ce',
    borderRadius: '6px',
    borderRadiusSmall: '4px',
    fontWeightStrong: '700',
  },
  Card: { borderRadius: '10px', color: '#faf9f3' },
  DataTable: {
    thColor: '#eef0e8',
    thTextColor: '#3a3e36',
    thFontWeight: '700',
    tdColor: '#faf9f3',
    borderColor: '#d6d8ce',
    tdColorHover: '#f0f1ea',
  },
  Statistic: { labelFontSize: '13px' },
}
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="jaJP" :date-locale="dateJaJP">
    <n-message-provider>
      <n-notification-provider>
        <div class="app-shell">
          <HeaderBar v-if="showHeader" />
          <main class="app-main">
            <router-view />
          </main>
        </div>
        <Transition name="boot-fade">
          <div v-if="booting" class="boot-overlay">
            <NSpin :size="48" />
            <p class="boot-text">
              {{ slowStart ? 'サーバーを起動しています。少々お待ちください…' : '読み込み中…' }}
            </p>
          </div>
        </Transition>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
/* 基盤(body/背景/フォント)は styles/tokens.css。ここはシェルの骨格のみ。 */
.app-shell {
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

/* カードの見出しを盤面の“帯”に。全画面で一貫させる。 */
.n-card > .n-card-header {
  border-bottom: 1px solid var(--line);
}
.n-card > .n-card-header .n-card-header__main {
  font-weight: 700;
  letter-spacing: 0.01em;
}

/* 起動時の全画面ローディング。ログイン画面と同じ方眼トーンに合わせる。 */
.boot-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background-color: var(--paper);
}
.boot-text {
  margin: 0;
  color: var(--ink-2);
  font-size: 14px;
}
.boot-fade-leave-active {
  transition: opacity 0.25s ease;
}
.boot-fade-leave-to {
  opacity: 0;
}
</style>
