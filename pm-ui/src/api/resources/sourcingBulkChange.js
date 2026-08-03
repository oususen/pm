export const createSourcingBulkChangeAPI = (client) => ({
  search(productCode) {
    return client.get('/sourcing-bulk-change/search/', { params: { product_code: productCode } })
  },
  apply(data) {
    return client.post('/sourcing-bulk-change/apply/', data)
  },
})
