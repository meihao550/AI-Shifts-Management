<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDrawer, NDrawerContent, NDropdown, NModal, NSpace } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
// ナビのアイコン（idea/icon のラインアート）。白背景を透明化したマスク画像で、
// CSS の mask-image + background-color: currentColor により文字色で塗る（ライト/ダーク両対応）。
import myPageIcon from '@/assets/nav/my-page.png'
import shiftIcon from '@/assets/nav/shift.png'
import requestsIcon from '@/assets/nav/requests.png'
import payrollIcon from '@/assets/nav/payroll.png'
import employeesIcon from '@/assets/nav/employees.png'
import rulesIcon from '@/assets/nav/rules.png'
import loginUsersIcon from '@/assets/nav/login-users.png'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const themeStore = useThemeStore()

const currentTitle = computed(() => (route.meta.title as string) ?? '')

// ナビ項目（アイコン付き）。アイコンは絵文字の仮置き（ランチャーと統一）。
interface NavItem {
  key: string
  label: string
  to: string
  icon: string
  adminOnly?: boolean
}
const allNav: NavItem[] = [
  // ホームは PC では自動的にマイページへ飛ぶため、メニューには出さない（ドロワーは PC 専用）。
  { key: 'my-page', label: 'マイページ', to: '/mypage', icon: myPageIcon },
  { key: 'shift', label: 'シフト表', to: '/shift', icon: shiftIcon },
  { key: 'requests', label: '希望提出', to: '/requests', icon: requestsIcon },
  { key: 'payroll', label: '人件費', to: '/payroll', icon: payrollIcon, adminOnly: true },
  { key: 'employees', label: '従業員管理', to: '/employees', icon: employeesIcon, adminOnly: true },
  { key: 'rules', label: 'ルール設定', to: '/rules', icon: rulesIcon, adminOnly: true },
  { key: 'login-users', label: 'ログイン管理', to: '/login-users', icon: loginUsersIcon, adminOnly: true },
]

// マスク画像を CSS 変数で渡す（.nav-ic が currentColor で塗る）。
function iconStyle(url: string) {
  return { '--nav-ic': `url(${url})` }
}
// 一般ユーザーには管理者専用を出さない。
const nav = computed(() => allNav.filter((i) => !i.adminOnly || auth.isAdmin))

// 左ドロワー（メニュー）の開閉。
const showMenu = ref(false)
function go(to: string) {
  showMenu.value = false
  router.push(to)
}

// public/ 配信物。静的 src だとビルド時に import 解決されるため :src（実行時参照）で渡す。
const logoSrc = '/favicon.png'

// アバター click で開くユーザーメニュー（ログアウト）。
const userMenuOptions = [{ label: 'ログアウト', key: 'logout' }]
function handleUserMenu(key: string) {
  if (key === 'logout') showLogoutConfirm.value = true
}

const showLogoutConfirm = ref(false)

