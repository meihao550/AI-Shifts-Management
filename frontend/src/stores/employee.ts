import { acceptHMRUpdate, defineStore } from 'pinia'
import { api } from '@/api/client'
import type {
  Availability,
  AvailabilityKind,
  Employee,
  FixedScheduleItem,
  PairConstraint,
} from '@/types'

interface State {
  employees: Employee[]
  loading: boolean
}

export const useEmployeeStore = defineStore('employee', {
  state: (): State => ({ employees: [], loading: false }),
  actions: {
    async fetchAll() {
      this.loading = true
      try {
        const { data } = await api.get<Employee[]>('/employees')
        this.employees = data
      } finally {
        this.loading = false
      }
    },
    async create(payload: Partial<Employee>) {
      const { data } = await api.post<Employee>('/employees', payload)
      this.employees.push(data)
      return data
    },
    async update(id: number, payload: Partial<Employee>) {
      const { data } = await api.patch<Employee>(`/employees/${id}`, payload)
      const idx = this.employees.findIndex((e) => e.id === id)
      if (idx >= 0) this.employees[idx] = data
      return data
    },
    async remove(id: number) {
      await api.delete(`/employees/${id}`)
      this.employees = this.employees.filter((e) => e.id !== id)
    },
    async listAvailabilities(id: number): Promise<Availability[]> {
      const { data } = await api.get<Availability[]>(`/employees/${id}/availabilities`)
      return data
    },
    async listAllAvailabilities(params: {
      year?: number
      month?: number
      kind?: AvailabilityKind
    }): Promise<Availability[]> {
      const { data } = await api.get<Availability[]>('/employees/availabilities', { params })
      return data
    },
    async createAvailability(payload: Omit<Availability, 'id'>): Promise<Availability> {
      const { data } = await api.post<Availability>('/employees/availabilities', payload)
      return data
    },
    async deleteAvailability(id: number) {
      await api.delete(`/employees/availabilities/${id}`)
    },
    // NGペア（一緒に入れたくない相手）。対称なので (a,b) 片方だけ持てばよい。
    async listPairs(): Promise<PairConstraint[]> {
      const { data } = await api.get<PairConstraint[]>('/pair-constraints')
      return data
    },
    async createPair(aId: number, bId: number): Promise<PairConstraint> {
      const { data } = await api.post<PairConstraint>('/pair-constraints', {
        employee_a_id: aId,
        employee_b_id: bId,
      })
      return data
    },
    async deletePair(id: number) {
      await api.delete(`/pair-constraints/${id}`)
    },
    // 固定カレンダー(曜日パターン)。
    async getFixedSchedule(id: number): Promise<FixedScheduleItem[]> {
      const { data } = await api.get<FixedScheduleItem[]>(`/employees/${id}/fixed-schedule`)
      return data
    },
    async saveFixedSchedule(
      id: number,
      items: FixedScheduleItem[],
    ): Promise<FixedScheduleItem[]> {
      const { data } = await api.put<FixedScheduleItem[]>(
        `/employees/${id}/fixed-schedule`,
        items,
      )
      return data
    },
  },
})

// アクション追加時に dev のホットリロードでストアが古いままにならないようにする
if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEmployeeStore, import.meta.hot))
}
