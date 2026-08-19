<template>
  <div class="master-menu problem-tools-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">品質問題分析ダッシュボード</h2>
        <p class="helper-text">直近90日のNG履歴からQC七つ道具を表示します</p>
      </div>
      <button class="btn-secondary" @click="loadData" :disabled="loading">{{ loading ? "更新中..." : "更新" }}</button>
    </div>

    <div v-if="error" class="helper-text error-text">{{ error }}</div>

    <div class="prepare-form filter-form">
      <label>
        <span class="field-label">ライン</span>
        <select v-model="selectedLine">
          <option value="">すべて</option>
          <option v-for="v in lineOptions" :key="`line-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">工程</span>
        <select v-model="selectedProcess">
          <option value="">すべて</option>
          <option v-for="v in processOptions" :key="`proc-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">製品</span>
        <select v-model="selectedProduct">
          <option value="">すべて</option>
          <option v-for="v in productOptions" :key="`prod-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">項目</span>
        <select v-model="selectedItem" :disabled="!isItemSelectable">
          <option value="">すべて</option>
          <option v-for="v in itemOptions" :key="`item-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label class="field-worker">
        <span class="field-label">作業者</span>
        <select v-model="selectedPerson">
          <option value="">すべて</option>
          <option v-for="v in personOptions" :key="`person-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label class="field-unit">
        <span class="field-label">台目</span>
        <select v-model="selectedUnit">
          <option value="">すべて</option>
          <option v-for="v in unitOptions" :key="`unit-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">開始日</span>
        <input v-model="startDate" type="date" />
      </label>
      <label>
        <span class="field-label">終了日</span>
        <input v-model="endDate" type="date" />
      </label>
    </div>

    <section class="summary-grid">
      <div class="summary-card">
        <div class="summary-label">NG総件数</div>
        <div class="summary-value accent-ng">{{ filteredRows.length }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">発生日数</div>
        <div class="summary-value">{{ uniqueDays }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">再発項目</div>
        <div class="summary-value">{{ recurrenceItems.length }}</div>
      </div>
      <div class="summary-card" v-if="controlOutCount > 0">
        <div class="summary-label">管理外日数</div>
        <div class="summary-value accent-ng">{{ controlOutCount }}</div>
      </div>
    </section>

    <!-- 1. チェックシート -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">1. チェックシート（要対応NG一覧）</h3>
        <span class="section-note">日別NG件数（直近14日）</span>
      </div>
      <div class="bar-chart">
        <div v-for="row in dailyNgChart" :key="`d-chart-${row.date}`" class="bar-row">
          <span class="bar-label">{{ row.date }}</span>
          <div class="bar-track"><div class="bar-fill red" :style="{ width: `${Math.min((row.count / Math.max(...dailyNgChart.map((x) => x.count), 1)) * 100, 100)}%` }"></div></div>
          <span class="bar-value">{{ row.count }}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead><tr><th>発生日</th><th>ライン</th><th>製品</th><th>工程</th><th>項目</th><th>作業者</th><th>台目</th><th>バッチ</th></tr></thead>
          <tbody>
            <tr v-for="row in incidents" :key="row.key">
              <td>{{ row.date }}</td>
              <td>{{ row.line }}</td>
              <td>{{ row.product }}</td>
              <td>{{ row.process }}</td>
              <td>{{ row.item }}</td>
              <td>{{ row.person }}</td>
              <td>{{ row.unit }}</td>
              <td>#{{ row.batchId }}</td>
            </tr>
            <tr v-if="!incidents.length"><td colspan="8" class="empty-cell">対象データがありません。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 2. パレート図 -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">2. パレート図（上位不良要因）</h3>
        <span class="section-note">要因別累積比率</span>
      </div>
      <div class="chart-control-row">
        <label><span class="field-label">集計項目</span>
          <select v-model="selectedParetoKey">
            <option v-for="opt in groupingOptions" :key="`pareto-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
          </select>
        </label>
      </div>
      <div class="bar-chart">
        <div v-for="row in paretoRows" :key="`p-${row.item}`" class="bar-row">
          <span class="bar-label">{{ row.item }}</span>
          <div class="bar-track"><div class="bar-fill purple" :style="{ width: `${Math.min(row.ratio, 100)}%` }"></div></div>
          <span class="bar-value">{{ row.ratio.toFixed(1) }}%</span>
        </div>
      </div>
    </section>

    <!-- 3. ヒストグラム -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">3. ヒストグラム（日別NG件数分布）</h3>
        <span class="section-note">日別件数の頻度</span>
      </div>
      <div class="chart-control-row">
        <label><span class="field-label">集計項目</span>
          <select v-model="selectedHistogramKey">
            <option v-for="opt in groupingOptions" :key="`hist-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
          </select>
        </label>
      </div>
      <div class="bar-chart">
        <div v-for="row in histogramRows" :key="`h-${row.bucket}`" class="bar-row">
          <span class="bar-label">{{ row.bucket }}</span>
          <div class="bar-track"><div class="bar-fill teal" :style="{ width: `${Math.min((row.days / Math.max(...histogramRows.map((x) => x.days), 1)) * 100, 100)}%` }"></div></div>
          <span class="bar-value">{{ row.days }}日</span>
        </div>
      </div>
    </section>

    <!-- 4 & 5: 散布図 + 管理図 並列 -->
    <div class="dual-panel-row">
      <section class="panel">
        <div class="section-head">
          <h3 class="section-title">4. 散布図（台目とNG傾向）</h3>
        </div>
        <div class="chart-control-row">
          <label><span class="field-label">X軸</span>
            <select v-model="selectedScatterXKey">
              <option v-for="opt in numericGroupingOptions" :key="`scx-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
            </select>
          </label>
        </div>
        <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="plot-svg">
          <line :x1="plot.left" :y1="plot.bottom" :x2="plot.right" :y2="plot.bottom" class="axis" />
          <line :x1="plot.left" :y1="plot.top" :x2="plot.left" :y2="plot.bottom" class="axis" />
          <circle
            v-for="row in scatterRows"
            :key="`sc-${row.unit}`"
            :cx="scaleX(row.unit, scatterXMax)"
            :cy="scaleY(row.count, scatterYMax)"
            r="4"
            class="dot"
          />
        </svg>
      </section>

      <section class="panel">
        <div class="section-head">
          <h3 class="section-title">5. 管理図（日別NG件数）</h3>
        </div>
        <div class="chart-control-row">
          <label><span class="field-label">集計項目</span>
            <select v-model="selectedControlKey">
              <option v-for="opt in groupingOptions" :key="`ctl-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
            </select>
          </label>
        </div>
        <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="plot-svg">
          <line :x1="plot.left" :y1="plot.bottom" :x2="plot.right" :y2="plot.bottom" class="axis" />
          <line :x1="plot.left" :y1="plot.top" :x2="plot.left" :y2="plot.bottom" class="axis" />
          <polyline :points="controlLinePoints" class="line-main" />
          <line :x1="plot.left" :y1="scaleY(controlAvg, controlYMax)" :x2="plot.right" :y2="scaleY(controlAvg, controlYMax)" class="line-avg" />
          <line :x1="plot.left" :y1="scaleY(controlUcl, controlYMax)" :x2="plot.right" :y2="scaleY(controlUcl, controlYMax)" class="line-ucl" />
          <text :x="plot.right + 4" :y="scaleY(controlAvg, controlYMax) + 3" class="svg-legend blue">CL</text>
          <text :x="plot.right + 4" :y="scaleY(controlUcl, controlYMax) + 3" class="svg-legend red">UCL</text>
        </svg>
      </section>
    </div>

    <!-- 6. 層別 -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">6. 層別（ライン別・工程別・人別・製品別）</h3>
        <span class="section-note">構成比の高い順</span>
      </div>
      <div class="strat-grid">
        <div>
          <div class="strat-heading">ライン別</div>
          <table class="data-table compact">
            <thead><tr><th>ライン</th><th>NG件数</th><th>構成比</th></tr></thead>
            <tbody>
              <tr v-for="row in stratificationRows" :key="`st-${row.line}`">
                <td>{{ row.line }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <div class="strat-heading">工程別</div>
          <table class="data-table compact">
            <thead><tr><th>工程</th><th>NG件数</th><th>構成比</th></tr></thead>
            <tbody>
              <tr v-for="row in stratificationProcessRows" :key="`sp-${row.process}`">
                <td>{{ row.process }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <div class="strat-heading">作業者別</div>
          <table class="data-table compact">
            <thead><tr><th>作業者</th><th>NG件数</th><th>構成比</th></tr></thead>
            <tbody>
              <tr v-for="row in stratificationPeopleRows" :key="`sr-${row.person}`">
                <td>{{ row.person }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <div class="strat-heading">製品別</div>
          <table class="data-table compact">
            <thead><tr><th>製品</th><th>NG件数</th><th>構成比</th></tr></thead>
            <tbody>
              <tr v-for="row in stratificationProductRows" :key="`spr-${row.product}`">
                <td>{{ row.product }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 補助グラフ: 円グラフ + レーダー -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">補助グラフ（円グラフ・レーダーチャート）</h3>
      </div>
      <div class="dual-panel-row inner">
        <div>
          <div class="chart-control-row">
            <label><span class="field-label">集計項目</span>
              <select v-model="selectedPieKey">
                <option v-for="opt in groupingOptions" :key="`pie-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>
          <div class="sub-title">不良項目構成</div>
          <svg viewBox="0 0 320 240" class="plot-svg-sm">
            <g transform="translate(120 120)">
              <path v-for="(slice, idx) in pieSlices" :key="`pie-${idx}`" :d="slice.d" :fill="slice.color" />
            </g>
          </svg>
          <div class="mini-legend">
            <div v-for="row in pieLegendRows" :key="`pl-${row.item}`" class="mini-legend-item">
              <span class="swatch" :style="{ background: row.color }"></span>
              <span>{{ row.item }}: {{ row.ratio.toFixed(1) }}%</span>
            </div>
          </div>
        </div>
        <div>
          <div class="sub-title" style="margin-top:32px;">層別バランス（レーダー）</div>
          <svg viewBox="0 0 320 240" class="plot-svg-sm">
            <g transform="translate(160 120)">
              <polygon v-for="ring in radarRings" :key="`ring-${ring}`" :points="radarRingPoints(ring)" class="radar-ring" />
              <line v-for="(axis, idx) in radarAxes" :key="`axis-${idx}`" x1="0" y1="0" :x2="axis.x" :y2="axis.y" class="radar-axis" />
              <polygon :points="radarDataPoints" class="radar-data" />
              <text v-for="(axis, idx) in radarAxes" :key="`label-${idx}`" :x="axis.labelX" :y="axis.labelY" class="radar-label">{{ axis.label }}</text>
            </g>
          </svg>
        </div>
      </div>
    </section>

    <!-- 追加グラフ: 棒グラフ + 折れ線 -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">追加グラフ（棒グラフ・折れ線グラフ）</h3>
      </div>
      <div class="dual-panel-row inner">
        <div>
          <div class="chart-control-row">
            <label><span class="field-label">対象</span>
              <select v-model="selectedBarTargetKey">
                <option v-for="opt in groupingOptions" :key="`bar-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
            <label><span class="field-label">横軸</span>
              <select v-model="selectedBarXAxisType">
                <option value="category">カテゴリ</option>
                <option value="rank">順位</option>
              </select>
            </label>
            <label><span class="field-label">縦軸</span>
              <select v-model="selectedBarYAxisType">
                <option value="count">件数</option>
                <option value="ratio">構成比(%)</option>
              </select>
            </label>
          </div>
          <div class="sub-title">棒グラフ（上位5項目）</div>
          <svg viewBox="0 0 320 240" class="plot-svg-sm">
            <line x1="30" y1="210" x2="300" y2="210" class="axis" />
            <line x1="30" y1="20" x2="30" y2="210" class="axis" />
            <text x="165" y="236" class="axis-label">{{ barAxisLabel }}</text>
            <text x="12" y="14" class="axis-label">{{ barYAxisTypeLabel }}</text>
            <g v-for="tick in barYAxisTicks" :key="`bar-y-${tick.value}`">
              <line x1="26" :y1="tick.y" x2="30" :y2="tick.y" class="axis-tick" />
              <text x="24" :y="tick.y + 3" class="axis-tick-label">{{ tick.value }}</text>
            </g>
            <g v-for="(row, idx) in barRows" :key="`bar-${row.label}`">
              <rect :x="38 + (idx * 52)" :y="210 - row.h" width="34" :height="row.h" class="bar-col" />
              <text :x="55 + (idx * 52)" y="224" class="mini-axis-label">{{ row.label }}</text>
            </g>
          </svg>
        </div>
        <div>
          <div class="chart-control-row">
            <label><span class="field-label">対象</span>
              <select v-model="selectedLineTargetKey">
                <option v-for="opt in groupingOptions" :key="`line-opt-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
            <label><span class="field-label">横軸</span>
              <select v-model="selectedLineXAxisType">
                <option value="sequence">時系列</option>
                <option value="category">カテゴリ</option>
              </select>
            </label>
            <label><span class="field-label">縦軸</span>
              <select v-model="selectedLineYAxisType">
                <option value="count">件数</option>
                <option value="cumulative">累積件数</option>
              </select>
            </label>
          </div>
          <div class="sub-title">折れ線グラフ（日別NG件数）</div>
          <svg viewBox="0 0 320 240" class="plot-svg-sm">
            <line x1="30" y1="210" x2="300" y2="210" class="axis" />
            <line x1="30" y1="20" x2="30" y2="210" class="axis" />
            <text x="165" y="236" class="axis-label">{{ lineAxisLabel }}</text>
            <text x="12" y="14" class="axis-label">{{ lineYAxisTypeLabel }}</text>
            <g v-for="tick in lineYAxisTicks" :key="`line-y-${tick.value}`">
              <line x1="26" :y1="tick.y" x2="30" :y2="tick.y" class="axis-tick" />
              <text x="24" :y="tick.y + 3" class="axis-tick-label">{{ tick.value }}</text>
            </g>
            <g v-for="tick in lineXAxisTicks" :key="`line-x-${tick.x}`">
              <line :x1="tick.x" y1="210" :x2="tick.x" y2="214" class="axis-tick" />
              <text :x="tick.x" y="224" class="mini-axis-label">{{ tick.label }}</text>
            </g>
            <polyline :points="linePointsSmall" class="line-main" />
          </svg>
        </div>
      </div>
    </section>

    <!-- 7. 特性要因図 -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">7. 特性要因図（フィッシュボーン）</h3>
        <span class="section-note">4M分析の入力補助</span>
      </div>
      <svg viewBox="0 0 700 260" class="fishbone-svg">
        <line x1="60" y1="130" x2="620" y2="130" class="bone-main" />
        <polygon points="620,130 605,122 605,138" fill="#334155" />
        <text x="635" y="135" class="bone-effect">結果</text>
        <line x1="180" y1="40" x2="260" y2="130" class="bone-branch" />
        <line x1="420" y1="40" x2="500" y2="130" class="bone-branch" />
        <line x1="180" y1="220" x2="260" y2="130" class="bone-branch" />
        <line x1="420" y1="220" x2="500" y2="130" class="bone-branch" />
        <rect x="110" y="18" width="120" height="28" rx="4" class="bone-bg man" />
        <text x="170" y="37" class="bone-text">人 (Man)</text>
        <rect x="350" y="18" width="120" height="28" rx="4" class="bone-bg machine" />
        <text x="410" y="37" class="bone-text">機械 (Machine)</text>
        <rect x="110" y="214" width="120" height="28" rx="4" class="bone-bg method" />
        <text x="170" y="233" class="bone-text">方法 (Method)</text>
        <rect x="350" y="214" width="120" height="28" rx="4" class="bone-bg material" />
        <text x="410" y="233" class="bone-text">材料 (Material)</text>
        <text x="190" y="72" class="bone-detail">{{ fishbone.people }}</text>
        <text x="430" y="72" class="bone-detail">{{ fishbone.machine }}</text>
        <text x="190" y="200" class="bone-detail">{{ fishbone.method }}</text>
        <text x="430" y="200" class="bone-detail">{{ fishbone.material }}</text>
      </svg>
    </section>

    <!-- 再発候補 -->
    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">再発候補（同一項目の発生回数）</h3>
        <span class="section-note">2回以上発生した項目を表示</span>
      </div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead><tr><th>項目</th><th>発生回数</th><th>最新発生日</th></tr></thead>
          <tbody>
            <tr v-for="row in recurrenceItems" :key="row.item" :class="{ 'rate-warn': row.count >= 5 }">
              <td>{{ row.item }}</td>
              <td>{{ row.count }}</td>
              <td>{{ row.latestDate }}</td>
            </tr>
            <tr v-if="!recurrenceItems.length"><td colspan="3" class="empty-cell">対象データがありません。</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import api from "@/api/client"

const loading = ref(false)
const error = ref("")
const incidentRowsAll = ref([])
const incidents = ref([])
const recurrenceItems = ref([])
const dailyNgChart = ref([])
const paretoRows = ref([])
const histogramRows = ref([])
const scatterRows = ref([])
const controlRows = ref([])
const stratificationRows = ref([])
const stratificationProcessRows = ref([])
const stratificationPeopleRows = ref([])
const stratificationProductRows = ref([])
const fishbone = ref({ people: "-", machine: "-", method: "-", material: "-" })
const svgWidth = 820
const svgHeight = 260
const plot = { left: 44, right: 792, top: 20, bottom: 228 }
const controlAvg = ref(0)
const controlUcl = ref(0)
const scatterXMax = ref(1)
const scatterYMax = ref(1)
const controlYMax = ref(1)
const controlLinePoints = ref("")
const pieLegendRows = ref([])
const pieSlices = ref([])
const radarDataPoints = ref("")
const barRows = ref([])
const linePointsSmall = ref("")
const barAxisLabel = ref("製品")
const lineAxisLabel = ref("発生日")
const barYAxisTicks = ref([])
const lineYAxisTicks = ref([])
const lineXAxisTicks = ref([])
const barYAxisTypeLabel = computed(() => (selectedBarYAxisType.value === "ratio" ? "構成比(%)" : "件数"))
const lineYAxisTypeLabel = computed(() => (selectedLineYAxisType.value === "cumulative" ? "累積件数" : "件数"))
const selectedLine = ref("")
const selectedProcess = ref("")
const selectedProduct = ref("")
const selectedItem = ref("")
const selectedPerson = ref("")
const selectedUnit = ref("")
const startDate = ref("")
const endDate = ref("")
const selectedParetoKey = ref("item")
const selectedHistogramKey = ref("date")
const selectedScatterXKey = ref("unit")
const selectedControlKey = ref("date")
const selectedPieKey = ref("item")
const selectedBarTargetKey = ref("product")
const selectedBarXAxisType = ref("category")
const selectedBarYAxisType = ref("count")
const selectedLineTargetKey = ref("date")
const selectedLineXAxisType = ref("sequence")
const selectedLineYAxisType = ref("count")

const groupingOptions = [
  { value: "item", label: "項目" },
  { value: "line", label: "ライン" },
  { value: "process", label: "工程" },
  { value: "product", label: "製品" },
  { value: "person", label: "作業者" },
  { value: "unit", label: "台目" },
  { value: "date", label: "発生日" },
]
const numericGroupingOptions = [
  { value: "unit", label: "台目" },
  { value: "batchId", label: "バッチ" },
]

const uniqueSorted = (rows, key) => [...new Set(rows.map((r) => r[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const lineOptions = computed(() => uniqueSorted(incidentRowsAll.value, "line"))
const processOptions = computed(() => uniqueSorted(incidentRowsAll.value, "process"))
const productOptions = computed(() => uniqueSorted(incidentRowsAll.value, "product"))
const itemOptions = computed(() => {
  if (!isItemSelectable.value) return []
  const base = incidentRowsAll.value.filter((r) => r.product === selectedProduct.value && r.process === selectedProcess.value)
  return uniqueSorted(base, "item")
})
const personOptions = computed(() => uniqueSorted(incidentRowsAll.value, "person"))
const unitOptions = computed(() => uniqueSorted(incidentRowsAll.value, "unit"))
const isItemSelectable = computed(() => Boolean(selectedProduct.value) && Boolean(selectedProcess.value))

const filteredRows = computed(() => incidentRowsAll.value.filter((r) => {
  if (startDate.value && r.date < startDate.value) return false
  if (endDate.value && r.date > endDate.value) return false
  if (selectedLine.value && r.line !== selectedLine.value) return false
  if (selectedProcess.value && r.process !== selectedProcess.value) return false
  if (selectedProduct.value && r.product !== selectedProduct.value) return false
  if (selectedItem.value && r.item !== selectedItem.value) return false
  if (selectedPerson.value && r.person !== selectedPerson.value) return false
  if (selectedUnit.value && String(r.unit) !== String(selectedUnit.value)) return false
  return true
}))

const uniqueDays = computed(() => new Set(filteredRows.value.map((r) => r.date)).size)
const controlOutCount = computed(() => controlRows.value.filter((r) => r.judge === "要注意").length)

const radarRings = [0.25, 0.5, 0.75, 1]
const radarLabels = ["ライン", "工程", "製品", "作業者", "台目"]
const radarRadius = 72
const radarAxes = radarLabels.map((label, idx) => {
  const angle = (-Math.PI / 2) + ((Math.PI * 2 * idx) / radarLabels.length)
  const x = Math.cos(angle) * radarRadius
  const y = Math.sin(angle) * radarRadius
  const labelX = Math.cos(angle) * (radarRadius + 16)
  const labelY = Math.sin(angle) * (radarRadius + 16)
  return { label, x, y, angle, labelX, labelY }
})

const scaleX = (x, max) => {
  const span = Math.max(Number(max || 1), 1)
  return plot.left + ((x / span) * (plot.right - plot.left))
}
const scaleY = (y, max) => {
  const span = Math.max(Number(max || 1), 1)
  return plot.bottom - ((y / span) * (plot.bottom - plot.top))
}

const toArray = (data) => data?.results || data || []
const toDate = (v) => new Date(v || "")
const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
const piePalette = ["#2563eb", "#16a34a", "#f59e0b", "#ef4444", "#7c3aed", "#0ea5a4", "#64748b"]
const polarToXY = (angle, radius) => ({ x: Math.cos(angle) * radius, y: Math.sin(angle) * radius })
const arcPath = (startAngle, endAngle, radius) => {
  const p1 = polarToXY(startAngle, radius)
  const p2 = polarToXY(endAngle, radius)
  const large = endAngle - startAngle > Math.PI ? 1 : 0
  return `M 0 0 L ${p1.x} ${p1.y} A ${radius} ${radius} 0 ${large} 1 ${p2.x} ${p2.y} Z`
}
const radarRingPoints = (ratio) => radarAxes.map((a) => {
  const p = polarToXY(a.angle, radarRadius * ratio)
  return `${p.x},${p.y}`
}).join(" ")
const normalizeValue = (row, key) => String(row[key] ?? "未設定")
const groupCountMap = (rows, key) => {
  const m = new Map()
  rows.forEach((r) => {
    const k = normalizeValue(r, key)
    m.set(k, (m.get(k) || 0) + 1)
  })
  return m
}

const recomputeByRows = (rows) => {
  incidents.value = [...rows].sort((a, b) => b.ts - a.ts).slice(0, 100)
  const dayMap = new Map()
  rows.forEach((r) => dayMap.set(r.date, (dayMap.get(r.date) || 0) + 1))
  dailyNgChart.value = [...dayMap.entries()].map(([date, count]) => ({ date, count })).sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 14)

  const factorMap = new Map()
  rows.forEach((r) => {
    if (!factorMap.has(r.item)) factorMap.set(r.item, { item: r.item, count: 0, latestDate: r.date, latestTs: r.ts })
    const v = factorMap.get(r.item)
    v.count += 1
    if (r.ts > v.latestTs) {
      v.latestTs = r.ts
      v.latestDate = r.date
    }
  })
  recurrenceItems.value = [...factorMap.values()].filter((v) => v.count >= 2).sort((a, b) => b.count - a.count).slice(0, 20)

  const totalNg = rows.length || 1
  const sortedFactors = [...groupCountMap(rows, selectedParetoKey.value).entries()]
    .map(([item, count]) => ({ item, count }))
    .sort((a, b) => b.count - a.count)
  const pieFactors = [...groupCountMap(rows, selectedPieKey.value).entries()]
    .map(([item, count]) => ({ item, count }))
    .sort((a, b) => b.count - a.count)
  const pieTop = pieFactors.slice(0, 6)
  pieLegendRows.value = pieTop.map((r, idx) => ({ item: r.item, ratio: (r.count / totalNg) * 100, color: piePalette[idx % piePalette.length] }))
  let pieStart = -Math.PI / 2
  pieSlices.value = pieLegendRows.value.map((r) => {
    const sweep = (r.ratio / 100) * Math.PI * 2
    const d = arcPath(pieStart, pieStart + sweep, 76)
    pieStart += sweep
    return { d, color: r.color }
  })
  let cum = 0
  paretoRows.value = sortedFactors.slice(0, 10).map((v) => {
    cum += v.count
    return { item: v.item, ratio: (cum / totalNg) * 100 }
  })
  const histMap = new Map()
  const histogramBaseMap = groupCountMap(rows, selectedHistogramKey.value)
  for (const [, count] of histogramBaseMap.entries()) {
    const bucket = count <= 2 ? "1-2件" : count <= 5 ? "3-5件" : count <= 10 ? "6-10件" : "11件以上"
    histMap.set(bucket, (histMap.get(bucket) || 0) + 1)
  }
  histogramRows.value = ["1-2件", "3-5件", "6-10件", "11件以上"].map((bucket) => ({ bucket, days: histMap.get(bucket) || 0 }))
  const scatterMap = groupCountMap(rows, selectedScatterXKey.value)
  scatterRows.value = [...scatterMap.entries()]
    .map(([unit, count]) => ({ unit: Number(unit), count }))
    .filter((r) => Number.isFinite(r.unit))
    .sort((a, b) => a.unit - b.unit)
    .slice(0, 50)
  scatterXMax.value = Math.max(...scatterRows.value.map((r) => r.unit), 1)
  scatterYMax.value = Math.max(...scatterRows.value.map((r) => r.count), 1)
  const controlBaseMap = groupCountMap(rows, selectedControlKey.value)
  const dayCounts = [...controlBaseMap.entries()].map(([date, count]) => ({ date, count })).sort((a, b) => (a.date < b.date ? -1 : 1))
  const avg = dayCounts.reduce((s, r) => s + r.count, 0) / (dayCounts.length || 1)
  const variance = dayCounts.reduce((s, r) => s + ((r.count - avg) ** 2), 0) / (dayCounts.length || 1)
  const sigma = Math.sqrt(variance)
  const ucl = avg + (3 * sigma)
  controlRows.value = dayCounts.slice(-30).map((r) => ({ ...r, judge: r.count > ucl ? "要注意" : "管理内" }))
  controlAvg.value = avg
  controlUcl.value = ucl
  controlYMax.value = Math.max(...controlRows.value.map((r) => r.count), Math.ceil(ucl), 1)
  controlLinePoints.value = controlRows.value.map((r, idx) => `${scaleX(idx + 1, controlRows.value.length)} ${scaleY(r.count, controlYMax.value)}`).join(" ")
  const lineMap = new Map()
  rows.forEach((r) => lineMap.set(r.line, (lineMap.get(r.line) || 0) + 1))
  stratificationRows.value = [...lineMap.entries()].map(([line, count]) => ({ line, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const processMap = new Map()
  rows.forEach((r) => processMap.set(r.process, (processMap.get(r.process) || 0) + 1))
  stratificationProcessRows.value = [...processMap.entries()].map(([process, count]) => ({ process, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const peopleMap = new Map()
  rows.forEach((r) => peopleMap.set(r.person, (peopleMap.get(r.person) || 0) + 1))
  stratificationPeopleRows.value = [...peopleMap.entries()].map(([person, count]) => ({ person, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const productMap = new Map()
  rows.forEach((r) => productMap.set(r.product, (productMap.get(r.product) || 0) + 1))
  stratificationProductRows.value = [...productMap.entries()].map(([product, count]) => ({ product, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const barBase = [...groupCountMap(rows, selectedBarTargetKey.value).entries()]
    .map(([product, count]) => ({ product, count }))
    .sort((a, b) => b.count - a.count)
  const topProducts = barBase.slice(0, 5)
  const maxProduct = Math.max(...topProducts.map((r) => (selectedBarYAxisType.value === "ratio" ? (r.count / totalNg) * 100 : r.count)), 1)
  barAxisLabel.value = selectedBarXAxisType.value === "rank"
    ? "順位"
    : (groupingOptions.find((o) => o.value === selectedBarTargetKey.value)?.label || "分類")
  barRows.value = topProducts.map((r) => ({
    label: selectedBarXAxisType.value === "rank" ? `#${topProducts.findIndex((x) => x.product === r.product) + 1}` : String(r.product).slice(0, 5),
    h: Math.max((((selectedBarYAxisType.value === "ratio" ? (r.count / totalNg) * 100 : r.count) / maxProduct) * 170), 2),
  }))
  barYAxisTicks.value = [0, 0.5, 1].map((r) => ({
    value: Math.round(maxProduct * r * 10) / 10,
    y: 210 - (170 * r),
  }))
  const lineBase = [...groupCountMap(rows, selectedLineTargetKey.value).entries()]
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => (selectedLineXAxisType.value === "category" ? (a.date < b.date ? -1 : 1) : (a.date < b.date ? -1 : 1)))
    .slice(-14)
  const lineDaily = lineBase.map((r, idx) => {
    if (selectedLineYAxisType.value !== "cumulative") return r
    return { ...r, count: lineBase.slice(0, idx + 1).reduce((s, v) => s + v.count, 0) }
  })
  const maxDaily = Math.max(...lineDaily.map((r) => r.count), 1)
  lineAxisLabel.value = selectedLineXAxisType.value === "sequence"
    ? "順序"
    : (groupingOptions.find((o) => o.value === selectedLineTargetKey.value)?.label || "分類")
  linePointsSmall.value = lineDaily.map((r, idx) => {
    const x = 34 + ((idx / Math.max(lineDaily.length - 1, 1)) * 262)
    const y = 210 - ((r.count / maxDaily) * 170)
    return `${x},${y}`
  }).join(" ")
  lineYAxisTicks.value = [0, 0.5, 1].map((r) => ({
    value: Math.round(maxDaily * r),
    y: 210 - (170 * r),
  }))
  lineXAxisTicks.value = lineDaily.filter((_, idx) => idx === 0 || idx === lineDaily.length - 1 || idx === Math.floor(lineDaily.length / 2)).map((r, idx, arr) => {
    const pos = arr.length <= 1 ? 0 : idx / (arr.length - 1)
    return {
      label: selectedLineXAxisType.value === "sequence" ? String(lineDaily.findIndex((x) => x.date === r.date) + 1) : String(r.date).slice(0, 5),
      x: 34 + (262 * pos),
    }
  })
  const toMax = (mapObj) => Math.max(...[...mapObj.values()], 0)
  const radarRaw = [
    toMax(lineMap),
    toMax(processMap),
    toMax(productMap),
    toMax(peopleMap),
    toMax(scatterMap),
  ]
  const radarBase = Math.max(...radarRaw, 1)
  radarDataPoints.value = radarAxes.map((a, idx) => {
    const r = (radarRaw[idx] / radarBase) * radarRadius
    const p = polarToXY(a.angle, r)
    return `${p.x},${p.y}`
  }).join(" ")
  fishbone.value = {
    people: recurrenceItems.value[0]?.item || "作業者要因を確認",
    machine: incidents.value[0]?.process || "設備要因を確認",
    method: "工程手順・検査頻度を確認",
    material: incidents.value[0]?.product || "材料・品番を確認",
  }
}

const loadData = async () => {
  loading.value = true
  error.value = ""
  try {
    const now = new Date()
    const from = new Date(now); from.setDate(now.getDate() - 90)
    const res = await api.integratedChecksheets.listBatches({ page_size: 200 })
    const batches = toArray(res.data).filter((b) => toDate(b.plan_date || b.created_at) >= from)
    const unitsRes = await Promise.all(batches.map((b) => api.integratedChecksheets.getBatchUnits(b.id)))
    const processNameById = new Map()
    batches.forEach((b) => (b.process_progress || []).forEach((p) => processNameById.set(p.process_block_id, p.process_name || p.process_code || `工程${p.process_block_id}`)))

    const incidentRows = []
    for (let i = 0; i < batches.length; i += 1) {
      const batch = batches[i]
      const units = toArray(unitsRes[i].data)
      const date = toDate(batch.plan_date || batch.created_at)
      for (const unit of units) {
        for (const check of unit.checks || []) {
          if (check.judgement !== "NG") continue
          incidentRows.push({
            key: `${batch.id}-${unit.id}-${check.id}`,
            ts: date,
            date: fmt(date),
            line: batch.line_code || "未設定",
            product: batch.product_code || "未設定",
            process: processNameById.get(check.process_block_id) || `工程${check.process_block_id}`,
            item: check.item_name || "未設定項目",
            person: check.checked_by_name || check.worker_name || check.worker_code || "未設定",
            unit: unit.sequence_no,
            batchId: batch.id,
          })
        }
      }
    }
    incidentRowsAll.value = incidentRows
    recomputeByRows(filteredRows.value)
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch([selectedProduct, selectedProcess], () => {
  if (!isItemSelectable.value) selectedItem.value = ""
})
watch(filteredRows, (rows) => {
  recomputeByRows(rows)
})
watch([
  selectedParetoKey,
  selectedHistogramKey,
  selectedScatterXKey,
  selectedControlKey,
  selectedPieKey,
  selectedBarTargetKey,
  selectedBarXAxisType,
  selectedBarYAxisType,
  selectedLineTargetKey,
  selectedLineXAxisType,
  selectedLineYAxisType,
], () => {
  recomputeByRows(filteredRows.value)
})
</script>

<style scoped>
.problem-tools-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.error-text {
  color: #b91c1c;
  font-weight: 700;
}

.prepare-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.prepare-form label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.field-label {
  white-space: nowrap;
  min-width: 40px;
  font-size: 12px;
  color: #334155;
}
.prepare-form select,
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  width: 150px;
  max-width: 42vw;
}
.prepare-form input[type="date"] { width: 140px; }
.filter-form .field-worker select { width: 140px; }
.filter-form .field-unit select { width: 110px; }

/* サマリーグリッド（weekly-monthlyと統一） */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.summary-card {
  padding: 12px 14px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}
.summary-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
.summary-value {
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
}
.accent-ng { color: #dc2626; }

/* パネル（weekly-monthlyと統一） */
.panel {
  padding: 12px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #fff;
}
.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.section-title { margin: 0; }
.section-note { font-size: 12px; color: #64748b; }

.sub-title { font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px; }

/* チャートコントロール */
.chart-control-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.chart-control-row label { display: inline-flex; align-items: center; gap: 6px; }
.chart-control-row select {
  width: 140px;
  padding: 4px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 12px;
}

/* バーチャート */
.bar-chart { margin-bottom: 10px; }
.bar-row {
  display: grid;
  grid-template-columns: 100px 1fr 56px;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
  font-size: 12px;
}
.bar-label { color: #334155; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { height: 14px; background: #eef2f7; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; transition: width .3s ease; }
.bar-fill.red { background: #dc2626; }
.bar-fill.purple { background: #7c3aed; }
.bar-fill.teal { background: #0ea5a4; }
.bar-value { color: #334155; font-weight: 600; }

/* テーブル */
.table-wrap { overflow-x: auto; }
.empty-cell { text-align: center; color: #64748b; padding: 18px 8px; }

/* レート強調（weekly-monthlyと統一） */
.rate-warn {
  color: #b45309;
  font-weight: 800;
  background: #fff7ed;
}

/* 2列並列 */
.dual-panel-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 12px;
}
.dual-panel-row.inner {
  gap: 14px;
}

/* 層別グリッド */
.strat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.strat-heading {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  margin-bottom: 4px;
}

/* SVG共通 */
.plot-svg {
  width: 100%;
  height: 260px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.plot-svg-sm {
  width: 100%;
  height: 240px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.axis { stroke: #94a3b8; stroke-width: 1; }
.dot { fill: #2563eb; opacity: 0.85; }
.line-main { fill: none; stroke: #0f766e; stroke-width: 2; }
.line-avg { stroke: #2563eb; stroke-width: 1.5; stroke-dasharray: 5 4; }
.line-ucl { stroke: #dc2626; stroke-width: 1.5; stroke-dasharray: 5 4; }
.svg-legend { font-size: 10px; font-weight: 600; }
.svg-legend.blue { fill: #2563eb; }
.svg-legend.red { fill: #dc2626; }
.axis-label { font-size: 10px; fill: #334155; text-anchor: middle; }
.axis-tick { stroke: #94a3b8; stroke-width: 1; }
.axis-tick-label { font-size: 9px; fill: #475569; text-anchor: end; }
.mini-axis-label { font-size: 10px; fill: #334155; text-anchor: middle; }
.bar-col { fill: #2563eb; opacity: 0.85; }

/* 円グラフ/レーダー */
.mini-legend { display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 4px 8px; margin-top: 8px; }
.mini-legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #334155; }
.swatch { width: 10px; height: 10px; border-radius: 2px; }
.radar-ring { fill: none; stroke: #cbd5e1; stroke-width: 1; }
.radar-axis { stroke: #94a3b8; stroke-width: 1; }
.radar-data { fill: rgba(37, 99, 235, 0.2); stroke: #2563eb; stroke-width: 2; }
.radar-label { font-size: 11px; fill: #334155; text-anchor: middle; dominant-baseline: middle; }

/* フィッシュボーン */
.fishbone-svg { width: 100%; max-height: 260px; }
.bone-main { stroke: #334155; stroke-width: 3; }
.bone-branch { stroke: #64748b; stroke-width: 2; }
.bone-effect { font-size: 14px; font-weight: 700; fill: #1e293b; }
.bone-bg { stroke: none; }
.bone-bg.man { fill: #dbeafe; }
.bone-bg.machine { fill: #fef3c7; }
.bone-bg.method { fill: #dcfce7; }
.bone-bg.material { fill: #fce7f3; }
.bone-text { font-size: 12px; font-weight: 700; fill: #1e293b; text-anchor: middle; }
.bone-detail { font-size: 10px; fill: #475569; text-anchor: middle; }

@media (max-width: 900px) {
  .dual-panel-row { grid-template-columns: 1fr; }
  .strat-grid { grid-template-columns: 1fr 1fr; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 600px) {
  .strat-grid { grid-template-columns: 1fr; }
}
</style>
