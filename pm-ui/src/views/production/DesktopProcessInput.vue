<template>
  <div class="desktop-process-input" :class="[pageModeClass, { 'embed-tablet': isEmbeddedTablet, 'compact-form-tablet': isCompactFormTablet, 'show-recent': showRecentPanel }]">
    <!-- ヘッダー -->
    <div class="header" :class="{ 'header-embed': isEmbeddedTablet }">
      <template v-if="!isEmbeddedTablet">
        <h2 class="page-title">工程作業記録 <DataSourceDialog title="工程作業記録（デスクトップ）" :sources="dsSources" /></h2>
      </template>
      <button :class="isEmbeddedTablet ? 'embed-icon-btn' : 'btn-checksheet-nav'" @click="openIntegratedChecksheetOperation" :title="isEmbeddedTablet ? 'チェックシート' : ''">
        <template v-if="isEmbeddedTablet"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/><polyline points="-2 8 5 17 18 -4" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg></template>
        <template v-else>チェックシート</template>
      </button>
      <button :class="isEmbeddedTablet ? 'embed-icon-btn' : 'btn-inspection-nav'" @click="openEquipmentInspection" :title="isEmbeddedTablet ? '設備点検' : ''">
        <template v-if="isEmbeddedTablet"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/><polyline points="1 6 6 13 15 -5" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></template>
        <template v-else>設備点検</template>
      </button>
      <template v-if="isEmbeddedTablet">
        <div class="embed-separator"></div>
        <button
          v-for="type in availableRecordTypes"
          :key="type.value"
          class="embed-icon-btn"
          :class="{ active: record.record_type === type.value }"
          @click="record.record_type = type.value"
          :title="type.label"
        >
          <svg v-if="type.value === 'EQUIPMENT_STATE'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="2 2 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="15" rx="2" ry="2"/><polyline points="17 2 12 7 7 2"/><line x1="6" y1="12" x2="11" y2="12" stroke="#22c55e" stroke-width="2.5"/><line x1="6" y1="15" x2="11" y2="15" stroke="#eab308" stroke-width="2.5"/><line x1="6" y1="18" x2="11" y2="18" stroke="#ef4444" stroke-width="2.5"/><path d="M18 9 l3 3 -8 8 -3 0 0 -3 8 -8z" stroke="currentColor" stroke-width="0.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <svg v-else-if="type.value === 'PRODUCTION'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
        </button>
        <div class="embed-separator"></div>
        <button class="embed-icon-btn" :class="{ active: showDone }" @click="showDone = !showDone" title="加工済">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="7 12 10 15 17 9"/></svg>
        </button>
        <button class="embed-icon-btn" :class="{ active: showYesterday }" @click="showYesterday = !showYesterday; onYesterdayToggle()" title="前日表示">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><text x="13" y="21" font-family="'Segoe UI', Arial, sans-serif" font-size="10.5" font-weight="900" fill="currentColor" stroke="none">-1</text></svg>
        </button>
        <button class="embed-icon-btn" :class="{ active: showTomorrow }" @click="showTomorrow = !showTomorrow; onTomorrowToggle()" title="明日計画">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><text x="13" y="21" font-family="'Segoe UI', Arial, sans-serif" font-size="10.5" font-weight="900" fill="currentColor" stroke="none">+1</text></svg>
        </button>
        <button class="embed-icon-btn" :class="{ active: filterCurrentTime }" @click="filterCurrentTime = !filterCurrentTime; onCurrentTimeToggle()" :disabled="isPlannedProductsLoading" title="現在時刻のみ">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </button>
        <div class="embed-separator"></div>
        <button class="btn-recent-toggle" :class="{ active: showRecentPanel }" @click="showRecentPanel = !showRecentPanel" title="最近の記録">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
        </button>
        <div v-if="selectedProcessId && headerProcessTargetLabel" class="header-target-chip embed-target-chip" :title="headerProcessTargetLabel">
          <span>{{ headerProcessTargetLabel }}</span>
        </div>
      </template>
      <template v-if="!isEmbeddedTablet">
        <div class="header-controls">
          <label class="header-label">ライン</label>
          <div class="line-select-wrapper">
            <select v-model="selectedLineId" @change="onLineChange" class="process-select">
              <option value="">-- ライン選択 --</option>
              <option v-for="line in availableLines" :key="line.id" :value="String(line.id)">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
            <button
              v-if="showSupportToggle"
              type="button"
              class="support-toggle-btn"
              :class="{ active: isSupportMode }"
              @click="toggleSupportMode"
            >{{ isSupportMode ? '応援ON' : '応援OFF' }}</button>
          </div>
          <label class="header-label">工程</label>
          <select v-model="selectedProcessId" @change="onProcessChange" class="process-select" :disabled="!selectedLineId">
            <option value="">-- 工程選択 --</option>
            <option v-for="p in filteredProcesses" :key="p.id" :value="p.id">
              {{ p.process_code }} - {{ p.process_name }}
            </option>
          </select>
          <span class="date-display">{{ currentDate }}</span>
          <div
            v-if="selectedProcessId && currentProcessingLabel"
            class="header-processing clickable"
            @click="jumpToProcessingProduct"
          >
            <span class="processing-chip">{{ currentProcessingLabel }}</span>
          </div>
          <div
            v-else-if="selectedProcessId && pauseNoticeLabel"
            class="header-processing pause"
          >
            <span class="processing-chip">{{ pauseNoticeLabel }}</span>
          </div>
          <div v-else class="header-processing empty">加工中なし</div>
          <div v-if="selectedProcessId && headerProcessTargetLabel" class="header-target-chip">
            <span>{{ headerProcessTargetLabel }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- 4列レイアウト -->
    <div class="four-col-layout">

      <!-- 列①: コントロール -->
      <div v-if="!isEmbeddedTablet" class="col-controls">
        <div class="section-title">記録種別</div>
        <div class="record-type-area">
          <button
            v-for="type in availableRecordTypes"
            :key="type.value"
            class="record-type-btn"
            :class="{ active: record.record_type === type.value }"
            @click="record.record_type = type.value"
          >{{ type.label }}</button>
        </div>

        <div class="section-title" style="margin-top:12px">表示設定</div>
        <div class="filter-area">
          <label class="filter-item">
            <span class="toggle-label">加工済</span>
            <input type="checkbox" v-model="showDone" class="toggle-input" />
            <span class="toggle-track" :class="{ on: showDone }"></span>
          </label>
          <label class="filter-item filter-item-reverse">
            <input type="checkbox" v-model="showTomorrow" class="toggle-input" @change="onTomorrowToggle" />
            <span class="toggle-track" :class="{ on: showTomorrow }"></span>
            <span class="toggle-label">明日計画</span>
          </label>
          <label class="filter-item">
            <span class="toggle-label">前日表示</span>
            <input type="checkbox" v-model="showYesterday" class="toggle-input" @change="onYesterdayToggle" />
            <span class="toggle-track" :class="{ on: showYesterday }"></span>
          </label>
          <label class="filter-item filter-item-reverse">
            <input type="checkbox" v-model="filterCurrentTime" class="toggle-input" @change="onCurrentTimeToggle" :disabled="isPlannedProductsLoading" />
            <span class="toggle-track" :class="{ on: filterCurrentTime }"></span>
            <span class="toggle-label">現在時刻のみ</span>
          </label>
        </div>
        <div v-if="timeSlots.length" class="slot-nav">
          <button class="slot-btn" :disabled="!canPrevSlot" @click="goPrevSlot">«</button>
          <span class="slot-label-text">{{ plannedTimeLabel }}</span>
          <button class="slot-btn" :disabled="!canNextSlot" @click="goNextSlot">»</button>
        </div>

        <div class="section-title" style="margin-top:12px">作業者</div>
        <div class="operator-area">
          <input type="text" v-model="record.operator_name" class="operator-input" placeholder="作業者名を入力" />
        </div>

        <template v-if="isScrapRecord">
          <div class="section-title" style="margin-top:12px">仕損フィルタ</div>
          <div class="scrap-filter-controls">
            <select v-model="scrapRelationFilter" class="scrap-filter-select">
              <option value="">{{ t('processInput.scrapFilter.all') }}</option>
              <option v-for="opt in scrapRelationOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
            <input
              v-model="scrapSearchText"
              type="text"
              class="scrap-filter-input"
              :placeholder="t('processInput.scrapSearch.placeholder')"
            />
          </div>
        </template>

        <template v-if="record.record_type === 'EQUIPMENT_STATE'">
          <div class="section-title" style="margin-top:12px">設備状態</div>
          <div class="equip-state-btns">
            <button
              v-for="state in equipmentStates"
              :key="state.value"
              class="equip-state-btn"
              :class="[{ active: record.equipment_state === state.value }, `state-${state.value.toLowerCase()}`]"
              @click="setEquipmentState(state.value)"
            >{{ state.label }}</button>
          </div>
        </template>
      </div>

      <!-- 列②: 製品リスト -->
      <div class="col-list">
        <div class="list-header">
          <span class="list-count">{{ filteredListItems.length }}件</span>
          <input
            v-model.trim="productCodeFilter"
            class="list-filter-input"
            :placeholder="t('processInput.productCodeSearchPlaceholder')"
            @input="currentPage = 1"
          />
        </div>
        <div v-if="twoPersonScopeWarning" class="scope-warning">{{ twoPersonScopeWarning }}</div>

        <div class="plan-list" v-if="!isPlannedProductsLoading">
          <div
            v-for="(item, idx) in pagedItems"
            :key="`${item.plan_date}-${item.product}-${item.process}-${item.sequence_no || ''}`"
            class="plan-item"
            :class="{
              selected: String(record.product_id) === String(item.product) && (!selectedGanttPlanId || selectedGanttPlanId === (item.gantt_plan_id || '')),
              'current-processing': isCurrentProcessingProduct(item.product),
              'temp-ended': isTempEndedProduct(item.product),
              'plan-edited': editedPlanIds.has(item.gantt_plan_id),
            }"
            @click="selectPlannedProduct(item)"
          >
            <div class="item-grid">
              <div class="item-code">{{ getDisplayProductCode(item) }}</div>
              <div class="item-plan">計{{ formatNumber(toSafeNumber(item.plan_qty)) }}</div>
              <div class="item-sub">{{ item.product_name || '' }}</div>
              <div class="item-actual" :class="{ over: getPlanQtyState(item) === 'over', done: getPlanQtyState(item) === 'done' }">実{{ formatNumber(toSafeNumber(item.actual_qty)) }}</div>
            </div>
            <span v-if="isTempEndedProduct(item.product)" class="status-badge temp-end">
              {{ t('processInput.tempEndBadge') }}
            </span>
          </div>
          <div v-if="filteredListItems.length === 0 && !manualProduct" class="empty-list">
            対象品番がありません
          </div>
        </div>
        <div class="plan-list loading-list" v-else>
          <div class="loading-text">読み込み中...</div>
        </div>

        <div v-if="!filterCurrentTime" class="pagination">
          <button class="page-btn" @click="goFirstPage" :disabled="currentPage === 1">⟨⟨</button>
          <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">⟨</button>
          <span class="page-info">{{ pageStart }}-{{ pageEnd }}/{{ filteredListItems.length }}</span>
          <button class="page-btn" @click="nextPage" :disabled="currentPage >= totalPages">⟩</button>
          <button class="page-btn" @click="goLastPage" :disabled="currentPage >= totalPages">⟩⟩</button>
        </div>

        <div v-if="record.record_type === 'PRODUCTION' || record.record_type === 'SCRAP'" class="manual-toggle-area">
          <button
            v-if="isEmbeddedTablet && filterCurrentTime && timeSlots.length > 1"
            type="button"
            class="btn-manual-nav"
            :disabled="!canPrevSlot"
            @click="goPrevSlot"
          >«</button>
          <button type="button" class="btn-link" @click="toggleManualProduct">
            {{ manualProduct ? t('processInput.backToSearch') : t('processInput.manualInput') }}
          </button>
          <button
            v-if="isEmbeddedTablet && filterCurrentTime && timeSlots.length > 1"
            type="button"
            class="btn-manual-nav"
            :disabled="!canNextSlot"
            @click="goNextSlot"
          >»</button>
        </div>
        <div v-if="isEmbeddedTablet && filterCurrentTime && plannedTimeLabel" class="planned-time-inline">
          予定加工時間: {{ plannedTimeLabel }}
        </div>
      </div>

      <!-- 列③: 登録フォーム -->
      <div class="col-form">
        <template v-if="record.record_type === 'EQUIPMENT_STATE'">
          <div class="form-area">
            <div class="product-header">
              <div class="product-code-large">{{ t('processInput.equipmentStateTitle') }}</div>
            </div>
            <div class="equip-form-section">
              <label class="equip-label">{{ t('processInput.state') }} <span class="required-mark">*</span></label>
              <div class="equip-state-grid">
                <button
                  v-for="state in equipmentStates"
                  :key="state.value"
                  class="equip-state-btn"
                  :class="[{ active: record.equipment_state === state.value }, `state-${state.value.toLowerCase()}`]"
                  @click="setEquipmentState(state.value)"
                >{{ state.label }}</button>
              </div>
            </div>
            <div class="reason-area">
              <label class="qty-label">{{ t('processInput.remarks') }}</label>
              <textarea
                v-model="record.remarks"
                rows="3"
                :placeholder="t('processInput.stateRemarksPlaceholder')"
                class="textarea-normal"
              ></textarea>
            </div>
            <div class="action-bar">
              <button class="btn-save" :disabled="!canSubmit || submitting" @click="submitRecord">
                {{ submitting ? t('processInput.submitting') : t('processInput.submit') }}
              </button>
            </div>
          </div>
        </template>

        <template v-else-if="!record.product_id">
          <div class="no-selection"><span>品番を選択してください</span></div>
        </template>

        <template v-else>
          <div class="form-area" :class="formModeClass">
            <div class="product-header">
              <div class="product-code-row">
                <div class="product-code-large">{{ selectedProductCode }}</div>
                <button
                  type="button"
                  class="product-photo-trigger product-photo-view-trigger"
                  :class="{ disabled: !canOpenProductPhotoDialog }"
                  :disabled="!canOpenProductPhotoDialog"
                  @click="openProductPhotoDialog('view')"
                  title="製品写真を表示"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
                <button
                  type="button"
                  class="product-photo-trigger"
                  :class="{ disabled: !canCaptureProductPhoto }"
                  :disabled="!canCaptureProductPhoto"
                  @click="openProductPhotoDialog('capture')"
                  title="製品写真を撮影"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14.5 4h-5L7.5 6H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2.5z"/>
                    <circle cx="12" cy="13" r="3.5"/>
                  </svg>
                </button>
              </div>
              <div class="product-name">{{ selectedProductName }}</div>
              <div v-if="selectedProductTimeLabel" class="product-time-label">{{ selectedProductTimeLabel }}</div>
            </div>

            <!-- オペレータアクション -->
            <div v-if="shouldShowOperatorActionRow" class="action-btns-section">
              <label class="equip-label">{{ isCompactFormTablet ? 'AC' : 'アクション' }} <span class="required-mark">*</span></label>
              <div v-if="shouldShowAutoStartAction" class="op-action-btns">
                <button type="button" class="op-action-btn action-start active" disabled>
                  {{ t(OPERATOR_ACTION_LABEL_KEYS.START) }}
                </button>
              </div>
              <div v-if="shouldShowOperatorActionSelector" class="op-action-btns">
                <button
                  v-for="action in operatorActionOptions"
                  :key="action.value"
                  type="button"
                  class="op-action-btn"
                  :class="[`action-${action.value.toLowerCase()}`, { active: isOperatorActionActive(action.value) }]"
                  @click="selectOperatorAction(action.value)"
                >{{ action.label }}</button>
                <span v-if="shouldUseCounterInput" class="op-action-note">
                  {{ t('processInput.counterQtyFormula', { actualQty: formatNumber(counterBaseQty) }) }}
                </span>
              </div>
            </div>

            <!-- 計画サマリ -->
            <div v-if="planStatus" class="stats-and-actions">
              <div class="current-actual">
                <div class="stat-block">
                  <span class="stat-label">{{ t('processInput.planQtyLabel') }}</span>
                  <span v-if="!editingPlanQty" class="stat-value plan clickable" @click="startEditPlanQty">{{ formatNumber(planStatus.planQty) }}</span>
                  <span v-else class="plan-qty-edit">
                    <input v-model.number="editPlanQtyValue" type="number" min="0" class="plan-qty-input" @keyup.escape="cancelEditPlanQty" />
                    <input v-if="!selectedPlanItem?.gantt_plan_id" v-model="editPlanStartTime" type="time" step="60" class="plan-time-input" />
                    <input v-if="!selectedPlanItem?.gantt_plan_id" v-model="editPlanEndTime" type="time" step="60" class="plan-time-input" />
                    <button class="plan-qty-btn save" @click="savePlanQty">保存</button>
                    <button class="plan-qty-btn cancel" @click="cancelEditPlanQty">取消</button>
                  </span>
                </div>
                <div class="stat-block">
                  <span class="stat-label">{{ t('processInput.recordedQty') }}</span>
                  <span class="stat-value actual">{{ formatNumber(planStatus.actualQty) }}</span>
                </div>
                <div class="stat-block">
                  <span class="stat-label">{{ t('processInput.remainingQty') }}</span>
                  <span class="stat-value remain" :class="{ over: planStatus.remaining <= 0 }">
                    {{ formatNumber(planStatus.remaining) }}
                  </span>
                </div>
                <div v-if="shouldShowQtyInput && record.qty" class="stat-block">
                  <span class="stat-label">{{ t('processInput.remainingAfterEntry') }}</span>
                  <span class="stat-value remain">{{ formatNumber(planStatus.remainingAfterInput) }}</span>
                </div>
              </div>
            </div>

            <!-- 数量入力 -->
            <div v-if="shouldShowQtyInput" class="qty-input-area">
              <div class="qty-row">
                <div v-if="shouldUseCounterInput" class="qty-col">
                  <label class="qty-label">
                    {{ t('processInput.counterQty') }}
                    <span class="required-mark">*</span>
                  </label>
                  <input
                    type="number"
                    v-model.number="record.counter_qty"
                    :min="counterBaseQty"
                    step="1"
                    inputmode="numeric"
                    class="qty-input"
                    :placeholder="t('processInput.counterQtyPlaceholder')"
                  />
                  <div v-if="counterQtyError" class="hint-text text-danger">{{ counterQtyError }}</div>
                </div>
                <div class="qty-col">
                  <label class="qty-label">
                    {{ record.record_type === 'SCRAP' ? t('processInput.scrapQty') : t('processInput.productionQty') }}
                    <span class="required-mark">*</span>
                  </label>
                  <input
                    ref="qtyInputRef"
                    type="number"
                    v-model.number="record.qty"
                    :min="qtyInputMin"
                    step="1"
                    inputmode="numeric"
                    class="qty-input"
                    :placeholder="t('processInput.qtyPlaceholder')"
                    :readonly="shouldUseCounterInput"
                  />
                </div>
                <div class="qty-col">
                  <label class="qty-label">{{ t('processInput.batchNo') }}</label>
                  <input
                    type="text"
                    v-model="record.batch_no"
                    :placeholder="t('processInput.batchNoPlaceholder')"
                    class="batch-input"
                  />
                </div>
                <div v-if="isCompactFormTablet" class="qty-col">
                  <label class="qty-label">作業日 <span class="required-mark">*</span></label>
                  <input type="date" v-model="workDateStr" class="work-date-input" />
                </div>
              </div>
            </div>

            <!-- クイック数量 -->
            <div v-if="shouldShowQtyInput && !shouldUseCounterInput && quickQtyPresets.length" class="quick-btns">
              <button
                v-for="preset in quickQtyPresets"
                :key="preset"
                class="btn-quick"
                @click="record.qty = preset"
              >{{ preset }}</button>
            </div>

            <!-- 中断/強制終了理由 -->
            <div v-if="requiresOperatorActionReason" class="reason-area">
              <label class="qty-label">
                {{ t(operatorActionReasonLabelKey) }}
                <span class="required-mark">*</span>
              </label>
              <select
                v-if="isPauseReasonDropdown"
                v-model="record.operator_action_reason"
                class="reason-select"
              >
                <option value="">{{ t('processInput.pauseReasonSelectPlaceholder') }}</option>
                <option v-for="reason in pauseReasons" :key="reason.value" :value="reason.value">{{ reason.label }}</option>
              </select>
              <select
                v-else-if="isTempEndReasonDropdown"
                v-model="record.operator_action_reason"
                class="reason-select"
              >
                <option value="">{{ t('processInput.tempEndReasonSelectPlaceholder') }}</option>
                <option v-for="reason in tempEndReasons" :key="reason.value" :value="reason.value">{{ reason.label }}</option>
              </select>
              <input
                v-else
                type="text"
                v-model="record.operator_action_reason"
                :placeholder="t(operatorActionReasonPlaceholderKey)"
                class="reason-input"
              />
            </div>

            <!-- 仕損フィールド -->
            <template v-if="isScrapRecord">
              <div class="scrap-fields">
                <div class="scrap-field-row">
                  <div class="scrap-field">
                    <label class="qty-label">{{ t('processInput.disposition') }} <span class="required-mark">*</span></label>
                    <select v-model="record.disposition_status" class="reason-select">
                      <option value="">{{ t('processInput.selectDisposition') }}</option>
                      <option v-for="opt in scrapDispositionOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    </select>
                  </div>
                  <div class="scrap-field">
                    <label class="qty-label">{{ t('processInput.productionRecorded') }} <span class="required-mark">*</span></label>
                    <select v-model="record.is_production_recorded" class="reason-select">
                      <option value="">-- 選択 --</option>
                      <option v-for="opt in productionRecordedOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    </select>
                  </div>
                </div>
                <div class="scrap-field">
                  <label class="qty-label">{{ t('processInput.reason') }} <span class="required-mark">*</span></label>
                  <select v-model="record.reason" class="reason-select">
                    <option value="">{{ t('processInput.selectReason') }}</option>
                    <option v-for="reason in scrapReasons" :key="reason.value" :value="reason.value">{{ reason.label }}</option>
                  </select>
                </div>
                <div v-if="record.reason === 'OTHER'" class="scrap-field">
                  <label class="qty-label">{{ t('processInput.reasonDetail') }} <span class="required-mark">*</span></label>
                  <input type="text" v-model="record.reason_detail" :placeholder="t('processInput.reasonDetailPlaceholder')" class="reason-input" />
                </div>
              </div>
            </template>

            <!-- 連産品通知 -->
            <div
              v-if="record.record_type === 'PRODUCTION' && (selectedCoproductNoticeLoading || selectedCoproductChildren.length)"
              class="coproduct-notice"
              :class="{ 'coproduct-collapsed': isCompactFormTablet && !coproductExpanded }"
            >
              <div v-if="selectedCoproductNoticeLoading" class="coproduct-notice-loading">読み込み中...</div>
              <template v-else>
                <div class="coproduct-notice-title" :class="{ 'coproduct-toggle': isCompactFormTablet }" @click="isCompactFormTablet && (coproductExpanded = !coproductExpanded)">
                  <template v-if="isCompactFormTablet">連産品 {{ selectedCoproductChildren.length }}件 {{ coproductExpanded ? '▲' : '▼' }}</template>
                  <template v-else>{{ t('processInput.coproductNotice.message', { code: selectedCoproductParentCode || record.product_code || '' }) }}</template>
                </div>
                <div v-if="!isCompactFormTablet || coproductExpanded" class="coproduct-notice-children">
                  <span v-for="child in selectedCoproductChildren" :key="child.product_id" class="coproduct-chip">
                    {{ child.product_code }}
                    <span v-if="child.product_name" class="coproduct-chip-name">{{ child.product_name }}</span>
                  </span>
                </div>
              </template>
            </div>

            <!-- 備考 -->
            <div class="reason-area">
              <label :class="{ 'qty-label': true, 'label-required-after': requiresTempEndOtherRemarks }">
                {{ t('processInput.remarks') }}
              </label>
              <textarea
                v-model="record.remarks"
                rows="2"
                :placeholder="t('processInput.remarksPlaceholder')"
                class="textarea-normal"
              ></textarea>
              <div v-if="requiresTempEndOtherRemarks" class="hint-text">
                {{ t('processInput.tempEndRemarksRequiredHint') }}
              </div>
            </div>

            <div v-if="!isCompactFormTablet" class="work-date-area">
              <label class="qty-label">作業日 <span class="required-mark">*</span></label>
              <input type="date" v-model="workDateStr" class="work-date-input" />
              <div class="work-date-hint">上部の日付は表示用です。保存は作業日で行います。</div>
            </div>
            <div v-if="isWorkDateChanged" class="reason-area">
              <label class="qty-label">作業日変更理由 <span class="required-mark">*</span></label>
              <select v-model="workDateChangeReason" class="reason-select">
                <option value="">-- 選択 --</option>
                <option value="入力忘れ">入力忘れ</option>
                <option value="先行生産">先行生産</option>
                <option value="OTHER">その他</option>
              </select>
              <input v-if="workDateChangeReason === 'OTHER'" type="text" v-model="workDateChangeReasonDetail" placeholder="理由を入力" class="reason-input" style="margin-top: 4px;" />
            </div>

            <div class="action-bar">
              <button class="btn-save" :disabled="!canSubmit || submitting" @click="submitRecord">
                {{ submitting ? t('processInput.submitting') : t('processInput.submit') }}
              </button>
              <button class="btn-cancel" @click="cancelSelection">キャンセル</button>
            </div>
          </div>
        </template>
      </div>

      <!-- 列④: 最近の実績 -->
      <div v-show="!isEmbeddedTablet || showRecentPanel" class="col-recent">
        <div class="section-title">最近の記録</div>
        <div v-if="recentRecordsForDisplay.length" class="recent-list">
          <div
            v-for="rec in recentRecordsForDisplay"
            :key="rec.id"
            class="recent-item"
            :style="getRecentRecordColorStyle(rec)"
          >
            <div class="recent-row1">
              <span class="recent-date">{{ formatShortDate(rec.timestamp) }}</span>
              <span class="recent-clock">{{ formatTime(rec.timestamp) }}</span>
              <span class="recent-qty" v-if="rec.qty > 0">{{ formatRecentQtyShort(rec) }}</span>
              <span class="recent-state" v-if="rec.equipment_state">{{ rec.equipment_state_display }}</span>
            </div>
            <div class="recent-row2">
              <span class="recent-type-label">{{ getRecentRecordTypeLabel(rec) }}</span>
              <span v-if="rec.product_code" class="recent-product">{{ rec.product_code }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-recent">記録なし</div>
      </div>

    </div><!-- /four-col-layout -->

    <!-- トースト通知 -->
    <transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
    </transition>

    <div
      v-if="showProductPhotoDialog"
      class="product-photo-overlay"
      @click.self="closeProductPhotoDialog"
    >
      <div class="product-photo-dialog">
        <div class="product-photo-dialog-header">
          <div class="product-photo-dialog-title">{{ selectedProductCode }}</div>
          <button type="button" class="product-photo-close" @click="closeProductPhotoDialog">×</button>
        </div>
        <div class="product-photo-dialog-body">
          <img
            v-if="productPhotoDisplayUrl"
            :src="productPhotoDisplayUrl"
            class="product-photo-dialog-image"
            alt="製品写真"
          />
          <div v-else class="product-photo-dialog-empty">写真未登録です。撮影して保存できます。</div>
        </div>
        <div v-if="productPhotoDialogMode === 'capture'" class="product-photo-dialog-actions">
          <button
            type="button"
            class="btn-save product-photo-save-btn"
            :disabled="!canCaptureProductPhoto"
            @click="openProductCamera"
          >
            {{ productPhotoUploading ? '保存中...' : '撮影して保存' }}
          </button>
          <input
            ref="productPhotoInputRef"
            type="file"
            accept="image/*"
            capture="environment"
            class="product-photo-file-input"
            @change="onProductPhotoSelected"
          />
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '取得/保存', table: 't_process_realtime_record', desc: '工程リアルタイム記録（生産完成・仕損・設備状態・作業者アクション）' },
  { op: '取得/更新', table: 'line_backlog', desc: '計画品番リスト・計画数・実績数の表示と更新' },
  { op: '取得/更新', table: 'line_gantt_plan', desc: 'ガント計画（計画数変更時の更新）' },
  { op: '保存', table: 'production_plan_change_log', desc: '計画数変更ログの記録' },
  { op: '取得', table: 'masters_product / masters_bom / masters_bomitem', desc: '製品マスタ・BOM展開' },
  { op: '取得', table: 'masters_routing / masters_routingstep / masters_routingstepmaterial', desc: 'ルーティング展開（工程別の対象製品取得）' },
  { op: '取得', table: 'gantt_display_product_map', desc: 'ガント表示用の品番マッピング' },
]
import { t, getLocaleCode } from '@/i18n'
import { getBusinessDate, formatISODate } from '@/utils/dateUtil'

