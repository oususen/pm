<template>
  <section class="weekly-plan">
    <div class="toolbar">
      <label
        >週開始日<input
          v-model="startDate"
          type="date"
          @change="confirmLoadPlan" /></label
      ><span>後工程計画をLT日数だけ前倒しして算出。TK=1号機、AJ=2号機。</span
      ><button class="btn" @click="showSettings = !showSettings">
        対象設定</button
      ><button class="btn" @click="openSaveDialog" :disabled="saving">
        {{ saving ? "保存中..." : "手回数を保存" }}</button
      ><button class="btn" @click="openPrintDialog">印刷</button
      ><button class="btn" @click="openResetDialog">手数リセット</button
      ><button class="btn primary" @click="confirmLoadPlan">計画・材料再計算</button
      ><span v-if="message" class="toolbar-message">{{ message }}</span>
    </div>
    <div
      v-if="showPrintDialog"
      class="print-modal"
      @click.self="showPrintDialog = false"
    >
      <section class="print-dialog">
        <h3>合計表を印刷</h3>
        <div class="print-date-fields">
          <label>開始日<input v-model="printStartDate" type="date" /></label
          ><label>終了日<input v-model="printEndDate" type="date" /></label>
        </div>
        <div class="print-date-fields">
          <label
            >向き<select v-model="printOrientation" style="width: 80px">
              <option value="landscape">横</option>
              <option value="portrait">縦</option>
            </select></label
          >
        </div>
        <div class="print-actions">
          <button class="btn primary" @click="printSummary">印刷</button
          ><button class="btn" @click="showPrintDialog = false">
            キャンセル
          </button>
        </div>
      </section>
    </div>
    <div
      v-if="showResetDialog"
      class="print-modal"
      @click.self="showResetDialog = false"
    >
      <section class="print-dialog">
        <h3>手回数をリセット</h3>
        <p style="font-size:12px;color:#666;margin:0 0 8px">指定期間の保存済み手回数を削除し、自数と同じ初期値に戻します。</p>
        <div class="print-date-fields">
          <label>開始日<input v-model="resetStartDate" type="date" /></label
          ><label>終了日<input v-model="resetEndDate" type="date" /></label>
        </div>
        <div class="print-actions">
          <button class="btn" style="background:#c53030;color:#fff" @click="executeReset">リセット</button
          ><button class="btn" @click="showResetDialog = false">キャンセル</button>
        </div>
      </section>
    </div>
    <div
      v-if="showSaveDialog"
      class="print-modal"
      @click.self="showSaveDialog = false"
    >
      <section class="print-dialog">
        <h3>手回数を保存</h3>
        <div style="display:flex;gap:4px;margin-bottom:8px">
          <button
            v-for="(week, idx) in weekGroups"
            :key="week.key"
            class="btn"
            :class="{ primary: saveWeekKey === week.key }"
            @click="selectSaveWeek(week, idx)"
          >{{ idx + 1 }}週目</button>
          <button
            class="btn"
            :class="{ primary: saveWeekKey === 'all' }"
            @click="selectSaveWeek(null)"
          >全期間</button>
        </div>
        <div class="print-actions">
          <button class="btn primary" @click="saveManualQuantities" :disabled="saving">
            {{ saving ? "保存中..." : "保存" }}
          </button
          ><button class="btn" @click="showSaveDialog = false">キャンセル</button>
        </div>
      </section>
    </div>
    <div v-if="saving" class="save-overlay">
      <div class="save-progress">
        <div class="save-bar"></div>
        <span>保存中...</span>
      </div>
    </div>
    <div v-if="showSettings" class="settings">
      <h3>
        週間計画対象設定
        <button
          class="btn"
          @click="exportTargetsExcel"
          style="margin-left: 8px; font-size: 12px"
        >
          Excel出力
        </button>
      </h3>
      <div class="form">
        <label
          >後工程ライン<select
            v-model="form.downstream_line"
            @change="onDownstreamLineChange"
          >
            <option :value="null">選択</option>
            <option v-for="x in lines" :key="x.id" :value="x.id">
              {{ x.line_code }} {{ x.line_name }}
            </option>
          </select></label
        ><label
          >後工程製品番号<select
            v-model="form.product"
            :disabled="!form.downstream_line"
          >
            <option :value="null">
              {{ form.downstream_line ? "選択" : "先に後工程ラインを選択" }}
            </option>
            <option v-for="x in downstreamProducts" :key="x.id" :value="x.id">
              {{ x.product_code }} {{ x.product_name }}
            </option>
          </select></label
        ><label
          >レーザ完成品番号<select
            v-model="form.finished_product"
            @change="selectAllPatterns"
          >
            <option :value="null">選択</option>
            <option
              v-for="x in laserFinishedProducts"
              :key="x.id"
              :value="x.id"
            >
              {{ x.product_code }} {{ x.product_name }}
            </option>
          </select></label
        ><label
          >レーザパターン<select
            v-model="selectedPatternIds"
            multiple
            :disabled="!form.finished_product"
          >
            <option v-for="x in filteredPatterns" :key="x.id" :value="x.id">
              {{ x.pattern_no }}
            </option>
          </select></label
        ><label
          >後工程数量取得元<select v-model="form.quantity_source">
            <option value="ORDER_QTY">後工程需要（order_qty）</option>
            <option value="PLAN_QTY">後工程計画（plan_qty）</option>
          </select></label
        ><label
          >LT(日)<input
            v-model.number="form.lead_time_days"
            min="0"
            type="number" /></label
        ><button class="btn primary" @click="saveTarget">
          {{ form.id ? "更新" : "追加" }}</button
        ><button class="btn" @click="reset">クリア</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>後工程ライン</th>
            <th>後工程製品</th>
            <th>パターン</th>
            <th>レーザ完成品</th>
            <th>取得元</th>
            <th>LT</th>
            <th>加工頻度</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="x in targets" :key="x.id">
            <td>{{ x.downstream_line_name }}</td>
            <td>{{ x.product_code }} {{ x.product_name }}</td>
            <td>{{ x.pattern_no }}</td>
            <td>{{ x.finished_product_code }}</td>
            <td>
              {{
                x.quantity_source === "PLAN_QTY" ? "後工程計画" : "後工程需要"
              }}
            </td>
            <td>{{ x.lead_time_days }}</td>
            <td>{{ x.freq_pattern_name || "毎日" }}</td>
            <td>
              <button @click="edit(x)">編集</button
              ><button @click="remove(x)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <h3 class="collapsible-header" @click="showDetail = !showDetail">
      {{ showDetail ? "▼" : "▶" }} 製品別明細
    </h3>
    <div v-show="showDetail">
      <div class="summary-filters">
        <label>後工程<select v-model="filterDetailDownstream">
          <option value="">全て</option>
          <option v-for="name in filterDetailDownstreamOptions" :key="name" :value="name">{{ name }}</option>
        </select></label>
        <label>設備<select v-model="filterDetailMachine">
          <option value="">全て</option>
          <option value="TK">1号機</option>
          <option value="AJ">2号機</option>
        </select></label>
        <label>製品番号<select v-model="filterDetailProductCode">
          <option value="">全て</option>
          <option v-for="code in filterDetailProductOptions" :key="code" :value="code">{{ code }}</option>
        </select></label>
        <label>パターン<select v-model="filterDetailPatternNo">
          <option value="">全て</option>
          <option v-for="no in filterDetailPatternOptions" :key="no" :value="String(no)">{{ no }}</option>
        </select></label>
      </div>
      <div class="grid">
      <table class="plan-table">
        <colgroup>
          <col
            v-for="(width, index) in fixedColumnWidths"
            :key="`fixed-${index}`"
            :style="{ width }"
          />
          <template v-for="week in weekGroups" :key="`columns-${week.key}`"
            ><template v-for="day in week.days" :key="`columns-${day}`"
              ><col class="demand-column" />
              <col class="automatic-column" />
              <col class="manual-column"
            /></template>
            <col class="week-total-column" />
            <col class="week-total-column" />
            <col class="week-total-column"
          /></template>
        </colgroup>
        <thead>
          <tr>
            <th v-for="column in fixedColumns" :key="column" rowspan="3">
              {{ column }}
            </th>
            <template v-for="week in weekGroups" :key="`dates-${week.key}`"
              ><th v-for="day in week.days" :key="day" colspan="3">
                {{ day.slice(5) }}
              </th>
              <th class="week-total" colspan="3">週合計</th></template
            >
          </tr>
          <tr>
            <template v-for="week in weekGroups" :key="`totals-${week.key}`"
              ><th v-for="day in week.days" :key="`total-${day}`" colspan="3">
                1号 {{ hours(day, "TK") }}h / 2号 {{ hours(day, "AJ") }}h
              </th>
              <th class="week-total" colspan="3">
                1号 {{ weeklyHours(week, "TK") }}h / 2号
                {{ weeklyHours(week, "AJ") }}h
              </th></template
            >
          </tr>
          <tr>
            <template v-for="week in weekGroups" :key="`labels-${week.key}`"
              ><template v-for="day in week.days" :key="`labels-${day}`"
                ><th>需要</th>
                <th>自回数</th>
                <th>手回数</th></template
              >
              <th class="week-total">需要</th>
              <th class="week-total">自回数</th>
              <th class="week-total">手回数</th></template
            >
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filteredRows"
            :key="row.id"
            :class="`product-group-${productGroup(row.product_code)}`"
          >
            <td>{{ row.downstream_line_name }}</td>
            <td>{{ number(row.take_qty, 0) }}</td>
            <td>{{ number(row.hours_per_sheet, 2) }}</td>
            <td>{{ row.lead_time_days }}</td>
            <td>{{ number(row.thickness, 1) }}</td>
            <td>{{ row.product_code }}</td>
            <td>{{ row.pattern_no }}</td>
            <td>{{ row.machine === "TK" ? "1号" : "2号" }}</td>
            <template v-for="week in weekGroups" :key="`${row.id}-${week.key}`"
              ><template v-for="day in week.days" :key="`${row.id}-${day}`"
                ><td>{{ number(dailyValue(row, day, "demand_qty"), 0) }}</td>
                <td
                  :class="{
                    'smaller-val': isSmallerValue(
                      dailyValue(row, day, 'automatic_sheets'),
                      dailyValue(row, day, 'manual_sheets'),
                    ),
                  }"
                >
                  {{
                    number(
                      dailyValue(row, day, "automatic_sheets"),
                      autoDigits(dailyValue(row, day, "automatic_sheets")),
                    )
                  }}
                </td>
                <td
                  :class="{
                    'smaller-val': isSmallerValue(
                      dailyValue(row, day, 'manual_sheets'),
                      dailyValue(row, day, 'automatic_sheets'),
                    ),
                  }"
                >
                  {{ dailyValue(row, day, "manual_sheets") }}
                </td></template
              >
              <td class="week-total">
                {{ number(weeklyValue(row, week, "demand_qty"), 0) }}
              </td>
              <td
                class="week-total"
                :class="{
                  'smaller-val': isSmallerValue(
                    weeklyValue(row, week, 'automatic_sheets'),
                    weeklyValue(row, week, 'manual_sheets'),
                  ),
                }"
              >
                {{
                  number(
                    weeklyValue(row, week, "automatic_sheets"),
                    autoDigits(weeklyValue(row, week, "automatic_sheets")),
                  )
                }}
              </td>
              <td
                class="week-total"
                :class="{
                  'smaller-val': isSmallerValue(
                    weeklyValue(row, week, 'manual_sheets'),
                    weeklyValue(row, week, 'automatic_sheets'),
                  ),
                }"
              >
                {{ weeklyValue(row, week, "manual_sheets") }}
              </td></template
            >
          </tr>
          <tr v-if="!filteredRows.length">
            <td :colspan="gridColumnCount">対象設定を追加してください。</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>
    <section class="pattern-summary-grid">
      <h3 class="collapsible-header" @click="showSummary = !showSummary">
        {{ showSummary ? "▼" : "▶" }} レーザ加工計画（パターン別合計）
      </h3>
      <div v-show="showSummary">
        <div class="summary-filters">
          <label>後工程<select v-model="filterDownstream">
            <option value="">全て</option>
            <option v-for="name in filterDownstreamOptions" :key="name" :value="name">{{ name }}</option>
          </select></label>
          <label>設備<select v-model="filterMachine">
            <option value="">全て</option>
            <option value="TK">1号機</option>
            <option value="AJ">2号機</option>
          </select></label>
          <label>製品番号<select v-model="filterProductCode">
            <option value="">全て</option>
            <option v-for="code in filterProductOptions" :key="code" :value="code">{{ code }}</option>
          </select></label>
          <label>板厚<select v-model="filterThickness">
            <option value="">全て</option>
            <option v-for="t in filterThicknessOptions" :key="t" :value="t">{{ t }}</option>
          </select></label>
          <label>パターン<select v-model="filterPatternNo">
            <option value="">全て</option>
            <option v-for="no in filterPatternOptions" :key="no" :value="String(no)">{{ no }}</option>
          </select></label>
        </div>
        <div class="pattern-summary-scroll">
        <table class="pattern-summary-table">
          <colgroup>
            <col
              v-for="(width, index) in summaryColumnWidths"
              :key="`summary-fixed-${index}`"
              :style="{ width }"
            />
            <template
              v-for="week in weekGroups"
              :key="`summary-columns-${week.key}`"
              ><template
                v-for="day in week.days"
                :key="`summary-columns-${day}`"
                ><col class="demand-column" />
                <col class="automatic-column" />
                <col class="manual-column" />
                <col class="progress-column"
              /></template>
              <col class="week-total-column" />
              <col class="week-total-column" />
              <col class="week-total-column" />
              <col class="week-total-column"
            /></template>
          </colgroup>
          <thead>
            <tr>
              <th v-for="column in summaryColumns" :key="column" rowspan="3">
                {{ column }}
              </th>
              <template
                v-for="week in weekGroups"
                :key="`summary-dates-${week.key}`"
                ><th
                  v-for="day in week.days"
                  :key="`summary-date-${day}`"
                  colspan="4"
                >
                  {{ day.slice(5) }}
                </th>
                <th class="week-total" colspan="4">週合計</th></template
              >
            </tr>
            <tr>
              <template
                v-for="week in weekGroups"
                :key="`summary-totals-${week.key}`"
                ><th
                  v-for="day in week.days"
                  :key="`summary-total-${day}`"
                  colspan="4"
                >
                  1号 {{ hours(day, "TK") }}h / 2号 {{ hours(day, "AJ") }}h
                </th>
                <th class="week-total" colspan="4">
                  1号 {{ weeklyHours(week, "TK") }}h / 2号
                  {{ weeklyHours(week, "AJ") }}h
                </th></template
              >
            </tr>
            <tr>
              <template
                v-for="week in weekGroups"
                :key="`summary-labels-${week.key}`"
                ><template
                  v-for="day in week.days"
                  :key="`summary-label-${day}`"
                  ><th>需要</th>
                  <th>自数</th>
                  <th>手数</th>
                  <th>進度</th></template
                >
                <th class="week-total">需要</th>
                <th class="week-total">自数</th>
                <th class="week-total">手数</th>
                <th class="week-total">進度</th></template
              >
            </tr>
          </thead>
          <tbody>
            <template v-for="pattern in filteredPatternRows" :key="pattern.pattern_no"
              ><tr
                :class="`summary-product-${summaryProductGroup(pattern.representative_product_code)}`"
              >
                <td>{{ pattern.downstream_line_names.join(" / ") }}</td>
                <td>
                  {{
                    pattern.take_qtys.map((qty) => number(qty, 0)).join(" / ")
                  }}
                </td>
                <td>{{ number(pattern.hours_per_sheet, 2) }}</td>
                <td>{{ pattern.lead_time_days.join(" / ") }}</td>
                <td>{{ number(pattern.thickness, 1) }}</td>
                <td>{{ pattern.representative_product_code }}</td>
                <td>{{ pattern.pattern_no }}</td>
                <td>{{ pattern.machine === "TK" ? "1号" : "2号" }}</td>
                <td class="initial-progress-cell">
                  <input
                    class="initial-progress-input"
                    v-model.number="pattern.initial_progress"
                    type="number"
                    step="0.01"
                    :disabled="pattern.initial_progress_locked"
                    @input="dirty = true"
                  /><button
                    class="lock-btn"
                    :class="{ locked: pattern.initial_progress_locked }"
                    @click="toggleLock(pattern)"
                  >
                    {{ pattern.initial_progress_locked ? "固定" : "入力" }}
                  </button>
                </td>
                <template
                  v-for="week in weekGroups"
                  :key="`${pattern.pattern_no}-${week.key}`"
                  ><template
                    v-for="day in week.days"
                    :key="`${pattern.pattern_no}-${day}`"
                    ><td>
                      {{
                        number(patternDailyValue(pattern, day, "demand_qty"), 0)
                      }}
                    </td>
                    <td
                      :class="{
                        'smaller-val': isSmallerValue(
                          patternDailyValue(pattern, day, 'automatic_sheets'),
                          patternDailyValue(pattern, day, 'manual_sheets'),
                        ),
                      }"
                    >
                      {{
                        patternDailyValue(pattern, day, "automatic_sheets") === 0
                          ? ''
                          : number(
                              patternDailyValue(pattern, day, "automatic_sheets"),
                              autoDigits(
                                patternDailyValue(pattern, day, "automatic_sheets"),
                              ),
                            )
                      }}
                    </td>
                    <td
                      class="manual-sheets-cell"
                      :class="{
                        'smaller-val': isSmallerValue(
                          patternDailyValue(pattern, day, 'manual_sheets'),
                          patternDailyValue(pattern, day, 'automatic_sheets'),
                        ),
                      }"
                      :data-tip="`${pattern.representative_product_code} t${number(pattern.thickness, 1)} ${pattern.machine === 'TK' ? '1号機' : '2号機'}`"
                      :data-force-key="`${pattern.laser_pattern_id}_${day}`"
                      @dblclick="forceShowInput(pattern, day)"
                    >
                      <input
                        v-if="patternDailyValue(pattern, day, 'automatic_sheets') !== 0 || patternDailyValue(pattern, day, 'manual_sheets') !== 0 || forcedInputCells.has(`${pattern.laser_pattern_id}_${day}`)"
                        class="manual-sheets"
                        v-model.number="pattern.daily[day].manual_sheets"
                        min="0"
                        step="1"
                        type="number"
                        @input="dirty = true"
                        @focus="$event.target.select()"
                      />
                    </td>
                    <td
                      class="progress-cell"
                      :class="progressClass(patternProgressDisplayRaw(pattern, day))"
                    >
                      {{ patternProgress(pattern, day) }}
                    </td></template
                  >
                  <td class="week-total">
                    {{
                      number(patternWeeklyValue(pattern, week, "demand_qty"), 0)
                    }}
                  </td>
                  <td
                    class="week-total"
                    :class="{
                      'smaller-val': isSmallerValue(
                        patternWeeklyValue(pattern, week, 'automatic_sheets'),
                        patternWeeklyValue(pattern, week, 'manual_sheets'),
                      ),
                    }"
                  >
                    {{
                      number(
                        patternWeeklyValue(pattern, week, "automatic_sheets"),
                        autoDigits(
                          patternWeeklyValue(pattern, week, "automatic_sheets"),
                        ),
                      )
                    }}
                  </td>
                  <td
                    class="week-total"
                    :class="{
                      'smaller-val': isSmallerValue(
                        patternWeeklyValue(pattern, week, 'manual_sheets'),
                        patternWeeklyValue(pattern, week, 'automatic_sheets'),
                      ),
                    }"
                  >
                    {{ patternWeeklyValue(pattern, week, "manual_sheets") }}
                  </td>
                  <td
                    class="week-total progress-cell"
                    :class="
                      progressClass(
                        patternProgressDisplayRaw(
                          pattern,
                          week.days[week.days.length - 1],
                        ),
                      )
                    "
                  >
                    {{
                      patternProgress(pattern, week.days[week.days.length - 1])
                    }}
                  </td></template
                >
              </tr></template
            >
            <tr v-if="!filteredPatternRows.length">
              <td :colspan="summaryGridColumnCount">
                対象設定を追加してください。
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </section>
    <section class="material-grid">
      <h3
        class="collapsible-header"
        @click="showMaterialSheets = !showMaterialSheets"
      >
        {{ showMaterialSheets ? "▼" : "▶" }} 日別材料必要枚数
      </h3>
      <div v-show="showMaterialSheets">
        <table class="material-table material-weekly">
          <thead>
            <tr>
              <th>材料コード</th>
              <th>材料名</th>
              <th>板厚</th>
              <template
                v-for="week in weekGroups"
                :key="`material-week-${week.key}`"
                ><th v-for="day in week.days" :key="`material-${day}`">
                  {{ day.slice(5) }}
                </th>
                <th class="week-total">週合計</th></template
              >
            </tr>
          </thead>
          <tbody>
            <tr v-for="material in materialRows" :key="material.material_id">
              <td>{{ material.material_code }}</td>
              <td>{{ material.material_name }}</td>
              <td>{{ number(material.thickness, 1) }}</td>
              <template
                v-for="week in weekGroups"
                :key="`${material.material_id}-week-${week.key}`"
                ><td
                  v-for="day in week.days"
                  :key="`${material.material_id}-${day}`"
                >
                  {{
                    number(
                      material.daily[day] ?? 0,
                      autoDigits(material.daily[day]),
                    )
                  }}
                </td>
                <td class="week-total">
                  {{
                    number(
                      materialWeeklyValue(material, week),
                      autoDigits(materialWeeklyValue(material, week)),
                    )
                  }}
                </td></template
              >
            </tr>
            <tr v-if="!materialRows.length">
              <td :colspan="3 + days.length + weekGroups.length">
                材料対象の週間計画がありません。
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="material-grid">
      <h3
        class="collapsible-header"
        @click="showMaterialLots = !showMaterialLots"
      >
        {{ showMaterialLots ? "▼" : "▶" }} 日別材料必要ロット数
      </h3>
      <div v-show="showMaterialLots">
        <table class="material-table material-weekly">
          <thead>
            <tr>
              <th>材料コード</th>
              <th>材料名</th>
              <th>発注倍数</th>
              <template v-for="week in weekGroups" :key="`lot-week-${week.key}`"
                ><th v-for="day in week.days" :key="`lot-${day}`">
                  {{ day.slice(5) }}
                </th>
                <th class="week-total">週合計</th></template
              >
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="material in materialRows"
              :key="`lot-${material.material_id}`"
            >
              <td>{{ material.material_code }}</td>
              <td>{{ material.material_name }}</td>
              <td>{{ material.order_lot_multiple }}</td>
              <template
                v-for="week in weekGroups"
                :key="`lot-${material.material_id}-week-${week.key}`"
                ><td
                  v-for="day in week.days"
                  :key="`lot-${material.material_id}-${day}`"
                >
                  {{
                    number(
                      lotQty(
                        material.daily[day] ?? 0,
                        material.order_lot_multiple,
                      ),
                      autoDigits(
                        lotQty(
                          material.daily[day] ?? 0,
                          material.order_lot_multiple,
                        ),
                      ),
                    )
                  }}
                </td>
                <td class="week-total">
                  {{
                    number(
                      lotQty(
                        materialWeeklyValue(material, week),
                        material.order_lot_multiple,
                      ),
                      autoDigits(
                        lotQty(
                          materialWeeklyValue(material, week),
                          material.order_lot_multiple,
                        ),
                      ),
                    )
                  }}
                </td></template
              >
            </tr>
            <tr v-if="!materialRows.length">
              <td :colspan="3 + days.length + weekGroups.length">
                材料対象の週間計画がありません。
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <LaserWeeklyMaterialOrder
      :start-date="startDate"
      :dates="allDays"
      :materials="materialRows"
      @message="message = $event"
    />
  </section>
