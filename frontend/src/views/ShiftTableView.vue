<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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
import type { Availability, AvailabilityKind, ShiftAssignment } from '@/types'
import AvailabilityCalendar from '@/components/AvailabilityCalendar.vue'

// セル編集で「有給」を表すための特別な選択値
const PAID_LEAVE_VALUE = '__paid_leave__'

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

// 手動編集用のドラフト（保存されるまではこちらを表示・編集する）
const draft = ref<ShiftAssignment[]>([])
const dirty = ref(false)

// 当月の有給（従業員×日付）。カレンダー/セルから登録され、即時に永続化する。
const paidLeaveList = ref<Availability[]>([])

async function loadPaidLeave() {
  paidLeaveList.value = await employeeStore.listAllAvailabilities({
    year: year.value,
    month: month.value,
    kind: 'paid_leave',
  })
}

function paidLeaveFor(employeeId: number, iso: string): Availability | undefined {
  return paidLeaveList.value.find(
    (a) => a.employee_id === employeeId && a.target_date === iso,
  )
}

// store のシフトが変わったらドラフトを作り直す
watch(
  () => shiftStore.shift,
  (s) => {
    draft.value = s ? s.assignments.map((a) => ({ ...a })) : []
    dirty.value = false
  },
  { immediate: true },
)

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      employeeStore.fetchAll(),
      ruleStore.fetchPatterns(),
      ruleStore.fetchHourlyStaffing(),
      shiftStore.fetch(year.value, month.value),
      loadPaidLeave(),
    ])
  } finally {
    loading.value = false
  }
})

const days = computed(() => {
  const list: Date[] = []
  const total = new Date(year.value, month.value, 0).getDate()
  for (let i = 1; i <= total; i++) list.push(new Date(year.value, month.value - 1, i))
  return list
})

const shift = computed(() => shiftStore.shift)

const employeeOptions = computed(() =>
  employeeStore.employees.map((e) => ({ label: e.name, value: e.id })),
)
const patternOptions = computed(() =>
  ruleStore.patterns.map((p) => ({ label: p.label, value: p.code })),
)

const shiftTypeLabels: Record<string, string> = {
  morning: '朝',
  evening: '夜',
  night: '深夜',
}

function shiftTypeLabel(code: string): string {
  return shiftTypeLabels[code] ?? code
}

// "HH:MM:SS" → "H"（ちょうどの時刻）/ "H:MM"（分あり）。内部は HH:MM のまま保持し表示のみ簡略化。
function hourLabel(t: string): string {
  const [hh, mm] = t.split(':')
  const hour = parseInt(hh, 10)
  return mm === '00' ? `${hour}` : `${hour}:${mm}`
}

// 割当を実時間帯で表示する（例 20:00-00:00 → "20 - 0"）。深夜跨ぎもそのまま表示。
// 休憩・実働はここには出さない（人件費画面で確認する）。
function timeRange(a: ShiftAssignment): string {
  return `${hourLabel(a.start_time)} - ${hourLabel(a.end_time)}`
}

function isoLocalDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

interface AssignmentCell {
  label: string
  mainMismatch: boolean
  paidLeave: boolean
}

// 割当の shift_type にはパターンの code が入る。メイン照合は区分(category)でも
// 一致とみなす（scheduler.py と同じく code / category の二本立て）。
function categoryOfCode(shiftCode: string | null): string | null {
  if (!shiftCode) return null
  return ruleStore.patterns.find((p) => p.code === shiftCode)?.category ?? null
}

function assignmentsFor(employeeId: number, date: Date): AssignmentCell {
  if (!shift.value) return { label: '', mainMismatch: false, paidLeave: false }
  const iso = isoLocalDate(date)

  // 有給日はシフトより優先して「有給」と表示する
  if (paidLeaveFor(employeeId, iso)) {
    return { label: '有給', mainMismatch: false, paidLeave: true }
  }

  const emp = employeeStore.employees.find((e) => e.id === employeeId)
  const mainType = emp?.main_shift_type ?? null

  const matches = draft.value.filter(
    (a) => a.employee_id === employeeId && a.target_date === iso,
  )
  if (matches.length === 0) return { label: '', mainMismatch: false, paidLeave: false }

  // code そのもの、または区分(category)が main_shift_type と一致すればメイン扱い。
  const mainMismatch =
    !!mainType &&
    matches.some(
      (a) => a.shift_type !== mainType && categoryOfCode(a.shift_type) !== mainType,
    )
  return {
    label: matches.map((a) => timeRange(a)).join(', '),
    mainMismatch,
    paidLeave: false,
  }
}

function cellStyle(date: Date) {
  const w = date.getDay()
  if (w === 0) return { color: '#c92a2a' }
  if (w === 6) return { color: '#1971c2' }
  return {}
}

// ---- 人数不足リマインド（時間カバレッジ方式） ------------------------------
// 割当がカバーする「拡張時」を返す（深夜跨ぎは 24=0:00, 25=1:00）。
function assignmentHours(a: ShiftAssignment): number[] {
  const s = parseInt(a.start_time.slice(0, 2), 10)
  let e = parseInt(a.end_time.slice(0, 2), 10)
  if (e <= s) e += 24 // 深夜跨ぎ
  const hours: number[] = []
  for (let h = s; h < e; h++) hours.push(h)
  return hours
}

