// 曜日まわりの共通ユーティリティ（日=赤/土=青、土日=休日扱い）。

/**
 * 曜日に応じた文字色を返す。日曜=赤, 土曜=青, 平日=null（色指定なし）。
 * カレンダー・シフト表の日付表示色に使う。平日の既定色は呼び出し側で決める。
 */
export function weekdayColor(d: Date): string | null {
  const w = d.getDay()
  if (w === 0) return '#c92a2a' // 日曜
  if (w === 6) return '#1971c2' // 土曜
  return null
}

/**
 * 土日を「休日扱い」にした日区分を返す。必要人数ルール(平日/休日)の判定に使う。
 * （祝日は未考慮。backend 側の判定と同じ区分）
 */
export function dayCategory(d: Date): 'weekday' | 'weekend_or_holiday' {
  const w = d.getDay()
  return w === 0 || w === 6 ? 'weekend_or_holiday' : 'weekday'
}
