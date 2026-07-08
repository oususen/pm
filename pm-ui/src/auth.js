import { reactive } from 'vue'
import api from './api/client'

const authState = reactive({
  user: null,
  ready: false,
})

let authPromise = null

const setUser = (user) => {
  authState.user = user || null
  authState.ready = true
}

const normalizeUser = (data) => {
  if (!data || data.authenticated !== true) return null
  return data.user || null
}

export const ensureAuth = async () => {
  if (authState.ready) {
    return authState.user
  }

  if (!authPromise) {
    authPromise = api.auth
      .me()
      .then((res) => normalizeUser(res.data))
      .catch(() => null)
      .then((user) => {
        setUser(user)
        return user
      })
      .finally(() => {
        authPromise = null
      })
  }

  return authPromise
}

export const login = async (username, password) => {
  await api.auth.csrf()
  const res = await api.auth.login({ username, password })
  const user = res.data?.user || null
  setUser(user)
  return user
}

export const switchUser = async (userId) => {
  await api.auth.csrf()
  const res = await api.auth.switchUser({ user_id: userId })
  const user = res.data?.user || null
  setUser(user)
  return user
}

export const switchBack = async () => {
  await api.auth.csrf()
  const res = await api.auth.switchBack()
  const user = res.data?.user || null
  setUser(user)
  return user
}

export const logout = async () => {
  try {
    await api.auth.logout()
  } finally {
    setUser(null)
  }
}

export { authState }
