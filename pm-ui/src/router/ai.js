const ai = [
  {
    path: '/ai/chat',
    name: 'AIChat',
    component: () => import('@/views/ai/AIChat.vue'),
    meta: { pageTitle: '社内AI（管理者）', manualPath: '共通/社内AIチャット.md', resource: 'settings.ai', permission: 'edit', fallbackToParent: false },
  },
  {
    path: '/ai/analysis',
    name: 'AIAnalysisUserPage',
    component: () => import('@/views/ai/AIAnalysisUserPage.vue'),
    meta: { pageTitle: 'AI分析', manualPath: '共通/AI分析の使い方.md', resource: 'ai.chat', fallbackToParent: false },
  },
]

export default ai
