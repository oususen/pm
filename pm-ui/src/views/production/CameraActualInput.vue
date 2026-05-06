<template>
  <div class="camera-actual-page">
    <h2>実績入力（カメラ）</h2>

    <div class="panel">
      <div class="row">
        <label>ライン *</label>
        <select v-model="selectedLineId" @change="onLineChange">
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
        <select v-model="captureMode" class="mode-select">
          <option value="auto">自動検知（YOLO PoC）</option>
          <option value="manual">手動検知（PoC）</option>
        </select>
        <button type="button" class="primary" :disabled="!canStart || isCapturing" @click="startCapture">
          カメラ開始
        </button>
        <button type="button" :disabled="!isCapturing" @click="stopCapture">
          カメラ停止
        </button>
        <button v-if="captureMode === 'manual'" type="button" class="detect" :disabled="!isCapturing" @click="registerDetection">
          検知+1（PoC）
        </button>
      </div>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <div class="tuning-grid">
        <label>送信間隔ms <input type="number" v-model.number="tuning.frame_interval_ms" @change="saveTuning" /></label>
        <label>ライン位置(0-1) <input type="number" step="0.01" v-model.number="tuning.line_position_ratio" @change="saveTuning" /></label>
        <label>ライン余白(0-1) <input type="number" step="0.01" v-model.number="tuning.side_margin_ratio" @change="saveTuning" /></label>
        <label>人物下側比率 <input type="number" step="0.01" v-model.number="tuning.person_bottom_ratio" @change="saveTuning" /></label>
        <label>最低Y比率 <input type="number" step="0.01" v-model.number="tuning.min_y_ratio" @change="saveTuning" /></label>
        <label>YOLO閾値 <input type="number" step="0.01" v-model.number="tuning.yolo_confidence" @change="saveTuning" /></label>
        <label>重複防止秒 <input type="number" step="0.1" v-model.number="tuning.dedup_seconds" @change="saveTuning" /></label>
        <label>動体閾値比率 <input type="number" step="0.001" v-model.number="tuning.motion_threshold_ratio" @change="saveTuning" /></label>
      </div>
    </div>

    <div class="panel">
      <h3 class="sub-title">製品形状学習（PoC）</h3>
      <div class="train-row">
        <input type="file" accept=".zip" @change="onDatasetFileChange" />
        <button type="button" @click="uploadDataset" :disabled="!datasetZipFile || trainingState === 'running'">データセットZIPアップロード</button>
      </div>
      <div class="train-row">
        <input type="file" accept="image/*" multiple @change="onPhotoFilesChange" />
        <label>写真ラベル
          <input type="text" v-model="photoLabelName" placeholder="製品コード" />
        </label>
        <button type="button" @click="uploadPhotos" :disabled="!photoFiles.length || trainingState === 'running'">写真をそのまま取込</button>
      </div>
      <div class="train-row">
        <label>epoch <input type="number" v-model.number="trainingEpochs" min="1" max="300" /></label>
        <label>imgsz <input type="number" v-model.number="trainingImgsz" min="160" max="1920" step="32" /></label>
        <button type="button" class="primary" @click="startShapeTraining" :disabled="trainingState === 'running'">学習開始</button>
      </div>
      <div class="train-status">
        <div>状態: {{ trainingState }}</div>
        <div>メッセージ: {{ trainingMessage || "-" }}</div>
        <div>データセット: {{ trainingDatasetDir || "-" }}</div>
        <div>モデル: {{ trainingModelPath || "-" }}</div>
      </div>
    </div>

    <div class="panel">
      <div class="preview-wrap">
      <video ref="videoEl" autoplay playsinline muted class="preview"></video>
      <div class="cross-line"></div>
      </div>
      <canvas ref="captureCanvasEl" class="hidden-canvas"></canvas>
      <div class="stats">
        <div>検知状態: {{ statusLabel }}</div>
        <div>期待形状: {{ expectedShapeCode || "-" }} / 推論: {{ lastShapeCode || "-" }} / 一致: {{ lastShapeMatch ? "OK" : "NG" }}</div>
        <div>セッション実績: {{ sessionCount }}</div>
        <div>セッション通過数: {{ sessionPassCount }}</div>
        <div>当日累計実績: {{ dailyCount }}</div>
        <div>未送信件数: {{ queue.length }}</div>
        <div>最終反映時刻: {{ lastAcceptedAt || "-" }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import api from "@/api/client"

const QUEUE_STORAGE_KEY = "camera-actual-queue-v1"
const DEVICE_STORAGE_KEY = "camera-actual-device-id-v1"
const TUNE_STORAGE_KEY = "camera-actual-tuning-v1"

const lines = ref([])
const processes = ref([])
const products = ref([])

const selectedLineId = ref("")
const selectedProcessId = ref("")
const selectedProductId = ref("")

const isCapturing = ref(false)
const captureMode = ref("auto")
const statusLabel = ref("待機中")
const sessionCount = ref(0)
const sessionPassCount = ref(0)
const lastShapeCode = ref("")
const expectedShapeCode = ref("")
const lastShapeMatch = ref(false)
const dailyCount = ref(0)
const lastAcceptedAt = ref("")
const errorMessage = ref("")
const queue = ref([])
const tuning = ref({
  line_position_ratio: 0.5,
  side_margin_ratio: 0.03,
  person_bottom_ratio: 0.78,
  min_y_ratio: 0.45,
  yolo_confidence: 0.5,
  dedup_seconds: 1.2,
  motion_threshold_ratio: 0.01,
  frame_interval_ms: 1200,
})

const videoEl = ref(null)
const captureCanvasEl = ref(null)
let mediaStream = null
let retryTimer = null
let autoDetectTimer = null
let autoDetectInFlight = false
let trainingStatusTimer = null
const autoSessionId = ref("")
const autoDetectConsecutiveErrors = ref(0)
const datasetZipFile = ref(null)
const photoFiles = ref([])
const photoLabelName = ref("")
const trainingEpochs = ref(30)
const trainingImgsz = ref(640)
const trainingState = ref("idle")
const trainingMessage = ref("")
const trainingDatasetDir = ref("")
const trainingModelPath = ref("")

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

const buildAutoSessionId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `autosess-${Date.now()}-${Math.floor(Math.random() * 100000)}`

const extractApiErrorMessage = (error, fallback) => {
  const data = error?.response?.data
  if (!data) return fallback
  if (typeof data.detail === "string" && data.detail) return data.detail
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) return String(data.non_field_errors[0])
  if (typeof data === "object") {
    const firstKey = Object.keys(data)[0]
    const firstVal = data[firstKey]
    if (Array.isArray(firstVal) && firstVal.length) return `${firstKey}: ${firstVal[0]}`
    if (typeof firstVal === "string" && firstVal) return `${firstKey}: ${firstVal}`
  }
  return fallback
}

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

