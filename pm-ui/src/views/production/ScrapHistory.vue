<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">仕損履歴</h2>
        <p class="subtitle">SCRAP記録を検索・一覧表示します。
          <button class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button>
        </p>
      </div>
      <div class="filters">
        <div class="filter-row">
          <label>期間</label>
          <input type="date" v-model="startDate" />
          <span>〜</span>
          <input type="date" v-model="endDate" />
        </div>
        <div class="filter-row">
          <label>工程</label>
          <select v-model="processId">
            <option value="">-- 工程を選択 --</option>
            <option v-for="p in processes" :key="p.id" :value="p.id">
              {{ p.process_code }} - {{ p.process_name }}
            </option>
          </select>
        </div>
        <div class="filter-row">
          <label>品番</label>
          <input type="text" v-model="productCode" placeholder="品番コード" />
        </div>
        <div class="filter-row">
          <label>理由</label>
          <select v-model="reason">
            <option value="">-- すべて --</option>
            <option v-for="r in scrapReasons" :key="r.value" :value="r.value">
              {{ r.label }}
            </option>
          </select>
        </div>
        <div class="filter-row">
          <label>判定</label>
          <select v-model="dispositionStatus">
            <option value="">-- すべて --</option>
            <option v-for="s in dispositionStatuses" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="load" :disabled="loading">検索</button>
          <button @click="resetFilters" :disabled="loading">リセット</button>
          <button @click="exportExcel" :disabled="loading || !filteredRecords.length">
            CSV出力
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="table-wrap">
      <table class="history-table">
        <thead>
          <tr>
            <th>記録時刻</th>
            <th>工程</th>
            <th>品番</th>
            <th>品名</th>
            <th class="num">仕損数</th>
            <th>判定</th>
            <th class="num">戻し数量</th>
            <th>発見時点</th>
            <th>理由</th>
            <th>理由詳細</th>
            <th>記入者</th>
            <th>補充</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="rec in filteredRecords"
            :key="rec.id"
            :class="{ selected: selectedRecord?.id === rec.id }"
            @click="loadBreakdown(rec)"
          >
            <td>{{ formatDateTime(rec.timestamp) }}</td>
            <td>{{ rec.process_code }} / {{ rec.process_name }}</td>
            <td>{{ rec.product_code || '-' }}</td>
            <td>{{ rec.product_name || '' }}</td>
            <td class="num">{{ formatNumber(rec.qty) }}</td>
            <td>{{ dispositionLabel(rec.scrap_disposition_status) }}</td>
            <td class="num">{{ formatNumber(rec.scrap_return_qty) }}</td>
            <td>{{ productionRecordedLabel(rec) }}</td>
            <td>{{ reasonLabel(rec.event_data?.reason) }}</td>
            <td>{{ rec.event_data?.reason_detail || '' }}</td>
            <td>{{ rec.operator_name || '' }}</td>
            <td class="center">
              <span v-if="rec.scrap_is_replenished">✅</span>
            </td>
          </tr>
          <tr v-if="!filteredRecords.length">
            <td colspan="12" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="selectedRecord" class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">BOM展開明細</div>
          <div class="panel-sub">
            {{ formatDateTime(selectedRecord.timestamp) }} / {{ selectedRecord.product_code }} / {{ selectedRecord.product_name }}
          </div>
        </div>
        <div v-if="breakdownLoading" class="panel-loading">読込中...</div>
      </div>
      <div class="panel-filters">
        <div class="filter-row">
          <label>加工/購入先</label>
          <select v-model="breakdownFilterType">
            <option value="">-- すべて --</option>
            <option value="purchase">購買</option>
            <option value="process">工程</option>
          </select>
          <input type="text" v-model="breakdownFilterText" placeholder="コード/名称" />
        </div>
        <button
          class="btn btn-clear"
          :disabled="!breakdownFilterType && !breakdownFilterText"
          @click="resetBreakdownFilters"
        >
          クリア
        </button>
      </div>
      <table class="detail-table">
        <thead>
          <tr>
            <th>品番</th>
            <th>品名</th>
            <th>加工/購入先</th>
            <th class="num">減算数</th>
            <th>補充完了</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredBreakdown" :key="row.detail_id">
            <td>{{ row.product_code || '-' }}</td>
            <td>{{ row.product_name || '' }}</td>
            <td>
              <template v-if="row.supplier_code || row.supplier_name">
                購買: {{ row.supplier_code || '' }} {{ row.supplier_name || '' }}
              </template>
              <template v-else-if="row.process_code">
                工程: {{ row.process_code }} / {{ row.process_name || '' }}
              </template>
              <template v-else>-</template>
            </td>
            <td class="num">{{ formatNumber(row.deduct_qty) }}</td>
            <td>
              <template v-if="row.is_replenished">✅</template>
              <button
                v-else
                class="link-btn"
                :disabled="marking"
                @click="markDetailReplenished(row.detail_id)"
              >
                この品を完了
              </button>
            </td>
          </tr>
          <tr v-if="!filteredBreakdown.length">
            <td colspan="5" class="no-data">
              {{ breakdown.length ? '該当する明細がありません' : '明細がありません' }}
            </td>
          </tr>
        </tbody>
      </table>

      <div class="decision-box">
        <div class="decision-info">
          <div class="decision-item">
            <span class="label">判定</span>
            <span class="value">{{ dispositionLabel(selectedRecord?.scrap_disposition_status) || '判定待ち' }}</span>
          </div>
          <div class="decision-item">
            <span class="label">仕損数量</span>
            <span class="value">{{ formatNumber(selectedScrapQty) }}</span>
          </div>
          <div class="decision-item">
            <span class="label">戻し済</span>
            <span class="value">{{ formatNumber(selectedReturnQty) }}</span>
          </div>
          <div class="decision-item">
            <span class="label">残数量</span>
            <span class="value">{{ formatNumber(remainingQty) }}</span>
          </div>
        </div>
        <div class="decision-actions">
          <input
            v-model.number="returnQty"
            type="number"
            min="0"
            :max="remainingQty"
            step="0.001"
            placeholder="戻し数量"
          />
          <button
            class="btn"
            :disabled="decisioning || !(returnQty > 0) || remainingQty <= 0"
            @click="returnToStock"
          >
            使用可として戻す
          </button>
          <button class="btn" :disabled="decisioning" @click="confirmScrap">
            仕損確定
          </button>
        </div>
        <div class="decision-hint">※ 戻し数量は残数量以内で入力してください。</div>
      </div>
      <div class="panel-actions">
        <button class="btn" :disabled="marking || selectedRecord?.scrap_is_replenished" @click="markReplenished(selectedRecord)">
          全品目を完了にする
        </button>
      </div>
    </div>

    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header">
          <h3>データソース — 仕損履歴</h3>
          <button class="ds-close" @click="showDataSource = false">×</button>
        </div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr><td>取得</td><td>t_process_realtime_record</td><td>仕損記録の一覧取得（record_type=SCRAP）</td></tr>
            <tr><td>取得</td><td>t_scrap_record / t_scrap_record_detail</td><td>仕損明細の展開表示（品目別の補充状態）</td></tr>
            <tr><td>更新</td><td>t_scrap_record_detail</td><td>品目別の補充完了マーク</td></tr>
            <tr><td>更新</td><td>t_scrap_record</td><td>処置ステータスの変更（保留→廃棄等）</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, onMounted, ref } from 'vue'