</template>
<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import ExcelJS from "exceljs";
import LaserWeeklyMaterialOrder from "./LaserWeeklyMaterialOrder.vue";
import api from "@/api/client";
const props = defineProps({
  initialStartDate: { type: String, default: "" },
});
const iso = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const monday = (value = new Date()) => {
  const d = new Date(value);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return iso(d);
};
const nextBusinessDay = () => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return iso(d);
};
const showDetail = ref(false),
  showSummary = ref(false),
  showMaterialSheets = ref(false),
  showMaterialLots = ref(false),
  dirty = ref(false),
  saving = ref(false);
const startDate = ref(monday(props.initialStartDate || new Date())),
  rows = ref([]),
  patternRows = ref([]),
  materialRows = ref([]),
  targets = ref([]),
  lines = ref([]),
  products = ref([]),
  patterns = ref([]),
  downstreamProducts = ref([]),
  message = ref(""),
  filterDetailDownstream = ref(""),
  filterDetailMachine = ref(""),
  filterDetailProductCode = ref(""),
  filterDetailPatternNo = ref(""),
  filterDownstream = ref(""),
  filterMachine = ref(""),
  filterProductCode = ref(""),
  filterPatternNo = ref(""),
  filterThickness = ref(""),
  showSettings = ref(false),
  showPrintDialog = ref(false),
  printStartDate = ref(nextBusinessDay()),
  printEndDate = ref(nextBusinessDay()),
  printOrientation = ref("landscape"),
  showSaveDialog = ref(false),
  saveWeekKey = ref(""),
  showResetDialog = ref(false),
  resetStartDate = ref(""),
  resetEndDate = ref(""),
  changedManualQuantities = ref({});
