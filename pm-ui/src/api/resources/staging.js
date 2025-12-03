export const createStagingAPI = (client) => ({
  // Staging Order Raw
  getStgOrderRaw() {
    return client.get('/stg-order-raw/')
  },
  getStgOrderRawItem(id) {
    return client.get(`/stg-order-raw/${id}/`)
  },

  // Staging Order Daily
  getStgOrderDaily() {
    return client.get('/stg-order-daily/')
  },
  getStgOrderDailyItem(id) {
    return client.get(`/stg-order-daily/${id}/`)
  },
})
