<template>
  <div class="plan-container">
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="field">
          <label>ライン</label>
          <select v-model="selectedLine" @change="loadData">
            <option v-for="line in lines" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>表示開始日</label>
          <input type="date" v-model="startDate" @change="refreshDates" />
        </div>
        <div class="field">
          <label>期間</label>
          <select v-model.number="horizonDays" @change="refreshDates">
            <option :value="30">30日</option>
            <option :value="60">60日</option>
            <option :value="90">90日</option>
          </select>
        </div>
        <div class="field">
          <label>検索</label>
          <input type="text" v-model="keyword" placeholder="品番/品名で絞り込み" />
        </div>
      </div>
      <div class="toolbar-right">
        <div class="field">
          <label>デフォルト開始時刻</label>
          <input
            type="text"
            inputmode="numeric"
            :value="finalProcessStartTime"
            @input="onDefaultTimeInput($event.target.value)"
            @blur="onDefaultTimeInput($event.target.value, true)"
            placeholder="00:00"
            maxlength="5"
            title="日別設定がない場合に使用される開始時刻"
          />
        </div>
        <div class="field checkbox-field">
          <label>
            <input type="checkbox" v-model="adjustToBreakEnd" />
            休憩明けに補正
          </label>
        </div>
        <button class="btn" @click="resetRows" :disabled="processing || !rows.length">クリア</button>
        <button class="btn" @click="openChangeReasonDialog" :disabled="processing">計画変更</button>
        <button class="btn" @click="savePlan" :disabled="processing || !rows.length || !selectedLine">保存</button>
        <button class="btn primary" @click="doPickup" :disabled="processing || !selectedLine">取り込み</button>
        <button class="btn accent" @click="toggleProcessGantt" :disabled="processing || !selectedLine">
          {{ showProcessGantt ? '工程ガントを閉じる' : '工程ガント表示' }}
        </button>
        <button class="btn accent" @click="toggleProcessLoad" :disabled="processing || !selectedLine">
          {{ showProcessLoad ? '工程負荷を閉じる' : '工程負荷表示' }}
        </button>
      </div>
    </div>

    <div class="grid-wrapper" ref="gridWrapperRef">
      <table class="plan-grid" :style="{ minWidth: tableMinWidth + 'px' }">
        <thead>
          <tr class="head-level1">
            <th rowspan="2" class="sticky-col number-col">No</th>
            <th rowspan="2" class="sticky-col code-col">品番</th>
            <th rowspan="2" class="sticky-col name-col">品名</th>
            <th
              v-for="(c, colIdx) in dateColumns"
              :key="c.key"
              colspan="6"
              class="date-head day-end"
              :class="c.dayClass"
            >
              <div class="date-header-content-horizontal">
                <span class="date-label">{{ c.label }}</span>
                <input
                  type="text"
                  inputmode="numeric"
                  :value="dailySettings[c.key]?.final_process_start_time || ''"
                  @input="onDailySettingTimeChange(c.key, $event.target.value)"
                  @blur="onDailySettingTimeBlur(c.key)"
                  class="time-input-inline"
                  :placeholder="finalProcessStartTime || '08:00'"
                  maxlength="5"
                  :title="`最終工程開始時刻（未設定時はデフォルト ${finalProcessStartTime || '08:00'} を使用）`"
                />
                <span v-if="getWorkTimeLabel(c.key)" class="work-time-label">
                  {{ getWorkTimeLabel(c.key) }}
                </span>
              </div>
            </th>
          </tr>
          <tr class="head-level2">
            <template v-for="(c, colIdx) in dateColumns" :key="c.key">
              <th class="mini" :class="c.dayClass">需要</th>
              <th class="mini" :class="c.dayClass">実績</th>
              <th class="mini" :class="c.dayClass">在庫</th>
              <th class="mini" :class="c.dayClass">計画</th>
              <th class="mini" :class="c.dayClass">順序</th>
              <th class="mini day-end" :class="c.dayClass">計画在庫</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in filteredRows" :key="row.id">
            <td class="sticky-col number-col">
              <div class="row-controls">
                <span class="product-info">{{ idx + 1 }}</span>
                <div class="reorder">
                  <button class="mini-btn" @click="moveRow(row.id, -1)" :disabled="rowIndex(row.id) <= 0">↑</button>
                  <button class="mini-btn" @click="moveRow(row.id, 1)" :disabled="rowIndex(row.id) >= rows.length - 1">↓</button>
                </div>
              </div>
            </td>
            <td class="sticky-col code-col">
              <span class="product-info">{{ row.product_code || getProductCode(row.product_id) }}</span>
            </td>
            <td class="sticky-col name-col">
              <span class="product-info">{{ row.product_name || getProductName(row.product_id) }}</span>
            </td>
            <template v-for="(c, colIdx) in dateColumns" :key="c.key">
              <td class="num" :class="c.dayClass">
                <span class="readonly-value">{{ displayValue(row.daily?.[c.key]?.demand) }}</span>
              </td>
              <td class="num" :class="c.dayClass">
                <span class="readonly-value">{{ displayValue(row.daily?.[c.key]?.actual) }}</span>
              </td>
              <td class="num stock" :class="c.dayClass">
                <span class="readonly-value">{{ displayValue(getStockDisplay(row, colIdx)) }}</span>
              </td>
              <td class="num plan" :class="c.dayClass">
                <div class="lot-stack">
                  <input
                    type="text"
                    inputmode="decimal"
                    :value="row.daily?.[c.key]?.plan === 0 || row.daily?.[c.key]?.plan === '' || row.daily?.[c.key]?.plan == null ? '' : row.daily?.[c.key]?.plan"
                    @input="onPlanInput(row, c.key, $event.target.value)"
                    :data-row="idx"
                    :data-col="colIdx"
                    data-field="plan"
                    @keydown="onCellKeydown($event, idx, colIdx, 'plan')"
                    :disabled="isPlanCellLocked(c.key)"
                    :class="{ locked: isPlanCellLocked(c.key) }"
                  />
                  <div
                    v-for="(lot, lotIdx) in row.daily?.[c.key]?.extraLots"
                    :key="lot.id || lotIdx"
                    class="lot-item"
                  >
                    <input
                      type="text"
                      inputmode="decimal"
                      :value="lot.plan_qty === 0 || lot.plan_qty === '' || lot.plan_qty == null ? '' : lot.plan_qty"
                      @input="onExtraPlanInput(row, c.key, lot, $event.target.value)"
                      :disabled="isPlanCellLocked(c.key)"
                      :class="{ locked: isPlanCellLocked(c.key) }"
                    />
                  </div>
                  <button class="mini-btn lot-add" type="button" @click="addExtraLot(row, c.key)" :disabled="isPlanCellLocked(c.key)">+</button>
                </div>
              </td>
              <td class="num sequence" :class="c.dayClass">
                <div class="lot-stack">
                  <input
                    type="text"
                    inputmode="numeric"
                    :value="row.daily?.[c.key]?.sequence_no === 0 || row.daily?.[c.key]?.sequence_no === '' || row.daily?.[c.key]?.sequence_no == null ? '' : row.daily?.[c.key]?.sequence_no"
                    @input="onSequenceInput(row, c.key, $event.target.value)"
                    :data-row="idx"
                    :data-col="colIdx"
                    data-field="sequence"
                    @keydown="onCellKeydown($event, idx, colIdx, 'sequence')"
                    :disabled="isPlanCellLocked(c.key)"
                    :class="{ locked: isPlanCellLocked(c.key) }"
                  />
                  <div
                    v-for="(lot, lotIdx) in row.daily?.[c.key]?.extraLots"
                    :key="lot.id || lotIdx"
                    class="lot-item"
                  >
                    <input
                      type="text"
                      inputmode="numeric"
                      :value="lot.sequence_no === 0 || lot.sequence_no === '' || lot.sequence_no == null ? '' : lot.sequence_no"
                      @input="onExtraSequenceInput(row, c.key, lot, $event.target.value)"
                      :disabled="isPlanCellLocked(c.key)"
                      :class="{ locked: isPlanCellLocked(c.key) }"
                    />
                    <button class="mini-btn lot-remove" type="button" @click="removeExtraLot(row, c.key, lot.id)" :disabled="isPlanCellLocked(c.key)">x</button>
                  </div>
                </div>
              </td>
              <td class="num stock-plan day-end" :class="c.dayClass">
                <span class="readonly-value">{{ displayValue(getPlanStockDisplay(row, colIdx)) }}</span>
              </td>
            </template>
          </tr>
          <tr v-if="!filteredRows.length">
            <td :colspan="3 + dateColumns.length * 6" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="gantt-section" v-if="showProcessGantt">
      <div class="process-header">
        <div class="process-info">
          <div class="process-title">
            工程ガント（勤務時間のみ表示）
            <span class="process-title-inline">ライン {{ selectedLine || '' }}</span>
            <span class="process-title-inline">期間 {{ startDate }} ～ {{ endDate }}</span>
          </div>
        </div>
        <div class="process-actions">
          <button class="btn" @click="saveGanttSchedule" :disabled="!selectedLine">工程ガント保存</button>
        </div>
      </div>
      <ProcessGanttView
        :key="ganttReloadKey"
        ref="ganttRef"
        :embedded="true"
        :preset-line="selectedLine"
        :preset-base-date="startDate"
        :preset-start-date="startDate"
        :preset-end-date="endDate"
      />
    </div>


    <div class="load-section" v-if="showProcessLoad">
      <div class="process-header">
        <div class="process-title">工程別 日別負荷 分（H）</div>
        <div class="process-meta">ライン {{ selectedLine || '' }} ／ 期間 {{ startDate }} ? {{ endDate }}</div>
      </div>
      <div class="load-body">
        <div v-if="processLoadLoading" class="load-message">読込中...</div>
        <div v-else-if="processLoadMessage" class="load-message">{{ processLoadMessage }}</div>
        <div v-else class="load-table-wrap">
          <table class="load-table" :style="{ minWidth: loadTableMinWidth + 'px' }">
            <thead>
              <tr>
                <th class="sticky-col load-process-col">工程</th>
                <th v-for="c in dateColumns" :key="c.key" class="mini" :class="c.dayClass">
                  {{ c.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="proc in processLoadRows" :key="proc.process_id">
                <td class="sticky-col load-process-col">{{ proc.process_name || proc.process_id }}</td>
                <td v-for="c in dateColumns" :key="c.key" class="num" :class="c.dayClass">
                  <span class="readonly-value">{{ displayValue(formatLoad(proc.daily?.[c.key])) }}</span>
                </td>
              </tr>
              <tr v-if="!processLoadRows.length">
                <td :colspan="dateColumns.length + 1" class="no-data">表示する負荷データがありません</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="footer-actions">
      <button class="btn-secondary">F1: 終了</button>
      <button class="btn-secondary">F3: クリア</button>
      <button class="btn-secondary">F5: 備考</button>
      <button class="btn-secondary" @click="openExportDialog" :disabled="processing || !filteredRows.length">F10: 印刷</button>
      <button class="btn-secondary">F12: 更新</button>
    </div>
    <div v-if="showChangeReasonDialog" class="modal-overlay" @click.self="closeChangeReasonDialog">
      <div class="modal-content">
        <h2>変更理由入力</h2>
        <textarea
          v-model="changeReasonDraft"
          rows="4"
          placeholder="変更理由を入力してください"
        ></textarea>
        <div class="modal-actions">
          <button class="btn" @click="closeChangeReasonDialog">キャンセル</button>
          <button class="btn primary" @click="confirmChangeReason">確定</button>
        </div>
      </div>
    </div>

    <div v-if="showExportDialog" class="modal-overlay" @click.self="closeExportDialog">
      <div class="modal-content export-modal">
        <h2>出力形式を選択してください</h2>
        <p class="export-note">
          対象: 現在の絞り込み結果（ライン: {{ selectedLineLabel || '未選択' }} ／ 期間: {{ startDate }} ～ {{ endDate }} ／ 日替わり時刻 08:00）
        </p>
        <div class="export-actions">
          <button class="btn" @click="exportToExcel" :disabled="!filteredRows.length">Excel出力</button>
          <button class="btn primary" @click="exportToPdf" :disabled="!filteredRows.length">PDF出力</button>
          <button class="btn" @click="closeExportDialog">キャンセル</button>
        </div>
      </div>
    </div>

    <div v-if="processing" class="processing-overlay">
      <div class="processing-box">
        <p class="processing-title">データ更新中</p>
        <p class="processing-sub">少々お待ちください</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import api from '@/api/client'
import ProcessGanttView from './ProcessGanttView.vue'
const selectedLine = ref('')
const toDateInput = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
const defaultStart = new Date()
defaultStart.setDate(defaultStart.getDate() - 1)
const startDate = ref(toDateInput(defaultStart))
const horizonDays = ref(30)
const keyword = ref('')
const TANK_LINE_CODE = 'L2200'
const TANK_PRODUCT_ORDER = [
  'YD60003386',
  'YD60011305',
  'YD60000441',
  'YD60008491',
  'YD60009848',
  'YD60014764',
  'YD60009783',
  'YD60009874',
  'YD60010942'
]
const gridWrapperRef = ref(null)
const lockDays = ref(0)
const isEditUnlocked = ref(false)
const changeReason = ref('')
const changeReasonDraft = ref('')
const showChangeReasonDialog = ref(false)

const lines = ref([])
const products = ref([])
const rows = ref([])
const showProcessGantt = ref(false)
const showProcessLoad = ref(false)
const ganttReloadKey = ref(0)
const ganttRef = ref(null)
const finalProcessStartTime = ref('08:00')
const adjustToBreakEnd = ref(true)
let lotTempId = 1
const processLoadLoading = ref(false)
const processLoadRows = ref([])
const processLoadMessage = ref('')
const dailySettings = ref({})
const calendarDayMap = ref({})
const workPatternMap = ref({})
const workStartFallback = { hour: 8, minute: 0 }
const workMinutesFallback = 480
const processing = ref(false)
const selectedLineObj = computed(() =>
  lines.value.find((l) => `${l.id}` === `${selectedLine.value}`)
)
const showExportDialog = ref(false)
const PRINT_CHUNK_DAYS = 14

const formatDateKey = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const buildLocalDate = (dateText) => {
  if (!dateText) return new Date()
  const [y, m, d] = dateText.split('-').map((v) => Number(v))
  if (!y || !m || !d) return new Date()
  return new Date(y, m - 1, d)
}

const lockUntilDate = computed(() => {
  const base = new Date()
  base.setHours(0, 0, 0, 0)
  base.setDate(base.getDate() + Number(lockDays.value || 0))
  return base
})

const isPlanCellLocked = (dateKey) => {
  if (!dateKey) return false
  const target = buildLocalDate(dateKey)
  return target <= lockUntilDate.value && !isEditUnlocked.value
}

const endDate = computed(() => {
  const d = buildLocalDate(startDate.value)
  d.setDate(d.getDate() + horizonDays.value - 1)
  return formatDateKey(d)
})

const dateColumns = computed(() => {
  const cols = []
  const base = buildLocalDate(startDate.value)
  const weekday = ['日', '月', '火', '水', '木', '金', '土']
  for (let i = 0; i < horizonDays.value; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i)
    const day = d.getDay()
    const label = `${d.getMonth() + 1}/${d.getDate()}(${weekday[day]})`
    const key = formatDateKey(d)
    const dayClass = day === 0 ? 'sun' : day === 6 ? 'sat' : ''
    cols.push({ key, label, dayClass })
  }
  return cols
})

// テーブルの最小幅を計算して、縮みすぎを防ぐ
const tableMinWidth = computed(() => {
  const fixedColsWidth = 60 + 187 + 100 // No + 品番 + 品名
  const perDayWidth = 80 * 6 // 6列×80px (需要、実績、在庫、計画、順序、計画在庫)
  return fixedColsWidth + dateColumns.value.length * perDayWidth
})

const loadTableMinWidth = computed(() => {
  const fixedColsWidth = 180
  const perDayWidth = 80
  return fixedColsWidth + dateColumns.value.length * perDayWidth
})

const initDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = {
      demand: 0,
      actual: 0,
      stock: 0,
      plan: '',
      plan_stock: 0,
      plan_base: 0,
      sequence_no: '',
      extraLots: [],
      has_row: false,
    }
  })
  return daily
}

