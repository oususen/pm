<template>
  <div class="page-container" v-if="canViewInput">
    <div class="page-header">
      <div>
        <h1 class="page-title">製品チェックシート入力</h1>
        <p class="helper-text" v-if="batch">
          {{ batch.product_code }} / {{ batch.process_code }} / ロット {{ batch.lot_no || '-' }}:
          {{ completedCount }} / {{ batch.quantity }} 枚入力済み
        </p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" type="button" @click="goReturn">戻る</button>
      </div>
    </div>

    <div v-if="batch && currentRecord" class="input-grid">
      <aside class="panel">
        <h2>対象</h2>
        <div class="record-nav">
          <button
            v-for="record in records"
            :key="record.id"
            type="button"
            class="record-chip"
            :class="{ active: record.id === currentRecord.id, done: record.status !== 'PENDING' }"
            @click="selectRecord(record)"
          >
            {{ record.sequence_no }}/{{ batch.quantity }}
          </button>
        </div>

        <div v-if="currentRecord.status !== 'PENDING'" class="result-summary">
          <div class="result-badge" :class="currentRecord.status === 'APPROVED' ? 'approved' : 'completed'">
            {{ currentRecord.status === 'APPROVED' ? '承認済み' : '入力済み' }}
          </div>
          <div class="result-meta">入力者: {{ currentRecord.completed_by_name || '-' }}</div>
          <div class="result-meta">完了: {{ formatDateTime(currentRecord.completed_at) }}</div>
          <div v-if="currentRecord.supervisor_name" class="result-meta">確認者: {{ currentRecord.supervisor_name }}</div>
          <div class="result-fields">
            <div v-for="field in fields" :key="'r-'+field.key" class="result-field-row">
              <span class="result-label">{{ field.label }}:</span>
              <span class="result-value">{{ displayValue(field) }}</span>
            </div>
          </div>
        </div>

        <h2>入力情報</h2>
        <label>計画日<input v-model="plannedShipDate" type="date" /></label>
        <label>台目<input v-model.number="shipmentUnitNo" type="number" min="1" /></label>
        <label>入力者<input v-model="completedByName" type="text" /></label>
        <button class="btn-primary" type="button" @click="saveCurrent" :disabled="saving || !canEditInput">{{ saving ? '保存中' : 'この1枚を保存' }}</button>
        <p v-if="!canEditInput" class="helper-text">閲覧のみ可能です（入力権限がありません）。</p>
        <p class="helper-text">計画日と台目は次の1枚へ引き継がれます。</p>
      </aside>

      <section class="sheet-panel">
        <div class="sheet-toolbar">
          <strong>{{ currentRecord.sequence_no }} / {{ batch.quantity }}</strong>
          <button class="btn-secondary" type="button" @click="prevRecord">前へ</button>
          <button class="btn-secondary" type="button" @click="nextRecord">次へ</button>
        </div>
        <div class="sheet-scroll">
          <div class="sheet-stage" :style="stageStyle">
            <img class="sheet-image" :src="version.background_image_url" alt="台紙" />
            <div
              v-for="field in fields"
              :key="field.key"
              class="input-box"
              :class="`type-${field.field_type}`"
              :style="boxStyle(field)"
            >
              <label v-if="field.show_label !== false">{{ field.label }}<span v-if="field.required" class="required">*</span></label>
              <button
                v-if="field.field_type === 'checkbox'"
                type="button"
                class="check-btn"
                :class="{ checked: responses[field.key] }"
                @click="responses[field.key] = !responses[field.key]"
              >
                {{ responses[field.key] ? '✓' : '□' }}
              </button>
              <select v-else-if="field.field_type === 'aggregate_okng'" v-model="responses[field.key]">
                <option value="">選択</option>
                <option value="OK">OK</option>
                <option value="NG">NG</option>
              </select>
              <input v-else-if="field.field_type === 'date'" v-model="responses[field.key]" type="date" />
              <input v-else-if="field.field_type === 'photo'" type="file" accept="image/*" @change="onPhotoChange($event, field.key)" />
              <div v-else-if="field.field_type === 'supervisor_stamp'" class="read-value">承認印</div>
              <div v-else-if="field.field_type === 'pen'" class="pen-area">
                <canvas
                  :ref="(el) => setPenCanvas(el, field.key)"
                  :width="field.width"
                  :height="field.height - (field.show_label !== false ? 18 : 0)"
                  @pointerdown="penDown($event, field.key)"
                  @pointermove="penMove($event, field.key)"
                  @pointerup="penUp(field.key)"
                  @pointerleave="penUp(field.key)"
                />
                <button type="button" class="pen-clear" @click="penClear(field.key)">消去</button>
              </div>
              <input v-else v-model="responses[field.key]" type="text" :placeholder="field.placeholder" />
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>

  <div class="page-container" v-else>
    <h1 class="page-title">製品チェックシート入力</h1>
    <p class="helper-text">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const route = useRoute()
