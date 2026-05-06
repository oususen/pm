<template>
  <div class="camera-actual-page">
    <h2>実績入力（カメラ）</h2>

    <div class="panel">
      <div class="row">
        <label>ライン *</label>
        <select v-model="selectedLineId" :disabled="isCapturing" @change="onLineChange">
          <option value="">選択してください</option>
          <option v-for="line in lines" :key="line.id" :value="String(line.id)">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
      </div>
      <div class="row">
        <label>工程 *</label>
        <select v-model="selectedProcessId" :disabled="isCapturing || !selectedLineId" @change="onProcessChange">
          <option value="">選択してください</option>
          <option v-for="process in filteredProcesses" :key="process.id" :value="String(process.id)">
            {{ process.process_code }} - {{ process.process_name }}
          </option>
        </select>
      </div>
      <div class="row">
        <label>製品 *</label>
        <select v-model="selectedProductId" :disabled="isCapturing || !selectedProcessId">
          <option value="">選択してください</option>
          <option v-for="product in filteredProducts" :key="product.id" :value="String(product.id)">
            {{ product.product_code }} - {{ product.product_name }}
          </option>
        </select>
      </div>
      <div class="button-row">
        <button type="button" class="primary" :disabled="!canStart || isCapturing" @click="startCapture">
          カメラ開始
        </button>
        <button type="button" :disabled="!isCapturing" @click="stopCapture">
          カメラ停止
        </button>
        <button type="button" class="detect" :disabled="!isCapturing" @click="registerDetection">
          検知+1（PoC）
        </button>
      </div>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    </div>

    <div class="panel">
      <video ref="videoEl" autoplay playsinline muted class="preview"></video>
      <div class="stats">
        <div>検知状態: {{ statusLabel }}</div>
        <div>セッション実績: {{ sessionCount }}</div>
        <div>当日累計実績: {{ dailyCount }}</div>
        <div>未送信件数: {{ queue.length }}</div>
        <div>最終反映時刻: {{ lastAcceptedAt || "-" }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import api from "@/api/client"

const QUEUE_STORAGE_KEY = "camera-actual-queue-v1"
const DEVICE_STORAGE_KEY = "camera-actual-device-id-v1"

const lines = ref([])
const processes = ref([])
const products = ref([])

const selectedLineId = ref("")
const selectedProcessId = ref("")
const selectedProductId = ref("")

const isCapturing = ref(false)
const statusLabel = ref("待機中")
const sessionCount = ref(0)
const dailyCount = ref(0)
const lastAcceptedAt = ref("")
const errorMessage = ref("")
const queue = ref([])

const videoEl = ref(null)
let mediaStream = null
let retryTimer = null

const canStart = computed(() => Boolean(selectedLineId.value && selectedProcessId.value && selectedProductId.value))

const filteredProcesses = computed(() =>
  processes.value.filter((row) => String(row.line) === String(selectedLineId.value))
)

const filteredProducts = computed(() =>
  products.value.filter((row) => {
    const lineOk = !row.line || String(row.line) === String(selectedLineId.value)
    const processOk = !row.process || String(row.process) === String(selectedProcessId.value)
    return lineOk && processOk
  })
)

const getDeviceId = () => {
  const existing = localStorage.getItem(DEVICE_STORAGE_KEY)
  if (existing) return existing
  const generated =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `device-${Date.now()}-${Math.floor(Math.random() * 100000)}`
  localStorage.setItem(DEVICE_STORAGE_KEY, generated)
  return generated
}

const buildEventId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `evt-${Date.now()}-${Math.floor(Math.random() * 100000)}`

const enqueue = (item) => {
  queue.value.push(item)
  localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue.value))
}

const dequeueAt = (index) => {
  queue.value.splice(index, 1)
  localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue.value))
}

const loadQueue = () => {
  const raw = localStorage.getItem(QUEUE_STORAGE_KEY)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    queue.value = Array.isArray(parsed) ? parsed : []
  } catch (error) {
    queue.value = []
  }
}

