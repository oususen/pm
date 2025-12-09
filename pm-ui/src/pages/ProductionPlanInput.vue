<template>
  <div class="plan-container">
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="field">
          <label>処理区分</label>
          <select v-model="mode">
            <option value="plan">1:生産計画</option>
            <option value="result">2:実績</option>
          </select>
        </div>
        <div class="field">
          <label>ライン</label>
          <select v-model="selectedLine" @change="loadData">
            <option value="">すべて</option>
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
        <button class="btn" @click="savePlan" :disabled="!rows.length">保存（ダミー）</button>
      </div>
    </div>

    <div class="grid-wrapper">
      <table class="plan-grid">
        <thead>
          <tr class="head-level1">
            <th rowspan="2" class="sticky-col code-col">品番</th>
            <th rowspan="2" class="sticky-col name-col">品名</th>
            <th v-for="c in dateColumns" :key="c.key" colspan="5" class="date-head">
              {{ c.label }}
            </th>
          </tr>
          <tr class="head-level2">
            <template v-for="c in dateColumns" :key="c.key">
              <th class="mini">需要</th>
              <th class="mini">実績</th>
              <th class="mini">在庫</th>
              <th class="mini">計画</th>
              <th class="mini">計画在庫</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.id">
            <td class="sticky-col code-col">
              <input type="text" v-model="row.product_code" />
            </td>
            <td class="sticky-col name-col">
              <input type="text" v-model="row.product_name" />
            </td>
            <template v-for="c in dateColumns" :key="c.key">
              <td class="num">
                <span class="readonly-value">{{ row.daily[c.key].demand || 0 }}</span>
              </td>
              <td class="num">
                <span class="readonly-value">{{ row.daily[c.key].actual || 0 }}</span>
              </td>
              <td class="num stock">
                <span class="readonly-value">{{ row.daily[c.key].stock || 0 }}</span>
              </td>
              <td class="num plan">
                <input type="number" v-model.number="row.daily[c.key].plan" @keydown.up.prevent @keydown.down.prevent />
              </td>
              <td class="num stock-plan">
                <span class="readonly-value">{{ row.daily[c.key].plan_stock || 0 }}</span>
              </td>
            </template>
          </tr>
          <tr v-if="!filteredRows.length">
            <td :colspan="2 + dateColumns.length * 5" class="no-data">行を追加してください</td>
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

const mode = ref('plan')
const selectedLine = ref('')
const startDate = ref(new Date().toISOString().slice(0, 10))
const horizonDays = ref(60) // 表示日から2か月（約60日）
const keyword = ref('')

const lines = ref([])
const products = ref([])
const rows = ref([])
let tempId = 1

const dateColumns = computed(() => {
  const cols = []
  const base = new Date(startDate.value)
  for (let i = 0; i < horizonDays.value; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i)
    const label = `${d.getMonth() + 1}/${d.getDate()}(${['日','月','火','水','木','金','土'][d.getDay()]})`
    const key = d.toISOString().slice(0, 10)
    cols.push({ key, label })
  }
  return cols
})

const initDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = { demand: 0, actual: 0, stock: 0, plan: 0, plan_stock: 0 }
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

const savePlan = () => {
  alert('デモ画面のため保存処理は未実装です。')
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
  // 再初期化は既存データの初期化だけ（簡易対応）
  rows.value.forEach((r) => {
    r.daily = initDaily()
  })
}

const loadData = async () => {
  rows.value = []
  try {
    const res = await api.lineDemands.list()
    const data = (res.data && (res.data.results || res.data)) || []
    const filtered = data.filter((d) => {
      const okLine = !selectedLine.value || `${d.line}` === `${selectedLine.value}`
      const inRange = !d.plan_date || (d.plan_date >= dateColumns.value[0].key && d.plan_date <= dateColumns.value[dateColumns.value.length - 1].key)
      return okLine && inRange
    })
    const productMap = new Map(products.value.map((p) => [p.id, p]))
    const uniqueProducts = Array.from(
      new Map(
        filtered
          .map((d) => {
            const p = productMap.get(d.product)
            if (!d.product || !p) return null
            if (p.is_phantom) return null
            return [d.product, { id: d.product, code: p.product_code || d.product_code || '', name: p.product_name || d.product_name || '' }]
          })
          .filter(Boolean)
      ).values()
    )
    if (uniqueProducts.length === 0) {
      addRow()
      return
    }
    rows.value = uniqueProducts.map((p) => ({
      id: `auto-${p.id}`,
      product_id: p.id,
      product_code: p.code,
      product_name: p.name,
      daily: initDaily(),
    }))
  } catch (e) {
    console.error('ライン需要取得エラー', e)
    if (!rows.value.length) addRow()
  }
}

const fetchLines = async () => {
  const res = await api.lines.getLines()
  lines.value = res.data.results || res.data || []
}
const fetchProducts = async () => {
  products.value = (await api.products.getAllProducts())
    .filter((p) => !p.is_phantom)
    .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
}

onMounted(async () => {
  try {
    await Promise.all([fetchLines(), fetchProducts()])
    loadData()
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})
</script>

<style scoped>
.plan-container {
  padding: 8px 10px 14px;
  background: #eef2f6;
  font-size: 13px;
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
}
.plan-grid th,
.plan-grid td {
  border: 1px solid #d7dfe8;
  padding: 4px 6px;
  white-space: nowrap;
}
.head-level1 {
  background: #d7e2f5;
}
.head-level2 {
  background: #eef2f7;
}
.date-head {
  text-align: center;
  font-weight: 700;
}
.mini {
  text-align: center;
  font-size: 12px;
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
.code-col {
  width: 120px;
  min-width: 120px;
  max-width: 120px;
}
.name-col {
  left: 120px;
  width: 100px;
  min-width: 100px;
  max-width: 100px;
  border-right: 2px solid #b5c1d2 !important;
}
.plan-grid input,
.plan-grid select {
  width: 100%;
  box-sizing: border-box;
  padding: 3px 4px;
  border: 1px solid #d1d5db;
  border-radius: 2px;
  font-size: 12px;
}
.num {
  text-align: right;
}
.num input {
  width: 40px;
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
  font-size: 12px;
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
</style>
