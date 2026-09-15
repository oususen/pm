const shifts = [
  {
    path: '/shifts',
    redirect: '/shifts/chart',
  },
  {
    path: '/shifts/chart',
    name: 'ShiftChart',
    component: () => import('@/views/shifts/ShiftManagement.vue'),
    meta: { pageTitle: 'シフト管理' },
  },
]

export default shifts
