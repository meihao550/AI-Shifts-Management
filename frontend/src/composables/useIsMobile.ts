import { onMounted, onUnmounted, ref } from 'vue'

// 画面幅がスマホサイズ(既定 ≤768px)かどうかを反応的に返す。
// 一覧テーブルを狭幅で「展開行」に切り替える判定に使う。
export function useIsMobile(maxWidth = 768) {
  const isMobile = ref(false)
  let mql: MediaQueryList | null = null
  const update = () => {
    isMobile.value = mql ? mql.matches : false
  }

  onMounted(() => {
    mql = window.matchMedia(`(max-width: ${maxWidth}px)`)
    update()
    mql.addEventListener('change', update)
  })
  onUnmounted(() => {
    mql?.removeEventListener('change', update)
  })

  return isMobile
}
