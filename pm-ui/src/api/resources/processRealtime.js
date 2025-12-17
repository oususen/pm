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
  }
}

