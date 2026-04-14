export const createKubotaSakaiTrucksAPI = (client) => ({
  getKubotaSakaiTrucks(params) {
    return client.get('/kubota-sakai-trucks/', { params })
  },
  getKubotaSakaiTruck(id) {
    return client.get(`/kubota-sakai-trucks/${id}/`)
  },
  createKubotaSakaiTruck(data) {
    return client.post('/kubota-sakai-trucks/', data)
  },
  updateKubotaSakaiTruck(id, data) {
    return client.put(`/kubota-sakai-trucks/${id}/`, data)
  },
  deleteKubotaSakaiTruck(id) {
    return client.delete(`/kubota-sakai-trucks/${id}/`)
  },
})
