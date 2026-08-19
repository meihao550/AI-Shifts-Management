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
  NStatistic,
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

const totalHoursForMe = computed(() => {
  if (!auth.user?.employee_id || !payroll.value) return null
  return (
    payroll.value.rows.find((r) => r.employee_id === auth.user?.employee_id)?.total_hours ?? 0
  )
})

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

    <NGrid :x-gap="16" :y-gap="16" :cols="3" responsive="screen">
      <NGridItem>
        <NCard title="今月">
          <NStatistic :label="monthLabel" :value="monthlyCost.toLocaleString()" suffix="円 (人件費)" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard title="自分の勤務時間">
          <NStatistic v-if="totalHoursForMe !== null" label="今月の総勤務時間" :value="totalHoursForMe" suffix="h" />
          <NEmpty v-else description="従業員リンクなし" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard title="シフト状態">
          <div v-if="shift">
            <NTag :type="shift.status === 'finalized' ? 'success' : 'default'" size="large">
              {{
                shift.status === 'finalized'
                  ? '確定済み'
                  : shift.status === 'published'
                    ? '公開中'
                    : 'ドラフト'
              }}
            </NTag>
            <p class="hint">割当件数: {{ shift.assignments.length }}</p>
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
  color: #8892a6;
  margin: 8px 0 0;
  font-size: 12px;
}

.preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