const loadTuning = () => {
  const raw = localStorage.getItem(TUNE_STORAGE_KEY)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === "object") {
      tuning.value = { ...tuning.value, ...parsed }
    }
  } catch {}
}

const saveTuning = () => {
  localStorage.setItem(TUNE_STORAGE_KEY, JSON.stringify(tuning.value))
}

const onDatasetFileChange = (event) => {
  const file = event?.target?.files?.[0]
  datasetZipFile.value = file || null
}
const onPhotoFilesChange = (event) => {
  photoFiles.value = Array.from(event?.target?.files || [])
}

const fetchTrainingStatus = async () => {
  try {
    const res = await api.cameraActuals.getShapeTrainingStatus()
    trainingState.value = res.data.state || "idle"
    trainingMessage.value = res.data.message || ""
    trainingDatasetDir.value = res.data.dataset_dir || ""
    trainingModelPath.value = res.data.model_path || ""
  } catch (error) {
    trainingMessage.value = extractApiErrorMessage(error, "学習状態の取得に失敗しました。")
  }
}

const uploadDataset = async () => {
  if (!datasetZipFile.value) return
  const formData = new FormData()
  formData.append("dataset_zip", datasetZipFile.value)
  try {
    await api.cameraActuals.uploadShapeDataset(formData)
    datasetZipFile.value = null
    trainingMessage.value = "データセットをアップロードしました。"
    await fetchTrainingStatus()
  } catch (error) {
    trainingMessage.value = extractApiErrorMessage(error, "データセットアップロードに失敗しました。")
  }
}

const uploadPhotos = async () => {
  if (!photoFiles.value.length) return
  const label = String(photoLabelName.value || "").trim()
  if (!label) {
    trainingMessage.value = "写真ラベル（製品コード）を入力してください。"
    return
  }
  const formData = new FormData()
  formData.append("label_name", label)
  photoFiles.value.forEach((f) => formData.append("photos", f))
  try {
    const res = await api.cameraActuals.uploadShapePhotos(formData)
    trainingMessage.value = `写真を ${res.data.count || 0} 枚取り込みました。`
    photoFiles.value = []
    await fetchTrainingStatus()
  } catch (error) {
    trainingMessage.value = extractApiErrorMessage(error, "写真取込に失敗しました。")
  }
}

