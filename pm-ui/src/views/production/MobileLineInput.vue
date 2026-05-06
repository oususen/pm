<template>
  <div class="mobile-input">
    <!-- ヘッダー -->
    <div class="mobile-header">
      <h2>ライン作業記録</h2>
      <div class="header-info">
        <span class="date">{{ currentDate }}</span>
        <button class="btn-inspection-nav" @click="openEquipmentInspection">設備点検</button>
      </div>
    </div>

    <!-- ライン選択 -->
    <div class="section">
      <label class="label-required">ライン</label>
      <select v-model="selectedLineId" @change="onLineChange" class="input-large">
        <option value="">-- ラインを選択 --</option>
        <option v-for="line in lines" :key="line.id" :value="line.id">
          {{ line.line_code }} - {{ line.line_name }}
        </option>
      </select>
    </div>

    <!-- 記録タイプ選択 -->
    <div v-if="selectedLineId" class="section">
      <label class="label-required">記録タイプ</label>
      <div class="type-buttons">
        <button
          v-for="type in recordTypes"
          :key="type.value"
          @click="record.record_type = type.value"
          class="type-btn"
          :class="{ active: record.record_type === type.value }"
        >
          {{ type.label }}
        </button>
      </div>
    </div>

    <!-- 製品選択 -->
    <div v-if="record.record_type" class="section">
      <label :class="record.record_type === 'PRODUCTION' ? 'label-required' : ''">製品</label>
      <template v-if="plannedProducts.length">
        <select v-model="record.product_id" class="input-large">
          <option value="">-- 製品を選択 --</option>
          <option
            v-for="p in plannedProducts"
            :key="`${p.plan_date}-${p.product_code}`"
            :value="p.product"
          >
            {{ p.product_code }} - {{ p.product_name || '' }}（計画: {{ formatNumber(p.plan_qty || 0) }}）
          </option>
        </select>
        <button type="button" class="btn-link" @click="toggleManualProduct">
          {{ manualProduct ? '選択に戻る' : '手入力する' }}
        </button>
      </template>
      <template v-if="manualProduct || !plannedProducts.length">
        <input
          type="text"
          v-model="record.product_code"
          placeholder="品番を入力（例: YD60000000）"
          class="input-normal"
        />
        <div v-if="!plannedProducts.length" class="hint">
          本日の計画が未取得のため手入力になります（ライン需要展開が未実行の可能性があります）。
        </div>
      </template>
    </div>

    <!-- 生産記録フォーム -->
    <div v-if="record.record_type === 'PRODUCTION'" class="form-section">
      <h3 class="section-title">生産記録</h3>

      <!-- 生産数量 -->
      <div class="section">
        <label class="label-required">生産数量</label>
        <input
          type="number"
          v-model.number="record.qty"
          min="1"
          step="1"
          inputmode="numeric"
          class="input-large input-qty"
          placeholder="数量を入力"
        />
      </div>

      <!-- クイック入力ボタン -->
      <div class="quick-btns">
        <button
          v-for="preset in quickQtyPresets"
          :key="preset"
          @click="record.qty = preset"
          class="btn-quick"
        >
          {{ preset }}
        </button>
      </div>

      <!-- ロット番号 -->
      <div class="section">
        <label>ロット番号</label>
        <input
          type="text"
          v-model="record.batch_no"
          placeholder="ロット番号（任意）"
          class="input-normal"
        />
      </div>

      <!-- 作業者名 -->
      <div class="section">
        <label>作業者名</label>
        <input
          type="text"
          v-model="record.operator_name"
          placeholder="作業者名（任意）"
          class="input-normal"
        />
      </div>

      <!-- 備考 -->
      <div class="section">
        <label>備考</label>
        <textarea
          v-model="record.remarks"
          rows="3"
          placeholder="特記事項があれば入力"
          class="textarea-normal"
        ></textarea>
      </div>
    </div>

    <!-- 設備状態変更フォーム -->
    <div v-if="record.record_type === 'EQUIPMENT_STATE'" class="form-section">
      <h3 class="section-title">設備状態変更</h3>

      <div class="section">
        <label class="label-required">状態</label>
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

      <!-- 備考 -->
      <div class="section">
        <label>備考</label>
        <textarea
          v-model="record.remarks"
          rows="3"
          placeholder="状態変更の理由など"
          class="textarea-normal"
        ></textarea>
      </div>
    </div>

    <!-- 送信ボタン -->
    <div v-if="record.record_type" class="action-section">
      <button
        @click="submitRecord"
        :disabled="!canSubmit || submitting"
        class="btn-submit"
      >
        {{ submitting ? '送信中...' : '記録を登録' }}
      </button>
    </div>

    <!-- 最近の記録 -->
    <div v-if="selectedLineId && recentRecords.length" class="recent-section">
      <h3 class="section-title">最近の記録</h3>
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
import { useRouter } from 'vue-router'
import api from '@/api/client'

const router = useRouter()
const lines = ref([])
const selectedLineId = ref('')
const recentRecords = ref([])
const submitting = ref(false)
const plannedProducts = ref([])
const defaultProductId = ref(null)
const manualProduct = ref(false)

const record = ref({
  record_type: '',
  product_id: '',
  product_code: '',
  qty: null,
  equipment_state: '',
  batch_no: '',
  operator_name: '',
  remarks: '',
})

const recordTypes = [
  { value: 'PRODUCTION', label: '生産記録' },
  { value: 'EQUIPMENT_STATE', label: '設備状態変更' },
]

