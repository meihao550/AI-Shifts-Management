<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NCard,
  NModal,
  NRadio,
  NRadioGroup,
  NSpace,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui'
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
type Status = FixedScheduleStatus | 'none'
// 各曜日の状態。'none' は「指定なし」（保存時に送らない）。
const states = ref<Status[]>(Array(7).fill('none'))

// 状態の表示メタ（ラベル・タグ色）。
const STATUS_META: Record<Status, { label: string; type: 'default' | 'success' | 'warning' | 'error' }> = {
  none: { label: '指定なし', type: 'default' },
  work_hard: { label: '確定出勤', type: 'success' },
  work: { label: '出勤(ソフト)', type: 'warning' },
  off: { label: '休み', type: 'error' },
}
const editOptions: Status[] = ['none', 'work_hard', 'work', 'off']

// 編集モーダルの状態。
const showEdit = ref(false)
const editingDow = ref<number | null>(null)
const editingValue = ref<Status>('none')

const employeeName = computed(
  () => store.employees.find((e) => e.id === employeeId.value)?.name ?? `#${employeeId.value}`,
)

onMounted(async () => {
  loading.value = true
  try {
    if (!store.employees.length) await store.fetchAll()
    const items = await store.getFixedSchedule(employeeId.value)
    const next: Status[] = Array(7).fill('none')
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

function openEdit(dow: number) {
  editingDow.value = dow
  editingValue.value = states.value[dow]
  showEdit.value = true
}

function applyEdit() {
  if (editingDow.value !== null) states.value[editingDow.value] = editingValue.value
  showEdit.value = false
  editingDow.value = null
}

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
        毎月流用する曜日パターンです。曜日を選んで編集します。<b>確定出勤</b>はその曜日に必ず入れます
        （満たせない場合は生成時に警告）。<b>出勤(ソフト)</b>は入りやすくする希望、<b>休み</b>はその曜日を
        休みに、<b>指定なし</b>は制約なしです。特定日の個別指定があればそちらが優先されます。
      </p>
      <div class="weekday-grid">
        <div v-for="(label, dow) in WEEKDAYS" :key="dow" class="weekday-row">
          <span class="weekday-label">{{ label }}曜日</span>
          <NSpace align="center">
            <NTag :type="STATUS_META[states[dow]].type" size="small">
              {{ STATUS_META[states[dow]].label }}
            </NTag>
            <NButton size="small" @click="openEdit(dow)">編集</NButton>
          </NSpace>
        </div>
      </div>
      <NSpace justify="end" style="margin-top: 16px">
        <NButton @click="goBack">キャンセル</NButton>
        <NButton type="primary" :loading="saving" @click="save">保存</NButton>
      </NSpace>
    </NSpin>

    <NModal
      v-model:show="showEdit"
      preset="card"
      :title="editingDow !== null ? `${WEEKDAYS[editingDow]}曜日の設定` : ''"
      style="width: 360px"
    >
      <NRadioGroup v-model:value="editingValue">
        <NSpace vertical>
          <NRadio v-for="opt in editOptions" :key="opt" :value="opt">
            {{ STATUS_META[opt].label }}
          </NRadio>
        </NSpace>
      </NRadioGroup>
      <NSpace justify="end" style="margin-top: 16px">
        <NButton @click="showEdit = false">キャンセル</NButton>
        <NButton type="primary" @click="applyEdit">決定</NButton>
      </NSpace>
    </NModal>
  </NCard>
</template>

<style scoped>
.weekday-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  max-width: 360px;
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
