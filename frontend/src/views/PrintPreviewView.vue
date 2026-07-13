<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NCard, NSpace } from 'naive-ui'

const route = useRoute()
const shiftId = route.params.shiftId
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const token = localStorage.getItem('token') || ''

async function download(kind: 'pdf' | 'excel') {
  const url = `${apiBase}/api/shifts/${shiftId}/export/${kind}`
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `shift-${shiftId}.${kind === 'pdf' ? 'pdf' : 'xlsx'}`
  a.click()
  URL.revokeObjectURL(a.href)
}

const previewUrl = computed(
  () => `${apiBase}/api/shifts/${shiftId}/export/pdf#toolbar=1`,
)
</script>

<template>
  <NCard title="印刷プレビュー">
    <template #header-extra>
      <NSpace>
        <NButton @click="download('pdf')">PDF ダウンロード</NButton>
        <NButton @click="download('excel')">Excel ダウンロード</NButton>
      </NSpace>
    </template>
    <p style="color: #6b7080; margin: 0 0 16px">
      PDF/Excel を直接ダウンロードできます。ブラウザで開くには下記プレビューをご利用ください。
      <br />
      ※ プレビューには認証済みのタブが必要です。
    </p>
    <object :data="previewUrl" type="application/pdf" width="100%" height="800px">
      <p>PDF プレビューを表示できません。上のボタンからダウンロードしてください。</p>
    </object>
  </NCard>
</template>
