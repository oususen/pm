<template>
  <div class="plan-container">
    <div class="tab-bar">
      <button
        v-for="tab in planTabs"
        :key="tab.key"
        type="button"
        class="tab-item"
        :class="{ active: activePlanTab === tab.key }"
        @click="selectPlanTab(tab)"
      >
        {{ tab.label }}
      </button>
      <button v-if="authState.user?.is_superuser" class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button>
    </div>

    <div v-if="!activePlanTab" class="no-tab-placeholder">タブを選択してください</div>
    <template v-else-if="activePlanTab !== 'line-settings'">
    <div v-if="activePlanTab === 'laser'" class="laser-subtab-bar">
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeLaserTab === 'normal-plan' }"
        @click="activeLaserTab = 'normal-plan'"
      >
        通常計画
      </button>
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeLaserTab === 'pattern-editor' }"
        @click="activeLaserTab = 'pattern-editor'"
      >
        パターン編集
      </button>
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeLaserTab === 'tab3' }"
        @click="activeLaserTab = 'tab3'"
      >
        月所要材料集計
      </button>
    </div>
    <div v-else-if="activePlanTab === 'spot'" class="laser-subtab-bar">
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeSpotTab === 'normal-plan' }"
        @click="activeSpotTab = 'normal-plan'"
      >
        通常計画
      </button>
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeSpotTab === 'excel' }"
        @click="activeSpotTab = 'excel'"
      >
        excel
      </button>
    </div>
    <div v-else-if="activePlanTab === 'floor-shipping'" class="laser-subtab-bar">
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeFloorShippingTab === 'inventory' }"
        @click="activeFloorShippingTab = 'inventory'"
      >
        在庫基準
      </button>
      <button
        type="button"
        class="laser-subtab-item"
        :class="{ active: activeFloorShippingTab === 'progress' }"
        @click="activeFloorShippingTab = 'progress'"
      >
        進度基準
      </button>
      <button
        type="button"
        class="laser-subtab-item manual-btn"
        @click="openManual('生産/配送計画.md')"
      >
        マニュアル
      </button>
    </div>

    <template
      v-if="(activePlanTab !== 'laser' || activeLaserTab === 'normal-plan') && (activePlanTab !== 'spot' || activeSpotTab === 'normal-plan')"
    >
    <div class="toolbar" :class="{ collapsed: toolbarCollapsed }">
      <button
        type="button"
        class="toolbar-toggle"
        @click="toggleToolbar"
        :title="toolbarCollapsed ? 'フィルタを表示' : 'フィルタを隠す'"
      >{{ toolbarCollapsed ? '▼' : '▲' }}</button>
      <div v-if="toolbarCollapsed" class="toolbar-summary">
        <span class="summary-item">{{ selectedLineSummary }}</span>
        <span class="summary-sep">|</span>
        <span class="summary-item">{{ startDate }} 〜 {{ horizonDays }}日</span>
        <span v-if="keyword" class="summary-sep">|</span>
        <span v-if="keyword" class="summary-item">検索: {{ keyword }}</span>
      </div>
      <div v-show="!toolbarCollapsed" class="toolbar-left">
        <div class="field">
          <label>ライン</label>
          <select v-model="selectedLine" @change="loadData">
            <option v-for="line in availableLines" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>表示開始日</label>
          <input type="date" v-model="startDate" @change="refreshDates" class="input-narrow" />
        </div>
        <div class="field">
          <label>期間</label>
          <select v-model.number="horizonDays" @change="refreshDates" class="select-narrow">
            <option :value="7">7日</option>
            <option :value="14">14日</option>
            <option :value="30">30日</option>
            <option :value="60">60日</option>
            <option :value="90">90日</option>
          </select>
        </div>
        <div class="field">
          <label>検索</label>
          <input type="text" v-model="keyword" placeholder="品番/品名で絞り込み" />
        </div>
      </div>
      <div v-show="!toolbarCollapsed" class="toolbar-right">
        <div class="field checkbox-field">
          <label>
            <input type="checkbox" v-model="hideWeekends" @change="localStorage.setItem(HIDE_WEEKENDS_KEY, hideWeekends ? '1' : '0')" />
            土日非表示
          </label>
        </div>
        <div class="field checkbox-field">
          <label>
            <input type="checkbox" v-model="adjustToBreakEnd" />
            休憩明けに補正
          </label>
        </div>
        <div class="field checkbox-field">
          <label>
            <input type="checkbox" v-model="hideEmptyRows" @change="localStorage.setItem(HIDE_EMPTY_ROWS_KEY, hideEmptyRows ? '1' : '0')" />
            空行非表示
          </label>
        </div>
        <button class="btn" @click="bulkDeletePlans" :disabled="processing || !selectedLine">計画一括削除</button>
        <button
          v-if="activePlanTab === 'floor-shipping'"
          class="btn primary"
          @click="openBulkActualDialog"
          :disabled="processing || !selectedLine || !rows.length"
        >一括実績入力</button>
        <button class="btn" @click="openChangeReasonDialog" :disabled="processing">計画変更</button>
        <button
          v-if="activePlanTab === 'floor-shipping'"
          class="btn primary"
          @click="saveActuals"
          :disabled="processing || !rows.length || !selectedLine"
        >実績保存</button>
        <button
          v-if="activePlanTab === 'floor-shipping' && activeFloorShippingTab === 'progress'"
          class="btn primary"
          @click="showRecalcWarning = true"
          :disabled="processing || !rows.length || !selectedLine"
        >過去から再計算</button>
        <button class="btn" @click="savePlan" :disabled="processing || !rows.length || !selectedLine">保存</button>
        <button class="btn" @click="openProductOrderDialog" :disabled="processing || !selectedLine || !rows.length">表示順</button>
        <button
          v-if="canShowFloorSpotAutoPlanButton"
          class="btn"
          @click="doFloorSpotAutoPlan"
          :disabled="processing || !selectedLine"
        >自動計画</button>
        <button
          v-if="canShowFloorSpotAutoPlanButton"
          class="btn"
          @click="openAggregateSettingsDialog"
        >まとめ設定</button>
        <button class="btn accent" @click="toggleProcessGantt" :disabled="processing || !selectedLine">
          {{ showProcessGantt ? 'ガント閉じ' : 'ガント表示' }}
        </button>
        <button class="btn accent" @click="toggleProcessLoad" :disabled="processing || !selectedLine">
          {{ showProcessLoad ? '負荷閉' : '負荷表示' }}
        </button>
        <button
          v-if="canShowFloorDeliveryDetailPDFButton"
          class="btn"
          style="background: #70AD47; color: #fff;"
          @click="downloadFloorShippingPDF"
          :disabled="processing || !selectedLine"
        >配送明細</button>
        <button
          v-if="canShowFloorDeliveryDetailPDFButton"
          class="btn"
          style="background: #2E86C1; color: #fff;"
          @click="downloadFloorShippingNewPDF"
          :disabled="processing || !selectedLine"
        >新配送明細</button>
        <button
          v-if="canShowFloorDeliveryDetailPDFButton"
          class="btn"
          style="background: #C07000; color: #fff;"
          @click="downloadFloorShippingLapPDF"
          :disabled="processing || !selectedLine"
        >配送明細(ラップ)</button>
        <button
          v-if="canShowDeliveryDetailPDFButton"
          class="btn"
          style="background: #1f4e78; color: #fff;"
          @click="downloadHokushinDeliveryListPDF"
          :disabled="processing || !selectedLine"
        >北進納入リスト</button>
        <button
          v-if="canShowDeliveryDetailPDFButton"
          class="btn"
          style="background: #2E86C1; color: #fff;"
          @click="downloadHokushinDeliveryListNewPDF"
          :disabled="processing || !selectedLine"
        >新納入リスト</button>
        <button
          v-if="canShowDeliveryDetailPDFButton"
          class="btn"
          style="background: #C07000; color: #fff;"
          @click="downloadHokushinDeliveryListLapPDF"
          :disabled="processing || !selectedLine"
        >納入リスト(ラップ)</button>
        <button
          v-if="canShowDeliveryDetailPDFButton"
          class="btn"
          style="background: #C00000; color: #fff;"
          @click="downloadHokushinDeliveryPDF"
          :disabled="processing || !selectedLine"
        >納品書</button>
        <button
          v-if="canShowDeliveryDetailPDFButton"
          class="btn"
          style="background: #C00000; color: #fff;"
          @click="downloadHokushinDeliveryAllPDF"
          :disabled="processing || !selectedLine"
        >納品書２</button>
      </div>
    </div>

    <div v-if="shouldLimitToCoproductParentAndDriver" class="line-rule-notice">
      注意: このラインでは、連産品は「親品番 + 代表部番（is_coproduct_driver）」のみ表示します。
      連産品の非代表子は表示しません。非連産品は通常どおり表示します。
    </div>
    <div v-if="currentLineRoutingFilterMode === 'fallback'" class="line-rule-notice">
      注意: 現行ルーティング品番の取得に失敗したため、ルーティングフィルタを解除して既存データを表示しています。
    </div>
    <div v-else-if="currentLineRoutingFilterMode === 'empty'" class="line-rule-notice">
      注意: このラインに有効な現行ルーティング品番がないため、表示対象はありません。
    </div>
    <div v-if="isFloorShippingDeliveryLine" class="line-rule-notice">
      注意: フロア配送は同一日・同一品番を sequence_no 昇順で 1件目=8時着、2件目=15時着 と解釈します（暫定運用: sequence_no > 50 は15時着扱い）。入力は 2件までです。
    </div>

    <div class="grid-wrapper" ref="gridWrapperRef">
      <table class="plan-grid" :class="{ 'hide-weekends': hideWeekends }" :style="{ minWidth: tableMinWidth + 'px' }">
        <colgroup>
          <col style="width: 30px" />
          <col style="width: 135px" />
          <col style="width: 100px" />
          <template v-for="c in visibleDateColumns" :key="`col-${c.key}`">
            <col :style="{ width: DAY_COL_WIDTH + 'px' }" />
            <col :style="{ width: DAY_COL_WIDTH + 'px' }" />
            <col :style="{ width: DAY_COL_WIDTH + 'px' }" />
            <col :style="{ width: DAY_COL_WIDTH + 'px' }" />
            <col :style="{ width: SEQUENCE_COL_WIDTH + 'px' }" />
            <col :style="{ width: DAY_COL_WIDTH + 'px' }" />
            <col v-if="c.weekGap" style="width: 6px" />
          </template>
        </colgroup>
        <thead>
          <tr class="head-level1">
            <th rowspan="3" class="sticky-col number-col">No</th>
            <th rowspan="3" class="sticky-col code-col">品番</th>
            <th rowspan="3" class="sticky-col name-col">品名</th>
            <template v-for="(c, colIdx) in visibleDateColumns" :key="c.key">
            <th
              colspan="6"
              class="date-head day-end"
              :class="c.dayClass"
            >
              <div class="date-header-content-horizontal">
                <span class="date-label">{{ c.label }}</span>
                <input
                  type="text"
                  inputmode="numeric"
                  :value="dailySettings[c.key]?.final_process_start_time || ''"
                  @input="onDailySettingTimeChange(c.key, $event.target.value)"
                  @blur="onDailySettingTimeBlur(c.key)"
                  class="time-input-inline"
                  :placeholder="finalProcessStartTime || '08:00'"
                  maxlength="5"
                  :title="`最終工程開始時刻（未設定時はデフォルト ${finalProcessStartTime || '08:00'} を使用）`"
                />
                <span v-if="getWorkTimeLabel(c.key)" class="work-time-label">
                  {{ getWorkTimeLabel(c.key) }}
                </span>
              </div>
            </th>
            <th v-if="c.weekGap" rowspan="3" class="week-gap"></th>
            </template>
          </tr>
          <tr class="head-level1b">
            <template v-for="(c, colIdx) in visibleDateColumns" :key="c.key">
              <th colspan="6" class="date-head day-end" :class="c.dayClass">
                <div class="date-header-content-horizontal">
                  <span v-if="getDayDemandMovingAvg(c.key)" class="day-plan-avg">需五:{{ getDayDemandMovingAvg(c.key) }}</span>
                  <span v-if="getDayDemandMovingAvg(c.key, 10)" class="day-plan-avg">需十:{{ getDayDemandMovingAvg(c.key, 10) }}</span>
                  <button
                    v-if="canShowFloorSpotAutoPlanButton"
                    type="button"
                    class="btn-day-apply"
                    :disabled="processing || !selectedLine || isPlanCellLocked(c.key)"
                    @click="applyDemandToPlanForDay(c.key)"
                    title="この日の需要を計画にセット"
                  >→</button>
                  <button
                    type="button"
                    class="btn-day-clear"
                    :disabled="processing || !selectedLine"
                    @click="clearDayPlan(c.key)"
                    title="この日の計画をクリアして順番を振り直す"
                  >×</button>
                  <button
                    type="button"
                    class="btn-day-plus"
                    :disabled="processing || !selectedLine"
                    @click="createIntegratedChecksheetForDay(c.key)"
                    title="この日の計画から工程一体チェックシートを作成"
                  >＋</button>
                  <span v-if="getDayPlanTotal(c.key)" class="day-plan-total">計合:{{ getDayPlanTotal(c.key) }}</span>
                </div>
              </th>
            </template>
          </tr>
          <tr class="head-level2">
            <template v-for="(c, colIdx) in visibleDateColumns" :key="c.key">
              <th class="mini stock-col" :class="c.dayClass">{{ isProgressMode ? '進度' : '在庫' }}</th>
              <th class="mini actual-col" :class="c.dayClass">実績</th>
              <th class="mini demand-col" :class="c.dayClass">{{ isProgressMode ? '受注' : '需要' }}</th>
              <th class="mini plan-col" :class="c.dayClass">計画</th>
              <th class="mini sequence-col" :class="c.dayClass">順</th>
              <th class="mini stock-plan-col day-end" :class="c.dayClass">{{ isProgressMode ? '計進' : '計庫' }}</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, idx) in filteredRows"
            :key="row.id"
            :class="{ 'active-input-row': activeInputRowId === row.id }"
            :style="getRowColorStyle(row)"
          >
            <td class="sticky-col number-col">
              <span class="product-info">{{ idx + 1 }}</span>
            </td>
            <td class="sticky-col code-col">
              <span class="product-info">{{ row.product_code || getProductCode(row.product_id) }}</span>
            </td>
            <td class="sticky-col name-col">
              <span class="product-info">{{ row.product_name || getProductName(row.product_id) }}</span>
            </td>
            <template v-for="(c, colIdx) in visibleDateColumns" :key="c.key">
              <td class="num stock" :class="c.dayClass">
                <span
                  class="readonly-value"
                  :class="{ negative: isNegativeValue(isProgressMode ? row.daily?.[c.key]?.progress : getStockDisplay(row, c.key)) }"
                >{{ displayValue(isProgressMode ? row.daily?.[c.key]?.progress : getStockDisplay(row, c.key)) }}</span>
              </td>
              <td class="num actual" :class="c.dayClass">
                <input
                  v-if="activePlanTab === 'floor-shipping'"
                  type="text"
                  inputmode="decimal"
                  :value="row.daily?.[c.key]?.actual === 0 || row.daily?.[c.key]?.actual === '' || row.daily?.[c.key]?.actual == null ? '' : row.daily?.[c.key]?.actual"
                  @input="onActualInput(row, c.key, $event.target.value)"
                  :data-row="idx"
                  :data-col="colIdx"
                  data-field="actual"
                  @keydown="onCellKeydown($event, idx, colIdx, 'actual')"
                  @focus="setActiveInputRow(row, $event)"
                  @blur="onCellBlur"
                />
                <span v-else class="readonly-value">{{ displayValue(row.daily?.[c.key]?.actual) }}</span>
              </td>
              <td class="num demand" :class="c.dayClass">
                <span class="readonly-value">{{ displayValue(isProgressMode ? row.daily?.[c.key]?.line_demand_qty : row.daily?.[c.key]?.demand) }}</span>
              </td>
              <td class="num plan" :class="c.dayClass">
                <div class="lot-stack">
                  <input
                    type="text"
                    inputmode="decimal"
                    :value="row.daily?.[c.key]?.plan === 0 || row.daily?.[c.key]?.plan === '' || row.daily?.[c.key]?.plan == null ? '' : row.daily?.[c.key]?.plan"
                    @input="onPlanInput(row, c.key, $event.target.value)"
                    :data-row="idx"
                    :data-col="colIdx"
                    data-field="plan"
                    @keydown="onCellKeydown($event, idx, colIdx, 'plan')"
                    @focus="setActiveInputRow(row, $event)"
                    @blur="onCellBlur"
                    :disabled="isPlanCellLocked(c.key)"
                    :readonly="isHolidayDate(c.key)"
                    :class="{ locked: isPlanCellLocked(c.key) }"
                  />
                  <div
                    v-for="(lot, lotIdx) in row.daily?.[c.key]?.extraLots"
                    :key="lot.id || lotIdx"
                    class="lot-item"
                  >
                    <input
                      type="text"
                      inputmode="decimal"
                      :value="lot.plan_qty === 0 || lot.plan_qty === '' || lot.plan_qty == null ? '' : lot.plan_qty"
                      @input="onExtraPlanInput(row, c.key, lot, $event.target.value)"
                      @focus="setActiveInputRow(row, $event)"
                      @blur="onCellBlur"
                      :disabled="isPlanCellLocked(c.key)"
                      :readonly="isHolidayDate(c.key)"
                      :class="{ locked: isPlanCellLocked(c.key) }"
                    />
                  </div>
                  <button class="mini-btn lot-add" type="button" @click="addExtraLot(row, c.key)" :disabled="isPlanCellLocked(c.key) || isHolidayDate(c.key) || (isFloorShippingDeliveryLine && row.daily?.[c.key]?.extraLots?.length >= 1)" :style="getPlanCellStyle(row)">+</button>
                </div>
              </td>
              <td class="num sequence" :class="c.dayClass">
                <div class="lot-stack">
                  <input
                    type="text"
                    inputmode="numeric"
                    :value="row.daily?.[c.key]?.sequence_no === 0 || row.daily?.[c.key]?.sequence_no === '' || row.daily?.[c.key]?.sequence_no == null ? '' : row.daily?.[c.key]?.sequence_no"
                    @input="onSequenceInput(row, c.key, $event.target.value)"
                    :data-row="idx"
                    :data-col="colIdx"
                    data-field="sequence"
                    @keydown="onCellKeydown($event, idx, colIdx, 'sequence')"
                    @focus="setActiveInputRow(row, $event)"
                    @blur="onCellBlur"
                    :disabled="isPlanCellLocked(c.key)"
                    :class="{ locked: isPlanCellLocked(c.key) }"
                  />
                  <div
                    v-for="(lot, lotIdx) in row.daily?.[c.key]?.extraLots"
                    :key="lot.id || lotIdx"
                    class="lot-item lot-item-vertical"
                  >
                    <input
                      type="text"
                      inputmode="numeric"
                      :value="lot.sequence_no === 0 || lot.sequence_no === '' || lot.sequence_no == null ? '' : lot.sequence_no"
                      @input="onExtraSequenceInput(row, c.key, lot, $event.target.value)"
                      @focus="setActiveInputRow(row, $event)"
                      @blur="onCellBlur"
                      :disabled="isPlanCellLocked(c.key)"
                      :class="{ locked: isPlanCellLocked(c.key) }"
                    />
                    <button class="mini-btn lot-remove" type="button" @click="removeExtraLot(row, c.key, lot.id)" :disabled="isPlanCellLocked(c.key)">x</button>
                  </div>
                </div>
              </td>
              <td class="num stock-plan day-end" :class="c.dayClass">
                <span
                  class="readonly-value"
                  :class="{ negative: isNegativeValue(isProgressMode ? getPlannedProgressDisplay(row, c.key) : getPlanStockDisplay(row, c.key)) }"
                >{{ displayValue(isProgressMode ? getPlannedProgressDisplay(row, c.key) : getPlanStockDisplay(row, c.key)) }}</span>
              </td>
              <td v-if="c.weekGap" class="week-gap"></td>
            </template>
          </tr>
          <tr v-if="isFloorShippingDeliveryLine" class="cart-summary-row">
            <td class="sticky-col number-col"></td>
            <td class="sticky-col code-col cart-label" colspan="2">8時着台車数</td>
            <template v-for="c in visibleDateColumns" :key="'am-cart-' + c.key">
              <td :class="c.dayClass"></td>
              <td :class="c.dayClass"></td>
              <td :class="c.dayClass"></td>
              <td class="num cart-value" :class="c.dayClass">{{ floorShippingCartCounts[c.key]?.am || '' }}</td>
              <td :class="c.dayClass"></td>
              <td :class="c.dayClass" class="day-end"></td>
              <td v-if="c.weekGap" class="week-gap"></td>
            </template>
          </tr>
          <tr v-if="isFloorShippingDeliveryLine" class="cart-summary-row">
            <td class="sticky-col number-col"></td>
            <td class="sticky-col code-col cart-label" colspan="2">15時着台車数</td>
            <template v-for="c in visibleDateColumns" :key="'pm-cart-' + c.key">
              <td :class="c.dayClass"></td>
              <td :class="c.dayClass"></td>
              <td :class="c.dayClass"></td>
              <td class="num cart-value" :class="c.dayClass">{{ floorShippingCartCounts[c.key]?.pm || '' }}</td>
              <td :class="c.dayClass"></td>
              <td :class="c.dayClass" class="day-end"></td>
              <td v-if="c.weekGap" class="week-gap"></td>
            </template>
          </tr>
          <tr v-if="!filteredRows.length">
            <td :colspan="3 + visibleDateColumns.length * 6 + visibleDateColumns.filter(c => c.weekGap).length" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="gantt-section" v-if="showProcessGantt">
      <div class="process-header">
        <div class="process-info">
          <div class="process-title">
            工程ガント（勤務時間のみ表示）
            <span class="process-title-inline">ライン {{ selectedLine || '' }}</span>
            <span class="process-title-inline">期間 {{ startDate }} ～ {{ endDate }}</span>
          </div>
        </div>
        <div class="process-actions">
          <div class="field checkbox-field gantt-toggle-field">
            <label>
              <input type="checkbox" v-model="showGanttAddAnchors" />
              ＋表示
            </label>
          </div>
          <button
            class="btn gantt-save-btn"
            :class="{ 'gantt-save-dirty': ganttEditDirty }"
            @click="saveGanttEditChanges"
            :disabled="!selectedLine || !ganttEditDirty"
          >
            時間数量保存
          </button>
          <button
            class="btn gantt-save-btn"
            :class="{ 'gantt-save-dirty': ganttStructureDirty }"
            @click="saveGanttStructureChanges"
            :disabled="!selectedLine || !ganttStructureDirty"
          >
            追加削除保存
          </button>
        </div>
      </div>
      <ProcessGanttView
        :key="ganttReloadKey"
        ref="ganttRef"
        :embedded="true"
        :preset-line="selectedLine"
        :preset-base-date="startDate"
        :preset-start-date="startDate"
        :preset-end-date="endDate"
        :show-add-anchors="showGanttAddAnchors"
        @dirty-change="onGanttDirtyChange"
        @mode-change="onGanttModeChange"
        @edit-dirty-change="onGanttEditDirtyChange"
        @structure-dirty-change="onGanttStructureDirtyChange"
      />
    </div>


    <div class="load-section" v-if="showProcessLoad">
      <div class="process-header">
        <div class="process-title">工程別 日別負荷 分（H）</div>
        <div class="process-meta">ライン {{ selectedLine || '' }} ／ 期間 {{ startDate }} ? {{ endDate }}</div>
      </div>
      <div class="load-body">
        <div v-if="processLoadLoading" class="load-message">読込中...</div>
        <div v-else-if="processLoadMessage" class="load-message">{{ processLoadMessage }}</div>
        <div v-else class="load-table-wrap">
          <table class="load-table" :style="{ minWidth: loadTableMinWidth + 'px' }">
            <thead>
              <tr>
                <th class="sticky-col load-process-col">工程</th>
                <th v-for="c in visibleDateColumns" :key="c.key" class="mini" :class="c.dayClass">
                  {{ c.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="proc in processLoadRows" :key="proc.process_id">
                <td class="sticky-col load-process-col">{{ proc.process_name || proc.process_id }}</td>
                <td v-for="c in visibleDateColumns" :key="c.key" class="num" :class="c.dayClass">
                  <span class="readonly-value">{{ displayValue(formatLoad(proc.daily?.[c.key])) }}</span>
                </td>
              </tr>
              <tr v-if="!processLoadRows.length">
                <td :colspan="visibleDateColumns.length + 1" class="no-data">表示する負荷データがありません</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="footer-actions">
      <button class="btn-secondary" @click="goBack">F1: 戻る</button>
      <button class="btn-secondary" @click="goForward">F2: 進む</button>
      <button class="btn-secondary" @click="resetRows" :disabled="processing">F3: クリア</button>
      <button class="btn-secondary" @click="doDisplayOnly" :disabled="processing || !selectedLine">F4: 表示のみ</button>
      <button class="btn-secondary" @click="doFetchOnly" :disabled="processing || !selectedLine">F6: 需要取込</button>
      <button class="btn-secondary" @click="doPickup" :disabled="processing || !selectedLine">F8: 取込＋在庫計算</button>
      <button class="btn-secondary" @click="resetRows" :disabled="processing">F5: キャンセル</button>
      <button class="btn-secondary" @click="openExportDialog" :disabled="processing || !filteredRows.length">F10: 印刷</button>
      <div v-if="showProcessGantt" class="footer-gantt-controls">
        <span class="footer-gantt-label">表示モード</span>
        <button
          type="button"
          class="btn-secondary footer-mode-btn"
          :class="{ active: !ganttMergeConsecutive }"
          @click="setGanttMergeMode(false)"
        >
          分解
        </button>
        <button
          type="button"
          class="btn-secondary footer-mode-btn"
          :class="{ active: ganttMergeConsecutive }"
          @click="setGanttMergeMode(true)"
        >
          連結
        </button>
        <label class="footer-gantt-toggle">
          <input type="checkbox" v-model="showGanttAddAnchors" />
          ＋表示
        </label>
        <button
          class="btn-secondary footer-gantt-save-btn"
          :class="{ 'gantt-save-dirty': ganttEditDirty }"
          @click="saveGanttEditChanges"
          :disabled="!selectedLine || !ganttEditDirty"
        >
          時間数量保存
        </button>
        <button
          class="btn-secondary footer-gantt-save-btn"
          :class="{ 'gantt-save-dirty': ganttStructureDirty }"
          @click="saveGanttStructureChanges"
          :disabled="!selectedLine || !ganttStructureDirty"
        >
          追加削除保存
        </button>
      </div>
    </div>
    <div v-if="showChangeReasonDialog" class="modal-overlay" @click.self="closeChangeReasonDialog">
      <div class="modal-content">
        <h2>変更理由入力</h2>
        <textarea
          v-model="changeReasonDraft"
          rows="4"
          placeholder="変更理由を入力してください"
        ></textarea>
        <div class="modal-actions">
          <button class="btn" @click="closeChangeReasonDialog">キャンセル</button>
          <button class="btn primary" @click="confirmChangeReason">確定</button>
        </div>
      </div>
    </div>

    <div v-if="showProductOrderDialog" class="modal-overlay" @click.self="showProductOrderDialog = false">
      <div class="modal-content" style="width: 820px; max-height: 80vh; overflow-y: auto;">
        <h2>製品表示順設定（{{ selectedLineLabel }}）</h2>
        <div style="display: flex; gap: 16px;">
          <div style="flex: 1; min-width: 0;">
            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
              <thead>
                <tr>
                  <th style="width: 24px; padding: 3px 4px; border-bottom: 1px solid #d7dfe8; background: #f5f6fa;">#</th>
                  <th style="padding: 3px 4px; border-bottom: 1px solid #d7dfe8; background: #f5f6fa; text-align: left;">品番</th>
                  <th style="padding: 3px 4px; border-bottom: 1px solid #d7dfe8; background: #f5f6fa; text-align: left;">品名</th>
                  <th style="width: 110px; padding: 3px 4px; border-bottom: 1px solid #d7dfe8; background: #f5f6fa; text-align: center;">行色 (R G B)</th>
                  <th style="width: 110px; padding: 3px 4px; border-bottom: 1px solid #d7dfe8; background: #f5f6fa; text-align: center;">+色 (R G B)</th>
                  <th style="width: 48px; padding: 3px 4px; border-bottom: 1px solid #d7dfe8; background: #f5f6fa; text-align: center;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in productOrderItems" :key="item.product_code"
                  :style="{
                    background: productOrderActiveCode === item.product_code ? '#dbeafe'
                      : item.bg_color ? item.bg_color : '',
                  }">
                  <td style="padding: 3px 4px; border-bottom: 1px solid #e5e5e5;">{{ idx + 1 }}</td>
                  <td style="padding: 3px 4px; border-bottom: 1px solid #e5e5e5; font-size: 10px;">{{ item.product_code }}</td>
                  <td style="padding: 3px 4px; border-bottom: 1px solid #e5e5e5;">
                    {{ item.product_name }}
                    <span v-if="item.plan_bg_color"
                      style="display: inline-block; margin-left: 3px; width: 16px; height: 13px; border-radius: 2px; vertical-align: middle; font-size: 9px; text-align: center; line-height: 13px; border: 1px solid #aaa;"
                      :style="{ background: item.plan_bg_color, color: item.plan_text_color || '#000' }"
                    >+</span>
                  </td>
                  <td style="padding: 3px 4px; border-bottom: 1px solid #e5e5e5;">
                    <div style="display: flex; align-items: center; gap: 2px;">
                      <span style="display: inline-block; width: 14px; height: 14px; border: 1px solid #aaa; border-radius: 2px; flex-shrink: 0;"
                        :style="{ background: item.bg_color || '#fff' }"></span>
                      <input type="text" inputmode="numeric" :value="hexToR(item.bg_color)" @input="item.bg_color = setRgbChannel(item.bg_color, 'r', $event.target.value)" style="width: 28px; font-size: 9px; padding: 0; border: 1px solid #ccc; border-radius: 2px; text-align: center;" />
                      <input type="text" inputmode="numeric" :value="hexToG(item.bg_color)" @input="item.bg_color = setRgbChannel(item.bg_color, 'g', $event.target.value)" style="width: 28px; font-size: 9px; padding: 0; border: 1px solid #ccc; border-radius: 2px; text-align: center;" />
                      <input type="text" inputmode="numeric" :value="hexToB(item.bg_color)" @input="item.bg_color = setRgbChannel(item.bg_color, 'b', $event.target.value)" style="width: 28px; font-size: 9px; padding: 0; border: 1px solid #ccc; border-radius: 2px; text-align: center;" />
                    </div>
                  </td>
                  <td style="padding: 3px 4px; border-bottom: 1px solid #e5e5e5;">
                    <div style="display: flex; align-items: center; gap: 2px;">
                      <span style="display: inline-block; width: 14px; height: 14px; border: 1px solid #aaa; border-radius: 2px; flex-shrink: 0;"
                        :style="{ background: item.plan_bg_color || '#fff' }"></span>
                      <input type="text" inputmode="numeric" :value="hexToR(item.plan_bg_color)" @input="item.plan_bg_color = setRgbChannel(item.plan_bg_color, 'r', $event.target.value)" style="width: 28px; font-size: 9px; padding: 0; border: 1px solid #ccc; border-radius: 2px; text-align: center;" />
                      <input type="text" inputmode="numeric" :value="hexToG(item.plan_bg_color)" @input="item.plan_bg_color = setRgbChannel(item.plan_bg_color, 'g', $event.target.value)" style="width: 28px; font-size: 9px; padding: 0; border: 1px solid #ccc; border-radius: 2px; text-align: center;" />
                      <input type="text" inputmode="numeric" :value="hexToB(item.plan_bg_color)" @input="item.plan_bg_color = setRgbChannel(item.plan_bg_color, 'b', $event.target.value)" style="width: 28px; font-size: 9px; padding: 0; border: 1px solid #ccc; border-radius: 2px; text-align: center;" />
                    </div>
                  </td>
                  <td style="padding: 3px 4px; border-bottom: 1px solid #e5e5e5; text-align: center;">
                    <button class="mini-btn" @click="moveProductOrder(idx, -1)" :disabled="idx === 0">&uarr;</button>
                    <button class="mini-btn" @click="moveProductOrder(idx, 1)" :disabled="idx === productOrderItems.length - 1">&darr;</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div style="width: 170px; flex-shrink: 0; font-size: 11px; border-left: 1px solid #d7dfe8; padding-left: 12px;">
            <div style="font-weight: 600; margin-bottom: 6px;">色サンプル</div>
            <div style="margin-bottom: 8px;">
              <div style="font-size: 10px; color: #666; margin-bottom: 3px;">行背景色</div>
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 16px; background: #bfdbfe; border: 1px solid #aaa; border-radius: 2px;"></span>
                <span style="font-family: monospace; font-size: 10px;">191 219 254</span>
                <span style="font-size: 10px; color: #666;">キャブ青</span>
              </div>
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 16px; background: #bbf7d0; border: 1px solid #aaa; border-radius: 2px;"></span>
                <span style="font-family: monospace; font-size: 10px;">187 247 208</span>
                <span style="font-size: 10px; color: #666;">キャノピー緑</span>
              </div>
            </div>
            <div>
              <div style="font-size: 10px; color: #666; margin-bottom: 3px;">+ボタン色</div>
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 16px; background: #d4a574; border: 1px solid #aaa; border-radius: 2px;"></span>
                <span style="font-family: monospace; font-size: 10px;">212 165 116</span>
                <span style="font-size: 10px; color: #666;">A 茶</span>
              </div>
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 16px; background: #bbbbbb; border: 1px solid #aaa; border-radius: 2px;"></span>
                <span style="font-family: monospace; font-size: 10px;">187 187 187</span>
                <span style="font-size: 10px; color: #666;">B グレー</span>
              </div>
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 16px; background: #444444; border: 1px solid #aaa; border-radius: 2px;"></span>
                <span style="font-family: monospace; font-size: 10px;">&nbsp;68 &nbsp;68 &nbsp;68</span>
                <span style="font-size: 10px; color: #666;">C 濃灰</span>
              </div>
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 16px; background: #fbbf24; border: 1px solid #aaa; border-radius: 2px;"></span>
                <span style="font-family: monospace; font-size: 10px;">251 191 &nbsp;36</span>
                <span style="font-size: 10px; color: #666;">D 黄</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showProductOrderDialog = false">キャンセル</button>
          <button class="btn primary" @click="saveProductOrder" :disabled="productOrderSaving">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showExportDialog" class="modal-overlay" @click.self="closeExportDialog">
      <div class="modal-content export-modal">
        <h2>出力形式を選択してください</h2>
        <p class="export-note">
          対象: 現在の絞り込み結果（ライン: {{ selectedLineLabel || '未選択' }} ／ 期間: {{ startDate }} ～ {{ endDate }} ／ 日替わり時刻 08:00）
        </p>
        <div class="export-actions">
          <button class="btn" @click="exportToExcel" :disabled="!filteredRows.length">Excel出力</button>
          <button class="btn primary" @click="exportToPdf" :disabled="!filteredRows.length">PDF出力</button>
          <button class="btn" @click="closeExportDialog">キャンセル</button>
        </div>
      </div>
    </div>

    <div v-if="showBulkActualDialog" class="modal-overlay" @click.self="closeBulkActualDialog">
      <div class="modal-content">
        <h2>実績一括入力</h2>
        <p class="export-note">期間内の計画合計を実績セルへセットします。セット後に差分だけ手修正してください。</p>
        <div class="field">
          <label>開始日</label>
          <input type="date" v-model="bulkActualStartDate" />
        </div>
        <div class="field">
          <label>終了日</label>
          <input type="date" v-model="bulkActualEndDate" />
        </div>
        <div class="modal-actions">
          <button class="btn" type="button" @click="closeBulkActualDialog">キャンセル</button>
          <button class="btn primary" type="button" @click="applyBulkActualFromPlan">セット</button>
        </div>
      </div>
    </div>

    <div v-if="processing" class="processing-overlay">
      <div class="processing-box">
        <p class="processing-title">データ更新中</p>
        <p class="processing-sub">少々お待ちください</p>
      </div>
    </div>
    <div
      v-if="cursorProductTail"
      class="cursor-product-bubble"
      :style="cursorProductBubbleStyle"
    >{{ cursorProductTail }}</div>
    </template>
    <LaserPatternEditor
      v-else-if="activePlanTab === 'laser' && activeLaserTab === 'pattern-editor'"
      class="laser-editor-section"
    />
    <div v-else-if="activePlanTab === 'spot' && activeSpotTab === 'excel'" class="laser-third-tab-panel">
      <div class="spot-excel-toolbar">
        <div class="field">
          <label>ライン</label>
          <select v-model="selectedLine">
            <option v-for="line in availableLines" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>
        <label class="btn spot-file-btn">
          Excel選択
          <input type="file" accept=".xlsx,.xls" @change="onSpotExcelFileChange" />
        </label>
        <button
          class="btn primary"
          @click="saveSpotExcelPlan"
          :disabled="processing || spotExcelLoading || !spotExcelRows.length || !selectedLine"
        >
          forup取込保存
        </button>
      </div>
      <div class="spot-excel-note">
        取込対象: forupシートの「部番 / 計画日 / 計画数」。sequence_no は 1 固定で保存します。
      </div>
      <div class="spot-excel-meta">
        <span v-if="spotExcelFileName">ファイル: {{ spotExcelFileName }}</span>
        <span v-if="spotExcelMessage">{{ spotExcelMessage }}</span>
      </div>
      <div v-if="spotExcelMissingProducts.length || spotExcelMissingProcesses.length" class="spot-excel-errors">
        <div v-if="spotExcelMissingProducts.length" class="spot-excel-error-card">
          <div class="spot-excel-error-title">未登録品番（{{ spotExcelMissingProducts.length }}件）</div>
          <ul>
            <li v-for="item in spotExcelMissingProducts" :key="`miss-prod-${item.row_no}-${item.product_code}`">
              行{{ item.row_no }}: {{ item.product_code }}
            </li>
          </ul>
        </div>
        <div v-if="spotExcelMissingProcesses.length" class="spot-excel-error-card">
          <div class="spot-excel-error-title">工程未設定（{{ spotExcelMissingProcesses.length }}件）</div>
          <ul>
            <li v-for="item in spotExcelMissingProcesses" :key="`miss-proc-${item.row_no}-${item.product_code}`">
              行{{ item.row_no }}: {{ item.product_code }}
            </li>
          </ul>
        </div>
      </div>
      <div class="spot-excel-table-wrap">
        <table class="spot-excel-table">
          <thead>
            <tr>
              <th>No</th>
              <th>部番</th>
              <th>計画日</th>
              <th>計画数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, idx) in spotExcelRows" :key="`spot-excel-${idx}`">
              <td>{{ idx + 1 }}</td>
              <td>{{ r.product_code }}</td>
              <td>{{ r.plan_date }}</td>
              <td class="num">{{ r.plan_qty }}</td>
            </tr>
            <tr v-if="!spotExcelRows.length">
              <td colspan="4" class="no-data">Excelを選択してください。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <LaserMonthlyMaterialSummary v-else class="laser-summary-section" />
    </template>

    <div v-else class="settings-panel">
      <h3 class="settings-title">ライン編集</h3>

      <div class="settings-section">
        <div class="settings-section-header" @click="settingsCollapsed.lines = !settingsCollapsed.lines">
          <span class="settings-section-arrow">{{ settingsCollapsed.lines ? '▶' : '▼' }}</span>
          タブ別ライン選択
        </div>
        <div v-show="!settingsCollapsed.lines" class="settings-section-body">
          <p class="settings-note">タブごとに表示対象のラインを選択して保存します。</p>
          <div class="settings-selector">
            <label>対象タブ</label>
            <select v-model="settingsTargetTab">
              <option v-for="tab in configurablePlanTabs" :key="`plan-line-setting-${tab.key}`" :value="tab.key">
                {{ tab.label }}
              </option>
            </select>
          </div>
          <div class="settings-list">
            <label v-for="line in lines" :key="`plan-target-${line.id}`" class="settings-check">
              <input
                type="checkbox"
                :checked="isLineSelectedForTargetTab(line.line_code)"
                @change="toggleLineForTargetTab(line.line_code)"
              />
              <span>{{ line.line_code }} - {{ line.line_name }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-header" @click="settingsCollapsed.prevDayShift = !settingsCollapsed.prevDayShift">
          <span class="settings-section-arrow">{{ settingsCollapsed.prevDayShift ? '▶' : '▼' }}</span>
          前日シフト台数設定（ライン×工程）
          <span class="settings-section-count">{{ prevDayShiftRules.length }}件</span>
        </div>
        <div v-show="!settingsCollapsed.prevDayShift" class="settings-section-body">
          <div class="settings-rule-editor">
            <select v-model="prevDayShiftDraft.lineCode">
              <option value="">ライン選択</option>
              <option v-for="line in lines" :key="`shift-line-${line.id}`" :value="normalizeLineCode(line.line_code)">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
            <select v-model="prevDayShiftDraft.processCode">
              <option value="">工程選択</option>
              <option v-for="proc in processOptions" :key="`shift-proc-${proc.id}`" :value="normalizeProcessCode(proc.process_code)">
                {{ proc.process_code }} - {{ proc.process_name }}
              </option>
            </select>
            <input v-model.number="prevDayShiftDraft.shiftQty" type="number" min="1" step="1" placeholder="台数" />
            <button class="btn" type="button" @click="addPrevDayShiftRule">追加</button>
          </div>
          <div class="settings-list settings-rules">
            <div v-for="(rule, idx) in prevDayShiftRules" :key="`shift-rule-${rule.lineCode}-${rule.processCode}`" class="settings-rule-row">
              <span>{{ rule.lineCode }} / {{ rule.processCode }} / 前日シフト {{ rule.shiftQty }}台</span>
              <button class="btn" type="button" @click="removePrevDayShiftRule(idx)">削除</button>
            </div>
            <div v-if="!prevDayShiftRules.length" class="settings-note">設定なし</div>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-header" @click="settingsCollapsed.ganttStartTime = !settingsCollapsed.ganttStartTime">
          <span class="settings-section-arrow">{{ settingsCollapsed.ganttStartTime ? '▶' : '▼' }}</span>
          ガント開始時刻設定（ライン×工程）
          <span class="settings-section-count">{{ ganttStartTimeRules.length }}件</span>
        </div>
        <div v-show="!settingsCollapsed.ganttStartTime" class="settings-section-body">
          <div class="settings-rule-editor">
            <select v-model="ganttStartTimeDraft.lineCode">
              <option value="">ライン選択</option>
              <option v-for="line in lines" :key="`gst-line-${line.id}`" :value="normalizeLineCode(line.line_code)">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
            <select v-model="ganttStartTimeDraft.processCode">
              <option value="">工程選択</option>
              <option v-for="proc in processOptions" :key="`gst-proc-${proc.id}`" :value="normalizeProcessCode(proc.process_code)">
                {{ proc.process_code }} - {{ proc.process_name }}
              </option>
            </select>
            <input v-model="ganttStartTimeDraft.startTime" type="time" step="60" />
            <button class="btn" type="button" @click="addGanttStartTimeRule">追加</button>
          </div>
          <div class="settings-list settings-rules">
            <div v-for="(rule, idx) in ganttStartTimeRules" :key="`gst-rule-${rule.lineCode}-${rule.processCode}`" class="settings-rule-row">
              <span>{{ rule.lineCode }} / {{ rule.processCode }} / 開始 {{ rule.startTime }}</span>
              <button class="btn" type="button" @click="removeGanttStartTimeRule(idx)">削除</button>
            </div>
            <div v-if="!ganttStartTimeRules.length" class="settings-note">設定なし</div>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-header" @click="settingsCollapsed.calcSpecial = !settingsCollapsed.calcSpecial">
          <span class="settings-section-arrow">{{ settingsCollapsed.calcSpecial ? '▶' : '▼' }}</span>
          計算特例（ライン×工程×計算対象×設定）
          <span class="settings-section-count">{{ plannedStockCalcRules.length }}件</span>
        </div>
        <div v-show="!settingsCollapsed.calcSpecial" class="settings-section-body">
          <div class="settings-rule-editor">
            <select v-model="plannedStockCalcDraft.lineCode">
              <option value="">ライン選択</option>
              <option v-for="line in lines" :key="`psc-line-${line.id}`" :value="normalizeLineCode(line.line_code)">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
            <select v-model="plannedStockCalcDraft.processCode">
              <option value="">工程選択</option>
              <option v-for="proc in processOptions" :key="`psc-proc-${proc.id}`" :value="normalizeProcessCode(proc.process_code)">
                {{ proc.process_code }} - {{ proc.process_name }}
              </option>
            </select>
            <select v-model="plannedStockCalcDraft.calcTarget">
              <option value="PLANNED_STOCK">計画在庫</option>
              <option value="STOCK">在庫</option>
              <option value="DEMAND">需要</option>
            </select>
            <select v-model="plannedStockCalcDraft.setting">
              <option value="PARENT_PLAN">後工程計画使用</option>
            </select>
            <button class="btn" type="button" @click="addPlannedStockCalcRule">追加</button>
          </div>
          <div class="settings-list settings-rules">
            <div v-for="(rule, idx) in plannedStockCalcRules" :key="`psc-rule-${rule.lineCode}-${rule.processCode}-${rule.calcTarget}`" class="settings-rule-row">
              <span>{{ rule.lineCode }} / {{ rule.processCode }} / {{ rule.calcTargetLabel || rule.calcTarget }} / {{ rule.settingLabel || rule.setting }}</span>
              <button class="btn" type="button" @click="removePlannedStockCalcRule(idx)">削除</button>
            </div>
            <div v-if="!plannedStockCalcRules.length" class="settings-note">設定なし</div>
          </div>
        </div>
      </div>
      <div class="settings-actions">
        <button class="btn" type="button" @click="saveLineSettings">保存</button>
      </div>
      <div v-if="lineSettingsMessage" class="settings-message">{{ lineSettingsMessage }}</div>
    </div>

    <!-- 北進塗装 納品書 確認モーダル -->
    <div v-if="hokushinDialogOpen" class="hokushin-dialog-overlay" @click.self="closeHokushinDialog">
      <div class="hokushin-dialog">
        <h3 class="hokushin-dialog-title">㈱北進塗装 納品書 発行確認</h3>
        <div v-if="!hokushinDialogEdit" class="hokushin-dialog-body">
          <p class="hokushin-dialog-text">
            <span class="hokushin-date">{{ formatJPDate(hokushinAmDate) }}15時着</span><br/>
            <span class="hokushin-date">{{ formatJPDate(hokushinYoiDate) }}8時着</span><br/>
            納品書を発行しますか？
          </p>
          <div v-if="!hokushinAmHasItems || !hokushinYoiHasItems" class="hokushin-dialog-warn">
            <template v-if="!hokushinAmHasItems && !hokushinYoiHasItems">
              ※両便とも明細がありません
            </template>
            <template v-else-if="!hokushinAmHasItems">
              ※AM便は明細がありません（宵積みのみ出力されます）
            </template>
            <template v-else>
              ※宵積みは明細がありません（AM便のみ出力されます）
            </template>
          </div>
          <div class="hokushin-dialog-actions">
            <button class="btn primary" @click="confirmHokushinDialog">はい</button>
            <button class="btn" @click="hokushinDialogEdit = true">いいえ</button>
            <button class="btn" @click="closeHokushinDialog">キャンセル</button>
          </div>
        </div>
        <div v-else class="hokushin-dialog-body">
          <p class="hokushin-dialog-text">日付を変更してください</p>
          <div class="hokushin-edit-row">
            <label>AM便 (15時着):</label>
            <input type="date" v-model="hokushinAmDate" />
          </div>
          <div class="hokushin-edit-row">
            <label>宵積み (8時着):</label>
            <input type="date" v-model="hokushinYoiDate" />
          </div>
          <div class="hokushin-dialog-actions">
            <button class="btn primary" @click="confirmHokushinDialog">OK</button>
            <button class="btn" @click="closeHokushinDialog">キャンセル</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 北進塗装 納品書２（全製品）確認モーダル -->
    <div v-if="hokushinAllDialogOpen" class="hokushin-dialog-overlay" @click.self="closeHokushinAllDialog">
      <div class="hokushin-dialog">
        <h3 class="hokushin-dialog-title">㈱北進塗装 納品書２（全製品）発行確認</h3>
        <div v-if="!hokushinAllDialogEdit" class="hokushin-dialog-body">
          <p class="hokushin-dialog-text">
            <span class="hokushin-date">{{ formatJPDate(hokushinAllAmDate) }}15時着</span><br/>
            <span class="hokushin-date">{{ formatJPDate(hokushinAllYoiDate) }}8時着</span><br/>
            納品書２（全製品）を発行しますか？
          </p>
          <div v-if="!hokushinAllAmHasItems || !hokushinAllYoiHasItems" class="hokushin-dialog-warn">
            <template v-if="!hokushinAllAmHasItems && !hokushinAllYoiHasItems">
              ※両便とも数量のある明細がありません（全製品が空白で出力されます）
            </template>
            <template v-else-if="!hokushinAllAmHasItems">
              ※AM便は数量のある明細がありません
            </template>
            <template v-else>
              ※宵積みは数量のある明細がありません
            </template>
          </div>
          <div class="hokushin-dialog-actions">
            <button class="btn primary" @click="confirmHokushinAllDialog">はい</button>
            <button class="btn" @click="hokushinAllDialogEdit = true">いいえ</button>
            <button class="btn" @click="closeHokushinAllDialog">キャンセル</button>
          </div>
        </div>
        <div v-else class="hokushin-dialog-body">
          <p class="hokushin-dialog-text">日付を変更してください</p>
          <div class="hokushin-edit-row">
            <label>AM便 (15時着):</label>
            <input type="date" v-model="hokushinAllAmDate" />
          </div>
          <div class="hokushin-edit-row">
            <label>宵積み (8時着):</label>
            <input type="date" v-model="hokushinAllYoiDate" />
          </div>
          <div class="hokushin-dialog-actions">
            <button class="btn primary" @click="confirmHokushinAllDialog">OK</button>
            <button class="btn" @click="closeHokushinAllDialog">キャンセル</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 過去から再計算 警告モーダル -->
  <div v-if="showRecalcWarning" class="recalc-overlay" @click.self="showRecalcWarning = false">
    <div class="recalc-modal">
      <div class="recalc-warning-text">
        <p>⚠ 注意</p>
        <ul>
          <li>過去の日の実績を入力した後にのみ実行してください。</li>
          <li>表示開始日を実績入力日の一番古い日にしてください。</li>
        </ul>
        <p>むやみに実行すると在庫・進度データが不整合になる恐れがあります。</p>
      </div>
      <div class="recalc-modal-buttons">
        <button class="btn" @click="showRecalcWarning = false">キャンセル</button>
        <button class="btn primary" @click="showRecalcWarning = false; recalculateProgressFromPast()">続行</button>
      </div>
    </div>
  </div>

  <!-- まとめ生産設定ダイアログ -->
  <div v-if="showAggregateDialog" class="modal-overlay" @click.self="showAggregateDialog = false">
    <div class="modal-content" style="max-width: 900px; width: 90%;">
      <h2 style="margin: 0 0 10px; font-size: 16px;">まとめ生産設定 — {{ selectedLineLabel }}</h2>
      <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 10px; flex-wrap: wrap;">
        <select v-model="aggForm.product" style="min-width: 240px; padding: 5px;">
          <option value="">製品選択</option>
          <option v-for="p in aggregateProductOptions" :key="p.product_id" :value="p.product_id">
            {{ p.product_code }} - {{ p.product_name }}
          </option>
        </select>
        <select v-model.number="aggForm.aggregate_weekday" style="padding: 5px;">
          <option v-for="d in aggWeekdayOptions" :key="d.value" :value="d.value">{{ d.label }}</option>
        </select>
        <input v-model.number="aggForm.aggregate_days" type="number" min="1" max="31" style="width: 60px; padding: 5px;" />
        <label style="font-size: 12px;"><input v-model="aggForm.is_active" type="checkbox" /> 有効</label>
        <button class="btn primary" @click="saveAggregateSetting">{{ aggForm.id ? '更新' : '追加' }}</button>
        <button v-if="aggForm.id" class="btn" @click="resetAggForm">取消</button>
      </div>
      <div style="max-height: 400px; overflow-y: auto; border: 1px solid #d7deea;">
        <table class="data-table" style="width: 100%; border-collapse: collapse;">
          <thead><tr>
            <th style="padding: 6px;">製品</th>
            <th style="padding: 6px;">まとめ生産日</th>
            <th style="padding: 6px;">対象期間</th>
            <th style="padding: 6px;">有効</th>
            <th style="padding: 6px;">操作</th>
          </tr></thead>
          <tbody>
            <tr v-for="r in aggRows" :key="r.id">
              <td style="padding: 5px;">{{ r.product_code }} - {{ r.product_name }}</td>
              <td style="padding: 5px;">{{ aggWeekdayLabel(r.aggregate_weekday) }}</td>
              <td style="padding: 5px;">{{ r.aggregate_days }}日</td>
              <td style="padding: 5px;">{{ r.is_active ? '有効' : '無効' }}</td>
              <td style="padding: 5px; white-space: nowrap;">
                <button class="btn" style="padding: 2px 6px; font-size: 11px;" @click="editAggRow(r)">編集</button>
                <button class="btn" style="padding: 2px 6px; font-size: 11px; color: #b00;" @click="deleteAggRow(r.id)">削除</button>
              </td>
            </tr>
            <tr v-if="aggRows.length === 0"><td colspan="5" style="text-align: center; color: #888; padding: 12px;">設定なし</td></tr>
          </tbody>
        </table>
      </div>
      <p style="margin: 8px 0 0; font-size: 11px; color: #888;">※ まとめ対象期間の需要は表示期間内のデータのみ使用します。表示期間末尾の曜日では需要が不足する場合があるため、対象期間分の余裕をもって表示期間を設定してください。</p>
      <div style="text-align: right; margin-top: 10px;">
        <button class="btn" @click="showAggregateDialog = false">閉じる</button>
      </div>
    </div>
  </div>

  <!-- 自動計画確認ダイアログ -->
  <div v-if="showAutoPlanConfirm" class="modal-overlay" @click.self="cancelAutoPlanConfirm">
    <div class="modal-content" style="max-width: 480px;">
      <h2 style="margin: 0 0 10px; font-size: 16px;">自動計画の確認</h2>
      <p style="margin: 0 0 4px;">表示期間内の需要数を計画数へセットして自動計画を実行します。</p>
      <p style="margin: 0 0 4px;">ライン: <strong>{{ autoPlanConfirmLine }}</strong></p>
      <p style="margin: 0 0 8px;">期間: <strong>{{ autoPlanConfirmPeriod }}</strong></p>
      <p style="margin: 0 0 10px;">需要取込→保存（工程展開・在庫計算・ガント生成）を実行します。</p>
      <p style="margin: 0; color: #c00; font-weight: 700; font-size: 13px;">※ まとめ生産の対象期間は表示期間内のデータのみ使用します。表示期間末尾では需要が不足する場合があります。</p>
      <div style="text-align: right; margin-top: 14px; display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn" @click="cancelAutoPlanConfirm">キャンセル</button>
        <button class="btn primary" @click="confirmAutoPlan">OK</button>
      </div>
    </div>
  </div>

  <!-- データソースモーダル -->
  <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
    <div class="ds-modal">
      <div class="ds-header"><h3>データソース</h3><button class="ds-close" @click="showDataSource = false">&times;</button></div>
      <table class="ds-table">
        <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
        <tbody>
          <tr><td colspan="3" style="background:#eef2ff;font-weight:600;color:#3730a3;">計画データ</td></tr>
          <tr><td>計画 読み書き</td><td>line_plan</td><td>ライン別日別生産計画</td></tr>
          <tr><td>需要/実績 読み書き</td><td>line_backlog</td><td>需要(seq=0)・計画実績(seq&gt;0)管理</td></tr>
          <tr><td>需要 読み取り</td><td>line_demand</td><td>顧客需要（内示/確定）</td></tr>
          <tr><td>ガント 生成</td><td>line_gantt_plan</td><td>ガントチャート計画データ</td></tr>
          <tr><td>計画変更ログ</td><td>production_plan_change_log</td><td>計画変更の履歴ログ</td></tr>
          <tr><td colspan="3" style="background:#eef2ff;font-weight:600;color:#3730a3;">設定</td></tr>
          <tr><td>表示順 読み書き</td><td>t_line_product_display_order</td><td>製品の表示順設定</td></tr>
          <tr><td>日別スケジュール 読み書き</td><td>line_daily_schedule_setting</td><td>日別の稼働時間・シフト設定</td></tr>
          <tr><td>デフォルトスケジュール</td><td>t_line_default_schedule_setting</td><td>ライン別デフォルト稼働設定</td></tr>
          <tr><td>自動計画集約 読み書き</td><td>t_auto_plan_aggregate_setting</td><td>自動計画の集約パターン設定</td></tr>
          <tr><td>計画ロック 読み取り</td><td>production_plan_lock_setting</td><td>計画変更ロック日設定</td></tr>
          <tr><td>計算特例 読み書き</td><td>system_setting</td><td>計画在庫計算の特例ルール（キー: production.*）</td></tr>
          <tr><td colspan="3" style="background:#eef2ff;font-weight:600;color:#3730a3;">マスタ</td></tr>
          <tr><td>ライン 読み取り</td><td>m_line</td><td>ラインマスタ</td></tr>
          <tr><td>製品 読み取り</td><td>m_product</td><td>製品マスタ</td></tr>
          <tr><td>工程 読み取り</td><td>m_process</td><td>工程マスタ</td></tr>
          <tr><td>BOM 読み取り</td><td>m_bom / m_bom_item</td><td>部品表（材料構成）</td></tr>
          <tr><td>カレンダー 読み取り</td><td>m_calendar / m_calendar_day</td><td>営業日カレンダー</td></tr>
          <tr><td>勤務パターン 読み取り</td><td>m_work_pattern</td><td>勤務パターンマスタ</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import ProcessGanttView from './ProcessGanttView.vue'
import LaserPatternEditor from './LaserPatternEditor.vue'
import LaserMonthlyMaterialSummary from './LaserMonthlyMaterialSummary.vue'
const router = useRouter()
const showDataSource = ref(false)
const selectedLine = ref('')
const TOOLBAR_COLLAPSED_KEY = 'productionPlanInput.toolbarCollapsed'
const toolbarCollapsed = ref(localStorage.getItem(TOOLBAR_COLLAPSED_KEY) === '1')
const HIDE_WEEKENDS_KEY = 'productionPlanInput.hideWeekends'
const hideWeekends = ref(localStorage.getItem(HIDE_WEEKENDS_KEY) === '1')
const HIDE_EMPTY_ROWS_KEY = 'productionPlanInput.hideEmptyRows'
const hideEmptyRows = ref(localStorage.getItem(HIDE_EMPTY_ROWS_KEY) === '1')
const openManual = (path) => { window.open(`/manual?path=${encodeURIComponent(path)}`, '_blank') }
const toggleToolbar = () => {
  toolbarCollapsed.value = !toolbarCollapsed.value
  localStorage.setItem(TOOLBAR_COLLAPSED_KEY, toolbarCollapsed.value ? '1' : '0')
}
const selectedLineSummary = computed(() => {
  const line = (availableLines.value || []).find((l) => l.id === selectedLine.value)
  if (!line) return 'ライン未選択'
  return `${line.line_code} - ${line.line_name}`
})
const activePlanTab = ref('')
const activeLaserTab = ref('normal-plan')
const selectPlanTab = (tab) => {
  if (activePlanTab.value === tab.key) return
  if (tab.key !== 'line-settings' && !confirm(`${tab.label}の計画作成ですか？`)) return
  activePlanTab.value = tab.key
}
const activeSpotTab = ref('normal-plan')
const activeFloorShippingTab = ref('progress')
const spotExcelRows = ref([])
const spotExcelFileName = ref('')
const spotExcelMessage = ref('')
const spotExcelLoading = ref(false)
const spotExcelProcess4013Id = ref(null)
const spotExcelMissingProducts = ref([])
const spotExcelMissingProcesses = ref([])
const settingsTargetTab = ref('tank')
const planTabs = [
  { key: 'tank', label: 'タンク' },
  { key: 'floor', label: 'フロア' },
  { key: 'kubota', label: 'クボタ' },
  { key: 'floor-shipping', label: 'フロア出荷' },
  { key: 'blade', label: 'ブレード' },
  { key: 'laser', label: 'レーザ' },
  { key: 'brake', label: 'ブレーキ' },
  { key: 'spot', label: 'スポット' },
  { key: 'line-settings', label: 'ライン編集' },
]
const operationalPlanTabs = ['tank', 'floor', 'kubota', 'floor-shipping', 'blade', 'laser', 'brake', 'spot']
const lineKeywordsByTab = {
  tank: ['タンク', 'tank'],
  floor: ['フロア', 'floor'],
  kubota: ['クボタ', 'kubota', '小型'],
  'floor-shipping': ['北進塗装', 'フロア配送'],
  blade: ['ブレード', 'blade'],
  laser: ['レーザ', 'laser'],
  brake: ['ブレーキ', 'brake', 'bend'],
  spot: ['スポット', 'spot'],
}
const PLAN_TARGET_LINES_KEY = 'production_plan_input_target_line_codes_by_tab'
const toDateInput = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
const defaultStart = new Date()
defaultStart.setDate(defaultStart.getDate() - 1)
const startDate = ref(toDateInput(defaultStart))
const horizonDays = ref(7)
const keyword = ref('')
const TANK_LINE_CODE = 'L2200'
const FLOOR_LINE_CODE = 'L2100'
const COPRODUCT_LIMITED_LINE_CODES = new Set(['L2201'])
const TANK_PRODUCT_ORDER = [
  'YD60003386',
  'YD60011305',
  'YD60000441',
  'YD60008491',
  'YD60009848',
  'YD60014764',
  'YD60009783',
  'YD60009874'
]
const FLOOR_SHIPPING_PRODUCT_ORDER = [
  'YD40006245',
  'YD40006630',
  'YD40006237',
  'YD40006618',
  'YD40006842',
  'YD40007003',
  'YD40007243',
  'YD40007372',
  'YD40007722',
  'YD40007688',
  'YD40002946',
]
const FLOOR_L2100_PRODUCT_ORDER = [
  'YD40006245',
  'YD40007003',
  'YD40006842',
  'YD40007243',
  'YD40007372',
  'YD40006630',
  'YD40006618',
  'YD40006237',
  'YD40007688',
  'YD40007722',
  'YD40002946',
  'YD40002683',
]
const FLOOR_4001_COPRODUCT_CHILD_DISPLAY_EXCEPTION_CODES = new Set(['YD40002683'])
const gridWrapperRef = ref(null)
const lockDays = ref(0)
const isEditUnlocked = ref(false)
const changeReason = ref('')
const changeReasonDraft = ref('')
const showChangeReasonDialog = ref(false)
const showBulkActualDialog = ref(false)
const bulkActualStartDate = ref('')
const bulkActualEndDate = ref('')
const showProductOrderDialog = ref(false)
const productOrderItems = ref([])
const productOrderSaving = ref(false)
const productOrderActiveCode = ref('')
const productOrderCache = ref(new Map())
const productColorCache = ref(new Map())
const lineSettingsMessage = ref('')
const settingsCollapsed = ref({ lines: false, prevDayShift: true, ganttStartTime: true, calcSpecial: true })
const prevDayShiftRules = ref([])
const prevDayShiftDraft = ref({
  lineCode: '',
  processCode: '',
  shiftQty: 2,
})
const ganttStartTimeRules = ref([])
const ganttStartTimeDraft = ref({
  lineCode: '',
  processCode: '',
  startTime: '08:00',
})
const plannedStockCalcRules = ref([])
const plannedStockCalcDraft = ref({
  lineCode: '',
  processCode: '',
  calcTarget: 'PLANNED_STOCK',
  setting: 'PARENT_PLAN',
})
const processOptions = ref([])

const lines = ref([])
const products = ref([])
const rows = ref([])
const showProcessGantt = ref(false)
const showProcessLoad = ref(false)
const showGanttAddAnchors = ref(false)
const ganttReloadKey = ref(0)
const ganttRef = ref(null)
const ganttDirty = ref(false)
const ganttEditDirty = ref(false)
const ganttStructureDirty = ref(false)
const ganttMergeConsecutive = ref(false)
const finalProcessStartTime = ref('08:00')
const adjustToBreakEnd = ref(true)
let lotTempId = 1
const processLoadLoading = ref(false)
const processLoadRows = ref([])
const processLoadMessage = ref('')
const dailySettings = ref({})
const calendarDayMap = ref({})
const workPatternMap = ref({})
const daisoCalendarId = ref(undefined)
const workStartFallback = { hour: 8, minute: 0 }
const workMinutesFallback = 480
const GANTT_GENERATE_TIMEOUT_MS = 120000
const processing = ref(false)
const showRecalcWarning = ref(false)
const activeInputRowId = ref(null)
const cursorProductTail = ref('')
const cursorProductBubbleStyle = ref({})
const currentLineRoutingFilterMode = ref('filtered')
const coproductDisplayCache = new Map()

const selectedLineObj = computed(() =>
  lines.value.find((l) => `${l.id}` === `${selectedLine.value}`)
)
const isProgressMode = computed(() =>
  activePlanTab.value === 'floor-shipping' && activeFloorShippingTab.value === 'progress'
)
const isFloorShippingDeliveryLine = computed(() => {
  if (activePlanTab.value !== 'floor-shipping') return false
  const line = selectedLineObj.value
  if (!line) return false
  const text = `${String(line.line_code || '').trim()} ${String(line.line_name || '').trim()}`
  return text.includes('フロア配送')
})
const floorShippingPdfSourceLineId = computed(() => {
  if (isFloorShippingDeliveryLine.value && selectedLine.value) {
    return selectedLine.value
  }
  const deliveryLine = lines.value.find((line) => {
    const text = `${String(line?.line_code || '').trim()} ${String(line?.line_name || '').trim()}`
    return text.includes('フロア配送')
  })
  return deliveryLine?.id || null
})
const canShowDeliveryDetailPDFButton = computed(() => (
  activePlanTab.value === 'floor-shipping'
))
const canShowFloorDeliveryDetailPDFButton = computed(() => (
  activePlanTab.value === 'floor' || activePlanTab.value === 'floor-shipping'
))
const isFloorSpotLine = computed(() => {
  const line = selectedLineObj.value
  if (!line) return false
  const lineCode = String(line.line_code || '').trim().toUpperCase()
  const lineName = String(line.line_name || '').trim()
  return lineCode === 'L2101' || lineName.includes('フロアスポット')
})
const isFloorShippingAutoPlanLine = computed(() => {
  const line = selectedLineObj.value
  if (!line) return false
  const lineCode = String(line.line_code || '').trim().toUpperCase()
  const lineName = String(line.line_name || '').trim()
  return activePlanTab.value === 'floor-shipping' && (lineCode === 'L2102' || lineName.includes('フロア配送'))
})
const canShowFloorSpotAutoPlanButton = computed(() => (
  (activePlanTab.value === 'floor' && isFloorSpotLine.value) || isFloorShippingAutoPlanLine.value
))
// フロア配送: 8時着/15時着台車数（台車1台=2個、異なる製品は混載しない）
const floorShippingCartCounts = computed(() => {
  if (!isFloorShippingDeliveryLine.value) return {}
  const result = {}
  dateColumns.value.forEach((c) => {
    let amCarts = 0
    let pmCarts = 0
    filteredRows.value.forEach((row) => {
      const daily = row.daily?.[c.key]
      if (!daily) return
      // メインロット（1件目=8時着）
      const mainQty = Number(daily.plan) || 0
      const mainSeq = parseInt(daily.sequence_no)
      const mainIsPM = !isNaN(mainSeq) && mainSeq > 50
      if (mainQty > 0) {
        if (mainIsPM) {
          pmCarts += Math.ceil(mainQty / 2)
        } else {
          amCarts += Math.ceil(mainQty / 2)
        }
      }
      // extraLots（2件目=15時着）
      const extras = Array.isArray(daily.extraLots) ? daily.extraLots : []
      extras.forEach((lot) => {
        const qty = Number(lot.plan_qty) || 0
        if (qty > 0) {
          pmCarts += Math.ceil(qty / 2)
        }
      })
    })
    result[c.key] = { am: amCarts, pm: pmCarts }
  })
  return result
})
const configurablePlanTabs = computed(() => planTabs.filter((tab) => operationalPlanTabs.includes(tab.key)))
const normalizeLineCode = (value) => String(value || '').trim().toUpperCase()
const normalizeProcessCode = (value) => String(value || '').trim().toUpperCase()
const normalizeLineCodes = (values) => Array.from(new Set(
  (Array.isArray(values) ? values : []).map((value) => normalizeLineCode(value)).filter(Boolean),
))
const normalizePrevDayShiftRules = (rows) => {
  const source = Array.isArray(rows) ? rows : []
  const seen = new Set()
  const normalized = []
  source.forEach((row) => {
    const lineCode = normalizeLineCode(row?.lineCode)
    const processCode = normalizeProcessCode(row?.processCode)
    const shiftQty = Number(row?.shiftQty)
    if (!lineCode || !processCode || !Number.isFinite(shiftQty) || shiftQty <= 0) return
    const key = `${lineCode}|${processCode}`
    if (seen.has(key)) return
    seen.add(key)
    normalized.push({
      lineCode,
      processCode,
      shiftQty: Math.floor(shiftQty),
    })
  })
  return normalized
}
const normalizeGanttStartTimeRules = (rows) => {
  const source = Array.isArray(rows) ? rows : []
  const seen = new Set()
  const normalized = []
  source.forEach((row) => {
    const lineCode = normalizeLineCode(row?.lineCode)
    const processCode = normalizeProcessCode(row?.processCode)
    const startTime = String(row?.startTime || '').trim()
    if (!lineCode || !processCode || !/^\d{2}:\d{2}$/.test(startTime)) return
    const [hh, mm] = startTime.split(':').map((v) => Number(v))
    if (!Number.isFinite(hh) || !Number.isFinite(mm) || hh < 0 || hh > 23 || mm < 0 || mm > 59) return
    const key = `${lineCode}|${processCode}`
    if (seen.has(key)) return
    seen.add(key)
    normalized.push({ lineCode, processCode, startTime: `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}` })
  })
  return normalized
}
const normalizePlannedStockCalcRules = (rows) => {
  const source = Array.isArray(rows) ? rows : []
  const seen = new Set()
  const normalized = []
  source.forEach((row) => {
    const lineCode = normalizeLineCode(row?.lineCode)
    const processCode = normalizeProcessCode(row?.processCode)
    // 旧形式(item/mode)との互換
    let calcTarget = String(row?.calcTarget || '').trim().toUpperCase()
    let setting = String(row?.setting || '').trim().toUpperCase()
    const oldItem = String(row?.item || '').trim().toUpperCase()
    const oldMode = String(row?.mode || '').trim().toUpperCase()
    if (!calcTarget && oldItem === 'PARENT_SHIPMENT_SOURCE') calcTarget = 'PLANNED_STOCK'
    if (!setting && oldMode === 'PLAN') setting = 'PARENT_PLAN'
    if (!lineCode || !processCode) return
    if (calcTarget !== 'PLANNED_STOCK' && calcTarget !== 'STOCK' && calcTarget !== 'DEMAND') return
    if (setting !== 'PARENT_PLAN' && setting !== 'ACTUAL_OR_PLAN') return
    const key = `${lineCode}|${processCode}|${calcTarget}`
    if (seen.has(key)) return
    seen.add(key)
    normalized.push({
      lineCode,
      processCode,
      calcTarget,
      setting,
      calcTargetLabel: calcTarget === 'STOCK' ? '在庫' : (calcTarget === 'DEMAND' ? '需要' : '計画在庫'),
      settingLabel: setting === 'PARENT_PLAN' ? '後工程計画使用' : '標準（実績優先）',
    })
  })
  return normalized
}
const userUnitLines = computed(() => {
  const unitLines = authState.user?.profile?.unit_lines
  return Array.isArray(unitLines) ? unitLines : []
})
const userAllowedLineIdSet = computed(() => new Set(
  userUnitLines.value
    .map((item) => String(item?.line_id || '').trim())
    .filter(Boolean),
))
const preferredUserLineId = computed(() => {
  const mappings = userUnitLines.value
  if (!mappings.length) return ''
  const defaultMapping = mappings.find((item) => item?.is_default)
  const target = defaultMapping || mappings[0]
  return target?.line_id ? String(target.line_id) : ''
})
const pickPreferredLineId = (candidates) => {
  const candidateList = Array.isArray(candidates) ? candidates : []
  if (!candidateList.length) return ''
  const preferredId = preferredUserLineId.value
  if (preferredId && candidateList.some((line) => String(line.id) === preferredId)) {
    return preferredId
  }
  return String(candidateList[0].id)
}
const createDefaultLineCodesByTab = (lineList = []) => {
  const result = {}
  const allCodes = lineList.map((line) => normalizeLineCode(line?.line_code))
  operationalPlanTabs.forEach((tabKey) => {
    if (tabKey === 'tank') {
      result[tabKey] = normalizeLineCodes(allCodes)
      return
    }
    const keywords = lineKeywordsByTab[tabKey] || []
    result[tabKey] = normalizeLineCodes(
      lineList
        .filter((line) => {
          const code = String(line?.line_code || '').toLowerCase()
          const name = String(line?.line_name || '').toLowerCase()
          return keywords.some((kw) => code.includes(kw) || name.includes(kw))
        })
        .map((line) => line?.line_code),
    )
  })
  return result
}
const lineCodesByTab = ref(createDefaultLineCodesByTab())
const getLineCodesForTab = (tabKey) => normalizeLineCodes(lineCodesByTab.value?.[tabKey])
const isOperationalPlanTab = (tabKey = activePlanTab.value) => operationalPlanTabs.includes(tabKey)
const availableLines = computed(() => {
  if (!isOperationalPlanTab(activePlanTab.value)) return []
  const targetCodes = new Set(getLineCodesForTab(activePlanTab.value))
  if (!targetCodes.size) return []
  const allowedIds = userAllowedLineIdSet.value
  return lines.value.filter((line) => {
    const code = normalizeLineCode(line?.line_code)
    if (!targetCodes.has(code)) return false
    if (!allowedIds.size) return true
    return allowedIds.has(String(line.id))
  })
})
const saveLineCodesByTab = () => {
  try {
    window.localStorage.setItem(PLAN_TARGET_LINES_KEY, JSON.stringify(lineCodesByTab.value))
  } catch (e) {
    console.warn('ライン編集設定保存失敗', e)
  }
}
const loadLineCodesByTab = async () => {
  const defaults = createDefaultLineCodesByTab(lines.value)
  const fromStorage = {}
  try {
    const raw = window.localStorage.getItem(PLAN_TARGET_LINES_KEY)
    if (!raw) {
      operationalPlanTabs.forEach((tabKey) => {
        fromStorage[tabKey] = normalizeLineCodes(defaults[tabKey] || [])
      })
    } else {
      const parsed = JSON.parse(raw)
      operationalPlanTabs.forEach((tabKey) => {
        const source = parsed?.[tabKey]
        const fallback = defaults[tabKey] || []
        fromStorage[tabKey] = normalizeLineCodes(Array.isArray(source) ? source : fallback)
      })
    }
  } catch (_e) {
    operationalPlanTabs.forEach((tabKey) => {
      const fallback = defaults[tabKey] || []
      fromStorage[tabKey] = normalizeLineCodes(fallback)
    })
  }
  lineCodesByTab.value = fromStorage

  try {
    const res = await api.productionRecordSettings.getSettings()
    const dbSettings = res?.data?.target_line_codes_by_tab
    const dbSpecialRules = res?.data?.special_rules
    if (!dbSettings || typeof dbSettings !== 'object' || Array.isArray(dbSettings)) return
    const merged = {}
    operationalPlanTabs.forEach((tabKey) => {
      const hasDbValue = Object.prototype.hasOwnProperty.call(dbSettings, tabKey)
      const fallback = fromStorage[tabKey] || defaults[tabKey] || []
      const source = hasDbValue ? dbSettings[tabKey] : fallback
      merged[tabKey] = normalizeLineCodes(Array.isArray(source) ? source : fallback)
    })
    lineCodesByTab.value = merged
    prevDayShiftRules.value = normalizePrevDayShiftRules(dbSpecialRules?.prev_day_shift_rules)
    ganttStartTimeRules.value = normalizeGanttStartTimeRules(dbSpecialRules?.gantt_start_time_rules)
    plannedStockCalcRules.value = normalizePlannedStockCalcRules(dbSpecialRules?.planned_stock_calc_rules)
    saveLineCodesByTab()
  } catch (e) {
    console.warn('ライン編集設定DB取得失敗', e)
  }
}
const syncLineCodesByTabToServer = async () => {
  const payload = {
    target_line_codes_by_tab: operationalPlanTabs.reduce((acc, tabKey) => {
      acc[tabKey] = getLineCodesForTab(tabKey)
      return acc
    }, {}),
    special_rules: {
      prev_day_shift_rules: normalizePrevDayShiftRules(prevDayShiftRules.value),
      gantt_start_time_rules: normalizeGanttStartTimeRules(ganttStartTimeRules.value),
      planned_stock_calc_rules: normalizePlannedStockCalcRules(plannedStockCalcRules.value),
    },
  }
  const res = await api.productionRecordSettings.saveSettings(payload)
  const dbSettings = res?.data?.target_line_codes_by_tab
  const dbSpecialRules = res?.data?.special_rules
  if (!dbSettings || typeof dbSettings !== 'object' || Array.isArray(dbSettings)) return
  const normalized = {}
  operationalPlanTabs.forEach((tabKey) => {
    const source = dbSettings?.[tabKey]
    const fallback = getLineCodesForTab(tabKey)
    normalized[tabKey] = normalizeLineCodes(Array.isArray(source) ? source : fallback)
  })
  lineCodesByTab.value = normalized
  prevDayShiftRules.value = normalizePrevDayShiftRules(dbSpecialRules?.prev_day_shift_rules)
  ganttStartTimeRules.value = normalizeGanttStartTimeRules(dbSpecialRules?.gantt_start_time_rules)
  plannedStockCalcRules.value = normalizePlannedStockCalcRules(dbSpecialRules?.planned_stock_calc_rules)
  saveLineCodesByTab()
}
const addPrevDayShiftRule = async () => {
  const rule = {
    lineCode: normalizeLineCode(prevDayShiftDraft.value.lineCode),
    processCode: normalizeProcessCode(prevDayShiftDraft.value.processCode),
    shiftQty: Number(prevDayShiftDraft.value.shiftQty),
  }
  const normalized = normalizePrevDayShiftRules([rule])
  if (!normalized.length) {
    alert('ライン・工程・台数を正しく入力してください。')
    return
  }
  const merged = normalizePrevDayShiftRules([...prevDayShiftRules.value, ...normalized])
  prevDayShiftRules.value = merged
  lineSettingsMessage.value = ''
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('前日シフト台数設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? '前日シフト台数設定を追加しました。（DB同期は失敗しました）'
    : '前日シフト台数設定を追加しました。'
}
const removePrevDayShiftRule = async (index) => {
  prevDayShiftRules.value = prevDayShiftRules.value.filter((_, i) => i !== index)
  lineSettingsMessage.value = ''
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('前日シフト台数設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? '前日シフト台数設定を削除しました。（DB同期は失敗しました）'
    : '前日シフト台数設定を削除しました。'
}
const addGanttStartTimeRule = async () => {
  const rule = {
    lineCode: normalizeLineCode(ganttStartTimeDraft.value.lineCode),
    processCode: normalizeProcessCode(ganttStartTimeDraft.value.processCode),
    startTime: String(ganttStartTimeDraft.value.startTime || '').trim(),
  }
  const normalized = normalizeGanttStartTimeRules([rule])
  if (!normalized.length) {
    alert('ライン・工程・開始時刻を正しく入力してください。')
    return
  }
  ganttStartTimeRules.value = normalizeGanttStartTimeRules([...ganttStartTimeRules.value, ...normalized])
  lineSettingsMessage.value = ''
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('ガント開始時刻設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? 'ガント開始時刻設定を追加しました。（DB同期は失敗しました）'
    : 'ガント開始時刻設定を追加しました。'
}
const removeGanttStartTimeRule = async (index) => {
  ganttStartTimeRules.value = ganttStartTimeRules.value.filter((_, i) => i !== index)
  lineSettingsMessage.value = ''
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('ガント開始時刻設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? 'ガント開始時刻設定を削除しました。（DB同期は失敗しました）'
    : 'ガント開始時刻設定を削除しました。'
}
const addPlannedStockCalcRule = async () => {
  const rule = {
    lineCode: normalizeLineCode(plannedStockCalcDraft.value.lineCode),
    processCode: normalizeProcessCode(plannedStockCalcDraft.value.processCode),
    calcTarget: String(plannedStockCalcDraft.value.calcTarget || '').trim().toUpperCase(),
    setting: String(plannedStockCalcDraft.value.setting || '').trim().toUpperCase(),
  }
  const normalized = normalizePlannedStockCalcRules([rule])
  if (!normalized.length) {
    alert('ライン・工程・項目を正しく入力してください。')
    return
  }
  plannedStockCalcRules.value = normalizePlannedStockCalcRules([...plannedStockCalcRules.value, ...normalized])
  lineSettingsMessage.value = ''
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('計算特例設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? '計算特例設定を追加しました。（DB同期は失敗しました）'
    : '計算特例設定を追加しました。'
}
const removePlannedStockCalcRule = async (index) => {
  plannedStockCalcRules.value = plannedStockCalcRules.value.filter((_, i) => i !== index)
  lineSettingsMessage.value = ''
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('計算特例設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? '計算特例設定を削除しました。（DB同期は失敗しました）'
    : '計算特例設定を削除しました。'
}
const isLineSelectedForTargetTab = (lineCode) => {
  const code = normalizeLineCode(lineCode)
  return getLineCodesForTab(settingsTargetTab.value).includes(code)
}
const toggleLineForTargetTab = (lineCode) => {
  const code = normalizeLineCode(lineCode)
  if (!code) return
  const tabKey = settingsTargetTab.value
  const current = new Set(getLineCodesForTab(tabKey))
  if (current.has(code)) current.delete(code)
  else current.add(code)
  lineCodesByTab.value = {
    ...lineCodesByTab.value,
    [tabKey]: Array.from(current),
  }
  lineSettingsMessage.value = ''
}
const saveLineSettings = async () => {
  saveLineCodesByTab()
  let dbSyncFailed = false
  try {
    await syncLineCodesByTabToServer()
  } catch (e) {
    dbSyncFailed = true
    console.warn('ライン編集設定DB保存失敗', e)
  }
  lineSettingsMessage.value = dbSyncFailed
    ? '対象ラインを保存しました。（DB同期は失敗しました）'
    : '対象ラインを保存しました。'
  if (!isOperationalPlanTab(activePlanTab.value)) return
  const availableIds = new Set(availableLines.value.map((line) => String(line.id)))
  if (!selectedLine.value || !availableIds.has(String(selectedLine.value))) {
    selectedLine.value = pickPreferredLineId(availableLines.value)
  }
  await loadData()
}
const ensureSelectedLineForActiveTab = async (shouldReload = true) => {
  if (!isOperationalPlanTab(activePlanTab.value)) return
  const candidates = availableLines.value
  const lineIds = new Set(candidates.map((line) => String(line.id)))
  if (selectedLine.value && lineIds.has(String(selectedLine.value))) return
  selectedLine.value = pickPreferredLineId(candidates)
  if (shouldReload) await loadData()
}
const shouldLimitToCoproductParentAndDriver = computed(() => {
  const code = String(selectedLineObj.value?.line_code || '').trim().toUpperCase()
  return COPRODUCT_LIMITED_LINE_CODES.has(code)
})
const showExportDialog = ref(false)
const PRINT_CHUNK_DAYS = 14

const formatDateKey = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const buildLocalDate = (dateText) => {
  if (!dateText) return new Date()
  const [y, m, d] = dateText.split('-').map((v) => Number(v))
  if (!y || !m || !d) return new Date()
  return new Date(y, m - 1, d)
}

const lockUntilDate = computed(() => {
  const base = new Date()
  base.setHours(0, 0, 0, 0)
  base.setDate(base.getDate() + Number(lockDays.value || 0))
  return base
})

const isPlanCellLocked = (dateKey) => {
  if (!dateKey) return false
  const target = buildLocalDate(dateKey)
  return target <= lockUntilDate.value && !isEditUnlocked.value
}

const isNonWorkingCalendarDay = (day) => {
  if (!day) return false
  const isWorking = day.is_working_day
  if (isWorking === false) return true
  if (typeof isWorking === 'string' && isWorking.toLowerCase() === 'false') return true
  return false
}

const isHolidayDate = (dateKey) => {
  if (!dateKey) return false
  const day = calendarDayMap.value[dateKey]
  if (day) {
    return isNonWorkingCalendarDay(day)
  }
  const target = buildLocalDate(dateKey)
  const weekday = target.getDay()
  return weekday === 0 || weekday === 6
}

const endDate = computed(() => {
  const d = buildLocalDate(startDate.value)
  d.setDate(d.getDate() + horizonDays.value - 1)
  return formatDateKey(d)
})

const dateColumns = computed(() => {
  const cols = []
  const base = buildLocalDate(startDate.value)
  const weekday = ['日', '月', '火', '水', '木', '金', '土']
  for (let i = 0; i < horizonDays.value; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i)
    const day = d.getDay()
    const label = `${d.getMonth() + 1}/${d.getDate()}(${weekday[day]})`
    const key = formatDateKey(d)
    let dayClass = day === 0 ? 'sun' : day === 6 ? 'sat' : day === 5 ? 'fri' : ''
    // カレンダ上の休日（祝日・GW等）も日曜と同じスタイルにする
    if (!dayClass && isHolidayDate(key)) {
      dayClass = 'sun'
    }
    cols.push({ key, label, dayClass })
  }
  return cols
})

const visibleDateColumns = computed(() => {
  if (!hideWeekends.value) return dateColumns.value
  const filtered = dateColumns.value.filter(c => c.dayClass !== 'sat' && c.dayClass !== 'sun')
  return filtered.map((c, i) => ({
    ...c,
    weekGap: hideWeekends.value && c.dayClass === 'fri' && i < filtered.length - 1
  }))
})

const DAY_COL_WIDTH = 40
const SEQUENCE_COL_WIDTH = 25

// テーブルの最小幅を計算して、縮みすぎを防ぐ
const tableMinWidth = computed(() => {
  const fixedColsWidth = 30 + 135 + 100 // No + 品番 + 品名
  const perDayWidth = (DAY_COL_WIDTH * 5) + SEQUENCE_COL_WIDTH
  const gapCount = visibleDateColumns.value.filter(c => c.weekGap).length
  return fixedColsWidth + visibleDateColumns.value.length * perDayWidth + gapCount * 6
})

const loadTableMinWidth = computed(() => {
  const fixedColsWidth = 180
  const perDayWidth = 80
  return fixedColsWidth + visibleDateColumns.value.length * perDayWidth
})

const initDaily = () => {
  const daily = {}
  dateColumns.value.forEach((c) => {
    daily[c.key] = {
      demand: 0,
      actual: 0,
      stock: 0,
      plan: '',
      plan_stock: 0,
      plan_base: 0,
      sequence_no: '',
      extraLots: [],
      has_row: false,
      line_demand_qty: 0,
      progress: 0,
      planned_progress: 0,
    }
  })
  return daily
}

const ensureDailyCell = (row, dateKey) => {
  if (!row.daily) row.daily = initDaily()
  if (!row.daily[dateKey]) {
    row.daily[dateKey] = {
      demand: 0,
      actual: 0,
      stock: 0,
      plan: '',
      plan_stock: 0,
      plan_base: 0,
      sequence_no: '',
      extraLots: [],
      has_row: false,
      line_demand_qty: 0,
      progress: 0,
      planned_progress: 0,
    }
  }
  if (!row.daily[dateKey].extraLots) {
    row.daily[dateKey].extraLots = []
  }
  return row.daily[dateKey]
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
  activeInputRowId.value = null
  cursorProductTail.value = ''
  cursorProductBubbleStyle.value = {}
}

const goBack = () => {
  router.back()
}

const goForward = () => {
  router.forward()
}

const normalizeExcelDate = (value) => {
  if (!value) return ''
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const y = value.getFullYear()
    const m = String(value.getMonth() + 1).padStart(2, '0')
    const d = String(value.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  const s = String(value).trim()
  if (!s) return ''
  const matched = s.match(/^(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})/)
  if (!matched) return ''
  return `${matched[1]}-${String(matched[2]).padStart(2, '0')}-${String(matched[3]).padStart(2, '0')}`
}

const parseSpotExcelFile = async (file) => {
  const buffer = await file.arrayBuffer()
  const wb = XLSX.read(buffer, { type: 'array', cellDates: true })
  const sheetName = wb.SheetNames.includes('forup') ? 'forup' : wb.SheetNames[0]
  if (!sheetName) return []
  const ws = wb.Sheets[sheetName]
  return XLSX.utils.sheet_to_json(ws, {
    defval: '',
    raw: false,
    blankrows: false,
  })
}

const onSpotExcelFileChange = async (event) => {
  const file = event?.target?.files?.[0]
  spotExcelRows.value = []
  spotExcelFileName.value = ''
  spotExcelMessage.value = ''
  spotExcelMissingProducts.value = []
  spotExcelMissingProcesses.value = []
  if (!file) return
  spotExcelLoading.value = true
  try {
    const parsedRows = await parseSpotExcelFile(file)
    const normalized = parsedRows
      .map((row, idx) => ({
        row_no: idx + 2,
        product_code: String(row?.部番 || '').trim(),
        plan_date: normalizeExcelDate(row?.計画日),
        plan_qty:
          row?.計画数 === '' || row?.計画数 === null || row?.計画数 === undefined
            ? NaN
            : Number(row?.計画数),
      }))
      .filter((row) => row.product_code && row.plan_date && Number.isFinite(row.plan_qty) && row.plan_qty > 0)

    spotExcelRows.value = normalized
    spotExcelFileName.value = file.name
    spotExcelMessage.value = `${normalized.length}件を読込しました。`
  } catch (e) {
    console.error('スポットExcel読込エラー', e)
    spotExcelMessage.value = 'Excel読込に失敗しました。forupシートを確認してください。'
  } finally {
    spotExcelLoading.value = false
    if (event?.target) event.target.value = ''
  }
}

const saveSpotExcelPlan = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  if (!spotExcelRows.value.length) {
    alert('取込対象がありません。')
    return
  }

  const productByCode = new Map(
    (Array.isArray(products.value) ? products.value : []).map((p) => [String(p.product_code || '').trim(), p]),
  )
  const resolveProcess4013 = async () => {
    if (spotExcelProcess4013Id.value) return spotExcelProcess4013Id.value
    const res = await api.processes.getProcesses({ page_size: 5000 })
    const processList = res?.data?.results || res?.data || []
    const process4013 = (Array.isArray(processList) ? processList : []).find(
      (p) => String(p?.process_code || '').trim() === '4013',
    )
    if (!process4013?.id) return null
    spotExcelProcess4013Id.value = process4013.id
    return process4013.id
  }

  const fixedProcessId = await resolveProcess4013()
  if (!fixedProcessId) {
    alert('工程コード4013が見つかりません。工程マスタを確認してください。')
    return
  }

  const items = []
  const missingProducts = []
  const missingProcesses = []

  spotExcelRows.value.forEach((row) => {
    const prod = productByCode.get(row.product_code)
    if (!prod) {
      missingProducts.push({ row_no: row.row_no, product_code: row.product_code })
      return
    }
    items.push({
      product_id: prod.id,
      process_id: fixedProcessId,
      plan_date: row.plan_date,
      plan_qty: Number(row.plan_qty),
      sequence_no: 1,
    })
  })

  if (!items.length) {
    alert('保存対象がありません。品番マスタまたは工程設定を確認してください。')
    return
  }

  processing.value = true
  try {
    spotExcelMissingProducts.value = missingProducts
    spotExcelMissingProcesses.value = missingProcesses
    const res = await api.linePlans.save({
      line_id: selectedLine.value,
      items,
    })
    spotExcelMessage.value = `保存完了: 作成${res.data?.created ?? 0}件 / 更新${res.data?.updated ?? 0}件`
    if (missingProducts.length > 0 || missingProcesses.length > 0) {
      spotExcelMessage.value += `（未登録品番:${missingProducts.length}件, 工程未設定:${missingProcesses.length}件）`
    }
    await loadData()
  } catch (e) {
    console.error('スポットExcel保存エラー', e)
    alert('Excel取込保存に失敗しました。')
  } finally {
    processing.value = false
  }
}

const savePlan = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  if (isEditUnlocked.value && !changeReason.value) {
    alert('変更理由を入力してください。')
    return
  }
  const floorShippingValidationError = validateFloorShippingLots()
  if (floorShippingValidationError) {
    alert(floorShippingValidationError)
    return
  }

  // 日別設定を先に保存
  try {
    await saveDailySettings()
  } catch (e) {
    console.error('日別設定の保存に失敗しました', e)
    // 日別設定の保存失敗は警告のみで続行
  }

  const items = []
  console.log('保存対象の行数:', rows.value.length)
  rows.value.forEach((r, rowIdx) => {
    console.log('保存チェック:', { product_id: r.product_id, process_id: r.process_id, product_code: r.product_code })
    if (!r.product_id || !r.process_id) {
      console.warn('スキップ: product_idまたはprocess_idがありません', r)
      return
    }
    dateColumns.value.forEach((c) => {
      const daily = ensureDailyCell(r, c.key)
      const mainPlanQty = daily.plan === '' || daily.plan === null || daily.plan === undefined ? null : Number(daily.plan)
      const mainSeqNo = daily.sequence_no === '' || daily.sequence_no === null || daily.sequence_no === undefined ? null : Number(daily.sequence_no)
      const lots = []
      if (!(mainPlanQty === null && mainSeqNo === null)) {
        lots.push({ plan_qty: mainPlanQty, sequence_no: mainSeqNo })
      }
      const extraLots = Array.isArray(daily.extraLots) ? daily.extraLots : []
      extraLots.forEach((lot) => {
        const lotPlanQty = lot.plan_qty === '' || lot.plan_qty === null || lot.plan_qty === undefined ? null : Number(lot.plan_qty)
        const lotSeqNo = lot.sequence_no === '' || lot.sequence_no === null || lot.sequence_no === undefined ? null : Number(lot.sequence_no)
        if (lotPlanQty === null && lotSeqNo === null) return
        lots.push({ plan_qty: lotPlanQty, sequence_no: lotSeqNo })
      })
      lots.forEach((lot) => {
        items.push({
          product_id: r.product_id,
          process_id: r.process_id,
          plan_date: c.key,
          plan_qty: lot.plan_qty === null ? 0 : lot.plan_qty,
          sequence_no: lot.sequence_no,
          display_order: rowIdx,
        })
      })
    })
  })
  console.log('保存アイテム数:', items.length)
  if (items.length > 0) {
    console.log('サンプルアイテム:', items[0])
  }
  if (!items.length) {
    alert('保存するデータがありません。product_idとprocess_idを確認してください。')
    return
  }
  processing.value = true
  try {
    const payload = {
      line_id: selectedLine.value,
      items,
    }
    if (isEditUnlocked.value && changeReason.value) {
      payload.change_reason = changeReason.value
    }
    const res = await api.linePlans.save(payload)
    console.info('保存結果', res.data)
    try {
      await api.lineBacklogs.expandProcesses({
        line_id: selectedLine.value,
        start_date: startDate.value,
        end_date: endDate.value,
        read_only: false,
        include_coproduct_children: true,
        use_coproduct: activePlanTab.value !== 'floor',
      })
      await api.lineBacklogs.recalculateInventory({
        line_id: selectedLine.value,
        start_date: startDate.value,
        end_date: endDate.value,
        include_progress: isProgressMode.value,
        line_final_only: true,
      })
      await withTimeout(
        api.lineGanttPlans.generate({
          line_id: selectedLine.value,
          start_date: startDate.value,
          end_date: endDate.value,
          clear_existing: true,
          final_process_start_time: finalProcessStartTime.value,
          adjust_to_break_end: adjustToBreakEnd.value,
        }),
        GANTT_GENERATE_TIMEOUT_MS,
        `工程ガント生成が ${Math.floor(GANTT_GENERATE_TIMEOUT_MS / 1000)}秒を超えたため中断しました。`,
      )
      // 工程ガントを再読み込み
      ganttReloadKey.value += 1
      if (showProcessLoad.value) {
        await loadProcessLoad()
      }
    } catch (expandError) {
      console.error('工程展開/ガント再計算エラー', expandError)
      let msg = '工程展開/ガント再計算に失敗しました。'
      if (expandError.response && expandError.response.data) {
        // DRFのValidationErrorなどは配列やオブジェクトで返ることがあるため文字列化
        msg += '\n' + (Array.isArray(expandError.response.data) ? expandError.response.data.join('\n') : JSON.stringify(expandError.response.data, null, 2))
      } else if (expandError?.message) {
        msg += `\n${expandError.message}`
      }
      alert(`保存は完了しましたが、エラーが発生しました。\n${msg}`)
      return
    }
    alert(`保存しました。\n作成: ${res.data.created}件, 更新: ${res.data.updated}件`)
    isEditUnlocked.value = false
    changeReason.value = ''
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました。')
  } finally {
    processing.value = false
  }
}

const getDailyTotalPlanQty = (daily) => {
  if (!daily) return 0
  let total = 0
  const main = Number(daily.plan)
  if (Number.isFinite(main) && main > 0) total += main
  const lots = Array.isArray(daily.extraLots) ? daily.extraLots : []
  lots.forEach((lot) => {
    const qty = Number(lot?.plan_qty)
    if (Number.isFinite(qty) && qty > 0) total += qty
  })
  return Math.floor(total)
}

const getDayPlanTotal = (dateKey) => {
  let total = 0
  rows.value.forEach((row) => {
    const daily = row.daily?.[dateKey]
    if (daily) total += getDailyTotalPlanQty(daily)
  })
  return total || ''
}

const DEMAND_EXCLUDE_CODES = ['YD40002683']

const getDayDemandTotal = (dateKey) => {
  let total = 0
  rows.value.forEach((row) => {
    const code = row.product_code || getProductCode(row.product_id)
    if (DEMAND_EXCLUDE_CODES.includes(code)) return
    const daily = row.daily?.[dateKey]
    if (!daily) return
    const val = Number(isProgressMode.value ? daily.line_demand_qty : daily.demand)
    if (Number.isFinite(val) && val > 0) total += val
  })
  return total
}

const getDayDemandMovingAvg = (dateKey, days = 5) => {
  const cols = dateColumns.value
  const idx = cols.findIndex((c) => c.key === dateKey)
  if (idx < 0) return ''
  let sum = 0
  let count = 0
  for (let i = idx; i < cols.length && count < days; i++) {
    if (isHolidayDate(cols[i].key)) continue
    sum += getDayDemandTotal(cols[i].key)
    count++
  }
  if (!count) return ''
  return Math.round(sum / count)
}

const createIntegratedChecksheetForDay = async (dateKey) => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  if (!dateKey) return
  const ok = window.confirm('チェックシート作成しますか？')
  if (!ok) return

  const targets = rows.value
    .map((row) => {
      const daily = ensureDailyCell(row, dateKey)
      const qty = getDailyTotalPlanQty(daily)
      return {
        product_id: row.product_id,
        quantity: qty,
      }
    })
    .filter((x) => x.product_id && x.quantity > 0)

  if (!targets.length) {
    alert('この日の計画数量がありません。')
    return
  }

  processing.value = true
  try {
    let created = 0
    const errors = []
    for (const target of targets) {
      try {
        await api.integratedChecksheets.prepareBatch({
          product: target.product_id,
          line: selectedLine.value,
          quantity: target.quantity,
          plan_date: dateKey,
          lot_no: '',
        })
        created += 1
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || '作成失敗'
        errors.push(`${target.product_id}: ${msg}`)
      }
    }
    if (errors.length) {
      alert(`チェックシート作成: ${created}件成功 / ${errors.length}件失敗\n${errors.join('\n')}`)
    } else {
      alert(`チェックシートを ${created} 件作成しました。`)
    }
  } finally {
    processing.value = false
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

const ROW_COLOR_MAP = {
  'YD40008720K': { bg: '#bfdbfe', color: '#000' },                                        // 1: キャブ U-5
  'YD40008750K': { bg: '#bbf7d0', color: '#000' },                                        // 2: キャノピー U-5
  'YD40008670K': { bg: '#bfdbfe', color: '#000' },                                        // 3: キャブ 55UR
  'YD40008650K': { bg: '#bbf7d0', color: '#000' },                                        // 4: キャノピー 55UR
  'YD40008730K': { bg: '#bfdbfe', color: '#000', planBg: '#d4a574', planColor: '#fff' },   // A: キャブ 5t-EN
  'YD40008760K': { bg: '#bfdbfe', color: '#000', planBg: '#bbb', planColor: '#000' },      // B: キャブ 3t-EN
  'YD40008780K': { bg: '#bfdbfe', color: '#000', planBg: '#444', planColor: '#fff' },      // C: キャブ U-5NA
  'YD40008790K': { bg: '#bbf7d0', color: '#000', planBg: '#fbbf24', planColor: '#000' },   // D: キャノピー U-5NA
  'YD40008770K': { bg: '#bfdbfe', color: '#000' },                                        // E: 未定
  'YD40008800K': { bg: '#bfdbfe', color: '#000' },                                        // F: 未定
}
const getProductColorFromCache = (code) => {
  const line = selectedLineObj.value
  if (!line) return null
  const ctx = getDisplayOrderContext()
  const cacheKey = `${line.id}__${ctx}`
  const colorMap = productColorCache.value.get(cacheKey)
  return colorMap?.get(code) || null
}
const getRowColorStyle = (row) => {
  const code = row.product_code || getProductCode(row.product_id)
  const db = getProductColorFromCache(code)
  if (db?.bg) return { backgroundColor: db.bg, color: db.color || '#000' }
  const c = ROW_COLOR_MAP[code]
  if (!c) return null
  return { backgroundColor: c.bg, color: c.color }
}
const getPlanCellStyle = (row) => {
  const code = row.product_code || getProductCode(row.product_id)
  const db = getProductColorFromCache(code)
  if (db?.planBg) return { backgroundColor: db.planBg, color: db.planColor || '#000' }
  const c = ROW_COLOR_MAP[code]
  if (!c?.planBg) return null
  return { backgroundColor: c.planBg, color: c.planColor || '#000' }
}
const getProductCodeTail5 = (row) => {
  const code = String(row?.product_code || getProductCode(row?.product_id) || '')
  if (!code) return ''
  const digitsOnly = (code.match(/\d/g) || []).join('')
  if (digitsOnly.length >= 5) return digitsOnly.slice(-5)
  return code.slice(-5)
}
const setActiveInputRow = (row, event) => {
  activeInputRowId.value = row?.id ?? null
  cursorProductTail.value = getProductCodeTail5(row)
  const rect = event?.target?.getBoundingClientRect?.()
  if (rect) {
    const left = Math.round(rect.left + (rect.width / 2))
    const top = Math.round(rect.top - 8)
    cursorProductBubbleStyle.value = {
      left: `${left}px`,
      top: `${top}px`,
      transform: 'translate(-50%, -100%)',
    }
  }
}
const onCellBlur = () => {
  window.setTimeout(() => {
    const root = gridWrapperRef.value
    const active = document.activeElement
    if (!root || !active || !root.contains(active)) {
      activeInputRowId.value = null
      cursorProductTail.value = ''
      cursorProductBubbleStyle.value = {}
    }
  }, 0)
}
const getRowProductCode = (row) => row.product_code || getProductCode(row.product_id) || ''
const normalizeProductCode = (code) =>
  String(code || '')
    .trim()
    .toUpperCase()
    .replace(/[０-９]/g, (s) => String.fromCharCode(s.charCodeAt(0) - 0xFEE0))
const normalizeFloorOrderCode = (code) =>
  normalizeProductCode(code).replace(/[A-Z]$/, '')
const getFloorShippingOrder = () => (
  isFloorShippingDeliveryLine.value
    ? FLOOR_SHIPPING_PRODUCT_ORDER.map((code) => `${code}T`)
    : FLOOR_SHIPPING_PRODUCT_ORDER
)

const sortRowsForLine = (inputRows) => {
  const line = selectedLineObj.value
  const ctx = getDisplayOrderContext()
  const cacheKey = line ? `${line.id}__${ctx}` : ''

  if (cacheKey && productOrderCache.value.has(cacheKey)) {
    const orderList = productOrderCache.value.get(cacheKey)
    const orderMap = new Map(orderList.map((code, idx) => [code, idx]))
    const fallback = orderList.length + 1
    return [...inputRows].sort((a, b) => {
      const codeA = getRowProductCode(a)
      const codeB = getRowProductCode(b)
      const priA = orderMap.has(codeA) ? orderMap.get(codeA) : fallback
      const priB = orderMap.has(codeB) ? orderMap.get(codeB) : fallback
      if (priA !== priB) return priA - priB
      return codeA.localeCompare(codeB)
    })
  }

  // フォールバック: ハードコード配列
  if (activePlanTab.value === 'floor-shipping') {
    const orderList = getFloorShippingOrder()
    const orderMap = new Map(orderList.map((code, idx) => [code, idx]))
    const fallback = orderList.length + 1
    return [...inputRows].sort((a, b) => {
      const codeA = normalizeProductCode(getRowProductCode(a))
      const codeB = normalizeProductCode(getRowProductCode(b))
      const priA = orderMap.has(codeA) ? orderMap.get(codeA) : fallback
      const priB = orderMap.has(codeB) ? orderMap.get(codeB) : fallback
      if (priA !== priB) return priA - priB
      return codeA.localeCompare(codeB)
    })
  }
  if (line && line.line_code === FLOOR_LINE_CODE) {
    const orderList = FLOOR_L2100_PRODUCT_ORDER
    const orderMap = new Map(orderList.map((code, idx) => [code, idx]))
    const fallback = orderList.length + 1
    return [...inputRows].sort((a, b) => {
      const codeA = normalizeFloorOrderCode(getRowProductCode(a))
      const codeB = normalizeFloorOrderCode(getRowProductCode(b))
      const priA = orderMap.has(codeA) ? orderMap.get(codeA) : fallback
      const priB = orderMap.has(codeB) ? orderMap.get(codeB) : fallback
      if (priA !== priB) return priA - priB
      return codeA.localeCompare(codeB)
    })
  }
  if (!line || line.line_code !== TANK_LINE_CODE) return inputRows
  const orderMap = new Map(TANK_PRODUCT_ORDER.map((code, idx) => [code, idx]))
  const fallback = TANK_PRODUCT_ORDER.length + 1
  return [...inputRows].sort((a, b) => {
    const codeA = getRowProductCode(a)
    const codeB = getRowProductCode(b)
    const priA = orderMap.has(codeA) ? orderMap.get(codeA) : fallback
    const priB = orderMap.has(codeB) ? orderMap.get(codeB) : fallback
    if (priA !== priB) return priA - priB
    return codeA.localeCompare(codeB)
  })
}

const isRowEmpty = (row) => {
  if (!row.daily) return true
  for (const key of Object.keys(row.daily)) {
    const d = row.daily[key]
    if (!d) continue
    if (Number(d.stock) || Number(d.actual) || Number(d.demand) || Number(d.plan) || Number(d.plan_stock))
      return false
  }
  return true
}

const filteredRows = computed(() => {
  let result = rows.value
  if (keyword.value) {
    const k = keyword.value.toLowerCase()
    result = result.filter((r) => {
      const txt = `${r.product_code || ''}${r.product_name || ''}${getProductCode(r.product_id)}${getProductName(r.product_id)}`.toLowerCase()
      return txt.includes(k)
    })
  }
  if (hideEmptyRows.value) {
    result = result.filter((r) => !isRowEmpty(r))
  }
  return result
})

const displayValue = (val) => {
  if (val === null || val === undefined || val === '') return ''
  const num = Number(val)
  if (!Number.isNaN(num) && num === 0) return ''
  return val
}

const toNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const isNegativeValue = (value) => {
  const num = Number(value)
  return Number.isFinite(num) && num < 0
}

const getPlanQtyTotal = (daily) => {
  if (!daily) return 0
  const main = toNumber(daily.plan)
  const extras = Array.isArray(daily.extraLots)
    ? daily.extraLots.reduce((sum, lot) => sum + toNumber(lot.plan_qty), 0)
    : 0
  return main + extras
}

const getPlanDelta = (daily) => getPlanQtyTotal(daily) - toNumber(daily?.plan_base)

const resolveColIdx = (colIdxOrDateKey) => {
  if (typeof colIdxOrDateKey === 'number') return colIdxOrDateKey
  if (typeof colIdxOrDateKey === 'string') {
    return dateColumns.value.findIndex((c) => c.key === colIdxOrDateKey)
  }
  return -1
}

const getPlanStockDisplay = (row, colIdxOrDateKey) => {
  if (!row || !row.daily) return ''
  const colIdx = resolveColIdx(colIdxOrDateKey)
  if (colIdx < 0) return ''
  const cols = dateColumns.value
  let carry = null
  let delta = 0
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    const raw = daily.plan_stock
    const hasRow = daily.has_row === true
    let value = raw
    if (hasRow) {
      carry = raw
    } else if (carry !== null && carry !== undefined) {
      value = carry
    }
    delta += getPlanDelta(daily)
    if (i === colIdx) {
      const baseValue = value === null || value === undefined ? 0 : Number(value)
      return baseValue + delta
    }
  }
  return ''
}

const getPlannedProgressDisplay = (row, colIdxOrDateKey) => {
  if (!row || !row.daily) return ''
  const colIdx = resolveColIdx(colIdxOrDateKey)
  if (colIdx < 0) return ''
  const cols = dateColumns.value
  let delta = 0
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    delta += getPlanDelta(daily)
    if (i === colIdx) {
      const base = daily.planned_progress
      const baseValue = base === null || base === undefined || base === '' ? 0 : Number(base)
      return baseValue + delta
    }
  }
  return ''
}

const getStockDisplay = (row, colIdxOrDateKey) => {
  if (!row || !row.daily) return ''
  const colIdx = resolveColIdx(colIdxOrDateKey)
  if (colIdx < 0) return ''
  const cols = dateColumns.value
  let carry = null
  for (let i = 0; i <= colIdx; i += 1) {
    const key = cols[i]?.key
    if (!key) continue
    const daily = row.daily[key] || {}
    const raw = daily.stock
    const hasRow = daily.has_row === true
    let value = raw
    if (hasRow) {
      carry = raw
    } else if (carry !== null && carry !== undefined) {
      value = carry
    }
    if (i === colIdx) return value
  }
  return ''
}

const focusCellInput = (rowIdx, colIdx, field) => {
  const root = gridWrapperRef.value
  if (!root) return false
  const selector = `input[data-row="${rowIdx}"][data-col="${colIdx}"][data-field="${field}"]`
  const target = root.querySelector(selector)
  if (!target || target.disabled || target.readOnly) return false
  target.focus()
  if (typeof target.select === 'function') {
    target.select()
  }
  return true
}

const onCellKeydown = (event, rowIdx, colIdx, field) => {
  const key = event.key
  const supportedKeys = ['Enter', 'Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']
  if (!supportedKeys.includes(key)) return

  event.preventDefault()

  const maxRow = filteredRows.value.length - 1
  const maxCol = dateColumns.value.length - 1
  if (maxRow < 0 || maxCol < 0) return

  const fieldOrder = ['plan', 'sequence']
  const moveHorizontal = (row, col, currentField, forward) => {
    const fieldIdx = fieldOrder.indexOf(currentField)
    if (forward) {
      if (fieldIdx < fieldOrder.length - 1) {
        return { row, col, field: fieldOrder[fieldIdx + 1] }
      }
      return { row, col: col + 1, field: fieldOrder[0] }
    }
    if (fieldIdx > 0) {
      return { row, col, field: fieldOrder[fieldIdx - 1] }
    }
    return { row, col: col - 1, field: fieldOrder[fieldOrder.length - 1] }
  }

  let nextRow = rowIdx
  let nextCol = colIdx
  let nextField = field
  let advance
  if (key === 'ArrowUp' || (key === 'Enter' && event.shiftKey)) {
    advance = () => ({ row: nextRow - 1, col: nextCol, field: nextField })
  } else if (key === 'ArrowDown' || key === 'Enter') {
    advance = () => ({ row: nextRow + 1, col: nextCol, field: nextField })
  } else if (key === 'ArrowLeft' || (key === 'Tab' && event.shiftKey)) {
    advance = () => moveHorizontal(nextRow, nextCol, nextField, false)
  } else {
    advance = () => moveHorizontal(nextRow, nextCol, nextField, true)
  }

  const first = advance()
  nextRow = first.row
  nextCol = first.col
  nextField = first.field
  const maxAttempts = (maxRow + 1) * (maxCol + 1) * fieldOrder.length
  let attempts = 0

  while (attempts < maxAttempts) {
    if (nextRow < 0 || nextRow > maxRow || nextCol < 0 || nextCol > maxCol) return
    if (focusCellInput(nextRow, nextCol, nextField)) return
    const moved = advance()
    nextRow = moved.row
    nextCol = moved.col
    nextField = moved.field
    attempts += 1
  }
}

const refreshDates = () => {
  // 再初期化は既存データの初期化だけ（簡易対応）
  rows.value.forEach((r) => {
    r.daily = initDaily()
  })
  if (selectedLine.value) {
    loadWorkPatternData(selectedLine.value, startDate.value, endDate.value)
  }
}

const loadData = async () => {
  // 取り込み前は空表示（手動で「取り込み」を押す運用）
  rows.value = []
  activeInputRowId.value = null
  cursorProductTail.value = ''
  cursorProductBubbleStyle.value = {}
  currentLineRoutingFilterMode.value = 'filtered'
  if (selectedLine.value) {
    await fetchLineDefaultSetting(selectedLine.value)
    await loadWorkPatternData(selectedLine.value, startDate.value, endDate.value)
    // 日別設定を読み込み、未設定の日にデフォルト値をセット
    await loadDailySettings()
    applyDefaultToDailySettings()
  } else {
    calendarDayMap.value = {}
    workPatternMap.value = {}
    // ライン未選択時はデフォルト値に戻す
    finalProcessStartTime.value = '08:00'
    adjustToBreakEnd.value = true
  }
}

const toApiRows = (payload) => {
  if (!payload) return []
  if (Array.isArray(payload.results)) return payload.results
  if (Array.isArray(payload)) return payload
  return []
}

const withTimeout = (promise, timeoutMs, timeoutMessage) => {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(timeoutMessage || 'request timeout'))
    }, timeoutMs)
    promise
      .then((value) => {
        clearTimeout(timer)
        resolve(value)
      })
      .catch((error) => {
        clearTimeout(timer)
        reject(error)
      })
  })
}

