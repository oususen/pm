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
            <th>ID</th>
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
            <td>{{ bom.id }}</td>
            <td>{{ bom.parent_product_code || getProductCodeOnly(bom.parent_product) }}</td>
            <td>{{ bom.version }}</td>
            <td>{{ bom.valid_from }}</td>
            <td>{{ bom.valid_to || '-' }}</td>
            <td>{{ bom.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="viewDetails(bom)" class="btn-sm">詳細</button>
              <button @click="viewTreeOnly(bom)" class="btn-sm">階層図</button>
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
            <input
              class="filter-input"
              type="text"
              v-model="parentProductFilter"
              placeholder="品番/品名で絞り込み"
              :disabled="isEdit"
            />
            <select v-model="formData.parent_product" required :disabled="isEdit">
              <option value="">選択してください</option>
              <option v-for="product in filteredParentProducts" :key="product.id" :value="product.id">
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
          <p><strong>BOM ID:</strong> {{ selectedBOM.id }}</p>
          <p><strong>親製品:</strong> {{ getProductName(selectedBOM.parent_product) }}</p>
          <p><strong>版:</strong> {{ selectedBOM.version }}</p>
          <p><strong>有効期間:</strong> {{ selectedBOM.valid_from }} 〜 {{ selectedBOM.valid_to || '無期限' }}</p>
          <p v-if="isPhantom(selectedBOM.parent_product)" class="phantom-info">

            この親製品は見なし組立です。リードタイム計算や展開ロジックの扱いに注意してください。

          </p>

        </div>
        <div v-if="bomTree" class="tree-section">
          <h3>階層表示</h3>
          <div class="tree-container">
            <ul class="tree-list">
              <li>
                <div class="tree-node root-node">
                  <span class="tree-product">{{ formatProductCode(bomTree.parent_product) }}</span>
                </div>
                <TreeBranch v-if="bomTree.items && bomTree.items.length" :items="bomTree.items" />
              </li>
            </ul>
          </div>
        </div>

        <h3>構成品目</h3>
        <div class="item-form">
          <div class="form-row">
            <div class="form-group">
              <label>子製品 *</label>
              <input
                class="filter-input"
                type="text"
                v-model="childProductFilter"
                placeholder="品番/品名で絞り込み"
              />
              <select v-model="itemForm.child_product" required>
                <option value="">選択してください</option>
                <option v-for="product in filteredChildProducts" :key="product.id" :value="product.id">
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
            <div class="form-group">
              <label>工程 *</label>
              <select v-model="itemForm.process" required>
                <option value="">選択してください</option>
                <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>ライン</label>
              <select v-model="itemForm.line">
                <option value="">選択しない</option>
                <option v-for="line in lines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>時間単位</label>
              <select v-model="itemForm.time_unit">
                <option value="MINUTE">分</option>
                <option value="DAY">日</option>
              </select>
            </div>
            <div class="form-group">
              <label>リードタイム(日)</label>
              <input type="number" min="0" v-model.number="itemForm.lead_time_days" :disabled="itemForm.time_unit === 'MINUTE'" />
            </div>
            <div class="form-group">
              <label>所要時間(分)</label>
              <input type="number" min="1" v-model.number="itemForm.duration_min" :disabled="itemForm.time_unit === 'DAY'" />
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
              <th>工程</th>
              <th>ライン</th>
              <th>時間</th>
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
              <td>{{ getProcessName(item.process) }}</td>
              <td>{{ getLineName(item.line) }}</td>
              <td>
                <span v-if="item.time_unit === 'MINUTE'">分 {{ item.duration_min || '-' }}</span>
                <span v-else>日 {{ item.lead_time_days }}</span>
              </td>
              <td>
                <button type="button" class="btn-sm" @click="startEditItem(item)">編集</button>
                <button type="button" class="btn-sm btn-danger" @click="deleteBOMItem(item.id)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <h3 class="mt-16">ルーティング自動生成</h3>
        <div class="routing-gen">
          <div class="form-row">
            <div class="form-group">
              <label>工程 *</label>
              <select v-model="routingGenForm.process_id">
                <option value="">選択してください</option>
                <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>ライン</label>
              <select v-model="routingGenForm.line_id">
                <option value="">選択しない</option>
                <option v-for="line in lines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>時間単位</label>
              <select v-model="routingGenForm.time_unit">
                <option value="MINUTE">分</option>
                <option value="DAY">日</option>
              </select>
            </div>
            <div class="form-group">
              <label>リードタイム(日)</label>
              <input type="number" min="0" v-model.number="routingGenForm.lead_time_days" :disabled="routingGenForm.time_unit === 'MINUTE'" />
            </div>
            <div class="form-group">
              <label>所要時間(分)</label>
              <input type="number" min="1" v-model.number="routingGenForm.duration_min" :disabled="routingGenForm.time_unit === 'DAY'" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>ルーティングコード</label>
              <input type="text" v-model="routingGenForm.routing_code" placeholder="未指定なら自動採番" />
            </div>
            <div class="form-group full-width">
              <label>説明</label>
              <input type="text" v-model="routingGenForm.description" placeholder="BOMから自動生成 のように記入" />
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn-primary" @click="generateRoutingFromBom" :disabled="!routingGenForm.process_id">
              BOMからルーティング生成
            </button>
            <button type="button" class="btn-secondary" @click="resetRoutingGenForm">リセット</button>
          </div>
          <p class="hint-text">MAKEの明細行数分のステップをこの工程・ラインで生成し、既存の自動ルーティングがあれば置き換えます。</p>
        </div>
        <div class="form-actions">
          <button type="button" @click="closeDetailsDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>

    <!-- 階層図のみダイアログ -->
    <div v-if="showTreeDialog" class="modal-overlay" @click.self="closeTreeDialog">
      <div class="modal-content modal-large">
        <h2>BOM階層図</h2>
        <div class="tree-section" v-if="!treeLoading">
          <div v-if="bomTree" class="tree-grid-container">
            <table class="tree-grid">
              <thead>
                <tr>
                  <th>部番</th>
                  <th class="level-col">階層</th>
                  <th class="qty-col">数量</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in treeRows" :key="row.key">
                  <td>
                    <span class="tree-line">{{ row.prefix }}</span>
                    <button
                      v-if="row.hasChildren"
                      @click="toggleNode(row.key)"
                      class="expand-btn"
                    >
                      {{ row.isExpanded ? '－' : '＋' }}
                    </button>
                    <span v-else class="expand-placeholder"></span>
                    {{ row.product }}
                  </td>
                  <td class="level-col">{{ row.level }}</td>
                  <td class="qty-col">{{ row.quantity }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else>データがありません</div>
        </div>
        <div v-else>読み込み中...</div>
        <div class="form-actions">
          <button type="button" @click="exportToExcel" class="btn-primary" :disabled="!bomTree">Excel出力</button>
          <button type="button" @click="closeTreeDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h, defineComponent } from 'vue'
import api from '../api/client'

const boms = ref([])
const products = ref([])
const suppliers = ref([])
const processes = ref([])
const lines = ref([])
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
const bomTree = ref(null)
const showTreeDialog = ref(false)
const treeLoading = ref(false)
const expandedNodes = ref(new Set())
const routingGenForm = ref({
  process_id: '',
  line_id: '',
  time_unit: 'MINUTE',
  lead_time_days: 0,
  duration_min: 60,
  routing_code: '',
  description: ''
})

const treeRows = computed(() => {
  if (!bomTree.value) return []
  const rows = []
  const rootKey = `root-${bomTree.value.id}`

  rows.push({
    key: rootKey,
    product: formatProductCode(bomTree.value.parent_product),
    quantity: '',
    level: 0,
    prefix: '',
    hasChildren: bomTree.value.items && bomTree.value.items.length > 0,
    isExpanded: expandedNodes.value.has(rootKey),
    parentKey: null,
  })

  const walk = (items, level, parentPrefix = '', parentKey = null, parentExpanded = true) => {
    if (!items || !parentExpanded) return
    items.forEach((item, index) => {
      const isLast = index === items.length - 1
      const connector = isLast ? '└─ ' : '├─ '
      const currentPrefix = parentPrefix + connector
      const itemKey = `item-${item.id}`
      const hasChildren = item.child_bom && item.child_bom.items && item.child_bom.items.length > 0

      rows.push({
        key: itemKey,
        product: formatProductCode(item.child_product),
        quantity: formatQuantity(item.quantity),
        level,
        prefix: currentPrefix,
        hasChildren,
        isExpanded: expandedNodes.value.has(itemKey),
        parentKey,
      })

      if (hasChildren) {
        const childPrefix = parentPrefix + (isLast ? '   ' : '│  ')
        const isExpanded = expandedNodes.value.has(itemKey)
        walk(item.child_bom.items, level + 1, childPrefix, itemKey, isExpanded)
      }
    })
  }

  const rootExpanded = expandedNodes.value.has(rootKey)
  walk(bomTree.value.items, 1, '', rootKey, rootExpanded)
  return rows
})

const toggleNode = (key) => {
  if (expandedNodes.value.has(key)) {
    expandedNodes.value.delete(key)
  } else {
    expandedNodes.value.add(key)
  }
}
const itemForm = ref({
  child_product: '',
  quantity: '1.000',
  loss_rate: '',
  sourcing_type: 'MAKE',
  supplier: '',
  process: '',
  line: '',
  time_unit: 'MINUTE',
  lead_time_days: 0,
  duration_min: 60,
  remark: ''
})
const editingItemId = ref(null)
const bomItemsRequestToken = ref(0)
const childProductFilter = ref('')
const parentProductFilter = ref('')

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
    products.value = (await api.products.getAllProducts()).sort((a, b) =>
      (b.product_code || '').localeCompare(a.product_code || '')
    )
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

const fetchProcesses = async () => {
  try {
    const response = await api.processes.getProcesses()
    processes.value = response.data.results || response.data
  } catch (error) {
    console.error('工程取得エラー:', error)
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

const resetItemForm = () => {
  itemForm.value = {
    child_product: '',
    quantity: '1.000',
    loss_rate: '',
    sourcing_type: 'MAKE',
    supplier: '',
    process: '',
    line: '',
    time_unit: 'MINUTE',
    lead_time_days: 0,
    duration_min: 60,
    remark: ''
  }
  editingItemId.value = null
}

const resetRoutingGenForm = () => {
  routingGenForm.value = {
    process_id: '',
    line_id: '',
    time_unit: 'MINUTE',
    lead_time_days: 0,
    duration_min: 60,
    routing_code: '',
    description: ''
  }
}

const fetchBOMItems = async (bomId, token = bomItemsRequestToken.value) => {
  const response = await api.boms.getBOMItems(bomId)
  if (token !== bomItemsRequestToken.value) return
  const items = response.data.results || response.data
  // 念のためクライアント側でもBOM IDで絞り込む
  bomItems.value = items.filter((item) => item.bom === bomId)
}

const fetchBOMTree = async (bomId) => {
  try {
    const response = await api.boms.getBOMTree(bomId)
    bomTree.value = response.data
  } catch (error) {
    console.error('BOMツリー取得エラー:', error)
    bomTree.value = null
  }
}

const getProductName = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return product ? `${product.product_code} - ${product.product_name}` : productId
}

const getProductCodeOnly = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return product ? product.product_code : productId
}

// Backward compatibility: some template renders may still call getProductCode
const getProductCode = (productId) => getProductCodeOnly(productId)

const formatProductCode = (productObj) => {
  if (!productObj) return ''
  return productObj.code || productObj.product_code || ''
}

const formatQuantity = (quantity) => {
  if (quantity === null || quantity === undefined) return ''
  const num = parseFloat(quantity)
  if (Number.isNaN(num)) return quantity
  return Math.trunc(num).toString()
}

const isPhantom = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return Boolean(product?.is_phantom)
}

const filteredChildProducts = computed(() => {
  const keyword = childProductFilter.value.trim().toLowerCase()
  if (!keyword) return products.value
  return products.value.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const filteredParentProducts = computed(() => {
  const keyword = parentProductFilter.value.trim().toLowerCase()
  if (!keyword) return products.value
  return products.value.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const getSupplierName = (supplierId) => {
  if (!supplierId) return '-'
  const supplier = suppliers.value.find(s => s.id === supplierId)
  return supplier ? supplier.supplier_name : supplierId
}

const getProcessName = (processId) => {
  if (!processId) return '-'
  const proc = processes.value.find(p => p.id === processId)
  return proc ? `${proc.process_code} - ${proc.process_name}` : processId
}

const getLineName = (lineId) => {
  if (!lineId) return '-'
  const line = lines.value.find(l => l.id === lineId)
  return line ? `${line.line_code} - ${line.line_name}` : lineId
}

const getSourcingTypeLabel = (value) => sourcingTypeMap[value] || value

const showNewDialog = () => {
  isEdit.value = false
  parentProductFilter.value = ''
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
  parentProductFilter.value = ''
  formData.value = {
    ...bom,
    parent_product: bom.parent_product
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  parentProductFilter.value = ''
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

const generateRoutingFromBom = async () => {
  if (!selectedBOM.value?.id) {
    alert('BOMを開いてから実行してください')
    return
  }
  if (!routingGenForm.value.process_id) {
    alert('工程を選択してください')
    return
  }

  const payload = {
    process_id: routingGenForm.value.process_id,
    time_unit: routingGenForm.value.time_unit,
    lead_time_days: routingGenForm.value.lead_time_days,
    duration_min: routingGenForm.value.duration_min,
    description: routingGenForm.value.description || undefined,
    routing_code: routingGenForm.value.routing_code || undefined,
    is_default: true,
  }
  if (routingGenForm.value.line_id) {
    payload.line_id = routingGenForm.value.line_id
  }

  try {
    const res = await api.boms.generateRouting(selectedBOM.value.id, payload)
    const steps = res.data?.generated_steps ?? '-'
    alert(`ルーティングを生成しました（ステップ: ${steps}）`)
  } catch (error) {
    console.error('ルーティング生成エラー:', error)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || 'ルーティング生成に失敗しました'
    alert('ルーティング生成に失敗しました\n\n' + errorMessage)
  }
}

const viewDetails = async (bom) => {
  selectedBOM.value = bom
  resetItemForm()
  resetRoutingGenForm()
  childProductFilter.value = ''
  bomItems.value = []
  bomTree.value = null
  const token = ++bomItemsRequestToken.value
  showDetailsDialog.value = true
  try {
    await fetchBOMItems(bom.id, token)
    await fetchBOMTree(bom.id)
  } catch (error) {
    console.error('BOM明細取得エラー:', error)
    alert('BOM明細の取得に失敗しました')
    bomItems.value = []
  }
}

const closeDetailsDialog = () => {
  showDetailsDialog.value = false
  selectedBOM.value = {}
  bomItems.value = []
  bomTree.value = null
  bomItemsRequestToken.value += 1
  resetItemForm()
  childProductFilter.value = ''
}

const viewTreeOnly = async (bom) => {
  showTreeDialog.value = true
  treeLoading.value = true
  bomTree.value = null
  expandedNodes.value = new Set()
  try {
    await fetchBOMTree(bom.id)
    // 初期状態：全て展開
    expandAllNodes()
  } catch (error) {
    alert('階層図の取得に失敗しました')
  } finally {
    treeLoading.value = false
  }
}

const expandAllNodes = () => {
  if (!bomTree.value) return
  const allKeys = new Set()
  const rootKey = `root-${bomTree.value.id}`
  allKeys.add(rootKey)

  const collectKeys = (items) => {
    if (!items) return
    items.forEach((item) => {
      const itemKey = `item-${item.id}`
      allKeys.add(itemKey)
      if (item.child_bom && item.child_bom.items && item.child_bom.items.length) {
        collectKeys(item.child_bom.items)
      }
    })
  }
  collectKeys(bomTree.value.items)
  expandedNodes.value = allKeys
}

const closeTreeDialog = () => {
  showTreeDialog.value = false
  bomTree.value = null
  expandedNodes.value = new Set()
}

const exportToExcel = () => {
  if (!bomTree.value) return

  // CSVヘッダー
  const headers = ['部番', '階層', '数量']
  const rows = [headers]

  // データ行を追加
  treeRows.value.forEach((row) => {
    // 罫線とボタン部分を含めた部番表示
    const productDisplay = row.prefix + row.product
    rows.push([
      productDisplay,
      row.level.toString(),
      row.quantity || ''
    ])
  })

  // CSV形式に変換
  const csvContent = rows.map(row =>
    row.map(cell => {
      // セル内にカンマや改行、ダブルクォートがある場合はエスケープ
      const cellStr = String(cell)
      if (cellStr.includes(',') || cellStr.includes('\n') || cellStr.includes('"')) {
        return '"' + cellStr.replace(/"/g, '""') + '"'
      }
      return cellStr
    }).join(',')
  ).join('\n')

  // BOM UTF-8付きでダウンロード（Excelで正しく開けるように）
  const bom = '\uFEFF'
  const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  // ファイル名を生成
  const parentProduct = formatProductCode(bomTree.value.parent_product)
  const timestamp = new Date().toISOString().slice(0, 10)
  const filename = `BOM階層図_${parentProduct}_${timestamp}.csv`

  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const startEditItem = (item) => {
  editingItemId.value = item.id
  itemForm.value = {
    child_product: item.child_product,
    quantity: item.quantity,
    loss_rate: item.loss_rate ?? '',
    sourcing_type: item.sourcing_type,
    supplier: item.supplier ?? '',
    process: item.process ?? '',
    line: item.line ?? '',
    time_unit: item.time_unit || 'MINUTE',
    lead_time_days: item.lead_time_days ?? 0,
    duration_min: item.duration_min ?? 60,
    remark: item.remark ?? ''
  }
}

const saveBOMItem = async () => {
  if (!selectedBOM.value?.id) return
  if (!itemForm.value.child_product || !itemForm.value.quantity) {
    alert('子製品と数量は必須です')
    return
  }
  if (!itemForm.value.process) {
    alert('工程は必須です')
    return
  }
  if (itemForm.value.time_unit === 'MINUTE' && (!itemForm.value.duration_min || itemForm.value.duration_min <= 0)) {
    alert('時間単位=分のときは所要時間(分)を1以上で入力してください')
    return
  }
  if (itemForm.value.time_unit === 'DAY' && itemForm.value.lead_time_days <= 0) {
    alert('時間単位=日 のときはリードタイム(日)を1以上で入力してください')
    return
  }

  const payload = {
    bom: selectedBOM.value.id,
    child_product: itemForm.value.child_product,
    quantity: itemForm.value.quantity,
    loss_rate: itemForm.value.loss_rate === '' ? null : itemForm.value.loss_rate,
    sourcing_type: itemForm.value.sourcing_type,
    supplier: itemForm.value.supplier || null,
    process: itemForm.value.process || null,
    line: itemForm.value.line || null,
    time_unit: itemForm.value.time_unit,
    lead_time_days: itemForm.value.lead_time_days,
    duration_min: itemForm.value.time_unit === 'MINUTE' ? itemForm.value.duration_min : null,
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
  fetchProcesses()
  fetchLines()
})

const TreeBranch = defineComponent({
  name: 'TreeBranch',
  props: {
    items: {
      type: Array,
      required: true,
    },
  },
  setup(props) {
    return () =>
      h(
        'ul',
        { class: 'tree-children' },
        props.items.map((item) =>
          h('li', { key: item.id }, [
            h('div', { class: 'tree-node' }, [
              h('span', { class: 'tree-product' }, formatProductCode(item.child_product)),
              h(
                'span',
                { class: 'tree-meta' },
                `数量: ${formatQuantity(item.quantity)}`
              ),
            ]),
            item.child_bom && item.child_bom.items && item.child_bom.items.length
              ? h(TreeBranch, { items: item.child_bom.items })
              : null,
          ])
        )
      )
  },
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

.tree-section {
  margin-bottom: 1.5rem;
}

.tree-grid-container {
  background: #f9fbff;
  border: 1px solid #e1e8f5;
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
}

.tree-grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

.tree-grid th,
.tree-grid td {
  border: 1px solid #d6dce6;
  padding: 6px 8px;
}

.tree-grid th {
  background: #eef5ff;
  text-align: left;
}

.level-col {
  width: 60px;
  text-align: center;
}

.qty-col {
  width: 90px;
  text-align: right;
}

.tree-line {
  font-family: 'Courier New', Consolas, monospace;
  color: #888;
  user-select: none;
  white-space: pre;
}

.expand-btn {
  display: inline-block;
  width: 20px;
  height: 20px;
  padding: 0;
  margin: 0 4px;
  border: 1px solid #ccc;
  background: #fff;
  color: #333;
  font-size: 14px;
  line-height: 18px;
  text-align: center;
  cursor: pointer;
  border-radius: 3px;
  vertical-align: middle;
}

.expand-btn:hover {
  background: #f0f0f0;
  border-color: #999;
}

.expand-placeholder {
  display: inline-block;
  width: 20px;
  margin: 0 4px;
}

.filter-input {
  width: 100%;
  margin-bottom: 0.5rem;
  padding: 0.4rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
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

.routing-gen {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e1e8f5;
  border-radius: 8px;
  background: #f8fbff;
}

.routing-gen .form-row {
  gap: 12px;
}

.routing-gen .form-group {
  min-width: 160px;
}

.mt-16 {
  margin-top: 16px;
}

.hint-text {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}
</style>
