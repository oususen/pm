<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製品マスタ</h1>
      <div class="page-actions">
        <button @click="fetchProducts" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>品番/品名</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchProducts"
            placeholder="品番・品名で検索"
          />
        </div>
        <div class="filter-field">
          <label>カテゴリ</label>
          <select v-model="filters.category">
            <option value="">すべて</option>
            <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">
              {{ cat.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>有効</label>
          <select v-model="filters.is_active">
            <option value="">すべて</option>
            <option value="true">有効</option>
            <option value="false">無効</option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="fetchProducts" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>品番コード</th>
            <th>品名</th>
            <th>カテゴリ</th>
            <th>単位</th>
            <th>標準LT(日)</th>
            <th>みなし組立</th>
            <th>仮想セット</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in products" :key="product.id">
            <td>{{ product.product_code }}</td>
            <td>{{ product.product_name }}</td>
            <td>{{ getCategoryLabel(product.category) }}</td>
            <td>{{ product.unit }}</td>
            <td>{{ product.standard_lt_days }}</td>
            <td>{{ product.is_phantom ? 'はい' : 'いいえ' }}</td>
            <td>{{ product.is_virtual_set ? 'はい' : 'いいえ' }}</td>
            <td>{{ product.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="editProduct(product)" class="btn-sm">編集</button>
              <button @click="deleteProduct(product.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="products.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '製品編集' : '製品新規作成' }}</h2>
        <form @submit.prevent="saveProduct">
          <div class="form-group">
            <label>品番コード *</label>
            <input v-model="formData.product_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>品名 *</label>
            <input v-model="formData.product_name" required />
          </div>
          <div class="form-group">
            <label>カテゴリ *</label>
            <select v-model="formData.category" required>
              <option value="">選択してください</option>
              <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">
                {{ cat.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>単位</label>
            <input v-model="formData.unit" placeholder="個" />
          </div>
          <div class="form-group">
            <label>標準LT(日)</label>
            <input v-model.number="formData.standard_lt_days" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_virtual_set" />
              仮想セット品番（連産品用、在庫を持たない親品番）
            </label>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

// カテゴリマッピング (DB英語 ⇔ UI日本語)
const categoryMap = {
  'ASSEMBLY': '集合',
  'SINGLE': '単品',
  'MATERIAL': '材料',
  'PURCHASED': '購入品'
}

const categoryOptions = [
  { value: 'ASSEMBLY', label: '集合' },
  { value: 'SINGLE', label: '単品' },
  { value: 'MATERIAL', label: '材料' },
  { value: 'PURCHASED', label: '購入品' }
]

const getCategoryLabel = (value) => categoryMap[value] || value

// データ
const products = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const filters = ref({
  search: '',
  category: '',
  is_active: ''
})
const formData = ref({
  product_code: '',
  product_name: '',
  category: '',
  unit: '個',
  standard_lt_days: 0,
  is_active: true,
  is_final_product: false,
  is_virtual_set: false,
})

// クエリパラメータを組み立て
const buildQueryParams = () => {
  const params = {}
  if (filters.value.search.trim()) {
    params.search = filters.value.search.trim()
  }
  if (filters.value.category) {
    params.category = filters.value.category
  }
  if (filters.value.is_active !== '') {
    params.is_active = filters.value.is_active === 'true'
  }
  return params
}

// 製品取得
const fetchProducts = async () => {
  try {
    const params = buildQueryParams()
    const response = await api.products.getProducts(params)
    products.value = response.data.results || response.data
  } catch (error) {
    console.error('製品取得エラー:', error)
    alert('製品データの取得に失敗しました')
  }
}

// 新規ダイアログ表示
const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    product_code: '',
    product_name: '',
    category: '',
  unit: '個',
  standard_lt_days: 0,
  is_active: true,
  is_final_product: false,
  is_virtual_set: false,
  }
  showDialog.value = true
}

// 編集ダイアログ表示
const editProduct = (product) => {
  isEdit.value = true
  formData.value = { ...product }
  showDialog.value = true
}

// ダイアログを閉じる
const closeDialog = () => {
  showDialog.value = false
}

// フィルタリセット
const resetFilters = async () => {
  filters.value = {
    search: '',
    category: '',
    is_active: ''
  }
  await fetchProducts()
}

// 保存
const saveProduct = async () => {
  try {
    if (isEdit.value) {
      await api.products.updateProduct(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.products.createProduct(formData.value)
      alert('作成しました')
    }
    await fetchProducts()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

// 削除
const deleteProduct = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.products.deleteProduct(id)
    await fetchProducts()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchProducts()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 180px;
}

.filter-field label {
  font-size: 12px;
  color: #555;
  margin-bottom: 4px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}
</style>

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

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
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
.form-group input[type="number"],
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
