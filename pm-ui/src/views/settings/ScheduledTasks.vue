<template>
  <div class="settings-container">
    <div class="page-header">
      <h2 class="page-title">定時タスク設定 <DataSourceDialog title="定時タスク設定" :sources="dsSources" /></h2>
      <button class="btn" type="button" @click="openManual">マニュアル</button>
    </div>

    <div class="card" v-if="showAutoPlanSection">
      <div class="card-header">
        <div>
          <div class="card-title">生産計画自動生成（需要→計画上書き）</div>
          <p class="helper">
            毎月指定日・時刻に需要取り込みのみ実行し、指定月の計画を需要で上書きします。対象月（今月／翌月／翌々月／翌々翌月）をラインごとに選択できます。
          </p>
          <p v-if="autoPlanLocked" class="helper warning">
            順序運用モードのため、この画面の自動計画設定は読み取り専用です。編集は「自動計画」画面で行ってください。
          </p>
        </div>
      </div>

      <div class="table-wrapper" v-if="autoPlanConfigs.length">
        <table class="config-table">
          <thead>
            <tr>
              <th style="width: 150px">ライン</th>
              <th style="width: 170px">実行タイミング</th>
              <th style="width: 180px">対象期間</th>
              <th style="width: 80px">有効</th>
              <th style="width: 200px">失敗時通知先</th>
              <th style="width: 180px">操作</th>
              <th>最終実行情報</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cfg in autoPlanConfigs" :key="configKey(cfg)">
              <td>
                <div class="line-name">{{ cfg.line_name || 'ライン未設定' }}</div>
                <div v-if="cfg.line_code" class="line-code">({{ cfg.line_code }})</div>
              </td>
              <td>
                <div class="time-row">
                  <input
                    type="number"
                    min="1"
                    max="31"
                    v-model.number="cfg.scheduled_dom"
                    :disabled="!canEditAutoPlan"
                    class="time-input"
                  />
                  <span class="suffix">日</span>
                </div>
                <div class="time-row">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    v-model.number="cfg.scheduled_hour"
                    :disabled="!canEditAutoPlan"
                    class="time-input"
                  />
                  <span class="suffix">時</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    v-model.number="cfg.scheduled_minute"
                    :disabled="!canEditAutoPlan"
                    class="time-input"
                  />
                  <span class="suffix">分</span>
                </div>
              </td>
              <td class="period-cell">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_current_month" :disabled="!canEditAutoPlan" />
                  今月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_next_month" :disabled="!canEditAutoPlan" />
                  翌月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_second_month" :disabled="!canEditAutoPlan" />
                  翌々月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_third_month" :disabled="!canEditAutoPlan" />
                  翌々翌月
                </label>
              </td>
              <td>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEditAutoPlan" />
                  有効
                </label>
              </td>
              <td class="notify-cell">
                <div class="notify-search">
                  <input
                    v-model="cfg.searchCode"
                    :disabled="!canEditAutoPlan"
                    class="notify-search-input"
                    placeholder="社員コード/氏名/ユーザー名で検索して追加"
                    @keyup.enter.prevent="addFirstCandidate(cfg)"
                  />
                </div>
                <div
                  v-if="candidateList(cfg).length"
                  class="candidate-list"
                >
                  <div
                    v-for="u in candidateList(cfg)"
                    :key="u.id"
                    class="candidate-item"
                    @click="addUser(cfg, u)"
                  >
                    <span class="candidate-code">{{ codeLabel(u) }}</span>
                    <span class="candidate-name">{{ nameLabel(u) }}</span>
                  </div>
                </div>
                <div class="selected-list" v-if="cfg.notify_user_codes.length">
                  <span
                    class="chip"
                    v-for="code in cfg.notify_user_codes"
                    :key="code"
                  >
                    <span class="chip-code">{{ code }}</span>
                    <span class="chip-name">{{ chipName(cfg, code) }}</span>
                    <button
                      type="button"
                      class="chip-remove"
                      :disabled="!canEditAutoPlan"
                      @click="removeCode(cfg, code)"
                    >
                      ×
                    </button>
                  </span>
                </div>
              </td>
              <td class="actions-cell">
                <button
                  class="btn primary"
                  @click="saveConfig(cfg)"
                  :disabled="saving.has(configKey(cfg)) || !canEditAutoPlan"
                >
                  {{ saving.has(configKey(cfg)) ? '保存中...' : '保存' }}
                </button>
                <button
                  class="btn"
                  @click="runNow(cfg)"
                  :disabled="isRunNowDisabled(cfg)"
                >
                  {{ runNowLabel(cfg) }}
                </button>
              </td>
              <td class="last-cell">
                <div class="last-row">
                  <span class="last-label">日時</span>
                  <span>{{ formatDateTime(cfg.last_run_at) }}</span>
                </div>
                <div class="last-row">
                  <span class="last-label">結果</span>
                  <span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span>
                </div>
                <div class="message-cell">{{ cfg.last_run_message || '-' }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="helper warning">生産ラインの設定が見つかりません。</p>
    </div>

    <template v-if="showInventorySection">
    <div
      class="card inventory-tone-card"
      :class="cardToneClass(idx)"
      v-for="(cfg, idx) in inventoryTaskConfigs"
      :key="configKey(cfg)"
    >
      <div class="field">
        <label>{{ inventoryTaskLabel(cfg.task_name) }} - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="cfg.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="cfg.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">{{ inventoryTaskHelp(cfg.task_name) }}</p>
      </div>

      <div v-if="showInventoryRangeSetting(cfg.task_name)" class="field" style="margin-top: 12px">
        <label>{{ showRangeBaseDay(cfg.task_name) ? '計算期間' : '対象期間' }}</label>
        <div class="input-row">
          <template v-if="showRangeBaseDay(cfg.task_name)">
            <select v-model="cfg.range_base_day" :disabled="!canEdit" class="date-input">
              <option value="TODAY">今日</option>
              <option value="YESTERDAY">昨日</option>
              <option value="TWO_DAYS_AGO">一昨日</option>
            </select>
            <span class="suffix">から</span>
          </template>
          <template v-else>
            <span class="suffix">今日から</span>
          </template>
          <input
            type="number"
            min="0"
            max="365"
            v-model.number="cfg.range_days_after"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日後</span>
        </div>
        <p class="helper">
          終了日のみ指定。開始日は製品ごとのリードタイムから自動決定されます（今日 − (最大LT + 1)営業日）。業務日付は8時境界です。
        </p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>失敗時通知先</label>
        <div class="notify-search">
          <input
            v-model="cfg.searchCode"
            :disabled="!canEdit"
            class="notify-search-input"
            placeholder="社員コード/氏名/ユーザー名で検索して追加"
            @keyup.enter.prevent="addFirstCandidate(cfg)"
          />
        </div>
        <div
          v-if="candidateList(cfg).length"
          class="candidate-list"
        >
          <div
            v-for="u in candidateList(cfg)"
            :key="u.id"
            class="candidate-item"
            @click="addUser(cfg, u)"
          >
            <span class="candidate-code">{{ codeLabel(u) }}</span>
            <span class="candidate-name">{{ nameLabel(u) }}</span>
          </div>
        </div>
        <div class="selected-list" v-if="cfg.notify_user_codes.length">
          <span
            class="chip"
            v-for="code in cfg.notify_user_codes"
            :key="code"
          >
            <span class="chip-code">{{ code }}</span>
            <span class="chip-name">{{ chipName(cfg, code) }}</span>
            <button
              type="button"
              class="chip-remove"
              :disabled="!canEdit"
              @click="removeCode(cfg, code)"
            >
              ×
            </button>
          </span>
        </div>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(cfg)"
          :disabled="saving.has(configKey(cfg)) || !canEdit"
        >
          {{ saving.has(configKey(cfg)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(cfg)"
          :disabled="isRunNowDisabled(cfg)"
          style="margin-left: 8px"
        >
          {{ runNowLabel(cfg) }}
        </button>
        <button
          v-if="canCancelTask(cfg) && isRunningStatus(cfg)"
          class="btn cancel"
          @click="cancelRun(cfg)"
          :disabled="cancelling.has(configKey(cfg)) || isCancelRequested(cfg) || !canEdit"
          style="margin-left: 8px"
        >
          {{ isCancelRequested(cfg) ? 'キャンセル要求中...' : (cancelling.has(configKey(cfg)) ? '要求中...' : 'キャンセル要求') }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="cfg.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(cfg.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ cfg.last_run_duration_seconds != null ? cfg.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ cfg.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    </template>

    <div class="card inventory-tone-card inventory-tone-a" v-if="showInventorySection">
      <div class="field">
        <label>計画実績自動セット（ライン・工程別）</label>
        <p class="helper">
          指定時刻に、当日（業務日付・8時境界）の計画合計を実績へ反映します。対象は当日分のみです。既存実績が０より大きい品番は上書きせず、スキップします。
        </p>
      </div>
      <div class="input-row" style="margin-top: 8px">
        <select v-model="newPlanToActual.line_id" class="date-input" :disabled="!canEdit">
          <option value="">ライン選択</option>
          <option v-for="line in selectableLines" :key="line.id" :value="line.id">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
        <select v-model="newPlanToActual.process_id" class="date-input" :disabled="!canEdit || !newPlanToActual.line_id">
          <option value="">工程選択</option>
          <option v-for="proc in selectableProcessesForNew" :key="proc.id" :value="proc.id">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
        <button class="btn" @click="addPlanToActualConfig" :disabled="!canEdit">追加</button>
      </div>
      <div class="table-wrapper" style="margin-top: 12px" v-if="planToActualConfigs.length">
        <table class="config-table">
          <thead>
            <tr>
              <th>ライン</th>
              <th>工程</th>
              <th>実行時刻</th>
              <th>有効</th>
              <th>操作</th>
              <th>最終実行情報</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cfg in planToActualConfigs" :key="configKey(cfg)">
              <td>{{ cfg.line_code || '-' }}</td>
              <td>{{ cfg.process_code || '-' }}</td>
              <td>
                <div class="time-row">
                  <input type="number" min="0" max="23" v-model.number="cfg.scheduled_hour" :disabled="!canEdit" class="time-input" />
                  <span class="suffix">時</span>
                  <input type="number" min="0" max="59" v-model.number="cfg.scheduled_minute" :disabled="!canEdit" class="time-input" />
                  <span class="suffix">分</span>
                </div>
              </td>
              <td>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />
                  有効
                </label>
              </td>
              <td class="actions-cell">
                <button class="btn primary" @click="saveConfig(cfg)" :disabled="saving.has(configKey(cfg)) || !canEdit">
                  {{ saving.has(configKey(cfg)) ? '保存中...' : '保存' }}
                </button>
                <button
                  v-if="cfg.is_draft"
                  class="btn"
                  @click="removePlanToActualDraft(cfg)"
                  :disabled="saving.has(configKey(cfg)) || !canEdit"
                >
                  キャンセル
                </button>
                <button class="btn" @click="runNow(cfg)" :disabled="isRunNowDisabled(cfg)">
                  {{ runNowLabel(cfg) }}
                </button>
              </td>
              <td class="last-cell">
                <div class="last-row"><span class="last-label">日時</span><span>{{ formatDateTime(cfg.last_run_at) }}</span></div>
                <div class="last-row"><span class="last-label">結果</span><span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span></div>
                <div class="message-cell">{{ cfg.last_run_message || '-' }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card inventory-tone-card inventory-tone-b" v-if="purchaseActualReconcileConfig && showInventorySection">
      <div class="field">
        <label>納入実績整合チェック（比較のみ） - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="purchaseActualReconcileConfig.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="purchaseActualReconcileConfig.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">夜間は比較のみ実行し、差分があればレポートを保存します。修正は下の「修正実行」ボタンで手動実行します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="purchaseActualReconcileConfig.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>差分通知先</label>
        <div class="notify-search">
          <input
            v-model="purchaseActualReconcileConfig.searchCode"
            :disabled="!canEdit"
            class="notify-search-input"
            placeholder="社員コード/氏名/ユーザー名で検索して追加"
            @keyup.enter.prevent="addFirstCandidate(purchaseActualReconcileConfig)"
          />
        </div>
        <div v-if="candidateList(purchaseActualReconcileConfig).length" class="candidate-list">
          <div
            v-for="u in candidateList(purchaseActualReconcileConfig)"
            :key="u.id"
            class="candidate-item"
            @click="addUser(purchaseActualReconcileConfig, u)"
          >
            <span class="candidate-code">{{ codeLabel(u) }}</span>
            <span class="candidate-name">{{ nameLabel(u) }}</span>
          </div>
        </div>
        <div class="selected-list" v-if="purchaseActualReconcileConfig.notify_user_codes.length">
          <span
            class="chip"
            v-for="code in purchaseActualReconcileConfig.notify_user_codes"
            :key="code"
          >
            <span class="chip-code">{{ code }}</span>
            <span class="chip-name">{{ chipName(purchaseActualReconcileConfig, code) }}</span>
            <button
              type="button"
              class="chip-remove"
              :disabled="!canEdit"
              @click="removeCode(purchaseActualReconcileConfig, code)"
            >
              ×
            </button>
          </span>
        </div>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(purchaseActualReconcileConfig)"
          :disabled="saving.has(configKey(purchaseActualReconcileConfig)) || !canEdit"
        >
          {{ saving.has(configKey(purchaseActualReconcileConfig)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(purchaseActualReconcileConfig)"
          :disabled="isRunNowDisabled(purchaseActualReconcileConfig)"
          style="margin-left: 8px"
        >
          {{ runNowLabel(purchaseActualReconcileConfig) }}
        </button>
        <button
          class="btn"
          @click="loadReconcileReport"
          :disabled="loadingReconcileReport"
          style="margin-left: 8px"
        >
          {{ loadingReconcileReport ? '読込中...' : 'レポート再読込' }}
        </button>
        <button
          class="btn cancel"
          @click="fixPurchaseActualReconcile"
          :disabled="fixingReconcile || !canEdit || isRunningStatus(purchaseActualReconcileConfig)"
          style="margin-left: 8px"
        >
          {{ fixingReconcile ? '修正中...' : '修正実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="purchaseActualReconcileConfig.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(purchaseActualReconcileConfig.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(purchaseActualReconcileConfig)">{{ purchaseActualReconcileConfig.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ purchaseActualReconcileConfig.last_run_duration_seconds != null ? purchaseActualReconcileConfig.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ purchaseActualReconcileConfig.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="last-run" v-if="latestReconcileReport">
        <h3 class="section-title">最新差分レポート</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>レポートID</th>
              <td>{{ latestReconcileReport.id }}</td>
            </tr>
            <tr>
              <th>作成日時</th>
              <td>{{ formatDateTime(latestReconcileReport.created_at) }}</td>
            </tr>
            <tr>
              <th>モード</th>
              <td>{{ latestReconcileReport.mode_display || latestReconcileReport.mode }}</td>
            </tr>
            <tr>
              <th>比較件数</th>
              <td>{{ latestReconcileReport.compared_count }}件</td>
            </tr>
            <tr>
              <th>差分件数</th>
              <td>{{ latestReconcileReport.diff_count }}件</td>
            </tr>
            <tr>
              <th>修正件数</th>
              <td>{{ latestReconcileReport.fixed_count }}件</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ latestReconcileReport.message || '-' }}</td>
            </tr>
          </tbody>
        </table>

        <div class="table-wrapper" style="margin-top: 12px" v-if="reconcileDetails.length">
          <table class="config-table">
            <thead>
              <tr>
                <th>納入日</th>
                <th>ライン</th>
                <th>品番</th>
                <th>期待実績</th>
                <th>Backlog実績</th>
                <th>差分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in reconcileDetails" :key="row.id">
                <td>{{ row.plan_date }}</td>
                <td>{{ row.line_code }} {{ row.line_name }}</td>
                <td>{{ row.product_code }} {{ row.product_name }}</td>
                <td>{{ row.expected_qty }}</td>
                <td>{{ row.backlog_qty }}</td>
                <td>{{ row.diff_qty }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card inventory-tone-card inventory-tone-a" v-if="productionActualReconcileConfig && showInventorySection">
      <div class="field">
        <label>生産実績整合チェック（比較のみ） - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="productionActualReconcileConfig.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="productionActualReconcileConfig.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">夜間は比較のみ実行し、差分があればレポートを保存します。修正は下の「修正実行」ボタンで手動実行します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="productionActualReconcileConfig.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>差分通知先</label>
        <div class="notify-search">
          <input
            v-model="productionActualReconcileConfig.searchCode"
            :disabled="!canEdit"
            class="notify-search-input"
            placeholder="社員コード/氏名/ユーザー名で検索して追加"
            @keyup.enter.prevent="addFirstCandidate(productionActualReconcileConfig)"
          />
        </div>
        <div v-if="candidateList(productionActualReconcileConfig).length" class="candidate-list">
          <div
            v-for="u in candidateList(productionActualReconcileConfig)"
            :key="u.id"
            class="candidate-item"
            @click="addUser(productionActualReconcileConfig, u)"
          >
            <span class="candidate-code">{{ codeLabel(u) }}</span>
            <span class="candidate-name">{{ nameLabel(u) }}</span>
          </div>
        </div>
        <div class="selected-list" v-if="productionActualReconcileConfig.notify_user_codes.length">
          <span
            class="chip"
            v-for="code in productionActualReconcileConfig.notify_user_codes"
            :key="code"
          >
            <span class="chip-code">{{ code }}</span>
            <span class="chip-name">{{ chipName(productionActualReconcileConfig, code) }}</span>
            <button
              type="button"
              class="chip-remove"
              :disabled="!canEdit"
              @click="removeCode(productionActualReconcileConfig, code)"
            >
              ×
            </button>
          </span>
        </div>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(productionActualReconcileConfig)"
          :disabled="saving.has(configKey(productionActualReconcileConfig)) || !canEdit"
        >
          {{ saving.has(configKey(productionActualReconcileConfig)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(productionActualReconcileConfig)"
          :disabled="isRunNowDisabled(productionActualReconcileConfig)"
          style="margin-left: 8px"
        >
          {{ runNowLabel(productionActualReconcileConfig) }}
        </button>
        <button
          class="btn"
          @click="loadProductionReconcileReport"
          :disabled="loadingProductionReconcileReport"
          style="margin-left: 8px"
        >
          {{ loadingProductionReconcileReport ? '読込中...' : 'レポート再読込' }}
        </button>
        <button
          class="btn cancel"
          @click="fixProductionActualReconcile"
          :disabled="fixingProductionReconcile || !canEdit || isRunningStatus(productionActualReconcileConfig)"
          style="margin-left: 8px"
        >
          {{ fixingProductionReconcile ? '修正中...' : '修正実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="productionActualReconcileConfig.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(productionActualReconcileConfig.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(productionActualReconcileConfig)">{{ productionActualReconcileConfig.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ productionActualReconcileConfig.last_run_duration_seconds != null ? productionActualReconcileConfig.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ productionActualReconcileConfig.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="last-run" v-if="latestProductionReconcileReport">
        <h3 class="section-title">最新差分レポート</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>レポートID</th>
              <td>{{ latestProductionReconcileReport.id }}</td>
            </tr>
            <tr>
              <th>作成日時</th>
              <td>{{ formatDateTime(latestProductionReconcileReport.created_at) }}</td>
            </tr>
            <tr>
              <th>モード</th>
              <td>{{ latestProductionReconcileReport.mode_display || latestProductionReconcileReport.mode }}</td>
            </tr>
            <tr>
              <th>比較件数</th>
              <td>{{ latestProductionReconcileReport.compared_count }}件</td>
            </tr>
            <tr>
              <th>差分件数</th>
              <td>{{ latestProductionReconcileReport.diff_count }}件</td>
            </tr>
            <tr>
              <th>修正件数</th>
              <td>{{ latestProductionReconcileReport.fixed_count }}件</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ latestProductionReconcileReport.message || '-' }}</td>
            </tr>
          </tbody>
        </table>

        <div class="table-wrapper" style="margin-top: 12px" v-if="productionReconcileDetails.length">
          <table class="config-table">
            <thead>
              <tr>
                <th>計画日</th>
                <th>ライン</th>
                <th>品番</th>
                <th>期待実績</th>
                <th>Backlog実績</th>
                <th>差分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in productionReconcileDetails" :key="row.id">
                <td>{{ row.plan_date }}</td>
                <td>{{ row.line_code }} {{ row.line_name }}</td>
                <td>{{ row.product_code }} {{ row.product_name }}</td>
                <td>{{ row.expected_qty }}</td>
                <td>{{ row.backlog_qty }}</td>
                <td>{{ row.diff_qty }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <template v-if="showSafetyStockSection">
    <div class="card" v-for="cfg in safetyStockConfigs" :key="configKey(cfg)">
      <div class="field">
        <label>{{ safetyStockTaskLabel(cfg.task_name) }} - 実行日・時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="1"
            max="31"
            v-model.number="cfg.scheduled_dom"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日</span>
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="cfg.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="cfg.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>実行日から何日間の平均日あたりを計算</label>
        <div class="input-row">
          <input
            type="number"
            min="1"
            max="365"
            v-model.number="cfg.average_days_window"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日</span>
        </div>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>上記の日当たりの何日分を安全在庫とする</label>
        <div class="input-row">
          <input
            type="number"
            min="1"
            max="365"
            v-model.number="cfg.safety_days"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日分</span>
        </div>
        <p class="helper">算出式: （実行日からの平均日あたり）×（安全在庫日数）で最小在庫数を更新します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(cfg)"
          :disabled="saving.has(configKey(cfg)) || !canEdit"
        >
          {{ saving.has(configKey(cfg)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(cfg)"
          :disabled="isRunNowDisabled(cfg)"
          style="margin-left: 8px"
        >
          {{ runNowLabel(cfg) }}
        </button>
        <button
          v-if="canCancelTask(cfg) && isRunningStatus(cfg)"
          class="btn cancel"
          @click="cancelRun(cfg)"
          :disabled="cancelling.has(configKey(cfg)) || isCancelRequested(cfg) || !canEdit"
          style="margin-left: 8px"
        >
          {{ isCancelRequested(cfg) ? 'キャンセル要求中...' : (cancelling.has(configKey(cfg)) ? '要求中...' : 'キャンセル要求') }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="cfg.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(cfg.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ cfg.last_run_duration_seconds != null ? cfg.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ cfg.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    </template>

    <div class="card" v-if="orderExpansionConfig && showOrderExpansionSection">
      <div class="field">
        <label>自動受注展開 - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="orderExpansionConfig.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="orderExpansionConfig.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">毎日指定した時刻にOPEN受注をLineDemandへ自動展開します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="orderExpansionConfig.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(orderExpansionConfig)"
          :disabled="saving.has(configKey(orderExpansionConfig)) || !canEdit"
        >
          {{ saving.has(configKey(orderExpansionConfig)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(orderExpansionConfig)"
          :disabled="isRunNowDisabled(orderExpansionConfig)"
          style="margin-left: 8px"
        >
          {{ runNowLabel(orderExpansionConfig) }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="orderExpansionConfig.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(orderExpansionConfig.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(orderExpansionConfig)">{{ orderExpansionConfig.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ orderExpansionConfig.last_run_duration_seconds != null ? orderExpansionConfig.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ orderExpansionConfig.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const route = useRoute()
const dsSources = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()

  if (mode === 'inventory') {
    return [
      { op: '読み書き', table: 'production_schedule_config', desc: '取り込み・在庫・進度・整合チェック・計画実績自動セットの定時設定' },
      { op: '読み取り', table: 'm_line', desc: '計画実績自動セットの対象ライン選択' },
      { op: '読み取り', table: 'm_process', desc: '計画実績自動セットの対象工程選択' },
      { op: '読み書き', table: 'production_purchase_actual_reconcile_report*', desc: '納入実績整合チェックのレポート' },
      { op: '読み書き', table: 'production_production_actual_reconcile_report*', desc: '生産実績整合チェックのレポート' },
    ]
  }

  if (mode === 'safety-stock') {
    return [
      { op: '読み書き', table: 'production_schedule_config', desc: '自動安全在庫タスク設定' },
    ]
  }

  if (mode === 'order-expansion') {
    return [
      { op: '読み書き', table: 'production_schedule_config', desc: '自動受注展開タスク設定' },
    ]
  }

  return [
    { op: '読み書き', table: 'production_schedule_config', desc: '定時タスク共通設定' },
    { op: '読み書き', table: 't_auto_plan_*', desc: '自動計画設定' },
    { op: '読み書き', table: 'production_purchase_actual_reconcile_report*', desc: '納入実績整合チェックのレポート' },
    { op: '読み書き', table: 'production_production_actual_reconcile_report*', desc: '生産実績整合チェックのレポート' },
  ]
})

const configs = ref([])
const saving = reactive(new Set())
const running = reactive(new Set())
const cancelling = reactive(new Set())
const reconcileReports = ref([])
const reconcileDetails = ref([])
const loadingReconcileReport = ref(false)
const fixingReconcile = ref(false)
const productionReconcileReports = ref([])
const productionReconcileDetails = ref([])
const loadingProductionReconcileReport = ref(false)
const fixingProductionReconcile = ref(false)
const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []
  if (permissions.some((item) => item.resource === 'settings.scheduled_tasks')) {
    return hasPermission(user, 'settings.scheduled_tasks', 'edit')
  }
  return hasPermission(user, 'settings', 'edit')
})
const userList = ref([])
const lines = ref([])
const processes = ref([])
const newPlanToActual = ref({
  line_id: '',
  process_id: '',
})
const planToActualDrafts = ref([])

const autoPlanConfigs = computed(() =>
  configs.value
    .filter((cfg) => cfg.task_name === 'AUTO_PLAN')
    .sort((a, b) => (a.line_code || '').localeCompare(b.line_code || ''))
)
const purchaseActualReconcileTaskName = 'PURCHASE_ACTUAL_RECONCILE_CHECK'
const productionActualReconcileTaskName = 'PRODUCTION_ACTUAL_RECONCILE_CHECK'
const inventoryTaskOrder = ['INVENTORY_RECALC', 'PICKUP_ONLY', 'INVENTORY_ONLY', 'PROGRESS_ONLY']
const inventoryTaskConfigs = computed(() =>
  configs.value
    .filter((cfg) => inventoryTaskOrder.includes(cfg.task_name))
    .sort((a, b) => inventoryTaskOrder.indexOf(a.task_name) - inventoryTaskOrder.indexOf(b.task_name))
)
const purchaseActualReconcileConfig = computed(() =>
  configs.value.find((cfg) => cfg.task_name === purchaseActualReconcileTaskName) || null
)
const latestReconcileReport = computed(() => (reconcileReports.value.length ? reconcileReports.value[0] : null))
const productionActualReconcileConfig = computed(() =>
  configs.value.find((cfg) => cfg.task_name === productionActualReconcileTaskName) || null
)
const latestProductionReconcileReport = computed(() => (
  productionReconcileReports.value.length ? productionReconcileReports.value[0] : null
))
const safetyStockTaskOrder = ['AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE']
const safetyStockConfigs = computed(() =>
  configs.value
    .filter((cfg) => safetyStockTaskOrder.includes(cfg.task_name))
    .sort((a, b) => safetyStockTaskOrder.indexOf(a.task_name) - safetyStockTaskOrder.indexOf(b.task_name))
)
const orderExpansionConfig = computed(() => configs.value.find((cfg) => cfg.task_name === 'ORDER_EXPANSION'))
const planToActualConfigs = computed(() => {
  const persisted = configs.value.filter((cfg) => cfg.task_name === 'PLAN_TO_ACTUAL_COPY')
  const merged = [...persisted, ...planToActualDrafts.value]
  return merged.sort((a, b) => {
      const lineA = (a.line_code || '').localeCompare(b.line_code || '')
      if (lineA !== 0) return lineA
      return (a.process_code || '').localeCompare(b.process_code || '')
    })
})
const selectableLines = computed(() =>
  lines.value.filter((line) => line?.is_active)
)
const selectableProcessesForNew = computed(() => {
  if (!newPlanToActual.value.line_id) return []
  return processes.value.filter((p) => String(p.line) === String(newPlanToActual.value.line_id))
})
const showAutoPlanSection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode !== 'inventory' && mode !== 'order-expansion' && mode !== 'safety-stock'
})
const showInventorySection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode === '' || mode === 'inventory'
})
const showSafetyStockSection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode === '' || mode === 'safety-stock'
})
const showOrderExpansionSection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode === '' || mode === 'order-expansion'
})
const autoPlanLocked = computed(() =>
  autoPlanConfigs.value.some((cfg) => cfg.auto_plan_sequence_locked)
)
const canEditAutoPlan = computed(() => canEdit.value && !autoPlanLocked.value)

const statusClass = (cfg) => ({
  'status-success': cfg.last_run_status === 'SUCCESS',
  'status-failed': cfg.last_run_status === 'FAILED',
  'status-running': cfg.last_run_status === 'RUNNING',
})

const inventoryTaskLabel = (taskName) => {
  if (taskName === purchaseActualReconcileTaskName) return '納入実績整合チェック'
  if (taskName === productionActualReconcileTaskName) return '生産実績整合チェック'
  if (taskName === 'PICKUP_ONLY') return '取り込みのみ'
  if (taskName === 'INVENTORY_ONLY') return '在庫計算のみ'
  if (taskName === 'PROGRESS_ONLY') return '進度計算のみ'
  if (taskName === 'PLAN_TO_ACTUAL_COPY') return '計画実績自動セット'
  return '取り込み＋在庫再計算'
}

const inventoryTaskHelp = (taskName) => {
  if (taskName === purchaseActualReconcileTaskName) return 'ProcessRealtimeRecord（納入実績入力）と LineBacklog.actual_qty を比較し、差分レポートを保存します。'
  if (taskName === productionActualReconcileTaskName) return 'ProcessWorkSession/ProcessRealtimeRecord（生産実績）と LineBacklog.actual_qty を比較し、差分レポートを保存します。'
  if (taskName === 'PICKUP_ONLY') return '毎日指定した時刻に需要取り込み（pickup / pickup_purchase）のみを実行します。'
  if (taskName === 'INVENTORY_ONLY') return '毎日指定した時刻に在庫・計画在庫の再計算のみを実行します（必要に応じて過去営業日まで遡って再計算、進度は更新しません）。'
  if (taskName === 'PROGRESS_ONLY') return '毎日指定した時刻に進度のみを再計算します（必要に応じてLT+1営業日前まで遡って再計算します）。'
  if (taskName === 'PLAN_TO_ACTUAL_COPY') return '毎日指定した時刻に、対象ライン・工程の業務日付計画合計を実績へ反映します。既存実績（actual_qty）が0以外の品番は上書きせずスキップします。'
  return '毎日指定した時刻に需要取り込み（pickup）→ 在庫・計画在庫・進度の自動再計算を実行します。'
}
const isSafetyStockTask = (taskName) => safetyStockTaskOrder.includes(taskName)
const safetyStockTaskLabel = (taskName) => {
  if (taskName === 'AUTO_SAFETY_STOCK_PURCHASE') return '自動安全在庫（購入品）'
  return '自動安全在庫（社内）'
}

// INVENTORY_RECALC は _resolve_effective_start_date が LT 基準で開始日を自動決定するため、
// UI での開始日選択は意味を持たない。PICKUP_ONLY のみ開始日選択を表示する。
const showRangeBaseDay = (taskName) => taskName === 'PICKUP_ONLY'
const showInventoryRangeSetting = (taskName) =>
  taskName !== purchaseActualReconcileTaskName
  && taskName !== productionActualReconcileTaskName

const configKey = (cfg) => `${cfg.task_name}-${cfg.line || 'none'}-${cfg.process || 'none'}-${cfg.id || cfg.temp_key || 'new'}`
const isRunningStatus = (cfg) => cfg?.last_run_status === 'RUNNING'
const isCancelRequested = (cfg) => (cfg?.last_run_message || '').includes('[CANCEL_REQUESTED]')
const canCancelTask = (cfg) => inventoryTaskOrder.includes(cfg?.task_name)
const isRunNowDisabled = (cfg) => !cfg || !cfg.id || !canEdit.value || running.has(configKey(cfg)) || isRunningStatus(cfg)
const runNowLabel = (cfg) => (running.has(configKey(cfg)) || isRunningStatus(cfg) ? '実行中...' : '今すぐ実行')
const openManual = () => {
  window.open(`/manual?path=${encodeURIComponent('設定/定時タスク設定.md')}`, '_blank')
}
const cardToneClass = (idx) => (idx % 2 === 0 ? 'inventory-tone-a' : 'inventory-tone-b')

const loadReconcileReport = async () => {
  loadingReconcileReport.value = true
  try {
    const res = await api.scheduleConfig.getPurchaseActualReconcileReports({
      limit: 10,
      detail_limit: 200,
    })
    reconcileReports.value = Array.isArray(res.data?.reports) ? res.data.reports : []
    reconcileDetails.value = Array.isArray(res.data?.details) ? res.data.details : []
  } catch (e) {
    console.error('整合レポートの取得に失敗', e)
    reconcileReports.value = []
    reconcileDetails.value = []
  } finally {
    loadingReconcileReport.value = false
  }
}

const loadProductionReconcileReport = async () => {
  loadingProductionReconcileReport.value = true
  try {
    const res = await api.scheduleConfig.getProductionActualReconcileReports({
      limit: 10,
      detail_limit: 200,
    })
    productionReconcileReports.value = Array.isArray(res.data?.reports) ? res.data.reports : []
    productionReconcileDetails.value = Array.isArray(res.data?.details) ? res.data.details : []
  } catch (e) {
    console.error('生産整合レポートの取得に失敗', e)
    productionReconcileReports.value = []
    productionReconcileDetails.value = []
  } finally {
    loadingProductionReconcileReport.value = false
  }
}

const loadConfig = async () => {
  try {
    const res = await api.scheduleConfig.getConfigs()
    const data = Array.isArray(res.data) ? res.data : [res.data]
    configs.value = data.map((cfg) => ({
      ...cfg,
      average_days_window: Number.isFinite(Number(cfg.average_days_window)) ? Number(cfg.average_days_window) : 60,
      safety_days: Number.isFinite(Number(cfg.safety_days)) ? Number(cfg.safety_days) : 1,
      notify_users: cfg.notify_users || [],
      notify_user_codes: cfg.notify_user_codes || [],
      notify_user_names: cfg.notify_user_names || {},
      searchCode: '',
    }))
  } catch (e) {
    console.error('スケジュール設定の取得に失敗', e)
  }
}

const loadUsers = async () => {
  try {
    const res = await api.accounts.getUsers({ is_active: true })
    userList.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('ユーザー一覧の取得に失敗', e)
  }
}

const loadLineProcessMasters = async () => {
  try {
    const [lineRes, processRes] = await Promise.all([
      api.lines.getLines({ is_active: true }),
      api.processes.getProcesses({ is_active: true }),
    ])
    lines.value = lineRes.data?.results || lineRes.data || []
    processes.value = processRes.data?.results || processRes.data || []
  } catch (e) {
    console.error('ライン/工程マスタの取得に失敗', e)
    lines.value = []
    processes.value = []
  }
}

const saveConfig = async (cfg) => {
  if (!canEdit.value) return
  if (cfg.task_name === 'AUTO_PLAN' && autoPlanLocked.value) {
    alert('順序運用モード中のため、この画面では自動計画設定を編集できません。')
    return
  }
  const key = configKey(cfg)
  saving.add(key)
  try {
    await api.scheduleConfig.saveConfig({
      id: cfg.id,
      task_name: cfg.task_name,
      line: cfg.line,
      process: cfg.process,
      scheduled_hour: cfg.scheduled_hour,
      scheduled_minute: cfg.scheduled_minute,
      scheduled_dom: cfg.scheduled_dom,
      range_start_date: null,
      range_end_date: null,
      range_base_day: showRangeBaseDay(cfg.task_name) ? (cfg.range_base_day || 'TODAY') : 'TODAY',
      range_days_after: Number.isFinite(Number(cfg.range_days_after)) ? Number(cfg.range_days_after) : 45,
      average_days_window: Number.isFinite(Number(cfg.average_days_window)) ? Number(cfg.average_days_window) : 60,
      safety_days: Number.isFinite(Number(cfg.safety_days)) ? Number(cfg.safety_days) : 1,
      is_enabled: cfg.is_enabled,
      include_current_month: cfg.include_current_month,
      include_next_month: cfg.include_next_month,
      include_second_month: cfg.include_second_month,
      include_third_month: cfg.include_third_month,
      notify_user_codes: cfg.notify_user_codes,
    })
    if (cfg.is_draft && cfg.temp_key) {
      planToActualDrafts.value = planToActualDrafts.value.filter((row) => row.temp_key !== cfg.temp_key)
    }
    alert('保存しました。設定は5分以内にスケジューラに反映されます。')
    await loadConfig()
  } catch (e) {
    alert('保存に失敗しました。')
  } finally {
    saving.delete(key)
  }
}

const addPlanToActualConfig = () => {
  if (!newPlanToActual.value.line_id || !newPlanToActual.value.process_id) {
    alert('ラインと工程を選択してください。')
    return
  }
  const line = lines.value.find((v) => String(v.id) === String(newPlanToActual.value.line_id))
  const process = processes.value.find((v) => String(v.id) === String(newPlanToActual.value.process_id))
  if (!line || !process) {
    alert('選択内容が不正です。')
    return
  }
  const exists = [...configs.value, ...planToActualDrafts.value].some((cfg) =>
    cfg.task_name === 'PLAN_TO_ACTUAL_COPY'
    && String(cfg.line) === String(line.id)
    && String(cfg.process) === String(process.id)
  )
  if (exists) {
    alert('同じライン・工程の設定は既に存在します。')
    return
  }
  planToActualDrafts.value.push({
    temp_key: `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    is_draft: true,
    task_name: 'PLAN_TO_ACTUAL_COPY',
    line: line.id,
    line_code: line.line_code,
    line_name: line.line_name,
    process: process.id,
    process_code: process.process_code,
    process_name: process.process_name,
    scheduled_hour: 7,
    scheduled_minute: 50,
    is_enabled: true,
    range_base_day: 'TODAY',
    range_days_after: 45,
    average_days_window: 60,
    safety_days: 1,
    include_current_month: false,
    include_next_month: false,
    include_second_month: false,
    include_third_month: false,
    notify_users: [],
    notify_user_codes: [],
    notify_user_names: {},
    searchCode: '',
    last_run_at: null,
    last_run_status: null,
    last_run_status_display: '',
    last_run_message: '',
    last_run_duration_seconds: null,
  })
  newPlanToActual.value = { line_id: '', process_id: '' }
}

const removePlanToActualDraft = (cfg) => {
  if (!cfg?.is_draft) return
  const key = cfg.temp_key
  planToActualDrafts.value = planToActualDrafts.value.filter((row) => row.temp_key !== key)
}

const pollTimer = ref(null)

const stopPolling = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

const runNow = async (cfg) => {
  if (!canEdit.value) return
  if (isRunningStatus(cfg)) {
    alert('既に実行中です。必要なら「キャンセル要求」を実行してください。')
    return
  }
  const key = configKey(cfg)
  const targetName =
    cfg.task_name === 'AUTO_PLAN'
      ? `生産計画自動生成（${cfg.line_name || cfg.line_code || 'ライン未設定'}）`
      : cfg.task_name === 'ORDER_EXPANSION'
        ? '自動受注展開'
        : isSafetyStockTask(cfg.task_name)
          ? safetyStockTaskLabel(cfg.task_name)
        : inventoryTaskLabel(cfg.task_name)
  const msg =
    cfg.task_name === 'AUTO_PLAN'
      ? `${targetName}を今すぐ実行しますか？`
      : cfg.task_name === 'ORDER_EXPANSION'
        ? '自動受注展開を今すぐ実行しますか？'
        : cfg.task_name === purchaseActualReconcileTaskName
          ? '納入実績整合チェック（比較のみ）を今すぐ実行しますか？\n差分があればレポートへ保存され、通知設定がある場合は通知します。'
        : cfg.task_name === productionActualReconcileTaskName
          ? '生産実績整合チェック（比較のみ）を今すぐ実行しますか？\n差分があればレポートへ保存され、通知設定がある場合は通知します。'
        : isSafetyStockTask(cfg.task_name)
          ? `${safetyStockTaskLabel(cfg.task_name)}を今すぐ実行しますか？\nバックグラウンドで実行されます。`
        : `${inventoryTaskLabel(cfg.task_name)}を今すぐ実行しますか？\nバックグラウンドで実行されます。`
  if (!confirm(msg)) return

  running.add(key)
  try {
    const res = await api.scheduleConfig.runNow({ task_name: cfg.task_name, config_id: cfg.id, line: cfg.line })
    // 非同期実行の場合はポーリングで完了を待つ
    if (res.data?.async) {
      await loadConfig()
      if (cfg.task_name === purchaseActualReconcileTaskName) {
        await loadReconcileReport()
      } else if (cfg.task_name === productionActualReconcileTaskName) {
        await loadProductionReconcileReport()
      }
      stopPolling()
      const pollStart = Date.now()
      const POLL_TIMEOUT = 10 * 60 * 1000 // 10分
      pollTimer.value = setInterval(async () => {
        // タイムアウト: 10分でポーリング停止
        if (Date.now() - pollStart > POLL_TIMEOUT) {
          stopPolling()
          running.delete(key)
          alert('10分経過しても完了しませんでした。\n継続実行中の可能性があります。必要なら「キャンセル要求」を実行してください。')
          return
        }
        await loadConfig()
        const updated = configs.value.find((c) => c.task_name === cfg.task_name && c.line === cfg.line)
        if (updated && updated.last_run_status !== 'RUNNING') {
          stopPolling()
          running.delete(key)
          const statusLabel = updated.last_run_status === 'SUCCESS' ? '成功' : '失敗'
          alert(`${targetName}が完了しました（${statusLabel}）\n${updated.last_run_message || ''}`)
          if (cfg.task_name === purchaseActualReconcileTaskName) {
            await loadReconcileReport()
          } else if (cfg.task_name === productionActualReconcileTaskName) {
            await loadProductionReconcileReport()
          }
        }
      }, 5000)
    } else {
      alert(`完了しました。\n${res.data?.detail || ''}`)
      await loadConfig()
      if (cfg.task_name === purchaseActualReconcileTaskName) {
        await loadReconcileReport()
      } else if (cfg.task_name === productionActualReconcileTaskName) {
        await loadProductionReconcileReport()
      }
      running.delete(key)
    }
  } catch (e) {
    running.delete(key)
    if (e.response?.status === 409) {
      alert(e.response.data?.detail || '既に実行中です。')
    } else {
      alert('実行に失敗しました。')
    }
  }
}

const fixPurchaseActualReconcile = async () => {
  const cfg = purchaseActualReconcileConfig.value
  if (!cfg || !canEdit.value) return
  if (isRunningStatus(cfg)) {
    alert('整合チェックが実行中です。完了後に再実行してください。')
    return
  }
  if (!confirm('最新状態で差分を手動修正しますか？\nLineBacklog.actual_qty を ProcessRealtimeRecord に合わせます。')) return

  fixingReconcile.value = true
  try {
    const res = await api.scheduleConfig.runPurchaseActualReconcileFix()
    alert(`修正を実行しました。\n${res.data?.message || ''}`)
    await loadConfig()
    await loadReconcileReport()
  } catch (e) {
    const detail = e.response?.data?.detail
    alert(detail || '修正実行に失敗しました。')
  } finally {
    fixingReconcile.value = false
  }
}

const fixProductionActualReconcile = async () => {
  const cfg = productionActualReconcileConfig.value
  if (!cfg || !canEdit.value) return
  if (isRunningStatus(cfg)) {
    alert('整合チェックが実行中です。完了後に再実行してください。')
    return
  }
  if (!confirm('最新状態で差分を手動修正しますか？\nLineBacklog.actual_qty を生産実績側に合わせます。')) return

  fixingProductionReconcile.value = true
  try {
    const res = await api.scheduleConfig.runProductionActualReconcileFix()
    alert(`修正を実行しました。\n${res.data?.message || ''}`)
    await loadConfig()
    await loadProductionReconcileReport()
  } catch (e) {
    const detail = e.response?.data?.detail
    alert(detail || '修正実行に失敗しました。')
  } finally {
    fixingProductionReconcile.value = false
  }
}

const cancelRun = async (cfg) => {
  if (!canEdit.value || !canCancelTask(cfg) || !isRunningStatus(cfg)) return
  const key = configKey(cfg)
  const targetName = inventoryTaskLabel(cfg.task_name)
  if (!confirm(`${targetName}のキャンセル要求を送信しますか？`)) return

  cancelling.add(key)
  try {
    const res = await api.scheduleConfig.cancel({
      task_name: cfg.task_name,
      config_id: cfg.id,
      line: cfg.line,
    })
    alert(res.data?.detail || 'キャンセル要求を受け付けました。')
    await loadConfig()
  } catch (e) {
    const detail = e.response?.data?.detail
    alert(detail || 'キャンセル要求に失敗しました。')
  } finally {
    cancelling.delete(key)
  }
}

const formatDateTime = (dt) => {
  if (!dt) return '-'
  const d = new Date(dt)
  return d.toLocaleString('ja-JP')
}

const codeLabel = (u) => u?.profile?.employee_code || u.username || u.email || `ID:${u.id}`

const nameLabel = (u) => {
  const name = `${u.last_name || ''}${u.first_name || ''}`.trim()
  return name || u.username || u.email || `ID:${u.id}`
}

const candidateList = (cfg) => {
  const kw = (cfg.searchCode || '').trim().toLowerCase()
  if (!kw) return []
  return userList.value
    .filter((u) => {
      const code = codeLabel(u).toLowerCase()
      const name = nameLabel(u).toLowerCase()
      return code.includes(kw) || name.includes(kw)
    })
    .slice(0, 10)
}

const chipName = (cfg, code) => {
  if (cfg.notify_user_names && cfg.notify_user_names[code]) return cfg.notify_user_names[code]
  const user = userList.value.find((u) => codeLabel(u) === code)
  return user ? nameLabel(user) : ''
}

const addUser = (cfg, user) => {
  const code = codeLabel(user)
  if (!cfg.notify_user_codes.includes(code)) {
    cfg.notify_user_codes = [...cfg.notify_user_codes, code]
    cfg.notify_user_names = {
      ...(cfg.notify_user_names || {}),
      [code]: nameLabel(user),
    }
  }
  cfg.searchCode = ''
}

const addFirstCandidate = (cfg) => {
  const first = candidateList(cfg)[0]
  if (first) addUser(cfg, first)
}

const removeCode = (cfg, code) => {
  cfg.notify_user_codes = cfg.notify_user_codes.filter((c) => c !== code)
  if (cfg.notify_user_names) {
    const names = { ...cfg.notify_user_names }
    delete names[code]
    cfg.notify_user_names = names
  }
}

const startPollingIfRunning = () => {
  const pollTargets = [...inventoryTaskConfigs.value, ...safetyStockConfigs.value]
  if (purchaseActualReconcileConfig.value) {
    pollTargets.push(purchaseActualReconcileConfig.value)
  }
  if (productionActualReconcileConfig.value) {
    pollTargets.push(productionActualReconcileConfig.value)
  }
  const runningTask = pollTargets.find((cfg) => cfg.last_run_status === 'RUNNING')
  if (!runningTask) return
  const key = configKey(runningTask)
  running.add(key)
  stopPolling()
  const pollStart = Date.now()
  const POLL_TIMEOUT = 10 * 60 * 1000
  pollTimer.value = setInterval(async () => {
    if (Date.now() - pollStart > POLL_TIMEOUT) {
      stopPolling()
      running.delete(key)
      return
    }
    await loadConfig()
    const currentTargets = [...inventoryTaskConfigs.value, ...safetyStockConfigs.value]
    if (purchaseActualReconcileConfig.value) {
      currentTargets.push(purchaseActualReconcileConfig.value)
    }
    if (productionActualReconcileConfig.value) {
      currentTargets.push(productionActualReconcileConfig.value)
    }
    const updated = currentTargets.find((cfg) => configKey(cfg) === key)
    if (updated && updated.last_run_status !== 'RUNNING') {
      stopPolling()
      running.delete(key)
      if (updated.task_name === purchaseActualReconcileTaskName) {
        await loadReconcileReport()
      } else if (updated.task_name === productionActualReconcileTaskName) {
        await loadProductionReconcileReport()
      }
    }
  }, 5000)
}

onMounted(async () => {
  await loadConfig()
  await loadLineProcessMasters()
  await loadReconcileReport()
  await loadProductionReconcileReport()
  loadUsers()
  startPollingIfRunning()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
  max-width: 100%;
  margin-bottom: 12px;
}
.inventory-tone-card.inventory-tone-a {
  background: #f7fbff;
  border-color: #b9d7f4;
  border-left: 6px solid #5b9bd5;
}
.inventory-tone-card.inventory-tone-b {
  background: #f9fff7;
  border-color: #c5e5be;
  border-left: 6px solid #70ad47;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.card-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 4px;
}
.table-wrapper {
  overflow-x: auto;
}
.config-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.config-table th {
  text-align: left;
  padding: 6px 6px;
  color: #444;
  border-bottom: 1px solid #e5e9ef;
  white-space: nowrap;
}
.config-table td {
  padding: 8px 6px;
  border-bottom: 1px solid #e5e9ef;
  vertical-align: top;
}
.line-name {
  font-weight: 700;
  color: #1f2a44;
}
.line-code {
  font-size: 11px;
  color: #6b7280;
}
.time-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.time-row:last-child {
  margin-bottom: 0;
}
.time-input {
  width: 60px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.date-input {
  width: 160px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.suffix {
  font-size: 12px;
  color: #333;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 12px;
}
.period-cell .checkbox-label {
  margin-bottom: 4px;
}
.period-cell .checkbox-label:last-child {
  margin-bottom: 0;
}
.actions-cell {
  display: flex;
  gap: 8px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.btn.cancel {
  background: #fff7ed;
  color: #b45309;
  border-color: #fdba74;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.notify-select {
  width: 100%;
  min-height: 60px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.notify-cell {
  min-width: 200px;
}
.notify-search-input {
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.candidate-list {
  border: 1px solid #e5e9ef;
  border-radius: 4px;
  margin-top: 6px;
  max-height: 160px;
  overflow: auto;
  background: #fff;
}
.candidate-item {
  padding: 6px 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  cursor: pointer;
}
.candidate-item:hover {
  background: #f3f6fb;
}
.candidate-code {
  font-weight: 700;
  color: #1f2a44;
  min-width: 80px;
}
.candidate-name {
  color: #444;
  font-size: 12px;
}
.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.chip {
  background: #eef2f6;
  border: 1px solid #cfd6e1;
  border-radius: 14px;
  padding: 4px 8px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.chip-code {
  font-weight: 700;
}
.chip-name {
  color: #4b5563;
}
.chip-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
  color: #6b7280;
}
.chip-remove:disabled {
  cursor: not-allowed;
  color: #9ca3af;
}
.notify-input {
  width: 100%;
  min-height: 60px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  padding: 6px 8px;
  resize: vertical;
}
.last-cell {
  font-size: 12px;
  color: #374151;
}
.last-row {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
  align-items: center;
}
.last-label {
  color: #6b7280;
  min-width: 32px;
}
.message-cell {
  white-space: pre-wrap;
  word-break: break-all;
  color: #111827;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field label {
  font-size: 12px;
  color: #444;
}
.card > .field:first-child > label {
  font-size: 16px;
  font-weight: 700;
  color: #1d4ed8;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.helper {
  margin: 0;
  font-size: 12px;
  color: #dc2626;
}
.helper.warning {
  color: #b45309;
  margin-top: 8px;
}
.actions {
  margin-top: 12px;
}
.last-run {
  margin-top: 16px;
  border-top: 1px solid #e5e9ef;
  padding-top: 12px;
}
.section-title {
  font-size: 13px;
  margin: 0 0 6px;
  font-weight: 600;
}
.info-table {
  font-size: 12px;
  border-collapse: collapse;
  width: 100%;
}
.info-table th {
  text-align: left;
  padding: 4px 8px 4px 0;
  color: #666;
  white-space: nowrap;
  width: 80px;
  vertical-align: top;
}
.info-table td {
  padding: 4px 0;
}
.status-success {
  color: #16a34a;
  font-weight: 600;
}
.status-failed {
  color: #dc2626;
  font-weight: 600;
}
.status-running {
  color: #2563eb;
  font-weight: 600;
}
</style>