const showDataSource = ref(false)
import api from '@/api/client'

const loading = ref(false)
const error = ref('')
const records = ref([])
const processes = ref([])
const breakdown = ref([])
const breakdownLoading = ref(false)
const selectedRecord = ref(null)
const marking = ref(false)
const decisioning = ref(false)
const returnQty = ref(null)

const today = new Date()
const toISODate = (d) => formatISODate(d)
const startDate = ref(toISODate(new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000)))
const endDate = ref(toISODate(new Date(today.getTime() + 24 * 60 * 60 * 1000)))
const processId = ref('')
const productCode = ref('')
const reason = ref('')
const dispositionStatus = ref('')
const breakdownFilterType = ref('')
const breakdownFilterText = ref('')

const scrapReasons = [
  { value: 'RUST', label: 'サビ' },
  { value: 'DEFORMATION', label: '変形/キズ' },
  { value: 'BEAD_MISALIGN', label: 'ビードずれ' },
  { value: 'BLOW_HOLE', label: 'ブローホール' },
  { value: 'WELD_PINHOLE', label: '溶接穴あき' },
  { value: 'UNDERCUT', label: 'アンダーカット' },
  { value: 'PRECISION_NG', label: '精度不良' },
  { value: 'MISSING_OR_WRONG_ASSEMBLY', label: '欠品/誤組' },
  { value: 'MATERIAL_WIP_DEFECT', label: '素材/仕掛不良' },
  { value: 'OTHER', label: 'その他' },
]

