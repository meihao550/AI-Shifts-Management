<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NSelect, NSpace, NSpin, NTag, useMessage } from 'naive-ui'
import { api } from '@/api/client'
import { useEmployeeStore } from '@/stores/employee'
import type { Availability, AvailabilityKind, Holiday } from '@/types'

const props = defineProps<{ year: number; month: number }>()

const employeeStore = useEmployeeStore()
const message = useMessage()

const selectedEmployeeId = ref<number | null>(null)
const availabilities = ref<Availability[]>([])
const loading = ref(false)
// ISO日付 -> 祝日名
const holidays = ref<Record<string, string>>({})

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

async function fetchHolidays() {
  try {
    const { data } = await api.get<Holiday[]>('/holidays', {
      params: { year: props.year, month: props.month },
    })
    holidays.value = Object.fromEntries(data.map((h) => [h.date, h.name]))
  } catch {
    holidays.value = {}
  }
}

watch(selectedEmployeeId, refresh)
watch(() => [props.year, props.month], () => {
  refresh()
  fetchHolidays()
})

onMounted(async () => {
  fetchHolidays()
  if (!employeeStore.employees.length) await employeeStore.fetchAll()
  if (employeeStore.employees.length && !selectedEmployeeId.value) {
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

function holidayName(d: Date): string | undefined {
  return holidays.value[isoDate(d)]
}

async function add(kind: AvailabilityKind, d: Date) {
  if (!selectedEmployeeId.value) return
  const created = await employeeStore.createAvailability({
    employee_id: selectedEmployeeId.value,
    target_date: isoDate(d),
    kind,
    shift_type: null,
    note: null,
  })
  availabilities.value.push(created)
}

async function remove(id: number) {
  await employeeStore.deleteAvailability(id)
  availabilities.value = availabilities.value.filter((a) => a.id !== id)
}

// クリックで状態を循環させる: なし → 休日 → 希望日 → なし
// 1回=休日 / 2回=希望日 / 3回=元に戻る。
// 素早い連打（ダブルクリック等）でも順序が崩れないよう、日付ごとに
// クリックを直列処理する（前のAPI呼び出し完了後に次を実行）。
const chains = new Map<string, Promise<void>>()

function cycle(d: Date) {
  if (!selectedEmployeeId.value) return
  const iso = isoDate(d)
  const prev = chains.get(iso) ?? Promise.resolve()
  const next = prev.then(() => step(d)).catch((e) => {
    message.error(`更新失敗: ${(e as Error).message}`)
  })
  chains.set(iso, next)
}

async function step(d: Date) {
  const items = itemsOn(d)
  const unavailable = items.find((i) => i.kind === 'unavailable')
  const preferred = items.find((i) => i.kind === 'preferred')

  if (!unavailable && !preferred) {
    // なし → 休日
    await add('unavailable', d)
  } else if (unavailable && !preferred) {
    // 休日 → 希望日
    await remove(unavailable.id)
    await add('preferred', d)
  } else if (preferred && !unavailable) {
    // 希望日 → なし
    await remove(preferred.id)
  } else {
    // 両方存在する場合（旧データ）はすべて消して「なし」に戻す
    for (const it of items) await remove(it.id)
  }
}

function dayClass(d: Date) {
  const items = itemsOn(d)
  if (items.some((i) => i.kind === 'unavailable')) return 'day day--unavailable'
  if (items.some((i) => i.kind === 'preferred')) return 'day day--preferred'
  return 'day'
}

function dayColor(d: Date) {
  const w = d.getDay()
  if (w === 0 || holidayName(d)) return '#c92a2a'
  if (w === 6) return '#1971c2'
  return '#333'
}
</script>

<template>
  <div>
    <NSpace align="center" style="margin-bottom: 12px">
      <span>従業員:</span>
      <NSelect
        v-model:value="selectedEmployeeId"
        :options="employeeOptions"
        placeholder="従業員を選択"
        style="width: 240px"
      />
      <NTag :bordered="false" round type="error">■ 休日 (勤務不可)</NTag>
      <NTag :bordered="false" round type="success">■ 希望日</NTag>
      <span class="hint">クリックで切替: 1回=休日 / 2回=希望日 / 3回=解除</span>
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
          :title="holidayName(d)"
          @click="cycle(d)"
        >
          <div class="num">{{ d.getDate() }}</div>
          <div v-if="holidayName(d)" class="holiday">{{ holidayName(d) }}</div>
          <div class="marks">
            <span
              v-if="itemsOn(d).some((i) => i.kind === 'unavailable')"
              class="mark mark--unavailable"
            >休</span>
            <span
              v-if="itemsOn(d).some((i) => i.kind === 'preferred')"
              class="mark mark--preferred"
            >希</span>
          </div>
        </div>
      </div>
    </NSpin>
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
  user-select: none;
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
.num {
  font-weight: 600;
  font-size: 13px;
}
.holiday {
  font-size: 9px;
  line-height: 1.1;
  color: #c92a2a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
