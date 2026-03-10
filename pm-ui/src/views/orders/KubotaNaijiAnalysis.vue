<template>
  <div class="naiji-analysis">
    <h2 class="page-title">クボタ内示分析</h2>

    <!-- タブバー -->
    <div class="tab-bar">
      <button :class="['tab-item', { active: activeTab === 'analysis' }]" @click="activeTab = 'analysis'">
        📊 変化推移分析
      </button>
      <button :class="['tab-item', { active: activeTab === 'report' }]" @click="activeTab = 'report'">
        📋 一括分析レポート
      </button>
    </div>

    <!-- ===== タブ1: 変化推移分析 ===== -->
    <div v-show="activeTab === 'analysis'">

      <!-- 検索条件 -->
      <div class="search-panel">
        <div class="search-row">
          <label class="search-label">製品</label>
          <select v-model="selectedProduct" class="form-select" @change="onProductChange">
            <option value="">-- 製品を選択 --</option>
            <option v-for="p in products" :key="p.product_code" :value="p.product_code">
              {{ p.product_code }}{{ p.product_name ? ` / ${p.product_name}` : '' }}
              （{{ p.snapshot_count }}件）
            </option>
          </select>

          <label class="search-label">納期</label>
          <input type="date" v-model="startDate" class="form-input" />
          <span class="range-sep">〜</span>
          <input type="date" v-model="endDate" class="form-input" />

          <button class="btn-primary" :disabled="!selectedProduct || loading" @click="fetchAnalysis">
            {{ loading ? '分析中...' : '分析実行' }}
          </button>
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
      </div>

      <!-- 結果エリア -->
      <div v-if="analysisData" class="result-area">

        <!-- 期間全体サマリー（安全在庫分析）-->
        <div v-if="analysisData.period_summary" class="period-summary">
          <h3 class="section-title">
            期間全体サマリー — 安全在庫分析
            <span class="summary-sub">（全スナップショット vs 確定、{{ analysisData.period_summary.dates_with_firm }} 納期 × 全取込分）</span>
          </h3>
          <div class="summary-meta">
            <span class="meta-item">分析納期数：<strong>{{ analysisData.period_summary.analyzed_dates }}</strong> 日</span>
            <span class="meta-sep">／</span>
            <span class="meta-item">うち確定あり：<strong>{{ analysisData.period_summary.dates_with_firm }}</strong> 日</span>
          </div>
          <div class="summary-grid">

            <!-- 予測誤差ブロック -->
            <div class="summary-block">
              <div class="block-title">予測誤差（全内示スナップショット − 確定）</div>
              <div class="block-rows">
                <div class="block-row">
                  <span class="block-label">最大差（内示 − 確定）</span>
                  <span class="block-val">
                    {{ fmt(analysisData.period_summary.max_diff) }}
                    <small v-if="analysisData.period_summary.max_diff_date" class="diff-date">
                      （{{ analysisData.period_summary.max_diff_date }}）
                    </small>
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">最小差（内示 − 確定）</span>
                  <span class="block-val">
                    {{ fmt(analysisData.period_summary.min_diff) }}
                    <small v-if="analysisData.period_summary.min_diff_date" class="diff-date">
                      （{{ analysisData.period_summary.min_diff_date }}）
                    </small>
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">平均絶対誤差（MAE）</span>
                  <span class="block-val">{{ fmt(analysisData.period_summary.mae) }}</span>
                </div>
                <div class="block-row">
                  <span class="block-label">平均差（符号付き）</span>
                  <span class="block-val" :class="biasClass(analysisData.period_summary.mean_error)">
                    {{ signFmt(analysisData.period_summary.mean_error) }}
                    <small class="bias-note">{{ biasNote(analysisData.period_summary.mean_error) }}</small>
                  </span>
                </div>
                <div class="block-row highlight-row">
                  <span class="block-label">予測誤差 σ（標準偏差）</span>
                  <span class="block-val sigma-val">{{ fmt(analysisData.period_summary.sigma) }}</span>
                </div>
              </div>
            </div>

            <!-- 欠品リスクブロック -->
            <div class="summary-block">
              <div class="block-title">欠品リスク（内示 ＜ 確定）</div>
              <div class="block-rows">
                <div class="block-row">
                  <span class="block-label">内示過小率</span>
                  <span class="block-val" :class="analysisData.period_summary.shortage_rate > 50 ? 'val-danger' : ''">
                    {{ fmt(analysisData.period_summary.shortage_rate) }} %
                    （{{ analysisData.period_summary.shortage_dates }} / {{ analysisData.period_summary.dates_with_firm }} 納期）
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">ワースト1位</span>
                  <span class="block-val" :class="analysisData.period_summary.max_shortage > 0 ? 'val-danger' : ''">
                    {{ fmt(analysisData.period_summary.max_shortage) }}
                    <small class="diff-date">出現率 {{ fmt(analysisData.period_summary.worst1_rate) }}%</small>
                  </span>
                </div>
                <div v-if="analysisData.period_summary.worst1_dates && analysisData.period_summary.worst1_dates.length" class="worst-dates-row">
                  <span class="worst-dates-label">出現日：</span>
                  <span v-for="d in analysisData.period_summary.worst1_dates" :key="d" class="worst-date-chip">{{ d }}</span>
                </div>
                <div class="block-row">
                  <span class="block-label">ワースト2位</span>
                  <span class="block-val" :class="analysisData.period_summary.worst2_qty > 0 ? 'val-danger' : ''">
                    {{ analysisData.period_summary.worst2_qty != null ? fmt(analysisData.period_summary.worst2_qty) : '—' }}
                    <small v-if="analysisData.period_summary.worst2_rate != null" class="diff-date">出現率 {{ fmt(analysisData.period_summary.worst2_rate) }}%</small>
                  </span>
                </div>
                <div v-if="analysisData.period_summary.worst2_dates && analysisData.period_summary.worst2_dates.length" class="worst-dates-row">
                  <span class="worst-dates-label">出現日：</span>
                  <span v-for="d in analysisData.period_summary.worst2_dates" :key="d" class="worst-date-chip">{{ d }}</span>
                </div>
              </div>
            </div>

            <!-- 安全在庫推奨ブロック -->
            <div class="summary-block safety-block">
              <div class="block-title">推奨安全在庫量（Z × σ）</div>
              <div class="block-rows">
                <div class="block-row">
                  <span class="block-label">90% サービスレベル <small>（Z=1.28）</small></span>
                  <span class="block-val ss-val">{{ fmt(analysisData.period_summary.safety_stock_90) }}</span>
                </div>
                <div class="block-row highlight-row">
                  <span class="block-label">95% サービスレベル <small>（Z=1.65）</small></span>
                  <span class="block-val ss-val">{{ fmt(analysisData.period_summary.safety_stock_95) }}</span>
                </div>
                <div class="block-row">
                  <span class="block-label">99% サービスレベル <small>（Z=2.33）</small></span>
                  <span class="block-val ss-val">{{ fmt(analysisData.period_summary.safety_stock_99) }}</span>
                </div>
                <div class="block-note">
                  ※ 内示が体系的に過小な場合はバイアス補正済み
                </div>
              </div>
            </div>

            <!-- 収束安定期間ブロック -->
            <div class="summary-block">
              <div class="block-title">収束安定期間（内示＝確定が続いた日数）</div>
              <div class="block-rows">
                <div class="block-note" style="margin-bottom:6px;">
                  ※ 各納期について、内示が確定値と一致してから納期まで連続して変わらなかった日数
                </div>
                <div class="block-row highlight-row">
                  <span class="block-label">平均</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_mean != null ? analysisData.period_summary.stable_days_mean + ' 日' : '—' }}
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">最短</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_min != null ? analysisData.period_summary.stable_days_min + ' 日' : '—' }}
                    <small v-if="analysisData.period_summary.stable_days_min_date" class="diff-date">
                      （{{ analysisData.period_summary.stable_days_min_date }}）
                    </small>
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">最長</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_max != null ? analysisData.period_summary.stable_days_max + ' 日' : '—' }}
                    <small v-if="analysisData.period_summary.stable_days_max_date" class="diff-date">
                      （{{ analysisData.period_summary.stable_days_max_date }}）
                    </small>
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">対象納期数</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_count != null ? analysisData.period_summary.stable_days_count + ' 件' : '—' }}
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- 納期選択タブ -->
        <div class="due-date-tabs">
          <span class="tabs-label">納期選択：</span>
          <button
            v-for="dd in analysisData.due_dates"
            :key="dd"
            :class="['tab-btn', { active: selectedDueDate === dd }]"
            @click="selectedDueDate = dd"
          >{{ formatDate(dd) }}</button>
        </div>

        <div v-if="selectedDueDate" class="content-grid">

          <!-- 左: グラフ -->
          <div class="chart-section">
            <h3 class="section-title">内示数量 推移グラフ（納期: {{ formatDate(selectedDueDate) }}）</h3>
            <div class="chart-wrap">
              <svg
                ref="svgEl"
                :viewBox="`0 0 ${svgW} ${svgH}`"
                width="100%"
                class="chart-svg"
              >
                <!-- グリッド線 -->
                <g class="grid">
                  <line
                    v-for="y in yGridLines"
                    :key="y.val"
                    :x1="padL"
                    :x2="svgW - padR"
                    :y1="y.py"
                    :y2="y.py"
                    stroke="#e0e0e0"
                    stroke-width="1"
                  />
                </g>
                <!-- Y軸ラベル -->
                <g class="y-labels">
                  <text
                    v-for="y in yGridLines"
                    :key="'yl' + y.val"
                    :x="padL - 6"
                    :y="y.py + 4"
                    text-anchor="end"
                    font-size="11"
                    fill="#666"
                  >{{ y.val }}</text>
                </g>
                <!-- X軸ラベル -->
                <g class="x-labels">
                  <text
                    v-for="(pt, i) in chartPoints"
                    :key="'xl' + i"
                    :x="pt.px"
                    :y="svgH - padB + 16"
                    text-anchor="middle"
                    font-size="10"
                    fill="#555"
                    :transform="`rotate(-40, ${pt.px}, ${svgH - padB + 16})`"
                  >{{ pt.label }}</text>
                </g>
                <!-- 折れ線 -->
                <polyline
                  v-if="chartPoints.length >= 2"
                  :points="chartPoints.map(p => `${p.px},${p.py}`).join(' ')"
                  fill="none"
                  stroke="#1a5fb4"
                  stroke-width="2"
                />
                <!-- 確定数量 横線 -->
                <line
                  v-if="firmY !== null"
                  :x1="padL"
                  :x2="svgW - padR"
                  :y1="firmY"
                  :y2="firmY"
                  stroke="#e53e3e"
                  stroke-width="1.5"
                  stroke-dasharray="6,3"
                />
                <text
                  v-if="firmY !== null"
                  :x="svgW - padR + 4"
                  :y="firmY + 4"
                  font-size="11"
                  fill="#e53e3e"
                >確定</text>
                <!-- データ点 -->
                <circle
                  v-for="(pt, i) in chartPoints"
                  :key="'pt' + i"
                  :cx="pt.px"
                  :cy="pt.py"
                  r="4"
                  :fill="pt.qty === 0 ? '#ccc' : '#1a5fb4'"
                  stroke="#fff"
                  stroke-width="1.5"
                >
                  <title>{{ pt.label }}: {{ pt.qty }}</title>
                </circle>
                <!-- 軸 -->
                <line :x1="padL" :x2="padL" :y1="padT" :y2="svgH - padB" stroke="#aaa" stroke-width="1" />
                <line :x1="padL" :x2="svgW - padR" :y1="svgH - padB" :y2="svgH - padB" stroke="#aaa" stroke-width="1" />
              </svg>
            </div>
          </div>

          <!-- 右: 統計 -->
          <div class="stat-section">
            <h3 class="section-title">統計サマリー</h3>
            <template v-if="currentStat">
              <table class="stat-table">
                <tbody>
                  <tr><th>スナップショット数</th><td>{{ currentStat.count }} 回</td></tr>
                  <tr><th>平均</th><td>{{ currentStat.mean }}</td></tr>
                  <tr><th>標準偏差</th><td>{{ currentStat.std_dev }}</td></tr>
                  <tr><th>変動係数(CV)</th><td>{{ currentStat.cv }} %</td></tr>
                  <tr><th>最小</th><td>{{ currentStat.min }}</td></tr>
                  <tr><th>最大</th><td>{{ currentStat.max }}</td></tr>
                  <tr><th>変動幅</th><td>{{ currentStat.range }}</td></tr>
                  <tr class="sep-row"><th colspan="2">変化量</th></tr>
                  <tr><th>初回内示</th><td>{{ currentStat.first_qty }}</td></tr>
                  <tr><th>最終内示</th><td>{{ currentStat.last_qty }}</td></tr>
                  <tr>
                    <th>初回→最終 変化</th>
                    <td :class="changeClass(currentStat.first_to_last_change)">
                      {{ sign(currentStat.first_to_last_change) }}
                      <small v-if="currentStat.first_to_last_pct !== null">
                        ({{ sign(currentStat.first_to_last_pct) }}%)
                      </small>
                    </td>
                  </tr>
                  <tr class="sep-row"><th colspan="2">確定との比較</th></tr>
                  <tr>
                    <th>確定数量</th>
                    <td>{{ currentStat.firm_qty !== null ? currentStat.firm_qty : '—' }}</td>
                  </tr>
                  <tr v-if="currentStat.firm_qty !== null">
                    <th>最終内示 vs 確定</th>
                    <td :class="changeClass(currentStat.last_vs_firm)">
                      {{ sign(currentStat.last_vs_firm) }}
                      <small v-if="currentStat.last_vs_firm_pct !== null">
                        ({{ sign(currentStat.last_vs_firm_pct) }}%)
                      </small>
                    </td>
                  </tr>
                </tbody>
              </table>
            </template>
            <p v-else class="no-stat">選択した納期の統計データがありません</p>
          </div>
        </div>

        <!-- 詳細テーブル -->
        <div class="detail-section">
          <h3 class="section-title">スナップショット一覧（全納期）</h3>
          <div class="table-scroll">
            <table class="detail-table">
              <thead>
                <tr>
                  <th class="sticky-col">取込日</th>
                  <th class="sticky-col2">ソースファイル</th>
                  <th
                    v-for="dd in analysisData.due_dates"
                    :key="dd"
                    :class="{ 'active-col': dd === selectedDueDate }"
                    @click="selectedDueDate = dd"
                    style="cursor:pointer"
                  >{{ formatDate(dd) }}</th>
                </tr>
                <!-- 確定行 -->
                <tr class="firm-row">
                  <th class="sticky-col">確定</th>
                  <th class="sticky-col2">—</th>
                  <td
                    v-for="dd in analysisData.due_dates"
                    :key="'firm-' + dd"
                    :class="{ 'active-col': dd === selectedDueDate }"
                    class="firm-cell"
                  >{{ analysisData.firm_quantities[dd] !== undefined ? analysisData.firm_quantities[dd] : '—' }}</td>
                </tr>
              </thead>
              <tbody>
                <tr v-for="snap in analysisData.snapshots" :key="snap.source_file">
                  <td class="sticky-col date-cell">{{ snap.snapshot_date }}</td>
                  <td class="sticky-col2 file-cell" :title="snap.source_file">{{ shortFileName(snap.source_file) }}</td>
                  <td
                    v-for="dd in analysisData.due_dates"
                    :key="dd"
                    :class="['qty-cell', { 'active-col': dd === selectedDueDate }, deltaCellClass(snap, dd)]"
                  >
                    <span v-if="snap.quantities[dd] !== undefined">{{ snap.quantities[dd] }}</span>
                    <span v-else class="empty-cell">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>

      <div v-else-if="!loading && selectedProduct" class="placeholder">
        条件を設定して「分析実行」を押してください
      </div>
    </div>

    <!-- ===== タブ2: 一括分析レポート ===== -->
    <div v-show="activeTab === 'report'">

      <div class="search-panel">
        <div class="search-row">
          <label class="field-label">製品選択</label>
          <div class="product-select-area">
            <div class="product-toolbar">
              <button class="btn-sm" @click="selectAll">全選択</button>
              <button class="btn-sm" @click="clearAll">全解除</button>
              <span class="selected-count">{{ selectedCodes.length }} 件選択中</span>
            </div>
            <div class="product-list" v-if="products.length">
              <label
                v-for="p in products"
                :key="p.product_code"
                class="product-item"
                :class="{ selected: selectedCodes.includes(p.product_code) }"
              >
                <input type="checkbox" :value="p.product_code" v-model="selectedCodes" />
                <span class="prod-code">{{ p.product_code }}</span>
                <span class="prod-name">{{ p.product_name }}</span>
              </label>
            </div>
            <div v-else class="no-products">読み込み中...</div>
          </div>
        </div>

        <div class="search-row">
          <label class="field-label">納期範囲</label>
          <input type="date" v-model="rStartDate" class="form-input" />
          <span class="range-sep">〜</span>
          <input type="date" v-model="rEndDate" class="form-input" />
        </div>

        <div class="search-row">
          <button
            class="btn-export"
            :disabled="exporting || selectedCodes.length === 0"
            @click="exportExcel"
          >
            {{ exporting ? 'Excel出力中...' : '📥 Excelレポート出力' }}
          </button>
          <span v-if="rErrorMsg" class="error-msg">{{ rErrorMsg }}</span>
        </div>
      </div>

      <!-- プレビューテーブル -->
      <div v-if="previewRows.length" class="preview-area">
        <h3 class="preview-title">プレビュー（{{ previewRows.length }} 製品）</h3>
        <div class="table-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th rowspan="2">品番</th>
                <th rowspan="2">品名</th>
                <th colspan="7" class="cat-error">予測誤差</th>
                <th colspan="5" class="cat-shortage">欠品リスク</th>
                <th colspan="3" class="cat-safety">推奨安全在庫</th>
                <th colspan="4" class="cat-stable">収束安定期間</th>
              </tr>
              <tr>
                <th class="cat-error">最大差</th>
                <th class="cat-error">最小差</th>
                <th class="cat-error">MAE</th>
                <th class="cat-error">平均差</th>
                <th class="cat-error">σ</th>
                <th class="cat-error">スナップ数</th>
                <th class="cat-error">分析納期数</th>
                <th class="cat-shortage">過小率%</th>
                <th class="cat-shortage">W1<br>過小量</th>
                <th class="cat-shortage">W1<br>出現率%</th>
                <th class="cat-shortage">W2<br>過小量</th>
                <th class="cat-shortage">W2<br>出現率%</th>
                <th class="cat-safety">90%</th>
                <th class="cat-safety">95%</th>
                <th class="cat-safety">99%</th>
                <th class="cat-stable">平均日</th>
                <th class="cat-stable">最短日</th>
                <th class="cat-stable">最長日</th>
                <th class="cat-stable">件数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in previewRows" :key="r.product_code">
                <td class="code-cell">{{ r.product_code }}</td>
                <td class="name-cell">{{ r.product_name }}</td>
                <td>{{ fmt(r.max_diff) }}</td>
                <td>{{ fmt(r.min_diff) }}</td>
                <td>{{ fmt(r.mae) }}</td>
                <td>{{ fmt(r.mean_error) }}</td>
                <td>{{ fmt(r.sigma) }}</td>
                <td>{{ r.snapshot_count }}</td>
                <td>{{ r.analyzed_dates }}</td>
                <td>{{ fmt(r.shortage_rate) }}</td>
                <td>{{ fmt(r.max_shortage) }}</td>
                <td>{{ fmt(r.worst1_rate) }}</td>
                <td>{{ r.worst2_qty != null ? fmt(r.worst2_qty) : '—' }}</td>
                <td>{{ r.worst2_rate != null ? fmt(r.worst2_rate) : '—' }}</td>
                <td class="ss-cell">{{ fmt(r.safety_stock_90) }}</td>
                <td class="ss-cell">{{ fmt(r.safety_stock_95) }}</td>
                <td class="ss-cell">{{ fmt(r.safety_stock_99) }}</td>
                <td>{{ r.stable_days_mean != null ? r.stable_days_mean + '日' : '—' }}</td>
                <td>{{ r.stable_days_min != null ? r.stable_days_min + '日' : '—' }}</td>
                <td>{{ r.stable_days_max != null ? r.stable_days_max + '日' : '—' }}</td>
                <td>{{ r.stable_days_count ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/api/client'

// ---- 共通 ----
const activeTab = ref('analysis')
const products = ref([])

const fetchProducts = async () => {
  try {
    const res = await api.staging.getKubotaNaijiProducts()
    products.value = res.data || []
  } catch (e) {
    console.error('製品一覧取得失敗', e)
  }
}
fetchProducts()

// ---- タブ1: 変化推移分析 ----
const selectedProduct = ref('')
const startDate = ref('')
const endDate = ref('')
const loading = ref(false)
const error = ref('')
const analysisData = ref(null)
const selectedDueDate = ref('')

const svgW = 700
const svgH = 320
const padL = 55
const padR = 50
const padT = 20
const padB = 70

const onProductChange = () => {
  analysisData.value = null
  selectedDueDate.value = ''
  error.value = ''
}

const fetchAnalysis = async () => {
  if (!selectedProduct.value) return
  loading.value = true
  error.value = ''
  analysisData.value = null
  selectedDueDate.value = ''

  try {
    const params = { product_code: selectedProduct.value }
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value

    const res = await api.staging.getKubotaNaijiAnalysis(params)
    analysisData.value = res.data

    if (res.data.due_dates && res.data.due_dates.length > 0) {
      selectedDueDate.value = res.data.due_dates[0]
    }
  } catch (e) {
    error.value = e?.response?.data?.error || e.message || '取得エラー'
  } finally {
    loading.value = false
  }
}

const chartPoints = computed(() => {
  if (!analysisData.value || !selectedDueDate.value) return []
  const snaps = analysisData.value.snapshots
  const dd = selectedDueDate.value
  const pts = snaps
    .filter(s => s.quantities[dd] !== undefined)
    .map(s => ({ label: s.snapshot_date, qty: s.quantities[dd] }))
  if (pts.length === 0) return []
  const qtyList = pts.map(p => p.qty)
  const firmQty = analysisData.value.firm_quantities[dd]
  const allVals = firmQty !== undefined ? [...qtyList, firmQty] : qtyList
  const minQ = Math.min(...allVals)
  const maxQ = Math.max(...allVals)
  const qRange = maxQ - minQ || 1
  const innerW = svgW - padL - padR
  const innerH = svgH - padT - padB
  const step = pts.length > 1 ? innerW / (pts.length - 1) : 0
  return pts.map((p, i) => ({
    px: padL + (pts.length === 1 ? innerW / 2 : i * step),
    py: padT + innerH - ((p.qty - minQ) / qRange) * innerH,
    qty: p.qty,
    label: p.label,
  }))
})

const yGridLines = computed(() => {
  if (!analysisData.value || !selectedDueDate.value) return []
  const dd = selectedDueDate.value
  const snaps = analysisData.value.snapshots
  const qtyList = snaps.filter(s => s.quantities[dd] !== undefined).map(s => s.quantities[dd])
  const firmQty = analysisData.value.firm_quantities[dd]
  const allVals = firmQty !== undefined ? [...qtyList, firmQty] : qtyList
  if (allVals.length === 0) return []
  const minQ = Math.min(...allVals)
  const maxQ = Math.max(...allVals)
  const qRange = maxQ - minQ || 1
  const innerH = svgH - padT - padB
  const count = 5
  return Array.from({ length: count + 1 }, (_, i) => {
    const val = Math.round(minQ + (qRange / count) * i)
    const py = padT + innerH - ((val - minQ) / qRange) * innerH
    return { val, py }
  })
})

const firmY = computed(() => {
  if (!analysisData.value || !selectedDueDate.value) return null
  const dd = selectedDueDate.value
  const firmQty = analysisData.value.firm_quantities[dd]
  if (firmQty === undefined) return null
  const snaps = analysisData.value.snapshots
  const qtyList = snaps.filter(s => s.quantities[dd] !== undefined).map(s => s.quantities[dd])
  const allVals = [...qtyList, firmQty]
  const minQ = Math.min(...allVals)
  const maxQ = Math.max(...allVals)
  const qRange = maxQ - minQ || 1
  const innerH = svgH - padT - padB
  return padT + innerH - ((firmQty - minQ) / qRange) * innerH
})

const currentStat = computed(() => {
  if (!analysisData.value || !selectedDueDate.value) return null
  return analysisData.value.statistics[selectedDueDate.value] || null
})

const formatDate = (s) => s ? s.replace(/-/g, '/') : ''
const fmt = (v) => v === null || v === undefined ? '—' : v
const signFmt = (v) => { if (v === null || v === undefined) return '—'; return v > 0 ? `+${v}` : `${v}` }
const biasClass = (v) => { if (v === null || v === undefined) return ''; return v < -1 ? 'val-danger' : v > 1 ? 'val-info' : '' }
const biasNote = (v) => {
  if (v === null || v === undefined) return ''
  if (v < -1) return '→ 内示が体系的に少ない（欠品リスク）'
  if (v > 1) return '→ 内示が体系的に多い（過剰在庫傾向）'
  return '→ バイアスなし'
}
const shortFileName = (name) => {
  if (!name) return ''
  const parts = name.split(/[/\\]/)
  const base = parts[parts.length - 1]
  return base.length > 30 ? '...' + base.slice(-28) : base
}
const sign = (v) => { if (v === null || v === undefined) return '—'; return v > 0 ? `+${v}` : `${v}` }
const changeClass = (v) => { if (!v) return ''; return v > 0 ? 'up' : v < 0 ? 'down' : '' }
const deltaCellClass = (snap, dd) => {
  if (!analysisData.value || snap.quantities[dd] === undefined) return ''
  const snaps = analysisData.value.snapshots
  const idx = snaps.findIndex(s => s.source_file === snap.source_file)
  if (idx <= 0) return ''
  const prev = snaps[idx - 1]
  if (prev.quantities[dd] === undefined) return ''
  const diff = snap.quantities[dd] - prev.quantities[dd]
  if (diff > 0) return 'cell-up'
  if (diff < 0) return 'cell-down'
  return ''
}

// ---- タブ2: 一括分析レポート ----
const selectedCodes = ref([])
const rStartDate = ref('')
const rEndDate = ref('')
const exporting = ref(false)
const rErrorMsg = ref('')
const previewRows = ref([])

const selectAll = () => { selectedCodes.value = products.value.map(p => p.product_code) }
const clearAll  = () => { selectedCodes.value = [] }

const exportExcel = async () => {
  if (selectedCodes.value.length === 0) return
  exporting.value = true
  rErrorMsg.value = ''
  previewRows.value = []
  try {
    const params = {
      product_codes: selectedCodes.value.join(','),
      start_date: rStartDate.value || undefined,
      end_date: rEndDate.value || undefined,
    }
    const previewRes = await api.staging.getKubotaNaijiBatchPreview(params)
    previewRows.value = previewRes.data

    const res = await api.staging.downloadKubotaNaijiBatchReport(params)
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const period = [rStartDate.value, rEndDate.value].filter(Boolean).join('_')
    a.download = `クボタ内示分析_${period || '全期間'}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    rErrorMsg.value = e?.response?.data?.error || 'エラーが発生しました'
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.naiji-analysis {
  padding: 16px;
  font-size: 13px;
}
.page-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 12px;
  color: #1a3a7a;
}

/* タブバー */
.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid #1a5fb4;
  margin-bottom: 16px;
}
.tab-item {
  padding: 7px 20px;
  border: 1px solid #c5d5e8;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  background: #f0f4fa;
  cursor: pointer;
  font-size: 13px;
  color: #444;
  font-weight: 600;
}
.tab-item.active {
  background: #1a5fb4;
  color: #fff;
  border-color: #1a5fb4;
}
.tab-item:hover:not(.active) { background: #dce8f5; }

/* 検索パネル共通 */
.search-panel {
  background: #f5f7fa;
  border: 1px solid #dde3ee;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.search-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.search-label {
  font-weight: 600;
  color: #444;
  white-space: nowrap;
}
.field-label {
  font-size: 13px;
  font-weight: bold;
  color: #1a3a7a;
  min-width: 80px;
  padding-top: 4px;
}
.form-select {
  padding: 6px 8px;
  border: 1px solid #bbb;
  border-radius: 4px;
  min-width: 220px;
}
.form-input {
  padding: 6px 8px;
  border: 1px solid #bbb;
  border-radius: 4px;
  width: 130px;
}
.range-sep { color: #888; }
.btn-primary {
  padding: 7px 18px;
  background: #1a5fb4;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg { color: #c0392b; font-size: 12px; }

/* 製品チェックリスト */
.product-select-area {
  flex: 1;
  border: 1px solid #c5cfe4;
  border-radius: 4px;
  background: #fff;
  overflow: hidden;
}
.product-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  background: #e8eef7;
  border-bottom: 1px solid #c5cfe4;
}
.btn-sm {
  padding: 2px 10px;
  font-size: 12px;
  border: 1px solid #6c8cbf;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
  color: #284b8f;
}
.btn-sm:hover { background: #e0e8f5; }
.selected-count { font-size: 12px; color: #284b8f; margin-left: 6px; }
.product-list {
  max-height: 180px;
  overflow-y: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  padding: 6px;
}
.product-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  border: 1px solid transparent;
  min-width: 260px;
}
.product-item:hover { background: #ebf0f9; }
.product-item.selected { background: #ddeeff; border-color: #6699cc; }
.prod-code { font-weight: bold; color: #1a3a7a; min-width: 120px; }
.prod-name { color: #444; }
.no-products { padding: 10px; color: #888; font-size: 13px; }

.btn-export {
  padding: 8px 24px;
  background: #284b8f;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  font-weight: bold;
}
.btn-export:hover:not(:disabled) { background: #1a3a7a; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

/* 期間サマリー */
.period-summary {
  background: #fff;
  border: 2px solid #1a5fb4;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.period-summary .section-title { margin-bottom: 12px; }
.summary-sub { font-size: 12px; font-weight: normal; color: #666; margin-left: 8px; }
.summary-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #555;
}
.meta-sep { color: #bbb; }
.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
.summary-block {
  background: #f7f9fc;
  border: 1px solid #dde3ee;
  border-radius: 6px;
  padding: 10px 12px;
}
.safety-block { background: #f0f7ff; border-color: #7eb8f7; }
.block-title {
  font-size: 12px;
  font-weight: 700;
  color: #1a3a7a;
  margin-bottom: 8px;
  border-bottom: 1px solid #dde3ee;
  padding-bottom: 4px;
}
.block-rows { display: flex; flex-direction: column; gap: 5px; }
.block-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 12px;
}
.highlight-row {
  background: #e8f0ff;
  border-radius: 3px;
  padding: 2px 4px;
  margin: 0 -4px;
}
.block-label { color: #555; flex-shrink: 0; }
.block-val { font-weight: 600; color: #222; text-align: right; margin-left: 8px; }
.sigma-val { color: #1a5fb4; font-size: 14px; }
.ss-val { color: #1a5fb4; font-size: 13px; }
.val-danger { color: #c0392b; }
.val-info   { color: #2471a3; }
.bias-note { font-size: 10px; font-weight: normal; color: #888; display: block; text-align: right; }
.diff-date { font-size: 11px; font-weight: normal; color: #666; margin-left: 4px; }
.worst-dates-row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; padding: 2px 8px 6px 8px; }
.worst-dates-label { font-size: 11px; color: #888; white-space: nowrap; }
.worst-date-chip { font-size: 11px; background: #fce8e8; color: #a00; border-radius: 3px; padding: 1px 5px; white-space: nowrap; }
.block-note { font-size: 10px; color: #999; margin-top: 4px; }

/* 納期タブ */
.due-date-tabs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.tabs-label { font-weight: 600; color: #555; }
.tab-btn {
  padding: 4px 10px;
  border: 1px solid #bbb;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}
.tab-btn.active { background: #1a5fb4; color: #fff; border-color: #1a5fb4; }

/* コンテンツグリッド */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 16px;
  margin-bottom: 20px;
}
.chart-section {
  background: #fff;
  border: 1px solid #dde3ee;
  border-radius: 6px;
  padding: 12px;
}
.section-title { font-size: 14px; font-weight: 600; color: #1a3a7a; margin: 0 0 10px; }
.chart-wrap { overflow-x: auto; }
.chart-svg { display: block; height: auto; }

/* 統計テーブル */
.stat-section {
  background: #fff;
  border: 1px solid #dde3ee;
  border-radius: 6px;
  padding: 12px;
}
.stat-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.stat-table th, .stat-table td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; text-align: left; }
.stat-table th { color: #555; font-weight: normal; width: 55%; }
.stat-table .sep-row th { background: #f0f4fa; font-weight: 600; color: #1a3a7a; padding-top: 8px; }
.up { color: #e67e22; font-weight: 600; }
.down { color: #2980b9; font-weight: 600; }
.no-stat { color: #999; font-size: 12px; }

/* 詳細テーブル */
.detail-section {
  background: #fff;
  border: 1px solid #dde3ee;
  border-radius: 6px;
  padding: 12px;
}
.table-scroll { overflow-x: auto; max-height: 400px; overflow-y: auto; }
.detail-table { border-collapse: collapse; font-size: 12px; white-space: nowrap; }
.detail-table th, .detail-table td { border: 1px solid #e0e0e0; padding: 4px 8px; text-align: right; }
.detail-table thead th { background: #f0f4fa; position: sticky; top: 0; z-index: 2; cursor: default; }
.detail-table thead th:first-child, .detail-table thead th:nth-child(2) { text-align: left; }
.sticky-col { position: sticky; left: 0; background: #f7f9fc; z-index: 1; text-align: left !important; min-width: 90px; }
.sticky-col2 { position: sticky; left: 90px; background: #f7f9fc; z-index: 1; text-align: left !important; min-width: 160px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.date-cell { color: #555; }
.file-cell { color: #555; font-size: 11px; }
.qty-cell { color: #222; }
.empty-cell { color: #ccc; }
.active-col { background: #e8f0ff !important; }
.cell-up { color: #c0392b; font-weight: 600; }
.cell-down { color: #2471a3; font-weight: 600; }
.firm-row td, .firm-row th { background: #fff0f0 !important; font-weight: 600; color: #c0392b; }
.firm-cell { text-align: right; }
.placeholder { color: #999; padding: 20px; text-align: center; }

/* プレビューテーブル */
.preview-area { margin-top: 10px; }
.preview-title { font-size: 14px; font-weight: bold; color: #1a3a7a; margin-bottom: 8px; }
.table-wrap { overflow-x: auto; }
.preview-table { border-collapse: collapse; font-size: 12px; white-space: nowrap; min-width: 100%; }
.preview-table th, .preview-table td { border: 1px solid #ccc; padding: 4px 8px; text-align: center; }
.preview-table thead th { background: #1f4e79; color: #fff; }
.cat-error    { background: #2e75b6 !important; }
.cat-shortage { background: #c00000 !important; }
.cat-safety   { background: #375623 !important; }
.cat-stable   { background: #7030a0 !important; }
.preview-table tbody tr:nth-child(even) { background: #ebf3fb; }
.preview-table tbody tr:hover { background: #d0e4f7; }
.code-cell { text-align: left; font-weight: bold; color: #1a3a7a; }
.name-cell { text-align: left; }
</style>
