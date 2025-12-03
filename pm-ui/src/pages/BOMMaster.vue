<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">構成マスタ（BOM）</h1>
      <div class="page-actions">
        <button @click="fetchBOMs" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>親製品</th>
            <th>版</th>
            <th>有効開始日</th>
            <th>有効終了日</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bom in boms" :key="bom.id">
            <td>{{ getProductName(bom.parent_product) }}</td>
            <td>{{ bom.version }}</td>
            <td>{{ bom.valid_from }}</td>
            <td>{{ bom.valid_to || '-' }}</td>
            <td>{{ bom.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="viewDetails(bom)" class="btn-sm">詳細</button>
              <button @click="editBOM(bom)" class="btn-sm">編集</button>
              <button @click="deleteBOM(bom.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="boms.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? 'BOM編集' : 'BOM新規作成' }}</h2>
        <form @submit.prevent="saveBOM">
          <div class="form-group">
            <label>親製品 *</label>
            <select v-model="formData.parent_product_id" required :disabled="isEdit">
              <option value="">選択してください</option>
              <option v-for="product in products" :key="product.id" :value="product.id">
                {{ product.product_code }} - {{ product.product_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>版 *</label>
            <input v-model="formData.version" required />
          </div>
          <div class="form-group">
            <label>有効開始日 *</label>
            <input type="date" v-model="formData.valid_from" required />
          </div>
          <div class="form-group">
            <label>有効終了日</label>
            <input type="date" v-model="formData.valid_to" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              有効
            </label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 詳細ダイアログ -->
    <div v-if="showDetailsDialog" class="modal-overlay" @click.self="closeDetailsDialog">
      <div class="modal-content modal-large">
        <h2>BOM詳細</h2>
        <div class="details-section">
          <p><strong>親製品:</strong> {{ getProductName(selectedBOM.parent_product) }}</p>
          <p><strong>版:</strong> {{ selectedBOM.version }}</p>
          <p><strong>有効期間:</strong> {{ selectedBOM.valid_from }} 〜 {{ selectedBOM.valid_to || '無期限' }}</p>
        </div>
        <h3>構成品目</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>子製品</th>
              <th>数量</th>
              <th>ロス率</th>
              <th>調達区分</th>
              <th>仕入先</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in bomItems" :key="item.id">
              <td>{{ getProductName(item.child_product) }}</td>
              <td>{{ item.quantity }}</td>
              <td>{{ item.loss_rate || '-' }}</td>
              <td>{{ getSourcingTypeLabel(item.sourcing_type) }}</td>
              <td>{{ getSupplierName(item.supplier) }}</td>
            </tr>
          </tbody>
        </table>
        <div class="form-actions">
          <button type="button" @click="closeDetailsDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const boms = ref([])
const products = ref([])
const suppliers = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  parent_product_id: '',
  version: 'v1',
  valid_from: '',
  valid_to: '',
  is_active: true
})

const showDetailsDialog = ref(false)
const selectedBOM = ref({})
const bomItems = ref([])

const sourcingTypeMap = {
  'MAKE': '自社製造',
  'BUY': '購買',
  'SUBCON': '外注'
}

const fetchBOMs = async () => {
  try {
    const response = await api.getBOMs()
    boms.value = response.data.results || response.data
  } catch (error) {
    console.error('BOM取得エラー:', error)
    alert('BOMデータの取得に失敗しました')
  }
}

const fetchProducts = async () => {
  try {
    const response = await api.getProducts()
    products.value = response.data.results || response.data
  } catch (error) {
    console.error('製品取得エラー:', error)
  }
}

const fetchSuppliers = async () => {
  try {
    const response = await api.getSuppliers()
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
  }
}

const getProductName = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return product ? `${product.product_code} - ${product.product_name}` : productId
}

const getSupplierName = (supplierId) => {
  if (!supplierId) return '-'
  const supplier = suppliers.value.find(s => s.id === supplierId)
  return supplier ? supplier.supplier_name : supplierId
}

const getSourcingTypeLabel = (value) => sourcingTypeMap[value] || value

const showNewDialog = () => {
  isEdit.value = false
  const today = new Date().toISOString().split('T')[0]
  formData.value = {
    parent_product_id: '',
    version: 'v1',
    valid_from: today,
    valid_to: '',
    is_active: true
  }
  showDialog.value = true
}

const editBOM = (bom) => {
  isEdit.value = true
  formData.value = {
    ...bom,
    parent_product_id: bom.parent_product
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveBOM = async () => {
  try {
    // データの前処理
    const dataToSend = {
      ...formData.value,
      valid_to: formData.value.valid_to || null
    }

    if (isEdit.value) {
      await api.updateBOM(dataToSend.id, dataToSend)
      alert('更新しました')
    } else {
      await api.createBOM(dataToSend)
      alert('作成しました')
    }
    await fetchBOMs()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    console.error('エラー詳細:', error.response?.data)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || '保存に失敗しました'
    alert('保存に失敗しました\n\n' + errorMessage)
  }
}

const deleteBOM = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.deleteBOM(id)
    await fetchBOMs()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

const viewDetails = async (bom) => {
  selectedBOM.value = bom
  try {
    const response = await api.getBOMItems(bom.id)
    bomItems.value = response.data.results || response.data
    showDetailsDialog.value = true
  } catch (error) {
    console.error('BOM明細取得エラー:', error)
    alert('BOM明細の取得に失敗しました')
  }
}

const closeDetailsDialog = () => {
  showDetailsDialog.value = false
}

onMounted(() => {
  fetchBOMs()
  fetchProducts()
  fetchSuppliers()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-large {
  min-width: 800px;
  max-width: 900px;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.modal-content h3 {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  color: #555;
}

.details-section {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.details-section p {
  margin: 0.5rem 0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input[type="text"],
.form-group input[type="date"],
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: white;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}
</style>
