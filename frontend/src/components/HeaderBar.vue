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
  const items = [
    { key: 'dashboard', label: 'ダッシュボード', to: '/dashboard' },
    { key: 'shift', label: 'シフト表', to: '/shift' },
    { key: 'payroll', label: '人件費', to: '/payroll' },
  ]
  if (auth.isAdmin) {
    items.push({ key: 'employees', label: '従業員管理', to: '/employees' })
    items.push({ key: 'rules', label: 'ルール設定', to: '/rules' })
  }
  return items
})

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
        <span class="mark" aria-hidden="true">勤</span>
        <span class="logo">シフト勤務表</span>
        <span v-if="currentTitle" class="pill">{{ currentTitle }}</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink v-for="item in nav" :key="item.key" :to="item.to" class="nav-item" active-class="active">
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="user">
        <NButton size="small" quaternary class="logout-btn" @click="showLogoutConfirm = true">
          ログアウト
        </NButton>
        <template v-if="auth.user">
          <NAvatar v-if="auth.user.picture_url" round size="small" :src="auth.user.picture_url"
            style="margin-right: 8px" />
          <span>{{ auth.user.name }}</span>
          <span class="role">{{ auth.user.role === 'admin' ? '管理者' : '社員' }}</span>
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

.mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 7px;
  background: var(--indigo);
  color: #fff;
  font-weight: 700;
  font-size: 16px;
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

.user :deep(.n-button) {
  color: var(--ink);
}

.role {
  margin-left: 8px;
  font-size: 11px;
  color: var(--ink-3);
}
</style>
