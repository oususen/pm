export const createEngineeringChangesAPI = (client) => ({
  list() {
    return client.get('/engineering-changes/')
  },
  create(payload) {
    return client.post('/engineering-changes/', payload)
  },
  updatePart(id, payload) {
    return client.put(`/engineering-changes/parts/${id}/`, payload)
  },
  recalculateCase(caseId) {
    return client.post(`/engineering-changes/cases/${caseId}/recalculate/`)
  },
  deletePart(id) {
    return client.delete(`/engineering-changes/parts/${id}/`)
  },
})
