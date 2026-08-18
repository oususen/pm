<template>
  <div class="laser-trouble-page">
    <header class="hero">
      <p class="eyebrow">その他 / トラブル対応</p>
      <h2 class="page-title">トラブル対応（レーザ）</h2>
      <p class="hero-text">事例確認と、実運用時の手順入力をタブで切り替えます。</p>
    </header>

    <div class="tab-bar">
      <button type="button" class="tab-button" :class="{ active: activeTab === 'example' }" @click="activeTab = 'example'">事例 2026-08-17</button>
      <button type="button" class="tab-button" :class="{ active: activeTab === 'steps' }" @click="activeTab = 'steps'">手順</button>
    </div>

    <template v-if="activeTab === 'example'">
      <section class="panel">
        <div class="panel-header">
          <h3>対応手順</h3>
          <p>レーザートラブルに伴う加工応援の時やること</p>
        </div>
        <ol class="step-list">
          <li v-for="step in exampleSteps" :key="step.no" class="step-item">
            <div class="step-no">{{ step.no }}</div>
            <div class="step-body">
              <div class="step-title">{{ step.title }}</div>
              <p v-if="step.detail" class="step-detail">{{ step.detail }}</p>
            </div>
          </li>
        </ol>

        <div class="sub-notes">
          <div v-for="note in reminders" :key="note.title" class="note-card">
            <div class="note-title">{{ note.title }}</div>
            <p class="note-text">{{ note.text }}</p>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h3>応援加工依頼</h3>
          <p>2026-08-17 実績</p>
        </div>

        <div class="summary-grid">
          <article class="summary-card">
            <div class="summary-label">対象期間</div>
            <div class="summary-value">2026-08-19 - 2026-08-26</div>
          </article>
          <article class="summary-card">
            <div class="summary-label">依頼メモ</div>
            <div class="summary-value">必要数/日を納入いただけるよう加工応援を依頼する。超過納入可。</div>
          </article>
        </div>

        <div class="table-wrap">
          <table class="plan-table">
            <thead>
              <tr>
                <th>ネスティング<br />No.</th>
                <th>俗称</th>
                <th>板厚</th>
                <th>材料仕込/日</th>
                <th>製品重量/日</th>
                <th>品番</th>
                <th>個/枚<br />（取り数）</th>
                <th>依頼数</th>
                <th v-for="day in exampleDateColumns" :key="day.key">{{ day.label }}</th>
                <th>合計数量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in exampleRows" :key="row.rowKey">
                <td>{{ row.nestingNo || '' }}</td>
                <td>{{ row.commonName || '' }}</td>
                <td>{{ row.thickness || '' }}</td>
                <td>{{ row.materialPerDay || '' }}</td>
                <td>{{ row.productWeightPerDay || '' }}</td>
                <td class="code-cell">{{ row.partNo }}</td>
                <td>{{ row.unitPerSet }}</td>
                <td>{{ row.requestQty }}</td>
                <td v-for="day in exampleDateColumns" :key="`${row.rowKey}-${day.key}`">{{ formatQty(row.daily[day.key]) }}</td>
                <td>{{ row.totalQty }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <template v-else>
      <section class="panel">
        <div class="panel-header">
          <h3>手順入力</h3>
          <p>トラブル発生時に順番に記入して使う。</p>
        </div>

        <ol class="step-list">
          <div class="step-row">
            <li class="step-item compact-step">
              <div class="step-no">1</div>
              <div class="step-body">
                <div class="step-title">復旧日時を仮定する</div>
                <p class="step-detail">最悪の場合でいつの何時に復旧するかを定義する。</p>
                <label class="field">
                  <span class="field-label">想定復旧日時</span>
                  <input v-model="stepForm.recoveryAt" class="field-input" type="datetime-local" />
                </label>
              </div>
            </li>

            <li class="step-item compact-step">
              <div class="step-no">2</div>
              <div class="step-body">
                <div class="step-title">トラブル設備</div>
                <p class="step-detail">どの設備でトラブルが起きているかを設備マスタから選択する。</p>
                <label class="field">
                  <span class="field-label">トラブル設備</span>
                  <select v-model="stepForm.troubleEquipment" class="field-input">
                    <option value="">選択してください</option>
                    <option v-for="equipment in troubleEquipmentOptions" :key="equipment.id" :value="equipment.id">{{ equipment.label }}</option>
                  </select>
                </label>
              </div>
            </li>
          </div>

          <li v-for="step in editableSteps.filter((item) => item.no >= 3)" :key="step.no" class="step-item">
            <div class="step-no">{{ step.no }}</div>
            <div class="step-body">
              <div class="step-title">{{ step.title }}</div>
              <p v-if="step.detail" class="step-detail">{{ step.detail }}</p>
              <div v-if="step.no === 3" class="field">
                <span class="field-label">加工対象一覧</span>
                <div v-if="stepForm.troubleEquipment" class="selection-summary">
                  <span>選定済みパータン: {{ selectedPatternCount }} 件</span>
                  <button type="button" class="mini-action" @click="clearSelectedPatterns" :disabled="!selectedPatternCount">選定クリア</button>
                </div>
                <div v-if="stepForm.troubleEquipment" class="table-wrap">
                  <table class="target-table">
                    <thead>
                      <tr>
                        <th>対応</th>
                        <th>パータン</th>
                        <th>完成品</th>
                        <th>加工時間</th>
                        <th>板厚</th>
                        <th>材料</th>
                      </tr>
                      <tr class="filter-row">
                        <th></th>
                        <th><input v-model.trim="step3Filters.patternNo" class="filter-input" type="text" placeholder="絞込" /></th>
                        <th>
                          <select v-model="step3Filters.finishedProduct" class="filter-input">
                            <option value="">すべて</option>
                            <option value="HAS">あり</option>
                            <option value="NONE">なし</option>
                          </select>
                        </th>
                        <th><input v-model.trim="step3Filters.processTime" class="filter-input" type="text" placeholder="絞込" /></th>
                        <th><input v-model.trim="step3Filters.thickness" class="filter-input" type="text" placeholder="絞込" /></th>
                        <th><input v-model.trim="step3Filters.material" class="filter-input" type="text" placeholder="絞込" /></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="pattern in filteredStep3Patterns" :key="pattern.id">
                        <td class="select-cell">
                          <input :checked="isPatternSelected(pattern.id)" type="checkbox" @change="togglePatternSelection(pattern)" />
                        </td>
                        <td class="target-code-cell">{{ pattern.patternNo }}</td>
                        <td class="target-finished-cell">{{ pattern.finishedProductsLabel }}</td>
                        <td>{{ formatMinutes(pattern.processTimeMin) }}</td>
                        <td>{{ pattern.thicknessLabel }}</td>
                        <td>{{ pattern.materialLabel }}</td>
                      </tr>
                      <tr v-if="!filteredStep3Patterns.length">
                        <td colspan="6" class="empty-cell">選択した設備に紐づくパータンがありません。</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <span v-else class="field-help">先にトラブル設備を選択してください。</span>
              </div>
              <div v-else-if="step.no === 4" class="field">
                <span class="field-label">手順3で選定したパータンの詳細情報</span>
                <div class="policy-section">
                  <span class="field-label">対応方針</span>
                  <div class="policy-buttons">
                    <button type="button" class="policy-button" :class="{ active: stepForm.responsePolicy === 'IN_HOUSE' }" @click="applyResponsePolicy('IN_HOUSE')">社内</button>
                    <button type="button" class="policy-button" :class="{ active: stepForm.responsePolicy === 'OTHER_EQUIPMENT' }" @click="applyResponsePolicy('OTHER_EQUIPMENT')">別設備</button>
                    <button type="button" class="policy-button" :class="{ active: stepForm.responsePolicy === 'OUTSOURCE' }" @click="applyResponsePolicy('OUTSOURCE')">外作</button>
                  </div>
                </div>
                <div v-if="step4DetailRows.length" class="table-wrap">
                  <table class="target-table detail-table">
                    <thead>
                      <tr>
                        <th>パータン</th>
                        <th>完成品</th>
                        <th>加工時間</th>
                        <th>板厚</th>
                        <th>材料</th>
                        <th>対応</th>
                        <th>需要日付</th>
                        <th>必要数</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-for="row in step4DetailRows" :key="`detail-${row.patternId}`">
                        <tr v-for="(demand, demandIndex) in row.demands" :key="`detail-${row.patternId}-${demand.id}`">
                          <td v-if="demandIndex === 0" :rowspan="row.demands.length" class="target-code-cell">{{ row.patternNo }}</td>
                          <td v-if="demandIndex === 0" :rowspan="row.demands.length" class="target-finished-cell">{{ row.finishedProductsLabel }}</td>
                          <td v-if="demandIndex === 0" :rowspan="row.demands.length">{{ formatMinutes(row.processTimeMin) }}</td>
                          <td v-if="demandIndex === 0" :rowspan="row.demands.length">{{ row.thicknessLabel }}</td>
                          <td v-if="demandIndex === 0" :rowspan="row.demands.length">{{ row.materialLabel }}</td>
                          <td v-if="demandIndex === 0" :rowspan="row.demands.length">
                            <select v-model="row.responseType" class="table-edit-select">
                              <option value="">選択してください</option>
                              <option value="IN_HOUSE">社内</option>
                              <option value="OTHER_EQUIPMENT">別設備</option>
                              <option value="OUTSOURCE">外作</option>
                            </select>
                          </td>
                          <td>
                            <input v-model="demand.demandDate" class="table-edit-input" type="date" />
                          </td>
                          <td>
                            <input v-model="demand.requiredQty" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" />
                          </td>
                          <td class="detail-action-cell">
                            <button type="button" class="mini-action" @click="addDemandRow(row.patternId)">追加</button>
                            <button
                              type="button"
                              class="mini-action"
                              :disabled="row.demands.length === 1"
                              @click="removeDemandRow(row.patternId, demand.id)"
                            >
                              削除
                            </button>
                          </td>
                        </tr>
                      </template>
                    </tbody>
                  </table>
                </div>
                <span v-else class="field-help">手順3で対応パータンを選定してください。</span>
                <div class="generate-actions">
                  <button
                    type="button"
                    class="policy-button"
                    :disabled="!step4DetailRows.length"
                    @click="generateStep4Table"
                  >
                    表を生成
                  </button>
                  <button
                    v-if="step4Rows.length"
                    type="button"
                    class="mini-action"
                    @click="clearStep4Table"
                  >
                    表をクリア
                  </button>
                  <button
                    v-if="step4Rows.length"
                    type="button"
                    class="mini-action"
                    @click="exportPlanTable(step4Rows, step4Totals, '手順4_詳細情報と対応方針')"
                  >
                    Excel出力
                  </button>
                </div>
                <span v-if="step4DetailRows.length && !step4Rows.length" class="field-help">手順3で選定したパータンをもとに、必要なときだけ表を生成します。</span>
                <div v-if="step4Rows.length" class="table-wrap step4-plan-wrap">
                  <table class="plan-table step4-plan-table">
                    <colgroup>
                      <col class="col-nesting" />
                      <col class="col-finished-part" />
                      <col class="col-component-part" />
                      <col class="col-small-num" />
                      <col class="col-common-name" />
                      <col class="col-thickness" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                      <col class="col-small-num" />
                      <col class="col-unit-set" />
                      <col class="col-small-num" />
                      <col class="col-mid-num" />
                      <template v-for="day in generatedStep4DateColumns" :key="`step4-col-${day.key}`">
                        <col class="col-day-num" />
                        <col class="col-day-num" />
                        <col class="col-day-material" />
                        <col class="col-day-num" />
                      </template>
                      <col class="col-small-num" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th rowspan="3">ネスティング<br />No.</th>
                        <th rowspan="3">完成<br />品番</th>
                        <th rowspan="3">構成子<br />品番</th>
                        <th rowspan="3">子取り数</th>
                        <th rowspan="3">俗称</th>
                        <th rowspan="3">板厚</th>
                        <th rowspan="3">材料仕込<br />/日</th>
                        <th rowspan="3">製品重量<br />/日</th>
                        <th rowspan="3">加工<br />時間</th>
                        <th rowspan="3">個/枚<br />（取り数）</th>
                        <th rowspan="3">依頼<br />数</th>
                        <th rowspan="3">平均必要数<br />個/日</th>
                        <th :colspan="generatedStep4DateColumns.length * 4">必要数/日</th>
                        <th rowspan="3">合計<br />数量</th>
                        <th rowspan="3">合計<br />時間</th>
                        <th rowspan="3">合計<br />枚数</th>
                        <th rowspan="3">合計<br />重量</th>
                      </tr>
                      <tr>
                        <th v-for="day in generatedStep4DateColumns" :key="`step4-head-${day.key}`" colspan="4">{{ day.label }}</th>
                      </tr>
                      <tr>
                        <template v-for="day in generatedStep4DateColumns" :key="`step4-subhead-${day.key}`">
                          <th>必要数</th>
                          <th>分/日</th>
                          <th>材料枚数</th>
                          <th>重量</th>
                        </template>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-for="row in step4Rows" :key="row.rowKey">
                        <tr v-for="(component, componentIndex) in row.componentItems" :key="`${row.rowKey}-${component.rowKey}`">
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ row.groupLabel }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length" class="code-cell">{{ row.partNo }}</td>
                          <td class="component-cell code-cell">{{ component.code }}</td>
                          <td>{{ component.takeQty }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.commonName" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ row.thickness }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.materialPerDay" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.productWeightPerDay" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ formatMinutes(row.processTimeMin) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.unitPerSet" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.requestQty" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.requiredPerDay" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <template v-if="componentIndex === 0" v-for="day in generatedStep4DateColumns" :key="`${row.rowKey}-${day.key}`">
                            <td :rowspan="row.componentItems.length">
                              <input v-model="row.daily[day.key]" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" />
                            </td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyProcessMinutes(row.daily[day.key], row.unitPerSet, row.processTimeMin) }}</td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyMaterialRequired(row.daily[day.key], row.unitPerSet) }}</td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyMaterialWeight(row.daily[day.key], row.unitPerSet, row.materialUnitWeightKg) }}</td>
                          </template>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyQty(row.daily) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyProcessMinutes(row.daily, row.unitPerSet, row.processTimeMin) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyMaterialRequired(row.daily, row.unitPerSet) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyMaterialWeight(row.daily, row.unitPerSet, row.materialUnitWeightKg) }}</td>
                        </tr>
                      </template>
                      <tr v-if="step4Rows.length" class="total-row">
                        <td colspan="10">合計</td>
                        <td>{{ step4Totals.requestQty }}</td>
                        <td>{{ step4Totals.requiredPerDay }}</td>
                        <template v-for="day in generatedStep4DateColumns" :key="`step4-total-${day.key}`">
                          <td>{{ step4Totals.daily[day.key]?.qty }}</td>
                          <td>{{ step4Totals.daily[day.key]?.minutes }}</td>
                          <td>{{ step4Totals.daily[day.key]?.materialRequired }}</td>
                          <td>{{ step4Totals.daily[day.key]?.weight }}</td>
                        </template>
                        <td>{{ step4Totals.totalQty }}</td>
                        <td>{{ step4Totals.totalMinutes }}</td>
                        <td>{{ step4Totals.totalMaterialRequired }}</td>
                        <td>{{ step4Totals.totalWeight }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div v-else-if="step.no === 5" class="field">
                <span class="field-label">社内・別設備対応表</span>
                <div class="generate-actions">
                  <button
                    type="button"
                    class="policy-button"
                    :disabled="!step4Rows.length || !step5SourceRows.length"
                    @click="generateStep5Table"
                  >
                    表を生成
                  </button>
                  <button
                    v-if="step5Generated"
                    type="button"
                    class="mini-action"
                    @click="clearStep5Table"
                  >
                    表をクリア
                  </button>
                  <button
                    v-if="step5Generated && step5Rows.length"
                    type="button"
                    class="mini-action"
                    @click="exportPlanTable(step5Rows, step5Totals, '手順5_社内別設備対応表')"
                  >
                    Excel出力
                  </button>
                </div>
                <span v-if="!step4Rows.length" class="field-help">先に手順4で表を生成してください。</span>
                <span v-else-if="!step5SourceRows.length" class="field-help">手順4で `社内` または `別設備` を選んだパータンがありません。</span>
                <span v-else-if="!step5Generated" class="field-help">手順4で `社内` と `別設備` にした内容だけを手順5に展開します。</span>
                <div v-if="step5Generated && step5Rows.length" class="table-wrap step4-plan-wrap">
                  <table class="plan-table step4-plan-table">
                    <colgroup>
                      <col class="col-nesting" />
                      <col class="col-finished-part" />
                      <col class="col-component-part" />
                      <col class="col-small-num" />
                      <col class="col-common-name" />
                      <col class="col-thickness" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                      <col class="col-small-num" />
                      <col class="col-unit-set" />
                      <col class="col-small-num" />
                      <col class="col-mid-num" />
                      <template v-for="day in generatedStep4DateColumns" :key="`step5-col-${day.key}`">
                        <col class="col-day-num" />
                        <col class="col-day-num" />
                        <col class="col-day-material" />
                        <col class="col-day-num" />
                      </template>
                      <col class="col-small-num" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th rowspan="3">ネスティング<br />No.</th>
                        <th rowspan="3">完成<br />品番</th>
                        <th rowspan="3">構成子<br />品番</th>
                        <th rowspan="3">子取り数</th>
                        <th rowspan="3">俗称</th>
                        <th rowspan="3">板厚</th>
                        <th rowspan="3">材料仕込<br />/日</th>
                        <th rowspan="3">製品重量<br />/日</th>
                        <th rowspan="3">加工<br />時間</th>
                        <th rowspan="3">個/枚<br />（取り数）</th>
                        <th rowspan="3">依頼<br />数</th>
                        <th rowspan="3">平均必要数<br />個/日</th>
                        <th :colspan="generatedStep4DateColumns.length * 4">必要数/日</th>
                        <th rowspan="3">合計<br />数量</th>
                        <th rowspan="3">合計<br />時間</th>
                        <th rowspan="3">合計<br />枚数</th>
                        <th rowspan="3">合計<br />重量</th>
                      </tr>
                      <tr>
                        <th v-for="day in generatedStep4DateColumns" :key="`step5-head-${day.key}`" colspan="4">{{ day.label }}</th>
                      </tr>
                      <tr>
                        <template v-for="day in generatedStep4DateColumns" :key="`step5-subhead-${day.key}`">
                          <th>必要数</th>
                          <th>分/日</th>
                          <th>材料枚数</th>
                          <th>重量</th>
                        </template>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-for="row in step5Rows" :key="`step5-${row.rowKey}`">
                        <tr v-for="(component, componentIndex) in row.componentItems" :key="`step5-${row.rowKey}-${component.rowKey}`">
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ row.groupLabel }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length" class="code-cell">{{ row.partNo }}</td>
                          <td class="component-cell code-cell">{{ component.code }}</td>
                          <td>{{ component.takeQty }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.commonName" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ row.thickness }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.materialPerDay" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.productWeightPerDay" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ formatMinutes(row.processTimeMin) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.unitPerSet" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.requestQty" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.requiredPerDay" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <template v-if="componentIndex === 0" v-for="day in generatedStep4DateColumns" :key="`step5-${row.rowKey}-${day.key}`">
                            <td :rowspan="row.componentItems.length">
                              <input v-model="row.daily[day.key]" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" />
                            </td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyProcessMinutes(row.daily[day.key], row.unitPerSet, row.processTimeMin) }}</td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyMaterialRequired(row.daily[day.key], row.unitPerSet) }}</td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyMaterialWeight(row.daily[day.key], row.unitPerSet, row.materialUnitWeightKg) }}</td>
                          </template>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyQty(row.daily) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyProcessMinutes(row.daily, row.unitPerSet, row.processTimeMin) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyMaterialRequired(row.daily, row.unitPerSet) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyMaterialWeight(row.daily, row.unitPerSet, row.materialUnitWeightKg) }}</td>
                        </tr>
                      </template>
                      <tr v-if="step5Rows.length" class="total-row">
                        <td colspan="10">合計</td>
                        <td>{{ step5Totals.requestQty }}</td>
                        <td>{{ step5Totals.requiredPerDay }}</td>
                        <template v-for="day in generatedStep4DateColumns" :key="`step5-total-${day.key}`">
                          <td>{{ step5Totals.daily[day.key]?.qty }}</td>
                          <td>{{ step5Totals.daily[day.key]?.minutes }}</td>
                          <td>{{ step5Totals.daily[day.key]?.materialRequired }}</td>
                          <td>{{ step5Totals.daily[day.key]?.weight }}</td>
                        </template>
                        <td>{{ step5Totals.totalQty }}</td>
                        <td>{{ step5Totals.totalMinutes }}</td>
                        <td>{{ step5Totals.totalMaterialRequired }}</td>
                        <td>{{ step5Totals.totalWeight }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div v-else-if="step.no === 6" class="field">
                <span class="field-label">外作対応表</span>
                <div class="generate-actions">
                  <button
                    type="button"
                    class="policy-button"
                    :disabled="!step4Rows.length || !step6SourceRows.length"
                    @click="generateStep6Table"
                  >
                    表を生成
                  </button>
                  <button
                    v-if="step6Generated"
                    type="button"
                    class="mini-action"
                    @click="clearStep6Table"
                  >
                    表をクリア
                  </button>
                  <button
                    v-if="step6Generated && step6Rows.length"
                    type="button"
                    class="mini-action"
                    @click="exportPlanTable(step6Rows, step6Totals, '手順6_外作対応表')"
                  >
                    Excel出力
                  </button>
                </div>
                <span v-if="!step4Rows.length" class="field-help">先に手順4で表を生成してください。</span>
                <span v-else-if="!step6SourceRows.length" class="field-help">手順4で `外作` を選んだパータンがありません。</span>
                <span v-else-if="!step6Generated" class="field-help">手順4で `外作` にした内容だけを手順6に展開します。</span>
                <div v-if="step6Generated && step6Rows.length" class="table-wrap step4-plan-wrap">
                  <table class="plan-table step4-plan-table">
                    <colgroup>
                      <col class="col-nesting" />
                      <col class="col-finished-part" />
                      <col class="col-component-part" />
                      <col class="col-small-num" />
                      <col class="col-common-name" />
                      <col class="col-thickness" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                      <col class="col-small-num" />
                      <col class="col-unit-set" />
                      <col class="col-small-num" />
                      <col class="col-mid-num" />
                      <template v-for="day in generatedStep4DateColumns" :key="`step6-col-${day.key}`">
                        <col class="col-day-num" />
                        <col class="col-day-num" />
                        <col class="col-day-material" />
                        <col class="col-day-num" />
                      </template>
                      <col class="col-small-num" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                      <col class="col-mid-num" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th rowspan="3">ネスティング<br />No.</th>
                        <th rowspan="3">完成<br />品番</th>
                        <th rowspan="3">構成子<br />品番</th>
                        <th rowspan="3">子取り数</th>
                        <th rowspan="3">俗称</th>
                        <th rowspan="3">板厚</th>
                        <th rowspan="3">材料仕込<br />/日</th>
                        <th rowspan="3">製品重量<br />/日</th>
                        <th rowspan="3">加工<br />時間</th>
                        <th rowspan="3">個/枚<br />（取り数）</th>
                        <th rowspan="3">依頼<br />数</th>
                        <th rowspan="3">平均必要数<br />個/日</th>
                        <th :colspan="generatedStep4DateColumns.length * 4">必要数/日</th>
                        <th rowspan="3">合計<br />数量</th>
                        <th rowspan="3">合計<br />時間</th>
                        <th rowspan="3">合計<br />枚数</th>
                        <th rowspan="3">合計<br />重量</th>
                      </tr>
                      <tr>
                        <th v-for="day in generatedStep4DateColumns" :key="`step6-head-${day.key}`" colspan="4">{{ day.label }}</th>
                      </tr>
                      <tr>
                        <template v-for="day in generatedStep4DateColumns" :key="`step6-subhead-${day.key}`">
                          <th>必要数</th>
                          <th>分/日</th>
                          <th>材料枚数</th>
                          <th>重量</th>
                        </template>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-for="row in step6Rows" :key="`step6-${row.rowKey}`">
                        <tr v-for="(component, componentIndex) in row.componentItems" :key="`step6-${row.rowKey}-${component.rowKey}`">
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ row.groupLabel }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length" class="code-cell">{{ row.partNo }}</td>
                          <td class="component-cell code-cell">{{ component.code }}</td>
                          <td>{{ component.takeQty }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.commonName" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ row.thickness }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.materialPerDay" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.productWeightPerDay" class="table-edit-input" type="text" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ formatMinutes(row.processTimeMin) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.unitPerSet" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.requestQty" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length"><input v-model="row.requiredPerDay" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" /></td>
                          <template v-if="componentIndex === 0" v-for="day in generatedStep4DateColumns" :key="`step6-${row.rowKey}-${day.key}`">
                            <td :rowspan="row.componentItems.length">
                              <input v-model="row.daily[day.key]" class="table-edit-input table-edit-input-num" type="number" min="0" step="1" />
                            </td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyProcessMinutes(row.daily[day.key], row.unitPerSet, row.processTimeMin) }}</td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyMaterialRequired(row.daily[day.key], row.unitPerSet) }}</td>
                            <td :rowspan="row.componentItems.length">{{ calculateDailyMaterialWeight(row.daily[day.key], row.unitPerSet, row.materialUnitWeightKg) }}</td>
                          </template>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyQty(row.daily) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyProcessMinutes(row.daily, row.unitPerSet, row.processTimeMin) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyMaterialRequired(row.daily, row.unitPerSet) }}</td>
                          <td v-if="componentIndex === 0" :rowspan="row.componentItems.length">{{ sumDailyMaterialWeight(row.daily, row.unitPerSet, row.materialUnitWeightKg) }}</td>
                        </tr>
                      </template>
                      <tr v-if="step6Rows.length" class="total-row">
                        <td colspan="10">合計</td>
                        <td>{{ step6Totals.requestQty }}</td>
                        <td>{{ step6Totals.requiredPerDay }}</td>
                        <template v-for="day in generatedStep4DateColumns" :key="`step6-total-${day.key}`">
                          <td>{{ step6Totals.daily[day.key]?.qty }}</td>
                          <td>{{ step6Totals.daily[day.key]?.minutes }}</td>
                          <td>{{ step6Totals.daily[day.key]?.materialRequired }}</td>
                          <td>{{ step6Totals.daily[day.key]?.weight }}</td>
                        </template>
                        <td>{{ step6Totals.totalQty }}</td>
                        <td>{{ step6Totals.totalMinutes }}</td>
                        <td>{{ step6Totals.totalMaterialRequired }}</td>
                        <td>{{ step6Totals.totalWeight }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <textarea v-model="step.memo" class="step-textarea" rows="2" placeholder="確認結果、判断、連絡内容を記入" />
            </div>
          </li>
        </ol>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

const activeTab = ref('example')

const exampleSteps = [
  { no: 1, title: '復旧日時を仮定する', detail: '最悪の場合でいつの何時に復旧するかを定義する。' },
  { no: 2, title: '上記時間までに必要な対象設備の部品有無を調べる' },
  { no: 3, title: 'それを踏まえ２号機で加工する、しないを決める' },
  { no: 4, title: 'それでも間に合わない場合、外作部品の選定をする' },
  { no: 5, title: '各部品別で必要な情報をまとめる', detail: '部番、品名、負荷/日、消費材料重量/日、製品重量/日、不足数量、各ネスティングから取れる枚数、必要枚数/日と週などを整理する。' },
  { no: 6, title: '材料の段取り', detail: 'ダイソウへの配送予定表からどれを、どれだけ、いつから、どうやって送るかを検討し、名成鋼機へ相談・連絡したうえで計画を立てて送る。' },
  { no: 7, title: '加工計画を応援先へ送る', detail: '生産計画シートを参照して送付する。' },
]

const reminders = [
  { title: '塗装部品', text: '社内塗装部品に関しての情報共有や相談は、早い段階で塗装事業部へ連絡を入れる。' },
  { title: '社内連絡', text: '社内関係者へ連絡を入れる。' },
  { title: 'データ準備', text: 'ネスティングデータ変換と単品データ作成を行う。三原・ホウダは同設備、積水はメーカーが異なるため単品データが必要。' },
]

const stepForm = reactive({
  recoveryAt: '',
  troubleEquipment: '',
  responsePolicy: '',
})
const step3Filters = reactive({
  patternNo: '',
  finishedProduct: '',
  processTime: '',
  thickness: '',
  material: '',
})

const troubleEquipmentOptions = ref([])
const laserPatternOptions = ref([])
const productOptions = ref([])
const selectedPatternIds = ref([])
const step4DetailRows = ref([])
const step4Rows = ref([])
const step5Generated = ref(false)
const step6Generated = ref(false)
const demandRowSeed = ref(0)

const editableSteps = reactive([
  { no: 2, title: 'トラブル設備', detail: 'どの設備でトラブルが起きているかを設備マスタから選択する。', memo: '' },
  { no: 3, title: '加工対象', detail: '手順2で選択した設備の全パータンから対応パータンを絞り込んで選定する。', memo: '' },
  { no: 4, title: '詳細情報と対応方針', detail: '手順3で選定したパータンの詳細確認と応援加工依頼表の作成、対応方針の決定を行う。', memo: '' },
  { no: 5, title: '社内', detail: '社内対応または別設備対応時の内容を記入する。', memo: '' },
  { no: 6, title: '外作', detail: '外作対応時の内容を記入する。', memo: '' },
  { no: 7, title: '加工計画を応援先へ送る', detail: '生産計画シートを参照して送付する。', memo: '' },
])

const normalizeList = (payload) => payload?.results || payload || []

const formatThickness = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return `${num.toFixed(3).replace(/\.?0+$/, '')} mm`
}