const router = useRouter()
const batch = ref(null)
const records = ref([])
const currentRecord = ref(null)
const responses = ref({})
const photos = ref({})
const penCanvases = {}
const penDrawing = ref({})

const setPenCanvas = (el, key) => {
  if (el) penCanvases[key] = el
}

const penDown = (event, key) => {
  const canvas = penCanvases[key]
  if (!canvas) return
  penDrawing.value[key] = true
  const ctx = canvas.getContext('2d')
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  ctx.beginPath()
  ctx.moveTo((event.clientX - rect.left) * scaleX, (event.clientY - rect.top) * scaleY)
  canvas.setPointerCapture(event.pointerId)
}

const penMove = (event, key) => {
  if (!penDrawing.value[key]) return
  const canvas = penCanvases[key]
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  ctx.lineWidth = 2
  ctx.strokeStyle = '#111'
  ctx.lineCap = 'round'
  ctx.lineTo((event.clientX - rect.left) * scaleX, (event.clientY - rect.top) * scaleY)
  ctx.stroke()
}

const penUp = (key) => {
  if (!penDrawing.value[key]) return
  penDrawing.value[key] = false
  const canvas = penCanvases[key]
  if (canvas) responses.value[key] = canvas.toDataURL('image/png')
}

const penClear = (key) => {
  const canvas = penCanvases[key]
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  responses.value[key] = ''
}

const restorePenCanvas = (key, dataUrl) => {
  const canvas = penCanvases[key]
  if (!canvas || !dataUrl || !dataUrl.startsWith('data:')) return
  const ctx = canvas.getContext('2d')
  const img = new window.Image()
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  }
  img.src = dataUrl
}

const plannedShipDate = ref('')
const shipmentUnitNo = ref('')
const completedByName = ref('')
const saving = ref(false)
const canAccessQuality = (resource, level = 'view', aliases = []) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) return candidates.some((c) => hasPermission(user, c, level))
  return hasPermission(user, 'quality', level)
}
const canViewInput = computed(() =>
  canAccessQuality('quality.product_checksheet_input', 'view', [
    'quality.product_checksheet_operation',
    'quality.product_checksheet_template',
    'quality',
  ])
)
const canEditInput = computed(() => canAccessQuality('quality.product_checksheet_input', 'edit'))

const version = computed(() => batch.value?.template_detail || {})
const fields = computed(() => version.value?.fields_data || [])
const completedCount = computed(() => records.value.filter((item) => item.status !== 'PENDING').length)
const stageStyle = computed(() => ({
  width: `${version.value?.background_width || 1200}px`,
  height: `${version.value?.background_height || 1600}px`,
}))

const loadBatch = async () => {
  const [batchRes, recordRes] = await Promise.all([
    api.productChecksheets.getBatch(route.params.batchId),
    api.productChecksheets.listBatchRecords(route.params.batchId),
  ])
  batch.value = batchRes.data
  records.value = recordRes.data || []
  const firstPending = records.value.find((item) => item.status === 'PENDING')
  const target = firstPending || records.value[0]
  if (firstPending && !shipmentUnitNo.value) {
    shipmentUnitNo.value = firstPending.sequence_no ?? 1
  }
  if (target) selectRecord(target)
}

const selectRecord = (record) => {
  currentRecord.value = record
  photos.value = {}
  responses.value = {}
  fields.value.forEach((field) => {
    const saved = record.responses_json?.[field.key]
    if (saved && Object.prototype.hasOwnProperty.call(saved, 'value')) {
      responses.value[field.key] = saved.value
    } else if (field.field_type === 'checkbox') {
      responses.value[field.key] = false
    } else {
      responses.value[field.key] = field.field_type === 'date' ? formatISODate(new Date()) : ''
    }
  })
  plannedShipDate.value = record.planned_ship_date || plannedShipDate.value || ''
  shipmentUnitNo.value = record.shipment_unit_no || shipmentUnitNo.value || ''
  completedByName.value = record.completed_by_name || completedByName.value || batch.value?.operator_name || ''
  nextTick(() => {
    fields.value.forEach((field) => {
      if (field.field_type === 'pen' && responses.value[field.key]) {
        restorePenCanvas(field.key, responses.value[field.key])
      }
    })
  })
}

const currentIndex = () => records.value.findIndex((item) => item.id === currentRecord.value?.id)
const prevRecord = () => {
  const index = currentIndex()
  if (index > 0) selectRecord(records.value[index - 1])
}
const nextRecord = () => {
  const index = currentIndex()
  if (index >= 0 && index + 1 < records.value.length) selectRecord(records.value[index + 1])
}

const onPhotoChange = (event, key) => {
  photos.value[key] = event.target.files?.[0] || null
}

