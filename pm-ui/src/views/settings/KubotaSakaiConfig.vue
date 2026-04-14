<template>
  <div class="page">
    <h1 class="page-title">クボタ堺便計画設定</h1>
    <div class="card">
      <div class="row">
        <label>未割付期限（日）</label>
        <input v-model.number="deadlineDays" type="number" min="0" />
      </div>
      <p class="help">調整後納期の何営業日前までに便割付を完了すべきかを設定します。</p>
      <div class="actions">
        <button class="btn" :disabled="loading || saving" @click="load">再読込</button>
        <button class="btn primary" :disabled="loading || saving" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'

const KEY = 'kubota_sakai.assignment_deadline_days'
const loading = ref(false)
const saving = ref(false)
const deadlineDays = ref(3)

const load = async () => {
  loading.value = true
  try {
    const res = await api.systemSettings.getAll()
    const value = res.data?.[KEY]?.value
    const parsed = Number(value)
    deadlineDays.value = Number.isFinite(parsed) ? parsed : 3
  } catch (error) {
    const message = error?.response?.data?.detail || '設定取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    await api.systemSettings.updateByKey({
      [KEY]: Number(deadlineDays.value || 0),
    })
    alert('保存しました。')
    await load()
  } catch (error) {
    const message = error?.response?.data?.detail || '設定保存に失敗しました。'
    alert(message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.page-title { margin: 0 0 12px 0; font-size: 20px; }
.card {
  max-width: 560px;
  background: #fff;
  border: 1px solid #d7dfe8;
  border-radius: 8px;
  padding: 16px;
}
.row { display: flex; gap: 12px; align-items: center; }
.row label { width: 160px; font-weight: 700; }
.row input { width: 120px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 4px; }
.help { color: #64748b; font-size: 12px; margin: 10px 0 16px; }
.actions { display: flex; gap: 8px; }
.btn { padding: 6px 12px; border: 1px solid #b5c1d2; background: #fff; border-radius: 4px; cursor: pointer; }
.btn.primary { background: #dff3e6; border-color: #8fc8a1; }
</style>
