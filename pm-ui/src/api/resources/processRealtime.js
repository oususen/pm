/**
 * 工程実時間記録API
 */
export function createProcessRealtimeAPI(client) {
  return {
    list(params = {}) {
      return client.get('/process-realtime-records/', { params })
    },
    create(data) {
      return client.post('/process-realtime-records/', data)
    },
    getProcessStatuses(params = {}) {
      return client.get('/process-realtime-records/status/', { params })
    },
    getSessions(params = {}) {
      return client.get('/process-realtime-records/sessions/', { params })
    },
    createSession(data) {
      return client.post('/process-realtime-records/sessions/', data)
    },
    updateSession(sessionId, data) {
      return client.patch(`/process-realtime-records/sessions/${sessionId}/`, data)
    },
    deleteSession(sessionId) {
      return client.delete(`/process-realtime-records/sessions/${sessionId}/`)
    },
    getScrapBreakdown(id) {
      return client.get(`/process-realtime-records/${id}/scrap-breakdown/`)
    },
    markReplenished(id) {
      return client.post(`/process-realtime-records/${id}/mark-replenished/`)
    },
    markDetailReplenished(id, detailId) {
      return client.post(`/process-realtime-records/${id}/mark-detail-replenished/`, { detail_id: detailId })
    },
    updateScrapDisposition(id, payload) {
      return client.post(`/process-realtime-records/${id}/scrap-disposition/`, payload)
    },
  }
}