const ensureDailyCell = (row, dateKey) => {
  if (!row.daily) row.daily = initDaily()
  if (!row.daily[dateKey]) {
    row.daily[dateKey] = {
      demand: 0,
      actual: 0,
      stock: 0,
      plan: '',
      plan_stock: 0,
      plan_base: 0,
      sequence_no: '',
      extraLots: [],
      has_row: false,
    }
  }
  if (!row.daily[dateKey].extraLots) {
    row.daily[dateKey].extraLots = []
  }
  return row.daily[dateKey]
}

const rowIndex = (rowId) => rows.value.findIndex((r) => r.id === rowId)

const moveRow = (rowId, direction) => {
  const idx = rowIndex(rowId)
  if (idx < 0) return
  const target = idx + direction
  if (target < 0 || target >= rows.value.length) return
  const reordered = [...rows.value]
  const [item] = reordered.splice(idx, 1)
  reordered.splice(target, 0, item)
  rows.value = reordered
}

const resetRows = () => {
  rows.value = []
}

const savePlan = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  if (isEditUnlocked.value && !changeReason.value) {
    alert('変更理由を入力してください。')
    return
  }

  // 日別設定を先に保存
  try {
    await saveDailySettings()
  } catch (e) {
    console.error('日別設定の保存に失敗しました', e)
    // 日別設定の保存失敗は警告のみで続行
  }

  const items = []
  console.log('保存対象の行数:', rows.value.length)
  rows.value.forEach((r) => {
    console.log('保存チェック:', { product_id: r.product_id, process_id: r.process_id, product_code: r.product_code })
    if (!r.product_id || !r.process_id) {
      console.warn('スキップ: product_idまたはprocess_idがありません', r)
      return
    }
    dateColumns.value.forEach((c) => {
      const daily = ensureDailyCell(r, c.key)
      const mainPlanQty = daily.plan === '' || daily.plan === null || daily.plan === undefined ? null : Number(daily.plan)
      const mainSeqNo = daily.sequence_no === '' || daily.sequence_no === null || daily.sequence_no === undefined ? null : Number(daily.sequence_no)
      const lots = []
      if (!(mainPlanQty === null && mainSeqNo === null)) {
        lots.push({ plan_qty: mainPlanQty, sequence_no: mainSeqNo })
      }
      const extraLots = Array.isArray(daily.extraLots) ? daily.extraLots : []
      extraLots.forEach((lot) => {
        const lotPlanQty = lot.plan_qty === '' || lot.plan_qty === null || lot.plan_qty === undefined ? null : Number(lot.plan_qty)
        const lotSeqNo = lot.sequence_no === '' || lot.sequence_no === null || lot.sequence_no === undefined ? null : Number(lot.sequence_no)
        if (lotPlanQty === null && lotSeqNo === null) return
        lots.push({ plan_qty: lotPlanQty, sequence_no: lotSeqNo })
      })
      lots.forEach((lot) => {
        items.push({
          product_id: r.product_id,
          process_id: r.process_id,
          plan_date: c.key,
          plan_qty: lot.plan_qty === null ? 0 : lot.plan_qty,
          sequence_no: lot.sequence_no,
        })
      })
    })
  })
  console.log('保存アイテム数:', items.length)
  if (items.length > 0) {
    console.log('サンプルアイテム:', items[0])
  }
  if (!items.length) {
    alert('保存するデータがありません。product_idとprocess_idを確認してください。')
    return
  }
  processing.value = true
  try {
    const payload = {
      line_id: selectedLine.value,
      items,
    }
    if (isEditUnlocked.value && changeReason.value) {
      payload.change_reason = changeReason.value
    }
    const res = await api.linePlans.save(payload)
    console.info('保存結果', res.data)
    try {
      await api.lineBacklogs.expandProcesses({
        line_id: selectedLine.value,
        start_date: startDate.value,
        end_date: endDate.value,
        read_only: false,
        include_coproduct_children: true,
      })
      await api.lineBacklogs.recalculateInventory({
        line_id: selectedLine.value,
        start_date: startDate.value,
        end_date: endDate.value,
        include_progress: false,
        line_final_only: true,
      })
      await api.lineGanttPlans.generate({
        line_id: selectedLine.value,
        start_date: startDate.value,
        end_date: endDate.value,
        clear_existing: true,
        final_process_start_time: finalProcessStartTime.value,
        adjust_to_break_end: adjustToBreakEnd.value,
      })
      // 工程ガントを再読み込み
      ganttReloadKey.value += 1
      if (showProcessLoad.value) {
        await loadProcessLoad()
      }
    } catch (expandError) {
      console.error('工程展開/ガント再計算エラー', expandError)
      let msg = '工程展開/ガント再計算に失敗しました。'
      if (expandError.response && expandError.response.data) {
        // DRFのValidationErrorなどは配列やオブジェクトで返ることがあるため文字列化
        msg += '\n' + (Array.isArray(expandError.response.data) ? expandError.response.data.join('\n') : JSON.stringify(expandError.response.data, null, 2))
      }
      alert(`保存は完了しましたが、エラーが発生しました。\n${msg}`)
      return
    }
    alert(`保存しました。\n作成: ${res.data.created}件, 更新: ${res.data.updated}件`)
    isEditUnlocked.value = false
    changeReason.value = ''
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました。')
  } finally {
    processing.value = false
  }
}