const reasonMap = scrapReasons.reduce((acc, r) => ({ ...acc, [r.value]: r.label }), {})
const reasonLabel = (val) => reasonMap[val] || ''

const dispositionStatuses = [
  { value: 'PENDING', label: '判定待ち' },
  { value: 'APPROVED', label: '使用可' },
  { value: 'REJECTED', label: '仕損確定' },
  { value: 'PARTIAL', label: '一部使用可' },
]
const dispositionMap = dispositionStatuses.reduce((acc, s) => ({ ...acc, [s.value]: s.label }), {})
const dispositionLabel = (val) => dispositionMap[val] || ''
const productionRecordedLabel = (rec) => {
  const raw =
    rec?.scrap_is_production_recorded !== null &&
    rec?.scrap_is_production_recorded !== undefined
      ? rec.scrap_is_production_recorded
      : rec?.event_data?.is_production_recorded
  return raw ? '実績入力後' : '実績入力前'
}
const isPurchaseRow = (row) => Boolean(row?.supplier_code || row?.supplier_name)
const isProcessRow = (row) => Boolean(!isPurchaseRow(row) && row?.process_code)

const filteredRecords = computed(() => {
  let list = records.value
  if (reason.value) {
    list = list.filter((r) => (r.event_data?.reason || '') === reason.value)
  }
  if (dispositionStatus.value) {
    list = list.filter((r) => {
      const status = r.scrap_disposition_status
      if (dispositionStatus.value === 'PENDING') {
        return !status || status === 'PENDING'
      }
      return status === dispositionStatus.value
    })
  }
  return list
})

const filteredBreakdown = computed(() => {
  let list = breakdown.value
  if (breakdownFilterType.value === 'purchase') {
    list = list.filter((row) => isPurchaseRow(row))
  } else if (breakdownFilterType.value === 'process') {
    list = list.filter((row) => isProcessRow(row))
  }
  const keyword = breakdownFilterText.value.trim().toLowerCase()
  if (keyword) {
    list = list.filter((row) => {
      const supplierText = `${row.supplier_code || ''} ${row.supplier_name || ''}`.toLowerCase()
      const processText = `${row.process_code || ''} ${row.process_name || ''}`.toLowerCase()
      if (breakdownFilterType.value === 'purchase') {
        return supplierText.includes(keyword)
      }
      if (breakdownFilterType.value === 'process') {
        return processText.includes(keyword)
      }
      return supplierText.includes(keyword) || processText.includes(keyword)
    })
  }
  return list
})

const formatDateTime = (ts) => {
  if (!ts) return ''
  return new Date(ts).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' })
}
const formatNumber = (n) => {
  if (n === null || n === undefined) return ''
  const num = Number(n)
  if (Number.isNaN(num)) return ''
  return num.toLocaleString()
}

const toNumber = (n) => {
  const num = Number(n)
  return Number.isNaN(num) ? 0 : num
}

const selectedScrapQty = computed(() => toNumber(selectedRecord.value?.qty))
const selectedReturnQty = computed(() => toNumber(selectedRecord.value?.scrap_return_qty))
const remainingQty = computed(() => Math.max(selectedScrapQty.value - selectedReturnQty.value, 0))

const resetFilters = () => {
  processId.value = ''
  productCode.value = ''
  reason.value = ''
  dispositionStatus.value = ''
  startDate.value = toISODate(new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000))
  endDate.value = toISODate(new Date(today.getTime() + 24 * 60 * 60 * 1000))
  load()
}

