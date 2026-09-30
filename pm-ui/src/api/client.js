import axios from 'axios'
import { createProductsAPI } from './resources/products'
import { createCustomersAPI } from './resources/customers'
import { createShipmentActualsAPI } from './resources/shipmentActuals'
import { createShippingTraceAPI } from './resources/shippingTrace'
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
import { createConsumablesAPI } from './resources/consumables'
import { createSmtpConfigsAPI } from './resources/smtpConfigs'
import { createPurchasePlanLockSettingAPI } from './resources/purchasePlanLockSetting'
import { createProductionPlanLineSettingsAPI } from './resources/productionPlanLineSettings'
import { createDailyProcessTargetsAPI } from './resources/dailyProcessTargets'
import { createProductionPlanLockSettingAPI } from './resources/productionPlanLockSetting'
import { createProductionRecordSettingsAPI } from './resources/productionRecordSettings'
import { createScheduleConfigAPI } from './resources/scheduleConfig'
import { createLineBacklogAdjustmentsAPI } from './resources/lineBacklogAdjustments'
import { createNotificationsAPI } from './resources/notifications'
import { createProductionPlanChangeLogsAPI } from './resources/productionPlanChangeLogs'
import { createLaserPatternsAPI } from './resources/laserPatterns'
import { createLaserProcessingFreqPatternsAPI } from './resources/laserProcessingFreqPatterns'
import { createLaserActualsAPI } from './resources/laserActuals'
import { createLaserShiftRecordsAPI } from './resources/laserShiftRecords'
import { createLaserWeeklyPlansAPI } from './resources/laserWeeklyPlans'
import { createDiscontinuationsAPI } from './resources/discontinuations'
import { createEngineeringChangesAPI } from './resources/engineeringChanges'
import { createPurchaseActualsAPI } from './resources/purchaseActuals'
import { createFujishojiDocumentAPI } from './resources/fujishojiDocument'
import { createSupplierOrderPatternsAPI } from './resources/supplierOrderPatterns'
import { createSupplierOrderSchedulesAPI } from './resources/supplierOrderSchedules'
import { createPurchaseOrderProposalsAPI } from './resources/purchaseOrderProposals'
import { createQualityEquipmentInspectionsAPI } from './resources/qualityEquipmentInspections'
import { createIntegratedChecksheetsAPI } from './resources/integratedChecksheets'
import { createOvertimeAPI } from './resources/overtime'
import { createBrakeLineActualsAPI } from './resources/brakeLineActuals'
import { createSpotLineActualsAPI } from './resources/spotLineActuals'
import { createManualDocumentsAPI } from './resources/manualDocuments'
import { createSystemSettingsAPI } from './resources/systemSettings'
import { createGanttDisplayProductMapsAPI } from './resources/ganttDisplayProductMaps'
import { createLineProductDisplayOrdersAPI } from './resources/lineProductDisplayOrders'
import { createPlanDeviationReportAPI, createRecordConfirmationAPI, createPlanDeviationLineConfigAPI } from './resources/planDeviationReport'
import { createKubotaSakaiTrucksAPI } from './resources/kubotaSakaiTrucks'
import { createSupplierTrucksAPI } from './resources/supplierTrucks'
import { createKubotaSakaiDueAdjustmentsAPI } from './resources/kubotaSakaiDueAdjustments'
import { createKubotaSakaiTripAssignmentsAPI } from './resources/kubotaSakaiTripAssignments'
import { createShippingTripsAPI } from './resources/shippingTrips'
import { createShippingProgressAPI } from './resources/shippingProgress'
import { createShippingProgressHorizonSettingAPI } from './resources/shippingProgressHorizonSetting'
import { createShipToLeadTimesAPI } from './resources/shipToLeadTimes'
import { createCameraActualsAPI } from './resources/cameraActuals'
import { createOutsourceAPI } from './resources/outsource'
import { createAutoPlanAggregateSettingsAPI } from './resources/autoPlanAggregateSettings'
import { createPurchaseAutoDeliveryListAPI } from './resources/purchaseAutoDeliveryList'
import { createPurchaseAutoOrderSendAPI } from './resources/purchaseAutoOrderSend'
import { createStocktakeRecordsAPI } from './resources/stocktakeRecords'
import { createPurchaseActualKikanMappingAPI } from './resources/purchaseActualKikanMapping'
import { createMorningMeetingsAPI } from './resources/morningMeetings'
import { createOrphanBacklogAPI } from './resources/orphanBacklog'
import { createLineCycleTimesAPI } from './resources/lineCycleTimes'
import { createLineLoadAPI } from './resources/lineLoad'
import { createTrainingCertificationAPI } from './resources/trainingCertification'
import { createActualCycleTimesAPI } from './resources/actualCycleTimes'
import { createProgressPdfCompareAPI } from './resources/progressPdfCompare'
import { createSourcingBulkChangeAPI } from './resources/sourcingBulkChange'
import { createProductionLockAPI } from './resources/productionLock'
import { createShiftsAPI } from './resources/shifts'

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
  shippingTrace: createShippingTraceAPI(client),
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
  consumables: createConsumablesAPI(client),
  smtpConfigs: createSmtpConfigsAPI(client),
  purchasePlanLockSetting: createPurchasePlanLockSettingAPI(client),
  productionPlanLineSettings: createProductionPlanLineSettingsAPI(client),
  dailyProcessTargets: createDailyProcessTargetsAPI(client),
  productionPlanLockSetting: createProductionPlanLockSettingAPI(client),
  productionRecordSettings: createProductionRecordSettingsAPI(client),
  aiChat: {
    chat(payload) { return client.post('/ai/chat/', payload || {}) },
    status(params) { return client.get('/ai/chat/', { params }) },
  },
  aiConversations: {
    list(params) { return client.get('/ai/conversations/', { params }) },
    get(id) { return client.get(`/ai/conversations/${id}/`) },
    create(data) { return client.post('/ai/conversations/', data) },
    update(id, data) { return client.patch(`/ai/conversations/${id}/`, data) },
    delete(id) { return client.delete(`/ai/conversations/${id}/`) },
  },
  aiSearchConfigs: {
    list() { return client.get('/ai-search-configs/') },
    create(data) { return client.post('/ai-search-configs/', data) },
    update(id, data) { return client.put(`/ai-search-configs/${id}/`, data) },
    delete(id) { return client.delete(`/ai-search-configs/${id}/`) },
    models() { return client.get('/ai-search-config-models/') },
  },
  aiSettings: {
    providers() { return client.get('/ai/settings/providers/') },
    updateProvider(id, data) { return client.patch(`/ai/settings/providers/${id}/`, data) },
    tools() { return client.get('/ai/settings/tools/') },
    updateTool(id, data) { return client.patch(`/ai/settings/tools/${id}/`, data) },
    dataPolicy() { return client.get('/ai/settings/data-policy/') },
    updateDataPolicy(data) { return client.put('/ai/settings/data-policy/', data) },
    sqlDictionary() { return client.get('/ai/settings/sql-dictionary/') },
    knowledgeSources() { return client.get('/ai/settings/knowledge-sources/') },
    updateKnowledgeSource(id, data) { return client.patch(`/ai/settings/knowledge-sources/${id}/`, data) },
    knowledgeDocuments() { return client.get('/ai/settings/knowledge-documents/') },
    createKnowledgeDocument(data) { return client.post('/ai/settings/knowledge-documents/', data) },
    updateKnowledgeDocument(id, data) { return client.patch(`/ai/settings/knowledge-documents/${id}/`, data) },
    deleteKnowledgeDocument(id) { return client.delete(`/ai/settings/knowledge-documents/${id}/`) },
  },
  ocr: {
    status() { return client.get('/ocr/status/') },
    recognize(data) { return client.post('/ocr/recognize/', data) },
  },
  scheduleConfig: createScheduleConfigAPI(client),
  lineBacklogAdjustments: createLineBacklogAdjustmentsAPI(client),
  notifications: createNotificationsAPI(client),
  productionPlanChangeLogs: createProductionPlanChangeLogsAPI(client),
  laserPatterns: createLaserPatternsAPI(client),
  laserProcessingFreqPatterns: createLaserProcessingFreqPatternsAPI(client),
  laserActuals: createLaserActualsAPI(client),
  laserShiftRecords: createLaserShiftRecordsAPI(client),
  laserWeeklyPlans: createLaserWeeklyPlansAPI(client),
  discontinuations: createDiscontinuationsAPI(client),
  engineeringChanges: createEngineeringChangesAPI(client),
  purchaseActuals: createPurchaseActualsAPI(client),
  fujishojiDocument: createFujishojiDocumentAPI(client),
  supplierOrderPatterns: createSupplierOrderPatternsAPI(client),
  supplierOrderSchedules: createSupplierOrderSchedulesAPI(client),
  purchaseOrderProposals: createPurchaseOrderProposalsAPI(client),
  qualityEquipmentInspections: createQualityEquipmentInspectionsAPI(client),
  integratedChecksheets: createIntegratedChecksheetsAPI(client),
  overtime: createOvertimeAPI(client),
  brakeLineActuals: createBrakeLineActualsAPI(client),
  spotLineActuals: createSpotLineActualsAPI(client),
  manualDocuments: createManualDocumentsAPI(client),
  systemSettings: createSystemSettingsAPI(client),
  ganttDisplayProductMaps: createGanttDisplayProductMapsAPI(client),
  lineProductDisplayOrders: createLineProductDisplayOrdersAPI(client),
  planDeviationReport: createPlanDeviationReportAPI(client),
  planDeviationLineConfig: createPlanDeviationLineConfigAPI(client),
  recordConfirmations: createRecordConfirmationAPI(client),
  kubotaSakaiTrucks: createKubotaSakaiTrucksAPI(client),
  supplierTrucks: createSupplierTrucksAPI(client),
  kubotaSakaiDueAdjustments: createKubotaSakaiDueAdjustmentsAPI(client),
  kubotaSakaiTripAssignments: createKubotaSakaiTripAssignmentsAPI(client),
  shippingTrips: createShippingTripsAPI(client),
  shippingProgress: createShippingProgressAPI(client),
  shippingProgressHorizonSetting: createShippingProgressHorizonSettingAPI(client),
  shipToLeadTimes: createShipToLeadTimesAPI(client),
  cameraActuals: createCameraActualsAPI(client),
  outsource: createOutsourceAPI(client),
  autoPlanAggregateSettings: createAutoPlanAggregateSettingsAPI(client),
  purchaseAutoDeliveryList: createPurchaseAutoDeliveryListAPI(client),
  purchaseAutoOrderSend: createPurchaseAutoOrderSendAPI(client),
  stocktakeRecords: createStocktakeRecordsAPI(client),
  purchaseActualKikanMapping: createPurchaseActualKikanMappingAPI(client),
  morningMeetings: createMorningMeetingsAPI(client),
  orphanBacklog: createOrphanBacklogAPI(client),
  lineCycleTimes: createLineCycleTimesAPI(client),
  lineLoad: createLineLoadAPI(client),
  trainingCertification: createTrainingCertificationAPI(client),
  actualCycleTimes: createActualCycleTimesAPI(client),
  progressPdfCompare: createProgressPdfCompareAPI(client),
  sourcingBulkChange: createSourcingBulkChangeAPI(client),
  productionLock: createProductionLockAPI(client),
  shifts: createShiftsAPI(client),
  client,
}