const route = useRoute()
const router = useRouter()
const localeCode = computed(() => getLocaleCode())
const FLOOR_LINE_CODE = 'L2100'

const processes = ref([])
const lines = ref([])
const selectedLineId = ref('')
const selectedProcessId = ref('')
const isSupportMode = ref(false)
const recentRecords = ref([])
const ganttPlanQtyMap = ref({})
const submitting = ref(false)
const qtyInputRef = ref(null)
const productPhotoInputRef = ref(null)

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : '')
const mediaEnvBase = import.meta.env.VITE_MEDIA_BASE_URL || ''
const browserOrigin = typeof window !== 'undefined' ? window.location.origin : ''
let mediaBaseUrl = ''
if (mediaEnvBase) {
  mediaBaseUrl = mediaEnvBase.replace(/\/$/, '')
} else if (import.meta.env.DEV) {
  mediaBaseUrl = browserOrigin
} else {
  mediaBaseUrl = browserOrigin
}

const manualProduct = ref(false)
const manualProducts = ref([])
const manualProductsLoading = ref(false)
const manualProductsLoaded = ref(false)
const manualProductsProcessId = ref(null)
const allPlanProducts = ref([])
const productionProducts = ref([])
const scrapProducts = ref([])
const allScrapProducts = ref([])
const scrapRelationFilter = ref('')
const scrapSearchText = ref('')
const defaultProductId = ref(null)
const selectedGanttPlanId = ref('')
const productImageMap = ref({})
const productMetaMap = ref({})
const filterCurrentTime = ref(true)
const showDone = ref(false)
const showTomorrow = ref(false)
const showYesterday = ref(false)
const calendarWorkingDays = ref(null)
const actualQtyByProductFromBacklog = ref(new Map())
const actualQtyByProductCodeFromBacklog = ref(new Map())
const timeSlots = ref([])
const activeSlotIndex = ref(null)
const selectedOperatorAction = ref('')
const startedProductIds = ref(new Set())
const startedProductIdsLoaded = ref(false)
const latestOperatorActionByProduct = ref(new Map())
const dailyProcessTargets = ref([])
const selectedCoproductChildren = ref([])
const selectedCoproductParentCode = ref('')
const selectedCoproductNoticeLoading = ref(false)
const isPlannedProductsLoading = ref(false)
const bomTreeCache = new Map()
const relatedProductsCacheByProcess = new Map()
let selectedCoproductNoticeRequestSeq = 0
let plannedProductsRequestSeq = 0

// ページネーション（SpotLineInput風）
const PAGE_SIZE = 8
const currentPage = ref(1)
const productCodeFilter = ref('')

// トースト
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null
function showToast(message, type = 'success') {
  toast.value = { show: true, message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

const shouldBlockBomService = (lineId = null, processId = null) => {
  const targetLineId = String(lineId ?? selectedLineId.value ?? '').trim()
  const targetProcessId = String(processId ?? selectedProcessId.value ?? '').trim()
  return !filterCurrentTime.value && targetLineId === '81' && targetProcessId === '24'
}

const record = ref({
  record_type: 'PRODUCTION',
  product_id: '',
  product_code: '',
  counter_qty: null,
  qty: null,
  operator_action_reason: '',
  operator_action_reason_detail: '',
  reason: '',
  reason_detail: '',
  disposition_status: '',
  is_production_recorded: '',
  equipment_state: '',
  batch_no: '',
  operator_name: '',
  remarks: '',
})

const recordTypeOptions = computed(() => [
  { value: 'EQUIPMENT_STATE', label: t('processInput.recordType.equipment') },
  { value: 'PRODUCTION', label: t('processInput.recordType.production') },
  { value: 'SCRAP', label: t('processInput.recordType.scrap') },
])

const scrapReasons = computed(() => [
  { value: 'RUST', label: t('processInput.scrapReason.rust') },
  { value: 'DEFORMATION', label: t('processInput.scrapReason.deformation') },
  { value: 'BEAD_MISALIGN', label: t('processInput.scrapReason.beadMisalign') },
  { value: 'BLOW_HOLE', label: t('processInput.scrapReason.blowHole') },
  { value: 'WELD_PINHOLE', label: t('processInput.scrapReason.weldPinhole') },
  { value: 'UNDERCUT', label: t('processInput.scrapReason.undercut') },
  { value: 'PRECISION_NG', label: t('processInput.scrapReason.precisionNg') },
  { value: 'MISSING_OR_WRONG_ASSEMBLY', label: t('processInput.scrapReason.missingAssembly') },
  { value: 'MATERIAL_WIP_DEFECT', label: t('processInput.scrapReason.materialWip') },
  { value: 'OTHER', label: t('processInput.scrapReason.other') },
])

const scrapDispositionOptions = computed(() => [
  { value: 'REJECTED', label: t('processInput.scrapDisposition.rejected') },
  { value: 'PENDING', label: t('processInput.scrapDisposition.pending') },
])

const productionRecordedOptions = computed(() => [
  { value: false, label: t('processInput.productionRecordedOptions.no') },
  { value: true, label: t('processInput.productionRecordedOptions.yes') },
])

const scrapRelationOptions = computed(() => [
  { value: 'own_process', label: t('processInput.scrapFilter.ownProcess') },
  { value: 'purchased', label: t('processInput.scrapFilter.purchased') },
  { value: 'in_house', label: t('processInput.scrapFilter.inHouse') },
])

const availableRecordTypes = computed(() => {
  const allowed = route.meta?.allowedRecordTypes
  if (Array.isArray(allowed) && allowed.length) {
    return recordTypeOptions.value.filter((type) => allowed.includes(type.value))
  }
  return recordTypeOptions.value
})

const isScrapRecord = computed(() => record.value.record_type === 'SCRAP')
const activeOperatorActions = new Set(['START', 'PAUSE', 'RESUME'])
const startedStateOperatorActions = new Set(['START', 'RESUME'])
const startedOperatorActions = ['END', 'PAUSE']
const pausedOperatorActions = ['RESUME', 'TEMP_END']

const PAUSE_REASON_EQUIPMENT_TROUBLE = '設備トラブル'

const equipmentStates = computed(() => [
  { value: 'RUNNING', label: t('processInput.equipmentState.running') },
  { value: 'IDLE', label: t('processInput.equipmentState.idle') },
  { value: 'SETUP', label: t('processInput.equipmentState.setup') },
  { value: 'MAINTENANCE', label: t('processInput.equipmentState.maintenance') },
  { value: 'BREAKDOWN', label: t('processInput.equipmentState.breakdown') },
  { value: 'STOPPED', label: t('processInput.equipmentState.stopped') },
])

const pauseReasons = computed(() => [
  { value: '設備トラブル', label: t('processInput.pauseReasonOption.equipmentTrouble') },
  { value: '治具トラブル', label: t('processInput.pauseReasonOption.jigTrouble') },
  { value: '品質トラブル', label: t('processInput.pauseReasonOption.qualityTrouble') },
  { value: 'ティーチング', label: t('processInput.pauseReasonOption.teaching') },
  { value: 'ワイヤ交換', label: t('processInput.pauseReasonOption.wireChange') },
  { value: '部品ショート', label: t('processInput.pauseReasonOption.partsShortage') },
  { value: '班長/対応者待ち', label: t('processInput.pauseReasonOption.leaderWait') },
  { value: '工程指導', label: t('processInput.pauseReasonOption.processGuidance') },
  { value: '３ｓ活動', label: t('processInput.pauseReasonOption.activity3s') },
  { value: '改善活動', label: t('processInput.pauseReasonOption.improvement') },
  { value: 'その他', label: t('processInput.pauseReasonOption.other') },
])

const tempEndReasons = computed(() => [
  { value: '本日設備復旧不可', label: t('processInput.tempEndReasonOption.equipmentUnrecoverableToday') },
  { value: '本日治具使用不可', label: t('processInput.tempEndReasonOption.jigUnavailableToday') },
  { value: '他へ製品切り替え', label: t('processInput.tempEndReasonOption.switchProduct') },
  { value: 'その他', label: t('processInput.tempEndReasonOption.other') },
])

const quickQtyPresets = ref([])

const OPERATOR_ACTION_LABEL_KEYS = {
  START: 'processInput.operatorAction.start',
  END: 'processInput.operatorAction.end',
  PAUSE: 'processInput.operatorAction.pause',
  RESUME: 'processInput.operatorAction.resume',
  TEMP_END: 'processInput.operatorAction.tempEnd',
  CANCEL: 'processInput.operatorAction.cancel',
}

// ──────────────────────────────
// ライン・工程
// ──────────────────────────────
const filteredProcesses = computed(() => {
  let list = processes.value
  if (selectedLineId.value) list = list.filter((p) => String(p.line) === String(selectedLineId.value))
  if (!isTwoPersonSameEquipmentMode.value) list = list.filter((p) => !p.two_person_only)
  return list
})
const userUnitLines = computed(() => {
  const unitLines = authState.user?.profile?.unit_lines
  return Array.isArray(unitLines) ? unitLines : []
})
const userAllowedLineIdSet = computed(() => new Set(
  userUnitLines.value.map((item) => String(item?.line_id || '').trim()).filter(Boolean),
))
const preferredUserLineId = computed(() => {
  const mappings = userUnitLines.value
  if (!mappings.length) return ''
  const defaultMapping = mappings.find((item) => item?.is_default)
  const target = defaultMapping || mappings[0]
  return target?.line_id ? String(target.line_id) : ''
})
const ownLines = computed(() => {
  const allowedIds = userAllowedLineIdSet.value
  if (!allowedIds.size) return lines.value
  return lines.value.filter((line) => allowedIds.has(String(line.id)))
})
const showSupportToggle = computed(() => {
  const ownCount = ownLines.value.length
  return ownCount > 0 && ownCount < lines.value.length
})
const availableLines = computed(() => {
  if (isSupportMode.value) return lines.value
  return ownLines.value
})
const selectedLineObj = computed(() =>
  lines.value.find((line) => String(line.id) === String(selectedLineId.value)) || null
)
const selectedProcessObj = computed(() =>
  processes.value.find((process) => String(process.id) === String(selectedProcessId.value)) || null
)
const isFloorLineSelected = computed(
  () => String(selectedLineObj.value?.line_code || '').trim().toUpperCase() === FLOOR_LINE_CODE
)

// ──────────────────────────────
// 日付
// ──────────────────────────────
const getBusinessToday = () => {
  const now = new Date()
  const logical = new Date(now)
  logical.setHours(logical.getHours() - 8)
  return logical
}

const fmtYmd = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

const addCalendarDays = (baseDate, direction) => {
  const workingSet = calendarWorkingDays.value
  const d = new Date(baseDate)
  for (let i = 0; i < 30; i++) {
    d.setDate(d.getDate() + direction)
    const ymd = fmtYmd(d)
    if (!workingSet || workingSet.has(ymd)) return d
  }
  d.setTime(baseDate.getTime())
  d.setDate(d.getDate() + direction)
  return d
}

const workDateStr = ref(fmtYmd(getBusinessToday()))
const workDateChangeReason = ref('')
const workDateChangeReasonDetail = ref('')
const businessTodayYmd = fmtYmd(getBusinessToday())
const isWorkDateChanged = computed(() => (workDateStr.value || '') !== businessTodayYmd)

const currentDateYmd = computed(() => {
  const today = getBusinessToday()
  if (showTomorrow.value) return fmtYmd(addCalendarDays(today, 1))
  if (showYesterday.value) return fmtYmd(addCalendarDays(today, -1))
  return fmtYmd(today)
})

const currentDate = computed(() => {
  const parts = currentDateYmd.value.split('-')
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
  return d.toLocaleDateString(localeCode.value, {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'short'
  })
})

let daisoCalendarId = null

const resolveDaisoCalendarId = async () => {
  if (daisoCalendarId) return daisoCalendarId
  try {
    const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 1 })
    const list = res.data.results || res.data || []
    if (list.length) { daisoCalendarId = list[0].id; return daisoCalendarId }
  } catch {}
  return null
}

const loadCalendarWorkingDays = async () => {
  const lineObj = selectedLineObj.value
  let calendarId = lineObj?.calendar
  if (!calendarId) calendarId = await resolveDaisoCalendarId()
  if (!calendarId) { calendarWorkingDays.value = null; return }
  try {
    const today = getBusinessToday()
    const from = new Date(today)
    from.setDate(from.getDate() - 7)
    const to = new Date(today)
    to.setDate(to.getDate() + 7)
    const res = await api.calendars.getCalendarDays(calendarId, {
      date_from: fmtYmd(from),
      date_to: fmtYmd(to),
      page_size: 100,
    })
    const days = res.data.results || res.data || []
    const workingSet = new Set()
    for (const day of days) {
      if (day.is_working_day) workingSet.add(day.target_date)
    }
    calendarWorkingDays.value = workingSet
  } catch {
    calendarWorkingDays.value = null
  }
}

// ──────────────────────────────
// 製品リスト
// ──────────────────────────────
const currentProductList = computed(() => {
  if (record.value.record_type === 'PRODUCTION') return productionProducts.value
  if (record.value.record_type === 'SCRAP') return scrapProducts.value
  return []
})

const displayProductList = computed(() => {
  if (record.value.record_type === 'SCRAP') return filterScrapCandidates(scrapProducts.value)
  return currentProductList.value
})

const manualProductOptions = computed(() => {
  const list = Array.isArray(manualProducts.value) ? manualProducts.value : []
  const materialTypes = ['intermediate', 'purchased']
  const coproductTypes = ['coproduct_parent', 'coproduct_child']
  let filtered = [...list].filter((p) => {
    if (!p || !(p.product_code || p.product_name)) return false
    if (record.value.record_type !== 'PRODUCTION') return true
    return !materialTypes.includes(p.relation_type)
  })
  if (record.value.record_type === 'SCRAP') filtered = filterScrapCandidates(filtered)
  return filtered.sort((a, b) => {
    const aCoproduct = coproductTypes.includes(a.relation_type)
    const bCoproduct = coproductTypes.includes(b.relation_type)
    if (aCoproduct !== bCoproduct) return aCoproduct ? -1 : 1
    return (a.product_code || '').localeCompare(b.product_code || '')
  })
})

const effectiveProductList = computed(() => {
  if (manualProduct.value || !displayProductList.value.length) {
    return manualProductOptions.value.map(p => ({
      plan_date: currentDateYmd.value,
      product: p.id || p.product,
      product_code: p.product_code || '',
      product_name: p.product_name || '',
      process: selectedProcessId.value,
      plan_qty: p.plan_qty ?? 0,
      actual_qty: p.actual_qty ?? 0,
      relation_type: p.relation_type || '',
    }))
  }
  return displayProductList.value
})

const isDone = (item) => {
  const planQty = toSafeNumber(item?.plan_qty)
  const actualQty = toSafeNumber(item?.actual_qty)
  return planQty > 0 && actualQty >= planQty
}

const filteredListItems = computed(() => {
  let items = effectiveProductList.value
  if (!showDone.value) items = items.filter(item => !isDone(item))
  const keyword = String(productCodeFilter.value || '').trim().toUpperCase()
  if (keyword) {
    items = items.filter((item) => {
      const code = String(item.product_code || '').toUpperCase()
      const name = String(item.product_name || '').toUpperCase()
      return code.includes(keyword) || name.includes(keyword)
    })
  }
  return [...items].sort((a, b) => {
    const seqDiff = getSequenceSortValue(a) - getSequenceSortValue(b)
    if (seqDiff !== 0) return seqDiff
    const planDiff = toSafeNumber(b.plan_qty) - toSafeNumber(a.plan_qty)
    if (planDiff !== 0) return planDiff
    return String(a?.product_code || '').localeCompare(String(b?.product_code || ''))
  })
})

const navProductItems = computed(() => {
  if (!filterCurrentTime.value) return filteredListItems.value
  let items = mergeProductionProductsByProduct(allPlanProducts.value)
  if (!showDone.value) items = items.filter(item => !isDone(item))
  const keyword = String(productCodeFilter.value || '').trim().toUpperCase()
  if (keyword) {
    items = items.filter((item) => {
      const code = String(item.product_code || '').toUpperCase()
      const name = String(item.product_name || '').toUpperCase()
      return code.includes(keyword) || name.includes(keyword)
    })
  }
  return [...items].sort((a, b) => {
    const seqDiff = getSequenceSortValue(a) - getSequenceSortValue(b)
    if (seqDiff !== 0) return seqDiff
    const planDiff = toSafeNumber(b.plan_qty) - toSafeNumber(a.plan_qty)
    if (planDiff !== 0) return planDiff
    return String(a?.product_code || '').localeCompare(String(b?.product_code || ''))
  })
})