const formatMinutes = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return `${num.toFixed(1).replace(/\.0$/, '')} 分/回`
}

const formatIntegerValue = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return String(Math.round(num))
}

const formatDecimalValue = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return ''
  return num.toFixed(1).replace(/\.0$/, '')
}

const formatTakeQtyValue = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return num.toFixed(3).replace(/\.?0+$/, '')
}

const createComponentDisplayItems = (componentItems = []) => {
  if (!Array.isArray(componentItems) || componentItems.length === 0) {
    return [{ rowKey: 'component-empty', code: '-', takeQty: '' }]
  }

  return componentItems.map((component, index) => ({
    rowKey: `component-${index}`,
    code: String(component.component_product_code || '').trim() || '-',
    takeQty: formatTakeQtyValue(component.take_qty),
  }))
}

const filteredLaserPatternOptions = computed(() => {
  const equipmentId = String(stepForm.troubleEquipment || '').trim()
  if (!equipmentId) return []
  return laserPatternOptions.value.filter((pattern) => String(pattern.equipment || '') === equipmentId)
})

const filteredStep3Patterns = computed(() => {
  const patternNoKeyword = String(step3Filters.patternNo || '').trim().toLowerCase()
  const finishedFilter = String(step3Filters.finishedProduct || '').trim()
  const processTimeKeyword = String(step3Filters.processTime || '').trim().toLowerCase()
  const thicknessKeyword = String(step3Filters.thickness || '').trim().toLowerCase()
  const materialKeyword = String(step3Filters.material || '').trim().toLowerCase()

  return filteredLaserPatternOptions.value.filter((pattern) => {
    if (patternNoKeyword && !String(pattern.patternNo || '').toLowerCase().includes(patternNoKeyword)) return false
    const hasFinishedProduct = Array.isArray(pattern.finishedItems) && pattern.finishedItems.length > 0
    if (finishedFilter === 'HAS' && !hasFinishedProduct) return false
    if (finishedFilter === 'NONE' && hasFinishedProduct) return false
    if (processTimeKeyword && !formatMinutes(pattern.processTimeMin).toLowerCase().includes(processTimeKeyword)) return false
    if (thicknessKeyword && !String(pattern.thicknessLabel || '').toLowerCase().includes(thicknessKeyword)) return false
    if (materialKeyword && !String(pattern.materialLabel || '').toLowerCase().includes(materialKeyword)) return false
    return true
  })
})

