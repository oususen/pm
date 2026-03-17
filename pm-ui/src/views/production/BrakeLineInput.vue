<template>
  <div class="brake-line-input">
    <!-- ヘッダー -->
    <div class="header">
      <h2 class="page-title">{{ t('brakeInput.pageTitle') }}</h2>
      <button class="btn-scrap-nav" @click="router.push('/production/scrap-record')">{{ t('productionMenu.tiles.scrapRecord') }}</button>
      <div class="header-controls">
        <label class="header-label">{{ t('brakeInput.process') }}</label>
        <select v-model="selectedProcessId" class="process-select" @change="onProcessChange">
          <option value="">{{ t('brakeInput.selectProcess') }}</option>
          <option v-for="p in processes" :key="p.id" :value="p.id">
            {{ p.process_code }} {{ p.process_name }}
          </option>
        </select>
        <label class="header-label">{{ t('brakeInput.date') }}</label>
        <input type="date" v-model="planDateStr" class="date-input" @change="loadPlan" />
        <span class="laser-date-label">{{ t('brakeInput.laserDate', { date: laserDateStr }) }}</span>
        <div class="header-processing" :class="{ empty: !currentProcessingMessages.length }">
          <template v-if="currentProcessingMessages.length">
            <span
              v-for="(msg, i) in currentProcessingMessages"
              :key="msg.equipmentKey"
              class="processing-chip"
              @click="jumpToProcessingItem(msg)"
            >{{ msg.label }}<template v-if="i < currentProcessingMessages.length - 1"> / </template></span>
          </template>
          <template v-else>{{ t('brakeInput.noProcessing') }}</template>
        </div>
      </div>
    </div>

    <!-- 4列レイアウト -->
    <div class="four-col-layout">

      <!-- 列①: コントロール -->
      <div class="col-controls">
        <!-- フィルター -->
        <div class="section-title">{{ t('brakeInput.displaySettings') }}</div>
        <div class="filter-area">
          <label class="filter-item">
            <span class="toggle-label">{{ t('brakeInput.showDone') }}</span>
            <input type="checkbox" v-model="showDone" class="toggle-input" />
            <span class="toggle-track" :class="{ on: showDone }"></span>
          </label>
          <label class="filter-item">
            <span class="toggle-label">{{ t('brakeInput.showTomorrow') }}</span>
            <input type="checkbox" v-model="showTomorrow" class="toggle-input" @change="onTomorrowToggle" />
            <span class="toggle-track" :class="{ on: showTomorrow }"></span>
          </label>
          <label class="filter-item">
            <span class="toggle-label">{{ t('brakeInput.showYesterday') }}</span>
            <input type="checkbox" v-model="showYesterday" class="toggle-input" @change="onYesterdayToggle" />
            <span class="toggle-track" :class="{ on: showYesterday }"></span>
          </label>
        </div>

        <!-- 作業者 -->
        <div class="section-title" style="margin-top:12px">{{ t('brakeInput.operator') }}</div>
        <div class="operator-area">
          <input
            type="text"
            v-model="operator"
            class="operator-input"
            :placeholder="t('brakeInput.operatorPlaceholder')"
          />
        </div>

        <!-- 端末別印刷設定 -->
        <div class="section-title" style="margin-top:12px">印刷設定</div>
        <div class="print-setting-area">
          <label class="filter-item">
            <span class="toggle-label">自動印刷</span>
            <input type="checkbox" v-model="printAutoEnabled" class="toggle-input" @change="savePrintSettings" />
            <span class="toggle-track" :class="{ on: printAutoEnabled }"></span>
          </label>
          <input
            type="text"
            v-model.trim="printDeviceId"
            class="operator-input"
            placeholder="端末ID"
            @change="savePrintSettings"
          />
          <input
            type="text"
            v-model.trim="printPrinterName"
            class="operator-input"
            placeholder="プリンタ名（表示用）"
            @change="savePrintSettings"
          />
        </div>

        <!-- 新規追加ボタン -->
        <div class="add-btn-area">
          <button class="btn-add-new" @click="openAddModal">{{ t('brakeInput.addNew') }}</button>
        </div>

        <!-- 注意書き -->
        <div class="hint-box">
          <p>{{ t('brakeInput.hintNewLine1') }}<br>　{{ t('brakeInput.hintNewLine2') }}</p>
          <p style="margin-top:8px">{{ t('brakeInput.hintExtraLine1') }}<br>　{{ t('brakeInput.hintExtraLine2') }}</p>
        </div>
      </div>

      <!-- 列②: 製品リスト -->
      <div class="col-list">
        <div class="list-header">
          <span class="list-count">{{ t('brakeInput.itemCount', { n: filteredItems.length }) }}</span>
        </div>

        <div class="plan-list" v-if="!loading">
          <div
            v-for="item in pagedItems"
            :key="itemKey(item)"
            class="plan-item"
            :class="{
              selected: isSelected(item),
              done: isDone(item),
              manual: item.is_manual,
            }"
            @click="selectItem(item)"
          >
            <div class="item-avatar" :style="{ backgroundColor: avatarColor(item.product_code) }">
              {{ item.product_code.slice(0, 2) }}
            </div>
            <div class="item-info">
              <div class="item-code">{{ item.product_code }}</div>
              <div class="item-sub">{{ planDateStr }}</div>
            </div>
            <div v-if="isDone(item)" class="done-badge">✓{{ item.actual_qty }}</div>
            <div v-if="item.is_manual" class="manual-badge">{{ item.product_id ? t('brakeInput.badgeExtra') : t('brakeInput.badgeNew') }}</div>
          </div>
          <div v-if="filteredItems.length === 0" class="empty-list">
            {{ t('brakeInput.emptyList') }}
          </div>
        </div>
        <div class="plan-list loading-list" v-else>
          <div class="loading-text">{{ t('brakeInput.loading') }}</div>
        </div>

        <!-- ページネーション -->
        <div class="pagination">
          <button class="page-btn" @click="goFirstPage" :disabled="currentPage === 1">⟨⟨</button>
          <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">⟨</button>
          <span class="page-info">{{ pageStart }}-{{ pageEnd }}/{{ filteredItems.length }}</span>
          <button class="page-btn" @click="nextPage" :disabled="currentPage >= totalPages">⟩</button>
          <button class="page-btn" @click="goLastPage" :disabled="currentPage >= totalPages">⟩⟩</button>
        </div>
      </div>

      <!-- 列③: 登録フォーム -->
      <div class="col-form">
        <template v-if="!selectedItem">
          <div class="no-selection">
            <span>{{ t('brakeInput.selectItem') }}</span>
          </div>
        </template>

        <template v-else>
          <div class="form-area">
            <!-- 製品情報 -->
            <div class="product-header">
              <div class="product-code-large">{{ selectedItem.product_code }}</div>
              <div class="product-name">{{ selectedItem.product_name }}</div>
              <div class="process-badge">{{ selectedItem.process_name }}</div>
            </div>

            <!-- 実績サマリ + 作業アクション -->
            <div class="stats-and-actions">
              <div class="current-actual">
                <div class="stat-block">
                  <span class="stat-label">{{ t('brakeInput.planQty') }}</span>
                  <span class="stat-value plan">{{ selectedItem.plan_qty }}</span>
                </div>
                <div class="stat-block">
                  <span class="stat-label">{{ t('brakeInput.actualQty') }}</span>
                  <span class="stat-value actual">{{ currentActualQty }}</span>
                </div>
                <div class="stat-block">
                  <span class="stat-label">{{ t('brakeInput.remaining') }}</span>
                  <span class="stat-value remain" :class="{ over: currentActualQty >= selectedItem.plan_qty }">
                    {{ Math.max(0, selectedItem.plan_qty - currentActualQty) }}
                  </span>
                </div>
              </div>

              <!-- 作業アクションボタン -->
              <div class="action-btns-area">
                <label class="equip-label">{{ t('brakeInput.action') }} <span class="required-mark">*</span></label>
                <div class="op-action-btns">
                  <button
                    v-for="act in operatorActionOptions"
                    :key="act.value"
                    class="op-action-btn"
                    :class="[`action-${act.value.toLowerCase()}`, { active: selectedAction === act.value }]"
                    @click="selectAction(act.value)"
                  >{{ act.label }}</button>
                </div>
                <div v-if="selectedItem && !selectedEquipmentId" class="equip-empty">{{ t('brakeInput.selectEquipFirst') }}</div>
              </div>
            </div>

            <!-- 加工中の開始者 -->
            <div v-if="currentWorkState === 'STARTED' && currentOperator" class="started-by-area">
              <span class="started-by-label">{{ t('brakeInput.startedBy') }}</span>
              <span class="started-by-name">{{ currentOperator }}</span>
            </div>

            <!-- 使用設備（必須） -->
            <div class="equip-select-area">
              <label class="equip-label">{{ t('brakeInput.equipment') }} <span class="required-mark">*</span></label>
              <div class="equip-btns">
                <button
                  v-for="eq in equipments"
                  :key="eq.id"
                  class="equip-btn"
                  :class="{ active: selectedEquipmentId === eq.id }"
                  @click="selectedEquipmentId = eq.id"
                >{{ eq.equipment_code }}<br><span class="equip-btn-name">{{ eq.equipment_name }}</span></button>
              </div>
              <div v-if="equipments.length === 0" class="equip-empty">{{ t('brakeInput.noEquipment') }}</div>
            </div>

            <!-- 数量入力（END/PAUSE のみ） -->
            <div v-if="requiresQty" class="qty-input-area">
              <div class="qty-row">
                <div class="qty-col">
                  <label class="qty-label">{{ t('brakeInput.processQty') }}</label>
                  <input
                    ref="qtyInputRef"
                    type="number"
                    v-model.number="inputQty"
                    min="1"
                    step="1"
                    inputmode="numeric"
                    class="qty-input qty-input-narrow"
                    :placeholder="t('brakeInput.qtyPlaceholder')"
                    @keyup.enter="save"
                  />
                </div>
                <div class="qty-col scrap-col">
                  <label class="qty-label scrap-label">{{ t('productionMenu.tiles.scrapRecord') }}</label>
                  <div class="scrap-inline">
                    <input
                      type="number"
                      v-model.number="scrapQty"
                      min="0"
                      step="1"
                      inputmode="numeric"
                      class="qty-input qty-input-narrow"
                      :placeholder="t('brakeInput.qtyPlaceholder')"
                    />
                    <select v-model="scrapReason" class="scrap-reason-select">
                      <option value="">{{ t('brakeInput.selectReason') }}</option>
                      <option v-for="r in SCRAP_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <!-- 理由（中断・一時終了） -->
            <div v-if="requiresReason" class="reason-area">
              <label class="qty-label">
                {{ selectedAction === 'TEMP_END' ? t('brakeInput.tempEndReasonLabel') : t('brakeInput.pauseReasonLabel') }}
                <span class="required-mark">*</span>
              </label>
              <select v-model="actionReason" class="reason-select">
                <option value="">{{ t('brakeInput.selectReason') }}</option>
                <option v-for="r in reasonOptions" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>

            <!-- アクションバー -->
            <div class="action-bar">
              <button class="btn-save" :disabled="!canSave" @click="save">{{ t('brakeInput.save') }}</button>
              <button class="btn-cancel" @click="cancel">{{ t('brakeInput.cancel') }}</button>
            </div>
          </div>
        </template>
      </div>

      <!-- 列④: 製品写真（将来用） -->
      <div class="col-photo">
        <div class="section-title">製品写真</div>
        <div class="photo-placeholder">
          <template v-if="selectedItem">
            <div class="photo-product-code">{{ selectedItem.product_code }}</div>
            <div class="photo-icon">📷</div>
            <div class="photo-label">将来実装予定</div>
          </template>
          <template v-else>
            <div class="photo-icon muted">📷</div>
            <div class="photo-label muted">品番を選択すると<br>写真が表示されます</div>
          </template>
        </div>
      </div>

    </div><!-- /four-col-layout -->

    <!-- 新規/追加モーダル -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="closeAddModal">
      <div class="modal">
        <h3 class="modal-title">{{ t('brakeInput.modalTitle') }}</h3>

        <div class="modal-field">
          <label>{{ t('brakeInput.typeLabel') }}</label>
          <div class="add-type-btns">
            <button class="type-btn" :class="{ active: addType === 'extra' }" @click="addType = 'extra'">
              {{ t('brakeInput.typeExtra') }}
            </button>
            <button class="type-btn" :class="{ active: addType === 'new' }" @click="addType = 'new'">
              {{ t('brakeInput.typeNew') }}
            </button>
          </div>
        </div>

        <div v-if="addType === 'extra'" class="modal-field">
          <label>{{ t('brakeInput.productCode') }}</label>
          <select v-model="addProductId" class="modal-select" @change="onAddProductSelect">
            <option value="">{{ t('brakeInput.selectProduct') }}</option>
            <option v-for="p in brakeLineProducts" :key="p.id" :value="p.id">
              {{ p.product_code }}　{{ p.product_name }}
            </option>
          </select>
          <div v-if="addProductId" class="selected-product-name">
            {{ brakeLineProducts.find(p => p.id === addProductId)?.product_name }}
          </div>
        </div>

        <div v-if="addType === 'new'" class="modal-field">
          <label>{{ t('brakeInput.productCodeManual') }}</label>
          <input
            type="text"
            v-model="addProductCodeManual"
            class="modal-input"
            :placeholder="t('brakeInput.productCodePlaceholder')"
            @input="addProductCodeManual = addProductCodeManual.toUpperCase()"
          />
          <div class="modal-hint">{{ t('brakeInput.newProductHint') }}</div>
        </div>

        <div class="modal-field">
          <label>{{ t('brakeInput.processLabel') }}</label>
          <select v-model="addProcessId" class="modal-select" disabled style="opacity:0.6;cursor:not-allowed;">
            <option v-for="p in processes" :key="p.id" :value="p.id">
              {{ p.process_code }} {{ p.process_name }}
            </option>
          </select>
        </div>

        <!-- 設備（必須） -->
        <div class="modal-field">
          <label>{{ t('brakeInput.equipmentLabel') }} <span class="required-mark">*</span></label>
          <div class="equip-btns equip-btns-modal">
            <button
              v-for="eq in addEquipments"
              :key="eq.id"
              class="equip-btn"
              :class="{ active: addEquipmentId === eq.id }"
              @click="addEquipmentId = eq.id"
            >{{ eq.equipment_code }}<br><span class="equip-btn-name">{{ eq.equipment_name }}</span></button>
          </div>
          <div v-if="addEquipments.length === 0" class="equip-empty">{{ t('brakeInput.noEquipment') }}</div>
        </div>

        <div v-if="addError" class="modal-error">{{ addError }}</div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="closeAddModal">{{ t('brakeInput.cancel') }}</button>
          <button class="btn-save" @click="confirmAdd" :disabled="!canConfirmAdd">{{ t('brakeInput.confirmAdd') }}</button>
        </div>
      </div>
    </div>


    <!-- トースト通知 -->
    <transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import QRCode from 'qrcode'
