export const createGanttDisplayProductMapsAPI = (client) => ({
  getGanttDisplayProductMaps(params = {}) {
    return client.get('/gantt-display-product-maps/', { params })
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
