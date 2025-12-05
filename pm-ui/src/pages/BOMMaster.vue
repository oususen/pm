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
            <select v-model="formData.parent_product" required :disabled="isEdit">
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
          <p v-if="isPhantom(selectedBOM.parent_product)" class="phantom-info">
            この親製品は見なし組立です。リードタイム計算や展開ロジックの扱いに注意してください。
          </p>
        </div>
        <h3>構成品目</h3>
        <div class="item-form">
          <div class="form-row">
            <div class="form-group">
              <label>子製品 *</label>
              <select v-model="itemForm.child_product" required>
                <option value="">選択してください</option>
                <option v-for="product in products" :key="product.id" :value="product.id">
                  {{ product.product_code }} - {{ product.product_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>数量 *</label>
              <input type="number" step="0.001" min="0" v-model="itemForm.quantity" required />
            </div>
            <div class="form-group">
              <label>ロス率</label>
              <input type="number" step="0.001" min="0" v-model="itemForm.loss_rate" />
            </div>
            <div class="form-group">
              <label>調達区分</label>
              <select v-model="itemForm.sourcing_type">
                <option v-for="option in sourcingTypeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>仕入先</label>
              <select v-model="itemForm.supplier">
                <option value="">選択しない</option>
                <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                  {{ supplier.supplier_name }}
                </option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group full-width">
              <label>備考</label>
              <input type="text" v-model="itemForm.remark" />
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn-primary" @click="saveBOMItem">
              {{ editingItemId ? '明細を更新' : '明細を追加' }}
            </button>
            <button type="button" class="btn-secondary" @click="resetItemForm" :disabled="!editingItemId">
              キャンセル
            </button>
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>子製品</th>
              <th>数量</th>
              <th>ロス率</th>
              <th>調達区分</th>
              <th>仕入先</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in bomItems" :key="item.id">
              <td>{{ getProductName(item.child_product) }}</td>
              <td>{{ item.quantity }}</td>
              <td>{{ item.loss_rate || '-' }}</td>
              <td>{{ getSourcingTypeLabel(item.sourcing_type) }}</td>
              <td>{{ getSupplierName(item.supplier) }}</td>
              <td>
                <button class="btn-sm" @click="startEditItem(item)">編集</button>
                <button class="btn-sm btn-danger" @click="deleteBOMItem(item.id)">削除</button>
              </td>
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
  parent_product: '',
  version: 'v1',
  valid_from: '',
  valid_to: '',
  is_active: true
})

const showDetailsDialog = ref(false)
const selectedBOM = ref({})
const bomItems = ref([])
const itemForm = ref({
  child_product: '',
  quantity: '1.000',
  loss_rate: '',
  sourcing_type: 'MAKE',
  supplier: '',
  remark: ''
})
const editingItemId = ref(null)

const sourcingTypeMap = {
  'MAKE': '自社製造',
  'BUY': '購買',
  'SUBCON': '外注'
}
const sourcingTypeOptions = [
  { value: 'MAKE', label: '自社製造' },
  { value: 'BUY', label: '購買' },
  { value: 'SUBCON', label: '外注' }
]

const fetchBOMs = async () => {
  try {
    const response = await api.boms.getBOMs()
    boms.value = response.data.results || response.data
  } catch (error) {
    console.error('BOM取得エラー:', error)
    alert('BOMデータの取得に失敗しました')
  }
}

const fetchProducts = async () => {
  try {
    // 全ページ取得（現状フィルタなし）
    products.value = await api.products.getAllProducts()
  } catch (error) {
    console.error('製品取得エラー:', error)
  }
}

const fetchSuppliers = async () => {
  try {
    const response = await api.suppliers.getSuppliers()
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
  }
}

const resetItemForm = () => {
  itemForm.value = {
    child_product: '',
    quantity: '1.000',
    loss_rate: '',
    sourcing_type: 'MAKE',
    supplier: '',
    remark: ''
  }
  editingItemId.value = null
}

const fetchBOMItems = async (bomId) => {
  const response = await api.boms.getBOMItems(bomId)
  bomItems.value = response.data.results || response.data
}

const getProductName = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return product ? `${product.product_code} - ${product.product_name}` : productId
}

const isPhantom = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return Boolean(product?.is_phantom)
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
    parent_product: '',
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
    parent_product: bom.parent_product
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveBOM = async () => {
  try {
    const dataToSend = {
      parent_product: formData.value.parent_product,
      version: formData.value.version,
      valid_from: formData.value.valid_from,
      valid_to: formData.value.valid_to || null,
      is_active: formData.value.is_active
    }

    if (isEdit.value) {
      await api.boms.updateBOM(formData.value.id, dataToSend)
      alert('更新しました')
    } else {
      await api.boms.createBOM(dataToSend)
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
    await api.boms.deleteBOM(id)
    await fetchBOMs()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

const viewDetails = async (bom) => {
  selectedBOM.value = bom
  resetItemForm()
  try {
    await fetchBOMItems(bom.id)
    showDetailsDialog.value = true
  } catch (error) {
    console.error('BOM明細取得エラー:', error)
    alert('BOM明細の取得に失敗しました')
  }
}

const closeDetailsDialog = () => {
  showDetailsDialog.value = false
}

const startEditItem = (item) => {
  editingItemId.value = item.id
  itemForm.value = {
    child_product: item.child_product,
    quantity: item.quantity,
    loss_rate: item.loss_rate ?? '',
    sourcing_type: item.sourcing_type,
    supplier: item.supplier ?? '',
    remark: item.remark ?? ''
  }
}

const saveBOMItem = async () => {
  if (!selectedBOM.value?.id) return
  if (!itemForm.value.child_product || !itemForm.value.quantity) {
    alert('子製品と数量は必須です')
    return
  }

  const payload = {
    bom: selectedBOM.value.id,
    child_product: itemForm.value.child_product,
    quantity: itemForm.value.quantity,
    loss_rate: itemForm.value.loss_rate === '' ? null : itemForm.value.loss_rate,
    sourcing_type: itemForm.value.sourcing_type,
    supplier: itemForm.value.supplier || null,
    remark: itemForm.value.remark || ''
  }

  try {
    if (editingItemId.value) {
      await api.boms.updateBOMItem(editingItemId.value, payload)
      alert('明細を更新しました')
    } else {
      await api.boms.createBOMItem(payload)
      alert('明細を追加しました')
    }
    await fetchBOMItems(selectedBOM.value.id)
    resetItemForm()
  } catch (error) {
    console.error('明細保存エラー:', error)
    console.error('エラー詳細:', error.response?.data)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || '明細の保存に失敗しました'
    alert('明細の保存に失敗しました\n\n' + errorMessage)
  }
}

const deleteBOMItem = async (id) => {
  if (!confirm('この明細を削除しますか？')) return
  try {
    await api.boms.deleteBOMItem(id)
    await fetchBOMItems(selectedBOM.value.id)
  } catch (error) {
    console.error('明細削除エラー:', error)
    alert('明細の削除に失敗しました')
  }
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

.phantom-info {
  margin-top: 0.5rem;
  color: #b15e00;
  font-size: 0.9rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.form-group.full-width {
  grid-column: 1 / -1;
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