import api from '@/api/client'
import { authState } from '@/auth'
import { t } from '@/i18n'

const SCRAP_REASONS = [
  { value: '500:その他',          label: '500: その他' },
  { value: '501:精度調整/試し曲げ', label: '501: 精度調整/試し曲げ' },
  { value: '502:精度不良',         label: '502: 精度不良' },
  { value: '503:変形/キズ',        label: '503: 変形/キズ' },
]

// ──────────────────────────────
// 日付ユーティリティ（8時区切り）
// ──────────────────────────────
const toYmd = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
const businessToday = () => {
  const d = new Date()
  if (d.getHours() < 8) d.setDate(d.getDate() - 1)
  return toYmd(d)
}
const addDays = (ymd, n) => {
  const d = new Date(ymd)
  d.setDate(d.getDate() + n)
  return toYmd(d)
}

// ──────────────────────────────
// 状態
// ──────────────────────────────
const router = useRouter()
const planDateStr = ref(businessToday())
const laserDateStr = ref('')  // バックエンドが営業日計算した値を使用
const processes = ref([])
const lines = ref([])
const allItems = ref([])
const selectedProcessId = ref('')
const selectedItem = ref(null)
const currentActualQty = ref(0)
const inputQty = ref(null)
const loading = ref(false)
const operator = ref('')
const printAutoEnabled = ref(false)
const printDeviceId = ref('')
const printPrinterName = ref('')

