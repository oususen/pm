<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">CSV Upload</h1>
    </div>

    <div class="page-content">
      <div class="upload-form">
        <div class="form-group">
          <div class="group-header">
            <label>Customer *</label>
            <span class="hint">タイルをクリックして選択してください</span>
          </div>
          <div class="tile-grid customer-grid">
            <button
              v-for="customer in customers"
              :key="customer.id"
              type="button"
              class="select-tile"
              :class="{ active: formData.customer_code === customer.customer_code }"
              @click="selectCustomer(customer)"
            >
              <div class="icon-badge">{{ customer.customer_code?.slice(0, 2) || 'CU' }}</div>
              <div class="tile-main">{{ customer.customer_code }}</div>
              <div class="tile-sub" :title="customer.customer_name">{{ customer.customer_name }}</div>
            </button>
          </div>
        </div>

        <div class="form-group">
          <div class="group-header">
            <label>Order Type *</label>
            <span class="hint">用途に応じて選択</span>
          </div>
          <div class="tile-grid compact">
            <button
              v-for="type in orderTypes"
              :key="type.value"
              type="button"
              class="select-tile compact-tile"
              :class="{ active: formData.order_type === type.value }"
              @click="selectOrderType(type.value)"
            >
              <div class="tile-content-row">
                <div class="icon-badge">{{ type.badge }}</div>
                <div class="tile-main">{{ type.label }}</div>
                <div class="tile-sub">{{ type.desc }}</div>
              </div>
            </button>
          </div>
        </div>

        <!-- Factory selection for Kubota (customer code 000196) -->
        <div v-if="isKubotaCustomer" class="form-group">
          <div class="group-header">
            <label>Factory *</label>
            <span class="hint">工場を選択してください</span>
          </div>
          <div class="tile-grid compact">
            <button
              v-for="factory in factories"
              :key="factory.value"
              type="button"
              class="select-tile compact-tile"
              :class="{ active: formData.factory === factory.value }"
              @click="selectFactory(factory.value)"
            >
              <div class="tile-content-row">
                <div class="icon-badge">{{ factory.badge }}</div>
                <div class="tile-main">{{ factory.label }}</div>
                <div class="tile-sub">{{ factory.desc }}</div>
              </div>
            </button>
          </div>
        </div>

        <div v-if="showTieraT3Option" class="form-group">
          <div class="group-header">
            <label>ティエラ{{ formData.order_type === 'FIRM' ? '確定' : '内示' }}（T3）</label>
            <span class="hint">新データ（末尾 _T3）はこちら</span>
          </div>
          <label class="toggle-row">
            <input
              type="checkbox"
              v-model="formData.is_tiera_t3"
            />
            <span>T3{{ formData.order_type === 'FIRM' ? '確定' : '内示' }}CSVとして取り込む</span>
          </label>
        </div>

        <div class="form-group">
          <label for="source_system">Source System</label>
          <input v-model="formData.source_system" type="text" id="source_system" placeholder="CSV" />
        </div>

        <div class="form-group">
          <label for="file">CSV File *</label>
          <input type="file" id="file" @change="onFileChange" accept=".csv" required />
          <div v-if="selectedFile" class="file-info">
            選択済み: {{ selectedFile.name }}
          </div>
          <div v-if="fileWarning" class="file-warning">
            ⚠️ {{ fileWarning }}
          </div>
        </div>

        <div class="form-actions">
          <button @click="uploadCSV" :disabled="uploading || isDuplicateFile" class="btn-primary">
            {{ uploading ? 'アップロード中...' : 'アップロード' }}
          </button>
        </div>

        <div v-if="result" class="result-section">
          <h3>{{ result.success ? '成功' : 'エラー' }}</h3>
          <p>{{ result.message }}</p>

          <!-- Display order creation results if available -->
          <div v-if="result.success && result.orders_created !== undefined" class="success-details">
            <h4>受注作成結果:</h4>
            <ul>
              <li>受注数: {{ result.orders_created }}件</li>
              <li>明細数: {{ result.lines_created }}件</li>
              <li v-if="result.superseded_forecast_orders > 0">上書きされた内示受注: {{ result.superseded_forecast_orders }}件</li>
            </ul>
          </div>

          <div
            v-if="result.additional_order_notices && result.additional_order_notices.length > 0"
            class="additional-order-notice"
          >
            <h4>お知らせ:</h4>
            <p>追加注文がありました。部番と数量を確認してください。</p>
            <div
              v-for="(notice, noticeIndex) in result.additional_order_notices"
              :key="`${notice.order_no || 'additional'}-${noticeIndex}`"
              class="additional-order-block"
            >
              <p class="additional-order-title">受注番号: {{ notice.order_no || '—' }}</p>
              <ul>
                <li v-for="(item, itemIndex) in (notice.items || [])" :key="`${item.product_code || 'product'}-${itemIndex}`">
                  部番 {{ item.product_code || '—' }} / 数量 {{ formatNumber(item.quantity) }}
                </li>
              </ul>
            </div>
          </div>

          <div v-if="result.order_creation_error" class="warnings">
            <h4>注意:</h4>
            <p>CSVはステージングに取り込まれましたが、受注作成時にエラーが発生しました。</p>
            <p>{{ result.order_creation_error }}</p>
          </div>

          <!-- 確定vs内示 比較 (クボタ堺確定取り込み時) -->
          <div v-if="result.forecast_diffs && result.forecast_diffs.length > 0" class="forecast-diff">
            <h4>確定・内示 数量比較 ({{ result.forecast_diffs.length }}件)</h4>
            <table class="diff-table">
              <thead>
                <tr>
                  <th>製品コード</th>
                  <th>納期</th>
                  <th>確定数</th>
                  <th>内示数</th>
                  <th>差分</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(d, index) in result.forecast_diffs"
                  :key="index"
                  :class="d.diff !== 0 ? (d.diff > 0 ? 'diff-up' : 'diff-down') : ''"
                >
                  <td>{{ d.product_code }}</td>
                  <td>{{ d.due_date }}</td>
                  <td class="num">{{ d.firm_qty.toLocaleString() }}</td>
                  <td class="num">{{ d.forecast_qty.toLocaleString() }}</td>
                  <td class="num diff-cell">{{ d.diff > 0 ? '+' : '' }}{{ d.diff.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="result.errors && result.errors.length > 0" class="errors">
            <h4>エラー:</h4>
            <ul>
              <li v-for="(error, index) in result.errors" :key="index">{{ error }}</li>
            </ul>
          </div>
          <div v-if="result.warnings && result.warnings.length > 0" class="warnings">
            <h4>警告:</h4>
            <ul>
              <li v-for="(warning, index) in result.warnings" :key="index">{{ warning }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const customers = ref([])
const selectedFile = ref(null)
const uploading = ref(false)
const result = ref(null)
const fileWarning = ref(null)
const isDuplicateFile = ref(false)
const orderTypes = [
  { value: 'FIRM', label: 'ＦＩＲＭ', desc: '確定受注', badge: 'Ｆ' },
  { value: 'FORECAST', label: 'FORECAST', desc: '内示/予測', badge: 'Fc' },
]
const factories = [
  { value: 'SAKAI', label: '堺工場', desc: 'Sakai', badge: '堺' },
  { value: 'HIRAKATA', label: '枚方工場', desc: 'Hirakata', badge: '枚' },
  { value: 'KMT', label: 'KMT工場', desc: 'KMT', badge: 'K' },
]

const formData = ref({
  customer_code: '',
  order_type: 'FIRM',
  source_system: 'CSV',
  factory: 'SAKAI',  // Default to Sakai for Kubota
  is_tiera_t3: false
})

// Check if selected customer is Kubota (000196)
const isKubotaCustomer = computed(() => {
  return formData.value.customer_code === '000196'
})

const isTieraCustomer = computed(() => {
  return formData.value.customer_code === '000001'
})

const showTieraT3Option = computed(() => {
  return isTieraCustomer.value
})

const fetchCustomers = async () => {
  try {
    const response = await api.customers.getCustomers()
    customers.value = response.data.results || response.data
  } catch (error) {
    console.error('Error fetching customers:', error)
    alert('得意先の取得に失敗しました')
  }
}

const onFileChange = async (event) => {
  const file = event.target.files[0]
  if (!file) {
    selectedFile.value = null
    fileWarning.value = null
    isDuplicateFile.value = false
    return
  }

  selectedFile.value = file

  // Check if filename already exists
  try {
    const response = await axios.get(
      `${API_BASE_URL}/stg-order-raw/check_filename/?filename=${encodeURIComponent(file.name)}`
    )

    if (response.data.exists) {
      fileWarning.value = response.data.message
      isDuplicateFile.value = true
    } else {
      fileWarning.value = null
      isDuplicateFile.value = false
    }
  } catch (error) {
    console.error('Error checking filename:', error)
    fileWarning.value = null
    isDuplicateFile.value = false
  }
}

const selectCustomer = (customer) => {
  formData.value.customer_code = customer.customer_code
  // Reset factory when customer changes
  if (customer.customer_code === '000196') {
    formData.value.factory = 'SAKAI'
  } else {
    formData.value.factory = null
  }
  formData.value.is_tiera_t3 = false
}

const selectOrderType = (type) => {
  formData.value.order_type = type
  if (type !== 'FIRM') {
    formData.value.is_tiera_t3 = false
  }
}

const selectFactory = (factory) => {
  formData.value.factory = factory
}

const uploadCSV = async () => {
  if (!formData.value.customer_code) {
    alert('得意先を選択してください')
    return
  }

  if (isKubotaCustomer.value && !formData.value.factory) {
    alert('工場を選択してください')
    return
  }

  if (!selectedFile.value) {
    alert('CSVファイルを選択してください')
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
    formDataToSend.append('is_tiera_t3', formData.value.is_tiera_t3 ? '1' : '0')

    // Add factory parameter for Kubota customer
    if (isKubotaCustomer.value && formData.value.factory) {
      formDataToSend.append('factory', formData.value.factory)
    }

    const uploadPath = '/stg-order-raw/upload_csv/'

    const response = await axios.post(
      `${API_BASE_URL}${uploadPath}`,
      formDataToSend,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )

    result.value = response.data

    // If successful, reset the file input for next upload
    if (response.data.success) {
      selectedFile.value = null
      fileWarning.value = null
      isDuplicateFile.value = false
      document.getElementById('file').value = ''
    }
  } catch (error) {
    console.error('Upload error:', error)
    console.error('Error response data:', error.response?.data)
    result.value = {
      success: false,
      message: error.response?.data?.message || error.response?.data?.error || error.message || 'Upload failed',
      errors: error.response?.data?.errors || [error.response?.data?.error || error.message],
      warnings: error.response?.data?.warnings || []
    }
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  fetchCustomers()
})
</script>

<style scoped>
.upload-form {
  max-width: 800px;
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

.file-warning {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #fff3cd;
  border: 2px solid #ffc107;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #856404;
  font-weight: 600;
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

.success-details {
  margin-top: 1rem;
  padding: 1rem;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
}

.success-details h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #155724;
}

.success-details ul {
  margin: 0;
  padding-left: 1.5rem;
}

.success-details li {
  color: #155724;
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

.additional-order-notice {
  margin-top: 1rem;
  padding: 1rem;
  background: #d1ecf1;
  border: 1px solid #bee5eb;
  border-radius: 4px;
  color: #0c5460;
}

.additional-order-block {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: #eef9fb;
  border-radius: 4px;
}

.additional-order-title {
  margin: 0 0 0.5rem 0;
  font-weight: 600;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 8px;
}

.hint {
  font-size: 12px;
  color: #666;
}

.tile-grid {
  margin-top: 0.75rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.tile-grid.compact {
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.tile-content-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.compact-tile .icon-badge {
  margin-bottom: 0;
  flex-shrink: 0;
}

.compact-tile .tile-main {
  font-weight: 600;
  color: #222;
  white-space: nowrap;
}

.compact-tile .tile-sub {
  font-size: 12px;
  color: #555;
  white-space: nowrap;
}

.tile-grid.customer-grid {
  grid-auto-flow: column;
  grid-auto-columns: minmax(220px, 1fr);
  overflow-x: auto;
  padding-bottom: 4px;
}

.select-tile {
  width: 100%;
  text-align: left;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.1s;
}

.select-tile:hover {
  border-color: #8aa8ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.select-tile.active {
  border-color: #5677ff;
  box-shadow: 0 2px 10px rgba(86, 119, 255, 0.18);
}

.icon-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #eef2ff, #d6e0ff);
  color: #2c3e7a;
  font-weight: 700;
  margin-bottom: 6px;
}

.tile-main {
  font-weight: 600;
  color: #222;
}

.tile-sub {
  font-size: 12px;
  color: #555;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  color: #333;
}

.toggle-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
}

/* 確定・内示 比較テーブル */
.forecast-diff {
  margin-top: 1rem;
  padding: 1rem;
  background: #f0f4ff;
  border: 1px solid #b8c8ff;
  border-radius: 4px;
}

.forecast-diff h4 {
  margin: 0 0 0.75rem 0;
  color: #2c3e7a;
  font-size: 0.95rem;
}

.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

.diff-table th {
  background: #dde6ff;
  color: #2c3e7a;
  padding: 5px 10px;
  text-align: center;
  border: 1px solid #b8c8ff;
  white-space: nowrap;
}

.diff-table td {
  padding: 4px 10px;
  border: 1px solid #d0d8f0;
  text-align: left;
}

.diff-table td.num {
  text-align: right;
}

.diff-table tr.diff-up td.diff-cell {
  color: #c00;
  font-weight: 600;
}

.diff-table tr.diff-down td.diff-cell {
  color: #0066cc;
  font-weight: 600;
}

.diff-table tr.diff-up {
  background: #fff5f5;
}

.diff-table tr.diff-down {
  background: #f5f8ff;
}
</style>
