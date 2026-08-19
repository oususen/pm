<template>
  <div class="master-menu trend-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">傾向確認・分析</h2>
        <p class="helper-text">工程一体チェックシート実績から集計</p>
      </div>
      <button class="btn-secondary" @click="loadData" :disabled="loading">{{ loading ? "更新中..." : "更新" }}</button>
    </div>
    <div v-if="error" class="helper-text" style="color:#b91c1c;">{{ error }}</div>
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
      <label class="check-label">
        <input v-model="showOnlyReworkRows" type="checkbox" />
        <span>修正流動ありのみ表示</span>
      </label>
      <label>
        <span class="field-label">お気に入り</span>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">-- 選択 --</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">{{ fav.name }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">登録名</span>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
      </label>
      <button class="btn favorite-star-btn" title="お気に入り登録" :disabled="loading" @click="saveFavorite">★</button>
    </div>

    <!-- KPI サマリーカード -->
    <div class="kpi-cards">
      <div class="kpi-card">
        <div class="kpi-label">判定総数</div>
        <div class="kpi-value">{{ kpi.total.toLocaleString() }}</div>
        <div class="kpi-sub">対象期間内</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">修正流動率</div>
        <div class="kpi-value">{{ kpi.reworkRate.toFixed(1) }}%</div>
        <div :class="['kpi-trend', kpi.reworkDiff > 0.05 ? 'worse' : kpi.reworkDiff < -0.05 ? 'better' : 'flat']">
          {{ kpi.reworkDiff > 0.05 ? '↑' : kpi.reworkDiff < -0.05 ? '↓' : '→' }}
          {{ Math.abs(kpi.reworkDiff).toFixed(1) }}pt 前週比
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">NG率</div>
        <div class="kpi-value">{{ kpi.ngRate.toFixed(1) }}%</div>
        <div :class="['kpi-trend', kpi.ngDiff > 0.05 ? 'worse' : kpi.ngDiff < -0.05 ? 'better' : 'flat']">
          {{ kpi.ngDiff > 0.05 ? '↑' : kpi.ngDiff < -0.05 ? '↓' : '→' }}
          {{ Math.abs(kpi.ngDiff).toFixed(1) }}pt 前週比
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">修正流動件数</div>
        <div class="kpi-value">{{ kpi.reworkCount.toLocaleString() }}</div>
        <div class="kpi-sub">NG件数: {{ kpi.ngCount.toLocaleString() }}</div>
      </div>
    </div>

    <!-- ===== 日次推移（メイントレンド） ===== -->
    <h3 class="section-title">日次推移（メイントレンド）</h3>
    <div class="chart-wrap">
      <div class="chart-header">
        <div class="chart-title">日次推移 — 修正流動件数 / NG件数</div>
        <div class="chart-subtitle">対象: {{ selectedFilterSummary }}</div>
      </div>
      <svg class="trend-svg" viewBox="0 0 920 290">
        <line v-for="t in dailyScale.ticks" :key="'dg-'+t" :x1="PL" :y1="yC(t, dailyScale.max)" :x2="PR" :y2="yC(t, dailyScale.max)" class="grid-line" />
        <line :x1="PL" :y1="PT" :x2="PL" :y2="PB" class="axis-line" />
        <line :x1="PL" :y1="PB" :x2="PR" :y2="PB" class="axis-line" />
        <text v-for="t in dailyScale.ticks" :key="'dyl-'+t" :x="PL - 6" :y="yC(t, dailyScale.max) + 4" text-anchor="end" class="axis-label">{{ t }}</text>
        <text v-for="lbl in dailyXLabels" :key="'dxl-'+lbl.idx" :x="dxC(lbl.idx)" :y="PB + 16" text-anchor="middle" class="axis-label">{{ lbl.label }}</text>
        <!-- 平均線 -->
        <line v-if="dailyAvgRework > 0" :x1="PL" :y1="yC(dailyAvgRework, dailyScale.max)" :x2="PR" :y2="yC(dailyAvgRework, dailyScale.max)" class="avg-line" />
        <text v-if="dailyAvgRework > 0" :x="PR + 4" :y="yC(dailyAvgRework, dailyScale.max) + 3" class="avg-label">平均 {{ dailyAvgRework.toFixed(1) }}</text>
        <!-- MA線 -->
        <polyline v-if="dailyReworkMaStr" :points="dailyReworkMaStr" class="trend-line rework-ma" />
        <polyline v-if="dailyNgMaStr" :points="dailyNgMaStr" class="trend-line ng-ma" />
        <!-- 実線 -->
        <polyline :points="dailyReworkStr" class="trend-line rework" />
        <polyline :points="dailyNgStr" class="trend-line ng" />
        <!-- マーカー -->
        <template v-for="(pt, idx) in dailyReworkPts" :key="'drm-'+idx">
          <circle v-if="idx % dailyMarkerInterval === 0 || idx === dailyReworkPts.length - 1" :cx="pt.x" :cy="pt.y" r="3" class="data-point rework-dot"><title>{{ pt.tip }}</title></circle>
        </template>
        <template v-for="(pt, idx) in dailyNgPts" :key="'dnm-'+idx">
          <circle v-if="idx % dailyMarkerInterval === 0 || idx === dailyNgPts.length - 1" :cx="pt.x" :cy="pt.y" r="3" class="data-point ng-dot"><title>{{ pt.tip }}</title></circle>
        </template>
        <text :x="PL - 8" :y="(PT + PB) / 2" text-anchor="middle" class="axis-title" :transform="`rotate(-90,${PL - 8},${(PT + PB) / 2})`">件数</text>
      </svg>
      <div class="trend-legend">
        <span class="legend-item"><span class="legend-swatch rework-bg"></span>修正流動件数</span>
        <span class="legend-item"><span class="legend-swatch ng-bg"></span>NG件数</span>
        <span class="legend-item"><span class="legend-line-dash rework-bg"></span>7日移動平均</span>
        <span class="legend-item"><span class="legend-line-dash avg-bg"></span>平均</span>
      </div>
    </div>
    <div class="table-wrap">
      <div class="table-title">日次推移表（{{ selectedFilterSummary }}）</div>
      <table class="data-table compact">
        <thead><tr><th>日付</th><th>判定総数</th><th>修正流動件数</th><th>修正流動率</th><th>NG件数</th><th>NG率</th></tr></thead>
        <tbody>
          <tr v-for="row in dailyRows" :key="`d-row-${row.date}`">
            <td>{{ row.date }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.reworkCount }}</td>
            <td :class="rateClass(row.reworkRate)">{{ row.reworkRate.toFixed(1) }}%</td>
            <td>{{ row.ngCount }}</td>
            <td :class="rateClass(row.ngRate)">{{ row.ngRate.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ===== 工程別 週次推移 ===== -->
    <h3 class="section-title">工程別 週次推移（修正流動率）</h3>
    <div class="chart-wrap">
      <div class="chart-header">
        <div class="chart-title">工程別 修正流動率 週次推移</div>
        <div class="chart-subtitle">直近{{ procWeeks.length }}週</div>
      </div>
      <svg v-if="procWeeks.length > 0" class="trend-svg" viewBox="0 0 920 290">
        <line v-for="t in weeklyRateScale.ticks" :key="'wg-'+t" :x1="PL" :y1="yC(t, weeklyRateScale.max)" :x2="PR" :y2="yC(t, weeklyRateScale.max)" class="grid-line" />
        <line :x1="PL" :y1="PT" :x2="PL" :y2="PB" class="axis-line" />
        <line :x1="PL" :y1="PB" :x2="PR" :y2="PB" class="axis-line" />
        <text v-for="t in weeklyRateScale.ticks" :key="'wyl-'+t" :x="PL - 6" :y="yC(t, weeklyRateScale.max) + 4" text-anchor="end" class="axis-label">{{ t }}%</text>
        <text v-for="(w, i) in procWeeks" :key="'wxl-'+i" :x="wxC(i)" :y="PB + 16" text-anchor="middle" class="axis-label">{{ shortDate(w) }}</text>
        <g v-for="(entry, eIdx) in procWeeklyEntries" :key="'pwl-'+eIdx">
          <polyline :points="weeklyLine(entry[1])" fill="none" :stroke="PALETTE[eIdx % PALETTE.length]" stroke-width="2" />
          <circle v-for="(w, wi) in procWeeks" :key="'pwp-'+eIdx+'-'+wi" :cx="wxC(wi)" :cy="yC(entry[1].get(w) || 0, weeklyRateScale.max)" r="3.5" :fill="PALETTE[eIdx % PALETTE.length]" class="data-point">
            <title>{{ entry[0] }} {{ shortDate(w) }}: {{ (entry[1].get(w) || 0).toFixed(1) }}%</title>
          </circle>
        </g>
        <text :x="PL - 8" :y="(PT + PB) / 2" text-anchor="middle" class="axis-title" :transform="`rotate(-90,${PL - 8},${(PT + PB) / 2})`">修正流動率 %</text>
      </svg>
      <div v-if="procWeeklyEntries.length" class="trend-legend proc-legend">
        <span v-for="(entry, eIdx) in procWeeklyEntries" :key="'pwleg-'+eIdx" class="legend-item">
          <span class="legend-swatch" :style="{ background: PALETTE[eIdx % PALETTE.length] }"></span>{{ entry[0] }}
        </span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>工程</th><th>推移</th><th>今週</th><th>先週</th><th>前週比</th><th>3か月平均</th></tr></thead>
        <tbody>
          <tr v-for="(row, rIdx) in processRows" :key="row.process">
            <td>{{ row.process }}</td>
            <td class="sparkline-cell">
              <svg width="80" height="22" viewBox="0 0 80 22">
                <polyline :points="sparkLine(procWeeklyRates.get(row.process))" fill="none" :stroke="PALETTE[rIdx % PALETTE.length]" stroke-width="1.5" />
              </svg>
            </td>
            <td>{{ row.thisWeek }}%</td>
            <td>{{ row.lastWeek }}%</td>
            <td :class="trendClass(row.diff)">{{ trendArrow(row.diff) }} {{ row.diff }}pt</td>
            <td>{{ row.ma3m }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ===== 集計結果 ===== -->
    <h3 class="section-title">集計結果（{{ summaryAxisLabel }}別）</h3>
    <div class="chart-wrap">
      <div class="chart-header">
        <div class="chart-title">{{ summaryAxisLabel }}別 修正流動件数・修正流動率</div>
        <div class="chart-subtitle">対象: {{ selectedFilterSummary }}</div>
      </div>
      <svg class="trend-svg" viewBox="0 0 920 320">
        <line v-for="t in sumCountScale.ticks" :key="'sg-'+t" :x1="PL" :y1="yC(t, sumCountScale.max)" :x2="PRD" :y2="yC(t, sumCountScale.max)" class="grid-line" />
        <line :x1="PL" :y1="PT" :x2="PL" :y2="PB" class="axis-line" />
        <line :x1="PL" :y1="PB" :x2="PRD" :y2="PB" class="axis-line" />
        <line :x1="PRD" :y1="PT" :x2="PRD" :y2="PB" class="axis-line-r" />
        <!-- 左Y軸ラベル（件数） -->
        <text v-for="t in sumCountScale.ticks" :key="'syl-'+t" :x="PL - 6" :y="yC(t, sumCountScale.max) + 4" text-anchor="end" class="axis-label">{{ t }}</text>
        <!-- 右Y軸ラベル（率%） -->
        <text v-for="t in sumRateScale.ticks" :key="'syr-'+t" :x="PRD + 6" :y="yC(t, sumRateScale.max) + 4" text-anchor="start" class="axis-label">{{ t }}%</text>
        <!-- 棒グラフ -->
        <g v-for="(row, idx) in summaryRows.slice(0, 12)" :key="'sbar-'+idx">
          <rect :x="sumBarX(idx)" :y="yC(row.reworkCount, sumCountScale.max)" :width="sumBarW" :height="Math.max(PB - yC(row.reworkCount, sumCountScale.max), 1)" class="summary-bar">
            <title>{{ row.key }}: {{ row.reworkCount }}件 ({{ row.reworkRate.toFixed(1) }}%)</title>
          </rect>
          <text :x="sumBarX(idx) + sumBarW / 2" :y="PB + 14" text-anchor="end" class="axis-label x-rotated" :transform="`rotate(-40,${sumBarX(idx) + sumBarW / 2},${PB + 14})`">{{ row.key.length > 10 ? row.key.slice(0, 10) + '…' : row.key }}</text>
        </g>
        <!-- 率折れ線 + マーカー -->
        <polyline :points="sumRateStr" class="trend-line rework-rate" />
        <circle v-for="(pt, idx) in sumRatePts" :key="'src-'+idx" :cx="pt.x" :cy="pt.y" r="4" class="data-point rate-dot">
          <title>{{ pt.tip }}</title>
        </circle>
        <!-- 平均修正流動率 -->
        <line v-if="sumAvgRate > 0" :x1="PL" :y1="yC(sumAvgRate, sumRateScale.max)" :x2="PRD" :y2="yC(sumAvgRate, sumRateScale.max)" class="avg-line" />
        <text v-if="sumAvgRate > 0" :x="PRD + 6" :y="yC(sumAvgRate, sumRateScale.max) - 4" class="avg-label">平均 {{ sumAvgRate.toFixed(1) }}%</text>
        <text :x="PL - 8" :y="(PT + PB) / 2" text-anchor="middle" class="axis-title" :transform="`rotate(-90,${PL - 8},${(PT + PB) / 2})`">件数</text>
        <text :x="PRD + 8" :y="(PT + PB) / 2" text-anchor="middle" class="axis-title" :transform="`rotate(90,${PRD + 8},${(PT + PB) / 2})`">率 %</text>
      </svg>
      <div class="trend-legend">
        <span class="legend-item"><span class="legend-swatch count-bg"></span>修正流動件数（棒）</span>
        <span class="legend-item"><span class="legend-swatch rate-bg"></span>修正流動率（折れ線）</span>
        <span class="legend-item"><span class="legend-line-dash avg-bg"></span>平均修正流動率</span>
      </div>
    </div>
    <div class="table-wrap">
      <div class="table-title">集計表（{{ selectedFilterSummary }}）</div>
      <table class="data-table compact">
        <thead><tr><th>{{ summaryAxisLabel }}</th><th>判定総数</th><th>修正流動件数</th><th>修正流動率</th><th>NG件数</th><th>NG率</th></tr></thead>
        <tbody>
          <tr v-for="row in summaryRows" :key="`s-row-${row.key}`">
            <td>{{ row.key }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.reworkCount }}</td>
            <td :class="rateClass(row.reworkRate)">{{ row.reworkRate.toFixed(1) }}%</td>
            <td>{{ row.ngCount }}</td>
            <td :class="rateClass(row.ngRate)">{{ row.ngRate.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ===== 上位不良要因（パレート分析） ===== -->
    <h3 class="section-title">上位修正流動要因（パレート分析）</h3>
    <div class="chart-wrap">
      <div class="chart-header">
        <div class="chart-title">修正流動要因パレート図</div>
        <div class="chart-subtitle">修正流動件数上位（累積構成比）</div>
      </div>
      <svg v-if="paretoData.length" class="trend-svg" viewBox="0 0 920 320">
        <line v-for="t in paretoCountScale.ticks" :key="'pg-'+t" :x1="PL" :y1="yC(t, paretoCountScale.max)" :x2="PRD" :y2="yC(t, paretoCountScale.max)" class="grid-line" />
        <line :x1="PL" :y1="PT" :x2="PL" :y2="PB" class="axis-line" />
        <line :x1="PL" :y1="PB" :x2="PRD" :y2="PB" class="axis-line" />
        <line :x1="PRD" :y1="PT" :x2="PRD" :y2="PB" class="axis-line-r" />
        <text v-for="t in paretoCountScale.ticks" :key="'pyl-'+t" :x="PL - 6" :y="yC(t, paretoCountScale.max) + 4" text-anchor="end" class="axis-label">{{ t }}</text>
        <text v-for="p in [0, 20, 40, 60, 80, 100]" :key="'pyr-'+p" :x="PRD + 6" :y="yC(p, 100) + 4" text-anchor="start" class="axis-label">{{ p }}%</text>
        <!-- 80%閾値 -->
        <line :x1="PL" :y1="yC(80, 100)" :x2="PRD" :y2="yC(80, 100)" class="threshold-line" />
        <text :x="PRD + 6" :y="yC(80, 100) - 3" class="threshold-label">80%</text>
        <!-- 棒 -->
        <g v-for="(f, idx) in paretoData" :key="'pb-'+idx">
          <rect :x="paretoBarX(idx)" :y="yC(f.count, paretoCountScale.max)" :width="paretoBarW" :height="Math.max(PB - yC(f.count, paretoCountScale.max), 1)" class="pareto-bar">
            <title>{{ f.itemName }}: {{ f.count }}件 (累計 {{ f.cumPct.toFixed(1) }}%)</title>
          </rect>
          <text :x="paretoBarX(idx) + paretoBarW / 2" :y="PB + 14" text-anchor="end" class="axis-label x-rotated" :transform="`rotate(-40,${paretoBarX(idx) + paretoBarW / 2},${PB + 14})`">{{ f.itemName.length > 12 ? f.itemName.slice(0, 12) + '…' : f.itemName }}</text>
        </g>
        <!-- 累積線 + マーカー -->
        <polyline :points="paretoCumStr" class="trend-line cumulative" />
        <circle v-for="(pt, idx) in paretoCumPts" :key="'pcm-'+idx" :cx="pt.x" :cy="pt.y" r="3.5" class="data-point cum-dot">
          <title>累計 {{ pt.pct }}%</title>
        </circle>
        <text :x="PL - 8" :y="(PT + PB) / 2" text-anchor="middle" class="axis-title" :transform="`rotate(-90,${PL - 8},${(PT + PB) / 2})`">件数</text>
        <text :x="PRD + 8" :y="(PT + PB) / 2" text-anchor="middle" class="axis-title" :transform="`rotate(90,${PRD + 8},${(PT + PB) / 2})`">累積 %</text>
      </svg>
      <div class="trend-legend">
        <span class="legend-item"><span class="legend-swatch pareto-bg"></span>修正流動件数（棒）</span>
        <span class="legend-item"><span class="legend-swatch cum-bg"></span>累積構成比（折れ線）</span>
        <span class="legend-item"><span class="legend-line-dash threshold-bg"></span>80%ライン</span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>順位</th><th>項目</th><th>件数</th><th>構成比</th><th>累積構成比</th></tr></thead>
        <tbody>
          <tr v-for="(f, idx) in paretoData" :key="f.itemName">
            <td>{{ idx + 1 }}</td>
            <td>{{ f.itemName }}</td>
            <td>{{ f.count }}</td>
            <td>{{ f.pct.toFixed(1) }}%</td>
            <td>{{ f.cumPct.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ===== ライン比較 ===== -->
    <h3 class="section-title">ライン比較（修正流動率）</h3>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>ライン</th><th>判定総数</th><th>修正流動件数</th><th>修正流動率</th><th></th></tr></thead>
        <tbody>
          <tr v-for="row in lineRows" :key="row.line">
            <td>{{ row.line }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.rework }}</td>
            <td :class="rateClass(Number(row.rate))">{{ row.rate }}%</td>
            <td class="inline-bar-cell"><div class="inline-bar-track"><div class="inline-bar-fill" :style="{ width: `${Math.min(Number(row.rate) / Math.max(lineMaxRate, 0.1) * 100, 100)}%` }"></div></div></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ===== 日別工程別 ===== -->
    <h3 class="section-title">日別工程別 修正流動率</h3>
    <div class="table-wrap">
      <div class="table-title">ライン / 工程 / 製品 / 日付 別一覧</div>
      <table class="data-table compact">
        <thead><tr><th>日付</th><th>ライン</th><th>工程</th><th>製品</th><th>判定総数</th><th>修正流動件数</th><th>修正流動率</th><th>NG件数</th><th>NG率</th></tr></thead>
        <tbody>
          <tr v-for="row in lineProcessDailyRows" :key="`lpd-${row.date}-${row.line}-${row.process}-${row.product}`">
            <td>{{ row.date }}</td>
            <td>{{ row.line }}</td>
            <td>{{ row.process }}</td>
            <td>{{ row.product }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.reworkCount }}</td>
            <td :class="rateClass(row.reworkRate)">{{ row.reworkRate.toFixed(1) }}%</td>
            <td>{{ row.ngCount }}</td>
            <td :class="rateClass(row.ngRate)">{{ row.ngRate.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import api from "@/api/client"
import { useIntegratedChecksheetFilters } from "@/composables/useIntegratedChecksheetFilters"

// ── 定数 ──
const PL = 65, PR = 855, PRD = 825, PT = 25, PB = 220
const PW = PR - PL, PWD = PRD - PL, PH = PB - PT
const BUSINESS_DAY_START_HOUR = 8
const MA_WINDOW = 7
const PALETTE = ["#2563eb", "#dc2626", "#16a34a", "#ea580c", "#8b5cf6", "#0891b2", "#ca8a04", "#be185d", "#4f46e5", "#059669"]

// ── State ──
const loading = ref(false)
const error = ref("")
const allRows = ref([])
const processRows = ref([])
const topFactors = ref([])
const lineRows = ref([])
const procWeeklyRates = ref(new Map())
const procWeeks = ref([])
const showOnlyReworkRows = ref(false)
const FAVORITE_SCREEN_KEY = "quality.product_checksheet_integrated_trend_analysis"
const {
  templateDefinitions,
  selectedLine,
  selectedProcess,
  selectedProduct,
  selectedItem,
  selectedPerson,
  selectedUnit,
  startDate,
  endDate,
  favorites,
  selectedFavoriteId,
  favoriteName,
  lineOptions,
  processOptions,
  productOptions,
  isItemSelectable,
  itemOptions,
  personOptions,
  unitOptions,
  buildMonthStartText,
  loadTemplateDefinitions,
  loadFavorites,
  applyFavorite,
  saveFavorite,
} = useIntegratedChecksheetFilters({
  sourceRows: allRows,
  favoriteScreenKey: FAVORITE_SCREEN_KEY,
  enableFavorites: true,
})

// ── ヘルパー ──
const toArray = (data) => data?.results || data || []
const toDate = (v) => new Date(v || "")
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
const rate = (ng, total) => total ? ((ng / total) * 100).toFixed(1) : "0.0"
const ngRateFromRows = (rows) => {
  const base = rows.filter((r) => !r.isRework)
  return rate(base.filter((r) => r.isNg).length, base.length)
}
const reworkRateFromRows = (rows) => rate(rows.filter((r) => r.isRework).length, rows.length)

const niceScale = (rawMax, steps = 4) => {
  if (rawMax <= 0) return { max: steps, step: 1, ticks: Array.from({ length: steps + 1 }, (_, i) => i) }
  const rough = rawMax / steps
  const mag = Math.pow(10, Math.floor(Math.log10(rough)))
  const norm = rough / mag
  let step
  if (norm <= 1.5) step = mag
  else if (norm <= 3) step = 2 * mag
  else if (norm <= 7) step = 5 * mag
  else step = 10 * mag
  const max = Math.ceil(rawMax / step) * step
  const ticks = []
  for (let v = 0; v <= max + step * 0.01; v += step) ticks.push(Math.round(v * 1000) / 1000)
  return { max, step, ticks }
}

const calcMA = (values, win) => values.map((_, i) => {
  const s = Math.max(0, i - win + 1)
  const slice = values.slice(s, i + 1)
  return slice.reduce((a, b) => a + b, 0) / slice.length
})

const yC = (val, scaleMax) => PB - (val / Math.max(scaleMax, 0.001)) * PH
const shortDate = (d) => { const p = d.split("-"); return `${parseInt(p[1])}/${parseInt(p[2])}` }

const trendArrow = (diff) => { const n = Number(diff); return n > 0.05 ? "↑" : n < -0.05 ? "↓" : "→" }
const trendClass = (diff) => { const n = Number(diff); return n > 0.05 ? "trend-worse" : n < -0.05 ? "trend-better" : "trend-flat" }
const rateClass = (r) => r >= 10 ? "rate-high" : r >= 5 ? "rate-mid" : ""

const filteredRows = computed(() => allRows.value.filter((r) => {
  if (startDate.value && r.dateText < startDate.value) return false
  if (endDate.value && r.dateText > endDate.value) return false
  if (selectedLine.value && r.line !== selectedLine.value) return false
  if (selectedProcess.value && r.process !== selectedProcess.value) return false
  if (selectedProduct.value && r.product !== selectedProduct.value) return false
  if (selectedItem.value && r.itemName !== selectedItem.value) return false
  if (selectedPerson.value && r.person !== selectedPerson.value) return false
  if (selectedUnit.value && r.unit !== selectedUnit.value) return false
  if (showOnlyReworkRows.value && !r.isRework) return false
  return true
}))

const summaryAxisKey = computed(() => {
  if (selectedItem.value) return "itemName"
  if (selectedPerson.value) return "person"
  if (selectedProduct.value) return "product"
  if (selectedProcess.value) return "process"
  return "line"
})
const summaryAxisLabel = computed(() => ({ itemName: "項目", person: "作業者", product: "製品", process: "工程", line: "ライン" })[summaryAxisKey.value] || "ライン")

const selectedFilterSummary = computed(() => {
  const parts = []
  if (selectedLine.value) parts.push(selectedLine.value)
  if (selectedProcess.value) parts.push(selectedProcess.value)
  if (selectedProduct.value) parts.push(selectedProduct.value)
  if (selectedItem.value) parts.push(selectedItem.value)
  if (selectedPerson.value) parts.push(selectedPerson.value)
  if (selectedUnit.value) parts.push(`台目:${selectedUnit.value}`)
  return parts.length ? parts.join(" + ") : "全体"
})

// ── Computed: 集計データ ──
const summaryRows = computed(() => {
  const map = new Map()
  filteredRows.value.forEach((r) => {
    const key = String(r[summaryAxisKey.value] || "未設定")
    if (!map.has(key)) map.set(key, { key, total: 0, ngCount: 0, reworkCount: 0 })
    const obj = map.get(key)
    obj.total += 1
    if (r.isNg) obj.ngCount += 1
    if (r.isRework) obj.reworkCount += 1
  })
  return [...map.values()]
    .map((r) => ({
      ...r,
      ngRate: r.total ? (r.ngCount / r.total) * 100 : 0,
      reworkRate: r.total ? (r.reworkCount / r.total) * 100 : 0,
    }))
    .sort((a, b) => b.reworkCount - a.reworkCount)
})

const dailyRows = computed(() => {
  const map = new Map()
  filteredRows.value.forEach((r) => {
    const key = r.dateText
    if (!map.has(key)) map.set(key, { date: key, total: 0, ngCount: 0, reworkCount: 0 })
    const obj = map.get(key)
    obj.total += 1
    if (r.isNg) obj.ngCount += 1
    if (r.isRework) obj.reworkCount += 1
  })
  return [...map.values()]
    .map((r) => {
      const ngBase = r.total - r.reworkCount
      return { ...r, ngRate: ngBase > 0 ? (r.ngCount / ngBase) * 100 : 0, reworkRate: r.total > 0 ? (r.reworkCount / r.total) * 100 : 0 }
    })
    .sort((a, b) => String(a.date).localeCompare(String(b.date), "ja"))
})

const lineProcessDailyRows = computed(() => {
  const map = new Map()
  filteredRows.value.forEach((r) => {
    const key = `${r.dateText}__${r.line}__${r.process}__${r.product}`
    if (!map.has(key)) map.set(key, { date: r.dateText, line: r.line, process: r.process, product: r.product, total: 0, ngCount: 0, reworkCount: 0 })
    const obj = map.get(key)
    obj.total += 1
    if (r.isNg) obj.ngCount += 1
    if (r.isRework) obj.reworkCount += 1
  })
  return [...map.values()]
    .map((r) => {
      const ngBase = r.total - r.reworkCount
      return { ...r, ngRate: ngBase > 0 ? (r.ngCount / ngBase) * 100 : 0, reworkRate: r.total > 0 ? (r.reworkCount / r.total) * 100 : 0 }
    })
    .sort((a, b) => {
      if (a.date !== b.date) return String(b.date).localeCompare(String(a.date), "ja")
      if (a.line !== b.line) return String(a.line).localeCompare(String(b.line), "ja")
      if (a.process !== b.process) return String(a.process).localeCompare(String(b.process), "ja")
      return String(a.product).localeCompare(String(b.product), "ja")
    })
})

// ── Computed: KPI ──
const kpi = computed(() => {
  const rows = filteredRows.value
  const total = rows.length
  const reworkCount = rows.filter((r) => r.isRework).length
  const ngCount = rows.filter((r) => r.isNg).length
  const reworkRate = total > 0 ? (reworkCount / total) * 100 : 0
  const nonRework = rows.filter((r) => !r.isRework)
  const ngRate = nonRework.length > 0 ? (ngCount / nonRework.length) * 100 : 0
  const now = new Date()
  const w1 = new Date(now); w1.setDate(now.getDate() - 7)
  const w2 = new Date(now); w2.setDate(now.getDate() - 14)
  const tw = rows.filter((r) => r.date >= w1)
  const lw = rows.filter((r) => r.date >= w2 && r.date < w1)
  const twRR = tw.length > 0 ? (tw.filter((r) => r.isRework).length / tw.length) * 100 : 0
  const lwRR = lw.length > 0 ? (lw.filter((r) => r.isRework).length / lw.length) * 100 : 0
  const twNR = tw.filter((r) => !r.isRework)
  const lwNR = lw.filter((r) => !r.isRework)
  const twNG = twNR.length > 0 ? (tw.filter((r) => r.isNg).length / twNR.length) * 100 : 0
  const lwNG = lwNR.length > 0 ? (lw.filter((r) => r.isNg).length / lwNR.length) * 100 : 0
  return { total, reworkCount, ngCount, reworkRate, ngRate, reworkDiff: twRR - lwRR, ngDiff: twNG - lwNG }
})

// ── Computed: 日次チャート座標 ──
const dailyMax = computed(() => Math.max(...dailyRows.value.map((r) => Math.max(r.reworkCount, r.ngCount)), 1))
const dailyScale = computed(() => niceScale(dailyMax.value, 4))
const dailyMarkerInterval = computed(() => Math.max(1, Math.ceil(dailyRows.value.length / 15)))
const dailyXLabels = computed(() => {
  const rows = dailyRows.value
  const interval = Math.max(1, Math.ceil(rows.length / 14))
  return rows.filter((_, i) => i % interval === 0 || i === rows.length - 1).map((r) => ({ idx: rows.indexOf(r), label: shortDate(r.date) }))
})
const dxC = (idx) => {
  const n = dailyRows.value.length
  return PL + (n > 1 ? (idx / (n - 1)) * PW : PW / 2)
}
const dailyPts = (key) => {
  const rows = dailyRows.value
  const max = dailyScale.value.max
  return rows.map((r, i) => ({ x: dxC(i), y: yC(r[key], max), tip: `${r.date}: ${r[key]}件` }))
}
const dailyReworkPts = computed(() => dailyPts("reworkCount"))
const dailyNgPts = computed(() => dailyPts("ngCount"))
const ptsToStr = (pts) => pts.map((p) => `${p.x},${p.y}`).join(" ")
const dailyReworkStr = computed(() => ptsToStr(dailyReworkPts.value))
const dailyNgStr = computed(() => ptsToStr(dailyNgPts.value))
const dailyAvgRework = computed(() => {
  const rows = dailyRows.value
  return rows.length ? rows.reduce((s, r) => s + r.reworkCount, 0) / rows.length : 0
})
const dailyReworkMaStr = computed(() => {
  const rows = dailyRows.value
  if (rows.length < 3) return ""
  const ma = calcMA(rows.map((r) => r.reworkCount), MA_WINDOW)
  const max = dailyScale.value.max
  return ma.map((v, i) => `${dxC(i)},${yC(v, max)}`).join(" ")
})
const dailyNgMaStr = computed(() => {
  const rows = dailyRows.value
  if (rows.length < 3) return ""
  const ma = calcMA(rows.map((r) => r.ngCount), MA_WINDOW)
  const max = dailyScale.value.max
  return ma.map((v, i) => `${dxC(i)},${yC(v, max)}`).join(" ")
})

// ── Computed: 集計チャート座標 ──
const sumSlice = computed(() => summaryRows.value.slice(0, 12))
const sumCountMax = computed(() => Math.max(...sumSlice.value.map((r) => r.reworkCount), 1))
const sumCountScale = computed(() => niceScale(sumCountMax.value, 4))
const sumRateMax = computed(() => Math.max(...sumSlice.value.map((r) => r.reworkRate), 1))
const sumRateScale = computed(() => niceScale(sumRateMax.value, 4))
const sumBandW = computed(() => PWD / Math.max(sumSlice.value.length, 1))
const sumBarW = computed(() => sumBandW.value * 0.55)
const sumBarX = (idx) => PL + idx * sumBandW.value + (sumBandW.value - sumBarW.value) / 2
const sumRatePts = computed(() => sumSlice.value.map((r, i) => ({
  x: PL + i * sumBandW.value + sumBandW.value / 2,
  y: yC(r.reworkRate, sumRateScale.value.max),
  tip: `${r.key}: ${r.reworkRate.toFixed(1)}%`,
})))
const sumRateStr = computed(() => ptsToStr(sumRatePts.value))
const sumAvgRate = computed(() => {
  const rows = summaryRows.value
  if (!rows.length) return 0
  const tRework = rows.reduce((s, r) => s + r.reworkCount, 0)
  const tAll = rows.reduce((s, r) => s + r.total, 0)
  return tAll > 0 ? (tRework / tAll) * 100 : 0
})

// ── Computed: パレート ──
const paretoData = computed(() => {
  if (!topFactors.value.length) return []
  const total = topFactors.value.reduce((s, f) => s + f.count, 0)
  let cum = 0
  return topFactors.value.slice(0, 8).map((f) => {
    const pct = total > 0 ? (f.count / total) * 100 : 0
    cum += f.count
    return { ...f, pct, cumPct: total > 0 ? (cum / total) * 100 : 0 }
  })
})
const paretoCountMax = computed(() => Math.max(...paretoData.value.map((f) => f.count), 1))
const paretoCountScale = computed(() => niceScale(paretoCountMax.value, 4))
const paretoBandW = computed(() => PWD / Math.max(paretoData.value.length, 1))
const paretoBarW = computed(() => paretoBandW.value * 0.55)
const paretoBarX = (idx) => PL + idx * paretoBandW.value + (paretoBandW.value - paretoBarW.value) / 2
const paretoCumPts = computed(() => paretoData.value.map((f, i) => ({
  x: PL + i * paretoBandW.value + paretoBandW.value / 2,
  y: yC(f.cumPct, 100),
  pct: f.cumPct.toFixed(1),
})))
const paretoCumStr = computed(() => ptsToStr(paretoCumPts.value))

// ── Computed: 工程別週次 ──
const procWeeklyEntries = computed(() => [...procWeeklyRates.value.entries()])
const procWeeklyMaxRate = computed(() => {
  let max = 0
  for (const [, wm] of procWeeklyRates.value) for (const [, r] of wm) if (r > max) max = r
  return max || 1
})
const weeklyRateScale = computed(() => niceScale(procWeeklyMaxRate.value, 4))
const wxC = (i) => PL + (procWeeks.value.length > 1 ? (i / (procWeeks.value.length - 1)) * PW : PW / 2)
const weeklyLine = (weekRateMap) => {
  const weeks = procWeeks.value
  if (!weeks.length) return ""
  return weeks.map((w, i) => `${wxC(i)},${yC(weekRateMap.get(w) || 0, weeklyRateScale.value.max)}`).join(" ")
}
const sparkLine = (weekRateMap) => {
  if (!weekRateMap || !procWeeks.value.length) return "0,11 80,11"
  const max = procWeeklyMaxRate.value
  const weeks = procWeeks.value
  return weeks.map((w, i) => {
    const r = weekRateMap.get(w) || 0
    const x = 2 + (weeks.length > 1 ? (i / (weeks.length - 1)) * 76 : 38)
    const y = 20 - (r / Math.max(max, 0.01)) * 16
    return `${x},${y}`
  }).join(" ")
}

// ── Computed: ライン比較 ──
const lineMaxRate = computed(() => Math.max(...lineRows.value.map((r) => Number(r.rate)), 0.1))

const loadData = async () => {
  loading.value = true
  error.value = ""
  try {
    const matchedDefinitions = templateDefinitions.value.filter((row) => {
      if (selectedLine.value && row.line !== selectedLine.value) return false
      if (selectedProduct.value && row.product !== selectedProduct.value) return false
      if (selectedProcess.value && row.process !== selectedProcess.value) return false
      return true
    })
    if ((selectedLine.value || selectedProduct.value || selectedProcess.value) && !matchedDefinitions.length) {
      allRows.value = []
      rebuildRows()
      return
    }

    const params = { page_size: 200 }
    if (startDate.value) params.plan_date__gte = startDate.value
    if (endDate.value) params.plan_date__lte = endDate.value
    if (selectedLine.value) {
      const lineId = matchedDefinitions.find((row) => row.line === selectedLine.value)?.lineId
      if (lineId) params.line = lineId
    }
    if (selectedProduct.value) {
      const productId = matchedDefinitions.find((row) => row.product === selectedProduct.value)?.productId
      if (productId) params.product = productId
    }
    if (selectedProcess.value) params.process_name = selectedProcess.value
    if (selectedItem.value) params.item_name = selectedItem.value
    if (selectedPerson.value) params.checked_by_name = selectedPerson.value
    if (selectedUnit.value) params.unit_sequence_no = selectedUnit.value
    params.business_date__gte = startDate.value || ""
    params.business_date__lte = endDate.value || ""

    const res = await api.integratedChecksheets.getAnalyticsRecords(params)
    allRows.value = toArray(res.data).map((row) => {
      const dateText = row.date_text || ""
      const date = toDate(dateText)
      if (!Number.isNaN(date.getTime())) date.setHours(0, 0, 0, 0)
      return {
        dateText,
        product: row.product || "未設定",
        person: row.person || "未設定",
        unit: String(row.unit || "未設定"),
        date,
        line: row.line || "未設定",
        process: row.process || "未設定",
        itemName: row.item_name || "未設定項目",
        isNg: Boolean(row.is_ng),
        isRework: Boolean(row.is_rework),
      }
    }).filter((row) => row.dateText)
    rebuildRows()
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

const rebuildRows = () => {
  const rows = filteredRows.value
  const now = new Date()
  const thisWeekStart = new Date(now); thisWeekStart.setDate(now.getDate() - 6)
  const lastWeekStart = new Date(now); lastWeekStart.setDate(now.getDate() - 13)
  const lastWeekEnd = new Date(now); lastWeekEnd.setDate(now.getDate() - 7)
  const threeMonthStart = new Date(now); threeMonthStart.setMonth(now.getMonth() - 3)

  // 工程別
  const byProcess = new Map()
  rows.forEach((r) => {
    if (!byProcess.has(r.process)) byProcess.set(r.process, [])
    byProcess.get(r.process).push(r)
  })
  processRows.value = [...byProcess.entries()]
    .map(([process, list]) => {
      const thisWeek = list.filter((r) => r.date >= thisWeekStart && r.date <= now)
      const lastWeek = list.filter((r) => r.date >= lastWeekStart && r.date <= lastWeekEnd)
      const ma3m = list.filter((r) => r.date >= threeMonthStart && r.date <= now)
      const t = Number(reworkRateFromRows(thisWeek))
      const l = Number(reworkRateFromRows(lastWeek))
      return { process, thisWeek: t.toFixed(1), lastWeek: l.toFixed(1), diff: (t - l).toFixed(1), ma3m: reworkRateFromRows(ma3m) }
    })
    .sort((a, b) => Number(b.thisWeek) - Number(a.thisWeek))

  // 上位修正流動要因
  const factorMap = new Map()
  rows.filter((r) => r.isRework).forEach((r) => factorMap.set(r.itemName, (factorMap.get(r.itemName) || 0) + 1))
  topFactors.value = [...factorMap.entries()].map(([itemName, count]) => ({ itemName, count })).sort((a, b) => b.count - a.count).slice(0, 10)

  // ライン比較
  const lineMap = new Map()
  rows.forEach((r) => {
    if (!lineMap.has(r.line)) lineMap.set(r.line, { line: r.line, total: 0, rework: 0 })
    const obj = lineMap.get(r.line)
    obj.total += 1
    if (r.isRework) obj.rework += 1
  })
  lineRows.value = [...lineMap.values()].map((r) => ({ ...r, rate: rate(r.rework, r.total) })).sort((a, b) => Number(b.rate) - Number(a.rate))

  // 工程別 週次データ
  const wMap = new Map()
  rows.forEach((r) => {
    const d = new Date(r.date)
    const day = d.getDay()
    d.setDate(d.getDate() - day + (day === 0 ? -6 : 1))
    const ws = ymd(d)
    const key = `${r.process}||${ws}`
    if (!wMap.has(key)) wMap.set(key, { process: r.process, week: ws, total: 0, rework: 0 })
    const o = wMap.get(key)
    o.total += 1
    if (r.isRework) o.rework += 1
  })
  const weeks = [...new Set([...wMap.values()].map((v) => v.week))].sort()
  const recentWeeks = weeks.slice(-8)
  const pwMap = new Map()
  for (const [, v] of wMap) {
    if (!recentWeeks.includes(v.week)) continue
    if (!pwMap.has(v.process)) pwMap.set(v.process, new Map())
    pwMap.get(v.process).set(v.week, v.total > 0 ? (v.rework / v.total) * 100 : 0)
  }
  procWeeks.value = recentWeeks
  procWeeklyRates.value = pwMap
}

onMounted(async () => {
  startDate.value = buildMonthStartText()
  await Promise.all([loadFavorites(), loadTemplateDefinitions()])
})
watch([selectedProduct, selectedProcess], () => { if (!isItemSelectable.value) selectedItem.value = "" })
watch([selectedLine, selectedProcess, selectedProduct, selectedItem, selectedPerson, selectedUnit, startDate, endDate], rebuildRows)
</script>

<style scoped>
/* ── レイアウト ── */
.trend-page { display: flex; flex-direction: column; gap: 14px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.page-header .helper-text { margin: 0; }
.page-header .btn-secondary { border: 1px solid #2563eb; background: #2563eb; color: #fff; border-radius: 4px; padding: 6px 16px; font-weight: 700; cursor: pointer; }
.page-header .btn-secondary:hover:not(:disabled) { background: #1d4ed8; border-color: #1d4ed8; }
.page-header .btn-secondary:disabled { opacity: 0.7; cursor: default; }
.prepare-form { display: flex; flex-wrap: wrap; align-items: end; gap: 8px; margin: 8px 0 10px; }
.prepare-form label { display: inline-flex; align-items: center; gap: 6px; margin: 0; width: auto; flex: 0 0 auto; }
.field-label { white-space: nowrap; min-width: 56px; }
.prepare-form select, .prepare-form input { padding: 5px 7px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
.filter-form .field-worker select { width: 140px; }
.filter-form .field-unit select { width: 110px; }
.check-label { padding: 4px 8px; border: 1px solid #dbe3ea; border-radius: 6px; background: #fff; }

/* ── KPI カード ── */
.kpi-cards { display: flex; gap: 10px; margin: 12px 0 6px; flex-wrap: wrap; }
.kpi-card { flex: 1; min-width: 150px; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kpi-label { font-size: 11px; color: #64748b; font-weight: 500; }
.kpi-value { font-size: 22px; font-weight: 700; color: #1e293b; line-height: 1.3; }
.kpi-sub { font-size: 11px; color: #94a3b8; }
.kpi-trend { font-size: 12px; font-weight: 600; margin-top: 1px; }
.kpi-trend.worse { color: #dc2626; }
.kpi-trend.better { color: #16a34a; }
.kpi-trend.flat { color: #94a3b8; }

/* ── チャートラップ ── */
.chart-wrap { margin: 6px 0 14px; padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.chart-header { margin-bottom: 8px; }
.chart-title { font-weight: 700; font-size: 13px; color: #1e293b; }
.chart-subtitle { font-size: 11px; color: #64748b; margin-top: 1px; }

/* ── SVG ── */
.trend-svg { width: 100%; display: block; }
.grid-line { stroke: #e5e7eb; stroke-width: 0.8; stroke-dasharray: 3,3; }
.axis-line { stroke: #9ca3af; stroke-width: 1; }
.axis-line-r { stroke: #d1d5db; stroke-width: 1; stroke-dasharray: 2,2; }
.axis-label { font-size: 10px; fill: #6b7280; font-family: system-ui, -apple-system, sans-serif; }
.axis-title { font-size: 10px; fill: #9ca3af; font-family: system-ui, -apple-system, sans-serif; }
.x-rotated { font-size: 10px; }
.avg-line { stroke: #9333ea; stroke-width: 1.5; stroke-dasharray: 5,4; }
.avg-label { font-size: 10px; fill: #9333ea; font-family: system-ui, -apple-system, sans-serif; }
.threshold-line { stroke: #dc2626; stroke-width: 1; stroke-dasharray: 6,3; opacity: 0.5; }
.threshold-label { font-size: 10px; fill: #dc2626; font-family: system-ui, -apple-system, sans-serif; opacity: 0.7; }

/* ── トレンドライン ── */
.trend-line { fill: none; stroke-width: 2; }
.trend-line.rework { stroke: #0ea5a4; }
.trend-line.ng { stroke: #ef4444; }
.trend-line.rework-ma { stroke: #0ea5a4; stroke-dasharray: 6,3; stroke-width: 1.5; opacity: 0.55; }
.trend-line.ng-ma { stroke: #ef4444; stroke-dasharray: 6,3; stroke-width: 1.5; opacity: 0.55; }
.trend-line.rework-rate { stroke: #2563eb; }
.trend-line.cumulative { stroke: #ef4444; stroke-width: 2; }

/* ── データポイント ── */
.data-point { stroke: #fff; stroke-width: 1.5; }
.rework-dot { fill: #0ea5a4; }
.ng-dot { fill: #ef4444; }
.rate-dot { fill: #2563eb; }
.cum-dot { fill: #ef4444; }

/* ── 棒グラフ ── */
.summary-bar { fill: #ea580c; opacity: 0.85; rx: 2; }
.pareto-bar { fill: #3b82f6; opacity: 0.85; rx: 2; }

/* ── 凡例 ── */
.trend-legend { display: flex; gap: 14px; margin-top: 8px; font-size: 11px; color: #475569; flex-wrap: wrap; }
.proc-legend { gap: 10px; }
.legend-item { display: inline-flex; align-items: center; gap: 5px; }
.legend-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; flex-shrink: 0; }
.legend-line-dash { width: 18px; height: 0; border-top: 2px dashed; display: inline-block; flex-shrink: 0; }
.rework-bg { background: #0ea5a4; }
.ng-bg { background: #ef4444; }
.count-bg { background: #ea580c; }
.rate-bg { background: #2563eb; }
.pareto-bg { background: #3b82f6; }
.cum-bg { background: #ef4444; }
.avg-bg { border-color: #9333ea; }
.threshold-bg { border-color: #dc2626; }

/* ── テーブル ── */
.table-title { font-weight: 700; margin-bottom: 6px; color: #1e293b; font-size: 13px; }
.table-wrap { margin-bottom: 14px; }
.sparkline-cell { padding: 2px 4px !important; }
.rate-high { color: #dc2626; font-weight: 600; }
.rate-mid { color: #ea580c; }
.trend-worse { color: #dc2626; font-weight: 600; }
.trend-better { color: #16a34a; font-weight: 600; }
.trend-flat { color: #94a3b8; }

/* ── インラインバー（ライン比較） ── */
.inline-bar-cell { width: 120px; padding: 4px !important; }
.inline-bar-track { height: 10px; background: #f1f5f9; border-radius: 999px; overflow: hidden; }
.inline-bar-fill { height: 100%; background: #3b82f6; border-radius: 999px; transition: width 0.3s; }

/* ── お気に入り ── */
.favorite-star-btn { border: 1px solid #eab308; background: #facc15; color: #78350f; min-width: 34px; height: 31px; border-radius: 4px; cursor: pointer; }
.favorite-star-btn:disabled { opacity: 0.6; cursor: default; }
</style>
