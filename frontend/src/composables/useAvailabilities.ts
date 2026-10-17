// 従業員の希望(availability)のロード・追加・削除と「同じ曜日へ一括適用」ロジック。
import { ref, type ComputedRef, type Ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useEmployeeStore } from '@/stores/employee'
import type { Availability, AvailabilityKind } from '@/types'
import { isoDate } from '@/utils/date'
import { KIND_LABELS } from '@/constants/availability'

// 配置に関わる種別（曜日一括で置き換える対象）。有給は個別管理なので残す。
const SCHEDULING_KINDS = new Set<AvailabilityKind>(['unavailable', 'preferred', 'mandatory'])
const WEEKDAY_NAMES = ['日', '月', '火', '水', '木', '金', '土']

interface PendingApply {
  weekday: number
  kind: AvailabilityKind
  note: string | null
  baseIso: string
}

/**
 * 希望データのロード/追加/削除と、登録直後の「今後の同じ曜日にも適用」を提供する composable。
 * 対象年月・選択従業員・当月の日付配列は呼び出し側の参照を共有する。
 */
export function useAvailabilities(opts: {
  year: () => number
  month: () => number
  selectedEmployeeId: Ref<number | null>
  days: ComputedRef<Date[]>
}) {
  const employeeStore = useEmployeeStore()
  const message = useMessage()

  const availabilities = ref<Availability[]>([])
  const loading = ref(false)
  const showApplyPrompt = ref(false)
  const pendingApply = ref<PendingApply | null>(null)

  /** 選択従業員・対象月の希望を読み込む（従業員未選択なら空）。 */
  async function refresh() {
    if (!opts.selectedEmployeeId.value) {
      availabilities.value = []
      return
    }
    loading.value = true
    try {
      const rows = await employeeStore.listAvailabilities(opts.selectedEmployeeId.value)
      availabilities.value = rows.filter((r) => {
        const d = new Date(r.target_date)
        return d.getFullYear() === opts.year() && d.getMonth() + 1 === opts.month()
      })
    } finally {
      loading.value = false
    }
  }

  /** 希望を1件追加し、成功したら作成行を返す（失敗時は null）。 */
  async function add(
    kind: AvailabilityKind,
    d: Date,
    note: string | null = null,
  ): Promise<Availability | null> {
    if (!opts.selectedEmployeeId.value) return null
    try {
      const created = await employeeStore.createAvailability({
        employee_id: opts.selectedEmployeeId.value,
        target_date: isoDate(d),
        kind,
        shift_type: null,
        note,
      })
      availabilities.value.push(created)
      message.success(`${isoDate(d)} を ${KIND_LABELS[kind]} に追加しました`)
      return created
    } catch (e) {
      message.error(`登録失敗: ${(e as Error).message}`)
      return null
    }
  }

  /** 希望を1件削除する。 */
  async function remove(id: number) {
    try {
      await employeeStore.deleteAvailability(id)
      availabilities.value = availabilities.value.filter((a) => a.id !== id)
    } catch (e) {
      message.error(`削除失敗: ${(e as Error).message}`)
    }
  }

  /**
   * 登録直後に「今後の同じ曜日にも適用するか」を尋ねる（基準日より後の同曜日が当月に無ければ聞かない）。
   */
  function promptSameWeekday(baseDate: Date, kind: AvailabilityKind, note: string | null) {
    const weekday = baseDate.getDay()
    const baseIso = isoDate(baseDate)
    const upcoming = opts.days.value.filter((d) => d.getDay() === weekday && isoDate(d) > baseIso)
    if (!upcoming.length) return
    pendingApply.value = { weekday, kind, note, baseIso }
    showApplyPrompt.value = true
  }

  /** 「はい」。当月の同じ曜日のうち基準日より後の日に同じ内容を適用する。 */
  async function confirmApplyWeekday() {
    const p = pendingApply.value
    showApplyPrompt.value = false
    if (!p || !opts.selectedEmployeeId.value) return
    const targets = opts.days.value.filter((d) => d.getDay() === p.weekday && isoDate(d) > p.baseIso)
    try {
      for (const d of targets) {
        const iso = isoDate(d)
        if (SCHEDULING_KINDS.has(p.kind)) {
          // 配置系(休日/希望日/確定出勤)は1日1つ。既存を置き換えてから登録する。
          const existing = availabilities.value.filter(
            (a) => a.target_date === iso && SCHEDULING_KINDS.has(a.kind),
          )
          for (const a of existing) {
            await employeeStore.deleteAvailability(a.id)
            availabilities.value = availabilities.value.filter((x) => x.id !== a.id)
          }
        } else if (availabilities.value.some((a) => a.target_date === iso && a.kind === p.kind)) {
          continue // 有給など: 既に同じ種別があればスキップ
        }
        const created = await employeeStore.createAvailability({
          employee_id: opts.selectedEmployeeId.value,
          target_date: iso,
          kind: p.kind,
          shift_type: null,
          note: p.note,
        })
        availabilities.value.push(created)
      }
      message.success(
        `今後の${WEEKDAY_NAMES[p.weekday]}曜日にも「${KIND_LABELS[p.kind]}」を登録しました`,
      )
    } catch (e) {
      message.error(`一括登録失敗: ${(e as Error).message}`)
    } finally {
      pendingApply.value = null
    }
  }

  return {
    availabilities,
    loading,
    refresh,
    add,
    remove,
    showApplyPrompt,
    pendingApply,
    weekdayNames: WEEKDAY_NAMES,
    promptSameWeekday,
    confirmApplyWeekday,
  }
}