const forcedInputCells = ref(new Set());
const forceShowInput = (pattern, day) => {
  const key = `${pattern.laser_pattern_id}_${day}`;
  if (!forcedInputCells.value.has(key)) {
    if (!pattern.daily[day]) pattern.daily[day] = { automatic_sheets: 0, manual_sheets: 0 };
    forcedInputCells.value = new Set([...forcedInputCells.value, key]);
    nextTick(() => {
      const td = document.querySelector(`[data-force-key="${key}"] input`);
      if (td) td.focus();
    });
  }
};
const fixedColumns = [
  "後工程",
  "取",
  "h/枚",
  "LT",
  "板厚",
  "製品番号",
  "P_№",
  "設備",
];
const fixedColumnWidths = [
  "68px",
  "32px",
  "42px",
  "28px",
  "36px",
  "94px",
  "38px",
  "36px",
];
const summaryColumns = [
  "後工程",
  "取",
  "h/枚",
  "LT",
  "板厚",
  "製品番号",
  "P_№",
  "設備",
  "期首",
];
const summaryColumnWidths = [
  "68px",
  "32px",
  "42px",
  "28px",
  "36px",
  "94px",
  "38px",
  "36px",
  "52px",
];
const productGroups = computed(() => {
  const groups = new Map();
  rows.value.forEach((row) => {
    if (!groups.has(row.product_code))
      groups.set(row.product_code, groups.size % 2);
  });
  return groups;
});
const productGroup = (productCode) => productGroups.value.get(productCode) || 0;
const filterDetailDownstreamOptions = computed(() =>
  [...new Set(rows.value.map((r) => r.downstream_line_name))].sort(),
);
const filterDetailProductOptions = computed(() =>
  [...new Set(rows.value.map((r) => r.product_code))].sort(),
);
const filterDetailPatternOptions = computed(() =>
  [...new Set(rows.value.map((r) => r.pattern_no))].sort((a, b) => a - b),
);
const filteredRows = computed(() =>
  rows.value.filter((r) => {
    if (filterDetailDownstream.value && r.downstream_line_name !== filterDetailDownstream.value) return false;
    if (filterDetailMachine.value && r.machine !== filterDetailMachine.value) return false;
    if (filterDetailProductCode.value && r.product_code !== filterDetailProductCode.value) return false;
    if (filterDetailPatternNo.value && String(r.pattern_no) !== filterDetailPatternNo.value) return false;
    return true;
  }),
);
const filterDownstreamOptions = computed(() =>
  [...new Set(patternRows.value.flatMap((p) => p.downstream_line_names))].sort(),
);
const filterProductOptions = computed(() =>
  [...new Set(patternRows.value.map((p) => p.representative_product_code))].sort(),
);
const filterPatternOptions = computed(() =>
  [...new Set(patternRows.value.map((p) => p.pattern_no))].sort((a, b) => a - b),
);
const filterThicknessOptions = computed(() =>
  [...new Set(patternRows.value.map((p) => p.thickness).filter(Boolean))].sort((a, b) => Number(a) - Number(b)),
);
const filteredPatternRows = computed(() =>
  patternRows.value.filter((p) => {
    if (filterDownstream.value && !p.downstream_line_names.includes(filterDownstream.value)) return false;
    if (filterMachine.value && p.machine !== filterMachine.value) return false;
    if (filterProductCode.value && p.representative_product_code !== filterProductCode.value) return false;
    if (filterPatternNo.value && String(p.pattern_no) !== filterPatternNo.value) return false;
    if (filterThickness.value && p.thickness !== filterThickness.value) return false;
    return true;
  }),
);
const summaryProductGroups = computed(() => {
  const groups = new Map();
  patternRows.value.forEach((pattern) => {
    if (!groups.has(pattern.representative_product_code))
      groups.set(pattern.representative_product_code, groups.size % 2);
  });
  return groups;
});
const summaryProductGroup = (productCode) =>
  summaryProductGroups.value.get(productCode) || 0;
