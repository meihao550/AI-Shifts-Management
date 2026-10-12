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
import { useIsMobile } from '@/composables/useIsMobile'
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

function loginEmployeeLabel(r: AllowedLogin): string {
  return r.employee_id != null
    ? (employeeNameById.value.get(r.employee_id) ?? `#${r.employee_id}`)
    : '—'
}

function renderDeleteButton(row: AllowedLogin) {
  return h(
    NPopconfirm,
    { onPositiveClick: () => remove(row.id) },
    {
      default: () => `${row.email} を削除しますか？`,
      trigger: () => h(NButton, { size: 'small', type: 'error', ghost: true }, () => '削除'),
    },
  )
}

const desktopColumns: DataTableColumns<AllowedLogin> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '氏名', key: 'name' },
  { title: 'メールアドレス', key: 'email' },
  { title: '権限', key: 'role', width: 100, render: (r) => roleLabels[r.role] ?? r.role },
  { title: '従業員', key: 'employee_id', render: (r) => loginEmployeeLabel(r) },
  { title: '操作', key: 'actions', width: 100, render: (row) => renderDeleteButton(row) },
]

// スマホ幅では列を ID・氏名・詳細(展開)に絞り、残りと操作は展開行で見せる。
const isMobile = useIsMobile()
const rowKey = (row: AllowedLogin) => row.id

function detailRow(label: string, value: unknown) {
  return h(
    'div',
    {
      style:
        'display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid var(--line)',
    },
    [
      h('span', { style: 'color:var(--ink-2);font-size:13px' }, label),
      h('span', { style: 'font-weight:600;text-align:right;word-break:break-all' }, String(value)),
    ],
  )
}

function renderLoginDetail(row: AllowedLogin) {
  return h('div', { style: 'padding:8px 4px 4px' }, [
    detailRow('メールアドレス', row.email),
    detailRow('権限', roleLabels[row.role] ?? row.role),
    detailRow('従業員', loginEmployeeLabel(row)),
    h('div', { style: 'margin-top:12px' }, [renderDeleteButton(row)]),
  ])
}

const mobileColumns: DataTableColumns<AllowedLogin> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '氏名', key: 'name' },
  { type: 'expand', title: '詳細', renderExpand: renderLoginDetail },
]

const columns = computed<DataTableColumns<AllowedLogin>>(() =>
  isMobile.value ? mobileColumns : desktopColumns,
)

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
      :row-key="rowKey"
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
