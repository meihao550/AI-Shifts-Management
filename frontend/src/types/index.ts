// 型の宣言をしているファイル

export type UserRole = 'admin' | 'employee'

export interface Me {
  id: number
  email: string
  name: string
  picture_url: string | null
  role: UserRole
  employee_id: number | null
}

export interface Employee {
  id: number
  name: string
  email: string | null
  age: number | null
  paid_leave_amount: number
  transport_cost: number
  hourly_wage: number
  main_shift_type: string | null
  main_shift_pinned: boolean
  weekly_shifts: number
  role: UserRole
  active: boolean
}

export type AvailabilityKind = 'unavailable' | 'preferred'

export interface Availability {
  id: number
  employee_id: number
  target_date: string
  shift_type: string | null
  kind: AvailabilityKind
  note: string | null
}

export interface ShiftPattern {
  id: number
  code: string
  label: string
  start_time: string
  end_time: string
  is_basic: boolean
  category: string
}

export type DayCategory = 'weekday' | 'weekend_or_holiday'

export interface StaffingRule {
  id?: number
  day_category: DayCategory
  shift_category: string
  required: number
}

export type ShiftStatus = 'draft' | 'published' | 'finalized'

export interface ShiftAssignment {
  id: number
  shift_id: number
  employee_id: number
  target_date: string
  shift_type: string
  start_time: string
  end_time: string
  crosses_midnight: boolean
}

export interface Shift {
  id: number
  year: number
  month: number
  status: ShiftStatus
  note: string | null
  assignments: ShiftAssignment[]
}

export interface PayrollRow {
  employee_id: number
  employee_name: string
  total_hours: number
  overnight_hours: number
  base_wage: number
  overnight_premium: number
  transport_cost_total: number
  insurance_status: 'social' | 'employment' | 'none'
  grand_total: number
}

export interface PayrollDay {
  target_date: string
  total_cost: number
  headcount: number
}

export interface PayrollReport {
  year: number
  month: number
  rows: PayrollRow[]
  per_day: PayrollDay[]
  monthly_total: number
}

export interface GenerateShiftResult {
  shift_id: number
  year: number
  month: number
  status: ShiftStatus
  assignments: ShiftAssignment[]
  solver_status: string
  solver_seconds: number
  llm_derived_constraints: Record<string, unknown> | null
  warnings: string[]
}

// 通知の型をつくる
// Notificationクラスじゃない理由としてNotificationはweb通知APIの予約語となっているため
export interface AppNotification {
  kind: string
  level: 'warning' | 'info' | 'success' | 'error'
  message: string
  target_year: number | null
  target_month: number | null
}