const empty = () => ({
  id: null,
  downstream_line: null,
  product: null,
  laser_pattern: null,
  finished_product: null,
  lead_time_days: 0,
  quantity_source: "ORDER_QTY",
  sort_order: 0,
  is_active: true,
});
const form = ref(empty());
const selectedPatternIds = ref([]);
const loadDownstreamProducts = async () => {
  if (!form.value.downstream_line) {
    downstreamProducts.value = [];
    return;
  }
  const { data } = await api.laserWeeklyPlans.getDownstreamProducts(
    form.value.downstream_line,
  );
  downstreamProducts.value = data || [];
};
const onDownstreamLineChange = async () => {
  form.value.product = null;
  form.value.finished_product = null;
  selectedPatternIds.value = [];
  try {
    await loadDownstreamProducts();
  } catch (e) {
    message.value = "後工程製品を取得できませんでした。";
  }
};
const laserFinishedProducts = computed(() => {
  const ids = new Set(
    patterns.value.flatMap((pattern) =>
      (pattern.finished_items || []).map((item) =>
        Number(item.finished_product),
      ),
    ),
  );
  const downstream = products.value.find(
    (product) => Number(product.id) === Number(form.value.product),
  );
  const baseCode = String(downstream?.product_code || "").replace(
    /[kKｋＫcCｃＣ]+$/,
    "",
  );
  return products.value
    .filter((product) => ids.has(Number(product.id)))
    .sort((a, b) => {
      const aMatch =
        baseCode && String(a.product_code || "") === baseCode ? 0 : 1;
      const bMatch =
        baseCode && String(b.product_code || "") === baseCode ? 0 : 1;
      if (aMatch !== bMatch) return aMatch - bMatch;
      return String(a.product_code || "").localeCompare(
        String(b.product_code || ""),
        "ja",
        { numeric: true },
      );
    });
});
const filteredPatterns = computed(() =>
  patterns.value.filter((pattern) =>
    (pattern.finished_items || []).some(
      (item) =>
        Number(item.finished_product) === Number(form.value.finished_product),
    ),
  ),
);
const selectAllPatterns = () => {
  selectedPatternIds.value = filteredPatterns.value.map(
    (pattern) => pattern.id,
  );
};
const allDates = ref([]);
const allDays = computed(() => allDates.value);
const weekStartKey = (dateKey) => monday(dateKey);
const days = computed(() => {
  const base = allDates.value.slice(0, 10);
  const lastDay = base[base.length - 1];
  if (!lastDay) return base;
  const lastWeekKey = weekStartKey(lastDay);
  const extended = [...base];
  for (const day of allDates.value.slice(base.length)) {
    if (weekStartKey(day) !== lastWeekKey) break;
    extended.push(day);
  }
  return extended;
});
const number = (value, digits) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "";
};
const autoDigits = (v) => (Math.abs(Number(v || 0)) < 0.1 ? 2 : 1);
const dailyValue = (row, day, field) => row.daily[day]?.[field] ?? 0;
const isManualDifferent = (row, day) =>
  Number(dailyValue(row, day, "automatic_sheets")) !==
  Number(dailyValue(row, day, "manual_sheets"));
