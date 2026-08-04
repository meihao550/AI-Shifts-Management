import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { GenerateShiftResult, PayrollReport, Shift, ShiftAssignment } from '@/types'

interface State {
  shift: Shift | null
  generating: boolean
  payroll: PayrollReport | null
}

export const useShiftStore = defineStore('shift', {
  state: (): State => ({ shift: null, generating: false, payroll: null }),
  actions: {
    async fetch(year: number, month: number) {
      try {
        const { data } = await api.get<Shift>('/shifts', { params: { year, month } })
        this.shift = data
      } catch (err: unknown) {
        if (isAxios404(err)) {
          this.shift = null
        } else {
          throw err
        }
      }
    },
    async generate(payload: {
      year: number
      month: number
      natural_language_note?: string | null
      use_llm?: boolean
    }): Promise<GenerateShiftResult> {
      this.generating = true
      try {
        const { data } = await api.post<GenerateShiftResult>('/shifts/generate', payload)
        this.shift = {
          id: data.shift_id,
          year: data.year,
          month: data.month,
          status: data.status,
          note: payload.natural_language_note ?? null,
          assignments: data.assignments,
        }
        return data
      } finally {
        this.generating = false
      }
    },
    async saveAssignments(shiftId: number, assignments: Omit<ShiftAssignment, 'id' | 'shift_id'>[]) {
      const { data } = await api.put<ShiftAssignment[]>(
        `/shifts/${shiftId}/assignments`,
        assignments,
      )
      if (this.shift) this.shift.assignments = data
    },
    async fetchPayroll(year: number, month: number) {
      try {
        const { data } = await api.get<PayrollReport>('/payroll', { params: { year, month } })
        this.payroll = data
      } catch (err: unknown) {
        if (isAxios404(err)) {
          this.payroll = null
        } else {
          throw err
        }
      }
    },
  },
})

function isAxios404(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    'response' in err &&
    (err as { response?: { status?: number } }).response?.status === 404
  )
}
