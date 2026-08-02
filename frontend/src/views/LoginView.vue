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
      <h1 class="title">AI-Shifts-Management</h1>
      <p class="subtitle">シフト作成を AI で 30 分に。</p>

      <NButton type="primary" size="large" block @click="loginWithGoogle">
        Google Workspace でログイン
      </NButton>

      <NDivider>うおｗ</NDivider>

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
  background: linear-gradient(140deg, #26314f, #4067a5);
}

.login-card {
  width: 440px;
  padding: 24px;
}

.title {
  margin: 0 0 4px;
  font-size: 22px;
}

.subtitle {
  margin: 0 0 24px;
  color: #6b7080;
}

.hint {
  color: #8892a6;
  font-size: 12px;
  margin-top: 12px;
}
</style>