interface Shortfall {
  day: number
  hour: number
  have: number
  need: number
}

// 各日・各時間の配置人数が必要人数に足りているか（土日は weekend 扱い。祝日は未考慮）
const shortfalls = computed<Shortfall[]>(() => {
  const out: Shortfall[] = []
  if (!shift.value) return out
  for (const d of days.value) {
    const iso = isoLocalDate(d)
    const dayCategory = d.getDay() === 0 || d.getDay() === 6 ? 'weekend_or_holiday' : 'weekday'
    // その日の各拡張時のカバレッジを集計
    const cover: Record<number, number> = {}
    for (const a of draft.value) {
      if (a.target_date !== iso) continue
      for (const h of assignmentHours(a)) cover[h] = (cover[h] ?? 0) + 1
    }
    for (const r of ruleStore.hourlyStaffing) {
      if (r.day_category !== dayCategory || r.required <= 0) continue
      const have = cover[r.hour] ?? 0
      if (have < r.required) out.push({ day: d.getDate(), hour: r.hour, have, need: r.required })
    }
  }
  return out
})

// ---- セル編集 --------------------------------------------------------------
const editCell = ref<{ employee_id: number; date: string; empName: string } | null>(null)
const editShiftType = ref<string | null>(null)

// セル編集の選択肢: シフトパターン + 「有給」
const cellEditOptions = computed(() => [
  { label: '有給', value: PAID_LEAVE_VALUE },
  ...ruleStore.patterns.map((p) => ({ label: p.label, value: p.code })),
])

function openCellEdit(employeeId: number, date: Date) {
  if (!shift.value) return
  const iso = isoLocalDate(date)
  if (paidLeaveFor(employeeId, iso)) {
    editShiftType.value = PAID_LEAVE_VALUE
  } else {
    const existing = draft.value.find((a) => a.employee_id === employeeId && a.target_date === iso)
    editShiftType.value = existing?.shift_type ?? null
  }
  editCell.value = {
    employee_id: employeeId,
    date: iso,
    empName: employeeStore.employees.find((e) => e.id === employeeId)?.name ?? '',
  }
}

async function saveCellEdit() {
  if (!editCell.value) return
  const { employee_id, date } = editCell.value
  const code = editShiftType.value
  const existingLeave = paidLeaveFor(employee_id, date)

  try {
    if (code === PAID_LEAVE_VALUE) {
      // 有給に設定: その日のシフト割当は外し、有給を登録（即時保存）
      draft.value = draft.value.filter(
        (a) => !(a.employee_id === employee_id && a.target_date === date),
      )
      if (!existingLeave) {
        const created = await employeeStore.createAvailability({
          employee_id,
          target_date: date,
          kind: 'paid_leave',
          shift_type: null,
          note: null,
        })
        paidLeaveList.value.push(created)
      }
      dirty.value = true
    } else {
      // 有給以外: 既存の有給があれば解除（即時保存）
      if (existingLeave) {
        await employeeStore.deleteAvailability(existingLeave.id)
        paidLeaveList.value = paidLeaveList.value.filter((a) => a.id !== existingLeave.id)
      }
      // その従業員・その日の既存割当を一旦削除してから、選択があれば追加
      draft.value = draft.value.filter(
        (a) => !(a.employee_id === employee_id && a.target_date === date),
      )
      if (code) {
        const p = ruleStore.patterns.find((pp) => pp.code === code)
        if (p) {
          draft.value.push({
            id: 0,
            shift_id: shift.value?.id ?? 0,
            employee_id,
            target_date: date,
            shift_type: p.code,
            start_time: p.start_time,
            end_time: p.end_time,
            crosses_midnight: p.end_time <= p.start_time,
            rest_minutes: p.rest_minutes, // パターンの休憩をスナップショット
          })
        }
      }
      dirty.value = true
    }
    editCell.value = null
  } catch (e) {
    message.error(`更新失敗: ${(e as Error).message}`)
  }
}

async function saveShift() {
  if (!shift.value) return
  try {
    const payload = draft.value.map((a) => ({
      employee_id: a.employee_id,
      target_date: a.target_date,
      shift_type: a.shift_type,
      start_time: a.start_time,
      end_time: a.end_time,
      crosses_midnight: a.crosses_midnight,
      // 送っても backend がパターンから解決して上書きする（型を満たすため付与）
      rest_minutes: a.rest_minutes,
    }))
    await shiftStore.saveAssignments(shift.value.id, payload)
    dirty.value = false
    if (shortfalls.value.length) {
      message.warning(`更新しました（人数不足が ${shortfalls.value.length} 件あります）`)
    } else {
      message.success('シフトを更新しました')
    }
  } catch (e) {
    message.error(`更新失敗: ${(e as Error).message}`)
  }
}

