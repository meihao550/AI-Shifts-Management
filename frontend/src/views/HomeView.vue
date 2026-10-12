<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
// ナビのアイコン（idea/icon のラインアート）。マスク画像を currentColor で塗る（ライト/ダーク両対応）。
import myPageIcon from '@/assets/nav/my-page.png'
import shiftIcon from '@/assets/nav/shift.png'
import requestsIcon from '@/assets/nav/requests.png'
import payrollIcon from '@/assets/nav/payroll.png'
import employeesIcon from '@/assets/nav/employees.png'
import rulesIcon from '@/assets/nav/rules.png'
import loginUsersIcon from '@/assets/nav/login-users.png'

const auth = useAuthStore()
const themeStore = useThemeStore()

// マスク画像を CSS 変数で渡す（.nav-ic が currentColor で塗る）。
function iconStyle(url: string) {
  return { '--nav-ic': `url(${url})` }
}

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
  { key: 'my-page', label: 'マイページ', to: '/mypage', icon: myPageIcon },
  { key: 'shift', label: 'シフト表', to: '/shift', icon: shiftIcon },
  { key: 'requests', label: '希望提出', to: '/requests', icon: requestsIcon },
  { key: 'payroll', label: '人件費', to: '/payroll', icon: payrollIcon, adminOnly: true },
  { key: 'employees', label: '従業員管理', to: '/employees', icon: employeesIcon, adminOnly: true },
  { key: 'rules', label: 'ルール設定', to: '/rules', icon: rulesIcon, adminOnly: true },
  { key: 'login-users', label: 'ログイン管理', to: '/login-users', icon: loginUsersIcon, adminOnly: true },
]

// 一般ユーザーには管理者専用タイルを出さない。
const tiles = computed(() => allTiles.filter((t) => !t.adminOnly || auth.isAdmin))
</script>

<template>
  <div class="launcher">
    <RouterLink v-for="t in tiles" :key="t.key" :to="t.to" class="tile">
      <span class="tile__box"><span class="tile__icon nav-ic" :style="iconStyle(t.icon)"></span></span>
      <span class="tile__label">{{ t.label }}</span>
    </RouterLink>

    <!-- 星マークで画面を暗転/復帰（ダーク/ライト切替）。遷移せずその場で反映。 -->
    <button type="button" class="tile tile--button" @click="themeStore.toggle()">
      <span class="tile__box">
        <span class="tile__icon">
          <svg width="40" height="40" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
              :fill="themeStore.isDark ? 'currentColor' : 'none'"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linejoin="round"
            />
          </svg>
        </span>
      </span>
      <span class="tile__label">{{ themeStore.isDark ? '明るくする' : '暗くする' }}</span>
    </button>
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
/* 星トグルはボタン要素なので既定装飾をリセットしてタイルと揃える。 */
.tile--button {
  background: none;
  border: none;
  cursor: pointer;
  font: inherit;
  padding: 0;
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
/* マスク画像を currentColor で塗るアイコン（ライト/ダーク両対応）。 */
.nav-ic {
  display: inline-block;
  width: 40px;
  height: 40px;
  background-color: currentColor;
  -webkit-mask-image: var(--nav-ic);
  mask-image: var(--nav-ic);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.tile__label {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
}
</style>
