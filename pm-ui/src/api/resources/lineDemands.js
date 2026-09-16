export const createLineDemandsAPI = (client) => ({
  list(params = {}) {
    const query = { page_size: 2000, ...params }
    return client.get('/line-demands/', { params: query })
  },
  expand(clearExisting = true) {
    return client.post('/line-demands/expand/', {
      clear_existing: clearExisting,
    })
  },
})
