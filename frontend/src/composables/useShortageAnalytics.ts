// 人手不足の集計・予測 API を取得する composable（管理者の分析画面で使う）。
import { ref } from 'vue'
import { api } from '@/api/client'

/** 曜日×拡張時の1スロットの人手不足実績統計（backend ShortageSlotStat に対応）。 */
export interface ShortageSlotStat {
  weekday: number
  hour: number
  samples: number
  shortage_rate: number
  avg_shortage: number
  avg_required: number
  avg_filled: number
}

/** 集計レスポンス（backend ShortageAnalytics に対応）。 */
export interface ShortageAnalytics {
  months: number
  total_slots: number
  slots: ShortageSlotStat[]
  ranking: ShortageSlotStat[]
}

/** 予測の1スロット（backend ForecastSlot に対応）。 */
export interface ForecastSlot {
  target_date: string
  weekday: number
  hour: number
  predicted_shortage: number
  required: number
}

/** 予測レスポンス（backend ShortageForecast に対応）。 */
export interface ShortageForecast {
  year: number
  month: number
  method: 'model' | 'baseline' | 'none'
  data_months: number
  caveat: string | null
  slots: ForecastSlot[]
}

/**
 * 集計(実績)と予測を取得する状態とローダーを返す。
 * fetchAnalytics は実績集計、fetchForecast は指定年月の予測を読む。
 */
export function useShortageAnalytics() {
  const analytics = ref<ShortageAnalytics | null>(null)
  const forecast = ref<ShortageForecast | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAnalytics() {
    const res = await api.get<ShortageAnalytics>('/analytics/shortage')
    analytics.value = res.data
  }

  async function fetchForecast(year: number, month: number) {
    const res = await api.get<ShortageForecast>('/analytics/shortage/forecast', {
      params: { year, month },
    })
    forecast.value = res.data
  }

  /** 実績と予測をまとめて読み込む（画面初期化用）。失敗は error にためる。 */
  async function load(year: number, month: number) {
    loading.value = true
    error.value = null
    try {
      await Promise.all([fetchAnalytics(), fetchForecast(year, month)])
    } catch (e) {
      error.value = e instanceof Error ? e.message : '読み込みに失敗しました'
    } finally {
      loading.value = false
    }
  }

  return { analytics, forecast, loading, error, load, fetchAnalytics, fetchForecast }
}
