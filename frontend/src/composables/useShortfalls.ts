// シフト表の「人数不足(Shortfall)」算出ロジック。時間カバレッジ方式(ADR-0005)。
import { computed, type ComputedRef, type Ref } from 'vue'
import type { HourlyStaffingRule, Shift, ShiftAssignment } from '@/types'
import { isoDate } from '@/utils/date'
import { dayCategory } from '@/utils/weekday'

export interface Shortfall {
  day: number
  hour: number
  have: number
  need: number
}

/** 割当がカバーする「拡張時」(深夜跨ぎは 24=0:00, 25=1:00)の配列を返す。 */
function assignmentHours(a: ShiftAssignment): number[] {
  const s = parseInt(a.start_time.slice(0, 2), 10)
  let e = parseInt(a.end_time.slice(0, 2), 10)
  if (e <= s) e += 24 // 深夜跨ぎ
  const hours: number[] = []
  for (let h = s; h < e; h++) hours.push(h)
  return hours
}

/**
 * 各日・各時間で配置人数が必要人数に満たない箇所(Shortfall)を算出する computed を返す。
 * 入力はリアクティブな参照/ゲッターで受け取り、変化に追従する（土日は休日扱い。祝日は未考慮）。
 */
export function useShortfalls(opts: {
  shift: ComputedRef<Shift | null>
  days: ComputedRef<Date[]>
  draft: Ref<ShiftAssignment[]>
  hourlyStaffing: () => HourlyStaffingRule[]
}): ComputedRef<Shortfall[]> {
  return computed<Shortfall[]>(() => {
    const out: Shortfall[] = []
    if (!opts.shift.value) return out
    for (const d of opts.days.value) {
      const iso = isoDate(d)
      const dayCat = dayCategory(d)
      // その日の各拡張時のカバレッジを集計
      const cover: Record<number, number> = {}
      for (const a of opts.draft.value) {
        if (a.target_date !== iso) continue
        for (const h of assignmentHours(a)) cover[h] = (cover[h] ?? 0) + 1
      }
      for (const r of opts.hourlyStaffing()) {
        if (r.day_category !== dayCat || r.required <= 0) continue
        const have = cover[r.hour] ?? 0
        if (have < r.required) {
          out.push({ day: d.getDate(), hour: r.hour, have, need: r.required })
        }
      }
    }
    return out
  })
}
