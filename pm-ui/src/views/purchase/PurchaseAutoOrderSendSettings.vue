<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">注文書自動送信設定</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="openNew">新規追加</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="loading" class="no-data">読み込み中...</div>
      <div v-else>
        <div class="truck-check-panel">
          <div class="truck-check-header">
            <h2>トラック積載判定</h2>
            <button class="btn-primary" :disabled="truckCheckLoading || !truckCheck.truck_id || !truckCheck.delivery_date" @click="runTruckLoadCheck">{{ truckCheckLoading ? '判定中...' : '判定実行' }}</button>
          </div>
          <div class="truck-check-form">
            <div class="form-group compact">
              <label>トラック</label>
              <select v-model="truckCheck.truck_id" @change="onTruckChange">
                <option value="">-- 選択 --</option>
                <option v-for="truck in truckCandidates" :key="truck.id" :value="truck.id">
                  {{ truck.supplier_code ? `${truck.supplier_code} / ` : '' }}{{ truck.name }}
                </option>
              </select>
            </div>
            <div class="form-group compact">
              <label>納期</label>
              <input v-model="truckCheck.delivery_date" type="date" />
            </div>
          </div>

          <div v-if="truckCheckResult" class="truck-check-result-area">
            <div class="truck-result-header">
              <span class="truck-result-name">{{ truckCheckResult.truck?.name || '-' }}</span>
              <span :class="['badge', truckCheckResult.can_fit ? 'badge-on' : 'badge-overload']">
                {{ truckCheckResult.can_fit ? '積載可' : '積載超過' }}
              </span>
              <span class="truck-result-occ">占有率: {{ truckCheckResult.occupancy_percent }}%</span>
              <span v-if="truckCheckResult.total_footprints" class="truck-result-occ">配置: {{ truckCheckResult.total_footprints - (truckCheckResult.overflow_count || 0) }}/{{ truckCheckResult.total_footprints }}枠</span>
              <span v-if="truckContainerSummaryText" class="truck-result-occ truck-result-summary">{{ truckContainerSummaryText }}</span>
              <span v-if="truckCheckResult.data_source" class="hint-text">（{{ truckCheckResult.data_source === 'proposal' ? '注文書' : '購買計画' }}）</span>
            </div>

            <div v-if="truckCheckResult.errors?.length" class="truck-result-errors">
              <span v-for="(err, i) in truckCheckResult.errors" :key="i">{{ err }}</span>
            </div>
            <div v-if="truckCheckResult.warnings?.length" class="truck-result-warnings">
              <span v-for="(w, i) in truckCheckResult.warnings" :key="i">{{ w }}</span>
            </div>
            <div v-if="truckCheckResult.invalid_items?.length" class="truck-result-warnings">
              <span v-for="(item, i) in truckCheckResult.invalid_items" :key="i">{{ item.product_code }}: {{ item.reason === 'container not configured' ? '容器未設定' : item.reason }}</span>
            </div>

            <div class="truck-svg-wrap">
              <svg :viewBox="truckSvgViewBox" class="truck-svg" preserveAspectRatio="xMidYMid meet">
                <rect x="0" y="0" :width="truckSvgViewW" :height="truckSvgViewH" class="truck-bed" />
                <template v-for="(item, idx) in truckPlacedItems" :key="idx">
                  <rect
                    :x="item.x" :y="item.y"
                    :width="item.w" :height="item.d"
                    :fill="item.color"
                    class="truck-container-rect"
                  >
                    <title>{{ item.label }}</title>
                  </rect>
                  <text
                    :x="item.x + item.w / 2"
                    :y="item.y + item.d / 2"
                    :font-size="item.fontSize"
                    text-anchor="middle"
                    dominant-baseline="central"
                    class="truck-layer-text"
                  >{{ item.layers }}</text>
                </template>
              </svg>
            </div>

            <div class="truck-legend">
              <div v-for="(item, idx) in truckLegendItems" :key="idx" class="truck-legend-row">
                <span class="truck-swatch" :style="{ background: item.color }"></span>
                <span class="truck-legend-code">{{ item.product_code }}×{{ item.qty }}（{{ item.containerCount }}容器）</span>
              </div>
            </div>

            <div class="truck-remaining" v-if="truckCheckResult.remaining?.length">
              <span class="truck-remaining-label">残りスペース</span>
              <div v-for="(r, idx) in truckCheckResult.remaining" :key="idx" class="truck-remaining-row">
                <span>{{ r.label }}</span>
                <span class="truck-remaining-count">あと{{ r.count }}箱</span>
              </div>
            </div>

            <div v-if="truckCheckResult.fetched_items?.length" class="truck-items-table">
              <table class="data-table compact-table">
                <thead>
                  <tr><th>品番</th><th>品名</th><th>数量</th><th>容器</th><th>容器数</th><th>親</th><th>積載</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in truckCheckResult.fetched_items" :key="idx">
                    <td>{{ item.product_code }}</td>
                    <td>{{ item.product_name }}</td>
                    <td class="td-right">{{ item.order_qty }}</td>
                    <td>{{ item.container_name || '-' }}</td>
                    <td class="td-right">{{ item.container_count || '-' }}</td>
                    <td>{{ item.parent_name || '-' }}</td>
                    <td><span :class="item.loaded ? 'badge-on' : 'badge-overload'" class="badge badge-sm">{{ item.loaded ? '○' : '未' }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <table v-if="configs.length" class="data-table">
        <thead>
          <tr>
            <th>仕入先</th>
            <th>実行時刻</th>
            <th>納入日</th>
            <th>進度表期間</th>
            <th>納入日判定</th>
            <th>数量方式</th>
            <th>安全在庫</th>
            <th>有効</th>
            <th>最終実行</th>
            <th>ステータス</th>
            <th>メッセージ</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="config in configs" :key="config.id">
            <td>{{ config.supplier_code }} {{ config.supplier_name }}</td>
            <td>{{ String(config.scheduled_hour).padStart(2, '0') }}:{{ String(config.scheduled_minute).padStart(2, '0') }}</td>
            <td>{{ config.lead_time_days }}営業日後</td>
            <td>{{ config.progress_days_back }}営業日前 ～ {{ config.progress_days_forward }}日後</td>
            <td>{{ deliveryDayModeLabel(config.delivery_day_mode) }}</td>
            <td>{{ calcModeLabel(config.calc_mode) }}</td>
            <td>{{ config.safety_stock_enabled ? `確保 (×${config.safety_stock_multiplier})` : '確保しない' }}</td>
            <td><span :class="['badge', config.is_enabled ? 'badge-on' : 'badge-off']">{{ config.is_enabled ? '有効' : '無効' }}</span></td>
            <td>{{ config.last_run_at || '-' }}</td>
            <td><span v-if="config.last_run_status" :class="['badge', `badge-${config.last_run_status.toLowerCase()}`]">{{ config.last_run_status }}</span></td>
            <td class="td-msg">{{ config.last_run_message || '' }}</td>
            <td class="td-actions">
              <button class="btn-sm" @click="openEdit(config)">編集</button>
              <button class="btn-sm btn-run" :disabled="running.has(config.id)" @click="runNow(config)">{{ running.has(config.id) ? '実行中...' : '今すぐ実行' }}</button>
              <button class="btn-sm btn-holiday" :disabled="running.has(config.id)" @click="runHolidayTrial(config)">休日トライ</button>
              <button class="btn-sm btn-danger" @click="remove(config)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="no-data">注文書自動送信設定がありません。</div>
    </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h2 class="modal-title">{{ isEdit ? '設定編集' : '新規設定' }}</h2>

        <div class="form-group">
          <label>仕入先 <span class="required">*</span></label>
          <select v-model="form.supplier_id" :disabled="isEdit">
            <option value="">-- 選択 --</option>
            <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.supplier_code }} {{ supplier.supplier_name }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>実行時刻 <span class="required">*</span></label>
          <div class="time-row">
            <input v-model.number="form.scheduled_hour" type="number" min="0" max="23" class="time-input" />
            <span class="suffix">時</span>
            <input v-model.number="form.scheduled_minute" type="number" min="0" max="59" class="time-input" />
            <span class="suffix">分</span>
          </div>
        </div>

        <div class="form-group">
          <label>納入日（実行日から何営業日後） <span class="required">*</span></label>
          <div class="time-row">
            <input v-model.number="form.lead_time_days" type="number" min="0" max="30" class="time-input" />
            <span class="suffix">営業日後</span>
          </div>
        </div>

        <div class="form-group">
          <label>進度表期間 <span class="required">*</span></label>
          <div class="time-row">
            <input v-model.number="form.progress_days_back" type="number" min="1" max="90" class="time-input" />
            <span class="suffix">営業日前 ～</span>
            <input v-model.number="form.progress_days_forward" type="number" min="1" max="120" class="time-input" />
            <span class="suffix">日後（発行日基準）</span>
          </div>
        </div>

        <div class="form-group">
          <label>数量算出方式 <span class="required">*</span></label>
          <select v-model="form.calc_mode">
            <option value="DEMAND">需要そのまま</option>
            <option value="LOT_ROUNDED">ロット丸め</option>
          </select>
        </div>

        <div class="form-group">
          <label>納入日判定方式 <span class="required">*</span></label>
          <select v-model="form.delivery_day_mode">
            <option value="PATTERN">納入パターン</option>
            <option value="SUPPLIER_CALENDAR">仕入れ先カレンダ</option>
          </select>
          <div v-if="showSupplierCalendarWarning" class="form-warning">
            選択した仕入先カレンダに納入日が未設定です。仕入れ先カレンダ判定では納入日を判定できません。
          </div>
        </div>

        <div class="form-group">
          <label>安全在庫確保</label>
          <select v-model="form.safety_stock_enabled">
            <option :value="false">確保しない</option>
            <option :value="true">確保する</option>
          </select>
          <div v-if="form.safety_stock_enabled" class="time-row" style="margin-top: 6px;">
            <span class="suffix">倍数:</span>
            <input v-model.number="form.safety_stock_multiplier" type="number" min="0.1" max="10" step="0.1" class="time-input" />
          </div>
          <div v-if="form.safety_stock_enabled" class="form-hint">納入数 = カバー期間需要合計 − 計進 + 安全在庫 × 倍数</div>
        </div>

        <div class="form-group">
          <label class="checkbox-label"><input v-model="form.is_enabled" type="checkbox" /> 有効</label>
        </div>

        <div class="form-group">
          <label>送信ファイル選択</label>
          <div class="file-toggle-grid">
            <label class="checkbox-label"><input v-model="form.send_order_excel" type="checkbox" /> 注文書Excel送信</label>
            <label class="checkbox-label"><input v-model="form.send_delivery_note_pdf" type="checkbox" /> 外作納品書 PDF</label>
          </div>
        </div>

        <div class="form-group">
          <div class="label-row">
            <label>メール本文（空欄なら自動生成）</label>
          </div>
          <textarea v-model="form.email_body_custom" rows="8" class="input-full"></textarea>
        </div>

        <div class="form-group">
          <label>返信先メールアドレス <span class="required">*</span></label>
          <ContactEmailSelect
            v-model="form.reply_to_email"
            :contacts="contactList"
            :supplier-keywords="selectedSupplierKeywords"
            placeholder="連絡先マスタから返信先を検索して追加"
          />
        </div>

        <div class="form-group">
          <label>業務員CC送信先メール <span class="required">*</span></label>
          <ContactEmailSelect
            v-model="ccEmailList"
            :contacts="contactList"
            :supplier-keywords="selectedSupplierKeywords"
            multiple
            placeholder="連絡先マスタからCC送信先を検索して追加"
          />
        </div>

        <div class="form-group">
          <label>失敗時の通知先 <span class="required">*</span></label>
          <UserChipSelect :userList="userList" v-model="form.notify_on_failure_user_ids" />
        </div>

        <div class="form-group">
          <label>納入日でないときの通知先 <span class="required">*</span></label>
          <UserChipSelect :userList="userList" v-model="form.notify_on_non_delivery_user_ids" />
        </div>

        <div class="form-actions">
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="btn-secondary" @click="closeModal">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/client'
import UserChipSelect from './UserChipSelect.vue'
import ContactEmailSelect from './ContactEmailSelect.vue'

const loading = ref(true)
const saving = ref(false)
const configs = ref([])
const truckCandidates = ref([])
const truckCheckLoading = ref(false)
const truckCheckResult = ref(null)
const truckCheck = reactive({
  truck_id: '',
  delivery_date: '',
})
const suppliers = ref([])
const userList = ref([])
const contactList = ref([])
const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const running = reactive(new Set())
const supplierCalendarHasDeliveryDays = ref(true)
const checkingSupplierCalendarDays = ref(false)
const todayYmd = new Date().toISOString().slice(0, 10)

const form = reactive({
  supplier_id: '',
  is_enabled: true,
  scheduled_hour: 7,
  scheduled_minute: 0,
  lead_time_days: 5,
  progress_days_back: 7,
  progress_days_forward: 30,
  calc_mode: 'LOT_ROUNDED',
  delivery_day_mode: 'SUPPLIER_CALENDAR',
  safety_stock_enabled: false,
  safety_stock_multiplier: 1,
  send_order_excel: true,
  send_delivery_note_pdf: true,
  email_body_custom: '',
  reply_to_email: '',
  cc_emails: '',
  notify_on_failure_user_ids: [],
  notify_on_non_delivery_user_ids: [],
})

const splitEmailLines = (text) => {
  return String(text || '')
    .split('\n')
    .map((email) => email.trim())
    .filter(Boolean)
}

const ccEmailList = computed({
  get: () => splitEmailLines(form.cc_emails),
  set: (emails) => {
    form.cc_emails = (emails || []).join('\n')
  },
})

const selectedSupplier = computed(() => suppliers.value.find((supplier) => String(supplier.id) === String(form.supplier_id)) || null)
const selectedSupplierKeywords = computed(() => {
  if (!selectedSupplier.value) return []
  return [selectedSupplier.value.supplier_code, selectedSupplier.value.supplier_name]
})
const showSupplierCalendarWarning = computed(() => {
  return (
    form.delivery_day_mode === 'SUPPLIER_CALENDAR'
    && !!selectedSupplier.value
    && !!selectedSupplier.value.calendar
    && !checkingSupplierCalendarDays.value
    && !supplierCalendarHasDeliveryDays.value
  )
})

const calcModeLabel = (mode) => {
  if (mode === 'LOT_ROUNDED') return 'ロット丸め'
  return '需要そのまま'
}

const deliveryDayModeLabel = (mode) => {
  if (mode === 'SUPPLIER_CALENDAR') return '仕入れ先カレンダ'
  return '納入パターン'
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await api.purchaseAutoOrderSend.getConfigs()
    configs.value = res.data || []
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) => (a.supplier_code || '').localeCompare(b.supplier_code || ''))
}