const equipmentStates = [
  { value: 'RUNNING', label: '運転中' },
  { value: 'IDLE', label: '待機' },
  { value: 'SETUP', label: '段取り中' },
  { value: 'MAINTENANCE', label: '保全中' },
  { value: 'BREAKDOWN', label: '故障' },
  { value: 'STOPPED', label: '停止' },
]

const quickQtyPresets = ref([10, 50, 100, 500])

const currentDate = computed(() => {
  return new Date().toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short'
  })
})

const currentDateYmd = computed(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
})

const canSubmit = computed(() => {
  if (!selectedLineId.value || !record.value.record_type) return false

  if (record.value.record_type === 'PRODUCTION') {
    const hasProduct = !!record.value.product_id || !!(record.value.product_code || '').trim()
    return record.value.qty > 0 && hasProduct
  }

  if (record.value.record_type === 'EQUIPMENT_STATE') {
    return !!record.value.equipment_state
  }

  return false
})

const onLineChange = () => {
  // ラインが変わったらフォームリセット
  resetForm()
  loadPlannedProducts()
  loadRecentRecords()
}

const resetForm = () => {
  record.value = {
    record_type: '',
    product_id: '',
    product_code: '',
    qty: null,
    equipment_state: '',
    batch_no: '',
    operator_name: '',
    remarks: '',
  }
  manualProduct.value = false
}

const submitRecord = async () => {
  if (!canSubmit.value) return

  submitting.value = true

  try {
    const data = {
      line_id: selectedLineId.value,
      record_type: record.value.record_type,
    }

    if (record.value.product_id) {
      data.product_id = record.value.product_id
    } else if ((record.value.product_code || '').trim()) {
      data.product_code = record.value.product_code.trim()
    }

    if (record.value.record_type === 'PRODUCTION') {
      data.qty = record.value.qty
      data.batch_no = record.value.batch_no
      data.operator_name = record.value.operator_name
    } else if (record.value.record_type === 'EQUIPMENT_STATE') {
      data.equipment_state = record.value.equipment_state
      data.qty = 0
    }

    data.remarks = record.value.remarks

    await api.lineRealtime.create(data)

    alert('記録を登録しました')
    resetForm()
    loadRecentRecords()
  } catch (error) {
    console.error('記録登録エラー:', error)
    alert('記録の登録に失敗しました')
  } finally {
    submitting.value = false
  }
}

const loadRecentRecords = async () => {
  if (!selectedLineId.value) return

  try {
    const res = await api.lineRealtime.list({
      line_id: selectedLineId.value,
      limit: 10,
    })
    recentRecords.value = res.data.results || res.data || []

    const lastProduction = recentRecords.value.find(r => r.record_type === 'PRODUCTION' && r.product)
    defaultProductId.value = lastProduction ? lastProduction.product : defaultProductId.value
  } catch (error) {
    console.error('最近の記録取得エラー:', error)
  }
}

const loadPlannedProducts = async () => {
  if (!selectedLineId.value) return

  plannedProducts.value = []
  try {
    const res = await api.lineDemands.list({
      line: selectedLineId.value,
      plan_date: currentDateYmd.value,
    })
    const items = res.data.results || res.data || []
    plannedProducts.value = Array.isArray(items) ? items : []

    if (plannedProducts.value.length === 1 && plannedProducts.value[0].product) {
      defaultProductId.value = plannedProducts.value[0].product
    }
  } catch (error) {
    console.error('本日の計画取得エラー:', error)
  }
}

const toggleManualProduct = () => {
  manualProduct.value = !manualProduct.value
  if (manualProduct.value) {
    record.value.product_id = ''
  } else {
    record.value.product_code = ''
  }
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatNumber = (value) => {
  if (value === null || value === undefined) return '0'
  return Number(value).toLocaleString()
}

const loadLines = async () => {
  try {
    const res = await api.lines.getLines()
    lines.value = res.data.results || res.data || []
  } catch (error) {
    console.error('ライン一覧取得エラー:', error)
    alert('ライン情報の取得に失敗しました')
  }
}

function openEquipmentInspection() {
  const lineId = selectedLineId.value || undefined
  router.push({
    path: '/quality/equipment-inspection/operation',
    query: lineId ? { line_id: String(lineId) } : {},
  })
}

onMounted(() => {
  loadLines()
})

watch(
  () => record.value.record_type,
  (type) => {
    if (!type) return
    if (!record.value.product_id && defaultProductId.value) {
      record.value.product_id = defaultProductId.value
    }
  }
)
</script>

<style scoped>
.mobile-input {
  max-width: 600px;
  margin: 0 auto;
  padding: 16px;
  background: #eef2f6;
  min-height: 100vh;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

.mobile-header {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.mobile-header h2 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #1f2a44;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: space-between;
  font-size: 13px;
  color: #64748b;
}
.btn-inspection-nav {
  height: 28px;
  padding: 0 10px;
  border: 1px solid #0e7490;
  background: #fff;
  color: #0e7490;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

.section {
  margin-bottom: 20px;
}

.section-title {
  margin: 20px 0 12px 0;
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
  padding: 12px;
  font-size: 15px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  box-sizing: border-box;
  font-family: inherit;
}

.input-large {
  font-size: 16px;
  font-weight: 600;
}

.input-qty {
  font-size: 24px !important;
  text-align: center;
  font-weight: 700;
}

.type-buttons,
.state-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
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
  gap: 8px;
  margin-bottom: 20px;
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
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.action-section {
  margin: 24px 0;
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
  padding: 16px;
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

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
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

.record-state {
  font-weight: 600;
  color: #4a7ae5;
}
</style>