const getProductName = (id) => {
  const p = products.value.find((x) => x.id === id)
  return p ? p.product_name : ''
}
const getProductCode = (id) => {
  const p = products.value.find((x) => x.id === id)
  return p ? p.product_code : ''
}
const getRowProductCode = (row) => row.product_code || getProductCode(row.product_id) || ''

const sortRowsForLine = (inputRows) => {
  const line = selectedLineObj.value
  if (!line || line.line_code !== TANK_LINE_CODE) return inputRows
  const orderMap = new Map(TANK_PRODUCT_ORDER.map((code, idx) => [code, idx]))
  const fallback = TANK_PRODUCT_ORDER.length + 1
  return [...inputRows].sort((a, b) => {
    const codeA = getRowProductCode(a)
    const codeB = getRowProductCode(b)
    const priA = orderMap.has(codeA) ? orderMap.get(codeA) : fallback
    const priB = orderMap.has(codeB) ? orderMap.get(codeB) : fallback
    if (priA !== priB) return priA - priB
    return codeA.localeCompare(codeB)
  })
}

const filteredRows = computed(() => {
  if (!keyword.value) return rows.value
  const k = keyword.value.toLowerCase()
  return rows.value.filter((r) => {
    const txt = `${r.product_code || ''}${r.product_name || ''}${getProductCode(r.product_id)}${getProductName(r.product_id)}`.toLowerCase()
    return txt.includes(k)
  })
})

const displayValue = (val) => {
  if (val === null || val === undefined || val === '') return ''
  const num = Number(val)
  if (!Number.isNaN(num) && num === 0) return ''
  return val
}

const toNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const getPlanQtyTotal = (daily) => {
  if (!daily) return 0
  const main = toNumber(daily.plan)
  const extras = Array.isArray(daily.extraLots)
    ? daily.extraLots.reduce((sum, lot) => sum + toNumber(lot.plan_qty), 0)
    : 0
  return main + extras
}

const getPlanDelta = (daily) => getPlanQtyTotal(daily) - toNumber(daily?.plan_base)

const getPlanStockDisplay = (row, colIdx) => {
  if (!row || !row.daily) return ''
  const cols = dateColumns.value
  let carry = null
  let delta = 0
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    const raw = daily.plan_stock
    const hasRow = daily.has_row === true
    let value = raw
    if (hasRow) {
      carry = raw
    } else if (carry !== null && carry !== undefined) {
      value = carry
    }
    delta += getPlanDelta(daily)
    if (i === colIdx) {
      const baseValue = value === null || value === undefined ? 0 : Number(value)
      return baseValue + delta
    }
  }
  return ''
}

