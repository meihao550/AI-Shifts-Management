import { acceptHMRUpdate, defineStore } from 'pinia'
import { api } from '@/api/client'
import type { Me } from '@/types'

interface State {
  user: Me | null
  hydrated: boolean
}

// 起動時に router guard と App.vue が同時に restore() を呼んでも /auth/me が
// 二重に飛ばないよう、進行中のリクエストを1本に共有する（モジュールスコープ）。
let inflight: Promise<void> | null = null

export const useAuthStore = defineStore('auth', {
  state: (): State => ({ user: null, hydrated: false }),
  getters: {
    isAuthenticated: (s) => !!s.user,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    // force=true はログイン直後（setToken 後）に最新の user を取り直すときだけ使う。
    async restore(force = false) {
      if (this.hydrated && !force) return
      if (inflight) {
        await inflight
        return
      }
      inflight = (async () => {
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
      })()
      try {
        await inflight
      } finally {
        inflight = null
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
