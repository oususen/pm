<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製品マスタ</h1>
      <div class="page-actions">
        <button @click="openLineFinalDialog" class="btn-secondary">ライン最終品 一括設定</button>
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
          <label>製品群</label>
          <select v-model="filters.product_group">
            <option value="">すべて</option>
            <option v-for="group in productGroups" :key="group.id" :value="group.id">
              {{ group.group_code }} - {{ group.group_name }}
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
        <div class="filter-field" v-if="showCustomerFilter">
          <label>客先</label>
          <select v-model="filters.customer_code">
            <option value="">すべて</option>
            <option v-for="customer in customers" :key="customer.id" :value="customer.customer_code">
              {{ customer.customer_code }} - {{ customer.customer_name }}
            </option>
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
          <label>工程</label>
          <select v-model="filters.process">
            <option value="">すべて</option>
            <option v-for="proc in processes" :key="proc.id" :value="proc.id">
              {{ proc.process_code }} - {{ proc.process_name }}
            </option>
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
              <th>最小発注数</th>
              <th>発注倍数</th>
              <th>機種名</th>
              <th>グループ</th>
              <th>容器</th>
              <th>容器入り数</th>
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
              <td>{{ product.order_lot_min ?? '-' }}</td>
              <td>{{ product.order_lot_multiple ?? 1 }}</td>
              <td>{{ product.model_name || '-' }}</td>
              <td>{{ getProductGroupLabel(product.product_group) }}</td>
              <td>{{ getContainerLabel(product.used_container) }}</td>
              <td>{{ product.capacity ?? '-' }}</td>
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
            <label>最小発注数</label>
            <input v-model.number="formData.order_lot_min" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>発注倍数</label>
            <input v-model.number="formData.order_lot_multiple" type="number" min="1" />
          </div>
          <div class="form-group">
            <label>機種名</label>
            <input v-model="formData.model_name" placeholder="例: 17U" />
          </div>
          <div class="form-group">
            <label>製品グループ</label>
            <select v-model="formData.product_group">
              <option :value="null">未設定</option>
              <option v-for="group in productGroups" :key="group.id" :value="group.id">
                {{ group.group_code }} - {{ group.group_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>使用容器</label>
            <select v-model="formData.used_container">
              <option :value="null">未設定</option>
              <option v-for="container in containers" :key="container.id" :value="container.id">
                {{ formatContainerOption(container) }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>容器入り数</label>
            <input v-model.number="formData.capacity" type="number" min="0" />
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
            <label>後工程</label>
            <select v-model="formData.next_process">
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
              <input type="checkbox" v-model="formData.is_final_product" />
              最終品（完成品として出荷される品目）
            </label>
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
    <!-- ライン最終品 一括設定ダイアログ -->
    <div v-if="showLineFinalDialog" class="modal-overlay" @click.self="showLineFinalDialog = false">
      <div class="modal-content line-final-modal">
        <h2>ライン最終品 一括設定</h2>

        <div class="lf-filter-bar">
          <div class="filter-field">
            <label>ライン</label>
            <select v-model="lfSelectedLine" @change="fetchLineFinalCandidates">
              <option value="">すべて</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
        </div>

        <div class="lf-lines-area">
          <div v-for="lineGroup in lfLineGroups" :key="lineGroup.line_id" class="lf-line-group">
            <h3 class="lf-line-header">{{ lineGroup.line_code }} - {{ lineGroup.line_name }}</h3>
            <table class="data-table lf-table">
              <thead>
                <tr>
                  <th style="width: 60px;">ライン最終品</th>
                  <th>品番コード</th>
                  <th>品名</th>
                  <th>カテゴリ</th>
                  <th>最終品</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in lineGroup.products" :key="product.id">
                  <td style="text-align: center;">
                    <input
                      type="checkbox"
                      v-model="lfChanges[product.id]"
                    />
                  </td>
                  <td>{{ product.product_code }}</td>
                  <td>{{ product.product_name }}</td>
                  <td>{{ getCategoryLabel(product.category) }}</td>
                  <td>{{ product.is_final_product ? '最終' : '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="lfLineGroups.length === 0" class="no-data">
            ルーティングに紐づく製品がありません
          </div>
        </div>

        <div class="form-actions">
          <button @click="saveLineFinal" class="btn-primary" :disabled="lfSaving">
            {{ lfSaving ? '保存中...' : '保存' }}
          </button>
          <button @click="showLineFinalDialog = false" class="btn-secondary">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '@/api/client'

// カテゴリマッピング (DB英語 ⇔ UI日本語)
const categoryMap = {
  'ASSEMBLY': '集合',
  'SINGLE': '単品',
  'MATERIAL': '材料',
  'PURCHASED': '購入品',
  'UNKNOWN': '未定',
  '–¢’è': '未定', // 文字化けして保存された既存値も未定扱い
}

const categoryOptions = [
  { value: 'ASSEMBLY', label: '集合' },
  { value: 'SINGLE', label: '単品' },
  { value: 'MATERIAL', label: '材料' },
  { value: 'PURCHASED', label: '購入品' },
  { value: 'UNKNOWN', label: '未定' },
]

const getCategoryLabel = (value) => categoryMap[value] || value

// データ
const products = ref([])
const lines = ref([])
const processes = ref([])
const productGroups = ref([])
const containers = ref([])
const customers = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const totalCount = ref(0)
const filters = ref({
  search: '',
  category: '',
  product_group: '',
  is_final_product: '',
  is_line_final_product: '',
  has_bom: '',
  customer_code: '',
  is_active: '',
  created_from: '',
  created_to: ''
})
const formData = ref({
  product_code: '',
  product_name: '',
  model_name: '',
  category: '',
  unit: '個',
  standard_lt_days: 0,
  order_lot_min: null,
  order_lot_multiple: 1,
  product_group: null,
  used_container: null,
  capacity: null,
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

// ライン最終品一括設定
const showLineFinalDialog = ref(false)
const lfSelectedLine = ref('')
const lfLineGroups = ref([])
const lfChanges = ref({})  // product_id -> boolean
const lfSaving = ref(false)

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

const showCustomerFilter = computed(() => filters.value.is_final_product === 'true')

const productGroupMap = computed(() => {
  const map = new Map()
  for (const group of productGroups.value) {
    map.set(group.id, group)
  }
  return map
})

const containerMap = computed(() => {
  const map = new Map()
  for (const container of containers.value) {
    map.set(container.id, container)
  }
  return map
})

const getProductGroupLabel = (groupId) => {
  if (!groupId) return '-'
  const group = productGroupMap.value.get(groupId)
  return group ? `${group.group_code} - ${group.group_name}` : '-'
}

const getContainerLabel = (containerId) => {
  if (!containerId) return '-'
  const container = containerMap.value.get(containerId)
  return container ? formatContainerOption(container) : '-'
}

const formatContainerOption = (container) => {
  if (!container) return ''
  if (container.capacity) {
    return `${container.name} (${container.capacity})`
  }
  return container.name
}

// クエリパラメータを組み立て
const buildQueryParams = () => {
  const params = {}
  if (filters.value.search.trim()) {
    params.search = filters.value.search.trim()
  }
  if (filters.value.category) {
    params.category = filters.value.category
  }
  if (filters.value.product_group) {
    params.product_group = filters.value.product_group
  }
  if (filters.value.is_final_product !== '') {
    params.is_final_product = filters.value.is_final_product === 'true'
  }
  if (filters.value.is_final_product === 'true' && filters.value.customer_code) {
    params.customer_code = filters.value.customer_code
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
  if (filters.value.process) {
    params.process = filters.value.process
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

const fetchProductGroups = async () => {
  try {
    const response = await api.productGroups.getProductGroups()
    productGroups.value = response.data.results || response.data
  } catch (error) {
    console.error('製品グループ取得エラー:', error)
  }
}

const fetchContainers = async () => {
  try {
    const response = await api.containerCapacities.getContainerCapacities()
    containers.value = response.data.results || response.data
  } catch (error) {
    console.error('容器取得エラー:', error)
  }
}

const fetchCustomers = async () => {
  try {
    const response = await api.customers.getCustomers()
    customers.value = response.data.results || response.data
  } catch (error) {
    console.error('得意先取得エラー:', error)
  }
}

// 新規ダイアログ表示
const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    product_code: '',
    product_name: '',
    model_name: '',
    category: '',
    unit: '個',
    standard_lt_days: 0,
    order_lot_min: null,
    order_lot_multiple: 1,
    product_group: null,
    used_container: null,
    capacity: null,
    line: null,
    process: null,
    next_process: null,
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
    model_name: product.model_name ?? '',
    order_lot_min: product.order_lot_min ?? null,
    order_lot_multiple: product.order_lot_multiple ?? 1,
    line: product.line ?? null,
    process: product.process ?? null,
    next_process: product.next_process ?? null,
    management_unit: product.management_unit ?? null,
    product_group: product.product_group ?? null,
    used_container: product.used_container ?? null,
    capacity: product.capacity ?? null,
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
    product_group: '',
    is_final_product: '',
    is_line_final_product: '',
    has_bom: '',
    customer_code: '',
    is_active: '',
    process: '',
    created_from: '',
    created_to: ''
  }
  await fetchProducts(1)
}

const normalizeNumber = (value) => {
  if (value === '' || value === null || Number.isNaN(value)) return null
  return value
}

// 保存
const saveProduct = async () => {
  try {
    const payload = {
      ...formData.value,
      model_name: formData.value.model_name || null,
      product_group: formData.value.product_group || null,
      used_container: formData.value.used_container || null,
      standard_lt_days: normalizeNumber(formData.value.standard_lt_days),
      order_lot_min: normalizeNumber(formData.value.order_lot_min),
      order_lot_multiple: Math.max(1, Number(formData.value.order_lot_multiple || 1)),
      self_lt_days: normalizeNumber(formData.value.self_lt_days),
      capacity: normalizeNumber(formData.value.capacity),
    }
    if (isEdit.value) {
      await api.products.updateProduct(payload.id, payload)
      alert('更新しました')
    } else {
      await api.products.createProduct(payload)
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

// ライン最終品一括設定
const openLineFinalDialog = async () => {
  lfSelectedLine.value = ''
  showLineFinalDialog.value = true
  await fetchLineFinalCandidates()
}

const fetchLineFinalCandidates = async () => {
  try {
    const lineId = lfSelectedLine.value || null
    const response = await api.products.getLineFinalCandidates(lineId)
    lfLineGroups.value = response.data
    // 現在の値でチェックボックス初期化
    const changes = {}
    for (const group of response.data) {
      for (const product of group.products) {
        changes[product.id] = product.is_line_final_product
      }
    }
    lfChanges.value = changes
  } catch (error) {
    console.error('ライン最終品候補取得エラー:', error)
    alert('データの取得に失敗しました')
  }
}

const saveLineFinal = async () => {
  lfSaving.value = true
  try {
    const updates = Object.entries(lfChanges.value).map(([id, val]) => ({
      id: Number(id),
      is_line_final_product: val,
    }))
    const response = await api.products.bulkUpdateLineFinal(updates)
    alert(`${response.data.updated}件 更新しました`)
    showLineFinalDialog.value = false
    await fetchProducts(currentPage.value)
  } catch (error) {
    console.error('一括更新エラー:', error)
    alert('保存に失敗しました')
  } finally {
    lfSaving.value = false
  }
}

onMounted(() => {
  fetchProducts(1)
  fetchLines()
  fetchProcesses()
  fetchProductGroups()
  fetchContainers()
  fetchCustomers()
})

watch(
  () => filters.value.is_final_product,
  (value) => {
    if (value !== 'true') {
      filters.value.customer_code = ''
    }
  }
)
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

/* ライン最終品一括設定モーダル */
.line-final-modal {
  min-width: 700px;
  max-width: 900px;
}

.lf-filter-bar {
  margin-bottom: 16px;
}

.lf-lines-area {
  max-height: 60vh;
  overflow-y: auto;
}

.lf-line-group {
  margin-bottom: 20px;
}

.lf-line-header {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  background-color: #f3f4f6;
  padding: 6px 10px;
  border-radius: 4px;
  margin: 0 0 4px 0;
}

.lf-table {
  font-size: 13px;
}

.lf-table td,
.lf-table th {
  padding: 4px 8px;
}
</style>
