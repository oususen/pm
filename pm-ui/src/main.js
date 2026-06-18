import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import { registerServiceWorker } from './registerServiceWorker'
import { setupNativePushNotifications } from './nativePush'
import axios from 'axios'

axios.defaults.withCredentials = true
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'

createApp(App).use(router).mount('#app')
registerServiceWorker()
setupNativePushNotifications(router)
