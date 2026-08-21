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
  getKubotaNaijiBatchPreview(params) {
    return client.get('/stg-order-raw/kubota_naiji_batch_preview/', { params })
  },
  downloadKubotaNaijiBatchReport(params) {
    return client.get('/stg-order-raw/kubota_naiji_batch_report/', {
      params,
      responseType: 'arraybuffer',
    })
  },

  // 汎用内示分析
  getNaijiCustomers() {
    return client.get('/stg-order-daily/naiji_customers/')
  },
  getNaijiProducts(params) {
    return client.get('/stg-order-daily/naiji_products/', { params })
  },
  getNaijiAnalysis(params) {
    return client.get('/stg-order-daily/naiji_analysis/', { params })
  },
  getNaijiBatchPreview(params) {
    return client.get('/stg-order-daily/naiji_batch_preview/', { params })
  },
  downloadNaijiBatchReport(params) {
    return client.get('/stg-order-daily/naiji_batch_report/', {
      params,
      responseType: 'arraybuffer',
    })
  },
  downloadNaijiPptxReport(payload) {
    return client.post('/stg-order-daily/naiji_pptx_report/', payload, {
      responseType: 'arraybuffer',
    })
  },

  manualCreate(data) {
    return client.post('/stg-order-raw/manual-create/', data)
  },
})
