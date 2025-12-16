import axios from 'axios'
import { createProductsAPI } from './resources/products'
import { createCustomersAPI } from './resources/customers'
import { createProcessesAPI } from './resources/processes'
import { createLinesAPI } from './resources/lines'
import { createSuppliersAPI } from './resources/suppliers'
import { createCalendarsAPI } from './resources/calendars'
import { createBomsAPI } from './resources/boms'
import { createRoutingsAPI } from './resources/routings'
import { createOrdersAPI } from './resources/orders'
import { createStagingAPI } from './resources/staging'
import { createLineDemandsAPI } from './resources/lineDemands'
import { createLineBacklogsAPI } from './resources/lineBacklogs'
import { createLineRealtimeAPI } from './resources/lineRealtime'

// ベースURL決定: 環境変数があれば最優先。なければ現在のホスト:8000 → :8002 → localhost。
const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  `http://${host}:8002/api` ||
  `http://${host}:8000/api` ||
  'http://localhost:8002/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

const bomsAPI = createBomsAPI(client)

export default {
  products: createProductsAPI(client),
  customers: createCustomersAPI(client),
  lines: createLinesAPI(client),
  suppliers: createSuppliersAPI(client),
  calendars: createCalendarsAPI(client),
  boms: bomsAPI,
  bomItems: { getBOMItems: bomsAPI.getBOMItems }, // BOMItemsに直接アクセス
  routings: createRoutingsAPI(client),
  orders: createOrdersAPI(client),
  staging: createStagingAPI(client),
  processes: createProcessesAPI(client),
  lineDemands: createLineDemandsAPI(client),
  lineBacklogs: createLineBacklogsAPI(client),
  lineRealtime: createLineRealtimeAPI(client),
}