const patternDailyValue = (pattern, day, field) =>
  pattern.daily[day]?.[field] ?? 0;
const isPatternManualDifferent = (pattern, day) =>
  Number(patternDailyValue(pattern, day, "automatic_sheets")) !==
  Number(patternDailyValue(pattern, day, "manual_sheets"));
const isSmallerValue = (a, b) => {
  const na = Number(a),
    nb = Number(b);
  return na !== nb && na < nb;
};
const hours = (day, machine) => {
  const sum = patternRows.value
    .filter((x) => x.machine === machine)
    .reduce(
      (n, x) =>
        n +
        Number(patternDailyValue(x, day, "manual_sheets")) *
          Number(x.hours_per_sheet || 0),
      0,
    );
  return sum.toFixed(2).replace(/\.00$/, "");
};
const weekGroups = computed(() => {
  const groups = [];
  const groupMap = new Map();
  for (const day of days.value) {
    const key = weekStartKey(day);
    if (!groupMap.has(key)) {
      const group = { key, days: [] };
      groupMap.set(key, group);
      groups.push(group);
    }
    groupMap.get(key).days.push(day);
  }
  return groups;
});
const weeklyValue = (row, week, field) =>
  week.days.reduce((s, day) => s + Number(dailyValue(row, day, field)), 0);
const weeklyHours = (week, machine) => {
  const sum = patternRows.value
    .filter((x) => x.machine === machine)
    .reduce(
      (n, x) =>
        n +
        week.days.reduce(
          (s, day) =>
            s +
            Number(patternDailyValue(x, day, "manual_sheets")) *
              Number(x.hours_per_sheet || 0),
          0,
        ),
      0,
    );
  return sum.toFixed(2).replace(/\.00$/, "");
};
const patternWeeklyValue = (pattern, week, field) =>
  week.days.reduce(
    (s, day) => s + Number(patternDailyValue(pattern, day, field)),
    0,
  );
const isWeeklyManualDifferent = (row, week) =>
  weeklyValue(row, week, "automatic_sheets") !==
  weeklyValue(row, week, "manual_sheets");
const isPatternWeeklyManualDifferent = (pattern, week) =>
  patternWeeklyValue(pattern, week, "automatic_sheets") !==
  patternWeeklyValue(pattern, week, "manual_sheets");
const cumulativePatternValue = (pattern, upToDay, field) => {
  let sum = 0;
  for (const day of days.value) {
    sum += Number(patternDailyValue(pattern, day, field));
    if (day === upToDay) break;
  }
  return sum;
};
const patternProgressRaw = (pattern, upToDay) =>
  (pattern.initial_progress || 0) +
  cumulativePatternValue(pattern, upToDay, "manual_sheets") -
  cumulativePatternValue(pattern, upToDay, "automatic_sheets");
const patternProgressDisplayRaw = (pattern, upToDay) => {
  return patternProgressRaw(pattern, upToDay);
};
const patternProgress = (pattern, upToDay) => {
  const v = patternProgressDisplayRaw(pattern, upToDay);
  return number(v, autoDigits(v));
};
const progressClass = (v) =>
  v > 0 ? "progress-ahead" : v < 0 ? "progress-behind" : "";
const lotQty = (sheets, lotMin) => {
  const s = Number(sheets),
    m = Number(lotMin) || 1;
  return s <= 0 ? 0 : s / m;
};
const materialWeeklyValue = (material, week) =>
  week.days.reduce((s, day) => s + Number(material.daily[day] ?? 0), 0);
