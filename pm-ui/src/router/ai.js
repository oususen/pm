const ai = [
  {
    path: '/ai/chat',
    name: 'AIChat',
    component: () => import('@/views/ai/AIChat.vue'),
    meta: { pageTitle: '社内AIチャット', resource: 'ai.chat', fallbackToParent: false },
  },
]

export default ai
