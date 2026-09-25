<template>
  <div class="ops-page">
    <div class="mode-bar">
      <button v-for="m in modes" :key="m.key" :class="['mode-btn', m.key, { active: mode === m.key }]" @click="switchMode(m.key)">
        {{ m.label }}
      </button>
    </div>

    <!-- 品目の特定 -->
    <div class="scan-row">
      <input v-model="qrText" class="code-input" placeholder="コードまたは品名を入力" @keyup.enter="lookup(qrText)" />
      <button class="btn-primary" @click="lookup(qrText)">検索</button>
      <button class="btn-qr" @click="showScanner = true">📷 QR</button>
    </div>
    <p v-if="lookupError" class="error-text">{{ lookupError }}</p>

    <div v-if="candidates.length" class="candidates">
      <div class="candidates-header">{{ candidates.length }}件 該当 — 選択してください</div>
      <div v-for="c in candidates" :key="c.id" class="candidate-row" @click="selectCandidate(c)">
        <img v-if="c.image_url" :src="c.image_url" class="candidate-img" alt="" />
        <div v-else class="candidate-img candidate-no-img">-</div>
        <div class="candidate-info">
          <div class="candidate-name">{{ c.name }}</div>
          <div class="candidate-sub">{{ c.code }} | 在庫: {{ c.stock_quantity }} {{ c.unit }}</div>
        </div>
      </div>
    </div>

    <div v-if="item" class="item-card">
      <img v-if="item.image_url" :src="item.image_url" class="item-img" alt="" @click="showEdit = !showEdit" />
      <div v-else class="item-img-placeholder" @click="triggerImageUpload">📷</div>
      <div class="item-info">
        <div class="item-name">{{ item.name }} <button class="edit-toggle" @click="showEdit = !showEdit">✏️</button></div>
        <div class="item-line">コード: {{ item.code }} | 保管場所: {{ item.storage_location || '-' }}</div>
        <div class="item-line">
          在庫数: <b :class="{ shortage: item.is_shortage }">{{ item.stock_quantity }} {{ item.unit }}</b>
          | 安全在庫: {{ item.safety_stock }} | 注文状態: {{ item.order_status_label }}
        </div>
      </div>
    </div>
    <div v-if="item && showEdit" class="edit-panel">
      <label>画像
        <input ref="imageInput" type="file" accept="image/*" capture="environment" @change="uploadImage" />
      </label>
      <div class="edit-row">
        <label class="edit-field">品名<input v-model="editForm.name" /></label>
        <label class="edit-field">単位<input v-model="editForm.unit" class="short" /></label>
      </div>
      <div class="edit-row">
        <label class="edit-field">カテゴリ<input v-model="editForm.category" /></label>
        <label class="edit-field">保管場所<input v-model="editForm.storage_location" /></label>
      </div>
      <div class="edit-row">
        <label class="edit-field">安全在庫<input v-model.number="editForm.safety_stock" type="number" class="short" /></label>
        <label class="edit-field">発注単位<input v-model.number="editForm.order_unit" type="number" class="short" /></label>
        <label class="edit-field">単価<input v-model="editForm.unit_price" type="number" step="0.01" class="short" /></label>
      </div>
      <div class="adjust-row">
        <label class="edit-field">在庫調整（現在: {{ item.stock_quantity }}）
          <div class="qty-row">
            <button class="qty-btn" @click="adjustQty -= 1">−</button>
            <input v-model.number="adjustQty" type="number" inputmode="numeric" />
            <button class="qty-btn" @click="adjustQty += 1">＋</button>
          </div>
        </label>
        <button class="btn-adjust" :disabled="editSaving || adjustQty === 0" @click="submitAdjustment">調整実行</button>
      </div>
      <div class="edit-actions">
        <button class="btn-save" :disabled="editSaving" @click="saveEdit">{{ editSaving ? '保存中...' : '保存' }}</button>
        <button class="btn-cancel" @click="showEdit = false">閉じる</button>
      </div>
      <p v-if="editMessage" class="result-text">{{ editMessage }}</p>
      <p v-if="editError" class="error-text">{{ editError }}</p>
    </div>

    <!-- 入力 -->
    <div v-if="item" class="form">
      <label>数量（{{ item.unit || '個' }}）
        <div class="qty-row">
          <button class="qty-btn" @click="quantity = Math.max(1, quantity - 1)">−</button>
          <input v-model.number="quantity" type="number" min="1" inputmode="numeric" />
          <button class="qty-btn" @click="quantity += 1">＋</button>
        </div>
      </label>
      <div v-if="mode === 'inbound'" class="inbound-worker">入庫者: {{ authState.user?.last_name || authState.user?.username }}</div>
      <template v-if="mode !== 'inbound'">
        <div class="filter-row">
          <label class="filter-label">係
            <select v-model="filterGroupId" @change="onGroupChange">
              <option :value="null">すべて</option>
              <option v-for="g in groupOptions" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </label>
          <label class="filter-label">班
            <select v-model="filterTeamId" @change="onTeamChange">
              <option :value="null">すべて</option>
              <option v-for="t in filteredTeamOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </label>
          <label class="filter-label">グループ
            <select v-model="filterUnitId" @change="onFilterChange">
              <option :value="null">すべて</option>
              <option v-for="u in filteredUnitOptions" :key="u.id" :value="u.id">{{ u.name }}</option>
            </select>
          </label>
        </div>
        <label>{{ mode === 'request' ? '依頼者' : '作業者' }}
          <select v-model="workerId">
            <option v-for="w in workers" :key="w.id" :value="w.id">
              {{ w.employee_code ? `${w.employee_code} ` : '' }}{{ w.name }}{{ w.team_name ? `（${w.team_name}）` : '' }}
            </option>
          </select>
        </label>
        <label v-if="mode === 'outbound'">使用ライン
          <select v-model="usageLine">
            <option value="">（未選択）</option>
            <option v-for="l in lineOptions" :key="l.id" :value="l.line_name">{{ l.line_code }} {{ l.line_name }}</option>
          </select>
        </label>
      </template>
      <label v-if="mode === 'request'">納期
        <select v-model="deadline">
          <option v-for="d in deadlineOptions" :key="d" :value="d">{{ d }}</option>
        </select>
      </label>
      <p v-if="mode === 'request' && item.order_status" class="warn-text">
        この品目には未完了の依頼があります（注文状態: {{ item.order_status_label }}）
      </p>
      <label>備考<input v-model="note" /></label>
      <p v-if="submitError" class="error-text">{{ submitError }}</p>
      <button :class="['submit-btn', mode]" :disabled="submitting" @click="submit">
        {{ submitting ? '登録中...' : `${currentMode.label}を確定` }}
      </button>
    </div>

    <p v-if="resultMessage" class="result-text">{{ resultMessage }}</p>

    <QrScanner v-if="showScanner" @scanned="onScanned" @close="showScanner = false" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import QrScanner from './QrScanner.vue'
