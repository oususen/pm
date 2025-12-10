<template>
  <div class="plan-container">
    <h2 class="page-title">仕入れ計画</h2>

    <div class="toolbar">
      <div class="toolbar-left">
        <div class="field">
          <label>仕入先</label>
          <select v-model="selectedSupplier" @change="loadData">
            <option value="">すべて</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">
              {{ s.supplier_code }} - {{ s.supplier_name }}
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
            <option :value="60">60日</option>
            <option :value="30">30日</option>
            <option :value="14">14日</option>
          </select>
        </div>
        <div class="field">
          <label>検索</label>
          <input type="text" v-model="keyword" placeholder="品番/品名で絞り込み" />
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="addRow">新規行追加</button>
        <button class="btn" @click="resetRows" :disabled="!rows.length">クリア</button>
        <button class="btn" @click="savePlan" :disabled="!rows.length || !selectedSupplier">保存</button>
        <button class="btn primary" @click="doPickup" :disabled="!selectedSupplier">取り込み</button>
      </div>
    </div>

    <div class="grid-wrapper">
      <table class="plan-grid" :style="{ minWidth: tableMinWidth + 'px' }">
        <thead>
          <tr class="head-level1">
            <th rowspan="2" class="sticky-col number-col">No</th>
            <th rowspan="2" class="sticky-col code-col">品番</th>
            <th rowspan="2" class="sticky-col name-col">品名</th>
            <th
              v-for="c in dateColumns"
              :key="c.key"
              colspan="5"
              class="date-head day-end"
              :class="c.dayClass"
            >
              {{ c.label }}
            </th>
          </tr>
          <tr class="head-level2">
            <template v-for="c in dateColumns" :key="c.key">
              <th class="mini" :class="c.dayClass">需要</th>
              <th class="mini" :class="c.dayClass">実績</th>
              <th class="mini" :class="c.dayClass">在庫</th>
              <th class="mini" :class="c.dayClass">計画</th>
              <th class="mini day-end" :class="c.dayClass">計画在庫</th>
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
            <template v-for="c in dateColumns" :key="c.key">
              <td class="num" :class="c.dayClass">
                <span class="readonly-value">{{ row.daily[c.key].demand || 0 }}</span>
              </td>
              <td class="num" :class="c.dayClass">
                <span class="readonly-value">{{ row.daily[c.key].actual || 0 }}</span>
              </td>
              <td class="num stock" :class="c.dayClass">
                <span class="readonly-value">{{ row.daily[c.key].stock || 0 }}</span>
              </td>
              <td class="num plan" :class="c.dayClass">
                <input
                  type="text"
                  inputmode="decimal"
                  :value="row.daily[c.key].plan === 0 || row.daily[c.key].plan === '' || row.daily[c.key].plan == null ? '' : row.daily[c.key].plan"
                  @input="onPlanInput(row, c.key, $event.target.value)"
                  @keydown.up.prevent
                  @keydown.down.prevent
                />
              </td>
              <td class="num stock-plan day-end" :class="c.dayClass">
                <span class="readonly-value">{{ row.daily[c.key].plan_stock || 0 }}</span>
              </td>
            </template>
          </tr>
          <tr v-if="!filteredRows.length">
            <td :colspan="3 + dateColumns.length * 5" class="no-data">行を追加してください</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="footer-actions">
      <button class="btn-secondary">F1: 終了</button>
      <button class="btn-secondary">F3: クリア</button>
      <button class="btn-secondary">F5: 備考</button>
      <button class="btn-secondary">F10: 印刷</button>
      <button class="btn-secondary">F12: 更新</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'

const selectedSupplier = ref('')
const startDate = ref(new Date().toISOString().slice(0, 10))
const horizonDays = ref(60)
const keyword = ref('')

const suppliers = ref([])
const products = ref([])
const rows = ref([])
let tempId = 1

const endDate = computed(() => {
  const d = new Date(startDate.value)
  d.setDate(d.getDate() + horizonDays.value - 1)
  return d.toISOString().slice(0, 10)
})

const dateColumns = computed(() => {
  const cols = []
  const base = new Date(startDate.value)
  const weekday = ['日', '月', '火', '水', '木', '金', '土']
  for (let i = 0; i < horizonDays.value; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i)
    const day = d.getDay()
    const label = `${d.getMonth() + 1}/${d.getDate()}(${weekday[day]})`
    const key = d.toISOString().slice(0, 10)
    const dayClass = day === 0 ? 'sun' : day === 6 ? 'sat' : ''
    cols.push({ key, label, dayClass })
  }
  return cols
})

const tableMinWidth = computed(() => {
  const fixedColsWidth = 40 + 187 + 100
  const perDayWidth = 80 * 5
  return fixedColsWidth + dateColumns.value.length * perDayWidth
})

const initDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = { demand: 0, actual: 0, stock: 0, plan: '', plan_stock: 0 }
  })
  return daily
}

const addRow = () => {
  rows.value.push({
    id: `tmp-${tempId++}`,
    product_id: '',
    product_code: '',
    product_name: '',
    daily: initDaily(),
  })
}

const resetRows = () => {
  rows.value = []
}

