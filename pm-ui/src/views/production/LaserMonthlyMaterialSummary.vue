<template>
  <div class="laser-material-summary">
    <div class="toolbar-block">
      <div class="toolbar-row">
        <span class="toolbar-label budget-label">予算（加工期間） <DataSourceDialog title="レーザ月次材料集計" :sources="dsSources" /></span>
        <div class="field">
          <label>開始日</label>
          <input v-model="budgetStartDate" type="date" />
        </div>
        <span class="range-sep">〜</span>
        <div class="field">
          <label>終了日</label>
          <input v-model="budgetEndDate" type="date" />
        </div>
        <div class="field">
          <label>シフト日数</label>
          <input v-model.number="shiftDays" type="number" min="0" max="30" style="width:60px;" />
          <span class="field-hint">日後の注文を対象</span>
        </div>
        <div v-if="budgetOrderPeriod" class="period-label">受注納期: {{ budgetOrderPeriod }}</div>
      </div>
      <div class="toolbar-row">
        <button class="btn primary" type="button" @click="loadSummary" :disabled="loading || !budgetStartDate || !budgetEndDate || !actualStartDate || !actualEndDate">
          集計
        </button>
        <button class="btn" type="button" @click="exportExcel" :disabled="loading || !materialTotals.length">
          Excel出力
        </button>
      </div>
    </div>

    <div class="summary-note">
      <span class="note-badge budget">予算</span> 顧客注文（確定優先/内示）× 完成品取り数から必要材料数を計算。
      <span class="note-badge actual">実績</span> レーザ実績のパターン × ショット回数から実際使用材料を計算。
    </div>

    <div v-if="message" class="summary-message" :class="messageTypeClass">
      {{ message }}
    </div>

    <div v-if="warnings.length" class="warning-panel">
      <div class="warning-title" @click="warningOpen = !warningOpen" style="cursor:pointer;user-select:none;">
        <span>注意 ({{ warnings.length }}件)</span>
        <span class="warning-toggle">{{ warningOpen ? '▲ 閉じる' : '▼ 展開' }}</span>
      </div>
      <template v-if="warningOpen">
        <div v-for="(warning, idx) in warnings" :key="`warn-${idx}`" class="warning-item">
          {{ warning }}
        </div>
      </template>
    </div>

    <div class="kpi-panel budget-panel">
      <div class="kpi-panel-head">
        <span class="kpi-panel-title">予算</span>
        <span class="kpi-panel-desc">顧客注文 × 完成品取り数から計算</span>
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
          <div class="stat-label">必要材料数(枚)</div>
          <div class="stat-value">{{ formatSheetQty(totals.required_material_qty) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">加工時間(時間)</div>
          <div class="stat-value">{{ formatNumber(totals.total_process_time_min / 60, 1) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">重量(t)</div>
          <div class="stat-value">{{ totals.total_weight_kg != null ? formatNumber(totals.total_weight_kg / 1000, 1) : '-' }}</div>
        </div>
      </div>
    </div>

    <div class="kpi-panel actual-panel">
      <div class="kpi-panel-head">
        <span class="kpi-panel-title">実績</span>
        <span class="kpi-panel-desc">実績パターン × ショット回数から計算</span>
      </div>
      <div class="stat-grid stat-grid-3">
        <div class="stat-card actual-card">
          <div class="stat-label">使用枚数</div>
          <div class="stat-value">{{ formatInteger(actualTotals.total_shot_count) }}</div>
        </div>
        <div class="stat-card actual-card">
          <div class="stat-label">加工時間(時間)</div>
          <div class="stat-value">{{ formatNumber(actualTotals.total_process_time_min / 60, 1) }}</div>
        </div>
        <div class="stat-card actual-card">
          <div class="stat-label">重量(t)</div>
          <div class="stat-value">{{ actualTotals.total_weight_kg != null ? formatNumber(actualTotals.total_weight_kg / 1000, 1) : '-' }}</div>
        </div>
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
              <td class="num">{{ row.total_weight_kg != null ? formatNumber(row.total_weight_kg / 1000, 1) : '-' }}</td>
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
                    / 1個あたり加工時間={{ formatNumber(Number(item.material_per_unit || 0) * Number(row.process_time_min || 0), 2) }}分
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
              <td class="num">{{ row.total_weight_kg != null ? formatNumber(row.total_weight_kg / 1000, 1) : '-' }}</td>
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
    <div class="panel">
      <div class="panel-head">
        <h3>実績材料使用集計</h3>
        <div class="panel-caption">{{ periodLabel }}</div>
      </div>
      <div class="table-wrap">
        <table class="summary-table">
          <thead>
            <tr>
              <th>材料コード</th>
              <th>材料名</th>
              <th>重量/枚(kg)</th>
              <th>実績枚数</th>
              <th>実績重量(t)</th>
              <th>実績加工時間(時間)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in actualMaterialTotals" :key="`act-mat-${row.material_id || row.material_code}`">
              <td>{{ row.material_code }}</td>
              <td>{{ row.material_name }}</td>
              <td class="num">{{ row.unit_weight_kg != null ? formatNumber(row.unit_weight_kg, 3) : '-' }}</td>
              <td class="num">{{ formatInteger(row.actual_shot_count) }}</td>
              <td class="num">{{ row.actual_weight_kg != null ? formatNumber(row.actual_weight_kg / 1000, 3) : '-' }}</td>
              <td class="num">{{ formatNumber(row.actual_process_time_min / 60, 2) }}</td>
            </tr>
            <tr v-if="!actualMaterialTotals.length">
              <td colspan="6" class="empty">対象期間の実績データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h3>実績設備別加工時間</h3>
      </div>
      <div class="table-wrap">
        <table class="summary-table">
          <thead>
            <tr>
              <th>設備コード</th>
              <th>設備名</th>
              <th>実績ショット数</th>
              <th>実績加工時間(時間)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in actualEquipmentTotals" :key="`act-eq-${row.equipment_id || row.equipment_code}`">
              <td>{{ row.equipment_code || '-' }}</td>
              <td>{{ row.equipment_name || '-' }}</td>
              <td class="num">{{ formatInteger(row.actual_shot_count) }}</td>
              <td class="num">{{ formatNumber(row.actual_process_time_min / 60, 2) }}</td>
            </tr>
            <tr v-if="!actualEquipmentTotals.length">
              <td colspan="4" class="empty">対象期間の実績データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 期間別材料発注量 -->
    <div class="panel order-summary-panel">
      <div class="panel-head">
        <h3>期間別材料発注量</h3>
      </div>
      <div class="order-toolbar">
        <div class="field">
          <label>開始日</label>
          <input v-model="orderSummaryStart" type="date" />
        </div>
        <span class="range-sep">〜</span>
        <div class="field">
          <label>終了日</label>
          <input v-model="orderSummaryEnd" type="date" />
        </div>
        <button class="btn primary" type="button" @click="loadOrderSummary" :disabled="orderSummaryLoading || !orderSummaryStart || !orderSummaryEnd">集計</button>
        <button class="btn" type="button" @click="showManualForm = !showManualForm">手動追加</button>
      </div>

      <!-- 手動追加フォーム -->
      <div v-if="showManualForm" class="manual-form">
        <div class="manual-form-row">
          <div class="field">
            <label>材料</label>
            <select v-model="manualMaterialId">
              <option value="">-- 選択 --</option>
              <option v-for="m in materialOptions" :key="m.id" :value="m.id">{{ m.product_code }} {{ m.product_name }}</option>
            </select>
          </div>
          <div class="field">
            <label>仕入先</label>
            <select v-model="manualSupplier">
              <option value="MEISEI">名成鋼機</option>
              <option value="SATO">佐藤商事</option>
            </select>
          </div>
          <div class="field">
            <label>納期</label>
            <input v-model="manualDeliveryDate" type="date" />
          </div>
          <div class="field">
            <label>ロット数</label>
            <input v-model.number="manualOrderLots" type="number" min="0" style="width:70px;" />
          </div>
          <div class="field">
            <label>ロット倍数</label>
            <input v-model.number="manualLotMultiple" type="number" min="0" style="width:70px;" />
          </div>
          <div class="field">
            <label>端数枚数</label>
            <input v-model.number="manualOrderSheets" type="number" min="0" style="width:70px;" />
          </div>
          <button class="btn primary" type="button" @click="saveManualOrder" :disabled="!manualMaterialId || !manualDeliveryDate || (manualOrderLots === 0 && manualOrderSheets === 0)">登録</button>
        </div>
      </div>

      <div v-if="orderSummaryMsg" class="summary-message" :class="orderSummaryMsgType === 'error' ? 'error' : 'info'">{{ orderSummaryMsg }}</div>

      <div class="table-wrap" v-if="orderSummaryDates.length">
        <table class="summary-table order-table">
          <thead>
            <tr>
              <th rowspan="2" class="sticky-col col-code">材料コード</th>
              <th rowspan="2" class="sticky-col col-name">材料名</th>
              <th rowspan="2" class="sticky-col col-supplier">仕入先</th>
              <th rowspan="2" class="sticky-col col-lot">倍数</th>
              <th v-for="d in orderSummaryDates" :key="'h1-'+d" :class="['date-col', weekdayClass(d)]">{{ formatDateShort(d) }}</th>
              <th rowspan="2">合計</th>
            </tr>
            <tr>
              <th v-for="d in orderSummaryDates" :key="'h2-'+d" :class="['date-col dow-row', weekdayClass(d)]">{{ weekdayLabel(d) }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in orderSummaryRows" :key="`${row.material_id}-${row.supplier}`">
              <!-- ロット数行 -->
              <tr>
                <td class="sticky-col col-code" rowspan="3">{{ row.material_code }}</td>
                <td class="sticky-col col-name" rowspan="3">{{ row.material_name }}</td>
                <td class="sticky-col col-supplier" rowspan="3">{{ row.supplier_label }}</td>
                <td class="sticky-col col-lot num" rowspan="3">{{ row.lot_multiple || '-' }}</td>
                <td v-for="d in orderSummaryDates" :key="`lot-${row.material_id}-${row.supplier}-${d}`" :class="['num', weekdayClass(d)]">
                  <span v-if="row.daily[d]?.order_lots">{{ row.daily[d].order_lots }}L</span>
                  <span v-if="row.daily[d]?.order_sheets" class="sheets-extra">+{{ row.daily[d].order_sheets }}</span>
                  <span v-if="row.daily[d]?.manual_ids?.length" class="manual-badge" @click="deleteManual(row.daily[d].manual_ids)" title="手動 (クリックで削除)">M</span>
                </td>
                <td class="num total-col">{{ rowTotalLots(row) }}L<span v-if="rowTotalSheets(row)" class="sheets-extra">+{{ rowTotalSheets(row) }}</span></td>
              </tr>
              <!-- 枚数行 -->
              <tr class="sub-row">
                <td v-for="d in orderSummaryDates" :key="`sheets-${row.material_id}-${row.supplier}-${d}`" :class="['num', weekdayClass(d)]">
                  {{ row.daily[d]?.total_sheets || '' }}
                </td>
                <td class="num total-col">{{ rowTotalAllSheets(row) }}</td>
              </tr>
              <!-- 重量行 -->
              <tr class="sub-row weight-row">
                <td v-for="d in orderSummaryDates" :key="`wt-${row.material_id}-${row.supplier}-${d}`" :class="['num', weekdayClass(d)]">
                  {{ row.daily[d]?.weight_kg != null && row.daily[d]?.total_sheets ? formatNumber(row.daily[d].weight_kg / 1000, 3) + 't' : '' }}
                </td>
                <td class="num total-col">{{ row.sheet_weight_kg ? formatNumber(rowTotalAllSheets(row) * row.sheet_weight_kg / 1000, 3) + 't' : '' }}</td>
              </tr>
            </template>
            <!-- 合計行 -->
            <tr class="total-row" v-if="orderSummaryRows.length">
              <td class="sticky-col col-code" colspan="4"><strong>合計</strong></td>
              <td v-for="d in orderSummaryDates" :key="`total-${d}`" :class="['num', weekdayClass(d)]">
                <div>{{ dailyTotalSheets(d) }}枚</div>
                <div class="weight-text">{{ formatNumber(dailyTotalWeight(d) / 1000, 3) }}t</div>
              </td>
              <td class="num total-col">
                <div>{{ grandTotalSheets() }}枚</div>
                <div class="weight-text">{{ formatNumber(grandTotalWeight() / 1000, 3) }}t</div>
              </td>
            </tr>
            <tr v-if="!orderSummaryRows.length && !orderSummaryLoading">
              <td :colspan="4 + orderSummaryDates.length + 1" class="empty">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, onMounted, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_laser_pattern', desc: 'レーザパターン（月次材料集計）' },
]

const today = new Date()
const toDateStr = (d) => formatISODate(d)
const addDays = (dateStr, days) => {
  const d = new Date(dateStr)
  d.setDate(d.getDate() + days)
  return toDateStr(d)
}
const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0)

const budgetStartDate = ref(toDateStr(firstDay))
const budgetEndDate = ref(toDateStr(lastDay))
const shiftDays = ref(5)
const actualStartDate = ref(toDateStr(firstDay))
const actualEndDate = ref(toDateStr(lastDay))

// 予算加工期間を実績期間に同期
watch(budgetStartDate, (v) => { actualStartDate.value = v })
watch(budgetEndDate, (v) => { actualEndDate.value = v })

// APIから返ってくる営業日計算済みの受注納期期間（集計後に更新）
const orderStartDate = ref('')
const orderEndDate = ref('')
const budgetOrderPeriod = computed(() => {
  if (!orderStartDate.value || !orderEndDate.value) return ''
  return `${orderStartDate.value} ～ ${orderEndDate.value}`
})
// 入力変更時は表示をクリア（再集計が必要）
watch([budgetStartDate, budgetEndDate, shiftDays], () => {
  orderStartDate.value = ''
  orderEndDate.value = ''
})
const loading = ref(false)
const message = ref('')
const messageType = ref('info')
const warnings = ref([])
const warningDetails = ref([])
const productPatternList = ref([])
const warningOpen = ref(false)
const materialTotals = ref([])
const equipmentTotals = ref([])
const patternRows = ref([])
const actualMaterialTotals = ref([])
const actualEquipmentTotals = ref([])
const actualTotals = ref({ total_shot_count: 0, total_weight_kg: null, total_process_time_min: 0 })
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
  const s = period.value.start_date || budgetStartDate.value
  const e = period.value.end_date || budgetEndDate.value
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
    maximumFractionDigits: 0,
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
  warningDetails.value = []
  productPatternList.value = []
  materialTotals.value = []
  equipmentTotals.value = []
  patternRows.value = []
  actualMaterialTotals.value = []
  actualEquipmentTotals.value = []
  actualTotals.value = { total_shot_count: 0, total_weight_kg: null, total_process_time_min: 0 }
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
  if (!budgetStartDate.value || !budgetEndDate.value || !actualStartDate.value || !actualEndDate.value) return
  loading.value = true
  message.value = ''
  messageType.value = 'info'
  try {
    const res = await api.laserPatterns.getMonthlyMaterialSummary({
      start_date: budgetStartDate.value,
      end_date: budgetEndDate.value,
      shift_days: shiftDays.value ?? 0,
      actual_start_date: actualStartDate.value,
      actual_end_date: actualEndDate.value,
    })
    const data = res?.data || {}
    warnings.value = Array.isArray(data.warnings) ? data.warnings : []
    warningDetails.value = Array.isArray(data.warning_details) ? data.warning_details : []
    productPatternList.value = Array.isArray(data.product_pattern_list) ? data.product_pattern_list : []
    materialTotals.value = Array.isArray(data.material_totals) ? data.material_totals : []
    equipmentTotals.value = Array.isArray(data.equipment_totals) ? data.equipment_totals : []
    patternRows.value = Array.isArray(data.pattern_rows) ? data.pattern_rows : []
    actualMaterialTotals.value = Array.isArray(data.actual_material_totals) ? data.actual_material_totals : []
    actualEquipmentTotals.value = Array.isArray(data.actual_equipment_totals) ? data.actual_equipment_totals : []
    actualTotals.value = data.actual_totals || { total_shot_count: 0, total_weight_kg: null, total_process_time_min: 0 }
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
    orderStartDate.value = data.order_start_date || ''
    orderEndDate.value = data.order_end_date || ''
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

  const r2 = (v) => (v != null && v !== '' ? Math.round(Number(v) * 100) / 100 : '')

  // ── 予算: 材料別集計 ──
  const materialRows = [
    ['対象期間', periodLabel.value || ''],
    [],
    [
      '材料コード', '材料名', '単位',
      '比重', '縦(mm)', '横(mm)', '厚さ(mm)',
      '重量/枚(kg)', '使用パターン数', '必要材料数',
      '総重量(t)', '梱包入り数', '必要梱包数', '加工時間(時間)',
    ],
  ]
  let sumMatQty = 0, sumMatWeightT = 0, sumMatPkg = 0, sumMatTimeH = 0
  materialTotals.value.forEach((row) => {
    const qty = Number(row.required_material_qty || 0)
    const weightT = row.total_weight_kg != null ? Number(row.total_weight_kg) / 1000 : 0
    const pkg = row.required_packages != null ? Number(row.required_packages) : 0
    const timeH = (row.total_process_time_min || 0) / 60
    sumMatQty += qty
    sumMatWeightT += weightT
    sumMatPkg += pkg
    sumMatTimeH += timeH
    materialRows.push([
      row.material_code || '',
      row.material_name || '',
      row.material_unit || '',
      row.specific_gravity != null ? Number(row.specific_gravity) : '',
      row.size_length != null ? Number(row.size_length) : '',
      row.size_width != null ? Number(row.size_width) : '',
      row.size_thickness != null ? Number(row.size_thickness) : '',
      r2(row.unit_weight_kg),
      Number(row.pattern_count || 0),
      r2(qty),
      row.total_weight_kg != null ? r2(weightT) : '',
      row.pack_qty != null ? Number(row.pack_qty) : '',
      row.required_packages != null ? Number(pkg) : '',
      r2(timeH),
    ])
  })
  materialRows.push(['合計', '', '', '', '', '', '', '', '', r2(sumMatQty), r2(sumMatWeightT), '', r2(sumMatPkg), r2(sumMatTimeH)])

  // ── 予算: 設備別 ──
  const equipmentRows = [
    ['対象期間', periodLabel.value || ''],
    [],
    ['設備コード', '設備名', '使用パターン数', '総加工時間(時間)'],
  ]
  let sumEqBudgetPat = 0, sumEqBudgetTimeH = 0
  equipmentTotals.value.forEach((row) => {
    const pat = Number(row.pattern_count || 0)
    const timeH = (row.total_process_time_min || 0) / 60
    sumEqBudgetPat += pat
    sumEqBudgetTimeH += timeH
    equipmentRows.push([
      row.equipment_code || '',
      row.equipment_name || '',
      pat,
      r2(timeH),
    ])
  })
  equipmentRows.push(['合計', '', sumEqBudgetPat, r2(sumEqBudgetTimeH)])

  // ── 予算: パターン別明細 ──
  const detailRows = [
    ['対象期間', periodLabel.value || ''],
    [],
    [
      'Ｐ№', '材料コード', '材料名', '設備コード', '設備名',
      '完成品コード', '完成品名', '採用区分',
      '完成品1個あたり材料', '完成品1個あたり加工時間(分)',
      '確定数', '内示数', '採用数',
      '完成品必要材料数', '総重量(t)', '必要梱包数', '加工時間(時間)',
    ],
  ]
  let sumDetMatQty = 0, sumDetWeightT = 0, sumDetPkg = 0, sumDetTimeH = 0
  // パターン別明細は完成品＋パターン単位で計算（パターン合計をそのまま繰り返すと、
  // 確定・内示がない完成品の行にも他の完成品分の重量・梱包数・加工時間が乗って見えるため）
  patternRows.value.forEach((row) => {
    const unitWeightKg = row.unit_weight_kg != null ? Number(row.unit_weight_kg) : null
    const packQty = row.pack_qty != null ? Number(row.pack_qty) : null
    const processTimeMin = Number(row.process_time_min || 0)
    ;(row.finished_items || []).forEach((item) => {
      const itemQty = Number(item.required_material_qty || 0)
      const itemWeightT = unitWeightKg != null ? (itemQty * unitWeightKg) / 1000 : null
      const itemTimeH = (itemQty * processTimeMin) / 60
      const itemPkg = packQty ? Math.ceil(itemQty / packQty) : null
      sumDetMatQty += itemQty
      sumDetWeightT += itemWeightT != null ? itemWeightT : 0
      sumDetPkg += itemPkg != null ? itemPkg : 0
      sumDetTimeH += itemTimeH
      detailRows.push([
        row.pattern_no || '',
        row.material_code || '',
        row.material_name || '',
        row.equipment_code || '',
        row.equipment_name || '',
        item.finished_product_code || '',
        item.finished_product_name || '',
        basisLabel(item.selected_basis),
        r2(item.material_per_unit),
        r2(Number(item.material_per_unit || 0) * processTimeMin),
        r2(item.firm_qty),
        r2(item.forecast_qty),
        r2(item.selected_qty),
        r2(itemQty),
        itemWeightT != null ? r2(itemWeightT) : '',
        itemPkg != null ? itemPkg : '',
        r2(itemTimeH),
      ])
    })
  })
  detailRows.push(['合計', '', '', '', '', '', '', '', '', '', '', '', '', r2(sumDetMatQty), r2(sumDetWeightT), r2(sumDetPkg), r2(sumDetTimeH)])

  // ── 実績: 材料別集計 ──
  const actualMaterialRows = [
    ['実績期間', `${actualStartDate.value || ''} ～ ${actualEndDate.value || ''}`],
    [],
    ['材料コード', '材料名', '重量/枚(kg)', '実績枚数', '実績重量(t)', '実績加工時間(時間)'],
  ]
  let sumActualShots = 0, sumActualWeightT = 0, sumActualTimeH = 0
  actualMaterialTotals.value.forEach((row) => {
    const shots = Number(row.actual_shot_count || 0)
    const weightT = row.actual_weight_kg != null ? Number(row.actual_weight_kg) / 1000 : 0
    const timeH = (row.actual_process_time_min || 0) / 60
    sumActualShots += shots
    sumActualWeightT += weightT
    sumActualTimeH += timeH
    actualMaterialRows.push([
      row.material_code || '',
      row.material_name || '',
      r2(row.unit_weight_kg),
      r2(shots),
      row.actual_weight_kg != null ? r2(weightT) : '',
      r2(timeH),
    ])
  })
  actualMaterialRows.push(['合計', '', '', r2(sumActualShots), r2(sumActualWeightT), r2(sumActualTimeH)])

  // ── 実績: 設備別 ──
  const actualEquipmentRows = [
    ['実績期間', `${actualStartDate.value || ''} ～ ${actualEndDate.value || ''}`],
    [],
    ['設備コード', '設備名', '実績ショット数', '実績加工時間(時間)'],
  ]
  let sumEqShots = 0, sumEqTimeH = 0
  actualEquipmentTotals.value.forEach((row) => {
    const shots = Number(row.actual_shot_count || 0)
    const timeH = (row.actual_process_time_min || 0) / 60
    sumEqShots += shots
    sumEqTimeH += timeH
    actualEquipmentRows.push([
      row.equipment_code || '',
      row.equipment_name || '',
      r2(shots),
      r2(timeH),
    ])
  })
  actualEquipmentRows.push(['合計', '', r2(sumEqShots), r2(sumEqTimeH)])

  // ── 完成品使用パターン一覧（全件） ──
  const productPatternRows = [['完成品番号', '完成品名', '使用パターン']]
  productPatternList.value.forEach((d) => {
    productPatternRows.push([
      d.product_code || '',
      d.product_name || '',
      Array.isArray(d.pattern_nos) ? d.pattern_nos.join(', ') : '',
    ])
  })
  if (!productPatternList.value.length) {
    productPatternRows.push(['', 'データがありません。', ''])
  }

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(materialRows), '予算_材料別集計')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(equipmentRows), '予算_設備別加工時間')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(detailRows), '予算_パターン別明細')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(actualMaterialRows), '実績_材料別集計')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(actualEquipmentRows), '実績_設備別加工時間')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(productPatternRows), '完成品使用パターン一覧')
  XLSX.writeFile(workbook, `レーザ所要材料集計_${budgetStartDate.value || ''}_${budgetEndDate.value || ''}.xlsx`)
}

