export const createLaserShiftRecordsAPI = (client) => ({
  getLaserShiftRecords(params = {}) {
    return client.get('/laser-shift-records/', { params })
  },
  getLaserShiftRecord(id) {
    return client.get(`/laser-shift-records/${id}/`)
  },
  createLaserShiftRecord(data) {
    return client.post('/laser-shift-records/', data)
  },
  patchLaserShiftRecord(id, data) {
    return client.patch(`/laser-shift-records/${id}/`, data)
  },
  deleteLaserShiftRecord(id) {
    return client.delete(`/laser-shift-records/${id}/`)
  },
})
