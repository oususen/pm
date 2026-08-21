<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">手動注文入力</h1>
    </div>

    <div class="page-content">
      <div class="entry-form">
        <!-- 顧客選択 -->
        <div class="form-group">
          <div class="group-header">
            <label>顧客 *</label>
          </div>
          <div class="tile-grid customer-grid">
            <button
              v-for="c in customers"
              :key="c.id"
              type="button"
              class="select-tile"
              :class="{ active: form.customer_code === c.customer_code }"
              @click="form.customer_code = c.customer_code"
            >
              <div class="icon-badge">{{ c.customer_code?.slice(0, 2) || 'CU' }}</div>
              <div class="tile-main">{{ c.customer_code }}</div>
              <div class="tile-sub" :title="c.customer_name">{{ c.customer_name }}</div>
            </button>
          </div>
        </div>

        <!-- 受注タイプ -->
        <div class="form-group">
          <div class="group-header">
            <label>受注タイプ *</label>
          </div>
          <div class="tile-grid compact">
            <button
              v-for="t in orderTypes"
              :key="t.value"
              type="button"
              class="select-tile compact-tile"
              :class="{ active: form.order_type === t.value }"
              @click="form.order_type = t.value"
            >
              <div class="tile-content-row">
                <div class="icon-badge">{{ t.badge }}</div>
                <div class="tile-main">{{ t.label }}</div>
                <div class="tile-sub">{{ t.desc }}</div>
              </div>
            </button>
          </div>
        </div>

        <!-- 工場選択 (クボタのみ) -->
        <div v-if="isKubota" class="form-group">
          <div class="group-header">
            <label>工場 *</label>
          </div>
          <div class="tile-grid compact">
            <button
              v-for="f in factories"
              :key="f.value"
              type="button"
              class="select-tile compact-tile"
              :class="{ active: form.factory === f.value }"
              @click="form.factory = f.value"
            >
              <div class="tile-content-row">
                <div class="icon-badge">{{ f.badge }}</div>
                <div class="tile-main">{{ f.label }}</div>
              </div>
            </button>
          </div>
        </div>

        <!-- 明細行 -->
        <div class="form-group">
          <div class="group-header">
            <label>明細行</label>
            <button class="btn-add" @click="addLine">＋ 行追加</button>
          </div>
          <div class="lines-table-wrap">
            <table class="lines-table">
              <thead>
                <tr>
                  <th class="col-no">#</th>
                  <th class="col-product">製品コード *</th>
                  <th class="col-qty">数量 *</th>
                  <th class="col-date">納期 *</th>
                  <th v-if="showShipTo" class="col-shipto">納入先</th>
                  <th v-if="showInspection" class="col-insp">検査タイプ</th>
                  <th class="col-custno">顧客発注番号</th>
                  <th v-if="isTiera" class="col-ctable">C表No</th>
                  <th class="col-remark">備考</th>
                  <th class="col-action"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in form.lines" :key="idx">
                  <td class="col-no">{{ idx + 1 }}</td>
                  <td class="col-product">
                    <div class="product-input-wrap">
                      <input
                        v-model="line.product_code"
                        type="text"
                        placeholder="製品コード"
                        @input="onProductInput(idx)"
                        @blur="hideProductSuggestions(idx)"
                      />
                      <ul v-if="line._suggestions?.length" class="suggestions">
                        <li
                          v-for="p in line._suggestions"
                          :key="p.product_code"
                          @mousedown.prevent="selectProduct(idx, p)"
                        >
                          {{ p.product_code }} - {{ p.product_name }}
                        </li>
                      </ul>
                    </div>
                    <div v-if="line._product_name" class="product-name-hint">{{ line._product_name }}</div>
                  </td>
                  <td class="col-qty">
                    <input v-model="line.quantity" type="number" min="1" step="1" placeholder="数量" />
                  </td>
                  <td class="col-date">
                    <input v-model="line.due_date" type="date" />
                  </td>
                  <td v-if="showShipTo" class="col-shipto">
                    <input v-model="line.ship_to_code" type="text" placeholder="納入先コード" />
                  </td>
                  <td v-if="showInspection" class="col-insp">
                    <select v-model="line.inspection_type">
                      <option value="">-</option>
                      <option value="N">N</option>
                      <option value="NS">NS</option>
                      <option value="TS">TS</option>
                      <option value="$">$</option>
                    </select>
                  </td>
                  <td class="col-custno">
                    <input v-model="line.customer_order_no" type="text" placeholder="発注番号" />
                  </td>
                  <td v-if="isTiera" class="col-ctable">
                    <input v-model="line.c_table_no" type="text" placeholder="C表No" />
                  </td>
                  <td class="col-remark">
                    <input v-model="line.remark" type="text" placeholder="備考" />
                  </td>
                  <td class="col-action">
                    <button v-if="form.lines.length > 1" class="btn-remove" @click="removeLine(idx)">✕</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 送信 -->
        <div class="form-actions">
          <button class="btn-primary" :disabled="submitting" @click="submit">
            {{ submitting ? '登録中...' : '受注登録' }}
          </button>
        </div>

        <!-- 結果 -->
        <div v-if="result" class="result-section" :class="result.success ? 'success' : 'error'">
          <h3>{{ result.success ? '登録完了' : 'エラー' }}</h3>
          <template v-if="result.success">
            <ul>
              <li>ソースファイル: {{ result.source_file }}</li>
              <li>ステージングレコード: {{ result.staging_records }}件</li>
              <li>受注数: {{ result.orders }}件</li>
              <li>明細数: {{ result.lines }}件</li>
            </ul>
          </template>
          <p v-else class="error-msg">{{ result.error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/api/client'

const customers = ref([])
const submitting = ref(false)
const result = ref(null)
let productSearchTimer = null

const orderTypes = [
  { value: 'FIRM', label: 'ＦＩＲＭ', desc: '確定受注', badge: 'Ｆ' },
  { value: 'FORECAST', label: 'FORECAST', desc: '内示/予測', badge: 'Fc' },
]
const factories = [
  { value: 'SAKAI', label: '堺工場', badge: '堺' },
  { value: 'HIRAKATA', label: '枚方工場', badge: '枚' },
  { value: 'HIRAKATA_2027', label: '枚方(27年~)', badge: '27' },
  { value: 'KMT', label: 'KMT工場', badge: 'K' },
]

const createEmptyLine = () => ({
  product_code: '',
  quantity: '',
  due_date: '',
  ship_to_code: '',
  inspection_type: '',
  customer_order_no: '',
  c_table_no: '',
  remark: '',
  _suggestions: [],
  _product_name: '',
})

const form = reactive({
  customer_code: '',
  order_type: 'FIRM',
  factory: 'SAKAI',
  lines: [createEmptyLine()],
})

const isKubota = computed(() => form.customer_code === '000196')
const isTiera = computed(() => form.customer_code === '000001')
const showShipTo = computed(() => isKubota.value || (!isTiera.value && form.customer_code))
const showInspection = computed(() => isKubota.value)

const addLine = () => {
  const last = form.lines[form.lines.length - 1]
  const newLine = createEmptyLine()
  if (last) {
    newLine.due_date = last.due_date
    newLine.ship_to_code = last.ship_to_code
    newLine.inspection_type = last.inspection_type
  }
  form.lines.push(newLine)
}

const removeLine = (idx) => {
  form.lines.splice(idx, 1)
}

const onProductInput = (idx) => {
  const line = form.lines[idx]
  const code = (line.product_code || '').trim()
  line._product_name = ''
  if (productSearchTimer) clearTimeout(productSearchTimer)
  if (code.length < 2) {
    line._suggestions = []
    return
  }
  productSearchTimer = setTimeout(async () => {
    try {
      const res = await api.products.getProducts({ search: code, page_size: 10 })
      const items = res.data?.results || res.data || []
      line._suggestions = items.slice(0, 10)
    } catch {
      line._suggestions = []
    }
  }, 300)
}

const selectProduct = (idx, product) => {
  const line = form.lines[idx]
  line.product_code = product.product_code
  line._product_name = product.product_name || ''
  line._suggestions = []
}

const hideProductSuggestions = (idx) => {
  setTimeout(() => {
    form.lines[idx]._suggestions = []
  }, 200)
}

const submit = async () => {
  if (!form.customer_code) return alert('顧客を選択してください')
  if (!form.lines.length) return alert('明細行を追加してください')

  for (let i = 0; i < form.lines.length; i++) {
    const l = form.lines[i]
    if (!l.product_code?.trim()) return alert(`明細行${i + 1}: 製品コードを入力してください`)
    if (!l.quantity || Number(l.quantity) <= 0) return alert(`明細行${i + 1}: 数量を入力してください`)
    if (!l.due_date) return alert(`明細行${i + 1}: 納期を入力してください`)
  }

  submitting.value = true
  result.value = null

  try {
    const payload = {
      customer_code: form.customer_code,
      order_type: form.order_type,
      factory: isKubota.value ? form.factory : '',
      lines: form.lines.map(l => ({
        product_code: l.product_code.trim(),
        quantity: l.quantity,
        due_date: l.due_date,
        ship_to_code: l.ship_to_code || '',
        inspection_type: l.inspection_type || '',
        customer_order_no: l.customer_order_no || '',
        c_table_no: l.c_table_no || '',
        remark: l.remark || '',
      })),
    }

    const res = await api.staging.manualCreate(payload)
    result.value = res.data

    if (res.data.success) {
      form.lines = [createEmptyLine()]
    }
  } catch (e) {
    result.value = {
      success: false,
      error: e?.response?.data?.error || e.message || '登録に失敗しました',
    }
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await api.customers.getCustomers()
    customers.value = res.data?.results || res.data || []
  } catch {
    customers.value = []
  }
})
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { margin-bottom: 12px; }
.page-title { font-size: 18px; margin: 0; }
.entry-form { max-width: 1200px; }

.form-group { margin-bottom: 16px; }
.group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}
.group-header label { font-weight: 700; font-size: 14px; }
.btn-add {
  padding: 2px 10px;
  font-size: 13px;
  background: #284b8f;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.tile-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.customer-grid { gap: 6px; }
.select-tile {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  min-width: 110px;
}
.select-tile.active { border-color: #284b8f; background: #eef2ff; }
.select-tile .icon-badge {
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  display: inline-block;
  padding: 1px 5px;
  border-radius: 3px;
  margin-bottom: 2px;
}
.select-tile .tile-main { font-weight: 700; font-size: 13px; }
.select-tile .tile-sub { font-size: 11px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }

.compact .select-tile { min-width: auto; }
.tile-content-row { display: flex; align-items: center; gap: 6px; }

.lines-table-wrap { overflow: visible; min-height: 300px; }
.lines-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.lines-table th {
  background: #f8fafc;
  padding: 6px 8px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}
.lines-table td {
  padding: 4px 4px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
  position: relative;
}
.lines-table input,
.lines-table select {
  width: 100%;
  padding: 4px 6px;
  font-size: 13px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  box-sizing: border-box;
}
.lines-table input:focus,
.lines-table select:focus {
  outline: none;
  border-color: #284b8f;
}

.col-no { width: 30px; text-align: center; }
.col-product { min-width: 180px; }
.col-qty { width: 80px; }
.col-date { width: 130px; }
.col-shipto { width: 110px; }
.col-insp { width: 90px; }
.col-custno { width: 130px; }
.col-ctable { width: 100px; }
.col-remark { width: 120px; }
.col-action { width: 32px; text-align: center; }

.product-input-wrap { position: relative; }
.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 180px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.suggestions li {
  padding: 5px 8px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.suggestions li:hover { background: #eef2ff; }
.product-name-hint { font-size: 11px; color: #64748b; margin-top: 1px; }

.btn-remove {
  background: none;
  border: none;
  color: #dc2626;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 6px;
}

.form-actions { margin-top: 16px; }
.btn-primary {
  padding: 8px 24px;
  background: #284b8f;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.result-section {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 8px;
}
.result-section.success { background: #f0fdf4; border: 1px solid #86efac; }
.result-section.error { background: #fef2f2; border: 1px solid #fca5a5; }
.result-section h3 { margin: 0 0 6px; font-size: 15px; }
.result-section ul { margin: 4px 0 0 16px; padding: 0; }
.result-section li { font-size: 13px; }
.error-msg { color: #dc2626; font-size: 13px; }
</style>
