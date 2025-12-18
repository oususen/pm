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
        <button class="btn" @click="savePlan" :disabled="!rows.length || !selectedLine">保存</button>
        <button class="btn primary" @click="doPickup" :disabled="!selectedLine">取り込み</button>
        <button class="btn accent" @click="doProcessExpand" :disabled="!selectedLine || expanding">
          工程展開
        </button>
        <button class="btn accent" @click="goProcessGantt" :disabled="!selectedLine">
          工程ガント表示
        </button>
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
              colspan="6"
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
              <td class="num sequence" :class="c.dayClass">
                <input
                  type="text"
                  inputmode="numeric"
                  :value="row.daily[c.key].sequence_no === 0 || row.daily[c.key].sequence_no === '' || row.daily[c.key].sequence_no == null ? '' : row.daily[c.key].sequence_no"
                  @input="onSequenceInput(row, c.key, $event.target.value)"
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
            <td :colspan="3 + dateColumns.length * 6" class="no-data">行を追加してください</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="process-section">
      <div class="process-header">
        <div>
          <div class="process-title">工程展開</div>
          <div class="process-hint">選択期間内の計画を工程別に展開して表示します。</div>
        </div>
        <div class="process-actions">
          <span v-if="expanding" class="process-status">展開中...</span>
          <button class="btn" @click="clearProcessPlans" :disabled="!processPlans.length">非表示</button>
        </div>
      </div>

      <div v-if="processPlans.length" class="process-panels">
        <div v-for="proc in processPlans" :key="proc.process_id" class="process-card">
          <div class="process-card__head">
            <div>
              <div class="process-card__title">{{ proc.process_name || ('工程ID: ' + proc.process_id) }}</div>
              <div class="process-card__sub">{{ proc.line_name }}</div>
            </div>
            <div class="setup-count">
              段取り回数: <span class="setup-count__value">{{ proc.setupCount || 0 }}</span>回
            </div>
          </div>
            <div class="process-card__body">
              <div class="process-table-wrap">
                <table class="process-table" :style="{ minWidth: processTableMinWidth + 'px' }">
                  <thead>
                    <tr>
                      <th class="sticky-col number-col">No</th>
                      <th class="sticky-col code-col">品番</th>
                      <th class="sticky-col name-col">品名</th>
                      <th v-for="c in dateColumns" :key="c.key" class="mini-head" :class="c.dayClass">
                        {{ c.label }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, idx) in proc.rows" :key="row.product_id">
                      <td class="sticky-col number-col">{{ idx + 1 }}</td>
                      <td class="sticky-col code-col">{{ row.product_code }}</td>
                    <td class="sticky-col name-col">{{ row.product_name }}</td>
                  <td v-for="c in dateColumns" :key="c.key" class="mini-cell" :class="c.dayClass">
                    <div class="cell-line">計 {{ row.daily[c.key].plan || 0 }}</div>
                    <div class="cell-line sub">需 {{ row.daily[c.key].order || 0 }}</div>
                    <div class="cell-line time" v-if="row.daily[c.key].time != null">
                      工 {{ row.daily[c.key].time }} 分
                      <span v-if="row.daily[c.key].capacity != null" class="capacity">/ 勤 {{ row.daily[c.key].capacity }} 分</span>
                    </div>
                    <div class="cell-line muted" v-else>
                      <span v-if="row.daily[c.key].capacity != null">勤 {{ row.daily[c.key].capacity }} 分</span>
                      <span v-else>工 情報なし</span>
                    </div>
                  </td>
                </tr>
                <tr class="total-row">
                  <td class="sticky-col number-col">-</td>
                  <td class="sticky-col code-col">合計</td>
                  <td class="sticky-col name-col">合計工数</td>
                  <td v-for="c in dateColumns" :key="c.key" class="mini-cell total" :class="c.dayClass">
                    <template v-if="proc.totalDaily && proc.totalDaily[c.key] && proc.totalDaily[c.key].time != null">
                      <div class="cell-line time">
                        工 {{ proc.totalDaily[c.key].time }} 分
                        <span v-if="proc.totalDaily[c.key].capacity != null" class="capacity">/ 勤 {{ proc.totalDaily[c.key].capacity }} 分</span>
                      </div>
                    </template>
                    <div v-else class="cell-line muted">-</div>
                  </td>
                </tr>
                <tr v-if="!proc.rows.length">
                  <td :colspan="3 + dateColumns.length" class="no-data">データがありません</td>
                </tr>
              </tbody>
          </table>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="process-empty">工程展開を実行すると、工程別の計画がここに表示されます。</div>
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
import { useRouter } from 'vue-router'
import api from '@/api/client'

