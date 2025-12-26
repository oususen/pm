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

