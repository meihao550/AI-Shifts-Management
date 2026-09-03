import { acceptHMRUpdate, defineStore } from 'pinia'
import { api } from '@/api/client'
import type { HourlyStaffingRule, ShiftPattern } from '@/types'

interface State {
  patterns: ShiftPattern[]
  hourlyStaffing: HourlyStaffingRule[]
}

export const useRuleStore = defineStore('rule', {
  state: (): State => ({ patterns: [], hourlyStaffing: [] }),
  actions: {
    async fetchPatterns() {
      const { data } = await api.get<ShiftPattern[]>('/rules/patterns')
      this.patterns = data
    },
    // 追加は時刻＋休憩のみ。コード/区分はサーバ側で自動生成する。
    async createPattern(payload: {
      start_time: string
      end_time: string
      label?: string
      rest_minutes?: number
    }) {
      const { data } = await api.post<ShiftPattern>('/rules/patterns', payload)
      this.patterns.push(data)
    },
    // 編集: 表示名・開始・終了・休憩のうち渡した項目だけ更新する。
    async updatePattern(
      id: number,
      payload: {
        label?: string
        start_time?: string
        end_time?: string
        rest_minutes?: number
      },
    ) {
      const { data } = await api.patch<ShiftPattern>(`/rules/patterns/${id}`, payload)
      const i = this.patterns.findIndex((p) => p.id === id)
      if (i !== -1) this.patterns[i] = data
    },
    async deletePattern(id: number) {
      await api.delete(`/rules/patterns/${id}`)
      this.patterns = this.patterns.filter((p) => p.id !== id)
    },
    async fetchHourlyStaffing() {
      const { data } = await api.get<HourlyStaffingRule[]>('/rules/hourly-staffing')
      this.hourlyStaffing = data
    },
    async saveHourlyStaffing(rows: HourlyStaffingRule[]) {
      const { data } = await api.put<HourlyStaffingRule[]>('/rules/hourly-staffing', rows)
      this.hourlyStaffing = data
    },
  },
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useRuleStore, import.meta.hot))
}
