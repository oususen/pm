<template>
  <div class="page-container">
    <h2 class="page-title">分割計画取込</h2>

    <div class="tab-row">
      <button class="tab-btn" :class="{ active: tab === 'import' }" @click="tab = 'import'">取込</button>
      <button class="tab-btn" :class="{ active: tab === 'history' }" @click="tab = 'history'; fetchLogs()">履歴</button>
    </div>

    <div v-if="tab === 'import'" class="import-section">
      <div class="file-input-row">
        <label class="file-label">
          分割計画Excel選択
          <input type="file" accept=".xlsx,.xls" @change="onFileSelect" />
        </label>
        <button class="btn-primary" :disabled="!file || importing" @click="doImport">
          {{ importing ? '取込中...' : '取込実行' }}
        </button>
      </div>
      <p class="help-text">外作先から返却された分割計画Excelを取り込みます。BOM展開も同時に実行されます。</p>

      <div v-if="confirmData" class="confirm-section">
        <h3>上書き確認</h3>
        <div v-for="(w, i) in confirmData.warnings.filter(x => x.message.includes('上書き'))" :key="i" class="warning-item">
          [{{ w.case_no }}]: {{ w.message }}
        </div>
        <div class="confirm-actions">
          <button class="btn-danger" :disabled="importing" @click="doConfirmedImport">
            {{ importing ? '取込中...' : '上書き実行' }}
          </button>
          <button class="btn-cancel" @click="confirmData = null">キャンセル</button>
        </div>
      </div>

      <div v-if="result" class="result-section">
        <h3>取込結果</h3>
        <div class="result-summary">
          <span class="badge badge-success">更新: {{ result.updated_count }}件</span>
          <span class="badge badge-warning">警告: {{ result.warning_count }}件</span>
          <span class="badge badge-error">エラー: {{ result.error_count }}件</span>
        </div>

        <div v-if="result.updated && result.updated.length" class="updated-list">
          <h4>更新された案件</h4>
          <table class="data-table">
            <thead><tr><th>案件番号</th><th>分割数</th><th>合計数量</th><th>材料支給</th></tr></thead>
            <tbody>
              <tr v-for="u in result.updated" :key="u.case_no">
                <td>{{ u.case_no }}</td>
                <td class="text-center">{{ u.split_count }}</td>
                <td class="text-right">{{ u.total_qty }}</td>
                <td class="text-center">{{ u.material_count || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="result.warnings && result.warnings.length" class="warning-list">
          <h4>警告</h4>
          <div v-for="(w, i) in result.warnings" :key="i" class="warning-item">
            行{{ w.row }} [{{ w.case_no }}]: {{ w.message }}
          </div>
        </div>

        <div v-if="result.errors && result.errors.length" class="error-list">
          <h4>エラー</h4>
          <div v-for="(e, i) in result.errors" :key="i" class="error-item">
            行{{ e.row }} [{{ e.case_no }}]: {{ e.message }}
          </div>
        </div>
      </div>
    </div>

    <div v-else>
      <table v-if="logs.length" class="data-table">
        <thead>
          <tr>
            <th>取込日時</th>
            <th>ファイル名</th>
            <th>取込者</th>
            <th>更新</th>
            <th>警告</th>
            <th>エラー</th>
            <th>詳細</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td class="nowrap">{{ formatDateTime(log.created_at) }}</td>
            <td>{{ log.file_name }}</td>
            <td>{{ log.imported_by || '-' }}</td>
            <td class="text-center">
              <span class="badge badge-success">{{ log.updated_count }}</span>
            </td>
            <td class="text-center">
              <span v-if="log.warning_count" class="badge badge-warning">{{ log.warning_count }}</span>
              <span v-else>-</span>
            </td>
            <td class="text-center">
              <span v-if="log.error_count" class="badge badge-error">{{ log.error_count }}</span>
              <span v-else>-</span>
            </td>
            <td>
              <button class="btn-detail" @click="toggleDetail(log.id)">
                {{ expandedId === log.id ? '閉じる' : '表示' }}
              </button>
            </td>
          </tr>
          <template v-for="log in logs" :key="'d-' + log.id">
            <tr v-if="expandedId === log.id" class="detail-row">
              <td colspan="7">
                <div v-if="log.detail?.updated?.length" class="detail-section">
                  <strong>更新案件:</strong>
                  <span v-for="u in log.detail.updated" :key="u.case_no" class="detail-tag">{{ u.case_no }} ({{ u.split_count }}分割/{{ u.total_qty }}個)</span>
                </div>
                <div v-if="log.detail?.warnings?.length" class="detail-section">
                  <strong>警告:</strong>
                  <div v-for="(w, i) in log.detail.warnings" :key="i" class="warning-item">行{{ w.row }} [{{ w.case_no }}]: {{ w.message }}</div>
                </div>
                <div v-if="log.detail?.errors?.length" class="detail-section">
                  <strong>エラー:</strong>
                  <div v-for="(e, i) in log.detail.errors" :key="i" class="error-item">行{{ e.row }} [{{ e.case_no }}]: {{ e.message }}</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div v-else class="empty">取込履歴がありません</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/api/client'

const tab = ref('import')
const file = ref(null)
const importing = ref(false)
const result = ref(null)
const confirmData = ref(null)
const logs = ref([])
const expandedId = ref(null)

function onFileSelect(e) {
  file.value = e.target.files[0] || null
  result.value = null
  confirmData.value = null
}

async function doImport() {
  if (!file.value) return
  importing.value = true
  result.value = null
  confirmData.value = null

  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const res = await api.outsource.importSplitExcel(formData)
    if (res.data.needs_confirm) {
      confirmData.value = res.data
    } else {
      result.value = res.data
    }
  } catch (err) {
    result.value = {
      updated_count: 0,
      warning_count: 0,
      error_count: 1,
      updated: [],
      warnings: [],
      errors: [{ row: 0, case_no: '-', message: err.response?.data?.error || err.message }],
    }
  } finally {
    importing.value = false
  }
}

async function doConfirmedImport() {
  if (!file.value) return
  importing.value = true
  confirmData.value = null
  result.value = null

  try {
    const formData = new FormData()
    formData.append('file', file.value)
    formData.append('confirm', 'true')
    const res = await api.outsource.importSplitExcel(formData)
    result.value = res.data
  } catch (err) {
    result.value = {
      updated_count: 0,
      warning_count: 0,
      error_count: 1,
      updated: [],
      warnings: [],
      errors: [{ row: 0, case_no: '-', message: err.response?.data?.error || err.message }],
    }
  } finally {
    importing.value = false
  }
}

async function fetchLogs() {
  try {
    const res = await api.outsource.getSplitImportLogs({ ordering: '-created_at' })
    logs.value = res.data.results || res.data
  } catch (err) {
    console.error(err)
  }
}

function toggleDetail(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function formatDateTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${mo}-${da} ${h}:${mi}`
}
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 8px; }
.tab-row { display: flex; gap: 4px; margin-bottom: 12px; border-bottom: 2px solid #eee; }
.tab-btn { padding: 6px 14px; border: none; background: transparent; cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab-btn.active { border-bottom-color: #1976d2; color: #1976d2; font-weight: 600; }
.file-input-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.file-label { font-size: 13px; display: flex; align-items: center; gap: 8px; }
.help-text { font-size: 12px; color: #666; margin-bottom: 16px; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.result-section { margin-top: 16px; }
.result-section h3 { font-size: 14px; margin-bottom: 8px; }
.result-summary { display: flex; gap: 12px; margin-bottom: 12px; }
.badge { padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #e65100; }
.badge-error { background: #fbe9e7; color: #c62828; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.nowrap { white-space: nowrap; }

.updated-list h4, .warning-list h4, .error-list h4 { font-size: 13px; margin: 8px 0 4px; }
.warning-item { color: #e65100; font-size: 12px; padding: 2px 0; }
.error-item { color: #c62828; font-size: 12px; padding: 2px 0; }

.confirm-section { margin-top: 16px; padding: 12px; background: #fff3e0; border: 1px solid #ffcc80; border-radius: 4px; }
.confirm-section h3 { font-size: 14px; margin-bottom: 8px; color: #e65100; }
.confirm-actions { margin-top: 10px; display: flex; gap: 8px; }
.btn-danger { padding: 6px 16px; background: #d32f2f; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancel { padding: 6px 16px; background: #e0e0e0; color: #333; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-detail { padding: 2px 8px; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 4px; cursor: pointer; font-size: 11px; }
.detail-row td { background: #fafafa; }
.detail-section { margin: 4px 0; font-size: 12px; }
.detail-tag { display: inline-block; margin: 2px 4px; padding: 1px 6px; background: #e8f5e9; border-radius: 3px; font-size: 11px; }
.empty { color: #888; padding: 10px; }
</style>
