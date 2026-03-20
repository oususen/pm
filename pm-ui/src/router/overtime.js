const overtime = [
  {
    path: '/overtime',
    redirect: '/overtime/menu',
  },
  {
    path: '/overtime/menu',
    name: 'OvertimeMenu',
    component: () => import('@/views/overtime/OvertimeMenu.vue'),
    meta: { pageTitle: '勤務管理メニュー' },
  },
  {
    path: '/overtime/apply',
    name: 'OvertimeApply',
    component: () => import('@/views/overtime/OvertimeApplicationForm.vue'),
    meta: { pageTitle: '残業申請' },
  },
  {
    path: '/overtime/apply/:id',
    name: 'OvertimeApplyEdit',
    component: () => import('@/views/overtime/OvertimeApplicationForm.vue'),
    props: true,
    meta: { pageTitle: '残業申請 編集' },
  },
  {
    path: '/overtime/list',
    name: 'OvertimeList',
    component: () => import('@/views/overtime/OvertimeApplicationList.vue'),
    meta: { pageTitle: '残業申請 一覧' },
  },
  {
    path: '/overtime/approvals',
    name: 'OvertimeApprovals',
    component: () => import('@/views/overtime/OvertimeApprovalList.vue'),
    meta: { pageTitle: '承認待ち一覧' },
  },
  {
    path: '/overtime/stats',
    name: 'OvertimeStats',
    component: () => import('@/views/overtime/OvertimeMonthlyStats.vue'),
    meta: { pageTitle: '月次労働時間統計' },
  },
]

export default overtime