import { errorMessage } from './consumableUtils'

const modes = [
  { key: 'outbound', label: '出庫' },
  { key: 'inbound', label: '入庫' },
  { key: 'request', label: '注文依頼' },
]

const route = useRoute()
const mode = ref(modes.some((m) => m.key === route.query.mode) ? route.query.mode : 'outbound')
const currentMode = computed(() => modes.find((m) => m.key === mode.value))

const qrText = ref('')
const item = ref(null)
const lookupError = ref('')
const showScanner = ref(false)
const candidates = ref([])

const workers = ref([])
const groupOptions = ref([])
const teamOptions = ref([])
const unitOptions = ref([])
const filterGroupId = ref(null)
const filterTeamId = ref(null)
const filterUnitId = ref(null)
const lineOptions = ref([])
const workerId = ref(authState.user?.id || null)
const quantity = ref(1)
const usageLine = ref('')
const deadlineOptions = ['最短', '通常', '余裕あり']
const deadline = ref('通常')
const note = ref('')
const submitting = ref(false)
const submitError = ref('')
const resultMessage = ref('')

const showEdit = ref(false)
const imageInput = ref(null)
const editForm = ref({})
const editSaving = ref(false)
const editMessage = ref('')
const editError = ref('')
const adjustQty = ref(0)

