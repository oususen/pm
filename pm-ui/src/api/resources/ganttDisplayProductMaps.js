export const createGanttDisplayProductMapsAPI = (client) => ({
  getGanttDisplayProductMaps(params = {}) {
    return client.get('/gantt-display-product-maps/', { params })
  },
  getProcessDisplayOrders(params = {}) {
    return client.get('/gantt-display-product-maps/process-display-orders/', { params })
  },
  bulkSaveProcessDisplayOrders(payload) {
    return client.post('/gantt-display-product-maps/process-display-orders/', payload)
  },
  getGanttDisplayProductMap(id) {
    return client.get(`/gantt-display-product-maps/${id}/`)
  },
  createGanttDisplayProductMap(payload) {
    return client.post('/gantt-display-product-maps/', payload)
  },
  updateGanttDisplayProductMap(id, payload) {
    return client.put(`/gantt-display-product-maps/${id}/`, payload)
  },
  deleteGanttDisplayProductMap(id) {
    return client.delete(`/gantt-display-product-maps/${id}/`)
  },
})
