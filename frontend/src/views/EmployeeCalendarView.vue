<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NSelect, NSpace, NSpin, useMessage } from 'naive-ui'
import { useEmployeeStore } from '@/stores/employee'
import type { FixedScheduleItem, FixedScheduleStatus } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useEmployeeStore()
const message = useMessage()

const employeeId = computed(() => Number(route.params.employeeId))
const loading = ref(false)
const saving = ref(false)

// 月=0..日=6（date.weekday() 準拠）。UIは月始まりで表示する。
const WEEKDAYS = ['月', '火', '水', '木', '金', '土', '日']
// 各曜日の状態。'none' は「指定なし」（保存時に送らない）。
const states = ref<(FixedScheduleStatus | 'none')[]>(Array(7).fill('none'))

const options = [
  { label: '指定なし', value: 'none' },
  { label: '出勤', value: 'work' },
  { label: '休み', value: 'off' },
]

const employeeName = computed(
  () => store.employees.find((e) => e.id === employeeId.value)?.name ?? `#${employeeId.value}`,
)

onMounted(async () => {
  loading.value = true
  try {
    if (!store.employees.length) await store.fetchAll()
    const items = await store.getFixedSchedule(employeeId.value)
    const next: (FixedScheduleStatus | 'none')[] = Array(7).fill('none')
    for (const it of items) {
      if (it.day_of_week >= 0 && it.day_of_week <= 6) next[it.day_of_week] = it.status
    }
    states.value = next
  } catch (e) {
    message.error(`読み込み失敗: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    const items: FixedScheduleItem[] = states.value
      .map((st, dow) => ({ day_of_week: dow, status: st }))
      .filter((x): x is FixedScheduleItem => x.status !== 'none')
    await store.saveFixedSchedule(employeeId.value, items)
    message.success('固定カレンダーを保存しました')
  } catch (e) {
    message.error(`保存失敗: ${(e as Error).message}`)
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/employees')
}
</script>

<template>
  <NCard :title="`固定カレンダー：${employeeName}`">
    <template #header-extra>
      <NButton @click="goBack">← 従業員一覧へ戻る</NButton>
    </template>
    <NSpin :show="loading">
      <p style="color: var(--ink-3); font-size: 13px; margin-top: 0">
        毎月流用する曜日パターンです。「休み」の曜日はその月の該当日すべてを休みに、「出勤」は
        その日に入りやすくします。「指定なし」は制約なし。特定日の個別指定（希望・有給など）が
        あればそちらが優先されます。
      </p>
      <div class="weekday-grid">
        <div v-for="(label, dow) in WEEKDAYS" :key="dow" class="weekday-row">
          <span class="weekday-label">{{ label }}曜日</span>
          <NSelect v-model:value="states[dow]" :options="options" style="width: 160px" />
        </div>
      </div>
      <NSpace justify="end" style="margin-top: 16px">
        <NButton @click="goBack">キャンセル</NButton>
        <NButton type="primary" :loading="saving" @click="save">保存</NButton>
      </NSpace>
    </NSpin>
  </NCard>
</template>

<style scoped>
.weekday-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  max-width: 320px;
}
.weekday-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.weekday-label {
  font-weight: 600;
}
</style>
