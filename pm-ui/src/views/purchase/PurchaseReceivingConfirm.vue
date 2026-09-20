<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">スマホ検収 確認</h1>
      <div class="page-actions">
        <select v-model="selectedSupplier" @change="loadRecords">
          <option value="">-- 全仕入先 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">
            {{ s.supplier_code }} {{ s.supplier_name }}
          </option>
        </select>
        <input type="date" v-model="targetDate" @change="loadRecords" />
        <div class="btn-group">
          <span class="filter-label">状態:</span>
          <button :class="['btn-filter', { active: statusFilter === 'pending' }]" @click="statusFilter = 'pending'; loadRecords()">未確認</button>
          <button :class="['btn-filter', { active: statusFilter === 'confirmed' }]" @click="statusFilter = 'confirmed'; loadRecords()">確認済</button>
          <button :class="['btn-filter', { active: statusFilter === 'all' }]" @click="statusFilter = 'all'; loadRecords()">全て</button>
        </div>
        <button class="btn-primary" @click="loadRecords" :disabled="loading">更新</button>
      </div>
    </div>

    <div class="page-content">
      <!-- サマリー -->
      <div v-if="records.length" class="confirm-summary">
        <span class="summary-item">全 {{ records.length }}件</span>
        <span class="summary-item pending">未確認 {{ pendingCount }}件</span>
        <span class="summary-item done">確認済 {{ confirmedCount }}件</span>
        <button
          v-if="pendingRecords.length"
          class="btn-success btn-confirm-all"
          @click="confirmAll"
          :disabled="saving"
        >全件確認 ({{ pendingRecords.length }}件)</button>
      </div>

      <div v-if="loading" class="no-data">読み込み中...</div>

      <table v-if="!loading && records.length" class="data-table">
        <thead>
          <tr>
            <th class="col-check"><input type="checkbox" v-model="selectAll" @change="toggleSelectAll" /></th>
            <th>状態</th>
            <th>仕入先</th>
            <th>検収日時</th>
            <th>品番</th>
            <th>品名</th>
            <th class="num">数量</th>
            <th>検収者</th>
            <th>備考</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in records"
            :key="r.id"
            :class="{ 'row-pending': r.receiving_status === 'pending', 'row-confirmed': r.receiving_status === 'confirmed' }"
          >
            <td class="col-check">
              <input
                v-if="r.receiving_status === 'pending'"
                type="checkbox"
                v-model="selectedIds"
                :value="r.id"
              />
            </td>
            <td>
              <span v-if="r.receiving_status === 'pending'" class="badge-pending">未確認</span>
              <span v-else class="badge-confirmed">確認済</span>
            </td>
            <td class="col-supplier">{{ r.supplier_code }} {{ r.supplier_name }}</td>
            <td>{{ r.timestamp }}</td>
            <td class="col-code">{{ r.product_code }}</td>
            <td>{{ r.product_name }}</td>
            <td class="num">
              <span :class="{ 'non-delivery': r.non_delivery }">{{ r.non_delivery ? '未納' : r.qty }}</span>
            </td>
            <td>{{ r.operator_name }}</td>
            <td>{{ r.remarks }}</td>
            <td>
              <button
                v-if="r.receiving_status === 'pending'"
                class="btn-sm-confirm"
                @click="confirmSingle(r)"
                :disabled="saving"
              >確認</button>
              <span v-else class="text-muted">-</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && !records.length" class="no-data">
        {{ statusFilter === 'pending' ? '未確認の検収データはありません' : '検収データがありません' }}
      </div>

      <!-- 選択確認バー -->
      <div v-if="selectedIds.length" class="confirm-bar">
        <span>{{ selectedIds.length }}件 選択中</span>
        <button class="btn-success" @click="confirmSelected" :disabled="saving">選択を確認済みにする</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

const suppliers = ref([])
const selectedSupplier = ref('')
const today = new Date()
const targetDate = ref(
  `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
)
const statusFilter = ref('pending')
const loading = ref(false)
const saving = ref(false)
const records = ref([])
const selectedIds = ref([])
const selectAll = ref(false)

const pendingRecords = computed(() => records.value.filter((r) => r.receiving_status === 'pending'))
const pendingCount = computed(() => pendingRecords.value.length)
const confirmedCount = computed(() => records.value.filter((r) => r.receiving_status === 'confirmed').length)

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) =>
    (a.supplier_code || '').localeCompare(b.supplier_code || '')
  )
}

const loadRecords = async () => {
  loading.value = true
  selectedIds.value = []
  selectAll.value = false
  try {
    const params = { status: statusFilter.value }
    if (selectedSupplier.value) params.supplier_id = selectedSupplier.value
    if (targetDate.value) params.target_date = targetDate.value
    const res = await api.client.get('/purchase-receiving/confirm/', { params })
    records.value = res.data.records || []
  } catch {
    alert('データの取得に失敗しました。')
    records.value = []
  } finally {
    loading.value = false
  }
}

const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedIds.value = pendingRecords.value.map((r) => r.id)
  } else {
    selectedIds.value = []
  }
}

const doConfirm = async (ids) => {
  if (!ids.length) return
  saving.value = true
  try {
    const res = await api.client.patch('/purchase-receiving/confirm/', { record_ids: ids })
    alert(res.data.detail || '確認済みにしました')
    await loadRecords()
  } catch {
    alert('確認に失敗しました。')
  } finally {
    saving.value = false
  }
}

const confirmSingle = (r) => doConfirm([r.id])
const confirmSelected = () => doConfirm([...selectedIds.value])
const confirmAll = () => {
  if (!confirm(`${pendingRecords.value.length}件を全て確認済みにしますか？`)) return
  doConfirm(pendingRecords.value.map((r) => r.id))
}

onMounted(async () => {
  await fetchSuppliers()
  await loadRecords()
})
</script>

<style scoped>
.confirm-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
}
.summary-item { color: #334155; }
.summary-item.pending { color: #ea580c; }
.summary-item.done { color: #16a34a; }
.btn-confirm-all { margin-left: auto; }

.col-check { width: 36px; text-align: center; }
.col-code { font-weight: 700; }
.col-supplier { white-space: nowrap; }

.badge-pending {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  background: #fef3c7;
  color: #92400e;
  border-radius: 10px;
}
.badge-confirmed {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  background: #dcfce7;
  color: #166534;
  border-radius: 10px;
}

.row-pending { background: #fffbeb; }
.row-confirmed { background: #f0fdf4; }

.non-delivery {
  color: #dc2626;
  font-weight: 700;
}

.btn-sm-confirm {
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
  background: #16a34a;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-sm-confirm:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-sm-confirm:hover:not(:disabled) { background: #15803d; }

.text-muted { color: #94a3b8; }

.confirm-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #1e293b;
  color: #fff;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 100;
  box-shadow: 0 -2px 12px rgba(0,0,0,.2);
}

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
</style>
