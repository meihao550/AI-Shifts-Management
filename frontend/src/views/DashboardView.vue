<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NSpin, NTag } from 'naive-ui'
import { useShiftStore } from '@/stores/shift'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'

const shiftStore = useShiftStore()
const auth = useAuthStore()
const notification = useNotificationStore()

const router = useRouter()
const loading = ref(false)

const today = new Date()
const year = today.getFullYear()
const month = today.getMonth() + 1

const monthLabel = `${year}年${month}月`

onMounted(async () => {
  loading.value = true
  try {
    await shiftStore.fetch(year, month)
    if (shiftStore.shift) {
      await shiftStore.fetchPayroll(year, month)
    }
    await notification.fetch() // 通知を仕込む
  } finally {
    loading.value = false
  }
})

const shift = computed(() => shiftStore.shift)
const payroll = computed(() => shiftStore.payroll)

const isAdmin = computed(() => auth.isAdmin)

// ログイン本人に紐付く従業員の payroll 行（未紐付け・未作成なら null）。
const myPayrollRow = computed(() =>
  auth.user?.employee_id && payroll.value
    ? (payroll.value.rows.find((r) => r.employee_id === auth.user?.employee_id) ?? null)
    : null,
)

const totalHoursForMe = computed(() => myPayrollRow.value?.total_hours ?? null)

// 予定給与＝本人の見込み給与（当月 payroll の grand_total）。
const myProjectedSalary = computed(() => myPayrollRow.value?.grand_total ?? null)

// 会社全体の人件費合計（管理者のみ表示）。
const monthlyCost = computed(() => payroll.value?.monthly_total ?? 0)
</script>

<template>
  <div class="dashboard">
    <NAlert
      v-for="n in notification.items"
      :key="n.kind"
      :type="n.level"
      show-icon
      style="margin-bottom: 12px"
    >
        {{ n.message }}
    </NAlert>

    <!-- 管理者: 会社全体の人件費合計 -->
    <section v-if="isAdmin" class="cost-hero">
      <div class="cost-hero__band" aria-hidden="true"></div>
      <p class="eyebrow">{{ monthLabel }} の人件費</p>
      <p class="cost-hero__value">
        <span class="yen">¥</span>{{ monthlyCost.toLocaleString() }}
      </p>
      <NButton quaternary size="small" @click="router.push('/payroll')">
        内訳を見る
      </NButton>
    </section>

    <!-- 一般: 本人の予定給与（見込み） -->
    <section v-else class="cost-hero">
      <div class="cost-hero__band" aria-hidden="true"></div>
      <p class="eyebrow">{{ monthLabel }} の予定給与</p>
      <p v-if="myProjectedSalary !== null" class="cost-hero__value">
        <span class="yen">¥</span>{{ myProjectedSalary.toLocaleString() }}
      </p>
      <template v-else>
        <p class="cost-hero__value"><span class="yen">¥</span>—</p>
        <p class="hint">今月のシフトが未作成、または従業員が未紐付けです。</p>
      </template>
    </section>

    <!-- カードのグリッドではなく、区切り線で分けた一覧にして見やすく -->
    <NSpin :show="loading">
      <section class="panel info-list">
        <div class="info-row">
          <span class="info-label">自分の勤務時間</span>
          <span class="info-value">
            <template v-if="totalHoursForMe !== null">
              <span class="num">{{ totalHoursForMe }}</span><span class="unit">h</span>
            </template>
            <span v-else class="muted">従業員リンクなし</span>
          </span>
        </div>

        <div class="info-row">
          <span class="info-label">シフト状態</span>
          <span class="info-value">
            <template v-if="shift">
              <NTag :type="shift.status === 'finalized' ? 'success' : 'default'">
                {{
                  shift.status === 'finalized'
                    ? '確定済み'
                    : shift.status === 'published'
                      ? '公開中'
                      : 'ドラフト'
                }}
              </NTag>
              <span class="hint">割当 {{ shift.assignments.length }} 件</span>
            </template>
            <span v-else class="muted">今月のシフトは未作成</span>
          </span>
        </div>

        <div class="info-row">
          <span class="info-label">シフト概要</span>
          <span class="info-value">
            <span v-if="!(shift && shift.assignments.length)" class="muted">
              今月のシフトはまだ作成されていません
            </span>
            <NButton type="primary" size="small" @click="router.push('/shift')">
              {{ shift && shift.assignments.length ? 'シフト表を開く' : 'シフト表作成' }}
            </NButton>
          </span>
        </div>
      </section>
    </NSpin>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hint {
  color: var(--ink-3);
  font-size: 13px;
}

/* 区切り線で項目を分けた一覧（Grid カードの置き換え） */
.panel {
  background: var(--panel);
  border: 1px solid var(--line-2);
  border-radius: var(--r-panel);
  box-shadow: var(--shadow-panel);
  overflow: hidden;
}
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
}
.info-row:last-child {
  border-bottom: none;
}
.info-label {
  color: var(--ink-2);
  font-weight: 600;
  font-size: 14px;
}
.info-value {
  display: flex;
  align-items: center;
  gap: 10px;
}
.info-value .num {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.info-value .unit {
  font-size: 14px;
  color: var(--ink-2);
  margin-left: 2px;
}
.muted {
  color: var(--ink-3);
  font-size: 13px;
}

/* 人件費ヒーロー: 月の一枚看板 */
.cost-hero {
  position: relative;
  overflow: hidden;
  background: var(--panel);
  border: 1px solid var(--line-2);
  border-radius: var(--r-panel);
  padding: 22px 24px 20px;
  box-shadow: var(--shadow-panel);
}
.cost-hero__band {
  position: absolute;
  inset: 0 auto 0 0;
  width: 6px;
  background: linear-gradient(180deg, var(--morning), var(--evening), var(--night));
}
.cost-hero .eyebrow {
  margin: 0 0 4px;
}
.cost-hero__value {
  margin: 0 0 10px;
  font-size: 44px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
  color: var(--ink);
}
.cost-hero__value .yen {
  font-size: 26px;
  margin-right: 2px;
  color: var(--ink-2);
}
</style>