// フィルター
const showDone = ref(false)
const showTomorrow = ref(false)
const showYesterday = ref(false)

// ページネーション
const PAGE_SIZE = 25
const currentPage = ref(1)


// 設備
const equipments = ref([])            // メインフォーム用設備一覧
const selectedEquipmentId = ref('')   // メインフォーム選択設備

// 作業アクション
const selectedAction = ref('')        // 選択中アクション
const actionReason = ref('')          // 中断/一時終了の理由
const workStateMap = ref({})          // {stateKey: lastAction}
const workOperatorMap = ref({})       // {stateKey: 開始者名}
const currentProcessingByEquipment = ref({}) // {equipmentKey: {equipmentLabel, productCode}}

const pauseReasons = computed(() => [
  t('brakeInput.pauseReason.equipmentTrouble'),
  t('brakeInput.pauseReason.jigTrouble'),
  t('brakeInput.pauseReason.qualityTrouble'),
  t('brakeInput.pauseReason.materialWait'),
  t('brakeInput.pauseReason.setup'),
  t('brakeInput.pauseReason.leaderWait'),
  t('brakeInput.pauseReason.activity3s'),
  t('brakeInput.pauseReason.improvement'),
  t('brakeInput.pauseReason.other'),
])
const tempEndReasons = computed(() => [
  t('brakeInput.tempEndReason.noEquipment'),
  t('brakeInput.tempEndReason.noJig'),
  t('brakeInput.tempEndReason.switchProduct'),
  t('brakeInput.tempEndReason.materialShortage'),
  t('brakeInput.tempEndReason.other'),
])

const NOT_STARTED_ACTIONS = ['START']
const STARTED_ACTIONS     = ['END', 'PAUSE']
const PAUSED_ACTIONS      = ['RESUME', 'TEMP_END']
const TEMP_ENDED_ACTIONS  = ['RESUME']
const actionLabels = computed(() => ({
  START: t('brakeInput.actionStart'),
  END: t('brakeInput.actionEnd'),
  PAUSE: t('brakeInput.actionPause'),
  RESUME: t('brakeInput.actionResume'),
  TEMP_END: t('brakeInput.actionTempEnd'),
}))

const isSameId = (a, b) => String(a ?? '').trim() === String(b ?? '').trim()

const buildEquipmentKey = (equipmentId) => {
  const id = String(equipmentId || '').trim()
  return id ? `id:${id}` : ''
}

const buildEquipmentLabel = (equipmentId, equipmentCode = '', equipmentName = '') => {
  const name = String(equipmentName || '').trim()
  if (name) return name
  const code = String(equipmentCode || '').trim()
  if (code) return code

  const id = String(equipmentId || '').trim()
  if (!id) return ''
  const eq = equipments.value.find((row) => String(row.id) === id)
  return String(eq?.equipment_name || eq?.equipment_code || '').trim()
}

const workStateKey = (item, equipmentId) => {
  if (!item) return ''
  const productKey = item.product_id || item.product_code
  const equipmentKey = buildEquipmentKey(equipmentId) || 'none'
  return `${item.process_id}-${productKey}-${equipmentKey}`
}

const currentWorkState = computed(() => {
  if (!selectedItem.value || !selectedEquipmentId.value) return 'NOT_STARTED'
  const last = workStateMap.value[workStateKey(selectedItem.value, selectedEquipmentId.value)]
  if (last === 'PAUSE')                   return 'PAUSED'
  if (last === 'TEMP_END')                return 'TEMP_ENDED'
  if (last === 'START' || last === 'RESUME') return 'STARTED'
  return 'NOT_STARTED'
})

// 加工中の場合の開始者名（設備未選択時は全設備を確認して最初に見つかった作業者を返す）
const currentOperator = computed(() => {
  if (!selectedItem.value) return ''
  if (selectedEquipmentId.value) {
    const key = workStateKey(selectedItem.value, selectedEquipmentId.value)
    return workOperatorMap.value[key] || ''
  }
  // 設備未選択時: この品番に関するいずれかの加工中作業者を返す
  const productKey = selectedItem.value.product_id || selectedItem.value.product_code
  const prefix = `${selectedItem.value.process_id}-${productKey}-`
  for (const [k, op] of Object.entries(workOperatorMap.value)) {
    if (k.startsWith(prefix)) return op
  }
  return ''
})

const operatorActionOptions = computed(() => {
  const toOpts = (actions) => actions.map(v => ({ value: v, label: actionLabels.value[v] }))
  if (!selectedItem.value || !selectedEquipmentId.value) return []
  if (currentWorkState.value === 'STARTED')    return toOpts(STARTED_ACTIONS)
  if (currentWorkState.value === 'PAUSED')     return toOpts(PAUSED_ACTIONS)
  if (currentWorkState.value === 'TEMP_ENDED') return toOpts(TEMP_ENDED_ACTIONS)
  return toOpts(NOT_STARTED_ACTIONS)
})

const requiresQty    = computed(() => selectedAction.value === 'END' || selectedAction.value === 'PAUSE')
const requiresReason = computed(() => selectedAction.value === 'PAUSE' || selectedAction.value === 'TEMP_END')
const reasonOptions  = computed(() => selectedAction.value === 'TEMP_END' ? tempEndReasons.value : pauseReasons.value)

