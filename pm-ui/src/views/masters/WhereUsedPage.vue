<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">逆展開（Where Used）</h2>
        <p class="subtitle">指定した製品がどの親製品で使われているかを確認します。</p>
      </div>
    </div>

    <div class="where-used-body">
      <div class="form-group">
        <label>製品を選択</label>
        <input
          class="filter-input"
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <select v-model="selectedProductId" @change="fetchWhereUsed">
          <option value="">選択してください</option>
          <option v-for="product in filteredProducts" :key="product.id" :value="product.id">
            {{ product.product_code }} - {{ product.product_name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>
          <input type="checkbox" v-model="recursive" @change="fetchWhereUsed" />
          再帰的に最終製品まで辿る
        </label>
      </div>

      <div v-if="loading" class="loading-text">読み込み中...</div>

      <div v-else-if="results.length > 0" class="where-used-results">
        <h3>この製品を使用している親製品（{{ results.length }}件）</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>親製品</th>
              <th>カテゴリ</th>
              <th>数量</th>
              <th>調達区分</th>
              <th>加工先</th>
              <th>加工工程</th>
              <th>自LT</th>
              <th>最終品</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="selfRow" class="self-row">
              <td>★ {{ selfRow.product_code }} - {{ selfRow.product_name }}（検索品）</td>
              <td>{{ getCategoryLabel(selfRow.category) }}</td>
              <td>1</td>
              <td>{{ getSourcingTypeLabel(selfRow.sourcing_type) }}</td>
              <td>{{ formatDestination(selfRow) }}</td>
              <td>{{ formatProcess(selfRow) }}</td>
              <td>{{ selfRow.self_lt_days ?? '-' }}</td>
              <td>{{ selfRow.is_final_product ? '最終品' : '' }}</td>
            </tr>
            <template v-for="item in results" :key="item.parent_product_id">
              <tr :style="getItemFinalColor(item) ? { background: getItemFinalColor(item) } : {}">
                <td>{{ item.parent_product_code }} - {{ item.parent_product_name }}</td>
                <td>{{ getCategoryLabel(item.category) }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ getSourcingTypeLabel(getWhereUsedDisplaySourcingType(item)) }}</td>
                <td>{{ formatDestination(item) }}</td>
                <td>{{ formatProcess(item) }}</td>
                <td>{{ item.parent_self_lt_days ?? '-' }}</td>
                <td>
                  <span v-if="item.is_final_product" class="final-badge" :style="{ background: getFinalProductColor(item.parent_product_code) }">最終品</span>
                </td>
              </tr>
              <template v-if="recursive && item.parents && item.parents.length > 0">
                <tr v-for="(child, idx) in flattenParents(item.parents, 1)" :key="`${item.parent_product_id}-${idx}`" class="nested-row" :style="child.final_product_code ? { background: getFinalProductColor(child.final_product_code) } : {}">
                  <td :style="{ paddingLeft: (child.level * 20 + 8) + 'px' }">
                    └ {{ child.parent_product_code }} - {{ child.parent_product_name }}
                  </td>
                  <td>{{ getCategoryLabel(child.category) }}</td>
                  <td>{{ child.quantity }}</td>
                  <td>{{ getSourcingTypeLabel(getWhereUsedDisplaySourcingType(child)) }}</td>
                  <td>{{ formatDestination(child) }}</td>
                  <td>{{ formatProcess(child) }}</td>
                  <td>{{ child.parent_self_lt_days ?? '-' }}</td>
                  <td>
                    <span v-if="child.is_final_product" class="final-badge" :style="{ background: getFinalProductColor(child.parent_product_code) }">最終品</span>
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
        </table>
      </div>

      <div v-else-if="selectedProductId && !loading" class="no-data">
        この製品を使用している親製品はありません
      </div>

      <div class="form-actions">
        <button type="button" @click="exportCsv" class="btn-info" :disabled="!results.length">Excel出力</button>
        <button type="button" @click="closePage" class="btn-secondary">閉じる</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const route = useRoute()

const products = ref([])
const productFilter = ref('')
const selectedProductId = ref('')
const recursive = ref(false)
const loading = ref(false)
const productsLoading = ref(false)
const results = ref([])
const selfRow = ref(null)

const categoryMap = {
  'ASSEMBLY': '組立品',
  'SINGLE': '単品',
  'MATERIAL': '材料',
  'PURCHASED': '購入品',
  'OUTSOURCED': '外作品',
  'UNKNOWN': '未定',
}
const sourcingTypeMap = {
  'MAKE': '自社製造',
  'BUY': '購買',
  'SUBCON': '外注',
}
const getCategoryLabel = (value) => categoryMap[value] || value || '-'
const getSourcingTypeLabel = (value) => sourcingTypeMap[value] || value
const getWhereUsedDisplaySourcingType = (item) => {
  if (!item) return ''
  const lineType = item.parent_line_type || item.line_type || ''
  if (lineType === 'PURCHASE') return 'BUY'
  if (lineType === 'OUTSOURCE') return 'SUBCON'
  if (lineType) return 'MAKE'
  return item.sourcing_type
}

const filteredProducts = computed(() => {
  const keyword = productFilter.value.trim().toLowerCase()
  if (!keyword) return products.value
  return products.value.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const formatCodeName = (code, name) => {
  if (code && name) return `${code} ${name}`
  return code || name || ''
}

const formatDestination = (item) => {
  if (!item) return ''
  const sourcingType = getWhereUsedDisplaySourcingType(item)
  const lineLabel = formatCodeName(item.parent_line_code || item.line_code, item.parent_line_name || item.line_name)
  const supplierLabel = formatCodeName(item.supplier_code, item.supplier_name)
  const lineType = item.parent_line_type || item.line_type || ''
  if (lineType === 'OUTSOURCE') return supplierLabel || lineLabel || '-'
  switch (sourcingType) {
    case 'BUY': return supplierLabel || lineLabel || '-'
    case 'SUBCON': return lineLabel || supplierLabel || '-'
    default: return lineLabel || supplierLabel || '-'
  }
}

const formatProcess = (item) => {
  if (!item) return '-'
  return formatCodeName(item.parent_process_code || item.process_code, item.parent_process_name || item.process_name) || '-'
}

const FINAL_PRODUCT_COLORS = [
  '#e3f2fd', '#fce4ec', '#e8f5e9', '#fff3e0', '#f3e5f5',
  '#e0f7fa', '#fff9c4', '#fbe9e7', '#e8eaf6', '#f1f8e9',
]

const findFinalProductCodes = (node) => {
  const codes = []
  if (node.is_final_product) codes.push(node.parent_product_code)
  if (node.parents && node.parents.length > 0) {
    for (const p of node.parents) {
      codes.push(...findFinalProductCodes(p))
    }
  }
  return [...new Set(codes)]
}

const allFinalProductCodes = computed(() => {
  const codes = new Set()
  for (const item of results.value) {
    findFinalProductCodes(item).forEach(c => codes.add(c))
  }
  return Array.from(codes)
})

const getFinalProductColor = (code) => {
  if (!code) return ''
  const idx = allFinalProductCodes.value.indexOf(code)
  if (idx < 0) return ''
  return FINAL_PRODUCT_COLORS[idx % FINAL_PRODUCT_COLORS.length]
}

const getItemFinalColor = (item) => {
  const codes = findFinalProductCodes(item)
  return getFinalProductColor(codes[0] || null)
}

const flattenParents = (parents, level) => {
  const result = []
  for (const p of parents) {
    const finalCode = p.is_final_product
      ? p.parent_product_code
      : (findFinalProductCodes(p)[0] || null)
    result.push({ ...p, level, final_product_code: finalCode })
    if (p.parents && p.parents.length > 0) {
      result.push(...flattenParents(p.parents, level + 1))
    }
  }
  return result
}

const fetchWhereUsed = async () => {
  if (!selectedProductId.value) {
    results.value = []
    selfRow.value = null
    return
  }
  loading.value = true
  try {
    const response = await api.products.getWhereUsed(
      selectedProductId.value,
      recursive.value
    )
    selfRow.value = response.data?.self_info || null
    results.value = response.data?.parents || []
  } catch (error) {
    console.error('逆展開取得エラー:', error)
    alert('逆展開データの取得に失敗しました')
    results.value = []
    selfRow.value = null
  } finally {
    loading.value = false
  }
}

const escCsv = (val) => {
  if (val === null || val === undefined) return ''
  const str = String(val)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}

const exportCsv = () => {
  if (!results.value.length) return
  const product = products.value.find(p => `${p.id}` === `${selectedProductId.value}`)
  const searchCode = product?.product_code || ''
  const searchName = product?.product_name || ''
  const bom = '﻿'
  const lines = []
  lines.push(['逆展開（Where Used）'].map(escCsv).join(','))
  lines.push(['検索品', `${searchCode} - ${searchName}`].map(escCsv).join(','))
  lines.push('')
  const header = ['親製品', 'カテゴリ', '数量', '調達区分', '加工先', '加工工程', '自LT', '最終品']
  lines.push(header.map(escCsv).join(','))

  const pushRow = (item, prefix) => {
    lines.push([
      escCsv(`${prefix}${item.parent_product_code} - ${item.parent_product_name}`),
      escCsv(getCategoryLabel(item.category)),
      escCsv(item.quantity),
      escCsv(getSourcingTypeLabel(getWhereUsedDisplaySourcingType(item))),
      escCsv(formatDestination(item)),
      escCsv(formatProcess(item)),
      escCsv(item.parent_self_lt_days ?? '-'),
      escCsv(item.is_final_product ? '最終品' : ''),
    ].join(','))
  }

  if (selfRow.value) {
    pushRow({ ...selfRow.value, parent_product_code: selfRow.value.product_code, parent_product_name: selfRow.value.product_name, parent_self_lt_days: selfRow.value.self_lt_days }, '★ ')
  }
  for (const item of results.value) {
    pushRow(item, '')
    if (recursive.value && item.parents && item.parents.length > 0) {
      for (const child of flattenParents(item.parents, 1)) {
        const indent = '　'.repeat(child.level - 1) + '└ '
        pushRow(child, indent)
      }
    }
  }

  const csvContent = bom + lines.join('\r\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `逆展開_${searchCode}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

const closePage = () => {
  window.close()
}

onMounted(async () => {
  productsLoading.value = true
  try {
    products.value = await api.products.getAllProducts({ is_active: true })
  } catch (error) {
    console.error('製品一覧取得エラー:', error)
  } finally {
    productsLoading.value = false
  }

  const productId = route.query.productId
  if (productId) {
    selectedProductId.value = productId
    await fetchWhereUsed()
  }
})
</script>

<style scoped>
.page-container {
  padding: 16px;
}
.page-header {
  margin-bottom: 16px;
}
.page-title {
  margin: 0 0 4px 0;
  font-size: 20px;
}
.subtitle {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.where-used-body {
  max-width: 1600px;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
  font-size: 13px;
}
.filter-input {
  width: 100%;
  margin-bottom: 0.5rem;
  padding: 0.4rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.form-group select {
  width: 100%;
  padding: 0.4rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.loading-text {
  padding: 20px;
  color: #666;
}
.no-data {
  padding: 20px;
  color: #999;
}
.where-used-results {
  margin-top: 1rem;
}
.where-used-results h3 {
  margin-bottom: 0.5rem;
  font-size: 14px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th,
.data-table td {
  border: 1px solid #ddd;
  padding: 6px 8px;
  text-align: left;
}
.data-table th {
  background: #f5f5f5;
  font-weight: 600;
  white-space: nowrap;
}
.self-row {
  background: #fffde7;
  font-weight: 600;
}
.nested-row {
  background-color: #f9f9f9;
}
.nested-row td:first-child {
  color: #666;
}
.final-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
}
.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.btn-info {
  background-color: #17a2b8;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-info:hover {
  background-color: #138496;
}
.btn-info:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-secondary {
  background-color: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-secondary:hover {
  background-color: #e9e9e9;
}
</style>
