<template>
  <div class="settings-container">
    <h2 class="page-title">文字起こし設定</h2>
    <div class="card">
      <div v-if="loading" class="loading">読み込み中...</div>
      <template v-else>
        <p class="description">
          通話録音の文字起こし（faster-whisper）に関する設定です。
        </p>

        <div class="field">
          <label>モデル常駐</label>
          <div class="toggle-row">
            <label class="toggle-label">
              <input type="checkbox" v-model="modelResident" />
              <span>文字起こしモデルをメモリに常駐させる</span>
            </label>
          </div>
          <p class="helper">
            有効: モデルを常にメモリに保持し、文字起こしを即座に開始します（約2GB使用）。<br>
            無効: 文字起こし完了後にモデルを解放し、メモリを節約します（次回はロードに数十秒かかります）。
          </p>
        </div>

        <div class="actions">
          <button class="btn primary" @click="save" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>

        <div v-if="saveMessage" class="save-message" :class="saveError ? 'error' : 'success'">
          {{ saveMessage }}
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'

const loading = ref(true)
const saving = ref(false)
const modelResident = ref(false)
const saveMessage = ref('')
const saveError = ref(false)

const fetchConfig = async () => {
  try {
    const res = await api.systemSettings.getAll()
    const settings = res.data
    const val = settings.whisper_model_resident?.value || 'false'
    modelResident.value = ['true', '1', 'yes'].includes(String(val).toLowerCase())
  } catch (e) {
    console.error('設定取得エラー', e)
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  saveMessage.value = ''
  try {
    await api.systemSettings.updateByKey({
      whisper_model_resident: modelResident.value ? 'true' : 'false',
    })
    saveMessage.value = '保存しました'
    saveError.value = false
  } catch (e) {
    saveMessage.value = '保存に失敗しました'
    saveError.value = true
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
  max-width: 720px;
}
.description {
  color: #555;
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.6;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.field > label {
  font-size: 12px;
  color: #444;
}
.helper {
  margin: 0;
  font-size: 12px;
  color: #666;
  line-height: 1.6;
}
.toggle-row {
  display: flex;
  align-items: center;
}
.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
}
.toggle-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.actions {
  margin-top: 12px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.save-message {
  margin-top: 10px;
  padding: 8px;
  border-radius: 4px;
  font-size: 13px;
}
.save-message.success {
  background: #d4edda;
  color: #155724;
}
.save-message.error {
  background: #fee;
  color: #c00;
}
.loading {
  color: #999;
  text-align: center;
  padding: 2rem;
}
</style>