const fetchCurrentLineProductIdSet = async (lineId) => {
  const numericLineId = Number(lineId)
  if (!Number.isFinite(numericLineId) || numericLineId <= 0) {
    return {
      mode: 'fallback',
      productIdSet: null,
    }
  }

  try {
    const res = await api.products.getLineFinalCandidates(numericLineId)
    const lineRows = toApiRows(res?.data)
    const targetLine = lineRows.find((row) => Number(row?.line_id) === numericLineId)
    const productIdSet = new Set()

    ;(targetLine?.products || []).forEach((product) => {
      const productId = Number(product?.id)
      if (Number.isFinite(productId) && productId > 0) {
        productIdSet.add(String(productId))
      }
    })

    return {
      mode: productIdSet.size === 0 ? 'empty' : 'filtered',
      productIdSet,
    }
  } catch (error) {
    console.warn('ライン現行ルーティング品番取得エラー:', { lineId: numericLineId, error })
    return {
      mode: 'fallback',
      productIdSet: null,
    }
  }
}

const collectCoproductParentCandidates = (rows) => {
  const parentIds = new Set()
  ;(Array.isArray(rows) ? rows : []).forEach((row) => {
    if (!row) return
    const productId = Number(row.product)
    if (!Number.isFinite(productId) || productId <= 0) return
    // L2201では「ライン最終品」も連産親候補として扱う
    const isLineFinalProduct = row.is_line_final_product === true || row.product_is_line_final_product === true
    const isVirtualSet = row.is_virtual_set === true
    const productCode = String(row.product_code || '').trim().toUpperCase()
    if (isLineFinalProduct || isVirtualSet || productCode.startsWith('ST')) {
      parentIds.add(productId)
    }
  })
  return Array.from(parentIds)
}