const mode = ref('plan')
const selectedLine = ref('')
const startDate = ref(new Date().toISOString().slice(0, 10))
const horizonDays = ref(60) // 表示日から2か月（約60日）
const keyword = ref('')

const lines = ref([])
const products = ref([])
const rows = ref([])
const processPlans = ref([])
const expanding = ref(false)
const router = useRouter()
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

// テーブルの最小幅を計算して、縮みすぎを防ぐ
const tableMinWidth = computed(() => {
  const fixedColsWidth = 60 + 187 + 100 // No + 品番 + 品名
  const perDayWidth = 80 * 6 // 6列×80px (需要、実績、在庫、計画、順序、計画在庫)
  return fixedColsWidth + dateColumns.value.length * perDayWidth
})

const processTableMinWidth = computed(() => {
  const fixedColsWidth = 60 + 187 + 100
  const perDayWidth = 200 // 工程日付列を広く表示（約2倍）
  return fixedColsWidth + dateColumns.value.length * perDayWidth
})

const initDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = { demand: 0, actual: 0, stock: 0, plan: '', plan_stock: 0, sequence_no: '' }
  })
  return daily
}

const initProcessDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = { plan: 0, order: 0, time: null, capacity: null }
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
  processPlans.value = []
}

const savePlan = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  const items = []
  rows.value.forEach((r) => {
    if (!r.product_id || !r.process_id) return
    dateColumns.value.forEach((c) => {
      const daily = r.daily[c.key]
      const seqNo = daily.sequence_no === '' || daily.sequence_no === null || daily.sequence_no === undefined ? null : Number(daily.sequence_no)
      items.push({
        product_id: r.product_id,
        process_id: r.process_id,
        plan_date: c.key,
        plan_qty: daily.plan === '' || daily.plan === null || daily.plan === undefined ? 0 : Number(daily.plan),
        actual_qty: Number(daily.actual || 0),
        stock_qty: Number(daily.stock || 0),
        planned_stock_qty: Number(daily.plan_stock || 0),
        sequence_no: seqNo,  // 日付ごとの順序番号
      })
    })
  })
  if (!items.length) {
    alert('保存するデータがありません。')
    return
  }
  try {
    const res = await api.lineBacklogs.save({
      line_id: selectedLine.value,
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

const clearProcessPlans = () => {
  processPlans.value = []
}

const buildProcessPlans = (backlogs = []) => {
  const grouped = new Map()
  backlogs.forEach((d) => {
    if (!d.process) return
    const procKey = d.process
    if (!grouped.has(procKey)) {
      grouped.set(procKey, {
        process_id: procKey,
        process_name: d.process_name || '',
        line_name: d.line_name || '',
        rows: [],
      })
    }
    const proc = grouped.get(procKey)
    const productKey = d.product
    let row = proc.rows.find((r) => r.product_id === productKey)
    if (!row) {
      row = {
        product_id: productKey,
        product_code: d.product_code || '',
        product_name: d.product_name || '',
        daily: initProcessDaily(),
      }
      proc.rows.push(row)
    }
    const dateKey = d.plan_date
    if (row.daily[dateKey]) {
      row.daily[dateKey].plan = Number(d.plan_qty || 0)
      row.daily[dateKey].order = Number(d.order_qty || 0)
      row.daily[dateKey].time = d.computed_time_min == null ? null : Number(d.computed_time_min)
      row.daily[dateKey].capacity = d.work_minutes == null ? null : Number(d.work_minutes)
      row.daily[dateKey].sequence_no = d.sequence_no  // 日付ごとの順序番号を保存
    }
  })
  const procs = Array.from(grouped.values())
  procs.forEach((proc) => {
    // 製品コード順でソート（表示用）
    proc.rows.sort((a, b) => {
      return (a.product_code || '').localeCompare(b.product_code || '')
    })
    // 合計工数（日別）を集計
    const totals = {}
    dateColumns.value.forEach((c) => {
      totals[c.key] = { time: 0, capacity: null, hasTime: false }
    })
    proc.rows.forEach((r) => {
      dateColumns.value.forEach((c) => {
        const cell = r.daily[c.key]
        if (!cell) return
        if (cell.time != null) {
          totals[c.key].time += Number(cell.time)
          totals[c.key].hasTime = true
        }
        if (totals[c.key].capacity == null && cell.capacity != null) {
          totals[c.key].capacity = Number(cell.capacity)
        }
      })
    })
    // hasTimeがない日はnullで非表示扱い
    Object.keys(totals).forEach((k) => {
      if (!totals[k].hasTime) totals[k].time = null
      delete totals[k].hasTime
    })
    proc.totalDaily = totals

    // 段取り回数を計算（日ごとにsequence_noでソートした順序で製品が切り替わる回数）
    let setupCount = 0
    let prevProductId = null
    dateColumns.value.forEach((c) => {
      // その日に計画がある製品を取得し、sequence_noでソート
      const productsForDay = proc.rows
        .map(r => ({
          product_id: r.product_id,
          plan: r.daily[c.key].plan,
          sequence_no: r.daily[c.key].sequence_no
        }))
        .filter(p => p.plan > 0)
        .sort((a, b) => {
          const aSeq = a.sequence_no != null ? a.sequence_no : Number.POSITIVE_INFINITY
          const bSeq = b.sequence_no != null ? b.sequence_no : Number.POSITIVE_INFINITY
          if (aSeq === bSeq) {
            return 0
          }
          return aSeq - bSeq
        })

      productsForDay.forEach(p => {
        if (prevProductId !== null && prevProductId !== p.product_id) {
          setupCount++
        }
        prevProductId = p.product_id
      })
    })
    proc.setupCount = setupCount
  })
  processPlans.value = procs
}

const refreshDates = () => {
  // 再初期化は既存データの初期化だけ（簡易対応）
  rows.value.forEach((r) => {
    r.daily = initDaily()
  })
  processPlans.value = []
}

const loadData = async () => {
  // 取り込み前は空表示（手動で「取り込み」を押す運用）
  rows.value = []
  processPlans.value = []
}

const onPlanInput = (row, dateKey, value) => {
  row.daily[dateKey].plan = value === '' ? '' : value
}

const onSequenceInput = (row, dateKey, value) => {
  row.daily[dateKey].sequence_no = value === '' ? '' : value
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

const doProcessExpand = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  expanding.value = true
  try {
    const payloadItems = []
    rows.value.forEach((r) => {
      if (!r.product_id) return
      dateColumns.value.forEach((c) => {
        const daily = r.daily[c.key]
        if (daily.plan === '' || daily.plan === null || daily.plan === undefined) return
        const planQty = Number(daily.plan || 0)
        payloadItems.push({
          product_id: r.product_id,
          process_id: r.process_id,
          plan_date: c.key,
          plan_qty: planQty,
          order_qty: Number(daily.demand || 0),
          demand_qty_plan: Number(daily.demand || 0),
        })
      })
    })

    const res = await api.lineBacklogs.expandProcesses({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
      items: payloadItems,
    })
    const payload = Array.isArray(res.data) ? res.data : res.data?.items || []
    buildProcessPlans(payload)
    alert('工程展開が完了しました。')
  } catch (e) {
    console.error('工程展開エラー', e)
    alert('工程展開に失敗しました。')
  } finally {
    expanding.value = false
  }
}

const goProcessGantt = () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  router.push({
    name: 'ProcessGanttView',
    query: { line: selectedLine.value, base: startDate.value },
  })
}

const doPickup = async () => {
  if (!selectedLine.value) return
  try {
    const res = await api.lineBacklogs.pickup({
      line_id: selectedLine.value,
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
          process_id: d.process,
          daily: initDaily(),
        })
      }
      const row = grouped.get(key)
      const dateKey = d.plan_date
      if (row.daily[dateKey]) {
        row.daily[dateKey].demand = Number(d.order_qty || 0)  // 需要=order_qty（取り込み時に計算された受注数/発注数）
        row.daily[dateKey].plan =
          d.plan_qty === null || d.plan_qty === undefined ? '' : d.plan_qty === 0 ? '' : d.plan_qty
        row.daily[dateKey].actual = Number(d.actual_qty || 0)
        row.daily[dateKey].stock = Number(d.stock_qty || 0)
        row.daily[dateKey].plan_stock = Number(d.planned_stock_qty || 0)
        row.daily[dateKey].sequence_no = d.sequence_no === null || d.sequence_no === undefined ? '' : d.sequence_no
      }
    })
    rows.value = Array.from(grouped.values())
    processPlans.value = []

    if (!rows.value.length) addRow()
  } catch (e) {
    console.error('バックログ取り込みエラー', e)
    alert('取り込みに失敗しました。')
  }
}

</script>

<style scoped>
.plan-container {
  padding: 8px 10px 14px;
  background: #eef2f6;
  font-size: 13px;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  color: #1f2a44;
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
  font-size: 13px;
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
  min-width: 400px; /* 5列ぶんの幅をさらに広げて文字潰れを防ぐ */
}
.mini {
  text-align: center;
  font-size: 12px;
  min-width: 80px; /* サブ列の最小幅を広げて視認性を上げる */
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
.btn.accent {
  background: #16a34a;
  color: #fff;
  border-color: #0f8a3c;
}
.btn.accent:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.process-section {
  margin-top: 14px;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 10px;
}
.process-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.process-title {
  font-weight: 700;
  font-size: 14px;
}
.process-hint {
  font-size: 12px;
  color: #64748b;
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
</style>