function doLogout() {
  showLogoutConfirm.value = false
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="header">
    <!-- グリッド 1fr auto 1fr: 左(ハンバーガー+ロゴ) / 中央(現在ページ名) / 右(ユーザー) -->
    <div class="header-inner">
      <div class="header-left">
        <!-- 左端のハンバーガー（PC のみ）。押すと左ドロワーを開く。 -->
        <button
          type="button"
          class="hamburger-btn nav-hamburger"
          aria-label="メニューを開く"
          @click="showMenu = true"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M4 7h16M4 12h16M4 17h16"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
            />
          </svg>
        </button>
        <RouterLink to="/" class="brand" aria-label="ホーム">
          <img class="mark-img" :src="logoSrc" alt="" aria-hidden="true" />
        </RouterLink>
      </div>

      <!-- 中央: 今見ている画面名 -->
      <span v-if="currentTitle" class="page-title">{{ currentTitle }}</span>
      <span v-else aria-hidden="true"></span>

      <div class="user">
        <template v-if="auth.user">
          <NDropdown
            trigger="click"
            size="large"
            placement="bottom-end"
            :options="userMenuOptions"
            @select="handleUserMenu"
          >
            <button type="button" class="user-trigger" aria-label="ユーザーメニュー">
              <NAvatar round size="small" :src="auth.user.picture_url || undefined">
                {{ auth.user.name.charAt(0) }}
              </NAvatar>
              <span class="user-name">{{ auth.user.name }}</span>
              <span class="role">{{ auth.user.role === 'admin' ? '管理者' : '社員' }}</span>
            </button>
          </NDropdown>
        </template>
      </div>
    </div>
  </header>

  <!-- 左スライドのメニュードロワー。右側はオーバーレイで暗転。 -->
  <NDrawer v-model:show="showMenu" :width="288" placement="left">
    <NDrawerContent closable>
      <template #header>
        <div class="menu-head">
          <img class="mark-img" :src="logoSrc" alt="" aria-hidden="true" />
          <span class="menu-title">シフト勤務表</span>
        </div>
      </template>
      <nav class="menu-list">
        <a
          v-for="item in nav"
          :key="item.key"
          class="menu-item"
          :class="{ active: route.path === item.to }"
          href="#"
          @click.prevent="go(item.to)"
        >
          <span class="menu-icon nav-ic" aria-hidden="true" :style="iconStyle(item.icon)"></span>
          <span class="menu-label">{{ item.label }}</span>
        </a>

        <!-- 星マークで画面を暗転/復帰（ダーク/ライト切替）。ドロワーは閉じずその場で反映。 -->
        <div class="menu-divider"></div>
        <button type="button" class="menu-item theme-toggle" @click="themeStore.toggle()">
          <span class="menu-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24">
              <path
                d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
                :fill="themeStore.isDark ? 'currentColor' : 'none'"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linejoin="round"
              />
            </svg>
          </span>
          <span class="menu-label">{{ themeStore.isDark ? '画面を明るくする' : '画面を暗くする' }}</span>
        </button>
      </nav>
    </NDrawerContent>
  </NDrawer>

  <NModal v-model:show="showLogoutConfirm" preset="card" title="確認" style="width: 360px">
    <p style="margin: 0 0 16px">ログアウトしますか？</p>
    <NSpace justify="end">
      <NButton @click="showLogoutConfirm = false">いいえ</NButton>
      <NButton type="primary" @click="doLogout">はい</NButton>
    </NSpace>
  </NModal>
</template>

<style scoped>
.header {
  background: var(--panel);
  color: var(--ink);
  /* 下端は黒いライン1本。 */
  border-bottom: 2px solid var(--ink);
  box-shadow: 0 1px 3px rgba(25, 28, 24, 0.06);
}

/* 左右の幅に関係なく中央列(ページ名)が常にヘッダー中央に来るよう 1fr auto 1fr。 */
.header-inner {
  max-width: var(--page-max-width);
  margin: 0 auto;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  justify-self: start;
}

.hamburger-btn {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--line-2);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.hamburger-btn:hover {
  background: var(--panel-strip);
  border-color: var(--indigo);
  color: var(--indigo-700);
}

.brand {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: var(--ink);
}

.mark-img {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  object-fit: cover;
  display: block;
}

/* 中央: 現在ページ名 */
.page-title {
  justify-self: center;
  text-align: center;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--ink);
  white-space: nowrap;
}

.user {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-self: end;
}

/* アバター+名前をまとめた click ターゲット（押すとログアウトメニュー）。 */
.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  color: var(--ink);
  font: inherit;
  transition: background 0.12s, border-color 0.12s;
}
.user-trigger:hover {
  background: var(--panel-strip);
  border-color: var(--line);
}
.user-name {
  font-weight: 600;
  font-size: 14px;
}

.role {
  font-size: 11px;
  color: var(--ink-3);
}

/* ドロワーのヘッダー（ロゴ+アプリ名） */
.menu-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.menu-title {
  font-weight: 700;
  font-size: 16px;
}

/* ドロワーのナビ一覧 */
.menu-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 10px;
  border-radius: 8px;
  text-decoration: none;
  color: var(--ink);
  font-weight: 500;
  transition: background 0.12s, color 0.12s;
}
.menu-item:hover {
  background: var(--panel-strip);
}
.menu-item.active {
  background: var(--indigo-050);
  color: var(--indigo-700);
}
.menu-icon {
  font-size: 20px;
  line-height: 1;
  width: 24px;
  text-align: center;
}
/* マスク画像を currentColor で塗るアイコン（ライト/ダーク両対応）。 */
.nav-ic {
  display: inline-block;
  width: 22px;
  height: 22px;
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
.menu-label {
  font-size: 15px;
}

/* ドロワー下部の区切り線＋星トグル（画面の暗転）。 */
.menu-divider {
  height: 1px;
  background: var(--line);
  margin: 8px 4px;
}
.theme-toggle {
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  font: inherit;
  text-align: left;
  color: var(--ink);
}

/* モバイル(狭幅): ハンバーガーは出さず、ナビはホーム(ランチャー)で代替。 */
@media (max-width: 768px) {
  .nav-hamburger {
    display: none;
  }
  .role {
    display: none;
  }
  .user-name {
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
