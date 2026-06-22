<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">納入予定</h1>
      <div class="page-actions">
        <select v-model="selectedSupplier">
          <option value="">-- 仕入先 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">
            {{ s.supplier_code }} {{ s.supplier_name }}
          </option>
        </select>
        <input type="date" v-model="targetDate" />
        <div class="btn-group">
          <span class="filter-label">G:</span>
          <button :class="['btn-filter', { active: filterG === '' }]" @click="filterG = ''">全</button>
          <button :class="['btn-filter', { active: filterG === 'yes' }]" @click="filterG = 'yes'">有</button>
          <button :class="['btn-filter', { active: filterG === 'no' }]" @click="filterG = 'no'">無</button>
        </div>
        <button class="btn-excel" :disabled="loadingTemplate" @click="downloadTemplate">
          {{ loadingTemplate ? 'テンプレ作成中...' : '納品リストテンプレ出力' }}
        </button>
        <button class="btn-progress" :disabled="loadingProgressExcel || !selectedSupplier" @click="downloadProgressExcel">
          {{ loadingProgressExcel ? '作成中...' : '進度表Excel' }}
        </button>
        <button class="btn-progress" :disabled="loadingProgressPdf || !selectedSupplier" @click="downloadProgressPdf">
          {{ loadingProgressPdf ? '作成中...' : '進度表PDF' }}
        </button>
        <button class="btn-delivery-note" :disabled="loadingDeliveryNote || !selectedSupplier" @click="downloadDeliveryNotePdf">
          {{ loadingDeliveryNote ? '作成中...' : '納品書PDF' }}
        </button>
        <label class="btn-upload">
          返送Excel取込
          <input ref="fileInputRef" type="file" accept=".xlsx,.xls" @change="onFileChange" style="display:none" />
        </label>
      </div>
    </div>

    <div class="page-content">
      <div v-if="errors.length" class="error-box">
        <div v-for="(msg, idx) in errors" :key="`err-${idx}`">{{ msg }}</div>
      </div>

      <table v-if="rows.length" class="data-table">
        <thead>
          <tr>
            <th>品番</th>
            <th>品名</th>
            <th class="num">数量</th>
            <th>納品日</th>
            <th>仕入先コード</th>
            <th>伝票番号</th>
            <th>備考</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.product_id">
            <td>{{ r.product_code }}</td>
            <td>{{ r.product_name }}</td>
            <td class="num"><input type="number" v-model.number="r.received_qty" min="0" class="input-qty" /></td>
            <td>{{ r.delivery_date }}</td>
            <td>{{ r.supplier_code }}</td>
            <td>{{ r.slip_no }}</td>
            <td><input v-model="r.note" class="input-note" /></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="no-data">テンプレ出力または納品リストExcelを取り込んでください。</div>

      <div v-if="rows.length" class="form-actions">
        <button class="btn-success" :disabled="saving" @click="saveSchedule">納入予定保存</button>
      </div>

      <section class="rule-box">
        <h2 class="rule-title">導入ルール</h2>
        <ul class="rule-list">
          <li>テンプレ出力前に「仕入先」を選択してください。テンプレには対象品番・品名が入ります。</li>
          <li>取込ヘッダーは「品番 / 品名 / 数量 / 納品日 / 仕入先コード / 伝票番号」を使用してください。</li>
          <li class="rule-important">納品日は `YYYY-MM-DD` / `YYYY/MM/DD` / `YYYY/M/D` 形式のみ取込可能です（例: 2026-06-08, 2026/06/08, 2026/6/8）。</li>
          <li class="rule-important">返送Excel内の納品日は全行同一、かつ画面の対象日と一致している必要があります。</li>
          <li class="rule-important">数量が空白の行は取込時に除外されます（保存しません）。</li>
          <li class="rule-important">数量が0の行は前回取り込んだ同日同製品の計画数を取消として保存され、同日同製品の計画数量を0へ上書きします。</li>
          <li>数量が1以上の行は計画として保存されます。</li>
          <li>再導入時は同日同製品のみ上書きし、他製品の計画は保持されます。</li>
          <li>マイナス数量はエラーです（0以上を入力）。</li>
        </ul>
      </section>

      <section class="rule-box">
        <h2 class="rule-title">修正・取消・変更のやり方</h2>
        <ol class="howto-list">
          <li>修正したい時は、同じ仕入先・同じ日付を選択してExcelを再取込し、納入予定保存を押します。</li>
          <li>数量を変更したい時は、対象製品の数量を新しい値（1以上）で取込して保存します。</li>
          <li>取消したい時は、対象製品の数量を0で取込して保存します。</li>
          <li>空白行は除外されるため、空白では取消になりません（取消は必ず0を入力）。</li>
        </ol>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

