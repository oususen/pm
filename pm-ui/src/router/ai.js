const ai = [
  {
    path: '/ai/chat',
    name: 'AIChat',
    component: () => import('@/views/ai/AIChat.vue'),
    meta: { pageTitle: '社内AI', manualPath: '共通/社内AIチャット.md', anyResources: ['ai.chat', 'ai.analysis'], fallbackToParent: false },
  },
]

export default ai