async function loadShift() {
  loading.value = true
  try {
    await Promise.all([shiftStore.fetch(year.value, month.value), loadPaidLeave()])
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
    await loadPaidLeave()
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
        <NButton v-if="shift" type="success" ghost @click="goPrint"> 印刷プレビュー </NButton>
      </NSpace>
    </NCard>

    <NCard title="休日・希望日カレンダー">
      <AvailabilityCalendar :year="year" :month="month" />
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

    <NCard title="シフト表（セルをクリックで編集）">
      <template #header-extra>
        <NSpace align="center">
          <NTag v-if="shift" :type="shift.status === 'finalized' ? 'success' : 'default'">
            {{
              shift.status === 'finalized'
                ? '確定済み'
                : shift.status === 'published'
                  ? '公開中'
                  : 'ドラフト'
            }}
          </NTag>
          <NTag v-if="dirty" type="warning" size="small">未保存の変更あり</NTag>
          <NButton v-if="shift" type="primary" size="small" :disabled="!dirty" @click="saveShift">
            更新
          </NButton>
        </NSpace>
      </template>
      <NSpin :show="loading || shiftStore.generating">
        <NAlert v-if="!shift" type="info">
          このシフトはまだ作成されていません。上の「シフトを生成」から作成できます。
        </NAlert>
        <template v-else>
          <NAlert
            v-if="shortfalls.length"
            type="warning"
            title="人数が規定に足りていません"
            style="margin-bottom: 12px"
          >
            <div class="shortfall-list">
              <span v-for="(s, i) in shortfalls" :key="i" class="shortfall-item">
                {{ s.day }}日 {{ s.hour }}:00台 {{ s.have }}/{{ s.need }}人
              </span>
            </div>
            <p class="shortfall-note">
              ※土日は休日扱いで判定しています（祝日は未考慮）。編集後は「更新」で保存してください。
            </p>
          </NAlert>
          <div class="table-scroll">
            <table class="shift-grid">
              <thead>
                <tr>
                  <th class="fixed">日付</th>
                  <th v-for="emp in employeeStore.employees" :key="emp.id">
                    {{ emp.name }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in days" :key="d.getTime()">
                  <td class="fixed" :style="cellStyle(d)">
                    {{ d.getDate() }}
                    <small>（{{ '日月火水木金土'[d.getDay()] }}）</small>
                  </td>
                  <template v-for="emp in employeeStore.employees" :key="emp.id">
                    <td
                      class="cell cell-editable"
                      :class="{
                        'cell-main-mismatch': assignmentsFor(emp.id, d).mainMismatch,
                        'cell-paid-leave': assignmentsFor(emp.id, d).paidLeave,
                      }"
                      :title="
                        assignmentsFor(emp.id, d).mainMismatch
                          ? `${emp.name} のメインシフト (${
                              shiftTypeLabel(emp.main_shift_type ?? '')
                            }) 以外で入っています`
                          : 'クリックで編集'
                      "
                      @click="openCellEdit(emp.id, d)"
                    >
                      {{ assignmentsFor(emp.id, d).label }}
                    </td>
                  </template>
                </tr>
              </tbody>
            </table>
            <p class="legend">
              <span class="legend-swatch legend-swatch--mismatch"></span>
              赤: メインシフト以外で入っている割当
            </p>
          </div>
        </template>
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
        <NInput v-model:value="availabilityForm.note" placeholder="メモ (任意)" />
        <NButton type="primary" block @click="submitAvailability">登録</NButton>
      </NSpace>
    </NModal>

    <NModal
      :show="!!editCell"
      preset="card"
      title="シフト編集"
      style="width: 360px"
      @update:show="(v: boolean) => { if (!v) editCell = null }"
    >
      <NSpace v-if="editCell" vertical>
        <p style="margin: 0">{{ editCell.empName }} / {{ editCell.date }}</p>
        <NSelect
          v-model:value="editShiftType"
          :options="cellEditOptions"
          clearable
          placeholder="シフトなし（休み）"
        />
        <NSpace justify="end">
          <NButton @click="editCell = null">キャンセル</NButton>
          <NButton type="primary" @click="saveCellEdit">反映</NButton>
        </NSpace>
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
  min-width: 68px;
  white-space: nowrap;
}
.shift-grid th.fixed {
  background: #eaeef7;
  z-index: 2;
}
.shift-grid td.cell-editable {
  cursor: pointer;
}
.shift-grid td.cell-editable:hover {
  background: #eef4ff;
}
.shift-grid td.cell-main-mismatch {
  background: #ffe3e3;
  color: #c92a2a;
  font-weight: 700;
}
.shift-grid td.cell-paid-leave {
  background: #fff4e0;
  color: #b06a12;
  font-weight: 700;
}
.shortfall-list {
  max-height: 120px;
  overflow: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  font-size: 12px;
}
.shortfall-item {
  white-space: nowrap;
}
.shortfall-note {
  margin: 8px 0 0;
  font-size: 11px;
  color: #8892a6;
}
.legend {
  margin: 12px 0 0;
  font-size: 12px;
  color: #6b7080;
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid #dde1e8;
}
.legend-swatch--mismatch {
  background: #ffe3e3;
}
</style>