const loadUsers = async () => {
  const res = await api.accounts.getUsers({ is_active: true, page_size: 9999 })
  userList.value = res.data?.results || res.data || []
}

const loadContacts = async () => {
  const res = await api.contacts.getContacts({ is_active: true, page_size: 9999 })
  contactList.value = (res.data?.results || res.data || []).filter((contact) => contact.email)
}

const loadTruckCandidates = async () => {
  // 仕入れ先トラックマスタのトラック一覧を取得
  try {
    const res = await api.supplierTrucks.getSupplierTrucks({ is_active: true, page_size: 9999 })
    truckCandidates.value = (res.data?.results || res.data || [])
  } catch (error) {
    console.error('仕入れ先トラック一覧取得エラー', error)
  }
}

const TRUCK_COLOR_PALETTE = [
  '#fca5a5', '#fbbf24', '#86efac', '#7dd3fc', '#c4b5fd',
  '#f9a8d4', '#fdba74', '#a7f3d0', '#93c5fd', '#fcd34d',
  '#d9f99d', '#f5d0fe', '#a5b4fc', '#fda4af', '#bef264',
]
const truckColorForProduct = (code) => {
  let hash = 0
  const str = String(code || '')
  for (let i = 0; i < str.length; i++) hash = (hash * 31 + str.charCodeAt(i)) >>> 0
  return TRUCK_COLOR_PALETTE[hash % TRUCK_COLOR_PALETTE.length]
}