const fetchCoproductDisplayProductIdSet = async (parentIds) => {
  const parentIdSet = new Set()
  const driverIdSet = new Set()
  const childIdSet = new Set()
  if (!Array.isArray(parentIds) || parentIds.length === 0) {
    return { parentIdSet, driverIdSet, childIdSet }
  }

  const responses = await Promise.all(
    parentIds.map(async (parentId) => {
      const cacheKey = String(parentId)
      if (coproductDisplayCache.has(cacheKey)) {
        return coproductDisplayCache.get(cacheKey)
      }
      try {
        const bomRes = await api.boms.getBOMs({
          parent_product: parentId,
          is_coproduct: true,
          is_active: true,
          page_size: 100,
        })
        const bomRows = toApiRows(bomRes?.data)
        if (!bomRows.length) {
          coproductDisplayCache.set(cacheKey, null)
          return null
        }

        const childIds = new Set()
        const driverIds = new Set()
        for (const bomRow of bomRows) {
          if (!bomRow) continue
          let bomItems = Array.isArray(bomRow.items) ? bomRow.items : []
          // 一覧で明細が返らない環境向けのフォールバック
          if (!bomItems.length && bomRow.id) {
            try {
              const detailRes = await api.boms.getBOM(bomRow.id)
              bomItems = toApiRows(detailRes?.data?.items)
            } catch (detailError) {
              console.warn('連産品BOM明細取得エラー:', { parentId, bomId: bomRow.id, detailError })
            }
          }
          ;(Array.isArray(bomItems) ? bomItems : []).forEach((item) => {
            if (!item) return
            const childId = Number(item.child_product)
            if (!Number.isFinite(childId) || childId <= 0) return
            const childIdStr = String(childId)
            childIds.add(childIdStr)
            if (item.is_coproduct_driver === true) {
              driverIds.add(childIdStr)
            }
          })
        }

        const entry = {
          parentId: String(parentId),
          childIds: Array.from(childIds),
          driverIds: Array.from(driverIds),
        }
        coproductDisplayCache.set(cacheKey, entry)
        return entry
      } catch (error) {
        console.warn('連産品BOM取得エラー:', { parentId, error })
        coproductDisplayCache.set(cacheKey, null)
        return null
      }
    })
  )

  responses.forEach((entry) => {
    if (!entry) return
    parentIdSet.add(entry.parentId)
    ;(entry.driverIds || []).forEach((driverId) => {
      if (!driverId) return
      driverIdSet.add(String(driverId))
    })
    ;(entry.childIds || []).forEach((childId) => {
      if (!childId) return
      childIdSet.add(String(childId))
    })
  })

  return { parentIdSet, driverIdSet, childIdSet }
}