function resetInputs() {
  quantity.value = 1
  usageLine.value = ''
  deadline.value = '通常'
  note.value = ''
  submitError.value = ''
}

function switchMode(key) {
  mode.value = key
  submitError.value = ''
  resultMessage.value = ''
}

async function lookup(raw) {
  const text = (raw || '').trim()
  if (!text) return
  lookupError.value = ''
  resultMessage.value = ''
  item.value = null
  candidates.value = []
  try {
    const data = (await api.consumables.lookupByQr(text)).data
    if (data.multiple) {
      candidates.value = data.results
    } else {
      item.value = data
      qrText.value = item.value.code
      resetInputs()
      initEditForm()
      showEdit.value = false
    }
  } catch (err) {
    lookupError.value = errorMessage(err)
  }
}

function onScanned(raw) {
  showScanner.value = false
  lookup(raw)
}

async function selectCandidate(c) {
  candidates.value = []
  try {
    item.value = (await api.consumables.getItem(c.id)).data
    qrText.value = item.value.code
    resetInputs()
    initEditForm()
    showEdit.value = false
  } catch (err) {
    lookupError.value = errorMessage(err)
  }
}

function initEditForm() {
  if (!item.value) return
  const i = item.value
  editForm.value = {
    name: i.name, unit: i.unit || '', category: i.category || '',
    storage_location: i.storage_location || '', safety_stock: i.safety_stock,
    order_unit: i.order_unit, unit_price: i.unit_price,
  }
  editMessage.value = ''
  editError.value = ''
  adjustQty.value = 0
}

function triggerImageUpload() {
  showEdit.value = true
  setTimeout(() => imageInput.value?.click(), 100)
}

async function uploadImage(e) {
  const file = e.target.files?.[0]
  if (!file || !item.value) return
  editError.value = ''
  editSaving.value = true
  try {
    const fd = new FormData()
    fd.append('image', file)
    const res = (await api.consumables.uploadItemImage(item.value.id, fd)).data
    item.value.image_url = res.image_url
    editMessage.value = '画像をアップロードしました'
  } catch (err) {
    editError.value = errorMessage(err)
  } finally {
    editSaving.value = false
  }
}

async function submitAdjustment() {
  if (!item.value || adjustQty.value === 0) return
  editSaving.value = true
  editError.value = ''
  editMessage.value = ''
  try {
    const res = (await api.consumables.adjustment({
      consumable: item.value.id,
      quantity: adjustQty.value,
    })).data
    item.value.stock_quantity = res.stock_after
    const sign = adjustQty.value > 0 ? '+' : ''
    editMessage.value = `在庫調整しました: ${sign}${adjustQty.value} → 在庫: ${res.stock_after}`
    adjustQty.value = 0
  } catch (err) {
    editError.value = errorMessage(err)
  } finally {
    editSaving.value = false
  }
}

async function saveEdit() {
  if (!item.value) return
  editSaving.value = true
  editError.value = ''
  editMessage.value = ''
  try {
    const res = (await api.consumables.updateItem(item.value.id, editForm.value)).data
    Object.assign(item.value, res)
    editMessage.value = '保存しました'
  } catch (err) {
    editError.value = errorMessage(err)
  } finally {
    editSaving.value = false
  }
}

