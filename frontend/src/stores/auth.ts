import { acceptHMRUpdate, defineStore } from 'pinia'
import { api } from '@/api/client'
import type { Me } from '@/types'

interface State {
  user: Me | null
  hydrated: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): State => ({ user: null, hydrated: false }),
  getters: {
    isAuthenticated: (s) => !!s.user,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async restore() {
      const token = localStorage.getItem('token')
      if (!token) {
        this.user = null
        this.hydrated = true
        return
      }
      try {
        const { data } = await api.get<Me>('/auth/me')
        this.user = data
      } catch {
        localStorage.removeItem('token')
        this.user = null
      } finally {
        this.hydrated = true
      }
    },
    setToken(token: string) {
      localStorage.setItem('token', token)
    },
    logout() {
      localStorage.removeItem('token')
      this.user = null
    },
  },
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