const selectedPatterns = computed(() => {
  const selectedSet = new Set(selectedPatternIds.value)
  return filteredLaserPatternOptions.value.filter((pattern) => selectedSet.has(pattern.id))
})

const selectedPatternCount = computed(() => selectedPatterns.value.length)

const isPatternSelected = (patternId) => selectedPatternIds.value.includes(patternId)

const togglePatternSelection = (pattern) => {
  const patternId = String(pattern.id || '')
  if (!patternId) return
  if (selectedPatternIds.value.includes(patternId)) {
    selectedPatternIds.value = selectedPatternIds.value.filter((id) => id !== patternId)
    return
  }
  selectedPatternIds.value = [...selectedPatternIds.value, patternId]
}

const clearSelectedPatterns = () => {
  selectedPatternIds.value = []
}

const createDemandRow = (existing = {}) => {
  demandRowSeed.value += 1
  return {
    id: `demand-${demandRowSeed.value}`,
    demandDate: existing.demandDate ?? '',
    requiredQty: existing.requiredQty ?? '',
  }
}

const formatDateLabel = (dateText) => {
  if (!dateText) return ''
  const weekdays = ['日', '月', '火', '水', '木', '金', '土']
  const date = new Date(`${dateText}T00:00:00`)
  if (Number.isNaN(date.getTime())) return dateText
  return `${date.getMonth() + 1}/${date.getDate()}(${weekdays[date.getDay()]})`
}