async function submit() {
  if (!item.value) return
  if (!Number.isInteger(quantity.value) || quantity.value < 1) {
    submitError.value = '数量は1以上の整数で入力してください'
    return
  }
  if (mode.value !== 'inbound' && !workerId.value) {
    submitError.value = '作業者を選択してください'
    return
  }
  submitting.value = true
  submitError.value = ''
  try {
    if (mode.value === 'request') {
      const req = (await api.consumables.createRequest({
        consumable: item.value.id,
        quantity: quantity.value,
        requester: workerId.value,
        deadline: deadline.value,
        note: note.value,
      })).data
      resultMessage.value = `注文依頼を登録しました: ${req.consumable_name} ${req.quantity}${req.unit}（納期: ${req.deadline}）`
    } else {
      const payload = {
        consumable: item.value.id,
        quantity: quantity.value,
        worker: mode.value === 'inbound' ? authState.user.id : workerId.value,
        usage_line: mode.value === 'outbound' ? usageLine.value : '',
        note: note.value,
      }
      const mv = (mode.value === 'outbound'
        ? await api.consumables.outbound(payload)
        : await api.consumables.inbound(payload)).data
      resultMessage.value = `${currentMode.value.label}しました: ${mv.consumable_name} ${mv.quantity}${mv.unit}（処理後在庫: ${mv.stock_after}）`
    }
    item.value = null
    qrText.value = ''
    resetInputs()
  } catch (err) {
    submitError.value = errorMessage(err)
  } finally {
    submitting.value = false
  }
}

async function fetchWorkers() {
  const params = {}
  if (filterGroupId.value) params.group = filterGroupId.value
  if (filterTeamId.value) params.team = filterTeamId.value
  if (filterUnitId.value) params.unit = filterUnitId.value
  const res = (await api.consumables.listWorkers(params)).data
  workers.value = res.workers
  if (!groupOptions.value.length) groupOptions.value = res.groups
  if (!teamOptions.value.length) teamOptions.value = res.teams
  if (!unitOptions.value.length) unitOptions.value = res.units
  if (!lineOptions.value.length) lineOptions.value = res.lines
  if (!workers.value.some((w) => w.id === workerId.value)) {
    workerId.value = workers.value.length ? workers.value[0].id : null
  }
}

const filteredTeamOptions = computed(() => {
  if (!filterGroupId.value) return teamOptions.value
  return teamOptions.value.filter((t) => t.parent_id === filterGroupId.value)
})

const filteredUnitOptions = computed(() => {
  if (!filterTeamId.value) return unitOptions.value
  return unitOptions.value.filter((u) => u.parent_id === filterTeamId.value)
})

function onGroupChange() {
  if (filterTeamId.value && !filteredTeamOptions.value.some((t) => t.id === filterTeamId.value)) {
    filterTeamId.value = null
  }
  if (filterUnitId.value && !filteredUnitOptions.value.some((u) => u.id === filterUnitId.value)) {
    filterUnitId.value = null
  }
  fetchWorkers()
}

function onTeamChange() {
  if (filterUnitId.value && !filteredUnitOptions.value.some((u) => u.id === filterUnitId.value)) {
    filterUnitId.value = null
  }
  fetchWorkers()
}

function onFilterChange() {
  fetchWorkers()
}

onMounted(async () => {
  await fetchWorkers()
  const seikan = groupOptions.value.find((g) => g.name === '製缶係')
  if (seikan) {
    filterGroupId.value = seikan.id
    await fetchWorkers()
  }
  if (authState.user?.id && workers.value.some((w) => w.id === authState.user.id)) {
    workerId.value = authState.user.id
  }
  if (route.query.code) lookup(String(route.query.code))
})
</script>

