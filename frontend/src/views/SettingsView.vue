<script setup lang="ts">
import { NCard, NRadio, NRadioGroup, NSpace } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import type { ThemeMode } from '@/stores/theme'

const theme = useThemeStore()

function onChange(value: string | number | boolean) {
  theme.setMode(value as ThemeMode)
}
</script>

<template>
  <NCard title="画面設定">
    <div class="setting-row">
      <div class="setting-label">
        <p class="setting-title">背景</p>
        <p class="setting-desc">画面全体の配色を切り替えます（この端末に保存されます）。</p>
      </div>
      <NRadioGroup :value="theme.mode" @update:value="onChange">
        <NSpace>
          <NRadio value="light">白（ライト）</NRadio>
          <NRadio value="dark">黒（ダーク）</NRadio>
        </NSpace>
      </NRadioGroup>
    </div>
  </NCard>
</template>

<style scoped>
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.setting-title {
  margin: 0;
  font-weight: 600;
}
.setting-desc {
  margin: 4px 0 0;
  color: var(--ink-3);
  font-size: 13px;
}
</style>
