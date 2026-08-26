<template>
  <div class="page-container converter-page">
    <div class="page-header">
      <h1 class="page-title">ティエラCSV変換 <DataSourceDialog title="ティエラCSV変換" :sources="dsSources" /></h1>
    </div>

    <div class="converter-layout">
      <section class="panel">
        <h2 class="panel-title">変換元</h2>
        <div class="form-grid">
          <div class="form-group full-width">
            <label>ティエラ原本CSV *</label>
            <input type="file" accept=".csv" @change="onSourceFileSelected" />
            <p class="field-hint">
              構成品番の先頭に付いた `■` の数で親子階層を判断します。例: `A` が親、`■B` が子、`■■C` が孫です。
            </p>
          </div>
          <div class="form-group">
            <label>版</label>
            <input v-model="bomImportForm.version" />
          </div>
          <div class="form-group">
            <label>有効開始日 *</label>
            <input type="date" v-model="bomImportForm.valid_from" />
          </div>
          <div class="form-group">
            <label>有効終了日</label>
            <input type="date" v-model="bomImportForm.valid_to" />
          </div>
          <div class="form-group full-width">
            <label>備考</label>
            <input v-model="bomImportForm.remark" />
          </div>
          <div class="form-group inline-check">
            <label><input type="checkbox" v-model="bomImportForm.is_active" /> 有効</label>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">実行</h2>
        <div class="action-row">
          <button class="btn-primary" :disabled="!canEdit || converting" @click="executeConvert">
            {{ converting ? '変換中...' : '変換' }}
          </button>
          <button class="btn-success" :disabled="!canEdit || !converted || productImporting" @click="executeProductImport">
            {{ productImporting ? '品番導入中...' : '品番導入' }}
          </button>
          <button class="btn-warning" :disabled="!canEdit || !converted || bomImporting" @click="executeBomImport">
            {{ bomImporting ? 'BOM導入中...' : 'BOM導入' }}
          </button>
        </div>
        <p class="hint-text">
          変換結果はCSVのみ保持します。重複親品番の判定は品番導入後に更新します。BOM導入後は、作成したBOM詳細を開いてそのままルーティング生成へ進めます。
        </p>
      </section>

      <section class="panel" v-if="converted">
        <h2 class="panel-title">変換結果</h2>
        <div class="result-grid">
          <div class="result-item">
            <span class="result-label">完成品</span>
            <span class="result-value">{{ converted.final_code }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">品番導入</span>
            <span class="result-value">{{ converted.product_filename }} / {{ converted.product_row_count }}件</span>
          </div>
          <div class="result-item">
            <span class="result-label">BOM導入</span>
            <span class="result-value">{{ converted.bom_filename }} / {{ converted.bom_row_count }}件</span>
          </div>
        </div>
        <div class="action-row mt-12">
          <button class="btn-secondary" @click="downloadCsv(converted.product_csv, converted.product_filename)">品番CSV保存</button>
          <button class="btn-secondary" @click="downloadCsv(converted.bom_csv, converted.bom_filename)">BOM CSV保存</button>
        </div>
      </section>

      <section class="panel" v-if="duplicateBomDetails.length">
        <h2 class="panel-title">既存BOMの再利用指定</h2>
        <p class="hint-text no-top-margin">
          既存BOMを使いたい親品番だけチェックしてください。チェックした親品番は既存BOMを使い、その親配下の子明細は今回の取込で追加しません。
        </p>
        <div class="duplicate-list">
          <label v-for="item in duplicateBomDetails" :key="item.parent_code" class="duplicate-item">
            <input
              type="checkbox"
              :value="item.parent_code"
              v-model="selectedReuseParentCodes"
            />
            <span class="duplicate-code">{{ item.parent_code }}</span>
            <span class="duplicate-meta">既存BOM ID: {{ item.bom_id }} / 開始日: {{ item.valid_from }}</span>
          </label>
        </div>
      </section>

      <section class="panel" v-if="productImportResult">
        <h2 class="panel-title">品番導入結果</h2>
        <div class="result-grid">
          <div class="result-item">
            <span class="result-label">新規</span>
            <span class="result-value">{{ productImportResult.created ?? 0 }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">更新</span>
            <span class="result-value">{{ productImportResult.updated ?? 0 }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">変更なし</span>
            <span class="result-value">{{ productImportResult.skipped ?? 0 }}</span>
          </div>
        </div>
      </section>

      <section class="panel" v-if="bomImportResult">
        <h2 class="panel-title">BOM導入結果</h2>
        <div class="result-grid">
          <div class="result-item">
            <span class="result-label">作成BOM</span>
            <span class="result-value">{{ bomImportResult.created_boms ?? 0 }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">作成明細</span>
            <span class="result-value">{{ bomImportResult.created_items ?? 0 }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">再利用BOM</span>
            <span class="result-value">{{ bomImportResult.reused_boms ?? 0 }}</span>
          </div>
          <div class="result-item" v-if="bomImportResult.skipped_child_rows_for_reuse != null">
            <span class="result-label">再利用でスキップした行</span>
            <span class="result-value">{{ bomImportResult.skipped_child_rows_for_reuse }}</span>
          </div>
        </div>
        <div class="open-bom-row" v-if="latestBomId">
          <button class="btn-secondary" @click="openLatestBom">最新BOMを開く</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { formatISODate } from '@/utils/dateUtil'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const router = useRouter()

const dsSources = [
  { op: '読み書き', table: 'm_product', desc: '製品マスタ（品番導入）' },
  { op: '読み書き', table: 'm_bom', desc: 'BOMヘッダ（BOM導入）' },
  { op: '読み書き', table: 'm_bom_item', desc: 'BOM明細（BOM導入）' },
  { op: '読み取り', table: 'm_process', desc: '工程マスタ（取込照合）' },
  { op: '読み取り', table: 'm_line', desc: 'ラインマスタ（取込照合）' },
  { op: '読み取り', table: 'm_supplier', desc: '仕入先マスタ（取込照合）' },
]

const canEdit = computed(() => canAccessMasterResource('masters.bom', 'edit'))
const sourceFile = ref(null)
const converting = ref(false)
const productImporting = ref(false)
const bomImporting = ref(false)
const converted = ref(null)
const productImportResult = ref(null)
const bomImportResult = ref(null)
const latestBomId = ref(null)
const duplicateBomDetails = ref([])
const selectedReuseParentCodes = ref([])

const bomImportForm = ref({
  version: 'v1',
  valid_from: formatISODate(new Date()),
  valid_to: '',
  remark: '',
  is_active: true,
})

const onSourceFileSelected = (event) => {
  sourceFile.value = event.target.files?.[0] || null
  converted.value = null
  productImportResult.value = null
  bomImportResult.value = null
  latestBomId.value = null
  duplicateBomDetails.value = []
  selectedReuseParentCodes.value = []
}

const buildCsvFile = (content, filename) => {
  return new File([`\ufeff${content}`], filename, { type: 'text/csv;charset=utf-8' })
}

const downloadCsv = (content, filename) => {
  const blob = new Blob([`\ufeff${content}`], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

const executeConvert = async () => {
  if (!sourceFile.value) {
    alert('ティエラ原本CSVを選択してください')
    return
  }
  converting.value = true
  try {
    const fd = new FormData()
    fd.append('file', sourceFile.value)
    const res = await api.boms.convertTieraImportPayload(fd)
    converted.value = res.data
    productImportResult.value = null
    bomImportResult.value = null
    latestBomId.value = null
    duplicateBomDetails.value = []
    selectedReuseParentCodes.value = []
  } catch (error) {
    console.error('ティエラCSV変換エラー:', error)
    alert(error?.response?.data?.detail || '変換に失敗しました')
  } finally {
    converting.value = false
  }
}

const refreshDuplicateBomDetails = async () => {
  if (!converted.value) return
  try {
    const fd = new FormData()
    fd.append('file', buildCsvFile(converted.value.bom_csv, converted.value.bom_filename))
    fd.append('version', bomImportForm.value.version || 'v1')
    fd.append('completed_product_code', converted.value.final_code || '')
    fd.append('valid_from', bomImportForm.value.valid_from || '')
    const res = await api.boms.importBOMCheck(fd)
    duplicateBomDetails.value = Array.isArray(res.data?.duplicate_bom_details)
      ? res.data.duplicate_bom_details
      : []
    selectedReuseParentCodes.value = []
  } catch (_) {
    duplicateBomDetails.value = []
    selectedReuseParentCodes.value = []
  }
}

const executeProductImport = async () => {
  if (!converted.value) {
    alert('先に変換してください')
    return
  }
  productImporting.value = true
  try {
    const fd = new FormData()
    fd.append('file', buildCsvFile(converted.value.product_csv, converted.value.product_filename))
    const res = await api.products.bulkUpdateImport(fd)
    productImportResult.value = res.data
    await refreshDuplicateBomDetails()
    alert('品番導入が完了しました')
  } catch (error) {
    console.error('品番導入エラー:', error)
    alert(error?.response?.data?.detail || '品番導入に失敗しました')
  } finally {
    productImporting.value = false
  }
}

const executeBomImport = async () => {
  if (!converted.value) {
    alert('先に変換してください')
    return
  }
  if (!bomImportForm.value.valid_from) {
    alert('有効開始日を入力してください')
    return
  }
  bomImporting.value = true
  try {
    const fd = new FormData()
    fd.append('file', buildCsvFile(converted.value.bom_csv, converted.value.bom_filename))
    fd.append('version', bomImportForm.value.version || 'v1')
    fd.append('completed_product_code', converted.value.final_code || '')
    fd.append('valid_from', bomImportForm.value.valid_from)
    fd.append('valid_to', bomImportForm.value.valid_to || '')
    fd.append('remark', bomImportForm.value.remark || '')
    fd.append('is_active', String(!!bomImportForm.value.is_active))
    fd.append('reuse_parent_codes', selectedReuseParentCodes.value.join(','))
    const res = await api.boms.importBOMCsv(fd)
    bomImportResult.value = res.data
    latestBomId.value = res.data?.completed_bom_id || null
    if (latestBomId.value) {
      alert('BOM導入が完了しました。作成したBOMを開けます。')
    } else {
      alert('BOM導入は完了しましたが、完成品BOMの特定はできませんでした。')
    }
  } catch (error) {
    console.error('BOM導入エラー:', error)
    const detail = error?.response?.data?.detail || 'BOM導入に失敗しました'
    const errors = error?.response?.data?.errors
    const duplicateDetails = error?.response?.data?.duplicate_bom_details
    if (Array.isArray(duplicateDetails)) {
      duplicateBomDetails.value = duplicateDetails
    }
    if (Array.isArray(errors) && errors.length > 0) {
      alert(`${detail}\n\n${errors.slice(0, 10).join('\n')}`)
    } else {
      alert(detail)
    }
  } finally {
    bomImporting.value = false
  }
}

const openLatestBom = () => {
  if (!latestBomId.value) return
  router.push({
    name: 'BOMMaster',
    query: {
      bomId: String(latestBomId.value),
      detail: 'full',
    },
  })
}
</script>

<style scoped>
.converter-page {
  padding: 16px;
}

.converter-layout {
  display: grid;
  gap: 16px;
}

.panel {
  background: #fffdf5;
  border: 1px solid #e8dcc0;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 8px 24px rgba(110, 82, 20, 0.08);
}

.panel-title {
  margin: 0 0 14px;
  font-size: 18px;
  color: #42311a;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: #5b4b34;
}

.field-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6d5a40;
}

.form-group input[type="text"],
.form-group input[type="date"],
.form-group input[type="file"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d7c7a8;
  border-radius: 8px;
  background: #fff;
  box-sizing: border-box;
}

.inline-check {
  justify-content: flex-end;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.result-item {
  background: #fff;
  border: 1px solid #eadfca;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-label {
  font-size: 12px;
  color: #7a6a55;
}

.result-value {
  font-size: 16px;
  font-weight: 700;
  color: #2e2418;
  word-break: break-all;
}

.open-bom-row {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.btn-primary,
.btn-success,
.btn-warning,
.btn-secondary {
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 700;
}

.btn-primary {
  background: #1f6feb;
  color: #fff;
}

.btn-success {
  background: #18864b;
  color: #fff;
}

.btn-warning {
  background: #b66a14;
  color: #fff;
}

.btn-secondary {
  background: #fff;
  color: #53432f;
  border-color: #d5c3a0;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.hint-text {
  margin: 12px 0 0;
  color: #6d5a40;
  font-size: 13px;
}

.no-top-margin {
  margin-top: 0;
}

.mt-12 {
  margin-top: 12px;
}

.duplicate-list {
  display: grid;
  gap: 10px;
}

.duplicate-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #eadfca;
  border-radius: 10px;
  background: #fff;
}

.duplicate-code {
  font-weight: 700;
  color: #2e2418;
  min-width: 100px;
}

.duplicate-meta {
  color: #6d5a40;
  font-size: 13px;
}

@media (max-width: 720px) {
  .action-row {
    flex-direction: column;
  }
}
</style>
