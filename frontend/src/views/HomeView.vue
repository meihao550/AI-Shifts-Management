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
  { key: 'my-page', label: 'マイページ', to: '/mypage', icon: '🏠' },
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

<style scoped>
/* モックの通り、角丸タイルを3列で並べる。PC では中央寄せ。 */
.launcher {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px 16px;
  max-width: 400px;
  margin: 8px auto 0;
}

.tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--ink);
}

.tile__box {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--panel);
  border: 1px solid var(--line-2);
  border-radius: 24px;
  box-shadow: var(--shadow-panel);
  transition: transform 0.12s, border-color 0.12s, box-shadow 0.12s;
}

.tile:hover .tile__box {
  transform: translateY(-2px);
  border-color: var(--indigo);
  box-shadow: 0 4px 14px rgba(25, 28, 24, 0.1);
}

.tile:active .tile__box {
  transform: translateY(0);
}

.tile__icon {
  font-size: 40px;
  line-height: 1;
}

.tile__label {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
}
</style>
