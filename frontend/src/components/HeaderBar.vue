<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDropdown } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

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

const menuOptions = [{ label: 'ログアウト', key: 'logout' }]

function onMenu(key: string) {
  if (key === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <div class="brand">
        <span class="logo">AI-Shifts</span>
        <span class="pill">{{ currentTitle }}</span>
      </div>
      <nav class="nav">
        <RouterLink
          v-for="item in nav"
          :key="item.key"
          :to="item.to"
          class="nav-item"
          active-class="active"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="user">
        <NDropdown :options="menuOptions" @select="onMenu">
          <NButton text>
            <template v-if="auth.user">
              <NAvatar
                v-if="auth.user.picture_url"
                round
                size="small"
                :src="auth.user.picture_url"
                style="margin-right: 8px"
              />
              <span>{{ auth.user.name }}</span>
              <span class="role">{{ auth.user.role === 'admin' ? '管理者' : '社員' }}</span>
            </template>
          </NButton>
        </NDropdown>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  background: #1e2a4a;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
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
  align-items: baseline;
  gap: 12px;
  min-width: 220px;
}
.logo {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.5px;
}
.pill {
  padding: 2px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
}
.nav {
  display: flex;
  gap: 16px;
  flex: 1;
}
.nav-item {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 14px;
}
.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}
.nav-item.active {
  color: #fff;
  background: rgba(80, 160, 255, 0.25);
}
.user :deep(.n-button) {
  color: #fff;
}
.role {
  margin-left: 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
}
</style>
