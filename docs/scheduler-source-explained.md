# シフト自動生成 ソースコード解説

シフト自動生成の実装を、**実際のソースコードを引用しながら**先頭から追って解説します。制約と目的関数の数式的な要約は [`calculation.md`](./calculation.md) にまとまっているので、本書はそれを **コードのどこで・どう実現しているか** に踏み込みます。

対象ファイル:

| ファイル | 役割 |
| --- | --- |
| [`app/routers/shifts.py`](../backend/app/routers/shifts.py) | HTTP エンドポイント。データ収集 → ソルバ呼び出し → 保存 |
| [`app/services/llm.py`](../backend/app/services/llm.py) | 自然言語メモ → 構造化制約（LLM） |
| [`app/services/scheduler.py`](../backend/app/services/scheduler.py) | CP-SAT ソルバ本体（制約・目的関数） |
| [`app/services/holidays.py`](../backend/app/services/holidays.py) | 平日 / 週末・祝日の判定 |

## データフロー全体像

```
POST /api/shifts/generate
        │
        ▼
 generate_shift() … shifts.py
   1. 従業員を取得（active のみ）
   2. シフトパターン取得（無ければ既定 3 種を自動投入）
   3. 必要人数ルール取得（無ければ既定値）
   4. 事前チェック（従業員数 ≥ 1日最大必要人員）
   5. 希望/勤務不可（availability）取得
   6. use_llm なら 自然言語メモ → LLMConstraints
        │
        ▼
 ShiftScheduler.solve() … scheduler.py
   - 決定変数 x[e,d,p] を生成
   - 制約 H1〜H3 を追加
   - 目的関数 S1〜S3 を構築し Minimize
   - CP-SAT で求解 → SchedulerResult
        │
        ▼
   7. 既存割当を削除して結果を保存
   8. ShiftGenerateResult を返す
```

---

## 1. エントリポイント `generate_shift()`（shifts.py）

`POST /api/shifts/generate`。`AdminUser` 依存で **管理者のみ**呼べます。

### 1-1. 従業員の取得

```python
employees = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())
if not employees:
    raise HTTPException(status_code=400, detail="有効な従業員がいません。…")
```

`active=True` の従業員だけを対象にします。0 人なら 400 で早期リターン。

### 1-2. シフトパターンの取得（無ければ自動投入）

```python
patterns = list(db.execute(select(ShiftPattern)).scalars())
if not patterns:
    # Auto-seed defaults so first-time users can generate immediately.
    db.add_all([
        ShiftPattern(code="morning", label="朝 09:00-17:00", start_time=_time(9, 0),  end_time=_time(17, 0), is_basic=True, category="morning"),
        ShiftPattern(code="evening", label="夜 17:00-01:00", start_time=_time(17, 0), end_time=_time(1, 0),  is_basic=True, category="evening"),
        ShiftPattern(code="night",   label="深夜 01:00-09:00", start_time=_time(1, 0), end_time=_time(9, 0),  is_basic=True, category="night"),
    ])
    db.commit()
    patterns = list(db.execute(select(ShiftPattern)).scalars())
```

初回ユーザーがすぐ生成できるよう、パターン未登録なら **朝/夜/深夜の 3 基本パターン**を投入します。`evening` と `night` は終了時刻が開始より早い（日跨ぎ）点に注意。

### 1-3. 必要人数ルール（無ければ既定値）

```python
staffing_rows = list(db.execute(select(StaffingRule)).scalars())
staffing_map = {(r.day_category.value, r.shift_category): r.required for r in staffing_rows}
if not staffing_map:
    staffing_map = {
        (DayCategory.weekday.value, "morning"): 2,
        (DayCategory.weekday.value, "evening"): 2,
        (DayCategory.weekday.value, "night"): 1,
        (DayCategory.weekend_or_holiday.value, "morning"): 3,
        (DayCategory.weekend_or_holiday.value, "evening"): 3,
        (DayCategory.weekend_or_holiday.value, "night"): 1,
    }
```

`staffing_map` のキーは `(日区分, シフト区分)`、値は必要人数。この map が後述の **ハード制約 H3** の右辺になります。

### 1-4. 求解前の実行可能性チェック

```python
max_daily_demand = max(
    staffing_map.get(("weekday", "morning"), 0) + … + staffing_map.get(("weekday", "night"), 0),
    staffing_map.get(("weekend_or_holiday", "morning"), 0) + … + staffing_map.get(("weekend_or_holiday", "night"), 0),
)
if len(employees) < max_daily_demand:
    raise HTTPException(status_code=400, detail="必要人員 (1 日最大 N 名) に対して有効な従業員が … 名しかいません。…")
```

