import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

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

  // Processes
  getProcesses() {
    return client.get('/processes/')
  },

  // Lines
  getLines() {
    return client.get('/lines/')
  },

  // Suppliers
  getSuppliers() {
    return client.get('/suppliers/')
  },

  // Calendars
  getCalendars() {
    return client.get('/calendars/')
  },

  // BOMs
  getBOMs() {
    return client.get('/boms/')
  },

  // Routings
  getRoutings() {
    return client.get('/routings/')
  },
}
