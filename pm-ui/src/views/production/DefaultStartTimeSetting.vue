<template>
  <div class="settings-container">
    <h2 class="page-title">デフォルト開始時刻設定</h2>
    <p class="helper-text">ライン別に最終工程のデフォルト開始時刻と「休憩明けに補正」を設定します。</p>

    <div class="card">
      <div class="card-header">
        <div class="summary">
          <span>対象ライン: {{ filteredRows.length }} 件</span>
          <span v-if="lastSavedAt">最終保存: {{ lastSavedAt }}</span>
        </div>
        <div class="filters">
          <label class="filter-label">区分</label>
          <select v-model="lineFilter" :disabled="loading">
            <option value="all">すべて</option>
            <option value="internal">社内</option>
            <option value="purchase">購買先</option>
          </select>
        </div>
        <div class="actions">
          <button class="btn" @click="reload" :disabled="loading">再読込</button>
          <button class="btn primary" @click="saveAll" :disabled="loading || saving || !canEdit">保存</button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="setting-table">
          <thead>
            <tr>
              <th class="col-line">ライン</th>
              <th class="col-time">デフォルト開始時刻</th>
              <th class="col-check">休憩明けに補正</th>
              <th class="col-updated">更新日時</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.line">
              <td class="col-line">
                <div class="line-code">{{ row.line_code }}</div>
                <div class="line-name">{{ row.line_name }}</div>
              </td>
              <td class="col-time">
                <input
                  type="text"
                  inputmode="numeric"
                  maxlength="5"
                  placeholder="08:00"
                  :value="row.final_process_start_time"
                  @input="(e) => onTimeInput(row, e.target.value)"
                  @blur="(e) => onTimeBlur(row, e.target.value)"
                  :disabled="!canEdit"
                />
              </td>
              <td class="col-check">
                <label class="check-wrap">
                  <input type="checkbox" v-model="row.adjust_to_break_end" :disabled="!canEdit" />
                  <span>ON</span>
                </label>
              </td>
              <td class="col-updated">
                <span v-if="row.updated_at">{{ formatDateTime(row.updated_at) }}</span>
                <span v-else class="muted">未設定</span>
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="4" class="no-data">ラインがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const rows = ref([])
const lineFilter = ref('all')
const loading = ref(false)
const saving = ref(false)
const lastSavedAt = ref('')

const canEdit = computed(() => hasPermission(authState.user, 'production.plan_input', 'edit'))

const normalizeTimeInput = (value, padOnBlur = false) => {
  const raw = String(value || '').replace(/[^0-9]/g, '')
  if (!raw) return ''
  const digits = raw.slice(0, 4)
  if (digits.length <= 2) {
    const h = digits
    return padOnBlur ? `${h.padStart(2, '0')}:00` : h
  }
  if (digits.length === 3) {
    const h = digits.slice(0, 1)
    const m = digits.slice(1, 3)
    return padOnBlur ? `${h.padStart(2, '0')}:${m}` : `${h}:${m}`
  }
  const h = digits.slice(0, 2)
  const m = digits.slice(2, 4)
  return `${h}:${m}`
}

const formatDateTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const y = d.getFullYear()
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  const hh = `${d.getHours()}`.padStart(2, '0')
  const mm = `${d.getMinutes()}`.padStart(2, '0')
  return `${y}/${m}/${day} ${hh}:${mm}`
}

const reload = async () => {
  loading.value = true
  try {
    const [lineRes, settingRes] = await Promise.all([
      api.lines.getLines(),
      api.lineDefaultScheduleSettings.getLineDefaultScheduleSettings(),
    ])
    const lines = (lineRes.data?.results || lineRes.data || []).sort((a, b) =>
      (a.line_code || '').localeCompare(b.line_code || '')
    )
    const map = {}
    ;(settingRes.data?.results || settingRes.data || []).forEach((s) => {
      map[s.line] = s
    })
    rows.value = lines.map((l) => {
      const setting = map[l.id] || {}
      return {
        line: l.id,
        line_code: l.line_code,
        line_name: l.line_name,
        line_type: l.line_type || '',
        final_process_start_time: setting.final_process_start_time || '',
        adjust_to_break_end: setting.adjust_to_break_end !== undefined ? setting.adjust_to_break_end : true,
        updated_at: setting.updated_at || '',
      }
    })
  } catch (e) {
    console.error('デフォルト開始時刻設定の読込に失敗しました', e)
    alert('デフォルト開始時刻設定の読込に失敗しました。')
  } finally {
    loading.value = false
  }
}

const onTimeInput = (row, value) => {
  row.final_process_start_time = normalizeTimeInput(value)
}

const onTimeBlur = (row, value) => {
  row.final_process_start_time = normalizeTimeInput(value, true)
}

const saveAll = async () => {
  saving.value = true
  try {
    const settings = rows.value.map((r) => ({
      line: r.line,
      final_process_start_time: r.final_process_start_time || null,
      adjust_to_break_end: !!r.adjust_to_break_end,
    }))
    await api.lineDefaultScheduleSettings.bulkSaveLineDefaultScheduleSettings(settings)
    lastSavedAt.value = formatDateTime(new Date().toISOString())
    await reload()
    alert('保存しました。')
  } catch (e) {
    console.error('デフォルト開始時刻設定の保存に失敗しました', e)
    alert('保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

onMounted(reload)

const filteredRows = computed(() => {
  if (lineFilter.value === 'internal') {
    return rows.value.filter((r) => r.line_type === 'PROD')
  }
  if (lineFilter.value === 'purchase') {
    return rows.value.filter((r) => r.line_type === 'PURCHASE')
  }
  return rows.value
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.page-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}
.helper-text {
  margin: 0 0 10px;
  color: #475569;
  font-size: 12px;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.filters select {
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  min-width: 120px;
}
.summary {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #334155;
}
.actions {
  display: flex;
  gap: 8px;
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
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.table-wrap {
  overflow-x: auto;
}
.setting-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.setting-table th,
.setting-table td {
  border: 1px solid #d7dfe8;
  padding: 6px 8px;
  font-size: 12px;
  color: #111;
}
.setting-table thead th {
  background: #e7edf7;
}
.col-line {
  width: 220px;
}
.line-code {
  font-weight: 700;
}
.line-name {
  color: #475569;
  font-size: 12px;
}
.col-time {
  width: 140px;
}
.col-time input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  font-size: 13px;
  text-align: center;
  color: #111827;
}
.col-check {
  width: 140px;
  text-align: center;
}
.check-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #0f766e;
}
.col-updated {
  width: 180px;
  color: #475569;
}
.muted {
  color: #94a3b8;
}
.no-data {
  text-align: center;
  color: #6b7280;
  padding: 10px 0;
}
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .summary {
    flex-direction: column;
    gap: 4px;
  }
  .filters {
    width: 100%;
  }
}
</style>

