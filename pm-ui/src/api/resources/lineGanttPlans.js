export const createLineGanttPlansAPI = (client) => ({
  getLineGanttPlans(params = {}) {
    const queryParams = new URLSearchParams()
    Object.keys(params).forEach((key) => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key])
      }
    })
    const query = queryParams.toString()
    return client.get(`/line-gantt-plans/${query ? '?' + query : ''}`)
  },
  generate(payload) {
    return client.post('/line-gantt-plans/generate/', payload)
  },
  bulkUpdate(payload) {
    return client.put('/line-gantt-plans/bulk-update/', payload)
  },
  bulkStructureSave(payload) {
    return client.post('/line-gantt-plans/bulk-structure-save/', payload)
  },
  manualAdd(payload) {
    return client.post('/line-gantt-plans/manual-add/', payload)
  },
  deleteProcess(payload) {
    return client.post('/line-gantt-plans/remove-process/', payload)
  },
  calcEndTime(payload) {
    return client.post('/line-gantt-plans/calc-end-time/', payload)
  },
  subProcessSave(payload) {
    return client.post('/line-gantt-plans/sub-process-save/', payload)
  },
})
