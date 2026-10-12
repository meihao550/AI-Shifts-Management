<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDropdown, NModal, NSpace } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentTitle = computed(() => (route.meta.title as string) ?? '')

const nav = computed(() => {
  // 一般ユーザーはマイページとシフト表のみ。それ以外は管理者だけ。
  const items = [
    { key: 'home', label: 'ホーム', to: '/' },
    { key: 'my-page', label: 'マイページ', to: '/mypage' },
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
      <RouterLink to="/" class="brand" aria-label="ホーム">
        <img class="mark-img" :src="logoSrc" alt="" aria-hidden="true" />
      </RouterLink>
      <!-- 現在のページ名。ロゴ文字とハンバーガーを無くした分、大きめに表示。 -->
      <span v-if="currentTitle" class="page-title">{{ currentTitle }}</span>
      <!-- 画面が広いときのインラインナビ。狭いときはホーム(ランチャー)で代替。 -->
      <nav class="nav">
        <RouterLink v-for="item in nav" :key="item.key" :to="item.to" class="nav-item" active-class="active">
          {{ item.label }}
        </RouterLink>
      </nav>
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
  gap: 20px;
  align-items: center;
  height: 60px;
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

/* 現在ページ名の見出し（旧 pill を拡大） */
.page-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--ink);
  white-space: nowrap;
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
  margin-left: auto;
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

/* 1200px 以下: インラインナビは隠す（ナビはホームのランチャーで行う）。 */
@media (max-width: 1200px) {
  .nav {
    display: none;
  }
  .header-inner {
    gap: 14px;
  }
  /* 権限ラベルは省略して幅を確保（名前・アバターは残す）。 */
  .role {
    display: none;
  }
}
</style>
