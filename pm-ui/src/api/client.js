import axios from 'axios'
import { createProductsAPI } from './resources/products'
import { createCustomersAPI } from './resources/customers'
import { createShipmentActualsAPI } from './resources/shipmentActuals'
import { createProcessesAPI } from './resources/processes'
import { createLinesAPI } from './resources/lines'
import { createSuppliersAPI } from './resources/suppliers'
import { createProductGroupsAPI } from './resources/productGroups'
import { createProductCodeMappingsAPI } from './resources/productCodeMappings'
import { createContainerCapacitiesAPI } from './resources/containerCapacities'
import { createEquipmentsAPI } from './resources/equipments'
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
import { createMobileDevicesAPI } from './resources/mobileDevices'
import { createSmtpConfigsAPI } from './resources/smtpConfigs'
import { createPurchasePlanLockSettingAPI } from './resources/purchasePlanLockSetting'
import { createProductionPlanLockSettingAPI } from './resources/productionPlanLockSetting'
import { createProductionRecordSettingsAPI } from './resources/productionRecordSettings'
import { createScheduleConfigAPI } from './resources/scheduleConfig'
import { createLineBacklogAdjustmentsAPI } from './resources/lineBacklogAdjustments'
import { createNotificationsAPI } from './resources/notifications'
import { createProductionPlanChangeLogsAPI } from './resources/productionPlanChangeLogs'
import { createLaserPatternsAPI } from './resources/laserPatterns'
import { createLaserActualsAPI } from './resources/laserActuals'
import { createLaserShiftRecordsAPI } from './resources/laserShiftRecords'
import { createEngineeringChangesAPI } from './resources/engineeringChanges'
import { createPurchaseActualsAPI } from './resources/purchaseActuals'
import { createFujishojiDocumentAPI } from './resources/fujishojiDocument'
import { createSupplierOrderPatternsAPI } from './resources/supplierOrderPatterns'
import { createSupplierOrderSchedulesAPI } from './resources/supplierOrderSchedules'
import { createPurchaseOrderProposalsAPI } from './resources/purchaseOrderProposals'
import { createPurchaseOrderApprovalConfigAPI } from './resources/purchaseOrderApprovalConfig'
import { createQualityEquipmentInspectionsAPI } from './resources/qualityEquipmentInspections'
import { createProductChecksheetsAPI } from './resources/productChecksheets'
import { createIntegratedChecksheetsAPI } from './resources/integratedChecksheets'
import { createOvertimeAPI } from './resources/overtime'
import { createBrakeLineActualsAPI } from './resources/brakeLineActuals'
import { createSpotLineActualsAPI } from './resources/spotLineActuals'
import { createSystemSettingsAPI } from './resources/systemSettings'
import { createGanttDisplayProductMapsAPI } from './resources/ganttDisplayProductMaps'
import { createLineProductDisplayOrdersAPI } from './resources/lineProductDisplayOrders'
import { createPlanDeviationReportAPI, createRecordConfirmationAPI } from './resources/planDeviationReport'
import { createKubotaSakaiTrucksAPI } from './resources/kubotaSakaiTrucks'
import { createKubotaSakaiDueAdjustmentsAPI } from './resources/kubotaSakaiDueAdjustments'
import { createKubotaSakaiTripAssignmentsAPI } from './resources/kubotaSakaiTripAssignments'
import { createShippingTripsAPI } from './resources/shippingTrips'
import { createShipToLeadTimesAPI } from './resources/shipToLeadTimes'
import { createCameraActualsAPI } from './resources/cameraActuals'
import { createOutsourceAPI } from './resources/outsource'

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

const API_DEBUG_LOG = import.meta.env.VITE_API_DEBUG_LOG === 'true'