const fetchMasters = async () => {
  const [lineRes, processRes, productRes] = await Promise.all([
    api.lines.getProductionLines(),
    api.processes.getProcesses({ is_active: true }),
    api.products.getProducts({ is_active: true, page_size: 2000 }),
  ])
  lines.value = lineRes.data.results || lineRes.data || []
  processes.value = processRes.data.results || processRes.data || []
  products.value = productRes.data.results || productRes.data || []
}

const refreshDailyCount = async () => {
  if (!selectedLineId.value || !selectedProcessId.value || !selectedProductId.value) return
  const res = await api.cameraActuals.getDaily({
    line_id: Number(selectedLineId.value),
    process_id: Number(selectedProcessId.value),
    product_id: Number(selectedProductId.value),
  })
  dailyCount.value = Number(res.data.actual_count || 0)
}

const postOneEvent = async (payload) => {
  const res = await api.cameraActuals.createEvent(payload)
  if (res.data?.accepted) {
    dailyCount.value = Number(res.data.total_count || dailyCount.value)
    lastAcceptedAt.value = new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }
}

const flushQueue = async () => {
  if (!queue.value.length) return
  for (let i = 0; i < queue.value.length; i += 1) {
    const item = queue.value[i]
    const ageMs = Date.now() - new Date(item.event_at).getTime()
    if (ageMs > 24 * 60 * 60 * 1000) {
      continue
    }
    try {
      await postOneEvent(item)
      dequeueAt(i)
      i -= 1
    } catch (error) {
      break
    }
  }
}

const scheduleFlush = () => {
  if (retryTimer) clearInterval(retryTimer)
  retryTimer = setInterval(() => {
    flushQueue().catch(() => {})
  }, 5000)
}

const registerDetection = async () => {
  if (!isCapturing.value) return
  const payload = {
    camera_event_id: buildEventId(),
    line_id: Number(selectedLineId.value),
    process_id: Number(selectedProcessId.value),
    product_id: Number(selectedProductId.value),
    event_at: new Date().toISOString(),
    count: 1,
    device_id: getDeviceId(),
    confidence: 0.9,
  }
  try {
    await postOneEvent(payload)
    sessionCount.value += 1
    statusLabel.value = "取得中"
    errorMessage.value = ""
  } catch (error) {
    enqueue(payload)
    sessionCount.value += 1
    statusLabel.value = "通信待機"
    errorMessage.value = "通信エラーのためキューに退避しました。"
  }
}

const stopCapture = () => {
  isCapturing.value = false
  statusLabel.value = "待機中"
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  if (videoEl.value) {
    videoEl.value.srcObject = null
  }
}

const startCapture = async () => {
  errorMessage.value = ""
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    })
    if (videoEl.value) {
      videoEl.value.srcObject = mediaStream
    }
    isCapturing.value = true
    statusLabel.value = "取得中"
    sessionCount.value = 0
    await refreshDailyCount()
  } catch (error) {
    statusLabel.value = "エラー"
    errorMessage.value = "カメラ起動に失敗しました。端末権限を確認してください。"
  }
}

const onLineChange = () => {
  selectedProcessId.value = ""
  selectedProductId.value = ""
}

const onProcessChange = () => {
  selectedProductId.value = ""
}

onMounted(async () => {
  loadQueue()
  scheduleFlush()
  try {
    await fetchMasters()
  } catch (error) {
    errorMessage.value = "初期データの取得に失敗しました。"
  }
  if (queue.value.length) {
    flushQueue().catch(() => {})
  }
})

onBeforeUnmount(() => {
  stopCapture()
  if (retryTimer) clearInterval(retryTimer)
})
</script>

<style scoped>
.camera-actual-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 12px;
}
.panel {
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
}
.row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
select,
button {
  height: 36px;
  font-size: 14px;
}
.button-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
button.primary {
  background: #0369a1;
  color: #fff;
  border: none;
  padding: 0 12px;
  border-radius: 6px;
}
button.detect {
  background: #14532d;
  color: #fff;
  border: none;
  padding: 0 12px;
  border-radius: 6px;
}
.preview {
  width: 100%;
  max-height: 360px;
  background: #111827;
  border-radius: 6px;
}
.stats {
  margin-top: 8px;
  display: grid;
  gap: 4px;
}
.error {
  color: #dc2626;
  margin: 0;
}
</style>
