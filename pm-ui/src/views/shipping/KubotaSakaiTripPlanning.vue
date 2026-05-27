<template>
  <div class="trip-planning-page">
    <div class="toolbar">
      <div class="field">
        <label>出荷開始日</label>
        <input v-model="targetDate" type="date" />
      </div>
      <div class="field">
        <label>期間</label>
        <select v-model.number="horizonDays">
          <option :value="5">5日</option>
          <option :value="14">14日</option>
          <option :value="31">31日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
        </select>
      </div>
      <div class="field search-field">
        <label>検索</label>
        <input v-model.trim="keyword" type="text" placeholder="品番" @keydown.enter="loadGrid" />
      </div>
      <div class="field">
        <label>お気に入り</label>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>登録名</label>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
      </div>
      <button class="btn favorite-btn" title="お気に入り登録" :disabled="loading || saving || importing" @click="saveFavorite">★</button>
      <button class="btn import-btn" :disabled="importing || loading" @click="importOrders">
        {{ importing ? '取込中...' : '取込' }}
      </button>
      <button class="btn save-btn" :disabled="loading || saving" @click="save">保存</button>
      <button class="btn" :disabled="loading" @click="loadGrid">表示</button>
      <button class="btn" :disabled="loading || exportingCsv" @click="exportLoadDetailCsv">
        {{ exportingCsv ? '出力中...' : '占有CSV' }}
      </button>
      <button class="btn pickup-btn" :disabled="loading || exportingPickupPdf" @click="openPickupPdfDialog">
        {{ exportingPickupPdf ? '出力中...' : '集荷明細PDF' }}
      </button>
      <button class="btn detail-btn" :disabled="loading" @click="showTruckDetail = !showTruckDetail">
        便詳細
      </button>
      <button class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button>
      <button class="btn pseudo-product-btn" :disabled="loading" @click="togglePseudoProductPanel">
        擬似便対象製品
      </button>
      <button class="btn auto-assign-btn" :disabled="loading || saving || autoAssigning" @click="openAutoAssignDialog">
        自動便振分
      </button>
      <span v-if="lastAdjustedAt" class="adj-badge">最新納期調整日: {{ formatAdjDate(lastAdjustedAt) }}</span>
    </div>

    <div v-if="showAutoAssignDialog" class="modal-overlay" @click.self="closeAutoAssignDialog">
      <div class="modal-card">
        <h3 class="modal-title">自動便振分</h3>
        <div class="modal-fields">
          <label class="modal-field">
            <span>適用カレンダ</span>
            <select v-model.number="autoAssignCalendarId">
              <option v-for="cal in calendarList" :key="cal.id" :value="cal.id">{{ cal.calendar_name }}</option>
            </select>
          </label>
          <label class="modal-field">
            <span>振分開始日</span>
            <input v-model="autoAssignStartDate" type="date" />
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn" :disabled="autoAssigning" @click="closeAutoAssignDialog">閉じる</button>
          <button class="btn auto-assign-btn" :disabled="autoAssigning" @click="autoAssignTrips">
            {{ autoAssigning ? '振分中...' : '実行' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showPickupPdfDialog" class="modal-overlay" @click.self="closePickupPdfDialog">
      <div class="modal-card">
        <h3 class="modal-title">集荷明細表（PDF）</h3>
        <div class="modal-fields">
          <label class="modal-field">
            <span>開始日</span>
            <input v-model="pickupPdfStartDate" type="date" />
          </label>
          <label class="modal-field">
            <span>終了日</span>
            <input v-model="pickupPdfEndDate" type="date" />
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn" :disabled="exportingPickupPdf" @click="closePickupPdfDialog">閉じる</button>
          <button class="btn pickup-btn" :disabled="exportingPickupPdf" @click="exportPickupDetailPdf">
            {{ exportingPickupPdf ? '出力中...' : 'PDF出力' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showTruckDetail" class="truck-detail-wrap">
      <table class="truck-detail-table">
        <thead>
          <tr>
            <th>便名</th>
            <th>俗称</th>
            <th>出発時刻</th>
            <th>着時刻</th>
            <th>長さ(mm)</th>
            <th>奥行き(mm)</th>
            <th>日ずれ</th>
            <th>通常便</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="truck in detailTrucks" :key="`detail-${truck.id}`">
            <td>{{ truck.name || '-' }}</td>
            <td>{{ truckDisplayName(truck) }}</td>
            <td>{{ truck.departure_time || '-' }}</td>
            <td>{{ truck.arrival_time || '-' }}</td>
            <td class="num-cell">{{ formatNumber(truck.width) }}</td>
            <td class="num-cell">{{ formatNumber(truck.depth) }}</td>
            <td class="num-cell">{{ formatNumber(truck.arrival_day_offset) }}</td>
            <td>{{ truck.default_use ? '通常' : '-' }}</td>
          </tr>
          <tr v-if="!detailTrucks.length">
            <td colspan="8" class="detail-empty">便マスタがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showPseudoProductPanel" class="pseudo-product-wrap">
      <div class="pseudo-product-toolbar">
        <span class="pseudo-product-title">擬似便対象製品</span>
        <button class="btn save-btn" :disabled="savingPseudo" @click="savePseudoProducts">
          {{ savingPseudo ? '保存中...' : '保存' }}
        </button>
      </div>
      <table class="pseudo-product-table">
        <thead>
          <tr>
            <th class="pseudo-label-col">便</th>
            <th v-for="row in pseudoProductRows" :key="`pth-${row.key}`" class="pseudo-product-col">
              <div class="pseudo-col-code">{{ row.product_code }}</div>
              <div class="pseudo-col-name">{{ productNameMap.get(row.product_code) || '' }}</div>
              <div class="pseudo-col-shipto">{{ row.ship_to_code || '-' }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pt in pseudoTrucks" :key="`ptr-${pt.id}`">
            <td class="pseudo-label-col">{{ pt.alias_name || pt.name }}</td>
            <td v-for="row in pseudoProductRows" :key="`pp-${row.key}-${pt.id}`" class="pseudo-check-cell">
              <input
                type="checkbox"
                :checked="row.truckIds.has(pt.id)"
                @change="togglePseudoTruck(row, pt.id)"
              />
            </td>
          </tr>
          <tr v-if="!pseudoProductRows.length">
            <td colspan="1" class="detail-empty">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="table-wrap" ref="tableWrapRef">
      <table class="grid">
        <thead ref="theadRef">
          <tr>
            <th rowspan="4" class="left-head code-col">品番</th>
            <th rowspan="4" class="left-head shipto-col">納入場</th>
            <th
              v-for="dateKey in dateKeys"
              :key="`day-${dateKey}`"
              :colspan="SLOT_COUNT"
              class="date-head"
              :class="{
                'holiday-head': isHoliday(dateKey),
                'day-split-left': isDaySplitStart(dateKey),
              }"
            >
              <div class="date-head-content">
                <span class="pseudo-occ pseudo-occ-left" :class="{ 'pseudo-occ-over': pseudoTruckOccupancyPercent(dateKey, 'A') > 95 }">A:{{ pseudoTruckOccupancyPercent(dateKey, 'A') }}%</span>
                <span class="date-head-label">{{ formatHeaderDate(dateKey) }}</span>
                <span class="pseudo-occ pseudo-occ-right" :class="{ 'pseudo-occ-over': pseudoTruckOccupancyPercent(dateKey, 'P') > 95 }">P:{{ pseudoTruckOccupancyPercent(dateKey, 'P') }}%</span>
              </div>
            </th>
          </tr>
          <tr>
            <template v-for="dateKey in dateKeys" :key="`truck-${dateKey}`">
              <th
                v-for="slotIdx in SLOT_COUNT"
                :key="`truck-${dateKey}-${slotIdx}`"
                :class="[
                  'truck-head',
                  slotWidthClass(slotIdx - 1),
                  {
                    'holiday-head': isHoliday(dateKey),
                    'day-split-left': slotIdx === 1 && isDaySplitStart(dateKey),
                  },
                ]"
              >
                {{ truckNameAt(dateKey, slotIdx - 1) }}
              </th>
            </template>
          </tr>
          <tr>
            <template v-for="dateKey in dateKeys" :key="`occ-${dateKey}`">
              <th
                v-for="slotIdx in SLOT_COUNT"
                :key="`occ-${dateKey}-${slotIdx}`"
                :class="[
                  'occ-head',
                  slotWidthClass(slotIdx - 1),
                  {
                    'holiday-head': isHoliday(dateKey),
                    'day-split-left': slotIdx === 1 && isDaySplitStart(dateKey),
                  },
                ]"
              >
                {{ truckOccupancyLabel(dateKey, slotIdx - 1) }}
              </th>
            </template>
          </tr>
          <tr>
            <template v-for="dateKey in dateKeys" :key="`item-${dateKey}`">
              <th
                v-for="slotIdx in SLOT_COUNT"
                :key="`item-${dateKey}-${slotIdx}`"
                :class="[
                  'item-head',
                  slotWidthClass(slotIdx - 1),
                  {
                    'holiday-head': isHoliday(dateKey),
                    'day-split-left': slotIdx === 1 && isDaySplitStart(dateKey),
                  },
                ]"
              >
                {{ slotLabels[slotIdx - 1] }}
              </th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in mergedRows" :key="row.rowKey">
            <td class="code-col">{{ row.product_code }}</td>
            <td class="shipto-col">{{ row.ship_to_code || '-' }}</td>
            <template v-for="dateKey in dateKeys" :key="`${row.rowKey}-${dateKey}`">
              <td class="cell-center cell-stacked col-order" :class="{ 'day-split-left': isDaySplitStart(dateKey) }">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-order-${slotIdx}`"
                  class="sub-cell"
                >
                  {{ sourceOrderLabel(slotEntryAt(row, dateKey, slotIdx - 1)) }}
                </div>
              </td>
              <td class="cell-right cell-stacked col-demand">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-demand-${slotIdx}`"
                  class="sub-cell"
                >
                  {{ formatNumber(slotEntryAt(row, dateKey, slotIdx - 1)?.delivery_qty) }}
                </div>
              </td>
              <td class="cell-right cell-stacked col-assigned">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-assigned-${slotIdx}`"
                  class="sub-cell"
                >
                  {{ formatNumber(assignedQty(slotEntryAt(row, dateKey, slotIdx - 1))) }}
                </div>
              </td>
              <td class="cell-select cell-stacked col-select">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-select-${slotIdx}`"
                  class="sub-cell select-subcell"
                >
                  <div v-if="slotEntryAt(row, dateKey, slotIdx - 1)" class="allocation-stack">
                    <div
                      v-for="(al, idx) in slotEntryAt(row, dateKey, slotIdx - 1).allocations"
                      :key="`${row.rowKey}-${dateKey}-${slotIdx}-al-${idx}`"
                      class="allocation-row"
                    >
                      <select v-model.number="al.truck_id" @change="handleAllocationChange(slotEntryAt(row, dateKey, slotIdx - 1))">
                        <option :value="null">便</option>
                        <option
                          v-for="truck in trucksByDate[dateKey] || []"
                          :key="truck.id"
                          :value="truck.id"
                        >
                          {{ truckDisplayName(truck) }}
                        </option>
                      </select>
                      <input
                        v-model="al.qty"
                        type="text"
                        inputmode="numeric"
                        @input="handleAllocationQtyInput(slotEntryAt(row, dateKey, slotIdx - 1))"
                        @focus="showProductBubble(row, $event)"
                        @mouseenter="showProductBubble(row, $event)"
                        @blur="handleQtyInputBlur"
                        @mouseleave="handleQtyInputMouseLeave($event)"
                      />
                      <button class="mini" @click="addAllocation(slotEntryAt(row, dateKey, slotIdx - 1))">+</button>
                      <button
                        class="mini danger"
                        :disabled="slotEntryAt(row, dateKey, slotIdx - 1).allocations.length <= 1"
                        @click="removeAllocation(slotEntryAt(row, dateKey, slotIdx - 1), idx)"
                      >
                        -
                      </button>
                    </div>
                  </div>
                </div>
              </td>
              <td class="cell-right cell-stacked col-remain">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-remain-${slotIdx}`"
                  class="sub-cell"
                  :class="{ 'remain-negative': parseNumber(slotEntryAt(row, dateKey, slotIdx - 1)?.unassigned_qty_preview) > 0 }"
                >
                  {{ formatNumber(slotEntryAt(row, dateKey, slotIdx - 1)?.unassigned_qty_preview) }}
                </div>
              </td>
            </template>
          </tr>
          <tr v-if="!mergedRows.length">
            <td :colspan="2 + dateKeys.length * SLOT_COUNT" class="empty">データがありません</td>
          </tr>
          <tr v-else class="daily-load-row">
            <td class="code-col daily-load-label">積み荷明細</td>
            <td class="shipto-col daily-load-label"></td>
            <template v-for="dateKey in dateKeys" :key="`daily-load-${dateKey}`">
              <td class="daily-load-cell" :colspan="SLOT_COUNT" :class="{ 'day-split-left': isDaySplitStart(dateKey) }">
                <div v-if="(loadBlocksByDate[dateKey] || []).length" class="daily-load-blocks">
                  <table class="daily-load-table">
                    <tbody>
                      <template v-for="(block, blockIdx) in loadBlocksByDate[dateKey]" :key="`${dateKey}-block-${blockIdx}`">
                        <tr v-for="(line, lineIdx) in block.lines" :key="`${dateKey}-line-${blockIdx}-${lineIdx}`">
                          <td v-if="lineIdx === 0" class="daily-load-truck" :rowspan="block.lines.length">{{ block.truckLabel }}</td>
                          <td class="daily-load-product">{{ line[0] ? `${line[0].productCode}×${formatNumber(line[0].qty)}` : '' }}</td>
                          <td class="daily-load-product">{{ line[1] ? `${line[1].productCode}×${formatNumber(line[1].qty)}` : '' }}</td>
                        </tr>
                      </template>
                    </tbody>
                  </table>
                </div>
                <div v-else class="daily-load-empty">-</div>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="note">未割付期限: 調整後納期の{{ assignmentDeadlineDays }}営業日前</div>
    <div
      v-if="cursorProductCode"
      class="cursor-product-bubble"
      :style="cursorProductBubbleStyle"
    >{{ cursorProductCode }}</div>

    <!-- データソースモーダル -->
    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header"><h3>データソース</h3><button class="ds-close" @click="showDataSource = false">&times;</button></div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr><td>便割付 読み書き</td><td>t_kubota_sakai_trip_assignment</td><td>納期調整→便への割付データ</td></tr>
            <tr><td>納期調整 読み取り</td><td>t_kubota_sakai_due_adjustment</td><td>出荷数(delivery_qty)の参照元</td></tr>
            <tr><td>便マスタ 読み取り</td><td>m_kubota_sakai_truck</td><td>便名・積載量</td></tr>
            <tr><td>擬似便製品 読み書き</td><td>m_kubota_sakai_pseudo_truck_product</td><td>擬似便自動振分の製品マスタ</td></tr>
            <tr><td>お気に入り 読み書き</td><td>user_favorite</td><td>画面フィルタのお気に入り保存</td></tr>
            <tr><td>カレンダー 読み取り</td><td>m_calendar / m_calendar_day</td><td>営業日判定</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import api from '@/api/client'

const showDataSource = ref(false)
const theadRef = ref(null)
const tableWrapRef = ref(null)

const setStickyTopValues = () => {
  if (!theadRef.value) return
  const rows = theadRef.value.querySelectorAll('tr')
  let cumTop = 0
  rows.forEach((tr) => {
    const cells = tr.querySelectorAll('th')
    cells.forEach((th) => {
      if (!th.hasAttribute('rowspan')) {
        th.style.top = `${cumTop}px`
      }
    })
    cumTop += tr.offsetHeight
  })
  const rowspanCells = theadRef.value.querySelectorAll('th[rowspan]')
  rowspanCells.forEach((th) => { th.style.top = '0px' })
}

const SLOT_COUNT = 5
const slotLabels = ['注番', '需要', '振分', '便選択', '残']

const formatLocalDate = (date) => {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const addDays = (baseDate, days) => {
  const d = new Date(`${baseDate}T00:00:00`)
  d.setDate(d.getDate() + days)
  return formatLocalDate(d)
}

const formatHeaderDate = (dateText) => {
  const d = new Date(`${dateText}T00:00:00`)
  const w = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()]
  return `${d.getMonth() + 1}/${d.getDate()}(${w})`
}

const formatAdjDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const parseNumber = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const num = Number(String(value).replace(/,/g, ''))
  return Number.isFinite(num) ? num : 0
}

const formatNumber = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return ''
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const parseIntegerQty = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const normalized = String(value).replace(/[，,]/g, '').replace(/[．]/g, '.')
  const num = Number(normalized)
  return Number.isFinite(num) ? Math.max(0, Math.trunc(num)) : 0
}

const normalizeQtyText = (value) => {
  const qty = parseIntegerQty(value)
  return qty > 0 ? String(qty) : ''
}

const normalizeAllocation = (item = null) => ({
  truck_id: item?.truck_id ?? null,
  qty: normalizeQtyText(item?.qty ?? ''),
})

const sortEntries = (items = []) => {
  return [...items].sort((a, b) => {
    const aFc = a.order_type === 'FORECAST' ? 1 : 0
    const bFc = b.order_type === 'FORECAST' ? 1 : 0
    if (aFc !== bFc) return aFc - bFc
    return String(a.source_order_no || '').localeCompare(String(b.source_order_no || ''))
  })
}

const targetDate = ref(formatLocalDate(new Date()))
const horizonDays = ref(5)
const keyword = ref('')
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')
const FAVORITE_SCREEN_KEY = 'shipping.kubota_sakai_trip_planning'
const loading = ref(false)
const importing = ref(false)
const saving = ref(false)
const lastAdjustedAt = ref(null)
const exportingCsv = ref(false)
const exportingPickupPdf = ref(false)
const assignmentDeadlineDays = ref(3)
const trucksByDate = ref({})
const summaryByDate = ref({})
const previewSummaryByDate = ref({})
const mergedRows = ref([])
const previewTimers = new Map()
const showTruckDetail = ref(false)
const showPseudoProductPanel = ref(false)
const pseudoTrucks = ref([])
const pseudoProductRows = ref([])
const savingPseudo = ref(false)
const autoAssigning = ref(false)
const showAutoAssignDialog = ref(false)
const calendarList = ref([])
const autoAssignCalendarId = ref(null)
const autoAssignStartDate = ref('')
const calendarDayMap = ref({})
const productNameMap = ref(new Map())
const showPickupPdfDialog = ref(false)
const pickupPdfStartDate = ref('')
const pickupPdfEndDate = ref('')
const holidayByDate = ref({})
const cursorProductCode = ref('')
const cursorProductBubbleStyle = ref({})

const dateKeys = computed(() => {
  const span = Math.max(1, Number(horizonDays.value) || 1)
  return Array.from({ length: span }).map((_, idx) => addDays(targetDate.value, idx))
})

const detailTrucks = computed(() => {
  const firstDate = dateKeys.value[0]
  const base = trucksByDate.value[firstDate] || []
  if (base.length > 0) return base
  const merged = []
  const seen = new Set()
  Object.values(trucksByDate.value || {}).forEach((list) => {
    ;(list || []).forEach((truck) => {
      const key = Number(truck.id)
      if (seen.has(key)) return
      seen.add(key)
      merged.push(truck)
    })
  })
  return merged
})

const isHoliday = (dateKey) => Boolean(holidayByDate.value[dateKey])
const isDaySplitStart = (dateKey) => dateKeys.value[0] !== dateKey
const pseudoTruckMarkers = {
  A: new Set(['A', 'A便', 'Ａ', 'Ａ便']),
  P: new Set(['P', 'P便', 'Ｐ', 'Ｐ便']),
}
const normalizeTruckMarker = (truck) => String(truck?.alias_name || truck?.name || '').trim().toUpperCase()
const isPseudoTruckType = (truck, type) => {
  const marker = normalizeTruckMarker(truck)
  const base = marker.replace(/\s+/g, '')
  if (type === 'A') return pseudoTruckMarkers.A.has(base)
  if (type === 'P') return pseudoTruckMarkers.P.has(base)
  return false
}
const isPseudoTruck = (truck) => isPseudoTruckType(truck, 'A') || isPseudoTruckType(truck, 'P')
const displayTrucksForDate = (dateKey) => (trucksByDate.value[dateKey] || []).filter((truck) => !isPseudoTruck(truck))
const slotWidthClass = (slotIdx) => {
  if (slotIdx === 0) return 'col-order'
  if (slotIdx === 1) return 'col-demand'
  if (slotIdx === 2) return 'col-assigned'
  if (slotIdx === 3) return 'col-select'
  return 'col-remain'
}

const sourceOrderLabel = (entry) => {
  if (!entry) return ''
  return entry.source_order_no || (entry.order_type === 'FORECAST' ? '内示' : '')
}

const assignedQty = (entry) => {
  if (!entry) return 0
  return entry.allocations.reduce((sum, al) => sum + parseIntegerQty(al.qty), 0)
}

const recalcEntry = (entry) => {
  if (!entry) return
  const assigned = assignedQty(entry)
  entry.unassigned_qty_preview = Number((parseNumber(entry.delivery_qty) - assigned).toFixed(3))
}

const handleAllocationChange = (entry) => {
  recalcEntry(entry)
  if (entry?.due_date) schedulePreview(entry.due_date)
}

const handleAllocationQtyInput = (entry) => {
  if (entry?.allocations?.length) {
    entry.allocations.forEach((al) => {
      al.qty = normalizeQtyText(al.qty)
    })
  }
  recalcEntry(entry)
  if (entry?.due_date) schedulePreview(entry.due_date)
}

const addAllocation = (entry) => {
  if (!entry) return
  entry.allocations.push(normalizeAllocation())
  if (entry.due_date) schedulePreview(entry.due_date)
}

const removeAllocation = (entry, idx) => {
  if (!entry || entry.allocations.length <= 1) return
  entry.allocations.splice(idx, 1)
  recalcEntry(entry)
  if (entry.due_date) schedulePreview(entry.due_date)
}

const entriesAt = (row, dateKey) => row.byDate?.[dateKey] || []
const slotEntryAt = (row, dateKey, slotIdx) => entriesAt(row, dateKey)[slotIdx] || null

const truckAt = (dateKey, slotIdx) => {
  const trucks = displayTrucksForDate(dateKey)
  return trucks[slotIdx] || null
}

const truckDisplayName = (truck) => {
  if (!truck) return ''
  return (truck.alias_name || '').trim() || truck.name || ''
}

const loadDetailTruckLabel = (truck) => {
  const base = truckDisplayName(truck) || truck?.name || ''
  if (!base) return '便'
  return base.includes('便') ? base : `便 ${base}`
}

const truckNameAt = (dateKey, slotIdx) => {
  const truck = truckAt(dateKey, slotIdx)
  return truckDisplayName(truck) || `便${slotIdx + 1}`
}

const truckOccupancyPercent = (dateKey, slotIdx) => {
  const truck = truckAt(dateKey, slotIdx)
  if (!truck) return 0
  const previewSummary = (previewSummaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === Number(truck.id))
  if (previewSummary) return parseNumber(previewSummary.occupancy_percent)
  const savedSummary = (summaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === Number(truck.id))
  return parseNumber(savedSummary?.occupancy_percent)
}

const truckOccupancyLabel = (dateKey, slotIdx) => `${truckOccupancyPercent(dateKey, slotIdx)}%`
const pseudoTruckOccupancyPercent = (dateKey, type) => {
  const pseudoTruck = (trucksByDate.value[dateKey] || []).find((truck) => isPseudoTruckType(truck, type))
  if (!pseudoTruck) return 0
  const previewSummary = (previewSummaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === Number(pseudoTruck.id))
  if (previewSummary) return parseNumber(previewSummary.occupancy_percent)
  const savedSummary = (summaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === Number(pseudoTruck.id))
  return parseNumber(savedSummary?.occupancy_percent)
}

const loadBlocksByDate = computed(() => {
  const result = {}
  dateKeys.value.forEach((dateKey) => {
    const truckMap = new Map((trucksByDate.value[dateKey] || []).map((truck) => [Number(truck.id), truck]))
    const qtyMap = new Map()
    mergedRows.value.forEach((row) => {
      const entries = entriesAt(row, dateKey)
      entries.forEach((entry) => {
        ;(entry.allocations || []).forEach((allocation) => {
          const truckId = Number(allocation.truck_id)
          const qty = parseIntegerQty(allocation.qty)
          if (!truckId || qty <= 0) return
          const key = `${truckId}||${row.product_code}`
          qtyMap.set(key, (qtyMap.get(key) || 0) + qty)
        })
      })
    })
    const items = [...qtyMap.entries()]
      .map(([key, qty]) => {
        const [truckIdText, productCode] = key.split('||')
        const truckId = Number(truckIdText)
        const truck = truckMap.get(truckId)
        return {
          truckId,
          truckLabel: loadDetailTruckLabel(truck),
          productCode,
          qty,
        }
      })
      .sort((a, b) => {
        if (a.truckId !== b.truckId) return a.truckId - b.truckId
        return String(a.productCode).localeCompare(String(b.productCode))
      })
    const blocks = []
    let currentTruckId = null
    items.forEach((item) => {
      if (item.truckId !== currentTruckId) {
        currentTruckId = item.truckId
        blocks.push({
          truckId: item.truckId,
          truckLabel: item.truckLabel,
          products: [],
        })
      }
      blocks[blocks.length - 1].products.push({
        productCode: item.productCode,
        qty: item.qty,
      })
    })
    result[dateKey] = blocks.map((block) => {
      const lines = []
      for (let idx = 0; idx < block.products.length; idx += 2) {
        lines.push(block.products.slice(idx, idx + 2))
      }
      return {
        truckId: block.truckId,
        truckLabel: block.truckLabel,
        lines: lines.length ? lines : [[]],
      }
    })
  })
  return result
})

const buildPayloadRowsForDate = (dateKey) => {
  return mergedRows.value
    .flatMap((row) => entriesAt(row, dateKey))
    .map((entry) => ({
      due_adjustment_id: entry.due_adjustment_id,
      allocations: entry.allocations
        .map((item) => ({
          truck_id: item.truck_id,
          qty: parseIntegerQty(item.qty),
        }))
        .filter((item) => item.truck_id && item.qty > 0),
    }))
}

const previewLoadForDate = async (dateKey) => {
  const payloadRows = buildPayloadRowsForDate(dateKey)
  try {
    const res = await api.kubotaSakaiTripAssignments.previewLoad(dateKey, payloadRows)
    const summaries = Array.isArray(res.data?.truck_summaries) ? res.data.truck_summaries : []
    previewSummaryByDate.value = {
      ...previewSummaryByDate.value,
      [dateKey]: summaries,
    }
  } catch (error) {
    console.warn('便占有率プレビュー取得失敗', error)
  }
}

const schedulePreview = (dateKey) => {
  if (!dateKey) return
  const prev = previewTimers.get(dateKey)
  if (prev) clearTimeout(prev)
  const timer = setTimeout(() => {
    previewLoadForDate(dateKey)
    previewTimers.delete(dateKey)
  }, 250)
  previewTimers.set(dateKey, timer)
}

const showProductBubble = (row, event) => {
  cursorProductCode.value = String(row?.product_code || '')
  const rect = event?.target?.getBoundingClientRect?.()
  if (!rect) return
  const left = Math.round(rect.left + rect.width / 2)
  const top = Math.round(rect.top - 8)
  cursorProductBubbleStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    transform: 'translate(-50%, -100%)',
  }
}

const hideProductBubble = () => {
  cursorProductCode.value = ''
  cursorProductBubbleStyle.value = {}
}

const handleQtyInputBlur = () => {
  window.setTimeout(() => {
    const root = tableWrapRef.value
    const active = document.activeElement
    if (!root || !active || !root.contains(active)) {
      hideProductBubble()
    }
  }, 0)
}

const handleQtyInputMouseLeave = (event) => {
  if (document.activeElement !== event?.target) {
    hideProductBubble()
  }
}

const refreshAllPreview = async () => {
  await Promise.all(dateKeys.value.map((dateKey) => previewLoadForDate(dateKey)))
}

const loadGrid = async () => {
  loading.value = true
  try {
    const responses = await Promise.all(
      dateKeys.value.map((dateKey) => api.kubotaSakaiTripAssignments.grid({
        target_date: dateKey,
        keyword: keyword.value,
      })),
    )
    const nextTrucksByDate = {}
    const nextSummaryByDate = {}
    const nextHolidayByDate = {}
    const map = new Map()
    let maxDeadline = 3

    responses.forEach((res, idx) => {
      const dateKey = dateKeys.value[idx]
      const trucks = Array.isArray(res.data?.trucks) ? res.data.trucks : []
      const summaries = Array.isArray(res.data?.truck_summaries) ? res.data.truck_summaries : []
      const payloadRows = Array.isArray(res.data?.rows) ? res.data.rows : []
      nextTrucksByDate[dateKey] = trucks
      nextSummaryByDate[dateKey] = summaries
      nextHolidayByDate[dateKey] = Boolean(res.data?.is_holiday)
      maxDeadline = Math.max(maxDeadline, Number(res.data?.assignment_deadline_days || 3))
      if (res.data?.last_adjusted_at) lastAdjustedAt.value = res.data.last_adjusted_at

      payloadRows.forEach((raw) => {
        if (raw.product_code && raw.product_name) {
          productNameMap.value.set(raw.product_code, raw.product_name)
        }
        const key = `${raw.product_code}||${raw.ship_to_code || ''}`
        if (!map.has(key)) {
          map.set(key, {
            rowKey: key,
            product_code: raw.product_code,
            ship_to_code: raw.ship_to_code || '',
            byDate: {},
            maxSlots: 1,
          })
        }
        const allocations = Array.isArray(raw.allocations) && raw.allocations.length
          ? raw.allocations.map((a) => normalizeAllocation(a))
          : [normalizeAllocation()]
        const entry = {
          due_adjustment_id: raw.due_adjustment_id,
          source_order_no: raw.source_order_no || '',
          order_type: raw.order_type || '',
          delivery_qty: parseNumber(raw.delivery_qty),
          overdue: Boolean(raw.overdue),
          allocations,
          unassigned_qty_preview: parseNumber(raw.unassigned_qty),
          due_date: dateKey,
        }
        recalcEntry(entry)
        if (!map.get(key).byDate[dateKey]) {
          map.get(key).byDate[dateKey] = []
        }
        map.get(key).byDate[dateKey].push(entry)
      })
    })

    const rows = [...map.values()]
    rows.forEach((row) => {
      let maxSlots = 1
      dateKeys.value.forEach((dateKey) => {
        row.byDate[dateKey] = sortEntries(row.byDate[dateKey] || [])
        maxSlots = Math.max(maxSlots, row.byDate[dateKey].length || 0)
      })
      row.maxSlots = maxSlots || 1
    })

    trucksByDate.value = nextTrucksByDate
    summaryByDate.value = nextSummaryByDate
    holidayByDate.value = nextHolidayByDate
    previewSummaryByDate.value = {}
    assignmentDeadlineDays.value = maxDeadline
    mergedRows.value = rows.sort((a, b) => {
      const codeCmp = String(a.product_code).localeCompare(String(b.product_code))
      if (codeCmp !== 0) return codeCmp
      return String(a.ship_to_code).localeCompare(String(b.ship_to_code))
    })
    await refreshAllPreview()
    nextTick(setStickyTopValues)
  } catch (error) {
    const message = error?.response?.data?.detail || 'データ取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const importOrders = async () => {
  if (importing.value || loading.value) return
  importing.value = true
  try {
    const res = await api.kubotaSakaiDueAdjustments.importOrders({
      start_date: targetDate.value,
      horizon_days: horizonDays.value,
    })
    const d = res.data || {}
    alert(`取込完了: 新規${d.created || 0}件, 更新${d.updated || 0}件, 内示→確定削除${d.deleted_forecast || 0}件`)
    await loadGrid()
  } catch (error) {
    const message = error?.response?.data?.detail || '取込に失敗しました。'
    alert(message)
  } finally {
    importing.value = false
  }
}

const csvEscape = (value) => {
  const text = value == null ? '' : String(value)
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

const exportLoadDetailCsv = async () => {
  exportingCsv.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.loadDetail(targetDate.value)
    const rows = Array.isArray(res.data?.rows) ? res.data.rows : []
    if (!rows.length) {
      alert('対象日の便割付データがありません。')
      return
    }

    const header = ['便', '便面積', '製品', '数量', '容器名', '容器', '使用容器数', '使用容器面積', '占有']
    const lines = [header.join(',')]
    rows.forEach((row) => {
      const truckLabel = row.truck_alias_name
        ? `${row.truck_alias_name} (${row.truck_name})`
        : row.truck_name
      const record = [
        truckLabel,
        row.truck_area,
        row.product_code,
        row.qty,
        row.container_name || '-',
        row.container_size || '-',
        row.container_count,
        row.used_container_area,
        `${row.occupancy_percent}%`,
      ]
      lines.push(record.map(csvEscape).join(','))
    })

    const csv = `\uFEFF${lines.join('\r\n')}`
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `便占有明細_${targetDate.value}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    const message = error?.response?.data?.detail || 'CSV出力に失敗しました。'
    alert(message)
  } finally {
    exportingCsv.value = false
  }
}

