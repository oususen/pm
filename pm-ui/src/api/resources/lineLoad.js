export const createLineLoadAPI = (client) => ({
  calculate(data) {
    return client.post('/line-load/calculate/', data)
  },
  coverage(data) {
    return client.post('/line-load/coverage/', data)
  },
})
