<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useAllowedLoginStore } from '@/stores/allowedLogin'
import { useEmployeeStore } from '@/stores/employee'
import type { AllowedLogin, UserRole } from '@/types'

const store = useAllowedLoginStore()
const employeeStore = useEmployeeStore()
const message = useMessage()
const showAdd = ref(false)
const form = ref<{ name: string; email: string; role: UserRole; employeeId: number | null }>({
  name: '',
  email: '',
  role: 'employee',
  employeeId: null,
})

const roleLabels: Record<UserRole, string> = { admin: '管理者', employee: '一般' }
const roleOptions = [
  { label: '一般', value: 'employee' },
  { label: '管理者', value: 'admin' },
]

// 従業員 select の選択肢（氏名）。id→氏名の表引きにも使う。
const employeeOptions = computed(() =>
  employeeStore.employees.map((e) => ({ label: e.name, value: e.id })),
)
const employeeNameById = computed(
  () => new Map(employeeStore.employees.map((e) => [e.id, e.name])),
)

onMounted(() => {
  store.fetchAll()
  employeeStore.fetchAll()
})

const columns: DataTableColumns<AllowedLogin> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '氏名', key: 'name' },
  { title: 'メールアドレス', key: 'email' },
  { title: '権限', key: 'role', width: 100, render: (r) => roleLabels[r.role] ?? r.role },
  {
    title: '従業員',
    key: 'employee_id',
    render: (r) =>
      r.employee_id != null ? (employeeNameById.value.get(r.employee_id) ?? `#${r.employee_id}`) : '—',
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) =>
      h(
        NPopconfirm,
        { onPositiveClick: () => remove(row.id) },
        {
          default: () => `${row.email} を削除しますか？`,
          trigger: () =>
            h(NButton, { size: 'small', type: 'error', ghost: true }, () => '削除'),
        },
      ),
  },
]

function openAdd() {
  form.value = { name: '', email: '', role: 'employee', employeeId: null }
  showAdd.value = true
}

async function save() {
  if (!form.value.name || !form.value.email) {
    message.warning('氏名とメールアドレスを入力してください')
    return
  }
  // 種別が従業員なら紐付ける従業員の選択を必須にする。
  if (form.value.role === 'employee' && form.value.employeeId == null) {
    message.warning('種別が従業員の場合は従業員を選択してください')
    return
  }
  try {
    await store.create(
      form.value.name,
      form.value.email,
      form.value.role,
      form.value.role === 'employee' ? form.value.employeeId : null,
    )
    message.success('追加しました')
    showAdd.value = false
  } catch (e) {
    message.error(`追加失敗: ${(e as Error).message}`)
  }
}

async function remove(id: number) {
  try {
    await store.remove(id)
    message.success('削除しました')
  } catch (e) {
    message.error(`削除失敗: ${(e as Error).message}`)
  }
}
</script>

<template>
  <NCard title="ログイン管理">
    <template #header-extra>
      <NButton type="primary" @click="openAdd">＋ ログインを許可する人を追加</NButton>
    </template>
    <p style="color: var(--ink-3); font-size: 13px; margin-top: 0">
      ここに登録されたメールアドレスの Google アカウントだけがログインできます。権限は次回ログイン時に反映されます。
    </p>
    <NDataTable
      :columns="columns"
      :data="store.items"
      :loading="store.loading"
      :bordered="false"
    />

    <NModal v-model:show="showAdd" preset="card" title="ログイン許可の追加" style="width: 460px">
      <NForm label-placement="left" label-width="120px">
        <NFormItem label="氏名"><NInput v-model:value="form.name" /></NFormItem>
        <NFormItem label="メールアドレス">
          <NInput v-model:value="form.email" placeholder="example@gmail.com" />
        </NFormItem>
        <NFormItem label="権限">
          <NSelect v-model:value="form.role" :options="roleOptions" />
        </NFormItem>
        <NFormItem v-if="form.role === 'employee'" label="従業員">
          <NSelect
            v-model:value="form.employeeId"
            :options="employeeOptions"
            placeholder="紐付ける従業員を選択（必須）"
            filterable
          />
        </NFormItem>
      </NForm>
      <NSpace justify="end" style="margin-top: 16px">
        <NButton @click="showAdd = false">キャンセル</NButton>
        <NButton type="primary" @click="save">追加</NButton>
      </NSpace>
    </NModal>
  </NCard>
</template>
