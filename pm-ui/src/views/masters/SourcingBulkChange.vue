<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">加工先一括変更</h2>
      <p class="subtitle">指定した部品の加工先（外作⇔社内）をBOM・ルーティング横断で一括変更します。</p>
    </div>

    <div class="body">
      <!-- 検索 -->
      <div class="search-row">
        <label>品番:</label>
        <input
          v-model="productCode"
          type="text"
          placeholder="例: YD00000598G"
          class="filter-input"
          @keydown.enter="search"
        />
        <button class="btn-primary" @click="search" :disabled="!productCode.trim() || loading">検索</button>
      </div>

      <div v-if="loading" class="loading-text">読み込み中...</div>

      <template v-if="product">
        <!-- 製品情報 -->
        <div class="product-info">
          <span class="info-label">品番:</span> {{ product.product_code }}
          <span class="info-label ml">品名:</span> {{ product.product_name }}
          <span class="info-label ml">カテゴリ:</span>
          <select v-model="newCategory" class="inline-select">
            <option v-for="c in categoryChoices" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>

        <!-- 一括変更設定 -->
        <fieldset class="change-panel">
          <legend>一括変更値</legend>
          <div class="change-fields">
            <div class="field">
              <label>調達区分:</label>
              <select v-model="newSourcingType">
                <option value="">-- 変更しない --</option>
                <option value="MAKE">自社製造</option>
                <option value="BUY">購買</option>
                <option value="SUBCON">外注</option>
              </select>
            </div>
            <div class="field">
              <label>工程:</label>
              <select v-model="newProcessId">
                <option :value="null">-- 変更しない --</option>
                <option :value="0">クリア</option>
                <option v-for="p in processes" :key="p.id" :value="p.id">{{ p.process_code }} {{ p.process_name }}</option>
              </select>
            </div>
            <div class="field">
              <label>ライン:</label>
              <select v-model="newLineId">
                <option :value="null">-- 変更しない --</option>
                <option :value="0">クリア</option>
                <option v-for="l in lines" :key="l.id" :value="l.id">{{ l.line_code }} {{ l.line_name }}</option>
              </select>
            </div>
            <div class="field">
              <label>仕入先:</label>
              <select v-model="newSupplierId">
                <option :value="null">-- 変更しない --</option>
                <option :value="0">クリア</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.supplier_code }} {{ s.supplier_name }}</option>
              </select>
            </div>
          </div>
        </fieldset>

        <!-- BOM一覧 -->
        <div class="section">
          <h3>
            <input type="checkbox" :checked="allBomChecked" @change="toggleAllBom" />
            BOM明細（{{ bomItems.length }}件）
          </h3>
          <div class="table-wrap">
            <table class="data-table" v-if="bomItems.length">
              <thead>
                <tr>
                  <th class="chk-col"><input type="checkbox" :checked="allBomChecked" @change="toggleAllBom" /></th>
                  <th>親製品</th>
                  <th>調達区分</th>
                  <th>仕入先</th>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>数量</th>
                  <th>LT(日)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in bomItems" :key="item.id">
                  <td class="chk-col"><input type="checkbox" v-model="selectedBomIds" :value="item.id" /></td>
                  <td>{{ item.parent_product_code }} {{ item.parent_product_name }}</td>
                  <td>{{ sourcingLabel(item.sourcing_type) }}</td>
                  <td>{{ item.supplier_name || '-' }}</td>
                  <td>{{ item.process_name || '-' }}</td>
                  <td>{{ item.line_name || '-' }}</td>
                  <td class="num">{{ item.quantity }}</td>
                  <td class="num">{{ item.lead_time_days }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="no-data">該当BOM明細なし</p>
          </div>
        </div>

        <!-- ルーティング一覧 -->
        <div class="section">
          <h3>
            <input type="checkbox" :checked="allStepChecked" @change="toggleAllStep" />
            ルーティング工程（{{ routingSteps.length }}件）
          </h3>
          <div class="table-wrap">
            <table class="data-table" v-if="routingSteps.length">
              <thead>
                <tr>
                  <th class="chk-col"><input type="checkbox" :checked="allStepChecked" @change="toggleAllStep" /></th>
                  <th>製品(ルーティング)</th>
                  <th>工程No</th>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>外作先</th>
                  <th>LT(日)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="step in routingSteps" :key="step.id">
                  <td class="chk-col"><input type="checkbox" v-model="selectedStepIds" :value="step.id" /></td>
                  <td>{{ step.routing_product_code }} {{ step.routing_product_name }}</td>
                  <td class="num">{{ step.step_no }}</td>
                  <td>{{ step.process_name || '-' }}</td>
                  <td>{{ step.line_name || '-' }}</td>
                  <td>{{ step.supplier_name || '-' }}</td>
                  <td class="num">{{ step.lead_time_days }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="no-data">該当ルーティング工程なし</p>
          </div>
        </div>

        <!-- 実行 -->
        <div class="form-actions">
          <span class="summary">選択: BOM {{ selectedBomIds.length }}件 / ルーティング {{ selectedStepIds.length }}件</span>
          <button
            class="btn-primary"
            @click="applyChanges"
            :disabled="applying || (!selectedBomIds.length && !selectedStepIds.length && newCategory === product.category)"
          >
            {{ applying ? '適用中...' : '一括変更を適用' }}
          </button>
        </div>
      </template>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const categoryChoices = [
  { value: 'ASSEMBLY', label: '組立品' },
  { value: 'SINGLE', label: '単品' },
  { value: 'MATERIAL', label: '材料' },
  { value: 'PURCHASED', label: '購入品' },
  { value: 'OUTSOURCED', label: '外作品' },
  { value: 'UNKNOWN', label: '未定' },
]

const sourcingMap = { MAKE: '自社製造', BUY: '購買', SUBCON: '外注' }
const sourcingLabel = (v) => sourcingMap[v] || v

const productCode = ref('')
const loading = ref(false)
const applying = ref(false)
const errorMsg = ref('')

const product = ref(null)
const newCategory = ref('')
const bomItems = ref([])
const routingSteps = ref([])

const selectedBomIds = ref([])
const selectedStepIds = ref([])

const newSourcingType = ref('')
const newProcessId = ref(null)
const newLineId = ref(null)
const newSupplierId = ref(null)

const processes = ref([])
const lines = ref([])
const suppliers = ref([])

const allBomChecked = computed(() => bomItems.value.length > 0 && selectedBomIds.value.length === bomItems.value.length)
const allStepChecked = computed(() => routingSteps.value.length > 0 && selectedStepIds.value.length === routingSteps.value.length)

const toggleAllBom = () => {
  if (allBomChecked.value) {
    selectedBomIds.value = []
  } else {
    selectedBomIds.value = bomItems.value.map((i) => i.id)
  }
}
const toggleAllStep = () => {
  if (allStepChecked.value) {
    selectedStepIds.value = []
  } else {
    selectedStepIds.value = routingSteps.value.map((i) => i.id)
  }
}

const search = async () => {
  const code = productCode.value.trim()
  if (!code) return
  loading.value = true
  errorMsg.value = ''
  product.value = null
  bomItems.value = []
  routingSteps.value = []
  selectedBomIds.value = []
  selectedStepIds.value = []
  try {
    const res = await api.sourcingBulkChange.search(code)
    product.value = res.data.product
    newCategory.value = res.data.product.category
    bomItems.value = res.data.bom_items
    routingSteps.value = res.data.routing_steps
    selectedBomIds.value = bomItems.value.map((i) => i.id)
    selectedStepIds.value = routingSteps.value.map((i) => i.id)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || '検索に失敗しました'
  } finally {
    loading.value = false
  }
}

const applyChanges = async () => {
  if (!product.value) return

  const bomChanges = {}
  const routingChanges = {}

  if (newSourcingType.value) bomChanges.sourcing_type = newSourcingType.value
  if (newProcessId.value !== null) {
    const val = newProcessId.value === 0 ? null : newProcessId.value
    bomChanges.process_id = val
    routingChanges.process_id = val
  }
  if (newLineId.value !== null) {
    const val = newLineId.value === 0 ? null : newLineId.value
    bomChanges.line_id = val
    routingChanges.line_id = val
  }
  if (newSupplierId.value !== null) {
    const val = newSupplierId.value === 0 ? null : newSupplierId.value
    bomChanges.supplier_id = val
    routingChanges.supplier_id = val
  }

  const hasBomChanges = selectedBomIds.value.length > 0 && Object.keys(bomChanges).length > 0
  const hasStepChanges = selectedStepIds.value.length > 0 && Object.keys(routingChanges).length > 0
  const hasCategoryChange = newCategory.value !== product.value.category

  if (!hasBomChanges && !hasStepChanges && !hasCategoryChange) {
    errorMsg.value = '変更する項目がありません'
    return
  }

  const msgs = []
  if (hasCategoryChange) msgs.push(`カテゴリ: ${product.value.category} → ${newCategory.value}`)
  if (hasBomChanges) msgs.push(`BOM ${selectedBomIds.value.length}件を更新`)
  if (hasStepChanges) msgs.push(`ルーティング ${selectedStepIds.value.length}件を更新`)

  if (!confirm(`以下の変更を適用しますか？\n\n${msgs.join('\n')}`)) return

  applying.value = true
  errorMsg.value = ''
  try {
    const res = await api.sourcingBulkChange.apply({
      product_id: product.value.id,
      new_category: hasCategoryChange ? newCategory.value : null,
      bom_item_ids: hasBomChanges ? selectedBomIds.value : [],
      routing_step_ids: hasStepChanges ? selectedStepIds.value : [],
      bom_changes: hasBomChanges ? bomChanges : {},
      routing_changes: hasStepChanges ? routingChanges : {},
    })
    alert(`変更完了: BOM ${res.data.bom_updated}件, ルーティング ${res.data.routing_step_updated}件 更新`)
    await search()
  } catch (e) {
    errorMsg.value = e.response?.data?.error || '変更適用に失敗しました'
  } finally {
    applying.value = false
  }
}

onMounted(async () => {
  try {
    const [procRes, lineRes, supRes] = await Promise.all([
      api.processes.getProcesses(),
      api.lines.getLines(),
      api.suppliers.getSuppliers(),
    ])
    processes.value = procRes.data.results || procRes.data
    lines.value = lineRes.data.results || lineRes.data
    suppliers.value = supRes.data.results || supRes.data
  } catch (e) {
    console.error('マスタ取得エラー:', e)
  }
})
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { margin-bottom: 12px; }
.page-title { margin: 0 0 4px; font-size: 20px; }
.subtitle { margin: 0; font-size: 12px; color: #666; }
.body { max-width: 1400px; }

.search-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
}
.search-row label { font-weight: 600; font-size: 13px; white-space: nowrap; }
.filter-input {
  padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; width: 240px; font-size: 13px;
}

.product-info {
  background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px;
  padding: 8px 12px; margin-bottom: 12px; font-size: 13px;
}
.info-label { font-weight: 600; }
.ml { margin-left: 16px; }
.inline-select { padding: 2px 4px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }

.change-panel {
  border: 2px solid #4a90d9; border-radius: 6px; padding: 10px 14px; margin-bottom: 14px;
}
.change-panel legend { font-weight: 700; font-size: 14px; color: #4a90d9; padding: 0 6px; }
.change-fields { display: flex; gap: 16px; flex-wrap: wrap; }
.change-fields .field { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.change-fields .field label { font-weight: 600; white-space: nowrap; }
.change-fields .field select { padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }

.section { margin-bottom: 14px; }
.section h3 { font-size: 14px; margin: 0 0 6px; display: flex; align-items: center; gap: 6px; }
.table-wrap { overflow-x: auto; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; text-align: left; }
.data-table th { background: #f5f5f5; font-weight: 600; white-space: nowrap; }
.data-table .chk-col { width: 30px; text-align: center; }
.data-table .num { text-align: right; }

.no-data { color: #999; font-size: 13px; padding: 8px 0; }
.loading-text { color: #666; padding: 16px 0; }
.error-msg { color: #d32f2f; margin-top: 8px; font-size: 13px; }

.form-actions {
  display: flex; align-items: center; gap: 12px; justify-content: flex-end; margin-top: 8px;
}
.summary { font-size: 13px; color: #555; }
.btn-primary {
  background: #4a90d9; color: #fff; border: none; padding: 8px 20px;
  border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 600;
}
.btn-primary:hover { background: #3a7bc8; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
