<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  NButton,
  NModal,
  NRadio,
  NRadioGroup,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui'
import { useEmployeeStore } from '@/stores/employee'
import type { Availability, AvailabilityKind } from '@/types'

// employeeId を渡すと従業員を固定（従業員セレクトを隠す）。従業員管理のカレンダーで使う。
const props = defineProps<{ year: number; month: number; employeeId?: number }>()

const employeeStore = useEmployeeStore()
const message = useMessage()

const lockEmployee = computed(() => props.employeeId != null)
const selectedEmployeeId = ref<number | null>(props.employeeId ?? null)
const availabilities = ref<Availability[]>([])
const loading = ref(false)

// 曜日で一括登録（毎月流用の手間軽減）。曜日は JS の getDay()（0=日..6=土）。
const bulkWeekday = ref<number | null>(null)
const bulkKind = ref<AvailabilityKind | 'clear' | null>(null)
const bulkWeekdayOptions = ['日', '月', '火', '水', '木', '金', '土'].map((l, i) => ({
  label: `${l}曜日`,
  value: i,
}))
const bulkKindOptions = [
  { label: '休日', value: 'unavailable' },
  { label: '希望日(出勤ソフト)', value: 'preferred' },
  { label: '確定出勤', value: 'mandatory' },
  { label: '指定なし(解除)', value: 'clear' },
]

// 日付クリックで開くモーダルの状態
const showModal = ref(false)
const modalDate = ref<Date | null>(null)
const modalKind = ref<AvailabilityKind | null>(null)
const startHour = ref<number | null>(null) // 希望開始「時」(0-23)。1時間単位
const endHour = ref<number | null>(null) // 希望終了「時」(0-23)。開始以前なら翌日扱い

// 0:00〜23:00 の1時間刻み
const hourOptions = Array.from({ length: 24 }, (_, h) => ({ label: `${h}:00`, value: h }))

const modalTitle = computed(() =>
  modalDate.value
    ? `${modalDate.value.getFullYear()}/${modalDate.value.getMonth() + 1}/${modalDate.value.getDate()}`
    : '',
)

const employeeOptions = computed(() =>
  employeeStore.employees.map((e) => ({ label: e.name, value: e.id })),
)

const days = computed(() => {
  const list: Date[] = []
  const n = new Date(props.year, props.month, 0).getDate()
  for (let d = 1; d <= n; d++) list.push(new Date(props.year, props.month - 1, d))
  return list
})

const firstWeekday = computed(() => new Date(props.year, props.month - 1, 1).getDay())

async function refresh() {
  if (!selectedEmployeeId.value) {
    availabilities.value = []
    return
  }
  loading.value = true
  try {
    const rows = await employeeStore.listAvailabilities(selectedEmployeeId.value)
    availabilities.value = rows.filter((r) => {
      const d = new Date(r.target_date)
      return d.getFullYear() === props.year && d.getMonth() + 1 === props.month
    })
  } finally {
    loading.value = false
  }
}

watch(selectedEmployeeId, refresh)
watch(() => [props.year, props.month], refresh)
// 親が employeeId を差し替えたら追従する。
watch(
  () => props.employeeId,
  (id) => {
    if (id != null) selectedEmployeeId.value = id
  },
)

onMounted(async () => {
  if (!employeeStore.employees.length) await employeeStore.fetchAll()
  if (props.employeeId != null) {
    selectedEmployeeId.value = props.employeeId
  } else if (employeeStore.employees.length && !selectedEmployeeId.value) {
    selectedEmployeeId.value = employeeStore.employees[0].id
  }
})

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function itemsOn(d: Date): Availability[] {
  const iso = isoDate(d)
  return availabilities.value.filter((a) => a.target_date === iso)
}

async function add(kind: AvailabilityKind, d: Date, note: string | null = null) {
  if (!selectedEmployeeId.value) return
  try {
    const created = await employeeStore.createAvailability({
      employee_id: selectedEmployeeId.value,
      target_date: isoDate(d),
      kind,
      shift_type: null,
      note,
    })
    availabilities.value.push(created)
    message.success(`${isoDate(d)} を ${kindLabels[kind]} に追加しました`)
  } catch (e) {
    message.error(`登録失敗: ${(e as Error).message}`)
  }
}

// 日付セルのクリックでモーダルを開く（入力状態はリセット）
function openDay(d: Date) {
  modalDate.value = d
  modalKind.value = null
  startHour.value = null
  endHour.value = null
  showModal.value = true
}

