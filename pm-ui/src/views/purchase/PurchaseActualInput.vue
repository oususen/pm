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
      </div>

      <table class="bulk-table">
        <thead>
          <tr>
            <th class="col-no">#</th>
            <th class="col-code">品番</th>
            <th class="col-name">品名</th>
            <th class="col-qty">計画数</th>
            <th class="col-qty">入荷数</th>
            <th class="col-remarks">備考</th>
            <th class="col-status"></th>
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
            <td class="col-remarks">
              <input v-model.trim="row.remarks" type="text" class="remarks-input" />
            </td>
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
  qty: null,
  remarks: '',
  error: '',
  result: '',
})

const normalizeBulkPlanDate = () => {
  const raw = String(bulkPlanDate.value || '').trim()
  if (!raw) return
  const digits = raw.replace(/\D/g, '')
  const currentYear = new Date().getFullYear()
  let year = currentYear, month = null, day = null
  if (digits.length === 3) { month = Number(digits.slice(0, 1)); day = Number(digits.slice(1, 3)) }
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

const loadBulkItems = async () => {
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

  const toRegister = bulkRows.value.filter((r) => r.resolved && r.qty > 0 && !r.result)
  if (toRegister.length === 0) {
    alert('登録可能な行がありません。品番と入荷数を入力してください。')
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
        remarks: row.remarks || '',
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
      api.lines.getLines(),
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
.bulk-line-input { border: 1px solid #9ca3af; background: #e6e6e6; padding: 4px 6px; font-size: 13px; flex: 1; min-width: 150px; max-width: 280px; }
.bulk-date-input { border: 1px solid #9ca3af; background: #f5f2bc; padding: 4px 6px; font-size: 13px; width: 110px; }
.bulk-date-active { background: #c9e8ff; }
.bulk-operator-input { border: 1px solid #9ca3af; background: #e6e6e6; padding: 4px 6px; font-size: 13px; width: 120px; }
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
.col-remarks { }
.col-status { width: 36px; text-align: center; }
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
