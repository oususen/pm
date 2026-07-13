<template>
  <div class="naiji-analysis">
    <h2 class="page-title">内示分析 <DataSourceDialog title="内示分析" :sources="dsSources" /></h2>

    <!-- 顧客選択 -->
    <div class="customer-bar">
      <label class="search-label">顧客</label>
      <select v-model="selectedCustomerId" class="form-select" @change="onCustomerChange">
        <option value="">-- 顧客を選択 --</option>
        <option v-for="c in customers" :key="c.id" :value="c.id">
          {{ c.customer_code }} / {{ c.customer_name || c.short_name }}
        </option>
      </select>
    </div>

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
              {{ p.product_code }}{{ p.product_name ? ` / ${p.product_name}` : '' }}{{ p.snapshot_count ? `（${p.snapshot_count}件）` : '' }}
            </option>
          </select>

          <label class="search-label">納入先</label>
          <select v-model="selectedShipTo" class="form-select form-select-ship-to">
            <option value="">全て</option>
            <option v-for="st in currentShipToList" :key="st" :value="st">{{ st }}</option>
          </select>

          <label class="search-label">納期</label>
          <input type="date" v-model="startDate" class="form-input" />
          <span class="range-sep">〜</span>
          <input type="date" v-model="endDate" class="form-input" />

          <button class="btn-primary" :disabled="!selectedProduct || !selectedCustomerId || loading" @click="fetchAnalysis">
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
              <div class="block-title">欠品リスク（収束直前の内示 ＜ 確定）</div>
              <div class="block-rows">
                <div class="block-row">
                  <span class="block-label">収束直前過小率</span>
                  <span class="block-val" :class="analysisData.period_summary.pre_converge_shortage_rate > 30 ? 'val-danger' : ''">
                    {{ fmt(analysisData.period_summary.pre_converge_shortage_rate) }} %
                    （{{ analysisData.period_summary.pre_converge_shortage_count }} / {{ analysisData.period_summary.pre_converge_total }} 納期）
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
                  ※ 各納期について、内示が確定値と一致してから納期まで連続して変わらなかった営業日数
                </div>
                <div class="block-row highlight-row">
                  <span class="block-label">平均</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_mean != null ? analysisData.period_summary.stable_days_mean + ' 日' : '—' }}
                  </span>
                </div>
                <div class="block-row highlight-row">
                  <span class="block-label">中央値</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_median != null ? analysisData.period_summary.stable_days_median + ' 日' : '—' }}
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">標準偏差</span>
                  <span class="block-val">
                    {{ analysisData.period_summary.stable_days_std != null ? analysisData.period_summary.stable_days_std + ' 日' : '—' }}
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
                <template v-if="analysisData.period_summary.stable_days_dist">
                  <div class="block-subtitle" style="margin-top:8px; font-weight:600; font-size:12px; color:#666;">分布</div>
                  <div class="block-row" :class="{ 'dist-danger': analysisData.period_summary.stable_days_dist.within_7 > 0 }">
                    <span class="block-label">7日以内</span>
                    <span class="block-val">
                      {{ analysisData.period_summary.stable_days_dist.within_7 }}件（{{ analysisData.period_summary.stable_days_dist.within_7_pct }}%）
                      <small class="dist-note">材料調達に間に合わない</small>
                    </span>
                  </div>
                  <div
                    v-if="analysisData.period_summary.stable_days_dist.within_7_dates?.length"
                    class="dist-dates-row"
                  >
                    <span class="dist-dates-label">納期日：</span>
                    <span
                      v-for="d in analysisData.period_summary.stable_days_dist.within_7_dates"
                      :key="d"
                      class="dist-date-chip"
                    >{{ d }}</span>
                  </div>
                  <div class="block-row" :class="{ 'dist-warning': analysisData.period_summary.stable_days_dist.within_8_14 > 0 }">
                    <span class="block-label">8〜14日</span>
                    <span class="block-val">
                      {{ analysisData.period_summary.stable_days_dist.within_8_14 }}件（{{ analysisData.period_summary.stable_days_dist.within_8_14_pct }}%）
                      <small class="dist-note">ギリギリ</small>
                    </span>
                  </div>
                  <div class="block-row">
                    <span class="block-label">15〜21日</span>
                    <span class="block-val">
                      {{ analysisData.period_summary.stable_days_dist.within_15_21 }}件（{{ analysisData.period_summary.stable_days_dist.within_15_21_pct }}%）
                    </span>
                  </div>
                  <div class="block-row dist-ok">
                    <span class="block-label">22日以上</span>
                    <span class="block-val">
                      {{ analysisData.period_summary.stable_days_dist.over_21 }}件（{{ analysisData.period_summary.stable_days_dist.over_21_pct }}%）
                      <small class="dist-note">問題なし</small>
                    </span>
                  </div>
                </template>
              </div>
            </div>

            <!-- 遅延率ブロック -->
            <div class="summary-block">
              <div class="block-title">遅延率</div>
              <div class="block-rows">
                <div class="block-note" style="margin-bottom:6px;">
                  ※ 確定日の遅れ傾向を2指標で表示
                </div>
                <div class="block-row highlight-row">
                  <span class="block-label">確定日＜5日</span>
                  <span class="block-val" :style="{ color: (analysisData.period_summary.firm_due_lt5_rate || 0) > 30 ? '#d32f2f' : '' }">
                    {{ analysisData.period_summary.firm_due_lt5_rate != null ? analysisData.period_summary.firm_due_lt5_rate + ' %' : '—' }}
                    <small v-if="analysisData.period_summary.firm_due_lt5_total != null" class="diff-date">
                      （{{ analysisData.period_summary.firm_due_lt5_count }} / {{ analysisData.period_summary.firm_due_lt5_total }} 納期）
                    </small>
                  </span>
                </div>
                <div class="block-row">
                  <span class="block-label">確定一致日≥確定日</span>
                  <span class="block-val" :style="{ color: (analysisData.period_summary.firm_converge_on_or_after_firm_rate || 0) > 30 ? '#d32f2f' : '' }">
                    {{ analysisData.period_summary.firm_converge_on_or_after_firm_rate != null ? analysisData.period_summary.firm_converge_on_or_after_firm_rate + ' %' : '—' }}
                    <small v-if="analysisData.period_summary.firm_converge_on_or_after_firm_total != null" class="diff-date">
                      （{{ analysisData.period_summary.firm_converge_on_or_after_firm_count }} / {{ analysisData.period_summary.firm_converge_on_or_after_firm_total }} 納期）
                    </small>
                  </span>
                </div>
                <div
                  v-if="analysisData.period_summary.firm_converge_on_or_after_firm_dates?.length"
                  class="dist-dates-row"
                >
                  <span class="dist-dates-label">納期日：</span>
                  <span
                    v-for="d in analysisData.period_summary.firm_converge_on_or_after_firm_dates"
                    :key="d"
                    class="dist-date-chip"
                  >{{ d }}</span>
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
                <polyline
                  v-if="chartPoints.length >= 2"
                  :points="chartPoints.map(p => `${p.px},${p.py}`).join(' ')"
                  fill="none"
                  stroke="#1a5fb4"
                  stroke-width="2"
                />
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
          <div class="section-title-row">
            <h3 class="section-title">スナップショット一覧（全納期）</h3>
            <button class="btn-export-small" @click="exportSnapshotExcel">📥 Excel出力</button>
          </div>
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
                <!-- 確定一致日行 -->
                <tr class="converge-row">
                  <th class="sticky-col converge-header">確定一致日</th>
                  <th class="sticky-col2">—</th>
                  <td
                    v-for="dd in analysisData.due_dates"
                    :key="'converge-' + dd"
                    :class="{ 'active-col': dd === selectedDueDate }"
                    class="converge-cell"
                  >{{ firmConvergeDates[dd] ? firmConvergeDates[dd].slice(5).replace('-', '/') : '—' }}</td>
                </tr>
                <!-- 確定日行 -->
                <tr class="converge-row">
                  <th class="sticky-col converge-header">確定日</th>
                  <th class="sticky-col2">—</th>
                  <td
                    v-for="dd in analysisData.due_dates"
                    :key="'firmdate-' + dd"
                    :class="{ 'active-col': dd === selectedDueDate }"
                    class="converge-cell"
                  >{{ firmIssueDates[dd] ? firmIssueDates[dd].slice(5).replace('-', '/') : '—' }}</td>
                </tr>
              </thead>
              <tbody>
                <tr v-for="snap in analysisData.snapshots" :key="snap.source_file">
                  <td class="sticky-col date-cell">{{ snap.snapshot_date }}</td>
                  <td class="sticky-col2 file-cell" :title="snap.source_file">{{ shortFileName(snap.source_file) }}</td>
                  <td
                    v-for="dd in analysisData.due_dates"
                    :key="dd"
                    :class="['qty-cell', { 'active-col': dd === selectedDueDate }, deltaCellClass(snap, dd), { 'cell-converge': firmConvergeDates[dd] === snap.snapshot_date }]"
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

      <div v-else-if="!loading && selectedProduct && selectedCustomerId" class="placeholder">
        条件を設定して「分析実行」を押してください
      </div>
      <div v-else-if="!selectedCustomerId" class="placeholder">
        顧客を選択してください
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
            <div class="product-list" v-if="batchProductItems.length">
              <label
                v-for="item in batchProductItems"
                :key="item.key"
                class="product-item"
                :class="{ selected: selectedCodes.includes(item.key) }"
              >
                <input type="checkbox" :value="item.key" v-model="selectedCodes" />
                <span class="prod-code">{{ item.product_code }}</span>
                <span v-if="item.ship_to" class="prod-ship-to">({{ item.ship_to }})</span>
                <span class="prod-name">{{ item.product_name }}</span>
              </label>
            </div>
            <div v-else class="no-products">{{ selectedCustomerId ? '読み込み中...' : '顧客を選択してください' }}</div>
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
            :disabled="exporting || selectedCodes.length === 0 || !selectedCustomerId"
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
                <th colspan="5" class="cat-firm-stable">安定日数</th>
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
                <th class="cat-firm-stable">平均日</th>
                <th class="cat-firm-stable">最短日</th>
                <th class="cat-firm-stable">最長日</th>
                <th class="cat-firm-stable">件数</th>
                <th class="cat-firm-stable">マイナス率%</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, idx) in previewRows" :key="r.product_code + (r.ship_to || '') + idx">
                <td class="code-cell">{{ r.product_code }}<small v-if="r.ship_to" style="color:#888;margin-left:4px">({{ r.ship_to }})</small></td>
                <td class="name-cell">{{ r.product_name }}</td>
                <td>{{ fmt(r.max_diff) }}</td>
                <td>{{ fmt(r.min_diff) }}</td>
                <td>{{ fmt(r.mae) }}</td>
                <td>{{ fmt(r.mean_error) }}</td>
                <td>{{ fmt(r.sigma) }}</td>
                <td>{{ r.snapshot_count }}</td>
                <td>{{ r.analyzed_dates }}</td>
                <td>{{ fmt(r.pre_converge_shortage_rate) }}</td>
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
                <td class="cat-firm-stable-cell">{{ r.firm_stable_days_mean != null ? r.firm_stable_days_mean + '日' : '—' }}</td>
                <td class="cat-firm-stable-cell">
                  {{ r.firm_stable_days_min != null ? r.firm_stable_days_min + '日' : '—' }}
                  <small v-if="r.firm_stable_days_min_date" class="diff-date">（{{ r.firm_stable_days_min_date }}）</small>
                </td>
                <td class="cat-firm-stable-cell">
                  {{ r.firm_stable_days_max != null ? r.firm_stable_days_max + '日' : '—' }}
                  <small v-if="r.firm_stable_days_max_date" class="diff-date">（{{ r.firm_stable_days_max_date }}）</small>
                </td>
                <td class="cat-firm-stable-cell">{{ r.firm_stable_days_count ?? '—' }}</td>
                <td class="cat-firm-stable-cell">{{ r.firm_stable_days_negative_rate != null ? r.firm_stable_days_negative_rate + '%' : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ===== 信憑性分析チャート ===== -->
      <div v-if="previewRows.length" class="credibility-section">
        <h3 class="cred-title">📈 内示信憑性分析</h3>
        <p class="cred-note">各指標を0〜100にスコア化（高いほど良い）。スコアは選択製品内の相対評価です。</p>

        <div class="cred-charts-row">
          <div class="cred-chart-card">
            <h4 class="cred-chart-title">① 総合信憑性レーダー</h4>
            <p class="cred-chart-note">面積が大きい ＝ 総合的に信頼できる内示</p>
            <canvas ref="radarChartRef"></canvas>
          </div>
          <div class="cred-chart-card">
            <h4 class="cred-chart-title">② 信憑性スコアランキング</h4>
            <p class="cred-chart-note">5指標のスタック表示（合計500点満点）</p>
            <canvas ref="barChartRef"></canvas>
          </div>
        </div>

        <div class="cred-charts-row">
          <div class="cred-chart-card cred-chart-full">
            <h4 class="cred-chart-title">③ リスクマップ（バブルチャート）</h4>
            <p class="cred-chart-note">右下・小バブルが理想　｜　X軸：収束安定期間 平均日（大きいほど良）　Y軸：過小率%（低いほど良）　バブルサイズ：MAE</p>
            <canvas ref="bubbleChartRef" style="max-height:320px"></canvas>
          </div>
        </div>

        <!-- スコアテーブル -->
        <div class="cred-score-wrap">
          <table class="cred-score-table">
            <thead>
              <tr>
                <th>順位</th>
                <th>品番</th>
                <th>品名</th>
                <th class="score-th">精度<br><small>MAE低</small></th>
                <th class="score-th">偏り少<br><small>平均差低</small></th>
                <th class="score-th">低リスク<br><small>過小率低</small></th>
                <th class="score-th">収束速度<br><small>安定期間長</small></th>
                <th class="score-th">予見性<br><small>マイナス率低</small></th>
                <th class="score-th total-th">総合スコア</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(s, i) in sortedScores" :key="s.product_code">
                <td class="rank-cell">{{ i + 1 }}</td>
                <td class="code-cell">{{ s.product_code }}</td>
                <td class="name-cell">{{ s.product_name }}</td>
                <td :class="['score-td', scoreClass(s.accuracy)]">{{ s.accuracy }}</td>
                <td :class="['score-td', scoreClass(s.bias)]">{{ s.bias }}</td>
                <td :class="['score-td', scoreClass(s.risk)]">{{ s.risk }}</td>
                <td :class="['score-td', scoreClass(s.convergence)]">{{ s.convergence }}</td>
                <td :class="['score-td', scoreClass(s.predictability)]">{{ s.predictability }}</td>
                <td :class="['score-td', 'total-td', scoreClass(s.composite)]"><strong>{{ s.composite }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import * as XLSX from 'xlsx'

const dsSources = [
  { op: '読み取り', table: 'stg_order_daily', desc: '日次受注ステージング（内示分析）' },
]
import {
  Chart,
  RadarController, LineElement, PointElement, RadialLinearScale, Filler,
  BubbleController, LinearScale,
  BarController, BarElement, CategoryScale,
  Tooltip, Legend,
} from 'chart.js'
Chart.register(
  RadarController, LineElement, PointElement, RadialLinearScale, Filler,
  BubbleController, LinearScale,
  BarController, BarElement, CategoryScale,
  Tooltip, Legend,
)

// ---- 顧客選択 ----
const customers = ref([])
const selectedCustomerId = ref('')

const fetchCustomers = async () => {
  try {
    const res = await api.staging.getNaijiCustomers()
    customers.value = res.data || []
  } catch (e) {
    console.error('顧客一覧取得失敗', e)
  }
}
fetchCustomers()

const onCustomerChange = () => {
  selectedProduct.value = ''
  analysisData.value = null
  selectedDueDate.value = ''
  products.value = []
  selectedCodes.value = []
  previewRows.value = []
  if (selectedCustomerId.value) {
    fetchProducts()
  }
}

// ---- 共通 ----
const activeTab = ref('analysis')
const products = ref([])

const fetchProducts = async () => {
  if (!selectedCustomerId.value) return
  try {
    const res = await api.staging.getNaijiProducts({ customer_id: selectedCustomerId.value })
    products.value = res.data || []
  } catch (e) {
    console.error('製品一覧取得失敗', e)
  }
}

// ---- タブ1: 変化推移分析 ----
const selectedProduct = ref('')
const selectedShipTo = ref('')
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

const currentShipToList = computed(() => {
  const p = products.value.find(p => p.product_code === selectedProduct.value)
  return p?.ship_to_list || []
})

const onProductChange = () => {
  analysisData.value = null
  selectedDueDate.value = ''
  selectedShipTo.value = ''
  error.value = ''
}

const fetchAnalysis = async () => {
  if (!selectedProduct.value || !selectedCustomerId.value) return
  loading.value = true
  error.value = ''
  analysisData.value = null
  selectedDueDate.value = ''

  try {
    const params = {
      customer_id: selectedCustomerId.value,
      product_code: selectedProduct.value,
    }
    if (selectedShipTo.value) params.ship_to = selectedShipTo.value
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value

    const res = await api.staging.getNaijiAnalysis(params)
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

const firmConvergeDates = computed(() => analysisData.value?.converge_dates || {})
const firmIssueDates = computed(() => analysisData.value?.firm_dates || {})

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

const batchProductItems = computed(() => {
  const items = []
  for (const p of products.value) {
    const shipToList = p.ship_to_list || []
    if (shipToList.length <= 1) {
      items.push({
        key: shipToList.length === 1 ? `${p.product_code}:${shipToList[0]}` : p.product_code,
        product_code: p.product_code,
        product_name: p.product_name,
        ship_to: shipToList.length === 1 ? shipToList[0] : '',
      })
    } else {
      for (const st of shipToList) {
        items.push({
          key: `${p.product_code}:${st}`,
          product_code: p.product_code,
          product_name: p.product_name,
          ship_to: st,
        })
      }
    }
  }
  return items
})

const selectAll = () => { selectedCodes.value = batchProductItems.value.map(i => i.key) }
const clearAll  = () => { selectedCodes.value = [] }

const exportSnapshotExcel = () => {
  const data = analysisData.value
  if (!data) return

  const dueDates = data.due_dates || []
  const header = ['取込日', 'ソースファイル', ...dueDates]
  const firmRow = ['確定', '—', ...dueDates.map(dd =>
    data.firm_quantities[dd] !== undefined ? data.firm_quantities[dd] : ''
  )]
  const snapRows = (data.snapshots || []).map(snap => [
    snap.snapshot_date,
    snap.source_file,
    ...dueDates.map(dd => snap.quantities[dd] !== undefined ? snap.quantities[dd] : ''),
  ])

  const wsData = [header, firmRow, ...snapRows]
  const ws = XLSX.utils.aoa_to_sheet(wsData)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'スナップショット一覧')

  const customerName = customers.value.find(c => c.id == selectedCustomerId.value)?.customer_name || ''
  const filename = `${customerName}_内示_${selectedProduct.value}_スナップショット.xlsx`
  XLSX.writeFile(wb, filename)
}

const exportExcel = async () => {
  if (selectedCodes.value.length === 0 || !selectedCustomerId.value) return
  exporting.value = true
  rErrorMsg.value = ''
  previewRows.value = []
  try {
    const params = {
      customer_id: selectedCustomerId.value,
      product_codes: selectedCodes.value.join(','),
      start_date: rStartDate.value || undefined,
      end_date: rEndDate.value || undefined,
    }
    const previewRes = await api.staging.getNaijiBatchPreview(params)
    previewRows.value = previewRes.data

    const res = await api.staging.downloadNaijiBatchReport(params)
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const period = [rStartDate.value, rEndDate.value].filter(Boolean).join('_')
    a.download = `内示分析_${period || '全期間'}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    rErrorMsg.value = e?.response?.data?.error || 'エラーが発生しました'
  } finally {
    exporting.value = false
  }
}

// ===== 信憑性分析チャート =====
const CHART_COLORS = [
  '#2563eb','#dc2626','#16a34a','#d97706','#7c3aed',
  '#0891b2','#db2777','#65a30d','#ea580c','#6b7280',
]

const radarChartRef  = ref(null)
const barChartRef    = ref(null)
const bubbleChartRef = ref(null)
let radarChart = null, barChartInst = null, bubbleChart = null

const credibilityScores = computed(() => {
  const rows = previewRows.value.filter(r => r.mae != null)
  if (!rows.length) return []

  const maes      = rows.map(r => r.mae || 0)
  const meanErrs  = rows.map(r => Math.abs(r.mean_error || 0))
  const stables   = rows.map(r => r.stable_days_mean || 0)
  const maxMAE      = Math.max(...maes) || 1
  const maxMeanErr  = Math.max(...meanErrs) || 1
  const maxStable   = Math.max(...stables) || 1

  return rows.map(r => {
    const accuracy      = Math.round(Math.max(0, (1 - (r.mae || 0) / maxMAE) * 100))
    const bias          = Math.round(Math.max(0, (1 - Math.abs(r.mean_error || 0) / maxMeanErr) * 100))
    const risk          = Math.round(Math.max(0, 100 - (r.pre_converge_shortage_rate || 0)))
    const convergence   = Math.round(Math.max(0, ((r.stable_days_mean || 0) / maxStable) * 100))
    const predictability = Math.round(Math.max(0, 100 - (r.firm_stable_days_negative_rate || 0)))
    const composite     = Math.round((accuracy + bias + risk + convergence + predictability) / 5)
    return { product_code: r.product_code, product_name: r.product_name,
             accuracy, bias, risk, convergence, predictability, composite, _raw: r }
  })
})

const sortedScores = computed(() =>
  [...credibilityScores.value].sort((a, b) => b.composite - a.composite)
)

function scoreClass(val) {
  if (val >= 75) return 'score-high'
  if (val >= 45) return 'score-mid'
  return 'score-low'
}

async function updateCharts() {
  await nextTick()
  const scores = credibilityScores.value
  if (!scores.length) return
  buildRadarChart(scores)
  buildBarChart(scores)
  buildBubbleChart(scores)
}

function buildRadarChart(scores) {
  if (!radarChartRef.value) return
  if (radarChart) { radarChart.destroy(); radarChart = null }
  radarChart = new Chart(radarChartRef.value, {
    type: 'radar',
    data: {
      labels: ['精度', '偏り少', '低リスク', '収束速度', '予見性'],
      datasets: scores.map((s, i) => ({
        label: s.product_code,
        data: [s.accuracy, s.bias, s.risk, s.convergence, s.predictability],
        borderColor: CHART_COLORS[i % CHART_COLORS.length],
        backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '22',
        borderWidth: 2, pointRadius: 3,
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      scales: { r: { min: 0, max: 100, ticks: { stepSize: 25, font: { size: 10 } }, pointLabels: { font: { size: 12 } } } },
      plugins: { legend: { position: 'right', labels: { font: { size: 10 }, boxWidth: 12 } } },
    },
  })
}

function buildBarChart(scores) {
  if (!barChartRef.value) return
  if (barChartInst) { barChartInst.destroy(); barChartInst = null }
  const sorted = [...scores].sort((a, b) => b.composite - a.composite)
  const defs = [
    { key: 'accuracy',      label: '精度',    color: '#2563eb' },
    { key: 'bias',          label: '偏り少',  color: '#16a34a' },
    { key: 'risk',          label: '低リスク', color: '#dc2626' },
    { key: 'convergence',   label: '収束速度', color: '#7c3aed' },
    { key: 'predictability',label: '予見性',  color: '#d97706' },
  ]
  barChartInst = new Chart(barChartRef.value, {
    type: 'bar',
    data: {
      labels: sorted.map(s => s.product_code),
      datasets: defs.map(d => ({
        label: d.label,
        data: sorted.map(s => s[d.key]),
        backgroundColor: d.color + 'cc',
        borderColor: d.color,
        borderWidth: 1,
      })),
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      scales: {
        x: { stacked: true, max: 500, ticks: { font: { size: 10 } } },
        y: { stacked: true, ticks: { font: { size: 10 } } },
      },
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            footer: items => `総合スコア: ${Math.round(items.reduce((s, i) => s + i.raw, 0) / 5)}`,
          },
        },
      },
    },
  })
}

function buildBubbleChart(scores) {
  if (!bubbleChartRef.value) return
  if (bubbleChart) { bubbleChart.destroy(); bubbleChart = null }
  const maxMAE = Math.max(...scores.map(s => s._raw.mae || 0)) || 1
  bubbleChart = new Chart(bubbleChartRef.value, {
    type: 'bubble',
    data: {
      datasets: scores.map((s, i) => ({
        label: s.product_code,
        data: [{
          x: s._raw.stable_days_mean || 0,
          y: s._raw.shortage_rate || 0,
          r: Math.max(6, ((s._raw.mae || 0) / maxMAE) * 28),
        }],
        backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '99',
        borderColor:     CHART_COLORS[i % CHART_COLORS.length],
        borderWidth: 2,
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      scales: {
        x: { title: { display: true, text: '収束安定期間 平均日（大きいほど良）', font: { size: 11 } }, ticks: { font: { size: 10 } } },
        y: { title: { display: true, text: '過小率%（小さいほど良）', font: { size: 11 } }, ticks: { font: { size: 10 } } },
      },
      plugins: {
        legend: { position: 'right', labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const s = scores[ctx.datasetIndex]
              return [`${s.product_code}  ${s.product_name}`,
                      `収束: ${ctx.raw.x}日  過小率: ${ctx.raw.y}%  MAE: ${s._raw.mae}`]
            },
          },
        },
      },
    },
  })
}

watch(previewRows, val => { if (val.length) updateCharts() })

onUnmounted(() => {
  if (radarChart)    radarChart.destroy()
  if (barChartInst)  barChartInst.destroy()
  if (bubbleChart)   bubbleChart.destroy()
})
</script>

<style scoped>
.section-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.section-title-row .section-title { margin-bottom: 0; }
.converge-row { background: #f0fdf4; }
.converge-header { font-size: 11px; color: #166534; white-space: nowrap; }
.converge-cell { font-size: 11px; color: #166534; font-weight: 600; text-align: center; }
.cell-converge { background: #bbf7d0 !important; font-weight: 700; outline: 2px solid #16a34a; }
.btn-export-small { padding: 4px 10px; font-size: 12px; background: #217346; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-export-small:hover { background: #1a5c38; }
.naiji-analysis { padding: 16px; font-size: 13px; }
.page-title { font-size: 18px; font-weight: bold; margin-bottom: 12px; color: #1a3a7a; }

.customer-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding: 8px 12px; background: #e8f0ff; border: 1px solid #b0c8e8; border-radius: 6px; }

.tab-bar { display: flex; gap: 4px; border-bottom: 2px solid #1a5fb4; margin-bottom: 16px; }
.tab-item { padding: 7px 20px; border: 1px solid #c5d5e8; border-bottom: none; border-radius: 6px 6px 0 0; background: #f0f4fa; cursor: pointer; font-size: 13px; color: #444; font-weight: 600; }
.tab-item.active { background: #1a5fb4; color: #fff; border-color: #1a5fb4; }
.tab-item:hover:not(.active) { background: #dce8f5; }

.search-panel { background: #f5f7fa; border: 1px solid #dde3ee; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; display: flex; flex-direction: column; gap: 10px; }
.search-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.search-label { font-weight: 600; color: #444; white-space: nowrap; }
.field-label { font-size: 13px; font-weight: bold; color: #1a3a7a; min-width: 80px; padding-top: 4px; }
.form-select { padding: 6px 8px; border: 1px solid #bbb; border-radius: 4px; min-width: 220px; }
.form-select-ship-to { min-width: 100px; }
.form-input { padding: 6px 8px; border: 1px solid #bbb; border-radius: 4px; width: 130px; }
.range-sep { color: #888; }
.btn-primary { padding: 7px 18px; background: #1a5fb4; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg { color: #c0392b; font-size: 12px; }

.product-select-area { flex: 1; border: 1px solid #c5cfe4; border-radius: 4px; background: #fff; overflow: hidden; }
.product-toolbar { display: flex; align-items: center; gap: 8px; padding: 5px 10px; background: #e8eef7; border-bottom: 1px solid #c5cfe4; }
.btn-sm { padding: 2px 10px; font-size: 12px; border: 1px solid #6c8cbf; border-radius: 3px; background: #fff; cursor: pointer; color: #284b8f; }
.btn-sm:hover { background: #e0e8f5; }
.selected-count { font-size: 12px; color: #284b8f; margin-left: 6px; }
.product-list { max-height: 180px; overflow-y: auto; display: flex; flex-wrap: wrap; gap: 2px; padding: 6px; }
.product-item { display: flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 3px; cursor: pointer; font-size: 12px; border: 1px solid transparent; min-width: 260px; }
.product-item:hover { background: #ebf0f9; }
.product-item.selected { background: #ddeeff; border-color: #6699cc; }
.prod-code { font-weight: bold; color: #1a3a7a; min-width: 120px; }
.prod-name { color: #444; }
.prod-ship-to { color: #1976d2; font-size: 11px; font-weight: 600; }
.no-products { padding: 10px; color: #888; font-size: 13px; }

.btn-export { padding: 8px 24px; background: #284b8f; color: #fff; border: none; border-radius: 4px; font-size: 14px; cursor: pointer; font-weight: bold; }
.btn-export:hover:not(:disabled) { background: #1a3a7a; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

.period-summary { background: #fff; border: 2px solid #1a5fb4; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
.period-summary .section-title { margin-bottom: 12px; }
.summary-sub { font-size: 12px; font-weight: normal; color: #666; margin-left: 8px; }
.summary-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; font-size: 13px; color: #555; }
.meta-sep { color: #bbb; }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.summary-block { background: #f7f9fc; border: 1px solid #dde3ee; border-radius: 6px; padding: 10px 12px; }
.safety-block { background: #f0f7ff; border-color: #7eb8f7; }
.block-title { font-size: 12px; font-weight: 700; color: #1a3a7a; margin-bottom: 8px; border-bottom: 1px solid #dde3ee; padding-bottom: 4px; }
.block-rows { display: flex; flex-direction: column; gap: 5px; }
.block-row { display: flex; justify-content: space-between; align-items: baseline; font-size: 12px; }
.highlight-row { background: #e8f0ff; border-radius: 3px; padding: 2px 4px; margin: 0 -4px; }
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
.block-subtitle { margin-top: 6px; }
.dist-danger { background: #fff0f0; }
.dist-danger .block-val { color: #d32f2f; font-weight: 600; }
.dist-warning { background: #fff8e1; }
.dist-warning .block-val { color: #f57f17; font-weight: 600; }
.dist-ok .block-val { color: #2e7d32; }
.dist-note { font-size: 10px; color: #999; margin-left: 4px; }
.dist-dates-row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; padding: 2px 8px 6px 8px; }
.dist-dates-label { font-size: 11px; color: #888; white-space: nowrap; }
.dist-date-chip { font-size: 11px; background: #fce8e8; color: #a00; border-radius: 3px; padding: 1px 5px; white-space: nowrap; }

.due-date-tabs { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.tabs-label { font-weight: 600; color: #555; }
.tab-btn { padding: 4px 10px; border: 1px solid #bbb; border-radius: 12px; background: #fff; cursor: pointer; font-size: 12px; }
.tab-btn.active { background: #1a5fb4; color: #fff; border-color: #1a5fb4; }

.content-grid { display: grid; grid-template-columns: 1fr 260px; gap: 16px; margin-bottom: 20px; }
.chart-section { background: #fff; border: 1px solid #dde3ee; border-radius: 6px; padding: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: #1a3a7a; margin: 0 0 10px; }
.chart-wrap { overflow-x: auto; }
.chart-svg { display: block; height: auto; }

.stat-section { background: #fff; border: 1px solid #dde3ee; border-radius: 6px; padding: 12px; }
.stat-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.stat-table th, .stat-table td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; text-align: left; }
.stat-table th { color: #555; font-weight: normal; width: 55%; }
.stat-table .sep-row th { background: #f0f4fa; font-weight: 600; color: #1a3a7a; padding-top: 8px; }
.up { color: #e67e22; font-weight: 600; }
.down { color: #2980b9; font-weight: 600; }
.no-stat { color: #999; font-size: 12px; }

.detail-section { background: #fff; border: 1px solid #dde3ee; border-radius: 6px; padding: 12px; }
.table-scroll { overflow-x: auto; max-height: 400px; overflow-y: auto; }
.detail-table { border-collapse: collapse; font-size: 12px; white-space: nowrap; }
.detail-table th, .detail-table td { border: 1px solid #e0e0e0; padding: 4px 8px; text-align: right; }
.detail-table thead th, .detail-table thead td { background: #f0f4fa; position: sticky; z-index: 2; cursor: default; }
.detail-table thead tr:nth-child(1) th, .detail-table thead tr:nth-child(1) td { top: 0; }
.detail-table thead tr:nth-child(2) th, .detail-table thead tr:nth-child(2) td { top: 25px; }
.detail-table thead tr:nth-child(3) th, .detail-table thead tr:nth-child(3) td { top: 50px; }
.detail-table thead tr:nth-child(4) th, .detail-table thead tr:nth-child(4) td { top: 75px; }
.detail-table thead th:first-child, .detail-table thead th:nth-child(2) { text-align: left; }
.sticky-col { position: sticky; left: 0; background: #f7f9fc; z-index: 1; text-align: left !important; min-width: 90px; }
.sticky-col2 { position: sticky; left: 90px; background: #f7f9fc; z-index: 1; text-align: left !important; min-width: 160px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.detail-table thead .sticky-col,
.detail-table thead .sticky-col2 { z-index: 3; }
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
.cat-firm-stable { background: #bf8f00 !important; }
.cat-firm-stable-cell { background: #fff8e1; }
.preview-table tbody tr:nth-child(even) { background: #ebf3fb; }
.preview-table tbody tr:hover { background: #d0e4f7; }
.code-cell { text-align: left; font-weight: bold; color: #1a3a7a; }
.name-cell { text-align: left; }
.ss-cell { font-weight: 600; color: #1a5fb4; }

.credibility-section { margin-top: 24px; padding: 16px; background: #f8faff; border: 1px solid #dde3ee; border-radius: 8px; }
.cred-title { font-size: 16px; font-weight: 700; color: #1a3a7a; margin: 0 0 4px; }
.cred-note  { font-size: 12px; color: #666; margin: 0 0 16px; }
.cred-charts-row { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.cred-chart-card { flex: 1; min-width: 320px; background: #fff; border: 1px solid #e0e7f0; border-radius: 6px; padding: 12px; }
.cred-chart-full { flex: 1 1 100%; }
.cred-chart-title { font-size: 13px; font-weight: 700; color: #1a3a7a; margin: 0 0 2px; }
.cred-chart-note  { font-size: 11px; color: #888; margin: 0 0 10px; }

.cred-score-wrap { overflow-x: auto; }
.cred-score-table { border-collapse: collapse; font-size: 12px; width: 100%; white-space: nowrap; }
.cred-score-table th, .cred-score-table td { border: 1px solid #dde3ee; padding: 5px 10px; text-align: center; }
.cred-score-table thead th { background: #1f4e79; color: #fff; font-size: 11px; }
.score-th { min-width: 70px; }
.total-th { background: #0d3561 !important; }
.rank-cell { font-weight: 700; color: #555; }
.score-td { font-weight: 600; font-size: 13px; }
.total-td { font-size: 14px; }
.score-high { background: #d4edda; color: #155724; }
.score-mid  { background: #fff3cd; color: #856404; }
.score-low  { background: #f8d7da; color: #721c24; }
</style>
