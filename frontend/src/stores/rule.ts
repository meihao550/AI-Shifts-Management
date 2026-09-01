import { defineStore } from 'pinia'
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
    async createPattern(payload: Omit<ShiftPattern, 'id'>) {
      const { data } = await api.post<ShiftPattern>('/rules/patterns', payload)
      this.patterns.push(data)
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
