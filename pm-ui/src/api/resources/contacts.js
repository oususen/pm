export const createContactsAPI = (client) => ({
  getContacts(params) {
    return client.get('/contacts/', { params })
  },
  getContact(id) {
    return client.get(`/contacts/${id}/`)
  },
  createContact(data) {
    return client.post('/contacts/', data)
  },
  updateContact(id, data) {
    return client.put(`/contacts/${id}/`, data)
  },
  deleteContact(id) {
    return client.delete(`/contacts/${id}/`)
  },
})