const currentNavIndex = computed(() => {
  const list = navProductItems.value
  if (!list.length) return -1
  const selectedId = String(record.value.product_id || '')
  if (selectedId) {
    const idx = list.findIndex((it) => String(it.product || it.id) === selectedId)
    if (idx >= 0) return idx
  }
  const firstVisibleId = String(filteredListItems.value?.[0]?.product || '')
  if (firstVisibleId) {
    const visibleIdx = list.findIndex((it) => String(it.product || it.id) === firstVisibleId)
    if (visibleIdx >= 0) return visibleIdx
  }
  return 0
})


const effectivePageSize = computed(() => (filterCurrentTime.value ? Math.max(filteredListItems.value.length, 1) : PAGE_SIZE))

const pagedItems = computed(() => {
  const size = effectivePageSize.value
  const start = (currentPage.value - 1) * size
  return filteredListItems.value.slice(start, start + size)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredListItems.value.length / effectivePageSize.value)))
const pageStart = computed(() => filteredListItems.value.length === 0 ? 0 : (currentPage.value - 1) * effectivePageSize.value + 1)
const pageEnd = computed(() => Math.min(currentPage.value * effectivePageSize.value, filteredListItems.value.length))

// 選択中の製品情報
const selectedProductObj = computed(() => {
  const pid = String(record.value.product_id || '').trim()
  if (!pid) return null
  const ganttId = selectedGanttPlanId.value
  if (ganttId) {
    const exact = effectiveProductList.value.find(p => String(p.product || p.id) === pid && p.gantt_plan_id === ganttId)
    if (exact) return exact
  }
  return effectiveProductList.value.find(p => String(p.product || p.id) === pid) || null
})
const selectedProductCode = computed(() =>
  selectedProductObj.value?.product_code || record.value.product_code || ''
)
const selectedProductName = computed(() =>
  selectedProductObj.value?.product_name || ''
)
const selectedProductImageUrl = computed(() => {
  const pid = selectedProductObj.value?.product ?? selectedProductObj.value?.id ?? record.value.product_id
  if (pid === null || pid === undefined || pid === '') return ''
  return (
    selectedProductObj.value?.image_url ||
    productImageMap.value[String(pid)] ||
    productImageMap.value[pid] ||
    ''
  )
})
const showProductPhotoDialog = ref(false)
const productPhotoDialogMode = ref('view')
const productPhotoPreviewUrl = ref('')
const productPhotoUploading = ref(false)
const canOpenProductPhotoDialog = computed(() => !!selectedProductCode.value)
const canCaptureProductPhoto = computed(() => !!record.value.product_id && !productPhotoUploading.value)
const productPhotoDisplayUrl = computed(() => productPhotoPreviewUrl.value || selectedProductImageUrl.value || '')

// ──────────────────────────────
// アバターカラー
// ──────────────────────────────

// ──────────────────────────────
// 作業状態
// ──────────────────────────────
const productCodeLookup = computed(() => {
  const lookup = new Map()
  const apply = (pid, code) => {
    if (pid === null || pid === undefined || pid === '') return
    const normalizedCode = String(code || '').trim()
    if (!normalizedCode) return
    const key = String(pid)
    if (!lookup.has(key)) lookup.set(key, normalizedCode)
  }
  const planLikeLists = [
    ...(Array.isArray(displayProductList.value) ? displayProductList.value : []),
    ...(Array.isArray(currentProductList.value) ? currentProductList.value : []),
    ...(Array.isArray(allPlanProducts.value) ? allPlanProducts.value : []),
    ...(Array.isArray(productionProducts.value) ? productionProducts.value : []),
    ...(Array.isArray(manualProducts.value) ? manualProducts.value : []),
  ]
  planLikeLists.forEach((item) => apply(item?.product ?? item?.id, item?.product_code))
  ;(Array.isArray(recentRecords.value) ? recentRecords.value : []).forEach((rec) => {
    apply(
      getOperatorActionProductId(rec) ?? rec?.product ?? rec?.product_id,
      rec?.product_code || rec?.event_data?.plan_target?.product_code
    )
  })
  return lookup
})

const selectedProductLatestOperatorAction = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return ''
  if (!startedProductIdsLoaded.value) return ''
  const productId = record.value.product_id
  if (!productId) return ''
  return String(latestOperatorActionByProduct.value.get(String(productId)) || '').toUpperCase()
})

const selectedProductWorkState = computed(() => {
  const latestAction = selectedProductLatestOperatorAction.value
  if (latestAction === 'PAUSE') return 'PAUSED'
  if (latestAction === 'TEMP_END') return 'TEMP_ENDED'
  if (startedStateOperatorActions.has(latestAction)) return 'STARTED'
  return 'NOT_STARTED'
})

const hasStartedOtherProduct = computed(() => {
  if (!startedProductIdsLoaded.value) return false
  const selectedProductId = String(record.value.product_id || '')
  for (const productId of startedProductIds.value) {
    if (!selectedProductId || String(productId) !== selectedProductId) return true
  }
  return false
})

const shouldAutoStartByProduct = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return false
  if (!startedProductIdsLoaded.value) return false
  const productId = record.value.product_id
  if (!productId) return false
  if (hasStartedOtherProduct.value) return false
  return selectedProductWorkState.value === 'NOT_STARTED'
})

const operatorActionOptions = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return []
  if (!hasSelectedProduct()) return []
  if (!startedProductIdsLoaded.value) return []
  if (selectedProductWorkState.value === 'PAUSED') {
    return pausedOperatorActions.map((action) => ({ value: action, label: t(OPERATOR_ACTION_LABEL_KEYS[action]) }))
  }
  if (selectedProductWorkState.value === 'TEMP_ENDED') {
    return ['RESUME', 'CANCEL'].map((action) => ({ value: action, label: t(OPERATOR_ACTION_LABEL_KEYS[action]) }))
  }
  if (selectedProductWorkState.value === 'STARTED') {
    return startedOperatorActions.map((action) => ({ value: action, label: t(OPERATOR_ACTION_LABEL_KEYS[action]) }))
  }
  return []
})

const allowedOperatorActions = computed(() =>
  operatorActionOptions.value.map((opt) => String(opt.value || '').toUpperCase())
)

const effectiveOperatorAction = computed(() => {
  if (shouldAutoStartByProduct.value) return 'START'
  const selectedAction = String(selectedOperatorAction.value || '').trim().toUpperCase()
  if (allowedOperatorActions.value.includes(selectedAction)) return selectedAction
  return ''
})
const shouldShowOperatorActionRow = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return false
  if (!hasSelectedProduct()) return false
  return startedProductIdsLoaded.value
})
const shouldShowOperatorActionSelector = computed(() => shouldShowOperatorActionRow.value && !shouldAutoStartByProduct.value)
const shouldShowAutoStartAction = computed(() => shouldShowOperatorActionRow.value && shouldAutoStartByProduct.value)
const isOperatorActionMode = computed(() => record.value.record_type === 'PRODUCTION' && !!effectiveOperatorAction.value)
const isQtyRequiredOperatorAction = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return false
  return ['END', 'PAUSE'].includes(String(effectiveOperatorAction.value || '').toUpperCase())
})
const shouldShowQtyInput = computed(() => {
  if (record.value.record_type === 'SCRAP') return true
  if (record.value.record_type !== 'PRODUCTION') return false
  return isQtyRequiredOperatorAction.value
})
const requiresOperatorActionReason = computed(() =>
  record.value.record_type === 'PRODUCTION' &&
  ['PAUSE', 'TEMP_END'].includes(String(effectiveOperatorAction.value || '').toUpperCase())
)
const operatorActionReasonLabelKey = computed(() =>
  effectiveOperatorAction.value === 'TEMP_END' ? 'processInput.tempEndReason' : 'processInput.pauseReason'
)
const operatorActionReasonPlaceholderKey = computed(() =>
  effectiveOperatorAction.value === 'TEMP_END' ? 'processInput.tempEndReasonPlaceholder' : 'processInput.pauseReasonPlaceholder'
)
const isPauseReasonDropdown = computed(() => String(effectiveOperatorAction.value || '').toUpperCase() === 'PAUSE')
const isTempEndReasonDropdown = computed(() => String(effectiveOperatorAction.value || '').toUpperCase() === 'TEMP_END')
const isTempEndReasonOtherSelected = computed(() => {
  const val = String(record.value.operator_action_reason || '').trim()
  if (!val) return false
  const otherLabel = t('processInput.tempEndReasonOption.other')
  if (val === 'その他' || val === 'OTHER' || val === otherLabel) return true
  const matched = tempEndReasons.value.find((r) => String(r.value || '').trim() === val)
  return !!matched && String(matched.label || '').trim() === String(otherLabel || '').trim()
})
const requiresTempEndOtherRemarks = computed(() => {
  if (!isTempEndReasonOtherSelected.value) return false
  return String(effectiveOperatorAction.value || '').toUpperCase() === 'TEMP_END'
})
const isEndOperatorAction = computed(() => String(effectiveOperatorAction.value || '').toUpperCase() === 'END')
const isPauseOperatorAction = computed(() => String(effectiveOperatorAction.value || '').toUpperCase() === 'PAUSE')
const qtyInputMin = computed(() => {
  if (isPauseOperatorAction.value) return 0
  return isEndOperatorAction.value && hasFilledText(record.value.remarks) ? 0 : 1
})

// ──────────────────────────────
// 加工中・中断中
// ──────────────────────────────
const currentProcessingProductId = computed(() => {
  if (!selectedProcessId.value || !startedProductIdsLoaded.value) return ''
  const activeProductIds = []
  latestOperatorActionByProduct.value.forEach((action, productId) => {
    if (startedStateOperatorActions.has(String(action || '').toUpperCase())) activeProductIds.push(String(productId))
  })
  if (!activeProductIds.length) return ''
  const selectedProductId = String(record.value.product_id || '')
  if (selectedProductId && activeProductIds.includes(selectedProductId)) return selectedProductId
  const recentActive = (Array.isArray(recentRecords.value) ? recentRecords.value : []).find((rec) => {
    if (rec?.record_type !== 'OPERATOR_ACTION') return false
    const action = rec?.event_data?.action || rec?.event_data?.operator_action || rec?.event_data?.action_type || ''
    if (!startedStateOperatorActions.has(String(action).toUpperCase())) return false
    const productId = String(getOperatorActionProductId(rec) || '')
    return !!productId && activeProductIds.includes(productId)
  })
  if (recentActive) return String(getOperatorActionProductId(recentActive) || '')
  return activeProductIds[0] || ''
})

const currentProcessingProductCode = computed(() => {
  const productId = currentProcessingProductId.value
  if (!productId) return ''
  return productCodeLookup.value.get(String(productId)) || ''
})

const currentProcessingLabel = computed(() => {
  const code = currentProcessingProductCode.value
  if (!code) return ''
  return t('processInput.currentProcessing', { code })
})

const isProductionRunning = computed(() => !!currentProcessingProductId.value)

const jumpToProcessingProduct = () => {
  const productId = currentProcessingProductId.value
  if (!productId) return
  const item = filteredListItems.value.find((it) => String(it.product) === String(productId))
  if (item) selectPlannedProduct(item)
}

const tempEndedProductIds = computed(() => {
  const ids = new Set()
  latestOperatorActionByProduct.value.forEach((action, productId) => {
    if (String(action || '').toUpperCase() === 'TEMP_END') ids.add(String(productId))
  })
  return ids
})
const isTempEndedProduct = (productId) => productId ? tempEndedProductIds.value.has(String(productId)) : false
const isCurrentProcessingProduct = (productId) => productId ? String(currentProcessingProductId.value || '') === String(productId) : false

const pausedProductInfo = computed(() => {
  if (!selectedProcessId.value || !startedProductIdsLoaded.value) return null
  const pausedProductIds = []
  latestOperatorActionByProduct.value.forEach((action, productId) => {
    if (String(action || '').toUpperCase() === 'PAUSE') pausedProductIds.push(String(productId))
  })
  if (!pausedProductIds.length) return null
  const selectedProductId = String(record.value.product_id || '')
  const targetProductId = pausedProductIds.includes(selectedProductId) ? selectedProductId : pausedProductIds[0]
  const code = productCodeLookup.value.get(String(targetProductId)) || ''
  const recentPauseRecord = (Array.isArray(recentRecords.value) ? recentRecords.value : []).find((rec) => {
    if (rec?.record_type !== 'OPERATOR_ACTION') return false
    const action = rec?.event_data?.action || rec?.event_data?.operator_action || rec?.event_data?.action_type || ''
    if (String(action).toUpperCase() !== 'PAUSE') return false
    const pid = String(getOperatorActionProductId(rec) || '')
    return pid && pid === String(targetProductId)
  })
  const reason = recentPauseRecord?.event_data?.pause_reason || recentPauseRecord?.event_data?.operator_action_reason || t('processInput.pauseReasonFallback')
  if (!code) return null
  return { code, reason }
})

const pauseNoticeLabel = computed(() => {
  const info = pausedProductInfo.value
  if (!info) return ''
  return t('processInput.pauseNotice', { code: info.code, reason: info.reason })
})

// ──────────────────────────────
// 計画数サマリ
// ──────────────────────────────
const toSafeNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const findProductionProductBySelection = (productId) => {
  if (!productId) return null
  const ganttId = selectedGanttPlanId.value
  if (ganttId) {
    const exact = productionProducts.value.find((p) => String(p.product) === String(productId) && p.gantt_plan_id === ganttId)
    if (exact) return exact
  }
  return productionProducts.value.find((p) => String(p.product) === String(productId)) || null
}

const planStatus = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return null
  const productId = record.value.product_id
  if (!productId) return null
  const target = findProductionProductBySelection(productId)
  if (!target) return null
  const planQty = toSafeNumber(target.plan_qty)
  const actualQty = toSafeNumber(target.actual_qty)
  const currentInput = Math.max(toSafeNumber(record.value.qty), 0)
  const remaining = Math.max(planQty - actualQty, 0)
  const remainingAfterInput = Math.max(planQty - actualQty - currentInput, 0)
  return { planQty, actualQty, remaining, remainingAfterInput }
})

const normalizeTargetText = (value) => String(value || '').trim().toLowerCase().replace(/\s+/g, '')

const selectedProcessTarget = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return null
  const list = Array.isArray(dailyProcessTargets.value) ? dailyProcessTargets.value : []
  if (!list.length) return null
  if (list.length === 1) return list[0]
  const code = normalizeTargetText(selectedProductCode.value)
  const name = normalizeTargetText(selectedProductName.value)
  const matched = list.find((item) => {
    const label = normalizeTargetText(item?.product_label)
    if (!label) return false
    return (code && (code.includes(label) || label.includes(code))) || (name && (name.includes(label) || label.includes(name)))
  })
  return matched || list[0] || null
})

const headerProcessTargetLabel = computed(() => {
  const list = Array.isArray(dailyProcessTargets.value) ? dailyProcessTargets.value : []
  if (!list.length) return ''
  return list
    .map((item) => {
      const time = String(item?.target_time || '').trim()
      const qty = formatNumber(item?.target_qty || 0)
      const label = String(item?.product_label || '').trim()
      return `${time}目標 ${qty}台${label ? ` (${label})` : ''}`
    })
    .join(' / ')
})

const shouldUseCounterInput = computed(() => {
  const lineCode = String(selectedLineObj.value?.line_code || '').trim().toUpperCase()
  const processCode = String(selectedProcessObj.value?.process_code || '').trim()
  return (
    record.value.record_type === 'PRODUCTION' &&
    shouldShowQtyInput.value &&
    lineCode === 'L2200' &&
    ['4019', '4053'].includes(processCode)
  )
})

const counterBaseQty = computed(() => {
  if (!shouldUseCounterInput.value) return 0
  const productId = record.value.product_id
  if (!productId) return 0
  const target = findProductionProductBySelection(productId)
  return Math.max(toSafeNumber(target?.actual_qty), 0)
})

const counterQtyError = computed(() => {
  if (!shouldUseCounterInput.value) return ''
  if (record.value.counter_qty === null || record.value.counter_qty === '') return ''
  const counterQty = toSafeNumber(record.value.counter_qty)
  if (counterQty < counterBaseQty.value) {
    return t('processInput.counterQtyMinError', { actualQty: formatNumber(counterBaseQty.value) })
  }
  return ''
})

const editingPlanQty = ref(false)
const editPlanQtyValue = ref(0)
const editPlanStartTime = ref('08:00')
const editPlanEndTime = ref('09:00')
const editedPlanIds = ref(new Set())

const selectedPlanItem = computed(() => {
  const productId = record.value.product_id
  if (!productId) return null
  return findProductionProductBySelection(productId)
})

const startEditPlanQty = async () => {
  const item = selectedPlanItem.value
  if (!item) return
  const pw = prompt('計画数を変更するにはパスワードを入力してください')
  if (!pw) return
  try {
    await api.systemSettings.verifyPlanQtyPassword({ password: pw })
  } catch (e) {
    const detail = e?.response?.data?.detail || 'パスワードが正しくありません。'
    alert(detail)
    return
  }
  editPlanQtyValue.value = toSafeNumber(item.plan_qty)
  if (!item.gantt_plan_id) {
    const now = new Date()
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    editPlanStartTime.value = `${hh}:${mm}`
    const endH = now.getHours() + 1
    editPlanEndTime.value = `${String(endH % 24).padStart(2, '0')}:${mm}`
  }
  editingPlanQty.value = true
}

const cancelEditPlanQty = () => {
  editingPlanQty.value = false
}

const savePlanQty = async () => {
  const item = selectedPlanItem.value
  if (!item) return
  const qty = Math.max(Math.round(toSafeNumber(editPlanQtyValue.value)), 0)
  const processId = selectedProcessId.value
  const process = processes.value.find(p => String(p.id) === String(processId))
  const lineId = process?.line
  if (!lineId || !processId) return

  try {
    if (item.gantt_plan_id) {
      await api.lineGanttPlans.bulkUpdate([{
        plan_id: item.gantt_plan_id,
        process_id: processId,
        output_product_id: item.product,
        quantity: qty,
      }])
    } else {
      const planDate = currentDateYmd.value
      const startTime = `${planDate}T${editPlanStartTime.value}:00`
      const endTime = `${planDate}T${editPlanEndTime.value}:00`
      const res = await api.lineGanttPlans.manualAdd({
        line_id: lineId,
        process_id: processId,
        output_product_id: item.product,
        start_time: startTime,
        end_time: endTime,
        quantity: qty,
      })
      const newPlanId = res?.data?.plan_id
      if (newPlanId) editedPlanIds.value.add(newPlanId)
    }
    if (item.gantt_plan_id) editedPlanIds.value.add(item.gantt_plan_id)
    editingPlanQty.value = false
    await loadPlannedProducts()
  } catch (e) {
    const detail = e?.response?.data?.detail || '計画数の保存に失敗しました。'
    alert(detail)
  }
}

const getPlanQtyState = (item) => {
  const planQty = toSafeNumber(item?.plan_qty)
  const actualQty = toSafeNumber(item?.actual_qty)
  if (planQty > 0 && actualQty === planQty) return 'done'
  if (actualQty > planQty) return 'over'
  return 'plan'
}

const getPlanQtyBadgeLabel = (item) => {
  const state = getPlanQtyState(item)
  const planQty = toSafeNumber(item?.plan_qty)
  const actualQty = toSafeNumber(item?.actual_qty)
  if (state === 'done') return t('processInput.planQtyDone')
  if (state === 'over') {
    const diff = formatNumber(Math.max(actualQty - planQty, 0))
    return t('processInput.planQtyOver', { diff })
  }
  return formatNumber(planQty)
}

// ──────────────────────────────
// 設備状態キャッシュ
// ──────────────────────────────
const equipmentStateStorageKey = computed(() => {
  const lineId = selectedLineId.value || 'none'
  const processId = selectedProcessId.value || 'none'
  return `pm_equipment_state_${lineId}_${processId}`
})
const loadEquipmentStateCache = () => {
  if (typeof window === 'undefined' || !window.localStorage) return ''
  const key = equipmentStateStorageKey.value
  if (!key) return ''
  const cached = window.localStorage.getItem(key) || ''
  if (!cached) return ''
  return equipmentStates.value.some((s) => s.value === cached) ? cached : ''
}
const saveEquipmentStateCache = (state) => {
  if (typeof window === 'undefined' || !window.localStorage) return
  const key = equipmentStateStorageKey.value
  if (!key || !state) return
  window.localStorage.setItem(key, state)
}
const setEquipmentState = (state) => {
  record.value.equipment_state = state
  saveEquipmentStateCache(state)
}
const restoreEquipmentStateIfNeeded = () => {
  if (record.value.record_type !== 'EQUIPMENT_STATE') return
  if (record.value.equipment_state) return
  if (isProductionRunning.value) { setEquipmentState('RUNNING'); return }
  const cached = loadEquipmentStateCache()
  if (cached) record.value.equipment_state = cached
}

// ──────────────────────────────
// フォーマット
// ──────────────────────────────
const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleDateString(localeCode.value, { year: 'numeric', month: '2-digit', day: '2-digit' })
}
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString(localeCode.value, { hour: '2-digit', minute: '2-digit' })
}
const formatShortDate = (timestamp) => {
  const d = new Date(timestamp)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
const formatNumber = (value) => {
  if (value === null || value === undefined) return '0'
  return Number(value).toLocaleString(localeCode.value)
}
const formatRecentQty = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0個'
  const isInteger = Number.isInteger(num)
  return `${num.toLocaleString(localeCode.value, isInteger ? {} : { maximumFractionDigits: 3 })}個`
}
const formatRecentValue = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  const isInteger = Number.isInteger(num)
  return num.toLocaleString(localeCode.value, isInteger ? {} : { maximumFractionDigits: 3 })
}

const dailyProductRankMap = computed(() => {
  const allMerged = mergeProductionProductsByProduct(allPlanProducts.value)
  const withPlan = allMerged.filter((p) => toSafeNumber(p?.plan_qty) > 0)
  const sorted = [...withPlan].sort((a, b) => {
    const seqDiff = getSequenceSortValue(a) - getSequenceSortValue(b)
    if (seqDiff !== 0) return seqDiff
    return String(a?.product_code || '').localeCompare(String(b?.product_code || ''))
  })
  const map = new Map()
  sorted.forEach((p, i) => {
    const key = productSeqKey(p)
    if (key && !map.has(key)) map.set(key, i + 1)
  })
  return map
})

