<template>
  <div class="page-container">
    <h2 class="page-title">分割計画取込</h2>

    <div class="import-section">
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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/api/client'

const file = ref(null)
const importing = ref(false)
const result = ref(null)

function onFileSelect(e) {
  file.value = e.target.files[0] || null
  result.value = null
}

async function doImport() {
  if (!file.value) return
  importing.value = true
  result.value = null

  try {
    const formData = new FormData()
    formData.append('file', file.value)
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
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }
.file-input-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.file-label { font-size: 13px; display: flex; align-items: center; gap: 8px; }
.help-text { font-size: 12px; color: #666; margin-bottom: 16px; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.result-section { margin-top: 16px; }
.result-section h3 { font-size: 14px; margin-bottom: 8px; }
.result-summary { display: flex; gap: 12px; margin-bottom: 12px; }
.badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #e65100; }
.badge-error { background: #fbe9e7; color: #c62828; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }

.updated-list h4, .warning-list h4, .error-list h4 { font-size: 13px; margin: 8px 0 4px; }
.warning-item { color: #e65100; font-size: 12px; padding: 2px 0; }
.error-item { color: #c62828; font-size: 12px; padding: 2px 0; }
</style>
