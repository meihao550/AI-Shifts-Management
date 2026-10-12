<script setup lang="ts">
// 開発(ローカル)専用の補助ツール。LoginView から import.meta.env.DEV のときだけ
// 動的 import されるため、本番ビルドには含まれない。backend 側も development 限定。
import { NButton, useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const message = useMessage()

// Google を経由せず管理者としてログイン（backend も development 限定で 404 ガード済み）。
async function devLogin() {
  try {
    const { data } = await api.post<{ token: string }>('/auth/dev-login')
    auth.setToken(data.token)
    await auth.restore(true)
    router.push('/')
  } catch (e) {
    message.error(`開発用ログイン失敗: ${(e as Error).message}`)
  }
}

// デモ用のモックデータ（従業員・シフトパターン・必要人員）を投入。
async function seedMock() {
  try {
    await api.post('/dev/seed')
    message.success('モックデータを投入しました')
  } catch (e) {
    message.error(`モックデータ投入失敗: ${(e as Error).message}`)
  }
}
</script>

<template>
  <div class="dev-tools">
    <p class="dev-label">開発ツール（ローカル限定）</p>
    <NButton secondary block @click="devLogin">開発用ログイン（管理者）</NButton>
    <NButton secondary block style="margin-top: 8px" @click="seedMock">モックデータ投入</NButton>
  </div>
</template>

<style scoped>
/* 点線で仕切り、本番UIと混ざらない見た目に。 */
.dev-tools {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px dashed var(--line-2);
}
.dev-label {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  letter-spacing: 0.04em;
}
</style>
