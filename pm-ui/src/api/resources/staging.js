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

  // クボタ内示分析
  getKubotaNaijiProducts() {
    return client.get('/stg-order-raw/kubota_naiji_products/')
  },
  getKubotaNaijiAnalysis(params) {
    return client.get('/stg-order-raw/kubota_naiji_analysis/', { params })
  },
})