const truckSvgViewW = computed(() => {
  const truck = truckCheckResult.value?.truck
  return truck ? truck.depth : 1
})
const truckSvgViewH = computed(() => {
  const truck = truckCheckResult.value?.truck
  return truck ? truck.width : 1
})
const truckSvgViewBox = computed(() => `0 0 ${truckSvgViewW.value} ${truckSvgViewH.value}`)

const truckPlacedItems = computed(() => {
  const placed = truckCheckResult.value?.placed || []
  const usedColors = new Map()
  return placed.map((p) => {
    const pw = Number(p.w) || 0
    const pd = Number(p.d) || 0
    if (!usedColors.has(p.product_code)) {
      usedColors.set(p.product_code, truckColorForProduct(p.product_code))
    }
    const slotProducts = Array.isArray(p.slot_products) ? p.slot_products : []
    const label = slotProducts.length
      ? slotProducts
        .map((sp) => `${sp.product_code}（${sp.container_count}容器）`)
        .join(' + ')
      : `${p.product_code}×${p.qty}（${p.layers || 1}段）`
    return {
      x: Number(p.x) || 0,
      y: Number(p.y) || 0,
      w: pw,
      d: pd,
      layers: p.layers || 1,
      fontSize: Math.max(60, Math.min(pw, pd) * 0.4),
      rotated: Boolean(p.rotated),
      color: usedColors.get(p.product_code),
      label,
    }
  })
})

