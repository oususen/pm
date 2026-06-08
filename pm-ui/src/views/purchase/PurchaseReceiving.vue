<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仕入れ検収 <button v-if="authState.user?.is_superuser" class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button></h1>
      <div class="page-actions">
        <select v-model="selectedSupplier" @change="onSupplierChange">
          <option value="">-- 仕入先 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">
            {{ s.supplier_code }} {{ s.supplier_name }}
          </option>
        </select>
        <input type="date" v-model="targetDate" @change="onTargetDateChange" />
        <button class="btn-primary" @click="loadCurrentTabData" :disabled="!selectedSupplier">検収データ取得</button>
        <button v-if="rows.length" class="btn-excel" @click="exportExcel">Excel出力</button>
        <button v-if="selectedSupplier" class="btn-history" @click="toggleHistory">検収履歴</button>
      </div>
    </div>

    <div class="page-content">
      <div class="receiving-tabs">
        <button :class="['tab-btn', { active: activeTab === 'progress' }]" @click="activeTab = 'progress'">進度方式</button>
        <button :class="['tab-btn', { active: activeTab === 'delivery_list' }]" @click="switchToDeliveryList">納入リスト</button>
      </div>

      <template v-if="activeTab === 'progress'">
      <div v-if="selectedSupplier && !loading" class="pattern-info">
        <span class="pattern-label">納入パターン:</span>
        <span class="pattern-value">{{ patternInfo ? `${patternInfo.pattern_name} (${patternInfo.recurrence_type_display})` : '未設定（毎日納入）' }}</span>
        <span v-if="isDeliveryDay" class="delivery-badge yes">本日は納入日</span>
        <span v-else class="delivery-badge no">本日は納入日ではありません</span>
        <span v-if="nextDeliveryDate" class="next-delivery">次回納入日: {{ nextDeliveryDate }}</span>
        <div class="btn-group basis-group">
          <button :class="['btn-filter', { active: basis === 'progress' }]" @click="switchBasis('progress')">進度基準</button>
          <button :class="['btn-filter', { active: basis === 'inventory' }]" @click="switchBasis('inventory')">在庫基準</button>
        </div>
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
          <span class="filter-label">G:</span>
          <button :class="['btn-filter', { active: filterG === '' }]" @click="filterG = ''">全</button>
          <button :class="['btn-filter', { active: filterG === 'yes' }]" @click="filterG = 'yes'">有</button>
          <button :class="['btn-filter', { active: filterG === 'no' }]" @click="filterG = 'no'">無</button>
        </div>
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
            <th class="col-dest">移動先</th>
            <th class="num col-total">予定</th>
            <th class="col-confirm"></th>
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
          <tr v-for="row in filteredRows" :key="row.product_id" :class="{ 'row-held': row.held, 'row-confirmed': row.confirmed, 'row-done': !row.held && !row.confirmed && row.actual_qty > 0 && row.actual_qty === row.expected_qty }">
            <td class="col-code">
              {{ row.product_code }}
              <button class="btn-hold" :class="{ active: row.held }" @click="toggleHold(row)">数変更</button>
            </td>
            <td class="col-name">{{ row.product_name }}</td>
            <td class="col-dest">{{ row.transfer_destination_label || '' }}</td>
            <td class="num col-total bold">{{ row.expected_qty }}</td>
            <td class="col-confirm">
              <button v-if="!row.actual_qty || row.actual_qty < row.expected_qty" class="btn-confirmed" :class="{ active: row.confirmed }" @click="row.confirmed = !row.confirmed">確認済</button>
              <span v-else class="badge-received">検収済</span>
            </td>
            <td class="num col-actual">{{ row.actual_qty || '' }}</td>
            <td v-for="d in coverageDates" :key="d" class="num col-date">{{ row.daily[d] || '' }}</td>
            <td class="num col-recv">
              <input v-if="!row.actual_qty || row.actual_qty < row.expected_qty" type="number" v-model.number="row.received_qty" min="0" class="input-qty" />
              <span v-else class="text-muted">-</span>
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

      <div v-if="selectedSupplier && !loading" class="add-row-area">
        <button class="btn-add" @click="openAddModal('progress')">+ 製品追加</button>
      </div>

      <div v-if="filteredRows.length || rows.length" class="form-actions">
        <button v-if="isAdminUser && hasConfirmableProgressRows" class="btn-confirm-all" type="button" @click="confirmAllProgressRows">全確認済み</button>
        <button v-if="filterHeld !== 'yes'" class="btn-success" @click="saveReceiving" :disabled="saving || !allTargetsConfirmed">検収確定</button>
        <button v-if="filterHeld === 'yes'" class="btn-held-confirm" @click="saveHeldReceiving" :disabled="saving || !allHeldConfirmed">数変更検収確定</button>
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
      </template>

      <template v-else>
        <div v-if="deliveryListLoading" class="no-data">読み込み中...</div>
        <div v-else-if="deliveryListRows.length" class="filter-bar">
          <label>品番:
            <input v-model="filterProductCodeDelivery" class="filter-input" placeholder="部分一致" />
          </label>
          <div class="btn-group">
            <span class="filter-label">G:</span>
            <button :class="['btn-filter', { active: filterGDelivery === '' }]" @click="filterGDelivery = ''">全</button>
            <button :class="['btn-filter', { active: filterGDelivery === 'yes' }]" @click="filterGDelivery = 'yes'">有</button>
            <button :class="['btn-filter', { active: filterGDelivery === 'no' }]" @click="filterGDelivery = 'no'">無</button>
          </div>
          <div class="btn-group">
            <span class="filter-label">数変更:</span>
            <button :class="['btn-filter', { active: filterHeldDelivery === '' }]" @click="filterHeldDelivery = ''">全</button>
            <button :class="['btn-filter', { active: filterHeldDelivery === 'yes' }]" @click="filterHeldDelivery = 'yes'">有</button>
            <button :class="['btn-filter', { active: filterHeldDelivery === 'no' }]" @click="filterHeldDelivery = 'no'">無</button>
          </div>
          <div class="btn-group">
            <span class="filter-label">差異:</span>
            <button :class="['btn-filter', { active: filterDiffDelivery === '' }]" @click="filterDiffDelivery = ''">全</button>
            <button :class="['btn-filter', { active: filterDiffDelivery === 'yes' }]" @click="filterDiffDelivery = 'yes'">有</button>
            <button :class="['btn-filter', { active: filterDiffDelivery === 'no' }]" @click="filterDiffDelivery = 'no'">無</button>
          </div>
          <div class="btn-group">
            <span class="filter-label">実績:</span>
            <button :class="['btn-filter', { active: filterActualDelivery === '' }]" @click="filterActualDelivery = ''">全</button>
            <button :class="['btn-filter', { active: filterActualDelivery === 'yes' }]" @click="filterActualDelivery = 'yes'">有</button>
            <button :class="['btn-filter', { active: filterActualDelivery === 'no' }]" @click="filterActualDelivery = 'no'">無</button>
          </div>
        </div>
        <table v-if="filteredDeliveryListRows.length" class="data-table">
          <thead>
            <tr>
              <th>品番</th>
              <th>品名</th>
              <th class="num">納入予定</th>
              <th class="col-confirm"></th>
              <th class="num">実績</th>
              <th class="num">実数</th>
              <th>備考</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredDeliveryListRows" :key="r.product_id" :class="{ 'row-held': r.held, 'row-confirmed': r.confirmed, 'row-done': r.actual_qty && r.actual_qty >= r.expected_qty }">
              <td>
                {{ r.product_code }}
                <button class="btn-hold" :class="{ active: r.held }" @click="toggleHoldDelivery(r)">数変更</button>
              </td>
              <td>{{ r.product_name }}</td>
              <td class="num">{{ r.expected_qty }}</td>
              <td class="col-confirm">
                <button v-if="!r.actual_qty || r.actual_qty < r.expected_qty" class="btn-confirmed" :class="{ active: r.confirmed }" @click="r.confirmed = !r.confirmed">確認済</button>
                <span v-else class="badge-received">検収済</span>
              </td>
              <td class="num">{{ r.actual_qty || '' }}</td>
              <td class="num">
                <input v-if="!r.actual_qty || r.actual_qty < r.expected_qty" type="number" v-model.number="r.received_qty" min="0" class="input-qty" />
                <span v-else class="text-muted">-</span>
              </td>
              <td><input v-model="r.note" class="input-note" /></td>
            </tr>
          </tbody>
        </table>
        <div v-else-if="deliveryListRows.length" class="no-data">表示条件に一致するデータがありません。</div>
        <div v-else class="no-data">この日の納入予定は未登録です（事務員が納入予定画面で登録）。</div>

        <div v-if="selectedSupplier" class="add-row-area">
          <button class="btn-add" @click="openAddModal('delivery')">+ 製品追加</button>
        </div>

        <div v-if="deliveryListRows.length" class="form-actions">
          <button v-if="isAdminUser && hasConfirmableDeliveryRows" class="btn-confirm-all" type="button" @click="confirmAllDeliveryRows">全確認済み</button>
          <button v-if="filterHeldDelivery !== 'yes'" class="btn-success" :disabled="saving || !allDeliveryTargetsConfirmed" @click="saveDeliveryListReceiving">検収確定</button>
          <button v-if="filterHeldDelivery === 'yes'" class="btn-held-confirm" :disabled="saving || !allDeliveryHeldConfirmed" @click="saveDeliveryListHeldReceiving">数変更検収確定</button>
        </div>
      </template>
    </div>

    <!-- 製品追加モーダル -->
    <div v-if="showAddModal" class="ds-overlay" @click.self="closeAddModal">
      <div class="add-modal">
        <div class="ds-header">
          <h3>製品追加</h3>
          <button class="ds-close" @click="closeAddModal">&times;</button>
        </div>
        <div class="add-modal-body">
          <input v-model="addModalSearch" class="add-modal-input" placeholder="品番・品名で検索" ref="addModalInputRef" />
          <div class="add-modal-list">
            <div v-for="p in addModalResults" :key="p.product_id" class="add-dropdown-item" @click="onAddModalSelect(p)">
              <span class="add-code">{{ p.product_code }}</span>
              <span class="add-name">{{ p.product_name }}</span>
            </div>
            <div v-if="addModalSearch && !addModalResults.length" class="add-modal-empty">該当する製品がありません</div>
          </div>
        </div>
      </div>
    </div>

    <!-- データソースモーダル -->
    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header"><h3>データソース</h3><button class="ds-close" @click="showDataSource = false">&times;</button></div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr class="ds-section"><td colspan="3"><strong>検収データ（通常タブ）</strong></td></tr>
            <tr><td>需要 読み取り</td><td>line_demand</td><td>顧客需要（進度ベース時の予定数量算出）</td></tr>
            <tr><td>計画実績 読み取り</td><td>line_backlog</td><td>計画数量（在庫ベース時の予定数量算出）</td></tr>
            <tr><td>実績 書き込み</td><td>process_realtime_record</td><td>検収確定時に生産実績レコード作成</td></tr>
            <tr class="ds-section"><td colspan="3"><strong>検収データ（納入リストタブ）</strong></td></tr>
            <tr><td>納入予定 読み取り</td><td>purchase_delivery_schedule</td><td>事務員登録の納入予定データ</td></tr>
            <tr class="ds-section"><td colspan="3"><strong>納入パターン判定</strong></td></tr>
            <tr><td>スケジュール 読み取り</td><td>supplier_order_schedule</td><td>仕入先×パターン割当</td></tr>
            <tr><td>パターン 読み取り</td><td>supplier_order_pattern</td><td>納入パターン定義</td></tr>
            <tr class="ds-section"><td colspan="3"><strong>マスタ</strong></td></tr>
            <tr><td>仕入先 読み取り</td><td>m_supplier</td><td>仕入先マスタ</td></tr>
            <tr><td>ライン 読み取り</td><td>m_line</td><td>仕入先コードからライン特定</td></tr>
            <tr><td>工程 読み取り</td><td>m_process</td><td>PURCHASE工程</td></tr>
            <tr><td>カレンダー 読み取り</td><td>m_calendar</td><td>営業日判定</td></tr>
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
import { authState } from '@/auth'

