<template>
  <div class="ops-page">
    <div class="mode-bar">
      <button v-for="m in modes" :key="m.key" :class="['mode-btn', m.key, { active: mode === m.key }]" @click="switchMode(m.key)">
        {{ m.label }}
      </button>
    </div>

    <!-- 品目の特定 -->
    <div class="scan-row">
      <input v-model="qrText" class="code-input" placeholder="コードを入力 または QR読取" @keyup.enter="lookup(qrText)" />
      <button class="btn-primary" @click="lookup(qrText)">検索</button>
      <button class="btn-qr" @click="showScanner = true">📷 QR</button>
    </div>
    <p v-if="lookupError" class="error-text">{{ lookupError }}</p>

    <div v-if="item" class="item-card">
      <img v-if="item.image_url" :src="item.image_url" class="item-img" alt="" />
      <div class="item-info">
        <div class="item-name">{{ item.name }}</div>
        <div class="item-line">コード: {{ item.code }} | 保管場所: {{ item.storage_location || '-' }}</div>
        <div class="item-line">
          在庫数: <b :class="{ shortage: item.is_shortage }">{{ item.stock_quantity }} {{ item.unit }}</b>
          | 安全在庫: {{ item.safety_stock }} | 注文状態: {{ item.order_status_label }}
        </div>
      </div>
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
      <label>作業者
        <select v-model="workerId">
          <option v-for="w in workers" :key="w.id" :value="w.id">
            {{ w.employee_code ? `${w.employee_code} ` : '' }}{{ w.name }}{{ w.team_name ? `（${w.team_name}）` : '' }}
          </option>
        </select>
      </label>
      <label v-if="mode === 'outbound'">使用ライン<input v-model="usageLine" /></label>
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
]

const route = useRoute()
const mode = ref(modes.some((m) => m.key === route.query.mode) ? route.query.mode : 'outbound')
const currentMode = computed(() => modes.find((m) => m.key === mode.value))

const qrText = ref('')
const item = ref(null)
const lookupError = ref('')
const showScanner = ref(false)

const workers = ref([])
const workerId = ref(authState.user?.id || null)
const quantity = ref(1)
const usageLine = ref('')
const note = ref('')
const submitting = ref(false)
const submitError = ref('')
const resultMessage = ref('')

function resetInputs() {
  quantity.value = 1
  usageLine.value = ''
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
  try {
    item.value = (await api.consumables.lookupByQr(text)).data
    qrText.value = item.value.code
    resetInputs()
  } catch (err) {
    lookupError.value = errorMessage(err)
  }
}

function onScanned(raw) {
  showScanner.value = false
  lookup(raw)
}

async function submit() {
  if (!item.value) return
  if (!Number.isInteger(quantity.value) || quantity.value < 1) {
    submitError.value = '数量は1以上の整数で入力してください'
    return
  }
  if (!workerId.value) {
    submitError.value = '作業者を選択してください'
    return
  }
  submitting.value = true
  submitError.value = ''
  const payload = {
    consumable: item.value.id,
    quantity: quantity.value,
    worker: workerId.value,
    usage_line: mode.value === 'outbound' ? usageLine.value : '',
    note: note.value,
  }
  try {
    const res = mode.value === 'outbound'
      ? await api.consumables.outbound(payload)
      : await api.consumables.inbound(payload)
    const mv = res.data
    resultMessage.value = `${currentMode.value.label}しました: ${mv.consumable_name} ${mv.quantity}${mv.unit}（処理後在庫: ${mv.stock_after}）`
    item.value = null
    qrText.value = ''
    resetInputs()
  } catch (err) {
    submitError.value = errorMessage(err)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  workers.value = (await api.consumables.listWorkers()).data
  if (route.query.code) lookup(String(route.query.code))
})
</script>

<style scoped>
.ops-page { padding: 10px; max-width: 560px; margin: 0 auto; }
.mode-bar { display: flex; gap: 6px; margin-bottom: 8px; }
.mode-btn { flex: 1; padding: 10px; font-size: 1.05em; border: 2px solid #ccc; border-radius: 6px; background: #f5f5f5; cursor: pointer; }
.mode-btn.active.outbound { background: #e65100; border-color: #e65100; color: #fff; }
.mode-btn.active.inbound { background: #2e7d32; border-color: #2e7d32; color: #fff; }
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
.qty-row { display: flex; gap: 6px; }
.qty-row input { flex: 1; text-align: center; }
.qty-btn { width: 48px; font-size: 1.3em; border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5; }
.submit-btn { padding: 12px; font-size: 1.1em; font-weight: 700; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.submit-btn.outbound { background: #e65100; }
.submit-btn.inbound { background: #2e7d32; }
.submit-btn:disabled { opacity: 0.6; }
.error-text { color: #c62828; white-space: pre-wrap; font-size: 0.9em; }
.result-text { margin-top: 10px; padding: 8px; background: #e8f5e9; border-radius: 4px; }
</style>