const currentProcessingMessages = computed(() => {
  const selectedProcessKey = String(selectedProcessId.value || '').trim()
  return Object.entries(currentProcessingByEquipment.value || {})
    .map(([equipmentKey, row]) => {
      const equipmentLabel = String(row?.equipmentLabel || '').trim()
      const productCode = String(row?.productCode || '').trim()
      const processKey = String(row?.processId ?? '').trim()
      if (!equipmentLabel) return null
      if (selectedProcessKey && processKey && selectedProcessKey !== processKey) return null
      return {
        equipmentKey,
        equipmentId: row?.equipment_id ?? null,
        productCode,
        label: productCode
          ? t('brakeInput.processingWithProduct', { equipment: equipmentLabel, product: productCode })
          : t('brakeInput.processingNoProduct', { equipment: equipmentLabel }),
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.label.localeCompare(b.label))
})
const headerProcessingText = computed(() => {
  return currentProcessingMessages.value.map((row) => row.label).join(' / ')
})

// 新規/追加モーダル
const showAddModal = ref(false)
const addType = ref('extra')          // 'extra'=追加(既存品セレクト) / 'new'=新規(手入力)
const addProductId = ref('')          // 追加: 選択した product.id
const addProductCodeManual = ref('')  // 新規: 手入力品番
const addProcessId = ref('')          // 追加/新規時の工程
const addEquipmentId = ref('')        // 追加/新規時の設備
const addError = ref('')
const brakeLineProducts = ref([])     // ブレーキライン加工品一覧（追加用）
const addEquipments = ref([])         // 追加モーダル用設備一覧

// トースト
const toast = ref({ show: false, message: '', type: 'success' })
const PRINT_SETTINGS_KEY = 'brake_line_print_settings_v1'

const qtyInputRef = ref(null)
const scrapQty = ref(null)
const scrapReason = ref('')

watch(
  () => operatorActionOptions.value.map((item) => item.value).join('|'),
  () => {
    syncSelectedAction()
  },
  { immediate: true }
)

watch(
  () => selectedAction.value,
  (action) => {
    const key = String(action || '').toUpperCase()
    if (!(key === 'PAUSE' || key === 'TEMP_END')) {
      actionReason.value = ''
    }
    if (key !== 'END') {
      inputQty.value = null
    }
  }
)

// ──────────────────────────────
// 作業者初期化（ログインユーザー）
// ──────────────────────────────
onMounted(async () => {
  loadPrintSettings()
  const user = authState.user
  if (user) {
    const last = user.last_name || ''
    const first = user.first_name || ''
    operator.value = (last + ' ' + first).trim() || user.username || ''
  }
  await loadPlan()
})

function inferDeviceId() {
  const host = String(window?.location?.hostname || '').trim()
  const ua = String(window?.navigator?.userAgent || '').trim()
  const uaShort = ua.slice(0, 24).replace(/\s+/g, '_')
  return [host, uaShort].filter(Boolean).join('_') || 'device-01'
}

function loadPrintSettings() {
  try {
    const raw = window.localStorage.getItem(PRINT_SETTINGS_KEY)
    if (!raw) {
      printDeviceId.value = inferDeviceId()
      return
    }
    const parsed = JSON.parse(raw)
    printAutoEnabled.value = !!parsed.autoEnabled
    printDeviceId.value = String(parsed.deviceId || '').trim() || inferDeviceId()
    printPrinterName.value = String(parsed.printerName || '').trim()
  } catch {
    printDeviceId.value = inferDeviceId()
  }
}

function savePrintSettings() {
  const payload = {
    autoEnabled: !!printAutoEnabled.value,
    deviceId: String(printDeviceId.value || '').trim(),
    printerName: String(printPrinterName.value || '').trim(),
  }
  window.localStorage.setItem(PRINT_SETTINGS_KEY, JSON.stringify(payload))
}

async function buildPrintHtml(item, qty) {
  const productCode = String(item?.product_code || '')
  const productName = String(item?.product_name || '')
  const processName = String(item?.process_name || '')
  const nextProcessName = String(item?.next_process_name || '—')
  const operatorName = String(operator.value || '')
  const processDate = planDateStr.value || ''

  // QRコード（製品番号のみ）をData URLとして生成
  let qrDataUrl = ''
  try {
    qrDataUrl = await QRCode.toDataURL(productCode, { margin: 1, width: 120 })
  } catch {
    qrDataUrl = ''
  }

  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>加工品ラベル</title>
  <style>
    @page { size: 50mm 80mm; margin: 0; }
    html, body { width: 50mm; height: 80mm; margin: 0; padding: 0; }
    body { font-family: "Yu Gothic", "Meiryo", sans-serif; box-sizing: border-box; }
    .label { width: 50mm; height: 80mm; padding: 2.5mm; padding-top: 10mm; border: 1px solid #000; box-sizing: border-box; display: flex; flex-direction: column; gap: 0; }
    .title { font-size: 8pt; font-weight: 700; text-align: center; border-bottom: 0.5px solid #000; padding-bottom: 1mm; margin-bottom: 1mm; }
    .code { font-size: 13pt; font-weight: 900; letter-spacing: .2mm; line-height: 1.1; }
    .name { font-size: 7.5pt; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 1mm; }
    .row { display: flex; align-items: baseline; font-size: 7.5pt; line-height: 1.4; gap: 1.5mm; }
    .row .lbl { color: #555; flex-shrink: 0; font-size: 6.5pt; }
    .row .val { font-weight: 700; }
    .qty-row { display: flex; align-items: baseline; margin-top: 1mm; gap: 1.5mm; }
    .qty-lbl { font-size: 7pt; color: #555; flex-shrink: 0; }
    .qty-val { font-size: 18pt; font-weight: 900; line-height: 1; }
    .qr-area { margin-top: auto; display: flex; justify-content: flex-end; }
    .qr-area img { width: 22mm; height: 22mm; }
  </style>
</head>
<body>
  <div class="label">
    <div class="title">加工品ラベル</div>
    <div class="code">${productCode}</div>
    <div class="name">${productName}</div>
    <div class="row"><span class="lbl">加工工程</span><span class="val">${processName}</span></div>
    <div class="row"><span class="lbl">後工程</span><span class="val">${nextProcessName}</span></div>
    <div class="row"><span class="lbl">加工日</span><span class="val">${processDate}</span></div>
    <div class="row"><span class="lbl">加工者</span><span class="val">${operatorName}</span></div>
    <div class="qty-row">
      <span class="qty-lbl">加工数</span>
      <span class="qty-val">${qty}</span>
    </div>
    <div class="qr-area">
      ${qrDataUrl ? `<img src="${qrDataUrl}" alt="QR" />` : ''}
    </div>
  </div>
</body>
</html>`
}

async function printLabel(item, qty) {
  const win = window.open('', '_blank')
  if (!win) {
    showToast('印刷ウィンドウを開けませんでした', 'error')
    return
  }
  const html = await buildPrintHtml(item, qty)
  win.document.open()
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => {
    win.print()
    win.onafterprint = () => win.close()
  }, 200)
}

// ──────────────────────────────
// 計画取得
// ──────────────────────────────
async function loadPlan() {
  loading.value = true
  selectedItem.value = null
  currentPage.value = 1
  selectedAction.value = ''
  actionReason.value = ''
  try {
    const res = await api.brakeLineActuals.getPlan(planDateStr.value)
    const data = res.data
    processes.value = data.processes || []
    lines.value = data.lines || []
    allItems.value = data.items || []
    laserDateStr.value = data.laser_date || ''
    // 工程が未選択なら最初の工程を選択
    if (!selectedProcessId.value && processes.value.length > 0) {
      selectedProcessId.value = processes.value[0].id
    }
    // 工程が確定したら設備・作業記録状態をロード
    if (selectedProcessId.value) {
      await Promise.all([
        fetchEquipments(selectedProcessId.value),
        fetchWorkStates(),
      ])
    } else {
      workStateMap.value = {}
      currentProcessingByEquipment.value = {}
    }
  } catch (e) {
    showToast(e?.response?.data?.detail || t('brakeInput.error.loadFailed'), 'error')
  } finally {
    loading.value = false
  }
}

async function fetchWorkStates() {
  try {
    const res = await api.brakeLineActuals.getRecordStates(planDateStr.value, selectedProcessId.value)
    const payload = res.data || {}
    if (payload.item_states || payload.processing_by_equipment) {
      workStateMap.value = payload.item_states || {}
      workOperatorMap.value = payload.item_operators || {}
      const processing = payload.processing_by_equipment || {}
      const normalized = {}
      Object.entries(processing).forEach(([equipmentKey, row]) => {
        normalized[equipmentKey] = {
          equipmentLabel: buildEquipmentLabel(row?.equipment_id, row?.equipment_code, row?.equipment_name),
          productCode: String(row?.product_code || '').trim(),
          processId: row?.process_id ?? '',
          equipment_id: row?.equipment_id ?? null,
        }
      })
      currentProcessingByEquipment.value = normalized
    } else {
      // 旧レスポンス互換（state_mapのみ）
      workStateMap.value = payload || {}
      workOperatorMap.value = {}
      currentProcessingByEquipment.value = {}
    }
  } catch {
    workStateMap.value = {}
    workOperatorMap.value = {}
    currentProcessingByEquipment.value = {}
  }
}

// ──────────────────────────────
// フィルター・表示リスト
// ──────────────────────────────
const processFilteredItems = computed(() => {
  const items = selectedProcessId.value
    ? allItems.value.filter(item => isSameId(item.process_id, selectedProcessId.value))
    : allItems.value
  // 同じ品番・工程の重複は先着優先で1行のみ表示
  const seen = new Set()
  return items.filter(item => {
    const key = `${item.process_id}-${item.product_id || `code:${item.product_code}`}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})

const filteredItems = computed(() => {
  let items = processFilteredItems.value
  if (!showDone.value) {
    items = items.filter(item => !isDone(item))
  }
  return items
})

const pagedItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredItems.value.slice(start, start + PAGE_SIZE)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / PAGE_SIZE)))
const pageStart = computed(() => {
  if (filteredItems.value.length === 0) return 0
  return (currentPage.value - 1) * PAGE_SIZE + 1
})
const pageEnd = computed(() => Math.min(currentPage.value * PAGE_SIZE, filteredItems.value.length))

// ──────────────────────────────
// 計算プロパティ
// ──────────────────────────────
const isDone = (item) => {
  if (item.actual_qty <= 0) return false
  // PAUSE/TEMP_END 中のアイテムは「加工済み」扱いしない（未完了のため常に表示）
  const hasPause = equipments.value.concat([{ id: null }]).some(eq => {
    const st = workStateMap.value[workStateKey(item, eq.id)]
    return st === 'PAUSE' || st === 'TEMP_END'
  })
  return !hasPause
}
const isSelected = (item) => {
  if (!selectedItem.value) return false
  return itemKey(item) === itemKey(selectedItem.value)
}
const itemKey = (item) => `${item.line_id}-${item.process_id}-${item.product_id || `code:${item.product_code || ''}`}`
const canSave = computed(() => {
  if (!selectedItem.value) return false
  if (!selectedEquipmentId.value) return false
  if (!selectedAction.value) return false
  if (requiresQty.value && !(inputQty.value > 0)) return false
  if (requiresReason.value && !actionReason.value) return false
  return true
})

// ──────────────────────────────
// アバターカラー（品番ハッシュ）
// ──────────────────────────────
const AVATAR_COLORS = ['#4e7cbf', '#7b5ea7', '#2e9688', '#c0714f', '#5e9e5e', '#c0954f', '#6a7fc0']
const avatarColor = (code) => {
  let h = 0
  for (let i = 0; i < code.length; i++) h = (h * 31 + code.charCodeAt(i)) & 0xffffffff
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length]
}

// ──────────────────────────────
// 操作
// ──────────────────────────────
async function selectItem(item) {
  selectedItem.value = item
  currentActualQty.value = item.actual_qty
  inputQty.value = null
  actionReason.value = ''
  // 設備が明示指定されているアイテム（手動追加）はその設備に切り替える
  // 設備未指定のアイテム（計画品）は設備選択を維持する
  if (item?.equipment_id) {
    selectedEquipmentId.value = item.equipment_id
  }
  // 設備は工程単位でロード済み。計画品は設備選択を維持する
  syncSelectedAction()
  nextTick(() => qtyInputRef.value?.focus())
}

function selectAction(action) {
  selectedAction.value = action
  actionReason.value = ''
  if (action === 'END') {
    nextTick(() => qtyInputRef.value?.focus())
  }
}

async function fetchEquipments(processId) {
  try {
    const res = await api.brakeLineActuals.getEquipments(processId)
    equipments.value = res.data || []
    if (selectedEquipmentId.value) {
      const exists = equipments.value.some((eq) => isSameId(eq.id, selectedEquipmentId.value))
      if (!exists) selectedEquipmentId.value = ''
    }
  } catch {
    equipments.value = []
    selectedEquipmentId.value = ''
  }
}

function cancel() {
  selectedItem.value = null
  inputQty.value = null
  selectedAction.value = ''
  actionReason.value = ''
  scrapQty.value = null
  scrapReason.value = ''
}

function jumpToProcessingItem(msg) {
  // 品番・工程が一致するアイテムを検索してフォームを開く
  const item = allItems.value.find(
    i => i.product_code === msg.productCode && isSameId(i.process_id, selectedProcessId.value)
  )
  if (!item) return
  selectedItem.value = item
  if (msg.equipmentId) {
    selectedEquipmentId.value = msg.equipmentId
  }
  selectedAction.value = ''
  inputQty.value = null
  actionReason.value = ''
  syncSelectedAction()
  // リスト内のページを合わせる
  const idx = filteredItems.value.findIndex(i => isSameId(i.product_id || i.product_code, item.product_id || item.product_code))
  if (idx >= 0) currentPage.value = Math.floor(idx / PAGE_SIZE) + 1
}

async function onProcessChange() {
  selectedItem.value = null
  currentPage.value = 1
  selectedEquipmentId.value = ''
  selectedAction.value = ''
  actionReason.value = ''
  if (selectedProcessId.value) {
    await Promise.all([
      fetchEquipments(selectedProcessId.value),
      fetchWorkStates(),
    ])
  } else {
    equipments.value = []
    workStateMap.value = {}
    currentProcessingByEquipment.value = {}
  }
}

function onTomorrowToggle() {
  if (showTomorrow.value) {
    showYesterday.value = false
    planDateStr.value = addDays(businessToday(), 1)
  } else {
    planDateStr.value = businessToday()
  }
  loadPlan()
}

function onYesterdayToggle() {
  if (showYesterday.value) {
    showTomorrow.value = false
    planDateStr.value = addDays(businessToday(), -1)
  } else {
    planDateStr.value = businessToday()
  }
  loadPlan()
}

// ──────────────────────────────
// 保存（作業記録 + 必要に応じてLineBacklog加算）
// ──────────────────────────────
async function save() {
  if (!canSave.value) return
  const item = selectedItem.value
  try {
    const res = await api.brakeLineActuals.saveRecord({
      line_id:               item.line_id,
      process_id:            item.process_id,
      product_id:            item.product_id,
      product_code:          item.product_code,
      equipment_id:          selectedEquipmentId.value,
      plan_date:             businessToday(),
      operator:              operator.value,
      operator_action:       selectedAction.value,
      operator_action_reason: actionReason.value,
      qty:                   requiresQty.value ? inputQty.value : 0,
      sequence_no:           item.sequence_no,
    })
    const data = res.data
    // 作業状態を更新
    const equipmentId = data.equipment || selectedEquipmentId.value
    const stateKey = workStateKey(item, equipmentId)
    workStateMap.value = {
      ...workStateMap.value,
      [stateKey]: data.operator_action,
    }
    // START/RESUME の場合は開始者を記録、それ以外は削除
    if (data.operator_action === 'START' || data.operator_action === 'RESUME') {
      workOperatorMap.value = { ...workOperatorMap.value, [stateKey]: data.operator || operator.value }
    } else {
      const next = { ...workOperatorMap.value }
      delete next[stateKey]
      workOperatorMap.value = next
    }
    // END の場合は LineBacklog の実績数も更新
    if (data.operator_action === 'END' && data.backlog) {
      item.actual_qty = data.backlog.actual_qty
      item.backlog_id = data.backlog.backlog_id
      currentActualQty.value = data.backlog.actual_qty
    }
    const shouldPrintByAction = data.operator_action === 'END' || data.operator_action === 'PAUSE'
    const printQty = Number(inputQty.value || 0)
    if (printAutoEnabled.value && shouldPrintByAction && printQty > 0) {
      await printLabel(item, printQty)
    }
    updateCurrentProcessingState(
      data.operator_action,
      equipmentId,
      data.equipment_code || '',
      data.equipment_name || '',
      data.product_code || item.product_code || '',
      item.process_id,
    )
    // 仕損登録（数量 > 0 かつ理由選択時）
    if ((scrapQty.value ?? 0) > 0 && scrapReason.value) {
      await saveScrap(item)
    }

    const wasEquipmentTroublePause = (
      data.operator_action === 'PAUSE' &&
      actionReason.value === t('brakeInput.pauseReason.equipmentTrouble')
    )

    inputQty.value = null
    actionReason.value = ''
    scrapQty.value = null
    scrapReason.value = ''
    // END / TEMP_END の場合はフォームをリセット
    if (data.operator_action === 'END' || data.operator_action === 'TEMP_END') {
      selectedItem.value = null
      selectedEquipmentId.value = ''
      selectedAction.value = ''
    } else {
      syncSelectedAction()
    }

    const label = actionLabels.value[data.operator_action] || data.operator_action
    if (data.operator_action === 'END' && data.backlog) {
      showToast(t('brakeInput.toast.recordedWithQty', { action: label, qty: data.backlog.actual_qty }))
    } else {
      showToast(t('brakeInput.toast.recorded', { action: label }))
    }

    // 設備トラブルで中断した場合は設備状態入力画面へ遷移
    if (wasEquipmentTroublePause) {
      await nextTick()
      router.push({ path: '/production/mobile-process-input', query: { process_id: item.process_id } })
      return
    }

    nextTick(() => qtyInputRef.value?.focus())
  } catch (e) {
    showToast(e?.response?.data?.detail || t('brakeInput.error.saveFailed'), 'error')
  }
}

async function saveScrap(item) {
  try {
    await api.processRealtime.create({
      process_id: item.process_id,
      record_type: 'SCRAP',
      qty: scrapQty.value,
      operator_name: operator.value,
      ...(item.product_id ? { product_id: item.product_id } : { product_code: item.product_code }),
      event_data: {
        reason: scrapReason.value,
        disposition_status: 'REJECTED',
        is_production_recorded: false,
        relation_type: 'own_process',
      },
    })
  } catch (e) {
    showToast(e?.response?.data?.detail || '仕損登録に失敗しました', 'error')
  }
}

function updateCurrentProcessingState(actionValue, equipmentId, equipmentCode, equipmentName, productCode, processId) {
  const action = String(actionValue || '').toUpperCase()
  const equipmentKey = buildEquipmentKey(equipmentId)
  if (!action || !equipmentKey) return

  if (action === 'START' || action === 'RESUME') {
    currentProcessingByEquipment.value = {
      ...currentProcessingByEquipment.value,
      [equipmentKey]: {
        equipmentLabel: buildEquipmentLabel(equipmentId, equipmentCode, equipmentName),
        productCode: String(productCode || '').trim(),
        processId: processId ?? '',
      },
    }
    return
  }

  if (action === 'END' || action === 'PAUSE' || action === 'TEMP_END') {
    const next = { ...currentProcessingByEquipment.value }
    delete next[equipmentKey]
    currentProcessingByEquipment.value = next
  }
}

function syncSelectedAction() {
  const opts = operatorActionOptions.value
  if (!opts.length) {
    selectedAction.value = ''
    return
  }
  if (!opts.some((opt) => opt.value === selectedAction.value)) {
    selectedAction.value = opts[0].value
  }
}


// ──────────────────────────────
// 新規/追加モーダル
// ──────────────────────────────
async function openAddModal() {
  addType.value = 'extra'
  addProductId.value = ''
  addProductCodeManual.value = ''
  addProcessId.value = selectedProcessId.value || (processes.value[0]?.id ?? '')
  addEquipmentId.value = ''
  addError.value = ''
  showAddModal.value = true
  await Promise.all([fetchBrakeLineProducts(), fetchAddEquipments()])
}

async function onModalProcessChange() {
  await Promise.all([fetchBrakeLineProducts(), fetchAddEquipments()])
}

async function fetchBrakeLineProducts() {
  try {
    const res = await api.brakeLineActuals.getProducts(addProcessId.value, planDateStr.value)
    brakeLineProducts.value = res.data || []
    if (addProductId.value && !brakeLineProducts.value.find(p => isSameId(p.id, addProductId.value))) {
      addProductId.value = ''
    }
  } catch {
    brakeLineProducts.value = []
  }
}

async function fetchAddEquipments() {
  try {
    const res = await api.brakeLineActuals.getEquipments(addProcessId.value)
    addEquipments.value = res.data || []
    if (addEquipmentId.value && !addEquipments.value.find(e => isSameId(e.id, addEquipmentId.value))) {
      addEquipmentId.value = ''
    }
  } catch {
    addEquipments.value = []
  }
}

function closeAddModal() {
  showAddModal.value = false
}

function onAddProductSelect() {
  addError.value = ''
}

const canConfirmAdd = computed(() => {
  if (!addProcessId.value || !addEquipmentId.value) return false
  if (addType.value === 'extra') return !!addProductId.value
  if (addType.value === 'new') return addProductCodeManual.value.trim().length > 0
  return false
})

async function confirmAdd() {
  addError.value = ''
  const procObj = processes.value.find(p => isSameId(p.id, addProcessId.value))
  const lineObj = lines.value[0]  // ブレーキラインは通常1ライン

  if (!lineObj) {
    addError.value = t('brakeInput.error.noLine')
    return
  }

  let newItem
  if (addType.value === 'extra') {
    const prod = brakeLineProducts.value.find(p => isSameId(p.id, addProductId.value))
    if (!prod) { addError.value = t('brakeInput.error.productNotFound'); return }

    // 同じ品番・工程が既にリストにある場合はスキップ（設備違いは同一行で管理）
    const alreadyExists = allItems.value.some(
      i => isSameId(i.product_id, prod.id) && isSameId(i.process_id, addProcessId.value)
    )
    if (alreadyExists) {
      addError.value = t('brakeInput.error.alreadyExists')
      return
    }

    newItem = {
      product_id: prod.id,
      product_code: prod.product_code,
      product_name: prod.product_name,
      line_id: lineObj.id,
      line_code: lineObj.line_code,
      line_name: lineObj.line_name,
      process_id: procObj?.id ?? addProcessId.value,
      process_code: procObj?.process_code ?? '',
      process_name: procObj?.process_name ?? '',
      equipment_id: addEquipmentId.value,
      laser_qty: 0,
      plan_qty: 0,
      actual_qty: 0,
      backlog_id: null,
      sequence_no: 1,
      is_manual: true,
    }
  } else {
    // 新規: DB未登録品番を手入力
    const code = addProductCodeManual.value.trim()
    // マスタに存在する品番は新規不可（追加から選択すること）
    try {
      const res = await api.products.getProducts({ product_code: code, page_size: 1 })
      const results = res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
      const found = results.length > 0
      if (found) {
        addError.value = t('brakeInput.error.productInMaster')
        return
      }
    } catch {
      // 照会失敗時はスルー（登録を止めない）
    }
    newItem = {
      product_id: null,
      product_code: code,
      product_name: t('brakeInput.newProductName'),
      line_id: lineObj.id,
      line_code: lineObj.line_code,
      line_name: lineObj.line_name,
      process_id: procObj?.id ?? addProcessId.value,
      process_code: procObj?.process_code ?? '',
      process_name: procObj?.process_name ?? '',
      equipment_id: addEquipmentId.value,
      laser_qty: 0,
      plan_qty: 0,
      actual_qty: 0,
      backlog_id: null,
      sequence_no: 1,
      is_manual: true,
    }
  }

  allItems.value.push(newItem)
  if (!isSameId(selectedProcessId.value, newItem.process_id)) {
    selectedProcessId.value = newItem.process_id
    await onProcessChange()
  } else {
    currentPage.value = 1
  }
  showAddModal.value = false
  // 追加したアイテムをすぐ選択
  await selectItem(newItem)
  selectedEquipmentId.value = newItem.equipment_id || ''
  syncSelectedAction()
  showToast(t('brakeInput.toast.added'))
}

// ──────────────────────────────
// ページネーション
// ──────────────────────────────
function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }
function goFirstPage() { currentPage.value = 1 }
function goLastPage() { currentPage.value = totalPages.value }

