<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仕入れ検収</h1>
      <div class="page-actions">
        <select v-model="selectedSupplier" @change="onSupplierChange">
          <option value="">-- 仕入先 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">
            {{ s.supplier_code }} {{ s.supplier_name }}
          </option>
        </select>
        <input type="date" v-model="targetDate" @change="loadReceivingData" />
        <button class="btn-primary" @click="loadReceivingData" :disabled="!selectedSupplier">検収データ取得</button>
        <button v-if="rows.length" class="btn-excel" @click="exportExcel">Excel出力</button>
        <button v-if="selectedSupplier" class="btn-history" @click="toggleHistory">検収履歴</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="selectedSupplier && !loading" class="pattern-info">
        <span class="pattern-label">納入パターン:</span>
        <span class="pattern-value">{{ patternInfo ? `${patternInfo.pattern_name} (${patternInfo.recurrence_type_display})` : '未設定（毎日納入）' }}</span>
        <span v-if="isDeliveryDay" class="delivery-badge yes">本日は納入日</span>
        <span v-else class="delivery-badge no">本日は納入日ではありません</span>
        <span v-if="nextDeliveryDate" class="next-delivery">次回納入日: {{ nextDeliveryDate }}</span>
        <span v-if="rows.length" class="summary-count">{{ filteredRows.length }} / {{ rows.length }}件 / 実績{{ actualCount }}件</span>
      </div>

      <div v-if="rows.length" class="filter-bar">
        <label>品番:
          <input v-model="filterProductCode" class="filter-input" placeholder="部分一致" />
        </label>
        <label>移動先:
          <select v-model="filterDest">
            <option value="">すべて</option>
            <option v-for="o in destOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </label>
        <label>後工程:
          <select v-model="filterNextProcess">
            <option value="">すべて</option>
            <option v-for="o in nextProcessOptions" :key="o" :value="o">{{ o }}</option>
          </select>
        </label>
        <div class="btn-group">
          <span class="filter-label">数変更:</span>
          <button :class="['btn-filter', { active: filterHeld === '' }]" @click="filterHeld = ''">全</button>
          <button :class="['btn-filter', { active: filterHeld === 'yes' }]" @click="filterHeld = 'yes'">有</button>
          <button :class="['btn-filter', { active: filterHeld === 'no' }]" @click="filterHeld = 'no'">無</button>
        </div>
        <div class="btn-group">
          <span class="filter-label">差異:</span>
          <button :class="['btn-filter', { active: filterDiff === '' }]" @click="filterDiff = ''">全</button>
          <button :class="['btn-filter', { active: filterDiff === 'yes' }]" @click="filterDiff = 'yes'">有</button>
          <button :class="['btn-filter', { active: filterDiff === 'no' }]" @click="filterDiff = 'no'">無</button>
        </div>
        <div class="btn-group">
          <span class="filter-label">実績:</span>
          <button :class="['btn-filter', { active: filterActual === '' }]" @click="filterActual = ''">全</button>
          <button :class="['btn-filter', { active: filterActual === 'yes' }]" @click="filterActual = 'yes'">有</button>
          <button :class="['btn-filter', { active: filterActual === 'no' }]" @click="filterActual = 'no'">無</button>
        </div>
      </div>

      <div v-if="loading" class="no-data">読み込み中...</div>

      <table v-if="filteredRows.length" class="data-table">
        <thead>
          <tr>
            <th class="col-code">品番</th>
            <th class="col-name">品名</th>
            <th class="num col-total">予定</th>
            <th class="num col-actual">実績</th>
            <th v-for="d in coverageDates" :key="d" class="num col-date">
              <div>{{ formatDateParts(d).date }}</div>
              <div class="dow">{{ formatDateParts(d).dow }}</div>
            </th>
            <th class="num col-recv">実数</th>
            <th class="num col-diff">差異</th>
            <th class="col-note">備考</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.product_id" :class="{ 'row-held': row.held, 'row-done': !row.held && row.actual_qty > 0 && row.actual_qty === row.expected_qty }">
            <td class="col-code">
              {{ row.product_code }}
              <button class="btn-hold" :class="{ active: row.held }" @click="toggleHold(row)">数変更</button>
            </td>
            <td class="col-name">{{ row.product_name }}</td>
            <td class="num col-total bold">{{ row.expected_qty }}</td>
            <td class="num col-actual">{{ row.actual_qty || '' }}</td>
            <td v-for="d in coverageDates" :key="d" class="num col-date">{{ row.daily[d] || '' }}</td>
            <td class="num col-recv">
              <input type="number" v-model.number="row.received_qty" min="0" class="input-qty" />
            </td>
            <td class="num col-diff" :class="{ 'diff-over': row.expected_qty - (row.actual_qty || 0) < 0, 'diff-short': row.expected_qty - (row.actual_qty || 0) > 0 }">{{ row.actual_qty ? row.expected_qty - row.actual_qty : '' }}</td>
            <td class="col-note">
              <input v-model="row.note" class="input-note" />
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !filteredRows.length && selectedSupplier" class="no-data">
        {{ isDeliveryDay ? '本日の納入予定データがありません' : '本日は納入日ではありません' }}
      </div>

      <div v-if="filteredRows.length" class="form-actions">
        <button v-if="filterHeld !== 'yes'" class="btn-success" @click="saveReceiving" :disabled="saving">検収確定</button>
        <button v-if="filterHeld === 'yes'" class="btn-held-confirm" @click="saveHeldReceiving" :disabled="saving">数変更検収確定</button>
      </div>

      <div v-if="showHistory" class="history-panel">
        <h3 class="history-title">検収履歴</h3>
        <div v-if="historyLoading" class="no-data">読み込み中...</div>
        <table v-else-if="historyRows.length" class="data-table">
          <thead>
            <tr>
              <th>日時</th>
              <th>品番</th>
              <th>品名</th>
              <th class="num">数量</th>
              <th>検収者</th>
              <th>備考</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in historyRows" :key="h.id">
              <td>{{ h.timestamp }}</td>
              <td>{{ h.product_code }}</td>
              <td>{{ h.product_name }}</td>
              <td class="num">{{ h.qty }}</td>
              <td>{{ h.operator_name }}</td>
              <td>{{ h.remarks }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">検収履歴がありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

const suppliers = ref([])
const selectedSupplier = ref('')
const targetDate = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const coverageDates = ref([])
const patternInfo = ref(null)
const isDeliveryDay = ref(false)
const nextDeliveryDate = ref('')

const filterDest = ref('')
const filterNextProcess = ref('')
const filterActual = ref('')
const filterProductCode = ref('')
const filterHeld = ref('')
const filterDiff = ref('')

const destOptions = computed(() => {
  const set = new Set()
  for (const r of rows.value) if (r.transfer_destination) set.add(r.transfer_destination)
  return [...set].sort().map((k) => ({ value: k, label: rows.value.find((r) => r.transfer_destination === k)?.transfer_destination_label || k }))
})
const nextProcessOptions = computed(() => {
  const set = new Set()
  for (const r of rows.value) if (r.next_process_name) set.add(r.next_process_name)
  return [...set].sort()
})
const actualCount = computed(() => rows.value.filter((r) => r.actual_qty).length)
const filteredRows = computed(() => {
  return rows.value.filter((r) => {
    if (filterDest.value && r.transfer_destination !== filterDest.value) return false
    if (filterNextProcess.value && r.next_process_name !== filterNextProcess.value) return false
    if (filterProductCode.value && !r.product_code.toUpperCase().includes(filterProductCode.value.toUpperCase())) return false
    if (filterHeld.value === 'yes' && !r.held) return false
    if (filterHeld.value === 'no' && r.held) return false
    if (filterDiff.value === 'yes' && r.actual_qty && r.actual_qty === r.expected_qty) return false
    if (filterDiff.value === 'no' && (!r.actual_qty || r.actual_qty !== r.expected_qty)) return false
    if (filterActual.value === 'yes' && !r.actual_qty) return false
    if (filterActual.value === 'no' && r.actual_qty) return false
    return true
  })
})

const DAY_NAMES = ['日', '月', '火', '水', '木', '金', '土']
const formatDateParts = (isoStr) => {
  const d = new Date(isoStr + 'T00:00:00')
  return { date: `${d.getMonth() + 1}/${d.getDate()}`, dow: DAY_NAMES[d.getDay()] }
}

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) =>
    (a.supplier_code || '').localeCompare(b.supplier_code || '')
  )
}

