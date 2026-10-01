const ai = [
  {
    path: '/ai/chat',
    name: 'AIChat',
    component: () => import('@/views/ai/AIChat.vue'),
    meta: { pageTitle: '社内AIチャット', manualPath: '共通/社内AIチャット.md', resource: 'ai.chat', fallbackToParent: false },
  },
]

export default ai
