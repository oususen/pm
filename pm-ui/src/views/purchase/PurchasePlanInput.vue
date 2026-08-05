<template>
  <div class="plan-container">
    <h2 class="page-title">仕入れ計画 <DataSourceDialog title="" :sources="dsSources" /></h2>

    <div class="basis-tab-bar">
      <button
        type="button"
        class="basis-tab-item"
        :class="{ active: basisMode === 'inventory' }"
        @click="basisMode = 'inventory'"
      >
        在庫基準
      </button>
      <button
        type="button"
        class="basis-tab-item"
        :class="{ active: basisMode === 'progress' }"
        @click="basisMode = 'progress'"
      >
        進度基準
      </button>
    </div>

    <div class="toolbar">
      <div class="toolbar-left">
        <div class="field">
          <label>仕入先</label>
          <select v-model.number="selectedSupplier" @change="loadData">
            <option value="">すべて</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">
              {{ s.supplier_code }} - {{ s.supplier_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>表示開始日</label>
          <input type="date" v-model="startDate" @change="refreshDates" class="input-narrow" />
        </div>
        <div class="field">
          <label>期間</label>
          <select v-model.number="horizonDays" @change="refreshDates" class="select-narrow">
            <option :value="30">30日</option>
            <option :value="60">60日</option>
            <option :value="90">90日</option>
            <option :value="120">120日</option>
          </select>
        </div>
        <div class="field">
          <label>検索</label>
          <input type="text" v-model="keyword" placeholder="品番/品名で絞り込み" />
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="resetRows" :disabled="processing || !rows.length">クリア</button>
        <button class="btn" @click="autoFillPlan" :disabled="processing || !rows.length || !canEdit">自動計画</button>
        <button class="btn" @click="openChangeReasonDialog" :disabled="processing || !canEdit">計画変更</button>
        <button class="btn" @click="savePlan" :disabled="processing || !rows.length || !selectedSupplier || !canEdit">保存</button>
        <button class="btn" @click="doDisplayOnly" :disabled="processing || !selectedSupplier">表示のみ</button>
        <button class="btn" @click="doPickup" :disabled="processing || !selectedSupplier || !canEdit">需要取込</button>
        <button class="btn primary" @click="doPickupWithInventory" :disabled="processing || !selectedSupplier || !canEdit">取込＋在庫計算</button>
      </div>
    </div>

    <div class="notice-bar">
      ※ 需要は「需要取込」実行時の表示期間（開始日〜期間）で集計した値です。期間を変えて取り込み直すと需要が変わります。
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
              :colspan="isProgressMode ? 6 : 7"
              class="date-head day-end"
              :class="c.dayClass"
            >
              {{ c.label }}
            </th>
          </tr>
          <tr class="head-level2">
            <template v-for="(c, colIdx) in dateColumns" :key="c.key">
              <template v-if="isProgressMode">
                <th class="mini" :class="c.dayClass">内示</th>
                <th class="mini" :class="c.dayClass">確定</th>
                <th class="mini" :class="c.dayClass">実績</th>
                <th class="mini" :class="c.dayClass">計画</th>
                <th class="mini" :class="c.dayClass">計進</th>
                <th class="mini day-end" :class="c.dayClass">進度</th>
              </template>
              <template v-else>
                <th class="mini" :class="c.dayClass">需要</th>
                <th class="mini" :class="c.dayClass">実績</th>
                <th class="mini" :class="c.dayClass">在庫</th>
                <th class="mini" :class="c.dayClass">計画</th>
                <th class="mini" :class="c.dayClass">計庫</th>
                <th class="mini" :class="c.dayClass">進度</th>
                <th class="mini day-end" :class="c.dayClass">計進</th>
              </template>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in filteredRows" :key="row.id">
            <td class="sticky-col number-col">
              <span class="product-info">{{ idx + 1 }}</span>
            </td>
            <td class="sticky-col code-col">
              <span class="product-info">{{ row.product_code || getProductCode(row.product_id) }}</span>
            </td>
            <td class="sticky-col name-col">
              <span class="product-info">{{ row.product_name || getProductName(row.product_id) }}</span>
            </td>
            <template v-for="(c, colIdx) in dateColumns" :key="c.key">
              <template v-if="isProgressMode">
                <td class="num" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(row.daily?.[c.key]?.forecast) }">{{ displayValue(row.daily?.[c.key]?.forecast) }}</span>
                </td>
                <td class="num" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(row.daily?.[c.key]?.firm) }">{{ displayValue(row.daily?.[c.key]?.firm) }}</span>
                </td>
                <td class="num" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(row.daily?.[c.key]?.actual) }">{{ displayValue(row.daily?.[c.key]?.actual) }}</span>
                </td>
                <td class="num plan" :class="c.dayClass">
                  <input
                    type="text"
                    inputmode="decimal"
                    :value="row.daily[c.key].plan === 0 || row.daily[c.key].plan === '' || row.daily[c.key].plan == null ? '' : row.daily[c.key].plan"
                    @input="onPlanInput(row, c.key, $event.target.value)"
                    :data-row="idx"
                    :data-col="colIdx"
                    @keydown="onCellKeydown($event, idx, colIdx)"
                    :disabled="!canEdit || isPlanCellLocked(c.key)"
                    :class="{ locked: isPlanCellLocked(c.key), negative: isNegativeValue(row.daily[c.key].plan) }"
                  />
                </td>
                <td class="num planned-progress" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(getPlannedProgressDisplay(row, colIdx)) }">{{ displayValue(getPlannedProgressDisplay(row, colIdx)) }}</span>
                </td>
                <td class="num progress day-end" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(getProgressDisplay(row, colIdx)) }">{{ displayValue(getProgressDisplay(row, colIdx)) }}</span>
                </td>
              </template>
              <template v-else>
                <td class="num" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(row.daily?.[c.key]?.demand) }">{{ displayValue(row.daily?.[c.key]?.demand) }}</span>
                </td>
                <td class="num" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(row.daily?.[c.key]?.actual) }">{{ displayValue(row.daily?.[c.key]?.actual) }}</span>
                </td>
                <td class="num stock" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(getStockDisplay(row, colIdx)) }">{{ displayValue(getStockDisplay(row, colIdx)) }}</span>
                </td>
                <td class="num plan" :class="c.dayClass">
                  <input
                    type="text"
                    inputmode="decimal"
                    :value="row.daily[c.key].plan === 0 || row.daily[c.key].plan === '' || row.daily[c.key].plan == null ? '' : row.daily[c.key].plan"
                    @input="onPlanInput(row, c.key, $event.target.value)"
                    :data-row="idx"
                    :data-col="colIdx"
                    @keydown="onCellKeydown($event, idx, colIdx)"
                    :disabled="!canEdit || isPlanCellLocked(c.key)"
                    :class="{ locked: isPlanCellLocked(c.key), negative: isNegativeValue(row.daily[c.key].plan) }"
                  />
                </td>
                <td class="num stock-plan" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(getPlanStockDisplay(row, colIdx)) }">{{ displayValue(getPlanStockDisplay(row, colIdx)) }}</span>
                </td>
                <td class="num progress" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(getProgressDisplay(row, colIdx)) }">{{ displayValue(getProgressDisplay(row, colIdx)) }}</span>
                </td>
                <td class="num planned-progress day-end" :class="c.dayClass">
                  <span class="readonly-value" :class="{ negative: isNegativeValue(getPlannedProgressDisplay(row, colIdx)) }">{{ displayValue(getPlannedProgressDisplay(row, colIdx)) }}</span>
                </td>
              </template>
            </template>
          </tr>
          <tr v-if="!filteredRows.length">
            <td :colspan="3 + dateColumns.length * (isProgressMode ? 6 : 7)" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="footer-actions">
      <button class="btn-secondary">F1: 終了</button>
      <button class="btn-secondary">F3: クリア</button>
      <button class="btn-secondary" @click="doDisplayOnly" :disabled="processing || !selectedSupplier">F4: 表示のみ</button>
      <button class="btn-secondary">F5: 備考</button>
      <button class="btn-secondary" @click="doPickup" :disabled="processing || !selectedSupplier || !canEdit">F6: 需要取込</button>
      <button class="btn-secondary" @click="doPickupWithInventory" :disabled="processing || !selectedSupplier || !canEdit">F8: 取込＋在庫計算</button>
      <button class="btn-secondary">F10: 印刷</button>
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

    <div v-if="processing" class="processing-overlay">
      <div class="processing-box">
        <p class="processing-title">データ更新中</p>
        <p class="processing-sub">少々お待ちください</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const entry = permissions.find((item) => item.resource === 'purchase.plan_input')
  if (entry) return Boolean(entry.can_edit)
  return hasPermission(user, 'purchase', 'edit')
})