<style scoped>
.ops-page { padding: 10px; max-width: 560px; margin: 0 auto; }
.mode-bar { display: flex; gap: 6px; margin-bottom: 8px; }
.mode-btn { flex: 1; padding: 10px; font-size: 1.05em; border: 2px solid #ccc; border-radius: 6px; background: #f5f5f5; cursor: pointer; }
.mode-btn.active.outbound { background: #e65100; border-color: #e65100; color: #fff; }
.mode-btn.active.inbound { background: #2e7d32; border-color: #2e7d32; color: #fff; }
.mode-btn.active.request { background: #1565c0; border-color: #1565c0; color: #fff; }
.scan-row { display: flex; gap: 6px; }
.code-input { flex: 1; padding: 8px; font-size: 1em; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; }
.btn-qr { background: #37474f; color: #fff; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; }
.item-card { display: flex; gap: 10px; margin-top: 10px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; background: #fff; }
.item-img { width: 72px; height: 72px; object-fit: cover; border-radius: 4px; }
.item-name { font-weight: 700; font-size: 1.05em; }
.item-line { font-size: 0.85em; color: #444; }
.shortage { color: #c62828; }
.form { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
.form label { display: flex; flex-direction: column; gap: 2px; font-size: 0.9em; }
.form input, .form select { padding: 8px; font-size: 1em; }
.candidates { margin-top: 8px; border: 1px solid #ddd; border-radius: 6px; background: #fff; max-height: 540px; overflow-y: auto; }
.candidates-header { padding: 6px 8px; font-size: 0.85em; color: #555; border-bottom: 1px solid #eee; }
.candidate-row { display: flex; align-items: center; gap: 10px; padding: 10px; cursor: pointer; border-bottom: 1px solid #f0f0f0; }
.candidate-row:last-child { border-bottom: none; }
.candidate-row:active { background: #e3f2fd; }
.candidate-img { width: 80px; height: 80px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }
.candidate-no-img { display: flex; align-items: center; justify-content: center; background: #eee; color: #999; font-size: 0.8em; }
.candidate-name { font-weight: 600; font-size: 1.05em; }
.candidate-sub { font-size: 0.85em; color: #666; }
.item-img-placeholder { width: 72px; height: 72px; display: flex; align-items: center; justify-content: center; font-size: 2em; background: #eee; border-radius: 4px; cursor: pointer; }
.edit-toggle { background: none; border: none; cursor: pointer; font-size: 0.9em; padding: 0 4px; }
.edit-panel { margin-top: 6px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; background: #fafafa; display: flex; flex-direction: column; gap: 6px; }
.edit-panel label { display: flex; flex-direction: column; gap: 2px; font-size: 0.85em; }
.edit-panel input { padding: 6px; font-size: 0.95em; }
.edit-panel input.short { max-width: 100px; }
.edit-row { display: flex; gap: 8px; }
.edit-field { flex: 1; display: flex; flex-direction: column; gap: 2px; font-size: 0.85em; }
.adjust-row { display: flex; gap: 8px; align-items: flex-end; }
.adjust-row .edit-field { flex: 1; }
.adjust-row .qty-row input { text-align: center; }
.btn-adjust { background: #e65100; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; white-space: nowrap; height: fit-content; }
.btn-adjust:disabled { opacity: 0.6; }
.edit-actions { display: flex; gap: 8px; }
.btn-save { background: #1565c0; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.btn-save:disabled { opacity: 0.6; }
.btn-cancel { background: #757575; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.inbound-worker { font-size: 0.9em; color: #333; padding: 4px 0; }
.filter-row { display: flex; gap: 8px; }
.filter-label { flex: 1; display: flex; flex-direction: column; gap: 2px; font-size: 0.85em; color: #555; }
.filter-label select { padding: 6px; font-size: 0.95em; }
.qty-row { display: flex; gap: 6px; }
.qty-row input { flex: 1; text-align: center; }
.qty-btn { width: 48px; font-size: 1.3em; border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5; }
.submit-btn { padding: 12px; font-size: 1.1em; font-weight: 700; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.submit-btn.outbound { background: #e65100; }
.submit-btn.inbound { background: #2e7d32; }
.submit-btn.request { background: #1565c0; }
.warn-text { color: #e65100; font-size: 0.85em; margin: 0; }
.submit-btn:disabled { opacity: 0.6; }
.error-text { color: #c62828; white-space: pre-wrap; font-size: 0.9em; }
.result-text { margin-top: 10px; padding: 8px; background: #e8f5e9; border-radius: 4px; }
</style>
