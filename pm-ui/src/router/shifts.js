const shifts = [
  {
    path: '/shifts',
    redirect: '/shifts/chart',
  },
  {
    path: '/shifts/chart',
    name: 'ShiftChart',
    component: () => import('@/views/shifts/ShiftManagement.vue'),
    meta: { pageTitle: 'シフト管理', resource: 'overtime.shift_management' },
  },
  {
    path: '/shifts/my-line',
    name: 'WorkerShiftChart',
    component: () => import('@/views/shifts/WorkerShiftChart.vue'),
    meta: { pageTitle: 'シフト確認' },
  },
]

export default shifts
