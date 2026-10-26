# 人手不足の記録・集計・予測（need は固定、gap を学習する）

シフト生成のたびに「人数が規定に足りていません（不足）」が出るが、従来その不足は計算して警告表示するだけで保存されておらず、「どの曜日・時間帯が慢性的に人手不足か」を把握・予測する手段が無かった。これを可視化し、採用・希望調整・ルール見直しの判断材料にする。

## 重要な前提：何を学習するのか

必要人数(`need`)は管理者が決める固定ルール（`HourlyStaffingRule`：曜日区分×拡張時）である。したがって**需要そのもの（本当の客数）は学習対象ではない**。本機能が記録・集計・予測するのは、

> 現状の登録メンバー＋希望シフトのパターンだと、どのスロットで `need` に配置が届かなくなりやすいか（＝**人手不足(shortage = required − filled)の起きやすさ**）

である。UI 文言・予測の `caveat` でもこの意味を明示し、「需要予測」と誤認させない。

## 設計（3層＋フロント）

1. **記録**: 新テーブル `CoverageOutcome`（`shift_id, target_date, hour, day_category, weekday, is_holiday, required, filled, shortage`）。シフト生成のたびに、当該月の行を delete→再挿入する（assignments と同じ「月ごと1スナップショット」。再生成で汚染しない）。履歴は「別の月が溜まること」で蓄積される。カバレッジ(required/filled)は深夜跨ぎ・拡張時軸の扱いを二重実装しないよう、`ShiftScheduler` が解から集計して `SchedulerResult.coverage` で返す（`_collect_coverage`）。

2. **集計（ML なし）**: `shortage_analytics.aggregate_shortage` が曜日×拡張時でまとめ、スロット別に {平均不足 / 不足発生率 / 平均required / 平均filled} とランキングを返す。履歴が少なくても実装直後から有用。`GET /api/analytics/shortage`（管理者のみ）。

3. **予測（ML）**: `shortage_forecast` が Strategy で予測器を差し替える。
   - 履歴が十分（`MIN_MONTHS_FOR_MODEL=3` かつ `MIN_ROWS_FOR_MODEL=200`）: numpy の Ridge 回帰（カレンダー特徴＋必要人数から不足を予測。閉形式 `w=(XᵀX+λI)⁻¹Xᵀy`、不足は 0 で下限クリップ）。
   - 少ない／学習失敗: 季節平均ベースライン（(weekday, hour) ごとの平均不足）に自動フォールバック。
   学習はリクエスト時にオンデマンド（小データなので安価・モデル永続化不要。scale-to-zero と相性が良い）。`GET /api/analytics/shortage/forecast?year=&month=`（管理者のみ）。予測には必ず `method`(model/baseline/none) と `caveat`（データが少ない間は参考値）を添える。

4. **フロント**: 管理者専用画面 `/analytics`（`ShortageAnalyticsView`）。実績の慢性不足ヒートマップ＋ランキングと、来月の予測不足ヒートマップ＋手法バッジ/注意書き。

## Considered Options

- **生成AIに数式（最適化モデル）を作らせる**（却下）: infeasible・非決定性・テスト不能・（コード生成なら）セキュリティ問題で "ごたつき" が悪化する。最適化は検証済みの固定 CP-SAT のままにし、AI/ML には入力の精度向上という限定的役割を与える。
- **scikit-learn で本格的なモデル**（現時点では却下）: Cloud Run のイメージ肥大・コールドスタート悪化（¥0/軽量運用方針）。numpy だけの軽量モデル＋ベースラインで始め、精度が必要になれば Strategy に sklearn 実装を後から足せるようにしておく。
- **不足をその場計算のまま（保存しない）**（却下）: 履歴が残らず集計も学習もできない。記録(`CoverageOutcome`)が全ての前提。

## 帰結

- 導入直後は学習データがほぼゼロのため、予測は季節平均ベースライン品質（`caveat` で明示）。**数ヶ月分の生成履歴が溜まるにつれて精度が上がる**。
- `need` を変えたい場合はルール設定で行う（学習ではない）。本機能はあくまで現状ルールに対する不足の起きやすさを示す。
