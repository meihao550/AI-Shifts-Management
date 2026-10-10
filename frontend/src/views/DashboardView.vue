<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NCard,
  NEmpty,
  NGrid,
  NGridItem,
  NSpin,
  NTag,
} from 'naive-ui'
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

    <NGrid :x-gap="16" :y-gap="16" :cols="2" responsive="screen">
      <NGridItem>
        <NCard title="自分の勤務時間">
          <p v-if="totalHoursForMe !== null" class="stat-number">
            {{ totalHoursForMe }}<span class="unit">h</span>
          </p>
          <NEmpty v-else description="従業員リンクなし" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard title="シフト状態">
          <div v-if="shift" class="status-row">
            <NTag :type="shift.status === 'finalized' ? 'success' : 'default'" size="large">
              {{
                shift.status === 'finalized'
                  ? '確定済み'
                  : shift.status === 'published'
                    ? '公開中'
                    : 'ドラフト'
              }}
            </NTag>
            <span class="hint">割当 {{ shift.assignments.length }} 件</span>
          </div>
          <NEmpty v-else description="今月のシフトは未作成" />
        </NCard>
      </NGridItem>
    </NGrid>

    <NCard title="シフト概要" style="margin-top: 24px">
      <NSpin :show="loading">
        <div v-if="shift && shift.assignments.length" class="preview">
          <p>
            {{ monthLabel }} のシフトが登録されています。詳細な編集・生成はシフト表画面へ。
          </p>
          <NButton type="primary" @click="router.push('/shift')">シフト表を開く</NButton>
        </div>
        <div v-else class="preview">
          <NEmpty description="今月のシフトはまだ作成されていません">
            <template #extra>
              <NButton type="primary" @click="router.push('/shift')">
                シフト表作成
              </NButton>
            </template>
          </NEmpty>
        </div>
      </NSpin>
    </NCard>
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

.preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-number .unit {
  font-size: 16px;
  color: var(--ink-2);
  margin-left: 3px;
}
</style>