const savePlan = async () => {
  if (!selectedSupplier.value) {
    alert('仕入先を選択してください。')
    return
  }
  const items = []
  rows.value.forEach((r) => {
    if (!r.product_id) return
    // 仕入れ用のprocess_idはダミー値（1固定）を使用
    const process_id = r.process_id || 1
    dateColumns.value.forEach((c) => {
      const daily = r.daily[c.key]
      items.push({
        product_id: r.product_id,
        process_id: process_id,
        plan_date: c.key,
        plan_qty: daily.plan === '' || daily.plan == null ? 0 : Number(daily.plan),
        actual_qty: Number(daily.actual || 0),
        stock_qty: Number(daily.stock || 0),
        planned_stock_qty: Number(daily.plan_stock || 0),
      })
    })
  })
  if (!items.length) {
    alert('保存するデータがありません。')
    return
  }
  try {
    // 仕入先IDをline_idとして使用（暫定）
    const res = await api.lineBacklogs.save({
      line_id: selectedSupplier.value,
      items,
    })
    console.info('保存結果', res.data)
    alert('保存しました。')
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました。')
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

const refreshDates = () => {
  rows.value.forEach((r) => {
    r.daily = initDaily()
  })
}

const loadData = async () => {
  rows.value = []
}

const onPlanInput = (row, dateKey, value) => {
  row.daily[dateKey].plan = value === '' ? '' : value
}

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = res.data.results || res.data || []
}

const fetchProducts = async () => {
  // 仕入れ対象製品を取得（sourcing_type='BUY'の部品）
  try {
    const bomItemsRes = await api.bomItems.getBOMItems({ sourcing_type: 'BUY' })
    const bomItems = bomItemsRes.data.results || bomItemsRes.data || []

    // 子製品のIDリストを取得
    const buyProductIds = new Set(bomItems.map(item => item.child_product))

    // 全製品から仕入れ対象のみをフィルタ
    const allProducts = await api.products.getAllProducts()
    products.value = allProducts
      .filter((p) => !p.is_phantom && buyProductIds.has(p.id))
      .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
  } catch (e) {
    console.error('仕入れ対象製品の取得エラー', e)
    products.value = []
  }
}

onMounted(async () => {
  try {
    await Promise.all([fetchSuppliers(), fetchProducts()])
    loadData()
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})

const doPickup = async () => {
  if (!selectedSupplier.value) {
    alert('仕入先を選択してください。')
    return
  }
  try {
    // 仕入先に紐づく既存バックログを取得（line_idに仕入先IDを流用）
    const res = await api.lineBacklogs.pickup({
      line_id: selectedSupplier.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    const data = res.data || []
    const grouped = new Map()
    data.forEach((d) => {
      if (!d.product) return
      const key = d.product
      if (!grouped.has(key)) {
        grouped.set(key, {
          id: `bk-${key}`,
          product_id: d.product,
          product_code: d.product_code || '',
          product_name: d.product_name || '',
          process_id: d.process || 1, // 仕入れ用ダミー値
          daily: initDaily(),
        })
      }
      const row = grouped.get(key)
      const dateKey = d.plan_date
      if (row.daily[dateKey]) {
        row.daily[dateKey].demand = Number(d.order_qty || 0)
        row.daily[dateKey].plan = d.plan_qty === null || d.plan_qty === undefined ? '' : d.plan_qty === 0 ? '' : d.plan_qty
        row.daily[dateKey].actual = Number(d.actual_qty || 0)
        row.daily[dateKey].stock = Number(d.stock_qty || 0)
        row.daily[dateKey].plan_stock = Number(d.planned_stock_qty || 0)
      }
    })

    rows.value = Array.from(grouped.values())
    if (!rows.value.length) {
      // データが無い場合は仕入れ対象製品の空行を自動追加
      products.value.forEach((p) => {
        rows.value.push({
          id: `prod-${p.id}`,
          product_id: p.id,
          product_code: p.product_code,
          product_name: p.product_name,
          process_id: 1, // 仕入れ用ダミー値
          daily: initDaily(),
        })
      })
    }
  } catch (e) {
    console.error('仕入れ計画 取り込みエラー', e)
    alert('取り込みに失敗しました。')
  }
}
</script>

<style scoped>
.plan-container {
  padding: 8px 10px 14px;
  background: #eef2f6;
  font-size: 13px;
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
  color: #1f2a44;
}
.page-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
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
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.grid-wrapper {
  margin-top: 10px;
  overflow-x: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.plan-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.plan-grid th,
.plan-grid td {
  border: 1px solid #d7dfe8;
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 1.288rem;
  font-weight: 500;
  color: #000;
}
.plan-grid th {
  font-weight: 700;
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
  min-width: 400px;
}
.mini {
  text-align: center;
  font-size: 12px;
  min-width: 80px;
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
  z-index: 4;
}
.number-col {
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  text-align: center;
}
.code-col {
  left: 40px;
  width: 187px;
  min-width: 187px;
  max-width: 187px;
}
.name-col {
  left: 227px;
  width: 100px;
  min-width: 100px;
  max-width: 100px;
  border-right: 2px solid #b5c1d2 !important;
}
.product-info {
  display: block;
  padding: 3px 4px;
  font-size: 1.288rem;
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
  font-size: 1.288rem;
  font-weight: 500;
  color: #000;
}
.num {
  text-align: right;
  min-width: 80px;
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
  font-size: 1.288rem;
  font-weight: 500;
  color: #000;
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
</style>
