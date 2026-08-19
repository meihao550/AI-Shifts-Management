import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { AppNotification } from '@/types'

interface State {
  items: AppNotification[]
}

export const useNotificationStore = defineStore('notification', {
  state: (): State => ({ items: [] }),
  actions: {
    async fetch() {
      const { data } = await api.get<AppNotification[]>('/notifications')
      this.items = data
    },
  },
})
