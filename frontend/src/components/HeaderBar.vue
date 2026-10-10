<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDropdown, NModal, NSpace } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { ref } from 'vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentTitle = computed(() => (route.meta.title as string) ?? '')

const nav = computed(() => {
  // 一般ユーザーはダッシュボードとシフト表のみ。それ以外は管理者だけ。
  const items = [
    { key: 'dashboard', label: 'ダッシュボード', to: '/dashboard' },
    { key: 'shift', label: 'シフト表', to: '/shift' },
  ]
  if (auth.isAdmin) {
    items.push({ key: 'payroll', label: '人件費', to: '/payroll' })
    items.push({ key: 'employees', label: '従業員管理', to: '/employees' })
    items.push({ key: 'rules', label: 'ルール設定', to: '/rules' })
    items.push({ key: 'login-users', label: 'ログイン管理', to: '/login-users' })
  }
  return items
})

// 狭い画面(≤1200px)用ハンバーガーの項目。key に遷移先パスを入れて select で push。
const dropdownOptions = computed(() => nav.value.map((i) => ({ label: i.label, key: i.to })))
function handleNavSelect(key: string) {
  router.push(key)
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
    <div class="header-inner">
      <RouterLink to="/dashboard" class="brand">
        <img class="mark-img" :src="logoSrc" alt="" aria-hidden="true" />
        <span class="logo">シフト勤務表</span>
        <span v-if="currentTitle" class="pill">{{ currentTitle }}</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink v-for="item in nav" :key="item.key" :to="item.to" class="nav-item" active-class="active">
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="nav-hamburger">
        <NDropdown
          trigger="click"
          size="large"
          placement="bottom-end"
          :options="dropdownOptions"
          @select="handleNavSelect"
        >
          <button type="button" class="hamburger-btn" aria-label="メニュー">
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
        </NDropdown>
      </div>
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
  /* 時間帯(朝→夕→深夜)の細い帯を1本だけ下端に。この題材の署名的ディテール。 */
  border-bottom: 2px solid transparent;
  border-image: linear-gradient(90deg,
      var(--morning) 0%,
      var(--evening) 50%,
      var(--night) 100%) 1;
  box-shadow: 0 1px 3px rgba(25, 28, 24, 0.06);
}

.header-inner {
  max-width: var(--page-max-width);
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  gap: 32px;
  align-items: center;
  height: 60px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 200px;
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

.logo {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.02em;
}

.pill {
  padding: 2px 9px;
  border-radius: var(--r-chip);
  background: var(--indigo-050);
  color: var(--indigo-700);
  font-size: 12px;
  font-weight: 600;
}

.nav {
  display: flex;
  gap: 6px;
  flex: 1;
}

.nav-item {
  position: relative;
  color: var(--ink-2);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.12s, background 0.12s;
}

.nav-item:hover {
  color: var(--ink);
  background: var(--panel-strip);
}

.nav-item.active {
  color: var(--indigo-700);
  background: var(--indigo-050);
}

.user {
  display: flex;
  align-items: center;
  gap: 8px;
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

/* ハンバーガーは広い画面では隠す。 */
.nav-hamburger {
  display: none;
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

/* 1200px 以下: inline ナビをハンバーガーに集約し、横溢れを防ぐ。 */
@media (max-width: 1200px) {
  .nav {
    display: none;
  }
  .nav-hamburger {
    display: flex;
    flex: 1;
    justify-content: flex-end;
  }
  .header-inner {
    gap: 16px;
  }
  .brand {
    min-width: auto;
  }
  /* 権限ラベルは省略して幅を確保（名前・アバターは残す）。 */
  .role {
    display: none;
  }
}
</style>