const dsSources = [
  { section: '計画データ' },
  { op: '需要/実績 読み書き', table: 'line_backlog', desc: '需要(seq=0)・計画実績(seq>0)・計画数入力' },
  { op: '需要 読み取り', table: 'line_demand', desc: '顧客需要（内示/確定）' },
  { op: '在庫再計算 書き込み', table: 'line_backlog', desc: '計画保存後の在庫・進度再計算' },
  { section: '設定' },
  { op: 'ロック設定 読み取り', table: 'purchase_plan_lock_setting', desc: '計画変更ロック日設定' },
  { section: 'マスタ' },
  { op: '仕入先 読み取り', table: 'm_supplier', desc: '仕入先マスタ' },
  { op: '製品 読み取り', table: 'm_product', desc: '製品マスタ（購入品フィルタ）' },
  { op: 'ルーティング 読み取り', table: 'm_routing_step', desc: '仕入先→製品の紐付け特定' },
  { op: 'BOM 読み取り', table: 'm_bom_item', desc: '部品表（sourcing_type=BUY）' },
  { op: 'ライン 読み取り', table: 'm_line', desc: '仕入先コードからライン解決' },
  { op: 'カレンダー 読み取り', table: 'm_calendar / m_calendar_day', desc: '営業日カレンダー（休日表示）' },
]

