import { acceptHMRUpdate, defineStore } from 'pinia'
import { api } from '@/api/client'
import type { AllowedLogin, UserRole } from '@/types'

interface State {
  items: AllowedLogin[]
  loading: boolean
}

export const useAllowedLoginStore = defineStore('allowedLogin', {
  state: (): State => ({ items: [], loading: false }),
  actions: {
    async fetchAll() {
      this.loading = true
      try {
        const { data } = await api.get<AllowedLogin[]>('/allowed-logins')
        this.items = data
      } finally {
        this.loading = false
      }
    },
    async create(name: string, email: string, role: UserRole) {
      const { data } = await api.post<AllowedLogin>('/allowed-logins', { name, email, role })
      this.items.push(data)
      return data
    },
    async remove(id: number) {
      await api.delete(`/allowed-logins/${id}`)
      this.items = this.items.filter((x) => x.id !== id)
    },
  },
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAllowedLoginStore, import.meta.hot))
}
