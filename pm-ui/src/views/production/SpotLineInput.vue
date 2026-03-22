<template>
  <div class="spot-line-input">
    <!-- ヘッダー -->
    <div class="header">
      <h2 class="page-title">スポットライン実績入力</h2>
      <button class="btn-scrap-nav" @click="router.push('/production/scrap-record')">仕損記録</button>
      <button class="btn-inspection-nav" @click="openEquipmentInspection">設備点検</button>
      <div class="header-controls">
        <label class="header-label">日付</label>
        <input type="date" v-model="planDateStr" class="date-input" @change="loadPlan" />
        <div class="header-processing" :class="{ empty: !currentProcessingMessages.length }">
          <template v-if="currentProcessingMessages.length">
            <span
              v-for="(msg, i) in currentProcessingMessages"
              :key="msg.equipmentKey"
              class="processing-chip"
              @click="jumpToProcessingItem(msg)"
            >{{ msg.label }}<template v-if="i < currentProcessingMessages.length - 1"> / </template></span>
          </template>
          <template v-else>加工中なし</template>
        </div>
      </div>
    </div>

    <!-- 4列レイアウト -->
    <div class="four-col-layout">

      <!-- 列①: コントロール -->
      <div class="col-controls">
        <div class="section-title">表示設定</div>
        <div class="filter-area">
          <label class="filter-item">
            <span class="toggle-label">加工済み表示</span>
            <input type="checkbox" v-model="showDone" class="toggle-input" />
            <span class="toggle-track" :class="{ on: showDone }"></span>
          </label>
          <label class="filter-item">
            <span class="toggle-label">明日の計画</span>
            <input type="checkbox" v-model="showTomorrow" class="toggle-input" @change="onTomorrowToggle" />
            <span class="toggle-track" :class="{ on: showTomorrow }"></span>
          </label>
          <label class="filter-item">
            <span class="toggle-label">前日表示</span>
            <input type="checkbox" v-model="showYesterday" class="toggle-input" @change="onYesterdayToggle" />
            <span class="toggle-track" :class="{ on: showYesterday }"></span>
          </label>
        </div>

        <div class="section-title" style="margin-top:12px">作業者</div>
        <div class="operator-area">
          <input type="text" v-model="operator" class="operator-input" placeholder="作業者名を入力" />
        </div>

        <div class="section-title" style="margin-top:12px">印刷設定</div>
        <div class="print-setting-area">
          <label class="filter-item">
            <span class="toggle-label">自動印刷</span>
            <input type="checkbox" v-model="printAutoEnabled" class="toggle-input" @change="savePrintSettings" />
            <span class="toggle-track" :class="{ on: printAutoEnabled }"></span>
          </label>
          <input type="text" v-model.trim="printDeviceId" class="operator-input" placeholder="端末ID" @change="savePrintSettings" />
          <input type="text" v-model.trim="printPrinterName" class="operator-input" placeholder="プリンタ名（表示用）" @change="savePrintSettings" />
        </div>

        <div class="add-btn-area">
          <button class="btn-add-new" @click="openAddModal">＋ 新規／追加</button>
        </div>

        <div class="hint-box">
          <p>・新規加工（DB未登録品）は<br>　「＋新規/追加 → 新規」</p>
          <p style="margin-top:8px">・付属外加工は<br>　「＋新規/追加 → 追加」</p>
        </div>
      </div>

      <!-- 列②: 製品リスト -->
      <div class="col-list">
        <div class="list-header">
          <span class="list-count">{{ filteredItems.length }}件</span>
        </div>
        <div class="list-filter">
          <input
            v-model.trim="productCodeFilter"
            class="list-filter-input"
            placeholder="部番検索"
            @input="currentPage = 1"
          />
        </div>

        <div class="plan-list" v-if="!loading">
          <div
            v-for="item in pagedItems"
            :key="itemKey(item)"
            class="plan-item"
            :class="{ selected: isSelected(item), done: isDone(item), manual: item.is_manual }"
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
            <div v-if="item.is_manual" class="manual-badge">{{ item.product_id ? '追加' : '新規' }}</div>
          </div>
          <div v-if="filteredItems.length === 0" class="empty-list">対象品番がありません</div>
        </div>
        <div class="plan-list loading-list" v-else>
          <div class="loading-text">読み込み中...</div>
        </div>

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
          <div class="no-selection"><span>品番を選択してください</span></div>
        </template>

        <template v-else>
          <div class="form-area">
            <div class="product-header">
              <div class="product-code-large">{{ selectedItem.product_code }}</div>
              <div class="product-name">{{ selectedItem.product_name }}</div>
              <div class="process-badge">{{ selectedItem.process_name }}</div>
            </div>

            <div class="stats-and-actions">
              <div class="current-actual">
                <div class="stat-block">
                  <span class="stat-label">計画数</span>
                  <span class="stat-value plan">{{ selectedItem.plan_qty }}</span>
                </div>
                <div class="stat-block">
                  <span class="stat-label">実績数</span>
                  <span class="stat-value actual">{{ currentActualQty }}</span>
                </div>
                <div class="stat-block">
                  <span class="stat-label">残り</span>
                  <span class="stat-value remain" :class="{ over: currentActualQty >= selectedItem.plan_qty }">
                    {{ Math.max(0, selectedItem.plan_qty - currentActualQty) }}
                  </span>
                </div>
              </div>

              <div class="action-btns-area">
                <label class="equip-label">アクション <span class="required-mark">*</span></label>
                <div class="op-action-btns">
                  <button
                    v-for="act in operatorActionOptions"
                    :key="act.value"
                    class="op-action-btn"
                    :class="[`action-${act.value.toLowerCase()}`, { active: selectedAction === act.value }]"
                    @click="selectAction(act.value)"
                  >{{ act.label }}</button>
                </div>
                <div v-if="selectedItem && selectedEquipmentIds.length === 0" class="equip-empty">設備を先に選択してください</div>
              </div>
            </div>

            <div v-if="currentWorkState === 'STARTED' && currentOperator" class="started-by-area">
              <span class="started-by-label">開始者：</span>
              <span class="started-by-name">{{ currentOperator }}</span>
            </div>

            <div class="equip-select-area">
              <label class="equip-label">使用設備 <span class="required-mark">*</span></label>
              <div class="equip-btns">
                <button
                  v-for="eq in equipments"
                  :key="eq.id"
                  class="equip-btn"
                  :class="{ active: selectedEquipmentIds.includes(eq.id) }"
                  @click="selectedEquipmentIds.includes(eq.id) ? selectedEquipmentIds = selectedEquipmentIds.filter(id => id !== eq.id) : selectedEquipmentIds.push(eq.id)"
                >{{ eq.equipment_code }}<br><span class="equip-btn-name">{{ eq.equipment_name }}</span></button>
              </div>
              <div v-if="equipments.length === 0" class="equip-empty">設備が登録されていません</div>
            </div>

            <div v-if="requiresQty" class="qty-input-area">
              <div class="qty-row">
                <div class="qty-col">
                  <label class="qty-label">加工数</label>
                  <input
                    ref="qtyInputRef"
                    type="number"
                    v-model.number="inputQty"
                    :min="selectedAction === 'PAUSE' ? 0 : 1"
                    step="1"
                    inputmode="numeric"
                    class="qty-input qty-input-narrow"
                    placeholder="数量"
                    @keyup.enter="save"
                  />
                </div>
                <div class="qty-col scrap-col">
                  <label class="qty-label scrap-label">仕損記録</label>
                  <div class="scrap-inline">
                    <input
                      type="number"
                      v-model.number="scrapQty"
                      min="0"
                      step="1"
                      inputmode="numeric"
                      class="qty-input qty-input-narrow"
                      placeholder="数量"
                    />
                    <select v-model="scrapReason" class="scrap-reason-select">
                      <option value="">理由を選択</option>
                      <option v-for="r in SCRAP_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="requiresReason" class="reason-area">
              <label class="qty-label">
                {{ selectedAction === 'TEMP_END' ? '一時終了理由' : '中断理由' }}
                <span class="required-mark">*</span>
              </label>
              <select v-model="actionReason" class="reason-select">
                <option value="">理由を選択</option>
                <option v-for="r in reasonOptions" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>

            <div class="action-bar">
              <button class="btn-save" :disabled="!canSave" @click="save">保存</button>
              <button class="btn-cancel" @click="cancel">キャンセル</button>
            </div>
          </div>
        </template>
      </div>

      <!-- 列④: 製品写真 -->
      <div class="col-photo">
        <div class="section-title">製品写真</div>
        <div class="photo-placeholder">
          <template v-if="selectedItem">
            <div class="photo-product-code">{{ selectedItem.product_code }}</div>
            <img v-if="photoPreviewUrl" :src="photoPreviewUrl" class="photo-preview" alt="製品写真" />
            <div v-else class="photo-icon">📷</div>
            <div class="photo-actions">
              <button class="btn-save photo-save-btn" :disabled="!canCapturePhoto" @click="openCamera">
                {{ photoUploading ? '保存中...' : '撮影して保存' }}
              </button>
              <input
                ref="photoInputRef"
                type="file"
                accept="image/*"
                capture="environment"
                class="photo-file-input"
                @change="onPhotoSelected"
              />
            </div>
            <div class="photo-label">{{ photoPreviewUrl ? '保存済み写真' : '未登録です。撮影して保存できます' }}</div>
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
        <h3 class="modal-title">新規／追加加工</h3>

        <div class="modal-field">
          <label>種別</label>
          <div class="add-type-btns">
            <button class="type-btn" :class="{ active: addType === 'extra' }" @click="addType = 'extra'">追加（計画外品番）</button>
            <button class="type-btn" :class="{ active: addType === 'new' }" @click="addType = 'new'">新規（DB未登録品）</button>
          </div>
        </div>

        <div v-if="addType === 'extra'" class="modal-field">
          <label>品番</label>
          <select v-model="addProductId" class="modal-select" @change="onAddProductSelect">
            <option value="">品番を選択</option>
            <option v-for="p in spotLineProducts" :key="p.id" :value="p.id">
              {{ p.product_code }}　{{ p.product_name }}
            </option>
          </select>
          <div v-if="addProductId" class="selected-product-name">
            {{ spotLineProducts.find(p => p.id === addProductId)?.product_name }}
          </div>
        </div>

        <div v-if="addType === 'new'" class="modal-field">
          <label>品番（手入力）</label>
          <input
            type="text"
            v-model="addProductCodeManual"
            class="modal-input"
            placeholder="品番を入力"
            @input="addProductCodeManual = addProductCodeManual.toUpperCase()"
          />
          <div class="modal-hint">マスタ未登録品番のみ入力可能です</div>
        </div>

        <div class="modal-field">
          <label>工程</label>
          <select v-model="addProcessId" class="modal-select" disabled style="opacity:0.6;cursor:not-allowed;">
            <option v-for="p in processes" :key="p.id" :value="p.id">
              {{ p.process_code }} {{ p.process_name }}
            </option>
          </select>
        </div>

        <div class="modal-field">
          <label>設備 <span class="required-mark">*</span></label>
          <div class="equip-btns equip-btns-modal">
            <button
              v-for="eq in addEquipments"
              :key="eq.id"
              class="equip-btn"
              :class="{ active: addEquipmentId === eq.id }"
              @click="addEquipmentId = eq.id"
            >{{ eq.equipment_code }}<br><span class="equip-btn-name">{{ eq.equipment_name }}</span></button>
          </div>
          <div v-if="addEquipments.length === 0" class="equip-empty">設備が登録されていません</div>
        </div>

        <div v-if="addError" class="modal-error">{{ addError }}</div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="closeAddModal">キャンセル</button>
          <button class="btn-save" @click="confirmAdd" :disabled="!canConfirmAdd">確定</button>
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