const filterRowsByExcludedProductIds = (rows, excludedIds) => {
  const isCoproductChildDisplayException = (row) => {
    const productCode = String(row?.product_code || '').trim().toUpperCase()
    if (!FLOOR_4001_COPRODUCT_CHILD_DISPLAY_EXCEPTION_CODES.has(productCode)) return false

    const processCode = String(
      row?.process_code || row?.processCode || row?.resolved_process_code || ''
    ).trim()
    if (processCode === '4001') return true

    const processId = Number(row?.process ?? row?.process_id)
    return Number.isFinite(processId) && processId === 4001
  }

  return (Array.isArray(rows) ? rows : []).filter((row) => {
    const productId = row?.product
    if (productId === null || productId === undefined || productId === '') return false
    if (excludedIds.has(String(productId)) && isCoproductChildDisplayException(row)) return true
    return !excludedIds.has(String(productId))
  })
}

const filterPlanRowsForCoproductDisplay = async (backlogRows, planRows) => {
  const candidates = collectCoproductParentCandidates([...(backlogRows || []), ...(planRows || [])])
  const { parentIdSet, driverIdSet, childIdSet } = await fetchCoproductDisplayProductIdSet(candidates)
  const excludedIds = new Set()
  childIdSet.forEach((childId) => {
    if (!childId) return
    const childKey = String(childId)
    if (driverIdSet.has(childKey)) return
    excludedIds.add(childKey)
  })
  parentIdSet.forEach((parentId) => {
    if (!parentId) return
    excludedIds.delete(String(parentId))
  })
  return {
    backlogRows: filterRowsByExcludedProductIds(backlogRows, excludedIds),
    planRows: filterRowsByExcludedProductIds(planRows, excludedIds),
  }
}

