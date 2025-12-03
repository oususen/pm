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

const API_BASE_URL = 'http://localhost:8002/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default {
  products: createProductsAPI(client),
  customers: createCustomersAPI(client),
  processes: createProcessesAPI(client),
  lines: createLinesAPI(client),
  suppliers: createSuppliersAPI(client),
  calendars: createCalendarsAPI(client),
  boms: createBomsAPI(client),
  routings: createRoutingsAPI(client),
  orders: createOrdersAPI(client),
  staging: createStagingAPI(client),
}