// ── 期間別材料発注量 ──
const orderSummaryStart = ref(toDateStr(firstDay))
const orderSummaryEnd = ref(toDateStr(lastDay))
const orderSummaryLoading = ref(false)
const orderSummaryMsg = ref('')
const orderSummaryMsgType = ref('info')
const orderSummaryDates = ref([])
const orderSummaryRows = ref([])
const showManualForm = ref(false)
const materialOptions = ref([])

const manualMaterialId = ref('')
const manualSupplier = ref('MEISEI')
const manualDeliveryDate = ref('')
const manualOrderLots = ref(0)
const manualLotMultiple = ref(100)
const manualOrderSheets = ref(0)

const formatDateShort = (d) => {
  const parts = d.split('-')
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`
}
const weekdayLabel = (d) => ['日', '月', '火', '水', '木', '金', '土'][new Date(d).getDay()]
const weekdayClass = (d) => {
  const dow = new Date(d).getDay()
  if (dow === 0) return 'sun'
  if (dow === 6) return 'sat'
  return ''
}

const rowTotalLots = (row) => orderSummaryDates.value.reduce((s, d) => s + (row.daily[d]?.order_lots || 0), 0)
const rowTotalSheets = (row) => orderSummaryDates.value.reduce((s, d) => s + (row.daily[d]?.order_sheets || 0), 0)
const rowTotalAllSheets = (row) => orderSummaryDates.value.reduce((s, d) => s + (row.daily[d]?.total_sheets || 0), 0)
const dailyTotalSheets = (d) => orderSummaryRows.value.reduce((s, r) => s + (r.daily[d]?.total_sheets || 0), 0)
const dailyTotalWeight = (d) => orderSummaryRows.value.reduce((s, r) => {
  const w = r.daily[d]?.weight_kg
  return s + (w || 0)
}, 0)
const grandTotalSheets = () => orderSummaryDates.value.reduce((s, d) => s + dailyTotalSheets(d), 0)
const grandTotalWeight = () => orderSummaryDates.value.reduce((s, d) => s + dailyTotalWeight(d), 0)

const loadOrderSummary = async () => {
  if (!orderSummaryStart.value || !orderSummaryEnd.value) return
  orderSummaryLoading.value = true
  orderSummaryMsg.value = ''
  try {
    const res = await api.laserWeeklyPlans.getMaterialOrderSummary(orderSummaryStart.value, orderSummaryEnd.value)
    const data = res?.data || {}
    orderSummaryDates.value = data.dates || []
    orderSummaryRows.value = data.rows || []
    if (!data.rows?.length) {
      orderSummaryMsg.value = '対象期間の発注データがありません。'
    }
  } catch (e) {
    orderSummaryMsg.value = e?.response?.data?.detail || '発注量集計の取得に失敗しました。'
    orderSummaryMsgType.value = 'error'
    orderSummaryDates.value = []
    orderSummaryRows.value = []
  } finally {
    orderSummaryLoading.value = false
  }
}

const loadMaterialOptions = async () => {
  try {
    const items = await api.products.getAllProducts({ category: 'MATERIAL' })
    materialOptions.value = items
  } catch {
    materialOptions.value = []
  }
}

const saveManualOrder = async () => {
  try {
    await api.laserWeeklyPlans.createMaterialOrderManual({
      material_id: manualMaterialId.value,
      supplier: manualSupplier.value,
      delivery_date: manualDeliveryDate.value,
      order_lots: manualOrderLots.value || 0,
      lot_multiple: manualLotMultiple.value || 0,
      order_sheets: manualOrderSheets.value || 0,
    })
    manualOrderLots.value = 0
    manualOrderSheets.value = 0
    await loadOrderSummary()
  } catch (e) {
    orderSummaryMsg.value = e?.response?.data?.detail || '手動追加に失敗しました。'
    orderSummaryMsgType.value = 'error'
  }
}

const deleteManual = async (ids) => {
  if (!ids?.length || !confirm('手動行を削除しますか？')) return
  try {
    for (const id of ids) {
      await api.laserWeeklyPlans.deleteMaterialOrderManual(id)
    }
    await loadOrderSummary()
  } catch (e) {
    orderSummaryMsg.value = e?.response?.data?.detail || '削除に失敗しました。'
    orderSummaryMsgType.value = 'error'
  }
}

onMounted(() => {
  loadSummary()
  loadMaterialOptions()
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
.toolbar-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toolbar-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.toolbar-label {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  align-self: flex-end;
  margin-bottom: 4px;
}
.toolbar-label.budget-label {
  background: #1e40af;
  color: #fff;
}
.toolbar-label.actual-label {
  background: #166534;
  color: #fff;
}
.field-hint {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
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
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.note-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
}
.note-badge.budget {
  background: #dbeafe;
  color: #1e40af;
}
.note-badge.actual {
  background: #dcfce7;
  color: #166534;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.warning-toggle {
  font-size: 11px;
  font-weight: 400;
}
.warning-item {
  font-size: 12px;
  color: #92400e;
  line-height: 1.5;
}
.kpi-panel {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #d7dfe8;
}
.kpi-panel-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
}
.kpi-panel-title {
  font-size: 13px;
  font-weight: 700;
}
.kpi-panel-desc {
  font-size: 11px;
  opacity: 0.8;
}
.budget-panel .kpi-panel-head {
  background: #1e40af;
  color: #fff;
}
.budget-panel {
  border-color: #1e40af;
}
.actual-panel .kpi-panel-head {
  background: #166534;
  color: #fff;
}
.actual-panel {
  border-color: #166534;
}
.kpi-panel .stat-grid {
  padding: 10px;
  background: #fff;
}
.actual-card {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%) !important;
  border-color: #86efac !important;
}
.stat-grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
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
/* 期間別材料発注量 */
.order-summary-panel {
  margin-top: 16px;
}
.order-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
}
.manual-form {
  padding: 8px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.manual-form-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.manual-form select {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 6px;
  background: #fff;
  max-width: 260px;
}
.order-table {
  font-size: 11px;
}
.order-table th,
.order-table td {
  padding: 3px 5px;
  white-space: nowrap;
}
.order-table .date-col {
  min-width: 44px;
  text-align: center;
}
.order-table .dow-row {
  font-size: 10px;
  color: #64748b;
}
.sticky-col {
  position: sticky;
  background: #fff;
  z-index: 1;
}
.col-code { left: 0; min-width: 80px; }
.col-name { left: 80px; min-width: 100px; }
.col-supplier { left: 180px; min-width: 60px; }
.col-lot { left: 240px; min-width: 40px; }
.sub-row td {
  border-top: none !important;
  padding-top: 0 !important;
  font-size: 10px;
  color: #475569;
}
.weight-row td {
  color: #64748b;
  font-size: 10px;
}
.total-row td {
  background: #f0f9ff;
  font-weight: 700;
  border-top: 2px solid #0ea5e9;
}
.total-col {
  background: #f8fafc;
  font-weight: 700;
}
.weight-text {
  font-size: 10px;
  color: #64748b;
  font-weight: 400;
}
.sheets-extra {
  font-size: 10px;
  color: #7c3aed;
}
.manual-badge {
  display: inline-block;
  margin-left: 2px;
  padding: 0 3px;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  background: #f97316;
  border-radius: 3px;
  cursor: pointer;
}
.sun { background: #fef2f2 !important; }
.sat { background: #eff6ff !important; }
</style>




