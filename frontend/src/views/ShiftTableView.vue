<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NCard,
  NDatePicker,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSpace,
  NSpin,
  NSwitch,
  NTag,
  useMessage,
} from 'naive-ui'
import { useShiftStore } from '@/stores/shift'
import { useEmployeeStore } from '@/stores/employee'
import { useRuleStore } from '@/stores/rule'
import type { AvailabilityKind } from '@/types'

const shiftStore = useShiftStore()
const employeeStore = useEmployeeStore()
const ruleStore = useRuleStore()
const router = useRouter()
const message = useMessage()

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)
const naturalNote = ref('')
const useLLM = ref(true)
const availDialog = ref(false)

const availabilityForm = ref<{
  employee_id: number | null
  target_date: string
  kind: AvailabilityKind
  shift_type: string | null
  note: string | null
}>({ employee_id: null, target_date: '', kind: 'unavailable', shift_type: null, note: null })

const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      employeeStore.fetchAll(),
      ruleStore.fetchPatterns(),
      shiftStore.fetch(year.value, month.value),
    ])
  } finally {
    loading.value = false
  }
})

const days = computed(() => {
  const list: Date[] = []
  const days = new Date(year.value, month.value, 0).getDate()
  for (let i = 1; i <= days; i++) list.push(new Date(year.value, month.value - 1, i))
  return list
})

const shift = computed(() => shiftStore.shift)

const employeeOptions = computed(() =>
  employeeStore.employees.map((e) => ({ label: e.name, value: e.id })),
)
const patternOptions = computed(() =>
  ruleStore.patterns.map((p) => ({ label: p.label, value: p.code })),
)

function assignmentsFor(employeeId: number, date: Date): string {
  if (!shift.value) return ''
  const iso = date.toISOString().slice(0, 10)
  return (
    shift.value.assignments
      .filter((a) => a.employee_id === employeeId && a.target_date === iso)
      .map((a) => a.shift_type)
      .join(', ') || ''
  )
}

function cellStyle(date: Date) {
  const w = date.getDay()
  if (w === 0) return { color: '#c92a2a' }
  if (w === 6) return { color: '#1971c2' }
  return {}
}

async function loadShift() {
  loading.value = true
  try {
    await shiftStore.fetch(year.value, month.value)
  } finally {
    loading.value = false
  }
}

