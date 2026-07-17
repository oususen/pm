export const createManualDocumentsAPI = (client) => ({
  read(path) {
    return client.get('/manual-documents/read/', { params: { path } })
  },
  write(path, content) {
    return client.post('/manual-documents/write/', { path, content })
  },
})