const truckLegendItems = computed(() => {
  const fetchedItems = truckCheckResult.value?.fetched_items || []
  if (fetchedItems.length) {
    return fetchedItems.map((item) => ({
      product_code: item.product_code,
      qty: Number(item.order_qty) || 0,
      containerCount: Number(item.container_count) || 0,
      color: truckColorForProduct(item.product_code),
    }))
  }

  const placed = truckCheckResult.value?.placed || []
  return placed.map((p, index) => ({
    product_code: p.product_code,
    qty: Number(p.qty) || 0,
    containerCount: Number(p.layers) || 1,
    color: truckColorForProduct(`${p.product_code}-${index}`),
  }))
})

const truckContainerSummaryText = computed(() => {
  const fetchedItems = truckCheckResult.value?.fetched_items || []
  if (!fetchedItems.length) return ''

  const directTotals = new Map()
  const parentBuckets = new Map()
  const childToParentMap = new Map()

  fetchedItems.forEach((item) => {
    const directName = String(item.container_name || '').trim()
    const directCount = Number(item.container_count) || 0
    if (directName && directCount > 0) {
      directTotals.set(directName, (directTotals.get(directName) || 0) + directCount)
    }

    const parentName = String(item.parent_name || '').trim()
    const parentCapacity = Number(item.parent_capacity) || 0
    if (parentName && parentCapacity > 0 && directCount > 0) {
      const bucket = parentBuckets.get(parentName) || { total: 0, capacity: parentCapacity }
      bucket.total += directCount
      bucket.capacity = parentCapacity
      parentBuckets.set(parentName, bucket)
      if (directName) {
        childToParentMap.set(directName, parentName)
      }
    }
  })

  const parts = []
  directTotals.forEach((count, name) => {
    const parentName = childToParentMap.get(name)
    const parentBucket = parentName ? parentBuckets.get(parentName) : null
    if (parentBucket) {
      parts.push(`${name}×${count}（ ${parentName}×${Math.ceil(parentBucket.total / parentBucket.capacity)}）`)
      return
    }
    parts.push(`${name}×${count}`)
  })
  return parts.join(' ＋ ')
})