const showDataSource = ref(false)
const suppliers = ref([])
const selectedSupplier = ref('')
const targetDate = ref(new Date().toISOString().slice(0, 10))
const basis = ref('progress')
const activeTab = ref('progress')
const deliveryListLoading = ref(false)
const deliveryListRows = ref([])
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const coverageDates = ref([])
const patternInfo = ref(null)
const isDeliveryDay = ref(false)
const nextDeliveryDate = ref('')

const supplierProducts = ref([])
const showAddModal = ref(false)
const addModalSearch = ref('')
const addModalTarget = ref('')
const addModalInputRef = ref(null)

const addModalResults = computed(() => {
  const q = addModalSearch.value.trim().toUpperCase()
  if (!q) return supplierProducts.value
  return supplierProducts.value.filter((p) =>
    p.product_code.toUpperCase().includes(q) || p.product_name.toUpperCase().includes(q)
  )
})

const openAddModal = (target) => {
  addModalTarget.value = target
  addModalSearch.value = ''
  showAddModal.value = true
  setTimeout(() => addModalInputRef.value?.focus(), 50)
}

const closeAddModal = () => {
  showAddModal.value = false
  addModalSearch.value = ''
}

const onAddModalSelect = (product) => {
  if (addModalTarget.value === 'progress') addProductToRows(product)
  else addProductToDeliveryRows(product)
}

