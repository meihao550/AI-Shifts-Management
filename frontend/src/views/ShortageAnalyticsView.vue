<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NAlert, NCard, NDatePicker, NEmpty, NSpace, NSpin, NTag } from 'naive-ui'
import {
  useShortageAnalytics,
  type ForecastSlot,
  type ShortageSlotStat,
} from '@/composables/useShortageAnalytics'

const { analytics, forecast, loading, error, load, fetchForecast } = useShortageAnalytics()

// 予測対象月。既定は「翌月」。NDatePicker(type=month) はタイムスタンプで持つ。
const now = new Date()
const monthTs = ref(new Date(now.getFullYear(), now.getMonth() + 1, 1).getTime())

const weekdayLabels = ['月', '火', '水', '木', '金', '土', '日']
const weekdays = [0, 1, 2, 3, 4, 5, 6]

/** 拡張時 h を表示用ラベルに（24=翌0時）。 */
function hourLabel(h: number): string {
  return h >= 24 ? `翌${h - 24}時` : `${h}時`
}

// ---- 実績（慢性不足）ヒートマップ -------------------------------------------
const actualMap = computed(() => {
  const m = new Map<string, ShortageSlotStat>()
  for (const s of analytics.value?.slots ?? []) m.set(`${s.weekday}-${s.hour}`, s)
  return m
})
const actualHours = computed(() => {
  const hs = new Set<number>()
  for (const s of analytics.value?.slots ?? []) hs.add(s.hour)
  return [...hs].sort((a, b) => a - b)
})

// ---- 予測ヒートマップ（曜日×時間に平均して可視化） --------------------------
const forecastAgg = computed(() => {
  const sum = new Map<string, { total: number; n: number }>()
  for (const s of forecast.value?.slots ?? []) {
    const k = `${s.weekday}-${s.hour}`
    const cur = sum.get(k) ?? { total: 0, n: 0 }
    cur.total += s.predicted_shortage
    cur.n += 1
    sum.set(k, cur)
  }
  const mean = new Map<string, number>()
  for (const [k, v] of sum) mean.set(k, v.total / v.n)
  return mean
})
const forecastHours = computed(() => {
  const hs = new Set<number>()
  for (const s of forecast.value?.slots ?? []) hs.add(s.hour)
  return [...hs].sort((a, b) => a - b)
})
const forecastMax = computed(() => {
  let mx = 0
  for (const v of forecastAgg.value.values()) mx = Math.max(mx, v)
  return mx
})

/** 不足の強さ(0..1)を indigo 系の背景色に変換する。0 は無色。 */
function cellStyle(intensity: number): Record<string, string> {
  const a = Math.max(0, Math.min(1, intensity))
  if (a <= 0.001) return { background: 'transparent' }
  return {
    background: `rgba(59, 78, 140, ${0.12 + a * 0.78})`,
    color: a > 0.55 ? '#fff' : 'inherit',
  }
}

const methodTag = computed(() => {
  const m = forecast.value?.method
  if (m === 'model') return { text: '学習モデル', type: 'success' as const }
  if (m === 'baseline') return { text: '季節平均(参考値)', type: 'warning' as const }
  return { text: 'データなし', type: 'default' as const }
})

function rankingLabel(s: ShortageSlotStat): string {
  return `${weekdayLabels[s.weekday]} ${hourLabel(s.hour)}`
}

