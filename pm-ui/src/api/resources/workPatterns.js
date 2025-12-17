export const createWorkPatternsAPI = (client) => ({
  getWorkPatterns() {
    return client.get('/work-patterns/')
  },
  getWorkPattern(id) {
    return client.get(`/work-patterns/${id}/`)
  },
  createWorkPattern(data) {
    return client.post('/work-patterns/', data)
  },
  updateWorkPattern(id, data) {
    return client.put(`/work-patterns/${id}/`, data)
  },
  patchWorkPattern(id, data) {
    return client.patch(`/work-patterns/${id}/`, data)
  },
  deleteWorkPattern(id) {
    return client.delete(`/work-patterns/${id}/`)
  },

  // Break Times
  getBreakTimes(workPatternId) {
    return client.get(`/break-times/?work_pattern=${workPatternId}`)
  },
  createBreakTime(data) {
    return client.post('/break-times/', data)
  },
  updateBreakTime(id, data) {
    return client.put(`/break-times/${id}/`, data)
  },
  deleteBreakTime(id) {
    return client.delete(`/break-times/${id}/`)
  },
})