const basisMode = ref('inventory')
const isProgressMode = computed(() => basisMode.value === 'progress')

const selectedSupplier = ref('')
const purchaseLineId = ref('')
const purchaseProcessId = ref('')
const startDate = ref(formatISODate(new Date()))
const horizonDays = ref(30)
const keyword = ref('')
const gridWrapperRef = ref(null)
const lockDays = ref(0)
const isEditUnlocked = ref(false)
const changeReason = ref('')
const changeReasonDraft = ref('')
const showChangeReasonDialog = ref(false)

const suppliers = ref([])
const products = ref([])
const rows = ref([])
const processing = ref(false)
const holidayDates = ref(new Set())

const buildLocalDate = (dateText) => {
  if (!dateText) return new Date()
  const [y, m, d] = dateText.split('-').map((v) => Number(v))
  if (!y || !m || !d) return new Date()
  return new Date(y, m - 1, d)
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
    const isHoliday = holidayDates.value.has(key)
    const dayClass = day === 0 ? 'sun' : day === 6 ? 'sat' : isHoliday ? 'sun' : ''
    cols.push({ key, label, dayClass })
  }
  return cols
})

const tableMinWidth = computed(() => {
  const fixedColsWidth = 40 + 187 + 100
  const perDayWidth = isProgressMode.value ? 270 : 315
  return fixedColsWidth + dateColumns.value.length * perDayWidth
})

const formatDateKey = (dateObj) => {
  const year = dateObj.getFullYear()
  const month = String(dateObj.getMonth() + 1).padStart(2, '0')
  const day = String(dateObj.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
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

const initDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = { demand: 0, actual: 0, stock: 0, plan: '', plan_stock: 0, progress: 0, planned_progress: 0, plan_base: 0, has_row: false, forecast: 0, firm: 0 }
  })
  return daily
}

const resetRows = () => {
  rows.value = []
}