const syncStep4DetailRows = () => {
  const currentRows = new Map(step4DetailRows.value.map((row) => [row.patternId, row]))
  step4DetailRows.value = selectedPatterns.value.map((pattern) => {
    const existing = currentRows.get(pattern.id)
    return {
      patternId: pattern.id,
      patternNo: pattern.patternNo,
      finishedProductsLabel: pattern.finishedProductsLabel,
      processTimeMin: pattern.processTimeMin,
      thicknessLabel: pattern.thicknessLabel,
      materialLabel: pattern.materialLabel,
      responseType: existing?.responseType ?? stepForm.responsePolicy ?? '',
      demands: Array.isArray(existing?.demands) && existing.demands.length
        ? existing.demands.map((demand) => createDemandRow(demand))
        : [createDemandRow()],
    }
  })
}

const applyResponsePolicy = (policy) => {
  stepForm.responsePolicy = policy
  step4DetailRows.value = step4DetailRows.value.map((row) => ({
    ...row,
    responseType: policy,
  }))
}

const addDemandRow = (patternId) => {
  step4DetailRows.value = step4DetailRows.value.map((row) => {
    if (row.patternId !== patternId) return row
    return {
      ...row,
      demands: [...row.demands, createDemandRow()],
    }
  })
}

const removeDemandRow = (patternId, demandId) => {
  step4DetailRows.value = step4DetailRows.value.map((row) => {
    if (row.patternId !== patternId) return row
    if (row.demands.length === 1) return row
    return {
      ...row,
      demands: row.demands.filter((demand) => demand.id !== demandId),
    }
  })
}

