/// <reference types="@capacitor/push-notifications" />

import type { CapacitorConfig } from '@capacitor/cli'

const serverUrl = (process.env.CAPACITOR_SERVER_URL || '').trim()
const cleartext = ['1', 'true', 'yes', 'on'].includes(
  String(process.env.CAPACITOR_CLEAR_TEXT || '').toLowerCase()
)

const config: CapacitorConfig = {
  appId: 'com.daiso.pm',
  appName: 'DAISO管理システム',
  webDir: 'dist',
  plugins: {
    PushNotifications: {
      presentationOptions: ['sound', 'alert', 'banner', 'list'],
    },
  },
}

if (serverUrl) {
  config.server = {
    url: serverUrl,
    cleartext,
  }
}

export default config