「1 人 1 日 1 パターン」(H1) の下では、ある日の総必要人数を満たすには **少なくともその人数の従業員が必要**です。ソルバに投げる前にこれを検査し、明らかに不可能なら親切なメッセージで 400 を返します（`INFEASIBLE` で無言で失敗するのを防ぐ）。

### 1-5. 希望・勤務不可（availability）の取得

```python
availability_rows = list(db.execute(select(EmployeeAvailability)).scalars())
```

カレンダー UI（[`AvailabilityCalendar.vue`](../frontend/src/components/AvailabilityCalendar.vue)）でクリック登録した `unavailable` / `preferred` がここに入ります。

### 1-6. 自然言語メモ → LLM 制約（任意）

```python
llm_result: dict = {}
if payload.use_llm and payload.natural_language_note:
    employees_hint = [{"id": e.id, "name": e.name} for e in employees]
    llm_result = await derive_constraints_from_text(payload.natural_language_note, employees_hint, payload.year, payload.month)

llm_constraints = LLMConstraints(
    hard_unavailable=llm_result.get("hard_unavailable", []) or [],
    max_shifts_per_week_override=llm_result.get("max_shifts_per_week_override", {}) or {},
    date_notes=llm_result.get("date_notes", {}) or {},
)
```

`use_llm` かつメモがある時だけ LLM を呼び、返ってきた辞書を `LLMConstraints` に詰め替えます。詳細は [§2](#2-自然言語メモの構造化-llmpy)。

### 1-7. ソルバ呼び出しと結果保存

DB モデル（`Employee` / `ShiftPattern` / `EmployeeAvailability`）を、ソルバ用の純粋なデータクラス（`EmployeeSpec` / `PatternSpec` / `AvailabilitySpec`）へ変換して `ShiftScheduler` に渡し、`solve()` します。

```python
scheduler = ShiftScheduler(year=…, month=…, employees=[EmployeeSpec(…)…],
                           patterns=[PatternSpec(…)…], staffing_rules=staffing_map,
                           availabilities=[AvailabilitySpec(…)…], llm_constraints=llm_constraints)
result = scheduler.solve()

shift = _get_or_create_shift(db, payload.year, payload.month)
db.query(ShiftAssignment).filter(ShiftAssignment.shift_id == shift.id).delete()  # 既存を全消し
for a in result.assignments:
    db.add(ShiftAssignment(shift_id=shift.id, **a))
shift.note = payload.natural_language_note
db.commit()
```

> **ポイント**: 生成は毎回 **その月の既存割当を全削除してから入れ直す**（べき等）。再生成しても重複しません。DB モデルとソルバ用データクラスを分離しているので、ソルバは SQLAlchemy に一切依存しません（テスト容易・純粋関数的）。

最後に `ShiftGenerateResult`（割当・`solver_status`・`solver_seconds`・`llm_derived_constraints`・`warnings`）を返します。

---

## 2. 自然言語メモの構造化（llm.py）

`derive_constraints_from_text()` は「今月の事情」テキストを、決まった JSON スキーマへ変換します。**絶対に例外を投げず、失敗時は空の制約を返す**設計です。

```python
async def derive_constraints_from_text(note, employees_hint, year, month) -> dict:
    empty = {"hard_unavailable": [], "max_shifts_per_week_override": {}, "date_notes": {}, "warnings": []}
    if not note or not note.strip():
        return empty
    …
    try:
        if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return await _call_anthropic(...)
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return await _call_openai(...)
    except Exception:
        logger.exception("LLM call failed; falling back to empty constraints")
    empty["warnings"].append("LLM が設定されていない、または呼び出しに失敗したため自然言語制約は無視されました")
    return empty
```

- プロバイダは `LLM_PROVIDER`（`anthropic` / `openai`）で切替。API キー未設定なら呼ばない。
- `SYSTEM_PROMPT` でスキーマを厳密指定し、`_parse_json()` が Markdown コードフェンス（```` ``` ````）を剥がして `json.loads`。
- 出力スキーマ:
  - `hard_unavailable`: `[{employee_id, date, reason}]` → **H2 に合流**（追加の勤務不可）
  - `max_shifts_per_week_override`: `{employee_id: 週上限}` → **S1 の週目標を上書き**
  - `date_notes`: `{date: メモ}` → **現状ソルバ未使用**（参考情報として結果に同梱）
  - `warnings`: 警告文

> LLM が落ちても全体が止まらないのが肝。制約抽出は「あればより良い」補助であり、無くても H1〜H3 と手動の希望だけで生成できます。

---

## 3. スケジューラ本体（scheduler.py）

ここが制約と目的関数の中核です。`ShiftScheduler.solve()` を順に読みます。

### 3-0. 入力データクラスと前処理

```python
self.patterns = [p for p in patterns if p.is_basic]  # scheduler uses only basic patterns
```

コンストラクタで **基本パターンのみ**に絞り込みます（例外パターンは自動割当対象外）。

`solve()` 冒頭のガード:

```python
if not emps:
    return SchedulerResult([], "NO_EMPLOYEES", 0.0, ["従業員が登録されていません"])
if not pats:
    return SchedulerResult([], "NO_PATTERNS", 0.0, ["シフトパターンが未定義です"])
```

勤務不可・希望はルックアップ集合に前処理します。`_unavailable_lookup()` は手動の `unavailable` に **LLM の `hard_unavailable` を合流**させています。

```python
def _unavailable_lookup(self) -> set[tuple[int, date]]:
    s = set()
    for a in self.availabilities:
        if a.kind == "unavailable":
            s.add((a.employee_id, a.target_date))
    for h in self.llm.hard_unavailable:          # ← LLM 由来もここで合流
        try:
            s.add((int(h["employee_id"]), date.fromisoformat(h["date"])))
        except (KeyError, ValueError, TypeError):
            continue                              # 壊れた項目は握りつぶす
    return s
```

### 3-1. 決定変数 `x[e, d, p]`

```python
# x[e, d, p] = 1 if employee e is assigned pattern p on day d
x = {}
for e in emps:
    for d in days:
        for p in pats:
            x[(e.id, d, p.id)] = model.NewBoolVar(f"x_e{e.id}_d{d.isoformat()}_p{p.code}")
```

`従業員 × 日 × 基本パターン` の 3 次元ブール変数。これが解の全て。

### 3-2. 制約 H1 — 1 人 1 日 1 パターンまで

```python
for e in emps:
    for d in days:
        model.Add(sum(x[(e.id, d, p.id)] for p in pats) <= 1)
```

同じ日に複数シフトへ入らない（`≤ 1`）。

### 3-3. 制約 H2 — 勤務不可日は割り当てない

```python
for e in emps:
    for d in days:
        if (e.id, d) in unavailable:
            for p in pats:
                model.Add(x[(e.id, d, p.id)] == 0)
```

`unavailable` 集合（手動 + LLM）に該当する `(従業員, 日)` は全パターンで `0` 固定。

### 3-4. 制約 H3 — 必要人数ちょうど

```python
for d in days:
    day_cat = category_for(d)                     # ← holidays.py。土日 or 祝日 → weekend_or_holiday
    for shift_cat in ("morning", "evening", "night"):
        required = self.staffing_rules.get((day_cat, shift_cat), 0)
        pats_in_cat = [p for p in pats if p.category == shift_cat]
        if not pats_in_cat:
            if required > 0:
                warnings.append(f"{d}: {shift_cat} パターンが定義されておらず必要人数を満たせません")
            continue
        total = sum(x[(e.id, d, p.id)] for e in emps for p in pats_in_cat)
        model.Add(total == required)              # ← 過不足なく「ちょうど」
```

各日・各シフト区分で **割当人数 = 必要人数**（等式）。日区分は `category_for(d)` が決めます（次節）。該当区分のパターンが 1 つも無い場合はハード制約を課さず**警告のみ**（等式を課すと即 `INFEASIBLE` になるため）。

### 3-5. 目的関数の材料 S1 — 週目標からの乖離ペナルティ

```python
max_shifts_override = {int(k): int(v) for k, v in self.llm.max_shifts_per_week_override.items()}
penalties = []
for e in emps:
    weekly = max_shifts_override.get(e.id, e.weekly_target)           # ← LLM 上書き優先
    monthly_target = max(0, weekly * (len(days)//7 + (1 if len(days)%7 else 0)))  # 週→月換算(≒ceil)
    total = sum(x[(e.id, d, p.id)] for d in days for p in pats)
    over  = model.NewIntVar(0, len(days), f"over_e{e.id}")
    under = model.NewIntVar(0, len(days), f"under_e{e.id}")
    model.Add(total - monthly_target == over - under)                # total とtargetの差を over/under に分解
    penalties += [over, under]
```

`total - target = over - under`（`over, under ≥ 0`）という定番の線形化で、絶対偏差 `|total - target|` を表現します。目的関数で `over + under` を最小化することで **目標シフト数に近づけます**。

### 3-6. 目的関数の材料 S2 — 希望日ボーナス

```python
bonus_terms = []
for eid, d, shift_type in preferred:
    for p in pats:
        if shift_type and p.code != shift_type and p.category != shift_type:
            continue                    # 希望に種別指定があれば、その種別のみ対象
        if (eid, d, p.id) in x:
            bonus_terms.append(x[(eid, d, p.id)])
```

`preferred`（希望）に合致する割当変数を集めます。希望に `shift_type` が付いていれば、`code` か `category` が一致するパターンだけを対象にします。

### 3-7. 目的関数の材料 S3 — 得意シフト（main_shift_type）ボーナス

```python
main_shift_bonus_terms = []
for e in emps:
    if not e.main_shift_type:
        continue
    for d in days:
        for p in pats:
            if p.code == e.main_shift_type or p.category == e.main_shift_type:
                main_shift_bonus_terms.append(x[(e.id, d, p.id)])
```

各従業員の `main_shift_type` に一致する割当を集めます。

### 3-8. 目的関数の合成と最小化

```python
obj = 0
if penalties:
    obj += sum(penalties)                       # 乖離ペナルティ  … 重み 1（小さくしたい）
if bonus_terms:
    obj -= 3 * sum(bonus_terms)                 # 希望日ボーナス  … 重み 3（引く=報酬）
if main_shift_bonus_terms:
    obj -= 5 * sum(main_shift_bonus_terms)      # 得意シフト      … 重み 5
if penalties or bonus_terms or main_shift_bonus_terms:
    model.Minimize(obj)
```

**1 本のスカラ目的関数**にまとめて最小化します。ボーナスは「引く」ことで報酬として働きます。重みは

```
得意シフト(5)  >  希望日(3)  >  週目標乖離(1)
```

の順で、得意シフト適合を最優先、次に本人の希望日、最後に労働量の均しを調整します。3 材料がすべて空なら `Minimize` を課さず、H1〜H3 を満たす任意の実行可能解を返します。

### 3-9. 求解とパラメータ

```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = self.max_solve_seconds   # 既定 20 秒で打ち切り
solver.parameters.num_search_workers = 4                         # 並列探索 4
status = solver.Solve(model)
```

時間制限（既定 20 秒）付きで解きます。時間切れでも、それまでに見つけた最良の実行可能解（`FEASIBLE`）を採用できます。

### 3-10. 解の取り出し

```python
if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    for e in emps:
        for d in days:
            for p in pats:
                if solver.Value(x[(e.id, d, p.id)]) == 1:
                    assignments.append({
                        "employee_id": e.id, "target_date": d, "shift_type": p.code,
                        "start_time": p.start, "end_time": p.end,
                        "crosses_midnight": _crosses_midnight(p.start, p.end),
                    })
else:
    warnings.append(f"CP-SAT が解を見つけられませんでした ({status_str})。必要人数や制約を緩めてください。")
```

値が 1 の変数だけを割当として拾います。`_crosses_midnight` は終了 ≤ 開始のとき（深夜跨ぎ）に `True`:

```python
def _crosses_midnight(start: time, end: time) -> bool:
    return end <= start
```

`OPTIMAL` / `FEASIBLE` 以外（`INFEASIBLE` など）のときは割当を空にし、警告を返します。

---

## 4. 日区分の判定（holidays.py）

H3 と、既定人数テーブルの「平日 / 週末・祝日」の振り分けはここが担います。

```python
import jpholiday

def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or is_holiday(d)      # 土(5)・日(6) もしくは 日本の祝日

def category_for(d: date) -> str:
    return "weekend_or_holiday" if is_weekend_or_holiday(d) else "weekday"
```

`jpholiday` により **日本の祝日も「週末・祝日」区分**として扱われ、H3 の必要人数に反映されます（祝日は必要人数が多い設定になりやすい）。

---

## 5. まとめ / 設計上のポイント

- **層の分離**: `shifts.py`（IO・DB・HTTP）→ 純粋データクラス変換 → `scheduler.py`（純粋な最適化ロジック）。ソルバは DB に非依存でテストしやすい。
- **ハードとソフトの使い分け**: 「必ず守る」= H1〜H3 を等式・0 固定で表現し、「なるべく守る」= S1〜S3 を重み付き目的関数で表現。重みで優先順位を制御。
- **フェイルセーフ**: パターン/ルール未登録は既定値で自動補完、LLM 失敗は空制約でスルー、求解前チェックで不可能な依頼を親切に弾く。
- **べき等な再生成**: 生成のたびに当月割当を作り直す。
- **既知の非対応**: `date_notes` はソルバ制約に未反映（表示用）。例外パターンは自動割当の対象外。

数式レベルの定義は [`calculation.md`](./calculation.md) を参照してください。
