// テーマ(ライト/ダーク)ストア。モードの保持・localStorage 保存・html.dark 適用・トグル。
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'
const KEY = 'theme-mode'

function initialMode(): ThemeMode {
  return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', {
  state: () => ({ mode: initialMode() as ThemeMode }),
  getters: {
    isDark: (s) => s.mode === 'dark',
  },
  actions: {
    // html.dark の付け外しで CSS 変数（tokens.css）を切り替える。
    apply() {
      document.documentElement.classList.toggle('dark', this.mode === 'dark')
    },
    setMode(mode: ThemeMode) {
      this.mode = mode
      localStorage.setItem(KEY, mode)
      this.apply()
    },
    // 星マークから呼ぶ: ライトとダークを反転（画面を暗転/復帰）。
    toggle() {
      this.setMode(this.mode === 'dark' ? 'light' : 'dark')
    },
  },
})
