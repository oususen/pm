<template>
  <div class="qr-overlay" @click.self="close">
    <div class="qr-box">
      <div class="qr-header">
        <span>QRコードを読み取ってください</span>
        <button class="close-btn" @click="close">✕</button>
      </div>
      <video ref="videoRef" class="qr-video" playsinline autoplay muted></video>
      <canvas ref="canvasRef" style="display:none"></canvas>
      <p v-if="error" class="qr-error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
// カメラでQRを読み取り、生の文字列を scanned で返す（jsQR。PurchaseReceivingMobile と同じ方式）
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import jsQR from 'jsqr'

const emit = defineEmits(['scanned', 'close'])
const videoRef = ref(null)
const canvasRef = ref(null)
const error = ref('')
let stream = null
let frame = null
let active = true

const stop = () => {
  active = false
  if (frame) { cancelAnimationFrame(frame); frame = null }
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null }
}

const close = () => {
  stop()
  emit('close')
}

const scanFrame = () => {
  if (!active || !videoRef.value || !canvasRef.value) return
  const video = videoRef.value
  if (video.readyState < video.HAVE_ENOUGH_DATA) {
    frame = requestAnimationFrame(scanFrame)
    return
  }
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  const code = jsQR(ctx.getImageData(0, 0, canvas.width, canvas.height).data, canvas.width, canvas.height)
  if (code && code.data) {
    stop()
    emit('scanned', code.data)
    return
  }
  frame = requestAnimationFrame(scanFrame)
}

onMounted(async () => {
  await nextTick()
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } },
    })
    videoRef.value.srcObject = stream
    videoRef.value.play()
    frame = requestAnimationFrame(scanFrame)
  } catch {
    error.value = 'カメラを起動できません。カメラの権限を確認してください（HTTPSが必要です）。'
  }
})

onBeforeUnmount(stop)
</script>

<style scoped>
.qr-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center; z-index: 1100; }
.qr-box { background: #fff; border-radius: 8px; padding: 10px; width: 92%; max-width: 480px; }
.qr-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-weight: 600; }
.close-btn { border: none; background: none; font-size: 1.3em; cursor: pointer; }
.qr-video { width: 100%; border-radius: 4px; background: #000; }
.qr-error { color: #c62828; font-size: 0.85em; }
</style>