const summaryGridColumnCount = computed(
  () =>
    summaryColumns.length + days.value.length * 4 + weekGroups.value.length * 4,
);
const toggleLock = async (pattern) => {
  const newLocked = !pattern.initial_progress_locked;
  try {
    await api.laserWeeklyPlans.saveInitialProgress([
      {
        laser_pattern_id: pattern.laser_pattern_id,
        week_start_date: startDate.value,
        initial_progress: pattern.initial_progress || 0,
        is_locked: newLocked,
      },
    ]);
    pattern.initial_progress_locked = newLocked;
    message.value = newLocked
      ? "期首進度を固定しました。"
      : "期首進度のロックを解除しました。";
  } catch (e) {
    message.value =
      e.response?.data?.detail || "期首進度を保存できませんでした。";
  }
};
const gridColumnCount = computed(
  () =>
    fixedColumns.length + days.value.length * 3 + weekGroups.value.length * 3,
);
const openSaveDialog = () => {
  const w1 = weekGroups.value[0];
  saveWeekKey.value = w1?.key || 'all';
  showSaveDialog.value = true;
};
const selectSaveWeek = (week) => {
  saveWeekKey.value = week ? week.key : 'all';
};
const openResetDialog = () => {
  const d = days.value;
  resetStartDate.value = d[0] || startDate.value;
  resetEndDate.value = d[d.length - 1] || startDate.value;
  showResetDialog.value = true;
};
const executeReset = async () => {
  if (!resetStartDate.value || !resetEndDate.value || resetEndDate.value < resetStartDate.value) {
    message.value = "期間を正しく指定してください。";
    return;
  }
  if (!confirm(`${resetStartDate.value} ～ ${resetEndDate.value} の手回数をリセットしますか？`)) return;
  try {
    const { data } = await api.laserWeeklyPlans.resetPatternManualQuantities(resetStartDate.value, resetEndDate.value);
    showResetDialog.value = false;
    await loadPlan();
    message.value = `${data.deleted_count}件の手回数をリセットしました。`;
  } catch (e) {
    message.value = e.response?.data?.detail || "リセットに失敗しました。";
  }
};
const openPrintDialog = () => {
  const date = nextBusinessDay();
  printStartDate.value = date;
  printEndDate.value = date;
  showPrintDialog.value = true;
};
const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const printNumber = (value, digits = 0) =>
  Number(value || 0).toLocaleString("ja-JP", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
const printSummary = async () => {
  if (
    !printStartDate.value ||
    !printEndDate.value ||
    printEndDate.value < printStartDate.value
  ) {
    message.value = "印刷期間を正しく指定してください。";
    return;
  }
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    message.value =
      "印刷画面を開けませんでした。ポップアップを許可してください。";
    return;
  }
  try {
    const { data } = await api.laserWeeklyPlans.getWeeklyPlan({
      start_date: printStartDate.value,
      end_date: printEndDate.value,
    });
    const printDays = data.dates || [];
    const patternsForPrint = (data.pattern_rows || []).sort(
      (a, b) =>
        a.downstream_line_names.join(" ").localeCompare(b.downstream_line_names.join(" "), "ja") ||
        a.representative_product_code.localeCompare(b.representative_product_code, "ja", { numeric: true }),
    );
    const machineHours = (day, machine) =>
      patternsForPrint
        .filter((pattern) => pattern.machine === machine)
        .reduce(
          (sum, pattern) =>
            sum +
            Number(pattern.daily[day]?.manual_sheets || 0) *
              Number(pattern.hours_per_sheet || 0),
          0,
        );
    if (dirty.value) {
      if (!confirm("未保存の変更があります。保存済みデータで印刷しますか？")) {
        printWindow.close();
        return;
      }
    }
    const dailyCells = (pattern) =>
      printDays
        .map((day) => {
          const daily = pattern.daily[day] || {};
          const ms = Number(daily.manual_sheets || 0);
          const isTK = pattern.machine === "TK";
          return `<td class="bl">${isTK && ms ? printNumber(ms) : ""}</td><td>${printNumber(daily.demand_qty)}</td><td class="br">${!isTK && ms ? printNumber(ms) : ""}</td>`;
        })
        .join("");
    const emptyInfo = "<td></td><td></td><td></td><td></td><td></td>";
    const emptyData = printDays.map(() => "<td></td><td></td><td></td>").join("");
    const rowsHtml =
      patternsForPrint
        .map((pattern, i) => {
          const prev = patternsForPrint[i - 1];
          const border = prev && prev.representative_product_code !== pattern.representative_product_code ? ' class="group-border"' : '';
          const isTK = pattern.machine === "TK";
          const hasData = printDays.some((day) => Number(pattern.daily[day]?.manual_sheets || 0) > 0);
          const takeQty = pattern.take_qtys.map((q) => printNumber(q, 0)).join("/");
          const info = hasData
            ? `<td>${takeQty}</td><td>${escapeHtml(pattern.downstream_line_names.join(" / "))}</td><td>${printNumber(pattern.thickness, 1)}</td><td>${escapeHtml(pattern.representative_product_code)}</td><td>${escapeHtml(pattern.pattern_no)}</td>`
            : `<td></td><td></td><td></td><td></td><td>${escapeHtml(pattern.pattern_no)}</td>`;
          const infoR = hasData
            ? `<td>${escapeHtml(pattern.pattern_no)}</td><td>${escapeHtml(pattern.representative_product_code)}</td><td>${printNumber(pattern.thickness, 1)}</td><td>${escapeHtml(pattern.downstream_line_names.join(" / "))}</td><td>${takeQty}</td>`
            : `<td>${escapeHtml(pattern.pattern_no)}</td><td></td><td></td><td></td><td></td>`;
          const left = isTK ? info : emptyInfo;
          const center = dailyCells(pattern);
          const right = isTK ? emptyInfo : infoR;
          return `<tr${border}>${left}${center}${right}</tr>`;
        })
        .join("") ||
      `<tr><td colspan="${10 + printDays.length * 3}">対象設定を追加してください。</td></tr>`;
    const dayCols = printDays.length * 3;
    const tkH = printDays.map((day) => `${escapeHtml(day.slice(5))} ${printNumber(machineHours(day, "TK"), 2)}h`).join(" / ");
    const ajH = printDays.map((day) => `${escapeHtml(day.slice(5))} ${printNumber(machineHours(day, "AJ"), 2)}h`).join(" / ");
    printWindow.document.write(
      `<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>レーザ加工計画（パターン別合計）</title><style>@page{size:${printOrientation.value};margin:10mm}body{font-family:Meiryo,sans-serif;color:#111827}h1{font-size:14px;margin:0 0 4px;display:flex;justify-content:space-between;align-items:baseline}h1 span{font-size:11px;font-weight:normal;color:#555}table{border-collapse:collapse;font-size:9px;table-layout:fixed}th,td{border:1px solid #94a3b8;padding:3px;white-space:nowrap;text-align:right;overflow:hidden}th{background:#e2e8f0}th.m-tk{background:#1e40af;color:#fff;text-align:center;font-size:10px}th.m-aj{background:#b45309;color:#fff;text-align:center;font-size:10px}.left{text-align:left}tr.group-border>td{border-top:2px solid #333}.bl{border-left:3px solid #333}.br{border-right:3px solid #333}@media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}</style></head><body><h1>レーザ加工計画（パターン別合計）<span>${escapeHtml(printStartDate.value)} ～ ${escapeHtml(printEndDate.value)}</span></h1><table><thead><tr><th class="m-tk" colspan="5">1号機 ${tkH}</th>${printDays.map((day) => `<th colspan="3">${escapeHtml(day.slice(5))}</th>`).join("")}<th class="m-aj" colspan="5">2号機 ${ajH}</th></tr><tr><th>取</th><th>後工程</th><th>板厚</th><th>製品番号</th><th>P_№</th>${printDays.map(() => '<th class="bl">1号手数</th><th>需要</th><th class="br">2号手数</th>').join("")}<th>P_№</th><th>製品番号</th><th>板厚</th><th>後工程</th><th>取</th></tr></thead><tbody>${rowsHtml}</tbody></table></body></html>`,
    );
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
    printWindow.close();
    showPrintDialog.value = false;
  } catch (e) {
    printWindow.close();
    message.value =
      e.response?.data?.detail || "印刷用の計画を取得できませんでした。";
  }
};
const markManualQuantity = (row, day) => {
  const sheets = Number(row.daily[day].manual_sheets);
  if (!Number.isInteger(sheets) || sheets < 0) {
    message.value = "手回数は0以上の整数で入力してください。";
    return;
  }
  changedManualQuantities.value = {
    ...changedManualQuantities.value,
    [`${row.id}:${day}`]: { target_id: row.id, plan_date: day, sheets },
  };
};
const saveManualQuantities = async () => {
  const selectedWeek = weekGroups.value.find((w) => w.key === saveWeekKey.value);
  const targetDays = selectedWeek ? selectedWeek.days : [...days.value];
  if (!targetDays.length) {
    message.value = "保存対象がありません。";
    return;
  }
  saving.value = true;
  try {
    const quantities = patternRows.value.flatMap((pattern) =>
      targetDays.map((day) => ({
        laser_pattern_id: pattern.laser_pattern_id,
        plan_date: day,
        sheets: Number(patternDailyValue(pattern, day, "manual_sheets")),
      })),
    );
    const lastTargetDay = targetDays[targetDays.length - 1];
    const progressDays = days.value.filter((d) => d >= targetDays[0]);
    const progressValues = patternRows.value.flatMap((pattern) =>
      progressDays.map((day) => ({
        laser_pattern_id: pattern.laser_pattern_id,
        progress_date: day,
        progress: patternProgressRaw(pattern, day),
      })),
    );
    await api.laserWeeklyPlans.savePatternManualQuantities(quantities, progressValues);
    showSaveDialog.value = false;
    const label = selectedWeek
      ? `${weekGroups.value.indexOf(selectedWeek) + 1}週目`
      : "全期間";
    message.value = `${label}の手回数を保存しました。`;
    await loadPlan();
  } catch (e) {
    message.value =
      e.response?.data?.detail || "手回数を保存できませんでした。";
  } finally {
    saving.value = false;
  }
};
const confirmLoadPlan = async () => {
  if (
    dirty.value &&
    !confirm("未保存の変更があります。破棄して再読み込みしますか？")
  )
    return;
  await loadPlan();
};
const loadPlan = async () => {
  startDate.value = monday(startDate.value);
  try {
    const { data } = await api.laserWeeklyPlans.getWeeklyPlan({
      start_date: startDate.value,
    });
    allDates.value = data.dates || [];
    rows.value = data.rows || [];
    patternRows.value = (data.pattern_rows || []).sort(
      (a, b) =>
        a.downstream_line_names
          .join(" ")
          .localeCompare(b.downstream_line_names.join(" "), "ja") ||
        a.representative_product_code.localeCompare(
          b.representative_product_code,
          "ja",
          { numeric: true },
        ),
    );
    materialRows.value = data.material_rows || [];
    changedManualQuantities.value = {};
    forcedInputCells.value = new Set();
    dirty.value = false;
    message.value = "";
  } catch (e) {
    message.value = e.response?.data?.detail || "計画を取得できませんでした。";
  }
};
const exportTargetsExcel = async () => {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("対象設定");
  const headers = [
    "後工程ライン",
    "後工程製品コード",
    "後工程製品名",
    "パターン",
    "レーザ完成品",
    "取得元",
    "LT",
  ];
  const headerRow = ws.addRow(headers);
  headerRow.eachCell((cell) => {
    cell.font = { bold: true };
    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: "FFE2E8F0" },
    };
    cell.border = { bottom: { style: "thin" } };
  });
  targets.value.forEach((x) => {
    ws.addRow([
      x.downstream_line_name,
      x.product_code,
      x.product_name,
      x.pattern_no,
      x.finished_product_code,
      x.quantity_source === "PLAN_QTY" ? "後工程計画" : "後工程需要",
      x.lead_time_days,
    ]);
  });
  ws.columns.forEach((col) => {
    col.width = 18;
  });
  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `週間計画対象設定_${startDate.value}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
};
const loadMasters = async () => {
  const [t, l, p, lp] = await Promise.all([
    api.laserWeeklyPlans.getTargets(),
    api.lines.getLines({ page_size: 1000, line_type: "PROD", is_active: true }),
    api.products.getAllProducts(),
    api.laserPatterns.getLaserPatterns({ page_size: 1000 }),
  ]);
  targets.value = t.data.results || t.data || [];
  lines.value = l.data.results || l.data || [];
  products.value = Array.isArray(p) ? p : p.data?.results || p.data || [];
  patterns.value = lp.data.results || lp.data || [];
};
const reset = () => {
  form.value = empty();
  selectedPatternIds.value = [];
  downstreamProducts.value = [];
};
const edit = async (x) => {
  form.value = { ...x };
  await loadDownstreamProducts();
  selectedPatternIds.value = [x.laser_pattern];
  showSettings.value = true;
};
const saveTarget = async () => {
  try {
    const p = { ...form.value };
    delete p.id;
    if (form.value.id) {
      p.laser_pattern = selectedPatternIds.value[0];
      await api.laserWeeklyPlans.updateTarget(form.value.id, p);
    } else {
      if (!selectedPatternIds.value.length) {
        message.value = "レーザパターンを1件以上選択してください。";
        return;
      }
      await Promise.all(
        selectedPatternIds.value.map((laser_pattern) =>
          api.laserWeeklyPlans.createTarget({ ...p, laser_pattern }),
        ),
      );
    }
    reset();
    await loadMasters();
    await loadPlan();
  } catch (e) {
    message.value =
      e.response?.data?.product?.[0] ||
      e.response?.data?.detail ||
      "対象設定を保存できませんでした。";
  }
};
const remove = async (x) => {
  if (!confirm(`${x.pattern_no} を削除しますか？`)) return;
  await api.laserWeeklyPlans.deleteTarget(x.id);
  await loadMasters();
  await loadPlan();
};
watch(
  () => props.initialStartDate,
  async (value) => {
    if (!value) return;
    const nextStartDate = monday(value);
    if (startDate.value === nextStartDate) return;
    startDate.value = nextStartDate;
    await loadPlan();
  },
);
onMounted(async () => {
  await loadMasters();
  await loadPlan();
});
</script>
<style scoped>
.summary-product-0 td {
  background: #f8fafc;
}
.summary-product-1 td {
  background: #e1ffe1;
}
.summary-product-0 .manual-sheets,
.summary-product-0 .initial-progress-input {
  background: #fff;
}
.summary-product-1 .manual-sheets,
.summary-product-1 .initial-progress-input {
  background: #f6fff6;
}
</style>
<style scoped>
.weekly-plan {
  padding: 12px;
}
.toolbar,
.form {
  display: flex;
  gap: 8px;
  align-items: end;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.toolbar {
  flex-wrap: nowrap;
  white-space: nowrap;
}
.toolbar span {
  font-size: 12px;
  color: #475569;
}
.toolbar-message {
  color: #1e40af;
  font-weight: bold;
}
.toolbar label {
  display: flex;
  align-items: center;
  gap: 4px;
}
.btn,
button {
  border: 1px solid #94a3b8;
  background: #fff;
  border-radius: 4px;
  padding: 5px 8px;
  cursor: pointer;
}
.primary {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}
.print-modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.35);
}
.print-dialog {
  width: 300px;
  padding: 16px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.3);
}
.print-dialog h3 {
  margin: 0 0 12px;
  font-size: 16px;
}
.print-date-fields,
.print-actions {
  display: flex;
  gap: 8px;
}
.print-date-fields {
  margin-bottom: 14px;
}
.print-date-fields input {
  min-width: 0;
  width: 132px;
}
.print-actions {
  justify-content: flex-end;
}
.settings {
  padding: 10px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  margin-bottom: 10px;
}
.settings h3,
.pattern-summary-grid h3,
.material-grid h3 {
  margin: 0 0 8px;
  font-size: 14px;
}
.collapsible-header {
  margin: 0 0 4px;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  color: #334155;
}
label {
  display: grid;
  gap: 3px;
  font-size: 12px;
}
input,
select {
  height: 30px;
  min-width: 120px;
  box-sizing: border-box;
}
.manual-sheets {
  min-width: 38px;
  width: 38px;
  height: 26px;
  text-align: right;
}
.manual-sheets-cell {
  position: relative;
}
.manual-sheets-cell:hover::after,
.manual-sheets-cell:focus-within::after {
  content: attr(data-tip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #333;
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
  z-index: 100;
  pointer-events: none;
}
.summary-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
}
.summary-filters label {
  display: flex;
  align-items: center;
  gap: 3px;
}
.summary-filters select {
  height: 24px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 4px;
  font-size: 12px;
}
.grid,
.pattern-summary-scroll {
  max-height: calc(100vh - 210px);
  overflow: auto;
}
.plan-table,
.pattern-summary-table {
  border-collapse: collapse;
  table-layout: fixed;
  width: max-content;
  min-width: 0;
  font-size: 12px;
}
.demand-column {
  width: 38px;
}
.automatic-column {
  width: 38px;
}
.manual-column {
  width: 42px;
}
.week-total-column {
  width: 42px;
}
.plan-table th,
.plan-table td,
.pattern-summary-table th,
.pattern-summary-table td {
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  padding: 4px;
  white-space: nowrap;
}
.plan-table th,
.pattern-summary-table th {
  background: #e2e8f0;
}
.plan-table thead tr:nth-child(1) th,
.pattern-summary-table thead tr:nth-child(1) th {
  position: sticky;
  top: 0;
  z-index: 3;
}
.plan-table thead tr:nth-child(2) th,
.pattern-summary-table thead tr:nth-child(2) th {
  position: sticky;
  top: 25px;
  z-index: 3;
}
.plan-table thead tr:nth-child(3) th,
.pattern-summary-table thead tr:nth-child(3) th {
  position: sticky;
  top: 50px;
  z-index: 3;
}
.plan-table td,
.pattern-summary-table td {
  text-align: right;
}
.plan-table td:nth-child(1),
.plan-table td:nth-child(6),
.plan-table td:nth-child(7),
.pattern-summary-table td:nth-child(1),
.pattern-summary-table td:nth-child(6),
.pattern-summary-table td:nth-child(7) {
  text-align: left;
}
.plan-table td.smaller-val,
.pattern-summary-table td.smaller-val {
  color: #dc2626;
  font-weight: 700;
}
.smaller-val input {
  color: #dc2626;
  font-weight: 700;
}
.product-group-0 td {
  background: #f8fafc;
}
.product-group-1 td {
  background: #eff7df;
}
.product-group-0 .manual-sheets {
  background: #fff;
}
.product-group-1 .manual-sheets {
  background: #f7fbee;
}
.plan-table thead tr:first-child th:nth-child(-n + 8),
.plan-table tbody td:nth-child(-n + 8),
.pattern-summary-table thead tr:first-child th:nth-child(-n + 8),
.pattern-summary-table tbody td:nth-child(-n + 8) {
  position: sticky;
  z-index: 2;
}
.plan-table thead tr:first-child th:nth-child(-n + 8),
.pattern-summary-table thead tr:first-child th:nth-child(-n + 8) {
  z-index: 4;
}
.plan-table thead tr:first-child th:nth-child(1),
.plan-table tbody td:nth-child(1),
.pattern-summary-table thead tr:first-child th:nth-child(1),
.pattern-summary-table tbody td:nth-child(1) {
  left: 0;
}
.plan-table thead tr:first-child th:nth-child(2),
.plan-table tbody td:nth-child(2),
.pattern-summary-table thead tr:first-child th:nth-child(2),
.pattern-summary-table tbody td:nth-child(2) {
  left: 68px;
}
.plan-table thead tr:first-child th:nth-child(3),
.plan-table tbody td:nth-child(3),
.pattern-summary-table thead tr:first-child th:nth-child(3),
.pattern-summary-table tbody td:nth-child(3) {
  left: 100px;
}
.plan-table thead tr:first-child th:nth-child(4),
.plan-table tbody td:nth-child(4),
.pattern-summary-table thead tr:first-child th:nth-child(4),
.pattern-summary-table tbody td:nth-child(4) {
  left: 142px;
}
.plan-table thead tr:first-child th:nth-child(5),
.plan-table tbody td:nth-child(5),
.pattern-summary-table thead tr:first-child th:nth-child(5),
.pattern-summary-table tbody td:nth-child(5) {
  left: 170px;
}
.plan-table thead tr:first-child th:nth-child(6),
.plan-table tbody td:nth-child(6),
.pattern-summary-table thead tr:first-child th:nth-child(6),
.pattern-summary-table tbody td:nth-child(6) {
  left: 206px;
}
.plan-table thead tr:first-child th:nth-child(7),
.plan-table tbody td:nth-child(7),
.pattern-summary-table thead tr:first-child th:nth-child(7),
.pattern-summary-table tbody td:nth-child(7) {
  left: 300px;
}
.plan-table thead tr:first-child th:nth-child(8),
.plan-table tbody td:nth-child(8),
.pattern-summary-table thead tr:first-child th:nth-child(8),
.pattern-summary-table tbody td:nth-child(8) {
  left: 338px;
  z-index: 5;
}
.plan-table thead tr:first-child th:nth-child(n + 9),
.plan-table thead tr:nth-child(2) th,
.plan-table thead tr:nth-child(3) th:nth-child(3n),
.plan-table tbody td:nth-child(3n + 11),
.pattern-summary-table thead tr:first-child th:nth-child(n + 9),
.pattern-summary-table thead tr:nth-child(2) th,
.pattern-summary-table thead tr:nth-child(3) th:nth-child(4n),
.pattern-summary-table tbody td:nth-child(4n + 13) {
  border-right: 3px solid #111827;
}
.plan-table thead th:nth-child(8),
.pattern-summary-table thead th:nth-child(8) {
  background: #e2e8f0;
}
.plan-table thead tr:first-child th:nth-child(8)::after,
.plan-table tbody td:nth-child(8)::after,
.pattern-summary-table thead tr:first-child th:nth-child(8)::after,
.pattern-summary-table tbody td:nth-child(8)::after {
  background: #2563eb;
  bottom: -1px;
  content: "";
  position: absolute;
  right: -2px;
  top: -1px;
  width: 3px;
  z-index: 6;
}
.pattern-summary-grid,
.material-grid {
  margin-top: 14px;
}
.material-grid {
  overflow: auto;
}
.material-table {
  border-collapse: collapse;
  width: max-content;
  min-width: 0;
  font-size: 12px;
}
.material-table th,
.material-table td {
  border: 1px solid #cbd5e1;
  padding: 4px;
  white-space: nowrap;
}
.material-table th {
  background: #e2e8f0;
}
.material-table td {
  text-align: right;
}
.material-table td:nth-child(-n + 2) {
  text-align: left;
}
.material-table th:nth-child(1),
.material-table td:nth-child(1) {
  width: 145px;
  max-width: 145px;
}
.material-table th:nth-child(2),
.material-table td:nth-child(2) {
  width: 145px;
  max-width: 145px;
}
.material-table th:nth-child(3),
.material-table td:nth-child(3) {
  width: 38px;
  max-width: 38px;
}
.material-table th:nth-child(n + 4),
.material-table td:nth-child(n + 4) {
  width: 42px;
  max-width: 42px;
}
.week-total {
  font-weight: 700;
}
.plan-table th.week-total,
.pattern-summary-table th.week-total {
  background: #93c5fd;
}
.plan-table td.week-total,
.pattern-summary-table td.week-total {
  background: #dbeafe;
}
th:not(.week-total) + th.week-total,
td:not(.week-total) + td.week-total {
  border-left: 3px solid #2563eb;
}
.progress-column {
  width: 38px;
}
.progress-cell {
  font-size: 11px;
  color: #64748b;
}
.progress-ahead {
  color: #059669 !important;
  font-weight: 700;
}
.progress-behind {
  color: #dc2626 !important;
  font-weight: 700;
}
.pattern-summary-table thead tr:first-child th:nth-child(9),
.pattern-summary-table tbody td:nth-child(9) {
  position: sticky;
  left: 374px;
  z-index: 5;
  border-right: 1px solid #cbd5e1;
}
.pattern-summary-table thead tr:first-child th:nth-child(9) {
  z-index: 7;
}
.pattern-summary-table thead tr:first-child th:nth-child(8) {
  z-index: 4;
}
.pattern-summary-table tbody td:nth-child(8) {
  z-index: 2;
}
.pattern-summary-table thead tr:first-child th:nth-child(8)::after,
.pattern-summary-table tbody td:nth-child(8)::after {
  display: none;
}
.pattern-summary-table thead tr:first-child th:nth-child(9)::after,
.pattern-summary-table tbody td:nth-child(9)::after {
  background: #2563eb;
  bottom: -1px;
  content: "";
  position: absolute;
  right: -2px;
  top: -1px;
  width: 3px;
  z-index: 6;
}
.initial-progress-input {
  min-width: 28px;
  width: 28px;
  height: 22px;
  text-align: right;
  font-size: 11px;
}
.lock-btn {
  font-size: 9px;
  padding: 0 3px;
  min-width: 0;
  height: 22px;
  line-height: 22px;
}
.lock-btn.locked {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}
.save-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.2);
}
.save-progress {
  background: #fff;
  padding: 20px 32px;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  text-align: center;
  min-width: 180px;
}
.save-bar {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  margin-bottom: 10px;
  overflow: hidden;
}
.save-bar::after {
  content: "";
  display: block;
  height: 100%;
  width: 40%;
  background: #0f766e;
  border-radius: 2px;
  animation: save-slide 1s ease-in-out infinite;
}
@keyframes save-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(350%);
  }
}
.material-weekly th.week-total {
  background: #93c5fd;
  font-weight: 700;
}
.material-weekly td.week-total {
  background: #dbeafe;
  font-weight: 700;
}
.material-weekly th:not(.week-total) + th.week-total,
.material-weekly td:not(.week-total) + td.week-total {
  border-left: 3px solid #2563eb;
}
</style>