async function generate() {
  loading.value = true
  try {
    const res = await shiftStore.generate({
      year: year.value,
      month: month.value,
      natural_language_note: naturalNote.value,
      use_llm: useLLM.value,
    })
    if (res.warnings.length) {
      message.warning(res.warnings.join(' / '))
    } else {
      message.success(`シフトを生成しました (${res.solver_seconds}s / ${res.solver_status})`)
    }
  } catch (e) {
    message.error(`生成に失敗: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

function openAvailability() {
  availDialog.value = true
}

async function submitAvailability() {
  if (!availabilityForm.value.employee_id || !availabilityForm.value.target_date) {
    message.warning('従業員と日付を選択してください')
    return
  }
  try {
    await employeeStore.createAvailability({
      employee_id: availabilityForm.value.employee_id,
      target_date: availabilityForm.value.target_date,
      kind: availabilityForm.value.kind,
      shift_type: availabilityForm.value.shift_type,
      note: availabilityForm.value.note,
    })
    message.success('希望を登録しました')
    availDialog.value = false
  } catch (e) {
    message.error(`登録失敗: ${(e as Error).message}`)
  }
}

function goPrint() {
  if (!shift.value) return
  router.push(`/print/${shift.value.id}`)
}
</script>

<template>
  <NSpace vertical>
    <NCard>
      <NSpace align="center" wrap>
        <span>対象月:</span>
        <NInputNumber v-model:value="year" :min="2024" :max="2100" style="width: 100px" />
        <NInputNumber v-model:value="month" :min="1" :max="12" style="width: 80px" />
        <NButton @click="loadShift">読み込み</NButton>
        <NButton type="primary" ghost @click="openAvailability">
          希望・不可能日を追加
        </NButton>
        <NButton
          v-if="shift"
          type="success"
          ghost
          @click="goPrint"
        >
          印刷プレビュー
        </NButton>
      </NSpace>
    </NCard>

    <NCard title="AIシフト生成">
      <p style="margin-top: 0; color: #6b7080">
        今月特有の事情（イベント、休暇、シフト希望など）を自然言語で入力できます。CP-SAT
        がハード制約（必要人数）・ソフト制約（希望）を満たす最適解を探索します。
      </p>
      <NInput
        v-model:value="naturalNote"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 8 }"
        placeholder="例: 8/15 は田中さんが夏季休暇で不可。8/20 は繁忙期のため朝を +1 人にしてください。"
      />
      <NSpace align="center" style="margin-top: 12px">
        <span>LLM を使用:</span>
        <NSwitch v-model:value="useLLM" />
        <NButton type="primary" :loading="shiftStore.generating" @click="generate">
          シフトを生成
        </NButton>
      </NSpace>
    </NCard>

    <NCard title="シフト表">
      <template #header-extra>
        <NTag v-if="shift" :type="shift.status === 'finalized' ? 'success' : 'default'">
          {{ shift.status }}
        </NTag>
      </template>
      <NSpin :show="loading || shiftStore.generating">
        <NAlert v-if="!shift" type="info">
          このシフトはまだ作成されていません。上の「シフトを生成」から作成できます。
        </NAlert>
        <div v-else class="table-scroll">
          <table class="shift-grid">
            <thead>
              <tr>
                <th class="fixed">従業員</th>
                <th v-for="d in days" :key="d.getTime()" :style="cellStyle(d)">
                  {{ d.getDate() }}
                  <br />
                  <small>{{ '日月火水木金土'[d.getDay()] }}</small>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="emp in employeeStore.employees" :key="emp.id">
                <td class="fixed">{{ emp.name }}</td>
                <td v-for="d in days" :key="d.getTime()" class="cell">
                  {{ assignmentsFor(emp.id, d) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </NSpin>
    </NCard>

    <NModal v-model:show="availDialog" preset="card" title="希望登録" style="width: 480px">
      <NSpace vertical>
        <NSelect
          v-model:value="availabilityForm.employee_id"
          placeholder="従業員を選択"
          :options="employeeOptions"
        />
        <NDatePicker
          v-model:formatted-value="availabilityForm.target_date"
          value-format="yyyy-MM-dd"
          type="date"
          style="width: 100%"
        />
        <NSelect
          v-model:value="availabilityForm.kind"
          :options="[
            { label: '勤務不可 (絶対)', value: 'unavailable' },
            { label: '入りたい (希望)', value: 'preferred' },
          ]"
        />
        <NSelect
          v-model:value="availabilityForm.shift_type"
          placeholder="シフト種別 (任意)"
          clearable
          :options="patternOptions"
        />
        <NInput
          v-model:value="availabilityForm.note"
          placeholder="メモ (任意)"
        />
        <NButton type="primary" block @click="submitAvailability">登録</NButton>
      </NSpace>
    </NModal>
  </NSpace>
</template>

<style scoped>
.table-scroll {
  overflow-x: auto;
  max-width: 100%;
}
.shift-grid {
  border-collapse: collapse;
  font-size: 12px;
  min-width: 100%;
}
.shift-grid th,
.shift-grid td {
  border: 1px solid #dde1e8;
  padding: 4px 6px;
  text-align: center;
  min-width: 40px;
  white-space: nowrap;
}
.shift-grid th {
  background: #f2f4f9;
  position: sticky;
  top: 0;
}
.shift-grid td.fixed,
.shift-grid th.fixed {
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 1;
  text-align: left;
  min-width: 120px;
}
.shift-grid th.fixed {
  background: #eaeef7;
  z-index: 2;
}
</style>