const fetchSupplierProducts = async () => {
  if (!selectedSupplier.value) { supplierProducts.value = []; return }
  try {
    const res = await api.client.get('/purchase-receiving/delivery-list-template/', {
      params: { supplier_id: selectedSupplier.value },
    })
    supplierProducts.value = res.data.items || []
  } catch { supplierProducts.value = [] }
}

const addProductToRows = (product) => {
  const existing = rows.value.find((r) => r.product_id === product.product_id)
  if (existing && isReceived(existing)) {
    if (!confirm(`${product.product_code} は検収済みです。追加検収行を作成しますか？`)) return
  } else if (existing) {
    alert(`${product.product_code} は既にリストにあります。`)
    return
  }
  rows.value.push({
    product_id: product.product_id,
    product_code: product.product_code,
    product_name: product.product_name,
    transfer_destination: '',
    transfer_destination_label: '',
    next_process_name: '',
    expected_qty: 0,
    actual_qty: 0,
    daily: {},
    received_qty: 0,
    held: false,
    confirmed: false,
    note: product.product_code,
    _manual: true,
  })
  addModalSearch.value = ''
}

const addProductToDeliveryRows = (product) => {
  const existing = deliveryListRows.value.find((r) => r.product_id === product.product_id)
  if (existing && isReceived(existing)) {
    if (!confirm(`${product.product_code} は検収済みです。追加検収行を作成しますか？`)) return
  } else if (existing) {
    alert(`${product.product_code} は既にリストにあります。`)
    return
  }
  deliveryListRows.value.push({
    product_id: product.product_id,
    product_code: product.product_code,
    product_name: product.product_name,
    expected_qty: 0,
    actual_qty: 0,
    received_qty: 0,
    held: false,
    confirmed: false,
    note: product.product_code,
    _manual: true,
  })
  addModalSearch.value = ''
}

