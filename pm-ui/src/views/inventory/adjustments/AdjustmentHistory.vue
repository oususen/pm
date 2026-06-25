<template>
  <div class="history-page">
    <div class="caption">[SSE0031] 調整履歴 <DataSourceDialog title="調整履歴" :sources="dsSources" /></div>

    <div class="filters">
      <label class="filter-field">
        <span>工程CD</span>
        <input v-model="filters.process_code" type="text" placeholder="例: 4007" @keyup.enter="load" />
      </label>
      <label class="filter-field">
        <span>品番</span>
        <input v-model="filters.product_code" type="text" placeholder="品番" @keyup.enter="load" />
      </label>
      <label class="filter-field">
        <span>種別</span>
        <select v-model="filters.adjust_type">
          <option value="">すべて</option>
          <option value="STOCK">在庫調整</option>
          <option value="PROGRESS">進度調整</option>
          <option value="PLANNED_STOCK">計画在庫調整</option>
          <option value="PLANNED_PROGRESS">計画進度調整</option>
        </select>
      </label>
      <label class="filter-field">
        <span>対象日（開始）</span>
        <input v-model="filters.start_date" type="date" />
      </label>
      <label class="filter-field">
        <span>対象日（終了）</span>
        <input v-model="filters.end_date" type="date" />
      </label>
      <button class="btn" @click="load" :disabled="loading">検索</button>
    </div>

    <div v-if="loading" class="center">読み込み中...</div>
    <div v-else-if="error" class="center error">{{ error }}</div>
    <div v-else>
      <p class="count">{{ rows.length }} 件{{ rows.length >= 500 ? '（上限500件）' : '' }}</p>
      <div class="table-wrap">
        <table class="grid">
          <thead>
            <tr>
              <th>対象日</th>
              <th>種別</th>
              <th>工程CD</th>
              <th>品番</th>
              <th>ライン</th>
              <th>調整値</th>
              <th>理由</th>
              <th>更新日時</th>
              <th>調整者</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.plan_date }}</td>
              <td>
                <span class="badge" :class="typeClass(row.adjust_type)">{{ typeLabel(row.adjust_type) }}</span>
              </td>
              <td>{{ row.process_code || '—' }}</td>
              <td>{{ row.product_code }}</td>
              <td>{{ row.line_code }}</td>
              <td class="num" :class="{ negative: row.adjust_qty < 0 }">{{ row.adjust_qty }}</td>
              <td class="reason">{{ row.reason || '—' }}</td>
              <td>{{ formatDatetime(row.updated_at) }}</td>
              <td>{{ row.updated_by_name ?? '—' }}</td>
              <td class="del-cell">
                <button class="btn-del" :disabled="deleting === row.id" @click="deleteRow(row)">削除</button>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="10" class="center">データなし</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_stock_adjustment', desc: '在庫調整履歴' },
  { op: '読み取り', table: 't_progress_adjustment', desc: '進度調整履歴' },
]

const filters = ref({
  process_code: '',
  product_code: '',
  adjust_type: '',
  start_date: '',
  end_date: '',
})
const rows = ref([])
const loading = ref(false)
const error = ref('')
const deleting = ref(null)

const TYPE_LABELS = {
  STOCK: '在庫調整',
  PROGRESS: '進度調整',
  PLANNED_STOCK: '計画在庫調整',
  PLANNED_PROGRESS: '計画進度調整',
}
const typeLabel = (t) => TYPE_LABELS[t] || t
const typeClass = (t) => ({
  'badge-stock': t === 'STOCK',
  'badge-progress': t === 'PROGRESS',
  'badge-planned-stock': t === 'PLANNED_STOCK',
  'badge-planned-progress': t === 'PLANNED_PROGRESS',
})

const formatDatetime = (val) => {
  if (!val) return '—'
  return val.replace('T', ' ').slice(0, 16)
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filters.value.process_code) params.process_code = filters.value.process_code
    if (filters.value.product_code) params.product_code = filters.value.product_code
    if (filters.value.adjust_type) params.adjust_type = filters.value.adjust_type
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const res = await api.lineBacklogAdjustments.list(params)
    rows.value = res.data
  } catch (e) {
    error.value = e?.response?.data?.detail || '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const deleteRow = async (row) => {
  const label = `${row.plan_date} / ${typeLabel(row.adjust_type)} / ${row.product_code} / ${row.line_code}`
  if (!confirm(`以下の調整を削除しますか？\n\n${label}`)) return
  deleting.value = row.id
  try {
    await api.lineBacklogAdjustments.remove(row.id)
    rows.value = rows.value.filter((r) => r.id !== row.id)
  } catch (e) {
    alert(e?.response?.data?.detail || '削除に失敗しました')
  } finally {
    deleting.value = null
  }
}

load()
</script>

<style scoped>
.history-page {
  padding: 12px 10px 18px;
  background: #efefdc;
  min-height: 100%;
}
.caption {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 10px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
  margin-bottom: 12px;
}
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 13px;
}
.filter-field input,
.filter-field select {
  padding: 4px 6px;
  border: 1px solid #c7ced9;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
}
.btn {
  padding: 5px 14px;
  background: #334155;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  height: 28px;
  align-self: flex-end;
}
.btn:hover { background: #1e293b; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.count {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 6px;
}
.table-wrap {
  overflow-x: auto;
}
.grid {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
  background: #fff;
}
.grid th,
.grid td {
  border: 1px solid #d1d5db;
  padding: 5px 8px;
  white-space: nowrap;
}
.grid th {
  background: #f1f5f9;
  font-weight: 600;
  text-align: center;
}
.grid tbody tr:hover { background: #f8fafc; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.negative { color: #dc2626; }
.reason { white-space: normal; max-width: 260px; }
.center { text-align: center; padding: 16px; }
.error { color: #dc2626; }

.badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.badge-stock { background: #dbeafe; color: #1d4ed8; }
.badge-progress { background: #dcfce7; color: #15803d; }
.badge-planned-stock { background: #e0e7ff; color: #4338ca; }
.badge-planned-progress { background: #fef9c3; color: #854d0e; }
.del-cell { text-align: center; padding: 3px 6px; }
.btn-del {
  padding: 2px 8px;
  background: #fee2e2;
  color: #dc2626;
  border: 1px solid #fca5a5;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}
.btn-del:hover { background: #fecaca; }
.btn-del:disabled { opacity: 0.5; cursor: not-allowed; }
</style>