const suppliers = ref([])
const selectedSupplier = ref('')
const targetDate = ref(new Date().toISOString().slice(0, 10))
const loadingTemplate = ref(false)
const loadingProgressExcel = ref(false)
const loadingProgressPdf = ref(false)
const loadingDeliveryNote = ref(false)
const saving = ref(false)
const rows = ref([])
const errors = ref([])
const fileInputRef = ref(null)
const filterG = ref('')

watch(selectedSupplier, (id) => {
  if (!id) { filterG.value = ''; return }
  const s = suppliers.value.find((sup) => sup.id === id)
  if (!s) { filterG.value = ''; return }
  if (s.supplier_type === 'outsource') filterG.value = 'yes'
  else if (s.supplier_type === 'purchase') filterG.value = 'no'
  else filterG.value = ''
})

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) =>
    (a.supplier_code || '').localeCompare(b.supplier_code || '')
  )
}

const fetchTemplateProducts = async () => {
  const res = await api.client.get('/purchase-receiving/delivery-list-template/', {
    params: { supplier_id: selectedSupplier.value },
  })
  return res.data
}

const saveWorkbookFile = async (wb, filename) => {
  try {
    if (window?.showSaveFilePicker) {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{ description: 'Excel', accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] } }],
      })
      const stream = await handle.createWritable()
      const buf = XLSX.write(wb, { type: 'array', bookType: 'xlsx' })
      await stream.write(buf)
      await stream.close()
      return
    }
  } catch (_) {
    // picker cancel fallback
  }
  XLSX.writeFile(wb, filename)
}

const downloadTemplate = async () => {
  if (!selectedSupplier.value) {
    alert('先に仕入先を選択してください。')
    return
  }
  loadingTemplate.value = true
  try {
    const res = await api.client.get('/purchase-receiving/delivery-list-excel/', {
      params: { supplier_id: selectedSupplier.value, target_date: targetDate.value, g_filter: filterG.value },
      responseType: 'blob',
    })
    const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
    const code = supplier ? supplier.supplier_code : ''
    const filename = `納品リスト_${code}_${targetDate.value}.xlsx`

    if (window?.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: filename,
          types: [{ description: 'Excel', accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] } }],
        })
        const stream = await handle.createWritable()
        await stream.write(res.data)
        await stream.close()
        return
      } catch (_) { /* picker cancel fallback */ }
    }
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    const detail = e?.response?.data?.detail
    alert(`納品リストテンプレ出力に失敗しました。${detail ? `\n${detail}` : ''}`)
  } finally {
    loadingTemplate.value = false
  }
}

const _downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const downloadProgressExcel = async () => {
  if (!selectedSupplier.value) return
  loadingProgressExcel.value = true
  try {
    const res = await api.client.get('/purchase-receiving/progress-excel/', {
      params: { supplier_id: selectedSupplier.value },
      responseType: 'blob',
    })
    const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
    const code = supplier ? supplier.supplier_code : ''
    _downloadBlob(res.data, `進度表_${code}_${targetDate.value}.xlsx`)
  } catch (e) {
    alert('進度表Excelの出力に失敗しました。')
  } finally {
    loadingProgressExcel.value = false
  }
}

const downloadProgressPdf = async () => {
  if (!selectedSupplier.value) return
  loadingProgressPdf.value = true
  try {
    const res = await api.client.get('/purchase-receiving/progress-pdf/', {
      params: { supplier_id: selectedSupplier.value },
      responseType: 'blob',
    })
    const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
    const code = supplier ? supplier.supplier_code : ''
    _downloadBlob(res.data, `進度表_${code}_${targetDate.value}.pdf`)
  } catch (e) {
    alert('進度表PDFの出力に失敗しました。')
  } finally {
    loadingProgressPdf.value = false
  }
}