const filterDest = ref('')
const filterNextProcess = ref('')
const filterActual = ref('')
const filterProductCode = ref('')
const filterHeld = ref('')
const filterDiff = ref('')
const filterG = ref('yes')
const filterHeldDelivery = ref('')
const filterDiffDelivery = ref('')
const filterActualDelivery = ref('')
const filterProductCodeDelivery = ref('')
const filterGDelivery = ref('yes')

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
    if (filterG.value === 'yes' && !r.product_code.endsWith('G')) return false
    if (filterG.value === 'no' && r.product_code.endsWith('G')) return false
    return true
  })
})
const filteredDeliveryListRows = computed(() => {
  return deliveryListRows.value.filter((r) => {
    if (filterProductCodeDelivery.value && !String(r.product_code || '').toUpperCase().includes(filterProductCodeDelivery.value.toUpperCase())) return false
    if (filterHeldDelivery.value === 'yes' && !r.held) return false
    if (filterHeldDelivery.value === 'no' && r.held) return false
    if (filterDiffDelivery.value === 'yes' && r.actual_qty && r.actual_qty === r.expected_qty) return false
    if (filterDiffDelivery.value === 'no' && (!r.actual_qty || r.actual_qty !== r.expected_qty)) return false
    if (filterActualDelivery.value === 'yes' && !r.actual_qty) return false
    if (filterActualDelivery.value === 'no' && r.actual_qty) return false
    if (filterGDelivery.value === 'yes' && !String(r.product_code || '').endsWith('G')) return false
    if (filterGDelivery.value === 'no' && String(r.product_code || '').endsWith('G')) return false
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

const switchBasis = (b) => {
  basis.value = b
  if (selectedSupplier.value) loadReceivingData()
}

const loadCurrentTabData = () => {
  if (activeTab.value === 'delivery_list') return loadDeliveryListData()
  return loadReceivingData()
}

const onTargetDateChange = () => {
  loadCurrentTabData()
}

const getDefaultGFilter = () => {
  const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
  if (!supplier) return 'yes'
  if (supplier.supplier_type === 'outsource') return 'yes'
  if (supplier.supplier_type === 'purchase') return 'no'
  return ''
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
  const gDefault = getDefaultGFilter()
  filterG.value = gDefault
  filterHeldDelivery.value = ''
  filterDiffDelivery.value = ''
  filterActualDelivery.value = ''
  filterProductCodeDelivery.value = ''
  filterGDelivery.value = gDefault
  deliveryListRows.value = []
  showAddModal.value = false
  if (selectedSupplier.value) {
    fetchSupplierProducts()
    if (activeTab.value === 'progress') loadReceivingData()
    else loadDeliveryListData()
  }
}

const switchToDeliveryList = async () => {
  activeTab.value = 'delivery_list'
  await loadDeliveryListData()
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
        basis: basis.value,
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
        confirmed: false,
        note: s ? s.note : item.product_code || '',
      }
    })
  } catch (e) {
    console.error('検収データ取得エラー', e)
    alert('データの取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const isReceived = (r) => !r._manual && r.actual_qty && r.actual_qty >= r.expected_qty

const saveReceiving = async () => {
  if (!rows.value.length) return
  const targets = filteredRows.value.filter((r) => !r.held && !isReceived(r))
  if (!targets.length) {
    alert('検収対象がありません。')
    return
  }
  saving.value = true
  try {
    await api.client.post('/purchase-receiving/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      items: targets.map((r) => ({
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
const allTargetsConfirmed = computed(() => filteredRows.value.filter((r) => !r.held && !isReceived(r)).every((r) => r.confirmed))
const allHeldConfirmed = computed(() => filteredRows.value.filter((r) => r.held && !isReceived(r)).every((r) => r.confirmed))
const allDeliveryTargetsConfirmed = computed(() => filteredDeliveryListRows.value.filter((r) => !r.held && !isReceived(r)).every((r) => r.confirmed))
const allDeliveryHeldConfirmed = computed(() => filteredDeliveryListRows.value.filter((r) => r.held && !isReceived(r)).every((r) => r.confirmed))
const hasConfirmableProgressRows = computed(() => filteredRows.value.some((r) => !isReceived(r) && !r.confirmed))
const hasConfirmableDeliveryRows = computed(() => filteredDeliveryListRows.value.some((r) => !isReceived(r) && !r.confirmed))

const confirmAllProgressRows = () => {
  for (const row of filteredRows.value) {
    if (!isReceived(row)) row.confirmed = true
  }
}

const confirmAllDeliveryRows = () => {
  for (const row of filteredDeliveryListRows.value) {
    if (!isReceived(row)) row.confirmed = true
  }
}

const saveHeldReceiving = async () => {
  const heldItems = filteredRows.value.filter((r) => r.held && !isReceived(r))
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
const isAdminUser = computed(() => authState.user?.username === 'admin')

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

const loadDeliveryListData = async () => {
  if (!selectedSupplier.value) return
  deliveryListLoading.value = true
  deliveryListRows.value = []
  try {
    const res = await api.client.get('/purchase-delivery-schedules/', {
      params: { supplier_id: selectedSupplier.value, target_date: targetDate.value },
    })
    const items = res.data.items || []
    deliveryListRows.value = items.map((r) => ({
      ...r,
      received_qty: r.expected_qty,
      held: false,
      confirmed: false,
      note: r.product_code || '',
    }))
  } catch (e) {
    console.error('納入リスト取得エラー', e)
  } finally {
    deliveryListLoading.value = false
  }
}

const saveDeliveryListReceiving = async () => {
  const targets = filteredDeliveryListRows.value.filter((r) => !r.held && !isReceived(r) && Number(r.received_qty) > 0)
  if (!targets.length) {
    alert('検収対象がありません。')
    return
  }
  saving.value = true
  try {
    await api.client.post('/purchase-receiving/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      items: targets.map((r) => ({
        product_id: r.product_id,
        expected_qty: r.expected_qty,
        received_qty: r.received_qty,
        note: r.note || '',
      })),
    })
    alert('検収を確定しました。')
    await loadDeliveryListData()
  } catch (e) {
    console.error('納入リスト検収確定エラー', e)
    alert('検収の確定に失敗しました。')
  } finally {
    saving.value = false
  }
}

const saveDeliveryListHeldReceiving = async () => {
  const targets = filteredDeliveryListRows.value.filter((r) => r.held && !isReceived(r) && Number(r.received_qty) > 0)
  if (!targets.length) {
    alert('数変更の検収対象がありません。')
    return
  }
  saving.value = true
  try {
    await api.client.post('/purchase-receiving/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      items: targets.map((r) => ({
        product_id: r.product_id,
        expected_qty: r.expected_qty,
        received_qty: r.received_qty,
        note: r.note || '',
      })),
    })
    alert('数変更検収を確定しました。')
    await loadDeliveryListData()
  } catch (e) {
    console.error('納入リスト数変更検収確定エラー', e)
    alert('数変更検収の確定に失敗しました。')
  } finally {
    saving.value = false
  }
}