const SCRAP_REASONS = [
  { value: '500:その他',          label: '500: その他' },
  { value: '501:精度調整/試し曲げ', label: '501: 精度調整/試し曲げ' },
  { value: '502:精度不良',         label: '502: 精度不良' },
  { value: '503:変形/キズ',        label: '503: 変形/キズ' },
]

const PAUSE_REASONS = ['設備トラブル', '治具トラブル', '品質トラブル', '材料待ち', '段取り', 'リーダー待ち', '3S活動', '改善活動', '品番間違い', 'その他']
const TEMP_END_REASONS = ['設備なし', '治具なし', '品番切替', '材料不足', 'その他']

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

const showDone = ref(false)
const showTomorrow = ref(false)
const showYesterday = ref(false)

// タブレット横向き想定: 1ページ8件でリスト内スクロールなし
const PAGE_SIZE = 8
const currentPage = ref(1)
const productCodeFilter = ref('')

const equipments = ref([])
const selectedEquipmentIds = ref([])

const selectedAction = ref('')
const actionReason = ref('')
const workStateMap = ref({})
const workOperatorMap = ref({})
const currentProcessingByEquipment = ref({})

const NOT_STARTED_ACTIONS = ['START']
const STARTED_ACTIONS     = ['END', 'PAUSE']
const PAUSED_ACTIONS      = ['RESUME', 'TEMP_END']
const TEMP_ENDED_ACTIONS  = ['RESUME']
const ACTION_LABELS = { START: '開始', END: '終了', PAUSE: '中断', RESUME: '再開', TEMP_END: '一時終了' }

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
  if (!selectedItem.value || selectedEquipmentIds.value.length === 0) return 'NOT_STARTED'
  // 最初の選択設備の状態で判定（複数設備は同じアクションで操作するため）
  const last = workStateMap.value[workStateKey(selectedItem.value, selectedEquipmentIds.value[0])]
  if (last === 'PAUSE')                      return 'PAUSED'
  if (last === 'TEMP_END')                   return 'TEMP_ENDED'
  if (last === 'START' || last === 'RESUME') return 'STARTED'
  return 'NOT_STARTED'
})