const openPickupPdfDialog = () => {
  showPickupPdfDialog.value = true
  pickupPdfStartDate.value = targetDate.value
  pickupPdfEndDate.value = addDays(targetDate.value, Math.max(0, Number(horizonDays.value || 1) - 1))
}

const closePickupPdfDialog = () => {
  if (exportingPickupPdf.value) return
  showPickupPdfDialog.value = false
}

const exportPickupDetailPdf = async () => {
  const startDate = pickupPdfStartDate.value
  const endDate = pickupPdfEndDate.value
  if (!startDate || !endDate) {
    alert('開始日と終了日を指定してください。')
    return
  }
  if (startDate > endDate) {
    alert('開始日は終了日以前を指定してください。')
    return
  }
  exportingPickupPdf.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.pickupDetailPdf(startDate, endDate)
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `クボタ堺_集荷明細表_${startDate}_${endDate}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    showPickupPdfDialog.value = false
  } catch (error) {
    const data = error?.response?.data
    if (data instanceof Blob) {
      alert('PDF出力に失敗しました。')
      return
    }
    const message = data?.detail || data?.error || 'PDF出力に失敗しました。'
    alert(message)
  } finally {
    exportingPickupPdf.value = false
  }
}

const save = async () => {
  const validation = validateBeforeSave()
  if (!validation.ok) {
    const proceed = window.confirm(`${validation.message}\n\nこのまま保存しますか？`)
    if (!proceed) return
  }
  saving.value = true
  try {
    for (const dateKey of dateKeys.value) {
      const payloadRows = mergedRows.value
        .flatMap((row) => entriesAt(row, dateKey))
        .map((entry) => ({
          due_adjustment_id: entry.due_adjustment_id,
          allocations: entry.allocations
            .map((item) => ({
              truck_id: item.truck_id,
              qty: parseIntegerQty(item.qty),
            }))
            .filter((item) => item.truck_id && item.qty > 0),
        }))
      await api.kubotaSakaiTripAssignments.bulkSave(dateKey, payloadRows)
    }
    await loadGrid()
    alert('保存しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '保存に失敗しました。'
    const errors = error?.response?.data?.errors
    if (Array.isArray(errors) && errors.length > 0) {
      const lines = errors.map((item) => {
        if (item.truck_name) return `${item.truck_name}: ${(item.errors || []).join(', ')}`
        if (item.due_adjustment_id) return `${item.detail || '入力エラー'}`
        return JSON.stringify(item)
      })
      alert([detail, ...lines].join('\n'))
    } else {
      alert(detail)
    }
  } finally {
    saving.value = false
  }
}

const validateBeforeSave = () => {
  let missingTruckCount = 0
  let unassignedQtyCount = 0
  const overloaded = []
  const overloadedSet = new Set()

  for (const dateKey of dateKeys.value) {
    const previewList = previewSummaryByDate.value[dateKey] || summaryByDate.value[dateKey] || []
    for (const row of mergedRows.value) {
      for (const entry of entriesAt(row, dateKey)) {
        const deliveryQty = parseIntegerQty(entry?.delivery_qty)
        if (deliveryQty <= 0) continue
        const validAllocations = (entry.allocations || []).filter(
          (item) => item?.truck_id && parseIntegerQty(item?.qty) > 0,
        )
        if (!validAllocations.length) missingTruckCount += 1

        const unassigned = parseNumber(entry?.unassigned_qty_preview)
        if (unassigned > 0) unassignedQtyCount += 1
      }
    }

    for (const item of previewList) {
      const occ = parseNumber(item?.occupancy_percent)
      if (occ > 95) {
        const key = `${dateKey}-${item?.truck_id}`
        if (overloadedSet.has(key)) continue
        overloadedSet.add(key)
        overloaded.push(`${dateKey} ${item?.truck_name || '便'} ${formatNumber(occ)}%`)
      }
    }
  }

  if (!missingTruckCount && !unassignedQtyCount && !overloaded.length) {
    return { ok: true, message: '' }
  }

  const lines = ['保存前チェックで注意点があります。']
  if (missingTruckCount) lines.push(`・便未選択: ${missingTruckCount}件`)
  if (unassignedQtyCount) lines.push(`・未割付残あり: ${unassignedQtyCount}件`)
  if (overloaded.length) lines.push(`・便占有率95%超: ${overloaded.join(' / ')}`)
  return { ok: false, message: lines.join('\n') }
}

// ---- 擬似便対象製品 ----

const togglePseudoProductPanel = async () => {
  showPseudoProductPanel.value = !showPseudoProductPanel.value
  if (showPseudoProductPanel.value) {
    await loadPseudoProducts()
  }
}

const loadPseudoProducts = async () => {
  try {
    const res = await api.kubotaSakaiTripAssignments.getPseudoTruckProducts()
    pseudoTrucks.value = res.data?.pseudo_trucks || []
    const mappings = res.data?.mappings || []
    const mappingMap = new Map()
    mappings.forEach((m) => {
      const key = `${m.product_code}||${m.ship_to_code || ''}`
      mappingMap.set(key, new Set((m.trucks || []).map((t) => Number(t.truck_id))))
    })
    const gridKeys = new Set()
    mergedRows.value.forEach((row) => {
      gridKeys.add(`${row.product_code}||${row.ship_to_code || ''}`)
    })
    pseudoProductRows.value = [...gridKeys].sort().map((key) => {
      const [productCode, shipToCode] = key.split('||', 2)
      return {
        key,
        product_code: productCode,
        ship_to_code: shipToCode,
        truckIds: mappingMap.get(key) || new Set(),
      }
    })
  } catch (error) {
    alert('擬似便対象製品の取得に失敗しました。')
  }
}

const togglePseudoTruck = (row, truckId) => {
  if (row.truckIds.has(truckId)) {
    row.truckIds.delete(truckId)
  } else {
    row.truckIds.add(truckId)
  }
}

const savePseudoProducts = async () => {
  savingPseudo.value = true
  try {
    const rows = pseudoProductRows.value.map((row) => ({
      product_code: row.product_code,
      ship_to_code: row.ship_to_code || '',
      truck_ids: [...row.truckIds],
    }))
    await api.kubotaSakaiTripAssignments.savePseudoTruckProducts(rows)
    alert('擬似便対象製品を保存しました。')
  } catch (error) {
    alert('保存に失敗しました。')
  } finally {
    savingPseudo.value = false
  }
}

// ---- 自動便振分 ----

const isWorkingDayByCalendar = (dateKey) => {
  if (dateKey in calendarDayMap.value) return calendarDayMap.value[dateKey]
  const d = new Date(`${dateKey}T00:00:00`)
  return d.getDay() !== 0 && d.getDay() !== 6
}

const addBusinessDaysByCalendar = (baseDateStr, days) => {
  let current = new Date(`${baseDateStr}T00:00:00`)
  let remaining = days
  while (remaining > 0) {
    current.setDate(current.getDate() + 1)
    if (isWorkingDayByCalendar(formatLocalDate(current))) remaining--
  }
  return formatLocalDate(current)
}

const openAutoAssignDialog = async () => {
  try {
    if (!calendarList.value.length) {
      const res = await api.calendars.getCalendars()
      calendarList.value = (res.data?.results || res.data || []).sort((a, b) =>
        String(a.calendar_name).localeCompare(String(b.calendar_name)),
      )
    }
    if (!autoAssignCalendarId.value && calendarList.value.length) {
      const kubota = calendarList.value.find(
        (c) => /kubota|kobota|クボタ/.test(`${c.calendar_code}${c.calendar_name}`),
      )
      autoAssignCalendarId.value = kubota ? kubota.id : calendarList.value[0].id
    }
    await loadCalendarDays()
    autoAssignStartDate.value = addBusinessDaysByCalendar(formatLocalDate(new Date()), 4)
    showAutoAssignDialog.value = true
  } catch (error) {
    alert('カレンダー情報の取得に失敗しました。')
  }
}

const closeAutoAssignDialog = () => {
  if (autoAssigning.value) return
  showAutoAssignDialog.value = false
}

const loadCalendarDays = async () => {
  if (!autoAssignCalendarId.value) return
  const res = await api.calendars.getCalendarDays(autoAssignCalendarId.value, { page_size: 9999 })
  const days = res.data?.results || res.data || []
  const map = {}
  days.forEach((d) => { map[d.target_date] = Boolean(d.is_working_day) })
  calendarDayMap.value = map
}

watch(autoAssignCalendarId, async (newVal) => {
  if (newVal && showAutoAssignDialog.value) {
    await loadCalendarDays()
    autoAssignStartDate.value = addBusinessDaysByCalendar(formatLocalDate(new Date()), 4)
  }
})

const autoAssignTrips = async () => {
  autoAssigning.value = true
  try {
    let pseudoData = pseudoProductRows.value
    if (!pseudoData.length || !pseudoTrucks.value.length) {
      const res = await api.kubotaSakaiTripAssignments.getPseudoTruckProducts()
      pseudoTrucks.value = res.data?.pseudo_trucks || []
      const mappings = res.data?.mappings || []
      pseudoData = mappings.map((m) => ({
        key: `${m.product_code}||${m.ship_to_code || ''}`,
        product_code: m.product_code,
        ship_to_code: m.ship_to_code || '',
        truckIds: new Set((m.trucks || []).map((t) => Number(t.truck_id))),
      }))
    }

    const pseudoMap = new Map()
    pseudoData.forEach((row) => {
      if (row.truckIds.size > 0) {
        pseudoMap.set(`${row.product_code}||${row.ship_to_code || ''}`, row.truckIds)
      }
    })

    const thresholdDate = autoAssignStartDate.value || formatLocalDate(new Date())

    const skippedProducts = new Set()
    let assignedCount = 0

    const pseudoTruckA = pseudoTrucks.value.find((t) => {
      const marker = (t.alias_name || t.name || '').trim().toUpperCase().replace(/\s+/g, '')
      return ['A', 'A便', 'Ａ', 'Ａ便'].includes(marker)
    })
    const pseudoTruckP = pseudoTrucks.value.find((t) => {
      const marker = (t.alias_name || t.name || '').trim().toUpperCase().replace(/\s+/g, '')
      return ['P', 'P便', 'Ｐ', 'Ｐ便'].includes(marker)
    })

    if (!pseudoTruckA && !pseudoTruckP) {
      alert('擬似便（A便/P便）がトラックマスタに登録されていません。')
      return
    }

    const getOccupancy = (dateKey, truckId) => {
      const preview = (previewSummaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === Number(truckId))
      if (preview) return parseNumber(preview.occupancy_percent)
      const saved = (summaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === Number(truckId))
      return parseNumber(saved?.occupancy_percent)
    }

    const targetDateKeys = dateKeys.value.filter((dk) => dk >= thresholdDate)

    const assignEntry = (entry, truck) => {
      const qty = parseIntegerQty(entry.delivery_qty)
      entry.allocations = [{ truck_id: truck.id, qty: String(qty) }]
      recalcEntry(entry)
      assignedCount++
    }

    const classifyEntry = (row, entry) => {
      if (parseNumber(entry.delivery_qty) <= 0) return null
      if (entry.allocations.some((al) => al.truck_id && parseIntegerQty(al.qty) > 0)) return null

      const lookupKey = `${row.product_code}||${row.ship_to_code || ''}`
      const truckIds = pseudoMap.get(lookupKey)
      if (!truckIds) { skippedProducts.add(`${row.product_code}(${row.ship_to_code || '-'})`); return null }

      const hasA = pseudoTruckA && truckIds.has(pseudoTruckA.id)
      const hasP = pseudoTruckP && truckIds.has(pseudoTruckP.id)
      if (!hasA && !hasP) { skippedProducts.add(row.product_code); return null }

      if (hasA && hasP) return 'both'
      if (hasA) return 'A_only'
      return 'P_only'
    }

    // Phase 1: 単独製品を割当（A-only→A, P-only→P）
    for (const dateKey of targetDateKeys) {
      for (const row of mergedRows.value) {
        for (const entry of entriesAt(row, dateKey)) {
          const type = classifyEntry(row, entry)
          if (type === 'A_only') assignEntry(entry, pseudoTruckA)
          else if (type === 'P_only') assignEntry(entry, pseudoTruckP)
        }
      }
    }

    // プレビュー更新 → A便の占有率を取得
    await Promise.all(targetDateKeys.map((dk) => previewLoadForDate(dk)))

    // Phase 2: A+P両方の製品 → Aに1つずつ積んで95%超えたらPに戻す
    for (const dateKey of targetDateKeys) {
      const bothEntries = []
      for (const row of mergedRows.value) {
        for (const entry of entriesAt(row, dateKey)) {
          if (classifyEntry(row, entry) === 'both') bothEntries.push(entry)
        }
      }
      if (!bothEntries.length) continue

      let aFull = false
      for (const entry of bothEntries) {
        if (aFull) {
          assignEntry(entry, pseudoTruckP)
          continue
        }
        // まずAに積んでみる
        assignEntry(entry, pseudoTruckA)
        await previewLoadForDate(dateKey)
        if (getOccupancy(dateKey, pseudoTruckA.id) >= 95) {
          // 超えた → この製品をPに戻す
          entry.allocations = [{ truck_id: pseudoTruckP.id, qty: String(parseIntegerQty(entry.delivery_qty)) }]
          recalcEntry(entry)
          aFull = true
        }
      }
    }

    await Promise.all(targetDateKeys.map((dk) => previewLoadForDate(dk)))

    let message = `自動振分完了: ${assignedCount}件割当`
    if (skippedProducts.size > 0) {
      message += `\n\n未設定のためスキップした製品:\n${[...skippedProducts].sort().join(', ')}`
    }
    showAutoAssignDialog.value = false
    alert(message)
  } catch (error) {
    alert('自動振分に失敗しました。')
  } finally {
    autoAssigning.value = false
  }
}

const toFavoritePayload = () => ({
  targetDate: String(targetDate.value || ''),
  horizonDays: Number(horizonDays.value || 5),
  keyword: String(keyword.value || ''),
})

const applyFavoritePayload = (payload) => {
  targetDate.value = String(payload?.targetDate || formatLocalDate(new Date()))
  const nextHorizon = Number(payload?.horizonDays || 5)
  horizonDays.value = [5, 14, 31, 60, 90].includes(nextHorizon) ? nextHorizon : 5
  keyword.value = String(payload?.keyword || '')
}

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得失敗:', e)
  }
}

const applyFavorite = () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  applyFavoritePayload(target.payload || {})
}

const saveFavorite = async () => {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    alert('お気に入り名を入力してください。')
    return
  }
  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    if (id) {
      await api.accounts.updateFavorite(id, payload)
    } else {
      await api.accounts.createFavorite(payload)
    }
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    alert('お気に入りを保存しました。')
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '保存に失敗しました。'
    alert(`お気に入り保存エラー: ${detail}`)
  }
}

onMounted(async () => {
  await loadFavorites()
  await loadGrid()
  await nextTick()
  setStickyTopValues()
})

onUnmounted(() => {
  previewTimers.forEach((timerId) => clearTimeout(timerId))
  previewTimers.clear()
  hideProductBubble()
})
</script>

<style scoped>
.trip-planning-page {
  padding: 8px;
  background: #eef2f6;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field label {
  font-size: 12px;
  color: #374151;
}
.field input {
  min-width: 140px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.field select {
  min-width: 90px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.search-field input {
  min-width: 220px;
}
.btn {
  padding: 6px 12px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.save-btn {
  background: #dff3e6;
  border-color: #8fc8a1;
}
.import-btn {
  background: #dbe8ff;
  border-color: #8daed6;
}
.detail-btn {
  background: #f7f7f7;
}
.pseudo-product-btn {
  background: #fef9c3;
  border-color: #d4a017;
}
.auto-assign-btn {
  background: #e0e7ff;
  border-color: #6366f1;
}
.favorite-btn {
  background: #facc15;
  border-color: #eab308;
  color: #78350f;
  font-weight: 700;
  min-width: 34px;
}
.adj-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: #e0f2fe;
  border: 1px solid #38bdf8;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #0369a1;
  white-space: nowrap;
}
.pickup-btn {
  background: #eefcf5;
  border-color: #80c79c;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-card {
  width: min(420px, calc(100vw - 32px));
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.18);
}
.modal-title {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}
.modal-fields {
  display: flex;
  gap: 8px;
}
.modal-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  font-size: 12px;
  color: #374151;
}
.modal-field input {
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.truck-detail-wrap {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 6px;
}
.truck-detail-table {
  width: 100%;
  border-collapse: collapse;
}
.truck-detail-table th,
.truck-detail-table td {
  border: 1px solid #2d3748;
  font-size: 12px;
  padding: 4px 6px;
}
.truck-detail-table th {
  background: #e8edf3;
  text-align: center;
}
.num-cell {
  text-align: center;
}
.detail-empty {
  text-align: center;
  color: #6b7280;
}
.pseudo-product-wrap {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 6px;
  max-height: 300px;
  overflow: auto;
}
.pseudo-product-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.pseudo-product-title {
  font-weight: 700;
  font-size: 13px;
  color: #111827;
}
.pseudo-product-table {
  width: auto;
  border-collapse: collapse;
}
.pseudo-product-table th,
.pseudo-product-table td {
  border: 1px solid #2d3748;
  font-size: 12px;
  padding: 4px 8px;
}
.pseudo-product-table th {
  background: #e8edf3;
  text-align: center;
}
.pseudo-check-cell {
  text-align: center;
}
.pseudo-label-col {
  white-space: nowrap;
  font-weight: 600;
  text-align: center;
  min-width: 30px;
}
.pseudo-product-col {
  text-align: center;
  white-space: nowrap;
  padding: 2px 6px !important;
}
.pseudo-col-code {
  font-size: 11px;
  font-weight: 600;
}
.pseudo-col-name {
  font-size: 10px;
  color: #374151;
}
.pseudo-col-shipto {
  font-size: 10px;
  color: #6b7280;
}
.day-split-left {
  border-left: 2px solid #111827 !important;
}
.table-wrap {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.grid {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}
.grid th,
.grid td {
  border-right: 1px solid #2d3748;
  border-bottom: 1px solid #2d3748;
  font-size: 12px;
  padding: 4px 0;
  background: #f8fafc;
  vertical-align: top;
}
.grid thead tr:first-child th {
  border-top: 1px solid #2d3748;
}
.grid th:first-child,
.grid td:first-child {
  border-left: 1px solid #2d3748;
}
.grid th {
  text-align: center;
  white-space: nowrap;
  position: sticky;
  z-index: 2;
}
.grid tbody td {
  padding: 0;
}
.left-head {
  background: #e5e7eb !important;
  position: sticky;
  z-index: 3 !important;
  left: 0;
}
.left-head.shipto-col {
  left: 136px;
}
.date-head {
  background: #eceff3 !important;
  padding: 0 6px !important;
}
.date-head-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.date-head-label {
  font-size: 24px;
  line-height: 1.2;
}
.pseudo-occ {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: 20px;
  font-weight: 500;
  color: #111827;
}
.pseudo-occ-left {
  left: 8px;
}
.pseudo-occ-right {
  right: 8px;
}
.pseudo-occ-over {
  color: #dc2626 !important;
  font-weight: 700;
}
.holiday-head {
  color: #b91c1c !important;
}
.truck-head,
.occ-head,
.item-head {
  min-width: 96px;
}
.col-order {
  width: 70px;
  min-width: 70px !important;
  max-width: 70px;
}
.col-demand,
.col-assigned,
.col-remain {
  width: 50px;
  min-width: 50px !important;
  max-width: 50px;
}
.col-select {
  width: 110px;
  min-width: 110px !important;
  max-width: 110px;
}
.truck-head {
  background: #f1f5f9 !important;
  border-bottom: 1px solid #2d3748 !important;
}
.occ-head {
  background: #f8fafc !important;
  border-bottom: 1px solid #2d3748 !important;
}
.item-head {
  background: #eef2f7 !important;
  font-weight: 500;
  border-bottom: 1px solid #2d3748 !important;
}
.code-col {
  min-width: 135px;
  background: #fff;
  position: sticky;
  left: 0;
  z-index: 1;
}
.shipto-col {
  min-width: 72px;
  text-align: center;
  background: #fff;
  position: sticky;
  left: 136px;
  z-index: 1;
}
.grid tbody td.code-col,
.grid tbody td.shipto-col {
  padding: 6px;
}
.cell-center {
  text-align: center;
  background: #fff;
}
.cell-right {
  text-align: center;
  background: #fff;
}
.cell-select {
  min-width: 180px;
  background: #fff;
}
.cell-stacked .sub-cell {
  min-height: 28px;
  line-height: 28px;
  padding: 0;
  border-bottom: 1px dashed #e2e8f0;
  box-sizing: border-box;
}
.cell-stacked .sub-cell:last-child {
  border-bottom: none;
}
.select-subcell {
  padding: 2px 0 !important;
  min-height: 30px !important;
  line-height: normal !important;
}
.allocation-stack {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.allocation-row {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.allocation-row select,
.allocation-row input {
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  height: 24px;
  padding: 2px 4px;
  font-size: 12px;
}
.allocation-row select {
  width: 35px;
}
.allocation-row input {
  width: 30px;
  text-align: right;
}
.mini {
  width: 15px;
  height: 15px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
  font-size: 10px;
  line-height: 1;
  padding: 0;
}
.mini.danger {
  color: #b91c1c;
}
.remain-negative {
  color: #b91c1c;
  font-weight: 700;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 20px 0 !important;
}
.note {
  font-size: 12px;
  color: #6b7280;
}
.cursor-product-bubble {
  position: fixed;
  z-index: 1200;
  pointer-events: none;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fde68a;
  border: 1px solid #d97706;
  color: #7c2d12;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
}
.daily-load-row td {
  background: #f9fbff;
  border-top: 2px solid #94a3b8;
}
.daily-load-label {
  font-weight: 700;
  text-align: center;
  background: #eef2f7 !important;
}
.daily-load-cell {
  padding: 0 !important;
  background: #fdfefe !important;
}
.daily-load-blocks {
  width: 100%;
}
.daily-load-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.daily-load-table td {
  border-right: 1px solid #cbd5e1;
  border-bottom: 1px solid #cbd5e1;
  padding: 2px 4px;
  font-size: 12px;
  line-height: 1.2;
  white-space: nowrap;
}
.daily-load-table tr:last-child td {
  border-bottom: none;
}
.daily-load-table td:last-child {
  border-right: none;
}
.daily-load-truck {
  width: 54px;
  text-align: left;
  vertical-align: top;
  background: #fafafa;
  font-weight: 500;
}
.daily-load-product {
  text-align: left;
  vertical-align: middle;
  color: #111827;
}
.daily-load-empty {
  min-height: 28px;
  line-height: 28px;
  padding: 0 6px;
  color: #94a3b8;
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