const saveCurrent = async () => {
  if (!canEditInput.value) return
  if (!currentRecord.value) return
  saving.value = true
  try {
    const data = new FormData()
    data.append('responses_json', JSON.stringify(responses.value))
    if (plannedShipDate.value) data.append('planned_ship_date', plannedShipDate.value)
    if (shipmentUnitNo.value) data.append('shipment_unit_no', shipmentUnitNo.value)
    if (completedByName.value) data.append('completed_by_name', completedByName.value)
    Object.entries(photos.value).forEach(([key, file]) => {
      if (file) data.append(key, file)
    })
    await api.productChecksheets.saveRecordInput(currentRecord.value.id, data)
    await loadBatch()
  } catch (error) {
    console.error(error)
    alert(`保存に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

const boxStyle = (field) => ({
  left: `${field.x}px`,
  top: `${field.y}px`,
  width: `${field.width}px`,
  height: `${field.height}px`,
})

const formatDateTime = (val) => {
  if (!val) return '-'
  const d = new Date(val)
  if (isNaN(d)) return val
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const displayValue = (field) => {
  const val = responses.value[field.key]
  if (val === undefined || val === null || val === '') return '-'
  if (field.field_type === 'checkbox') return val ? '✓' : '□'
  if (field.field_type === 'pen') return val ? '(手書き入力あり)' : '-'
  if (field.field_type === 'photo') return val ? '(写真あり)' : '-'
  if (field.field_type === 'supervisor_stamp') return '承認印'
  return String(val)
}

const goReturn = () => {
  const returnPath = route.query.return
  if (returnPath) {
    router.push(String(returnPath))
    return
  }
  router.push('/quality/product-checksheet/templates')
}

onMounted(() => {
  if (!canViewInput.value) return
  loadBatch()
})
</script>

<style scoped>
.helper-text { margin: 0; color: #5f6b76; }
.input-grid { display: grid; grid-template-columns: 260px 1fr; gap: 16px; align-items: start; }
.panel, .sheet-panel { background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; }
.panel h2 { margin: 8px 0; font-size: 16px; }
.panel label { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; font-size: 13px; }
.panel input { border: 1px solid #cfd6df; border-radius: 6px; padding: 8px; }
.record-nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 14px; }
.record-chip { border: 1px solid #cfd6df; background: #fff; border-radius: 6px; padding: 6px 4px; cursor: pointer; }
.record-chip.done { background: #059669; border-color: #059669; color: #fff; }
.record-chip.active { background: #2563eb; border-color: #2563eb; color: #fff; }
.sheet-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.sheet-scroll { overflow: auto; max-height: calc(100vh - 190px); border: 1px solid #edf1f5; background: #f8fafc; }
.sheet-stage { position: relative; }
.sheet-image { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.input-box { position: absolute; display: flex; flex-direction: column; gap: 3px; justify-content: center; font-size: 12px; }
.input-box label { color: #111827; font-weight: 600; line-height: 1; }
.input-box input, .input-box select { width: 100%; min-width: 0; border: 1px solid #aeb8c3; border-radius: 4px; padding: 4px; background: rgba(255,255,255,0.92); }
.check-btn { width: 100%; height: 100%; border: 2px solid #111827; background: rgba(255,255,255,0.75); font-size: 20px; cursor: pointer; }
.check-btn.checked { color: #047857; border-color: #047857; }
.read-value { border: 1px dashed #c2410c; color: #c2410c; background: rgba(255,255,255,0.75); padding: 4px; text-align: center; }
.pen-area { position: relative; width: 100%; height: 100%; }
.pen-area canvas { width: 100%; height: calc(100% - 20px); background: rgba(255,255,255,0.05); border: 1px solid rgba(174,184,195,0.3); border-radius: 4px; cursor: crosshair; touch-action: none; }
.pen-clear { position: absolute; top: 2px; right: 2px; font-size: 10px; padding: 1px 6px; border: 1px solid #aeb8c3; border-radius: 3px; background: rgba(255,255,255,0.9); cursor: pointer; color: #dc2626; }
.required { color: #dc2626; margin-left: 2px; }
.btn-primary, .btn-secondary { border-radius: 6px; padding: 8px 12px; border: 1px solid #2563eb; cursor: pointer; text-decoration: none; }
.btn-primary { background: #2563eb; color: #fff; width: 100%; justify-content: center; }
.btn-secondary { background: #fff; color: #2563eb; }
.result-summary { border: 1px solid #d1d5db; border-radius: 6px; padding: 10px; margin-bottom: 14px; background: #f9fafb; }
.result-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.result-badge.completed { background: #dbeafe; color: #1e40af; }
.result-badge.approved { background: #d1fae5; color: #065f46; }
.result-meta { font-size: 12px; color: #6b7280; line-height: 1.6; }
.result-fields { margin-top: 8px; border-top: 1px solid #e5e7eb; padding-top: 6px; }
.result-field-row { display: flex; gap: 6px; font-size: 12px; line-height: 1.8; }
.result-label { color: #374151; font-weight: 600; white-space: nowrap; min-width: 60px; }
.result-value { color: #111827; }
@media (max-width: 900px) { .input-grid { grid-template-columns: 1fr; } }
</style>