const currentOperator = computed(() => {
  if (!selectedItem.value) return ''
  if (selectedEquipmentIds.value.length > 0) {
    return workOperatorMap.value[workStateKey(selectedItem.value, selectedEquipmentIds.value[0])] || ''
  }
  const productKey = selectedItem.value.product_id || selectedItem.value.product_code
  const prefix = `${selectedItem.value.process_id}-${productKey}-`
  for (const [k, op] of Object.entries(workOperatorMap.value)) {
    if (k.startsWith(prefix)) return op
  }
  return ''
})

const operatorActionOptions = computed(() => {
  const toOpts = (actions) => actions.map(v => ({ value: v, label: ACTION_LABELS[v] }))
  if (!selectedItem.value || selectedEquipmentIds.value.length === 0) return []
  if (currentWorkState.value === 'STARTED')    return toOpts(STARTED_ACTIONS)
  if (currentWorkState.value === 'PAUSED')     return toOpts(PAUSED_ACTIONS)
  if (currentWorkState.value === 'TEMP_ENDED') return toOpts(TEMP_ENDED_ACTIONS)
  return toOpts(NOT_STARTED_ACTIONS)
})

const requiresQty    = computed(() => selectedAction.value === 'END' || selectedAction.value === 'PAUSE')
const requiresReason = computed(() => selectedAction.value === 'PAUSE' || selectedAction.value === 'TEMP_END')
const reasonOptions  = computed(() => selectedAction.value === 'TEMP_END' ? TEMP_END_REASONS : PAUSE_REASONS)

