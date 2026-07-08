export const createAuthAPI = (client) => ({
  csrf() {
    return client.get('/auth/csrf/')
  },
  login(payload) {
    return client.post('/auth/login/', payload)
  },
  getSwitchableUsers() {
    return client.get('/auth/switchable-users/')
  },
  switchUser(payload) {
    return client.post('/auth/switch-user/', payload)
  },
  switchBack() {
    return client.post('/auth/switch-back/')
  },
  logout() {
    return client.post('/auth/logout/')
  },
  me() {
    return client.get('/auth/me/')
  },
})
