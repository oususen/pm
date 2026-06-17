<template>
  <div class="page-container ics-operation" v-if="canView">
    <!-- ページヘッダー -->
    <div v-show="!activeBatch" class="page-header">
      <h2 class="page-title">{{ pageTitleText }}
        <span v-if="!isReviewMode && !isTestMode" class="page-title-note">{{ t('integratedOperation.pageNote') }}</span>
      </h2>
      <div class="page-actions">
        <button
          v-if="isTestMode"
          class="btn-secondary"
          @click="backToTemplateFromTest"
        >テンプレートへ戻る</button>
        <button
          v-if="showBackToProcessInput"
          class="btn-secondary"
          @click="backToProcessInput"
        >{{ t('integratedOperation.btn.backToProcessInput') }}</button>
        <button
          v-if="isReviewMode"
          class="btn-secondary"
          @click="openNewBatchSection"
        >{{ t('integratedOperation.btn.newBatch') }}</button>
        <button v-if="!isTestMode" class="btn-secondary" @click="refreshAll" :disabled="loading">{{ t('common.update') }}</button>
      </div>
    </div>

    <section v-if="isTestMode && !activeBatch" class="panel test-panel">
      <div class="panel-title-row">
        <h3 class="panel-title">テスト実施</h3>
      </div>
      <div v-if="loadingTestTemplate" class="no-data">テンプレート読込中...</div>
      <div v-else-if="testTemplate" class="prepare-form">
        <label>
          <span class="field-label">ライン</span>
          <input :value="testTemplate.line_code || '-'" type="text" disabled style="width:140px" />
        </label>
        <label>
          <span class="field-label">製品</span>
          <input :value="testTemplate.product_code || '-'" type="text" disabled style="width:180px" />
        </label>
        <label>
          <span class="field-label">テンプレート</span>
          <input :value="`${testTemplate.name || '-'} (v${testTemplate.version || 1})`" type="text" disabled style="width:260px" />
        </label>
        <label>
          <span class="field-label">台数</span>
          <input v-model.number="testBatch.quantity" type="number" min="1" style="width:80px" />
        </label>
        <label>
          <span class="field-label">対象日</span>
          <input v-model="testBatch.plan_date" type="date" style="width:140px" />
        </label>
        <button class="btn-primary" @click="startTestBatch" :disabled="!canEdit || !testBatch.quantity || !testBatch.plan_date">テスト開始</button>
      </div>
      <p v-if="testTemplate" class="test-note">テスト実施の入力内容はDB保存されません。画面を閉じると破棄されます。</p>
      <div v-else-if="!loadingTestTemplate" class="no-data">テスト対象テンプレートを読めませんでした。</div>
    </section>

    <!-- フィルタパネル -->
    <section v-show="!activeBatch && !isTestMode" class="panel filter-panel">
      <div class="prepare-form filter-form">
        <label>
          <span class="field-label">{{ t('integratedOperation.line') }}</span>
          <select v-model="selectedLine" :disabled="loading || isLineLockedFromRoute">
            <option value="">{{ t('integratedOperation.allLines') }}</option>
            <option v-for="l in lineOptions" :key="l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">{{ t('integratedOperation.product') }}</span>
          <select v-model="selectedProduct" :disabled="loading">
            <option value="">{{ t('integratedOperation.allProducts') }}</option>
            <option v-for="p in filteredProductOptions" :key="p.id" :value="p.id">{{ p.product_code }} - {{ p.product_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">{{ t('integratedOperation.statusLabel') }}</span>
          <select v-model="batchStatusFilter">
            <option value="">{{ t('integratedOperation.all') }}</option>
            <option value="OPEN">{{ t('integratedOperation.status.open') }}</option>
            <option value="COMPLETED">{{ t('integratedOperation.status.completed') }}</option>
            <option value="LEADER_CONFIRMED">{{ t('integratedOperation.status.leaderConfirmed') }}</option>
            <option value="SUPERVISOR_CONFIRMED">{{ t('integratedOperation.status.supervisorConfirmed') }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">刻印番号</span>
          <input v-model="seiBanFilter" type="text" placeholder="部分一致検索" style="width:160px" :disabled="loading" @keydown.enter="doSearch()" />
        </label>
        <button class="btn-secondary btn-sm" @click="doSearch()" :disabled="loading" style="align-self:flex-end">検索</button>
        <button class="btn-secondary btn-sm" @click="resetFilters()" :disabled="loading" style="align-self:flex-end">リセット</button>
      </div>
    </section>

    <!-- 新規バッチ作成 -->
    <section v-if="isReviewMode && !activeBatch && !isTestMode" class="panel" ref="newBatchSectionRef">
      <div class="panel-title-row">
        <h3 class="panel-title">{{ t('integratedOperation.newBatchTitle') }}</h3>
        <button class="btn-secondary btn-sm" @click="showNewBatchSection = !showNewBatchSection">
          {{ showNewBatchSection ? t('integratedOperation.btn.hide') : t('integratedOperation.btn.show') }}
        </button>
      </div>
      <div v-if="showNewBatchSection" class="prepare-form">
        <label>
          <span class="field-label">{{ t('integratedOperation.col.line') }} <span class="required-mark">*</span></span>
          <select v-model="newBatch.line">
            <option value="">{{ t('integratedOperation.field.select') }}</option>
            <option v-for="l in lineOptions" :key="'nb-'+l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">{{ t('integratedOperation.col.product') }} <span class="required-mark">*</span></span>
          <select v-model="newBatch.product">
            <option value="">{{ t('integratedOperation.field.select') }}</option>
            <option v-for="p in newBatchProductOptions" :key="'nb-'+p.id" :value="p.id">{{ p.product_code }} - {{ p.product_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">{{ t('integratedOperation.col.quantity') }} <span class="required-mark">*</span></span>
          <input type="number" v-model.number="newBatch.quantity" min="1" style="width:80px" />
        </label>
        <label>
          <span class="field-label">{{ t('integratedOperation.col.planDate') }} <span class="required-mark">*</span></span>
          <input type="date" v-model="newBatch.plan_date" style="width:140px" />
        </label>
        <label>
          <span class="field-label">{{ t('integratedOperation.col.lotNo') }}</span>
          <input type="text" v-model.trim="newBatch.lot_no" :placeholder="t('integratedOperation.field.optional')" style="width:120px" />
        </label>
        <button class="btn-primary" @click="prepareBatch" :disabled="preparing || !newBatch.product || !newBatch.line || !newBatch.quantity || !newBatch.plan_date || !canEdit">
          {{ preparing ? t('integratedOperation.btn.creating') : t('integratedOperation.btn.createBatch') }}
        </button>
      </div>
    </section>

    <!-- バッチ一覧 -->
    <section v-show="!activeBatch && !isTestMode" class="panel">
      <h3 class="panel-title">{{ t('integratedOperation.batchList') }}</h3>
      <div v-if="loadingBatches" class="no-data">{{ t('integratedOperation.loading') }}</div>
      <div v-else-if="!batches.length" class="no-data">{{ t('integratedOperation.noBatches') }}</div>
      <div v-else class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>{{ t('integratedOperation.col.id') }}</th>
              <th>{{ t('integratedOperation.col.planDate') }}</th>
              <th>{{ t('integratedOperation.col.line') }}</th>
              <th>{{ t('integratedOperation.col.product') }}</th>
              <th>{{ t('integratedOperation.col.templateName') }}</th>
              <th>{{ t('integratedOperation.col.lotNo') }}</th>
              <th>{{ t('integratedOperation.col.quantity') }}</th>
              <th>{{ t('integratedOperation.col.progress') }}</th>
              <th>{{ t('integratedOperation.col.processProgress') }}</th>
              <th>{{ t('integratedOperation.col.status') }}</th>
              <th>{{ t('integratedOperation.col.createdAt') }}</th>
              <th>{{ t('integratedOperation.col.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in batches" :key="b.id" :class="{ 'row-selected': activeBatchId === b.id }">
              <td>{{ b.id }}</td>
              <td>{{ b.plan_date || '-' }}</td>
              <td>{{ b.line_code || '-' }}</td>
              <td>{{ b.product_code || '-' }}</td>
              <td>{{ b.template_name || '-' }}</td>
              <td>{{ b.lot_no || '-' }}</td>
              <td>{{ b.quantity }}</td>
              <td>{{ b.completed_count ?? 0 }} / {{ b.quantity }}</td>
              <td>
                <div class="process-progress-list">
                  <span
                    v-for="chip in processProgressChips(b.process_progress)"
                    :key="chip.key"
                    class="process-progress-chip"
                    :class="{ done: chip.done }"
                  >
                    {{ chip.label }}
                  </span>
                </div>
              </td>
              <td>
                <span class="status-chip" :class="statusClass(b.status)">{{ statusLabel(b.status) }}</span>
              </td>
              <td>{{ formatDateTime(b.created_at) }}</td>
              <td class="action-cell">
                <button class="btn-primary btn-sm" @click="openBatchDetail(b)">{{ t('integratedOperation.detail') }}</button>
                <button
                  v-if="isReviewMode && canLeaderConfirm(b)"
                  class="btn-secondary btn-sm"
                  :disabled="actionLoading"
                  @click="leaderConfirm(b)"
                >{{ t('integratedOperation.btn.leaderConfirm') }}</button>
                <button
                  v-if="isReviewMode && canEditBatch(b)"
                  class="btn-secondary btn-sm"
                  :disabled="actionLoading"
                  @click="openEditBatchDialog(b)"
                >{{ t('integratedOperation.btn.edit') }}</button>
                <button
                  v-if="isReviewMode && canDeleteBatch(b)"
                  class="btn-sm btn-delete-batch"
                  :disabled="actionLoading"
                  @click="deleteBatch(b)"
                >{{ t('integratedOperation.btn.delete') }}</button>
                <button
                  v-if="isReviewMode && canShowSupervisorConfirm(b)"
                  class="btn-secondary btn-sm"
                  :disabled="actionLoading || !isSupervisorUser"
                  @click="supervisorConfirm(b)"
                >{{ t('integratedOperation.btn.supervisorConfirm') }}</button>
                <span v-if="b.status === 'SUPERVISOR_CONFIRMED'" class="status-chip ok">{{ t('integratedOperation.btn.confirmed') }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 刻印番号 履歴照会 -->
    <section v-if="isReviewMode && !activeBatch && !isTestMode && historyResults.length" class="panel">
      <h3 class="panel-title">刻印番号 履歴照会</h3>
      <div v-for="item in historyResults" :key="item.unit_id" class="history-unit-card">
        <div class="history-unit-header">
          <span class="history-sei-ban">{{ item.sei_ban }}</span>
          <span class="history-meta">{{ item.product_code }} {{ item.product_name }} | {{ item.line_code }} | 計画日: {{ item.plan_date || '-' }} | ロット: {{ item.lot_no || '-' }} | 台目#{{ item.sequence_no }}</span>
        </div>
        <table class="data-table compact history-table">
          <thead>
            <tr>
              <th style="width:100px">工程</th>
              <th>チェック項目</th>
              <th style="width:60px">種別</th>
              <th style="width:70px">判定</th>
              <th style="width:100px">値</th>
              <th style="width:90px">実施者</th>
              <th style="width:80px">実施日</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="proc in item.processes" :key="proc.block_id">
              <tr class="history-process-header">
                <td :colspan="7">
                  <strong>{{ proc.process_code }} {{ proc.process_name }}</strong>
                  <span v-if="proc.hold && proc.hold.status === 'held'" class="history-hold-badge held">保留中: {{ proc.hold.reason }}</span>
                  <span v-if="proc.hold && proc.hold.status === 'released'" class="history-hold-badge released">保留解除済 (理由: {{ proc.hold.hold_reason }} → 解除: {{ proc.hold.release_reason }}, {{ proc.hold.released_by }}, {{ formatHistoryDate(proc.hold.released_at) }})</span>
                </td>
              </tr>
              <tr v-if="!proc.checks.length">
                <td :colspan="7" class="no-data" style="padding:2px 8px;font-size:11px">チェック記録なし</td>
              </tr>
              <tr v-for="(chk, ci) in proc.checks" :key="proc.block_id + '-' + ci">
                <td>{{ proc.process_code }}</td>
                <td>{{ chk.item_name }}</td>
                <td>{{ historyRecordTypeLabel(chk.record_type) }}</td>
                <td :class="historyJudgementClass(chk.judgement)">{{ chk.judgement || '-' }}</td>
                <td>{{ chk.numeric_value || chk.text_value || '-' }}</td>
                <td>{{ chk.checked_by || '-' }}</td>
                <td>{{ formatHistoryDate(chk.checked_at) }}</td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>

    <!-- バッチ詳細（マトリクス） -->
    <section v-if="activeBatch" class="panel matrix-panel">
      <div class="matrix-header">
        <h3 class="panel-title">
          {{ activeBatch.product_code }} {{ activeBatch.product_name }}
          <span class="batch-meta">| {{ activeBatch.template_name || '-' }} | ロット: {{ activeBatch.lot_no || '-' }} | 最終工程計画日: {{ activeBatch.plan_date || '-' }}</span>
          <span v-if="isReviewMode && reviewRoleLabel" class="batch-meta">| 確認: {{ reviewRoleLabel }}</span>
        </h3>
        <div class="matrix-header-actions">
          <button v-if="showBackToProcessInput" class="btn-secondary btn-sm" @click="backToProcessInput">工程作業入力へ戻る</button>
          <button class="btn-secondary btn-sm" @click="closeBatchDetail">{{ t('integratedOperation.backToList') }}</button>
        </div>
      </div>

      <div v-if="loadingUnits" class="no-data">{{ t('integratedOperation.loading') }}</div>
      <div v-else-if="!units.length" class="no-data">{{ t('integratedOperation.noUnits') }}</div>
      <div v-else class="matrix-scroll">
        <table class="data-table matrix-table">
          <thead>
            <tr>
              <th class="th-no">№</th>
              <th class="th-process">工程</th>
              <th class="th-item">チェック項目</th>
              <th class="th-type">種別</th>
              <th
                v-for="u in units"
                :key="'h-'+u.id"
                class="th-unit"
                :class="{ clickable: true }"
                  @click="canEdit ? openUnitModal(u) : null"
              >
                <div class="unit-header">
                  <span>{{ u.sequence_no }}</span>
                  <span class="status-chip mini" :class="statusClass(u.status)">{{ statusShort(u.status) }}</span>
                  <span v-if="shouldShowHoldMark(u)" class="unit-hold-mark">保留</span>
                  <span v-if="u.sei_ban" class="unit-sei-ban">{{ u.sei_ban }}</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="block in matrixVisibleBlocks" :key="'blk-'+block.id">
              <!-- 工程ヘッダー行 -->
              <tr class="block-header-row">
                <td :colspan="4" class="block-header-cell">
                  <div class="block-header-inner">
                    <span class="block-title-left">
                      {{ block.process_code }} {{ block.process_name }}
                      <span v-if="block.sketch_image_url" class="sketch-badge">略図あり</span>
                    </span>
                    <span class="block-title-right">確認者</span>
                  </div>
                </td>
              <td
                v-for="u in units"
                :key="'bh-'+block.id+'-'+u.id"
                class="block-checker-cell"
                :class="{ 'cell-disabled-by-process': isBlockedByPreferredProcess(block), 'block-held': isBlockHeld(u, block.id) }"
                @click="canEdit && !isBlockedByPreferredProcess(block) ? openUnitModal(u, block.id) : null"
              >
                <span v-if="isBlockHeld(u, block.id)" class="block-hold-mark" :title="getBlockHoldReason(u, block.id)">保留</span>
                {{ getBlockCheckerName(u, block.id) || '-' }}
                <span v-if="getBlockCheckedDate(u, block.id)" class="checker-date">{{ getBlockCheckedDate(u, block.id) }}</span>
              </td>
              </tr>
              <!-- 各チェック項目行 -->
              <tr v-for="(item, itemIdx) in block.items" :key="'item-'+item.id">
                <td class="td-no">{{ itemIdx + 1 }}</td>
                <td class="td-process">{{ block.process_code }}</td>
                <td class="td-item">
                  {{ item.item_name }}
                  <span v-if="item.standard" class="item-standard">{{ item.standard }}</span>
                  <button v-if="item.attachments?.length" class="btn-attachment-ref btn-attachment-sm" @click.stop="openAttachmentViewer(item)">付表({{ item.attachments.length }})</button>
                </td>
                <td class="td-type">
                  <span class="type-tag" :class="'type-' + item.record_type">{{ recordTypeLabel(item.record_type) }}</span>
                </td>
                <td
                  v-for="u in units"
                  :key="'c-'+item.id+'-'+u.id"
                  class="td-cell"
                  :class="cellClass(u, block, item)"
                  @click="canEdit && !isBlockedByPreferredProcess(block) ? openUnitModal(u, block.id) : null"
                >
                  <template v-if="isBlockLocked(u, block)">
                    <span class="lock-icon">&#128274;</span>
                  </template>
                  <template v-else>
                    {{ cellDisplay(u, item) }}
                  </template>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 台目入力モーダル -->
    <div v-if="modalUnit" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ t('integratedOperation.checkInput') }}</h3>
          <div class="modal-header-actions">
            <button class="btn-secondary btn-sm" @click="closeModal">{{ t('common.close') }}</button>
            <button class="btn-close" @click="closeModal">&times;</button>
          </div>
        </div>
        <div class="modal-body">
          <div
            v-for="block in modalVisibleBlocks"
            :key="'mb-'+block.id"
            class="process-section"
            :class="{ 'ratio-4-1': block.sketch_image_url && (!isBlockLockedForModal(block) || isBlockViewOnlyForModal(block)) && block.items?.length }"
          >
            <div class="process-section-header" :class="{ locked: isBlockLockedForModal(block) && !isBlockViewOnlyForModal(block), 'view-only-header': isBlockViewOnlyForModal(block) }">
              <strong>{{ block.process_code }} {{ block.process_name }}</strong>
              <span v-if="getBlockProgress(block)" class="progress-text">
                {{ getBlockProgress(block).done }} / {{ getBlockProgress(block).total }}
              </span>
              <span v-if="modalUnit?.sei_ban" class="sei-ban-label">刻印番号: {{ modalUnit.sei_ban }}</span>
              <span v-if="isBlockHeld(modalUnit, block.id)" class="lock-label hold-lock">
                この工程は保留中です
                <button v-if="isLeaderOrAbove" class="btn-release-hold" @click="releaseHold(block.id)">保留解除</button>
              </span>
              <span v-else-if="isBlockLockedForModal(block) && isBlockLockedByHold(modalUnit, block)" class="lock-label hold-lock">前工程が保留中のためロック</span>
              <span v-else-if="isBlockViewOnlyForModal(block)" class="lock-label" style="color:#16a34a">チェック完了（閲覧のみ）</span>
              <span v-else-if="isBlockLockedForModal(block)" class="lock-label">{{ t('integratedOperation.lockedByPrevious') }}</span>
              <button
                v-if="block.sketch_image_url && (!isBlockLockedForModal(block) || isBlockViewOnlyForModal(block))"
                class="btn-sketch-toggle"
                @click="sketchCollapsed[block.id] = !sketchCollapsed[block.id]"
              >{{ sketchCollapsed[block.id] ? '▶ 台紙表示' : '▼ 台紙非表示' }}</button>
            </div>

            <!-- チェック項目 -->
            <div v-if="!isBlockLockedForModal(block) || isBlockViewOnlyForModal(block)" class="items-list" :class="{ 'view-only': isBlockViewOnlyForModal(block) }">
              <div v-for="(item, itemIdx) in block.items" :key="'mi-'+item.id" class="item-row" :class="{ 'item-optional': !item.is_required }">
                <span class="item-no">{{ itemIdx + 1 }}</span>
                <div class="item-label-area">
                  <span class="item-name">{{ item.item_name }}</span>
                  <span v-if="item.is_required" class="required-mark">*</span>
                  <span v-if="item.standard" class="item-hint">{{ item.standard }}</span>
                  <span v-if="item.unit" class="item-hint">[{{ item.unit }}]</span>
                </div>
                <button
                  v-if="item.attachments?.length"
                  class="btn-attachment-ref"
                  @click="openAttachmentViewer(item)"
                >付表({{ item.attachments.length }})</button>
                <div class="item-input-area">
                  <!-- CHECK -->
                  <template v-if="item.record_type === 'CHECK'">
                    <button
                      class="judge-btn ok"
                      :class="{ active: modalResponses[item.id]?.judgement === 'OK' }"
                      @click="setJudgement(item.id, 'OK')"
                      :disabled="!canEdit"
                    >OK</button>
                    <button
                      class="judge-btn ng"
                      :class="{ active: modalResponses[item.id]?.judgement === 'NG' }"
                      @click="setJudgement(item.id, 'NG')"
                      :disabled="!canEdit"
                    >NG</button>
                    <button
                      class="judge-btn rework"
                      :class="{ active: modalResponses[item.id]?.judgement === '修正流動' }"
                      @click="setJudgement(item.id, '修正流動')"
                      :disabled="!canEdit"
                    >{{ t('integratedOperation.reworkFlow') }}</button>
                  </template>
                  <!-- NUMERIC_CHECK -->
                  <template v-else-if="item.record_type === 'NUMERIC_CHECK'">
                    <div class="numeric-check-row">
                      <input
                        type="number"
                        step="any"
                        class="numeric-input"
                        :value="modalResponses[item.id]?.numeric_value ?? ''"
                        @input="setNumericOnly(item.id, $event.target.value)"
                        :disabled="!canEdit"
                        :placeholder="item.criteria || '数値'"
                      />
                      <span v-if="item.unit" class="unit-label">{{ item.unit }}</span>
                      <button
                        class="judge-btn ok"
                        :class="{ active: modalResponses[item.id]?.judgement === 'OK' }"
                        @click="setJudgement(item.id, 'OK')"
                        :disabled="!canEdit"
                      >OK</button>
                      <button
                        class="judge-btn ng"
                        :class="{ active: modalResponses[item.id]?.judgement === 'NG' }"
                        @click="setJudgement(item.id, 'NG')"
                        :disabled="!canEdit"
                      >NG</button>
                      <button
                        class="judge-btn rework"
                        :class="{ active: modalResponses[item.id]?.judgement === '修正流動' }"
                        @click="setJudgement(item.id, '修正流動')"
                        :disabled="!canEdit"
                      >{{ t('integratedOperation.reworkFlow') }}</button>
                    </div>
                  </template>
                  <!-- NUMERIC -->
                  <template v-else-if="isNumericRecordType(item.record_type)">
                    <input
                      type="number"
                      step="any"
                      class="numeric-input"
                      :class="{ 'numeric-ok': modalResponses[item.id]?.judgement === 'OK' && item.criteria, 'numeric-ng': modalResponses[item.id]?.judgement === 'NG' && item.criteria }"
                      :value="modalResponses[item.id]?.numeric_value ?? ''"
                      @input="setNumeric(item.id, $event.target.value)"
                      :disabled="!canEdit"
                      :placeholder="item.criteria || '数値'"
                    />
                    <span v-if="item.unit" class="unit-label">{{ item.unit }}</span>
                    <span v-if="modalResponses[item.id]?.judgement && item.criteria" class="auto-judge-badge" :class="modalResponses[item.id].judgement === 'OK' ? 'ok' : 'ng'">{{ modalResponses[item.id].judgement }}</span>
                  </template>
                  <!-- PHOTO / PHOTO_NUMERIC -->
                  <template v-else-if="item.record_type === 'PHOTO' || item.record_type === 'PHOTO_NUMERIC'">
                    <div class="photo-input-row">
                      <label class="photo-upload-btn" :class="{ disabled: !canEdit }">
                        {{ modalResponses[item.id]?.photo_url ? '写真変更' : '写真撮影' }}
                        <input type="file" accept="image/*" capture="environment" :disabled="!canEdit" @change="uploadCheckPhoto($event, item.id)" style="display:none" />
                      </label>
                      <div v-if="modalResponses[item.id]?.photo_url" class="photo-preview-mini">
                        <img :src="modalResponses[item.id].photo_url" alt="撮影写真" @click="previewPhoto(modalResponses[item.id].photo_url)" />
                      </div>
                      <span v-if="modalResponses[item.id]?.photo_url" class="photo-ok-badge">撮影済</span>
                    </div>
                    <div v-if="item.record_type === 'PHOTO_NUMERIC'" class="photo-numeric-sub">
                      <input
                        type="number" step="any" class="numeric-input"
                        :value="modalResponses[item.id]?.numeric_value ?? ''"
                        @input="setNumeric(item.id, $event.target.value)"
                        :disabled="!canEdit"
                        :placeholder="item.criteria || '数値'"
                      />
                      <span v-if="item.unit" class="unit-label">{{ item.unit }}</span>
                    </div>
                  </template>
                  <!-- TEXT -->
                  <template v-else>
                    <textarea
                      class="text-input text-area"
                      :value="modalResponses[item.id]?.text_value ?? ''"
                      @input="setText(item.id, $event.target.value)"
                      :disabled="!canEdit"
                      :placeholder="item.criteria || 'テキスト'"
                      rows="1"
                    />
                  </template>
                </div>
              </div>
            </div>

            <!-- 略図 + フィールドオーバーレイ -->
            <div
              v-if="block.sketch_image_url && (!isBlockLockedForModal(block) || isBlockViewOnlyForModal(block))"
              v-show="!sketchCollapsed[block.id]"
              class="sketch-container"
              :ref="el => setSketchContainerRef(block.id, el)"
            >
              <div class="sketch-zoom-bar">
                <button class="btn-zoom" @click="setSketchZoom(block.id, -0.2)">−</button>
                <span class="zoom-label">{{ Math.round((sketchZoom[block.id] || 1) * 100) }}%</span>
                <button class="btn-zoom" @click="setSketchZoom(block.id, 0.2)">＋</button>
                <button class="btn-zoom" @click="sketchZoom[block.id] = 1">リセット</button>
              </div>
              <div class="sketch-inner" :style="{ width: ((sketchZoom[block.id] || 1) * 100) + '%' }">
                <img :src="block.sketch_image_url" alt="略図" class="sketch-img" @load="onSketchImgLoad(block.id, $event)" />
                <div
                  v-for="field in (block.sketch_fields || [])"
                  :key="'sf-'+field.id"
                  class="sketch-field-overlay"
                  :style="sketchFieldStyle(block.id, field)"
                >
                  <template v-if="field.field_type === 'checkbox'">
                    <button
                      class="sketch-overlay-btn"
                      :class="{ checked: modalSketchFieldResponses[block.id]?.[field.key] === true }"
                      @click="setSketchFieldValue(block.id, field.key, modalSketchFieldResponses[block.id]?.[field.key] === true ? null : true)"
                      :disabled="!canEdit"
                    >{{ modalSketchFieldResponses[block.id]?.[field.key] === true ? '✓' : '' }}</button>
                  </template>
                  <template v-else-if="field.field_type === 'pen'">
                    <canvas
                      :ref="el => setPenCanvasRef(block.id, field.key, el)"
                      class="pen-canvas-overlay"
                      :class="{ 'pen-inactive': !penModeActive[block.id] }"
                      :width="field.width || 120"
                      :height="field.height || 40"
                      @pointerdown="penDown(block.id, field.key, $event)"
                      @pointermove="penMove(block.id, field.key, $event)"
                      @pointerup="penUp(block.id, field.key, $event)"
                      @pointerleave="penUp(block.id, field.key, $event)"
                    />
                    <button v-if="canEdit && penModeActive[block.id]" class="btn-pen-clear-overlay" title="クリア" @click="penClear(block.id, field.key)">&#10005;</button>
                  </template>
                  <template v-else>
                    <input
                      type="text"
                      class="sketch-overlay-input"
                      :value="modalSketchFieldResponses[block.id]?.[field.key] ?? ''"
                      @input="setSketchFieldValue(block.id, field.key, $event.target.value)"
                      :disabled="!canEdit"
                    />
                  </template>
                </div>
              </div>
            </div>

            <!-- ロック中表示 -->
            <div v-else class="locked-message">
              <template v-if="isBlockHeld(modalUnit, block.id)">
                <div class="hold-reason-display">
                  <strong>保留理由:</strong> {{ getBlockHoldReason(modalUnit, block.id) || '未記入' }}
                </div>
              </template>
              <template v-else>
                {{ t('integratedOperation.completePreviousRequired') }}
              </template>
            </div>

          </div>
          <div class="modal-save-bar">
            <div class="modal-save-bar-main">
              <button
                v-if="!isReviewMode && canEdit && modalVisibleBlocks.some(b => b.sketch_image_url && (b.sketch_fields || []).some(f => f.field_type === 'pen'))"
                class="btn-pen-mode-toggle"
                :class="{ active: modalPenModeOn }"
                @click="toggleModalPenMode"
              >{{ modalPenModeOn ? '✏️ 描画ON' : '✏️ 描画OFF' }}</button>
              <span class="modal-unit-label">台目 #{{ modalUnit.sequence_no }} {{ isReviewMode ? '確認' : '入力' }}{{ modalUnit.sei_ban ? ' | 刻印番号: ' + modalUnit.sei_ban : '' }}</span>
              <button
                class="btn-secondary btn-sm"
                @click="moveModalUnit(-1)"
                :disabled="!canMovePrevUnit"
              >{{ t('integratedOperation.prevUnit') }}</button>
              <button
                class="btn-secondary btn-sm"
                @click="moveModalUnit(1)"
                :disabled="!canMoveNextUnit"
              >{{ t('integratedOperation.nextUnit') }}</button>
              <span class="status-chip" :class="statusClass(modalHeaderStatusCode)">{{ modalHeaderStatusLabel }}</span>
              <button
                v-if="!isReviewMode && modalVisibleBlocks.length === 1 && !isBlockLockedForModal(modalVisibleBlocks[0]) && !isBlockViewOnlyForModal(modalVisibleBlocks[0]) && modalVisibleBlocks[0].items?.length"
                class="btn-primary btn-sm"
                @click="saveBlockChecks(modalVisibleBlocks[0], { hold: false })"
                :disabled="savingBlock === modalVisibleBlocks[0].id || !canEdit"
              >
                {{ savingBlock === modalVisibleBlocks[0].id ? t('common.saving') : t('integratedOperation.saveThisProcess') }}
              </button>
              <button
                v-if="!isReviewMode && isLeaderOrAbove && modalVisibleBlocks.length === 1 && !isBlockLockedForModal(modalVisibleBlocks[0]) && !isBlockViewOnlyForModal(modalVisibleBlocks[0]) && modalVisibleBlocks[0].items?.length"
                class="btn-secondary btn-sm btn-hold"
                @click="saveBlockChecks(modalVisibleBlocks[0], { hold: true })"
                :disabled="savingBlock === modalVisibleBlocks[0].id || !canEdit"
              >{{ t('integratedOperation.hold') }}</button>
              <button class="btn-secondary btn-sm" @click="closeModal">{{ t('common.close') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- バッチ編集ダイアログ -->
    <div v-if="editBatchDialog.visible" class="modal-backdrop" @click.self="editBatchDialog.visible = false">
      <div class="modal-panel edit-batch-modal">
        <h3 class="modal-title">バッチ編集</h3>
        <div class="edit-batch-form">
          <label>
            <span class="field-label">計画日</span>
            <input type="date" v-model="editBatchDialog.plan_date" />
          </label>
          <label>
            <span class="field-label">台数</span>
            <input type="number" min="1" v-model.number="editBatchDialog.quantity" />
          </label>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary btn-sm" @click="editBatchDialog.visible = false">キャンセル</button>
          <button class="btn-primary btn-sm" :disabled="actionLoading" @click="submitEditBatch">保存</button>
        </div>
      </div>
    </div>

    <!-- 付表閲覧モーダル -->
    <div v-if="attachmentViewer.visible" class="modal-backdrop att-backdrop" @click.self="closeAttachmentViewer">
      <div class="modal-panel att-modal-panel">
        <div class="att-modal-header">
          <div>
            <h3 class="att-modal-title">付表参照</h3>
            <div class="att-modal-item-name">{{ attachmentViewer.itemName }}</div>
          </div>
          <button class="btn-secondary btn-sm" @click="closeAttachmentViewer">閉じる</button>
        </div>
        <div v-if="attachmentViewer.attachments.length" class="att-list">
          <div v-for="(att, aIdx) in attachmentViewer.attachments" :key="aIdx" class="att-card">
            <div class="att-card-title">{{ att.title || `付表 ${att.display_order || aIdx + 1}` }}</div>
            <div v-if="att.image_url" class="att-image-wrap">
              <img :src="att.image_url" :alt="att.title || '付表画像'" />
            </div>
            <div class="att-text"><strong>補足説明:</strong> {{ att.description || '-' }}</div>
            <div class="att-text"><strong>確認ポイント:</strong> {{ att.check_point || '-' }}</div>
            <div class="att-text"><strong>OK例:</strong> {{ att.ok_example || '-' }}</div>
            <div class="att-text"><strong>NG例:</strong> {{ att.ng_example || '-' }}</div>
          </div>
        </div>
        <div v-else class="no-data">付表はありません。</div>
      </div>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">{{ pageTitleText }}</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import { t } from '@/i18n'
const route = useRoute()
const router = useRouter()

// --- 権限 ---
const canAccessQuality = (resource, level = 'view', aliases = [], fallbackToQuality = true) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) return candidates.some((c) => hasPermission(user, c, level))
  return fallbackToQuality ? hasPermission(user, 'quality', level) : false
}
const isReviewMode = computed(() => route.name === 'IntegratedChecksheetReview')
const isTestMode = computed(() => Boolean(route.query?.test_template_id) && !isReviewMode.value)
const pageTitleText = computed(() => (
  isTestMode.value
    ? '工程一体チェックシート テスト実施'
    : (isReviewMode.value ? t('integratedOperation.pageTitleReview') : t('integratedOperation.pageTitleWork'))
))
const isLeaderOrAbove = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const role = user.profile?.role || ''
  return ['leader', 'supervisor', 'chief', 'manager'].includes(role)
})
const isSupervisorUser = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  return (user.profile?.role || '') === 'supervisor'
})
const canView = computed(() =>
  canAccessQuality(
    isReviewMode.value ? 'quality.integrated_checksheet_review' : 'quality.integrated_checksheet_operation',
    'view',
    isReviewMode.value
      ? ['quality.product_checksheet_review']
      : [
          'quality.integrated_checksheet_operation',
          'quality.product_checksheet_input',
          'quality.integrated_checksheet',
          'quality',
        ],
    !isReviewMode.value
  )
)
const canEdit = computed(() =>
  canAccessQuality(
    isReviewMode.value ? 'quality.integrated_checksheet_review' : 'quality.integrated_checksheet_operation',
    'edit',
    isReviewMode.value
      ? ['quality.product_checksheet_review']
      : [
          'quality.integrated_checksheet_operation',
          'quality.product_checksheet_input',
          'quality.integrated_checksheet',
          'quality',
        ],
    !isReviewMode.value
  )
)

// --- マスタ ---
const allLines = ref([])
const allProducts = ref([])
const lineOptions = computed(() => allLines.value)
const lineFinalProductsByLine = ref({})
const filteredProductOptions = computed(() => {
  if (!selectedLine.value) return allProducts.value
  return lineFinalProductsByLine.value[String(selectedLine.value)] || []
})
const newBatchProductOptions = computed(() => {
  if (!newBatch.line) return allProducts.value
  return lineFinalProductsByLine.value[String(newBatch.line)] || []
})

// --- フィルタ ---
const selectedLine = ref('')
const selectedProduct = ref('')
const batchStatusFilter = ref('OPEN')
const seiBanFilter = ref('')

// --- バッチ一覧 ---
const batches = ref([])
const loadingBatches = ref(false)
const loading = computed(() => loadingBatches.value)

// --- 新規バッチ ---
const newBatch = reactive({ product: '', line: '', quantity: 1, plan_date: '', lot_no: '' })
const preparing = ref(false)
const showNewBatchSection = ref(true)
const newBatchSectionRef = ref(null)
const loadingTestTemplate = ref(false)
const testTemplate = ref(null)
const testBatch = reactive({ quantity: 1, plan_date: '', lot_no: 'TEST' })

// --- 刻印番号 履歴照会 ---
const historyResults = ref([])
const loadingHistory = ref(false)

const searchHistory = async () => {
  if (!seiBanFilter.value.trim()) {
    historyResults.value = []
    return
  }
  loadingHistory.value = true
  try {
    const res = await api.integratedChecksheets.searchUnitHistory({ sei_ban: seiBanFilter.value.trim() })
    historyResults.value = res.data || []
  } catch {
    historyResults.value = []
  } finally {
    loadingHistory.value = false
  }
}

const formatHistoryDate = (isoStr) => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return '-'
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const historyRecordTypeLabel = (rt) => {
  const map = { CHECK: 'C', NUMERIC: 'N', NUMERIC_CHECK: 'NC', PHOTO_NUMERIC: 'PN', PHOTO: 'P', TEXT: 'T' }
  return map[rt] || rt
}

const historyJudgementClass = (j) => {
  if (j === 'OK') return 'history-ok'
  if (j === 'NG') return 'history-ng'
  if (j === '修正流動') return 'history-rework'
  return ''
}

// --- バッチ詳細 ---
const activeBatchId = ref(null)
const activeBatch = ref(null)
const reviewRole = ref('')
const units = ref([])
const loadingUnits = ref(false)
const actionLoading = ref(false)
const templateBlocks = ref([])
const attachmentViewer = ref({ visible: false, itemName: '', attachments: [] })
const openAttachmentViewer = (item) => {
  attachmentViewer.value = {
    visible: true,
    itemName: item.item_name || '',
    attachments: item.attachments || [],
  }
}
const closeAttachmentViewer = () => {
  attachmentViewer.value = { visible: false, itemName: '', attachments: [] }
}
const matrixVisibleBlocks = computed(() => {
  if (!preferredProcessId.value) return templateBlocks.value
  return templateBlocks.value.filter((b) => !isBlockedByPreferredProcess(b))
})
const preferredProcessId = ref('')
const lockedLineIdFromRoute = ref('')
const isLineLockedFromRoute = computed(() => Boolean(lockedLineIdFromRoute.value))

const processIdFromBlock = (block) => {
  if (!block) return ''
  return String(
    block.process_id
    ?? block.process
    ?? block.production_process
    ?? block.production_process_id
    ?? block.process_master
    ?? block.process_master_id
    ?? ''
  )
}

const isBlockedByPreferredProcess = (block) => {
  const preferred = String(preferredProcessId.value || '')
  if (!preferred) return false
  const blockProcessId = processIdFromBlock(block)
  if (!blockProcessId) return false
  return blockProcessId !== preferred
}

// --- モーダル ---
const modalUnit = ref(null)
const modalResponses = ref({})
const modalSketchFieldResponses = ref({})
const modalSelectedBlockId = ref(null)
const savingBlock = ref(null)

// --- ヘルパー ---
const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('ja-JP')
}
const formatDate = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const reviewRoleLabel = computed(() => {
  if (reviewRole.value === 'leader') return 'リーダ'
  if (reviewRole.value === 'supervisor') return '班長'
  return ''
})

const processProgressChips = (progressList) => {
  if (!Array.isArray(progressList) || !progressList.length) return [{ key: 'none', label: '-', done: false }]
  return progressList.map((p, idx) => {
    const doneUnits = Number(p.done_units ?? 0)
    const totalUnits = Number(p.total_units ?? 0)
    return {
      key: `${p.process_block_id || idx}`,
      label: `${p.process_code || p.process_name || '-'}:${doneUnits}/${totalUnits}`,
      done: totalUnits > 0 && doneUnits >= totalUnits,
    }
  })
}

const getBlockCheckerName = (unit, blockId) => {
  if (!unit?.checks || !Array.isArray(unit.checks)) return ''
  const checks = unit.checks
    .filter((c) => Number(c.process_block_id) === Number(blockId) && c.checked_by_name)
    .sort((a, b) => {
      const ta = a?.checked_at ? new Date(a.checked_at).getTime() : 0
      const tb = b?.checked_at ? new Date(b.checked_at).getTime() : 0
      return tb - ta
    })
  return checks[0]?.checked_by_name || ''
}

const getBlockCheckedDate = (unit, blockId) => {
  if (!unit?.checks || !Array.isArray(unit.checks)) return ''
  const checks = unit.checks
    .filter((c) => Number(c.process_block_id) === Number(blockId) && c.checked_at)
    .sort((a, b) => new Date(b.checked_at).getTime() - new Date(a.checked_at).getTime())
  if (!checks[0]?.checked_at) return ''
  const d = new Date(checks[0].checked_at)
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
}


const statusClass = (st) => {
  switch (st) {
    case 'PENDING': return 'pending'
    case 'IN_PROGRESS': return 'in-progress'
    case 'COMPLETED': return 'completed'
    case 'APPROVED': return 'approved'
    case 'OPEN': return 'in-progress'
    case 'LEADER_CONFIRMED': return 'completed'
    case 'SUPERVISOR_CONFIRMED': return 'approved'
    default: return 'pending'
  }
}

const statusLabel = (st) => {
  switch (st) {
    case 'PENDING': return t('integratedOperation.status.pending')
    case 'IN_PROGRESS': return t('integratedOperation.status.inProgress')
    case 'COMPLETED': return t('integratedOperation.status.completed')
    case 'APPROVED': return t('integratedOperation.status.approved')
    case 'OPEN': return t('integratedOperation.status.open')
    case 'LEADER_CONFIRMED': return t('integratedOperation.status.leaderConfirmed')
    case 'SUPERVISOR_CONFIRMED': return t('integratedOperation.status.supervisorConfirmed')
    default: return st
  }
}

const statusShort = (st) => {
  switch (st) {
    case 'PENDING': return '-'
    case 'IN_PROGRESS': return '中'
    case 'COMPLETED': return '済'
    case 'APPROVED': return '認'
    default: return '-'
  }
}

const recordTypeLabel = (rt) => {
  switch (rt) {
    case 'CHECK': return 'C'
    case 'NUMERIC': return 'N'
    case 'NUMERIC_CHECK': return '数+C'
    case 'PHOTO_NUMERIC': return '写+数'
    case 'PHOTO': return '写'
    case 'TEXT': return 'T'
    default: return rt
  }
}

const isNumericRecordType = (recordType) => ['NUMERIC', 'PHOTO_NUMERIC'].includes(String(recordType || '').toUpperCase())
const isPhotoOnlyRecordType = (recordType) => String(recordType || '').toUpperCase() === 'PHOTO'

// --- 工程ロック判定 ---
const getUnitProcessProgress = (unit) => {
  return unit.process_progress || []
}

const isBlockLocked = (unit, block) => {
  const progress = getUnitProcessProgress(unit)
  let holdFound = false
  for (const pp of progress) {
    if (holdFound) return true
    if (isBlockHeld(unit, pp.process_block_id)) holdFound = true
    if (pp.process_block_id === block.id) return holdFound
    if (!pp.complete && pp.total > 0) return true
  }
  return false
}

const isBlockCompleted = (unit, block) => {
  if (!unit) return false
  const progress = getUnitProcessProgress(unit)
  const pp = progress.find((p) => p.process_block_id === block.id)
  return pp?.complete && pp?.total > 0
}

const isBlockViewOnly = (unit, block) => {
  if (isReviewMode.value) return true
  return isBlockCompleted(unit, block)
}

const isBlockLockedForModal = (block) => {
  if (!modalUnit.value) return false
  return isBlockLocked(modalUnit.value, block)
}

const isBlockLockedByHold = (unit, block) => {
  if (!unit) return false
  const progress = getUnitProcessProgress(unit)
  for (const pp of progress) {
    if (pp.process_block_id === block.id) return false
    if (isBlockHeld(unit, pp.process_block_id)) return true
  }
  return false
}

const isBlockViewOnlyForModal = (block) => {
  if (!modalUnit.value) return false
  return isBlockViewOnly(modalUnit.value, block)
}

const getBlockProgress = (block) => {
  if (!modalUnit.value) return null
  const progress = getUnitProcessProgress(modalUnit.value)
  return progress.find((pp) => pp.process_block_id === block.id) || null
}

// --- マトリクスセル表示 ---
const getCheckForItem = (unit, item) => {
  if (!unit.checks) return null
  return unit.checks.find((c) => c.item === item.id)
}

const cellDisplay = (unit, item) => {
  const check = getCheckForItem(unit, item)
  if (!check) return ''
  if (item.record_type === 'CHECK') {
    if (check.judgement === 'OK') return '✓'
    if (check.judgement === 'NG') return '✗'
    if (check.judgement === '修正流動') return '修正流動'
    return ''
  }
  if (item.record_type === 'NUMERIC_CHECK') {
    const num = check.numeric_value != null ? check.numeric_value : ''
    const jdg = check.judgement === 'OK' ? '✓' : check.judgement === 'NG' ? '✗' : check.judgement === '修正流動' ? '修' : ''
    return jdg ? `${num} ${jdg}` : String(num)
  }
  if (isNumericRecordType(item.record_type)) {
    return check.numeric_value != null ? check.numeric_value : ''
  }
  if (isPhotoOnlyRecordType(item.record_type)) {
    return check.photo_url ? '📷' : ''
  }
  return check.text_value || ''
}

const cellClass = (unit, block, item) => {
  if (isBlockedByPreferredProcess(block)) return 'cell-disabled-by-process'
  if (isBlockLocked(unit, block)) return 'cell-locked'
  const check = getCheckForItem(unit, item)
  if (!check) return 'cell-empty'
  if (item.record_type === 'CHECK' || item.record_type === 'NUMERIC_CHECK') {
    if (check.judgement === 'OK') return 'cell-ok'
    if (check.judgement === 'NG') return 'cell-ng'
    if (check.judgement === '修正流動') return 'cell-rework'
  }
  if (isNumericRecordType(item.record_type) && check.numeric_value != null && item.criteria) {
    const bounds = parseCriteria(item.criteria, item.standard)
    if (bounds) {
      const v = parseFloat(check.numeric_value)
      const okMin = bounds.min === null || v >= bounds.min
      const okMax = bounds.max === null || v <= bounds.max
      return (okMin && okMax) ? 'cell-ok' : 'cell-ng'
    }
  }
  if (check.numeric_value != null || check.text_value || check.photo_url) return 'cell-filled'
  return 'cell-empty'
}

// --- データ取得 ---
const loadMasters = async () => {
  try {
    const [lineRes, productRes] = await Promise.all([
      api.lines.getLines({ line_type: 'PROD', page_size: 1000 }),
      api.products.getProducts({ is_active: true, is_line_final_product: true, page_size: 1000 }),
    ])
    allLines.value = lineRes.data?.results || lineRes.data || []
    allProducts.value = productRes.data?.results || productRes.data || []
  } catch (error) {
    console.error('マスタ取得に失敗:', error)
  }
}

const ensureLineFinalProducts = async (lineId) => {
  if (!lineId) return allProducts.value
  const key = String(lineId)
  if (Object.prototype.hasOwnProperty.call(lineFinalProductsByLine.value, key)) {
    return lineFinalProductsByLine.value[key]
  }
  try {
    const res = await api.integratedChecksheets.listTemplates({ line: lineId, is_active: true, page_size: 1000 })
    const templates = res.data?.results || res.data || []
    const productMap = new Map()
    templates.forEach((t) => {
      if (t.product && !productMap.has(Number(t.product))) {
        productMap.set(Number(t.product), {
          id: t.product,
          product_code: t.product_code || '',
          product_name: t.product_name || '',
        })
      }
    })
    const products = [...productMap.values()]
    lineFinalProductsByLine.value = {
      ...lineFinalProductsByLine.value,
      [key]: products,
    }
    return products
  } catch (error) {
    console.error('ライン製品候補の取得に失敗:', error)
    lineFinalProductsByLine.value = {
      ...lineFinalProductsByLine.value,
      [key]: [],
    }
    return []
  }
}

const doSearch = () => {
  loadBatches()
  if (seiBanFilter.value.trim()) {
    searchHistory()
  } else {
    historyResults.value = []
  }
}

const resetFilters = () => {
  if (!isLineLockedFromRoute.value) selectedLine.value = ''
  selectedProduct.value = ''
  batchStatusFilter.value = 'OPEN'
  seiBanFilter.value = ''
  historyResults.value = []
  loadBatches()
}

const loadBatches = async () => {
  if (isTestMode.value) {
    batches.value = []
    return
  }
  loadingBatches.value = true
  try {
    const params = {}
    const effectiveLineId = lockedLineIdFromRoute.value || selectedLine.value
    if (effectiveLineId) params.line = effectiveLineId
    if (selectedProduct.value) params.product = selectedProduct.value
    if (batchStatusFilter.value) params.status = batchStatusFilter.value
    if (seiBanFilter.value) params.sei_ban = seiBanFilter.value
    const res = await api.integratedChecksheets.listBatches(params)
    batches.value = res.data?.results || res.data || []
  } catch {
    batches.value = []
  } finally {
    loadingBatches.value = false
  }
}

const loadBatchUnits = async (batchId) => {
  if (isTestMode.value) return
  loadingUnits.value = true
  try {
    const [unitsRes, batchRes] = await Promise.all([
      api.integratedChecksheets.getBatchUnits(batchId),
      api.integratedChecksheets.getBatch(batchId),
    ])
    units.value = unitsRes.data || []
    const batchData = batchRes.data
    // テンプレートの工程ブロック情報を取得
    if (batchData.template) {
      const tmplRes = await api.integratedChecksheets.getTemplate(batchData.template)
      templateBlocks.value = tmplRes.data?.process_blocks || []
    }
  } catch (error) {
    console.error('台目取得に失敗:', error)
    units.value = []
    templateBlocks.value = []
  } finally {
    loadingUnits.value = false
  }
}

const isCheckFilled = (check) => {
  if (!check) return false
  if (check.judgement) return true
  if (check.numeric_value !== null && check.numeric_value !== '' && check.numeric_value !== undefined) return true
  if (check.text_value) return true
  if (check.photo_url) return true
  return false
}

const buildUnitProcessProgress = (unitChecks = [], blocks = templateBlocks.value) => {
  const checksByItem = new Map(unitChecks.map((check) => [Number(check.item), check]))
  return (blocks || []).map((block) => {
    const items = Array.isArray(block.items) ? block.items : []
    const requiredItems = items.filter((item) => item.is_required)
    const done = items.filter((item) => isCheckFilled(checksByItem.get(Number(item.id)))).length
    const requiredDone = requiredItems.filter((item) => isCheckFilled(checksByItem.get(Number(item.id)))).length
    return {
      process_block_id: block.id,
      process_code: block.process_code || '',
      process_name: block.process_name || '',
      sort_order: block.sort_order || 0,
      total: items.length,
      done,
      complete: requiredItems.length === 0 || requiredDone >= requiredItems.length,
    }
  })
}

const buildBatchProcessProgress = (targetUnits, blocks = templateBlocks.value) => {
  const totalUnits = Array.isArray(targetUnits) ? targetUnits.length : 0
  return (blocks || []).map((block) => {
    const requiredItemIds = new Set((block.items || []).filter((item) => item.is_required).map((item) => Number(item.id)))
    const doneUnits = requiredItemIds.size === 0
      ? totalUnits
      : (targetUnits || []).filter((unit) => {
          const checkedIds = new Set((unit.checks || []).filter(isCheckFilled).map((check) => Number(check.item)))
          return [...requiredItemIds].every((itemId) => checkedIds.has(itemId))
        }).length
    return {
      process_block_id: block.id,
      process_code: block.process_code || '',
      process_name: block.process_name || '',
      done_units: doneUnits,
      total_units: totalUnits,
    }
  })
}

const buildLocalUnitStatus = (unit) => {
  const progress = buildUnitProcessProgress(unit.checks || [])
  if (!progress.length) return 'PENDING'
  if (progress.every((item) => item.complete)) return 'COMPLETED'
  if ((unit.checks || []).some(isCheckFilled) || hasUnitHoldFlag(unit)) return 'IN_PROGRESS'
  return 'PENDING'
}

const buildLocalUnit = (sequenceNo) => {
  const unit = {
    id: `test-unit-${sequenceNo}`,
    sequence_no: sequenceNo,
    status: 'PENDING',
    completed_at: null,
    approved_at: null,
    approved_by: null,
    checks: [],
    sketch_responses: [],
    process_progress: [],
  }
  unit.process_progress = buildUnitProcessProgress(unit.checks)
  return unit
}

const refreshTestBatchState = () => {
  if (!isTestMode.value) return
  units.value = units.value.map((unit) => {
    const nextStatus = buildLocalUnitStatus(unit)
    const completedAt = nextStatus === 'COMPLETED' ? (unit.completed_at || new Date().toISOString()) : null
    return {
      ...unit,
      status: nextStatus,
      completed_at: completedAt,
      process_progress: buildUnitProcessProgress(unit.checks || []),
    }
  })
  if (activeBatch.value) {
    const completedCount = units.value.filter((unit) => unit.status === 'COMPLETED').length
    activeBatch.value = {
      ...activeBatch.value,
      quantity: units.value.length,
      unit_count: units.value.length,
      completed_count: completedCount,
      status: completedCount >= units.value.length && units.value.length > 0 ? 'COMPLETED' : 'OPEN',
      process_progress: buildBatchProcessProgress(units.value),
    }
  }
}

const loadTestTemplate = async () => {
  const templateId = Number(route.query?.test_template_id || 0)
  if (!templateId) return
  loadingTestTemplate.value = true
  try {
    const res = await api.integratedChecksheets.getTemplate(templateId)
    testTemplate.value = res.data
    templateBlocks.value = Array.isArray(res.data?.process_blocks) ? res.data.process_blocks : []
    if (!testBatch.plan_date) {
      testBatch.plan_date = formatDate(new Date())
    }
  } catch (error) {
    console.error('テストテンプレート取得失敗:', error)
    testTemplate.value = null
    templateBlocks.value = []
    alert(`テストテンプレートの取得に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    loadingTestTemplate.value = false
  }
}

const openBatchDetail = async (batch) => {
  activeBatchId.value = batch.id
  activeBatch.value = batch
  await loadBatchUnits(batch.id)
}

const canLeaderConfirm = (b) => ['OPEN', 'COMPLETED'].includes(b.status)
const canShowSupervisorConfirm = (b) => b.status === 'LEADER_CONFIRMED'
const canDeleteBatch = (b) => ['OPEN', 'COMPLETED'].includes(b.status)
const canEditBatch = (b) => ['OPEN', 'COMPLETED'].includes(b.status)

const editBatchDialog = ref({ visible: false, batchId: null, plan_date: '', quantity: 1 })

const openEditBatchDialog = (batch) => {
  editBatchDialog.value = {
    visible: true,
    batchId: batch.id,
    plan_date: batch.plan_date || '',
    quantity: batch.quantity || 1,
  }
}

const submitEditBatch = async () => {
  const d = editBatchDialog.value
  if (!d.batchId) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.editBatch(d.batchId, {
      plan_date: d.plan_date || null,
      quantity: d.quantity,
    })
    d.visible = false
    await loadBatches()
  } catch (e) {
    alert(`${t('integratedOperation.alert.editFailed')}: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const deleteBatch = async (batch) => {
  if (!window.confirm(`バッチ（${batch.line_code || '-'} / ${batch.product_code || '-'}, 計画日: ${batch.plan_date || '-'}, ロット: ${batch.lot_no || '-'}）を削除しますか？この操作は取り消せません。`)) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.deleteBatch(batch.id)
    if (activeBatch.value && activeBatch.value.id === batch.id) {
      activeBatch.value = null
    }
    await loadBatches()
    alert(t('integratedOperation.alert.batchDeleted'))
  } catch (e) {
    alert(`${t('integratedOperation.alert.deleteFailed')}: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const leaderConfirm = async (batch) => {
  if (!window.confirm('リーダ確認を実行します。全台目の必須項目が完了している必要があります。よろしいですか？')) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.leaderConfirm(batch.id)
    await loadBatches()
    alert(t('integratedOperation.alert.leaderConfirmed'))
  } catch (e) {
    alert(`${t('integratedOperation.alert.leaderConfirmFailed')}: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const supervisorConfirm = async (batch) => {
  if (!isSupervisorUser.value) {
    alert(t('integratedOperation.alert.supervisorOnly'))
    return
  }
  if (!window.confirm('班長確認を実行します。よろしいですか？')) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.supervisorConfirm(batch.id)
    await loadBatches()
    alert(t('integratedOperation.alert.supervisorConfirmed'))
  } catch (e) {
    alert(`${t('integratedOperation.alert.supervisorConfirmFailed')}: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const openReviewByRole = async (batch, role) => {
  reviewRole.value = role || ''
  await openBatchDetail(batch)
}

const closeBatchDetail = () => {
  activeBatchId.value = null
  activeBatch.value = null
  reviewRole.value = ''
  units.value = []
  if (!isTestMode.value) {
    templateBlocks.value = []
  }
}

const refreshAll = () => {
  if (isTestMode.value) return
  loadBatches()
  if (activeBatchId.value) {
    loadBatchUnits(activeBatchId.value)
  }
}

const openNewBatchSection = () => {
  showNewBatchSection.value = true
  newBatchSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const showBackToProcessInput = computed(() =>
  String(route.query?.source || '') === 'mobile_process_input'
)

const backToProcessInput = () => {
  const lineId = selectedLine.value || ''
  const processId = preferredProcessId.value || ''
  router.push({
    path: '/production/mobile-process-input',
    query: {
      ...(lineId ? { line_id: String(lineId) } : {}),
      ...(processId ? { process_id: String(processId) } : {}),
    },
  })
}

const backToTemplateFromTest = () => {
  const templateId = Number(route.query?.test_template_id || 0)
  router.push({
    path: '/quality/product-checksheet/integrated/templates',
    query: templateId ? { id: String(templateId) } : {},
  })
}

const applyInitialFiltersFromQuery = async () => {
  if (isTestMode.value) return
  preferredProcessId.value = route.query?.process_id ? String(route.query.process_id) : ''
  const lineIdFromQuery = route.query?.line_id ? String(route.query.line_id) : ''
  lockedLineIdFromRoute.value = lineIdFromQuery || ''
  if (!lineIdFromQuery) return
  const exists = allLines.value.some((l) => String(l.id) === lineIdFromQuery)
  if (!exists) return
  selectedLine.value = lineIdFromQuery
  await ensureLineFinalProducts(lineIdFromQuery)
}

const startTestBatch = () => {
  if (!canEdit.value || !testTemplate.value) return
  const quantity = Number(testBatch.quantity || 0)
  if (quantity <= 0 || !testBatch.plan_date) return
  const nextUnits = Array.from({ length: quantity }, (_, index) => buildLocalUnit(index + 1))
  units.value = nextUnits
  activeBatchId.value = `test-template-${testTemplate.value.id}`
  activeBatch.value = {
    id: activeBatchId.value,
    template: testTemplate.value.id,
    template_name: testTemplate.value.name || '',
    product: testTemplate.value.product,
    product_code: testTemplate.value.product_code || '',
    product_name: testTemplate.value.product_name || '',
    line: testTemplate.value.line,
    line_code: testTemplate.value.line_code || '',
    plan_date: testBatch.plan_date,
    quantity,
    lot_no: testBatch.lot_no || 'TEST',
    status: 'OPEN',
    unit_count: quantity,
    completed_count: 0,
    process_progress: buildBatchProcessProgress(nextUnits),
    created_at: null,
    updated_at: null,
  }
  refreshTestBatchState()
}

// --- バッチ作成 ---
const prepareBatch = async () => {
  if (!canEdit.value) return
  if (!newBatch.product || !newBatch.line || !newBatch.quantity || !newBatch.plan_date) return
  preparing.value = true
  try {
    const res = await api.integratedChecksheets.prepareBatch({
      product: newBatch.product,
      line: newBatch.line,
      quantity: newBatch.quantity,
      plan_date: newBatch.plan_date,
      lot_no: newBatch.lot_no,
    })
    const created = res.data
    await loadBatches()
    if (created?.id) {
      await openBatchDetail(created)
    }
    // フォーム初期化
    newBatch.quantity = 1
    newBatch.lot_no = ''
    newBatch.plan_date = ''
  } catch (error) {
    alert(`${t('integratedOperation.alert.batchCreateFailed')}: ${error.response?.data?.detail || error.message}`)
  } finally {
    preparing.value = false
  }
}

// --- モーダル ---
const modalVisibleBlocks = computed(() => {
  if (!modalSelectedBlockId.value) return templateBlocks.value
  return templateBlocks.value.filter((b) => b.id === modalSelectedBlockId.value)
})
const modalCurrentBlock = computed(() => {
  if (modalVisibleBlocks.value.length !== 1) return null
  return modalVisibleBlocks.value[0]
})
const modalHeaderStatusCode = computed(() => {
  const block = modalCurrentBlock.value
  if (!block) return modalUnit.value?.status || 'PENDING'
  if (isBlockLockedForModal(block)) return 'PENDING'
  const p = getBlockProgress(block)
  if (!p || Number(p.total || 0) <= 0) return 'PENDING'
  if (p.complete) return 'COMPLETED'
  const done = Number(p.done || 0)
  if (done <= 0) return 'PENDING'
  return 'IN_PROGRESS'
})
const modalHeaderStatusLabel = computed(() => {
  const block = modalCurrentBlock.value
  if (!block) return statusLabel(modalUnit.value?.status)
  if (isBlockLockedForModal(block)) return 'ロック中'
  return statusLabel(modalHeaderStatusCode.value)
})
const currentModalUnitIndex = computed(() => {
  if (!modalUnit.value) return -1
  return units.value.findIndex((u) => u.id === modalUnit.value.id)
})
const canMovePrevUnit = computed(() => currentModalUnitIndex.value > 0)
const canMoveNextUnit = computed(() => {
  const idx = currentModalUnitIndex.value
  return idx >= 0 && idx < units.value.length - 1
})

const openUnitModal = (unit, blockId = null) => {
  if (!canView.value) return
  let resolvedBlockId = blockId || null
  if (!resolvedBlockId && preferredProcessId.value) {
    const matched = templateBlocks.value.find((b) => !isBlockedByPreferredProcess(b))
    if (matched?.id) resolvedBlockId = matched.id
  }
  if (resolvedBlockId) {
    const targetBlock = templateBlocks.value.find((b) => Number(b.id) === Number(resolvedBlockId))
    if (targetBlock && isBlockedByPreferredProcess(targetBlock)) return
  }
  modalUnit.value = unit
  modalSelectedBlockId.value = resolvedBlockId
  // 既存チェック結果を modalResponses にマッピング
  const resp = {}
  if (unit.checks) {
    for (const c of unit.checks) {
      resp[c.item] = {
        judgement: c.judgement || '',
        numeric_value: c.numeric_value,
        text_value: c.text_value || '',
        photo_url: c.photo_url || '',
      }
    }
  }
  // テンプレートの全項目について空エントリを用意
  for (const block of templateBlocks.value) {
    for (const item of block.items) {
      if (!resp[item.id]) {
        resp[item.id] = { judgement: '', numeric_value: null, text_value: '', photo_url: '' }
      }
    }
  }
  modalResponses.value = resp
  const sketchResp = {}
  if (unit.sketch_responses) {
    for (const sr of unit.sketch_responses) {
      const blockId = Number(sr.process_block)
      const fr = sr.field_responses && typeof sr.field_responses === 'object' ? { ...sr.field_responses } : {}
      sketchResp[blockId] = fr
    }
  }
  modalSketchFieldResponses.value = sketchResp
}

const moveModalUnit = (delta) => {
  if (!modalUnit.value) return
  const currentIdx = currentModalUnitIndex.value
  if (currentIdx < 0) return
  const nextIdx = currentIdx + delta
  if (nextIdx < 0 || nextIdx >= units.value.length) return
  const nextUnit = units.value[nextIdx]
  if (!nextUnit) return
  openUnitModal(nextUnit, modalSelectedBlockId.value)
}

const closeModal = () => {
  modalUnit.value = null
  modalResponses.value = {}
  modalSelectedBlockId.value = null
  penModeActive.value = {}
}

const setJudgement = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  // トグル: 同じ値をクリックしたらクリア
  modalResponses.value[itemId].judgement = modalResponses.value[itemId].judgement === val ? '' : val
}

const toHalfWidth = (s) => s.replace(/[０-９]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0)).replace(/．/g, '.').replace(/＋/g, '+').replace(/－/g, '-')

const parseCriteria = (criteria, standard) => {
  if (!criteria) return null
  const c = toHalfWidth(criteria).trim()
  // 範囲: "300-360", "300~360", "300～360"
  let m = c.match(/^([+-]?\d+\.?\d*)\s*[-~～]\s*([+-]?\d+\.?\d*)$/)
  if (m) return { min: parseFloat(m[1]), max: parseFloat(m[2]) }
  // 以上: ">=300", "≧300", "300以上"
  m = c.match(/^[>≧][=＝]?\s*([+-]?\d+\.?\d*)$/) || c.match(/^([+-]?\d+\.?\d*)\s*以上$/)
  if (m) return { min: parseFloat(m[1]), max: null }
  // 以下: "<=360", "≦360", "360以下"
  m = c.match(/^[<≦][=＝]?\s*([+-]?\d+\.?\d*)$/) || c.match(/^([+-]?\d+\.?\d*)\s*以下$/)
  if (m) return { min: null, max: parseFloat(m[1]) }
  // 公差: "±10" or "±10%"
  m = c.match(/^[±]\s*(\d+\.?\d*)\s*(%?)$/)
  if (m) {
    const stdVal = parseFloat(toHalfWidth(String(standard || '')))
    if (isNaN(stdVal)) return null
    const tol = parseFloat(m[1])
    if (m[2] === '%') {
      const delta = stdVal * tol / 100
      return { min: stdVal - delta, max: stdVal + delta }
    }
    return { min: stdVal - tol, max: stdVal + tol }
  }
  return null
}

const findItemForId = (itemId) => {
  for (const block of templateBlocks.value) {
    const item = block.items.find(i => i.id === itemId)
    if (item) return item
  }
  return null
}

const setNumeric = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  const numVal = val !== '' ? parseFloat(val) : null
  modalResponses.value[itemId].numeric_value = numVal
  // 自動判定
  const item = findItemForId(itemId)
  if (item && numVal !== null && !isNaN(numVal)) {
    const bounds = parseCriteria(item.criteria, item.standard)
    if (bounds) {
      const okMin = bounds.min === null || numVal >= bounds.min
      const okMax = bounds.max === null || numVal <= bounds.max
      modalResponses.value[itemId].judgement = (okMin && okMax) ? 'OK' : 'NG'
    }
  }
}

const setNumericOnly = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  modalResponses.value[itemId].numeric_value = val !== '' ? parseFloat(val) : null
}

const setText = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  modalResponses.value[itemId].text_value = val
}

const uploadCheckPhoto = async (event, itemId) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await api.integratedChecksheets.uploadAttachmentImage(formData)
    if (!modalResponses.value[itemId]) {
      modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '', photo_url: '' }
    }
    modalResponses.value[itemId].photo_url = res.data.image_url
  } catch (err) {
    console.error('写真アップロード失敗:', err)
    alert('写真のアップロードに失敗しました。')
  }
}

const previewPhoto = (url) => {
  window.open(url, '_blank')
}

const hasMissingRequiredItems = (block) => {
  if (!block || !Array.isArray(block.items)) return false
  return block.items.some((item) => {
    if (!item.is_required) return false
    const r = modalResponses.value[item.id]
    if (!r) return true
    if (item.record_type === 'CHECK') return !r.judgement
    if (item.record_type === 'NUMERIC_CHECK') return !r.judgement || r.numeric_value === null || r.numeric_value === '' || r.numeric_value === undefined
    if (isNumericRecordType(item.record_type)) return r.numeric_value === null || r.numeric_value === '' || r.numeric_value === undefined
    if (item.record_type === 'PHOTO') return !r.photo_url
    if (item.record_type === 'PHOTO_NUMERIC') return !r.photo_url || r.numeric_value === null || r.numeric_value === '' || r.numeric_value === undefined
    return !r.text_value
  })
}

const getRequiredItemIdsForUnit = () => {
  const ids = []
  for (const block of templateBlocks.value) {
    for (const item of block.items || []) {
      if (item.is_required) ids.push(item.id)
    }
  }
  return ids
}

const hasUnitMissingRequired = (unit) => {
  if (!unit) return false
  const requiredIds = getRequiredItemIdsForUnit()
  if (!requiredIds.length) return false
  const checkedIds = new Set()
  for (const c of (unit.checks || [])) {
    if (c.judgement || c.numeric_value !== null && c.numeric_value !== undefined || c.text_value || c.photo_url) {
      checkedIds.add(c.item)
    }
  }
  return requiredIds.some((id) => !checkedIds.has(id))
}

const hasUnitAnyCheckValue = (unit) => {
  if (!unit) return false
  for (const c of (unit.checks || [])) {
    if (c.judgement || c.numeric_value !== null && c.numeric_value !== undefined || c.text_value || c.photo_url) {
      return true
    }
  }
  return false
}

const hasUnitHoldFlag = (unit) => {
  if (!unit || !Array.isArray(unit.sketch_responses)) return false
  return unit.sketch_responses.some((resp) => Boolean(resp?.field_responses?._hold))
}

const isBlockHeld = (unit, blockId) => {
  if (!unit || !Array.isArray(unit.sketch_responses)) return false
  const resp = unit.sketch_responses.find((r) => Number(r.process_block) === Number(blockId))
  return Boolean(resp?.field_responses?._hold)
}

const getBlockHoldReason = (unit, blockId) => {
  if (!unit || !Array.isArray(unit.sketch_responses)) return ''
  const resp = unit.sketch_responses.find((r) => Number(r.process_block) === Number(blockId))
  return String(resp?.field_responses?._hold_reason || '')
}

const shouldShowHoldMark = (unit) => {
  return hasUnitHoldFlag(unit)
}

const sketchNaturalSizes = ref({})
const sketchContainerRefs = {}

const sketchTouchCleanups = {}
const setSketchContainerRef = (blockId, el) => {
  if (sketchTouchCleanups[blockId]) {
    sketchTouchCleanups[blockId]()
    delete sketchTouchCleanups[blockId]
  }
  sketchContainerRefs[blockId] = el
  if (!el) return
  const onTS = (e) => onSketchTouchStart(blockId, e)
  const onTM = (e) => onSketchTouchMove(blockId, e)
  const onTE = () => onSketchTouchEnd(blockId)
  el.addEventListener('touchstart', onTS, { passive: false })
  el.addEventListener('touchmove', onTM, { passive: false })
  el.addEventListener('touchend', onTE)
  sketchTouchCleanups[blockId] = () => {
    el.removeEventListener('touchstart', onTS)
    el.removeEventListener('touchmove', onTM)
    el.removeEventListener('touchend', onTE)
  }
}

const onSketchImgLoad = (blockId, e) => {
  const img = e.target
  sketchNaturalSizes.value[blockId] = { w: img.naturalWidth, h: img.naturalHeight }
}

const sketchFieldStyle = (blockId, field) => {
  const nat = sketchNaturalSizes.value[blockId]
  if (!nat || !nat.w || !nat.h) return { position: 'absolute', left: '0', top: '0' }
  return {
    position: 'absolute',
    left: `${(field.x / nat.w) * 100}%`,
    top: `${(field.y / nat.h) * 100}%`,
    width: `${(field.width / nat.w) * 100}%`,
    height: `${(field.height / nat.h) * 100}%`,
  }
}

const setSketchFieldValue = (blockId, fieldKey, value) => {
  if (!canEdit.value) return
  if (!modalSketchFieldResponses.value[blockId]) {
    modalSketchFieldResponses.value[blockId] = {}
  }
  modalSketchFieldResponses.value[blockId][fieldKey] = value
}

const sketchCollapsed = ref({})
const sketchZoom = ref({})
const setSketchZoom = (blockId, delta) => {
  const cur = sketchZoom.value[blockId] || 1
  sketchZoom.value[blockId] = Math.max(0.4, Math.min(3, +(cur + delta).toFixed(1)))
}
const pinchState = {}
const onSketchTouchStart = (blockId, e) => {
  if (e.touches.length === 2) {
    e.preventDefault()
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    pinchState[blockId] = { dist: Math.hypot(dx, dy), zoom: sketchZoom.value[blockId] || 1 }
  }
}
const onSketchTouchMove = (blockId, e) => {
  if (e.touches.length === 2 && pinchState[blockId]) {
    e.preventDefault()
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    const dist = Math.hypot(dx, dy)
    const ratio = dist / pinchState[blockId].dist
    sketchZoom.value[blockId] = Math.max(0.4, Math.min(3, +(pinchState[blockId].zoom * ratio).toFixed(2)))
  }
}
const onSketchTouchEnd = (blockId) => {
  delete pinchState[blockId]
}

const penCanvasRefs = {}
const penDrawingState = {}
const penModeActive = ref({})

const modalPenModeOn = computed(() => {
  return modalVisibleBlocks.value.some(b => penModeActive.value[b.id])
})
const toggleModalPenMode = () => {
  const next = !modalPenModeOn.value
  for (const b of modalVisibleBlocks.value) {
    if (b.sketch_image_url && (b.sketch_fields || []).some(f => f.field_type === 'pen')) {
      penModeActive.value[b.id] = next
    }
  }
}

const setPenCanvasRef = (blockId, fieldKey, el) => {
  const k = `${blockId}_${fieldKey}`
  penCanvasRefs[k] = el
  if (el) {
    nextTick(() => {
      const data = modalSketchFieldResponses.value[blockId]?.[fieldKey]
      if (data && typeof data === 'string' && data.startsWith('data:')) {
        const img = new Image()
        img.onload = () => { el.getContext('2d').drawImage(img, 0, 0) }
        img.src = data
      }
    })
  }
}

const penDown = (blockId, fieldKey, e) => {
  if (!canEdit.value || !penModeActive.value[blockId]) return
  const k = `${blockId}_${fieldKey}`
  const canvas = penCanvasRefs[k]
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = (e.clientX - rect.left) * (canvas.width / rect.width)
  const y = (e.clientY - rect.top) * (canvas.height / rect.height)
  penDrawingState[k] = true
  const ctx = canvas.getContext('2d')
  ctx.beginPath()
  ctx.moveTo(x, y)
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.strokeStyle = '#000'
  canvas.setPointerCapture(e.pointerId)
}

const penMove = (blockId, fieldKey, e) => {
  const k = `${blockId}_${fieldKey}`
  if (!penDrawingState[k]) return
  const canvas = penCanvasRefs[k]
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = (e.clientX - rect.left) * (canvas.width / rect.width)
  const y = (e.clientY - rect.top) * (canvas.height / rect.height)
  const ctx = canvas.getContext('2d')
  ctx.lineTo(x, y)
  ctx.stroke()
}

const penUp = (blockId, fieldKey, e) => {
  const k = `${blockId}_${fieldKey}`
  if (!penDrawingState[k]) return
  penDrawingState[k] = false
  const canvas = penCanvasRefs[k]
  if (!canvas) return
  setSketchFieldValue(blockId, fieldKey, canvas.toDataURL('image/png'))
}

const penClear = (blockId, fieldKey) => {
  const k = `${blockId}_${fieldKey}`
  const canvas = penCanvasRefs[k]
  if (!canvas) return
  canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height)
  setSketchFieldValue(blockId, fieldKey, null)
}

const getSketchPayloadForBlock = (unit, blockId, hold, holdReason = '') => {
  const existing = (unit?.sketch_responses || []).find((resp) => Number(resp.process_block) === Number(blockId))
  const drawingData = existing?.drawing_data && typeof existing.drawing_data === 'object' ? existing.drawing_data : {}
  const modalFieldValues = modalSketchFieldResponses.value[blockId] || {}
  const fieldResponses = { ...modalFieldValues }
  fieldResponses._hold = Boolean(hold)
  if (hold) {
    fieldResponses._hold_reason = String(holdReason || '').trim()
  } else {
    delete fieldResponses._hold_reason
  }
  return { drawing_data: drawingData, field_responses: fieldResponses }
}

const releaseHold = async (blockId) => {
  if (!modalUnit.value) return
  let releaseReason = ''
  while (!releaseReason) {
    const input = window.prompt('保留解除の理由を入力してください:')
    if (input === null) return
    releaseReason = String(input).trim()
    if (!releaseReason) alert('理由は必須です。')
  }
  try {
    const res = await api.integratedChecksheets.releaseHold(modalUnit.value.id, { process_block_id: blockId, release_reason: releaseReason })
    const updatedUnit = {
      ...res.data,
      sketch_responses: (modalUnit.value.sketch_responses || []).map((sr) => {
        if (Number(sr.process_block) !== Number(blockId)) return sr
        const fr = { ...sr.field_responses }
        delete fr._hold
        delete fr._hold_reason
        return { ...sr, field_responses: fr }
      }),
    }
    updateUnitInList(updatedUnit)
    modalUnit.value = updatedUnit
    if (activeBatch.value) await loadBatchUnits(activeBatch.value.id)
    const refreshed = units.value.find((u) => u.id === updatedUnit.id)
    if (refreshed) modalUnit.value = refreshed
  } catch (e) {
    alert(`保留解除に失敗しました: ${e.response?.data?.detail || e.message}`)
  }
}

// 工程ブロック単位で保存
const saveBlockChecks = async (block, options = {}) => {
  if (!canEdit.value) return
  if (!modalUnit.value) return
  const hold = Boolean(options.hold)
  let holdReason = ''

  const missingItems = block.items.filter((item) => {
    if (!item.is_required) return false
    const r = modalResponses.value[item.id]
    if (!r) return true
    if (item.record_type === 'CHECK') return !r.judgement
    if (item.record_type === 'NUMERIC_CHECK') return !r.judgement || r.numeric_value === null || r.numeric_value === '' || r.numeric_value === undefined
    if (isNumericRecordType(item.record_type)) return r.numeric_value === null || r.numeric_value === '' || r.numeric_value === undefined
    if (item.record_type === 'PHOTO') return !r.photo_url
    if (item.record_type === 'PHOTO_NUMERIC') return !r.photo_url || r.numeric_value === null || r.numeric_value === '' || r.numeric_value === undefined
    return !r.text_value
  })
  if (missingItems.length > 0) {
    const names = missingItems.map((i) => i.item_name).join('、')
    if (!hold) {
      alert(`${t('integratedOperation.alert.requiredMissing')}\n${names}\n\n${t('integratedOperation.alert.useHold')}`)
      return
    }
  }
  if (hold) {
    while (!holdReason) {
      const input = window.prompt(
        `${t('integratedOperation.alert.holdIncomplete')}\n${t('integratedOperation.alert.holdReasonRequired')}`,
        holdReason
      )
      if (input === null) return
      holdReason = String(input || '').trim()
      if (!holdReason) {
        alert(t('integratedOperation.alert.holdReasonMandatory'))
      }
    }
  }

  const savedUnitId = modalUnit.value.id
  savingBlock.value = block.id
  try {
    const checks = []
    for (const item of block.items) {
      const r = modalResponses.value[item.id]
      if (!r) continue
      const entry = { item: item.id }
      if (item.record_type === 'CHECK') {
        entry.judgement = r.judgement || ''
      } else if (item.record_type === 'NUMERIC_CHECK') {
        entry.numeric_value = r.numeric_value
        entry.judgement = r.judgement || ''
      } else if (isNumericRecordType(item.record_type)) {
        entry.numeric_value = r.numeric_value
        entry.judgement = r.judgement || ''
      } else if (item.record_type === 'PHOTO' || item.record_type === 'PHOTO_NUMERIC') {
        entry.photo_url = r.photo_url || ''
        if (item.record_type === 'PHOTO_NUMERIC') {
          entry.numeric_value = r.numeric_value
        }
      } else {
        entry.text_value = r.text_value || ''
      }
      checks.push(entry)
    }
    const sketchPayload = getSketchPayloadForBlock(modalUnit.value, block.id, hold, holdReason)
    if (isTestMode.value) {
      const currentChecks = Array.isArray(modalUnit.value.checks) ? [...modalUnit.value.checks] : []
      const nextChecks = currentChecks.filter((check) => !block.items.some((item) => Number(item.id) === Number(check.item)))
      nextChecks.push(...checks)
      const currentSketches = Array.isArray(modalUnit.value.sketch_responses) ? [...modalUnit.value.sketch_responses] : []
      const sketchIndex = currentSketches.findIndex((resp) => Number(resp.process_block) === Number(block.id))
      const sketchPatch = {
        ...(sketchIndex >= 0 ? currentSketches[sketchIndex] : {}),
        process_block: block.id,
        drawing_data: sketchPayload.drawing_data,
        field_responses: sketchPayload.field_responses,
      }
      if (sketchIndex >= 0) currentSketches[sketchIndex] = sketchPatch
      else currentSketches.push(sketchPatch)
      const nextStatus = buildLocalUnitStatus({
        ...modalUnit.value,
        checks: nextChecks,
        sketch_responses: currentSketches,
      })
      const updatedUnit = {
        ...modalUnit.value,
        checks: nextChecks,
        sketch_responses: currentSketches,
        status: nextStatus,
        completed_at: nextStatus === 'COMPLETED' ? (modalUnit.value.completed_at || new Date().toISOString()) : null,
        process_progress: buildUnitProcessProgress(nextChecks),
      }
      updateUnitInList(updatedUnit)
      modalUnit.value = updatedUnit
      refreshTestBatchState()
      const currentIdx = units.value.findIndex((u) => u.id === savedUnitId)
      if (currentIdx >= 0 && currentIdx + 1 < units.value.length) {
        const nextUnit = units.value[currentIdx + 1]
        if (nextUnit) openUnitModal(nextUnit, modalSelectedBlockId.value)
      }
      return
    }
    const res = await api.integratedChecksheets.saveChecks(modalUnit.value.id, {
      process_block_id: block.id,
      checks,
    })
    await api.integratedChecksheets.saveSketch(modalUnit.value.id, {
      process_block_id: block.id,
      drawing_data: sketchPayload.drawing_data,
      field_responses: sketchPayload.field_responses,
    })
    // モーダルのunitを更新
    const updatedUnit = {
      ...res.data,
      sketch_responses: Array.isArray(modalUnit.value?.sketch_responses)
        ? (() => {
            const next = [...modalUnit.value.sketch_responses]
            const idx = next.findIndex((resp) => Number(resp.process_block) === Number(block.id))
            const patch = {
              ...(idx >= 0 ? next[idx] : {}),
              process_block: block.id,
              drawing_data: sketchPayload.drawing_data,
              field_responses: sketchPayload.field_responses,
            }
            if (idx >= 0) next[idx] = patch
            else next.push(patch)
            return next
          })()
        : [{
            process_block: block.id,
            drawing_data: sketchPayload.drawing_data,
            field_responses: sketchPayload.field_responses,
          }],
    }
    updateUnitInList(updatedUnit)
    modalUnit.value = updatedUnit
    // バッチ一覧も更新
    loadBatches()

    // 保存成功後、自動で次の一台へ移動（末尾はそのまま）
    const currentIdx = units.value.findIndex((u) => u.id === savedUnitId)
    if (currentIdx >= 0 && currentIdx + 1 < units.value.length) {
      const nextUnit = units.value[currentIdx + 1]
      if (nextUnit) openUnitModal(nextUnit, modalSelectedBlockId.value)
    }
  } catch (error) {
    alert(`${t('integratedOperation.alert.saveFailed')}: ${error.response?.data?.detail || error.message}`)
  } finally {
    savingBlock.value = null
  }
}

const updateUnitInList = (updatedUnit) => {
  const idx = units.value.findIndex((u) => u.id === updatedUnit.id)
  if (idx >= 0) {
    units.value[idx] = updatedUnit
  }
}

// --- ウォッチ ---
watch([() => selectedLine.value, () => selectedProduct.value, () => batchStatusFilter.value], () => {
  loadBatches()
})

watch(() => selectedLine.value, async () => {
  await ensureLineFinalProducts(selectedLine.value)
  if (!filteredProductOptions.value.some((p) => String(p.id) === String(selectedProduct.value))) {
    selectedProduct.value = ''
  }
  if (!selectedProduct.value && filteredProductOptions.value.length === 1) {
    selectedProduct.value = filteredProductOptions.value[0].id
  }
})

watch(() => newBatch.line, async () => {
  await ensureLineFinalProducts(newBatch.line)
  if (!newBatchProductOptions.value.some((p) => String(p.id) === String(newBatch.product))) {
    newBatch.product = ''
  }
  if (!newBatch.product && newBatchProductOptions.value.length === 1) {
    newBatch.product = newBatchProductOptions.value[0].id
  }
})

// --- マウント ---
onMounted(async () => {
  if (!canView.value) return
  await loadMasters()
  if (isTestMode.value) {
    await loadTestTemplate()
    return
  }
  await applyInitialFiltersFromQuery()
  await loadBatches()
})
</script>

<style scoped>
.ics-operation {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: #111827;
  font-family: 'Meiryo', 'Yu Gothic UI', 'Yu Gothic', sans-serif;
  font-size: 14px;
}
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
.page-title-note { font-size: 12px; font-weight: 400; color: #2563eb; margin-left: 8px; }
.page-actions { display: flex; gap: 8px; }
.test-note { margin: 8px 0 0; font-size: 12px; color: #b45309; }

/* パネル */
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panel-title { margin: 0; font-size: 15px; font-weight: 700; color: #0f172a; }
.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.batch-meta { font-size: 13px; font-weight: 400; color: #6b7280; }

/* フィルタ */
.filter-panel {
  display: block;
}
.filter-form {
  justify-content: flex-start;
}
.filter-form label {
  margin: 0;
  width: auto;
  flex: 0 0 auto;
}
.filter-panel label,
.prepare-form label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}
.field-label {
  white-space: nowrap;
  min-width: 56px;
}
.filter-panel select,
.filter-panel input,
.prepare-form select,
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.prepare-form {
  display: flex;
  gap: 8px;
  align-items: end;
  flex-wrap: wrap;
}

.process-progress-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.process-progress-chip {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.4;
  background: #eef2f7;
  color: #334155;
  border: 1px solid #d7dee8;
}
.process-progress-chip.done {
  background: #16a34a;
  border-color: #15803d;
  color: #ffffff;
}
.required-mark { color: #dc2626; font-size: 12px; margin-left: 2px; }

/* テーブル */
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 5px 7px; border-bottom: 1px solid #edf1f5; text-align: left; }
.data-table th { background: #f7f9fb; font-size: 12px; font-weight: 700; white-space: nowrap; }
.data-table.compact th, .data-table.compact td { padding: 4px 6px; font-size: 13px; }
.row-selected { background: #eff6ff; }
.action-cell { display: flex; gap: 4px; }

/* ステータスチップ */
.status-chip {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid transparent;
  display: inline-block;
  white-space: nowrap;
}
.status-chip.mini { padding: 1px 5px; font-size: 10px; }
.status-chip.pending { background: #f3f4f6; border-color: #d1d5db; color: #6b7280; }
.status-chip.in-progress { background: #dbeafe; border-color: #93c5fd; color: #1d4ed8; }
.status-chip.completed { background: #d1fae5; border-color: #6ee7b7; color: #065f46; }
.status-chip.approved { background: #d1fae5; border-color: #34d399; color: #065f46; font-weight: 800; }

/* ボタン */
.btn-primary, .btn-secondary, .btn-sm {
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-delete-batch { background: #fff; color: #dc2626; border-color: #fca5a5; }
.btn-delete-batch:hover:not(:disabled) { background: #fef2f2; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-panel { background: #fff; border-radius: 8px; box-shadow: 0 20px 60px rgba(15,23,42,0.25); padding: 16px 20px; min-width: 320px; }
.modal-title { margin: 0 0 12px; font-size: 16px; font-weight: 700; }
.edit-batch-form { display: flex; flex-direction: column; gap: 10px; }
.edit-batch-form label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; font-weight: 500; color: #334155; }
.edit-batch-form input { padding: 5px 7px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; padding-top: 10px; border-top: 1px solid #e2e8f0; }
.btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { background: #93c5fd; border-color: #93c5fd; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #2563eb; border-color: #2563eb; }
.btn-secondary:hover { background: #eff6ff; }
.btn-close { background: none; border: none; font-size: 22px; cursor: pointer; color: #6b7280; padding: 0 4px; line-height: 1; }
.no-data { color: #6b7280; padding: 8px 0; font-size: 13px; }

/* マトリクス */
.matrix-panel { overflow: hidden; }
.matrix-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.matrix-header-actions { display: flex; gap: 6px; }
.matrix-scroll { overflow: auto; max-height: calc(100vh - 160px); border: 1px solid #dde2ea; border-radius: 4px; }
.matrix-table { border-collapse: collapse; }
.matrix-table th, .matrix-table td { padding: 3px 6px; border: 1px solid #e5e7eb; font-size: 12px; white-space: nowrap; }
.th-process { min-width: 60px; position: sticky; left: 30px; z-index: 2; background: #f7f9fb; }
.th-item { min-width: 140px; position: sticky; left: 90px; z-index: 2; background: #f7f9fb; }
.th-type { min-width: 28px; position: sticky; left: 230px; z-index: 2; background: #f7f9fb; text-align: center; }
.th-unit { min-width: 52px; text-align: center; cursor: pointer; }
.th-unit:hover { background: #dbeafe; }
.unit-header { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.unit-hold-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  color: #92400e;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}
.unit-sei-ban {
  display: block;
  font-size: 9px;
  color: #6b7280;
  white-space: nowrap;
  line-height: 1.2;
}
.sei-ban-label {
  margin-left: 12px;
  padding: 2px 8px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #1e40af;
}

.th-no { position: sticky; left: 0; z-index: 2; min-width: 30px; }
.td-no { position: sticky; left: 0; z-index: 1; background: #fff; font-size: 11px; color: #6b7280; text-align: center; min-width: 30px; }
.td-process { position: sticky; left: 30px; z-index: 1; background: #fff; font-size: 11px; color: #6b7280; }
.td-item { position: sticky; left: 90px; z-index: 1; background: #fff; max-width: 200px; white-space: pre-line; }
.td-type { position: sticky; left: 230px; z-index: 1; background: #fff; text-align: center; }
.td-cell { text-align: center; cursor: pointer; min-width: 52px; }
.td-cell:hover { background: #f0f4ff; }
.td-cell.cell-disabled-by-process {
  cursor: not-allowed;
  background: #f3f4f6;
  color: #9ca3af;
}
.td-cell.cell-disabled-by-process:hover { background: #f3f4f6; }

.item-standard { font-size: 10px; color: #9ca3af; display: block; white-space: pre-line; }

.type-tag { font-size: 10px; font-weight: 700; padding: 1px 4px; border-radius: 3px; }
.type-tag.type-CHECK { background: #dbeafe; color: #1d4ed8; }
.type-tag.type-NUMERIC { background: #fef3c7; color: #92400e; }
.type-tag.type-TEXT { background: #e0e7ff; color: #3730a3; }

/* マトリクス工程ヘッダー */
.block-header-row td { background: #1e293b; color: #fff; font-weight: 700; font-size: 13px; padding: 4px 8px; }
.block-header-cell {
  position: sticky;
  left: 0;
}
.block-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.block-title-left { display: inline-flex; align-items: center; gap: 6px; }
.block-title-right { font-size: 11px; color: #cbd5e1; font-weight: 600; }
.block-checker-cell {
  background: #1e293b;
  color: #cbd5e1;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  min-width: 52px;
  cursor: pointer;
}
.block-checker-cell .checker-date { display: block; font-size: 9px; opacity: 0.7; font-weight: 400; }
.block-checker-cell:hover { background: #334155; color: #ffffff; }
.block-checker-cell.cell-disabled-by-process {
  cursor: not-allowed;
  background: #334155;
  color: #94a3b8;
}
.block-checker-cell.cell-disabled-by-process:hover {
  background: #334155;
  color: #94a3b8;
}
.block-checker-cell.block-held { background: #78350f; }
.block-hold-mark {
  display: inline-block;
  background: #fbbf24;
  color: #78350f;
  font-size: 9px;
  font-weight: 700;
  padding: 0 4px;
  border-radius: 3px;
  margin-right: 3px;
  line-height: 1.4;
}
.sketch-badge { font-size: 10px; background: #fbbf24; color: #78350f; padding: 1px 6px; border-radius: 3px; margin-left: 6px; font-weight: 400; }

/* セル状態 */
.cell-locked { background: #f3f4f6; color: #d1d5db; }
.cell-empty { color: #d1d5db; }
.cell-ok { background: #ecfdf5; color: #059669; font-weight: 700; }
.cell-ng { background: #fef2f2; color: #dc2626; font-weight: 700; }
.cell-rework { background: #f5f3ff; color: #6d28d9; font-weight: 700; }
.cell-filled { background: #f0fdf4; color: #166534; }
.lock-icon { font-size: 12px; }

/* モーダル */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 8px;
  overflow-y: auto;
}
.modal-content {
  background: #fff;
  border-radius: 8px;
  width: calc(100vw - 16px);
  max-width: none;
  height: calc(100vh - 16px);
  height: calc(100dvh - 16px);
  max-height: calc(100vh - 16px);
  max-height: calc(100dvh - 16px);
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 30px rgba(0,0,0,0.2);
}
.modal-header {
  position: relative;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.modal-header h3 {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  font-size: 16px;
  white-space: nowrap;
}
.modal-header-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.modal-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
.modal-save-bar {
  position: sticky;
  bottom: 0;
  background: linear-gradient(to bottom, rgba(248, 250, 252, 0.75), #f8fafc 35%);
  padding: 10px 0 4px;
  margin-top: 8px;
}
.modal-save-bar-main {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.modal-unit-label {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-weight: 700;
  color: #0f172a;
  pointer-events: none;
}

@media (max-width: 1200px) {
  .modal-overlay { padding: 4px; }
  .modal-content {
    width: calc(100vw - 8px);
    height: calc(100vh - 8px);
    height: calc(100dvh - 8px);
    max-height: calc(100vh - 8px);
    max-height: calc(100dvh - 8px);
    border-radius: 6px;
  }
}

/* 工程セクション */
.process-section {
  margin-bottom: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}
.process-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #1e293b;
  color: #fff;
  font-size: 14px;
}
.process-section-header.locked { background: #9ca3af; }
.progress-text { font-size: 12px; font-weight: 400; color: #94a3b8; }
.lock-label { font-size: 11px; color: #fbbf24; margin-left: auto; }
.lock-label.hold-lock { color: #f87171; font-weight: 600; }
.btn-release-hold {
  margin-left: 8px;
  padding: 1px 8px;
  font-size: 11px;
  font-weight: 600;
  background: #fff;
  color: #dc2626;
  border: 1px solid #dc2626;
  border-radius: 4px;
  cursor: pointer;
}
.btn-release-hold:hover { background: #fef2f2; }

/* 略図 */
.sketch-placeholder {
  position: relative;
  border-bottom: 1px solid #e5e7eb;
  max-height: 340px;
  overflow: hidden;
}
.sketch-img { width: 100%; height: auto; display: block; }
.sketch-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.35);
  font-size: 44px;
  color: #1f2937;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-align: center;
  line-height: 1.2;
  z-index: 1;
}
.sketch-overlay::before {
  content: '';
  position: absolute;
  width: min(92%, 720px);
  height: 112px;
  background: rgba(255, 255, 255, 0.88);
  border: 2px solid rgba(107, 114, 128, 0.35);
  border-radius: 999px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.sketch-overlay span {
  position: relative;
  z-index: 2;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.75);
}

/* チェック項目リスト */
.items-list { padding: 6px 10px; }
.item-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid #f3f4f6;
}
.item-row:last-child { border-bottom: none; }
.item-row.item-optional { background: #dcfce7; }
.item-label-area { flex: 1; min-width: 0; }
.item-no { font-size: 12px; color: #6b7280; min-width: 20px; text-align: center; flex-shrink: 0; }
.item-name { font-size: 13px; font-weight: 500; white-space: pre-line; }
.item-hint { font-size: 11px; color: #9ca3af; margin-left: 4px; white-space: pre-line; }
.item-input-area { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

/* OK/NGボタン */
.judge-btn {
  padding: 4px 14px;
  border-radius: 4px;
  border: 2px solid #d1d5db;
  background: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.judge-btn.ok { color: #059669; border-color: #a7f3d0; }
.judge-btn.ok.active { background: #059669; color: #fff; border-color: #059669; }
.judge-btn.ng { color: #dc2626; border-color: #fca5a5; }
.judge-btn.ng.active { background: #dc2626; color: #fff; border-color: #dc2626; }
.judge-btn.rework { color: #7c3aed; border-color: #c4b5fd; }
.judge-btn.rework.active { background: #7c3aed; color: #fff; border-color: #7c3aed; }
.btn-hold { border-color: #d97706; color: #b45309; }

/* 数値・テキスト入力 */
.numeric-input, .text-input {
  padding: 4px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  width: 100px;
}
.text-input { width: 140px; }
.text-area { resize: vertical; min-height: 32px; width: 400px; font-family: inherit; line-height: 1.5; }
.unit-label { font-size: 12px; color: #6b7280; }
.numeric-input.numeric-ok { border-color: #059669; background: #ecfdf5; }
.numeric-input.numeric-ng { border-color: #dc2626; background: #fef2f2; }
.numeric-check-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sketch-container { border-bottom: 1px solid #e5e7eb; overflow: auto; touch-action: pan-x pan-y; }
.sketch-zoom-bar { position: sticky; top: 0; left: 0; z-index: 3; display: flex; align-items: center; gap: 4px; padding: 2px 6px; background: rgba(248,250,252,0.9); }
.btn-zoom { padding: 1px 8px; font-size: 14px; border: 1px solid #cbd5e1; border-radius: 3px; background: #fff; cursor: pointer; }
.zoom-label { font-size: 12px; color: #64748b; min-width: 40px; text-align: center; }
.sketch-inner { position: relative; display: inline-block; width: 100%; }
.sketch-field-overlay { box-sizing: border-box; overflow: hidden; }
.sketch-overlay-btn { width: 100%; height: 100%; border: 1px solid #94a3b8; background: rgba(255,255,255,0.7); font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.sketch-overlay-btn.checked { background: rgba(209,250,229,0.8); color: #065f46; font-weight: 700; }
.sketch-overlay-input { width: 100%; height: 100%; box-sizing: border-box; border: 1px solid #94a3b8; background: rgba(255,255,255,0.7); font-size: 11px; padding: 1px 3px; }
.pen-canvas-overlay { width: 100%; height: 100%; touch-action: none; cursor: crosshair; background: rgba(255,255,255,0.01); border: 1px solid #94a3b8; box-sizing: border-box; }
.pen-canvas-overlay.pen-inactive { pointer-events: none; touch-action: auto; cursor: default; }
.btn-sketch-toggle { margin-left: 8px; padding: 1px 8px; font-size: 11px; border: 1px solid rgba(255,255,255,0.4); border-radius: 3px; background: transparent; color: #cbd5e1; cursor: pointer; }
.btn-pen-mode-toggle { margin-right: auto; padding: 4px 12px; font-size: 13px; border: 2px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; white-space: nowrap; }
.btn-pen-mode-toggle.active { background: #fef3c7; border-color: #f59e0b; color: #92400e; }
.btn-pen-clear-overlay { position: absolute; top: 0; right: 0; font-size: 10px; padding: 0 3px; background: rgba(255,255,255,0.8); color: #dc2626; border: none; cursor: pointer; line-height: 1.4; }
.auto-judge-badge { font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
.auto-judge-badge.ok { background: #d1fae5; color: #065f46; }
.auto-judge-badge.ng { background: #fee2e2; color: #991b1b; }

/* ロック中メッセージ */
.hold-reason-display {
  padding: 8px 16px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 6px;
  color: #92400e;
  font-size: 13px;
  display: inline-block;
}
.locked-message {
  padding: 12px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  background: #f9fafb;
}
.btn-attachment-ref {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid #3b82f6;
  border-radius: 4px;
  background: #eff6ff;
  color: #2563eb;
  cursor: pointer;
  white-space: nowrap;
  margin-left: 4px;
}
.btn-attachment-ref:hover { background: #dbeafe; }
.btn-attachment-sm { font-size: 10px; padding: 0 4px; }
.att-backdrop { z-index: 200; }
.att-modal-panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(15,23,42,.25);
  max-width: 600px;
  width: 95%;
  max-height: 85vh;
  overflow-y: auto;
}
.att-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
}
.att-modal-title { font-size: 16px; font-weight: 700; margin: 0; }
.att-modal-item-name { font-size: 12px; color: #64748b; margin-top: 2px; }
.att-list { padding: 12px 16px; }
.att-card {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 10px;
}
.att-card-title { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.att-image-wrap { margin-bottom: 8px; }
.att-image-wrap img { max-width: 100%; max-height: 300px; border: 1px solid #cbd5e1; object-fit: contain; }
.att-text { font-size: 12px; margin-bottom: 3px; line-height: 1.4; }
.photo-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.photo-upload-btn {
  display: inline-block;
  padding: 4px 12px;
  font-size: 13px;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  background: #eff6ff;
  color: #2563eb;
  cursor: pointer;
}
.photo-upload-btn:hover { background: #dbeafe; }
.photo-upload-btn.disabled { opacity: .5; pointer-events: none; }
.photo-preview-mini img {
  height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  cursor: pointer;
  object-fit: cover;
}
.photo-ok-badge {
  font-size: 11px;
  font-weight: 700;
  color: #16a34a;
}
.photo-numeric-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

/* ビューモード（完了済み工程） */
.items-list.view-only { pointer-events: none; opacity: 0.75; }
.view-only-header { background: #064e3b; }

/* 刻印番号 履歴照会 */
.history-unit-card { margin-bottom: 12px; border: 1px solid #e2e8f0; border-radius: 4px; overflow: hidden; }
.history-unit-header { background: #1e293b; color: #e2e8f0; padding: 6px 10px; font-size: 12px; display: flex; gap: 12px; align-items: center; }
.history-sei-ban { font-weight: 700; font-size: 13px; color: #38bdf8; }
.history-meta { opacity: 0.85; }
.history-table { margin: 0; }
.history-table th { font-size: 11px; padding: 3px 6px; }
.history-table td { font-size: 11px; padding: 2px 6px; }
.history-process-header td { background: #f1f5f9; font-size: 12px; padding: 4px 8px; }
.history-hold-badge { font-size: 10px; margin-left: 8px; padding: 1px 6px; border-radius: 3px; }
.history-hold-badge.held { background: #fef3c7; color: #92400e; }
.history-hold-badge.released { background: #d1fae5; color: #065f46; }
.history-ok { color: #16a34a; font-weight: 600; }
.history-ng { color: #dc2626; font-weight: 600; }
.history-rework { color: #d97706; font-weight: 600; }

</style>