const currentProcessingMessages = computed(() =>
  Object.entries(currentProcessingByEquipment.value || {})
    .map(([equipmentKey, row]) => {
      const equipmentLabel = String(row?.equipmentLabel || '').trim()
      const productCode = String(row?.productCode || '').trim()
      if (!equipmentLabel) return null
      return {
        equipmentKey,
        equipmentId: row?.equipment_id ?? null,
        productCode,
        label: productCode
          ? `現在${equipmentLabel}は${productCode}加工中`
          : `現在${equipmentLabel}は加工中`,
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.label.localeCompare(b.label))
)

// 新規/追加モーダル
const showAddModal = ref(false)
const addType = ref('extra')
const addProductId = ref('')
const addProductCodeManual = ref('')
const addProcessId = ref('')
const addEquipmentId = ref('')
const addError = ref('')
const spotLineProducts = ref([])
const addEquipments = ref([])

const toast = ref({ show: false, message: '', type: 'success' })
const PRINT_SETTINGS_KEY = 'spot_line_print_settings_v1'

const qtyInputRef = ref(null)
const photoInputRef = ref(null)
const scrapQty = ref(null)
const scrapReason = ref('')
const photoPreviewUrl = ref('')
const photoUploading = ref(false)
const canCapturePhoto = computed(() => !!selectedItem.value?.product_id && !photoUploading.value)

watch(
  () => operatorActionOptions.value.map((item) => item.value).join('|'),
  () => { syncSelectedAction() },
  { immediate: true }
)

watch(
  () => selectedAction.value,
  (action) => {
    const key = String(action || '').toUpperCase()
    if (!(key === 'PAUSE' || key === 'TEMP_END')) actionReason.value = ''
    if (key !== 'END') inputQty.value = null
  }
)

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
    if (!raw) { printDeviceId.value = inferDeviceId(); return }
    const parsed = JSON.parse(raw)
    printAutoEnabled.value = !!parsed.autoEnabled
    printDeviceId.value = String(parsed.deviceId || '').trim() || inferDeviceId()
    printPrinterName.value = String(parsed.printerName || '').trim()
  } catch {
    printDeviceId.value = inferDeviceId()
  }
}

function savePrintSettings() {
  window.localStorage.setItem(PRINT_SETTINGS_KEY, JSON.stringify({
    autoEnabled: !!printAutoEnabled.value,
    deviceId: String(printDeviceId.value || '').trim(),
    printerName: String(printPrinterName.value || '').trim(),
  }))
}

