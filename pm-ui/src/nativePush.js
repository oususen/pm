import { Capacitor } from '@capacitor/core'
import { PushNotifications } from '@capacitor/push-notifications'
import api from '@/api/client'

let listenersAttached = false
let currentToken = ''
let currentUserId = null

const isNativeAndroidApp = () => {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
}

const normalizeNotificationData = (notification) => {
  const data = notification?.data || notification?.notification?.data || {}
  const sessionId = Number(data.session_id || data.sessionId || 0)
  return {
    sessionId: sessionId > 0 ? sessionId : null,
    url: data.url || '',
  }
}

const navigateFromPush = (router, notification) => {
  const { sessionId, url } = normalizeNotificationData(notification)
  if (sessionId) {
    router.push(`/notifications/calls?session=${sessionId}`)
    return
  }
  if (typeof url === 'string' && url.startsWith('/')) {
    router.push(url)
  }
}

const createIncomingCallChannel = async () => {
  await PushNotifications.createChannel({
    id: 'incoming_calls',
    name: '社内通話着信',
    description: '社内通話の着信通知',
    importance: 5,
    visibility: 1,
    sound: 'default',
    vibration: true,
    lights: true,
  })
}

const registerCurrentToken = async (user) => {
  if (!user || !currentToken) return
  await api.notifications.registerNativePushToken({
    platform: 'android',
    token: currentToken,
    device_name: navigator.userAgent || '',
    app_version: import.meta.env.VITE_ANDROID_APP_RELEASE_LABEL || '',
  })
  currentUserId = user.id
}

const unregisterCurrentToken = async () => {
  if (!currentToken) return
  try {
    await api.notifications.unregisterNativePushToken(currentToken)
  } catch (error) {
    console.error('ネイティブ Push トークン解除に失敗しました:', error)
  } finally {
    currentUserId = null
  }
}

export const setupNativePushNotifications = async (router) => {
  if (!isNativeAndroidApp()) return
  if (!listenersAttached) {
    await PushNotifications.addListener('registration', async (token) => {
      currentToken = token?.value || ''
      if (!currentToken) return
      const userId = currentUserId
      if (!userId) return
      try {
        await api.notifications.registerNativePushToken({
          platform: 'android',
          token: currentToken,
          device_name: navigator.userAgent || '',
          app_version: import.meta.env.VITE_ANDROID_APP_RELEASE_LABEL || '',
        })
      } catch (error) {
        console.error('ネイティブ Push トークン登録に失敗しました:', error)
      }
    })
    await PushNotifications.addListener('registrationError', (error) => {
      console.error('ネイティブ Push 登録エラー:', error)
    })
    await PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.info('ネイティブ Push 受信:', notification)
    })
    await PushNotifications.addListener('pushNotificationActionPerformed', (notification) => {
      navigateFromPush(router, notification.notification || notification)
    })
    listenersAttached = true
  }
  await createIncomingCallChannel()
}

export const syncNativePushRegistration = async (user) => {
  if (!isNativeAndroidApp()) return
  if (!user) {
    await unregisterCurrentToken()
    try {
      await PushNotifications.unregister()
    } catch (error) {
      console.error('ネイティブ Push の端末解除に失敗しました:', error)
    }
    return
  }

  currentUserId = user.id

  try {
    const configResponse = await api.notifications.getNativePushConfig()
    if (!configResponse.data?.enabled) return

    let permStatus = await PushNotifications.checkPermissions()
    if (permStatus.receive === 'prompt') {
      permStatus = await PushNotifications.requestPermissions()
    }
    if (permStatus.receive !== 'granted') {
      return
    }

    if (currentToken) {
      await registerCurrentToken(user)
      return
    }

    await PushNotifications.register()
  } catch (error) {
    console.error('ネイティブ Push 初期化に失敗しました:', error)
  }
}
