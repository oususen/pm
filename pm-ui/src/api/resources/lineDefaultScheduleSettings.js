export const createLineDefaultScheduleSettingsAPI = (client) => ({
  getLineDefaultScheduleSettings(params = {}) {
    return client.get('/line-default-schedule-settings/', { params })
  },
  saveLineDefaultScheduleSetting(payload) {
    return client.post('/line-default-schedule-settings/', payload)
  },
  bulkSaveLineDefaultScheduleSettings(settings) {
    return client.post('/line-default-schedule-settings/bulk_save/', { settings })
  },
})
