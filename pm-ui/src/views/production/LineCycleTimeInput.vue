<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">ラインサイクルタイム入力 <DataSourceDialog title="ラインサイクルタイム入力" :sources="dsSources" /></h1>
        <p class="helper-text">長期負荷計算用: ルーティングから自動抽出した完成品 × 工程のサイクルタイム(秒/個)を登録</p>
      </div>
      <div class="page-actions">
        <router-link to="/production/actual-cycle-time" class="btn-secondary">出来高集計</router-link>
        <router-link to="/production/line-load-chart" class="btn-secondary">負荷チャート</router-link>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field">
            <label>ライン</label>
            <select v-model="selectedLineId" @change="onLineChange">
              <option :value="null">-- 選択 --</option>
              <option v-for="line in prodLines" :key="line.id" :value="line.id">
                {{ line.line_code }} {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="filter-field wide">
            <label>品番/品名検索</label>
            <input v-model="searchText" placeholder="品番・品名で絞込" />
          </div>
          <label class="filter-check">
            <input v-model="showMissingOnly" type="checkbox" />
            未入力のみ
          </label>
          <div class="filter-actions">
            <button
              class="btn-fetch"
              :disabled="!selectedLineId || loading || fetching"
              @click="fetchActualCT"
            >{{ fetching ? '取得中...' : '出来高CT取得' }}</button>
            <button class="btn-primary" :disabled="!dirty || saving" @click="saveAll">
              {{ saving ? '保存中...' : `一括保存 (${changedCount}件)` }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="loading" class="empty-state">読込中...</div>

      <div v-else-if="selectedLineId && matrixProcesses.length" class="table-wrapper">
        <div class="summary-bar">
          <span>完成品: {{ filteredProducts.length }} / {{ matrixProducts.length }}品</span>
          <span>工程: {{ matrixProcesses.length }}</span>
          <span>登録済セル: {{ registeredCount }}</span>
        </div>
        <table class="data-table compact">
          <thead>
            <tr>
              <th class="sticky-col col-name">品名</th>
              <th class="col-code col-code-right">品番</th>
              <th
                v-for="proc in matrixProcesses"
                :key="proc.id"
                class="col-ct"
                :title="proc.process_name"
              >{{ proc.process_code }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(product, rowIdx) in filteredProducts"
              :key="product.id"
              :class="{ 'row-editing': activeRow === rowIdx }"
            >
              <td class="sticky-col col-name" :title="product.product_name">{{ product.product_name }}</td>
              <td class="col-code col-code-right">{{ product.product_code }}</td>
              <td v-for="(proc, colIdx) in matrixProcesses" :key="proc.id" class="col-ct">
                <input
                  v-if="hasRelation(product.id, proc.id)"
                  type="number"
                  step="0.01"
                  min="0"
                  class="ct-input"
                  :class="{ changed: isCellChanged(product.id, proc.id) }"
                  :value="getCellValue(product.id, proc.id)"
                  :data-row="rowIdx"
                  :data-col="colIdx"
                  @input="onCellInput(product.id, proc.id, $event)"
                  @focus="activeRow = rowIdx"
                  @keydown="onCellKeydown($event, rowIdx, colIdx)"
                />
                <span v-else class="no-relation">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="selectedLineId && !loading" class="empty-state">
        このラインに紐づくルーティング（完成品）がありません
      </div>
      <div v-else class="empty-state">
        ラインを選択してください
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 'm_line', desc: '対象ライン選択' },
  { op: '参照', table: 'm_routing / m_routing_step', desc: '現行ルーティングから完成品×工程マトリクスを生成' },
  { op: '読み書き', table: 'm_line_cycle_time', desc: '長期負荷計算用のライン別CT（秒/個）' },
  { op: '参照', table: 't_finished_product_cycle_time', desc: '出来高CT取得ボタンの反映元' },
]

const prodLines = ref([])
const matrixProducts = ref([])
const matrixProcesses = ref([])
const productProcessSet = ref(new Set())
const selectedLineId = ref(null)
const searchText = ref('')
const showMissingOnly = ref(false)
const loading = ref(false)
const saving = ref(false)
const fetching = ref(false)
const activeRow = ref(-1)

const editedValues = reactive({})
const originalValues = reactive({})

onMounted(async () => {
  const res = await api.lines.getLines({ is_active: true, line_type: 'PROD' })
  prodLines.value = (res.data.results || res.data).sort((a, b) => a.line_code.localeCompare(b.line_code))
})

const onLineChange = async () => {
  if (!selectedLineId.value) {
    matrixProducts.value = []
    matrixProcesses.value = []
    productProcessSet.value = new Set()
    return
  }
  Object.keys(editedValues).forEach(k => delete editedValues[k])
  Object.keys(originalValues).forEach(k => delete originalValues[k])

  loading.value = true
  try {
    const res = await api.lineCycleTimes.matrix(selectedLineId.value)
    const data = res.data
    matrixProducts.value = data.products
    matrixProcesses.value = data.processes
    productProcessSet.value = new Set(
      data.product_processes.map(pp => `${pp.product}_${pp.process}`)
    )
    for (const [key, val] of Object.entries(data.existing)) {
      originalValues[key] = val
      editedValues[key] = val
    }
  } catch (e) {
    alert('読込エラー: ' + (e.response?.data?.detail || e.message))
    matrixProducts.value = []
    matrixProcesses.value = []
  } finally {
    loading.value = false
  }
}

const filteredProducts = computed(() => {
  const q = searchText.value.toLowerCase()
  return matrixProducts.value.filter((p) => {
    const matchesSearch = !q ||
      p.product_code.toLowerCase().includes(q) ||
      (p.product_name || '').toLowerCase().includes(q)
    if (!matchesSearch) return false
    if (!showMissingOnly.value) return true
    return hasMissingCycleTime(p.id)
  })
})

const registeredCount = computed(() => {
  return Object.keys(originalValues).length
})

const changedCount = computed(() => {
  let count = 0
  for (const key in editedValues) {
    const cur = editedValues[key]
    if (cur === undefined || cur === '' || cur === null) continue
    const orig = originalValues[key]
    if (orig === undefined || orig === null || String(orig) !== String(cur)) count++
  }
  return count
})

const dirty = computed(() => changedCount.value > 0)

const hasRelation = (productId, processId) => {
  return productProcessSet.value.has(`${productId}_${processId}`)
}

const hasMissingCycleTime = (productId) => {
  return matrixProcesses.value.some((proc) => {
    if (!hasRelation(productId, proc.id)) return false
    const val = editedValues[`${productId}_${proc.id}`]
    return val === undefined || val === null || val === ''
  })
}

const getCellValue = (productId, processId) => {
  const val = editedValues[`${productId}_${processId}`]
  return val !== undefined && val !== null ? val : ''
}

const isCellChanged = (productId, processId) => {
  const key = `${productId}_${processId}`
  const cur = editedValues[key]
  if (cur === undefined || cur === '' || cur === null) return false
  const orig = originalValues[key]
  return orig === undefined || orig === null || String(orig) !== String(cur)
}

const focusCell = (row, col) => {
  const el = document.querySelector(`.ct-input[data-row="${row}"][data-col="${col}"]`)
  if (el) { el.focus(); el.select() }
}

const onCellKeydown = (event, row, col) => {
  const maxRow = filteredProducts.value.length - 1
  const maxCol = matrixProcesses.value.length - 1
  if (event.key === 'Enter' || event.key === 'ArrowDown') {
    event.preventDefault()
    if (row < maxRow) focusCell(row + 1, col)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (row > 0) focusCell(row - 1, col)
  } else if (event.key === 'Tab' || event.key === 'ArrowRight') {
    if (event.key === 'Tab' && event.shiftKey) return
    if (event.key === 'ArrowRight') {
      const input = event.target
      if (input.selectionStart !== input.value.length) return
    }
    event.preventDefault()
    if (col < maxCol) {
      focusCell(row, col + 1)
    } else if (row < maxRow) {
      focusCell(row + 1, 0)
    }
  } else if (event.key === 'ArrowLeft') {
    const input = event.target
    if (input.selectionStart !== 0) return
    event.preventDefault()
    if (col > 0) {
      focusCell(row, col - 1)
    } else if (row > 0) {
      focusCell(row - 1, maxCol)
    }
  }
}

const onCellInput = (productId, processId, event) => {
  const key = `${productId}_${processId}`
  const val = event.target.value
  editedValues[key] = val === '' ? undefined : val
}

const fetchActualCT = async () => {
  if (!selectedLineId.value) return
  fetching.value = true
  try {
    const res = await api.actualCycleTimes.latestForLine(selectedLineId.value)
    const values = res.data.values || {}
    let filled = 0
    for (const [key, info] of Object.entries(values)) {
      if (!productProcessSet.value.has(key)) continue
      const newVal = String(info.cycle_time_sec)
      const orig = originalValues[key]
      if (orig !== undefined && orig !== null && String(orig) === newVal) continue
      editedValues[key] = newVal
      filled++
    }
    if (filled > 0) {
      alert(`${filled}セルに出来高CTを反映しました（期間: ${Object.values(values)[0]?.calc_from_date} ~ ${Object.values(values)[0]?.calc_to_date}）\n「一括保存」で確定してください`)
    } else if (res.data.count > 0) {
      alert('このラインのルーティングに一致する完成品CTがありませんでした')
    } else {
      alert('このラインの保存済み完成品CTがありません。先に出来高集計で計算・保存してください')
    }
  } catch (e) {
    alert('取得エラー: ' + (e.response?.data?.error || e.message))
  } finally {
    fetching.value = false
  }
}

const saveAll = async () => {
  const items = []
  for (const key in editedValues) {
    const val = editedValues[key]
    if (val === undefined || val === '' || val === null) continue
    const orig = originalValues[key]
    if (orig !== undefined && orig !== null && String(orig) === String(val)) continue
    const [productId, processId] = key.split('_').map(Number)
    items.push({
      product: productId,
      line: selectedLineId.value,
      process: processId,
      cycle_time_sec: parseFloat(val),
    })
  }
  if (!items.length) return
  saving.value = true
  try {
    const res = await api.lineCycleTimes.bulkUpsert(items)
    alert(`保存完了: 新規${res.data.created}件, 更新${res.data.updated}件`)
    await onLineChange()
  } catch (e) {
    alert('保存エラー: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.page-title { font-size: 18px; font-weight: 700; margin: 0; }
.helper-text { font-size: 12px; color: #888; margin: 2px 0 0; }
.page-actions { display: flex; gap: 8px; }
.page-content { display: flex; flex-direction: column; gap: 8px; }

.filter-bar { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 10px 12px; }
.filter-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.filter-field { display: flex; flex-direction: column; gap: 2px; }
.filter-field.wide { flex: 1; }
.filter-field label { font-size: 11px; font-weight: 600; color: #666; }
.filter-field input, .filter-field select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
.filter-check { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #333; padding-bottom: 4px; }
.filter-actions { display: flex; gap: 6px; }

.summary-bar { font-size: 12px; color: #666; display: flex; gap: 16px; padding: 4px 0; }

.btn-fetch { padding: 5px 14px; background: #e67e22; color: #fff; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.btn-fetch:disabled { opacity: 0.6; cursor: default; }
.btn-primary { padding: 5px 14px; background: #3498db; color: #fff; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.btn-secondary { padding: 5px 14px; background: #fff; color: #333; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; cursor: pointer; text-decoration: none; }

.table-wrapper { overflow: auto; max-height: calc(100vh - 220px); border: 1px solid #dee2e6; border-radius: 4px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { padding: 3px 6px; border: 1px solid #e0e0e0; white-space: nowrap; }
.data-table thead th { background: #f0f2f5; position: sticky; top: 0; z-index: 2; font-weight: 600; text-align: center; }
.sticky-col { position: sticky; left: 0; z-index: 1; background: #fff; }
.data-table thead .sticky-col { z-index: 3; background: #f0f2f5; }
.col-code { min-width: 100px; max-width: 140px; }
.col-code-right { text-align: right; }
.col-name { min-width: 120px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.col-ct { width: 80px; text-align: left; padding: 1px !important; }

.ct-input {
  width: 100%; border: 1px solid #ddd; background: #fff; text-align: left;
  font-size: 12px; padding: 2px 4px; outline: none; box-sizing: border-box;
  border-radius: 2px;
}
.ct-input:focus { background: #eef6ff; border-color: #3498db; }
.ct-input.changed { background: #fff3cd; font-weight: 600; border-color: #f0ad4e; }
.ct-input::-webkit-inner-spin-button { display: none; }

.row-editing td { background: #e8f5e9 !important; }
.row-editing .sticky-col { background: #e8f5e9 !important; }
.no-relation { color: #ccc; font-size: 11px; }

.empty-state { text-align: center; color: #999; padding: 40px; font-size: 14px; }
</style>