// モーダルの「登録」。希望日のときだけ開始・終了「時」を note に保存する。
// 終了 <= 開始 は翌日扱い（例 20:00-01:00 = 翌1:00）。解釈はバックエンドに合わせる。
async function confirmAdd() {
  if (!modalDate.value || !modalKind.value) {
    message.warning('種別を選択してください')
    return
  }
  let note: string | null = null
  if (modalKind.value === 'preferred') {
    if (startHour.value == null || endHour.value == null) {
      message.warning('開始・終了時刻を選択してください')
      return
    }
    const pad = (h: number) => String(h).padStart(2, '0')
    note = `${pad(startHour.value)}:00-${pad(endHour.value)}:00`
  }
  await add(modalKind.value, modalDate.value, note)
  showModal.value = false
}

async function remove(id: number) {
  try {
    await employeeStore.deleteAvailability(id)
    availabilities.value = availabilities.value.filter((a) => a.id !== id)
  } catch (e) {
    message.error(`削除失敗: ${(e as Error).message}`)
  }
}

// 配置に関わる種別（曜日一括で置き換える対象）。有給は個別管理なので残す。
const SCHEDULING_KINDS = new Set<AvailabilityKind>(['unavailable', 'preferred', 'mandatory'])

// 選んだ曜日（当月ぶん）を、選んだ種別で一括登録する。既存の配置系は置き換える。
async function applyBulk() {
  if (!selectedEmployeeId.value) {
    message.warning('従業員を選択してください')
    return
  }
  if (bulkWeekday.value == null || !bulkKind.value) {
    message.warning('曜日と種別を選択してください')
    return
  }
  const targets = days.value.filter((d) => d.getDay() === bulkWeekday.value)
  try {
    for (const d of targets) {
      const iso = isoDate(d)
      // その日の配置系(休日/希望日/確定出勤)を一旦消してから、選んだ種別を付ける。
      const existing = availabilities.value.filter(
        (a) => a.target_date === iso && SCHEDULING_KINDS.has(a.kind),
      )
      for (const a of existing) {
        await employeeStore.deleteAvailability(a.id)
        availabilities.value = availabilities.value.filter((x) => x.id !== a.id)
      }
      if (bulkKind.value !== 'clear') {
        const created = await employeeStore.createAvailability({
          employee_id: selectedEmployeeId.value,
          target_date: iso,
          kind: bulkKind.value,
          shift_type: null,
          note: null,
        })
        availabilities.value.push(created)
      }
    }
    const label = bulkKindOptions.find((o) => o.value === bulkKind.value)?.label ?? ''
    message.success(`${bulkWeekdayOptions[bulkWeekday.value].label}を「${label}」で一括登録しました`)
  } catch (e) {
    message.error(`一括登録失敗: ${(e as Error).message}`)
  }
}

function dayClass(d: Date) {
  const items = itemsOn(d)
  if (items.some((i) => i.kind === 'paid_leave')) return 'day day--paid-leave'
  if (items.some((i) => i.kind === 'unavailable')) return 'day day--unavailable'
  if (items.some((i) => i.kind === 'mandatory')) return 'day day--mandatory'
  if (items.some((i) => i.kind === 'preferred')) return 'day day--preferred'
  return 'day'
}

const kindLabels: Record<AvailabilityKind, string> = {
  unavailable: '休日',
  preferred: '希望日',
  mandatory: '確定出勤',
  paid_leave: '有給',
}

function dayColor(d: Date) {
  const w = d.getDay()
  if (w === 0) return '#c92a2a'
  if (w === 6) return '#1971c2'
  return '#333'
}
</script>

