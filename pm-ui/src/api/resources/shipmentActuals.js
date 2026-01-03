export const createShipmentActualsAPI = (client) => ({
  getShipmentActuals(params = {}) {
    const queryParams = new URLSearchParams()
    Object.keys(params).forEach((key) => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key])
      }
    })
    const query = queryParams.toString()
    return client.get(`/shipment-actuals/${query ? '?' + query : ''}`)
  },
  createShipmentActual(data) {
    return client.post('/shipment-actuals/', data)
  },
  updateShipmentActual(id, data) {
    return client.put(`/shipment-actuals/${id}/`, data)
  },
  deleteShipmentActual(id) {
    return client.delete(`/shipment-actuals/${id}/`)
  },
  getShipmentActualHistory(id) {
    return client.get(`/shipment-actuals/${id}/history/`)
  },
})
