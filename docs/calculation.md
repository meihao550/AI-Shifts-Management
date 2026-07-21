# シフト計算ロジック（制約と目的関数）

本ドキュメントは、月次シフトを自動生成する CP-SAT ソルバ（[`backend/app/services/scheduler.py`](../backend/app/services/scheduler.py) の `ShiftScheduler`）で使用している **制約** と **目的関数** をまとめたものです。実装から抽出しています。

## 概要

- ソルバ: Google OR-Tools の **CP-SAT**（制約充足＋整数最適化）
- 対象: ある年月（`year`, `month`）の 1 か月分
- 使用パターン: **基本パターン（`is_basic=True`）のみ**（例外パターンは自動割当の対象外）
- 打ち切り時間: 既定 `max_solve_seconds = 20.0` 秒 / 探索ワーカー数 `4`

## 決定変数

```
x[e, d, p] ∈ {0, 1}
```

従業員 `e` に、日 `d`、シフトパターン `p` を割り当てるとき `1`。
（`e` = 従業員、`d` = その月の各日、`p` = 基本パターン）

## 入力データ

| 項目 | 内容 |
| --- | --- |
| `employees` | 従業員（週の希望シフト数 `weekly_target`、`main_shift_type`、時給など） |
| `patterns` | シフトパターン（`category` = `morning` / `evening` / `night`、`is_basic`） |
| `staffing_rules` | `(日区分, シフト区分) → 必要人数`。日区分 = `weekday` / `weekend_or_holiday` |
| `availabilities` | 各従業員の `unavailable`（勤務不可）/ `preferred`（希望） |
| `llm_constraints` | 自然言語メモから LLM が抽出した追加制約（任意） |

日区分の判定（平日か 週末・祝日か）は [`holidays.py`](../backend/app/services/holidays.py) の `category_for()` が行い、**土日＋日本の祝日**（`jpholiday`）を `weekend_or_holiday` として扱います。

`staffing_rules` が未設定の場合は、PDF 仕様に基づく既定値が使われます（[`shifts.py`](../backend/app/routers/shifts.py)）:

| 日区分 | morning | evening | night |
| --- | --- | --- | --- |
| 平日 (`weekday`) | 2 | 2 | 1 |
| 週末・祝日 (`weekend_or_holiday`) | 3 | 3 | 1 |

## 制約（HARD）

必ず満たす必要がある制約です。満たせない場合、ソルバは実行不能（`INFEASIBLE`）を返します。

### H1. 1 人 1 日あたり最大 1 パターン

各従業員は同じ日に高々 1 つのパターンにしか入れない。

```
∀ e, d:  Σ_p x[e, d, p] ≤ 1
```

### H2. 勤務不可日には割り当てない

`unavailable` 指定のある `(従業員, 日)` には一切割り当てない。
LLM が抽出した `hard_unavailable` も同じ扱いで合流させる。

```
∀ (e, d) ∈ unavailable, ∀ p:  x[e, d, p] = 0
```

### H3. 必要人数の充足（過不足なし）

各日・各シフト区分（morning / evening / night）で、割り当て人数が必要人数に **ちょうど一致** する。

```
∀ d, ∀ shift_cat:  Σ_{e, p∈shift_cat} x[e, d, p] = required(day_cat(d), shift_cat)
```

- `required` は `staffing_rules` から取得（未定義は 0）。
- 必要人数 > 0 なのに該当区分のパターンが 1 つも定義されていない場合は、割り当てず **警告** を追加する（ハード制約は課さない）。
- なお実行前チェックとして、1 日の最大必要人員数より有効な従業員数が少ない場合は、ソルバを回す前に HTTP 400 で弾く（[`shifts.py`](../backend/app/routers/shifts.py)）。

## 目的関数（SOFT）

以下を 1 本の目的関数にまとめ、**最小化** する。

```
minimize:  Σ penalties
           − 3 · Σ bonus_terms
           − 5 · Σ main_shift_bonus_terms
```

各項の意味は次のとおり。

### S1. 週の希望シフト数からの乖離ペナルティ（`penalties`）

各従業員の月間目標を、週目標から換算する。

```
monthly_target = weekly × ceil(月の日数 / 7)
```

（`weekly` は LLM の `max_shifts_per_week_override` があればそれを優先）

実割当数 `total` との差を `over`（超過）/ `under`（不足）に分解し、その合計をペナルティとして最小化する。

```
total − monthly_target = over − under
penalty += over + under        （重み 1）
```

→ 目標にできるだけ近い割当数になるよう促す。

### S2. 希望日ボーナス（`bonus_terms`、重み 3）

`preferred`（希望）指定に一致する割当ごとに **報酬**（目的関数を下げる）。
希望に `shift_type` が付いている場合は、パターンの `code` または `category` が一致するもののみ対象。

```
obj −= 3 · Σ (希望に合致した割当)
```

### S3. 得意シフト（`main_shift_type`）ボーナス（`main_shift_bonus_terms`、重み 5）

各従業員の `main_shift_type` に一致する（`p.code == main_shift_type` または `p.category == main_shift_type`）割当ごとに報酬。

```
obj −= 5 · Σ (main_shift に合致した割当)
```

> **重み設計**: `main_shift`（5） > `preferred`（3） > 週目標乖離（1）。
> 得意シフトへの適合を最優先し、次に本人の希望日、最後に労働量の均し（週目標乖離）を調整する。

## 出力

`SchedulerResult`:

| フィールド | 内容 |
| --- | --- |
| `assignments` | 割当リスト（`employee_id`, `target_date`, `shift_type`, `start_time`, `end_time`, `crosses_midnight`） |
| `solver_status` | `OPTIMAL` / `FEASIBLE` / `INFEASIBLE` / `NO_EMPLOYEES` / `NO_PATTERNS` など |
| `solver_seconds` | 求解にかかった秒数 |
| `warnings` | 警告メッセージ（パターン未定義、求解失敗など） |

`crosses_midnight` は終了時刻 ≤ 開始時刻のとき（日跨ぎ）に `True`。

## 補足

- 目的関数の各項（`penalties` / `bonus_terms` / `main_shift_bonus_terms`）がいずれも空の場合は `Minimize` を課さず、H1〜H3 を満たす任意解を返す。
- LLM 由来の制約（`hard_unavailable` / `max_shifts_per_week_override` / `date_notes`）は任意入力で、自然言語メモ（`natural_language_note`）から抽出される。`date_notes` は現状ソルバの制約には未使用（参考情報）。