const getStockDisplay = (row, colIdx) => {
  if (!row || !row.daily) return ''
  const cols = dateColumns.value
  let carry = null
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    const raw = daily.stock
    const hasRow = daily.has_row === true
    let value = raw
    if (hasRow) {
      carry = raw
    } else if (carry !== null && carry !== undefined) {
      value = carry
    }
    if (i === colIdx) return value
  }
  return ''
}

const focusCellInput = (rowIdx, colIdx, field) => {
  const root = gridWrapperRef.value
  if (!root) return
  const selector = `input[data-row="${rowIdx}"][data-col="${colIdx}"][data-field="${field}"]`
  const target = root.querySelector(selector)
  if (target) {
    target.focus()
    if (typeof target.select === 'function') {
      target.select()
    }
  }
}

const onCellKeydown = (event, rowIdx, colIdx, field) => {
  const key = event.key
  const supportedKeys = ['Enter', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']
  if (!supportedKeys.includes(key)) return

  event.preventDefault()

  const maxRow = filteredRows.value.length - 1
  const maxCol = dateColumns.value.length - 1
  if (maxRow < 0 || maxCol < 0) return

  const fieldOrder = ['plan', 'sequence']
  let nextRow = rowIdx
  let nextCol = colIdx
  let nextField = field

  if (key === 'Enter') {
    nextRow += event.shiftKey ? -1 : 1
  } else if (key === 'ArrowUp') {
    nextRow -= 1
  } else if (key === 'ArrowDown') {
    nextRow += 1
  } else if (key === 'ArrowLeft') {
    const fieldIdx = fieldOrder.indexOf(field)
    if (fieldIdx > 0) {
      nextField = fieldOrder[fieldIdx - 1]
    } else {
      nextCol -= 1
      nextField = fieldOrder[fieldOrder.length - 1]
    }
  } else if (key === 'ArrowRight') {
    const fieldIdx = fieldOrder.indexOf(field)
    if (fieldIdx < fieldOrder.length - 1) {
      nextField = fieldOrder[fieldIdx + 1]
    } else {
      nextCol += 1
      nextField = fieldOrder[0]
    }
  }

  if (nextRow < 0 || nextRow > maxRow) return
  if (nextCol < 0 || nextCol > maxCol) return

  focusCellInput(nextRow, nextCol, nextField)
}

const refreshDates = () => {
  // 再初期化は既存データの初期化だけ（簡易対応）
  rows.value.forEach((r) => {
    r.daily = initDaily()
  })
  if (selectedLine.value) {
    loadWorkPatternData(selectedLine.value, startDate.value, endDate.value)
  }
}

const loadData = async () => {
  // 取り込み前は空表示（手動で「取り込み」を押す運用）
  rows.value = []
  if (selectedLine.value) {
    await fetchLineDefaultSetting(selectedLine.value)
    await loadWorkPatternData(selectedLine.value, startDate.value, endDate.value)
    // 日別設定を読み込み、未設定の日にデフォルト値をセット
    await loadDailySettings()
    applyDefaultToDailySettings()
  } else {
    calendarDayMap.value = {}
    workPatternMap.value = {}
    // ライン未選択時はデフォルト値に戻す
    finalProcessStartTime.value = '08:00'
    adjustToBreakEnd.value = true
  }
}

const onPlanInput = (row, dateKey, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.plan = value === '' ? '' : value
}

const onSequenceInput = (row, dateKey, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.sequence_no = value === '' ? '' : value
}

const addExtraLot = (row, dateKey) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.extraLots.push({
    id: `lot-${lotTempId++}`,
    plan_qty: '',
    sequence_no: '',
  })
}

const removeExtraLot = (row, dateKey, lotId) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.extraLots = daily.extraLots.filter((lot) => lot.id !== lotId)
}

const onExtraPlanInput = (row, dateKey, lot, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  const target = daily.extraLots.find((item) => item.id === lot.id)
  if (target) {
    target.plan_qty = value === '' ? '' : value
  }
}

const onExtraSequenceInput = (row, dateKey, lot, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  const target = daily.extraLots.find((item) => item.id === lot.id)
  if (target) {
    target.sequence_no = value === '' ? '' : value
  }
}

const toggleProcessGantt = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  showProcessGantt.value = !showProcessGantt.value
  if (showProcessGantt.value) {
    ganttReloadKey.value += 1
  }
}

const saveGanttSchedule = async () => {
  if (!showProcessGantt.value) {
    alert('工程ガントを表示してください。')
    return
  }
  const gantt = ganttRef.value
  if (!gantt || typeof gantt.saveSchedule !== 'function') {
    alert('工程ガントが未読込です。')
    return
  }
  await gantt.saveSchedule()
}


const loadProcessLoad = async () => {
  if (!selectedLine.value) return
  processLoadLoading.value = true
  processLoadMessage.value = ''
  try {
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: selectedLine.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!rawPlans.length) {
      processLoadRows.value = []
      processLoadMessage.value = '工程ガントが未作成です。先に工程ガントを生成してください。'
      return
    }
    processLoadRows.value = buildProcessLoad(rawPlans)
  } catch (e) {
    console.error('工程負荷取得エラー', e)
    processLoadRows.value = []
    processLoadMessage.value = '工程負荷の取得に失敗しました。'
  } finally {
    processLoadLoading.value = false
  }
}

const toggleProcessLoad = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  showProcessLoad.value = !showProcessLoad.value
  if (showProcessLoad.value) {
    await loadProcessLoad()
  }
}

const fetchLines = async () => {
  const res = await api.lines.getProductionLines()
  lines.value = res.data.results || res.data || []
}
const fetchProducts = async () => {
  products.value = (await api.products.getAllProducts())
    .filter((p) => !p.is_phantom)
    .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
}

onMounted(async () => {
  try {
    await Promise.all([fetchLines(), fetchProducts(), fetchLockSetting()])
    loadData()
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})

const fetchLockSetting = async () => {
  try {
    const res = await api.productionPlanLockSetting.getSetting()
    lockDays.value = Number(res.data?.lock_days ?? 0)
  } catch (e) {
    console.error('生産計画ロック設定の取得エラー', e)
    lockDays.value = 0
  }
}

const fetchLineDefaultSetting = async (lineId) => {
  if (!lineId) {
    finalProcessStartTime.value = '08:00'
    adjustToBreakEnd.value = true
    return
  }
  try {
    const res = await api.lineDefaultScheduleSettings.getLineDefaultScheduleSettings({ line: lineId })
    const data = res.data?.results || res.data || []
    const setting = Array.isArray(data) ? data[0] : data
    finalProcessStartTime.value = setting?.final_process_start_time || '08:00'
    if (setting && Object.prototype.hasOwnProperty.call(setting, 'adjust_to_break_end')) {
      adjustToBreakEnd.value = !!setting.adjust_to_break_end
    } else {
      adjustToBreakEnd.value = true
    }
  } catch (e) {
    console.error('ラインデフォルト開始時刻の取得エラー', e)
    finalProcessStartTime.value = '08:00'
    adjustToBreakEnd.value = true
  }
}

const openChangeReasonDialog = () => {
  changeReasonDraft.value = changeReason.value
  showChangeReasonDialog.value = true
}

const closeChangeReasonDialog = () => {
  showChangeReasonDialog.value = false
}

const confirmChangeReason = () => {
  const reason = (changeReasonDraft.value || '').trim()
  if (!reason) {
    alert('変更理由を入力してください。')
    return
  }
  changeReason.value = reason
  isEditUnlocked.value = true
  showChangeReasonDialog.value = false
}

const parseTimeParts = (value) => {
  if (!value) return null
  const parts = String(value).split(':')
  if (parts.length < 2) return null
  const hour = Number(parts[0])
  const minute = Number(parts[1])
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null
  return { hour, minute }
}

const getWorkStartForDate = (dateKey) => {
  const day = calendarDayMap.value[dateKey]
  if (day && day.is_working_day === false) return null
  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.start_time)
    if (parsed) return parsed
  }
  return workStartFallback
}

