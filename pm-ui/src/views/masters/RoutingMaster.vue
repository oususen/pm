<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">ルーティングマスタ</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="refreshAll" :disabled="loadingRoutings || loadingSteps">
          更新
        </button>
      </div>
    </div>

    <div class="filter-row">
      <input
        v-model.trim="searchText"
        class="search-input"
        placeholder="品番コード / 品名 / ルーティングコードで検索"
      />
      <label class="checkbox-inline">
        <input v-model="onlyActive" type="checkbox" />
        有効のみ
      </label>
      <span class="count-text">表示件数: {{ filteredRoutings.length }}</span>
    </div>

    <div class="split-layout">
      <section class="panel routing-panel">
        <h2 class="panel-title">ルーティング一覧</h2>
        <div class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>品番</th>
                <th>品名</th>
                <th>既定</th>
                <th>有効</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="routing in filteredRoutings"
                :key="routing.id"
                :class="{ selected: selectedRoutingId === routing.id }"
                @click="selectRouting(routing.id)"
              >
                <td>{{ productCode(routing) }}</td>
                <td>{{ productName(routing) }}</td>
                <td>{{ routing.is_default ? '○' : '' }}</td>
                <td>{{ routing.is_active ? '有効' : '無効' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!loadingRoutings && filteredRoutings.length === 0" class="empty-state">
            該当データがありません
          </div>
        </div>
      </section>

      <section class="panel step-panel">
        <h2 class="panel-title">
          工程一覧
          <span v-if="selectedRouting" class="panel-subtitle">
            {{ productCode(selectedRouting) }} / {{ selectedRouting.routing_code }}
          </span>
        </h2>

        <div v-if="!selectedRouting" class="empty-state">
          左の一覧からルーティングを選択してください
        </div>

        <div v-else class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>階層</th>
                <th>工程番号</th>
                <th>並列G</th>
                <th>工程</th>
                <th>ライン</th>
                <th>加工後品目</th>
                <th>時間単位</th>
                <th>LT(日)</th>
                <th>所要時間(分)</th>
                <th>使用個数</th>
                <th>親製品</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="step in sortedSteps" :key="step.id">
                <td>{{ step.hierarchy_path || '-' }}</td>
                <td>{{ step.step_no }}</td>
                <td>{{ step.parallel_group }}</td>
                <td>{{ step.process_name || step.process || '-' }}</td>
                <td>{{ step.line_name || step.line || '-' }}</td>
                <td>{{ step.output_product_code || '-' }}</td>
                <td>{{ displayTimeUnit(step.time_unit) }}</td>
                <td>{{ step.lead_time_days ?? '' }}</td>
                <td>{{ step.duration_min ?? '' }}</td>
                <td>{{ usageQuantity(step) }}</td>
                <td>{{ step.remark || '' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!loadingSteps && sortedSteps.length === 0" class="empty-state">
            工程がありません
          </div>
        </div>
      </section>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'

const routings = ref([])
const productsById = ref({})
const selectedRoutingId = ref(null)
const steps = ref([])
const materialsByStepId = ref({})
const bomQuantityByChildId = ref({})
const searchText = ref('')
const onlyActive = ref(true)
const loadingRoutings = ref(false)
const loadingSteps = ref(false)
const errorMessage = ref('')
const stepLoadToken = ref(0)

const normalizeList = (payload) => payload?.results || payload || []

const toPathNumbers = (path) => {
  if (!path) return []
  return String(path)
    .split('.')
    .map((part) => Number(part))
    .filter((num) => Number.isFinite(num))
}

const compareSteps = (a, b) => {
  const left = toPathNumbers(a.hierarchy_path)
  const right = toPathNumbers(b.hierarchy_path)
  const maxLen = Math.max(left.length, right.length)
  for (let i = 0; i < maxLen; i += 1) {
    const lv = left[i] ?? -1
    const rv = right[i] ?? -1
    if (lv !== rv) return lv - rv
  }
  if ((a.step_no ?? 0) !== (b.step_no ?? 0)) return (a.step_no ?? 0) - (b.step_no ?? 0)
  return (a.parallel_group ?? 0) - (b.parallel_group ?? 0)
}

const productCode = (routing) => productsById.value[routing.product]?.product_code || ''
const productName = (routing) => {
  const product = productsById.value[routing.product]
  return product?.product_name || routing.product_name || ''
}

const selectedRouting = computed(() => routings.value.find((r) => r.id === selectedRoutingId.value) || null)

const filteredRoutings = computed(() => {
  const q = searchText.value.toLowerCase()
  return routings.value.filter((routing) => {
    if (onlyActive.value && !routing.is_active) return false
    if (!q) return true
    const text = [
      routing.routing_code,
      productCode(routing),
      productName(routing),
    ].join(' ').toLowerCase()
    return text.includes(q)
  })
})

const sortedSteps = computed(() => {
  return [...steps.value].sort((a, b) => {
    const stepDiff = Number(a.step_no ?? 0) - Number(b.step_no ?? 0)
    if (stepDiff !== 0) return stepDiff
    const groupDiff = Number(a.parallel_group ?? 0) - Number(b.parallel_group ?? 0)
    if (groupDiff !== 0) return groupDiff
    return Number(a.id ?? 0) - Number(b.id ?? 0)
  })
})

const displayTimeUnit = (timeUnit) => {
  if (timeUnit === 'MINUTE') return '分'
  if (timeUnit === 'DAY') return '日'
  return timeUnit || ''
}

const formatQuantity = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return Number.isInteger(num) ? String(num) : String(num)
}

const usageQuantity = (step) => {
  if (!step?.output_product) return ''
  if (step.usage_quantity !== undefined && step.usage_quantity !== null && step.usage_quantity !== '') {
    return formatQuantity(step.usage_quantity)
  }

  if (step.hierarchy_path && step.hierarchy_path.includes('.')) {
    const parentPath = step.hierarchy_path.split('.').slice(0, -1).join('.')
    const parentStep = steps.value.find((item) => item.hierarchy_path === parentPath)
    if (parentStep) {
      const parentMaterials = materialsByStepId.value[parentStep.id] || []
      const material = parentMaterials.find((item) => item.component === step.output_product)
      if (material) return formatQuantity(material.quantity)
    }
  }

  if (step.remark) {
    const fallbackParent = steps.value.find((item) => item.output_product_code === step.remark)
    if (fallbackParent) {
      const parentMaterials = materialsByStepId.value[fallbackParent.id] || []
      const material = parentMaterials.find((item) => item.component === step.output_product)
      if (material) return formatQuantity(material.quantity)
    }
  }

  return formatQuantity(bomQuantityByChildId.value[step.output_product])
}

const fetchProducts = async () => {
  const allProducts = await api.products.getAllProducts()
  const map = {}
  allProducts.forEach((product) => {
    map[product.id] = product
  })
  productsById.value = map
}

const fetchRoutings = async () => {
  loadingRoutings.value = true
  try {
    const res = await api.routings.getRoutings({ page_size: 5000 })
    const list = normalizeList(res.data)
    routings.value = list

    if (!selectedRoutingId.value && list.length > 0) {
      selectedRoutingId.value = list[0].id
    }
  } finally {
    loadingRoutings.value = false
  }
}

const fetchBomQuantityMap = async (routing) => {
  if (!routing?.product) return {}
  const bomRes = await api.boms.getBOMs({
    parent_product: routing.product,
    is_active: true,
    page_size: 200,
  })
  const bomList = normalizeList(bomRes.data)
  if (bomList.length === 0) return {}

  const latestBom = [...bomList].sort((a, b) => {
    const av = `${a.valid_from || ''}#${a.id || 0}`
    const bv = `${b.valid_from || ''}#${b.id || 0}`
    return av < bv ? 1 : -1
  })[0]
  if (!latestBom?.id) return {}

  const itemRes = await api.boms.getBOMItems({ bom: latestBom.id })
  const items = normalizeList(itemRes.data)
  const map = {}
  items.forEach((item) => {
    map[item.child_product] = item.quantity
  })
  return map
}

const fetchStepsAndMaterials = async (routingId) => {
  const token = Date.now()
  stepLoadToken.value = token
  loadingSteps.value = true
  errorMessage.value = ''

  try {
    const stepRes = await api.routings.getRoutingSteps({ routing: routingId, page_size: 5000 })
    const routingIdNum = Number(routingId)
    const stepList = normalizeList(stepRes.data).filter(
      (step) => Number(step.routing) === routingIdNum
    )
    if (stepLoadToken.value !== token) return
    steps.value = stepList

    const materialCalls = stepList.map(async (step) => {
      const res = await api.routings.getRoutingStepMaterials({ routing_step: step.id, page_size: 5000 })
      return { stepId: step.id, materials: normalizeList(res.data) }
    })
    const materialResults = await Promise.all(materialCalls)
    if (stepLoadToken.value !== token) return
    const materialMap = {}
    materialResults.forEach(({ stepId, materials }) => {
      materialMap[stepId] = materials
    })
    materialsByStepId.value = materialMap

    const routing = routings.value.find((item) => item.id === routingId)
    bomQuantityByChildId.value = await fetchBomQuantityMap(routing)
  } catch (error) {
    console.error('ルーティング工程取得エラー:', error)
    errorMessage.value = 'ルーティング工程の取得に失敗しました'
  } finally {
    if (stepLoadToken.value === token) {
      loadingSteps.value = false
    }
  }
}

const selectRouting = async (routingId) => {
  if (!routingId) return
  if (selectedRoutingId.value === routingId) {
    await fetchStepsAndMaterials(routingId)
    return
  }
  selectedRoutingId.value = routingId
}

const refreshAll = async () => {
  errorMessage.value = ''
  try {
    await Promise.all([fetchProducts(), fetchRoutings()])
  } catch (error) {
    console.error('ルーティングマスタ更新エラー:', error)
    errorMessage.value = 'データ更新に失敗しました'
  }
}

watch(selectedRoutingId, async (routingId) => {
  if (!routingId) {
    steps.value = []
    materialsByStepId.value = {}
    bomQuantityByChildId.value = {}
    return
  }
  await fetchStepsAndMaterials(routingId)
})

watch(filteredRoutings, (list) => {
  if (!list.length) {
    selectedRoutingId.value = null
    return
  }
  if (!list.some((item) => item.id === selectedRoutingId.value)) {
    selectedRoutingId.value = list[0].id
  }
})

onMounted(async () => {
  await refreshAll()
})
</script>

<style scoped>
.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.search-input {
  width: 420px;
  max-width: 100%;
  padding: 8px 10px;
  border: 1px solid #d5d7dd;
  border-radius: 6px;
}

.checkbox-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}

.count-text {
  color: #666;
  font-size: 13px;
}

.split-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 12px;
}

.panel {
  border: 1px solid #dcdfe5;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.panel-title {
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid #eceff5;
  font-size: 16px;
}

.panel-subtitle {
  margin-left: 8px;
  color: #556;
  font-size: 13px;
  font-weight: 400;
}

.table-wrap {
  max-height: 72vh;
  overflow: auto;
}

.step-panel .data-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #d7dce8;
}

.compact th,
.compact td {
  padding: 6px 8px;
  font-size: 13px;
  white-space: nowrap;
}

.routing-panel .compact tbody tr {
  cursor: pointer;
}

.routing-panel .compact tbody tr.selected {
  background: #eaf2ff;
}

.empty-state {
  padding: 16px;
  color: #666;
}

.error-text {
  margin-top: 8px;
  color: #b42318;
}

@media (max-width: 1400px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}
</style>
