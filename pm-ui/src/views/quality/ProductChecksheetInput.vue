<template>
  <div class="page-container">
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

        <h2>出荷分</h2>
        <label>出荷日<input v-model="plannedShipDate" type="date" /></label>
        <label>台目<input v-model.number="shipmentUnitNo" type="number" min="1" /></label>
        <label>入力者<input v-model="completedByName" type="text" /></label>
        <button class="btn-primary" type="button" @click="saveCurrent" :disabled="saving || !canEditInput">{{ saving ? '保存中' : 'この1枚を保存' }}</button>
        <p v-if="!canEditInput" class="helper-text">閲覧のみ可能です（入力権限がありません）。</p>
        <p class="helper-text">出荷日と台目は次の1枚へ引き継がれます。</p>
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
              <input v-else v-model="responses[field.key]" type="text" :placeholder="field.placeholder" />
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
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
const plannedShipDate = ref('')
const shipmentUnitNo = ref('')
const completedByName = ref('')
const saving = ref(false)
const canAccessQuality = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) return hasPermission(user, resource, level)
  return hasPermission(user, 'quality', level)
}
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
  const target = records.value.find((item) => item.status === 'PENDING') || records.value[0]
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
      responses.value[field.key] = field.field_type === 'date' ? new Date().toISOString().slice(0, 10) : ''
    }
  })
  plannedShipDate.value = record.planned_ship_date || plannedShipDate.value || ''
  shipmentUnitNo.value = record.shipment_unit_no || shipmentUnitNo.value || ''
  completedByName.value = record.completed_by_name || completedByName.value || batch.value?.operator_name || ''
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

const goReturn = () => {
  const returnPath = route.query.return
  if (returnPath) {
    router.push(String(returnPath))
    return
  }
  router.push('/quality/product-checksheet/templates')
}

onMounted(loadBatch)
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
.record-chip.done { border-color: #059669; color: #047857; }
.record-chip.active { background: #eff6ff; border-color: #2563eb; color: #1d4ed8; }
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
.required { color: #dc2626; margin-left: 2px; }
.btn-primary, .btn-secondary { border-radius: 6px; padding: 8px 12px; border: 1px solid #2563eb; cursor: pointer; text-decoration: none; }
.btn-primary { background: #2563eb; color: #fff; width: 100%; justify-content: center; }
.btn-secondary { background: #fff; color: #2563eb; }
@media (max-width: 900px) { .input-grid { grid-template-columns: 1fr; } }
</style>
