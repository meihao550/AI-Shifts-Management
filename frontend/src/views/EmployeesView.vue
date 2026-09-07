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

// メインシフト区分(朝/夜/深夜)は廃止(ADR-0002)。配置制御は「普段入れる時間」に一本化。

// 普段入れる時間帯（1時間刻み, 0〜24）。0:00〜24:00 を選択肢に。
const hourOptions = Array.from({ length: 25 }, (_, h) => ({ label: `${h}:00`, value: h }))

function windowLabel(e: Employee): string {
  if (e.available_start_hour == null || e.available_end_hour == null) return '制限なし'
  return `${e.available_start_hour}:00–${e.available_end_hour}:00`
}

const columns: DataTableColumns<Employee> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名前', key: 'name' },
  { title: '有給', key: 'paid_leave_amount', render: (r)=> `¥${r.paid_leave_amount}`},
  { title: '年齢', key: 'age', width: 80 },
  { title: '時給', key: 'hourly_wage', width: 100, render: (r) => `¥${r.hourly_wage}` },
  { title: '交通費/日', key: 'transport_cost', width: 100, render: (r) => `¥${r.transport_cost}` },
  {
    title: 'Wワーク',
    key: 'is_dual_worker',
    width: 80,
    render: (r) => (r.is_dual_worker ? '○' : ''),
  },
  { title: '週回数', key: 'weekly_shifts', width: 80 },
  {
    title: '週回数固定',
    key: 'weekly_shifts_pinned',
    width: 90,
    render: (r) => (r.weekly_shifts_pinned ? '○' : ''),
  },
  {
    title: '普段の時間',
    key: 'available_start_hour',
    width: 120,
    render: (r) => windowLabel(r),
  },
  {
    title: 'ロール',
    key: 'role',
    width: 90,
    render: (r) => (r.role === 'admin' ? '管理者' : '一般'),
  },
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

// 新規従業員登録の際の初期値
function openCreate() {
  form.value = {
    name: '',
    email: null,
    age: null,
    paid_leave_amount: 0,
    transport_cost: 0,
    hourly_wage: 1200,
    is_dual_worker: false,
    weekly_shifts: 3,
    weekly_shifts_pinned: true,
    role: 'employee',
    active: true,
    available_start_hour: null,
    available_end_hour: null,
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
        <NFormItem label="有給金額">
          <NInputNumber v-model:value="form.paid_leave_amount" :min="0" style="width: 100%" />
        </NFormItem>
        <NFormItem label="Wワーク(掛け持ち)">
          <NSwitch v-model:value="form.is_dual_worker" />
          <span style="margin-left: 8px; color: #8892a6; font-size: 12px">
            ONでWワーク専用パターンにも配置可（OFFは基本パターンのみ）
          </span>
        </NFormItem>
        <NFormItem label="週勤務回数">
          <NInputNumber v-model:value="form.weekly_shifts" :min="0" :max="7" style="width: 100%" />
        </NFormItem>
        <NFormItem label="週回数を固定">
          <NSwitch v-model:value="form.weekly_shifts_pinned" />
          <span style="margin-left: 8px; color: #8892a6; font-size: 12px">
            ONで完全な週はちょうど週回数だけ入れる（絶対遵守。半端な週は目安）
          </span>
        </NFormItem>
        <NFormItem label="普段入れる時間">
          <NSpace align="center" :wrap="false" style="width: 100%">
            <NSelect
              v-model:value="form.available_start_hour"
              :options="hourOptions"
              clearable
              placeholder="開始"
              style="width: 120px"
            />
            <span>〜</span>
            <NSelect
              v-model:value="form.available_end_hour"
              :options="hourOptions"
              clearable
              placeholder="終了"
              style="width: 120px"
            />
          </NSpace>
        </NFormItem>
        <p style="margin: -6px 0 8px 110px; color: var(--ink-3); font-size: 12px">
          1時間刻み。空欄で制限なし。この時間内に収まるシフトにだけ生成配置します（終了が開始以前なら翌日扱い）。
        </p>
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