function targetYm(): { year: number; month: number } {
  const d = new Date(monthTs.value)
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

async function onMonthChange() {
  const { year, month } = targetYm()
  await fetchForecast(year, month)
}

onMounted(() => {
  const { year, month } = targetYm()
  load(year, month)
})

// 予測スロットの集計対象が無い（空月）判定に使う
const hasForecast = computed(() => (forecast.value?.slots.length ?? 0) > 0)
const noData = computed(() => (analytics.value?.total_slots ?? 0) === 0)
</script>

<template>
  <div class="analytics">
    <h1 class="page-title">人手不足分析</h1>
    <p class="lead">
      シフト生成のたびに貯まる実績から、<strong>どの曜日・時間帯で規定人数に届きにくいか</strong>を
      可視化・予測します。必要人数はルール設定の固定値のため、ここでは「人手不足の起きやすさ」を見ます。
    </p>

    <NSpin :show="loading">
      <NAlert v-if="error" type="error" :show-icon="true" style="margin-bottom: 16px">
        {{ error }}
      </NAlert>

      <!-- 実績: 慢性的な人手不足 -->
      <NCard title="慢性的な人手不足（実績）" class="section" :bordered="true">
        <template #header-extra>
          <NTag size="small" :bordered="false">
            蓄積 {{ analytics?.months ?? 0 }} ヶ月 / {{ analytics?.total_slots ?? 0 }} スロット
          </NTag>
        </template>

        <NEmpty v-if="noData" description="まだ生成履歴がありません。シフトを生成すると集計されます。" />

        <template v-else>
          <div class="heatmap-wrap">
            <table class="heatmap">
              <thead>
                <tr>
                  <th class="corner">時\曜</th>
                  <th v-for="wd in weekdays" :key="wd">{{ weekdayLabels[wd] }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="h in actualHours" :key="h">
                  <th class="hour">{{ hourLabel(h) }}</th>
                  <td
                    v-for="wd in weekdays"
                    :key="wd"
                    :style="cellStyle(actualMap.get(`${wd}-${h}`)?.shortage_rate ?? 0)"
                    :title="
                      actualMap.get(`${wd}-${h}`)
                        ? `不足率 ${Math.round((actualMap.get(`${wd}-${h}`)!.shortage_rate) * 100)}% / 平均不足 ${actualMap.get(`${wd}-${h}`)!.avg_shortage.toFixed(1)}人 (n=${actualMap.get(`${wd}-${h}`)!.samples})`
                        : 'データなし'
                    "
                  >
                    {{
                      actualMap.get(`${wd}-${h}`) && actualMap.get(`${wd}-${h}`)!.avg_shortage > 0
                        ? actualMap.get(`${wd}-${h}`)!.avg_shortage.toFixed(1)
                        : ''
                    }}
                  </td>
                </tr>
              </tbody>
            </table>
            <p class="legend">色が濃いほど不足が常態化（セルの数字＝平均不足人数, ホバーで詳細）</p>
          </div>

          <div v-if="analytics?.ranking.length" class="ranking">
            <h3>不足しやすい時間帯 TOP</h3>
            <ol>
              <li v-for="(s, i) in analytics.ranking" :key="i">
                <strong>{{ rankingLabel(s) }}</strong>
                — 不足率 {{ Math.round(s.shortage_rate * 100) }}% ・
                平均 {{ s.avg_shortage.toFixed(1) }}人不足
                <span class="muted">(n={{ s.samples }})</span>
              </li>
            </ol>
          </div>
        </template>
      </NCard>

      <!-- 予測: 来月の人手不足 -->
      <NCard title="人手不足の予測" class="section" :bordered="true">
        <template #header-extra>
          <NSpace align="center" :size="8">
            <NTag size="small" :type="methodTag.type" :bordered="false">{{ methodTag.text }}</NTag>
            <NDatePicker
              v-model:value="monthTs"
              type="month"
              size="small"
              :clearable="false"
              @update:value="onMonthChange"
            />
          </NSpace>
        </template>

        <NAlert
          v-if="forecast?.caveat"
          :type="forecast.method === 'model' ? 'info' : 'warning'"
          :show-icon="true"
          style="margin-bottom: 14px"
        >
          {{ forecast.caveat }}
        </NAlert>

        <NEmpty v-if="!hasForecast" description="予測対象のスロットがありません。" />

        <div v-else class="heatmap-wrap">
          <table class="heatmap">
            <thead>
              <tr>
                <th class="corner">時\曜</th>
                <th v-for="wd in weekdays" :key="wd">{{ weekdayLabels[wd] }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in forecastHours" :key="h">
                <th class="hour">{{ hourLabel(h) }}</th>
                <td
                  v-for="wd in weekdays"
                  :key="wd"
                  :style="
                    cellStyle(
                      forecastMax > 0 ? (forecastAgg.get(`${wd}-${h}`) ?? 0) / forecastMax : 0,
                    )
                  "
                  :title="`予測不足 ${(forecastAgg.get(`${wd}-${h}`) ?? 0).toFixed(2)}人`"
                >
                  {{
                    (forecastAgg.get(`${wd}-${h}`) ?? 0) >= 0.05
                      ? (forecastAgg.get(`${wd}-${h}`) ?? 0).toFixed(1)
                      : ''
                  }}
                </td>
              </tr>
            </tbody>
          </table>
          <p class="legend">色が濃いほど来月その曜日・時間帯で不足が出やすい（数字＝予測不足人数）</p>
        </div>
      </NCard>
    </NSpin>
  </div>
</template>

<style scoped>
.analytics {
  max-width: 960px;
  margin: 0 auto;
  padding: 8px 4px 40px;
}
.page-title {
  font-size: 1.4rem;
  margin: 0 0 6px;
}
.lead {
  color: var(--n-text-color-3, #666);
  font-size: 0.9rem;
  line-height: 1.6;
  margin: 0 0 18px;
}
.section {
  margin-bottom: 20px;
}
.heatmap-wrap {
  overflow-x: auto;
}
.heatmap {
  border-collapse: collapse;
  font-size: 0.8rem;
  width: 100%;
}
.heatmap th,
.heatmap td {
  border: 1px solid var(--n-border-color, #e0e0e6);
  text-align: center;
  padding: 4px 2px;
  min-width: 42px;
  height: 26px;
}
.heatmap th.hour,
.heatmap th.corner {
  font-weight: 500;
  white-space: nowrap;
  background: var(--n-color-embedded, rgba(0, 0, 0, 0.03));
}
.legend {
  font-size: 0.75rem;
  color: var(--n-text-color-3, #888);
  margin: 8px 0 0;
}
.ranking {
  margin-top: 18px;
}
.ranking h3 {
  font-size: 0.95rem;
  margin: 0 0 8px;
}
.ranking ol {
  margin: 0;
  padding-left: 20px;
  line-height: 1.9;
  font-size: 0.88rem;
}
.muted {
  color: var(--n-text-color-3, #999);
  font-size: 0.8rem;
}
</style>
