<template>
  <div class="page-container">
    <h2 class="page-title">外作先展開Excel出力 <DataSourceDialog title="外作先展開Excel出力" :sources="dsSources" /></h2>

    <div class="filter-row">
      <select v-model="filterStatus" @change="fetchOrders" class="filter-select">
        <option value="IMPORTED">取込済（未送付）</option>
        <option value="SENT_TO_SUB">展開送付済</option>
        <option value="">全て</option>
      </select>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchOrders" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchOrders" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
      <button class="btn-primary" :disabled="!selectedIds.length || exporting" @click="doExport">
        {{ exporting ? '出力中...' : `Excel出力（${selectedIds.length}件）` }}
      </button>
      <button class="btn-secondary" :disabled="!selectedIds.length || recalculating" @click="recalculateSelected">
        {{ recalculating ? '再計算中...' : `選択行を再計算（${selectedIds.length}件）` }}
      </button>
    </div>

    <div v-if="showRecalcDialog" class="dialog-overlay">
      <div class="dialog-card">
        <h3 class="dialog-title">再計算条件入力</h3>
        <div class="dialog-row">
          <label>外作先展開日数</label>
          <input type="number" min="0" step="1" v-model.number="recalcForm.outsource_expand_days" />
        </div>
        <div class="dialog-row">
          <label>社内承認日数</label>
          <input type="number" min="0" step="1" v-model.number="recalcForm.internal_approval_days" />
        </div>
        <div class="dialog-row">
          <label>業務処理日数</label>
          <input type="number" min="0" step="1" v-model.number="recalcForm.business_process_days" />
        </div>
        <div class="dialog-note">
          発注LT = 外作先展開日数 + 社内承認日数 + 業務処理日数
        </div>
        <div class="dialog-actions">
          <button class="btn-month" @click="showRecalcDialog = false">キャンセル</button>
          <button class="btn-secondary" :disabled="recalculating" @click="confirmRecalculate">この条件で再計算</button>
        </div>
      </div>
    </div>

    <table class="data-table" v-if="orders.length">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
          <th>案件番号</th>
          <th>品目コード</th>
          <th>品番</th>
          <th>品目名称</th>
          <th>BOM有無</th>
          <th>数量</th>
          <th>塗装日</th>
          <th>調達最長LT</th>
          <th>材料コード</th>
          <th>調達先</th>
          <th>最早着手</th>
          <th>最遅完了</th>
          <th>ステータス</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in orders" :key="o.id">
          <td><input type="checkbox" :value="o.id" v-model="selectedIds" /></td>
          <td class="case-no">{{ o.case_no }}</td>
          <td>{{ o.item_code }}</td>
          <td>{{ o.product_number || '-' }}</td>
          <td>{{ o.item_name }}</td>
          <td>{{ o.has_bom ? 'あり' : 'なし' }}</td>
          <td class="text-right">{{ o.order_qty }}</td>
          <td>{{ o.painting_date }}</td>
          <td>{{ o.max_procurement_lt ?? '-' }}</td>
          <td>{{ o.max_procurement_material_code || '-' }}</td>
          <td>{{ o.max_procurement_supplier_name || '-' }}</td>
          <td>{{ o.earliest_start || '-' }}</td>
          <td>{{ o.latest_finish || '-' }}</td>
          <td>{{ statusLabel(o.status) }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else-if="!loading" class="empty-state">対象案件がありません</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_outsource_order / t_outsource_order_line', desc: '案件一覧の取得' },
  { op: '読み書き', table: 't_outsource_order', desc: 'Excel出力・制約日再計算' },
]

function monthRange(d) {
  const y = d.getFullYear(), m = d.getMonth()
  const from = `${y}-${String(m + 1).padStart(2, '0')}-01`
  const to = `${y}-${String(m + 1).padStart(2, '0')}-${String(new Date(y, m + 1, 0).getDate()).padStart(2, '0')}`
  return { from, to }
}
const now = new Date()
const twoMonthsLater = new Date()
twoMonthsLater.setMonth(twoMonthsLater.getMonth() + 2)
const { to: initTo } = monthRange(twoMonthsLater)
const paintingFrom = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`)
const paintingTo = ref(initTo)

function shiftMonth(delta) {
  const d = new Date(paintingFrom.value + 'T00:00:00')
  d.setMonth(d.getMonth() + delta)
  const { from, to } = monthRange(d)
  paintingFrom.value = from
  paintingTo.value = to
  fetchOrders()
}

const orders = ref([])
const selectedIds = ref([])
const filterStatus = ref('IMPORTED')
const loading = ref(false)
const exporting = ref(false)
const recalculating = ref(false)
const showRecalcDialog = ref(false)
const recalcForm = ref({
  outsource_expand_days: 0,
  internal_approval_days: 0,
  business_process_days: 0,
})

const allSelected = computed(() => orders.value.length > 0 && selectedIds.value.length === orders.value.length)

function toggleAll(e) {
  selectedIds.value = e.target.checked ? orders.value.map(o => o.id) : []
}

const STATUS_MAP = { IMPORTED: '取込済', SENT_TO_SUB: '展開送付済', SPLIT_REGISTERED: '分割登録済', IN_PROGRESS: '加工中', COMPLETED: '完了' }
function statusLabel(s) { return STATUS_MAP[s] || s }

async function fetchOrders() {
  loading.value = true
  selectedIds.value = []
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value
    const res = await api.outsource.getOrders(params)
    orders.value = res.data.results || res.data
  } finally {
    loading.value = false
  }
}

async function doExport() {
  exporting.value = true
  try {
    const res = await api.outsource.exportExcel(selectedIds.value)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'split_plan_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
    await fetchOrders()
  } finally {
    exporting.value = false
  }
}

async function recalculateSelected() {
  showRecalcDialog.value = true
}

async function confirmRecalculate() {
  recalculating.value = true
  try {
    await Promise.all(
      selectedIds.value.map(id => api.outsource.calculateConstraints(id, recalcForm.value))
    )
    showRecalcDialog.value = false
    await fetchOrders()
  } catch (e) {
    alert(e.response?.data?.error || '再計算に失敗しました')
  } finally {
    recalculating.value = false
  }
}

onMounted(fetchOrders)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }
.filter-row { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.filter-select { padding: 4px 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.filter-label { font-size: 12px; color: #555; }
.filter-date { padding: 3px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; width: 130px; }
.filter-sep { font-size: 12px; color: #888; }
.btn-month { padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-month:hover { background: #e3f2fd; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 6px 12px; background: #e8f5e9; color: #2e7d32; border: 1px solid #81c784; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.case-no { font-family: monospace; font-size: 11px; }
.empty-state { text-align: center; padding: 32px; color: #999; }
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.dialog-card {
  width: 420px;
  background: #fff;
  border-radius: 8px;
  padding: 14px;
}
.dialog-title { font-size: 15px; margin-bottom: 10px; }
.dialog-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dialog-row label { width: 130px; font-size: 12px; color: #555; }
.dialog-row input { width: 120px; padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; }
.dialog-note { font-size: 12px; color: #666; margin: 6px 0 10px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
