// チャットの音声入力。ブラウザで録音し、サーバー(PC内のWhisper)で文字にして返す。
// 音声はサーバーに保存されない。文字は入力欄へ入れるだけで、自動では送信しない。
import { computed, onBeforeUnmount, ref } from 'vue'
import api from '@/api/client'

const MAX_SECONDS = 60
const MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']

const pickMimeType = () => {
  if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return ''
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || ''
}

export function useVoiceInput(onText) {
  const supported = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'
  const recording = ref(false)
  const transcribing = ref(false)
  const seconds = ref(0)
  const error = ref('')
  const busy = computed(() => recording.value || transcribing.value)
  let recorder = null
  let stream = null
  let chunks = []
  let timer = null

  const releaseStream = () => {
    clearInterval(timer)
    timer = null
    stream?.getTracks().forEach((track) => track.stop())
    stream = null
  }

  const transcribe = async (blob) => {
    transcribing.value = true
    seconds.value = 0
    timer = setInterval(() => { seconds.value += 1 }, 1000)
    try {
      const extension = blob.type.includes('mp4') ? 'mp4' : 'webm'
      const form = new FormData()
      form.append('audio', blob, `voice.${extension}`)
      const { data } = await api.aiChat.transcribe(form)
      const text = String(data.text || '').trim()
      if (text) onText(text)
      else error.value = '音声から文字を認識できませんでした。もう一度、はっきりお話しください。'
    } catch (requestError) {
      error.value = requestError.response?.data?.detail || '音声を文字にできませんでした。'
    } finally {
      clearInterval(timer)
      timer = null
      transcribing.value = false
    }
  }

  const start = async () => {
    error.value = ''
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      error.value = 'マイクを使えません。ブラウザのマイクの許可を確認してください。'
      return
    }
    const mimeType = pickMimeType()
    chunks = []
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    recorder.ondataavailable = (event) => { if (event.data?.size) chunks.push(event.data) }
    recorder.onstop = () => {
      const type = recorder?.mimeType || mimeType || 'audio/webm'
      releaseStream()
      recording.value = false
      const blob = new Blob(chunks, { type })
      chunks = []
      if (blob.size) void transcribe(blob)
    }
    recorder.start()
    recording.value = true
    seconds.value = 0
    timer = setInterval(() => {
      seconds.value += 1
      if (seconds.value >= MAX_SECONDS) stop()
    }, 1000)
  }

  const stop = () => {
    if (recorder && recorder.state !== 'inactive') recorder.stop()
  }

  const toggle = () => {
    if (transcribing.value) return
    if (recording.value) stop()
    else void start()
  }

  onBeforeUnmount(() => {
    if (recorder && recorder.state !== 'inactive') {
      recorder.onstop = null
      recorder.stop()
    }
    releaseStream()
  })

  return { supported, recording, transcribing, seconds, error, busy, toggle, MAX_SECONDS }
}
