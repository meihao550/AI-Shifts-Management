<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NDatePicker, NSpace } from 'naive-ui'
import AvailabilityCalendar from '@/components/AvailabilityCalendar.vue'
import { useEmployeeStore } from '@/stores/employee'

const route = useRoute()
const router = useRouter()
const store = useEmployeeStore()

const employeeId = computed(() => Number(route.params.employeeId))

// 表示対象の年月（既定は今月）。月ナビでシフト表と同じ月を編集できる。
const now = new Date()
const cursor = ref<number>(new Date(now.getFullYear(), now.getMonth(), 1).getTime())
const year = computed(() => new Date(cursor.value).getFullYear())
const month = computed(() => new Date(cursor.value).getMonth() + 1)

const employeeName = computed(
  () => store.employees.find((e) => e.id === employeeId.value)?.name ?? `#${employeeId.value}`,
)

onMounted(() => {
  if (!store.employees.length) store.fetchAll()
})

function goBack() {
  router.push('/employees')
}
</script>

<template>
  <NCard :title="`カレンダー：${employeeName}`">
    <template #header-extra>
      <NButton @click="goBack">← 従業員一覧へ戻る</NButton>
    </template>
    <NSpace align="center" style="margin-bottom: 12px">
      <span>対象月:</span>
      <NDatePicker v-model:value="cursor" type="month" />
      <span class="hint">
        シフト表の「休日・希望日」カレンダーと同じデータです。ここでの登録はそちらにも反映されます。
      </span>
    </NSpace>
    <AvailabilityCalendar :year="year" :month="month" :employee-id="employeeId" />
  </NCard>
</template>

<style scoped>
.hint {
  color: var(--ink-3);
  font-size: 12px;
}
</style>
