export function createActualCycleTimesAPI(client) {
  return {
    calc(params) {
      return client.get('/actual-cycle-time/calc/', { params })
    },
    save(data) {
      return client.post('/actual-cycle-time/save/', data)
    },
    calcFinished(params) {
      return client.get('/finished-product-cycle-time/calc/', { params })
    },
    saveFinished(data) {
      return client.post('/finished-product-cycle-time/save/', data)
    },
    list(params) {
      return client.get('/actual-cycle-time/list/', { params })
    },
    listFinished(params) {
      return client.get('/finished-product-cycle-time/list/', { params })
    },
  }
}
