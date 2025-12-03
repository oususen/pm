import axios from 'axios'

const API_BASE_URL = 'http://localhost:8002/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default {
  // Products
  getProducts() {
    return client.get('/products/')
  },
  getProduct(id) {
    return client.get(`/products/${id}/`)
  },
  createProduct(data) {
    return client.post('/products/', data)
  },
  updateProduct(id, data) {
    return client.put(`/products/${id}/`, data)
  },
  deleteProduct(id) {
    return client.delete(`/products/${id}/`)
  },

  // Customers
  getCustomers() {
    return client.get('/customers/')
  },
  getCustomer(id) {
    return client.get(`/customers/${id}/`)
  },
  createCustomer(data) {
    return client.post('/customers/', data)
  },
  updateCustomer(id, data) {
    return client.put(`/customers/${id}/`, data)
  },
  deleteCustomer(id) {
    return client.delete(`/customers/${id}/`)
  },

  // Processes
  getProcesses() {
    return client.get('/processes/')
  },
  getProcess(id) {
    return client.get(`/processes/${id}/`)
  },
  createProcess(data) {
    return client.post('/processes/', data)
  },
  updateProcess(id, data) {
    return client.put(`/processes/${id}/`, data)
  },
  deleteProcess(id) {
    return client.delete(`/processes/${id}/`)
  },

  // Lines
  getLines() {
    return client.get('/lines/')
  },
  getLine(id) {
    return client.get(`/lines/${id}/`)
  },
  createLine(data) {
    return client.post('/lines/', data)
  },
  updateLine(id, data) {
    return client.put(`/lines/${id}/`, data)
  },
  deleteLine(id) {
    return client.delete(`/lines/${id}/`)
  },

  // Suppliers
  getSuppliers() {
    return client.get('/suppliers/')
  },
  getSupplier(id) {
    return client.get(`/suppliers/${id}/`)
  },
  createSupplier(data) {
    return client.post('/suppliers/', data)
  },
  updateSupplier(id, data) {
    return client.put(`/suppliers/${id}/`, data)
  },
  deleteSupplier(id) {
    return client.delete(`/suppliers/${id}/`)
  },

  // Calendars
  getCalendars() {
    return client.get('/calendars/')
  },
  getCalendar(id) {
    return client.get(`/calendars/${id}/`)
  },
  createCalendar(data) {
    return client.post('/calendars/', data)
  },
  updateCalendar(id, data) {
    return client.put(`/calendars/${id}/`, data)
  },
  deleteCalendar(id) {
    return client.delete(`/calendars/${id}/`)
  },

  // Calendar Days
  getCalendarDays(calendarId) {
    return client.get(`/calendar-days/?calendar=${calendarId}`)
  },
  createCalendarDay(data) {
    return client.post('/calendar-days/', data)
  },
  updateCalendarDay(id, data) {
    return client.put(`/calendar-days/${id}/`, data)
  },
  deleteCalendarDay(id) {
    return client.delete(`/calendar-days/${id}/`)
  },

  // BOMs
  getBOMs() {
    return client.get('/boms/')
  },
  getBOM(id) {
    return client.get(`/boms/${id}/`)
  },
  createBOM(data) {
    return client.post('/boms/', data)
  },
  updateBOM(id, data) {
    return client.put(`/boms/${id}/`, data)
  },
  deleteBOM(id) {
    return client.delete(`/boms/${id}/`)
  },

  // BOM Items
  getBOMItems(bomId) {
    return client.get(`/bom-items/?bom=${bomId}`)
  },
  createBOMItem(data) {
    return client.post('/bom-items/', data)
  },
  updateBOMItem(id, data) {
    return client.put(`/bom-items/${id}/`, data)
  },
  deleteBOMItem(id) {
    return client.delete(`/bom-items/${id}/`)
  },

  // Routings
  getRoutings() {
    return client.get('/routings/')
  },
  getRouting(id) {
    return client.get(`/routings/${id}/`)
  },
  createRouting(data) {
    return client.post('/routings/', data)
  },
  updateRouting(id, data) {
    return client.put(`/routings/${id}/`, data)
  },
  deleteRouting(id) {
    return client.delete(`/routings/${id}/`)
  },

  // Routing Steps
  getRoutingSteps(routingId) {
    return client.get(`/routing-steps/?routing=${routingId}`)
  },
  createRoutingStep(data) {
    return client.post('/routing-steps/', data)
  },
  updateRoutingStep(id, data) {
    return client.put(`/routing-steps/${id}/`, data)
  },
  deleteRoutingStep(id) {
    return client.delete(`/routing-steps/${id}/`)
  },
}