const getWorkEndForDate = (dateKey, startParts) => {
  const day = calendarDayMap.value[dateKey]
  if (day && day.is_working_day === false) return null
  const start = startParts || workStartFallback
  let endParts = null
  let dayOffset = 0

  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.end_time)
    if (parsed) {
      endParts = parsed
      if (parsed.hour < start.hour || (parsed.hour === start.hour && parsed.minute <= start.minute)) {
        dayOffset = 1
      }
    }
  }

  if (!endParts) {
    const workMinutes = day && day.work_minutes != null ? Number(day.work_minutes) : workMinutesFallback
    if (!Number.isFinite(workMinutes)) return null
    const startMinutes = start.hour * 60 + start.minute
    const endMinutesTotal = Math.max(0, startMinutes + workMinutes)
    dayOffset = Math.floor(endMinutesTotal / (24 * 60))
    const endMinutesInDay = endMinutesTotal % (24 * 60)
    endParts = {
      hour: Math.floor(endMinutesInDay / 60),
      minute: endMinutesInDay % 60,
    }
  }

  return { ...endParts, dayOffset }
}

const formatWorkTimeLabel = (dateKey) => {
  if (!dateKey) return ''
  const workStart = getWorkStartForDate(dateKey)
  if (!workStart) return ''
  const workEnd = getWorkEndForDate(dateKey, workStart)
  if (!workEnd) return ''
  const startLabel = `${String(workStart.hour).padStart(2, '0')}:${String(workStart.minute).padStart(2, '0')}`
  const endLabel = `${String(workEnd.hour).padStart(2, '0')}:${String(workEnd.minute).padStart(2, '0')}`
  const endPrefix = workEnd.dayOffset > 0 ? '翌' : ''
  return `(${startLabel}〜${endPrefix}${endLabel})`
}

const getWorkTimeLabel = (dateKey) => formatWorkTimeLabel(dateKey)

const loadWorkPatternData = async (lineId, start, end) => {
  calendarDayMap.value = {}
  workPatternMap.value = {}
  if (!lineId) return

  let calendarId = null
  const line = lines.value.find((item) => String(item.id) === String(lineId))
  if (line && line.calendar) {
    calendarId = line.calendar
  } else {
    try {
      const lineRes = await api.lines.getLine(lineId)
      calendarId = lineRes.data?.calendar ?? null
    } catch (e) {
      console.error('ライン勤務カレンダ取得エラー', e)
      calendarId = null
    }
  }
  if (!calendarId) return

  try {
    const daysRes = await api.calendars.getCalendarDays(calendarId)
    const days = daysRes.data?.results || daysRes.data || []
    const filtered = days.filter((day) => {
      if (!day.target_date) return false
      if (start && day.target_date < start) return false
      if (end && day.target_date > end) return false
      return true
    })
    const dayMap = {}
    const patternIds = new Set()
    filtered.forEach((day) => {
      dayMap[day.target_date] = day
      if (day.work_pattern) patternIds.add(String(day.work_pattern))
    })
    calendarDayMap.value = dayMap
    if (patternIds.size) {
      const patternsRes = await api.workPatterns.getWorkPatterns()
      const patterns = patternsRes.data?.results || patternsRes.data || []
      const patternMap = {}
      patterns.forEach((pattern) => {
        patternMap[String(pattern.id)] = pattern
      })
      workPatternMap.value = patternMap
    }
  } catch (e) {
    console.error('勤務パターン取得エラー', e)
  }
}


const buildProcessLoad = (plans) => {
  const processMap = new Map()
  plans.forEach((plan) => {
    const planDate = plan.plan_date || plan.planDate
    if (!planDate) return
    const dateKey = String(planDate).slice(0, 10)
    const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
    processes.forEach((pp) => {
      const pid = pp.process_id ?? 'unknown'
      let entry = processMap.get(pid)
      if (!entry) {
        entry = {
          process_id: pid,
          process_name: pp.process_name || '',
          process_number: pp.process_number ?? null,
          daily: {},
        }
        processMap.set(pid, entry)
      }
      const minutes = Number(pp.effective_minutes ?? pp.total_minutes_required ?? 0)
      if (!Number.isFinite(minutes) || minutes === 0) return
      entry.daily[dateKey] = (entry.daily[dateKey] || 0) + minutes
    })
  })
  const list = Array.from(processMap.values())
  list.sort((a, b) => {
    const aNum = a.process_number ?? 9999
    const bNum = b.process_number ?? 9999
    if (aNum != bNum) return aNum - bNum
    return (a.process_name || '').localeCompare(b.process_name || '')
  })
  return list
}

const formatLoad = (val) => {
  if (val == null) return ''
  const num = Number(val)
  if (Number.isNaN(num) || num === 0) return ''
  const minutes = Math.round(num * 10) / 10
  const hours = Math.round((minutes / 60) * 10) / 10
  return `${minutes} (${hours})`
}

const selectedLineLabel = computed(() => {
  const line = lines.value.find((item) => String(item.id) === String(selectedLine.value))
  if (!line) return ''
  const code = line.line_code || ''
  const name = line.line_name || ''
  return `${code} ${name}`.trim()
})

const openExportDialog = () => {
  if (!filteredRows.value.length) {
    alert('出力対象のデータがありません。')
    return
  }
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  showExportDialog.value = true
}

const closeExportDialog = () => {
  showExportDialog.value = false
}