const generatedStep4DateColumns = computed(() => {
  const keys = Array.from(new Set(
    step4DetailRows.value
      .flatMap((row) => row.demands || [])
      .map((demand) => String(demand.demandDate || '').trim())
      .filter(Boolean),
  )).sort()

  return keys.map((key) => ({
    key,
    label: formatDateLabel(key),
  }))
})

const step5SourceRows = computed(() => step4Rows.value.filter((row) => ['IN_HOUSE', 'OTHER_EQUIPMENT'].includes(row.responseType)))
const step6SourceRows = computed(() => step4Rows.value.filter((row) => row.responseType === 'OUTSOURCE'))
const step5Rows = computed(() => (step5Generated.value ? step5SourceRows.value : []))
const step6Rows = computed(() => (step6Generated.value ? step6SourceRows.value : []))

const createEmptyDailyMap = (columns = generatedStep4DateColumns.value) => Object.fromEntries(columns.map((day) => [day.key, '']))

const calculateMaterialUnitWeightKg = (product) => {
  const specificGravity = Number(product?.specific_gravity)
  const length = Number(product?.size_length)
  const width = Number(product?.size_width)
  const thickness = Number(product?.size_thickness)

  if (![specificGravity, length, width, thickness].every((value) => Number.isFinite(value) && value > 0)) return null

  return (specificGravity * length * width * thickness) / 1000000
}

const sumDailyQty = (daily) => {
  const total = Object.values(daily || {}).reduce((sum, value) => sum + Number(value || 0), 0)
  return total || ''
}

const calculateDailyProcessMinutes = (requiredQty, unitPerSet, processTimeMin) => {
  const qty = Number(requiredQty || 0)
  const unit = Number(unitPerSet || 0)
  const processTime = Number(processTimeMin || 0)
  if (!Number.isFinite(qty) || !Number.isFinite(unit) || !Number.isFinite(processTime)) return ''
  if (qty <= 0 || unit <= 0 || processTime <= 0) return ''
  return formatDecimalValue((qty / unit) * processTime)
}

const calculateDailyMaterialRequired = (requiredQty, unitPerSet) => {
  const qty = Number(requiredQty || 0)
  const unit = Number(unitPerSet || 0)
  if (!Number.isFinite(qty) || !Number.isFinite(unit) || qty <= 0 || unit <= 0) return ''
  return formatDecimalValue(qty / unit)
}

const calculateDailyMaterialWeight = (requiredQty, unitPerSet, materialUnitWeightKg) => {
  const materialRequired = Number(calculateDailyMaterialRequired(requiredQty, unitPerSet) || 0)
  const unitWeight = Number(materialUnitWeightKg || 0)
  if (!Number.isFinite(materialRequired) || !Number.isFinite(unitWeight) || materialRequired <= 0 || unitWeight <= 0) return ''
  return formatDecimalValue(materialRequired * unitWeight)
}

const sumDailyProcessMinutes = (daily, unitPerSet, processTimeMin) => {
  const unit = Number(unitPerSet || 0)
  const processTime = Number(processTimeMin || 0)
  if (!Number.isFinite(unit) || !Number.isFinite(processTime) || unit <= 0 || processTime <= 0) return ''

  const total = Object.values(daily || {}).reduce((sum, value) => sum + Number(value || 0), 0)
  if (!Number.isFinite(total) || total <= 0) return ''

  return formatDecimalValue((total / unit) * processTime)
}

const sumDailyMaterialRequired = (daily, unitPerSet) => {
  const unit = Number(unitPerSet || 0)
  if (!Number.isFinite(unit) || unit <= 0) return ''

  const total = Object.values(daily || {}).reduce((sum, value) => sum + Number(value || 0), 0)
  if (!Number.isFinite(total) || total <= 0) return ''

  return formatDecimalValue(total / unit)
}

const sumDailyMaterialWeight = (daily, unitPerSet, materialUnitWeightKg) => {
  const materialRequired = Number(sumDailyMaterialRequired(daily, unitPerSet) || 0)
  const unitWeight = Number(materialUnitWeightKg || 0)
  if (!Number.isFinite(materialRequired) || !Number.isFinite(unitWeight) || materialRequired <= 0 || unitWeight <= 0) return ''
  return formatDecimalValue(materialRequired * unitWeight)
}

const sumPlanColumn = (rows, getter) => {
  const total = rows.reduce((sum, row) => {
    const value = Number(getter(row) || 0)
    return Number.isFinite(value) ? sum + value : sum
  }, 0)

  return total > 0 ? formatDecimalValue(total) : ''
}

const buildPlanTotals = (rows) => {
  const daily = Object.fromEntries(generatedStep4DateColumns.value.map((day) => {
    const qty = rows.reduce((sum, row) => sum + Number(row.daily?.[day.key] || 0), 0)
    const minutes = rows.reduce((sum, row) => {
      const value = Number(calculateDailyProcessMinutes(row.daily?.[day.key], row.unitPerSet, row.processTimeMin) || 0)
      return sum + (Number.isFinite(value) ? value : 0)
    }, 0)
    const materialRequired = rows.reduce((sum, row) => {
      const value = Number(calculateDailyMaterialRequired(row.daily?.[day.key], row.unitPerSet) || 0)
      return sum + (Number.isFinite(value) ? value : 0)
    }, 0)
    const weight = rows.reduce((sum, row) => {
      const value = Number(calculateDailyMaterialWeight(row.daily?.[day.key], row.unitPerSet, row.materialUnitWeightKg) || 0)
      return sum + (Number.isFinite(value) ? value : 0)
    }, 0)

    return [day.key, {
      qty: qty > 0 ? formatDecimalValue(qty) : '',
      minutes: minutes > 0 ? formatDecimalValue(minutes) : '',
      materialRequired: materialRequired > 0 ? formatDecimalValue(materialRequired) : '',
      weight: weight > 0 ? formatDecimalValue(weight) : '',
    }]
  }))

  return {
    requestQty: sumPlanColumn(rows, (row) => row.requestQty),
    requiredPerDay: sumPlanColumn(rows, (row) => row.requiredPerDay),
    daily,
    totalQty: sumPlanColumn(rows, (row) => sumDailyQty(row.daily)),
    totalMinutes: sumPlanColumn(rows, (row) => sumDailyProcessMinutes(row.daily, row.unitPerSet, row.processTimeMin)),
    totalMaterialRequired: sumPlanColumn(rows, (row) => sumDailyMaterialRequired(row.daily, row.unitPerSet)),
    totalWeight: sumPlanColumn(rows, (row) => sumDailyMaterialWeight(row.daily, row.unitPerSet, row.materialUnitWeightKg)),
  }
}

