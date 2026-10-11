<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

interface Tile {
  key: string
  label: string
  to: string
  icon: string
  adminOnly?: boolean
}

// スマホのホーム画面のように、各ページへ飛べるアイコンタイル。
// icon は絵文字の仮置き（後で画像へ差し替え可能）。
const allTiles: Tile[] = [
  { key: 'my-page', label: 'マイページ', to: '/dashboard', icon: '🏠' },
  { key: 'shift', label: 'シフト表', to: '/shift', icon: '📅' },
  { key: 'payroll', label: '人件費', to: '/payroll', icon: '💰', adminOnly: true },
  { key: 'employees', label: '従業員管理', to: '/employees', icon: '👥', adminOnly: true },
  { key: 'rules', label: 'ルール設定', to: '/rules', icon: '⚙️', adminOnly: true },
  { key: 'login-users', label: 'ログイン管理', to: '/login-users', icon: '🔑', adminOnly: true },
]

// 一般ユーザーには管理者専用タイルを出さない。
const tiles = computed(() => allTiles.filter((t) => !t.adminOnly || auth.isAdmin))
</script>

<template>
  <div class="launcher">
    <RouterLink v-for="t in tiles" :key="t.key" :to="t.to" class="tile">
      <span class="tile__box"><span class="tile__icon">{{ t.icon }}</span></span>
      <span class="tile__label">{{ t.label }}</span>
    </RouterLink>
  </div>
</template>
