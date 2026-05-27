<template>
  <div class="mobile-input" :class="[pageModeClass, { 'tablet-input': isTabletLayout, 'embed-tablet': isEmbeddedTablet }]">
    <div class="mobile-header">
      <h2>{{ pageTitle }} <button class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button></h2>
      <div class="header-info">
        <span class="date">{{ currentDate }}</span>
        <div class="header-actions">
          <button class="btn-inspection-nav btn-checksheet-nav" @click="openIntegratedChecksheetOperation">チェックシート実施</button>
          <button class="btn-inspection-nav" @click="openEquipmentInspection">設備点検</button>
        </div>
      </div>
    </div>

    <div class="section inline-row dual-row compact-label-row">
      <div class="inline-group">
        <label class="label-required inline-label">{{ t('processInput.line') }}</label>
        <div class="line-select-row">
          <select v-model="selectedLineId" @change="onLineChange" class="input-large flex-input" :disabled="isEmbeddedTablet">
            <option value="">{{ t('processInput.selectLine') }}</option>
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
          >
            {{ isSupportMode ? '応援ON' : '応援OFF' }}
          </button>
        </div>
      </div>

      <div class="inline-group">
        <label class="label-required inline-label">{{ t('processInput.process') }}</label>
        <select
          v-model="selectedProcessId"
          @change="onProcessChange"
          class="input-large flex-input"
          :disabled="!selectedLineId || isEmbeddedTablet"
        >
          <option value="">{{ t('processInput.selectProcess') }}</option>
          <option v-for="p in filteredProcesses" :key="p.id" :value="p.id">
            {{ p.process_code }} - {{ p.process_name }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="!isScrapOnlyPage" class="section inline-row dual-row">
      <div v-if="selectedProcessId && showRecordTypeSelection" class="inline-group">
        <label class="label-required inline-label">{{ t('processInput.recordType') }}</label>
        <div class="type-buttons inline-buttons">
          <button
            v-for="type in availableRecordTypes"
            :key="type.value"
            @click="record.record_type = type.value"
            class="type-btn record-type-btn"
            :class="{ active: record.record_type === type.value }"
          >
            {{ type.label }}
          </button>
          <div
            v-if="shouldShowOperatorActionRow"
            class="operator-action-buttons operator-action-buttons-inline"
          >
            <button
              v-if="shouldShowAutoStartAction"
              type="button"
              class="operator-action-btn active"
              disabled
            >
              {{ t(OPERATOR_ACTION_LABEL_KEYS.START) }}
            </button>
            <button
              v-for="action in shouldShowOperatorActionSelector ? operatorActionOptions : []"
              :key="action.value"
              type="button"
              class="operator-action-btn"
              :class="{ active: isOperatorActionActive(action.value) }"
              @click="selectOperatorAction(action.value)"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
      </div>
      <div
        v-else-if="selectedProcessId && availableRecordTypes.length === 1"
        class="inline-group"
      >
        <label class="inline-label">{{ t('processInput.recordType') }}</label>
        <div class="single-type">{{ availableRecordTypes[0].label }}</div>
      </div>
    </div>

    <div v-if="selectedProcessId && isScrapRecord" class="section inline-row dual-row">
      <div class="inline-group">
        <label class="inline-label">{{ t('processInput.scrapFilter.label') }}</label>
        <select v-model="scrapRelationFilter" class="input-large flex-input scrap-filter-select">
          <option value="">{{ t('processInput.scrapFilter.all') }}</option>
          <option v-for="opt in scrapRelationOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>
      <div class="inline-group">
        <label class="inline-label">{{ t('processInput.scrapSearch.label') }}</label>
        <input
          v-model="scrapSearchText"
          type="text"
          class="input-large flex-input scrap-filter-input"
          :placeholder="t('processInput.scrapSearch.placeholder')"
        />
      </div>
    </div>

    <div
      v-if="record.record_type === 'PRODUCTION' || (record.record_type === 'SCRAP' && currentProductList.length)"
      class="planned-buttons"
    >
      <div class="planned-header">
        <div v-if="currentProductList.length" class="planned-nav">
          <button
            type="button"
            class="slot-btn"
            :disabled="!canPrevSlot"
            @click="goPrevSlot"
          >
            «
          </button>
          <span class="planned-label">{{ t('processInput.plannedToday') }}</span>
          <span v-if="plannedTimeLabel" class="slot-label">{{ plannedTimeLabel }}</span>
          <button
            type="button"
            class="slot-btn"
            :disabled="!canNextSlot"
            @click="goNextSlot"
          >
            »
          </button>
        </div>
        <label v-if="currentProductList.length" class="current-time-toggle">
          <input
            type="checkbox"
            v-model="filterCurrentTime"
            @change="onCurrentTimeToggle"
            :disabled="isPlannedProductsLoading"
          />
          <span>{{ t('processInput.currentTimeOnly') }}</span>
        </label>
      </div>
      <div v-if="isPlannedProductsLoading" class="hint">{{ t('processInput.loadingProductList') }}</div>
      <div v-if="record.record_type === 'SCRAP'" class="planned-cards">
        <div
          v-for="p in displayProductList"
          :key="`${p.plan_date}-${p.product}-${p.process}-${p.sequence_no || ''}`"
          class="planned-card"
          :class="{ active: record.product_id === p.product }"
          @click="selectPlannedProduct(p)"
        >
          <div class="card-image">
            <img v-if="getImageUrl(p)" :src="getImageUrl(p)" alt="product image" />
            <div v-else class="no-image">{{ t('processInput.noImage') }}</div>
          </div>
          <div class="card-body">
            <div class="card-code">{{ p.product_code || t('processInput.unsetProductCode') }}</div>
            <div class="card-name">{{ p.product_name || '' }}</div>
            <div class="card-plan" v-if="p.plan_qty != null">
              {{ t('processInput.planLabel', { qty: formatNumber(p.plan_qty) }) }}
            </div>
          </div>
        </div>
        <div
          v-if="record.record_type === 'SCRAP' && currentProductList.length && !displayProductList.length && isScrapFilterActive"
          class="hint"
        >
          {{ t('processInput.scrapFilter.noMatch') }}
        </div>
      </div>
      <div v-else-if="currentProductList.length" class="planned-list">
        <button
          v-for="(p, idx) in displayProductList"
          :key="`${p.plan_date}-${p.product}-${p.process}-${p.sequence_no || ''}`"
          class="btn-planned"
          :class="{
            active: record.product_id === p.product,
            'current-processing': isCurrentProcessingProduct(p.product),
          }"
          type="button"
          @click="selectPlannedProduct(p)"
        >
          {{ getDisplayProductCode(p) }}
          <span
            v-if="p.plan_qty != null"
            class="plan-qty"
            :class="{
              'plan-qty--done': getPlanQtyState(p) === 'done',
              'plan-qty--over': getPlanQtyState(p) === 'over',
            }"
          >
            {{ t('processInput.planQtyBadge', { qty: getPlanQtyBadgeLabel(p) }) }}
          </span>
          <span v-if="isTempEndedProduct(p.product)" class="status-badge status-badge--temp-end">
            {{ t('processInput.tempEndBadge') }}
          </span>
        </button>
      </div>
    </div>

    <div v-if="selectedProcessId && currentProcessingLabel" class="section current-processing-banner">
      {{ currentProcessingLabel }}
    </div>
    <div v-if="selectedProcessId && pauseNoticeLabel" class="section current-processing-banner pause-notice-banner">
      {{ pauseNoticeLabel }}
    </div>

    <div v-if="record.record_type" class="section inline-row product-row">
      <div class="label-stack">
        <label :class="record.record_type === 'PRODUCTION' ? 'label-required inline-label' : 'inline-label'">
          {{ t('processInput.product') }}
        </label>
        <div
          v-if="record.record_type === 'PRODUCTION' || record.record_type === 'SCRAP'"
          class="product-toggle"
        >
          <button type="button" class="btn-link toggle-link" @click="toggleManualProduct">
            {{ manualProduct ? t('processInput.backToSearch') : t('processInput.manualInput') }}
          </button>
        </div>
      </div>

      <div class="product-inputs">
        <template v-if="currentProductList.length && !manualProduct">
          <div class="product-select-row">
            <select v-model="record.product_id" class="input-large flex-input">
              <option value="">{{ t('processInput.selectProduct') }}</option>
              <option
                v-for="p in displayProductList"
                :key="`${p.plan_date}-${p.product_code}-${p.sequence_no || ''}`"
                :value="p.product"
              >
                {{ p.product_code }} - {{ p.product_name || '' }}
                {{ getPlanQtyParenLabel(p) }}
              </option>
            </select>
          </div>
        </template>

        <template v-if="manualProduct || !currentProductList.length">
          <div class="product-select-row">
            <select v-model="record.product_id" class="input-large flex-input">
              <option value="">{{ t('processInput.selectProductCode') }}</option>
              <option
                v-for="p in manualProductOptions"
                :key="p.id"
                :value="p.id"
              >
                {{ p.product_code }} - {{ p.product_name || '' }}
              </option>
            </select>
          </div>
          <div v-if="manualProductsLoading" class="hint">{{ t('processInput.loadingProductList') }}</div>
          <div v-if="!currentProductList.length" class="hint">
            {{ t('processInput.noPlanHint') }}
          </div>
        </template>
        <div
          v-if="record.record_type === 'PRODUCTION' && (selectedCoproductNoticeLoading || selectedCoproductChildren.length)"
          class="coproduct-notice"
        >
          <div v-if="selectedCoproductNoticeLoading" class="coproduct-notice__loading">
            {{ t('processInput.coproductNotice.loading') }}
          </div>
          <template v-else>
            <div class="coproduct-notice__title">
              {{
                t('processInput.coproductNotice.message', {
                  code: selectedCoproductParentCode || record.product_code || '',
                })
              }}
            </div>
            <div class="coproduct-notice__label">
              {{ t('processInput.coproductNotice.childrenLabel') }}
            </div>
            <div class="coproduct-notice__children">
              <span
                v-for="child in selectedCoproductChildren"
                :key="child.product_id"
                class="coproduct-notice__chip"
              >
                {{ child.product_code }}
                <span v-if="child.product_name" class="coproduct-notice__chip-name">
                  {{ child.product_name }}
                </span>
              </span>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div
      v-if="shouldShowOperatorActionRow && !showRecordTypeSelection"
      class="section operator-action-row"
    >
      <label class="label-required inline-label operator-action-title">{{ t('processInput.operatorAction') }}</label>
      <div v-if="shouldShowOperatorActionSelector" class="operator-action-buttons">
        <button
          v-for="action in operatorActionOptions"
          :key="action.value"
          type="button"
          class="operator-action-btn"
          :class="{ active: isOperatorActionActive(action.value) }"
          @click="selectOperatorAction(action.value)"
        >
          {{ action.label }}
        </button>
      </div>
      <div v-else-if="shouldShowAutoStartAction" class="operator-action-buttons">
        <button type="button" class="operator-action-btn active" disabled>
          {{ t(OPERATOR_ACTION_LABEL_KEYS.START) }}
        </button>
      </div>
    </div>

    <div
      v-if="(record.record_type === 'PRODUCTION' && hasSelectedProduct() && hasEffectiveOperatorAction()) || record.record_type === 'SCRAP'"
      class="form-section"
      :class="formModeClass"
    >
      <div class="section inline-row qty-row">
        <div v-if="shouldShowQtyInput" class="inline-group qty-group">
          <label class="label-required inline-label">
            {{
              record.record_type === 'SCRAP'
                ? t('processInput.scrapQty')
                : t('processInput.productionQty')
            }}
          </label>
          <input
            type="number"
            v-model.number="record.qty"
            :min="qtyInputMin"
            step="1"
            inputmode="numeric"
            class="input-large input-qty flex-input"
            :placeholder="t('processInput.qtyPlaceholder')"
          />
        </div>
        <div class="inline-group">
          <label class="inline-label">{{ t('processInput.batchNo') }}</label>
          <input
            type="text"
            v-model="record.batch_no"
            :placeholder="t('processInput.batchNoPlaceholder')"
            class="input-normal flex-input"
          />
        </div>
      </div>

      <div class="quick-btns" v-if="shouldShowQtyInput && quickQtyPresets.length">
        <button
          v-for="preset in quickQtyPresets"
          :key="preset"
          @click="record.qty = preset"
          class="btn-quick"
        >
          {{ preset }}
        </button>
      </div>

      <div v-if="planStatus" class="plan-status">
        <div class="plan-status__title">{{ t('processInput.planSummaryTitle') }}</div>
        <div class="plan-status__row">
          <span class="plan-status__label">{{ t('processInput.planQtyShort') }}</span>
          <span class="plan-status__value">{{ formatNumber(planStatus.planQty) }}</span>
        </div>
        <div class="plan-status__row">
          <span class="plan-status__label">{{ t('processInput.recordedQty') }}</span>
          <span class="plan-status__value">{{ formatNumber(planStatus.actualQty) }}</span>
        </div>
        <div class="plan-status__row">
          <span class="plan-status__label">{{ t('processInput.remainingQty') }}</span>
          <span class="plan-status__value">{{ formatNumber(planStatus.remaining) }}</span>
        </div>
        <div class="plan-status__row plan-status__row--muted" v-if="shouldShowQtyInput && record.qty">
          <span class="plan-status__label">{{ t('processInput.remainingAfterEntry') }}</span>
          <span class="plan-status__value">{{ formatNumber(planStatus.remainingAfterInput) }}</span>
        </div>
      </div>

      <div v-if="requiresOperatorActionReason" class="section">
        <label class="label-required">{{ t(operatorActionReasonLabelKey) }}</label>
        <select
          v-if="isPauseReasonDropdown"
          v-model="record.operator_action_reason"
          class="input-large"
        >
          <option value="">{{ t('processInput.pauseReasonSelectPlaceholder') }}</option>
          <option v-for="reason in pauseReasons" :key="reason.value" :value="reason.value">
            {{ reason.label }}
          </option>
        </select>
        <select
          v-else-if="isTempEndReasonDropdown"
          v-model="record.operator_action_reason"
          class="input-large"
        >
          <option value="">{{ t('processInput.tempEndReasonSelectPlaceholder') }}</option>
          <option v-for="reason in tempEndReasons" :key="reason.value" :value="reason.value">
            {{ reason.label }}
          </option>
        </select>
        <input
          v-else
          type="text"
          v-model="record.operator_action_reason"
          :placeholder="t(operatorActionReasonPlaceholderKey)"
          class="input-normal"
        />
      </div>

      <div v-if="isScrapRecord" class="section inline-row dual-row">
        <div class="inline-group">
          <label class="label-required inline-label">{{ t('processInput.disposition') }}</label>
          <select v-model="record.disposition_status" class="input-large flex-input">
            <option value="">{{ t('processInput.selectDisposition') }}</option>
            <option v-for="opt in scrapDispositionOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
        <div class="inline-group">
          <label class="label-required inline-label">{{ t('processInput.productionRecorded') }}</label>
          <select v-model="record.is_production_recorded" class="input-large flex-input">
            <option value="">-- 選択 --</option>
            <option v-for="opt in productionRecordedOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <div class="hint">{{ t('processInput.productionRecordedHint') }}</div>
        </div>
      </div>
      <div v-if="isScrapRecord" class="hint">{{ t('processInput.dispositionHint') }}</div>

      <div v-if="isScrapRecord" class="section">
        <label class="label-required">{{ t('processInput.reason') }}</label>
        <select v-model="record.reason" class="input-large">
          <option value="">{{ t('processInput.selectReason') }}</option>
          <option v-for="reason in scrapReasons" :key="reason.value" :value="reason.value">
            {{ reason.label }}
          </option>
        </select>
        <div v-if="record.reason === 'OTHER'" class="hint">{{ t('processInput.reasonOtherHint') }}</div>
      </div>

      <div v-if="record.reason === 'OTHER'" class="section">
        <label class="label-required">{{ t('processInput.reasonDetail') }}</label>
        <input
          type="text"
          v-model="record.reason_detail"
          :placeholder="t('processInput.reasonDetailPlaceholder')"
          class="input-normal"
        />
      </div>

      <div class="section inline-row row-label-input">
        <label class="label-required inline-label label-side">{{ t('processInput.operator') }}</label>
        <input
          type="text"
          v-model="record.operator_name"
          :placeholder="t('processInput.operatorPlaceholder')"
          class="input-normal flex-input"
        />
      </div>

      <div class="section">
        <label :class="{ 'label-required': requiresTempEndOtherRemarks }">
          {{ t('processInput.remarks') }}
        </label>
        <textarea
          v-model="record.remarks"
          rows="3"
          :placeholder="t('processInput.remarksPlaceholder')"
          class="textarea-normal"
        ></textarea>
        <div v-if="requiresTempEndOtherRemarks" class="hint">
          {{ t('processInput.tempEndRemarksRequiredHint') }}
        </div>
      </div>
    </div>

    <div v-if="record.record_type === 'EQUIPMENT_STATE'" class="form-section">
      <h3 class="section-title">{{ t('processInput.equipmentStateTitle') }}</h3>

      <div class="section">
        <label class="label-required">{{ t('processInput.state') }}</label>
        <div class="state-buttons">
          <button
            v-for="state in equipmentStates"
            :key="state.value"
            @click="setEquipmentState(state.value)"
            class="state-btn"
            :class="[
              { active: record.equipment_state === state.value },
              `state-${state.value.toLowerCase()}`
            ]"
          >
            {{ state.label }}
          </button>
        </div>
      </div>

      <div class="section">
        <label>{{ t('processInput.remarks') }}</label>
        <textarea
          v-model="record.remarks"
          rows="3"
          :placeholder="t('processInput.stateRemarksPlaceholder')"
          class="textarea-normal"
        ></textarea>
      </div>
    </div>

    <div v-if="record.record_type" class="action-section action-sticky">
      <button
        @click="submitRecord"
        :disabled="!canSubmit || submitting"
        class="btn-submit"
      >
        {{ submitting ? t('processInput.submitting') : t('processInput.submit') }}
      </button>
    </div>

    <div v-if="selectedProcessId && recentRecordsForDisplay.length" class="recent-section">
      <h3 class="section-title">{{ t('processInput.recentRecords') }}</h3>
      <div class="record-list">
        <div
          v-for="rec in recentRecordsForDisplay"
          :key="rec.id"
          class="record-item"
          :style="getRecentRecordColorStyle(rec)"
        >
          <div class="record-time">
            <div class="record-date">{{ formatDate(rec.timestamp) }}</div>
            <div class="record-clock">{{ formatTime(rec.timestamp) }}</div>
          </div>
          <div class="record-type">
            <div class="record-type__label">{{ getRecentRecordTypeLabel(rec) }}</div>
            <div v-if="rec.product_code" class="record-type__product">{{ rec.product_code }}</div>
          </div>
          <div class="record-qty" v-if="rec.qty > 0">{{ formatRecentQtyWithPlan(rec) }}</div>
          <div class="record-state" v-if="rec.equipment_state">
            {{ rec.equipment_state_display }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header">
          <h3>データソース — {{ pageTitle }}</h3>
          <button class="ds-close" @click="showDataSource = false">×</button>
        </div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr><td>取得/保存</td><td>t_process_realtime_record</td><td>工程リアルタイム記録（生産完成・仕損・設備状態・作業者アクション）</td></tr>
            <tr><td>保存</td><td>t_scrap_record / t_scrap_record_detail</td><td>仕損記録・仕損明細（仕損登録時に自動作成）</td></tr>
            <tr><td>取得</td><td>line_backlog</td><td>計画品番リスト・計画数・実績数の表示</td></tr>
            <tr><td>更新</td><td>line_backlog</td><td>実績数(actual_qty)・仕損数(scrap_qty)の加算</td></tr>
            <tr><td>取得</td><td>masters_product / masters_bom / masters_bomitem</td><td>製品マスタ・BOM展開（仕損対象の子部品取得）</td></tr>
            <tr><td>取得</td><td>masters_routing / masters_routingstep / masters_routingstepmaterial</td><td>ルーティング展開（工程別の対象製品取得）</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
const showDataSource = ref(false)
import { authState, ensureAuth } from '@/auth'
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

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : '')
const mediaEnvBase = import.meta.env.VITE_MEDIA_BASE_URL || ''
const browserOrigin = typeof window !== 'undefined' ? window.location.origin : ''
let mediaBaseUrl = ''
if (mediaEnvBase) {
  mediaBaseUrl = mediaEnvBase.replace(/\/$/, '')
} else if (import.meta.env.DEV) {
  // In dev (Vite) we keep the current origin so the dev server can proxy /media for remote devices.
  mediaBaseUrl = browserOrigin
} else {
  // 本番環境では nginx が /media/ を直接配信するため、ブラウザのオリジンをそのまま使用
  mediaBaseUrl = browserOrigin
}