const toggleHoldDelivery = (row) => {
  row.held = !row.held
  if (row.held) row.received_qty = 0
  else row.received_qty = row.expected_qty
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
.receiving-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}
.tab-btn {
  padding: 6px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.tab-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
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
.basis-group { margin-left: 8px; }
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
.btn-confirmed {
  margin-left: 4px;
  padding: 1px 6px;
  font-size: 11px;
  border: 1px solid #d1d5db;
  border-radius: 3px;
  background: #fff;
  color: #64748b;
  cursor: pointer;
}
.btn-confirmed.active {
  background: #dcfce7;
  border-color: #22c55e;
  color: #166534;
  font-weight: 600;
}
.badge-received {
  display: inline-block;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 600;
  background: #e2e8f0;
  color: #64748b;
  border-radius: 3px;
}
.text-muted { color: #94a3b8; }
.add-row-area { margin: 8px 0; }
.btn-add {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  border: 1px dashed #94a3b8;
  border-radius: 4px;
  background: #fff;
  color: #475569;
  cursor: pointer;
}
.btn-add:hover { background: #f1f5f9; }
.add-modal {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0,0,0,.2);
  width: 480px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}
.add-modal-body { padding: 12px 18px 18px; display: flex; flex-direction: column; gap: 8px; overflow: hidden; }
.add-modal-input { width: 100%; padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 14px; }
.add-modal-list { overflow-y: auto; max-height: 50vh; border: 1px solid #e5e7eb; border-radius: 4px; }
.add-modal-empty { padding: 12px; color: #94a3b8; font-size: 13px; text-align: center; }
.add-dropdown-item {
  display: flex;
  gap: 8px;
  padding: 6px 10px;
  font-size: 13px;
  cursor: pointer;
}
.add-dropdown-item:hover { background: #eff6ff; }
.add-code { font-weight: 600; color: #1e293b; min-width: 140px; }
.add-name { color: #64748b; }
.row-confirmed { background: #f0fdf4; }
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
.btn-confirm-all {
  padding: 6px 16px;
  background: #0f766e;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
}
.btn-confirm-all:hover { background: #0d9488; }
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
.ds-section td { background: #f0f4ff; padding: 6px 12px; }
</style>