const getDisplayProductCode = (item) => {
  const code = String(item?.product_code || '').trim() || t('processInput.unsetProductCode')
  if (toSafeNumber(item?.plan_qty) <= 0) return code
  const rank = dailyProductRankMap.value.get(productSeqKey(item))
  if (!rank) return code
  return `${rank} ${code}`
}

const getSequenceSortValue = (item) => {
  const ms = item?.gantt_start_ms
  if (Number.isFinite(ms)) return ms
  const start = item?.start
  if (start instanceof Date && !isNaN(start.getTime())) return start.getTime()
  const seqRaw = item?.sequence_no
  const seqNo = seqRaw === null || seqRaw === undefined || seqRaw === '' ? null : Number(seqRaw)
  if (!Number.isFinite(seqNo) || seqNo <= 0) return Number.POSITIVE_INFINITY
  return seqNo
}

// ──────────────────────────────
// 最近のレコード
// ──────────────────────────────
const getOperatorActionProductId = (rec) => {
  if (!rec) return null
  return rec.product ?? rec.product_id ?? rec.event_data?.plan_target?.product_id ?? null
}
const getOperatorActionLabel = (action) => {
  const actionKey = String(action || '').toUpperCase()
  const labelKey = OPERATOR_ACTION_LABEL_KEYS[actionKey]
  return labelKey ? t(labelKey) : ''
}
const getRecentRecordTypeLabel = (rec) => {
  if (!rec) return ''
  if (rec.record_type === 'OPERATOR_ACTION') {
    const action = rec.event_data?.action || rec.event_data?.operator_action || rec.event_data?.action_type || ''
    return getOperatorActionLabel(action) || t('processInput.recordType.operatorAction')
  }
  if (rec.record_type === 'PRODUCTION') return '完成'
  return rec.record_type_display
}
const isCoproductChildRecord = (rec) => {
  const parentRecordId = rec?.event_data?.coproduct_parent_record_id
  return parentRecordId !== null && parentRecordId !== undefined && String(parentRecordId).trim() !== ''
}
const isEndOperatorActionRecord = (rec) => {
  if (!rec || rec.record_type !== 'OPERATOR_ACTION') return false
  const action = String(rec?.event_data?.action || rec?.event_data?.operator_action || rec?.event_data?.action_type || '').toUpperCase()
  return action === 'END'
}
const recentRecordsForDisplay = computed(() => {
  const items = Array.isArray(recentRecords.value) ? recentRecords.value : []
  const endActionRecordIdsLinkedFromProduction = new Set(
    items.filter((rec) => rec?.record_type === 'PRODUCTION')
      .map((rec) => rec?.event_data?.operator_action_record_id)
      .filter((id) => id !== null && id !== undefined && String(id).trim() !== '')
      .map((id) => String(id))
  )
  return items.filter((rec) => {
    if (isCoproductChildRecord(rec)) return false
    if (isEndOperatorActionRecord(rec) && endActionRecordIdsLinkedFromProduction.has(String(rec?.id))) return false
    return true
  })
})

const recentPlanQtyLookup = computed(() => {
  const map = new Map()
  const add = (productId, productCode, planQty) => {
    const qty = toSafeNumber(planQty)
    if (qty <= 0) return
    const idKey = String(productId || '').trim()
    const codeKey = String(productCode || '').trim()
    if (idKey && !map.has(`id:${idKey}`)) map.set(`id:${idKey}`, qty)
    if (codeKey && !map.has(`code:${codeKey}`)) map.set(`code:${codeKey}`, qty)
  }
  ;(Array.isArray(allPlanProducts.value) ? allPlanProducts.value : []).forEach((item) => add(item?.product, item?.product_code, item?.plan_qty))
  ;(Array.isArray(currentProductList.value) ? currentProductList.value : []).forEach((item) => add(item?.product, item?.product_code, item?.plan_qty))
  return map
})

const getRecentPlanQty = (rec) => {
  const productCode = String(rec?.product_code || rec?.event_data?.plan_target?.product_code || '').trim()
  if (productCode && rec?.timestamp) {
    const bizDate = formatISODate(getBusinessDate(new Date(rec.timestamp)))
    const byGantt = ganttPlanQtyMap.value?.[productCode]?.[bizDate]
    if (byGantt !== null && byGantt !== undefined && Number.isFinite(Number(byGantt))) return Number(byGantt)
  }
  const eventPlanQty = rec?.event_data?.plan_target?.plan_qty
  if (eventPlanQty !== null && eventPlanQty !== undefined && Number.isFinite(Number(eventPlanQty))) return Number(eventPlanQty)
  const productId = String(rec?.product ?? rec?.product_id ?? '').trim()
  if (productId) { const byId = recentPlanQtyLookup.value.get(`id:${productId}`); if (Number.isFinite(byId)) return byId }
  if (productCode) { const byCode = recentPlanQtyLookup.value.get(`code:${productCode}`); if (Number.isFinite(byCode)) return byCode }
  return 0
}
const formatRecentQtyWithPlan = (rec) => {
  const planQty = getRecentPlanQty(rec)
  return `計画${formatRecentValue(planQty)} / 実績${formatRecentQty(rec?.qty)}`
}
const formatRecentQtyShort = (rec) => {
  const planQty = getRecentPlanQty(rec)
  return `計${formatRecentValue(planQty)}/実${formatRecentValue(rec?.qty)}`
}

