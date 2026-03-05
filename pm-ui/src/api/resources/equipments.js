export const createEquipmentsAPI = (client) => ({
  getEquipments(params) {
    return client.get('/equipments/', { params })
  },
  getEquipment(id) {
    return client.get(`/equipments/${id}/`)
  },
  createEquipment(data) {
    return client.post('/equipments/', data)
  },
  updateEquipment(id, data) {
    return client.put(`/equipments/${id}/`, data)
  },
  deleteEquipment(id) {
    return client.delete(`/equipments/${id}/`)
  },
})
