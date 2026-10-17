// シフト表のセル表示ロジック（割当→ラベル・時間帯バンド・有給表示のマップ化）。
import { computed, type ComputedRef, type Ref } from 'vue'
import type { Availability, Employee, Shift, ShiftAssignment, ShiftPattern } from '@/types'
import { isoDate } from '@/utils/date'
import { weekdayColor } from '@/utils/weekday'

type Band = 'morning' | 'evening' | 'night' | null

export interface AssignmentCell {
  label: string
  paidLeave: boolean
  band: Band // 時間帯の機能色（先頭割当の区分）
}

const EMPTY_CELL: AssignmentCell = { label: '', paidLeave: false, band: null }

/** "HH:MM:SS" → "H"(ちょうど)/"H:MM"(分あり)。表示だけ簡略化する。 */
function hourLabel(t: string): string {
  const [hh, mm] = t.split(':')
  const hour = parseInt(hh, 10)
  return mm === '00' ? `${hour}` : `${hour}:${mm}`
}

/** 割当を実時間帯で表示する（例 20:00-00:00 → "20 - 0"）。深夜跨ぎもそのまま。 */
function timeRange(a: ShiftAssignment): string {
  return `${hourLabel(a.start_time)} - ${hourLabel(a.end_time)}`
}

/**
 * シフト表の各セル表示（ラベル・有給・時間帯バンド）を計算する composable。
 * `cellAt(従業員ID, 日)` と、曜日色の `cellStyle(日)` を返す。
 */
export function useShiftGrid(opts: {
  shift: ComputedRef<Shift | null>
  days: ComputedRef<Date[]>
  draft: Ref<ShiftAssignment[]>
  employees: () => Employee[]
  patterns: () => ShiftPattern[]
  paidLeaveFor: (employeeId: number, iso: string) => Availability | undefined
}) {
  // 割当の shift_type はパターンの code。メイン照合は区分(category)でも一致とみなす。
  function categoryOfCode(shiftCode: string | null): string | null {
    if (!shiftCode) return null
    return opts.patterns().find((p) => p.code === shiftCode)?.category ?? null
  }

  function assignmentsFor(employeeId: number, date: Date): AssignmentCell {
    if (!opts.shift.value) return { ...EMPTY_CELL }
    const iso = isoDate(date)

    // 有給日はシフトより優先して「有給」と表示する
    if (opts.paidLeaveFor(employeeId, iso)) {
      return { label: '有給', paidLeave: true, band: null }
    }

    const matches = opts.draft.value.filter(
      (a) => a.employee_id === employeeId && a.target_date === iso,
    )
    if (matches.length === 0) return { ...EMPTY_CELL }

    const cat = categoryOfCode(matches[0].shift_type)
    const band: Band = cat === 'morning' || cat === 'evening' || cat === 'night' ? cat : null
    return {
      label: matches.map((a) => timeRange(a)).join(', '),
      paidLeave: false,
      band,
    }
  }

  // 各セルの表示値を1描画1回だけ計算してマップ化する。
  const cellMap = computed(() => {
    const m = new Map<string, AssignmentCell>()
    for (const emp of opts.employees()) {
      for (const d of opts.days.value) {
        m.set(`${emp.id}|${isoDate(d)}`, assignmentsFor(emp.id, d))
      }
    }
    return m
  })

  function cellAt(employeeId: number, date: Date): AssignmentCell {
    return cellMap.value.get(`${employeeId}|${isoDate(date)}`) ?? EMPTY_CELL
  }

  // 土日のみ色付け（平日は色指定なし＝既定テキスト色を継承）。
  function cellStyle(date: Date) {
    const c = weekdayColor(date)
    return c ? { color: c } : {}
  }

  return { cellAt, cellStyle }
}
