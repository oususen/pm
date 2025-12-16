/**
 * ライン実時間記録API
 */
export function createLineRealtimeAPI(client) {
  return {
    /**
     * 記録一覧取得
     */
    list(params = {}) {
      return client.get('/line-realtime-records/', { params })
    },

    /**
     * 記録作成
     */
    create(data) {
      return client.post('/line-realtime-records/', data)
    },

    /**
     * ライン状態一覧取得
     */
    getLineStatuses() {
      return client.get('/line-status/list_all/')
    },

    /**
     * 日次リセット（全ライン）
     */
    resetAllDaily() {
      return client.post('/line-status/reset_all_daily/')
    },
  }
}
