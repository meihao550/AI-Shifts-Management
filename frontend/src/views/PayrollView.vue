<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NInputNumber,
  NSpace,
  NStatistic,
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

const rowColumns: DataTableColumns<PayrollRow> = [
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

    <NCard v-if="payroll" title="サマリ">
      <NSpace align="center">
        <NStatistic label="月間人件費" :value="payroll.monthly_total.toLocaleString()" suffix="円" />
        <NTag :bordered="false" type="info">従業員数: {{ payroll.rows.length }} 名</NTag>
      </NSpace>
    </NCard>

    <NCard v-if="payroll" title="従業員別">
      <NDataTable :columns="rowColumns" :data="payroll.rows" :bordered="false" />
    </NCard>

    <NCard v-if="payroll" title="日別">
      <NDataTable :columns="dayColumns" :data="payroll.per_day" :bordered="false" />
    </NCard>
  </NSpace>
</template>