const manualProduct = ref(false)
const manualProducts = ref([])
const manualProductsLoading = ref(false)
const manualProductsLoaded = ref(false)
const manualProductsProcessId = ref(null)
const allPlanProducts = ref([])
const productionProducts = ref([])
const actualQtyByProductFromBacklog = ref(new Map())
const actualQtyByProductCodeFromBacklog = ref(new Map())
const scrapProducts = ref([])
const allScrapProducts = ref([])
const scrapRelationFilter = ref('')
const scrapSearchText = ref('')
const defaultProductId = ref(null)
const productImageMap = ref({})
const productMetaMap = ref({})
// 初期表示は「現在時刻のみ」をON（現在時刻の時間帯を優先表示）
const filterCurrentTime = ref(true)
const timeSlots = ref([])
const activeSlotIndex = ref(null)
const selectedOperatorAction = ref('')
const startedProductIds = ref(new Set())
const startedProductIdsLoaded = ref(false)
const latestOperatorActionByProduct = ref(new Map())
const selectedCoproductChildren = ref([])
const selectedCoproductParentCode = ref('')
const selectedCoproductNoticeLoading = ref(false)
const isPlannedProductsLoading = ref(false)
const bomTreeCache = new Map()
const relatedProductsCacheByProcess = new Map()
let selectedCoproductNoticeRequestSeq = 0
let plannedProductsRequestSeq = 0

const shouldBlockBomService = (lineId = null, processId = null) => {
  const targetLineId = String(lineId ?? selectedLineId.value ?? '').trim()
  const targetProcessId = String(processId ?? selectedProcessId.value ?? '').trim()
  return !filterCurrentTime.value && targetLineId === '81' && targetProcessId === '24'
}

const record = ref({
  record_type: '',
  product_id: '',
  product_code: '',
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

const showRecordTypeSelection = computed(() => availableRecordTypes.value.length > 1)
const pageTitleKeyMap = {
  MobileProcessInput: 'processInput.pageTitleWork',
  TabletProcessInput: 'processInput.pageTitleWork',
  ScrapRecordInput: 'processInput.pageTitleScrap',
}

const isTabletLayout = computed(() => route.name === 'TabletProcessInput')
const isEmbeddedTablet = computed(() => String(route.query.embed || '') === 'tablet')

const pageTitle = computed(() => {
  const key = pageTitleKeyMap[route.name]
  if (key) return t(key)
  return route.meta?.pageTitle || t('processInput.pageTitleWork')
})

const filteredProcesses = computed(() => {
  if (!selectedLineId.value) return processes.value
  return processes.value.filter((p) => String(p.line) === String(selectedLineId.value))
})
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
const isFloorLineSelected = computed(
  () => String(selectedLineObj.value?.line_code || '').trim().toUpperCase() === FLOOR_LINE_CODE
)

const isScrapOnlyPage = computed(() => route.name === 'ScrapRecordInput')
const isScrapRecord = computed(() => record.value.record_type === 'SCRAP')
const activeOperatorActions = new Set(['START', 'PAUSE', 'RESUME'])
const startedStateOperatorActions = new Set(['START', 'RESUME'])
const startedOperatorActions = ['END', 'PAUSE']
const pausedOperatorActions = ['RESUME', 'TEMP_END']

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
    if (!selectedProductId || String(productId) !== selectedProductId) {
      return true
    }
  }
  return false
})

const shouldAutoStartByProduct = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return false
  if (!startedProductIdsLoaded.value) return false
  const productId = record.value.product_id
  if (!productId) return false
  // 同工程で別製品が開始中（中断含む）の場合は新規STARTを出さない。
  if (hasStartedOtherProduct.value) return false
  return selectedProductWorkState.value === 'NOT_STARTED'
})

const operatorActionOptions = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return []
  if (!hasSelectedProduct()) return []
  if (!startedProductIdsLoaded.value) return []

  if (selectedProductWorkState.value === 'PAUSED') {
    return pausedOperatorActions.map((action) => ({
      value: action,
      label: t(OPERATOR_ACTION_LABEL_KEYS[action]),
    }))
  }
  if (selectedProductWorkState.value === 'TEMP_ENDED') {
    return ['RESUME', 'CANCEL'].map((action) => ({
      value: action,
      label: t(OPERATOR_ACTION_LABEL_KEYS[action]),
    }))
  }
  if (selectedProductWorkState.value === 'STARTED') {
    return startedOperatorActions.map((action) => ({
      value: action,
      label: t(OPERATOR_ACTION_LABEL_KEYS[action]),
    }))
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
const shouldShowOperatorActionSelector = computed(() => {
  return shouldShowOperatorActionRow.value && !shouldAutoStartByProduct.value
})
const shouldShowAutoStartAction = computed(
  () => shouldShowOperatorActionRow.value && shouldAutoStartByProduct.value
)
const isOperatorActionMode = computed(
  () => record.value.record_type === 'PRODUCTION' && !!effectiveOperatorAction.value
)
const isQtyRequiredOperatorAction = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return false
  const actionKey = String(effectiveOperatorAction.value || '').toUpperCase()
  return ['END', 'PAUSE'].includes(actionKey)
})
const shouldShowQtyInput = computed(() => {
  if (record.value.record_type === 'SCRAP') return true
  if (record.value.record_type !== 'PRODUCTION') return false
  return isQtyRequiredOperatorAction.value
})
const requiresOperatorActionReason = computed(
  () =>
    record.value.record_type === 'PRODUCTION' &&
    ['PAUSE', 'TEMP_END'].includes(String(effectiveOperatorAction.value || '').toUpperCase())
)
const operatorActionReasonLabelKey = computed(() =>
  effectiveOperatorAction.value === 'TEMP_END'
    ? 'processInput.tempEndReason'
    : 'processInput.pauseReason'
)
const operatorActionReasonPlaceholderKey = computed(() =>
  effectiveOperatorAction.value === 'TEMP_END'
    ? 'processInput.tempEndReasonPlaceholder'
    : 'processInput.pauseReasonPlaceholder'
)
const isPauseReasonDropdown = computed(
  () => String(effectiveOperatorAction.value || '').toUpperCase() === 'PAUSE'
)
const isTempEndReasonDropdown = computed(
  () => String(effectiveOperatorAction.value || '').toUpperCase() === 'TEMP_END'
)
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

const OPERATOR_ACTION_LABEL_KEYS = {
  START: 'processInput.operatorAction.start',
  END: 'processInput.operatorAction.end',
  PAUSE: 'processInput.operatorAction.pause',
  RESUME: 'processInput.operatorAction.resume',
  TEMP_END: 'processInput.operatorAction.tempEnd',
  CANCEL: 'processInput.operatorAction.cancel',
}

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
  {
    value: '設備トラブル',
    label: t('processInput.pauseReasonOption.equipmentTrouble'),
  },
  {
    value: '治具トラブル',
    label: t('processInput.pauseReasonOption.jigTrouble'),
  },
  {
    value: '品質トラブル',
    label: t('processInput.pauseReasonOption.qualityTrouble'),
  },
  {
    value: 'ティーチング',
    label: t('processInput.pauseReasonOption.teaching'),
  },
  {
    value: 'ワイヤ交換',
    label: t('processInput.pauseReasonOption.wireChange'),
  },
  {
    value: '部品ショート',
    label: t('processInput.pauseReasonOption.partsShortage'),
  },
  {
    value: '班長/対応者待ち',
    label: t('processInput.pauseReasonOption.leaderWait'),
  },
  {
    value: '工程指導',
    label: t('processInput.pauseReasonOption.processGuidance'),
  },
  {
    value: '３ｓ活動',
    label: t('processInput.pauseReasonOption.activity3s'),
  },
  {
    value: '改善活動',
    label: t('processInput.pauseReasonOption.improvement'),
  },
  {
    value: 'その他',
    label: t('processInput.pauseReasonOption.other'),
  },
])

const tempEndReasons = computed(() => [
  {
    value: '本日設備復旧不可',
    label: t('processInput.tempEndReasonOption.equipmentUnrecoverableToday'),
  },
  {
    value: '本日治具使用不可',
    label: t('processInput.tempEndReasonOption.jigUnavailableToday'),
  },
  {
    value: '他へ製品切り替え',
    label: t('processInput.tempEndReasonOption.switchProduct'),
  },
  {
    value: 'その他',
    label: t('processInput.tempEndReasonOption.other'),
  },
])

const quickQtyPresets = ref([])

const ensureScrapDefaults = () => {
  if (record.value.record_type !== 'SCRAP') return
  if (!record.value.qty || record.value.qty <= 0) {
    record.value.qty = 1
  }
  if (!(record.value.disposition_status || '').trim()) {
    record.value.disposition_status = 'REJECTED'
  }
}

const ensureDefaultRecordType = () => {
  const types = availableRecordTypes.value
  if (!types.length) {
    record.value.record_type = ''
    return
  }

  const exists = types.some((t) => t.value === record.value.record_type)
  if (types.length === 1) {
    record.value.record_type = types[0].value
    return
  }

  if (!exists) {
    record.value.record_type = ''
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
  if (typeof window === 'undefined') return ''
  const candidates = [
    'currentUserName',
    'userName',
    'username',
    'loginUser',
    'operatorName',
  ]
  for (const key of candidates) {
    const v = window.localStorage ? window.localStorage.getItem(key) : ''
    if (v && v.trim()) return v.trim()
  }
  return ''
}

const defaultOperatorName = ref(resolveDefaultOperator())

watch(
  () => authState.user,
  () => {
    const resolved = resolveDefaultOperator()
    if (resolved && resolved !== defaultOperatorName.value) {
      defaultOperatorName.value = resolved
    }
    if (!(record.value.operator_name || '').trim()) {
      record.value.operator_name = resolved
    }
  }
)

watch(
  [availableLines, preferredUserLineId],
  ([nextLines, nextPreferred]) => {
    const candidateList = Array.isArray(nextLines) ? nextLines : []
    const exists = candidateList.some((line) => String(line.id) === String(selectedLineId.value))
    if (exists) return
    if (nextPreferred && candidateList.some((line) => String(line.id) === String(nextPreferred))) {
      selectedLineId.value = String(nextPreferred)
      return
    }
    selectedLineId.value = candidateList.length ? String(candidateList[0].id) : ''
  },
  { immediate: true }
)

watch(
  ownLines,
  (nextOwnLines) => {
    if (isSupportMode.value) return
    const ownIds = new Set((nextOwnLines || []).map((line) => String(line.id)))
    if (selectedLineId.value && ownIds.has(String(selectedLineId.value))) return
    const preferred = preferredUserLineId.value
    if (preferred && ownIds.has(String(preferred))) {
      selectedLineId.value = String(preferred)
      onLineChange()
      return
    }
    if (nextOwnLines.length) {
      selectedLineId.value = String(nextOwnLines[0].id)
      onLineChange()
    }
  },
)

watch(
  availableRecordTypes,
  () => {
    ensureDefaultRecordType()
  },
  { immediate: true }
)

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
  const exists = equipmentStates.value.some((s) => s.value === cached)
  return exists ? cached : ''
}