const exportExcel = () => {
  const headers = [
    '記録時刻',
    '工程',
    '品番',
    '品名',
    '仕損数',
    '判定',
    '戻し数量',
    '発見時点',
    '理由',
    '理由詳細',
    '記入者',
    '補充',
  ]
  const rows = filteredRecords.value.map((rec) => [
    formatDateTime(rec.timestamp),
    `${rec.process_code || ''} / ${rec.process_name || ''}`.trim(),
    rec.product_code || '',
    rec.product_name || '',
    formatNumber(rec.qty),
    dispositionLabel(rec.scrap_disposition_status),
    formatNumber(rec.scrap_return_qty),
    productionRecordedLabel(rec),
    reasonLabel(rec.event_data?.reason),
    rec.event_data?.reason_detail || '',
    rec.operator_name || '',
    rec.scrap_is_replenished ? '済' : '',
  ])
  const escapeCsv = (value) => {
    const text = `${value ?? ''}`
    const escaped = text.replace(/"/g, '""')
    return `"${escaped}"`
  }
  const csvLines = [headers.map(escapeCsv).join(','), ...rows.map((r) => r.map(escapeCsv).join(','))]
  const bom = '\ufeff'
  const csvContent = `${bom}${csvLines.join('\r\n')}`
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const filename = `scrap-history_${toISODate(new Date())}.csv`
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

const resetBreakdownFilters = () => {
  breakdownFilterType.value = ''
  breakdownFilterText.value = ''
}

const loadBreakdown = async (rec) => {
  if (!rec?.id) return
  selectedRecord.value = rec
  breakdownLoading.value = true
  breakdown.value = []
  try {
    const res = await api.processRealtime.getScrapBreakdown(rec.id)
    breakdown.value = res.data || []
    selectedRecord.value.scrap_is_replenished =
      breakdown.value.length > 0 && breakdown.value.every((d) => d.is_replenished)
    selectedRecord.value.scrap_replenished_at = selectedRecord.value.scrap_is_replenished
      ? new Date().toISOString()
      : null
    if (remainingQty.value > 0) {
      returnQty.value = remainingQty.value
    } else {
      returnQty.value = null
    }
  } catch (e) {
    console.error('展開明細取得エラー', e)
  } finally {
    breakdownLoading.value = false
  }
}

const markReplenished = async (rec) => {
  if (!rec?.id || rec.scrap_is_replenished) return
  marking.value = true
  try {
    await api.processRealtime.markReplenished(rec.id)
    // refresh record flags
    await load()
    if (selectedRecord.value?.id === rec.id) {
      await loadBreakdown(rec)
    }
  } catch (e) {
    console.error('補充完了更新エラー', e)
  } finally {
    marking.value = false
  }
}

const markDetailReplenished = async (detailId) => {
  if (!selectedRecord.value?.id || !detailId) return
  marking.value = true
  try {
    await api.processRealtime.markDetailReplenished(selectedRecord.value.id, detailId)
    await loadBreakdown(selectedRecord.value)
  } catch (e) {
    console.error('明細補充完了更新エラー', e)
  } finally {
    marking.value = false
  }
}

const returnToStock = async () => {
  if (!selectedRecord.value?.id) return
  const qty = Number(returnQty.value)
  if (!qty || qty <= 0) return
  if (qty > remainingQty.value) {
    alert('戻し数量が残数量を超えています。')
    return
  }
  const recordId = selectedRecord.value.id
  decisioning.value = true
  try {
    await api.processRealtime.updateScrapDisposition(recordId, {
      action: 'RETURN',
      qty,
    })
    await load()
    const target = records.value.find((r) => r.id === recordId)
    if (target) {
      await loadBreakdown(target)
    }
  } catch (e) {
    console.error('戻し処理エラー', e)
    alert('戻し処理に失敗しました')
  } finally {
    decisioning.value = false
  }
}

const confirmScrap = async () => {
  if (!selectedRecord.value?.id) return
  const recordId = selectedRecord.value.id
  decisioning.value = true
  try {
    await api.processRealtime.updateScrapDisposition(recordId, {
      action: 'CONFIRM_SCRAP',
    })
    await load()
    const target = records.value.find((r) => r.id === recordId)
    if (target) {
      await loadBreakdown(target)
    }
  } catch (e) {
    console.error('仕損確定エラー', e)
    alert('仕損確定に失敗しました')
  } finally {
    decisioning.value = false
  }
}

const loadProcesses = async () => {
  try {
    const res = await api.processes.getProcesses({ is_active: true })
    processes.value = res.data.results || res.data || []
  } catch (e) {
    console.error('工程取得エラー', e)
  }
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {
      record_type: 'SCRAP',
      start_date: startDate.value,
      end_date: endDate.value,
    }
    if (processId.value) params.process_id = processId.value
    if (productCode.value.trim()) params.product_code = productCode.value.trim()
    const res = await api.processRealtime.list(params)
    const data = res.data?.results || res.data || []
    records.value = Array.isArray(data) ? data : []
    // 直近1件を自動表示
    if (records.value.length) {
      await loadBreakdown(records.value[0])
    } else {
      selectedRecord.value = null
      breakdown.value = []
    }
  } catch (e) {
    error.value = e?.message || '読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadProcesses()
  load()
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}
.page-title {
  margin: 0;
}
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}
.filter-row {
  display: flex;
  gap: 6px;
  align-items: center;
}
.filter-row label {
  font-weight: 600;
  font-size: 13px;
}
.filter-row input,
.filter-row select {
  padding: 6px 8px;
  min-height: 32px;
}
.filter-actions {
  display: flex;
  gap: 8px;
}
.filter-actions button {
  padding: 8px 12px;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.history-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1100px;
}
.history-table th,
.history-table td {
  border: 1px solid #e5e7eb;
  padding: 8px 10px;
  font-size: 13px;
  text-align: left;
}
.history-table th {
  background: #f4f6fb;
}
.history-table tbody tr {
  cursor: pointer;
}
.history-table tbody tr:hover {
  background: #f8fafc;
}
.history-table tbody tr.selected {
  background: #fbcfe8;
}
.center {
  text-align: center;
}
.num {
  text-align: right;
}
.no-data {
  text-align: center;
  color: #6b7280;
  padding: 12px;
}
.loading,
.error {
  padding: 12px;
  color: #6b7280;
}
.error {
  color: #dc2626;
}
.history-table .link-btn {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}
.panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.panel-filters {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.panel-filters .filter-row {
  flex: 1;
}
.btn-clear {
  padding: 6px 10px;
  font-size: 12px;
}
.panel-title {
  font-weight: 700;
}
.panel-sub {
  font-size: 12px;
  color: #6b7280;
}
.panel-loading {
  font-size: 12px;
  color: #64748b;
}
.panel-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
.decision-box {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.decision-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
}
.decision-item {
  display: flex;
  gap: 6px;
  align-items: center;
}
.decision-item .label {
  font-weight: 600;
  color: #334155;
}
.decision-item .value {
  color: #111827;
}
.decision-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.decision-actions input {
  padding: 6px 8px;
  min-height: 32px;
  width: 140px;
}
.decision-hint {
  font-size: 12px;
  color: #64748b;
}
.btn {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}
.btn:disabled {
  cursor: not-allowed;
  color: #94a3b8;
}
.detail-table {
  width: 100%;
  border-collapse: collapse;
}
.detail-table th,
.detail-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  font-size: 13px;
}
.detail-table td:nth-child(3) {
  white-space: nowrap;
}
.ds-btn { margin-left: 8px; padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-btn:hover { background: #e2e8f0; }
.ds-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.ds-modal { background: #fff; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.2); max-width: 700px; width: 90%; max-height: 80vh; overflow: auto; }
.ds-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #e5e7eb; }
.ds-header h3 { margin: 0; font-size: 15px; }
.ds-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #64748b; }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th, .ds-table td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.ds-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.ds-table td:first-child { white-space: nowrap; font-weight: 500; color: #2563eb; }
.ds-table td:nth-child(2) { font-family: monospace; font-size: 12px; color: #0f172a; }
</style>