const downloadDeliveryNotePdf = async () => {
  if (!selectedSupplier.value) return
  loadingDeliveryNote.value = true
  try {
    const res = await api.client.get('/purchase-receiving/delivery-note-pdf/', {
      params: { supplier_id: selectedSupplier.value, target_date: targetDate.value, g_filter: filterG.value },
      responseType: 'blob',
    })
    const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
    const code = supplier ? supplier.supplier_code : ''
    _downloadBlob(res.data, `外作納品書_${code}_${targetDate.value}.pdf`)
  } catch (e) {
    alert('納品書PDFの出力に失敗しました。')
  } finally {
    loadingDeliveryNote.value = false
  }
}

const normalizeHeader = (v) => String(v || '').trim().replace(/\s/g, '')
const readCell = (row, map, name) => row[map[name] ?? -1]
const DATE_PATTERN = /^(\d{4})([-/])(\d{1,2})\2(\d{1,2})$/

const formatNormalizedDate = (year, month, day) => `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`

const buildDateResult = (year, month, day, fallbackValue) => {
  if (
    !Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day) ||
    month < 1 || month > 12 || day < 1 || day > 31
  ) {
    return { blank: false, valid: false, value: fallbackValue }
  }
  return { blank: false, valid: true, value: formatNormalizedDate(year, month, day) }
}

const parseDeliveryDateStrict = (v) => {
  if (v instanceof Date && !Number.isNaN(v.getTime())) {
    return buildDateResult(v.getFullYear(), v.getMonth() + 1, v.getDate(), String(v))
  }
  if (typeof v === 'number' && Number.isFinite(v)) {
    const parsed = XLSX.SSF.parse_date_code(v)
    if (!parsed) return { blank: false, valid: false, value: String(v) }
    return buildDateResult(parsed.y, parsed.m, parsed.d, String(v))
  }
  const raw = String(v ?? '').trim()
  if (!raw) return { blank: true, valid: false, value: '' }
  const match = raw.match(DATE_PATTERN)
  if (!match) return { blank: false, valid: false, value: raw }
  return buildDateResult(Number(match[1]), Number(match[3]), Number(match[4]), raw)
}

const parseQty = (v) => {
  const raw = String(v ?? '').trim()
  if (raw === '') return { blank: true, qty: 0, invalid: false }
  const n = Number(raw)
  if (!Number.isFinite(n)) return { blank: false, qty: 0, invalid: true }
  return { blank: false, qty: Math.floor(n), invalid: false }
}