// CSRFトークンを自動的に付与
client.interceptors.request.use((config) => {
  // FormData の場合は Content-Type をブラウザに委譲し、boundary 付きで送る
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    if (config.headers && typeof config.headers.set === 'function') {
      config.headers.set('Content-Type', undefined)
    } else if (config.headers) {
      delete config.headers['Content-Type']
    }
  }

  const csrfToken = getCookie('csrftoken')
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  if (API_DEBUG_LOG) {
    // デバッグ時のみ出力
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, { params: config.params, data: config.data })
  }
  return config
})

client.interceptors.response.use(
  (response) => {
    if (API_DEBUG_LOG) {
      // デバッグ時のみ出力
      console.log(`[API Response] ${response.status} ${response.config.url}`, {
        isArray: Array.isArray(response.data),
        length: Array.isArray(response.data) ? response.data.length : 'N/A',
        data: response.data
      })
    }
    return response
  },
  (error) => {
    if (API_DEBUG_LOG) {
      // デバッグ時のみ出力
      console.error(`[API Error] ${error.config?.url}`, error.response || error)
    }
    return Promise.reject(error)
  }
)

const bomsAPI = createBomsAPI(client)

export default {
  products: createProductsAPI(client),
  productGroups: createProductGroupsAPI(client),
  productCodeMappings: createProductCodeMappingsAPI(client),
  containerCapacities: createContainerCapacitiesAPI(client),
  equipments: createEquipmentsAPI(client),
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
  mobileDevices: createMobileDevicesAPI(client),
  smtpConfigs: createSmtpConfigsAPI(client),
  purchasePlanLockSetting: createPurchasePlanLockSettingAPI(client),
  productionPlanLockSetting: createProductionPlanLockSettingAPI(client),
  productionRecordSettings: createProductionRecordSettingsAPI(client),
  scheduleConfig: createScheduleConfigAPI(client),
  lineBacklogAdjustments: createLineBacklogAdjustmentsAPI(client),
  notifications: createNotificationsAPI(client),
  productionPlanChangeLogs: createProductionPlanChangeLogsAPI(client),
  laserPatterns: createLaserPatternsAPI(client),
  laserActuals: createLaserActualsAPI(client),
  laserShiftRecords: createLaserShiftRecordsAPI(client),
  engineeringChanges: createEngineeringChangesAPI(client),
  purchaseActuals: createPurchaseActualsAPI(client),
  fujishojiDocument: createFujishojiDocumentAPI(client),
  supplierOrderPatterns: createSupplierOrderPatternsAPI(client),
  supplierOrderSchedules: createSupplierOrderSchedulesAPI(client),
  purchaseOrderProposals: createPurchaseOrderProposalsAPI(client),
  purchaseOrderApprovalConfig: createPurchaseOrderApprovalConfigAPI(client),
  qualityEquipmentInspections: createQualityEquipmentInspectionsAPI(client),
  productChecksheets: createProductChecksheetsAPI(client),
  integratedChecksheets: createIntegratedChecksheetsAPI(client),
  overtime: createOvertimeAPI(client),
  brakeLineActuals: createBrakeLineActualsAPI(client),
  spotLineActuals: createSpotLineActualsAPI(client),
  systemSettings: createSystemSettingsAPI(client),
  ganttDisplayProductMaps: createGanttDisplayProductMapsAPI(client),
  lineProductDisplayOrders: createLineProductDisplayOrdersAPI(client),
  planDeviationReport: createPlanDeviationReportAPI(client),
  recordConfirmations: createRecordConfirmationAPI(client),
  kubotaSakaiTrucks: createKubotaSakaiTrucksAPI(client),
  kubotaSakaiDueAdjustments: createKubotaSakaiDueAdjustmentsAPI(client),
  kubotaSakaiTripAssignments: createKubotaSakaiTripAssignmentsAPI(client),
  shippingTrips: createShippingTripsAPI(client),
  shipToLeadTimes: createShipToLeadTimesAPI(client),
  cameraActuals: createCameraActualsAPI(client),
  outsource: createOutsourceAPI(client),
  client,
}