// ──────────────────────────────
// トースト
// ──────────────────────────────
let toastTimer = null
function showToast(message, type = 'success') {
  toast.value = { show: true, message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}
</script>

<style scoped>
/* ═══════════════════════════════
   ベース
═══════════════════════════════ */
.brake-line-input {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100%;
  background: #f0f2f5;
  font-size: 14px;
  position: relative;
  overflow: hidden;
}

/* ═══════════════════════════════
   ヘッダー
═══════════════════════════════ */
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
.btn-scrap-nav {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #c0714f;
  background: #fff;
  color: #c0714f;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}
.btn-scrap-nav:hover { background: #fff3ef; }

.page-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
  color: #333;
  white-space: nowrap;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}
.header-label { font-size: 12px; color: #666; white-space: nowrap; }
.process-select, .date-input {
  height: 30px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
}
.process-select { min-width: 180px; }
.date-input { width: 136px; }
.laser-date-label { font-size: 12px; color: #888; white-space: nowrap; }
.header-processing {
  flex: 1 1 360px;
  min-width: 280px;
  max-width: 100%;
  height: 30px;
  display: flex;
  align-items: center;
  margin-left: 4px;
  border: 1px solid #d9ebff;
  background: #ecf5ff;
  border-radius: 6px;
  color: #1e5da8;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  padding: 0 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.processing-chip {
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.processing-chip:hover {
  color: #0d3a7a;
}
.header-processing.empty {
  border-color: #e4e7ed;
  background: #f7f8fa;
  color: #8a94a6;
}

/* ═══════════════════════════════
   4列レイアウト
═══════════════════════════════ */
.four-col-layout {
  display: grid;
  grid-template-columns: 1.5fr 1.5fr 3.5fr 3.5fr;
  grid-template-areas: "controls list form photo";
  flex: 1;
  overflow: hidden;
  gap: 0;
}

/* ── 共通カラムスタイル ── */
.col-controls,
.col-list,
.col-form,
.col-photo {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0; /* grid アイテムが grid 高さを超えて伸びるのを防ぐ */
  background: #fff;
  border-right: 1px solid #e0e0e0;
}
.col-controls { grid-area: controls; }
.col-list { grid-area: list; }
.col-form { grid-area: form; }
.col-photo { grid-area: photo; }
.col-photo { border-right: none; }

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  letter-spacing: .5px;
  padding: 8px 12px 4px;
}

/* ═══════════════════════════════
   列①: コントロール
═══════════════════════════════ */
.col-controls { background: #fafafa; }

.filter-area {
  padding: 4px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.toggle-input { display: none; }
.toggle-track {
  width: 34px;
  height: 18px;
  background: #ccc;
  border-radius: 9px;
  position: relative;
  transition: background .2s;
  flex-shrink: 0;
}
.toggle-track::after {
  content: '';
  position: absolute;
  width: 14px;
  height: 14px;
  background: #fff;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: left .2s;
  box-shadow: 0 1px 3px rgba(0,0,0,.3);
}
.toggle-track.on { background: #4e7cbf; }
.toggle-track.on::after { left: 18px; }
.toggle-label { font-size: 12px; color: #444; flex: 1; }

.operator-area { padding: 4px 12px 8px; }
.operator-input {
  width: 100%;
  height: 28px;
  padding: 0 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  box-sizing: border-box;
}
.print-setting-area {
  padding: 4px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.add-btn-area { padding: 8px 12px; }
.btn-add-new {
  width: 100%;
  height: 32px;
  border: 1px dashed #4e7cbf;
  background: #f0f4ff;
  color: #4e7cbf;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}
.btn-add-new:hover { background: #dce8ff; }

.hint-box {
  margin: 8px 12px;
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 6px;
  padding: 10px 10px;
  font-size: 11px;
  color: #7a6200;
  line-height: 1.7;
}

/* ═══════════════════════════════
   列②: 製品リスト
═══════════════════════════════ */
.list-header {
  padding: 6px 12px;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
}
.list-count { font-size: 12px; color: #888; }

.plan-list {
  flex: 1;
  overflow-y: auto;
}
.loading-list { display: flex; align-items: center; justify-content: center; }

.plan-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background .1s;
}
.plan-item:hover { background: #f5f8ff; }
.plan-item.selected { background: #e3ecff; border-left: 3px solid #4e7cbf; padding-left: 7px; }
.plan-item.done { opacity: 0.6; }
.plan-item.manual { border-left: 3px solid #e67e22; padding-left: 7px; }

.item-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.item-info { flex: 1; min-width: 0; }
.item-code { font-size: 12px; font-weight: 600; color: #222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-sub { font-size: 10px; color: #999; }
.done-badge { font-size: 10px; color: #2e9688; font-weight: 700; white-space: nowrap; }
.manual-badge {
  font-size: 9px;
  background: #fde8d0;
  color: #e67e22;
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
}

.empty-list, .loading-text {
  padding: 32px 12px;
  text-align: center;
  color: #bbb;
  font-size: 13px;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 6px 10px;
  border-top: 1px solid #eee;
  background: #fafafa;
  font-size: 11px;
}
.page-btn {
  width: 22px;
  height: 22px;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 3px;
  cursor: pointer;
  font-size: 10px;
}
.page-btn:disabled { opacity: 0.35; cursor: default; }
.page-info { flex: 1; text-align: center; color: #666; }

/* ═══════════════════════════════
   列③: 登録フォーム
═══════════════════════════════ */
.no-selection {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #bbb;
  font-size: 13px;
}

.form-area {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
}

.product-header {
  margin-bottom: 16px;
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.product-code-large { font-size: 18px; font-weight: 700; color: #222; }
.product-name { font-size: 13px; color: #666; }
.process-badge {
  font-size: 11px;
  background: #4e7cbf;
  color: #fff;
  padding: 2px 8px;
  border-radius: 10px;
}

.stats-and-actions {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.stats-and-actions .current-actual {
  margin-bottom: 0;
}
.stats-and-actions .action-btns-area {
  flex: 1;
  min-width: 160px;
}

.current-actual {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.stat-block {
  background: #f8f8f8;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 8px 14px;
  text-align: center;
  min-width: 72px;
}
.stat-label { display: block; font-size: 10px; color: #999; margin-bottom: 2px; }
.stat-value { font-size: 20px; font-weight: 700; }
.stat-value.plan { color: #4e7cbf; }
.stat-value.actual { color: #2e9688; }
.stat-value.remain { color: #e67e22; }
.stat-value.remain.over { color: #2e9688; }

/* ── 作業アクションボタン ── */
.action-btns-area {
  margin-bottom: 16px;
}
.op-action-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.op-action-btn {
  min-width: 72px;
  height: 36px;
  padding: 0 12px;
  border: 2px solid #ccc;
  background: #fafafa;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  transition: background .15s, border-color .15s, color .15s;
}
.op-action-btn:hover { filter: brightness(.93); }
/* 開始 */
.op-action-btn.action-start              { border-color: #2e9688; color: #2e9688; }
.op-action-btn.action-start.active       { background: #2e9688; color: #fff; }
/* 終了 */
.op-action-btn.action-end                { border-color: #4e7cbf; color: #4e7cbf; }
.op-action-btn.action-end.active         { background: #4e7cbf; color: #fff; }
/* 中断 */
.op-action-btn.action-pause              { border-color: #e67e22; color: #e67e22; }
.op-action-btn.action-pause.active       { background: #e67e22; color: #fff; }
/* 再開 */
.op-action-btn.action-resume             { border-color: #8e44ad; color: #8e44ad; }
.op-action-btn.action-resume.active      { background: #8e44ad; color: #fff; }
/* 一時終了 */
.op-action-btn.action-temp_end           { border-color: #c0392b; color: #c0392b; }
.op-action-btn.action-temp_end.active    { background: #c0392b; color: #fff; }

/* 理由セレクト */
.reason-area { margin-bottom: 12px; }
.reason-select {
  width: 100%;
  height: 34px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
  box-sizing: border-box;
  margin-top: 4px;
}

/* ── 使用設備選択 ── */
.started-by-area {
  margin-bottom: 12px;
  padding: 6px 10px;
  background: #fff8e1;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 13px;
}
.started-by-label {
  color: #92400e;
  font-weight: 600;
}
.started-by-name {
  color: #1e293b;
  margin-left: 4px;
}
.equip-select-area {
  margin-bottom: 16px;
}
.equip-label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}
.required-mark {
  color: #c0392b;
  font-weight: 700;
  margin-left: 2px;
}
.equip-btns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.equip-btns-modal {
  gap: 8px;
}
.equip-btn {
  min-width: 70px;
  padding: 6px 10px;
  border: 1px solid #ccc;
  background: #fafafa;
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  color: #444;
  text-align: center;
  line-height: 1.5;
  transition: background .15s, border-color .15s;
}
.equip-btn:hover { background: #e8f0fe; border-color: #4e7cbf; }
.equip-btn.active {
  background: #4e7cbf;
  color: #fff;
  border-color: #4e7cbf;
  box-shadow: 0 2px 6px rgba(78,124,191,.35);
}
.equip-btn-name {
  font-size: 10px;
  font-weight: 400;
  opacity: .85;
}
.equip-empty {
  font-size: 12px;
  color: #bbb;
  padding: 6px 0;
}

.qty-input-area { margin-bottom: 8px; }
.qty-row { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.qty-col { display: flex; flex-direction: column; }
.qty-input-narrow { width: 90px !important; }
.scrap-col { flex: 1; min-width: 200px; }
.scrap-label { color: #c0714f !important; font-weight: 600; }
.scrap-inline { display: flex; gap: 8px; align-items: center; }
.scrap-reason-select {
  height: 48px;
  flex: 1;
  min-width: 120px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
}
.qty-label { display: block; font-size: 12px; color: #666; margin-bottom: 6px; }
.qty-input {
  width: 160px;
  height: 48px;
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  border: 2px solid #4e7cbf;
  border-radius: 6px;
  padding: 0 8px;
}
.qty-input:focus { outline: none; border-color: #2e5ca8; box-shadow: 0 0 0 3px rgba(78,124,191,.2); }

.action-bar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  padding: 10px 20px;
  padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid #e8e8e8;
  background: #fafafa;
  flex-shrink: 0;
  position: sticky;
  bottom: 0;
  z-index: 12;
}
.btn-cancel {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #666;
}
.btn-cancel:hover { background: #f0f0f0; }

.btn-save {
  height: 34px;
  padding: 0 18px;
  border: none;
  background: #4e7cbf;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn-save:disabled { background: #c8c8c8; cursor: default; }
.btn-save:not(:disabled):hover { background: #3a6aad; }

.btn-change {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #4e7cbf;
  background: #fff;
  color: #4e7cbf;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.btn-change:disabled { border-color: #ccc; color: #ccc; cursor: default; }
.btn-change:not(:disabled):hover { background: #e8f0fe; }

/* ═══════════════════════════════
   列④: 製品写真（将来用）
═══════════════════════════════ */
.col-photo { background: #fafafa; }

.photo-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  border: 2px dashed #e0e0e0;
  margin: 8px;
  border-radius: 8px;
  background: #fff;
}
.photo-product-code { font-size: 12px; font-weight: 600; color: #555; text-align: center; }
.photo-icon { font-size: 40px; line-height: 1; }
.photo-icon.muted { opacity: .3; }
.photo-label { font-size: 11px; color: #aaa; text-align: center; line-height: 1.6; }
.photo-label.muted { opacity: .7; }

/* ═══════════════════════════════
   モーダル（全面オーバーレイ）
═══════════════════════════════ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  width: 340px;
  box-shadow: 0 8px 32px rgba(0,0,0,.25);
}
.modal-title { font-size: 16px; font-weight: 700; margin: 0 0 8px; }
.modal-desc { font-size: 13px; color: #666; margin: 0 0 16px; }
.modal-field { margin-bottom: 14px; }
.modal-field label { display: block; font-size: 12px; color: #666; margin-bottom: 5px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }

.add-type-btns { display: flex; gap: 8px; }
.type-btn {
  flex: 1;
  height: 36px;
  border: 1px solid #ccc;
  background: #fafafa;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.type-btn.active { background: #4e7cbf; color: #fff; border-color: #4e7cbf; }

.modal-select, .modal-input {
  width: 100%;
  height: 34px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
  box-sizing: border-box;
}
.modal-hint { font-size: 11px; color: #aaa; margin-top: 4px; }
.modal-error { color: #c0392b; font-size: 12px; margin-top: 8px; }
.selected-product-name { font-size: 12px; color: #555; margin-top: 4px; }

/* ═══════════════════════════════
   トースト
═══════════════════════════════ */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  z-index: 300;
  box-shadow: 0 4px 16px rgba(0,0,0,.2);
}
.toast.success { background: #2e9688; color: #fff; }
.toast.error   { background: #c0392b; color: #fff; }
.toast-enter-active, .toast-leave-active { transition: opacity .3s, transform .3s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(12px); }

@media (max-width: 1366px) {
  .four-col-layout {
    grid-template-columns: 180px 250px 1fr;
    grid-template-areas: "controls list form";
  }

  .col-photo {
    display: none;
  }
}

@media (max-width: 1024px) {
  .four-col-layout {
    grid-template-columns: 240px minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    grid-template-areas:
      "controls form"
      "list form";
    overflow: hidden;
  }

  .col-controls,
  .col-list,
  .col-form {
    border-right: 1px solid #e0e0e0;
  }

  .col-controls {
    overflow-y: auto;
  }

  .col-list {
    max-height: none;
    min-height: 0;
  }

  .col-form {
    min-height: 0;
  }

  .op-action-btn {
    min-width: 88px;
    height: 42px;
    font-size: 14px;
  }

  .equip-btn {
    min-width: 82px;
    font-size: 12px;
    padding: 8px 10px;
  }

  .qty-input {
    width: 190px;
    height: 56px;
    font-size: 28px;
  }

  .btn-cancel,
  .btn-save,
  .btn-change {
    height: 40px;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .header {
    padding: 8px 10px;
    gap: 8px;
  }

  .header-controls {
    width: 100%;
  }

  .header-processing {
    margin-left: 0;
    min-width: 100%;
    height: 28px;
    font-size: 12px;
    padding: 0 8px;
  }

  .four-col-layout {
    grid-template-columns: 1fr;
    grid-template-areas:
      "controls"
      "list"
      "form";
  }

  .col-controls,
  .col-list,
  .col-form {
    border-right: none;
    border-bottom: 1px solid #e0e0e0;
  }

  .col-list {
    max-height: 36vh;
  }

  .form-area {
    padding: 14px;
  }

  .action-bar { z-index: 20; }
}
</style>