const step4Totals = computed(() => buildPlanTotals(step4Rows.value))
const step5Totals = computed(() => buildPlanTotals(step5Rows.value))
const step6Totals = computed(() => buildPlanTotals(step6Rows.value))

const buildStep4Rows = () => {
  const detailRowMap = new Map(step4DetailRows.value.map((row) => [row.patternId, row]))
  const currentRows = new Map(step4Rows.value.map((row) => [row.rowKey, row]))
  const currentColumns = generatedStep4DateColumns.value
  const nextRows = []

  selectedPatterns.value.forEach((pattern, patternIndex) => {
    const detailRow = detailRowMap.get(pattern.id)
    const dailyFromDemand = createEmptyDailyMap(currentColumns)
    const demandTotalQty = Array.isArray(detailRow?.demands)
      ? detailRow.demands.reduce((sum, demand) => {
        const qty = Number(demand.requiredQty || 0)
        if (demand.demandDate && Object.hasOwn(dailyFromDemand, demand.demandDate)) {
          dailyFromDemand[demand.demandDate] = Number(dailyFromDemand[demand.demandDate] || 0) + qty
        }
        return sum + qty
      }, 0)
      : 0
    const finishedItems = Array.isArray(pattern.finishedItems) && pattern.finishedItems.length
      ? pattern.finishedItems
      : [{ finished_product_code: pattern.patternNo, finished_product_name: '', units_per_shot: '' }]

    finishedItems.forEach((finished, finishedIndex) => {
      const rowKey = `${pattern.id}-${finishedIndex}`
      const existing = currentRows.get(rowKey)
      nextRows.push({
        patternId: pattern.id,
        rowKey,
        groupLabel: pattern.patternNo,
        componentItems: pattern.componentItems,
        commonName: existing?.commonName ?? pattern.commonName ?? '',
        thickness: pattern.thicknessLabel,
        materialPerDay: existing?.materialPerDay ?? '',
        productWeightPerDay: existing?.productWeightPerDay ?? '',
        partNo: String(finished.finished_product_code || pattern.patternNo || '').trim(),
        processTimeMin: existing?.processTimeMin ?? pattern.processTimeMin,
        materialUnitWeightKg: pattern.materialUnitWeightKg,
        unitPerSet: existing?.unitPerSet ?? formatIntegerValue(finished.units_per_shot),
        responseType: detailRow?.responseType ?? existing?.responseType ?? stepForm.responsePolicy ?? '',
        requestQty: demandTotalQty || '',
        requiredPerDay: existing?.requiredPerDay ?? '',
        daily: dailyFromDemand,
      })
    })
  })

  step4Rows.value = nextRows
}

const generateStep4Table = () => {
  buildStep4Rows()
}

const clearStep4Table = () => {
  step4Rows.value = []
  step5Generated.value = false
  step6Generated.value = false
}

const generateStep5Table = () => {
  step5Generated.value = true
}

const clearStep5Table = () => {
  step5Generated.value = false
}

const generateStep6Table = () => {
  step6Generated.value = true
}

const clearStep6Table = () => {
  step6Generated.value = false
}

const formatQty = (value) => (value === null || value === undefined ? '' : value)

const buildPlanExportSheetData = (rows, totals) => {
  const dateHeaders = generatedStep4DateColumns.value.flatMap((day) => ([
    `${day.label}_必要数`,
    `${day.label}_分/日`,
    `${day.label}_材料枚数`,
    `${day.label}_重量`,
  ]))

  const headers = [
    'ネスティングNo.',
    '完成品番',
    '構成子品番',
    '子取り数',
    '俗称',
    '板厚',
    '材料仕込/日',
    '製品重量/日',
    '加工時間',
    '個/枚（取り数）',
    '依頼数',
    '平均必要数 個/日',
    ...dateHeaders,
    '合計数量',
    '合計時間',
    '合計枚数',
    '合計重量',
  ]

  const body = []
  const merges = []
  const mergeColumns = [0, 1, 4, 5, 6, 7, 8, 9, 10, 11]
  const dayColumnStart = 12
  const dayColumnCount = generatedStep4DateColumns.value.length * 4
  const totalColumnStart = dayColumnStart + dayColumnCount

  rows.forEach((row) => {
    const components = Array.isArray(row.componentItems) && row.componentItems.length ? row.componentItems : [{ code: '', takeQty: '' }]
    const groupStartRowIndex = body.length + 1

    components.forEach((component, index) => {
      body.push([
        index === 0 ? row.groupLabel || '' : '',
        index === 0 ? row.partNo || '' : '',
        component.code || '',
        component.takeQty || '',
        index === 0 ? row.commonName || '' : '',
        index === 0 ? row.thickness || '' : '',
        index === 0 ? row.materialPerDay || '' : '',
        index === 0 ? row.productWeightPerDay || '' : '',
        index === 0 ? formatMinutes(row.processTimeMin) : '',
        index === 0 ? row.unitPerSet || '' : '',
        index === 0 ? row.requestQty || '' : '',
        index === 0 ? row.requiredPerDay || '' : '',
        ...generatedStep4DateColumns.value.flatMap((day) => (index === 0
          ? [
            row.daily?.[day.key] || '',
            calculateDailyProcessMinutes(row.daily?.[day.key], row.unitPerSet, row.processTimeMin),
            calculateDailyMaterialRequired(row.daily?.[day.key], row.unitPerSet),
            calculateDailyMaterialWeight(row.daily?.[day.key], row.unitPerSet, row.materialUnitWeightKg),
          ]
          : ['', '', '', ''])),
        index === 0 ? sumDailyQty(row.daily) : '',
        index === 0 ? sumDailyProcessMinutes(row.daily, row.unitPerSet, row.processTimeMin) : '',
        index === 0 ? sumDailyMaterialRequired(row.daily, row.unitPerSet) : '',
        index === 0 ? sumDailyMaterialWeight(row.daily, row.unitPerSet, row.materialUnitWeightKg) : '',
      ])
    })

    if (components.length > 1) {
      const groupEndRowIndex = groupStartRowIndex + components.length - 1
      mergeColumns.forEach((columnIndex) => {
        merges.push({ s: { r: groupStartRowIndex, c: columnIndex }, e: { r: groupEndRowIndex, c: columnIndex } })
      })
      for (let columnIndex = dayColumnStart; columnIndex < totalColumnStart + 4; columnIndex += 1) {
        merges.push({ s: { r: groupStartRowIndex, c: columnIndex }, e: { r: groupEndRowIndex, c: columnIndex } })
      }
    }
  })

  const totalRow = [
    '合計',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    totals?.requestQty || '',
    totals?.requiredPerDay || '',
    ...generatedStep4DateColumns.value.flatMap((day) => ([
      totals?.daily?.[day.key]?.qty || '',
      totals?.daily?.[day.key]?.minutes || '',
      totals?.daily?.[day.key]?.materialRequired || '',
      totals?.daily?.[day.key]?.weight || '',
    ])),
    totals?.totalQty || '',
    totals?.totalMinutes || '',
    totals?.totalMaterialRequired || '',
    totals?.totalWeight || '',
  ]

  const totalRowIndex = body.length + 1
  merges.push({ s: { r: totalRowIndex, c: 0 }, e: { r: totalRowIndex, c: 9 } })

  return {
    rows: [headers, ...body, totalRow],
    merges,
  }
}

