<script setup lang="ts">
import { computed, ref } from 'vue'
import { NAlert, NInputNumber, NSpace } from 'naive-ui'
import AvailabilityCalendar from '@/components/AvailabilityCalendar.vue'
import { useAuthStore } from '@/stores/auth'

// 従業員が自分の希望（休日・希望日・確定出勤・有給）を提出するページ。
// 希望入力はシフト表ページから分離し、ここに集約する。
const auth = useAuthStore()

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)

// 従業員は自分の従業員IDに固定（本人分のみ提出）。
// 管理者は employeeId を渡さない＝カレンダー内のセレクトで従業員を選べる。
const lockedEmployeeId = computed(() =>
  auth.isAdmin ? undefined : (auth.user?.employee_id ?? undefined),
)

// 従業員だが従業員レコードに未紐付けのアカウント（提出先が決まらない）。
const unlinked = computed(() => !auth.isAdmin && auth.user?.employee_id == null)
</script>

<template>
  <div class="request-page">
    <NSpace align="center" wrap style="margin-bottom: 12px">
      <span>対象月:</span>
      <NInputNumber v-model:value="year" :min="2024" :max="2100" style="width: 100px" />
      <NInputNumber v-model:value="month" :min="1" :max="12" style="width: 80px" />
    </NSpace>

    <NAlert v-if="unlinked" type="warning" title="従業員情報に紐付いていません">
      このアカウントはまだ従業員情報に紐付いていないため、希望を提出できません。
      管理者にログイン管理での紐付けを依頼してください。
    </NAlert>
    <template v-else>
      <p class="desc">
        カレンダーの日付をクリックして、休日・希望日・確定出勤・有給を登録できます。
        ここで提出した希望がシフト作成時に反映されます。
      </p>
      <AvailabilityCalendar :year="year" :month="month" :employee-id="lockedEmployeeId" />
    </template>
  </div>
</template>

<style scoped>
.request-page {
  display: flex;
  flex-direction: column;
}
.desc {
  margin: 0 0 12px;
  color: var(--ink-3);
  font-size: 13px;
  line-height: 1.7;
}
</style>