const escapeCsv = (value) => {
  const text = `${value ?? ''}`
  const escaped = text.replace(/"/g, '""')
  return `"${escaped}"`
}

const escapeHtml = (value) => {
  const text = `${value ?? ''}`
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const formatLotValues = (daily, field) => {
  if (!daily) return ''
  const values = []
  const mainVal = daily[field]
  if (mainVal !== '' && mainVal !== null && mainVal !== undefined) {
    const disp = displayValue(mainVal)
    if (disp !== '') values.push(disp)
  }
  if (Array.isArray(daily.extraLots)) {
    daily.extraLots.forEach((lot) => {
      const val = field === 'plan' ? lot.plan_qty : lot.sequence_no
      if (val !== '' && val !== null && val !== undefined) {
        const disp = displayValue(val)
        if (disp !== '') values.push(disp)
      }
    })
  }
  return values.join('/')
}

const buildExportRow = (row) => {
  const data = []
  dateColumns.value.forEach((c, colIdx) => {
    const daily = row.daily?.[c.key] || {}
    data.push(displayValue(daily.demand))
    data.push(displayValue(daily.actual))
    data.push(displayValue(getStockDisplay(row, colIdx)))
    data.push(formatLotValues(daily, 'plan'))
    data.push(formatLotValues(daily, 'sequence_no'))
    data.push(displayValue(getPlanStockDisplay(row, colIdx)))
  })
  return data
}

const exportToExcel = () => {
  if (!filteredRows.value.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const bom = '\ufeff'
  const linesOut = []
  linesOut.push([escapeCsv('ライン'), escapeCsv(selectedLineLabel.value || '')].join(','))
  linesOut.push([escapeCsv('期間'), escapeCsv(`${startDate.value} ～ ${endDate.value}`)].join(','))
  linesOut.push([escapeCsv('日替わり時刻'), escapeCsv('08:00')].join(','))
  linesOut.push([escapeCsv('デフォルト開始時刻'), escapeCsv(finalProcessStartTime.value || '00:00')].join(','))
  linesOut.push('')

  const header1 = ['No', '品番']
  dateColumns.value.forEach((c) => {
    for (let i = 0; i < 6; i += 1) {
      header1.push(c.label)
    }
  })
  const header2 = ['No', '品番']
  dateColumns.value.forEach(() => {
    header2.push('需要', '実績', '在庫', '計画', '順序', '計画在庫')
  })
  linesOut.push(header1.map(escapeCsv).join(','))
  linesOut.push(header2.map(escapeCsv).join(','))

  filteredRows.value.forEach((row, idx) => {
    const rowData = buildExportRow(row)
    rowData.unshift(row.product_code || getProductCode(row.product_id) || '')
    rowData.unshift(idx + 1)
    linesOut.push(rowData.map(escapeCsv).join(','))
  })

  const csvContent = bom + linesOut.join('\r\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const lineLabel = selectedLineLabel.value ? `_${selectedLineLabel.value.replace(/\\s+/g, '_')}` : ''
  link.href = url
  link.download = `production_plan${lineLabel}_${startDate.value}_${endDate.value}.csv`
  link.click()
  URL.revokeObjectURL(url)
  closeExportDialog()
}

const buildPrintTableHtml = () => {
  const headerInfo = `
    <div class="meta">
      <div><strong>ライン:</strong> ${escapeHtml(selectedLineLabel.value || '')}</div>
      <div><strong>期間:</strong> ${escapeHtml(startDate.value)} ～ ${escapeHtml(endDate.value)}</div>
      <div><strong>日替わり時刻:</strong> 08:00</div>
    </div>
  `

  const metrics = [
    { key: 'demand', label: '計需', getValue: (row, daily, colIdx) => displayValue(daily.demand) },
    { key: 'actual', label: '実需', getValue: (row, daily, colIdx) => displayValue(daily.actual) },
    { key: 'plan', label: '計画', getValue: (row, daily, colIdx) => formatLotValues(daily, 'plan') },
    { key: 'sequence', label: '順序', getValue: (row, daily, colIdx) => formatLotValues(daily, 'sequence_no') },
    { key: 'stock', label: '在庫', getValue: (row, daily, colIdx) => displayValue(getStockDisplay(row, colIdx)) },
    { key: 'plan_stock', label: '計画在庫', getValue: (row, daily, colIdx) => displayValue(getPlanStockDisplay(row, colIdx)) },
  ]

  const chunkDateColumns = () => {
    const chunks = []
    const SIZE = 30
    for (let i = 0; i < dateColumns.value.length; i += SIZE) {
      chunks.push({ cols: dateColumns.value.slice(i, i + SIZE), offset: i })
    }
    return chunks
  }

  const buildProductTable = (row, idx, chunkCols, offset) => {
    const thead = (() => {
      const headers = ['<tr class="head1"><th class="metric-col">項目</th>']
      chunkCols.forEach((c) => {
        headers.push(`<th class="date">${escapeHtml(c.label)}</th>`)
      })
      headers.push('</tr>')
      return headers.join('')
    })()

    const tbody = (() => {
      const rowsHtml = metrics.map((m) => {
        const cells = [`<td class="metric-name">${escapeHtml(m.label)}</td>`]
        chunkCols.forEach((c, localIdx) => {
          const globalIdx = offset + localIdx
          const daily = row.daily?.[c.key] || {}
          cells.push(`<td class="num">${escapeHtml(m.getValue(row, daily, globalIdx))}</td>`)
        })
        return `<tr>${cells.join('')}</tr>`
      })
      if (!rowsHtml.length) {
        rowsHtml.push(`<tr><td colspan="${1 + chunkCols.length}" class="no-data">データがありません</td></tr>`)
      }
      return rowsHtml.join('')
    })()

    return `
      <div class="product-block">
        <div class="product-header">
          <div><strong>No:</strong> ${idx + 1}</div>
          <div><strong>品番:</strong> ${escapeHtml(row.product_code || getProductCode(row.product_id) || '')}</div>
          <div><strong>品名:</strong> ${escapeHtml(row.product_name || getProductName(row.product_id) || '')}</div>
        </div>
        <table class="vertical-table">
          <thead>${thead}</thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>
    `
  }

  const tablesHtml = filteredRows.value
    .map((row, idx) =>
      chunkDateColumns()
        .map((chunk, cidx) => {
          const range = `${escapeHtml(chunk.cols[0]?.label || '')} ～ ${escapeHtml(chunk.cols[chunk.cols.length - 1]?.label || '')}`
          return `
            <div class="chunk-header">No.${idx + 1} 品番:${escapeHtml(row.product_code || getProductCode(row.product_id) || '')} ／ 期間: ${range}</div>
            ${buildProductTable(row, idx, chunk.cols, chunk.offset)}
          `
        })
        .join('')
    )
    .join('')

  const style = `
    <style>
      @page { size: A3 landscape; margin: 10mm; }
      body { font-family: "Noto Sans JP", "Segoe UI", sans-serif; color: #111; }
      h1 { margin: 0 0 8px; font-size: 18px; }
      .meta { display: flex; gap: 18px; margin-bottom: 8px; font-size: 12px; }
      .product-block { margin-bottom: 14px; page-break-inside: avoid; }
      .product-header { display: flex; gap: 14px; font-size: 12px; margin: 6px 0; }
      .chunk-header { margin: 6px 0 2px; font-size: 11px; color: #374151; }
      table.vertical-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; }
      th, td { border: 1px solid #cbd5e1; padding: 6px 8px; }
      th.date { background: #e7edf7; }
      th.metric-col { width: 90px; background: #cfd8ec; }
      td.metric-name { background: #f4f6fb; font-weight: 700; }
      td.num { text-align: right; }
      .no-data { text-align: center; }
    </style>
  `

  const html = `
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        ${style}
        <title>生産計画印刷</title>
      </head>
      <body>
        <h1>生産計画一覧</h1>
        ${headerInfo}
        ${tablesHtml}
      </body>
    </html>
  `
  return html
}

const exportToPdf = () => {
  if (!filteredRows.value.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const html = buildPrintTableHtml()
  const win = window.open('', '_blank')
  if (!win) {
    alert('ポップアップがブロックされました。許可して再実行してください。')
    return
  }
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => {
    win.print()
    win.onafterprint = () => win.close()
  }, 150)
  closeExportDialog()
}

const onGlobalKeydown = (event) => {
  if (event.key === 'F10') {
    event.preventDefault()
    openExportDialog()
  }
}

const doPickup = async () => {
  if (!selectedLine.value) return
  processing.value = true
  try {
    await api.lineBacklogs.pickup({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    await api.lineBacklogs.recalculateInventory({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
      include_progress: false,
      line_final_only: true,
    })
    const [backlogRes, planRes] = await Promise.all([
      api.lineBacklogs.getLineBacklogs({
        line: selectedLine.value,
        plan_date__gte: startDate.value,
        plan_date__lte: endDate.value,
      }),
      api.linePlans.getLinePlans({
        line: selectedLine.value,
        plan_date__gte: startDate.value,
        plan_date__lte: endDate.value,
      }),
    ])
    const backlogData = backlogRes.data?.results || backlogRes.data || []
    const planData = planRes.data?.results || planRes.data || []

    const lineFinalBacklogs = backlogData.filter(d => d.is_line_final_product === true)
    const lineFinalPlans = planData.filter(d => d.is_line_final_product !== false)

    const grouped = new Map()
    const demandMap = new Map()
    const actualMap = new Map()
    const stockSourceMap = new Map()
    const prodKeyByDateKey = new Map()
    const productInfoByProdKey = new Map()
    const planLotsByDate = new Map()

    const normalizeSeq = (seq) => {
      if (seq === null || seq === undefined || seq === '' || seq === 0) return null
      const num = Number(seq)
      return Number.isFinite(num) ? num : null
    }
    const ensureRow = (prodKey) => {
      if (!grouped.has(prodKey)) {
        const info = productInfoByProdKey.get(prodKey) || {}
        grouped.set(prodKey, {
          id: `pl-${prodKey}`,
          product_id: info.product_id || '',
          product_code: info.product_code || '',
          product_name: info.product_name || '',
          process_id: info.process_id || '',
          daily: initDaily(),
        })
      }
      return grouped.get(prodKey)
    }

    lineFinalPlans.forEach((d) => {
      if (!d.product) return
      const prodKey = `${d.product}`
      const dateKey = `${prodKey}__${d.plan_date}`
      const seqNo = normalizeSeq(d.sequence_no) ?? 1
      productInfoByProdKey.set(prodKey, {
        product_id: d.product,
        product_code: d.product_code || '',
        product_name: d.product_name || '',
        process_id: d.process,
      })
      if (!planLotsByDate.has(dateKey)) {
        planLotsByDate.set(dateKey, [])
      }
      planLotsByDate.get(dateKey).push({
        plan_qty: d.plan_qty,
        sequence_no: seqNo,
      })
    })

    lineFinalBacklogs.forEach((d) => {
      if (!d.product) return
      const prodKey = `${d.product}`
      const dateKey = `${prodKey}__${d.plan_date}`
      const seqNo = normalizeSeq(d.sequence_no) ?? 0
      prodKeyByDateKey.set(dateKey, prodKey)
      if (!productInfoByProdKey.has(prodKey)) {
        productInfoByProdKey.set(prodKey, {
          product_id: d.product,
          product_code: d.product_code || '',
          product_name: d.product_name || '',
          process_id: d.process,
        })
      }
      const planQtyVal = Number(d.plan_qty || 0)
      const planIdVal = d.plan_id || ''
      const isDemandRow = seqNo === 0 && planQtyVal <= 0 && planIdVal === ''
      if (isDemandRow) {
        const current = Number(d.order_qty || 0)
        const prev = demandMap.get(dateKey)
        demandMap.set(dateKey, prev == null ? current : Math.max(prev, current))
      }
      const actualVal = Number(d.actual_qty || 0)
      const prevActual = actualMap.get(dateKey)
      actualMap.set(dateKey, prevActual == null ? actualVal : Math.max(prevActual, actualVal))
      const stockEntry = stockSourceMap.get(dateKey)
      const priority = seqNo === 0 ? 0 : 1
      if (
        !stockEntry ||
        priority < stockEntry.priority ||
        (priority === stockEntry.priority && seqNo < stockEntry.seq)
      ) {
        stockSourceMap.set(dateKey, {
          priority,
          seq: seqNo,
          stock: Number(d.stock_qty || 0),
          plan_stock: Number(d.planned_stock_qty || 0),
        })
      }
    })

    planLotsByDate.forEach((lots, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const sorted = [...lots].sort((a, b) => (a.sequence_no || 0) - (b.sequence_no || 0))
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      const main = sorted[0]
      if (main) {
        const planQty = Number(main.plan_qty || 0)
        daily.plan = Number.isFinite(planQty) && planQty > 0 ? main.plan_qty : ''
        daily.sequence_no = main.sequence_no
      }
      daily.extraLots = sorted.slice(1).map((lot) => ({
        id: `lot-${lotTempId++}`,
        plan_qty: lot.plan_qty,
        sequence_no: lot.sequence_no,
      }))
      daily.plan_base = sorted.reduce((sum, lot) => sum + Number(lot.plan_qty || 0), 0)
      daily.has_row = true
    })

    demandMap.forEach((qty, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      daily.demand = Number(qty || 0)
      daily.actual = Number(actualMap.get(dateKey) || 0)
    })

    stockSourceMap.forEach((entry, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      daily.stock = Number(entry.stock || 0)
      daily.plan_stock = Number(entry.plan_stock || 0)
      daily.actual = Number(actualMap.get(dateKey) || 0)
      daily.has_row = true
    })

    rows.value = sortRowsForLine(Array.from(grouped.values()))

    // 日別設定を読み込み、未設定の日にデフォルト値をセット
    await loadDailySettings()
    applyDefaultToDailySettings()
  } catch (e) {
    console.error('バックログ取り込みエラー', e)
    alert('取り込みに失敗しました。')
  } finally {
    processing.value = false
  }
}

const loadDailySettings = async () => {
  if (!selectedLine.value) return
  try {
    const res = await api.lineDailyScheduleSettings.getLineDailyScheduleSettings({
      line: selectedLine.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    })
    const settings = res.data?.results || res.data || []
    const settingsMap = {}
    settings.forEach((s) => {
      settingsMap[s.plan_date] = {
        id: s.id,
        final_process_start_time: s.final_process_start_time,
        adjust_to_break_end: s.adjust_to_break_end,
      }
    })
    dailySettings.value = settingsMap
  } catch (e) {
    console.error('日別設定読み込みエラー', e)
  }
}

// 日別設定が未設定の日にデフォルト開始時刻を表示用にセット
const applyDefaultToDailySettings = () => {
  const defaultTime = finalProcessStartTime.value || '08:00'
  dateColumns.value.forEach((c) => {
    if (!dailySettings.value[c.key] || !dailySettings.value[c.key].final_process_start_time) {
      dailySettings.value[c.key] = {
        ...dailySettings.value[c.key],
        final_process_start_time: defaultTime,
      }
    }
  })
}

const onDailySettingTimeChange = (dateKey, timeValue) => {
  if (!dailySettings.value[dateKey]) {
    dailySettings.value[dateKey] = {}
  }
  const normalized = normalizeTimeInput(timeValue)
  dailySettings.value[dateKey].final_process_start_time = normalized || null
}

const onDailySettingTimeBlur = async (dateKey) => {
  // 時刻入力欄から離れた時に自動保存
  if (!selectedLine.value) return
  const setting = dailySettings.value[dateKey]
  if (!setting || !setting.final_process_start_time) return
  const normalized = normalizeTimeInput(setting.final_process_start_time, true)
  if (!normalized) return
  // デフォルト値と同じ場合は日別設定として保存しない（不要な上書きを防止）
  const defaultTime = finalProcessStartTime.value || '08:00'
  if (normalized === defaultTime) {
    setting.final_process_start_time = null
    return
  }
  setting.final_process_start_time = normalized

  try {
    await api.lineDailyScheduleSettings.bulkSaveLineDailyScheduleSettings([{
      line: selectedLine.value,
      plan_date: dateKey,
      final_process_start_time: normalized,
      adjust_to_break_end: adjustToBreakEnd.value,
    }])
    console.log(`日別設定を保存しました: ${dateKey} - ${setting.final_process_start_time}`)
  } catch (e) {
    console.error('日別設定の保存に失敗しました', e)
  }
}

const saveDailySettings = async () => {
  if (!selectedLine.value) return
  const settings = []
  Object.keys(dailySettings.value).forEach((dateKey) => {
    const setting = dailySettings.value[dateKey]
    if (setting.final_process_start_time) {
      settings.push({
        line: selectedLine.value,
        plan_date: dateKey,
        final_process_start_time: setting.final_process_start_time,
        adjust_to_break_end: adjustToBreakEnd.value,
      })
    }
  })
  if (settings.length === 0) return
  try {
    await api.lineDailyScheduleSettings.bulkSaveLineDailyScheduleSettings(settings)
  } catch (e) {
    console.error('日別設定保存エラー', e)
    throw e
  }
}

const normalizeTimeInput = (value, padOnBlur = false) => {
  const raw = String(value || '').replace(/[^0-9]/g, '')
  if (!raw) return ''
  const digits = raw.slice(0, 4)
  if (digits.length <= 2) {
    const hours = digits
    return padOnBlur ? `${hours.padStart(2, '0')}:00` : hours
  }
  if (digits.length === 3) {
    const hours = digits.slice(0, 1)
    const mins = digits.slice(1, 3)
    return padOnBlur ? `${hours.padStart(2, '0')}:${mins}` : `${hours}:${mins}`
  }
  const hours = digits.slice(0, 2)
  const mins = digits.slice(2, 4)
  return `${hours}:${mins}`
}

const onDefaultTimeInput = (value, padOnBlur = false) => {
  finalProcessStartTime.value = normalizeTimeInput(value, padOnBlur)
}

</script>

<style scoped>
.plan-container {
  padding: 6px 8px 10px;
  background: #eef2f6;
  font-size: 13px;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  color: #1f2a44;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  padding: 6px;
  border-radius: 4px;
}
.toolbar-left {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.toolbar-right {
  display: flex;
  gap: 6px;
  align-items: flex-end;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field.checkbox-field {
  justify-content: flex-end;
  padding-bottom: 4px;
}
.field.checkbox-field label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.field label {
  font-size: 12px;
  color: #444;
}
.field input,
.field select {
  padding: 6px 8px;
  min-width: 140px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.grid-wrapper {
  margin-top: 6px;
  flex: 1;
  min-height: 200px;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.plan-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  --header-row-height: 30px;
}
.plan-grid th,
.plan-grid td {
  border: 1px solid #d7dfe8;
  padding: 3px 6px;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
  color: #000;
}
.lot-stack {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.lot-item {
  display: flex;
  gap: 4px;
  align-items: center;
}
.lot-add,
.lot-remove {
  padding: 2px 6px;
  font-size: 11px;
  line-height: 1;
}
.plan-grid th {
  font-weight: 700;
}
.plan-grid thead th {
  position: sticky;
  top: 0;
  z-index: 4;
}
.plan-grid thead tr.head-level1 th {
  top: 0;
}
.plan-grid thead tr.head-level2 th {
  top: var(--header-row-height);
}
.plan-grid thead th.sticky-col {
  z-index: 8;
}
.plan-grid thead tr.head-level1 th {
  background: #cfd8ec;
}
.plan-grid thead tr.head-level2 th {
  background: #e7edf7;
}
.plan-grid thead th.sat {
  background: #ffe8cc;
}
.plan-grid thead th.sun {
  background: #ffd6d6;
}
thead tr.head-level1 th.sticky-col {
  background: #cfd8ec;
}
thead tr.head-level2 th.sticky-col {
  background: #e7edf7;
}
.sat {
  background: #ffe8cc;
}
.sun {
  background: #ffd6d6;
}
.head-level1 {
  background: #cfd8ec;
  color: #1a2140;
}
.head-level2 {
  background: #e7edf7;
  color: #1a2140;
}
.date-head {
  text-align: center;
  font-weight: 700;
  /* min-widthを削除して自然な幅に */
}
.date-header-content-horizontal {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.date-label {
  font-weight: 700;
  font-size: 11px;
  white-space: nowrap;
}
.work-time-label {
  font-size: 16px;
  color: #dc2626;
  white-space: nowrap;
}
.time-input-inline {
  padding: 1px 2px;
  font-size: 14px;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  width: 68px;
  min-width: 68px;
  max-width: 68px;
  text-align: center;
  color: #15803d;
  -webkit-text-fill-color: #15803d;
  flex-shrink: 0;
  box-sizing: border-box;
}
.time-input-inline::placeholder {
  color: #15803d;
  opacity: 1;
}
.mini {
  text-align: center;
  font-size: 14px;
  min-width: 60px; /* サブ列の幅を縮小 */
}
.day-end {
  border-right: 4px solid #a2b0c5 !important;
}
.sticky-col {
  position: sticky;
  left: 0;
  background: #f8fafc;
  z-index: 3;
}
thead .sticky-col {
  z-index: 8;
}
.number-col {
  width: 60px;
  min-width: 60px;
  max-width: 60px;
  text-align: center;
}
.code-col {
  left: 60px;
  width: 187px; /* 156px の1.2倍 */
  min-width: 187px;
  max-width: 187px;
}
.name-col {
  left: 247px;
  width: 100px;
  min-width: 100px;
  max-width: 100px;
  border-right: 2px solid #b5c1d2 !important;
}
.row-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}
.reorder {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.mini-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  background: #fff;
  cursor: pointer;
  line-height: 1;
}
.mini-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.product-info {
  display: block;
  padding: 3px 4px;
  font-size: 13px;
  font-weight: 500;
  color: #000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.plan-grid input,
.plan-grid select {
  width: 100%;
  box-sizing: border-box;
  padding: 3px 4px;
  border: 1px solid #d1d5db;
  border-radius: 2px;
  font-size: 13px;
  font-weight: 500;
  color: #000;
}
.plan-grid input.locked {
  background: #f1f5f9;
  color: #666;
  cursor: not-allowed;
}
.num {
  text-align: right;
  min-width: 80px; /* セル幅を広げて日付列が潰れないようにする */
}
.num input {
  width: 100%;
  text-align: right;
}
.num input[type="number"]::-webkit-outer-spin-button,
.num input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.num input[type="number"] {
  -moz-appearance: textfield;
  appearance: textfield;
}
.readonly-value {
  display: inline-block;
  width: 40px;
  padding: 3px 4px;
  text-align: right;
  color: #666;
  font-size: 13px;
  font-weight: 500;
  color: #000;
}
.stock {
  background: #f7f9fb;
}
.plan {
  background: #fffbe6;
}
.sequence {
  background: #e0f2fe;
}
.stock-plan {
  background: #f1f7ff;
}
.no-data {
  text-align: center;
  color: #888;
  padding: 10px 0;
}
.footer-actions {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.btn,
.btn-secondary {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn:hover,
.btn-secondary:hover {
  background: #f3f4f6;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.btn.accent {
  background: #16a34a;
  color: #fff;
  border-color: #0f8a3c;
}
.btn.accent:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}


.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.modal-content {
  background: #fff;
  border-radius: 6px;
  width: 420px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
.modal-content h2 {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 700;
}
.modal-content textarea {
  width: 100%;
  resize: vertical;
  min-height: 90px;
  padding: 8px;
  border: 1px solid #cfd6e1;
  border-radius: 4px;
  font-size: 12px;
  font-family: inherit;
}
.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.export-modal h2 {
  margin-bottom: 6px;
}
.export-note {
  font-size: 12px;
  color: #4b5563;
  margin: 0 0 12px;
  line-height: 1.5;
}
.export-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.process-section {
  margin-top: 8px;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 8px 10px;
}
.process-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.process-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.process-title {
  font-weight: 700;
  font-size: 14px;
}
.process-title-inline {
  margin-left: 8px;
  font-weight: 600;
  color: #111827;
}
.process-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.process-status {
  font-size: 12px;
  color: #2563eb;
}
.process-panels {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.process-card {
  border: 1px solid #d7dfe8;
  border-radius: 6px;
  background: #f9fbff;
}
.process-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 10px 0;
}
.process-card__title {
  font-weight: 700;
}
.process-card__sub {
  color: #4b5563;
  font-size: 12px;
}
.setup-count {
  font-size: 13px;
  color: #6b7280;
  padding: 4px 8px;
  background: #fef3c7;
  border-radius: 4px;
  border: 1px solid #fbbf24;
}
.setup-count__value {
  font-weight: 700;
  color: #d97706;
  font-size: 14px;
}
.process-card__body {
  padding: 8px 10px 10px;
}
.process-table-wrap {
  overflow-x: auto;
}
.process-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.process-table th,
.process-table td {
  border: 1px solid #d7dfe8;
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 12px;
}
.process-table .mini-head {
  text-align: center;
  background: #eef2f7;
  min-width: 180px;
}
.process-table .mini-cell {
  text-align: right;
  min-width: 180px; /* 日付列幅を約2倍に拡大 */
}
.process-table .cell-line {
  text-align: right;
  font-size: 12px;
}
.process-table .cell-line.sub {
  color: #6b7280;
}
.process-table .cell-line.time {
  color: #0f766e;
  font-weight: 700;
}
.process-table .capacity {
  color: #475569;
  font-weight: 500;
  margin-left: 4px;
}
.process-table .cell-line.muted {
  color: #94a3b8;
}
.process-table .total-row {
  background: #fefce8;
  font-weight: 700;
}
.process-table .total .cell-line {
  font-weight: 700;
}
.process-empty {
  font-size: 12px;
  color: #6b7280;
  padding: 4px 0;
}
.process-meta {
  color: #111827;
  font-size: 13px;
  white-space: nowrap;
}
.gantt-section {
  margin-top: 6px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.load-section {
  margin-top: 6px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.load-body {
  min-height: 40px;
}
.load-message {
  color: #6b7280;
  font-size: 12px;
  padding: 6px 0;
}
.load-table-wrap {
  overflow-x: auto;
}
.load-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.load-table th,
.load-table td {
  border: 1px solid #d7dfe8;
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
  color: #000;
  text-align: center;
}
.load-table thead th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: #e7edf7;
}
.load-process-col {
  width: 180px;
  min-width: 180px;
  max-width: 180px;
  border-right: 2px solid #b5c1d2 !important;
  text-align: left;
}
.processing-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  pointer-events: all;
}
.processing-box {
  background: #1f2a44;
  color: #fff;
  padding: 18px 28px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  text-align: center;
  min-width: 240px;
}
.processing-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.processing-sub {
  margin: 6px 0 0;
  font-size: 13px;
  opacity: 0.9;
}
</style>
