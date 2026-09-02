<template>
  <div class="freq-editor">
    <div class="header-row">
      <h3>レーザ加工頻度パターン</h3>
      <button class="btn primary" @click="openNew">新規</button>
    </div>
    <table class="freq-table">
      <thead>
        <tr>
          <th>コード</th>
          <th>パターン名</th>
          <th>頻度種別</th>
          <th>条件</th>
          <th>有効</th>
          <th>備考</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td>{{ row.pattern_code }}</td>
          <td>{{ row.pattern_name }}</td>
          <td>{{ freqTypeLabel(row.frequency_type) }}</td>
          <td>{{ conditionLabel(row) }}</td>
          <td>{{ row.is_active ? '有効' : '無効' }}</td>
          <td>{{ row.note }}</td>
          <td class="actions">
            <button class="btn-sm" @click="openEdit(row)">編集</button>
            <button class="btn-sm danger" @click="remove(row)">削除</button>
          </td>
        </tr>
        <tr v-if="!rows.length"><td colspan="7" class="empty">データがありません</td></tr>
      </tbody>
    </table>

    <div v-if="showDialog" class="modal-overlay" @click.self="showDialog = false">
      <div class="modal-content">
        <h3>{{ form.id ? '加工頻度パターン編集' : '加工頻度パターン新規作成' }}</h3>
        <div class="form-group">
          <label>パターンコード *</label>
          <input v-model.trim="form.pattern_code" type="text" />
        </div>
        <div class="form-group">
          <label>パターン名 *</label>
          <input v-model.trim="form.pattern_name" type="text" />
        </div>
        <div class="form-group">
          <label>頻度種別 *</label>
          <select v-model="form.frequency_type">
            <option value="DAILY">毎日</option>
            <option value="WEEKLY">毎週曜日</option>
            <option value="EVERY_N_DAYS">N営業日ごと</option>
          </select>
        </div>
        <div v-if="form.frequency_type === 'WEEKLY'" class="form-group">
          <label>加工曜日 *</label>
          <select v-model.number="form.day_of_week">
            <option :value="0">月</option>
            <option :value="1">火</option>
            <option :value="2">水</option>
            <option :value="3">木</option>
            <option :value="4">金</option>
          </select>
        </div>
        <div v-if="form.frequency_type === 'EVERY_N_DAYS'" class="form-group">
          <label>間隔営業日数 *</label>
          <input v-model.number="form.interval_days" type="number" min="2" />
        </div>
        <div class="form-group">
          <label><input v-model="form.is_active" type="checkbox" /> 有効</label>
        </div>
        <div class="form-group">
          <label>備考</label>
          <input v-model.trim="form.note" type="text" />
        </div>
        <div class="form-actions">
          <button class="btn primary" @click="save">保存</button>
          <button class="btn" @click="showDialog = false">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'

const rows = ref([])
const showDialog = ref(false)
const emptyForm = () => ({ id: null, pattern_code: '', pattern_name: '', frequency_type: 'DAILY', day_of_week: 0, interval_days: 2, is_active: true, note: '' })
const form = ref(emptyForm())
const DOW = ['月', '火', '水', '木', '金']

const freqTypeLabel = (type) => ({ DAILY: '毎日', WEEKLY: '毎週曜日', EVERY_N_DAYS: 'N営業日ごと' })[type] || type
const conditionLabel = (row) => {
  if (row.frequency_type === 'WEEKLY') return `毎週 ${DOW[row.day_of_week] || ''}`
  if (row.frequency_type === 'EVERY_N_DAYS') return `${row.interval_days}営業日ごと`
  return ''
}

const load = async () => {
  const { data } = await api.laserProcessingFreqPatterns.getPatterns()
  rows.value = Array.isArray(data) ? data : (data.results || [])
}

const openNew = () => { form.value = emptyForm(); showDialog.value = true }
const openEdit = (row) => { form.value = { ...row }; showDialog.value = true }

const save = async () => {
  if (!form.value.pattern_code || !form.value.pattern_name) { window.alert('コードとパターン名を入力してください。'); return }
  try {
    if (form.value.id) {
      await api.laserProcessingFreqPatterns.updatePattern(form.value.id, form.value)
    } else {
      await api.laserProcessingFreqPatterns.createPattern(form.value)
    }
    showDialog.value = false
    await load()
  } catch (e) {
    window.alert(e.response?.data?.detail || e.response?.data?.pattern_code?.[0] || '保存に失敗しました。')
  }
}

const remove = async (row) => {
  if (!confirm(`${row.pattern_code} を削除しますか？`)) return
  try {
    await api.laserProcessingFreqPatterns.deletePattern(row.id)
    await load()
  } catch (e) {
    window.alert(e.response?.data?.detail || '削除に失敗しました。')
  }
}

onMounted(load)
</script>

<style scoped>
.freq-editor { padding: 8px }
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px }
.header-row h3 { margin: 0; font-size: 14px }
.freq-table { border-collapse: collapse; width: 100%; font-size: 12px }
.freq-table th, .freq-table td { border: 1px solid #cbd5e1; padding: 6px 8px }
.freq-table th { background: #e2e8f0 }
.freq-table .empty { text-align: center; color: #6b7280 }
.freq-table .actions { white-space: nowrap }
.btn { border: 1px solid #94a3b8; background: #fff; border-radius: 4px; padding: 5px 10px; cursor: pointer }
.btn.primary { background: #0f766e; color: #fff; border-color: #0f766e }
.btn-sm { border: 1px solid #94a3b8; background: #fff; border-radius: 4px; padding: 3px 8px; cursor: pointer; font-size: 12px }
.btn-sm.danger { border-color: #b91c1c; color: #b91c1c }
.modal-overlay { position: fixed; inset: 0; z-index: 20; display: grid; place-items: center; background: rgba(15,23,42,.35) }
.modal-content { width: 400px; padding: 16px; background: #fff; border-radius: 6px; box-shadow: 0 12px 28px rgba(15,23,42,.3) }
.modal-content h3 { margin: 0 0 12px; font-size: 16px }
.form-group { margin-bottom: 10px }
.form-group label { display: block; font-size: 12px; margin-bottom: 3px }
.form-group input[type="text"], .form-group input[type="number"], .form-group select { width: 100%; height: 32px; border: 1px solid #cbd5e1; border-radius: 4px; padding: 0 8px; box-sizing: border-box }
.form-group input[type="checkbox"] { margin-right: 4px }
.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px }
</style>