const ensureL2201LineFinalRows = (grouped, productInfoByProdKey) => {
  if (!shouldLimitToCoproductParentAndDriver.value) return
  const lineId = Number(selectedLine.value)
  if (!Number.isFinite(lineId) || lineId <= 0) return

  ;(Array.isArray(products.value) ? products.value : []).forEach((prod) => {
    if (!prod || prod.is_line_final_product !== true) return
    if (Number(prod.line) !== lineId) return
    const pid = Number(prod.id)
    if (!Number.isFinite(pid) || pid <= 0) return
    const prodKey = String(pid)

    if (!productInfoByProdKey.has(prodKey)) {
      productInfoByProdKey.set(prodKey, {
        product_id: pid,
        product_code: String(prod.product_code || ''),
        product_name: String(prod.product_name || ''),
        process_id: prod.process || '',
      })
    }
    if (!grouped.has(prodKey)) {
      grouped.set(prodKey, {
        id: `pl-${prodKey}`,
        product_id: pid,
        product_code: String(prod.product_code || ''),
        product_name: String(prod.product_name || ''),
        process_id: prod.process || '',
        daily: initDaily(),
      })
    }
  })
}

// その日の全行のsequence_noの最大値+1を返す
const getNextSequenceForDate = (dateKey) => {
  let max = 0
  rows.value.forEach((row) => {
    const daily = row.daily?.[dateKey]
    if (!daily) return
    const seq = parseInt(daily.sequence_no)
    if (!isNaN(seq) && seq > max) max = seq
    if (daily.extraLots) {
      daily.extraLots.forEach((lot) => {
        const lotSeq = parseInt(lot.sequence_no)
        if (!isNaN(lotSeq) && lotSeq > max) max = lotSeq
      })
    }
  })
  return max + 1
}

// 日付ヘッダーの×ボタン: その日の計画(LinePlan/LineGanttPlan/LineBacklog)をクリア
const clearDayPlan = async (dateKey) => {
  if (!selectedLine.value) return
  if (!confirm(`${dateKey} の計画をクリアします。よろしいですか？`)) return
  processing.value = true
  try {
    await api.linePlans.bulkDelete({
      line_id: selectedLine.value,
      start_date: dateKey,
      end_date: dateKey,
    })
    // フロントエンドのデータもクリア（計画・順のみ。需要・実績・在庫は維持）
    rows.value.forEach((row) => {
      const daily = row.daily?.[dateKey]
      if (!daily) return
      daily.plan = ''
      daily.sequence_no = ''
      daily.extraLots = []
      daily.plan_stock = 0
    })
  } catch (e) {
    console.error('計画クリアエラー', e)
    alert('クリアに失敗しました。')
  } finally {
    processing.value = false
  }
}

const onPlanInput = (row, dateKey, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.plan = value === '' ? '' : value
  // 数量 > 0 かつ順が未設定の場合、入力順で自動採番
  const numVal = parseFloat(value)
  if (!isNaN(numVal) && numVal > 0) {
    const seq = daily.sequence_no
    if (seq === '' || seq === null || seq === undefined) {
      daily.sequence_no = getNextSequenceForDate(dateKey)
    }
  } else {
    // 数量クリア時は順もクリア
    daily.sequence_no = ''
  }
}

const onActualInput = (row, dateKey, value) => {
  const daily = ensureDailyCell(row, dateKey)
  daily.actual = value === '' ? '' : value
}

const onSequenceInput = (row, dateKey, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.sequence_no = value === '' ? '' : value
}

const addExtraLot = (row, dateKey) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  if (isFloorShippingDeliveryLine.value && Array.isArray(daily.extraLots) && daily.extraLots.length >= 1) {
    alert('フロア配送は同一日・同一品番で2件までです。')
    return
  }
  if (isFloorShippingDeliveryLine.value) {
    const mainPlanQty = Number(daily.plan)
    if (!Number.isFinite(mainPlanQty) || mainPlanQty <= 0) {
      alert('フロア配送は先に1件目を入力してください。')
      return
    }
    const mainSeq = parseInt(daily.sequence_no)
    if (isNaN(mainSeq) || mainSeq <= 0) {
      daily.sequence_no = getNextSequenceForDate(dateKey)
    }
  }
  daily.extraLots.push({
    id: `lot-${lotTempId++}`,
    plan_qty: '',
    sequence_no: isFloorShippingDeliveryLine.value ? getNextSequenceForDate(dateKey) : '',
  })
}

const removeExtraLot = (row, dateKey, lotId) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  daily.extraLots = daily.extraLots.filter((lot) => lot.id !== lotId)
}

const onExtraPlanInput = (row, dateKey, lot, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  const target = daily.extraLots.find((item) => item.id === lot.id)
  if (target) {
    target.plan_qty = value === '' ? '' : value
    if (isFloorShippingDeliveryLine.value) {
      const numVal = parseFloat(value)
      if (!isNaN(numVal) && numVal > 0) {
        if (target.sequence_no === '' || target.sequence_no === null || target.sequence_no === undefined) {
          target.sequence_no = getNextSequenceForDate(dateKey)
        }
      } else {
        target.sequence_no = ''
      }
    }
  }
}

const onExtraSequenceInput = (row, dateKey, lot, value) => {
  if (isPlanCellLocked(dateKey)) return
  const daily = ensureDailyCell(row, dateKey)
  const target = daily.extraLots.find((item) => item.id === lot.id)
  if (target) {
    target.sequence_no = value === '' ? '' : value
  }
}

const validateFloorShippingLots = () => {
  if (!isFloorShippingDeliveryLine.value) return ''
  for (const row of rows.value) {
    for (const c of dateColumns.value) {
      const daily = ensureDailyCell(row, c.key)
      const lots = []
      const mainPlanQty = daily.plan === '' || daily.plan === null || daily.plan === undefined ? null : Number(daily.plan)
      if (mainPlanQty !== null && mainPlanQty > 0) {
        lots.push(mainPlanQty)
      }
      const extraLots = Array.isArray(daily.extraLots) ? daily.extraLots : []
      extraLots.forEach((lot) => {
        const lotPlanQty = lot.plan_qty === '' || lot.plan_qty === null || lot.plan_qty === undefined ? null : Number(lot.plan_qty)
        if (lotPlanQty !== null && lotPlanQty > 0) {
          lots.push(lotPlanQty)
        }
      })
      if (lots.length > 2) {
        const label = row.product_code || getProductCode(row.product_id) || row.product_id
        return `${c.key} の ${label} は 2件までです。`
      }
    }
  }
  return ''
}

const toggleProcessGantt = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  showProcessGantt.value = !showProcessGantt.value
  if (showProcessGantt.value) {
    ganttDirty.value = false
    ganttEditDirty.value = false
    ganttStructureDirty.value = false
    ganttMergeConsecutive.value = false
    ganttReloadKey.value += 1
  } else {
    ganttDirty.value = false
    ganttEditDirty.value = false
    ganttStructureDirty.value = false
    ganttMergeConsecutive.value = false
  }
}

const onGanttDirtyChange = (isDirty) => {
  ganttDirty.value = !!isDirty
}

const onGanttModeChange = (isMerged) => {
  ganttMergeConsecutive.value = !!isMerged
}

const onGanttEditDirtyChange = (isDirty) => {
  ganttEditDirty.value = !!isDirty
}

const onGanttStructureDirtyChange = (isDirty) => {
  ganttStructureDirty.value = !!isDirty
}

const setGanttMergeMode = (isMerged) => {
  ganttMergeConsecutive.value = !!isMerged
  const gantt = ganttRef.value
  if (gantt && typeof gantt.setMergeConsecutive === 'function') {
    gantt.setMergeConsecutive(isMerged)
  }
}

const saveGanttEditChanges = async () => {
  if (!showProcessGantt.value) {
    alert('工程ガントを表示してください。')
    return
  }
  const gantt = ganttRef.value
  if (!gantt || typeof gantt.saveEditChanges !== 'function') {
    alert('工程ガントが未読込です。')
    return
  }
  await gantt.saveEditChanges()
}

const saveGanttStructureChanges = async () => {
  if (!showProcessGantt.value) {
    alert('工程ガントを表示してください。')
    return
  }
  const gantt = ganttRef.value
  if (!gantt || typeof gantt.saveStructureChanges !== 'function') {
    alert('工程ガントが未読込です。')
    return
  }
  await gantt.saveStructureChanges()
}


const loadProcessLoad = async () => {
  if (!selectedLine.value) return
  processLoadLoading.value = true
  processLoadMessage.value = ''
  try {
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: selectedLine.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!rawPlans.length) {
      processLoadRows.value = []
      processLoadMessage.value = '工程ガントが未作成です。先に工程ガントを生成してください。'
      return
    }
    processLoadRows.value = buildProcessLoad(rawPlans)
  } catch (e) {
    console.error('工程負荷取得エラー', e)
    processLoadRows.value = []
    processLoadMessage.value = '工程負荷の取得に失敗しました。'
  } finally {
    processLoadLoading.value = false
  }
}

const toggleProcessLoad = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  showProcessLoad.value = !showProcessLoad.value
  if (showProcessLoad.value) {
    await loadProcessLoad()
  }
}

const fetchLines = async () => {
  const res = await api.lines.getProductionLines()
  lines.value = res.data.results || res.data || []
  await loadLineCodesByTab()
  await ensureSelectedLineForActiveTab(false)
}
const fetchProducts = async () => {
  products.value = (await api.products.getAllProducts())
    .filter((p) => !p.is_phantom)
    .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
}
const fetchProcessOptions = async () => {
  const res = await api.processes.getProcesses({ page_size: 5000 })
  const list = res?.data?.results || res?.data || []
  processOptions.value = (Array.isArray(list) ? list : [])
    .map((proc) => ({
      id: proc.id,
      process_code: String(proc.process_code || '').trim(),
      process_name: String(proc.process_name || '').trim(),
    }))
    .filter((proc) => proc.process_code)
    .sort((a, b) => a.process_code.localeCompare(b.process_code))
}

onMounted(async () => {
  try {
    await ensureAuth()
    await Promise.all([fetchLines(), fetchProducts(), fetchLockSetting(), fetchProcessOptions()])
    await loadData()
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})

watch(
  () => userUnitLines.value.map((item) => `${item?.line_id || ''}:${item?.is_default ? 1 : 0}:${item?.sort_order || 0}`).join('|'),
  async () => {
    await ensureSelectedLineForActiveTab()
  }
)

watch(activePlanTab, async () => {
  lineSettingsMessage.value = ''
  await ensureSelectedLineForActiveTab()
})
watch(settingsTargetTab, () => {
  lineSettingsMessage.value = ''
})

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})

const fetchLockSetting = async () => {
  try {
    const res = await api.productionPlanLockSetting.getSetting()
    lockDays.value = Number(res.data?.lock_days ?? 0)
  } catch (e) {
    console.error('生産計画ロック設定の取得エラー', e)
    lockDays.value = 0
  }
}

const fetchLineDefaultSetting = async (lineId) => {
  if (!lineId) {
    finalProcessStartTime.value = '08:00'
    adjustToBreakEnd.value = true
    return
  }
  try {
    const res = await api.lineDefaultScheduleSettings.getLineDefaultScheduleSettings({ line: lineId })
    const data = res.data?.results || res.data || []
    const setting = Array.isArray(data) ? data[0] : data
    finalProcessStartTime.value = setting?.final_process_start_time || '08:00'
    if (setting && Object.prototype.hasOwnProperty.call(setting, 'adjust_to_break_end')) {
      adjustToBreakEnd.value = !!setting.adjust_to_break_end
    } else {
      adjustToBreakEnd.value = true
    }
  } catch (e) {
    console.error('ラインデフォルト開始時刻の取得エラー', e)
    finalProcessStartTime.value = '08:00'
    adjustToBreakEnd.value = true
  }
}

