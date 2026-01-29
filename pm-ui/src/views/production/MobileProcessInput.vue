<template>
  <div class="mobile-input" :class="pageModeClass">
    <div class="mobile-header">
      <h2>{{ pageTitle }}</h2>
      <div class="header-info">
        <span class="date">{{ currentDate }}</span>
      </div>
    </div>

    <div class="section inline-row dual-row">
      <div class="inline-group">
        <label class="label-required inline-label">{{ t('processInput.line') }}</label>
        <select v-model="selectedLineId" @change="onLineChange" class="input-large flex-input">
          <option value="">{{ t('processInput.selectLine') }}</option>
          <option v-for="line in lines" :key="line.id" :value="String(line.id)">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
      </div>

      <div class="inline-group">
        <label class="label-required inline-label">{{ t('processInput.process') }}</label>
        <select
          v-model="selectedProcessId"
          @change="onProcessChange"
          class="input-large flex-input"
          :disabled="!selectedLineId"
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
            class="type-btn"
            :class="{ active: record.record_type === type.value }"
          >
            {{ type.label }}
          </button>
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
      v-if="(record.record_type === 'PRODUCTION' || record.record_type === 'SCRAP') && currentProductList.length"
      class="planned-buttons"
    >
      <span class="planned-label">{{ t('processInput.plannedToday') }}</span>
      <div v-if="record.record_type === 'SCRAP'" class="planned-cards">
        <div
          v-for="p in displayProductList"
          :key="`${p.plan_date}-${p.product}-${p.process}`"
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
      <div v-else class="planned-list">
        <button
          v-for="p in displayProductList"
          :key="`${p.plan_date}-${p.product}-${p.process}`"
          class="btn-planned"
          :class="{ active: record.product_id === p.product }"
          type="button"
          @click="selectPlannedProduct(p)"
        >
          {{ p.product_code || t('processInput.unsetProductCode') }}
          <span v-if="p.plan_qty != null" class="plan-qty">
            {{ t('processInput.planQtyBadge', { qty: formatNumber(p.plan_qty) }) }}
          </span>
        </button>
      </div>
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
                :key="`${p.plan_date}-${p.product_code}`"
                :value="p.product"
              >
                {{ p.product_code }} - {{ p.product_name || '' }}
                {{ t('processInput.planQtyParen', { qty: formatNumber(p.plan_qty || 0) }) }}
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
      </div>
    </div>

    <div
      v-if="record.record_type === 'PRODUCTION' || record.record_type === 'SCRAP'"
      class="form-section"
      :class="formModeClass"
    >
      <div class="section inline-row qty-row">
        <div class="inline-group qty-group">
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
            min="1"
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

      <div class="quick-btns" v-if="quickQtyPresets.length">
        <button
          v-for="preset in quickQtyPresets"
          :key="preset"
          @click="record.qty = preset"
          class="btn-quick"
        >
          {{ preset }}
        </button>
      </div>

      <div v-if="isScrapRecord" class="section">
        <label class="label-required">{{ t('processInput.disposition') }}</label>
        <select v-model="record.disposition_status" class="input-large">
          <option value="">{{ t('processInput.selectDisposition') }}</option>
          <option v-for="opt in scrapDispositionOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <div class="hint">{{ t('processInput.dispositionHint') }}</div>
      </div>

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
        <label>{{ t('processInput.remarks') }}</label>
        <textarea
          v-model="record.remarks"
          rows="3"
          :placeholder="t('processInput.remarksPlaceholder')"
          class="textarea-normal"
        ></textarea>
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
            @click="record.equipment_state = state.value"
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

    <div v-if="selectedProcessId && recentRecords.length" class="recent-section">
      <h3 class="section-title">{{ t('processInput.recentRecords') }}</h3>
      <div class="record-list">
        <div v-for="rec in recentRecords" :key="rec.id" class="record-item">
          <div class="record-time">{{ formatTime(rec.timestamp) }}</div>
          <div class="record-type">
            <div class="record-type__label">{{ rec.record_type_display }}</div>
            <div v-if="rec.product_code" class="record-type__product">{{ rec.product_code }}</div>
          </div>
          <div class="record-qty" v-if="rec.qty > 0">{{ rec.qty }}</div>
          <div class="record-state" v-if="rec.equipment_state">
            {{ rec.equipment_state_display }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import { t, getLocaleCode } from '@/i18n'

const route = useRoute()
const localeCode = computed(() => getLocaleCode())

const processes = ref([])
const lines = ref([])
const selectedLineId = ref('')
const selectedProcessId = ref('')
const recentRecords = ref([])
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
const productionProducts = ref([])
const scrapProducts = ref([])
const scrapRelationFilter = ref('')
const scrapSearchText = ref('')
const defaultProductId = ref(null)
const productImageMap = ref({})

const record = ref({
  record_type: '',
  product_id: '',
  product_code: '',
  qty: null,
  reason: '',
  reason_detail: '',
  disposition_status: '',
  equipment_state: '',
  batch_no: '',
  operator_name: '',
  remarks: '',
})

const recordTypeOptions = computed(() => [
  { value: 'PRODUCTION', label: t('processInput.recordType.production') },
  { value: 'EQUIPMENT_STATE', label: t('processInput.recordType.equipment') },
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

const scrapRelationOptions = computed(() => [
  { value: 'coproduct_parent', label: t('processInput.scrapFilter.coproductParent') },
  { value: 'coproduct_child', label: t('processInput.scrapFilter.coproductChild') },
  { value: 'intermediate', label: t('processInput.scrapFilter.intermediate') },
  { value: 'purchased', label: t('processInput.scrapFilter.purchased') },
  { value: 'output_product', label: t('processInput.scrapFilter.outputProduct') },
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
  ScrapRecordInput: 'processInput.pageTitleScrap',
}

const pageTitle = computed(() => {
  const key = pageTitleKeyMap[route.name]
  if (key) return t(key)
  return route.meta?.pageTitle || t('processInput.pageTitleWork')
})

const filteredProcesses = computed(() => {
  if (!selectedLineId.value) return processes.value
  return processes.value.filter((p) => String(p.line) === String(selectedLineId.value))
})

const isScrapOnlyPage = computed(() => route.name === 'ScrapRecordInput')
const isScrapRecord = computed(() => record.value.record_type === 'SCRAP')

const equipmentStates = computed(() => [
  { value: 'RUNNING', label: t('processInput.equipmentState.running') },
  { value: 'IDLE', label: t('processInput.equipmentState.idle') },
  { value: 'SETUP', label: t('processInput.equipmentState.setup') },
  { value: 'MAINTENANCE', label: t('processInput.equipmentState.maintenance') },
  { value: 'BREAKDOWN', label: t('processInput.equipmentState.breakdown') },
  { value: 'STOPPED', label: t('processInput.equipmentState.stopped') },
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
  availableRecordTypes,
  () => {
    ensureDefaultRecordType()
  },
  { immediate: true }
)

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

const isScrapFilterActive = computed(() => {
  return !!scrapRelationFilter.value || !!(scrapSearchText.value || '').trim()
})

const filterScrapCandidates = (list) => {
  const items = Array.isArray(list) ? list : []
  const relation = scrapRelationFilter.value
  const query = (scrapSearchText.value || '').trim().toLowerCase()
  if (!relation && !query) return items
  return items.filter((p) => {
    if (!p) return false
    if (relation) {
      const type = p.relation_type || ''
      if (type !== relation) return false
    }
    if (query) {
      const code = (p.product_code || '').toLowerCase()
      const name = (p.product_name || '').toLowerCase()
      if (!code.includes(query) && !name.includes(query)) return false
    }
    return true
  })
}

const displayProductList = computed(() => {
  if (record.value.record_type === 'SCRAP') {
    return filterScrapCandidates(scrapProducts.value)
  }
  return currentProductList.value
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

const canSubmit = computed(() => {
  if (!selectedProcessId.value || !record.value.record_type) return false

  if (record.value.record_type === 'PRODUCTION' || record.value.record_type === 'SCRAP') {
    const hasProduct = !!record.value.product_id || !!(record.value.product_code || '').trim()
    if (!(record.value.qty > 0 && hasProduct)) return false
    if (record.value.record_type === 'SCRAP') {
      if (!record.value.reason) return false
      const detailText = (record.value.reason_detail || '').trim()
      if (record.value.reason === 'OTHER' && !detailText) return false
      if (!(record.value.operator_name || '').trim()) return false
      if (!(record.value.disposition_status || '').trim()) return false
    }
    return true
  }

  if (record.value.record_type === 'EQUIPMENT_STATE') {
    return !!record.value.equipment_state
  }

  return false
})

const resetForm = () => {
  record.value = {
    record_type: '',
    product_id: '',
    product_code: '',
    qty: null,
    reason: '',
    reason_detail: '',
    disposition_status: '',
    equipment_state: '',
    batch_no: '',
    operator_name: defaultOperatorName.value || '',
    remarks: '',
  }
  manualProduct.value = false
  scrapRelationFilter.value = ''
  scrapSearchText.value = ''
  ensureDefaultRecordType()
}

const onProcessChange = () => {
  const proc = processes.value.find((p) => String(p.id) === String(selectedProcessId.value))
  if (proc?.line) {
    selectedLineId.value = String(proc.line)
  }

  resetForm()
  manualProducts.value = []
  manualProductsLoaded.value = false
  manualProductsProcessId.value = null
  loadPlannedProducts()
  loadRecentRecords()
}

const onLineChange = () => {
  selectedProcessId.value = ''
  recentRecords.value = []
  productionProducts.value = []
  scrapProducts.value = []
  defaultProductId.value = null
  productImageMap.value = {}
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

const submitRecord = async () => {
  if (!canSubmit.value) return

  submitting.value = true
  try {
    const data = {
      process_id: selectedProcessId.value,
      record_type: record.value.record_type,
    }

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

    data.remarks = record.value.remarks

    if (record.value.record_type === 'SCRAP' && record.value.reason) {
      const eventData = {
        reason: record.value.reason,
        disposition_status: record.value.disposition_status || 'REJECTED',
      }
      if (record.value.reason === 'OTHER' && (record.value.reason_detail || '').trim()) {
        eventData.reason_detail = record.value.reason_detail.trim()
      }
      data.event_data = eventData
    }

    await api.processRealtime.create(data)

    alert(t('processInput.alert.saved'))
    resetForm()
    loadRecentRecords()
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
  } catch (error) {
    console.error('最近の記録取得エラー:', error)
  }
}


const buildCurrentTimePlanItems = async (lineId, processId) => {
  try {
    const targetDate = currentDateYmd.value
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: lineId,
      plan_date__gte: targetDate,
      plan_date__lte: targetDate,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    if (!Array.isArray(rawPlans) || !rawPlans.length) {
      return { items: [], hasPlan: false }
    }

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
        map.set(key, {
          plan_date: targetDate,
          product: productId,
          product_code: pp.output_product_code || plan.product_code || '',
          product_name: pp.output_product_name || plan.product_name || '',
          process: processId,
          plan_qty: pp.quantity ?? plan.plan_qty ?? 0,
        })
      })
    })
    return { items: Array.from(map.values()), hasPlan: true }
  } catch (e) {
    console.error('現在時間の計画取得エラー:', e)
    return { items: [], hasPlan: false }
  }
}

const loadPlannedProducts = async () => {
  if (!selectedProcessId.value) return

  productionProducts.value = []
  scrapProducts.value = []
  try {
    const process = processes.value.find(p => String(p.id) === String(selectedProcessId.value))
    const lineId = process?.line
    if (!lineId) return

    // 工程に紐づく「当日の予定製品」を優先的に取得（line-backlogs は process 単位で絞れる）
    const listRes = await api.lineBacklogs.getLineBacklogs({
      line: lineId,
      process: selectedProcessId.value,
      plan_date: currentDateYmd.value,
    })
    const listItems = listRes.data.results || listRes.data || []
    let tempProducts = []
    if (Array.isArray(listItems) && listItems.length > 0) {
      tempProducts = listItems
    } else {
      // まだ line-backlogs が計算されていない場合は pickup で生成（当日のみ）
      try {
        const pickupRes = await api.lineBacklogs.pickup({
          line_id: lineId,
          start_date: currentDateYmd.value,
          end_date: currentDateYmd.value,
        })
        const pickupItems = pickupRes.data.results || pickupRes.data || []
        tempProducts = (Array.isArray(pickupItems) ? pickupItems : []).filter(
          (it) => String(it.process) === String(selectedProcessId.value) && String(it.plan_date) === String(currentDateYmd.value)
        )
      } catch (e) {
        console.error('本日の計画ピックアップエラー:', e)
        tempProducts = []
      }
    }

    // 可能なら現在時刻に該当する計画のみを表示する
    const activeResult = await buildCurrentTimePlanItems(lineId, selectedProcessId.value)
    if (activeResult.hasPlan) {
      tempProducts = activeResult.items
    }

    // 連産品の子品番を除外（生産記録用）
    const filteredForProduction = await filterCoproductChildrenFromList(tempProducts)

    // 生産記録用リストを作成
    productionProducts.value = [...filteredForProduction]

    // 仕損品記録用リストを作成: related-products APIから工程関連製品を追加
    await loadScrapProducts(selectedProcessId.value, filteredForProduction, lineId)

    if (productionProducts.value.length === 1 && productionProducts.value[0].product) {
      defaultProductId.value = productionProducts.value[0].product
    }

    if (!productionProducts.value.length && !scrapProducts.value.length) {
      loadManualProducts(selectedProcessId.value)
    }
  } catch (error) {
    console.error('本日の計画取得エラー:', error)
  }
}

const loadScrapProducts = async (processId, baseProducts, fallbackLineId = null) => {
  try {
    // 基本リスト（生産記録と同じ）から開始
    const scrapMap = new Map()
    baseProducts.forEach((it) => {
      const key = `${it.product}_${it.process}`
      if (!scrapMap.has(key)) scrapMap.set(key, it)
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

    const relationTypeMap = new Map()
    relatedProducts.forEach((prod) => {
      relationTypeMap.set(String(prod.id), prod.relation_type)
      const key = `${prod.id}_${processId}`
      if (!scrapMap.has(key)) {
        // line-backlog形式に変換して追加
        scrapMap.set(key, {
          product: prod.id,
          product_code: prod.product_code,
          product_name: prod.product_name,
          process: processId,
          plan_qty: 0,
          plan_date: null,
          relation_type: prod.relation_type, // 'coproduct_parent', 'coproduct_child', 'intermediate', 'purchased'
        })
      }
    })

    scrapMap.forEach((item) => {
      if (!item || item.relation_type || item.product == null) return
      const rt = relationTypeMap.get(String(item.product))
      if (rt) {
        item.relation_type = rt
      }
    })

    scrapProducts.value = Array.from(scrapMap.values())

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
      const res = await api.bomService.getBomTree(parentId)
      const tree = res.data
      if (!tree || !tree.is_coproduct) continue
      for (const ch of tree.children || []) {
        if (ch?.product_id) childIds.add(ch.product_id)
      }
    } catch (error) {
      console.error('連産品BOM取得エラー:', error)
    }
  }

  if (childIds.size === 0) return candidates
  return candidates.filter((it) => !childIds.has(it.product))
}

const loadProductImages = async (idSet) => {
  try {
    if (!idSet || idSet.size === 0) {
      productImageMap.value = {}
      return
    }
    // 1) まとめて取得
    const all = await api.products.getAllProducts({ page_size: 5000 })
    const map = {}
    all.forEach((p) => {
      const pidNum = p.id
      const pidStr = String(p.id)
      if (idSet.has(pidNum) || idSet.has(pidStr)) {
        const val = p.image_url || ''
        map[pidNum] = val
        map[pidStr] = val
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
          }
        } catch (err) {
          console.warn('製品詳細取得失敗 (画像用):', mid, err)
        }
      }
    }

    productImageMap.value = map
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
  record.value.product_id = p.product || ''
  record.value.product_code = p.product_code || ''
  manualProduct.value = false
  if (record.value.record_type === 'PRODUCTION') {
    const qtyNum = Number(p.plan_qty)
    if (!Number.isNaN(qtyNum)) {
      record.value.qty = qtyNum
    }
  }
}

watch(
  () => route.name,
  () => {
    selectedLineId.value = ''
    selectedProcessId.value = ''
    recentRecords.value = []
    productionProducts.value = []
    scrapProducts.value = []
    defaultProductId.value = null
    productImageMap.value = {}
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
  () => record.value.record_type,
  (type) => {
    if (!type) return
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
      if (plan && plan.plan_qty != null && !Number.isNaN(Number(plan.plan_qty))) {
        record.value.qty = Number(plan.plan_qty)
      }
    }
  },
  { immediate: true }
)

watch(
  () => [record.value.product_id, record.value.product_code],
  () => {
    ensureScrapDefaults()
  }
)

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

onMounted(() => {
  loadLines()
  loadProcesses()
  ensureAuth()
})
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

.header-info .date {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.header-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #64748b;
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
  font-size: 24px !important;
  height: 40px;
  line-height: 40px;
  padding: 0 8px;
  text-align: center;
  font-weight: 700;
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
.planned-label {
  font-size: 12px;
  color: #475569;
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
}
.btn-planned.active {
  border-color: #4a7ae5;
  background: #eff6ff;
  color: #1f2a44;
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
.product-toggle {
  margin-top: 0;
}
.toggle-link {
  padding: 0;
}
.inline-link {
  margin-top: 0;
}
</style>
