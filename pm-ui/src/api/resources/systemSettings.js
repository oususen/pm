export const createSystemSettingsAPI = (client) => ({
  // 全設定を辞書形式で取得（ポーリング等の用途）
  getAll: () => client.get('/system-settings/'),
  // 全設定をリスト形式で取得（管理画面用）
  list: () => client.get('/system-settings/detail/'),
  // 新規設定を作成
  create: (data) => client.post('/system-settings/detail/', data),
  // 複数キーをまとめて更新: { key: value, ... }
  updateByKey: (data) => client.patch('/system-settings/update-by-key/', data),
  setPlanQtyPassword: (data) => client.post('/system-settings/set-plan-qty-password/', data),
  verifyPlanQtyPassword: (data) => client.post('/system-settings/verify-plan-qty-password/', data),
})
