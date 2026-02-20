import axios from 'axios'
import { createProductsAPI } from './resources/products'
import { createCustomersAPI } from './resources/customers'
import { createShipmentActualsAPI } from './resources/shipmentActuals'
import { createProcessesAPI } from './resources/processes'
import { createLinesAPI } from './resources/lines'
import { createSuppliersAPI } from './resources/suppliers'
import { createProductGroupsAPI } from './resources/productGroups'
import { createContainerCapacitiesAPI } from './resources/containerCapacities'
import { createCalendarsAPI } from './resources/calendars'
import { createWorkPatternsAPI } from './resources/workPatterns'
import { createBomsAPI } from './resources/boms'
import { createRoutingsAPI } from './resources/routings'
import { createOrdersAPI } from './resources/orders'
import { createStagingAPI } from './resources/staging'
import { createLineDemandsAPI } from './resources/lineDemands'
import { createLinePlansAPI } from './resources/linePlans'
import { createLineBacklogsAPI } from './resources/lineBacklogs'
import { createLineGanttPlansAPI } from './resources/lineGanttPlans'
import { createLineDailyScheduleSettingsAPI } from './resources/lineDailyScheduleSettings'
import { createLineDefaultScheduleSettingsAPI } from './resources/lineDefaultScheduleSettings'
import { createLineRealtimeAPI } from './resources/lineRealtime'
import { createProcessRealtimeAPI } from './resources/processRealtime'
import { createBomServiceAPI } from './resources/bomService'
import { createAuthAPI } from './resources/auth'
import { createAccountsAPI } from './resources/accounts'
import { createContactsAPI } from './resources/contacts'
import { createSmtpConfigsAPI } from './resources/smtpConfigs'
import { createPurchasePlanLockSettingAPI } from './resources/purchasePlanLockSetting'
import { createProductionPlanLockSettingAPI } from './resources/productionPlanLockSetting'
import { createScheduleConfigAPI } from './resources/scheduleConfig'
import { createNotificationsAPI } from './resources/notifications'
import { createProductionPlanChangeLogsAPI } from './resources/productionPlanChangeLogs'
import { createEngineeringChangesAPI } from './resources/engineeringChanges'

// ベースURL決定: 環境変数があれば最優先。なければ現在のホスト:8000 → :8081 → localhost。
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:8081/api')

// CSRFトークンをクッキーから取得する関数
function getCookie(name) {
  if (typeof document === 'undefined') return null
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // クッキーを送受信
})

// CSRFトークンを自動的に付与
client.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken')
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  // デバッグ: リクエスト情報をコンソールに出力
  console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, { params: config.params, data: config.data })
  return config
})

client.interceptors.response.use(
  (response) => {
    // デバッグ: レスポンス情報をコンソールに出力
    console.log(`[API Response] ${response.status} ${response.config.url}`, {
      isArray: Array.isArray(response.data),
      length: Array.isArray(response.data) ? response.data.length : 'N/A',
      data: response.data
    })
    return response
  },
  (error) => {
    // デバッグ: エラー情報をコンソールに出力
    console.error(`[API Error] ${error.config?.url}`, error.response || error)
    return Promise.reject(error)
  }
)

const bomsAPI = createBomsAPI(client)

export default {
  products: createProductsAPI(client),
  productGroups: createProductGroupsAPI(client),
  containerCapacities: createContainerCapacitiesAPI(client),
  customers: createCustomersAPI(client),
  lines: createLinesAPI(client),
  suppliers: createSuppliersAPI(client),
  calendars: createCalendarsAPI(client),
  workPatterns: createWorkPatternsAPI(client),
  boms: bomsAPI,
  bomItems: { getBOMItems: bomsAPI.getBOMItems }, // BOMItemsに直接アクセス
  routings: createRoutingsAPI(client),
  orders: createOrdersAPI(client),
  staging: createStagingAPI(client),
  processes: createProcessesAPI(client),
  lineDemands: createLineDemandsAPI(client),
  linePlans: createLinePlansAPI(client),
  lineBacklogs: createLineBacklogsAPI(client),
  shipmentActuals: createShipmentActualsAPI(client),
  lineGanttPlans: createLineGanttPlansAPI(client),
  lineDailyScheduleSettings: createLineDailyScheduleSettingsAPI(client),
  lineDefaultScheduleSettings: createLineDefaultScheduleSettingsAPI(client),
  lineRealtime: createLineRealtimeAPI(client),
  processRealtime: createProcessRealtimeAPI(client),
  bomService: createBomServiceAPI(client),
  auth: createAuthAPI(client),
  accounts: createAccountsAPI(client),
  contacts: createContactsAPI(client),
  smtpConfigs: createSmtpConfigsAPI(client),
  purchasePlanLockSetting: createPurchasePlanLockSettingAPI(client),
  productionPlanLockSetting: createProductionPlanLockSettingAPI(client),
  scheduleConfig: createScheduleConfigAPI(client),
  notifications: createNotificationsAPI(client),
  productionPlanChangeLogs: createProductionPlanChangeLogsAPI(client),
  engineeringChanges: createEngineeringChangesAPI(client),
}