async function buildPrintHtml(item, qty) {
  const productCode = String(item?.product_code || '')
  const productName = String(item?.product_name || '')
  const processName = String(item?.process_name || '')
  const operatorName = String(operator.value || '')
  const processDate = planDateStr.value || ''

  let qrDataUrl = ''
  try {
    qrDataUrl = await QRCode.toDataURL(productCode, { margin: 1, width: 120 })
  } catch { qrDataUrl = '' }

  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>加工品ラベル</title>
  <style>
    @page { size: 60mm 85mm; margin: 0; }
    html, body { width: 60mm; height: 85mm; margin: 0; padding: 0; }
    body { font-family: "Yu Gothic", "Meiryo", sans-serif; box-sizing: border-box; }
    .label { width: 60mm; height: 85mm; padding: 2.5mm; padding-top: 15mm; border: 1px solid #000; box-sizing: border-box; display: flex; flex-direction: column; gap: 0; }
    .title { font-size: 8pt; font-weight: 700; text-align: center; border-bottom: 0.5px solid #000; padding-bottom: 1mm; margin-bottom: 1mm; }
    .code { font-size: 16pt; font-weight: 900; letter-spacing: .2mm; line-height: 1.1; }
    .name { font-size: 11pt; line-height: 1.2; margin-bottom: 1mm; }
    .row { display: flex; align-items: baseline; font-size: 11pt; line-height: 1.35; gap: 1.5mm; }
    .row .lbl { color: #555; flex-shrink: 0; font-size: 7.5pt; }
    .row .val { font-weight: 700; }
    .row-lg .val { font-size: 16pt; font-weight: 900; }
    .qty-row { display: flex; align-items: baseline; gap: 1.5mm; margin-top: 1mm; }
    .qty-lbl { font-size: 7.5pt; color: #555; flex-shrink: 0; }
    .qty-val { font-size: 16pt; font-weight: 900; line-height: 1; }
    .qr-area { display: flex; justify-content: flex-end; margin-top: 1.5mm; }
    .qr-area img { width: 16mm; height: 16mm; display: block; }
  </style>
</head>
<body>
  <div class="label">
    <div class="title">加工品ラベル</div>
    <div class="code">${productCode}</div>
    <div class="name">${productName}</div>
    <div class="row"><span class="lbl">加工工程</span><span class="val">${processName}</span></div>
    <div class="row row-lg"><span class="lbl">加工日</span><span class="val">${processDate}</span></div>
    <div class="row"><span class="lbl">加工者</span><span class="val">${operatorName}</span></div>
    <div class="qty-row">
      <span class="qty-lbl">加工数</span>
      <span class="qty-val">${qty}</span>
    </div>
    <div class="qr-area">${qrDataUrl ? `<img src="${qrDataUrl}" alt="QR" />` : ''}</div>
  </div>
</body>
</html>`
}

async function printLabel(item, qty) {
  const win = window.open('', '_blank')
  if (!win) { showToast('印刷ウィンドウを開けませんでした', 'error'); return }
  const html = await buildPrintHtml(item, qty)
  win.document.open()
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => { win.print(); win.onafterprint = () => win.close() }, 200)
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
    const res = await api.spotLineActuals.getPlan(planDateStr.value)
    const data = res.data
    processes.value = data.processes || []
    lines.value = data.lines || []
    allItems.value = data.items || []
    if (!selectedProcessId.value && processes.value.length > 0) {
      selectedProcessId.value = processes.value[0].id
    }
    if (selectedProcessId.value) {
      await Promise.all([fetchEquipments(), fetchWorkStates()])
    } else {
      workStateMap.value = {}
      currentProcessingByEquipment.value = {}
    }
  } catch (e) {
    showToast(e?.response?.data?.detail || '計画の読み込みに失敗しました', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchWorkStates() {
  try {
    const res = await api.spotLineActuals.getRecordStates(planDateStr.value, selectedProcessId.value)
    const payload = res.data || {}
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
  if (!showDone.value) items = items.filter(item => !isDone(item))
  const keyword = String(productCodeFilter.value || '').trim().toUpperCase()
  if (keyword) items = items.filter((item) => String(item.product_code || '').toUpperCase().includes(keyword))
  return items
})

const pagedItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredItems.value.slice(start, start + PAGE_SIZE)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / PAGE_SIZE)))
const pageStart = computed(() => filteredItems.value.length === 0 ? 0 : (currentPage.value - 1) * PAGE_SIZE + 1)
const pageEnd = computed(() => Math.min(currentPage.value * PAGE_SIZE, filteredItems.value.length))

// ──────────────────────────────
// 計算プロパティ
// ──────────────────────────────
const isDone = (item) => {
  if (item.actual_qty <= 0) return false
  const hasPause = equipments.value.concat([{ id: null }]).some(eq => {
    const st = workStateMap.value[workStateKey(item, eq.id)]
    return st === 'PAUSE' || st === 'TEMP_END'
  })
  return !hasPause
}
const isSelected = (item) => selectedItem.value && itemKey(item) === itemKey(selectedItem.value)
const itemKey = (item) => `${item.line_id}-${item.process_id}-${item.product_id || `code:${item.product_code || ''}`}`
const canSave = computed(() => {
  if (!selectedItem.value || selectedEquipmentIds.value.length === 0 || !selectedAction.value) return false
  if (selectedAction.value === 'END' && !(inputQty.value > 0)) return false
  if (selectedAction.value === 'PAUSE' && !(inputQty.value >= 0)) return false
  if (requiresReason.value && !actionReason.value) return false
  return true
})

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
  photoPreviewUrl.value = ''
  if (item?.equipment_id) selectedEquipmentIds.value = [item.equipment_id]
  if (item?.image_url) {
    photoPreviewUrl.value = item.image_url
  } else if (item?.product_id) {
    await loadProductPhoto(item.product_id)
  }
  syncSelectedAction()
  nextTick(() => qtyInputRef.value?.focus())
}

function selectAction(action) {
  selectedAction.value = action
  actionReason.value = ''
  if (action === 'END') nextTick(() => qtyInputRef.value?.focus())
}

async function fetchEquipments() {
  try {
    const res = await api.spotLineActuals.getEquipments()
    equipments.value = res.data || []
    if (selectedEquipmentIds.value.length > 0) {
      selectedEquipmentIds.value = selectedEquipmentIds.value.filter(
        id => equipments.value.some((eq) => isSameId(eq.id, id))
      )
    }
  } catch {
    equipments.value = []
    selectedEquipmentIds.value = []
  }
}

function cancel() {
  selectedItem.value = null
  inputQty.value = null
  selectedAction.value = ''
  actionReason.value = ''
  scrapQty.value = null
  scrapReason.value = ''
  photoPreviewUrl.value = ''
}

function openCamera() {
  if (!canCapturePhoto.value) { showToast('マスタ登録品番のみ写真を保存できます', 'error'); return }
  photoInputRef.value?.click()
}

async function loadProductPhoto(productId) {
  try {
    const res = await api.products.getProduct(productId)
    photoPreviewUrl.value = String(res?.data?.image_url || '').trim()
  } catch {
    photoPreviewUrl.value = ''
  }
}

async function onPhotoSelected(event) {
  const file = event?.target?.files?.[0]
  if (!file || !selectedItem.value?.product_id) return
  let objectUrl = null
  try {
    objectUrl = URL.createObjectURL(file)
    photoPreviewUrl.value = objectUrl
  } catch { /* プレビューなしで続行 */ }

  const formData = new FormData()
  formData.append('file', file)
  photoUploading.value = true
  try {
    const res = await api.products.uploadProductImage(selectedItem.value.product_id, formData)
    const imageUrl = String(res?.data?.image_url || '').trim()
    selectedItem.value = { ...selectedItem.value, image_url: imageUrl }
    if (!objectUrl) photoPreviewUrl.value = imageUrl
    showToast('製品写真を保存しました')
  } catch (e) {
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    photoPreviewUrl.value = selectedItem.value?.image_url || ''
    showToast(e?.response?.data?.detail || '製品写真の保存に失敗しました', 'error')
  } finally {
    photoUploading.value = false
    if (event?.target) event.target.value = ''
  }
}

function jumpToProcessingItem(msg) {
  const item = allItems.value.find(
    i => i.product_code === msg.productCode && isSameId(i.process_id, selectedProcessId.value)
  )
  if (!item) return
  selectedItem.value = item
  if (msg.equipmentId) selectedEquipmentIds.value = [msg.equipmentId]
  selectedAction.value = ''
  inputQty.value = null
  actionReason.value = ''
  syncSelectedAction()
  const idx = filteredItems.value.findIndex(i => isSameId(i.product_id || i.product_code, item.product_id || item.product_code))
  if (idx >= 0) currentPage.value = Math.floor(idx / PAGE_SIZE) + 1
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
// 保存
// ──────────────────────────────
async function save() {
  if (!canSave.value) return
  const item = selectedItem.value
  try {
    let lastData = null
    // 複数設備対応: 設備ごとにレコードを作成
    // 数量加算（actual_qty への反映）は最初の設備のみ行い、二重カウントを防ぐ
    for (let i = 0; i < selectedEquipmentIds.value.length; i++) {
      const eqId = selectedEquipmentIds.value[i]
      const isFirst = i === 0
      const res = await api.spotLineActuals.saveRecord({
        line_id:               item.line_id,
        process_id:            item.process_id,
        product_id:            item.product_id,
        product_code:          item.product_code,
        equipment_id:          eqId,
        plan_date:             planDateStr.value,
        operator:              operator.value,
        operator_action:       selectedAction.value,
        operator_action_reason: actionReason.value,
        qty:                   (requiresQty.value && isFirst) ? inputQty.value : 0,
        // 2台目以降はqty検証・actual_qty加算をスキップ（二重カウント防止）
        skip_qty_update:       !isFirst,
        sequence_no:           item.sequence_no,
      })
      const data = res.data
      const equipmentId = data.equipment || eqId
      const stateKey = workStateKey(item, equipmentId)
      workStateMap.value = { ...workStateMap.value, [stateKey]: data.operator_action }
      if (data.operator_action === 'START' || data.operator_action === 'RESUME') {
        workOperatorMap.value = { ...workOperatorMap.value, [stateKey]: data.operator || operator.value }
      } else {
        const next = { ...workOperatorMap.value }
        delete next[stateKey]
        workOperatorMap.value = next
      }
      updateCurrentProcessingState(data.operator_action, equipmentId, data.equipment_code || '', data.equipment_name || '', data.product_code || item.product_code || '', item.process_id)
      if (isFirst) lastData = data
    }
    const data = lastData
    if (data.operator_action === 'END' && data.backlog) {
      item.actual_qty = data.backlog.actual_qty
      currentActualQty.value = data.backlog.actual_qty
    }
    const shouldPrint = data.operator_action === 'END' || data.operator_action === 'PAUSE'
    const printQty = Number(inputQty.value || 0)
    if (printAutoEnabled.value && shouldPrint && printQty > 0) {
      await printLabel(item, printQty)
    }
    if ((scrapQty.value ?? 0) > 0 && scrapReason.value) {
      await saveScrap(item)
    }
    inputQty.value = null
    actionReason.value = ''
    scrapQty.value = null
    scrapReason.value = ''
    if (data.operator_action === 'END' || data.operator_action === 'TEMP_END') {
      selectedItem.value = null
      selectedEquipmentIds.value = []
      selectedAction.value = ''
    } else {
      syncSelectedAction()
    }
    // 複数設備の楽観的更新がズレる場合に備え、サーバー状態で加工中表示を確定同期する
    await fetchWorkStates()
    const label = ACTION_LABELS[data.operator_action] || data.operator_action
    if (data.operator_action === 'END' && data.backlog) {
      showToast(`${label}（累計${data.backlog.actual_qty}個）`)
    } else {
      showToast(`${label}を記録しました`)
    }
    nextTick(() => qtyInputRef.value?.focus())
  } catch (e) {
    showToast(e?.response?.data?.detail || '保存に失敗しました', 'error')
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
  if (!opts.length) { selectedAction.value = ''; return }
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
  await Promise.all([fetchSpotLineProducts(), fetchAddEquipments()])
}

async function fetchSpotLineProducts() {
  try {
    const res = await api.spotLineActuals.getProducts(addProcessId.value, planDateStr.value)
    spotLineProducts.value = res.data || []
    if (addProductId.value && !spotLineProducts.value.find(p => isSameId(p.id, addProductId.value))) {
      addProductId.value = ''
    }
  } catch {
    spotLineProducts.value = []
  }
}

async function fetchAddEquipments() {
  try {
    const res = await api.spotLineActuals.getEquipments()
    addEquipments.value = res.data || []
    if (addEquipmentId.value && !addEquipments.value.find(e => isSameId(e.id, addEquipmentId.value))) {
      addEquipmentId.value = ''
    }
  } catch {
    addEquipments.value = []
  }
}

function closeAddModal() { showAddModal.value = false }
function onAddProductSelect() { addError.value = '' }

const canConfirmAdd = computed(() => {
  if (!addProcessId.value || !addEquipmentId.value) return false
  if (addType.value === 'extra') return !!addProductId.value
  if (addType.value === 'new') return addProductCodeManual.value.trim().length > 0
  return false
})

async function confirmAdd() {
  addError.value = ''
  const procObj = processes.value.find(p => isSameId(p.id, addProcessId.value))
  const lineObj = lines.value[0]
  if (!lineObj) { addError.value = 'ラインが見つかりません'; return }

  let newItem
  if (addType.value === 'extra') {
    const prod = spotLineProducts.value.find(p => isSameId(p.id, addProductId.value))
    if (!prod) { addError.value = '品番が見つかりません'; return }
    const alreadyExists = allItems.value.some(
      i => isSameId(i.product_id, prod.id) && isSameId(i.process_id, addProcessId.value)
    )
    if (alreadyExists) { addError.value = 'この品番は既にリストにあります'; return }
    newItem = {
      product_id: prod.id, product_code: prod.product_code, product_name: prod.product_name,
      line_id: lineObj.id, line_code: lineObj.line_code, line_name: lineObj.line_name,
      process_id: procObj?.id ?? addProcessId.value,
      process_code: procObj?.process_code ?? '', process_name: procObj?.process_name ?? '',
      equipment_id: addEquipmentId.value, plan_qty: 0, actual_qty: 0,
      backlog_id: null, sequence_no: 1, is_manual: true,
    }
  } else {
    const code = addProductCodeManual.value.trim()
    try {
      const res = await api.products.getProducts({ product_code: code, page_size: 1 })
      const results = res.data?.results ?? (Array.isArray(res.data) ? res.data : [])
      if (results.length > 0) { addError.value = 'この品番はマスタに存在します。追加から選択してください'; return }
    } catch { /* スルー */ }
    newItem = {
      product_id: null, product_code: code, product_name: '（新規）',
      line_id: lineObj.id, line_code: lineObj.line_code, line_name: lineObj.line_name,
      process_id: procObj?.id ?? addProcessId.value,
      process_code: procObj?.process_code ?? '', process_name: procObj?.process_name ?? '',
      equipment_id: addEquipmentId.value, plan_qty: 0, actual_qty: 0,
      backlog_id: null, sequence_no: 1, is_manual: true,
    }
  }

  allItems.value.push(newItem)
  if (!isSameId(selectedProcessId.value, newItem.process_id)) {
    selectedProcessId.value = newItem.process_id
  } else {
    currentPage.value = 1
  }
  showAddModal.value = false
  await selectItem(newItem)
  selectedEquipmentIds.value = newItem.equipment_id ? [newItem.equipment_id] : []
  syncSelectedAction()
  showToast('追加しました')
}

// ──────────────────────────────
// ページネーション
// ──────────────────────────────
function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }
function goFirstPage() { currentPage.value = 1 }
function goLastPage() { currentPage.value = totalPages.value }

function openEquipmentInspection() {
  const processId = selectedProcessId.value || undefined
  const lineId = lines.value[0]?.id || undefined
  router.push({
    path: '/quality/equipment-inspection/operation',
    query: {
      ...(processId ? { process_id: String(processId) } : {}),
      ...(lineId ? { line_id: String(lineId) } : {}),
    },
  })
}

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
.spot-line-input {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100%;
  background: #f0f2f5;
  font-size: 14px;
  position: relative;
  overflow: hidden;
}
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
.page-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  white-space: nowrap;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex: 1;
}
.header-label {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
}
.date-input {
  height: 30px;
  padding: 0 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
}
.header-processing {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 10px;
  border-radius: 14px;
  background: #fff3e0;
  font-size: 12px;
  color: #e65100;
  flex-wrap: wrap;
}
.header-processing.empty {
  background: #f5f5f5;
  color: #999;
}
.processing-chip {
  cursor: pointer;
  text-decoration: underline;
  white-space: nowrap;
}

/* 4列レイアウト */
.four-col-layout {
  display: grid;
  grid-template-columns: 180px 260px 1fr 200px;
  flex: 1;
  overflow: hidden;
  gap: 0;
}
.col-controls, .col-form, .col-photo {
  overflow-y: auto;
  padding: 12px;
  border-right: 1px solid #dde1e8;
}
/* リスト列はスクロールなし（タブレット横向き、8件/ページで画面内に収める） */
.col-list {
  overflow-y: visible;
  padding: 12px;
  border-right: 1px solid #dde1e8;
}
.col-photo { border-right: none; }
.section-title {
  font-size: 11px;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}
.filter-area { display: flex; flex-direction: column; gap: 8px; }
.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.toggle-label { font-size: 13px; flex: 1; }
.toggle-input { display: none; }
.toggle-track {
  width: 36px; height: 20px;
  border-radius: 10px;
  background: #ccc;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}
.toggle-track::after {
  content: '';
  position: absolute;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #fff;
  top: 2px; left: 2px;
  transition: left 0.2s;
}
.toggle-track.on { background: #4e7cbf; }
.toggle-track.on::after { left: 18px; }
.operator-area { margin-bottom: 4px; }
.operator-input {
  width: 100%;
  height: 32px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  box-sizing: border-box;
  margin-bottom: 4px;
}
.print-setting-area { display: flex; flex-direction: column; gap: 6px; }
.add-btn-area { margin-top: 16px; }
.btn-add-new {
  width: 100%;
  height: 36px;
  border: 2px dashed #4e7cbf;
  background: #fff;
  color: #4e7cbf;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.hint-box {
  margin-top: 16px;
  padding: 10px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.6;
  color: #666;
}
/* リスト */
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.list-count { font-size: 12px; color: #888; }
.list-filter { margin-bottom: 8px; }
.list-filter-input {
  width: 100%;
  height: 32px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  box-sizing: border-box;
}
.plan-list { display: flex; flex-direction: column; gap: 4px; }
.plan-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 8px;
  background: #fff;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.15s;
  position: relative;
}
.plan-item:hover { border-color: #b0c4e8; }
.plan-item.selected { border-color: #4e7cbf; background: #e8f0fb; }
.plan-item.done { opacity: 0.5; }
.item-avatar {
  width: 28px; height: 28px;
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
.item-code { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-sub { display: none; }
.done-badge {
  font-size: 11px;
  background: #e8f5e9;
  color: #388e3c;
  border-radius: 4px;
  padding: 2px 6px;
  font-weight: 700;
}
.manual-badge {
  font-size: 10px;
  background: #fff3e0;
  color: #f57c00;
  border-radius: 4px;
  padding: 2px 5px;
}
.empty-list { text-align: center; padding: 24px 0; color: #aaa; font-size: 13px; }
.loading-list { opacity: 0.5; }
.loading-text { text-align: center; padding: 24px 0; color: #aaa; font-size: 13px; }
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 8px;
}
.page-btn {
  width: 28px; height: 28px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}
.page-btn:disabled { opacity: 0.4; cursor: default; }
.page-info { font-size: 12px; color: #666; padding: 0 4px; }

/* フォーム */
.no-selection {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aaa;
  font-size: 14px;
}
.form-area { display: flex; flex-direction: column; gap: 16px; }
.product-header { padding-bottom: 12px; border-bottom: 1px solid #e8e8e8; }
.product-code-large { font-size: 22px; font-weight: 900; letter-spacing: 0.5px; }
.product-name { font-size: 14px; color: #555; margin-top: 2px; }
.process-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  background: #e3ecfa;
  color: #3558a0;
  border-radius: 4px;
  font-size: 12px;
}
.stats-and-actions { display: flex; flex-direction: column; gap: 12px; }
.current-actual { display: flex; gap: 16px; }
.stat-block { text-align: center; }
.stat-label { display: block; font-size: 11px; color: #888; }
.stat-value { font-size: 22px; font-weight: 900; }
.stat-value.plan { color: #4e7cbf; }
.stat-value.actual { color: #2e9688; }
.stat-value.remain { color: #c0714f; }
.stat-value.remain.over { color: #388e3c; }
.action-btns-area { display: flex; flex-direction: column; gap: 6px; }
.equip-label { font-size: 12px; color: #555; }
.required-mark { color: #e53935; margin-left: 2px; }
.op-action-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.op-action-btn {
  height: 40px;
  padding: 0 16px;
  border: 2px solid #ccc;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.15s;
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
.started-by-area { font-size: 12px; color: #666; }
.started-by-label { margin-right: 4px; }
.started-by-name { font-weight: 700; }
.equip-select-area { display: flex; flex-direction: column; gap: 6px; }
.equip-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.equip-btn {
  min-width: 80px;
  padding: 8px 12px;
  border: 2px solid #ccc;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  transition: border-color 0.15s;
}
.equip-btn.active { border-color: #4e7cbf; background: #e8f0fb; }
.equip-btn-name { display: block; font-size: 10px; color: #888; font-weight: normal; }
.equip-empty { font-size: 12px; color: #aaa; }
.qty-input-area { display: flex; flex-direction: column; gap: 8px; }
.qty-row { display: flex; gap: 16px; flex-wrap: wrap; }
.qty-col { display: flex; flex-direction: column; gap: 4px; }
.qty-label { font-size: 12px; color: #555; }
.scrap-label { color: #c0714f; }
.qty-input {
  height: 44px;
  padding: 0 8px;
  border: 2px solid #ccc;
  border-radius: 6px;
  font-size: 20px;
  font-weight: 700;
  text-align: center;
}
.qty-input-narrow { width: 100px; }
.scrap-inline { display: flex; gap: 6px; align-items: center; }
.scrap-reason-select {
  height: 44px;
  padding: 0 6px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 12px;
}
.reason-area { display: flex; flex-direction: column; gap: 6px; }
.reason-select {
  height: 36px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
}
.action-bar { display: flex; gap: 8px; }
.btn-save {
  height: 44px;
  padding: 0 24px;
  background: #4e7cbf;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 700;
}
.btn-save:disabled { opacity: 0.4; cursor: default; }
.btn-cancel {
  height: 44px;
  padding: 0 16px;
  background: #fff;
  color: #666;
  border: 1px solid #ccc;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

/* 写真列 */
.photo-placeholder { display: flex; flex-direction: column; gap: 8px; align-items: center; }
.photo-product-code { font-size: 12px; font-weight: 700; color: #555; text-align: center; }
.photo-preview { width: 100%; max-width: 160px; border-radius: 8px; border: 1px solid #ddd; }
.photo-icon { font-size: 48px; opacity: 0.3; }
.photo-icon.muted { font-size: 32px; }
.photo-actions { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.photo-save-btn { width: 100%; height: 36px; font-size: 12px; }
.photo-file-input { display: none; }
.photo-label { font-size: 11px; color: #aaa; text-align: center; }
.photo-label.muted { font-size: 12px; }

/* モーダル */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 400px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 90vh;
  overflow-y: auto;
}
.modal-title { font-size: 16px; font-weight: 700; margin: 0; }
.modal-field { display: flex; flex-direction: column; gap: 6px; }
.modal-field label { font-size: 12px; color: #666; }
.modal-select, .modal-input {
  height: 36px;
  padding: 0 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
}
.modal-hint { font-size: 11px; color: #999; }
.modal-error { color: #e53935; font-size: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.add-type-btns { display: flex; gap: 8px; }
.type-btn {
  flex: 1;
  height: 36px;
  border: 2px solid #ccc;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.type-btn.active { border-color: #4e7cbf; background: #e8f0fb; color: #4e7cbf; font-weight: 700; }
.selected-product-name { font-size: 12px; color: #555; }
.equip-btns-modal { flex-wrap: wrap; }

/* トースト */
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  background: #323232;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  z-index: 300;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  white-space: nowrap;
}
.toast.error { background: #e53935; }
.toast-enter-active, .toast-leave-active { transition: opacity 0.3s; }
.toast-enter-from, .toast-leave-to { opacity: 0; }
</style>
