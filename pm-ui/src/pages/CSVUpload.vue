<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">CSV Upload</h1>
    </div>

    <div class="page-content">
      <div class="upload-form">
        <div class="form-group">
          <label for="customer_code">Customer Code *</label>
          <select v-model="formData.customer_code" id="customer_code" required>
            <option value="">Select Customer</option>
            <option v-for="customer in customers" :key="customer.id" :value="customer.customer_code">
              {{ customer.customer_code }} - {{ customer.customer_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label for="order_type">Order Type *</label>
          <select v-model="formData.order_type" id="order_type" required>
            <option value="FIRM">FIRM</option>
            <option value="FORECAST">FORECAST</option>
          </select>
        </div>

        <div class="form-group">
          <label for="source_system">Source System</label>
          <input v-model="formData.source_system" type="text" id="source_system" placeholder="CSV" />
        </div>

        <div class="form-group">
          <label for="file">CSV File *</label>
          <input type="file" id="file" @change="onFileChange" accept=".csv" required />
          <div v-if="selectedFile" class="file-info">
            Selected: {{ selectedFile.name }}
          </div>
        </div>

        <div class="form-actions">
          <button @click="uploadCSV" :disabled="uploading" class="btn-primary">
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </div>

        <div v-if="result" class="result-section">
          <h3>{{ result.success ? 'Success' : 'Error' }}</h3>
          <p>{{ result.message }}</p>
          <div v-if="result.errors && result.errors.length > 0" class="errors">
            <h4>Errors:</h4>
            <ul>
              <li v-for="(error, index) in result.errors" :key="index">{{ error }}</li>
            </ul>
          </div>
          <div v-if="result.warnings && result.warnings.length > 0" class="warnings">
            <h4>Warnings:</h4>
            <ul>
              <li v-for="(warning, index) in result.warnings" :key="index">{{ warning }}</li>
            </ul>
          </div>
          <div v-if="result.success" class="create-orders-section">
            <button @click="createOrders" :disabled="creatingOrders" class="btn-success">
              {{ creatingOrders ? 'Creating...' : 'Create Orders from Staging' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'
import axios from 'axios'

const customers = ref([])
const selectedFile = ref(null)
const uploading = ref(false)
const creatingOrders = ref(false)
const result = ref(null)

const formData = ref({
  customer_code: '',
  order_type: 'FIRM',
  source_system: 'CSV'
})

const fetchCustomers = async () => {
  try {
    const response = await api.customers.getCustomers()
    customers.value = response.data.results || response.data
  } catch (error) {
    console.error('Error fetching customers:', error)
    alert('Failed to fetch customers')
  }
}

const onFileChange = (event) => {
  selectedFile.value = event.target.files[0]
}

const uploadCSV = async () => {
  if (!formData.value.customer_code) {
    alert('Please select a customer')
    return
  }

  if (!selectedFile.value) {
    alert('Please select a CSV file')
    return
  }

  uploading.value = true
  result.value = null

  try {
    const formDataToSend = new FormData()
    formDataToSend.append('file', selectedFile.value)
    formDataToSend.append('customer_code', formData.value.customer_code)
    formDataToSend.append('order_type', formData.value.order_type)
    formDataToSend.append('source_system', formData.value.source_system)

    const response = await axios.post(
      'http://localhost:8002/api/stg-order-raw/upload_csv/',
      formDataToSend,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )

    result.value = response.data
  } catch (error) {
    console.error('Upload error:', error)
    result.value = {
      success: false,
      message: error.response?.data?.error || error.message || 'Upload failed',
      errors: [error.response?.data?.error || error.message]
    }
  } finally {
    uploading.value = false
  }
}

const createOrders = async () => {
  creatingOrders.value = true

  try {
    const response = await axios.post('http://localhost:8002/api/stg-order-raw/create_orders/')
    alert(`Created ${response.data.orders} orders with ${response.data.lines} lines`)
    result.value = null
    selectedFile.value = null
    document.getElementById('file').value = ''
  } catch (error) {
    console.error('Create orders error:', error)
    alert('Failed to create orders: ' + (error.response?.data?.error || error.message))
  } finally {
    creatingOrders.value = false
  }
}

onMounted(() => {
  fetchCustomers()
})
</script>

<style scoped>
.upload-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input[type="text"],
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type="file"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.file-info {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #f0f0f0;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #666;
}

.form-actions {
  margin-top: 2rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.result-section {
  margin-top: 2rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #f9f9f9;
}

.result-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.errors {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
}

.warnings {
  margin-top: 1rem;
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffeeba;
  border-radius: 4px;
}

.create-orders-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #ddd;
}

.btn-success {
  padding: 0.5rem 1rem;
  border: none;
  background-color: #28a745;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-success:hover {
  background-color: #218838;
}

.btn-success:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style>
