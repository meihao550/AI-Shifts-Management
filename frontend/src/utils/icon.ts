// アイコン描画の共通ユーティリティ。

/**
 * マスク画像(PNG)の URL を CSS 変数 `--nav-ic` に載せた style を返す。
 * 使う側は `.nav-ic { mask-image: var(--nav-ic); background-color: currentColor }`
 * で文字色に合わせて描画する（ライト/ダーク両対応）。
 */
export function maskIconStyle(url: string): Record<string, string> {
  return { '--nav-ic': `url(${url})` }
}