const onSupplierChange = () => {
  rows.value = []
  coverageDates.value = []
  patternInfo.value = null
  isDeliveryDay.value = false
  nextDeliveryDate.value = ''
  filterProductCode.value = ''
  filterDest.value = ''
  filterNextProcess.value = ''
  filterHeld.value = ''
  filterDiff.value = ''
  filterActual.value = ''
  if (selectedSupplier.value) loadReceivingData()
}

const loadReceivingData = async () => {
  if (!selectedSupplier.value) return
  loading.value = true
  rows.value = []
  coverageDates.value = []
  patternInfo.value = null
  isDeliveryDay.value = false
  nextDeliveryDate.value = ''
  try {
    const res = await api.client.get('/purchase-receiving/', {
      params: {
        supplier_id: selectedSupplier.value,
        target_date: targetDate.value,
      },
    })
    const data = res.data
    patternInfo.value = data.pattern || null
    isDeliveryDay.value = data.is_delivery_day || false
    nextDeliveryDate.value = data.next_delivery_date || ''
    coverageDates.value = data.coverage_dates || []
    const saved = loadHeldState()
    rows.value = (data.items || []).map((item) => {
      const s = saved[item.product_id]
      return {
        ...item,
        received_qty: s ? s.received_qty : item.expected_qty,
        held: s ? true : false,
        note: s ? s.note : '',
      }
    })
  } catch (e) {
    console.error('検収データ取得エラー', e)
    alert('データの取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const saveReceiving = async () => {
  if (!rows.value.length) return
  const targets = filteredRows.value.filter((r) => !r.held)
  const withActual = targets.filter((r) => r.actual_qty)
  if (withActual.length) {
    const codes = withActual.map((r) => r.product_code).join(', ')
    if (!confirm(`実績がある製品が${withActual.length}件あります:\n${codes}\n\n検収を続行しますか？`)) return
  }
  saving.value = true
  try {
    await api.client.post('/purchase-receiving/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      items: filteredRows.value.filter((r) => !r.held).map((r) => ({
        product_id: r.product_id,
        expected_qty: r.expected_qty,
        received_qty: r.received_qty,
        note: r.note || '',
      })),
    })
    alert('検収を確定しました。')
    saveHeldState()
    await loadReceivingData()
  } catch (e) {
    console.error('検収確定エラー', e)
    alert('検収の確定に失敗しました。')
  } finally {
    saving.value = false
  }
}

