<template>
  <div class="page frame">
    <div class="top-bar">[SSE0030] 仕入れ実績入力</div>
    <div class="toolbar">
      <label class="toolbar-field">
        <span>納入日</span>
        <input
          v-model.trim="arrivalDate"
          type="text"
          placeholder="YYYY/MM/DD"
          @blur="normalizeArrivalDate"
          @keydown.enter.prevent="normalizeArrivalDate"
        />
      </label>
      <label class="toolbar-field">
        <span>処理方法</span>
        <select v-model="activeTab">
          <option value="individual">1:個別</option>
          <option value="bulk">2:一括</option>
        </select>
      </label>
    </div>
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'individual' }" type="button" @click="activeTab = 'individual'">個別</button>
      <button class="tab" :class="{ active: activeTab === 'bulk' }" type="button" @click="activeTab = 'bulk'">一括</button>
    </div>

    <!-- 個別タブ -->
    <div v-show="activeTab === 'individual'" class="content">
      <section class="left-pane">
        <section class="panel">
          <div class="row"><label>品番</label>
            <input
              ref="barcodeInputRef"
              v-model.trim="barcode"
              type="text"
              placeholder="バーコード読取後 Enter"
              @keydown.enter.prevent="resolveProductFromBarcode"
            />
          </div>
          <div class="row"><label>品名</label><input :value="productName" type="text" readonly /></div>
          <div class="row"><label>部品番号</label>
            <input
              v-model.trim="productCode"
              type="text"
              @blur="resolveProductFromCode"
              @keydown.enter.prevent="resolveProductFromCode"
            />
          </div>
        </section>

        <section class="panel">
          <div class="section-title">工程情報</div>
          <div class="row row-3"><label>工程順位</label><input value="10" type="text" readonly /><input :value="resolvedProcessLabel" type="text" readonly /></div>
          <div class="row"><label>加工先</label><input :value="resolvedLineLabel" type="text" readonly /></div>
          <div class="row"><label>購入先</label><input :value="selectedSupplierLabel" type="text" readonly /></div>
          <div class="row"><label>納入数</label><input ref="qtyInputRef" v-model.number="qty" type="number" min="1" step="1" /></div>
          <div class="row"><label>担当者</label><input v-model.trim="operatorName" type="text" readonly /></div>
          <div class="row"><label>備考</label><textarea v-model.trim="remarks" rows="2"></textarea></div>
        </section>

        <div class="candidate-wrap" v-if="supplierCandidates.length > 1">
          <div class="candidate-title">購入先候補（複数のため選択してください）</div>
          <table class="candidate-table">
            <thead>
              <tr>
                <th>工程順位</th>
                <th>工程CD</th>
                <th>加工先CD</th>
                <th>加工先名</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in supplierCandidates"
                :key="c.key"
                :class="{ selected: selectedSupplierKey === c.key }"
                @click="selectSupplierCandidate(c)"
              >
                <td>{{ c.stepNo }}</td>
                <td>{{ c.processCode }}</td>
                <td>{{ c.lineCode }}</td>
                <td>{{ c.lineName }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="right-pane">
        <div class="section-title">仕入進度情報</div>
        <table class="progress-table">
          <thead>
            <tr>
              <th>日付</th>
              <th>計需</th>
              <th>実需</th>
              <th>内示</th>
              <th>確定</th>
              <th>入荷</th>
              <th>計画</th>
              <th>調整</th>
              <th>在庫</th>
              <th>計画在庫</th>
              <th>進度</th>
              <th>計進</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in progressRows" :key="row.date" :class="{ holiday: isHoliday(row.date) }">
              <td :class="{ holidayText: isHoliday(row.date) }">{{ formatDate(row.date) }}</td>
              <td>{{ displayNum(getMetric(row, ['plan_demand', 'demand_qty_plan'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['actual_demand', 'order_qty', 'firm'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['forecast', 'forecast_order_qty'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['firm', 'firm_order_qty', 'order_qty'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['inbound', 'actual_qty'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['plan', 'plan_qty'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['adjust', 'adjust_qty'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['stock', 'stock_qty'])) }}</td>
              <td>{{ displayNum(getMetric(row, ['planned_stock', 'planned_stock_qty'])) }}</td>
              <td :class="{ negative: Number(getMetric(row, ['progress', 'progress_qty']) || 0) < 0 }">{{ displayNum(getMetric(row, ['progress', 'progress_qty'])) }}</td>
              <td :class="{ negative: Number(getMetric(row, ['planned_progress', 'planned_progress_qty']) || 0) < 0 }">{{ displayNum(getMetric(row, ['planned_progress', 'planned_progress_qty'])) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- 一括タブ -->
    <div v-show="activeTab === 'bulk'" class="bulk-section">
      <div class="bulk-header">
        <div class="bulk-header-row">
          <label class="bulk-label-tag">購入先</label>
          <select v-model="bulkSupplierId" @change="loadBulkItems" class="bulk-supplier-select">
            <option value="">選択してください</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">
              {{ s.supplier_code }} - {{ s.supplier_name }}
            </option>
          </select>
          <input :value="bulkLineLabel" type="text" readonly class="bulk-line-input" />
          <button class="btn" type="button" :disabled="!bulkRows.length" @click="copyPlanToActual">計画数を入荷数へコピー</button>
        </div>
        <div class="bulk-header-row">
          <label class="bulk-label-tag">計画日</label>
          <input
            v-model.trim="bulkPlanDate"
            type="text"
            placeholder="YYYY/MM/DD"
            class="bulk-date-input bulk-date-active"
            @blur="onBulkPlanDateBlur"
            @keydown.enter.prevent="onBulkPlanDateBlur"
          />
          <label class="bulk-label-tag">納入日</label>
          <input
            v-model.trim="arrivalDate"
            type="text"
            placeholder="YYYY/MM/DD"
            class="bulk-date-input"
            @blur="normalizeArrivalDate"
            @keydown.enter.prevent="normalizeArrivalDate"
          />
          <label class="bulk-label-tag">担当者</label>
          <input :value="operatorName" type="text" readonly class="bulk-operator-input" />
        </div>
        <div class="bulk-header-row">
          <label class="bulk-label-tag">CSV取込</label>
          <button class="btn" type="button" @click="openBulkCsvSelector">資材入荷外注納入一覧表</button>
          <select v-model="bulkCsvEncoding" class="bulk-encoding-select">
            <option value="Shift_JIS">Shift_JIS</option>
            <option value="UTF-8">UTF-8</option>
          </select>
          <span class="bulk-import-note">CSVの仕入先・納入日・品番・数量を一括行へ反映</span>
          <input
            ref="bulkCsvInputRef"
            type="file"
            accept=".csv"
            style="display:none"
            @change="onBulkCsvSelected"
          />
        </div>
      </div>

      <table class="bulk-table">
        <thead>
          <tr>
            <th class="col-no" rowspan="2">#</th>
            <th class="col-code" rowspan="2">品番</th>
            <th class="col-name" rowspan="2">品名</th>
            <th class="col-qty" rowspan="2">計画数</th>
            <th class="col-qty" rowspan="2">入荷数</th>
            <th :colspan="dateColumns.length" class="col-date-group">直近納入実績</th>
            <th class="col-status" rowspan="2"></th>
          </tr>
          <tr>
            <th v-for="dc in dateColumns" :key="dc.key" class="col-date">{{ dc.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in bulkRows"
            :key="i"
            :class="{
              'row-ok': row.result === 'ok',
              'row-error': row.result === 'error',
              'row-warn': row.error && !row.result,
            }"
          >
            <td class="col-no">{{ i + 1 }}</td>
            <td class="col-code">
              <input
                v-model.trim="row.barcode"
                type="text"
                placeholder="品番 / バーコード"
                :readonly="row.resolved"
                @keydown.enter.prevent="resolveBulkRow(i)"
                class="code-input"
              />
              <select
                v-if="row.candidates && row.candidates.length > 1"
                v-model="row.selectedKey"
                @change="selectBulkCandidate(i)"
                class="candidate-select"
              >
                <option value="">購入先選択</option>
                <option v-for="c in row.candidates" :key="c.key" :value="c.key">{{ c.lineName }}</option>
              </select>
            </td>
            <td class="col-name">{{ row.productName }}</td>
            <td class="col-qty text-right">{{ row.planQty > 0 ? row.planQty.toLocaleString() : '' }}</td>
            <td class="col-qty">
              <input v-model.number="row.qty" type="number" min="0" step="1" class="qty-input" />
            </td>
            <td
              v-for="dc in dateColumns"
              :key="dc.key"
              class="col-date text-right"
              :class="{ 'cell-actual': row.actualsByDate[dc.key] > 0 }"
            >{{ row.actualsByDate[dc.key] > 0 ? row.actualsByDate[dc.key].toLocaleString() : '' }}</td>
            <td class="col-status">
              <span v-if="row.result === 'ok'" class="icon-ok">✓</span>
              <span v-else-if="row.result === 'error'" class="icon-error" :title="row.error">×</span>
              <span v-else-if="row.error" class="icon-warn" :title="row.error">!</span>
              <button v-else type="button" class="btn-remove" @click="removeBulkRow(i)">削</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="bulk-table-footer">
        <button class="btn" type="button" @click="addBulkRow">行追加</button>
        <span class="bulk-count">{{ bulkRows.length }}件</span>
      </div>
    </div>

    <div class="actions">
      <template v-if="activeTab === 'individual'">
        <button class="btn primary" :disabled="submitting || !canEdit" @click="submit">登録</button>
        <button class="btn" :disabled="submitting" @click="clearForm">画面クリア</button>
      </template>
      <template v-else>
        <button class="btn primary" :disabled="bulkSubmitting || !canEdit" @click="submitBulk">一括登録</button>
        <button class="btn" :disabled="bulkSubmitting" @click="clearBulkRows">画面クリア</button>
      </template>
    </div>

    <div class="footer-strip">
      <span>F1:終了</span>
      <span>F3:画面クリア</span>
      <span>F11:前頁</span>
      <span>F12:登録</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import { hasPermission } from '@/router'

const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const entry = permissions.find((item) => item.resource === 'purchase.actual_input')
  if (entry) return Boolean(entry.can_edit)
  return hasPermission(user, 'purchase', 'edit')
})

// ── 共通 ──────────────────────────────────────
const activeTab = ref('individual')
const lines = ref([])
const processes = ref([])
const suppliers = ref([])
const arrivalDate = ref('')
const operatorName = ref('')
const submitting = ref(false)

// ── 個別タブ ──────────────────────────────────
const supplierId = ref('')
const resolvedLineId = ref('')
const resolvedProcessId = ref('')
const selectedSupplierKey = ref('')
const supplierCandidates = ref([])
const barcode = ref('')
const productId = ref('')
const productCode = ref('')
const productName = ref('')
const qty = ref(null)
const remarks = ref('')
const barcodeInputRef = ref(null)
const qtyInputRef = ref(null)
const progressRows = ref([])

const selectedSupplier = computed(() =>
  suppliers.value.find((s) => String(s.id) === String(supplierId.value)) || null
)
const selectedSupplierLabel = computed(() => {
  if (!selectedSupplier.value) return ''
  return `${selectedSupplier.value.supplier_code || ''} - ${selectedSupplier.value.supplier_name || ''}`.trim()
})
const resolvedLine = computed(() =>
  lines.value.find((l) => String(l.id) === String(resolvedLineId.value)) || null
)
const resolvedProcess = computed(() =>
  processes.value.find((p) => String(p.id) === String(resolvedProcessId.value)) || null
)
const resolvedLineLabel = computed(() => {
  if (!resolvedLine.value) return ''
  return `${resolvedLine.value.line_code || ''} - ${resolvedLine.value.line_name || ''}`.trim()
})
const resolvedProcessLabel = computed(() => {
  if (!resolvedProcess.value) return ''
  return `${resolvedProcess.value.process_code || ''} - ${resolvedProcess.value.process_name || ''}`.trim()
})

const resolvePurchaseLine = (supplier) => {
  if (!supplier) return null
  const name = String(supplier.supplier_name || '').trim()
  const code = String(supplier.supplier_code || '').trim()
  return (
    lines.value.find((l) => String(l.line_name || '').trim() === name) ||
    lines.value.find((l) => String(l.line_name || '').includes(name)) ||
    lines.value.find((l) => String(l.line_code || '').trim() === code) ||
    lines.value.find((l) => String(l.line_name || '').includes(code)) ||
    null
  )
}
const resolvePurchaseProcess = (lineId) => {
  if (!lineId) return null
  return (
    processes.value.find(
      (p) =>
        String(p.line) === String(lineId) &&
        String(p.process_code || '').toUpperCase() === 'PURCHASE'
    ) || null
  )
}
const onSupplierChange = () => {
  const supplier = selectedSupplier.value
  const line = resolvePurchaseLine(supplier)
  const process = line ? resolvePurchaseProcess(line.id) : null
  resolvedLineId.value = line?.id ? String(line.id) : ''
  resolvedProcessId.value = process?.id ? String(process.id) : ''
  if (!line) {
    alert('購入先に対応するラインが見つかりません。ライン名=購入先名の設定を確認してください。')
  } else if (!process) {
    alert('購入先ラインに対応するPURCHASE工程が見つかりません。')
  }
}
const selectSupplierCandidate = (c) => {
  selectedSupplierKey.value = c.key
  supplierId.value = c.supplierId ? String(c.supplierId) : ''
  resolvedLineId.value = c.lineId ? String(c.lineId) : ''
  resolvedProcessId.value = c.processId ? String(c.processId) : ''
  loadProgress()
}
const resolveSupplierCandidatesByProduct = async (_pid) => {
  supplierCandidates.value = []
  selectedSupplierKey.value = ''
  supplierId.value = ''
  resolvedLineId.value = ''
  resolvedProcessId.value = ''
  if (!productCode.value) return

  const res = await api.purchaseActuals.getCandidates(productCode.value)
  const candidates = Array.isArray(res.data?.candidates) ? res.data.candidates : []
  supplierCandidates.value = candidates.map((c) => ({
    key: c.key,
    stepNo: Number(c.step_no || 10),
    processId: c.process_id || null,
    processCode: c.process_code || 'PURCHASE',
    lineId: c.line_id || null,
    lineCode: c.line_code || '',
    lineName: c.line_name || '',
    supplierId: c.supplier_id || null,
  }))

  if (supplierCandidates.value.length === 1) {
    selectSupplierCandidate(supplierCandidates.value[0])
    await nextTick()
    qtyInputRef.value?.focus()
  } else {
    await loadProgress()
  }
}
const resolveProductFromCode = async () => {
  const code = String(productCode.value || '').trim()
  if (!code) return
  try {
    const candidateRes = await api.purchaseActuals.getCandidates(code)
    const product = candidateRes.data?.product
    if (!product?.id) {
      productId.value = ''
      productName.value = ''
      alert('品番が見つかりません。')
      return
    }
    productId.value = product.id
    productCode.value = product.product_code || code
    productName.value = product.product_name || ''
    await resolveSupplierCandidatesByProduct(product.id)
    await loadProgress()
  } catch (e) {
    console.error('品番解決失敗:', e)
    alert('品番の取得に失敗しました。')
  }
}
const loadProgress = async () => {
  if (!productCode.value) {
    progressRows.value = []
    return
  }
  try {
    const res = await api.purchaseActuals.getProgress({
      product_code: productCode.value,
      start_date: arrivalDate.value || undefined,
      line_id: resolvedLineId.value || undefined,
      process_id: resolvedProcessId.value || undefined,
    })
    progressRows.value = Array.isArray(res.data?.rows) ? res.data.rows : []
  } catch (e) {
    progressRows.value = []
  }
}
const resolveProductFromBarcode = async () => {
  const code = String(barcode.value || '').trim()
  if (!code) return
  productCode.value = code
  await resolveProductFromCode()
  if (productId.value) {
    qty.value = qty.value || 1
  }
}
const clearForm = async () => {
  barcode.value = ''
  productId.value = ''
  productCode.value = ''
  productName.value = ''
  qty.value = null
  remarks.value = ''
  supplierCandidates.value = []
  selectedSupplierKey.value = ''
  supplierId.value = ''
  resolvedLineId.value = ''
  resolvedProcessId.value = ''
  progressRows.value = []
  await nextTick()
  barcodeInputRef.value?.focus()
}
const submit = async () => {
  if (!canEdit.value) return
  if (!supplierId.value) {
    alert('購入先を選択してください。')
    return
  }
  if (!resolvedLineId.value) {
    alert('ラインを解決できません。設定を確認してください。')
    return
  }
  if (!productId.value && !productCode.value) {
    alert('品番を入力してください。')
    return
  }
  if (!qty.value || qty.value <= 0) {
    alert('数量は1以上で入力してください。')
    return
  }

  submitting.value = true
  try {
    await api.purchaseActuals.register({
      process_id: resolvedProcessId.value ? Number(resolvedProcessId.value) : null,
      product_code: productCode.value,
      qty: Number(qty.value),
      arrival_date: arrivalDate.value,
      supplier_id: supplierId.value ? Number(supplierId.value) : null,
      line_id: resolvedLineId.value ? Number(resolvedLineId.value) : null,
      operator_name: operatorName.value || '',
      remarks: remarks.value || '',
    })
    alert('登録しました。')
    await clearForm()
  } catch (e) {
    console.error('登録失敗:', e)
    alert('登録に失敗しました。')
  } finally {
    submitting.value = false
  }
}

// ── 一括タブ ──────────────────────────────────
const bulkSupplierId = ref('')
const bulkPlanDate = ref('')
const bulkLineLabel = ref('')
const bulkLineId = ref('')
const bulkProcessId = ref('')
const bulkRows = ref([])
const bulkSubmitting = ref(false)
const bulkCsvInputRef = ref(null)
const bulkCsvEncoding = ref('Shift_JIS')

// 直近14日分の日付列（計画日±7日）
const dateColumns = computed(() => {
  const cols = []
  const base = bulkPlanDate.value ? new Date(bulkPlanDate.value.replace(/\//g, '-')) : new Date()
  if (isNaN(base.getTime())) return cols
  for (let i = -7; i <= 7; i++) {
    const d = new Date(base)
    d.setDate(base.getDate() + i)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    cols.push({ key: `${y}-${m}-${day}`, label: `${d.getMonth() + 1}/${d.getDate()}` })
  }
  return cols
})

const createBulkRow = (opts = {}) => ({
  barcode: opts.productCode || '',
  productCode: opts.productCode || '',
  productName: opts.productName || '',
  productId: opts.productId || null,
  lineId: opts.lineId || '',
  processId: opts.processId || '',
  candidates: [],
  selectedKey: '',
  resolved: opts.resolved || false,
  planQty: opts.planQty || 0,
  qty: opts.qty ?? null,
  actualsByDate: opts.actualsByDate || {},
  error: '',
  result: '',
})

const parseCsvLine = (line) => {
  const cols = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i += 1
      } else {
        inQuotes = !inQuotes
      }
    } else if (ch === ',' && !inQuotes) {
      cols.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  cols.push(current.trim())
  return cols
}

const normalizeSupplierCode = (value) => {
  const digits = String(value || '').replace(/\D/g, '')
  if (!digits) return ''
  return String(Number(digits))
}

const findSupplierFromCsv = (supplierCode, supplierName) => {
  const normalizedCode = normalizeSupplierCode(supplierCode)
  const normalizedName = String(supplierName || '').trim()
  return (
    suppliers.value.find((item) => normalizeSupplierCode(item.supplier_code) === normalizedCode) ||
    suppliers.value.find((item) => String(item.supplier_name || '').trim() === normalizedName) ||
    null
  )
}

const normalizeMappingCode = (value) => String(value || '').trim().toUpperCase()

const normalizeImportDateText = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return ''

  const parts = raw.split(/\D+/).filter(Boolean)
  let year = null
  let month = null
  let day = null

  if (parts.length === 3 && parts[0].length === 4) {
    year = Number(parts[0])
    month = Number(parts[1])
    day = Number(parts[2])
  } else {
    const digits = raw.replace(/\D/g, '')
    if (digits.length !== 8) return ''
    year = Number(digits.slice(0, 4))
    month = Number(digits.slice(4, 6))
    day = Number(digits.slice(6, 8))
  }

  if (!year || !month || !day) return ''
  const normalized = new Date(year, month - 1, day)
  if (
    normalized.getFullYear() !== year ||
    normalized.getMonth() + 1 !== month ||
    normalized.getDate() !== day
  ) {
    return ''
  }
  return `${year}/${String(month).padStart(2, '0')}/${String(day).padStart(2, '0')}`
}

const resolveCsvImportMapping = (rawProductCode, inputType, mappings) => {
  const sourceCode = String(rawProductCode || '').trim()
  const sourceKey = normalizeMappingCode(sourceCode)
  const candidates = (Array.isArray(mappings) ? mappings : []).filter(
    (item) => normalizeMappingCode(item.coreProductCode) === sourceKey,
  )
  if (!candidates.length) {
    return { mapped: false, required: inputType === '外注納入', productCode: sourceCode }
  }
  const selected = candidates[0]
  const mappedCode = String(selected?.appProductCode || '').trim()
  if (!mappedCode) {
    return { mapped: false, required: inputType === '外注納入', productCode: sourceCode }
  }
  return { mapped: true, required: false, productCode: mappedCode }
}

const normalizeBulkPlanDate = () => {
  const raw = String(bulkPlanDate.value || '').trim()
  if (!raw) return
  const digits = raw.replace(/\D/g, '')
  const currentYear = new Date().getFullYear()
  let year = currentYear, month = null, day = null
  if (digits.length === 2) {
    const parts = raw.split(/\D+/)
    if (parts.length === 2) { month = Number(parts[0]); day = Number(parts[1]) }
    else { month = Number(digits.slice(0, 1)); day = Number(digits.slice(1, 2)) }
  }
  else if (digits.length === 3) { month = Number(digits.slice(0, 1)); day = Number(digits.slice(1, 3)) }
  else if (digits.length === 4) { month = Number(digits.slice(0, 2)); day = Number(digits.slice(2, 4)) }
  else if (digits.length === 8) { year = Number(digits.slice(0, 4)); month = Number(digits.slice(4, 6)); day = Number(digits.slice(6, 8)) }
  else return
  if (!month || !day || month < 1 || month > 12 || day < 1 || day > 31) return
  const d = new Date(year, month - 1, day)
  if (d.getFullYear() !== year || d.getMonth() + 1 !== month || d.getDate() !== day) return
  bulkPlanDate.value = `${year}/${String(month).padStart(2, '0')}/${String(day).padStart(2, '0')}`
}

const onBulkPlanDateBlur = async () => {
  normalizeBulkPlanDate()
  // 納入日が未入力なら計画日と同じ値をセット
  if (!arrivalDate.value && bulkPlanDate.value) arrivalDate.value = bulkPlanDate.value
  if (bulkSupplierId.value) await loadBulkItems()
}

const openBulkCsvSelector = () => {
  bulkCsvInputRef.value?.click()
}

const loadBulkItems = async () => {
  normalizeBulkPlanDate()
  bulkLineLabel.value = ''
  bulkLineId.value = ''
  bulkProcessId.value = ''
  bulkRows.value = []
  if (!bulkSupplierId.value) return

  try {
    const res = await api.purchaseActuals.getBulkItems({
      supplier_id: bulkSupplierId.value,
      plan_date: bulkPlanDate.value || arrivalDate.value || undefined,
    })
    bulkLineLabel.value = res.data?.line_name || ''
    bulkLineId.value = res.data?.line_id ? String(res.data.line_id) : ''
    bulkProcessId.value = res.data?.process_id ? String(res.data.process_id) : ''

    const items = Array.isArray(res.data?.items) ? res.data.items : []
    bulkRows.value = items.map((item) =>
      createBulkRow({
        productCode: item.product_code,
        productName: item.product_name,
        productId: item.product_id,
        lineId: item.line_id ? String(item.line_id) : bulkLineId.value,
        processId: item.process_id ? String(item.process_id) : bulkProcessId.value,
        planQty: item.plan_qty || 0,
        actualsByDate: item.actuals_by_date || {},
        resolved: true,
      })
    )
    if (bulkRows.value.length === 0) {
      bulkRows.value.push(createBulkRow())
    }
  } catch (e) {
    console.error('一括アイテム取得失敗:', e)
    bulkRows.value = [createBulkRow()]
  }
}

const onBulkCsvSelected = (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const text = String(e.target?.result || '')
      const linesRaw = text.split(/\r?\n/).filter((line) => line.trim())
      if (linesRaw.length < 2) {
        alert('CSVにデータがありません。')
        return
      }

      const headers = parseCsvLine(linesRaw[0]).map((item) => String(item || '').trim())
      const getIndex = (name) => headers.indexOf(name)
      const idxInputType = getIndex('入力区分')
      const idxArrivalDate = getIndex('入荷日')
      const idxProductCode = getIndex('品番')
      const idxProductName = getIndex('品名規格')
      const idxSupplierCode = getIndex('仕入先CD')
      const idxSupplierName = getIndex('仕入先名')
      const idxInboundQty = getIndex('入荷数量')
      const idxProductionQty = getIndex('生産数量')
      const requiredIndexes = [idxArrivalDate, idxProductCode, idxSupplierCode, idxSupplierName]
      if (requiredIndexes.some((idx) => idx < 0) || (idxInboundQty < 0 && idxProductionQty < 0)) {
        alert('CSVヘッダーを認識できません。資材入荷外注納入一覧表の形式を確認してください。')
        return
      }

      const supplierKeys = new Set()
      const arrivalDates = new Set()
      const aggregated = new Map()

      for (const [index, line] of linesRaw.slice(1).entries()) {
        const cols = parseCsvLine(line)
        const inputType = idxInputType >= 0 ? String(cols[idxInputType] || '').trim() : ''
        if (inputType && !['資材入荷', '外注納入'].includes(inputType)) continue

        const productCode = String(cols[idxProductCode] || '').trim()
        if (!productCode) continue

        const supplierCode = String(cols[idxSupplierCode] || '').trim()
        const supplierName = String(cols[idxSupplierName] || '').trim()
        const arrivalDateText = String(cols[idxArrivalDate] || '').trim()
        const normalizedArrivalDate = normalizeImportDateText(arrivalDateText)
        if (!normalizedArrivalDate) {
          alert(`CSVの入荷日を解釈できません。${index + 2}行目: ${arrivalDateText}`)
          return
        }
        const inboundQty = idxInboundQty >= 0 ? Number(String(cols[idxInboundQty] || '').trim() || 0) : 0
        const productionQty = idxProductionQty >= 0 ? Number(String(cols[idxProductionQty] || '').trim() || 0) : 0
        const qty = inputType === '外注納入'
          ? productionQty
          : inputType === '資材入荷'
            ? inboundQty
            : 0
        if (!qty || qty <= 0) continue

        supplierKeys.add(`${supplierCode}__${supplierName}`)
        arrivalDates.add(normalizedArrivalDate)

        const current = aggregated.get(productCode) || {
          productCode,
          inputType,
          productName: String(cols[idxProductName] || '').trim(),
          qty: 0,
        }
        current.qty += qty
        if (!current.productName) current.productName = String(cols[idxProductName] || '').trim()
        aggregated.set(productCode, current)
      }

      if (!aggregated.size) {
        alert('取込対象の数量行がありません。')
        return
      }
      if (supplierKeys.size !== 1) {
        alert('複数の仕入先が含まれるCSVは取込できません。仕入先ごとに分けてください。')
        return
      }
      if (arrivalDates.size !== 1) {
        alert('複数の入荷日が含まれるCSVは取込できません。入荷日ごとに分けてください。')
        return
      }

      const [supplierKey] = Array.from(supplierKeys)
      const [supplierCode, supplierName] = supplierKey.split('__')
      const supplier = findSupplierFromCsv(supplierCode, supplierName)
      if (!supplier?.id) {
        alert(`仕入先を特定できません。CSV: ${supplierCode} ${supplierName}`)
        return
      }

      let mappings = []
      try {
        const mappingRes = await api.purchaseActualKikanMapping.getMapping(supplier.id)
        mappings = Array.isArray(mappingRes.data?.mappings) ? mappingRes.data.mappings : []
      } catch (_mappingError) {
        alert('マッピング設定の取得に失敗しました。')
        return
      }

      const mappedAggregated = new Map()
      const unresolvedOutsourceCodes = []
      for (const item of Array.from(aggregated.values())) {
        const resolvedMapping = resolveCsvImportMapping(item.productCode, item.inputType, mappings)
        if (!resolvedMapping.mapped && resolvedMapping.required) {
          unresolvedOutsourceCodes.push(item.productCode)
          continue
        }

        const targetCode = resolvedMapping.productCode || item.productCode
        const current = mappedAggregated.get(targetCode) || {
          productCode: targetCode,
          productName: item.productName,
          qty: 0,
        }
        current.qty += item.qty
        mappedAggregated.set(targetCode, current)
      }

      if (unresolvedOutsourceCodes.length > 0) {
        alert(`外注納入の品番マッピングが未設定です。\n${unresolvedOutsourceCodes.join('\n')}`)
        return
      }
      if (!mappedAggregated.size) {
        alert('マッピング後に取込対象の品番がありません。')
        return
      }

      const [arrivalDateText] = Array.from(arrivalDates)
      bulkSupplierId.value = String(supplier.id)
      bulkPlanDate.value = arrivalDateText
      arrivalDate.value = arrivalDateText
      await loadBulkItems()

      const existingRowsByCode = new Map(
        bulkRows.value.map((row) => [String(row.productCode || row.barcode || '').trim().toUpperCase(), row])
      )
      bulkRows.value = Array.from(mappedAggregated.values()).map((item) => {
        const existing = existingRowsByCode.get(String(item.productCode || '').trim().toUpperCase())
        return createBulkRow({
          productCode: item.productCode,
          productName: existing?.productName || item.productName,
          productId: existing?.productId || null,
          lineId: existing?.lineId || bulkLineId.value,
          processId: existing?.processId || bulkProcessId.value,
          planQty: existing?.planQty || 0,
          actualsByDate: existing?.actualsByDate || {},
          resolved: Boolean((existing?.lineId || bulkLineId.value) && (existing?.processId || bulkProcessId.value)),
          qty: item.qty,
        })
      })

      const unresolvedCount = bulkRows.value.filter((row) => !row.resolved).length
      alert(`${bulkRows.value.length}件をCSVから読み込みました。${unresolvedCount > 0 ? ` ${unresolvedCount}件はラインまたは工程の解決が必要です。` : ''}`)
    } catch (err) {
      console.error('CSV取込失敗:', err)
      alert(`CSVの読み込みに失敗しました。${err?.message || ''}`)
    } finally {
      if (bulkCsvInputRef.value) bulkCsvInputRef.value.value = ''
    }
  }
  reader.readAsText(file, bulkCsvEncoding.value)
}

const _applyBulkCandidate = (row, c) => {
  row.selectedKey = c.key
  row.lineId = c.lineId ? String(c.lineId) : ''
  row.processId = c.processId ? String(c.processId) : ''
  row.resolved = true
  row.error = ''
}

const resolveBulkRow = async (i) => {
  const row = bulkRows.value[i]
  if (!row) return
  const code = String(row.barcode || '').trim()
  if (!code) return

  row.productCode = ''
  row.productName = ''
  row.productId = null
  row.candidates = []
  row.selectedKey = ''
  row.resolved = false
  row.error = ''
  row.planQty = 0

  try {
    const res = await api.purchaseActuals.getCandidates(code)
    const product = res.data?.product
    if (!product?.id) {
      row.error = '品番が見つかりません'
      return
    }
    row.productId = product.id
    row.productCode = product.product_code || code
    row.productName = product.product_name || ''
    row.barcode = row.productCode

    const rawCandidates = Array.isArray(res.data?.candidates) ? res.data.candidates : []
    // 選択中の購入先で絞り込む（なければ全候補）
    const filtered = bulkSupplierId.value
      ? rawCandidates.filter((c) => String(c.supplier_id) === String(bulkSupplierId.value))
      : rawCandidates
    const activeCandidates = filtered.length > 0 ? filtered : rawCandidates

    row.candidates = activeCandidates.map((c) => ({
      key: c.key,
      processId: c.process_id || null,
      lineId: c.line_id || null,
      lineCode: c.line_code || '',
      lineName: c.line_name || '',
      supplierId: c.supplier_id || null,
    }))

    if (row.candidates.length === 1) {
      _applyBulkCandidate(row, row.candidates[0])
    } else if (row.candidates.length === 0) {
      // 一括の購入先ラインをフォールバックとして使用
      row.lineId = bulkLineId.value
      row.processId = bulkProcessId.value
      row.resolved = true
    }
    // 複数候補の場合はselectで選択させる
  } catch (e) {
    row.error = '取得失敗'
  }
}

const selectBulkCandidate = (i) => {
  const row = bulkRows.value[i]
  if (!row) return
  const c = row.candidates.find((c) => c.key === row.selectedKey)
  if (c) _applyBulkCandidate(row, c)
}

const copyPlanToActual = () => {
  bulkRows.value.forEach((row) => {
    if (row.planQty > 0) row.qty = row.planQty
  })
}

const addBulkRow = () => {
  bulkRows.value.push(createBulkRow())
}

const removeBulkRow = (i) => {
  bulkRows.value.splice(i, 1)
  if (bulkRows.value.length === 0) bulkRows.value.push(createBulkRow())
}

const clearBulkRows = () => {
  bulkRows.value = [createBulkRow()]
}

const submitBulk = async () => {
  if (!canEdit.value) return

  const toRegister = bulkRows.value.filter((r) => {
    const hasProductCode = Boolean(String(r.productCode || r.barcode || '').trim())
    const hasQty = Number(r.qty || 0) > 0
    return hasProductCode && hasQty && !r.result
  })
  if (toRegister.length === 0) {
    alert('登録可能な行がありません。品番と入荷数を確認してください。')
    return
  }

  bulkSubmitting.value = true
  let successCount = 0
  let errorCount = 0

  for (const row of toRegister) {
    try {
      await api.purchaseActuals.register({
        process_id: row.processId ? Number(row.processId) : null,
        product_code: row.productCode,
        qty: Number(row.qty),
        arrival_date: arrivalDate.value,
        supplier_id: bulkSupplierId.value ? Number(bulkSupplierId.value) : null,
        line_id: row.lineId ? Number(row.lineId) : (bulkLineId.value ? Number(bulkLineId.value) : null),
        operator_name: operatorName.value || '',
      })
      row.result = 'ok'
      successCount++
    } catch (e) {
      row.result = 'error'
      row.error = e?.response?.data?.detail || '登録失敗'
      errorCount++
    }
  }

  bulkSubmitting.value = false
  alert(`登録完了: ${successCount}件成功${errorCount > 0 ? `、${errorCount}件失敗` : ''}`)

  if (successCount > 0) {
    bulkRows.value = bulkRows.value.filter((r) => r.result !== 'ok')
    if (bulkRows.value.length === 0) clearBulkRows()
  }
}

// ── 共通ユーティリティ ─────────────────────────
const displayNum = (value) => {
  const n = Number(value || 0)
  if (!n) return ''
  return n.toLocaleString()
}
const formatDate = (value) => {
  if (!value) return ''
  return String(value).replace(/-/g, '/')
}
const getMetric = (row, keys = []) => {
  for (const key of keys) {
    if (row && Object.prototype.hasOwnProperty.call(row, key) && row[key] !== null && row[key] !== undefined) {
      return row[key]
    }
  }
  return 0
}
const isHoliday = (value) => {
  if (!value) return false
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return false
  const day = d.getDay()
  return day === 0 || day === 6
}
const normalizeArrivalDate = () => {
  const raw = String(arrivalDate.value || '').trim()
  if (!raw) return

  const digits = raw.replace(/\D/g, '')
  const currentYear = new Date().getFullYear()
  let year = currentYear
  let month = null
  let day = null

  if (digits.length === 3) {
    month = Number(digits.slice(0, 1))
    day = Number(digits.slice(1, 3))
  } else if (digits.length === 4) {
    month = Number(digits.slice(0, 2))
    day = Number(digits.slice(2, 4))
  } else if (digits.length === 8) {
    year = Number(digits.slice(0, 4))
    month = Number(digits.slice(4, 6))
    day = Number(digits.slice(6, 8))
  } else {
    return
  }

  if (!month || !day || month < 1 || month > 12 || day < 1 || day > 31) return
  const d = new Date(year, month - 1, day)
  if (d.getFullYear() !== year || d.getMonth() + 1 !== month || d.getDate() !== day) return

  const mm = String(month).padStart(2, '0')
  const dd = String(day).padStart(2, '0')
  arrivalDate.value = `${year}/${mm}/${dd}`
}

onMounted(async () => {
  try {
    await ensureAuth()
    const user = authState.user
    operatorName.value = (user?.last_name && user?.first_name)
      ? `${user.last_name} ${user.first_name}`.trim()
      : (user?.username || user?.email || '')

    const [supplierRes, lineRes, processRes] = await Promise.all([
      api.suppliers.getSuppliers(),
      api.lines.getLines({ page_size: 500 }),
      api.processes.getProcesses({ is_active: true }),
    ])
    suppliers.value = supplierRes.data?.results || supplierRes.data || []
    lines.value = lineRes.data?.results || lineRes.data || []
    processes.value = processRes.data?.results || processRes.data || []
    await nextTick()
    barcodeInputRef.value?.focus()
    await loadProgress()
  } catch (e) {
    console.error('初期読込失敗:', e)
    alert('初期データの取得に失敗しました。')
  }
})
</script>

<style scoped>
.frame { background: #cfd2d3; padding: 8px; border: 1px solid #aeb4b8; min-height: 100%; }
.top-bar { margin-bottom: 6px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 8px; }
.toolbar-field { display: flex; align-items: center; gap: 6px; }
.toolbar-field span { background: #4f6f82; color: #fff; padding: 4px 10px; }
.tabs { border-bottom: 1px solid #9aa3a9; margin-bottom: 8px; }
.tab { border: 1px solid #9aa3a9; border-bottom: none; background: #d6d6d6; padding: 4px 10px; margin-right: 4px; cursor: pointer; }
.tab.active { background: #efefef; }
.content { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; align-items: start; }
.left-pane { min-width: 0; }
.right-pane { border: 1px solid #8d9498; background: #bfc1c2; padding: 8px; min-height: 420px; }
.panel { border: 1px solid #8d9498; background: #bfc1c2; padding: 8px; margin-bottom: 8px; }
.section-title { background: #4f6f82; color: #fff; padding: 3px 8px; margin: -8px -8px 8px; font-weight: 700; }
.row { display: grid; grid-template-columns: 80px 1fr; gap: 4px; margin-bottom: 4px; }
.row.row-3 { grid-template-columns: 80px 70px 1fr; }
.row label { background: #4f6f82; color: #fff; text-align: center; padding: 3px; }
.row input, .row select, .row textarea, .toolbar input, .toolbar select {
  border: 1px solid #9ca3af; background: #f5f2bc; padding: 4px 6px; font-size: 13px;
}
.row input[readonly] { background: #e6e6e6; }
.candidate-wrap { margin-top: 10px; border: 1px solid #8a8f92; background: #d2d2d2; }
.candidate-title { background: #4f6c7d; color: #fff; padding: 4px 8px; font-weight: 700; }
.candidate-table { width: 100%; border-collapse: collapse; }
.candidate-table th, .candidate-table td { border: 1px solid #8a8f92; padding: 3px 6px; background: #ecebd2; font-size: 12px; }
.candidate-table thead th { background: #4f6c7d; color: #fff; }
.candidate-table tbody tr { cursor: pointer; }
.candidate-table tbody tr.selected td { background: #cbe8ff; }
.actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
.btn { border: 1px solid #6d7478; background: #e5e5e5; padding: 4px 10px; font-weight: 700; cursor: pointer; }
.btn:disabled { opacity: 0.5; cursor: default; }
.btn.primary { background: #d7f0ff; }
.progress-table { width: 100%; border-collapse: collapse; background: #efefef; }
.progress-table th, .progress-table td { border: 1px solid #8a8f92; padding: 3px 6px; font-size: 12px; }
.progress-table th { background: #4f6f82; color: #fff; text-align: center; }
.progress-table tr.holiday td { background: #ffe6e6; }
.progress-table td.holidayText { color: #d60000; font-weight: 700; }
.negative { color: #c00; font-weight: 700; }

/* 一括タブ */
.bulk-section { border: 1px solid #8d9498; background: #bfc1c2; padding: 8px; }
.bulk-header { margin-bottom: 8px; }
.bulk-header-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.bulk-label-tag { background: #4f6f82; color: #fff; padding: 4px 10px; white-space: nowrap; }
.bulk-supplier-select { border: 1px solid #9ca3af; background: #f5f2bc; padding: 4px 6px; font-size: 13px; min-width: 200px; }
.bulk-encoding-select { border: 1px solid #9ca3af; background: #f5f2bc; padding: 4px 6px; font-size: 13px; width: 120px; }
.bulk-line-input { border: 1px solid #9ca3af; background: #e6e6e6; padding: 4px 6px; font-size: 13px; flex: 1; min-width: 150px; max-width: 280px; }
.bulk-date-input { border: 1px solid #9ca3af; background: #f5f2bc; padding: 4px 6px; font-size: 13px; width: 110px; }
.bulk-date-active { background: #c9e8ff; }
.bulk-operator-input { border: 1px solid #9ca3af; background: #e6e6e6; padding: 4px 6px; font-size: 13px; width: 120px; }
.bulk-import-note { font-size: 12px; color: #475569; }
.bulk-table { width: 100%; border-collapse: collapse; background: #efefef; }
.bulk-table th { background: #4f6f82; color: #fff; padding: 4px 6px; font-size: 12px; text-align: center; white-space: nowrap; }
.bulk-table td { border: 1px solid #8a8f92; padding: 3px 4px; font-size: 12px; }
.bulk-table tr.row-ok td { background: #d4edda; }
.bulk-table tr.row-error td { background: #f8d7da; }
.bulk-table tr.row-warn td { background: #fff3cd; }
.col-no { width: 32px; text-align: center; }
.col-code { width: 180px; }
.col-name { }
.col-qty { width: 80px; }
.col-date-group { background: #3a5a6e; text-align: center; font-size: 11px; padding: 2px 4px; }
.col-date { width: 46px; text-align: center; font-size: 11px; white-space: nowrap; }
.col-status { width: 36px; text-align: center; }
.cell-actual { background: #d4edda; font-weight: 700; color: #155724; }
.text-right { text-align: right; }
.code-input { width: 100%; border: 1px solid #9ca3af; background: #f5f2bc; padding: 3px 5px; font-size: 12px; box-sizing: border-box; }
.code-input[readonly] { background: #e6e6e6; }
.candidate-select { width: 100%; border: 1px solid #f59e0b; background: #fffbeb; padding: 2px 4px; font-size: 11px; margin-top: 2px; box-sizing: border-box; }
.qty-input { width: 72px; border: 1px solid #9ca3af; background: #f5f2bc; padding: 3px 5px; font-size: 12px; text-align: right; }
.remarks-input { width: 100%; border: 1px solid #9ca3af; background: #f5f2bc; padding: 3px 5px; font-size: 12px; box-sizing: border-box; }
.icon-ok { color: #198754; font-weight: 700; }
.icon-error { color: #c00; font-weight: 700; cursor: help; }
.icon-warn { color: #b45309; font-weight: 700; cursor: help; }
.btn-remove { border: 1px solid #888; background: #f0c0c0; padding: 1px 5px; font-size: 11px; cursor: pointer; }
.bulk-table-footer { display: flex; align-items: center; gap: 12px; margin-top: 6px; }
.bulk-count { font-size: 12px; color: #555; }

.footer-strip {
  margin-top: 8px;
  background: #5f7d8f;
  color: #fff;
  display: flex;
  justify-content: space-between;
  padding: 4px 10px;
  font-weight: 700;
}
@media (max-width: 1100px) {
  .content { grid-template-columns: 1fr; }
}
</style>

