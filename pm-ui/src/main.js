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

document.addEventListener('keydown', e => {
  if (e.target.type !== 'number') return
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault()
    const td = e.target.closest('td')
    if (!td) return
    const tr = td.parentElement
    const colIdx = Array.from(tr.children).indexOf(td)
    const nextRow = e.key === 'ArrowUp' ? tr.previousElementSibling : tr.nextElementSibling
    if (!nextRow) return
    const targetTd = nextRow.children[colIdx]
    if (!targetTd) return
    const input = targetTd.querySelector('input[type="number"]')
    if (input) input.focus()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const td = e.target.closest('td')
    if (!td) return
    const tr = td.parentElement
    const colIdx = Array.from(tr.children).indexOf(td)
    const nextRow = tr.nextElementSibling
    if (!nextRow) return
    const targetTd = nextRow.children[colIdx]
    if (!targetTd) return
    const input = targetTd.querySelector('input[type="number"]')
    if (input) input.focus()
  }
})
registerServiceWorker()
setupNativePushNotifications(router)