const heldStorageKey = () => `receiving_held_${selectedSupplier.value}_${targetDate.value}`
const saveHeldState = () => {
  const state = {}
  for (const r of rows.value) {
    if (r.held) state[r.product_id] = { received_qty: r.received_qty, note: r.note }
  }
  if (Object.keys(state).length) localStorage.setItem(heldStorageKey(), JSON.stringify(state))
  else localStorage.removeItem(heldStorageKey())
}
const loadHeldState = () => {
  try { return JSON.parse(localStorage.getItem(heldStorageKey()) || '{}') } catch { return {} }
}

const hasHeldRows = computed(() => rows.value.some((r) => r.held))

const saveHeldReceiving = async () => {
  const heldItems = filteredRows.value.filter((r) => r.held)
  saving.value = true
  try {
    await api.client.post('/purchase-receiving/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      items: heldItems.map((r) => ({
        product_id: r.product_id,
        expected_qty: r.expected_qty,
        received_qty: r.received_qty,
        note: r.note || '',
      })),
    })
    for (const r of heldItems) r.held = false
    saveHeldState()
    alert('数変更検収を確定しました。')
    await loadReceivingData()
  } catch (e) {
    console.error('数変更検収確定エラー', e)
    alert('数変更検収の確定に失敗しました。')
  } finally {
    saving.value = false
  }
}

const showHistory = ref(false)
const historyLoading = ref(false)
const historyRows = ref([])

