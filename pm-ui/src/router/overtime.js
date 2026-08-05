const overtime = [
  {
    path: '/overtime',
    redirect: '/overtime/menu',
  },
  {
    path: '/overtime/menu',
    name: 'OvertimeMenu',
    component: () => import('@/views/overtime/OvertimeMenu.vue'),
    meta: { pageTitle: '勤務管理メニュー', manualPath: '勤務/勤務管理.md' },
  },
  {
    path: '/overtime/apply',
    name: 'OvertimeApply',
    component: () => import('@/views/overtime/OvertimeApplicationForm.vue'),
    meta: { pageTitle: '残業申請', manualPath: '勤務/残業申請.md' },
  },
  {
    path: '/overtime/apply/:id',
    name: 'OvertimeApplyEdit',
    component: () => import('@/views/overtime/OvertimeApplicationForm.vue'),
    props: true,
    meta: { pageTitle: '残業申請 編集', manualPath: '勤務/残業申請.md' },
  },
  {
    path: '/overtime/my',
    name: 'OvertimeMyApplications',
    component: () => import('@/views/overtime/OvertimeMyApplications.vue'),
    meta: { pageTitle: '自分の申請一覧' },
  },
  {
    path: '/overtime/list',
    name: 'OvertimeList',
    component: () => import('@/views/overtime/OvertimeApplicationList.vue'),
    meta: { pageTitle: '残業申請 一覧', manualPath: '勤務/申請一覧.md' },
  },
  {
    path: '/overtime/approvals',
    name: 'OvertimeApprovals',
    component: () => import('@/views/overtime/OvertimeApprovalList.vue'),
    meta: { pageTitle: '承認待ち一覧', manualPath: '勤務/承認待ち一覧.md' },
  },
  {
    path: '/overtime/stats',
    name: 'OvertimeStats',
    component: () => import('@/views/overtime/OvertimeMonthlyStats.vue'),
    meta: { pageTitle: '月次労働時間統計', manualPath: '勤務/月次労働時間統計.md' },
  },
  {
    path: '/overtime/productivity-stats',
    name: 'OvertimeProductivityStats',
    component: () => import('@/views/overtime/OvertimeProductivityStats.vue'),
    meta: { pageTitle: '加工費集計', manualPath: '勤務/加工費集計.md' },
  },
]

export default overtime
