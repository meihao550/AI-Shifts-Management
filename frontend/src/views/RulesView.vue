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
import type { ShiftPattern, StaffingRule } from '@/types'

const store = useRuleStore()
const message = useMessage()

onMounted(async () => {
  await Promise.all([store.fetchPatterns(), store.fetchStaffing()])
})

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
  { title: '基本', key: 'is_basic', render: (r) => (r.is_basic ? '○' : '') },
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

const staffingRows = ref<StaffingRule[]>([])

async function loadStaffing() {
  await store.fetchStaffing()
  staffingRows.value =
    store.staffing.length > 0
      ? store.staffing.map((r) => ({ ...r }))
      : defaultStaffing()
}

function defaultStaffing(): StaffingRule[] {
  return [
    { day_category: 'weekday', shift_category: 'morning', required: 2 },
    { day_category: 'weekday', shift_category: 'evening', required: 2 },
    { day_category: 'weekday', shift_category: 'night', required: 1 },
    { day_category: 'weekend_or_holiday', shift_category: 'morning', required: 3 },
    { day_category: 'weekend_or_holiday', shift_category: 'evening', required: 3 },
    { day_category: 'weekend_or_holiday', shift_category: 'night', required: 1 },
  ]
}

async function saveStaffing() {
  try {
    await store.saveStaffing(staffingRows.value)
    message.success('保存しました')
  } catch (e) {
    message.error(`保存失敗: ${(e as Error).message}`)
  }
}

onMounted(loadStaffing)
</script>

<template>
  <NSpace vertical>
    <NCard title="シフトパターン">
      <template #header-extra>
        <NButton type="primary" @click="showPattern = true">＋ パターン追加</NButton>
      </template>
      <NDataTable :columns="patternColumns" :data="store.patterns" />
    </NCard>

    <NCard title="必要人員 (曜日区分 × シフト区分)">
      <template #header-extra>
        <NButton type="primary" @click="saveStaffing">保存</NButton>
      </template>
      <table class="staffing">
        <thead>
          <tr>
            <th>日区分</th>
            <th>シフト区分</th>
            <th>必要人数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in staffingRows" :key="i">
            <td>{{ row.day_category === 'weekday' ? '平日' : '土日祝' }}</td>
            <td>
              {{
                row.shift_category === 'morning'
                  ? '朝'
                  : row.shift_category === 'evening'
                    ? '夜'
                    : '深夜'
              }}
            </td>
            <td>
              <NInputNumber v-model:value="row.required" :min="0" style="width: 100px" />
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
        <NInput v-model:value="patternForm.code" placeholder="コード (例: morning)" />
        <NInput v-model:value="patternForm.label" placeholder="表示名 (例: 朝 09:00-17:00)" />
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