const onFileChange = async (event) => {
  const file = event.target?.files?.[0]
  if (!file) return
  if (!selectedSupplier.value) {
    alert('先に仕入先を選択してください。')
    if (fileInputRef.value) fileInputRef.value.value = ''
    return
  }
  rows.value = []
  errors.value = []
  try {
    const data = await fetchTemplateProducts()
    const productMap = new Map((data.items || []).map((p) => [String(p.product_code || '').trim().toUpperCase(), p]))
    const supplierCode = String(data?.supplier?.supplier_code || '').trim().toUpperCase()

    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array' })
    const sheet = wb.Sheets[wb.SheetNames[0]]
    const matrix = XLSX.utils.sheet_to_json(sheet, { header: 1, blankrows: false })
    if (!matrix.length) {
      errors.value = ['Excelにデータがありません。']
      return
    }
    const headers = (matrix[0] || []).map(normalizeHeader)
    const idx = {}
    headers.forEach((h, i) => { idx[h] = i })
    const required = ['品番', '品名', '数量', '納品日', '仕入先コード', '伝票番号']
    const missing = required.filter((h) => idx[h] === undefined)
    if (missing.length) {
      errors.value = [`ヘッダー不足: ${missing.join(', ')}`]
      return
    }

    const grouped = new Map()
    const rowErrors = []
    const deliveryDateErrors = []
    const deliveryDates = new Set()
    for (let i = 1; i < matrix.length; i += 1) {
      const row = matrix[i]
      const rowNo = i + 1
      const productCode = String(readCell(row, idx, '品番') || '').trim().toUpperCase()
      if (!productCode) continue

      const qtyInfo = parseQty(readCell(row, idx, '数量'))
      const deliveryDateInfo = parseDeliveryDateStrict(readCell(row, idx, '納品日'))
      const supplierCodeRaw = String(readCell(row, idx, '仕入先コード') || '').trim().toUpperCase()
      const slipNo = String(readCell(row, idx, '伝票番号') || '').trim()

      if (deliveryDateInfo.blank) {
        deliveryDateErrors.push(`${rowNo}行目: 納品日は必須です。YYYY-MM-DD / YYYY/MM/DD / YYYY/M/D 形式で入力してください。`)
        continue
      }
      if (!deliveryDateInfo.valid) {
        deliveryDateErrors.push(`${rowNo}行目: 納品日はYYYY-MM-DD / YYYY/MM/DD / YYYY/M/D 形式のみ取込可能です (${deliveryDateInfo.value})`)
        continue
      }
      deliveryDates.add(deliveryDateInfo.value)

      if (!productMap.has(productCode)) {
        rowErrors.push(`${rowNo}行目: 品番が対象外です (${productCode})`)
        continue
      }
      if (qtyInfo.blank) {
        // 数量空白行は除外して処理
        continue
      }
      if (qtyInfo.invalid || qtyInfo.qty < 0) {
        rowErrors.push(`${rowNo}行目: 数量は0以上を入力してください (${productCode})`)
        continue
      }
      if (supplierCodeRaw && supplierCode && supplierCodeRaw !== supplierCode) {
        rowErrors.push(`${rowNo}行目: 仕入先コードが選択中と不一致です (${supplierCodeRaw})`)
        continue
      }
      const product = productMap.get(productCode)
      const key = product.product_id
      if (!grouped.has(key)) {
        grouped.set(key, {
          product_id: product.product_id,
          product_code: product.product_code,
          product_name: product.product_name,
          received_qty: 0,
          delivery_date: deliveryDateInfo.value,
          supplier_code: supplierCode,
          slip_no: slipNo,
          note: '',
        })
      }
      const current = grouped.get(key)
      current.received_qty += qtyInfo.qty
      if (!current.slip_no && slipNo) current.slip_no = slipNo
    }

    if (deliveryDateErrors.length) {
      errors.value = deliveryDateErrors
      rows.value = []
      return
    }

    if (deliveryDates.size > 1) {
      errors.value = ['返送Excel内の納品日は全行同一である必要があります。複数の日付が含まれています。']
      rows.value = []
      return
    }

    const [importDeliveryDate] = [...deliveryDates]
    if (importDeliveryDate && importDeliveryDate !== targetDate.value) {
      errors.value = [`返送Excelの納品日 (${importDeliveryDate}) が画面の対象日 (${targetDate.value}) と一致していません。`]
      rows.value = []
      return
    }

    rows.value = [...grouped.values()].sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
    errors.value = rowErrors
  } catch (e) {
    alert('納品リスト取込に失敗しました。')
  } finally {
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

const saveSchedule = async () => {
  const targets = rows.value.filter((r) => Number(r.received_qty) >= 0)
  if (!selectedSupplier.value || !targets.length) {
    alert('保存対象がありません。')
    return
  }
  saving.value = true
  try {
    await api.client.post('/purchase-delivery-schedules/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      items: targets.map((r) => ({ product_id: r.product_id, qty: r.received_qty })),
    })
    alert('納入予定を保存しました。')
    rows.value = []
    errors.value = []
  } catch (e) {
    alert('納入予定の保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

onMounted(fetchSuppliers)
</script>

<style scoped>
.btn-group { display: flex; align-items: center; gap: 2px; }
.filter-label { color: #475569; font-weight: 600; margin-right: 2px; font-size: 13px; }
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
.btn-progress {
  padding: 6px 12px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.btn-progress:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-delivery-note {
  padding: 6px 12px;
  background: #10b981;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.btn-delivery-note:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-upload {
  padding: 6px 12px;
  background: #f59e0b;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.page-content { display: grid; gap: 10px; }
.error-box {
  background: #fff1f2;
  color: #be123c;
  border: 1px solid #fecdd3;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
}
.form-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.rule-box {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #d6d3c9;
  border-radius: 6px;
  background: #f8f6ea;
}
.rule-title {
  margin: 0 0 6px 0;
  font-size: 14px;
  font-weight: 700;
}
.rule-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
  font-size: 13px;
  line-height: 1.5;
}
.howto-list {
  margin: 0;
  padding-left: 20px;
  display: grid;
  gap: 4px;
  font-size: 13px;
  line-height: 1.5;
}
.rule-important {
  color: #b91c1c;
  font-size: 16px;
  font-weight: 700;
}
</style>
