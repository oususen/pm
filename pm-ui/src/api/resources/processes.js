export const createProcessesAPI = (client) => ({
  getProcesses(params = {}) {
    return client.get('/processes/', { params })
  },
  getProcess(id) {
    return client.get(`/processes/${id}/`)
  },
  createProcess(data) {
    return client.post('/processes/', data)
  },
  updateProcess(id, data) {
    return client.put(`/processes/${id}/`, data)
  },
  deleteProcess(id) {
    return client.delete(`/processes/${id}/`)
  },
})