const toggleHistory = async () => {
  showHistory.value = !showHistory.value
  if (!showHistory.value) return
  historyLoading.value = true
  try {
    const res = await api.client.get('/purchase-receiving/history/', {
      params: { supplier_id: selectedSupplier.value, target_date: targetDate.value },
    })
    historyRows.value = res.data.records || []
  } catch (e) {
    console.error('検収履歴取得エラー', e)
  } finally {
    historyLoading.value = false
  }
}

const toggleHold = (row) => {
  row.held = !row.held
  if (row.held) row.received_qty = 0
  else row.received_qty = row.expected_qty
  saveHeldState()
}

const exportExcel = () => {
  const header = ['品番', '品名', '予定', '実績', ...coverageDates.value.map((d) => { const p = formatDateParts(d); return `${p.date}(${p.dow})` }), '実数', '備考']
  const data = filteredRows.value.map((r) => [
    r.product_code,
    r.product_name,
    r.expected_qty,
    r.actual_qty || '',
    ...coverageDates.value.map((d) => r.daily[d] || ''),
    r.received_qty,
    r.note || '',
  ])
  const ws = XLSX.utils.aoa_to_sheet([header, ...data])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '仕入れ検収')
  const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
  const name = supplier ? supplier.supplier_code : ''
  XLSX.writeFile(wb, `仕入れ検収_${name}_${targetDate.value}.xlsx`)
}

onMounted(fetchSuppliers)
</script>

<style scoped>
.pattern-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 13px;
}
.pattern-label { font-weight: 600; color: #475569; }
.pattern-value { color: #1e293b; }
.delivery-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.delivery-badge.yes { background: #dcfce7; color: #166534; }
.delivery-badge.no { background: #fef3c7; color: #92400e; }
.next-delivery { color: #6366f1; font-weight: 500; }
.summary-count { margin-left: auto; color: #334155; font-weight: 600; }
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
}
.filter-bar label { display: flex; align-items: center; gap: 4px; color: #475569; font-weight: 600; }
.filter-bar select, .filter-input { padding: 2px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
.filter-input { width: 100px; }
.filter-count { color: #94a3b8; margin-left: auto; }
.btn-group { display: flex; align-items: center; gap: 2px; }
.filter-label { color: #475569; font-weight: 600; margin-right: 2px; }
.btn-filter {
  padding: 2px 8px;
  font-size: 12px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  border-radius: 3px;
}
.btn-filter.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.col-code { min-width: 130px; }
.btn-hold {
  margin-left: 4px;
  padding: 1px 6px;
  font-size: 11px;
  border: 1px solid #d1d5db;
  border-radius: 3px;
  background: #fff;
  color: #64748b;
  cursor: pointer;
}
.btn-hold.active {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #92400e;
  font-weight: 600;
}
.row-held { background: #fffbeb; }
.row-held td { color: #94a3b8; }
.col-name { min-width: 120px; }
.col-total { min-width: 70px; font-weight: 700; }
.col-actual { min-width: 60px; color: #2563eb; font-weight: 600; }
.col-diff { min-width: 50px; }
.diff-short { color: #dc2626; font-weight: 700; }
.diff-over { color: #2563eb; font-weight: 700; }
.row-done { background: #f1f5f9; }
.row-done td { color: #94a3b8; }
.col-date { min-width: 44px; color: #64748b; font-size: 12px; text-align: center; white-space: nowrap; }
.col-date .dow { font-size: 11px; color: #94a3b8; }
.col-recv { min-width: 80px; }
.col-note { min-width: 100px; }
.bold { font-weight: 700; }
.input-qty {
  width: 70px;
  text-align: right;
  padding: 2px 4px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}
.input-note {
  width: 100%;
  padding: 2px 4px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}
.form-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.btn-held-confirm {
  padding: 6px 16px;
  background: #f59e0b;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
}
.btn-held-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-history {
  padding: 6px 16px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
}
.history-panel {
  margin-top: 16px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.history-title { margin: 0 0 8px; font-size: 14px; color: #334155; }
.btn-excel {
  padding: 6px 16px;
  background: #059669;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
}
</style>