const savePlan = async () => {
  if (!canEdit.value) return
  if (!selectedSupplier.value) {
    alert('仕入先を選択してください。')
    return
  }
  if (isEditUnlocked.value && !changeReason.value) {
    alert('変更理由を入力してください。')
    return
  }
  const lineId = await resolvePurchaseLineId()
  if (!lineId || !purchaseProcessId.value) {
    alert('仕入れラインの解決に失敗しました。')
    return
  }
  const items = []
  rows.value.forEach((r) => {
    if (!r.product_id) return
    // 仕入れ用のprocess_idはダミー値（1固定）を使用
    const process_id = r.process_id || purchaseProcessId.value
    dateColumns.value.forEach((c) => {
      const daily = r.daily[c.key]
      const currentPlan = daily.plan === '' || daily.plan == null ? 0 : Number(daily.plan)
      const originalPlan = toNumber(daily.plan_base)

      // 変更があったデータのみを送信対象とする
      if (currentPlan !== originalPlan) {
        items.push({
          product_id: r.product_id,
          process_id: process_id,
          plan_date: c.key,
          plan_qty: currentPlan,
          sequence_no: 1,
        })
      }
    })
  })
  if (!items.length) {
    alert('保存するデータがありません。')
    return
  }
  processing.value = true
  try {
    const payload = {
      line_id: lineId,
      items,
    }
    if (isEditUnlocked.value && changeReason.value) {
      payload.change_reason = changeReason.value
    }
    const res = await api.lineBacklogs.save(payload)
    console.info('保存結果', res.data)

    // 再計算の開始日は、画面の表示開始日と今日のうち、早い方（過去の方）を採用する
    // これにより、未来の日付を表示して保存した場合でも、今日からの在庫推移が正しく再計算されるようにする
    // JST(UTC+9)に変換し、8時区切りで業務日を算出
    const nowJst = new Date(Date.now() + 9 * 60 * 60 * 1000)
    if (nowJst.getUTCHours() < 8) nowJst.setUTCDate(nowJst.getUTCDate() - 1)
    const today = formatISODate(nowJst)
    const recalcStartDate = startDate.value < today ? startDate.value : today

    const recalcRes = await api.lineBacklogs.recalculateInventory({
      line_id: lineId,
      start_date: recalcStartDate,
      end_date: endDate.value,
    })
    const productCount = recalcRes?.data?.product_count ?? 0
    const recalcDays = Math.round((new Date(endDate.value) - new Date(recalcStartDate)) / 86400000) + 1
    alert(`${items.length}件の計画を保存しました。\n${productCount}製品 × ${recalcDays}日分の在庫・進度を再計算しました。`)
    isEditUnlocked.value = false
    changeReason.value = ''
    await fetchAndApplyData(lineId)
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

const isNegativeValue = (value) => {
  if (value === null || value === undefined || value === '') return false
  const num = Number(value)
  return Number.isFinite(num) && num < 0
}

const getPlanQtyTotal = (daily) => {
  if (!daily) return 0
  return toNumber(daily.plan)
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

const getProgressDisplay = (row, colIdx) => {
  if (!row || !row.daily) return ''
  const cols = dateColumns.value
  let carry = null
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    const raw = daily.progress
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

const getPlannedProgressDisplay = (row, colIdx) => {
  if (!row || !row.daily) return ''
  const cols = dateColumns.value
  let carry = null
  let delta = 0
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    const raw = daily.planned_progress
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

const focusCellInput = (rowIdx, colIdx) => {
  const root = gridWrapperRef.value
  if (!root) return
  const selector = `input[data-row="${rowIdx}"][data-col="${colIdx}"]`
  const target = root.querySelector(selector)
  if (target) {
    target.focus()
    if (typeof target.select === 'function') {
      target.select()
    }
  }
}

const onCellKeydown = (event, rowIdx, colIdx) => {
  const key = event.key
  const supportedKeys = ['Enter', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']
  if (!supportedKeys.includes(key)) return

  event.preventDefault()

  const maxRow = filteredRows.value.length - 1
  const maxCol = dateColumns.value.length - 1
  if (maxRow < 0 || maxCol < 0) return

  let nextRow = rowIdx
  let nextCol = colIdx

  if (key === 'Enter') {
    nextRow += event.shiftKey ? -1 : 1
  } else if (key === 'ArrowUp') {
    nextRow -= 1
  } else if (key === 'ArrowDown') {
    nextRow += 1
  } else if (key === 'ArrowLeft') {
    nextCol -= 1
  } else if (key === 'ArrowRight') {
    nextCol += 1
  }

  if (nextRow < 0 || nextRow > maxRow) return
  if (nextCol < 0 || nextCol > maxCol) return

  focusCellInput(nextRow, nextCol)
}

const refreshDates = () => {
  rows.value.forEach((r) => {
    r.daily = initDaily()
  })
  loadHolidayColumns()
}

const buildWeekendFallback = () => {
  const fallback = new Set()
  const base = buildLocalDate(startDate.value)
  for (let i = 0; i < horizonDays.value; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i)
    const day = d.getDay()
    if (day === 0 || day === 6) {
      fallback.add(formatDateKey(d))
    }
  }
  return fallback
}

const normalizeList = (payload) => {
  return Array.isArray(payload) ? payload : payload?.results || []
}

const loadHolidayColumns = async () => {
  const fallback = buildWeekendFallback()
  try {
    const pickDaiso = (rows) => {
      const list = rows || []
      const exact = list.find((row) => String(row.calendar_code || '').trim().toLowerCase() === 'daiso')
      if (exact) return exact
      return list.find((row) => {
        const code = String(row.calendar_code || '').trim().toLowerCase()
        const name = String(row.calendar_name || '').trim().toLowerCase()
        return code.includes('daiso') || name.includes('daiso') || name.includes('ダイソウ')
      })
    }

    const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 200 })
    const rows = normalizeList(res.data || [])
    let daiso = pickDaiso(rows)
    if (!daiso) {
      const fallbackRes = await api.calendars.getCalendars({ page_size: 5000 })
      const fallbackRows = normalizeList(fallbackRes.data || [])
      daiso = pickDaiso(fallbackRows)
    }
    if (!daiso?.id) {
      holidayDates.value = fallback
      return
    }

    const daysRes = await api.calendars.getCalendarDays(daiso.id, { page_size: 5000 })
    const dayRows = normalizeList(daysRes.data || [])
    const displayedDates = new Set()
    const base = buildLocalDate(startDate.value)
    for (let i = 0; i < horizonDays.value; i++) {
      const d = new Date(base)
      d.setDate(d.getDate() + i)
      displayedDates.add(formatDateKey(d))
    }
    const holidaySet = new Set(
      dayRows
        .filter((day) => !day.is_working_day && displayedDates.has(day.target_date))
        .map((day) => day.target_date)
    )
    holidayDates.value = holidaySet.size > 0 ? new Set([...fallback, ...holidaySet]) : fallback
  } catch (e) {
    console.error('仕入計画 休日判定の取得エラー', e)
    holidayDates.value = fallback
  }
}

const loadData = async () => {
  rows.value = []
  purchaseLineId.value = ''
  purchaseProcessId.value = ''
  await fetchProducts(selectedSupplier.value || null)
}

const onPlanInput = (row, dateKey, value) => {
  if (!canEdit.value) return
  if (isPlanCellLocked(dateKey)) return
  row.daily[dateKey].plan = value === '' ? '' : value
}

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = res.data.results || res.data || []
}

const fetchLockSetting = async () => {
  try {
    const res = await api.purchasePlanLockSetting.getSetting()
    lockDays.value = Number(res.data?.lock_days ?? 0)
  } catch (e) {
    console.error('仕入計画ロック設定の取得エラー', e)
    lockDays.value = 0
  }
}

const fetchProducts = async (supplierId = null) => {
  try {
    let targetProductIds = new Set()
    if (supplierId) {
      // ルーティング基準（互換）:
      // 1) 外作先一致
      // 2) 仕入先コードと一致するライン上の工程
      const supplier = suppliers.value.find((s) => Number(s.id) === Number(supplierId))
      const [stepsBySupplierRes, linesRes] = await Promise.all([
        api.routings.getRoutingSteps({ supplier: supplierId, page_size: 5000 }),
        api.lines.getLines({ page_size: 500 }),
      ])
      const stepsBySupplier = stepsBySupplierRes.data.results || stepsBySupplierRes.data || []
      const allLines = linesRes.data.results || linesRes.data || []
      const purchaseLine = supplier?.supplier_code
        ? allLines.find((l) => String(l.line_code || '').trim() === String(supplier.supplier_code || '').trim())
        : null
      let stepsByLine = []
      if (purchaseLine?.id) {
        const stepsByLineRes = await api.routings.getRoutingSteps({ line: purchaseLine.id, page_size: 5000 })
        stepsByLine = stepsByLineRes.data.results || stepsByLineRes.data || []
      }
      const mergedSteps = [...stepsBySupplier, ...stepsByLine]
      targetProductIds = new Set(
        mergedSteps
          .map((s) => Number(s.output_product))
          .filter((id) => Number.isFinite(id) && id > 0)
      )
    } else {
      const params = { sourcing_type: 'BUY' }
      const bomItemsRes = await api.bomItems.getBOMItems(params)
      const bomItems = bomItemsRes.data.results || bomItemsRes.data || []
      targetProductIds = new Set(bomItems.map((item) => item.child_product))
    }

    // 全製品から対象のみを抽出
    const allProducts = await api.products.getAllProducts()
    const filtered =
      supplierId && targetProductIds.size
        ? allProducts.filter((p) => !p.is_phantom && targetProductIds.has(p.id))
        : allProducts.filter((p) => !p.is_phantom)

    products.value = filtered.sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
  } catch (e) {
    console.error('仕入れ対象製品の取得エラー', e)
    products.value = []
  }
}

onMounted(async () => {
  try {
    await Promise.all([fetchSuppliers(), fetchProducts(), fetchLockSetting()])
    await loadHolidayColumns()
    await loadData()
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})

const fetchAndApplyData = async (lineId) => {
  const productIds = products.value.map((p) => p.id)
  if (!productIds.length) {
    alert('この仕入先の購入部品が見つかりません。')
    rows.value = []
    return
  }

  const [backlogRes, lineDemandRes] = await Promise.all([
    api.lineBacklogs.getLineBacklogs({
      line: lineId,
      product__in: productIds.join(','),
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    }),
    api.lineDemands.list({
      line: lineId,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    }),
  ])
  const backlogs = backlogRes.data.results || backlogRes.data || []

  // 製品ごとにグルーピング
  const grouped = new Map()
  products.value.forEach((p) => {
    grouped.set(p.id, {
      id: `prod-${p.id}`,
      product_id: p.id,
      product_code: p.product_code,
      product_name: p.product_name,
      process_id: purchaseProcessId.value,
      daily: initDaily(),
    })
  })

  backlogs.forEach((d) => {
    if (!d.product) return
    if (d.sequence_no !== 0 && d.sequence_no !== 1) return
    if (!purchaseProcessId.value && d.process) {
      purchaseProcessId.value = d.process
    }
    const row = grouped.get(d.product)
    if (!row) return
    const dateKey = d.plan_date
    if (!row.daily[dateKey]) return
    if (d.sequence_no === 0) {
      // 基礎行: 需要・実績・在庫・進度
      row.daily[dateKey].demand = Number(d.order_qty || 0)
      row.daily[dateKey].actual = Number(d.actual_qty || 0)
      row.daily[dateKey].stock = Number(d.stock_qty || 0)
      row.daily[dateKey].plan_stock = Number(d.planned_stock_qty || 0)
      row.daily[dateKey].progress = Number(d.progress_qty || 0)
      row.daily[dateKey].planned_progress = Number(d.planned_progress_qty || 0)
      row.daily[dateKey].has_row = true
    } else if (d.sequence_no === 1) {
      // 計画行: plan_qty のみ
      row.daily[dateKey].plan = d.plan_qty === null || d.plan_qty === undefined ? '' : d.plan_qty === 0 ? '' : d.plan_qty
      row.daily[dateKey].plan_base = Number(d.plan_qty || 0)
    }
  })

  const demandData = lineDemandRes?.data?.results || lineDemandRes?.data || []
  demandData.forEach((d) => {
    if (!d.product) return
    const row = grouped.get(d.product)
    if (!row) return
    const dateKey = d.plan_date
    if (!row.daily[dateKey]) return
    row.daily[dateKey].forecast += Number(d.forecast_qty || 0)
    row.daily[dateKey].firm += Number(d.firm_qty || 0)
  })

  rows.value = Array.from(grouped.values())
}

const doDisplayOnly = async () => {
  if (!selectedSupplier.value) {
    alert('仕入先を選択してください。')
    return
  }
  processing.value = true
  try {
    await fetchProducts(selectedSupplier.value)
    // pickupPurchaseを呼ばずにラインを解決する
    let lineId = purchaseLineId.value
    if (!lineId) {
      const supplier = suppliers.value.find((s) => Number(s.id) === Number(selectedSupplier.value))
      if (supplier?.supplier_code) {
        const linesRes = await api.lines.getLines({ page_size: 500 })
        const lines = linesRes.data.results || linesRes.data || []
        const purchaseLine = lines.find((l) => l.line_code === supplier.supplier_code)
        lineId = purchaseLine?.id || ''
        purchaseLineId.value = lineId
      }
    }
    if (!lineId) {
      alert('仕入れラインの解決に失敗しました。')
      rows.value = []
      return
    }

    if (!purchaseProcessId.value) {
      const stepsRes = await api.routings.getRoutingSteps({ line: lineId })
      const steps = stepsRes.data.results || stepsRes.data || []
      const stepWithProcess = steps.find(s => s.process)
      if (stepWithProcess) {
        purchaseProcessId.value = stepWithProcess.process
      }
    }

    await fetchAndApplyData(lineId)
  } catch (e) {
    console.error('仕入れ計画 表示のみエラー', e)
    alert('データ取得に失敗しました。')
  } finally {
    processing.value = false
  }
}

const doPickup = async () => {
  if (!canEdit.value) return
  if (!selectedSupplier.value) {
    alert('仕入先を選択してください。')
    return
  }
  processing.value = true
  try {
    await fetchProducts(selectedSupplier.value)
    const pickupRes = await api.lineBacklogs.pickupPurchase({
      supplier_id: selectedSupplier.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    purchaseLineId.value = pickupRes?.data?.line_id || ''
    purchaseProcessId.value = pickupRes?.data?.process_id || ''
    if (!purchaseLineId.value || !purchaseProcessId.value) {
      alert('仕入れラインの解決に失敗しました。')
      rows.value = []
      return
    }
    await fetchAndApplyData(purchaseLineId.value)
  } catch (e) {
    console.error('仕入れ計画 需要取込エラー', e)
    alert('取り込みに失敗しました。')
  } finally {
    processing.value = false
  }
}

const doPickupWithInventory = async () => {
  if (!canEdit.value) return
  if (!selectedSupplier.value) {
    alert('仕入先を選択してください。')
    return
  }
  processing.value = true
  try {
    await fetchProducts(selectedSupplier.value)
    const pickupRes = await api.lineBacklogs.pickupPurchase({
      supplier_id: selectedSupplier.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    purchaseLineId.value = pickupRes?.data?.line_id || ''
    purchaseProcessId.value = pickupRes?.data?.process_id || ''
    if (!purchaseLineId.value || !purchaseProcessId.value) {
      alert('仕入れラインの解決に失敗しました。')
      rows.value = []
      return
    }
    await api.lineBacklogs.recalculateInventory({
      line_id: purchaseLineId.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    await fetchAndApplyData(purchaseLineId.value)
  } catch (e) {
    console.error('仕入れ計画 取込＋在庫計算エラー', e)
    alert('取り込みに失敗しました。')
  } finally {
    processing.value = false
  }
}

const resolvePurchaseLineId = async () => {
  if (purchaseLineId.value) return purchaseLineId.value
  if (!selectedSupplier.value) return ''
  try {
    const res = await api.lineBacklogs.pickupPurchase({
      supplier_id: selectedSupplier.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    purchaseLineId.value = res?.data?.line_id || ''
    purchaseProcessId.value = res?.data?.process_id || ''
    return purchaseLineId.value
  } catch (e) {
    console.error('仕入れライン解決エラー', e)
    return ''
  }
}

const autoFillPlan = () => {
  if (!canEdit.value) return
  if (!rows.value.length) return

  const hasExistingPlan = rows.value.some((r) =>
    dateColumns.value.some((c) => {
      const plan = r.daily[c.key]?.plan
      return plan !== '' && plan != null && Number(plan) !== 0
    })
  )

  if (hasExistingPlan) {
    if (!confirm('既存の計画値を上書きしますか？')) return
  }

  rows.value.forEach((r) => {
    dateColumns.value.forEach((c) => {
      if (isPlanCellLocked(c.key)) return
      const daily = r.daily[c.key]
      const demandValue = isProgressMode.value
        ? Number(daily?.forecast || 0) + Number(daily?.firm || 0)
        : daily?.demand
      if (demandValue !== null && demandValue !== undefined && Number(demandValue) !== 0) {
        r.daily[c.key].plan = demandValue
      }
    })
  })
}

const openChangeReasonDialog = () => {
  if (!canEdit.value) return
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
</script>

<style scoped>
.plan-container {
  padding: 8px 10px 14px;
  background: #eef2f6;
  font-size: 12px;
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
  color: #1f2a44;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}
.basis-tab-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.basis-tab-item {
  border: 1px solid #b9c5d6;
  background: #f8fafc;
  color: #1f2937;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.basis-tab-item.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}
.notice-bar {
  font-size: 11px;
  color: #7a5800;
  background: #fff8e1;
  border-left: 3px solid #f0b429;
  padding: 4px 8px;
  margin-bottom: 6px;
  border-radius: 2px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  padding: 8px;
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
  gap: 4px;
}
.field label {
  font-size: 12px;
  color: #444;
}
.field input,
.field select {
  padding: 6px 8px;
  min-width: 140px;
}
.field input.input-narrow {
  min-width: unset;
  width: 110px;
}
.field select.select-narrow {
  min-width: unset;
  width: 55px;
  padding: 6px 0;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.grid-wrapper {
  margin-top: 10px;
  flex: 1;
  min-height: 0;
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
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
  color: #000;
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
  min-width: 270px;
}
.mini {
  text-align: center;
  font-size: 12px;
  min-width: 30px;
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
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  text-align: center;
}
.code-col {
  left: 40px;
  width: 125px;
  min-width: 125px;
  max-width: 125px;
}
.name-col {
  left: 165px;
  width: 130px;
  min-width: 130px;
  max-width: 130px;
  border-right: 2px solid #b5c1d2 !important;
}
.product-info {
  display: block;
  padding: 3px 4px;
  font-size: 12px;
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
  font-size: 12px;
  font-weight: 500;
  color: #000;
}
.plan-grid input.locked {
  background: #f1f5f9;
  color: #666;
  cursor: not-allowed;
}
.plan-grid tbody td.num.plan {
  padding: 0 !important;
}
.plan-grid tbody td.num.plan input {
  border: 0;
  border-radius: 0;
  padding: 0 4px;
  margin: 0;
  min-height: 24px;
  background: transparent;
}
.num {
  text-align: right;
  min-width: 30px;
}
.num input {
  width: 100%;
  text-align: right;
}
.readonly-value {
  display: inline-block;
  width: 28px;
  padding: 3px 4px;
  text-align: right;
  color: #666;
  font-size: 12px;
  font-weight: 500;
  color: #000;
}
.readonly-value.negative {
  color: #c62828;
  font-weight: 700;
}
.num input.negative {
  color: #c62828;
  font-weight: 700;
}
.stock {
  background: #f7f9fb;
}
.plan {
  background: #fffbe6;
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
  margin-top: 10px;
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




