<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NSpin } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

onMounted(async () => {
  const token = route.query.token as string | undefined
  if (token) {
    auth.setToken(token)
    await auth.restore(true) // 既に hydrated 済みでも、ログイン直後は user を取り直す
    router.replace('/dashboard')
  } else {
    router.replace('/login')
  }
})
</script>

<template>
  <div class="wrap">
    <NSpin size="large" />
    <p>ログイン処理中…</p>
  </div>
</template>

<style scoped>
.wrap {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
</style>