const openChangeReasonDialog = () => {
  changeReasonDraft.value = changeReason.value
  showChangeReasonDialog.value = true
}

const closeChangeReasonDialog = () => {
  showChangeReasonDialog.value = false
}

const confirmChangeReason = () => {
  const reason = (changeReasonDraft.value || '').trim()
  if (!reason) {
    alert('変更理由を入力してください。')
    return
  }
  changeReason.value = reason
  isEditUnlocked.value = true
  showChangeReasonDialog.value = false
}

const hexToRgb = (hex) => {
  if (!hex || hex.length < 7) return [0, 0, 0]
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}
const hexToR = (hex) => hexToRgb(hex)[0]
const hexToG = (hex) => hexToRgb(hex)[1]
const hexToB = (hex) => hexToRgb(hex)[2]
const setRgbChannel = (hex, ch, val) => {
  const [r, g, b] = hexToRgb(hex)
  const v = Math.max(0, Math.min(255, Number(val) || 0))
  const nr = ch === 'r' ? v : r
  const ng = ch === 'g' ? v : g
  const nb = ch === 'b' ? v : b
  return `#${((1 << 24) | (nr << 16) | (ng << 8) | nb).toString(16).slice(1)}`
}

const getDisplayOrderContext = () => {
  if (activePlanTab.value === 'floor-shipping') return 'floor-shipping'
  return 'default'
}

const openProductOrderDialog = async () => {
  if (!selectedLine.value) return
  const ctx = getDisplayOrderContext()
  const seen = new Set()
  const items = []
  for (const row of rows.value) {
    const code = getRowProductCode(row)
    if (!code || seen.has(code)) continue
    seen.add(code)
    items.push({
      product_code: code,
      product_name: row.product_name || getProductName(row.product_id) || '',
      bg_color: '',
      text_color: '',
      plan_bg_color: '',
      plan_text_color: '',
    })
  }
  try {
    const res = await api.lineProductDisplayOrders.getOrders({
      line: selectedLine.value,
      context: ctx,
    })
    const saved = res.data || []
    if (saved.length > 0) {
      const savedMap = new Map(saved.map((s) => [s.product_code, s]))
      items.forEach((item) => {
        const s = savedMap.get(item.product_code)
        if (s) {
          item.bg_color = s.bg_color || ''
          item.text_color = s.text_color || ''
          item.plan_bg_color = s.plan_bg_color || ''
          item.plan_text_color = s.plan_text_color || ''
        }
      })
      const orderMap = new Map(saved.map((s) => [s.product_code, s.display_order]))
      items.sort((a, b) => {
        const oa = orderMap.has(a.product_code) ? orderMap.get(a.product_code) : 99999
        const ob = orderMap.has(b.product_code) ? orderMap.get(b.product_code) : 99999
        return oa - ob
      })
    }
  } catch (e) {
    console.error('表示順取得エラー', e)
  }
  productOrderItems.value = items
  productOrderActiveCode.value = ''
  showProductOrderDialog.value = true
}

const moveProductOrder = (idx, direction) => {
  const newIdx = idx + direction
  if (newIdx < 0 || newIdx >= productOrderItems.value.length) return
  const arr = [...productOrderItems.value]
  productOrderActiveCode.value = arr[idx].product_code
  ;[arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]]
  productOrderItems.value = arr
}

const saveProductOrder = async () => {
  if (!selectedLine.value) return
  productOrderSaving.value = true
  const ctx = getDisplayOrderContext()
  try {
    await api.lineProductDisplayOrders.bulkSave({
      line_id: selectedLine.value,
      context: ctx,
      items: productOrderItems.value.map((item, idx) => ({
        product_code: item.product_code,
        display_order: idx,
        bg_color: item.bg_color && item.bg_color !== '#ffffff' ? item.bg_color : '',
        text_color: item.text_color && item.text_color !== '#ffffff' ? item.text_color : '',
        plan_bg_color: item.plan_bg_color && item.plan_bg_color !== '#ffffff' ? item.plan_bg_color : '',
        plan_text_color: item.plan_text_color && item.plan_text_color !== '#ffffff' ? item.plan_text_color : '',
      })),
    })
    const cacheKey = `${selectedLine.value}__${ctx}`
    productOrderCache.value.set(cacheKey, productOrderItems.value.map((i) => i.product_code))
    const colorMap = new Map()
    productOrderItems.value.forEach((item) => {
      if (item.bg_color || item.plan_bg_color) {
        colorMap.set(item.product_code, {
          bg: item.bg_color && item.bg_color !== '#ffffff' ? item.bg_color : '',
          color: item.text_color && item.text_color !== '#ffffff' ? item.text_color : '#000',
          planBg: item.plan_bg_color && item.plan_bg_color !== '#ffffff' ? item.plan_bg_color : '',
          planColor: item.plan_text_color && item.plan_text_color !== '#ffffff' ? item.plan_text_color : '#000',
        })
      }
    })
    productColorCache.value.set(cacheKey, colorMap)
    rows.value = sortRowsForLine(rows.value)
    showProductOrderDialog.value = false
  } catch (e) {
    alert('保存に失敗しました。')
    console.error('表示順保存エラー', e)
  } finally {
    productOrderSaving.value = false
  }
}

const parseTimeParts = (value) => {
  if (!value) return null
  const parts = String(value).split(':')
  if (parts.length < 2) return null
  const hour = Number(parts[0])
  const minute = Number(parts[1])
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null
  return { hour, minute }
}

const getWorkStartForDate = (dateKey) => {
  const day = calendarDayMap.value[dateKey]
  if (isNonWorkingCalendarDay(day)) return null
  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.start_time)
    if (parsed) return parsed
  }
  return workStartFallback
}

const getWorkEndForDate = (dateKey, startParts) => {
  const day = calendarDayMap.value[dateKey]
  if (isNonWorkingCalendarDay(day)) return null
  const start = startParts || workStartFallback
  let endParts = null
  let dayOffset = 0

  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.end_time)
    if (parsed) {
      endParts = parsed
      if (parsed.hour < start.hour || (parsed.hour === start.hour && parsed.minute <= start.minute)) {
        dayOffset = 1
      }
    }
  }

  if (!endParts) {
    const workMinutes = day && day.work_minutes != null ? Number(day.work_minutes) : workMinutesFallback
    if (!Number.isFinite(workMinutes)) return null
    const startMinutes = start.hour * 60 + start.minute
    const endMinutesTotal = Math.max(0, startMinutes + workMinutes)
    dayOffset = Math.floor(endMinutesTotal / (24 * 60))
    const endMinutesInDay = endMinutesTotal % (24 * 60)
    endParts = {
      hour: Math.floor(endMinutesInDay / 60),
      minute: endMinutesInDay % 60,
    }
  }

  return { ...endParts, dayOffset }
}

const formatWorkTimeLabel = (dateKey) => {
  if (!dateKey) return ''
  const workStart = getWorkStartForDate(dateKey)
  if (!workStart) return ''
  const workEnd = getWorkEndForDate(dateKey, workStart)
  if (!workEnd) return ''
  const startLabel = `${String(workStart.hour).padStart(2, '0')}:${String(workStart.minute).padStart(2, '0')}`
  const endLabel = `${String(workEnd.hour).padStart(2, '0')}:${String(workEnd.minute).padStart(2, '0')}`
  const endPrefix = workEnd.dayOffset > 0 ? '翌' : ''
  return `(${startLabel}〜${endPrefix}${endLabel})`
}

const getWorkTimeLabel = (dateKey) => formatWorkTimeLabel(dateKey)

const resolveDaisoCalendarId = async () => {
  if (daisoCalendarId.value !== undefined) return daisoCalendarId.value || null
  const pickDaiso = (rows) => {
    const list = rows || []
    const exact = list.find((row) => String(row.calendar_code || '').trim().toLowerCase() === 'daiso')
    if (exact) return exact
    return list.find((row) => {
      const code = String(row.calendar_code || '').trim().toLowerCase()
      const name = String(row.calendar_name || '').trim().toLowerCase()
      return code.includes('daiso') || name.includes('daiso') || name.includes('ダイソウ')
    })
  }
  try {
    const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 200 })
    const rows = res.data?.results || res.data || []
    let daiso = pickDaiso(rows)
    if (!daiso) {
      const fallbackRes = await api.calendars.getCalendars({ page_size: 5000 })
      const fallbackRows = fallbackRes.data?.results || fallbackRes.data || []
      daiso = pickDaiso(fallbackRows)
    }
    daisoCalendarId.value = daiso?.id || null
  } catch (e) {
    console.error('DAISOカレンダ取得エラー', e)
    daisoCalendarId.value = null
  }
  return daisoCalendarId.value || null
}

const resolveLineCalendarId = async (lineId) => {
  let calendarId = null
  const line = lines.value.find((item) => String(item.id) === String(lineId))
  const lineCalendar = line?.calendar?.id ?? line?.calendar ?? null
  if (lineCalendar) {
    calendarId = lineCalendar
  } else {
    try {
      const lineRes = await api.lines.getLine(lineId)
      calendarId = lineRes.data?.calendar?.id ?? lineRes.data?.calendar ?? null
    } catch (e) {
      console.error('ライン勤務カレンダ取得エラー', e)
    }
  }
  if (calendarId) return calendarId
  return await resolveDaisoCalendarId()
}

const loadWorkPatternData = async (lineId, start, end) => {
  calendarDayMap.value = {}
  workPatternMap.value = {}
  if (!lineId) return

  const calendarId = await resolveLineCalendarId(lineId)
  if (!calendarId) return

  const filterByRange = (days) => {
    return (days || []).filter((day) => {
      if (!day.target_date) return false
      if (start && day.target_date < start) return false
      if (end && day.target_date > end) return false
      return true
    })
  }

  try {
    const daysRes = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 })
    const days = daysRes.data?.results || daysRes.data || []
    const primaryFiltered = filterByRange(days)
    const mergedByDate = new Map(primaryFiltered.map((day) => [day.target_date, day]))

    const daisoId = await resolveDaisoCalendarId()
    if (daisoId && String(daisoId) !== String(calendarId)) {
      const daisoRes = await api.calendars.getCalendarDays(daisoId, { page_size: 5000 })
      const daisoDays = daisoRes.data?.results || daisoRes.data || []
      const daisoFiltered = filterByRange(daisoDays)
      daisoFiltered.forEach((day) => {
        if (!mergedByDate.has(day.target_date)) {
          mergedByDate.set(day.target_date, day)
        }
      })
    }

    const filtered = Array.from(mergedByDate.values())
    const dayMap = {}
    const patternIds = new Set()
    filtered.forEach((day) => {
      dayMap[day.target_date] = day
      if (day.work_pattern) patternIds.add(String(day.work_pattern))
    })
    calendarDayMap.value = dayMap
    if (patternIds.size) {
      const patternsRes = await api.workPatterns.getWorkPatterns()
      const patterns = patternsRes.data?.results || patternsRes.data || []
      const patternMap = {}
      patterns.forEach((pattern) => {
        patternMap[String(pattern.id)] = pattern
      })
      workPatternMap.value = patternMap
    }
  } catch (e) {
    console.error('勤務パターン取得エラー', e)
  }
}


const buildProcessLoad = (plans) => {
  const processMap = new Map()
  plans.forEach((plan) => {
    const planDate = plan.plan_date || plan.planDate
    if (!planDate) return
    const dateKey = String(planDate).slice(0, 10)
    const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
    processes.forEach((pp) => {
      const pid = pp.process_id ?? 'unknown'
      let entry = processMap.get(pid)
      if (!entry) {
        entry = {
          process_id: pid,
          process_name: pp.process_name || '',
          process_number: pp.process_number ?? null,
          daily: {},
        }
        processMap.set(pid, entry)
      }
      const minutes = Number(pp.effective_minutes ?? pp.total_minutes_required ?? 0)
      if (!Number.isFinite(minutes) || minutes === 0) return
      entry.daily[dateKey] = (entry.daily[dateKey] || 0) + minutes
    })
  })
  const list = Array.from(processMap.values())
  list.sort((a, b) => {
    const aNum = a.process_number ?? 9999
    const bNum = b.process_number ?? 9999
    if (aNum != bNum) return aNum - bNum
    return (a.process_name || '').localeCompare(b.process_name || '')
  })
  return list
}

const formatLoad = (val) => {
  if (val == null) return ''
  const num = Number(val)
  if (Number.isNaN(num) || num === 0) return ''
  const minutes = Math.round(num * 10) / 10
  const hours = Math.round((minutes / 60) * 10) / 10
  return `${minutes} (${hours})`
}

const selectedLineLabel = computed(() => {
  const line = lines.value.find((item) => String(item.id) === String(selectedLine.value))
  if (!line) return ''
  const code = line.line_code || ''
  const name = line.line_name || ''
  return `${code} ${name}`.trim()
})

const openExportDialog = () => {
  if (!filteredRows.value.length) {
    alert('出力対象のデータがありません。')
    return
  }
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  showExportDialog.value = true
}

const closeExportDialog = () => {
  showExportDialog.value = false
}

