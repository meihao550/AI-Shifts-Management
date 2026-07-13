<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  NSwitch,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useEmployeeStore } from '@/stores/employee'
import type { Employee } from '@/types'

const store = useEmployeeStore()
const message = useMessage()
const showEdit = ref(false)
const form = ref<Partial<Employee>>({})

onMounted(() => store.fetchAll())

const shiftOptions = [
  { label: '朝', value: 'morning' },
  { label: '夜', value: 'evening' },
  { label: '深夜', value: 'night' },
]

const columns: DataTableColumns<Employee> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名前', key: 'name' },
  { title: 'Email', key: 'email' },
  { title: '年齢', key: 'age', width: 80 },
  { title: '時給', key: 'hourly_wage', width: 100, render: (r) => `¥${r.hourly_wage}` },
  { title: '交通費/日', key: 'transport_cost', width: 100, render: (r) => `¥${r.transport_cost}` },
  { title: 'メインシフト', key: 'main_shift_type', width: 100 },
  { title: '週回数', key: 'weekly_shifts', width: 80 },
  { title: 'ロール', key: 'role', width: 90 },
  { title: '在籍', key: 'active', width: 70, render: (r) => (r.active ? '○' : '×') },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row) =>
      h('div', { style: 'display:flex;gap:8px' }, [
        h(
          NButton,
          {
            size: 'small',
            onClick: () => openEdit(row),
          },
          () => '編集',
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => remove(row.id) },
          {
            default: () => '削除しますか？',
            trigger: () => h(NButton, { size: 'small', type: 'error', ghost: true }, () => '削除'),
          },
        ),
      ]),
  },
]

function openCreate() {
  form.value = {
    name: '',
    email: null,
    age: null,
    transport_cost: 0,
    hourly_wage: 1200,
    main_shift_type: 'morning',
    weekly_shifts: 3,
    role: 'employee',
    active: true,
  }
  showEdit.value = true
}

function openEdit(row: Employee) {
  form.value = { ...row }
  showEdit.value = true
}

async function save() {
  try {
    if (form.value.id) {
      await store.update(form.value.id, form.value)
    } else {
      await store.create(form.value)
    }
    message.success('保存しました')
    showEdit.value = false
  } catch (e) {
    message.error(`保存失敗: ${(e as Error).message}`)
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
  <NCard title="従業員管理">
    <template #header-extra>
      <NButton type="primary" @click="openCreate">＋ 新規従業員</NButton>
    </template>
    <NDataTable :columns="columns" :data="store.employees" :loading="store.loading" :bordered="false" />

    <NModal
      v-model:show="showEdit"
      preset="card"
      :title="form.id ? '従業員を編集' : '新規従業員'"
      style="width: 560px"
    >
      <NForm label-placement="left" label-width="110px">
        <NFormItem label="名前"><NInput v-model:value="form.name" /></NFormItem>
        <NFormItem label="Email"><NInput v-model:value="form.email" /></NFormItem>
        <NFormItem label="年齢">
          <NInputNumber v-model:value="form.age" :min="15" :max="99" style="width: 100%" />
        </NFormItem>
        <NFormItem label="時給 (円)">
          <NInputNumber v-model:value="form.hourly_wage" :min="0" style="width: 100%" />
        </NFormItem>
        <NFormItem label="交通費/日 (円)">
          <NInputNumber v-model:value="form.transport_cost" :min="0" style="width: 100%" />
        </NFormItem>
        <NFormItem label="メインシフト">
          <NSelect v-model:value="form.main_shift_type" :options="shiftOptions" clearable />
        </NFormItem>
        <NFormItem label="週勤務回数">
          <NInputNumber v-model:value="form.weekly_shifts" :min="0" :max="7" style="width: 100%" />
        </NFormItem>
        <NFormItem label="ロール">
          <NSelect
            v-model:value="form.role"
            :options="[
              { label: '一般', value: 'employee' },
              { label: '管理者', value: 'admin' },
            ]"
          />
        </NFormItem>
        <NFormItem label="在籍中">
          <NSwitch v-model:value="form.active" />
        </NFormItem>
      </NForm>
      <NSpace justify="end" style="margin-top: 16px">
        <NButton @click="showEdit = false">キャンセル</NButton>
        <NButton type="primary" @click="save">保存</NButton>
      </NSpace>
    </NModal>
  </NCard>
</template>
