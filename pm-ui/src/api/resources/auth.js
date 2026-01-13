export const createAuthAPI = (client) => ({
  csrf() {
    return client.get('/auth/csrf/')
  },
  login(payload) {
    return client.post('/auth/login/', payload)
  },
  logout() {
    return client.post('/auth/logout/')
  },
  me() {
    return client.get('/auth/me/')
  },
})
