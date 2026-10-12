<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NCheckbox,
  NCheckboxGroup,
  NDataTable,
  NInputNumber,
  NPopover,
  NSpace,
  NTag,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useShiftStore } from '@/stores/shift'
import type { PayrollDay, PayrollRow } from '@/types'

const store = useShiftStore()
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)

async function load() {
  await store.fetchPayroll(year.value, month.value)
}

onMounted(load)

const payroll = computed(() => store.payroll)

const allRowColumns: DataTableColumns<PayrollRow> = [
  { title: '従業員', key: 'employee_name' },
  { title: '拘束時間', key: 'total_hours', render: (r) => `${r.total_hours} h` },
  { title: '実働時間', key: 'worked_hours', render: (r) => `${r.worked_hours} h` },
  { title: '深夜時間', key: 'overnight_hours', render: (r) => `${r.overnight_hours} h` },
  { title: '基本賃金', key: 'base_wage', render: (r) => `¥${r.base_wage.toLocaleString()}` },
  {
    title: '深夜割増',
    key: 'overnight_premium',
    render: (r) => `¥${r.overnight_premium.toLocaleString()}`,
  },
  {
    title: '交通費',
    key: 'transport_cost_total',
    render: (r) => `¥${r.transport_cost_total.toLocaleString()}`,
  },
  {
    title: '有給',
    key: 'paid_leave_total',
    render: (r) => `¥${r.paid_leave_total.toLocaleString()}（${r.paid_leave_days}日）`,
  },
  {
    title: '保険',
    key: 'insurance_status',
    render: (r) =>
      ({
        social: '社会保険',
        employment: '雇用保険',
        none: '未加入',
      })[r.insurance_status],
  },
  { title: '合計', key: 'grand_total', render: (r) => `¥${r.grand_total.toLocaleString()}` },
]

// 表示する列をオンオフできるようにする（従業員列は識別のため常に表示）。
const columnDefs = [
  { key: 'total_hours', title: '拘束時間' },
  { key: 'worked_hours', title: '実働時間' },
  { key: 'overnight_hours', title: '深夜時間' },
  { key: 'base_wage', title: '基本賃金' },
  { key: 'overnight_premium', title: '深夜割増' },
  { key: 'transport_cost_total', title: '交通費' },
  { key: 'paid_leave_total', title: '有給' },
  { key: 'insurance_status', title: '保険' },
  { key: 'grand_total', title: '合計' },
]
const visibleKeys = ref<string[]>(columnDefs.map((c) => c.key))
const rowColumns = computed<DataTableColumns<PayrollRow>>(() =>
  allRowColumns.filter((c) => {
    if (!('key' in c)) return true
    const key = String(c.key)
    return key === 'employee_name' || visibleKeys.value.includes(key)
  }),
)

const dayColumns: DataTableColumns<PayrollDay> = [
  { title: '日付', key: 'target_date' },
  { title: '人件費', key: 'total_cost', render: (r) => `¥${r.total_cost.toLocaleString()}` },
  { title: '人数', key: 'headcount' },
]
</script>

<template>
  <NSpace vertical>
    <NCard>
      <NSpace align="center">
        <span>対象月:</span>
        <NInputNumber v-model:value="year" :min="2024" :max="2100" style="width: 100px" />
        <NInputNumber v-model:value="month" :min="1" :max="12" style="width: 80px" />
        <NButton type="primary" @click="load">計算</NButton>
      </NSpace>
    </NCard>

    <NAlert v-if="!payroll" type="warning">
      対象月のシフトが存在しないか、まだ計算されていません。
    </NAlert>

    <NAlert v-if="payroll && payroll.warnings.length" type="error" title="要確認">
      <ul style="margin: 0; padding-left: 18px">
        <li v-for="(w, i) in payroll.warnings" :key="i">{{ w }}</li>
      </ul>
    </NAlert>

    <section v-if="payroll" class="cost-hero">
      <div class="cost-hero__band" aria-hidden="true"></div>
      <div>
        <p class="eyebrow">{{ year }}年{{ month }}月 の人件費合計</p>
        <p class="cost-hero__value">
          <span class="yen">¥</span>{{ payroll.monthly_total.toLocaleString() }}
        </p>
      </div>
      <NTag :bordered="false" round>従業員 {{ payroll.rows.length }} 名</NTag>
    </section>

    <NCard v-if="payroll" title="従業員別">
      <template #header-extra>
        <NPopover trigger="click" placement="bottom-end">
          <template #trigger>
            <NButton size="small" secondary>表示する項目</NButton>
          </template>
          <NCheckboxGroup v-model:value="visibleKeys">
            <NSpace vertical size="small">
              <NCheckbox v-for="c in columnDefs" :key="c.key" :value="c.key" :label="c.title" />
            </NSpace>
          </NCheckboxGroup>
        </NPopover>
      </template>
      <NDataTable :columns="rowColumns" :data="payroll.rows" :bordered="false" />
    </NCard>

    <NCard v-if="payroll" title="日別">
      <NDataTable :columns="dayColumns" :data="payroll.per_day" :bordered="false" />
    </NCard>
  </NSpace>
</template>

<style scoped>
.cost-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--panel);
  border: 1px solid var(--line-2);
  border-radius: var(--r-panel);
  padding: 20px 24px;
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
  margin: 0;
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
  color: var(--ink);
}
.cost-hero__value .yen {
  font-size: 24px;
  margin-right: 2px;
  color: var(--ink-2);
}
</style>