const exportPlanTable = (rows, totals, fileLabel) => {
  if (!Array.isArray(rows) || rows.length === 0) return
  const sheetData = buildPlanExportSheetData(rows, totals)
  const ws = XLSX.utils.aoa_to_sheet(sheetData.rows)
  ws['!merges'] = sheetData.merges
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '計画表')
  XLSX.writeFile(wb, `${fileLabel}.xlsx`)
}

const exampleDateColumns = [
  { key: '2026-08-19', label: '8/19(水)' },
  { key: '2026-08-20', label: '8/20(木)' },
  { key: '2026-08-21', label: '8/21(金)' },
  { key: '2026-08-24', label: '8/24(月)' },
  { key: '2026-08-25', label: '8/25(火)' },
  { key: '2026-08-26', label: '8/26(水)' },
]

const exampleRows = [
  { rowKey: '1-V053143612-01', nestingNo: 1, commonName: 'クボタ ラジエータ', thickness: 'SS400/t6.0', materialPerDay: '2.0t', productWeightPerDay: '1.6t', partNo: 'V053143612-01', unitPerSet: 1, requestQty: 460, daily: { '2026-08-19': 72, '2026-08-20': 92, '2026-08-21': 92, '2026-08-24': 92, '2026-08-25': 92, '2026-08-26': 92 }, totalQty: 532 },
  { rowKey: '1-V053143612-10', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'V053143612-10', unitPerSet: 1, requestQty: 460, daily: { '2026-08-19': 72, '2026-08-20': 92, '2026-08-21': 92, '2026-08-24': 92, '2026-08-25': 92, '2026-08-26': 92 }, totalQty: 532 },
  { rowKey: '1-V053143612-17', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'V053143612-17', unitPerSet: 1, requestQty: 460, daily: { '2026-08-19': 72, '2026-08-20': 92, '2026-08-21': 92, '2026-08-24': 92, '2026-08-25': 92, '2026-08-26': 92 }, totalQty: 532 },
  { rowKey: '1-V053143612-18', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'V053143612-18', unitPerSet: 1, requestQty: 460, daily: { '2026-08-19': 72, '2026-08-20': 92, '2026-08-21': 92, '2026-08-24': 92, '2026-08-25': 92, '2026-08-26': 92 }, totalQty: 532 },
  { rowKey: '2-YD40006000-00', nestingNo: 2, commonName: 'フロアプレート（6000）', thickness: 'SS400/t6.0', materialPerDay: '0.4t', productWeightPerDay: '0.4t', partNo: 'YD40006000-00', unitPerSet: 1, requestQty: 36, daily: { '2026-08-19': null, '2026-08-20': 8, '2026-08-21': 8, '2026-08-24': 8, '2026-08-25': 8, '2026-08-26': 8 }, totalQty: 40 },
  { rowKey: '2-YD40005598-09', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'YD40005598-09', unitPerSet: 2, requestQty: 72, daily: { '2026-08-19': null, '2026-08-20': 15, '2026-08-21': 15, '2026-08-24': 15, '2026-08-25': 15, '2026-08-26': 15 }, totalQty: 75 },
  { rowKey: '2-YD40004738-29', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'YD40004738-29', unitPerSet: 1, requestQty: 36, daily: { '2026-08-19': null, '2026-08-20': 8, '2026-08-21': 8, '2026-08-24': 8, '2026-08-25': 8, '2026-08-26': 8 }, totalQty: 40 },
  { rowKey: '3-YD40004397-00', nestingNo: 3, commonName: 'フロアプレート（4397）', thickness: 'SS400/t6.0', materialPerDay: '0.4t', productWeightPerDay: '0.4t', partNo: 'YD40004397-00', unitPerSet: 1, requestQty: 34, daily: { '2026-08-19': null, '2026-08-20': 7, '2026-08-21': 7, '2026-08-24': 7, '2026-08-25': 7, '2026-08-26': 7 }, totalQty: 35 },
  { rowKey: '3-YD40005598-09', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'YD40005598-09', unitPerSet: 2, requestQty: 68, daily: { '2026-08-19': null, '2026-08-20': 14, '2026-08-21': 14, '2026-08-24': 14, '2026-08-25': 14, '2026-08-26': 14 }, totalQty: 70 },
  { rowKey: '3-YD40004738-29', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'YD40004738-29', unitPerSet: 1, requestQty: 34, daily: { '2026-08-19': null, '2026-08-20': 7, '2026-08-21': 7, '2026-08-24': 7, '2026-08-25': 7, '2026-08-26': 7 }, totalQty: 35 },
  { rowKey: '4-V05314352-01', nestingNo: 4, commonName: 'クボタ ファンBKT', thickness: 'SS400/t6.0', materialPerDay: '2.0t', productWeightPerDay: '1.6t', partNo: 'V05314352-01', unitPerSet: 1, requestQty: 440, daily: { '2026-08-19': null, '2026-08-20': 88, '2026-08-21': 88, '2026-08-24': 88, '2026-08-25': 88, '2026-08-26': 88 }, totalQty: 440 },
  { rowKey: '4-V053143521-02', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'V053143521-02', unitPerSet: 4, requestQty: 1760, daily: { '2026-08-19': null, '2026-08-20': 352, '2026-08-21': 352, '2026-08-24': 352, '2026-08-25': 352, '2026-08-26': 352 }, totalQty: 1760 },
  { rowKey: '4-V053143521-03', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'V053143521-03', unitPerSet: 1, requestQty: 440, daily: { '2026-08-19': null, '2026-08-20': 88, '2026-08-21': 88, '2026-08-24': 88, '2026-08-25': 88, '2026-08-26': 88 }, totalQty: 440 },
  { rowKey: '4-V053143612-06', nestingNo: '', commonName: '', thickness: '', materialPerDay: '', productWeightPerDay: '', partNo: 'V053143612-06', unitPerSet: 4, requestQty: 1760, daily: { '2026-08-19': null, '2026-08-20': 352, '2026-08-21': 352, '2026-08-24': 352, '2026-08-25': 352, '2026-08-26': 352 }, totalQty: 1760 },
]

const fetchTroubleEquipments = async () => {
  try {
    const response = await api.equipments.getEquipments({ ordering: 'display_order,equipment_code' })
    const rows = normalizeList(response.data)
    troubleEquipmentOptions.value = rows
      .filter((item) => item && item.is_active !== false)
      .map((item) => {
        const code = String(item.equipment_code || '').trim()
        const name = String(item.equipment_name || '').trim()
        return {
          id: String(item.id),
          label: code && name ? `${code} - ${name}` : (name || code),
        }
      })
      .filter((item) => item.id && item.label)
  } catch (error) {
    console.error('設備マスタ取得エラー:', error)
    troubleEquipmentOptions.value = []
  }
}

const fetchLaserPatterns = async () => {
  try {
    const response = await api.laserPatterns.getLaserPatterns({ page_size: 500 })
    const rows = normalizeList(response.data)
    laserPatternOptions.value = rows
      .map((item) => {
        const materialCode = String(item.material_code || '').trim()
        const materialName = String(item.material_name || '').trim()
        const finishedItems = Array.isArray(item.finished_items) ? item.finished_items : []
        const finishedProductsLabel = finishedItems.length
          ? finishedItems
            .map((finished) => {
              const code = String(finished.finished_product_code || '').trim()
              const name = String(finished.finished_product_name || '').trim()
              return code && name ? `${code} ${name}` : (code || name || '-')
            })
            .join(' / ')
          : '-'
        const materialProduct = productOptions.value.find((product) => String(product.id || '') === String(item.material || ''))
        const componentItems = createComponentDisplayItems(item.component_items)
        return {
          id: String(item.id),
          equipment: String(item.equipment || ''),
          patternNo: String(item.pattern_no || '').trim(),
          commonName: finishedItems[0]?.finished_product_name || '',
          finishedProductsLabel,
          finishedItems,
          componentItems,
          processTimeMin: item.process_time_min,
          thicknessLabel: formatThickness(materialProduct?.size_thickness),
          materialLabel: materialCode && materialName ? `${materialCode} ${materialName}` : (materialCode || materialName || '-'),
          materialUnitWeightKg: calculateMaterialUnitWeightKg(materialProduct),
        }
      })
      .filter((item) => item.id && item.equipment && item.patternNo)
  } catch (error) {
    console.error('レーザーパタン取得エラー:', error)
    laserPatternOptions.value = []
  }
}

