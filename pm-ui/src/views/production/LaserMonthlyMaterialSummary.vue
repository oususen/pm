<template>
  <div class="laser-material-summary">
    <div class="toolbar">
      <div class="field">
        <label>開始日</label>
        <input v-model="startDate" type="date" />
      </div>
      <span class="range-sep">〜</span>
      <div class="field">
        <label>終了日</label>
        <input v-model="endDate" type="date" />
      </div>
      <button class="btn primary" type="button" @click="loadSummary" :disabled="loading || !startDate || !endDate">
        集計
      </button>
      <button class="btn" type="button" @click="exportExcel" :disabled="loading || !materialTotals.length">
        Excel出力
      </button>
    </div>

    <div class="summary-note">
      完成品受注明細を月単位で集計し、確定がある納期は確定、ない納期は内示を採用します。
      必要材料数は、各完成品の採用数量を完成品取り数で割った値を合計して算出します。
    </div>

    <div v-if="message" class="summary-message" :class="messageTypeClass">
      {{ message }}
    </div>

    <div v-if="warnings.length" class="warning-panel">
      <div class="warning-title">注意</div>
      <div v-for="(warning, idx) in warnings" :key="`warn-${idx}`" class="warning-item">
        {{ warning }}
      </div>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">材料種類数</div>
        <div class="stat-value">{{ totals.material_type_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">対象パターン数</div>
        <div class="stat-value">{{ totals.pattern_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">必要材料数</div>
        <div class="stat-value">{{ formatSheetQty(totals.required_material_qty) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">総加工時間(時間)</div>
        <div class="stat-value">{{ formatNumber(totals.total_process_time_min / 60, 1) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">総重量(t)</div>
        <div class="stat-value">{{ totals.total_weight_kg != null ? formatNumber(totals.total_weight_kg / 1000, 2) : '-' }}</div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h3>材料別集計</h3>
        <div class="panel-caption">{{ periodLabel }}</div>
      </div>
      <div class="table-wrap">
        <table class="summary-table">
          <thead>
            <tr>
              <th>材料コード</th>
              <th>材料名</th>
              <th>単位</th>
              <th>比重</th>
              <th>縦(mm)</th>
              <th>横(mm)</th>
              <th>厚さ(mm)</th>
              <th>重量/枚(kg)</th>
              <th>使用パターン数</th>
              <th>必要材料数</th>
              <th>総重量(t)</th>
              <th>梱包入り数</th>
              <th>必要梱包数</th>
              <th>加工時間(時間)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in materialTotals" :key="`mat-${row.material_id || row.material_code}`">
              <td>{{ row.material_code }}</td>
              <td>{{ row.material_name }}</td>
              <td>{{ row.material_unit || '-' }}</td>
              <td class="num">{{ row.specific_gravity != null ? formatNumber(row.specific_gravity, 4) : '-' }}</td>
              <td class="num">{{ row.size_length != null ? formatNumber(row.size_length, 1) : '-' }}</td>
              <td class="num">{{ row.size_width != null ? formatNumber(row.size_width, 1) : '-' }}</td>
              <td class="num">{{ row.size_thickness != null ? formatNumber(row.size_thickness, 3) : '-' }}</td>
              <td class="num">{{ row.unit_weight_kg != null ? formatNumber(row.unit_weight_kg, 3) : '-' }}</td>
              <td class="num">{{ formatInteger(row.pattern_count) }}</td>
              <td class="num">{{ formatSheetQty(row.required_material_qty) }}</td>
              <td class="num">{{ row.total_weight_kg != null ? formatNumber(row.total_weight_kg / 1000, 3) : '-' }}</td>
              <td class="num">{{ row.pack_qty != null ? formatInteger(row.pack_qty) : '-' }}</td>
              <td class="num">{{ row.required_packages != null ? formatInteger(row.required_packages) : '-' }}</td>
              <td class="num">{{ formatNumber(row.total_process_time_min / 60, 2) }}</td>
            </tr>
            <tr v-if="!materialTotals.length">
              <td colspan="14" class="empty">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h3>設備別加工時間</h3>
        <div class="panel-caption">{{ periodLabel }}</div>
      </div>
      <div class="table-wrap">
        <table class="summary-table">
          <thead>
            <tr>
              <th>設備コード</th>
              <th>設備名</th>
              <th>使用パターン数</th>
              <th>総加工時間(時間)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in equipmentTotals" :key="`eq-${row.equipment_id || row.equipment_code}`">
              <td>{{ row.equipment_code || '-' }}</td>
              <td>{{ row.equipment_name || '-' }}</td>
              <td class="num">{{ formatInteger(row.pattern_count) }}</td>
              <td class="num">{{ formatNumber(row.total_process_time_min / 60, 2) }}</td>
            </tr>
            <tr v-if="!equipmentTotals.length">
              <td colspan="4" class="empty">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h3>パターン別明細</h3>
        <div class="panel-caption">材料予算用パターンのみ表示</div>
      </div>
      <div class="table-wrap">
        <table class="summary-table detail-table">
          <thead>
            <tr>
              <th>Ｐ№</th>
              <th>材料</th>
              <th>設備</th>
              <th>完成品内訳</th>
              <th>必要材料数</th>
              <th>総重量(t)</th>
              <th>必要梱包数</th>
              <th>加工時間(時間)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in patternRows" :key="`pattern-${row.pattern_id}`">
              <td class="pattern-no">{{ row.pattern_no }}</td>
              <td>
                <div>{{ row.material_code }}</div>
                <div class="sub-text">{{ row.material_name }}</div>
              </td>
              <td>
                <div>{{ row.equipment_code }}</div>
                <div class="sub-text">{{ row.equipment_name }}</div>
              </td>
              <td class="finished-cell">
                <div
                  v-for="item in row.finished_items"
                  :key="`${row.pattern_id}-${item.finished_product_id || item.finished_product_code}`"
                  class="finished-item"
                >
                  <div class="finished-title">
                    {{ item.finished_product_code }} - {{ item.finished_product_name }}
                  </div>
                  <div class="finished-meta">
                    完成品1個あたり材料={{ formatSheetQty(item.material_per_unit) }}
                    / 確定={{ formatNumber(item.firm_qty, 1) }}
                    / 内示={{ formatNumber(item.forecast_qty, 1) }}
                    / 採用={{ formatNumber(item.selected_qty, 1) }} ({{ basisLabel(item.selected_basis) }})
                  </div>
                  <div class="finished-meta">
                    この完成品の必要材料={{ formatSheetQty(item.required_material_qty) }}
                  </div>
                </div>
              </td>
              <td class="num strong">
                {{ formatSheetQty(row.required_material_qty) }}
                <span class="unit-text">{{ row.material_unit || '' }}</span>
              </td>
              <td class="num">{{ row.total_weight_kg != null ? formatNumber(row.total_weight_kg / 1000, 3) : '-' }}</td>
              <td class="num">{{ row.required_packages != null ? formatInteger(row.required_packages) : '-' }}</td>
              <td class="num">{{ formatNumber(row.total_process_time_min / 60, 2) }}</td>
            </tr>
            <tr v-if="!patternRows.length">
              <td colspan="8" class="empty">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

const today = new Date()
const toDateStr = (d) => d.toISOString().slice(0, 10)
const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0)

const startDate = ref(toDateStr(firstDay))
const endDate = ref(toDateStr(lastDay))
const loading = ref(false)
const message = ref('')
const messageType = ref('info')
const warnings = ref([])
const materialTotals = ref([])
const equipmentTotals = ref([])
const patternRows = ref([])
const totals = ref({
  material_type_count: 0,
  pattern_count: 0,
  required_material_qty: 0,
  total_process_time_min: 0,
  total_weight_kg: null,
})
const period = ref({
  start_date: '',
  end_date: '',
})

const messageTypeClass = computed(() => ({
  info: messageType.value === 'info',
  error: messageType.value === 'error',
}))

const periodLabel = computed(() => {
  const s = period.value.start_date || startDate.value
  const e = period.value.end_date || endDate.value
  if (!s || !e) return ''
  return `${s} ～ ${e}`
})

const formatNumber = (value, digits = 1) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return '0'
  return num.toLocaleString('ja-JP', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

const formatInteger = (value) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return '0'
  return Math.round(num).toLocaleString('ja-JP')
}

const formatSheetQty = (value) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return '0'
  return num.toLocaleString('ja-JP', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  })
}

const basisLabel = (value) => {
  const key = String(value || '').toUpperCase()
  if (key === 'FIRM') return '確定のみ'
  if (key === 'FORECAST') return '内示のみ'
  if (key === 'MIXED') return '日別で確定優先'
  return '対象なし'
}

const extractErrorMessage = (error) => {
  const payload = error?.response?.data
  if (payload?.detail) return String(payload.detail)
  if (typeof payload === 'string' && payload.trim()) return payload.trim()
  if (payload && typeof payload === 'object') {
    const firstKey = Object.keys(payload)[0]
    if (firstKey) {
      const value = payload[firstKey]
      if (Array.isArray(value) && value.length) return String(value[0])
      if (typeof value === 'string' && value) return value
    }
  }
  return '月所要材料集計の取得に失敗しました。'
}

const resetRows = () => {
  warnings.value = []
  materialTotals.value = []
  equipmentTotals.value = []
  patternRows.value = []
  totals.value = {
    material_type_count: 0,
    pattern_count: 0,
    required_material_qty: 0,
    total_process_time_min: 0,
    total_weight_kg: null,
  }
  period.value = {
    start_date: '',
    end_date: '',
  }
}

const loadSummary = async () => {
  if (!startDate.value || !endDate.value) return
  loading.value = true
  message.value = ''
  messageType.value = 'info'
  try {
    const res = await api.laserPatterns.getMonthlyMaterialSummary({ start_date: startDate.value, end_date: endDate.value })
    const data = res?.data || {}
    warnings.value = Array.isArray(data.warnings) ? data.warnings : []
    materialTotals.value = Array.isArray(data.material_totals) ? data.material_totals : []
    equipmentTotals.value = Array.isArray(data.equipment_totals) ? data.equipment_totals : []
    patternRows.value = Array.isArray(data.pattern_rows) ? data.pattern_rows : []
    totals.value = {
      material_type_count: Number(data?.totals?.material_type_count || 0),
      pattern_count: Number(data?.totals?.pattern_count || 0),
      required_material_qty: Number(data?.totals?.required_material_qty || 0),
      total_process_time_min: Number(data?.totals?.total_process_time_min || 0),
      total_weight_kg: data?.totals?.total_weight_kg != null ? Number(data.totals.total_weight_kg) : null,
    }
    period.value = {
      start_date: data.start_date || '',
      end_date: data.end_date || '',
    }
    message.value = patternRows.value.length
      ? '集計を更新しました。'
      : '対象月に材料予算用パターンの受注データがありません。'
  } catch (error) {
    resetRows()
    message.value = extractErrorMessage(error)
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportExcel = () => {
  if (!materialTotals.value.length) return

  const materialRows = [
    ['対象期間', periodLabel.value || ''],
    [],
  ]
  if (warnings.value.length) {
    materialRows.push(['注意'])
    warnings.value.forEach((warning) => {
      materialRows.push([warning])
    })
    materialRows.push([])
  }
  materialRows.push([
    '材料コード', '材料名', '単位',
    '比重', '縦(mm)', '横(mm)', '厚さ(mm)',
    '重量/枚(kg)', '使用パターン数', '必要材料数',
    '総重量(t)', '梱包入り数', '必要梱包数', '加工時間(時間)',
  ])
  materialTotals.value.forEach((row) => {
    materialRows.push([
      row.material_code || '',
      row.material_name || '',
      row.material_unit || '',
      row.specific_gravity != null ? Number(row.specific_gravity) : '',
      row.size_length != null ? Number(row.size_length) : '',
      row.size_width != null ? Number(row.size_width) : '',
      row.size_thickness != null ? Number(row.size_thickness) : '',
      row.unit_weight_kg != null ? Number(row.unit_weight_kg) : '',
      Number(row.pattern_count || 0),
      Number(row.required_material_qty || 0),
      row.total_weight_kg != null ? Number(row.total_weight_kg) / 1000 : '',
      row.pack_qty != null ? Number(row.pack_qty) : '',
      row.required_packages != null ? Number(row.required_packages) : '',
      Number((row.total_process_time_min || 0) / 60),
    ])
  })

  const equipmentRows = [
    ['対象期間', periodLabel.value || ''],
    [],
    ['設備コード', '設備名', '使用パターン数', '総加工時間(時間)'],
  ]
  equipmentTotals.value.forEach((row) => {
    equipmentRows.push([
      row.equipment_code || '',
      row.equipment_name || '',
      Number(row.pattern_count || 0),
      Number((row.total_process_time_min || 0) / 60),
    ])
  })

  const detailRows = [
    ['対象期間', periodLabel.value || ''],
    [],
    [
      'Ｐ№',
      '材料コード',
      '材料名',
      '設備コード',
      '設備名',
      '完成品コード',
      '完成品名',
      '採用区分',
      '完成品1個あたり材料',
      '確定数',
      '内示数',
      '採用数',
      '完成品必要材料数',
      '必要材料数',
      '総重量(t)',
      '必要梱包数',
      '加工時間(時間)',
    ],
  ]
  patternRows.value.forEach((row) => {
    ;(row.finished_items || []).forEach((item) => {
      detailRows.push([
        row.pattern_no || '',
        row.material_code || '',
        row.material_name || '',
        row.equipment_code || '',
        row.equipment_name || '',
        item.finished_product_code || '',
        item.finished_product_name || '',
        basisLabel(item.selected_basis),
        Number(item.material_per_unit || 0),
        Number(item.firm_qty || 0),
        Number(item.forecast_qty || 0),
        Number(item.selected_qty || 0),
        Number(item.required_material_qty || 0),
        Number(row.required_material_qty || 0),
        row.total_weight_kg != null ? Number(row.total_weight_kg) / 1000 : '',
        row.required_packages != null ? Number(row.required_packages) : '',
        Number((row.total_process_time_min || 0) / 60),
      ])
    })
  })

  const workbook = XLSX.utils.book_new()
  const materialSheet = XLSX.utils.aoa_to_sheet(materialRows)
  const equipmentSheet = XLSX.utils.aoa_to_sheet(equipmentRows)
  const detailSheet = XLSX.utils.aoa_to_sheet(detailRows)
  XLSX.utils.book_append_sheet(workbook, materialSheet, '材料別集計')
  XLSX.utils.book_append_sheet(workbook, equipmentSheet, '設備別加工時間')
  XLSX.utils.book_append_sheet(workbook, detailSheet, 'パターン別明細')
  XLSX.writeFile(workbook, `レーザ所要材料集計_${startDate.value || ''}_${endDate.value || ''}.xlsx`)
}

onMounted(() => {
  loadSummary()
})
</script>

<style scoped>
.laser-material-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field input {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  background: #fff;
}
.range-sep {
  display: flex;
  align-items: flex-end;
  padding-bottom: 4px;
  font-size: 14px;
  color: #475569;
}
.period-label {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 10px;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 6px;
  font-size: 13px;
  color: #166534;
  white-space: nowrap;
}
.btn {
  border: 1px solid #94a3b8;
  border-radius: 6px;
  background: #fff;
  height: 32px;
  padding: 0 12px;
  cursor: pointer;
}
.btn.primary {
  background: #0f766e;
  border-color: #0f766e;
  color: #fff;
}
.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.summary-note {
  font-size: 12px;
  color: #475569;
}
.summary-message {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
}
.summary-message.info {
  background: #ecfeff;
  color: #155e75;
}
.summary-message.error {
  background: #fef2f2;
  color: #b91c1c;
}
.warning-panel {
  border: 1px solid #f59e0b;
  background: #fffbeb;
  border-radius: 8px;
  padding: 10px 12px;
}
.warning-title {
  font-weight: 700;
  color: #92400e;
  margin-bottom: 4px;
}
.warning-item {
  font-size: 12px;
  color: #92400e;
  line-height: 1.5;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}
.stat-card {
  border: 1px solid #d7dfe8;
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  padding: 12px;
}
.stat-label {
  font-size: 12px;
  color: #64748b;
}
.stat-value {
  margin-top: 6px;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}
.panel {
  border: 1px solid #d7dfe8;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.panel-head h3 {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
}
.panel-caption {
  font-size: 12px;
  color: #64748b;
}
.table-wrap {
  overflow: auto;
}
.summary-table {
  width: 100%;
  border-collapse: collapse;
}
.summary-table th,
.summary-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 12px;
  vertical-align: top;
}
.summary-table th {
  background: #f8fafc;
  color: #334155;
  text-align: left;
  white-space: nowrap;
}
.summary-table .num {
  text-align: right;
  white-space: nowrap;
}
.summary-table .empty {
  text-align: center;
  color: #64748b;
  padding: 20px 10px;
}
.pattern-no {
  white-space: nowrap;
  font-weight: 700;
}
.sub-text {
  color: #64748b;
  margin-top: 2px;
}
.finished-cell {
  min-width: 420px;
}
.finished-item + .finished-item {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #d7dfe8;
}
.finished-title {
  font-weight: 700;
  color: #0f172a;
}
.finished-meta {
  margin-top: 2px;
  color: #475569;
  line-height: 1.5;
}
.strong {
  font-weight: 700;
  color: #0f172a;
}
.unit-text {
  margin-left: 4px;
  color: #64748b;
  font-weight: 400;
}
@media (max-width: 1300px) {
  .stat-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 900px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
  .finished-cell {
    min-width: 280px;
  }
}
</style>