const saveEquipmentStateCache = (state) => {
  if (typeof window === 'undefined' || !window.localStorage) return
  const key = equipmentStateStorageKey.value
  if (!key) return
  if (!state) return
  window.localStorage.setItem(key, state)
}

const setEquipmentState = (state) => {
  record.value.equipment_state = state
  saveEquipmentStateCache(state)
}

const restoreEquipmentStateIfNeeded = () => {
  if (record.value.record_type !== 'EQUIPMENT_STATE') return
  if (record.value.equipment_state) return
  if (isProductionRunning.value) {
    setEquipmentState('RUNNING')
    return
  }
  const cached = loadEquipmentStateCache()
  if (cached) {
    record.value.equipment_state = cached
  }
}

const getWorkDate = () => {
  // 勤務開始 08:00 を日付の境目にする。08:00 未満は前日扱い。
  const now = new Date()
  const logical = new Date(now)
  logical.setHours(logical.getHours() - 8)
  return logical
}

const currentDate = computed(() => {
  const logical = getWorkDate()
  return logical.toLocaleDateString(localeCode.value, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short'
  })
})

const currentDateYmd = computed(() => {
  const logical = getWorkDate()
  const y = logical.getFullYear()
  const m = String(logical.getMonth() + 1).padStart(2, '0')
  const d = String(logical.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
})

const currentProductList = computed(() => {
  if (record.value.record_type === 'PRODUCTION') {
    return productionProducts.value
  } else if (record.value.record_type === 'SCRAP') {
    return scrapProducts.value
  }
  return []
})

const productCodeLookup = computed(() => {
  const lookup = new Map()
  const apply = (pid, code) => {
    if (pid === null || pid === undefined || pid === '') return
    const normalizedCode = String(code || '').trim()
    if (!normalizedCode) return
    const key = String(pid)
    if (!lookup.has(key)) {
      lookup.set(key, normalizedCode)
    }
  }

  const planLikeLists = [
    ...(Array.isArray(displayProductList.value) ? displayProductList.value : []),
    ...(Array.isArray(currentProductList.value) ? currentProductList.value : []),
    ...(Array.isArray(allPlanProducts.value) ? allPlanProducts.value : []),
    ...(Array.isArray(productionProducts.value) ? productionProducts.value : []),
    ...(Array.isArray(manualProducts.value) ? manualProducts.value : []),
  ]
  planLikeLists.forEach((item) => {
    apply(item?.product ?? item?.id, item?.product_code)
  })

  ;(Array.isArray(recentRecords.value) ? recentRecords.value : []).forEach((rec) => {
    apply(
      getOperatorActionProductId(rec) ?? rec?.product ?? rec?.product_id,
      rec?.product_code || rec?.event_data?.plan_target?.product_code
    )
  })

  return lookup
})

const currentProcessingProductId = computed(() => {
  if (!selectedProcessId.value || !startedProductIdsLoaded.value) return ''

  const activeProductIds = []
  latestOperatorActionByProduct.value.forEach((action, productId) => {
    if (startedStateOperatorActions.has(String(action || '').toUpperCase())) {
      activeProductIds.push(String(productId))
    }
  })
  if (!activeProductIds.length) return ''

  const selectedProductId = String(record.value.product_id || '')
  if (selectedProductId && activeProductIds.includes(selectedProductId)) {
    return selectedProductId
  }

  const recentActive = (Array.isArray(recentRecords.value) ? recentRecords.value : []).find((rec) => {
    if (rec?.record_type !== 'OPERATOR_ACTION') return false
    const action =
      rec?.event_data?.action ||
      rec?.event_data?.operator_action ||
      rec?.event_data?.action_type ||
      ''
    if (!startedStateOperatorActions.has(String(action).toUpperCase())) return false
    const productId = String(getOperatorActionProductId(rec) || '')
    return !!productId && activeProductIds.includes(productId)
  })
  if (recentActive) {
    return String(getOperatorActionProductId(recentActive) || '')
  }

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

const isProductionRunning = computed(() => {
  return !!currentProcessingProductId.value
})

const tempEndedProductIds = computed(() => {
  const ids = new Set()
  latestOperatorActionByProduct.value.forEach((action, productId) => {
    if (String(action || '').toUpperCase() === 'TEMP_END') {
      ids.add(String(productId))
    }
  })
  return ids
})

const isTempEndedProduct = (productId) => {
  if (!productId) return false
  return tempEndedProductIds.value.has(String(productId))
}

const isCurrentProcessingProduct = (productId) => {
  if (!productId) return false
  return String(currentProcessingProductId.value || '') === String(productId)
}

const pausedProductInfo = computed(() => {
  if (!selectedProcessId.value || !startedProductIdsLoaded.value) return null

  const pausedProductIds = []
  latestOperatorActionByProduct.value.forEach((action, productId) => {
    if (String(action || '').toUpperCase() === 'PAUSE') {
      pausedProductIds.push(String(productId))
    }
  })
  if (!pausedProductIds.length) return null

  const selectedProductId = String(record.value.product_id || '')
  const targetProductId = pausedProductIds.includes(selectedProductId)
    ? selectedProductId
    : pausedProductIds[0]

  const code = productCodeLookup.value.get(String(targetProductId)) || ''

  const recentPauseRecord = (Array.isArray(recentRecords.value) ? recentRecords.value : []).find((rec) => {
    if (rec?.record_type !== 'OPERATOR_ACTION') return false
    const action =
      rec?.event_data?.action ||
      rec?.event_data?.operator_action ||
      rec?.event_data?.action_type ||
      ''
    if (String(action).toUpperCase() !== 'PAUSE') return false
    const pid = String(getOperatorActionProductId(rec) || '')
    return pid && pid === String(targetProductId)
  })

  const reason =
    recentPauseRecord?.event_data?.pause_reason ||
    recentPauseRecord?.event_data?.operator_action_reason ||
    t('processInput.pauseReasonFallback')

  if (!code) return null
  return { code, reason }
})

const pauseNoticeLabel = computed(() => {
  const info = pausedProductInfo.value
  if (!info) return ''
  return t('processInput.pauseNotice', {
    code: info.code,
    reason: info.reason,
  })
})

const isScrapFilterActive = computed(() => {
  return !!scrapRelationFilter.value || !!(scrapSearchText.value || '').trim()
})

const normalizeRelationType = (type) => {
  if (!type) return ''
  return String(type)
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2') // camelCase -> snake_case
    .replace(/[\s\-.]/g, '_')
    .toLowerCase()
}

const getProductMeta = (productId) => {
  if (productId === null || productId === undefined) return {}
  const idStr = String(productId)
  return productMetaMap.value[idStr] || productMetaMap.value[productId] || {}
}

const getOriginProcessId = (item) => {
  if (!item) return null
  return (
    item.origin_process_id ??
    item.source_process_id ??
    item.process ??
    null
  )
}

const isUpstreamProductCandidate = (item) => {
  if (!item) return false
  const relation = normalizeRelationType(item.relation_type)
  if (relation === 'purchased') return false

  const sourcing = String(item.sourcing_type || item.sourcingType || '')
    .toUpperCase()
  const originProcess = getOriginProcessId(item)
  const currentProcess = selectedProcessId.value
  const hasDifferentProcess =
    originProcess &&
    currentProcess &&
    String(originProcess) !== String(currentProcess)

  // 購買品は除外。工程が異なり調達区分が自社/外注なら前工程品扱い。
  if (hasDifferentProcess && sourcing === 'BUY') return false
  if (hasDifferentProcess) return true
  // 調達区分だけで自工程品と分かる場合（工程未設定のMAKE/SUBCONも対象）
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

const getRelationTypesForItem = (item) => {
  if (!item) return []
  const types = []
  const normalized = normalizeRelationType(item.relation_type || '')
  if (normalized) types.push(normalized)
  if (isUpstreamProductCandidate(item)) types.push('upstream_product')
  if (isFinalProductCandidate(item)) types.push('final_product')
  return Array.from(new Set(types))
}

// 排他的なカテゴリ判定: 購入品 > 社内製作品(前工程品) > 自工程製品
// BOM由来の process_id（related-products APIから取得）で判定
const getScrapCategory = (item) => {
  if (!item) return null
  // 1. 購入品判定: relation_type または sourcing_type
  const relation = normalizeRelationType(item.relation_type || '')
  if (relation === 'purchased') return 'purchased'
  const sourcing = String(item.sourcing_type || item.sourcingType || '').toUpperCase()
  if (sourcing === 'BUY') return 'purchased'
  // 2. BOM由来の工程IDで自工程 vs 社内製作品を判定
  //    ※ getOriginProcessId は item.process(常に選択中の工程)にフォールバックするため使わない
  const bomProcessId = item.origin_process_id ?? null
  const currentProcess = selectedProcessId.value
  if (bomProcessId && currentProcess && String(bomProcessId) !== String(currentProcess)) {
    return 'in_house'
  }
  // 3. intermediate で工程不明の場合も社内製作品（前工程からの投入材料）
  if (relation === 'intermediate' && !bomProcessId) return 'in_house'
  // 4. デフォルトは自工程製品
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
      // 自工程製品は利用者が明示選択できるよう未選択状態に戻す
      record.value.is_production_recorded = ''
    }
  }
}

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

  const matchesRelation = (p) => {
    if (!relation) return true
    return getScrapCategory(p) === relation
  }

  const filtered = items.filter((p) => {
    if (!p) return false
    if (!matchesRelation(p)) return false
    if (query && !matchesQuery(p)) return false
    return true
  })
  // もし選択した区分で0件になった場合は、区分条件を外して検索条件のみで返す（使える製品が全く出ないのを防ぐ）
  if (relation && filtered.length === 0) {
    return items.filter((p) => {
      if (!p) return false
      if (query && !matchesQuery(p)) return false
      return true
    })
  }
  return filtered
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
  const code = String(item?.product_code || '').trim() || ''
  if (toSafeNumber(item?.plan_qty) <= 0) return code
  const rank = dailyProductRankMap.value.get(productSeqKey(item))
  if (!rank) return code
  return `${rank} ${code}`
}

const displayProductList = computed(() => {
  if (record.value.record_type === 'SCRAP') {
    return filterScrapCandidates(scrapProducts.value)
  }
  return [...currentProductList.value].sort((a, b) => {
    const seqDiff = getSequenceSortValue(a) - getSequenceSortValue(b)
    if (seqDiff !== 0) return seqDiff
    const planDiff = toSafeNumber(b.plan_qty) - toSafeNumber(a.plan_qty)
    if (planDiff !== 0) return planDiff
    return String(a?.product_code || '').localeCompare(String(b?.product_code || ''))
  })
})

const toSafeNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const parseSeqNo = (raw) => {
  if (raw === null || raw === undefined || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

const productSeqKey = (item) => {
  const pid = String(item?.product || '')
  const seq = parseSeqNo(item?.sequence_no)
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

const buildPlanQtyMapFromSlots = (slots, processId) => {
  const qtyMap = new Map()
  const source = Array.isArray(slots) ? slots : []
  source.forEach((slot) => {
    const items = Array.isArray(slot?.items) ? slot.items : []
    items.forEach((item) => {
      const productId = item?.product
      if (productId === null || productId === undefined || productId === '') return
      const key = `${productId}_${processId}`
      const next = toSafeNumber(qtyMap.get(key)) + toSafeNumber(item?.plan_qty)
      qtyMap.set(key, next)
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

const buildTotalActualByProduct = (items) => {
  const totalMap = new Map()
  ;(Array.isArray(items) ? items : []).forEach((item) => {
    if (!item || item.product === null || item.product === undefined || item.product === '') return
    const key = String(item.product)
    const qty = toSafeNumber(item.actual_qty)
    if (!totalMap.has(key) || qty > toSafeNumber(totalMap.get(key))) {
      totalMap.set(key, qty)
    }
  })
  return totalMap
}

const buildPlanBeforeActiveSlotByProduct = (slots, activeIndex) => {
  const planBeforeMap = new Map()
  const normalizedActiveIndex = Number.isFinite(Number(activeIndex)) ? Number(activeIndex) : 0
  const upperBound = Math.max(Math.min(normalizedActiveIndex, slots.length), 0)

  for (let idx = 0; idx < upperBound; idx += 1) {
    const merged = mergeProductionProductsByProduct(slots[idx]?.items || [])
    merged.forEach((item) => {
      const key = String(item?.product || '')
      if (!key) return
      const nextPlan = toSafeNumber(planBeforeMap.get(key)) + toSafeNumber(item?.plan_qty)
      planBeforeMap.set(key, nextPlan)
    })
  }
  return planBeforeMap
}

const applySlotActualProgress = (slotItems, planBeforeMap, totalActualMap) => {
  return (Array.isArray(slotItems) ? slotItems : []).map((item) => {
    const key = String(item?.product || '')
    if (!key) return item
    const totalActual = toSafeNumber(totalActualMap.get(key))
    const plannedBefore = toSafeNumber(planBeforeMap.get(key))
    const slotActual = Math.max(totalActual - plannedBefore, 0)
    return {
      ...item,
      actual_qty: slotActual,
    }
  })
}

const getPlanQtyState = (item) => {
  const planQty = toSafeNumber(item?.plan_qty)
  const productIdKey = String(item?.product || '').trim()
  const productCodeKey = String(item?.product_code || '').trim()
  const actualQty = toSafeNumber(
    actualQtyByProductFromBacklog.value.get(productIdKey) ??
    actualQtyByProductCodeFromBacklog.value.get(productCodeKey) ??
    0
  )
  if (planQty > 0 && actualQty === planQty) {
    return 'done'
  }
  if (actualQty > planQty) {
    return 'over'
  }
  return 'plan'
}

const getPlanQtyBadgeLabel = (item) => {
  const state = getPlanQtyState(item)
  const planQty = toSafeNumber(item?.plan_qty)
  const productIdKey = String(item?.product || '').trim()
  const productCodeKey = String(item?.product_code || '').trim()
  const actualQty = toSafeNumber(
    actualQtyByProductFromBacklog.value.get(productIdKey) ??
    actualQtyByProductCodeFromBacklog.value.get(productCodeKey) ??
    0
  )
  if (state === 'done') {
    return t('processInput.planQtyDone')
  }
  if (state === 'over') {
    const diff = formatNumber(Math.max(actualQty - planQty, 0))
    return t('processInput.planQtyOver', { diff })
  }
  return formatNumber(planQty)
}

const getPlanQtyParenLabel = (item) => {
  const badgeValue = getPlanQtyBadgeLabel(item)
  if (['done', 'over'].includes(getPlanQtyState(item))) {
    return `（${badgeValue}）`
  }
  return t('processInput.planQtyParen', { qty: badgeValue })
}

const buildActualQtyLookupByProductProcess = (items, processId) => {
  const result = new Map()
  const source = Array.isArray(items) ? items : []
  source.forEach((item) => {
    if (!item || item.product == null) return
    const key = `${item.product}_${processId}`
    const qty = toSafeNumber(item.actual_qty)
    const seqRaw = item.sequence_no
    const seqNo = seqRaw === null || seqRaw === undefined || seqRaw === '' ? null : Number(seqRaw)
    // 実績は sequence_no=0 行が正なので最優先。次点は数量が大きい方を採用。
    const priority = seqNo === 0 ? 2 : 1
    const current = result.get(key)
    if (!current || priority > current.priority || (priority === current.priority && qty > current.qty)) {
      result.set(key, { qty, priority })
    }
  })

  const qtyMap = new Map()
  result.forEach((value, key) => {
    qtyMap.set(key, value.qty)
  })
  return qtyMap
}

const buildActualQtyLookupByProductCode = (items) => {
  const result = new Map()
  const source = Array.isArray(items) ? items : []
  source.forEach((item) => {
    if (!item) return
    const code = String(item.product_code || '').trim()
    if (!code) return
    const qty = toSafeNumber(item.actual_qty)
    const seqRaw = item.sequence_no
    const seqNo = seqRaw === null || seqRaw === undefined || seqRaw === '' ? null : Number(seqRaw)
    // 実績は sequence_no=0 を最優先。次点は数量が大きい方を採用。
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

const planStatus = computed(() => {
  if (record.value.record_type !== 'PRODUCTION') return null
  const productId = record.value.product_id
  if (!productId) return null
  const target = productionProducts.value.find(
    (p) => String(p.product) === String(productId)
  )
  if (!target) return null

  const planQty = toSafeNumber(target.plan_qty)
  const actualQty = toSafeNumber(target.actual_qty)
  const currentInput = Math.max(toSafeNumber(record.value.qty), 0)
  const remaining = Math.max(planQty - actualQty, 0)
  const remainingAfterInput = Math.max(planQty - actualQty - currentInput, 0)

  return {
    planQty,
    actualQty,
    remaining,
    remainingAfterInput,
  }
})

const manualProductOptions = computed(() => {
  const list = Array.isArray(manualProducts.value) ? manualProducts.value : []
  const materialTypes = ['intermediate', 'purchased']
  const coproductTypes = ['coproduct_parent', 'coproduct_child']
  let filtered = [...list]
    .filter((p) => {
      if (!p || !(p.product_code || p.product_name)) return false
      if (record.value.record_type !== 'PRODUCTION') return true
      return !materialTypes.includes(p.relation_type)
    })
  if (record.value.record_type === 'SCRAP') {
    filtered = filterScrapCandidates(filtered)
  }
  return filtered.sort((a, b) => {
    const aCoproduct = coproductTypes.includes(a.relation_type)
    const bCoproduct = coproductTypes.includes(b.relation_type)
    if (aCoproduct !== bCoproduct) return aCoproduct ? -1 : 1
    return (a.product_code || '').localeCompare(b.product_code || '')
  })
})

const normalizeImageUrl = (rawUrl) => {
  if (!rawUrl) return ''
  const base = mediaBaseUrl || browserOrigin
  if (rawUrl.startsWith('/media')) {
    return `${base}${rawUrl}`
  }
  try {
    const urlObj = new URL(rawUrl, base || undefined)
    const localHosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
    if (localHosts.includes(urlObj.hostname)) {
      return `${base}${urlObj.pathname}${urlObj.search}${urlObj.hash}`
    }
    return urlObj.toString()
  } catch (e) {
    return rawUrl
  }
}

const getImageUrl = (p) => {
  const url = normalizeImageUrl(
    productImageMap.value[p.product] ||
    productImageMap.value[String(p.product)] ||
    ''
  )
  return url
}

const selectOperatorAction = (action) => {
  selectedOperatorAction.value = selectedOperatorAction.value === action ? '' : action
}

const isOperatorActionActive = (action) => {
  return String(effectiveOperatorAction.value || '').toUpperCase() === String(action || '').toUpperCase()
}

const getOperatorActionLabel = (action) => {
  const actionKey = String(action || '').toUpperCase()
  const labelKey = OPERATOR_ACTION_LABEL_KEYS[actionKey]
  return labelKey ? t(labelKey) : ''
}

const getRecentRecordTypeLabel = (rec) => {
  if (!rec) return ''
  if (rec.record_type === 'OPERATOR_ACTION') {
    const action =
      rec.event_data?.action ||
      rec.event_data?.operator_action ||
      rec.event_data?.action_type ||
      ''
    return getOperatorActionLabel(action) || t('processInput.recordType.operatorAction')
  }
  return rec.record_type_display
}

const isCoproductChildRecord = (rec) => {
  const parentRecordId = rec?.event_data?.coproduct_parent_record_id
  return parentRecordId !== null && parentRecordId !== undefined && String(parentRecordId).trim() !== ''
}

const isEndOperatorActionRecord = (rec) => {
  if (!rec || rec.record_type !== 'OPERATOR_ACTION') return false
  const action = String(
    rec?.event_data?.action ||
    rec?.event_data?.operator_action ||
    rec?.event_data?.action_type ||
    ''
  ).toUpperCase()
  return action === 'END'
}

const recentRecordsForDisplay = computed(() => {
  const items = Array.isArray(recentRecords.value) ? recentRecords.value : []
  const endActionRecordIdsLinkedFromProduction = new Set(
    items
      .filter((rec) => rec?.record_type === 'PRODUCTION')
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
  ;(Array.isArray(allPlanProducts.value) ? allPlanProducts.value : []).forEach((item) => {
    add(item?.product, item?.product_code, item?.plan_qty)
  })
  ;(Array.isArray(currentProductList.value) ? currentProductList.value : []).forEach((item) => {
    add(item?.product, item?.product_code, item?.plan_qty)
  })
  return map
})

const getOperatorActionProductId = (rec) => {
  if (!rec) return null
  return (
    rec.product ??
    rec.product_id ??
    rec.event_data?.plan_target?.product_id ??
    null
  )
}

const loadStartedProductIds = async () => {
  startedProductIdsLoaded.value = false
  latestOperatorActionByProduct.value = new Map()
  if (!selectedProcessId.value) {
    startedProductIds.value = new Set()
    latestOperatorActionByProduct.value = new Map()
    startedProductIdsLoaded.value = true
    return
  }

  try {
    const res = await api.processRealtime.list({
      process_id: selectedProcessId.value,
      record_type: 'OPERATOR_ACTION',
      limit: 2000,
      page_size: 2000,
    })
    const items = res.data.results || res.data || []
    const latestActionByProduct = new Map()

    ;(Array.isArray(items) ? items : []).forEach((rec) => {
      const pid = getOperatorActionProductId(rec)
      if (pid === null || pid === undefined || pid === '') return
      const productId = String(pid)
      if (latestActionByProduct.has(productId)) return

      const action =
        rec.event_data?.action ||
        rec.event_data?.operator_action ||
        rec.event_data?.action_type ||
        ''
      latestActionByProduct.set(productId, String(action).toUpperCase())
    })

    const started = new Set()
    latestActionByProduct.forEach((action, productId) => {
      if (activeOperatorActions.has(action)) {
        started.add(productId)
      }
    })

    startedProductIds.value = started
    latestOperatorActionByProduct.value = latestActionByProduct
    startedProductIdsLoaded.value = true
  } catch (error) {
    console.error('開始済み製品取得エラー:', error)
    startedProductIds.value = new Set()
    latestOperatorActionByProduct.value = new Map()
    startedProductIdsLoaded.value = true
  }
}

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

const hasFilledText = (value) => {
  return (value ?? '').toString().trim().length > 0
}

const hasSelectedProduct = () => {
  return !!record.value.product_id || hasFilledText(record.value.product_code)
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

  return (
    candidates.find((item) => {
      const candidateId = item?.product ?? item?.id
      return candidateId != null && String(candidateId) === productId
    }) || null
  )
}

const clearSelectedCoproductNotice = () => {
  selectedCoproductChildren.value = []
  selectedCoproductParentCode.value = ''
  selectedCoproductNoticeLoading.value = false
}

const invalidateSelectedCoproductNotice = () => {
  selectedCoproductNoticeRequestSeq += 1
  clearSelectedCoproductNotice()
}

const isStProductCode = (productCode) => {
  return String(productCode || '').trim().toUpperCase().startsWith('ST')
}

const getBomTreeCached = async (productId) => {
  if (shouldBlockBomService()) {
    console.warn('[BOM BLOCKED] getBomTreeCached', {
      lineId: selectedLineId.value,
      processId: selectedProcessId.value,
      productId,
    })
    return null
  }
  const cacheKey = String(productId || '').trim()
  if (!cacheKey) return null
  if (bomTreeCache.has(cacheKey)) {
    return bomTreeCache.get(cacheKey)
  }
  try {
    console.debug('[BOM CALL] getBomTreeCached', {
      lineId: selectedLineId.value,
      processId: selectedProcessId.value,
      productId,
    })
    const res = await api.bomService.getBomTree(productId)
    const tree = res?.data || null
    bomTreeCache.set(cacheKey, tree)
    return tree
  } catch (error) {
    console.error('連産品BOM取得エラー:', error)
    bomTreeCache.set(cacheKey, null)
    return null
  }
}

const getRelatedProductsCached = async (processId) => {
  const cacheKey = String(processId || '').trim()
  if (!cacheKey) return []
  if (relatedProductsCacheByProcess.has(cacheKey)) {
    return relatedProductsCacheByProcess.get(cacheKey) || []
  }
  try {
    const res = await api.processes.getRelatedProducts(processId)
    const rows = res?.data || []
    const list = Array.isArray(rows) ? rows : []
    relatedProductsCacheByProcess.set(cacheKey, list)
    return list
  } catch (error) {
    console.error('工程関連製品取得エラー:', error)
    relatedProductsCacheByProcess.set(cacheKey, [])
    return []
  }
}

const enrichCoproductParentsForList = async (candidates, processId) => {
  const list = Array.isArray(candidates) ? [...candidates] : []
  if (!processId || list.length === 0) return list

  const relatedProducts = await getRelatedProductsCached(processId)
  const coproductParents = relatedProducts.filter(
    (p) => normalizeRelationType(p?.relation_type) === 'coproduct_parent'
  )
  if (coproductParents.length === 0) return list

  const existingProductIds = new Set(
    list
      .map((it) => String(it?.product || '').trim())
      .filter(Boolean)
  )

  for (const parent of coproductParents) {
    const parentId = String(parent?.id || '').trim()
    if (!parentId || existingProductIds.has(parentId)) continue

    const tree = await getBomTreeCached(parent.id)
    if (!tree?.is_coproduct || !Array.isArray(tree.children) || tree.children.length === 0) continue

    const childIdSet = new Set(
      tree.children
        .map((ch) => String(ch?.product_id || '').trim())
        .filter(Boolean)
    )
    if (childIdSet.size === 0) continue

    const matchedChildren = list.filter((it) => childIdSet.has(String(it?.product || '').trim()))
    if (matchedChildren.length === 0) continue

    const base = matchedChildren[0] || {}
    const planQty = matchedChildren.reduce((maxVal, it) => {
      const qty = Number(it?.plan_qty ?? 0)
      return Number.isFinite(qty) ? Math.max(maxVal, qty) : maxVal
    }, 0)

    list.push({
      ...base,
      product: parent.id,
      product_code: parent.product_code || '',
      product_name: parent.product_name || '',
      relation_type: 'coproduct_parent',
      plan_qty: planQty,
    })
    existingProductIds.add(parentId)
  }

  return list
}

const loadSelectedCoproductNotice = async () => {
  if (record.value.record_type !== 'PRODUCTION') {
    invalidateSelectedCoproductNotice()
    return
  }

  const productId = String(record.value.product_id || '').trim()
  if (!productId) {
    invalidateSelectedCoproductNotice()
    return
  }

  const selectedProduct = findSelectedProductCandidate()
  const productCode = String(selectedProduct?.product_code || record.value.product_code || '').trim()
  if (productCode && !isStProductCode(productCode)) {
    invalidateSelectedCoproductNotice()
    return
  }

  const requestSeq = ++selectedCoproductNoticeRequestSeq
  selectedCoproductNoticeLoading.value = true

  try {
    const tree = await getBomTreeCached(productId)
    if (requestSeq !== selectedCoproductNoticeRequestSeq) return
    if (!tree?.is_coproduct || !Array.isArray(tree.children) || tree.children.length === 0) {
      clearSelectedCoproductNotice()
      return
    }

    const childMap = new Map()
    tree.children.forEach((child) => {
      if (!child?.product_id) return
      const key = String(child.product_id)
      if (childMap.has(key)) return
      childMap.set(key, {
        product_id: child.product_id,
        product_code: child.product_code || String(child.product_id),
        product_name: child.product_name || '',
      })
    })

    if (childMap.size === 0) {
      clearSelectedCoproductNotice()
      return
    }

    selectedCoproductParentCode.value = String(tree.product_code || productCode || '').trim()
    selectedCoproductChildren.value = Array.from(childMap.values())
  } finally {
    if (requestSeq === selectedCoproductNoticeRequestSeq) {
      selectedCoproductNoticeLoading.value = false
    }
  }
}

const hasEffectiveOperatorAction = () => {
  return hasFilledText(effectiveOperatorAction.value)
}

const isEndOperatorAction = computed(() => {
  return String(effectiveOperatorAction.value || '').toUpperCase() === 'END'
})

const qtyInputMin = computed(() => {
  return isEndOperatorAction.value && hasFilledText(record.value.remarks) ? 0 : 1
})

const hasRequiredProductionFields = ({ requireQty = true } = {}) => {
  if (!hasSelectedProduct()) return false
  if (requireQty) {
    const qtyValue = Number(record.value.qty)
    const hasQty =
      record.value.qty !== null &&
      record.value.qty !== '' &&
      !Number.isNaN(qtyValue)
    if (!hasQty) return false

    const allowZeroOnEndWithRemarks =
      isEndOperatorAction.value && hasFilledText(record.value.remarks)
    if (allowZeroOnEndWithRemarks) {
      if (qtyValue < 0) return false
    } else if (qtyValue <= 0) {
      return false
    }
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
    const detailText = (record.value.reason_detail || '').trim()
    if (record.value.reason === 'OTHER' && !detailText) return false
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

const resetForm = () => {
  record.value = {
    record_type: '',
    product_id: '',
    product_code: '',
    qty: null,
    operator_action_reason: '',
    operator_action_reason_detail: '',
    reason: '',
    reason_detail: '',
    disposition_status: '',
    is_production_recorded: '',
    equipment_state: '',
    batch_no: '',
    operator_name: defaultOperatorName.value || '',
    remarks: '',
  }
  manualProduct.value = false
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

const isEquipmentTroubleReason = (value) => {
  return String(value || '').trim() === PAUSE_REASON_EQUIPMENT_TROUBLE
}

const ensureProductChecksheetBeforeRealtime = async (data) => {
  const recordType = String(data.record_type || '').toUpperCase()
  const action = String(data.event_data?.action || '').toUpperCase()
  const isProductionRecord = recordType === 'PRODUCTION'
  const isOperatorEnd = recordType === 'OPERATOR_ACTION' && action === 'END'
  if (!isProductionRecord && !isOperatorEnd) return true

  const productId = data.product_id
  const qty = isOperatorEnd ? data.production_qty : data.qty
  if (!selectedLineId.value || !selectedProcessId.value || !productId || !qty) return true

  const response = await api.productChecksheets.prepareBatch({
    line: selectedLineId.value,
    process: selectedProcessId.value,
    product: productId,
    quantity: qty,
    lot_no: data.batch_no || '',
    operator_name: data.operator_name || record.value.operator_name || '',
    source_context: {
      source: 'MobileProcessInput',
      payload: data,
    },
  })
  const batch = response.data
  if (!batch.required || batch.is_complete) return true

  sessionStorage.setItem('product-checksheet:mobile-process-input', JSON.stringify({
    selectedLineId: selectedLineId.value,
    selectedProcessId: selectedProcessId.value,
    record: record.value,
  }))
  alert(`この工程作業入力は製品チェックシートが必要です。${batch.completed_count}/${batch.quantity} 枚の入力が完了しています。全数入力後に登録できます。`)
  router.push({
    path: `/quality/product-checksheet/input/${batch.id}`,
    query: { return: route.fullPath },
  })
  return false
}

const onProcessChange = () => {
  const proc = processes.value.find((p) => String(p.id) === String(selectedProcessId.value))
  if (proc?.line) {
    selectedLineId.value = String(proc.line)
  }

  productionProducts.value = []
  scrapProducts.value = []
  allPlanProducts.value = []
  allScrapProducts.value = []
  actualQtyByProductFromBacklog.value = new Map()
  actualQtyByProductCodeFromBacklog.value = new Map()
  timeSlots.value = []
  activeSlotIndex.value = null
  defaultProductId.value = null
  productImageMap.value = {}
  productMetaMap.value = {}
  invalidateSelectedCoproductNotice()
  resetForm()
  manualProducts.value = []
  manualProductsLoaded.value = false
  manualProductsProcessId.value = null
  loadPlannedProducts()
  loadStartedProductIds()
  loadRecentRecords()
}

const onLineChange = () => {
  selectedProcessId.value = ''
  recentRecords.value = []
  productionProducts.value = []
  scrapProducts.value = []
  allPlanProducts.value = []
  allScrapProducts.value = []
  timeSlots.value = []
  activeSlotIndex.value = null
  startedProductIds.value = new Set()
  startedProductIdsLoaded.value = false
  latestOperatorActionByProduct.value = new Map()
  defaultProductId.value = null
  productImageMap.value = {}
  productMetaMap.value = {}
  invalidateSelectedCoproductNotice()
  manualProducts.value = []
  manualProductsLoaded.value = false
  manualProductsProcessId.value = null
  resetForm()
}

const toggleManualProduct = () => {
  manualProduct.value = !manualProduct.value
  if (manualProduct.value) {
    record.value.product_id = ''
    record.value.product_code = ''
    loadManualProducts(selectedProcessId.value)
  } else {
    record.value.product_id = ''
    record.value.product_code = ''
  }
}

const onCurrentTimeToggle = () => {
  if (!timeSlots.value.length && filterCurrentTime.value) {
    loadPlannedProducts()
    return
  }
  if (!filterCurrentTime.value && isFloorLineSelected.value) {
    loadPlannedProducts()
    return
  }
  if (filterCurrentTime.value && activeSlotIndex.value === null && timeSlots.value.length) {
    activeSlotIndex.value = 0
  }
  applyTimeSlotFilter()
}

const submitRecord = async () => {
  if (!canSubmit.value) return
  if (!window.confirm(t('processInput.alert.confirmSubmit'))) return

  submitting.value = true
  let submittedOperatorAction = ''
  let submittedOperatorProductId = ''
  let moveToEquipmentState = false
  try {
    const data = {
      process_id: selectedProcessId.value,
      record_type: record.value.record_type,
    }

    if (isOperatorActionMode.value) {
      const selectedPlanTarget = findSelectedPlanTarget()
      if (!selectedPlanTarget?.product) {
        return
      }
      data.record_type = 'OPERATOR_ACTION'
      data.qty = 0
      data.product_id = selectedPlanTarget.product
      const operatorName = (record.value.operator_name || defaultOperatorName.value || '').trim()
      if (operatorName) {
        data.operator_name = operatorName
      }
      const activeSlot =
        filterCurrentTime.value && timeSlots.value.length
          ? timeSlots.value[activeSlotIndex.value ?? 0]
          : null
      const targetStartIso =
        toIsoDateTimeOrNull(selectedPlanTarget.start) || toIsoDateTimeOrNull(activeSlot?.start)
      const targetEndIso =
        toIsoDateTimeOrNull(selectedPlanTarget.end) || toIsoDateTimeOrNull(activeSlot?.end)

      data.event_data = {
        action: effectiveOperatorAction.value,
        plan_target: {
          line_id: selectedLineId.value || null,
          process_id: selectedProcessId.value || null,
          plan_date: selectedPlanTarget.plan_date || currentDateYmd.value || null,
          product_id: selectedPlanTarget.product || null,
          product_code: selectedPlanTarget.product_code || '',
          product_name: selectedPlanTarget.product_name || '',
          plan_qty: selectedPlanTarget.plan_qty ?? null,
          actual_qty: selectedPlanTarget.actual_qty ?? null,
          slot_start: targetStartIso,
          slot_end: targetEndIso,
          slot_label: slotLabel.value || null,
        },
      }
      submittedOperatorAction = String(effectiveOperatorAction.value || '').toUpperCase()
      submittedOperatorProductId = String(selectedPlanTarget.product || '')
      if (submittedOperatorAction === 'PAUSE') {
        data.qty = record.value.qty
        data.batch_no = record.value.batch_no
        data.event_data.pause_qty = record.value.qty
      }
      if (submittedOperatorAction === 'END') {
        data.production_qty = record.value.qty
        data.batch_no = record.value.batch_no
      }
      if (requiresOperatorActionReason.value) {
        let reasonText = (record.value.operator_action_reason || '').trim()
        if (submittedOperatorAction === 'TEMP_END' && isTempEndReasonOtherSelected.value) {
          reasonText = (record.value.remarks || '').trim()
        }
        data.event_data.operator_action_reason = reasonText
        if (submittedOperatorAction === 'PAUSE') {
          data.event_data.pause_reason = reasonText
          moveToEquipmentState = isEquipmentTroubleReason(reasonText)
        } else if (submittedOperatorAction === 'TEMP_END') {
          data.event_data.temp_end_reason = reasonText
        }
      }
    } else {
      if (record.value.product_id) {
        data.product_id = record.value.product_id
      } else if ((record.value.product_code || '').trim()) {
        data.product_code = record.value.product_code.trim()
      }

      if (record.value.record_type === 'PRODUCTION' || record.value.record_type === 'SCRAP') {
        data.qty = record.value.qty
        data.batch_no = record.value.batch_no
        data.operator_name = record.value.operator_name
      } else if (record.value.record_type === 'EQUIPMENT_STATE') {
        data.equipment_state = record.value.equipment_state
        data.qty = 0
      }

      if (record.value.record_type === 'SCRAP' && record.value.reason) {
        const currentProduct =
          scrapProducts.value.find((p) => String(p.product) === String(record.value.product_id)) ||
          manualProducts.value.find((p) => String(p.id) === String(record.value.product_id))
        const eventData = {
          reason: record.value.reason,
          disposition_status: record.value.disposition_status || 'REJECTED',
          is_production_recorded: record.value.is_production_recorded || false,
          relation_type: currentProduct?.relation_type || '',
        }
        if (record.value.reason === 'OTHER' && (record.value.reason_detail || '').trim()) {
          eventData.reason_detail = record.value.reason_detail.trim()
        }
        data.event_data = eventData
      }
    }

    data.remarks = record.value.remarks

    const checksheetReady = await ensureProductChecksheetBeforeRealtime(data)
    if (!checksheetReady) return

    const res = await api.processRealtime.create(data)
    if (submittedOperatorProductId) {
      const nextStarted = new Set(startedProductIds.value)
      const nextLatestOperatorAction = new Map(latestOperatorActionByProduct.value)
      if (submittedOperatorAction) {
        nextLatestOperatorAction.set(submittedOperatorProductId, submittedOperatorAction)
      }
      if (submittedOperatorAction === 'END' || submittedOperatorAction === 'TEMP_END' || submittedOperatorAction === 'CANCEL') {
        nextStarted.delete(submittedOperatorProductId)
      } else if (activeOperatorActions.has(submittedOperatorAction)) {
        nextStarted.add(submittedOperatorProductId)
      }
      startedProductIds.value = nextStarted
      latestOperatorActionByProduct.value = nextLatestOperatorAction
      startedProductIdsLoaded.value = true
    }

    // 計画超過チェック警告
    const overrun = res.data?.plan_overrun_warning
    if (overrun) {
      alert(
        `⚠ 計画超過\n` +
        `${overrun.process_name} / ${overrun.product_code} ${overrun.product_name}\n` +
        `計画: ${overrun.plan_qty} → 実績: ${overrun.actual_qty} （${overrun.over_qty} 超過）\n` +
        `数量を確認してください。`
      )
    } else {
      alert(t('processInput.alert.saved'))
    }
    if (moveToEquipmentState) {
      prepareEquipmentStateForm()
    } else {
      resetForm()
    }
    await loadPlannedProducts()
    await loadStartedProductIds()
    await loadRecentRecords()
  } catch (error) {
    console.error('記録登録エラー:', error)
    alert(t('processInput.alert.saveFailed'))
  } finally {
    submitting.value = false
  }
}

const loadRecentRecords = async () => {
  if (!selectedProcessId.value) return

  try {
    const res = await api.processRealtime.list({
      process_id: selectedProcessId.value,
      limit: 10,
    })
    recentRecords.value = res.data.results || res.data || []

    const lastProduction = recentRecords.value.find(r => r.record_type === 'PRODUCTION' && r.product)
    defaultProductId.value = lastProduction ? lastProduction.product : defaultProductId.value

    await loadGanttPlanQty()
  } catch (error) {
    console.error('最近の記録取得エラー:', error)
  }
}

const loadGanttPlanQty = async () => {
  if (!selectedLineId.value || !selectedProcessId.value) {
    ganttPlanQtyMap.value = {}
    return
  }
  const records = Array.isArray(recentRecords.value) ? recentRecords.value : []
  const dateSet = new Set()
  for (const rec of records) {
    const ts = rec?.timestamp
    if (ts) dateSet.add(formatISODate(getBusinessDate(new Date(ts))))
  }
  if (!dateSet.size) {
    ganttPlanQtyMap.value = {}
    return
  }
  try {
    const res = await api.processRealtime.getGanttPlanQty({
      line_id: selectedLineId.value,
      process_id: selectedProcessId.value,
      dates: [...dateSet].join(','),
    })
    ganttPlanQtyMap.value = res.data || {}
  } catch {
    ganttPlanQtyMap.value = {}
  }
}


const buildCurrentTimePlanItems = async (lineId, processId, existingItems = []) => {
  try {
    const targetDate = currentDateYmd.value
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: lineId,
      plan_date__gte: targetDate,
      plan_date__lte: targetDate,
      page_size: 1000,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!Array.isArray(rawPlans) || !rawPlans.length) {
      return { items: [], hasPlan: false }
    }

    const actualLookup = buildActualQtyLookupByProductProcess(existingItems, processId)

    const now = new Date()
    const map = new Map()
    rawPlans.forEach((plan) => {
      const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
      processes.forEach((pp) => {
        if (String(pp.process_id) != String(processId)) return
        const start = new Date(pp.start_time)
        const end = new Date(pp.end_time)
        if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return
        if (now < start || now > end) return

        const productId = pp.output_product_id ?? plan.product
        if (!productId) return
        const key = `${productId}_${processId}`
        if (map.has(key)) return
        const actualQty = actualLookup.has(key) ? actualLookup.get(key) : 0
        map.set(key, {
          plan_date: targetDate,
          product: productId,
          product_code: pp.output_product_code || plan.product_code || '',
          product_name: pp.output_product_name || plan.product_name || '',
          process: processId,
          plan_qty: pp.quantity ?? plan.plan_qty ?? 0,
          actual_qty: actualQty,
          sequence_no: plan.sequence_no ?? null,
        })
      })
    })
    return { items: Array.from(map.values()), hasPlan: true }
  } catch (e) {
    console.error('現在時間の計画取得エラー:', e)
    return { items: [], hasPlan: false }
  }
}

const buildPlanTimeSlots = async (lineId, processId, existingItems = []) => {
  try {
    const targetDate = currentDateYmd.value
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: lineId,
      plan_date__gte: targetDate,
      plan_date__lte: targetDate,
      page_size: 1000,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!Array.isArray(rawPlans) || !rawPlans.length) {
      return { slots: [], activeIndex: null }
    }

    const actualLookup = buildActualQtyLookupByProductProcess(existingItems, processId)

    const slotMap = new Map()
    rawPlans.forEach((plan) => {
      const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
      processes.forEach((pp) => {
        if (String(pp.process_id) != String(processId)) return
        const start = new Date(pp.start_time)
        const end = new Date(pp.end_time)
        if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return

        const productId = pp.output_product_id ?? plan.product
        if (!productId) return
        const key = `${productId}_${processId}`
        const actualQty = actualLookup.has(key) ? actualLookup.get(key) : 0
        const item = {
          plan_date: targetDate,
          product: productId,
          product_code: pp.output_product_code || plan.product_code || '',
          product_name: pp.output_product_name || plan.product_name || '',
          process: processId,
          plan_qty: pp.quantity ?? plan.plan_qty ?? 0,
          actual_qty: actualQty,
          start,
          end,
          sequence_no: plan.sequence_no ?? null,
        }

        const slotKey = `${start.toISOString()}_${end.toISOString()}`
        if (!slotMap.has(slotKey)) {
          slotMap.set(slotKey, { start, end, items: [] })
        }
        slotMap.get(slotKey).items.push(item)
      })
    })

    const slots = Array.from(slotMap.values()).sort((a, b) => a.start - b.start)
    const now = new Date()
    let activeIndex = null
    slots.forEach((slot, idx) => {
      if (now >= slot.start && now <= slot.end && activeIndex === null) {
        activeIndex = idx
      }
    })
    if (activeIndex === null && slots.length > 0) {
      activeIndex = 0
    }

    return { slots, activeIndex }
  } catch (e) {
    console.error('時間帯スロット構築エラー:', e)
    return { slots: [], activeIndex: null }
  }
}

const formatSlotTime = (dt) => {
  if (!(dt instanceof Date)) return ''
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

const toIsoDateTimeOrNull = (value) => {
  if (!value) return null
  const dt = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(dt.getTime())) return null
  return dt.toISOString()
}

const ensureStartedProductsVisible = (items) => {
  const base = [...(Array.isArray(items) ? items : [])]
  if (!startedProductIdsLoaded.value || !startedProductIds.value?.size) {
    return base
  }

  const existingIds = new Set(
    base
      .map((item) => String(item?.product || ''))
      .filter((id) => id !== '')
  )
  const allMerged = mergeProductionProductsByProduct(allPlanProducts.value)
  const allMap = new Map(
    allMerged
      .map((item) => [String(item?.product || ''), item])
      .filter(([id]) => id !== '')
  )

  startedProductIds.value.forEach((productId) => {
    const key = String(productId || '')
    if (!key || existingIds.has(key)) return
    const src = allMap.get(key)
    if (!src) return
    base.push({ ...src })
    existingIds.add(key)
  })

  return base
}

const filterFloorProductsByDisplayMap = async (lineId, processId, items, forceFloorMode = false) => {
  if (filterCurrentTime.value) return Array.isArray(items) ? items : []
  if (!forceFloorMode && !isFloorLineSelected.value) return Array.isArray(items) ? items : []
  if (!lineId || !processId) return Array.isArray(items) ? items : []
  try {
    const res = await api.ganttDisplayProductMaps.getGanttDisplayProductMaps({
      line: lineId,
      process: processId,
      page_size: 500,
    })
    const rows = res.data?.results || res.data || []
    const allowedProductIds = new Set(
      (Array.isArray(rows) ? rows : [])
        .map((row) => String(row?.display_product || '').trim())
        .filter(Boolean)
    )
    if (!allowedProductIds.size) return []
    return (Array.isArray(items) ? items : []).filter((item) =>
      allowedProductIds.has(String(item?.product || '').trim())
    )
  } catch (e) {
    console.error('ガント表示品マップ取得エラー:', e)
    return Array.isArray(items) ? items : []
  }
}

const mergeMissingFloorMapProducts = async (lineId, processId, items) => {
  if (filterCurrentTime.value) return Array.isArray(items) ? items : []
  if (!lineId || !processId) return Array.isArray(items) ? items : []
  try {
    const res = await api.ganttDisplayProductMaps.getGanttDisplayProductMaps({
      line: lineId,
      process: processId,
      page_size: 500,
    })
    const rows = Array.isArray(res.data?.results || res.data) ? (res.data?.results || res.data) : []
    const base = Array.isArray(items) ? [...items] : []
    const exists = new Set(base.map((it) => String(it?.product || '').trim()).filter(Boolean))
    rows.forEach((row) => {
      const productId = String(row?.display_product || '').trim()
      if (!productId || exists.has(productId)) return
      base.push({
        plan_date: currentDateYmd.value,
        product: row.display_product,
        product_code: row.display_product_code || '',
        product_name: row.display_product_name || '',
        process: processId,
        plan_qty: 0,
        actual_qty: 0,
      })
      exists.add(productId)
    })
    return base
  } catch (e) {
    console.error('表示品マップ補完エラー:', e)
    return Array.isArray(items) ? items : []
  }
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
  const totalActualMap = buildTotalActualByProduct(allPlanProducts.value)
  const slotItems = applySlotActualProgress(mergedSlotItems, planBeforeMap, totalActualMap)
  productionProducts.value = [...slotItems]

  const slotProductIds = new Set(slotItems.map((p) => String(p.product)))
  let filteredScrap = allScrapProducts.value.filter((p) =>
    slotProductIds.has(String(p.product))
  )
  if (!filteredScrap.length) {
    filteredScrap = [...allScrapProducts.value]
  }
  scrapProducts.value = filteredScrap
}

const canPrevSlot = computed(() => {
  return filterCurrentTime.value && timeSlots.value.length > 0 && (activeSlotIndex.value ?? 0) > 0
})

const canNextSlot = computed(() => {
  return (
    filterCurrentTime.value &&
    timeSlots.value.length > 0 &&
    (activeSlotIndex.value ?? 0) < timeSlots.value.length - 1
  )
})

const slotLabel = computed(() => {
  if (!timeSlots.value.length) return ''
  if (filterCurrentTime.value) {
    const idx = activeSlotIndex.value ?? 0
    const slot = timeSlots.value[idx]
    if (!slot) return ''
    return `${formatSlotTime(slot.start)} - ${formatSlotTime(slot.end)}`
  }
  // 「現在時刻のみ」OFF時は当日計画の全体時間帯を表示
  const first = timeSlots.value[0]
  const last = timeSlots.value[timeSlots.value.length - 1]
  if (!first || !last) return ''
  return `${formatSlotTime(first.start)} - ${formatSlotTime(last.end)}`
})

const selectedProductTimeLabel = computed(() => {
  if (!timeSlots.value.length) return ''
  const productId = String(record.value.product_id || '').trim()
  if (!productId) return ''

  let startTime = null
  let endTime = null
  ;(timeSlots.value || []).forEach((slot) => {
    const slotItems = Array.isArray(slot?.items) ? slot.items : []
    const hasSelectedProduct = slotItems.some(
      (item) => String(item?.product || '').trim() === productId
    )
    if (!hasSelectedProduct) return

    const slotStart = slot?.start instanceof Date ? slot.start : new Date(slot?.start)
    const slotEnd = slot?.end instanceof Date ? slot.end : new Date(slot?.end)
    if (Number.isNaN(slotStart.getTime()) || Number.isNaN(slotEnd.getTime())) return
    if (!startTime || slotStart.getTime() < startTime.getTime()) {
      startTime = slotStart
    }
    if (!endTime || slotEnd.getTime() > endTime.getTime()) {
      endTime = slotEnd
    }
  })

  if (!startTime || !endTime) return ''
  return `${formatSlotTime(startTime)} - ${formatSlotTime(endTime)}`
})

const plannedTimeLabel = computed(() => {
  return selectedProductTimeLabel.value || slotLabel.value
})

const goPrevSlot = () => {
  if (!canPrevSlot.value) return
  activeSlotIndex.value = Math.max(0, (activeSlotIndex.value ?? 0) - 1)
  applyTimeSlotFilter()
}

const goNextSlot = () => {
  if (!canNextSlot.value) return
  activeSlotIndex.value = Math.min(timeSlots.value.length - 1, (activeSlotIndex.value ?? 0) + 1)
  applyTimeSlotFilter()
}

const fetchProcessPlanProductsFromBacklogs = async (lineId, processId) => {
  const listRes = await api.lineBacklogs.getLineBacklogs({
    line: lineId,
    process: processId,
    plan_date: currentDateYmd.value,
    page_size: 1000,
  })
  const listItems = listRes.data.results || listRes.data || []
  if (Array.isArray(listItems) && listItems.length > 0) {
    return listItems
  }

  try {
    const pickupRes = await api.lineBacklogs.pickup({
      line_id: lineId,
      start_date: currentDateYmd.value,
      end_date: currentDateYmd.value,
    })
    const pickupItems = pickupRes.data.results || pickupRes.data || []
    return (Array.isArray(pickupItems) ? pickupItems : []).filter(
      (it) => String(it.process) === String(processId) && String(it.plan_date) === String(currentDateYmd.value)
    )
  } catch (e) {
    console.error('本日の計画ピックアップエラー:', e)
    return []
  }
}

const loadPlannedProducts = async () => {
  if (!selectedProcessId.value) return
  const requestSeq = ++plannedProductsRequestSeq
  isPlannedProductsLoading.value = true
  invalidateSelectedCoproductNotice()

  productionProducts.value = []
  scrapProducts.value = []
  allPlanProducts.value = []
  allScrapProducts.value = []
  timeSlots.value = []
  activeSlotIndex.value = null
  try {
    const process = processes.value.find(p => String(p.id) === String(selectedProcessId.value))
    const lineId = process?.line
    if (!lineId) return
    const processId = selectedProcessId.value
    // 現在時刻のみON時は、まず LINE_GANTT_PLANS を使って即時表示する
    if (filterCurrentTime.value) {
      const [currentSlotItemsResult, fastSlotResult] = await Promise.all([
        buildCurrentTimePlanItems(lineId, processId, []),
        buildPlanTimeSlots(lineId, processId, []),
      ])
      if (requestSeq !== plannedProductsRequestSeq) return

      allPlanProducts.value = mergeProductionProductsByProduct(currentSlotItemsResult.items || [])
      timeSlots.value = fastSlotResult.slots
      activeSlotIndex.value = fastSlotResult.activeIndex
      applyTimeSlotFilter()
    }

    let tempProducts = await fetchProcessPlanProductsFromBacklogs(lineId, processId)
    const lineObj = lines.value.find((line) => String(line.id) === String(lineId)) || null
    const lineCode = String(lineObj?.line_code || '').trim().toUpperCase()
    const floorMapOnlyMode = !filterCurrentTime.value && lineCode === FLOOR_LINE_CODE
    tempProducts = await filterFloorProductsByDisplayMap(lineId, processId, tempProducts, floorMapOnlyMode)

    // 時間帯スロットを構築し、デフォルトで現在時刻スロットを選択
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
        const seqKey = seq !== null ? seq : 'none'
        const startMs = item?.start instanceof Date ? item.start.getTime() : Number.POSITIVE_INFINITY
        const prev = seqMap.get(seqKey)
        if (!prev) { seqMap.set(seqKey, { qty: toSafeNumber(item?.plan_qty), startMs }) }
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
      return {
        ...it,
        actual_qty: actualLookup.has(key)
          ? toSafeNumber(actualLookup.get(key))
          : toSafeNumber(it?.actual_qty),
      }
    })

    let mapFilteredForProduction = []
    if (floorMapOnlyMode) {
      // フロアライン + 「現在時刻のみ」OFF時は、表示品マップにある製品のみをそのまま表示対象にする
      mapFilteredForProduction = await mergeMissingFloorMapProducts(lineId, processId, tempProducts)
      if (requestSeq !== plannedProductsRequestSeq) return
    } else {
      // 連産親を補完し、連産品の子品番を除外（生産記録用）
      const productsWithParents = await enrichCoproductParentsForList(tempProducts, processId)
      if (requestSeq !== plannedProductsRequestSeq) return
      const filteredForProduction = await filterCoproductChildrenFromList(productsWithParents)
      if (requestSeq !== plannedProductsRequestSeq) return
      mapFilteredForProduction = await filterFloorProductsByDisplayMap(
        lineId,
        processId,
        filteredForProduction,
        floorMapOnlyMode
      )
      if (requestSeq !== plannedProductsRequestSeq) return
    }

    // 計画数は t_line_gantt_plan（時間帯スロット）由来で最終確定する
    const expanded = []
    mapFilteredForProduction.forEach((item) => {
      const pid = String(item?.product || '')
      const entries = ganttEntriesByProduct.get(pid)
      if (!entries || entries.size === 0) {
        expanded.push({ ...item, plan_qty: 0 })
        return
      }
      entries.forEach((entry, seqKey) => {
        expanded.push({ ...item, plan_qty: toSafeNumber(entry.qty), sequence_no: seqKey === 'none' ? null : seqKey, gantt_start_ms: Number.isFinite(entry.startMs) ? entry.startMs : null })
      })
    })
    mapFilteredForProduction = expanded

    const dedupMap = new Map()
    mapFilteredForProduction.forEach((item) => {
      const key = productSeqKey(item)
      if (key && !dedupMap.has(key)) dedupMap.set(key, item)
    })
    mapFilteredForProduction = Array.from(dedupMap.values())

    // 生産記録用リスト（全時間帯）を保持
    allPlanProducts.value = [...mapFilteredForProduction]

    // 生産記録の体感速度を優先し、まず生産リストを先に反映
    applyTimeSlotFilter()

    if (productionProducts.value.length === 1 && productionProducts.value[0].product) {
      defaultProductId.value = productionProducts.value[0].product
    }

    if (!productionProducts.value.length) {
      loadManualProducts(processId)
    }

    // 仕損品記録用リストは後続で構築（PRODUCTIONでは待たない）
    // フロアライン + 「現在時刻のみ」OFF で生産記録表示中は、重い仕損候補展開（BOM多段取得）を実行しない
    const skipScrapBackgroundLoad = floorMapOnlyMode && record.value.record_type !== 'SCRAP'
    if (skipScrapBackgroundLoad) {
      allScrapProducts.value = []
      scrapProducts.value = []
    } else {
      const scrapLoadTask = (async () => {
        await loadScrapProducts(processId, mapFilteredForProduction, lineId, {
          skipBomExpansion: floorMapOnlyMode,
        })
        if (requestSeq !== plannedProductsRequestSeq) return
        allScrapProducts.value = [...scrapProducts.value]
        if (record.value.record_type === 'SCRAP') {
          applyTimeSlotFilter()
          if (!productionProducts.value.length && !scrapProducts.value.length) {
            loadManualProducts(processId)
          }
        }
      })()

      if (record.value.record_type === 'SCRAP') {
        await scrapLoadTask
      } else {
        scrapLoadTask.catch((err) => {
          console.error('仕損品記録用製品リスト取得エラー:', err)
        })
      }
    }
  } catch (error) {
    console.error('本日の計画取得エラー:', error)
  } finally {
    if (requestSeq === plannedProductsRequestSeq) {
      isPlannedProductsLoading.value = false
    }
  }
}

const loadScrapProducts = async (processId, baseProducts, fallbackLineId = null, options = {}) => {
  try {
    const skipBomExpansion = Boolean(options?.skipBomExpansion)
    const forceBlockBom = shouldBlockBomService(fallbackLineId, processId)
    // 基本リスト（生産記録と同じ）から開始
    const scrapMap = new Map()
    baseProducts.forEach((it) => {
      const key = `${it.product}_${it.process}`
      if (!scrapMap.has(key)) {
        scrapMap.set(key, {
          ...it,
          origin_process_id: it.process ?? processId,
          origin_line_id: it.line ?? fallbackLineId,
          sourcing_type: it.sourcing_type || it.sourcingType || '',
        })
      }
    })

    // 工程計画が無い場合はラインの当日計画を候補に加える
    if (!scrapMap.size && fallbackLineId) {
      try {
        const lineRes = await api.lineBacklogs.getLineBacklogs({
          line: fallbackLineId,
          plan_date: currentDateYmd.value,
        })
        const lineItems = lineRes.data.results || lineRes.data || []
        ;(Array.isArray(lineItems) ? lineItems : []).forEach((it) => {
          if (!it || !it.product) return
          const normalized = {
            ...it,
            process: processId,
            origin_process_id: it.process ?? processId,
            origin_line_id: it.line ?? fallbackLineId,
            sourcing_type: it.sourcing_type || it.sourcingType || '',
          }
          const key = `${normalized.product}_${normalized.process}`
          if (!scrapMap.has(key)) scrapMap.set(key, normalized)
        })
      } catch (e) {
        console.error('仕損品記録用ライン計画取得エラー:', e)
      }
    }

    // related-products APIから工程関連製品を取得して追加
    const relatedRes = await api.processes.getRelatedProducts(processId)
    const relatedProducts = relatedRes.data || []
    console.debug('ScrapRecord relatedProducts', {
      processId,
      count: Array.isArray(relatedProducts) ? relatedProducts.length : 0,
    })
    console.table(
      (relatedProducts || []).map((p) => ({
        product: p.product_code || p.id,
        relation_type: p.relation_type,
        normalized: normalizeRelationType(p.relation_type),
      }))
    )

    // related-products から relation_type と BOM由来の工程ID を保持
    const relatedInfoMap = new Map()
    relatedProducts.forEach((prod) => {
      relatedInfoMap.set(String(prod.id), {
        relation_type: prod.relation_type,
        process_id: prod.process_id,
        sourcing_type: prod.sourcing_type || '',
      })
      const key = `${prod.id}_${processId}`
      if (!scrapMap.has(key)) {
        // line-backlog形式に変換して追加
        scrapMap.set(key, {
          product: prod.id,
          product_code: prod.product_code,
          product_name: prod.product_name,
          process: processId,
          origin_process_id: prod.process_id || processId,
          origin_line_id: prod.line_id || fallbackLineId,
          sourcing_type: prod.sourcing_type || '',
          plan_qty: 0,
          plan_date: null,
          relation_type: prod.relation_type,
        })
      }
    })

    // line-backlog由来のアイテムを related-products の情報で補完
    // (relation_type + BOM由来の正しい origin_process_id)
    scrapMap.forEach((item) => {
      if (!item || item.product == null) return
      const info = relatedInfoMap.get(String(item.product))
      if (!info) return
      if (!item.relation_type && info.relation_type) {
        item.relation_type = info.relation_type
      }
      if (!item.sourcing_type && info.sourcing_type) {
        item.sourcing_type = info.sourcing_type
      }
      // BOM由来の工程IDで上書き（line-backlogは使用工程を返すため不正確）
      // APIの値を優先: process_id があればそれを、なければnullに（line-backlog値を除去）
      item.origin_process_id = info.process_id || null
    })

    if (skipBomExpansion || forceBlockBom) {
      if (forceBlockBom) {
        console.warn('[BOM BLOCKED] loadScrapProducts', {
          lineId: fallbackLineId,
          processId,
        })
      }
      scrapProducts.value = Array.from(scrapMap.values())
      const idSet = new Set([
        ...productionProducts.value.map((p) => p.product).filter(Boolean),
        ...scrapProducts.value.map((p) => p.product).filter(Boolean),
      ])
      await loadProductImages(idSet)
      return
    }

    // 最終工程向け: output_product の直子部品をBOM階層1から補完（子はカテゴリで purchased / intermediate 判定）
    const bomCache = new Map()
    const addBomChildren = async (parentProductId) => {
      if (!parentProductId) return
      const cacheKey = String(parentProductId)
      if (!bomCache.has(cacheKey)) {
        try {
          console.debug('[BOM CALL] output_product children', {
            lineId: fallbackLineId,
            processId,
            parentProductId,
          })
          const treeRes = await api.bomService.getBomTree(parentProductId)
          bomCache.set(cacheKey, treeRes.data || null)
        } catch (err) {
          console.error('BOMツリー取得エラー (output_product children):', parentProductId, err)
          bomCache.set(cacheKey, null)
        }
      }
      const tree = bomCache.get(cacheKey)
      if (!tree || !Array.isArray(tree.children)) return
      console.debug('BOM直子', {
        parentProductId,
        parentCode: tree.product_code,
        children: tree.children.map((ch) => ({
          product_id: ch.product_id,
          product_code: ch.product_code,
          category: ch.category,
          sourcing_type: ch.sourcing_type,
        })),
      })
      let added = 0
      tree.children.forEach((ch) => {
        if (!ch?.product_id) return
        const childKey = `${ch.product_id}_${processId}`
        const childRelation =
          ch.category === 'PURCHASED' || ch.category === 'MATERIAL' ? 'purchased' : 'intermediate'
        const childOriginProcess = ch.process_id || ch.processId || null
        const childOriginLine = ch.line_id || ch.lineId || fallbackLineId
        if (scrapMap.has(childKey)) {
          const existing = scrapMap.get(childKey) || {}
          const merged = {
            ...existing,
          }
          if (!merged.relation_type) merged.relation_type = childRelation
          if (!merged.origin_process_id && childOriginProcess) merged.origin_process_id = childOriginProcess
          if (!merged.origin_line_id && childOriginLine) merged.origin_line_id = childOriginLine
          if (!merged.sourcing_type && ch.sourcing_type) merged.sourcing_type = ch.sourcing_type
          scrapMap.set(childKey, merged)
          return
        }
        scrapMap.set(childKey, {
          product: ch.product_id,
          product_code: ch.product_code || ch.product_id,
          product_name: ch.product_name || '',
          process: processId,
          origin_process_id: childOriginProcess || processId,
          origin_line_id: childOriginLine,
          sourcing_type: ch.sourcing_type || '',
          plan_qty: 0,
          plan_date: null,
          relation_type: childRelation,
        })
        added += 1
      })
      console.debug('BOM子部品補完', {
        parentProductId,
        parentCode: tree.product_code,
        childrenCount: tree.children.length,
        added,
      })
    }

    const outputProducts = Array.from(scrapMap.values()).filter(
      (it) => normalizeRelationType(it.relation_type) === 'output_product'
    )
    console.debug('BOM直子対象 output_products', outputProducts.map((p) => ({
      product: p.product,
      code: p.product_code,
      relation_type: p.relation_type,
    })))
    for (const op of outputProducts) {
      await addBomChildren(op.product)
    }

    // 連産親がある場合は、BOMツリーから子品番を取得して連産子として補完
    const coproductParentIds = (relatedProducts || [])
      .filter((p) => normalizeRelationType(p.relation_type) === 'coproduct_parent')
      .map((p) => p.id)
    for (const parentId of coproductParentIds) {
      try {
        console.debug('[BOM CALL] coproduct children', {
          lineId: fallbackLineId,
          processId,
          parentId,
        })
        const treeRes = await api.bomService.getBomTree(parentId)
        const tree = treeRes.data
        if (!tree || !Array.isArray(tree.children)) continue
        tree.children.forEach((ch) => {
          if (!ch?.product_id) return
          const key = `${ch.product_id}_${processId}`
          const existing = scrapMap.get(key)
          if (existing) {
            // 既存エントリも連産子として扱えるよう relation_type を上書き
            existing.relation_type = 'coproduct_child'
            scrapMap.set(key, existing)
            return
          }
          scrapMap.set(key, {
            product: ch.product_id,
            product_code: ch.product_code || ch.product_id,
            product_name: ch.product_name || '',
            process: processId,
            plan_qty: 0,
            plan_date: null,
            relation_type: 'coproduct_child',
          })
        })
      } catch (err) {
        console.error('連産品BOM子取得エラー:', parentId, err)
      }
    }

    scrapMap.forEach((item) => {
      if (!item || item.product == null) return
      const info = relatedInfoMap.get(String(item.product))
      if (!info) return
      if (!item.relation_type && info.relation_type) {
        item.relation_type = info.relation_type
      }
      if (info.process_id) {
        item.origin_process_id = info.process_id
      }
    })

    scrapProducts.value = Array.from(scrapMap.values())
    const relationSummary = {}
    scrapProducts.value.forEach((p) => {
      const key = normalizeRelationType(p.relation_type) || '(empty)'
      relationSummary[key] = (relationSummary[key] || 0) + 1
    })
    console.debug('ScrapRecord scrapProducts (normalized)', {
      processId,
      count: scrapProducts.value.length,
      relationSummary,
    })
    console.table(
      scrapProducts.value.map((p) => ({
        product: p.product_code || p.product,
        relation_type: p.relation_type,
        origin_process_id: p.origin_process_id,
        sourcing_type: p.sourcing_type,
        category: getScrapCategory(p),
      }))
    )

    // 画像マップを構築
    const idSet = new Set([
      ...productionProducts.value.map((p) => p.product).filter(Boolean),
      ...scrapProducts.value.map((p) => p.product).filter(Boolean),
    ])
    await loadProductImages(idSet)
  } catch (error) {
    console.error('仕損品記録用製品リスト取得エラー:', error)
    // エラー時は基本リストのみを使用
    scrapProducts.value = [...baseProducts]
  }
}

const filterCoproductChildrenFromList = async (candidates) => {
  const parentSetItems = candidates.filter(
    (it) => it.product && typeof it.product_code === 'string' && it.product_code.startsWith('STYD')
  )
  if (parentSetItems.length === 0) return candidates

  const parentIds = [...new Set(parentSetItems.map((it) => it.product))]
  const childIds = new Set()

  for (const parentId of parentIds) {
    try {
      const tree = await getBomTreeCached(parentId)
      if (!tree || !tree.is_coproduct) continue
      for (const ch of tree.children || []) {
        if (ch?.product_id) childIds.add(ch.product_id)
      }
    } catch (error) {
      console.error('連産品候補除外エラー:', error)
    }
  }

  if (childIds.size === 0) return candidates
  return candidates.filter((it) => !childIds.has(it.product))
}

const loadProductImages = async (idSet) => {
  try {
    if (!idSet || idSet.size === 0) {
      productImageMap.value = {}
      productMetaMap.value = {}
      return
    }
    // 1) まとめて取得
    const all = await api.products.getAllProducts({ page_size: 5000 })
    const map = {}
    const meta = {}
    all.forEach((p) => {
      const pidNum = p.id
      const pidStr = String(p.id)
      if (idSet.has(pidNum) || idSet.has(pidStr)) {
        const val = p.image_url || ''
        map[pidNum] = val
        map[pidStr] = val
        const metaEntry = {
          is_final_product: !!p.is_final_product,
          is_line_final_product: !!p.is_line_final_product,
          category: p.category || '',
        }
        meta[pidNum] = metaEntry
        meta[pidStr] = metaEntry
      }
    })

    // 2) 取りこぼしがあれば個別に取得（ページング漏れ対策）
    const missingIds = [...idSet].filter((id) => !(String(id) in map))
    if (missingIds.length) {
      for (const mid of missingIds) {
        try {
          const res = await api.products.getProduct(mid)
          const p = res.data || res
          if (p) {
            const pidNum = p.id
            const pidStr = String(p.id)
            const val = p.image_url || ''
            map[pidNum] = val
            map[pidStr] = val
            const metaEntry = {
              is_final_product: !!p.is_final_product,
              is_line_final_product: !!p.is_line_final_product,
              category: p.category || '',
            }
            meta[pidNum] = metaEntry
            meta[pidStr] = metaEntry
          }
        } catch (err) {
          console.warn('製品詳細取得失敗 (画像用):', mid, err)
        }
      }
    }

    productImageMap.value = map
    productMetaMap.value = meta
  } catch (error) {
    console.error('製品画像取得エラー:', error)
  }
}

const loadManualProducts = async (processId) => {
  if (!processId) return
  if (
    manualProductsLoading.value ||
    (manualProductsLoaded.value && String(manualProductsProcessId.value) === String(processId))
  ) {
    return
  }
  manualProductsLoading.value = true
  try {
    const res = await api.processes.getRelatedProducts(processId)
    const items = res?.data || res || []
    manualProducts.value = Array.isArray(items) ? items : []
    manualProductsProcessId.value = processId
    manualProductsLoaded.value = true
  } catch (error) {
    console.error('手入力用製品一覧取得エラー:', error)
  } finally {
    manualProductsLoading.value = false
  }
}

const selectPlannedProduct = (p) => {
  const nextProductId = p?.product ?? ''
  const isSameProduct = String(record.value.product_id || '') === String(nextProductId || '')
  if (isSameProduct) {
    record.value.product_id = ''
    record.value.product_code = ''
    if (record.value.record_type === 'PRODUCTION') {
      record.value.qty = null
      record.value.operator_action_reason = ''
      selectedOperatorAction.value = ''
    }
    return
  }

  record.value.product_id = p.product || ''
  record.value.product_code = p.product_code || ''
  manualProduct.value = false
  if (record.value.record_type === 'PRODUCTION') {
    record.value.qty = null
  }
  applyScrapTypeDefaults(p)
}

watch(
  () => route.name,
  () => {
    selectedLineId.value = ''
    selectedProcessId.value = ''
    recentRecords.value = []
    productionProducts.value = []
    scrapProducts.value = []
    startedProductIds.value = new Set()
    startedProductIdsLoaded.value = false
    latestOperatorActionByProduct.value = new Map()
    defaultProductId.value = null
    productImageMap.value = {}
    productMetaMap.value = {}
    record.value.operator_name = defaultOperatorName.value || ''
    resetForm()
  }
)

watch(
  () => record.value.reason,
  (val) => {
    if (val !== 'OTHER') {
      record.value.reason_detail = ''
    }
  }
)

watch(
  () => effectiveOperatorAction.value,
  (action) => {
    const actionKey = String(action || '').toUpperCase()
    if (!['PAUSE', 'TEMP_END'].includes(actionKey)) {
      record.value.operator_action_reason = ''
      record.value.operator_action_reason_detail = ''
    }
  }
)

watch(
  () => record.value.operator_action_reason,
  (val) => {
    if (val !== 'その他') {
      record.value.operator_action_reason_detail = ''
    }
  }
)

watch(
  () => record.value.product_id,
  (pid) => {
    if (!pid || record.value.record_type !== 'SCRAP') return
    const candidate =
      scrapProducts.value.find((p) => String(p.product) === String(pid)) ||
      manualProducts.value.find((p) => String(p.id) === String(pid)) ||
      manualProducts.value.find((p) => String(p.product) === String(pid))
    if (candidate) {
      applyScrapTypeDefaults(candidate)
    }
  }
)

watch(
  () => scrapRelationFilter.value,
  (val) => {
    if (record.value.record_type !== 'SCRAP') return
    if (val === 'purchased' || val === 'in_house') {
      record.value.is_production_recorded = true
    } else if (val === 'own_process') {
      record.value.is_production_recorded = ''
    }
  }
)

watch(
  () => record.value.record_type,
  (type) => {
    if (!type) return
    if (type !== 'PRODUCTION') {
      selectedOperatorAction.value = ''
    }
    if (type === 'EQUIPMENT_STATE') {
      record.value.qty = null
      record.value.batch_no = ''
      record.value.operator_name = ''
      record.value.reason_detail = ''
      record.value.reason = ''
    } else if (type === 'SCRAP') {
      if (!(record.value.operator_name || '').trim()) {
        record.value.operator_name = defaultOperatorName.value || ''
      }
      ensureScrapDefaults()
    } else {
      record.value.reason_detail = ''
      record.value.reason = ''
      record.value.disposition_status = ''
      if (!(record.value.operator_name || '').trim()) {
        record.value.operator_name = defaultOperatorName.value || ''
      }
    }
    if (!record.value.product_id && defaultProductId.value) {
      record.value.product_id = defaultProductId.value
      const plan = currentProductList.value.find(
        (p) => String(p.product) === String(defaultProductId.value)
      )
      if (plan) {
        record.value.qty = null
      }
    }
    restoreEquipmentStateIfNeeded()
  },
  { immediate: true }
)

watch(
  () => [record.value.product_id, record.value.product_code],
  () => {
    ensureScrapDefaults()
    loadSelectedCoproductNotice()
  }
)

watch(
  () => [selectedLineId.value, selectedProcessId.value],
  () => {
    restoreEquipmentStateIfNeeded()
  }
)

const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleDateString(localeCode.value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString(localeCode.value, {
    hour: '2-digit',
    minute: '2-digit'
  })
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

const getRecentPlanQty = (rec) => {
  const productCode = String(rec?.product_code || rec?.event_data?.plan_target?.product_code || '').trim()
  if (productCode && rec?.timestamp) {
    const bizDate = formatISODate(getBusinessDate(new Date(rec.timestamp)))
    const byGantt = ganttPlanQtyMap.value?.[productCode]?.[bizDate]
    if (byGantt !== null && byGantt !== undefined && Number.isFinite(Number(byGantt))) {
      return Number(byGantt)
    }
  }
  const eventPlanQty = rec?.event_data?.plan_target?.plan_qty
  if (eventPlanQty !== null && eventPlanQty !== undefined && Number.isFinite(Number(eventPlanQty))) {
    return Number(eventPlanQty)
  }
  const productId = String(rec?.product ?? rec?.product_id ?? '').trim()
  if (productId) {
    const byId = recentPlanQtyLookup.value.get(`id:${productId}`)
    if (Number.isFinite(byId)) return byId
  }
  if (productCode) {
    const byCode = recentPlanQtyLookup.value.get(`code:${productCode}`)
    if (Number.isFinite(byCode)) return byCode
  }
  return 0
}

const formatRecentQtyWithPlan = (rec) => {
  const planQty = getRecentPlanQty(rec)
  return `計画${formatRecentValue(planQty)} / 実績${formatRecentQty(rec?.qty)}`
}

const RECENT_RECORD_COLOR_PALETTE = [
  { border: '#2563eb', bg: '#eff6ff' },
  { border: '#059669', bg: '#ecfdf5' },
  { border: '#d97706', bg: '#fffbeb' },
  { border: '#7c3aed', bg: '#f5f3ff' },
  { border: '#db2777', bg: '#fdf2f8' },
  { border: '#0f766e', bg: '#f0fdfa' },
  { border: '#b91c1c', bg: '#fef2f2' },
]

const hashString = (value) => {
  const text = String(value || '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0
  }
  return hash
}

const getRecentRecordColorStyle = (rec) => {
  const key = String(rec?.product_code || rec?.event_data?.plan_target?.product_code || '').trim()
  if (!key) return null
  const idx = hashString(key) % RECENT_RECORD_COLOR_PALETTE.length
  const color = RECENT_RECORD_COLOR_PALETTE[idx]
  return {
    borderLeft: `4px solid ${color.border}`,
    backgroundColor: color.bg,
  }
}

const pageModeClass = computed(() => {
  switch (record.value.equipment_state) {
    case 'RUNNING':
      return 'page-run'
    case 'IDLE':
      return 'page-idle'
    case 'SETUP':
      return 'page-setup'
    case 'MAINTENANCE':
      return 'page-maintenance'
    case 'BREAKDOWN':
      return 'page-breakdown'
    case 'STOPPED':
      return 'page-stopped'
    default:
      return ''
  }
})

const formModeClass = computed(() => {
  if (record.value.record_type === 'PRODUCTION') return 'mode-production'
  if (record.value.record_type === 'SCRAP') return 'mode-scrap'
  return ''
})

const loadProcesses = async () => {
  try {
    const res = await api.processes.getProcesses({ is_active: true })
    processes.value = res.data.results || res.data || []
  } catch (error) {
    console.error('工程一覧取得エラー:', error)
    alert(t('processInput.alert.loadProcessFailed'))
  }
}

const loadLines = async () => {
  try {
    const res = await api.lines.getProductionLines()
    lines.value = res.data.results || res.data || []
  } catch (error) {
    console.error('ライン一覧取得エラー:', error)
    alert(t('processInput.alert.loadLineFailed'))
  }
}

const toggleSupportMode = () => {
  isSupportMode.value = !isSupportMode.value
  if (isSupportMode.value) return
  const ownIds = new Set(ownLines.value.map((line) => String(line.id)))
  if (selectedLineId.value && ownIds.has(String(selectedLineId.value))) return
  const preferred = preferredUserLineId.value
  if (preferred && ownIds.has(String(preferred))) {
    selectedLineId.value = String(preferred)
    onLineChange()
    return
  }
  if (ownLines.value.length) {
    selectedLineId.value = String(ownLines.value[0].id)
    onLineChange()
  } else {
    selectedLineId.value = ''
    onLineChange()
  }
}

const applySupportModeFromQuery = () => {
  const raw = String(route.query.support_mode || '').toLowerCase()
  if (raw === 'on' || raw === '1' || raw === 'true') {
    isSupportMode.value = true
    return
  }
  if (raw === 'off' || raw === '0' || raw === 'false') {
    isSupportMode.value = false
  }
}

const applyInitialLineSelection = () => {
  const candidateList = Array.isArray(availableLines.value) ? availableLines.value : []
  if (!candidateList.length) {
    selectedLineId.value = ''
    return
  }
  const preferred = preferredUserLineId.value
  if (preferred && candidateList.some((line) => String(line.id) === String(preferred))) {
    selectedLineId.value = String(preferred)
    return
  }
  selectedLineId.value = String(candidateList[0].id)
}

function openEquipmentInspection() {
  const processId = selectedProcessId.value || undefined
  const lineId = selectedLineId.value || undefined
  router.push({
    path: '/quality/equipment-inspection/operation',
    query: {
      ...(processId ? { process_id: String(processId) } : {}),
      ...(lineId ? { line_id: String(lineId) } : {}),
    },
  })
}

function openIntegratedChecksheetOperation() {
  const lineId = selectedLineId.value || undefined
  const processId = selectedProcessId.value || undefined
  router.push({
    path: '/quality/product-checksheet/integrated/operation',
    query: {
      source: 'mobile_process_input',
      ...(lineId ? { line_id: String(lineId) } : {}),
      ...(processId ? { process_id: String(processId) } : {}),
    },
  })
}

const restorePendingProductChecksheetInput = () => {
  const raw = sessionStorage.getItem('product-checksheet:mobile-process-input')
  if (!raw) return false
  try {
    const saved = JSON.parse(raw)
    if (saved.selectedLineId) selectedLineId.value = String(saved.selectedLineId)
    if (saved.selectedProcessId) {
      selectedProcessId.value = String(saved.selectedProcessId)
      onProcessChange()
    }
    if (saved.record) {
      record.value = { ...record.value, ...saved.record }
    }
    sessionStorage.removeItem('product-checksheet:mobile-process-input')
    return true
  } catch (error) {
    console.warn('製品チェックシート入力前の工程入力復元に失敗しました', error)
    return false
  }
}

onMounted(async () => {
  await ensureAuth()
  applySupportModeFromQuery()
  await Promise.all([loadLines(), loadProcesses()])
  applyInitialLineSelection()
  if (restorePendingProductChecksheetInput()) return
  const queryLineId = route.query.line_id
  if (queryLineId) {
    const exists = availableLines.value.some((line) => String(line.id) === String(queryLineId))
    if (exists) {
      selectedLineId.value = String(queryLineId)
    }
  }
  const queryProcessId = route.query.process_id
  if (queryProcessId) {
    selectedProcessId.value = String(queryProcessId)
    onProcessChange()
  }
  if (route.query.operator_name !== undefined) {
    const name = String(route.query.operator_name || '')
    defaultOperatorName.value = name
    record.value.operator_name = name
  } else if (route.query.clear_operator === '1') {
    defaultOperatorName.value = ''
    record.value.operator_name = ''
  }
})

watch(
  () => route.query.support_mode,
  () => {
    applySupportModeFromQuery()
  },
)
</script>

<style scoped>
.mobile-input {
  max-width: 600px;
  margin: 0 auto;
  padding: 10px;
  background: #eef2f6;
  min-height: 100vh;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.mobile-input.page-run {
  background: #86efac;
}
.mobile-input.page-idle {
  background: #f97316;
}
.mobile-input.page-setup {
  background: #fed7aa;
}
.mobile-input.page-maintenance {
  background: #93c5fd;
}
.mobile-input.page-breakdown {
  background: #ef4444;
}
.mobile-input.page-stopped {
  background: #ffffff;
}
.mobile-input.tablet-input {
  max-width: 1080px;
  padding: 16px 18px;
}
.mobile-input.tablet-input .planned-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.mobile-input.tablet-input .planned-cards {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.mobile-input.tablet-input .record-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.mobile-input.embed-tablet .compact-label-row .inline-group {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 6px;
}
.mobile-input.embed-tablet .compact-label-row .inline-label {
  margin-bottom: 0;
  white-space: nowrap;
}
.mobile-input.embed-tablet .compact-label-row .input-large {
  height: 36px;
  padding: 0 8px;
  line-height: 1.2;
  font-size: 14px;
  box-sizing: border-box;
}

.mobile-header {
  background: #fff;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mobile-header h2 {
  margin: 0;
  font-size: 18px;
  color: #1f2a44;
}
.btn-inspection-nav {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #0e7490;
  background: #fff;
  color: #0e7490;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}

.header-info .date {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #64748b;
}
.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn-checksheet-nav {
  border-color: #2563eb;
  color: #2563eb;
}

.section {
  margin-bottom: 10px;
}

.section-title {
  margin: 12px 0 8px 0;
  font-size: 16px;
  font-weight: 700;
  color: #1f2a44;
}

label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
}

.label-required::after {
  content: ' *';
  color: #ef4444;
}

.input-large,
.input-normal,
.textarea-normal {
  width: 100%;
  padding: 12px 12px 12px 0;
  font-size: 14px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  box-sizing: border-box;
  font-family: inherit;
}
.input-large {
  text-align: left;
}

.input-large {
  font-size: 14px;
  font-weight: 600;
}

.input-qty {
  font-size: 30px !important;
  height: 40px;
  line-height: 40px;
  padding: 0 8px;
  text-align: center;
  font-weight: 700;
}
.input-qty::placeholder {
  font-size: 20px;
  font-weight: 400;
}
.qty-row .input-qty {
  max-width: 140px;
}
.qty-group {
  flex: 0 0 33%;
  max-width: 33%;
}

.type-buttons {
  display: flex;
  gap: 8px;
  flex: 1;
}
.single-type {
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  font-weight: 700;
}

.scrap-filter-select {
  min-width: 160px;
}
.scrap-filter-input {
  min-width: 160px;
  flex: 1 1 180px;
}

.state-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.type-btn,
.state-btn {
  padding: 14px;
  border: 2px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn.active,
.state-btn.active {
  border-color: #4a7ae5;
  background: #eff6ff;
  color: #4a7ae5;
}

.state-btn.state-running.active {
  border-color: #16a34a;
  background: #f0fdf4;
  color: #16a34a;
}

.state-btn.state-breakdown.active {
  border-color: #ef4444;
  background: #fef2f2;
  color: #ef4444;
}

.state-btn.state-maintenance.active {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #f59e0b;
}

.quick-btns {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin-bottom: 12px;
}

.btn-quick {
  padding: 10px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.btn-quick:active {
  background: #e2e8f0;
}

.form-section {
  background: #fff;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid transparent;
}
.form-section.mode-production {
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
}
.form-section.mode-scrap {
  background: #ffd6d6;
  border-color: #ffb3b3;
}

.plan-status {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 10px;
  padding: 10px;
  margin-top: 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
}
.plan-status__title {
  grid-column: 1 / -1;
  font-weight: 700;
  font-size: 13px;
  opacity: 0.92;
}
.plan-status__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 13px;
}
.plan-status__label {
  opacity: 0.9;
}
.plan-status__value {
  font-weight: 700;
  font-size: 16px;
}
.plan-status__row--muted {
  color: #e0f2fe;
}

.action-section {
  margin: 12px 0;
}
.action-section.action-sticky {
  position: sticky;
  bottom: 0;
  background: #eef2f6;
  padding: 8px 0;
  margin: 0;
}

.btn-submit {
  width: 100%;
  padding: 16px;
  background: #4a7ae5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}

.btn-submit:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.btn-submit:not(:disabled):hover {
  background: #3865c7;
}

.recent-section {
  background: #fff;
  padding: 12px;
  border-radius: 8px;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-item {
  display: grid;
  grid-template-columns: 60px 1fr auto auto;
  gap: 8px;
  align-items: center;
  padding: 10px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 13px;
}

.record-time {
  font-weight: 600;
  color: #64748b;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.record-date {
  font-size: 12px;
  color: #94a3b8;
}
.record-clock {
  font-size: 13px;
}

.record-type {
  color: #1f2a44;
}

.record-type__label {
  font-weight: 600;
}

.record-type__product {
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
}

.record-qty {
  font-weight: 700;
  color: #16a34a;
}

.record-state {
  font-weight: 600;
  color: #4a7ae5;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}
.planned-buttons {
  margin-top: -2px;
  display: grid;
  gap: 4px;
}
.record-type-btn {
  padding: 6px 10px;
}
.record-type-btn.active {
  border-color: #dc2626;
  background: #ef4444;
  color: #ffffff;
}
.current-processing-banner {
  padding: 10px 12px;
  border-radius: 8px;
  background: #16a34a;
  border: 1px solid #15803d;
  color: #ffffff;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.01em;
}
.current-processing-banner.pause-notice-banner {
  background: #f97316;
  border-color: #ea580c;
  color: #ffffff;
}
.planned-header {
  display: grid;
  gap: 8px;
}
.planned-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.planned-label {
  font-size: 12px;
  color: #475569;
}
.slot-label {
  font-size: 12px;
  color: #0f172a;
  font-weight: 600;
}
.slot-btn {
  width: 44px;
  height: 32px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  border-radius: 6px;
  color: #0f172a;
  font-weight: 800;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.08s ease;
}
.slot-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.slot-btn:not(:disabled):hover {
  background: #e2e8f0;
  border-color: #94a3b8;
}
.slot-btn:not(:disabled):active {
  transform: scale(0.96);
}
.operator-action-row {
  display: grid;
  gap: 4px;
}
.operator-action-title {
  font-size: 12px;
  color: #475569;
}
.operator-action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.operator-action-buttons-inline {
  margin-left: 6px;
}
.operator-action-btn {
  min-width: 68px;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  font-size: 12px;
  color: #334155;
  cursor: pointer;
}
.operator-action-btn.active {
  border-color: #0ea5e9;
  background: #e0f2fe;
  color: #0c4a6e;
  font-weight: 700;
}
.current-time-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
  justify-self: flex-start;
}
.current-time-toggle input {
  width: 16px;
  height: 16px;
  accent-color: #0ea5e9;
}
.planned-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.planned-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
}
.planned-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
  cursor: pointer;
  display: grid;
  gap: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.planned-card.active {
  border-color: #4a7ae5;
  box-shadow: 0 2px 8px rgba(74, 122, 229, 0.25);
}
.card-image {
  width: 100%;
  aspect-ratio: 4/3;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
}
.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.no-image {
  font-size: 12px;
  color: #94a3b8;
}
.card-body {
  display: grid;
  gap: 2px;
}
.card-code {
  font-weight: 700;
  font-size: 14px;
}
.card-name {
  font-size: 12px;
  color: #475569;
}
.card-plan {
  font-size: 12px;
  color: #111827;
}
.btn-planned {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-planned .plan-qty {
  margin-left: 4px;
  color: #475569;
  border-radius: 4px;
  padding: 1px 4px;
}
.status-badge {
  margin-left: 4px;
  border-radius: 4px;
  padding: 1px 4px;
  font-size: 11px;
  font-weight: 700;
}
.status-badge--temp-end {
  background: #94a3b8;
  color: #ffffff;
}
.btn-planned .plan-qty.plan-qty--done,
.btn-planned .plan-qty.plan-qty--over {
  background: #ef4444;
  color: #ffffff;
}
.btn-planned.active {
  border-color: #15803d;
  background: #16a34a;
  color: #ffffff;
}
.btn-planned.current-processing {
  border-color: #1d4ed8;
  background: #2563eb;
  color: #ffffff;
}
.btn-planned.active .plan-qty,
.btn-planned.current-processing .plan-qty {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.22);
}

.btn-link {
  margin-top: 8px;
  padding: 0;
  border: none;
  background: transparent;
  color: #4a7ae5;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

.inline-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.row-label-input {
  align-items: center;
}
.label-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dual-row {
  flex-wrap: nowrap;
  align-items: flex-start;
}
.inline-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  flex: 1 1 0;
  min-width: 0;
}

.inline-label {
  margin: 0;
  min-width: 0;
}
.label-side {
  white-space: nowrap;
  min-width: 4.5em;
}

.flex-input {
  flex: 1;
}
.line-select-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.support-toggle-btn {
  height: 38px;
  min-width: 78px;
  padding: 0 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.support-toggle-btn.active {
  border-color: #f59e0b;
  background: #ffedd5;
  color: #9a3412;
}

.product-row {
  align-items: flex-start;
}
.product-inputs {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.product-select-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.coproduct-notice {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  background: #fffbeb;
}
.coproduct-notice__loading {
  font-size: 12px;
  color: #92400e;
  font-weight: 600;
}
.coproduct-notice__title {
  font-size: 13px;
  font-weight: 700;
  color: #92400e;
  line-height: 1.5;
}
.coproduct-notice__label {
  font-size: 12px;
  font-weight: 700;
  color: #b45309;
}
.coproduct-notice__children {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.coproduct-notice__chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #fcd34d;
  color: #78350f;
  font-size: 12px;
  font-weight: 700;
}
.coproduct-notice__chip-name {
  font-weight: 500;
}
.product-toggle {
  margin-top: 0;
}
.toggle-link {
  padding: 0;
}
.inline-link {
  margin-top: 0;
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