<template>
  <div>
    <NSpace align="center" style="margin-bottom: 12px">
      <template v-if="!lockEmployee">
        <span>従業員:</span>
        <NSelect
          v-model:value="selectedEmployeeId"
          :options="employeeOptions"
          placeholder="従業員を選択"
          style="width: 240px"
        />
      </template>
      <NTag :bordered="false" round type="error">■ 休日</NTag>
      <NTag :bordered="false" round type="success">■ 希望日</NTag>
      <NTag :bordered="false" round type="info">■ 確定出勤</NTag>
      <NTag :bordered="false" round type="warning">■ 有給</NTag>
      <span class="hint">日付をクリックして登録</span>
    </NSpace>

    <NSpace align="center" style="margin-bottom: 12px">
      <span class="hint">曜日で一括:</span>
      <NSelect
        v-model:value="bulkWeekday"
        :options="bulkWeekdayOptions"
        placeholder="曜日"
        style="width: 110px"
      />
      <NSelect
        v-model:value="bulkKind"
        :options="bulkKindOptions"
        placeholder="種別"
        style="width: 170px"
      />
      <NButton size="small" :disabled="!selectedEmployeeId" @click="applyBulk">当月へ適用</NButton>
      <span class="hint">例: 木曜=確定出勤、他の曜日=休日。毎月この操作で流用できます。</span>
    </NSpace>

    <NSpin :show="loading">
      <div class="cal">
        <div v-for="w in ['日', '月', '火', '水', '木', '金', '土']" :key="w" class="head">
          {{ w }}
        </div>
        <div
          v-for="i in firstWeekday"
          :key="`pad-${i}`"
          class="pad"
        />
        <div
          v-for="d in days"
          :key="d.getTime()"
          :class="dayClass(d)"
          :style="{ color: dayColor(d) }"
          @click="openDay(d)"
        >
          <div class="num">{{ d.getDate() }}</div>
          <div class="marks">
            <span
              v-if="itemsOn(d).some((i) => i.kind === 'unavailable')"
              class="mark mark--unavailable"
            >休</span>
            <span
              v-if="itemsOn(d).some((i) => i.kind === 'preferred')"
              class="mark mark--preferred"
            >希</span>
            <span
              v-if="itemsOn(d).some((i) => i.kind === 'mandatory')"
              class="mark mark--mandatory"
            >確</span>
            <span
              v-if="itemsOn(d).some((i) => i.kind === 'paid_leave')"
              class="mark mark--paid-leave"
            >有</span>
          </div>
        </div>
      </div>
    </NSpin>

    <NModal v-model:show="showModal" preset="card" :title="modalTitle" style="width: 420px">
      <NSpace vertical>
        <!-- 既に登録済みの内容（削除もここから） -->
        <div v-if="modalDate">
          <div v-for="a in itemsOn(modalDate)" :key="a.id" class="item-row">
            <NTag
              :type="
                a.kind === 'unavailable'
                  ? 'error'
                  : a.kind === 'paid_leave'
                    ? 'warning'
                    : a.kind === 'mandatory'
                      ? 'info'
                      : 'success'
              "
              size="small"
            >
              {{ kindLabels[a.kind] }}<template v-if="a.note"> ({{ a.note }})</template>
            </NTag>
            <NButton size="tiny" quaternary type="error" @click="remove(a.id)">削除</NButton>
          </div>
        </div>

        <!-- 種別を選択。希望日のときだけ時刻欄が出る -->
        <NRadioGroup v-model:value="modalKind">
          <NSpace vertical>
            <NRadio value="unavailable">休日として登録</NRadio>
            <NRadio value="preferred">希望日(出勤ソフト)として登録</NRadio>
            <NRadio value="mandatory">確定出勤として登録</NRadio>
            <NRadio value="paid_leave">有給として登録</NRadio>
          </NSpace>
        </NRadioGroup>

        <div v-if="modalKind === 'preferred'">
          <NSpace align="center">
            <span>開始</span>
            <NSelect
              v-model:value="startHour"
              :options="hourOptions"
              placeholder="開始時"
              style="width: 110px"
            />
            <span>終了</span>
            <NSelect
              v-model:value="endHour"
              :options="hourOptions"
              placeholder="終了時"
              style="width: 110px"
            />
          </NSpace>
          <p class="hint" style="margin: 6px 0 0">
            1時間単位で選択。終了が開始以前なら翌日扱い（例: 20:00→翌1:00）。
          </p>
        </div>

        <NButton type="primary" block :disabled="!modalKind" @click="confirmAdd">登録</NButton>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
.cal {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.head {
  text-align: center;
  font-weight: 600;
  padding: 6px 0;
  color: #4a5170;
  background: #f2f4f9;
  border-radius: 6px;
  font-size: 12px;
}
.pad {
  min-height: 60px;
}
.day {
  min-height: 60px;
  padding: 4px 6px;
  border: 1px solid #dde1e8;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  background: #fff;
  transition: box-shadow 0.15s;
}
.day:hover {
  box-shadow: 0 0 0 2px rgba(80, 160, 255, 0.25);
}
.day--unavailable {
  background: #fdecec;
  border-color: #f5c2c2;
}
.day--preferred {
  background: #e8f7ec;
  border-color: #bde0c6;
}
.day--mandatory {
  background: #e6f0ff;
  border-color: #b6d0f5;
}
.day--paid-leave {
  background: #fff4e0;
  border-color: #f0d199;
}
.num {
  font-weight: 600;
  font-size: 13px;
}
.marks {
  margin-top: auto;
  display: flex;
  gap: 4px;
}
.mark {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  color: #fff;
}
.mark--unavailable {
  background: #d33f3f;
}
.mark--preferred {
  background: #2f9e44;
}
.mark--mandatory {
  background: #1971c2;
}
.mark--paid-leave {
  background: #e8933a;
}
.hint {
  color: #8892a6;
  font-size: 12px;
}
.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
</style>
