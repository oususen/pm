export function createShiftsAPI(client) {
  return {
    // ライン
    getLines: () => client.get('/shifts/lines/'),
    getLine: (id) => client.get(`/shifts/lines/${id}/`),
    createLine: (data) => client.post('/shifts/lines/', data),
    updateLine: (id, data) => client.patch(`/shifts/lines/${id}/`, data),
    deleteLine: (id) => client.delete(`/shifts/lines/${id}/`),
    reorderWorkers: (lineId, workerIds) =>
      client.post(`/shifts/lines/${lineId}/reorder-workers/`, { worker_ids: workerIds }),
    getProcessLoads: (lineId, date) =>
      client.get(`/shifts/lines/${lineId}/process-loads/`, { params: { date } }),

    // 作業者
    getWorkers: (params) => client.get('/shifts/workers/', { params }),
    createWorker: (data) => client.post('/shifts/workers/', data),
    updateWorker: (id, data) => client.patch(`/shifts/workers/${id}/`, data),
    deleteWorker: (id) => client.delete(`/shifts/workers/${id}/`),

    // ライン工程
    getLineProcesses: (params) => client.get('/shifts/line-processes/', { params }),
    createLineProcess: (data) => client.post('/shifts/line-processes/', data),
    updateLineProcess: (id, data) => client.patch(`/shifts/line-processes/${id}/`, data),
    deleteLineProcess: (id) => client.delete(`/shifts/line-processes/${id}/`),

    // 配置
    getAssignments: (params) => client.get('/shifts/assignments/', { params }),
    getAssignmentsByRange: (params) => client.get('/shifts/assignments/by-range/', { params }),
    createAssignment: (data) => client.post('/shifts/assignments/', data),
    updateAssignment: (id, data) => client.patch(`/shifts/assignments/${id}/`, data),
    deleteAssignment: (id) => client.delete(`/shifts/assignments/${id}/`),
    copyDay: (data) => client.post('/shifts/assignments/copy-day/', data),
    resetDay: (data) => client.post('/shifts/assignments/reset-day/', data),
  }
}
