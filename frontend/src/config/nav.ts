// アプリの画面遷移ナビ定義。ヘッダーの左ドロワーとホームのランチャーで共有する。
// アイコンは idea/icon 由来のラインアート。白背景を透明化したマスク画像で、
// CSS の mask-image + background-color: currentColor により文字色で塗る（ライト/ダーク両対応）。
import myPageIcon from '@/assets/nav/my-page.png'
import shiftIcon from '@/assets/nav/shift.png'
import requestsIcon from '@/assets/nav/requests.png'
import payrollIcon from '@/assets/nav/payroll.png'
import employeesIcon from '@/assets/nav/employees.png'
import rulesIcon from '@/assets/nav/rules.png'
import loginUsersIcon from '@/assets/nav/login-users.png'

export interface NavItem {
  key: string
  label: string
  to: string
  icon: string
  adminOnly?: boolean
}

/** ナビ項目一覧。adminOnly=true は管理者にだけ表示する。 */
export const navItems: NavItem[] = [
  { key: 'my-page', label: 'マイページ', to: '/mypage', icon: myPageIcon },
  { key: 'shift', label: 'シフト表', to: '/shift', icon: shiftIcon },
  { key: 'requests', label: '希望提出', to: '/requests', icon: requestsIcon },
  { key: 'payroll', label: '人件費', to: '/payroll', icon: payrollIcon, adminOnly: true },
  { key: 'employees', label: '従業員管理', to: '/employees', icon: employeesIcon, adminOnly: true },
  { key: 'rules', label: 'ルール設定', to: '/rules', icon: rulesIcon, adminOnly: true },
  { key: 'login-users', label: 'ログイン管理', to: '/login-users', icon: loginUsersIcon, adminOnly: true },
]
