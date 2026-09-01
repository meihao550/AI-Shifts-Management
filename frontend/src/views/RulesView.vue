<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NInputNumber,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  NTimePicker,
  NInput,
  NSwitch,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useRuleStore } from '@/stores/rule'
import type { DayCategory, HourlyStaffingRule, ShiftPattern } from '@/types'

const store = useRuleStore()
const message = useMessage()

const showPattern = ref(false)
const patternForm = ref<{
  code: string
  label: string
  start_time: number | null
  end_time: number | null
  category: string
  is_basic: boolean
}>({ code: '', label: '', start_time: null, end_time: null, category: 'morning', is_basic: true })

function toTimeString(ms: number | null): string {
  if (ms == null) return '09:00:00'
  const d = new Date(ms)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}:00`
}

const patternColumns: DataTableColumns<ShiftPattern> = [
  { title: 'コード', key: 'code' },
  { title: '表示名', key: 'label' },
  { title: '開始', key: 'start_time' },
  { title: '終了', key: 'end_time' },
  { title: '区分', key: 'category' },
  { title: '基本', key: 'is_basic', render: (r) => (r.is_basic ? '○' : 'Wワーク') },
  {
    title: '操作',
    key: 'ops',
    render: (row) =>
      h(
        NPopconfirm,
        { onPositiveClick: () => deletePattern(row.id) },
        {
          default: () => '削除しますか？',
          trigger: () =>
            h(NButton, { size: 'small', type: 'error', ghost: true }, () => '削除'),
        },
      ),
  },
]

async function addPattern() {
  try {
    await store.createPattern({
      code: patternForm.value.code,
      label: patternForm.value.label,
      start_time: toTimeString(patternForm.value.start_time),
      end_time: toTimeString(patternForm.value.end_time),
      category: patternForm.value.category,
      is_basic: patternForm.value.is_basic,
    })
    message.success('追加しました')
    showPattern.value = false
  } catch (e) {
    message.error(`追加失敗: ${(e as Error).message}`)
  }
}

async function deletePattern(id: number) {
  try {
    await store.deletePattern(id)
    message.success('削除しました')
  } catch (e) {
    message.error(`削除失敗: ${(e as Error).message}`)
  }
}

// --- 時間別必要人数 (時間カバレッジ方式) ---
// 営業日は 1:00 起点。拡張時 1〜24（24 = 翌0:00-1:00）を行にする。
const HOURS = Array.from({ length: 24 }, (_, i) => i + 1) // 1..24

// hour -> 必要人数。曜日区分ごとに保持。
const weekday = ref<Record<number, number>>({})
const weekend = ref<Record<number, number>>({})

function hourLabel(hour: number): string {
  // 24:00-25:00 のような拡張時表記（要件書§12.2）
  return `${hour}:00–${hour + 1}:00`
}

function defaultRequired(hour: number, isWeekend: boolean): number {
  if (hour >= 1 && hour <= 8) return 1 // 深夜 1:00-9:00
  if (hour >= 9 && hour <= 16) return isWeekend ? 3 : 2 // 朝 9:00-17:00
  if (hour >= 17 && hour <= 24) return isWeekend ? 3 : 2 // 夜 17:00-翌1:00
  return 0
}

async function loadHourlyStaffing() {
  await store.fetchHourlyStaffing()
  const wd: Record<number, number> = {}
  const we: Record<number, number> = {}
  for (const hour of HOURS) {
    wd[hour] = defaultRequired(hour, false)
    we[hour] = defaultRequired(hour, true)
  }
  // サーバに保存済みがあれば上書き
  for (const r of store.hourlyStaffing) {
    if (r.day_category === 'weekday') wd[r.hour] = r.required
    else we[r.hour] = r.required
  }
  weekday.value = wd
  weekend.value = we
}

async function saveHourlyStaffing() {
  const rows: HourlyStaffingRule[] = []
  for (const hour of HOURS) {
    rows.push({ day_category: 'weekday' as DayCategory, hour, required: weekday.value[hour] ?? 0 })
    rows.push({
      day_category: 'weekend_or_holiday' as DayCategory,
      hour,
      required: weekend.value[hour] ?? 0,
    })
  }
  try {
    await store.saveHourlyStaffing(rows)
    message.success('保存しました')
  } catch (e) {
    message.error(`保存失敗: ${(e as Error).message}`)
  }
}

onMounted(async () => {
  await Promise.all([store.fetchPatterns(), loadHourlyStaffing()])
})
</script>

<template>
  <NSpace vertical>
    <NCard title="シフトパターン">
      <template #header-extra>
        <NButton type="primary" @click="showPattern = true">＋ パターン追加</NButton>
      </template>
      <p style="margin-top: 0; color: #6b7080">
        基本パターン(朝/夜/深夜)に加え、Wワーク向けの不定時刻パターンもここから追加できます
        (「基本パターン」を OFF にすると Wワーク扱い)。
      </p>
      <NDataTable :columns="patternColumns" :data="store.patterns" />
    </NCard>

    <NCard title="必要人員 (1時間ごと × 曜日区分)">
      <template #header-extra>
        <NButton type="primary" @click="saveHourlyStaffing">保存</NButton>
      </template>
      <p style="margin-top: 0; color: #6b7080">
        営業日は 1:00 起点で扱います。深夜跨ぎは拡張時表記(24:00 = 翌0:00)。各時間ちょうどの
        人数になるよう配置します。
      </p>
      <table class="staffing">
        <thead>
          <tr>
            <th>時間帯</th>
            <th>平日</th>
            <th>土日祝</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="hour in HOURS" :key="hour">
            <td>{{ hourLabel(hour) }}</td>
            <td>
              <NInputNumber v-model:value="weekday[hour]" :min="0" style="width: 100px" />
            </td>
            <td>
              <NInputNumber v-model:value="weekend[hour]" :min="0" style="width: 100px" />
            </td>
          </tr>
        </tbody>
      </table>
    </NCard>

    <NModal
      v-model:show="showPattern"
      preset="card"
      title="シフトパターン追加"
      style="width: 480px"
    >
      <NSpace vertical>
        <NInput v-model:value="patternForm.code" placeholder="コード (例: w_20_01)" />
        <NInput v-model:value="patternForm.label" placeholder="表示名 (例: Wワーク 20:00-01:00)" />
        <NTimePicker v-model:value="patternForm.start_time" format="HH:mm" placeholder="開始時刻" />
        <NTimePicker v-model:value="patternForm.end_time" format="HH:mm" placeholder="終了時刻" />
        <NSelect
          v-model:value="patternForm.category"
          :options="[
            { label: '朝', value: 'morning' },
            { label: '夜', value: 'evening' },
            { label: '深夜', value: 'night' },
          ]"
        />
        <NSpace align="center">
          <span>基本パターン:</span>
          <NSwitch v-model:value="patternForm.is_basic" />
          <span style="color: #8892a6; font-size: 12px">OFF = Wワーク(不定時刻)</span>
        </NSpace>
        <NButton type="primary" block @click="addPattern">追加</NButton>
      </NSpace>
    </NModal>
  </NSpace>
</template>

<style scoped>
.staffing {
  width: 100%;
  border-collapse: collapse;
}
.staffing th,
.staffing td {
  padding: 8px 12px;
  border: 1px solid #dde1e8;
  text-align: left;
}
.staffing th {
  background: #f2f4f9;
}
</style>
