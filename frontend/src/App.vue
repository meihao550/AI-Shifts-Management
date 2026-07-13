<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { NConfigProvider, NMessageProvider, NNotificationProvider, dateJaJP, jaJP } from 'naive-ui'
import HeaderBar from '@/components/HeaderBar.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const showHeader = computed(() => route.meta.hideHeader !== true && auth.isAuthenticated)

onMounted(async () => {
  await auth.restore()
})
</script>

<template>
  <n-config-provider :locale="jaJP" :date-locale="dateJaJP">
    <n-message-provider>
      <n-notification-provider>
        <div class="app-shell">
          <HeaderBar v-if="showHeader" />
          <main class="app-main">
            <router-view />
          </main>
        </div>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
:root {
  --page-max-width: 1400px;
}
body {
  margin: 0;
  font-family:
    'Hiragino Kaku Gothic ProN',
    'Noto Sans JP',
    system-ui,
    sans-serif;
  background: #f6f7fb;
  color: #202226;
}
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-main {
  flex: 1;
  padding: 24px;
  max-width: var(--page-max-width);
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
