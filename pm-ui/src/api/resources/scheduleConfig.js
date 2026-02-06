export const createScheduleConfigAPI = (client) => ({
  getConfigs() {
    return client.get('/schedule-config/')
  },
  saveConfig(payload) {
    return client.post('/schedule-config/', payload)
  },
  runNow() {
    return client.post('/schedule-config/run-now/')
  },
})
