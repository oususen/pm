export function createLineDailyScheduleSettingsAPI(client) {
  const endpoint = '/line-daily-schedule-settings/'

  return {
    /**
     * ライン別日次スケジュール設定一覧を取得
     * @param {Object} params - クエリパラメータ { line, plan_date, plan_date__gte, plan_date__lte }
     */
    getLineDailyScheduleSettings(params = {}) {
      return client.get(endpoint, { params })
    },

    /**
     * 特定のスケジュール設定を取得
     * @param {number} id
     */
    getLineDailyScheduleSetting(id) {
      return client.get(`${endpoint}${id}/`)
    },

    /**
     * スケジュール設定を作成
     * @param {Object} data - { line, plan_date, final_process_start_time, adjust_to_break_end }
     */
    createLineDailyScheduleSetting(data) {
      return client.post(endpoint, data)
    },

    /**
     * スケジュール設定を更新
     * @param {number} id
     * @param {Object} data
     */
    updateLineDailyScheduleSetting(id, data) {
      return client.put(`${endpoint}${id}/`, data)
    },

    /**
     * スケジュール設定を部分更新
     * @param {number} id
     * @param {Object} data
     */
    patchLineDailyScheduleSetting(id, data) {
      return client.patch(`${endpoint}${id}/`, data)
    },

    /**
     * スケジュール設定を削除
     * @param {number} id
     */
    deleteLineDailyScheduleSetting(id) {
      return client.delete(`${endpoint}${id}/`)
    },

    /**
     * 複数のスケジュール設定を一括保存
     * @param {Array} settings - [{ line, plan_date, final_process_start_time, adjust_to_break_end }, ...]
     */
    bulkSaveLineDailyScheduleSettings(settings) {
      return client.post(`${endpoint}bulk_save/`, { settings })
    },
  }
}
