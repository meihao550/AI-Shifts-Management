import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { hideHeader: true, public: true },
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: () => import('@/views/AuthCallbackView.vue'),
    meta: { hideHeader: true, public: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: 'ホーム' },
    // PC(>768px)では自動的にマイページへ。スマホはホーム(ランチャー)を表示。
    beforeEnter: () => {
      if (window.matchMedia('(min-width: 769px)').matches) {
        return { name: 'my-page' }
      }
    },
  },
  {
    path: '/mypage',
    name: 'my-page',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'マイページ' },
  },
  {
    path: '/shift',
    name: 'shift-table',
    component: () => import('@/views/ShiftTableView.vue'),
    meta: { title: 'シフト表' },
  },
  {
    path: '/employees',
    name: 'employees',
    component: () => import('@/views/EmployeesView.vue'),
    meta: { title: '従業員管理', adminOnly: true },
  },
  {
    path: '/rules',
    name: 'rules',
    component: () => import('@/views/RulesView.vue'),
    meta: { title: 'ルール設定', adminOnly: true },
  },
  {
    path: '/login-users',
    name: 'login-users',
    component: () => import('@/views/LoginUsersView.vue'),
    meta: { title: 'ログイン管理', adminOnly: true },
  },
  {
    path: '/payroll',
    name: 'payroll',
    component: () => import('@/views/PayrollView.vue'),
    meta: { title: '人件費計算', adminOnly: true },
  },
  {
    path: '/employees/:employeeId/calendar',
    name: 'employee-calendar',
    component: () => import('@/views/EmployeeCalendarView.vue'),
    meta: { title: '固定カレンダー', adminOnly: true },
  },
  {
    path: '/print/:shiftId',
    name: 'print-preview',
    component: () => import('@/views/PrintPreviewView.vue'),
    meta: { title: '印刷プレビュー' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.hydrated) {
    await auth.restore()
  }
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.adminOnly && auth.user?.role !== 'admin') {
    return { name: 'my-page' }
  }
})

export default router
