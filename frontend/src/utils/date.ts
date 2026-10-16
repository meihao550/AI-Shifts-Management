// 日付まわりの共通ユーティリティ。

/**
 * Date を「端末ローカルの」`YYYY-MM-DD` 文字列に変換する。
 * toISOString() は UTC 変換で日付がずれるため、getFullYear/Month/Date を使う。
 */
export function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