const escapeCsv = (value) => {
  const text = `${value ?? ''}`
  const escaped = text.replace(/"/g, '""')
  return `"${escaped}"`
}

const escapeHtml = (value) => {
  const text = `${value ?? ''}`
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const formatLotValues = (daily, field) => {
  if (!daily) return ''
  const values = []
  const mainVal = daily[field]
  if (mainVal !== '' && mainVal !== null && mainVal !== undefined) {
    const disp = displayValue(mainVal)
    if (disp !== '') values.push(disp)
  }
  if (Array.isArray(daily.extraLots)) {
    daily.extraLots.forEach((lot) => {
      const val = field === 'plan' ? lot.plan_qty : lot.sequence_no
      if (val !== '' && val !== null && val !== undefined) {
        const disp = displayValue(val)
        if (disp !== '') values.push(disp)
      }
    })
  }
  return values.join('/')
}

const buildExportRow = (row) => {
  const data = []
  dateColumns.value.forEach((c, colIdx) => {
    const daily = row.daily?.[c.key] || {}
    if (isProgressMode.value) {
      data.push(displayValue(daily.line_demand_qty))
      data.push(displayValue(daily.actual))
      data.push(displayValue(daily.progress))
      data.push(formatLotValues(daily, 'plan'))
      data.push(formatLotValues(daily, 'sequence_no'))
      data.push(displayValue(daily.planned_progress))
    } else {
      data.push(displayValue(daily.demand))
      data.push(displayValue(daily.actual))
      data.push(displayValue(getStockDisplay(row, colIdx)))
      data.push(formatLotValues(daily, 'plan'))
      data.push(formatLotValues(daily, 'sequence_no'))
      data.push(displayValue(getPlanStockDisplay(row, colIdx)))
    }
  })
  return data
}

const downloadFloorShippingPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/floor-shipping-pdf/', {
      params: {
        line: sourceLineId,
        start_date: startDate.value,
        end_date: endDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `フロア配送明細_${startDate.value}_${endDate.value}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('配送明細PDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const downloadFloorShippingLapPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/floor-shipping-lap-pdf/', {
      params: {
        line: sourceLineId,
        start_date: startDate.value,
        end_date: endDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `フロア配送明細_ラップ_${startDate.value}_${endDate.value}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('配送明細ラップPDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const downloadFloorShippingNewPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/floor-shipping-new-pdf/', {
      params: {
        line: sourceLineId,
        start_date: startDate.value,
        end_date: endDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `フロア配送明細_新_${startDate.value}_${endDate.value}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('新配送明細PDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const downloadHokushinDeliveryListPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-list-pdf/', {
      params: {
        line: sourceLineId,
        start_date: startDate.value,
        end_date: endDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  } catch (e) {
    console.error('北進納入リストPDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const downloadHokushinDeliveryListNewPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-list-new-pdf/', {
      params: {
        line: sourceLineId,
        start_date: startDate.value,
        end_date: endDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  } catch (e) {
    console.error('新北進納入リストPDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const downloadHokushinDeliveryListLapPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-list-lap-pdf/', {
      params: {
        line: sourceLineId,
        start_date: startDate.value,
        end_date: endDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  } catch (e) {
    console.error('北進納入リストラップPDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

// 北進塗装納品書 確認モーダル状態
const hokushinDialogOpen = ref(false)
const hokushinDialogEdit = ref(false)
const hokushinAmDate = ref('')
const hokushinYoiDate = ref('')
const hokushinAmHasItems = ref(true)
const hokushinYoiHasItems = ref(true)

const formatJPDate = (ymd) => {
  if (!ymd) return ''
  const parts = ymd.split('-')
  if (parts.length !== 3) return ymd
  return `${parseInt(parts[1], 10)}月${parseInt(parts[2], 10)}日`
}

const closeHokushinDialog = () => {
  hokushinDialogOpen.value = false
  hokushinDialogEdit.value = false
}

// ボタン押下: プレビュー取得→確認モーダル表示
const downloadHokushinDeliveryPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-pdf/', {
      params: { line: sourceLineId, preview: '1' },
    })
    const data = res.data || {}
    hokushinAmDate.value = data.am_delivery_date || ''
    hokushinYoiDate.value = data.yoi_delivery_date || ''
    hokushinAmHasItems.value = !!data.am_has_items
    hokushinYoiHasItems.value = !!data.yoi_has_items
    if (!hokushinAmHasItems.value && !hokushinYoiHasItems.value) {
      // 両便とも空でも編集可能にしたい場合のためダイアログは開く
      // （BOSS要望: いいえで日付変更可能）
    }
    hokushinDialogEdit.value = false
    hokushinDialogOpen.value = true
  } catch (e) {
    console.error('北進塗装納品書プレビュー取得エラー', e)
    alert('プレビュー取得に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

// 確認: はい or 編集OK → 実際にPDF発行
const confirmHokushinDialog = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-pdf/', {
      params: {
        line: sourceLineId,
        am_delivery_date: hokushinAmDate.value,
        yoi_delivery_date: hokushinYoiDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    closeHokushinDialog()
  } catch (e) {
    if (e.response?.status === 404 && e.response?.data instanceof Blob) {
      try {
        const text = await e.response.data.text()
        const json = JSON.parse(text)
        if (json.code === 'EMPTY_DELIVERY') {
          alert('指定した日付に対象便がありません。')
          return
        }
        alert('PDF生成に失敗しました: ' + (json.detail || ''))
        return
      } catch (_) {
        // fallthrough
      }
    }
    console.error('北進塗装納品書PDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

// 北進塗装 納品書２（全製品）モーダル状態
const hokushinAllDialogOpen = ref(false)
const hokushinAllDialogEdit = ref(false)
const hokushinAllAmDate = ref('')
const hokushinAllYoiDate = ref('')
const hokushinAllAmHasItems = ref(true)
const hokushinAllYoiHasItems = ref(true)

const closeHokushinAllDialog = () => {
  hokushinAllDialogOpen.value = false
  hokushinAllDialogEdit.value = false
}

const downloadHokushinDeliveryAllPDF = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-all-pdf/', {
      params: { line: sourceLineId, preview: '1' },
    })
    const data = res.data || {}
    hokushinAllAmDate.value = data.am_delivery_date || ''
    hokushinAllYoiDate.value = data.yoi_delivery_date || ''
    hokushinAllAmHasItems.value = !!data.am_has_items
    hokushinAllYoiHasItems.value = !!data.yoi_has_items
    hokushinAllDialogEdit.value = false
    hokushinAllDialogOpen.value = true
  } catch (e) {
    console.error('北進塗装納品書２プレビュー取得エラー', e)
    alert('プレビュー取得に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const confirmHokushinAllDialog = async () => {
  const sourceLineId = floorShippingPdfSourceLineId.value
  if (!sourceLineId) {
    alert('フロア配送ラインが見つかりません。')
    return
  }
  try {
    const res = await api.client.get('/hokushin-delivery-all-pdf/', {
      params: {
        line: sourceLineId,
        am_delivery_date: hokushinAllAmDate.value,
        yoi_delivery_date: hokushinAllYoiDate.value,
      },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    closeHokushinAllDialog()
  } catch (e) {
    if (e.response?.status === 500 && e.response?.data instanceof Blob) {
      try {
        const text = await e.response.data.text()
        const json = JSON.parse(text)
        alert('PDF生成に失敗しました: ' + (json.detail || ''))
        return
      } catch (_) {
        // fallthrough
      }
    }
    console.error('北進塗装納品書２PDF生成エラー', e)
    alert('PDF生成に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const exportToExcel = () => {
  if (!filteredRows.value.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const bom = '\ufeff'
  const linesOut = []
  linesOut.push([escapeCsv('ライン'), escapeCsv(selectedLineLabel.value || '')].join(','))
  linesOut.push([escapeCsv('期間'), escapeCsv(`${startDate.value} ～ ${endDate.value}`)].join(','))
  linesOut.push([escapeCsv('日替わり時刻'), escapeCsv('08:00')].join(','))
  linesOut.push([escapeCsv('デフォルト開始時刻'), escapeCsv(finalProcessStartTime.value || '00:00')].join(','))
  linesOut.push('')

  const header1 = ['No', '品番']
  dateColumns.value.forEach((c) => {
    for (let i = 0; i < 6; i += 1) {
      header1.push(c.label)
    }
  })
  const header2 = ['No', '品番']
  dateColumns.value.forEach(() => {
    if (isProgressMode.value) {
      header2.push('進度', '実績', '受注', '計画', '順', '計進')
    } else {
      header2.push('在庫', '実績', '需要', '計画', '順序', '計庫')
    }
  })
  linesOut.push(header1.map(escapeCsv).join(','))
  linesOut.push(header2.map(escapeCsv).join(','))

  filteredRows.value.forEach((row, idx) => {
    const rowData = buildExportRow(row)
    rowData.unshift(row.product_code || getProductCode(row.product_id) || '')
    rowData.unshift(idx + 1)
    linesOut.push(rowData.map(escapeCsv).join(','))
  })

  const csvContent = bom + linesOut.join('\r\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const lineLabel = selectedLineLabel.value ? `_${selectedLineLabel.value.replace(/\\s+/g, '_')}` : ''
  link.href = url
  link.download = `production_plan${lineLabel}_${startDate.value}_${endDate.value}.csv`
  link.click()
  URL.revokeObjectURL(url)
  closeExportDialog()
}

const buildPrintTableHtml = () => {
  const headerInfo = `
    <div class="meta">
      <div><strong>ライン:</strong> ${escapeHtml(selectedLineLabel.value || '')}</div>
      <div><strong>期間:</strong> ${escapeHtml(startDate.value)} ～ ${escapeHtml(endDate.value)}</div>
      <div><strong>日替わり時刻:</strong> 08:00</div>
    </div>
  `

  const metrics = isProgressMode.value ? [
    { key: 'progress', label: '進度', getValue: (row, daily, colIdx) => displayValue(daily.progress) },
    { key: 'actual', label: '実績', getValue: (row, daily, colIdx) => displayValue(daily.actual) },
    { key: 'demand', label: '受注', getValue: (row, daily, colIdx) => displayValue(daily.line_demand_qty) },
    { key: 'plan', label: '計画', getValue: (row, daily, colIdx) => formatLotValues(daily, 'plan') },
    { key: 'sequence', label: '順', getValue: (row, daily, colIdx) => formatLotValues(daily, 'sequence_no') },
    { key: 'planned_progress', label: '計進', getValue: (row, daily, colIdx) => displayValue(daily.planned_progress) },
  ] : [
    { key: 'stock', label: '在庫', getValue: (row, daily, colIdx) => displayValue(getStockDisplay(row, colIdx)) },
    { key: 'actual', label: '実需', getValue: (row, daily, colIdx) => displayValue(daily.actual) },
    { key: 'demand', label: '計需', getValue: (row, daily, colIdx) => displayValue(daily.demand) },
    { key: 'plan', label: '計画', getValue: (row, daily, colIdx) => formatLotValues(daily, 'plan') },
    { key: 'sequence', label: '順序', getValue: (row, daily, colIdx) => formatLotValues(daily, 'sequence_no') },
    { key: 'plan_stock', label: '計庫', getValue: (row, daily, colIdx) => displayValue(getPlanStockDisplay(row, colIdx)) },
  ]

  const chunkDateColumns = () => {
    const chunks = []
    const SIZE = 30
    for (let i = 0; i < dateColumns.value.length; i += SIZE) {
      chunks.push({ cols: dateColumns.value.slice(i, i + SIZE), offset: i })
    }
    return chunks
  }

  const buildProductTable = (row, idx, chunkCols, offset) => {
    const thead = (() => {
      const headers = ['<tr class="head1"><th class="metric-col">項目</th>']
      chunkCols.forEach((c) => {
        headers.push(`<th class="date">${escapeHtml(c.label)}</th>`)
      })
      headers.push('</tr>')
      return headers.join('')
    })()

    const tbody = (() => {
      const rowsHtml = metrics.map((m) => {
        const cells = [`<td class="metric-name">${escapeHtml(m.label)}</td>`]
        chunkCols.forEach((c, localIdx) => {
          const globalIdx = offset + localIdx
          const daily = row.daily?.[c.key] || {}
          cells.push(`<td class="num">${escapeHtml(m.getValue(row, daily, globalIdx))}</td>`)
        })
        return `<tr>${cells.join('')}</tr>`
      })
      if (!rowsHtml.length) {
        rowsHtml.push(`<tr><td colspan="${1 + chunkCols.length}" class="no-data">データがありません</td></tr>`)
      }
      return rowsHtml.join('')
    })()

    return `
      <div class="product-block">
        <div class="product-header">
          <div><strong>No:</strong> ${idx + 1}</div>
          <div><strong>品番:</strong> ${escapeHtml(row.product_code || getProductCode(row.product_id) || '')}</div>
          <div><strong>品名:</strong> ${escapeHtml(row.product_name || getProductName(row.product_id) || '')}</div>
        </div>
        <table class="vertical-table">
          <thead>${thead}</thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>
    `
  }

  const tablesHtml = filteredRows.value
    .map((row, idx) =>
      chunkDateColumns()
        .map((chunk, cidx) => {
          const range = `${escapeHtml(chunk.cols[0]?.label || '')} ～ ${escapeHtml(chunk.cols[chunk.cols.length - 1]?.label || '')}`
          return `
            <div class="chunk-header">No.${idx + 1} 品番:${escapeHtml(row.product_code || getProductCode(row.product_id) || '')} ／ 期間: ${range}</div>
            ${buildProductTable(row, idx, chunk.cols, chunk.offset)}
          `
        })
        .join('')
    )
    .join('')

  const style = `
    <style>
      @page { size: A3 landscape; margin: 10mm; }
      body { font-family: "Noto Sans JP", "Segoe UI", sans-serif; color: #111; }
      h1 { margin: 0 0 8px; font-size: 18px; }
      .meta { display: flex; gap: 18px; margin-bottom: 8px; font-size: 12px; }
      .product-block { margin-bottom: 14px; page-break-inside: avoid; }
      .product-header { display: flex; gap: 14px; font-size: 12px; margin: 6px 0; }
      .chunk-header { margin: 6px 0 2px; font-size: 11px; color: #374151; }
      table.vertical-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; }
      th, td { border: 1px solid #cbd5e1; padding: 6px 8px; }
      th.date { background: #e7edf7; }
      th.metric-col { width: 90px; background: #cfd8ec; }
      td.metric-name { background: #f4f6fb; font-weight: 700; }
      td.num { text-align: right; }
      .no-data { text-align: center; }
    </style>
  `

  const html = `
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        ${style}
        <title>生産計画印刷</title>
      </head>
      <body>
        <h1>生産計画一覧</h1>
        ${headerInfo}
        ${tablesHtml}
      </body>
    </html>
  `
  return html
}

const exportToPdf = () => {
  if (!filteredRows.value.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const html = buildPrintTableHtml()
  const win = window.open('', '_blank')
  if (!win) {
    alert('ポップアップがブロックされました。許可して再実行してください。')
    return
  }
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => {
    win.print()
    win.onafterprint = () => win.close()
  }, 150)
  closeExportDialog()
}

const onGlobalKeydown = (event) => {
  if (event.key === 'F1') {
    event.preventDefault()
    goBack()
  } else if (event.key === 'F2') {
    event.preventDefault()
    goForward()
  } else if (event.key === 'F3') {
    event.preventDefault()
    if (!processing.value) resetRows()
  } else if (event.key === 'F4') {
    event.preventDefault()
    if (!processing.value && selectedLine.value) doDisplayOnly()
  } else if (event.key === 'F6') {
    event.preventDefault()
    if (!processing.value && selectedLine.value) doFetchOnly()
  } else if (event.key === 'F8') {
    event.preventDefault()
    if (!processing.value && selectedLine.value) doPickup()
  } else if (event.key === 'F5') {
    event.preventDefault()
    if (showChangeReasonDialog.value) {
      closeChangeReasonDialog()
    } else if (showBulkActualDialog.value) {
      closeBulkActualDialog()
    } else if (showExportDialog.value) {
      closeExportDialog()
    } else if (!processing.value) {
      resetRows()
    }
  } else if (event.key === 'F10') {
    event.preventDefault()
    openExportDialog()
  }
}

const fetchAndApplyData = async () => {
  currentLineRoutingFilterMode.value = 'filtered'
  const fetchLineDemands = activePlanTab.value === 'floor-shipping'
    ? api.lineDemands.list({
        line: selectedLine.value,
        plan_date__gte: startDate.value,
        plan_date__lte: endDate.value,
      })
    : Promise.resolve(null)
  const displayOrderCtx = getDisplayOrderContext()
  const displayOrderCacheKey = `${selectedLine.value}__${displayOrderCtx}`
  const fetchDisplayOrder = productOrderCache.value.has(displayOrderCacheKey)
    ? Promise.resolve(null)
    : api.lineProductDisplayOrders.getOrders({ line: selectedLine.value, context: displayOrderCtx }).catch(() => null)
  const [backlogRes, planRes, lineRoutingFilter, lineDemandRes, displayOrderRes] = await Promise.all([
    api.lineBacklogs.getLineBacklogs({
      line: selectedLine.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    }),
    api.linePlans.getLinePlans({
      line: selectedLine.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    }),
    fetchCurrentLineProductIdSet(selectedLine.value),
    fetchLineDemands,
    fetchDisplayOrder,
  ])
  if (displayOrderRes) {
    const saved = displayOrderRes.data || []
    if (saved.length > 0) {
      const sorted = [...saved].sort((a, b) => a.display_order - b.display_order)
      productOrderCache.value.set(displayOrderCacheKey, sorted.map((s) => s.product_code))
      const colorMap = new Map()
      saved.forEach((s) => {
        if (s.bg_color || s.plan_bg_color) {
          colorMap.set(s.product_code, {
            bg: s.bg_color || '', color: s.text_color || '#000',
            planBg: s.plan_bg_color || '', planColor: s.plan_text_color || '#000',
          })
        }
      })
      if (colorMap.size > 0) productColorCache.value.set(displayOrderCacheKey, colorMap)
    }
  }
  currentLineRoutingFilterMode.value = lineRoutingFilter?.mode || 'fallback'
  const backlogData = backlogRes.data?.results || backlogRes.data || []
  const planData = planRes.data?.results || planRes.data || []
    const selectedLineCode = normalizeLineCode(lines.value.find((line) => String(line.id) === String(selectedLine.value))?.line_code)
    const processCodeById = new Map((processOptions.value || []).map((proc) => [String(proc.id), normalizeProcessCode(proc.process_code)]))
    const plannedStockRuleMap = new Map(
      (plannedStockCalcRules.value || []).map((rule) => [
        `${normalizeLineCode(rule.lineCode)}|${normalizeProcessCode(rule.processCode)}|${String(rule.calcTarget || '').trim().toUpperCase()}`,
        String(rule.setting || '').trim().toUpperCase(),
      ]),
    )
    const filterRowsByCurrentLineRouting = (items) => {
      const list = Array.isArray(items) ? items : []
      if (lineRoutingFilter?.mode === 'fallback') {
        return list
      }
      if (!(lineRoutingFilter?.productIdSet instanceof Set)) {
        return list
      }
      return list.filter((item) => {
        const productId = item?.product
        if (productId === null || productId === undefined || productId === '') return false
        return lineRoutingFilter.productIdSet.has(String(productId))
      })
    }

    let displayBacklogs = filterRowsByCurrentLineRouting(
      backlogData.filter(d => d.is_line_final_product === true)
    )
    let displayPlans = filterRowsByCurrentLineRouting(
      planData.filter(d => d.is_line_final_product !== false)
    )
    if (shouldLimitToCoproductParentAndDriver.value) {
      const filtered = await filterPlanRowsForCoproductDisplay(backlogData, planData)
      displayBacklogs = filterRowsByCurrentLineRouting(filtered.backlogRows)
      displayPlans = filterRowsByCurrentLineRouting(filtered.planRows)
    }

    const grouped = new Map()
    const demandMap = new Map()
    const actualMap = new Map()
    const stockSourceMap = new Map()
    const progressSourceMap = new Map()
    const lineDemandMap = new Map()
    const prodKeyByDateKey = new Map()
    const productInfoByProdKey = new Map()
    const planLotsByDate = new Map()

    const normalizeSeq = (seq) => {
      if (seq === null || seq === undefined || seq === '' || seq === 0) return null
      const num = Number(seq)
      return Number.isFinite(num) ? num : null
    }
    const ensureRow = (prodKey) => {
      if (!grouped.has(prodKey)) {
        const info = productInfoByProdKey.get(prodKey) || {}
        grouped.set(prodKey, {
          id: `pl-${prodKey}`,
          product_id: info.product_id || '',
          product_code: info.product_code || '',
          product_name: info.product_name || '',
          process_id: info.process_id || '',
          daily: initDaily(),
        })
      }
      return grouped.get(prodKey)
    }

    displayPlans.forEach((d) => {
      if (!d.product) return
      const prodKey = `${d.product}`
      const dateKey = `${prodKey}__${d.plan_date}`
      const seqNo = normalizeSeq(d.sequence_no) ?? 1
      productInfoByProdKey.set(prodKey, {
        product_id: d.product,
        product_code: d.product_code || '',
        product_name: d.product_name || '',
        process_id: d.process,
      })
      if (!planLotsByDate.has(dateKey)) {
        planLotsByDate.set(dateKey, [])
      }
      planLotsByDate.get(dateKey).push({
        plan_qty: d.plan_qty,
        sequence_no: seqNo,
      })
    })

    displayBacklogs.forEach((d) => {
      if (!d.product) return
      const prodKey = `${d.product}`
      const dateKey = `${prodKey}__${d.plan_date}`
      const seqNo = normalizeSeq(d.sequence_no) ?? 0
      prodKeyByDateKey.set(dateKey, prodKey)
      if (!productInfoByProdKey.has(prodKey)) {
        productInfoByProdKey.set(prodKey, {
          product_id: d.product,
          product_code: d.product_code || '',
          product_name: d.product_name || '',
          process_id: d.process,
        })
      }
      const planQtyVal = Number(d.plan_qty || 0)
      const planIdVal = d.plan_id || ''
      const isDemandRow = seqNo === 0 && planQtyVal <= 0 && planIdVal === ''
      if (isDemandRow) {
        const processCode = processCodeById.get(String(d.process)) || normalizeProcessCode(d.process_code)
        const demandRuleKey = `${selectedLineCode}|${processCode}|DEMAND`
        const useParentPlanDemand = plannedStockRuleMap.get(demandRuleKey) === 'PARENT_PLAN'
        const current = Number(useParentPlanDemand ? (d.demand_qty_plan || 0) : (d.order_qty || 0))
        const prev = demandMap.get(dateKey)
        demandMap.set(dateKey, prev == null ? current : Math.max(prev, current))
      }
      const actualVal = Number(d.actual_qty || 0)
      const prevActual = actualMap.get(dateKey)
      actualMap.set(dateKey, prevActual == null ? actualVal : Math.max(prevActual, actualVal))
      const stockEntry = stockSourceMap.get(dateKey)
      const priority = seqNo === 0 ? 0 : 1
      if (
        !stockEntry ||
        priority < stockEntry.priority ||
        (priority === stockEntry.priority && seqNo < stockEntry.seq)
      ) {
        stockSourceMap.set(dateKey, {
          priority,
          seq: seqNo,
          stock: Number(d.stock_qty || 0),
          plan_stock: Number(d.planned_stock_qty || 0),
        })
      }
      // 進度データ（sequence_no=0の需要行を優先）
      const progressEntry = progressSourceMap.get(dateKey)
      if (
        !progressEntry ||
        priority < progressEntry.priority ||
        (priority === progressEntry.priority && seqNo < progressEntry.seq)
      ) {
        progressSourceMap.set(dateKey, {
          priority,
          seq: seqNo,
          progress: Number(d.progress_qty || 0),
          planned_progress: Number(d.planned_progress_qty || 0),
        })
      }
    })

    planLotsByDate.forEach((lots, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const sorted = [...lots].sort((a, b) => (a.sequence_no || 0) - (b.sequence_no || 0))
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      const main = sorted[0]
      if (main) {
        const planQty = Number(main.plan_qty || 0)
        daily.plan = Number.isFinite(planQty) && planQty > 0 ? main.plan_qty : ''
        daily.sequence_no = main.sequence_no
      }
      daily.extraLots = sorted.slice(1).map((lot) => ({
        id: `lot-${lotTempId++}`,
        plan_qty: lot.plan_qty,
        sequence_no: lot.sequence_no,
      }))
      daily.plan_base = sorted.reduce((sum, lot) => sum + Number(lot.plan_qty || 0), 0)
      daily.has_row = true
    })

    demandMap.forEach((qty, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      daily.demand = Number(qty || 0)
      daily.actual = Number(actualMap.get(dateKey) || 0)
    })

    stockSourceMap.forEach((entry, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      daily.stock = Number(entry.stock || 0)
      daily.plan_stock = Number(entry.plan_stock || 0)
      daily.actual = Number(actualMap.get(dateKey) || 0)
      daily.has_row = true
    })

    // 進度データを適用
    progressSourceMap.forEach((entry, dateKey) => {
      const parts = dateKey.split('__')
      const date = parts.pop()
      const prodKey = parts.join('__')
      if (!prodKey || !date) return
      const row = ensureRow(prodKey)
      const daily = ensureDailyCell(row, date)
      daily.progress = Number(entry.progress || 0)
      daily.planned_progress = Number(entry.planned_progress || 0)
    })

    // LineDemand受注データを適用（進度基準モード用）
    if (lineDemandRes) {
      const demandData = lineDemandRes.data?.results || lineDemandRes.data || []
      demandData.forEach((d) => {
        if (!d.product) return
        const prodKey = `${d.product}`
        const dateKey = `${prodKey}__${d.plan_date}`
        const firm = Number(d.firm_qty || 0)
        const forecast = Number(d.forecast_qty || 0)
        // 確定あったら確定、ないときは内示、両方あるときは合計
        const qty = (firm > 0 && forecast > 0) ? firm + forecast : (firm > 0 ? firm : forecast)
        const prev = lineDemandMap.get(dateKey) || 0
        lineDemandMap.set(dateKey, prev + qty)
      })
      lineDemandMap.forEach((qty, dateKey) => {
        const parts = dateKey.split('__')
        const date = parts.pop()
        const prodKey = parts.join('__')
        if (!prodKey || !date) return
        const row = ensureRow(prodKey)
        const daily = ensureDailyCell(row, date)
        daily.line_demand_qty = qty
      })
    }

    // L2201専用: ライン最終品は計画/在庫データが未作成でも行表示する
    ensureL2201LineFinalRows(grouped, productInfoByProdKey)

    rows.value = sortRowsForLine(Array.from(grouped.values()))

    // 日別設定を読み込み、未設定の日にデフォルト値をセット
    await loadDailySettings()
    applyDefaultToDailySettings()
}

const doPickup = async () => {
  if (!selectedLine.value) return
  processing.value = true
  try {
    await api.lineBacklogs.pickup({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    await api.lineBacklogs.recalculateInventory({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
      include_progress: isProgressMode.value,
      line_final_only: true,
    })
    await fetchAndApplyData()
  } catch (e) {
    console.error('バックログ取り込みエラー', e)
    alert('取り込みに失敗しました。')
  } finally {
    processing.value = false
  }
}

const doDisplayOnly = async () => {
  if (!selectedLine.value) return
  processing.value = true
  try {
    await fetchAndApplyData()
  } catch (e) {
    console.error('データ取得エラー', e)
    alert('データの取得に失敗しました。')
  } finally {
    processing.value = false
  }
}

const doFetchOnly = async () => {
  if (!selectedLine.value) return
  processing.value = true
  try {
    await api.lineBacklogs.pickup({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    await fetchAndApplyData()
  } catch (e) {
    console.error('データ取得エラー', e)
    alert('データの取得に失敗しました。')
  } finally {
    processing.value = false
  }
}

const autoPlanAggregateSettingsMap = ref({})

const loadAutoPlanAggregateSettingsForSelectedLine = async () => {
  if (!selectedLine.value) {
    autoPlanAggregateSettingsMap.value = {}
    return
  }
  const res = await api.autoPlanAggregateSettings.list({
    line: selectedLine.value,
    is_active: true,
    page_size: 1000,
  })
  const rowsData = res?.data?.results || res?.data || []
  const map = {}
  ;(Array.isArray(rowsData) ? rowsData : []).forEach((row) => {
    const code = String(row?.product_code || '').trim()
    if (!code) return
    map[code] = {
      aggregate_weekday: Number(row.aggregate_weekday),
      aggregate_days: Number(row.aggregate_days) || 7,
    }
  })
  autoPlanAggregateSettingsMap.value = map
}

// まとめ生産設定ダイアログ
const showAggregateDialog = ref(false)
const aggRows = ref([])
const aggWeekdayOptions = [
  { value: 0, label: '日曜' }, { value: 1, label: '月曜' }, { value: 2, label: '火曜' },
  { value: 3, label: '水曜' }, { value: 4, label: '木曜' }, { value: 5, label: '金曜' },
  { value: 6, label: '土曜' },
]
const aggWeekdayLabel = (v) => aggWeekdayOptions.find((x) => x.value === Number(v))?.label || '-'
const emptyAggForm = () => ({ id: null, product: '', aggregate_weekday: 2, aggregate_days: 7, is_active: true })
const aggForm = ref(emptyAggForm())
const resetAggForm = () => { aggForm.value = emptyAggForm() }

const aggregateProductOptions = computed(() => {
  const seen = new Set()
  return rows.value
    .filter((r) => {
      const id = r.product_id
      if (!id || seen.has(id)) return false
      seen.add(id)
      return true
    })
    .map((r) => ({
      product_id: r.product_id,
      product_code: r.product_code || getProductCode(r.product_id),
      product_name: r.product_name || getProductName(r.product_id),
    }))
    .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
})

const loadAggRows = async () => {
  if (!selectedLine.value) { aggRows.value = []; return }
  const res = await api.autoPlanAggregateSettings.list({ line: selectedLine.value, page_size: 1000 })
  aggRows.value = res?.data?.results || res?.data || []
}

const openAggregateSettingsDialog = async () => {
  resetAggForm()
  await loadAggRows()
  showAggregateDialog.value = true
}

const saveAggregateSetting = async () => {
  if (!aggForm.value.product) { alert('製品を選択してください。'); return }
  const payload = {
    line: selectedLine.value,
    product: aggForm.value.product,
    aggregate_weekday: Number(aggForm.value.aggregate_weekday),
    aggregate_days: Number(aggForm.value.aggregate_days),
    is_active: !!aggForm.value.is_active,
  }
  try {
    if (aggForm.value.id) {
      await api.autoPlanAggregateSettings.update(aggForm.value.id, payload)
    } else {
      await api.autoPlanAggregateSettings.create(payload)
    }
    await loadAggRows()
    resetAggForm()
  } catch (e) {
    alert(e?.response?.data?.detail || '保存に失敗しました。')
  }
}

const editAggRow = (row) => {
  aggForm.value = {
    id: row.id, product: row.product,
    aggregate_weekday: row.aggregate_weekday, aggregate_days: row.aggregate_days,
    is_active: row.is_active,
  }
}

const deleteAggRow = async (id) => {
  if (!confirm('削除しますか？')) return
  await api.autoPlanAggregateSettings.remove(id)
  await loadAggRows()
  if (aggForm.value.id === id) resetAggForm()
}

const applyDemandToPlanForDay = (dateKey) => {
  if (isPlanCellLocked(dateKey)) return
  rows.value.forEach((row) => {
    const daily = ensureDailyCell(row, dateKey)
    const sourceQty = isProgressMode.value ? daily.line_demand_qty : daily.demand
    const demandQtyRaw = Number(sourceQty || 0)
    const demandQty = Number.isFinite(demandQtyRaw) ? Math.max(0, demandQtyRaw) : 0
    const newPlan = demandQty > 0 ? demandQty : ''
    if (daily.plan !== newPlan) {
      daily.plan = newPlan
      if (demandQty > 0) {
        const seq = daily.sequence_no
        if (seq === '' || seq === null || seq === undefined) {
          daily.sequence_no = getNextSequenceForDate(dateKey)
        }
      } else {
        daily.sequence_no = ''
      }
    }
  })
}

const applyDemandToPlanForVisiblePeriod = () => {
  const getWeekday = (dateKey) => {
    const dt = new Date(`${dateKey}T00:00:00`)
    return dt.getDay()
  }
  const addDays = (dateKey, days) => {
    const dt = new Date(`${dateKey}T00:00:00`)
    dt.setDate(dt.getDate() + days)
    const y = dt.getFullYear()
    const m = String(dt.getMonth() + 1).padStart(2, '0')
    const d = String(dt.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  const calcAggregateDemand = (row, dateKey, days) => {
    let total = 0
    for (let offset = 1; offset <= days; offset += 1) {
      const targetKey = addDays(dateKey, offset)
      const targetDaily = ensureDailyCell(row, targetKey)
      const sourceQty = isProgressMode.value ? targetDaily.line_demand_qty : targetDaily.demand
      const demandQtyRaw = Number(sourceQty || 0)
      const demandQty = Number.isFinite(demandQtyRaw) ? Math.max(0, demandQtyRaw) : 0
      total += demandQty
    }
    return total
  }

  let autoPlanCount = 0
  rows.value.forEach((row) => {
    dateColumns.value.forEach((c) => {
      const daily = ensureDailyCell(row, c.key)
      let demandQty = 0
      const productCode = String(row?.product_code || '').trim()
      const aggregateSetting = autoPlanAggregateSettingsMap.value[productCode]
      if (aggregateSetting) {
        const targetWeekday = Number.isFinite(aggregateSetting.aggregate_weekday) ? aggregateSetting.aggregate_weekday : 2
        const days = Number.isFinite(aggregateSetting.aggregate_days) && aggregateSetting.aggregate_days > 0
          ? Math.floor(aggregateSetting.aggregate_days)
          : 7
        if (getWeekday(c.key) === targetWeekday) {
          demandQty = calcAggregateDemand(row, c.key, days)
        } else {
          demandQty = 0
        }
      } else {
        const sourceQty = isProgressMode.value ? daily.line_demand_qty : daily.demand
        const demandQtyRaw = Number(sourceQty || 0)
        demandQty = Number.isFinite(demandQtyRaw) ? Math.max(0, demandQtyRaw) : 0
      }
      daily.plan = demandQty > 0 ? demandQty : ''
      daily.sequence_no = ''
      daily.extraLots = []
      if (demandQty > 0) autoPlanCount += 1
    })
  })
  return autoPlanCount
}

const showAutoPlanConfirm = ref(false)
const autoPlanConfirmLine = ref('')
const autoPlanConfirmPeriod = ref('')
let autoPlanConfirmResolve = null

const cancelAutoPlanConfirm = () => {
  showAutoPlanConfirm.value = false
  if (autoPlanConfirmResolve) { autoPlanConfirmResolve(false); autoPlanConfirmResolve = null }
}
const confirmAutoPlan = () => {
  showAutoPlanConfirm.value = false
  if (autoPlanConfirmResolve) { autoPlanConfirmResolve(true); autoPlanConfirmResolve = null }
}

const doFloorSpotAutoPlan = async () => {
  if (!selectedLine.value) return
  if (!canShowFloorSpotAutoPlanButton.value) return
  autoPlanConfirmLine.value = selectedLineLabel.value || `ID:${selectedLine.value}`
  autoPlanConfirmPeriod.value = `${startDate.value} ～ ${endDate.value}`
  showAutoPlanConfirm.value = true
  const confirmed = await new Promise((resolve) => { autoPlanConfirmResolve = resolve })
  if (!confirmed) return

  processing.value = true
  try {
    await loadAutoPlanAggregateSettingsForSelectedLine()
    await api.lineBacklogs.pickup({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    await fetchAndApplyData()
    const autoPlanCount = applyDemandToPlanForVisiblePeriod()
    if (!autoPlanCount) {
      alert('表示期間内に需要がないため、自動計画を実行しませんでした。')
      return
    }
  } catch (e) {
    console.error('自動計画エラー', e)
    alert('自動計画の事前処理（需要取込）に失敗しました。')
    return
  } finally {
    processing.value = false
  }

  await savePlan()
}

const openBulkActualDialog = () => {
  bulkActualStartDate.value = startDate.value
  bulkActualEndDate.value = endDate.value
  showBulkActualDialog.value = true
}

const closeBulkActualDialog = () => {
  showBulkActualDialog.value = false
}

const calcDailyPlanTotal = (daily) => {
  if (!daily) return 0
  let total = Number(daily.plan || 0)
  if (!Number.isFinite(total)) total = 0
  const extraLots = Array.isArray(daily.extraLots) ? daily.extraLots : []
  extraLots.forEach((lot) => {
    const qty = Number(lot?.plan_qty || 0)
    if (Number.isFinite(qty)) total += qty
  })
  return total
}

const applyBulkActualFromPlan = () => {
  if (!bulkActualStartDate.value || !bulkActualEndDate.value) {
    alert('開始日と終了日を指定してください。')
    return
  }
  if (bulkActualStartDate.value > bulkActualEndDate.value) {
    alert('終了日は開始日以降で指定してください。')
    return
  }
  if (bulkActualStartDate.value < startDate.value || bulkActualEndDate.value > endDate.value) {
    alert('選択期間は表示期間内で指定してください。')
    return
  }
  rows.value.forEach((row) => {
    dateColumns.value.forEach((c) => {
      if (c.key < bulkActualStartDate.value || c.key > bulkActualEndDate.value) return
      const daily = ensureDailyCell(row, c.key)
      const planTotal = calcDailyPlanTotal(daily)
      daily.actual = planTotal > 0 ? planTotal : ''
    })
  })
  showBulkActualDialog.value = false
}

const saveActuals = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }

  const items = []
  const invalidCells = []
  rows.value.forEach((row) => {
    if (!row.product_id || !row.process_id) return
    dateColumns.value.forEach((c) => {
      const daily = ensureDailyCell(row, c.key)
      const rawActual = daily.actual
      if (rawActual !== '' && rawActual !== null && rawActual !== undefined && Number.isNaN(Number(rawActual))) {
        invalidCells.push(`${row.product_code || getProductCode(row.product_id) || row.product_id} / ${c.key}`)
      }
      const actualVal = Number(rawActual || 0)
      items.push({
        product_id: row.product_id,
        process_id: row.process_id,
        plan_date: c.key,
        actual_qty: Number.isFinite(actualVal) ? actualVal : 0,
        sequence_no: 0,
      })
    })
  })

  if (invalidCells.length) {
    alert(`実績に数値以外が入力されています。\n${invalidCells.slice(0, 10).join('\n')}${invalidCells.length > 10 ? `\n...他${invalidCells.length - 10}件` : ''}`)
    return
  }

  if (!items.length) {
    alert('実績保存対象がありません。')
    return
  }

  processing.value = true
  try {
    const res = await api.lineBacklogs.save({
      line_id: selectedLine.value,
      items,
    })
    alert(`実績を保存しました。\n作成: ${res.data?.created ?? 0}件, 更新: ${res.data?.updated ?? 0}件`)
    await fetchAndApplyData()
  } catch (e) {
    console.error('実績保存エラー', e)
    alert('実績保存に失敗しました。')
  } finally {
    processing.value = false
  }
}

const recalculateProgressFromPast = async () => {
  if (!selectedLine.value) {
    alert('ラインを選択してください。')
    return
  }
  const productIds = Array.from(new Set(
    rows.value
      .map((row) => Number(row.product_id))
      .filter((id) => Number.isFinite(id) && id > 0)
  ))
  if (!productIds.length) {
    alert('再計算対象の品番がありません。')
    return
  }

  let calcStartDate = startDate.value
  try {
    const responses = await Promise.all(
      productIds.map((productId) => api.lineBacklogs.getCalcStartDate({ product_id: productId }))
    )
    const dates = responses
      .map((res) => res?.data?.calc_start_date)
      .filter((dateStr) => typeof dateStr === 'string' && dateStr.length > 0)
    if (dates.length) {
      const ltStartDate = dates.reduce((minDate, dateStr) => (dateStr < minDate ? dateStr : minDate), dates[0])
      calcStartDate = ltStartDate < startDate.value ? ltStartDate : startDate.value
    }
  } catch (e) {
    console.error('calc_start_date取得エラー', e)
  }

  const lineLabel = selectedLineLabel.value || `ID:${selectedLine.value}`
  const ok = window.confirm(
    `進度のみ過去再計算を実行します。\n` +
    `ライン: ${lineLabel}\n` +
    `表示開始日: ${startDate.value}\n` +
    `再計算開始日（内部）: ${calcStartDate}（ルーティング/BOM由来LTで自動算出）\n` +
    `終了日: ${endDate.value}\n` +
    `対象品番: ${productIds.length}件`
  )
  if (!ok) return

  processing.value = true
  try {
    await api.lineBacklogs.recalculateInventoryDeep({
      line_id: selectedLine.value,
      start_date: calcStartDate,
      end_date: endDate.value,
      product_ids: productIds,
      progress_only: true,
    })
    await fetchAndApplyData()
    alert('過去から再計算（進度のみ）が完了しました。')
  } catch (e) {
    console.error('過去から再計算エラー', e)
    alert('過去から再計算に失敗しました。')
  } finally {
    processing.value = false
  }
}

const bulkDeletePlans = async () => {
  if (!selectedLine.value) return
  const lineLabel = selectedLineLabel.value || `ID:${selectedLine.value}`
  const confirmed = window.confirm(
    `選択ラインの計画を一括削除します。\nライン: ${lineLabel}\n期間: ${startDate.value} ～ ${endDate.value}\n\n対象: plan / gantt / linebacklog( sequence_no != 0 )\n実行してよろしいですか？`
  )
  if (!confirmed) return

  processing.value = true
  try {
    const res = await api.linePlans.bulkDelete({
      line_id: selectedLine.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    await fetchAndApplyData()
    // 削除後に埋め込みガント/工程負荷の表示を最新化
    ganttReloadKey.value += 1
    if (showProcessLoad.value) {
      await loadProcessLoad()
    }
    const deletedPlan = Number(res.data?.deleted_plan || 0)
    const deletedGantt = Number(res.data?.deleted_gantt || 0)
    const deletedBacklog = Number(res.data?.deleted_backlog || 0)
    alert(`一括削除しました。\nplan: ${deletedPlan}件\ngantt: ${deletedGantt}件\nlinebacklog(sequence_no!=0): ${deletedBacklog}件`)
  } catch (e) {
    console.error('計画一括削除エラー', e)
    alert('計画一括削除に失敗しました。')
  } finally {
    processing.value = false
  }
}

const loadDailySettings = async () => {
  if (!selectedLine.value) return
  try {
    const res = await api.lineDailyScheduleSettings.getLineDailyScheduleSettings({
      line: selectedLine.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
    })
    const settings = res.data?.results || res.data || []
    const settingsMap = {}
    settings.forEach((s) => {
      const t = s.final_process_start_time
      settingsMap[s.plan_date] = {
        id: s.id,
        final_process_start_time: t ? t.slice(0, 5) : t,
        adjust_to_break_end: s.adjust_to_break_end,
      }
    })
    dailySettings.value = settingsMap
  } catch (e) {
    console.error('日別設定読み込みエラー', e)
  }
}

// 日別設定が未設定の日にデフォルト開始時刻を表示用にセット
const applyDefaultToDailySettings = () => {
  const defaultTime = finalProcessStartTime.value || '08:00'
  dateColumns.value.forEach((c) => {
    if (!dailySettings.value[c.key] || !dailySettings.value[c.key].final_process_start_time) {
      dailySettings.value[c.key] = {
        ...dailySettings.value[c.key],
        final_process_start_time: defaultTime,
      }
    }
  })
}

const onDailySettingTimeChange = (dateKey, timeValue) => {
  if (!dailySettings.value[dateKey]) {
    dailySettings.value[dateKey] = {}
  }
  const normalized = normalizeTimeInput(timeValue)
  dailySettings.value[dateKey].final_process_start_time = normalized || null
}

const onDailySettingTimeBlur = async (dateKey) => {
  // 時刻入力欄から離れた時に自動保存
  if (!selectedLine.value) return
  const setting = dailySettings.value[dateKey]
  if (!setting || !setting.final_process_start_time) return
  const normalized = normalizeTimeInput(setting.final_process_start_time, true)
  if (!normalized) return
  // デフォルト値と同じ場合は日別設定として保存しない（不要な上書きを防止）
  const defaultTime = finalProcessStartTime.value || '08:00'
  if (normalized === defaultTime) {
    setting.final_process_start_time = null
    return
  }
  setting.final_process_start_time = normalized

  try {
    await api.lineDailyScheduleSettings.bulkSaveLineDailyScheduleSettings([{
      line: selectedLine.value,
      plan_date: dateKey,
      final_process_start_time: normalized,
      adjust_to_break_end: adjustToBreakEnd.value,
    }])
    console.log(`日別設定を保存しました: ${dateKey} - ${setting.final_process_start_time}`)
  } catch (e) {
    console.error('日別設定の保存に失敗しました', e)
  }
}

const saveDailySettings = async () => {
  if (!selectedLine.value) return
  const settings = []
  Object.keys(dailySettings.value).forEach((dateKey) => {
    const setting = dailySettings.value[dateKey]
    if (setting.final_process_start_time) {
      settings.push({
        line: selectedLine.value,
        plan_date: dateKey,
        final_process_start_time: setting.final_process_start_time,
        adjust_to_break_end: adjustToBreakEnd.value,
      })
    }
  })
  if (settings.length === 0) return
  try {
    await api.lineDailyScheduleSettings.bulkSaveLineDailyScheduleSettings(settings)
  } catch (e) {
    console.error('日別設定保存エラー', e)
    throw e
  }
}

const normalizeTimeInput = (value, padOnBlur = false) => {
  const raw = String(value || '').replace(/[^0-9]/g, '')
  if (!raw) return ''
  const digits = raw.slice(0, 4)
  if (digits.length <= 2) {
    const hours = digits
    return padOnBlur ? `${hours.padStart(2, '0')}:00` : hours
  }
  if (digits.length === 3) {
    const hours = digits.slice(0, 1)
    const mins = digits.slice(1, 3)
    return padOnBlur ? `${hours.padStart(2, '0')}:${mins}` : `${hours}:${mins}`
  }
  const hours = digits.slice(0, 2)
  const mins = digits.slice(2, 4)
  return `${hours}:${mins}`
}

const onDefaultTimeInput = (value, padOnBlur = false) => {
  finalProcessStartTime.value = normalizeTimeInput(value, padOnBlur)
}

</script>

<style scoped>
.hokushin-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hokushin-dialog {
  background: #fff;
  min-width: 360px;
  max-width: 480px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  padding: 20px 24px;
  font-family: "Noto Sans JP", "Segoe UI", Arial, sans-serif;
}
.hokushin-dialog-title {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: #1f2a44;
  border-bottom: 2px solid #C00000;
  padding-bottom: 6px;
}
.hokushin-dialog-text {
  font-size: 15px;
  line-height: 1.8;
  margin: 12px 0;
  color: #1f2a44;
}
.hokushin-dialog-text .hokushin-date {
  font-weight: 700;
  color: #C00000;
}
.hokushin-dialog-warn {
  background: #FFF3CD;
  border-left: 4px solid #FFC107;
  padding: 8px 12px;
  margin: 10px 0;
  font-size: 13px;
  color: #856404;
}
.hokushin-edit-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 10px 0;
  font-size: 14px;
}
.hokushin-edit-row label {
  min-width: 130px;
  color: #1f2a44;
}
.hokushin-edit-row input[type="date"] {
  padding: 4px 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.hokushin-dialog-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 18px;
}
.hokushin-dialog-actions .btn {
  padding: 6px 16px;
  border: 1px solid #ccc;
  background: #f5f5f5;
  color: #333;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.hokushin-dialog-actions .btn.primary {
  background: #C00000;
  color: #fff;
  border-color: #C00000;
  font-weight: 700;
}
.hokushin-dialog-actions .btn:hover {
  opacity: 0.88;
}

.plan-container {
  padding: 6px 8px 10px;
  background: #eef2f6;
  font-size: 13px;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  color: #1f2a44;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.tab-bar {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid #cbd5e1;
}
.tab-item {
  padding: 7px 14px;
  border: 1px solid #cbd5e1;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.tab-item.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}
.no-tab-placeholder {
  margin-top: 40px;
  text-align: center;
  color: #94a3b8;
  font-size: 15px;
}
.settings-panel {
  margin-top: 8px;
  padding: 14px;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  background: #fff;
}
.settings-title {
  margin: 0;
  font-size: 17px;
}
.settings-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-top: 10px;
  overflow: hidden;
}
.settings-section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f8fafc;
  font-weight: 600;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  user-select: none;
}
.settings-section-header:hover { background: #f1f5f9; }
.settings-section-arrow { font-size: 10px; color: #6b7280; width: 12px; }
.settings-section-count { margin-left: auto; font-weight: 400; font-size: 12px; color: #6b7280; }
.settings-section-body { padding: 8px 12px 12px; }
.settings-note {
  margin: 6px 0 12px;
  color: #64748b;
  font-size: 13px;
}
.settings-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.settings-selector label {
  font-size: 13px;
  font-weight: 700;
}
.settings-selector select {
  min-width: 160px;
  padding: 7px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
}
.settings-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 8px;
}
.settings-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.settings-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
.settings-rule-editor {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.settings-rule-editor select,
.settings-rule-editor input {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  padding: 6px 8px;
}
.settings-rules {
  margin-top: 6px;
  margin-bottom: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.settings-rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 1px solid #d7deea;
  border-radius: 6px;
  background: #f8fafc;
  padding: 6px 8px;
  font-size: 13px;
}
.settings-message {
  margin-top: 8px;
  color: #166534;
  font-size: 13px;
  font-weight: 700;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  padding: 6px;
  border-radius: 4px;
  position: relative;
}
.toolbar.collapsed {
  padding: 2px 6px;
  align-items: center;
}
.toolbar-toggle {
  position: absolute;
  top: 2px;
  right: 4px;
  width: 22px;
  height: 18px;
  font-size: 10px;
  line-height: 1;
  border: 1px solid #8aa0c0;
  background: #fff;
  border-radius: 3px;
  cursor: pointer;
  padding: 0;
  z-index: 2;
}
.toolbar-toggle:hover {
  background: #f0f4fa;
}
.toolbar.collapsed .toolbar-toggle {
  position: static;
}
.toolbar-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #1f2a44;
  font-weight: 600;
  flex: 1;
}
.toolbar-summary .summary-sep {
  color: #8aa0c0;
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
  gap: 2px;
}
.field.checkbox-field {
  justify-content: flex-end;
  padding-bottom: 4px;
}
.field.checkbox-field label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
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
.field input.input-narrow {
  min-width: unset;
  width: 110px;
}
.field select.select-narrow {
  min-width: unset;
  width: 55px;
  padding: 6px 0;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.grid-wrapper {
  margin-top: 6px;
  flex: 1;
  min-height: 200px;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.line-rule-notice {
  margin-top: 6px;
  padding: 6px 10px;
  border: 1px solid #f3d08a;
  background: #fff8e8;
  color: #7a4b00;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
}
.plan-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  --header-row1-height: 24px;
  --header-row2-height: 20px;
  --header-row3-height: 18px;
}
.plan-grid th,
.plan-grid td {
  border: 1px solid #a0aec0;
  padding: 2px 3px;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 500;
  color: #000;
}
.lot-stack {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.lot-item {
  display: flex;
  gap: 4px;
  align-items: center;
}
.lot-item-vertical {
  flex-direction: column;
  gap: 1px;
  align-items: flex-end;
}
.lot-item-vertical .lot-remove {
  padding: 0;
}
.lot-add,
.lot-remove {
  padding: 2px 6px;
  font-size: 11px;
  line-height: 1;
}
.plan-grid th {
  font-weight: 700;
}
.plan-grid thead th {
  position: sticky;
  top: 0;
  z-index: 4;
}
.plan-grid thead tr.head-level1 th {
  top: 0;
  height: var(--header-row1-height);
  padding: 0 4px;
}
.plan-grid thead tr.head-level1b th {
  top: calc(var(--header-row1-height) - 1px);
  height: var(--header-row2-height);
  padding: 0;
}
.plan-grid thead tr.head-level2 th {
  top: calc(var(--header-row1-height) + var(--header-row2-height) - 2px);
  height: var(--header-row3-height);
  padding: 0;
  position: sticky;
}
.plan-grid thead tr.head-level2 th::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100%;
  height: 2px;
  background: #000;
}
.plan-grid thead th.sticky-col {
  z-index: 8;
}
.plan-grid thead tr.head-level1 th {
  background: #cfd8ec;
}
.plan-grid thead tr.head-level1b th {
  background: #cfd8ec;
}
.plan-grid thead tr.head-level2 th {
  background: #e7edf7;
}
.day-plan-total {
  font-weight: 700;
  font-size: 11px;
  color: #c00;
  margin-left: auto;
}
.day-plan-avg {
  font-size: 11px;
  font-weight: 700;
  color: #000;
}
.plan-grid thead th.sat {
  background: #ffe8cc;
}
.plan-grid thead th.sun {
  background: #ffd6d6;
}
thead tr.head-level1 th.sticky-col {
  background: #cfd8ec;
}
thead tr.head-level2 th.sticky-col {
  background: #e7edf7;
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
  /* min-widthを削除して自然な幅に */
}
.date-header-content-horizontal {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.date-label {
  font-weight: 700;
  font-size: 11px;
  white-space: nowrap;
}
.work-time-label {
  font-size: 11px;
  color: #000;
  white-space: nowrap;
}
.time-input-inline {
  padding: 0 2px;
  font-size: 11px;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  height: 16px;
  width: 45px;
  min-width: 45px;
  max-width: 45px;
  text-align: center;
  color: #15803d;
  -webkit-text-fill-color: #15803d;
  flex-shrink: 0;
  box-sizing: border-box;
}
.time-input-inline::placeholder {
  color: #15803d;
  opacity: 1;
}
.btn-day-apply {
  padding: 0 4px;
  font-size: 11px;
  line-height: 1.4;
  border: 1px solid #60a5fa;
  border-radius: 3px;
  background: #fff;
  color: #2563eb;
  cursor: pointer;
  flex-shrink: 0;
  font-weight: 700;
}
.btn-day-apply:hover:not(:disabled) {
  background: #dbeafe;
}
.btn-day-apply:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-day-clear {
  padding: 0 4px;
  font-size: 11px;
  line-height: 1.4;
  border: 1px solid #f87171;
  border-radius: 3px;
  background: #fff;
  color: #dc2626;
  cursor: pointer;
  flex-shrink: 0;
}
.btn-day-clear:hover:not(:disabled) {
  background: #fee2e2;
}
.btn-day-clear:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-day-plus {
  padding: 0 4px;
  font-size: 11px;
  line-height: 1.4;
  border: 1px solid #22c55e;
  border-radius: 3px;
  background: #ecfdf5;
  color: #15803d;
  cursor: pointer;
  flex-shrink: 0;
  font-weight: 700;
}
.btn-day-plus:hover:not(:disabled) {
  background: #dcfce7;
}
.btn-day-plus:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.plan-grid th.mini {
  text-align: center;
  font-size: 11px;
  min-width: 40px;
}
.plan-grid .mini.demand-col,
.plan-grid .mini.actual-col,
.plan-grid .mini.stock-col,
.plan-grid .mini.plan-col,
.plan-grid .mini.stock-plan-col {
  min-width: 40px;
}
.plan-grid .mini.sequence-col {
  min-width: 25px !important;
  width: 25px !important;
  max-width: 25px !important;
}
.day-end {
  border-right: 3px solid #000 !important;
}
.week-gap {
  width: 6px !important;
  min-width: 6px !important;
  max-width: 6px !important;
  background: #f8a0a0 !important;
  border-left: none !important;
  border-right: none !important;
  padding: 0 !important;
}
.sticky-col {
  position: sticky;
  left: 0;
  background: #f8fafc;
  z-index: 3;
}
thead .sticky-col {
  z-index: 8;
}
.number-col {
  width: 30px;
  min-width: 30px;
  max-width: 30px;
  text-align: center;
  position: sticky;
}
.number-col::after {
  content: '';
  position: absolute;
  top: 0;
  right: -1px;
  width: 1px;
  height: 100%;
  background: #999;
  z-index: 9;
}
.code-col {
  left: 30px;
  width: 135px;
  min-width: 135px;
  max-width: 135px;
  position: sticky;
}
.code-col::after {
  content: '';
  position: absolute;
  top: 0;
  right: -1px;
  width: 1px;
  height: 100%;
  background: #999;
  z-index: 9;
}
.name-col {
  left: 165px;
  width: 100px;
  min-width: 100px;
  max-width: 100px;
  border-right: none !important;
  position: sticky;
}
.name-col::after {
  content: '';
  position: absolute;
  top: 0;
  right: -2px;
  width: 2px;
  height: 100%;
  background: #000;
  z-index: 9;
}
.plan-grid tbody td.code-col {
  padding: 0 !important;
  text-align: left;
}
.plan-grid tbody td.code-col .product-info {
  padding: 0;
  text-align: left;
}
.plan-grid tbody td.name-col {
  padding: 0 !important;
}
.plan-grid tbody td.name-col .product-info {
  padding: 0;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  word-break: break-all;
  font-size: 11px;
  line-height: 1.15;
  text-align: center;
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
.plan-grid input.locked {
  background: #f1f5f9;
  color: #666;
  cursor: not-allowed;
}
.plan-grid tbody tr td {
  border-top: 1px solid #000;
  border-bottom: 1px solid #000;
}
.plan-grid tbody tr.active-input-row td {
  background: #fff7cf;
}
.plan-grid tbody tr.active-input-row td.sticky-col {
  background: #ffef9c;
}
.plan-grid tbody td.num.plan {
  padding: 0 !important;
}
.plan-grid tbody td.num.plan .lot-stack {
  height: 100%;
  gap: 0;
}
.plan-grid tbody td.num.plan .lot-item {
  gap: 0;
  border-top: 1px solid #d7dfe8;
}
.plan-grid tbody td.num.plan input {
  border: 0;
  border-radius: 0;
  padding: 0 4px;
  margin: 0;
  min-height: 24px;
  background: transparent;
}
.plan-grid tbody td.num.plan .lot-add {
  width: 100%;
  height: 20px;
  padding: 0 4px;
  margin: 0;
  border: 0;
  border-top: 1px solid #d7dfe8;
  border-radius: 0;
  background: transparent;
  text-align: left;
}
.plan-grid tbody td.num.sequence {
  padding: 0 !important;
}
.plan-grid tbody td.num.sequence input {
  padding: 0 4px;
}
.num {
  text-align: right;
  min-width: 80px; /* セル幅を広げて日付列が潰れないようにする */
}
.num.demand,
.num.actual,
.num.stock,
.num.plan,
.num.stock-plan {
  min-width: 40px;
}
.num.sequence {
  min-width: 25px;
  width: 25px;
  max-width: 25px;
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
.readonly-value.negative {
  color: #c00000;
  font-weight: 700;
}
.stock {
  background: #f7f9fb;
  font-family: Consolas, "Courier New", monospace;
}
.stock .readonly-value.negative {
  color: #b8860b;
}
.plan {
  background: #fffbe6;
}
.sequence {
  background: #e0f2fe;
}
.stock-plan {
  background: #f1f7ff;
  padding-right: 0.5px !important;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.plan-grid tbody tr[style] td:not(.week-gap) {
  background: inherit !important;
  color: inherit !important;
}
.plan-grid tbody tr[style] td.day-end {
  border-right: 3px solid #000 !important;
}
.plan-grid tbody tr[style] td.sticky-col {
  background: inherit !important;
  color: inherit !important;
}
.no-data {
  text-align: center;
  color: #888;
  padding: 10px 0;
}
.footer-actions {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  align-items: center;
  flex-wrap: wrap;
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
.footer-gantt-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.footer-gantt-label {
  font-size: 12px;
  font-weight: 700;
  color: #374151;
}
.footer-mode-btn.active {
  background: #2563eb;
  color: #fff;
  border-color: #1d4ed8;
}
.footer-gantt-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #111827;
}
.footer-gantt-save-btn {
  font-weight: 700;
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
.header-readonly-btn:disabled {
  background: #fff !important;
  color: #374151;
  border-color: #b5c1d2;
}
.cursor-product-bubble {
  position: fixed;
  z-index: 1200;
  pointer-events: none;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fde68a;
  border: 1px solid #d97706;
  color: #7c2d12;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
}


.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.modal-content {
  background: #fff;
  border-radius: 6px;
  width: 420px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
.modal-content h2 {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 700;
}
.modal-content textarea {
  width: 100%;
  resize: vertical;
  min-height: 90px;
  padding: 8px;
  border: 1px solid #cfd6e1;
  border-radius: 4px;
  font-size: 12px;
  font-family: inherit;
}
.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.export-modal h2 {
  margin-bottom: 6px;
}
.export-note {
  font-size: 12px;
  color: #4b5563;
  margin: 0 0 12px;
  line-height: 1.5;
}
.export-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.process-section {
  margin-top: 8px;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 8px 10px;
}
.process-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.process-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.process-title {
  font-weight: 700;
  font-size: 14px;
}
.process-title-inline {
  margin-left: 8px;
  font-weight: 600;
  color: #111827;
}
.process-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.gantt-save-btn {
  min-height: 64px;
  font-weight: 700;
}
.gantt-save-btn.gantt-save-dirty {
  background: #dc2626;
  color: #fff;
  border-color: #b91c1c;
}
.footer-gantt-save-btn.gantt-save-dirty {
  background: #dc2626;
  color: #fff;
  border-color: #b91c1c;
}
.gantt-save-btn.gantt-save-dirty:hover {
  background: #b91c1c;
}
.footer-gantt-save-btn.gantt-save-dirty:hover {
  background: #b91c1c;
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
.process-meta {
  color: #111827;
  font-size: 13px;
  white-space: nowrap;
}
.gantt-section {
  margin-top: 6px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.load-section {
  margin-top: 6px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.load-body {
  min-height: 40px;
}
.load-message {
  color: #6b7280;
  font-size: 12px;
  padding: 6px 0;
}
.load-table-wrap {
  overflow-x: auto;
}
.load-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.load-table th,
.load-table td {
  border: 1px solid #d7dfe8;
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
  color: #000;
  text-align: center;
}
.load-table thead th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: #e7edf7;
}
.load-process-col {
  width: 180px;
  min-width: 180px;
  max-width: 180px;
  border-right: 2px solid #b5c1d2 !important;
  text-align: left;
}
.laser-subtab-bar {
  display: flex;
  gap: 6px;
  margin: 8px 0;
}
.laser-subtab-item {
  border: 1px solid #b9c5d6;
  background: #f8fafc;
  color: #1f2937;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.laser-subtab-item.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}
.laser-subtab-item.manual-btn {
  margin-left: auto;
  background: #e8f5e9;
  border-color: #4caf50;
  color: #2e7d32;
}
.laser-editor-section {
  margin-top: 8px;
}
.laser-third-tab-panel {
  margin-top: 8px;
  border: 1px solid #d7dfe8;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  padding: 16px;
  font-size: 13px;
}
.laser-summary-section {
  margin-top: 8px;
}
.spot-excel-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.spot-file-btn {
  position: relative;
  overflow: hidden;
}
.spot-file-btn input[type='file'] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.spot-excel-note {
  margin-top: 8px;
}
.spot-excel-meta {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.spot-excel-errors {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 8px;
}
.spot-excel-error-card {
  border: 1px solid #fecaca;
  background: #fff1f2;
  border-radius: 6px;
  padding: 8px 10px;
}
.spot-excel-error-title {
  font-weight: 700;
  color: #991b1b;
  margin-bottom: 4px;
}
.spot-excel-error-card ul {
  margin: 0;
  padding-left: 18px;
  max-height: 120px;
  overflow: auto;
}
.spot-excel-table-wrap {
  margin-top: 8px;
  max-height: 420px;
  overflow: auto;
  border: 1px solid #d7dfe8;
}
.spot-excel-table {
  width: 100%;
  border-collapse: collapse;
}
.spot-excel-table th,
.spot-excel-table td {
  border: 1px solid #d7dfe8;
  padding: 6px 8px;
  white-space: nowrap;
}
.spot-excel-table thead th {
  position: sticky;
  top: 0;
  background: #e7edf7;
  z-index: 2;
}
.processing-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  pointer-events: all;
}
.processing-box {
  background: #1f2a44;
  color: #fff;
  padding: 18px 28px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  text-align: center;
  min-width: 240px;
}
.processing-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.processing-sub {
  margin: 6px 0 0;
  font-size: 13px;
  opacity: 0.9;
}
.cart-summary-row {
  background: #f0f4ff !important;
  border-top: 2px solid #7a8bb5;
}
.cart-summary-row td {
  font-weight: 700;
  font-size: 12px;
}
.cart-summary-row .cart-label {
  text-align: left;
  white-space: nowrap;
  background: #e0e8f5 !important;
}
.cart-summary-row .cart-value {
  text-align: right;
  font-size: 13px;
  color: #1a3a6a;
}
.recalc-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.recalc-modal {
  background: #fff;
  border: 3px solid #c62828;
  border-radius: 10px;
  padding: 28px 32px;
  max-width: 520px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.25);
}
.recalc-warning-text {
  color: #c62828;
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.8;
}
.recalc-warning-text p:first-child {
  font-size: 1.4rem;
  margin-bottom: 8px;
}
.recalc-warning-text ul {
  margin: 0 0 12px 20px;
  padding: 0;
}
.recalc-warning-text li {
  margin-bottom: 4px;
}
.recalc-modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
.ds-btn { margin-left: 8px; padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-btn:hover { background: #e2e8f0; }
.ds-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.ds-modal { background: #fff; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.2); max-width: 700px; width: 90%; max-height: 80vh; overflow: auto; }
.ds-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #e5e7eb; }
.ds-header h3 { margin: 0; font-size: 15px; }
.ds-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #64748b; }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th, .ds-table td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.ds-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.ds-table td:first-child { white-space: nowrap; font-weight: 500; color: #2563eb; }
.ds-table td:nth-child(2) { font-family: monospace; font-size: 12px; color: #0f172a; }
</style>