const RECENT_RECORD_COLOR_PALETTE = [
  { border: '#2563eb', bg: '#eff6ff' }, { border: '#059669', bg: '#ecfdf5' },
  { border: '#d97706', bg: '#fffbeb' }, { border: '#7c3aed', bg: '#f5f3ff' },
  { border: '#db2777', bg: '#fdf2f8' }, { border: '#0f766e', bg: '#f0fdfa' },
  { border: '#b91c1c', bg: '#fef2f2' },
]
const hashString = (value) => {
  const text = String(value || '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) hash = (hash * 31 + text.charCodeAt(i)) >>> 0
  return hash
}
const getRecentRecordColorStyle = (rec) => {
  const key = String(rec?.product_code || rec?.event_data?.plan_target?.product_code || '').trim()
  if (!key) return null
  const idx = hashString(key) % RECENT_RECORD_COLOR_PALETTE.length
  const color = RECENT_RECORD_COLOR_PALETTE[idx]
  return { borderLeft: `4px solid ${color.border}`, backgroundColor: color.bg }
}

// ──────────────────────────────
// ページモードクラス
// ──────────────────────────────
const isEmbeddedTablet = computed(() => String(route.query.embed || '') === 'tablet')
const isTwoPersonSameEquipmentMode = computed(() => String(route.query.two_person_same_equipment || '') === '1')
const normalizeOperatorName = (value) => String(value || '').trim().toLowerCase()
const operatorScopeName = computed(() => normalizeOperatorName(record.value.operator_name || defaultOperatorName.value || ''))
const operatorScopeUserId = computed(() => String(route.query.operator_user_id || '').trim())
const twoPersonScopeWarning = computed(() => {
  if (!isTwoPersonSameEquipmentMode.value) return ''
  if (operatorScopeUserId.value) return ''
  return '作業者ID未指定のため加工中が混在表示されます'
})
const showRecentPanel = ref(false)
const coproductExpanded = ref(false)
const isCompactFormTablet = computed(() => true)

const pageModeClass = computed(() => {
  switch (record.value.equipment_state) {
    case 'RUNNING': return 'page-run'
    case 'IDLE': return 'page-idle'
    case 'SETUP': return 'page-setup'
    case 'MAINTENANCE': return 'page-maintenance'
    case 'BREAKDOWN': return 'page-breakdown'
    case 'STOPPED': return 'page-stopped'
    default: return ''
  }
})
const formModeClass = computed(() => {
  if (record.value.record_type === 'PRODUCTION') return 'mode-production'
  if (record.value.record_type === 'SCRAP') return 'mode-scrap'
  return ''
})

// ──────────────────────────────
// 仕損フィルタ
// ──────────────────────────────
const normalizeRelationType = (type) => {
  if (!type) return ''
  return String(type).replace(/([a-z0-9])([A-Z])/g, '$1_$2').replace(/[\s\-.]/g, '_').toLowerCase()
}
const getProductMeta = (productId) => {
  if (productId === null || productId === undefined) return {}
  const idStr = String(productId)
  return productMetaMap.value[idStr] || productMetaMap.value[productId] || {}
}
const getOriginProcessId = (item) => item?.origin_process_id ?? item?.source_process_id ?? item?.process ?? null

const isUpstreamProductCandidate = (item) => {
  if (!item) return false
  const relation = normalizeRelationType(item.relation_type)
  if (relation === 'purchased') return false
  const sourcing = String(item.sourcing_type || item.sourcingType || '').toUpperCase()
  const originProcess = getOriginProcessId(item)
  const currentProcess = selectedProcessId.value
  const hasDifferentProcess = originProcess && currentProcess && String(originProcess) !== String(currentProcess)
  if (hasDifferentProcess && sourcing === 'BUY') return false
  if (hasDifferentProcess) return true
  if (!originProcess && sourcing && sourcing !== 'BUY') return true
  return false
}
const isFinalProductCandidate = (item) => {
  if (!item) return false
  const productId = item.product ?? item.id
  const meta = getProductMeta(productId)
  if (item.is_final_product || item.is_line_final_product) return true
  if (meta.is_final_product || meta.is_line_final_product) return true
  return normalizeRelationType(item.relation_type) === 'final_product'
}
const getScrapCategory = (item) => {
  if (!item) return null
  const relation = normalizeRelationType(item.relation_type || '')
  if (relation === 'purchased') return 'purchased'
  const sourcing = String(item.sourcing_type || item.sourcingType || '').toUpperCase()
  if (sourcing === 'BUY') return 'purchased'
  const bomProcessId = item.origin_process_id ?? null
  const currentProcess = selectedProcessId.value
  if (bomProcessId && currentProcess && String(bomProcessId) !== String(currentProcess)) return 'in_house'
  if (relation === 'intermediate' && !bomProcessId) return 'in_house'
  return 'own_process'
}
const applyScrapTypeDefaults = (item) => {
  if (!item || record.value.record_type !== 'SCRAP') return
  const category = getScrapCategory(item)
  if (category) {
    scrapRelationFilter.value = category
    if (category === 'purchased' || category === 'in_house') {
      record.value.is_production_recorded = true
    } else if (category === 'own_process') {
      record.value.is_production_recorded = ''
    }
  }
}
const isScrapFilterActive = computed(() => !!scrapRelationFilter.value || !!(scrapSearchText.value || '').trim())

const filterScrapCandidates = (list) => {
  const items = Array.isArray(list) ? list : []
  const relation = scrapRelationFilter.value
  const query = (scrapSearchText.value || '').trim().toLowerCase()
  if (!relation && !query) return items
  const matchesQuery = (p) => {
    const code = (p.product_code || '').toLowerCase()
    const name = (p.product_name || '').toLowerCase()
    return code.includes(query) || name.includes(query)
  }
  const matchesRelation = (p) => !relation || getScrapCategory(p) === relation
  const filtered = items.filter((p) => p && matchesRelation(p) && (!query || matchesQuery(p)))
  if (relation && filtered.length === 0) {
    return items.filter((p) => p && (!query || matchesQuery(p)))
  }
  return filtered
}

// ──────────────────────────────
// 時間帯スロット
// ──────────────────────────────
const formatSlotTime = (dt) => {
  if (!(dt instanceof Date)) return ''
  return `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
}
const toIsoDateTimeOrNull = (value) => {
  if (!value) return null
  const dt = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(dt.getTime())) return null
  return dt.toISOString()
}

const slotLabel = computed(() => {
  if (!timeSlots.value.length) return ''
  if (filterCurrentTime.value) {
    const idx = activeSlotIndex.value ?? 0
    const slot = timeSlots.value[idx]
    if (!slot) return ''
    return `${formatSlotTime(slot.start)} - ${formatSlotTime(slot.end)}`
  }
  const first = timeSlots.value[0]
  const last = timeSlots.value[timeSlots.value.length - 1]
  if (!first || !last) return ''
  return `${formatSlotTime(first.start)} - ${formatSlotTime(last.end)}`
})

const selectedProductTimeLabel = computed(() => {
  if (!timeSlots.value.length) return ''
  const productId = String(record.value.product_id || '').trim()
  if (!productId) return ''
  const ganttId = selectedGanttPlanId.value
  let startTime = null
  let endTime = null
  ;(timeSlots.value || []).forEach((slot) => {
    const slotItems = Array.isArray(slot?.items) ? slot.items : []
    const matched = ganttId
      ? slotItems.some((item) => String(item?.product || '').trim() === productId && item?.gantt_plan_id === ganttId)
      : slotItems.some((item) => String(item?.product || '').trim() === productId)
    if (!matched) return
    const slotStart = slot?.start instanceof Date ? slot.start : new Date(slot?.start)
    const slotEnd = slot?.end instanceof Date ? slot.end : new Date(slot?.end)
    if (Number.isNaN(slotStart.getTime()) || Number.isNaN(slotEnd.getTime())) return
    if (!startTime || slotStart.getTime() < startTime.getTime()) startTime = slotStart
    if (!endTime || slotEnd.getTime() > endTime.getTime()) endTime = slotEnd
  })
  if (!startTime || !endTime) return ''
  return `${formatSlotTime(startTime)} - ${formatSlotTime(endTime)}`
})

const plannedTimeLabel = computed(() => selectedProductTimeLabel.value || slotLabel.value)
const canPrevSlot = computed(() => filterCurrentTime.value && timeSlots.value.length > 0 && (activeSlotIndex.value ?? 0) > 0)
const canNextSlot = computed(() => filterCurrentTime.value && timeSlots.value.length > 0 && (activeSlotIndex.value ?? 0) < timeSlots.value.length - 1)
const goPrevSlot = () => { if (!canPrevSlot.value) return; activeSlotIndex.value = Math.max(0, (activeSlotIndex.value ?? 0) - 1); applyTimeSlotFilter() }
const goNextSlot = () => { if (!canNextSlot.value) return; activeSlotIndex.value = Math.min(timeSlots.value.length - 1, (activeSlotIndex.value ?? 0) + 1); applyTimeSlotFilter() }

// ──────────────────────────────
// ヘルパー
// ──────────────────────────────
const hasFilledText = (value) => (value ?? '').toString().trim().length > 0
const hasSelectedProduct = () => !!record.value.product_id || hasFilledText(record.value.product_code)
const hasEffectiveOperatorAction = () => hasFilledText(effectiveOperatorAction.value)

const ensureScrapDefaults = () => {
  if (record.value.record_type !== 'SCRAP') return
  if (!record.value.qty || record.value.qty <= 0) record.value.qty = 1
  if (!(record.value.disposition_status || '').trim()) record.value.disposition_status = 'REJECTED'
}

const ensureDefaultRecordType = () => {
  const types = availableRecordTypes.value
  if (!types.length) { record.value.record_type = ''; return }
  const exists = types.some((t) => t.value === record.value.record_type)
  if (types.length === 1) { record.value.record_type = types[0].value; return }
  if (!exists) {
    const hasProd = types.some((t) => t.value === 'PRODUCTION')
    record.value.record_type = hasProd ? 'PRODUCTION' : types[0].value
  }
}

const resolveDefaultOperator = () => {
  const user = authState.user
  if (user) {
    const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim()
    if (fullName) return fullName
    if (user.username) return user.username
    if (user.email) return user.email
  }
  return ''
}

const defaultOperatorName = ref(resolveDefaultOperator())

const findSelectedPlanTarget = () => {
  const productId = record.value.product_id
  if (!productId) return null
  const productIdStr = String(productId)
  const candidates = [
    ...(Array.isArray(displayProductList.value) ? displayProductList.value : []),
    ...(Array.isArray(currentProductList.value) ? currentProductList.value : []),
    ...(Array.isArray(allPlanProducts.value) ? allPlanProducts.value : []),
  ]
  return candidates.find((item) => String(item?.product) === productIdStr) || null
}

const findSelectedProductCandidate = () => {
  const productId = String(record.value.product_id || '').trim()
  if (!productId) return null
  const candidates = [
    findSelectedPlanTarget(),
    ...(Array.isArray(displayProductList.value) ? displayProductList.value : []),
    ...(Array.isArray(currentProductList.value) ? currentProductList.value : []),
    ...(Array.isArray(allPlanProducts.value) ? allPlanProducts.value : []),
    ...(Array.isArray(manualProducts.value) ? manualProducts.value : []),
  ]
  return candidates.find((item) => {
    const candidateId = item?.product ?? item?.id
    return candidateId != null && String(candidateId) === productId
  }) || null
}

const hasRequiredProductionFields = ({ requireQty = true } = {}) => {
  if (!hasSelectedProduct()) return false
  if (requireQty) {
    if (shouldUseCounterInput.value) {
      const counterQtyValue = Number(record.value.counter_qty)
      const hasCounterQty = record.value.counter_qty !== null && record.value.counter_qty !== '' && !Number.isNaN(counterQtyValue)
      if (!hasCounterQty) return false
      if (counterQtyError.value) return false
    }
    const qtyValue = Number(record.value.qty)
    const hasQty = record.value.qty !== null && record.value.qty !== '' && !Number.isNaN(qtyValue)
    if (!hasQty) return false
    const allowZero = isPauseOperatorAction.value || (isEndOperatorAction.value && hasFilledText(record.value.remarks))
    if (allowZero) { if (qtyValue < 0) return false }
    else if (qtyValue <= 0) return false
  }
  if (!hasFilledText(record.value.operator_name)) return false
  return true
}

const canSubmit = computed(() => {
  if (!selectedProcessId.value || !record.value.record_type) return false
  if (isOperatorActionMode.value) {
    if (!findSelectedPlanTarget()) return false
    if (requiresOperatorActionReason.value && !hasFilledText(record.value.operator_action_reason)) return false
    if (requiresTempEndOtherRemarks.value && !hasFilledText(record.value.remarks)) return false
    return hasRequiredProductionFields({ requireQty: shouldShowQtyInput.value })
  }
  if (record.value.record_type === 'PRODUCTION') {
    if (!hasEffectiveOperatorAction()) return false
    if (requiresOperatorActionReason.value && !hasFilledText(record.value.operator_action_reason)) return false
    if (requiresTempEndOtherRemarks.value && !hasFilledText(record.value.remarks)) return false
    return hasRequiredProductionFields({ requireQty: shouldShowQtyInput.value })
  }
  if (record.value.record_type === 'SCRAP') {
    if (!hasRequiredProductionFields()) return false
    if (!record.value.reason) return false
    if (record.value.reason === 'OTHER' && !(record.value.reason_detail || '').trim()) return false
    if (!(record.value.disposition_status || '').trim()) return false
    if (record.value.is_production_recorded === '') return false
    if (!scrapRelationFilter.value) return false
    return true
  }
  if (record.value.record_type === 'EQUIPMENT_STATE') {
    if (!record.value.equipment_state) return false
    return true
  }
  return false
})

// ──────────────────────────────
// 操作
// ──────────────────────────────
const selectOperatorAction = (action) => {
  selectedOperatorAction.value = selectedOperatorAction.value === action ? '' : action
}
const isOperatorActionActive = (action) =>
  String(effectiveOperatorAction.value || '').toUpperCase() === String(action || '').toUpperCase()

const selectPlannedProduct = (p) => {
  const nextProductId = p?.product ?? ''
  const nextGanttPlanId = p?.gantt_plan_id || ''
  const isSameProduct = String(record.value.product_id || '') === String(nextProductId || '')
  const isSameGanttPlan = selectedGanttPlanId.value === nextGanttPlanId
  if (isSameProduct && isSameGanttPlan) {
    record.value.product_id = ''
    record.value.product_code = ''
    selectedGanttPlanId.value = ''
    if (record.value.record_type === 'PRODUCTION') {
      record.value.qty = null
      record.value.operator_action_reason = ''
      selectedOperatorAction.value = ''
    }
    return
  }
  record.value.product_id = p.product || p.id || ''
  record.value.product_code = p.product_code || ''
  selectedGanttPlanId.value = nextGanttPlanId
  manualProduct.value = false
  if (record.value.record_type === 'PRODUCTION') record.value.qty = null
  applyScrapTypeDefaults(p)
}

const cancelSelection = () => {
  record.value.product_id = ''
  record.value.product_code = ''
  selectedGanttPlanId.value = ''
  selectedOperatorAction.value = ''
  closeProductPhotoDialog()
}

const toggleManualProduct = async () => {
  if (!manualProduct.value) {
    const pw = prompt('手入力するにはパスワードを入力してください')
    if (!pw) return
    try {
      await api.systemSettings.verifyPlanQtyPassword({ password: pw })
    } catch (e) {
      const detail = e?.response?.data?.detail || 'パスワードが正しくありません。'
      alert(detail)
      return
    }
  }
  manualProduct.value = !manualProduct.value
  if (manualProduct.value) {
    record.value.product_id = ''
    record.value.product_code = ''
    selectedGanttPlanId.value = ''
    loadManualProducts(selectedProcessId.value)
  } else {
    record.value.product_id = ''
    record.value.product_code = ''
    selectedGanttPlanId.value = ''
  }
  closeProductPhotoDialog()
}

const revokeProductPhotoPreviewUrl = () => {
  if (productPhotoPreviewUrl.value && productPhotoPreviewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(productPhotoPreviewUrl.value)
  }
}

const openProductPhotoDialog = (mode = 'view') => {
  if (!canOpenProductPhotoDialog.value) return
  productPhotoDialogMode.value = mode
  revokeProductPhotoPreviewUrl()
  productPhotoPreviewUrl.value = ''
  showProductPhotoDialog.value = true
}

const closeProductPhotoDialog = () => {
  showProductPhotoDialog.value = false
  productPhotoDialogMode.value = 'view'
  revokeProductPhotoPreviewUrl()
  productPhotoPreviewUrl.value = ''
}

const openProductCamera = () => {
  if (!record.value.product_id) {
    showToast('マスタ登録品番のみ写真を保存できます', 'error')
    return
  }
  if (productPhotoUploading.value) return
  productPhotoInputRef.value?.click()
}

const onProductPhotoSelected = async (event) => {
  const file = event?.target?.files?.[0]
  const productId = record.value.product_id
  if (!file || !productId) return

  let objectUrl = ''
  try {
    objectUrl = URL.createObjectURL(file)
    productPhotoPreviewUrl.value = objectUrl
  } catch {
    objectUrl = ''
  }

  productPhotoUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.products.uploadProductImage(productId, formData)
    const imageUrl = String(res?.data?.image_url || '').trim()
    if (imageUrl) {
      productImageMap.value = {
        ...productImageMap.value,
        [productId]: imageUrl,
        [String(productId)]: imageUrl,
      }
      if (!objectUrl) productPhotoPreviewUrl.value = imageUrl
    }
    showToast('製品写真を保存しました')
  } catch (e) {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl)
      objectUrl = ''
    }
    productPhotoPreviewUrl.value = ''
    showToast(e?.response?.data?.detail || '製品写真の保存に失敗しました', 'error')
  } finally {
    productPhotoUploading.value = false
    if (event?.target) event.target.value = ''
  }
}

const onCurrentTimeToggle = () => {
  if (!timeSlots.value.length && filterCurrentTime.value) { loadPlannedProducts(); return }
  if (!filterCurrentTime.value && isFloorLineSelected.value) { loadPlannedProducts(); return }
  if (filterCurrentTime.value && activeSlotIndex.value === null && timeSlots.value.length) activeSlotIndex.value = 0
  applyTimeSlotFilter()
}

async function onTomorrowToggle() {
  if (showTomorrow.value) showYesterday.value = false
  await reloadAfterDateChange()
}

async function onYesterdayToggle() {
  if (showYesterday.value) showTomorrow.value = false
  await reloadAfterDateChange()
}

async function reloadAfterDateChange() {
  if (!selectedProcessId.value) return
  if (!calendarWorkingDays.value) await loadCalendarWorkingDays()
  currentPage.value = 1
  loadPlannedProducts()
  loadStartedProductIds()
  loadRecentRecords()
}

// ──────────────────────────────
// ページネーション
// ──────────────────────────────
function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }
function goFirstPage() { currentPage.value = 1 }
function goLastPage() { currentPage.value = totalPages.value }

const findSlotIndexByProduct = (productId) => {
  const pid = String(productId || '').trim()
  if (!pid || !Array.isArray(timeSlots.value) || !timeSlots.value.length) return -1
  return timeSlots.value.findIndex((slot) =>
    Array.isArray(slot?.items) && slot.items.some((it) => String(it?.product || '').trim() === pid)
  )
}

const moveProductBy = (delta) => {
  const list = navProductItems.value
  if (!list.length) return
  const baseIdx = currentNavIndex.value < 0 ? 0 : currentNavIndex.value
  const nextIdx = Math.min(Math.max(baseIdx + delta, 0), list.length - 1)
  if (nextIdx === baseIdx) return
  const target = list[nextIdx]
  const targetId = String(target?.product || target?.id || '')
  if (!targetId) return
  if (filterCurrentTime.value) {
    const slotIdx = findSlotIndexByProduct(targetId)
    if (slotIdx >= 0) {
      activeSlotIndex.value = slotIdx
      applyTimeSlotFilter()
    }
  }
  selectPlannedProduct(target)
}


// ──────────────────────────────
// リセット
// ──────────────────────────────
const resetForm = () => {
  record.value = {
    record_type: 'PRODUCTION', product_id: '', product_code: '', counter_qty: null, qty: null,
    operator_action_reason: '', operator_action_reason_detail: '',
    reason: '', reason_detail: '', disposition_status: '', is_production_recorded: '',
    equipment_state: '', batch_no: '', operator_name: defaultOperatorName.value || '', remarks: '',
  }
  manualProduct.value = false
  selectedGanttPlanId.value = ''
  selectedOperatorAction.value = ''
  scrapRelationFilter.value = ''
  scrapSearchText.value = ''
  ensureDefaultRecordType()
}

const prepareEquipmentStateForm = () => {
  const productId = record.value.product_id
  const productCode = record.value.product_code
  record.value.record_type = 'EQUIPMENT_STATE'
  record.value.product_id = productId
  record.value.product_code = productCode
  record.value.counter_qty = null
  record.value.qty = null
  record.value.batch_no = ''
  record.value.operator_action_reason = ''
  record.value.operator_action_reason_detail = ''
  record.value.reason = ''
  record.value.reason_detail = ''
  record.value.disposition_status = ''
  record.value.is_production_recorded = ''
  record.value.equipment_state = ''
  record.value.remarks = ''
  selectedOperatorAction.value = ''
}

const isEquipmentTroubleReason = (value) => String(value || '').trim() === PAUSE_REASON_EQUIPMENT_TROUBLE

// ──────────────────────────────
// 連産品
// ──────────────────────────────
const clearSelectedCoproductNotice = () => {
  selectedCoproductChildren.value = []
  selectedCoproductParentCode.value = ''
  selectedCoproductNoticeLoading.value = false
}
const invalidateSelectedCoproductNotice = () => {
  selectedCoproductNoticeRequestSeq += 1
  clearSelectedCoproductNotice()
}
const isStProductCode = (productCode) => String(productCode || '').trim().toUpperCase().startsWith('ST')

const getBomTreeCached = async (productId) => {
  if (shouldBlockBomService()) return null
  const cacheKey = String(productId || '').trim()
  if (!cacheKey) return null
  if (bomTreeCache.has(cacheKey)) return bomTreeCache.get(cacheKey)
  try {
    const res = await api.bomService.getBomTree(productId)
    const tree = res?.data || null
    bomTreeCache.set(cacheKey, tree)
    return tree
  } catch { bomTreeCache.set(cacheKey, null); return null }
}

const getRelatedProductsCached = async (processId) => {
  const cacheKey = String(processId || '').trim()
  if (!cacheKey) return []
  if (relatedProductsCacheByProcess.has(cacheKey)) return relatedProductsCacheByProcess.get(cacheKey) || []
  try {
    const res = await api.processes.getRelatedProducts(processId)
    const list = Array.isArray(res?.data) ? res.data : []
    relatedProductsCacheByProcess.set(cacheKey, list)
    return list
  } catch { relatedProductsCacheByProcess.set(cacheKey, []); return [] }
}

const enrichCoproductParentsForList = async (candidates, processId) => {
  const list = Array.isArray(candidates) ? [...candidates] : []
  if (!processId || list.length === 0) return list
  const relatedProducts = await getRelatedProductsCached(processId)
  const coproductParents = relatedProducts.filter((p) => normalizeRelationType(p?.relation_type) === 'coproduct_parent')
  if (coproductParents.length === 0) return list
  const existingProductIds = new Set(list.map((it) => String(it?.product || '').trim()).filter(Boolean))
  for (const parent of coproductParents) {
    const parentId = String(parent?.id || '').trim()
    if (!parentId || existingProductIds.has(parentId)) continue
    const tree = await getBomTreeCached(parent.id)
    if (!tree?.is_coproduct || !Array.isArray(tree.children) || tree.children.length === 0) continue
    const childIdSet = new Set(tree.children.map((ch) => String(ch?.product_id || '').trim()).filter(Boolean))
    if (childIdSet.size === 0) continue
    const matchedChildren = list.filter((it) => childIdSet.has(String(it?.product || '').trim()))
    if (matchedChildren.length === 0) continue
    const base = matchedChildren[0] || {}
    const planQty = matchedChildren.reduce((maxVal, it) => { const qty = Number(it?.plan_qty ?? 0); return Number.isFinite(qty) ? Math.max(maxVal, qty) : maxVal }, 0)
    list.push({ ...base, product: parent.id, product_code: parent.product_code || '', product_name: parent.product_name || '', relation_type: 'coproduct_parent', plan_qty: planQty })
    existingProductIds.add(parentId)
  }
  return list
}

const loadSelectedCoproductNotice = async () => {
  if (record.value.record_type !== 'PRODUCTION') { invalidateSelectedCoproductNotice(); return }
  const productId = String(record.value.product_id || '').trim()
  if (!productId) { invalidateSelectedCoproductNotice(); return }
  const selectedProduct = findSelectedProductCandidate()
  const productCode = String(selectedProduct?.product_code || record.value.product_code || '').trim()
  if (productCode && !isStProductCode(productCode)) { invalidateSelectedCoproductNotice(); return }
  const requestSeq = ++selectedCoproductNoticeRequestSeq
  selectedCoproductNoticeLoading.value = true
  try {
    const tree = await getBomTreeCached(productId)
    if (requestSeq !== selectedCoproductNoticeRequestSeq) return
    if (!tree?.is_coproduct || !Array.isArray(tree.children) || tree.children.length === 0) { clearSelectedCoproductNotice(); return }
    const childMap = new Map()
    tree.children.forEach((child) => {
      if (!child?.product_id) return
      const key = String(child.product_id)
      if (childMap.has(key)) return
      childMap.set(key, { product_id: child.product_id, product_code: child.product_code || String(child.product_id), product_name: child.product_name || '' })
    })
    if (childMap.size === 0) { clearSelectedCoproductNotice(); return }
    selectedCoproductParentCode.value = String(tree.product_code || productCode || '').trim()
    selectedCoproductChildren.value = Array.from(childMap.values())
  } finally {
    if (requestSeq === selectedCoproductNoticeRequestSeq) selectedCoproductNoticeLoading.value = false
  }
}

// ──────────────────────────────
// 保存
// ──────────────────────────────
const submitRecord = async () => {
  if (!canSubmit.value) return
  if (!window.confirm(t('processInput.alert.confirmSubmit'))) return
  submitting.value = true
  let submittedOperatorAction = ''
  let submittedOperatorProductId = ''
  let moveToEquipmentState = false
  try {
    const data = { process_id: selectedProcessId.value, record_type: record.value.record_type }
    if (isOperatorActionMode.value) {
      const selectedPlanTarget = findSelectedPlanTarget()
      if (!selectedPlanTarget?.product) return
      data.record_type = 'OPERATOR_ACTION'
      data.qty = 0
      data.product_id = selectedPlanTarget.product
      const operatorName = (record.value.operator_name || defaultOperatorName.value || '').trim()
      if (operatorName) data.operator_name = operatorName
      const activeSlot = filterCurrentTime.value && timeSlots.value.length ? timeSlots.value[activeSlotIndex.value ?? 0] : null
      const targetStartIso = toIsoDateTimeOrNull(selectedPlanTarget.start) || toIsoDateTimeOrNull(activeSlot?.start)
      const targetEndIso = toIsoDateTimeOrNull(selectedPlanTarget.end) || toIsoDateTimeOrNull(activeSlot?.end)
      data.event_data = {
        action: effectiveOperatorAction.value,
        two_person_same_equipment: isTwoPersonSameEquipmentMode.value ? true : undefined,
        operator_user_id: route.query.operator_user_id ? String(route.query.operator_user_id) : undefined,
        plan_target: {
          line_id: selectedLineId.value || null, process_id: selectedProcessId.value || null,
          plan_date: selectedPlanTarget.plan_date || currentDateYmd.value || null,
          product_id: selectedPlanTarget.product || null, product_code: selectedPlanTarget.product_code || '',
          product_name: selectedPlanTarget.product_name || '', plan_qty: selectedPlanTarget.plan_qty ?? null,
          actual_qty: selectedPlanTarget.actual_qty ?? null, slot_start: targetStartIso, slot_end: targetEndIso,
          slot_label: slotLabel.value || null,
        },
      }
      submittedOperatorAction = String(effectiveOperatorAction.value || '').toUpperCase()
      submittedOperatorProductId = String(selectedPlanTarget.product || '')
      if (submittedOperatorAction === 'PAUSE') { data.qty = record.value.qty; data.batch_no = record.value.batch_no; data.event_data.pause_qty = record.value.qty }
      if (submittedOperatorAction === 'END') { data.production_qty = record.value.qty; data.batch_no = record.value.batch_no }
      if (requiresOperatorActionReason.value) {
        let reasonText = (record.value.operator_action_reason || '').trim()
        if (submittedOperatorAction === 'TEMP_END' && isTempEndReasonOtherSelected.value) reasonText = (record.value.remarks || '').trim()
        data.event_data.operator_action_reason = reasonText
        if (submittedOperatorAction === 'PAUSE') { data.event_data.pause_reason = reasonText; moveToEquipmentState = isEquipmentTroubleReason(reasonText) }
        else if (submittedOperatorAction === 'TEMP_END') data.event_data.temp_end_reason = reasonText
      }
    } else {
      if (record.value.product_id) data.product_id = record.value.product_id
      else if ((record.value.product_code || '').trim()) data.product_code = record.value.product_code.trim()
      if (record.value.record_type === 'PRODUCTION' || record.value.record_type === 'SCRAP') {
        data.qty = record.value.qty; data.batch_no = record.value.batch_no; data.operator_name = record.value.operator_name
      } else if (record.value.record_type === 'EQUIPMENT_STATE') {
        data.equipment_state = record.value.equipment_state; data.qty = 0
      }
      if (record.value.record_type === 'SCRAP' && record.value.reason) {
        const currentProduct =
          scrapProducts.value.find((p) => String(p.product) === String(record.value.product_id)) ||
          manualProducts.value.find((p) => String(p.id) === String(record.value.product_id))
        const eventData = {
          reason: record.value.reason, disposition_status: record.value.disposition_status || 'REJECTED',
          is_production_recorded: record.value.is_production_recorded || false,
          relation_type: currentProduct?.relation_type || '',
        }
        if (record.value.reason === 'OTHER' && (record.value.reason_detail || '').trim()) eventData.reason_detail = record.value.reason_detail.trim()
        data.event_data = eventData
      }
    }
    data.remarks = record.value.remarks
    const targetWorkDate = (workDateStr.value || '').trim()
    if (isWorkDateChanged.value) {
      if (!workDateChangeReason.value) {
        alert('作業日が今日と異なります。変更理由を選択してください。')
        return
      }
      if (workDateChangeReason.value === 'OTHER' && !(workDateChangeReasonDetail.value || '').trim()) {
        alert('その他の場合、理由の入力は必須です。')
        return
      }
      const reasonText = workDateChangeReason.value === 'OTHER' ? workDateChangeReasonDetail.value.trim() : workDateChangeReason.value
      if (!window.confirm(`作業日 ${targetWorkDate} で保存しますか？\n理由: ${reasonText}`)) return
      data.work_date = targetWorkDate
      data.remarks = ((data.remarks || '') + `\n【作業日変更: ${targetWorkDate}】${reasonText}`).trim()
    }
    const res = await api.processRealtime.create(data)
    if (submittedOperatorProductId) {
      const nextStarted = new Set(startedProductIds.value)
      const nextLatestOperatorAction = new Map(latestOperatorActionByProduct.value)
      if (submittedOperatorAction) nextLatestOperatorAction.set(submittedOperatorProductId, submittedOperatorAction)
      if (['END', 'TEMP_END', 'CANCEL'].includes(submittedOperatorAction)) nextStarted.delete(submittedOperatorProductId)
      else if (activeOperatorActions.has(submittedOperatorAction)) nextStarted.add(submittedOperatorProductId)
      startedProductIds.value = nextStarted
      latestOperatorActionByProduct.value = nextLatestOperatorAction
      startedProductIdsLoaded.value = true
    }
    const overrun = res.data?.plan_overrun_warning
    if (overrun) {
      alert(`⚠ 計画超過\n${overrun.process_name} / ${overrun.product_code} ${overrun.product_name}\n計画: ${overrun.plan_qty} → 実績: ${overrun.actual_qty} （${overrun.over_qty} 超過）\n数量を確認してください。`)
    } else {
      showToast(t('processInput.alert.saved'))
    }
    if (moveToEquipmentState) prepareEquipmentStateForm()
    else resetForm()
    await loadPlannedProducts()
    await loadStartedProductIds()
    await loadRecentRecords()
  } catch (error) {
    console.error('記録登録エラー:', error)
    const responseData = error?.response?.data
    const message = responseData?.detail
      || Object.values(responseData || {}).flat().find((value) => typeof value === 'string')
      || t('processInput.alert.saveFailed')
    alert(message)
  } finally {
    submitting.value = false
  }
}

// ──────────────────────────────
// データ読み込み
// ──────────────────────────────
const onProcessChange = () => {
  const proc = processes.value.find((p) => String(p.id) === String(selectedProcessId.value))
  if (proc?.line) selectedLineId.value = String(proc.line)
  productionProducts.value = []; scrapProducts.value = []; allPlanProducts.value = []; allScrapProducts.value = []
  dailyProcessTargets.value = []
  timeSlots.value = []; activeSlotIndex.value = null; defaultProductId.value = null
  productImageMap.value = {}; productMetaMap.value = {}
  invalidateSelectedCoproductNotice()
  resetForm()
  manualProducts.value = []; manualProductsLoaded.value = false; manualProductsProcessId.value = null
  loadPlannedProducts(); loadStartedProductIds(); loadRecentRecords()
}

const onLineChange = () => {
  selectedProcessId.value = ''; recentRecords.value = []; productionProducts.value = []; scrapProducts.value = []
  allPlanProducts.value = []; allScrapProducts.value = []; timeSlots.value = []; activeSlotIndex.value = null
  dailyProcessTargets.value = []
  startedProductIds.value = new Set(); startedProductIdsLoaded.value = false
  latestOperatorActionByProduct.value = new Map(); defaultProductId.value = null
  productImageMap.value = {}; productMetaMap.value = {}
  invalidateSelectedCoproductNotice()
  manualProducts.value = []; manualProductsLoaded.value = false; manualProductsProcessId.value = null
  resetForm()
  loadCalendarWorkingDays()
}

const loadStartedProductIds = async () => {
  startedProductIdsLoaded.value = false
  latestOperatorActionByProduct.value = new Map()
  if (!selectedProcessId.value) {
    startedProductIds.value = new Set(); latestOperatorActionByProduct.value = new Map()
    startedProductIdsLoaded.value = true; return
  }
  try {
    const res = await api.processRealtime.list({ process_id: selectedProcessId.value, record_type: 'OPERATOR_ACTION', limit: 2000, page_size: 2000 })
    const items = res.data.results || res.data || []
    const latestActionByProduct = new Map()
    ;(Array.isArray(items) ? items : []).forEach((rec) => {
      if (isTwoPersonSameEquipmentMode.value) {
        if (!rec?.event_data?.two_person_same_equipment) return
        const scopeUserId = operatorScopeUserId.value
        if (scopeUserId) {
          const recUserId = String(rec?.event_data?.operator_user_id || '').trim()
          if (recUserId !== scopeUserId) return
        } else {
          const scope = operatorScopeName.value
          if (scope) {
            const recOperator = normalizeOperatorName(rec?.operator_name || rec?.event_data?.operator_name || '')
            if (recOperator !== scope) return
          }
        }
      }
      const pid = getOperatorActionProductId(rec)
      if (pid === null || pid === undefined || pid === '') return
      const productId = String(pid)
      if (latestActionByProduct.has(productId)) return
      const action = rec.event_data?.action || rec.event_data?.operator_action || rec.event_data?.action_type || ''
      latestActionByProduct.set(productId, String(action).toUpperCase())
    })
    const started = new Set()
    latestActionByProduct.forEach((action, productId) => { if (activeOperatorActions.has(action)) started.add(productId) })
    startedProductIds.value = started
    latestOperatorActionByProduct.value = latestActionByProduct
    startedProductIdsLoaded.value = true
  } catch {
    startedProductIds.value = new Set(); latestOperatorActionByProduct.value = new Map()
    startedProductIdsLoaded.value = true
  }
}

const loadRecentRecords = async () => {
  if (!selectedProcessId.value) return
  try {
    const res = await api.processRealtime.list({ process_id: selectedProcessId.value, limit: 10 })
    recentRecords.value = res.data.results || res.data || []
    const lastProduction = recentRecords.value.find(r => r.record_type === 'PRODUCTION' && r.product)
    defaultProductId.value = lastProduction ? lastProduction.product : defaultProductId.value
    await loadGanttPlanQty()
  } catch (error) { console.error('最近の記録取得エラー:', error) }
}

const loadGanttPlanQty = async () => {
  if (!selectedLineId.value || !selectedProcessId.value) { ganttPlanQtyMap.value = {}; return }
  const records = Array.isArray(recentRecords.value) ? recentRecords.value : []
  const dateSet = new Set()
  for (const rec of records) { const ts = rec?.timestamp; if (ts) dateSet.add(formatISODate(getBusinessDate(new Date(ts)))) }
  if (!dateSet.size) { ganttPlanQtyMap.value = {}; return }
  try {
    const res = await api.processRealtime.getGanttPlanQty({ line_id: selectedLineId.value, process_id: selectedProcessId.value, dates: [...dateSet].join(',') })
    ganttPlanQtyMap.value = res.data || {}
  } catch { ganttPlanQtyMap.value = {} }
}

const parseSeqNo = (raw) => {
  if (raw === null || raw === undefined || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

const productSeqKey = (item) => {
  const pid = String(item?.product || '')
  const seq = parseSeqNo(item?.sequence_no)
  const planId = item?.gantt_plan_id || ''
  if (planId) {
    return seq !== null ? `${pid}_seq${seq}_${planId}` : `${pid}_${planId}`
  }
  return seq !== null ? `${pid}_seq${seq}` : pid
}

const mergeProductionProductsByProduct = (items) => {
  const mergedMap = new Map()
  ;(Array.isArray(items) ? items : []).forEach((item) => {
    if (!item || item.product === null || item.product === undefined || item.product === '') return
    const key = productSeqKey(item)
    if (!mergedMap.has(key)) {
      mergedMap.set(key, {
        ...item,
        plan_qty: toSafeNumber(item.plan_qty),
        actual_qty: toSafeNumber(item.actual_qty),
        sequence_no: parseSeqNo(item.sequence_no),
      })
      return
    }
    const current = mergedMap.get(key)
    current.plan_qty = toSafeNumber(current.plan_qty) + toSafeNumber(item.plan_qty)
    current.actual_qty = Math.max(toSafeNumber(current.actual_qty), toSafeNumber(item.actual_qty))
  })
  return Array.from(mergedMap.values())
}

const buildTotalActualByProduct = (items) => {
  const totalMap = new Map()
  ;(Array.isArray(items) ? items : []).forEach((item) => {
    if (!item || item.product === null || item.product === undefined || item.product === '') return
    const key = String(item.product)
    const qty = toSafeNumber(item.actual_qty)
    if (!totalMap.has(key) || qty > toSafeNumber(totalMap.get(key))) totalMap.set(key, qty)
  })
  return totalMap
}

const buildPlanBeforeActiveSlotByProduct = (slots, activeIndex) => {
  const planBeforeMap = new Map()
  const upperBound = Math.max(Math.min(Number(activeIndex) || 0, slots.length), 0)
  for (let idx = 0; idx < upperBound; idx += 1) {
    mergeProductionProductsByProduct(slots[idx]?.items || []).forEach((item) => {
      const key = String(item?.product || ''); if (!key) return
      planBeforeMap.set(key, toSafeNumber(planBeforeMap.get(key)) + toSafeNumber(item?.plan_qty))
    })
  }
  return planBeforeMap
}

const applySlotActualProgress = (slotItems, planBeforeMap, totalActualMap, totalPlanByProduct) => {
  return (Array.isArray(slotItems) ? slotItems : []).map((item) => {
    const key = String(item?.product || ''); if (!key) return item
    const totalActual = toSafeNumber(totalActualMap.get(key))
    const plannedBefore = toSafeNumber(planBeforeMap.get(key))
    const slotActual = Math.max(totalActual - plannedBefore, 0)
    const planQty = toSafeNumber(item.plan_qty)
    const totalPlan = toSafeNumber(totalPlanByProduct?.get(key))
    const isLastSlotForProduct = (plannedBefore + planQty) >= totalPlan
    return { ...item, actual_qty: isLastSlotForProduct ? slotActual : Math.min(slotActual, planQty) }
  })
}

const buildActualQtyLookupByProductProcess = (items, processId) => {
  const result = new Map()
  ;(Array.isArray(items) ? items : []).forEach((item) => {
    if (!item || item.product == null) return
    const key = `${item.product}_${processId}`
    const qty = toSafeNumber(item.actual_qty)
    const seqNo = item.sequence_no === null || item.sequence_no === undefined || item.sequence_no === '' ? null : Number(item.sequence_no)
    const priority = seqNo === 0 ? 2 : 1
    const current = result.get(key)
    if (!current || priority > current.priority || (priority === current.priority && qty > current.qty)) result.set(key, { qty, priority })
  })
  const qtyMap = new Map()
  result.forEach((value, key) => qtyMap.set(key, value.qty))
  return qtyMap
}

const buildPlanQtyMapFromSlots = (slots, processId) => {
  const qtyMap = new Map()
  ;(Array.isArray(slots) ? slots : []).forEach((slot) => {
    ;(Array.isArray(slot?.items) ? slot.items : []).forEach((item) => {
      const productId = item?.product
      if (productId === null || productId === undefined || productId === '') return
      const key = `${productId}_${processId}`
      qtyMap.set(key, toSafeNumber(qtyMap.get(key)) + toSafeNumber(item?.plan_qty))
    })
  })
  return qtyMap
}

const buildSequenceMapFromSlots = (slots, processId) => {
  const seqMap = new Map()
  ;(Array.isArray(slots) ? slots : []).forEach((slot) => {
    ;(Array.isArray(slot?.items) ? slot.items : []).forEach((item) => {
      const productId = item?.product
      if (productId === null || productId === undefined || productId === '') return
      const seqRaw = item?.sequence_no
      const seqNo = seqRaw === null || seqRaw === undefined || seqRaw === '' ? null : Number(seqRaw)
      if (!Number.isFinite(seqNo) || seqNo <= 0) return
      const key = `${productId}_${processId}`
      const current = seqMap.get(key)
      if (!Number.isFinite(current)) seqMap.set(key, seqNo)
      else seqMap.set(key, Math.min(current, seqNo))
    })
  })
  return seqMap
}

const buildActualQtyLookupByProductCode = (items) => {
  const result = new Map()
  ;(Array.isArray(items) ? items : []).forEach((item) => {
    if (!item) return
    const code = String(item.product_code || '').trim()
    if (!code) return
    const qty = toSafeNumber(item.actual_qty)
    const seqRaw = item.sequence_no
    const seqNo = seqRaw === null || seqRaw === undefined || seqRaw === '' ? null : Number(seqRaw)
    const priority = seqNo === 0 ? 2 : 1
    const current = result.get(code)
    if (!current || priority > current.priority || (priority === current.priority && qty > current.qty)) {
      result.set(code, { qty, priority })
    }
  })
  const qtyMap = new Map()
  result.forEach((value, key) => qtyMap.set(key, value.qty))
  return qtyMap
}

const ensureStartedProductsVisible = (items) => {
  const base = [...(Array.isArray(items) ? items : [])]
  if (!startedProductIdsLoaded.value || !startedProductIds.value?.size) return base
  const existingIds = new Set(base.map((item) => String(item?.product || '')).filter((id) => id !== ''))
  const allMerged = mergeProductionProductsByProduct(allPlanProducts.value)
  const allMap = new Map(allMerged.map((item) => [String(item?.product || ''), item]).filter(([id]) => id !== ''))
  startedProductIds.value.forEach((productId) => {
    const key = String(productId || ''); if (!key || existingIds.has(key)) return
    const src = allMap.get(key); if (!src) return
    base.push({ ...src }); existingIds.add(key)
  })
  return base
}

const filterFloorProductsByDisplayMap = async (lineId, processId, items, forceFloorMode = false) => {
  if (filterCurrentTime.value) return Array.isArray(items) ? items : []
  if (!forceFloorMode && !isFloorLineSelected.value) return Array.isArray(items) ? items : []
  if (!lineId || !processId) return Array.isArray(items) ? items : []
  try {
    const res = await api.ganttDisplayProductMaps.getGanttDisplayProductMaps({ line: lineId, process: processId, page_size: 500 })
    const rows = res.data?.results || res.data || []
    const allowedProductIds = new Set((Array.isArray(rows) ? rows : []).map((row) => String(row?.display_product || '').trim()).filter(Boolean))
    if (!allowedProductIds.size) return []
    return (Array.isArray(items) ? items : []).filter((item) => allowedProductIds.has(String(item?.product || '').trim()))
  } catch { return Array.isArray(items) ? items : [] }
}

const mergeMissingFloorMapProducts = async (lineId, processId, items) => {
  if (filterCurrentTime.value) return Array.isArray(items) ? items : []
  if (!lineId || !processId) return Array.isArray(items) ? items : []
  try {
    const res = await api.ganttDisplayProductMaps.getGanttDisplayProductMaps({ line: lineId, process: processId, page_size: 500 })
    const rows = Array.isArray(res.data?.results || res.data) ? (res.data?.results || res.data) : []
    const base = Array.isArray(items) ? [...items] : []
    const exists = new Set(base.map((it) => String(it?.product || '').trim()).filter(Boolean))
    rows.forEach((row) => {
      const productId = String(row?.display_product || '').trim()
      if (!productId || exists.has(productId)) return
      base.push({ plan_date: currentDateYmd.value, product: row.display_product, product_code: row.display_product_code || '', product_name: row.display_product_name || '', process: processId, plan_qty: 0, actual_qty: 0 })
      exists.add(productId)
    })
    return base
  } catch { return Array.isArray(items) ? items : [] }
}

const applyTimeSlotFilter = () => {
  const slots = timeSlots.value || []
  let index = activeSlotIndex.value
  if (slots.length === 0 || !filterCurrentTime.value) {
    const mergedAll = mergeProductionProductsByProduct(allPlanProducts.value)
    productionProducts.value = ensureStartedProductsVisible(mergedAll)
    scrapProducts.value = [...allScrapProducts.value]
    return
  }
  if (index === null || index < 0) index = 0
  if (index > slots.length - 1) index = slots.length - 1
  activeSlotIndex.value = index
  const mergedSlotItems = mergeProductionProductsByProduct(slots[index]?.items || [])
  const planBeforeMap = buildPlanBeforeActiveSlotByProduct(slots, index)
  const planDerivedMap = buildTotalActualByProduct(allPlanProducts.value)
  const backlogActuals = actualQtyByProductFromBacklog.value
  const totalActualMap = new Map(planDerivedMap)
  backlogActuals.forEach((qty, pid) => totalActualMap.set(pid, qty))
  const totalPlanByProduct = new Map()
  allPlanProducts.value.forEach((item) => {
    const pid = String(item?.product || ''); if (!pid) return
    totalPlanByProduct.set(pid, toSafeNumber(totalPlanByProduct.get(pid)) + toSafeNumber(item?.plan_qty))
  })
  const slotItems = applySlotActualProgress(mergedSlotItems, planBeforeMap, totalActualMap, totalPlanByProduct)
  productionProducts.value = [...slotItems]
  const slotProductIds = new Set(slotItems.map((p) => String(p.product)))
  let filteredScrap = allScrapProducts.value.filter((p) => slotProductIds.has(String(p.product)))
  if (!filteredScrap.length) filteredScrap = [...allScrapProducts.value]
  scrapProducts.value = filteredScrap
}

const buildCurrentTimePlanItems = async (lineId, processId, existingItems = []) => {
  try {
    const targetDate = currentDateYmd.value
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({ line: lineId, plan_date__gte: targetDate, plan_date__lte: targetDate, page_size: 1000 })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!Array.isArray(rawPlans) || !rawPlans.length) return { items: [], hasPlan: false }
    const actualLookup = buildActualQtyLookupByProductProcess(existingItems, processId)
    const now = new Date(); const map = new Map()
    rawPlans.forEach((plan) => {
      const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
      processes.forEach((pp) => {
        if (String(pp.process_id) != String(processId)) return
        const start = new Date(pp.start_time); const end = new Date(pp.end_time)
        if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return
        if (now < start || now > end) return
        const productId = pp.output_product_id ?? plan.product; if (!productId) return
        const actualKey = `${productId}_${processId}`
        const key = `${productId}_${processId}_${plan.plan_id || ''}`; if (map.has(key)) return
        map.set(key, {
          plan_date: targetDate, product: productId, product_code: pp.output_product_code || plan.product_code || '',
          product_name: pp.output_product_name || plan.product_name || '', process: processId,
          plan_qty: pp.quantity ?? plan.plan_qty ?? 0, actual_qty: actualLookup.has(actualKey) ? actualLookup.get(actualKey) : 0,
          sequence_no: plan.sequence_no ?? null, gantt_plan_id: plan.plan_id || null,
        })
      })
    })
    return { items: Array.from(map.values()), hasPlan: true }
  } catch { return { items: [], hasPlan: false } }
}

const buildPlanTimeSlots = async (lineId, processId, existingItems = []) => {
  try {
    const targetDate = currentDateYmd.value
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({ line: lineId, plan_date__gte: targetDate, plan_date__lte: targetDate, page_size: 1000 })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!Array.isArray(rawPlans) || !rawPlans.length) return { slots: [], activeIndex: null }
    const actualLookup = buildActualQtyLookupByProductProcess(existingItems, processId)
    const slotMap = new Map()
    rawPlans.forEach((plan) => {
      const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
      processes.forEach((pp) => {
        if (String(pp.process_id) != String(processId)) return
        const start = new Date(pp.start_time); const end = new Date(pp.end_time)
        if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return
        const productId = pp.output_product_id ?? plan.product; if (!productId) return
        const key = `${productId}_${processId}`
        const item = {
          plan_date: targetDate, product: productId, product_code: pp.output_product_code || plan.product_code || '',
          product_name: pp.output_product_name || plan.product_name || '', process: processId,
          plan_qty: pp.quantity ?? plan.plan_qty ?? 0, actual_qty: actualLookup.has(key) ? actualLookup.get(key) : 0, start, end,
          sequence_no: plan.sequence_no ?? null, gantt_plan_id: plan.plan_id || null,
        }
        const slotKey = `${start.toISOString()}_${end.toISOString()}`
        if (!slotMap.has(slotKey)) slotMap.set(slotKey, { start, end, items: [] })
        slotMap.get(slotKey).items.push(item)
      })
    })
    const slots = Array.from(slotMap.values()).sort((a, b) => a.start - b.start)
    const now = new Date()
    let activeIdx = null
    slots.forEach((slot, idx) => { if (now >= slot.start && now <= slot.end && activeIdx === null) activeIdx = idx })
    if (activeIdx === null && slots.length > 0) activeIdx = 0
    return { slots, activeIndex: activeIdx }
  } catch { return { slots: [], activeIndex: null } }
}

const fetchProcessPlanProductsFromBacklogs = async (lineId, processId) => {
  const listRes = await api.lineBacklogs.getLineBacklogs({ line: lineId, process: processId, plan_date: currentDateYmd.value, page_size: 1000 })
  const listItems = listRes.data.results || listRes.data || []
  if (Array.isArray(listItems) && listItems.length > 0) return listItems
  try {
    const pickupRes = await api.lineBacklogs.pickup({ line_id: lineId, start_date: currentDateYmd.value, end_date: currentDateYmd.value })
    const pickupItems = pickupRes.data.results || pickupRes.data || []
    return (Array.isArray(pickupItems) ? pickupItems : []).filter(
      (it) => String(it.process) === String(processId) && String(it.plan_date) === String(currentDateYmd.value)
    )
  } catch { return [] }
}

const filterCoproductChildrenFromList = async (candidates) => {
  const parentSetItems = candidates.filter((it) => it.product && typeof it.product_code === 'string' && it.product_code.startsWith('STYD'))
  if (parentSetItems.length === 0) return candidates
  const parentIds = [...new Set(parentSetItems.map((it) => it.product))]
  const childIds = new Set()
  for (const parentId of parentIds) {
    try {
      const tree = await getBomTreeCached(parentId)
      if (!tree || !tree.is_coproduct) continue
      for (const ch of tree.children || []) { if (ch?.product_id) childIds.add(ch.product_id) }
    } catch {}
  }
  if (childIds.size === 0) return candidates
  return candidates.filter((it) => !childIds.has(it.product))
}

const loadProductImages = async (idSet) => {
  try {
    if (!idSet || idSet.size === 0) { productImageMap.value = {}; productMetaMap.value = {}; return }
    const all = await api.products.getAllProducts({ page_size: 5000 })
    const map = {}; const meta = {}
    all.forEach((p) => {
      const pidNum = p.id; const pidStr = String(p.id)
      if (idSet.has(pidNum) || idSet.has(pidStr)) {
        const val = p.image_url || ''; map[pidNum] = val; map[pidStr] = val
        const metaEntry = { is_final_product: !!p.is_final_product, is_line_final_product: !!p.is_line_final_product, category: p.category || '' }
        meta[pidNum] = metaEntry; meta[pidStr] = metaEntry
      }
    })
    const missingIds = [...idSet].filter((id) => !(String(id) in map))
    for (const mid of missingIds) {
      try {
        const res = await api.products.getProduct(mid); const p = res.data || res
        if (p) {
          const val = p.image_url || ''; map[p.id] = val; map[String(p.id)] = val
          const metaEntry = { is_final_product: !!p.is_final_product, is_line_final_product: !!p.is_line_final_product, category: p.category || '' }
          meta[p.id] = metaEntry; meta[String(p.id)] = metaEntry
        }
      } catch {}
    }
    productImageMap.value = map; productMetaMap.value = meta
  } catch {}
}

const loadManualProducts = async (processId) => {
  if (!processId) return
  if (manualProductsLoading.value || (manualProductsLoaded.value && String(manualProductsProcessId.value) === String(processId))) return
  manualProductsLoading.value = true
  try {
    const res = await api.processes.getRelatedProducts(processId)
    manualProducts.value = await filterInputEligibleProducts(
      processId,
      Array.isArray(res?.data) ? res.data : []
    )
    manualProductsProcessId.value = processId; manualProductsLoaded.value = true
  } catch {} finally { manualProductsLoading.value = false }
}

const filterInputEligibleProducts = async (processId, candidates) => {
  const list = Array.isArray(candidates) ? candidates : []
  const productIds = [...new Set(list.map((item) => item?.product ?? item?.id).filter(Boolean))]
  if (!productIds.length) return []
  try {
    const res = await api.processes.getInputEligibleProducts(processId, {
      plan_date: currentDateYmd.value,
      product_ids: productIds,
    })
    const eligibleIds = new Set((res?.data?.product_ids || []).map(String))
    return list.filter((item) => eligibleIds.has(String(item?.product ?? item?.id)))
  } catch (error) {
    console.error('入力可能品番の判定エラー:', error)
    return []
  }
}

const filterTimeSlotsByEligibleProducts = async (processId, slots) => {
  const list = Array.isArray(slots) ? slots : []
  const eligibleItems = await filterInputEligibleProducts(
    processId,
    list.flatMap((slot) => Array.isArray(slot?.items) ? slot.items : [])
  )
  const eligibleIds = new Set(eligibleItems.map((item) => String(item?.product ?? item?.id)))
  return list.map((slot) => ({
    ...slot,
    items: (Array.isArray(slot?.items) ? slot.items : []).filter(
      (item) => eligibleIds.has(String(item?.product ?? item?.id))
    ),
  })).filter((slot) => slot.items.length > 0)
}

const loadScrapProducts = async (processId, baseProducts, fallbackLineId = null, options = {}) => {
  try {
    const skipBomExpansion = Boolean(options?.skipBomExpansion)
    const forceBlockBom = shouldBlockBomService(fallbackLineId, processId)
    const scrapMap = new Map()
    baseProducts.forEach((it) => {
      const key = `${it.product}_${it.process}`
      if (!scrapMap.has(key)) scrapMap.set(key, { ...it, origin_process_id: it.process ?? processId, origin_line_id: it.line ?? fallbackLineId, sourcing_type: it.sourcing_type || it.sourcingType || '' })
    })
    if (!scrapMap.size && fallbackLineId) {
      try {
        const lineRes = await api.lineBacklogs.getLineBacklogs({ line: fallbackLineId, plan_date: currentDateYmd.value })
        ;(lineRes.data.results || lineRes.data || []).forEach((it) => {
          if (!it?.product) return
          const key = `${it.product}_${processId}`
          if (!scrapMap.has(key)) scrapMap.set(key, { ...it, process: processId, origin_process_id: it.process ?? processId, origin_line_id: it.line ?? fallbackLineId, sourcing_type: it.sourcing_type || it.sourcingType || '' })
        })
      } catch {}
    }
    const relatedRes = await api.processes.getRelatedProducts(processId)
    const relatedProducts = relatedRes.data || []
    const relatedInfoMap = new Map()
    relatedProducts.forEach((prod) => {
      relatedInfoMap.set(String(prod.id), { relation_type: prod.relation_type, process_id: prod.process_id, sourcing_type: prod.sourcing_type || '' })
      const key = `${prod.id}_${processId}`
      if (!scrapMap.has(key)) scrapMap.set(key, { product: prod.id, product_code: prod.product_code, product_name: prod.product_name, process: processId, origin_process_id: prod.process_id || processId, origin_line_id: prod.line_id || fallbackLineId, sourcing_type: prod.sourcing_type || '', plan_qty: 0, plan_date: null, relation_type: prod.relation_type })
    })
    scrapMap.forEach((item) => {
      if (!item?.product) return
      const info = relatedInfoMap.get(String(item.product)); if (!info) return
      if (!item.relation_type && info.relation_type) item.relation_type = info.relation_type
      if (!item.sourcing_type && info.sourcing_type) item.sourcing_type = info.sourcing_type
      item.origin_process_id = info.process_id || null
    })
    if (skipBomExpansion || forceBlockBom) {
      scrapProducts.value = Array.from(scrapMap.values())
      const idSet = new Set([...productionProducts.value.map((p) => p.product).filter(Boolean), ...scrapProducts.value.map((p) => p.product).filter(Boolean)])
      await loadProductImages(idSet); return
    }
    const bomCache = new Map()
    const addBomChildren = async (parentProductId) => {
      if (!parentProductId) return
      const cacheKey = String(parentProductId)
      if (!bomCache.has(cacheKey)) { try { const treeRes = await api.bomService.getBomTree(parentProductId); bomCache.set(cacheKey, treeRes.data || null) } catch { bomCache.set(cacheKey, null) } }
      const tree = bomCache.get(cacheKey)
      if (!tree || !Array.isArray(tree.children)) return
      tree.children.forEach((ch) => {
        if (!ch?.product_id) return
        const childKey = `${ch.product_id}_${processId}`
        const childRelation = ch.category === 'PURCHASED' || ch.category === 'MATERIAL' ? 'purchased' : 'intermediate'
        if (scrapMap.has(childKey)) {
          const existing = scrapMap.get(childKey) || {}
          if (!existing.relation_type) existing.relation_type = childRelation
          if (!existing.origin_process_id && (ch.process_id || ch.processId)) existing.origin_process_id = ch.process_id || ch.processId
          if (!existing.sourcing_type && ch.sourcing_type) existing.sourcing_type = ch.sourcing_type
          scrapMap.set(childKey, existing); return
        }
        scrapMap.set(childKey, { product: ch.product_id, product_code: ch.product_code || ch.product_id, product_name: ch.product_name || '', process: processId, origin_process_id: (ch.process_id || ch.processId) || processId, origin_line_id: (ch.line_id || ch.lineId) || fallbackLineId, sourcing_type: ch.sourcing_type || '', plan_qty: 0, plan_date: null, relation_type: childRelation })
      })
    }
    const outputProducts = Array.from(scrapMap.values()).filter((it) => normalizeRelationType(it.relation_type) === 'output_product')
    for (const op of outputProducts) await addBomChildren(op.product)
    const coproductParentIds = (relatedProducts || []).filter((p) => normalizeRelationType(p.relation_type) === 'coproduct_parent').map((p) => p.id)
    for (const parentId of coproductParentIds) {
      try {
        const treeRes = await api.bomService.getBomTree(parentId); const tree = treeRes.data
        if (!tree || !Array.isArray(tree.children)) continue
        tree.children.forEach((ch) => {
          if (!ch?.product_id) return
          const key = `${ch.product_id}_${processId}`
          if (scrapMap.has(key)) { scrapMap.get(key).relation_type = 'coproduct_child'; return }
          scrapMap.set(key, { product: ch.product_id, product_code: ch.product_code || ch.product_id, product_name: ch.product_name || '', process: processId, plan_qty: 0, plan_date: null, relation_type: 'coproduct_child' })
        })
      } catch {}
    }
    scrapMap.forEach((item) => {
      if (!item?.product) return; const info = relatedInfoMap.get(String(item.product)); if (!info) return
      if (!item.relation_type && info.relation_type) item.relation_type = info.relation_type
      if (info.process_id) item.origin_process_id = info.process_id
    })
    scrapProducts.value = Array.from(scrapMap.values())
    const idSet = new Set([...productionProducts.value.map((p) => p.product).filter(Boolean), ...scrapProducts.value.map((p) => p.product).filter(Boolean)])
    await loadProductImages(idSet)
  } catch { scrapProducts.value = [...baseProducts] }
}

const loadPlannedProducts = async () => {
  if (!selectedProcessId.value) {
    dailyProcessTargets.value = []
    return
  }
  const requestSeq = ++plannedProductsRequestSeq
  isPlannedProductsLoading.value = true
  invalidateSelectedCoproductNotice()
  productionProducts.value = []; scrapProducts.value = []; allPlanProducts.value = []; allScrapProducts.value = []
  timeSlots.value = []; activeSlotIndex.value = null
  actualQtyByProductFromBacklog.value = new Map()
  actualQtyByProductCodeFromBacklog.value = new Map()
  try {
    const process = processes.value.find(p => String(p.id) === String(selectedProcessId.value))
    const lineId = process?.line; if (!lineId) return
    const processId = selectedProcessId.value
    try {
      const targetRes = await api.dailyProcessTargets.list({
        line: lineId,
        process: processId,
        plan_date: currentDateYmd.value,
        page_size: 100,
      })
      if (requestSeq === plannedProductsRequestSeq) {
        dailyProcessTargets.value = targetRes.data?.results || targetRes.data || []
      }
    } catch (targetError) {
      console.error('日別目標取得エラー:', targetError)
      if (requestSeq === plannedProductsRequestSeq) dailyProcessTargets.value = []
    }
    let tempProducts = await fetchProcessPlanProductsFromBacklogs(lineId, processId)
    const lineObj = lines.value.find((line) => String(line.id) === String(lineId)) || null
    const lineCode = String(lineObj?.line_code || '').trim().toUpperCase()
    const floorMapOnlyMode = !filterCurrentTime.value && lineCode === FLOOR_LINE_CODE
    tempProducts = await filterFloorProductsByDisplayMap(lineId, processId, tempProducts, floorMapOnlyMode)
    const slotResult = await buildPlanTimeSlots(lineId, processId, tempProducts)
    if (requestSeq !== plannedProductsRequestSeq) return
    timeSlots.value = slotResult.slots
    activeSlotIndex.value = slotResult.activeIndex
    const ganttEntriesByProduct = new Map()
    ;(slotResult.slots || []).forEach((slot) => {
      ;(Array.isArray(slot?.items) ? slot.items : []).forEach((item) => {
        const productId = item?.product
        if (productId === null || productId === undefined || productId === '') return
        const seq = parseSeqNo(item?.sequence_no)
        const pid = String(productId)
        if (!ganttEntriesByProduct.has(pid)) ganttEntriesByProduct.set(pid, new Map())
        const seqMap = ganttEntriesByProduct.get(pid)
        const ganttPlanId = item?.gantt_plan_id || ''
        const seqKey = ganttPlanId ? `${seq !== null ? seq : 'none'}__${ganttPlanId}` : (seq !== null ? seq : 'none')
        const prev = seqMap.get(seqKey)
        const startMs = item?.start instanceof Date ? item.start.getTime() : Number.POSITIVE_INFINITY
        if (!prev) { seqMap.set(seqKey, { qty: toSafeNumber(item?.plan_qty), startMs, gantt_plan_id: ganttPlanId }) }
        else { prev.qty += toSafeNumber(item?.plan_qty); prev.startMs = Math.min(prev.startMs, startMs) }
      })
    })

    const actualLookup = buildActualQtyLookupByProductProcess(tempProducts, processId)
    actualQtyByProductCodeFromBacklog.value = buildActualQtyLookupByProductCode(tempProducts)
    const backlogActualByProduct = new Map()
    actualLookup.forEach((qty, key) => {
      const productId = String(key).split('_')[0]
      if (!productId) return
      const current = toSafeNumber(backlogActualByProduct.get(productId))
      const next = toSafeNumber(qty)
      if (next > current) backlogActualByProduct.set(productId, next)
    })
    actualQtyByProductFromBacklog.value = backlogActualByProduct
    tempProducts = (Array.isArray(tempProducts) ? tempProducts : []).map((it) => {
      const key = `${it?.product}_${processId}`
      return { ...it, actual_qty: actualLookup.has(key) ? toSafeNumber(actualLookup.get(key)) : toSafeNumber(it?.actual_qty) }
    })
    let mapFilteredForProduction = []
    if (floorMapOnlyMode) {
      mapFilteredForProduction = await mergeMissingFloorMapProducts(lineId, processId, tempProducts)
      if (requestSeq !== plannedProductsRequestSeq) return
    } else {
      const productsWithParents = await enrichCoproductParentsForList(tempProducts, processId)
      if (requestSeq !== plannedProductsRequestSeq) return
      const filteredForProduction = await filterCoproductChildrenFromList(productsWithParents)
      if (requestSeq !== plannedProductsRequestSeq) return
      mapFilteredForProduction = await filterFloorProductsByDisplayMap(lineId, processId, filteredForProduction, floorMapOnlyMode)
      if (requestSeq !== plannedProductsRequestSeq) return
    }

    const eligibleCandidates = [
      ...mapFilteredForProduction,
      ...timeSlots.value.flatMap((slot) => slot.items || []),
    ]
    const eligibleItems = await filterInputEligibleProducts(processId, eligibleCandidates)
    if (requestSeq !== plannedProductsRequestSeq) return
    const eligibleIds = new Set(eligibleItems.map((item) => String(item.product ?? item.id)))
    mapFilteredForProduction = mapFilteredForProduction.filter((item) => eligibleIds.has(String(item.product ?? item.id)))
    timeSlots.value = timeSlots.value.map((slot) => ({
      ...slot,
      items: (slot.items || []).filter((item) => eligibleIds.has(String(item.product ?? item.id))),
    }))

    const expanded = []
    mapFilteredForProduction.forEach((item) => {
      const pid = String(item?.product || '')
      const entries = ganttEntriesByProduct.get(pid)
      if (!entries || entries.size === 0) {
        expanded.push({ ...item, plan_qty: 0 })
        return
      }
      entries.forEach((entry, seqKey) => {
        const seqPart = String(seqKey).split('__')[0]
        const seqNo = seqPart === 'none' ? null : Number(seqPart)
        expanded.push({ ...item, plan_qty: toSafeNumber(entry.qty), sequence_no: Number.isFinite(seqNo) ? seqNo : null, gantt_start_ms: Number.isFinite(entry.startMs) ? entry.startMs : null, gantt_plan_id: entry.gantt_plan_id || null })
      })
    })
    mapFilteredForProduction = expanded

    const dedupMap = new Map()
    mapFilteredForProduction.forEach((item) => {
      const key = productSeqKey(item)
      if (key && !dedupMap.has(key)) dedupMap.set(key, item)
    })
    mapFilteredForProduction = Array.from(dedupMap.values())

    // 同一製品の複数計画（本体 + hakogumi_prev等）に実績を開始時刻順に分配
    const planGroupsByProduct = new Map()
    mapFilteredForProduction.forEach((item, idx) => {
      if (!item?.gantt_plan_id) return
      const pid = String(item?.product || '')
      if (!pid) return
      if (!planGroupsByProduct.has(pid)) planGroupsByProduct.set(pid, [])
      planGroupsByProduct.get(pid).push(idx)
    })
    planGroupsByProduct.forEach((indices, pid) => {
      if (indices.length <= 1) return
      const totalActual = toSafeNumber(backlogActualByProduct.get(pid))
      const sorted = indices
        .map((idx) => ({ idx, startMs: mapFilteredForProduction[idx]?.gantt_start_ms ?? Number.POSITIVE_INFINITY }))
        .sort((a, b) => a.startMs - b.startMs)
      let remaining = totalActual
      sorted.forEach(({ idx }, i) => {
        const planQty = toSafeNumber(mapFilteredForProduction[idx].plan_qty)
        const isLast = i === sorted.length - 1
        const attributed = isLast ? Math.max(remaining, 0) : Math.min(Math.max(remaining, 0), planQty)
        mapFilteredForProduction[idx] = { ...mapFilteredForProduction[idx], actual_qty: attributed }
        remaining -= attributed
      })
    })

    allPlanProducts.value = [...mapFilteredForProduction]
    applyTimeSlotFilter()
    if (productionProducts.value.length === 1 && productionProducts.value[0].product) defaultProductId.value = productionProducts.value[0].product
    if (!productionProducts.value.length) loadManualProducts(processId)
    const skipScrapBackgroundLoad = floorMapOnlyMode && record.value.record_type !== 'SCRAP'
    if (skipScrapBackgroundLoad) { allScrapProducts.value = []; scrapProducts.value = [] }
    else {
      const scrapLoadTask = (async () => {
        await loadScrapProducts(processId, mapFilteredForProduction, lineId, { skipBomExpansion: floorMapOnlyMode })
        if (requestSeq !== plannedProductsRequestSeq) return
        allScrapProducts.value = [...scrapProducts.value]
        if (record.value.record_type === 'SCRAP') { applyTimeSlotFilter(); if (!productionProducts.value.length && !scrapProducts.value.length) loadManualProducts(processId) }
      })()
      if (record.value.record_type === 'SCRAP') await scrapLoadTask
      else scrapLoadTask.catch(() => {})
    }
  } catch (error) { console.error('本日の計画取得エラー:', error) }
  finally { if (requestSeq === plannedProductsRequestSeq) isPlannedProductsLoading.value = false }
}

const loadProcesses = async () => {
  try { const res = await api.processes.getProcesses({ is_active: true }); processes.value = res.data.results || res.data || [] }
  catch { alert(t('processInput.alert.loadProcessFailed')) }
}

const loadLines = async () => {
  try { const res = await api.lines.getProductionLines(); lines.value = res.data.results || res.data || [] }
  catch { alert(t('processInput.alert.loadLineFailed')) }
}

const toggleSupportMode = () => {
  isSupportMode.value = !isSupportMode.value
  if (isSupportMode.value) return
  const ownIds = new Set(ownLines.value.map((line) => String(line.id)))
  if (selectedLineId.value && ownIds.has(String(selectedLineId.value))) return
  const preferred = preferredUserLineId.value
  if (preferred && ownIds.has(String(preferred))) { selectedLineId.value = String(preferred); onLineChange(); return }
  if (ownLines.value.length) { selectedLineId.value = String(ownLines.value[0].id); onLineChange() }
  else { selectedLineId.value = ''; onLineChange() }
}

const applySupportModeFromQuery = () => {
  const raw = String(route.query.support_mode || '').toLowerCase()
  if (raw === 'on' || raw === '1' || raw === 'true') isSupportMode.value = true
  else if (raw === 'off' || raw === '0' || raw === 'false') isSupportMode.value = false
}

const applyInitialLineSelection = () => {
  const candidateList = Array.isArray(availableLines.value) ? availableLines.value : []
  if (!candidateList.length) { selectedLineId.value = ''; return }
  const preferred = preferredUserLineId.value
  if (preferred && candidateList.some((line) => String(line.id) === String(preferred))) { selectedLineId.value = String(preferred); return }
  selectedLineId.value = String(candidateList[0].id)
}

function openEquipmentInspection() {
  const source = String(route.query?.parent_source || 'desktop_process_input')
  const returnPanel = route.query?.parent_panel ? String(route.query.parent_panel) : ''
  const returnOperatorName = route.query?.operator_name ? String(route.query.operator_name) : ''
  const returnOperatorUserId = route.query?.operator_user_id ? String(route.query.operator_user_id) : ''
  router.push({ path: '/quality/equipment-inspection/operation', query: {
    source,
    ...(selectedProcessId.value ? { process_id: String(selectedProcessId.value) } : {}),
    ...(selectedLineId.value ? { line_id: String(selectedLineId.value) } : {}),
    ...(returnPanel ? { return_panel: returnPanel } : {}),
    ...(returnOperatorName ? { return_operator_name: returnOperatorName } : {}),
    ...(returnOperatorUserId ? { return_operator_user_id: returnOperatorUserId } : {}),
  }})
}

function openIntegratedChecksheetOperation() {
  const source = String(route.query?.parent_source || 'desktop_process_input')
  const returnPanel = route.query?.parent_panel ? String(route.query.parent_panel) : ''
  const returnOperatorName = route.query?.operator_name ? String(route.query.operator_name) : ''
  const returnOperatorUserId = route.query?.operator_user_id ? String(route.query.operator_user_id) : ''
  router.push({ path: '/quality/product-checksheet/integrated/operation', query: {
    source,
    ...(selectedLineId.value ? { line_id: String(selectedLineId.value) } : {}),
    ...(selectedProcessId.value ? { process_id: String(selectedProcessId.value) } : {}),
    ...(returnPanel ? { return_panel: returnPanel } : {}),
    ...(returnOperatorName ? { return_operator_name: returnOperatorName } : {}),
    ...(returnOperatorUserId ? { return_operator_user_id: returnOperatorUserId } : {}),
  }})
}

// ──────────────────────────────
// ウォッチャー
// ──────────────────────────────
watch(() => authState.user, () => {
  const resolved = resolveDefaultOperator()
  if (resolved && resolved !== defaultOperatorName.value) defaultOperatorName.value = resolved
  if (!(record.value.operator_name || '').trim()) record.value.operator_name = resolved
})

watch([availableLines, preferredUserLineId], ([nextLines, nextPreferred]) => {
  const candidateList = Array.isArray(nextLines) ? nextLines : []
  if (candidateList.some((line) => String(line.id) === String(selectedLineId.value))) return
  if (nextPreferred && candidateList.some((line) => String(line.id) === String(nextPreferred))) { selectedLineId.value = String(nextPreferred); return }
  selectedLineId.value = candidateList.length ? String(candidateList[0].id) : ''
}, { immediate: true })

watch(ownLines, (nextOwnLines) => {
  if (isSupportMode.value) return
  const ownIds = new Set((nextOwnLines || []).map((line) => String(line.id)))
  if (selectedLineId.value && ownIds.has(String(selectedLineId.value))) return
  const preferred = preferredUserLineId.value
  if (preferred && ownIds.has(String(preferred))) { selectedLineId.value = String(preferred); onLineChange(); return }
  if (nextOwnLines.length) { selectedLineId.value = String(nextOwnLines[0].id); onLineChange() }
})

watch(availableRecordTypes, () => ensureDefaultRecordType(), { immediate: true })

watch(() => record.value.reason, (val) => { if (val !== 'OTHER') record.value.reason_detail = '' })

watch(() => effectiveOperatorAction.value, (action) => {
  const actionKey = String(action || '').toUpperCase()
  if (!['PAUSE', 'TEMP_END'].includes(actionKey)) { record.value.operator_action_reason = ''; record.value.operator_action_reason_detail = '' }
  if (!shouldUseCounterInput.value) record.value.counter_qty = null
})

watch(() => record.value.operator_action_reason, (val) => { if (val !== 'その他') record.value.operator_action_reason_detail = '' })

watch(() => record.value.product_id, (pid) => {
  if (record.value.record_type === 'PRODUCTION') {
    record.value.counter_qty = null
    record.value.qty = null
  }
  if (!pid || record.value.record_type !== 'SCRAP') return
  const candidate = scrapProducts.value.find((p) => String(p.product) === String(pid)) || manualProducts.value.find((p) => String(p.id) === String(pid))
  if (candidate) applyScrapTypeDefaults(candidate)
})

watch(() => scrapRelationFilter.value, (val) => {
  if (record.value.record_type !== 'SCRAP') return
  if (val === 'purchased' || val === 'in_house') record.value.is_production_recorded = true
  else if (val === 'own_process') record.value.is_production_recorded = ''
})

watch(() => record.value.record_type, (type) => {
  if (!type) return
  if (type !== 'PRODUCTION') selectedOperatorAction.value = ''
  if (type === 'EQUIPMENT_STATE') { record.value.counter_qty = null; record.value.qty = null; record.value.batch_no = ''; record.value.operator_name = ''; record.value.reason_detail = ''; record.value.reason = '' }
  else if (type === 'SCRAP') { if (!(record.value.operator_name || '').trim()) record.value.operator_name = defaultOperatorName.value || ''; ensureScrapDefaults() }
  else { record.value.reason_detail = ''; record.value.reason = ''; record.value.disposition_status = ''; if (!(record.value.operator_name || '').trim()) record.value.operator_name = defaultOperatorName.value || '' }
  if (!record.value.product_id && defaultProductId.value) {
    record.value.product_id = defaultProductId.value
    const plan = currentProductList.value.find((p) => String(p.product) === String(defaultProductId.value))
    if (plan) { record.value.counter_qty = null; record.value.qty = null }
  }
  restoreEquipmentStateIfNeeded()
  currentPage.value = 1
}, { immediate: true })

watch(
  () => [record.value.counter_qty, counterBaseQty.value, shouldUseCounterInput.value],
  () => {
    if (!shouldUseCounterInput.value) return
    if (record.value.counter_qty === null || record.value.counter_qty === '') {
      record.value.qty = null
      return
    }
    const counterQty = toSafeNumber(record.value.counter_qty)
    const calculatedQty = counterQty - counterBaseQty.value
    record.value.qty = calculatedQty >= 0 ? calculatedQty : null
  },
  { immediate: true },
)

watch(() => [record.value.product_id, record.value.product_code], () => { ensureScrapDefaults(); loadSelectedCoproductNotice() })

watch(() => [selectedLineId.value, selectedProcessId.value], () => restoreEquipmentStateIfNeeded())

watch(() => route.query.support_mode, () => applySupportModeFromQuery())
watch(
  () => [isTwoPersonSameEquipmentMode.value, operatorScopeName.value, operatorScopeUserId.value, selectedProcessId.value],
  () => {
    if (!selectedProcessId.value) return
    loadStartedProductIds()
  },
)
watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

// embed時: 加工中情報を親フレームに通知
if (isEmbeddedTablet.value) {
  watch(currentProcessingLabel, (label) => {
    window.parent.postMessage({
      type: 'processing-status',
      processId: String(route.query.process_id || ''),
      label: label || '',
    }, '*')
  }, { immediate: true })
  window.addEventListener('message', (e) => {
    if (e.data?.type === 'jump-to-processing' && e.data.processId === String(route.query.process_id || '')) {
      jumpToProcessingProduct()
    }
  })
}

// ──────────────────────────────
// 初期化
// ──────────────────────────────
onMounted(async () => {
  await ensureAuth()
  applySupportModeFromQuery()
  await Promise.all([loadLines(), loadProcesses()])
  applyInitialLineSelection()
  const queryLineId = route.query.line_id
  if (queryLineId) { if (availableLines.value.some((line) => String(line.id) === String(queryLineId))) selectedLineId.value = String(queryLineId) }
  const queryProcessId = route.query.process_id
  if (queryProcessId) { selectedProcessId.value = String(queryProcessId); onProcessChange() }
  if (route.query.operator_name !== undefined) {
    const name = String(route.query.operator_name || ''); defaultOperatorName.value = name; record.value.operator_name = name
  } else if (route.query.clear_operator === '1') { defaultOperatorName.value = ''; record.value.operator_name = '' }
})
</script>

<style scoped>
.desktop-process-input {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100%;
  background: #f0f2f5;
  font-size: 14px;
  position: relative;
  overflow: hidden;
}
.desktop-process-input.page-run { background: #d1fae5; }
.desktop-process-input.page-idle { background: #ffedd5; }
.desktop-process-input.page-setup { background: #fef3c7; }
.desktop-process-input.page-maintenance { background: #dbeafe; }
.desktop-process-input.page-breakdown { background: #fecaca; }
.desktop-process-input.page-stopped { background: #f3f4f6; }

.header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.page-title { font-size: 16px; font-weight: 700; margin: 0; white-space: nowrap; }
.btn-checksheet-nav {
  height: 30px; padding: 0 12px; border: 1px solid #2563eb; background: #fff; color: #2563eb;
  border-radius: 4px; cursor: pointer; font-size: 12px; white-space: nowrap; flex-shrink: 0;
}
.btn-inspection-nav {
  height: 30px; padding: 0 12px; border: 1px solid #0e7490; background: #fff; color: #0e7490;
  border-radius: 4px; cursor: pointer; font-size: 12px; white-space: nowrap; flex-shrink: 0;
}
.header-controls {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; flex: 1; min-width: 0;
}
.header-label { font-size: 12px; color: #666; white-space: nowrap; }
.line-select-wrapper { display: flex; align-items: center; gap: 6px; }
.process-select {
  height: 30px; padding: 0 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; min-width: 160px;
}
.date-display { font-size: 13px; font-weight: 600; color: #475569; white-space: nowrap; }
.support-toggle-btn {
  height: 30px; padding: 0 10px; border: 1px solid #cbd5e1; border-radius: 4px;
  background: #fff; color: #334155; font-size: 12px; font-weight: 700; cursor: pointer; white-space: nowrap;
}
.support-toggle-btn.active { border-color: #f59e0b; background: #ffedd5; color: #9a3412; }
.header-processing {
  display: flex; align-items: center; gap: 6px; min-height: 28px; padding: 4px 10px;
  border-radius: 14px; background: #dcfce7; font-size: 12px; color: #166534;
  flex-wrap: wrap; flex: 1 1 200px; min-width: 0; font-weight: 700;
}
.header-processing.pause { background: #ffedd5; color: #9a3412; }
.header-processing.empty { background: #f5f5f5; color: #999; font-weight: 400; }
.header-target-chip {
  display: flex; align-items: center; min-height: 28px; padding: 4px 10px;
  border-radius: 14px; background: #fff7ed; border: 1px solid #fdba74;
  font-size: 12px; color: #9a3412; font-weight: 700;
  flex: 1 1 260px; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.embed-target-chip {
  flex: 1 1 180px;
  min-height: 24px;
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 12px;
}
.processing-chip { white-space: nowrap; }
.header-processing.clickable { cursor: pointer; }
.header-processing.clickable:hover { filter: brightness(0.92); }

/* 4列レイアウト */
.four-col-layout {
  display: grid;
  grid-template-columns: 180px 260px minmax(0, 1fr) 220px;
  flex: 1; overflow: hidden; gap: 0; min-height: 0;
}
.col-controls, .col-form, .col-recent {
  overflow-y: auto; padding: 12px; border-right: 1px solid #dde1e8; min-width: 0;
}
.col-list { overflow-y: visible; padding: 12px; border-right: 1px solid #dde1e8; min-width: 0; }
.col-recent { border-right: none; }
.section-title {
  font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase;
  margin-bottom: 6px; letter-spacing: 0.5px;
}

/* コントロール列 */
.record-type-area { display: flex; flex-direction: row; gap: 4px; }
.record-type-btn {
  flex: 1; height: 26px; border: 2px solid #ccc; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 11px; font-weight: 600; transition: all 0.15s; padding: 0;
}
.record-type-btn.active { border-color: #4a7ae5; background: #eff6ff; color: #4a7ae5; }
.filter-area { display: flex; flex-direction: column; gap: 8px; }
.filter-item { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 0; border-bottom: 1px solid #9aa5b4; }
.filter-item:last-child { border-bottom: none; }
.filter-item-reverse { flex-direction: row; }
.toggle-label { font-size: 13px; flex: 1; }
.toggle-input { display: none; }
.toggle-track {
  width: 36px; height: 20px; border-radius: 10px; background: #ccc;
  position: relative; transition: background 0.2s; flex-shrink: 0;
}
.toggle-track::after {
  content: ''; position: absolute; width: 16px; height: 16px; border-radius: 50%;
  background: #fff; top: 2px; left: 2px; transition: left 0.2s;
}
.toggle-track.on { background: #4e7cbf; }
.toggle-track.on::after { left: 18px; }
.slot-nav { display: flex; align-items: center; gap: 4px; margin-top: 6px; }
.slot-btn {
  width: 32px; height: 26px; border: 1px solid #ccc; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 14px; font-weight: 800;
}
.slot-btn:disabled { opacity: 0.4; cursor: default; }
.slot-label-text { font-size: 11px; color: #333; font-weight: 600; }
.operator-area { margin-bottom: 4px; }
.operator-input {
  width: 100%; height: 32px; padding: 0 8px; border: 1px solid #ccc;
  border-radius: 4px; font-size: 13px; box-sizing: border-box;
}
.scrap-filter-controls { display: flex; flex-direction: column; gap: 6px; }
.scrap-filter-select, .scrap-filter-input {
  width: 100%; height: 30px; padding: 0 6px; border: 1px solid #ccc;
  border-radius: 4px; font-size: 12px; box-sizing: border-box;
}
.equip-state-btns { display: flex; flex-direction: column; gap: 4px; }
.equip-state-btn {
  width: 100%; height: 32px; border: 2px solid #ccc; border-radius: 6px;
  background: #fff; cursor: pointer; font-size: 12px; font-weight: 600;
}
.equip-state-btn.active { border-color: #4a7ae5; background: #eff6ff; color: #4a7ae5; }
.equip-state-btn.state-running.active { border-color: #16a34a; background: #f0fdf4; color: #16a34a; }
.equip-state-btn.state-breakdown.active { border-color: #ef4444; background: #fef2f2; color: #ef4444; }
.equip-state-btn.state-maintenance.active { border-color: #f59e0b; background: #fffbeb; color: #f59e0b; }
.equip-form-section { margin-bottom: 12px; }
.equip-state-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.equip-state-grid .equip-state-btn { width: 100%; height: 40px; font-size: 14px; }

/* 製品リスト列 */
.list-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.list-count { font-size: 12px; color: #888; white-space: nowrap; }
.scope-warning {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #9a3412;
  background: #ffedd5;
  border: 1px solid #fdba74;
  border-radius: 4px;
  padding: 3px 6px;
}
.list-filter-input {
  flex: 1; height: 28px; padding: 0 6px; border: 1px solid #ccc;
  border-radius: 4px; font-size: 12px; box-sizing: border-box; min-width: 0;
}
.plan-list { display: flex; flex-direction: column; gap: 4px; }
.plan-item {
  display: flex; align-items: center; gap: 6px; padding: 5px 8px;
  border-radius: 8px; background: #fff; border: 2px solid transparent;
  cursor: pointer; transition: border-color 0.15s; position: relative;
}
.plan-item:hover { border-color: #b0c4e8; }
.plan-item.selected { border-color: #4e7cbf; background: #e8f0fb; }
.plan-item.current-processing { border-color: #16a34a; background: #f0fdf4; }
.plan-item.temp-ended { opacity: 0.6; }
.item-grid {
  display: grid; grid-template-columns: 1fr auto; gap: 0 6px;
  flex: 1; min-width: 0;
}
.item-code { font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-plan { font-size: 11px; color: #555; text-align: right; white-space: nowrap; }
.item-sub { font-size: 10px; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-actual { font-size: 10px; color: #555; text-align: right; white-space: nowrap; }
.item-actual.done { color: #16a34a; font-weight: 700; }
.item-actual.over { color: #ef4444; font-weight: 700; }
.status-badge { font-size: 9px; border-radius: 4px; padding: 1px 4px; font-weight: 700; }
.status-badge.temp-end { background: #94a3b8; color: #fff; }
.empty-list { text-align: center; padding: 24px 0; color: #aaa; font-size: 13px; }
.loading-list { opacity: 0.5; }
.loading-text { text-align: center; padding: 24px 0; color: #aaa; font-size: 13px; }
.pagination {
  display: flex; align-items: center; justify-content: center; gap: 4px; margin-top: 8px;
}
.page-btn {
  width: 28px; height: 28px; border: 1px solid #ccc; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 12px;
}
.page-btn:disabled { opacity: 0.4; cursor: default; }
.page-info { font-size: 12px; color: #666; padding: 0 4px; }
.manual-toggle-area { margin-top: 8px; text-align: center; }
.manual-toggle-area { display: flex; align-items: center; justify-content: center; gap: 8px; }
.planned-time-inline {
  margin-top: 6px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}
.btn-link {
  padding: 0; border: none; background: transparent; color: #4a7ae5;
  font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: underline;
}
.btn-manual-nav {
  height: 26px;
  padding: 0 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.btn-manual-nav:disabled { opacity: 0.45; cursor: default; }

/* フォーム列 */
.no-selection {
  height: 100%; display: flex; align-items: center; justify-content: center;
  color: #aaa; font-size: 14px;
}
.form-area { display: flex; flex-direction: column; gap: 14px; }
.form-area.mode-production {
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px;
}
.form-area.mode-scrap {
  background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 14px;
}
.product-header { padding-bottom: 10px; border-bottom: 1px solid #e8e8e8; }
.product-code-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.product-code-large { font-size: 22px; font-weight: 900; letter-spacing: 0.5px; overflow-wrap: anywhere; }
.product-photo-trigger {
  width: 34px;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.product-photo-trigger:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}
.product-photo-view-trigger:hover:not(:disabled) {
  background: #f0fdf4;
  border-color: #86efac;
  color: #15803d;
}
.product-photo-trigger.disabled,
.product-photo-trigger:disabled {
  opacity: 0.45;
  cursor: default;
}
.product-name { font-size: 14px; color: #555; margin-top: 2px; }
.product-time-label { font-size: 12px; color: #0f172a; font-weight: 600; margin-top: 4px; }
.product-photo-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.64);
  z-index: 9998;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.product-photo-dialog {
  width: min(920px, 100%);
  max-height: min(88vh, 900px);
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.28);
  display: flex;
  flex-direction: column;
}
.product-photo-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #e2e8f0;
}
.product-photo-dialog-title {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}
.product-photo-close {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  cursor: pointer;
  font-size: 24px;
  line-height: 1;
}
.product-photo-dialog-body {
  padding: 18px;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}
.product-photo-dialog-image {
  display: block;
  max-width: 100%;
  max-height: calc(88vh - 120px);
  object-fit: contain;
  border-radius: 12px;
  background: #fff;
}
.product-photo-dialog-empty {
  font-size: 16px;
  font-weight: 700;
  color: #64748b;
}
.product-photo-dialog-actions {
  padding: 14px 18px 18px;
  display: flex;
  justify-content: center;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}
.product-photo-save-btn {
  min-width: 220px;
}
.product-photo-file-input {
  display: none;
}
.action-btns-section { display: flex; flex-direction: column; gap: 6px; }
.embed-tablet .action-btns-section { flex-direction: row; align-items: center; gap: 4px; }
.embed-tablet .op-action-btns { gap: 4px; }
.embed-tablet .op-action-btn { height: 26px; padding: 0 6px; font-size: 11px; border-radius: 4px; border-width: 1px; }
.equip-label { font-size: 12px; color: #555; }
.required-mark { color: #e53935; margin-left: 2px; }
.op-action-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.op-action-note {
  align-self: center;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}
.op-action-btn {
  height: 36px; padding: 0 14px; border: 2px solid #ccc; border-radius: 6px;
  background: #fff; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.15s;
}
.op-action-btn.active { border-color: currentColor; }
.action-start { color: #4e7cbf; }
.action-start.active { background: #e8f0fb; border-color: #4e7cbf; }
.action-end { color: #2e9688; }
.action-end.active { background: #e0f2ef; border-color: #2e9688; }
.action-pause { color: #c0714f; }
.action-pause.active { background: #fdf0ea; border-color: #c0714f; }
.action-resume { color: #7b5ea7; }
.action-resume.active { background: #f0ebf8; border-color: #7b5ea7; }
.action-temp_end { color: #888; }
.action-temp_end.active { background: #f0f0f0; border-color: #888; }
.action-cancel { color: #dc2626; }
.action-cancel.active { background: #fef2f2; border-color: #dc2626; }
.stats-and-actions { display: flex; flex-direction: column; gap: 12px; }
.current-actual { display: flex; gap: 16px; flex-wrap: wrap; }
.stat-block { text-align: center; }
.stat-label { display: block; font-size: 11px; color: #888; }
.stat-value { font-size: 22px; font-weight: 900; }
.stat-value.plan { color: #4e7cbf; }
.stat-value.actual { color: #2e9688; }
.stat-value.remain { color: #c0714f; }
.stat-value.remain.over { color: #388e3c; }
.stat-value.clickable { cursor: pointer; text-decoration: underline; text-decoration-style: dotted; }
.stat-value.clickable:hover { color: #1d74d8; }
.plan-qty-edit { display: inline-flex; align-items: center; gap: 4px; }
.plan-qty-input { width: 70px; font-size: 16px; padding: 2px 4px; text-align: right; }
.plan-time-input { width: 90px; font-size: 14px; padding: 2px 4px; }
.plan-qty-btn { padding: 2px 8px; border: 1px solid #b8c3d6; border-radius: 4px; background: #fff; cursor: pointer; font-size: 13px; }
.plan-qty-btn.save { background: #1d74d8; color: #fff; border-color: #1d74d8; }
.plan-qty-btn.cancel { background: #f5f5f5; }
.plan-item.plan-edited { background: #fffde7; }
.qty-input-area { display: flex; flex-direction: column; gap: 8px; }
.qty-row { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; }
.qty-col { display: flex; flex-direction: column; gap: 4px; }
.qty-label { font-size: 12px; color: #555; }
.label-required-after::after { content: ' *'; color: #e53935; }
.qty-input {
  height: 44px; width: 100px; padding: 0 8px; border: 2px solid #ccc; border-radius: 6px;
  font-size: 20px; font-weight: 700; text-align: center;
}
.qty-input[readonly] {
  background: #f8fafc;
  color: #475569;
}
.batch-input {
  height: 44px; width: 140px; padding: 0 8px; border: 1px solid #ccc;
  border-radius: 6px; font-size: 14px;
}
.quick-btns { display: flex; gap: 6px; flex-wrap: wrap; }
.btn-quick {
  padding: 6px 12px; background: #f1f5f9; border: 1px solid #cbd5e1;
  border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;
}
.btn-quick:active { background: #e2e8f0; }
.reason-area { display: flex; flex-direction: column; gap: 6px; }
.reason-select {
  height: 36px; padding: 0 8px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; width: 100%;
}
.reason-input {
  height: 36px; padding: 0 8px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; width: 100%;
  box-sizing: border-box;
}
.textarea-normal {
  width: 100%; padding: 8px; font-size: 13px; border: 1px solid #ccc;
  border-radius: 6px; box-sizing: border-box; font-family: inherit; resize: vertical;
}
.hint-text { font-size: 11px; color: #6b7280; }
.scrap-fields { display: flex; flex-direction: column; gap: 10px; }
.scrap-field-row { display: flex; gap: 12px; flex-wrap: wrap; }
.scrap-field { flex: 1; min-width: 150px; display: flex; flex-direction: column; gap: 4px; }
.coproduct-notice {
  padding: 10px 12px; border: 1px solid #f59e0b; border-radius: 8px; background: #fffbeb;
  display: flex; flex-direction: column; gap: 6px;
}
.coproduct-notice-loading { font-size: 12px; color: #92400e; font-weight: 600; }
.coproduct-notice-title { font-size: 13px; font-weight: 700; color: #92400e; }
.coproduct-toggle { cursor: pointer; font-size: 12px; }
.coproduct-collapsed { padding: 4px 8px; gap: 0; }
.coproduct-notice-children { display: flex; flex-wrap: wrap; gap: 6px; }
.coproduct-chip {
  display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px;
  border-radius: 999px; background: #fff; border: 1px solid #fcd34d;
  color: #78350f; font-size: 12px; font-weight: 700;
}
.coproduct-chip-name { font-weight: 500; }
.work-date-area { margin-bottom: 12px; }
.work-date-input { padding: 6px 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; }
.work-date-hint { font-size: 11px; color: #888; margin-top: 2px; }
.action-bar { display: flex; gap: 8px; }
.btn-save {
  height: 44px; padding: 0 24px; background: #4e7cbf; color: #fff; border: none;
  border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 700;
}
.btn-save:disabled { opacity: 0.4; cursor: default; }
.btn-cancel {
  height: 44px; padding: 0 16px; background: #fff; color: #666; border: 1px solid #ccc;
  border-radius: 8px; cursor: pointer; font-size: 13px;
}

/* 最近の記録列 */
.recent-list { display: flex; flex-direction: column; gap: 4px; }
.recent-item {
  padding: 4px 6px; background: #f8fafc; border-radius: 6px; font-size: 11px;
}
.recent-row1 { display: flex; gap: 6px; align-items: baseline; }
.recent-row2 { display: flex; gap: 6px; align-items: baseline; margin-top: 1px; }
.recent-date { color: #64748b; font-weight: 600; white-space: nowrap; }
.recent-clock { color: #1f2a44; font-weight: 600; white-space: nowrap; }
.recent-qty { color: #16a34a; font-weight: 700; white-space: nowrap; margin-left: auto; }
.recent-state { color: #4a7ae5; font-weight: 600; white-space: nowrap; margin-left: auto; }
.recent-type-label { font-weight: 600; color: #1f2a44; white-space: nowrap; }
.recent-product { color: #64748b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.empty-recent { text-align: center; padding: 24px 0; color: #aaa; font-size: 12px; }

/* トースト */
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  padding: 12px 24px; border-radius: 8px; background: #323232; color: #fff;
  font-size: 14px; font-weight: 600; z-index: 300; box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  white-space: nowrap;
}
.toast.error { background: #e53935; }
.toast-enter-active, .toast-leave-active { transition: opacity 0.3s; }
.toast-enter-from, .toast-leave-to { opacity: 0; }

/* レスポンシブ */
@media (max-width: 1180px) {
  .four-col-layout { grid-template-columns: 140px 210px minmax(0, 1fr) 160px; }
  .col-controls, .col-list, .col-form, .col-recent { padding: 8px; }
}
@media (max-width: 1024px) {
  .four-col-layout { grid-template-columns: 120px 180px minmax(0, 1fr) 140px; }
  .col-controls, .col-list, .col-form, .col-recent { padding: 6px; }
}
@media (max-width: 860px) {
  .four-col-layout {
    grid-template-columns: 110px 160px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
  }
  .col-controls { grid-row: 1; grid-column: 1; }
  .col-list { grid-row: 1; grid-column: 2; }
  .col-form { grid-row: 1; grid-column: 3; }
  .col-recent { grid-row: 2; grid-column: 1 / -1; border-top: 1px solid #dde1e8; border-right: none; max-height: 200px; }
  .col-recent .recent-list { display: flex; flex-wrap: wrap; gap: 4px; }
  .col-recent .recent-item { flex: 0 0 auto; }
}
@media (max-width: 680px) {
  .four-col-layout {
    grid-template-columns: minmax(0, 1fr);
    overflow-y: auto;
  }
  .col-controls, .col-list, .col-form, .col-recent {
    overflow: visible; border-right: none; border-bottom: 1px solid #dde1e8; padding: 8px;
    grid-row: auto; grid-column: auto;
  }
  .col-recent { border-bottom: none; max-height: none; }
  .col-recent .recent-list { display: flex; flex-direction: column; }
}
.ds-btn { margin-left: 8px; padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-btn:hover { background: #e2e8f0; }
/* embed-tablet: 親フレーム（DualProcessInput）から iframe で埋め込まれた時 */
.header-embed {
  padding: 2px 8px;
  gap: 6px;
}
.embed-icon-btn, .btn-recent-toggle {
  height: 30px; width: 30px; padding: 0; border: 1px solid #cbd5e1; background: #fff; color: #64748b;
  border-radius: 4px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.embed-icon-btn:hover, .btn-recent-toggle:hover { background: #f1f5f9; }
.embed-icon-btn.active { border-color: #14532d; background: #15803d; color: #fff; }
.btn-recent-toggle.active { border-color: #14532d; background: #15803d; color: #fff; }
.embed-separator { width: 1px; height: 20px; background: #d1d5db; flex-shrink: 0; }
.embed-text-icon { font-size: 12px; font-weight: 800; line-height: 1; }
.desktop-process-input.embed-tablet .four-col-layout {
  grid-template-columns: 35fr 65fr;
}
.desktop-process-input.embed-tablet.show-recent .four-col-layout {
  grid-template-columns: 35fr 65fr 180px;
}
.desktop-process-input.embed-tablet .col-list,
.desktop-process-input.embed-tablet .col-form,
.desktop-process-input.embed-tablet .col-recent {
  padding: 0;
  grid-column: auto;
  grid-row: auto;
}
.desktop-process-input.embed-tablet .plan-item {
  padding: 2px 4px; border-radius: 4px;
}
.desktop-process-input.compact-form-tablet .form-area { gap: 4px; padding: 4px !important; }
.desktop-process-input.compact-form-tablet .product-header { padding-bottom: 2px; }
.desktop-process-input.compact-form-tablet .product-code-large { font-size: 16px; }
.desktop-process-input.compact-form-tablet .product-name { margin-top: 0; font-size: 12px; }
.desktop-process-input.compact-form-tablet .product-time-label { margin-top: 0; font-size: 11px; }
.desktop-process-input.compact-form-tablet .action-btns-section { flex-direction: row; align-items: center; gap: 4px; }
.desktop-process-input.compact-form-tablet .op-action-btns { gap: 4px; }
.desktop-process-input.compact-form-tablet .op-action-btn { height: 26px; padding: 0 6px; font-size: 11px; border-radius: 4px; border-width: 1px; }
.desktop-process-input.compact-form-tablet .stats-and-actions { gap: 4px; }
.desktop-process-input.compact-form-tablet .current-actual { gap: 8px; }
.desktop-process-input.compact-form-tablet .stat-label { font-size: 10px; }
.desktop-process-input.compact-form-tablet .stat-value { font-size: 16px; }
.desktop-process-input.compact-form-tablet .qty-input-area { gap: 4px; }
.desktop-process-input.compact-form-tablet .qty-row { gap: 8px; }
.desktop-process-input.compact-form-tablet .qty-input { height: 30px; width: 54px; font-size: 14px; padding: 0 4px; border-width: 1px; border-radius: 4px; }
.desktop-process-input.compact-form-tablet .batch-input { height: 30px; width: 82px; font-size: 12px; padding: 0 4px; border-radius: 4px; }
.desktop-process-input.compact-form-tablet .qty-label { font-size: 11px; }
.desktop-process-input.compact-form-tablet .btn-quick { padding: 2px 8px; font-size: 12px; border-radius: 4px; }
.desktop-process-input.compact-form-tablet .reason-area { gap: 2px; }
.desktop-process-input.compact-form-tablet .reason-area textarea { padding: 4px; }
.desktop-process-input.compact-form-tablet .work-date-area { margin-bottom: 4px; }
.desktop-process-input.compact-form-tablet .work-date-input { height: 30px; font-size: 12px; padding: 0 4px; border-radius: 4px; }
.desktop-process-input.compact-form-tablet .coproduct-notice { padding: 4px 8px; gap: 4px; }
.desktop-process-input.compact-form-tablet .coproduct-notice-children { gap: 4px; }
.desktop-process-input.compact-form-tablet .coproduct-chip { padding: 2px 6px; font-size: 11px; }
.desktop-process-input.compact-form-tablet .action-bar { gap: 4px; }
.desktop-process-input.compact-form-tablet .btn-save { height: 34px; padding: 0 16px; font-size: 13px; border-radius: 6px; }
.desktop-process-input.compact-form-tablet .btn-cancel { height: 34px; padding: 0 12px; font-size: 12px; border-radius: 6px; }
.desktop-process-input.compact-form-tablet .plan-qty-input { width: 46px; font-size: 13px; }
.desktop-process-input.compact-form-tablet .plan-time-input { width: 60px; font-size: 12px; }
.desktop-process-input.compact-form-tablet .plan-qty-btn { padding: 1px 6px; font-size: 11px; }
.embed-tablet .form-area { gap: 4px; padding: 4px !important; }
.embed-tablet .product-header { padding-bottom: 2px; }
.embed-tablet .product-code-large { font-size: 16px; }
.embed-tablet .product-name { margin-top: 0; font-size: 12px; }
.embed-tablet .product-time-label { margin-top: 0; font-size: 11px; }
.embed-tablet .stats-and-actions { gap: 4px; }
.embed-tablet .current-actual { gap: 8px; }
.embed-tablet .stat-label { font-size: 10px; }
.embed-tablet .stat-value { font-size: 16px; }
.embed-tablet .reason-area { gap: 2px; }
.embed-tablet .reason-area textarea { padding: 4px; }
.embed-tablet .work-date-area { margin-bottom: 4px; }
.embed-tablet .action-bar { gap: 4px; }
.embed-tablet .coproduct-notice { padding: 4px 8px; gap: 4px; }
.embed-tablet .qty-input-area { gap: 4px; }
.embed-tablet .qty-row { gap: 8px; }
.embed-tablet .qty-input { height: 30px; width: 54px; font-size: 14px; padding: 0 4px; border-width: 1px; border-radius: 4px; }
.embed-tablet .batch-input { height: 30px; width: 82px; font-size: 12px; padding: 0 4px; border-radius: 4px; }
.embed-tablet .qty-label { font-size: 11px; }
.embed-tablet .btn-quick { padding: 2px 8px; font-size: 12px; border-radius: 4px; }
.embed-tablet .work-date-input { height: 30px; font-size: 12px; padding: 0 4px; border-radius: 4px; }
.embed-tablet .plan-qty-input { width: 46px; font-size: 13px; }
.embed-tablet .plan-time-input { width: 60px; font-size: 12px; }
.embed-tablet .plan-qty-btn { padding: 1px 6px; font-size: 11px; }
</style>
