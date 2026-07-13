import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { ShiftPattern, StaffingRule } from '@/types'

interface State {
  patterns: ShiftPattern[]
  staffing: StaffingRule[]
}

export const useRuleStore = defineStore('rule', {
  state: (): State => ({ patterns: [], staffing: [] }),
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
    async fetchStaffing() {
      const { data } = await api.get<StaffingRule[]>('/rules/staffing')
      this.staffing = data
    },
    async saveStaffing(rows: StaffingRule[]) {
      const { data } = await api.put<StaffingRule[]>('/rules/staffing', rows)
      this.staffing = data
    },
  },
})
