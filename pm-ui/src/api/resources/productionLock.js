export function createProductionLockAPI(client) {
  return {
    list(params) {
      return client.get('/production-locks/', { params })
    },
    lock(payload) {
      return client.post('/production-locks/', payload)
    },
    unlock(payload) {
      return client.delete('/production-locks/', { data: payload })
    },
  }
}
