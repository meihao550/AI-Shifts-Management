// 希望(availability)の種別ラベル。カレンダーの composable とタグ表示で共有する。
import type { AvailabilityKind } from '@/types'

export const KIND_LABELS: Record<AvailabilityKind, string> = {
  unavailable: '休日',
  preferred: '希望日',
  mandatory: '確定出勤',
  paid_leave: '有給',
}
