export const createPurchaseOrderApprovalConfigAPI = (client) => ({
  get() {
    return client.get('/purchase-order-approval-config/')
  },
  save(data) {
    return client.put('/purchase-order-approval-config/', data)
  },
})