const onTruckChange = () => {
  truckCheckResult.value = null
}

const runTruckLoadCheck = async () => {
  if (!truckCheck.truck_id || !truckCheck.delivery_date) {
    alert('トラックと納期を選択してください')
    return
  }

  truckCheckLoading.value = true
  truckCheckResult.value = null
  try {
    const res = await api.purchaseAutoOrderSend.checkTruckLoad({
      truck_id: truckCheck.truck_id,
      delivery_date: truckCheck.delivery_date,
    })
    truckCheckResult.value = res.data
  } catch (error) {
    console.error('トラック積載判定エラー', error)
    const data = error?.response?.data
    const detail = data?.detail || ''
    const invalidItems = data?.invalid_items || []
    const lines = [detail || 'トラック積載判定に失敗しました']
    if (invalidItems.length) {
      lines.push('')
      invalidItems.forEach((item) => {
        const reason = item.reason === 'container not configured' ? '容器未設定' : item.reason === 'product not found' ? '品番不明' : item.reason
        lines.push(`  ${item.product_code}: ${reason}`)
      })
    }
    alert(lines.join('\n'))
  } finally {
    truckCheckLoading.value = false
  }
}

const checkSelectedSupplierCalendarDeliveryDays = async () => {
  supplierCalendarHasDeliveryDays.value = true
  checkingSupplierCalendarDays.value = false
  if (form.delivery_day_mode !== 'SUPPLIER_CALENDAR') return
  if (!selectedSupplier.value?.calendar) return

  checkingSupplierCalendarDays.value = true
  try {
    const res = await api.calendars.getCalendarDays(selectedSupplier.value.calendar)
    const days = res.data?.results || res.data || []
    supplierCalendarHasDeliveryDays.value = days.some(
      (day) => Boolean(day.is_delivery_day) && String(day.target_date || '') >= todayYmd,
    )
  } catch (error) {
    console.error('仕入先カレンダ納入日確認エラー', error)
    supplierCalendarHasDeliveryDays.value = true
  } finally {
    checkingSupplierCalendarDays.value = false
  }
}

