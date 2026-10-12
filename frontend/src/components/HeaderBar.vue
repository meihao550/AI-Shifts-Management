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

// 左端ハンバーガーのメニュー項目（key=遷移先パス）。選択で push。
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
    <!-- グリッド 1fr auto 1fr: 左(ハンバーガー+ロゴ) / 中央(現在ページ名) / 右(ユーザー) -->
    <div class="header-inner">
      <div class="header-left">
        <!-- 左端のハンバーガー（PC のみ）。狭幅ではホーム(ランチャー)で代替するため隠す。 -->
        <div class="nav-hamburger">
          <NDropdown
            trigger="click"
            size="large"
            placement="bottom-start"
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