const fetchProducts = async () => {
  try {
    const response = await api.products.getAllProducts({ page_size: 5000, is_active: true })
    productOptions.value = normalizeList(response?.data ?? response)
  } catch (error) {
    console.error('製品マスタ取得エラー:', error)
    productOptions.value = []
  }
}

onMounted(async () => {
  await Promise.all([fetchTroubleEquipments(), fetchProducts()])
  await fetchLaserPatterns()
})

watch(
  () => stepForm.troubleEquipment,
  () => {
    clearSelectedPatterns()
    stepForm.responsePolicy = ''
    step4DetailRows.value = []
    step3Filters.patternNo = ''
    step3Filters.finishedProduct = ''
    step3Filters.processTime = ''
    step3Filters.thickness = ''
    step3Filters.material = ''
    clearStep4Table()
  },
)

watch(
  selectedPatterns,
  () => {
    syncStep4DetailRows()
    clearStep4Table()
  },
  { deep: true },
)

watch(
  step4DetailRows,
  (rows) => {
    const responseTypeMap = new Map(rows.map((row) => [row.patternId, row.responseType]))
    step4Rows.value = step4Rows.value.map((row) => ({
      ...row,
      responseType: responseTypeMap.get(row.patternId) ?? row.responseType,
    }))
  },
  { deep: true },
)
</script>

<style scoped>
.laser-trouble-page {
  padding: 16px;
  display: grid;
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgba(251, 191, 36, 0.2), transparent 28%),
    linear-gradient(180deg, #fff7ed 0%, #fff 48%, #f8fafc 100%);
}
.hero,
.panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  padding: 16px;
}
.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #9a3412;
}
.page-title {
  margin: 0;
  font-size: 24px;
  color: #7c2d12;
}
.hero-text {
  margin: 8px 0 0;
  line-height: 1.6;
}
.tab-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.tab-button {
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid #fdba74;
  border-radius: 999px;
  background: #fff7ed;
  color: #9a3412;
  font-weight: 700;
  cursor: pointer;
}
.tab-button.active {
  background: #9a3412;
  color: #fff;
  border-color: #9a3412;
}
.panel-header {
  margin-bottom: 12px;
}
.panel-header h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}
.panel-header p {
  margin: 4px 0 0;
  color: #475569;
}
.step-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.step-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.step-item {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid #fed7aa;
  border-radius: 12px;
  background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%);
}
.step-no {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: #ea580c;
  color: #fff;
  font-weight: 700;
  display: grid;
  place-items: center;
}
.step-title {
  font-weight: 700;
  color: #7c2d12;
}
.compact-step {
  height: 100%;
}
.step-detail,
.note-text {
  margin: 4px 0 0;
  line-height: 1.6;
  color: #334155;
}
.field {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}
.field-label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}
.field-input,
.step-textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #fff;
  color: #0f172a;
}
.field-input {
  min-height: 36px;
  padding: 0 10px;
}
.field-help {
  font-size: 12px;
  color: #64748b;
}
.policy-section {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}
.policy-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.policy-button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #fdba74;
  border-radius: 999px;
  background: #fff7ed;
  color: #9a3412;
  font-weight: 700;
  cursor: pointer;
}
.policy-button.active {
  background: #9a3412;
  border-color: #9a3412;
  color: #fff;
}
.selection-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 4px;
  color: #7c2d12;
  font-size: 13px;
  font-weight: 700;
}
.mini-action {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #fdba74;
  border-radius: 999px;
  background: #fff7ed;
  color: #9a3412;
  cursor: pointer;
}
.mini-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.step-textarea {
  padding: 10px;
  resize: vertical;
  margin-top: 8px;
}
.sub-notes {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.note-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  padding: 12px;
}
.note-title {
  font-weight: 700;
  color: #0f172a;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.summary-card {
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
  border: 1px solid #fed7aa;
}
.summary-label {
  font-size: 12px;
  color: #9a3412;
  margin-bottom: 4px;
}
.summary-value {
  font-weight: 700;
  line-height: 1.5;
}
.table-wrap {
  overflow-x: auto;
}
.plan-table {
  width: 100%;
  min-width: 1220px;
  border-collapse: collapse;
  font-size: 13px;
}
.plan-table th,
.plan-table td {
  border: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: center;
  white-space: nowrap;
}
.plan-table thead th {
  background: #7c2d12;
  color: #fff;
  position: sticky;
  top: 0;
}
.code-cell {
  text-align: left;
  font-family: Consolas, "Courier New", monospace;
}
.component-cell {
  min-width: 220px;
  text-align: left;
  white-space: normal;
  line-height: 1.4;
}
.target-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}
.target-table th,
.target-table td {
  border: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}
.target-table thead th {
  background: #9a3412;
  color: #fff;
  position: sticky;
  top: 0;
}
.select-cell {
  width: 72px;
  text-align: center;
}
.filter-row th {
  background: #fff7ed;
  color: #0f172a;
}
.filter-row .filter-input {
  width: 100%;
  min-height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  background: #fff;
  color: #0f172a;
}
.target-code-cell {
  white-space: nowrap;
  font-family: Consolas, "Courier New", monospace;
}
.target-finished-cell {
  min-width: 260px;
}
.detail-table {
  margin-top: 4px;
}
.detail-action-cell {
  white-space: nowrap;
  text-align: center;
}
.table-edit-select {
  width: 100%;
  min-height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  background: #fff;
  color: #0f172a;
}
.step4-plan-wrap {
  margin-top: 12px;
  border: 1px solid #f1d2b2;
  border-radius: 14px;
  background: linear-gradient(180deg, #fffdf8 0%, #fff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
  padding: 8px;
}
.generate-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.step4-plan-table {
  min-width: 1500px;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
}
.step4-plan-table th,
.step4-plan-table td {
  padding: 6px 4px;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: middle;
}
.step4-plan-table th:first-child,
.step4-plan-table td:first-child {
  border-left: 1px solid #e5e7eb;
}
.step4-plan-table thead tr:first-child th {
  background: linear-gradient(180deg, #8f3d16 0%, #7c2d12 100%);
  font-size: 11px;
  letter-spacing: 0.02em;
}
.step4-plan-table thead tr:nth-child(2) th {
  background: #9a3412;
  font-size: 11px;
}
.step4-plan-table thead tr:nth-child(3) th {
  background: #b45309;
  font-size: 10px;
  font-weight: 700;
}
.step4-plan-table tbody tr:nth-child(odd) td {
  background: #fffaf5;
}
.step4-plan-table tbody tr:hover td {
  background: #fff1e6;
}
.step4-plan-table .code-cell,
.step4-plan-table .component-cell {
  background-clip: padding-box;
}
.step4-plan-table .component-cell {
  line-height: 1.3;
}
.step4-plan-table .total-row td {
  background: #fff0db !important;
  font-weight: 700;
  color: #7c2d12;
}
.step4-plan-table .total-row td:first-child {
  text-align: center;
}
.step4-plan-table .table-edit-input {
  padding: 0 6px;
  min-height: 30px;
  border: 1px solid #d7dee8;
  border-radius: 7px;
  background: #ffffff;
  box-shadow: inset 0 1px 1px rgba(15, 23, 42, 0.04);
}
.step4-plan-table .component-cell {
  min-width: 0;
}
.step4-plan-table .table-edit-input:focus {
  outline: none;
  border-color: #ea580c;
  box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.12);
}
.step4-plan-table td {
  font-variant-numeric: tabular-nums;
}
.step4-plan-table td:not(.code-cell):not(.component-cell) {
  text-align: center;
}
.col-nesting {
  width: 72px;
}
.col-finished-part {
  width: 106px;
}
.col-component-part {
  width: 165px;
}
.col-common-name {
  width: 170px;
}
.col-thickness {
  width: 40px;
}
.col-small-num {
  width: 56px;
}
.col-mid-num {
  width: 62px;
}
.col-unit-set {
  width: 86px;
}
.col-day-num {
  width: 58px;
}
.col-day-material {
  width: 64px;
}
.table-edit-input {
  width: 100%;
  min-height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  background: #fff;
  color: #0f172a;
}
.table-edit-input-num {
  text-align: right;
}
.empty-cell {
  text-align: center;
  color: #64748b;
}

@media (max-width: 960px) {
  .step-row,
  .sub-notes,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