const resetForm = () => {
  form.supplier_id = ''
  form.is_enabled = true
  form.scheduled_hour = 7
  form.scheduled_minute = 0
  form.lead_time_days = 5
  form.progress_days_back = 7
  form.progress_days_forward = 30
  form.calc_mode = 'LOT_ROUNDED'
  form.delivery_day_mode = 'SUPPLIER_CALENDAR'
  form.safety_stock_enabled = false
  form.safety_stock_multiplier = 1
  form.send_order_excel = true
  form.send_delivery_note_pdf = true
  form.email_body_custom = ''
  form.reply_to_email = ''
  form.cc_emails = ''
  form.notify_on_failure_user_ids = []
  form.notify_on_non_delivery_user_ids = []
  supplierCalendarHasDeliveryDays.value = true
  checkingSupplierCalendarDays.value = false
}

const openNew = () => {
  resetForm()
  isEdit.value = false
  editId.value = null
  showModal.value = true
}

const openEdit = (config) => {
  isEdit.value = true
  editId.value = config.id
  form.supplier_id = config.supplier_id
  form.is_enabled = config.is_enabled
  form.scheduled_hour = config.scheduled_hour
  form.scheduled_minute = config.scheduled_minute
  form.lead_time_days = config.lead_time_days
  form.progress_days_back = config.progress_days_back ?? 7
  form.progress_days_forward = config.progress_days_forward ?? 30
  form.calc_mode = config.calc_mode
  form.delivery_day_mode = config.delivery_day_mode || 'PATTERN'
  form.safety_stock_enabled = !!config.safety_stock_enabled
  form.safety_stock_multiplier = config.safety_stock_multiplier ?? 1
  form.send_order_excel = config.send_order_excel
  form.send_delivery_note_pdf = config.send_delivery_note_pdf ?? true
  form.email_body_custom = config.email_body_custom || ''
  form.reply_to_email = config.reply_to_email || ''
  form.cc_emails = config.cc_emails || ''
  form.notify_on_failure_user_ids = [...(config.notify_on_failure_user_ids || [])]
  form.notify_on_non_delivery_user_ids = [...(config.notify_on_non_delivery_user_ids || [])]
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const validate = () => {
  const errors = []
  if (!form.supplier_id) errors.push('仕入先')
  if (form.lead_time_days === null || form.lead_time_days === '' || Number.isNaN(form.lead_time_days)) {
    errors.push('納入日（営業日後）')
  }
  if (!form.progress_days_back) errors.push('進度表（営業日前）')
  if (!form.progress_days_forward) errors.push('進度表（日後・発行日基準）')
  if (!form.reply_to_email?.trim()) errors.push('返信先メールアドレス')
  if (!form.cc_emails?.trim()) errors.push('業務員CC送信先メール')
  if (!form.notify_on_failure_user_ids.length) errors.push('失敗時の通知先')
  if (!form.notify_on_non_delivery_user_ids.length) errors.push('納入日でないときの通知先')
  if (showSupplierCalendarWarning.value) errors.push('仕入先カレンダ（納入日未設定）')
  if (errors.length) {
    alert(`以下の項目は必須です:\n${errors.join('\n')}`)
    return false
  }
  return true
}

const buildPayload = () => ({
  supplier_id: form.supplier_id,
  is_enabled: form.is_enabled,
  scheduled_hour: form.scheduled_hour,
  scheduled_minute: form.scheduled_minute,
  lead_time_days: form.lead_time_days,
  progress_days_back: form.progress_days_back,
  progress_days_forward: form.progress_days_forward,
  calc_mode: form.calc_mode,
  delivery_day_mode: form.delivery_day_mode,
  safety_stock_enabled: form.safety_stock_enabled,
  safety_stock_multiplier: form.safety_stock_multiplier,
  send_order_excel: form.send_order_excel,
  send_delivery_note_pdf: form.send_delivery_note_pdf,
  email_body_custom: form.email_body_custom,
  reply_to_email: form.reply_to_email,
  cc_emails: form.cc_emails,
  notify_on_failure_user_ids: form.notify_on_failure_user_ids,
  notify_on_non_delivery_user_ids: form.notify_on_non_delivery_user_ids,
})

const save = async () => {
  if (!validate()) return
  saving.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await api.purchaseAutoOrderSend.updateConfig(editId.value, payload)
    } else {
      await api.purchaseAutoOrderSend.createConfig(payload)
    }
    closeModal()
    await loadConfigs()
  } catch (error) {
    const detail = error?.response?.data?.detail
    alert(`保存に失敗しました。${detail ? `\n${detail}` : ''}`)
  } finally {
    saving.value = false
  }
}

