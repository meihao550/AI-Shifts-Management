// シフト自動生成(LLM＋CP-SATソルバー)の実行と、生成時の入力状態・警告を扱う。
import { ref, type Ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useShiftStore } from '@/stores/shift'

/**
 * 生成まわりの状態(useLLM/自然言語メモ/生成警告)と generate() を提供する composable。
 * loading と対象年月は呼び出し側の ref を共有し、生成後処理(afterGenerate)で有給再読込等を行う。
 */
export function useShiftGeneration(opts: {
  year: Ref<number>
  month: Ref<number>
  loading: Ref<boolean>
  afterGenerate: () => Promise<void>
}) {
  const shiftStore = useShiftStore()
  const message = useMessage()

  const genWarnings = ref<string[]>([])
  const useLLM = ref(true)
  const naturalNote = ref('')

  async function generate() {
    opts.loading.value = true
    try {
      const res = await shiftStore.generate({
        year: opts.year.value,
        month: opts.month.value,
        natural_language_note: naturalNote.value,
        use_llm: useLLM.value,
      })
      await opts.afterGenerate()
      genWarnings.value = res.warnings
      if (res.warnings.length) {
        message.warning(`シフトを生成しました（注意 ${res.warnings.length} 件。表の上に表示中）`)
      } else {
        message.success(`シフトを生成しました (${res.solver_seconds}s / ${res.solver_status})`)
      }
    } catch (e) {
      message.error(`生成に失敗: ${(e as Error).message}`)
    } finally {
      opts.loading.value = false
    }
  }

  return { genWarnings, useLLM, naturalNote, generate }
}