const startShapeTraining = async () => {
  try {
    await api.cameraActuals.startShapeTraining({
      epochs: Number(trainingEpochs.value || 30),
      imgsz: Number(trainingImgsz.value || 640),
      base_model: "yolov8n.pt",
    })
    trainingMessage.value = "学習を開始しました。"
    await fetchTrainingStatus()
  } catch (error) {
    trainingMessage.value = extractApiErrorMessage(error, "学習開始に失敗しました。")
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
  autoDetectInFlight = false
  if (autoDetectTimer) {
    clearInterval(autoDetectTimer)
    autoDetectTimer = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  if (videoEl.value) {
    videoEl.value.srcObject = null
  }
}

const captureFrameDataUrl = () => {
  if (!videoEl.value || !captureCanvasEl.value) return ""
  const video = videoEl.value
  const canvas = captureCanvasEl.value
  const width = video.videoWidth || 640
  const height = video.videoHeight || 360
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext("2d")
  if (!ctx) return ""
  ctx.drawImage(video, 0, 0, width, height)
  return canvas.toDataURL("image/jpeg", 0.7)
}

const runAutoDetectOnce = async () => {
  if (!isCapturing.value || captureMode.value !== "auto" || autoDetectInFlight) return
  if (!videoEl.value || videoEl.value.readyState < 2 || videoEl.value.videoWidth < 32 || videoEl.value.videoHeight < 32) return
  const frameDataUrl = captureFrameDataUrl()
  if (!frameDataUrl) return
  autoDetectInFlight = true
  try {
    const res = await api.cameraActuals.autoDetect({
      session_id: autoSessionId.value,
      line_id: Number(selectedLineId.value),
      process_id: Number(selectedProcessId.value),
      product_id: Number(selectedProductId.value),
      frame_data_url: frameDataUrl,
      frame_captured_at: new Date().toISOString(),
      device_id: getDeviceId(),
      ...tuning.value,
    })
    const passCount = Number(res.data.pass_count || 0)
    const detectedCount = Number(res.data.detected_count || 0)
    expectedShapeCode.value = String(res.data.expected_shape_code || "")
    lastShapeCode.value = String(res.data.shape_code || "")
    lastShapeMatch.value = Boolean(res.data.shape_match)
    sessionPassCount.value += passCount
    sessionCount.value += passCount
    dailyCount.value = Number(res.data.total_count || dailyCount.value)
    statusLabel.value = detectedCount > 0
      ? `検知 ${detectedCount}件 / 通過 +${passCount}件（累計 ${sessionPassCount.value}件）`
      : `監視中（累計通過 ${sessionPassCount.value}件）`
    if (passCount > 0) {
      lastAcceptedAt.value = new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    }
    errorMessage.value = ""
    autoDetectConsecutiveErrors.value = 0
  } catch (error) {
    autoDetectConsecutiveErrors.value += 1
    statusLabel.value = "自動検知エラー"
    const detail = extractApiErrorMessage(error, "自動検知に失敗しました。")
    errorMessage.value = detail
    const shouldStop =
      error?.response?.status === 503 ||
      autoDetectConsecutiveErrors.value >= 3 ||
      String(detail).includes("未インストール")
    if (shouldStop && autoDetectTimer) {
      clearInterval(autoDetectTimer)
      autoDetectTimer = null
      statusLabel.value = "自動検知停止"
      errorMessage.value = `${detail} 自動送信を停止しました。依存導入後に再度「カメラ開始」を押してください。`
    }
  } finally {
    autoDetectInFlight = false
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
    sessionPassCount.value = 0
    autoDetectConsecutiveErrors.value = 0
    autoSessionId.value = buildAutoSessionId()
    await refreshDailyCount()
    if (captureMode.value === "auto") {
      autoDetectTimer = setInterval(() => {
        runAutoDetectOnce().catch(() => {})
      }, Number(tuning.value.frame_interval_ms || 1200))
    }
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
  loadTuning()
  scheduleFlush()
  trainingStatusTimer = setInterval(() => {
    fetchTrainingStatus().catch(() => {})
  }, 3000)
  try {
    await fetchMasters()
    const firstProduct = (products.value || [])[0]
    if (firstProduct?.product_code) photoLabelName.value = firstProduct.product_code
    await fetchTrainingStatus()
  } catch (error) {
    errorMessage.value = "初期データの取得に失敗しました。"
  }
  if (queue.value.length) {
    flushQueue().catch(() => {})
  }
})
watch(selectedProductId, (nextId) => {
  const p = products.value.find((x) => String(x.id) === String(nextId))
  if (p?.product_code) photoLabelName.value = p.product_code
})

onBeforeUnmount(() => {
  stopCapture()
  if (retryTimer) clearInterval(retryTimer)
  if (trainingStatusTimer) clearInterval(trainingStatusTimer)
})
watch(
  () => tuning.value.frame_interval_ms,
  (nextMs) => {
    saveTuning()
    if (!isCapturing.value || captureMode.value !== "auto") return
    const intervalMs = Math.max(200, Number(nextMs || 1200))
    if (autoDetectTimer) clearInterval(autoDetectTimer)
    autoDetectTimer = setInterval(() => {
      runAutoDetectOnce().catch(() => {})
    }, intervalMs)
  }
)
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
.mode-select {
  min-width: 190px;
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
.preview-wrap {
  position: relative;
}
.cross-line {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 2px;
  background: rgba(239, 68, 68, 0.8);
  transform: translateX(-50%);
  pointer-events: none;
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
.hidden-canvas {
  display: none;
}
.tuning-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 6px 10px;
}
.tuning-grid label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  gap: 8px;
}
.tuning-grid input {
  width: 90px;
  height: 28px;
}
.sub-title {
  margin: 0 0 8px;
  font-size: 15px;
}
.train-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.train-row label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.train-row input[type="number"] {
  width: 88px;
  height: 30px;
}
.train-status {
  display: grid;
  gap: 3px;
  font-size: 12px;
}
</style>