const remove = async (config) => {
  if (!confirm(`${config.supplier_code} ${config.supplier_name} の設定を削除しますか？`)) return
  try {
    await api.purchaseAutoOrderSend.deleteConfig(config.id)
    await loadConfigs()
  } catch {
    alert('削除に失敗しました。')
  }
}

const runNow = async (config) => {
  if (!confirm(`${config.supplier_code} ${config.supplier_name} の注文書自動送信を今すぐ実行しますか？`)) return
  running.add(config.id)
  try {
    await api.purchaseAutoOrderSend.runNow(config.id)
    const start = Date.now()
    const timer = setInterval(async () => {
      if (Date.now() - start > 5 * 60 * 1000) {
        clearInterval(timer)
        running.delete(config.id)
        alert('5分経過しても完了しませんでした。')
        return
      }
      await loadConfigs()
      const updated = configs.value.find((item) => item.id === config.id)
      if (updated && updated.last_run_status !== 'RUNNING') {
        clearInterval(timer)
        running.delete(config.id)
        alert(`完了: ${updated.last_run_status}\n${updated.last_run_message || ''}`)
      }
    }, 3000)
  } catch {
    running.delete(config.id)
    alert('実行に失敗しました。')
  }
}

const runHolidayTrial = async (config) => {
  if (!confirm(`${config.supplier_code} ${config.supplier_name} の注文書自動送信を休日トライ実行しますか？`)) return
  running.add(config.id)
  try {
    await api.purchaseAutoOrderSend.runHolidayTrial(config.id)
    const start = Date.now()
    const timer = setInterval(async () => {
      if (Date.now() - start > 5 * 60 * 1000) {
        clearInterval(timer)
        running.delete(config.id)
        alert('5分経過しても完了しませんでした。')
        return
      }
      await loadConfigs()
      const updated = configs.value.find((item) => item.id === config.id)
      if (updated && updated.last_run_status !== 'RUNNING') {
        clearInterval(timer)
        running.delete(config.id)
        alert(`完了: ${updated.last_run_status}\n${updated.last_run_message || ''}`)
      }
    }, 3000)
  } catch {
    running.delete(config.id)
    alert('休日トライ実行に失敗しました。')
  }
}

onMounted(async () => {
  await Promise.all([loadConfigs(), loadSuppliers(), loadUsers(), loadContacts(), loadTruckCandidates()])
})

watch(
  () => [form.supplier_id, form.delivery_day_mode, selectedSupplier.value?.calendar],
  () => {
    checkSelectedSupplierCalendarDeliveryDays()
  },
)
</script>

