<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">ルーティングマスタ</h1>
      <div class="page-actions">
        <select v-model="migrationLineId" class="line-select" :disabled="loadingLines">
          <option value="">ライン選択（在庫移行用）</option>
          <option v-for="line in lines" :key="line.id" :value="line.id">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
        <button
          class="btn-warning"
          @click="openMigrationDialog"
          :disabled="!migrationLineId || checkingMigration"
        >
          {{ checkingMigration ? '確認中...' : 'ルーティング変更後の在庫移行' }}
        </button>
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
      <span v-if="!canEdit" class="readonly-note">閲覧のみ（編集権限なし）</span>
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

        <div v-else>
          <div class="step-filter-row">
            <label>工程</label>
            <select v-model="processFilter">
              <option value="">すべて</option>
              <option v-for="proc in processFilterOptions" :key="proc.value" :value="proc.value">
                {{ proc.label }}
              </option>
            </select>
          </div>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>階層</th>
                  <th>工程番号</th>
                  <th>並列G</th>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>加工後品目</th>
                  <th>代表部品</th>
                  <th>時間単位</th>
                  <th>LT(日)</th>
                  <th>所要時間(分)</th>
                  <th>使用個数</th>
                  <th>親製品</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="step in filteredSteps" :key="step.id">
                  <td>{{ step.hierarchy_path || '-' }}</td>
                  <td>{{ step.step_no }}</td>
                  <td>{{ step.parallel_group }}</td>
                  <td>{{ step.process_name || step.process || '-' }}</td>
                  <td>{{ step.line_name || step.line || '-' }}</td>
                  <td>{{ step.output_product_code || '-' }}</td>
                  <td>{{ isRepresentativePart(step) ? '○' : '' }}</td>
                  <td>{{ displayTimeUnit(step.time_unit) }}</td>
                  <td>{{ step.lead_time_days ?? '' }}</td>
                  <td>
                    <div class="duration-editor">
                      <template v-if="isMinuteStep(step)">
                        <input
                          v-model.number="durationDraftByStepId[step.id]"
                          type="number"
                          min="1"
                          step="1"
                          class="duration-input"
                          :disabled="!canEdit || savingDurationStepId === step.id"
                          @keydown.enter.prevent="saveDuration(step)"
                        />
                        <button
                          class="duration-save-btn"
                          :disabled="!canEdit || !isDurationDirty(step) || savingDurationStepId === step.id"
                          @click="saveDuration(step)"
                        >
                          {{ savingDurationStepId === step.id ? '保存中' : '保存' }}
                        </button>
                      </template>
                      <span v-else>{{ step.duration_min ?? '' }}</span>
                    </div>
                  </td>
                  <td>{{ usageQuantity(step) }}</td>
                  <td>{{ step.remark || '' }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!loadingSteps && filteredSteps.length === 0" class="empty-state">
              工程がありません
            </div>
          </div>
        </div>
      </section>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <!-- ルーティング変更在庫移行ダイアログ -->
    <div v-if="migrationDialogVisible" class="migration-overlay">
      <div class="migration-dialog">
        <h3 class="migration-title">⚠ ルーティング変更による在庫移行の確認</h3>
        <p class="migration-desc">
          以下の品番でルーティング変更が検出されました。<br>
          旧ラインの在庫を新ラインへ移行しますか？
        </p>
        <div class="migration-date-row">
          <label>移行基準日</label>
          <input type="date" v-model="migrationDate" class="migration-date-input" />
        </div>
        <table class="migration-table">
          <thead>
            <tr>
              <th>移行</th>
              <th>品番</th>
              <th>品名</th>
              <th>旧ライン / 旧工程</th>
              <th>新ライン / 新工程</th>
              <th>現在在庫</th>
              <th>移行数量</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in migrationCandidates" :key="item.product_id">
              <td><input type="checkbox" v-model="item.checked" /></td>
              <td>{{ item.product_code }}</td>
              <td>{{ item.product_name }}</td>
              <td>{{ item.old_line_code }} / {{ item.old_process_code }}</td>
              <td>{{ item.new_line_code }} / {{ item.new_process_code }}</td>
              <td class="qty-cell">{{ item.stock_qty }}</td>
              <td>
                <input
                  v-if="item.checked"
                  type="number"
                  v-model.number="item.migrate_qty"
                  :max="item.stock_qty"
                  min="0"
                  class="migrate-qty-input"
                />
                <span v-else>-</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="migration-note">
          ※ 実績(actual_qty)は旧ラインに残ります<br>
          ※ 移行はadjust_qtyへの加減算で行われます（在庫再計算後に反映）
        </p>
        <div class="migration-actions">
          <button class="btn-secondary" @click="migrationDialogVisible = false">キャンセル</button>
          <button
            class="btn-primary"
            @click="executeMigration"
            :disabled="executingMigration"
          >{{ executingMigration ? '移行中...' : '移行実行' }}</button>
        </div>
      </div>
    </div>

    <!-- 孤立在庫なし通知 -->
    <div v-if="noMigrationMessage" class="migration-overlay" @click="noMigrationMessage = false">
      <div class="migration-dialog migration-dialog--small">
        <h3 class="migration-title" style="color: #15803d">✓ 移行対象なし</h3>
        <p class="migration-desc">ルーティング変更による孤立在庫は見つかりませんでした。</p>
        <div class="migration-actions">
          <button class="btn-primary" @click="noMigrationMessage = false">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

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
const durationDraftByStepId = ref({})
const savingDurationStepId = ref(null)
const processFilter = ref('')
const representativeChildProductIds = ref(new Set())

// 在庫移行機能
const lines = ref([])
const loadingLines = ref(false)
const migrationLineId = ref('')
const _nowJst = new Date(Date.now() + 9 * 60 * 60 * 1000)
const migrationDate = ref(_nowJst.toISOString().slice(0, 10))
const migrationDialogVisible = ref(false)
const migrationCandidates = ref([])
const checkingMigration = ref(false)
const executingMigration = ref(false)
const noMigrationMessage = ref(false)

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
const canEdit = computed(() => hasPermission(authState.user, 'masters', 'edit'))

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

const processFilterOptions = computed(() => {
  const map = new Map()
  sortedSteps.value.forEach((step) => {
    if (!step?.process) return
    if (!map.has(String(step.process))) {
      map.set(String(step.process), step.process_name || String(step.process))
    }
  })
  return Array.from(map.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ja'))
})

const filteredSteps = computed(() => {
  if (!processFilter.value) return sortedSteps.value
  return sortedSteps.value.filter((step) => String(step.process) === String(processFilter.value))
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

const isRepresentativePart = (step) => {
  if (!step?.output_product) return false
  return representativeChildProductIds.value.has(Number(step.output_product))
}

const collectRepresentativeParentIds = (stepList, routing) => {
  const parentIds = new Set()
  const stepCodeToProductId = new Map()
  const productCodeToProductId = new Map()

  Object.values(productsById.value).forEach((product) => {
    const pid = Number(product?.id)
    const pcode = String(product?.product_code || '').trim()
    if (Number.isFinite(pid) && pid > 0 && pcode) {
      productCodeToProductId.set(pcode, pid)
    }
  })

  stepList.forEach((step) => {
    const pid = Number(step?.output_product)
    const pcode = String(step?.output_product_code || '').trim()
    if (Number.isFinite(pid) && pid > 0 && pcode) {
      stepCodeToProductId.set(pcode, pid)
    }
  })

  const rootProductId = Number(routing?.product)
  if (Number.isFinite(rootProductId) && rootProductId > 0) {
    parentIds.add(rootProductId)
  }

  stepList.forEach((step) => {
    const parentCode = String(step?.remark || '').trim()
    if (!parentCode) return
    const parentId = stepCodeToProductId.get(parentCode) || productCodeToProductId.get(parentCode)
    if (Number.isFinite(parentId) && parentId > 0) {
      parentIds.add(parentId)
    }
  })

  return Array.from(parentIds)
}

const fetchRepresentativeChildSet = async (stepList, routing) => {
  const targetChildIds = new Set(
    stepList
      .map((step) => Number(step?.output_product))
      .filter((id) => Number.isFinite(id) && id > 0)
  )
  if (!targetChildIds.size) return new Set()

  const parentIds = collectRepresentativeParentIds(stepList, routing)
  if (!parentIds.length) return new Set()

  const representativeSet = new Set()

  for (const parentId of parentIds) {
    try {
      const bomRes = await api.boms.getBOMs({
        parent_product: parentId,
        is_coproduct: true,
        page_size: 100,
      })
      const bomRows = normalizeList(bomRes?.data)
      for (const bomRow of bomRows) {
        let bomItems = Array.isArray(bomRow?.items) ? bomRow.items : []
        if (!bomItems.length && bomRow?.id) {
          try {
            const detailRes = await api.boms.getBOM(bomRow.id)
            bomItems = Array.isArray(detailRes?.data?.items) ? detailRes.data.items : []
          } catch (detailError) {
            console.warn('連産品BOM明細取得エラー:', { parentId, bomId: bomRow.id, detailError })
            continue
          }
        }
        bomItems.forEach((item) => {
          const childId = Number(item?.child_product)
          if (!Number.isFinite(childId) || !targetChildIds.has(childId)) return
          if (item?.is_coproduct_driver === true) {
            representativeSet.add(childId)
          }
        })
      }
    } catch (error) {
      console.warn('連産品BOM取得エラー:', { parentId, error })
    }
  }

  return representativeSet
}

const resetDurationDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = step.duration_min ?? ''
  })
  durationDraftByStepId.value = draftMap
}

const isMinuteStep = (step) => step?.time_unit === 'MINUTE'

const parseDuration = (value) => {
  if (value === '' || value === null || value === undefined) return null
  const num = Number(value)
  if (!Number.isFinite(num) || !Number.isInteger(num)) return null
  if (num <= 0) return null
  return num
}

const isDurationDirty = (step) => {
  const draft = durationDraftByStepId.value[step.id]
  const current = step.duration_min
  if (draft === '' || draft === null || draft === undefined) {
    return !(current === '' || current === null || current === undefined)
  }
  return String(draft) !== String(current ?? '')
}

const saveDuration = async (step) => {
  if (!canEdit.value || !isMinuteStep(step) || !step?.id) return
  if (!isDurationDirty(step)) return

  const duration = parseDuration(durationDraftByStepId.value[step.id])
  if (duration === null) {
    alert('所要時間(分)は1以上の整数で入力してください。')
    return
  }

  savingDurationStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { duration_min: duration })
    step.duration_min = duration
    durationDraftByStepId.value[step.id] = duration
  } catch (error) {
    console.error('所要時間更新エラー:', error)
    const detail = error?.response?.data?.detail || '所要時間の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingDurationStepId.value === step.id) {
      savingDurationStepId.value = null
    }
  }
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
  processFilter.value = ''
  representativeChildProductIds.value = new Set()

  try {
    const stepRes = await api.routings.getRoutingSteps({ routing: routingId, page_size: 5000 })
    const routingIdNum = Number(routingId)
    const stepList = normalizeList(stepRes.data).filter(
      (step) => Number(step.routing) === routingIdNum
    )
    if (stepLoadToken.value !== token) return
    steps.value = stepList
    resetDurationDrafts(stepList)

    // ルーティングID一括取得（ステップ数分のN+1リクエストを回避）
    // routing 指定時はサーバー側でページネーション無効化のため page_size 不要
    const routing = routings.value.find((item) => item.id === routingId)
    const [matRes, representativeSet, bomQuantityMap] = await Promise.all([
      api.routings.getRoutingStepMaterials({ routing: routingId }),
      fetchRepresentativeChildSet(stepList, routing),
      fetchBomQuantityMap(routing),
    ])
    if (stepLoadToken.value !== token) return

    const allMaterials = normalizeList(matRes.data)
    const materialMap = {}
    allMaterials.forEach((mat) => {
      const sid = mat.routing_step
      if (!materialMap[sid]) materialMap[sid] = []
      materialMap[sid].push(mat)
    })
    materialsByStepId.value = materialMap
    representativeChildProductIds.value = representativeSet
    bomQuantityByChildId.value = bomQuantityMap
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
    representativeChildProductIds.value = new Set()
    durationDraftByStepId.value = {}
    processFilter.value = ''
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

const fetchLines = async () => {
  loadingLines.value = true
  try {
    const res = await api.lines.getLines({ page_size: 500 })
    lines.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('ライン一覧取得エラー', e)
  } finally {
    loadingLines.value = false
  }
}

const openMigrationDialog = async () => {
  if (!migrationLineId.value) return
  checkingMigration.value = true
  try {
    const res = await api.lineBacklogs.detectStockMigration({ line_id: migrationLineId.value })
    const candidates = res.data || []
    if (candidates.length === 0) {
      noMigrationMessage.value = true
      return
    }
    migrationCandidates.value = candidates.map((c) => ({ ...c, migrate_qty: c.stock_qty, checked: true }))
    migrationDialogVisible.value = true
  } catch (e) {
    console.error('在庫移行検出エラー', e)
    alert('孤立在庫の検出に失敗しました。')
  } finally {
    checkingMigration.value = false
  }
}

const executeMigration = async () => {
  executingMigration.value = true
  try {
    const items = migrationCandidates.value
      .filter((c) => c.checked && c.migrate_qty > 0)
      .map((c) => ({
        product_id: c.product_id,
        old_line_id: c.old_line_id,
        old_process_id: c.old_process_id,
        new_line_id: c.new_line_id,
        new_process_id: c.new_process_id,
        migrate_qty: c.migrate_qty,
      }))
    if (items.length === 0) {
      migrationDialogVisible.value = false
      return
    }
    const res = await api.lineBacklogs.executeStockMigration({ migration_date: migrationDate.value, items })
    migrationDialogVisible.value = false
    const count = res.data?.count ?? items.length
    alert(`在庫移行が完了しました。${count}件`)
  } catch (e) {
    const detail = e?.response?.data?.detail || '在庫移行に失敗しました。'
    console.error('在庫移行実行エラー', e)
    alert(`エラー: ${detail}`)
  } finally {
    executingMigration.value = false
  }
}

onMounted(async () => {
  await Promise.all([refreshAll(), fetchLines()])
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

.readonly-note {
  color: #b45309;
  font-size: 12px;
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

.step-filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #eceff5;
  background: #fafbfc;
}

.step-filter-row label {
  font-size: 13px;
  color: #374151;
}

.step-filter-row select {
  min-width: 180px;
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
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

.duration-editor {
  display: flex;
  align-items: center;
  gap: 6px;
}

.duration-input {
  width: 80px;
  padding: 2px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  text-align: right;
}

.duration-save-btn {
  padding: 2px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f9fafb;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
}

.duration-save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.line-select {
  padding: 6px 10px;
  border: 1px solid #d5d7dd;
  border-radius: 6px;
  font-size: 13px;
  min-width: 220px;
}

.btn-warning {
  padding: 6px 14px;
  background: #d97706;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn-warning:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 6px 14px;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

/* 在庫移行ダイアログ */
.migration-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2100;
}
.migration-dialog {
  background: #fff;
  border-radius: 10px;
  padding: 24px 28px;
  max-width: 820px;
  width: 95%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  max-height: 80vh;
  overflow-y: auto;
}
.migration-dialog--small {
  max-width: 400px;
}
.migration-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
  color: #b45309;
}
.migration-desc {
  font-size: 13px;
  color: #374151;
  margin: 0 0 12px;
  line-height: 1.6;
}
.migration-date-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-size: 13px;
}
.migration-date-input {
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.migration-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 12px;
}
.migration-table th {
  background: #f3f4f6;
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid #d1d5db;
  white-space: nowrap;
}
.migration-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: middle;
}
.qty-cell {
  text-align: right;
  font-weight: 600;
}
.migrate-qty-input {
  width: 70px;
  padding: 2px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  text-align: right;
  font-size: 12px;
}
.migration-note {
  font-size: 11px;
  color: #6b7280;
  margin: 0 0 16px;
  line-height: 1.6;
}
.migration-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 1400px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}
</style>
