<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NCard } from 'naive-ui'
import { apiBase } from '@/api/client'

const route = useRoute()

// OAuth コールバックで許可リスト外だった場合、?error=not_allowed で戻される。
const notAllowed = computed(() => route.query.error === 'not_allowed')

// backend への遷移はコールドスタート時に数秒かかるため、押下直後に
// ローディング表示を出して「固まった」ように見えないようにする。
const loggingIn = ref(false)

function loginWithGoogle() {
  loggingIn.value = true
  window.location.href = `${apiBase}/api/auth/google/login`
}

// 開発(ローカル)でのみ読み込む補助ツール。本番ビルドでは DEV=false となり、
// この動的 import ごとツリーシェイクされてバンドルに含まれない。
const DevLoginTools = import.meta.env.DEV
  ? defineAsyncComponent(() => import('@/components/DevLoginTools.vue'))
  : null
</script>

<template>
  <div class="login-shell">
    <NCard class="login-card">
      <div class="brand-row">
        <span class="mark" aria-hidden="true">勤</span>
        <h1 class="title">シフト勤務表</h1>
      </div>
      <p class="subtitle">月のシフトを組み、人件費まで一枚で。</p>

      <p v-if="notAllowed" class="error">
        このアカウントはログインを許可されていません。管理者にお問い合わせください。
      </p>

      <NButton
        type="primary"
        size="large"
        block
        :loading="loggingIn"
        :disabled="loggingIn"
        @click="loginWithGoogle"
      >
        {{ loggingIn ? 'ログインページへ移動中…' : 'Google でログイン' }}
      </NButton>

      <p v-if="loggingIn" class="hint">
        サーバーを起動しています。数秒かかることがあります…
      </p>
      <p v-else class="hint">
        管理者が許可したアカウントのみログインできます。
      </p>

      <!-- ローカル開発環境でのみ読み込まれる（本番ビルドには含まれない）。 -->
      <component :is="DevLoginTools" v-if="DevLoginTools" />
    </NCard>
  </div>
</template>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background-color: var(--paper);
}

.login-card {
  width: 440px;
  max-width: 100%;
  padding: 24px 28px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line-2);
  box-shadow: 0 8px 30px rgba(25, 28, 24, 0.1);
}
/* 上端に黒いライン1本 */
.login-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: var(--ink);
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}
.mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--indigo);
  color: #fff;
  font-weight: 700;
  font-size: 17px;
}
.title {
  margin: 0;
  font-size: 24px;
  letter-spacing: 0.01em;
}

.subtitle {
  margin: 6px 0 22px;
  color: var(--ink-2);
}

.hint {
  color: var(--ink-3);
  font-size: 12px;
  margin-top: 12px;
  line-height: 1.7;
}
.error {
  color: #c92a2a;
  background: #fdecec;
  border: 1px solid #f5c2c2;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  margin: 0 0 14px;
}
</style>
