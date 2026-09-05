<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NDivider, NForm, NFormItem, NInput, useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const message = useMessage()

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const devEmail = ref('admin@example.com')
const devName = ref('管理者')

function loginWithGoogle() {
  window.location.href = `${apiBase}/api/auth/google/login`
}

async function loginDev() {
  try {
    await auth.devLogin(devEmail.value, devName.value)
    router.replace('/dashboard')
  } catch (e) {
    message.error(`ログインに失敗しました: ${(e as Error).message}`)
  }
}

async function seed() {
  try {
    const res = await fetch(`${apiBase}/api/dev/seed`, { method: 'POST' })
    if (!res.ok) throw new Error(await res.text())
    message.success('サンプルデータを投入しました')
  } catch (e) {
    message.error(`投入失敗: ${(e as Error).message}`)
  }
}

async function reset() {
  if (!window.confirm('全データを削除して 25 名分のサンプルを再投入します。よろしいですか？')) return
  try {
    const res = await fetch(`${apiBase}/api/dev/reset`, { method: 'POST' })
    if (!res.ok) throw new Error(await res.text())
    message.success('リセット完了')
  } catch (e) {
    message.error(`リセット失敗: ${(e as Error).message}`)
  }
}
</script>

<template>
  <div class="login-shell">
    <NCard class="login-card">
      <div class="brand-row">
        <span class="mark" aria-hidden="true">勤</span>
        <h1 class="title">シフト勤務表</h1>
      </div>
      <p class="subtitle">月のシフトを組み、人件費まで一枚で。</p>

      <NButton type="primary" size="large" block @click="loginWithGoogle">
        Google Workspace でログイン
      </NButton>

      <NDivider>開発用</NDivider>

      <NForm label-placement="left" label-width="80px">
        <NFormItem label="Email">
          <NInput v-model:value="devEmail" placeholder="admin@example.com" />
        </NFormItem>
        <NFormItem label="Name">
          <NInput v-model:value="devName" placeholder="管理者" />
        </NFormItem>
      </NForm>
      <NButton block @click="loginDev">開発用ログイン (dev only)</NButton>
      <NButton block secondary style="margin-top: 8px" @click="seed">
        サンプルデータ投入 (25 名分)
      </NButton>
      <NButton block secondary type="warning" style="margin-top: 8px" @click="reset">
        データ全リセット + サンプル再投入
      </NButton>
      <p class="hint">
        本番環境では利用不可。 <br />
        初回にログインしたユーザは自動的に <b>管理者</b> になります。 <br />
        「サンプルデータ投入」を押すと従業員 25 名 + シフトパターン + 必要人員が入ります。
      </p>
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
  background-image: linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 28px 28px;
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
/* 上端に時間帯(朝→夕→深夜)の帯を1本 */
.login-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: linear-gradient(90deg, var(--morning), var(--evening), var(--night));
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
</style>
