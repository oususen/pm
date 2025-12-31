<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製品マスタ</h1>
      <div class="page-actions">
        <button @click="fetchProducts(1)" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>品番/品名</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchProducts(1)"
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
          <label>最終品</label>
          <select v-model="filters.is_final_product">
            <option value="">すべて</option>
            <option value="true">はい</option>
            <option value="false">いいえ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>ライン最終品</label>
          <select v-model="filters.is_line_final_product">
            <option value="">すべて</option>
            <option value="true">はい</option>
            <option value="false">いいえ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>BOM持ち</label>
          <select v-model="filters.has_bom">
            <option value="">すべて</option>
            <option value="true">あり</option>
            <option value="false">なし</option>
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
        <div class="filter-field">
          <label>作成日 From</label>
          <input type="date" v-model="filters.created_from" />
        </div>
        <div class="filter-field">
          <label>作成日 To</label>
          <input type="date" v-model="filters.created_to" />
        </div>
        <div class="filter-actions">
          <button @click="fetchProducts(1)" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <div class="list-area">
        <table class="data-table">
          <thead>
            <tr>
              <th>品番コード</th>
              <th>品名</th>
              <th>カテゴリ</th>
              <th>単位</th>
              <th>標準LT(日)</th>
              <th>最終品</th>
              <th>ライン最終品</th>
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
              <td>{{ product.is_final_product ? '最終' : '' }}</td>
              <td>{{ product.is_line_final_product ? 'はい' : '' }}</td>
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

        <div class="pagination-area">
          <div class="pagination" v-if="totalPages > 1">
            <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(1)">
              最初
            </button>
            <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">
              前へ
            </button>
            <button
              v-for="page in visiblePages"
              :key="page"
              class="pagination-btn"
              :class="{ 'is-active': page === currentPage }"
              @click="changePage(page)"
            >
              {{ page }}
            </button>
            <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">
              次へ
            </button>
            <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="changePage(totalPages)">
              最後
            </button>
          </div>
          <div class="pagination-info">{{ pageRangeLabel }}</div>
        </div>

        <div v-if="products.length === 0" class="no-data">
          データがありません
        </div>
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
            <label>ライン情報</label>
            <select v-model="formData.line">
              <option :value="null">未設定</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>工程情報</label>
            <select v-model="formData.process">
              <option :value="null">未設定</option>
              <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                {{ proc.process_code }} - {{ proc.process_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>管理区分（日/分）</label>
            <select v-model="formData.management_unit">
              <option :value="null">未設定</option>
              <option value="DAY">日</option>
              <option value="MINUTE">分</option>
            </select>
          </div>
          <div class="form-group">
            <label>画像URL</label>
            <input v-model="formData.image_url" placeholder="/media/products/..." />
            <div class="upload-row">
              <input type="file" ref="fileInput" @change="onFileSelected" accept="image/*" />
              <button type="button" class="btn-secondary" @click="triggerFileInput" :disabled="!isEdit && !formData.id">
                画像をアップロード
              </button>
              <span class="hint-small" v-if="!isEdit && !formData.id">保存後にアップロードできます</span>
            </div>
            <div class="image-preview" v-if="formData.image_url">
              <img :src="formData.image_url" alt="Product image" />
            </div>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_line_final_product" />
              ライン最終品（ラインで最後に出力される品目）
            </label>
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
import { ref, onMounted, computed } from 'vue'
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
const lines = ref([])
const processes = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const totalCount = ref(0)
const filters = ref({
  search: '',
  category: '',
  is_final_product: '',
  is_line_final_product: '',
  has_bom: '',
  is_active: '',
  created_from: '',
  created_to: ''
})
const formData = ref({
  product_code: '',
  product_name: '',
  category: '',
  unit: '個',
  standard_lt_days: 0,
  line: null,
  process: null,
  management_unit: null,
  is_active: true,
  is_line_final_product: false,
  is_final_product: false,
  is_virtual_set: false,
  image_url: '',
})
const fileInput = ref(null)

const totalPages = computed(() => {
  if (totalCount.value === 0) return 1
  return Math.ceil(totalCount.value / pageSize.value)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const windowSize = 2
  const start = Math.max(1, current - windowSize)
  const end = Math.min(total, current + windowSize)
  const pages = []
  for (let i = start; i <= end; i += 1) {
    pages.push(i)
  }
  return pages
})

const pageRangeLabel = computed(() => {
  if (totalCount.value === 0) return '0件'
  const start = (currentPage.value - 1) * pageSize.value + 1
  const end = Math.min(currentPage.value * pageSize.value, totalCount.value)
  return `${totalCount.value}件中 ${start}-${end}件`
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
  if (filters.value.is_final_product !== '') {
    params.is_final_product = filters.value.is_final_product === 'true'
  }
  if (filters.value.is_line_final_product !== '') {
    params.is_line_final_product = filters.value.is_line_final_product === 'true'
  }
  if (filters.value.has_bom !== '') {
    params.has_bom = filters.value.has_bom === 'true'
  }
  if (filters.value.is_active !== '') {
    params.is_active = filters.value.is_active === 'true'
  }
  if (filters.value.created_from) {
    params.created_from = filters.value.created_from
  }
  if (filters.value.created_to) {
    params.created_to = filters.value.created_to
  }
  return params
}

// 製品取得
const fetchProducts = async (page = 1) => {
  try {
    const params = buildQueryParams()
    params.page = page
    params.page_size = pageSize.value
    const response = await api.products.getProducts(params)
    const data = response.data
    if (data?.results) {
      products.value = data.results
      totalCount.value = data.count ?? data.results.length
    } else {
      products.value = Array.isArray(data) ? data : []
      totalCount.value = products.value.length
    }
    currentPage.value = page
  } catch (error) {
    console.error('製品取得エラー:', error)
    alert('製品データの取得に失敗しました')
  }
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines()
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
  }
}

const fetchProcesses = async () => {
  try {
    const response = await api.processes.getProcesses()
    processes.value = response.data.results || response.data
  } catch (error) {
    console.error('工程取得エラー:', error)
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
    line: null,
    process: null,
    management_unit: null,
    is_active: true,
    is_line_final_product: false,
    is_final_product: false,
    is_virtual_set: false,
    image_url: '',
  }
  showDialog.value = true
}

// 編集ダイアログ表示
const editProduct = (product) => {
  isEdit.value = true
  formData.value = {
    ...product,
    line: product.line ?? null,
    process: product.process ?? null,
    management_unit: product.management_unit ?? null,
  }
  if (!formData.value.image_url) {
    formData.value.image_url = ''
  }
  showDialog.value = true
}

// ダイアログを閉じる
const closeDialog = () => {
  showDialog.value = false
  if (fileInput.value) fileInput.value.value = ''
}

// フィルタリセット
const resetFilters = async () => {
  filters.value = {
    search: '',
    category: '',
    is_final_product: '',
    is_line_final_product: '',
    has_bom: '',
    is_active: '',
    created_from: '',
    created_to: ''
  }
  await fetchProducts(1)
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

const triggerFileInput = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const onFileSelected = async (e) => {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  if (!formData.value.id) {
    alert('先に保存してからアップロードしてください。')
    return
  }
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await api.products.uploadProductImage(formData.value.id, fd)
    formData.value.image_url = res.data.image_url || ''
    alert('画像をアップロードしました')
  } catch (error) {
    console.error('画像アップロードエラー:', error)
    alert('画像のアップロードに失敗しました')
  } finally {
    if (fileInput.value) fileInput.value.value = ''
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

const changePage = async (page) => {
  const target = Math.min(Math.max(page, 1), totalPages.value)
  if (target === currentPage.value) return
  await fetchProducts(target)
}

onMounted(() => {
  fetchProducts(1)
  fetchLines()
  fetchProcesses()
})
</script>

<style scoped>
.page-container {
  height: 100%;
}

.page-content {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

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

.list-area {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
}

.pagination-area {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pagination {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pagination-btn {
  padding: 4px 10px;
  border: 1px solid #d1d5db;
  background-color: #fff;
  color: #374151;
  border-radius: 4px;
  cursor: pointer;
}

.pagination-btn.is-active {
  background-color: #1f2937;
  border-color: #1f2937;
  color: #fff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 12px;
  color: #6b7280;
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
.upload-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hint-small {
  font-size: 12px;
  color: #64748b;
}
.image-preview img {
  max-height: 120px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  margin-top: 6px;
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