<style scoped>
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 6px 8px; border-bottom: 2px solid #e5e9ef; font-weight: 700; color: #374151; background: #f8fafc; white-space: nowrap; }
.data-table td { padding: 8px; border-bottom: 1px solid #e5e9ef; }
.td-msg { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #64748b; }
.td-actions { white-space: nowrap; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-on { background: #dcfce7; color: #166534; }
.badge-off { background: #f1f5f9; color: #64748b; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-failed { background: #fee2e2; color: #991b1b; }
.badge-running { background: #dbeafe; color: #1e40af; }
.badge-skipped { background: #fef3c7; color: #92400e; }
.btn-sm { padding: 3px 10px; font-size: 12px; border: 1px solid #d1d5db; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-run { border-color: #3b82f6; color: #2563eb; }
.btn-holiday { border-color: #f59e0b; color: #b45309; }
.btn-danger { border-color: #fca5a5; color: #dc2626; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 8px; padding: 24px; width: 520px; max-height: 85vh; overflow-y: auto; box-shadow: 0 4px 24px rgba(0,0,0,0.2); }
.modal-title { margin: 0 0 16px; font-size: 16px; }
.form-group { margin-bottom: 14px; }
.form-group > label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.form-group select, .input-full { width: 100%; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
.time-row { display: flex; align-items: center; gap: 4px; }
.time-input { width: 60px; text-align: center; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
.suffix { font-size: 13px; color: #475569; }
.form-warning { margin-top: 6px; padding: 8px 10px; border-radius: 4px; background: #fff7ed; color: #9a3412; font-size: 12px; border: 1px solid #fdba74; }
.checkbox-label { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.file-toggle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; }
.label-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.form-hint { margin-top: 4px; font-size: 11px; color: #6b7280; }
.required { color: #dc2626; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.btn-primary { padding: 6px 16px; background: #2563eb; color: #fff; border: none; border-radius: 4px; font-weight: 600; cursor: pointer; }
.btn-secondary { padding: 6px 16px; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
 .truck-check-panel { margin-bottom: 18px; padding: 14px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f8fafc; }
 .truck-check-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
 .truck-check-header h2 { margin: 0; font-size: 15px; }
 .truck-check-form { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
 .form-group.compact { margin-bottom: 0; min-width: 220px; }
 .truck-check-form select { width: 100%; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
 .hint-text { font-size: 11px; color: #6b7280; margin-left: 4px; }
 .truck-check-result-area { margin-top: 12px; padding: 12px; border-radius: 6px; background: #fff; border: 1px solid #d1d5db; }
 .truck-result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; }
 .truck-result-name { font-weight: 700; }
 .truck-result-occ { font-size: 13px; color: #475569; }
 .badge-overload { background: #fee2e2; color: #991b1b; }
 .badge-sm { padding: 1px 5px; font-size: 10px; }
 .truck-result-errors { font-size: 12px; color: #991b1b; margin-bottom: 4px; display: flex; flex-direction: column; gap: 2px; }
 .truck-result-warnings { font-size: 12px; color: #92400e; margin-bottom: 4px; display: flex; flex-direction: column; gap: 2px; }
 .truck-svg-wrap { width: 100%; max-width: 400px; background: #fff; border: 1px solid #d7dfe8; border-radius: 4px; margin-bottom: 8px; }
 .truck-svg { display: block; width: 100%; height: auto; }
 .truck-bed { fill: #eef2f6; stroke: #1f2937; stroke-width: 6; }
 .truck-container-rect { stroke: #111827; stroke-width: 2; }
 .truck-layer-text { fill: #111827; font-weight: 700; user-select: none; }
 .truck-legend { display: flex; flex-direction: column; gap: 2px; margin-bottom: 6px; font-size: 12px; }
 .truck-result-summary { font-weight: 600; color: #374151; }
 .truck-legend-row { display: flex; align-items: center; gap: 5px; }
 .truck-swatch { flex-shrink: 0; width: 10px; height: 10px; border-radius: 2px; border: 1px solid rgba(0,0,0,0.15); }
 .truck-legend-code { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
 .truck-remaining { margin-top: 6px; border-top: 1px dashed #c5cfde; padding-top: 4px; font-size: 12px; }
 .truck-remaining-label { display: block; font-weight: 700; color: #374151; margin-bottom: 2px; }
 .truck-remaining-row { display: flex; align-items: center; justify-content: space-between; font-size: 11px; }
 .truck-remaining-count { white-space: nowrap; color: #0369a1; font-weight: 600; }
 .truck-items-table { margin-top: 10px; }
 .compact-table { font-size: 12px; }
 .compact-table th { padding: 4px 6px; }
 .compact-table td { padding: 3px 6px; }
 .td-right { text-align: right; }
</style>
